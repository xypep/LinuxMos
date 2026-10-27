"""Command-line helpers: `--list-actions` (the register as a table) and `--check-hotkeys` (conflict report).

They work without a running island (from the code's definitions, the config and gsettings); with one running,
the table also shows what each function is doing. Output is German, like the rest of the interface.
"""

import sys

from island import hotkeys, registry
from island.storage import Config


def _cinnamon_state():
    """(entries of the custom shortcuts, system bindings) – ([], []) if gsettings can't be read."""
    try:
        keys = hotkeys.CinnamonKeys()
    except Exception:
        return None, []
    if not keys.available:
        return None, keys.system_bindings()
    return keys.entries(), keys.system_bindings()


def _rows(config):
    """Rows from the running island (live status) or, without one, from the definitions."""
    try:
        from island.control import Control, ControlError
        control = Control()
        if control.running():
            try:
                return control.registry(), True
            except ControlError:
                pass
    except ImportError:         # no PyGObject here (a headless machine): the definitions and the config will do
        pass
    entries, _system = _cinnamon_state()
    return registry.build().rows(config, entries), False


def list_actions(argv, out=sys.stdout):
    config = Config.load()
    rows, live = _rows(config)
    if "--markdown" in argv:
        print("| Hotkey | Funktion | Aufruf |\n|---|---|---|", file=out)
        for row in rows:
            if row["hotkey_key"] and row["default_hotkey"]:
                print(f"| `{hotkeys.pretty(row['default_hotkey'])}` | {row['name']} | `linuxmos-island --action "
                      f"{row['id']}` |", file=out)
        return 0
    header = ("ID", "Name", "Kategorie", "Hotkey", "Schalter", "Aktion", "Status" if live else "")
    table = [header]
    for row in rows:
        switch = "–" if row["enabled"] is None else f"{row['enabled_key']}={'an' if row['enabled'] else 'aus'}"
        action = "ja" if row["has_action"] else (f"Tab {row['tab']}" if row["tab"] else "–")
        hotkey = hotkeys.pretty(row["hotkey"]) if row["hotkey"] else ("(aus)" if row["hotkey_key"] else "–")
        table.append((row["id"], row["name"], row["category"], hotkey, switch, action,
                      row["status"] if live else ""))
    widths = [max(len(str(r[i])) for r in table) for i in range(len(header))]
    for r in table:
        print("  ".join(str(c).ljust(widths[i]) for i, c in enumerate(r)).rstrip(), file=out)
    print(f"\n{len(rows)} Funktionen" + (" · Status von der laufenden Insel" if live else
                                         " · MosIsland läuft nicht, kein Status"), file=out)
    return 0


def check_hotkeys(out=sys.stdout):
    """0 if every hotkey is free, 1 if two of ours clash or one is a system shortcut."""
    config = Config.load()
    entries, system_bindings = _cinnamon_state()
    reg = registry.build()
    ours = reg.ours(config, entries)
    own_names = {fn.kb_name for fn in reg if fn.kb_name}
    # Cinnamon lists our own shortcuts as custom ones too: they are not "someone else"
    others = [(accel, f"Cinnamon-Kürzel „{entry['name']}“") for entry in (entries or [])
              if entry["name"] not in own_names for accel in entry["binding"]]
    conflicts = hotkeys.find_conflicts(ours, system_bindings + others)
    for fid, (name, accel) in ours.items():
        print(f"{hotkeys.pretty(accel):<20} {name}", file=out)
    print(file=out)
    if not conflicts:
        print(f"Keine Konflikte ({len(ours)} Hotkeys geprüft"
              + ("" if entries is not None else "; Cinnamons Kürzel nicht lesbar, nur Mint-Standards") + ").", file=out)
        return 0
    for c in conflicts:
        print(f"KONFLIKT {hotkeys.pretty(c.accel)}: {c.first} ↔ {c.second}", file=out)
    return 1
