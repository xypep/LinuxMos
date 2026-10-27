"""Clip transfer, the part without GTK: limits, the receiving side, the inbox, how a send is called.

This module is used by the CLI (`linuxmos-clip`, which also runs on a machine without a screen when
another PC delivers a clip through sshd) and by the island. Nothing in here imports gi.

Transport: one `ssh` call per clip with the data on stdin, no connection stays open. The receiving side
(`receive`, called by `receive-ssh` from the restricted authorized_keys line) writes
    <inbox>/<id>.json   what it is (type, name, size, sender, time): renamed into place LAST, so an entry
                        exists for the island only when it is complete
    <inbox>/<id>.txt    the text, or <id>.png/.jpg/... the image
and puts a received file straight into ~/Downloads/LinuxMos (the entry only points to it). All of it is
written to a temporary file first and renamed; a clip over its limit is aborted while reading stdin.
"""

import json
import os
import re
import stat
import time
from collections import namedtuple
from pathlib import Path

from island.storage import DATA_DIR

# ---- exit codes: the receiver's status travels back through ssh, the sender turns it into a sentence --------
EXIT_OK = 0
EXIT_FAILED = 1
EXIT_USAGE = 2
EXIT_DISABLED = 3       # clip_receive_enabled is off
EXIT_TOO_LARGE = 4
EXIT_REJECTED = 5       # receive-ssh: not a command we accept
EXIT_BAD_CONTENT = 6    # empty, not UTF-8 text, not an image
EXIT_FULL = 7           # inbox quota
EXIT_COMMAND_MISSING = 127   # the shell on the other side did not find linuxmos-clip

KINDS = ("text", "image", "file")
DEFAULT_KEY = "~/.ssh/linuxmos_clip_ed25519"
CHUNK = 64 * 1024
NAME_MAX = 120                  # characters of a received file's name (the file system allows 255 bytes)
ORPHAN_AGE_S = 3600             # a temporary file or payload without its entry this old is garbage
ID_RE = re.compile(r"\d{13}-[0-9a-f]{6}")
HOST_RE = re.compile(r"[A-Za-z0-9._:\-]{1,253}")
USER_RE = re.compile(r"[A-Za-z0-9._][A-Za-z0-9._\-]{0,63}")
PEER_NAME_MAX = 40

# What receive-ssh accepts, character for character (always used with fullmatch: "$" would let a trailing
# newline through). No shell is ever involved.
COMMAND_RE = re.compile(
    r"linuxmos-clip receive --type (text|image|file)"
    r"(?: --name (?:'([A-Za-z0-9._ \-]{1,120})'|([A-Za-z0-9._\-]{1,120})))?")

# image kind -> extension, by the first bytes
IMAGE_SIGNATURES = ((b"\x89PNG\r\n\x1a\n", "png"), (b"\xff\xd8\xff", "jpg"), (b"GIF87a", "gif"),
                    (b"GIF89a", "gif"), (b"BM", "bmp"))
IMAGE_EXTENSIONS = {"png", "jpg", "gif", "bmp", "webp"}


class ClipError(Exception):
    """Something a person should be told; code is the exit status."""

    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.message = message


# =============================================================================
# Paths and limits
# =============================================================================
# Plain tuples instead of dataclasses, and os.urandom instead of secrets, shutil.which, subprocess at the top:
# the island imports this module while receiving is on, and dataclasses (inspect), secrets (hashlib, OpenSSL)
# and subprocess would stay in its memory for good (~3 MB)
class Paths(namedtuple("Paths", "inbox downloads")):      # received files go to <downloads>/LinuxMos
    __slots__ = ()

    @property
    def files(self):
        return self.downloads / "LinuxMos"


def downloads_dir():
    """The user's download folder without GLib: XDG_DOWNLOAD_DIR from user-dirs.dirs, else ~/Downloads."""
    config_home = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    try:
        text = (config_home / "user-dirs.dirs").read_text(encoding="utf-8")
        match = re.search(r'^XDG_DOWNLOAD_DIR="([^"]+)"', text, re.M)
        if match:
            path = Path(match.group(1).replace("$HOME", str(Path.home())))
            if path.is_absolute():
                return path
    except OSError:
        pass
    return Path.home() / "Downloads"


