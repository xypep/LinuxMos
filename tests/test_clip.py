"""Clip transfer: the receiving side, names, limits, the command check, peers, the CLI and a real ssh loop.

Needs only Python for most tests. The loopback test starts an sshd of its own on 127.0.0.1 and is skipped
where ssh, ssh-keygen or sshd are missing.
"""

import io
import json
import os
import shutil
import signal
import socket
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

from tests import _sandbox  # noqa: F401  (must come first)
from island import storage
from island.services import clipcore as core

ROOT = Path(__file__).resolve().parent.parent
CLI = ROOT / "bin" / "linuxmos-clip"
PNG = b"\x89PNG\r\n\x1a\n" + b"\0" * 64
LIMITS = core.Limits(text=2048, image=4096, file=8192, quota=200_000, keep_days=7)


class Folders(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="clip-test-"))
        self.addCleanup(shutil.rmtree, self.root, True)
        self.paths = core.Paths(self.root / "inbox", self.root / "Downloads")

    def receive(self, kind, data, name=None, limits=LIMITS, **kwargs):
        return core.receive(io.BytesIO(data), kind, name, self.paths, limits, sender="10.0.0.5", **kwargs)

    def code_of(self, kind, data, name=None, limits=LIMITS):
        with self.assertRaises(core.ClipError) as caught:
            self.receive(kind, data, name, limits)
        return caught.exception.code

    def everything(self):
        found = []
        for folder in (self.paths.inbox, self.paths.files):
            if folder.exists():
                found += [str(p.relative_to(self.root)) for p in folder.iterdir()]
        return sorted(found)


class FileNames(unittest.TestCase):
    def test_paths_dots_and_controls_are_removed(self):
        cases = {"../x": "x", "../../etc/passwd": "passwd", ".hidden": "hidden", "..": "datei", "...": "datei",
                 "a\x01b\x7f.txt": "a_b_.txt", "C:\\dir\\win.txt": "win.txt", "dir/sub/file.tar.gz": "file.tar.gz",
                 "  spaced name .pdf ": "spaced name .pdf", "a..b": "a.b", "": "datei", None: "datei",
                 "evil\u202egpj.exe": "evil_gpj.exe", "x/": "datei"}
        for given, expected in cases.items():
            self.assertEqual(core.sanitize_name(given), expected, repr(given))

    def test_long_names_are_cut_but_keep_the_extension(self):
        name = core.sanitize_name("n" * 500 + ".pdf")
        self.assertTrue(name.endswith(".pdf"))
        self.assertLessEqual(len(name.encode()), 200)
        wide = core.sanitize_name("ä" * 300 + ".txt")          # two bytes each
        self.assertLessEqual(len(wide.encode()), 200)


