"""The register of functions: one entry per thing the island can do. The single source of truth for the
overview window, `--list-actions`, `--action ID`, the hotkey list and the gestures' "run a function".

The data part (names, categories, config keys, default hotkeys) needs no GTK and no running island:
`build()` gives the entries without callables, which is all the settings window needs while the island is
off. The island calls `populate(window)` at start-up and every entry gets its `action` (what a click or a
hotkey does) and `status` (what the overview shows next to it).

A later feature registers itself with `register(Function(...))` – nothing else has to change.
"""

import logging
from dataclasses import dataclass
from typing import Callable, Optional

from island import hotkeys

log = logging.getLogger("mosisland.registry")

# Category names as the overview shows them, in this order
CATEGORIES = ("Insel", "Zwischenablage", "Bildschirm", "Werkzeuge", "Aufgaben & Fokus", "Wohlbefinden", "Medien & Wetter",
              "Live-Hinweise", "KI", "System")


@dataclass
class Function:
    id: str
    name: str                                   # German, as shown
    description: str
    category: str
    enabled_key: Optional[str] = None           # the config switch that turns it on and off
    hotkey_key: Optional[str] = None            # its key in the config's "hotkeys" section
    default_hotkey: Optional[str] = None        # "<Primary><Alt>v"
    action: Optional[Callable] = None           # what a click or a hotkey does
    status: Optional[Callable] = None           # -> (running: bool, text: str) or None
    hide_window_first: bool = False             # the settings window steps aside first (screen grabs)
    dangerous: bool = False                     # asks for confirmation (restart, power off)
    tab: Optional[str] = None                   # the island tab that belongs to it (opened if there is no action)
    kb_name: Optional[str] = None               # name of Cinnamon's custom shortcut that runs it
    kb_args: Optional[str] = None               # ... and what it passes to the program
    kb_exe: str = "island"                      # island | spotlight

    def kb_command(self, bin_dir):
        if self.kb_exe == "spotlight":
            return f"{bin_dir}/linuxmos-spotlight"
        return f"{bin_dir}/linuxmos-island {self.kb_args}"


def _hot(fid, accel, name, args, **extra):
    """Fields shared by everything that has a Cinnamon shortcut."""
    return dict(hotkey_key=fid, default_hotkey=accel, kb_name=name, kb_args=args, **extra)


