"""Countdown timer. Ticks once per second, and only while it is running."""

from gi.repository import GLib


class Timer:
    def __init__(self, on_tick, on_done):
        self._on_tick = on_tick
        self._on_done = on_done
        self._end_us = None
        self._source = 0
        self.total = 0
        self.label = "Timer"  # "Timer", "Fokus" or "Pause" (Pomodoro)

    @property
    def running(self):
        return self._end_us is not None

    @property
    def remaining(self):
        if not self.running:
            return 0
        return max(0, int((self._end_us - GLib.get_monotonic_time()) / 1_000_000 + 0.999))

    def start(self, seconds, label="Timer"):
        self.label = label
        self.total = int(seconds)
        self._end_us = GLib.get_monotonic_time() + self.total * 1_000_000
        if not self._source:
            self._source = GLib.timeout_add_seconds(1, self._tick)
        self._on_tick()

    def cancel(self):
        self._stop()
        self._on_tick()

    def _stop(self):
        self._end_us = None
        if self._source:
            GLib.source_remove(self._source)
            self._source = 0

    def _tick(self):
        if self.remaining <= 0:
            self._source = 0
            self._end_us = None
            self._on_tick()
            self._on_done()
            return GLib.SOURCE_REMOVE
        self._on_tick()
        return GLib.SOURCE_CONTINUE


def format_seconds(seconds):
    minutes, secs = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours}:{minutes:02d}:{secs:02d}" if hours else f"{minutes:02d}:{secs:02d}"
