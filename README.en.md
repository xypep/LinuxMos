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
- **Command bar** – `Ctrl+Alt+Space` or the magnifier tab: one input field for apps, files (recently used + home folder), calculator (`12*7`, `sqrt(2)`, `50*20%`), units (`5 km in mi`, `100 f in c`, `1 GiB in MB`), currencies (`20 usd in eur`, ECB rates) and web search (DuckDuckGo, Google, Startpage …). `Enter` opens or copies, `Ctrl+Enter` pastes the result into the previous window or shows the file in its folder. The rofi Spotlight search (`Super+Space`) stays as an alternative
- **Controls** – Wi-Fi, Bluetooth, Do Not Disturb, dark mode, mic, volume, brightness, screenshot, lock, suspend, restart, power off
- **Live activities** – volume, brightness, Caps Lock, keyboard layout, charging, Wi-Fi lost, headphones connected, VPN on/off (optionally with country and IP)
- **Microphone & camera in use** – an orange dot while an app records, a green one while the camera is on (like iOS), with the app's name; opened, the header has a mic button to mute
- **Download progress** – a small ring on the island while Firefox or Chromium/Chrome downloads (with a percentage for Chromium), "Download finished" with a click to the file
- **Several monitors** – the island sits on the primary monitor, a fixed one or the one with the mouse (it moves when a hotkey or the tray opens it); it follows monitors being plugged in and out by itself
- **Screen recording** – `Ctrl+Alt+R` (area) or `Ctrl+Alt+Shift+R` (monitor under the pointer); the same key ends it. MP4 (H.264, with system sound or the microphone if you like) or GIF, saved in `~/Videos/LinuxMos`. The island steps out of the picture, the tray icon turns red (a click ends it), then a card with "Play" and "Show in folder". A forgotten recording stops by itself after 30 minutes
- **AI chat & dictation** (optional, your own API key, off by default) – a chat tab (`Ctrl+Alt+A`), the answer streams in live. Works with any OpenAI-compatible server: OpenAI, OpenRouter, Ollama, LM Studio … The key lives in the keyring (libsecret), not in the config. **Dictation** (`Ctrl+Alt+M`): speak, press the key again – the text is typed into the active window (or lands in the chat field)
- **Mascot** – eyes, a cat, a robot or a blob while you are away; they doze off and wave when you come back
- **Tray menu** – autostart, mascot (pick the character), minimal notch, OSD, clipboard auto-clear, search (files, currencies, search engine), screenshot, text & QR, screen recording (format, sound), AI (chat, dictation, connection & API key), notifications (on/off, do not disturb, hide apps), live hints (mic & camera, VPN, downloads), monitor, language, quit
- **English or German** – follows the system language automatically, switchable in the tray menu (`Sprache / Language`)

**Lightweight** – measured: Conky widgets ~0.03 % CPU, MosIsland ~0.1 % CPU (Cinnamon 6, music playing) and ~60 MB RAM. No blur compositor, no polling loops.

| MosIsland RAM (Xvfb, fresh profile, 10 s after start) | before (1.9.0) | after (1.10.0) |
|-------------------------------------------------------|----------------|----------------|
| RSS (what `top` shows)                                | 116 MB         | **60 MB**      |
| PSS (shared libraries counted proportionally)         | 87 MB          | **49 MB**      |
| Every tab opened once                                 | –              | 62 MB          |
| CPU while idle (60 s, Xvfb)                           | 0.2 %          | 0.2 %          |

The biggest chunk (−49 MB) was Mesa: GTK loads the OpenGL driver including LLVM at start-up just to pick a window format – yet the island never draws with OpenGL. The rest (−7 MB): tabs are built the first time they open, weather/lyrics/covers/rates come through `curl` instead of Python's HTTPS stack, and freed memory goes back to the system after the island folds. On real hardware the saving depends on the graphics driver – `linuxmos-perf` shows the island's RAM.

Recording, chat and dictation cost nothing while idle: the chat tab is built the first time it opens (measured 59 MB RSS after start-up, +0.7 MB afterwards, idle CPU unchanged), and ffmpeg and curl only run while you record or ask.

---

## Requirements

