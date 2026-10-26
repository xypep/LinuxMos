"""Synced lyrics from LRCLIB (lrclib.net, free, no key) with a small disk cache.

Only the song title, artist, album and length are sent, and only while the
lyrics are actually shown (lyrics view open or lyrics-in-pill enabled).
"""

import hashlib
import json
import re
import threading
import urllib.parse
import urllib.request

from gi.repository import GLib

from island.storage import CACHE_DIR

USER_AGENT = "LinuxMos-Island/1.1 (+https://github.com/xypep/LinuxMos)"
API = "https://lrclib.net/api/get?"
LYRICS_DIR = CACHE_DIR / "lyrics"
_LINE = re.compile(r"\[(\d+):(\d+(?:\.\d+)?)\](.*)")


def parse_lrc(text):
    """LRC text -> sorted [(time_us, line)]. Empty lines are kept as pauses."""
    lines = []
    for raw in (text or "").splitlines():
        stamps = []
        rest = raw
        while True:
            m = _LINE.match(rest)
            if not m:
                break
            stamps.append((int(m.group(1)) * 60 + float(m.group(2))) * 1_000_000)
            rest = m.group(3)
        for stamp in stamps:
            lines.append((int(stamp), rest.strip()))
    return sorted(lines)


def line_index(lines, position_us):
    """Index of the line being sung at position_us (-1 before the first)."""
    lo, hi = 0, len(lines)
    while lo < hi:
        mid = (lo + hi) // 2
        if lines[mid][0] <= position_us:
            lo = mid + 1
        else:
            hi = mid
    return lo - 1


class LyricsFetcher:
    def __init__(self):
        self._memory = {}
        self._pending = set()

    @staticmethod
    def key(track):
        return hashlib.sha1(f"{track.artist}|{track.title}|{track.length_us // 1_000_000}".encode()).hexdigest()

    def get(self, track, callback):
        """callback(lines or [], plain_text_or_None) on the main loop."""
        key = self.key(track)
        if key in self._memory:
            callback(*self._memory[key])
            return
        if key in self._pending:
            return
        self._pending.add(key)
        threading.Thread(target=self._worker, args=(track, key, callback), daemon=True).start()

    def _worker(self, track, key, callback):
        path = LYRICS_DIR / f"{key}.json"
        data = None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            try:
                query = {"track_name": track.title, "artist_name": track.artist}
                if track.length_us:
                    query["duration"] = round(track.length_us / 1_000_000)
                req = urllib.request.Request(API + urllib.parse.urlencode(query),
                                             headers={"User-Agent": USER_AGENT})
                with urllib.request.urlopen(req, timeout=8) as resp:
                    found = json.load(resp)
                data = {"synced": found.get("syncedLyrics") or "", "plain": found.get("plainLyrics") or ""}
            except urllib.error.HTTPError as exc:
                data = {"synced": "", "plain": ""} if exc.code == 404 else None
            except (OSError, ValueError):
                data = None  # offline: don't cache, try again next time
            if data is not None:
                LYRICS_DIR.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(data), encoding="utf-8")
        GLib.idle_add(self._deliver, key, data, callback)

    def _deliver(self, key, data, callback):
        self._pending.discard(key)
        if data is None:
            callback([], None)
        else:
            result = (parse_lrc(data["synced"]), data["plain"] or None)
            self._memory[key] = result
            callback(*result)
        return GLib.SOURCE_REMOVE