def definitions():
    """All functions, without callables. Order = order in the overview within a category."""
    P = "<Primary><Alt>"
    S = "<Primary><Alt><Shift>"
    f = Function
    return [
        # ---- Insel ----
        f("toggle", "Insel öffnen/schließen", "Klappt die Insel auf oder zu.", "Insel",
          **_hot("toggle", P + "i", "MosIsland (LinuxMos)", "--toggle")),
        f("search", "Suche (Command Bar)", "Apps, Dateien, Rechner, Einheiten, Währungen und Websuche in einem Feld.",
          "Insel", tab="search", **_hot("search", P + "space", "MosIsland Suche (LinuxMos)", "--tab search")),
        f("spotlight", "Spotlight-Suche (rofi)", "Die rofi-Suche als Alternative zur Command Bar.", "Insel",
          **_hot("spotlight", "<Super>space", "Spotlight (LinuxMos)", None, kb_exe="spotlight")),
        f("settings", "Einstellungen & Übersicht", "Dieses Fenster: Funktionen, Hotkeys, Gesten, Einstellungen.",
          "Insel", **_hot("settings", P + "h", "MosIsland Einstellungen (LinuxMos)", "--settings --tab overview")),
        f("gestures", "Gesten auf der Pille", "Mausrad, Mittelklick, Rechtsklick und Doppelklick auf der Pille.",
          "Insel", enabled_key="gestures_enabled"),
        f("compact", "Minimal-Notch", "Im Leerlauf nur eine dünne Linie statt der Pille.", "Insel",
          enabled_key="compact_when_idle"),
        # ---- Zwischenablage ----
        f("clipboard", "Zwischenablage-Verlauf", "Verlauf mit Suche und Pins; ein Klick fügt direkt ein.",
          "Zwischenablage", tab="clipboard",
          **_hot("clipboard", P + "v", "MosIsland Zwischenablage (LinuxMos)", "--tab clipboard")),
        f("clip-actions", "Zwischenablage-Aktionen",
          "Formatierung entfernen, Links bereinigen, Groß/klein, JSON, URL/Base64, Zeilen, QR-Code.",
          "Zwischenablage", enabled_key="clipactions_enabled",
          **_hot("clip-actions", S + "v", "MosIsland Zwischenablage-Aktionen (LinuxMos)", "--action clip-actions")),
        f("shelf", "Ablage", "Dateien auf die Insel ziehen und später wieder herausziehen.", "Zwischenablage",
          tab="shelf"),
        f("clip-send", "Clip senden", "Zwischenablage per SSH an einen anderen PC schicken (nur auf Knopfdruck).",
          "Zwischenablage", enabled_key="clip_send_enabled",
          **_hot("clip-send", S + "t", "MosIsland Clip senden (LinuxMos)", "--clip-send")),
        f("clip-receive", "Clip-Empfang", "Clips anderer PCs im Eingang und im Verlauf annehmen.", "Zwischenablage",
          enabled_key="clip_receive_enabled", tab="clipboard"),
        # ---- Bildschirm ----
        f("screenshot-area", "Screenshot vom Bereich", "Bereich aufziehen, in die Zwischenablage und in den Ordner.",
          "Bildschirm", hide_window_first=True,
          **_hot("screenshot-area", P + "s", "MosIsland Screenshot Bereich (LinuxMos)", "--shot area")),
        f("screenshot-screen", "Screenshot vom Bildschirm", "Der Monitor unter der Maus.", "Bildschirm",
          hide_window_first=True,
          **_hot("screenshot-screen", S + "s", "MosIsland Screenshot Bildschirm (LinuxMos)", "--shot screen")),
        f("ocr", "Text vom Bildschirm (OCR)", "Bereich aufziehen, der erkannte Text landet in der Zwischenablage.",
          "Bildschirm", hide_window_first=True,
          **_hot("ocr", P + "o", "MosIsland Text erkennen (LinuxMos)", "--ocr")),
        f("qr", "QR-Code lesen", "QR-Code oder Barcode aus einem Bereich lesen.", "Bildschirm",
          hide_window_first=True, **_hot("qr", P + "q", "MosIsland QR-Code lesen (LinuxMos)", "--qr")),
        f("record-area", "Aufnahme vom Bereich", "Bildschirmaufnahme (MP4 oder GIF); nochmal drücken beendet sie.",
          "Bildschirm", hide_window_first=True,
          **_hot("record-area", P + "r", "MosIsland Aufnahme Bereich (LinuxMos)", "--record area")),
        f("record-screen", "Aufnahme vom Bildschirm", "Der Monitor unter der Maus.", "Bildschirm",
          hide_window_first=True,
          **_hot("record-screen", S + "r", "MosIsland Aufnahme Bildschirm (LinuxMos)", "--record screen")),
        f("color-picker", "Farbpipette", "Farbe vom Bildschirm aufnehmen (Lupe, Hex/RGB/HSL/HSV).", "Bildschirm",
          enabled_key="colorpicker_enabled", hide_window_first=True,
          **_hot("color-picker", P + "c", "MosIsland Farbpipette (LinuxMos)", "--action color-picker")),
        # ---- Werkzeuge ----
        f("keep-awake", "Wach halten", "Kein Bildschirmschoner, keine Bildschirmabschaltung, kein Ruhezustand.",
          "Werkzeuge", enabled_key="keepawake_enabled", tab="tools",
          **_hot("keep-awake", P + "k", "MosIsland Wach halten (LinuxMos)", "--action keep-awake")),
        f("pin-window", "Fenster anpinnen", "Das aktive Fenster immer im Vordergrund halten.", "Werkzeuge",
          enabled_key="pin_enabled", tab="tools",
          **_hot("pin-window", P + "p", "MosIsland Fenster anpinnen (LinuxMos)", "--action pin-window")),
        # ---- Aufgaben & Fokus ----
        f("todo", "Aufgaben", "Aufgaben mit Fälligkeit und Erinnerung.", "Aufgaben & Fokus", tab="todo"),
        f("note", "Notiz & Pomodoro", "Notiz, Fokus-Timer und Countdown.", "Aufgaben & Fokus", tab="note"),
        f("water", "Wasser-Erinnerung", "Trinkerinnerung mit Tagesziel und Diagramm.", "Aufgaben & Fokus",
          enabled_key="water_reminders", tab="water"),
        # ---- Wohlbefinden ----
        f("stretch", "Dehn-Erinnerung", "Nach 45 Minuten aktiver Zeit eine Übung; „Jetzt dehnen“ zeigt sie sofort.",
          "Wohlbefinden", enabled_key="stretch_enabled", tab="stretch"),
        f("mascot", "Maskottchen", "Augen, Katze, Roboter oder Blob im Leerlauf.", "Wohlbefinden",
          enabled_key="mascot"),
        f("eye-mode", "Augen-Modus", "Im Leerlauf wird die Figur groß, Temperatur und Akku verschwinden.",
          "Wohlbefinden", enabled_key="eye_mode"),
        # ---- Medien & Wetter ----
        f("media", "Musik", "Player per MPRIS: Cover, Play/Pause, Spulen.", "Medien & Wetter", tab="home"),
        f("lyrics", "Lyrics in der Pille", "Die gesungene Zeile in der eingeklappten Pille.", "Medien & Wetter",
          enabled_key="lyrics_in_pill", tab="home"),
        f("weather", "Wetter", "Temperatur und Regenwarnung (MET Norway).", "Medien & Wetter", tab="weather"),
        # ---- Live-Hinweise ----
        f("notifications", "Benachrichtigungen als Karte", "Jede Benachrichtigung erscheint auf der Insel.",
          "Live-Hinweise", enabled_key="notifications_on_island"),
        f("osd", "Lautstärke & Helligkeit", "Overlay auf der Insel statt Cinnamons Anzeige.", "Live-Hinweise",
          enabled_key="osd"),
        f("privacy", "Mikrofon & Kamera", "Oranger und grüner Punkt, solange eine App aufnimmt.", "Live-Hinweise",
          enabled_key="privacy_indicator"),
        f("vpn", "VPN-Status", "VPN an/aus melden.", "Live-Hinweise", enabled_key="vpn_status"),
        f("downloads", "Download-Fortschritt", "Ring in der Pille, solange ein Browser lädt.", "Live-Hinweise",
          enabled_key="downloads_progress"),
        # ---- KI ----
        f("chat", "KI-Chat", "Chat-Tab mit eigenem API-Key.", "KI", enabled_key="ai_chat", tab="chat",
          **_hot("chat", P + "a", "MosIsland KI-Chat (LinuxMos)", "--chat")),
        f("voice", "Diktat", "Sprechen, Taste nochmal drücken: der Text wird ins aktive Fenster getippt.", "KI",
          enabled_key="ai_voice", **_hot("voice", P + "m", "MosIsland Diktat (LinuxMos)", "--voice")),
        # ---- System ----
        f("controls", "Steuerung", "WLAN, Bluetooth, Nicht stören, Dark Mode, Mikro, Lautstärke, Helligkeit.",
          "System", tab="controls"),
        f("lock", "Bildschirm sperren", "Sperrt den Bildschirm.", "System"),
        f("suspend", "Ruhezustand", "Schickt den PC in den Ruhezustand.", "System"),
        f("reboot", "Neustart", "Startet den PC neu.", "System", dangerous=True),
        f("poweroff", "Ausschalten", "Fährt den PC herunter.", "System", dangerous=True),
    ]


