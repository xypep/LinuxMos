"""Markup editor for screenshots: arrow, rectangle, marker, text and pixelate.

Imported only when a shot is opened for editing, so it costs nothing while
unused. Shapes are kept as data and rendered once at the image's own
resolution whenever they change; the canvas just shows that render scaled
to the window, plus the shape being drawn right now.
"""

import math
from pathlib import Path

import cairo
import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("PangoCairo", "1.0")
from gi.repository import Gdk, GLib, Gtk, Pango, PangoCairo  # noqa: E402

from island.i18n import _  # noqa: E402
from island.services import screenshot  # noqa: E402

# (tool, tooltip as German source string, key)
TOOLS = [
    ("arrow", "Pfeil (A)", Gdk.KEY_a),
    ("rect", "Rechteck (R)", Gdk.KEY_r),
    ("marker", "Marker (M)", Gdk.KEY_m),
    ("text", "Text (T)", Gdk.KEY_t),
    ("blur", "Verpixeln – für private Daten (B)", Gdk.KEY_b),
]
# Apple's dark-mode system colours, like the island
COLORS = [(1.0, 0.27, 0.23), (1.0, 0.84, 0.04), (0.19, 0.82, 0.35), (0.04, 0.52, 1.0), (1.0, 1.0, 1.0), (0.11, 0.11, 0.12)]
MARKER_ALPHA = 0.45
WINDOW_RADIUS = 22
IMAGE_RADIUS = 12
HEADER_H, TOOLBAR_H, PAD = 44, 82, 22
CONFIRM_MS = 3000


# ---- drawing ---------------------------------------------------------------------
def _rect(p0, p1):
    x0, y0 = p0
    x1, y1 = p1
    return min(x0, x1), min(y0, y1), abs(x1 - x0), abs(y1 - y0)


def _rounded_rect(cr, x, y, w, h, r):
    r = max(0.0, min(r, w / 2, h / 2))
    cr.new_sub_path()
    cr.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    cr.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    cr.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    cr.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
    cr.close_path()


def _arrow(cr, p0, p1, width):
    (x0, y0), (x1, y1) = p0, p1
    length = math.hypot(x1 - x0, y1 - y0)
    if length < 1:
        return
    ux, uy = (x1 - x0) / length, (y1 - y0) / length
    head = min(length, width * 5)
    # The shaft ends inside the head, so the round cap never pokes out of the tip
    cr.set_line_width(width)
    cr.set_line_cap(cairo.LINE_CAP_ROUND)
    cr.move_to(x0, y0)
    cr.line_to(x1 - ux * head * 0.7, y1 - uy * head * 0.7)
    cr.stroke()
    bx, by, half = x1 - ux * head, y1 - uy * head, head * 0.55
    cr.move_to(x1, y1)
    cr.line_to(bx - uy * half, by + ux * half)
    cr.line_to(bx + uy * half, by - ux * half)
    cr.close_path()
    cr.fill()


def _text_layout(cr, text, width):
    layout = PangoCairo.create_layout(cr)
    font = Pango.FontDescription.from_string("Sans Bold")
    font.set_absolute_size(width * 7 * Pango.SCALE)
    layout.set_font_description(font)
    layout.set_text(text, -1)
    return layout


def _luminance(color):
    r, g, b = color
    return 0.299 * r + 0.587 * g + 0.114 * b


