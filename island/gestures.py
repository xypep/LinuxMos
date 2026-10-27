"""Mouse gestures on the folded pill: which gesture is which, and what each one does. No GTK in here.

The window feeds its scroll and click events to classify_*(); the result is a gesture id, config["gestures"]
maps it to an action id, and the window carries the action out. The defaults reproduce what the island did
before gestures were configurable: the wheel changes the volume by 5 %, a click with the middle or right
button opens the island like the left one.

Everything is event handling – no timer, nothing that runs while the pill is left alone. With
`gestures_enabled` off the window doesn't even connect the handlers (log: `gestures: disabled, no handlers`).
"""

# The island's tabs (name, German label), in the order of the tab bar – what "open tab X" can point to
TABS = (("search", "Suche"), ("home", "Jetzt"), ("clipboard", "Zwischenablage"), ("shelf", "Ablage"),
        ("todo", "Aufgaben"), ("note", "Notiz & Fokus"), ("chat", "KI-Chat"), ("water", "Wasser"),
        ("stretch", "Dehnen"), ("weather", "Wetter"), ("controls", "Steuerung"), ("tools", "Werkzeuge"))

# gesture id -> (label, kind, default action). kind: wheel | click
GESTURES = {
    "wheel": ("Mausrad auf der Pille", "wheel", "volume_wheel"),
    "wheel_shift": ("Mausrad mit Umschalt", "wheel", "default"),
    "wheel_ctrl": ("Mausrad mit Strg", "wheel", "default"),
    "wheel_left": ("Mausrad am linken Rand", "wheel", "default"),
    "wheel_right": ("Mausrad am rechten Rand", "wheel", "default"),
    "click_middle": ("Mittelklick", "click", "expand"),
    "click_right": ("Rechtsklick", "click", "expand"),
    "click_double": ("Doppelklick", "click", "none"),
}

# action id -> (label, kinds it fits). A wheel action reads the direction; "default" = "as the plain wheel"
ACTIONS = {
    "none": ("Nichts", ("wheel", "click")),
    "default": ("Wie das normale Mausrad", ("wheel",)),
    "expand": ("Insel aufklappen", ("wheel", "click")),
    "volume_wheel": ("Lautstärke ± (Mausrad)", ("wheel",)),
    "volume_up": ("Lauter", ("click",)),
    "volume_down": ("Leiser", ("click",)),
    "brightness_wheel": ("Helligkeit ± (Mausrad)", ("wheel",)),
    "brightness_up": ("Heller", ("click",)),
    "brightness_down": ("Dunkler", ("click",)),
    "tab_wheel": ("Tab wechseln (Mausrad)", ("wheel",)),
    "tab_next": ("Nächster Tab", ("click",)),
    "tab_prev": ("Vorheriger Tab", ("click",)),
    "play_pause": ("Play/Pause", ("wheel", "click")),
    "track_wheel": ("Titel wechseln (Mausrad)", ("wheel",)),
    "track_next": ("Nächster Titel", ("click",)),
    "track_prev": ("Vorheriger Titel", ("click",)),
    "settings": ("Einstellungen öffnen", ("wheel", "click")),
}
TAB_PREFIX, FUNCTION_PREFIX = "tab:", "function:"
VOLUME_STEP = 5
BRIGHTNESS_STEP = 5
# The outer part of the pill that counts as its edge for the wheel (a fraction of the width, at least in px)
EDGE_FRACTION, EDGE_MIN_PX = 0.2, 28

SHIFT, CTRL = 1 << 0, 1 << 2      # Gdk.ModifierType.SHIFT_MASK / CONTROL_MASK


def kind_of(gesture):
    return GESTURES[gesture][1]


def valid_action(gesture, action, tabs=(), function_ids=()):
    """Is `action` a choice for this gesture? Tab and function actions carry their target after a colon."""
    if not isinstance(action, str):
        return False
    kind = kind_of(gesture)
    if action in ACTIONS:
        return kind in ACTIONS[action][1] and not (action == "default" and gesture == "wheel")
    if action.startswith(TAB_PREFIX):
        return action[len(TAB_PREFIX):] in tabs
    if action.startswith(FUNCTION_PREFIX):
        return action[len(FUNCTION_PREFIX):] in function_ids
    return False


def resolve(section, tabs=(), function_ids=()):
    """{gesture: action} from the config's "gestures" section; a missing or unusable entry gets its default."""
    section = section if isinstance(section, dict) else {}
    result = {}
    for gesture, (_label, _kind, default) in GESTURES.items():
        value = section.get(gesture)
        result[gesture] = value if valid_action(gesture, value, tabs, function_ids) else default
    return result


def action_for(gesture, mapping):
    """The action to run for a gesture ("default" falls back to the plain wheel's)."""
    action = mapping.get(gesture, GESTURES[gesture][2])
    if action == "default":
        action = mapping.get("wheel", GESTURES["wheel"][2])
    return action


def classify_wheel(state, x, width):
    """Which wheel gesture is this? state: Gdk modifier mask; x: pointer in the pill, width: the pill's width."""
    if state & SHIFT:
        return "wheel_shift"
    if state & CTRL:
        return "wheel_ctrl"
    edge = max(EDGE_MIN_PX, width * EDGE_FRACTION)
    if width > 2 * edge:
        if x < edge:
            return "wheel_left"
        if x > width - edge:
            return "wheel_right"
    return "wheel"


def classify_click(button):
    """1 = left (always opens the island, not a gesture), 2 = middle, 3 = right."""
    return {2: "click_middle", 3: "click_right"}.get(button)


def next_in(items, current, step):
    """The item `step` places after `current` in a list, wrapping around (current not in the list: the first)."""
    if not items:
        return None
    if current not in items:
        return items[0]
    return items[(items.index(current) + step) % len(items)]


class Scroll:
    """Smooth-scrolling mice send many tiny deltas: collect them until one whole step has gathered."""

    def __init__(self):
        self.acc = 0.0

    def add(self, delta):
        """Returns +1 / -1 (up / down) when a step is complete, else 0. delta > 0 = scrolled down."""
        self.acc += delta
        if abs(self.acc) >= 1:
            step = -1 if self.acc > 0 else 1
            self.acc = 0.0
            return step
        return 0
