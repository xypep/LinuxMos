"""Which monitor the island sits on (config "monitor").

  "primary"   the primary monitor (default)
  "pointer"   the monitor under the mouse whenever a hotkey or the tray opens the island
  0, 1, ...   a monitor by number, counted from the left (0 = leftmost)
  "HDMI-1"    a monitor by its connector name, as xrandr shows it

A monitor that is not connected falls back to the primary one. The setting
stays as it is, so the island goes back when the monitor is plugged in again.
Nothing here polls: the island re-places itself on GDK's monitors-changed.
"""

try:
    from gi.repository import GdkX11
except ImportError:
    GdkX11 = None

PRIMARY, POINTER = "primary", "pointer"
# Cinnamon's panel height if panels-height has no entry for the panel
CINNAMON_PANEL_H = 40


def all_monitors(display):
    return [display.get_monitor(i) for i in range(display.get_n_monitors())]


def ordered(display):
    """Monitors from left to right (then top to bottom): the numbering of the config."""
    def key(monitor):
        g = monitor.get_geometry()
        return g.x, g.y

    return sorted(all_monitors(display), key=key)


def name(monitor):
    """Connector name (HDMI-1, eDP-1, DP-2): GTK's X11 backend reports it as the model."""
    return monitor.get_model() or ""


def primary(display):
    return display.get_primary_monitor() or display.get_monitor(0)


def at_pointer(display):
    seat = display.get_default_seat()
    pointer = seat.get_pointer() if seat else None
    if pointer is None:
        return None
    _screen, x, y = pointer.get_position()
    return display.get_monitor_at_point(x, y)


def index_of(choice):
    """Monitor number from the config (int or "1"), else None. True/False are no numbers."""
    if isinstance(choice, bool):
        return None
    if isinstance(choice, int):
        return choice
    if isinstance(choice, str) and choice.strip().isdigit():
        return int(choice)
    return None


def find(display, choice):
    """The monitor a number or name stands for, or None (not connected, primary, pointer)."""
    monitors = ordered(display)
    index = index_of(choice)
    if index is not None:
        return monitors[index] if 0 <= index < len(monitors) else None
    if isinstance(choice, str) and choice not in (PRIMARY, POINTER):
        wanted = choice.strip().lower()
        for monitor in monitors:
            if name(monitor).lower() == wanted:
                return monitor
    return None


def key(display, monitor):
    """What the tray stores for a monitor: its name (stays right when others are plugged in), else its number."""
    return name(monitor) or ordered(display).index(monitor)


def describe(monitor):
    g = monitor.get_geometry()
    return f"{name(monitor) or '?'} · {g.width}×{g.height}"


def _cinnamon_order(display):
    """Monitors in Muffin's numbering (the one Cinnamon's panel settings use): RandR output order.

    Output IDs are handed out in that order; GDK itself lists the primary monitor first.
    """
    def output(monitor):
        try:
            return GdkX11.X11Monitor.get_output(monitor)
        except (AttributeError, TypeError):
            return 0

    monitors = all_monitors(display)
    if GdkX11 is None or not all(output(m) for m in monitors):
        return monitors
    return sorted(monitors, key=output)


def _entries(settings, key):
    """Cinnamon's per-panel lists ("1:40", "1:0:top") -> {panel id: rest}."""
    result = {}
    for entry in settings.get_strv(key):
        panel, _sep, rest = entry.partition(":")
        if rest:
            result[panel] = rest
    return result


def cinnamon_top_panel(display, monitor, settings):
    """Height of a Cinnamon panel at the top of this monitor (0 if none or it hides itself).

    Fallback for a work area that misses the panel on a second monitor.
    """
    if settings is None:
        return 0
    keys = settings.props.settings_schema.list_keys()
    if "panels-enabled" not in keys:
        return 0
    try:
        number = _cinnamon_order(display).index(monitor)
    except ValueError:
        return 0
    heights = _entries(settings, "panels-height") if "panels-height" in keys else {}
    autohide = _entries(settings, "panels-autohide") if "panels-autohide" in keys else {}
    best = 0
    for panel, rest in _entries(settings, "panels-enabled").items():
        mon, _sep, position = rest.partition(":")
        if position != "top" or not mon.isdigit() or int(mon) != number:
            continue
        if autohide.get(panel, "false") != "false":
            continue  # hides itself (true) or gets out of the way (intel): reserves no space
        try:
            height = int(heights.get(panel, CINNAMON_PANEL_H))
        except ValueError:
            height = CINNAMON_PANEL_H
        best = max(best, height)
    return best


def top_of(display, monitor, panel_settings=None):
    """(x, width, y) of the usable top edge: the work area, the Cinnamon panel as a fallback."""
    geometry, area = monitor.get_geometry(), monitor.get_workarea()
    top = area.y
    if area.y == geometry.y and not monitor.is_primary():
        # Without per-monitor work areas (_GTK_WORKAREAS) GTK only knows the primary monitor's
        top = geometry.y + cinnamon_top_panel(display, monitor, panel_settings)
    return area.x, area.width, top
