#!/usr/bin/env bash
# =============================================================================
# LinuxMos – macOS-Look für Linux Mint Cinnamon, leichtgewichtig.
#
# Windows-Video  ->  LinuxMos
#   Windhawk Themes / Buttons     -> WhiteSur GTK + Cinnamon + Window-Theme
#   Cursor / Icons                -> WhiteSur Cursors / WhiteSur Icons
#   Taskbar Styler + Animationen  -> Plank Dock (Zoom-Effekt) + Cinnamon Effects
#   Start/Notification Styler     -> WhiteSur Cinnamon-Theme
#   Rainmeter Top Bar / Widgets   -> Cinnamon Panel oben + Conky
#   Raycast                       -> rofi (Spotlight, Super+Space)
#   Island (Dynamic Island)       -> MosIsland (--island, Python/GTK)
#
# Usage: ./install.sh [OPTIONS]   (./install.sh --help)
#
# Kann auch per `source` geladen werden (update.sh nutzt die Funktionen),
# dann läuft nichts automatisch.
# =============================================================================
set -Eeuo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TWEAKS="${REPO_DIR}/lib/cinnamon_tweaks.py"

DATA_DIR="${XDG_DATA_HOME:-$HOME/.local/share}"
CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}"
STATE_DIR="${DATA_DIR}/linuxmos"
BACKUP_DIR="${STATE_DIR}/backup"
CACHE_DIR="${XDG_CACHE_HOME:-$HOME/.cache}/linuxmos"
BIN_DIR="$HOME/.local/bin"
APP_CONF_DIR="${CONFIG_DIR}/linuxmos"
AUTOSTART_DIR="${CONFIG_DIR}/autostart"
PLANK_DOCK="net.launchpad.plank.dock.settings:/net/launchpad/plank/docks/dock1/"

# dconf-Pfade, die gesichert und von uninstall.sh wiederhergestellt werden
DCONF_PATHS=(
  /org/cinnamon/
  /org/gnome/desktop/interface/
  /org/gnome/desktop/wm/preferences/
  /org/x/apps/portal/
  /net/launchpad/plank/
)

APT_PACKAGES=(
  git curl plank conky-std rofi fonts-inter
  # Build-Dependencies für das WhiteSur GTK-Theme
  sassc libglib2.0-dev-bin libxml2-utils
)
# Nur mit --island (das meiste davon ist auf Mint schon installiert)
ISLAND_PACKAGES=(
  python3-gi python3-gi-cairo gir1.2-gtk-3.0 gir1.2-wnck-3.0
  gir1.2-xapp-1.0 gir1.2-cinnamondesktop-3.0
  xdotool pulseaudio-utils libnotify-bin sound-theme-freedesktop
  # Screenshot-Tool (Ctrl+Alt+S)
  maim slop xclip
  # Text (Ctrl+Alt+O) und QR-Codes (Ctrl+Alt+Q) vom Bildschirm
  tesseract-ocr tesseract-ocr-deu tesseract-ocr-eng zbar-tools
  # Ländernamen für den VPN-Hinweis (auf Mint meist schon da)
  iso-codes
)

# ---- Defaults ---------------------------------------------------------------
VARIANT="dark"        # dark | light
EFFECTS="balanced"    # balanced | minimal
WEATHER_CITY=""
DO_WIDGETS=1
DO_SPOTLIGHT=1
DO_FIREFOX=0
DO_ISLAND=0
SNAPSHOT="ask"        # ask | yes | no
ASSUME_YES=0
PANEL_HEIGHT=28

# ---- Output helpers ---------------------------------------------------------
if [[ -t 1 ]]; then
  C_B=$'\e[1m'; C_G=$'\e[32m'; C_Y=$'\e[33m'; C_R=$'\e[31m'; C_0=$'\e[0m'
else
  C_B=""; C_G=""; C_Y=""; C_R=""; C_0=""
fi
step() { printf '\n%s==> %s%s\n' "${C_B}" "$*" "${C_0}"; }
info() { printf '    %s\n' "$*"; }
ok()   { printf '    %s✔%s %s\n' "${C_G}" "${C_0}" "$*"; }
warn() { printf '    %s!%s %s\n' "${C_Y}" "${C_0}" "$*" >&2; }
die()  { printf '%sFEHLER:%s %s\n' "${C_R}" "${C_0}" "$*" >&2; exit 1; }
trap 'die "Abbruch in Zeile ${LINENO}: ${BASH_COMMAND}"' ERR

