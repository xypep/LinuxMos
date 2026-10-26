#!/usr/bin/env python3
"""Small helper for the Cinnamon tweaks that are awkward to do in pure Bash.

Every subcommand is idempotent, so install.sh can be re-run safely.

Subcommands:
  panel-top HEIGHT                 move the main panel to the top and resize it
  drop-applets UUID...             remove applets (e.g. the window list) from all panels
  xlet-set UUID KEY JSON_VALUE     change a setting in every instance of an applet
  add-keybinding NAME CMD BINDING  add (or update) a custom keyboard shortcut
  strip-binding SCHEMA KEY BINDING remove one accelerator from a keybinding list
  render TEMPLATE OUT KEY=VALUE... replace @KEY@ placeholders in a template file
"""

import ast
import glob
import json
import os
import subprocess
import sys

CUSTOM_KB_SCHEMA = "org.cinnamon.desktop.keybindings"
CUSTOM_KB_ITEM_SCHEMA = "org.cinnamon.desktop.keybindings.custom-keybinding"
CUSTOM_KB_BASE = "/org/cinnamon/desktop/keybindings/custom-keybindings"
SPICES_DIR = os.path.expanduser("~/.config/cinnamon/spices")


# --------------------------------------------------------------------------- #
# gsettings wrappers
# --------------------------------------------------------------------------- #
def gget(schema, key):
    out = subprocess.run(
        ["gsettings", "get", schema, key], check=True, capture_output=True, text=True
    ).stdout.strip()
    # Empty typed arrays are printed as "@as []"
    if out.startswith("@"):
        out = out.split(" ", 1)[1]
    return ast.literal_eval(out)


def gset(schema, key, value):
    # Python's repr of str/list/bool is valid GVariant text for our types,
    # except booleans, which GVariant spells in lowercase.
    text = str(value).lower() if isinstance(value, bool) else repr(value)
    subprocess.run(["gsettings", "set", schema, key, text], check=True)


# --------------------------------------------------------------------------- #
# Panel / applets
# --------------------------------------------------------------------------- #
def panel_top(height):
    panels = gget("org.cinnamon", "panels-enabled")  # ['1:0:bottom', ...]
    if not panels:
        print("No panel found – skipping.", file=sys.stderr)
        return
    # Only the first (main) panel is moved; additional panels stay untouched.
    panel_id, monitor, _pos = panels[0].split(":")
    panels[0] = f"{panel_id}:{monitor}:top"
    gset("org.cinnamon", "panels-enabled", panels)

    heights = [h for h in gget("org.cinnamon", "panels-height") if h.split(":")[0] != panel_id]
    heights.insert(0, f"{panel_id}:{height}")
    gset("org.cinnamon", "panels-height", heights)


def drop_applets(uuids):
    applets = gget("org.cinnamon", "enabled-applets")
    # Format: panelN:zone:order:uuid[:instance-id]
    kept = [a for a in applets if a.split(":")[3].lstrip("!") not in uuids]
    if kept != applets:
        gset("org.cinnamon", "enabled-applets", kept)


def xlet_set(uuid, key, json_value):
    value = json.loads(json_value)
    files = glob.glob(os.path.join(SPICES_DIR, uuid, "*.json"))
    if not files:
        print(f"No config for {uuid} yet – open its settings once and re-run.", file=sys.stderr)
        return
    for path in files:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        if key not in data or not isinstance(data[key], dict):
            continue
        data[key]["value"] = value
        # Write atomically: Cinnamon watches these files and reloads them live.
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=4)
        os.replace(tmp, path)


# --------------------------------------------------------------------------- #
# Keybindings
# --------------------------------------------------------------------------- #
def _kb_path(entry):
    return f"{CUSTOM_KB_ITEM_SCHEMA}:{CUSTOM_KB_BASE}/{entry}/"


def add_keybinding(name, command, binding):
    entries = gget(CUSTOM_KB_SCHEMA, "custom-list")

    # Reuse an existing entry with the same name (idempotent re-runs).
    target = None
    for entry in entries:
        if entry == "__dummy__":
            continue
        if gget(_kb_path(entry), "name") == name:
            target = entry
            break

    if target is None:
        # Cinnamon only picks up entries whose id contains "custom".
        n = 0
        while f"custom{n}" in entries:
            n += 1
        target = f"custom{n}"

    path = _kb_path(target)
    gset(path, "name", name)
    gset(path, "command", command)
    gset(path, "binding", [binding])

    if target not in entries:
        # Changing custom-list is what makes Cinnamon reload the bindings.
        gset(CUSTOM_KB_SCHEMA, "custom-list", entries + [target])


def has_key(schema, key):
    return subprocess.run(["gsettings", "writable", schema, key], capture_output=True).returncode == 0


def strip_binding(schema, key, binding):
    # e.g. switch-input-source only exists since Cinnamon 6.2
    if not has_key(schema, key):
        return
    current = gget(schema, key)
    kept = [b for b in current if b.lower() != binding.lower()]
    if kept != current:
        gset(schema, key, kept)
        print(f"Removed {binding} from {schema} {key}.")


# --------------------------------------------------------------------------- #
# Templates
# --------------------------------------------------------------------------- #
def render(template, out, pairs):
    with open(template, encoding="utf-8") as fh:
        text = fh.read()
    for pair in pairs:
        key, _, value = pair.partition("=")
        text = text.replace(f"@{key}@", value)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(text)


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    cmd, args = argv[1], argv[2:]
    if cmd == "panel-top" and len(args) == 1:
        panel_top(int(args[0]))
    elif cmd == "drop-applets" and args:
        drop_applets(set(args))
    elif cmd == "xlet-set" and len(args) == 3:
        xlet_set(*args)
    elif cmd == "add-keybinding" and len(args) == 3:
        add_keybinding(*args)
    elif cmd == "strip-binding" and len(args) == 3:
        strip_binding(*args)
    elif cmd == "render" and len(args) >= 2:
        render(args[0], args[1], args[2:])
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
