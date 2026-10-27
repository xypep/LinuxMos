"""Keep awake: no screen saver, no screen off, no automatic suspend – while it is switched on.

How: Cinnamon's session manager (`org.gnome.SessionManager.Inhibit`, flags "suspend" + "idle"). cinnamon-session
hands the idle state to the screen saver and cinnamon-settings-daemon's power plugin, so both stand down; a
manual lock or suspend still works. If that fails, `org.freedesktop.ScreenSaver.Inhibit` (cinnamon-settings-
daemon forwards it to the session manager), then `systemd-inhibit`.

The lock belongs to our D-Bus connection (or, for systemd-inhibit, to a child that ends when its input pipe
closes): if the island quits or is killed, the lock is gone with it. Nothing is remembered across restarts.

No tick: switching off after `minutes` is one timer for the end time. Nothing here runs while it is off.
"""

import logging

from gi.repository import Gio, GLib

log = logging.getLogger("mosisland.keepawake")

APP_ID = "linuxmos-island"
REASON = "Wach halten (MosIsland)"
INHIBIT_SUSPEND, INHIBIT_IDLE = 4, 8
CALL_TIMEOUT_MS = 3000
SD_CHECK_MS = 700          # systemd-inhibit that is gone this soon did not get its lock


class KeepAwake:
    def __init__(self, on_change):
        self._on_change = on_change
        self.active = False
        self.backend = None             # session | screensaver | systemd
        self._cookie = None
        self._proc = None               # systemd-inhibit
        self._starting = False
        self._abort = False             # stop() came while the lock was still being asked for
        self._timer = 0
        self._deadline = None           # monotonic µs, None = until switched off
        self._bus = None
        self.failed = False             # the last start found no way to hold the lock (the island says so once)
        self.announce_off = False       # the lock ended by itself or by toggle: the island says "off" once

    # ---- state ---------------------------------------------------------------------------------------
    def remaining(self):
        """Seconds left, or None if it runs until switched off (or is off)."""
        if not self.active or self._deadline is None:
            return None
        return max(0, int((self._deadline - GLib.get_monotonic_time()) / 1_000_000))

    def toggle(self, minutes):
        if self.active:
            self.stop("switched off")
        else:
            self.start(minutes)

    def start(self, minutes):
        """Take the lock; minutes <= 0 = until switched off. on_change fires once it holds (or failed)."""
        if self.active or self._starting:
            return
        self._starting = True
        self._abort = False
        self.failed = False
        self._pending_minutes = minutes
        try:
            self._bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        except GLib.Error as error:
            log.warning("keepawake: no session bus: %s", error.message)
            self._bus = None
        self._attempt(0)

    def stop(self, why="switched off"):
        if self._starting:
            self._abort = True
        if self._timer:
            GLib.source_remove(self._timer)
            self._timer = 0
        self._deadline = None
        was = self.active
        self._release()
        self.active = False
        self.backend = None
        if was:
            self.announce_off = why != "island quits" and why != "disabled"
            log.info("keepawake: off (%s), lock released", why)
            self._on_change()

    # ---- taking the lock: the first method that works -------------------------------------------------------
    def _attempt(self, index):
        methods = (self._via_session, self._via_screensaver, self._via_systemd)
        if index >= len(methods):
            self._starting = False
            self.failed = True
            log.warning("keepawake: no way to keep the screen awake worked")
            self._on_change()
            return
        methods[index](lambda ok, i=index: self._on_result(ok, i))

    def _on_result(self, ok, index):
        if not ok:
            self._attempt(index + 1)
            return
        self._starting = False
        if self._abort:                 # switched off meanwhile: give the lock straight back
            self._abort = False
            self._release()
            self.backend = None
            return
        self.active = True
        minutes = self._pending_minutes
        if minutes and minutes > 0:
            self._deadline = GLib.get_monotonic_time() + int(minutes * 60 * 1_000_000)
            self._timer = GLib.timeout_add_seconds(int(minutes * 60), self._on_expired)
        log.info("keepawake: on via %s%s", self.backend, f" for {minutes} min" if minutes and minutes > 0 else "")
        self._on_change()

    def _call(self, dest, path, iface, method, args, reply_type, done):
        if self._bus is None:
            done(False, None)
            return

        def finished(bus, result):
            try:
                done(True, bus.call_finish(result))
            except GLib.Error as error:
                log.debug("keepawake: %s.%s failed: %s", iface, method, error.message)
                done(False, None)

        self._bus.call(dest, path, iface, method, args, GLib.VariantType(reply_type) if reply_type else None,
                       Gio.DBusCallFlags.NONE, CALL_TIMEOUT_MS, None, finished)

    def _via_session(self, result):
        def done(ok, reply):
            if ok:
                self._cookie, self.backend = reply.unpack()[0], "session"
            result(ok)

        self._call("org.gnome.SessionManager", "/org/gnome/SessionManager", "org.gnome.SessionManager", "Inhibit",
                   GLib.Variant("(susu)", (APP_ID, 0, REASON, INHIBIT_SUSPEND | INHIBIT_IDLE)), "(u)", done)

    def _via_screensaver(self, result):
        def done(ok, reply):
            if ok:
                self._cookie, self.backend = reply.unpack()[0], "screensaver"
            result(ok)

        self._call("org.freedesktop.ScreenSaver", "/org/freedesktop/ScreenSaver", "org.freedesktop.ScreenSaver",
                   "Inhibit", GLib.Variant("(ss)", (APP_ID, REASON)), "(u)", done)

    def _via_systemd(self, result):
        """systemd-inhibit around a `cat` that reads our pipe: when the island dies the pipe closes, cat ends,
        and so does the lock."""
        if GLib.find_program_in_path("systemd-inhibit") is None:
            result(False)
            return
        try:
            proc = Gio.Subprocess.new(
                ["systemd-inhibit", "--what=idle:sleep", "--who=MosIsland", f"--why={REASON}", "--mode=block", "cat"],
                Gio.SubprocessFlags.STDIN_PIPE | Gio.SubprocessFlags.STDOUT_SILENCE
                | Gio.SubprocessFlags.STDERR_SILENCE)
        except GLib.Error:
            result(False)
            return

        gone = []

        def exited(_proc, _result):
            gone.append(True)
            if self._proc is proc and self.active:       # ended later without us asking
                self._proc = None
                self.stop("the lock process ended")

        proc.wait_async(None, exited)

        def check():
            if gone:                                     # it did not get its lock (no logind, no permission)
                result(False)
            else:
                self._proc, self.backend = proc, "systemd"
                result(True)
            return GLib.SOURCE_REMOVE

        GLib.timeout_add(SD_CHECK_MS, check)

    # ---- giving it back ------------------------------------------------------------------------------------
    def _release(self):
        cookie, backend, proc = self._cookie, self.backend, self._proc
        self._cookie = self._proc = None
        if backend == "systemd" and proc is not None:
            try:
                proc.get_stdin_pipe().close(None)
            except GLib.Error:
                pass
            proc.force_exit()
        elif cookie is not None and self._bus is not None:
            if backend == "session":
                args = ("org.gnome.SessionManager", "/org/gnome/SessionManager", "org.gnome.SessionManager",
                        "Uninhibit")
            else:
                args = ("org.freedesktop.ScreenSaver", "/org/freedesktop/ScreenSaver", "org.freedesktop.ScreenSaver",
                        "UnInhibit")
            self._call(*args, GLib.Variant("(u)", (cookie,)), None, lambda *_: None)

    def _on_expired(self):
        self._timer = 0
        self.stop("time is up")
        return GLib.SOURCE_REMOVE

    def shutdown(self, why="island quits"):
        """The island quits (or the feature is switched off): give the lock back at once."""
        if self.active or self._cookie is not None or self._proc is not None:
            self.stop(why)
            if self._bus is not None:
                try:
                    self._bus.flush_sync(None)
                except GLib.Error:
                    pass
