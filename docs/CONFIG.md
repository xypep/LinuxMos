# MosIsland – alle Einstellungen

Datei: `~/.config/linuxmos/island/config.json`. Am einfachsten öffnest du sie mit dem **Zahnrad** oben rechts in der aufgeklappten Insel (oder Tray → „Einstellungen öffnen“): Fehlende Schlüssel werden vorher mit ihren Standardwerten eingetragen, damit du alle Optionen siehst.

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
| `linuxmos-island --stretch-now` | Zeigt sofort eine Dehn-Karte (auch bei laufender Insel) |
| `linuxmos-island --stretch-test` | Intervall 1 Minute, Takt 5 s, Pause nach 20 s, Überspringen nach 40 s, „Später“ 10 s/6 s, Wiederkommen nach 15 s |
| `linuxmos-island --force-idle` | Startet im Leerlauf (Maskottchen bzw. Augen-Modus ohne Warten); Hover oder Klick beendet es |
| `LINUXMOS_LOG=debug linuxmos-island` | Log mit jeder Messung (Standard: `info`) |
