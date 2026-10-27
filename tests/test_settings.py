"""The settings window's rules: validation of every kind of input, saving, hotkey changes, /proc numbers."""

import json
import os
import tempfile
import unittest
from pathlib import Path

from tests import _sandbox  # noqa: F401  (must come first)
from island import settingsmeta as meta
from island.settingslogic import Store, action_choices, action_label, proc_stats
from island import registry
from island.storage import Config


def ok(key, value):
    return meta.validate(key, value)[0]


class Validation(unittest.TestCase):
    def test_numbers_are_checked_against_their_range(self):
        self.assertTrue(ok("offset_y", 6))
        self.assertTrue(ok("offset_y", "12"))
        self.assertFalse(ok("offset_y", 301))
        self.assertFalse(ok("offset_y", -1))
        self.assertFalse(ok("offset_y", "abc"))
        self.assertFalse(ok("offset_y", 2.5))                       # an integer field
        self.assertFalse(ok("offset_y", True))
        self.assertFalse(ok("offset_y", float("nan")))
        self.assertEqual(meta.validate("eye_mode_scale", "2,5"), (True, 2.5, ""))
        self.assertFalse(ok("eye_mode_scale", 3.1))
        self.assertTrue(ok("keepawake_minutes", 0))
        self.assertFalse(ok("colorpicker_history", 0))

    def test_the_message_names_the_range(self):
        self.assertEqual(meta.validate("water_interval_min", 5)[2], "Zwischen 15 und 1440")
        self.assertEqual(meta.validate("eye_mode_scale", 9)[2], "Zwischen 1,5 und 3")

    def test_booleans_and_choices(self):
        self.assertTrue(ok("osd", False))
        self.assertFalse(ok("osd", "yes"))
        self.assertTrue(ok("colorpicker_format", "hsl"))
        self.assertFalse(ok("colorpicker_format", "cmyk"))
        self.assertTrue(ok("record_audio", "mic"))
        self.assertFalse(ok("language", "fr"))

    def test_free_choices(self):
        self.assertEqual(meta.validate("monitor", "2"), (True, 2, ""))
        self.assertEqual(meta.validate("monitor", "HDMI-1"), (True, "HDMI-1", ""))
        self.assertTrue(ok("command_bar_engine", "https://de.wikipedia.org/w/index.php?search=%s"))
        self.assertFalse(ok("command_bar_engine", "https://example.org/"))
        self.assertTrue(ok("command_bar_engine", "google"))

    def test_times_urls_and_languages(self):
        self.assertTrue(ok("water_start", "09:00"))
        for bad in ("9:00", "24:00", "09:60", "morgens", ""):
            self.assertFalse(ok("water_start", bad), bad)
        self.assertEqual(meta.validate("ai_base_url", "http://localhost:11434/v1/")[1], "http://localhost:11434/v1")
        self.assertFalse(ok("ai_base_url", "localhost:11434"))
        self.assertTrue(ok("ai_base_url", ""))                       # optional: OpenAI
        self.assertTrue(ok("ocr_languages", "deu+eng"))
        self.assertFalse(ok("ocr_languages", "deu eng"))
        self.assertFalse(ok("ocr_languages", ""))                    # not optional

    def test_the_tracking_list_takes_commas(self):
        self.assertEqual(meta.validate("clipactions_tracking_params", "affil, partner_* ,, x")[1],
                         ["affil", "partner_*", "x"])
        self.assertEqual(meta.validate("clipactions_tracking_params", "")[1], [])

    def test_unknown_keys_and_wrong_types(self):
        self.assertFalse(ok("no_such_key", 1))
        self.assertFalse(ok("city", 5))
        self.assertTrue(ok("city", ""))

    def test_every_default_passes_its_own_validation(self):
        from island.storage import DEFAULT_CONFIG
        for key in meta.FIELDS:
            self.assertTrue(ok(key, DEFAULT_CONFIG[key]), key)


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.path = Config.PATH
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps({"city": "Köln", "stranger": {"a": 1}}), encoding="utf-8")
        self.store = Store(keys_factory=FakeKeys)
        FakeKeys.instances = []

    def read(self):
        return json.loads(self.path.read_text(encoding="utf-8"))

    def test_a_valid_value_is_saved_and_the_rest_of_the_file_stays(self):
        self.assertEqual(self.store.set_value("osd", False), (True, ""))
        data = self.read()
        self.assertEqual((data["osd"], data["city"], data["stranger"]), (False, "Köln", {"a": 1}))
        self.assertNotIn("stretch_enabled", data)                    # only what changed

    def test_an_invalid_value_is_refused_and_the_file_is_untouched(self):
        before = self.path.read_text(encoding="utf-8")
        ok_, message = self.store.set_value("offset_y", 9999)
        self.assertFalse(ok_)
        self.assertIn("Zwischen", message)
        self.assertEqual(self.path.read_text(encoding="utf-8"), before)

    def test_a_broken_file_is_never_overwritten(self):
        self.path.write_text('{"city": ', encoding="utf-8")
        with self.assertLogs("mosisland.config", "WARNING"):
            store = Store(keys_factory=FakeKeys)
        self.assertIsNotNone(store.error)
        self.assertFalse(store.set_value("osd", False)[0])
        self.assertFalse(store.set_gesture("click_middle", "none")[0])
        self.assertFalse(store.set_hotkey("clipboard", "<Primary><Alt>b", "/bin")[0])
        self.assertEqual(self.path.read_text(encoding="utf-8"), '{"city": ')

    def test_gestures_are_stored_only_when_they_differ_from_the_default(self):
        self.assertTrue(self.store.set_gesture("click_double", "play_pause")[0])
        self.assertEqual(self.read()["gestures"], {"click_double": "play_pause"})
        self.assertTrue(self.store.set_gesture("click_double", "none")[0])            # the default again
        self.assertEqual(self.read()["gestures"], {})
        self.assertFalse(self.store.set_gesture("click_middle", "volume_wheel")[0])   # a wheel action for a click
        self.assertFalse(self.store.set_gesture("click_middle", "tab:nowhere")[0])
        self.assertTrue(self.store.set_gesture("wheel_left", "function:color-picker")[0])
        self.assertEqual(self.store.gesture_map()["wheel_left"], "function:color-picker")

    def test_hotkey_change_goes_to_the_config_and_to_cinnamon(self):
        self.assertEqual(self.store.set_hotkey("clipboard", "<Control><Alt>b", "/home/u/.local/bin"), (True, ""))
        self.assertEqual(self.read()["hotkeys"], {"clipboard": "<Primary><Alt>b"})
        written = FakeKeys.instances[-1].written
        self.assertEqual(written, [("MosIsland Zwischenablage (LinuxMos)",
                                    "/home/u/.local/bin/linuxmos-island --tab clipboard", "<Primary><Alt>b",
                                    "--tab clipboard")])

    def test_the_default_is_stored_as_not_changed_and_reset_goes_back_to_it(self):
        self.store.set_hotkey("clipboard", "<Primary><Alt>b", "/b")
        self.assertEqual(self.store.reset_hotkey("clipboard", "/b"), (True, ""))
        self.assertEqual(self.read()["hotkeys"], {})
        self.assertEqual(FakeKeys.instances[-1].written[-1][2], "<Primary><Alt>v")

    def test_a_hotkey_can_be_removed(self):
        self.assertTrue(self.store.set_hotkey("clipboard", "", "/b")[0])
        self.assertEqual(self.read()["hotkeys"], {"clipboard": ""})
        self.assertEqual(FakeKeys.instances[-1].written[-1][2], "")

    def test_hotkey_rules(self):
        self.assertFalse(self.store.set_hotkey("todo", "<Primary><Alt>b", "/b")[0])            # no hotkey for this one
        self.assertFalse(self.store.set_hotkey("nope", "<Primary><Alt>b", "/b")[0])
        self.assertFalse(self.store.set_hotkey("clipboard", "garbage<", "/b")[0])

    def test_conflicts_name_the_other_function_and_system_shortcuts(self):
        self.assertEqual(self.store.conflict("color-picker", "<Primary><Alt>v"), "Zwischenablage-Verlauf")
        self.assertEqual(self.store.conflict("clipboard", "<Control><Alt>V"), None)        # its own key is no conflict
        self.assertEqual(self.store.conflict("color-picker", "<Primary><Alt>t"), "Cinnamon: terminal")
        self.assertEqual(self.store.conflict("color-picker", "<Primary><Alt>u"), None)
        # a hotkey given to one function now clashes for the others
        self.store.set_hotkey("keep-awake", "<Primary><Alt>u", "/b")
        self.assertEqual(self.store.conflict("color-picker", "<Primary><Alt>u"), "Wach halten")

    def test_without_cinnamon_the_hotkey_is_still_saved(self):
        store = Store(keys_factory=lambda: FakeKeys(available=False))
        ok_, message = store.set_hotkey("clipboard", "<Primary><Alt>b", "/b")
        self.assertTrue(ok_)
        self.assertIn("nicht erreichbar", message)
        self.assertEqual(self.read()["hotkeys"], {"clipboard": "<Primary><Alt>b"})


