"""Now-playing state from MPRIS media players (Spotify, Firefox, VLC, Rhythmbox, ...).

Purely signal driven: players are discovered via NameOwnerChanged and their
state arrives through PropertiesChanged. The playback position is not
signalled by MPRIS, so a small clock extrapolates it from one query
(re-anchored on play/pause, track change and the Seeked signal).
"""

from dataclasses import dataclass

from gi.repository import Gio, GLib

MPRIS_PREFIX = "org.mpris.MediaPlayer2."
MPRIS_PATH = "/org/mpris/MediaPlayer2"
PLAYER_IFACE = "org.mpris.MediaPlayer2.Player"


@dataclass
class Track:
    bus_name: str
    track_id: str
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
    def __init__(self, on_change, on_position=None):
        self._on_change = on_change
        self._on_position = on_position
        # Position clock: (bus name, position µs, monotonic µs, playing)
        self._anchor = None
        self._last_key = None
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
        proxy.connect("g-signal", self._on_player_signal, name)
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

    def _on_player_signal(self, _proxy, _sender, signal, params, name):
        if signal == "Seeked":
            track = self.current()
            if track and track.bus_name == name:
                self._set_anchor(track, params.unpack()[0])

    def _emit(self):
        track = self.current()
        key = (track.bus_name, track.track_id, track.title, track.playing) if track else None
        if key != self._last_key:
            # New song, other player, play or pause: re-anchor the position clock
            self._last_key = key
            self.sync()
        self._on_change(track)

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
        track_id = meta.get("mpris:trackid") or ""
        return Track(
            bus_name=name,
            track_id=str(track_id),
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

    # ---- position clock -----------------------------------------------------
    def _set_anchor(self, track, position_us):
        self._anchor = (track.bus_name, int(position_us), GLib.get_monotonic_time(), track.playing)
        if self._on_position:
            self._on_position()

    def sync(self):
        """Re-read the real position once (after which the clock runs on its own)."""
        track = self.current()
        if not track:
            self._anchor = None
            return
        self.query_position(lambda pos: self._set_anchor(track, pos) if pos is not None else None)

    def position(self):
        """Current position in µs, extrapolated without any D-Bus traffic."""
        track = self.current()
        if not track or not self._anchor or self._anchor[0] != track.bus_name:
            return None
        _name, pos, mono, playing = self._anchor
        if playing and track.playing:
            pos += GLib.get_monotonic_time() - mono
        return min(pos, track.length_us) if track.length_us else pos

    def set_position(self, position_us):
        """Seek to an absolute position (progress bar, lyrics line)."""
        track = self.current()
        if not track:
            return
        proxy = self._players[track.bus_name]
        position_us = max(0, int(position_us))
        if track.track_id.startswith("/") and "NoTrack" not in track.track_id:
            proxy.call("SetPosition", GLib.Variant("(ox)", (track.track_id, position_us)),
                       Gio.DBusCallFlags.NONE, -1, None, None)
        else:
            # Players without a track id only support relative seeking
            current = self.position() or 0
            proxy.call("Seek", GLib.Variant("(x)", (position_us - current,)), Gio.DBusCallFlags.NONE, -1, None, None)
        # Optimistic update; the player's Seeked signal corrects it if needed
        self._set_anchor(track, position_us)

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
