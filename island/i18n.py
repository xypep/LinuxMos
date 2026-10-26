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
    "Antwort nicht lesbar": "Unreadable answer",
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

    # Live marks: microphone, camera, VPN, downloads
    "Live-Hinweise": "Live hints",
    "Mikrofon & Kamera": "Microphone & camera",
    "VPN-Status": "VPN status",
    "VPN: Land & IP (fragt ipinfo.io)": "VPN: country & IP (asks ipinfo.io)",
    "Download-Fortschritt": "Download progress",
    "Mikrofon aktiv · {apps}": "Microphone on · {apps}",
    "Kamera aktiv · {apps}": "Camera on · {apps}",
    "Kamera & Mikrofon aktiv · {apps}": "Camera & microphone on · {apps}",
    "Mikrofon stumm": "Microphone muted",
    "Mikrofon an": "Microphone on",
    "Mikrofon: {apps} · Klick = stumm": "Microphone: {apps} · click = mute",
    "Mikrofon stumm: {apps} · Klick = an": "Microphone muted: {apps} · click = unmute",
    "Kamera: {apps}": "Camera: {apps}",
    "VPN verbunden · {name}": "VPN connected · {name}",
    "VPN getrennt": "VPN disconnected",
    "Download": "Download",
    "Download · {name}": "Download · {name}",
    "Download fertig · {name}": "Download finished · {name}",

    # Command bar
    "Suche  (Ctrl+Alt+Space)": "Search  (Ctrl+Alt+Space)",
    "Suche": "Search",
    "Suche öffnen  (Ctrl+Alt+Space)": "Open search  (Ctrl+Alt+Space)",
    "Dateien durchsuchen": "Search files",
    "Währungen (fragt frankfurter.dev)": "Currencies (asks frankfurter.dev)",
    "Websuche mit": "Search the web with",
    "Apps, Dateien, Rechnen, Web …": "Apps, files, maths, web …",
    "Apps starten · Dateien finden · 12*7 · 5 km in mi · 20 usd in eur · Websuche":
        "Launch apps · find files · 12*7 · 5 km in mi · 20 usd in eur · web search",
    "↵ öffnen · Ctrl+↵ einfügen bzw. im Ordner zeigen · Esc schließt":
        "↵ open · Ctrl+↵ paste or show in folder · Esc closes",
    "App": "App",
    "Datei": "File",
    "Ordner": "Folder",
    "Web": "Web",
    "Rechner": "Calculator",
    "Einheit": "Unit",
    "Umrechnung": "Conversion",
    "Währung": "Currency",
    "Dateien werden gesucht …": "Searching files …",
    "Website öffnen": "Open website",
    "„{query}“ im Web suchen": "Search the web for “{query}”",
    "Wechselkurse werden geladen …": "Loading exchange rates …",
    "Wechselkurse nicht erreichbar (offline?)": "Exchange rates not reachable (offline?)",
    "EZB-Kurs vom {date}": "ECB rate of {date}",
    "{app} lässt sich nicht starten": "Can't start {app}",
    "Lässt sich nicht öffnen": "Can't open it",
    "Kopiert · {text}": "Copied · {text}",

    # Monitor
    "Monitor": "Monitor",
    "Hauptmonitor": "Primary monitor",
    "Monitor mit der Maus (beim Öffnen)": "Monitor with the mouse (when opened)",
    "{monitor} (Hauptmonitor)": "{monitor} (primary)",
    "{monitor} (nicht angeschlossen)": "{monitor} (not connected)",

    # Mascots
    "Anzeigen, wenn ich weg bin": "Show while I am away",
    "Augen": "Eyes",
    "Katze": "Cat",
    "Roboter": "Robot",
    "Blob": "Blob",

    # Screen recording
    "Bildschirmaufnahme": "Screen recording",
    "Bereich aufnehmen  (Ctrl+Alt+R)": "Record area  (Ctrl+Alt+R)",
    "Bildschirm aufnehmen  (Ctrl+Alt+Shift+R)": "Record screen  (Ctrl+Alt+Shift+R)",
    "Aufnahme beenden": "Stop recording",
    "Format": "Format",
    "Ton (nur MP4)": "Sound (MP4 only)",
    "Ohne Ton": "No sound",
    "Systemton": "System sound",
    "Mikrofon": "Microphone",
    "MosIsland · Aufnahme läuft, ein Klick beendet sie": "MosIsland · recording, a click stops it",
    "Für Aufnahmen fehlt: {programs}": "Recording needs: {programs}",
    "Bereich zu klein": "Area too small",
    "Aufnahme fehlgeschlagen": "Recording failed",
    "GIF wird erstellt …": "Making the GIF …",
    "GIF-Erstellung fehlgeschlagen": "Could not make the GIF",
    "Aufnahme gespeichert": "Recording saved",
    "Abspielen": "Play",
    "Im Ordner zeigen": "Show in folder",

    # AI chat and dictation
    "KI": "AI",
    "KI-Chat  (Ctrl+Alt+A)": "AI chat  (Ctrl+Alt+A)",
    "Chat-Tab  (Ctrl+Alt+A)": "Chat tab  (Ctrl+Alt+A)",
    "Diktat  (Ctrl+Alt+M)": "Dictation  (Ctrl+Alt+M)",
    "Diktat direkt einfügen": "Paste dictation right away",
    "Verbindung & API-Key …": "Connection & API key …",
    "API-Key entfernen": "Remove API key",
    "KI-Verbindung": "AI connection",
    "Abbrechen": "Cancel",
    "Speichern": "Save",
    "Adresse": "Address",
    "OpenAI-kompatibler Server, z. B. http://localhost:11434/v1 für Ollama":
        "OpenAI-compatible server, e.g. http://localhost:11434/v1 for Ollama",
    "Chat-Modell": "Chat model",
    "Modell für Diktat": "Model for dictation",
    "API-Key": "API key",
    "Der Key liegt im Schlüsselbund, nicht in config.json. Fragen und Diktate gehen an die Adresse "
    "oben. Leer lassen = der gespeicherte Key bleibt. Ein lokaler Server braucht keinen Key.":
        "The key lives in the keyring, not in config.json. Questions and dictations go to the address "
        "above. Leave empty = the stored key stays. A local server needs no key.",
    "Key entfernen": "Remove key",
    "gespeichert (zum Ändern neuen Key eintippen)": "stored (type a new key to change it)",
    "KI-Chat ist aus · Tray-Menü › KI": "AI chat is off · tray menu › AI",
    "Diktat ist aus · Tray-Menü › KI": "Dictation is off · tray menu › AI",
    "Adresse muss mit http:// oder https:// beginnen": "The address must start with http:// or https://",
    "API-Key im Schlüsselbund gespeichert": "API key saved in the keyring",
    "Key nicht gespeichert: Schlüsselbund nicht erreichbar (libsecret-tools?)":
        "Key not saved: keyring not reachable (libsecret-tools?)",
    "API-Key entfernt": "API key removed",
    "Key nicht entfernt": "Key not removed",
    "Für das Diktat fehlt: {programs}": "Dictation needs: {programs}",
    "Diktat lässt sich nicht starten": "Can't start the dictation",
    "Diktat · sprich jetzt, Ctrl+Alt+M beendet": "Dictation · speak now, Ctrl+Alt+M ends it",
    "Zu kurz, nichts aufgenommen": "Too short, nothing recorded",
    "Wird aufgeschrieben …": "Writing it down …",
    "Kein API-Key gespeichert · Tray-Menü › KI › Verbindung": "No API key stored · tray menu › AI › Connection",
    "Nichts verstanden": "Nothing understood",
    "Diktat eingefügt": "Dictation pasted",
    "Diktat · kopiert": "Dictation · copied",
    "Einfügen": "Paste",
    "Neues Gespräch": "New conversation",
    "Frag etwas. Der Chat spricht mit dem Server aus den Einstellungen (Zahnrad), das Gespräch bleibt nur "
    "im Arbeitsspeicher.":
        "Ask something. The chat talks to the server from the settings (gear); the conversation only "
        "stays in memory.",
    "Frag etwas …  (↵ sendet)": "Ask something …  (↵ sends)",
    "Kein API-Key gespeichert. Zahnrad oben rechts: „Verbindung & API-Key …“":
        "No API key stored. Gear at the top right: “Connection & API key …”",
    "Noch kein API-Key – Zahnrad oben rechts": "No API key yet – gear at the top right",
    "Stopp": "Stop",
    "Senden": "Send",
    "Antwort kopieren": "Copy answer",
    "Du bist ein hilfreicher Assistent auf einem Linux-Desktop. Antworte knapp und in der Sprache des Nutzers.":
        "You are a helpful assistant on a Linux desktop. Keep answers short and reply in the user's language.",
    "Server nicht erreichbar (Adresse und Verbindung prüfen)": "Server not reachable (check address and connection)",
    "Keine Antwort vom Server (Zeitüberschreitung)": "No answer from the server (timeout)",
    "Leere Antwort": "Empty answer",
    "API-Key abgelehnt (HTTP {status})": "API key rejected (HTTP {status})",
    "Adresse oder Modell nicht gefunden (HTTP {status})": "Address or model not found (HTTP {status})",
    "Zu viele Anfragen oder Guthaben aufgebraucht (HTTP {status})":
        "Too many requests or credit used up (HTTP {status})",
    "Server meldet einen Fehler (HTTP {status})": "The server reports an error (HTTP {status})",
    "Anfrage fehlgeschlagen": "Request failed",

    # Command line
    "Wetter-Ort gesetzt: {city}": "Weather location set: {city}",
    "secret-tool fehlt: sudo apt install libsecret-tools": "secret-tool is missing: sudo apt install libsecret-tools",
    "API-Key (die Eingabe bleibt unsichtbar): ": "API key (the input stays invisible): ",
    "Kein Key eingegeben.": "No key entered.",
    "Der Schlüsselbund hat den Key nicht angenommen (läuft gnome-keyring?).":
        "The keyring did not take the key (is gnome-keyring running?).",
    "API-Key im Schlüsselbund gespeichert.": "API key saved in the keyring.",
}
