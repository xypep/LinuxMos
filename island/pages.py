"""The tabs of the opened island: Now, Clipboard, Shelf, Note & Timer, Weather, Controls."""

import time

from gi.repository import Gdk, GdkPixbuf, Gio, GLib, Gtk, Pango

from island.services import art, system
from island.services.timer import format_seconds
from island.storage import DATA_DIR
from island.widgets import (button, clear, css_class, icon, label, placeholder_cover,
                            rounded_image)

URI_TARGETS = [Gtk.TargetEntry.new("text/uri-list", 0, 0)]


def _fmt_us(us):
    return format_seconds(max(0, us) // 1_000_000)


class Page(Gtk.Box):
    def __init__(self, island, spacing=10):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=spacing)
        self.island = island

    def on_show(self):
        """Called every time the tab becomes visible on the opened island."""


# =============================================================================
# Now: music, weather, timer, battery
# =============================================================================
class HomePage(Page):
    COVER = 72

    def __init__(self, island):
        super().__init__(island, spacing=12)
        media = island.media

        # ---- now playing --------------------------------------------------
        self.cover_slot = Gtk.Box()
        self.title = label("", ("title",), max_chars=40)
        self.artist = label("", ("dim",), max_chars=40)
        self.progress = Gtk.ProgressBar(valign=Gtk.Align.CENTER)
        self.elapsed = label("0:00", ("dim", "small"), ellipsize=False)
        self.length = label("", ("dim", "small"), xalign=1.0, ellipsize=False)
        times = Gtk.Box()
        times.pack_start(self.elapsed, True, True, 0)
        times.pack_end(self.length, False, False, 0)

        info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3, valign=Gtk.Align.CENTER)
        for w in (self.title, self.artist, self.progress, times):
            info.pack_start(w, False, False, 0)

        self.prev_btn = button("media-skip-backward-symbolic", css=("circle",), size=18, on_click=media.previous)
        self.play_btn = button("media-playback-start-symbolic", css=("circle", "big"), size=22,
                               on_click=media.play_pause)
        self.next_btn = button("media-skip-forward-symbolic", css=("circle",), size=18, on_click=media.next)
        controls = Gtk.Box(spacing=6, valign=Gtk.Align.CENTER)
        for b in (self.prev_btn, self.play_btn, self.next_btn):
            controls.pack_start(b, False, False, 0)

        card = css_class(Gtk.Box(spacing=14), "card")
        card.pack_start(self.cover_slot, False, False, 0)
        card.pack_start(info, True, True, 0)
        card.pack_end(controls, False, False, 0)

        empty = css_class(Gtk.Box(spacing=14), "card")
        empty.pack_start(placeholder_cover(self.COVER), False, False, 0)
        empty_text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3, valign=Gtk.Align.CENTER)
        empty_text.pack_start(label("Gerade läuft nichts", ("title",)), False, False, 0)
        empty_text.pack_start(label("Spotify, Firefox, VLC & Co. erscheinen hier automatisch", ("dim",)),
                              False, False, 0)
        empty.pack_start(empty_text, True, True, 0)

        # "empty" first: it is what shows until a player appears
        self.media_stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.CROSSFADE)
        self.media_stack.add_named(empty, "empty")
        self.media_stack.add_named(card, "media")
        self.pack_start(self.media_stack, False, False, 0)

        # ---- tiles ----------------------------------------------------------
        tiles = Gtk.Box(spacing=12, homogeneous=True)
        self.weather_tile = self._tile("weather-few-clouds-symbolic", "–", "Wetter", "weather")
        self.timer_tile = self._tile("alarm-symbolic", "Timer", "Kein Timer", "note")
        # Desktop PCs have no battery: the tile then leads to the controls
        self.battery_tile = self._tile("emblem-system-symbolic", "Steuerung", "WLAN, Ton, Theme", "controls")
        for t in (self.weather_tile, self.timer_tile, self.battery_tile):
            tiles.pack_start(t["button"], True, True, 0)
        self.pack_start(tiles, True, True, 0)
        self._art_url = None

    def _tile(self, icon_name, value, caption, tab):
        img = icon(icon_name, 22)
        val = label(value, ("big-value",), ellipsize=True)
        cap = label(caption, ("dim", "small"))
        text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, valign=Gtk.Align.CENTER)
        text.pack_start(val, False, False, 0)
        text.pack_start(cap, False, False, 0)
        box = Gtk.Box(spacing=10)
        box.pack_start(img, False, False, 0)
        box.pack_start(text, True, True, 0)
        btn = css_class(Gtk.Button(), "card", "tile-button")
        btn.set_can_focus(False)
        btn.add(box)
        btn.connect("clicked", lambda *_: self.island.select_tab(tab))
        return {"button": btn, "icon": img, "value": val, "caption": cap}

    @staticmethod
    def _set_tile(tile, icon_name, value, caption):
        tile["icon"].set_from_icon_name(icon_name, Gtk.IconSize.MENU)
        tile["value"].set_text(value)
        tile["caption"].set_text(caption)

    # ---- updates -------------------------------------------------------------
    def update_media(self, track):
        if not track:
            self.media_stack.set_visible_child_name("empty")
            return
        self.media_stack.set_visible_child_name("media")
        self.title.set_text(track.title or "Unbekannter Titel")
        self.artist.set_text(track.artist or track.bus_name.rsplit(".", 1)[-1].capitalize())
        self.play_btn.get_child().set_from_icon_name(
            "media-playback-pause-symbolic" if track.playing else "media-playback-start-symbolic",
            Gtk.IconSize.MENU)
        self.prev_btn.set_sensitive(track.can_previous)
        self.next_btn.set_sensitive(track.can_next)
        self.length.set_text(_fmt_us(track.length_us) if track.length_us else "")
        self.progress.set_visible(bool(track.length_us))
        if track.art_url != self._art_url or not self.cover_slot.get_children():
            self._art_url = track.art_url
            clear(self.cover_slot)
            self.cover_slot.add(placeholder_cover(self.COVER))
            self.cover_slot.show_all()
            art.load(track.art_url, self.COVER * 2, self._on_cover)

    def _on_cover(self, pixbuf):
        if pixbuf is None:
            return
        clear(self.cover_slot)
        self.cover_slot.add(rounded_image(pixbuf, self.COVER, 12, self.get_scale_factor()))
        self.cover_slot.show_all()

    def set_position(self, position_us):
        track = self.island.track
        if position_us is None or not track or not track.length_us:
            return
        self.elapsed.set_text(_fmt_us(position_us))
        self.progress.set_fraction(min(1.0, position_us / track.length_us))

    def update_weather(self, weather):
        if weather.current:
            c = weather.current
            self._set_tile(self.weather_tile, c["icon"], f"{c['temp']}°", f"{c['text']} · {c['city']}")
        else:
            caption = "Ort festlegen" if not weather.configured else "nicht verfügbar"
            self._set_tile(self.weather_tile, "weather-few-clouds-symbolic", "–", caption)

    def update_timer(self, timer):
        if timer.running:
            self._set_tile(self.timer_tile, "alarm-symbolic", format_seconds(timer.remaining), "läuft")
        else:
            self._set_tile(self.timer_tile, "alarm-symbolic", "Timer", "Kein Timer")

    def update_battery(self, battery):
        if battery.present:
            self._set_tile(self.battery_tile, battery.icon_name, f"{battery.percentage} %",
                           "Lädt" if battery.plugged else "Akku")
        else:
            self._set_tile(self.battery_tile, "emblem-system-symbolic", "Steuerung", "WLAN, Ton, Theme")


