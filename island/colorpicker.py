"""The colour picker's overlay: a borderless window over the whole screen that shows a frozen snapshot.

The snapshot is taken once (with the island out of the way), so neither the island nor this window is in the
picture. The window covers every monitor (one override-redirect window at 0,0 of the X screen) and grabs the
pointer and keyboard. A loupe follows the pointer; it is only redrawn when the pointer moves.

    click   pick the pixel under the pointer      Esc / right click   cancel
    wheel   change the loupe's size (5 … 25 pixels square)

The snapshot is in device pixels; with a HiDPI scale factor the window is smaller than the snapshot, and the
pointer position is multiplied by the scale to find the pixel. The snapshot is released the moment the picker
closes.
"""

import logging
import os
import tempfile
from pathlib import Path

import cairo
import gi

gi.require_version("GdkPixbuf", "2.0")
gi.require_version("PangoCairo", "1.0")
from gi.repository import Gdk, GdkPixbuf, Gio, GLib, Gtk, Pango, PangoCairo  # noqa: E402

from island.services import colors  # noqa: E402
from island.storage import CACHE_DIR  # noqa: E402

log = logging.getLogger("mosisland.colorpicker")

SNAPSHOT_DIR = CACHE_DIR / "colorpicker"
ZOOM = 10                 # one screen pixel becomes ZOOM x ZOOM pixels in the loupe
SIZE_MIN, SIZE_MAX, SIZE_DEFAULT = 5, 25, 11
LABEL_H, LABEL_W, LABEL_GAP, EDGE = 26, 96, 8, 14


def grab_snapshot(callback):
    """Shoot the whole X screen (all monitors, device pixels) with maim; callback((surface, scale)) or None.

    maim, not GDK: GDK reads the screen through a shared-memory image that it keeps attached for good (15 MB
    that never go back). maim runs, writes a BMP into the cache and ends; the file is deleted once it is loaded.
    """
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix="snap-", suffix=".bmp", dir=SNAPSHOT_DIR)
    os.close(fd)
    path = Path(name)

    def finished(proc, result):
        outcome = None
        try:
            if proc.wait_check_finish(result):
                pixbuf = GdkPixbuf.Pixbuf.new_from_file(str(path))
                root_width = Gdk.Screen.get_default().get_root_window().get_width()
                outcome = (Gdk.cairo_surface_create_from_pixbuf(pixbuf, 1, None),
                           max(1.0, pixbuf.get_width() / root_width))
                pixbuf = None
        except GLib.Error as error:
            log.warning("colorpicker: no snapshot: %s", error.message)
        path.unlink(missing_ok=True)
        callback(outcome)

    try:
        proc = Gio.Subprocess.new(["maim", "--hidecursor", "--format=bmp", str(path)],
                                  Gio.SubprocessFlags.STDOUT_SILENCE | Gio.SubprocessFlags.STDERR_SILENCE)
    except GLib.Error:
        path.unlink(missing_ok=True)
        callback(None)
        return
    proc.wait_check_async(None, finished)


