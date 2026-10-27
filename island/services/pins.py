"""Always on top for any window: libwnck's make_above()/unmake_above(), kept in step by signals.

Only windows pinned here are watched: the screen's `window-closed` drops a pin (a libwnck window has no `closed`
signal of its own; the handler is connected only while something is pinned), `state-changed` of a pinned window
notices the user taking "Always on top" off in the window menu. Nothing polls. Pins last for this session; with
`pin_release_on_exit` the island puts them back when it quits.
"""

import logging

log = logging.getLogger("mosisland.pins")


class Pins:
    def __init__(self, wnck_module, screen, on_change, own_xids):
        self._wnck = wnck_module            # the Wnck module (None if libwnck is missing)
        self._screen = screen
        self._on_change = on_change
        self._own_xids = own_xids           # callable -> set of window ids that belong to the island
        self._pinned = {}                   # xid -> (window, state handler)
        self._closed_handler = 0            # Wnck.Screen::window-closed, only while something is pinned

    # ---- what is pinned ----------------------------------------------------------------------------
    @property
    def count(self):
        return len(self._pinned)

    def windows(self):
        return [window for window, _ in self._pinned.values()]

    def is_pinned(self, window):
        return window is not None and window.get_xid() in self._pinned

    # ---- rules ---------------------------------------------------------------------------------------------
    def blocked(self, window):
        """Why this window can't be pinned (German, one short sentence), or None if it can."""
        if self._wnck is None:
            return "libwnck fehlt"
        if window is None:
            return "Kein Fenster im Vordergrund"
        if window.get_xid() in self._own_xids():
            return "Die Insel selbst lässt sich nicht anpinnen"
        kind = window.get_window_type()
        W = self._wnck.WindowType
        if kind == W.DESKTOP:
            return "Der Schreibtisch lässt sich nicht anpinnen"
        if kind == W.DOCK:
            return "Panel und Dock lassen sich nicht anpinnen"
        if kind not in (W.NORMAL, W.DIALOG, W.UTILITY):
            return "Dieses Fenster lässt sich nicht anpinnen"
        if window.is_fullscreen():
            return "Vollbild-Fenster lassen sich nicht überlagern"
        if not self.is_pinned(window) and not window.get_actions() & self._wnck.WindowActions.ABOVE:
            return "Der Fenstermanager erlaubt es für dieses Fenster nicht"
        return None

    # ---- pin / unpin -----------------------------------------------------------------------------------
    def toggle(self, window):
        """Pin the window, or unpin it if it is. Returns (ok, message): the message tells what happened or why not."""
        if self.is_pinned(window):
            self.unpin(window)
            return True, f"Angepinnt aufgehoben: {_title(window)}"
        why = self.blocked(window)
        if why:
            return False, why
        self.pin(window)
        return True, f"Angepinnt: {_title(window)}"

    def pin(self, window):
        xid = window.get_xid()
        if xid in self._pinned:
            return
        window.make_above()
        self._pinned[xid] = (window, window.connect("state-changed", self._on_state))
        self._watch_screen()
        log.info("pinned %s (%d pinned)", _title(window), len(self._pinned))
        self._on_change()

    def unpin(self, window, put_back=True):
        entry = self._pinned.pop(window.get_xid(), None)
        if entry is None:
            return
        window.disconnect(entry[1])
        self._watch_screen()
        if put_back:
            window.unmake_above()
        log.info("unpinned %s (%d pinned)", _title(window), len(self._pinned))
        self._on_change()

    def release_all(self):
        """Take every pin back (the island quits, or the feature is switched off)."""
        for window in self.windows():
            try:
                window.unmake_above()
            except Exception:           # the window may be on its way out
                pass
        self.forget_all()
        log.info("all pins released")

    def forget_all(self):
        """Stop watching without touching the windows (the island quits and keeps them pinned)."""
        for window, handler in list(self._pinned.values()):
            window.disconnect(handler)
        self._pinned.clear()
        self._watch_screen()

    def _watch_screen(self):
        """One handler on the screen while at least one window is pinned, none otherwise."""
        if self._screen is None:
            return
        if self._pinned and not self._closed_handler:
            self._closed_handler = self._screen.connect("window-closed", self._on_closed)
        elif not self._pinned and self._closed_handler:
            self._screen.disconnect(self._closed_handler)
            self._closed_handler = 0

    # ---- signals ----------------------------------------------------------------------------------------------
    def _on_closed(self, _screen, window):
        if self._pinned.pop(window.get_xid(), None) is not None:
            log.info("pinned window closed (%d pinned)", len(self._pinned))
            self._watch_screen()
            self._on_change()

    def _on_state(self, window, _changed, _new):
        if window.get_xid() in self._pinned and not window.is_above():
            self.unpin(window, put_back=False)      # the user took it off in the window menu


def _title(window):
    name = window.get_name() or "Fenster"
    app = window.get_application()
    app_name = app.get_name() if app else ""
    return f"{app_name} · {name}"[:60] if app_name and app_name != name else name[:60]
