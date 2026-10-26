"""Screen recording: an area (slop) or the monitor under the pointer, grabbed by ffmpeg (x11grab).

Only builds the commands and finishes the files; the island runs them (app.py: record()),
so nothing here costs anything until a hotkey or the tray asks for a recording.

    MP4  H.264 straight into ~/Videos/LinuxMos, with the system sound or the microphone if wanted
    GIF  recorded as a small temporary MP4 first, then turned into a GIF with an own palette
         (ffmpeg's default palette makes GIFs look dull), no sound

ffmpeg ends cleanly on SIGINT (it writes the file's index first): the island sends that to stop
and never kills it.
"""

import os
import re
import time
from pathlib import Path

from gi.repository import Gio, GLib

from island.storage import CACHE_DIR

FORMATS = ("mp4", "gif")
AUDIO = ("off", "system", "mic")
# Temporary MP4s of GIF recordings; the log of the last ffmpeg run (the reason if one fails)
TEMP_DIR = CACHE_DIR / "recordings"
LOG = TEMP_DIR / "ffmpeg.log"

MIN_SIDE = 16               # px: a smaller area is a mis-click, not a recording
GIF_FPS, GIF_MAX_WIDTH = 15, 960
# PulseAudio source names that follow the default devices (PipeWire's pulse server knows them too)
AUDIO_SOURCES = {"system": "@DEFAULT_MONITOR@", "mic": "@DEFAULT_SOURCE@"}

# slop's look is the screenshot selection's (a light blue veil), printing "WxH+X+Y"
SELECT_ARGV = ["slop", "--format=%wx%h+%x+%y", "--highlight", "--color=0.04,0.52,1,0.25", "--bordersize=1"]

_GEOMETRY = re.compile(r"^\s*(\d+)x(\d+)\+(-?\d+)\+(-?\d+)\s*$")


def missing(mode):
    """Programs a recording of this mode needs but that are not installed."""
    need = ["ffmpeg"] + (["slop"] if mode == "area" else [])
    return [p for p in need if GLib.find_program_in_path(p) is None]


def default_dir():
    """~/Videos/LinuxMos (~/Videos on a German system as well)."""
    videos = GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_VIDEOS)
    return Path(videos or Path.home() / "Videos") / "LinuxMos"


def folder(config):
    custom = (config.get("record_dir") or "").strip()
    return Path(custom).expanduser() if custom else default_dir()


def open_folder(config):
    directory = folder(config)
    directory.mkdir(parents=True, exist_ok=True)
    try:
        Gio.AppInfo.launch_default_for_uri(directory.as_uri(), None)
    except GLib.Error:
        pass


def fmt(config):
    value = config.get("record_format", "mp4")
    return value if value in FORMATS else "mp4"


def audio(config):
    """The sound source asked for; GIFs have none."""
    value = config.get("record_audio", "off")
    return value if value in AUDIO and fmt(config) == "mp4" else "off"


def fps(config):
    value = config.get("record_fps", 30)
    return value if isinstance(value, int) and not isinstance(value, bool) and 1 <= value <= 60 else 30


def max_seconds(config):
    """Recording stops by itself after this long (0 = never), so a forgotten one cannot fill the disk."""
    value = config.get("record_max_min", 30)
    return value * 60 if isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0 else 0


def _unique(directory, stem, ext):
    path = directory / f"{stem}.{ext}"
    n = 2
    while path.exists():
        path = directory / f"{stem}_{n}.{ext}"
        n += 1
    return path


def new_paths(config):
    """(path ffmpeg records to, final path). They are the same unless the result is a GIF."""
    stem = time.strftime("Recording_%Y-%m-%d_%H-%M-%S")
    directory = folder(config)
    directory.mkdir(parents=True, exist_ok=True)
    if fmt(config) == "gif":
        TEMP_DIR.mkdir(parents=True, exist_ok=True)
        return _unique(TEMP_DIR, stem, "mp4"), _unique(directory, stem, "gif")
    final = _unique(directory, stem, "mp4")
    return final, final


