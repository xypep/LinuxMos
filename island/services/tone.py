"""The reminder's chimes, made on first use from sine waves (nothing is shipped, nothing from third parties).

A soft double tone: two notes that fade in and out, a little overlapping, with a hint of overtones so it
sounds like a small bell and not like a beep. Played with paplay, whose --volume scales the whole thing.
"""

import logging
import math
import struct
import wave

from island.services import system
from island.storage import CACHE_DIR

log = logging.getLogger("mosisland.tone")

RATE = 44100
PEAK = 0.55          # of full scale; the volume setting only turns it down from there
# name -> ((start s, frequency Hz, length s) per note): C5 -> E5 calm, E5 -> G5 a little higher and longer
CHIMES = {
    "chime": ((0.00, 523.25, 0.34), (0.17, 659.25, 0.40)),
    "chime-up": ((0.00, 659.25, 0.42), (0.20, 783.99, 0.52)),
}
OVERTONES = ((1, 1.0), (2, 0.16), (3, 0.05))    # (multiple of the frequency, level)
ATTACK_S = 0.035


def path(name):
    return CACHE_DIR / f"stretch-{name}.wav"


def _note(frequency, length):
    """Samples of one note: raised-cosine fade-in, then a smooth fade-out over the rest."""
    samples = []
    count = int(length * RATE)
    norm = sum(level for _m, level in OVERTONES)
    for i in range(count):
        t = i / RATE
        fade_in = min(1.0, t / ATTACK_S)
        fade_in = 0.5 - 0.5 * math.cos(math.pi * fade_in)
        fade_out = 0.5 + 0.5 * math.cos(math.pi * i / count)    # 1 -> 0 over the whole note
        tone = sum(level * math.sin(2 * math.pi * frequency * multiple * t) for multiple, level in OVERTONES) / norm
        samples.append(tone * fade_in * fade_out ** 1.5)
    return samples


def render(name):
    """The samples (floats, -1..1) of a chime."""
    notes = CHIMES[name]
    total = int((max(start + length for start, _f, length in notes) + 0.05) * RATE)
    mix = [0.0] * total
    for start, frequency, length in notes:
        offset = int(start * RATE)
        for i, value in enumerate(_note(frequency, length)):
            mix[offset + i] += value
    top = max(abs(v) for v in mix) or 1.0
    return [v / top * PEAK for v in mix]


def ensure(name):
    """The WAV of a chime in the cache folder (written the first time). None if it can't be written."""
    target = path(name)
    if target.is_file() and target.stat().st_size > 0:
        return target
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(target) + ".tmp", "wb") as out:
            out.setnchannels(1)
            out.setsampwidth(2)
            out.setframerate(RATE)
            out.writeframes(b"".join(struct.pack("<h", int(v * 32767)) for v in render(name)))
        target.with_name(target.name + ".tmp").replace(target)
    except OSError as error:
        log.warning("cannot write %s: %s", target, error)
        return None
    log.info("made %s", target)
    return target


def play(name, volume):
    """Play a chime at volume 0..1 (0 = silent). paplay missing or no sound server: a log line, nothing else."""
    if volume <= 0:
        return
    if not system.has("paplay"):
        log.info("no paplay: chime skipped")
        return
    target = ensure(name)
    if target is not None:
        system.run(["paplay", f"--volume={int(volume * 65536)}", str(target)],
                   lambda ok, _out: None if ok else log.info("paplay could not play %s", target.name))
