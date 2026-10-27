"""Loads album covers (local files or http URLs) off the UI thread, with a small cache.

Every cover is decoded once at COVER_PX (the biggest size the island shows,
rounded_image() scales it down for the pill) by GdkPixbuf's own worker, so no
Python thread is needed. Downloaded covers are stored already shrunk to
COVER_PX: a few KB per cover on disk instead of originals of up to 5 MB.
"""

from collections import OrderedDict
from urllib.parse import unquote, urlparse

from gi.repository import GdkPixbuf, Gio, GLib

from island.services import http
from island.storage import CACHE_DIR

ART_DIR = CACHE_DIR / "art"
COVER_PX = 144          # HomePage.COVER at scale 2
MAX_DOWNLOAD = 5 * 1024 * 1024
DISK_LIMIT = 40
SHRINK_ABOVE = 200 * 1024
_memory = OrderedDict()  # url -> Pixbuf
_MEMORY_LIMIT = 6
_waiting = {}            # url -> [callbacks] while it loads


def load(url, callback):
    """callback(pixbuf or None) is always invoked on the main loop."""
    if not url:
        callback(None)
        return
    if url in _memory:
        _memory.move_to_end(url)
        callback(_memory[url])
        return
    if url in _waiting:
        _waiting[url].append(callback)   # the pill and the opened island ask for the same song
        return
    _waiting[url] = [callback]
    parsed = urlparse(url)
    if parsed.scheme == "file":
        _decode_file(url, Gio.File.new_for_path(unquote(parsed.path)))
    elif parsed.scheme in ("http", "https"):
        cached = _cache_path(url)
        try:
            size = cached.stat().st_size
        except OSError:
            size = None
        if size:
            # A full-size original from before 1.10: shrink it on the way
            shrink = (lambda pix: _store(url, pix)) if size > SHRINK_ABOVE else None
            _decode_file(url, Gio.File.new_for_path(str(cached)), shrink)
        else:
            http.get(url, lambda status, body: _downloaded(url, status, body), timeout=6, max_bytes=MAX_DOWNLOAD)
    else:
        _deliver(url, None)


def _cache_path(url):
    # GLib's SHA-1 gives the same names as hashlib's (old cache files stay valid) without OpenSSL
    return ART_DIR / GLib.compute_checksum_for_string(GLib.ChecksumType.SHA1, url, -1)


def _decode_file(url, gfile, on_pixbuf=None):
    def opened(f, result):
        try:
            stream = f.read_finish(result)
        except GLib.Error:
            _deliver(url, None)
            return
        _decode(url, stream, on_pixbuf)

    gfile.read_async(GLib.PRIORITY_LOW, None, opened)


def _decode(url, stream, on_pixbuf=None):
    def done(_src, result):
        try:
            pixbuf = GdkPixbuf.Pixbuf.new_from_stream_finish(result)
        except GLib.Error:
            pixbuf = None
        try:
            stream.close(None)
        except GLib.Error:
            pass
        if pixbuf is not None and on_pixbuf:
            on_pixbuf(pixbuf)
        _deliver(url, pixbuf)

    GdkPixbuf.Pixbuf.new_from_stream_at_scale_async(stream, COVER_PX, COVER_PX, True, None, done)


def _downloaded(url, status, body):
    if status != 200 or not body:
        _deliver(url, None)
        return
    _decode(url, Gio.MemoryInputStream.new_from_bytes(GLib.Bytes.new(body)), lambda pix: _store(url, pix))


def _store(url, pixbuf):
    """Keep the shrunk cover on disk; only the DISK_LIMIT newest survive."""
    try:
        ART_DIR.mkdir(parents=True, exist_ok=True)
        target = _cache_path(url)
        if pixbuf.get_has_alpha():
            pixbuf.savev(str(target), "png", [], [])
        else:
            pixbuf.savev(str(target), "jpeg", ["quality"], ["90"])
        files = sorted(ART_DIR.iterdir(), key=lambda p: p.stat().st_mtime)
        for old in files[:-DISK_LIMIT]:
            old.unlink(missing_ok=True)
    except (OSError, GLib.Error):
        pass


def _deliver(url, pixbuf):
    if pixbuf is not None:
        _memory[url] = pixbuf
        while len(_memory) > _MEMORY_LIMIT:
            _memory.popitem(last=False)
    for callback in _waiting.pop(url, []):
        callback(pixbuf)
