"""Screenshots: an area (maim + slop) or the monitor under the pointer (maim).

The shot is saved as PNG and put on the clipboard with xclip, which stays in
the background as the clipboard owner, so the image survives the island.
Nothing here runs until a hotkey or button asks for a shot.
"""

import time
from pathlib import Path

from gi.repository import Gdk, Gio, GLib

from island.storage import CACHE_DIR

# Shots that are not kept in the pictures folder (screenshot_save = false)
TEMP_DIR = CACHE_DIR / "screenshots"
TEMP_KEEP = 5

# Selection look: a light blue veil like macOS (needs the compositor, Cinnamon always has one)
SELECT_ARGS = ["--select", "--highlight", "--color=0.04,0.52,1,0.25", "--bordersize=1"]


def missing(mode):
    """Programs a shot of this mode needs but that are not installed."""
    need = ["maim", "xclip"] + (["slop"] if mode == "area" else [])
    return [p for p in need if GLib.find_program_in_path(p) is None]


def default_dir():
    """~/Pictures/LinuxMos (~/Bilder/LinuxMos on a German system)."""
    pictures = GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_PICTURES)
    return Path(pictures or Path.home() / "Pictures") / "LinuxMos"


def folder(config):
    custom = (config.get("screenshot_dir") or "").strip()
    return Path(custom).expanduser() if custom else default_dir()


def _unique(directory, stem):
    path = directory / f"{stem}.png"
    n = 2
    while path.exists():
        path = directory / f"{stem}_{n}.png"
        n += 1
    return path


def new_path(config, saved=None):
    """Where the next shot goes: the pictures folder, or a small rotating cache."""
    saved = config.get("screenshot_save", True) if saved is None else saved
    directory = folder(config) if saved else TEMP_DIR
    directory.mkdir(parents=True, exist_ok=True)
    if not saved:
        old = sorted(TEMP_DIR.glob("*.png"), key=lambda p: p.stat().st_mtime)
        for path in old[:max(0, len(old) - TEMP_KEEP + 1)]:
            path.unlink(missing_ok=True)
    return _unique(directory, time.strftime("Screenshot_%Y-%m-%d_%H-%M-%S"))


def is_temp(path):
    return Path(path).parent == TEMP_DIR


def pointer_monitor_geometry():
    """X11 geometry 'WxH+X+Y' of the monitor under the pointer, in device pixels."""
    display = Gdk.Display.get_default()
    _screen, x, y = display.get_default_seat().get_pointer().get_position()
    monitor = display.get_monitor_at_point(x, y) or display.get_primary_monitor() or display.get_monitor(0)
    g, scale = monitor.get_geometry(), monitor.get_scale_factor()
    return f"{g.width * scale}x{g.height * scale}+{g.x * scale}+{g.y * scale}"


def capture_argv(mode, geometry, path):
    """maim exits non-zero when the selection is cancelled (Esc, right click)."""
    argv = ["maim", "--hidecursor", "--format=png"]
    if mode == "area":
        argv += SELECT_ARGS
    elif geometry:
        argv.append(f"--geometry={geometry}")
    return argv + [str(path)]


def copy_argv(path):
    return ["xclip", "-selection", "clipboard", "-target", "image/png", "-in", str(path)]


def copy(path):
    """Put the PNG on the clipboard. xclip forks and serves it until something else is copied."""
    try:
        Gio.Subprocess.new(copy_argv(path), Gio.SubprocessFlags.STDOUT_SILENCE | Gio.SubprocessFlags.STDERR_SILENCE)
        return True
    except GLib.Error:
        return False


def open_folder(config):
    directory = folder(config)
    directory.mkdir(parents=True, exist_ok=True)
    try:
        Gio.AppInfo.launch_default_for_uri(directory.as_uri(), None)
    except GLib.Error:
        pass
