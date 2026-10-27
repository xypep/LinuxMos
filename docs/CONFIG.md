# MosIsland – alle Einstellungen

Datei: `~/.config/linuxmos/island/config.json`. Am bequemsten änderst du sie im **Einstellungsfenster** (Zahnrad oben rechts in der aufgeklappten Insel, Tray → „Einstellungen & Übersicht“, `Ctrl+Alt+H` oder `linuxmos-island --settings`): Der Tab „Funktionen“ hat für jeden Schlüssel unten ein passendes Eingabefeld, das den Wert prüft (ungültig = rot, wird nicht gespeichert). Als Datei öffnest du sie mit dem Link „Config als Datei öffnen“ im Fenster (oder Tray → „Config-Datei öffnen“): Fehlende Schlüssel werden vorher mit ihren Standardwerten eingetragen, damit du alle Optionen siehst.

- **Änderungen gelten sofort.** Die Insel beobachtet die Datei (inotify, kostet nichts) und übernimmt, was sich geändert hat – ohne Neustart. Ausnahme: `language` (wirkt nach einem Neustart der Insel).
- **Ungültiges JSON** (Komma vergessen, Anführungszeichen …) lässt alle bisherigen Werte aktiv. Eine Karte meldet „Config ungültig, alte Werte bleiben“ mit Zeile und Spalte der Fehlerstelle. Solange die Datei kaputt ist, schreibt die Insel nicht hinein, dein Text bleibt unberührt.
- **Fehlt ein Schlüssel**, gilt der Standardwert. **Unbekannte Schlüssel** bleiben erhalten. Ein Wert außerhalb des gültigen Bereichs wird auf die nächste Grenze gesetzt (in der Datei bleibt er stehen, wie du ihn geschrieben hast), ein Wert vom falschen Typ gilt als nicht gesetzt (Standardwert).
- Geschrieben wird atomar (erst eine Temp-Datei, dann umbenannt); die Insel ändert nur die Schlüssel, die sie selbst geändert hat, und lässt den Rest der Datei, wie er gerade ist.

## Allgemein

| Schlüssel | Standard | Bedeutung · gültige Werte |
|---|---|---|
| `city` | `""` | Wetter-Ort (auch `linuxmos-island --set-city`). Ein neuer Ort sucht seine Koordinaten neu |
| `latitude`, `longitude` | `null` | Koordinaten des Orts, trägt die Insel selbst ein |
| `offset_y` | `6` | Abstand zur Top Bar in Pixel |
| `monitor` | `"primary"` | `"primary"`, `"pointer"` (Monitor mit der Maus), eine Zahl von links (`0` = ganz links) oder ein Anschlussname wie `"HDMI-1"` |
| `language` | `"auto"` | `auto` (Systemsprache), `de`, `en` – wirkt nach einem Neustart |
| `compact_when_idle` | `false` | Pille im Leerlauf zu einer dünnen Linie |
| `osd` | `true` | Lautstärke und Helligkeit als Overlay auf der Insel |
| `lyrics_in_pill` | `false` | Aktuelle Lyrics-Zeile in der eingeklappten Pille |

## Maskottchen und Augen-Modus

| Schlüssel | Standard | Bedeutung · gültige Werte |
|---|---|---|
| `mascot` | `true` | Maskottchen im Leerlauf. Ist es aus, bewirkt auch der Augen-Modus nichts |
| `mascot_style` | `"eyes"` | `eyes`, `cat`, `robot`, `blob` |
| `eye_mode` | `true` | **Augen-Modus:** Im Leerlauf wächst die Pille, die Figur wird größer, Temperatur und Akku verschwinden. Hover, Klick oder Eingabe bringen alles sanft (ca. 250 ms) zurück. Läuft sonst etwas in der Pille (Musik, Timer, Dehn-Countdown, Dehn-Symbol) oder kommt eine Karte oder ein Hinweis, geht das vor |
| `eye_mode_scale` | `2.0` | Vergrößerung der Figur: `1.5` bis `3.0` (alles darunter/darüber wird auf die Grenze gesetzt) |

## Dehn-Erinnerung