# The functions that have an action of their own once the island has populated the register (the others open their tab).
# Kept here so that the settings window and `--list-actions` know it without a running island.
ACTION_IDS = frozenset({
    "toggle", "search", "spotlight", "settings", "gestures", "clipboard", "clip-actions", "clip-send",
    "screenshot-area", "screenshot-screen", "ocr", "qr", "record-area", "record-screen", "color-picker",
    "keep-awake", "pin-window", "chat", "voice", "stretch", "lock", "suspend", "reboot", "poweroff",
})


class Registry:
    def __init__(self, functions=()):
        self._functions = {}
        self.open_tab = None        # callable(tab name): set by populate(), used for functions without an action
        for fn in functions:
            self.register(fn)

    def register(self, fn):
        """Add a function (or replace the one with the same id: how a later feature takes over an entry)."""
        self._functions[fn.id] = fn

    def get(self, fid):
        return self._functions.get(fid)

    def __iter__(self):
        return iter(self._functions.values())

    def __contains__(self, fid):
        return fid in self._functions

    def ids(self):
        return list(self._functions)

    def by_category(self):
        """[(category, [Function])] in the order of CATEGORIES (others last)."""
        groups = {}
        for fn in self:
            groups.setdefault(fn.category, []).append(fn)
        order = [c for c in CATEGORIES if c in groups] + [c for c in groups if c not in CATEGORIES]
        return [(c, groups[c]) for c in order]

    # ---- config ----------------------------------------------------------------------------------
    @staticmethod
    def enabled(fn, config):
        """True/False from the function's config switch; None if it has none."""
        return config.flag(fn.enabled_key) if fn.enabled_key else None

    def ours(self, config, entries=None):
        """{id: (name, accel)} in the shape hotkeys.find_conflicts wants."""
        return {fn.id: (fn.name, accel) for fn in self if fn.hotkey_key
                for accel in [effective_hotkey(fn, config, entries)] if accel}

    # ---- IPC -------------------------------------------------------------------------------------
    def rows(self, config, entries=None, live=False):
        """The register as plain data (the overview window gets this as JSON). live: also run the status
        callables (only the running island can)."""
        result = []
        for fn in self:
            running, text = None, ""
            if live and fn.status is not None:
                try:
                    state = fn.status()
                except Exception:       # a status that fails must not take the overview down
                    log.exception("status of %s failed", fn.id)
                    state = None
                if state:
                    running, text = bool(state[0]), state[1]
            result.append({
                "id": fn.id, "name": fn.name, "description": fn.description, "category": fn.category,
                "enabled_key": fn.enabled_key, "enabled": self.enabled(fn, config),
                "hotkey_key": fn.hotkey_key, "default_hotkey": fn.default_hotkey or "",
                "hotkey": effective_hotkey(fn, config, entries) if fn.hotkey_key else "",
                "has_action": fn.action is not None or fn.id in ACTION_IDS, "tab": fn.tab or "",
                "hide_window_first": fn.hide_window_first, "dangerous": fn.dangerous,
                "running": running, "status": text,
            })
        return result


