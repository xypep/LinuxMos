"""Apps, files and web search for the command bar.

Apps: GLib's index of the desktop files (name, generic name, keywords, in the
session's language) plus a substring match on the names, ordered by how often
they were started from here. Files: the recently used list plus one scan of
the home folder (no hidden folders, 5 levels deep, at most 20 000 entries) in
a thread on the first search. The list is kept compact (one string of names,
~1 MB) and dropped again a few minutes after the last search, so it costs
neither CPU nor memory while nobody searches.
"""

import os
import re
import threading
import time
import urllib.parse
from array import array
from bisect import bisect_right
from collections import deque
from itertools import accumulate
from pathlib import Path

from gi.repository import Gio, GLib, Gtk

from island.storage import DATA_DIR, load_json, save_json

USAGE_PATH = DATA_DIR / "command.json"

SCAN_DEPTH = 5
SCAN_MAX = 20000
INDEX_MAX_AGE = 10 * 60     # rescan on the next search after this long
INDEX_DROP_S = 3 * 60       # forget the list this long after the last search
SKIP_DIRS = {"node_modules", "__pycache__", "site-packages", "venv", "snap", "Trash", "lost+found"}
MAX_HITS = 1000             # candidates ranked per search

ENGINES = {
    "duckduckgo": ("DuckDuckGo", "https://duckduckgo.com/?q=%s"),
    "google": ("Google", "https://www.google.com/search?q=%s"),
    "startpage": ("Startpage", "https://www.startpage.com/do/search?q=%s"),
    "ecosia": ("Ecosia", "https://www.ecosia.org/search?q=%s"),
    "bing": ("Bing", "https://www.bing.com/search?q=%s"),
    "brave": ("Brave Search", "https://search.brave.com/search?q=%s"),
}
# Typed addresses: "github.com", "www.example.org/path", "localhost:8080", "https://…"
_URL = re.compile(r"^(?:https?://\S+|(?:www\.)?(?:[a-z0-9-]+\.)+(?P<tld>[a-z]{2,})(?::\d+)?(?:/\S*)?"
                  r"|localhost(?::\d+)?(?:/\S*)?)$", re.IGNORECASE)
# Endings that are rather file names than websites ("notes.txt" is no address)
_NOT_TLD = {"txt", "md", "py", "sh", "js", "json", "pdf", "png", "jpg", "jpeg", "gif", "svg", "zip", "tar", "gz",
            "deb", "doc", "docx", "odt", "ods", "xls", "xlsx", "csv", "html", "htm", "css", "conf", "log", "mp3",
            "mp4", "mkv", "webm", "iso", "exe", "desktop", "ini", "xml", "yml", "yaml", "toml", "cfg", "bak"}


def engine(config):
    """(name, URL template with %s) of the web search engine."""
    choice = str(config.get("command_bar_engine") or "duckduckgo")
    if choice in ENGINES:
        return ENGINES[choice]
    if "%s" in choice and choice.startswith(("https://", "http://")):
        return urllib.parse.urlsplit(choice).hostname or choice, choice
    return ENGINES["duckduckgo"]


def search_url(config, query):
    name, template = engine(config)
    return name, template.replace("%s", urllib.parse.quote_plus(query))


def as_url(text):
    """The address if the text looks like one, else None."""
    text = text.strip()
    m = _URL.match(text)
    if not m or (m.group("tld") and m.group("tld").lower() in _NOT_TLD):
        return None
    return text if text.lower().startswith(("http://", "https://")) else f"https://{text}"


def short_path(path):
    """/home/me/Documents -> ~/Documents."""
    home = str(Path.home())
    return "~" + path[len(home):] if path == home or path.startswith(home + "/") else path


class FileIndex:
    """File names under a folder in a compact form: one string with all names (one per line) and
    offsets into it, instead of 20 000 Python objects. Scanned breadth-first, so the shallow
    entries make it into the cap.
    """

    def __init__(self, root):
        dirs, names, lowers, parents, kinds = [root], [], [], array("I"), bytearray()
        queue = deque([(0, 0)])  # (index in dirs, depth)
        while queue and len(names) < SCAN_MAX:
            parent, depth = queue.popleft()
            try:
                with os.scandir(dirs[parent]) as entries:
                    for entry in entries:
                        name = entry.name
                        if name.startswith(".") or name.endswith("~") or "\n" in name:
                            continue
                        try:
                            is_dir = entry.is_dir(follow_symlinks=False)
                        except OSError:
                            continue
                        low = name.lower()
                        names.append(name)
                        lowers.append(low if len(low) == len(name) else name)  # offsets must match
                        parents.append(parent)
                        kinds.append(is_dir)
                        if is_dir and depth + 1 < SCAN_DEPTH and name not in SKIP_DIRS:
                            dirs.append(entry.path)
                            queue.append((len(dirs) - 1, depth + 1))
            except OSError:
                continue
        self._dirs, self._parents, self._kinds = dirs, parents, kinds
        self._names = "\n".join(names) + "\n"
        self._lower = "\n".join(lowers) + "\n"
        self._starts = array("I", accumulate((len(n) + 1 for n in names), initial=0))
        self.size = len(names)

    def _path(self, i):
        return f"{self._dirs[self._parents[i]]}/{self._names[self._starts[i]:self._starts[i + 1] - 1]}"

    def search(self, terms, skip=(), limit=5):
        """[(path, is_dir)] whose name contains every term: names starting with the query first,
        then shallow paths, then short names."""
        lower, starts, phrase = self._lower, self._starts, " ".join(terms)
        hits, pos = [], 0
        while len(hits) < MAX_HITS:
            pos = lower.find(terms[0], pos)
            if pos < 0:
                break
            i = bisect_right(starts, pos) - 1
            end = starts[i + 1] - 1
            name = lower[starts[i]:end]
            if all(t in name for t in terms[1:]):
                path = self._path(i)
                if path not in skip:
                    hits.append((_rank(name, phrase), path.count("/"), len(name), path, bool(self._kinds[i])))
            pos = end + 1  # next entry
        hits.sort()
        return [(path, is_dir) for *_key, path, is_dir in hits[:limit]]


