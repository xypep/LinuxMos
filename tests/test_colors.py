"""Colour conversions and the picker's history file."""

import json
import unittest

from tests import _sandbox  # noqa: F401  (must come first)
from island.services import colors
from island.storage import DATA_DIR


class Conversions(unittest.TestCase):
    def test_formats_of_a_known_colour(self):
        rgb = (26, 43, 60)
        self.assertEqual(colors.all_formats(rgb), {"hex": "#1A2B3C", "rgb": "rgb(26, 43, 60)",
                                                   "hsl": "hsl(210, 40%, 17%)", "hsv": "hsv(210, 57%, 24%)"})

    def test_extremes(self):
        self.assertEqual(colors.fmt((0, 0, 0), "hsl"), "hsl(0, 0%, 0%)")
        self.assertEqual(colors.fmt((255, 255, 255), "hsv"), "hsv(0, 0%, 100%)")
        self.assertEqual(colors.fmt((255, 0, 0), "hsl"), "hsl(0, 100%, 50%)")
        self.assertEqual(colors.fmt((0, 0, 255), "hsv"), "hsv(240, 100%, 100%)")

    def test_hex_parsing(self):
        self.assertEqual(colors.from_hex("#abc"), (170, 187, 204))
        self.assertEqual(colors.from_hex("1A2B3C"), (26, 43, 60))
        for bad in ("", "#12", "#gggggg", None, "#1234567"):
            self.assertIsNone(colors.from_hex(bad))

    def test_unknown_format_falls_back_to_hex(self):
        self.assertEqual(colors.format_choice("rgb"), "rgb")
        self.assertEqual(colors.format_choice("cmyk"), "hex")
        self.assertEqual(colors.format_choice(None), "hex")
        self.assertEqual(colors.fmt((1, 2, 3), "cmyk"), "#010203")

    def test_out_of_range_is_clamped(self):
        self.assertEqual(colors.to_hex((300, -5, 12)), "#FF000C")


class HistoryFile(unittest.TestCase):
    def setUp(self):
        self.path = DATA_DIR / "colors-test.json"
        self.path.unlink(missing_ok=True)

    def test_newest_first_limit_and_dedupe(self):
        history = colors.History(3, self.path)
        for rgb in ((1, 1, 1), (2, 2, 2), (3, 3, 3), (4, 4, 4)):
            history.add(rgb)
        self.assertEqual([i["hex"] for i in history.ordered()], ["#040404", "#030303", "#020202"])
        history.add((2, 2, 2))
        self.assertEqual([i["hex"] for i in history.ordered()], ["#020202", "#040404", "#030303"])

    def test_pinned_stay_and_do_not_count(self):
        history = colors.History(2, self.path)
        history.add((1, 1, 1))
        history.toggle_pin("#010101")
        for n in range(2, 6):
            history.add((n, n, n))
        hexes = [i["hex"] for i in history.ordered()]
        self.assertEqual(hexes[0], "#010101")
        self.assertEqual(len(hexes), 3)               # the pinned one plus two

    def test_saved_and_read_back_and_a_broken_file_is_ignored(self):
        history = colors.History(20, self.path)
        history.add((9, 8, 7))
        self.assertEqual(json.loads(self.path.read_text())[0]["hex"], "#090807")
        self.assertEqual(colors.History(20, self.path).items[0]["hex"], "#090807")
        self.path.write_text("{not json")
        self.assertEqual(colors.History(20, self.path).items, [])
        self.path.write_text(json.dumps([{"hex": "nope"}, 5, {"hex": "#112233", "pinned": True}]))
        self.assertEqual([i["hex"] for i in colors.History(20, self.path).items], ["#112233"])

    def test_lowering_the_limit_drops_old_unpinned_entries(self):
        history = colors.History(20, self.path)
        for n in range(1, 6):
            history.add((n, n, n))
        history.set_limit(2)
        self.assertEqual(len(history.items), 2)


if __name__ == "__main__":
    unittest.main()
