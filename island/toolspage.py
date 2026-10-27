"""The "Werkzeuge" tab: colour picker with its history, keep awake, pinned windows.

Built the first time the tab opens (LazyPage). The island calls the update_*() methods when a service changes,
only for a tab that was built; nothing here ticks – the keep-awake time left is read when the tab opens or the
state changes, not counted down.
"""

from gi.repository import Gdk, Gtk

from island.pages import Page
from island.services import colors
from island.widgets import button, clear, css_class, icon, label

SWATCH = 20


class Swatch(Gtk.EventBox):
    """A small colour square: click copies it, right click pins it."""

    def __init__(self, item, on_copy, on_pin):
        super().__init__(visible_window=False)
        self.item = item
        rgb = colors.from_hex(item["hex"]) or (0, 0, 0)
        self.rgb = rgb
        self.pinned = bool(item.get("pinned"))
        self.set_size_request(SWATCH + 4, SWATCH + 4)
        self.set_tooltip_text(f"{item['hex']} · Klick kopiert · Rechtsklick fixiert"
                              + (" (fixiert)" if self.pinned else ""))
        self.connect("draw", self._on_draw)
        self.connect("button-press-event", lambda _w, e: on_copy(item["hex"]) if e.button == 1
                     else on_pin(item["hex"]) if e.button in (2, 3) else None)
        self.connect("realize", lambda w: w.get_window().set_cursor(
            Gdk.Cursor.new_from_name(w.get_display(), "pointer")))

    def _on_draw(self, _w, cr):
        x = y = 2
        cr.set_source_rgb(*(c / 255 for c in self.rgb))
        _round(cr, x, y, SWATCH, SWATCH, 5)
        cr.fill()
        cr.set_line_width(1.5 if self.pinned else 1)
        cr.set_source_rgba(1, 0.84, 0.04, 1) if self.pinned else cr.set_source_rgba(1, 1, 1, 0.28)
        _round(cr, x, y, SWATCH, SWATCH, 5)
        cr.stroke()
        return False


def _round(cr, x, y, w, h, r):
    cr.new_sub_path()
    cr.arc(x + w - r, y + r, r, -1.5708, 0)
    cr.arc(x + w - r, y + h - r, r, 0, 1.5708)
    cr.arc(x + r, y + h - r, r, 1.5708, 3.1416)
    cr.arc(x + r, y + r, r, 3.1416, 4.7124)
    cr.close_path()


class ToolsPage(Page):
    def __init__(self, island):
        super().__init__(island, spacing=10)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.pack_start(self._picker_card(), False, False, 0)
        box.pack_start(self._awake_card(), False, False, 0)
        box.pack_start(self._pins_card(), False, False, 0)
        scrolled = Gtk.ScrolledWindow(vexpand=True)
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.add(box)
        self.pack_start(scrolled, True, True, 0)
        self.update_colors()
        self.update_awake()
        self.update_pins()

    @staticmethod
    def _card(title, hint):
        card = css_class(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8), "card")
        head = Gtk.Box(spacing=8)
        head.pack_start(label(title, ("title",), ellipsize=False), False, False, 0)
        head.pack_start(label(hint, ("dim", "small")), True, True, 0)
        card.pack_start(head, False, False, 0)
        return card

    # ---- colour picker ---------------------------------------------------------------------------------------
    def _picker_card(self):
        card = self._card("Farbpipette", self.island.hotkey_hint("color-picker"))
        row = Gtk.Box(spacing=10)
        self.pick_button = button("color-select-symbolic", text="Farbe aufnehmen", css=("accent",),
                                  on_click=self.island.pick_color)
        row.pack_start(self.pick_button, False, False, 0)
        self.swatches = Gtk.FlowBox(selection_mode=Gtk.SelectionMode.NONE, max_children_per_line=20,
                                    row_spacing=2, column_spacing=2, valign=Gtk.Align.CENTER, homogeneous=True)
        row.pack_start(self.swatches, True, True, 0)
        card.pack_start(row, False, False, 0)
        return card

    def update_colors(self):
        history = self.island.color_history()
        clear(self.swatches)
        for item in (history.ordered() if history else []):
            self.swatches.add(Swatch(item, self.island.copy_color, self.island.pin_color))
        if not self.swatches.get_children():
            self.swatches.add(label("Noch keine Farben", ("dim", "small"), ellipsize=False))
        self.swatches.show_all()
        self.pick_button.set_sensitive(self.island.config.flag("colorpicker_enabled"))

    # ---- keep awake -------------------------------------------------------------------------------------------
    def _awake_card(self):
        card = self._card("Wach halten", self.island.hotkey_hint("keep-awake"))
        row = Gtk.Box(spacing=10)
        self.awake_switch = Gtk.Switch(valign=Gtk.Align.CENTER)
        self._awake_syncing = False
        self.awake_switch.connect("notify::active", self._on_awake_toggled)
        row.pack_start(self.awake_switch, False, False, 0)
        self.awake_text = label("", ("dim",))
        row.pack_start(self.awake_text, True, True, 0)
        card.pack_start(row, False, False, 0)
        return card

    def _on_awake_toggled(self, switch, _param):
        if self._awake_syncing:
            return
        want = switch.get_active()
        if want != self.island.keepawake_active():
            self.island.toggle_keepawake()

    def update_awake(self):
        enabled = self.island.config.flag("keepawake_enabled")
        active = self.island.keepawake_active()
        self._awake_syncing = True
        self.awake_switch.set_active(active)
        self.awake_switch.set_sensitive(enabled)
        self._awake_syncing = False
        self.awake_text.set_text(self.island.keepawake_text() if enabled else "Aus in den Einstellungen")

    # ---- pinned windows ----------------------------------------------------------------------------------------
    def _pins_card(self):
        card = self._card("Fenster anpinnen", self.island.hotkey_hint("pin-window"))
        self.pin_button = button("view-pin-symbolic", text="Aktives Fenster anpinnen",
                                 on_click=self.island.toggle_pin_active)
        top = Gtk.Box(spacing=10)
        top.pack_start(self.pin_button, False, False, 0)
        self.pin_hint = label("", ("dim", "small"))
        top.pack_start(self.pin_hint, True, True, 0)
        card.pack_start(top, False, False, 0)
        self.pin_list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        card.pack_start(self.pin_list, False, False, 0)
        return card

    def update_pins(self):
        enabled = self.island.config.flag("pin_enabled")
        self.pin_button.set_sensitive(enabled)
        windows = self.island.pinned_windows() if enabled else []
        clear(self.pin_list)
        self.pin_hint.set_text("" if enabled else "Aus in den Einstellungen")
        for window in windows:
            row = Gtk.Box(spacing=8)
            row.pack_start(icon("view-pin-symbolic", 14), False, False, 0)
            row.pack_start(label(window.get_name() or "Fenster", max_chars=60), True, True, 0)
            row.pack_end(button(text="Aufheben", css=("mini",),
                                on_click=lambda w=window: self.island.unpin_window(w)), False, False, 0)
            self.pin_list.pack_start(row, False, False, 0)
        if enabled and not windows:
            self.pin_list.pack_start(label("Kein Fenster angepinnt – zuerst ein Fenster anklicken, dann hier oder "
                                           "mit dem Hotkey anpinnen", ("dim", "small")), False, False, 0)
        self.pin_list.show_all()

    def on_show(self):
        self.update_awake()
        self.update_pins()
