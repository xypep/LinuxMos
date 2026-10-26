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
