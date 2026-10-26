"""Notifications as cards on the island – the island only listens in.

Cinnamon stays the notification server: it owns org.freedesktop.Notifications
and keeps the history in its applet. The island opens a second connection to
the session bus and turns it into a monitor (BecomeMonitor), which receives
copies of just these messages:
  Notify                   an app shows a notification          -> card
  the reply to Notify      the id Cinnamon gave it              -> updates, closing
  NotificationClosed (3)   the app withdrew it (e.g. was read)  -> card goes
Nothing is polled; between notifications the connection is silent. A bus that
refuses BecomeMonitor gets eavesdropping match rules instead.

While the cards are on, the island switches Cinnamon's banners off
(org.cinnamon.desktop.notifications display-notifications = false). Cinnamon
then files every notification straight into its applet. `banners_hidden` is
kept on disk, so the island knows after a crash that it was the one.
"""

import html
import re

import gi

gi.require_version("GdkPixbuf", "2.0")
from gi.repository import GdkPixbuf, Gio, GLib  # noqa: E402

from island.storage import DATA_DIR, load_json, save_json  # noqa: E402

STATE_FILE = DATA_DIR / "notifications.json"
IFACE = "org.freedesktop.Notifications"
BUS = ("org.freedesktop.DBus", "/org/freedesktop/DBus")
RULES = [
    f"type='method_call',interface='{IFACE}',member='Notify'",
    f"type='method_return',sender='{IFACE}'",
    f"type='signal',interface='{IFACE}',member='NotificationClosed'",
]
NOTIFY_SIGNATURE = "(susssasa{sv}i)"
IMAGE_SIGNATURE = GLib.VariantType("(iiibiiay)")
CLOSED_BY_APP = 3
URGENCY_CRITICAL = 2
MAX_APPS = 12        # apps remembered for the tray's "hide" list
MAX_PENDING = 32     # Notify calls waiting for Cinnamon's reply
IMAGE_PX = 80        # pictures are scaled to this once (shown at 40 px, 2x for HiDPI)

_TAG = re.compile(r"<[^>]*>")
_BREAK = re.compile(r"<br\s*/?>", re.IGNORECASE)


class Notification:
    """One Notify call, as far as the island needs it."""

    __slots__ = ("id", "sender", "pid", "app", "entry", "replaces", "icon", "summary", "body",
                 "image", "urgency", "timeout", "_image_data", "_image_path")

    def __init__(self):
        self.id = None       # set once Cinnamon's reply passes by
        self.pid = None      # sender's process, looked up on the main thread
        self.image = None    # GdkPixbuf (avatar, cover) or None, see load_image()
        self._image_data = None
        self._image_path = ""

    def load_image(self):
        """Picture by the spec's priority: image-data, image-path, a file given as the app icon.

        Main thread only: file loading may touch GIO, which must not run on GDBus' worker thread.
        """
        if self._image_data is not None:
            self.image = _image_from_data(*self._image_data)
        for path in (self._image_path, self.icon):
            if self.image is None and path.startswith(("/", "file://")):
                self.image = _image_from_path(path)
        self._image_data = None

    @property
    def name(self):
        """What the user knows the app as (also the key of the hide list)."""
        if self.app:
            return self.app
        if self.entry:
            info = desktop_info(self.entry)
            return info.get_name() if info else self.entry
        return ""


def plain_text(markup):
    """Notification bodies may carry <b>, <i>, <a>, <img> and entities."""
    text = _TAG.sub("", _BREAK.sub("\n", markup or ""))
    return html.unescape(text).strip()


def desktop_info(entry):
    if not entry:
        return None
    name = entry if entry.endswith(".desktop") else f"{entry}.desktop"
    try:
        return Gio.DesktopAppInfo.new(name)
    except TypeError:  # PyGObject raises instead of returning NULL
        return None


def _hint_string(hints, *keys):
    for key in keys:
        value = hints.lookup_value(key, GLib.VariantType("s"))
        if value is not None and value.get_string():
            return value.get_string()
    return ""


