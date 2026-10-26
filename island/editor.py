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
from gi.repository import Gdk, Gtk, Pango, PangoCairo  # noqa: E402

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
COLORS = [(1.0, 0.23, 0.19), (1.0, 0.8, 0.0), (0.2, 0.78, 0.35), (0.04, 0.52, 1.0), (1.0, 1.0, 1.0), (0.1, 0.1, 0.1)]
MARKER_ALPHA = 0.45
BG = (0.16, 0.16, 0.17)


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
class _Glyph(Gtk.DrawingArea):
    """Toolbar icon drawn with cairo: looks the same with every icon theme."""

    def __init__(self, tool=None, color=None, size=18):
        super().__init__()
        self.tool, self.color = tool, color
        self.set_size_request(size, size)

    def do_draw(self, cr):
        s = min(self.get_allocated_width(), self.get_allocated_height())
        if self.color:
            cr.arc(s / 2, s / 2, s / 2 - 2, 0, 2 * math.pi)
            cr.set_source_rgb(*self.color)
            cr.fill_preserve()
            cr.set_source_rgba(0.5, 0.5, 0.5, 0.8)
            cr.set_line_width(1)
            cr.stroke()
            return False
        fg = self.get_style_context().get_color(self.get_state_flags())
        cr.set_source_rgba(fg.red, fg.green, fg.blue, fg.alpha)
        p = s * 0.18
        if self.tool == "arrow":
            _arrow(cr, (p, s - p), (s - p, p), s * 0.11)
        elif self.tool == "rect":
            cr.set_line_width(s * 0.1)
            _rounded_rect(cr, p, p + s * 0.08, s - 2 * p, s - 2 * p - s * 0.16, s * 0.1)
            cr.stroke()
        elif self.tool == "marker":
            cr.set_line_width(s * 0.3)
            cr.set_line_cap(cairo.LINE_CAP_ROUND)
            cr.move_to(p + 1, s * 0.62)
            cr.line_to(s - p - 1, s * 0.38)
            cr.push_group()
            cr.stroke()
            cr.pop_group_to_source()
            cr.paint_with_alpha(0.55)
        elif self.tool == "text":
            layout = PangoCairo.create_layout(cr)
            font = Pango.FontDescription.from_string("Sans Bold")
            font.set_absolute_size(s * 0.8 * Pango.SCALE)
            layout.set_font_description(font)
            layout.set_text("T", -1)
            w, h = layout.get_pixel_size()
            cr.move_to((s - w) / 2, (s - h) / 2)
            PangoCairo.show_layout(cr, layout)
        elif self.tool == "blur":
            cell = (s - 2 * p) / 3
            for i in range(3):
                for j in range(3):
                    cr.rectangle(p + i * cell, p + j * cell, cell, cell)
                    cr.save()
                    cr.clip()
                    cr.paint_with_alpha(0.9 if (i + j) % 2 == 0 else 0.35)
                    cr.restore()
                    cr.new_path()
        return False


def _radio(group, child, tooltip):
    btn = Gtk.RadioButton.new_from_widget(group)
    btn.set_mode(False)  # looks like a toggle button, not a radio dot
    btn.set_can_focus(False)
    btn.add(child)
    btn.set_tooltip_text(tooltip)
    return btn


def _icon_button(icon_name, tooltip, callback, text=None):
    btn = Gtk.Button()
    btn.set_can_focus(False)
    box = Gtk.Box(spacing=6)
    box.pack_start(Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.BUTTON), False, False, 0)
    if text:
        box.pack_start(Gtk.Label(label=text), False, False, 0)
    btn.add(box)
    btn.set_tooltip_text(tooltip)
    btn.connect("clicked", lambda *_: callback())
    return btn


