"""Clip transfer on the island: sending on request, watching the inbox, cards for the result.

Nothing here runs by itself:
  send     a button, the hotkey or the CLI starts ONE ssh process (Gio.Subprocess, data on stdin, no connection
           stays open). There is no clipboard watcher and no owner-change handler for sending.
  receive  one Gio.FileMonitor (inotify) on the inbox folder, only while clip_receive_enabled is on. A new entry
           goes into the clipboard history (marked "received") or the shelf, plus a card. NOTHING is put on the
           clipboard until the user clicks the card or the entry.
With both switches off the island does not even import this module (see IslandWindow._apply_clip).
The texts are German only, like the stretch reminder's: they do not go through island/i18n.py.
"""

import logging
import os
import time

from gi.repository import Gdk, GdkPixbuf, Gio, GLib, Gtk

from island.services import clipcore as core
from island.services.clipboard import SECRET_TARGETS, TEXT_TARGETS
from island.services.fullscreen import FullscreenWatcher
from island.storage import CACHE_DIR, DATA_DIR, load_json, save_json

log = logging.getLogger("mosisland.clip")

STATE_FILE = DATA_DIR / "clip-state.json"      # ids of inbox entries that were already delivered
SCAN_DELAY_MS = 250                            # one look after the last event (an entry is two renames)
MAX_DELIVER = 50                               # a long backlog: only the newest ones become cards and entries
GUIDE_URL = "https://github.com/xypep/LinuxMos/blob/main/docs/CLIP.md"
RESULT_MS, ERROR_MS = 6000, 12000
KIND_NAMES = {"text": "Text", "image": "Bild", "file": "Datei"}


def _short(text, limit):
    text = " ".join(text.split())
    return text if len(text) <= limit else text[:limit - 1] + "…"