# =============================================================================
# Clipboard history
# =============================================================================
class ClipboardPage(Page):
    def __init__(self, island):
        super().__init__(island)
        self.search = Gtk.SearchEntry(placeholder_text="Verlauf durchsuchen …", hexpand=True)
        island.make_typeable(self.search)
        self.search.connect("search-changed", lambda *_: self.listbox.invalidate_filter())
        self.search.connect("activate", lambda *_: self._paste_first())
        self.search.connect("key-press-event", self._on_search_key)

        top = Gtk.Box(spacing=8)
        top.pack_start(self.search, True, True, 0)
        top.pack_start(button("edit-clear-all-symbolic", tooltip="Verlauf leeren (Angepinntes bleibt)",
                              on_click=island.clipboard.clear), False, False, 0)
        self.pack_start(top, False, False, 0)

        self.listbox = Gtk.ListBox(selection_mode=Gtk.SelectionMode.BROWSE)
        self.listbox.set_activate_on_single_click(True)
        self.listbox.set_filter_func(self._filter)
        self.listbox.connect("row-activated", lambda _lb, row: island.paste(row.item))
        placeholder = label("Noch nichts kopiert – alles, was du kopierst, landet hier.", ("dim",), xalign=0.5)
        placeholder.show()
        self.listbox.set_placeholder(placeholder)

        scrolled = Gtk.ScrolledWindow(vexpand=True)
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.add(self.listbox)
        self.pack_start(scrolled, True, True, 0)
        self._dirty = True

    def mark_dirty(self):
        self._dirty = True
        if self.get_mapped():
            self.rebuild()

    def on_show(self):
        if self._dirty:
            self.rebuild()

    def rebuild(self):
        self._dirty = False
        clear(self.listbox)
        items = sorted(self.island.clipboard.items, key=lambda i: (not i.get("pinned"), -i.get("time", 0)))
        for item in items:
            self.listbox.add(self._row(item))
        self.listbox.show_all()

    def _row(self, item):
        row = Gtk.ListBoxRow()
        row.item = item
        box = Gtk.Box(spacing=10)
        if item["kind"] == "image":
            try:
                pix = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                    str(self.island.clipboard.image_path(item)), 120, 40, True)
                box.pack_start(Gtk.Image.new_from_pixbuf(pix), False, False, 0)
            except GLib.Error:
                pass
            w, h = item.get("size", (0, 0))
            box.pack_start(label(f"Bild · {w}×{h}", ("dim",)), True, True, 0)
        else:
            text = " ⏎ ".join(line.strip() for line in item["text"].strip().splitlines()[:3])
            box.pack_start(label(text[:300], max_chars=60), True, True, 0)

        stamp = time.localtime(item.get("time", 0))
        today = time.localtime()
        when = time.strftime("%H:%M" if stamp[:3] == today[:3] else "%d.%m.", stamp)
        box.pack_start(label(when, ("dim", "small"), ellipsize=False), False, False, 0)
        pin = button("view-pin-symbolic", tooltip="Anpinnen", css=("mini",) + (("pinned",) if item.get("pinned") else ()),
                     size=14, on_click=lambda: self.island.clipboard.toggle_pin(item))
        remove = button("window-close-symbolic", tooltip="Entfernen", css=("mini",), size=14,
                        on_click=lambda: self.island.clipboard.remove(item))
        box.pack_start(pin, False, False, 0)
        box.pack_start(remove, False, False, 0)
        row.add(box)
        return row

    def _filter(self, row):
        query = self.search.get_text().strip().lower()
        if not query:
            return True
        return row.item["kind"] == "text" and query in row.item["text"].lower()

    def _visible_rows(self):
        return [r for r in self.listbox.get_children() if r.get_child_visible()]

    def _paste_first(self):
        rows = self._visible_rows()
        if rows:
            self.island.paste(rows[0].item)

    def _on_search_key(self, _entry, event):
        if event.keyval == Gdk.KEY_Down:
            rows = self._visible_rows()
            if rows:
                self.listbox.select_row(rows[0])
                rows[0].grab_focus()
            return True
        return False

    def focus_search(self):
        self.search.grab_focus()


