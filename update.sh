#!/usr/bin/env bash
# =============================================================================
# LinuxMos – aktualisieren.
#
#   ./update.sh               LinuxMos (git pull), Themes, Island & Tools updaten.
#                             Deine Einstellungen (Panel, Dock, Widget-Positionen,
#                             Island-Daten) bleiben unangetastet.
#   ./update.sh --check       Nur prüfen, ob es eine neue Version gibt
#   ./update.sh --no-themes   WhiteSur-Themes nicht neu laden (schneller)
#   ./update.sh --full        Zusätzlich alle Design-Einstellungen neu anwenden
#                             (wie bei der Installation, mit deinen damaligen Optionen)
# =============================================================================
# Alles steckt in main(): Bash liest die Funktion komplett ein, bevor sie läuft.
# So stört es nicht, wenn `git pull` diese Datei während des Updates ersetzt.

main() {
  set -Eeuo pipefail
  local repo_dir
  repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  local orig_args=("$@") full=0 themes=1 check=0 pulled=0

  while (( $# )); do
    case "$1" in
      --full)      full=1 ;;
      --no-themes) themes=0 ;;
      --check)     check=1 ;;
      --pulled)    pulled=1 ;;  # intern: nach dem Selbst-Update neu gestartet
      -h|--help)   sed -n '3,11p' "$0"; return 0 ;;
      *)           echo "Unbekannte Option: $1 (siehe --help)" >&2; return 2 ;;
    esac
    shift
  done

  # Funktionen und Pfade aus install.sh laden (führt nichts aus)
  # shellcheck source=install.sh
  source "${repo_dir}/install.sh"

  (( EUID != 0 )) || die "Bitte NICHT mit sudo starten – das Script fragt selbst nach dem Passwort."

  # ---- 1. LinuxMos selbst ------------------------------------------------------
  if (( ! pulled )); then
    step "LinuxMos aktualisieren"
    if [[ ! -d "${repo_dir}/.git" ]]; then
      warn "Kein Git-Repo (ZIP-Download?) – lade die neue Version manuell herunter."
    elif [[ -n "$(git -C "${repo_dir}" status --porcelain --untracked-files=no 2>/dev/null)" ]]; then
      warn "Lokale Änderungen im Repo – git pull übersprungen (git stash, dann erneut)."
    else
      local old new behind
      if ! old="$(git -C "${repo_dir}" rev-parse HEAD 2>/dev/null)"; then
        warn "git kann das Repo nicht lesen (gehört es einem anderen Benutzer?) – git pull übersprungen."
        old=""
      fi
    fi
    if [[ -n "${old:-}" ]]; then
      git -C "${repo_dir}" fetch -q || warn "git fetch fehlgeschlagen (offline?)"
      behind="$(git -C "${repo_dir}" rev-list --count 'HEAD..@{u}' 2>/dev/null || echo 0)"
      if (( check )); then
        if (( behind > 0 )); then
          info "${behind} neue Änderung(en) verfügbar:"
          git -C "${repo_dir}" log --oneline 'HEAD..@{u}' | sed 's/^/      /'
          info "Installieren mit: ./update.sh"
        else
          ok "LinuxMos ist aktuell ($(git -C "${repo_dir}" log -1 --format='%h, %cd' --date=short))"
        fi
        return 0
      fi
      if (( behind > 0 )) && git -C "${repo_dir}" pull -q --ff-only; then
        new="$(git -C "${repo_dir}" rev-parse HEAD)"
        ok "Aktualisiert: ${old:0:7} → ${new:0:7}"
        git -C "${repo_dir}" log --oneline "${old}..${new}" | sed 's/^/      /'
        # Mit der neuen Version dieses Scripts weitermachen
        exec "${repo_dir}/update.sh" --pulled "${orig_args[@]}"
      fi
      ok "Schon die neueste Version ($(git -C "${repo_dir}" log -1 --format='%h, %cd' --date=short))"
    fi
    (( check )) && return 0
  fi

  # ---- 2. Optionen der Installation laden -----------------------------------------
  if [[ ! -f "${STATE_DIR}/install.conf" ]]; then
    die "Keine LinuxMos-Installation gefunden – zuerst ./install.sh ausführen."
  fi
  # shellcheck disable=SC1091
  source "${STATE_DIR}/install.conf"
  derive_names
  # Den Wetter-Ort hat der Nutzer evtl. seitdem in der Island geändert -> nicht überschreiben
  WEATHER_CITY=""

  # ---- 3. Neue Abhängigkeiten ---------------------------------------------------------
  step "Abhängigkeiten prüfen"
  local packages=("${APT_PACKAGES[@]}")
  (( DO_ISLAND )) && packages+=("${ISLAND_PACKAGES[@]}")
  install_missing_packages "${packages[@]}"
  ok "Alles da"

  # ---- 4. Themes ------------------------------------------------------------------------
  if (( themes )); then
    install_themes
  else
    info "Themes übersprungen (--no-themes)"
  fi

  # ---- 5. Programme (ohne deine Einstellungen anzufassen) -----------------------------
  step "LinuxMos-Programme aktualisieren"
  install_tools
  if (( DO_WIDGETS )); then
    install -m 755 "${REPO_DIR}/bin/linuxmos-widgets" "${BIN_DIR}/linuxmos-widgets"
    "${BIN_DIR}/linuxmos-widgets" restart
  fi
  if (( DO_SPOTLIGHT )); then
    install -m 755 "${REPO_DIR}/bin/linuxmos-spotlight" "${BIN_DIR}/linuxmos-spotlight"
  fi
  ok "Tools aktualisiert"
  setup_island

  # ---- 6. Optional: Design komplett neu anwenden -----------------------------------------
  if (( full )); then
    backup_settings   # legt nur ein Backup an, falls noch keins existiert
    apply_appearance
    setup_top_bar
    setup_dock
    setup_effects
    setup_widgets
    setup_spotlight
  fi
  save_install_config

  step "Update fertig 🎉"
  if [[ -d "${REPO_DIR}/.git" ]]; then
    info "Version: $(git -C "${REPO_DIR}" log -1 --format='%h, %cd' --date=short)"
  fi
  (( full )) || info "Design-Einstellungen unverändert – mit --full neu anwenden."
}

main "$@"
exit $?
