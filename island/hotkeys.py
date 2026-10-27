"""Hotkeys: accelerator strings, conflicts, and the bridge to Cinnamon's custom shortcuts.

Cinnamon (not the island) listens for the keys: `install.sh` makes one custom shortcut per function that runs
`linuxmos-island --something`. The island manages them from the config's `hotkeys` section by writing the
same gsettings entries the keyboard settings write, so a change takes effect at once, without a restart.

The first half is plain Python (no GTK, no gsettings) and is what the tests and `--check-hotkeys` use.
The second half talks to gsettings through Gio and only runs when a hotkey is read or changed – never at idle.
"""

import logging
import re
from dataclasses import dataclass

log = logging.getLogger("mosisland.hotkeys")

MODIFIERS = {"primary": "ctrl", "control": "ctrl", "ctrl": "ctrl", "alt": "alt", "mod1": "alt", "shift": "shift",
             "super": "super", "mod4": "super", "hyper": "hyper", "meta": "meta"}
ORDER = ("ctrl", "alt", "shift", "super", "hyper", "meta")
CANONICAL = {"ctrl": "<Primary>", "alt": "<Alt>", "shift": "<Shift>", "super": "<Super>", "hyper": "<Hyper>",
             "meta": "<Meta>"}
SHOWN = {"ctrl": "Ctrl", "alt": "Alt", "shift": "Shift", "super": "Super", "hyper": "Hyper", "meta": "Meta"}
TOKEN = re.compile(r"<([A-Za-z0-9_]+)>")
# Key names as Cinnamon writes them -> how they read
KEY_ALIASES = {"escape": "Escape", "return": "Return", "space": "space", "delete": "Delete", "tab": "Tab"}


@dataclass(frozen=True)
class Accel:
    mods: frozenset
    key: str

    def __str__(self):
        return canonical(self)


def parse(text):
    """'<Primary><Alt>v' (also <Control>, <Ctrl>, <Mod1>) -> Accel, or None if it is not a usable accelerator.

    A usable one has a key; the key is compared case-insensitively ("V" is the same shortcut as "v").
    """
    if not isinstance(text, str):
        return None
    rest, mods = text.strip(), set()
    while rest.startswith("<"):
        match = TOKEN.match(rest)
        if not match:
            return None
        mod = MODIFIERS.get(match.group(1).lower())
        if mod is None:
            return None
        mods.add(mod)
        rest = rest[match.end():]
    if not rest or "<" in rest or ">" in rest or any(c.isspace() for c in rest):
        return None
    return Accel(frozenset(mods), rest.lower())


def canonical(accel):
    """Accel -> '<Primary><Alt>v' (modifiers in a fixed order; the key as GTK spells it for letters)."""
    mods = "".join(CANONICAL[m] for m in ORDER if m in accel.mods)
    key = accel.key
    return mods + (key if len(key) == 1 else _key_name(key))


def _key_name(key):
    if key in KEY_ALIASES:
        return KEY_ALIASES[key]
    if re.fullmatch(r"f\d{1,2}", key):
        return key.upper()
    return key[:1].upper() + key[1:] if key.isalpha() else key


def normalize(text):
    """The canonical spelling of an accelerator string, or None."""
    accel = parse(text)
    return canonical(accel) if accel else None


def pretty(text):
    """'<Primary><Alt><Shift>v' -> 'Ctrl+Alt+Shift+V' (what the overview shows)."""
    accel = parse(text)
    if accel is None:
        return ""
    key = accel.key
    shown = key.upper() if len(key) == 1 else (_key_name(key)[:1].upper() + _key_name(key)[1:])
    return "+".join([SHOWN[m] for m in ORDER if m in accel.mods] + [shown])


def same(a, b):
    pa, pb = parse(a), parse(b)
    return pa is not None and pa == pb


# ---- conflicts ------------------------------------------------------------------------------------------
# What Mint/Cinnamon bind by default; used when the gsettings schemas can't be read (no Cinnamon around)
MINT_DEFAULTS = (
    ("<Primary><Alt>t", "Terminal"), ("<Primary><Alt>l", "Bildschirm sperren"),
    ("<Primary><Alt>Delete", "Abmelden"), ("<Primary><Alt>End", "Ausschalten"),
    ("<Primary><Alt>Escape", "Cinnamon neu starten"), ("<Primary><Alt>Up", "Arbeitsfläche hoch"),
    ("<Primary><Alt>Down", "Arbeitsfläche runter"), ("<Primary><Alt>Left", "Arbeitsfläche links"),
    ("<Primary><Alt>Right", "Arbeitsfläche rechts"), ("<Primary><Alt>Tab", "Panels wechseln"),
    ("<Alt>F2", "Befehl ausführen"), ("<Super>l", "Bildschirm sperren"), ("<Super>e", "Dateimanager"),
    ("<Super>d", "Schreibtisch zeigen"), ("<Alt>Tab", "Fenster wechseln"),
)


@dataclass(frozen=True)
class Conflict:
    accel: str            # canonical
    first: str            # who has it
    second: str           # who else wants it
    system: bool          # the other one is not one of ours (Cinnamon, another program)


