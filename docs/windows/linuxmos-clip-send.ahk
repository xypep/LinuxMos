; linuxmos-clip-send.ahk – AutoHotkey v2: die aktuelle Zwischenablage (Text) an den Linux-PC senden.
;
; UNGETESTET (Windows-Seite, "Best Effort"). Gesendet wird NUR, wenn du die Tastenkombination drückst:
; kein Watcher, kein Timer, kein automatisches Senden.
;
; Einrichtung: AutoHotkey v2 installieren, Werte unten anpassen, Datei doppelklicken (oder in den Autostart).
; Der Schlüssel linuxmos_clip_ed25519 und die Zeile in authorized_keys des Linux-PCs: docs/CLIP-WINDOWS.md.
#Requires AutoHotkey v2.0
#SingleInstance Force

LinuxUser := "alec"                       ; Benutzer auf dem Linux-PC
LinuxHost := "linux-pc"                   ; Name oder IP des Linux-PCs
KeyFile   := EnvGet("USERPROFILE") "\.ssh\linuxmos_clip_ed25519"

; Strg+Alt+Umschalt+T. Passwörter aus Passwort-Managern gehören nicht hierher: nur senden, was du senden willst.
^!+t:: {
    text := A_Clipboard
    if (Trim(text) = "") {
        Note("Zwischenablage ist leer (nur Text wird gesendet)")
        return
    }
    ; Per Datei auf stdin: Bytes bleiben Bytes (keine PowerShell-Pipe, keine Codepage-Umwege)
    tmp := A_Temp "\linuxmos-clip-" A_TickCount ".txt"
    file := FileOpen(tmp, "w", "UTF-8-RAW")
    file.Write(text)
    file.Close()
    ssh := 'ssh -o BatchMode=yes -o ConnectTimeout=5 -o StrictHostKeyChecking=yes -o IdentitiesOnly=yes'
        . ' -i "' KeyFile '" ' LinuxUser '@' LinuxHost ' "linuxmos-clip receive --type text"'
    ; cmd /c "<alles>": die äußeren Anführungszeichen schützt cmd, die inneren gehören zu ssh
    code := RunWait(A_ComSpec ' /c "' ssh ' < "' tmp '""', , "Hide")
    try FileDelete(tmp)
    Note(code = 0 ? "Gesendet an " LinuxHost : "Nicht gesendet (Code " code "): ssh-Fehler, Limit oder PC aus")
}

Note(message) {
    ToolTip(message)
    SetTimer(() => ToolTip(), -3000)
}
