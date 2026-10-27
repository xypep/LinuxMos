"""Colours picked from the screen: conversions between the formats and the history file. No GTK in here."""

import colorsys
import time

from island.storage import DATA_DIR, load_json, save_json

HISTORY_FILE = DATA_DIR / "colors.json"
FORMATS = ("hex", "rgb", "hsl", "hsv")
DEFAULT_FORMAT = "hex"
FORMAT_LABELS = {"hex": "HEX", "rgb": "RGB", "hsl": "HSL", "hsv": "HSV"}


def clamp_byte(value):
    return max(0, min(255, int(value)))


def to_hex(rgb):
    return "#{:02X}{:02X}{:02X}".format(*(clamp_byte(c) for c in rgb))


def from_hex(text):
    """'#1A2B3C' / '1a2b3c' / '#abc' -> (r, g, b), or None."""
    text = (text or "").strip().lstrip("#")
    if len(text) == 3:
        text = "".join(c * 2 for c in text)
    if len(text) != 6:
        return None
    try:
        return tuple(int(text[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return None


def to_hsl(rgb):
    """(h 0-360, s %, l %) rounded."""
    h, l, s = colorsys.rgb_to_hls(*(c / 255 for c in rgb))
    return round(h * 360) % 360, round(s * 100), round(l * 100)


def to_hsv(rgb):
    h, s, v = colorsys.rgb_to_hsv(*(c / 255 for c in rgb))
    return round(h * 360) % 360, round(s * 100), round(v * 100)


def fmt(rgb, kind):
    """The colour as text in one of the formats."""
    r, g, b = (clamp_byte(c) for c in rgb)
    if kind == "rgb":
        return f"rgb({r}, {g}, {b})"
    if kind == "hsl":
        h, s, l = to_hsl((r, g, b))
        return f"hsl({h}, {s}%, {l}%)"
    if kind == "hsv":
        h, s, v = to_hsv((r, g, b))
        return f"hsv({h}, {s}%, {v}%)"
    return to_hex((r, g, b))


def all_formats(rgb):
    return {kind: fmt(rgb, kind) for kind in FORMATS}


def format_choice(value):
    return value if value in FORMATS else DEFAULT_FORMAT


class History:
    """The last colours (pinned ones stay), newest first. [{"hex": "#AABBCC", "pinned": false, "time": 0}]"""

    def __init__(self, limit=20, path=HISTORY_FILE):
        self.path = path
        self.limit = max(1, int(limit))
        stored = load_json(path, [])
        self.items = [i for i in stored if isinstance(i, dict) and from_hex(i.get("hex")) is not None] \
            if isinstance(stored, list) else []
        self._trim()

    def add(self, rgb):
        """Put a colour at the top (an old entry of it moves up and keeps its pin)."""
        hex_ = to_hex(rgb)
        pinned = False
        for old in list(self.items):
            if old["hex"].upper() == hex_:
                pinned = bool(old.get("pinned"))
                self.items.remove(old)
        self.items.insert(0, {"hex": hex_, "pinned": pinned, "time": time.time()})
        self._trim()
        self.save()

    def toggle_pin(self, hex_):
        for item in self.items:
            if item["hex"] == hex_:
                item["pinned"] = not item.get("pinned")
        self._trim()
        self.save()

    def set_limit(self, limit):
        self.limit = max(1, int(limit))
        self._trim()

    def _trim(self):
        """At most `limit` unpinned colours; the pinned ones don't count."""
        unpinned = [i for i in self.items if not i.get("pinned")]
        for old in unpinned[self.limit:]:
            self.items.remove(old)

    def ordered(self):
        """Pinned first, then by time."""
        return sorted(self.items, key=lambda i: (not i.get("pinned"), -i.get("time", 0)))

    def save(self):
        save_json(self.path, self.items)

    def clear(self):
        self.items = [i for i in self.items if i.get("pinned")]
        self.save()
