"""The island's keep-awake service on its own, for test_keepawake.py: start it, say what happened, wait to be killed.
Usage: keepawake_client.py [MINUTES]   (stdin line 'stop' switches it off, SIGTERM quits through shutdown())."""

import os
import signal
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import gi

gi.require_version("Gio", "2.0")
from gi.repository import GLib

from island.services.keepawake import KeepAwake

loop = GLib.MainLoop()


def changed():
    k = awake
    print(f"state active={k.active} backend={k.backend} failed={k.failed}", flush=True)


awake = KeepAwake(changed)
GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGTERM, lambda: (awake.shutdown(), loop.quit(), False)[2])
awake.start(float(sys.argv[1]) if len(sys.argv) > 1 else 0)
GLib.io_add_watch(0, GLib.IO_IN, lambda *_: (awake.stop("asked") if sys.stdin.readline().strip() == "stop" else None, True)[1])
loop.run()