def default_paths():
    return Paths(DATA_DIR / "clip-inbox", downloads_dir())


class Limits(namedtuple("Limits", "text image file quota keep_days",
                        defaults=(1024 * 1024, 20 * 1024 * 1024, 100 * 1024 * 1024, 500 * 1024 * 1024, 7))):
    __slots__ = ()

    @classmethod
    def from_config(cls, cfg):
        mb = 1024 * 1024
        return cls(text=cfg.integer("clip_max_text_kb", 1, 10240) * 1024,
                   image=cfg.integer("clip_max_image_mb", 1, 500) * mb,
                   file=cfg.integer("clip_max_file_mb", 1, 8192) * mb,
                   quota=cfg.integer("clip_inbox_quota_mb", 10, 100000) * mb,
                   keep_days=cfg.integer("clip_inbox_keep_days", 1, 365))

    def for_kind(self, kind):
        return {"text": self.text, "image": self.image, "file": self.file}[kind]


def human(size):
    for unit, step in (("GB", 1 << 30), ("MB", 1 << 20), ("KB", 1 << 10)):
        if size >= step:
            return f"{size / step:.1f} {unit}".replace(".0 ", " ")
    return f"{size} B"


# =============================================================================
# File names
# =============================================================================
_FORBIDDEN = re.compile(r'[\x00-\x1f\x7f-\x9f\u202a-\u202e\u2066-\u2069\u200b-\u200f<>:"|?*\\/]')


def sanitize_name(name, fallback="datei"):
    """A name that is safe to create in a folder: no path, no '..', no leading dot, no control characters.

    Looks at the last part after / or \\, so a name like "../../x" or "C:\\dir\\x.txt" becomes "x" / "x.txt".
    """
    name = (name or "").replace("\\", "/").split("/")[-1]
    name = _FORBIDDEN.sub("_", name)
    name = re.sub(r"\.{2,}", ".", name)
    name = name.strip(" .")
    if not name:
        name = fallback
    stem, dot, ext = name.rpartition(".")
    if not dot or not stem:                  # no extension (or just ".bashrc"-like, whose dot was stripped)
        stem, ext = name, ""
    else:
        ext = "." + ext
    # Characters first, then bytes (the file system limit is 255 bytes; a number may be added to the stem)
    stem, ext = stem[:NAME_MAX], ext[:16]
    while len((stem + ext).encode("utf-8")) > 200:
        stem = stem[:-1]
    return (stem or fallback) + ext


def _exclusive(directory, name, mode=0o600):
    """Create <directory>/<name> new (never overwrite, never follow a symlink); numbered if it exists.

    Returns (fd, path).
    """
    stem, dot, ext = name.rpartition(".")
    if not dot or not stem:
        stem, ext = name, ""
    else:
        ext = "." + ext
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
    for number in range(0, 1000):
        candidate = directory / (name if number == 0 else f"{stem} ({number}){ext}")
        try:
            return os.open(candidate, flags, mode), candidate
        except FileExistsError:
            continue
    raise ClipError(EXIT_FAILED, "Zu viele gleichnamige Dateien")


def make_private_dir(path):
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    try:
        if stat.S_IMODE(path.stat().st_mode) != 0o700:
            path.chmod(0o700)
    except OSError:
        pass


# =============================================================================
# Receiving
# =============================================================================
def new_id(now=None):
    return f"{int((now or time.time()) * 1000):013d}-{os.urandom(3).hex()}"


def image_extension(head):
    for signature, ext in IMAGE_SIGNATURES:
        if head.startswith(signature):
            return ext
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "webp"
    return None


def _write_json_private(path, data):
    tmp = path.with_name(f".tmp-{os.urandom(4).hex()}.json")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