def find_conflicts(ours, system=()):
    """Clashes between our functions and with the system.

    ours: {function id: (name, accel string)}; system: [(accel string, label)].
    Two of ours on one accelerator, or one of ours on a system shortcut, is a conflict.
    """
    seen, result = {}, []
    for fid, (name, text) in ours.items():
        accel = parse(text)
        if accel is None:
            continue
        if accel in seen:
            result.append(Conflict(canonical(accel), seen[accel], name, False))
        else:
            seen[accel] = name
    for text, label in system:
        accel = parse(text)
        if accel is not None and accel in seen:
            result.append(Conflict(canonical(accel), seen[accel], label, True))
    return result


def conflict_for(accel_text, own_id, ours, system=()):
    """Who already has this accelerator (a name), ignoring the function `own_id` itself; None if it is free."""
    accel = parse(accel_text)
    if accel is None:
        return None
    for fid, (name, text) in ours.items():
        if fid != own_id and parse(text) == accel:
            return name
    for text, label in system:
        if parse(text) == accel:
            return label
    return None


# ---- Cinnamon's custom shortcuts (gsettings) ---------------------------------------------------------
KB_SCHEMA = "org.cinnamon.desktop.keybindings"
KB_ITEM_SCHEMA = "org.cinnamon.desktop.keybindings.custom-keybinding"
KB_BASE = "/org/cinnamon/desktop/keybindings/custom-keybindings"
# Schemas whose keys of type "as" are shortcuts (the system's own)
SYSTEM_SCHEMAS = (KB_SCHEMA, KB_SCHEMA + ".media-keys", KB_SCHEMA + ".wm", "org.cinnamon.muffin.keybindings")
SCHEMA_LABELS = {KB_SCHEMA + ".media-keys": "Cinnamon", KB_SCHEMA + ".wm": "Cinnamon", KB_SCHEMA: "Cinnamon",
                 "org.cinnamon.muffin.keybindings": "Cinnamon"}


class CinnamonKeys:
    """Reads and writes Cinnamon's custom shortcuts (gsettings). Create it when needed, drop it afterwards."""

    def __init__(self):
        from gi.repository import Gio
        self.Gio = Gio
        source = Gio.SettingsSchemaSource.get_default()
        self.available = bool(source and source.lookup(KB_SCHEMA, True) and source.lookup(KB_ITEM_SCHEMA, True))
        self._source = source
        self._root = Gio.Settings.new(KB_SCHEMA) if self.available else None

    def _item(self, entry):
        return self.Gio.Settings.new_with_path(KB_ITEM_SCHEMA, f"{KB_BASE}/{entry}/")

    def entries(self):
        """[{id, name, command, binding: [accel]}] of all custom shortcuts."""
        if not self.available:
            return []
        result = []
        for entry in self._root.get_strv("custom-list"):
            if entry == "__dummy__":
                continue
            item = self._item(entry)
            result.append({"id": entry, "name": item.get_string("name"), "command": item.get_string("command"),
                           "binding": list(item.get_strv("binding"))})
        return result

    def system_bindings(self):
        """[(accel, label)] of Cinnamon's own shortcuts, or Mint's usual ones if the schemas aren't there."""
        found = []
        source = self._source
        for schema_id in SYSTEM_SCHEMAS:
            schema = source.lookup(schema_id, True) if source else None
            if schema is None:
                continue
            settings = self.Gio.Settings.new(schema_id)
            for key in schema.list_keys():
                value = settings.get_value(key)
                if value.get_type_string() != "as" or key == "custom-list":
                    continue
                for accel in value.unpack():
                    if accel and "<" in accel and parse(accel):
                        found.append((accel, f"{SCHEMA_LABELS.get(schema_id, schema_id)}: {key}"))
        return found or [(accel, f"Mint: {label}") for accel, label in MINT_DEFAULTS]

    def find(self, entries, name, command_tail):
        """Our entry for a function: by its name, else by a command that ends the same way."""
        for entry in entries:
            if entry["name"] == name:
                return entry
        if command_tail:
            for entry in entries:
                if entry["command"].endswith(command_tail):
                    return entry
        return None

    def set_binding(self, name, command, accel, command_tail=None):
        """Give the shortcut `name` this accelerator ('' removes it). The entry is made if it is missing.

        Returns True if something was written.
        """
        if not self.available:
            log.warning("hotkeys: Cinnamon's shortcut schema is missing, nothing written")
            return False
        entries = self.entries()
        entry = self.find(entries, name, command_tail)
        listed = self._root.get_strv("custom-list")
        if entry is None:
            if not accel:
                return False
            n = 0
            while f"custom{n}" in listed:
                n += 1
            entry_id, created = f"custom{n}", True
        else:
            entry_id, created = entry["id"], False
        item = self._item(entry_id)
        if entry is not None and command_tail and entry["command"].endswith(command_tail):
            command = entry["command"]       # the user's or install.sh's path to the program stays
        wanted = [accel] if accel else []
        changed = created or list(item.get_strv("binding")) != wanted or item.get_string("command") != command
        if not changed:
            return False
        item.set_string("name", name)
        item.set_string("command", command)
        item.set_strv("binding", wanted)
        if created:
            self._root.set_strv("custom-list", [e for e in listed if e != "__dummy__"] + [entry_id])
        else:
            self._poke(listed)
        self.Gio.Settings.sync()
        log.info("hotkeys: %s -> %s", name, accel or "(off)")
        return True

    def _poke(self, listed):
        """Cinnamon rereads its shortcuts when custom-list changes: rotate it by one so a changed binding of
        an existing entry is picked up even where only the list is watched."""
        if len(listed) > 1:
            self._root.set_strv("custom-list", listed[1:] + listed[:1])
