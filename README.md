# LinuxMos – macOS-Look für Linux Mint Cinnamon (leichtgewichtig)

Die Linux-Mint-Version des Videos „Windows 27 Golden Gate“: Linux Mint sieht danach aus wie macOS, mit Ampel-Buttons, Glass-Dock, Top Bar, Widgets und Spotlight-Suche. Der Unterschied: **Es läuft im Leerlauf mit nahezu 0 % CPU**. Es gibt keinen Blur-Compositor, keine Dauer-Animationen und keine Hintergrund-Launcher.

> Getestet für **Linux Mint 22.x Cinnamon** (Basis Ubuntu 24.04). Andere Editionen (Xfce/MATE) werden nicht unterstützt.

---

## Inhalt

1. [Was du bekommst](#was-du-bekommst)
2. [Windows-Video → Linux Mint (Mapping)](#windows-video--linux-mint-mapping)
3. [Schnellinstallation](#schnellinstallation)
4. [Optionen](#optionen)
5. [Schritt für Schritt (manuell, wie im Video)](#schritt-für-schritt-manuell-wie-im-video)
6. [Performance – warum das hier nicht 80 % CPU frisst](#performance--warum-das-hier-nicht-80--cpu-frisst)
7. [Anpassen](#anpassen)
8. [Troubleshooting](#troubleshooting)
9. [Rückgängig machen](#rückgängig-machen)
10. [Credits & Lizenzen](#credits--lizenzen)

---

## Was du bekommst

- **Theme** – WhiteSur (GTK 3/4, Cinnamon-Shell, Fensterrahmen) mit macOS-Ampel-Buttons **links**
- **Icons & Cursor** – WhiteSur Icons und WhiteSur Cursors
- **Wallpaper** – WhiteSur Dark/Light (2K)
- **Top Bar** – Cinnamon-Panel oben (28 px), Logo-Menü, Uhr im macOS-Format („So. 25. Okt. 14:32“)
- **Dock** – Plank mit Glass-Theme und macOS-Zoom beim Hovern
- **Animationen** – schnelle Minimize-Animation Richtung Dock
- **Widgets** – große Desktop-Uhr und ein System-Widget (CPU/RAM/Disk/Akku, optional Wetter)
- **Spotlight** – `Super+Space` öffnet die rofi-Suche (Apps, Befehle, Fenster, Dateien)
- **Backup & Undo** – Timeshift-Snapshot (optional) und Sicherung aller geänderten Einstellungen

## Windows-Video → Linux Mint (Mapping)

| Im Video (Windows)                         | Hier (Linux Mint)                                     | Hintergrund-Last |
|--------------------------------------------|-------------------------------------------------------|------------------|
| Restore Point                              | Timeshift-Snapshot und dconf-Backup                   | –                |
| Windhawk UXTheme Hook + Theme              | WhiteSur GTK/Cinnamon/Metacity-Theme                  | 0                |
| Start Menu Styler / Notification Styler    | WhiteSur Cinnamon-Theme (Menü, Benachrichtigungen)    | 0                |
| Taskbar Styler (macOS 26 Clear Dock)       | **Plank** mit WhiteSur-Dock-Theme                     | ~0 %             |
| Dock Animation                             | Plank Zoom (150 %)                                    | nur beim Hovern  |
| macOS Minimize Animation (Genie)           | Cinnamon-Effekt „traditional“, Speed „fast“           | nur beim Minimieren |
| File Explorer Styler + Translucent Windows | Nemo mit WhiteSur-Theme (ohne Blur, absichtlich)      | 0                |
| Resource Redirect (macOS-Icons)            | WhiteSur Icon Theme                                   | 0                |
| Settings Styler                            | Cinnamon Settings übernehmen das GTK-Theme automatisch | 0                |
| Rainmeter Top Bar + Control Center         | Cinnamon-Panel oben (Sound, Netzwerk, Helligkeit)     | 0                |
| Rainmeter Clock / Big Sur Widgets          | **Conky** (Uhr + System-Widget)                       | ~0,03 %          |
| Raycast                                    | **rofi** (Spotlight-Theme)                            | 0 (nur wenn offen) |

## Schnellinstallation

```bash
git clone https://github.com/xypep/LinuxMos.git
cd LinuxMos
./install.sh
```

- Das Script **nicht** mit `sudo` starten. Es fragt selbst nach dem Passwort (für `apt` und Timeshift).
- Danach **einmal ab- und wieder anmelden**.
- Dauer: ca. 3–5 Minuten (vor allem der Download der Icon- und Theme-Repos).

## Optionen

```bash
./install.sh --help
```

| Option              | Wirkung                                                  |
|---------------------|----------------------------------------------------------|
| `--light`           | Helles Design statt Dark Mode                            |
| `--minimal`         | Alle Animationen aus (Dock-Zoom, Fenster-Effekte)        |
| `--weather Berlin`  | Wetter im System-Widget (wttr.in, Update alle 30 min)    |
| `--no-widgets`      | Keine Conky-Widgets                                      |
| `--no-spotlight`    | Keine Spotlight-Suche                                    |
| `--firefox`         | Zusätzlich WhiteSur-Theme für Firefox                    |
| `--snapshot`        | Timeshift-Snapshot ohne Nachfrage                        |
| `--no-snapshot`     | Keinen Timeshift-Snapshot                                |
| `-y`, `--yes`       | Alle Rückfragen automatisch mit „ja“ beantworten         |

Beispiel:

```bash
./install.sh --weather "Hamburg" --snapshot
```

Das Script ist **idempotent**: Du kannst es mehrfach ausführen, zum Beispiel um von Dark auf `--light` zu wechseln. Das Original-Backup wird dabei nicht überschrieben.

---

## Schritt für Schritt (manuell, wie im Video)

Alles hier macht `install.sh` automatisch. Die Anleitung ist für dich, wenn du verstehen willst, was passiert, oder lieber alles von Hand machst.

### 0. Sicherung anlegen (= Restore Point)

**Menu → Timeshift** öffnen, beim ersten Start den Assistenten durchgehen (Typ `RSYNC`) und dann **Create** klicken.

Per Terminal:

```bash
sudo timeshift --create --comments "Before LinuxMos"
```

### 1. Pakete installieren

```bash
sudo apt update
sudo apt install git curl plank conky-std rofi fonts-inter sassc libglib2.0-dev-bin libxml2-utils
```

### 2. Theme mit Ampel-Buttons (= UXTheme Hook + Windows-Theme)

```bash
mkdir -p ~/.cache/linuxmos && cd ~/.cache/linuxmos
git clone --depth 1 https://github.com/vinceliuice/WhiteSur-gtk-theme.git
cd WhiteSur-gtk-theme
./install.sh -c dark -o normal -l --round
```

Danach unter **System Settings → Themes**:

- `Applications`: **WhiteSur-Dark**
- `Window borders`: **WhiteSur-Dark**
- `Desktop`: **WhiteSur-Dark**

Die Buttons kommen nach links unter **System Settings → Windows → Titlebar → Buttons layout**: `Left`. Per Terminal:

```bash
gsettings set org.cinnamon.desktop.wm.preferences button-layout 'close,minimize,maximize:'
```

### 3. Icons und Cursor (= Resource Redirect)

```bash
cd ~/.cache/linuxmos
git clone --depth 1 https://github.com/vinceliuice/WhiteSur-icon-theme.git
git clone --depth 1 https://github.com/vinceliuice/WhiteSur-cursors.git
(cd WhiteSur-icon-theme && ./install.sh)
(cd WhiteSur-cursors && ./install.sh)
```

Dann unter **System Settings → Themes**: `Icons` → **WhiteSur-dark**, `Mouse Pointer` → **WhiteSur-cursors**.

### 4. Wallpaper

Die macOS-artigen Wallpaper liegen im Repo [WhiteSur-wallpapers](https://github.com/vinceliuice/WhiteSur-wallpapers), Ordner `2k/` oder `4k/`. Bild runterladen, dann **Rechtsklick auf den Desktop → Change Desktop Background**.

### 5. Top Bar (= Rainmeter Top Bar)

1. **Rechtsklick aufs Panel → Panel edit mode** aktivieren.
2. **Rechtsklick → Move** und das Panel nach **oben** ziehen.
3. **Rechtsklick → Panel settings → Panel height**: `28`.
4. Das Applet **Grouped window list** entfernen, denn laufende Apps zeigt jetzt das Dock.
5. **Rechtsklick aufs Menü-Icon → Configure → Menu icon**: `start-here-symbolic` (zeigt das Logo aus dem WhiteSur-Icon-Theme), Text leer lassen.
6. **Rechtsklick auf die Uhr → Configure → Use a custom date format**: `%a %e. %b  %H:%M`.

Das „Control Center“ aus dem Video sind hier die Applets für **Sound**, **Network** und **Power** (Helligkeit). Sie sind schon in der Top Bar.

### 6. Dock (= Taskbar Styler + Dock Animation)

1. Plank starten: `plank &`
2. Das Dock-Theme verlinken:

   ```bash
   mkdir -p ~/.local/share/plank/themes/LinuxMos-Dark
   cp ~/.themes/WhiteSur-Dark/plank/dock.theme ~/.local/share/plank/themes/LinuxMos-Dark/
   ```

3. `Ctrl` + Rechtsklick aufs Dock → **Preferences**:
   - `Theme`: **LinuxMos-Dark**
   - `Hide`: **Intelligent**
   - `Icon Size`: `48`
   - `Zoom`: an, `150 %` (die macOS-Vergrößerung)
4. Autostart: **System Settings → Startup Applications → + → Choose application → Plank**.

### 7. Animationen (= Genie-Animation)

**System Settings → Effects**:

- `Minimizing windows`: **Traditional** (schrumpft ins Dock, die leichte Variante von „Genie“)
- `Window animation speed`: **Faster** (das Video nennt die Mac-Animationen selbst „überdramatisch“)

Ein echtes Genie gibt es unter Cinnamon nicht. Dafür bräuchte man Compiz, und das ist genau die Art Effekt-Overhead, die wir vermeiden.

### 8. Widgets (= Rainmeter + JaxCore + Big Sur Widgets)

```bash
mkdir -p ~/.config/linuxmos/conky
cp config/conky/clock.conf ~/.config/linuxmos/conky/
# stats.conf.in ist ein Template – am einfachsten über install.sh erzeugen
conky -d -c ~/.config/linuxmos/conky/clock.conf
```

- **clock.conf** – große Desktop-Uhr im macOS-Stil, Update alle 5 s
- **stats.conf** – Glass-Widget oben rechts (CPU, RAM, Disk, Akku, optional Wetter), Update alle 3 s

Steuern mit `linuxmos-widgets start|stop|restart`.

### 9. Spotlight (= Raycast)

```bash
rofi -show drun -theme ~/.config/linuxmos/rofi/spotlight.rasi
```

Tastenkürzel: **System Settings → Keyboard → Shortcuts → Custom Shortcuts → Add custom shortcut**. Als Command `~/.local/bin/linuxmos-spotlight` eintragen, als Shortcut `Super+Space`.

Achtung: `Super+Space` ist in Cinnamon standardmäßig „Switch input source“ (Tastaturlayout wechseln). `install.sh` gibt das Kürzel frei. Der Layout-Wechsel geht dann über `Shift+Super+Space` oder `XF86Keyboard`.

Bedienung in der Suche:

- `Shift+→`: Modus wechseln (Apps → Run → Fenster → Dateien)
- `Esc` oder `Super+Space`: Suche schließen

> Du willst mehr Raycast-Features (Rechner, Erweiterungen)? Dann nimm [Ulauncher](https://ulauncher.io/). Der läuft aber dauerhaft im Hintergrund (~60–100 MB RAM). rofi braucht 0 MB, solange es nicht offen ist.

---

## Performance – warum das hier nicht 80 % CPU frisst

### Typische CPU-Fresser bei macOS-Setups unter Linux

| Ursache                                          | Was LinuxMos stattdessen macht                         |
|--------------------------------------------------|--------------------------------------------------------|
| Compositor mit Blur (picom `dual_kawase`, KWin-Blur) | Kein Blur. Transparenz kommt nur aus dem Theme (statisch) |
| Conky mit Lua/Cairo und `update_interval 0.5`    | `conky-std` ohne Lua, Update alle 3–5 s                |
| Cinnamon-Desklets (laufen im Cinnamon-Prozess)   | Conky als eigener, winziger Prozess                    |
| Dock-Animationen in Endlosschleife               | Plank animiert nur beim Hovern oder Starten            |
| Launcher-Daemons (Ulauncher, Albert)             | rofi startet erst auf Tastendruck                      |
| Wetter-Widget, das jede Sekunde pollt            | `curl` alle 30 Minuten                                 |

### Gemessene Werte (Leerlauf)

| Komponente              | CPU      | RAM      |
|-------------------------|----------|----------|
| Conky Uhr (`clock.conf`)  | ~0,00 %  | ~15 MB   |
| Conky System (`stats.conf`) | ~0,03 % | ~15 MB   |
| Plank (ohne Hover)      | ~0 %     | ~30 MB   |
| rofi                    | 0 % (nicht aktiv) | 0 MB |

Die Conky-Werte wurden 30 s lang unter Xorg gemessen. Für Plank und rofi sind es typische Erfahrungswerte.

### Selbst messen

```bash
linuxmos-perf        # misst 5 s lang cinnamon, Xorg, plank, conky, ...
linuxmos-perf 15     # 15 s
```

Wenn die Summe im Leerlauf über ~10 % liegt, stimmt etwas nicht. Dann in dieser Reihenfolge prüfen:

1. **GPU-Treiber**: **Driver Manager** öffnen und den proprietären NVIDIA-Treiber nutzen, falls vorhanden. Ohne richtigen Treiber rendert Cinnamon per CPU (llvmpipe). Prüfen mit:

   ```bash
   glxinfo -B | grep "OpenGL renderer"
   ```

2. **Noch schlanker**: `./install.sh --minimal` schaltet alle Animationen ab.
3. **Widgets aus**: `linuxmos-widgets stop`, dann neu messen.

---

## Anpassen

| Was                        | Wie                                                                              |
|----------------------------|----------------------------------------------------------------------------------|
| Widget-Position            | `gap_x` / `gap_y` / `alignment` in `~/.config/linuxmos/conky/*.conf`, danach `linuxmos-widgets restart` |
| Uhr ohne Datum             | Erste `${alignc}`-Zeile in `clock.conf` löschen                                  |
| Dock-Apps                  | Apps per Drag & Drop ins Dock ziehen; zum Entfernen rausziehen                   |
| Dock-Einstellungen         | `Ctrl` + Rechtsklick aufs Dock → **Preferences**                                 |
| Akzentfarbe Spotlight      | `accent:` in `~/.config/linuxmos/rofi/spotlight.rasi`                            |
| Hell/Dunkel wechseln       | `./install.sh --light` bzw. `./install.sh` erneut ausführen                      |
| Login-Screen               | **Login Window** (Admin) → `Appearance` → Hintergrundbild und Theme wählen       |

## Troubleshooting

<details>
<summary><b>Theme wird nur teilweise angewendet</b></summary>

Einmal ab- und wieder anmelden. Flatpak-Apps brauchen zusätzlich:

```bash
cd ~/.cache/linuxmos/WhiteSur-gtk-theme && ./tweaks.sh -F
```

</details>

<details>
<summary><b>Widgets liegen über den Fenstern oder sind unsichtbar</b></summary>

```bash
linuxmos-widgets restart
```

Wenn sie unsichtbar bleiben: In der jeweiligen `.conf` den Wert `own_window_type = 'normal'` auf `'desktop'` ändern.

</details>

<details>
<summary><b>Super+Space macht nichts</b></summary>

**System Settings → Keyboard → Shortcuts → Custom Shortcuts**: Prüfen, ob „Spotlight (LinuxMos)“ existiert. Nach dem Ändern hilft manchmal `Ctrl+Alt+Esc` (Cinnamon neu laden).

</details>

<details>
<summary><b>Das alte Panel unten ist noch da / das Dock fehlt</b></summary>

`Ctrl+Alt+Esc` lädt Cinnamon neu. Das Dock startest du manuell mit `plank &`.

</details>

<details>
<summary><b>Wetter zeigt „nicht verfügbar“</b></summary>

wttr.in ist manchmal überlastet. Das Widget versucht es alle 30 min automatisch erneut.

</details>

## Rückgängig machen

```bash
./uninstall.sh           # Einstellungen, Panel, Shortcuts wiederherstellen; Dock und Widgets entfernen
./uninstall.sh --purge   # zusätzlich Themes, Icons, Cursor und Wallpaper löschen
```

Pakete entfernst du bei Bedarf manuell:

```bash
sudo apt remove plank conky-std rofi fonts-inter
```

Wenn alles schiefgeht: **Timeshift → Restore** auf den Snapshot „Before LinuxMos“.

## Projektstruktur

```text
install.sh                 Installation (Themes, Panel, Dock, Effekte, Widgets, Spotlight)
uninstall.sh               Wiederherstellung aus dem Backup
lib/cinnamon_tweaks.py     Helfer für Panel, Applets, Shortcuts, Templates
config/conky/              Uhr- und System-Widget
config/rofi/               Spotlight-Theme (Template)
bin/linuxmos-widgets       Widgets starten/stoppen
bin/linuxmos-spotlight     Spotlight öffnen/schließen
bin/linuxmos-perf          CPU-Last messen
```

Gesichert wird nach `~/.local/share/linuxmos/backup/`, der Download-Cache liegt in `~/.cache/linuxmos/`.

## Credits & Lizenzen

- [WhiteSur GTK Theme, Icons, Cursors, Wallpapers](https://github.com/vinceliuice) von vinceliuice (GPL-3.0). Die Themes werden beim Installieren direkt vom Original-Repo geladen und sind nicht in diesem Repo enthalten.
- [Plank](https://launchpad.net/plank), [Conky](https://github.com/brndnmtthws/conky), [rofi](https://github.com/davatorium/rofi), [Inter](https://rsms.me/inter/)

Dieses Projekt steht in keiner Verbindung zu Apple Inc. „macOS“ ist eine Marke von Apple Inc.
