"""The file shelf: files dropped on the island wait here until dragged out again."""

from gi.repository import Gio

from island.storage import DATA_DIR, load_json, save_json

SHELF_FILE = DATA_DIR / "shelf.json"


def _exists(uri):
    return Gio.File.new_for_uri(uri).query_exists(None)


class Shelf:
    def __init__(self, on_change):
        self._on_change = on_change
        stored = load_json(SHELF_FILE, [])
        self.uris = [u for u in stored if isinstance(u, str) and _exists(u)]

    def add(self, uris):
        added = [u for u in uris if u and u not in self.uris]
        if added:
            self.uris.extend(added)
            self._changed()
        return len(added)

    def remove(self, uri):
        if uri in self.uris:
            self.uris.remove(uri)
            self._changed()

    def clear(self):
        self.uris.clear()
        self._changed()

    def _changed(self):
        save_json(SHELF_FILE, self.uris)
        self._on_change()
