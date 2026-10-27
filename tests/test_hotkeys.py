"""Accelerators, conflicts, and the bridge to Cinnamon's custom shortcuts (gsettings, in memory)."""

import os
import unittest

from tests import _sandbox  # noqa: F401  (must come first)
from island import hotkeys, registry
from island.storage import Config

try:
    os.environ.setdefault("GSETTINGS_BACKEND", "memory")        # never touch the real dconf
    from gi.repository import Gio  # noqa: F401
    HAVE_GI = True
except (ImportError, ValueError):
    HAVE_GI = False


class Accelerators(unittest.TestCase):
    def test_spellings_of_the_same_shortcut_are_equal(self):
        spellings = ["<Primary><Alt>v", "<Control><Alt>V", "<Alt><Ctrl>v", "<Mod1><Primary>v"]
        self.assertEqual(len({hotkeys.normalize(s) for s in spellings}), 1)
        self.assertEqual(hotkeys.normalize("<Control><Alt>V"), "<Primary><Alt>v")

    def test_shift_and_special_keys(self):
        self.assertEqual(hotkeys.normalize("<Alt><Shift><Primary>t"), "<Primary><Alt><Shift>t")
        self.assertEqual(hotkeys.normalize("<Super>space"), "<Super>space")
        self.assertEqual(hotkeys.normalize("<Primary><Alt>f5"), "<Primary><Alt>F5")
        self.assertEqual(hotkeys.normalize("<Primary><Alt>Delete"), "<Primary><Alt>Delete")

    def test_pretty(self):
        self.assertEqual(hotkeys.pretty("<Primary><Alt><Shift>v"), "Ctrl+Alt+Shift+V")
        self.assertEqual(hotkeys.pretty("<Primary><Alt>space"), "Ctrl+Alt+Space")
        self.assertEqual(hotkeys.pretty("<Super>space"), "Super+Space")
        self.assertEqual(hotkeys.pretty("nonsense<"), "")

    def test_rubbish_is_not_an_accelerator(self):
        for bad in ("", None, "<Primary>", "<Nope>v", "<Primary><Alt>", "<Primary>a b", 5, "<Primary>v>"):
            self.assertIsNone(hotkeys.parse(bad), bad)


class Conflicts(unittest.TestCase):
    def test_two_of_ours_on_one_key(self):
        ours = {"a": ("Alpha", "<Primary><Alt>x"), "b": ("Beta", "<Control><Alt>X"), "c": ("Gamma", "<Super>q")}
        found = hotkeys.find_conflicts(ours)
        self.assertEqual([(c.first, c.second, c.system) for c in found], [("Alpha", "Beta", False)])

    def test_against_the_system(self):
        ours = {"a": ("Alpha", "<Primary><Alt>t")}
        found = hotkeys.find_conflicts(ours, [("<Primary><Alt>t", "Cinnamon: terminal")])
        self.assertEqual([(c.second, c.system) for c in found], [("Cinnamon: terminal", True)])

    def test_conflict_for_ignores_the_function_itself(self):
        ours = {"a": ("Alpha", "<Primary><Alt>x"), "b": ("Beta", "<Primary><Alt>y")}
        self.assertIsNone(hotkeys.conflict_for("<Primary><Alt>x", "a", ours))
        self.assertEqual(hotkeys.conflict_for("<Primary><Alt>y", "a", ours), "Beta")
        self.assertEqual(hotkeys.conflict_for("<Primary><Alt>l", "a", ours, [("<Control><Alt>l", "Sperren")]), "Sperren")

    def test_the_shipped_defaults_do_not_clash(self):
        reg = registry.build()
        ours = reg.ours(Config(Config.load()))
        self.assertGreater(len(ours), 15)
        clashes = hotkeys.find_conflicts(ours, [(a, f"Mint: {n}") for a, n in hotkeys.MINT_DEFAULTS])
        self.assertEqual(clashes, [])


@unittest.skipUnless(HAVE_GI, "needs PyGObject")
class CinnamonBridge(unittest.TestCase):
    def setUp(self):
        keys = hotkeys.CinnamonKeys()
        if not keys.available:
            self.skipTest("Cinnamon's keybinding schema is not installed")
        self.keys = keys
        keys._root.reset("custom-list")

    def test_a_missing_shortcut_is_created_and_changed_in_place(self):
        self.assertTrue(self.keys.set_binding("MosIsland Test (LinuxMos)", "/bin/x --test", "<Primary><Alt>j"))
        entries = self.keys.entries()
        self.assertEqual([(e["name"], e["command"], e["binding"]) for e in entries],
                         [("MosIsland Test (LinuxMos)", "/bin/x --test", ["<Primary><Alt>j"])])
        self.assertFalse(self.keys.set_binding("MosIsland Test (LinuxMos)", "/bin/x --test", "<Primary><Alt>j"))
        self.assertTrue(self.keys.set_binding("MosIsland Test (LinuxMos)", "/bin/x --test", "<Primary><Alt>k"))
        self.assertEqual(len(self.keys.entries()), 1)
        self.assertEqual(self.keys.entries()[0]["binding"], ["<Primary><Alt>k"])

    def test_the_users_path_to_the_program_is_kept_and_an_empty_binding_turns_it_off(self):
        self.keys.set_binding("MosIsland Test (LinuxMos)", "/home/u/.local/bin/linuxmos-island --tab x",
                              "<Primary><Alt>j")
        self.keys.set_binding("MosIsland Test (LinuxMos)", "/usr/bin/linuxmos-island --tab x", "", "--tab x")
        entry = self.keys.entries()[0]
        self.assertEqual((entry["command"], entry["binding"]), ("/home/u/.local/bin/linuxmos-island --tab x", []))

    def test_an_entry_is_found_by_its_command_when_the_name_differs(self):
        self.keys.set_binding("Old name", "/x/linuxmos-island --action keep-awake", "<Primary><Alt>k")
        self.assertTrue(self.keys.set_binding("MosIsland Wach halten (LinuxMos)", "/y/linuxmos-island --action keep-awake",
                                              "<Primary><Alt>w", "--action keep-awake"))
        self.assertEqual(len(self.keys.entries()), 1)

    def test_system_bindings_are_listed(self):
        found = self.keys.system_bindings()
        self.assertTrue(any(hotkeys.same(a, "<Primary><Alt>t") for a, _ in found))      # the terminal
        self.assertFalse(any(label.endswith("custom-list") for _a, label in found))


class EffectiveHotkey(unittest.TestCase):
    def setUp(self):
        self.fn = registry.build().get("clipboard")

    def test_default_then_cinnamon_then_config(self):
        cfg = Config()
        self.assertEqual(registry.effective_hotkey(self.fn, cfg), "<Primary><Alt>v")
        entries = [{"id": "custom0", "name": self.fn.kb_name, "command": "x --tab clipboard",
                    "binding": ["<Super>v"]}]
        self.assertEqual(registry.effective_hotkey(self.fn, cfg, entries), "<Super>v")
        cfg["hotkeys"] = {"clipboard": "<Control><Alt>b"}
        self.assertEqual(registry.effective_hotkey(self.fn, cfg, entries), "<Primary><Alt>b")
        cfg["hotkeys"] = {"clipboard": ""}
        self.assertEqual(registry.effective_hotkey(self.fn, cfg, entries), "")

    def test_a_shortcut_the_user_switched_off_in_cinnamon_has_no_hotkey(self):
        entries = [{"id": "custom0", "name": self.fn.kb_name, "command": "x", "binding": []}]
        self.assertEqual(registry.effective_hotkey(self.fn, Config(), entries), "")


if __name__ == "__main__":
    unittest.main()
