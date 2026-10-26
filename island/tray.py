"""Tray icon (XApp status icon, shown by Cinnamon's panel) with the island's switches."""

import shutil
from pathlib import Path

import gi
from gi.repository import GLib, Gtk

from island import __version__
from island import mascots
from island.i18n import LANGUAGES, _
from island.services import finder, monitors, recorder, screenshot, system

try:
    gi.require_version("XApp", "1.0")
    from gi.repository import XApp
except (ValueError, ImportError):
    XApp = None

AUTOSTART = Path.home() / ".config" / "autostart" / "linuxmos-island.desktop"

# Clipboard auto-delete choices in the tray (minutes, 0 = off); other values via config.json.
# Labels are German source strings, translated when the menu is built.
# Tray icon: normal, and while a screen recording runs (a click on it stops the recording)
ICON, RECORDING_ICON = "view-app-grid-symbolic", "media-record"

AUTODELETE_CHOICES = [(0, "Nie"), (15, "Nach 15 Minuten"), (60, "Nach 1 Stunde"), (1440, "Nach 24 Stunden")]


def _launcher():
    return shutil.which("linuxmos-island") or str(Path.home() / ".local" / "bin" / "linuxmos-island")


class Tray:
    def __init__(self, island):
        self.island = island
        self.icon = None
        self._notify_menu = None
        self._notify_refresh_id = 0
        self._monitor_menu = None
        self._record_stop = None
        self._checks = {}           # tray switches that other parts of the island can flip: key -> menu item
        self._syncing = False
        if XApp is None:
            return
        self.icon = XApp.StatusIcon()
        self.icon.set_name("linuxmos-island")
        self.icon.set_icon_name(ICON)
        self.icon.set_tooltip_text("MosIsland")
        self.icon.connect("activate", lambda *_: island.stop_recording() if island.recording
                          else self._open(island.toggle))
        self.icon.set_secondary_menu(self._build_menu())

    def _build_menu(self):
        cfg = self.island.config
        menu = Gtk.Menu()

        def item(label, callback):
            mi = Gtk.MenuItem(label=label)
            mi.connect("activate", lambda *_: callback())
            menu.append(mi)

        def check(label, active, callback):
            mi = Gtk.CheckMenuItem(label=label)
            mi.set_active(active)
            mi.connect("toggled", lambda w: callback(w.get_active()))
            menu.append(mi)

        item(_("MosIsland öffnen"), lambda: self._open(self.island.expand))
        menu.append(Gtk.SeparatorMenuItem())
        check(_("Mit Cinnamon starten"), AUTOSTART.exists(), self._set_autostart)
        menu.append(self._mascot_menu(cfg))
        menu.append(self._stretch_menu(cfg))
        check(_("Minimal-Notch"), cfg.get("compact_when_idle", False),
              lambda on: self.island.set_option("compact_when_idle", on))
        check(_("Lautstärke & Helligkeit anzeigen"), cfg.get("osd", True), self._set_osd)
        menu.append(self._autodelete_menu(cfg.get("clipboard_autodelete_min", 0)))
        menu.append(self._search_menu(cfg))
        menu.append(self._screenshot_menu(cfg))
        menu.append(self._read_menu(cfg))
        menu.append(self._record_menu(cfg))
        menu.append(self._ai_menu(cfg))
        menu.append(self._notifications_menu())
        menu.append(self._live_menu(cfg))
        menu.append(self._monitors_menu())
        menu.append(self._language_menu(cfg.get("language", "auto")))
        menu.append(Gtk.SeparatorMenuItem())
        item("Einstellungen öffnen", self.island.open_settings)
        item(_("Über MosIsland"), self._about)
        item(_("Beenden"), lambda: self.island.get_application().quit())
        menu.show_all()
        return menu

    def rebuild(self):
        """config.json was edited: build the menu again so every switch shows what the file says."""
        if self.icon is not None:
            self.icon.set_secondary_menu(self._build_menu())

    def _flag(self, key, label, active, callback):
        """A check item whose state can also be set from outside (refresh_stretch): callback only for clicks."""
        mi = Gtk.CheckMenuItem(label=label)
        mi.set_active(active)
        mi.connect("toggled", lambda w: None if self._syncing else callback(w.get_active()))
        self._checks[key] = mi
        return mi

    def refresh_stretch(self):
        """The reminder was switched on or off elsewhere (card button, tab, edited file): tick the right boxes."""
        if not self._checks:
            return
        cfg = self.island.config
        values = {"stretch_enabled": cfg.flag("stretch_enabled"),
                  "stretch_today": cfg.get("stretch_off_date") == self.island.stretch.env.today(),
                  "eye_mode": cfg.flag("eye_mode")}
        self._syncing = True
        try:
            for key, value in values.items():
                if key in self._checks and self._checks[key].get_active() != value:
                    self._checks[key].set_active(value)
        finally:
            self._syncing = False

    def _open(self, action):
        """Open/toggle from the tray – in pointer mode on the monitor the tray was clicked on."""
        self.island.follow_pointer()
        action()

    @staticmethod
    def _radio_items(sub, choices, current, on_select):
        """One radio item per (value, label) in sub; on_select(value) for the newly chosen one."""
        group = None
        for value, text in choices:
            mi = Gtk.RadioMenuItem.new_with_label_from_widget(group, text)
            group = group or mi
            mi.set_active(value == current)
            # "toggled" also fires for the item that gets deselected
            mi.connect("toggled", lambda w, v=value: w.get_active() and on_select(v))
            sub.append(mi)

    @classmethod
    def _radio_menu(cls, label, choices, current, on_select):
        """Submenu with one radio item per (value, label)."""
        sub = Gtk.Menu()
        cls._radio_items(sub, choices, current, on_select)
        parent = Gtk.MenuItem(label=label)
        parent.set_submenu(sub)
        return parent

    def _autodelete_menu(self, current):
        choices = [(minutes, _(text)) for minutes, text in AUTODELETE_CHOICES]
        if current not in dict(choices):
            # custom value from config.json
            choices.append((current, _("Nach {minutes} Minuten").format(minutes=current)))
        return self._radio_menu(_("Zwischenablage automatisch leeren"), choices, current,
                                lambda minutes: self.island.set_option("clipboard_autodelete_min", minutes))

    def _mascot_menu(self, cfg):
        sub = Gtk.Menu()
        show = Gtk.CheckMenuItem(label=_("Anzeigen, wenn ich weg bin"))
        show.set_active(cfg.get("mascot", True))
        show.connect("toggled", lambda w: self.island.set_option("mascot", w.get_active()))
        sub.append(show)
        sub.append(self._flag("eye_mode", "Augen-Modus (groß im Leerlauf)", cfg.flag("eye_mode"),
                              lambda on: self.island.set_option("eye_mode", on)))
        sub.append(Gtk.SeparatorMenuItem())
        current = cfg.get("mascot_style", mascots.DEFAULT)
        self._radio_items(sub, [(key, _(name)) for key, name in mascots.STYLES.items()],
                          current if current in mascots.STYLES else mascots.DEFAULT,
                          lambda key: self.island.set_option("mascot_style", key))
        parent = Gtk.MenuItem(label=_("Maskottchen"))
        parent.set_submenu(sub)
        return parent

    def _stretch_menu(self, cfg):
        sub = Gtk.Menu()
        sub.append(self._flag("stretch_enabled", "Dehn-Erinnerung", cfg.flag("stretch_enabled"),
                              lambda on: self.island.set_option("stretch_enabled", on)))
        sub.append(self._flag("stretch_today", "Heute aus",
                              cfg.get("stretch_off_date") == self.island.stretch.env.today(),
                              self.island.stretch.on_today))
        sub.append(Gtk.SeparatorMenuItem())
        for text, callback in (("Jetzt dehnen", self.island.stretch.trigger_now),
                               ("Übungen bearbeiten …", self.island.open_exercises)):
            mi = Gtk.MenuItem(label=text)
            mi.connect("activate", lambda _w, cb=callback: cb())
            sub.append(mi)
        parent = Gtk.MenuItem(label="Dehnen")
        parent.set_submenu(sub)
        return parent

    def _search_menu(self, cfg):
        sub = Gtk.Menu()
        open_item = Gtk.MenuItem(label=_("Suche öffnen  (Ctrl+Alt+Space)"))
        open_item.connect("activate", lambda *_: self.island.open_tab("search"))
        sub.append(open_item)
        sub.append(Gtk.SeparatorMenuItem())
        for text, key in ((_("Dateien durchsuchen"), "command_bar_files"),
                          (_("Währungen (fragt frankfurter.dev)"), "command_bar_currency")):
            mi = Gtk.CheckMenuItem(label=text)
            mi.set_active(cfg.get(key, True))
            mi.connect("toggled", lambda w, k=key: self.island.set_option(k, w.get_active()))
            sub.append(mi)
        current = cfg.get("command_bar_engine") or "duckduckgo"
        choices = [(key, name) for key, (name, _url) in finder.ENGINES.items()]
        if current not in finder.ENGINES:
            choices.append((current, finder.engine(cfg)[0]))  # own URL from config.json
        sub.append(self._radio_menu(_("Websuche mit"), choices, current,
                                    lambda key: self.island.set_option("command_bar_engine", key)))
        parent = Gtk.MenuItem(label=_("Suche"))
        parent.set_submenu(sub)
        return parent

    def _screenshot_menu(self, cfg):
        sub = Gtk.Menu()
        for text, mode in ((_("Bereich aufnehmen  (Ctrl+Alt+S)"), "area"),
                           (_("Bildschirm aufnehmen  (Ctrl+Alt+Shift+S)"), "screen")):
            mi = Gtk.MenuItem(label=text)
            mi.connect("activate", lambda _w, m=mode: self.island.screenshot(m))
            sub.append(mi)
        sub.append(Gtk.SeparatorMenuItem())
        for text, key, default in ((_("Im Ordner speichern"), "screenshot_save", True),
                                   (_("Editor sofort öffnen"), "screenshot_open_editor", False)):
            mi = Gtk.CheckMenuItem(label=text)
            mi.set_active(cfg.get(key, default))
            mi.connect("toggled", lambda w, k=key: self.island.set_option(k, w.get_active()))
            sub.append(mi)
        folder = Gtk.MenuItem(label=_("Ordner öffnen"))
        folder.connect("activate", lambda *_: screenshot.open_folder(self.island.config))
        sub.append(folder)
        parent = Gtk.MenuItem(label="Screenshot")
        parent.set_submenu(sub)
        return parent

    def _record_menu(self, cfg):
        sub = Gtk.Menu()
        for text, mode in ((_("Bereich aufnehmen  (Ctrl+Alt+R)"), "area"),
                           (_("Bildschirm aufnehmen  (Ctrl+Alt+Shift+R)"), "screen")):
            mi = Gtk.MenuItem(label=text)
            mi.connect("activate", lambda _w, m=mode: self.island.record(m))
            sub.append(mi)
        self._record_stop = Gtk.MenuItem(label=_("Aufnahme beenden"))
        self._record_stop.set_sensitive(self.island.recording)
        self._record_stop.connect("activate", lambda *_: self.island.stop_recording())
        sub.append(self._record_stop)
        sub.append(Gtk.SeparatorMenuItem())
        sub.append(self._radio_menu(_("Format"), [("mp4", "MP4"), ("gif", "GIF")], recorder.fmt(cfg),
                                    lambda value: self.island.set_option("record_format", value)))
        sub.append(self._radio_menu(_("Ton (nur MP4)"), [("off", _("Ohne Ton")), ("system", _("Systemton")),
                                                         ("mic", _("Mikrofon"))],
                                    cfg.get("record_audio", "off") if cfg.get("record_audio", "off") in recorder.AUDIO
                                    else "off",
                                    lambda value: self.island.set_option("record_audio", value)))
        folder = Gtk.MenuItem(label=_("Ordner öffnen"))
        folder.connect("activate", lambda *_: recorder.open_folder(self.island.config))
        sub.append(folder)
        parent = Gtk.MenuItem(label=_("Bildschirmaufnahme"))
        parent.set_submenu(sub)
        return parent

    def _ai_menu(self, cfg):
        sub = Gtk.Menu()
        for text, key, default in ((_("Chat-Tab  (Ctrl+Alt+A)"), "ai_chat", False),
                                   (_("Diktat  (Ctrl+Alt+M)"), "ai_voice", False),
                                   (_("Diktat direkt einfügen"), "ai_voice_autopaste", True)):
            mi = Gtk.CheckMenuItem(label=text)
            mi.set_active(cfg.get(key, default))
            mi.connect("toggled", lambda w, k=key: self.island.set_option(k, w.get_active()))
            sub.append(mi)
        sub.append(Gtk.SeparatorMenuItem())
        for text, callback in ((_("Verbindung & API-Key …"), self.island.ai_settings),
                               (_("API-Key entfernen"), self.island.remove_ai_key)):
            mi = Gtk.MenuItem(label=text)
            mi.connect("activate", lambda _w, cb=callback: cb())
            sub.append(mi)
        parent = Gtk.MenuItem(label=_("KI"))
        parent.set_submenu(sub)
        return parent

    def set_recording(self, on):
        """A screen recording starts or ends: red icon (a click stops it) and the stop item."""
        if self._record_stop is not None:
            self._record_stop.set_sensitive(on)
        if self.icon is not None:
            self.icon.set_icon_name(RECORDING_ICON if on else ICON)
            self.icon.set_tooltip_text(_("MosIsland · Aufnahme läuft, ein Klick beendet sie") if on else "MosIsland")

    def _read_menu(self, cfg):
        sub = Gtk.Menu()
        for text, kind in ((_("Text erkennen  (Ctrl+Alt+O)"), "text"),
                           (_("QR-Code lesen  (Ctrl+Alt+Q)"), "qr")):
            mi = Gtk.MenuItem(label=text)
            mi.connect("activate", lambda _w, k=kind: self.island.read_screen(k))
            sub.append(mi)
        sub.append(Gtk.SeparatorMenuItem())
        for text, key in ((_("Zeilenumbrüche behalten"), "ocr_keep_linebreaks"),
                          (_("Links aus QR-Codes sofort öffnen"), "qr_open_links")):
            mi = Gtk.CheckMenuItem(label=text)
            mi.set_active(cfg.get(key, False))
            mi.connect("toggled", lambda w, k=key: self.island.set_option(k, w.get_active()))
            sub.append(mi)
        parent = Gtk.MenuItem(label=_("Text & QR"))
        parent.set_submenu(sub)
        return parent

    def _live_menu(self, cfg):
        sub = Gtk.Menu()
        for text, key, default in ((_("Mikrofon & Kamera"), "privacy_indicator", True),
                                   (_("VPN-Status"), "vpn_status", True),
                                   (_("VPN: Land & IP (fragt ipinfo.io)"), "vpn_lookup", False),
                                   (_("Download-Fortschritt"), "downloads_progress", True)):
            mi = Gtk.CheckMenuItem(label=text)
            mi.set_active(cfg.get(key, default))
            mi.connect("toggled", lambda w, k=key: self.island.set_option(k, w.get_active()))
            sub.append(mi)
        parent = Gtk.MenuItem(label=_("Live-Hinweise"))
        parent.set_submenu(sub)
        return parent

    def _monitors_menu(self):
        self._monitor_menu = Gtk.Menu()
        self._fill_monitors_menu()
        parent = Gtk.MenuItem(label=_("Monitor"))
        parent.set_submenu(self._monitor_menu)
        return parent

    def refresh_monitors(self):
        """Monitor plugged in or out: list the connected ones again."""
        if self._monitor_menu is not None:
            self._fill_monitors_menu()

    def _fill_monitors_menu(self):
        sub = self._monitor_menu
        for child in sub.get_children():
            sub.remove(child)
        display = self.island.get_display()
        current = self.island.config.get("monitor", monitors.PRIMARY)
        if not isinstance(current, (str, int)):
            current = monitors.PRIMARY  # broken value in config.json: the island uses the primary one
        choices = [(monitors.PRIMARY, _("Hauptmonitor")),
                   (monitors.POINTER, _("Monitor mit der Maus (beim Öffnen)"))]
        connected = monitors.ordered(display)
        for monitor in connected:
            text = monitors.describe(monitor)
            if monitor.is_primary():
                text = _("{monitor} (Hauptmonitor)").format(monitor=text)
            choices.append((monitors.key(display, monitor), text))
        # A number from config.json picks the item of that monitor; a monitor that is unplugged stays listed
        index = monitors.index_of(current)
        if index is not None and 0 <= index < len(connected):
            current = monitors.key(display, connected[index])
        elif current not in dict(choices):
            choices.append((current, _("{monitor} (nicht angeschlossen)").format(monitor=current)))
        self._radio_items(sub, choices, current, lambda value: self.island.set_option("monitor", value))
        sub.show_all()

    def _notifications_menu(self):
        self._notify_menu = Gtk.Menu()
        self._fill_notifications_menu()
        parent = Gtk.MenuItem(label=_("Benachrichtigungen"))
        parent.set_submenu(self._notify_menu)
        return parent

    def refresh_notifications(self):
        """Rebuild the notifications submenu (new app seen, switch changed) – once, after the current event."""
        if self._notify_menu is None or self._notify_refresh_id:
            return

        def refresh():
            self._notify_refresh_id = 0
            self._fill_notifications_menu()
            return GLib.SOURCE_REMOVE

        self._notify_refresh_id = GLib.idle_add(refresh)

    def _fill_notifications_menu(self):
        sub = self._notify_menu
        for child in sub.get_children():
            sub.remove(child)
        island, on = self.island, self.island.config.get("notifications_on_island", True)

        def check(text, active, callback, sensitive=True):
            mi = Gtk.CheckMenuItem(label=text)
            mi.set_active(active)
            mi.set_sensitive(sensitive)
            mi.connect("toggled", lambda w: callback(w.get_active()))
            sub.append(mi)

        check(_("Auf der Insel anzeigen"), on, lambda v: island.set_option("notifications_on_island", v))
        check(_("Nicht stören"), bool(island.dnd_get()), island.dnd_set)
        sub.append(Gtk.SeparatorMenuItem())
        header = Gtk.MenuItem(label=_("Auf der Insel ausblenden:"))
        header.set_sensitive(False)
        sub.append(header)
        apps = island.notification_apps()
        for name, hidden in apps:
            check(name, hidden, lambda v, n=name: island.set_app_hidden(n, v), sensitive=on)
        if not apps:
            empty = Gtk.MenuItem(label=_("Noch keine Benachrichtigungen"))
            empty.set_sensitive(False)
            sub.append(empty)
        sub.show_all()

    def _language_menu(self, current):
        # Bilingual on purpose: whoever ends up in the wrong language still finds the way back
        choices = [("auto", _("Automatisch (System)"))] + list(LANGUAGES.items())
        return self._radio_menu("Sprache / Language", choices, current if current in LANGUAGES else "auto",
                                self.island.set_language)

    @staticmethod
    def _set_autostart(enabled):
        if enabled:
            AUTOSTART.parent.mkdir(parents=True, exist_ok=True)
            AUTOSTART.write_text(
                "[Desktop Entry]\nType=Application\nName=MosIsland (LinuxMos)\nComment=Dynamic Island for Cinnamon\n"
                f"Exec={_launcher()}\nX-GNOME-Autostart-enabled=true\nX-GNOME-Autostart-Delay=3\n",
                encoding="utf-8")
        else:
            AUTOSTART.unlink(missing_ok=True)

    def _set_osd(self, enabled):
        self.island.set_option("osd", enabled)
        # Island's overlays replace Cinnamon's own volume/brightness popup
        cinnamon = system.settings("org.cinnamon")
        if not cinnamon or "show-media-keys-osd" not in cinnamon.props.settings_schema.list_keys():
            return
        # Boolean in newer Cinnamon, a size string (small|medium|large|disabled) in older ones
        if cinnamon.get_value("show-media-keys-osd").get_type_string() == "b":
            cinnamon.set_boolean("show-media-keys-osd", not enabled)
        else:
            cinnamon.set_string("show-media-keys-osd", "disabled" if enabled else "medium")

    @staticmethod
    def _about():
        dialog = Gtk.AboutDialog(
            program_name="MosIsland",
            version=__version__,
            comments=_("Dynamic Island für Linux Mint Cinnamon – Teil von LinuxMos.\n"
                       "Inspiriert von Island (exuupery) und Nusa (rama2555) – eigene Umsetzung."),
            website="https://github.com/xypep/LinuxMos",
            logo_icon_name="view-app-grid-symbolic",
        )
        dialog.run()
        dialog.destroy()
