"""HTTP GET through curl, a short-lived process per request.

    http.get(url, callback)        callback(status, body: bytes)
    http.get_json(url, callback)   callback(status, data or None)

status is the HTTP code, 0 when no answer came (offline, timeout, too big,
curl missing). Callbacks always run on the main loop.

Why curl and not urllib: Python's HTTPS stack (ssl, http.client, email and
OpenSSL's CA store) would stay in the island's memory for good after the first
request – a few MB for one weather update every 30 minutes. curl is in the base
packages of install.sh, and Gio.Subprocess needs no threads either.
"""

import json

from gi.repository import Gio, GLib

USER_AGENT = "LinuxMos-Island/1.10 (+https://github.com/xypep/LinuxMos)"
MAX_BYTES = 8 * 1024 * 1024
# curl appends the status code to the body: always three digits, "000" without an answer
_STATUS = "%{http_code}"


def get(url, callback, timeout=10, headers=(), max_bytes=MAX_BYTES):
    argv = ["curl", "--silent", "--location", "--max-redirs", "5", "--proto", "=https,http",
            "--max-time", str(timeout), "--max-filesize", str(max_bytes), "--user-agent", USER_AGENT,
            "--write-out", _STATUS]
    for header in headers:
        argv += ["--header", header]
    argv += ["--", url]
    try:
        proc = Gio.Subprocess.new(argv, Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_SILENCE)
    except GLib.Error:
        GLib.idle_add(_fail, callback)  # no curl: same as offline (and never called back re-entrantly)
        return

    def done(p, result):
        try:
            _ok, out, _err = p.communicate_finish(result)
            data = out.get_data() if out is not None else b""
        except GLib.Error:
            data = b""
        body, code = data[:-3], data[-3:]
        # curl fails (exit code) on no answer, a timeout or a body over max_bytes; a 404 is no failure
        ok = p.get_successful() and code.isdigit() and len(body) <= max_bytes
        status = int(code) if ok else 0
        callback(status, body if status else b"")

    proc.communicate_async(None, None, done)


def _fail(callback):
    callback(0, b"")
    return GLib.SOURCE_REMOVE


def get_json(url, callback, timeout=10, headers=()):
    def parsed(status, body):
        try:
            data = json.loads(body) if status else None
        except ValueError:
            data = None
        callback(status, data)

    get(url, parsed, timeout, ("Accept: application/json",) + tuple(headers))
