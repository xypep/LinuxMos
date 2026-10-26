# Tests auf echtem Linux Mint

Diese Tests sind noch offen. Sie gehen nur auf einem echten Linux Mint 22 mit Cinnamon 6 (X11), nicht im Container.
Im Container getestet ist alles mit Xvfb, einem eigenen Session-Bus und einem nachgebauten Benachrichtigungs-Dienst.

Abhaken, was klappt. Was nicht klappt: Nummer + was passiert ist notieren (unten unter „Ergebnisse“).

---

## Vorbereitung

```bash
cd ~/LinuxMos
git fetch && git checkout claude/affectionate-feynman-573ubj && git pull
./update.sh
linuxmos-island --version          # erwartet: MosIsland 1.11.0
```

- [ ] **V1** `update.sh` läuft ohne Fehler durch, die Insel startet neu
- [ ] **V2** Deine bisherigen Einstellungen (Wetter-Ort, Tray-Schalter, Clipboard-Verlauf) sind noch da

---

## Paket 5 – Benachrichtigungen als Karte

### A. Grundfunktion

```bash
notify-send -a "Test" "Hallo" "Das ist eine Testnachricht"
```

- [ ] **A1** Oben auf der Insel erscheint eine Karte mit Titel „Hallo“, Text und „Test“ rechts oben
- [ ] **A2** Cinnamon zeigt **kein** eigenes Popup (Banner)
- [ ] **A3** Die Meldung steht trotzdem im Benachrichtigungs-Applet in der Top Bar
- [ ] **A4** Die Karte verschwindet nach ~7 s von selbst
- [ ] **A5** Solange die Maus auf der Karte liegt, bleibt sie; nach dem Wegfahren verschwindet sie nach ~3 s
- [ ] **A6** Über der Karte klappt die Insel **nicht** in die Tabs auf
- [ ] **A7** Prüfen: `gsettings get org.cinnamon.desktop.notifications display-notifications` → `false`

### B. Inhalt der Karte

```bash
# Markup im Text wird entfernt
notify-send -a "Test" "Markup" "Das ist <b>fett</b> &amp; <i>kursiv</i>"

# Langer Text: höchstens 4 Zeilen, dann „…“
notify-send -a "Test" "Lang" "$(printf 'Ein ziemlich langer Satz für die Karte. %.0s' {1..10})"

# Nur Titel, kein Text
notify-send -a "Test" "Nur ein Titel"

# Mit Bild (neuester Screenshot aus Ctrl+Alt+S)
notify-send -a "Test" -h string:image-path:"$(ls -t "$(xdg-user-dir PICTURES)"/LinuxMos/*.png | head -1)" "Mit Bild" "Rechts vom Bild steht der Text"

# App-Icon über die Desktop-Datei
notify-send -a "Firefox" -h string:desktop-entry:firefox "Firefox-Icon" "Links oben sollte das Firefox-Logo sein"
```

- [ ] **B1** Markup: „Das ist fett & kursiv“ ohne `<b>` und ohne `&amp;`
- [ ] **B2** Langer Text: maximal 4 Zeilen, die Karte wächst nicht über die normale Kartengröße
- [ ] **B3** Nur Titel: Karte ist klein und hat keinen leeren Kasten
- [ ] **B4** Bild: abgerundetes Bild links neben dem Text
- [ ] **B5** Firefox-Logo als Icon links oben
- [ ] **B6** Kurze Meldungen ergeben eine niedrige Karte, lange eine höhere (kein leerer Platz unten)

### C. Mehrere Meldungen, Updates, Schließen

```bash
# Drei schnell hintereinander -> die neueste bleibt, Zähler „+2“
notify-send -a "Chat" "Ben" "Eins"; notify-send -a "Chat" "Lea" "Zwei"; notify-send -a "Chat" "Anna" "Drei"

# Update derselben Meldung (kein Zähler)
ID=$(notify-send -p -a "Download" "Download" "10 %"); sleep 2; notify-send -r "$ID" -a "Download" "Download" "80 %"

# Die App zieht die Meldung zurück
ID=$(notify-send -p -a "Test" "Wird gleich zurückgezogen" "…"); sleep 2
gdbus call --session --dest org.freedesktop.Notifications --object-path /org/freedesktop/Notifications \
  --method org.freedesktop.Notifications.CloseNotification "$ID"

# Kritisch: bleibt stehen
notify-send -u critical -a "Akku" "Akku fast leer" "Noch 5 %"
```

