"""Loads album covers (local files or http URLs) off the UI thread, with a small cache."""

import hashlib
import threading
import urllib.request
from collections import OrderedDict
from urllib.parse import unquote, urlparse

from gi.repository import GdkPixbuf, GLib

from island.storage import CACHE_DIR

ART_DIR = CACHE_DIR / "art"
_memory = OrderedDict()  # (url, size) -> Pixbuf
_MEMORY_LIMIT = 12


def load(url, size, callback):
    """callback(pixbuf or None) is always invoked on the main loop."""
    if not url:
        callback(None)
        return
    key = (url, size)
    if key in _memory:
        _memory.move_to_end(key)
        callback(_memory[key])
        return
    threading.Thread(target=_worker, args=(url, size, callback), daemon=True).start()


def _worker(url, size, callback):
    pixbuf = None
    try:
        parsed = urlparse(url)
        if parsed.scheme == "file":
            path = unquote(parsed.path)
        elif parsed.scheme in ("http", "https"):
            path = _download(url)
        else:
            path = None
        if path:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(str(path), size, size, True)
    except (OSError, GLib.Error, ValueError):
        pixbuf = None
    GLib.idle_add(_deliver, url, size, pixbuf, callback)


def _download(url):
    ART_DIR.mkdir(parents=True, exist_ok=True)
    target = ART_DIR / hashlib.sha1(url.encode()).hexdigest()
    if not target.exists():
        req = urllib.request.Request(url, headers={"User-Agent": "LinuxMos-Island"})
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = resp.read(5 * 1024 * 1024)
        target.write_bytes(data)
        # Keep the cache small: only the 40 newest covers survive
        files = sorted(ART_DIR.iterdir(), key=lambda p: p.stat().st_mtime)
        for old in files[:-40]:
            old.unlink(missing_ok=True)
    return target


def _deliver(url, size, pixbuf, callback):
    if pixbuf is not None:
        _memory[(url, size)] = pixbuf
        while len(_memory) > _MEMORY_LIMIT:
            _memory.popitem(last=False)
    callback(pixbuf)
    return GLib.SOURCE_REMOVE