def draw_shape(cr, shape, width):
    """Everything except pixelate, which works on the pixels below it (see pixelate())."""
    tool, color = shape["tool"], shape["color"]
    shadow = width * 0.35
    if tool in ("arrow", "rect"):
        for dx, rgba in ((shadow, (0, 0, 0, 0.3)), (0, (*color, 1))):
            cr.save()
            cr.translate(dx, dx)
            cr.set_source_rgba(*rgba)
            if tool == "arrow":
                _arrow(cr, shape["p0"], shape["p1"], width)
            else:
                cr.set_line_width(width)
                _rounded_rect(cr, *_rect(shape["p0"], shape["p1"]), width * 1.2)
                cr.stroke()
            cr.restore()
    elif tool == "marker":
        points = shape["points"]
        cr.save()
        # Multiply: like a real highlighter, the text below stays readable
        cr.set_operator(cairo.OPERATOR_MULTIPLY)
        cr.set_source_rgba(*color, MARKER_ALPHA)
        cr.set_line_width(width * 6)
        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        cr.set_line_join(cairo.LINE_JOIN_ROUND)
        cr.move_to(*points[0])
        for point in points[1:] or [(points[0][0] + 0.1, points[0][1])]:
            cr.line_to(*point)
        cr.stroke()
        cr.restore()
    elif tool == "text":
        layout = _text_layout(cr, shape["text"], width)
        _w, h = layout.get_pixel_size()
        x, y = shape["p0"]
        cr.save()
        cr.move_to(x, y - h / 2)  # the click marks the middle of the first line's left edge
        PangoCairo.layout_path(cr, layout)
        halo = (0, 0, 0, 0.6) if _luminance(color) > 0.6 else (1, 1, 1, 0.9)
        cr.set_source_rgba(*halo)
        cr.set_line_width(width * 1.2)
        cr.set_line_join(cairo.LINE_JOIN_ROUND)
        cr.stroke_preserve()
        cr.set_source_rgb(*color)
        cr.fill()
        cr.restore()
    elif tool == "blur":
        # Only the preview while dragging; the real thing is pixelate()
        cr.save()
        cr.rectangle(*_rect(shape["p0"], shape["p1"]))
        cr.set_source_rgba(0.5, 0.5, 0.5, 0.35)
        cr.fill_preserve()
        cr.set_source_rgba(1, 1, 1, 0.9)
        cr.set_line_width(max(1.0, width / 2))
        cr.set_dash([width * 2, width * 2])
        cr.stroke()
        cr.restore()


def pixelate(surface, x, y, w, h, block):
    """Coarse mosaic of a region. Unlike a soft blur, big blocks cannot be sharpened back into text."""
    x, y = int(x), int(y)
    w, h = int(math.ceil(w)), int(math.ceil(h))
    if w < 1 or h < 1:
        return
    sw, sh = max(1, math.ceil(w / block)), max(1, math.ceil(h / block))
    small = cairo.ImageSurface(cairo.FORMAT_ARGB32, sw, sh)
    cr = cairo.Context(small)
    cr.scale(sw / w, sh / h)
    cr.set_source_surface(surface, -x, -y)
    cr.get_source().set_filter(cairo.FILTER_GOOD)  # averages every block when shrinking
    cr.paint()
    cr = cairo.Context(surface)
    cr.rectangle(x, y, w, h)
    cr.clip()
    cr.translate(x, y)
    cr.scale(w / sw, h / sh)
    cr.set_source_surface(small, 0, 0)
    cr.get_source().set_filter(cairo.FILTER_NEAREST)
    cr.paint()


# ---- small widgets ----------------------------------------------------------------------
_css_screens = set()


def _load_css(screen):
    """Once per screen: the editor also runs without the island (and its style.css)."""
    if hash(screen) in _css_screens:
        return
    provider = Gtk.CssProvider()
    provider.load_from_path(str(Path(__file__).with_name("editor.css")))
    Gtk.StyleContext.add_provider_for_screen(screen, provider, Gtk.STYLE_PROVIDER_PRIORITY_USER + 1)
    _css_screens.add(hash(screen))


