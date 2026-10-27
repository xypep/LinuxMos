"""The stretch reminder: when it falls due and how a round goes. No GTK in here.

The island feeds it through three small interfaces so the rules can be tested with a fake clock:

    env    after(seconds, callback) -> handle, cancel(handle), idle_s(callback), screen_asleep(callback), today()
    view   what the user sees (card, mark in the pill, countdown ring, chime, short messages)
    gates  blocked() -> "fullscreen" | "focus" | None, watch(on): what holds a reminder back

Counting: one coarse tick (every minute, every 5 minutes while away) asks for the idle time once. Input
within the last minute makes the tick count as active time; 5 minutes without input start the count over
(a real break replaces the stretching). When the active time reaches the interval the reminder is due; it
waits while a fullscreen window is in front or a Pomodoro focus phase runs, and is dropped if the screen is
off/locked or the last input is too old by then. Nothing runs while the feature is off.

A round: card -> (later | start | skip) -> countdown -> "done" (checked against the input during the
countdown) -> statistics. An ignored card comes back bigger, three times at most, then it counts as missed.
"""

import json
import logging
import random
from dataclasses import dataclass

from island.storage import CONFIG_DIR, DATA_DIR, load_json, save_json

log = logging.getLogger("mosisland.stretch")

EXERCISES_FILE = CONFIG_DIR / "stretch_exercises.json"
STATS_FILE = DATA_DIR / "stretch.json"
KEEP_DAYS = 30
VERIFY_RATIO = 0.7     # the idle time at the end of the countdown must be this share of its length
ESCALATE_MAX = 3
GIVE_UP_S = 600        # a countdown that is never confirmed counts as unconfirmed after this long
BUSY_RETRY_S = 10      # another card is up: look again after this long
LONG_EVERY = 4         # every 4th reminder is a long exercise (if the daily limit allows)
OUTCOMES = ("done", "unconfirmed", "snoozed", "skipped", "missed")


# =============================================================================
# Rules (everything that is a number)
# =============================================================================
@dataclass(frozen=True)
class Rules:
    interval_s: int = 45 * 60
    break_reset_s: int = 5 * 60
    idle_skip_s: int = 30 * 60
    active_window_s: int = 60      # input within this long = active
    tick_s: int = 60
    slow_tick_s: int = 5 * 60      # while away
    snooze_s: tuple = (5 * 60, 3 * 60)
    snooze_max: int = 2
    escalate_s: int = 3 * 60
    escalate: bool = True
    verify_idle: bool = True
    long_per_day: int = 2

    @classmethod
    def from_config(cls, cfg, test=False):
        if test:
            # --stretch-test: a minute of activity, thresholds and waits in seconds
            return cls(interval_s=60, break_reset_s=20, idle_skip_s=40, active_window_s=5, tick_s=5, slow_tick_s=10,
                       snooze_s=(10, 6), snooze_max=cfg.integer("stretch_snooze_max", 0, 5), escalate_s=15,
                       escalate=cfg.flag("stretch_escalate"), verify_idle=cfg.flag("stretch_verify_idle"),
                       long_per_day=cfg.integer("stretch_long_per_day", 0, 10))
        snooze = cfg.integer("stretch_snooze_min", 1, 60) * 60
        return cls(interval_s=cfg.integer("stretch_interval_min", 1, 600) * 60,
                   break_reset_s=cfg.integer("stretch_break_reset_min", 1, 120) * 60,
                   idle_skip_s=cfg.integer("stretch_idle_skip_min", 1, 600) * 60,
                   snooze_s=(snooze, max(60, round(snooze * 0.6 / 60) * 60)),
                   snooze_max=cfg.integer("stretch_snooze_max", 0, 5),
                   escalate=cfg.flag("stretch_escalate"), verify_idle=cfg.flag("stretch_verify_idle"),
                   long_per_day=cfg.integer("stretch_long_per_day", 0, 10))

    def snooze_length(self, nth):
        """Seconds of the nth later (0 = the first): the first one in full, the following ones shorter."""
        return self.snooze_s[min(nth, len(self.snooze_s) - 1)]


class ActivityCounter:
    """Active seconds since the last real break; fed one idle measurement per tick."""

    def __init__(self, rules):
        self.rules = rules
        self.active_s = 0

    def reset(self):
        self.active_s = 0

    def sample(self, idle_s):
        """'away' (a break: the count starts over), 'quiet' (not at the keyboard just now) or 'active' (+1 tick)."""
        rules = self.rules
        if idle_s >= rules.break_reset_s:
            self.active_s = 0
            return "away"
        if idle_s >= rules.active_window_s:
            return "quiet"
        self.active_s += rules.tick_s
        return "active"

    @property
    def due(self):
        return self.active_s >= self.rules.interval_s


