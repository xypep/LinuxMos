"""Paths, config and small JSON persistence helpers."""

import json
import os
from pathlib import Path


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
    # UI language: auto (follows the session's locale) | de | en
    "language": "auto",
    # Shrink the idle island to a thin line (keeps browser tabs free)
    "compact_when_idle": False,
    "clipboard_limit": 50,
    # Drop unpinned clipboard entries after N minutes (0 = keep)
    "clipboard_autodelete_min": 0,
    # Tray switches
    "mascot": True,
    "osd": True,
    "lyrics_in_pill": False,
    # Screenshots: keep a copy in the folder ("" = ~/Pictures/LinuxMos), open the editor right away
    "screenshot_save": True,
    "screenshot_dir": "",
    "screenshot_open_editor": False,
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
    # Water reminder
    "water_goal_ml": 2000,
    "water_portion_ml": 250,
    "water_reminders": True,
    "water_start": "09:00",
    "water_end": "21:00",
    "water_interval_min": 60,
}


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


class Config(dict):
    PATH = CONFIG_DIR / "config.json"

    @classmethod
    def load(cls):
        cfg = cls(DEFAULT_CONFIG)
        stored = load_json(cls.PATH, {})
        if isinstance(stored, dict):
            cfg.update(stored)
        return cfg

    def save(self):
        save_json(self.PATH, dict(self))