confirm() {
  (( ASSUME_YES )) && return 0
  local reply
  read -r -p "    $1 [j/N] " reply
  [[ "${reply,,}" == j* || "${reply,,}" == y* ]]
}

# Setzt einen gsettings-Key nur, wenn Schema und Key existieren.
# So bricht das Script bei abweichenden Cinnamon-Versionen nicht ab.
gset() {
  if gsettings writable "$1" "$2" &>/dev/null; then
    gsettings set "$1" "$2" "$3" || warn "gsettings set $1 $2 $3 fehlgeschlagen"
  else
    warn "Key '$1 $2' existiert nicht – übersprungen"
  fi
}

usage() {
  cat <<EOF
LinuxMos – macOS-Look für Linux Mint Cinnamon

Usage: ./install.sh [OPTIONS]

  --light            Helles Design statt Dark Mode
  --minimal          Alle Animationen aus (Dock-Zoom, Fenster-Effekte)
  --weather CITY     Wetter im Widget anzeigen (z. B. --weather Berlin)
  --no-widgets       Keine Conky-Widgets (Uhr, System)
  --no-spotlight     Keine Spotlight-Suche (rofi)
  --firefox          Zusätzlich WhiteSur-Theme für Firefox installieren
  --island           MosIsland (Dynamic Island) installieren: Musik, Clipboard,
                     Ablage, Notiz/Timer, Wetter, Controls, Screenshots, Text/QR oben in der Mitte
  --snapshot         Vorher Timeshift-Snapshot erstellen (ohne Nachfrage)
  --no-snapshot      Keinen Timeshift-Snapshot erstellen
  -y, --yes          Alle Rückfragen mit "ja" beantworten
  -h, --help         Diese Hilfe

Rückgängig machen: ./uninstall.sh
EOF
}

# ---- Argumente --------------------------------------------------------------
parse_args() {
while (( $# )); do
  case "$1" in
    --light)        VARIANT="light" ;;
    --minimal)      EFFECTS="minimal" ;;
    --weather)      [[ -n "${2:-}" ]] || die "--weather braucht einen Ort"; WEATHER_CITY="$2"; shift
                    # Landet in einer Conky-Shell-Zeile -> nur harmlose Zeichen erlauben
                    [[ "${WEATHER_CITY}" =~ ^[[:alnum:][:space:],.-]+$ ]] || die "Ungültiger Ort: ${WEATHER_CITY}" ;;
    --no-widgets)   DO_WIDGETS=0 ;;
    --no-spotlight) DO_SPOTLIGHT=0 ;;
    --firefox)      DO_FIREFOX=1 ;;
    --island)       DO_ISLAND=1 ;;
    --snapshot)     SNAPSHOT="yes" ;;
    --no-snapshot)  SNAPSHOT="no" ;;
    -y|--yes)       ASSUME_YES=1 ;;
    -h|--help)      usage; exit 0 ;;
    *)              usage >&2; die "Unbekannte Option: $1" ;;
  esac
  shift
done
}

# Abgeleitete Namen je nach Variante
derive_names() {
if [[ "${VARIANT}" == "dark" ]]; then
  GTK_THEME="WhiteSur-Dark";  ICON_THEME="WhiteSur-dark";  PLANK_THEME="LinuxMos-Dark"
  WALLPAPER="WhiteSur-dark.jpg"; COLOR_SCHEME="prefer-dark"
  W_BG="1c1c1e"; W_FG="f5f5f7"; W_FG2="8e8e93"
  R_BG="#1e1e20e6"; R_FG="#f5f5f7"; R_FG2="#8e8e93"; R_BORDER="#ffffff22"
else
  GTK_THEME="WhiteSur-Light"; ICON_THEME="WhiteSur-light"; PLANK_THEME="LinuxMos-Light"
  WALLPAPER="WhiteSur-light.jpg"; COLOR_SCHEME="prefer-light"
  W_BG="f2f2f7"; W_FG="1c1c1e"; W_FG2="6e6e73"
  R_BG="#f5f5f7e6"; R_FG="#1c1c1e"; R_FG2="#6e6e73"; R_BORDER="#00000022"
fi
CURSOR_THEME="WhiteSur-cursors"
}