# =============================================================================
# Exercises (the user's own list in stretch_exercises.json)
# =============================================================================
@dataclass(frozen=True)
class Exercise:
    name: str
    text: str
    seconds: int
    long: bool = False


DEFAULT_EXERCISES = [
    Exercise("Aufstehen und strecken", "Steh auf, recke dich und streck dich so weit wie möglich.", 15),
    Exercise("Arme über den Kopf", "Hände verschränken, Arme nach oben strecken und leicht zur Seite lehnen.", 15),
    Exercise("Schultern kreisen", "Beide Schultern langsam nach hinten kreisen lassen, den Nacken locker.", 15),
    Exercise("Nacken seitlich neigen", "Ohr Richtung Schulter sinken lassen, nach der halben Zeit die Seite wechseln.", 20),
    Exercise("Handgelenke kreisen", "Hände zu Fäusten, Handgelenke in beide Richtungen kreisen lassen.", 15),
    Exercise("Rücken ins Hohlkreuz", "Aufstehen, Hände in die Hüften, den Oberkörper sanft nach hinten biegen.", 15),
    Exercise("Blick in die Ferne", "20-20-20: Schau 20 Sekunden lang auf etwas, das mindestens 6 Meter weit weg ist.", 20),
    Exercise("Kurz gehen, Wasser holen", "Steh auf, hol dir ein Glas Wasser und geh ein paar Schritte.", 20),
    Exercise("Hinlegen, Rücken entspannen", "Leg dich flach auf den Rücken, Beine angezogen, und atme ruhig.", 60, True),
    Exercise("Tiefe Kniebeuge halten", "Füße schulterbreit, tief in die Hocke gehen und die Position halten.", 30, True),
]


def _default_file_content():
    return [{"name": e.name, "text": e.text, "seconds": e.seconds, "long": e.long} for e in DEFAULT_EXERCISES]


def ensure_exercise_file(path=EXERCISES_FILE):
    """Make the user's exercise list with the default exercises if there is none yet. True if it was made."""
    if path.exists():
        return False
    try:
        save_json(path, _default_file_content())
        log.info("made %s with the default exercises", path)
        return True
    except OSError as error:
        log.warning("cannot write %s: %s", path, error)
        return False


def load_exercises(path=EXERCISES_FILE):
    """(exercises, problem): the user's list, made on first use. A broken file never stops the reminder.

    problem is None or a short German sentence for a message; the defaults are used then.
    """
    if not path.exists():
        ensure_exercise_file(path)
        return list(DEFAULT_EXERCISES), None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        log.warning("%s is not usable (%s): default exercises", path.name, error)
        return list(DEFAULT_EXERCISES), "Übungsdatei ungültig, Standardliste aktiv"
    items = raw if isinstance(raw, list) else []
    exercises = []
    for item in items:
        exercise = _exercise_from(item)
        if exercise is None:
            log.warning("%s: skipping %r", path.name, item)
        else:
            exercises.append(exercise)
    if not exercises:
        log.warning("%s holds no usable exercise: default list", path.name)
        return list(DEFAULT_EXERCISES), "Übungsdatei leer oder ungültig, Standardliste aktiv"
    return exercises, None


def _exercise_from(item):
    if not isinstance(item, dict):
        return None
    name, text, seconds = item.get("name"), item.get("text", ""), item.get("seconds")
    if not isinstance(name, str) or not name.strip() or not isinstance(text, str):
        return None
    if isinstance(seconds, bool) or not isinstance(seconds, (int, float)):
        return None
    return Exercise(name.strip(), text.strip(), int(min(max(seconds, 5), 300)), item.get("long") is True)


class Picker:
    """Shuffled rotation: every exercise of a kind comes up once before one repeats, never twice in a row."""

    def __init__(self, rng=None):
        self._rng = rng or random.Random()
        self._bags = {}

    def pick(self, exercises, want_long, last=""):
        pool = [e for e in exercises if e.long == want_long] or list(exercises)
        key = tuple(pool)
        bag = [e for e in self._bags.get(key, []) if e in pool]
        if not bag:
            bag = list(pool)
            self._rng.shuffle(bag)
            if len(bag) > 1 and bag[-1].name == last:    # pop() takes from the end: not the one we just had
                bag[0], bag[-1] = bag[-1], bag[0]
        elif bag[-1].name == last and len(bag) > 1:
            bag[0], bag[-1] = bag[-1], bag[0]
        choice = bag.pop()
        self._bags[key] = bag
        return choice


