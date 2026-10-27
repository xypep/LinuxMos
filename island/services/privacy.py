"""Microphone and camera in use: an orange and a green dot on the island.

Push based, nothing is polled:
  microphone  the `pactl subscribe` stream the volume indicator already runs
              (events on source-output / source); on an event the recording
              streams are listed once (`pactl -f json list ...`)
  camera      inotify on /dev/video* (IN_OPEN / IN_CLOSE) plus /dev itself for
              plugged cameras; on an event the processes holding a camera are
              looked up in /proc/*/fd (like `fuser`, only our own processes)

Peak meters (pavucontrol) and streams on a speaker's monitor are no recording
and stay out. A camera that is opened only for a moment (PipeWire probing the
devices, a browser listing them) never shows: the lookup waits a second.
"""

import ctypes
import json
import os
import struct

from gi.repository import Gio, GLib

from island.services import system

# <sys/inotify.h>
IN_OPEN, IN_CLOSE_WRITE, IN_CLOSE_NOWRITE = 0x20, 0x08, 0x10
IN_CREATE, IN_DELETE, IN_IGNORED = 0x100, 0x200, 0x8000
EVENT = struct.Struct("iIII")    # wd, mask, cookie, len

MIC_DEBOUNCE_MS = 300
CAM_SETTLE_MS = 1000
# Streams that only measure a level, not record
METER_NAMES = {"peak detect"}
# Process names -> what the user knows them as
PRETTY = {"pipewire": "PipeWire", "wireplumber": "PipeWire", "chrome": "Chrome", "chromium": "Chromium",
          "firefox": "Firefox", "firefox-bin": "Firefox", "obs": "OBS Studio", "zoom": "Zoom",
          "teams-for-linux": "Teams", "cheese": "Cheese", "guvcview": "guvcview"}


def _libc():
    try:
        libc = ctypes.CDLL(None, use_errno=True)
        libc.inotify_init1.argtypes = [ctypes.c_int]
        libc.inotify_add_watch.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_uint32]
        libc.inotify_rm_watch.argtypes = [ctypes.c_int, ctypes.c_int]
        return libc
    except (OSError, AttributeError):
        return None


def app_name(pid):
    """A readable name for a process: its desktop entry's name, else the program name."""
    try:
        exe = os.path.basename(os.readlink(f"/proc/{pid}/exe"))
    except OSError:
        try:
            exe = open(f"/proc/{pid}/comm", encoding="utf-8").read().strip()
        except OSError:
            return None
    exe = exe.removesuffix(" (deleted)")
    if exe in PRETTY:
        return PRETTY[exe]
    try:
        info = Gio.DesktopAppInfo.new(f"{exe}.desktop")
    except TypeError:
        info = None
    return info.get_name() if info else exe


