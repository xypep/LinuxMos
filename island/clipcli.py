"""linuxmos-clip: send and receive clips (text, images, files) between PCs over SSH.

    setup        make a key, note a peer, confirm its fingerprint, print the line for the receiver's authorized_keys
    doctor       check everything on the way (ssh, key, peer, sshd, inbox)
    send         send text (stdin) or a file to a peer – only when you call it
    receive      read a clip from stdin into the inbox (what the sender's ssh call runs)
    receive-ssh  the forced command of the restricted key: checks SSH_ORIGINAL_COMMAND, then does `receive`
    apply        copy an inbox entry to the clipboard (needs xclip)
    list, clean  show or empty the inbox
    --selftest   run the receiving side locally without ssh

No GTK in here: the receiving side also runs on a machine without a screen. Texts are German (they reach
the island's cards and a terminal), identifiers and comments English.
"""

import argparse
import os
import signal
import socket
import stat
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from island.services import clipcore as core
from island.services.clipcore import (EXIT_BAD_CONTENT, EXIT_DISABLED, EXIT_FAILED, EXIT_FULL, EXIT_OK,
                                      EXIT_REJECTED, EXIT_TOO_LARGE, EXIT_USAGE, ClipError, human)
from island.storage import Config

SSH_DIR = Path.home() / ".ssh"
RECEIVER_COMMAND = "~/.local/bin/linuxmos-clip"
GUIDE = "docs/CLIP.md"


def say(text="", file=None):
    print(text, file=file or sys.stdout, flush=True)


def fail(text, code=EXIT_FAILED):
    say(text, sys.stderr)
    return code


def mark(level, text):
    say(f"  {'✔' if level == 'ok' else '✘' if level == 'bad' else '!'} {text}")


# =============================================================================
# receive / receive-ssh
# =============================================================================
def _sender_address():
    """The sending PC's address as sshd saw it (SSH_CONNECTION = client ip, client port, server ip, server port)."""
    return (os.environ.get("SSH_CONNECTION") or "").split(" ")[0]


def _on_signal(_signum, _frame):
    raise SystemExit(EXIT_FAILED)     # unwinds through receive(), which removes its temporary files


def do_receive(kind, name):
    cfg = Config.load()
    if not cfg.flag("clip_receive_enabled"):
        return fail("Empfang ist ausgeschaltet (clip_receive_enabled in config.json oder Tray → Clip-Empfang)",
                    EXIT_DISABLED)
    signal.signal(signal.SIGHUP, _on_signal)
    signal.signal(signal.SIGTERM, _on_signal)
    try:
        entry = core.receive(sys.stdin.buffer, kind, name, core.default_paths(), core.Limits.from_config(cfg),
                             sender=_sender_address())
    except ClipError as error:
        return fail(error.message, error.code)
    except OSError as error:
        return fail(f"Speichern fehlgeschlagen: {error.strerror or error}")
    say(f"Empfangen: {kind} ({human(entry['size'])})")
    return EXIT_OK


def cmd_receive(args):
    return do_receive(args.type, args.name)


def cmd_receive_ssh(_args):
    """Forced command: SSH_ORIGINAL_COMMAND is data. It is matched against one regex and never run by a shell."""
    parsed = core.parse_command(os.environ.get("SSH_ORIGINAL_COMMAND"))
    if parsed is None:
        return fail("Abgelehnt: dieser Schlüssel darf nur Clips abliefern (receive --type text|image|file)",
                    EXIT_REJECTED)
    return do_receive(*parsed)


# =============================================================================
# send
# =============================================================================
def _find_peer(cfg, wanted):
    found = core.peers(cfg)
    if wanted:
        for peer in found:
            if peer["name"].lower() == wanted.lower():
                return peer, None
        return None, f"Kein Peer mit dem Namen „{wanted}“" + (
            " (vorhanden: " + ", ".join(p["name"] for p in found) + ")" if found else " – erst `linuxmos-clip setup`")
    peer = core.default_peer(cfg)
    if peer is None:
        return None, ("Kein Peer eingerichtet – `linuxmos-clip setup`" if not found
                      else "Mehrere Peers: --peer NAME angeben oder clip_default_peer setzen")
    return peer, None