def _read_limited(stream, limit, room):
    """Yield chunks of stream; ClipError once more than limit bytes (or more than the inbox has room for) came."""
    total = 0
    while True:
        chunk = stream.read(CHUNK)
        if not chunk:
            return
        total += len(chunk)
        if total > limit:
            raise ClipError(EXIT_TOO_LARGE, f"Zu groß: über {human(limit)} (Limit des Empfängers)")
        if total > room:
            raise ClipError(EXIT_FULL, "Eingang voll (clip_inbox_quota_mb)")
        yield chunk


def receive(stream, kind, name, paths, limits, sender="", now=None):
    """Store one clip read from stream (binary, e.g. sys.stdin.buffer); returns its entry (a dict).

    Raises ClipError and leaves nothing behind when the clip is too large, empty, not what it claims to be
    or does not fit the inbox.
    """
    if kind not in KINDS:
        raise ClipError(EXIT_USAGE, "Unbekannter Typ")
    now = now or time.time()
    make_private_dir(paths.inbox)
    cleanup(paths, limits.keep_days, now=now)
    room = limits.quota - usage(paths)
    if room <= 0:
        raise ClipError(EXIT_FULL, "Eingang voll (clip_inbox_quota_mb)")
    limit = limits.for_kind(kind)
    entry_id = new_id(now)
    entry = {"id": entry_id, "type": kind, "size": 0, "sender": sender[:64], "time": now}
    temps = []        # everything to delete if we fail
    try:
        if kind == "text":
            data = b"".join(_read_limited(stream, limit, room))
            if not data.strip():
                raise ClipError(EXIT_BAD_CONTENT, "Leerer Text")
            try:
                text = data.decode("utf-8")
            except UnicodeDecodeError:
                raise ClipError(EXIT_BAD_CONTENT, "Kein gültiger UTF-8-Text") from None
            # Text from Windows or from `echo`: CRLF -> LF, and one line break at the end is not meant
            text = text.replace("\r\n", "\n")
            if text.endswith("\n"):
                text = text[:-1]
            data = text.encode("utf-8")
            if not data.strip():
                raise ClipError(EXIT_BAD_CONTENT, "Leerer Text")
            payload = paths.inbox / f"{entry_id}.txt"
            fd, tmp = _temp_file(paths.inbox)
            temps.append(tmp)
            with os.fdopen(fd, "wb") as fh:
                fh.write(data)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp, payload)
            temps.append(payload)
            entry.update(size=len(data), name="", payload=payload.name, chars=len(text))
        elif kind == "image":
            ext, size = None, 0
            fd, tmp = _temp_file(paths.inbox)
            temps.append(tmp)
            with os.fdopen(fd, "wb") as fh:
                for chunk in _read_limited(stream, limit, room):
                    if ext is None:
                        ext = image_extension(chunk[:16])
                        if ext is None:
                            raise ClipError(EXIT_BAD_CONTENT, "Kein Bild (PNG, JPEG, GIF, BMP oder WebP erwartet)")
                    fh.write(chunk)
                    size += len(chunk)
                fh.flush()
                os.fsync(fh.fileno())
            if not size:
                raise ClipError(EXIT_BAD_CONTENT, "Leeres Bild")
            payload = paths.inbox / f"{entry_id}.{ext}"
            os.replace(tmp, payload)
            temps.append(payload)
            entry.update(size=size, name="", payload=payload.name)
        else:
            paths.files.mkdir(mode=0o755, parents=True, exist_ok=True)
            size = 0
            fd, tmp = _temp_file(paths.files, prefix=".clip-tmp-")
            temps.append(tmp)
            with os.fdopen(fd, "wb") as fh:
                for chunk in _read_limited(stream, limit, room):
                    fh.write(chunk)
                    size += len(chunk)
                fh.flush()
                os.fsync(fh.fileno())
            if not size:
                raise ClipError(EXIT_BAD_CONTENT, "Leere Datei")
            safe = sanitize_name(name)
            final_fd, final = _exclusive(paths.files, safe)
            os.close(final_fd)
            temps.append(final)       # until the entry is complete a failure removes it again
            os.replace(tmp, final)    # onto our own just-created empty file: never over someone else's
            entry.update(size=size, name=final.name, path=str(final))
        _write_json_private(paths.inbox / f"{entry_id}.json", entry)
        return entry
    except BaseException:
        for leftover in temps:
            Path(leftover).unlink(missing_ok=True)
        raise


