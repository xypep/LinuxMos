"""Small GTK helpers shared by the settings window and its pages (settings.py runs as __main__, so the pages
can't import from it)."""

from pathlib import Path

import gi

from island import without_gl
from island.storage import launcher_path

gi.require_version("Gtk", "3.0")
with without_gl():
    from gi.repository import Gio, GLib, Gtk

TRAY_LINES = (
    "Einstellungen & Übersicht · Wach halten (Häkchen) · Farbpipette starten · Fenster anpinnen",
    "Autostart · Maskottchen (Figur, Augen-Modus) · Dehnen · Minimal-Notch · Lautstärke & Helligkeit",
    "Zwischenablage automatisch leeren · Clip-Transfer · Suche · Screenshot · Text & QR · Bildschirmaufnahme",
    "KI · Benachrichtigungen · Live-Hinweise · Monitor · Sprache · Config-Datei öffnen · Über · Beenden",
)


# ---- small helpers -------------------------------------------------------------------------------------------
def label(text="", css=(), xalign=0.0, wrap=False, selectable=False):
    lbl = Gtk.Label(label=text, xalign=xalign, wrap=wrap, selectable=selectable)
    if wrap:
        lbl.set_line_wrap_mode(2)           # Pango.WrapMode.WORD_CHAR
    for cls in css:
        lbl.get_style_context().add_class(cls)
    return lbl


def css_class(widget, *classes):
    for cls in classes:
        widget.get_style_context().add_class(cls)
    return widget


def clear(container):
    for child in container.get_children():
        child.destroy()


def flat_button(text, css=(), on_click=None, tooltip=None):
    btn = Gtk.Button(label=text)
    btn.set_relief(Gtk.ReliefStyle.NONE)
    btn.set_can_focus(False)
    css_class(btn, *css)
    if tooltip:
        btn.set_tooltip_text(tooltip)
    if on_click:
        btn.connect("clicked", lambda *_: on_click())
    return btn


def banner(text, error=False):
    box = css_class(Gtk.Box(spacing=10), "banner", *(["error"] if error else []))
    box.pack_start(label(text, wrap=True), True, True, 0)
    return box


def bin_dir():
    return str(Path(launcher_path()).parent)


def open_file(path):
    """xdg-open, else gio open, else xed (the first one that works)."""
    for argv in (["xdg-open", str(path)], ["gio", "open", str(path)], ["xed", str(path)]):
        if GLib.find_program_in_path(argv[0]):
            try:
                Gio.Subprocess.new(argv, Gio.SubprocessFlags.STDOUT_SILENCE | Gio.SubprocessFlags.STDERR_SILENCE)
                return True
            except GLib.Error:
                continue
    return False
