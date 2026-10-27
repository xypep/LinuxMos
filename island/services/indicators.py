"""Short system events for the island: volume, brightness, Caps Lock, keyboard
layout, network and Bluetooth audio devices.

Every source is push based, nothing is polled:
  volume      `pactl subscribe` (a blocked process, 0 % CPU while nothing happens;
              the microphone indicator reads the same stream)
  brightness  Cinnamon settings daemon: Power.Screen "Changed" signal
  Caps Lock   GDK keymap "state-changed" (XKB events)
  layout      gsettings org.cinnamon.desktop.input-sources "current"
  network     NetworkManager "StateChanged"
  headphones  BlueZ PropertiesChanged on org.bluez.Device1 ("Connected")
"""

import gi
from gi.repository import Gdk, Gio, GLib

from island.i18n import _
from island.services import system

try:
    gi.require_version("CinnamonDesktop", "3.0")
    from gi.repository import CinnamonDesktop
except (ValueError, ImportError):
    CinnamonDesktop = None

NM = ("org.freedesktop.NetworkManager", "/org/freedesktop/NetworkManager", "org.freedesktop.NetworkManager")
NM_DISCONNECTED, NM_CONNECTED_SITE = 20, 60
SCREEN = ("org.cinnamon.SettingsDaemon.Power", "/org/cinnamon/SettingsDaemon/Power",
          "org.cinnamon.SettingsDaemon.Power.Screen")


