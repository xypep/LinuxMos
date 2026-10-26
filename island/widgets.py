"""Small UI building blocks: the pill shape, the size animator and widget helpers."""

import math

import cairo
from gi.repository import Gdk, GLib, Gtk, Pango


class Pill(Gtk.Box):
    """The black island itself. Draws its rounded shape and clips its children to it."""

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.set_halign(Gtk.Align.CENTER)
        self.set_valign(Gtk.Align.START)
        # Otherwise the scrollable tabs propagate vexpand and Gtk.Box centers the pill
        self.set_vexpand(False)
        self.set_hexpand(False)
        self.radius = 17.0

    def _shape(self, cr, w, h):
        r = max(0.0, min(self.radius, h / 2, w / 2))
        cr.new_sub_path()
        cr.arc(w - r, r, r, -math.pi / 2, 0)
        cr.arc(w - r, h - r, r, 0, math.pi / 2)
        cr.arc(r, h - r, r, math.pi / 2, math.pi)
        cr.arc(r, r, r, math.pi, 3 * math.pi / 2)
        cr.close_path()

    def do_draw(self, cr):
        w, h = self.get_allocated_width(), self.get_allocated_height()
        self._shape(cr, w, h)
        cr.set_source_rgba(0, 0, 0, 0.96)
        cr.fill_preserve()
        cr.set_source_rgba(1, 1, 1, 0.08)
        cr.set_line_width(1)
        cr.stroke()
        cr.save()
        self._shape(cr, w, h)
        cr.clip()
        Gtk.Box.do_draw(self, cr)
        cr.restore()
        return False


class Animator:
    """Animates (width, height, radius) on the frame clock, only while moving."""

    def __init__(self, widget, apply, duration_ms=240):
        self._widget = widget
        self._apply = apply
        self._duration = duration_ms * 1000
        self.value = (0.0, 0.0, 0.0)
        self._from = self._to = self.value
        self._start = None
        self._tick_id = 0
        self._on_done = None
        self._bounce = False

    def jump(self, target):
        self.value = self._to = tuple(map(float, target))
        self._apply(*self.value)

    def to(self, target, on_done=None, bounce=False):
        self._from, self._to = self.value, tuple(map(float, target))
        self._start, self._on_done, self._bounce = None, on_done, bounce
        if not self._tick_id:
            self._tick_id = self._widget.add_tick_callback(self._tick)

    @property
    def target(self):
        return self._to

    def _tick(self, _widget, clock):
        now = clock.get_frame_time()
        if self._start is None:
            self._start = now
        p = min(1.0, (now - self._start) / self._duration)
        if self._bounce:
            # easeOutBack: a gentle overshoot, like iOS when the island opens
            c = 1.2
            e = 1 + (c + 1) * (p - 1) ** 3 + c * (p - 1) ** 2
        else:
            e = 1 - (1 - p) ** 3  # easeOutCubic
        self.value = tuple(a + (b - a) * e for a, b in zip(self._from, self._to))
        self._apply(*self.value)
        if p < 1.0:
            return GLib.SOURCE_CONTINUE
        self._tick_id = 0
        done, self._on_done = self._on_done, None
        if done:
            done()
        return GLib.SOURCE_REMOVE


