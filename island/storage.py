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
    # Shrink the idle island to a thin line (keeps browser tabs free)
    "compact_when_idle": False,
    "clipboard_limit": 50,
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