class Indicators:
    def __init__(self, emit):
        """emit(kind, **data) is called for every event worth a short peek."""
        self._emit = emit
        self._volume = None       # (percent, muted)
        self._brightness = None
        self._caps = None
        self._net_connected = None
        self._volume_debounce = 0
        self._proxies = []        # keep D-Bus proxies alive
        self.pactl_listeners = []  # fn(line) for every `pactl subscribe` line (None: sound server gone)

        self._watch_volume()
        self._watch_brightness()
        self._watch_keyboard()
        self._watch_network()
        self._watch_bluetooth()

    # ---- volume ----------------------------------------------------------------
    def _watch_volume(self):
        if not system.has("pactl"):
            return GLib.SOURCE_REMOVE
        try:
            proc = Gio.Subprocess.new(["pactl", "subscribe"],
                                      Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_SILENCE)
        except GLib.Error:
            return GLib.SOURCE_REMOVE
        self._volume_proc = proc
        stream = Gio.DataInputStream.new(proc.get_stdout_pipe())
        self._query_volume(emit=False)  # baseline
        stream.read_line_async(GLib.PRIORITY_DEFAULT, None, self._on_pactl_line)
        return GLib.SOURCE_REMOVE

    def _on_pactl_line(self, stream, result):
        try:
            line, _length = stream.read_line_finish_utf8(result)
        except GLib.Error:
            line = None
        for listener in self.pactl_listeners:
            listener(line)
        if line is None:
            # Sound server restarted: subscribe again in a moment
            GLib.timeout_add_seconds(5, self._watch_volume)
            return
        if "'change' on sink #" in line or "'change' on server" in line:
            if self._volume_debounce:
                GLib.source_remove(self._volume_debounce)
            self._volume_debounce = GLib.timeout_add(60, self._debounced_volume)
        stream.read_line_async(GLib.PRIORITY_DEFAULT, None, self._on_pactl_line)

    def _debounced_volume(self):
        self._volume_debounce = 0
        self._query_volume(emit=True)
        return GLib.SOURCE_REMOVE

    def _query_volume(self, emit):
        def got_volume(percent):
            if percent is None:
                return
            system.run(["pactl", "get-sink-mute", "@DEFAULT_SINK@"],
                       lambda ok, out: got_mute(percent, ok and "yes" in out))

        def got_mute(percent, muted):
            state = (percent, muted)
            if emit and self._volume is not None and state != self._volume:
                self._emit("volume", percent=percent, muted=muted)
            self._volume = state

        system.volume_get(got_volume)

    # ---- brightness ----------------------------------------------------------
    def _watch_brightness(self):
        Gio.DBusProxy.new_for_bus(Gio.BusType.SESSION, Gio.DBusProxyFlags.DO_NOT_AUTO_START, None,
                                  *SCREEN, None, self._on_screen_proxy)

    def _on_screen_proxy(self, _src, result):
        try:
            proxy = Gio.DBusProxy.new_for_bus_finish(result)
        except GLib.Error:
            return
        self._proxies.append(proxy)
        proxy.connect("g-signal", self._on_screen_signal)
        system.brightness_get(lambda v: setattr(self, "_brightness", v))

    def _on_screen_signal(self, _proxy, _sender, signal, _params):
        if signal != "Changed":
            return

        def got(value):
            if value is not None and value != self._brightness and self._brightness is not None:
                self._emit("brightness", percent=value)
            self._brightness = value

        system.brightness_get(got)

    # ---- keyboard: Caps Lock + layout -------------------------------------------
    def _watch_keyboard(self):
        display = Gdk.Display.get_default()
        if display:
            keymap = Gdk.Keymap.get_for_display(display)
            self._caps = keymap.get_caps_lock_state()
            keymap.connect("state-changed", self._on_keymap_state)
        self._sources = system.settings("org.cinnamon.desktop.input-sources")
        if self._sources:
            self._sources.connect("changed::current", self._on_layout_changed)
            self._xkb = CinnamonDesktop.XkbInfo.new() if CinnamonDesktop else None

    def _on_keymap_state(self, keymap):
        caps = keymap.get_caps_lock_state()
        if caps != self._caps:
            self._caps = caps
            self._emit("capslock", on=caps)

    def _on_layout_changed(self, settings, _key):
        sources = settings.get_value("sources").unpack()
        current = settings.get_uint("current")
        if len(sources) < 2 or current >= len(sources):
            return
        layout_id = sources[current][1]
        name = layout_id.upper()
        if self._xkb:
            found, display_name, *_rest = self._xkb.get_layout_info(layout_id)
            if found and display_name:
                name = display_name
        self._emit("layout", name=name)

    # ---- network ---------------------------------------------------------------
    def _watch_network(self):
        Gio.DBusProxy.new_for_bus(Gio.BusType.SYSTEM, Gio.DBusProxyFlags.NONE, None, *NM, None, self._on_nm_proxy)

    def _on_nm_proxy(self, _src, result):
        try:
            proxy = Gio.DBusProxy.new_for_bus_finish(result)
        except GLib.Error:
            return
        state = proxy.get_cached_property("State")
        if state is None:
            return  # NetworkManager not running
        self._nm = proxy
        self._proxies.append(proxy)
        self._net_connected = state.unpack() >= NM_CONNECTED_SITE
        proxy.connect("g-signal", self._on_nm_signal)

    def _on_nm_signal(self, proxy, _sender, signal, params):
        if signal != "StateChanged":
            return
        state = params.unpack()[0]
        if state <= NM_DISCONNECTED and self._net_connected:
            self._net_connected = False
            self._emit("network", connected=False, name="", wireless=False)
        elif state >= NM_CONNECTED_SITE and self._net_connected is False:
            self._net_connected = True
            self._describe_primary(proxy)

    def _describe_primary(self, proxy):
        path = proxy.get_cached_property("PrimaryConnection")
        path = path.unpack() if path is not None else "/"
        if path == "/":
            self._emit("network", connected=True, name="", wireless=False)
            return

        def ready(_src, result):
            try:
                active = Gio.DBusProxy.new_for_bus_finish(result)
                name = active.get_cached_property("Id").unpack()
                wireless = "wireless" in active.get_cached_property("Type").unpack()
            except (GLib.Error, AttributeError):
                name, wireless = "", False
            self._emit("network", connected=True, name=name, wireless=wireless)

        Gio.DBusProxy.new_for_bus(Gio.BusType.SYSTEM, Gio.DBusProxyFlags.NONE, None, NM[0], path,
                                  "org.freedesktop.NetworkManager.Connection.Active", None, ready)

    # ---- Bluetooth audio ---------------------------------------------------------
    def _watch_bluetooth(self):
        try:
            self._system_bus = Gio.bus_get_sync(Gio.BusType.SYSTEM, None)
        except GLib.Error:
            return
        self._system_bus.signal_subscribe(
            "org.bluez", "org.freedesktop.DBus.Properties", "PropertiesChanged", None,
            "org.bluez.Device1", Gio.DBusSignalFlags.NONE, self._on_bluez_changed)

    def _on_bluez_changed(self, bus, _sender, path, _iface, _signal, params):
        _iface_name, changed, _invalidated = params.unpack()
        if "Connected" not in changed:
            return
        connected = bool(changed["Connected"])

        def got_device(bus_, result):
            try:
                props = bus_.call_finish(result).unpack()[0]
            except GLib.Error:
                return
            icon = props.get("Icon", "")
            if not icon.startswith("audio"):
                return  # only headphones, headsets and speakers
            name = props.get("Alias") or props.get("Name") or _("Bluetooth-Gerät")
            if connected:
                self._battery(bus_, path, lambda pct: self._emit(
                    "bluetooth", name=name, connected=True, battery=pct, icon=f"{icon}-symbolic"))
            else:
                self._emit("bluetooth", name=name, connected=False, battery=None, icon=f"{icon}-symbolic")

        bus.call("org.bluez", path, "org.freedesktop.DBus.Properties", "GetAll",
                 GLib.Variant("(s)", ("org.bluez.Device1",)), GLib.VariantType("(a{sv})"),
                 Gio.DBusCallFlags.NONE, 2000, None, got_device)

    @staticmethod
    def _battery(bus, path, callback):
        def done(bus_, result):
            try:
                callback(int(bus_.call_finish(result).unpack()[0]))
            except (GLib.Error, ValueError, TypeError):
                callback(None)  # many headsets don't report it (or BlueZ without battery support)

        bus.call("org.bluez", path, "org.freedesktop.DBus.Properties", "Get",
                 GLib.Variant("(ss)", ("org.bluez.Battery1", "Percentage")), GLib.VariantType("(v)"),
                 Gio.DBusCallFlags.NONE, 2000, None, done)


def volume_icon(percent, muted=False):
    if muted or percent == 0:
        return "audio-volume-muted-symbolic"
    level = "low" if percent < 34 else "medium" if percent < 67 else "high"
    return f"audio-volume-{level}-symbolic"

