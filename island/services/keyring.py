"""The AI API key in the user's keyring (libsecret, through `secret-tool`).

The key never goes into config.json and never onto a command line (those show up in `ps`):
secret-tool reads it from its standard input. Everything is a short-lived process, so the key
lives in the island's memory only while a request is being built.
"""

from gi.repository import Gio, GLib

ATTRS = ["service", "linuxmos-island", "account", "ai-api-key"]
LABEL = "MosIsland KI-Chat"


def _later(callback, value):
    """Answer from the main loop, never re-entrantly from inside the caller."""
    GLib.idle_add(lambda: callback(value) and False)


def available():
    return GLib.find_program_in_path("secret-tool") is not None


def _spawn(argv, stdin=False):
    flags = Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_SILENCE
    if stdin:
        flags |= Gio.SubprocessFlags.STDIN_PIPE
    return Gio.Subprocess.new(argv, flags)


def lookup(callback):
    """callback(key): the stored key, "" if there is none (or the keyring cannot be reached)."""
    if not available():
        _later(callback, "")
        return
    try:
        proc = _spawn(["secret-tool", "lookup", *ATTRS])
    except GLib.Error:
        _later(callback, "")
        return

    def done(p, result):
        try:
            _ok, out, _err = p.communicate_utf8_finish(result)
        except GLib.Error:
            out = ""
        callback((out or "").strip() if p.get_successful() else "")

    proc.communicate_utf8_async(None, None, done)


def store(key, callback):
    """Save the key (secret-tool reads it from stdin, without a trailing newline); callback(ok)."""
    if not available() or not key:
        _later(callback, False)
        return
    try:
        proc = _spawn(["secret-tool", "store", f"--label={LABEL}", *ATTRS], stdin=True)
    except GLib.Error:
        _later(callback, False)
        return

    def done(p, result):
        try:
            p.communicate_utf8_finish(result)
            ok = p.get_successful()
        except GLib.Error:
            ok = False
        callback(ok)

    proc.communicate_utf8_async(key, None, done)


def store_sync(key):
    """Same without a main loop (the --set-key command); True on success."""
    if not available() or not key:
        return False
    try:
        proc = _spawn(["secret-tool", "store", f"--label={LABEL}", *ATTRS], stdin=True)
        proc.communicate_utf8(key, None)
        return proc.get_successful()
    except GLib.Error:
        return False


def clear(callback):
    """Remove the key; callback(ok)."""
    if not available():
        _later(callback, False)
        return
    try:
        proc = _spawn(["secret-tool", "clear", *ATTRS])
    except GLib.Error:
        _later(callback, False)
        return

    def done(p, result):
        try:
            p.communicate_utf8_finish(result)
            ok = p.get_successful()
        except GLib.Error:
            ok = False
        callback(ok)

    proc.communicate_utf8_async(None, None, done)
