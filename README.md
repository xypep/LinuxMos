> [!NOTE]
> **Vibe-coded Projekt** – Dieses Projekt wurde größtenteils mit KI-Unterstützung (Claude) entwickelt.
> Der Code funktioniert für meinen Anwendungsfall, ist aber nicht professionell geprüft. Nutzung auf eigene Verantwortung.

**Deutsch** · [English](README.en.md)

# LinuxMos

Macht Linux Mint Cinnamon zum leichtgewichtigen macOS-Look-alike – mit Dock, Top Bar, Widgets, Spotlight und optional einer Dynamic Island – ohne dass der Desktop im Leerlauf CPU frisst.

![MosIsland](https://img.shields.io/badge/MosIsland-1.3.0-blue)
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
- **Steuerung** – WLAN, Bluetooth, Nicht stören, Dark Mode, Mikro, Lautstärke, Helligkeit, Screenshot, Sperren, Ruhezustand, Neustart, Aus
- **Live-Hinweise** – Lautstärke, Helligkeit, Feststelltaste, Tastatur-Sprache, Laden, WLAN weg, Kopfhörer verbunden
- **Maskottchen** – Augen im Leerlauf, die eindösen und winken, wenn du zurückkommst
- **Tray-Menü** – Autostart, Maskottchen, Minimal-Notch, OSD, Zwischenablage automatisch leeren, Sprache, Beenden
- **Deutsch oder Englisch** – folgt automatisch der Systemsprache, umschaltbar im Tray-Menü (`Sprache / Language`)

**Leichtgewichtig** – gemessen: Conky-Widgets ~0,03 % CPU, MosIsland ~0,1 % CPU (unter Cinnamon 6, Musik läuft). Kein Blur-Compositor, keine Polling-Schleifen.

---

## Voraussetzungen

- **Linux Mint 22.x Cinnamon** (Basis Ubuntu 24.04), X11-Session
- Ein Benutzer mit `sudo`-Rechten (das Script fragt selbst nach dem Passwort)
- Internetverbindung (apt-Pakete und WhiteSur-Themes von GitHub)
- Optional: **Timeshift** eingerichtet (für den Snapshot vor der Installation)

Alle Pakete installiert `install.sh` selbst, u. a. `plank`, `conky-std`, `rofi`, `fonts-inter`, `sassc`; mit `--island` zusätzlich `python3-gi`, `gir1.2-gtk-3.0`, `gir1.2-wnck-3.0`, `gir1.2-xapp-1.0`, `xdotool`, `pulseaudio-utils`.

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
linuxmos-perf                # CPU-Last des Desktops messen
linuxmos-widgets restart     # Conky-Widgets neu starten
linuxmos-island --tab todo   # MosIsland auf einem Tab öffnen
linuxmos-island --set-city "München"
```

### Hotkeys

| Hotkey           | Funktion                                                    |
|------------------|-------------------------------------------------------------|
| `Super+Space`    | Spotlight-Suche öffnen/schließen                            |
| `Shift+→`        | In der Suche: Modus wechseln (Apps, Run, Fenster, Dateien)  |
| `Ctrl+Alt+I`     | MosIsland öffnen/schließen                                  |
| `Ctrl+Alt+V`     | Zwischenablage-Verlauf (tippen = suchen, `Enter` = einfügen)|
| `Esc`            | MosIsland zuklappen                                         |
| Mausrad auf der Pille | Lautstärke ±5 %                                        |

---

## Wichtige Hinweise

> [!WARNING]
> `install.sh` ändert viele Cinnamon-Einstellungen: Panel nach oben, Fensterliste raus, Theme, Icons, Schrift, Effekte, eigene Tastenkürzel, `Super+Space` wird vom Tastaturlayout-Wechsel abgezogen, mit `--island` wird Cinnamons Lautstärke-OSD abgeschaltet. Vorher wird alles nach `~/.local/share/linuxmos/backup/` gesichert, `./uninstall.sh` stellt es wieder her. Ein Timeshift-Snapshot vorab wird empfohlen.

> [!CAUTION]
> `install.sh` lädt die WhiteSur-Themes direkt von GitHub (vinceliuice) und führt deren Installer aus, außerdem installiert es Pakete per `sudo apt`. Nicht mit `sudo` starten – das Script fragt selbst nach dem Passwort.

> [!IMPORTANT]
> Netzwerkzugriffe: Wetter über api.met.no und nominatim.openstreetmap.org (MosIsland) bzw. wttr.in (Conky), Lyrics über lrclib.net – jeweils nur, wenn du die Funktion nutzt. Der Clipboard-Verlauf liegt unverschlüsselt in `~/.local/share/linuxmos/island/clipboard.json`; Kopien aus Passwort-Managern werden nur übersprungen, wenn diese sie als geheim markieren (KeePassXC & Co.).

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
  "compact_when_idle": false,
  "mascot": true,
  "osd": true,
  "lyrics_in_pill": false,
  "clipboard_limit": 50,
  "clipboard_autodelete_min": 0,
  "water_goal_ml": 2000,
  "water_portion_ml": 250,
  "water_reminders": true,
  "water_start": "09:00",
  "water_end": "21:00",
  "water_interval_min": 60
}
```

`language`: `auto` (Systemsprache: Deutsch bei `de_*`, sonst Englisch), `de` oder `en`. Beim Umschalten im Tray-Menü startet die MosIsland kurz neu (ein laufender Timer geht dabei verloren).

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
- **MosIsland braucht ~115 MB RAM** – fast komplett Python + GTK3 selbst.
- **Kein echtes „Genie“ und kein Blur** – bewusst, weil beides dauerhaft Leistung kostet.
- **MosIsland nur unter X11** (Standard bei Mint Cinnamon). Oberfläche auf Deutsch und Englisch; `install.sh`, `update.sh` und `uninstall.sh` sprechen nur Deutsch.
- **Lyrics/Wetter** hängen von LRCLIB bzw. MET Norway ab – nicht jeder Song hat synchronisierte Lyrics.
- **Ist die MosIsland beendet**, fehlt das Lautstärke-OSD (weil Cinnamons eigenes abgeschaltet ist) – im Tray-Menü „Lautstärke & Helligkeit anzeigen“ ausschalten bringt Cinnamons OSD zurück.
- **Einfügen per Klick** funktioniert nicht in Fenstern, die als root laufen – der Eintrag liegt dann trotzdem in der Zwischenablage.

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
- [MET Norway](https://www.met.no/en) (CC BY 4.0), [OpenStreetMap](https://www.openstreetmap.org/copyright) (ODbL), [LRCLIB](https://lrclib.net) – Wetter, Ortssuche, Lyrics
- Ideen: [Island](https://github.com/exuupery/island) von exuupery und [Nusa](https://rama2555.github.io/nusa/) von Rama (beide Windows, Closed Source) – kein Code und keine Grafiken übernommen
- Entwickelt mit Unterstützung von Claude (Anthropic)

Dieses Projekt steht in keiner Verbindung zu Apple Inc. „macOS“ ist eine Marke von Apple Inc.
