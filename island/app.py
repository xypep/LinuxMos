"""The island window and application.

States of the pill (in priority order while folded):
  card      a bigger live event with text and buttons (notification, recognised
            text, QR code)
  activity  short live event (volume, brightness, Caps Lock, layout, charging,
            network, headphones, timer/Pomodoro, to-do due, water, rain, ...)
  timer     a running countdown (timer or Pomodoro)
  lyrics    the line being sung (if "lyrics in the pill" is on)
  media     music is playing
  compact   a thin line (minimal notch)
  mascot    the user is away: the clock rests and the mascot comes out (eyes, cat, robot or blob)
  idle      clock, temperature, battery
Live marks sit at the folded island's right end in every state but a card:
an orange dot while a microphone records, a green one while a camera is on,
a ring while a download runs (details and the mute button in the opened
island's header). "compact" gives way to "idle" while one shows.
Hovering, clicking or a hotkey opens it into the tab view. The first tab is
the command bar (Ctrl+Alt+Space): apps, files, calculator, units, currencies
and web search in one field, built on first use.
It sits on the primary monitor, a chosen one or the one with the mouse
(config "monitor", see services/monitors.py) and moves on monitor hotplug.

Idle cost: no polling. The clock ticks once a minute; everything else is
D-Bus signals or X11 events (notifications: a D-Bus monitor that only wakes
up when one is sent; camera and downloads: inotify). Animations run on the frame clock only while
the island changes size.
Memory: GTK starts without the OpenGL probe (island/__init__.py), the tabs
but "Now" are built on first use, HTTP goes through curl (services/http.py)
and freed memory is handed back a few seconds after the island folds.
"""

import ctypes
import gc
import math
import os
import signal
import sys
from datetime import datetime
from pathlib import Path

import gi

from island import without_gl

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("GdkPixbuf", "2.0")
gi.require_version("GdkX11", "3.0")
with without_gl():   # GTK starts on import: ~49 MB less (see island/__init__.py)
    import cairo
    from gi.repository import Gdk, GdkX11, Gio, GLib, Gtk, Pango

try:
    gi.require_version("Wnck", "3.0")
    from gi.repository import Wnck  # noqa: E402
except (ValueError, ImportError):
    Wnck = None

from island import APP_ID, __version__, i18n  # noqa: E402
from island.i18n import _, n_  # noqa: E402
from island.pages import (ClipboardPage, ControlsPage, HomePage, LazyPage, NotePage, ShelfPage,  # noqa: E402
                          TodoPage, URI_TARGETS, WaterPage, WeatherPage)
from island.services import art, monitors, ocr, recorder, screenshot, system  # noqa: E402
from island.services.clipboard import ClipboardHistory  # noqa: E402
from island.services.downloads import Downloads, download_dir, human_size  # noqa: E402
from island.services.idle import IdleWatcher  # noqa: E402
from island.services.indicators import Indicators, volume_icon  # noqa: E402
from island.services.lyrics import LyricsFetcher, line_index  # noqa: E402
from island.services.mpris import MprisWatcher  # noqa: E402
from island.services.notifications import URGENCY_CRITICAL, Notifications, desktop_info  # noqa: E402
from island.services.power import Battery  # noqa: E402
from island.services.privacy import Privacy  # noqa: E402
from island.services.shelf import Shelf  # noqa: E402
from island.services.timer import Timer, format_seconds  # noqa: E402
from island.services.todo import TodoList  # noqa: E402
from island.services.vpn import Vpn  # noqa: E402
from island.services.water import Water  # noqa: E402
from island.services.weather import Weather  # noqa: E402
from island.storage import Config  # noqa: E402
from island.tray import Tray  # noqa: E402
from island.widgets import (Animator, Eyes, LiveDots, Pill, button, clear, css_class, icon, label,  # noqa: E402
                            rounded_image)

EXPANDED_W, EXPANDED_H, EXPANDED_R = 660, 350, 30
COLLAPSED_H = 34
COLLAPSED_W = {"idle": 196, "mascot": 196, "media": 320, "lyrics": 440, "timer": 220, "activity": 340}
COMPACT_W, COMPACT_H = 110, 8
CARD_W, CARD_H, CARD_R = 460, 150, 26
# Cards without buttons shrink to their text: header + margins, body lines (or the 40 px picture)
CARD_MIN_H, CARD_CHROME_H, CARD_IMAGE_H = 76, 56, 40
WIN_W, WIN_H = EXPANDED_W, EXPANDED_H

HOVER_OPEN_MS = 160
HOVER_CLOSE_MS = 320
# Time for the compositor to drop the hidden island from the screen before maim shoots
SHOT_HIDE_MS = 200
# A card stays this long, longer while the pointer is on it, and a little after it leaves
CARD_MS = 9000
CARD_LEAVE_MS = 3000
# Notification cards: this long unless the app asks for a time (clamped); critical ones stay
NOTIFY_MS = 7000
NOTIFY_MIN_MS, NOTIFY_MAX_MS = 4000, 15000
# Live marks: config switch -> service attribute
LIVE_SWITCHES = {"privacy_indicator": "privacy", "vpn_status": "vpn", "downloads_progress": "downloads"}
# A new download is announced after this delay (Chrome names it "Unconfirmed 123" at first)
DOWNLOAD_HINT_MS = 1200
# Memory freed while the island was open (tabs, results, editor) goes back to the system this long after it
# folds; the first time a little after start-up
TRIM_MS, TRIM_START_MS = 5000, 15000
# Cinnamon's switch for its own banners; the island turns it off while it shows the cards
BANNERS = ("org.cinnamon.desktop.notifications", "display-notifications")

