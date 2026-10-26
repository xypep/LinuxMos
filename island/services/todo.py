"""To-do list with reminders. One GLib timeout points at the next due task – no polling."""

import re
import time
import uuid
from datetime import datetime, timedelta

from gi.repository import GLib

from island.storage import DATA_DIR, load_json, save_json

TODO_FILE = DATA_DIR / "todo.json"


def parse_due(text, now=None):
    """'14:30', '1430', '9', 'in 20 min', 'in 2 h' -> epoch seconds, or None."""
    now = now or datetime.now()
    text = (text or "").strip().lower()
    if not text:
        return None
    m = re.fullmatch(r"in\s*(\d+)\s*(m|min|minuten?|h|std|stunden?)", text)
    if m:
        amount = int(m.group(1))
        delta = timedelta(hours=amount) if m.group(2).startswith(("h", "s")) else timedelta(minutes=amount)
        return (now + delta).timestamp()
    m = re.fullmatch(r"(\d{1,2})(?::|\.)?(\d{2})?\s*(uhr)?", text)
    if m:
        hour, minute = int(m.group(1)), int(m.group(2) or 0)
        if hour > 23 or minute > 59:
            return None
        due = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if due <= now:
            due += timedelta(days=1)  # "9:00" in the evening means tomorrow morning
        return due.timestamp()
    raise ValueError(text)


def _today_start():
    return datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp()


class TodoList:
    def __init__(self, on_change, on_due):
        self._on_change = on_change
        self._on_due = on_due
        self._timer = 0
        stored = load_json(TODO_FILE, [])
        today = _today_start()
        # Tasks finished before today are cleaned up automatically
        self.items = [t for t in stored if isinstance(t, dict) and t.get("text")
                      and not (t.get("done") and (t.get("done_at") or 0) < today)]
        self._schedule()

    @property
    def done_today(self):
        today = _today_start()
        return sum(1 for t in self.items if t.get("done") and (t.get("done_at") or 0) >= today)

    def add(self, text, due=None):
        self.items.append({"id": uuid.uuid4().hex[:8], "text": text.strip(), "due": due,
                           "done": False, "done_at": None, "notified": False, "created": time.time()})
        self._changed()

    def toggle(self, item):
        item["done"] = not item.get("done")
        item["done_at"] = time.time() if item["done"] else None
        self._changed()

    def remove(self, item):
        if item in self.items:
            self.items.remove(item)
            self._changed()

    def sorted_items(self):
        return sorted(self.items, key=lambda t: (t.get("done", False), t.get("due") or 1e12, t.get("created", 0)))

    # ---- reminders ---------------------------------------------------------
    def _schedule(self):
        if self._timer:
            GLib.source_remove(self._timer)
            self._timer = 0
        pending = [t["due"] for t in self.items if t.get("due") and not t.get("done") and not t.get("notified")]
        if pending:
            delay = max(0.0, min(pending) - time.time())
            # Capped so suspend/resume can't make us oversleep for hours
            self._timer = GLib.timeout_add_seconds(int(min(delay, 600)) + 1, self._fire)

    def _fire(self):
        self._timer = 0
        now = time.time()
        for task in self.items:
            if task.get("due") and not task.get("done") and not task.get("notified") and task["due"] <= now:
                task["notified"] = True
                self._on_due(task)
        self._changed()
        return GLib.SOURCE_REMOVE

    def _changed(self):
        save_json(TODO_FILE, self.items)
        self._schedule()
        self._on_change()
