> [!NOTE]
> **Vibe-coded project** – This project was built largely with AI assistance (Claude).
> The code works for my use case but has not been professionally reviewed. Use at your own risk.

[Deutsch](README.md) · **English**

# LinuxMos

Turns Linux Mint Cinnamon into a lightweight macOS look-alike – dock, top bar, widgets, Spotlight and an optional Dynamic Island – without the desktop eating CPU while idle.

![MosIsland](https://img.shields.io/badge/MosIsland-1.6.0-blue)
![Platform](https://img.shields.io/badge/platform-Linux%20Mint%2022%20Cinnamon-87CF3E)
![Display server](https://img.shields.io/badge/display-X11-lightgrey)

---

## Preview

<p align="center">
  <img src="docs/img/island-home.png" alt="MosIsland expanded: music with cover art, weather, Pomodoro timer" width="45%">
  &nbsp;
  <img src="docs/img/island-pills-nusa.png" alt="MosIsland collapsed: lyrics, Pomodoro, water reminder, headphones, brightness, Caps Lock" width="45%">
</p>

---

## Table of contents

- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Usage](#usage)
- [Important notes](#important-notes)
- [Configuration](#configuration)
- [Known issues](#known-issues)
- [Roadmap](#roadmap)
- [License](#license)
- [Credits](#credits)

> The detailed step-by-step guide (including how to do everything by hand) is available in German: [docs/ANLEITUNG.md](docs/ANLEITUNG.md).

---

## Features

**macOS look** (`install.sh`)
- **Theme** – WhiteSur (GTK 3/4, Cinnamon, window borders) with traffic-light buttons on the left, icons, cursor, wallpaper, Inter font
- **Top bar** – Cinnamon panel moved to the top (28 px), logo menu, macOS-style clock
- **Dock** – Plank with a glass theme and zoom on hover
- **Animations** – fast window effects; `--minimal` turns them all off
- **Widgets** – Conky clock and a glass system widget (CPU, RAM, disk, battery, optional weather)
- **Spotlight** – `Super+Space` opens a rofi search (apps, commands, windows, files)
- **Backup & undo** – optional Timeshift snapshot, backup of every changed setting, `uninstall.sh`
- **Update** – `update.sh` fetches new versions without touching your settings

<img src="docs/img/widgets.png" alt="Conky clock and system widget" width="70%">

**MosIsland** (optional, `--island`) – a Dynamic Island at the top centre, inspired by [Island](https://github.com/exuupery/island) and [Nusa](https://rama2555.github.io/nusa/). It has its own name so it is not mistaken for exuupery's Island; the command stays `linuxmos-island`.
- **Music** from any MPRIS player (Spotify, Firefox/YouTube, VLC …) with cover art, play/pause/skip and seeking
- **Synced lyrics** (LRCLIB) – the current line lights up, click a line to jump there, optionally shown in the pill
- **Clipboard** – history with search and pins; one click pastes straight into the active window; optionally cleared after X minutes (pins stay)
- **Shelf** – drop files on the island and drag them out again later
- **To-dos** with reminders, a **note**, **Pomodoro** and timers, a **water reminder** with daily goal and chart
- **Weather** (MET Norway, no API key) with rain warning
- **Screenshots** – an area (`Ctrl+Alt+S`) or the monitor under the pointer (`Ctrl+Alt+Shift+S`), straight to the clipboard and `~/Pictures/LinuxMos`; the island hides itself for the shot. Clicking the notice opens the **markup editor** in the island's look (black, floating tool pill): arrow, rectangle, highlighter, text and pixelate for private data
- **Text from the screen (OCR)** – `Ctrl+Alt+O`, drag an area: tesseract (German + English) recognises the text, it goes to the clipboard and shows as a **card** on the island (preview, "To note", "Copy"). Also in the screenshot editor via the "Text" button
- **QR codes & barcodes** – `Ctrl+Alt+Q`: content to the clipboard, an "Open" button for links; for Wi-Fi codes the password is copied and "Connect" is offered
- **Notifications as cards** – every notification shows on top of the island: app icon, picture (avatar, cover), title, text, hides by itself; when several arrive, the newest replaces the old one and counts along ("+2"). A click brings the app to the front, 🔕 hides an app. Cinnamon stays the notification service, the island only listens in; the history stays in the notifications applet
- **Controls** – Wi-Fi, Bluetooth, Do Not Disturb, dark mode, mic, volume, brightness, screenshot, lock, suspend, restart, power off
- **Live activities** – volume, brightness, Caps Lock, keyboard layout, charging, Wi-Fi lost, headphones connected, VPN on/off (optionally with country and IP)
- **Microphone & camera in use** – an orange dot while an app records, a green one while the camera is on (like iOS), with the app's name; opened, the header has a mic button to mute
- **Download progress** – a small ring on the island while Firefox or Chromium/Chrome downloads (with a percentage for Chromium), "Download finished" with a click to the file
- **Mascot** – a pair of eyes while you are away; they doze off and wave when you come back
- **Tray menu** – autostart, mascot, minimal notch, OSD, clipboard auto-clear, screenshot, text & QR, notifications (on/off, do not disturb, hide apps), live hints (mic & camera, VPN, downloads), language, quit
- **English or German** – follows the system language automatically, switchable in the tray menu (`Sprache / Language`)

**Lightweight** – measured: Conky widgets ~0.03 % CPU, MosIsland ~0.1 % CPU (Cinnamon 6, music playing). No blur compositor, no polling loops.

---

## Requirements

- **Linux Mint 22.x Cinnamon** (based on Ubuntu 24.04), X11 session
- A user with `sudo` rights (the script asks for the password itself)
- Internet connection (apt packages and the WhiteSur themes from GitHub)
- Optional: **Timeshift** set up (for the snapshot before installing)

`install.sh` installs every package itself, e.g. `plank`, `conky-std`, `rofi`, `fonts-inter`, `sassc`; with `--island` also `python3-gi`, `gir1.2-gtk-3.0`, `gir1.2-wnck-3.0`, `gir1.2-xapp-1.0`, `xdotool`, `pulseaudio-utils`, `iso-codes`.

---

## Installation

### Option A – with Git (recommended, makes `update.sh` work)

```bash
git clone https://github.com/xypep/LinuxMos.git
cd LinuxMos
./install.sh                 # macOS look only
./install.sh --island        # including MosIsland
```

### Option B – as a ZIP

1. On GitHub: **Code → Download ZIP**
2. Extract the archive and `cd` into the folder
3. Run `./install.sh` (to update later: download the new ZIP, then run `./update.sh`)

Then **log out and back in once**.

---

## Usage

1. Install (see above), e.g. `./install.sh --island --weather Berlin`
2. Log out and back in
3. Move the mouse over MosIsland at the top centre – it expands
4. Updates: `./update.sh` · Undo: `./uninstall.sh`

### `install.sh` options

```bash
./install.sh --help
```

| Option              | Effect                                                   |
|---------------------|----------------------------------------------------------|
| `--light`           | Light theme instead of dark mode                         |
| `--minimal`         | All animations off                                       |
| `--weather CITY`    | Weather location for the widget and MosIsland            |
| `--island`          | Install MosIsland                                        |
| `--no-widgets`      | No Conky widgets                                         |
| `--no-spotlight`    | No Spotlight search                                      |
| `--firefox`         | WhiteSur theme for Firefox as well                       |
| `--snapshot` / `--no-snapshot` | Timeshift snapshot without asking / never     |
| `-y`, `--yes`       | Answer "yes" to every question                           |

### More commands

```bash
./update.sh --check          # is there a new version?
./update.sh                  # update (keeps your settings)
./update.sh --full           # also re-apply the design
./uninstall.sh               # restore everything
./uninstall.sh --purge       # also delete themes and MosIsland data
linuxmos-perf                # measure the desktop's CPU load
linuxmos-widgets restart     # restart the Conky widgets
linuxmos-island --tab todo   # open MosIsland on a tab
linuxmos-island --shot area  # screenshot: area | screen (monitor under the pointer)
linuxmos-island --ocr        # recognise the text in an area
linuxmos-island --qr         # read a QR code/barcode in an area
linuxmos-island --set-city "Munich"
```

### Hotkeys

| Hotkey           | Action                                                      |
|------------------|-------------------------------------------------------------|
| `Super+Space`    | Open/close the Spotlight search                             |
| `Shift+→`        | In the search: switch mode (apps, run, windows, files)      |
| `Ctrl+Alt+I`     | Open/close MosIsland                                        |
| `Ctrl+Alt+V`     | Clipboard history (type to search, `Enter` pastes)          |
| `Ctrl+Alt+S`     | Screenshot of an area (`Esc` or the hotkey again cancels)   |
| `Ctrl+Alt+Shift+S` | Screenshot of the monitor under the pointer               |
| `Ctrl+Alt+O`     | Recognise the text in an area (OCR) → clipboard             |
| `Ctrl+Alt+Q`     | Read a QR code/barcode in an area → clipboard               |
| In the editor    | `A` arrow · `R` rectangle · `M` highlighter · `T` text · `B` pixelate · `O` recognise text · `1`–`6` color · `Ctrl+Z` · `Ctrl+C` · `Ctrl+S` = Done |
| `Esc`            | Collapse MosIsland                                          |
| Mouse wheel on the pill | Volume ±5 %                                          |

---

## Important notes

> [!WARNING]
> `install.sh` changes many Cinnamon settings: panel to the top, window list removed, theme, icons, font, effects, custom shortcuts; `Super+Space` is taken from the keyboard-layout switcher, and with `--island` Cinnamon's volume OSD is turned off. Everything is backed up to `~/.local/share/linuxmos/backup/` first, and `./uninstall.sh` restores it. A Timeshift snapshot beforehand is recommended.

> [!CAUTION]
> `install.sh` downloads the WhiteSur themes straight from GitHub (vinceliuice) and runs their installers; it also installs packages via `sudo apt`. Do not run it with `sudo` – it asks for the password itself.

> [!IMPORTANT]
> Network access: weather via api.met.no and nominatim.openstreetmap.org (MosIsland) or wttr.in (Conky), lyrics via lrclib.net – only when you use the feature. The VPN's country and IP come from ipinfo.io – only with `vpn_lookup` (off by default), once per VPN connection; ipinfo.io sees the VPN's exit IP. The clipboard history is stored unencrypted in `~/.local/share/linuxmos/island/clipboard.json`; copies from password managers are only skipped if they mark them as secret (KeePassXC and similar).

> [!IMPORTANT]
> While MosIsland shows notifications as cards, it turns Cinnamon's own banners off (`org.cinnamon.desktop.notifications display-notifications`) – notifications then go to the notifications applet without a popup, the island shows the card. Quitting the island or switching off tray → "Notifications" → "Show on the island" brings Cinnamon's banners back. "Do not disturb" (controls tab, tray) then applies to the island; critical ones (e.g. battery almost empty) still come through. The cards show message contents large at the top centre – consider "Do not disturb" while sharing your screen.

> [!IMPORTANT]
> Clicking a clipboard entry sends `Ctrl+V` (`Ctrl+Shift+V` in terminals) to the previously active window via `xdotool`.

---

## Configuration

MosIsland: `~/.config/linuxmos/island/config.json` – most switches are also in the tray menu and the water tab.

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
  "water_goal_ml": 2000,
  "water_portion_ml": 250,
  "water_reminders": true,
  "water_start": "09:00",
  "water_end": "21:00",
  "water_interval_min": 60
}
```

`language`: `auto` (system language: German for `de_*`, English otherwise), `de` or `en`. Switching it in the tray menu restarts MosIsland briefly (a running timer is lost).

Screenshots: `screenshot_save` also keeps every shot as a PNG (otherwise clipboard only), `screenshot_dir` changes the folder (empty = `~/Pictures/LinuxMos`, localised like `~/Bilder/LinuxMos`), `screenshot_open_editor` opens the editor right after the shot. "Done" in the editor overwrites the shot with the marked-up version. All of it is also in the tray menu under "Screenshot".

Text & QR: `ocr_languages` are tesseract languages joined with `+` (more via `sudo apt install tesseract-ocr-fra` etc., list: `tesseract --list-langs`). By default the lines of a paragraph are joined and hyphens at line ends removed; `ocr_keep_linebreaks` keeps the text line by line. `qr_open_links` opens links from QR codes in the browser right away instead of showing an "Open" button. Both switches are also in the tray menu under "Text & QR". Recognition runs entirely locally, the image is deleted afterwards.

Notifications: `notifications_on_island` shows them as cards on the island (and turns Cinnamon's banners off for that), `notifications_dnd` is the island's "do not disturb", `notifications_exclude` a list of app names (as shown on the card) or desktop IDs (`firefox`, `org.telegram.desktop`) that never show as a card – e.g. `["Spotify", "Thunderbird"]`. All of it is also in the tray menu under "Notifications", which lists the recently seen apps to tick off. The island only listens in via a D-Bus monitor and stores none of it (only the app names for that list, in `~/.local/share/linuxmos/island/notifications.json`).

Live hints: `privacy_indicator` shows the orange (microphone) and green (camera) dot; the microphone comes from PipeWire/PulseAudio (`pactl subscribe`, level meters like pavucontrol don't count), the camera from inotify on `/dev/video*`. `vpn_status` reports VPN on/off (NetworkManager VPNs, WireGuard and the tun/wg interfaces of other VPN apps such as Mullvad), `vpn_lookup` adds country and IP from ipinfo.io (an outside request, hence off by default). `downloads_progress` watches the download folder (`downloads_dir`, empty = the XDG download folder, e.g. `~/Downloads`) for `.part` (Firefox) and `.crdownload` (Chromium/Chrome) files. All of it is also in the tray menu under "Live hints".

Other files:

| File                                          | Contents                                       |
|-----------------------------------------------|------------------------------------------------|
| `~/.config/linuxmos/conky/*.conf`             | Widget position and look (`gap_x`, `gap_y`, `alignment`) |
| `~/.config/linuxmos/rofi/spotlight.rasi`      | Look of the Spotlight search                   |
| `~/.local/share/linuxmos/install.conf`        | Chosen install options (used by `update.sh`)   |
| `~/.local/share/linuxmos/island/`             | MosIsland data: note, to-dos, water log, clipboard history, shelf |

---

## Known issues

- **A complete `install.sh` run on real Mint 22 has not been tested yet** – MosIsland, panel changes, update and uninstall were tested under Cinnamon 6, the WhiteSur install step was not. Please report problems.
- **MosIsland needs ~115 MB RAM** – almost entirely Python + GTK3 itself.
- **No real "genie" effect and no blur** – on purpose, both cost performance all the time.
- **MosIsland is X11 only** (the default on Mint Cinnamon). Its UI is English and German; `install.sh`, `update.sh` and `uninstall.sh` only speak German.
- **Lyrics/weather** depend on LRCLIB and MET Norway – not every song has synced lyrics.
- **While MosIsland is not running** there is no volume OSD (Cinnamon's own is turned off) – switching off "Show volume & brightness" in the tray menu brings Cinnamon's OSD back.
- **Click-to-paste** does not work in windows running as root – the entry is still on the clipboard.
- **OCR quality** depends on the font size – very small or heavily stylised text, text on photos and handwriting are often not recognised cleanly. Picking a larger area or zooming in first helps.
- **Wi-Fi passwords from QR codes** end up in the clipboard history like everything you copy – delete them there if needed or set `clipboard_autodelete_min`.
- **Buttons in notifications** ("Reply", "Accept" …) are not on the card – only Cinnamon, as the notification service, can trigger them. Clicking the card brings the app to the front (the sender's window, otherwise the app is started); the buttons are in the notifications applet.
- **If MosIsland crashes** (or is killed with `kill -9`), Cinnamon's banners stay off until the island runs again. Back right away: `gsettings set org.cinnamon.desktop.notifications display-notifications true` (or start `linuxmos-island` and switch the cards off in the tray). `uninstall.sh` restores them as well.
- **In front of fullscreen apps** (videos, games) the island stays hidden, and so do the cards – the notifications are in the applet afterwards.
- **Download percentages** only exist when the browser reports its progress (Chromium/Chrome do); Firefox downloads show size and speed. Downloads into other folders than `downloads_dir` are not seen.
- **The camera's app** is only found for your own user's programs; when the camera runs through PipeWire (e.g. Flatpak apps via the portal) it says "PipeWire" instead of the app. The camera can't be muted like the microphone – there is no system switch for it.
- **A screenshot on the clipboard** is held by a small `xclip` process in the background until you copy something else (so the image survives quitting the island).

More solutions (German): [docs/ANLEITUNG.md → Troubleshooting](docs/ANLEITUNG.md#troubleshooting)

---

## Roadmap

- [x] macOS look with theme, top bar, dock, widgets, Spotlight
- [x] Backup, uninstall and update (`update.sh`)
- [x] MosIsland with music, lyrics, clipboard, shelf, to-dos, Pomodoro, water, weather, controls
- [x] Live activities, mascot, tray menu
- [x] Clipboard auto-clear (`clipboard_autodelete_min`)
- [ ] Complete test run on Linux Mint 22.x
- [x] English UI for MosIsland (`language`, tray menu)
- [x] Screenshot tool with markup editor (`Ctrl+Alt+S`, `Ctrl+Alt+Shift+S`)
- [x] Text from the screen (OCR, `Ctrl+Alt+O`) and QR codes (`Ctrl+Alt+Q`)
- [x] Notifications as cards on the island (`notifications_on_island`, exclusion list)
- [x] Microphone/camera dot with mute button, VPN status, download progress (`privacy_indicator`, `vpn_status`, `downloads_progress`)

---

## License

This project is licensed under the MIT License – see [LICENSE](LICENSE).

The WhiteSur themes (GPL-3.0) are not part of this repository; they are downloaded from the original during installation.

---

## Credits

- [WhiteSur GTK theme, icons, cursors, wallpapers](https://github.com/vinceliuice) – macOS theme (GPL-3.0)
- [Plank](https://launchpad.net/plank) – dock
- [Conky](https://github.com/brndnmtthws/conky) – desktop widgets
- [rofi](https://github.com/davatorium/rofi) – Spotlight search
- [Inter](https://rsms.me/inter/) – font
- [PyGObject / GTK 3](https://pygobject.gnome.org/) – MosIsland UI
- [maim / slop](https://github.com/naelstrof/maim) – screenshots and area selection
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) (Apache-2.0) – text recognition
- [ZBar](https://github.com/mchehab/zbar) (LGPL-2.1) – QR codes and barcodes
- [MET Norway](https://www.met.no/en) (CC BY 4.0), [OpenStreetMap](https://www.openstreetmap.org/copyright) (ODbL), [LRCLIB](https://lrclib.net) – weather, geocoding, lyrics
- Ideas: [Island](https://github.com/exuupery/island) by exuupery and [Nusa](https://rama2555.github.io/nusa/) by Rama (both Windows, closed source) – no code or artwork reused
- Built with the help of Claude (Anthropic)

This project is not affiliated with Apple Inc. "macOS" is a trademark of Apple Inc.
