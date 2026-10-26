"""Is the window in front fullscreen (a film, a game)? Follows libwnck's signals, no polling.

Only connected while the stretch reminder is on: the reminder waits until the window is not fullscreen.
"""

import logging

log = logging.getLogger("mosisland.fullscreen")


class FullscreenWatcher:
    def __init__(self, screen, on_change):
        self._screen = screen
        self._on_change = on_change
        self._screen_handler = 0
        self._window = None
        self._window_handler = 0
        self.fullscreen = False

    def start(self):
        if self._screen is None or self._screen_handler:
            return
        self._screen_handler = self._screen.connect("active-window-changed", self._on_active_changed)
        self._attach(self._screen.get_active_window())

    def stop(self):
        if self._screen_handler:
            self._screen.disconnect(self._screen_handler)
            self._screen_handler = 0
        self._detach()
        self.fullscreen = False

    def _detach(self):
        if self._window is not None and self._window_handler:
            self._window.disconnect(self._window_handler)
        self._window, self._window_handler = None, 0

    def _attach(self, window):
        self._detach()
        self._window = window
        if window is not None:
            self._window_handler = window.connect("state-changed", lambda *_: self._evaluate())
        self._evaluate()

    def _on_active_changed(self, screen, _previous):
        self._attach(screen.get_active_window())

    def _evaluate(self):
        window = self._window
        fullscreen = bool(window is not None and window.is_fullscreen())
        if fullscreen != self.fullscreen:
            self.fullscreen = fullscreen
            log.info("active window %s fullscreen", "is" if fullscreen else "is no longer")
            self._on_change(fullscreen)