class Receiving(Folders):
    def test_text_is_stored_with_its_entry_and_private_rights(self):
        entry = self.receive("text", "Grüße\r\nZeile\r\n".encode())
        self.assertEqual(core.read_text(entry, self.paths), "Grüße\nZeile")
        self.assertEqual((entry["type"], entry["chars"], entry["sender"]), ("text", 11, "10.0.0.5"))
        self.assertEqual(stat.S_IMODE(self.paths.inbox.stat().st_mode), 0o700)
        for path in self.paths.inbox.iterdir():
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600, path.name)
        self.assertEqual([e["id"] for e in core.list_entries(self.paths)], [entry["id"]])

    def test_empty_and_binary_text_is_refused(self):
        for data in (b"", b"  \n ", b"\xff\xfe\x00bad"):
            self.assertEqual(self.code_of("text", data), core.EXIT_BAD_CONTENT, data)
        self.assertEqual(self.everything(), [])

    def test_images_are_recognised_by_their_first_bytes(self):
        entry = self.receive("image", PNG)
        self.assertTrue(entry["payload"].endswith(".png"))
        self.assertTrue(self.receive("image", b"\xff\xd8\xff\xe0" + b"0" * 20)["payload"].endswith(".jpg"))
        self.assertTrue(self.receive("image", b"RIFF\x00\x00\x00\x00WEBPVP8 ")["payload"].endswith(".webp"))
        self.assertEqual(self.code_of("image", b"<html>not an image</html>"), core.EXIT_BAD_CONTENT)
        self.assertEqual(self.code_of("image", b""), core.EXIT_BAD_CONTENT)

    def test_a_file_lands_in_downloads_and_the_entry_points_to_it(self):
        entry = self.receive("file", b"abc", "report.pdf")
        saved = Path(entry["path"])
        self.assertEqual((saved.parent, saved.name, saved.read_bytes()), (self.paths.files, "report.pdf", b"abc"))
        self.assertEqual(stat.S_IMODE(saved.stat().st_mode), 0o600)
        self.assertEqual(core.payload_path(core.list_entries(self.paths)[0], self.paths), saved)

    def test_over_the_limit_is_aborted_and_nothing_is_left(self):
        self.assertEqual(self.code_of("text", b"x" * (LIMITS.text + 1)), core.EXIT_TOO_LARGE)
        self.assertEqual(self.code_of("image", PNG + b"y" * LIMITS.image), core.EXIT_TOO_LARGE)
        self.assertEqual(self.code_of("file", b"z" * (LIMITS.file + 1), "big.bin"), core.EXIT_TOO_LARGE)
        self.assertEqual(self.everything(), [])
        # exactly the limit is fine
        self.assertEqual(self.receive("file", b"z" * LIMITS.file, "ok.bin")["size"], LIMITS.file)

    def test_the_limit_is_enforced_while_reading_not_after(self):
        class Endless(io.RawIOBase):
            served = 0

            def readable(self):
                return True

            def read(self, n=-1):
                self.served += n
                return b"x" * n

        stream = Endless()
        with self.assertRaises(core.ClipError):
            core.receive(stream, "file", "endless.bin", self.paths, LIMITS)
        self.assertLessEqual(stream.served, LIMITS.file + 2 * core.CHUNK)    # stopped right after the limit
        self.assertEqual(self.everything(), [])

    def test_a_broken_stream_leaves_no_half_file(self):
        class Dies(io.RawIOBase):
            first = True

            def readable(self):
                return True

            def read(self, n=-1):
                if self.first:
                    self.first = False
                    return PNG        # a valid start for every kind
                raise ConnectionResetError("the sender went away")

        for kind in core.KINDS:
            with self.assertRaises(ConnectionResetError):
                core.receive(Dies(), kind, "half.bin", self.paths, LIMITS)
        self.assertEqual(self.everything(), [])

    def test_collisions_get_a_number_and_symlinks_are_not_followed(self):
        self.paths.files.mkdir(parents=True)
        outside = self.root / "outside.txt"
        (self.paths.files / "ln.txt").symlink_to(outside)
        (self.paths.files / "taken.txt").write_text("mine")
        names = [self.receive("file", b"data", given)["name"] for given in ("ln.txt", "ln.txt", "taken.txt", "taken.txt")]
        self.assertEqual(names, ["ln (1).txt", "ln (2).txt", "taken (1).txt", "taken (2).txt"])
        self.assertFalse(outside.exists())
        self.assertEqual((self.paths.files / "taken.txt").read_text(), "mine")

    def test_evil_names_stay_inside_the_folder(self):
        for given in ("../x", "../../.ssh/authorized_keys", ".bashrc", "/etc/passwd", "a\nb", "x" * 400):
            entry = self.receive("file", b"data", given)
            self.assertEqual(Path(entry["path"]).parent, self.paths.files, given)
            self.assertFalse(Path(entry["name"]).name.startswith("."), given)
        self.assertEqual(sorted(p.name for p in self.root.iterdir()), ["Downloads", "inbox"])

    def test_the_quota_refuses_what_does_not_fit(self):
        small = core.Limits(text=2048, image=4096, file=8192, quota=1000, keep_days=7)
        self.assertEqual(self.code_of("text", b"q" * 1500, limits=small), core.EXIT_FULL)
        self.receive("text", b"a" * 600, limits=small)
        self.assertEqual(self.code_of("text", b"b" * 900, limits=small), core.EXIT_FULL)
        self.assertEqual(len(core.list_entries(self.paths)), 1)

    def test_received_files_count_against_the_quota_while_their_entry_exists(self):
        entry = self.receive("file", b"f" * 5000, "big.bin")
        self.assertGreaterEqual(core.usage(self.paths), 5000)
        core.remove_entry(entry, self.paths)
        self.assertLess(core.usage(self.paths), 1000)
        self.assertTrue(Path(entry["path"]).exists())      # the file itself stays: it is the user's now