- [ ] **C1** Bei drei Meldungen zeigt die Karte „Anna / Drei“ und rechts oben „Chat · +2“
- [ ] **C2** Nach dem Schließen (✕) fängt der Zähler bei der nächsten Meldung wieder bei 0 an
- [ ] **C3** Download: Text wechselt von „10 %“ auf „80 %“, **ohne** „+1“
- [ ] **C4** CloseNotification: Karte verschwindet sofort
- [ ] **C5** Kritische Meldung bleibt stehen, bis ✕ gedrückt wird (auch nach Maus drüber und weg)

### D. Klick auf die Karte

- [ ] **D1** Firefox offen, aber ein anderes Fenster vorne. Dann:
  `notify-send -a "Firefox" -h string:desktop-entry:firefox "Klick mich" "Holt Firefox nach vorne"` → Klick auf die Karte → Firefox kommt nach vorne, Karte ist weg
- [ ] **D2** Wie D1, aber Firefox auf **Arbeitsfläche 2**, du bist auf Arbeitsfläche 1 → Klick wechselt zu Arbeitsfläche 2 und aktiviert Firefox
- [ ] **D3** Wie D1, aber Firefox **minimiert** → Firefox wird wiederhergestellt
- [ ] **D4** Firefox geschlossen → Klick startet Firefox
- [ ] **D5** Klick auf den Titel (Kopfzeile) wirkt genauso wie Klick auf den Text
- [ ] **D6** Klick auf ✕ schließt nur die Karte, öffnet **nichts**
- [ ] **D7** Mauszeiger über der Karte ist eine Hand

### E. Echte Apps

Nur die Apps testen, die du installiert hast:

- [ ] **E1** Thunderbird: neue Mail → Karte mit Absender/Betreff, Klick holt Thunderbird nach vorne
- [ ] **E2** Telegram / Signal / Discord: Nachricht → Karte mit **Avatar**, Klick holt die App nach vorne
- [ ] **E3** Firefox-Webbenachrichtigung (z. B. WhatsApp Web, Mail im Browser) → Karte, Klick holt Firefox nach vorne
- [ ] **E4** Spotify (falls es Song-Wechsel meldet) → Karte mit Cover
- [ ] **E5** Nachricht in der App lesen, solange die Karte noch steht → Karte verschwindet (wenn die App die Meldung zurückzieht, z. B. Telegram)

### F. App ausblenden

- [ ] **F1** `notify-send -a "Spam" "Werbung" "Kauf jetzt"` → auf 🔕 in der Karte klicken → kurzer Hinweis „Spam ausgeblendet · Tray → Benachrichtigungen“
- [ ] **F2** Die gleiche Meldung nochmal schicken → **keine** Karte (steht aber im Applet)
- [ ] **F3** Tray → „Benachrichtigungen“: „Spam“ ist abgehakt, darüber stehen die anderen zuletzt gesehenen Apps
- [ ] **F4** Haken bei „Spam“ entfernen → nächste Spam-Meldung kommt wieder als Karte
- [ ] **F5** In `~/.config/linuxmos/island/config.json` steht `"notifications_exclude": [...]` passend zum Tray

### G. Nicht stören

- [ ] **G1** Steuerung-Tab → „Nicht stören“ an → `notify-send -a Test "DnD" "sollte nicht kommen"` → **keine** Karte, **kein** Banner, steht im Applet
- [ ] **G2** Bei „Nicht stören“: `notify-send -u critical -a Test "Kritisch" "kommt trotzdem"` → Karte erscheint
- [ ] **G3** Tray → „Benachrichtigungen“ → „Nicht stören“ zeigt denselben Zustand wie der Steuerung-Tab
- [ ] **G4** „Nicht stören“ wieder aus → Karten kommen wieder
- [ ] **G5** Systemeinstellungen → Benachrichtigungen → „Benachrichtigungen aktivieren“ einschalten, während die Insel läuft → „Nicht stören“ der Insel geht aus, Cinnamon zeigt trotzdem **keine** Banner (der Schalter springt zurück)

### H. Karten aus / Insel beenden

- [ ] **H1** Tray → „Benachrichtigungen“ → „Auf der Insel anzeigen“ aus → `notify-send -a Test "Aus" "Cinnamon-Banner"` → **Cinnamon-Popup** erscheint, keine Karte
- [ ] **H2** Bei Karten aus schaltet „Nicht stören“ (Steuerung-Tab) Cinnamons eigenes „Nicht stören“
- [ ] **H3** Wieder einschalten → Karten kommen, Cinnamon-Banner sind wieder aus
- [ ] **H4** Tray → „Beenden“ → `notify-send -a Test "Insel aus" "Cinnamon-Banner"` → Cinnamon-Popup erscheint
- [ ] **H5** `linuxmos-island &` → Karten sind wieder da, keine Banner
- [ ] **H6** Sprache umschalten (Tray → Sprache / Language) → Insel startet neu, Karten funktionieren danach, keine Banner

