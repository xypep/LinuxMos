"""Small UI building blocks: the pill shape, the size animator and widget helpers."""

import math

import cairo
from gi.repository import Gdk, GLib, Gtk, Pango

from island import mascots


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
        if self._tick_id:
            self._widget.remove_tick_callback(self._tick_id)
            self._tick_id = 0
        self._on_done = None
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
    """The mascot: a pair of eyes (or another character, see mascots.py) that blinks now and
    then, dozes off and says hello.

    It only animates while visible: a blink is ~180 ms of frames every few
    seconds, sleeping and greeting are static drawings. In the big-eyes mode
    (set_scale) the same drawing is just scaled up.
    """

    BASE_W, BASE_H = 60, 22

    def __init__(self, style=mascots.DEFAULT):
        super().__init__()
        self.set_size_request(self.BASE_W, self.BASE_H)
        self.figure = style
        self.scale = 1.0
        self.mode = "awake"     # awake | sleep | hello
        self._blink = 0.0       # 0 = open, 1 = closed
        self._blink_id = 0
        self._tick_id = 0
        self._start = 0
        self._more_blinks = 0   # blinks still to follow the running one (blink_twice)
        self.connect("map", lambda *_: self._schedule_blink())
        self.connect("unmap", lambda *_: self._stop())

    def set_scale(self, scale):
        """1.0 = the normal size; bigger for the idle island's big-eyes mode."""
        if scale != self.scale:
            self.scale = scale
            self.set_size_request(round(self.BASE_W * scale), round(self.BASE_H * scale))
            self.queue_draw()

    def blink_twice(self):
        """Two quick blinks now (the heads-up before a stretch card); False if the eyes aren't on show."""
        if self.mode != "awake" or not self.get_mapped():
            return False
        self._more_blinks = 1
        self._stop()
        self._begin_blink()
        return True

    def set_figure(self, figure):
        if figure != self.figure:
            self.figure = figure
            self.queue_draw()

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
        self._blink = math.sin(math.pi * min(1.0, max(0.0, p)))
        self.queue_draw()
        if p < 1.0:
            return GLib.SOURCE_CONTINUE
        self._blink = 0.0
        if self._more_blinks:
            self._more_blinks -= 1
            self._start = clock.get_frame_time() + 110_000    # eyes open for a moment, then the next blink
            return GLib.SOURCE_CONTINUE
        self._tick_id = 0
        self._schedule_blink()
        return GLib.SOURCE_REMOVE

    def do_draw(self, cr):
        w, h = self.get_allocated_width(), self.get_allocated_height()
        if self.scale != 1.0:
            # The drawing is made for 60x22 px: centre that box and blow it up
            cr.translate(0, (h - self.BASE_H * self.scale) / 2)
            cr.scale(self.scale, self.scale)
            w, h = w / self.scale, self.BASE_H
        mascots.draw(self.figure, cr, w, h, self.mode, self._blink)
        return False


class Ring(Gtk.DrawingArea):
    """A progress ring (the stretch countdown in the pill's left slot). Redraws only when the percent changes."""

    SIZE = 22
    COLOR = (0.30, 0.82, 0.70)

    def __init__(self):
        super().__init__()
        self.set_size_request(self.SIZE, self.SIZE)
        self.set_valign(Gtk.Align.CENTER)
        self.fraction = 0.0

    def set_fraction(self, fraction):
        fraction = min(max(fraction, 0.0), 1.0)
        if round(fraction * 100) != round(self.fraction * 100):
            self.fraction = fraction
            self.queue_draw()
        else:
            self.fraction = fraction

    def do_draw(self, cr):
        cx = cy = self.SIZE / 2
        r = self.SIZE / 2 - 2.2
        cr.set_line_width(3)
        cr.set_source_rgba(1, 1, 1, 0.18)
        cr.arc(cx, cy, r, 0, 2 * math.pi)
        cr.stroke()
        if self.fraction > 0:
            cr.set_source_rgb(*self.COLOR)
            cr.set_line_cap(cairo.LINE_CAP_ROUND)
            cr.arc(cx, cy, r, -math.pi / 2, -math.pi / 2 + 2 * math.pi * self.fraction)
            cr.stroke()
        return False