class Inbox(Folders):
    def test_cleanup_drops_old_entries_and_stray_files_but_not_received_files(self):
        # receiving cleans up too (with its own clock), so the new one goes first and the old ones are "from the past"
        new = self.receive("text", b"new text")
        old = self.receive("text", b"old text", now=time.time() - 8 * 86400)
        old_file = self.receive("file", b"keep me", "keep.txt", now=time.time() - 9 * 86400)
        (self.paths.inbox / ".tmp-abc").write_text("half")
        (self.paths.inbox / "9999999999999-aaaaaa.txt").write_text("orphan")
        (self.paths.files / ".clip-tmp-zzz").write_text("half")
        past = time.time() - 7200
        for stray in (self.paths.inbox / ".tmp-abc", self.paths.inbox / "9999999999999-aaaaaa.txt",
                      self.paths.files / ".clip-tmp-zzz"):
            os.utime(stray, (past, past))
        (self.paths.inbox / ".tmp-fresh").write_text("being written right now")
        self.assertEqual(core.cleanup(self.paths, 7), 2)
        self.assertEqual([e["id"] for e in core.list_entries(self.paths)], [new["id"]])
        self.assertTrue(Path(old_file["path"]).exists())
        self.assertFalse((self.paths.inbox / old["payload"]).exists())
        self.assertFalse((self.paths.inbox / ".tmp-abc").exists())
        self.assertFalse((self.paths.inbox / "9999999999999-aaaaaa.txt").exists())
        self.assertFalse((self.paths.files / ".clip-tmp-zzz").exists())
        self.assertTrue((self.paths.inbox / ".tmp-fresh").exists())       # younger than an hour: maybe in use

    def test_entries_come_oldest_first_and_odd_files_are_skipped(self):
        first = self.receive("text", b"one", now=time.time() - 50)
        second = self.receive("text", b"two")
        (self.paths.inbox / "broken.json").write_text("{ nope")
        (self.paths.inbox / "1793000000000-abcdef.json").write_text(json.dumps({"id": "1793000000000-abcdef"}))
        bad = {"id": "1793000000001-abcdef", "type": "file", "size": 1, "time": 1, "sender": "",
               "path": "/etc/passwd"}
        (self.paths.inbox / "1793000000001-abcdef.json").write_text(json.dumps(bad))
        escape = {"id": "1793000000002-abcdef", "type": "text", "size": 1, "time": 1, "sender": "",
                  "payload": "../../etc/passwd"}
        (self.paths.inbox / "1793000000002-abcdef.json").write_text(json.dumps(escape))
        self.assertEqual([e["id"] for e in core.list_entries(self.paths)], [first["id"], second["id"]])

    def test_an_entry_exists_only_when_it_is_complete(self):
        """The entry file is renamed in last: until then the island has nothing to read."""
        seen = []
        original = core._write_json_private

        def spy(path, data):
            seen.append(core.list_entries(self.paths))      # payload is in place, the entry is not yet
            return original(path, data)

        core._write_json_private = spy
        try:
            self.receive("text", b"hello")
        finally:
            core._write_json_private = original
        self.assertEqual(seen, [[]])
        self.assertEqual(len(core.list_entries(self.paths)), 1)


class CommandCheck(unittest.TestCase):
    def test_only_the_exact_receive_command_passes(self):
        self.assertEqual(core.parse_command("linuxmos-clip receive --type text"), ("text", None))
        self.assertEqual(core.parse_command("linuxmos-clip receive --type file --name 'my file.pdf'"),
                         ("file", "my file.pdf"))
        self.assertEqual(core.parse_command("linuxmos-clip receive --type image --name pic.png"), ("image", "pic.png"))
        rejected = [None, "", "ls", "id", "/bin/sh", "linuxmos-clip", "linuxmos-clip receive",
                    "linuxmos-clip receive --type video", "linuxmos-clip receive --type text\n",
                    "linuxmos-clip receive --type text ", " linuxmos-clip receive --type text",
                    "linuxmos-clip receive --type file; id", "linuxmos-clip receive --type file && id",
                    "linuxmos-clip receive --type file | sh", "linuxmos-clip receive --type file `id`",
                    "linuxmos-clip receive --type file $(id)", "linuxmos-clip receive --type text --name '$(id)'",
                    "linuxmos-clip receive --type text --name a/b", "linuxmos-clip receive --type text --name ..\\x",
                    "linuxmos-clip receive --type text --name ''", "linuxmos-clip receive --type text --name 'a'; id",
                    "linuxmos-clip receive --type text --name " + "a" * 121,
                    "linuxmos-clip receive --type text --name 'a' --name 'b'",
                    "~/.local/bin/linuxmos-clip receive --type text", "linuxmos-clip send --peer x",
                    "linuxmos-clip receive --type text --name 'tab\there'", "linuxmos-clip receive  --type text"]
        for command in rejected:
            self.assertIsNone(core.parse_command(command), repr(command))