def _raw_image(hints):
    """image-data (iiibiiay): raw pixels, e.g. the sender's avatar in chat apps."""
    for key in ("image-data", "image_data", "icon_data"):
        value = hints.lookup_value(key, IMAGE_SIGNATURE)
        if value is not None:
            width, height, rowstride = (value.get_child_value(i).get_int32() for i in range(3))
            return (width, height, rowstride, value.get_child_value(3).get_boolean(),
                    value.get_child_value(4).get_int32(), value.get_child_value(5).get_int32(),
                    value.get_child_value(6).get_data_as_bytes())
    return None


def _image_from_data(width, height, rowstride, has_alpha, bits, channels, data):
    # Anything GdkPixbuf can't take, or less data than the header promises, is dropped
    row = width * (4 if has_alpha else 3)
    if (bits != 8 or channels != (4 if has_alpha else 3) or not 0 < width <= 4096 or not 0 < height <= 4096
            or rowstride < row or data.get_size() < rowstride * (height - 1) + row):
        return None
    try:
        pixbuf = GdkPixbuf.Pixbuf.new_from_bytes(data, GdkPixbuf.Colorspace.RGB, has_alpha, bits,
                                                 width, height, rowstride)
    except GLib.Error:
        return None
    return _shrink(pixbuf)


def _image_from_path(path):
    if path.startswith("file://"):
        try:
            path = GLib.filename_from_uri(path)[0]
        except GLib.Error:
            return None
    try:
        return GdkPixbuf.Pixbuf.new_from_file_at_scale(path, IMAGE_PX, IMAGE_PX, True)
    except GLib.Error:
        return None


def _shrink(pixbuf):
    w, h = pixbuf.get_width(), pixbuf.get_height()
    if max(w, h) <= IMAGE_PX:
        return pixbuf.copy()  # detach from the message's memory
    factor = IMAGE_PX / max(w, h)
    return pixbuf.scale_simple(max(1, round(w * factor)), max(1, round(h * factor)),
                               GdkPixbuf.InterpType.BILINEAR)


def _parse_notify(message):
    body = message.get_body()
    if body is None or body.get_type_string() != NOTIFY_SIGNATURE:
        return None
    hints = body.get_child_value(6)
    n = Notification()
    n.sender = message.get_sender()
    n.app = body.get_child_value(0).get_string().strip()
    n.replaces = body.get_child_value(1).get_uint32()
    n.icon = body.get_child_value(2).get_string()
    n.summary = plain_text(body.get_child_value(3).get_string())
    n.body = plain_text(body.get_child_value(4).get_string())
    n.timeout = body.get_child_value(7).get_int32()
    n.entry = _hint_string(hints, "desktop-entry")
    urgency = hints.lookup_value("urgency", GLib.VariantType("y"))
    n.urgency = urgency.get_byte() if urgency is not None else 1
    n._image_data = _raw_image(hints)
    n._image_path = _hint_string(hints, "image-path", "image_path")
    return n


