"""What the settings window's "Funktionen" tab knows about each config key: group, label, kind, valid range.

Pure data and validation (no GTK): the window builds its inputs from FIELDS and refuses to save what validate()
rejects. The island itself still clamps and ignores bad values on its own (storage.Config.number & co.), this
is for the person typing.
"""

import re
from dataclasses import dataclass
from typing import Optional

HHMM = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
LANG_LIST = re.compile(r"^[A-Za-z_]{2,12}(\+[A-Za-z_]{2,12})*$")


@dataclass(frozen=True)
class Field:
    key: str
    label: str
    kind: str                               # bool | int | float | choice | text | time | path | url | list
    low: Optional[float] = None
    high: Optional[float] = None
    choices: tuple = ()                     # ((value, label), ...)
    help: str = ""
    restart: bool = False                   # takes effect after the island restarts
    free: bool = False                      # choice that also accepts any text (own search URL, ...)
    optional: bool = False                  # text/path/url may be empty


def _b(key, label, help=""):
    return Field(key, label, "bool", help=help)


def _i(key, label, low, high, help=""):
    return Field(key, label, "int", low, high, help=help)


GROUPS = [
    ("Allgemein", [
        Field("city", "Wetter-Ort", "text", optional=True, help="Leer = kein Wetter"),
        _i("offset_y", "Abstand zur Top Bar (px)", 0, 300),
        Field("monitor", "Monitor", "choice", choices=(("primary", "Hauptmonitor"),
                                                       ("pointer", "Monitor mit der Maus")), free=True,
              help="Auch eine Nummer von links (0, 1 …) oder ein Anschlussname wie HDMI-1"),
        Field("language", "Sprache", "choice", choices=(("auto", "Automatisch"), ("de", "Deutsch"),
                                                        ("en", "English")), restart=True),
        _b("compact_when_idle", "Minimal-Notch im Leerlauf"),
        _b("osd", "Lautstärke & Helligkeit auf der Insel"),
        _b("lyrics_in_pill", "Lyrics in der Pille"),
        _b("gestures_enabled", "Gesten auf der Pille"),
    ]),
    ("Maskottchen & Augen", [
        _b("mascot", "Maskottchen im Leerlauf"),
        Field("mascot_style", "Figur", "choice", choices=(("eyes", "Augen"), ("cat", "Katze"), ("robot", "Roboter"),
                                                          ("blob", "Blob"))),
        _b("eye_mode", "Augen-Modus (groß im Leerlauf)"),
        Field("eye_mode_scale", "Größe im Augen-Modus", "float", 1.5, 3.0),
    ]),
    ("Dehn-Erinnerung", [
        _b("stretch_enabled", "Dehn-Erinnerung"),
        _i("stretch_interval_min", "Aktive Minuten bis zur Karte", 1, 600),
        _i("stretch_break_reset_min", "Pause, die das Dehnen ersetzt (min)", 1, 120),
        _i("stretch_idle_skip_min", "Karte verwerfen nach Leerlauf (min)", 1, 600),
        _i("stretch_snooze_min", "Später: Minuten", 1, 60),
        _i("stretch_snooze_max", "Später: wie oft", 0, 5),
        _b("stretch_escalate", "Ignorierte Karte kommt größer wieder"),
        _b("stretch_verify_idle", "„Erledigt“ nur ohne Eingabe"),
        _i("stretch_long_per_day", "Aufwendige Übungen pro Tag", 0, 10),
        _b("stretch_sound", "Ton"),
        Field("stretch_volume", "Lautstärke des Tons", "float", 0.0, 1.0),
    ]),
    ("Wasser", [
        _b("water_reminders", "Wasser-Erinnerung"),
        _i("water_goal_ml", "Tagesziel (ml)", 500, 6000),
        _i("water_portion_ml", "Portion (ml)", 50, 2000),
        Field("water_start", "Von (HH:MM)", "time"),
        Field("water_end", "Bis (HH:MM)", "time"),
        _i("water_interval_min", "Abstand (min)", 15, 1440),
    ]),
    ("Zwischenablage", [
        _i("clipboard_limit", "Einträge im Verlauf", 1, 1000),
        _i("clipboard_autodelete_min", "Automatisch leeren nach (min, 0 = nie)", 0, 100000),
        _b("clipactions_enabled", "Zwischenablage-Aktionen"),
        Field("clipactions_tracking_params", "Zusätzliche Tracking-Parameter", "list", optional=True,
              help="Mit Komma trennen; utm_* o. ä. mit Stern"),
    ]),
    ("Clip-Transfer", [
        _b("clip_send_enabled", "Senden"),
        _b("clip_receive_enabled", "Empfang"),
        _i("clip_max_text_kb", "Größter Text (KB)", 1, 10240),
        _i("clip_max_image_mb", "Größtes Bild (MB)", 1, 500),
        _i("clip_max_file_mb", "Größte Datei (MB)", 1, 8192),
        _i("clip_inbox_keep_days", "Eingang behalten (Tage)", 1, 365),
        _i("clip_inbox_quota_mb", "Eingang höchstens (MB)", 10, 100000),
    ]),
    ("Bildschirm", [
        _b("screenshot_save", "Screenshots im Ordner speichern"),
        Field("screenshot_dir", "Screenshot-Ordner", "path", optional=True, help="Leer = Bilder/LinuxMos"),
        _b("screenshot_open_editor", "Editor nach dem Screenshot öffnen"),
        Field("record_format", "Aufnahme-Format", "choice", choices=(("mp4", "MP4"), ("gif", "GIF"))),
        Field("record_audio", "Aufnahme-Ton", "choice", choices=(("off", "Ohne"), ("system", "Systemton"),
                                                                ("mic", "Mikrofon"))),
        _i("record_fps", "Aufnahme-Bilder pro Sekunde", 1, 60),
        _i("record_max_min", "Aufnahme endet nach (min, 0 = nie)", 0, 1440),
        Field("record_dir", "Aufnahme-Ordner", "path", optional=True, help="Leer = Videos/LinuxMos"),
        Field("ocr_languages", "Sprachen der Texterkennung", "text", help="tesseract-Sprachen mit +, z. B. deu+eng"),
        _b("ocr_keep_linebreaks", "Zeilenumbrüche bei erkanntem Text behalten"),
        _b("qr_open_links", "Links aus QR-Codes sofort öffnen"),
    ]),
    ("Werkzeuge", [
        _b("colorpicker_enabled", "Farbpipette"),
        Field("colorpicker_format", "Farbformat", "choice", choices=(("hex", "HEX"), ("rgb", "RGB"), ("hsl", "HSL"),
                                                                    ("hsv", "HSV"))),
        _i("colorpicker_history", "Letzte Farben", 1, 200),
        _b("keepawake_enabled", "Wach halten"),
        _i("keepawake_minutes", "Wach halten: automatisch aus nach (min, 0 = nie)", 0, 1440),
        _b("pin_enabled", "Fenster anpinnen"),
        _b("pin_release_on_exit", "Pins beim Beenden der Insel aufheben"),
    ]),
    ("Benachrichtigungen & Live-Hinweise", [
        _b("notifications_on_island", "Benachrichtigungen als Karte"),
        _b("notifications_dnd", "Nicht stören (Insel)"),
        _b("privacy_indicator", "Mikrofon- und Kamera-Punkt"),
        _b("vpn_status", "VPN-Status"),
        _b("vpn_lookup", "VPN: Land und IP abfragen (ipinfo.io)"),
        _b("downloads_progress", "Download-Fortschritt"),
        Field("downloads_dir", "Download-Ordner", "path", optional=True, help="Leer = Download-Ordner des Systems"),
    ]),
    ("Suche", [
        Field("command_bar_engine", "Suchmaschine", "choice",
              choices=(("duckduckgo", "DuckDuckGo"), ("google", "Google"), ("startpage", "Startpage"),
                       ("ecosia", "Ecosia"), ("bing", "Bing"), ("brave", "Brave")), free=True,
              help="Oder eine eigene Adresse mit %s für die Suche"),
        _b("command_bar_files", "Dateien durchsuchen"),
        _b("command_bar_currency", "Währungen umrechnen"),
    ]),
    ("KI", [
        _b("ai_chat", "Chat-Tab"),
        _b("ai_voice", "Diktat"),
        _b("ai_voice_autopaste", "Diktat direkt einfügen"),
        Field("ai_base_url", "Adresse des Servers", "url", optional=True, help="Bis /v1; leer = OpenAI"),
        Field("ai_model", "Chat-Modell", "text", optional=True),
        Field("ai_stt_model", "Modell für Diktat", "text", optional=True),
        _i("ai_history", "Mitgeschickte Nachrichten", 1, 200),
        Field("ai_voice_language", "Sprache des Diktats", "text", optional=True, help="Code wie de; leer = erkennen"),
        _i("ai_voice_max_s", "Längstes Diktat (s)", 5, 3600),
    ]),
]

