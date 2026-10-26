"""Rules of the stretch reminder with a fake clock (python3 -m unittest discover tests)."""

import json
import random
import unittest

from tests import _sandbox  # noqa: F401  (must come first)
from island import storage
from island.services import stretch
from island.services.stretch import Rules, Stretch


class FakeEnv:
    """A clock you wind by hand; idle time and screen state are whatever the test says."""

    def __init__(self):
        self.now = 0.0
        self.day = "2026-10-26"
        self.idle = 0
        self.asleep = False
        self.idle_queries = 0
        self._timers = {}
        self._next = 1

    def today(self):
        return self.day

    def after(self, seconds, callback):
        handle, self._next = self._next, self._next + 1
        self._timers[handle] = (self.now + max(1, round(seconds)), callback)
        return handle

    def cancel(self, handle):
        self._timers.pop(handle, None)

    def idle_s(self, callback):
        self.idle_queries += 1
        callback(self.idle() if callable(self.idle) else self.idle)

    def screen_asleep(self, callback):
        callback(self.asleep)

    @property
    def timers(self):
        return len(self._timers)

    def advance(self, seconds):
        end = self.now + seconds
        while True:
            due = [(when, handle) for handle, (when, _cb) in self._timers.items() if when <= end]
            if not due:
                break
            when, handle = min(due)
            self.now = when
            _when, callback = self._timers.pop(handle)
            callback()
        self.now = end


class FakeView:
    def __init__(self):
        self.cards, self.sounds, self.messages = [], [], []
        self.symbol_on = False
        self.countdowns = []
        self.countdown_running = False
        self.busy_now = False
        self.cleared = 0

    def busy(self):
        return self.busy_now

    def alert(self, then):
        then()

    def card(self, spec):
        self.cards.append(spec)

    def symbol(self, on):
        self.symbol_on = on

    def countdown(self, name, seconds):
        self.countdowns.append((name, seconds))
        self.countdown_running = True

    def countdown_stop(self):
        self.countdown_running = False

    def sound(self, name, volume):
        self.sounds.append(name)

    def message(self, text, icon="", seconds=4):
        self.messages.append(text)

    def clear(self):
        self.cleared += 1
        self.symbol_on = False

    def changed(self):
        pass


class FakeGates:
    def __init__(self):
        self.reason = None
        self.watching = False

    def blocked(self):
        return self.reason

    def watch(self, on):
        self.watching = on


def make(config_changes=None, rules=None, test=False):
    config = storage.Config(storage.DEFAULT_CONFIG)
    config.update(config_changes or {})
    env, view, gates = FakeEnv(), FakeView(), FakeGates()
    stats = stretch.Stats(storage.DATA_DIR / f"stats-{random.random()}.json")
    s = Stretch(config, env, view, gates, stats=stats, test=test, rng=random.Random(1))
    if rules:
        s.rules = s.counter.rules = rules
    return s, env, view, gates


def run_until_card(s, env, step=60, limit=100):
    for _ in range(limit):
        if s.round is not None:
            return True
        env.advance(step)
    return s.round is not None


class Counting(unittest.TestCase):
    def test_active_time_makes_a_card_after_the_interval(self):
        s, env, view, _gates = make()
        s.apply()
        env.advance(44 * 60)
        self.assertIsNone(s.round)
        env.advance(2 * 60)
        self.assertIsNotNone(s.round)
        self.assertEqual(view.cards[-1].kind, "reminder")
        self.assertTrue(view.symbol_on)
        self.assertEqual(view.sounds, ["chime"])

    def test_one_idle_query_per_tick(self):
        s, env, _view, _gates = make()
        s.apply()
        env.advance(10 * 60)
        self.assertEqual(env.idle_queries, 10)

    def test_input_older_than_a_minute_is_not_active(self):
        s, env, _view, _gates = make()
        env.idle = 90
        s.apply()
        env.advance(60 * 60)
        self.assertIsNone(s.round)
        self.assertEqual(s.counter.active_s, 0)

    def test_a_five_minute_break_starts_over(self):
        s, env, _view, _gates = make()
        s.apply()
        env.advance(40 * 60)
        self.assertEqual(s.counter.active_s, 40 * 60)
        env.idle = 5 * 60
        env.advance(60)
        self.assertEqual(s.counter.active_s, 0)
        env.idle = 0
        env.advance(10 * 60)
        # counting resumed with the slow tick (5 minutes after the break), then a tick a minute
        self.assertEqual(s.counter.active_s, 6 * 60)
        self.assertIsNone(s.round)

    def test_ticks_slow_down_while_away_and_speed_up_on_return(self):
        s, env, _view, _gates = make()
        env.idle = 600
        s.apply()
        env.advance(60)
        before = env.idle_queries
        env.advance(10 * 60)
        self.assertEqual(env.idle_queries - before, 2)           # one per 5 minutes
        env.idle = 0
        s.user_back()
        before = env.idle_queries
        env.advance(60)
        self.assertEqual(env.idle_queries - before, 1)

    def test_unmeasurable_idle_pauses_without_timers(self):
        s, env, view, gates = make()
        env.idle = lambda: None
        s.apply()
        env.advance(60)
        self.assertEqual(env.timers, 0)
        self.assertFalse(gates.watching)
        self.assertTrue(view.messages)