class Picker(Gtk.Window):
    def __init__(self, surface, scale, on_done):
        super().__init__(type=Gtk.WindowType.POPUP)
        self._surface = surface
        self._scale = scale
        self._on_done = on_done
        self._size = SIZE_DEFAULT
        self._pos = (0.0, 0.0)             # pointer in window (logical) pixels
        self._dirty = None                 # the last loupe rectangle, to be repainted when it moves
        self._finished = False
        self._seat = None
        self._data = surface.get_data()    # BGRA, premultiplied; read for the colour under the pointer
        self._stride = surface.get_stride()
        screen = Gdk.Screen.get_default()
        self.set_app_paintable(True)
        self.set_decorated(False)
        self.set_skip_taskbar_hint(True)
        self.set_default_size(screen.get_width(), screen.get_height())
        self.move(0, 0)
        self.add_events(Gdk.EventMask.POINTER_MOTION_MASK | Gdk.EventMask.BUTTON_PRESS_MASK
                        | Gdk.EventMask.SCROLL_MASK | Gdk.EventMask.SMOOTH_SCROLL_MASK
                        | Gdk.EventMask.KEY_PRESS_MASK)
        self.connect("draw", self._on_draw)
        self.connect("motion-notify-event", self._on_motion)
        self.connect("button-press-event", self._on_press)
        self.connect("scroll-event", self._on_scroll)
        self.connect("key-press-event", self._on_key)
        self.connect("map-event", self._on_mapped)
        self._wheel_acc = 0.0

    # ---- start / end ------------------------------------------------------------------------------------
    def start(self):
        display = Gdk.Display.get_default()
        _screen, x, y = display.get_default_seat().get_pointer().get_position()
        self._pos = (float(x), float(y))
        self.show_all()

    def _on_mapped(self, *_):
        GLib.idle_add(self._grab)
        return False

    def _grab(self):
        window = self.get_window()
        if window is None or self._finished:
            return GLib.SOURCE_REMOVE
        cursor = Gdk.Cursor.new_from_name(self.get_display(), "crosshair")
        seat = self.get_display().get_default_seat()
        status = seat.grab(window, Gdk.SeatCapabilities.ALL, False, cursor, None, None)
        if status != Gdk.GrabStatus.SUCCESS:
            log.warning("colorpicker: the pointer could not be grabbed (%s)", status.value_nick)
            self._finish(None)
            return GLib.SOURCE_REMOVE
        self._seat = seat
        self.queue_draw()
        return GLib.SOURCE_REMOVE

    def _finish(self, rgb):
        if self._finished:
            return
        self._finished = True
        if self._seat is not None:
            self._seat.ungrab()
            self._seat = None
        self.destroy()
        # Let go of the snapshot (8-33 MB) before reporting back
        self._surface = self._data = None
        self._on_done(rgb)

    # ---- the pixel under the pointer -----------------------------------------------------------------
    def _device(self):
        x, y = self._pos
        return int(x * self._scale), int(y * self._scale)

    def _rgb_at(self, px, py):
        width, height = self._surface.get_width(), self._surface.get_height()
        px, py = max(0, min(width - 1, px)), max(0, min(height - 1, py))
        i = py * self._stride + px * 4
        return self._data[i + 2], self._data[i + 1], self._data[i]       # cairo ARGB32 is B, G, R, A in memory

    # ---- events -----------------------------------------------------------------------------------------------
    def _on_motion(self, _w, event):
        self._move_to(event.x, event.y)
        return True

    def _move_to(self, x, y):
        old = self._loupe_rect()
        self._pos = (x, y)
        self._invalidate(old)
        self._invalidate(self._loupe_rect())

    def _invalidate(self, rect):
        x, y, w, h = rect
        self.queue_draw_area(int(x) - 2, int(y) - 2, int(w) + 4, int(h) + 4)

    def _on_press(self, _w, event):
        if event.type != Gdk.EventType.BUTTON_PRESS:
            return True
        if event.button == 1:
            self._finish(self._rgb_at(*self._device()))
        elif event.button == 3:
            self._finish(None)
        return True

    def _on_scroll(self, _w, event):
        if event.direction == Gdk.ScrollDirection.SMOOTH:
            self._wheel_acc += event.get_scroll_deltas()[2]
        elif event.direction in (Gdk.ScrollDirection.UP, Gdk.ScrollDirection.DOWN):
            self._wheel_acc += -1 if event.direction == Gdk.ScrollDirection.UP else 1
        if abs(self._wheel_acc) >= 1:
            step = -2 if self._wheel_acc > 0 else 2       # wheel up = bigger loupe
            self._wheel_acc = 0.0
            old = self._loupe_rect()
            self._size = max(SIZE_MIN, min(SIZE_MAX, self._size + step))
            self._invalidate(old)
            self._invalidate(self._loupe_rect())
        return True

    def _on_key(self, _w, event):
        if event.keyval == Gdk.KEY_Escape:
            self._finish(None)
        elif event.keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter, Gdk.KEY_space):
            self._finish(self._rgb_at(*self._device()))
        return True

    # ---- drawing ---------------------------------------------------------------------------------------------
    def _loupe_rect(self):
        """x, y, width, height of the loupe including its label, in window pixels, kept on the screen."""
        side = self._size * ZOOM
        width = max(side, LABEL_W)             # the label under a small loupe is wider than the loupe
        x, y = self._pos
        screen_w, screen_h = self.get_allocated_width() or 1, self.get_allocated_height() or 1
        lx, ly = x + EDGE, y + EDGE
        if lx + width > screen_w:
            lx = x - EDGE - width
        total_h = side + LABEL_GAP + LABEL_H
        if ly + total_h > screen_h:
            ly = y - EDGE - total_h
        return lx, ly, width, total_h

    def _on_draw(self, _w, cr):
        if self._surface is None:
            return False
        # The frozen screen (the snapshot is in device pixels)
        cr.save()
        cr.scale(1 / self._scale, 1 / self._scale)
        cr.set_source_surface(self._surface, 0, 0)
        cr.paint()
        cr.restore()
        if self._seat is None:
            return False
        self._draw_loupe(cr)
        return False

    def _draw_loupe(self, cr):
        lx, ly, width, _h = self._loupe_rect()
        side = self._size * ZOOM
        px, py = self._device()
        n = self._size
        half = n // 2
        rgb = self._rgb_at(px, py)
        # The magnified pixels: nearest-neighbour, so every pixel stays a clear square
        cr.save()
        _rounded(cr, lx, ly, side, side, 10)
        cr.clip()
        cr.translate(lx, ly)
        cr.scale(ZOOM / self._scale, ZOOM / self._scale)
        cr.translate(-(px - half), -(py - half))
        cr.set_source_surface(self._surface, 0, 0)
        cr.get_source().set_filter(cairo.FILTER_NEAREST)
        cr.paint()
        cr.restore()
        # Frame and the marked middle pixel
        cr.set_line_width(2)
        cr.set_source_rgba(0, 0, 0, 0.85)
        _rounded(cr, lx, ly, side, side, 10)
        cr.stroke()
        cr.set_line_width(1)
        cr.set_source_rgba(1, 1, 1, 0.9)
        _rounded(cr, lx + 1, ly + 1, side - 2, side - 2, 9)
        cr.stroke()
        mid = half * ZOOM
        cr.set_line_width(2)
        cr.set_source_rgba(0, 0, 0, 0.9)
        cr.rectangle(lx + mid - 1, ly + mid - 1, ZOOM + 2, ZOOM + 2)
        cr.stroke()
        cr.set_line_width(1)
        cr.set_source_rgba(1, 1, 1, 0.95)
        cr.rectangle(lx + mid, ly + mid, ZOOM, ZOOM)
        cr.stroke()
        # Label: colour swatch and hex value
        ly2 = ly + side + LABEL_GAP
        _rounded(cr, lx, ly2, width, LABEL_H, 8)
        cr.set_source_rgba(0, 0, 0, 0.85)
        cr.fill()
        cr.set_source_rgb(*(c / 255 for c in rgb))
        _rounded(cr, lx + 6, ly2 + 5, 16, 16, 4)
        cr.fill_preserve()
        cr.set_source_rgba(1, 1, 1, 0.5)
        cr.set_line_width(1)
        cr.stroke()
        layout = PangoCairo.create_layout(cr)
        layout.set_font_description(Pango.FontDescription("Inter 10"))
        layout.set_text(colors.to_hex(rgb), -1)
        cr.set_source_rgb(0.96, 0.96, 0.97)
        cr.move_to(lx + 28, ly2 + 4)
        PangoCairo.show_layout(cr, layout)


def _rounded(cr, x, y, w, h, r):
    cr.new_sub_path()
    cr.arc(x + w - r, y + r, r, -1.5708, 0)
    cr.arc(x + w - r, y + h - r, r, 0, 1.5708)
    cr.arc(x + r, y + h - r, r, 1.5708, 3.1416)
    cr.arc(x + r, y + r, r, 3.1416, 4.7124)
    cr.close_path()