# =============================================================================
# Shelf
# =============================================================================
class ShelfPage(Page):
    def __init__(self, island):
        super().__init__(island)
        self.count = label("", ("dim",))
        header = Gtk.Box(spacing=8)
        header.pack_start(label("Ablage", ("title",), ellipsize=False), False, False, 0)
        header.pack_start(self.count, True, True, 0)

        # Drag source for all files at once
        self.drag_all = css_class(Gtk.EventBox(), "drag-all")
        self.drag_all.set_no_show_all(True)
        drag_box = Gtk.Box(spacing=6)
        drag_box.pack_start(icon("edit-select-all-symbolic", 14), False, False, 0)
        drag_box.pack_start(label("Alle ziehen", ellipsize=False), False, False, 0)
        self.drag_all.add(drag_box)
        drag_box.show_all()
        self._make_drag_source(self.drag_all, lambda: list(island.shelf.uris), "folder-documents")
        header.pack_end(button("edit-clear-all-symbolic", tooltip="Ablage leeren", on_click=island.shelf.clear),
                        False, False, 0)
        header.pack_end(self.drag_all, False, False, 0)
        self.pack_start(header, False, False, 0)

        self.flow = Gtk.FlowBox(selection_mode=Gtk.SelectionMode.NONE, max_children_per_line=6,
                                min_children_per_line=6, homogeneous=True, row_spacing=6, column_spacing=6,
                                valign=Gtk.Align.START)
        scrolled = Gtk.ScrolledWindow(vexpand=True)
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.add(self.flow)

        empty = css_class(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8, valign=Gtk.Align.CENTER),
                          "dropzone")
        empty.pack_start(icon("document-send-symbolic", 36), False, False, 0)
        empty.pack_start(label("Dateien auf die Insel ziehen", ("title",), xalign=0.5), False, False, 0)
        empty.pack_start(label("Sie warten hier, bis du sie woanders hinziehst.", ("dim",), xalign=0.5),
                         False, False, 0)

        self.stack = Gtk.Stack(vexpand=True, transition_type=Gtk.StackTransitionType.CROSSFADE)
        self.stack.add_named(scrolled, "files")
        self.stack.add_named(empty, "empty")
        self.pack_start(self.stack, True, True, 0)
        self.rebuild()

    def _make_drag_source(self, widget, get_uris, icon_name):
        widget.drag_source_set(Gdk.ModifierType.BUTTON1_MASK, URI_TARGETS,
                               Gdk.DragAction.COPY | Gdk.DragAction.MOVE)
        widget.drag_source_set_icon_name(icon_name)
        widget.connect("drag-begin", lambda *_: self.island.set_dragging_out(True))
        widget.connect("drag-end", lambda *_: self.island.set_dragging_out(False))
        widget.connect("drag-data-get", lambda _w, _ctx, data, _info, _t: data.set_uris(get_uris()))

    def rebuild(self):
        clear(self.flow)
        uris = self.island.shelf.uris
        n = len(uris)
        self.count.set_text(f"{n} Datei{'en' if n != 1 else ''}" if n else "")
        for uri in uris:
            self.flow.add(self._tile(uri))
        self.flow.show_all()
        self.drag_all.set_visible(n > 1)
        self.stack.set_visible_child_name("files" if uris else "empty")

    def _tile(self, uri):
        gfile = Gio.File.new_for_uri(uri)
        name, gicon, thumb = gfile.get_basename(), None, None
        try:
            info = gfile.query_info("standard::display-name,standard::icon,thumbnail::path",
                                    Gio.FileQueryInfoFlags.NONE, None)
            name = info.get_display_name()
            gicon = info.get_icon()
            thumb = info.get_attribute_byte_string("thumbnail::path")
        except GLib.Error:
            pass

        if thumb:
            try:
                img = Gtk.Image.new_from_pixbuf(GdkPixbuf.Pixbuf.new_from_file_at_scale(thumb, 48, 48, True))
            except GLib.Error:
                thumb = None
        if not thumb:
            img = Gtk.Image.new_from_gicon(gicon, Gtk.IconSize.DIALOG) if gicon else icon("text-x-generic", 48)
            img.set_pixel_size(48)

        name_lbl = label(name, ("small",), xalign=0.5, max_chars=12)
        name_lbl.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.pack_start(img, False, False, 0)
        box.pack_start(name_lbl, False, False, 0)

        event = css_class(Gtk.EventBox(), "shelf-tile")
        event.set_tooltip_text(f"{name}\nZiehen zum Ablegen · Doppelklick öffnet")
        event.add(box)
        self._make_drag_source(event, lambda: [uri], "text-x-generic")
        if gicon:
            event.drag_source_set_icon_gicon(gicon)
        event.connect("button-press-event", self._on_tile_press, uri)

        remove = button("window-close-symbolic", tooltip="Aus der Ablage entfernen", css=("mini", "tile-close"),
                        size=12, on_click=lambda: self.island.shelf.remove(uri))
        remove.set_halign(Gtk.Align.END)
        remove.set_valign(Gtk.Align.START)
        overlay = Gtk.Overlay()
        overlay.add(event)
        overlay.add_overlay(remove)
        return overlay

    def _on_tile_press(self, _widget, event, uri):
        if event.type == Gdk.EventType._2BUTTON_PRESS:
            try:
                Gio.AppInfo.launch_default_for_uri(uri, None)
            except GLib.Error:
                pass
            self.island.collapse()
            return True
        return False


