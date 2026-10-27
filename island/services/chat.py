"""AI chat and speech-to-text against an OpenAI-compatible server, through curl.

    ChatRequest(on_delta, on_done).start(config, key, history)   streamed answer, .cancel() stops it
    transcribe(config, key, wav_path, on_done)                   on_done(text, error)

The server is the config's "ai_base_url" (OpenAI by default; Ollama, LM Studio, OpenRouter and the like
speak the same protocol). The API key comes from the keyring (services/keyring.py) and goes to curl on
its standard input together with the URL and the request body, so neither shows up in `ps`.
Every request is one short-lived curl process that is read as it arrives; nothing runs in between.

Errors are (kind, status, detail) tuples, describe() turns them into a sentence.
"""

import json

from gi.repository import Gio, GLib

from island.i18n import _

DEFAULT_BASE = "https://api.openai.com/v1"
DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_STT_MODEL = "whisper-1"
HISTORY = 20                  # messages sent along with a question
CHAT_TIMEOUT, STT_TIMEOUT = 180, 90
# curl appends the HTTP status to the output after the body, on a line of its own
STATUS_MARK = "HTTPSTATUS:"
WRITE_OUT = f"\n{STATUS_MARK}%{{http_code}}\n"

# German source string, translated through i18n when it is used
SYSTEM_PROMPT = ("Du bist ein hilfreicher Assistent auf einem Linux-Desktop. "
                 "Antworte knapp und in der Sprache des Nutzers.")

# curl's exit codes that mean something to the user
CURL_UNREACHABLE = (6, 7)     # host not found, connection refused
CURL_TIMEOUT = 28


# ---- settings ----------------------------------------------------------------------
def base_url(config):
    url = (config.get("ai_base_url") or "").strip().rstrip("/")
    return url if url.startswith(("http://", "https://")) else DEFAULT_BASE


def model(config):
    return (config.get("ai_model") or "").strip() or DEFAULT_MODEL


def stt_model(config):
    return (config.get("ai_stt_model") or "").strip() or DEFAULT_STT_MODEL


def is_local(config):
    """A server on this computer (Ollama, LM Studio ...) needs no key."""
    try:
        host = GLib.Uri.parse(base_url(config), GLib.UriFlags.NONE).get_host() or ""
    except GLib.Error:
        return False
    return host in ("localhost", "::1") or host.startswith("127.")


def host(config):
    """The server's name for the status line."""
    try:
        return GLib.Uri.parse(base_url(config), GLib.UriFlags.NONE).get_host() or base_url(config)
    except GLib.Error:
        return base_url(config)


def history_limit(config):
    value = config.get("ai_history", HISTORY)
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 1 else HISTORY


def system_prompt(config):
    return (config.get("ai_system_prompt") or "").strip() or _(SYSTEM_PROMPT)


def build_messages(config, history):
    """The system prompt and the last messages of the conversation."""
    return [{"role": "system", "content": system_prompt(config)}] + list(history[-history_limit(config):])


# ---- curl ----------------------------------------------------------------------------
def _quote(text):
    """A value in curl's config file syntax (inside double quotes)."""
    return (str(text).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
            .replace("\r", "\\r").replace("\t", "\\t"))


def curl_config(url, key, lines=()):
    """curl's config for stdin: URL, key header and the request's own lines (data, form fields)."""
    out = [f'url = "{_quote(url)}"', 'request = "POST"']
    if key:
        out.append(f'header = "{_quote("Authorization: Bearer " + key)}"')
    out += lines
    return "\n".join(out) + "\n"


def curl_argv(timeout):
    return ["curl", "--silent", "--no-buffer", "--proto", "=https,http", "--connect-timeout", "10",
            "--max-time", str(timeout), "--write-out", WRITE_OUT, "--config", "-"]


def chat_config(config, key, history):
    body = json.dumps({"model": model(config), "messages": build_messages(config, history), "stream": True})
    return curl_config(base_url(config) + "/chat/completions", key,
                       ['header = "Content-Type: application/json"', f'data-binary = "{_quote(body)}"'])


