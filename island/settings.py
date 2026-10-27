"""linuxmos-island-settings: the settings & overview window. Its own process: it starts when it is opened and is
gone when it is closed, so it costs nothing while you don't use it.

    Übersicht   every function with its hotkey, a switch and its status; a click on a name runs it, a click on the
                hotkey changes it; what is running now; gestures and tray at a glance
    Gesten      the mouse gestures on the pill and what each one does
    Funktionen  every setting of the config with an input that checks the value

It asks the running island (over the session bus, see control.py) for the register and the status, and runs
functions through it. Settings are written to config.json, which the island reloads by itself. If the island is
not running the window still works: the config can be changed, the status is empty.

Logic is in settingslogic.py; this file only draws.
"""

import logging
import sys
from pathlib import Path

import gi

from island import without_gl

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
with without_gl():
    from gi.repository import Gdk, Gio, GLib, Gtk

from island import hotkeys  # noqa: E402
from island.control import Control, ControlError  # noqa: E402
from island.settingslogic import Store  # noqa: E402
from island.settingsui import banner, clear, css_class, label, open_file  # noqa: E402
from island.storage import CONFIG_DIR, Config, load_json, save_json  # noqa: E402

log = logging.getLogger("mosisland.settings")

APP_ID = "org.linuxmos.IslandSettings"
TABS = (("overview", "Übersicht", "view-list-symbolic"), ("gestures", "Gesten", "input-mouse-symbolic"),
        ("functions", "Funktionen", "preferences-system-symbolic"))
GEOMETRY_FILE = CONFIG_DIR / "settings-window.json"
HIDE_MS = 350              # the window must be gone from the screen before a screen grab starts
GRAB_TIMEOUT_S = 120       # a screen grab that never reports back: the window returns anyway
EDIT_MODS = Gdk.ModifierType.CONTROL_MASK | Gdk.ModifierType.MOD1_MASK | Gdk.ModifierType.SUPER_MASK \
    | Gdk.ModifierType.SHIFT_MASK | Gdk.ModifierType.META_MASK | Gdk.ModifierType.HYPER_MASK
MODIFIER_KEYS = {Gdk.KEY_Control_L, Gdk.KEY_Control_R, Gdk.KEY_Alt_L, Gdk.KEY_Alt_R, Gdk.KEY_Shift_L, Gdk.KEY_Shift_R,
                 Gdk.KEY_Super_L, Gdk.KEY_Super_R, Gdk.KEY_Meta_L, Gdk.KEY_Meta_R, Gdk.KEY_ISO_Level3_Shift,
                 Gdk.KEY_Hyper_L, Gdk.KEY_Hyper_R, Gdk.KEY_Caps_Lock, Gdk.KEY_Num_Lock}