class Gates(unittest.TestCase):
    def due(self, s, env):
        s.apply()
        env.advance(44 * 60)

    def test_fullscreen_holds_the_card_back_until_it_is_released(self):
        s, env, view, gates = make()
        gates.reason = "fullscreen"
        self.due(s, env)
        env.advance(5 * 60)
        self.assertTrue(s.pending)
        self.assertEqual(view.cards, [])
        gates.reason = None
        s.release()
        self.assertEqual(len(view.cards), 1)
        self.assertFalse(s.pending)

    def test_focus_timer_holds_it_back_and_the_end_of_focus_shows_it(self):
        s, env, view, gates = make()
        gates.reason = "focus"
        self.due(s, env)
        env.advance(5 * 60)
        self.assertEqual(view.cards, [])
        gates.reason = None
        s.release()
        self.assertEqual(len(view.cards), 1)

    def test_release_with_nothing_due_does_nothing(self):
        s, env, view, _gates = make()
        s.apply()
        env.advance(10 * 60)
        queries = env.idle_queries
        s.release()
        self.assertEqual((view.cards, env.idle_queries), ([], queries))

    def test_a_break_while_waiting_replaces_the_stretching(self):
        s, env, view, gates = make()
        gates.reason = "fullscreen"
        self.due(s, env)
        env.advance(60)
        env.idle = 12 * 60
        gates.reason = None
        s.release()
        self.assertEqual(view.cards, [])
        self.assertFalse(s.pending)
        self.assertEqual(s.counter.active_s, 0)

    def test_screen_off_or_locked_drops_the_reminder_and_counting_restarts(self):
        s, env, view, _gates = make()
        env.asleep = True
        self.due(s, env)
        env.advance(2 * 60)
        self.assertEqual(view.cards, [])
        self.assertEqual(s.counter.active_s, 60)     # counting again from the return

    def test_old_last_input_drops_it(self):
        rules = Rules(idle_skip_s=10 * 60, break_reset_s=60 * 60)
        s, env, view, gates = make(rules=rules)
        gates.reason = "fullscreen"
        self.due(s, env)
        env.idle = 20 * 60
        gates.reason = None
        s.release()
        self.assertEqual(view.cards, [])

    def test_busy_island_delays_the_card(self):
        s, env, view, _gates = make()
        view.busy_now = True
        self.due(s, env)
        env.advance(3 * 60)
        self.assertEqual(view.cards, [])
        view.busy_now = False
        env.advance(stretch.BUSY_RETRY_S)
        self.assertEqual(len(view.cards), 1)