class Peers(unittest.TestCase):
    GOOD = {"name": "Windows-PC", "host": "192.168.0.50", "user": "alec", "port": 22,
            "key": "~/.ssh/linuxmos_clip_ed25519", "os": "windows"}

    def test_a_valid_peer_is_normalised(self):
        peer = core.valid_peer(self.GOOD)
        self.assertEqual((peer["name"], peer["port"], peer["os"]), ("Windows-PC", 22, "windows"))
        self.assertTrue(peer["key"].endswith("/.ssh/linuxmos_clip_ed25519") and "~" not in peer["key"])
        self.assertEqual(core.valid_peer({"name": "x", "host": "h", "user": "u"})["port"], 22)

    def test_nothing_that_could_become_an_ssh_option_gets_through(self):
        for change in ({"host": "-oProxyCommand=touch /tmp/pwned"}, {"host": "a b"}, {"host": "a;b"}, {"host": "a\n"},
                       {"user": "-oFoo"}, {"user": "a b"}, {"user": "x\n"}, {"port": 0}, {"port": 70000},
                       {"port": "22"}, {"port": True}, {"name": ""}, {"name": 5}, {"host": None}):
            self.assertIsNone(core.valid_peer(dict(self.GOOD, **change)), change)
        self.assertIsNone(core.valid_peer("Windows-PC"))

    def test_default_peer_and_names(self):
        second = dict(self.GOOD, name="Laptop", host="192.168.0.51")
        cfg = storage.Config(storage.DEFAULT_CONFIG)
        cfg["clip_peers"] = [self.GOOD, dict(self.GOOD), "junk", second]
        self.assertEqual([p["name"] for p in core.peers(cfg)], ["Windows-PC", "Laptop"])    # repeated name dropped
        self.assertIsNone(core.default_peer(cfg))                                            # two, none chosen
        cfg["clip_default_peer"] = "Laptop"
        self.assertEqual(core.default_peer(cfg)["host"], "192.168.0.51")
        cfg["clip_peers"] = [self.GOOD]
        cfg["clip_default_peer"] = ""
        self.assertEqual(core.default_peer(cfg)["name"], "Windows-PC")                       # the only one
        self.assertEqual(core.peer_label(cfg, "192.168.0.50"), "Windows-PC")
        self.assertEqual(core.peer_label(cfg, "10.9.9.9"), "10.9.9.9")
        self.assertEqual(core.peer_label(cfg, ""), "lokal")

    def test_the_ssh_call_has_the_safety_options_and_no_shell(self):
        peer = core.valid_peer(self.GOOD)
        argv = core.ssh_argv(peer, core.remote_command("file", "my file.pdf"))
        joined = " ".join(argv)
        for option in ("BatchMode=yes", "ConnectTimeout=5", "StrictHostKeyChecking=yes", "ControlMaster=no",
                       "IdentitiesOnly=yes"):
            self.assertIn(option, joined)
        self.assertNotIn("accept-new", joined)
        self.assertEqual(argv[-2:], ["alec@192.168.0.50", "linuxmos-clip receive --type file --name 'my file.pdf'"])
        self.assertEqual(core.parse_command(argv[-1]), ("file", "my file.pdf"))

    def test_remote_commands_always_pass_the_receivers_check(self):
        for name in ("a b.pdf", "../x", "ü.txt", "x'y.txt", "a;b", "$(id).txt", "n" * 300, ".hidden", "line\nbreak"):
            parsed = core.parse_command(core.remote_command("file", name))
            self.assertIsNotNone(parsed, repr(name))
            self.assertEqual(Path(parsed[1]).name, parsed[1])