class _Glyph(Gtk.DrawingArea):
    """Toolbar icon drawn with cairo: crisp and the same with every icon theme."""

    def __init__(self, tool=None, color=None, size=20):
        super().__init__()
        self.tool, self.color = tool, color
        self.set_size_request(size, size)

    def do_draw(self, cr):
        s = min(self.get_allocated_width(), self.get_allocated_height())
        if self.color:
            parent = self.get_parent()
            chosen = isinstance(parent, Gtk.ToggleButton) and parent.get_active()
            # Chosen: a white ring with a gap around the dot (like iOS colour pickers)
            if chosen:
                cr.arc(s / 2, s / 2, s / 2 - 0.75, 0, 2 * math.pi)
                cr.set_source_rgba(1, 1, 1, 0.95)
                cr.set_line_width(1.5)
                cr.stroke()
            cr.arc(s / 2, s / 2, s / 2 - (4 if chosen else 2), 0, 2 * math.pi)
            cr.set_source_rgb(*self.color)
            cr.fill_preserve()
            cr.set_source_rgba(1, 1, 1, 0.18)
            cr.set_line_width(1)
            cr.stroke()
            return False
        cr.set_source_rgba(0.96, 0.96, 0.97, 1)
        p = s * 0.16
        if self.tool == "arrow":
            _arrow(cr, (p, s - p), (s - p, p), s * 0.1)
        elif self.tool == "rect":
            cr.set_line_width(s * 0.09)
            _rounded_rect(cr, p, p + s * 0.1, s - 2 * p, s - 2 * p - s * 0.2, s * 0.14)
            cr.stroke()
        elif self.tool == "marker":
            cr.set_line_width(s * 0.28)
            cr.set_line_cap(cairo.LINE_CAP_ROUND)
            cr.move_to(p + 1, s * 0.64)
            cr.curve_to(s * 0.4, s * 0.5, s * 0.6, s * 0.5, s - p - 1, s * 0.36)
            cr.push_group()
            cr.stroke()
            cr.pop_group_to_source()
            cr.paint_with_alpha(0.6)
        elif self.tool == "text":
            layout = PangoCairo.create_layout(cr)
            font = Pango.FontDescription.from_string("Inter, Sans Semi-Bold")
            font.set_absolute_size(s * 0.82 * Pango.SCALE)
            layout.set_font_description(font)
            layout.set_text("T", -1)
            _ink, logical = layout.get_pixel_extents()
            cr.move_to((s - logical.width) / 2, (s - logical.height) / 2)
            PangoCairo.show_layout(cr, layout)
        elif self.tool == "blur":
            cell = (s - 2 * p) / 3
            for i in range(3):
                for j in range(3):
                    _rounded_rect(cr, p + i * cell + 0.5, p + j * cell + 0.5, cell - 1, cell - 1, 1.2)
                    cr.save()
                    cr.clip()
                    cr.paint_with_alpha(0.95 if (i + j) % 2 == 0 else 0.35)
                    cr.restore()
                    cr.new_path()
        return False


def _radio(group, child, tooltip, css=None):
    btn = Gtk.RadioButton.new_from_widget(group)
    btn.set_mode(False)  # a toggle button, not a radio dot
    btn.set_can_focus(False)
    btn.add(child)
    btn.set_tooltip_text(tooltip)
    if css:
        btn.get_style_context().add_class(css)
    return btn


def _button(icon_name, tooltip, callback, text=None, css=None):
    btn = Gtk.Button()
    btn.set_can_focus(False)
    box = Gtk.Box(spacing=6)
    if icon_name:
        box.pack_start(Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.BUTTON), False, False, 0)
    if text:
        box.pack_start(Gtk.Label(label=text), False, False, 0)
    btn.add(box)
    btn.set_tooltip_text(tooltip)
    btn.connect("clicked", lambda *_: callback())
    if css:
        btn.get_style_context().add_class(css)
    return btn


def _separator():
    return Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)


