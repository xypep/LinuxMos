"""Tray icon (XApp status icon, shown by Cinnamon's panel) with the island's switches."""

import shutil
from pathlib import Path

import gi
from gi.repository import Gtk

from island import __version__
from island.i18n import LANGUAGES, _
from island.services import system

try:
    gi.require_version("XApp", "1.0")
    from gi.repository import XApp
except (ValueError, ImportError):
    XApp = None

AUTOSTART = Path.home() / ".config" / "autostart" / "linuxmos-island.desktop"

# Clipboard auto-delete choices in the tray (minutes, 0 = off); other values via config.json.
# Labels are German source strings, translated when the menu is built.
AUTODELETE_CHOICES = [(0, "Nie"), (15, "Nach 15 Minuten"), (60, "Nach 1 Stunde"), (1440, "Nach 24 Stunden")]


def _launcher():
    return shutil.which("linuxmos-island") or str(Path.home() / ".local" / "bin" / "linuxmos-island")


class Tray:
    def __init__(self, island):
        self.island = island
        self.icon = None
        if XApp is None:
            return
        self.icon = XApp.StatusIcon()
        self.icon.set_name("linuxmos-island")
        self.icon.set_icon_name("view-app-grid-symbolic")
        self.icon.set_tooltip_text("MosIsland")
        self.icon.connect("activate", lambda *_: island.toggle())
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

        item(_("MosIsland öffnen"), lambda: self.island.expand())
        menu.append(Gtk.SeparatorMenuItem())
        check(_("Mit Cinnamon starten"), AUTOSTART.exists(), self._set_autostart)
        check(_("Maskottchen"), cfg.get("mascot", True), lambda on: self.island.set_option("mascot", on))
        check(_("Minimal-Notch"), cfg.get("compact_when_idle", False),
              lambda on: self.island.set_option("compact_when_idle", on))
        check(_("Lautstärke & Helligkeit anzeigen"), cfg.get("osd", True), self._set_osd)
        menu.append(self._autodelete_menu(cfg.get("clipboard_autodelete_min", 0)))
        menu.append(self._language_menu(cfg.get("language", "auto")))
        menu.append(Gtk.SeparatorMenuItem())
        item(_("Über MosIsland"), self._about)
        item(_("Beenden"), lambda: self.island.get_application().quit())
        menu.show_all()
        return menu

    @staticmethod
    def _radio_menu(label, choices, current, on_select):
        """Submenu with one radio item per (value, label); on_select(value) for the newly chosen one."""
        sub = Gtk.Menu()
        group = None
        for value, text in choices:
            mi = Gtk.RadioMenuItem.new_with_label_from_widget(group, text)
            group = group or mi
            mi.set_active(value == current)
            # "toggled" also fires for the item that gets deselected
            mi.connect("toggled", lambda w, v=value: w.get_active() and on_select(v))
            sub.append(mi)
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
