"""Is the screen locked or switched off? Asked once when a reminder falls due, never in a loop."""

import re

from island.services import system


def asleep(callback):
    """callback(True) if the screen saver is active (locked) or the monitor is off (DPMS), else False."""
    def screensaver(ok, out):
        if ok and re.search(r"\bis active\b", out):
            callback(True)
        elif system.has("xset"):
            system.run(["xset", "q"], lambda ok2, out2: callback(bool(ok2 and re.search(r"Monitor is Off", out2))))
        else:
            callback(False)

    if system.has("cinnamon-screensaver-command"):
        system.run(["cinnamon-screensaver-command", "-q"], screensaver)
    else:
        screensaver(False, "")