# =============================================================================
# 0. Vorabprüfungen
# =============================================================================
preflight() {
  step "Vorabprüfung"
  (( EUID != 0 )) || die "Bitte NICHT mit sudo starten – das Script fragt selbst nach dem Passwort."
  command -v apt-get >/dev/null || die "apt-get nicht gefunden – das Script ist für Linux Mint / Ubuntu."
  command -v gsettings >/dev/null || die "gsettings nicht gefunden."
  command -v python3 >/dev/null || die "python3 nicht gefunden."
  command -v dconf >/dev/null || die "dconf nicht gefunden (sudo apt install dconf-cli)."

  if [[ "${XDG_CURRENT_DESKTOP:-}" != *Cinnamon* ]]; then
    warn "Keine laufende Cinnamon-Session erkannt (XDG_CURRENT_DESKTOP='${XDG_CURRENT_DESKTOP:-}')."
    confirm "Trotzdem fortfahren?" || exit 1
  fi
  if [[ -r /etc/os-release ]]; then
    # In einer Subshell, damit os-release keine Script-Variablen (z. B. VARIANT) überschreibt
    # shellcheck disable=SC1091
    info "System: $(. /etc/os-release && echo "${PRETTY_NAME:-unbekannt}")"
  fi
  ok "Alles bereit"
}

# =============================================================================
# 1. Sicherung (Timeshift = das "Restore Point" aus dem Video)
# =============================================================================
snapshot() {
  step "Systemsicherung (Timeshift)"
  if ! command -v timeshift >/dev/null; then
    warn "Timeshift nicht installiert – übersprungen."
    return
  fi
  if [[ "${SNAPSHOT}" == "no" ]]; then
    info "Übersprungen (--no-snapshot)."
    return
  fi
  if [[ "${SNAPSHOT}" == "ask" ]] && ! confirm "Timeshift-Snapshot vor der Installation erstellen? (empfohlen)"; then
    info "Übersprungen."
    return
  fi
  if sudo timeshift --create --comments "Before LinuxMos" --scripted; then
    ok "Snapshot erstellt"
  else
    warn "Snapshot fehlgeschlagen (Timeshift eingerichtet?). Weiter ohne."
  fi
}

