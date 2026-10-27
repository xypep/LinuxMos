"""Synced lyrics from LRCLIB (lrclib.net, free, no key) with a small disk cache.

Only the song title, artist, album and length are sent, and only while the
lyrics are actually shown (lyrics view open or lyrics-in-pill enabled).
"""

import json
import re
import urllib.parse

from gi.repository import GLib

from island.services import http
from island.storage import CACHE_DIR

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
        # GLib's SHA-1 (same names as hashlib's): hashlib would load OpenSSL's libcrypto
        return GLib.compute_checksum_for_string(GLib.ChecksumType.SHA1,
                                                f"{track.artist}|{track.title}|{track.length_us // 1_000_000}", -1)

    def get(self, track, callback):
        """callback(lines or [], plain_text_or_None) on the main loop."""
        key = self.key(track)
        if key in self._memory:
            callback(*self._memory[key])
            return
        if key in self._pending:
            return
        self._pending.add(key)
        path = LYRICS_DIR / f"{key}.json"
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            data = None
        if isinstance(data, dict):
            self._deliver(key, data, callback)
            return
        query = {"track_name": track.title, "artist_name": track.artist}
        if track.length_us:
            query["duration"] = round(track.length_us / 1_000_000)

        def done(status, found):
            if status == 404:
                data = {"synced": "", "plain": ""}   # LRCLIB doesn't know the song
            elif status == 200 and isinstance(found, dict):
                data = {"synced": found.get("syncedLyrics") or "", "plain": found.get("plainLyrics") or ""}
            else:
                data = None   # offline: don't cache, try again next time
            if data is not None:
                try:
                    LYRICS_DIR.mkdir(parents=True, exist_ok=True)
                    path.write_text(json.dumps(data), encoding="utf-8")
                except OSError:
                    pass
            self._deliver(key, data, callback)

        http.get_json(API + urllib.parse.urlencode(query), done, timeout=8)

    def _deliver(self, key, data, callback):
        self._pending.discard(key)
        if data is None:
            callback([], None)
        else:
            result = (parse_lrc(data.get("synced")), data.get("plain") or None)
            self._memory[key] = result
            callback(*result)
