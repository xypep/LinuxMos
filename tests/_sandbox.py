"""Import this first: the island's config, data and cache folders go to a throw-away directory."""

import atexit
import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if "LINUXMOS_TEST_HOME" not in os.environ:
    home = tempfile.mkdtemp(prefix="linuxmos-test-")
    os.environ["LINUXMOS_TEST_HOME"] = home
    os.environ["XDG_CONFIG_HOME"] = os.path.join(home, "config")
    os.environ["XDG_DATA_HOME"] = os.path.join(home, "data")
    os.environ["XDG_CACHE_HOME"] = os.path.join(home, "cache")
    atexit.register(shutil.rmtree, home, True)