def cmd_send(args):
    cfg = Config.load()
    if not cfg.flag("clip_send_enabled"):
        return fail("Senden ist ausgeschaltet (clip_send_enabled in config.json oder Tray → Clip-Senden)")
    if not core.ssh_available():
        return fail("ssh fehlt: sudo apt install openssh-client")
    peer, problem = _find_peer(cfg, args.peer)
    if problem:
        return fail(problem)
    if (problem := core.key_problem(peer)):
        return fail(problem)
    limits = core.Limits.from_config(cfg)
    kind = args.type or ("file" if args.file else "text")
    name = args.name or (Path(args.file).name if args.file else None)
    stdin, data = None, None
    if args.file:
        _size, problem = core.check_sendable(args.file, limits, kind)
        if problem:
            return fail(problem)
        if kind == "text":
            data = Path(args.file).read_bytes()
        else:
            stdin = open(args.file, "rb")
    elif sys.stdin.isatty():
        return fail("Nichts zu senden: Text über stdin (echo hallo | linuxmos-clip send) oder eine Datei angeben")
    elif kind == "text":
        data = sys.stdin.buffer.read(limits.text + 1)
        if len(data) > limits.text:
            return fail(f"Zu groß: über {human(limits.text)} (Limit clip_max_text_kb)")
    else:
        stdin = sys.stdin.buffer      # streamed; the receiver enforces its limit while reading
    if data is not None and not data.strip():
        return fail("Nichts zu senden: der Text ist leer")
    argv = core.ssh_argv(peer, core.remote_command(kind, name))
    try:
        done = subprocess.run(argv, input=data, stdin=None if data is not None else stdin,
                              stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    except OSError as error:
        return fail(f"ssh lässt sich nicht starten: {error}")
    finally:
        if stdin not in (None, sys.stdin.buffer):
            stdin.close()
    if done.returncode == 0:
        say(f"Gesendet an {peer['name']}")
        return EXIT_OK
    _short, long = core.explain_failure(done.returncode, done.stderr.decode("utf-8", "replace"), peer)
    return fail(f"Nicht gesendet an {peer['name']}: {long}")


# =============================================================================
# apply / list / clean
# =============================================================================
MIME = {"png": "image/png", "jpg": "image/jpeg", "gif": "image/gif", "bmp": "image/bmp", "webp": "image/webp"}


def _pick(entries, wanted):
    if not wanted:      # the newest one that can go on a clipboard
        copyable = [e for e in entries if e["type"] != "file"]
        return copyable[-1] if copyable else None
    matches = [e for e in entries if e["id"].startswith(wanted)]
    exact = [e for e in matches if e["id"] == wanted]
    return exact[0] if exact else matches[0] if len(matches) == 1 else None


def cmd_apply(args):
    if not core.have("xclip"):
        return fail("xclip fehlt: sudo apt install xclip (die MosIsland braucht es nicht, sie kopiert selbst)")
    paths = core.default_paths()
    entries = core.list_entries(paths)
    entry = _pick(entries, args.id)
    if entry is None:
        return fail("Kein passender Eintrag (linuxmos-clip list zeigt die IDs)")
    if entry["type"] == "file":
        say(f"Dateien werden nie kopiert, sie liegen hier: {entry['path']}")
        return EXIT_OK
    source = core.payload_path(entry, paths)
    try:
        if entry["type"] == "text":
            argv, data = ["xclip", "-selection", "clipboard", "-i"], source.read_bytes()
        else:
            argv, data = ["xclip", "-selection", "clipboard", "-t", MIME[source.suffix[1:]], "-i", str(source)], None
        # xclip stays in the background to serve the selection: do not wait for its output pipes
        done = subprocess.run(argv, input=data, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError as error:
        return fail(f"Kopieren fehlgeschlagen: {error}")
    if done.returncode != 0:
        return fail("xclip hat den Inhalt nicht angenommen (läuft ein X11-Display? DISPLAY gesetzt?)")
    say(f"In die Zwischenablage kopiert: {entry['id']} ({entry['type']})")
    return EXIT_OK


def _describe(entry, paths):
    if entry["type"] == "text":
        first = core.read_text(entry, paths).strip().splitlines()[:1]
        return (first[0][:50] if first else "") + f"  ({entry.get('chars', '?')} Zeichen)"
    return entry.get("name") or "Bild"


def cmd_list(_args):
    paths = core.default_paths()
    entries = core.list_entries(paths)
    if not entries:
        say("Der Eingang ist leer.")
        return EXIT_OK
    now = time.time()
    for entry in entries:
        age = max(0, int(now - entry["time"]))
        ago = f"{age // 86400} d" if age >= 86400 else f"{age // 3600} h" if age >= 3600 else f"{age // 60} min"
        say(f"{entry['id']}  {entry['type']:<5} {human(entry['size']):>9}  vor {ago:<6} {entry['sender'] or 'lokal':<15} "
            f"{_describe(entry, paths)}")
    return EXIT_OK


def cmd_clean(args):
    cfg = Config.load()
    paths = core.default_paths()
    removed = core.cleanup(paths, core.Limits.from_config(cfg).keep_days, everything=args.all)
    say(f"{removed} Einträge entfernt (empfangene Dateien in {paths.files} bleiben)")
    return EXIT_OK


# =============================================================================
# setup
# =============================================================================
def _ask(question, default=""):
    if not sys.stdin.isatty():
        return default
    answer = input(f"{question}{f' [{default}]' if default else ''}: ").strip()
    return answer or default


def _fingerprint(line):
    code, out, _err = core.run_quiet(["ssh-keygen", "-l", "-E", "sha256", "-f", "-"], stdin=line + "\n")
    parts = out.split()
    return (parts[1], parts[-1].strip("()")) if code == 0 and len(parts) >= 4 else (None, None)


def _scan_host_key(host, port):
    """(known_hosts line, fingerprint, type) of the host's best key, or (None, None, reason)."""
    code, out, err = core.run_quiet(["ssh-keyscan", "-T", "5", "-p", str(port), "-t", "ed25519,ecdsa,rsa", host],
                                    timeout=20)
    lines = [ln for ln in out.splitlines() if ln and not ln.startswith("#")]
    if code is None or not lines:
        return None, None, (err.strip().splitlines() or ["keine Antwort"])[-1]
    for wanted in ("ssh-ed25519", "ecdsa-sha2-nistp256", "ssh-rsa"):
        for line in lines:
            fields = line.split()
            if len(fields) >= 3 and fields[1] == wanted:
                fp, kind = _fingerprint(line)
                if fp:
                    return line, fp, kind
    return None, None, "kein verwertbarer Host-Schlüssel"


def host_known(host, port):
    target = host if port == 22 else f"[{host}]:{port}"
    code, out, _err = core.run_quiet(["ssh-keygen", "-F", target])
    return code == 0 and bool(out.strip())


def _add_known_host(line):
    SSH_DIR.mkdir(mode=0o700, exist_ok=True)
    fd = os.open(SSH_DIR / "known_hosts", os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    with os.fdopen(fd, "a", encoding="utf-8") as fh:
        fh.write(line.rstrip("\n") + "\n")


def _make_key(path):
    if path.exists():
        return True
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    comment = f"linuxmos-clip@{socket.gethostname()}"
    code, _out, err = core.run_quiet(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", comment, "-f", str(path)])
    if code != 0:
        say(f"ssh-keygen ist fehlgeschlagen: {err.strip()}", sys.stderr)
        return False
    path.chmod(0o600)
    return True


def authorized_keys_line(public_key, command=RECEIVER_COMMAND):
    """The line for the receiver: with `restrict` and a forced command the key can do nothing but deliver clips."""
    return f'restrict,command="{command} receive-ssh" {public_key.strip()}'


def cmd_setup(args):
    for program in ("ssh", "ssh-keygen", "ssh-keyscan"):
        if not core.have(program):
            return fail(f"{program} fehlt: sudo apt install openssh-client")
    say("Clip-Transfer einrichten (dieser PC sendet an den Empfänger)\n")
    name = args.name or _ask("Name des Empfängers (z. B. Windows-PC)")
    host = args.host or _ask("Adresse des Empfängers (IP oder Name)")
    user = args.user or _ask("Benutzer auf dem Empfänger", os.environ.get("USER", ""))
    port = args.port or int(_ask("SSH-Port", "22") or 22)
    peer_os = args.os or _ask("Betriebssystem des Empfängers (linux/windows)", "linux")
    key_path = Path(os.path.expanduser(args.key or core.DEFAULT_KEY))
    raw = {"name": name, "host": host, "user": user, "port": port, "key": args.key or core.DEFAULT_KEY, "os": peer_os}
    if not core.valid_peer(raw):
        return fail("Angaben ungültig (Name, Adresse, Benutzer, Port 1–65535)", EXIT_USAGE)

    say("\n1. Schlüssel")
    if not _make_key(key_path):
        return EXIT_FAILED
    if key_path.stat().st_mode & 0o077:
        key_path.chmod(0o600)
    mark("ok", f"{key_path} (nur für Clips gedacht, ohne Passwort, Rechte 600)")
    public_key = Path(str(key_path) + ".pub").read_text(encoding="utf-8").strip()

    say("\n2. Host-Schlüssel des Empfängers")
    if host_known(host, port):
        mark("ok", "schon bekannt (known_hosts)")
    else:
        line, fp, kind = _scan_host_key(host, port)
        if line is None:
            mark("bad", f"keine Antwort von {host}:{port}: {kind}")
            say("    Läuft dort der SSH-Server und ist der PC an? Windows: OpenSSH-Server-Dienst (docs/CLIP-WINDOWS.md).")
            return EXIT_FAILED
        say(f"    {host} meldet den Schlüssel {kind}:\n      {fp}")
        say("    Vergleiche das mit dem Empfänger, z. B. dort: ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub")
        if args.fingerprint:
            confirmed = args.fingerprint.strip() == fp
            if not confirmed:
                return fail(f"Der Fingerabdruck stimmt nicht mit --fingerprint überein ({args.fingerprint}) – abgebrochen",
                            EXIT_FAILED)
        else:
            if not sys.stdin.isatty():
                return fail("Der Fingerabdruck muss bewusst bestätigt werden (Terminal oder --fingerprint SHA256:…)")
            confirmed = input("    Stimmt der Fingerabdruck? Dann „ja“ eintippen: ").strip().lower() in ("ja", "yes")
        if not confirmed:
            return fail("Nicht bestätigt – nichts gespeichert")
        _add_known_host(line)
        mark("ok", "Host-Schlüssel gespeichert")

    say("\n3. Peer speichern")
    cfg = Config.load()
    stored = [p for p in (cfg.get("clip_peers") or []) if isinstance(p, dict) and p.get("name") != name]
    stored.append({"name": name, "host": host, "user": user, "port": port, "key": args.key or core.DEFAULT_KEY,
                   "os": peer_os})
    cfg["clip_peers"] = stored
    if not cfg.get("clip_default_peer"):
        cfg["clip_default_peer"] = name
    if args.enable_send or _ask("Senden jetzt einschalten (clip_send_enabled)? j/n", "n").lower() in ("j", "ja", "y"):
        cfg["clip_send_enabled"] = True
    if not cfg.save():
        return fail("config.json ist ungültig – der Peer wurde nicht gespeichert (Zeile in config.json prüfen)")
    mark("ok", f"{name} → {user}@{host}:{port} in config.json (clip_peers)")

    say(f"\n4. Auf dem Empfänger ({name}) diese Zeile in ~/.ssh/authorized_keys eintragen:\n")
    say("    " + authorized_keys_line(public_key, args.receiver_command))
    say("\n    Der Schlüssel darf damit nichts anderes als Clips abliefern (kein Login, keine Weiterleitung).")
    say(f"    Auf dem Empfänger muss außerdem der Empfang an sein (clip_receive_enabled) – siehe {GUIDE}.")
    say("    Danach prüfen: linuxmos-clip doctor")
    return EXIT_OK


# =============================================================================
# doctor
# =============================================================================
def _port_open(port):
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=1):
            return True
    except OSError:
        return False


def cmd_doctor(args):
    cfg = Config.load()
    paths = core.default_paths()
    bad = 0

    def report(level, text):
        nonlocal bad
        bad += level == "bad"
        mark(level, text)

    send, receive = cfg.flag("clip_send_enabled"), cfg.flag("clip_receive_enabled")
    say(f"Senden: {'an' if send else 'aus'} · Empfang: {'an' if receive else 'aus'}")
    if cfg.error:
        report("bad", f"config.json ist ungültig ({cfg.error}) – es gelten die Standardwerte")

    say("\nSSH auf diesem PC")
    if core.ssh_available():
        report("ok", "ssh-Client vorhanden")
    else:
        report("bad", "ssh fehlt: sudo apt install openssh-client")

    found = core.peers(cfg)
    say("\nPeers")
    if not found:
        report("warn" if not send else "bad", "kein Peer eingerichtet (linuxmos-clip setup)")
    for peer in found:
        say(f" {peer['name']} → {peer['user']}@{peer['host']}:{peer['port']}")
        problem = core.key_problem(peer)
        report("bad" if problem else "ok", problem or f"Schlüssel {peer['key']} (Rechte ok)")
        if core.have("ssh-keygen"):
            if host_known(peer["host"], peer["port"]):
                report("ok", "Host-Schlüssel bekannt")
            else:
                report("bad", "Host-Schlüssel unbekannt: linuxmos-clip setup")
        if args.offline or problem or not core.ssh_available():
            continue
        # An empty clip: reaches the receiver's forced command and is refused as empty – nothing is stored
        done = subprocess.run(core.ssh_argv(peer, core.remote_command("text")), stdin=subprocess.DEVNULL,
                              stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        stderr = done.stderr.decode("utf-8", "replace")
        if done.returncode == EXIT_BAD_CONTENT:
            report("ok", "erreichbar, Schlüssel angenommen, Empfänger bereit")
        else:
            report("bad", core.explain_failure(done.returncode, stderr, peer)[1])

    say("\nEmpfang auf diesem PC")
    if not receive:
        report("warn", "aus – nichts wird angenommen (Tray → Clip-Empfang)")
    else:
        if _port_open(22):
            report("ok", "SSH-Server antwortet auf Port 22")
        elif Path("/usr/sbin/sshd").exists():
            report("bad", "SSH-Server installiert, antwortet aber nicht auf Port 22: sudo systemctl enable --now ssh "
                          "(läuft er auf einem anderen Port, ist das hier nur ein Hinweis)")
        else:
            report("bad", "openssh-server fehlt: sudo apt install openssh-server (wird nicht automatisch installiert)")
        try:
            keys = (SSH_DIR / "authorized_keys").read_text(encoding="utf-8")
        except OSError:
            keys = ""
        if "receive-ssh" in keys:
            report("ok", "authorized_keys enthält eine Clip-Zeile")
        else:
            report("warn", "authorized_keys hat keine Clip-Zeile (die erzeugt `linuxmos-clip setup` auf dem Sender)")
    cli = core.have("linuxmos-clip")
    report("ok" if cli else "warn", "linuxmos-clip liegt im PATH" if cli else
           f"linuxmos-clip liegt nicht im PATH (in authorized_keys steht deshalb der Pfad {RECEIVER_COMMAND})")

    say("\nEingang")
    if paths.inbox.exists():
        mode = stat.S_IMODE(paths.inbox.stat().st_mode)
        report("ok" if mode == 0o700 else "bad", f"{paths.inbox} (Rechte {mode:o})")
    else:
        report("ok", f"{paths.inbox} wird beim ersten Empfang angelegt")
    limits = core.Limits.from_config(cfg)
    used = core.usage(paths)
    report("ok" if used < limits.quota else "bad",
           f"belegt {human(used)} von {human(limits.quota)} (Einträge werden nach {limits.keep_days} Tagen gelöscht)")
    report("ok" if core.have("xclip") else "warn",
           "xclip vorhanden (für `linuxmos-clip apply`)" if core.have("xclip") else
           "xclip fehlt – nur nötig für `linuxmos-clip apply`, die MosIsland kopiert selbst")
    return EXIT_FAILED if bad else EXIT_OK


# =============================================================================
# selftest
# =============================================================================
def _selftest():
    """The receiving side against a throw-away folder, no ssh, no config: limits, names, atomicity, the command check."""
    import io

    results = []

    def check(name, ok, detail=""):
        results.append(ok)
        mark("ok" if ok else "bad", name + (f" – {detail}" if detail and not ok else ""))

    def attempt(*args, **kwargs):
        try:
            return core.receive(*args, **kwargs), None
        except ClipError as error:
            return None, error.code

    png = b"\x89PNG\r\n\x1a\n" + b"\0" * 64
    limits = core.Limits(text=2048, image=4096, file=8192, quota=60000, keep_days=7)
    with tempfile.TemporaryDirectory(prefix="linuxmos-clip-selftest-") as root:
        root = Path(root)
        paths = core.Paths(root / "inbox", root / "Downloads")

        def receive(kind, data, name=None):
            return attempt(io.BytesIO(data), kind, name, paths, limits, sender="127.0.0.1")

        say("Empfangsweg ohne SSH (Wegwerf-Ordner)")
        entry, _ = receive("text", "Grüße\r\nZeile\r\n".encode())
        check("Text: CRLF → LF, ein Zeilenende am Schluss entfernt",
              bool(entry) and core.read_text(entry, paths) == "Grüße\nZeile" and entry["chars"] == 11)
        entry, _ = receive("image", png)
        check("Bild wird erkannt und gespeichert", bool(entry) and entry["payload"].endswith(".png"))
        _entry, code = receive("image", b"not an image at all")
        check("Kein Bild wird abgelehnt", code == EXIT_BAD_CONTENT)
        entry, _ = receive("file", b"abc", "report.pdf")
        check("Datei landet in Downloads/LinuxMos",
              bool(entry) and Path(entry["path"]).read_bytes() == b"abc" and Path(entry["path"]).parent == paths.files)
        check("Rechte: Eingang 700, Dateien 600",
              stat.S_IMODE(paths.inbox.stat().st_mode) == 0o700 and all(
                  stat.S_IMODE(p.stat().st_mode) == 0o600 for p in paths.inbox.iterdir()) and
              stat.S_IMODE(Path(entry["path"]).stat().st_mode) == 0o600)

        before = sorted(os.listdir(paths.inbox)), sorted(os.listdir(paths.files))
        _entry, code = receive("text", b"x" * (limits.text + 1))
        check("Zu großer Text: Abbruch", code == EXIT_TOO_LARGE)
        _entry, code = receive("file", b"y" * (limits.file + 1), "big.bin")
        check("Zu große Datei: Abbruch", code == EXIT_TOO_LARGE)
        _entry, code = receive("image", png + b"z" * limits.image)
        check("Zu großes Bild: Abbruch", code == EXIT_TOO_LARGE)
        check("… ohne halbe Dateien", (sorted(os.listdir(paths.inbox)), sorted(os.listdir(paths.files))) == before)

        paths.files.mkdir(parents=True, exist_ok=True)
        outside = root / "outside.txt"
        (paths.files / "ln.txt").symlink_to(outside)
        names, twice = {}, []
        for given in ("../x", ".hidden", "a\x01b\x7f.txt", "n" * 500 + ".txt", "..", "C:\\dir\\win.txt", "ln.txt", "ln.txt"):
            entry, _ = receive("file", b"data", given)
            names[given] = entry and entry["name"]
            if given == "ln.txt":
                twice.append(entry["name"])
        folder_ok = all(p.parent == paths.files for p in (Path(e["path"]) for e in core.list_entries(paths) if e["type"] == "file"))
        check("Bösartige Namen: kein Pfad, kein Punkt am Anfang, keine Steuerzeichen",
              names["../x"] == "x" and names[".hidden"] == "hidden" and "\x01" not in names["a\x01b\x7f.txt"]
              and names[".."] == "datei" and names["C:\\dir\\win.txt"] == "win.txt" and folder_ok)
        check("Sehr langer Name wird gekürzt", len(names["n" * 500 + ".txt"].encode()) <= 200)
        check("Kollision: nummeriert, nichts überschrieben, Symlink nicht verfolgt",
              twice == ["ln (1).txt", "ln (2).txt"] and not outside.exists() and (paths.files / "ln.txt").is_symlink())

        ok = [("linuxmos-clip receive --type text", ("text", None)),
              ("linuxmos-clip receive --type file --name 'my file.pdf'", ("file", "my file.pdf")),
              ("linuxmos-clip receive --type image --name pic.png", ("image", "pic.png"))]
        bad = ["ls", "receive --type file", "linuxmos-clip receive --type file; id", "linuxmos-clip receive --type text && id",
               "linuxmos-clip receive --type text --name '$(id)'", "linuxmos-clip receive --type text --name a/b",
               "linuxmos-clip receive --type video", "linuxmos-clip receive --type text\n", "linuxmos-clip receive --type text --name ''",
               "linuxmos-clip receive --type text --name 'a'; id", "/bin/sh", "", None,
               "linuxmos-clip receive --type text --name " + "a" * 121]
        check("receive-ssh nimmt nur die erlaubten Befehle an", all(core.parse_command(c) == r for c, r in ok))
        check("receive-ssh lehnt alles andere ab", all(core.parse_command(c) is None for c in bad))

        # Quota: the inbox refuses what does not fit
        small = core.Limits(text=2048, image=4096, file=8192, quota=1000, keep_days=7)
        _entry, code = attempt(io.BytesIO(b"q" * 1500), "text", None, core.Paths(root / "q", root / "Downloads"), small)
        check("Eingang voll (Quota)", code == EXIT_FULL)

        # Old entries go
        old = time.time() - 8 * 86400
        stale, _ = attempt(io.BytesIO(b"old text"), "text", None, paths, limits, now=old)
        removed = core.cleanup(paths, 7)
        check("Aufräumen: alte Einträge weg, neue bleiben",
              bool(stale) and removed >= 1 and not (paths.inbox / (stale["id"] + ".json")).exists() and
              len(core.list_entries(paths)) >= 3)
    say(f"\n{sum(results)} von {len(results)} Prüfungen bestanden")
    return EXIT_OK if all(results) else EXIT_FAILED


# =============================================================================
def build_parser():
    parser = argparse.ArgumentParser(prog="linuxmos-clip", description="Clips (Text, Bilder, Dateien) per SSH zwischen PCs.")
    parser.add_argument("--selftest", action="store_true", help="Empfangsweg lokal prüfen, ohne SSH")
    sub = parser.add_subparsers(dest="command")

    setup = sub.add_parser("setup", help="Schlüssel erzeugen, Peer eintragen, authorized_keys-Zeile ausgeben")
    setup.add_argument("--name")
    setup.add_argument("--host")
    setup.add_argument("--user")
    setup.add_argument("--port", type=int)
    setup.add_argument("--os", choices=["linux", "windows"])
    setup.add_argument("--key", help=f"Schlüsseldatei (Standard {core.DEFAULT_KEY})")
    setup.add_argument("--fingerprint", help="erwarteter Host-Fingerabdruck (SHA256:…): bestätigt ihn für Skripte")
    setup.add_argument("--enable-send", action="store_true", help="clip_send_enabled gleich einschalten")
    setup.add_argument("--receiver-command", default=RECEIVER_COMMAND,
                       help=f"Pfad von linuxmos-clip auf dem Empfänger (Standard {RECEIVER_COMMAND})")
    setup.set_defaults(run=cmd_setup)

    doctor = sub.add_parser("doctor", help="alles auf dem Weg prüfen")
    doctor.add_argument("--offline", action="store_true", help="Peers nicht anrufen")
    doctor.set_defaults(run=cmd_doctor)

    send = sub.add_parser("send", help="senden (nur auf deinen Aufruf)")
    send.add_argument("--peer", help="Name des Peers (Standard: clip_default_peer)")
    send.add_argument("--type", choices=core.KINDS)
    send.add_argument("--name", help="Dateiname beim Empfänger")
    send.add_argument("file", nargs="?", help="Datei; ohne Angabe wird stdin gelesen")
    send.set_defaults(run=cmd_send)

    receive = sub.add_parser("receive", help="einen Clip von stdin in den Eingang schreiben")
    receive.add_argument("--type", choices=core.KINDS, required=True)
    receive.add_argument("--name")
    receive.set_defaults(run=cmd_receive)

    sub.add_parser("receive-ssh", help="Zwangsbefehl für authorized_keys").set_defaults(run=cmd_receive_ssh)

    apply_ = sub.add_parser("apply", help="Eintrag per xclip in die Zwischenablage kopieren")
    apply_.add_argument("id", nargs="?", help="ID (oder Anfang davon); ohne Angabe der neueste Text/Bild-Eintrag")
    apply_.set_defaults(run=cmd_apply)

    sub.add_parser("list", help="Eingang anzeigen").set_defaults(run=cmd_list)
    clean = sub.add_parser("clean", help="alte Einträge löschen")
    clean.add_argument("--all", action="store_true", help="alle Einträge löschen")
    clean.set_defaults(run=cmd_clean)
    return parser


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")     # no locale under sshd: never fail on an umlaut
        except (AttributeError, ValueError):
            pass
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.selftest:
        return _selftest()
    if not getattr(args, "run", None):
        parser.print_help()
        return EXIT_USAGE
    try:
        return args.run(args)
    except KeyboardInterrupt:
        return 130
