"""`linuxmos-island --list-actions` and `--check-hotkeys` with no island running and no gsettings: the definitions and the config."""

import io
import json
import unittest
from unittest import mock

from tests import _sandbox  # noqa: F401  (must come first)
from island import cli, registry
from island.storage import Config


class Case(unittest.TestCase):
    def setUp(self):
        Config.PATH.parent.mkdir(parents=True, exist_ok=True)
        Config.PATH.unlink(missing_ok=True)
        patch = mock.patch.object(cli, "_cinnamon_state", return_value=(None, []))
        patch.start()
        self.addCleanup(patch.stop)
        # no island on the bus: what _rows() falls back to
        rows = mock.patch.object(cli, "_rows", side_effect=lambda config: (registry.build().rows(config), False))
        rows.start()
        self.addCleanup(rows.stop)

    def run_cli(self, func, *args):
        out = io.StringIO()
        code = func(*args, out=out)
        return code, out.getvalue()


class ListActions(Case):
    def test_every_function_is_in_the_table(self):
        code, text = self.run_cli(cli.list_actions, ["--list-actions"])
        self.assertEqual(code, 0)
        for fid in registry.build().ids():
            self.assertIn(fid, text)
        self.assertIn("MosIsland läuft nicht", text)
        self.assertIn("Ctrl+Alt+Shift+V", text)

    def test_the_table_shows_the_switch_and_the_hotkey_of_the_config(self):
        Config.PATH.write_text(json.dumps({"keepawake_enabled": False, "hotkeys": {"color-picker": "<Control><Alt>b"}}))
        _code, text = self.run_cli(cli.list_actions, ["--list-actions"])
        line = [row for row in text.splitlines() if row.startswith("keep-awake")][0]
        self.assertIn("keepawake_enabled=aus", line)
        picker = [row for row in text.splitlines() if row.startswith("color-picker")][0]
        self.assertIn("Ctrl+Alt+B", picker)

    def test_markdown_is_the_hotkey_table_of_the_readme(self):
        _code, text = self.run_cli(cli.list_actions, ["--list-actions", "--markdown"])
        lines = text.strip().splitlines()
        self.assertEqual(lines[0], "| Hotkey | Funktion | Aufruf |")
        self.assertIn("| `Ctrl+Alt+C` | Farbpipette | `linuxmos-island --action color-picker` |", lines)
        self.assertNotIn("Marker", text)


class CheckHotkeys(Case):
    def test_the_shipped_defaults_are_free(self):
        code, text = self.run_cli(cli.check_hotkeys)
        self.assertEqual(code, 0)
        self.assertIn("Keine Konflikte", text)

    def test_two_functions_on_one_key_are_reported(self):
        Config.PATH.write_text(json.dumps({"hotkeys": {"keep-awake": "<Primary><Alt>v"}}))
        code, text = self.run_cli(cli.check_hotkeys)
        self.assertEqual(code, 1)
        self.assertIn("KONFLIKT Ctrl+Alt+V: Zwischenablage-Verlauf ↔ Wach halten", text)

    def test_a_system_shortcut_is_reported(self):
        with mock.patch.object(cli, "_cinnamon_state", return_value=(None, [("<Control><Alt>t", "Cinnamon: terminal")])):
            Config.PATH.write_text(json.dumps({"hotkeys": {"keep-awake": "<Primary><Alt>t"}}))
            code, text = self.run_cli(cli.check_hotkeys)
        self.assertEqual(code, 1)
        self.assertIn("Wach halten ↔ Cinnamon: terminal", text)

    def test_a_switched_off_hotkey_is_no_conflict(self):
        Config.PATH.write_text(json.dumps({"hotkeys": {"keep-awake": "", "color-picker": ""}}))
        self.assertEqual(self.run_cli(cli.check_hotkeys)[0], 0)


if __name__ == "__main__":
    unittest.main()
