# Clip-Transfer – Text, Bilder und Dateien zwischen PCs

Mit dem Clip-Transfer schickst du Text, ein Bild oder eine Datei per SSH von einem PC zum anderen: mit einem Knopf an einem Eintrag der Zwischenablage oder der Ablage, mit einem Hotkey oder von der Kommandozeile. Das Gegenstück heißt Empfang: Was ankommt, wartet in einem Eingangsordner, steht im Zwischenablage-Verlauf (Text, Bild) bzw. in der Ablage (Datei) und erscheint als Karte auf der Insel.

**Der Grundsatz ist: nur manuell.**

- **Senden** passiert ausschließlich auf deine ausdrückliche Handlung (Knopf, Hotkey, `linuxmos-clip send`). Es gibt kein automatisches Senden, keinen Clipboard-Watcher und nichts, was auf eine Änderung der Zwischenablage reagiert.
- **Empfangen** ist passiv: Inhalte landen im Eingangsordner und im Verlauf. **Nichts wird automatisch in die Zwischenablage geschrieben**; erst ein Klick auf die Karte oder den Eintrag kopiert den Inhalt. Dateien werden nie geöffnet.
- Als privat markierte Kopien (Passwort-Manager wie KeePassXC) werden nie gesendet.
- Beide Richtungen sind getrennt schaltbar und **standardmäßig aus**. Aus heißt aus: kein Datei-Monitor, nichts geladen (das Log sagt `clip: disabled, no monitors`).

Es gibt keinen Daemon, keine dauerhafte Verbindung und keinen Netzwerk-Port der Insel: Jeder Clip ist ein einzelner `ssh`-Aufruf, der danach endet. Der Empfänger braucht einen laufenden SSH-Server.

Zur Windows-Seite siehe [CLIP-WINDOWS.md](CLIP-WINDOWS.md) (ungetestet).

## Inhalt

