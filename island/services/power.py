"""Battery state from UPower (signal driven, no polling)."""

from gi.repository import Gio, GLib

UPOWER = "org.freedesktop.UPower"
DISPLAY_DEVICE = "/org/freedesktop/UPower/devices/DisplayDevice"
DEVICE_IFACE = "org.freedesktop.UPower.Device"

TYPE_BATTERY = 2
STATE_CHARGING, STATE_FULL, STATE_PENDING_CHARGE = 1, 4, 5


class Battery:
    def __init__(self, on_change):
        self._on_change = on_change
        self._proxy = None
        self.present = False
        self.percentage = 0
        self.plugged = False
        Gio.DBusProxy.new_for_bus(
            Gio.BusType.SYSTEM, Gio.DBusProxyFlags.NONE, None,
            UPOWER, DISPLAY_DEVICE, DEVICE_IFACE, None, self._on_ready,
        )

    def _on_ready(self, _src, result):
        try:
            self._proxy = Gio.DBusProxy.new_for_bus_finish(result)
        except GLib.Error:
            return  # no UPower (desktop PC, container) -> simply no battery
        self._proxy.connect("g-properties-changed", lambda *_: self._refresh(notify=True))
        self._refresh(notify=False)

    def _get(self, name):
        value = self._proxy.get_cached_property(name)
        return value.unpack() if value is not None else None

    def _refresh(self, notify):
        was_plugged = self.plugged
        self.present = bool(self._get("IsPresent")) and self._get("Type") == TYPE_BATTERY
        self.percentage = round(self._get("Percentage") or 0)
        self.plugged = self._get("State") in (STATE_CHARGING, STATE_FULL, STATE_PENDING_CHARGE)
        just_plugged = notify and self.present and self.plugged and not was_plugged
        self._on_change(self, just_plugged)

    @property
    def icon_name(self):
        level = "full" if self.percentage >= 90 else "good" if self.percentage >= 50 \
            else "low" if self.percentage >= 20 else "caution"
        return f"battery-{level}{'-charging' if self.plugged else ''}-symbolic"
