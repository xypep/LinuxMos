"""The island window and application.

States of the pill (in priority order while folded):
  activity  short live event (volume, brightness, Caps Lock, layout, charging,
            network, headphones, timer/Pomodoro, to-do due, water, rain, ...)
  timer     a running countdown (timer or Pomodoro)
  lyrics    the line being sung (if "lyrics in the pill" is on)
  media     music is playing
  compact   a thin line (minimal notch)
  mascot    the user is away: the clock rests and a pair of eyes comes out
  idle      clock, temperature, battery
Hovering, clicking or a hotkey opens it into the tab view.

Idle cost: no polling. The clock ticks once a minute; everything else is
D-Bus signals or X11 events. Animations run on the frame clock only while
the island changes size.
"""

import ctypes
import math
import signal
import sys
from pathlib import Path

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("GdkPixbuf", "2.0")
gi.require_version("GdkX11", "3.0")
import cairo  # noqa: E402
from gi.repository import Gdk, GdkX11, Gio, GLib, Gtk  # noqa: E402

try:
    gi.require_version("Wnck", "3.0")
    from gi.repository import Wnck  # noqa: E402
except (ValueError, ImportError):
    Wnck = None

from island import APP_ID, __version__  # noqa: E402
from island.pages import (ClipboardPage, ControlsPage, HomePage, NotePage, ShelfPage,  # noqa: E402
                          TodoPage, URI_TARGETS, WaterPage, WeatherPage)
from island.services import art, system  # noqa: E402
from island.services.clipboard import ClipboardHistory  # noqa: E402
from island.services.idle import IdleWatcher  # noqa: E402
from island.services.indicators import Indicators, volume_icon  # noqa: E402
from island.services.lyrics import LyricsFetcher, line_index  # noqa: E402
from island.services.mpris import MprisWatcher  # noqa: E402
from island.services.power import Battery  # noqa: E402
from island.services.shelf import Shelf  # noqa: E402
from island.services.timer import Timer, format_seconds  # noqa: E402
from island.services.todo import TodoList  # noqa: E402
from island.services.water import Water  # noqa: E402
from island.services.weather import Weather  # noqa: E402
from island.storage import Config  # noqa: E402
from island.tray import Tray  # noqa: E402
from island.widgets import Animator, Eyes, Pill, clear, css_class, icon, label, rounded_image  # noqa: E402

EXPANDED_W, EXPANDED_H, EXPANDED_R = 660, 350, 30
COLLAPSED_H = 34
COLLAPSED_W = {"idle": 196, "mascot": 196, "media": 320, "lyrics": 440, "timer": 220, "activity": 340}
COMPACT_W, COMPACT_H = 110, 8
WIN_W, WIN_H = EXPANDED_W, EXPANDED_H

HOVER_OPEN_MS = 160
HOVER_CLOSE_MS = 320

TABS = [
    ("home", "audio-x-generic-symbolic", "Jetzt"),
    ("clipboard", "edit-paste-symbolic", "Zwischenablage"),
    ("shelf", "folder-symbolic", "Ablage"),
    ("todo", "object-select-symbolic", "Aufgaben"),
    ("note", "document-edit-symbolic", "Notiz & Fokus"),
    ("water", "weather-showers-scattered-symbolic", "Wasser"),
    ("weather", "weather-few-clouds-symbolic", "Wetter"),
    ("controls", "emblem-system-symbolic", "Steuerung"),
]

TERMINALS = {"gnome-terminal-server", "gnome-terminal", "xfce4-terminal", "tilix", "terminator", "kitty",
             "alacritty", "konsole", "xterm", "wezterm", "foot", "guake", "mate-terminal"}