class RoundFlow(unittest.TestCase):
    def setUp(self):
        self.s, self.env, self.view, self.gates = make()
        self.s.apply()
        self.assertTrue(run_until_card(self.s, self.env))

    def test_later_twice_then_only_start_or_skip(self):
        s, env, view = self.s, self.env, self.view
        self.assertTrue(view.cards[-1].can_snooze)
        s.snooze()
        env.advance(5 * 60 - 1)
        self.assertEqual(len(view.cards), 1)
        env.advance(1)
        self.assertEqual(len(view.cards), 2)
        s.snooze()
        env.advance(3 * 60)                                  # the second one is shorter
        self.assertEqual(len(view.cards), 3)
        self.assertFalse(view.cards[-1].can_snooze)
        s.snooze()                                           # no third one
        self.assertEqual(s.round.phase, "card")
        self.assertEqual(s.stats.day(env.today())["snoozed"], 2)
        s.skip()
        self.assertEqual(s.stats.day(env.today())["skipped"], 1)
        self.assertIsNone(s.round)

    def test_ignored_card_comes_back_bigger_three_times_then_missed(self):
        s, env, view = self.s, self.env, self.view
        for level in (1, 2, 3):
            env.advance(3 * 60)
            self.assertEqual(view.cards[-1].level, level)
        self.assertEqual(view.sounds, ["chime", "chime-up", "chime-up", "chime-up"])
        env.advance(3 * 60)
        self.assertIsNone(s.round)
        self.assertEqual(s.stats.day(env.today())["missed"], 1)
        self.assertFalse(view.symbol_on)
        env.advance(60)
        self.assertEqual(env.idle_queries > 0 and s.counter.active_s, 60)    # counting again

    def test_no_escalation_when_switched_off(self):
        s, env, view, _gates = make({"stretch_escalate": False})
        s.apply()
        self.assertTrue(run_until_card(s, env))
        env.advance(12 * 60)
        self.assertEqual(len(view.cards), 1)
        self.assertEqual(view.sounds, ["chime"])
        self.assertEqual(s.stats.day(env.today())["missed"], 1)

    def test_countdown_without_input_is_confirmed(self):
        s, env, view = self.s, self.env, self.view
        seconds = s.round.exercise.seconds
        s.start()
        self.assertEqual(view.countdowns[-1][1], seconds)
        self.assertFalse(view.symbol_on)
        env.idle = seconds - 1                           # the last input was at the start
        env.advance(seconds)
        self.assertEqual(view.cards[-1].kind, "confirm")
        s.confirm()
        self.assertEqual(s.stats.day(env.today())["done"], 1)
        self.assertIsNone(s.round)

    def test_sitting_on_the_computer_is_not_confirmed_twice_then_unconfirmed(self):
        s, env, view = self.s, self.env, self.view
        seconds = s.round.exercise.seconds
        env.idle = 1                                     # moving the mouse the whole time
        s.start()
        env.advance(seconds)
        s.confirm()
        self.assertEqual(view.cards[-1].kind, "retry")
        self.assertEqual(s.stats.day(env.today())["done"], 0)
        s.start()
        env.advance(seconds)
        s.confirm()
        self.assertIsNone(s.round)
        day = s.stats.day(env.today())
        self.assertEqual((day["unconfirmed"], day["done"]), (1, 0))

    def test_second_try_can_succeed(self):
        s, env, view = self.s, self.env, self.view
        seconds = s.round.exercise.seconds
        env.idle = 1
        s.start()
        env.advance(seconds)
        s.confirm()
        env.idle = seconds
        s.start()
        env.advance(seconds)
        s.confirm()
        self.assertEqual(s.stats.day(env.today())["done"], 1)

    def test_verify_off_always_confirms(self):
        s, env, _view = self.s, self.env, self.view
        s.config["stretch_verify_idle"] = False
        s.apply()
        env.idle = 0
        s.start()
        env.advance(s.round.exercise.seconds)
        s.confirm()
        self.assertEqual(s.stats.day(env.today())["done"], 1)

    def test_a_countdown_nobody_confirms_counts_as_unconfirmed(self):
        s, env, _view = self.s, self.env, self.view
        env.idle = 100
        s.start()
        env.advance(s.round.exercise.seconds)
        env.advance(stretch.GIVE_UP_S)
        self.assertIsNone(s.round)
        self.assertEqual(s.stats.day(env.today())["unconfirmed"], 1)

    def test_clicking_the_mark_shows_the_card_again_without_a_sound(self):
        s, env, view = self.s, self.env, self.view
        s.snooze()
        s.reshow()
        self.assertEqual(len(view.cards), 2)
        self.assertEqual(view.sounds, ["chime"])
        env.advance(60 * 60)                              # the old snooze timer is gone
        self.assertEqual(s.stats.day(env.today())["snoozed"], 1)


class OffSwitches(unittest.TestCase):
    def test_disabled_runs_no_timers_and_asks_nothing(self):
        s, env, view, gates = make({"stretch_enabled": False})
        s.apply()
        env.advance(5 * 3600)
        self.assertEqual((env.timers, env.idle_queries, gates.watching), (0, 0, False))

    def test_switching_off_mid_round_stops_everything(self):
        s, env, view, gates = make()
        s.apply()
        run_until_card(s, env)
        s.disable()
        self.assertEqual((env.timers, s.round, gates.watching), (0, None, False))
        self.assertFalse(view.symbol_on)
        self.assertFalse(s.config["stretch_enabled"])
        queries = env.idle_queries
        env.advance(3600)
        self.assertEqual(env.idle_queries, queries)

    def test_today_off_ends_at_midnight(self):
        s, env, _view, gates = make()
        s.apply()
        s.on_today(True)
        self.assertEqual(env.timers, 0)
        env.advance(3600)
        s.on_minute()
        self.assertFalse(s.running)
        env.day = "2026-10-27"
        s.on_minute()
        self.assertTrue(s.running)
        self.assertTrue(gates.watching)
        self.assertGreater(env.timers, 0)

    def test_switch_on_again(self):
        s, env, _view, _gates = make({"stretch_enabled": False})
        s.apply()
        s.config["stretch_enabled"] = True
        s.apply()
        env.advance(120)
        self.assertEqual(env.idle_queries, 2)

    def test_stretch_now_works_even_when_off_and_leaves_nothing_behind(self):
        s, env, view, _gates = make({"stretch_enabled": False})
        s.apply()
        s.trigger_now()
        self.assertEqual(len(view.cards), 1)
        s.skip()
        self.assertEqual(env.timers, 0)


