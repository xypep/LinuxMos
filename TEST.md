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
linuxmos-island --version          # erwartet: MosIsland 1.6.0
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

---

## Ergebnisse

| Nr. | Ergebnis | Notiz |
|-----|----------|-------|
|     |          |       |

Getestet am: ______ · Mint-Version: `cat /etc/linuxmint/info` → ______ · Cinnamon: `cinnamon --version` → ______
