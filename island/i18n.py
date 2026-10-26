"""UI language: German source strings with an English translation table.

    _("Lautstärke {percent} %").format(percent=40)

returns the text in the active language. The language is picked once at
start-up (config "language": auto | de | en; auto follows the session's
locale, anything that is not German gets English). Switching it in the tray
restarts the island, so no widget ever has to be relabelled live.

Dates are formatted here too, independent of the system locale (LC_TIME),
so the clock always matches the UI language.
"""

import os

LANGUAGES = {"de": "Deutsch", "en": "English"}  # endonyms: never translated
_lang = "de"


def detect():
    """Language of the session: the first locale variable that is set decides."""
    for var in ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
        value = os.environ.get(var, "").split(":")[0]
        if value:
            return "de" if value.lower().startswith("de") else "en"
    return "en"


def resolve(choice):
    """Config value (auto | de | en) -> the language actually used."""
    return choice if choice in LANGUAGES else detect()


def setup(choice):
    global _lang
    _lang = resolve(choice)


def current():
    return _lang


def _(text):
    if _lang == "de":
        return text
    return EN.get(text, text)


def n_(singular, plural, n):
    """Singular for n == 1, else plural (same rule in German and English)."""
    return _(singular if n == 1 else plural)


# ---- numbers & dates -----------------------------------------------------------
WEEKDAYS = {"de": ("Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"),
            "en": ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")}
MONTHS = {"de": ("Jan", "Feb", "Mär", "Apr", "Mai", "Jun", "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"),
          "en": ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")}


def decimal(value, digits=1):
    """1.5 -> '1,5' in German, '1.5' in English."""
    text = f"{value:.{digits}f}"
    return text.replace(".", ",") if _lang == "de" else text


def weekday(index):
    """0 = Monday (datetime.weekday())."""
    return WEEKDAYS[_lang][index]


def day_month(when):
    """Short date without year: '26.10.' / 'Oct 26'."""
    if _lang == "de":
        return when.strftime("%d.%m.")
    return f"{MONTHS['en'][when.month - 1]} {when.day}"


def header_date(when):
    """Date and time in the opened island's header: 'Mo 26. Okt  14:30' / 'Mon Oct 26  14:30'."""
    day, month = weekday(when.weekday()), MONTHS[_lang][when.month - 1]
    date = f"{day} {when.day}. {month}" if _lang == "de" else f"{day} {month} {when.day}"
    return f"{date}  {when:%H:%M}"


# ---- English translations ----------------------------------------------------------
# Key: the German text exactly as written in the code (placeholders included).
EN = {
    # Tabs
    "Jetzt": "Now",
    "Zwischenablage": "Clipboard",
    "Ablage": "Shelf",
    "Aufgaben": "To-do",
    "Notiz & Fokus": "Note & Focus",
    "Wasser": "Water",
    "Wetter": "Weather",
    "Steuerung": "Controls",

    # Folded island: live activities
    "Wiedergabe": "Playing",
    "Kopiert": "Copied",
    "Stumm": "Muted",
    "Lautstärke {percent} %": "Volume {percent} %",
    "Helligkeit {percent} %": "Brightness {percent} %",
    "Feststelltaste an": "Caps Lock on",
    "Feststelltaste aus": "Caps Lock off",
    "Tastatur: {name}": "Keyboard: {name}",
    "Verbunden · {name}": "Connected · {name}",
    "Wieder online": "Back online",
    "Keine Verbindung": "No connection",
    "{name} · verbunden": "{name} · connected",
    "{name} getrennt": "{name} disconnected",
    "Bluetooth-Gerät": "Bluetooth device",
    "{n} Datei abgelegt": "{n} file dropped",
    "{n} Dateien abgelegt": "{n} files dropped",
    "Lädt · {percent} %": "Charging · {percent} %",
    "Regen in etwa 1 Std.": "Rain in about 1 h",
    "Zeit für Wasser · Klick = +{ml} ml": "Time for water · click = +{ml} ml",

    # Timer & Pomodoro
    "Timer": "Timer",
    "Fokus": "Focus",
    "Pause": "Break",
    "Fokus geschafft": "Focus done",
    "Zeit für {minutes} Minuten Pause.": "Time for a {minutes} minute break.",
    "Fokus geschafft · {minutes} min Pause": "Focus done · {minutes} min break",
    "Pause vorbei": "Break is over",
    "Klick auf die Insel startet die nächste Fokus-Runde.": "Click the island to start the next focus round.",
    "Pause vorbei · Klick = weiter": "Break over · click = go on",
    "Timer abgelaufen": "Time's up",
    "{time} sind um.": "{time} are up.",
    "Erinnerung": "Reminder",

    # Lyrics
    "Lade Lyrics …": "Loading lyrics …",
    "Nur unsynchronisierte Lyrics verfügbar": "Only unsynced lyrics available",
    "Keine Lyrics gefunden": "No lyrics found",
    "Lyrics gerade nicht erreichbar (offline?)": "Lyrics not reachable right now (offline?)",
    "Aktuelle Zeile in der Pille zeigen": "Show the current line in the pill",

    # Now
    "Gerade läuft nichts": "Nothing playing",
    "Spotify, Firefox, VLC & Co. erscheinen hier automatisch":
        "Spotify, Firefox, VLC & co. show up here automatically",
    "Unbekannter Titel": "Unknown title",
    "Kein Timer": "No timer",
    "WLAN, Ton, Theme": "Wi-Fi, sound, theme",
    "Ort festlegen": "Set location",
    "nicht verfügbar": "unavailable",
    "Lädt": "Charging",
    "Akku": "Battery",

    # Clipboard
    "Verlauf durchsuchen …": "Search history …",
    "Verlauf leeren (Angepinntes bleibt)": "Clear history (pinned items stay)",
    "Noch nichts kopiert – alles, was du kopierst, landet hier.":
        "Nothing copied yet – everything you copy lands here.",
    "Bild · {w}×{h}": "Image · {w}×{h}",
    "Anpinnen": "Pin",
    "Entfernen": "Remove",

    # Shelf
    "Alle ziehen": "Drag all",
    "Ablage leeren": "Clear shelf",
    "Dateien auf die Insel ziehen": "Drop files on the island",
    "Sie warten hier, bis du sie woanders hinziehst.": "They wait here until you drag them somewhere else.",
    "{n} Datei": "{n} file",
    "{n} Dateien": "{n} files",
    "{name}\nZiehen zum Ablegen · Doppelklick öffnet": "{name}\nDrag to drop · double-click opens",
    "Aus der Ablage entfernen": "Remove from shelf",

    # Note & timer
    "Notiz": "Note",
    "Fokus 25": "Focus 25",
    "Pause 5": "Break 5",
    "Pomodoro: 25 min Fokus, dann Pause": "Pomodoro: 25 min focus, then a break",
    "Start": "Start",
    "Stoppen": "Stop",

    # To-do
    "Neue Aufgabe …": "New task …",
    "Erinnerung: 14:30 · 9 · in 20 min · in 2 h (leer = keine)":
        "Reminder: 14:30 · 9 · 2pm · in 20 min · in 2 h (empty = none)",
    "Hinzufügen": "Add",
    "Nichts zu tun – genieß den Moment.": "Nothing to do – enjoy the moment.",
    "Zeit nicht verstanden – z. B. 14:30, 9, in 20 min, in 2 h":
        "Time not understood – e.g. 14:30, 9, 2pm, in 20 min, in 2 h",
    "{done}/{total} heute erledigt": "{done}/{total} done today",
    "morgen {time}": "tomorrow {time}",
    "Löschen": "Delete",

    # Water
    "Trinken": "Drink",
    "Letzten Eintrag zurücknehmen": "Undo last entry",
    "Einstellungen": "Settings",
    "Heute pro Stunde (ml)": "Today per hour (ml)",
    "Portion (Flasche/Glas)": "Portion (bottle/glass)",
    "Tagesziel": "Daily goal",
    "Erinnern alle": "Remind every",
    "bis": "to",
    "Erinnerungen": "Reminders",
    "Aktive Zeit": "Active hours",
    "Heute · {pct} %": "Today · {pct} %",
    " · Ziel erreicht 🎉": " · goal reached 🎉",

    # Weather
    "Für welchen Ort soll das Wetter angezeigt werden?": "Which place should the weather be shown for?",
    "z. B. Berlin": "e.g. London",
    "Speichern": "Save",
    "Vorhersage: MET Norway · Ortssuche: OpenStreetMap · kein Konto nötig":
        "Forecast: MET Norway · place search: OpenStreetMap · no account needed",
    "Ort ändern": "Change location",
    "Aktualisieren": "Refresh",
    "Lade Wetter …": "Loading weather …",
    "{hour} Uhr": "{hour}:00",
    "Daten: MET Norway (CC BY 4.0)": "Data: MET Norway (CC BY 4.0)",
    "Wetter nicht verfügbar": "Weather unavailable",
    "Ort „{city}“ nicht gefunden": "Place “{city}” not found",
    "Klar": "Clear",
    "Heiter": "Fair",
    "Teils bewölkt": "Partly cloudy",
    "Bewölkt": "Cloudy",
    "Nebel": "Fog",
    "Leichte Schauer": "Light showers",
    "Schauer": "Showers",
    "Starke Schauer": "Heavy showers",
    "Leichter Regen": "Light rain",
    "Starker Regen": "Heavy rain",
    "Regen": "Rain",
    "Schneeregen": "Sleet",
    "Leichter Schnee": "Light snow",
    "Starker Schnee": "Heavy snow",
    "Schnee": "Snow",
    "Gewitter": "Thunderstorm",

    # Controls
    "WLAN": "Wi-Fi",
    "Nicht stören": "Do not disturb",
    "Mikro aus": "Mic off",
    "Sperren": "Lock",
    "Ruhezustand": "Suspend",
    "Neustart": "Restart",
    "Aus": "Shut down",
    "Nochmal?": "Again?",

    # Screenshot & editor
    "Screenshot kopiert · Klick = bearbeiten": "Screenshot copied · click = edit",
    "Screenshot kopiert": "Screenshot copied",
    "Für Screenshots fehlt: {programs}": "Screenshots need: {programs}",
    "Gespeichert & kopiert": "Saved & copied",
    "Bearbeiten": "Edit",
    "Screenshot bearbeiten": "Edit screenshot",
    "Pfeil (A)": "Arrow (A)",
    "Rechteck (R)": "Rectangle (R)",
    "Marker (M)": "Highlighter (M)",
    "Text (T)": "Text (T)",
    "Verpixeln – für private Daten (B)": "Pixelate – for private data (B)",
    "Farbe ({key})": "Color ({key})",
    "Speichern und kopieren (Ctrl+S)": "Save and copy (Ctrl+S)",
    "In die Zwischenablage (Ctrl+C)": "Copy to clipboard (Ctrl+C)",
    "Rückgängig (Ctrl+Z)": "Undo (Ctrl+Z)",
    "Text eingeben, Enter": "Type text, Enter",
    "Fertig": "Done",
    "Schließen (Esc)": "Close (Esc)",
    "Verwerfen?": "Discard?",
    "Ungespeicherte Markierungen – nochmal zum Verwerfen": "Unsaved markup – again to discard",
    "Bereich aufnehmen  (Ctrl+Alt+S)": "Capture area  (Ctrl+Alt+S)",
    "Bildschirm aufnehmen  (Ctrl+Alt+Shift+S)": "Capture screen  (Ctrl+Alt+Shift+S)",
    "Im Ordner speichern": "Save to folder",
    "Editor sofort öffnen": "Open editor right away",
    "Ordner öffnen": "Open folder",

    # Tray
    "MosIsland öffnen": "Open MosIsland",
    "Mit Cinnamon starten": "Start with Cinnamon",
    "Maskottchen": "Mascot",
    "Minimal-Notch": "Minimal notch",
    "Lautstärke & Helligkeit anzeigen": "Show volume & brightness",
    "Zwischenablage automatisch leeren": "Clear clipboard automatically",
    "Nie": "Never",
    "Nach 15 Minuten": "After 15 minutes",
    "Nach 1 Stunde": "After 1 hour",
    "Nach 24 Stunden": "After 24 hours",
    "Nach {minutes} Minuten": "After {minutes} minutes",
    "Automatisch (System)": "Automatic (system)",
    "Über MosIsland": "About MosIsland",
    "Beenden": "Quit",
    "Dynamic Island für Linux Mint Cinnamon – Teil von LinuxMos.\n"
    "Inspiriert von Island (exuupery) und Nusa (rama2555) – eigene Umsetzung.":
        "Dynamic Island for Linux Mint Cinnamon – part of LinuxMos.\n"
        "Inspired by Island (exuupery) and Nusa (rama2555) – an independent implementation.",

    # Text & QR codes from the screen
    "Text & QR": "Text & QR",
    "Text erkennen  (Ctrl+Alt+O)": "Recognise text  (Ctrl+Alt+O)",
    "QR-Code lesen  (Ctrl+Alt+Q)": "Read QR code  (Ctrl+Alt+Q)",
    "Zeilenumbrüche behalten": "Keep line breaks",
    "Links aus QR-Codes sofort öffnen": "Open links from QR codes right away",
    "Texterkennung": "text recognition",
    "QR-Codes": "QR codes",
    "Für {what} fehlt: {programs}": "Missing for {what}: {programs}",
    "Für Texterkennung fehlt: {programs}": "Missing for text recognition: {programs}",
    "Text wird erkannt …": "Recognising text …",
    "Sprachdaten fehlen: {languages}": "Language data missing: {languages}",
    "Texterkennung fehlgeschlagen": "Text recognition failed",
    "Kein Text gefunden": "No text found",
    "Text erkannt · kopiert": "Text recognised · copied",
    "{n} Zeichen": "{n} characters",
    "Schließen": "Close",
    "In Notiz": "To note",
    "Kopieren": "Copy",
    "In Notiz eingefügt · Klick = öffnen": "Added to note · click = open",
    "QR-Erkennung fehlgeschlagen": "QR recognition failed",
    "Kein QR-Code gefunden": "No QR code found",
    "{n} Code": "{n} code",
    "{n} Codes": "{n} codes",
    "WLAN „{ssid}“ · Passwort kopiert": "Wi-Fi “{ssid}” · password copied",
    "WLAN „{ssid}“ · Name kopiert": "Wi-Fi “{ssid}” · name copied",
    "Passwort: {password}": "Password: {password}",
    "Offenes Netz ohne Passwort": "Open network without a password",
    "Verbinden": "Connect",
    "Verbinde mit {ssid} …": "Connecting to {ssid} …",
    "WLAN-Verbindung fehlgeschlagen": "Wi-Fi connection failed",
    "Öffnen": "Open",
    "Link kopiert": "Link copied",
    "Link lässt sich nicht öffnen": "Can't open the link",
    "{kind} · kopiert": "{kind} · copied",
    "Codes kopiert": "Codes copied",
    "QR-Code · kopiert": "QR code · copied",
    "Text": "Text",
    "Text erkennen und kopieren (O)": "Recognise and copy text (O)",
    "Text kopiert ({n} Zeichen)": "Text copied ({n} characters)",

    # Notifications
    "Benachrichtigungen": "Notifications",
    "Auf der Insel anzeigen": "Show on the island",
    "Auf der Insel ausblenden:": "Hide on the island:",
    "Noch keine Benachrichtigungen": "No notifications yet",
    "Benachrichtigungen von {app} ausblenden": "Hide notifications from {app}",
    "{app} ausgeblendet · Tray → Benachrichtigungen": "{app} hidden · tray → Notifications",

    # Command line
    "Wetter-Ort gesetzt: {city}": "Weather location set: {city}",
}