- [Einrichtung Schritt für Schritt](#einrichtung-schritt-für-schritt)
- [Benutzen](#benutzen)
- [Limits](#limits)
- [Was die Karten sagen](#was-die-karten-sagen)
- [Sicherheit](#sicherheit)
- [Einstellungen](#einstellungen)
- [linuxmos-clip auf der Kommandozeile](#linuxmos-clip-auf-der-kommandozeile)
- [Problemlösung](#problemlösung)
- [Aufräumen und Deinstallieren](#aufräumen-und-deinstallieren)

---

## Einrichtung Schritt für Schritt

Beispiel: **PC A** (Absender) schickt an **PC B** (Empfänger), beide mit LinuxMos und MosIsland. Für die Gegenrichtung wiederholst du alles mit vertauschten Rollen.

`openssh-client` ist auf Mint meist da (`install.sh --island` bzw. `update.sh` installieren ihn bei Bedarf). Der **SSH-Server wird nie automatisch installiert**: Das musst du auf dem Empfänger selbst entscheiden.

### 1. Auf PC B (Empfänger): SSH-Server und Empfang

```bash
sudo apt install openssh-server          # falls nicht vorhanden
sudo systemctl enable --now ssh          # läuft dauerhaft (nur für diesen Zweck nötig: Port 22 ist dann offen)
ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub     # Fingerabdruck notieren, du vergleichst ihn gleich
```

Empfang einschalten: Tray-Menü → **Clip-Transfer** → **Clip-Empfang** (oder `"clip_receive_enabled": true` in `config.json`). Ohne diesen Schalter lehnt `linuxmos-clip receive` alles ab.

> Der SSH-Server ist ein offener Port. Wer nur im Heimnetz teilen will, schützt ihn mit der Firewall (`sudo ufw allow from 192.168.0.0/24 to any port 22`). Passwort-Anmeldung kannst du in `/etc/ssh/sshd_config` (`PasswordAuthentication no`) abschalten; der Clip-Transfer braucht sie nie.

### 2. Auf PC A (Absender): einrichten

```bash
linuxmos-clip setup
```

Es fragt Name, Adresse und Benutzer des Empfängers und dann:

1. **Schlüssel:** erzeugt `~/.ssh/linuxmos_clip_ed25519` (ed25519, ohne Passwort, Rechte 600), falls er noch fehlt. Er dient nur diesem Zweck.
2. **Host-Schlüssel:** zeigt den **Fingerabdruck** des Empfängers. Vergleiche ihn mit dem aus Schritt 1 und tippe nur bei Übereinstimmung `ja`. Es gibt keine stille Annahme (`accept-new`); ohne diese bewusste Bestätigung wird nichts gespeichert. Für Skripte gibt es `--fingerprint SHA256:…` (es muss stimmen).
3. **Peer:** trägt den Empfänger in `config.json` ein (`clip_peers`, der erste wird `clip_default_peer`) und fragt, ob Senden gleich eingeschaltet werden soll.
4. **authorized_keys-Zeile:** gibt die Zeile für den Empfänger aus.

Die Zeile sieht so aus:

```text
restrict,command="~/.local/bin/linuxmos-clip receive-ssh" ssh-ed25519 AAAAC3… linuxmos-clip@pc-a
```

`restrict` schaltet alles ab (Terminal, Port-Weiterleitung, Agent, X11), und `command=` erzwingt, dass der Schlüssel nur `linuxmos-clip receive-ssh` startet. **Mit diesem Schlüssel kann man nichts anderes tun als Clips abliefern.** (Warum der Pfad `~/.local/bin/…` und nicht nur `linuxmos-clip` dort steht: sshd startet den Zwangsbefehl ohne dein `PATH`. Liegt das Programm woanders, gib beim `setup` den Pfad mit `--receiver-command /usr/local/bin/linuxmos-clip` an.)

### 3. Auf PC B: die Zeile eintragen

```bash
mkdir -p ~/.ssh && chmod 700 ~/.ssh
nano ~/.ssh/authorized_keys              # die ganze Zeile ans Ende, speichern
chmod 600 ~/.ssh/authorized_keys
```

### 4. Prüfen

```bash
linuxmos-clip doctor                     # auf PC A: Schlüssel, Peer, Host-Schlüssel, Erreichbarkeit
linuxmos-clip doctor                     # auf PC B: SSH-Server, authorized_keys, Eingang, Quota
```

`doctor` ruft den Peer mit einem **leeren** Clip an: Er beweist Verbindung, Schlüssel und Empfänger und speichert nichts. Danach kannst du etwas senden (siehe unten).

---

## Benutzen

### Senden (immer von Hand)

Voraussetzung: **Clip-Senden** ist an (Tray → Clip-Transfer, oder `clip_send_enabled`) und mindestens ein Peer ist eingerichtet.

| Wie | Was passiert |
|---|---|
| **Knopf „An PC senden“** (Papierflieger) an einem Eintrag im Tab **Zwischenablage** | Text oder Bild dieses Eintrags geht an den Peer |
| Derselbe Knopf an einer Datei im Tab **Ablage** (beim Darüberfahren sichtbar) | Die Datei geht an den Peer (Ordner nicht) |
| **`Ctrl+Alt+Shift+T`** | Die **aktuelle Zwischenablage** geht an den Standard-Peer: Text, Bild oder eine einzelne in Nemo kopierte Datei |
| `linuxmos-island --clip-send` | dasselbe wie der Hotkey |
| `linuxmos-clip send …` | von der Kommandozeile oder aus Skripten, siehe unten |

Mit **mehreren Peers** fragt der Knopf kurz nach dem Ziel (eine Zeile „Senden an: …“ unten im Tab); sonst geht es direkt an den einen Peer. Der **Standard-Peer** (für den Hotkey und `linuxmos-clip send` ohne `--peer`) ist `clip_default_peer`; im Streifen „Transfer“ unten im Zwischenablage-Tab wechselst du ihn mit einem Klick auf den Peer-Namen.

Der Hotkey liegt auf `Ctrl+Alt+Shift+T`, weil `Ctrl+Alt+T` in Cinnamon schon das Terminal öffnet. `install.sh`/`update.sh` tragen ihn ein; du kannst ihn in den Tastatur-Einstellungen von Cinnamon ändern („MosIsland Clip senden“).

Der Verlauf speichert höchstens 20 000 Zeichen pro Text. Ein längerer Text geht vollständig nur mit dem Hotkey (er liest die Zwischenablage selbst), der Knopf am Eintrag sendet den gekürzten Verlaufstext und sagt das auf der Karte.

### Empfangen (passiv)

Voraussetzung: **Clip-Empfang** ist an. Kommt etwas an, passiert Folgendes:

- Eine **Karte** „Vom Windows-PC empfangen · Text (123 Zeichen)“ (oder Bild, Datei) erscheint oben auf der Insel. Kommen mehrere zusammen an, sagt sie „3 Einträge empfangen“.
- Text und Bilder stehen im **Zwischenablage-Verlauf**, markiert mit **empfangen** (Mauszeiger darauf: von wem).
- Dateien liegen in `~/Downloads/LinuxMos/` und stehen in der **Ablage** (zum Herausziehen oder Doppelklicken).
- **Ein Klick auf die Karte oder auf den Eintrag kopiert** Text oder Bild in die Zwischenablage. Anders als bei normalen Einträgen wird dabei **nichts ins aktive Fenster getippt**; eingefügt wird, wenn du es willst (`Ctrl+V`). Ein Klick auf die Karte einer Datei öffnet die Ablage.
- Läuft **Vollbild** (Film, Spiel), **wartet** die Karte und erscheint danach. Dasselbe gilt, solange du die Insel offen hast, eine Aufnahme läuft oder eine andere Karte zu sehen ist.
- Ist die Insel **nicht gestartet**, wartet der Eintrag im Eingangsordner und erscheint beim nächsten Start.

Der Eingangsordner ist `~/.local/share/linuxmos/island/clip-inbox/` (Rechte 700, Dateien 600). Einträge, die älter sind als `clip_inbox_keep_days` (7 Tage), werden beim Start der Insel und beim Eintreffen eines neuen gelöscht (kein Timer); neue werden abgelehnt, wenn der Eingang `clip_inbox_quota_mb` (500 MB) überschreiten würde. **Empfangene Dateien** in `~/Downloads/LinuxMos/` bleiben immer: Sie gehören dir. Solange ihr Eintrag existiert, zählen sie zur Quota.

Text, den ein Windows-PC oder `echo` schickt, bekommt `\r\n` → `\n`, und ein einzelner Zeilenumbruch am Ende wird entfernt (er ist fast nie gemeint).

---

## Limits

| Was | Standard | Schlüssel |
|---|---|---|
| Text | 1024 KB | `clip_max_text_kb` |
| Bild | 20 MB | `clip_max_image_mb` |
| Datei | 100 MB | `clip_max_file_mb` |
| Eingang gesamt | 500 MB | `clip_inbox_quota_mb` |
| Aufbewahrung im Eingang | 7 Tage | `clip_inbox_keep_days` |

**Der Empfänger erzwingt die Limits beim Lesen von stdin**, nicht nur der Sender: Ein zu großer Clip wird mitten im Lesen abgebrochen und aufgeräumt, es bleiben keine halben Dateien. Auch der Sender prüft vorher und spart sich den Versuch. Bei Unterschieden gilt das **strengere**: Das Limit des Empfängers hängt von dessen `config.json` ab.

---

## Was die Karten sagen

| Karte | Bedeutung · was tun |
|---|---|
| **Gesendet an Name** | angekommen |
| **Nicht erreichbar** | PC aus, falsche Adresse/Port, SSH-Server läuft nicht, Firewall. Auf dem Empfänger: `linuxmos-clip doctor` |
| **Schlüssel abgelehnt** | Die Zeile fehlt in `authorized_keys` des Empfängers, ist unvollständig oder gehört zu einem anderen Schlüssel |
| **Host-Schlüssel unbekannt** | Der Empfänger ist noch nicht bestätigt: `linuxmos-clip setup` (zeigt den Fingerabdruck) |
| **Host-Schlüssel geändert** | Der Empfänger meldet einen anderen Schlüssel als beim ersten Mal (neu installiert? oder jemand dazwischen?). Nicht senden, erst klären; bei einer Neuinstallation `ssh-keygen -R <adresse>` und `setup` |
| **Zu groß** | über dem Limit (Sender oder Empfänger) |
| **Empfang aus** | auf dem Empfänger ist `clip_receive_enabled` aus |
| **Eingang voll** | die Quota des Empfängers ist erreicht: `linuxmos-clip clean --all` dort oder warten |
| **Der Empfänger hat den Inhalt nicht angenommen** | leer, kein UTF-8-Text oder kein Bild |
| **linuxmos-clip fehlt** | der Pfad in der `authorized_keys`-Zeile stimmt nicht |
| **Als privat markiert … nie gesendet** | der Hotkey hat eine Kopie aus einem Passwort-Manager erkannt |
| **Schlüsseldatei fehlt / zu offene Rechte** | `~/.ssh/linuxmos_clip_ed25519` (oder `key` des Peers) prüfen, Rechte 600 |

Alle Meldungen erscheinen als Karte (die Insel öffnet nie ein Dialogfenster), der Streifen „Transfer“ im Zwischenablage-Tab zeigt den letzten Stand.

---

## Sicherheit

- **Nur SSH-Schlüssel (ed25519), keine Passwörter.** Aufrufe laufen mit `BatchMode=yes` (nie eine Rückfrage), `StrictHostKeyChecking=yes` (ein unbekannter oder geänderter Host-Schlüssel wird abgelehnt, nie stillschweigend angenommen), `IdentitiesOnly=yes`, `ControlMaster=no` (keine dauerhafte Verbindung) und `ConnectTimeout=5`.
- **Der Schlüssel ist beschränkt.** Mit `restrict,command="… receive-ssh"` kann er nur `receive-ssh` starten. Der liest den Befehl, den der Absender angefragt hat (`SSH_ORIGINAL_COMMAND`), und akzeptiert genau eine Form: `linuxmos-clip receive --type text|image|file` und optional `--name '…'` mit `[A-Za-z0-9._ -]{1,120}`. Alles andere (`ls`, `receive --type file; id`, …) wird mit Exit-Code 5 abgelehnt. Der Befehl läuft **nie über eine Shell**. Getestet mit einem echten `sshd`: kein Login, kein Terminal, keine Port-Weiterleitung, kein `sftp`/`scp`.
- **Dateinamen werden bereinigt:** kein Pfad (alles vor dem letzten `/` oder `\` fällt weg), kein `..`, kein Punkt am Anfang, keine Steuer- oder Bidi-Zeichen, Länge begrenzt. Gleichnamige Dateien bekommen eine Nummer (`bericht (1).pdf`), nichts wird überschrieben; Symlinks werden weder verfolgt noch angelegt.
- **Empfangenes wird nie ausgeführt oder geöffnet.** Dateien liegen nur da; Bilder werden von GdkPixbuf dekodiert, wenn du die Karte siehst oder den Eintrag öffnest (wie ein Bild, das du aus dem Browser kopierst).
- **Ein gestohlener Schlüssel** erlaubt nur, Clips bei dir abzuliefern – bis zu den Limits und der Quota, also Text im Verlauf (er landet in keiner Zwischenablage, solange du nicht klickst), Bilder und Dateien in deinen Ordnern. Lösche die Zeile aus `authorized_keys`, und er ist wertlos. Der Absender des Clips ist die Adresse, von der er kam (`SSH_CONNECTION`), mehr weiß der Empfänger nicht.
- **Klartext:** Verlauf (`clipboard.json`), Eingang und empfangene Dateien liegen **unverschlüsselt** auf der Platte, wie der bestehende Zwischenablage-Verlauf. Kopien, die ein Passwort-Manager als geheim markiert, werden weder in den Verlauf aufgenommen noch gesendet.
- **Keine neuen offenen Ports durch die Insel.** Der Empfänger braucht den SSH-Server des Systems (Port 22); schränke ihn mit der Firewall auf dein Heimnetz ein.
- **Gesendet wird nur auf Handlung.** Eine Änderung der Zwischenablage löst nie etwas aus.

---

## Einstellungen

Alle Schlüssel mit Standardwert stehen in [CONFIG.md](CONFIG.md#clip-transfer). Kurz:

```json
{
  "clip_send_enabled": false,
  "clip_receive_enabled": false,
  "clip_max_text_kb": 1024,
  "clip_max_image_mb": 20,
  "clip_max_file_mb": 100,
  "clip_inbox_keep_days": 7,
  "clip_inbox_quota_mb": 500,
  "clip_default_peer": "",
  "clip_peers": []
}
```

Ein Peer-Eintrag (`linuxmos-clip setup` schreibt ihn; so sieht er aus):

```json
{"name": "Windows-PC", "host": "192.168.0.50", "user": "alec", "port": 22,
 "key": "~/.ssh/linuxmos_clip_ed25519", "os": "windows"}
```

`name` (Anzeige und `--peer`), `host`, `user`, `port`, `key` (Standard `~/.ssh/linuxmos_clip_ed25519`), `os` (`linux` oder `windows`), optional `ip`: die Adresse, mit der dieser PC **zu dir** sendet, wenn sie nicht gleich `host` ist (damit die Karte „Vom Windows-PC“ sagt statt der IP). Einträge mit ungültigen Angaben (ein Host, der mit `-` beginnt, ein falscher Port …) werden ignoriert.

---

## linuxmos-clip auf der Kommandozeile

```text
linuxmos-clip setup [--name N --host H --user U --port P --os linux|windows --key DATEI
                     --fingerprint SHA256:… --enable-send --receiver-command PFAD]
linuxmos-clip doctor [--offline]
linuxmos-clip send [--peer NAME] [--type text|image|file] [--name NAME] [DATEI]
linuxmos-clip receive --type text|image|file [--name NAME]      (liest stdin; das ruft der Sender auf)
linuxmos-clip receive-ssh                                        (Zwangsbefehl in authorized_keys)
linuxmos-clip apply [ID]        Eintrag per xclip in die Zwischenablage (nur mit xclip; ohne ID: der neueste)
linuxmos-clip list              Eingang anzeigen
linuxmos-clip clean [--all]     alte (oder alle) Einträge löschen; empfangene Dateien bleiben
linuxmos-clip --selftest        den Empfangsweg ohne SSH in einem Wegwerf-Ordner prüfen
```

Beispiele:

```bash
echo "kommt gleich" | linuxmos-clip send --peer Laptop                 # Text von stdin
linuxmos-clip send --peer Laptop ~/Dokumente/bericht.pdf              # eine Datei
linuxmos-clip send --peer Laptop --type image ~/Bilder/foto.png       # ein Bild
linuxmos-clip send --peer Laptop --type text notiz.txt                # eine Textdatei als Text
```

`send` sendet nur, wenn `clip_send_enabled` an ist, und tut es nur auf diesen Aufruf. Die Exit-Codes von `receive` (an den Sender zurückgereicht): 0 ok, 3 Empfang aus, 4 zu groß, 5 Befehl abgelehnt, 6 Inhalt nicht angenommen (leer, kein UTF-8, kein Bild), 7 Eingang voll.

`apply` ist ein Hilfsmittel für Skripte und Terminals; die Insel selbst kopiert per GTK und braucht `xclip` dafür nicht.

---

## Problemlösung

`linuxmos-clip doctor` auf beiden PCs sagt meist schon, was fehlt. Typische Fälle:

| Symptom | Ursache und Abhilfe |
|---|---|
| `Permission denied (publickey)` / „Schlüssel abgelehnt“ | Die Zeile steht nicht (vollständig, in einer Zeile) in `~/.ssh/authorized_keys` des Empfängers, oder die Rechte stimmen nicht (`~/.ssh` 700, Datei 600, Heimordner nicht für andere schreibbar). Bei Verdacht auf dem Empfänger `sudo journalctl -u ssh -n 30` ansehen |
| „Host-Schlüssel unbekannt“ | `linuxmos-clip setup` ausführen und den Fingerabdruck bestätigen |
| `linuxmos-clip: command not found` / „linuxmos-clip fehlt“ | Der Pfad im `command="…"` stimmt nicht: auf dem Empfänger `ls ~/.local/bin/linuxmos-clip`, sonst die Zeile anpassen |
| Verbindung geht, aber nichts erscheint auf der Insel | Auf dem Empfänger ist `clip_receive_enabled` aus (dann kommt „Empfang aus“ zurück), oder die Insel läuft nicht (der Eintrag wartet, `linuxmos-clip list` zeigt ihn) |
| Nichts kommt an, kein Fehler | Das Log der Insel (`LINUXMOS_LOG=debug linuxmos-island`) zeigt `clip: watching …` bei aktivem Empfang |
| Die Karte kommt erst später | Vollbild, offene Insel, laufende Aufnahme oder eine andere Karte halten sie zurück, siehe oben |
| Text hat am Ende zu viel/zu wenig Zeilenumbruch | Der Empfänger entfernt genau einen abschließenden Zeilenumbruch und wandelt `\r\n` um |

---

## Aufräumen und Deinstallieren

- `linuxmos-clip clean` (alte Einträge) bzw. `clean --all` (alle) leert den Eingang. Empfangene Dateien in `~/Downloads/LinuxMos/` bleiben.
- `./uninstall.sh` entfernt das Programm `linuxmos-clip`; `./uninstall.sh --purge` löscht zusätzlich den Eingang, die gespeicherten Peers (sie stehen in `config.json`) und den Schlüssel `~/.ssh/linuxmos_clip_*`. Empfangene Dateien, `known_hosts`-Einträge und die Zeilen in `authorized_keys` der Empfänger bleiben; die Zeilen entfernst du dort von Hand.