# ---- the editor -------------------------------------------------------------------------
class Editor(Gtk.Window):
    """on_saved(path) runs after "Save" wrote the file and put it on the clipboard."""

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
        self._view = (1.0, 0.0, 0.0)  # scale, offset x, offset y
        self._render()

        self.set_title(_("Screenshot bearbeiten"))
        self.set_icon_name("camera-photo")
        self._build()
        self._size_to_image()
        self.connect("key-press-event", self._on_key)
        self.connect("delete-event", lambda *_: not self._may_close())
        self.show_all()  # after the default size, or GTK maps it at its minimum size

    # ---- layout ------------------------------------------------------------------------
    def _build(self):
        header = Gtk.HeaderBar(show_close_button=True, title=_("Screenshot bearbeiten"), subtitle=self.path.name)
        self.set_titlebar(header)

        tools = Gtk.Box()
        tools.get_style_context().add_class("linked")
        self.tool_buttons = {}
        group = None
        for name, tooltip, _key in TOOLS:
            btn = _radio(group, _Glyph(tool=name), _(tooltip))
            group = group or btn
            btn.connect("toggled", lambda b, n=name: b.get_active() and self._set_tool(n))
            tools.pack_start(btn, False, False, 0)
            self.tool_buttons[name] = btn
        header.pack_start(tools)

        colors = Gtk.Box()
        colors.get_style_context().add_class("linked")
        self.color_buttons = []
        group = None
        for i, color in enumerate(COLORS):
            btn = _radio(group, _Glyph(color=color, size=16), _("Farbe ({key})").format(key=i + 1))
            group = group or btn
            btn.connect("toggled", lambda b, c=color: b.get_active() and self._set_color(c))
            colors.pack_start(btn, False, False, 0)
            self.color_buttons.append(btn)
        header.pack_start(colors)

        save = _icon_button("document-save-symbolic", _("Speichern und kopieren (Ctrl+S)"), self.save, _("Speichern"))
        save.get_style_context().add_class("suggested-action")
        header.pack_end(save)
        header.pack_end(_icon_button("edit-copy-symbolic", _("In die Zwischenablage (Ctrl+C)"), self.copy))
        self.undo_button = _icon_button("edit-undo-symbolic", _("Rückgängig (Ctrl+Z)"), self.undo)
        self.undo_button.set_sensitive(False)
        header.pack_end(self.undo_button)

        self.canvas = Gtk.DrawingArea(can_focus=True)
        # Motion only while a button is held: no events at all while just hovering
        self.canvas.add_events(Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.BUTTON_RELEASE_MASK
                               | Gdk.EventMask.BUTTON_MOTION_MASK)
        self.canvas.connect("draw", self._on_draw)
        self.canvas.connect("button-press-event", self._on_press)
        self.canvas.connect("motion-notify-event", self._on_motion)
        self.canvas.connect("button-release-event", self._on_release)
        self.canvas.connect("realize", lambda *_: self._update_cursor())
        self.add(self.canvas)

        # Text tool: a small entry that pops up where the user clicked
        self.text_entry = Gtk.Entry(width_chars=24, placeholder_text=_("Text eingeben, Enter"))
        self.text_entry.connect("activate", self._commit_text)
        self.popover = Gtk.Popover(relative_to=self.canvas, modal=True)
        self.popover.add(self.text_entry)
        self.text_entry.show()  # the window's show_all() does not reach into popovers
        self.popover.connect("closed", lambda *_: self._cancel_text())
        self._text_at = None

    def _size_to_image(self):
        display = Gdk.Display.get_default()
        _screen, x, y = display.get_default_seat().get_pointer().get_position()
        monitor = display.get_monitor_at_point(x, y) or display.get_primary_monitor() or display.get_monitor(0)
        area, scale = monitor.get_workarea(), monitor.get_scale_factor()
        w = min(self.iw / scale + 40, area.width * 0.85)
        h = min(self.ih / scale + 40, area.height * 0.85 - 50)
        self.set_default_size(max(560, int(w)), max(320, int(h)))
        self.set_position(Gtk.WindowPosition.CENTER)

    # ---- state -------------------------------------------------------------------------
    def _set_tool(self, name):
        self.tool = name
        self._update_cursor()

    def _set_color(self, color):
        self.color = color

    def _update_cursor(self):
        win = self.canvas.get_window()
        if win:
            win.set_cursor(Gdk.Cursor.new_from_name(win.get_display(), "text" if self.tool == "text" else "crosshair"))

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
        self._render()
        self.canvas.queue_draw()

    # ---- canvas ------------------------------------------------------------------------
    def _on_draw(self, widget, cr):
        aw, ah = widget.get_allocated_width(), widget.get_allocated_height()
        cr.set_source_rgb(*BG)
        cr.paint()
        # Never upscale: on a HiDPI screen 1/scale shows the shot pixel for pixel
        s = min((aw - 24) / self.iw, (ah - 24) / self.ih, 1 / widget.get_scale_factor())
        s = max(s, 0.01)
        ox, oy = (aw - self.iw * s) / 2, (ah - self.ih * s) / 2
        self._view = (s, ox, oy)
        cr.translate(ox, oy)
        cr.scale(s, s)
        cr.set_source_surface(self._composite, 0, 0)
        cr.get_source().set_filter(cairo.FILTER_GOOD)
        cr.paint()
        if self.current:
            cr.rectangle(0, 0, self.iw, self.ih)
            cr.clip()
            draw_shape(cr, self.current, self.unit)
        return False

    def _to_image(self, event):
        s, ox, oy = self._view
        x = min(max((event.x - ox) / s, 0), self.iw)
        y = min(max((event.y - oy) / s, 0), self.ih)
        return (x, y)

    def _on_press(self, _w, event):
        if event.button != 1 or event.type != Gdk.EventType.BUTTON_PRESS:
            return False
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
        self.get_titlebar().set_subtitle(_("In der Zwischenablage"))

    def save(self):
        """Overwrite the shot in the pictures folder (a cached shot gets a file there) and copy it."""
        target = screenshot.new_path(self.config, saved=True) if screenshot.is_temp(self.path) else self.path
        try:
            self._composite.write_to_png(str(target))
        except (OSError, cairo.Error) as err:
            self.get_titlebar().set_subtitle(str(err))
            return
        screenshot.copy(target)
        self._dirty = False
        if self._on_saved:
            self._on_saved(target)
        self.destroy()

    def _may_close(self):
        if not self._dirty:
            return True
        dialog = Gtk.MessageDialog(transient_for=self, modal=True, message_type=Gtk.MessageType.QUESTION,
                                   buttons=Gtk.ButtonsType.NONE, text=_("Änderungen verwerfen?"))
        dialog.format_secondary_text(_("Der Screenshot ohne Markierungen bleibt erhalten."))
        dialog.add_buttons(_("Abbrechen"), Gtk.ResponseType.CANCEL, _("Verwerfen"), Gtk.ResponseType.ACCEPT)
        answer = dialog.run()
        dialog.destroy()
        return answer == Gtk.ResponseType.ACCEPT

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
            if self._may_close():
                self.destroy()
        elif not ctrl and Gdk.KEY_1 <= key <= Gdk.KEY_9 and key - Gdk.KEY_1 < len(COLORS):
            self.color_buttons[key - Gdk.KEY_1].set_active(True)
        elif not ctrl and key in {k for _n, _t, k in TOOLS}:
            name = next(n for n, _t, k in TOOLS if k == key)
            self.tool_buttons[name].set_active(True)
        else:
            return False
        return True
