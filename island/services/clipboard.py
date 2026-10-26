"""Clipboard history (text and images) driven by the X11 owner-change event."""

import hashlib
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
    def __init__(self, limit, on_change):
        self.limit = limit
        self._on_change = on_change
        stored = load_json(HISTORY_FILE, [])
        self.items = [i for i in stored if isinstance(i, dict) and self._valid(i)]
        self._save_id = 0
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
        digest = hashlib.sha1(data).hexdigest()[:16]
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

    # ---- persistence -------------------------------------------------------
    def _changed(self):
        self._on_change()
        if self._save_id:
            GLib.source_remove(self._save_id)
        self._save_id = GLib.timeout_add(800, self._save)

    def _save(self):
        self._save_id = 0
        save_json(HISTORY_FILE, self.items)
        return GLib.SOURCE_REMOVE
