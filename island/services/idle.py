"""Is the user away? Muffin's IdleMonitor tells us via D-Bus signals (no polling).

States: "active" -> "idle" (after IDLE_S) -> "sleep" (after SLEEP_S) -> "back" when
the user returns, which the island turns into a short "hello" from the mascot.

idle_ms() answers "how long since the last input" on demand (the stretch reminder asks once a minute):
Muffin's GetIdletime, else the X screen saver extension through ctypes (libXss, loaded only then).
"""

import ctypes
import logging

from gi.repository import Gio, GLib

log = logging.getLogger("mosisland.idle")

NAME = "org.cinnamon.Muffin.IdleMonitor"
PATH = "/org/cinnamon/Muffin/IdleMonitor/Core"
IDLE_S = 60
SLEEP_S = 5 * 60


class IdleWatcher:
    def __init__(self, on_state):
        self._on_state = on_state
        self.state = "active"
        self._proxy = None
        self._idle_id = self._sleep_id = self._active_id = None
        Gio.DBusProxy.new_for_bus(Gio.BusType.SESSION, Gio.DBusProxyFlags.DO_NOT_AUTO_START, None,
                                  NAME, PATH, NAME, None, self._on_ready)

    @property
    def available(self):
        return self._proxy is not None

    def idle_ms(self, callback):
        """callback(milliseconds since the last input, or None if neither Muffin nor libXss can tell)."""
        proxy = self._proxy

        def fallback():
            callback(xss_idle_ms())

        if proxy is None:
            fallback()
            return

        def done(source, result):
            try:
                callback(int(source.call_finish(result).unpack()[0]))
            except (GLib.Error, TypeError, IndexError, ValueError):
                fallback()

        proxy.call("GetIdletime", None, Gio.DBusCallFlags.NONE, 2000, None, done)

    def _on_ready(self, _src, result):
        try:
            proxy = Gio.DBusProxy.new_for_bus_finish(result)
        except GLib.Error:
            return
        if proxy.get_name_owner() is None:
            return  # not running under Cinnamon/Muffin
        self._proxy = proxy
        proxy.connect("g-signal", self._on_signal)
        self._add_watch("AddIdleWatch", GLib.Variant("(t)", (IDLE_S * 1000,)), "_idle_id")
        self._add_watch("AddIdleWatch", GLib.Variant("(t)", (SLEEP_S * 1000,)), "_sleep_id")

    def _add_watch(self, method, params, attr):
        def done(proxy, result):
            try:
                setattr(self, attr, proxy.call_finish(result).unpack()[0])
            except GLib.Error:
                pass

        self._proxy.call(method, params, Gio.DBusCallFlags.NONE, 2000, None, done)

    def _on_signal(self, _proxy, _sender, signal, params):
        if signal != "WatchFired":
            return
        watch = params.unpack()[0]
        if watch == self._idle_id:
            self._set("idle")
            # One-shot watch: fires the moment the user touches mouse or keyboard
            self._add_watch("AddUserActiveWatch", None, "_active_id")
        elif watch == self._sleep_id:
            self._set("sleep")
        elif watch == self._active_id:
            self._active_id = None
            self._set("back")

    def _set(self, state):
        self.state = state
        self._on_state(state)


# ---- X screen saver extension: the fallback outside Cinnamon (and in Xvfb) -------------------
class _XScreenSaverInfo(ctypes.Structure):
    _fields_ = [("window", ctypes.c_ulong), ("state", ctypes.c_int), ("kind", ctypes.c_int),
                ("til_or_since", ctypes.c_ulong), ("idle", ctypes.c_ulong), ("event_mask", ctypes.c_ulong)]


_xss = {}    # loaded on the first call: libs, a connection of our own and the info record


def xss_idle_ms():
    """Milliseconds since the last input from libXss, or None (library, display or extension missing)."""
    if not _xss:
        _xss["ok"] = False
        try:
            x11, xss = ctypes.CDLL("libX11.so.6"), ctypes.CDLL("libXss.so.1")
            x11.XOpenDisplay.restype = ctypes.c_void_p
            x11.XOpenDisplay.argtypes = [ctypes.c_char_p]
            x11.XDefaultRootWindow.restype = ctypes.c_ulong
            x11.XDefaultRootWindow.argtypes = [ctypes.c_void_p]
            xss.XScreenSaverAllocInfo.restype = ctypes.POINTER(_XScreenSaverInfo)
            xss.XScreenSaverQueryInfo.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.POINTER(_XScreenSaverInfo)]
            display = x11.XOpenDisplay(None)
            if display:
                _xss.update(ok=True, xss=xss, display=display, root=x11.XDefaultRootWindow(display),
                            info=xss.XScreenSaverAllocInfo())
        except (OSError, AttributeError) as error:
            log.warning("no idle time from libXss: %s", error)
        if not _xss["ok"]:
            log.warning("idle time unavailable (neither Muffin's IdleMonitor nor libXss)")
    if not _xss["ok"]:
        return None
    if not _xss["xss"].XScreenSaverQueryInfo(_xss["display"], _xss["root"], _xss["info"]):
        return None
    return int(_xss["info"].contents.idle)