class FakeKeys:
    instances = []

    def __init__(self, available=True):
        self.available = available
        self.written = []
        FakeKeys.instances.append(self)

    def entries(self):
        return [{"id": "custom0", "name": "Mein Kürzel", "command": "x", "binding": ["<Primary><Alt>w"]}]

    def system_bindings(self):
        return [("<Primary><Alt>t", "Cinnamon: terminal")]

    def set_binding(self, name, command, accel, tail=None):
        self.written.append((name, command, accel, tail))
        return True


class Labels(unittest.TestCase):
    def test_action_labels_and_choices(self):
        names = {"color-picker": "Farbpipette"}
        self.assertEqual(action_label("volume_wheel", names), "Lautstärke ± (Mausrad)")
        self.assertEqual(action_label("tab:clipboard", names), "Tab öffnen: Zwischenablage")
        self.assertEqual(action_label("function:color-picker", names), "Funktion: Farbpipette")
        reg = registry.build()
        wheel = dict(action_choices("wheel", reg))
        click = dict(action_choices("click_middle", reg))
        self.assertIn("volume_wheel", wheel)
        self.assertNotIn("default", wheel)
        self.assertNotIn("volume_wheel", click)
        self.assertIn("volume_up", click)
        self.assertIn("function:keep-awake", click)
        self.assertIn("tab:tools", click)


class ProcStats(unittest.TestCase):
    def test_reads_a_fake_proc_tree(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "42").mkdir()
            hz = os.sysconf("SC_CLK_TCK")
            fields = ["S", "1"] + ["0"] * 9 + [str(hz * 3), str(hz * 1)] + ["0"] * 6 + [str(hz * 100)] + ["0"] * 5
            (root / "42" / "stat").write_text("42 (linuxmos-island) " + " ".join(fields))
            (root / "uptime").write_text("160.00 100.00")
            (root / "42" / "smaps_rollup").write_text("Rss:   61440 kB\nPss:   43008 kB\n")
            stats = proc_stats(42, root)
            self.assertAlmostEqual(stats["cpu_avg"], 100.0 * 4 / 60, places=3)     # 4 s of CPU in the 60 s it lived
            self.assertEqual((stats["rss_mb"], stats["pss_mb"]), (60.0, 42.0))

    def test_a_process_that_is_gone_gives_none(self):
        self.assertIsNone(proc_stats(2 ** 22 + 7))

    def test_the_real_thing_for_this_process(self):
        stats = proc_stats(os.getpid())
        self.assertIsNotNone(stats)
        self.assertGreater(stats["rss_mb"], 1)


if __name__ == "__main__":
    unittest.main()
