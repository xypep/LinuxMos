"""The client side of the island's control interface (see app.py: CONTROL_XML).

Used by the settings window and by `linuxmos-island --list-actions` to ask the running island for the register
and its status, and to run a function. Everything is a call on the session bus, so only the user's own
processes can reach it. No GTK needed: a plain GLib main context is enough for the signal.
"""

import json

from gi.repository import Gio, GLib

from island import APP_ID

PATH = "/org/linuxmos/Island"
IFACE = "org.linuxmos.Island.Control"
TIMEOUT_MS = 4000


class Control:
    def __init__(self):
        self._bus = None
        try:
            self._bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        except GLib.Error:
            self._bus = None

    def running(self):
        """Is an island on the session bus?"""
        if self._bus is None:
            return False
        try:
            reply = self._bus.call_sync("org.freedesktop.DBus", "/org/freedesktop/DBus", "org.freedesktop.DBus",
                                        "NameHasOwner", GLib.Variant("(s)", (APP_ID,)), GLib.VariantType("(b)"),
                                        Gio.DBusCallFlags.NONE, 1000, None)
            return bool(reply.unpack()[0])
        except GLib.Error:
            return False

    def _call(self, method, args=None, reply="(s)"):
        if self._bus is None:
            raise ControlError("kein Session-Bus")
        try:
            return self._bus.call_sync(APP_ID, PATH, IFACE, method, args, GLib.VariantType(reply),
                                       Gio.DBusCallFlags.NONE, TIMEOUT_MS, None).unpack()
        except GLib.Error as error:
            raise ControlError(error.message) from None

    def registry(self):
        return json.loads(self._call("GetRegistry")[0])

    def status(self):
        return json.loads(self._call("GetStatus")[0])

    def run(self, fid):
        """(ok, message, busy)."""
        return self._call("Run", GLib.Variant("(s)", (fid,)), "(bsb)")

    def on_finished(self, callback):
        """callback() whenever the island reports that a screen grab it ran for us is over. Returns the id to
        unsubscribe with."""
        return self._bus.signal_subscribe(APP_ID, IFACE, "ActionFinished", PATH, None, Gio.DBusSignalFlags.NONE,
                                          lambda *_: callback())

    def unsubscribe(self, subscription):
        if self._bus is not None and subscription:
            self._bus.signal_unsubscribe(subscription)


class ControlError(Exception):
    pass