# Tooltips are German source strings, translated when the tab bar is built
TABS = [
    ("search", "system-search-symbolic", "Suche  (Ctrl+Alt+Space)"),
    ("home", "audio-x-generic-symbolic", "Jetzt"),
    ("clipboard", "edit-paste-symbolic", "Zwischenablage"),
    ("shelf", "folder-symbolic", "Ablage"),
    ("todo", "object-select-symbolic", "Aufgaben"),
    ("note", "document-edit-symbolic", "Notiz & Fokus"),
    ("chat", "face-smile-symbolic", "KI-Chat  (Ctrl+Alt+A)"),
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
        i18n.setup(self.config.get("language", "auto"))
        self.expanded = False
        self.track = None
        self._activity = None       # dict(icon, text, level, sticky)
        self._activity_id = 0
        self._pinned = False        # opened for typing / via hotkey: stays open off-hover
        self._prev_window = None    # Wnck window to return focus and pastes to
        self._dragging_out = False
        self._open_id = self._close_id = self._position_id = 0
        self._monitor = None        # the monitor the island sits on (pointer mode: the last one used)
        self._place_id = 0
        self._shown_kind = None
        self._scroll_acc = 0.0
        self._current_tab = "home"
        self._idle_state = "active"   # active | idle | sleep | hello
        self._hello_id = 0
        self._pomodoro_count = 0
        self._shooting = False
        self._shot_proc = None
        self._shot_stop = None      # ends the running capture: kill maim/slop, SIGINT ffmpeg (finishes the file)
        self._shot_out = ""         # what slop printed (the chosen area)
        self._capture_gen = 0
        self._recording = False
        self._dictation = None      # the ffmpeg recording the microphone (see voice())
        self._transcribing = False
        self._card = None           # dict, see show_card()
        self._card_id = 0
        self._card_shown = None     # the card the widgets were built for
        self._live_prev = (False, False, False)   # microphone, camera, muted: for the hints
        self._downloads_seen = False
        self._download_hint_id = 0
        self._header_live_dirty = False
        self._trim_id = 0
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
        self.clipboard = ClipboardHistory(self.config["clipboard_limit"], self.config["clipboard_autodelete_min"],
                                          self._on_clipboard)
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
        self.stack.add_named(self._build_card(), "card")
        self.stack.add_named(self._build_expanded(), "expanded")
        self.pill.add(self.stack)

        self.battery = Battery(self._on_battery)
        self.indicators = Indicators(self._on_indicator)
        self.idle = IdleWatcher(self._on_idle)
        self.notifications = Notifications(self._on_notification, self._on_notification_closed)
        self.privacy = Privacy(self._on_privacy)
        self.indicators.pactl_listeners.append(self.privacy.on_pactl_line)
        self.vpn = Vpn(self.config, self._on_vpn)
        self.downloads = Downloads(self.config, self._on_downloads, self._on_download_done)
        self._banner_settings = system.settings(BANNERS[0])
        if self._banner_settings:
            self._banner_settings.connect(f"changed::{BANNERS[1]}", self._on_banners_changed)
        self.tray = Tray(self)
        self.anim = Animator(self, self._apply_geometry)
        if self.config.get("notifications_on_island", True):
            self._set_notification_cards(True)
        self._apply_live_switches()

        self._schedule_clock()
        self.connect("realize", self._on_realize)
        screen = self.get_screen()
        screen.connect("monitors-changed", lambda *_: self._on_monitors_changed())
        screen.connect("size-changed", lambda *_: self._place())
        # The panel can move or change height later (or load after us at login):
        # follow it via its settings instead of polling the work area
        self._panel_settings = system.settings("org.cinnamon")
        if self._panel_settings:
            for key in ("panels-enabled", "panels-height", "panels-autohide"):
                self._panel_settings.connect(f"changed::{key}", lambda *_: self._place_soon())
        self._place_soon(4000)
        self._schedule_trim(TRIM_START_MS)

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
        self.set_title("MosIsland")
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

    def _target_monitor(self, display):
        """Config "monitor" -> GdkMonitor; anything not connected falls back to the primary one."""
        choice = self.config.get("monitor", monitors.PRIMARY)
        if choice == monitors.POINTER:
            if self._monitor in monitors.all_monitors(display):
                return self._monitor
            return monitors.primary(display)
        return monitors.find(display, choice) or monitors.primary(display)

    def _place(self):
        display = Gdk.Display.get_default()
        monitor = self._target_monitor(display)
        if monitor is None:
            return  # no monitor at all (all switched off)
        self._monitor = monitor
        x, width, top = monitors.top_of(display, monitor, self._panel_settings)  # below the top bar
        self.move(x + (width - WIN_W) // 2, top + int(self.config.get("offset_y", 6)))

    def _place_soon(self, delay_ms=600):
        """Place again a little later (the panel and the work area settle after us); one pending at a time."""
        if self._place_id:
            GLib.source_remove(self._place_id)

        def place():
            self._place_id = 0
            self._place()
            return GLib.SOURCE_REMOVE

        self._place_id = GLib.timeout_add(delay_ms, place)

    def _on_monitors_changed(self):
        # Plugged in, unplugged, rearranged: move at once, and again once Muffin has
        # put the panels on the new layout (it updates the work areas after GDK's signal)
        self._place()
        self._place_soon(1500)
        self.tray.refresh_monitors()

    def follow_pointer(self):
        """Pointer mode: move the folded island to the monitor under the mouse (hotkeys, tray)."""
        if self.expanded or self.config.get("monitor") != monitors.POINTER:
            return
        monitor = monitors.at_pointer(Gdk.Display.get_default())
        if monitor is not None and monitor != self._monitor:
            self._monitor = monitor
            self._place()

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
        if self._card:
            return "card"
        if self._activity:
            return "activity"
        if self.timer.running:
            return "timer"
        if self.track and self.track.playing:
            if self.config.get("lyrics_in_pill") and self._lyrics_lines and self._lyric_idx >= 0:
                return "lyrics"
            return "media"
        if self.config.get("compact_when_idle") and not self.live_dots.width:
            return "compact"
        if self.config.get("mascot", True) and self._idle_state != "active":
            return "mascot"
        return "idle"

    def _collapsed_geometry(self):
        kind = self._collapsed_kind()
        if kind == "compact":
            return (COMPACT_W, COMPACT_H, COMPACT_H / 2)
        if kind == "card":
            return (CARD_W, self._card["height"], CARD_R)
        marks = self.live_dots.width
        return (COLLAPSED_W[kind] + (marks + 8 if marks else 0), COLLAPSED_H, COLLAPSED_H / 2)

    def _show_collapsed(self):
        kind = self._collapsed_kind()
        self._fill_collapsed(kind)
        if kind == "compact":
            self.stack.set_visible_child_full("blank", Gtk.StackTransitionType.NONE)
        elif kind == "card":
            self.stack.set_visible_child_full("card", Gtk.StackTransitionType.CROSSFADE)
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
        if self._header_live_dirty:
            self._fill_header_live()
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
        if note := self._built("note"):
            note.flush()
        self.stack.set_visible_child_full("blank", Gtk.StackTransitionType.NONE)
        self._release_focus()
        self.anim.to(self._collapsed_geometry(), on_done=lambda: None if self.expanded else self._show_collapsed())
        self._schedule_trim()

    def _schedule_trim(self, delay_ms=TRIM_MS):
        """Give freed memory back once things settle (one pending at a time, never while open)."""
        if self._trim_id:
            GLib.source_remove(self._trim_id)

        def trim():
            self._trim_id = 0
            if not self.expanded:
                _trim_memory()
            return GLib.SOURCE_REMOVE

        self._trim_id = GLib.timeout_add(delay_ms, trim)

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
            self.pages["clipboard"].page.focus_search()
        elif name == "search":
            self.pages["search"].page.focus_entry()
        elif name == "chat" and self.expanded:
            self.pages["chat"].page.focus_entry()

    # =========================================================================
    # Folded content
    # =========================================================================
    def _build_collapsed(self):
        self.c_left = Gtk.Box(spacing=6)
        self.c_center = label("", ("pill-text",), xalign=0.5)
        self.eyes = Eyes(self.config.get("mascot_style", "eyes"))
        self.c_center_stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.CROSSFADE,
                                        transition_duration=400, hhomogeneous=False)
        self.c_center_stack.add_named(self.c_center, "text")
        self.c_center_stack.add_named(self.eyes, "eyes")
        self.c_right = Gtk.Box(spacing=6)
        self.live_dots = LiveDots()   # kept across refills, unlike c_left/c_right
        box = Gtk.Box(spacing=8, margin_start=14, margin_end=14)
        box.set_size_request(-1, COLLAPSED_H)
        box.pack_start(self.c_left, False, False, 0)
        box.pack_start(self.c_center_stack, True, True, 0)
        box.pack_end(self.live_dots, False, False, 0)
        box.pack_end(self.c_right, False, False, 0)
        return box

    def _fill_collapsed(self, kind):
        self._shown_kind = kind
        if kind == "card":
            self._fill_card()
            return
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
            art.load(self.track.art_url, lambda pix: self._set_pill_cover(slot, pix))
            if kind == "lyrics":
                text = self._lyrics_lines[self._lyric_idx][1] or "♪"
                self.c_right.add(icon("media-view-subtitles-symbolic", 14))
            else:
                text = self.track.title or _("Wiedergabe")
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

    # ---- cards: a live event with a few lines of text and buttons ------------------
    def _build_card(self):
        self.card_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6,
                                margin_top=12, margin_bottom=14, margin_start=18, margin_end=12)
        # Margins come on top of the size request -> subtract them
        self.card_box.set_size_request(CARD_W - 30, CARD_H - 26)
        return self.card_box

    def show_card(self, icon_name, title, body, meta="", actions=(), image=None, on_click=None, tools=(),
                  ms=CARD_MS, **extra):
        """Show a card in place of the folded pill.

        icon_name: icon name or Gio.Icon; image: a picture beside the text (GdkPixbuf);
        actions: (label, callback, primary) buttons, tools: (icon, tooltip, callback) small
        buttons in the header – a click on either runs the callback and closes the card;
        on_click: a click on the text does the same; ms: how long it stays (None = until closed);
        extra: kept in the card dict (e.g. the notification it shows).
        """
        self._card = {"icon": icon_name, "title": title, "body": body, "meta": meta, "actions": list(actions),
                      "image": image, "on_click": on_click, "tools": list(tools), "ms": ms, **extra}
        self._card["lines"], self._card["height"] = self._card_size(self._card)
        if ms is None:
            self._stop_card_timer()
        else:
            self._start_card_timer(ms)
        self.refresh_collapsed()

    def _card_size(self, card):
        """(body lines, card height): measured with Pango, so short cards don't show an empty box."""
        lines = 3 if card["actions"] else 4
        if card["actions"]:
            return lines, CARD_H
        layout = self.create_pango_layout(card["body"] or " ")
        font = self.get_pango_context().get_font_description().copy()
        font.set_size(10 * Pango.SCALE)  # .card-body in style.css
        layout.set_font_description(font)
        layout.set_width((CARD_W - 30 - (CARD_IMAGE_H + 10 if card["image"] is not None else 0)) * Pango.SCALE)
        layout.set_wrap(Pango.WrapMode.WORD_CHAR)
        count = layout.get_line_count()
        line_h = layout.get_pixel_extents()[1].height / count
        lines = min(lines, count)
        body_h = max(lines * line_h, CARD_IMAGE_H if card["image"] is not None else 0)
        return lines, int(min(CARD_H, max(CARD_MIN_H, CARD_CHROME_H + body_h)))

    def dismiss_card(self):
        if self._drop_card():
            self.refresh_collapsed()

    def _drop_card(self):
        """Forget the card without redrawing; True if there was one."""
        self._stop_card_timer()
        had, self._card, self._card_shown = self._card is not None, None, None
        return had

    def _start_card_timer(self, ms):
        self._stop_card_timer()
        self._card_id = GLib.timeout_add(ms, self._on_card_timeout)

    def _stop_card_timer(self):
        if self._card_id:
            GLib.source_remove(self._card_id)
            self._card_id = 0

    def _on_card_timeout(self):
        if self._pointer_inside() and not self.expanded:
            return GLib.SOURCE_CONTINUE  # still reading: ask again later
        self._card_id = 0
        self.dismiss_card()
        return GLib.SOURCE_REMOVE

    def _fill_card(self):
        card = self._card
        if self._card_shown is card:
            return  # already built (e.g. an activity arrived meanwhile)
        self._card_shown = card
        clear(self.card_box)
        # Margins come on top of the size request -> subtract them
        self.card_box.set_size_request(CARD_W - 30, card["height"] - 26)
        # Small max widths keep the labels' natural size below the card's, so the pill never grows
        head = Gtk.Box(spacing=8)
        head.pack_start(self._card_icon(card["icon"]), False, False, 0)
        head.pack_start(label(card["title"], ("title",), max_chars=20), True, True, 0)
        if card["meta"]:
            head.pack_start(label(card["meta"], ("dim", "small"), max_chars=22), False, False, 0)
        for icon_name, tooltip, callback in card["tools"]:
            head.pack_start(button(icon_name, tooltip=tooltip, css=("mini",), size=14,
                                   on_click=lambda c=callback: self._card_action(c)), False, False, 0)
        head.pack_start(button("window-close-symbolic", tooltip=_("Schließen"), css=("mini",), size=14,
                               on_click=self.dismiss_card), False, False, 0)

        body = label(card["body"], ("card-body",), max_chars=30)
        body.set_line_wrap(True)
        body.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
        body.set_lines(card["lines"])
        body.set_yalign(0.0)
        if len(card["body"]) > 120:
            body.set_tooltip_text(card["body"][:1000])
        content = body
        if card["image"] is not None:
            content = Gtk.Box(spacing=10)
            picture = rounded_image(card["image"], 40, 9, self.get_scale_factor())
            picture.set_valign(Gtk.Align.START)
            content.pack_start(picture, False, False, 0)
            content.pack_start(body, True, True, 0)
        main = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        main.pack_start(head, False, False, 0)
        main.pack_start(content, True, True, 0)
        if card["on_click"]:
            # The header's buttons keep their own clicks (they have their own input windows)
            main = self._clickable(main, lambda: self._card_action(card["on_click"]))
        self.card_box.pack_start(main, True, True, 0)

        if card["actions"]:
            row = Gtk.Box(spacing=6, halign=Gtk.Align.END)
            for text, callback, primary in card["actions"]:
                row.pack_start(button(text=text, css=("accent",) if primary else (),
                                      on_click=lambda c=callback: self._card_action(c)), False, False, 0)
            self.card_box.pack_end(row, False, False, 0)
        self.card_box.show_all()

    @staticmethod
    def _card_icon(spec):
        if isinstance(spec, Gio.Icon):
            img = Gtk.Image.new_from_gicon(spec, Gtk.IconSize.MENU)
            img.set_pixel_size(16)
            return img
        return icon(spec, 16)

    @staticmethod
    def _clickable(child, on_click):
        """Wrap a widget so a click on it (not on its buttons) runs on_click; hand cursor on hover."""
        box = Gtk.EventBox(visible_window=False)
        box.add(child)
        box.connect("button-release-event",
                    lambda _w, event: event.button == Gdk.BUTTON_PRIMARY and (on_click() or True))
        box.connect("realize", lambda w: w.get_window().set_cursor(
            Gdk.Cursor.new_from_name(w.get_display(), "pointer")))
        return box

    def _card_action(self, callback):
        self.dismiss_card()
        callback()

    # =========================================================================
    # Opened content
    # =========================================================================
    def _build_expanded(self):
        # Only "Now" is built up front: the others the first time they open (memory, start-up time)
        self.pages = {
            "search": LazyPage(self, _command_page),
            "home": HomePage(self),
            "clipboard": LazyPage(self, ClipboardPage),
            "shelf": LazyPage(self, ShelfPage),
            "todo": LazyPage(self, TodoPage),
            "note": LazyPage(self, NotePage),
            "chat": LazyPage(self, _chat_page),
            "water": LazyPage(self, WaterPage),
            "weather": LazyPage(self, WeatherPage),
            "controls": LazyPage(self, ControlsPage),
        }
        self.tab_buttons = {}
        tabs = Gtk.Box(spacing=2)
        for name, icon_name, tooltip in TABS:
            btn = Gtk.Button()
            btn.set_relief(Gtk.ReliefStyle.NONE)
            btn.set_can_focus(False)
            btn.add(icon(icon_name, 16))
            btn.set_tooltip_text(_(tooltip))
            css_class(btn, "tab")
            if name == "chat":    # only there while the AI chat is switched on
                btn.get_child().show()    # show_all() skips a no_show_all widget's children
                btn.set_no_show_all(True)
                btn.set_visible(self.config.get("ai_chat", False))
            btn.connect("clicked", lambda _b, n=name: self._on_tab_clicked(n))
            tabs.pack_start(btn, False, False, 0)
            self.tab_buttons[name] = btn

        self.header_time = label("", ("title",), ellipsize=False)
        self.header_live = Gtk.Box(spacing=2, valign=Gtk.Align.CENTER)   # microphone, camera, VPN, downloads
        header = Gtk.Box(spacing=8)
        header.pack_start(tabs, False, False, 0)
        header.pack_end(self.header_time, False, False, 0)
        header.pack_end(self.header_live, False, False, 0)

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

    def _on_tab_clicked(self, name):
        self.select_tab(name)
        if name == "search":
            # A click on the tab means "I want to type" (hovering never takes the focus)
            self.request_focus()
            self.pages["search"].page.focus_entry()

    def select_tab(self, name):
        if name not in self.pages or (name == "chat" and not self.config.get("ai_chat", False)):
            return
        self._current_tab = name
        self.body.set_visible_child_name(name)
        for tab, btn in self.tab_buttons.items():
            ctx = btn.get_style_context()
            (ctx.add_class if tab == name else ctx.remove_class)("active")
        if self.expanded:
            self.pages[name].on_show()

    def _built(self, name):
        """The page of a tab that was opened before, else None (it reads the state when it is built)."""
        page = self.pages[name]
        return page.page if page.built else None

    def _update_header_time(self):
        self.header_time.set_text(i18n.header_date(datetime.now()))

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
        if self.clipboard.copy(item):
            self._paste_into_previous()

    def paste_text(self, text):
        """Copy a text (e.g. a result of the command bar) and type it into the window the user came from."""
        if ocr.copy_text(text):
            self._paste_into_previous()

    def _paste_into_previous(self):
        target = self._prev_window
        self.collapse()
        if target is None or not system.has("xdotool"):
            self.show_activity("edit-copy-symbolic", _("Kopiert"))
            return
        names = {(target.get_class_group_name() or "").lower(), (target.get_class_instance_name() or "").lower()}
        keys = "ctrl+shift+v" if names & TERMINALS else "ctrl+v"

        def send():
            system.run(["xdotool", "key", "--clearmodifiers", keys])
            return GLib.SOURCE_REMOVE

        # Give the window manager a moment to hand the focus back
        GLib.timeout_add(180, send)

    def leave(self):
        """Fold away without handing the focus back: an app, file or website opens and takes it."""
        self._prev_window = None
        self.collapse()

    def launch_context(self):
        """Lets the window manager give the focus to what the island starts."""
        context = Gdk.Display.get_default().get_app_launch_context()
        context.set_timestamp(self._server_time())
        return context

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
        if self._card and not self.expanded:
            return False  # reading the card: don't open the tabs over it
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
        if self._card and not self.expanded and self._card["ms"] is not None:
            self._start_card_timer(CARD_LEAVE_MS)
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
        if self._card:
            return True  # only the card's own buttons act
        if self._activity and (self._activity.get("sticky") or self._activity.get("on_click")):
            callback = self._activity.get("on_click")
            self._end_activity()  # e.g. dismiss "Time's up"
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
        text = _("Stumm") if muted else _("Lautstärke {percent} %").format(percent=value)
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
            text = n_("{n} Datei abgelegt", "{n} Dateien abgelegt", added).format(n=added)
            self.show_activity("folder-symbolic", text)

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
        if page := self._built("clipboard"):
            page.mark_dirty()

    def _on_shelf(self):
        if page := self._built("shelf"):
            page.rebuild()

    def _on_battery(self, battery, just_plugged):
        self.pages["home"].update_battery(battery)
        if just_plugged:
            self.show_activity(battery.icon_name, _("Lädt · {percent} %").format(percent=battery.percentage),
                               level=battery.percentage / 100)
        elif self._shown_kind == "idle" and not self.expanded:
            self._fill_collapsed("idle")

    def _on_weather(self, weather, rain_started):
        self.pages["home"].update_weather(weather)
        if page := self._built("weather"):
            page.update(weather)
        if rain_started:
            self.show_activity("weather-showers-symbolic", _("Regen in etwa 1 Std."), seconds=6)
        elif self._shown_kind == "idle" and not self.expanded:
            self._fill_collapsed("idle")

    def _on_timer_tick(self):
        if note := self._built("note"):
            note.update_timer(self.timer)
        self.pages["home"].update_timer(self.timer)
        if self.expanded:
            return
        if self._collapsed_kind() == "timer" and self._shown_kind == "timer":
            self.c_center.set_text(format_seconds(self.timer.remaining))
        elif self._collapsed_kind() != self._shown_kind:
            self.refresh_collapsed()

    def _on_timer_done(self):
        system.play_sound()
        if self.timer.kind == "focus":
            # Pomodoro: focus done -> break starts by itself (every 4th one is long)
            self._pomodoro_count += 1
            long_break = self._pomodoro_count % 4 == 0
            minutes = 15 if long_break else 5
            system.notify(_("Fokus geschafft"), _("Zeit für {minutes} Minuten Pause.").format(minutes=minutes))
            self.timer.start(minutes * 60, "break")
            self.show_activity("alarm-symbolic", _("Fokus geschafft · {minutes} min Pause").format(minutes=minutes),
                               seconds=5)
        elif self.timer.kind == "break":
            system.notify(_("Pause vorbei"), _("Klick auf die Insel startet die nächste Fokus-Runde."))
            self.show_activity("alarm-symbolic", _("Pause vorbei · Klick = weiter"), sticky=True,
                               on_click=lambda: self.start_pomodoro("focus"))
        else:
            system.notify(_("Timer abgelaufen"), _("{time} sind um.").format(time=format_seconds(self.timer.total)))
            self.show_activity("alarm-symbolic", _("Timer abgelaufen"), sticky=True)

    def start_pomodoro(self, phase):
        if phase == "focus":
            self.timer.start(25 * 60, "focus")
        else:
            self.timer.start(5 * 60, "break")

    # ---- to-do, water --------------------------------------------------------
    def _on_todo(self):
        if page := self._built("todo"):
            page.rebuild()

    def _on_todo_due(self, task):
        system.play_sound()
        system.notify(_("Erinnerung"), task["text"])
        self.show_activity("alarm-symbolic", task["text"], sticky=True,
                           on_click=lambda: self.expand(tab="todo"))

    def _on_water(self):
        if page := self._built("water"):
            page.update()

    def _on_water_remind(self):
        portion = self.water.portion
        self.show_activity("weather-showers-scattered-symbolic",
                           _("Zeit für Wasser · Klick = +{ml} ml").format(ml=portion),
                           seconds=12, on_click=self.water.drink)

    # ---- system events (overlays) -----------------------------------------------
    def _on_indicator(self, kind, **data):
        if kind in ("volume", "brightness") and not self.config.get("osd", True):
            return
        if kind == "volume":
            self._on_volume(data["percent"], data["muted"])
        elif kind == "brightness":
            self.show_activity("display-brightness-symbolic",
                               _("Helligkeit {percent} %").format(percent=data["percent"]),
                               level=data["percent"] / 100)
        elif kind == "capslock":
            text = _("Feststelltaste an") if data["on"] else _("Feststelltaste aus")
            self.show_activity("input-keyboard-symbolic", text, seconds=1.6)
        elif kind == "layout":
            self.show_activity("input-keyboard-symbolic", _("Tastatur: {name}").format(name=data["name"]), seconds=1.8)
        elif kind == "network":
            if data["connected"]:
                icon_name = "network-wireless-symbolic" if data["wireless"] else "network-wired-symbolic"
                self.show_activity(icon_name, _("Verbunden · {name}").format(name=data["name"]) if data["name"]
                                   else _("Wieder online"))
            else:
                self.show_activity("network-offline-symbolic", _("Keine Verbindung"), seconds=4)
        elif kind == "bluetooth":
            if data["connected"]:
                battery = data["battery"]
                text = _("{name} · verbunden").format(name=data["name"])
                if battery is not None:
                    text += f" · {battery} %"
                self.show_activity(data["icon"], text, level=battery / 100 if battery is not None else None,
                                   seconds=3.5)
            else:
                self.show_activity(data["icon"], _("{name} getrennt").format(name=data["name"]))

    # ---- live marks: microphone, camera, VPN, downloads -----------------------------
    def _apply_live_switches(self):
        for key, attr in LIVE_SWITCHES.items():
            service = getattr(self, attr)
            (service.start if self.config.get(key, True) else service.stop)()
        self._update_live()

    def _update_live(self):
        p, d = self.privacy, self.downloads
        mic = ("muted" if p.mic_muted else "on") if p.mic_apps else None
        download = (-1 if d.percent is None else d.percent) if d.active else None
        if self.live_dots.set_state(mic, bool(p.cam_apps), download):
            self.refresh_collapsed()   # the pill grows or shrinks by the marks
        self._fill_header_live()

    def _fill_header_live(self):
        if not self.expanded:
            self._header_live_dirty = True   # built when the island opens
            return
        self._header_live_dirty = False
        box = self.header_live
        clear(box)
        p, v, d = self.privacy, self.vpn, self.downloads
        if p.mic_apps:
            apps = ", ".join(p.mic_apps)
            tip = (_("Mikrofon stumm: {apps} · Klick = an") if p.mic_muted
                   else _("Mikrofon: {apps} · Klick = stumm")).format(apps=apps)
            box.pack_start(button("microphone-sensitivity-muted-symbolic" if p.mic_muted
                                  else "audio-input-microphone-symbolic", tooltip=tip, size=14,
                                  css=("mini", "live-mic") + (("muted",) if p.mic_muted else ()),
                                  on_click=self.toggle_mic), False, False, 0)
        if p.cam_apps:
            cam = css_class(icon("camera-web-symbolic", 14), "live-cam")
            cam.set_tooltip_text(_("Kamera: {apps}").format(apps=", ".join(p.cam_apps)))
            box.pack_start(cam, False, False, 3)
        if v.names:
            shield = css_class(icon("network-vpn-symbolic", 14), "dim")
            shield.set_tooltip_text(self._vpn_text(with_name=True))
            box.pack_start(shield, False, False, 3)
        if d.active:
            percent = d.percent
            short = f"{percent} %" if percent is not None else human_size(d.total_size)
            lines = [f"{item.name} · {human_size(item.size)} · {human_size(item.speed)}/s"
                     for item in d.items.values()]
            box.pack_start(button("folder-download-symbolic", text=short, tooltip="\n".join(lines), size=14,
                                  css=("mini", "live-download"), on_click=self.open_downloads), False, False, 0)
        box.show_all()

    def toggle_mic(self):
        self.privacy.set_mic_muted(not self.privacy.mic_muted)

    def _on_privacy(self):
        p = self.privacy
        mic_was, cam_was, muted_was = self._live_prev
        new_mic, new_cam = p.mic_apps and not mic_was, p.cam_apps and not cam_was
        if new_cam:
            apps = ", ".join(dict.fromkeys(p.cam_apps + (p.mic_apps if new_mic else [])))
            text = _("Kamera & Mikrofon aktiv · {apps}") if new_mic else _("Kamera aktiv · {apps}")
            self.show_activity("camera-web-symbolic", text.format(apps=apps), seconds=3)
        elif new_mic:
            self.show_activity("audio-input-microphone-symbolic",
                               _("Mikrofon aktiv · {apps}").format(apps=", ".join(p.mic_apps)),
                               seconds=3, on_click=self.toggle_mic)
        elif p.mic_apps and p.mic_muted != muted_was:
            if p.mic_muted:
                self.show_activity("microphone-sensitivity-muted-symbolic", _("Mikrofon stumm"), seconds=1.8)
            else:
                self.show_activity("audio-input-microphone-symbolic", _("Mikrofon an"), seconds=1.8)
        self._live_prev = (bool(p.mic_apps), bool(p.cam_apps), p.mic_muted)
        self._update_live()

    def _vpn_text(self, with_name=False):
        v = self.vpn
        parts = [", ".join(v.names)] if with_name or not v.info else []
        if v.info:
            parts += [f"{v.info['flag']} {v.info['country']}".strip(), v.info["ip"]]
        return "VPN · " + " · ".join(p for p in parts if p)

    def _on_vpn(self, event):
        if event == "up":
            self.show_activity("network-vpn-symbolic",
                               _("VPN verbunden · {name}").format(name=", ".join(self.vpn.names)), seconds=3.5)
        elif event == "info":
            self.show_activity("network-vpn-symbolic", self._vpn_text(), seconds=5)
        else:
            self.show_activity("network-vpn-symbolic", _("VPN getrennt"), seconds=3)
        self._fill_header_live()

    def _on_downloads(self):
        active = self.downloads.active
        if active and not self._downloads_seen and not self._download_hint_id:
            self._download_hint_id = GLib.timeout_add(DOWNLOAD_HINT_MS, self._download_hint)
        self._downloads_seen = active
        self._update_live()

    def _download_hint(self):
        self._download_hint_id = 0
        items = list(self.downloads.items.values())
        if items:
            text = _("Download · {name}").format(name=items[0].name)
            if len(items) > 1:
                text += f" +{len(items) - 1}"
            self.show_activity("folder-download-symbolic", text, seconds=2.5, on_click=self.open_downloads)
        return GLib.SOURCE_REMOVE

    def _on_download_done(self, path):
        self.show_activity("folder-download-symbolic", _("Download fertig · {name}").format(name=path.name),
                           seconds=5, on_click=lambda: self.reveal_file(path))

    def open_downloads(self):
        try:
            Gio.AppInfo.launch_default_for_uri(download_dir(self.config).as_uri(), None)
        except GLib.Error:
            pass

    def reveal_file(self, path):
        """Show the file selected in the file manager (Nemo), else open its folder."""
        path = Path(path)

        def open_folder():
            try:
                Gio.AppInfo.launch_default_for_uri(path.parent.as_uri(), self.launch_context())
            except GLib.Error:
                pass

        def done(bus, result):
            try:
                bus.call_finish(result)
            except GLib.Error:
                open_folder()

        try:
            bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        except GLib.Error:
            open_folder()
            return
        bus.call("org.freedesktop.FileManager1", "/org/freedesktop/FileManager1", "org.freedesktop.FileManager1",
                 "ShowItems", GLib.Variant("(ass)", ([path.as_uri()], "")), None, Gio.DBusCallFlags.NONE,
                 3000, None, done)

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

    # ---- screenshots ---------------------------------------------------------------
    def screenshot(self, mode):
        """Area or monitor under the pointer -> clipboard (+ pictures folder), without the island in it."""
        if mode not in ("area", "screen") or self._cancel_capture():
            return
        missing = screenshot.missing(mode)
        if missing:
            self.show_activity("dialog-warning-symbolic",
                               _("Für Screenshots fehlt: {programs}").format(programs=", ".join(missing)), seconds=5)
            return
        geometry = screenshot.pointer_monitor_geometry() if mode == "screen" else None
        path = screenshot.new_path(self.config)
        self._capture(screenshot.capture_argv(mode, geometry, path), lambda ok: self._on_shot(ok, path))

    def _cancel_capture(self):
        """The hotkey again during the selection: give up and bring the island back. True if one ran."""
        if not self._shooting:
            return False
        if self._shot_proc and self._shot_stop:
            self._shot_stop()
        return True

    def _capture(self, argv, on_done, stdout=False, record=False, chain=False):
        """Run argv (maim, slop or ffmpeg) with the island out of the picture, then on_done(ok).

        stdout: keep what it prints in self._shot_out (slop's area); record: ffmpeg, which ends on SIGINT
        so its file is finished; chain: after a success on_done starts the next capture at once and the
        island stays hidden in between (a recording after its area was chosen).
        """
        self._shooting = True
        self._capture_gen += 1
        self._drop_card()
        if self.expanded:
            self.collapse()
        # Fold at once (no animation while hidden), then step out of the picture
        self.anim.jump(self._collapsed_geometry())
        self._show_collapsed()
        self.hide()

        def finish(ok):
            self._shot_proc = self._shot_stop = None
            if record:
                self._set_recording(False)
            if chain and ok:
                gen = self._capture_gen
                on_done(ok)
                if gen == self._capture_gen:
                    self._end_capture()   # nothing followed: bring the island back
                return
            self._end_capture()
            on_done(ok)

        def done(proc, result):
            try:
                if stdout:
                    _ok, out, _err = proc.communicate_utf8_finish(result)
                    self._shot_out = (out or "").strip()
                    ok = proc.get_successful()
                else:
                    ok = proc.wait_check_finish(result)
            except GLib.Error:
                ok = False  # cancelled (Esc, or killed above)
            finish(ok)

        def shoot():
            try:
                if record:
                    proc = recorder.launcher().spawnv(argv)
                    self._shot_stop = lambda: proc.send_signal(signal.SIGINT)
                else:
                    flags = Gio.SubprocessFlags.STDERR_SILENCE | (
                        Gio.SubprocessFlags.STDOUT_PIPE if stdout else Gio.SubprocessFlags.STDOUT_SILENCE)
                    proc = Gio.Subprocess.new(argv, flags)
                    self._shot_stop = proc.force_exit
            except GLib.Error:
                finish(False)
                return GLib.SOURCE_REMOVE
            self._shot_proc = proc
            if record:
                self._set_recording(True)
            if stdout:
                proc.communicate_utf8_async(None, None, done)
            else:
                proc.wait_check_async(None, done)
            return GLib.SOURCE_REMOVE

        GLib.timeout_add(SHOT_HIDE_MS, shoot)

    def _end_capture(self):
        self._shooting = False
        self.show()
        self._place()

    def _on_shot(self, ok, path):
        if not ok or not path.is_file():
            path.unlink(missing_ok=True)
            return  # selection cancelled
        screenshot.copy(path)
        if self.config.get("screenshot_open_editor", False):
            self.open_editor(path)
        else:
            self.show_activity("camera-photo-symbolic", _("Screenshot kopiert · Klick = bearbeiten"), seconds=6,
                               on_click=lambda: self.open_editor(path))

    def open_editor(self, path):
        if not path.is_file():
            return
        from island.editor import Editor  # loaded on first use only

        def saved(_target):
            self.show_activity("document-save-symbolic", _("Gespeichert & kopiert"))

        Editor(path, self.config, application=self.get_application(), on_saved=saved,
               on_text=lambda text: self._on_text(text, None, copy=False)).present()

    # ---- text & QR codes from the screen ----------------------------------------------
    def read_screen(self, kind):
        """Pick an area and read its text ('text') or its QR codes ('qr') onto the clipboard."""
        if kind not in ("text", "qr") or self._cancel_capture():
            return
        missing = ocr.missing(kind)
        if missing:
            what = _("Texterkennung") if kind == "text" else _("QR-Codes")
            self.show_activity("dialog-warning-symbolic", _("Für {what} fehlt: {programs}").format(
                what=what, programs=", ".join(missing)), seconds=5)
            return
        path = ocr.temp_path()

        def captured(ok):
            if not ok or not path.is_file() or path.stat().st_size == 0:
                path.unlink(missing_ok=True)
                return  # selection cancelled
            if kind == "text":
                self.show_activity("edit-find-symbolic", _("Text wird erkannt …"), seconds=20)
                ocr.read_text(path, self.config, self._on_text, delete=True)
            else:
                ocr.read_codes(path, self._on_codes, delete=True)

        self._capture(screenshot.capture_argv("area", None, path), captured)

    # ---- screen recording --------------------------------------------------------------
    @property
    def recording(self):
        return self._recording

    def record(self, mode):
        """Record an area or the monitor under the pointer; the same hotkey again stops and saves it.

        The island stays out of the picture the whole time (hidden): the tray icon turns red and a click
        on it stops the recording, and notifications wait in Cinnamon's applet instead of popping up in it.
        """
        if mode not in ("area", "screen"):
            return
        if self._recording:
            self.stop_recording()
            return
        if self._cancel_capture():
            return    # the area selection is open: the hotkey again gives up
        missing = recorder.missing(mode)
        if missing:
            self.show_activity("dialog-warning-symbolic",
                               _("Für Aufnahmen fehlt: {programs}").format(programs=", ".join(missing)), seconds=5)
            return
        if mode == "screen":
            self._start_recording(recorder.usable(recorder.parse_geometry(screenshot.pointer_monitor_geometry())))
        else:
            self._capture(recorder.SELECT_ARGV, self._on_record_area, stdout=True, chain=True)

    def stop_recording(self):
        if self._recording and self._shot_proc and self._shot_stop:
            self._shot_stop()

    def _on_record_area(self, ok):
        geometry = recorder.parse_geometry(self._shot_out) if ok else None
        if geometry is None:
            return    # the selection was cancelled
        if recorder.usable(geometry) is None:
            self._end_capture()
            self.show_activity("dialog-warning-symbolic", _("Bereich zu klein"), seconds=3)
            return
        self._start_recording(recorder.usable(geometry))

    def _start_recording(self, geometry):
        path, final = recorder.new_paths(self.config)
        self._capture(recorder.record_argv(self.config, geometry, path), lambda _ok: self._on_recorded(path, final),
                      record=True)

    def _set_recording(self, on):
        self._recording = on
        self.tray.set_recording(on)

    def _on_recorded(self, path, final):
        if not recorder.good(path):
            path.unlink(missing_ok=True)
            error = recorder.last_error()
            self.show_activity("dialog-warning-symbolic", _("Aufnahme fehlgeschlagen") + (f": {error}" if error else ""),
                               seconds=7)
            return
        if path == final:
            self._recording_saved(final)
            return
        self.show_activity("camera-video-symbolic", _("GIF wird erstellt …"), seconds=600)
        recorder.convert_to_gif(path, final, lambda ok: self._on_gif(ok, final))

    def _on_gif(self, ok, final):
        self._clear_activity()
        if ok and recorder.good(final):
            self._recording_saved(final)
        else:
            error = recorder.last_error()
            self.show_activity("dialog-warning-symbolic", _("GIF-Erstellung fehlgeschlagen")
                               + (f": {error}" if error else ""), seconds=7)

    def _recording_saved(self, path):
        self.show_card("camera-video-symbolic", _("Aufnahme gespeichert"), path.name,
                       meta=human_size(path.stat().st_size),
                       actions=[(_("Abspielen"), lambda: self._open_link(path.as_uri()), True),
                                (_("Im Ordner zeigen"), lambda: self.reveal_file(path), False)])

    def _clear_activity(self):
        """Drop a running live activity (e.g. "recognising ...") without redrawing."""
        if self._activity_id:
            GLib.source_remove(self._activity_id)
            self._activity_id = 0
        self._activity = None

    def _on_text(self, text, error, copy=True):
        self._clear_activity()
        if error == "language":
            self.show_activity("dialog-warning-symbolic", _("Sprachdaten fehlen: {languages}").format(
                languages=self.config.get("ocr_languages", "deu+eng")), seconds=6)
            return
        if error:
            self.show_activity("dialog-warning-symbolic", _("Texterkennung fehlgeschlagen"), seconds=5)
            return
        if not text:
            self.show_activity("edit-find-symbolic", _("Kein Text gefunden"), seconds=3)
            return
        if copy:
            ocr.copy_text(text)
        self.show_card("edit-select-all-symbolic", _("Text erkannt · kopiert"), text,
                       meta=_("{n} Zeichen").format(n=len(text)),
                       actions=[(_("In Notiz"), lambda: self._to_note(text), False),
                                (_("Kopieren"), lambda: self._copy_again(text), True)])

    def _on_codes(self, codes, error):
        if error:
            self.show_activity("dialog-warning-symbolic", _("QR-Erkennung fehlgeschlagen"), seconds=5)
            return
        if not codes:
            self.show_activity("dialog-question-symbolic", _("Kein QR-Code gefunden"), seconds=3)
            return
        meta = n_("{n} Code", "{n} Codes", len(codes)).format(n=len(codes)) if len(codes) > 1 else ""
        kind, data = codes[0]
        wifi = ocr.parse_wifi(data) if len(codes) == 1 else None
        url = ocr.link(data) if len(codes) == 1 else None
        if wifi:
            ocr.copy_text(wifi["password"] or wifi["ssid"])
            title = (_("WLAN „{ssid}“ · Passwort kopiert") if wifi["password"]
                     else _("WLAN „{ssid}“ · Name kopiert")).format(ssid=wifi["ssid"])
            body = _("Passwort: {password}").format(password=wifi["password"]) if wifi["password"] \
                else _("Offenes Netz ohne Passwort")
            actions = [(_("Verbinden"), lambda: self._join_wifi(wifi), True)] if system.has("nmcli") else []
            self.show_card("network-wireless-symbolic", title, body, actions=actions)
            return
        text = "\n".join(d for _k, d in codes)
        ocr.copy_text(text)
        if url and self.config.get("qr_open_links", False):
            self._open_link(url)
            return
        actions = [(_("Öffnen"), lambda: self._open_link(url), True)] if url else \
            [(_("In Notiz"), lambda: self._to_note(text), False)]
        if url:
            title = _("Link kopiert")
        elif len(codes) == 1:
            title = _("{kind} · kopiert").format(kind=kind)  # QR-Code, EAN-13, ...
        else:
            title = _("Codes kopiert")
        qr_icon = "qrcode-symbolic" if Gtk.IconTheme.get_default().has_icon("qrcode-symbolic") else "view-grid-symbolic"
        self.show_card(qr_icon, title, text, meta=meta, actions=actions)

    def _copy_again(self, text):
        if ocr.copy_text(text):
            self.show_activity("edit-copy-symbolic", _("Kopiert"))

    def _to_note(self, text):
        self.pages["note"].page.append(text)
        self.show_activity("document-edit-symbolic", _("In Notiz eingefügt · Klick = öffnen"), seconds=4,
                           on_click=lambda: self.expand(tab="note"))

    def _open_link(self, url):
        try:
            Gio.AppInfo.launch_default_for_uri(url, None)
        except GLib.Error:
            self.show_activity("dialog-warning-symbolic", _("Link lässt sich nicht öffnen"), seconds=4)

    def _join_wifi(self, wifi):
        argv = ["nmcli", "device", "wifi", "connect", wifi["ssid"]]
        if wifi["password"]:
            argv += ["password", wifi["password"]]
        self.show_activity("network-wireless-acquiring-symbolic",
                           _("Verbinde mit {ssid} …").format(ssid=wifi["ssid"]), seconds=20)

        def done(ok, _out):
            # Success shows up by itself as "Connected · name" (network indicator)
            if ok:
                self._end_activity()
            else:
                self.show_activity("network-wireless-offline-symbolic", _("WLAN-Verbindung fehlgeschlagen"),
                                   seconds=5)

        system.run(argv, done)

    # ---- notifications: Cinnamon stays the server, the island listens in ------------------
    def _on_notification(self, n):
        name = n.name
        if name == "MosIsland":
            return  # the island shows its own events as live activities already
        if self.notifications.remember(name):
            self.tray.refresh_notifications()
        if self._shooting or self._notification_hidden(n):
            return
        critical = n.urgency == URGENCY_CRITICAL
        if self.config.get("notifications_dnd", False) and not critical:
            return  # "do not disturb": only Cinnamon's applet gets it
        card = self._card
        shown = card.get("notification") if card else None
        if card and shown is None:
            return  # a card the user asked for (text, QR) stays; the applet keeps the notification
        if shown is None:
            extra = 0
        elif n.replaces and n.replaces == shown.id:
            extra = card["extra"]  # the same notification, updated (e.g. a download's progress)
        else:
            extra = card["extra"] + 1  # newest wins, the counter says how many came before
        if n.body:
            title, body, meta = n.summary or name, n.body, [name] if n.summary else []
        else:
            title, body, meta = name or n.summary, n.summary if name else "", []
        if extra:
            meta.append(f"+{extra}")
        if critical:
            ms = None
        elif n.timeout > 0:
            ms = min(max(n.timeout, NOTIFY_MIN_MS), NOTIFY_MAX_MS)
        else:
            ms = NOTIFY_MS
        tools = [("notifications-disabled-symbolic", _("Benachrichtigungen von {app} ausblenden").format(app=name),
                  lambda: self._hide_app(name))] if name else []
        self.show_card(self._notification_icon(n), title, body, meta=" · ".join(meta), image=n.image,
                       on_click=lambda: self._open_notification(n), tools=tools, ms=ms,
                       notification=n, extra=extra)

    def _on_notification_closed(self, notification_id):
        """The app withdrew it (e.g. the message was read elsewhere)."""
        shown = self._card.get("notification") if self._card else None
        if shown is not None and shown.id == notification_id:
            self.dismiss_card()

    def _notification_hidden(self, n):
        hidden = {h.lower() for h in self.config.get("notifications_exclude") or [] if isinstance(h, str)}
        return bool(hidden & {x.lower() for x in (n.name, n.app, n.entry) if x})

    @staticmethod
    def _notification_icon(n):
        theme = Gtk.IconTheme.get_default()
        if n.icon and not n.icon.startswith(("/", "file://")) and theme.has_icon(n.icon):
            return n.icon
        info = desktop_info(n.entry) or desktop_info(n.app.lower())
        if info and info.get_icon():
            return info.get_icon()
        if n.app and theme.has_icon(n.app.lower()):
            return n.app.lower()
        return "preferences-system-notifications-symbolic" \
            if theme.has_icon("preferences-system-notifications-symbolic") else "dialog-information-symbolic"

    def _open_notification(self, n):
        """Bring the sending app to the front.

        The app's own click action can't be triggered: only Cinnamon, the server, may send ActionInvoked.
        """
        window = self._find_app_window(n)
        if window is not None:
            now = self._server_time()
            workspace = window.get_workspace()
            if workspace is not None and workspace != self._wnck.get_active_workspace():
                workspace.activate(now)
            window.activate(now)
            return
        info = desktop_info(n.entry) or desktop_info(n.app.lower())
        if info:
            try:
                info.launch([], Gdk.Display.get_default().get_app_launch_context())
            except GLib.Error:
                pass

    def _find_app_window(self, n):
        if not self._wnck:
            return None
        windows = [w for w in reversed(self._wnck.get_windows_stacked())
                   if w.get_window_type() == Wnck.WindowType.NORMAL]
        if n.pid:
            for window in windows:
                if window.get_pid() == n.pid:
                    return window
        # desktop-entry "org.telegram.desktop" vs. WM_CLASS "telegram-desktop": try the last part too
        names = {x.lower() for x in (n.entry, n.app) if x}
        names |= {x.rsplit(".", 1)[-1] for x in names}
        for window in windows:
            classes = {(window.get_class_group_name() or "").lower(), (window.get_class_instance_name() or "").lower()}
            if classes & names:
                return window
        return None

    def _hide_app(self, name):
        self.set_app_hidden(name, True)
        self.show_activity("notifications-disabled-symbolic",
                           _("{app} ausgeblendet · Tray → Benachrichtigungen").format(app=name), seconds=4)

    def notification_apps(self):
        """[(name, hidden)] for the tray: apps seen recently, then hidden ones not seen lately."""
        hidden = [h for h in self.config.get("notifications_exclude") or [] if isinstance(h, str)]
        names = {}
        for name in self.notifications.apps + hidden:
            names.setdefault(name.lower(), name)
        lower_hidden = {h.lower() for h in hidden}
        return [(name, key in lower_hidden) for key, name in names.items()]

    def set_app_hidden(self, name, hidden):
        keep = [h for h in self.config.get("notifications_exclude") or []
                if isinstance(h, str) and h.lower() != name.lower()]
        self.set_option("notifications_exclude", keep + [name] if hidden else keep)
        self.tray.refresh_notifications()

    def dnd_get(self):
        if self.config.get("notifications_on_island", True):
            return self.config.get("notifications_dnd", False)
        return system.dnd_get()

    def dnd_set(self, enabled):
        """Do not disturb: the island's own while it shows the cards, else Cinnamon's."""
        if self.config.get("notifications_on_island", True):
            self.config["notifications_dnd"] = bool(enabled)
            self.config.save()
            shown = self._card.get("notification") if self._card else None
            if enabled and shown is not None and shown.urgency != URGENCY_CRITICAL:
                self.dismiss_card()
        else:
            system.dnd_set(enabled)
        self.tray.refresh_notifications()

    def _set_notification_cards(self, on):
        if on:
            self._hide_banners()
            self.notifications.start()
        else:
            self.notifications.stop()
            self.restore_banners()
            if self._card and self._card.get("notification") is not None:
                self._drop_card()
        self.tray.refresh_notifications()

    def _hide_banners(self):
        """Cards on: Cinnamon files notifications straight into its applet, without banners."""
        settings = self._banner_settings
        if settings is None:
            return
        if not settings.get_boolean(BANNERS[1]) and not self.notifications.banners_hidden:
            # Cinnamon's "do not disturb" was on: the island's takes over
            self.config["notifications_dnd"] = True
            self.config.save()
        self.notifications.set_banners_hidden(True)  # on disk first: after a crash we still know it was us
        settings.set_boolean(BANNERS[1], False)

    def restore_banners(self):
        """Cards off or island quits: Cinnamon's banners come back ("do not disturb" carries over)."""
        settings = self._banner_settings
        if settings is None or not self.notifications.banners_hidden:
            return
        self.notifications.set_banners_hidden(False)  # first, so _on_banners_changed lets the write be
        settings.set_boolean(BANNERS[1], not self.config.get("notifications_dnd", False))
        Gio.Settings.sync()

    def _on_banners_changed(self, settings, key):
        if self.notifications.banners_hidden and settings.get_boolean(key):
            # Switched on elsewhere (Cinnamon's settings) = "do not disturb" off; the island keeps showing them
            self.config["notifications_dnd"] = False
            self.config.save()
            settings.set_boolean(key, False)
        self.tray.refresh_notifications()

    def shutdown(self):
        if note := self._built("note"):
            note.flush()
        self.notifications.stop()
        self.restore_banners()

    # ---- options (tray, checkboxes) ----------------------------------------------
    def set_option(self, key, value):
        self.config[key] = value
        self.config.save()
        if key == "lyrics_in_pill":
            self._update_lyrics_track()
        elif key == "clipboard_autodelete_min":
            self.clipboard.set_autodelete(value)
        elif key == "notifications_on_island":
            self._set_notification_cards(value)
        elif key in LIVE_SWITCHES:
            self._apply_live_switches()
        elif key == "monitor":
            self._place()
        elif key == "mascot_style":
            self.eyes.set_figure(value)
        elif key == "ai_chat":
            self._apply_ai_tab()
        elif key == "ai_voice" and (page := self._built("chat")):
            page.refresh()
        elif key == "vpn_lookup" and value:
            self.vpn.refresh_info()
        elif key.startswith("command_bar_") and (page := self._built("search")):
            page.refresh()
        self.refresh_collapsed()

    def set_language(self, choice):
        """auto | de | en. A different UI language needs a fresh start (no live relabelling)."""
        changed = i18n.resolve(choice) != i18n.current()
        self.config["language"] = choice
        self.config.save()
        if changed:
            self.get_application().restart()

    # ---- AI: chat and dictation (own API key, see services/chat.py) ---------------------
    def _apply_ai_tab(self):
        on = self.config.get("ai_chat", False)
        self.tab_buttons["chat"].set_visible(on)
        if not on and self._current_tab == "chat":
            self.select_tab("home")

    def _ai_hint(self, text):
        self.show_activity("dialog-information-symbolic", text, seconds=4)

    def open_chat(self):
        """Hotkey: the chat tab (closes the island if it already shows it)."""
        if not self.config.get("ai_chat", False):
            self._ai_hint(_("KI-Chat ist aus · Tray-Menü › KI"))
            return
        self.open_tab("chat")

    def ai_settings(self):
        from island import aidialog  # loaded on first use only
        aidialog.show(self)

    def apply_ai_settings(self, url, model, stt_model, key):
        """The dialog's "Save": address and models into config.json, a typed key into the keyring."""
        url = url.strip().rstrip("/")
        if url and not url.startswith(("http://", "https://")):
            self.show_activity("dialog-warning-symbolic", _("Adresse muss mit http:// oder https:// beginnen"),
                               seconds=5)
            url = ""
        self.config.update(ai_base_url=url, ai_model=model.strip(), ai_stt_model=stt_model.strip())
        self.config.save()
        key = key.strip()
        if key:
            from island.services import keyring
            keyring.store(key, self._on_key_saved)
        else:
            self.ai_changed()

    def _on_key_saved(self, ok):
        if ok:
            self.show_activity("dialog-password-symbolic", _("API-Key im Schlüsselbund gespeichert"), seconds=3)
        else:
            self.show_activity("dialog-warning-symbolic", _("Key nicht gespeichert: Schlüsselbund nicht erreichbar "
                                                           "(libsecret-tools?)"), seconds=7)
        self.ai_changed()

    def remove_ai_key(self):
        from island.services import keyring
        keyring.clear(lambda ok: (self.show_activity("dialog-password-symbolic", _("API-Key entfernt"), seconds=3)
                                  if ok else self.show_activity("dialog-warning-symbolic",
                                                                _("Key nicht entfernt"), seconds=4),
                                  self.ai_changed()))

    def ai_changed(self):
        """Server, model or key changed: the chat page shows where its questions go."""
        if page := self._built("chat"):
            page.refresh()

    def voice(self):
        """Dictation: the first call records the microphone, the next one ends it and writes down what was said."""
        if self._dictation is not None:
            self._dictation.send_signal(signal.SIGINT)
            return
        if self._transcribing:
            return
        if not self.config.get("ai_voice", False):
            self._ai_hint(_("Diktat ist aus · Tray-Menü › KI"))
            return
        from island.services import dictation
        missing = dictation.missing()
        if missing:
            self.show_activity("dialog-warning-symbolic",
                               _("Für das Diktat fehlt: {programs}").format(programs=", ".join(missing)), seconds=5)
            return
        self._remember_active_window()    # the window the text goes to
        try:
            proc = recorder.launcher(dictation.LOG).spawnv(dictation.record_argv(self.config))
        except GLib.Error:
            self.show_activity("dialog-warning-symbolic", _("Diktat lässt sich nicht starten"), seconds=5)
            return
        self._dictation = proc
        self.show_activity("audio-input-microphone-symbolic", _("Diktat · sprich jetzt, Ctrl+Alt+M beendet"),
                           sticky=True, on_click=self.voice)
        proc.wait_check_async(None, self._on_dictation_recorded)

    def _on_dictation_recorded(self, proc, result):
        from island.services import dictation, keyring
        try:
            proc.wait_check_finish(result)
        except GLib.Error:
            pass    # ffmpeg exits non-zero after the SIGINT that ends it: the file decides
        self._dictation = None
        self._clear_activity()
        try:
            size = dictation.WAV.stat().st_size
        except OSError:
            size = 0
        if size < dictation.MIN_BYTES:
            dictation.WAV.unlink(missing_ok=True)
            error = recorder.last_error(dictation.LOG) if not size else ""
            self.show_activity("dialog-warning-symbolic", error or _("Zu kurz, nichts aufgenommen"), seconds=4)
            return
        self.show_activity("audio-input-microphone-symbolic", _("Wird aufgeschrieben …"), seconds=120)
        self._transcribing = True
        keyring.lookup(self._transcribe)

    def _transcribe(self, key):
        from island.services import chat, dictation
        if not key and not chat.is_local(self.config):
            self._transcribed("", ("nokey", 0, ""))
            return
        chat.transcribe(self.config, key, dictation.WAV, self._transcribed)

    def _transcribed(self, text, error):
        from island.services import chat, dictation
        dictation.WAV.unlink(missing_ok=True)    # the recording is not kept
        self._transcribing = False
        self._clear_activity()
        if error:
            message = (_("Kein API-Key gespeichert · Tray-Menü › KI › Verbindung") if error[0] == "nokey"
                       else chat.describe(error))
            self.show_activity("dialog-warning-symbolic", message, seconds=7)
        elif not text:
            self.show_activity("audio-input-microphone-symbolic", _("Nichts verstanden"), seconds=3)
        else:
            self._deliver_dictation(text)

    def _deliver_dictation(self, text):
        """The chat's question field if the chat is open, else typed into the window the user came from."""
        page = self._built("chat")
        if self.expanded and self._current_tab == "chat" and page:
            page.insert_text(text)
            return
        if not ocr.copy_text(text):
            return
        if self.config.get("ai_voice_autopaste", True) and self._prev_window is not None and system.has("xdotool"):
            self.show_activity("audio-input-microphone-symbolic", _("Diktat eingefügt"), seconds=2)
            self._paste_into_previous()
            return
        self.show_card("audio-input-microphone-symbolic", _("Diktat · kopiert"), text,
                       meta=_("{n} Zeichen").format(n=len(text)),
                       actions=[(_("Einfügen"), self._paste_into_previous, True),
                                (_("In Notiz"), lambda: self._to_note(text), False)])

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
            self.pages["home"].set_lyrics([], _("Lade Lyrics …"))
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
                                          _("Nur unsynchronisierte Lyrics verfügbar"))
            self._lyrics_lines = []
        else:
            self.pages["home"].set_lyrics([], _("Keine Lyrics gefunden") if plain is not None
                                          else _("Lyrics gerade nicht erreichbar (offline?)"))
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


