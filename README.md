> [!NOTE]
> **Vibe-coded Projekt** – Dieses Projekt wurde größtenteils mit KI-Unterstützung (Claude) entwickelt.
> Der Code funktioniert für meinen Anwendungsfall, ist aber nicht professionell geprüft. Nutzung auf eigene Verantwortung.

**Deutsch** · [English](README.en.md)

# LinuxMos

Macht Linux Mint Cinnamon zum leichtgewichtigen macOS-Look-alike – mit Dock, Top Bar, Widgets, Spotlight und optional einer Dynamic Island – ohne dass der Desktop im Leerlauf CPU frisst.

![MosIsland](https://img.shields.io/badge/MosIsland-1.6.0-blue)
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
- [Bekannte Probleme](#bekannte-probleme)
- [Roadmap](#roadmap)
- [Lizenz](#lizenz)
- [Credits](#credits)

> Die ausführliche Schritt-für-Schritt-Anleitung (auch ohne Script, alles von Hand) steht in [docs/ANLEITUNG.md](docs/ANLEITUNG.md).

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
- **Maskottchen** – Augen im Leerlauf, die eindösen und winken, wenn du zurückkommst
- **Tray-Menü** – Autostart, Maskottchen, Minimal-Notch, OSD, Zwischenablage automatisch leeren, Suche (Dateien, Währungen, Suchmaschine), Screenshot, Text & QR, Benachrichtigungen (an/aus, Nicht stören, Apps ausblenden), Live-Hinweise (Mikro & Kamera, VPN, Downloads), Monitor, Sprache, Beenden
- **Deutsch oder Englisch** – folgt automatisch der Systemsprache, umschaltbar im Tray-Menü (`Sprache / Language`)

**Leichtgewichtig** – gemessen: Conky-Widgets ~0,03 % CPU, MosIsland ~0,1 % CPU (unter Cinnamon 6, Musik läuft) und ~60 MB RAM. Kein Blur-Compositor, keine Polling-Schleifen.

| MosIsland-RAM (Xvfb, frisches Profil, 10 s nach dem Start) | vorher (1.9.0) | nachher (1.10.0) |
|------------------------------------------------------------|----------------|------------------|
| RSS (was `top` zeigt)                                      | 116 MB         | **60 MB**        |
| PSS (geteilte Bibliotheken anteilig)                       | 87 MB          | **49 MB**        |
| Alle Tabs einmal geöffnet                                  | –              | 62 MB            |
| CPU im Leerlauf (60 s, Xvfb)                               | 0,2 %          | 0,2 %            |

Der größte Brocken (−49 MB) war Mesa: GTK lädt beim Start den OpenGL-Treiber samt LLVM, nur um ein Fenster-Format auszusuchen – die Insel zeichnet aber gar nicht mit OpenGL. Der Rest (−7 MB): Tabs werden erst beim ersten Öffnen gebaut, Wetter/Lyrics/Cover/Kurse kommen über `curl` statt über Pythons HTTPS-Stack, und freier Speicher geht nach dem Zuklappen zurück ans System. Auf echter Hardware hängt die Ersparnis vom Grafiktreiber ab – `linuxmos-perf` zeigt den RAM der Insel.

---

## Voraussetzungen

- **Linux Mint 22.x Cinnamon** (Basis Ubuntu 24.04), X11-Session
- Ein Benutzer mit `sudo`-Rechten (das Script fragt selbst nach dem Passwort)
- Internetverbindung (apt-Pakete und WhiteSur-Themes von GitHub)
- Optional: **Timeshift** eingerichtet (für den Snapshot vor der Installation)

Alle Pakete installiert `install.sh` selbst, u. a. `plank`, `conky-std`, `rofi`, `fonts-inter`, `sassc`; mit `--island` zusätzlich `python3-gi`, `gir1.2-gtk-3.0`, `gir1.2-wnck-3.0`, `gir1.2-xapp-1.0`, `xdotool`, `pulseaudio-utils`, `iso-codes`.

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
linuxmos-island --set-city "München"
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
  "command_bar_engine": "duckduckgo",
  "command_bar_files": true,
  "command_bar_currency": true,
  "water_goal_ml": 2000,
  "water_portion_ml": 250,
  "water_reminders": true,
  "water_start": "09:00",
  "water_end": "21:00",
  "water_interval_min": 60
}
```

`language`: `auto` (Systemsprache: Deutsch bei `de_*`, sonst Englisch), `de` oder `en`. Beim Umschalten im Tray-Menü startet die MosIsland kurz neu (ein laufender Timer geht dabei verloren).

`monitor`: `"primary"` (Hauptmonitor, Standard), `"pointer"` (der Monitor, auf dem die Maus steht, wenn du die Insel per Hotkey oder Tray öffnest – eingeklappt bleibt sie dort, bis du sie woanders öffnest), eine Nummer von links (`0` = ganz links, `1` = der daneben …) oder der Anschlussname wie in `xrandr --listmonitors` (`"HDMI-1"`, `"DP-2"`, `"eDP-1"`). Ist der gewählte Monitor nicht angeschlossen, geht die Insel auf den Hauptmonitor und kehrt beim Einstecken zurück – die Einstellung bleibt. Im Tray-Menü unter „Monitor“ stehen alle angeschlossenen Monitore; gespeichert wird dort der Name, weil die Nummern sich beim Umstecken verschieben können.

Screenshots: `screenshot_save` legt jede Aufnahme zusätzlich als PNG ab (sonst nur Zwischenablage), `screenshot_dir` ändert den Ordner (leer = `~/Bilder/LinuxMos` bzw. `~/Pictures/LinuxMos`), `screenshot_open_editor` öffnet den Editor direkt nach der Aufnahme. „Fertig“ im Editor überschreibt die Aufnahme mit der markierten Fassung. Alles auch im Tray-Menü unter „Screenshot“.

Text & QR: `ocr_languages` sind tesseract-Sprachen, mit `+` verbunden (weitere per `sudo apt install tesseract-ocr-fra` usw., Liste: `tesseract --list-langs`). Standardmäßig werden die Zeilen eines Absatzes zusammengefügt und Trennstriche am Zeilenende entfernt; `ocr_keep_linebreaks` behält den Text zeilengenau. `qr_open_links` öffnet Links aus QR-Codes sofort im Browser statt nur einen „Öffnen“-Button zu zeigen. Beide Schalter auch im Tray-Menü unter „Text & QR“. Die Erkennung läuft komplett lokal, das Bild wird danach gelöscht.

Benachrichtigungen: `notifications_on_island` zeigt sie als Karte auf der Insel (und schaltet dafür Cinnamons Banner ab), `notifications_dnd` ist „Nicht stören“ der Insel, `notifications_exclude` eine Liste von App-Namen (wie in der Karte angezeigt) oder Desktop-IDs (`firefox`, `org.telegram.desktop`), die nie als Karte erscheinen – z. B. `["Spotify", "Thunderbird"]`. Alles auch im Tray-Menü unter „Benachrichtigungen“, dort stehen die zuletzt gesehenen Apps zum Abhaken. Die Insel liest die Benachrichtigungen per D-Bus-Monitor nur mit, nichts davon wird gespeichert (nur die App-Namen für die Liste, in `~/.local/share/linuxmos/island/notifications.json`).

Live-Hinweise: `privacy_indicator` zeigt den orangen (Mikrofon) und grünen (Kamera) Punkt; das Mikrofon kommt aus PipeWire/PulseAudio (`pactl subscribe`, Pegelanzeigen wie pavucontrol zählen nicht), die Kamera über inotify auf `/dev/video*`. `vpn_status` meldet VPN an/aus (NetworkManager-VPNs, WireGuard sowie tun/wg-Schnittstellen anderer VPN-Apps wie Mullvad), `vpn_lookup` holt dazu Land und IP von ipinfo.io (externe Anfrage, deshalb standardmäßig aus). `downloads_progress` beobachtet den Download-Ordner (`downloads_dir`, leer = XDG-Download-Ordner, z. B. `~/Downloads`) auf `.part` (Firefox) und `.crdownload` (Chromium/Chrome). Alles auch im Tray-Menü unter „Live-Hinweise“.

Command Bar: `command_bar_engine` ist die Suchmaschine (`duckduckgo`, `google`, `startpage`, `ecosia`, `bing`, `brave` oder eine eigene URL mit `%s` für die Suche, z. B. `"https://de.wikipedia.org/w/index.php?search=%s"`). `command_bar_files` sucht Dateien: zuletzt benutzte und alles im Home-Ordner bis 5 Ebenen tief (ohne versteckte Ordner, höchstens 20 000 Einträge); die Liste entsteht beim ersten Tippen in einem Thread und wird 3 Minuten nach der letzten Suche wieder verworfen. `command_bar_currency` rechnet Währungen mit den EZB-Kursen um (siehe Netzwerkzugriffe oben). Apps, die du über die Command Bar startest, rücken nach oben (Zähler in `~/.local/share/linuxmos/island/command.json`). Alles auch im Tray-Menü unter „Suche“.

Weitere Dateien:

| Datei                                         | Inhalt                                         |
|-----------------------------------------------|------------------------------------------------|
| `~/.config/linuxmos/conky/*.conf`             | Position und Aussehen der Widgets (`gap_x`, `gap_y`, `alignment`) |
| `~/.config/linuxmos/rofi/spotlight.rasi`      | Aussehen der Spotlight-Suche                   |
| `~/.local/share/linuxmos/install.conf`        | Gewählte Install-Optionen (nutzt `update.sh`)  |
| `~/.local/share/linuxmos/island/`             | MosIsland-Daten: Notiz, Aufgaben, Wasser-Log, Verlauf, Ablage |

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
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) (Apache-2.0) – Texterkennung
- [ZBar](https://github.com/mchehab/zbar) (LGPL-2.1) – QR-Codes und Barcodes
- [MET Norway](https://www.met.no/en) (CC BY 4.0), [OpenStreetMap](https://www.openstreetmap.org/copyright) (ODbL), [LRCLIB](https://lrclib.net) – Wetter, Ortssuche, Lyrics
- Ideen: [Island](https://github.com/exuupery/island) von exuupery und [Nusa](https://rama2555.github.io/nusa/) von Rama (beide Windows, Closed Source) – kein Code und keine Grafiken übernommen
- Entwickelt mit Unterstützung von Claude (Anthropic)

Dieses Projekt steht in keiner Verbindung zu Apple Inc. „macOS“ ist eine Marke von Apple Inc.