### I. Absturz und Ab-/Anmelden

- [ ] **I1** `pkill -9 -x linuxmos-island` → Banner bleiben aus (erwartet, steht so in der README) → `linuxmos-island &` → alles wieder normal
- [ ] **I2** Nach I1 ohne Neustart der Insel: `gsettings set org.cinnamon.desktop.notifications display-notifications true` → Cinnamon-Banner sind wieder da
- [ ] **I3** Abmelden und wieder anmelden → Insel startet automatisch, Karten funktionieren, keine doppelten Popups
- [ ] **I4** Neustart des Rechners → wie I3

### J. Sonderfälle

- [ ] **J1** Vollbild-Video (YouTube im Vollbild) + `notify-send -a Test "Vollbild" "…"` → keine Karte über dem Video, Meldung steht im Applet
- [ ] **J2** Während einer Screenshot-Auswahl (`Ctrl+Alt+S`, Rahmen noch nicht gezogen) kommt eine Meldung → die Auswahl wird nicht gestört
- [ ] **J3** OCR-Karte (`Ctrl+Alt+O`) ist sichtbar, dann kommt eine Meldung → die OCR-Karte bleibt stehen
- [ ] **J4** Insel aufgeklappt (Maus drauf), dann kommt eine Meldung → beim Zuklappen erscheint die Karte (falls sie noch nicht abgelaufen ist)
- [ ] **J5** Timer/Pomodoro läuft ab → nur die Live-Aktivität der Insel, **keine** zusätzliche Karte „MosIsland“
- [ ] **J6** 20 Meldungen in Folge: `for i in $(seq 20); do notify-send -a Flut "Nr. $i" "Test"; done` → Insel bleibt flüssig, zeigt am Ende „Nr. 20“ mit „+19“

### K. Englische Oberfläche

- [ ] **K1** Tray → Sprache / Language → English → Untermenü heißt „Notifications“, Einträge „Show on the island“, „Do not disturb“, „Hide on the island:“
- [ ] **K2** Tooltip von 🔕 auf der Karte: „Hide notifications from …“
- [ ] **K3** Danach wieder auf Deutsch bzw. Automatisch stellen

### L. Leistung (Definition of Done)

```bash
# Insel 1 Minute in Ruhe lassen, keine Musik, dann:
linuxmos-perf 20
grep VmRSS /proc/$(pgrep -x linuxmos-island)/status
```

- [ ] **L1** `linuxmos-island` im Leerlauf ≤ 0,2 % CPU (bisher ~0,1 %)
- [ ] **L2** RAM ungefähr wie vorher (~115 MB)
- [ ] **L3** Nach J6 (20 Meldungen) fällt die CPU wieder auf den Leerlauf-Wert

### M. Uninstall (optional, nur wenn du sowieso neu installieren willst)

- [ ] **M1** `./uninstall.sh` → danach erscheinen Cinnamon-Banner wieder normal
- [ ] **M2** `./install.sh --island` → Karten funktionieren wieder

## Paket 6 – Mikrofon/Kamera, VPN, Downloads

### N. Mikrofon

```bash
parecord /tmp/mic-test.wav     # nimmt auf, bis Ctrl+C
```