class LiveDots(Gtk.DrawingArea):
    """Status marks at the folded island's right end: a stretching figure (a reminder waits for an answer),
    microphone (orange), camera (green), download ring.

    Static drawings: they only redraw when their state changes.
    """

    DOT, RING, GLYPH, GAP = 7, 14, 12, 5
    MIC, MUTED, CAM, RING_FG = (1.0, 0.62, 0.04), (0.6, 0.6, 0.62), (0.19, 0.82, 0.35), (0.04, 0.52, 1.0)
    STRETCH = (0.30, 0.82, 0.70)

    def __init__(self):
        super().__init__()
        self.mic = None          # None | "on" | "muted"
        self.cam = False
        self.download = None     # None | -1 (no percentage) | 0..100
        self.stretch = False
        self.set_valign(Gtk.Align.CENTER)
        self.set_no_show_all(True)

    def set_state(self, mic, cam, download, stretch=False):
        """True if the width changed (the pill has to resize)."""
        if (mic, cam, download, stretch) == (self.mic, self.cam, self.download, self.stretch):
            return False
        before = self.width
        self.mic, self.cam, self.download, self.stretch = mic, cam, download, stretch
        self.set_size_request(self.width, self.RING)
        self.set_visible(self.width > 0)
        self.queue_draw()
        return self.width != before

    @property
    def width(self):
        parts = [self.GLYPH] * self.stretch + [self.DOT] * ((self.mic is not None) + self.cam) \
            + ([self.RING] if self.download is not None else [])
        return sum(parts) + self.GAP * max(0, len(parts) - 1)

    def hits_stretch(self, x):
        """x in this widget's coordinates: on the stretching figure (a little margin to hit it easily)."""
        return self.stretch and -4 <= x <= self.GLYPH + self.GAP

    def do_draw(self, cr):
        h = self.get_allocated_height()
        x, cy = 0.0, h / 2
        if self.stretch:
            self._draw_stretcher(cr, x + self.GLYPH / 2, cy)
            x += self.GLYPH + self.GAP
        for color in ([self.MIC if self.mic == "on" else self.MUTED] if self.mic else []) + \
                     ([self.CAM] if self.cam else []):
            cr.set_source_rgb(*color)
            cr.arc(x + self.DOT / 2, cy, self.DOT / 2, 0, 2 * math.pi)
            cr.fill()
            x += self.DOT + self.GAP
        if self.download is not None:
            r = self.RING / 2 - 1.2
            cx = x + self.RING / 2
            cr.set_line_width(2)
            cr.set_source_rgba(1, 1, 1, 0.22)
            cr.arc(cx, cy, r, 0, 2 * math.pi)
            cr.stroke()
            if self.download >= 0:
                cr.set_source_rgb(*self.RING_FG)
                cr.arc(cx, cy, r, -math.pi / 2, -math.pi / 2 + 2 * math.pi * self.download / 100)
                cr.stroke()
            # Arrow down in the middle
            cr.set_source_rgba(0.96, 0.96, 0.97, 1)
            cr.set_line_width(1.4)
            cr.move_to(cx, cy - 3)
            cr.line_to(cx, cy + 2.5)
            cr.move_to(cx - 2.5, cy)
            cr.line_to(cx, cy + 2.5)
            cr.line_to(cx + 2.5, cy)
            cr.stroke()
        return False

    def _draw_stretcher(self, cr, cx, cy):
        """A little figure with its arms up."""
        cr.set_source_rgb(*self.STRETCH)
        cr.set_line_width(1.7)
        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        cr.set_line_join(cairo.LINE_JOIN_ROUND)
        cr.arc(cx, cy - 4.6, 1.7, 0, 2 * math.pi)
        cr.fill()
        cr.move_to(cx - 4.2, cy - 5.2)    # arms up
        cr.line_to(cx, cy - 1.6)
        cr.line_to(cx + 4.2, cy - 5.2)
        cr.move_to(cx, cy - 1.6)          # body
        cr.line_to(cx, cy + 1.8)
        cr.move_to(cx - 2.6, cy + 5.6)    # legs
        cr.line_to(cx, cy + 1.8)
        cr.line_to(cx + 2.6, cy + 5.6)
        cr.stroke()


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
