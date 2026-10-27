"""Always on top: the rules about what may be pinned, the bookkeeping, and the signals (fake libwnck, no display)."""

import itertools
import unittest

from tests import _sandbox  # noqa: F401  (must come first)
from island.services.pins import Pins


class WindowType:
    NORMAL, DIALOG, UTILITY, DESKTOP, DOCK, MENU, SPLASHSCREEN, TOOLBAR = range(8)


class WindowActions:
    ABOVE = 1


class FakeWnck:
    WindowType = WindowType
    WindowActions = WindowActions


class Signals:
    def __init__(self):
        self._handlers, self._ids = {}, itertools.count(1)

    def connect(self, name, callback):
        hid = next(self._ids)
        self._handlers[hid] = (name, callback)
        return hid

    def disconnect(self, hid):
        del self._handlers[hid]

    def emit(self, name, *args):
        for n, cb in list(self._handlers.values()):
            if n == name:
                cb(self, *args)

    def count(self):
        return len(self._handlers)


class FakeApp:
    def get_name(self):
        return "Firefox"


class FakeWindow(Signals):
    def __init__(self, xid, kind=WindowType.NORMAL, name="Seite", fullscreen=False, actions=WindowActions.ABOVE):
        super().__init__()
        self.xid, self.kind, self.name, self.fullscreen, self.actions, self.above = xid, kind, name, fullscreen, actions, False

    get_xid = lambda self: self.xid                                    # noqa: E731
    get_window_type = lambda self: self.kind                           # noqa: E731
    get_name = lambda self: self.name                                  # noqa: E731
    get_application = lambda self: FakeApp()                           # noqa: E731
    is_fullscreen = lambda self: self.fullscreen                       # noqa: E731
    get_actions = lambda self: self.actions                            # noqa: E731
    is_above = lambda self: self.above                                 # noqa: E731

    def make_above(self):
        self.above = True

    def unmake_above(self):
        self.above = False

    def menu_unpin(self):
        """The user takes 'Always on top' off in the window menu."""
        self.above = False
        self.emit("state-changed", 0, 0)


class Case(unittest.TestCase):
    def setUp(self):
        self.screen = Signals()
        self.changes = 0
        self.own = {999}
        self.pins = Pins(FakeWnck, self.screen, self.changed, lambda: self.own)

    def changed(self):
        self.changes += 1


class Rules(Case):
    def test_a_normal_window_can_be_pinned_and_unpinned(self):
        w = FakeWindow(1)
        ok, message = self.pins.toggle(w)
        self.assertTrue(ok)
        self.assertIn("Angepinnt", message)
        self.assertTrue(w.above)
        self.assertEqual((self.pins.count, self.pins.is_pinned(w)), (1, True))
        ok, message = self.pins.toggle(w)
        self.assertTrue(ok)
        self.assertFalse(w.above)
        self.assertEqual(self.pins.count, 0)

    def test_what_may_not_be_pinned_and_why(self):
        cases = [(None, "Kein Fenster"), (FakeWindow(999), "Insel selbst"),
                 (FakeWindow(2, WindowType.DESKTOP), "Schreibtisch"), (FakeWindow(3, WindowType.DOCK), "Panel"),
                 (FakeWindow(4, WindowType.MENU), "lässt sich nicht"), (FakeWindow(5, fullscreen=True), "Vollbild"),
                 (FakeWindow(6, actions=0), "Fenstermanager")]
        for window, reason in cases:
            ok, message = self.pins.toggle(window)
            self.assertFalse(ok)
            self.assertIn(reason, message)
            if window is not None:
                self.assertFalse(window.above)
        self.assertEqual((self.pins.count, self.changes), (0, 0))

    def test_dialogs_and_utility_windows_are_fine(self):
        for n, kind in enumerate((WindowType.DIALOG, WindowType.UTILITY)):
            self.assertTrue(self.pins.toggle(FakeWindow(10 + n, kind))[0])

    def test_without_libwnck(self):
        pins = Pins(None, None, self.changed, lambda: set())
        self.assertEqual(pins.toggle(FakeWindow(1)), (False, "libwnck fehlt"))

    def test_a_fullscreen_window_that_is_pinned_can_still_be_unpinned(self):
        w = FakeWindow(1)
        self.pins.toggle(w)
        w.fullscreen = True
        self.assertTrue(self.pins.toggle(w)[0])


class Signal(Case):
    def test_a_closed_window_drops_its_pin(self):
        a, b = FakeWindow(1), FakeWindow(2)
        self.pins.toggle(a)
        self.pins.toggle(b)
        self.screen.emit("window-closed", a)
        self.assertEqual((self.pins.count, [w.xid for w in self.pins.windows()]), (1, [2]))
        self.screen.emit("window-closed", FakeWindow(3))                  # one that was never pinned
        self.assertEqual(self.pins.count, 1)

    def test_taking_it_off_in_the_window_menu_is_noticed(self):
        w = FakeWindow(1)
        self.pins.toggle(w)
        w.menu_unpin()
        self.assertEqual(self.pins.count, 0)

    def test_there_is_a_handler_on_the_screen_only_while_something_is_pinned(self):
        self.assertEqual(self.screen.count(), 0)
        a, b = FakeWindow(1), FakeWindow(2)
        self.pins.toggle(a)
        self.pins.toggle(b)
        self.assertEqual((self.screen.count(), a.count(), b.count()), (1, 1, 1))
        self.pins.toggle(a)
        self.assertEqual((self.screen.count(), a.count()), (1, 0))
        self.pins.toggle(b)
        self.assertEqual((self.screen.count(), b.count()), (0, 0))


class Release(Case):
    def test_release_all_puts_everything_back_and_leaves_no_handlers(self):
        windows = [FakeWindow(n) for n in (1, 2, 3)]
        for w in windows:
            self.pins.toggle(w)
        self.pins.release_all()
        self.assertEqual((self.pins.count, self.screen.count()), (0, 0))
        self.assertTrue(all(not w.above and w.count() == 0 for w in windows))

    def test_forget_all_keeps_the_windows_pinned(self):
        w = FakeWindow(1)
        self.pins.toggle(w)
        self.pins.forget_all()
        self.assertTrue(w.above)
        self.assertEqual((self.pins.count, w.count(), self.screen.count()), (0, 0, 0))


if __name__ == "__main__":
    unittest.main()