class IslandWindow(Gtk.Window):
    def __init__(self, app):
        super().__init__(application=app)
        self.config = Config.load()
        self.expanded = False
        self.track = None
        self._activity = None       # dict(icon, text, level, sticky)
        self._activity_id = 0
        self._pinned = False        # opened for typing / via hotkey: stays open off-hover
        self._prev_window = None    # Wnck window to return focus and pastes to
        self._dragging_out = False
        self._open_id = self._close_id = self._position_id = 0
        self._shown_kind = None
        self._scroll_acc = 0.0
        self._current_tab = "home"
        self._idle_state = "active"   # active | idle | sleep | hello
        self._hello_id = 0
        self._pomodoro_count = 0
        # Lyrics: fetched lazily, advanced by one timeout per line (no polling)
        self._lyrics_view = False
        self._lyrics_key = None
        self._lyrics_lines = []
        self._lyric_idx = -1
        self._lyric_timer = 0
        self._lyrics_synced_at = 0

        self._setup_window()
        self._load_css()

        # Services first: the pages read from them while building
        self.media = MprisWatcher(self._on_media, self._on_media_position)
        self.lyrics = LyricsFetcher()
        self.clipboard = ClipboardHistory(self.config["clipboard_limit"], self._on_clipboard)
        self.shelf = Shelf(self._on_shelf)
        self.timer = Timer(self._on_timer_tick, self._on_timer_done)
        self.weather = Weather(self.config, self._on_weather)
        self.todo = TodoList(self._on_todo, self._on_todo_due)
        self.water = Water(self.config, self._on_water, self._on_water_remind)

        self.pill = Pill()
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        root.set_size_request(WIN_W, WIN_H)
        root.pack_start(self.pill, False, False, 0)
        self.add(root)

        self.stack = Gtk.Stack(hhomogeneous=False, vhomogeneous=False, interpolate_size=False,
                               transition_duration=140)
        self.stack.add_named(Gtk.Box(), "blank")
        self.stack.add_named(self._build_collapsed(), "collapsed")
        self.stack.add_named(self._build_expanded(), "expanded")
        self.pill.add(self.stack)

        self.battery = Battery(self._on_battery)
        self.indicators = Indicators(self._on_indicator)
        self.idle = IdleWatcher(self._on_idle)
        self.tray = Tray(self)
        self.anim = Animator(self, self._apply_geometry)

        self._schedule_clock()
        self.connect("realize", self._on_realize)
        screen = self.get_screen()
        screen.connect("monitors-changed", lambda *_: self._place())
        screen.connect("size-changed", lambda *_: self._place())
        # The panel can move or change height later (or load after us at login):
        # follow it via its settings instead of polling the work area
        self._panel_settings = system.settings("org.cinnamon")
        if self._panel_settings:
            for key in ("panels-enabled", "panels-height", "panels-autohide"):
                self._panel_settings.connect(f"changed::{key}", lambda *_: self._place_soon())
        self._place_soon(4000)

        if Wnck:
            Wnck.set_client_type(Wnck.ClientType.PAGER)
            self._wnck = Wnck.Screen.get_default()
        else:
            self._wnck = None

    # =========================================================================
    # Window setup
    # =========================================================================
    def _setup_window(self):
        self.set_name("island")
        self.set_title("Island")
        visual = self.get_screen().get_rgba_visual()
        if visual:
            self.set_visual(visual)
        self.set_app_paintable(True)
        self.set_decorated(False)
        self.set_resizable(False)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_keep_above(True)
        self.stick()
        # DOCK: always on top, never in Alt+Tab, below fullscreen windows,
        # and not focused on click (we ask for focus only to type)
        self.set_type_hint(Gdk.WindowTypeHint.DOCK)
        self.set_accept_focus(False)
        self.set_default_size(WIN_W, WIN_H)

        self.add_events(Gdk.EventMask.ENTER_NOTIFY_MASK | Gdk.EventMask.LEAVE_NOTIFY_MASK
                        | Gdk.EventMask.SCROLL_MASK | Gdk.EventMask.SMOOTH_SCROLL_MASK
                        | Gdk.EventMask.BUTTON_PRESS_MASK)
        self.connect("draw", self._on_draw)
        self.connect("enter-notify-event", self._on_enter)
        self.connect("leave-notify-event", self._on_leave)
        self.connect("button-press-event", self._on_button_press)
        self.connect("scroll-event", self._on_scroll)
        self.connect("key-press-event", self._on_key)
        self.connect("focus-out-event", self._on_focus_out)

        self.drag_dest_set(Gtk.DestDefaults.DROP, URI_TARGETS, Gdk.DragAction.COPY)
        self.connect("drag-motion", self._on_drag_motion)
        self.connect("drag-leave", lambda *_: self._schedule_close())
        self.connect("drag-data-received", self._on_drag_data)

    def _load_css(self):
        provider = Gtk.CssProvider()
        provider.load_from_path(str(Path(__file__).with_name("style.css")))
        Gtk.StyleContext.add_provider_for_screen(self.get_screen(), provider,
                                                 Gtk.STYLE_PROVIDER_PRIORITY_USER + 1)

    def _on_realize(self, _widget):
        self._place()
        self.anim.jump(self._collapsed_geometry())
        self._show_collapsed()

    def _place(self):
        display = Gdk.Display.get_default()
        monitor = display.get_primary_monitor() or display.get_monitor(0)
        area = monitor.get_workarea()  # below the top bar
        self.move(area.x + (area.width - WIN_W) // 2, area.y + int(self.config.get("offset_y", 6)))

    def _place_soon(self, delay_ms=600):
        def place():
            self._place()
            return GLib.SOURCE_REMOVE

        GLib.timeout_add(delay_ms, place)

    @staticmethod
    def _on_draw(_widget, cr):
        # Fully transparent window; only the pill paints
        cr.set_operator(cairo.OPERATOR_SOURCE)
        cr.set_source_rgba(0, 0, 0, 0)
        cr.paint()
        cr.set_operator(cairo.OPERATOR_OVER)
        return False

    # =========================================================================
    # Geometry / animation
    # =========================================================================
    def _apply_geometry(self, w, h, r):
        w, h = min(max(w, 1), WIN_W), min(max(h, 1), WIN_H)
        self.pill.set_size_request(int(round(w)), int(round(h)))
        self.pill.radius = r
        self.pill.queue_draw()
        if self.get_window():
            # Clicks outside the pill fall through to the windows below
            x = int((WIN_W - math.ceil(w)) / 2)
            self.input_shape_combine_region(
                cairo.Region(cairo.RectangleInt(x, 0, int(math.ceil(w)), int(math.ceil(h)))))

    def _collapsed_kind(self):
        if self._activity:
            return "activity"
        if self.timer.running:
            return "timer"
        if self.track and self.track.playing:
            if self.config.get("lyrics_in_pill") and self._lyrics_lines and self._lyric_idx >= 0:
                return "lyrics"
            return "media"
        if self.config.get("compact_when_idle"):
            return "compact"
        if self.config.get("mascot", True) and self._idle_state != "active":
            return "mascot"
        return "idle"

    def _collapsed_geometry(self):
        kind = self._collapsed_kind()
        if kind == "compact":
            return (COMPACT_W, COMPACT_H, COMPACT_H / 2)
        return (COLLAPSED_W[kind], COLLAPSED_H, COLLAPSED_H / 2)

    def _show_collapsed(self):
        kind = self._collapsed_kind()
        self._fill_collapsed(kind)
        if kind == "compact":
            self.stack.set_visible_child_full("blank", Gtk.StackTransitionType.NONE)
        else:
            self.stack.set_visible_child_full("collapsed", Gtk.StackTransitionType.CROSSFADE)

    def refresh_collapsed(self):
        """Re-render the folded island and morph to its new size if needed."""
        if self.expanded:
            return
        target = self._collapsed_geometry()
        if target != self.anim.target:
            self.stack.set_visible_child_full("blank", Gtk.StackTransitionType.NONE)
            self.anim.to(target, on_done=lambda: None if self.expanded else self._show_collapsed())
        else:
            self._show_collapsed()

    def expand(self, tab=None, focus=False):
        if tab:
            self.select_tab(tab)
        self._cancel_hover_timers()
        if focus:
            self.request_focus()
        if self.expanded:
            return
        self._remember_active_window()
        self.expanded = True
        self.stack.set_visible_child_full("blank", Gtk.StackTransitionType.NONE)
        self.anim.to((EXPANDED_W, EXPANDED_H, EXPANDED_R), on_done=self._on_expanded, bounce=True)

    def _on_expanded(self):
        if not self.expanded:
            return
        self.stack.set_visible_child_full("expanded", Gtk.StackTransitionType.CROSSFADE)
        self.pages[self._current_tab].on_show()
        self._update_header_time()
        self.media.sync()
        if not self._position_id:
            self._position_id = GLib.timeout_add_seconds(1, self._update_position)
            self._update_position()

    def collapse(self):
        if not self.expanded:
            return
        self._cancel_hover_timers()
        self.expanded = False
        self._pinned = False
        self.pages["note"].flush()
        self.stack.set_visible_child_full("blank", Gtk.StackTransitionType.NONE)
        self._release_focus()
        self.anim.to(self._collapsed_geometry(), on_done=lambda: None if self.expanded else self._show_collapsed())

    def toggle(self, focus=False):
        if self.expanded:
            self.collapse()
        else:
            self.expand(focus=focus)

    def open_tab(self, name):
        """Hotkey entry point: open on a tab, or close if it is already showing."""
        if self.expanded and self._current_tab == name:
            self.collapse()
            return
        self.expand(tab=name, focus=True)
        if name == "clipboard":
            self.pages["clipboard"].focus_search()

    # =========================================================================
    # Folded content
    # =========================================================================
    def _build_collapsed(self):
        self.c_left = Gtk.Box(spacing=6)
        self.c_center = label("", ("pill-text",), xalign=0.5)
        self.eyes = Eyes()
        self.c_center_stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.CROSSFADE,
                                        transition_duration=400, hhomogeneous=False)
        self.c_center_stack.add_named(self.c_center, "text")
        self.c_center_stack.add_named(self.eyes, "eyes")
        self.c_right = Gtk.Box(spacing=6)
        box = Gtk.Box(spacing=8, margin_start=14, margin_end=14)
        box.set_size_request(-1, COLLAPSED_H)
        box.pack_start(self.c_left, False, False, 0)
        box.pack_start(self.c_center_stack, True, True, 0)
        box.pack_end(self.c_right, False, False, 0)
        return box

    def _fill_collapsed(self, kind):
        self._shown_kind = kind
        clear(self.c_left)
        clear(self.c_right)
        self.c_center_stack.set_visible_child_name("eyes" if kind == "mascot" else "text")
        text = ""
        if kind == "activity":
            a = self._activity
            self.c_left.add(icon(a["icon"], 16))
            text = a["text"]
            if a.get("level") is not None:
                bar = Gtk.LevelBar(min_value=0, max_value=1, value=a["level"], valign=Gtk.Align.CENTER)
                bar.set_size_request(80, -1)
                self.c_right.add(bar)
        elif kind == "timer":
            self.c_left.add(icon("alarm-symbolic", 16))
            text = format_seconds(self.timer.remaining)
            self.c_right.add(label(self.timer.label, ("dim", "small"), ellipsize=False))
        elif kind in ("media", "lyrics"):
            slot = Gtk.Box()
            slot.add(icon("audio-x-generic-symbolic", 16))
            self.c_left.add(slot)
            art.load(self.track.art_url, 44, lambda pix: self._set_pill_cover(slot, pix))
            if kind == "lyrics":
                text = self._lyrics_lines[self._lyric_idx][1] or "♪"
                self.c_right.add(icon("media-view-subtitles-symbolic", 14))
            else:
                text = self.track.title or "Wiedergabe"
                self.c_right.add(icon("audio-volume-high-symbolic", 14))
        elif kind == "mascot":
            self.eyes.set_mode({"sleep": "sleep", "hello": "hello"}.get(self._idle_state, "awake"))
        if kind in ("idle", "mascot"):
            if kind == "idle":
                text = GLib.DateTime.new_now_local().format("%H:%M")
            if self.weather.current:
                self.c_left.add(icon(self.weather.current["icon"], 14))
                self.c_left.add(label(f"{self.weather.current['temp']}°", ("small",), ellipsize=False))
            if self.battery.present:
                self.c_right.add(label(f"{self.battery.percentage}%", ("small",), ellipsize=False))
                self.c_right.add(icon(self.battery.icon_name, 14))
        self.c_center.set_text(text)
        self.c_left.show_all()
        self.c_right.show_all()

    def _set_pill_cover(self, slot, pixbuf):
        if pixbuf is None or self._shown_kind not in ("media", "lyrics"):
            return
        clear(slot)
        slot.add(rounded_image(pixbuf, 22, 6, self.get_scale_factor()))
        slot.show_all()

    def show_activity(self, icon_name, text, level=None, sticky=False, seconds=2.5, on_click=None):
        """A short live event in the folded island (like iOS Live Activities).

        on_click: what a click on the folded pill does while the event shows.
        """
        self._activity = {"icon": icon_name, "text": text, "level": level, "sticky": sticky,
                          "on_click": on_click}
        if self._activity_id:
            GLib.source_remove(self._activity_id)
            self._activity_id = 0
        if not sticky:
            self._activity_id = GLib.timeout_add(int(seconds * 1000), self._end_activity)
        if self._shown_kind == "activity" and not self.expanded:
            self._fill_collapsed("activity")  # update in place (e.g. volume steps)
        else:
            self.refresh_collapsed()

    def _end_activity(self):
        self._activity_id = 0
        self._activity = None
        self.refresh_collapsed()
        return GLib.SOURCE_REMOVE

    # =========================================================================
    # Opened content
    # =========================================================================
    def _build_expanded(self):
        self.pages = {
            "home": HomePage(self),
            "clipboard": ClipboardPage(self),
            "shelf": ShelfPage(self),
            "todo": TodoPage(self),
            "note": NotePage(self),
            "water": WaterPage(self),
            "weather": WeatherPage(self),
            "controls": ControlsPage(self),
        }
        self.tab_buttons = {}
        tabs = Gtk.Box(spacing=2)
        for name, icon_name, tooltip in TABS:
            btn = Gtk.Button()
            btn.set_relief(Gtk.ReliefStyle.NONE)
            btn.set_can_focus(False)
            btn.add(icon(icon_name, 16))
            btn.set_tooltip_text(tooltip)
            css_class(btn, "tab")
            btn.connect("clicked", lambda _b, n=name: self.select_tab(n))
            tabs.pack_start(btn, False, False, 0)
            self.tab_buttons[name] = btn

        self.header_time = label("", ("title",), ellipsize=False)
        header = Gtk.Box(spacing=8)
        header.pack_start(tabs, False, False, 0)
        header.pack_end(self.header_time, False, False, 0)

        self.body = Gtk.Stack(transition_type=Gtk.StackTransitionType.CROSSFADE, transition_duration=120)
        for name, page in self.pages.items():
            self.body.add_named(page, name)

        view = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12,
                       margin_top=14, margin_bottom=16, margin_start=18, margin_end=18)
        # Margins come on top of the size request -> subtract them
        view.set_size_request(EXPANDED_W - 36, EXPANDED_H - 30)
        view.pack_start(header, False, False, 0)
        view.pack_start(self.body, True, True, 0)
        self.select_tab("home")
        return view

    def select_tab(self, name):
        if name not in self.pages:
            return
        self._current_tab = name
        self.body.set_visible_child_name(name)
        for tab, btn in self.tab_buttons.items():
            ctx = btn.get_style_context()
            (ctx.add_class if tab == name else ctx.remove_class)("active")
        if self.expanded:
            self.pages[name].on_show()

    def _update_header_time(self):
        now = GLib.DateTime.new_now_local()
        self.header_time.set_text(now.format("%a %e. %b  %H:%M"))

    def _update_position(self):
        if not self.expanded:
            self._position_id = 0
            return GLib.SOURCE_REMOVE
        if self._current_tab == "home" and self.track and self.track.playing:
            # Extrapolated locally – no D-Bus traffic per second
            self.pages["home"].set_position(self.media.position())
        return GLib.SOURCE_CONTINUE

    # =========================================================================
    # Focus & paste
    # =========================================================================
    def _own_xid(self):
        win = self.get_window()
        return win.get_xid() if isinstance(win, GdkX11.X11Window) else None

    def _remember_active_window(self):
        if not self._wnck:
            return
        active = self._wnck.get_active_window()
        if active is not None and active.get_xid() != self._own_xid():
            self._prev_window = active

    def _server_time(self):
        win = self.get_window()
        if isinstance(win, GdkX11.X11Window):
            return GdkX11.x11_get_server_time(win)
        return Gtk.get_current_event_time()

    def request_focus(self):
        """Take the keyboard (only when the user wants to type into the island)."""
        self._pinned = True
        if self.is_active():
            return
        self.set_accept_focus(True)
        self.present_with_time(Gtk.get_current_event_time() or self._server_time())

    def _release_focus(self):
        if self.is_active() and self._prev_window is not None:
            try:
                self._prev_window.activate(self._server_time())
            except GLib.Error:
                pass
        self.set_accept_focus(False)

    def make_typeable(self, widget):
        """Clicking into this widget gives the island keyboard focus."""
        def on_press(*_):
            self.request_focus()
            return False

        widget.connect("button-press-event", on_press)

    def paste(self, item):
        """Copy a clipboard entry and type it into the window the user came from."""
        if not self.clipboard.copy(item):
            return
        target = self._prev_window
        self.collapse()
        if target is None or not system.has("xdotool"):
            self.show_activity("edit-copy-symbolic", "Kopiert")
            return
        names = {(target.get_class_group_name() or "").lower(), (target.get_class_instance_name() or "").lower()}
        keys = "ctrl+shift+v" if names & TERMINALS else "ctrl+v"

        def send():
            system.run(["xdotool", "key", "--clearmodifiers", keys])
            return GLib.SOURCE_REMOVE

        # Give the window manager a moment to hand the focus back
        GLib.timeout_add(180, send)

    # =========================================================================
    # Pointer, keyboard, drag & drop
    # =========================================================================
    def _cancel_hover_timers(self):
        for attr in ("_open_id", "_close_id"):
            if getattr(self, attr):
                GLib.source_remove(getattr(self, attr))
                setattr(self, attr, 0)

    def _on_enter(self, _w, event):
        if self._close_id:
            GLib.source_remove(self._close_id)
            self._close_id = 0
        if not self.expanded and not self._open_id and event.mode == Gdk.CrossingMode.NORMAL:
            self._open_id = GLib.timeout_add(HOVER_OPEN_MS, self._hover_open)
        return False

    def _hover_open(self):
        self._open_id = 0
        if self._pointer_inside():
            self.expand()
        return GLib.SOURCE_REMOVE

    def _on_leave(self, _w, event):
        if event.detail == Gdk.NotifyType.INFERIOR or event.mode != Gdk.CrossingMode.NORMAL:
            return False
        if self._open_id:
            GLib.source_remove(self._open_id)
            self._open_id = 0
        self._schedule_close()
        return False

    def _schedule_close(self):
        if self.expanded and not self._pinned and not self._close_id:
            self._close_id = GLib.timeout_add(HOVER_CLOSE_MS, self._hover_close)

    def _hover_close(self):
        if not self.expanded or self._pinned:
            self._close_id = 0
            return GLib.SOURCE_REMOVE
        if self._pointer_inside() or self._dragging_out or self._button_held():
            return GLib.SOURCE_CONTINUE  # check again shortly
        self._close_id = 0
        self.collapse()
        return GLib.SOURCE_REMOVE

    def _pointer_state(self):
        win = self.get_window()
        pointer = Gdk.Display.get_default().get_default_seat().get_pointer()
        _, x, y, mask = win.get_device_position(pointer)
        return x, y, mask

    def _pointer_inside(self):
        if not self.get_window():
            return False
        x, y, _ = self._pointer_state()
        w, h, _r = self.anim.value
        left = (WIN_W - w) / 2
        return left <= x <= left + w and 0 <= y <= h + 4

    def _button_held(self):
        _, _, mask = self._pointer_state()
        return bool(mask & Gdk.ModifierType.BUTTON1_MASK)

    def _on_button_press(self, _w, event):
        if self.expanded:
            return False
        if self._activity and (self._activity.get("sticky") or self._activity.get("on_click")):
            callback = self._activity.get("on_click")
            self._end_activity()  # e.g. dismiss "Timer abgelaufen"
            if callback:
                callback()
            return True
        self.expand()
        return True

    def _on_scroll(self, _w, event):
        if self.expanded:
            return False
        if event.direction == Gdk.ScrollDirection.SMOOTH:
            _ok, _dx, dy = event.get_scroll_deltas()
            self._scroll_acc += dy
        elif event.direction in (Gdk.ScrollDirection.UP, Gdk.ScrollDirection.DOWN):
            self._scroll_acc += -1 if event.direction == Gdk.ScrollDirection.UP else 1
        if abs(self._scroll_acc) >= 1:
            step = -5 if self._scroll_acc > 0 else 5
            self._scroll_acc = 0.0
            system.volume_step(step, self._on_volume)
        return True

    def _on_volume(self, value, muted=False):
        if value is None:
            return
        text = "Stumm" if muted else f"Lautstärke {value} %"
        self.show_activity(volume_icon(value, muted), text, level=0 if muted else value / 100)

    def _on_key(self, _w, event):
        if event.keyval == Gdk.KEY_Escape and self.expanded:
            self.collapse()
            return True
        return False

    def _on_focus_out(self, *_):
        # The user clicked somewhere else while typing -> fold away
        if self.expanded and self._pinned:
            self._prev_window = None  # focus already went where the user wanted
            self.collapse()
        return False

    def set_dragging_out(self, active):
        self._dragging_out = active
        if not active:
            self._schedule_close()

    def _on_drag_motion(self, _w, context, _x, _y, time):
        if self._dragging_out or self.drag_dest_find_target(context, None) is None:
            return False
        if not self.expanded:
            self.expand(tab="shelf")
        elif self._current_tab != "shelf":
            self.select_tab("shelf")
        if self._close_id:
            GLib.source_remove(self._close_id)
            self._close_id = 0
        Gdk.drag_status(context, Gdk.DragAction.COPY, time)
        return True

    def _on_drag_data(self, _w, _context, _x, _y, data, _info, _time):
        uris = data.get_uris() or []
        added = self.shelf.add(uris)
        if added and not self.expanded:
            self.show_activity("folder-symbolic", f"{added} Datei{'en' if added > 1 else ''} abgelegt")

    # =========================================================================
    # Service callbacks
    # =========================================================================
    def _on_media(self, track):
        self.track = track
        self.pages["home"].update_media(track)
        self._update_lyrics_track()
        if not self.expanded:
            if self._shown_kind == "media" and track and track.playing:
                self._fill_collapsed("media")  # new song: update in place
            else:
                self.refresh_collapsed()

    def _on_clipboard(self):
        self.pages["clipboard"].mark_dirty()

    def _on_shelf(self):
        self.pages["shelf"].rebuild()

    def _on_battery(self, battery, just_plugged):
        self.pages["home"].update_battery(battery)
        if just_plugged:
            self.show_activity(battery.icon_name, f"Lädt · {battery.percentage} %", level=battery.percentage / 100)
        elif self._shown_kind == "idle" and not self.expanded:
            self._fill_collapsed("idle")

    def _on_weather(self, weather, rain_started):
        self.pages["home"].update_weather(weather)
        self.pages["weather"].update(weather)
        if rain_started:
            self.show_activity("weather-showers-symbolic", "Regen in etwa 1 Std.", seconds=6)
        elif self._shown_kind == "idle" and not self.expanded:
            self._fill_collapsed("idle")

    def _on_timer_tick(self):
        self.pages["note"].update_timer(self.timer)
        self.pages["home"].update_timer(self.timer)
        if self.expanded:
            return
        if self._collapsed_kind() == "timer" and self._shown_kind == "timer":
            self.c_center.set_text(format_seconds(self.timer.remaining))
        elif self._collapsed_kind() != self._shown_kind:
            self.refresh_collapsed()

    def _on_timer_done(self):
        system.play_sound()
        if self.timer.label == "Fokus":
            # Pomodoro: focus done -> break starts by itself (every 4th one is long)
            self._pomodoro_count += 1
            long_break = self._pomodoro_count % 4 == 0
            minutes = 15 if long_break else 5
            system.notify("Fokus geschafft", f"Zeit für {minutes} Minuten Pause.")
            self.timer.start(minutes * 60, "Pause")
            self.show_activity("alarm-symbolic", f"Fokus geschafft · {minutes} min Pause", seconds=5)
        elif self.timer.label == "Pause":
            system.notify("Pause vorbei", "Klick auf die Insel startet die nächste Fokus-Runde.")
            self.show_activity("alarm-symbolic", "Pause vorbei · Klick = weiter", sticky=True,
                               on_click=lambda: self.start_pomodoro("focus"))
        else:
            system.notify("Timer abgelaufen", f"{format_seconds(self.timer.total)} sind um.")
            self.show_activity("alarm-symbolic", "Timer abgelaufen", sticky=True)

    def start_pomodoro(self, phase):
        if phase == "focus":
            self.timer.start(25 * 60, "Fokus")
        else:
            self.timer.start(5 * 60, "Pause")

    # ---- to-do, water --------------------------------------------------------
    def _on_todo(self):
        self.pages["todo"].rebuild()

    def _on_todo_due(self, task):
        system.play_sound()
        system.notify("Erinnerung", task["text"])
        self.show_activity("alarm-symbolic", task["text"], sticky=True,
                           on_click=lambda: self.expand(tab="todo"))

    def _on_water(self):
        self.pages["water"].update()

    def _on_water_remind(self):
        portion = self.water.portion
        self.show_activity("weather-showers-scattered-symbolic", f"Zeit für Wasser · Klick = +{portion} ml",
                           seconds=12, on_click=self.water.drink)

    # ---- system events (overlays) -----------------------------------------------
    def _on_indicator(self, kind, **data):
        if kind in ("volume", "brightness") and not self.config.get("osd", True):
            return
        if kind == "volume":
            self._on_volume(data["percent"], data["muted"])
        elif kind == "brightness":
            self.show_activity("display-brightness-symbolic", f"Helligkeit {data['percent']} %",
                               level=data["percent"] / 100)
        elif kind == "capslock":
            self.show_activity("input-keyboard-symbolic", "Feststelltaste an" if data["on"] else "Feststelltaste aus",
                               seconds=1.6)
        elif kind == "layout":
            self.show_activity("input-keyboard-symbolic", f"Tastatur: {data['name']}", seconds=1.8)
        elif kind == "network":
            if data["connected"]:
                icon_name = "network-wireless-symbolic" if data["wireless"] else "network-wired-symbolic"
                self.show_activity(icon_name, f"Verbunden · {data['name']}" if data["name"] else "Wieder online")
            else:
                self.show_activity("network-offline-symbolic", "Keine Verbindung", seconds=4)
        elif kind == "bluetooth":
            if data["connected"]:
                battery = data["battery"]
                text = f"{data['name']} · verbunden" + (f" · {battery} %" if battery is not None else "")
                self.show_activity(data["icon"], text, level=battery / 100 if battery is not None else None,
                                   seconds=3.5)
            else:
                self.show_activity(data["icon"], f"{data['name']} getrennt")

    # ---- mascot ------------------------------------------------------------------
    def _on_idle(self, state):
        if self._hello_id:
            GLib.source_remove(self._hello_id)
            self._hello_id = 0
        if state == "back":
            # Wave hello for a moment, then the clock returns
            self._idle_state = "hello"
            self._hello_id = GLib.timeout_add(2500, self._end_hello)
        else:
            self._idle_state = state
        if self._shown_kind == "mascot" and self._collapsed_kind() == "mascot":
            self.eyes.set_mode({"sleep": "sleep", "hello": "hello"}.get(self._idle_state, "awake"))
        else:
            self.refresh_collapsed()

    def _end_hello(self):
        self._hello_id = 0
        self._idle_state = "active"
        self.refresh_collapsed()
        return GLib.SOURCE_REMOVE

    # ---- options (tray, checkboxes) ----------------------------------------------
    def set_option(self, key, value):
        self.config[key] = value
        self.config.save()
        if key == "lyrics_in_pill":
            self._update_lyrics_track()
        self.refresh_collapsed()

    # ---- lyrics ------------------------------------------------------------------
    def set_lyrics_view(self, active):
        self._lyrics_view = active
        self.pages["home"].show_lyrics_view(active)
        self._update_lyrics_track()

    def _lyrics_wanted(self):
        return bool(self.track and self.track.title and (self._lyrics_view or self.config.get("lyrics_in_pill")))

    def _update_lyrics_track(self):
        """Fetch lyrics for a new song (only if they are shown somewhere)."""
        if not self._lyrics_wanted():
            self._stop_lyric_timer()
            return
        key = self.lyrics.key(self.track)
        if key != self._lyrics_key:
            self._lyrics_key = key
            self._lyrics_lines, self._lyric_idx = [], -1
            self.pages["home"].set_lyrics([], "Lade Lyrics …")
            track = self.track
            self.lyrics.get(track, lambda lines, plain: self._on_lyrics(key, lines, plain))
        else:
            self._advance_lyrics()

    def _on_lyrics(self, key, lines, plain):
        if key != self._lyrics_key:
            return  # song changed meanwhile
        self._lyrics_lines = lines
        if lines:
            self.pages["home"].set_lyrics(lines, None)
        elif plain:
            self.pages["home"].set_lyrics([(None, line) for line in plain.splitlines() if line.strip()],
                                          "Nur unsynchronisierte Lyrics verfügbar")
            self._lyrics_lines = []
        else:
            self.pages["home"].set_lyrics([], "Keine Lyrics gefunden" if plain is not None
                                          else "Lyrics gerade nicht erreichbar (offline?)")
        self._advance_lyrics()

    def _on_media_position(self):
        """The position clock was re-anchored (seek, play/pause, new song)."""
        self._lyrics_synced_at = GLib.get_monotonic_time()
        self._advance_lyrics()

    def _stop_lyric_timer(self):
        if self._lyric_timer:
            GLib.source_remove(self._lyric_timer)
            self._lyric_timer = 0

    def _advance_lyrics(self):
        """Show the current line and sleep until the next one starts."""
        self._stop_lyric_timer()
        if not self._lyrics_lines or not self._lyrics_wanted():
            return
        position = self.media.position()
        if position is None:
            return
        idx = line_index(self._lyrics_lines, position)
        if idx != self._lyric_idx:
            self._lyric_idx = idx
            self.pages["home"].highlight_lyric(idx)
            if not self.expanded:
                if self._collapsed_kind() == "lyrics" and self._shown_kind == "lyrics":
                    self.c_center.set_text(self._lyrics_lines[idx][1] or "♪")
                elif self._collapsed_kind() != self._shown_kind:
                    self.refresh_collapsed()
        if not (self.track and self.track.playing):
            return
        if GLib.get_monotonic_time() - self._lyrics_synced_at > 20_000_000:
            # Re-anchor every ~20 s against drift (calls _on_media_position back)
            self._lyrics_synced_at = GLib.get_monotonic_time()
            self.media.sync()
        if idx + 1 < len(self._lyrics_lines):
            delay_ms = (self._lyrics_lines[idx + 1][0] - position) / 1000
            self._lyric_timer = GLib.timeout_add(int(max(30, delay_ms)), self._on_lyric_timer)

    def _on_lyric_timer(self):
        self._lyric_timer = 0
        self._advance_lyrics()
        return GLib.SOURCE_REMOVE

    # =========================================================================
    # Clock: one wake-up per minute
    # =========================================================================
    def _schedule_clock(self):
        now = GLib.DateTime.new_now_local()
        GLib.timeout_add_seconds(max(1, 60 - now.get_second()), self._on_minute)

    def _on_minute(self):
        if self._shown_kind == "idle" and not self.expanded:
            self.c_center.set_text(GLib.DateTime.new_now_local().format("%H:%M"))
        if self.expanded:
            self._update_header_time()
        self._schedule_clock()
        return GLib.SOURCE_REMOVE


class IslandApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.window = None

    def do_startup(self):
        Gtk.Application.do_startup(self)
        # Actions are reachable via D-Bus, so hotkeys don't need a Python start-up:
        #   gdbus call ... --method org.gtk.Actions.Activate toggle [] {}
        toggle = Gio.SimpleAction.new("toggle", None)
        toggle.connect("activate", lambda *_: self.window and self.window.toggle(focus=True))
        tab = Gio.SimpleAction.new("tab", GLib.VariantType("s"))
        tab.connect("activate", lambda _a, param: self.window and self.window.open_tab(param.unpack()))
        quit_action = Gio.SimpleAction.new("quit", None)
        quit_action.connect("activate", lambda *_: self.quit())
        for action in (toggle, tab, quit_action):
            self.add_action(action)

    def do_activate(self):
        if self.window is None:
            self.window = IslandWindow(self)
            self.window.show_all()
        else:
            # A second start (e.g. from the menu) toggles the running island
            self.window.toggle(focus=True)

    def do_shutdown(self):
        if self.window:
            self.window.pages["note"].flush()
        Gtk.Application.do_shutdown(self)


def _set_process_name(name=b"linuxmos-island"):
    """Show up as 'linuxmos-island' in top/htop instead of 'python3'."""
    try:
        ctypes.CDLL("libc.so.6").prctl(15, ctypes.c_char_p(name), 0, 0, 0)  # PR_SET_NAME
    except (OSError, AttributeError):
        pass


def main(argv=None):
    argv = list(sys.argv if argv is None else argv)
    if "--version" in argv:
        print(f"LinuxMos Island {__version__}")
        return 0
    if "--set-city" in argv:
        i = argv.index("--set-city")
        if i + 1 >= len(argv):
            print("Usage: linuxmos-island --set-city CITY", file=sys.stderr)
            return 2
        cfg = Config.load()
        cfg.update(city=argv[i + 1].strip(), latitude=None, longitude=None)
        cfg.save()
        print(f"Wetter-Ort gesetzt: {cfg['city']}")
        return 0

    _set_process_name()
    app = IslandApp()
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGTERM, lambda: app.quit() or GLib.SOURCE_REMOVE)
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGINT, lambda: app.quit() or GLib.SOURCE_REMOVE)
    return app.run(argv[:1])
