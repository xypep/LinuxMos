# linuxmos-clip-receive.ps1 – Empfänger für Clips von LinuxMos (Linux -> Windows)
#
# UNGETESTET: Die Windows-Seite von LinuxMos konnte nicht auf einem echten Windows geprüft werden
# ("Best Effort"). Bitte erst mit unwichtigen Inhalten ausprobieren und Fehler melden.
#
# sshd startet dieses Script als Zwangsbefehl der Clip-Zeile in administrators_authorized_keys bzw.
# authorized_keys (siehe docs/CLIP-WINDOWS.md). Es liest den Clip von stdin und legt ihn in einen
# Eingangsordner. Es setzt NICHTS in die Zwischenablage und öffnet nichts.
#
#   Text, Bilder   %LOCALAPPDATA%\LinuxMos\clip-inbox\<id>.txt / <id>.png ...   plus <id>.json (zuletzt angelegt)
#   Dateien        %USERPROFILE%\Downloads\LinuxMos\<name>                        plus <id>.json im Eingangsordner
#
# Exit-Codes wie bei linuxmos-clip: 0 ok, 1 Fehler, 4 zu groß, 5 Befehl abgelehnt, 6 Inhalt nicht angenommen,
# 7 Eingang voll. Die Limits unten entsprechen den Standardwerten von linuxmos-clip.

$ErrorActionPreference = 'Stop'

$MaxText  = 1MB
$MaxImage = 20MB
$MaxFile  = 100MB
$Quota    = 500MB      # zählt nur den Eingangsordner (Text, Bilder, Einträge), nicht Downloads\LinuxMos
$KeepDays = 7

$Inbox = Join-Path $env:LOCALAPPDATA 'LinuxMos\clip-inbox'
$Files = Join-Path $env:USERPROFILE 'Downloads\LinuxMos'

function Fail([int]$Code, [string]$Message) {
    [Console]::Error.WriteLine($Message)
    exit $Code
}

# 1. Nur dieser eine Befehl ist erlaubt (SSH_ORIGINAL_COMMAND ist Text, nie ein Befehl, der ausgeführt wird)
$command = $env:SSH_ORIGINAL_COMMAND
$pattern = '^linuxmos-clip receive --type (text|image|file)(?: --name (?:''([A-Za-z0-9._ \-]{1,120})''|([A-Za-z0-9._\-]{1,120})))?\z'
$match = [regex]::Match([string]$command, $pattern)
if (-not $match.Success) {
    Fail 5 'Abgelehnt: dieser Schlüssel darf nur Clips abliefern (receive --type text|image|file)'
}
$kind = $match.Groups[1].Value
$requestedName = if ($match.Groups[2].Success) { $match.Groups[2].Value } else { $match.Groups[3].Value }

# 2. Ordner und Aufräumen (alte Einträge raus, Dateien in Downloads bleiben)
New-Item -ItemType Directory -Force -Path $Inbox | Out-Null
$cutoff = (Get-Date).AddDays(-$KeepDays)
Get-ChildItem -LiteralPath $Inbox -Force -File | Where-Object { $_.LastWriteTime -lt $cutoff } |
    Remove-Item -Force -ErrorAction SilentlyContinue
$used = (Get-ChildItem -LiteralPath $Inbox -Force -File | Measure-Object -Property Length -Sum).Sum
if ($null -eq $used) { $used = 0 }
$room = $Quota - $used
if ($room -le 0) { Fail 7 'Eingang voll' }

# 3. Dateinamen bereinigen: kein Pfad, kein "..", kein Punkt am Anfang, keine Steuerzeichen
function Get-SafeName([string]$Name) {
    if (-not $Name) { return 'datei' }
    $Name = ($Name -replace '\\', '/').Split('/')[-1]
    $Name = [regex]::Replace($Name, '[\x00-\x1f\x7f-\x9f<>:"|?*]', '_')
    $Name = [regex]::Replace($Name, '\.{2,}', '.').Trim(' ', '.')
    if ($Name.Length -gt 120) { $Name = $Name.Substring(0, 120) }
    if (-not $Name) { return 'datei' }
    # reservierte Windows-Namen (CON, NUL, COM1 ...)
    if ($Name -match '^(CON|PRN|AUX|NUL|COM[0-9]|LPT[0-9])(\..*)?$') { return '_' + $Name }
    return $Name
}

