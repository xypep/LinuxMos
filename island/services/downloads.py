"""Downloads in progress: a small ring on the island, a hint when one is done.

Push based, nothing is polled while no download runs:
  files     inotify on the download folder (Gio.FileMonitor, at most one
            update per second): browsers write into a temporary file there
              Firefox            name.part        -> renamed to name
              Chromium/Chrome    name.crdownload  -> renamed to name
  percent   the file system doesn't know a download's total size. Browsers
            that report progress to the dock (com.canonical.Unity.LauncherEntry,
            e.g. Chromium/Chrome) give a real percentage; else the island shows
            the size so far and the speed.
While downloads run, one check every 15 s drops the ones that stalled (paused).
"""

import os
import time
from pathlib import Path

from gi.repository import Gio, GLib

from island.i18n import _, decimal

TEMP_SUFFIXES = {".part": "firefox", ".crdownload": "chromium"}
RATE_LIMIT_MS = 1000
STALL_CHECK_S = 15
STALL_AFTER_S = 60
LAUNCHER = "com.canonical.Unity.LauncherEntry"


def download_dir(config):
    folder = config.get("downloads_dir") or GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_DOWNLOAD)
    return Path(os.path.expanduser(folder)) if folder else Path.home() / "Downloads"


def temp_kind(name):
    """'firefox' / 'chromium' for a browser's temporary download file, else None."""
    for suffix, kind in TEMP_SUFFIXES.items():
        if name.endswith(suffix) and len(name) > len(suffix):
            return kind
    return None


def display_name(name):
    for suffix in TEMP_SUFFIXES:
        name = name.removesuffix(suffix)
    # Chrome starts with "Unconfirmed 123456" until the name is known
    return _("Download") if name.startswith("Unconfirmed ") else name


class Download:
    __slots__ = ("path", "name", "kind", "size", "speed", "changed")

    def __init__(self, path, kind):
        self.path = path
        self.name = display_name(path.name)
        self.kind = kind
        self.size = 0
        self.speed = 0.0         # bytes/s, smoothed
        self.changed = time.monotonic()


class Downloads:
    def __init__(self, config, on_change, on_done):
        """on_change() when the running downloads change, on_done(path) when one is finished."""
        self.config = config
        self._on_change = on_change
        self._on_done = on_done
        self.enabled = False
        self.items = {}          # temporary path -> Download
        self._progress = {}      # kind -> 0..1 reported by the browser (all its downloads together)
        self._monitor = None
        self._bus = None
        self._sub = 0
        self._stall_id = 0

    # ---- lifecycle ---------------------------------------------------------------
    def start(self):
        if self.enabled:
            return
        self.enabled = True
        folder = download_dir(self.config)
        try:
            self._monitor = Gio.File.new_for_path(str(folder)).monitor_directory(
                Gio.FileMonitorFlags.WATCH_MOVES, None)
        except GLib.Error:
            self._monitor = None
        if self._monitor:
            self._monitor.set_rate_limit(RATE_LIMIT_MS)
            self._monitor.connect("changed", self._on_file_event)
        try:
            self._bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
            self._sub = self._bus.signal_subscribe(None, LAUNCHER, "Update", None, None,
                                                   Gio.DBusSignalFlags.NONE, self._on_launcher)
        except GLib.Error:
            self._bus = None

    def stop(self):
        if not self.enabled:
            return
        self.enabled = False
        if self._monitor:
            self._monitor.cancel()
            self._monitor = None
        if self._bus and self._sub:
            self._bus.signal_unsubscribe(self._sub)
            self._sub = 0
        if self._stall_id:
            GLib.source_remove(self._stall_id)
            self._stall_id = 0
        had = bool(self.items)
        self.items.clear()
        self._progress.clear()
        if had:
            self._on_change()

    def restart(self):
        """The folder changed in the settings."""
        if self.enabled:
            self.stop()
            self.start()

    # ---- what the island shows -----------------------------------------------------
    @property
    def active(self):
        return bool(self.items)

    @property
    def percent(self):
        """0..100 if every running download has a reported progress, else None."""
        kinds = {d.kind for d in self.items.values()}
        if not kinds or any(kind not in self._progress for kind in kinds):
            return None
        values = [self._progress[kind] for kind in kinds]
        return int(round(100 * sum(values) / len(values)))

    @property
    def total_size(self):
        return sum(d.size for d in self.items.values())

    @property
    def total_speed(self):
        return sum(d.speed for d in self.items.values())

    # ---- events ------------------------------------------------------------------
    def _on_file_event(self, _monitor, file, other, event):
        path = Path(file.get_path() or "")
        kind = temp_kind(path.name)
        E = Gio.FileMonitorEvent
        if event == E.RENAMED and other is not None:
            new = Path(other.get_path() or "")
            item = self.items.pop(path, None)
            new_kind = temp_kind(new.name)
            if new_kind:
                # Chrome: "Unconfirmed 1.crdownload" -> "name.crdownload"
                moved = item or Download(new, new_kind)
                moved.path, moved.name = new, display_name(new.name)
                self.items[new] = moved
                self._update(moved)
            elif kind:
                self._finished(new)
            if item is not None or new_kind or kind:
                self._changed()
        elif kind is None:
            return
        elif event in (E.CREATED, E.CHANGED, E.CHANGES_DONE_HINT, E.MOVED_IN):
            item = self.items.get(path)
            if item is None:
                item = self.items[path] = Download(path, kind)
            self._update(item)
            self._changed()
        elif event in (E.DELETED, E.MOVED_OUT):
            # Cancelled (a finished download is renamed, not deleted)
            if self.items.pop(path, None) is not None:
                self._changed()

    @staticmethod
    def _update(item):
        try:
            size = os.stat(item.path).st_size
        except OSError:
            return
        now = time.monotonic()
        dt = now - item.changed
        if dt > 0.2 and size >= item.size:
            rate = (size - item.size) / dt
            item.speed = rate if item.speed == 0 else 0.6 * item.speed + 0.4 * rate
        item.size, item.changed = size, now

    def _finished(self, path):
        self._on_done(path)

    def _changed(self):
        if not self.items:
            self._progress.clear()   # the browser's last report belongs to the finished ones
        if self.items and not self._stall_id:
            self._stall_id = GLib.timeout_add_seconds(STALL_CHECK_S, self._check_stalled)
        self._on_change()

    def _check_stalled(self):
        now = time.monotonic()
        stalled = [p for p, d in self.items.items() if now - d.changed > STALL_AFTER_S]
        for path in stalled:
            del self.items[path]   # paused; the next write brings it back
        if stalled:
            self._on_change()
        if self.items:
            return GLib.SOURCE_CONTINUE
        self._stall_id = 0
        return GLib.SOURCE_REMOVE

    def _on_launcher(self, _bus, _sender, _path, _iface, _signal, params):
        try:
            app_uri, props = params.unpack()
        except (TypeError, ValueError):
            return
        kind = "firefox" if "firefox" in app_uri else "chromium" if any(
            name in app_uri for name in ("chrom", "brave", "vivaldi", "opera", "edge")) else None
        if kind is None:
            return
        if props.get("progress-visible") and "progress" in props:
            self._progress[kind] = max(0.0, min(1.0, float(props["progress"])))
        elif "progress-visible" in props:
            self._progress.pop(kind, None)
        else:
            return
        if self.items:
            self._on_change()


def human_size(size):
    """1536 -> '1,5 KB' (decimal comma in German)."""
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1000 or unit == "GB":
            return f"{int(size)} {unit}" if unit == "B" else f"{decimal(size, 1 if size < 100 else 0)} {unit}"
        size /= 1000
    return ""
