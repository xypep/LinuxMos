"""A stand-in for what Cinnamon provides, for test_keepawake.py: the session manager's Inhibit (flags,
cookie, released when the client's bus connection goes away – like cinnamon-session does) and, optionally,
org.freedesktop.ScreenSaver. Usage: fake_session.py [session] [screensaver]   (prints 'ready' when it owns the names)."""

import sys

import gi

gi.require_version("Gio", "2.0")
from gi.repository import Gio, GLib

SESSION_XML = """<node><interface name="org.gnome.SessionManager">
<method name="Inhibit"><arg type="s" direction="in"/><arg type="u" direction="in"/><arg type="s" direction="in"/>
<arg type="u" direction="in"/><arg type="u" direction="out"/></method>
<method name="Uninhibit"><arg type="u" direction="in"/></method>
<method name="IsInhibited"><arg type="u" direction="in"/><arg type="b" direction="out"/></method>
<method name="GetInhibitors"><arg type="as" direction="out"/></method></interface></node>"""
SAVER_XML = """<node><interface name="org.freedesktop.ScreenSaver">
<method name="Inhibit"><arg type="s" direction="in"/><arg type="s" direction="in"/><arg type="u" direction="out"/></method>
<method name="UnInhibit"><arg type="u" direction="in"/></method>
<method name="Count"><arg type="u" direction="out"/></method></interface></node>"""

holders = {}        # cookie -> (sender, flags, app, how)
watches = {}        # sender -> watch id
counter = [100]
bus = None


def forget_sender(sender):
    for cookie in [c for c, (s, *_rest) in holders.items() if s == sender]:
        del holders[cookie]
        print(f"released {cookie} (client gone)", flush=True)
    watches.pop(sender, None)


def take(sender, flags, app, how):
    counter[0] += 1
    holders[counter[0]] = (sender, flags, app, how)
    if sender not in watches:
        watches[sender] = Gio.bus_watch_name_on_connection(bus, sender, Gio.BusNameWatcherFlags.NONE, None,
                                                           lambda *_: forget_sender(sender))
    print(f"inhibit {counter[0]} {how} flags={flags} app={app}", flush=True)
    return counter[0]


def session_call(_c, sender, _p, _i, method, params, inv):
    args = params.unpack()
    if method == "Inhibit":
        inv.return_value(GLib.Variant("(u)", (take(sender, args[3], args[0], "session"),)))
    elif method == "Uninhibit":
        holders.pop(args[0], None)
        print(f"uninhibit {args[0]}", flush=True)
        inv.return_value(None)
    elif method == "IsInhibited":
        inv.return_value(GLib.Variant("(b)", (any(f & args[0] for _s, f, *_r in holders.values()),)))
    else:
        inv.return_value(GLib.Variant("(as)", ([str(c) for c in holders],)))


def saver_call(_c, sender, _p, _i, method, params, inv):
    args = params.unpack()
    if method == "Inhibit":
        inv.return_value(GLib.Variant("(u)", (take(sender, 8, args[0], "screensaver"),)))
    elif method == "UnInhibit":
        holders.pop(args[0], None)
        print(f"uninhibit {args[0]}", flush=True)
        inv.return_value(None)
    else:
        inv.return_value(GLib.Variant("(u)", (len(holders),)))


def main(which):
    global bus
    loop = GLib.MainLoop()
    todo = [(w, x, p, n) for w, x, p, n in (
        ("session", SESSION_XML, "/org/gnome/SessionManager", "org.gnome.SessionManager"),
        ("screensaver", SAVER_XML, "/org/freedesktop/ScreenSaver", "org.freedesktop.ScreenSaver")) if w in which]
    pending = [len(todo)]

    def acquired(connection, name):
        global bus
        bus = connection
        for w, xml, path, iface in todo:
            if iface == name:
                continue
        pending[0] -= 1
        if pending[0] == 0:
            print("ready", flush=True)

    for w, xml, path, name in todo:
        def on_bus(connection, _name, xml=xml, path=path, w=w):
            global bus
            bus = connection
            node = Gio.DBusNodeInfo.new_for_xml(xml)
            connection.register_object(path, node.interfaces[0], session_call if w == "session" else saver_call,
                                       None, None)

        Gio.bus_own_name(Gio.BusType.SESSION, name, Gio.BusNameOwnerFlags.NONE, on_bus, acquired, lambda *_: loop.quit())
    loop.run()


if __name__ == "__main__":
    main(sys.argv[1:] or ["session"])