def _rank(name, query):
    """0: starts with the query, 1: a word starts with it, 2: somewhere inside."""
    if name.startswith(query):
        return 0
    i = name.find(query)
    return 1 if i > 0 and not name[i - 1].isalnum() else 2


class Finder:
    def __init__(self, on_files_ready):
        self._on_files_ready = on_files_ready
        self._apps = None           # all visible apps, reloaded when the installed apps change
        self._usage = None
        self._index = None          # FileIndex of the home folder
        self._index_time = 0
        self._scanning = False
        self._drop_id = 0
        self._monitor = Gio.AppInfoMonitor.get()
        self._monitor.connect("changed", lambda *_: setattr(self, "_apps", None))

    # ---- apps ----------------------------------------------------------------
    def _all_apps(self):
        if self._apps is None:
            self._apps = [a for a in Gio.AppInfo.get_all() if a.should_show() and a.get_id()]
        return self._apps

    def _counts(self):
        if self._usage is None:
            data = load_json(USAGE_PATH, {})
            self._usage = data.get("apps", {}) if isinstance(data, dict) else {}
        return self._usage

    def apps(self, query, limit=5):
        """Matching apps: GLib's ranking groups first, each by use; then names containing the query."""
        counts, by_id = self._counts(), {a.get_id(): a for a in self._all_apps()}
        query = query.strip().lower()
        if not query:
            # Empty bar: the most used apps
            used = sorted((i for i in counts if i in by_id), key=lambda i: -counts[i])
            return [by_id[i] for i in used[:limit]]
        result, seen = [], set()
        for group in Gio.DesktopAppInfo.search(query):
            hits = sorted((by_id[i] for i in group if i in by_id and i not in seen),
                          key=lambda a: (-counts.get(a.get_id(), 0), a.get_name().lower()))
            for app in hits:
                seen.add(app.get_id())
                result.append(app)
        # "fox" -> Firefox: GLib only matches the start of words
        rest = [a for a in self._all_apps() if a.get_id() not in seen and query in a.get_name().lower()]
        rest.sort(key=lambda a: (-counts.get(a.get_id(), 0), a.get_name().lower()))
        return (result + rest)[:limit]

    def launched(self, app):
        counts = self._counts()
        counts[app.get_id()] = counts.get(app.get_id(), 0) + 1
        save_json(USAGE_PATH, {"apps": counts})

    # ---- files ---------------------------------------------------------------
    def files(self, query, limit=5):
        """[(path, is_dir)]: recently used first, then the home folder (once its scan is in)."""
        terms = query.strip().lower().split()
        if not terms or (len(terms) == 1 and len(terms[0]) < 2):
            return []
        self._keep_index()
        if not self._scanning and (self._index is None or time.monotonic() - self._index_time > INDEX_MAX_AGE):
            self._scanning = True
            threading.Thread(target=self._scan_worker, daemon=True).start()
        found, seen = [], set()
        for path in self._recent(terms, 2):
            seen.add(path)
            found.append((path, os.path.isdir(path)))
        if self._index:
            found += self._index.search(terms, seen, limit - len(found))
        return found[:limit]

    @staticmethod
    def _recent(terms, limit):
        hits = []
        for item in Gtk.RecentManager.get_default().get_items():
            if not item.is_local():
                continue
            name = (item.get_display_name() or "").lower()
            if all(t in name for t in terms):
                hits.append(item)
        hits.sort(key=lambda i: -i.get_modified())
        paths = []
        for item in hits:
            try:
                path = GLib.filename_from_uri(item.get_uri())[0]
            except GLib.Error:
                continue
            if os.path.exists(path):
                paths.append(path)
                if len(paths) == limit:
                    break
        return paths

    def _scan_worker(self):
        GLib.idle_add(self._scan_done, FileIndex(str(Path.home())))

    def _scan_done(self, index):
        first = self._index is None
        self._index, self._index_time, self._scanning = index, time.monotonic(), False
        self._keep_index()
        if first:
            self._on_files_ready()
        return GLib.SOURCE_REMOVE

    def _keep_index(self):
        """(Re)start the countdown that drops the file list after the last search."""
        if self._drop_id:
            GLib.source_remove(self._drop_id)
        self._drop_id = GLib.timeout_add_seconds(INDEX_DROP_S, self._drop_index)

    def _drop_index(self):
        self._drop_id = 0
        self._index = None
        return GLib.SOURCE_REMOVE

    @property
    def scanning(self):
        return self._scanning and self._index is None
