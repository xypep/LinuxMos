"""Now-playing state from MPRIS media players (Spotify, Firefox, VLC, Rhythmbox, ...).

Purely signal driven: players are discovered via NameOwnerChanged and their
state arrives through PropertiesChanged. Only the playback position has to be
queried, and the UI does that solely while the island is open.
"""

from dataclasses import dataclass

from gi.repository import Gio, GLib

MPRIS_PREFIX = "org.mpris.MediaPlayer2."
MPRIS_PATH = "/org/mpris/MediaPlayer2"
PLAYER_IFACE = "org.mpris.MediaPlayer2.Player"


@dataclass
class Track:
    bus_name: str
    title: str
    artist: str
    art_url: str
    length_us: int
    playing: bool
    can_next: bool
    can_previous: bool


def _cached(proxy, name):
    value = proxy.get_cached_property(name)
    return value.unpack() if value is not None else None


class MprisWatcher:
    def __init__(self, on_change):
        self._on_change = on_change
        self._players = {}  # bus name -> Gio.DBusProxy
        self._recent = []   # bus names, most recently active last
        self._bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        self._bus.signal_subscribe(
            "org.freedesktop.DBus", "org.freedesktop.DBus", "NameOwnerChanged",
            "/org/freedesktop/DBus", "org.mpris.MediaPlayer2",
            Gio.DBusSignalFlags.MATCH_ARG0_NAMESPACE, self._on_name_owner_changed,
        )
        self._bus.call(
            "org.freedesktop.DBus", "/org/freedesktop/DBus", "org.freedesktop.DBus",
            "ListNames", None, GLib.VariantType("(as)"), Gio.DBusCallFlags.NONE,
            -1, None, self._on_list_names,
        )

    # ---- discovery ---------------------------------------------------------
    def _on_list_names(self, bus, result):
        try:
            names = bus.call_finish(result).unpack()[0]
        except GLib.Error:
            return
        for name in names:
            if name.startswith(MPRIS_PREFIX):
                self._add_player(name)

    def _on_name_owner_changed(self, _bus, _sender, _path, _iface, _signal, params):
        name, _old, new = params.unpack()
        if not name.startswith(MPRIS_PREFIX):
            return
        if new:
            self._add_player(name)
        else:
            self._remove_player(name)

    def _add_player(self, name):
        if name in self._players:
            return
        Gio.DBusProxy.new(
            self._bus, Gio.DBusProxyFlags.GET_INVALIDATED_PROPERTIES, None,
            name, MPRIS_PATH, PLAYER_IFACE, None, self._on_proxy_ready, name,
        )

    def _on_proxy_ready(self, _src, result, name):
        try:
            proxy = Gio.DBusProxy.new_finish(result)
        except GLib.Error:
            return
        self._players[name] = proxy
        self._recent.append(name)
        proxy.connect("g-properties-changed", self._on_properties_changed, name)
        self._emit()

    def _remove_player(self, name):
        self._players.pop(name, None)
        if name in self._recent:
            self._recent.remove(name)
        self._emit()

    def _on_properties_changed(self, proxy, changed, _invalidated, name):
        changed = changed.unpack()
        if changed.get("PlaybackStatus") == "Playing" and name in self._recent:
            # The player that started playing last is the one we show
            self._recent.remove(name)
            self._recent.append(name)
        self._emit()

    def _emit(self):
        self._on_change(self.current())

    # ---- state -------------------------------------------------------------
    def current(self):
        """The track to show: the latest playing player, else the latest one at all."""
        if not self._recent:
            return None
        playing = [n for n in self._recent if _cached(self._players[n], "PlaybackStatus") == "Playing"]
        name = (playing or self._recent)[-1]
        proxy = self._players[name]
        meta = _cached(proxy, "Metadata") or {}
        title = meta.get("xesam:title") or ""
        if not title and _cached(proxy, "PlaybackStatus") is None:
            return None
        artist = meta.get("xesam:artist") or []
        if isinstance(artist, str):
            artist = [artist]
        return Track(
            bus_name=name,
            title=title,
            artist=", ".join(artist),
            art_url=meta.get("mpris:artUrl") or "",
            length_us=int(meta.get("mpris:length") or 0),
            playing=_cached(proxy, "PlaybackStatus") == "Playing",
            can_next=bool(_cached(proxy, "CanGoNext")),
            can_previous=bool(_cached(proxy, "CanGoPrevious")),
        )

    # ---- control -----------------------------------------------------------
    def _call(self, method):
        track = self.current()
        if track:
            self._players[track.bus_name].call(method, None, Gio.DBusCallFlags.NONE, -1, None, None)

    def play_pause(self):
        self._call("PlayPause")

    def next(self):
        self._call("Next")

    def previous(self):
        self._call("Previous")

    def query_position(self, callback):
        """Ask the active player for its position (µs); callback(position or None)."""
        track = self.current()
        if not track:
            callback(None)
            return

        def done(bus, result):
            try:
                callback(bus.call_finish(result).unpack()[0])
            except GLib.Error:
                callback(None)

        self._bus.call(
            track.bus_name, MPRIS_PATH, "org.freedesktop.DBus.Properties", "Get",
            GLib.Variant("(ss)", (PLAYER_IFACE, "Position")), GLib.VariantType("(v)"),
            Gio.DBusCallFlags.NONE, 1000, None, done,
        )
