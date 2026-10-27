"""Dictation: the microphone through ffmpeg into a small mono WAV, which chat.transcribe() turns into text.

The recording is a temporary file: it goes away as soon as the text is back (or the attempt failed).
16 kHz mono is what speech models work with anyway, and keeps ten minutes under 20 MB (the usual
upload limit of the speech APIs is 25 MB).
"""

from gi.repository import GLib

from island.services.recorder import TEMP_DIR

WAV = TEMP_DIR / "dictation.wav"
LOG = TEMP_DIR / "dictation.log"
MIN_BYTES = 16000        # under half a second of speech: a mis-press, not a dictation
DEFAULT_MAX_S, LIMIT_S = 120, 600


def missing():
    return [p for p in ("ffmpeg",) if GLib.find_program_in_path(p) is None]


def max_seconds(config):
    value = config.get("ai_voice_max_s", DEFAULT_MAX_S)
    return value if isinstance(value, int) and not isinstance(value, bool) and 1 <= value <= LIMIT_S else DEFAULT_MAX_S


def record_argv(config):
    """ffmpeg recording the default microphone until it is stopped (SIGINT) or max_seconds() are over."""
    return ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y", "-f", "pulse", "-i",
            "@DEFAULT_SOURCE@", "-ac", "1", "-ar", "16000", "-t", str(max_seconds(config)), str(WAV)]