- **Linux Mint 22.x Cinnamon** (based on Ubuntu 24.04), X11 session
- A user with `sudo` rights (the script asks for the password itself)
- Internet connection (apt packages and the WhiteSur themes from GitHub)
- Optional: **Timeshift** set up (for the snapshot before installing)

`install.sh` installs every package itself, e.g. `plank`, `conky-std`, `rofi`, `fonts-inter`, `sassc`; with `--island` also `python3-gi`, `gir1.2-gtk-3.0`, `gir1.2-wnck-3.0`, `gir1.2-xapp-1.0`, `xdotool`, `pulseaudio-utils`, `iso-codes`, `ffmpeg` (recording, dictation) and `libsecret-tools` (API key in the keyring).

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
linuxmos-perf                # measure the desktop's CPU load and the island's RAM
linuxmos-widgets restart     # restart the Conky widgets
linuxmos-island --tab todo   # open MosIsland on a tab
linuxmos-island --shot area  # screenshot: area | screen (monitor under the pointer)
linuxmos-island --ocr        # recognise the text in an area
linuxmos-island --qr         # read a QR code/barcode in an area
linuxmos-island --record area  # screen recording: area | screen; call again = stop
linuxmos-island --chat       # open the AI chat
linuxmos-island --voice      # start dictation, call again = recognise the text
linuxmos-island --set-key    # store the AI chat's API key in the keyring
linuxmos-island --set-city "Munich"
```

### Hotkeys

| Hotkey           | Action                                                      |
|------------------|-------------------------------------------------------------|
| `Super+Space`    | Open/close the Spotlight search                             |
| `Shift+→`        | In the search: switch mode (apps, run, windows, files)      |
| `Ctrl+Alt+I`     | Open/close MosIsland                                        |
| `Ctrl+Alt+V`     | Clipboard history (type to search, `Enter` pastes)          |
| `Ctrl+Alt+Space` | MosIsland's command bar: apps, files, calculator, units, currencies, web (`↑`/`↓`, `Enter`, `Ctrl+Enter`) |
| `Ctrl+Alt+S`     | Screenshot of an area (`Esc` or the hotkey again cancels)   |
| `Ctrl+Alt+Shift+S` | Screenshot of the monitor under the pointer               |
| `Ctrl+Alt+O`     | Recognise the text in an area (OCR) → clipboard             |
| `Ctrl+Alt+Q`     | Read a QR code/barcode in an area → clipboard               |
| `Ctrl+Alt+R`     | Start recording an area (again = stop and save)             |
| `Ctrl+Alt+Shift+R` | Record the monitor under the pointer                      |
| `Ctrl+Alt+A`     | Open the AI chat (with `ai_chat`)                           |
| `Ctrl+Alt+M`     | Dictation: record, press again = recognise and paste (with `ai_voice`) |
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
> Network access: weather via api.met.no and nominatim.openstreetmap.org (MosIsland) or wttr.in (Conky), lyrics via lrclib.net – only when you use the feature. The command bar gets exchange rates from api.frankfurter.dev (ECB rates, no account) – only when you type a currency conversion, at most every 12 hours; switch it off with `command_bar_currency`. The web search sends what you typed to the chosen search engine only when you press `Enter`. The VPN's country and IP come from ipinfo.io – only with `vpn_lookup` (off by default), once per VPN connection; ipinfo.io sees the VPN's exit IP. The clipboard history is stored unencrypted in `~/.local/share/linuxmos/island/clipboard.json`; copies from password managers are only skipped if they mark them as secret (KeePassXC and similar).

> [!IMPORTANT]
> AI chat and dictation are off until you switch them on in the tray menu under "AI". After that they send your question or your voice recording to the server in `ai_base_url` (empty: OpenAI) – only when you send something. The conversation stays in memory, the dictation recording (`~/.cache/linuxmos/island/recordings/dictation.wav`) is deleted as soon as the text is back. The API key lives in the keyring (`secret-tool`), never in `config.json`, and reaches `curl` through standard input only, so it is not in the process list either. A local server (Ollama, LM Studio on `localhost`) needs no key and sends nothing to the internet.

> [!IMPORTANT]
> During a screen recording the island stays invisible so it does not end up in the video, and notifications do not show as cards (they wait in the notification applet). The recording captures everything that is on the screen – including passwords you type there.

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
  "water_interval_min": 60
}
```