def transcribe_config(config, key, path):
    lines = [f'form = "file=@{_quote(path)}"', f'form = "model={_quote(stt_model(config))}"',
             'form = "response_format=json"']
    language = (config.get("ai_voice_language") or "").strip()
    if language:
        lines.append(f'form = "language={_quote(language)}"')
    return curl_config(base_url(config) + "/audio/transcriptions", key, lines)


# ---- reading the replies -------------------------------------------------------------
def parse_stream_line(line):
    """One line of the event stream -> ("delta", text) | ("done", None) | ("status", code) |
    ("error", message) | ("other", line) | None (nothing to do)."""
    line = line.rstrip("\r")
    if not line.strip() or line.startswith(":"):
        return None
    if line.startswith(STATUS_MARK):
        digits = line[len(STATUS_MARK):].strip()
        return ("status", int(digits)) if digits.isdigit() else None
    if not line.startswith("data:"):
        return ("other", line)
    payload = line[5:].strip()
    if payload == "[DONE]":
        return ("done", None)
    try:
        obj = json.loads(payload)
    except ValueError:
        return None
    if not isinstance(obj, dict):
        return None
    if obj.get("error"):
        return ("error", error_message(obj))
    return ("delta", _content(obj)) if _content(obj) else None


def _content(obj):
    """The text of a streamed chunk (delta) or of a whole answer (message)."""
    try:
        choice = obj["choices"][0]
    except (KeyError, IndexError, TypeError):
        return ""
    if not isinstance(choice, dict):
        return ""
    part = choice.get("delta") or choice.get("message") or {}
    content = part.get("content") if isinstance(part, dict) else None
    return content if isinstance(content, str) else ""


def error_message(obj):
    """The server's own words from {"error": {"message": ...}} (or {"error": "..."})."""
    err = obj.get("error") if isinstance(obj, dict) else None
    if isinstance(err, dict):
        err = err.get("message")
    return str(err).strip()[:300] if err else ""


def body_error(text):
    """Error text from a reply that is no event stream: the server's message, else the start of the body."""
    try:
        message = error_message(json.loads(text))
    except ValueError:
        message = ""
    return message or " ".join(text.split())[:200]


def describe(error):
    """(kind, status, detail) -> a sentence for the user."""
    kind, status, detail = error
    if kind == "unreachable":
        text = _("Server nicht erreichbar (Adresse und Verbindung prüfen)")
    elif kind == "timeout":
        text = _("Keine Antwort vom Server (Zeitüberschreitung)")
    elif kind == "empty":
        text = _("Leere Antwort")
    elif kind == "auth":
        text = _("API-Key abgelehnt (HTTP {status})").format(status=status)
    elif kind == "notfound":
        text = _("Adresse oder Modell nicht gefunden (HTTP {status})").format(status=status)
    elif kind == "limit":
        text = _("Zu viele Anfragen oder Guthaben aufgebraucht (HTTP {status})").format(status=status)
    elif kind == "http":
        text = _("Server meldet einen Fehler (HTTP {status})").format(status=status)
    else:
        text = _("Anfrage fehlgeschlagen")
    return f"{text}: {detail}" if detail else text


def classify(status, exit_code):
    """HTTP status and curl's exit code -> an error kind, None if the request went through."""
    if status in (401, 403):
        return "auth"
    if status == 404:
        return "notfound"
    if status == 429:
        return "limit"
    if status >= 400:
        return "http"
    if status == 0:
        if exit_code in CURL_UNREACHABLE:
            return "unreachable"
        if exit_code == CURL_TIMEOUT:
            return "timeout"
        return "failed" if exit_code else None
    return None


def _send_stdin(proc, text):
    """Write curl's config to its stdin without blocking, then close the pipe."""
    pipe = proc.get_stdin_pipe()

    def wrote(stream, result):
        try:
            stream.write_all_finish(result)
        except GLib.Error:
            pass
        stream.close_async(GLib.PRIORITY_DEFAULT, None, lambda s, r: None)

    pipe.write_all_async(text.encode("utf-8"), GLib.PRIORITY_DEFAULT, None, wrote)


