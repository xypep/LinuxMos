"""config.json handling: defaults, reload, atomic save, nothing of the user's is lost."""

import json
import unittest

from tests import _sandbox  # noqa: F401  (must come first)
from island import storage


class ConfigFile(unittest.TestCase):
    def setUp(self):
        self.path = storage.CONFIG_DIR / "config.json"
        self.path.unlink(missing_ok=True)

    def write(self, data):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(data if isinstance(data, str) else json.dumps(data), encoding="utf-8")

    def read(self):
        return json.loads(self.path.read_text(encoding="utf-8"))

    def test_old_file_gets_new_keys_as_defaults_and_keeps_user_values(self):
        self.write({"city": "Köln", "mascot_style": "cat", "something_new": [1, 2]})
        cfg = storage.Config.load()
        self.assertEqual((cfg["city"], cfg["mascot_style"]), ("Köln", "cat"))
        self.assertTrue(cfg["stretch_enabled"])
        self.assertEqual((cfg["stretch_interval_min"], cfg["eye_mode_scale"]), (45, 2.0))
        self.assertEqual(cfg["something_new"], [1, 2])

    def test_save_writes_only_our_changes_and_keeps_edits_and_unknown_keys(self):
        self.write({"city": "Köln", "unknown_key": {"a": 1}})
        cfg = storage.Config.load()
        self.path.write_text(json.dumps({"city": "Köln", "unknown_key": {"a": 1}, "osd": False}), encoding="utf-8")
        cfg["mascot_style"] = "robot"          # we change one key, the user edited another one meanwhile
        self.assertTrue(cfg.save())
        data = self.read()
        self.assertEqual((data["mascot_style"], data["osd"], data["unknown_key"]), ("robot", False, {"a": 1}))
        self.assertNotIn("stretch_enabled", data)

    def test_save_is_atomic_no_tmp_left(self):
        cfg = storage.Config.load()
        cfg["offset_y"] = 9
        cfg.save()
        self.assertEqual(self.read()["offset_y"], 9)
        self.assertEqual([p.name for p in self.path.parent.iterdir() if p.name.endswith(".tmp")], [])

    def test_reload_reports_what_changed_and_resets_removed_keys(self):
        self.write({"osd": False, "mascot": False})
        cfg = storage.Config.load()
        self.write({"osd": False, "eye_mode_scale": 2.5})
        changed, error = cfg.reload()
        self.assertIsNone(error)
        self.assertEqual(sorted(changed), ["eye_mode_scale", "mascot"])
        self.assertTrue(cfg["mascot"])
        self.assertEqual(cfg["eye_mode_scale"], 2.5)
        self.assertEqual(cfg.reload(), ([], None))

    def test_broken_json_keeps_old_values_names_the_place_and_blocks_saving(self):
        self.write({"osd": False})
        cfg = storage.Config.load()
        self.write('{\n "osd": true,\n "mascot": \n}')
        changed, error = cfg.reload()
        self.assertEqual(changed, [])
        self.assertIn("Zeile 4", error)
        self.assertFalse(cfg["osd"])
        cfg["offset_y"] = 12
        self.assertFalse(cfg.save())
        self.assertIn('"mascot":', self.path.read_text(encoding="utf-8"))   # the user's text is untouched
        self.write({"osd": True})
        changed, error = cfg.reload()
        self.assertEqual(sorted(changed), ["offset_y", "osd"])      # the unsaved offset_y change gives way to the file
        self.assertEqual(cfg["offset_y"], 6)
        self.assertIsNone(error)
        self.assertIsNone(cfg.error)

    def test_a_list_instead_of_an_object_is_an_error(self):
        self.write("[1, 2]")
        self.assertIsNotNone(storage.Config.load().error)

    def test_fill_defaults_adds_missing_keys_only(self):
        self.write({"city": "Bonn", "zzz": 1, "stretch_interval_min": 30})
        cfg = storage.Config.load()
        self.assertTrue(cfg.fill_defaults())
        data = self.read()
        self.assertEqual((data["city"], data["stretch_interval_min"], data["zzz"]), ("Bonn", 30, 1))
        self.assertEqual(set(storage.DEFAULT_CONFIG) - set(data), set())
        self.assertEqual(list(data)[-1], "zzz")
        before = self.path.read_text(encoding="utf-8")
        cfg.fill_defaults()
        self.assertEqual(self.path.read_text(encoding="utf-8"), before)

    def test_fill_defaults_leaves_a_broken_file_alone(self):
        self.write("{ nope")
        self.assertFalse(storage.Config.load().fill_defaults())
        self.assertEqual(self.path.read_text(encoding="utf-8"), "{ nope")

    def test_values_are_clamped_and_wrong_types_fall_back(self):
        cfg = storage.Config(storage.DEFAULT_CONFIG)
        for given, expected in ((9, 3.0), (0.2, 1.5), (2.2, 2.2), ("big", 2.0), (None, 2.0), (True, 2.0)):
            cfg["eye_mode_scale"] = given
            self.assertEqual(cfg.number("eye_mode_scale", 1.5, 3.0), expected, given)
        cfg["stretch_volume"] = 7
        self.assertEqual(cfg.number("stretch_volume", 0, 1), 1.0)
        cfg["stretch_interval_min"] = "x"
        self.assertEqual(cfg.integer("stretch_interval_min", 1, 600), 45)
        cfg["stretch_enabled"] = "yes"
        self.assertTrue(cfg.flag("stretch_enabled"))


if __name__ == "__main__":
    unittest.main()
