"""Text and QR codes from the screen: tesseract and zbarimg on a captured area.

The area is shot with maim + slop (like an area screenshot) into the cache,
read and deleted again. Nothing here runs until a hotkey or button asks, and
the readers run as async subprocesses, so the island never blocks.

The *_argv / parse_* helpers are shared with the short-lived fallback
process (island.shot), which runs them synchronously.
"""

import base64
import os
import re
import tempfile
from pathlib import Path

import gi

gi.require_version("GdkPixbuf", "2.0")
from gi.repository import GdkPixbuf, Gio, GLib  # noqa: E402

from island.storage import CACHE_DIR  # noqa: E402

TEMP_DIR = CACHE_DIR / "ocr"
# Screen text is ~96 dpi, tesseract is trained on ~300: areas up to this size are
# scaled 2x first, which fixes most errors on small UI fonts (9-11 px)
UPSCALE_MAX = 1600
ZBAR_NS = "{http://zbar.sourceforge.net/2008/barcode}"
ZBAR_NOTHING_FOUND = 4
URL_RE = re.compile(r"^(https?://|www\.)\S+$", re.IGNORECASE)
# tesseract's OpenMP threads spin-wait: barely faster on a small area, and two runs at
# once (hotkey + editor) slow each other down to minutes. One thread each.
TESSERACT_ENV = {"OMP_THREAD_LIMIT": "1"}
# List items keep their own line when paragraphs are joined
BULLET_RE = re.compile(r"^([-–•·*▪◦]|\d{1,3}[.)]|[a-zA-Z][.)])\s")


def missing(kind):
    """Programs reading 'text' or 'qr' from the screen needs but that are not installed."""
    need = ["maim", "slop", "xclip", "tesseract" if kind == "text" else "zbarimg"]
    return [p for p in need if GLib.find_program_in_path(p) is None]


def temp_path(prefix="area-"):
    """A fresh file in the cache (maim and GdkPixbuf overwrite it)."""
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=prefix, suffix=".png", dir=TEMP_DIR)
    os.close(fd)
    return Path(name)


def upscaled(path):
    """A 2x copy of a small image for tesseract, or the path itself if it is big enough already."""
    try:
        pixbuf = GdkPixbuf.Pixbuf.new_from_file(str(path))
    except GLib.Error:
        return path
    w, h = pixbuf.get_width(), pixbuf.get_height()
    if max(w, h) > UPSCALE_MAX:
        return path
    out = temp_path("2x-")
    try:
        pixbuf.scale_simple(w * 2, h * 2, GdkPixbuf.InterpType.BILINEAR).savev(
            str(out), "png", ["compression"], ["1"])
    except GLib.Error:
        out.unlink(missing_ok=True)
        return path
    return out


# ---- text (tesseract) -------------------------------------------------------------
def text_argv(path, languages):
    return ["tesseract", str(path), "stdout", "-l", languages or "eng", "--psm", "3"]


def tidy(text, keep_linebreaks=False):
    """Clean tesseract's output. By default the lines of a paragraph become one line.

    Blank lines (paragraphs) and list items stay; a word split by a hyphen at the
    line end is put back together ("fort-|zufahren" -> "fortzufahren", but
    "E-|Mail" keeps its hyphen).
    """
    text = text.replace("\f", "").replace("\r", "")
    paragraphs = [p for p in re.split(r"\n\s*\n", text) if p.strip()]
    out = []
    for para in paragraphs:
        lines = [line.strip() for line in para.splitlines() if line.strip()]
        if keep_linebreaks:
            out.append("\n".join(lines))
            continue
        joined = ""
        for line in lines:
            if not joined:
                joined = line
            elif BULLET_RE.match(line):
                joined += "\n" + line
            elif joined.endswith("-") and len(joined) > 1 and joined[-2].isalpha():
                joined = (joined[:-1] if line[:1].islower() else joined) + line
            else:
                joined += " " + line
        out.append(joined)
    return "\n\n".join(out)


def text_result(returncode, out, err, keep_linebreaks=False):
    """(text, error): text may be "" when nothing was recognised."""
    if returncode != 0:
        if "Failed loading language" in err or "Error opening data file" in err:
            return "", "language"
        return "", (err.strip().splitlines() or ["tesseract"])[-1]
    return tidy(out, keep_linebreaks), None