FIELDS = {field.key: field for _name, fields in GROUPS for field in fields}

# Config keys that have no input here on purpose (set by the island, by a command, or not a plain value)
NOT_EDITED = frozenset({
    "latitude", "longitude", "stretch_off_date", "notifications_exclude", "clip_default_peer", "clip_peers",
    "hotkeys", "gestures", "overview_intro_seen", "ai_system_prompt",
})


def validate(key, value):
    """(ok, normalized value, message). The message is German and short; it is empty when ok."""
    field = FIELDS.get(key)
    if field is None:
        return False, value, "Unbekannter Schlüssel"
    kind = field.kind
    if kind == "bool":
        if isinstance(value, bool):
            return True, value, ""
        return False, value, "Ja oder Nein"
    if kind in ("int", "float"):
        if isinstance(value, str):
            try:
                value = float(value.strip().replace(",", "."))
            except ValueError:
                return False, value, "Eine Zahl eingeben"
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value != value:
            return False, value, "Eine Zahl eingeben"
        if kind == "int":
            if value != int(value):
                return False, value, "Eine ganze Zahl eingeben"
            value = int(value)
        if value < field.low or value > field.high:
            return False, value, f"Zwischen {_num(field.low)} und {_num(field.high)}"
        return True, value, ""
    if not isinstance(value, (str, list)):
        return False, value, "Text eingeben"
    if kind == "list":
        items = value if isinstance(value, list) else [p.strip() for p in value.split(",")]
        items = [p.strip() for p in items if isinstance(p, str) and p.strip()]
        return True, items, ""
    text = value.strip() if isinstance(value, str) else ""
    if not text:
        return (True, "", "") if field.optional else (False, text, "Darf nicht leer sein")
    if kind == "choice":
        known = {v for v, _l in field.choices}
        if text in known:
            return True, text, ""
        if field.free:
            if field.key == "monitor":
                return True, int(text) if text.isdigit() else text, ""
            if field.key == "command_bar_engine" and "%s" not in text:
                return False, text, "Eigene Adresse mit %s für die Suche"
            return True, text, ""
        return False, text, "Keine gültige Auswahl"
    if kind == "time":
        return (True, text, "") if HHMM.match(text) else (False, text, "Uhrzeit als HH:MM")
    if kind == "url":
        return (True, text.rstrip("/"), "") if re.match(r"^https?://\S+$", text) else \
            (False, text, "Adresse mit http:// oder https://")
    if field.key == "ocr_languages":
        return (True, text, "") if LANG_LIST.match(text) else (False, text, "Sprachen mit + verbinden, z. B. deu+eng")
    return True, text, ""


def _num(value):
    return str(int(value)) if value == int(value) else str(value).replace(".", ",")