# =============================================================================
# Statistics: per day, the last 30 days
# =============================================================================
class Stats:
    def __init__(self, path=STATS_FILE):
        self.path = path
        data = load_json(path, {})
        data = data if isinstance(data, dict) else {}
        self.days = data.get("days") if isinstance(data.get("days"), dict) else {}
        state = data.get("state") if isinstance(data.get("state"), dict) else {}
        self.count = state.get("count") if isinstance(state.get("count"), int) else 0
        self.last = state.get("last") if isinstance(state.get("last"), str) else ""

    def day(self, day):
        entry = self.days.get(day)
        entry = entry if isinstance(entry, dict) else {}
        return {key: entry.get(key, 0) if isinstance(entry.get(key, 0), int) else 0 for key in (*OUTCOMES, "long")}

    def record(self, day, outcome):
        """Count an outcome ('done', ..., or 'long' for a long exercise shown) for the day and save."""
        entry = self.day(day)
        entry[outcome] += 1
        self.days[day] = entry
        self._save()

    def shown(self, name):
        """A reminder was shown: the rotation counter moves on."""
        self.count += 1
        self.last = name
        self._save()

    def _save(self):
        keep = sorted(self.days)[-KEEP_DAYS:]
        self.days = {day: self.days[day] for day in keep}
        try:
            save_json(self.path, {"days": self.days, "state": {"count": self.count, "last": self.last}})
        except OSError as error:
            log.warning("cannot save %s: %s", self.path, error)


# =============================================================================
# The reminder
# =============================================================================
@dataclass
class Round:
    exercise: Exercise
    phase: str = "card"        # card | snoozed | countdown | confirm | retry
    snoozes: int = 0
    escalations: int = 0       # how often the card came back bigger
    attempt: int = 0           # countdowns started
    verified: bool = True      # the idle check at the end of the last countdown


@dataclass(frozen=True)
class CardSpec:
    kind: str                  # reminder | retry | confirm
    exercise: Exercise
    level: int                 # 0..ESCALATE_MAX: bigger and louder with every return
    can_snooze: bool


