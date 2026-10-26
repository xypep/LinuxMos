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
