"""Screenshot without a running island: python3 -m island.shot area|screen

A short-lived process for the hotkeys' fallback. With the island running,
linuxmos-island --shot goes straight to it over D-Bus instead.
"""

import subprocess
import sys

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import GLib, Gtk  # noqa: E402

from island import i18n  # noqa: E402
from island.i18n import _  # noqa: E402
from island.services import screenshot  # noqa: E402
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


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    mode = argv[0] if argv else "area"
    if mode not in ("area", "screen"):
        print("Usage: python3 -m island.shot area|screen", file=sys.stderr)
        return 2
    config = Config.load()
    i18n.setup(config.get("language", "auto"))
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