class TestMode(unittest.TestCase):
    def test_a_minute_interval_and_second_thresholds(self):
        s, env, view, _gates = make(test=True)
        s.apply()
        env.advance(55)
        self.assertEqual(view.cards, [])
        env.advance(10)
        self.assertEqual(len(view.cards), 1)
        self.assertEqual(s.rules.break_reset_s, 20)


class Exercises(unittest.TestCase):
    def setUp(self):
        self.path = storage.CONFIG_DIR / f"exercises-{random.random()}.json"

    def test_first_start_writes_the_default_list(self):
        exercises, problem = stretch.load_exercises(self.path)
        self.assertIsNone(problem)
        self.assertEqual(len(exercises), 10)
        written = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(set(written[0]), {"name", "text", "seconds", "long"})
        self.assertEqual(sum(1 for e in exercises if e.long), 2)
        self.assertTrue(all(10 <= e.seconds <= 20 for e in exercises if not e.long))
        self.assertTrue(all(30 <= e.seconds <= 60 for e in exercises if e.long))

    def test_the_reminder_makes_the_file_when_it_first_runs_and_never_when_off(self):
        stretch.EXERCISES_FILE.unlink(missing_ok=True)
        s, _env, _view, _gates = make({"stretch_enabled": False})
        s.apply()
        self.assertFalse(stretch.EXERCISES_FILE.exists())
        s.config["stretch_enabled"] = True
        s.apply()
        self.assertTrue(stretch.EXERCISES_FILE.exists())

    def test_own_entries_and_garbage(self):
        self.path.write_text(json.dumps([{"name": "Dehnen", "text": "x", "seconds": 12},
                                         {"name": "", "seconds": 5}, "junk", {"name": "A", "seconds": "x"},
                                         {"name": "Lang", "seconds": 999, "long": True}]), encoding="utf-8")
        exercises, problem = stretch.load_exercises(self.path)
        self.assertIsNone(problem)
        self.assertEqual([(e.name, e.seconds, e.long) for e in exercises], [("Dehnen", 12, False), ("Lang", 300, True)])

    def test_broken_file_gives_the_defaults_and_stays_untouched(self):
        self.path.write_text("[ nope", encoding="utf-8")
        exercises, problem = stretch.load_exercises(self.path)
        self.assertEqual(len(exercises), 10)
        self.assertIsNotNone(problem)
        self.assertEqual(self.path.read_text(encoding="utf-8"), "[ nope")

    def test_rotation_never_repeats_directly_and_visits_all(self):
        picker = stretch.Picker(random.Random(3))
        short = [e for e in stretch.DEFAULT_EXERCISES if not e.long]
        last, seen = "", []
        for _ in range(len(short) * 6):
            choice = picker.pick(stretch.DEFAULT_EXERCISES, False, last)
            self.assertNotEqual(choice.name, last)
            self.assertFalse(choice.long)
            seen.append(choice.name)
            last = choice.name
        self.assertEqual(set(seen), {e.name for e in short})
        for window in range(0, len(seen) - len(short) + 1, len(short)):
            self.assertEqual(len(set(seen[window:window + len(short)])), len(short))   # a full pass before repeats

    def test_every_fourth_is_long_at_most_twice_a_day(self):
        s, env, view, _gates = make()
        kinds = []
        for _ in range(12):
            s.trigger_now()
            kinds.append(s.round.exercise.long)
            s.skip()
        self.assertEqual(kinds, [False, False, False, True, False, False, False, True, False, False, False, False])
        env.day = "2026-10-27"
        kinds = []
        for _ in range(4):
            s.trigger_now()
            kinds.append(s.round.exercise.long)
            s.skip()
        self.assertEqual(kinds, [False, False, False, True])         # counter keeps going, the cap is per day


class StatsFile(unittest.TestCase):
    def test_only_thirty_days_are_kept(self):
        path = storage.DATA_DIR / "stats-prune.json"
        stats = stretch.Stats(path)
        for day in range(1, 41):
            stats.record(f"2026-09-{day:02d}" if day <= 30 else f"2026-10-{day - 30:02d}", "done")
        reloaded = stretch.Stats(path)
        self.assertEqual(len(reloaded.days), 30)
        self.assertNotIn("2026-09-01", reloaded.days)
        self.assertIn("2026-10-10", reloaded.days)

    def test_persists_counts_and_rotation(self):
        path = storage.DATA_DIR / "stats-persist.json"
        stats = stretch.Stats(path)
        stats.shown("Schultern kreisen")
        stats.record("2026-10-26", "missed")
        again = stretch.Stats(path)
        self.assertEqual((again.count, again.last, again.day("2026-10-26")["missed"]), (1, "Schultern kreisen", 1))


if __name__ == "__main__":
    unittest.main()