Gezählt wird nur **aktive** Zeit (Eingabe in der letzten Minute). Mehr dazu in der [README](../README.md#dehn-erinnerung). Eine Erinnerung, die wegen Vollbild oder Fokus-Timer wartet, fällt schon nach `stretch_break_reset_min` ohne Eingabe aus (eine echte Pause hat sie ersetzt); `stretch_idle_skip_min` greift, wenn er kleiner ist oder ein Bildschirm aus/gesperrt ist.

| Schlüssel | Standard | Bedeutung · gültige Werte |
|---|---|---|
| `stretch_enabled` | `true` | Hauptschalter. Aus heißt aus: keine Timer, keine Ticks, keine Abfragen (Log: `disabled, no timers`) |
| `stretch_off_date` | `""` | `"JJJJ-MM-TT"` des Tages, an dem „Heute aus“ gewählt wurde. Die Erinnerung ruht bis Mitternacht. Leer = nicht gesetzt |
| `stretch_interval_min` | `45` | Minuten aktiver Zeit am Stück bis zur Erinnerung: `1`–`600` |
| `stretch_break_reset_min` | `5` | So viele Minuten ohne Eingabe zählen als echte Pause: Die Zählung beginnt von vorn, die Pause ersetzt das Dehnen (keine Karte danach): `1`–`120` |
| `stretch_idle_skip_min` | `30` | Wird eine Erinnerung gezeigt und die letzte Eingabe ist so lange her (oder der Bildschirm ist aus bzw. gesperrt), fällt sie aus; neu gezählt wird ab der Rückkehr: `1`–`600` |
| `stretch_snooze_min` | `5` | Minuten bis zur Karte nach dem ersten „Später“; jedes weitere kürzer (3/5, bei 5 also 3 Minuten): `1`–`60` |
| `stretch_snooze_max` | `2` | Wie oft „Später“ pro Runde geht: `0`–`5`. Danach bleibt „Start“ oder „Überspringen“ |
| `stretch_escalate` | `true` | Wird die Karte ignoriert, kommt sie nach 3 Minuten größer und mit höherem Ton wieder, höchstens dreimal, dann zählt sie als „verpasst“. Aus: kein Wiederkommen, „verpasst“ nach 12 Minuten |
| `stretch_verify_idle` | `true` | „Erledigt“ zählt nur, wenn während des Countdowns kaum Eingabe kam (Leerlaufzeit am Ende ≥ 70 % der Countdown-Dauer). Sonst „Du warst am Rechner, noch mal?“, beim zweiten Mal „unbestätigt“. Aus: „Erledigt“ zählt immer |
| `stretch_long_per_day` | `2` | Jede vierte Erinnerung ist eine aufwendige Übung (`"long": true`), aber höchstens so oft pro Tag: `0`–`10` |
| `stretch_sound` | `true` | Ton bei der Erinnerung, beim Wiederkommen und am Ende des Countdowns |
| `stretch_volume` | `0.5` | Lautstärke des Tons: `0.0` (stumm) bis `1.0` |

**Übungen:** `~/.config/linuxmos/island/stretch_exercises.json` (Tray → Dehnen → „Übungen bearbeiten …“). Beim ersten Start entsteht sie mit der Standardliste; sie wird bei jeder Erinnerung neu gelesen. Eine Liste von Einträgen:

```json
[
 {"name": "Schultern kreisen", "text": "Beide Schultern langsam nach hinten kreisen lassen.", "seconds": 15, "long": false}
]
```

`name` (Titel der Karte), `text` (die Anweisung), `seconds` (Dauer des Countdowns, `5`–`300`; kurze Übungen 10–20, aufwendige 30–60), `long` (`true` = aufwendige Übung). Einträge ohne Namen oder mit unlesbarer Dauer werden übersprungen; ist die Datei kaputt oder leer, gilt die Standardliste (deine Datei bleibt, wie sie ist).

**Statistik:** `~/.local/share/linuxmos/island/stretch.json`, pro Tag erledigt, unbestätigt, später, übersprungen, verpasst; nur die letzten 30 Tage.

## Werkzeuge

Alle vier sind Handgriffe, im Leerlauf kostet keines etwas. Jedes hat einen Schalter; ist er aus, laufen dafür weder Handler noch Timer noch Sperren (im Log steht `clipactions: disabled`, `colorpicker: disabled`, `keepawake: disabled, no lock, no timer`, `pins: disabled, no handlers`).

| Schlüssel | Standard | Bedeutung · gültige Werte |
|---|---|---|
| `clipactions_enabled` | `true` | **Zwischenablage-Aktionen** (Knopf „Aktionen“ am Verlaufseintrag, Hotkey `Ctrl+Alt+Shift+V` für den aktuellen Inhalt): Formatierung entfernen, Tracking aus Links, GROSS/klein/Titel, JSON, URL, Base64, Leerzeichen, Zeilen sortieren, doppelte Zeilen, QR-Code (nur mit `qrencode`). Das Ergebnis ersetzt die Zwischenablage erst nach dem Klick und steht als **neuer** Verlaufseintrag da, das Original bleibt. Als privat markierte Kopien (Passwort-Manager) werden nie verarbeitet |
| `clipactions_tracking_params` | `[]` | Zusätzliche Link-Parameter, die „Tracking aus Links entfernen“ löscht: Namen (`"affil"`) oder Präfixe mit Stern (`"partner_*"`). Eingebaut sind `utm_*`, `fbclid`, `gclid`, `dclid`, `msclkid`, `yclid`, `twclid`, `ttclid`, `mc_eid`, `mc_cid`, `igshid`, `igsh`, `ref_src`, `ref_url`, `_hsenc`, `_hsmi`, `mkt_tok`, `vero_id`, `spm`, `si`, `pk_*`, `hsa_*`, `mtm_*` u. ä.; funktionale Parameter (`id`, `page`, `q`, `ref`, `v`, `t` …) bleiben immer |
| `colorpicker_enabled` | `true` | **Farbpipette** (`Ctrl+Alt+C`, Knopf im Werkzeuge-Tab, Tray). Die Insel blendet sich aus, der Bildschirm wird einmal aufgenommen und als Standbild gezeigt; Klick wählt, `Esc` oder Rechtsklick bricht ab, das Mausrad ändert die Lupe (5–25 Pixel) |
| `colorpicker_format` | `"hex"` | Format der kopierten Farbe: `hex`, `rgb`, `hsl`, `hsv` (andere Werte gelten als `hex`). Die Karte zeigt immer alle vier |
| `colorpicker_history` | `20` | Wie viele der letzten Farben (`~/.local/share/linuxmos/island/colors.json`) bleiben: `1`–`200`; fixierte Farben zählen nicht mit |
| `keepawake_enabled` | `true` | **Wach halten** (`Ctrl+Alt+K`, Schalter im Werkzeuge-Tab, Tray-Häkchen): kein Bildschirmschoner, keine Bildschirmabschaltung, kein automatischer Ruhezustand. Sperren und Ruhezustand von Hand gehen weiter. Wird nie über einen Neustart gemerkt |
| `keepawake_minutes` | `60` | Nach so vielen Minuten schaltet es sich selbst aus (ein einziger Timer auf den Endzeitpunkt, kein Tick); `0` = bis du es ausschaltest: `0`–`1440` |
| `pin_enabled` | `true` | **Fenster anpinnen** (`Ctrl+Alt+P`, Knopf im Werkzeuge-Tab, Tray): das aktive Fenster bleibt im Vordergrund. Nicht anpinnbar sind die Insel selbst, Schreibtisch, Panel/Dock, Menüs und Vollbild-Fenster (eine Karte sagt warum). Aus: alle Pins werden aufgehoben, es hängt kein Handler am Fensterverwalter |
| `pin_release_on_exit` | `true` | Beim Beenden der Insel alle Pins aufheben; `false` lässt die Fenster angepinnt (die Insel merkt sich nichts davon) |

## Hotkeys

Cinnamon, nicht die Insel, lauscht auf die Tasten: `install.sh` legt für jede Funktion ein benutzerdefiniertes Kürzel an, das `linuxmos-island …` aufruft. Das Einstellungsfenster (Tab „Übersicht“, Klick auf das Kürzel) und der Abschnitt `hotkeys` ändern genau diese Kürzel – **sofort, ohne Neustart**.

| Schlüssel | Standard | Bedeutung · gültige Werte |
|---|---|---|
| `hotkeys` | `{}` | Nur das, was vom Standard abweicht: `{"color-picker": "<Primary><Alt>b", "chat": ""}`. Schlüssel ist die ID der Funktion (`linuxmos-island --list-actions`), Wert eine Tastenkombination wie in Cinnamon (`<Primary><Alt>v`, auch `<Control>`, `<Super>`, `<Shift>`); `""` schaltet den Hotkey aus. Ein Eintrag, der verschwindet, setzt den Standard zurück. Ungültige Werte werden ignoriert |

Konflikte (zwei Funktionen auf einer Taste, oder eine Taste, die Cinnamon/Mint schon belegen) meldet das Fenster beim Ändern in Rot mit dem Namen des anderen; speichern geht dann nur mit „Trotzdem speichern“. Prüfen aller Hotkeys auf einmal: `linuxmos-island --check-hotkeys` (Ausgabe 1, wenn es einen Konflikt gibt).

## Gesten auf der Pille

Wirken nur auf die **eingeklappte** Pille. Reine Ereignisbehandlung, kein Timer; mit `gestures_enabled: false` sind die Handler gar nicht erst verbunden (Log: `gestures: disabled, no handlers`). Ein einfacher Linksklick öffnet die Insel immer, er ist keine Geste.

| Schlüssel | Standard | Bedeutung · gültige Werte |
|---|---|---|
| `gestures_enabled` | `true` | Hauptschalter. Aus: Mausrad, Mittel- und Rechtsklick auf der Pille tun nichts |
| `gestures` | `{}` | Aktion je Geste, nur Abweichungen vom Standard. Gesten: `wheel` (Mausrad auf der Pille, Standard `volume_wheel` = Lautstärke ±5 %), `wheel_shift`, `wheel_ctrl`, `wheel_left`, `wheel_right` (Mausrad mit Umschalt/Strg, am linken/rechten Rand – Standard `default` = wie `wheel`), `click_middle` und `click_right` (Standard `expand` = Insel aufklappen), `click_double` (Standard `none`) |

Aktionen: `none`, `default` (nur für die Mausrad-Varianten), `expand`, `volume_wheel`/`volume_up`/`volume_down`, `brightness_wheel`/`brightness_up`/`brightness_down`, `tab_wheel`/`tab_next`/`tab_prev`, `play_pause`, `track_wheel`/`track_next`/`track_prev`, `settings`, `tab:NAME` (z. B. `tab:clipboard`) und `function:ID` (eine Funktion aus dem Register, z. B. `function:keep-awake`). Die `*_wheel`-Aktionen lesen die Richtung des Mausrads und passen nur zu den Mausrad-Gesten, `*_up`/`*_down`/`*_next`/`*_prev` nur zu Klicks. Eine unbekannte oder unpassende Aktion gilt als nicht gesetzt (Standard). Der Doppelklick klappt die Insel mit dem ersten Klick wie immer auf und klappt sie für seine Aktion wieder zu. Wer länger als einen Moment auf der Pille verweilt, klappt sie per Hover auf – dann gehen die Gesten an den aufgeklappten Tab.

## Einstellungsfenster

| Schlüssel | Standard | Bedeutung · gültige Werte |
|---|---|---|
| `overview_intro_seen` | `false` | Die Karte „Neu: Übersicht der Funktionen“ wird einmal nach Installation oder Update gezeigt, danach setzt die Insel das auf `true`. Zum erneuten Zeigen auf `false` stellen |

Fenstergröße und -position merkt sich `~/.config/linuxmos/island/settings-window.json` (getrennt von der `config.json`, damit das Speichern keine Neuladung der Insel auslöst).

## Zwischenablage, Screenshots, Aufnahmen

| Schlüssel | Standard | Bedeutung · gültige Werte |
|---|---|---|
| `clipboard_limit` | `50` | Höchstzahl der Einträge im Verlauf (Pins zählen nicht mit) |
| `clipboard_autodelete_min` | `0` | Nicht angepinnte Einträge nach so vielen Minuten löschen, `0` = nie |
| `screenshot_save` | `true` | Jede Aufnahme zusätzlich als PNG ablegen |
| `screenshot_dir` | `""` | Ordner für Screenshots, leer = `~/Bilder/LinuxMos` bzw. `~/Pictures/LinuxMos` |
| `screenshot_open_editor` | `false` | Markup-Editor sofort nach der Aufnahme öffnen |
| `record_format` | `"mp4"` | `mp4` oder `gif` |
| `record_audio` | `"off"` | `off`, `system`, `mic` (nur MP4) |
| `record_fps` | `30` | `1`–`60` (GIFs höchstens 15) |
| `record_max_min` | `30` | Aufnahme nach so vielen Minuten beenden, `0` = nie |
| `record_dir` | `""` | Ordner für Aufnahmen, leer = `~/Videos/LinuxMos` |
| `ocr_languages` | `"deu+eng"` | tesseract-Sprachen, mit `+` verbunden |
| `ocr_keep_linebreaks` | `false` | Zeilenumbrüche der erkannten Texte behalten |
| `qr_open_links` | `false` | Links aus QR-Codes sofort im Browser öffnen |

## Clip-Transfer

Text, Bilder und Dateien per SSH zwischen PCs, **nur auf Handlung** (Knopf, Hotkey `Ctrl+Alt+Shift+T`, `linuxmos-clip send`); empfangene Inhalte landen im Eingang und im Verlauf, nie automatisch in der Zwischenablage. Einrichtung: [CLIP.md](CLIP.md). Beide Schalter sind auch im Tray-Menü („Clip-Transfer“). Sind beide aus, gibt es keinen Datei-Monitor und nichts wird geladen (Log: `clip: disabled, no monitors`). Die Schlüssel `clip_auto_send` und `clip_autoapply` gibt es nicht.

| Schlüssel | Standard | Bedeutung · gültige Werte |
|---|---|---|
| `clip_send_enabled` | `false` | Senden erlauben (Knopf „An PC senden“, Hotkey, `linuxmos-clip send`) |
| `clip_receive_enabled` | `false` | Empfang: die Insel beobachtet den Eingang (`Gio.FileMonitor`), und `linuxmos-clip receive` nimmt Clips an. Aus: der Empfänger lehnt alles ab |
| `clip_max_text_kb` | `1024` | Größtes Textstück in KB: `1`–`10240`. Der **Empfänger** erzwingt es beim Lesen |
| `clip_max_image_mb` | `20` | Größtes Bild in MB: `1`–`500` |
| `clip_max_file_mb` | `100` | Größte Datei in MB: `1`–`8192` |
| `clip_inbox_keep_days` | `7` | Einträge im Eingang werden nach so vielen Tagen gelöscht (beim Start und beim Eintreffen eines neuen, ohne Timer): `1`–`365`. Empfangene Dateien in `~/Downloads/LinuxMos` bleiben |
| `clip_inbox_quota_mb` | `500` | Der Eingang lehnt neue Clips ab, wenn er (Text, Bilder und die Dateien der vorhandenen Einträge) darüber käme: `10`–`100000` |
| `clip_default_peer` | `""` | Name des Peers für Hotkey und `linuxmos-clip send` ohne `--peer`. Leer: der einzige Peer, sonst fragt der Knopf nach |
| `clip_peers` | `[]` | Liste der Empfänger (`linuxmos-clip setup` trägt sie ein), siehe unten |

Ein Peer-Eintrag:

```json
{"name": "Windows-PC", "host": "192.168.0.50", "user": "alec", "port": 22,
 "key": "~/.ssh/linuxmos_clip_ed25519", "os": "windows"}
```

`name` (höchstens 40 Zeichen, eindeutig), `host` (Adresse oder Name), `user`, `port` (`1`–`65535`, Standard `22`), `key` (Standard `~/.ssh/linuxmos_clip_ed25519`), `os` (`linux` oder `windows`), optional `ip` (Adresse, mit der dieser PC zu dir sendet, falls sie nicht `host` ist; so zeigt die Karte „Vom Windows-PC“). Ein Eintrag, dessen Angaben nicht stimmen (ein Host oder Benutzer, der mit `-` beginnt, Leerzeichen, ein falscher Port), wird ignoriert.

**Dateien:** Eingang `~/.local/share/linuxmos/island/clip-inbox/` (Rechte 700), empfangene Dateien `~/Downloads/LinuxMos/`, Schlüssel `~/.ssh/linuxmos_clip_ed25519`, Stand der gezeigten Einträge `~/.local/share/linuxmos/island/clip-state.json`.

## Benachrichtigungen und Live-Hinweise

| Schlüssel | Standard | Bedeutung · gültige Werte |
|---|---|---|
| `notifications_on_island` | `true` | Benachrichtigungen als Karte auf der Insel (Cinnamons Banner sind solange aus) |
| `notifications_dnd` | `false` | „Nicht stören“ der Insel |
| `notifications_exclude` | `[]` | Liste von App-Namen oder Desktop-IDs, die nie als Karte erscheinen |
| `privacy_indicator` | `true` | Orangener Punkt (Mikrofon) und grüner (Kamera) |
| `vpn_status` | `true` | VPN an/aus melden |
| `vpn_lookup` | `false` | Land und IP des VPN bei ipinfo.io abfragen (externe Anfrage) |
| `downloads_progress` | `true` | Download-Ring auf der Insel |
| `downloads_dir` | `""` | Ordner, den sie beobachtet; leer = Download-Ordner des Systems |

## KI-Chat und Diktat (standardmäßig aus)

| Schlüssel | Standard | Bedeutung · gültige Werte |
|---|---|---|
| `ai_chat` | `false` | Chat-Tab (`Ctrl+Alt+A`) |
| `ai_voice` | `false` | Diktat (`Ctrl+Alt+M`) |
| `ai_voice_autopaste` | `true` | Diktat direkt ins vorige Fenster tippen |
| `ai_base_url` | `""` | Adresse des Servers bis `/v1`, leer = OpenAI |
| `ai_model` | `""` | Chat-Modell, leer = `gpt-4o-mini` |
| `ai_stt_model` | `""` | Modell für Diktat, leer = `whisper-1` |
| `ai_system_prompt` | `""` | Ersetzt die kurze Standardanweisung |
| `ai_history` | `20` | Nachrichten, die mitgeschickt werden (`≥ 1`) |
| `ai_voice_language` | `""` | Sprachcode wie `de`, leer = erkennen lassen |
| `ai_voice_max_s` | `120` | Längste Diktat-Aufnahme in Sekunden |

Der API-Key steht nie in dieser Datei, sondern im Schlüsselbund.

## Command Bar

| Schlüssel | Standard | Bedeutung · gültige Werte |
|---|---|---|
| `command_bar_engine` | `"duckduckgo"` | `duckduckgo`, `google`, `startpage`, `ecosia`, `bing`, `brave` oder eine URL mit `%s` |
| `command_bar_files` | `true` | Dateien im Home-Ordner suchen |
| `command_bar_currency` | `true` | Währungen umrechnen (EZB-Kurse von frankfurter.dev) |

## Wasser

| Schlüssel | Standard | Bedeutung · gültige Werte |
|---|---|---|
| `water_goal_ml` | `2000` | Tagesziel (500–6000 im Wasser-Tab) |
| `water_portion_ml` | `250` | Portion pro Klick (50–2000 im Wasser-Tab) |
| `water_reminders` | `true` | Erinnerungen an |
| `water_start`, `water_end` | `"09:00"`, `"21:00"` | Aktive Zeit, `HH:MM` |
| `water_interval_min` | `60` | Abstand der Erinnerungen, mindestens `15` |

## Debug-Schalter beim Start

Keine Config-Schlüssel, sondern Kommandozeile (gelten nur für diesen Start):

| Aufruf | Wirkung |
|---|---|
| `linuxmos-island --list-actions` | Alle Funktionen des Registers als Tabelle: ID, Name, Kategorie, Hotkey, Schalter, Aktion (mit laufender Insel auch der Status); `--markdown` gibt die Hotkey-Tabelle fürs README aus |
| `linuxmos-island --action ID` | Löst eine Funktion aus dem Register aus (z. B. `color-picker`, `keep-awake`, `pin-window`, `clip-actions`); braucht die laufende Insel |
| `linuxmos-island --check-hotkeys` | Konfliktbericht: Hotkeys untereinander und gegen Cinnamons Kürzel und die Mint-Standards (Ausgabe 1 bei Konflikt) |
| `linuxmos-island --settings [--tab overview\|gestures\|functions]` | Einstellungsfenster (eigener Prozess, geht auch ohne laufende Insel) |
| `linuxmos-island --stretch-now` | Zeigt sofort eine Dehn-Karte (auch bei laufender Insel) |
| `linuxmos-island --stretch-test` | Intervall 1 Minute, Takt 5 s, Pause nach 20 s, Überspringen nach 40 s, „Später“ 10 s/6 s, Wiederkommen nach 15 s |
| `linuxmos-island --force-idle` | Startet im Leerlauf (Maskottchen bzw. Augen-Modus ohne Warten); Hover oder Klick beendet es |
| `LINUXMOS_LOG=debug linuxmos-island` | Log mit jeder Messung (Standard: `info`) |