# ---- the window ----------------------------------------------------------------------------------------------------
class SettingsWindow(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="MosIsland – Einstellungen & Übersicht")
        self.set_name("island")
        self.store = Store()
        self.control = Control()
        self.island_up = self.control.running()
        self._finished_sub = 0
        self._grab_timeout = 0
        self._editing = None                      # the overview's hotkey editor that is capturing keys
        self._seat = None

        geometry = load_json(GEOMETRY_FILE, {})
        w, h = (geometry.get("w", 920), geometry.get("h", 680)) if isinstance(geometry, dict) else (920, 680)
        self.set_default_size(max(640, int(w)), max(420, int(h)))
        if isinstance(geometry, dict) and "x" in geometry and "y" in geometry:
            self.move(int(geometry["x"]), int(geometry["y"]))

        self.sidebar = Gtk.ListBox(selection_mode=Gtk.SelectionMode.BROWSE)
        css_class(self.sidebar, "sidebar")
        for name, text, icon_name in TABS:
            row = Gtk.ListBoxRow()
            row.name = name
            row.set_can_focus(False)
            box = Gtk.Box(spacing=10)
            box.pack_start(Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.MENU), False, False, 0)
            box.pack_start(label(text), True, True, 0)
            row.add(box)
            self.sidebar.add(row)
        self.sidebar.connect("row-selected", self._on_sidebar)
        side = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        css_class(side, "sidebar")
        side.set_size_request(190, -1)
        side.pack_start(label("MosIsland", ("section-title",)), False, False, 14)
        side.pack_start(self.sidebar, False, False, 0)
        side.pack_end(label(f"Version {self._version()}", ("dim", "small")), False, False, 12)
        self.config_link = Gtk.LinkButton.new_with_label("", "Config als Datei öffnen")
        self.config_link.connect("activate-link", lambda *_: self._open_config() or True)
        side.pack_end(self.config_link, False, False, 0)

        self.banners = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.CROSSFADE, transition_duration=120)
        from island.settingspages import FunctionsPage, GesturesPage, OverviewPage
        self.pages = {"overview": OverviewPage(self), "gestures": GesturesPage(self),
                      "functions": FunctionsPage(self)}
        for name, page in self.pages.items():
            self.stack.add_named(page, name)
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8, margin=18)
        content.pack_start(self.banners, False, False, 0)
        content.pack_start(self.stack, True, True, 0)

        root = Gtk.Box()
        root.pack_start(side, False, False, 0)
        root.pack_start(content, True, True, 0)
        self.add(root)
        self.connect("key-press-event", self._on_key)
        self.connect("delete-event", self._on_close)
        self.show_all()
        self.refresh_banners()
        self.show_tab("overview")

    @staticmethod
    def _version():
        from island import __version__
        return __version__

    # ---- tabs and banners -------------------------------------------------------------------------------------------
    def show_tab(self, name):
        if name not in self.pages:
            name = "overview"
        for row in self.sidebar.get_children():
            if row.name == name:
                self.sidebar.select_row(row)
        self.stack.set_visible_child_name(name)
        self.pages[name].on_show()

    def _on_sidebar(self, _box, row):
        if row is not None:
            self.show_tab(row.name)

    def refresh_banners(self):
        clear(self.banners)
        if self.store.error:
            self.banners.pack_start(banner(f"Die Config-Datei ist ungültig ({self.store.error}) – es wird nichts "
                                           "gespeichert, bis sie wieder stimmt. „Config als Datei öffnen“ hilft.",
                                           error=True), False, False, 0)
        if not self.island_up:
            self.banners.pack_start(banner("MosIsland läuft nicht. Du siehst nur die Config; Status und Starten "
                                           "gehen erst, wenn die Insel läuft. Änderungen gelten beim nächsten Start."),
                                    False, False, 0)
        self.banners.show_all()

    def notice(self, text, error=False):
        """A message at the top that stays until the next one (validation errors, results)."""
        self.refresh_banners()
        if text:
            self.banners.pack_start(banner(text, error=error), False, False, 0)
            self.banners.show_all()

    def _open_config(self):
        self.store.config.fill_defaults()
        if not open_file(Config.PATH):
            self.notice(f"Kein Editor gefunden · Datei: {Config.PATH}", error=True)

    # ---- the island ---------------------------------------------------------------------------------------------------
    def island_registry(self):
        """The register: names, switches and hotkeys from our own fresh read of the config and Cinnamon (the
        island learns of a change a moment later), and the live status from the island if there is one."""
        entries = None
        try:
            keys = hotkeys.CinnamonKeys()
            entries = keys.entries() if keys.available else None
        except Exception:               # no gsettings: the config and the defaults are what we know
            pass
        rows = self.store.registry.rows(self.store.config, entries)
        self.island_up = self.control.running()
        if self.island_up:
            try:
                live = {row["id"]: row for row in self.control.registry()}
            except ControlError as error:
                log.warning("island did not answer: %s", error)
                self.island_up = False
                live = {}
            for row in rows:
                if row["id"] in live:
                    row["running"], row["status"] = live[row["id"]]["running"], live[row["id"]]["status"]
        return rows

    def island_status(self):
        if not self.island_up:
            return None
        try:
            return self.control.status()
        except ControlError:
            return None

    def run_function(self, row):
        """Run a function in the island. Screen grabs: this window steps aside first and comes back when the island
        reports the grab is over."""
        if not self.island_up:
            self.notice("MosIsland läuft nicht – gestartet wird dort nichts.", error=True)
            return
        if row["hide_window_first"]:
            self.hide()
            self._finished_sub = self.control.on_finished(self._on_action_finished)
            self._grab_timeout = GLib.timeout_add_seconds(GRAB_TIMEOUT_S, self._come_back)
            GLib.timeout_add(HIDE_MS, self._run_hidden, row["id"])
        else:
            self._run_now(row["id"])

    def _run_now(self, fid):
        try:
            ok, message, _busy = self.control.run(fid)
        except ControlError as error:
            self.notice(f"Die Insel antwortet nicht: {error}", error=True)
            return
        if not ok:
            self.notice(message or "Das hat nicht geklappt", error=True)

    def _run_hidden(self, fid):
        try:
            ok, _message, busy = self.control.run(fid)
        except ControlError:
            ok, busy = False, False
        if not ok or not busy:       # nothing is being grabbed (an error card or an instant action): come back
            self._come_back()
        return GLib.SOURCE_REMOVE

    def _on_action_finished(self):
        GLib.timeout_add(250, self._come_back)

    def _come_back(self):
        if self._finished_sub:
            self.control.unsubscribe(self._finished_sub)
            self._finished_sub = 0
        if self._grab_timeout:
            GLib.source_remove(self._grab_timeout)
            self._grab_timeout = 0
        self.present()
        return GLib.SOURCE_REMOVE

    # ---- capturing a hotkey ----------------------------------------------------------------------------------------------
    def start_capture(self, editor):
        """Route the next key press to `editor` (a grab, so Cinnamon's own shortcuts don't swallow it)."""
        self.stop_capture()
        self._editing = editor
        seat = Gdk.Display.get_default().get_default_seat()
        status = seat.grab(self.get_window(), Gdk.SeatCapabilities.KEYBOARD, False, None, None, None)
        if status == Gdk.GrabStatus.SUCCESS:
            self._seat = seat

    def stop_capture(self):
        if self._seat is not None:
            self._seat.ungrab()
            self._seat = None
        self._editing = None

    def _on_key(self, _w, event):
        editor = self._editing
        if editor is None:
            return False
        if event.keyval == Gdk.KEY_Escape:
            editor.cancel()
            return True
        if event.keyval in MODIFIER_KEYS:
            return True
        keymap = Gdk.Keymap.get_for_display(Gdk.Display.get_default())
        found, keyval, _eff, _group, _consumed = keymap.translate_keyboard_state(
            event.hardware_keycode, Gdk.ModifierType(0), event.group)
        if not found:
            keyval = event.keyval
        state = int(event.state & EDIT_MODS)
        name = Gtk.accelerator_name(Gdk.keyval_to_lower(keyval), Gdk.ModifierType(state))
        editor.captured(hotkeys.normalize(name), name)
        return True

    # ---- closing ---------------------------------------------------------------------------------------------------------
    def _on_close(self, *_):
        self.stop_capture()
        if self._finished_sub:
            self.control.unsubscribe(self._finished_sub)
        x, y = self.get_position()
        w, h = self.get_size()
        try:
            save_json(GEOMETRY_FILE, {"w": w, "h": h, "x": x, "y": y})
        except OSError:
            pass
        return False


class SettingsApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE)
        self.window = None

    def do_startup(self):
        Gtk.Application.do_startup(self)
        screen = Gdk.Screen.get_default()
        for name in ("style.css", "settings.css"):
            provider = Gtk.CssProvider()
            provider.load_from_path(str(Path(__file__).with_name(name)))
            Gtk.StyleContext.add_provider_for_screen(screen, provider, Gtk.STYLE_PROVIDER_PRIORITY_USER + 1)

    def do_command_line(self, command_line):
        argv = command_line.get_arguments()[1:]
        tab = "overview"
        if "--tab" in argv and argv.index("--tab") + 1 < len(argv):
            tab = argv[argv.index("--tab") + 1]
        if self.window is None:
            self.window = SettingsWindow(self)
        self.window.show_tab(tab)
        self.window.present()
        return 0


def main(argv=None):
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s: %(message)s", datefmt="%H:%M:%S")
    return SettingsApp().run(sys.argv if argv is None else argv)


if __name__ == "__main__":
    sys.exit(main())
