"""VPN on/off as a live hint, optionally with the exit's country and IP.

Push based through NetworkManager, nothing is polled:
  NM VPN connections   OpenVPN, WireGuard, ... (ActiveConnections, StateChanged)
  other VPN apps       Mullvad, Proton CLI, wg-quick, openvpn: their tun/wireguard
                       interface shows up in NetworkManager's devices (unmanaged)
Bridges and VM interfaces (virbr, vnet, docker, ...) are no VPN and stay out.

The country/IP lookup asks ipinfo.io once per connect – only with
"vpn_lookup" on (off by default): that request leaves the machine.
"""

import gettext
import json

from gi.repository import Gio, GLib

from island import i18n
from island.services import http

NM = ("org.freedesktop.NetworkManager", "/org/freedesktop/NetworkManager", "org.freedesktop.NetworkManager")
ACTIVE_IFACE = "org.freedesktop.NetworkManager.Connection.Active"
DEVICE_IFACE = "org.freedesktop.NetworkManager.Device"
VPN_TYPES = {"vpn", "wireguard"}
ACTIVATING, ACTIVATED = 1, 2
DEV_TUN, DEV_WIREGUARD = 16, 29
NOT_VPN = ("virbr", "vnet", "docker", "veth", "br-", "vboxnet", "vmnet", "tap", "lxc", "lxd")
SCAN_DEBOUNCE_MS = 500
LOOKUP_DELAY_S = 2       # routes and DNS settle after the tunnel comes up
LOOKUP_URL = "https://ipinfo.io/json"
ISO_3166 = "/usr/share/iso-codes/json/iso_3166-1.json"


def flag(code):
    """'DE' -> 🇩🇪 (regional indicator letters)."""
    if len(code) != 2 or not code.isalpha():
        return ""
    return "".join(chr(0x1F1E6 + ord(c) - ord("A")) for c in code.upper())


def country_name(code):
    """Country name in the UI language from iso-codes (installed on Mint), else the code."""
    try:
        with open(ISO_3166, encoding="utf-8") as fh:
            entries = json.load(fh)["3166-1"]
    except (OSError, ValueError, KeyError):
        return code
    for entry in entries:
        if entry.get("alpha_2") == code.upper():
            name = entry.get("common_name") or entry.get("name") or code
            if i18n.current() == "en":
                return name
            try:
                return gettext.translation("iso_3166-1", languages=[i18n.current()]).gettext(name)
            except OSError:
                return name
    return code