class Privacy:
    def __init__(self, on_change):
        """on_change() whenever the microphone or camera state changes."""
        self._on_change = on_change
        self.enabled = False
        self.mic_apps = []        # apps recording right now
        self.mic_muted = False    # all sources in use are muted
        self.cam_apps = []        # apps holding a camera
        self._mic_sources = []    # source names in use (for muting)
        self._mic_id = 0
        self._mic_busy = False
        self._mic_again = False
        self._libc = _libc()
        self._fd = -1
        self._io_id = 0
        self._dev_wd = -1
        self._cam_wds = {}        # wd -> device path
        self._cam_id = 0

    # ---- lifecycle ---------------------------------------------------------------
    def start(self):
        if self.enabled:
            return
        self.enabled = True
        self.on_pactl_line("")   # current state, e.g. a call already running
        self._start_camera()

    def stop(self):
        if not self.enabled:
            return
        self.enabled = False
        for attr in ("_mic_id", "_cam_id", "_io_id"):
            if getattr(self, attr):
                GLib.source_remove(getattr(self, attr))
                setattr(self, attr, 0)
        if self._fd >= 0:
            os.close(self._fd)
            self._fd = -1
        self._cam_wds.clear()
        changed = self.active
        self.mic_apps, self.cam_apps, self._mic_sources = [], [], []
        if changed:
            self._on_change()

    @property
    def active(self):
        return bool(self.mic_apps or self.cam_apps)

    # ---- microphone ----------------------------------------------------------------
    def on_pactl_line(self, line):
        """A line from `pactl subscribe` (None: the sound server went away, "": look now)."""
        if not self.enabled:
            return
        if line is None:
            line = ""
        elif line and "source-output" not in line and "on source #" not in line and "on server" not in line:
            return
        if self._mic_id:
            GLib.source_remove(self._mic_id)
        self._mic_id = GLib.timeout_add(MIC_DEBOUNCE_MS, self._query_mic)

    def _query_mic(self):
        self._mic_id = 0
        if self._mic_busy:
            self._mic_again = True   # one more look when the running one is done
            return GLib.SOURCE_REMOVE
        if not system.has("pactl"):
            return GLib.SOURCE_REMOVE
        self._mic_busy = True
        system.run(["pactl", "-f", "json", "list", "sources"],
                   lambda ok, out: system.run(["pactl", "-f", "json", "list", "source-outputs"],
                                              lambda ok2, out2: self._got_mic(ok and ok2, out, out2)))
        return GLib.SOURCE_REMOVE

    def _got_mic(self, ok, sources_json, outputs_json):
        self._mic_busy = False
        if self._mic_again:
            self._mic_again = False
            self._query_mic()
            return
        if not self.enabled:
            return
        apps, used, muted = parse_recording(sources_json, outputs_json, os.getpid()) if ok else ([], [], False)
        state = (apps, muted)
        self._mic_sources = used
        if state != (self.mic_apps, self.mic_muted):
            self.mic_apps, self.mic_muted = state
            self._on_change()

    def set_mic_muted(self, muted):
        """Mute (or unmute) every microphone that is recording right now."""
        for name in self._mic_sources or ["@DEFAULT_SOURCE@"]:
            system.run(["pactl", "set-source-mute", name, "1" if muted else "0"])
        # The "change on source" event that follows updates mic_muted

    # ---- camera ------------------------------------------------------------------
    def _start_camera(self):
        libc = self._libc
        if libc is None or not os.path.isdir("/dev"):
            return
        fd = libc.inotify_init1(os.O_NONBLOCK | os.O_CLOEXEC)
        if fd < 0:
            return
        self._fd = fd
        self._dev_wd = libc.inotify_add_watch(fd, b"/dev", IN_CREATE | IN_DELETE)
        for name in sorted(os.listdir("/dev")):
            if name.startswith("video"):
                self._watch_device(f"/dev/{name}")
        self._io_id = GLib.unix_fd_add_full(GLib.PRIORITY_DEFAULT, fd, GLib.IOCondition.IN, self._on_inotify)
        self._schedule_camera(0)   # already in use before the island started?

    def _watch_device(self, path):
        # Needs read access to the device; the seat's user gets it through udev (uaccess)
        wd = self._libc.inotify_add_watch(self._fd, path.encode(), IN_OPEN | IN_CLOSE_WRITE | IN_CLOSE_NOWRITE)
        if wd >= 0:
            self._cam_wds[wd] = path

    def _on_inotify(self, fd, _condition):
        try:
            data = os.read(fd, 4096)
        except BlockingIOError:
            return GLib.SOURCE_CONTINUE
        except OSError:
            self._io_id = 0
            return GLib.SOURCE_REMOVE
        offset, camera_event = 0, False
        while offset + EVENT.size <= len(data):
            wd, mask, _cookie, length = EVENT.unpack_from(data, offset)
            name = data[offset + EVENT.size:offset + EVENT.size + length].split(b"\0", 1)[0].decode(errors="replace")
            offset += EVENT.size + length
            if wd == self._dev_wd:
                if name.startswith("video"):
                    if mask & IN_CREATE:
                        self._watch_device(f"/dev/{name}")
                    camera_event = True
            elif mask & IN_IGNORED:
                self._cam_wds.pop(wd, None)   # device unplugged
                camera_event = True
            elif wd in self._cam_wds:
                camera_event = True
        if camera_event:
            self._schedule_camera(CAM_SETTLE_MS)
        return GLib.SOURCE_CONTINUE

    def _schedule_camera(self, ms):
        if self._cam_id:
            GLib.source_remove(self._cam_id)
        self._cam_id = GLib.timeout_add(ms, self._check_camera)

    def _check_camera(self):
        self._cam_id = 0
        apps = camera_users(set(self._cam_wds.values()), os.getpid())
        if apps != self.cam_apps:
            self.cam_apps = apps
            self._on_change()
        return GLib.SOURCE_REMOVE


def parse_recording(sources_json, outputs_json, own_pid):
    """(apps, sources in use, all muted) from `pactl -f json list sources` / `source-outputs`."""
    try:
        sources = json.loads(sources_json or "[]")
        outputs = json.loads(outputs_json or "[]")
    except ValueError:
        return [], [], False
    by_index = {}
    for src in sources:
        props = src.get("properties") or {}
        monitor = src.get("name", "").endswith(".monitor") or props.get("device.class") == "monitor"
        by_index[str(src.get("index"))] = (src.get("name", ""), bool(src.get("mute")), monitor)
    apps, used, muted = [], [], []
    for out in outputs:
        props = out.get("properties") or {}
        source = by_index.get(str(out.get("source")))
        if source is None or source[2] or out.get("corked"):
            continue   # a speaker's monitor, or paused
        if (props.get("media.name") or "").lower() in METER_NAMES:
            continue
        if str(props.get("application.process.id")) == str(own_pid):
            continue
        name = props.get("application.name") or props.get("application.process.binary") or "?"
        if name not in apps:
            apps.append(name)
        if source[0] not in used:
            used.append(source[0])
            muted.append(source[1])
    return apps, used, bool(muted) and all(muted)


def camera_users(devices, own_pid):
    """Names of the apps that have one of the devices open (only our own processes are readable)."""
    if not devices:
        return []
    uid, apps = os.getuid(), []
    try:
        pids = [p for p in os.listdir("/proc") if p.isdigit()]
    except OSError:
        return []
    for pid in pids:
        if int(pid) == own_pid:
            continue
        try:
            if os.stat(f"/proc/{pid}").st_uid != uid:
                continue
            fds = os.listdir(f"/proc/{pid}/fd")
        except OSError:
            continue
        for fd in fds:
            try:
                target = os.readlink(f"/proc/{pid}/fd/{fd}")
            except OSError:
                continue
            if target in devices:
                name = app_name(pid)
                if name and name not in apps:
                    apps.append(name)
                break
    return apps