# =============================================================================
# Note & timer
# =============================================================================
NOTE_FILE = DATA_DIR / "note.txt"


class NotePage(Page):
    PRESETS = [(1, "1 min"), (5, "5 min"), (10, "10 min"), (25, "25 min")]

    def __init__(self, island):
        super().__init__(island)
        row = Gtk.Box(spacing=12)
        self.pack_start(row, True, True, 0)

        # ---- note -----------------------------------------------------------
        self.text = Gtk.TextView(wrap_mode=Gtk.WrapMode.WORD_CHAR, left_margin=10, right_margin=10,
                                 top_margin=8, bottom_margin=8)
        island.make_typeable(self.text)
        try:
            self.text.get_buffer().set_text(NOTE_FILE.read_text(encoding="utf-8"))
        except OSError:
            self.text.get_buffer().set_text("")
        self.text.get_buffer().connect("changed", self._on_note_changed)
        self._save_id = 0
        note_scroll = css_class(Gtk.ScrolledWindow(hexpand=True), "note")
        note_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        note_scroll.add(self.text)
        note_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        note_box.pack_start(label("Notiz", ("title",)), False, False, 0)
        note_box.pack_start(note_scroll, True, True, 0)
        row.pack_start(note_box, True, True, 0)

        # ---- timer ----------------------------------------------------------
        timer_box = css_class(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8), "card")
        timer_box.set_size_request(220, -1)
        timer_box.pack_start(label("Timer", ("title",)), False, False, 0)
        self.remaining = label("00:00", ("timer-display", "dim"), xalign=0.5, ellipsize=False)
        timer_box.pack_start(self.remaining, False, False, 0)

        presets = Gtk.Grid(column_spacing=6, row_spacing=6, column_homogeneous=True)
        for i, (minutes, text) in enumerate(self.PRESETS):
            presets.attach(button(text=text, on_click=lambda m=minutes: island.timer.start(m * 60)), i % 2, i // 2, 1, 1)
        timer_box.pack_start(presets, False, False, 0)

        custom = Gtk.Box(spacing=6)
        self.spin = Gtk.SpinButton.new_with_range(1, 600, 1)
        self.spin.set_value(15)
        island.make_typeable(self.spin)
        custom.pack_start(self.spin, True, True, 0)
        custom.pack_start(label("min", ("dim",), ellipsize=False), False, False, 0)
        custom.pack_start(button(text="Start", css=("accent",),
                                 on_click=lambda: island.timer.start(int(self.spin.get_value()) * 60)),
                          False, False, 0)
        timer_box.pack_start(custom, False, False, 0)
        self.stop_btn = button("media-playback-stop-symbolic", "Stoppen", on_click=island.timer.cancel)
        self.stop_btn.get_child().show_all()
        self.stop_btn.set_no_show_all(True)
        timer_box.pack_end(self.stop_btn, False, False, 0)
        row.pack_start(timer_box, False, False, 0)

    def _on_note_changed(self, _buffer):
        if self._save_id:
            GLib.source_remove(self._save_id)
        self._save_id = GLib.timeout_add(800, self._save_note)

    def _save_note(self):
        self._save_id = 0
        buf = self.text.get_buffer()
        NOTE_FILE.parent.mkdir(parents=True, exist_ok=True)
        NOTE_FILE.write_text(buf.get_text(buf.get_start_iter(), buf.get_end_iter(), True), encoding="utf-8")
        return GLib.SOURCE_REMOVE

    def flush(self):
        if self._save_id:
            GLib.source_remove(self._save_id)
            self._save_note()

    def update_timer(self, timer):
        self.remaining.set_text(format_seconds(timer.remaining) if timer.running else "00:00")
        ctx = self.remaining.get_style_context()
        (ctx.remove_class if timer.running else ctx.add_class)("dim")
        self.stop_btn.set_visible(timer.running)


# =============================================================================
# Weather
# =============================================================================
class WeatherPage(Page):
    def __init__(self, island):
        super().__init__(island)
        self.stack = Gtk.Stack(vexpand=True, transition_type=Gtk.StackTransitionType.CROSSFADE)
        self.pack_start(self.stack, True, True, 0)

        # ---- setup ------------------------------------------------------------
        setup = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10, valign=Gtk.Align.CENTER)
        setup.pack_start(icon("weather-few-clouds-symbolic", 40), False, False, 0)
        setup.pack_start(label("Für welchen Ort soll das Wetter angezeigt werden?", ("title",), xalign=0.5),
                         False, False, 0)
        self.city_entry = Gtk.Entry(placeholder_text="z. B. Berlin", width_chars=24, halign=Gtk.Align.CENTER)
        island.make_typeable(self.city_entry)
        self.city_entry.connect("activate", lambda *_: self._save_city())
        entry_row = Gtk.Box(spacing=8, halign=Gtk.Align.CENTER)
        entry_row.pack_start(self.city_entry, False, False, 0)
        entry_row.pack_start(button(text="Speichern", css=("accent",), on_click=self._save_city), False, False, 0)
        setup.pack_start(entry_row, False, False, 0)
        setup.pack_start(label("Vorhersage: MET Norway · Ortssuche: OpenStreetMap · kein Konto nötig",
                               ("dim", "small"), xalign=0.5), False, False, 0)
        self.stack.add_named(setup, "setup")

        # ---- forecast ---------------------------------------------------------
        data = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        top = Gtk.Box(spacing=14)
        self.now_icon = icon("weather-clear-symbolic", 44)
        self.now_temp = label("–", ("huge",), ellipsize=False)
        self.now_text = label("", ("title",))
        self.now_city = label("", ("dim",))
        desc = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, valign=Gtk.Align.CENTER)
        desc.pack_start(self.now_text, False, False, 0)
        desc.pack_start(self.now_city, False, False, 0)
        top.pack_start(self.now_icon, False, False, 0)
        top.pack_start(self.now_temp, False, False, 0)
        top.pack_start(desc, True, True, 0)
        top.pack_end(button("document-edit-symbolic", tooltip="Ort ändern", on_click=self._edit_city), False, False, 0)
        top.pack_end(button("view-refresh-symbolic", tooltip="Aktualisieren", on_click=island.weather.refresh),
                     False, False, 0)
        data.pack_start(top, False, False, 0)

        self.hourly = css_class(Gtk.Box(homogeneous=True), "card")
        self.daily = css_class(Gtk.Box(homogeneous=True), "card")
        data.pack_start(self.hourly, False, False, 0)
        data.pack_start(self.daily, False, False, 0)
        self.status = label("", ("dim", "small"), xalign=1.0)
        data.pack_end(self.status, False, False, 0)
        self.stack.add_named(data, "data")

    def _save_city(self):
        city = self.city_entry.get_text().strip()
        if city:
            self.island.weather.set_city(city)
            self.status.set_text("Lade Wetter …")
            self.stack.set_visible_child_name("data")

    def _edit_city(self):
        self.city_entry.set_text(self.island.config.get("city", ""))
        self.stack.set_visible_child_name("setup")
        self.island.request_focus()
        self.city_entry.grab_focus()

    @staticmethod
    def _column(top, icon_name, bottom):
        col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        col.pack_start(label(top, ("dim", "small"), xalign=0.5, ellipsize=False), False, False, 0)
        col.pack_start(icon(icon_name, 20), False, False, 0)
        col.pack_start(label(bottom, ("small",), xalign=0.5, ellipsize=False), False, False, 0)
        return col

    def update(self, weather):
        if not weather.configured:
            self.stack.set_visible_child_name("setup")
            return
        if self.stack.get_visible_child_name() == "setup" and not self.island.is_active():
            self.stack.set_visible_child_name("data")
        if weather.current:
            c = weather.current
            self.now_icon.set_from_icon_name(c["icon"], Gtk.IconSize.MENU)
            self.now_temp.set_text(f"{c['temp']}°")
            self.now_text.set_text(c["text"])
            self.now_city.set_text(c["city"])
            clear(self.hourly)
            for h in weather.hourly:
                self.hourly.pack_start(self._column(f"{h['time']} Uhr", h["icon"], f"{h['temp']}°"), True, True, 0)
            clear(self.daily)
            for d in weather.daily:
                self.daily.pack_start(self._column(d["day"], d["icon"], f"{d['max']}° / {d['min']}°"), True, True, 0)
            self.hourly.show_all()
            self.daily.show_all()
            self.status.set_text("Daten: MET Norway (CC BY 4.0)")
        elif weather.error:
            self.now_text.set_text("Wetter nicht verfügbar")
            self.now_city.set_text(weather.config.get("city", ""))
            self.status.set_text(weather.error[:80])


