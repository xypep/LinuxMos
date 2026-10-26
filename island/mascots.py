"""The mascots: small characters that sit in the idle island while the user is away.

Each one is a Cairo drawing for a 60x22 px area in three moods:

    awake   eyes open, blink 0 = open … 1 = closed (the widget animates it)
    sleep   eyes closed, "z z" in the corner
    hello   happy eyes, for a moment after the user comes back

Pure drawing code (no GTK): widgets.Eyes owns the timing and calls draw().
"""

import math

import cairo

# Config value -> name shown in the tray (German source strings, translated there)
STYLES = {"eyes": "Augen", "cat": "Katze", "robot": "Roboter", "blob": "Blob"}
DEFAULT = "eyes"

WHITE = (0.96, 0.96, 0.97)
INK = (0.09, 0.09, 0.11)
CAT_EYE, ROBOT_EYE, ROBOT_LAMP = (0.86, 0.95, 0.42), (0.36, 0.86, 1.0), (1.0, 0.45, 0.30)
BLOB_BODY, BLOB_CHEEK = (1.0, 0.82, 0.30), (1.0, 0.52, 0.52)


def draw(style, cr, w, h, mode, blink):
    """Paint the mascot `style` (unknown names draw the eyes) onto cr."""
    DRAWERS.get(style, _eyes)(cr, w, h, mode, blink)
    if mode == "sleep":
        _zzz(cr, w, 0 if style not in DRAWERS or style == "eyes" else 3)   # heads reach further right


# ---- shared pieces ---------------------------------------------------------------
def _rgb(cr, color, alpha=1.0):
    cr.set_source_rgba(*color, alpha)


def _round_rect(cr, x, y, w, h, r):
    r = max(0.0, min(r, w / 2, h / 2))
    cr.new_sub_path()
    cr.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    cr.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    cr.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    cr.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
    cr.close_path()


def _ellipse(cr, cx, cy, rx, ry):
    cr.save()
    cr.translate(cx, cy)
    cr.scale(max(rx, 0.01), max(ry, 0.01))
    cr.arc(0, 0, 1, 0, 2 * math.pi)
    cr.restore()


def _sleep_eye(cr, cx, cy, half_w):
    """Closed eye: a soft downward curve."""
    cr.set_line_width(2)
    cr.set_line_cap(cairo.LINE_CAP_ROUND)
    cr.arc(cx, cy - 2, half_w, math.pi * 0.15, math.pi * 0.85)
    cr.stroke()


def _happy_eye(cr, cx, cy, half_w, width=2.4):
    """Happy eye: ^"""
    cr.set_line_width(width)
    cr.set_line_cap(cairo.LINE_CAP_ROUND)
    cr.set_line_join(cairo.LINE_JOIN_ROUND)
    cr.move_to(cx - half_w, cy + 3)
    cr.line_to(cx, cy - 4)
    cr.line_to(cx + half_w, cy + 3)
    cr.stroke()


