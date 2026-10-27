"""Paths, config and small JSON persistence helpers."""

import json
import logging
import math
import os
import shutil
from pathlib import Path

log = logging.getLogger("mosisland.config")


def _xdg(var, fallback):
    return Path(os.environ.get(var) or Path.home() / fallback)


CONFIG_DIR = _xdg("XDG_CONFIG_HOME", ".config") / "linuxmos" / "island"
DATA_DIR = _xdg("XDG_DATA_HOME", ".local/share") / "linuxmos" / "island"
CACHE_DIR = _xdg("XDG_CACHE_HOME", ".cache") / "linuxmos" / "island"

DEFAULT_CONFIG = {
    # Weather: the city is geocoded once, the coordinates are cached
    "city": "",
    "latitude": None,
    "longitude": None,
    # Distance between the top bar and the island, in px
    "offset_y": 6,
    # Monitor: primary | pointer (follows the mouse when a hotkey or the tray opens it) |
    # a number from the left (0 = leftmost) | a connector name like "HDMI-1" (xrandr)
    "monitor": "primary",
    # UI language: auto (follows the session's locale) | de | en
    "language": "auto",
    # Shrink the idle island to a thin line (keeps browser tabs free)
    "compact_when_idle": False,
    "clipboard_limit": 50,
    # Drop unpinned clipboard entries after N minutes (0 = keep)
    "clipboard_autodelete_min": 0,
    # Tray switches; mascot_style: eyes | cat | robot | blob
    "mascot": True,
    "mascot_style": "eyes",
    "osd": True,
    "lyrics_in_pill": False,
    # Screenshots: keep a copy in the folder ("" = ~/Pictures/LinuxMos), open the editor right away
    "screenshot_save": True,
    "screenshot_dir": "",
    "screenshot_open_editor": False,
    # Screen recording (Ctrl+Alt+R area, Ctrl+Alt+Shift+R monitor; the hotkey again stops it):
    # record_format mp4 | gif, record_audio off | system | mic (MP4 only), record_fps 1-60 (GIFs: at most 15),
    # record_max_min stops a recording by itself (0 = never), record_dir "" = ~/Videos/LinuxMos
    "record_format": "mp4",
    "record_audio": "off",
    "record_fps": 30,
    "record_max_min": 30,
    "record_dir": "",
    # Text from the screen (tesseract languages, joined with +) and QR codes
    "ocr_languages": "deu+eng",
    "ocr_keep_linebreaks": False,
    "qr_open_links": False,
    # Notifications as cards on the island (Cinnamon's banners are off meanwhile, its applet keeps
    # the history); "do not disturb" of the island; apps (names or desktop entries) to leave out
    "notifications_on_island": True,
    "notifications_dnd": False,
    "notifications_exclude": [],
    # Live marks: microphone/camera in use (dots + mute button), VPN on/off, downloads in progress.
    # vpn_lookup asks ipinfo.io for the VPN's country and IP (a request to an outside service: off by
    # default); downloads_dir "" = the XDG download folder
    "privacy_indicator": True,
    "vpn_status": True,
    "vpn_lookup": False,
    "downloads_progress": True,
    "downloads_dir": "",
    # AI with an own API key (off by default; chat and dictation send text and audio to the server):
    # ai_chat = the chat tab (Ctrl+Alt+A), ai_voice = dictation (Ctrl+Alt+M) with ai_voice_autopaste
    # typing the text into the window you came from. Any OpenAI-compatible server works (ai_base_url,
    # "" = OpenAI; Ollama: http://localhost:11434/v1); the key lives in the keyring, not here.
    # ai_system_prompt "" = a short built-in one, ai_history = messages sent along with a question,
    # ai_voice_language "" = detect (or an ISO code like "de"), ai_voice_max_s = longest dictation
    "ai_chat": False,
    "ai_voice": False,
    "ai_voice_autopaste": True,
    "ai_base_url": "",
    "ai_model": "",
    "ai_stt_model": "",
    "ai_system_prompt": "",
    "ai_history": 20,
    "ai_voice_language": "",
    "ai_voice_max_s": 120,
    # Command bar (Ctrl+Alt+Space): web search engine (duckduckgo | google | startpage | ecosia | bing |
    # brave, or a URL with %s for the query), file results from the home folder, currencies (ECB rates
    # via frankfurter.dev: a request to an outside service, only when a conversion is typed)
    "command_bar_engine": "duckduckgo",
    "command_bar_files": True,
    "command_bar_currency": True,
    # Water reminder
    "water_goal_ml": 2000,
    "water_portion_ml": 250,
    "water_reminders": True,
    "water_start": "09:00",
    "water_end": "21:00",
    "water_interval_min": 60,
    # Stretch reminder: counts active time (input within the last minute); a pause of
    # stretch_break_reset_min replaces the stretching, a reminder that falls due while the screen is off or
    # locked or the last input is stretch_idle_skip_min old is dropped. "Later" at most stretch_snooze_max
    # times (stretch_snooze_min, then 3/5 of it), an ignored card comes back bigger (stretch_escalate)
    # up to three times, "done" needs stretch_verify_idle (no input during the countdown), every 4th
    # exercise is a long one but at most stretch_long_per_day a day. stretch_off_date = "YYYY-MM-DD" of
    # the day "Today off" was chosen.
    "stretch_enabled": True,
    "stretch_interval_min": 45,
    "stretch_break_reset_min": 5,
    "stretch_idle_skip_min": 30,
    "stretch_snooze_min": 5,
    "stretch_snooze_max": 2,
    "stretch_escalate": True,
    "stretch_verify_idle": True,
    "stretch_long_per_day": 2,
    "stretch_sound": True,
    "stretch_volume": 0.5,
    "stretch_off_date": "",
    # Clip transfer (text, images, files between PCs over SSH; both directions off by default, see docs/CLIP.md).
    # Sending happens only when you press a button, the hotkey or call `linuxmos-clip send`; receiving only
    # fills the inbox and the history, nothing is put on the clipboard until you click it.
    # clip_max_*: limits the RECEIVER enforces while reading; the inbox drops entries after clip_inbox_keep_days
    # and refuses new ones above clip_inbox_quota_mb. clip_peers: [{"name", "host", "user", "port", "key",
    # "os"}] (made by `linuxmos-clip setup`), clip_default_peer: the name of the one the hotkey sends to.
    "clip_send_enabled": False,
    "clip_receive_enabled": False,
    "clip_max_text_kb": 1024,
    "clip_max_image_mb": 20,
    "clip_max_file_mb": 100,
    "clip_inbox_keep_days": 7,
    "clip_inbox_quota_mb": 500,
    "clip_default_peer": "",
    "clip_peers": [],
    # Big eyes in the idle island: the mascot grows by eye_mode_scale (1.5-3.0), temperature and battery go
    "eye_mode": True,
    "eye_mode_scale": 2.0,
    # Clipboard actions on a history entry or the current clipboard (strip formatting, clean links, case,
    # JSON, URL/Base64, lines, QR). clipactions_tracking_params extends the built-in list of link parameters to
    # drop (names; "utm_*" style prefixes with a trailing *). Results only replace the clipboard on a click.
    "clipactions_enabled": True,
    "clipactions_tracking_params": [],
    # Colour picker (Ctrl+Alt+C): format of the copied colour hex | rgb | hsl | hsv, length of the history
    "colorpicker_enabled": True,
    "colorpicker_format": "hex",
    "colorpicker_history": 20,
    # Keep awake (Ctrl+Alt+K): no screen saver, screen off or automatic suspend; 0 = until switched off.
    # Never remembered across restarts.
    "keepawake_enabled": True,
    "keepawake_minutes": 60,
    # Always on top for any window (Ctrl+Alt+P); the pins end when the island quits (pin_release_on_exit)
    "pin_enabled": True,
    "pin_release_on_exit": True,
    # Hotkeys by function id (see `linuxmos-island --list-actions`): only the ones changed from the default,
    # "<Primary><Alt>v" style; "" switches a hotkey off. The island writes them into Cinnamon's custom shortcuts.
    "hotkeys": {},
    # Mouse gestures on the folded pill: the master switch and the action per gesture (see island/gestures.py)
    "gestures_enabled": True,
    "gestures": {},
    # The "New: overview of the functions" card was shown once
    "overview_intro_seen": False,
}