- [ ] **N1** Kurz „Mikrofon aktiv · parecord“ (o. ä.), danach ein **oranger Punkt** rechts in der Pille; die Pille ist etwas breiter
- [ ] **N2** Insel aufklappen: Kopfzeile neben der Uhr zeigt ein orangefarbenes Mikro; Maus drauf → „Mikrofon: … · Klick = stumm“
- [ ] **N3** Klick auf das Mikro → Symbol durchgestrichen, Punkt grau, Hinweis „Mikrofon stumm“; `pactl get-source-mute @DEFAULT_SOURCE@` → `yes`
- [ ] **N4** Nochmal klicken → „Mikrofon an“, Punkt wieder orange
- [ ] **N5** Stummschalten über Cinnamons Sound-Applet → Punkt wird ebenfalls grau
- [ ] **N6** `Ctrl+C` bei parecord → Punkt verschwindet, Pille wieder normal breit
- [ ] **N7** pavucontrol öffnen, Tab „Eingabegeräte“ (Pegel läuft) → **kein** Punkt
- [ ] **N8** Echte App: Mikrofontest im Browser (z. B. Firefox, https://webcammictest.com) → „Mikrofon aktiv · Firefox“; Tab schließen → Punkt weg
- [ ] **N9** Minimal-Notch im Tray an, dann N1 wiederholen → statt des Strichs erscheint die normale Pille mit Punkt; nach N6 wieder der Strich

### O. Kamera (falls eine Webcam da ist)

```bash
ls -l /dev/video*                  # crw-rw----+ … video …  (das + = Rechte für dich)
cheese                             # oder: ffplay /dev/video0
```

- [ ] **O1** Nach ~1 s „Kamera aktiv · Cheese“ und ein **grüner Punkt**; mit Mikrofon zusammen beide Punkte
- [ ] **O2** Aufgeklappt: grünes Kamera-Symbol, Maus drauf → „Kamera: Cheese“
- [ ] **O3** Cheese schließen → Punkt nach ~1 s weg
- [ ] **O4** Browser-Einstellungen → Kamera-Auswahl öffnen (listet nur auf) → **kein** Punkt
- [ ] **O5** USB-Webcam erst bei laufender Insel einstecken, dann O1 → klappt auch
- [ ] **O6** Videocall (Meet/Zoom/Teams im Browser oder als App) → Punkt mit App-Namen (oder „PipeWire“)

### P. VPN

Ohne echtes VPN (legt kurz eine tun-Schnittstelle an):

```bash
sudo ip tuntap add dev tun9 mode tun && sudo ip link set tun9 up
sleep 3
sudo ip tuntap del dev tun9 mode tun
```

- [ ] **P1** „VPN verbunden · tun9“, nach dem Löschen „VPN getrennt“
- [ ] **P2** Aufgeklappt, während tun9 da ist: VPN-Symbol in der Kopfzeile, Maus drauf → „VPN · tun9“
- [ ] **P3** Mit echtem VPN im NetworkManager (Netzwerk-Applet → VPN): Hinweis mit dem Namen der Verbindung, erst wenn sie **verbunden** ist (nicht schon beim Verbinden)
- [ ] **P4** Tray → „Live-Hinweise“ → „VPN: Land & IP (fragt ipinfo.io)“ an, VPN neu verbinden → nach ~2 s „VPN · 🇨🇭 Schweiz · 1.2.3.4“ (Land und IP des VPN-Servers, Ländername auf Deutsch)
- [ ] **P5** Ohne den Schalter aus P4 geht **keine** Anfrage raus: `sudo tcpdump -i any host ipinfo.io` bleibt beim Verbinden leer (optional)
- [ ] **P6** Virtuelle Maschine (virt-manager/VirtualBox) starten → **kein** VPN-Hinweis (vnet/virbr/vboxnet)

### Q. Downloads

```bash
# Simuliert einen Firefox-Download
D="$(xdg-user-dir DOWNLOAD)"
for i in $(seq 1 8); do head -c 5000000 /dev/zero >> "$D/test.bin.part"; sleep 1; done
mv "$D/test.bin.part" "$D/test.bin"
```

- [ ] **Q1** Nach ~1 s „Download · test.bin“, danach ein **Ring mit Pfeil** rechts in der Pille
- [ ] **Q2** Aufgeklappt: Download-Symbol mit Größe (z. B. „35 MB“), Maus drauf → „test.bin · 35 MB · 5 MB/s“; Klick öffnet den Download-Ordner
- [ ] **Q3** Nach dem `mv`: „Download fertig · test.bin“, Ring weg; Klick auf den Hinweis → Nemo öffnet sich mit **test.bin markiert**
- [ ] **Q4** Echter Firefox-Download (z. B. https://ash-speed.hetzner.com/100MB.bin) → wie Q1–Q3, am Ende der richtige Dateiname
- [ ] **Q5** Download in Firefox abbrechen → Ring verschwindet, **kein** „fertig“-Hinweis
- [ ] **Q6** Chromium/Chrome-Download → Ring füllt sich blau, Kopfzeile zeigt **Prozent** statt Größe (wenn nicht: notieren, Browser + Version)
- [ ] **Q7** Download pausieren → nach ~1 Minute verschwindet der Ring; Fortsetzen → kommt wieder
- [ ] **Q8** `rm "$(xdg-user-dir DOWNLOAD)/test.bin"`

### R. Schalter, Sprache, Leistung

- [ ] **R1** Tray → „Live-Hinweise“: „Mikrofon & Kamera“ aus → Punkte weg, N1 zeigt nichts mehr; wieder an → Punkt kommt (auch für eine schon laufende Aufnahme)
- [ ] **R2** „VPN-Status“ aus → P1 zeigt nichts; „Download-Fortschritt“ aus → Q1 zeigt nichts
- [ ] **R3** Schalter stehen danach in `~/.config/linuxmos/island/config.json` (`privacy_indicator`, `vpn_status`, `vpn_lookup`, `downloads_progress`); `./update.sh` lässt sie so
- [ ] **R4** English: Untermenü „Live hints“, Hinweise „Microphone on · …“, „VPN connected · …“, „Download finished · …“
- [ ] **R5** Leerlauf (kein Download, kein Mikro): `linuxmos-perf 20` → `linuxmos-island` ≤ 0,2 % CPU wie vorher
- [ ] **R6** Während Q4 läuft: `linuxmos-perf 10` → `linuxmos-island` bleibt unter ~1 % CPU
- [ ] **R7** Mit laufender Aufnahme (N1) eine Minute warten: `linuxmos-perf 20` → ebenfalls ≤ 0,2 %

---

## Paket 7 – Command Bar

### S. Öffnen und Tastatur

- [ ] **S1** `update.sh` hat den Hotkey angelegt: Systemeinstellungen → Tastatur → Tastenkürzel → Eigene Tastenkürzel → „MosIsland Suche (LinuxMos)“ = `Ctrl+Alt+Space`
- [ ] **S2** `Ctrl+Alt+Space` in einem beliebigen Fenster → Insel klappt auf, Lupen-Tab aktiv, Cursor im Eingabefeld, sofort tippbar
- [ ] **S3** Hotkey nochmal → Insel klappt zu, das vorige Fenster hat wieder den Fokus
- [ ] **S4** Wieder öffnen → letzte Eingabe steht markiert drin, Tippen ersetzt sie
- [ ] **S5** `↑`/`↓` wechseln den Treffer, `Esc` klappt zu
- [ ] **S6** Insel per Maus öffnen, auf die Lupe klicken → Cursor im Feld (Hovern allein nimmt **nicht** den Fokus)
- [ ] **S7** `Super+Space` öffnet weiterhin die rofi-Suche

### T. Treffer

- [ ] **T1** `fire` → Firefox ganz oben, `Enter` startet ihn und Firefox bekommt den Fokus
- [ ] **T2** `einst` (bzw. `sett`) → Systemeinstellungen; Apps, die du öfter startest, rutschen bei gleicher Trefferart nach oben
- [ ] **T3** Leeres Feld → die zuletzt über die Suche gestarteten Apps
- [ ] **T4** Name einer Datei im Home-Ordner (z. B. aus `~/Dokumente`) → Datei mit Ordner darunter; `Enter` öffnet sie mit der Standard-App
- [ ] **T5** Gleicher Treffer, `Ctrl+Enter` → Nemo öffnet sich mit der Datei markiert
- [ ] **T6** Eine gerade in LibreOffice/Xed geöffnete Datei steht oben (zuletzt benutzt)
- [ ] **T7** `12*7` → „= 84“; `Enter` → Hinweis „Kopiert · 84“, `Ctrl+V` in einem Editor fügt 84 ein
- [ ] **T8** In Xed: `Ctrl+Alt+Space`, `2^10`, `Ctrl+Enter` → „1024“ steht direkt in Xed
- [ ] **T9** `1,5*2` → „= 3“; `50*20%` → „= 10“; `sqrt(2)` → „= 1,41421356237“
- [ ] **T10** `5 km in mi` → „5 km = 3,10686 mi“; `100 f in c` → „37,7778 °C“; `1 GiB in MB` → „1073,74 MB“
- [ ] **T11** `20 usd in eur` → nach kurzem „Wechselkurse werden geladen …“ der Betrag in EUR mit „EZB-Kurs vom …“; danach liegt `~/.cache/linuxmos/island/rates.json`
- [ ] **T12** Ohne Netz (WLAN aus) und ohne `rates.json` → „Wechselkurse nicht erreichbar (offline?)“, die Insel hängt nicht
- [ ] **T13** `github.com` → „Website öffnen“ öffnet https://github.com im Browser
- [ ] **T14** `linux mint wallpaper` → letzter Treffer „… im Web suchen · DuckDuckGo“, `Enter` öffnet die Suche im Browser

### U. Schalter, Sprache, Leistung

- [ ] **U1** Tray → „Suche“ → „Websuche mit“ → Google: der Web-Treffer heißt jetzt Google; in `config.json` steht `"command_bar_engine": "google"`
- [ ] **U2** „Dateien durchsuchen“ aus → keine Datei-Treffer mehr; „Währungen“ aus → `20 usd in eur` zeigt nur noch die Websuche
- [ ] **U3** Eigene URL in `config.json`: `"command_bar_engine": "https://de.wikipedia.org/w/index.php?search=%s"`, Insel neu starten → Web-Treffer heißt „de.wikipedia.org“
- [ ] **U4** English: Tab-Tooltip „Search“, Platzhalter „Apps, files, maths, web …“, `5 km in mi` → „3.10686 mi“ (Punkt statt Komma)
- [ ] **U5** Leerlauf ohne die Suche je geöffnet zu haben: `linuxmos-perf 20` → `linuxmos-island` ≤ 0,2 % CPU wie vorher
- [ ] **U6** Suche benutzt (Datei gesucht), zugeklappt, 1 Minute warten: `linuxmos-perf 20` → ebenfalls ≤ 0,2 %
- [ ] **U7** RAM: `ps -o rss= -C linuxmos-island` vor der ersten Suche und danach notieren (erwartet: etwa +5 MB)

---

## Paket 8 – Mehrere Monitore

Braucht einen zweiten Monitor (oder Laptop + externer Bildschirm). `xrandr --listmonitors` zeigt die Namen.

### W. Monitor wählen

- [ ] **W1** Ohne Änderung sitzt die Insel oben mittig auf dem Hauptmonitor, direkt unter der Top Bar (wie vorher)
- [ ] **W2** Tray → „Monitor“ listet „Hauptmonitor“, „Monitor mit der Maus (beim Öffnen)“ und jeden angeschlossenen Monitor mit Name und Auflösung (der Hauptmonitor mit „(Hauptmonitor)“)
- [ ] **W3** Den anderen Monitor wählen → die Insel springt sofort hinüber, oben mittig; in `config.json` steht z. B. `"monitor": "HDMI-1"`
- [ ] **W4** Hat der andere Monitor eine eigene Top Bar: die Insel sitzt darunter, nicht dahinter. Ohne Top Bar dort: 6 px vom oberen Rand
- [ ] **W5** In `config.json` `"monitor": 0` bzw. `1` eintragen, Insel neu starten → linker bzw. rechter Monitor; im Tray ist der passende Monitor markiert
- [ ] **W6** Hovern, Karten (`notify-send Test Hallo`), Screenshot-Hinweis und Command Bar erscheinen auf dem gewählten Monitor

### X. Ein- und Ausstecken

- [ ] **X1** Insel auf dem externen Monitor, Kabel ziehen (oder in den Bildschirmeinstellungen ausschalten) → die Insel wechselt binnen ~2 s auf den Hauptmonitor
- [ ] **X2** Tray → „Monitor“ zeigt den Monitor jetzt als „… (nicht angeschlossen)“, die Einstellung in `config.json` ist unverändert
- [ ] **X3** Wieder einstecken → die Insel kehrt auf den externen Monitor zurück, unter dessen Top Bar
- [ ] **X4** Monitore in den Bildschirmeinstellungen tauschen (links/rechts) oder Auflösung ändern → die Insel bleibt mittig auf dem gewählten Monitor
- [ ] **X5** Laptop: Deckel zu mit externem Monitor (falls so eingerichtet) und wieder auf → die Insel landet nie außerhalb des Bildschirms

### Y. Monitor mit der Maus

- [ ] **Y1** Tray → „Monitor“ → „Monitor mit der Maus (beim Öffnen)“: die Insel bleibt erst einmal, wo sie ist
- [ ] **Y2** Maus auf den anderen Monitor, `Ctrl+Alt+I` → die Insel öffnet sich dort; zugeklappt bleibt sie dort
- [ ] **Y3** Maus zurück, `Ctrl+Alt+Space` (oder `Ctrl+Alt+V`) → die Insel öffnet sich auf diesem Monitor
- [ ] **Y4** Linksklick aufs Tray-Icon in der Top Bar des Nebenmonitors (falls dort eine ist) → die Insel öffnet sich dort
- [ ] **Y5** Nur die Maus bewegen (ohne Hotkey) → die Insel bleibt, wo sie ist

### Z. Leistung

- [ ] **Z1** Leerlauf: `linuxmos-perf 20` → `linuxmos-island` ≤ 0,2 % CPU wie vorher, mit `"primary"` und mit `"pointer"`
- [ ] **Z2** Englisch: Tray → „Monitor“ heißt „Monitor“, Einträge „Primary monitor“, „Monitor with the mouse (when opened)“

---

## Paket 9 – RAM und Performance

### R. Speicher

```bash
linuxmos-perf 10                   # unten steht „MosIsland RAM: RSS … MB · PSS … MB“
grep -c -E "libLLVM|libgallium" /proc/$(pgrep -x -n linuxmos-island)/maps    # erwartet: 0
```

- [ ] **R1** Gleich nach dem Anmelden (Insel noch nicht geöffnet): RSS deutlich unter 115 MB (unter Xvfb: ~60 MB) – Wert notieren: ______ MB
- [ ] **R2** Kein `libLLVM`/`libgallium` in der Insel (Befehl oben → `0`)
- [ ] **R3** Alle Tabs einmal öffnen, zuklappen, 10 s warten, neu messen → höchstens ein paar MB mehr als R1: ______ MB
- [ ] **R4** Leerlauf: `linuxmos-perf 20` → `linuxmos-island` ≤ 0,2 % CPU wie vorher

### S. Tabs bei Bedarf

- [ ] **S1** Jeder Tab (Zwischenablage, Ablage, Aufgaben, Notiz, Wasser, Wetter, Steuerung) zeigt beim ersten Öffnen sofort seinen Inhalt, kein leerer Bereich
- [ ] **S2** Timer starten (Jetzt-Tab → Timer-Kachel → Notiz & Fokus) **nach** einem frischen Start: die Restzeit läuft im Notiz-Tab
- [ ] **S3** Etwas kopieren, bevor die Zwischenablage je offen war → beim Öffnen steht es oben
- [ ] **S4** Text per `Ctrl+Alt+O` erkennen → „In Notiz“, bevor der Notiz-Tab je offen war → der Text steht in der Notiz

### T. Netz über curl

- [ ] **T1** Wetter: Ort neu setzen (`linuxmos-island --set-city Hamburg`, Insel neu starten) → Wetter erscheint
- [ ] **T2** Lyrics-Ansicht bei einem bekannten Song → Lyrics laufen mit
- [ ] **T3** Spotify-/Browser-Cover erscheinen in Pille und Jetzt-Tab; `ls -la ~/.cache/linuxmos/island/art` → neue Dateien nur wenige KB groß
- [ ] **T4** Command Bar: `20 usd in eur` → Ergebnis mit Kurs
- [ ] **T5** WLAN aus → Wetter-Tab „Aktualisieren“ → „Keine Verbindung“, keine Fehlermeldung, Insel läuft weiter
- [ ] **T6** Über die Command Bar eine App mit 3D/Video starten (z. B. ein Spiel, Blender oder Celluloid) → läuft normal (sie erbt `GDK_GL` nicht)

---

## Paket 10 – Bildschirmaufnahme, KI-Chat, Diktat, Maskottchen

Vorher: `./update.sh` (installiert `ffmpeg` und `libsecret-tools` nach, setzt die Hotkeys `Ctrl+Alt+R`, `Ctrl+Alt+Shift+R`, `Ctrl+Alt+A`, `Ctrl+Alt+M`; bestehende Tastenkürzel von dir bleiben).

### U. Bildschirmaufnahme

```bash
ls ~/Videos/LinuxMos
ffprobe -v error -show_entries stream=codec_name,width,height -of default=nw=1 ~/Videos/LinuxMos/Recording_*.mp4
```

- [ ] **U1** `Ctrl+Alt+Shift+R`: Insel verschwindet, Tray-Icon wird **rot**; nach ~5 s `Ctrl+Alt+Shift+R` nochmal → Karte „Aufnahme gespeichert“ mit „Abspielen“ und „Im Ordner zeigen“
- [ ] **U2** Die MP4 spielt ab (Bild, Maus sichtbar), Insel und Tray-Hinweis sind **nicht** im Video; `ffprobe` zeigt `h264` in Monitorgröße
- [ ] **U3** `Ctrl+Alt+R`, Bereich aufziehen → nur der Bereich wird aufgenommen; `Esc` bei der Auswahl bricht ab, die Insel kommt zurück
- [ ] **U4** Ein Klick auf das rote Tray-Icon beendet die Aufnahme; Tray → „Bildschirmaufnahme“ → „Aufnahme beenden“ ebenso
- [ ] **U5** Tray → „Format“ → GIF, kurze Aufnahme: Insel zeigt „GIF wird erstellt …“, danach Karte; die GIF öffnet sich im Browser und läuft; keine `.mp4` mehr in `~/.cache/linuxmos/island/recordings/`
- [ ] **U6** Tray → „Ton (nur MP4)“ → „Systemton“, Musik laufen lassen, aufnehmen → die MP4 hat Ton; mit „Mikrofon“ ist die eigene Stimme drauf
- [ ] **U7** Aufnahme läuft, `Ctrl+Alt+S` → Aufnahme endet sauber, die Datei spielt ab
- [ ] **U8** `"record_max_min": 1` in `config.json`, Insel neu starten, aufnehmen und nichts tun → nach ~60 s endet die Aufnahme von selbst mit Karte
- [ ] **U9** Während der Aufnahme `notify-send Test` → kein Popup im Video; danach im Benachrichtigungs-Applet
- [ ] **U10** Idle-CPU nach einer Aufnahme: `linuxmos-perf 20` → `linuxmos-island` ≤ 0,2 %, kein `ffmpeg`-Prozess mehr (`pgrep ffmpeg`)

### V. KI-Chat (mit eigenem Server)

```bash
linuxmos-island --set-key          # Key unsichtbar eintippen
secret-tool lookup service linuxmos-island account ai-api-key | wc -c      # > 1
grep -c "sk-" ~/.config/linuxmos/island/config.json                         # erwartet: 0
```

- [ ] **V1** Tray → „KI“ → „Chat-Tab“ einschalten: neuer Smiley-Tab erscheint; `Ctrl+Alt+A` öffnet ihn, Cursor steht in der Eingabezeile
- [ ] **V2** „Verbindung & API-Key …“ (Zahnrad im Chat oder Tray): Adresse/Modell eintragen, Key tippen, „Speichern“ → „API-Key im Schlüsselbund gespeichert“; beim erneuten Öffnen steht „gespeichert“ im Key-Feld
- [ ] **V3** Frage senden: Antwort läuft Wort für Wort ein, Kopieren-Symbol daneben kopiert sie; ■ bricht eine laufende Antwort ab
- [ ] **V4** Während einer Antwort `ps aux | grep curl` → der Key steht **nicht** in der Befehlszeile
- [ ] **V5** Falscher Key → rote Blase „API-Key abgelehnt (HTTP 401) …“, die Frage steht wieder in der Eingabezeile
- [ ] **V6** Server aus/Adresse falsch → „Server nicht erreichbar …“
- [ ] **V7** „Neues Gespräch“ leert den Verlauf; eine Folgefrage bezieht sich auf die vorige Antwort
- [ ] **V8** Ollama lokal (`http://localhost:11434/v1`, kein Key) → Chat geht ohne Key
- [ ] **V9** „Key entfernen“ (Tray) → `secret-tool lookup …` liefert nichts; Chat sagt „Kein API-Key gespeichert“
- [ ] **V10** Chat-Tab ausschalten → Tab verschwindet, `Ctrl+Alt+A` zeigt „KI-Chat ist aus“
- [ ] **V11** `linuxmos-perf`: RSS direkt nach dem Start und nach dem ersten Öffnen des Chat-Tabs: ______ MB / ______ MB (Erwartung: ~+1 MB)

### W. Diktat

- [ ] **W1** Tray → „KI“ → „Diktat“ einschalten; Cursor in ein Textfeld (z. B. gedit), `Ctrl+Alt+M` → Insel zeigt „Diktat · sprich jetzt“, **orangen Mikrofon-Punkt**
- [ ] **W2** Satz sprechen, `Ctrl+Alt+M` nochmal → „Wird aufgeschrieben …“, dann steht der Text im Textfeld (Terminal: per `Ctrl+Shift+V`)
- [ ] **W3** „Diktat direkt einfügen“ aus → statt Einfügen kommt eine Karte „Diktat · kopiert“ mit „Einfügen“ und „In Notiz“
- [ ] **W4** Chat-Tab offen, Mikro-Button neben dem Senden-Knopf → der Text landet in der Eingabezeile, nicht im anderen Fenster
- [ ] **W5** Zu kurz (< 0,5 s) → „Zu kurz, nichts aufgenommen“
- [ ] **W6** Nach dem Diktat existiert `~/.cache/linuxmos/island/recordings/dictation.wav` nicht mehr
- [ ] **W7** Server ohne `/audio/transcriptions` (z. B. Ollama) → Fehlermeldung mit HTTP 404, Insel läuft weiter

### X. Maskottchen

- [ ] **X1** Tray → „Maskottchen“ zeigt Anzeigen-Haken und die Figuren Augen, Katze, Roboter, Blob
- [ ] **X2** Figur wählen, 5 min nichts tun (oder `"idle"` abwarten) → die gewählte Figur erscheint in der Pille, blinzelt, schläft mit „z z“ ein
- [ ] **X3** Maus bewegen → Figur winkt (^ ^), danach Uhr; die Wahl bleibt nach einem Neustart erhalten

---

## Ergebnisse

| Nr. | Ergebnis | Notiz |
|-----|----------|-------|
|     |          |       |

Getestet am: ______ · Mint-Version: `cat /etc/linuxmint/info` → ______ · Cinnamon: `cinnamon --version` → ______