$limit = switch ($kind) { 'text' { $MaxText } 'image' { $MaxImage } default { $MaxFile } }
$id = '{0:D13}-{1}' -f [int64][DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds(), (Get-Random -Maximum 16777215).ToString('x6')
$targetDir = if ($kind -eq 'file') { New-Item -ItemType Directory -Force -Path $Files | Select-Object -ExpandProperty FullName } else { $Inbox }
$tmp = Join-Path $targetDir ('.clip-tmp-' + [guid]::NewGuid().ToString('N'))

# 4. stdin in eine temporäre Datei lesen, das Limit gilt schon beim Lesen
$stdin = [Console]::OpenStandardInput()
$buffer = New-Object byte[] 65536
$total = 0L
$head = New-Object byte[] 16
$headLength = 0
$stream = [System.IO.File]::Open($tmp, [System.IO.FileMode]::CreateNew, [System.IO.FileAccess]::Write)
try {
    while (($n = $stdin.Read($buffer, 0, $buffer.Length)) -gt 0) {
        if ($headLength -lt 16) {
            $take = [Math]::Min(16 - $headLength, $n)
            [Array]::Copy($buffer, 0, $head, $headLength, $take)
            $headLength += $take
        }
        $total += $n
        if ($total -gt $limit) { $stream.Close(); Remove-Item -Force $tmp; Fail 4 'Zu groß (Limit des Empfängers)' }
        if ($total -gt $room) { $stream.Close(); Remove-Item -Force $tmp; Fail 7 'Eingang voll' }
        $stream.Write($buffer, 0, $n)
    }
    $stream.Flush()
} catch {
    $stream.Close()
    Remove-Item -Force $tmp -ErrorAction SilentlyContinue
    throw
}
$stream.Close()
if ($total -eq 0) { Remove-Item -Force $tmp; Fail 6 'Leerer Clip' }

# 5. Prüfen, ob es ist, was es sein soll, dann an den Platz bewegen (nie etwas überschreiben)
$extension = $null
if ($kind -eq 'text') {
    try {
        [void](New-Object System.Text.UTF8Encoding($false, $true)).GetString([System.IO.File]::ReadAllBytes($tmp))
    } catch {
        Remove-Item -Force $tmp
        Fail 6 'Kein gültiger UTF-8-Text'
    }
    $extension = 'txt'
} elseif ($kind -eq 'image') {
    $hex = ($head[0..11] | ForEach-Object { '{0:x2}' -f $_ }) -join ''
    if     ($hex.StartsWith('89504e470d0a1a0a'))            { $extension = 'png' }
    elseif ($hex.StartsWith('ffd8ff'))                       { $extension = 'jpg' }
    elseif ($hex.StartsWith('474946383761') -or $hex.StartsWith('474946383961')) { $extension = 'gif' }
    elseif ($hex.StartsWith('424d'))                         { $extension = 'bmp' }
    elseif ($hex.StartsWith('52494646') -and $hex.Substring(16, 8) -eq '57454250') { $extension = 'webp' }
    else { Remove-Item -Force $tmp; Fail 6 'Kein Bild (PNG, JPEG, GIF, BMP oder WebP erwartet)' }
}

$entry = [ordered]@{
    id     = $id
    type   = $kind
    size   = $total
    sender = (([string]$env:SSH_CONNECTION) -split ' ')[0]
    time   = [Math]::Round(([DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds() / 1000.0), 3)
}
if ($kind -eq 'file') {
    $safe = Get-SafeName $requestedName
    $base = [System.IO.Path]::GetFileNameWithoutExtension($safe)
    $ext = [System.IO.Path]::GetExtension($safe)
    $final = $null
    for ($i = 0; $i -lt 1000 -and -not $final; $i++) {
        $candidate = if ($i -eq 0) { $safe } else { "$base ($i)$ext" }
        try {
            [System.IO.File]::Move($tmp, (Join-Path $Files $candidate))     # schlägt fehl, wenn es den Namen schon gibt
            $final = $candidate
        } catch [System.IO.IOException] { }
    }
    if (-not $final) { Remove-Item -Force $tmp -ErrorAction SilentlyContinue; Fail 1 'Zu viele gleichnamige Dateien' }
    $entry.name = $final
    $entry.path = Join-Path $Files $final
} else {
    $payload = "$id.$extension"
    [System.IO.File]::Move($tmp, (Join-Path $Inbox $payload))
    $entry.name = ''
    $entry.payload = $payload
}

# 6. Der Eintrag zuletzt: er ist das Zeichen, dass alles vollständig da ist
$entryTmp = Join-Path $Inbox ('.tmp-' + [guid]::NewGuid().ToString('N') + '.json')
[System.IO.File]::WriteAllText($entryTmp, ($entry | ConvertTo-Json -Compress), (New-Object System.Text.UTF8Encoding($false)))
[System.IO.File]::Move($entryTmp, (Join-Path $Inbox "$id.json"))
[Console]::Out.WriteLine("Empfangen: $kind ($total Bytes)")
exit 0