class ChatRequest:
    """One streamed answer: on_delta(text) per piece, on_done(error) at the end (None = fine).

    A cancelled request ends with on_done(("cancelled", 0, "")).
    """

    def __init__(self, on_delta, on_done):
        self._on_delta, self._on_done = on_delta, on_done
        self._proc = None
        self._cancelled = False
        self._status = 0
        self._chunks = 0
        self._stream_error = ""
        self._other = []

    def start(self, config, key, history):
        try:
            self._proc = Gio.Subprocess.new(
                curl_argv(CHAT_TIMEOUT), Gio.SubprocessFlags.STDIN_PIPE | Gio.SubprocessFlags.STDOUT_PIPE
                | Gio.SubprocessFlags.STDERR_SILENCE)
        except GLib.Error:
            GLib.idle_add(self._finish, ("failed", 0, "curl"))
            return
        _send_stdin(self._proc, chat_config(config, key, history))
        self._lines = Gio.DataInputStream.new(self._proc.get_stdout_pipe())
        self._read()

    def cancel(self):
        self._cancelled = True
        if self._proc:
            self._proc.force_exit()

    def _read(self):
        self._lines.read_line_async(GLib.PRIORITY_DEFAULT, None, self._on_line)

    def _on_line(self, stream, result):
        try:
            line, _length = stream.read_line_finish_utf8(result)
        except GLib.Error:
            line = None
        if line is None:
            self._proc.wait_async(None, self._on_exit)  # end of the output
            return
        event = parse_stream_line(line)
        if event:
            kind, value = event
            if kind == "delta":
                self._chunks += 1
                self._on_delta(value)
            elif kind == "status":
                self._status = value
            elif kind == "error":
                self._stream_error = value
            elif kind == "other":
                self._other.append(value)
        self._read()

    def _on_exit(self, proc, result):
        try:
            proc.wait_finish(result)
        except GLib.Error:
            pass
        self._finish(self._outcome(proc.get_exit_status() if proc.get_if_exited() else 1))

    def _outcome(self, exit_code):
        if self._cancelled:
            return ("cancelled", 0, "")
        body = "\n".join(self._other)
        if not self._chunks and not self._stream_error and body.strip():
            # A server that ignores "stream": the whole answer comes as one JSON document
            try:
                text = _content(json.loads(body))
            except ValueError:
                text = ""
            if text and self._status < 400:
                self._chunks += 1
                self._on_delta(text)
        kind = classify(self._status, exit_code)
        if kind:
            return (kind, self._status, self._stream_error or body_error(body))
        if self._stream_error:
            return ("http", self._status, self._stream_error)
        if not self._chunks:
            return ("empty", self._status, body_error(body))
        return None

    def _finish(self, error):
        self._on_done(error)
        return GLib.SOURCE_REMOVE


def transcribe(config, key, path, on_done):
    """Speech to text for the WAV file `path`; on_done(text, error) with error None on success."""
    try:
        proc = Gio.Subprocess.new(curl_argv(STT_TIMEOUT), Gio.SubprocessFlags.STDIN_PIPE
                                  | Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_SILENCE)
    except GLib.Error:
        GLib.idle_add(lambda: on_done("", ("failed", 0, "curl")) and False)
        return

    def done(p, result):
        try:
            _ok, out, _err = p.communicate_utf8_finish(result)
        except GLib.Error:
            out = ""
        text, error = parse_transcription(out or "", p.get_exit_status() if p.get_if_exited() else 1)
        on_done(text, error)

    # communicate would write the config as well, but keeps the pipe handling in one place
    proc.communicate_utf8_async(transcribe_config(config, key, str(path)), None, done)


def parse_transcription(output, exit_code):
    """curl's output (JSON body + status line) -> (text, error)."""
    body, _mark, status_text = output.rpartition(f"\n{STATUS_MARK}")
    status = int(status_text.strip()) if status_text.strip().isdigit() else 0
    kind = classify(status, exit_code)
    if kind:
        return "", (kind, status, body_error(body))
    try:
        obj = json.loads(body)
    except ValueError:
        return "", ("failed", status, body_error(body))
    text = obj.get("text") if isinstance(obj, dict) else None
    if not isinstance(text, str):
        return "", ("failed", status, error_message(obj) if isinstance(obj, dict) else "")
    return text.strip(), None