class Vpn:
    def __init__(self, config, on_change):
        """on_change(event): "up" (names), "down", "info" (country/IP arrived)."""
        self.config = config
        self._on_change = on_change
        self.enabled = False
        self.names = []          # active VPNs
        self.info = None         # dict(ip, country, flag) after a lookup
        self._known = False      # the start state is no event
        self._bus = None
        self._proxy = None
        self._subs = []
        self._scan_id = 0
        self._generation = 0
        self._lookup_id = 0

    # ---- lifecycle ---------------------------------------------------------------
    def start(self):
        if self.enabled:
            return
        self.enabled = True
        self._known = False
        try:
            self._bus = Gio.bus_get_sync(Gio.BusType.SYSTEM, None)
        except GLib.Error:
            return
        Gio.DBusProxy.new(self._bus, Gio.DBusProxyFlags.DO_NOT_AUTO_START, None, *NM, None, self._on_proxy)
        # A VPN's state changes on its own object (activating -> activated), not in ActiveConnections
        self._subs.append(self._bus.signal_subscribe(
            NM[0], ACTIVE_IFACE, "StateChanged", None, None, Gio.DBusSignalFlags.NONE,
            lambda *_: self._schedule_scan()))

    def stop(self):
        if not self.enabled:
            return
        self.enabled = False
        for sub in self._subs:
            self._bus.signal_unsubscribe(sub)
        self._subs = []
        self._proxy = None
        for attr in ("_scan_id", "_lookup_id"):
            if getattr(self, attr):
                GLib.source_remove(getattr(self, attr))
                setattr(self, attr, 0)
        self._generation += 1
        self.names, self.info = [], None

    def _on_proxy(self, _src, result):
        try:
            proxy = Gio.DBusProxy.new_finish(result)
        except GLib.Error:
            return
        if not self.enabled or proxy.get_name_owner() is None:
            return   # NetworkManager not running
        self._proxy = proxy
        proxy.connect("g-properties-changed", self._on_properties)
        proxy.connect("g-signal", lambda _p, _s, signal, _a:
                      signal in ("DeviceAdded", "DeviceRemoved") and self._schedule_scan())
        self._schedule_scan(0)

    def _on_properties(self, _proxy, changed, _invalidated):
        keys = changed.keys()
        if "ActiveConnections" in keys or "AllDevices" in keys:
            self._schedule_scan()

    # ---- scan: which VPNs are up ---------------------------------------------------
    def _schedule_scan(self, ms=SCAN_DEBOUNCE_MS):
        if not self.enabled:
            return
        if self._scan_id:
            GLib.source_remove(self._scan_id)
        self._scan_id = GLib.timeout_add(ms, self._scan)

    def _cached(self, name):
        value = self._proxy.get_cached_property(name) if self._proxy else None
        return value.unpack() if value is not None else []

    def _scan(self):
        self._scan_id = 0
        if self._proxy is None:
            return GLib.SOURCE_REMOVE
        self._generation += 1
        generation = self._generation
        conns, devices = self._cached("ActiveConnections"), self._cached("AllDevices")
        results = {"conns": {}, "devices": {}}
        pending = [len(conns) + len(devices)]

        def got(kind, path, props):
            if generation != self._generation:
                return   # a newer scan runs
            results[kind][path] = props
            pending[0] -= 1
            if pending[0] == 0:
                self._apply(results)

        if not pending[0]:
            self._apply(results)
        for path in conns:
            self._get_all(path, ACTIVE_IFACE, lambda props, p=path: got("conns", p, props))
        for path in devices:
            self._get_all(path, DEVICE_IFACE, lambda props, p=path: got("devices", p, props))
        return GLib.SOURCE_REMOVE

    def _get_all(self, path, iface, callback):
        def done(bus, result):
            try:
                callback(bus.call_finish(result).unpack()[0])
            except GLib.Error:
                callback({})   # gone meanwhile

        self._bus.call(NM[0], path, "org.freedesktop.DBus.Properties", "GetAll",
                       GLib.Variant("(s)", (iface,)), GLib.VariantType("(a{sv})"),
                       Gio.DBusCallFlags.NONE, 2000, None, done)

    def _apply(self, results):
        names = vpn_names(results["conns"].values(), results["devices"].values())
        old, self.names = self.names, names
        if not self._known:
            self._known = True
            return   # what was up before the island started is no news
        if names and names != old:
            self.info = None
            self._on_change("up")
            self._schedule_lookup()
        elif old and not names:
            self.info = None
            self._on_change("down")

    # ---- country / IP --------------------------------------------------------------
    def refresh_info(self):
        """The lookup was just switched on: ask now if a VPN is up."""
        if self.enabled and self.names and self.info is None:
            self._schedule_lookup()

    def _schedule_lookup(self):
        if self._lookup_id:
            GLib.source_remove(self._lookup_id)
            self._lookup_id = 0
        if self.config.get("vpn_lookup", False):
            self._lookup_id = GLib.timeout_add_seconds(LOOKUP_DELAY_S, self._lookup)

    def _lookup(self):
        self._lookup_id = 0
        generation = self._generation
        http.get_json(LOOKUP_URL, lambda _status, data: self._got_lookup(generation, data), timeout=8)
        return GLib.SOURCE_REMOVE

    def _got_lookup(self, generation, data):
        if generation != self._generation or not self.names or not isinstance(data, dict):
            return
        code = str(data.get("country") or "")
        self.info = {"ip": str(data.get("ip") or ""), "flag": flag(code),
                     "country": country_name(code) if code else ""}
        self._on_change("info")


def vpn_names(conns, devices):
    """Names of the VPNs that are up: NM VPN connections, else VPN-like interfaces."""
    names, nm_vpn = [], False
    for props in conns:
        kind = props.get("Type", "")
        if (props.get("Vpn") or kind in VPN_TYPES) and props.get("State") in (ACTIVATING, ACTIVATED):
            nm_vpn = True
            if props.get("State") == ACTIVATED and props.get("Id") and props["Id"] not in names:
                names.append(props["Id"])
    if nm_vpn:
        return names   # their tunnel devices are the same VPN (still connecting: not up yet)
    for props in devices:
        iface = props.get("Interface", "")
        if props.get("DeviceType") in (DEV_TUN, DEV_WIREGUARD) and iface and not iface.startswith(NOT_VPN):
            names.append(iface)
    return names