def _command_page(island):
    from island.commandbar import CommandPage  # loaded on first use only
    return CommandPage(island)


def _chat_page(island):
    from island.chatpage import ChatPage  # loaded on first use only
    return ChatPage(island)


class IslandApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.window = None
        self.restart_requested = False

    def restart(self):
        """Quit and start again (main() re-executes the process after the clean shutdown)."""
        self.restart_requested = True
        self.quit()

    def do_startup(self):
        Gtk.Application.do_startup(self)
        # Actions are reachable via D-Bus, so hotkeys don't need a Python start-up:
        #   gdbus call ... --method org.gtk.Actions.Activate toggle [] {}
        def hotkey(name, param_type, handler):
            """Action that runs handler(window, param) – on the monitor under the mouse in pointer mode."""
            action = Gio.SimpleAction.new(name, param_type and GLib.VariantType(param_type))

            def activate(_action, param):
                if self.window:
                    self.window.follow_pointer()
                    handler(self.window, param.unpack() if param is not None else None)

            action.connect("activate", activate)
            return action

        toggle = hotkey("toggle", None, lambda win, _p: win.toggle(focus=True))
        tab = hotkey("tab", "s", lambda win, name: win.open_tab(name))
        shot = hotkey("screenshot", "s", lambda win, mode: win.screenshot(mode))
        read_text = hotkey("ocr", None, lambda win, _p: win.read_screen("text"))
        read_qr = hotkey("qr", None, lambda win, _p: win.read_screen("qr"))
        record = hotkey("record", "s", lambda win, mode: win.record(mode))
        chat_tab = hotkey("chat", None, lambda win, _p: win.open_chat())
        voice = hotkey("voice", None, lambda win, _p: win.voice())
        quit_action = Gio.SimpleAction.new("quit", None)
        quit_action.connect("activate", lambda *_: self.quit())
        for action in (toggle, tab, shot, read_text, read_qr, record, chat_tab, voice, quit_action):
            self.add_action(action)

    def do_activate(self):
        if self.window is None:
            self.window = IslandWindow(self)
            self.window.show_all()
        else:
            # A second start (e.g. from the menu) toggles the running island
            self.window.follow_pointer()
            self.window.toggle(focus=True)

    def do_shutdown(self):
        if self.window:
            self.window.shutdown()
        Gtk.Application.do_shutdown(self)