class Stretch:
    def __init__(self, config, env, view, gates, stats=None, test=False, rng=None):
        self.config = config
        self.env = env
        self.view = view
        self.gates = gates
        self.stats = stats or Stats()
        self.test = test
        self.rules = Rules.from_config(config, test)
        self.counter = ActivityCounter(self.rules)
        self.picker = Picker(rng)
        self.round = None
        self.pending = False        # due, waiting for the gates (fullscreen, focus)
        self.running = False        # counting active time
        self.unavailable = False    # the idle time can't be measured
        self._tick = self._round_timer = self._countdown = self._give_up = None
        self._slow = False

    # ---- on / off ------------------------------------------------------------
    def enabled(self):
        return self.config.flag("stretch_enabled") and self.config.get("stretch_off_date") != self.env.today()

    def apply(self):
        """Start, stop or retune according to the config (start-up, tray, card buttons, edited file)."""
        self.rules = Rules.from_config(self.config, self.test)
        self.counter.rules = self.rules
        if not self.enabled():
            if self.running or self.round or self.pending or self._tick:
                self._stop()
            log.info("disabled, no timers%s", " (off today)" if self.config.flag("stretch_enabled") else "")
            self.view.changed()
            return
        if self.unavailable:
            return
        if not self.running:
            self.running = True
            self.gates.watch(True)
            log.info("enabled: reminder after %d min of activity (tick %d s)%s", self.rules.interval_s // 60,
                     self.rules.tick_s, ", test mode" if self.test else "")
            ensure_exercise_file()    # the user's list, made the first time the reminder runs
            if self.round is None and not self.pending:
                self._schedule_tick(self.rules.tick_s)
        self.view.changed()

    def _stop(self):
        for name in ("_tick", "_round_timer", "_countdown", "_give_up"):
            self._cancel(name)
        self.running = self.pending = False
        self.round = None
        self.counter.reset()
        self.gates.watch(False)
        self.view.clear()

    def on_minute(self):
        """Called by the island's clock: the day changed, so 'today off' is over (no timer of our own for it)."""
        if not self.running and not self.unavailable and self.config.flag("stretch_enabled") \
                and self.config.get("stretch_off_date") and self.enabled():
            log.info("a new day: back on")
            self.apply()

    # ---- timers -----------------------------------------------------------------
    def _arm(self, name, seconds, callback):
        self._cancel(name)
        setattr(self, name, self.env.after(seconds, callback))

    def _cancel(self, name):
        handle = getattr(self, name)
        if handle is not None:
            self.env.cancel(handle)
            setattr(self, name, None)

    def _schedule_tick(self, seconds):
        self._slow = seconds == self.rules.slow_tick_s
        self._arm("_tick", seconds, self._on_tick)

    def user_back(self):
        """The user touched the keyboard after a long break: count again at the normal pace right away."""
        if self.running and self._tick is not None and self._slow:
            self._schedule_tick(self.rules.tick_s)

    # ---- counting --------------------------------------------------------------------
    def _on_tick(self):
        self._tick = None
        self.env.idle_s(self._on_sample)    # the one idle query of this tick

    def _on_sample(self, idle_s):
        if not self.running or self.round is not None or self.pending:
            return
        if idle_s is None:
            self._give_up_counting()
            return
        kind = self.counter.sample(idle_s)
        log.debug("idle %ds -> %s, %ds of %ds active", idle_s, kind, self.counter.active_s, self.rules.interval_s)
        if self.counter.due:
            log.info("due after %d min of activity", self.counter.active_s // 60)
            self.pending = True
            self._try_show()
        else:
            self._schedule_tick(self.rules.slow_tick_s if kind == "away" else self.rules.tick_s)

    def _give_up_counting(self):
        log.warning("the idle time can't be measured: stretch reminder paused")
        self.unavailable = True
        self.running = False
        self.gates.watch(False)
        self.view.message("Dehn-Erinnerung pausiert: Leerlaufzeit nicht messbar", "dialog-warning-symbolic", 6)

    # ---- due: wait for the gates, check the user is there, show ----------------------------
    def release(self):
        """A gate opened (fullscreen left, focus phase over): show what was held back."""
        if self.pending and self.round is None and not self.gates.blocked():
            self._try_show()

    def _try_show(self):
        reason = self.gates.blocked()
        if reason:
            log.info("due, waiting (%s)", reason)
            return
        self.env.idle_s(self._checked_idle)

    def _checked_idle(self, idle_s):
        if not self.pending or self.round is not None:
            return
        rules = self.rules
        if idle_s is not None and idle_s >= min(rules.break_reset_s, rules.idle_skip_s):
            self._drop(f"last input {idle_s // 60} min ago, a break replaced it")
        else:
            self.env.screen_asleep(self._checked_screen)

    def _checked_screen(self, asleep):
        if not self.pending or self.round is not None:
            return
        if asleep:
            self._drop("screen off or locked")
        else:
            self._start_round()

    def _drop(self, why):
        log.info("dropped (%s), counting again", why)
        self.pending = False
        self.counter.reset()
        if self.running:
            self._schedule_tick(self.rules.tick_s)

    # ---- a round -----------------------------------------------------------------------
    def trigger_now(self):
        """'Stretch now' (tab, --stretch-now): a reminder at once, whatever the gates and the counter say."""
        if self.round is not None:
            self.reshow()
            return
        self._cancel("_tick")
        self.pending = True
        self._start_round()

    def _start_round(self):
        today = self.env.today()
        exercises, problem = load_exercises()    # read every time: edits to the file count without a restart
        if problem:
            self.view.message(problem, "dialog-warning-symbolic", 5)
        want_long = (self.stats.count + 1) % LONG_EVERY == 0 and self.stats.day(today)["long"] < self.rules.long_per_day
        exercise = self.picker.pick(exercises, want_long, self.stats.last)
        self.pending = False
        self.round = Round(exercise)
        self.stats.shown(exercise.name)
        if exercise.long:
            self.stats.record(today, "long")
        log.info("reminder: %s (%d s%s)", exercise.name, exercise.seconds, ", long" if exercise.long else "")
        self.view.alert(self._present)
        self.view.changed()

    def _spec(self):
        r = self.round
        kind = {"confirm": "confirm", "retry": "retry"}.get(r.phase, "reminder")
        return CardSpec(kind, r.exercise, r.escalations, r.snoozes < self.rules.snooze_max)

    def _present(self, quiet=False):
        """Put the card for the current phase up (and the mark in the pill, which stays when the card folds)."""
        r = self.round
        if r is None:
            return
        if self.view.busy():
            self._arm("_round_timer", BUSY_RETRY_S, lambda: self._present(quiet))
            return
        r.phase = "card" if r.phase == "snoozed" else r.phase
        self.view.symbol(True)
        self.view.card(self._spec())
        if r.phase == "card":
            if not quiet:
                self._sound("chime-up" if r.escalations else "chime")
            # An escalating card comes back; without escalation it is simply missed after the same time
            wait = self.rules.escalate_s * (1 if self.rules.escalate else ESCALATE_MAX + 1)
            self._arm("_round_timer", wait, self._on_ignored)
        else:
            self._arm("_give_up", GIVE_UP_S, self._on_give_up)

    def _on_ignored(self):
        self._round_timer = None
        r = self.round
        if r is None or r.phase != "card":
            return
        if self.rules.escalate and r.escalations < ESCALATE_MAX:
            r.escalations += 1
            log.info("ignored: the card comes back bigger (%d of %d)", r.escalations, ESCALATE_MAX)
            self._present()
        else:
            self._finish("missed")

    def reshow(self):
        """The mark in the pill was clicked: the card again (a later is over when you ask for it)."""
        r = self.round
        if r is None or r.phase == "countdown":
            return
        self._cancel("_round_timer")
        self._present(quiet=True)

    def _sound(self, name):
        if self.config.flag("stretch_sound"):
            self.view.sound(name, self.config.number("stretch_volume", 0, 1))

    # ---- the user's answers -------------------------------------------------------------------
    def start(self):
        r = self.round
        if r is None or r.phase not in ("card", "snoozed", "retry"):
            return
        for name in ("_round_timer", "_give_up"):
            self._cancel(name)
        r.attempt += 1
        r.phase = "countdown"
        self.view.symbol(False)
        self.view.countdown(r.exercise.name, r.exercise.seconds)
        self._arm("_countdown", r.exercise.seconds, self._countdown_done)
        log.info("countdown %d s (attempt %d)", r.exercise.seconds, r.attempt)

    def snooze(self):
        r = self.round
        if r is None or r.phase != "card" or r.snoozes >= self.rules.snooze_max:
            return
        wait = self.rules.snooze_length(r.snoozes)
        r.snoozes += 1
        r.phase = "snoozed"
        self.stats.record(self.env.today(), "snoozed")
        self._arm("_round_timer", wait, self._present)
        log.info("later (%d of %d), again in %d s", r.snoozes, self.rules.snooze_max, wait)
        self.view.changed()

    def skip(self):
        if self.round is not None:
            self._finish("skipped")

    def off_today(self):
        self.config["stretch_off_date"] = self.env.today()
        self.config.save()
        self.apply()
        self.view.message("Heute aus · morgen geht es wieder los", "avatar-default-symbolic", 5)

    def disable(self):
        self.config["stretch_enabled"] = False
        self.config.save()
        self.apply()
        self.view.message("Dehn-Erinnerung aus · einschalten: Tray › Dehnen", "avatar-default-symbolic", 7)

    def on_today(self, on):
        """Tray / tab switch for 'today off'."""
        self.config["stretch_off_date"] = self.env.today() if on else ""
        self.config.save()
        self.apply()

    def _countdown_done(self):
        self._countdown = None
        r = self.round
        if r is None or r.phase != "countdown":
            return
        self.view.countdown_stop()
        self._sound("chime")

        def checked(idle_s):
            if self.round is not r:
                return
            r.verified = (not self.rules.verify_idle or idle_s is None
                          or idle_s >= VERIFY_RATIO * r.exercise.seconds)
            log.info("countdown over: idle %s s of %d s -> %s", "?" if idle_s is None else idle_s,
                     r.exercise.seconds, "verified" if r.verified else "was at the computer")
            r.phase = "confirm"
            self._present()

        if self.rules.verify_idle:
            self.env.idle_s(checked)    # the answer to 'done' is decided now, not when the button is clicked
        else:
            checked(None)

    def confirm(self):
        """'Done' after the countdown."""
        r = self.round
        if r is None or r.phase != "confirm":
            return
        if r.verified:
            self.view.message("Gut gemacht · erledigt", "emblem-ok-symbolic", 3)
            self._finish("done")
        elif r.attempt < 2:
            r.phase = "retry"
            self._present()
        else:
            self.view.message("Zählt als unbestätigt", "dialog-information-symbolic", 4)
            self._finish("unconfirmed")

    def _on_give_up(self):
        self._give_up = None
        if self.round is not None:
            self._finish("unconfirmed")    # the exercise was done, only the answer never came

    def _finish(self, outcome):
        for name in ("_round_timer", "_countdown", "_give_up"):
            self._cancel(name)
        if outcome:
            self.stats.record(self.env.today(), outcome)
        log.info("round over: %s", outcome)
        self.round = None
        self.view.clear()
        self.view.changed()
        self.counter.reset()
        if self.running:
            self._schedule_tick(self.rules.tick_s)

    # ---- for the tab ---------------------------------------------------------------------------
    def today(self):
        return self.stats.day(self.env.today())

