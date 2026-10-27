> [!NOTE]
> **Vibe-coded Projekt** – Dieses Projekt wurde größtenteils mit KI-Unterstützung (Claude) entwickelt.
> Der Code funktioniert für meinen Anwendungsfall, ist aber nicht professionell geprüft. Nutzung auf eigene Verantwortung.

**Deutsch** · [English](README.en.md)

# LinuxMos

Macht Linux Mint Cinnamon zum leichtgewichtigen macOS-Look-alike – mit Dock, Top Bar, Widgets, Spotlight und optional einer Dynamic Island – ohne dass der Desktop im Leerlauf CPU frisst.

![MosIsland](https://img.shields.io/badge/MosIsland-1.14.0-blue)
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
- [Clip-Transfer](#clip-transfer)
- [Werkzeuge & Zentrale](#werkzeuge--zentrale)
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
- **Clip-Transfer** (optional, standardmäßig aus) – Text, Bilder und Dateien per SSH an einen anderen PC schicken (Linux oder Windows): Knopf am Eintrag der Zwischenablage/Ablage, `Ctrl+Alt+Shift+T` oder `linuxmos-clip send`. **Nur auf deinen Handgriff**, kein Watcher; Empfangenes landet im Eingang, im Verlauf (markiert „empfangen“) bzw. in der Ablage und wird **nie automatisch kopiert** – erst ein Klick auf die Karte tut es. Nur SSH-Schlüssel, der Schlüssel darf per `restrict,command=…` nichts außer Clips abliefern → [Details](#clip-transfer)
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
- **Zwischenablage-Aktionen** – an jedem Verlaufseintrag (Knopf „Aktionen“) und per `Ctrl+Alt+Shift+V` für den aktuellen Inhalt: Formatierung entfernen, Tracking-Parameter aus Links löschen (`utm_*`, `fbclid`, `gclid` …), GROSS/klein/Titel, JSON formatieren oder zusammenfassen, URL und Base64 kodieren/dekodieren, Leerzeichen bereinigen, Zeilen sortieren, doppelte Zeilen entfernen, QR-Code (wenn `qrencode` da ist). Das Ergebnis erscheint als **neuer** Verlaufseintrag, das Original bleibt; als privat markierte Kopien (Passwort-Manager) fasst nichts davon an → [Details](#werkzeuge--zentrale)
- **Farbpipette** – `Ctrl+Alt+C`: Bildschirm einfrieren, Lupe (11×11 Pixel, 10-fach) mit Hex-Wert am Mauszeiger, Klick wählt. Hex, RGB, HSL oder HSV in die Zwischenablage, Karte mit allen Formaten, die letzten 20 Farben als Farbfelder (fixierbar)
- **Wach halten** – `Ctrl+Alt+K` oder Tray-Häkchen: kein Bildschirmschoner, keine Bildschirmabschaltung, kein automatischer Ruhezustand; Kaffeetasse in der Pille, schaltet sich nach 60 Minuten selbst aus. Die Sperre hängt an der D-Bus-Verbindung der Insel – stürzt sie ab, ist sie weg
- **Fenster anpinnen** – `Ctrl+Alt+P`: das aktive Fenster bleibt immer im Vordergrund (Pin mit Anzahl in der Pille, Liste mit „Aufheben“ im Werkzeuge-Tab)
- **Einstellungen & Übersicht** – `Ctrl+Alt+H`, das Zahnrad oder der Tray-Eintrag öffnen ein eigenes Fenster (eigener Prozess, nur solange es offen ist): **alle Funktionen** mit Hotkey, Schalter und Status, Suchfeld, ein Klick auf den Namen startet die Funktion, ein Klick auf das Kürzel ändert den Hotkey (mit Konfliktwarnung, sofort wirksam), „Was läuft gerade“ mit CPU und RAM der Insel, die **Gesten** auf der Pille (Mausrad, Mittel-/Rechts-/Doppelklick … frei belegbar) und alle Einstellungen mit geprüften Eingabefeldern → [Details](#werkzeuge--zentrale)
- **Config-Neuladen** – Änderungen an `config.json` gelten sofort (inotify, kostet nichts); ein Tippfehler lässt die alten Werte aktiv und meldet die Fehlerstelle auf einer Karte. Als Datei öffnest du sie im Einstellungsfenster („Config als Datei öffnen“) oder über Tray → „Config-Datei öffnen“
- **Tray-Menü** – Einstellungen & Übersicht, Wach halten (Häkchen), Farbpipette, aktives Fenster anpinnen, Autostart, Maskottchen (Figur wählen, Augen-Modus), Dehnen (Erinnerung, Heute aus, Jetzt dehnen, Übungen), Minimal-Notch, OSD, Zwischenablage automatisch leeren, Clip-Transfer (Senden, Empfang), Suche (Dateien, Währungen, Suchmaschine), Screenshot, Text & QR, Bildschirmaufnahme (Format, Ton), KI (Chat, Diktat, Verbindung & API-Key), Benachrichtigungen (an/aus, Nicht stören, Apps ausblenden), Live-Hinweise (Mikro & Kamera, VPN, Downloads), Monitor, Sprache, Config-Datei öffnen, Beenden
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

**Paket „Clip-Transfer“ (1.13.0)** – gemessen wie oben (Xvfb mit echtem Muffin, `linuxmos-perf 60`, 12 s nach dem Start, frisches Profil), jede Zeile ein eigener Start:

| MosIsland                                                          | RSS     | PSS     | CPU (60 s) |
|--------------------------------------------------------------------|---------|---------|------------|
| vorher (1.12.0)                                                    | 59,9 MB | 42,4 MB | 0,2 % (13 Ticks) |
| nachher, Transfer aus (Standard): **nichts geladen, kein Monitor** | 60,1 MB | 42,5 MB | 0,2 % (13 Ticks) |
| nachher, nur Empfang an (ein inotify-Monitor)                      | 60,4 MB | 42,7 MB | 0,2 % (13 Ticks) |
| nachher, nur Senden an                                             | 60,5 MB | 42,8 MB | 0,2 % (14 Ticks) |
| nachher, beides an                                                 | 60,4 MB | 42,8 MB | 0,2 % (13 Ticks) |
| nachher, beides an, Text + Bild empfangen, Zwischenablage-Tab geöffnet | 61,3 MB | 43,5 MB | 0,2 % (13 Ticks) |
| zum Vergleich: vorher (1.12.0) mit einmal geöffnetem Zwischenablage-Tab | 60,6 MB | 42,9 MB | 0,2 % (12 Ticks) |

„Ticks“ sind CPU-Zeit in Hundertstelsekunden während der 60 s (13 Ticks = 0,13 s). Das Paket kostet im Leerlauf 0,2 bis 0,6 MB RAM (mit empfangenen Inhalten und geöffnetem Tab 0,7 MB mehr als vorher), die CPU-Last ändert sich nicht messbar. Aus heißt aus: Sind Senden und Empfang aus, wird das Modul nicht einmal importiert (im Log steht `clip: disabled, no monitors`). Ein erster Entwurf kostete 4 MB, weil `dataclasses`, `secrets` (→ OpenSSL) und `subprocess` im Speicher blieben; der Kern nimmt jetzt nur noch Standardmodule, die die Insel schon geladen hat. Kein Daemon, kein Polling, keine dauerhafte SSH-Verbindung: Pro Clip startet ein `ssh`-Prozess, der danach endet.

**Paket „Werkzeuge & Zentrale“ (1.14.0)** – gemessen wie oben, jede Zeile ein eigener Start mit frischem Profil, 12 s nach dem Start, `linuxmos-perf 60`; „Ticks“ sind CPU-Zeit in Hundertstelsekunden während der 60 s. Damit vorher und nachher denselben Zustand haben, mit `--force-idle` (Maskottchen von Anfang an, das blinzelt – der teuerste Leerlauf-Zustand):

| MosIsland                                              | RSS     | PSS     | CPU (60 s)       |
|--------------------------------------------------------|---------|---------|------------------|
| vorher (1.13.0), Lauf 1                                | 59 MB   | 39 MB   | 0,8 % (49 Ticks) |
| vorher (1.13.0), Lauf 2                                | 59 MB   | 39 MB   | 0,8 % (49 Ticks) |
| nachher (1.14.0), Lauf 1                               | 60 MB   | 40 MB   | 0,8 % (47 Ticks) |
| nachher (1.14.0), Lauf 2                               | 59 MB   | 40 MB   | 0,8 % (51 Ticks) |
| nachher, alle neuen Funktionen aus                     | 59 MB   | 40 MB   | 0,7 % (42 Ticks) |
| nachher, Wach halten an + ein Fenster angepinnt (ohne `--force-idle`) | 61 MB | 34 MB | 0,7 % (41 Ticks) |
| nachher, Tab „Werkzeuge“ geöffnet, Farbpipette 3× benutzt (ohne `--force-idle`) | 62 MB | 37 MB | 0,4 % (26 Ticks) |
| nachher, Einstellungsfenster offen                     | Insel 60 MB, Fenster (eigener Prozess) 63 MB | – | 0,7 % (44 Ticks) |

Das Paket kostet im Leerlauf **etwa 0,5 bis 1 MB RAM** (neue Module, das Register mit 41 Einträgen, das D-Bus-Objekt), die CPU-Last ändert sich nicht messbar: Es gibt keinen neuen Timer, keinen Tick, kein Polling. Wach halten ist eine Sperre ohne Tick (ein Timer auf den Endzeitpunkt), Pins hängen nur ein Signal an den Bildschirm, solange ein Fenster angepinnt ist. Ohne `--force-idle` bestimmt der Zustand die Zahl, nicht die Version: war eben Eingabe (Pille zeigt die Uhr), sind es etwa 25 Ticks, nach einer Minute Ruhe (blinzelndes Maskottchen) etwa 40 bis 47 – gemessen bei 1.13.0 genauso (25 und 47 Ticks in zwei Läufen). PSS hängt davon ab, wie viele andere Prozesse dieselben Seiten teilen, und schwankt deshalb zwischen 34 und 41 MB. **Die Farbpipette** braucht, solange sie offen ist, 15 MB mehr (das Standbild), 60,6 MB → 75 MB → **61,0 MB** nach dem Schließen, auch nach dem dritten Mal; ein erster Entwurf, der den Bildschirm über GDK las, behielt 15 MB für immer (GDK hängt ein Shared-Memory-Bild dauerhaft an), deshalb nimmt jetzt `maim` das Bild auf. **Das Einstellungsfenster** ist ein eigener Prozess (63 MB, solange es offen ist) und danach weg: `pgrep -f island.settings` ist leer.

---

## Voraussetzungen

- **Linux Mint 22.x Cinnamon** (Basis Ubuntu 24.04), X11-Session
- Ein Benutzer mit `sudo`-Rechten (das Script fragt selbst nach dem Passwort)
- Internetverbindung (apt-Pakete und WhiteSur-Themes von GitHub)
- Optional: **Timeshift** eingerichtet (für den Snapshot vor der Installation)

Alle Pakete installiert `install.sh` selbst, u. a. `plank`, `conky-std`, `rofi`, `fonts-inter`, `sassc`; mit `--island` zusätzlich `python3-gi`, `gir1.2-gtk-3.0`, `gir1.2-wnck-3.0`, `gir1.2-xapp-1.0`, `xdotool`, `pulseaudio-utils`, `iso-codes`, `ffmpeg` (Aufnahme, Diktat) und `libsecret-tools` (API-Key im Schlüsselbund). **Optional, nicht automatisch installiert:** `qrencode` (`sudo apt install qrencode`) für die Aktion „QR-Code“ der Zwischenablage.

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
linuxmos-island --clip-send  # Zwischenablage an den Standard-Peer senden (Clip-Transfer, nur auf Aufruf)
linuxmos-clip setup          # Clip-Transfer einrichten: Schlüssel, Peer, Fingerabdruck bestätigen
linuxmos-clip doctor         # Clip-Transfer prüfen (ssh, Schlüssel, Peer, sshd, Eingang)
echo hallo | linuxmos-clip send --peer Laptop   # Text/Datei von der Kommandozeile senden
linuxmos-island --settings   # Einstellungen & Übersicht (eigenes Fenster), --tab overview|gestures|functions
linuxmos-island --action ID  # eine Funktion aus dem Register auslösen, z. B. color-picker, keep-awake, pin-window, clip-actions
linuxmos-island --list-actions  # alle Funktionen als Tabelle (--markdown: Hotkey-Tabelle fürs README)
linuxmos-island --check-hotkeys # Hotkeys auf Konflikte prüfen (untereinander und mit Cinnamon/Mint)
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
| `Ctrl+Alt+Shift+T` | Zwischenablage an den Standard-Peer senden (mit „Clip-Senden“; `Ctrl+Alt+T` ist in Cinnamon das Terminal) |
| `Ctrl+Alt+Shift+V` | Aktionen für den Inhalt der Zwischenablage (Formatierung, Links, JSON, Base64 …) |
| `Ctrl+Alt+C`     | Farbpipette: Lupe am Mauszeiger, Klick wählt, `Esc` bricht ab, Mausrad ändert die Lupe |
| `Ctrl+Alt+K`     | Wach halten ein/aus                                         |
| `Ctrl+Alt+P`     | Aktives Fenster anpinnen / wieder lösen                     |
| `Ctrl+Alt+H`     | Einstellungen & Übersicht (Tab „Übersicht“)                 |
| Im Editor        | `A` Pfeil · `R` Rechteck · `M` Marker · `T` Text · `B` Verpixeln · `O` Text erkennen · `1`–`6` Farbe · `Ctrl+Z` · `Ctrl+C` · `Ctrl+S` = Fertig |
| `Esc`            | MosIsland zuklappen                                         |
| Mausrad auf der Pille | Lautstärke ±5 % (umbelegbar, siehe [Gesten](#werkzeuge--zentrale)) |

Alle Tasten sind im Einstellungsfenster änderbar (Tab „Übersicht“, Klick auf das Kürzel) und stehen in der Config unter `hotkeys`. Die Tabelle oben entspricht dem Register der Insel; `linuxmos-island --list-actions` zeigt es mit den **echten** Werten, `--check-hotkeys` prüft auf Konflikte.

---

## Wichtige Hinweise

> [!WARNING]
> `install.sh` ändert viele Cinnamon-Einstellungen: Panel nach oben, Fensterliste raus, Theme, Icons, Schrift, Effekte, eigene Tastenkürzel, `Super+Space` wird vom Tastaturlayout-Wechsel abgezogen, mit `--island` wird Cinnamons Lautstärke-OSD abgeschaltet. Vorher wird alles nach `~/.local/share/linuxmos/backup/` gesichert, `./uninstall.sh` stellt es wieder her. Ein Timeshift-Snapshot vorab wird empfohlen.

> [!CAUTION]
> `install.sh` lädt die WhiteSur-Themes direkt von GitHub (vinceliuice) und führt deren Installer aus, außerdem installiert es Pakete per `sudo apt`. Nicht mit `sudo` starten – das Script fragt selbst nach dem Passwort.

> [!IMPORTANT]
> Netzwerkzugriffe: Wetter über api.met.no und nominatim.openstreetmap.org (MosIsland) bzw. wttr.in (Conky), Lyrics über lrclib.net – jeweils nur, wenn du die Funktion nutzt. Wechselkurse holt die Command Bar von api.frankfurter.dev (EZB-Kurse, ohne Konto) – nur, wenn du eine Währungsumrechnung tippst, höchstens alle 12 Stunden; abschaltbar mit `command_bar_currency`. Die Websuche öffnet deine Eingabe erst bei `Enter` in der gewählten Suchmaschine. Land und IP des VPN fragt die Insel bei ipinfo.io ab – nur mit `vpn_lookup` (standardmäßig aus), einmal pro VPN-Verbindung; ipinfo.io sieht dabei die Ausgangs-IP des VPN. Der Clipboard-Verlauf liegt unverschlüsselt in `~/.local/share/linuxmos/island/clipboard.json`; Kopien aus Passwort-Managern werden nur übersprungen, wenn diese sie als geheim markieren (KeePassXC & Co.).

> [!IMPORTANT]
> Der Clip-Transfer ist aus, bis du „Clip-Senden“ und/oder „Clip-Empfang“ im Tray-Menü einschaltest. Gesendet wird nur auf deinen Handgriff (Knopf, `Ctrl+Alt+Shift+T`, `linuxmos-clip send`), nie automatisch, und nur per SSH (Schlüssel, `StrictHostKeyChecking=yes`) an Peers, die du mit `linuxmos-clip setup` eingerichtet und deren Fingerabdruck du bestätigt hast. Der Empfänger braucht einen laufenden SSH-Server (Port 22, `openssh-server` wird nicht automatisch installiert). **Verlauf, Eingang (`~/.local/share/linuxmos/island/clip-inbox/`) und empfangene Dateien (`~/Downloads/LinuxMos/`) liegen unverschlüsselt auf der Platte**, wie der Zwischenablage-Verlauf; als privat markierte Kopien (KeePassXC) werden weder gespeichert noch gesendet. Empfangenes landet nie von selbst in der Zwischenablage und wird nie geöffnet. [Sicherheit im Detail](docs/CLIP.md#sicherheit)

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
  "clip_send_enabled": false,
  "clip_receive_enabled": false,
  "clip_max_text_kb": 1024,
  "clip_max_image_mb": 20,
  "clip_max_file_mb": 100,
  "clip_inbox_keep_days": 7,
  "clip_inbox_quota_mb": 500,
  "clip_default_peer": "",
  "clip_peers": [],
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
  "eye_mode_scale": 2.0,
  "clipactions_enabled": true,
  "clipactions_tracking_params": [],
  "colorpicker_enabled": true,
  "colorpicker_format": "hex",
  "colorpicker_history": 20,
  "keepawake_enabled": true,
  "keepawake_minutes": 60,
  "pin_enabled": true,
  "pin_release_on_exit": true,
  "hotkeys": {},
  "gestures_enabled": true,
  "gestures": {},
  "overview_intro_seen": false
}
```

Am bequemsten im **Einstellungsfenster** (Zahnrad oben rechts in der aufgeklappten Insel, `Ctrl+Alt+H`, Tray → „Einstellungen & Übersicht“): Der Tab „Funktionen“ hat zu jedem Schlüssel ein Eingabefeld, das den Wert prüft. Als Datei: Link „Config als Datei öffnen“ im Fenster oder Tray → „Config-Datei öffnen“ – das trägt fehlende Schlüssel mit ihren Standardwerten ein und öffnet die Datei per `xdg-open` (sonst `gio open`, sonst `xed`), also im Standardprogramm für `.json`-Dateien. Gespeichert gilt sofort, ohne Neustart. Ist das JSON ungültig, bleiben die alten Werte aktiv, eine Karte meldet „Config ungültig, alte Werte bleiben“ mit Zeile und Spalte, und die Insel schreibt nicht in die Datei, bis sie wieder stimmt. Unbekannte Schlüssel bleiben erhalten, Werte außerhalb des gültigen Bereichs werden auf die Grenze gesetzt. **Alle Schlüssel mit Standardwert, Bedeutung und Bereich: [docs/CONFIG.md](docs/CONFIG.md).**

`language`: `auto` (Systemsprache: Deutsch bei `de_*`, sonst Englisch), `de` oder `en`. Beim Umschalten im Tray-Menü startet die MosIsland kurz neu (ein laufender Timer geht dabei verloren).

`monitor`: `"primary"` (Hauptmonitor, Standard), `"pointer"` (der Monitor, auf dem die Maus steht, wenn du die Insel per Hotkey oder Tray öffnest – eingeklappt bleibt sie dort, bis du sie woanders öffnest), eine Nummer von links (`0` = ganz links, `1` = der daneben …) oder der Anschlussname wie in `xrandr --listmonitors` (`"HDMI-1"`, `"DP-2"`, `"eDP-1"`). Ist der gewählte Monitor nicht angeschlossen, geht die Insel auf den Hauptmonitor und kehrt beim Einstecken zurück – die Einstellung bleibt. Im Tray-Menü unter „Monitor“ stehen alle angeschlossenen Monitore; gespeichert wird dort der Name, weil die Nummern sich beim Umstecken verschieben können.

Clip-Transfer: `clip_send_enabled` und `clip_receive_enabled` schalten Senden und Empfang getrennt (beide aus; auch im Tray-Menü unter „Clip-Transfer“). `clip_max_text_kb`, `clip_max_image_mb`, `clip_max_file_mb` sind die Limits, die der **Empfänger beim Lesen** erzwingt; `clip_inbox_keep_days` und `clip_inbox_quota_mb` räumen den Eingang auf (beim Start und beim Eintreffen, ohne Timer) bzw. lehnen zu viel ab. `clip_peers` trägt `linuxmos-clip setup` ein, ein Eintrag sieht so aus: `{"name": "Windows-PC", "host": "192.168.0.50", "user": "alec", "port": 22, "key": "~/.ssh/linuxmos_clip_ed25519", "os": "windows"}`; `clip_default_peer` ist das Ziel von Hotkey und `linuxmos-clip send` ohne `--peer`. Alle Einzelheiten: [docs/CLIP.md](docs/CLIP.md), [docs/CONFIG.md](docs/CONFIG.md#clip-transfer).

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
| `~/.local/share/linuxmos/island/clip-inbox/`  | Clip-Eingang (Rechte 700): empfangener Text und Bilder samt Eintrag; Aufräumen nach `clip_inbox_keep_days` |
| `~/Downloads/LinuxMos/`                       | Per Clip-Transfer empfangene Dateien (bleiben immer, auch nach `uninstall.sh`) |
| `~/.ssh/linuxmos_clip_ed25519`                | Schlüssel des Clip-Transfers, nur dafür gedacht (`linuxmos-clip setup`; `uninstall.sh --purge` löscht ihn) |
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

## Clip-Transfer

Text, Bilder und Dateien per SSH zwischen PCs – Linux ↔ Linux im Container getestet, Windows als Doku (ungetestet). Einrichtung Schritt für Schritt: **[docs/CLIP.md](docs/CLIP.md)**, Windows: [docs/CLIP-WINDOWS.md](docs/CLIP-WINDOWS.md), Schlüssel: [docs/CONFIG.md](docs/CONFIG.md#clip-transfer).

**Nur manuell**
- **Senden** nur auf ausdrückliche Handlung: Knopf „An PC senden“ (Papierflieger) an Einträgen der Zwischenablage und Dateien der Ablage, `Ctrl+Alt+Shift+T` (sendet die **aktuelle** Zwischenablage an den Standard-Peer; Text, Bild oder eine in Nemo kopierte Datei), `linuxmos-island --clip-send` oder `linuxmos-clip send`. Kein Watcher, kein `owner-change`, nichts automatisch – geprüft: Zwischenablage mehrfach ändern → kein `ssh`-Prozess, kein Eintrag beim Empfänger. Mehrere Peers: eine kleine Auswahl-Zeile, sonst direkt der Standard-Peer.
- **Empfangen** ist passiv: Der Clip landet im Eingangsordner, im Zwischenablage-Verlauf (Text, Bild, markiert „empfangen“) bzw. in der Ablage und in `~/Downloads/LinuxMos/` (Dateien) und zeigt eine Karte „Vom Windows-PC empfangen: Text (123 Zeichen)“. **Nichts wird automatisch in die Zwischenablage geschrieben**; ein Klick auf Karte oder Eintrag kopiert (und tippt nichts ins Fenster). Läuft Vollbild (oder ist die Insel offen, eine Aufnahme aktiv, eine andere Karte zu sehen), wartet die Karte und erscheint danach; ist die Insel nicht gestartet, wartet der Eintrag bis zum Start.
- Als privat markierte Kopien (Passwort-Manager) werden nie gesendet. Ergebnis immer als Karte: „Gesendet an …“ oder der Grund (nicht erreichbar, Schlüssel abgelehnt, Host-Schlüssel unbekannt, zu groß …), nie ein Dialogfenster.

**Sicherheit**
- Transport: ein einziger `ssh`-Aufruf pro Clip, Daten auf stdin und gestreamt (nie komplett im Speicher), `BatchMode=yes`, `StrictHostKeyChecking=yes`, `ControlMaster=no`, `IdentitiesOnly=yes`, `ConnectTimeout=5`; asynchron (`Gio.Subprocess`), die Oberfläche hängt nie.
- `linuxmos-clip setup` erzeugt `~/.ssh/linuxmos_clip_ed25519` (ed25519, Rechte 600), zeigt beim ersten Mal den **Fingerabdruck** des Empfängers und verlangt eine bewusste Bestätigung (kein stilles `accept-new`) und gibt die Zeile für `authorized_keys` aus: `restrict,command="~/.local/bin/linuxmos-clip receive-ssh" ssh-ed25519 AAAA…`. Damit kann der Schlüssel **nichts anderes als Clips abliefern**.
- `receive-ssh` prüft `SSH_ORIGINAL_COMMAND` gegen eine strenge Regex (nur `receive --type text|image|file` und optional `--name` mit `[A-Za-z0-9._ -]{1,120}`) und führt nie etwas über eine Shell aus. Der Empfänger erzwingt die Limits (Text 1 MB, Bild 20 MB, Datei 100 MB) **beim Lesen von stdin** und räumt beim Abbruch auf; geschrieben wird atomar (Temp-Datei, dann `rename`, der Eintrag zuletzt). Dateinamen werden bereinigt (kein Pfad, kein `..`, kein Punkt am Anfang, keine Steuerzeichen, Länge begrenzt, Kollisionen nummeriert, nie überschrieben, Symlinks weder verfolgt noch angelegt).
- Kein Netzwerk-Port der Insel. Verlauf und Eingang sind Klartext (siehe „Wichtige Hinweise“).

`linuxmos-clip`: `setup`, `doctor`, `send`, `receive`, `receive-ssh`, `apply [ID]` (per `xclip`, nur optional), `list`, `clean`, `--selftest`.

---

## Werkzeuge & Zentrale

Paket „Werkzeuge & Zentrale“ (1.14.0). Alles ist einzeln abschaltbar (Einstellungsfenster, `config.json`); aus heißt aus: keine Handler, keine Timer, keine Sperren – das Log sagt es (`keepawake: disabled, no lock, no timer`, `pins: disabled, no handlers`, `gestures: disabled, no handlers` …). Texte dieses Pakets gibt es nur auf Deutsch.

### Zwischenablage-Aktionen

Am Verlaufseintrag der Knopf **Aktionen** (die drei Punkte), oder `Ctrl+Alt+Shift+V` für das, was gerade in der Zwischenablage ist. Die Aktionen stehen als Knöpfe da, ein Klick führt aus:

| Aktion | Was passiert |
|---|---|
| Formatierung entfernen | Es bleibt reiner Text (HTML/RTF fliegt aus der Zwischenablage) |
| Tracking aus Links entfernen | `utm_*`, `fbclid`, `gclid`, `msclkid`, `mc_eid`, `igshid`, `ref_src` u. ä. verschwinden aus allen Links im Text, funktionale Parameter (`id`, `page`, `q`, `ref`, `v` …) und der Rest bleiben Zeichen für Zeichen. Weitere Namen in `clipactions_tracking_params` („Link bereinigt, 3 Parameter entfernt“) |
| GROSS · klein · Titel-Schreibweise | `don't` wird `Don't`, nicht `Don'T` |
| JSON formatieren / zusammenfassen | Reihenfolge und Umlaute bleiben; kaputtes JSON: Karte mit Zeile und Spalte, die Zwischenablage bleibt, wie sie war |
| URL kodieren / dekodieren · Base64 kodieren / dekodieren | Base64 nimmt auch das URL-sichere Alphabet und fehlende `=`; Binärdaten werden abgelehnt |
| Leerzeichen bereinigen | Doppelte Leerzeichen, Leerzeichen am Zeilenende, mehr als eine Leerzeile, Enden |
| Zeilen sortieren · Doppelte Zeilen entfernen | Ohne Rücksicht auf Groß/klein sortiert; beim Entfernen bleibt die erste |
| QR-Code | Nur, wenn `qrencode` installiert ist (sonst fehlt der Knopf): Karte mit dem Code, „Als Bild kopieren“ |

Das Ergebnis ersetzt die Zwischenablage erst nach dem Klick und steht als **neuer Verlauf-Eintrag** da – das Original bleibt. Die Karte bietet „Original zurück“ und „Einfügen“. **Als privat markierte Kopien (KeePassXC & Co.) werden nie verarbeitet** (Karte „Als privat markiert“; sie stehen auch nie im Verlauf). Ohne Änderung („Nichts zu ändern“) bleibt alles, wie es ist. Reine Textfunktionen: im Leerlauf läuft nichts.

### Farbpipette

`Ctrl+Alt+C`, der Knopf im Tab „Werkzeuge“ oder Tray → „Farbpipette starten“. Die Insel blendet sich aus, der gesamte Bildschirm (alle Monitore, auch mit HiDPI-Skalierung) wird **einmal** aufgenommen und als Standbild über den Bildschirm gelegt – so sind weder Insel noch Overlay im Bild. Am Mauszeiger eine Lupe (11×11 Pixel, 10-fach, die Mitte markiert) mit dem Hex-Wert, aktualisiert nur bei Mausbewegung. **Klick** wählt, **`Esc`** oder Rechtsklick bricht ab, das **Mausrad** ändert die Lupe (5 bis 25 Pixel). Danach liegt die Farbe im Format `colorpicker_format` (`hex`, `rgb`, `hsl`, `hsv`) in der Zwischenablage, die Karte zeigt ein Farbfeld und alle vier Formate (ein Klick auf HEX/RGB/HSL/HSV kopiert dieses). Die letzten 20 Farben (`colorpicker_history`, `~/.local/share/linuxmos/island/colors.json`) stehen im Tab „Werkzeuge“ als kleine Farbfelder: Klick kopiert, Rechtsklick fixiert (gelber Rand, fixierte zählen nicht gegen das Limit). Das Standbild wird sofort wieder freigegeben (Messwert unten). Die Aufnahme macht `maim`, das für die Screenshots ohnehin da ist.

### Wach halten

`Ctrl+Alt+K`, Schalter im Tab „Werkzeuge“ oder das Tray-Häkchen. Solange es an ist: Kaffeetasse in der Pille, kein Bildschirmschoner, keine Bildschirmabschaltung, kein automatischer Ruhezustand; Sperren und Ruhezustand **von Hand** gehen weiter. Nach `keepawake_minutes` (Standard 60, `0` = nie) schaltet es sich selbst aus – ein einziger Timer auf den Endzeitpunkt, kein Tick. Nach einem Neustart ist es immer aus.

**Technik:** `org.gnome.SessionManager.Inhibit` mit den Flags „Ruhezustand“ und „Leerlauf“. Das ist der Sitzungsmanager von Cinnamon (`cinnamon-session`): Er reicht den Leerlauf-Zustand an den Bildschirmschoner und an `cinnamon-settings-daemon` weiter, das Bildschirmabschaltung und automatischen Ruhezustand macht – beide halten still. Hilfsweise `org.freedesktop.ScreenSaver.Inhibit` (das nimmt `csd-screensaver-proxy` an und gibt es an den Sitzungsmanager weiter), zuletzt `systemd-inhibit`. **Die Sperre gehört der D-Bus-Verbindung der Insel:** Wird die Insel beendet oder stürzt sie ab (auch `kill -9`), nimmt `cinnamon-session` die Sperre zurück – bei `systemd-inhibit` hängt sie an einem Kindprozess, der endet, sobald die Insel weg ist. Gegen den echten `cinnamon-session` getestet (siehe Tests).

### Fenster anpinnen

`Ctrl+Alt+P` schaltet das aktive Fenster um (`Wnck.Window.make_above()` / `unmake_above()`); der Knopf im Tab „Werkzeuge“ zeigt die angepinnten Fenster mit „Aufheben“. Solange eines angepinnt ist, sitzt ein Pin mit der Anzahl in der Pille. Nicht anpinnbar sind die Insel selbst, Schreibtisch, Panel und Dock sowie Menüs; bei Vollbild-Fenstern und solchen, die der Fenstermanager nicht erlaubt, sagt eine Karte warum. Die Insel merkt sich die Pins nur für die laufende Sitzung: schließt du ein Fenster (das `window-closed`-Signal von libwnck – ein einzelnes Wnck-Fenster hat kein `closed`), fällt es aus der Liste; nimmst du „Immer im Vordergrund“ im Fenstermenü weg, bemerkt das `state-changed`. Beim Beenden der Insel werden alle Pins aufgehoben (`pin_release_on_exit`). **Vollbild-Spiele und -Videos lassen sich nicht überlagern** – das entscheidet der Fenstermanager, nicht die Insel.

### Einstellungen & Übersicht

`Ctrl+Alt+H`, das Zahnrad oder Tray → „Einstellungen & Übersicht“ (auch `linuxmos-island --settings [--tab …]`). Ein **eigenes Programm** (`linuxmos-island-settings`): Es startet nur, wenn du es öffnest, und ist beim Schließen weg – im Leerlauf kostet es nichts. Es fragt die laufende Insel über D-Bus (nur dein Benutzer, kein Netzwerk) nach Register und Status; läuft die Insel nicht, zeigt es die Config und einen Hinweis. Größe und Position merkt es sich.

- **Übersicht:** Suchfeld oben. Alle Funktionen nach Kategorien mit Beschreibung, **Hotkey**, **Schalter** und **Status**. Ein Klick auf den **Namen** löst die Funktion aus (bei Screenshot, Aufnahme, OCR, QR und Farbpipette tritt das Fenster vorher zur Seite und kommt danach wieder; Funktionen ohne Aktion öffnen ihren Tab, Neustart und Ausschalten fragen nach). Ein Klick auf das **Kürzel** ändert den Hotkey: Kombination drücken, bei Konflikt rote Warnung mit dem Namen der anderen Funktion (Speichern dann nur mit „Trotzdem speichern“), „Zurücksetzen“ pro Hotkey, „Entfernen“. Die Änderung gilt sofort. Oben „Was läuft gerade“ (laufende und ausgeschaltete Funktionen, CPU und RAM der Insel – einmal gelesen, „Aktualisieren“ liest neu, kein Timer), unten die Gesten und der Inhalt des Tray-Menüs.
- **Gesten:** Hauptschalter und eine Auswahl je Geste. Auf der **eingeklappten** Pille: Mausrad, Mausrad mit Umschalt oder Strg, Mausrad am linken oder rechten Rand, Mittelklick, Rechtsklick, Doppelklick. Aktionen: Lautstärke ±, Helligkeit ±, nächster/vorheriger Tab, Play/Pause, nächster/vorheriger Titel, Tab öffnen, Funktion aus dem Register, Einstellungen, Insel aufklappen, nichts. **Die Standardwerte sind das alte Verhalten** (Mausrad = Lautstärke ±5 %, Mittel- und Rechtsklick klappen auf). Reine Ereignisbehandlung; mit dem Hauptschalter aus sind die Handler nicht einmal verbunden. Wer länger als einen Moment auf der Pille verweilt, klappt sie per Hover auf – dann gehören Mausrad und Klicks dem aufgeklappten Tab.
- **Funktionen:** jeder Config-Schlüssel mit passendem Feld (Schalter, Zahl, Auswahl, Text). Ungültiges wird rot markiert und nicht gespeichert, die Config bleibt gültig.

Einmal nach Installation oder Update zeigt die Insel die Karte „Neu: Übersicht der Funktionen“ mit einem Knopf zum Öffnen.

**Hotkeys und Cinnamon:** Auf die Tasten hört Cinnamon (benutzerdefinierte Kürzel, die `install.sh` anlegt). Das Fenster schreibt Änderungen in genau diese Kürzel und in `hotkeys` der Config; ein von Hand geänderter `hotkeys`-Abschnitt wird von der laufenden Insel in die Kürzel übernommen. Hinweis: Cinnamon belegt `Ctrl+Alt+Shift+R` schon selbst (Bildschirmrekorder) – das ist dieselbe Taste wie „Aufnahme vom Bildschirm“ (`linuxmos-island --check-hotkeys` zeigt es); ändere eine der beiden.

## Tests

Im Container getestet, ohne echte Hardware: Xvfb mit echtem **Muffin** (Leerlaufzeit, Fenster, Vollbild) und privatem D-Bus, die Regeln der Erinnerung zusätzlich mit einer künstlichen Uhr (`python3 -m unittest discover -s tests -t .`, 198 Tests; die meisten brauchen nur Python, die zu Wach halten, Hotkeys und Pins brauchen PyGObject bzw. `dbus-daemon` und werden sonst übersprungen; der Loopback-Test des Clip-Transfers startet einen eigenen `sshd` auf 127.0.0.1 und wird übersprungen, wo `sshd` fehlt). Was damit nicht geht (Ohren, echter Bildschirm, deine Standard-Programme, zwei echte PCs, Windows, echte Tasten), steht in [TEST.md](TEST.md) unter „Paket 11“ bis „Paket 13“.

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

**Clip-Transfer (Paket 12)** – im Container mit einem echten `sshd` (zwei Benutzer, 127.0.0.1) und Xvfb mit Muffin; die Bildschirmfotos der Karten wurden angesehen:

| Test | Ergebnis |
|---|---|
| `--selftest` und Rundlauf über `ssh` auf 127.0.0.1 | ✅ `--selftest` (16 Prüfungen, ohne SSH); Text (mit Umlauten), Bild und Datei (3 MB, byte-identisch) über einen echten `sshd`, mit der Zeile `restrict,command="~/.local/bin/linuxmos-clip receive-ssh" …` im installierten Layout (`island-app`) |
| Limits | ✅ zu großer Text, zu großes Bild und zu große Datei werden **beim Empfänger beim Lesen** abgebrochen (auch mit einem Strom ohne Ende getestet: Abbruch kurz nach dem Limit), danach liegt nichts Halbes im Eingang oder in `Downloads/LinuxMos`; ebenso nach `SIGHUP` (so beendet `sshd` einen abgebrochenen Aufruf) und bei einer abgerissenen Verbindung; Quota und Aufräumen alter Einträge als Unit-Tests |
| Sicherheit: Dateinamen | ✅ `../x`, `../../.ssh/authorized_keys`, `.hidden`, Steuer- und Bidi-Zeichen, 500 Zeichen, `C:\dir\x.txt`: nur der letzte Teil, ohne Punkt am Anfang, gekürzt; Kollisionen `name (1).ext`; ein Symlink am Zielnamen wird nicht verfolgt |
| Sicherheit: `receive-ssh`, der beschränkte Schlüssel | ✅ `ls`, `id`, `receive --type file; id`, `… --name '$(id)'`, `/bin/sh`, kein Befehl: abgelehnt (Exit 5), nichts ausgeführt. Mit dem Schlüssel kein Terminal (`PTY allocation request failed`), keine Port-Weiterleitung (`administratively prohibited`), kein `sftp`/`scp`. Beim Schreiben der Regex fand ein Test, dass `$` einen abschließenden Zeilenumbruch durchlässt – jetzt überall `fullmatch` |
| Host-Schlüssel | ✅ `setup` verlangt die Bestätigung (falscher `--fingerprint` bricht ab, nichts gespeichert); unbekannter Host-Schlüssel beim Senden wird abgelehnt, `known_hosts` bleibt unverändert |
| Senden und Empfang aus | ✅ Log `clip: disabled, no monitors`, Modul nicht importiert; `linuxmos-perf` siehe Tabelle oben: CPU unverändert (0,2 %, 13 Ticks), +0,2 MB RSS |
| Empfang bei nicht laufender Insel | ✅ Einträge, die ankamen, während die Insel aus war, werden beim Start zugestellt (Log `3 new in the inbox`; zwei Texte → Karte „2 Einträge empfangen“, beide im Verlauf, Datei in der Ablage) |
| Empfang bei Vollbild | ✅ echtes Vollbildfenster unter Muffin: Log `card waits (fullscreen)`, die Karte erscheint beim Verlassen |
| Peer nicht erreichbar, Schlüssel falsch, Host-Schlüssel unbekannt, Schlüsseldatei fehlt oder zu offen | ✅ jeweils eine verständliche Karte; die Insel bleibt flüssig (Hotkey-Aufruf 30 ms, während der Versuch 5 s auf einen toten Peer wartet; die Insel lässt sich dabei öffnen) |
| Kein automatisches Senden oder Einfügen | ✅ Zwischenablage sechsmal geändert (Text, Dateiliste, Bild) → kein `ssh`-Prozess, kein Log-Eintrag zum Senden, beim Empfänger nichts Neues; empfangener Text steht nach dem Eintreffen im Verlauf, die Zwischenablage bleibt unverändert, bis die Karte angeklickt wird |
| Als privat markierte Kopie | ⚠️ ein Programm, das die Zwischenablage wie KeePassXC bietet (Text **und** `x-kde-passwordManagerHint`), simuliert: Hotkey → Karte „Als privat markiert“, nichts gesendet, nicht im Verlauf. Mit dem echten KeePassXC nicht probiert (TEST.md) |
| Knöpfe, Auswahl, Hotkey-Aktion | ✅ Knopf an Zeilen des Verlaufs, bei zwei Peers die Auswahl-Zeile, Hotkey-Aktion mit Text, Bild (kein Rest im Cache) und einer Datei-URL. Die Tastenkombination `Ctrl+Alt+Shift+T` selbst und ein möglicher Konflikt in Cinnamon konnten ohne Cinnamon nicht geprüft werden (TEST.md) |
| `update.sh` auf bestehender Installation | ⚠️ das echte Script lief als gewöhnlicher Benutzer mit Attrappen für `apt`, `gsettings` und `dconf` (`--pulled --no-themes`; ohne Git und Themes): `config.json` byte-identisch, neue Schlüssel mit Standardwerten, `linuxmos-clip` und die neuen Module installiert, der Hotkey eingetragen, `linuxmos-clip --selftest` läuft aus `island-app`. `git pull` und Themes nicht |
| `uninstall.sh` | ✅ ohne `--purge` ist `linuxmos-clip` weg, Eingang, Peers, Schlüssel und empfangene Dateien bleiben; mit `--purge` sind Eingang, Peers und `~/.ssh/linuxmos_clip_*` weg (andere Schlüssel nicht), empfangene Dateien bleiben |
| Windows (Senden nach Linux, Empfang unter Windows, AutoHotkey, PowerShell-Script) | ❌ **nicht getestet** (kein Windows verfügbar): [docs/CLIP-WINDOWS.md](docs/CLIP-WINDOWS.md), Scripts in `docs/windows/` |

**Werkzeuge & Zentrale (Paket 13)** – im Container mit Xvfb und echtem Muffin, einem **echten `cinnamon-session`** auf einem privaten D-Bus (`--session` mit einer leeren Komponentenliste; er stellt `org.gnome.SessionManager` bereit), den installierten Cinnamon-Schemas (gsettings-Backend `keyfile`, damit zwei Prozesse dasselbe sehen), zwei Monitoren (`xrandr --setmonitor`, 3840×1080) und `GDK_SCALE=2`; die Bildschirmfotos der Karten, der Lupe und der Fenster wurden angesehen:

| Test | Ergebnis |
|---|---|
| Debug-Hilfen | ✅ `--list-actions` (41 Funktionen; ohne Insel aus den Definitionen und der Config, mit Insel mit Status, `--markdown` für die Hotkey-Tabelle), `--action ID` (bei laufender Insel per D-Bus, ohne sie Hinweis und Exit 1), `--check-hotkeys` (Exit 1 bei Konflikt). Der Bericht fand einen **echten** Konflikt: `Ctrl+Alt+Shift+R` („Aufnahme vom Bildschirm“) ist auch Cinnamons `toggle-recording` |
| Idle-CPU und RAM vorher/nachher | ✅ siehe Tabelle oben: +0,5 bis 1 MB RSS, CPU unverändert (49/49 Ticks vorher, 47/51 nachher); mit allen neuen Funktionen aus 42. Ist das Einstellungsfenster geschlossen, läuft kein Prozess dafür (`pgrep -f island.settings` leer) |
| Alle Funktionen aus | ✅ Log: `clipactions: disabled`, `colorpicker: disabled`, `keepawake: disabled, no lock, no timer`, `pins: disabled, no handlers`, `gestures: disabled, no handlers`; die Hotkeys zeigen „… ist aus · Einstellungen & Übersicht“; Mausrad und Mittelklick tun nichts (kein `scroll-event`-Handler verbunden), ein Linksklick öffnet weiter. Zur Laufzeit ausgeschaltet (Config geändert): eine laufende Wach-halten-Sperre wird freigegeben (`off (disabled)`), Pins werden aufgehoben, der Wheel-Handler abgehängt; wieder eingeschaltet geht es ohne Neustart |
| Zwischenablage-Aktionen | ✅ jede Aktion mit Beispieltext als Unit-Test (Tracking: 9 Fälle inkl. Satzzeichen hinter Links, Klammern in Links, kodierte Namen, eigene Liste; kaputtes JSON mit Zeile und Spalte; Base64 mit URL-Alphabet, ohne Padding, Binärdaten abgelehnt). In der Insel: Knopf am Eintrag und Hotkey; „Tracking aus Links entfernen“ → Karte „Link bereinigt, 1 Parameter entfernt“, das Ergebnis steht **neu** oben im Verlauf, das Original darunter. QR-Code: Karte, `zbarimg` liest den Link zurück |
| Als privat markierte Kopie | ⚠️ ein Programm, das Text **und** `x-kde-passwordManagerHint` anbietet, simuliert: nicht im Verlauf, `Ctrl+Alt+Shift+V` → Karte „Als privat markiert“, nichts verarbeitet. Mit dem echten KeePassXC nicht probiert (TEST.md AH3) |
| Farbpipette | ✅ pixelgenau (Streifenbild, jedes Pixel eine andere Farbe) bei Skalierung 100 % über zwei Monitore (x = 100, 301, 1919, 2500, 3839) und bei `GDK_SCALE=2` (x = 101, 300, 1000, 1919); Lupe 11×11, Mausrad 5–25, `Esc` und Rechtsklick brechen ab (Zwischenablage bleibt), Verlauf mit fixierter Farbe, Klick im Tab kopiert. Insel nicht im Bild (das Pixel unter der schwarzen Pille ist weiß), RAM 60,6 → 75 → **61,0 MB**, drei Läufe hintereinander. ⚠️ **150 %** nicht prüfbar (GDK kennt nur ganze Faktoren; die Bruchteil-Skalierung von Cinnamon per `xrandr` hat Xvfb nicht); Pixel genau am Monitorrand (x = 1920) war vom Fensterschatten meiner Testfenster verfälscht |
| Wach halten | ✅ gegen den **echten `cinnamon-session`**: die Sperre erscheint (`GetInhibitors`, Flags 12 = Ruhezustand + Leerlauf, `IsInhibited(8)` = wahr), Auto-Aus nach 1 Minute (Log `off (time is up)`, Liste leer), frei nach Ausschalten, `--quit`, `SIGTERM` und **`kill -9`** der Insel (die Sperre ist mit der D-Bus-Verbindung weg). Die Rückfälle (`org.freedesktop.ScreenSaver`, `systemd-inhibit` mit einem Stellvertreter-Skript: sein Kindprozess endet mit der Insel) als Tests mit Stellvertretern; kein Dienst erreichbar → Karte „Wach halten nicht möglich“. ⚠️ ob der Bildschirm wirklich nicht abschaltet, lässt sich ohne echte Hardware nicht sehen (TEST.md AI1) |
| Fenster anpinnen | ✅ unter Muffin: anpinnen und aufheben per Hotkey-Aufruf (`_NET_WM_STATE_ABOVE`), zwei Fenster („2 Fenster angepinnt“), Fenster schließen (`window-closed`) und Änderung über das Fenstermenü (`set_keep_above(False)` aus einer App erzeugt dieselbe Nachricht wie das Menü) werden erkannt, Pins nach Beenden aufgehoben, mit `pin_release_on_exit: false` bleiben sie, zur Laufzeit ausgeschaltet → alle aufgehoben. Panel/Dock-Fenster: Karte „Panel und Dock lassen sich nicht anpinnen“. Die Regeln (Insel selbst, Schreibtisch, Menü, Vollbild, vom Fenstermanager nicht erlaubt) als Unit-Tests mit einem Wnck-Stellvertreter; Pin mit Anzahl und Kaffeetasse in der Pille angesehen. ⚠️ echtes Vollbild und das echte Cinnamon-Panel nicht probiert |
| Register | ✅ 41 Funktionen; alle 13 bestehenden Hotkeys erscheinen mit den **echten** Werten (auch eine in Cinnamon geänderte Taste, z. B. `Super+V`); Konfliktwarnung getestet mit einem absichtlichen Doppel (`Ctrl+Alt+V` für zwei Funktionen), mit einer Cinnamon-Taste (`Ctrl+Alt+T`) und mit dem echten Fund oben |
| Klick auf den Funktionsnamen | ✅ Wach halten startet in der Insel; Funktion ohne Aktion (Wasser) öffnet ihren Tab; Farbpipette, Screenshot, OCR: das Fenster tritt vorher zur Seite (nicht im Bild) und **kommt zurück**, sobald die Insel das Ende meldet; Neustart fragt nach („Abbrechen“ führt nichts aus, „Ja“ ruft `systemctl reboot` – ein Stellvertreter, **nicht** das echte) |
| Hotkey ändern, übernehmen, zurücksetzen | ✅ Taste drücken (mit Tastatur-Grab, damit Cinnamons eigene Kürzel sie nicht schlucken), Konflikt rot, ohne Strg/Alt/Super abgelehnt, `Esc`, „Trotzdem speichern“, „Zurücksetzen“, „Entfernen“; geschrieben werden `config.json` und das Cinnamon-Kürzel (gsettings), eine von Hand geänderte `hotkeys`-Sektion übernimmt die laufende Insel sofort. ⚠️ dass **echtes** Cinnamon die Taste sofort neu liest, ließ sich ohne Cinnamon nicht sehen (TEST.md AG3) |
| Gesten | ✅ Standard = altes Verhalten: Mittel- und Rechtsklick klappen auf (xdotool), „Mausrad = Lautstärke ±5 %“ ist als Standardwert geprüft (Unit-Test) – die Lautstärke selbst nicht, im Container fehlt `pactl`. Umbelegt wirkt sofort: Mausrad → Funktion „Wach halten“, Umschalt → nichts, Strg → „wie Mausrad“, Rechtsklick → nichts, Doppelklick → Funktion (klappt die vom ersten Klick geöffnete Insel wieder zu). Der linke und rechte Rand als Klassifizierung im Unit-Test, mit der Aktion „Fenster anpinnen“ ohne aktives Fenster nur als Karte gesehen. Hauptschalter aus → keine Gesten, Linksklick öffnet weiter |
| Insel läuft nicht | ✅ Fenster zeigt den Hinweis und die Config, Klick auf eine Funktion sagt, dass die Insel fehlt, Werte lassen sich ändern und gelten beim nächsten Start |
| Ungültige Werte | ✅ `9999` bei „Abstand zur Top Bar“ und `99:99` bei der Uhrzeit: rot, Meldung, **nicht gespeichert** (Datei unverändert, gültiges JSON); eine kaputte Config-Datei wird nie überschrieben. Jeder Standardwert besteht seine eigene Prüfung (Test) |
| `update.sh` auf bestehender Installation | ⚠️ das echte Script lief als gewöhnlicher Benutzer mit Stellvertretern für `apt` und `dpkg` (`--pulled --no-themes`, ohne Git/Themes, ohne Bildschirm) über einer „1.13.0-Installation“: `config.json` **byte-identisch**, eigene und unbekannte Schlüssel bleiben, neue kommen mit Standardwerten; ein selbst geändertes Kürzel (`Super+V`) bleibt, die fünf neuen Kürzel kommen dazu; `linuxmos-island-settings` und die neuen Module liegen da, `--list-actions` aus dem installierten Ordner zeigt `Super+V`. `git pull` und Themes nicht |
| `uninstall.sh` | ✅ ohne `--purge` ist `linuxmos-island-settings` weg, Farbverlauf und Config bleiben; mit `--purge` sind Farbverlauf, Fensterposition und Cache weg |
| Absturz beim Schließen eines gemerkten Fensters | ✅ beim Testen gefunden und behoben: Die Insel merkte sich das Fenster, aus dem sie geöffnet wurde, als libwnck-Objekt; war es inzwischen geschlossen (z. B. das kurzlebige Einstellungsfenster), stürzte libwnck beim Loslassen ab (Segfault, davor nur eine GLib-Warnung). Jetzt wird nur die Fenster-ID gemerkt und bei Bedarf aufgelöst; drei Durchläufe ohne Absturz |

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
- **Clip-Transfer:** Die **Windows-Seite ist ungetestet** (Best Effort); die Windows-Island gibt es noch nicht und soll später (V2.1) einen eigenen Sender und Empfänger bekommen. Der Empfänger braucht einen laufenden SSH-Server (nicht automatisch installiert). Der Zwangsbefehl in `authorized_keys` nutzt `~/.local/bin/linuxmos-clip`, weil sshd ihn ohne dein `PATH` startet. Der Absender eines Clips ist nur die Adresse, von der er kam (`ip` im Peer-Eintrag, damit die Karte den Namen nennt). Der Verlauf kürzt Texte auf 20 000 Zeichen (der Hotkey sendet die volle Zwischenablage). Der Hotkey sendet eine einzelne Datei, mehrere nur einzeln aus der Ablage; Ordner werden nicht gesendet. Die Texte des Clip-Transfers gibt es nur auf Deutsch.
- **Werkzeuge & Zentrale:** Cinnamon belegt `Ctrl+Alt+Shift+R` selbst (Bildschirmrekorder) – dieselbe Taste wie „Aufnahme vom Bildschirm“; `linuxmos-island --check-hotkeys` zeigt es, im Einstellungsfenster lässt sich eine der beiden ändern. **Wach halten** verhindert Bildschirmschoner, Abschaltung und automatischen Ruhezustand über den Sitzungsmanager; Programme, die selbst dagegen arbeiten, und ein Ruhezustand per Deckel (Laptop zuklappen) bleiben unberührt. **Fenster anpinnen** geht nicht über Vollbild-Spiele/-Videos, Fenster, die du selbst über das Fenstermenü anpinnst, zählt die Insel nicht (sie sieht nur die, die sie angepinnt hat). Die **Farbpipette** liest den Bildschirm so, wie X11 ihn liefert: bei Bruchteil-Skalierung (xrandr) die Pixel vor dem Herunterskalieren, nicht den fertigen Bildschirm; unter Wayland geht sie nicht. Das Mausrad auf der Pille wirkt nur, solange die Pille noch zu ist – wer länger als einen Moment darauf bleibt, klappt sie auf. Die Texte des Pakets (Zwischenablage-Aktionen, Werkzeuge, Einstellungsfenster) gibt es nur auf Deutsch. Die Hotkey-Änderung im Fenster schreibt Cinnamons Kürzel und setzt voraus, dass Cinnamon sie live neu liest; ob das auf deinem Mint so ist, prüft [TEST.md](TEST.md) Paket 13 (AG3).
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
- [x] Clip-Transfer: Text, Bilder, Dateien per SSH, nur manuell (`clip_*`, `Ctrl+Alt+Shift+T`, `linuxmos-clip`), siehe [docs/CLIP.md](docs/CLIP.md)
- [ ] Clip-Transfer auf zwei echten PCs und mit Windows prüfen ([TEST.md](TEST.md) Paket 12, [docs/CLIP-WINDOWS.md](docs/CLIP-WINDOWS.md))
- [x] Werkzeuge & Zentrale: Zwischenablage-Aktionen, Farbpipette, Wach halten, Fenster anpinnen, Einstellungsfenster mit Hotkey-Übersicht und Gesten (`Ctrl+Alt+Shift+V`, `Ctrl+Alt+C`, `Ctrl+Alt+K`, `Ctrl+Alt+P`, `Ctrl+Alt+H`)
- [ ] Werkzeuge & Zentrale auf echtem Mint prüfen: echte Tasten, Bildschirmabschaltung, Bruchteil-Skalierung ([TEST.md](TEST.md) Paket 13)
- [ ] Windows-Island (V2.1) mit eigenem Clip-Sender und -Empfänger

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
