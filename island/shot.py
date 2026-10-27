"""Screenshot, text or QR code without a running island:

    python3 -m island.shot area|screen|ocr|qr

A short-lived process for the hotkeys' fallback. With the island running,
linuxmos-island --shot/--ocr/--qr go straight to it over D-Bus instead.
"""

import os
import subprocess
import sys

import gi

from island import without_gl

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
with without_gl():   # GTK starts on import (see island/__init__.py)
    from gi.repository import Gio, GLib, Gtk

from island import i18n  # noqa: E402
from island.i18n import _  # noqa: E402
from island.services import ocr, screenshot  # noqa: E402
from island.storage import Config  # noqa: E402

NOTIFY_WAIT_S = 30


def _notify_edit(title, body):
    """Notification with an "Edit" button; True if it was clicked."""
    if not GLib.find_program_in_path("notify-send"):
        return False
    base = ["notify-send", "-a", "MosIsland", "-i", "camera-photo-symbolic"]
    try:
        # --action/--wait need libnotify 0.7.10+ (Mint 22 has 0.8)
        out = subprocess.run(base + ["--action=edit=" + _("Bearbeiten"), "--wait", title, body],
                             capture_output=True, text=True, timeout=NOTIFY_WAIT_S)
    except subprocess.TimeoutExpired:
        return False
    if out.returncode != 0:
        subprocess.run(base + [title, body], check=False)
        return False
    return out.stdout.strip() == "edit"


def _edit(path, config):
    from island.editor import Editor

    editor = Editor(path, config)
    editor.connect("destroy", lambda *_: Gtk.main_quit())
    editor.present()
    Gtk.main()


def _notify(icon, title, body=""):
    if GLib.find_program_in_path("notify-send"):
        subprocess.run(["notify-send", "-a", "MosIsland", "-i", icon, title, body], check=False)


def _run(argv, env=None):
    out = subprocess.run(argv, capture_output=True, text=True, errors="replace", check=False,
                         env={**os.environ, **env} if env else None)
    return out.returncode, out.stdout, out.stderr


def _copy_text(text):
    # xclip forks and keeps serving the text after this process is gone
    subprocess.run(["xclip", "-selection", "clipboard", "-in"], input=text, text=True, check=False)


def read_screen(kind, config):
    """Pick an area, read its text or QR codes onto the clipboard and say so in a notification."""
    missing = ocr.missing(kind)
    if missing:
        print(_("Für {what} fehlt: {programs}").format(
            what=_("Texterkennung") if kind == "text" else _("QR-Codes"), programs=", ".join(missing)),
            file=sys.stderr)
        return 1
    path = ocr.temp_path()
    try:
        if subprocess.run(screenshot.capture_argv("area", None, path), check=False).returncode != 0 \
                or path.stat().st_size == 0:
            return 1  # selection cancelled
        if kind == "text":
            source = ocr.upscaled(path)
            text, error = ocr.text_result(*_run(ocr.text_argv(source, config.get("ocr_languages", "deu+eng")),
                                                ocr.TESSERACT_ENV),
                                          config.get("ocr_keep_linebreaks", False))
            if source != path:
                source.unlink(missing_ok=True)
        else:
            codes, error = ocr.codes_result(*_run(ocr.codes_argv(path)))
            wifi = ocr.parse_wifi(codes[0][1]) if len(codes) == 1 else None
            text = (wifi["password"] or wifi["ssid"]) if wifi else "\n".join(d for _k, d in codes)
    finally:
        path.unlink(missing_ok=True)

    if error:
        _notify("dialog-warning-symbolic", _("Sprachdaten fehlen: {languages}").format(
            languages=config.get("ocr_languages", "deu+eng")) if error == "language" else error)
        return 1
    if not text:
        _notify("edit-find-symbolic", _("Kein Text gefunden") if kind == "text" else _("Kein QR-Code gefunden"))
        return 0
    _copy_text(text)
    if kind == "qr" and config.get("qr_open_links", False) and ocr.link(text):
        Gio.AppInfo.launch_default_for_uri(ocr.link(text), None)
    _notify("edit-select-all-symbolic", _("Text erkannt · kopiert") if kind == "text" else _("QR-Code · kopiert"),
            text[:300])
    return 0


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    mode = argv[0] if argv else "area"
    if mode not in ("area", "screen", "ocr", "qr"):
        print("Usage: python3 -m island.shot area|screen|ocr|qr", file=sys.stderr)
        return 2
    config = Config.load()
    i18n.setup(config.get("language", "auto"))
    if mode in ("ocr", "qr"):
        return read_screen("text" if mode == "ocr" else "qr", config)
    missing = screenshot.missing(mode)
    if missing:
        print(_("Für Screenshots fehlt: {programs}").format(programs=", ".join(missing)), file=sys.stderr)
        return 1

    geometry = screenshot.pointer_monitor_geometry() if mode == "screen" else None
    path = screenshot.new_path(config)
    if subprocess.run(screenshot.capture_argv(mode, geometry, path), check=False).returncode != 0 \
            or not path.is_file():
        path.unlink(missing_ok=True)
        return 1  # selection cancelled
    subprocess.run(screenshot.copy_argv(path), check=False)

    if config.get("screenshot_open_editor", False) or _notify_edit(
            _("Screenshot kopiert"), "" if screenshot.is_temp(path) else str(path)):
        _edit(path, config)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