class FailureTexts(unittest.TestCase):
    def reason(self, code, stderr=""):
        return core.explain_failure(code, stderr)[0]

    def test_ssh_failures_become_sentences(self):
        cases = [(255, "ssh: connect to host 10.0.0.1 port 22: Connection timed out", "nicht erreichbar"),
                 (255, "ssh: connect to host 10.0.0.1 port 22: Connection refused", "nicht erreichbar"),
                 (255, "ssh: Could not resolve hostname x: Name or service not known", "nicht erreichbar"),
                 (255, "u@h: Permission denied (publickey).", "Schlüssel abgelehnt"),
                 (255, "Host key verification failed.", "Host-Schlüssel unbekannt"),
                 (255, "@@@ WARNING: REMOTE HOST IDENTIFICATION HAS CHANGED! @@@\nHost key verification failed.",
                  "Host-Schlüssel geändert"),
                 (core.EXIT_TOO_LARGE, "", "zu groß"), (core.EXIT_DISABLED, "", "Empfang aus"),
                 (core.EXIT_FULL, "", "Eingang voll"), (127, "bash: linuxmos-clip: command not found", "linuxmos-clip fehlt")]
        for code, stderr, expected in cases:
            self.assertEqual(self.reason(code, stderr), expected, stderr)
        self.assertEqual(self.reason(42), "Fehler 42")


class ConfigKeys(unittest.TestCase):
    def setUp(self):
        self.path = storage.CONFIG_DIR / "config.json"
        self.path.unlink(missing_ok=True)

    def test_defaults_are_off_and_complete(self):
        cfg = storage.Config.load()
        self.assertEqual((cfg["clip_send_enabled"], cfg["clip_receive_enabled"]), (False, False))
        self.assertEqual((cfg["clip_max_text_kb"], cfg["clip_max_image_mb"], cfg["clip_max_file_mb"]), (1024, 20, 100))
        self.assertEqual((cfg["clip_inbox_keep_days"], cfg["clip_inbox_quota_mb"]), (7, 500))
        self.assertEqual((cfg["clip_default_peer"], cfg["clip_peers"]), ("", []))
        for forbidden in ("clip_auto_send", "clip_autoapply"):
            self.assertNotIn(forbidden, storage.DEFAULT_CONFIG)

    def test_an_old_file_keeps_the_users_values_and_gets_the_new_keys(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps({"city": "Köln", "clip_max_file_mb": 5, "future_key": [1]}))
        cfg = storage.Config.load()
        self.assertEqual((cfg["city"], cfg["clip_max_file_mb"], cfg["future_key"]), ("Köln", 5, [1]))
        self.assertFalse(cfg["clip_send_enabled"])
        self.assertTrue(cfg.fill_defaults())
        data = json.loads(self.path.read_text())
        self.assertEqual((data["clip_max_file_mb"], data["future_key"], data["clip_peers"]), (5, [1], []))

    def test_limits_follow_the_config_and_are_clamped(self):
        cfg = storage.Config(storage.DEFAULT_CONFIG)
        cfg.update(clip_max_text_kb=0, clip_max_image_mb="big", clip_max_file_mb=10 ** 9, clip_inbox_keep_days=-3)
        limits = core.Limits.from_config(cfg)
        self.assertEqual((limits.text, limits.image, limits.keep_days), (1024, 20 * 1024 * 1024, 1))
        self.assertEqual(limits.file, 8192 * 1024 * 1024)