backup_settings() {
  step "Aktuelle Desktop-Einstellungen sichern"
  if [[ -d "${BACKUP_DIR}" ]]; then
    info "Backup existiert bereits (${BACKUP_DIR}) – Original bleibt erhalten."
    return
  fi
  mkdir -p "${BACKUP_DIR}"
  local path file
  for path in "${DCONF_PATHS[@]}"; do
    file="${BACKUP_DIR}/$(tr '/' '_' <<<"${path#/}").dconf"
    printf '%s\n' "${path}" >"${file}.path"
    dconf dump "${path}" >"${file}"
  done
  if [[ -d "${CONFIG_DIR}/cinnamon/spices" ]]; then
    tar -C "${CONFIG_DIR}/cinnamon" -czf "${BACKUP_DIR}/spices.tar.gz" spices
  fi
  [[ -d "${CONFIG_DIR}/plank" ]] || touch "${BACKUP_DIR}/.no-plank-config"
  ok "Gesichert nach ${BACKUP_DIR}"
}

# =============================================================================
# 2. Pakete
# =============================================================================
install_packages() {
  step "Pakete installieren (apt)"
  if (( DO_ISLAND )); then
    APT_PACKAGES+=("${ISLAND_PACKAGES[@]}")
  fi
  info "${APT_PACKAGES[*]}"
  sudo apt-get update -qq
  sudo apt-get install -y --no-install-recommends "${APT_PACKAGES[@]}"
  ok "Pakete installiert"
}

# Installiert nur Pakete, die noch fehlen (für update.sh: kein apt-Lauf, wenn nichts fehlt)
install_missing_packages() {
  local missing=() pkg
  for pkg in "$@"; do
    dpkg-query -W -f='${Status}' "${pkg}" 2>/dev/null | grep -q "install ok installed" || missing+=("${pkg}")
  done
  if (( ${#missing[@]} )); then
    info "Neue Abhängigkeiten: ${missing[*]}"
    sudo apt-get update -qq
    sudo apt-get install -y --no-install-recommends "${missing[@]}"
  fi
}

# Klont ein Repo flach in den Cache bzw. aktualisiert es.
fetch_repo() {
  local name="$1" url="$2" dir="${CACHE_DIR}/$1"
  shift 2
  if [[ -d "${dir}/.git" ]]; then
    git -C "${dir}" pull -q --ff-only || warn "Update von ${name} fehlgeschlagen – nutze vorhandene Version."
  else
    git clone -q --depth 1 "$@" "${url}" "${dir}"
  fi
}

# =============================================================================
# 3. Themes, Icons, Cursor, Wallpaper  (= Windhawk UXTheme + Resource Redirect)
# =============================================================================
install_themes() {
  step "WhiteSur-Themes laden und installieren"
  mkdir -p "${CACHE_DIR}"

  fetch_repo WhiteSur-gtk-theme  https://github.com/vinceliuice/WhiteSur-gtk-theme.git
  fetch_repo WhiteSur-icon-theme https://github.com/vinceliuice/WhiteSur-icon-theme.git
  fetch_repo WhiteSur-cursors    https://github.com/vinceliuice/WhiteSur-cursors.git
  # Wallpaper-Repo ist groß: nur den 2k-Ordner holen
  if [[ ! -d "${CACHE_DIR}/WhiteSur-wallpapers/.git" ]]; then
    fetch_repo WhiteSur-wallpapers https://github.com/vinceliuice/WhiteSur-wallpapers.git \
      --filter=blob:none --sparse
    git -C "${CACHE_DIR}/WhiteSur-wallpapers" sparse-checkout set 2k
  else
    fetch_repo WhiteSur-wallpapers https://github.com/vinceliuice/WhiteSur-wallpapers.git
  fi

  info "GTK/Cinnamon/Window-Theme (${GTK_THEME}) ..."
  # -o normal: nur die transparente Variante, -l: auch GTK4/libadwaita-Apps
  ( cd "${CACHE_DIR}/WhiteSur-gtk-theme" && ./install.sh -c "${VARIANT}" -o normal -l --round >/dev/null )
  ok "GTK-Theme"

  info "Icons (${ICON_THEME}) ..."
  ( cd "${CACHE_DIR}/WhiteSur-icon-theme" && ./install.sh >/dev/null )
  ok "Icons"

  info "Cursor ..."
  ( cd "${CACHE_DIR}/WhiteSur-cursors" && ./install.sh >/dev/null )
  # Fallback-Pfad für ältere X11-Apps
  mkdir -p "$HOME/.icons"
  # (WhiteSur installiert fest nach ~/.local/share/icons)
  ln -sfn "$HOME/.local/share/icons/${CURSOR_THEME}" "$HOME/.icons/${CURSOR_THEME}"
  ok "Cursor"

  info "Wallpaper ..."
  mkdir -p "${DATA_DIR}/backgrounds/linuxmos"
  cp -f "${CACHE_DIR}/WhiteSur-wallpapers/2k/"WhiteSur*.jpg "${DATA_DIR}/backgrounds/linuxmos/"
  ok "Wallpaper"

  info "Plank-Dock-Theme ..."
  local plank_src="$HOME/.themes/${GTK_THEME}/plank/dock.theme"
  [[ -f "${plank_src}" ]] || plank_src="${CACHE_DIR}/WhiteSur-gtk-theme/other/plank/theme-${VARIANT^}/dock.theme"
  mkdir -p "${DATA_DIR}/plank/themes/${PLANK_THEME}"
  cp -f "${plank_src}" "${DATA_DIR}/plank/themes/${PLANK_THEME}/dock.theme"
  ok "Plank-Theme"

  if (( DO_FIREFOX )); then
    info "Firefox-Theme ..."
    if ( cd "${CACHE_DIR}/WhiteSur-gtk-theme" && ./tweaks.sh -f >/dev/null ); then
      ok "Firefox-Theme (Firefox neu starten)"
    else
      warn "Firefox-Theme fehlgeschlagen – Firefox einmal starten und erneut versuchen."
    fi
  fi
}

apply_appearance() {
  step "Design anwenden"
  gset org.cinnamon.desktop.interface      gtk-theme    "${GTK_THEME}"
  gset org.cinnamon.desktop.interface      icon-theme   "${ICON_THEME}"
  gset org.cinnamon.desktop.interface      cursor-theme "${CURSOR_THEME}"
  gset org.cinnamon.desktop.interface      font-name    "Inter 10"
  gset org.cinnamon.desktop.wm.preferences theme        "${GTK_THEME}"
  gset org.cinnamon.desktop.wm.preferences titlebar-font "Inter Bold 10"
  gset org.cinnamon.theme                  name         "${GTK_THEME}"

  # Ampel-Buttons links wie bei macOS (Muffin + GTK-CSD-Apps)
  gset org.cinnamon.desktop.wm.preferences button-layout "close,minimize,maximize:"
  gset org.gnome.desktop.wm.preferences    button-layout "close,minimize,maximize:"

  # Dark/Light Mode auch für libadwaita- und Flatpak-Apps
  gset org.x.apps.portal                   color-scheme "${COLOR_SCHEME}"
  gset org.gnome.desktop.interface         color-scheme "${COLOR_SCHEME}"

  gset org.cinnamon.desktop.background picture-uri     "file://${DATA_DIR}/backgrounds/linuxmos/${WALLPAPER}"
  gset org.cinnamon.desktop.background picture-options "zoom"
  ok "Theme, Icons, Cursor, Schrift, Wallpaper gesetzt"
}

# =============================================================================
# 4. Top Bar (= Rainmeter Top Bar)
# =============================================================================
setup_top_bar() {
  step "Cinnamon-Panel zur macOS Top Bar umbauen"
  python3 "${TWEAKS}" panel-top "${PANEL_HEIGHT}"
  # Fensterliste fliegt raus – laufende Apps zeigt jetzt das Dock
  python3 "${TWEAKS}" drop-applets grouped-window-list@cinnamon.org window-list@cinnamon.org
  # Menü-Button: Logo aus dem WhiteSur-Icon-Theme, ohne Text
  python3 "${TWEAKS}" xlet-set menu@cinnamon.org menu-icon '"start-here-symbolic"' || true
  python3 "${TWEAKS}" xlet-set menu@cinnamon.org menu-label '""' || true
  # macOS-Uhrformat: "So. 25. Okt.  14:32"
  python3 "${TWEAKS}" xlet-set calendar@cinnamon.org use-custom-format 'true' || true
  python3 "${TWEAKS}" xlet-set calendar@cinnamon.org custom-format '"%a %e. %b  %H:%M"' || true
  ok "Panel oben, ${PANEL_HEIGHT}px, Fensterliste entfernt"
}

# =============================================================================
# 5. Dock (= Taskbar Styler + Dock Animation)
# =============================================================================
desktop_file() {
  local id="$1" dir
  for dir in /usr/share/applications /var/lib/flatpak/exports/share/applications \
             "${DATA_DIR}/applications" "${DATA_DIR}/flatpak/exports/share/applications"; do
    [[ -f "${dir}/${id}" ]] && { printf '%s\n' "${dir}/${id}"; return 0; }
  done
  return 1
}

setup_dock() {
  step "Plank-Dock einrichten"
  local launchers="${CONFIG_DIR}/plank/dock1/launchers"

  # Nur beim ersten Mal Standard-Apps anlegen, eigene Docks bleiben unangetastet
  if [[ ! -d "${launchers}" ]] || [[ -z "$(ls -A "${launchers}")" ]]; then
    mkdir -p "${launchers}"
    local items=() id path name
    for id in nemo.desktop firefox.desktop org.gnome.Terminal.desktop org.x.editor.desktop \
              mintinstall.desktop cinnamon-settings.desktop; do
      path="$(desktop_file "${id}")" || continue
      name="${id%.desktop}.dockitem"
      printf '[PlankDockItemPreferences]\nLauncher=file://%s\n' "${path}" >"${launchers}/${name}"
      items+=("'${name}'")
    done
    if (( ${#items[@]} )); then
      gset "${PLANK_DOCK}" dock-items "[$(IFS=,; echo "${items[*]}")]"
    fi
  fi

  gset "${PLANK_DOCK}" theme          "${PLANK_THEME}"
  gset "${PLANK_DOCK}" position       "bottom"
  gset "${PLANK_DOCK}" alignment      "center"
  gset "${PLANK_DOCK}" icon-size      48
  gset "${PLANK_DOCK}" hide-mode      "intelligent"
  gset "${PLANK_DOCK}" show-dock-item false
  if [[ "${EFFECTS}" == "minimal" ]]; then
    gset "${PLANK_DOCK}" zoom-enabled false
  else
    # Die macOS-Vergrößerung – kostet nur CPU, solange die Maus über dem Dock ist
    gset "${PLANK_DOCK}" zoom-enabled true
    gset "${PLANK_DOCK}" zoom-percent 150
  fi

  mkdir -p "${AUTOSTART_DIR}"
  cat >"${AUTOSTART_DIR}/linuxmos-plank.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Plank (LinuxMos)
Comment=macOS-style dock
Exec=plank
X-GNOME-Autostart-enabled=true
EOF

  if ! pgrep -u "$(id -u)" -x plank >/dev/null; then
    setsid plank >/dev/null 2>&1 < /dev/null &
  fi
  ok "Dock läuft und startet automatisch"
}

# =============================================================================
# 6. Animationen (= Dock Animation + macOS Minimize Animation)
# =============================================================================
setup_effects() {
  step "Fenster-Animationen (${EFFECTS})"
  gset org.cinnamon startup-animation false
  if [[ "${EFFECTS}" == "minimal" ]]; then
    gset org.cinnamon desktop-effects-close       "none"
    gset org.cinnamon desktop-effects-map         "none"
    gset org.cinnamon desktop-effects-minimize    "none"
    gset org.cinnamon desktop-effects-change-size false
    gset org.cinnamon desktop-effects-on-menus    false
    gset org.cinnamon desktop-effects-on-dialogs  false
    gset org.cinnamon desktop-effects-workspace   false
  else
    # "traditional" schrumpft das Fenster Richtung Dock – das nächste an "Genie",
    # ohne Compiz/Blur. Speed 2 = schnell, also keine "overdramatischen" Animationen.
    gset org.cinnamon desktop-effects-close       "traditional"
    gset org.cinnamon desktop-effects-map         "traditional"
    gset org.cinnamon desktop-effects-minimize    "traditional"
    gset org.cinnamon desktop-effects-change-size true
    gset org.cinnamon window-effect-speed         2
  fi
  ok "Effekte gesetzt"
}

# =============================================================================
# 7. Widgets (= Rainmeter: Uhr, System, Wetter)
# =============================================================================
setup_widgets() {
  (( DO_WIDGETS )) || return 0
  step "Desktop-Widgets (Conky)"
  local conky_dir="${APP_CONF_DIR}/conky" weather=""
  mkdir -p "${conky_dir}" "${BIN_DIR}"

  if [[ -n "${WEATHER_CITY}" ]]; then
    local city="${WEATHER_CITY// /+}"
    # Nur alle 30 min ein curl-Aufruf (ohne Emoji – Xft kann keine Farb-Emojis)
    weather=$'\n\n${color1}${font Inter:style=Bold:size=9}WETTER${font}${color}\n'
    weather+="\${voffset 4}\${execi 1800 curl -fsm 5 'https://wttr.in/${city}?format=%t+%C&lang=de' || echo 'nicht verfügbar'}"
  fi

  cp -f "${REPO_DIR}/config/conky/clock.conf" "${conky_dir}/clock.conf"
  python3 "${TWEAKS}" render "${REPO_DIR}/config/conky/stats.conf.in" "${conky_dir}/stats.conf" \
    "BG=${W_BG}" "FG=${W_FG}" "FG2=${W_FG2}" "ACCENT=0a84ff" "WEATHER=${weather}"

  install -m 755 "${REPO_DIR}/bin/linuxmos-widgets" "${BIN_DIR}/linuxmos-widgets"
  cat >"${AUTOSTART_DIR}/linuxmos-widgets.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=LinuxMos Widgets
Comment=Conky clock and system widgets
Exec=${BIN_DIR}/linuxmos-widgets start
X-GNOME-Autostart-enabled=true
X-GNOME-Autostart-Delay=4
EOF

  "${BIN_DIR}/linuxmos-widgets" restart
  ok "Uhr + System-Widget laufen (Update alle 5 s / 3 s)"
}

# =============================================================================
# 8. Spotlight (= Raycast)
# =============================================================================
setup_spotlight() {
  (( DO_SPOTLIGHT )) || return 0
  step "Spotlight-Suche (rofi, Super+Space)"
  mkdir -p "${APP_CONF_DIR}/rofi" "${BIN_DIR}"
  python3 "${TWEAKS}" render "${REPO_DIR}/config/rofi/spotlight.rasi.in" "${APP_CONF_DIR}/rofi/spotlight.rasi" \
    "ICONS=${ICON_THEME}" "BG=${R_BG}" "FG=${R_FG}" "FG2=${R_FG2}" "BORDER=${R_BORDER}"
  install -m 755 "${REPO_DIR}/bin/linuxmos-spotlight" "${BIN_DIR}/linuxmos-spotlight"

  # Super+Space ist in Cinnamon für "Tastaturlayout wechseln" belegt -> freigeben
  python3 "${TWEAKS}" strip-binding org.cinnamon.desktop.keybindings.wm switch-input-source "<Super>space"
  python3 "${TWEAKS}" add-keybinding "Spotlight (LinuxMos)" "${BIN_DIR}/linuxmos-spotlight" "<Super>space"
  ok "Super+Space öffnet die Suche (Layout-Wechsel weiter über Shift+Super+Space)"
}

# =============================================================================
# 9. MosIsland (= Dynamic Island, inspiriert von exuupery/island)
# =============================================================================
setup_island() {
  (( DO_ISLAND )) || return 0
  step "MosIsland (Dynamic Island)"
  local app_dir="${STATE_DIR}/island-app"

  # Laufende Insel beenden, damit die neue Version startet
  if [[ -x "${BIN_DIR}/linuxmos-island" ]]; then
    "${BIN_DIR}/linuxmos-island" --quit
    sleep 1
  fi

  rm -rf "${app_dir}"
  mkdir -p "${app_dir}" "${BIN_DIR}" "${AUTOSTART_DIR}" "${DATA_DIR}/applications"
  cp -r "${REPO_DIR}/island" "${app_dir}/"
  find "${app_dir}" -name __pycache__ -prune -exec rm -rf {} +
  install -m 755 "${REPO_DIR}/bin/linuxmos-island" "${BIN_DIR}/linuxmos-island"

  if [[ -n "${WEATHER_CITY}" ]]; then
    "${BIN_DIR}/linuxmos-island" --set-city "${WEATHER_CITY}" >/dev/null
  fi

  cat >"${AUTOSTART_DIR}/linuxmos-island.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=MosIsland (LinuxMos)
Comment=Dynamic Island for Cinnamon
Exec=${BIN_DIR}/linuxmos-island
X-GNOME-Autostart-enabled=true
X-GNOME-Autostart-Delay=3
EOF
  cat >"${DATA_DIR}/applications/linuxmos-island.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=MosIsland
Comment=Dynamic Island: Musik, Zwischenablage, Ablage, Notiz, Wetter
Exec=${BIN_DIR}/linuxmos-island --toggle
Icon=view-app-grid-symbolic
Categories=Utility;
EOF

  # MosIsland zeigt Lautstärke & Helligkeit selbst an -> Cinnamons eigenes OSD aus
  # (im Tray-Menü umschaltbar; uninstall.sh stellt den Originalwert wieder her).
  # Hat der Nutzer die MosIsland-Anzeige im Tray abgeschaltet, bleibt das so.
  if ! grep -qs '"osd": false' "${CONFIG_DIR}/linuxmos/island/config.json"; then
    # Je nach Cinnamon-Version Boolean oder Text ("small|medium|large|disabled")
    case "$(gsettings range org.cinnamon show-media-keys-osd 2>/dev/null | head -1)" in
      "type b") gset org.cinnamon show-media-keys-osd false ;;
      "type s"|enum*) gset org.cinnamon show-media-keys-osd disabled ;;
    esac
  fi

  python3 "${TWEAKS}" add-keybinding "MosIsland (LinuxMos)" "${BIN_DIR}/linuxmos-island --toggle" "<Primary><Alt>i"
  python3 "${TWEAKS}" add-keybinding "MosIsland Zwischenablage (LinuxMos)" \
    "${BIN_DIR}/linuxmos-island --tab clipboard" "<Primary><Alt>v"
  python3 "${TWEAKS}" add-keybinding "MosIsland Screenshot Bereich (LinuxMos)" \
    "${BIN_DIR}/linuxmos-island --shot area" "<Primary><Alt>s"
  python3 "${TWEAKS}" add-keybinding "MosIsland Screenshot Bildschirm (LinuxMos)" \
    "${BIN_DIR}/linuxmos-island --shot screen" "<Primary><Alt><Shift>s"
  python3 "${TWEAKS}" add-keybinding "MosIsland Text erkennen (LinuxMos)" \
    "${BIN_DIR}/linuxmos-island --ocr" "<Primary><Alt>o"
  python3 "${TWEAKS}" add-keybinding "MosIsland QR-Code lesen (LinuxMos)" \
    "${BIN_DIR}/linuxmos-island --qr" "<Primary><Alt>q"

  setsid "${BIN_DIR}/linuxmos-island" >/dev/null 2>&1 < /dev/null &
  ok "MosIsland läuft (Ctrl+Alt+I öffnen, Ctrl+Alt+V Zwischenablage, Ctrl+Alt+S Screenshot, Ctrl+Alt+O Text, Tray-Icon für Einstellungen)"
}

install_tools() {
  mkdir -p "${BIN_DIR}"
  install -m 755 "${REPO_DIR}/bin/linuxmos-perf" "${BIN_DIR}/linuxmos-perf"
}

# Merkt sich die gewählten Optionen, damit update.sh sie wiederverwenden kann
save_install_config() {
  mkdir -p "${STATE_DIR}"
  {
    echo "# LinuxMos – Optionen der letzten Installation (von install.sh geschrieben)"
    printf 'VARIANT=%q\nEFFECTS=%q\nWEATHER_CITY=%q\n' "${VARIANT}" "${EFFECTS}" "${WEATHER_CITY}"
    printf 'DO_WIDGETS=%q\nDO_SPOTLIGHT=%q\nDO_FIREFOX=%q\nDO_ISLAND=%q\n' \
      "${DO_WIDGETS}" "${DO_SPOTLIGHT}" "${DO_FIREFOX}" "${DO_ISLAND}"
  } >"${STATE_DIR}/install.conf"
}

summary() {
  step "Fertig 🎉"
  cat <<EOF
    Design:      ${GTK_THEME} · ${ICON_THEME} · ${CURSOR_THEME}
    Top Bar:     Cinnamon-Panel oben (${PANEL_HEIGHT}px)
    Dock:        Plank (${PLANK_THEME}), Zoom $( [[ "${EFFECTS}" == minimal ]] && echo aus || echo an )
    Widgets:     $( (( DO_WIDGETS )) && echo "Conky (Uhr + System${WEATHER_CITY:+ + Wetter})" || echo "–" )
    Spotlight:   $( (( DO_SPOTLIGHT )) && echo "Super+Space" || echo "–" )
    MosIsland:   $( (( DO_ISLAND )) && echo "oben mittig · Ctrl+Alt+I · Ctrl+Alt+V · Ctrl+Alt+S · Ctrl+Alt+O" || echo "– (mit --island)" )

    Tipps:
      • Einmal ab- und wieder anmelden, damit wirklich alle Apps das Theme nutzen.
      • CPU-Last prüfen:     linuxmos-perf
      • Widgets neu starten: linuxmos-widgets restart
      • Aktualisieren:       ./update.sh
      • Alles zurück:        ./uninstall.sh
EOF
}

main() {
  preflight
  snapshot
  backup_settings
  install_packages
  install_themes
  apply_appearance
  setup_top_bar
  setup_dock
  setup_effects
  setup_widgets
  setup_spotlight
  setup_island
  install_tools
  save_install_config
  summary
}

# Nur ausführen, wenn direkt gestartet (nicht per `source` aus update.sh)
if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  parse_args "$@"
  derive_names
  main
fi