# ---- geometry --------------------------------------------------------------------
def parse_geometry(text):
    """'WxH+X+Y' (slop, screenshot.pointer_monitor_geometry) -> (w, h, x, y), None if it is none."""
    match = _GEOMETRY.match(text or "")
    return tuple(int(g) for g in match.groups()) if match else None


def usable(geometry):
    """Round the size down to even numbers (H.264 with yuv420p needs them); None if too small."""
    if geometry is None:
        return None
    w, h, x, y = geometry
    w, h = w - w % 2, h - h % 2
    return (w, h, x, y) if w >= MIN_SIDE and h >= MIN_SIDE else None


def grab_input(geometry, display=None):
    """x11grab's input: ':0.0+X,Y' (the screen number is optional in $DISPLAY but not for the offset)."""
    display = display or os.environ.get("DISPLAY") or ":0"
    host, _sep, rest = display.rpartition(":")
    number, dot, screen = rest.partition(".")
    return f"{host}:{number}.{screen if dot else '0'}+{geometry[2]},{geometry[3]}"


# ---- commands ----------------------------------------------------------------------
def record_argv(config, geometry, path, display=None):
    """ffmpeg grabbing `geometry` (w, h, x, y) into `path`, with the sound the config asks for."""
    w, h, _x, _y = geometry
    gif = fmt(config) == "gif"
    rate = min(fps(config), GIF_FPS) if gif else fps(config)
    argv = ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
            "-thread_queue_size", "512", "-f", "x11grab", "-framerate", str(rate), "-draw_mouse", "1",
            "-video_size", f"{w}x{h}", "-i", grab_input(geometry, display)]
    source = AUDIO_SOURCES.get(audio(config))
    if source:
        argv += ["-thread_queue_size", "512", "-f", "pulse", "-i", source]
    # ultrafast keeps the encoder's CPU use low while something else is happening on the screen
    argv += ["-c:v", "libx264", "-preset", "ultrafast" if gif else "veryfast", "-crf", "23",
             "-pix_fmt", "yuv420p"]
    if source:
        argv += ["-c:a", "aac", "-b:a", "128k"]
    limit = max_seconds(config)
    if limit:
        argv += ["-t", str(limit)]
    return argv + ["-movflags", "+faststart", str(path)]


def gif_argv(source, target):
    """MP4 -> GIF with a palette made from the video itself (and at most 960 px wide)."""
    graph = (f"fps={GIF_FPS},scale='min({GIF_MAX_WIDTH},iw)':-2:flags=lanczos,split[a][b];"
             "[a]palettegen=stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=5")
    return ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y", "-i", str(source),
            "-vf", graph, "-loop", "0", str(target)]


def launcher(log=LOG):
    """Gio.SubprocessLauncher that keeps ffmpeg's error messages in `log`."""
    log.parent.mkdir(parents=True, exist_ok=True)
    launcher_ = Gio.SubprocessLauncher.new(Gio.SubprocessFlags.STDOUT_SILENCE)
    launcher_.set_stderr_file_path(str(log))
    return launcher_


def last_error(log=LOG):
    """The last line ffmpeg complained about (empty if none)."""
    try:
        lines = [line.strip() for line in log.read_text(errors="replace").splitlines() if line.strip()]
    except OSError:
        return ""
    return lines[-1][:160] if lines else ""


def good(path):
    """A recording that exists and holds data (ffmpeg exits non-zero after SIGINT, so the file decides)."""
    try:
        return path.stat().st_size > 0
    except OSError:
        return False


def convert_to_gif(source, target, on_done):
    """Turn the MP4 into a GIF in the background; on_done(ok). The MP4 goes away afterwards."""
    try:
        proc = launcher().spawnv(gif_argv(source, target))
    except GLib.Error:
        on_done(False)
        return

    def finished(p, result):
        try:
            ok = p.wait_check_finish(result)
        except GLib.Error:
            ok = False
        Path(source).unlink(missing_ok=True)
        if not ok:
            Path(target).unlink(missing_ok=True)
        on_done(ok)

    proc.wait_check_async(None, finished)
