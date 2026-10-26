> [!NOTE]
> **Vibe-coded Projekt** – Dieses Projekt wurde größtenteils mit KI-Unterstützung (Claude) entwickelt.
> Der Code funktioniert für meinen Anwendungsfall, ist aber nicht professionell geprüft. Nutzung auf eigene Verantwortung.

**Deutsch** · [English](README.en.md)

# LinuxMos

Macht Linux Mint Cinnamon zum leichtgewichtigen macOS-Look-alike – mit Dock, Top Bar, Widgets, Spotlight und optional einer Dynamic Island – ohne dass der Desktop im Leerlauf CPU frisst.

![MosIsland](https://img.shields.io/badge/MosIsland-1.12.0-blue)
![Platform](https://img.shields.io/badge/platform-Linux%20Mint%2022%20Cinnamon-87CF3E)
![Display server](https://img.shields.io/badge/display-X11-lightgrey)

---

## Preview

<p align="center">
  <img src="docs/img/island-home.png" alt="MosIsland aufgeklappt: Musik mit Cover, Wetter, Pomodoro-Timer" width="45%">
  &nbsp;
  <img src="docs/img/island-pills-nusa.png" alt="MosIsland eingeklappt: Lyrics, Pomodoro, Wasser-Erinnerung, Kopfhörer, Helligkeit, Feststelltaste" width="45%">
</p>

---

## Inhaltsverzeichnis

- [Features](#features)
- [Voraussetzungen](#voraussetzungen)
- [Installation](#installation)
- [Nutzung](#nutzung)
- [Wichtige Hinweise](#wichtige-hinweise)
- [Konfiguration](#konfiguration)
- [Dehn-Erinnerung](#dehn-erinnerung)
- [Tests](#tests)
- [Bekannte Probleme](#bekannte-probleme)
- [Roadmap](#roadmap)
- [Lizenz](#lizenz)
- [Credits](#credits)

> Die ausführliche Schritt-für-Schritt-Anleitung (auch ohne Script, alles von Hand) steht in [docs/ANLEITUNG.md](docs/ANLEITUNG.md), alle Einstellungen mit Standardwert und gültigem Bereich in [docs/CONFIG.md](docs/CONFIG.md).

---

## Features

**macOS-Look** (`install.sh`)
- **Theme** – WhiteSur (GTK 3/4, Cinnamon, Fensterrahmen) mit Ampel-Buttons links, Icons, Cursor, Wallpaper, Schrift Inter
- **Top Bar** – Cinnamon-Panel oben (28 px), Logo-Menü, Uhr im macOS-Format
- **Dock** – Plank mit Glass-Theme und Zoom beim Hovern
- **Animationen** – schnelle Fenster-Effekte, `--minimal` schaltet alle ab
- **Widgets** – Conky-Uhr und Glass-System-Widget (CPU, RAM, Disk, Akku, optional Wetter)
- **Spotlight** – `Super+Space` öffnet eine rofi-Suche (Apps, Befehle, Fenster, Dateien)
- **Backup & Undo** – optionaler Timeshift-Snapshot, Sicherung aller geänderten Einstellungen, `uninstall.sh`
- **Update** – `update.sh` holt neue Versionen, ohne deine Einstellungen anzufassen

<img src="docs/img/widgets.png" alt="Conky-Uhr und System-Widget" width="70%">

**MosIsland** (optional, `--island`) – eine Dynamic Island oben in der Mitte, inspiriert von [Island](https://github.com/exuupery/island) und [Nusa](https://rama2555.github.io/nusa/). Eigener Name, damit sie nicht mit exuuperys Island verwechselt wird; der Befehl bleibt `linuxmos-island`.
- **Musik** von jedem MPRIS-Player (Spotify, Firefox/YouTube, VLC …) mit Cover, Play/Pause/Skip und Spulen
- **Synced Lyrics** (LRCLIB) – Zeile leuchtet mit, Klick springt hin, optional in der Pille
- **Zwischenablage** – Verlauf mit Suche und Pins, ein Klick fügt direkt ins aktive Fenster ein, optional automatisch leeren nach X Minuten (Pins bleiben)
- **Ablage** – Dateien auf die Insel ziehen und später wieder herausziehen
- **Aufgaben** mit Erinnerung, **Notiz**, **Pomodoro** und Timer, **Wasser-Erinnerung** mit Tagesziel und Diagramm
- **Wetter** (MET Norway, ohne API-Key) mit Regenwarnung
- **Screenshots** – Bereich (`Ctrl+Alt+S`) oder Bildschirm unter der Maus (`Ctrl+Alt+Shift+S`), sofort in der Zwischenablage und in `~/Bilder/LinuxMos`; die Insel blendet sich dafür aus. Klick auf den Hinweis öffnet den **Markup-Editor** im Look der Insel (schwarz, schwebende Werkzeug-Pille): Pfeil, Rechteck, Marker, Text und Verpixeln für private Daten
- **Text vom Bildschirm (OCR)** – `Ctrl+Alt+O`, Bereich aufziehen: tesseract (Deutsch + Englisch) erkennt den Text, er landet in der Zwischenablage und als **Karte** auf der Insel (Vorschau, „In Notiz“, „Kopieren“). Auch im Screenshot-Editor per Button „Text“
- **QR-Codes & Barcodes** – `Ctrl+Alt+Q`: Inhalt in die Zwischenablage, bei Links ein „Öffnen“-Button, bei WLAN-Codes wird das Passwort kopiert und „Verbinden“ angeboten
- **Benachrichtigungen als Karte** – jede Benachrichtigung erscheint oben auf der Insel: App-Icon, Bild (Avatar, Cover), Titel, Text, verschwindet von selbst; kommen mehrere, ersetzt die neueste die alte und zählt mit („+2“). Klick holt die App nach vorne, 🔕 blendet eine App aus. Cinnamon bleibt der Benachrichtigungs-Dienst, die Insel liest nur mit; der Verlauf bleibt im Benachrichtigungs-Applet
- **Command Bar** – `Ctrl+Alt+Space` oder der Lupen-Tab: ein Eingabefeld für Apps, Dateien (zuletzt benutzte + Home-Ordner), Rechner (`12*7`, `sqrt(2)`, `50*20%`), Einheiten (`5 km in mi`, `100 f in c`, `1 GiB in MB`), Währungen (`20 usd in eur`, EZB-Kurse) und Websuche (DuckDuckGo, Google, Startpage …). `Enter` öffnet bzw. kopiert, `Ctrl+Enter` fügt das Ergebnis ins vorige Fenster ein oder zeigt die Datei im Ordner. Die rofi-Spotlight-Suche (`Super+Space`) bleibt als Alternative
- **Steuerung** – WLAN, Bluetooth, Nicht stören, Dark Mode, Mikro, Lautstärke, Helligkeit, Screenshot, Sperren, Ruhezustand, Neustart, Aus
- **Live-Hinweise** – Lautstärke, Helligkeit, Feststelltaste, Tastatur-Sprache, Laden, WLAN weg, Kopfhörer verbunden, VPN an/aus (optional mit Land und IP)
- **Mikrofon & Kamera in Benutzung** – oranger Punkt, solange eine App aufnimmt, grüner bei aktiver Kamera (wie bei iOS), mit App-Namen; aufgeklappt sitzt oben ein Mikro-Button zum Stummschalten
- **Download-Fortschritt** – kleiner Ring auf der Insel, solange Firefox oder Chromium/Chrome lädt (bei Chromium mit Prozent), „Download fertig“ mit Klick zur Datei
- **Mehrere Monitore** – die Insel sitzt auf dem Hauptmonitor, einem festen Monitor oder dem, auf dem die Maus steht (wechselt beim Öffnen per Hotkey oder Tray); Ein- und Ausstecken verfolgt sie von selbst
- **Bildschirmaufnahme** – `Ctrl+Alt+R` (Bereich) oder `Ctrl+Alt+Shift+R` (Bildschirm unter der Maus), dieselbe Taste beendet sie. MP4 (H.264, auf Wunsch mit Systemton oder Mikrofon) oder GIF, gespeichert in `~/Videos/LinuxMos`. Die Insel blendet sich aus dem Bild aus, das Tray-Icon wird rot (ein Klick beendet), danach eine Karte mit „Abspielen“ und „Im Ordner zeigen“. Eine vergessene Aufnahme stoppt nach 30 Minuten von selbst
- **KI-Chat & Diktat** (optional, eigener API-Key, standardmäßig aus) – ein Chat-Tab (`Ctrl+Alt+A`), die Antwort läuft live ein. Funktioniert mit jedem OpenAI-kompatiblen Server: OpenAI, OpenRouter, Ollama, LM Studio … Der Key liegt im Schlüsselbund (libsecret), nicht in der Config. **Diktat** (`Ctrl+Alt+M`): sprechen, Taste nochmal drücken – der Text wird ins aktive Fenster getippt (oder landet in der Chat-Zeile)
- **Maskottchen** – im Leerlauf Augen, Katze, Roboter oder Blob; sie dösen ein und winken, wenn du zurückkommst
- **Augen-Modus** – im Leerlauf wächst die Pille, die Figur wird 1,5- bis 3-mal so groß (`eye_mode_scale`), Temperatur und Akku verschwinden; Hover, Klick oder Eingabe bringen alles in ca. 250 ms zurück. Warnungen, Musik, Timer und die Dehn-Karte gehen vor. Setzt eingeschaltetes Maskottchen voraus (`mascot`), sonst bewirkt er nichts
- **Dehn-Erinnerung** – nach 45 Minuten *aktiver* Zeit am Rechner (Eingabe in der letzten Minute) zeigt die Insel eine Karte mit einer Übung und einem weichen Doppelton. „Start“ lässt einen Countdown mit Ring in der Pille laufen, **„Erledigt“ zählt nur, wenn du in der Zeit wirklich nicht getippt hast.** Eine echte Pause (5 min ohne Eingabe) ersetzt das Dehnen, bei Vollbild und während eines Fokus-Timers wartet die Karte. Später, Heute aus, Aus, Statistik pro Tag, eigene Übungen → [Details](#dehn-erinnerung)
- **Einstellungs-Zahnrad** – das Zahnrad oben rechts in der aufgeklappten Insel öffnet `config.json` im Editor, alle Optionen stehen dann drin. Änderungen gelten sofort (inotify, kostet nichts); ein Tippfehler lässt die alten Werte aktiv und meldet die Fehlerstelle auf einer Karte
- **Tray-Menü** – Autostart, Maskottchen (Figur wählen, Augen-Modus), Dehnen (Erinnerung, Heute aus, Jetzt dehnen, Übungen), Minimal-Notch, OSD, Zwischenablage automatisch leeren, Suche (Dateien, Währungen, Suchmaschine), Screenshot, Text & QR, Bildschirmaufnahme (Format, Ton), KI (Chat, Diktat, Verbindung & API-Key), Benachrichtigungen (an/aus, Nicht stören, Apps ausblenden), Live-Hinweise (Mikro & Kamera, VPN, Downloads), Monitor, Sprache, Einstellungen öffnen, Beenden
- **Deutsch oder Englisch** – folgt automatisch der Systemsprache, umschaltbar im Tray-Menü (`Sprache / Language`)

**Leichtgewichtig** – gemessen: Conky-Widgets ~0,03 % CPU, MosIsland ~0,1 % CPU (unter Cinnamon 6, Musik läuft) und ~60 MB RAM. Kein Blur-Compositor, keine Polling-Schleifen.

| MosIsland-RAM (Xvfb, frisches Profil, 10 s nach dem Start) | vorher (1.9.0) | nachher (1.10.0) |
|------------------------------------------------------------|----------------|------------------|
| RSS (was `top` zeigt)                                      | 116 MB         | **60 MB**        |
| PSS (geteilte Bibliotheken anteilig)                       | 87 MB          | **49 MB**        |
| Alle Tabs einmal geöffnet                                  | –              | 62 MB            |
| CPU im Leerlauf (60 s, Xvfb)                               | 0,2 %          | 0,2 %            |

Der größte Brocken (−49 MB) war Mesa: GTK lädt beim Start den OpenGL-Treiber samt LLVM, nur um ein Fenster-Format auszusuchen – die Insel zeichnet aber gar nicht mit OpenGL. Der Rest (−7 MB): Tabs werden erst beim ersten Öffnen gebaut, Wetter/Lyrics/Cover/Kurse kommen über `curl` statt über Pythons HTTPS-Stack, und freier Speicher geht nach dem Zuklappen zurück ans System. Auf echter Hardware hängt die Ersparnis vom Grafiktreiber ab – `linuxmos-perf` zeigt den RAM der Insel.

Aufnahme, Chat und Diktat kosten im Leerlauf nichts: der Chat-Tab entsteht erst beim ersten Öffnen (gemessen 59 MB RSS nach dem Start, +0,7 MB danach, Leerlauf-CPU unverändert), ffmpeg und curl laufen nur, solange du aufnimmst bzw. fragst.

**Paket „Wellbeing“ (1.12.0)** – gemessen in Xvfb mit echtem Muffin, `linuxmos-perf 60`, 12 s nach dem Start:

| MosIsland                                              | RSS     | CPU (60 s) |
|--------------------------------------------------------|---------|------------|
| vorher (1.11.0)                                        | 59,1 MB | 0,5 %      |
| nachher, Dehn-Erinnerung an (Standard)                 | 59,7 MB | 0,5 %      |
| nachher, Dehn-Erinnerung aus                           | 59,5 MB | 0,4 %      |
| nachher, Augen-Modus (groß, `--force-idle`)            | 58,5 MB | 0,8 %      |
| nachher, Augen-Modus aus (normales Maskottchen)        | 58,7 MB | 0,9 %      |

Das Paket kostet etwa 0,6 MB RAM. Die CPU-Werte sind in dieser Umgebung (Software-Rendering, schon vorher 0,5 %) höher als auf echter Hardware (0,1–0,2 %); entscheidend ist der Vergleich: Der Tick der Erinnerung ist nicht messbar (über 120 s mit Tick alle 5 s, also zwölfmal häufiger als im Betrieb: 760 ms CPU, ohne Erinnerung 763 ms). Die Augen kosten groß so viel wie klein – das Blinzeln gab es schon vorher.

---

## Voraussetzungen

- **Linux Mint 22.x Cinnamon** (Basis Ubuntu 24.04), X11-Session
- Ein Benutzer mit `sudo`-Rechten (das Script fragt selbst nach dem Passwort)
- Internetverbindung (apt-Pakete und WhiteSur-Themes von GitHub)
- Optional: **Timeshift** eingerichtet (für den Snapshot vor der Installation)

Alle Pakete installiert `install.sh` selbst, u. a. `plank`, `conky-std`, `rofi`, `fonts-inter`, `sassc`; mit `--island` zusätzlich `python3-gi`, `gir1.2-gtk-3.0`, `gir1.2-wnck-3.0`, `gir1.2-xapp-1.0`, `xdotool`, `pulseaudio-utils`, `iso-codes`, `ffmpeg` (Aufnahme, Diktat) und `libsecret-tools` (API-Key im Schlüsselbund).

---

## Installation

### Option A – mit Git (empfohlen, dann funktioniert `update.sh`)

```bash
git clone https://github.com/xypep/LinuxMos.git
cd LinuxMos
./install.sh                 # nur der macOS-Look
./install.sh --island        # inklusive MosIsland
```

### Option B – als ZIP

1. Auf GitHub **Code → Download ZIP**
2. Archiv entpacken und im Terminal in den Ordner wechseln
3. `./install.sh` starten (Updates später manuell: neue ZIP holen, dann `./update.sh`)

Danach **einmal ab- und wieder anmelden**.

---

## Nutzung

1. Installieren (siehe oben), z. B. `./install.sh --island --weather Berlin`
2. Ab- und wieder anmelden
3. Maus auf die MosIsland oben in der Mitte fahren – sie klappt auf
4. Updates: `./update.sh` · Rückgängig: `./uninstall.sh`

### Optionen von `install.sh`

```bash
./install.sh --help
```

| Option              | Wirkung                                                  |
|---------------------|----------------------------------------------------------|
| `--light`           | Helles Design statt Dark Mode                            |
| `--minimal`         | Alle Animationen aus                                     |
| `--weather CITY`    | Wetter-Ort für Widget und MosIsland                      |
| `--island`          | MosIsland installieren                                   |
| `--no-widgets`      | Keine Conky-Widgets                                      |
| `--no-spotlight`    | Keine Spotlight-Suche                                    |
| `--firefox`         | WhiteSur-Theme auch für Firefox                          |
| `--snapshot` / `--no-snapshot` | Timeshift-Snapshot ohne Nachfrage / nie       |
| `-y`, `--yes`       | Alle Rückfragen mit „ja“ beantworten                     |

### Weitere Befehle

```bash
./update.sh --check          # gibt es eine neue Version?
./update.sh                  # aktualisieren (Einstellungen bleiben)
./update.sh --full           # zusätzlich das Design neu anwenden
./uninstall.sh               # alles zurücksetzen
./uninstall.sh --purge       # zusätzlich Themes und MosIsland-Daten löschen
linuxmos-perf                # CPU-Last des Desktops und RAM der Insel messen
linuxmos-widgets restart     # Conky-Widgets neu starten
linuxmos-island --tab todo   # MosIsland auf einem Tab öffnen
linuxmos-island --shot area  # Screenshot: area (Bereich) | screen (Monitor unter der Maus)
linuxmos-island --ocr        # Text aus einem Bereich erkennen
linuxmos-island --qr         # QR-Code/Barcode aus einem Bereich lesen
linuxmos-island --record area  # Bildschirmaufnahme: area | screen; nochmal aufrufen = beenden
linuxmos-island --chat       # KI-Chat öffnen
linuxmos-island --voice      # Diktat starten, nochmal aufrufen = Text erkennen
linuxmos-island --set-key    # API-Key für den KI-Chat im Schlüsselbund speichern
linuxmos-island --set-city "München"
linuxmos-island --stretch-now   # sofort eine Dehn-Karte zeigen (auch bei laufender Insel)
linuxmos-island --stretch-test  # Test: Intervall 1 Minute, Leerlauf-Schwellen in Sekunden (nur beim Start)
linuxmos-island --force-idle    # Test: Maskottchen/Augen-Modus ohne Warten, Hover beendet es (nur beim Start)
LINUXMOS_LOG=debug linuxmos-island   # Log mit jeder Messung (Standard: info)
```

### Hotkeys

| Hotkey           | Funktion                                                    |
|------------------|-------------------------------------------------------------|
| `Super+Space`    | Spotlight-Suche öffnen/schließen                            |
| `Shift+→`        | In der Suche: Modus wechseln (Apps, Run, Fenster, Dateien)  |
| `Ctrl+Alt+I`     | MosIsland öffnen/schließen                                  |
| `Ctrl+Alt+V`     | Zwischenablage-Verlauf (tippen = suchen, `Enter` = einfügen)|
| `Ctrl+Alt+Space` | Command Bar der MosIsland: Apps, Dateien, Rechner, Einheiten, Währungen, Web (`↑`/`↓`, `Enter`, `Ctrl+Enter`) |
| `Ctrl+Alt+S`     | Screenshot vom Bereich (`Esc` oder Hotkey nochmal = abbrechen) |
| `Ctrl+Alt+Shift+S` | Screenshot vom Bildschirm unter der Maus                  |
| `Ctrl+Alt+O`     | Text aus einem Bereich erkennen (OCR) → Zwischenablage      |
| `Ctrl+Alt+Q`     | QR-Code/Barcode aus einem Bereich lesen → Zwischenablage    |
| `Ctrl+Alt+R`     | Bildschirmaufnahme vom Bereich starten (nochmal = beenden und speichern) |
| `Ctrl+Alt+Shift+R` | Bildschirmaufnahme vom Monitor unter der Maus             |
| `Ctrl+Alt+A`     | KI-Chat öffnen (mit `ai_chat`)                              |
| `Ctrl+Alt+M`     | Diktat: aufnehmen, nochmal drücken = Text erkennen und einfügen (mit `ai_voice`) |
| Im Editor        | `A` Pfeil · `R` Rechteck · `M` Marker · `T` Text · `B` Verpixeln · `O` Text erkennen · `1`–`6` Farbe · `Ctrl+Z` · `Ctrl+C` · `Ctrl+S` = Fertig |
| `Esc`            | MosIsland zuklappen                                         |
| Mausrad auf der Pille | Lautstärke ±5 %                                        |

---

## Wichtige Hinweise

> [!WARNING]
> `install.sh` ändert viele Cinnamon-Einstellungen: Panel nach oben, Fensterliste raus, Theme, Icons, Schrift, Effekte, eigene Tastenkürzel, `Super+Space` wird vom Tastaturlayout-Wechsel abgezogen, mit `--island` wird Cinnamons Lautstärke-OSD abgeschaltet. Vorher wird alles nach `~/.local/share/linuxmos/backup/` gesichert, `./uninstall.sh` stellt es wieder her. Ein Timeshift-Snapshot vorab wird empfohlen.

> [!CAUTION]
> `install.sh` lädt die WhiteSur-Themes direkt von GitHub (vinceliuice) und führt deren Installer aus, außerdem installiert es Pakete per `sudo apt`. Nicht mit `sudo` starten – das Script fragt selbst nach dem Passwort.

> [!IMPORTANT]
> Netzwerkzugriffe: Wetter über api.met.no und nominatim.openstreetmap.org (MosIsland) bzw. wttr.in (Conky), Lyrics über lrclib.net – jeweils nur, wenn du die Funktion nutzt. Wechselkurse holt die Command Bar von api.frankfurter.dev (EZB-Kurse, ohne Konto) – nur, wenn du eine Währungsumrechnung tippst, höchstens alle 12 Stunden; abschaltbar mit `command_bar_currency`. Die Websuche öffnet deine Eingabe erst bei `Enter` in der gewählten Suchmaschine. Land und IP des VPN fragt die Insel bei ipinfo.io ab – nur mit `vpn_lookup` (standardmäßig aus), einmal pro VPN-Verbindung; ipinfo.io sieht dabei die Ausgangs-IP des VPN. Der Clipboard-Verlauf liegt unverschlüsselt in `~/.local/share/linuxmos/island/clipboard.json`; Kopien aus Passwort-Managern werden nur übersprungen, wenn diese sie als geheim markieren (KeePassXC & Co.).

> [!IMPORTANT]
> KI-Chat und Diktat sind aus, bis du sie im Tray-Menü unter „KI“ einschaltest. Danach schicken sie deine Frage bzw. deine Sprachaufnahme an den Server aus `ai_base_url` (ohne Eintrag: OpenAI) – nur, wenn du etwas abschickst. Das Gespräch bleibt im Arbeitsspeicher, die Diktat-Aufnahme (`~/.cache/linuxmos/island/recordings/dictation.wav`) wird gelöscht, sobald der Text da ist. Der API-Key liegt im Schlüsselbund (`secret-tool`), nie in `config.json`, und geht nur über die Standardeingabe an `curl`, steht also auch nicht in der Prozessliste. Ein lokaler Server (Ollama, LM Studio unter `localhost`) braucht keinen Key und schickt nichts ins Internet.

> [!IMPORTANT]
> Während einer Bildschirmaufnahme bleibt die Insel unsichtbar, damit sie nicht im Video landet, und Benachrichtigungen erscheinen nicht als Karte (sie stehen danach im Benachrichtigungs-Applet). Die Aufnahme zeichnet alles auf, was auf dem Bildschirm zu sehen ist – auch Passwörter, die du dort tippst.

> [!IMPORTANT]
> Solange die MosIsland Benachrichtigungen als Karte zeigt, schaltet sie Cinnamons eigene Banner ab (`org.cinnamon.desktop.notifications display-notifications`) – Benachrichtigungen landen dann ohne Popup im Benachrichtigungs-Applet, die Karte zeigt die Insel. Beim Beenden der Insel oder mit Tray → „Benachrichtigungen“ → „Auf der Insel anzeigen“ aus kommen Cinnamons Banner zurück. „Nicht stören“ (Steuerung-Tab, Tray) gilt dann für die Insel; kritische Meldungen (z. B. Akku fast leer) kommen trotzdem durch. Die Karten zeigen Nachrichteninhalte groß oben in der Mitte – bei Bildschirmfreigaben ggf. „Nicht stören“ einschalten.

> [!IMPORTANT]
> Ein Klick auf einen Clipboard-Eintrag sendet per `xdotool` `Ctrl+V` (in Terminals `Ctrl+Shift+V`) an das zuletzt aktive Fenster.

---

## Konfiguration

MosIsland: `~/.config/linuxmos/island/config.json` – die meisten Schalter gibt es auch im Tray-Menü und im Wasser-Tab.

```json
{
  "city": "Berlin",
  "language": "auto",
  "offset_y": 6,
  "monitor": "primary",
  "compact_when_idle": false,
  "mascot": true,
  "mascot_style": "eyes",
  "osd": true,
  "lyrics_in_pill": false,
  "clipboard_limit": 50,
  "clipboard_autodelete_min": 0,
  "screenshot_save": true,
  "screenshot_dir": "",
  "screenshot_open_editor": false,
  "ocr_languages": "deu+eng",
  "ocr_keep_linebreaks": false,
  "qr_open_links": false,
  "notifications_on_island": true,
  "notifications_dnd": false,
  "notifications_exclude": [],
  "privacy_indicator": true,
  "vpn_status": true,
  "vpn_lookup": false,
  "downloads_progress": true,
  "downloads_dir": "",
  "record_format": "mp4",
  "record_audio": "off",
  "record_fps": 30,
  "record_max_min": 30,
  "record_dir": "",
  "ai_chat": false,
  "ai_voice": false,
  "ai_voice_autopaste": true,
  "ai_base_url": "",
  "ai_model": "",
  "ai_stt_model": "",
  "ai_system_prompt": "",
  "ai_history": 20,
  "ai_voice_language": "",
  "ai_voice_max_s": 120,
  "command_bar_engine": "duckduckgo",
  "command_bar_files": true,
  "command_bar_currency": true,
  "water_goal_ml": 2000,
  "water_portion_ml": 250,
  "water_reminders": true,
  "water_start": "09:00",
  "water_end": "21:00",
  "water_interval_min": 60,
  "stretch_enabled": true,
  "stretch_interval_min": 45,
  "stretch_break_reset_min": 5,
  "stretch_idle_skip_min": 30,
  "stretch_snooze_min": 5,
  "stretch_snooze_max": 2,
  "stretch_escalate": true,
  "stretch_verify_idle": true,
  "stretch_long_per_day": 2,
  "stretch_sound": true,
  "stretch_volume": 0.5,
  "stretch_off_date": "",
  "eye_mode": true,
  "eye_mode_scale": 2.0
}
```

Am bequemsten über das **Zahnrad** oben rechts in der aufgeklappten Insel (oder Tray → „Einstellungen öffnen“): Es trägt fehlende Schlüssel mit ihren Standardwerten ein und öffnet die Datei per `xdg-open` (sonst `gio open`, sonst `xed`) – also im Standardprogramm für `.json`-Dateien. Gespeichert gilt sofort, ohne Neustart. Ist das JSON ungültig, bleiben die alten Werte aktiv, eine Karte meldet „Config ungültig, alte Werte bleiben“ mit Zeile und Spalte, und die Insel schreibt nicht in die Datei, bis sie wieder stimmt. Unbekannte Schlüssel bleiben erhalten, Werte außerhalb des gültigen Bereichs werden auf die Grenze gesetzt. **Alle Schlüssel mit Standardwert, Bedeutung und Bereich: [docs/CONFIG.md](docs/CONFIG.md).**

`language`: `auto` (Systemsprache: Deutsch bei `de_*`, sonst Englisch), `de` oder `en`. Beim Umschalten im Tray-Menü startet die MosIsland kurz neu (ein laufender Timer geht dabei verloren).

`monitor`: `"primary"` (Hauptmonitor, Standard), `"pointer"` (der Monitor, auf dem die Maus steht, wenn du die Insel per Hotkey oder Tray öffnest – eingeklappt bleibt sie dort, bis du sie woanders öffnest), eine Nummer von links (`0` = ganz links, `1` = der daneben …) oder der Anschlussname wie in `xrandr --listmonitors` (`"HDMI-1"`, `"DP-2"`, `"eDP-1"`). Ist der gewählte Monitor nicht angeschlossen, geht die Insel auf den Hauptmonitor und kehrt beim Einstecken zurück – die Einstellung bleibt. Im Tray-Menü unter „Monitor“ stehen alle angeschlossenen Monitore; gespeichert wird dort der Name, weil die Nummern sich beim Umstecken verschieben können.

Screenshots: `screenshot_save` legt jede Aufnahme zusätzlich als PNG ab (sonst nur Zwischenablage), `screenshot_dir` ändert den Ordner (leer = `~/Bilder/LinuxMos` bzw. `~/Pictures/LinuxMos`), `screenshot_open_editor` öffnet den Editor direkt nach der Aufnahme. „Fertig“ im Editor überschreibt die Aufnahme mit der markierten Fassung. Alles auch im Tray-Menü unter „Screenshot“.

Text & QR: `ocr_languages` sind tesseract-Sprachen, mit `+` verbunden (weitere per `sudo apt install tesseract-ocr-fra` usw., Liste: `tesseract --list-langs`). Standardmäßig werden die Zeilen eines Absatzes zusammengefügt und Trennstriche am Zeilenende entfernt; `ocr_keep_linebreaks` behält den Text zeilengenau. `qr_open_links` öffnet Links aus QR-Codes sofort im Browser statt nur einen „Öffnen“-Button zu zeigen. Beide Schalter auch im Tray-Menü unter „Text & QR“. Die Erkennung läuft komplett lokal, das Bild wird danach gelöscht.

Benachrichtigungen: `notifications_on_island` zeigt sie als Karte auf der Insel (und schaltet dafür Cinnamons Banner ab), `notifications_dnd` ist „Nicht stören“ der Insel, `notifications_exclude` eine Liste von App-Namen (wie in der Karte angezeigt) oder Desktop-IDs (`firefox`, `org.telegram.desktop`), die nie als Karte erscheinen – z. B. `["Spotify", "Thunderbird"]`. Alles auch im Tray-Menü unter „Benachrichtigungen“, dort stehen die zuletzt gesehenen Apps zum Abhaken. Die Insel liest die Benachrichtigungen per D-Bus-Monitor nur mit, nichts davon wird gespeichert (nur die App-Namen für die Liste, in `~/.local/share/linuxmos/island/notifications.json`).

Live-Hinweise: `privacy_indicator` zeigt den orangen (Mikrofon) und grünen (Kamera) Punkt; das Mikrofon kommt aus PipeWire/PulseAudio (`pactl subscribe`, Pegelanzeigen wie pavucontrol zählen nicht), die Kamera über inotify auf `/dev/video*`. `vpn_status` meldet VPN an/aus (NetworkManager-VPNs, WireGuard sowie tun/wg-Schnittstellen anderer VPN-Apps wie Mullvad), `vpn_lookup` holt dazu Land und IP von ipinfo.io (externe Anfrage, deshalb standardmäßig aus). `downloads_progress` beobachtet den Download-Ordner (`downloads_dir`, leer = XDG-Download-Ordner, z. B. `~/Downloads`) auf `.part` (Firefox) und `.crdownload` (Chromium/Chrome). Alles auch im Tray-Menü unter „Live-Hinweise“.

Command Bar: `command_bar_engine` ist die Suchmaschine (`duckduckgo`, `google`, `startpage`, `ecosia`, `bing`, `brave` oder eine eigene URL mit `%s` für die Suche, z. B. `"https://de.wikipedia.org/w/index.php?search=%s"`). `command_bar_files` sucht Dateien: zuletzt benutzte und alles im Home-Ordner bis 5 Ebenen tief (ohne versteckte Ordner, höchstens 20 000 Einträge); die Liste entsteht beim ersten Tippen in einem Thread und wird 3 Minuten nach der letzten Suche wieder verworfen. `command_bar_currency` rechnet Währungen mit den EZB-Kursen um (siehe Netzwerkzugriffe oben). Apps, die du über die Command Bar startest, rücken nach oben (Zähler in `~/.local/share/linuxmos/island/command.json`). Alles auch im Tray-Menü unter „Suche“.

Maskottchen: `mascot_style` ist `eyes` (Augen, Standard), `cat`, `robot` oder `blob`; `mascot` schaltet es ganz ab. Beides im Tray-Menü unter „Maskottchen“.

Augen-Modus: `eye_mode` (Standard an, Tray → „Maskottchen“ → „Augen-Modus (groß im Leerlauf)“) lässt die Figur im Leerlauf (derselbe Moment, in dem das Maskottchen kommt) um `eye_mode_scale` wachsen, 1,5 bis 3,0 – Werte außerhalb gelten als die nächste Grenze. Bei ausgeschaltetem Maskottchen (`mascot: false`) bewirkt er nichts. Läuft sonst etwas in der Pille (Musik, Timer, Dehn-Countdown, das Dehn-Symbol), bleibt es bei der normalen Pille; Karten und Hinweise (Akku niedrig, WLAN weg, Dehn-Karte …) erscheinen wie immer, danach kehren die Augen zurück. Mikrofon-/Kamerapunkte bleiben sichtbar.

<img src="docs/img/island-eyes.png" alt="Augen-Modus: Augen, Katze, Roboter und Blob im Leerlauf, groß" width="60%">

Bildschirmaufnahme: `record_format` ist `mp4` oder `gif` (GIFs haben höchstens 15 Bilder pro Sekunde, 960 px Breite und keinen Ton), `record_audio` `off`, `system` (was die Lautsprecher spielen) oder `mic` (nur MP4), `record_fps` 1–60, `record_max_min` beendet eine Aufnahme nach so vielen Minuten (`0` = nie), `record_dir` ändert den Ordner (leer = `~/Videos/LinuxMos`). Das Bild kommt von ffmpeg (`x11grab`) und braucht X11. Format und Ton auch im Tray-Menü unter „Bildschirmaufnahme“.

KI: `ai_chat` zeigt den Chat-Tab, `ai_voice` schaltet das Diktat frei, `ai_voice_autopaste` tippt das Diktat ins vorige Fenster (sonst Karte mit „Einfügen“). `ai_base_url` ist die Adresse des Servers bis `/v1` (leer = `https://api.openai.com/v1`, Ollama: `http://localhost:11434/v1`), `ai_model` das Chat-Modell (leer = `gpt-4o-mini`), `ai_stt_model` das Modell für Diktat (leer = `whisper-1`; der Server braucht `/audio/transcriptions`). `ai_system_prompt` ersetzt die kurze Standardanweisung, `ai_history` ist die Zahl der Nachrichten, die mitgeschickt werden, `ai_voice_language` ein Sprachcode wie `de` (leer = erkennen lassen), `ai_voice_max_s` die längste Diktat-Aufnahme. Adresse, Modelle und Key setzt du im Tray-Menü unter „KI“ → „Verbindung & API-Key …“, oder den Key mit `linuxmos-island --set-key`.

Weitere Dateien:

| Datei                                         | Inhalt                                         |
|-----------------------------------------------|------------------------------------------------|
| `~/.config/linuxmos/conky/*.conf`             | Position und Aussehen der Widgets (`gap_x`, `gap_y`, `alignment`) |
| `~/.config/linuxmos/rofi/spotlight.rasi`      | Aussehen der Spotlight-Suche                   |
| `~/.local/share/linuxmos/install.conf`        | Gewählte Install-Optionen (nutzt `update.sh`)  |
| `~/.local/share/linuxmos/island/`             | MosIsland-Daten: Notiz, Aufgaben, Wasser-Log, Verlauf, Ablage, Dehn-Statistik (`stretch.json`, 30 Tage) |
| `~/.config/linuxmos/island/stretch_exercises.json` | Deine Dehn-Übungen (Name, Anweisung, Sekunden, `long`) – beim ersten Mal mit der Standardliste angelegt |
| `~/.cache/linuxmos/island/stretch-*.wav`      | Die beiden Töne der Dehn-Erinnerung, beim ersten Gebrauch selbst erzeugt (`uninstall.sh` löscht sie) |

---

## Dehn-Erinnerung

<p align="center"><img src="docs/img/island-stretch.png" alt="Dehn-Erinnerung: Karte mit Übung, die größere Karte beim zweiten Mal, das Figürchen in der Pille und der Countdown-Ring" width="80%"></p>

Alles auf der Insel, keine Dialogfenster. Der Hauptschalter ist Tray → „Dehnen“ → „Dehn-Erinnerung“ (`stretch_enabled`), dazu „Heute aus“ (bis Mitternacht) und der Tab „Dehnen“. **Aus heißt wirklich aus:** kein Timer, kein Tick, keine Abfrage (im Log steht `stretch: disabled, no timers`).

**Wann sie kommt**
- Gezählt wird nur *aktive* Zeit: Ein Tick pro Minute fragt einmal die Zeit seit der letzten Eingabe ab (Muffins IdleMonitor, den die Insel fürs Maskottchen ohnehin nutzt; Ersatz außerhalb von Cinnamon: libXss). War in der letzten Minute Eingabe, zählt die Minute. Ist der Rechner länger im Leerlauf, tickt es nur alle 5 Minuten.
- **5 Minuten ohne Eingabe** (`stretch_break_reset_min`) sind eine echte Pause: Die Zählung beginnt von vorn, es kommt keine Karte „hinterher“.
- Ist die Erinnerung fällig und der Bildschirm aus oder gesperrt (`cinnamon-screensaver-command -q`, `xset q`, einmalig, nur jetzt) oder die letzte Eingabe länger als `stretch_idle_skip_min` her, fällt sie aus; neu gezählt wird ab der Rückkehr.
- **Vollbild** (Film, Spiel): Die Erinnerung wartet und kommt, sobald du raus bist. Die Insel hört dafür auf libwncks Fenster-Signale, fragt nichts ab. **Fokus-Timer:** Läuft einer, kommt keine Karte; wird sie währenddessen fällig, kommt sie beim Ende der Fokusphase, noch vor der Pause. Ist dann nichts fällig, passiert nichts.

**Was auf der Karte steht:** Übungsname, Anweisung, „Start“, „Später“, „Heute aus“, „Aus“ (setzt `stretch_enabled` auf `false` und zeigt kurz, wie man es wieder einschaltet). Die Karte klappt nach 15 s ein und lässt ein kleines Figürchen rechts in der Pille zurück, bis du reagiert hast; ein Klick darauf zeigt sie wieder. Vor der Karte blinzeln die Augen zweimal (wenn sie gerade zu sehen sind).

**Gegen „einfach Erledigt klicken“**
- „Start“ startet einen Countdown (kurze Übungen 10–20 s, aufwendige 30–60 s) mit einem Ring links in der Pille. „Erledigt“ gibt es erst danach, und es zählt nur, wenn die Leerlaufzeit am Ende mindestens **70 %** der Countdown-Dauer beträgt (`stretch_verify_idle`). Sonst: „Du warst am Rechner, noch mal?“ – beim zweiten Mal zählt es als „unbestätigt“.
- „Später“ höchstens zweimal pro Runde (5, dann 3 Minuten), danach nur noch Start oder „Überspringen“.
- Wird die Karte ignoriert, kommt sie nach 3 Minuten größer und mit etwas höherem Ton wieder, höchstens dreimal (`stretch_escalate`), danach zählt sie als „verpasst“.
- Die Statistik pro Tag (erledigt, unbestätigt, später, übersprungen, verpasst; 30 Tage) steht im Tab „Dehnen“ und in `~/.local/share/linuxmos/island/stretch.json`.

**Übungen** stehen in `~/.config/linuxmos/island/stretch_exercises.json` (Tray → Dehnen → „Übungen bearbeiten …“) und sind erweiterbar: `name`, `text`, `seconds`, `long`. Die Auswahl rotiert ohne direkte Wiederholung; jede vierte Erinnerung ist eine aufwendige (`long: true`), höchstens `stretch_long_per_day`-mal pro Tag.

**Ton:** Ein weicher Doppelton (C5 → E5, ca. 0,5 s, sanft ein- und ausklingend), beim Wiederkommen etwas höher und länger (E5 → G5), am Ende des Countdowns noch einmal der erste. Die beiden WAV-Dateien erzeugt die Insel beim ersten Gebrauch aus Sinuswellen (nichts von Dritten) in `~/.cache/linuxmos/island/` und spielt sie mit `paplay`; `stretch_sound` und `stretch_volume` (0.0–1.0) steuern ihn.

Nichts davon verlässt den Rechner: Es gibt keine Netzabfragen, und die Insel speichert nur die Zahlen der Statistik, nie was du tippst.

---

## Tests

Im Container getestet, ohne echte Hardware: Xvfb mit echtem **Muffin** (Leerlaufzeit, Fenster, Vollbild) und privatem D-Bus, die Regeln der Erinnerung zusätzlich mit einer künstlichen Uhr (`python3 -m unittest discover -s tests -t .`, 45 Tests, brauchen nur Python). Was damit nicht geht (Ohren, echter Bildschirm, deine Standard-Programme), steht in [TEST.md](TEST.md) unter „Paket 11“.

Hilfen zum Ausprobieren: `linuxmos-island --stretch-now` (Karte sofort), `--stretch-test` (Intervall 1 Minute; Takt 5 s, Pause nach 20 s, Überspringen nach 40 s, „Später“ 10 s/6 s, Wiederkommen nach 15 s), `--force-idle` (Augen-Modus ohne Warten).

| Test | Ergebnis |
|---|---|
| Debug-Hilfen | ✅ `--stretch-now` (startet die Insel mit Karte, bei laufender Insel per D-Bus; läuft schon eine Runde, zeigt es sie wieder), `--stretch-test`, `--force-idle`; die beiden Start-Schalter melden bei laufender Insel „läuft schon“ |
| Idle-CPU und RAM vorher/nachher | ✅ siehe Tabelle oben: +0,6 MB RSS, CPU unverändert |
| `stretch_enabled: false`, Tray-Häkchen aus, „Heute aus“, Karte „Aus“ | ✅ Log `disabled, no timers`, danach 20 s lang keine Messzeile (Testmodus, 5-s-Takt); weder Tick noch Wnck-Signal verbunden; Tray-Häkchen folgen; „Heute aus“ endet beim Datumswechsel von selbst |
| Idle-Logik | ✅ Pause: 30 s ohne Eingabe (Testmodus, Schwelle 20 s) → Zählung 0; Bildschirm gesperrt (Stub für `cinnamon-screensaver-command`) → verworfen, danach neu gezählt; Unit-Tests mit künstlicher Uhr: 5-Minuten-Pause, Tick-Takt (60 s / 5 min), „letzte Eingabe zu alt“, Messung nicht möglich → pausiert statt zu raten. Die 30-Minuten-Regel greift im echten Ablauf selten allein, weil die 5-Minuten-Pause früher zuschlägt |
| Vollbild | ✅ echtes Vollbildfenster unter Muffin: Erinnerung wird fällig, wartet (`waiting (fullscreen)`), kommt beim Verlassen |
| Fokus-Timer | ✅ fällig im Fokus → Karte, sobald der Fokus-Timer abgebrochen wird bzw. am natürlichen Ende (die Pause läuft dann schon); nichts fällig → nichts passiert |
| Countdown mit Bewegung / sitzen bleiben | ✅ echte Leerlaufzeit von Muffin: Maus bewegt → „Du warst am Rechner“ (zweiter Versuch bewegt → „unbestätigt“), Maus ruhig → „erledigt“; auch „erst bewegt, dann ruhig“ → erledigt |
| „Später“-Limit, Eskalation, Statistik | ✅ zweimal Später (10 s/6 s im Testmodus), dritte Runde abgelehnt; ignorierte Karte kommt dreimal größer wieder, dann „verpasst“; `stretch.json` enthält die Zahlen; 30-Tage-Grenze und Rotation (jede 4. lang, höchstens 2/Tag, keine direkte Wiederholung) als Unit-Tests |
| Ton | ⚠️ erzeugt und analysiert (0,62 s und 0,77 s, mono 44,1 kHz; 97 % der Energie unter 1 kHz, nichts über 3 kHz, Spitze −5 dBFS, erste und letzte Probe null); `paplay` wird mit der richtigen Lautstärke (`--volume`) aufgerufen, `stretch_sound: false` ruft es nicht mehr auf. **Hören konnte ich ihn nicht** (kein Audiogerät) → TEST.md |
| Augen-Modus | ✅ Größe 1.5, 2.0 und 3.0, alle vier Figuren (auch schlafend), Warnhinweis und Karte erscheinen normal, Musik/Timer/Dehn-Symbol gehen vor, Rückkehr bei Hover/Klick, `eye_mode: false` und `mascot: false` |
| Zahnrad | ✅ Datei wird mit allen Schlüsseln befüllt (eigene Werte und unbekannte Schlüssel bleiben), `xdg-open` wird gerufen, geänderter Wert gilt ohne Neustart, kaputtes JSON → Karte mit „Zeile 4, Spalte 1“ und alte Werte bleiben, in die kaputte Datei wird nicht geschrieben, repariert → Karte weg. Welches Programm sich bei dir öffnet, hängt vom System ab (TEST.md) |
| `update.sh` auf bestehende Installation | ⚠️ das Script selbst lässt sich im Container nicht laufen (apt, kein root). Getestet: Eine von 1.11.0 geschriebene `config.json` bleibt mit allen Nutzerwerten, die neuen Schlüssel gelten mit Standardwerten, der installierte Ordner (`island-app`) startet. Das Script musste nicht geändert werden |
| `uninstall.sh` | ✅ ohne `--purge` ist das WAV-Paar weg, Statistik und Übungsdatei bleiben; mit `--purge` ist alles weg |

---

## Bekannte Probleme

- **Kompletter `install.sh`-Lauf auf echtem Mint 22 noch nicht getestet** – MosIsland, Panel-Umbau, Update und Uninstall sind unter Cinnamon 6 getestet, der WhiteSur-Installationsschritt nicht. Bitte Fehler melden.
- **MosIsland braucht ~60 MB RAM** (bis 1.9 ~115 MB) – fast komplett Python + GTK3 selbst; Nusa (Rust) schafft ~30 MB.
- **Kein echtes „Genie“ und kein Blur** – bewusst, weil beides dauerhaft Leistung kostet.
- **MosIsland nur unter X11** (Standard bei Mint Cinnamon). Oberfläche auf Deutsch und Englisch; `install.sh`, `update.sh` und `uninstall.sh` sprechen nur Deutsch.
- **Lyrics/Wetter** hängen von LRCLIB bzw. MET Norway ab – nicht jeder Song hat synchronisierte Lyrics.
- **Ist die MosIsland beendet**, fehlt das Lautstärke-OSD (weil Cinnamons eigenes abgeschaltet ist) – im Tray-Menü „Lautstärke & Helligkeit anzeigen“ ausschalten bringt Cinnamons OSD zurück.
- **Einfügen per Klick** funktioniert nicht in Fenstern, die als root laufen – der Eintrag liegt dann trotzdem in der Zwischenablage.
- **OCR-Qualität** hängt von der Schriftgröße ab – sehr kleiner oder stark stilisierter Text, Schrift auf Bildern und Handschrift werden oft nicht sauber erkannt. Größeren Bereich wählen oder vorher hineinzoomen hilft.
- **WLAN-Passwörter aus QR-Codes** landen wie alles Kopierte im Clipboard-Verlauf – bei Bedarf dort löschen oder `clipboard_autodelete_min` setzen.
- **Buttons in Benachrichtigungen** („Antworten“, „Annehmen“ …) gibt es auf der Karte nicht – die kann nur Cinnamon als Benachrichtigungs-Dienst auslösen. Ein Klick auf die Karte holt die App nach vorne (Fenster des Absenders, sonst wird die App gestartet); die Buttons stehen im Benachrichtigungs-Applet.
- **Stürzt die MosIsland ab** (oder wird mit `kill -9` beendet), bleiben Cinnamons Banner aus, bis die Insel wieder läuft. Sofort zurück: `gsettings set org.cinnamon.desktop.notifications display-notifications true` (oder einfach `linuxmos-island` starten und im Tray die Karten ausschalten). `uninstall.sh` stellt sie ebenfalls wieder her.
- **Vor Vollbild-Apps** (Videos, Spiele) bleibt die Insel unsichtbar, also auch die Karten – Benachrichtigungen findest du danach im Applet.
- **Download-Prozent** gibt es nur, wenn der Browser seinen Fortschritt meldet (Chromium/Chrome tun das); Firefox-Downloads zeigen Größe und Tempo. Downloads in andere Ordner als `downloads_dir` sieht die Insel nicht.
- **Dateien in der Command Bar** findet die Insel nur im Home-Ordner (bis 5 Ebenen, keine versteckten Ordner) und in der Liste zuletzt benutzter Dateien – für die ganze Platte bleibt die rofi-Suche (`Super+Space`, Modus „Dateien“). Neue Dateien tauchen spätestens 10 Minuten später auf.
- **Kamera-App** erkennt die Insel nur bei Programmen des eigenen Benutzers; läuft die Kamera über PipeWire (z. B. Flatpak-Apps über das Portal), steht dort „PipeWire“ statt der App. Den Kamera-Punkt kann man nicht abschalten wie das Mikrofon – dafür gibt es keinen Systemschalter.
- **Mehrere Monitore:** Ohne Hotkey wechselt die Insel im Modus `"pointer"` den Monitor nicht – Hovern öffnet sie nur dort, wo sie gerade sitzt. Sitzt sie auf einem Nebenmonitor zu hoch (unter der Top Bar), hilft `offset_y`.
- **Bildschirmaufnahme** gibt es nur unter X11. „Systemton“ nimmt den Standard-Ausgang von PulseAudio/PipeWire auf (`@DEFAULT_MONITOR@`); wechselst du während der Aufnahme das Gerät, bleibt der Ton beim alten. Ein anderer Screenshot-, OCR- oder QR-Hotkey während einer Aufnahme beendet sie (und speichert sie). Lange GIFs werden groß – dafür MP4 nehmen.
- **KI-Chat:** Antworten erscheinen als reiner Text (kein Markdown). Das Diktat braucht einen Server mit `/audio/transcriptions` (OpenAI, Groq, LocalAI, faster-whisper-server …); Ollama hat das nicht. Ist der Schlüsselbund gesperrt, fragt GNOME beim ersten Zugriff nach dem Passwort. Der Chat zeigt keine Bilder und merkt sich nichts über einen Neustart hinaus.
- **Dehn-Erinnerung:** Vollbild erkennt die Insel am Fenster-Status des Fensterverwalters (`_NET_WM_STATE_FULLSCREEN`); Spiele, die ihn nicht setzen, bleiben unerkannt. Die Zählung ist an Eingabe gekoppelt: Wer nur ein Video schaut (ohne Maus und Tastatur), zählt nicht als aktiv. Ob der Ton gut klingt, lässt sich nur mit eigenen Ohren prüfen (`stretch_volume`). Läuft kein PulseAudio/PipeWire oder fehlt `paplay`, bleibt die Erinnerung still (steht im Log).
- **Augen-Modus:** Läuft sonst nichts in der Pille, ersetzt er die normale Maskottchen-Pille; Mikrofon-/Kamerapunkte und Download-Ring bleiben daneben sichtbar. Ohne Maskottchen (`mascot: false`) bewirkt er nichts.
- **Zahnrad:** Die Datei öffnet sich im Standardprogramm für `.json` (`xdg-open`). Ist das bei dir der Browser, per `xdg-mime default xed.desktop application/json` ändern. Ein Neustart ist nur für `language` nötig; offene, schon gebaute Tabs zeigen geänderte Werte erst beim nächsten Öffnen der Insel.
- **Screenshot-Bild in der Zwischenablage** hält ein kleiner `xclip`-Prozess im Hintergrund, bis du etwas anderes kopierst (so überlebt das Bild auch ein Beenden der Insel).

Weitere Lösungen: [docs/ANLEITUNG.md → Troubleshooting](docs/ANLEITUNG.md#troubleshooting)

---

## Roadmap

- [x] macOS-Look mit Theme, Top Bar, Dock, Widgets, Spotlight
- [x] Backup, Uninstall und Update (`update.sh`)
- [x] MosIsland mit Musik, Lyrics, Zwischenablage, Ablage, Aufgaben, Pomodoro, Wasser, Wetter, Steuerung
- [x] Live-Hinweise, Maskottchen, Tray-Menü
- [x] Zwischenablage automatisch leeren (`clipboard_autodelete_min`)
- [ ] Kompletter Testlauf auf Linux Mint 22.x
- [x] Englische Oberfläche für die MosIsland (`language`, Tray-Menü)
- [x] Screenshot-Tool mit Markup-Editor (`Ctrl+Alt+S`, `Ctrl+Alt+Shift+S`)
- [x] Text vom Bildschirm (OCR, `Ctrl+Alt+O`) und QR-Codes (`Ctrl+Alt+Q`)
- [x] Benachrichtigungen als Karte auf der Insel (`notifications_on_island`, Ausschlussliste)
- [x] Mikrofon-/Kamera-Punkt mit Stumm-Button, VPN-Status, Download-Fortschritt (`privacy_indicator`, `vpn_status`, `downloads_progress`)
- [x] Command Bar in der Insel (`Ctrl+Alt+Space`): Apps, Dateien, Rechner, Einheiten, Währungen, Websuche
- [x] Mehrere Monitore: Hauptmonitor, fester Monitor oder der mit der Maus (`monitor`, Tray-Menü), folgt dem Ein- und Ausstecken
- [x] Weniger RAM: 116 → 60 MB (ohne OpenGL-Test, Tabs erst bei Bedarf, HTTP über `curl`, Cover verkleinert im Cache)
- [x] Bildschirmaufnahme als MP4 oder GIF (`Ctrl+Alt+R`, `Ctrl+Alt+Shift+R`)
- [x] KI-Chat und Diktat mit eigenem API-Key im Schlüsselbund (`ai_chat`, `ai_voice`, `Ctrl+Alt+A`, `Ctrl+Alt+M`)
- [x] Weitere Maskottchen: Katze, Roboter, Blob (`mascot_style`)
- [x] Dehn-Erinnerung mit Aktivitätszählung, Countdown, Prüfung gegen „einfach klicken“, Ton und Statistik (`stretch_*`)
- [x] Augen-Modus: große Figur im Leerlauf (`eye_mode`, `eye_mode_scale`)
- [x] Einstellungs-Zahnrad mit Neuladen ohne Neustart und [docs/CONFIG.md](docs/CONFIG.md)
- [ ] Dehn-Erinnerung und Augen-Modus auf echtem Mint prüfen (Ton, Sperrbildschirm, echtes Vollbild)

---

## Lizenz

Dieses Projekt steht unter der MIT-Lizenz – siehe [LICENSE](LICENSE).

Die WhiteSur-Themes (GPL-3.0) sind nicht Teil dieses Repos, sie werden bei der Installation vom Original geladen.

---

## Credits

- [WhiteSur GTK Theme, Icons, Cursors, Wallpapers](https://github.com/vinceliuice) – macOS-Theme (GPL-3.0)
- [Plank](https://launchpad.net/plank) – Dock
- [Conky](https://github.com/brndnmtthws/conky) – Desktop-Widgets
- [rofi](https://github.com/davatorium/rofi) – Spotlight-Suche
- [Inter](https://rsms.me/inter/) – Schrift
- [PyGObject / GTK 3](https://pygobject.gnome.org/) – MosIsland-Oberfläche
- [maim / slop](https://github.com/naelstrof/maim) – Screenshots und Bereichsauswahl
- [FFmpeg](https://ffmpeg.org/) (LGPL/GPL) – Bildschirmaufnahme und Diktat
- [libsecret](https://gitlab.gnome.org/GNOME/libsecret) (LGPL-2.1) – API-Key im Schlüsselbund
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) (Apache-2.0) – Texterkennung
- [ZBar](https://github.com/mchehab/zbar) (LGPL-2.1) – QR-Codes und Barcodes
- [MET Norway](https://www.met.no/en) (CC BY 4.0), [OpenStreetMap](https://www.openstreetmap.org/copyright) (ODbL), [LRCLIB](https://lrclib.net) – Wetter, Ortssuche, Lyrics
- Ideen: [Island](https://github.com/exuupery/island) von exuupery und [Nusa](https://rama2555.github.io/nusa/) von Rama (beide Windows, Closed Source) – kein Code und keine Grafiken übernommen
- Entwickelt mit Unterstützung von Claude (Anthropic)

Dieses Projekt steht in keiner Verbindung zu Apple Inc. „macOS“ ist eine Marke von Apple Inc.