def _zzz(cr, w, dx=0):
    w += dx
    cr.set_source_rgba(*WHITE, 0.6)
    cr.select_font_face("Inter", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    cr.set_font_size(8)
    cr.move_to(w - 9, 8)
    cr.show_text("z")
    cr.set_font_size(6)
    cr.move_to(w - 4, 4)
    cr.show_text("z")


# ---- the characters ----------------------------------------------------------------
def _eyes(cr, w, h, mode, blink):
    EYE_W, EYE_H, GAP = 9, 15, 13
    _rgb(cr, WHITE)
    cy = h / 2
    for cx in (w / 2 - GAP / 2 - EYE_W / 2, w / 2 + GAP / 2 + EYE_W / 2):
        if mode == "sleep":
            _sleep_eye(cr, cx, cy, EYE_W / 2)
        elif mode == "hello":
            _happy_eye(cr, cx, cy, EYE_W / 2)
        else:
            eh = max(2.0, EYE_H * (1 - blink))
            _round_rect(cr, cx - EYE_W / 2, cy - eh / 2, EYE_W, eh, EYE_W / 2)
            cr.fill()


def _cat(cr, w, h, mode, blink):
    cx = w / 2
    # Head with two ears
    _rgb(cr, WHITE)
    cr.set_line_width(1.6)
    cr.set_line_join(cairo.LINE_JOIN_ROUND)
    cr.move_to(cx - 21, 9.5)
    cr.line_to(cx - 19.5, 1.2)
    cr.line_to(cx - 11, 4.2)
    cr.curve_to(cx - 5, 2.6, cx + 5, 2.6, cx + 11, 4.2)
    cr.line_to(cx + 19.5, 1.2)
    cr.line_to(cx + 21, 9.5)
    cr.curve_to(cx + 23, 19, cx + 12, 21, cx, 21)
    cr.curve_to(cx - 12, 21, cx - 23, 19, cx - 21, 9.5)
    cr.close_path()
    cr.stroke()
    # Whiskers
    cr.set_line_width(1)
    cr.set_line_cap(cairo.LINE_CAP_ROUND)
    _rgb(cr, WHITE, 0.55)
    for side in (-1, 1):
        for dy in (-1.5, 1.5):
            cr.move_to(cx + side * 22.5, 13 + dy)
            cr.line_to(cx + side * 28.5, 12 + dy * 2.2)
            cr.stroke()
    # Eyes
    for side in (-1, 1):
        ex, ey = cx + side * 8.5, 11.5
        if mode == "sleep":
            _rgb(cr, WHITE)
            _sleep_eye(cr, ex, ey + 2, 3.6)
        elif mode == "hello":
            _rgb(cr, WHITE)
            _happy_eye(cr, ex, ey + 1, 3.4, 2.0)
        else:
            ry = max(0.9, 4.6 * (1 - blink))
            _rgb(cr, CAT_EYE)
            _ellipse(cr, ex, ey, 4.2, ry)
            cr.fill()
            _rgb(cr, INK)    # the slit pupil
            _ellipse(cr, ex, ey, 1.1, ry * 0.92)
            cr.fill()
    # Nose
    _rgb(cr, BLOB_CHEEK)
    cr.move_to(cx - 1.8, 15.6)
    cr.line_to(cx + 1.8, 15.6)
    cr.line_to(cx, 17.6)
    cr.close_path()
    cr.fill()


def _robot(cr, w, h, mode, blink):
    cx = w / 2
    # Antenna with a lamp
    _rgb(cr, WHITE, 0.8)
    cr.set_line_width(1.4)
    cr.move_to(cx, 4.5)
    cr.line_to(cx, 2.4)
    cr.stroke()
    _rgb(cr, ROBOT_LAMP, 0.35 if mode == "sleep" else 1.0)
    cr.arc(cx, 1.9, 1.7, 0, 2 * math.pi)
    cr.fill()
    # Face plate
    _rgb(cr, WHITE)
    cr.set_line_width(1.6)
    _round_rect(cr, cx - 20, 4.8, 40, 16, 5)
    cr.stroke()
    # Eyes: LED squares
    for side in (-1, 1):
        ex, ey = cx + side * 9, 12.2
        _rgb(cr, ROBOT_EYE, 0.45 if mode == "sleep" else 1.0)
        if mode == "sleep":
            cr.set_line_width(2)
            cr.set_line_cap(cairo.LINE_CAP_ROUND)
            cr.move_to(ex - 3.2, ey + 1)
            cr.line_to(ex + 3.2, ey + 1)
            cr.stroke()
        elif mode == "hello":
            _happy_eye(cr, ex, ey + 1, 3.4, 2.2)
        else:
            eh = max(1.6, 7 * (1 - blink))
            _round_rect(cr, ex - 3.5, ey - eh / 2, 7, eh, 1.8)
            cr.fill()
    # Mouth
    _rgb(cr, WHITE, 0.6)
    cr.set_line_width(1.3)
    cr.set_line_cap(cairo.LINE_CAP_ROUND)
    cr.move_to(cx - 4, 17.6)
    cr.line_to(cx + 4, 17.6)
    cr.stroke()


def _blob(cr, w, h, mode, blink):
    cx, cy = w / 2, h / 2 + 0.5
    _rgb(cr, BLOB_BODY)
    _ellipse(cr, cx, cy, 21, 10)
    cr.fill()
    _rgb(cr, INK)
    for side in (-1, 1):
        ex, ey = cx + side * 8, cy - 1.5
        if mode == "sleep":
            _sleep_eye(cr, ex, ey + 2, 3.2)
        elif mode == "hello":
            _happy_eye(cr, ex, ey, 3.2, 2.0)
            _rgb(cr, BLOB_CHEEK, 0.75)
            _ellipse(cr, ex + side * 4.2, ey + 4.6, 2.4, 1.5)
            cr.fill()
            _rgb(cr, INK)
        else:
            _ellipse(cr, ex, ey, 3.1, max(0.7, 3.4 * (1 - blink)))
            cr.fill()
            if blink < 0.5:
                _rgb(cr, WHITE)
                cr.arc(ex + 1, ey - 1.1, 0.9, 0, 2 * math.pi)
                cr.fill()
                _rgb(cr, INK)
    # Smile
    cr.set_line_width(1.5)
    cr.set_line_cap(cairo.LINE_CAP_ROUND)
    radius = 3.6 if mode == "hello" else 2.6
    cr.arc(cx, cy + 2.2, radius, math.pi * 0.15, math.pi * 0.85)
    cr.stroke()


DRAWERS = {"eyes": _eyes, "cat": _cat, "robot": _robot, "blob": _blob}
