# Clip-Transfer mit Windows (ungetestet)

> [!WARNING]
> **Nichts auf dieser Seite konnte auf einem echten Windows geprüft werden.** Die Linux-Seite (Empfang, Senden, Schlüssel, Limits, Sicherheit) ist getestet, die Windows-Seite ist „Best Effort“: Befehle und Scripts sind sorgfältig geschrieben, aber nie gelaufen. Probiere es erst mit unwichtigen Inhalten aus, und melde Fehler. Die Windows-Island gibt es noch nicht; sie soll später (V2.1) einen eigenen Sender und Empfänger bekommen.

Grundsatz wie auf Linux: **Gesendet wird nur, wenn du es auslöst** (Befehl, Tastenkombination). Empfangene Inhalte landen in einem Ordner, **nie automatisch in der Zwischenablage**.

Die Einrichtung der Schlüssel ist dieselbe wie in [CLIP.md](CLIP.md): ein ed25519-Schlüssel nur für Clips, und auf dem Empfänger eine Zeile in `authorized_keys` mit `restrict,command="…"`.

Inhalt: [Windows → Linux](#windows--linux) · [Linux → Windows](#linux--windows)

---

## Windows → Linux

Der OpenSSH-Client ist in Windows 10/11 eingebaut (`ssh -V` in PowerShell prüft es).

### 1. Schlüssel (einmal, in PowerShell)

```powershell
ssh-keygen -t ed25519 -N '""' -C "linuxmos-clip@windows" -f "$env:USERPROFILE\.ssh\linuxmos_clip_ed25519"
Get-Content "$env:USERPROFILE\.ssh\linuxmos_clip_ed25519.pub"
```

Die ausgegebene Zeile (`ssh-ed25519 AAAA… linuxmos-clip@windows`) kommt **auf dem Linux-PC** in `~/.ssh/authorized_keys`, mit dem Vorsatz, der den Schlüssel auf Clips beschränkt:

```text
restrict,command="~/.local/bin/linuxmos-clip receive-ssh" ssh-ed25519 AAAA… linuxmos-clip@windows
```

Auf dem Linux-PC muss der Empfang an sein (Tray → Clip-Transfer → Clip-Empfang) und der SSH-Server laufen (`linuxmos-clip doctor` prüft das). Den Host-Schlüssel des Linux-PCs einmal bewusst bestätigen – hier ist ein Gang ins Terminal nötig, weil später mit `StrictHostKeyChecking=yes` gearbeitet wird:

```powershell
ssh -i "$env:USERPROFILE\.ssh\linuxmos_clip_ed25519" alec@linux-pc
```

Es erscheint der Fingerabdruck; vergleiche ihn mit dem auf dem Linux-PC (`ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub`) und tippe nur bei Übereinstimmung `yes`. Danach meldet der Linux-PC „Abgelehnt: dieser Schlüssel darf nur Clips abliefern“ und trennt – das ist richtig so, ein Login ist mit diesem Schlüssel nicht möglich.

### 2. Text senden

```powershell
Get-Clipboard | ssh -i $env:USERPROFILE\.ssh\linuxmos_clip_ed25519 alec@linux-pc "linuxmos-clip receive --type text"
```

Hinweise (Windows PowerShell 5.1): Umlaute gehen nur durch die Pipe, wenn vorher `$OutputEncoding = [System.Text.UTF8Encoding]::new($false)` gesetzt wird (PowerShell 7 braucht das nicht). `Get-Clipboard -Raw` schickt den Text als Ganzes statt zeilenweise. Ein einzelner Zeilenumbruch am Ende (den PowerShell anhängt) und `\r\n` werden vom Empfänger zu `\n` bzw. entfernt.

### 3. Datei senden

**Binärdaten niemals durch PowerShell-Pipes schicken** (PowerShell wandelt sie in Text um und zerstört sie). Der Weg über `cmd` reicht die Datei unverändert an ssh weiter:

```bat
cmd /c "ssh -i %USERPROFILE%\.ssh\linuxmos_clip_ed25519 alec@linux-pc ""linuxmos-clip receive --type file --name datei.pdf"" < datei.pdf"
```

Der Dateiname hinter `--name` darf nur `A–Z a–z 0–9 . _ - Leerzeichen` enthalten (bei Leerzeichen in einfache Anführungszeichen setzen: `--name 'mein bericht.pdf'`). Für ein Bild nimmst du `--type image`.

### 4. Mit einer Tastenkombination (AutoHotkey v2)

[`windows/linuxmos-clip-send.ahk`](windows/linuxmos-clip-send.ahk) sendet bei **Strg+Alt+Umschalt+T** den Text der Zwischenablage an den Linux-PC (Benutzer, Adresse und Schlüsseldatei oben im Script anpassen). Es läuft **nur auf deinen Tastendruck**, hat keinen Timer und keinen Watcher. Gib damit keine Passwörter aus einem Passwort-Manager frei: Auf Windows markiert nicht jeder Manager seine Kopien so, dass ein Script es erkennen könnte.

---

## Linux → Windows

Der Linux-PC sendet wie immer mit `ssh`. Auf Windows muss dafür der **optionale OpenSSH-Server** laufen und ein kleines Script die Clips annehmen.

### 1. OpenSSH-Server unter Windows einrichten (PowerShell als Administrator)

```powershell
# Installieren (Windows 10/11: Einstellungen → Optionale Features geht auch)
Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0

# Starten und beim Anmelden automatisch starten
Start-Service sshd
Set-Service -Name sshd -StartupType Automatic

# Firewall: Windows legt die Regel meist selbst an; sonst
if (-not (Get-NetFirewallRule -Name 'OpenSSH-Server-In-TCP' -ErrorAction SilentlyContinue)) {
    New-NetFirewallRule -Name 'OpenSSH-Server-In-TCP' -DisplayName 'OpenSSH Server (sshd)' `
        -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22
}
```

Wenn der PC nur im Heimnetz stehen soll: Die Regel nur für das **private** Profil und das lokale Netz erlauben (`-Profile Private -RemoteAddress LocalSubnet`). Der Dienst nimmt sonst Verbindungen aus jedem Netz an, in dem der Rechner hängt.

### 2. Den Clip-Schlüssel eintragen

Auf dem **Linux-PC** `linuxmos-clip setup` ausführen (`--os windows`); es gibt die Schlüsselzeile aus. Auf Windows kommt sie in eine der beiden Dateien, je nachdem, ob das Konto Administrator ist:

- **Kein Administrator:** `C:\Users\<name>\.ssh\authorized_keys`
- **Administrator-Konto:** `C:\ProgramData\ssh\administrators_authorized_keys`, und dort müssen die Rechte stimmen, sonst ignoriert sshd die Datei:

  ```powershell
  icacls.exe "C:\ProgramData\ssh\administrators_authorized_keys" /inheritance:r /grant "Administrators:F" /grant "SYSTEM:F"
  ```

Die Zeile bekommt den Vorsatz `restrict` und als Zwangsbefehl das Empfänger-Script (Pfad anpassen):

```text
restrict,command="powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\Users\alec\linuxmos-clip-receive.ps1" ssh-ed25519 AAAA… linuxmos-clip@linux-pc
```

Damit kann der Schlüssel auch auf Windows nur Clips abliefern.

### 3. Das Empfänger-Script

[`windows/linuxmos-clip-receive.ps1`](windows/linuxmos-clip-receive.ps1) nach `C:\Users\<name>\linuxmos-clip-receive.ps1` kopieren. Es macht dasselbe wie `linuxmos-clip receive`:

- Der Befehl (`SSH_ORIGINAL_COMMAND`) wird gegen dieselbe strenge Regel geprüft, alles andere wird abgelehnt (Exit-Code 5); nichts davon läuft durch eine Shell.
- Der Clip wird von stdin in eine temporäre Datei gelesen, die Limits (Text 1 MB, Bild 20 MB, Datei 100 MB, Eingang 500 MB) gelten schon beim Lesen; zu große Clips werden abgebrochen und aufgeräumt.
- Dateinamen werden bereinigt (kein Pfad, kein `..`, kein Punkt am Anfang, keine Steuerzeichen, reservierte Windows-Namen), gleichnamige Dateien bekommen eine Nummer, nichts wird überschrieben.
- Ablage: Text und Bilder in `%LOCALAPPDATA%\LinuxMos\clip-inbox\` (`<id>.txt`, `<id>.png` …), Dateien in `%USERPROFILE%\Downloads\LinuxMos\`. Zu jedem Eintrag liegt eine `<id>.json` mit Typ, Name, Größe, Absender und Zeit daneben (dasselbe Format wie unter Linux; die Windows-Island soll sie später lesen).
- **Es setzt nichts in die Zwischenablage und öffnet nichts.** Einen Text holst du dir aus der `.txt`-Datei, z. B. `Get-Content (gci "$env:LOCALAPPDATA\LinuxMos\clip-inbox\*.txt" | sort LastWriteTime | select -Last 1) -Raw | Set-Clipboard`.
- Einträge im Eingangsordner, die älter als 7 Tage sind, werden beim nächsten Empfang gelöscht (Dateien in Downloads bleiben).

### 4. Auf dem Linux-PC senden

Wie in [CLIP.md](CLIP.md): `linuxmos-clip setup` mit `--os windows` (oder in der Config `"os": "windows"`), dann Knopf, Hotkey oder `linuxmos-clip send`. Der Peer sieht so aus:

```json
{"name": "Windows-PC", "host": "192.168.0.50", "user": "alec", "port": 22,
 "key": "~/.ssh/linuxmos_clip_ed25519", "os": "windows"}
```

Beim ersten Mal zeigt `setup` den Fingerabdruck des Windows-Hosts (`ssh-keyscan`), den du mit dem von Windows vergleichst:

```powershell
ssh-keygen -lf C:\ProgramData\ssh\ssh_host_ed25519_key.pub
```

### Bekannte Unsicherheiten (nicht geprüft)

- Ob die `restrict`-Option und der Zwangsbefehl mit deiner Version von Win32-OpenSSH wie beschrieben zusammenspielen (neuere Versionen ab 8.x sollten es).
- Ob `[Console]::OpenStandardInput()` bei einem Zwangsbefehl in `powershell.exe -File` Binärdaten unverändert liefert (es sollte).
- Dass der Empfangsweg `linuxmos-clip doctor` auf dem Linux-Sender zufriedenstellt: `doctor` schickt einen leeren Text und erwartet den Exit-Code 6 („leer“) – das Script antwortet mit 6.
- Die Quota des Scripts zählt nur den Eingangsordner, nicht `Downloads\LinuxMos`.
