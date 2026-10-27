"""What the settings window does, without any GTK: reading and writing the config, hotkey changes, /proc numbers.

The window only draws and calls these functions, so the rules (what is valid, what a reset does, which conflicts
exist) are testable. Writing goes through storage.Config: atomic, keeps unknown keys, never touches a broken file.
"""

import os
from pathlib import Path

from island import gestures, hotkeys, registry, settingsmeta
from island.storage import Config


class Store:
    """The config as the window sees it. The island picks every change up by itself (inotify)."""

    def __init__(self, keys_factory=None):
        self.config = Config.load()
        self._keys_factory = keys_factory or hotkeys.CinnamonKeys
        self.registry = registry.build()

    # ---- state -------------------------------------------------------------------------------------------
    @property
    def error(self):
        """Why the config file is unusable (None = fine). While it is broken nothing can be saved."""
        return self.config.error

    def reload(self):
        self.config = Config.load()

    # ---- values ------------------------------------------------------------------------------------------
    def set_value(self, key, value):
        """Validate and save one key. Returns (ok, message): a rejected value is not saved."""
        if self.error:
            return False, "Die Config-Datei ist ungültig – erst reparieren (Link unten)"
        ok, normalized, message = settingsmeta.validate(key, value)
        if not ok:
            return False, message
        if self.config.get(key) == normalized and key in self.config:
            return True, ""
        self.config[key] = normalized
        if not self.config.save():
            return False, "Konnte nicht gespeichert werden (Datei ungültig?)"
        return True, ""

    # ---- gestures -------------------------------------------------------------------------------------------
    def gesture_map(self):
        return gestures.resolve(self.config.section("gestures"), tabs=[t for t, _ in gestures.TABS],
                                function_ids=self.registry.ids())

    def set_gesture(self, gesture, action):
        """Save the action of one gesture; the default is stored as 'not set' so the file stays short."""
        if self.error:
            return False, "Die Config-Datei ist ungültig"
        tabs, ids = [t for t, _ in gestures.TABS], self.registry.ids()
        if not gestures.valid_action(gesture, action, tabs, ids):
            return False, "Diese Aktion passt nicht zu der Geste"
        default = gestures.GESTURES[gesture][2]
        self.config.set_in_section("gestures", gesture, None if action == default else action)
        return (True, "") if self.config.save() else (False, "Konnte nicht gespeichert werden")

    # ---- hotkeys ------------------------------------------------------------------------------------------------
    def hotkey_state(self):
        """(ours {id: (name, accel)}, system [(accel, label)], entries): everything a conflict check needs."""
        entries, system = None, []
        try:
            keys = self._keys_factory()
            if keys.available:
                entries = keys.entries()
            system = keys.system_bindings()
        except Exception:       # no gsettings or no Cinnamon schemas: defaults and config only
            pass
        ours = self.registry.ours(self.config, entries)
        own_names = {fn.kb_name for fn in self.registry if fn.kb_name}
        others = [(accel, f"Cinnamon-Kürzel „{entry['name']}“") for entry in (entries or [])
                  if entry["name"] not in own_names for accel in entry["binding"]]
        return ours, system + others, entries

    def conflict(self, fid, accel):
        """The name of whoever has this accelerator already, or None."""
        ours, system, _entries = self.hotkey_state()
        return hotkeys.conflict_for(accel, fid, ours, system)

    def set_hotkey(self, fid, accel, bin_dir):
        """Make `accel` the hotkey of a function ('' = none): the config's section and Cinnamon's shortcut.

        An accelerator equal to the default is stored as 'not changed'. Returns (ok, message)."""
        fn = self.registry.get(fid)
        if fn is None or not fn.hotkey_key:
            return False, "Diese Funktion hat keinen Hotkey"
        if self.error:
            return False, "Die Config-Datei ist ungültig"
        accel = hotkeys.normalize(accel) if accel else ""
        if accel is None:
            return False, "Keine gültige Tastenkombination"
        default = hotkeys.normalize(fn.default_hotkey) if fn.default_hotkey else ""
        self.config.set_in_section("hotkeys", fn.hotkey_key, None if accel == default else accel)
        if not self.config.save():
            return False, "Konnte nicht gespeichert werden"
        try:
            keys = self._keys_factory()
            tail = fn.kb_args if fn.kb_exe == "island" else "linuxmos-spotlight"
            if not keys.available:
                return True, "Gespeichert; Cinnamons Kürzel sind hier nicht erreichbar"
            keys.set_binding(fn.kb_name, fn.kb_command(bin_dir), accel, tail)
        except Exception as error:
            return True, f"Gespeichert, aber Cinnamon nicht erreicht: {error}"
        return True, ""

    def reset_hotkey(self, fid, bin_dir):
        fn = self.registry.get(fid)
        return self.set_hotkey(fid, fn.default_hotkey or "", bin_dir) if fn else (False, "Unbekannte Funktion")


# ---- /proc: the island's numbers, read once --------------------------------------------------------------------
def proc_stats(pid, proc_root="/proc"):
    """{rss_mb, pss_mb, cpu_avg} of a process: its memory and the CPU it used on average since it started
    (percent of one core). None if it can't be read."""
    root = Path(proc_root)
    try:
        fields = (root / str(pid) / "stat").read_text().rsplit(")", 1)[1].split()
        ticks = int(fields[11]) + int(fields[12])                 # utime + stime
        started = int(fields[19]) / os.sysconf("SC_CLK_TCK")
        uptime = float((root / "uptime").read_text().split()[0])
        hz = os.sysconf("SC_CLK_TCK")
        alive = max(1.0, uptime - started)
        result = {"cpu_avg": 100.0 * (ticks / hz) / alive, "rss_mb": None, "pss_mb": None}
        for line in (root / str(pid) / "smaps_rollup").read_text().splitlines():
            if line.startswith("Rss:"):
                result["rss_mb"] = int(line.split()[1]) / 1024
            elif line.startswith("Pss:"):
                result["pss_mb"] = int(line.split()[1]) / 1024
        if result["rss_mb"] is None:      # no smaps_rollup: statm's resident pages
            pages = int((root / str(pid) / "statm").read_text().split()[1])
            result["rss_mb"] = pages * os.sysconf("SC_PAGE_SIZE") / 1048576
        return result
    except (OSError, ValueError, IndexError):
        return None


def tab_label(name):
    return dict(gestures.TABS).get(name, name)


def action_label(action, registry_names):
    """A gesture's action as the window shows it."""
    if action in gestures.ACTIONS:
        return gestures.ACTIONS[action][0]
    if action.startswith(gestures.TAB_PREFIX):
        return "Tab öffnen: " + tab_label(action[len(gestures.TAB_PREFIX):])
    if action.startswith(gestures.FUNCTION_PREFIX):
        return "Funktion: " + registry_names.get(action[len(gestures.FUNCTION_PREFIX):], action)
    return action


def action_choices(gesture, registry_obj):
    """[(action id, label)] a gesture can be set to, in the order the drop-down shows them."""
    kind = gestures.kind_of(gesture)
    choices = [(aid, label) for aid, (label, kinds) in gestures.ACTIONS.items()
               if kind in kinds and not (aid == "default" and gesture == "wheel")]
    choices += [(gestures.TAB_PREFIX + name, "Tab öffnen: " + label) for name, label in gestures.TABS]
    choices += [(gestures.FUNCTION_PREFIX + fn.id, "Funktion: " + fn.name) for fn in registry_obj
                if fn.id in registry.ACTION_IDS and fn.id not in ("settings",)]
    return choices
