"""Water reminder: daily goal, drink log, gentle reminders during the active hours."""

import time
from datetime import datetime, timedelta

from gi.repository import GLib

from island.storage import DATA_DIR, load_json, save_json

WATER_FILE = DATA_DIR / "water.json"
KEEP_DAYS = 14


def _hm(text, fallback):
    try:
        hour, minute = (int(x) for x in str(text).split(":"))
        return hour, minute
    except ValueError:
        return fallback


class Water:
    def __init__(self, config, on_change, on_remind):
        self.config = config
        self._on_change = on_change
        self._on_remind = on_remind
        self._timer = 0
        self._last_reminder = None
        self._started = datetime.now()
        stored = load_json(WATER_FILE, [])
        cutoff = time.time() - KEEP_DAYS * 86400
        self.log = [e for e in stored if isinstance(e, list) and len(e) == 2 and e[0] >= cutoff]
        self.schedule()

    # ---- settings ------------------------------------------------------------
    @property
    def goal(self):
        return int(self.config.get("water_goal_ml", 2000))

    @property
    def portion(self):
        return int(self.config.get("water_portion_ml", 250))

    # ---- log -----------------------------------------------------------------
    def today_entries(self):
        start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
        return [e for e in self.log if e[0] >= start]

    @property
    def today_ml(self):
        return sum(ml for _t, ml in self.today_entries())

    def per_hour(self):
        hours = [0] * 24
        for t, ml in self.today_entries():
            hours[datetime.fromtimestamp(t).hour] += ml
        return hours

    def drink(self, ml=None):
        self.log.append([time.time(), int(ml or self.portion)])
        self._changed()

    def undo(self):
        today = self.today_entries()
        if today:
            self.log.remove(today[-1])
            self._changed()

    def _changed(self):
        save_json(WATER_FILE, self.log)
        self.schedule()
        self._on_change()

    # ---- reminders -----------------------------------------------------------
    def schedule(self):
        """Arm a single timeout for the next reminder (or none at all)."""
        if self._timer:
            GLib.source_remove(self._timer)
            self._timer = 0
        if not self.config.get("water_reminders", True):
            return
        nxt = self._next_reminder(datetime.now())
        if nxt:
            delay = (nxt - datetime.now()).total_seconds()
            self._timer = GLib.timeout_add_seconds(int(max(1, min(delay, 1800))), self._fire)

    def _next_reminder(self, now):
        start_h, start_m = _hm(self.config.get("water_start", "09:00"), (9, 0))
        end_h, end_m = _hm(self.config.get("water_end", "21:00"), (21, 0))
        interval = timedelta(minutes=max(15, int(self.config.get("water_interval_min", 60))))
        day_start = now.replace(hour=start_h, minute=start_m, second=0, microsecond=0)
        day_end = now.replace(hour=end_h, minute=end_m, second=0, microsecond=0)

        if self.today_ml >= self.goal or now >= day_end:
            return day_start + timedelta(days=1) + interval  # tomorrow
        # One interval after the last drink or the last reminder, whichever came later
        today = self.today_entries()
        events = [datetime.fromtimestamp(today[-1][0])] if today else []
        if self._last_reminder and self._last_reminder.date() == now.date():
            events.append(self._last_reminder)
        # Nothing yet today: count from when the island started (no reminder right at login)
        base = max(events) if events else max(day_start, self._started)
        candidate = max(base + interval, day_start + interval)
        return candidate if candidate < day_end else day_start + timedelta(days=1) + interval

    def _fire(self):
        self._timer = 0
        now = datetime.now()
        nxt = self._next_reminder(now)
        # Fire only if we really reached the reminder time (the timeout is capped at 30 min)
        if nxt and nxt <= now + timedelta(seconds=5) and self.today_ml < self.goal:
            self._last_reminder = now
            self._on_remind()
        self.schedule()
        return GLib.SOURCE_REMOVE