class Notifications:
    def __init__(self, on_notify, on_closed):
        """on_notify(Notification) for every new or updated one, on_closed(id) when an app withdraws one."""
        self._on_notify = on_notify
        self._on_closed = on_closed
        self._conn = None
        self._cancellable = None
        self._pending = {}  # (sender, serial) -> Notification, until the reply names its id
        state = load_json(STATE_FILE, {})
        state = state if isinstance(state, dict) else {}
        self.apps = [a for a in state.get("apps", []) if isinstance(a, str) and a][:MAX_APPS]
        self.banners_hidden = bool(state.get("banners_hidden"))

    # ---- persisted state ---------------------------------------------------------
    def _save(self):
        save_json(STATE_FILE, {"apps": self.apps, "banners_hidden": self.banners_hidden})

    def set_banners_hidden(self, hidden):
        if hidden != self.banners_hidden:
            self.banners_hidden = hidden
            self._save()

    def remember(self, name):
        """Note an app for the tray's hide list; True if it is new there."""
        if not name or (self.apps and self.apps[0] == name):
            return False
        known = name.lower() in (a.lower() for a in self.apps)
        self.apps = [name] + [a for a in self.apps if a.lower() != name.lower()]
        del self.apps[MAX_APPS:]
        self._save()
        return not known

    # ---- monitor connection -------------------------------------------------------
    @property
    def running(self):
        return self._cancellable is not None

    def start(self):
        if self.running:
            return
        try:
            address = Gio.dbus_address_get_for_bus_sync(Gio.BusType.SESSION, None)
        except GLib.Error:
            return
        self._cancellable = Gio.Cancellable()
        Gio.DBusConnection.new_for_address(
            address, Gio.DBusConnectionFlags.AUTHENTICATION_CLIENT | Gio.DBusConnectionFlags.MESSAGE_BUS_CONNECTION,
            None, self._cancellable, self._on_connected)

    def stop(self):
        if self._cancellable:
            self._cancellable.cancel()
            self._cancellable = None
        if self._conn:
            self._conn.close(None, None)
            self._conn = None
        self._pending.clear()

    def _on_connected(self, _src, result):
        try:
            conn = Gio.DBusConnection.new_for_address_finish(result)
        except GLib.Error:
            return  # stopped meanwhile, or no session bus
        if not self.running:
            conn.close(None, None)
            return
        self._conn = conn
        conn.add_filter(self._filter)
        conn.call(*BUS, "org.freedesktop.DBus.Monitoring", "BecomeMonitor", GLib.Variant("(asu)", (RULES, 0)),
                  None, Gio.DBusCallFlags.NONE, 5000, self._cancellable, self._on_monitor)

    def _on_monitor(self, conn, result):
        try:
            conn.call_finish(result)
        except GLib.Error as error:
            if error.matches(Gio.io_error_quark(), Gio.IOErrorEnum.CANCELLED):
                return
            # Bus without BecomeMonitor (or not allowed): eavesdrop instead
            for rule in RULES:
                conn.call(*BUS, "org.freedesktop.DBus", "AddMatch", GLib.Variant("(s)", (f"{rule},eavesdrop='true'",)),
                          None, Gio.DBusCallFlags.NONE, 5000, self._cancellable, None)

    def _filter(self, conn, message, incoming):
        """Runs on GDBus' worker thread: parse there, hand over to the main loop.

        Every copy we listen to is dropped (None), so GDBus never answers or
        routes it; the bus driver's own replies (BecomeMonitor, AddMatch) pass.
        """
        if not incoming or message.get_sender() == BUS[0]:
            return message
        kind = message.get_message_type()
        try:
            if kind == Gio.DBusMessageType.METHOD_CALL:
                if message.get_member() == "Notify":
                    n = _parse_notify(message)
                    if n is not None:
                        GLib.idle_add(self._dispatch_notify, conn, n, message.get_serial())
            elif kind == Gio.DBusMessageType.METHOD_RETURN:
                body = message.get_body()
                if body is not None and body.get_type_string() == "(u)":
                    GLib.idle_add(self._dispatch_reply, conn, message.get_destination(),
                                  message.get_reply_serial(), body.get_child_value(0).get_uint32())
            elif kind == Gio.DBusMessageType.SIGNAL and message.get_member() == "NotificationClosed":
                body = message.get_body()
                if body is not None and body.get_type_string() == "(uu)":
                    GLib.idle_add(self._dispatch_closed, conn, *body.unpack())
        except (GLib.Error, TypeError, ValueError):
            pass  # a malformed message never takes the island down
        return None

    def _dispatch_notify(self, conn, n, serial):
        if conn is self._conn:
            if len(self._pending) >= MAX_PENDING:
                self._pending.pop(next(iter(self._pending)))
            self._pending[(n.sender, serial)] = n
            n.load_image()
            self._lookup_pid(n)
            self._on_notify(n)
        return GLib.SOURCE_REMOVE

    def _dispatch_reply(self, conn, destination, serial, notification_id):
        n = self._pending.pop((destination, serial), None) if conn is self._conn else None
        if n is not None:
            n.id = notification_id
        return GLib.SOURCE_REMOVE

    def _dispatch_closed(self, conn, notification_id, reason):
        if conn is self._conn and reason == CLOSED_BY_APP:
            self._on_closed(notification_id)
        return GLib.SOURCE_REMOVE

    @staticmethod
    def _lookup_pid(n):
        """The sender's process, to find its window on click (short-lived senders are already gone)."""
        def done(bus, result):
            try:
                n.pid = bus.call_finish(result).unpack()[0]
            except GLib.Error:
                pass

        try:
            bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        except GLib.Error:
            return
        bus.call(*BUS, "org.freedesktop.DBus", "GetConnectionUnixProcessID", GLib.Variant("(s)", (n.sender,)),
                 GLib.VariantType("(u)"), Gio.DBusCallFlags.NONE, 1000, None, done)