class Cli(unittest.TestCase):
    """The real bin/linuxmos-clip in a throw-away home: what sshd would run for a sender."""

    def setUp(self):
        self.home = Path(tempfile.mkdtemp(prefix="clip-cli-"))
        self.addCleanup(shutil.rmtree, self.home, True)
        self.env = {"PATH": os.environ["PATH"], "HOME": str(self.home), "LANG": "C.UTF-8"}
        (self.home / ".config/linuxmos/island").mkdir(parents=True)
        self.inbox = self.home / ".local/share/linuxmos/island/clip-inbox"

    def config(self, **values):
        (self.home / ".config/linuxmos/island/config.json").write_text(json.dumps(values))

    def run_cli(self, *args, stdin=b"", extra=None):
        env = dict(self.env, **(extra or {}))
        return subprocess.run([sys.executable, str(CLI), *args], input=stdin, capture_output=True, env=env, timeout=60)

    def stored(self):
        return sorted(p.name for p in self.inbox.iterdir()) if self.inbox.exists() else []

    def test_selftest_passes(self):
        done = self.run_cli("--selftest")
        self.assertEqual(done.returncode, 0, done.stdout.decode())
        self.assertIn(b"Pr\xc3\xbcfungen bestanden", done.stdout)

    def test_receiving_is_refused_while_it_is_switched_off(self):
        done = self.run_cli("receive", "--type", "text", stdin=b"hello")
        self.assertEqual(done.returncode, core.EXIT_DISABLED)
        self.assertEqual(self.stored(), [])

    def test_receive_writes_an_entry_and_records_the_sender(self):
        self.config(clip_receive_enabled=True)
        done = self.run_cli("receive", "--type", "text", stdin=b"hello\r\n",
                            extra={"SSH_CONNECTION": "192.168.0.50 50222 192.168.0.9 22"})
        self.assertEqual(done.returncode, 0, done.stderr)
        entry = json.loads(next(self.inbox.glob("*.json")).read_text())
        self.assertEqual((entry["type"], entry["sender"], entry["chars"]), ("text", "192.168.0.50", 5))

    def test_the_receiver_enforces_its_own_limit(self):
        self.config(clip_receive_enabled=True, clip_max_text_kb=1, clip_max_file_mb=1)
        done = self.run_cli("receive", "--type", "text", stdin=b"x" * 5000)
        self.assertEqual(done.returncode, core.EXIT_TOO_LARGE)
        done = self.run_cli("receive", "--type", "file", "--name", "big.bin", stdin=b"x" * (2 * 1024 * 1024))
        self.assertEqual(done.returncode, core.EXIT_TOO_LARGE)
        self.assertEqual(self.stored(), [])
        self.assertEqual(list((self.home / "Downloads/LinuxMos").iterdir()), [])

    def test_receive_ssh_runs_nothing_but_a_clip(self):
        self.config(clip_receive_enabled=True)
        marker = self.home / "pwned"
        for command in ("ls", "id", f"linuxmos-clip receive --type file; touch {marker}",
                        f"linuxmos-clip receive --type text --name '$(touch {marker})'",
                        f"linuxmos-clip receive --type text && touch {marker}", "", None):
            extra = {"SSH_ORIGINAL_COMMAND": command} if command is not None else {}
            done = self.run_cli("receive-ssh", stdin=b"payload", extra=extra)
            self.assertEqual(done.returncode, core.EXIT_REJECTED, command)
        self.assertFalse(marker.exists())
        self.assertEqual(self.stored(), [])
        done = self.run_cli("receive-ssh", stdin=b"fine", extra={"SSH_ORIGINAL_COMMAND": "linuxmos-clip receive --type text"})
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(len([n for n in self.stored() if n.endswith(".json")]), 1)

    def test_authorized_keys_line_restricts_the_key(self):
        from island.clipcli import authorized_keys_line
        line = authorized_keys_line("ssh-ed25519 AAAAC3Nza comment")
        self.assertEqual(line, 'restrict,command="~/.local/bin/linuxmos-clip receive-ssh" ssh-ed25519 AAAAC3Nza comment')

    def test_a_clip_killed_while_receiving_leaves_nothing(self):
        self.config(clip_receive_enabled=True)
        proc = subprocess.Popen([sys.executable, str(CLI), "receive", "--type", "file", "--name", "x.bin"],
                                stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=self.env)
        try:
            proc.stdin.write(b"a" * 100_000)
            proc.stdin.flush()
            time.sleep(1.0)                  # it has a temporary file by now
            proc.send_signal(signal.SIGHUP)  # what sshd does when the connection drops
            proc.wait(timeout=10)
        finally:
            proc.stdin.close()
        self.assertEqual(self.stored(), [])
        folder = self.home / "Downloads/LinuxMos"
        self.assertEqual(list(folder.iterdir()) if folder.exists() else [], [])


def _free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@unittest.skipUnless(all(shutil.which(p) for p in ("ssh", "ssh-keygen")) and os.path.exists("/usr/sbin/sshd"),
                     "ssh and sshd are needed for the loopback test")