def effective_hotkey(fn, config, entries=None):
    """The accelerator a function really has: what the config says, else what Cinnamon has for its shortcut
    (the user may have changed it in the keyboard settings), else the default. '' = no hotkey."""
    if not fn.hotkey_key:
        return ""
    section = config.section("hotkeys")
    if fn.hotkey_key in section:
        value = section[fn.hotkey_key]
        return hotkeys.normalize(value) or "" if isinstance(value, str) else ""
    if entries is not None and fn.kb_name:
        tail = fn.kb_args if fn.kb_exe == "island" else "linuxmos-spotlight"
        for entry in entries:
            if entry["name"] == fn.kb_name or (tail and entry["command"].endswith(tail)):
                return hotkeys.normalize(entry["binding"][0]) or "" if entry["binding"] else ""
    return hotkeys.normalize(fn.default_hotkey) or "" if fn.default_hotkey else ""


def build():
    """A registry with the data only (no actions): enough for the settings window and `--list-actions`."""
    return Registry(definitions())


# The one registry of this process. populate() fills in the actions in the island.
REGISTRY = Registry(definitions())


def populate(host):
    """Give every function its action and status; `host` is the island window."""
    h = host
    actions = {
        "toggle": lambda: h.toggle(focus=True),
        "search": lambda: h.open_tab("search"),
        "spotlight": h.launch_spotlight,
        "settings": lambda: h.open_overview("overview"),
        "gestures": lambda: h.open_overview("gestures"),
        "clipboard": lambda: h.open_tab("clipboard"),
        "clip-actions": h.clip_actions_current,
        "clip-send": h.clip_send_clipboard,
        "screenshot-area": lambda: h.screenshot("area"),
        "screenshot-screen": lambda: h.screenshot("screen"),
        "ocr": lambda: h.read_screen("text"),
        "qr": lambda: h.read_screen("qr"),
        "record-area": lambda: h.record("area"),
        "record-screen": lambda: h.record("screen"),
        "color-picker": h.pick_color,
        "keep-awake": h.toggle_keepawake,
        "pin-window": h.toggle_pin_active,
        "chat": h.open_chat,
        "voice": h.voice,
        "stretch": h.stretch.trigger_now,
        "lock": h.system_lock,
        "suspend": h.system_suspend,
        "reboot": h.system_reboot,
        "poweroff": h.system_poweroff,
    }
    REGISTRY.open_tab = h.open_tab
    statuses = h.function_statuses()
    for fn in REGISTRY:
        fn.action = actions.get(fn.id)
        fn.status = statuses.get(fn.id)
    return REGISTRY


def run(fid):
    """Run a function by id. Returns (ok, message). A function without an action opens its tab."""
    fn = REGISTRY.get(fid)
    if fn is None:
        return False, f"unbekannte Funktion: {fid}"
    try:
        if fn.action is not None:
            fn.action()
        elif fn.tab and REGISTRY.open_tab is not None:
            REGISTRY.open_tab(fn.tab)
        else:
            return False, f"{fn.name} hat keine Aktion"
    except Exception as error:      # an action that fails must not take the island down
        log.exception("action %s failed", fid)
        return False, str(error)
    return True, ""
