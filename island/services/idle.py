"""Is the user away? Muffin's IdleMonitor tells us via D-Bus signals (no polling).

States: "active" -> "idle" (after IDLE_S) -> "sleep" (after SLEEP_S) -> "back" when
the user returns, which the island turns into a short "hello" from the mascot.
"""

from gi.repository import Gio, GLib

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
