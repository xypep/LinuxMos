"""MosIsland (LinuxMos) – a Dynamic-Island-style status pill for Linux Mint Cinnamon."""

import os
from contextlib import contextmanager

__version__ = "1.12.0"
APP_ID = "org.linuxmos.Island"


@contextmanager
def without_gl():
    """Import GTK inside this block: GDK then skips probing the OpenGL driver.

    GDK 3 loads the GL driver at start-up only to rank the X visuals. The island
    draws with Cairo alone, and Mesa's driver brings libLLVM along (~49 MB of
    the island's memory). The variable leaves the environment again afterwards,
    so apps started from the island keep their OpenGL. A GDK_GL the user set wins.
    """
    preset = "GDK_GL" in os.environ
    if not preset:
        os.environ["GDK_GL"] = "disable"
    try:
        yield
    finally:
        if not preset:
            os.environ.pop("GDK_GL", None)
