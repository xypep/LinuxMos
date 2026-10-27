"""Clipboard history (text and images) driven by the X11 owner-change event."""

import time

from gi.repository import Gdk, GdkPixbuf, GLib, Gtk

from island.storage import DATA_DIR, load_json, save_json

HISTORY_FILE = DATA_DIR / "clipboard.json"
IMAGE_DIR = DATA_DIR / "clipboard-images"
MAX_TEXT = 20000

# Password managers (KeePassXC, Bitwarden, ...) mark secrets with this target
SECRET_TARGETS = {"x-kde-passwordManagerHint"}
TEXT_TARGETS = {"UTF8_STRING", "STRING", "TEXT", "text/plain", "text/plain;charset=utf-8"}


class ClipboardHistory:
    def __init__(self, limit, autodelete_min, on_change):
        self.limit = limit
        self.autodelete_min = max(0, int(autodelete_min or 0))
        self._on_change = on_change
        stored = load_json(HISTORY_FILE, [])
        self.items = [i for i in stored if isinstance(i, dict) and self._valid(i)]
        self._save_id = 0
        self._expire_id = 0
        # Entries that ran out while the island was off go right away
        if self._drop_expired():
            self._queue_save()
        self._schedule_expiry()
        self._clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        self._clipboard.connect("owner-change", self._on_owner_change)

    @staticmethod
    def _valid(item):
        if item.get("kind") == "image":
            return (IMAGE_DIR / item.get("image", "")).is_file()
        return bool(item.get("text"))

    # ---- capture -----------------------------------------------------------
    def _on_owner_change(self, clipboard, _event):
        clipboard.request_targets(self._on_targets)

    def _on_targets(self, clipboard, atoms, *_):
        names = {a.name() for a in (atoms or [])}
        if not names or names & SECRET_TARGETS:
            return
        if names & TEXT_TARGETS:
            clipboard.request_text(self._on_text)
        elif any(n.startswith("image/") for n in names):
            clipboard.request_image(self._on_image)

    def _on_text(self, _clipboard, text, *_):
        if text and text.strip():
            self._add({"kind": "text", "text": text[:MAX_TEXT]}, key=text[:MAX_TEXT])

    def _on_image(self, _clipboard, pixbuf, *_):
        if pixbuf is None:
            return
        ok, data = pixbuf.save_to_bufferv("png", [], [])
        if not ok:
            return
        # GLib's SHA-1 (same file names as hashlib's) keeps OpenSSL's libcrypto out of memory
        digest = GLib.compute_checksum_for_bytes(GLib.ChecksumType.SHA1, GLib.Bytes.new(data))[:16]
        name = f"{digest}.png"
        IMAGE_DIR.mkdir(parents=True, exist_ok=True)
        path = IMAGE_DIR / name
        if not path.exists():
            path.write_bytes(data)
        self._add({"kind": "image", "image": name, "size": [pixbuf.get_width(), pixbuf.get_height()]}, key=name)

    def _add(self, item, key):
        # Same content again -> move it to the top, keep its pin
        pinned = False
        for old in list(self.items):
            if old.get("text", old.get("image")) == key:
                pinned = old.get("pinned", False)
                self.items.remove(old)
        item.update(pinned=pinned, time=time.time())
        self.items.insert(0, item)
        self._trim()
        self._changed()

    def _trim(self):
        unpinned = [i for i in self.items if not i.get("pinned")]
        for old in unpinned[self.limit:]:
            self._forget(old)

    def _forget(self, item):
        self.items.remove(item)
        if item.get("kind") == "image" and not any(i.get("image") == item["image"] for i in self.items):
            (IMAGE_DIR / item["image"]).unlink(missing_ok=True)

    # ---- actions -----------------------------------------------------------
    def copy(self, item):
        """Put an entry back on the clipboard."""
        if item["kind"] == "image":
            try:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file(str(IMAGE_DIR / item["image"]))
            except GLib.Error:
                return False
            self._clipboard.set_image(pixbuf)
        else:
            self._clipboard.set_text(item["text"], -1)
        # Hand the content to the clipboard manager so it survives the island
        self._clipboard.store()
        return True

    def toggle_pin(self, item):
        item["pinned"] = not item.get("pinned")
        if not item["pinned"]:
            # Unpinned entries get a fresh auto-delete period instead of vanishing at once
            item["unpinned"] = time.time()
        self._changed()

    def remove(self, item):
        if item in self.items:
            self._forget(item)
            self._changed()

    def clear(self):
        for item in [i for i in self.items if not i.get("pinned")]:
            self._forget(item)
        self._changed()

    def image_path(self, item):
        return IMAGE_DIR / item["image"]

    # ---- auto-delete -------------------------------------------------------
    def set_autodelete(self, minutes):
        self.autodelete_min = max(0, int(minutes or 0))
        self._changed()

    def prune(self):
        """Re-check on demand: the timer is monotonic and pauses during suspend."""
        if self._drop_expired():
            self._changed()

    def _expires_at(self, item):
        return max(item.get("time", 0), item.get("unpinned", 0)) + self.autodelete_min * 60

    def _drop_expired(self):
        if not self.autodelete_min:
            return False
        now = time.time()
        expired = [i for i in self.items if not i.get("pinned") and self._expires_at(i) <= now]
        for item in expired:
            self._forget(item)
        return bool(expired)

    def _schedule_expiry(self):
        """One-shot timer for the next entry that runs out (no polling)."""
        if self._expire_id:
            GLib.source_remove(self._expire_id)
            self._expire_id = 0
        if not self.autodelete_min:
            return
        due = [self._expires_at(i) for i in self.items if not i.get("pinned")]
        if due:
            delay = max(1, int(min(due) - time.time()) + 1)
            self._expire_id = GLib.timeout_add_seconds(delay, self._on_expire)

    def _on_expire(self):
        self._expire_id = 0
        self._changed()
        return GLib.SOURCE_REMOVE

    # ---- persistence -------------------------------------------------------
    def _changed(self):
        self._drop_expired()
        self._schedule_expiry()
        self._on_change()
        self._queue_save()

    def _queue_save(self):
        if self._save_id:
            GLib.source_remove(self._save_id)
        self._save_id = GLib.timeout_add(800, self._save)

    def _save(self):
        self._save_id = 0
        save_json(HISTORY_FILE, self.items)
        return GLib.SOURCE_REMOVE