class SshLoopback(unittest.TestCase):
    """A real sshd on 127.0.0.1 with the restricted key line: what the island and the CLI really call."""

    @classmethod
    def setUpClass(cls):
        cls.dir = Path(tempfile.mkdtemp(prefix="clip-ssh-"))
        cls.home = cls.dir / "receiver"
        (cls.home / ".config/linuxmos/island").mkdir(parents=True)
        (cls.home / ".config/linuxmos/island/config.json").write_text(json.dumps({"clip_receive_enabled": True}))
        for name in ("hostkey", "client"):
            subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(cls.dir / name)], check=True)
        cls.port = _free_port()
        # The documented restricted line; env only points the receiver at the test's folders
        public = (cls.dir / "client.pub").read_text().strip()
        command = f"env HOME={cls.home} {sys.executable} {CLI} receive-ssh"
        (cls.dir / "authorized_keys").write_text(f'restrict,command="{command}" {public}\n')
        (cls.dir / "authorized_keys").chmod(0o600)
        (cls.dir / "sshd_config").write_text(
            f"Port {cls.port}\nListenAddress 127.0.0.1\nHostKey {cls.dir / 'hostkey'}\nPidFile {cls.dir / 'pid'}\n"
            f"AuthorizedKeysFile {cls.dir / 'authorized_keys'}\nPasswordAuthentication no\nKbdInteractiveAuthentication no\n"
            f"UsePAM no\nStrictModes no\nPermitRootLogin yes\nLogLevel ERROR\n")
        os.makedirs("/run/sshd", exist_ok=True) if os.geteuid() == 0 else None
        cls.sshd = subprocess.Popen(["/usr/sbin/sshd", "-D", "-e", "-f", str(cls.dir / "sshd_config")],
                                    stderr=subprocess.PIPE)
        for _attempt in range(50):
            try:
                socket.create_connection(("127.0.0.1", cls.port), timeout=0.2).close()
                break
            except OSError:
                time.sleep(0.1)
        else:
            cls.tearDownClass()
            raise unittest.SkipTest("sshd does not start here")
        hostkey = (cls.dir / "hostkey.pub").read_text().split()
        (cls.dir / "known_hosts").write_text(f"[127.0.0.1]:{cls.port} {hostkey[0]} {hostkey[1]}\n")
        cls.peer = {"name": "Loop", "host": "127.0.0.1", "user": os.environ.get("USER") or "root", "port": cls.port,
                    "key": str(cls.dir / "client"), "os": "linux"}
        try:
            cls.probe()
        except AssertionError:
            cls.tearDownClass()
            raise unittest.SkipTest("an unprivileged sshd cannot log in here")

    @classmethod
    def tearDownClass(cls):
        if getattr(cls, "sshd", None):
            cls.sshd.terminate()
            cls.sshd.wait(timeout=10)
            cls.sshd.stderr.close()
        shutil.rmtree(cls.dir, True)

    @classmethod
    def ssh(cls, command, stdin=b"", peer=None, known_hosts=None):
        argv = core.ssh_argv(peer or cls.peer, command)
        # the test's own known_hosts file instead of the user's; the production options stay untouched
        argv[1:1] = ["-o", f"UserKnownHostsFile={known_hosts or cls.dir / 'known_hosts'}", "-F", "/dev/null"]
        return subprocess.run(argv, input=stdin, capture_output=True, timeout=60)

    @classmethod
    def probe(cls):
        done = cls.ssh("linuxmos-clip receive --type text")
        assert done.returncode == core.EXIT_BAD_CONTENT, done.stderr

    def inbox(self):
        folder = self.home / ".local/share/linuxmos/island/clip-inbox"
        return sorted(folder.glob("*.json")) if folder.exists() else []

    def test_text_image_and_file_arrive(self):
        before = len(self.inbox())
        self.assertEqual(self.ssh(core.remote_command("text"), "Grüße über SSH".encode()).returncode, 0)
        self.assertEqual(self.ssh(core.remote_command("image"), PNG).returncode, 0)
        blob = os.urandom(300_000)
        self.assertEqual(self.ssh(core.remote_command("file", "Mein Bericht.pdf"), blob).returncode, 0)
        entries = self.inbox()
        self.assertEqual(len(entries), before + 3)
        saved = self.home / "Downloads/LinuxMos/Mein Bericht.pdf"
        self.assertEqual(saved.read_bytes(), blob)

    def test_the_key_can_do_nothing_but_deliver_clips(self):
        marker = self.dir / "pwned"
        for command in ("ls", f"touch {marker}", f"linuxmos-clip receive --type file; touch {marker}", "/bin/sh"):
            done = self.ssh(command, b"data")
            self.assertEqual(done.returncode, core.EXIT_REJECTED, command)
        self.assertFalse(marker.exists())
        # no shell at all (no command), no terminal, no forwarding
        argv = core.ssh_argv(self.peer, "x")[:-1]
        argv[1:1] = ["-o", f"UserKnownHostsFile={self.dir / 'known_hosts'}", "-F", "/dev/null"]
        self.assertEqual(subprocess.run(argv, input=b"", capture_output=True, timeout=60).returncode, core.EXIT_REJECTED)
        argv.remove("-T")        # ask for a terminal after all
        tty = subprocess.run(argv[:1] + ["-tt"] + argv[1:] + ["linuxmos-clip receive --type text"], input=b"",
                             capture_output=True, timeout=60)
        self.assertIn(b"PTY allocation request failed", tty.stderr)

    def test_the_receivers_limit_comes_back_as_too_large(self):
        config = self.home / ".config/linuxmos/island/config.json"
        config.write_text(json.dumps({"clip_receive_enabled": True, "clip_max_file_mb": 1}))
        try:
            done = self.ssh(core.remote_command("file", "big.bin"), os.urandom(2 * 1024 * 1024))
            self.assertEqual(done.returncode, core.EXIT_TOO_LARGE)
            self.assertEqual(core.explain_failure(done.returncode, done.stderr.decode())[0], "zu groß")
            self.assertFalse((self.home / "Downloads/LinuxMos/big.bin").exists())
            self.assertEqual([p.name for p in (self.home / "Downloads/LinuxMos").glob(".clip-tmp-*")], [])
        finally:
            config.write_text(json.dumps({"clip_receive_enabled": True}))

    def test_an_unknown_host_key_is_refused_not_accepted(self):
        empty = self.dir / "empty_known_hosts"
        empty.write_text("")
        done = self.ssh(core.remote_command("text"), b"hello", known_hosts=empty)
        self.assertEqual(done.returncode, 255)
        self.assertEqual(core.explain_failure(done.returncode, done.stderr.decode())[0], "Host-Schlüssel unbekannt")
        self.assertEqual(empty.read_text(), "")      # nothing was added behind the user's back

    def test_a_refused_key_and_a_dead_port_have_their_own_reasons(self):
        other = self.dir / "other"
        subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(other)], check=True)
        done = self.ssh(core.remote_command("text"), b"hi", peer=dict(self.peer, key=str(other)))
        self.assertEqual(core.explain_failure(done.returncode, done.stderr.decode())[0], "Schlüssel abgelehnt")
        done = self.ssh(core.remote_command("text"), b"hi", peer=dict(self.peer, port=_free_port()))
        self.assertEqual(core.explain_failure(done.returncode, done.stderr.decode())[0], "nicht erreichbar")

    def test_sending_from_the_cli_goes_through_the_same_call(self):
        sender = Path(tempfile.mkdtemp(prefix="clip-sender-"))
        self.addCleanup(shutil.rmtree, sender, True)
        (sender / ".config/linuxmos/island").mkdir(parents=True)
        key = sender / "key"
        shutil.copy(self.dir / "client", key)
        key.chmod(0o600)
        peer = dict(self.peer, key=str(key))
        (sender / ".config/linuxmos/island/config.json").write_text(
            json.dumps({"clip_send_enabled": True, "clip_peers": [peer], "clip_default_peer": "Loop"}))
        # ssh reads known_hosts from the user's real home: give the CLI an ssh that points at the test's file
        shim = sender / "bin"
        shim.mkdir()
        (shim / "ssh").write_text(f'#!/bin/sh\nexec {shutil.which("ssh")} -o UserKnownHostsFile={self.dir / "known_hosts"} -F /dev/null "$@"\n')
        (shim / "ssh").chmod(0o755)
        env = {"PATH": f"{shim}:{os.environ['PATH']}", "HOME": str(sender), "LANG": "C.UTF-8"}
        before = len(self.inbox())
        done = subprocess.run([sys.executable, str(CLI), "send", "--peer", "Loop"], input="per CLI gesendet".encode(),
                              capture_output=True, env=env, timeout=60)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn(b"Gesendet an Loop", done.stdout)
        self.assertEqual(len(self.inbox()), before + 1)
        # send switched off: nothing is sent
        (sender / ".config/linuxmos/island/config.json").write_text(json.dumps({"clip_peers": [peer]}))
        done = subprocess.run([sys.executable, str(CLI), "send", "--peer", "Loop"], input=b"nope", capture_output=True,
                              env=env, timeout=60)
        self.assertNotEqual(done.returncode, 0)
        self.assertEqual(len(self.inbox()), before + 1)


if __name__ == "__main__":
    unittest.main()