def _set_process_name(name=b"linuxmos-island"):
    """Show up as 'linuxmos-island' in top/htop instead of 'python3'."""
    try:
        ctypes.CDLL("libc.so.6").prctl(15, ctypes.c_char_p(name), 0, 0, 0)  # PR_SET_NAME
    except (OSError, AttributeError):
        pass


def _trim_memory():
    """Collect Python's reference cycles (dropped widgets), then return glibc's free heap pages to the system."""
    gc.collect()
    try:
        ctypes.CDLL("libc.so.6").malloc_trim(0)
    except (OSError, AttributeError):
        pass


def _set_key():
    """linuxmos-island --set-key: put the AI API key into the keyring (typed invisibly, or piped in)."""
    import getpass
    from island.services import keyring
    i18n.setup(Config.load().get("language", "auto"))
    if not keyring.available():
        print(_("secret-tool fehlt: sudo apt install libsecret-tools"), file=sys.stderr)
        return 1
    key = (getpass.getpass(_("API-Key (die Eingabe bleibt unsichtbar): ")) if sys.stdin.isatty()
           else sys.stdin.readline()).strip()
    if not key:
        print(_("Kein Key eingegeben."), file=sys.stderr)
        return 2
    if not keyring.store_sync(key):
        print(_("Der Schlüsselbund hat den Key nicht angenommen (läuft gnome-keyring?)."), file=sys.stderr)
        return 1
    print(_("API-Key im Schlüsselbund gespeichert."))
    return 0


def main(argv=None):
    argv = list(sys.argv if argv is None else argv)
    if "--version" in argv:
        print(f"MosIsland {__version__}")
        return 0
    if "--set-city" in argv:
        i = argv.index("--set-city")
        if i + 1 >= len(argv):
            print("Usage: linuxmos-island --set-city CITY", file=sys.stderr)
            return 2
        cfg = Config.load()
        cfg.update(city=argv[i + 1].strip(), latitude=None, longitude=None)
        cfg.save()
        i18n.setup(cfg.get("language", "auto"))
        print(_("Wetter-Ort gesetzt: {city}").format(city=cfg["city"]))
        return 0

    if "--set-key" in argv:
        return _set_key()

    _set_process_name()
    app = IslandApp()
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGTERM, lambda: app.quit() or GLib.SOURCE_REMOVE)
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGINT, lambda: app.quit() or GLib.SOURCE_REMOVE)
    status = app.run(argv[:1])
    if app.restart_requested:
        # Drop the bus connection first so the new process can take over the app ID at once
        try:
            Gio.bus_get_sync(Gio.BusType.SESSION, None).close_sync(None)
        except GLib.Error:
            pass
        os.execv(sys.executable, [sys.executable, "-m", "island"])
    return status
