"""Keep awake against stand-ins for Cinnamon's session manager and screen saver on a private session bus:
the lock is taken, flagged for idle and suspend, released on request, on a timer, on SIGTERM, and when the
client is killed with SIGKILL (the lock belongs to the bus connection)."""

import os
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
PYTHON = shutil.which("python3.12") or sys.executable


def have_gi():
    return subprocess.run([PYTHON, "-c", "import gi; gi.require_version('Gio','2.0')"],
                          capture_output=True).returncode == 0


@unittest.skipUnless(shutil.which("dbus-daemon") and have_gi(), "needs dbus-daemon and PyGObject")
class KeepAwake(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="kat-")
        daemon = subprocess.Popen(["dbus-daemon", "--session", "--nofork", "--print-address"], stdout=subprocess.PIPE,
                                  text=True)
        self.daemon = daemon
        self.env = dict(os.environ, DBUS_SESSION_BUS_ADDRESS=daemon.stdout.readline().strip(),
                        GSETTINGS_BACKEND="memory", PYTHONPATH=str(HERE.parent))
        self.procs = [daemon]

    def tearDown(self):
        for proc in self.procs:
            if proc.poll() is None:
                proc.kill()
            proc.wait()
            for stream in (proc.stdout, proc.stdin):
                if stream:
                    stream.close()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def spawn(self, script, *args, env=None):
        proc = subprocess.Popen([PYTHON, str(HERE / script), *args], env=env or self.env, stdout=subprocess.PIPE,
                                stdin=subprocess.PIPE, text=True)
        self.procs.append(proc)
        return proc

    def wait_for(self, proc, text, timeout=8):
        end = time.time() + timeout
        seen = []
        while time.time() < end:
            line = proc.stdout.readline()
            if not line:
                break
            seen.append(line.strip())
            if text in line:
                return seen
        self.fail(f"never saw {text!r}: {seen}")

    def fake(self, *which):
        proc = self.spawn("fake_session.py", *which)
        self.wait_for(proc, "ready")
        return proc

    # ---- the session manager path ------------------------------------------------------------------
    def test_lock_with_idle_and_suspend_flags_then_released_on_stop(self):
        fake = self.fake("session")
        client = self.spawn("keepawake_client.py")
        self.wait_for(client, "active=True backend=session")
        self.assertIn("flags=12", "".join(self.wait_for(fake, "inhibit")))       # suspend (4) + idle (8)
        client.stdin.write("stop\n")
        client.stdin.flush()
        self.wait_for(client, "active=False")
        self.wait_for(fake, "uninhibit")

    def test_lock_is_released_when_the_client_is_killed(self):
        fake = self.fake("session")
        client = self.spawn("keepawake_client.py")
        self.wait_for(client, "active=True")
        self.wait_for(fake, "inhibit")
        client.send_signal(signal.SIGKILL)
        self.wait_for(fake, "client gone")

    def test_sigterm_gives_the_lock_back(self):
        fake = self.fake("session")
        client = self.spawn("keepawake_client.py")
        self.wait_for(client, "active=True")
        self.wait_for(fake, "inhibit")
        client.send_signal(signal.SIGTERM)
        self.wait_for(fake, "uninhibit")

    def test_the_timer_switches_it_off(self):
        self.fake("session")
        client = self.spawn("keepawake_client.py", "0.03")                       # 1.8 seconds
        self.wait_for(client, "active=True")
        started = time.time()
        self.wait_for(client, "active=False", timeout=10)
        self.assertGreater(time.time() - started, 0.5)

    # ---- the fall-backs ------------------------------------------------------------------------------------
    def test_screensaver_is_the_second_choice(self):
        fake = self.fake("screensaver")                                          # no session manager at all
        client = self.spawn("keepawake_client.py")
        self.wait_for(client, "active=True backend=screensaver")
        self.wait_for(fake, "inhibit")
        client.send_signal(signal.SIGKILL)
        self.wait_for(fake, "client gone")

    def test_systemd_inhibit_is_the_last_resort_and_ends_with_the_client(self):
        bindir = Path(self.tmp) / "bin"
        bindir.mkdir()
        log = Path(self.tmp) / "sd.log"
        script = bindir / "systemd-inhibit"
        script.write_text(f'#!/bin/sh\necho started >> {log}\nwhile case "$1" in --*) true;; *) false;; esac; do shift; done\n'
                          f'"$@"\necho ended >> {log}\n')
        script.chmod(script.stat().st_mode | stat.S_IEXEC)
        env = dict(self.env, PATH=f"{bindir}:{os.environ['PATH']}")
        client = self.spawn("keepawake_client.py", env=env)                      # no session manager, no screen saver
        self.wait_for(client, "active=True backend=systemd")
        self.assertEqual(log.read_text().split(), ["started"])
        client.send_signal(signal.SIGKILL)
        end = time.time() + 5
        while time.time() < end and "ended" not in log.read_text():
            time.sleep(0.1)
        self.assertEqual(log.read_text().split(), ["started", "ended"])           # the lock did not outlive the island

    def test_nothing_works_is_reported_not_crashed(self):
        env = dict(self.env, PATH="/nonexistent")
        client = self.spawn("keepawake_client.py", env=env)
        self.wait_for(client, "failed=True")


if __name__ == "__main__":
    unittest.main()
