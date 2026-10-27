"""Gestures: defaults reproduce the old behaviour, classification, config resolution."""

import unittest

from tests import _sandbox  # noqa: F401  (must come first)
from island import gestures as g

TABS = [name for name, _ in g.TABS]
FUNCTIONS = ["color-picker", "keep-awake"]


class Defaults(unittest.TestCase):
    def test_the_defaults_are_what_the_island_always_did(self):
        mapping = g.resolve({}, TABS, FUNCTIONS)
        self.assertEqual(mapping["wheel"], "volume_wheel")                 # wheel on the pill: volume +-5 %
        self.assertEqual((g.VOLUME_STEP, mapping["click_middle"], mapping["click_right"]), (5, "expand", "expand"))
        self.assertEqual(mapping["click_double"], "none")
        for gesture in ("wheel_shift", "wheel_ctrl", "wheel_left", "wheel_right"):
            self.assertEqual(g.action_for(gesture, mapping), "volume_wheel", gesture)   # modifiers and edges did it too

    def test_a_changed_wheel_carries_the_specific_gestures_along(self):
        mapping = g.resolve({"wheel": "brightness_wheel", "wheel_shift": "tab_wheel"}, TABS, FUNCTIONS)
        self.assertEqual(g.action_for("wheel_left", mapping), "brightness_wheel")
        self.assertEqual(g.action_for("wheel_shift", mapping), "tab_wheel")


class Resolve(unittest.TestCase):
    def test_unusable_entries_fall_back_to_the_default(self):
        section = {"wheel": "fly_to_the_moon", "click_middle": "volume_wheel",       # a wheel action for a click
                   "click_right": 5, "click_double": "tab:nowhere", "wheel_left": "function:nope",
                   "unknown_gesture": "expand", "wheel_shift": "none"}
        mapping = g.resolve(section, TABS, FUNCTIONS)
        self.assertEqual((mapping["wheel"], mapping["click_middle"], mapping["click_right"], mapping["click_double"]),
                         ("volume_wheel", "expand", "expand", "none"))
        self.assertEqual(mapping["wheel_left"], "default")
        self.assertEqual(mapping["wheel_shift"], "none")
        self.assertNotIn("unknown_gesture", mapping)

    def test_tab_and_function_targets(self):
        mapping = g.resolve({"click_double": "tab:clipboard", "click_middle": "function:color-picker"}, TABS, FUNCTIONS)
        self.assertEqual((mapping["click_double"], mapping["click_middle"]), ("tab:clipboard", "function:color-picker"))

    def test_the_plain_wheel_cannot_be_set_to_default(self):
        self.assertEqual(g.resolve({"wheel": "default"}, TABS, FUNCTIONS)["wheel"], "volume_wheel")

    def test_a_config_that_is_not_a_dict_is_empty(self):
        self.assertEqual(g.resolve(["x"], TABS, FUNCTIONS), g.resolve({}, TABS, FUNCTIONS))
        self.assertEqual(g.resolve(None, TABS, FUNCTIONS), g.resolve({}, TABS, FUNCTIONS))


class Classify(unittest.TestCase):
    def test_modifiers_beat_edges_and_edges_beat_the_middle(self):
        self.assertEqual(g.classify_wheel(g.SHIFT, 100, 200), "wheel_shift")
        self.assertEqual(g.classify_wheel(g.CTRL, 100, 200), "wheel_ctrl")
        self.assertEqual(g.classify_wheel(g.SHIFT | g.CTRL, 5, 200), "wheel_shift")
        self.assertEqual(g.classify_wheel(0, 10, 200), "wheel_left")
        self.assertEqual(g.classify_wheel(0, 195, 200), "wheel_right")
        self.assertEqual(g.classify_wheel(0, 100, 200), "wheel")

    def test_a_tiny_pill_has_no_edges(self):
        self.assertEqual(g.classify_wheel(0, 3, 40), "wheel")

    def test_buttons(self):
        self.assertIsNone(g.classify_click(1))               # left is not a gesture: it always opens the island
        self.assertEqual(g.classify_click(2), "click_middle")
        self.assertEqual(g.classify_click(3), "click_right")
        self.assertIsNone(g.classify_click(8))


class Helpers(unittest.TestCase):
    def test_smooth_scrolling_collects_until_one_step(self):
        s = g.Scroll()
        self.assertEqual([s.add(0.4), s.add(0.4), s.add(0.4)], [0, 0, -1])      # three small steps down = one down
        self.assertEqual(s.add(-1.0), 1)                                          # up
        self.assertEqual(s.add(0.2), 0)

    def test_next_in_wraps_around(self):
        self.assertEqual(g.next_in(["a", "b", "c"], "c", 1), "a")
        self.assertEqual(g.next_in(["a", "b", "c"], "a", -1), "c")
        self.assertEqual(g.next_in(["a", "b"], "zzz", 1), "a")
        self.assertIsNone(g.next_in([], "a", 1))


if __name__ == "__main__":
    unittest.main()