def _temp_file(directory, prefix=".tmp-"):
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
    for _attempt in range(10):
        path = directory / f"{prefix}{os.urandom(6).hex()}"
        try:
            return os.open(path, flags, 0o600), path
        except FileExistsError:
            continue
    raise ClipError(EXIT_FAILED, "Temporäre Datei lässt sich nicht anlegen")


def parse_command(text):
    """(kind, name or None) for a command receive-ssh accepts, else None. The whole string must match."""
    match = COMMAND_RE.fullmatch(text) if isinstance(text, str) else None
    if not match:
        return None
    return match.group(1), match.group(2) or match.group(3)


# =============================================================================
# The inbox
# =============================================================================
def _valid_entry(data, paths):
    """The entry dict if a meta file holds a sane one (anyone who can write the folder can write anything)."""
    if not isinstance(data, dict) or not isinstance(data.get("id"), str) or not ID_RE.fullmatch(data["id"]):
        return None
    kind = data.get("type")
    if kind not in KINDS or not isinstance(data.get("size"), int) or isinstance(data.get("size"), bool):
        return None
    if not isinstance(data.get("time"), (int, float)):
        return None
    data.setdefault("sender", "")
    if not isinstance(data["sender"], str):
        return None
    if kind == "file":
        path = data.get("path")
        if not isinstance(path, str):
            return None
        try:
            if Path(path).parent != paths.files:
                return None
        except (OSError, ValueError):
            return None
    else:
        payload = data.get("payload")
        if not isinstance(payload, str) or not payload.startswith(data["id"] + ".") or "/" in payload:
            return None
        ext = payload[len(data["id"]) + 1:]
        if (kind == "text" and ext != "txt") or (kind == "image" and ext not in IMAGE_EXTENSIONS):
            return None
    return data


def list_entries(paths):
    """All complete entries, oldest first. Unreadable or odd files are skipped."""
    entries = []
    try:
        names = sorted(os.listdir(paths.inbox))
    except OSError:
        return entries
    for name in names:
        if not name.endswith(".json") or name.startswith("."):
            continue
        try:
            with open(paths.inbox / name, encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, ValueError):
            continue
        entry = _valid_entry(data, paths)
        if entry and name == entry["id"] + ".json":
            entries.append(entry)
    entries.sort(key=lambda e: (e["time"], e["id"]))
    return entries


def payload_path(entry, paths):
    """Where an entry's data is: the inbox file (text, image) or the received file."""
    if entry["type"] == "file":
        return Path(entry["path"])
    return paths.inbox / entry["payload"]


def read_text(entry, paths):
    """The full text of a text entry ('' if it is gone)."""
    try:
        return payload_path(entry, paths).read_text(encoding="utf-8")
    except (OSError, ValueError):
        return ""


def usage(paths):
    """Bytes the inbox holds: text and images in it plus the files it points to (while their entry exists)."""
    total = 0
    try:
        for name in os.listdir(paths.inbox):
            try:
                total += (paths.inbox / name).lstat().st_size
            except OSError:
                pass
    except OSError:
        return 0
    for entry in list_entries(paths):
        if entry["type"] == "file":
            try:
                total += os.lstat(entry["path"]).st_size
            except OSError:
                pass
    return total


def remove_entry(entry, paths):
    """Delete an entry. A received file stays where it is: from then on it is the user's own."""
    if entry["type"] != "file":
        payload_path(entry, paths).unlink(missing_ok=True)
    (paths.inbox / (entry["id"] + ".json")).unlink(missing_ok=True)