def launcher_path():
    """The `linuxmos-island` program: the one on PATH, else the usual place of `install.sh`."""
    return shutil.which("linuxmos-island") or str(Path.home() / ".local" / "bin" / "linuxmos-island")


def load_json(path, default):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return default


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


def read_config_file(path):
    """(dict, None) from a config file; ({}, None) if it does not exist; (None, message) if it is broken.

    The message names the place in the file ("Zeile 3, Spalte 8: ...") so a card can show it.
    """
    try:
        text = Path(path).read_text(encoding="utf-8")
    except FileNotFoundError:
        return {}, None
    except OSError as error:
        return None, str(error)
    try:
        data = json.loads(text)
    except json.JSONDecodeError as error:
        return None, f"Zeile {error.lineno}, Spalte {error.colno}: {error.msg}"
    if not isinstance(data, dict):
        return None, "Zeile 1: Oben muss ein Objekt { … } stehen"
    return data, None


def number(value, low, high, default):
    """value as a float clamped to low..high; anything that is not a number falls back to default."""
    if isinstance(value, bool) or not isinstance(value, (int, float)) or math.isnan(value):
        value = default
    return min(max(float(value), low), high)


class Config(dict):
    PATH = CONFIG_DIR / "config.json"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._synced = dict(self)    # what the file held when we last read or wrote it
        self.error = None            # why the file on disk is unusable (None = fine)

    @classmethod
    def load(cls):
        cfg = cls(DEFAULT_CONFIG)
        stored, cfg.error = read_config_file(cls.PATH)
        if stored:
            cfg.update(stored)
        if cfg.error:
            log.warning("config.json is not valid (%s): defaults stay active", cfg.error)
        cfg._synced = dict(cfg)
        return cfg

    def reload(self):
        """Read the file again (it was edited). (keys that changed, error): on an error nothing changes."""
        stored, error = read_config_file(self.PATH)
        self.error = error
        if error:
            log.warning("config.json is not valid (%s): keeping the old values", error)
            return [], error
        fresh = dict(DEFAULT_CONFIG)
        fresh.update(stored)
        changed = [key for key in {*fresh, *self} if self.get(key, _MISSING) != fresh.get(key, _MISSING)]
        self.clear()
        self.update(fresh)
        self._synced = dict(self)
        return changed, None

    def save(self):
        """Write what changed here onto what the file holds now.

        The file may have been edited meanwhile and may hold keys this version does not know: both stay.
        Nothing is written while the file is broken, so a half-edited text is never overwritten.
        """
        disk, error = read_config_file(self.PATH)
        if error:
            self.error = error
            log.warning("config.json is not valid (%s): not saving", error)
            return False
        ours = {key: value for key, value in self.items() if key not in self._synced or self._synced[key] != value}
        if ours or not self.PATH.exists():
            disk.update(ours)
            save_json(self.PATH, disk)
        self._synced = dict(self)
        return True

    def fill_defaults(self):
        """Put every missing key into the file with its default (so an editor shows all options).

        Existing values and unknown keys stay; known keys come in the order of DEFAULT_CONFIG. False if the
        file is broken (then nothing is touched).
        """
        disk, error = read_config_file(self.PATH)
        if error:
            return False
        full = {key: disk.get(key, default) for key, default in DEFAULT_CONFIG.items()}
        full.update({key: value for key, value in disk.items() if key not in DEFAULT_CONFIG})
        if list(full.items()) != list(disk.items()) or not self.PATH.exists():
            save_json(self.PATH, full)
        return True

    # ---- typed reads: a wrong type or an out-of-range value in the file never breaks a feature ----
    def number(self, key, low, high):
        return number(self.get(key), low, high, DEFAULT_CONFIG.get(key, low))

    def integer(self, key, low, high):
        return round(self.number(key, low, high))

    def flag(self, key):
        value = self.get(key, DEFAULT_CONFIG.get(key, False))
        return value if isinstance(value, bool) else bool(DEFAULT_CONFIG.get(key, False))

    def section(self, key):
        """A dict-valued key (hotkeys, gestures) as a copy; a wrong type in the file counts as empty."""
        value = self.get(key)
        return dict(value) if isinstance(value, dict) else {}

    def set_in_section(self, key, name, value):
        """section[name] = value (None removes it). Replaces the whole dict: save() compares by value and the
        defaults' dicts are shared between instances, so a dict must never be changed in place."""
        section = self.section(key)
        if value is None:
            section.pop(name, None)
        else:
            section[name] = value
        self[key] = section


_MISSING = object()