# =============================================================================
# Controls
# =============================================================================
class ControlsPage(Page):
    def __init__(self, island):
        super().__init__(island, spacing=12)
        self._syncing = False
        self._armed = {}

        # ---- toggles ----------------------------------------------------------
        grid = Gtk.Box(spacing=8, homogeneous=True)
        self.toggles = {
            "wifi": self._toggle(grid, "network-wireless-symbolic", "WLAN", lambda on: system.wifi_set(on, self._later)),
            "bluetooth": self._toggle(grid, "bluetooth-active-symbolic", "Bluetooth",
                                      lambda on: system.bluetooth_set(on, self._later)),
            "dnd": self._toggle(grid, "notifications-disabled-symbolic", "Nicht stören", system.dnd_set),
            "dark": self._toggle(grid, "weather-clear-night-symbolic", "Dark Mode", system.dark_set),
            "mic": self._toggle(grid, "microphone-sensitivity-muted-symbolic", "Mikro aus",
                                lambda on: system.mic_mute_set(on, self._later)),
        }
        self.pack_start(grid, False, False, 0)

        # ---- sliders ----------------------------------------------------------
        sliders = css_class(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6), "card")
        self.volume = self._slider(sliders, "audio-volume-high-symbolic", lambda v: system.volume_set(v))
        self.brightness_row = Gtk.Box()
        self.brightness = self._slider(sliders, "display-brightness-symbolic", system.brightness_set,
                                       row=self.brightness_row)
        self.pack_start(sliders, False, False, 0)

        # ---- actions ----------------------------------------------------------
        actions = Gtk.Box(spacing=8, homogeneous=True)
        actions.pack_start(button("camera-photo-symbolic", "Screenshot", on_click=self._screenshot), True, True, 0)
        actions.pack_start(button("system-lock-screen-symbolic", "Sperren",
                                  on_click=lambda: (island.collapse(), system.lock())), True, True, 0)
        for key, icon_name, text, action in (
                ("suspend", "weather-clear-night-symbolic", "Ruhezustand", system.suspend),
                ("reboot", "system-reboot-symbolic", "Neustart", system.reboot),
                ("poweroff", "system-shutdown-symbolic", "Aus", system.poweroff)):
            btn = button(icon_name, text)
            btn.connect("clicked", self._on_dangerous, key, text, action)
            actions.pack_start(btn, True, True, 0)
        self.pack_start(actions, False, False, 0)

    def _toggle(self, parent, icon_name, text, setter):
        btn = css_class(Gtk.ToggleButton(), "tile")
        btn.set_can_focus(False)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.pack_start(icon(icon_name, 20), False, False, 0)
        box.pack_start(label(text, ("small",), xalign=0.5), False, False, 0)
        btn.add(box)
        btn.connect("toggled", lambda b: None if self._syncing else setter(b.get_active()))
        parent.pack_start(btn, True, True, 0)
        return btn

    def _slider(self, parent, icon_name, setter, row=None):
        row = row or Gtk.Box()
        row.set_spacing(10)
        scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        scale.set_draw_value(False)
        scale.set_can_focus(False)
        pending = {"id": 0}

        def apply():
            pending["id"] = 0
            setter(scale.get_value())
            return GLib.SOURCE_REMOVE

        def changed(_scale):
            if self._syncing:
                return
            # Debounce: dragging the slider fires dozens of events per second
            if pending["id"]:
                GLib.source_remove(pending["id"])
            pending["id"] = GLib.timeout_add(60, apply)

        scale.connect("value-changed", changed)
        row.pack_start(icon(icon_name, 16), False, False, 0)
        row.pack_start(scale, True, True, 0)
        parent.pack_start(row, False, False, 0)
        return scale

    def _set_toggle(self, key, value):
        btn = self.toggles[key]
        self._syncing = True
        btn.set_sensitive(value is not None)
        btn.set_active(bool(value))
        self._syncing = False

    def _set_scale(self, scale, value):
        self._syncing = True
        if value is not None:
            scale.set_value(value)
        self._syncing = False

    def _later(self, *_):
        """Re-read the real state shortly after a change (nmcli & co. are asynchronous)."""
        def refresh():
            self.on_show()
            return GLib.SOURCE_REMOVE

        GLib.timeout_add(700, refresh)

    def on_show(self):
        system.wifi_get(lambda v: self._set_toggle("wifi", v))
        system.bluetooth_get(lambda v: self._set_toggle("bluetooth", v))
        system.mic_muted_get(lambda v: self._set_toggle("mic", v))
        self._set_toggle("dnd", system.dnd_get())
        self._set_toggle("dark", system.dark_get())
        system.volume_get(lambda v: self._set_scale(self.volume, v))

        def brightness(v):
            self.brightness_row.set_visible(v is not None)
            self._set_scale(self.brightness, v)

        system.brightness_get(brightness)

    def _screenshot(self):
        self.island.collapse()
        def shoot():
            system.screenshot_area()
            return GLib.SOURCE_REMOVE

        # Let the island fold away before the selection starts
        GLib.timeout_add(350, shoot)

    def _on_dangerous(self, btn, key, text, action):
        """Sleep, restart and shut down have to be clicked twice."""
        if key in self._armed:
            GLib.source_remove(self._armed.pop(key))
            self.island.collapse()
            action()
            return
        box = btn.get_child()
        box.get_children()[-1].set_text("Nochmal?")
        css_class(btn, "danger")

        def disarm():
            self._armed.pop(key, None)
            box.get_children()[-1].set_text(text)
            btn.get_style_context().remove_class("danger")
            return GLib.SOURCE_REMOVE

        self._armed[key] = GLib.timeout_add_seconds(3, disarm)