def cleanup(paths, keep_days, now=None, everything=False):
    """Drop entries older than keep_days (all of them with everything=True) and stray temporary files.

    Called when the island starts, when an entry arrives and by `linuxmos-clip clean`: no timer anywhere.
    Returns how many entries went.
    """
    now = now or time.time()
    removed = 0
    for entry in list_entries(paths):
        if everything or now - entry["time"] > keep_days * 86400:
            remove_entry(entry, paths)
            removed += 1
    known = set()
    for entry in list_entries(paths):
        known.update((entry["id"] + ".json", entry.get("payload")))
    payloads = tuple("." + ext for ext in ("txt", *IMAGE_EXTENSIONS))
    for folder, is_inbox in ((paths.inbox, True), (paths.files, False)):
        try:
            names = os.listdir(folder)
        except OSError:
            continue
        for name in names:
            if name in known:
                continue
            # Half-written temporary files, and data whose entry is missing (a crash between the two renames)
            stray = name.startswith(".tmp-") or name.endswith(payloads) if is_inbox else name.startswith(".clip-tmp-")
            if not stray:
                continue
            try:
                if now - (folder / name).lstat().st_mtime > ORPHAN_AGE_S:
                    (folder / name).unlink()
            except OSError:
                pass
    return removed


# =============================================================================
# Peers and the ssh call
# =============================================================================
def valid_peer(raw):
    """A normalised peer dict from a config entry, or None if it cannot be used."""
    if not isinstance(raw, dict):
        return None
    name = raw.get("name")
    host = raw.get("host")
    user = raw.get("user")
    port = raw.get("port", 22)
    key = raw.get("key") or DEFAULT_KEY
    if not (isinstance(name, str) and name.strip() and isinstance(host, str) and isinstance(user, str)
            and isinstance(key, str)):
        return None
    if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535:
        return None
    # A host or user starting with "-" would be taken as an ssh option
    if not HOST_RE.fullmatch(host) or host.startswith("-") or not USER_RE.fullmatch(user):
        return None
    peer_os = raw.get("os") if raw.get("os") in ("linux", "windows") else "linux"
    ip = raw.get("ip") if isinstance(raw.get("ip"), str) else ""
    return {"name": name.strip()[:PEER_NAME_MAX], "host": host, "user": user, "port": port,
            "key": os.path.expanduser(key), "os": peer_os, "ip": ip}


def peers(cfg):
    """The usable peers of a config, in order; invalid entries and repeated names are left out."""
    seen, result = set(), []
    for raw in cfg.get("clip_peers") or []:
        peer = valid_peer(raw)
        if peer and peer["name"] not in seen:
            seen.add(peer["name"])
            result.append(peer)
    return result


def default_peer(cfg):
    found = peers(cfg)
    wanted = cfg.get("clip_default_peer")
    for peer in found:
        if peer["name"] == wanted:
            return peer
    return found[0] if len(found) == 1 else None


def peer_label(cfg, sender):
    """A name for the address a clip came from: the peer it belongs to, else the address."""
    for peer in peers(cfg):
        if sender and sender in (peer["host"], peer["ip"]):
            return peer["name"]
    return sender or "lokal"


def remote_command(kind, name=None):
    command = f"linuxmos-clip receive --type {kind}"
    if name:
        safe = re.sub(r"[^A-Za-z0-9._ \-]", "_", sanitize_name(name))[:NAME_MAX]
        command += f" --name '{safe}'"
    return command


def ssh_argv(peer, command):
    return ["ssh", "-T",
            "-o", "BatchMode=yes", "-o", "ConnectTimeout=5", "-o", "StrictHostKeyChecking=yes",
            "-o", "ControlMaster=no", "-o", "ControlPath=none", "-o", "IdentitiesOnly=yes",
            "-o", "ClearAllForwardings=yes", "-o", "ServerAliveInterval=10", "-o", "ServerAliveCountMax=3",
            "-i", peer["key"], "-p", str(peer["port"]), f"{peer['user']}@{peer['host']}", command]