`language`: `auto` (system language: German for `de_*`, English otherwise), `de` or `en`. Switching it in the tray menu restarts MosIsland briefly (a running timer is lost).

`monitor`: `"primary"` (primary monitor, default), `"pointer"` (the monitor the mouse is on when you open the island via a hotkey or the tray – folded, it stays there until you open it somewhere else), a number from the left (`0` = leftmost, `1` = the one next to it …) or the connector name as in `xrandr --listmonitors` (`"HDMI-1"`, `"DP-2"`, `"eDP-1"`). If the chosen monitor is not connected, the island goes to the primary monitor and comes back when it is plugged in – the setting stays. The tray menu lists all connected monitors under "Monitor"; it stores the name, because the numbers can shift when monitors are replugged.

Screenshots: `screenshot_save` also keeps every shot as a PNG (otherwise clipboard only), `screenshot_dir` changes the folder (empty = `~/Pictures/LinuxMos`, localised like `~/Bilder/LinuxMos`), `screenshot_open_editor` opens the editor right after the shot. "Done" in the editor overwrites the shot with the marked-up version. All of it is also in the tray menu under "Screenshot".

Text & QR: `ocr_languages` are tesseract languages joined with `+` (more via `sudo apt install tesseract-ocr-fra` etc., list: `tesseract --list-langs`). By default the lines of a paragraph are joined and hyphens at line ends removed; `ocr_keep_linebreaks` keeps the text line by line. `qr_open_links` opens links from QR codes in the browser right away instead of showing an "Open" button. Both switches are also in the tray menu under "Text & QR". Recognition runs entirely locally, the image is deleted afterwards.