# ---- QR and barcodes (zbarimg) ----------------------------------------------------------
def codes_argv(path):
    # XML keeps codes with line breaks apart and marks binary data
    return ["zbarimg", "--quiet", "--xml", str(path)]


def parse_codes(xml_text):
    """[(type, data)] from zbarimg's XML, duplicates removed."""
    import xml.etree.ElementTree as ET  # only needed once a code was scanned

    start = xml_text.find("<barcodes")
    if start < 0:
        return []
    try:
        root = ET.fromstring(xml_text[start:])
    except ET.ParseError:
        return []
    codes = []
    for symbol in root.iter(ZBAR_NS + "symbol"):
        node = symbol.find(ZBAR_NS + "data")
        if node is None:
            continue
        data = node.text or ""
        if node.get("format") == "base64":
            data = base64.b64decode(data).decode("utf-8", "replace")
        code = (symbol.get("type") or "", data)
        if data and code not in codes:
            codes.append(code)
    return codes


def codes_result(returncode, out, err):
    """(codes, error): codes may be [] when nothing was found."""
    if returncode == ZBAR_NOTHING_FOUND:
        return [], None
    if returncode != 0:
        return [], (err.strip().splitlines() or ["zbarimg"])[-1]
    return parse_codes(out), None


def parse_wifi(data):
    """WIFI:T:WPA;S:name;P:secret;; -> {ssid, password, security}, or None."""
    if not data.upper().startswith("WIFI:"):
        return None
    fields = {}
    for part in re.findall(r"((?:\\.|[^;])+)", data[5:]):
        key, sep, value = part.partition(":")
        if sep:
            fields[key.upper()] = re.sub(r"\\(.)", r"\1", value)
    if "S" not in fields:
        return None
    return {"ssid": fields["S"], "password": fields.get("P", ""), "security": fields.get("T", "")}


def link(data):
    """An http(s) URL to open, or None ('www.x.org' gets https://)."""
    data = data.strip()
    if not URL_RE.match(data):
        return None
    return data if "://" in data else "https://" + data


# ---- running (async, for the island and the editor) ----------------------------------------
def _run(argv, callback, env=None):
    """callback(returncode, stdout, stderr) on the main loop."""
    launcher = Gio.SubprocessLauncher.new(Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_PIPE)
    for key, value in (env or {}).items():
        launcher.setenv(key, value, True)
    try:
        proc = launcher.spawnv(argv)
    except GLib.Error as err:
        callback(-1, "", err.message)
        return

    def done(p, result):
        try:
            _ok, out, err = p.communicate_finish(result)
        except GLib.Error as error:
            callback(-1, "", error.message)
            return
        code = p.get_exit_status() if p.get_if_exited() else -1
        decode = (lambda b: b.get_data().decode("utf-8", "replace") if b else "")
        callback(code, decode(out), decode(err))

    proc.communicate_async(None, None, done)


def read_text(path, config, callback, delete=False):
    """Recognise the text in an image; callback(text, error). delete: remove the image afterwards."""
    source = upscaled(path)

    def done(code, out, err):
        for p in {source, path} if delete else {source} - {path}:
            p.unlink(missing_ok=True)
        callback(*text_result(code, out, err, config.get("ocr_keep_linebreaks", False)))

    _run(text_argv(source, config.get("ocr_languages", "deu+eng")), done, TESSERACT_ENV)


def read_codes(path, callback, delete=False):
    """Find QR codes and barcodes in an image; callback(codes, error)."""
    def done(code, out, err):
        if delete:
            path.unlink(missing_ok=True)
        callback(*codes_result(code, out, err))

    _run(codes_argv(path), done)


def copy_text(text):
    """Put text on the clipboard. xclip forks and serves it until something else is copied."""
    try:
        proc = Gio.Subprocess.new(["xclip", "-selection", "clipboard", "-in"],
                                  Gio.SubprocessFlags.STDIN_PIPE | Gio.SubprocessFlags.STDOUT_SILENCE
                                  | Gio.SubprocessFlags.STDERR_SILENCE)
    except GLib.Error:
        return False
    def done(p, result):
        try:
            p.communicate_finish(result)
        except GLib.Error:
            pass

    proc.communicate_async(GLib.Bytes.new(text.encode("utf-8")), None, done)
    return True
