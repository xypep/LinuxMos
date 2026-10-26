"""System controls: Wi-Fi, Bluetooth, sound, brightness, theme, power actions.

Every external command runs asynchronously through Gio.Subprocess, so the
island never blocks while nmcli or bluetoothctl take their time.
"""

import re
from pathlib import Path

from gi.repository import Gio, GLib

THEME_DIRS = [Path.home() / ".themes", Path.home() / ".local/share/themes", Path("/usr/share/themes")]
ICON_DIRS = [Path.home() / ".icons", Path.home() / ".local/share/icons", Path("/usr/share/icons")]


def has(program):
    return GLib.find_program_in_path(program) is not None


def run(argv, callback=None):
    """Run a command without blocking; callback(ok, stdout) on the main loop."""
    try:
        proc = Gio.Subprocess.new(argv, Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_SILENCE)
    except GLib.Error:
        if callback:
            callback(False, "")
        return

    def done(p, result):
        try:
            _ok, out, _err = p.communicate_utf8_finish(result)
        except GLib.Error:
            out = ""
        if callback:
            callback(p.get_successful(), out or "")

    proc.communicate_utf8_async(None, None, done)


def settings(schema):
    """Gio.Settings for a schema, or None if it is not installed."""
    source = Gio.SettingsSchemaSource.get_default()
    if source and source.lookup(schema, True):
        return Gio.Settings.new(schema)
    return None


# ---- Wi-Fi / Bluetooth ------------------------------------------------------
def wifi_get(callback):
    if not has("nmcli"):
        callback(None)
        return
    run(["nmcli", "-t", "radio", "wifi"], lambda ok, out: callback(out.strip() == "enabled" if ok else None))


def wifi_set(enabled, callback=None):
    run(["nmcli", "radio", "wifi", "on" if enabled else "off"], callback and (lambda ok, _: callback(ok)))


def bluetooth_get(callback):
    if not has("bluetoothctl"):
        callback(None)
        return

    def parse(ok, out):
        if not ok or "Controller" not in out:
            callback(None)  # no adapter
        else:
            callback(bool(re.search(r"Powered:\s*yes", out)))

    run(["bluetoothctl", "show"], parse)


def bluetooth_set(enabled, callback=None):
    run(["bluetoothctl", "power", "on" if enabled else "off"], callback and (lambda ok, _: callback(ok)))


# ---- Sound ------------------------------------------------------------------
def volume_get(callback):
    def parse(ok, out):
        match = re.search(r"(\d+)%", out) if ok else None
        callback(int(match.group(1)) if match else None)

    run(["pactl", "get-sink-volume", "@DEFAULT_SINK@"], parse)


def volume_set(percent, callback=None):
    percent = max(0, min(100, int(percent)))
    run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{percent}%"],
        callback and (lambda ok, _: callback(percent if ok else None)))


def volume_step(delta, callback):
    """Change the volume relative to now, capped at 100 %."""
    volume_get(lambda current: volume_set(current + delta, callback) if current is not None else callback(None))


def mic_muted_get(callback):
    run(["pactl", "get-source-mute", "@DEFAULT_SOURCE@"],
        lambda ok, out: callback("yes" in out if ok else None))


def mic_mute_set(muted, callback=None):
    run(["pactl", "set-source-mute", "@DEFAULT_SOURCE@", "1" if muted else "0"],
        callback and (lambda ok, _: callback(ok)))


# ---- Brightness (Cinnamon settings daemon, laptops only) --------------------
_POWER = ("org.cinnamon.SettingsDaemon.Power", "/org/cinnamon/SettingsDaemon/Power",
          "org.cinnamon.SettingsDaemon.Power.Screen")


def brightness_get(callback):
    def done(bus, result):
        try:
            callback(int(bus.call_finish(result).unpack()[0]))
        except GLib.Error:
            callback(None)

    Gio.bus_get_sync(Gio.BusType.SESSION, None).call(
        *_POWER, "GetPercentage", None, GLib.VariantType("(u)"), Gio.DBusCallFlags.NONE, 1000, None, done)


def brightness_set(percent):
    Gio.bus_get_sync(Gio.BusType.SESSION, None).call(
        *_POWER, "SetPercentage", GLib.Variant("(u)", (max(1, min(100, int(percent))),)),
        None, Gio.DBusCallFlags.NONE, 1000, None, None)


# ---- Notifications / theme --------------------------------------------------
def dnd_get():
    s = settings("org.cinnamon.desktop.notifications")
    return None if s is None else not s.get_boolean("display-notifications")


def dnd_set(enabled):
    s = settings("org.cinnamon.desktop.notifications")
    if s:
        s.set_boolean("display-notifications", not enabled)


def dark_get():
    portal = settings("org.x.apps.portal")
    if portal and portal.get_string("color-scheme") in ("prefer-dark", "prefer-light"):
        return portal.get_string("color-scheme") == "prefer-dark"
    iface = settings("org.cinnamon.desktop.interface")
    return bool(iface and "dark" in iface.get_string("gtk-theme").lower())


def _swap_variant(name, dark):
    """WhiteSur-Light <-> WhiteSur-Dark (also for lowercase icon theme names)."""
    pairs = [("-Light", "-Dark"), ("-light", "-dark")]
    for light, dark_suffix in pairs:
        old, new = (light, dark_suffix) if dark else (dark_suffix, light)
        if old in name:
            return name.replace(old, new)
    return None


def _exists(name, dirs):
    return any((d / name).is_dir() for d in dirs)


def dark_set(dark):
    """Switch LinuxMos (WhiteSur) between dark and light, plus the app color scheme."""
    targets = [
        ("org.cinnamon.desktop.interface", "gtk-theme", THEME_DIRS),
        ("org.cinnamon.desktop.wm.preferences", "theme", THEME_DIRS),
        ("org.cinnamon.theme", "name", THEME_DIRS),
        ("org.cinnamon.desktop.interface", "icon-theme", ICON_DIRS),
    ]
    for schema, key, dirs in targets:
        s = settings(schema)
        if not s:
            continue
        new = _swap_variant(s.get_string(key), dark)
        if new and _exists(new, dirs):
            s.set_string(key, new)
    scheme = "prefer-dark" if dark else "prefer-light"
    for schema in ("org.x.apps.portal", "org.gnome.desktop.interface"):
        s = settings(schema)
        if s and "color-scheme" in s.props.settings_schema.list_keys():
            s.set_string("color-scheme", scheme)


# ---- Power / tools ----------------------------------------------------------
def lock():
    run(["cinnamon-screensaver-command", "--lock"])


def suspend():
    run(["systemctl", "suspend"])


def reboot():
    run(["systemctl", "reboot"])


def poweroff():
    run(["systemctl", "poweroff"])


def screenshot_area():
    """Area screenshot straight to the clipboard."""
    if has("gnome-screenshot"):
        run(["gnome-screenshot", "--area", "--clipboard"])
        return True
    return False


def play_sound():
    for argv in (["canberra-gtk-play", "-i", "complete"],
                 ["paplay", "/usr/share/sounds/freedesktop/stereo/complete.oga"]):
        if has(argv[0]):
            run(argv)
            return


def notify(title, body=""):
    if has("notify-send"):
        run(["notify-send", "-a", "MosIsland", "-i", "alarm-symbolic", title, body])