Notifications: `notifications_on_island` shows them as cards on the island (and turns Cinnamon's banners off for that), `notifications_dnd` is the island's "do not disturb", `notifications_exclude` a list of app names (as shown on the card) or desktop IDs (`firefox`, `org.telegram.desktop`) that never show as a card – e.g. `["Spotify", "Thunderbird"]`. All of it is also in the tray menu under "Notifications", which lists the recently seen apps to tick off. The island only listens in via a D-Bus monitor and stores none of it (only the app names for that list, in `~/.local/share/linuxmos/island/notifications.json`).

Live hints: `privacy_indicator` shows the orange (microphone) and green (camera) dot; the microphone comes from PipeWire/PulseAudio (`pactl subscribe`, level meters like pavucontrol don't count), the camera from inotify on `/dev/video*`. `vpn_status` reports VPN on/off (NetworkManager VPNs, WireGuard and the tun/wg interfaces of other VPN apps such as Mullvad), `vpn_lookup` adds country and IP from ipinfo.io (an outside request, hence off by default). `downloads_progress` watches the download folder (`downloads_dir`, empty = the XDG download folder, e.g. `~/Downloads`) for `.part` (Firefox) and `.crdownload` (Chromium/Chrome) files. All of it is also in the tray menu under "Live hints".

Command bar: `command_bar_engine` is the search engine (`duckduckgo`, `google`, `startpage`, `ecosia`, `bing`, `brave` or your own URL with `%s` for the query, e.g. `"https://en.wikipedia.org/w/index.php?search=%s"`). `command_bar_files` searches files: recently used ones and everything in the home folder up to 5 levels deep (no hidden folders, at most 20,000 entries); the list is built in a thread when you first type and dropped again 3 minutes after the last search. `command_bar_currency` converts currencies with the ECB rates (see network access above). Apps you start from the command bar move up (counter in `~/.local/share/linuxmos/island/command.json`). All of it is also in the tray menu under "Search".

Mascot: `mascot_style` is `eyes` (the default), `cat`, `robot` or `blob`; `mascot` switches it off altogether. Both in the tray menu under "Mascot".

Screen recording: `record_format` is `mp4` or `gif` (GIFs have at most 15 frames per second, 960 px width and no sound), `record_audio` `off`, `system` (what the speakers play) or `mic` (MP4 only), `record_fps` 1–60, `record_max_min` ends a recording after that many minutes (`0` = never), `record_dir` changes the folder (empty = `~/Videos/LinuxMos`). The picture comes from ffmpeg (`x11grab`) and needs X11. Format and sound also in the tray menu under "Screen recording".

AI: `ai_chat` shows the chat tab, `ai_voice` enables dictation, `ai_voice_autopaste` types the dictation into the previous window (otherwise a card with "Paste"). `ai_base_url` is the server's address up to `/v1` (empty = `https://api.openai.com/v1`, Ollama: `http://localhost:11434/v1`), `ai_model` the chat model (empty = `gpt-4o-mini`), `ai_stt_model` the model for dictation (empty = `whisper-1`; the server needs `/audio/transcriptions`). `ai_system_prompt` replaces the short default instruction, `ai_history` is the number of messages sent along, `ai_voice_language` a language code like `en` (empty = detect), `ai_voice_max_s` the longest dictation. Set address, models and key in the tray menu under "AI" → "Connection & API key …", or the key with `linuxmos-island --set-key`.

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
- **MosIsland needs ~60 MB RAM** (up to 1.9: ~115 MB) – almost entirely Python + GTK3 itself; Nusa (Rust) gets by with ~30 MB.
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
- **Files in the command bar** are only found in the home folder (up to 5 levels, no hidden folders) and in the recently used list – for the whole disk there is still the rofi search (`Super+Space`, "Files" mode). New files show up 10 minutes later at the latest.
- **The camera's app** is only found for your own user's programs; when the camera runs through PipeWire (e.g. Flatpak apps via the portal) it says "PipeWire" instead of the app. The camera can't be muted like the microphone – there is no system switch for it.
- **Several monitors:** in `"pointer"` mode the island only changes monitors on a hotkey – hovering opens it where it currently sits. If it sits too high on a second monitor (under the top bar), use `offset_y`.
- **Screen recording** is X11 only. "System sound" records PulseAudio/PipeWire's default output (`@DEFAULT_MONITOR@`); if you switch devices during a recording the sound stays on the old one. Another screenshot, OCR or QR hotkey during a recording ends it (and saves it). Long GIFs get big – use MP4 for those.
- **AI chat:** answers appear as plain text (no Markdown). Dictation needs a server with `/audio/transcriptions` (OpenAI, Groq, LocalAI, faster-whisper-server …); Ollama has none. If the keyring is locked, GNOME asks for its password on first access. The chat shows no images and remembers nothing beyond a restart.
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
- [x] Command bar in the island (`Ctrl+Alt+Space`): apps, files, calculator, units, currencies, web search
- [x] Several monitors: primary, a fixed one or the one with the mouse (`monitor`, tray menu), follows plugging in and out
- [x] Less RAM: 116 → 60 MB (no OpenGL probe, tabs built on demand, HTTP through `curl`, covers cached shrunk)
- [x] Screen recording as MP4 or GIF (`Ctrl+Alt+R`, `Ctrl+Alt+Shift+R`)
- [x] AI chat and dictation with your own API key in the keyring (`ai_chat`, `ai_voice`, `Ctrl+Alt+A`, `Ctrl+Alt+M`)
- [x] More mascots: cat, robot, blob (`mascot_style`)

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
- [FFmpeg](https://ffmpeg.org/) (LGPL/GPL) – screen recording and dictation
- [libsecret](https://gitlab.gnome.org/GNOME/libsecret) (LGPL-2.1) – API key in the keyring
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) (Apache-2.0) – text recognition
- [ZBar](https://github.com/mchehab/zbar) (LGPL-2.1) – QR codes and barcodes
- [MET Norway](https://www.met.no/en) (CC BY 4.0), [OpenStreetMap](https://www.openstreetmap.org/copyright) (ODbL), [LRCLIB](https://lrclib.net) – weather, geocoding, lyrics
- Ideas: [Island](https://github.com/exuupery/island) by exuupery and [Nusa](https://rama2555.github.io/nusa/) by Rama (both Windows, closed source) – no code or artwork reused
- Built with the help of Claude (Anthropic)

This project is not affiliated with Apple Inc. "macOS" is a trademark of Apple Inc.
