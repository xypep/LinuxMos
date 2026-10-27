"""The island's side of the stretch reminder: the card, the mark and the ring in the pill, chimes, messages.

The texts are German only, on purpose: they don't go through island/i18n.py (whose English table would turn
the button "Aus" into "Shut down", a word of the controls tab).

services/stretch.py holds the rules and only talks to these small adapters:
GlibEnv (clock, idle time, screen state), IslandGates (what holds a reminder back) and StretchView.
"""

import logging
from datetime import date

from gi.repository import GLib

from island.services import screen, tone
from island.services.fullscreen import FullscreenWatcher

log = logging.getLogger("mosisland.stretch")

CARD_REMINDER_MS = 15000       # then the card folds into the mark in the pill
CARD_ANSWER_MS = 30000
BIG_CARD_W, BIG_CARD_H = 560, 178
COUNTDOWN_STEP_MS = 250        # the ring's frame rate: 4 per second, only while a countdown runs
BLINK_HEADS_UP_MS = 700        # two blinks of the eyes, then the card
ICON = "avatar-default-symbolic"


class GlibEnv:
    """Clock and measurements for the reminder: GLib timeouts, the island's idle source, the screen saver."""

    def __init__(self, island):
        self.island = island

    @staticmethod
    def today():
        return date.today().isoformat()

    @staticmethod
    def after(seconds, callback):
        def fire():
            callback()
            return GLib.SOURCE_REMOVE

        return GLib.timeout_add_seconds(max(1, round(seconds)), fire)

    @staticmethod
    def cancel(handle):
        GLib.source_remove(handle)

    def idle_s(self, callback):
        self.island.idle.idle_ms(lambda ms: callback(None if ms is None else ms // 1000))

    @staticmethod
    def screen_asleep(callback):
        screen.asleep(callback)


class IslandGates:
    """What holds a reminder back: a Pomodoro focus phase, a fullscreen window in front."""

    def __init__(self, island):
        self.island = island
        self.watcher = FullscreenWatcher(island.wnck, self._on_fullscreen)

    def blocked(self):
        timer = self.island.timer
        if timer.running and timer.kind == "focus":
            return "focus"
        return "fullscreen" if self.watcher.fullscreen else None

    def watch(self, on):
        (self.watcher.start if on else self.watcher.stop)()

    def _on_fullscreen(self, fullscreen):
        if not fullscreen:
            self.island.stretch.release()


class StretchView:
    def __init__(self, island):
        self.island = island
        self.stretch = None            # set once the controller exists (it needs this view first)
        self._cd_id = 0
        self._cd_start = 0
        self._cd_total = 1

    # ---- what the island shows -------------------------------------------------------------
    def busy(self):
        """The card would not be seen or would trample another: the opened island, a screenshot or recording
        (the island is hidden), another card (a notification, recognised text). The reminder looks again shortly."""
        island = self.island
        card = island.current_card()
        return island.expanded or island.capturing or (card is not None and not card.get("stretch"))

    def alert(self, then):
        """The eyes blink twice (if they are on show), then the card comes."""
        def later():
            then()
            return GLib.SOURCE_REMOVE

        if self.island.blink_eyes():
            GLib.timeout_add(BLINK_HEADS_UP_MS, later)
        else:
            then()

    def card(self, spec):
        island, s, ex = self.island, self.stretch, spec.exercise
        if spec.kind == "reminder":
            title, body, meta = ex.name, ex.text, "Dehnpause · {seconds} s".format(seconds=ex.seconds)
            actions = [("Start", s.start, True),
                       ("Später", s.snooze, False) if spec.can_snooze else ("Überspringen", s.skip, False),
                       ("Heute aus", s.off_today, False), ("Aus", s.disable, False)]
            ms = CARD_REMINDER_MS + 5000 * spec.level
        elif spec.kind == "retry":
            title, meta = "Du warst am Rechner", ex.name
            body = "Noch mal? Lass Maus und Tastatur diesmal in Ruhe."
            actions = [("Noch mal", s.start, True), ("Überspringen", s.skip, False)]
            ms = CARD_ANSWER_MS
        else:
            title, meta = "Geschafft?", ex.name
            body = "Klick auf Erledigt, wenn du fertig bist."
            actions = [("Erledigt", s.confirm, True)]
            ms = CARD_ANSWER_MS
        big = spec.kind == "reminder" and spec.level > 0
        extra = {"width": BIG_CARD_W, "height": BIG_CARD_H, "big": True} if big else {}
        island.show_card(ICON, title, body, meta=meta, actions=actions, ms=ms, stretch=True, **extra)

    def symbol(self, on):
        self.island.set_stretch_mark(on)

    def countdown(self, name, seconds):
        self.countdown_stop()
        self._cd_start, self._cd_total = GLib.get_monotonic_time(), max(1, seconds)
        self.island.set_stretch_progress(name, 0.0, seconds)
        self._cd_id = GLib.timeout_add(COUNTDOWN_STEP_MS, self._countdown_step, name)

    def _countdown_step(self, name):
        elapsed = (GLib.get_monotonic_time() - self._cd_start) / 1_000_000
        remaining = max(0.0, self._cd_total - elapsed)
        self.island.set_stretch_progress(name, min(1.0, elapsed / self._cd_total), int(remaining + 0.999))
        return GLib.SOURCE_CONTINUE

    def countdown_stop(self):
        if self._cd_id:
            GLib.source_remove(self._cd_id)
            self._cd_id = 0
        self.island.set_stretch_progress(None)

    def sound(self, name, volume):
        tone.play(name, volume)

    def message(self, text, icon="", seconds=4):
        self.island.show_activity(icon or ICON, text, seconds=seconds)

    def clear(self):
        """The round is over (or the feature went off): no card, no mark, no ring."""
        self.countdown_stop()
        self.island.set_stretch_mark(False)
        self.island.drop_stretch_card()

    def changed(self):
        """Counts or switches changed: the tab and the tray show the new state."""
        self.island.on_stretch_changed()
