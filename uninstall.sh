#!/usr/bin/env bash
# =============================================================================
# LinuxMos – alles rückgängig machen.
#
#   ./uninstall.sh          Einstellungen wiederherstellen, Dock/Widgets entfernen
#   ./uninstall.sh --purge  zusätzlich Themes, Icons, Cursor, Wallpaper löschen
# =============================================================================
set -Euo pipefail

DATA_DIR="${XDG_DATA_HOME:-$HOME/.local/share}"
CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}"
STATE_DIR="${DATA_DIR}/linuxmos"
BACKUP_DIR="${STATE_DIR}/backup"
CACHE_DIR="${XDG_CACHE_HOME:-$HOME/.cache}/linuxmos"
BIN_DIR="$HOME/.local/bin"

PURGE=0
case "${1:-}" in
  --purge)   PURGE=1 ;;
  "")        ;;
  -h|--help) sed -n '3,6p' "$0"; exit 0 ;;
  *)         echo "Unbekannte Option: $1" >&2; exit 2 ;;
esac

step() { printf '\n\e[1m==> %s\e[0m\n' "$*"; }
ok()   { printf '    \e[32m✔\e[0m %s\n' "$*"; }
warn() { printf '    \e[33m!\e[0m %s\n' "$*" >&2; }

(( EUID != 0 )) || { echo "Bitte NICHT mit sudo starten." >&2; exit 1; }

# ---- Laufende Komponenten stoppen ------------------------------------------
step "Dock, Widgets und Spotlight stoppen"
[[ -x "${BIN_DIR}/linuxmos-widgets" ]] && "${BIN_DIR}/linuxmos-widgets" stop
pkill -u "$(id -u)" -x plank 2>/dev/null || true
rm -f "${CONFIG_DIR}/autostart/linuxmos-plank.desktop" \
      "${CONFIG_DIR}/autostart/linuxmos-widgets.desktop" \
      "${BIN_DIR}/linuxmos-widgets" "${BIN_DIR}/linuxmos-spotlight" "${BIN_DIR}/linuxmos-perf"
rm -rf "${CONFIG_DIR}/linuxmos"
ok "Gestoppt und Autostart entfernt"

# ---- Einstellungen wiederherstellen ----------------------------------------
step "Original-Einstellungen wiederherstellen"
if [[ -d "${BACKUP_DIR}" ]]; then
  for file in "${BACKUP_DIR}"/*.dconf; do
    [[ -f "${file}.path" ]] || continue
    path="$(<"${file}.path")"
    # Erst zurücksetzen, dann laden: so verschwinden auch neu gesetzte Keys
    dconf reset -f "${path}"
    dconf load "${path}" <"${file}"
    ok "${path}"
  done
  if [[ -f "${BACKUP_DIR}/spices.tar.gz" ]]; then
    tar -C "${CONFIG_DIR}/cinnamon" -xzf "${BACKUP_DIR}/spices.tar.gz"
    ok "Applet-Einstellungen (Menü, Uhr)"
  fi
  if [[ -f "${BACKUP_DIR}/.no-plank-config" ]]; then
    rm -rf "${CONFIG_DIR}/plank"
  fi
  # Backup archivieren, damit eine neue Installation wieder ein frisches anlegt
  mv "${BACKUP_DIR}" "${STATE_DIR}/backup.restored-$(date +%Y%m%d-%H%M%S)"
else
  warn "Kein Backup gefunden (${BACKUP_DIR}) – setze nur die LinuxMos-Teile zurück."
  gsettings reset org.cinnamon.desktop.keybindings.wm switch-input-source || true
fi

# ---- Optional: Themes löschen ----------------------------------------------
if (( PURGE )); then
  step "Themes, Icons, Cursor und Wallpaper löschen"
  if [[ -x "${CACHE_DIR}/WhiteSur-gtk-theme/install.sh" ]]; then
    ( cd "${CACHE_DIR}/WhiteSur-gtk-theme" && ./install.sh -r >/dev/null ) || warn "WhiteSur-Uninstaller meldete Fehler"
    ( cd "${CACHE_DIR}/WhiteSur-gtk-theme" && ./tweaks.sh -f -r >/dev/null 2>&1 ) || true
  else
    rm -rf "$HOME"/.themes/WhiteSur-*
    rm -rf "${CONFIG_DIR}/gtk-4.0/"{gtk.css,gtk-dark.css,gtk-Light.css,gtk-Dark.css,assets,windows-assets}
  fi
  rm -rf "$HOME"/.local/share/icons/WhiteSur{,-dark,-light,-cursors} \
         "$HOME/.icons/WhiteSur-cursors" \
         "${DATA_DIR}"/plank/themes/LinuxMos-* \
         "${DATA_DIR}/backgrounds/linuxmos" \
         "${CACHE_DIR}"
  ok "Gelöscht"
  echo
  echo "    Pakete bei Bedarf manuell entfernen:"
  echo "      sudo apt remove plank conky-std rofi fonts-inter"
fi

step "Fertig – einmal ab- und wieder anmelden."