def explain_failure(returncode, stderr, peer=None):
    """(short reason, long reason) for a failed send. The reason is what the card says."""
    err = (stderr or "").strip()
    last = err.splitlines()[-1][:160] if err else ""
    low = err.lower()
    if "remote host identification has changed" in low:
        return "Host-Schlüssel geändert", "Der Host-Schlüssel hat sich geändert – nicht senden, erst prüfen (möglicher Angriff)"
    if "host key verification failed" in low or "no matching host key" in low:
        return "Host-Schlüssel unbekannt", "Host-Schlüssel unbekannt: einmal `linuxmos-clip setup` ausführen und den Fingerabdruck bestätigen"
    if "permission denied" in low:
        return "Schlüssel abgelehnt", "Der Empfänger lehnt den Schlüssel ab (fehlt die Zeile in dessen authorized_keys?)"
    if any(text in low for text in ("timed out", "connection refused", "no route to host", "network is unreachable",
                                    "could not resolve", "name or service not known", "connection closed by",
                                    "connection reset", "broken pipe")):
        return "nicht erreichbar", "Nicht erreichbar (PC aus, falsche Adresse oder SSH-Dienst läuft nicht)"
    if returncode == EXIT_TOO_LARGE:
        return "zu groß", "Zu groß für den Empfänger (dessen Limit gilt)"
    if returncode == EXIT_DISABLED:
        return "Empfang aus", "Der Empfänger hat den Empfang ausgeschaltet (clip_receive_enabled)"
    if returncode == EXIT_FULL:
        return "Eingang voll", "Der Eingang des Empfängers ist voll (clip_inbox_quota_mb)"
    if returncode == EXIT_BAD_CONTENT:
        return "nicht angenommen", "Der Empfänger hat den Inhalt nicht angenommen" + (f": {last}" if last else "")
    if returncode == EXIT_REJECTED:
        return "Befehl abgelehnt", "Der Empfänger lehnt den Befehl ab (Version von linuxmos-clip passt nicht?)"
    if returncode == EXIT_COMMAND_MISSING or "command not found" in low:
        return "linuxmos-clip fehlt", "Auf dem Empfänger fehlt linuxmos-clip (Pfad in der authorized_keys-Zeile prüfen)"
    return f"Fehler {returncode}", f"Senden fehlgeschlagen (Code {returncode})" + (f": {last}" if last else "")


def key_problem(peer):
    """A sentence if the peer's key file cannot be used, else None."""
    path = Path(peer["key"])
    try:
        mode = path.stat().st_mode
    except OSError:
        return f"Schlüsseldatei fehlt: {peer['key']} (linuxmos-clip setup)"
    if mode & 0o077:
        return f"Schlüsseldatei hat zu offene Rechte (chmod 600 {peer['key']})"
    return None


def check_sendable(path, limits, kind):
    """(size, None) or (None, reason) for a file to send, checked on our side before ssh is started."""
    try:
        info = os.stat(path)
    except OSError:
        return None, "Datei nicht gefunden"
    if not stat.S_ISREG(info.st_mode):
        return None, "Keine gewöhnliche Datei"
    if info.st_size == 0:
        return None, "Datei ist leer"
    limit = limits.for_kind(kind)
    if info.st_size > limit:
        return None, f"Zu groß: {human(info.st_size)} (Limit {human(limit)})"
    return info.st_size, None


# =============================================================================
# Tools that may be missing
# =============================================================================
def which(program):
    for folder in (os.environ.get("PATH") or os.defpath).split(os.pathsep):
        candidate = os.path.join(folder or ".", program)
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    return None


def have(program):
    return which(program) is not None


def ssh_available():
    return have("ssh")


def run_quiet(argv, timeout=10, stdin=None):
    """(returncode, stdout, stderr) of a short command; (None, '', reason) if it cannot run."""
    import subprocess      # the CLI only
    try:
        done = subprocess.run(argv, input=stdin, capture_output=True, text=True, timeout=timeout)
        return done.returncode, done.stdout, done.stderr
    except (OSError, subprocess.SubprocessError) as error:
        return None, "", str(error)
