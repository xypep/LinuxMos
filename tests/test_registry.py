"""The register of functions: consistent with the config, the CLI wrapper and the island's tabs."""

import re
import unittest
from pathlib import Path
from unittest import mock

from tests import _sandbox  # noqa: F401  (must come first)
from island import gestures, registry, settingsmeta
from island.storage import DEFAULT_CONFIG, Config

ROOT = Path(__file__).resolve().parent.parent


class Definitions(unittest.TestCase):
    def setUp(self):
        self.reg = registry.build()

    def test_ids_names_and_hotkeys_are_unique(self):
        ids = self.reg.ids()
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len({fn.name for fn in self.reg}), len(ids))
        hot = [fn.default_hotkey for fn in self.reg if fn.default_hotkey]
        self.assertEqual(len(hot), len(set(hot)))
        names = [fn.kb_name for fn in self.reg if fn.kb_name]
        self.assertEqual(len(names), len(set(names)))

    def test_every_enabled_key_is_a_boolean_in_the_defaults(self):
        for fn in self.reg:
            if fn.enabled_key:
                self.assertIn(fn.enabled_key, DEFAULT_CONFIG, fn.id)
                self.assertIsInstance(DEFAULT_CONFIG[fn.enabled_key], bool, fn.id)

    def test_the_new_tools_are_in(self):
        for fid, accel in (("clip-actions", "<Primary><Alt><Shift>v"), ("color-picker", "<Primary><Alt>c"),
                           ("keep-awake", "<Primary><Alt>k"), ("pin-window", "<Primary><Alt>p"),
                           ("settings", "<Primary><Alt>h")):
            self.assertEqual(self.reg.get(fid).default_hotkey, accel)

    def test_the_existing_hotkeys_keep_their_values(self):
        """What install.sh has always bound (it is the same list the README tells)."""
        expected = {"toggle": "<Primary><Alt>i", "clipboard": "<Primary><Alt>v", "search": "<Primary><Alt>space",
                    "screenshot-area": "<Primary><Alt>s", "screenshot-screen": "<Primary><Alt><Shift>s",
                    "ocr": "<Primary><Alt>o", "qr": "<Primary><Alt>q", "record-area": "<Primary><Alt>r",
                    "record-screen": "<Primary><Alt><Shift>r", "chat": "<Primary><Alt>a", "voice": "<Primary><Alt>m",
                    "clip-send": "<Primary><Alt><Shift>t", "spotlight": "<Super>space"}
        for fid, accel in expected.items():
            self.assertEqual(self.reg.get(fid).default_hotkey, accel, fid)

    def test_the_shortcut_names_and_commands_match_install_sh(self):
        install = (ROOT / "install.sh").read_text(encoding="utf-8")
        for fn in self.reg:
            if fn.kb_name and fn.kb_exe == "island":
                self.assertIn(f'"{fn.kb_name}"', install, fn.id)
                self.assertIn(f"linuxmos-island {fn.kb_args}", install, fn.id)

    def test_action_ids_are_known_functions(self):
        self.assertLessEqual(registry.ACTION_IDS, set(self.reg.ids()))

    def test_every_config_key_has_an_input_or_a_reason_not_to(self):
        for key in DEFAULT_CONFIG:
            self.assertTrue(key in settingsmeta.FIELDS or key in settingsmeta.NOT_EDITED, key)
        for key in settingsmeta.FIELDS:
            self.assertIn(key, DEFAULT_CONFIG, key)

    def test_the_gesture_tabs_are_the_islands_tabs(self):
        source = (ROOT / "island" / "app.py").read_text(encoding="utf-8")
        block = source[source.index("TABS = ["):source.index("TERMINALS")]
        self.assertEqual(re.findall(r'\("(\w+)", "[\w-]+", ', block), [name for name, _ in gestures.TABS])

    def test_every_category_is_known_and_the_order_is_stable(self):
        for fn in self.reg:
            self.assertIn(fn.category, registry.CATEGORIES, fn.id)
        self.assertEqual([c for c, _ in self.reg.by_category()][0], "Insel")


class Populate(unittest.TestCase):
    def test_actions_go_to_exactly_the_functions_that_have_one(self):
        reg = registry.REGISTRY
        host = mock.MagicMock()
        host.function_statuses.return_value = {"keep-awake": lambda: (True, "an")}
        try:
            registry.populate(host)
            with_action = {fn.id for fn in reg if fn.action is not None}
            self.assertEqual(with_action, set(registry.ACTION_IDS))
            self.assertIsNotNone(reg.get("keep-awake").status)
            self.assertIsNone(reg.get("todo").status)
        finally:
            for fn in reg:
                fn.action = fn.status = None
            reg.open_tab = None

    def test_run_calls_the_action_and_opens_a_tab_for_the_rest(self):
        reg = registry.REGISTRY
        calls = []
        reg.get("keep-awake").action = lambda: calls.append("awake")
        reg.open_tab = calls.append
        try:
            self.assertEqual(registry.run("keep-awake"), (True, ""))
            self.assertEqual(registry.run("todo"), (True, ""))
            self.assertEqual(calls, ["awake", "todo"])
            self.assertFalse(registry.run("mascot")[0])                  # no action, no tab
            self.assertFalse(registry.run("no-such-function")[0])
            reg.get("keep-awake").action = mock.Mock(side_effect=RuntimeError("boom"))
            with self.assertLogs("mosisland.registry", "ERROR"):
                self.assertEqual(registry.run("keep-awake"), (False, "boom"))   # an action that fails is reported
        finally:
            reg.get("keep-awake").action = None
            reg.open_tab = None

    def test_a_later_feature_can_register_itself(self):
        reg = registry.Registry(registry.definitions())
        reg.register(registry.Function("offline", "Offline-Modus", "Nichts geht ins Netz.", "System",
                                       enabled_key="offline_mode"))
        self.assertIn("offline", reg)
        rows = reg.rows(Config(DEFAULT_CONFIG))
        self.assertEqual([r for r in rows if r["id"] == "offline"][0]["enabled"], False)


class Rows(unittest.TestCase):
    def test_rows_have_the_switch_and_the_hotkey_from_the_config(self):
        cfg = Config(DEFAULT_CONFIG)
        cfg["stretch_enabled"] = False
        cfg["hotkeys"] = {"color-picker": "<Control><Alt>b"}
        rows = {r["id"]: r for r in registry.build().rows(cfg)}
        self.assertEqual(rows["stretch"]["enabled"], False)
        self.assertEqual(rows["color-picker"]["hotkey"], "<Primary><Alt>b")
        self.assertEqual(rows["color-picker"]["default_hotkey"], "<Primary><Alt>c")
        self.assertIsNone(rows["todo"]["enabled"])
        self.assertTrue(rows["screenshot-area"]["hide_window_first"])
        self.assertTrue(rows["reboot"]["dangerous"])

    def test_a_status_that_fails_does_not_break_the_rows(self):
        reg = registry.build()
        reg.get("todo").status = mock.Mock(side_effect=RuntimeError("x"))
        reg.get("water").status = lambda: (True, "Heute 250 ml")
        with self.assertLogs("mosisland.registry", "ERROR"):
            rows = {r["id"]: r for r in reg.rows(Config(DEFAULT_CONFIG), live=True)}
        self.assertEqual(rows["water"]["status"], "Heute 250 ml")
        self.assertIsNone(rows["todo"]["running"])


if __name__ == "__main__":
    unittest.main()