# ---- the editor -------------------------------------------------------------------------
class Editor(Gtk.Window):
    """A black, borderless window in the island's style with a floating tool pill.

    on_saved(path) runs after "Done" wrote the file and put it on the clipboard.
    """

    def __init__(self, path, config, application=None, on_saved=None):
        super().__init__(application=application)
        self.path = Path(path)
        self.config = config
        self._on_saved = on_saved
        self._base = cairo.ImageSurface.create_from_png(str(self.path))
        self.iw, self.ih = self._base.get_width(), self._base.get_height()
        # Line width in image pixels: about 5 px on a 1080p shot, more on 4K
        self.unit = max(2.5, max(self.iw, self.ih) / 400)
        self.shapes = []
        self.current = None     # shape being drawn
        self.tool = "arrow"
        self.color = COLORS[0]
        self._dirty = False
        self._close_armed = 0   # timeout id while "click again to discard" shows
        self._toast_id = 0
        self._view = (1.0, 0.0, 0.0)  # scale, offset x, offset y
        self._render()

        self.set_name("mos-editor")
        self.set_title(_("Screenshot bearbeiten"))
        self.set_icon_name("camera-photo")
        self.set_decorated(False)
        self.set_app_paintable(True)
        visual = self.get_screen().get_rgba_visual()
        if visual:
            self.set_visual(visual)
        _load_css(self.get_screen())
        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        self.connect("draw", self._on_window_draw)
        self.connect("button-press-event", self._on_window_press)
        self.connect("key-press-event", self._on_key)
        self.connect("delete-event", lambda *_: not self._request_close())
        self._build()
        self._size_to_image()
        self.show_all()  # after the default size, or GTK maps it at its minimum size

    # ---- layout ------------------------------------------------------------------------
    def _build(self):
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        # Header: file name, a short status note, close
        header = Gtk.Box(spacing=8, margin_start=PAD, margin_end=12, margin_top=10)
        header.set_size_request(-1, HEADER_H - 10)
        name = Gtk.Label(label=self.path.name, xalign=0, ellipsize=Pango.EllipsizeMode.END)
        name.get_style_context().add_class("dim")
        self.toast = Gtk.Label(label="")
        self.toast.get_style_context().add_class("toast")
        self.close_label = Gtk.Label(label=_("Verwerfen?"), no_show_all=True)
        close_box = Gtk.Box(spacing=4)
        close_box.pack_start(Gtk.Image.new_from_icon_name("window-close-symbolic", Gtk.IconSize.BUTTON),
                             False, False, 0)
        close_box.pack_start(self.close_label, False, False, 0)
        self.close_button = Gtk.Button(can_focus=False, valign=Gtk.Align.CENTER)
        self.close_button.add(close_box)
        self.close_button.set_tooltip_text(_("Schließen (Esc)"))
        self.close_button.get_style_context().add_class("close")
        self.close_button.connect("clicked", lambda *_: self._request_close() and self.destroy())
        header.pack_start(name, True, True, 0)
        header.set_center_widget(self.toast)
        header.pack_end(self.close_button, False, False, 0)
        root.pack_start(header, False, False, 0)

        self.canvas = Gtk.DrawingArea(can_focus=True, vexpand=True, hexpand=True)
        # Motion only while a button is held: no events at all while just hovering
        self.canvas.add_events(Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.BUTTON_RELEASE_MASK
                               | Gdk.EventMask.BUTTON_MOTION_MASK)
        self.canvas.connect("draw", self._on_draw)
        self.canvas.connect("button-press-event", self._on_press)
        self.canvas.connect("motion-notify-event", self._on_motion)
        self.canvas.connect("button-release-event", self._on_release)
        self.canvas.connect("realize", lambda *_: self._update_cursor())
        root.pack_start(self.canvas, True, True, 0)

        # The floating pill: tools | colours | undo, copy, done
        pill = Gtk.Box(spacing=2, halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER,
                       margin_top=12, margin_bottom=18)
        pill.get_style_context().add_class("toolbar")
        self.tool_buttons = {}
        group = None
        for name_, tooltip, _key in TOOLS:
            btn = _radio(group, _Glyph(tool=name_), _(tooltip))
            group = group or btn
            btn.connect("toggled", lambda b, n=name_: b.get_active() and self._set_tool(n))
            pill.pack_start(btn, False, False, 0)
            self.tool_buttons[name_] = btn
        pill.pack_start(_separator(), False, False, 0)
        self.color_buttons = []
        group = None
        for i, color in enumerate(COLORS):
            btn = _radio(group, _Glyph(color=color, size=22), _("Farbe ({key})").format(key=i + 1), css="color")
            group = group or btn
            btn.connect("toggled", self._on_color_toggled, color)
            pill.pack_start(btn, False, False, 0)
            self.color_buttons.append(btn)
        pill.pack_start(_separator(), False, False, 0)
        self.undo_button = _button("edit-undo-symbolic", _("Rückgängig (Ctrl+Z)"), self.undo)
        self.undo_button.set_sensitive(False)
        pill.pack_start(self.undo_button, False, False, 0)
        pill.pack_start(_button("edit-copy-symbolic", _("In die Zwischenablage (Ctrl+C)"), self.copy), False, False, 0)
        pill.pack_start(_button(None, _("Speichern und kopieren (Ctrl+S)"), self.save, _("Fertig"), css="done"),
                        False, False, 0)
        root.pack_start(pill, False, False, 0)
        self.add(root)

        # Text tool: a small entry that pops up where the user clicked
        self.text_entry = Gtk.Entry(width_chars=22, placeholder_text=_("Text eingeben, Enter"))
        self.text_entry.connect("activate", self._commit_text)
        self.popover = Gtk.Popover(relative_to=self.canvas, modal=True)
        self.popover.get_style_context().add_class("mos-pop")
        self.popover.add(self.text_entry)
        self.text_entry.show()  # the window's show_all() does not reach into popovers
        self.popover.connect("closed", lambda *_: self._cancel_text())
        self._text_at = None

    def _size_to_image(self):
        display = Gdk.Display.get_default()
        _screen, x, y = display.get_default_seat().get_pointer().get_position()
        monitor = display.get_monitor_at_point(x, y) or display.get_primary_monitor() or display.get_monitor(0)
        area, scale = monitor.get_workarea(), monitor.get_scale_factor()
        chrome_h = HEADER_H + TOOLBAR_H + PAD
        fit = min(1 / scale, (area.width * 0.85 - 2 * PAD) / self.iw, (area.height * 0.85 - chrome_h) / self.ih)
        w = self.iw * fit + 2 * PAD
        h = self.ih * fit + chrome_h
        self.set_default_size(max(680, int(w)), max(360, int(h)))
        self.set_position(Gtk.WindowPosition.CENTER)

    def _on_window_draw(self, _widget, cr):
        """Rounded black body like the island; the corners stay transparent."""
        w, h = self.get_allocated_width(), self.get_allocated_height()
        cr.set_operator(cairo.OPERATOR_SOURCE)
        cr.set_source_rgba(0, 0, 0, 0)
        cr.paint()
        cr.set_operator(cairo.OPERATOR_OVER)
        _rounded_rect(cr, 0.5, 0.5, w - 1, h - 1, WINDOW_RADIUS)
        cr.set_source_rgba(0.04, 0.04, 0.05, 0.97)
        cr.fill_preserve()
        cr.set_source_rgba(1, 1, 1, 0.09)
        cr.set_line_width(1)
        cr.stroke()
        return False

    def _on_window_press(self, _w, event):
        # Borderless: drag the window by any free spot (the canvas keeps its own clicks)
        if event.button == 1 and event.type == Gdk.EventType.BUTTON_PRESS:
            self.begin_move_drag(event.button, int(event.x_root), int(event.y_root), event.time)
            return True
        return False

    # ---- state -------------------------------------------------------------------------
    def _set_tool(self, name):
        self.tool = name
        self._update_cursor()

    def _on_color_toggled(self, btn, color):
        if btn.get_active():
            self.color = color
        # The dots draw the ring themselves
        for b in self.color_buttons:
            b.queue_draw()

    def _update_cursor(self):
        win = self.canvas.get_window()
        if win:
            win.set_cursor(Gdk.Cursor.new_from_name(win.get_display(), "text" if self.tool == "text" else "crosshair"))

    def _show_toast(self, text):
        self.toast.set_text(text)
        if self._toast_id:
            GLib.source_remove(self._toast_id)

        def clear():
            self._toast_id = 0
            self.toast.set_text("")
            return GLib.SOURCE_REMOVE

        self._toast_id = GLib.timeout_add(1800, clear)

    def _render(self):
        """Bake all shapes into one image at full resolution (runs only when shapes change)."""
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, self.iw, self.ih)
        cr = cairo.Context(surface)
        cr.set_source_surface(self._base, 0, 0)
        cr.paint()
        for shape in self.shapes:
            if shape["tool"] == "blur":
                pixelate(surface, *_rect(shape["p0"], shape["p1"]), block=max(8, round(self.unit * 5)))
            else:
                draw_shape(cr, shape, self.unit)
        surface.flush()
        self._composite = surface

    def _add(self, shape):
        self.shapes.append(shape)
        self._changed()

    def undo(self):
        if self.shapes:
            self.shapes.pop()
            self._changed()

    def _changed(self):
        self._dirty = bool(self.shapes)
        self.undo_button.set_sensitive(bool(self.shapes))
        self._disarm_close()
        self._render()
        self.canvas.queue_draw()

    # ---- canvas ------------------------------------------------------------------------
    def _on_draw(self, widget, cr):
        aw, ah = widget.get_allocated_width(), widget.get_allocated_height()
        # Never upscale: on a HiDPI screen 1/scale shows the shot pixel for pixel
        s = min((aw - 2 * PAD) / self.iw, (ah - 8) / self.ih, 1 / widget.get_scale_factor())
        s = max(s, 0.01)
        dw, dh = self.iw * s, self.ih * s
        ox, oy = (aw - dw) / 2, (ah - dh) / 2
        self._view = (s, ox, oy)
        # Soft shadow below the shot
        for spread, alpha in ((14, 0.05), (9, 0.08), (5, 0.12), (2, 0.18)):
            _rounded_rect(cr, ox - spread, oy - spread + 4, dw + 2 * spread, dh + 2 * spread, IMAGE_RADIUS + spread)
            cr.set_source_rgba(0, 0, 0, alpha)
            cr.fill()
        cr.save()
        _rounded_rect(cr, ox, oy, dw, dh, IMAGE_RADIUS)
        cr.clip()
        cr.translate(ox, oy)
        cr.scale(s, s)
        cr.set_source_surface(self._composite, 0, 0)
        cr.get_source().set_filter(cairo.FILTER_GOOD)
        cr.paint()
        if self.current:
            draw_shape(cr, self.current, self.unit)
        cr.restore()
        # Hairline so a dark shot still separates from the black window
        _rounded_rect(cr, ox + 0.5, oy + 0.5, dw - 1, dh - 1, IMAGE_RADIUS)
        cr.set_source_rgba(1, 1, 1, 0.1)
        cr.set_line_width(1)
        cr.stroke()
        return False

    def _to_image(self, event):
        s, ox, oy = self._view
        x = min(max((event.x - ox) / s, 0), self.iw)
        y = min(max((event.y - oy) / s, 0), self.ih)
        return (x, y)

    def _on_press(self, _w, event):
        if event.button != 1 or event.type != Gdk.EventType.BUTTON_PRESS:
            return True  # never start a window drag from the canvas
        point = self._to_image(event)
        if self.tool == "text":
            self._ask_text(event, point)
            return True
        if self.tool == "marker":
            self.current = {"tool": "marker", "color": self.color, "points": [point]}
        else:
            self.current = {"tool": self.tool, "color": self.color, "p0": point, "p1": point}
        self.canvas.queue_draw()
        return True

    def _on_motion(self, _w, event):
        if not self.current:
            return False
        point = self._to_image(event)
        if self.current["tool"] == "marker":
            self.current["points"].append(point)
        else:
            self.current["p1"] = point
        self.canvas.queue_draw()
        return True

    def _on_release(self, _w, event):
        shape, self.current = self.current, None
        if not shape or event.button != 1:
            return False
        if shape["tool"] == "marker":
            self._add(shape)
        elif shape["tool"] == "arrow":
            (x0, y0), (x1, y1) = shape["p0"], shape["p1"]
            if math.hypot(x1 - x0, y1 - y0) >= self.unit * 3:
                self._add(shape)
        else:
            _x, _y, w, h = _rect(shape["p0"], shape["p1"])
            if w >= 3 and h >= 3:
                self._add(shape)
        self.canvas.queue_draw()
        return True

    # ---- text ------------------------------------------------------------------------
    def _ask_text(self, event, point):
        self._text_at = point
        rect = Gdk.Rectangle()
        rect.x, rect.y, rect.width, rect.height = int(event.x), int(event.y), 1, 1
        self.popover.set_pointing_to(rect)
        self.text_entry.set_text("")
        self.popover.popup()
        self.text_entry.grab_focus()

    def _commit_text(self, entry):
        text, point = entry.get_text().strip(), self._text_at
        self._text_at = None
        self.popover.popdown()
        if text and point:
            self._add({"tool": "text", "color": self.color, "p0": point, "text": text})

    def _cancel_text(self):
        self._text_at = None

    # ---- output ----------------------------------------------------------------------
    def copy(self):
        out = screenshot.TEMP_DIR / "edited.png"
        out.parent.mkdir(parents=True, exist_ok=True)
        self._composite.write_to_png(str(out))
        screenshot.copy(out)
        self._show_toast(_("Kopiert"))

    def save(self):
        """Overwrite the shot in the pictures folder (a cached shot gets a file there) and copy it."""
        target = screenshot.new_path(self.config, saved=True) if screenshot.is_temp(self.path) else self.path
        try:
            self._composite.write_to_png(str(target))
        except (OSError, cairo.Error) as err:
            self._show_toast(str(err))
            return
        screenshot.copy(target)
        self._dirty = False
        if self._on_saved:
            self._on_saved(target)
        self.destroy()

    def _request_close(self):
        """True if the window may close. Unsaved markup needs a second click/Esc, like Restart in the island."""
        if not self._dirty or self._close_armed:
            return True
        self.close_label.show()
        self.close_button.get_style_context().add_class("armed")
        self._show_toast(_("Ungespeicherte Markierungen – nochmal zum Verwerfen"))
        self._close_armed = GLib.timeout_add(CONFIRM_MS, self._disarm_close)
        return False

    def _disarm_close(self):
        if self._close_armed:
            GLib.source_remove(self._close_armed)
            self._close_armed = 0
        self.close_label.hide()
        self.close_button.get_style_context().remove_class("armed")
        return GLib.SOURCE_REMOVE

    def _on_key(self, _w, event):
        if self.popover.get_visible():
            return False  # typing text
        ctrl = event.state & Gdk.ModifierType.CONTROL_MASK
        key = Gdk.keyval_to_lower(event.keyval)
        if ctrl and key == Gdk.KEY_z:
            self.undo()
        elif ctrl and key == Gdk.KEY_c:
            self.copy()
        elif ctrl and key == Gdk.KEY_s:
            self.save()
        elif key == Gdk.KEY_Escape:
            if self._request_close():
                self.destroy()
        elif not ctrl and Gdk.KEY_1 <= key <= Gdk.KEY_9 and key - Gdk.KEY_1 < len(COLORS):
            self.color_buttons[key - Gdk.KEY_1].set_active(True)
        elif not ctrl and key in {k for _n, _t, k in TOOLS}:
            name = next(n for n, _t, k in TOOLS if k == key)
            self.tool_buttons[name].set_active(True)
        else:
            return False
        return True