class ClipTransfer:
    def __init__(self, island):
        self.island = island
        self.config = island.config
        self.paths = core.default_paths()
        self.status = None                  # (ok, text, time) of the last transfer, for the Transfer section
        self.on_status = lambda: None
        self._monitor = None
        self._logged = None
        self._wait_logged = None
        self._scan_id = 0
        self._sending = None                # (Gio.Subprocess, peer) while a send runs
        self._waiting_entries = []          # received, their card waits (fullscreen, a capture, another card …)
        self._waiting_cards = []            # result cards that wait
        self._watcher = None                # FullscreenWatcher: attached only while something waits
        self._busy_activity = None          # the "sending …" activity, so only that one is cleared again

    # ---- switches ------------------------------------------------------------
    @property
    def send_enabled(self):
        return self.config.flag("clip_send_enabled")

    @property
    def receive_enabled(self):
        return self.config.flag("clip_receive_enabled")

    @property
    def waiting(self):
        return bool(self._waiting_entries or self._waiting_cards)

    def apply(self):
        """Make the config take effect: the inbox monitor exists only while receiving is on."""
        state = (self.send_enabled, self.receive_enabled)
        if state != self._logged:
            self._logged = state
            log.info("clip: send %s, receive %s", "on" if state[0] else "off", "on" if state[1] else "off")
        if self.receive_enabled:
            self._start_monitor()
        else:
            self._stop_monitor()

    def stop(self):
        self._stop_monitor()
        self._stop_watcher()
        if self._scan_id:
            GLib.source_remove(self._scan_id)
            self._scan_id = 0

    # ---- the inbox monitor ----------------------------------------------------
    def _start_monitor(self):
        if self._monitor is not None:
            return
        try:
            core.make_private_dir(self.paths.inbox)
            self._monitor = Gio.File.new_for_path(str(self.paths.inbox)).monitor_directory(
                Gio.FileMonitorFlags.NONE, None)
        except (GLib.Error, OSError) as error:
            log.warning("clip: the inbox is not watched: %s", error)
            return
        self._monitor.connect("changed", self._on_event)
        log.info("clip: watching %s", self.paths.inbox)
        self._scan_later(0)      # entries that arrived while the island was off

    def _stop_monitor(self):
        if self._monitor is not None:
            self._monitor.cancel()
            self._monitor = None
            log.info("clip: inbox no longer watched")

    def _on_event(self, _monitor, gfile, _other, event):
        if event not in (Gio.FileMonitorEvent.CREATED, Gio.FileMonitorEvent.MOVED_IN,
                         Gio.FileMonitorEvent.CHANGES_DONE_HINT):
            return
        name = gfile.get_basename() or ""
        if name.endswith(".json") and not name.startswith("."):    # the entry file is renamed in last
            self._scan_later(SCAN_DELAY_MS)

    def _scan_later(self, delay_ms):
        if self._scan_id:
            GLib.source_remove(self._scan_id)
        self._scan_id = GLib.timeout_add(delay_ms, self._scan)

    def _scan(self):
        self._scan_id = 0
        try:
            self._deliver_new()
        except Exception:      # a broken file in the inbox must never take the island down
            log.exception("clip: reading the inbox failed")
        return GLib.SOURCE_REMOVE

    def _deliver_new(self):
        limits = core.Limits.from_config(self.config)
        core.cleanup(self.paths, limits.keep_days)
        entries = core.list_entries(self.paths)
        done = {i for i in load_json(STATE_FILE, {}).get("delivered", []) if isinstance(i, str)}
        fresh = [e for e in entries if e["id"] not in done]
        for entry in fresh[-MAX_DELIVER:]:
            if self._deliver(entry):
                self._waiting_entries.append(entry)
        if fresh:
            save_json(STATE_FILE, {"delivered": [e["id"] for e in entries]})
            log.info("clip: %d new in the inbox", len(fresh))
            self.flush()
        elif done - {e["id"] for e in entries}:
            save_json(STATE_FILE, {"delivered": [e["id"] for e in entries]})

    def _deliver(self, entry):
        """Put an entry where the user finds it (history or shelf). False if it cannot be used."""
        who = core.peer_label(self.config, entry["sender"])
        island = self.island
        try:
            if entry["type"] == "text":
                text = core.read_text(entry, self.paths)
                if not text:
                    return False
                island.clipboard.add_received_text(text, who, entry["id"])
            elif entry["type"] == "image":
                pixbuf = GdkPixbuf.Pixbuf.new_from_file(str(core.payload_path(entry, self.paths)))
                island.clipboard.add_received_image(pixbuf, who, entry["id"])
            else:
                island.shelf.add([Gio.File.new_for_path(entry["path"]).get_uri()])
        except (GLib.Error, OSError) as error:
            log.warning("clip: entry %s cannot be used: %s", entry["id"], error)
            return False
        return True

    # ---- cards (they wait while the island is busy) --------------------------------
    def flush(self):
        """Show what waits, unless the island is busy: fullscreen, a capture, the opened island, another card."""
        if not self.waiting:
            self._stop_watcher()
            return
        reason = self.island.clip_card_blocker()
        if reason:
            if (reason, self.waiting) != self._wait_logged:
                self._wait_logged = (reason, self.waiting)
                log.info("clip: card waits (%s)", reason)
            if reason == "fullscreen":
                self._start_watcher()
            return
        self._wait_logged = None
        self._stop_watcher()
        cards, self._waiting_cards = self._waiting_cards, []
        entries, self._waiting_entries = self._waiting_entries, []
        if cards:
            self.island.show_card(clip=True, **cards[-1])
        if entries:
            self.island.show_card(clip=True, **self._received_card(entries))

    def _start_watcher(self):
        if self._watcher is None:
            self._watcher = FullscreenWatcher(self.island.wnck, self._on_fullscreen)
            self._watcher.start()

    def _stop_watcher(self):
        if self._watcher is not None:
            self._watcher.stop()
            self._watcher = None

    def _on_fullscreen(self, fullscreen):
        if not fullscreen:
            GLib.idle_add(self._flush_idle)

    def _flush_idle(self):
        self.flush()
        return GLib.SOURCE_REMOVE

    def _post(self, **card):
        self._waiting_cards.append(card)
        self.flush()

    def _received_card(self, entries):
        who = core.peer_label(self.config, entries[-1]["sender"])
        if len(entries) > 1:
            kinds = ", ".join(f"{sum(e['type'] == k for e in entries)} {name}" for k, name in KIND_NAMES.items()
                              if any(e["type"] == k for e in entries))
            return dict(icon_name="emblem-downloads-symbolic", title=f"{len(entries)} Einträge empfangen",
                        body=kinds, meta=_short(who, 22), title_chars=28,
                        on_click=lambda: self.island.expand(tab="clipboard"))
        entry = entries[0]
        icon_name = "emblem-downloads-symbolic"
        image = None
        if entry["type"] == "text":
            text = core.read_text(entry, self.paths)
            meta, body = f"Text ({entry.get('chars', len(text))} Zeichen)", _short(text, 160)
            click = lambda: self.copy_entry(entry)      # noqa: E731
        elif entry["type"] == "image":
            meta, body = "Bild", f"{core.human(entry['size'])} · Klick kopiert es"
            click = lambda: self.copy_entry(entry)      # noqa: E731
            try:
                image = GdkPixbuf.Pixbuf.new_from_file_at_scale(str(core.payload_path(entry, self.paths)), 80, 80, True)
            except GLib.Error:
                pass
        else:
            meta, body = "Datei", f"{entry['name']} ({core.human(entry['size'])}) · liegt in der Ablage"
            click = lambda: self.island.expand(tab="shelf")     # noqa: E731
        return dict(icon_name=icon_name, title=f"Vom {_short(who, 14)} empfangen", body=body, meta=meta,
                    image=image, on_click=click, title_chars=28)

    # ---- copying a received entry: only ever on a click ---------------------------------
    def copy_entry(self, entry):
        """Put a received text or image on the clipboard (the click is the only way it gets there)."""
        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        try:
            if entry["type"] == "text":
                clipboard.set_text(core.read_text(entry, self.paths), -1)
            else:
                clipboard.set_image(GdkPixbuf.Pixbuf.new_from_file(str(core.payload_path(entry, self.paths))))
        except (GLib.Error, OSError):
            self.island.show_activity("dialog-warning-symbolic", "Eintrag lässt sich nicht mehr kopieren", seconds=4)
            return
        clipboard.store()
        self.island.show_activity("edit-copy-symbolic", "Kopiert")

    # ---- sending -----------------------------------------------------------------------
    def peers(self):
        return core.peers(self.config)

    def default_peer(self):
        return core.default_peer(self.config)

    def send_text(self, text, peer=None, note=""):
        data = text.encode("utf-8")
        if not data.strip():
            return self._fail(peer or self.default_peer(), "Nichts zu senden: der Text ist leer")
        self._start(peer, "text", data=data, note=note or f"Text ({len(text)} Zeichen)")

    def send_path(self, path, kind="file", peer=None, delete_after=False, name=None):
        self._start(peer, kind, path=str(path), delete_after=delete_after, name=name or os.path.basename(path))

    def _start(self, peer, kind, data=None, path=None, delete_after=False, name=None, note=""):
        cleanup = (lambda: os.unlink(path)) if delete_after and path else (lambda: None)   # noqa: E731
        if not self.send_enabled:
            cleanup()
            return self._notice("Clip-Senden ist aus", "Einschalten: Tray → Clip-Transfer → Clip-Senden")
        try:
            peer = peer or self._choose_peer()
            if peer is None:
                return cleanup()
            if self._sending is not None:
                cleanup()
                return self.island.show_activity("document-send-symbolic", "Es läuft schon eine Übertragung",
                                                 seconds=3)
            if (problem := core.key_problem(peer)):
                cleanup()
                return self._fail(peer, problem)
            limits = core.Limits.from_config(self.config)
            if data is not None and len(data) > limits.text:
                return self._fail(peer, f"Zu groß: {core.human(len(data))} (Limit {core.human(limits.text)})")
            if path is not None:
                size, problem = core.check_sendable(path, limits, kind)
                if problem:
                    cleanup()
                    return self._fail(peer, problem)
                note = note or (f"Bild ({core.human(size)})" if kind == "image" else f"{name} ({core.human(size)})")
            argv = core.ssh_argv(peer, core.remote_command(kind, name if kind == "file" else None))
            flags = Gio.SubprocessFlags.STDERR_PIPE | Gio.SubprocessFlags.STDOUT_SILENCE
            if data is not None:
                flags |= Gio.SubprocessFlags.STDIN_PIPE
            launcher = Gio.SubprocessLauncher.new(flags)
            if path is not None:
                launcher.set_stdin_file_path(path)       # streamed by the child, never loaded here
            proc = launcher.spawnv(argv)
        except (GLib.Error, OSError) as error:
            cleanup()
            return self._fail(peer, f"ssh lässt sich nicht starten: {error}")
        self._sending = (proc, peer)
        self.island.show_activity("document-send-symbolic", f"Sende an {_short(peer['name'], 20)} …", sticky=True)
        self._busy_activity = self.island._activity
        self._set_status(None, f"Sende an {peer['name']} …")
        log.info("clip: sending %s to %s", kind, peer["name"])

        def done(process, result):
            self._sending = None
            cleanup()
            try:
                _ok, _out, err = process.communicate_finish(result)
                stderr = bytes(err.get_data()).decode("utf-8", "replace") if err is not None else ""
            except GLib.Error as error:
                stderr = str(error)
            code = process.get_exit_status() if process.get_if_exited() else -1
            if self.island._activity is self._busy_activity:
                self.island._clear_activity()
            if code == 0:
                self._ok(peer, note)
            else:
                short, long = core.explain_failure(code, stderr, peer)
                log.info("clip: sending to %s failed: %s", peer["name"], short)
                self._fail(peer, long, short)

        proc.communicate_async(GLib.Bytes.new(data) if data is not None else None, None, done)

    def _choose_peer(self):
        peer = self.default_peer()
        if peer is None:
            if self.peers():
                self._notice("Welcher PC?", "Mehrere Peers eingerichtet: clip_default_peer setzen oder den Knopf am Eintrag benutzen")
            else:
                self._notice("Kein Peer eingerichtet", "Im Terminal: linuxmos-clip setup", setup=True)
        return peer

    def _ok(self, peer, note):
        self._set_status(True, f"Gesendet an {peer['name']}")
        self._post(icon_name="emblem-ok-symbolic", title=f"Gesendet an {_short(peer['name'], 14)}", body=note,
                   ms=RESULT_MS, title_chars=28)

    def _fail(self, peer, reason, short=None):
        name = peer["name"] if peer else "PC"
        self._set_status(False, f"{name}: {short or _short(reason, 40)}")
        self._post(icon_name="dialog-warning-symbolic", title=f"Nicht gesendet an {_short(name, 10)}", body=reason,
                   ms=ERROR_MS, title_chars=28)

    def _notice(self, title, body, setup=False):
        actions = [("Befehl kopieren", lambda: self._copy_command("linuxmos-clip setup"), False),
                   ("Anleitung", self.open_guide, True)] if setup else []
        self._post(icon_name="dialog-information-symbolic", title=title, body=body, ms=ERROR_MS,
                   actions=actions, title_chars=28)

    def _set_status(self, ok, text):
        self.status = (ok, text, time.time())
        self.on_status()

    # ---- helpers for the pages and the tray ------------------------------------------------------
    def setup_hint(self):
        """The card behind the 'Einrichten' link: the command to run, and the guide."""
        self._notice("Clip-Transfer einrichten", "Im Terminal: linuxmos-clip setup  (Schritt für Schritt: docs/CLIP.md)",
                     setup=True)

    @staticmethod
    def _copy_command(text):
        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        clipboard.set_text(text, -1)
        clipboard.store()

    @staticmethod
    def open_guide():
        try:
            Gio.AppInfo.launch_default_for_uri(GUIDE_URL, None)
        except GLib.Error:
            pass

    # ---- the hotkey: send what is on the clipboard now -------------------------------------------
    def send_clipboard(self):
        """Ctrl+Alt+Shift+T: the clipboard as it is right now goes to the default peer. Private copies never."""
        if not self.send_enabled:
            return self._notice("Clip-Senden ist aus", "Einschalten: Tray → Clip-Transfer → Clip-Senden")
        if self._choose_peer() is None:
            return
        Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD).request_targets(self._on_targets)

    def _on_targets(self, clipboard, atoms, *_):
        names = {a.name() for a in (atoms or [])}
        if not names:
            return self._notice("Zwischenablage ist leer", "Es gibt nichts zu senden")
        if names & SECRET_TARGETS:
            return self._post(icon_name="dialog-password-symbolic", title="Nicht gesendet", ms=RESULT_MS,
                              body="Als privat markiert (Passwort-Manager): so etwas wird nie gesendet",
                              title_chars=28)
        if "text/uri-list" in names or "x-special/gnome-copied-files" in names:
            clipboard.request_uris(self._on_uris)
        elif names & TEXT_TARGETS:
            clipboard.request_text(lambda _c, text, *_: self.send_text(text) if text else self._notice(
                "Zwischenablage ist leer", "Es gibt nichts zu senden"))
        elif any(n.startswith("image/") for n in names):
            clipboard.request_image(self._on_image)
        else:
            self._notice("Nicht gesendet", "Dieser Inhalt der Zwischenablage lässt sich nicht senden")

    def _on_uris(self, _clipboard, uris, *_):
        paths = [Gio.File.new_for_uri(u).get_path() for u in uris or []]
        paths = [p for p in paths if p]
        if len(paths) != 1:
            return self._notice("Nicht gesendet", "Es lässt sich immer nur eine Datei senden (mehrere: in der Ablage einzeln)")
        self.send_path(paths[0])

    def _on_image(self, _clipboard, pixbuf, *_):
        if pixbuf is None:
            return self._notice("Zwischenablage ist leer", "Es gibt nichts zu senden")
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        path = CACHE_DIR / f"clip-send-{os.urandom(4).hex()}.png"
        try:
            pixbuf.savev(str(path), "png", [], [])
            os.chmod(path, 0o600)
        except (GLib.Error, OSError):
            path.unlink(missing_ok=True)
            return self._notice("Nicht gesendet", "Das Bild lässt sich nicht zwischenspeichern")
        self.send_path(path, kind="image", delete_after=True)