class Eyes(Gtk.DrawingArea):
    """The mascot: two eyes that blink now and then, doze off and say hello.

    It only animates while visible: a blink is ~180 ms of frames every few
    seconds, sleeping and greeting are static drawings.
    """

    EYE_W, EYE_H, GAP = 9, 15, 13

    def __init__(self):
        super().__init__()
        self.set_size_request(60, 22)
        self.mode = "awake"     # awake | sleep | hello
        self._blink = 0.0       # 0 = open, 1 = closed
        self._blink_id = 0
        self._tick_id = 0
        self._start = 0
        self.connect("map", lambda *_: self._schedule_blink())
        self.connect("unmap", lambda *_: self._stop())

    def set_mode(self, mode):
        if mode != self.mode:
            self.mode = mode
            self.queue_draw()
            self._schedule_blink()

    def _schedule_blink(self):
        self._stop()
        if self.mode == "awake" and self.get_mapped():
            self._blink_id = GLib.timeout_add(int(GLib.random_int_range(2500, 6500)), self._begin_blink)

    def _stop(self):
        if self._blink_id:
            GLib.source_remove(self._blink_id)
            self._blink_id = 0

    def _begin_blink(self):
        self._blink_id = 0
        self._start = 0
        if not self._tick_id:
            self._tick_id = self.add_tick_callback(self._tick)
        return GLib.SOURCE_REMOVE

    def _tick(self, _widget, clock):
        now = clock.get_frame_time()
        self._start = self._start or now
        p = (now - self._start) / 180_000
        self._blink = math.sin(math.pi * min(1.0, p))
        self.queue_draw()
        if p < 1.0:
            return GLib.SOURCE_CONTINUE
        self._tick_id = 0
        self._blink = 0.0
        self._schedule_blink()
        return GLib.SOURCE_REMOVE

    def do_draw(self, cr):
        w, h = self.get_allocated_width(), self.get_allocated_height()
        cr.set_source_rgba(0.96, 0.96, 0.97, 1)
        cy = h / 2
        for cx in (w / 2 - self.GAP / 2 - self.EYE_W / 2, w / 2 + self.GAP / 2 + self.EYE_W / 2):
            if self.mode == "sleep":
                # Closed eyes: a soft downward curve
                cr.set_line_width(2)
                cr.arc(cx, cy - 2, self.EYE_W / 2, math.pi * 0.15, math.pi * 0.85)
                cr.stroke()
            elif self.mode == "hello":
                # Happy eyes: ^ ^
                cr.set_line_width(2.4)
                cr.move_to(cx - self.EYE_W / 2, cy + 3)
                cr.line_to(cx, cy - 4)
                cr.line_to(cx + self.EYE_W / 2, cy + 3)
                cr.stroke()
            else:
                eh = max(2.0, self.EYE_H * (1 - self._blink))
                r = min(self.EYE_W / 2, eh / 2)
                x, y = cx - self.EYE_W / 2, cy - eh / 2
                cr.new_sub_path()
                cr.arc(x + self.EYE_W - r, y + r, r, -math.pi / 2, 0)
                cr.arc(x + self.EYE_W - r, y + eh - r, r, 0, math.pi / 2)
                cr.arc(x + r, y + eh - r, r, math.pi / 2, math.pi)
                cr.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
                cr.close_path()
                cr.fill()
        if self.mode == "sleep":
            cr.set_source_rgba(0.96, 0.96, 0.97, 0.6)
            cr.select_font_face("Inter", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
            cr.set_font_size(8)
            cr.move_to(w - 9, 8)
            cr.show_text("z")
            cr.set_font_size(6)
            cr.move_to(w - 4, 4)
            cr.show_text("z")
        return False


class BarChart(Gtk.DrawingArea):
    """Tiny bar chart (water per hour). Draws only when its data changes."""

    def __init__(self, height=110):
        super().__init__()
        self.set_size_request(-1, height)
        self.values = []
        self.labels = []

    def set_data(self, values, labels):
        self.values, self.labels = list(values), list(labels)
        self.queue_draw()

    def do_draw(self, cr):
        w, h = self.get_allocated_width(), self.get_allocated_height()
        n = len(self.values)
        if not n:
            return False
        top = max(max(self.values), 1)
        axis_w, base = 34, h - 16
        slot = (w - axis_w) / n
        cr.select_font_face("Inter", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        cr.set_font_size(9)
        # y axis: 0, half, max
        for frac in (0, 0.5, 1):
            y = base - (base - 8) * frac
            cr.set_source_rgba(1, 1, 1, 0.08)
            cr.rectangle(axis_w, y, w - axis_w, 1)
            cr.fill()
            cr.set_source_rgba(1, 1, 1, 0.45)
            cr.move_to(0, y + 3)
            cr.show_text(f"{int(top * frac)}")
        for i, value in enumerate(self.values):
            bh = (base - 8) * value / top
            x = axis_w + i * slot + slot * 0.2
            bw = slot * 0.6
            if bh > 0:
                r = min(3, bw / 2, bh / 2)
                cr.new_sub_path()
                cr.arc(x + bw - r, base - bh + r, r, -math.pi / 2, 0)
                cr.line_to(x + bw, base)
                cr.line_to(x, base)
                cr.arc(x + r, base - bh + r, r, math.pi, 3 * math.pi / 2)
                cr.close_path()
                cr.set_source_rgba(0.04, 0.52, 1.0, 0.95)
                cr.fill()
            if i < len(self.labels) and self.labels[i]:
                cr.set_source_rgba(1, 1, 1, 0.45)
                cr.move_to(x - 2, h - 2)
                cr.show_text(self.labels[i])
        return False


# ---- helpers ----------------------------------------------------------------
def label(text="", css=(), xalign=0.0, ellipsize=True, max_chars=-1):
    lbl = Gtk.Label(label=text, xalign=xalign)
    if ellipsize:
        lbl.set_ellipsize(Pango.EllipsizeMode.END)
    if max_chars > 0:
        lbl.set_max_width_chars(max_chars)
    for cls in css:
        lbl.get_style_context().add_class(cls)
    return lbl


def icon(name, size=16):
    img = Gtk.Image.new_from_icon_name(name, Gtk.IconSize.MENU)
    img.set_pixel_size(size)
    return img


def button(icon_name=None, text=None, tooltip=None, css=(), size=16, on_click=None):
    btn = Gtk.Button()
    btn.set_relief(Gtk.ReliefStyle.NONE)
    btn.set_can_focus(False)
    if icon_name and text:
        box = Gtk.Box(spacing=6)
        box.pack_start(icon(icon_name, size), False, False, 0)
        box.pack_start(label(text, ellipsize=False), False, False, 0)
        btn.add(box)
    elif icon_name:
        btn.add(icon(icon_name, size))
    else:
        btn.set_label(text or "")
    if tooltip:
        btn.set_tooltip_text(tooltip)
    for cls in css:
        btn.get_style_context().add_class(cls)
    if on_click:
        btn.connect("clicked", lambda *_: on_click())
    return btn


def css_class(widget, *classes):
    ctx = widget.get_style_context()
    for cls in classes:
        ctx.add_class(cls)
    return widget


def clear(container):
    for child in container.get_children():
        child.destroy()


def rounded_image(pixbuf, size, radius, scale=1):
    """A Gtk.Image with a pixbuf cropped to a rounded square (album covers)."""
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, size * scale, size * scale)
    surface.set_device_scale(scale, scale)
    cr = cairo.Context(surface)
    r = radius
    cr.new_sub_path()
    cr.arc(size - r, r, r, -math.pi / 2, 0)
    cr.arc(size - r, size - r, r, 0, math.pi / 2)
    cr.arc(r, size - r, r, math.pi / 2, math.pi)
    cr.arc(r, r, r, math.pi, 3 * math.pi / 2)
    cr.close_path()
    cr.clip()
    pw, ph = pixbuf.get_width(), pixbuf.get_height()
    factor = size / min(pw, ph)  # cover, not contain
    cr.translate((size - pw * factor) / 2, (size - ph * factor) / 2)
    cr.scale(factor, factor)
    Gdk.cairo_set_source_pixbuf(cr, pixbuf, 0, 0)
    cr.paint()
    return Gtk.Image.new_from_surface(surface)


def placeholder_cover(size):
    box = Gtk.Box()
    box.set_size_request(size, size)
    css_class(box, "cover-placeholder")
    img = icon("audio-x-generic-symbolic", size // 2)
    img.set_hexpand(True)
    img.set_vexpand(True)
    box.add(img)
    return box
