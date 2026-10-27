"""The tabs of the opened island: Now, Clipboard, Shelf, To-do, Note & Focus, Water, Stretch, Weather, Controls."""

import time
from datetime import datetime, timedelta

from gi.repository import Gdk, GdkPixbuf, Gio, GLib, Gtk, Pango

from island.i18n import _, day_month, decimal, n_
from island.services import art, system
from island.services.timer import format_seconds
from island.services.todo import parse_due
from island.storage import DATA_DIR
from island.widgets import (BarChart, button, clear, css_class, icon, label, placeholder_cover,
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


class LazyPage(Page):
    """A tab whose content is built the first time it is needed (start-up time and memory).

    The factory gets the island (a Page class fits) and reads the services' state while building,
    so the island only forwards service updates to pages that are built (IslandWindow._built).
    """

    def __init__(self, island, factory):
        super().__init__(island, spacing=0)
        self._factory = factory
        self._page = None

    @property
    def built(self):
        return self._page is not None

    @property
    def page(self):
        if self._page is None:
            self._page = self._factory(self.island)
            self.pack_start(self._page, True, True, 0)
            self._page.show_all()
        return self._page

    def on_show(self):
        self.page.on_show()


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
        # Click on the bar to seek
        seek = Gtk.EventBox()
        seek.add(self.progress)
        seek.connect("button-press-event", self._on_seek)
        self.elapsed = label("0:00", ("dim", "small"), ellipsize=False)
        self.length = label("", ("dim", "small"), xalign=1.0, ellipsize=False)
        times = Gtk.Box()
        times.pack_start(self.elapsed, True, True, 0)
        times.pack_end(self.length, False, False, 0)

        info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3, valign=Gtk.Align.CENTER)
        for w in (self.title, self.artist, seek, times):
            info.pack_start(w, False, False, 0)

        self.prev_btn = button("media-skip-backward-symbolic", css=("circle",), size=18, on_click=media.previous)
        self.play_btn = button("media-playback-start-symbolic", css=("circle", "big"), size=22,
                               on_click=media.play_pause)
        self.next_btn = button("media-skip-forward-symbolic", css=("circle",), size=18, on_click=media.next)
        self.lyrics_btn = css_class(Gtk.ToggleButton(), "circle")
        self.lyrics_btn.set_can_focus(False)
        self.lyrics_btn.add(icon("media-view-subtitles-symbolic", 16))
        self.lyrics_btn.set_tooltip_text("Lyrics")
        self.lyrics_btn.connect("toggled", lambda b: island.set_lyrics_view(b.get_active()))
        controls = Gtk.Box(spacing=6, valign=Gtk.Align.CENTER)
        for b in (self.lyrics_btn, self.prev_btn, self.play_btn, self.next_btn):
            controls.pack_start(b, False, False, 0)

        card = css_class(Gtk.Box(spacing=14), "card")
        card.pack_start(self.cover_slot, False, False, 0)
        card.pack_start(info, True, True, 0)
        card.pack_end(controls, False, False, 0)

        empty = css_class(Gtk.Box(spacing=14), "card")
        empty.pack_start(placeholder_cover(self.COVER), False, False, 0)
        empty_text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3, valign=Gtk.Align.CENTER)
        empty_text.pack_start(label(_("Gerade läuft nichts"), ("title",)), False, False, 0)
        empty_text.pack_start(label(_("Spotify, Firefox, VLC & Co. erscheinen hier automatisch"), ("dim",)),
                              False, False, 0)
        empty.pack_start(empty_text, True, True, 0)

        # "empty" first: it is what shows until a player appears
        self.media_stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.CROSSFADE)
        self.media_stack.add_named(empty, "empty")
        self.media_stack.add_named(card, "media")
        self.pack_start(self.media_stack, False, False, 0)

        # ---- tiles ----------------------------------------------------------
        tiles = Gtk.Box(spacing=12, homogeneous=True)
        self.weather_tile = self._tile("weather-few-clouds-symbolic", "–", _("Wetter"), "weather")
        self.timer_tile = self._tile("alarm-symbolic", _("Timer"), _("Kein Timer"), "note")
        # Desktop PCs have no battery: the tile then leads to the controls
        self.battery_tile = self._tile("emblem-system-symbolic", _("Steuerung"), _("WLAN, Ton, Theme"), "controls")
        for t in (self.weather_tile, self.timer_tile, self.battery_tile):
            tiles.pack_start(t["button"], True, True, 0)

        # ---- lyrics (replaces the tiles while the lyrics button is on) ------
        self.lyrics_list = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
        self.lyrics_list.set_activate_on_single_click(True)
        self.lyrics_list.connect("row-activated", self._on_lyric_clicked)
        self.lyrics_scroll = Gtk.ScrolledWindow(vexpand=True)
        self.lyrics_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.lyrics_scroll.add(self.lyrics_list)
        self.lyrics_status = label("", ("dim",), xalign=0.5)
        in_pill = Gtk.CheckButton(label=_("Aktuelle Zeile in der Pille zeigen"))
        in_pill.set_can_focus(False)
        in_pill.set_active(bool(island.config.get("lyrics_in_pill")))
        in_pill.connect("toggled", lambda b: island.set_option("lyrics_in_pill", b.get_active()))
        lyrics_footer = Gtk.Box(spacing=8)
        lyrics_footer.pack_start(in_pill, False, False, 0)
        lyrics_footer.pack_end(label("Lyrics: LRCLIB", ("dim", "small"), ellipsize=False), False, False, 0)
        lyrics_box = css_class(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6), "card")
        lyrics_box.pack_start(self.lyrics_status, False, False, 0)
        lyrics_box.pack_start(self.lyrics_scroll, True, True, 0)
        lyrics_box.pack_end(lyrics_footer, False, False, 0)
        self.lyrics_status.set_no_show_all(True)

        self.lower = Gtk.Stack(transition_type=Gtk.StackTransitionType.CROSSFADE, vexpand=True)
        self.lower.add_named(tiles, "tiles")
        self.lower.add_named(lyrics_box, "lyrics")
        self.pack_start(self.lower, True, True, 0)
        self._art_url = None
        self._lyric_rows = []
        self._lyric_idx = -1

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
        self.title.set_text(track.title or _("Unbekannter Titel"))
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
            art.load(track.art_url, self._on_cover)

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

    def _on_seek(self, widget, event):
        track = self.island.track
        width = widget.get_allocated_width()
        if track and track.length_us and width > 0:
            self.island.media.set_position(track.length_us * max(0.0, min(1.0, event.x / width)))
            self.set_position(self.island.media.position())
        return True

    # ---- lyrics --------------------------------------------------------------
    def _on_lyric_clicked(self, _listbox, row):
        if row.time_us is not None:  # unsynced lyrics have no time to jump to
            self.island.media.set_position(row.time_us)

    def show_lyrics_view(self, active):
        self.lower.set_visible_child_name("lyrics" if active else "tiles")
        if self.lyrics_btn.get_active() != active:
            self.lyrics_btn.set_active(active)

    def set_lyrics(self, lines, status):
        """lines: [(time_us, text)]; status: text shown instead of/above the lines."""
        clear(self.lyrics_list)
        self._lyric_rows, self._lyric_idx = [], -1
        for time_us, text in lines:
            row = Gtk.ListBoxRow()
            row.time_us = time_us
            lbl = label(text or "♪", ("lyric",), xalign=0.5, ellipsize=False)
            lbl.set_line_wrap(True)
            row.add(lbl)
            self.lyrics_list.add(row)
            self._lyric_rows.append(row)
        self.lyrics_list.show_all()
        self.lyrics_status.set_text(status or "")
        self.lyrics_status.set_visible(bool(status))
        self.lyrics_scroll.set_visible(bool(lines))

    def highlight_lyric(self, index):
        if index == self._lyric_idx:
            return
        for i in (self._lyric_idx, index):
            if 0 <= i < len(self._lyric_rows):
                ctx = self._lyric_rows[i].get_child().get_style_context()
                (ctx.add_class if i == index else ctx.remove_class)("current")
        self._lyric_idx = index
        if 0 <= index < len(self._lyric_rows) and self.get_mapped():
            # Keep the line being sung in the middle
            row = self._lyric_rows[index]
            alloc = row.get_allocation()
            adj = self.lyrics_scroll.get_vadjustment()
            target = alloc.y - (adj.get_page_size() - alloc.height) / 2
            adj.set_value(max(adj.get_lower(), min(target, adj.get_upper() - adj.get_page_size())))

    def update_weather(self, weather):
        if weather.current:
            c = weather.current
            self._set_tile(self.weather_tile, c["icon"], f"{c['temp']}°", f"{c['text']} · {c['city']}")
        else:
            caption = _("Ort festlegen") if not weather.configured else _("nicht verfügbar")
            self._set_tile(self.weather_tile, "weather-few-clouds-symbolic", "–", caption)

    def update_timer(self, timer):
        if timer.running:
            self._set_tile(self.timer_tile, "alarm-symbolic", format_seconds(timer.remaining), timer.label)
        else:
            self._set_tile(self.timer_tile, "alarm-symbolic", _("Timer"), _("Kein Timer"))

    def update_battery(self, battery):
        if battery.present:
            self._set_tile(self.battery_tile, battery.icon_name, f"{battery.percentage} %",
                           _("Lädt") if battery.plugged else _("Akku"))
        else:
            self._set_tile(self.battery_tile, "emblem-system-symbolic", _("Steuerung"), _("WLAN, Ton, Theme"))


# =============================================================================
# Clipboard history
# =============================================================================
class ClipboardPage(Page):
    def __init__(self, island):
        super().__init__(island)
        self.search = Gtk.SearchEntry(placeholder_text=_("Verlauf durchsuchen …"), hexpand=True)
        island.make_typeable(self.search)
        self.search.connect("search-changed", lambda *_: self.listbox.invalidate_filter())
        self.search.connect("activate", lambda *_: self._paste_first())
        self.search.connect("key-press-event", self._on_search_key)

        top = Gtk.Box(spacing=8)
        top.pack_start(self.search, True, True, 0)
        top.pack_start(button("edit-clear-all-symbolic", tooltip=_("Verlauf leeren (Angepinntes bleibt)"),
                              on_click=island.clipboard.clear), False, False, 0)
        self.pack_start(top, False, False, 0)

        self.listbox = Gtk.ListBox(selection_mode=Gtk.SelectionMode.BROWSE)
        self.listbox.set_activate_on_single_click(True)
        self.listbox.set_filter_func(self._filter)
        self.listbox.connect("row-activated", lambda _lb, row: self._activate(row.item))
        placeholder = label(_("Noch nichts kopiert – alles, was du kopierst, landet hier."), ("dim",), xalign=0.5)
        placeholder.show()
        self.listbox.set_placeholder(placeholder)

        scrolled = Gtk.ScrolledWindow(vexpand=True)
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.add(self.listbox)
        self.pack_start(scrolled, True, True, 0)
        self.transfer = None       # the "Transfer" strip: built the first time the tab opens
        self._dirty = True

    def _activate(self, item):
        """A click on an entry types it into the window you came from; a received one is only copied."""
        if item.get("received"):
            self.island.copy_received(item)
        else:
            self.island.paste(item)

    def update_transfer(self):
        if self.transfer is not None:
            self.transfer.refresh()

    def mark_dirty(self):
        self._dirty = True
        if self.get_mapped():
            self.rebuild()

    def on_show(self):
        self.island.clipboard.prune()
        if self.transfer is None:
            from island.clipview import TransferBar      # lazy: only once the tab is looked at
            self.transfer = TransferBar(self.island)
            self.pack_end(self.transfer, False, False, 0)
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
            box.pack_start(label(_("Bild · {w}×{h}").format(w=w, h=h), ("dim",)), True, True, 0)
        else:
            text = " ⏎ ".join(line.strip() for line in item["text"].strip().splitlines()[:3])
            box.pack_start(label(text[:300], max_chars=60), True, True, 0)

        if received := item.get("received"):
            mark = label("empfangen", ("dim", "small", "received"), ellipsize=False)
            mark.set_tooltip_text(f"Von {received.get('from') or 'einem anderen PC'} empfangen · Klick kopiert")
            box.pack_start(mark, False, False, 0)
        stamp = datetime.fromtimestamp(item.get("time", 0))
        when = f"{stamp:%H:%M}" if stamp.date() == datetime.now().date() else day_month(stamp)
        box.pack_start(label(when, ("dim", "small"), ellipsize=False), False, False, 0)
        if self.island.clip_can_send():
            box.pack_start(button("document-send-symbolic", tooltip="An PC senden", css=("mini",), size=14,
                                  on_click=lambda: self._send(item)), False, False, 0)
        pin = button("view-pin-symbolic", tooltip=_("Anpinnen"), css=("mini",) + (("pinned",) if item.get("pinned") else ()),
                     size=14, on_click=lambda: self.island.clipboard.toggle_pin(item))
        remove = button("window-close-symbolic", tooltip=_("Entfernen"), css=("mini",), size=14,
                        on_click=lambda: self.island.clipboard.remove(item))
        box.pack_start(pin, False, False, 0)
        box.pack_start(remove, False, False, 0)
        row.add(box)
        return row

    def _send(self, item):
        """The row's button: ask for the peer if there are several, then send this entry (only on this click)."""
        clip = self.island.clip
        if clip is None or self.transfer is None:
            return

        def send(peer):
            if item["kind"] == "image":
                clip.send_path(self.island.clipboard.image_path(item), kind="image", peer=peer)
            else:
                text = item["text"]
                note = f"Text ({len(text)} Zeichen" + (", gekürzt auf die Länge des Verlaufs" if len(text) >= 20000
                                                       else "") + ")"
                clip.send_text(text, peer=peer, note=note)

        self.transfer.request_send(send)

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
            self._activate(rows[0].item)

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
        header.pack_start(label(_("Ablage"), ("title",), ellipsize=False), False, False, 0)
        header.pack_start(self.count, True, True, 0)

        # Drag source for all files at once
        self.drag_all = css_class(Gtk.EventBox(), "drag-all")
        self.drag_all.set_no_show_all(True)
        drag_box = Gtk.Box(spacing=6)
        drag_box.pack_start(icon("edit-select-all-symbolic", 14), False, False, 0)
        drag_box.pack_start(label(_("Alle ziehen"), ellipsize=False), False, False, 0)
        self.drag_all.add(drag_box)
        drag_box.show_all()
        self._make_drag_source(self.drag_all, lambda: list(island.shelf.uris), "folder-documents")
        header.pack_end(button("edit-clear-all-symbolic", tooltip=_("Ablage leeren"), on_click=island.shelf.clear),
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
        empty.pack_start(label(_("Dateien auf die Insel ziehen"), ("title",), xalign=0.5), False, False, 0)
        empty.pack_start(label(_("Sie warten hier, bis du sie woanders hinziehst."), ("dim",), xalign=0.5),
                         False, False, 0)

        self.stack = Gtk.Stack(vexpand=True, transition_type=Gtk.StackTransitionType.CROSSFADE)
        self.stack.add_named(scrolled, "files")
        self.stack.add_named(empty, "empty")
        self.pack_start(self.stack, True, True, 0)
        self.transfer = None       # the "Transfer" strip, only while sending is on (built when needed)
        self.rebuild()

    def update_transfer(self):
        if self.transfer is not None:
            self.transfer.refresh()

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
        self.count.set_text(n_("{n} Datei", "{n} Dateien", n).format(n=n) if n else "")
        for uri in uris:
            self.flow.add(self._tile(uri))
        self.flow.show_all()
        self.drag_all.set_visible(n > 1)
        self.stack.set_visible_child_name("files" if uris else "empty")
        if self.island.clip_can_send() and self.transfer is None:
            from island.clipview import TransferBar
            self.transfer = TransferBar(self.island, always=False)
            self.pack_end(self.transfer, False, False, 0)
        if self.transfer is not None:
            self.transfer.refresh()

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
        event.set_tooltip_text(_("{name}\nZiehen zum Ablegen · Doppelklick öffnet").format(name=name))
        event.add(box)
        self._make_drag_source(event, lambda: [uri], "text-x-generic")
        if gicon:
            event.drag_source_set_icon_gicon(gicon)
        event.connect("button-press-event", self._on_tile_press, uri)

        remove = button("window-close-symbolic", tooltip=_("Aus der Ablage entfernen"), css=("mini", "tile-close"),
                        size=12, on_click=lambda: self.island.shelf.remove(uri))
        remove.set_halign(Gtk.Align.END)
        remove.set_valign(Gtk.Align.START)
        overlay = Gtk.Overlay()
        overlay.add(event)
        overlay.add_overlay(remove)
        if self.island.clip_can_send() and gfile.get_path() and self._is_regular(gfile):
            send = button("document-send-symbolic", tooltip="An PC senden", css=("mini", "tile-close"), size=12,
                          on_click=lambda: self._send(gfile.get_path()))
            send.set_halign(Gtk.Align.START)
            send.set_valign(Gtk.Align.START)
            overlay.add_overlay(send)
        return overlay

    @staticmethod
    def _is_regular(gfile):
        try:
            return gfile.query_info("standard::type", Gio.FileQueryInfoFlags.NONE, None).get_file_type() \
                == Gio.FileType.REGULAR
        except GLib.Error:
            return False

    def _send(self, path):
        """The tile's button: a file goes to a peer (asks first if there are several). Folders are not sent."""
        clip = self.island.clip
        if clip is not None and self.transfer is not None:
            self.transfer.request_send(lambda peer: clip.send_path(path, kind="file", peer=peer))

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
    PRESETS = [(1, "1 min"), (5, "5 min"), (10, "10 min")]

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
        note_box.pack_start(label(_("Notiz"), ("title",)), False, False, 0)
        note_box.set_margin_top(12)
        note_box.pack_start(note_scroll, True, True, 0)
        row.pack_start(note_box, True, True, 0)

        # ---- timer ----------------------------------------------------------
        timer_box = css_class(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8), "card")
        timer_box.set_size_request(220, -1)
        self.mode = label("", ("dim",), xalign=1.0, ellipsize=False)
        title = Gtk.Box()
        title.pack_start(label(_("Timer"), ("title",)), True, True, 0)
        title.pack_end(self.mode, False, False, 0)
        timer_box.pack_start(title, False, False, 0)
        self.remaining = label("00:00", ("timer-display", "dim"), xalign=0.5, ellipsize=False)
        timer_box.pack_start(self.remaining, False, False, 0)

        # Pomodoro: 25 min focus, then a break (every 4th one is longer)
        pomodoro = Gtk.Box(spacing=6, homogeneous=True)
        pomodoro.pack_start(button(text=_("Fokus 25"), css=("accent",), tooltip=_("Pomodoro: 25 min Fokus, dann Pause"),
                                   on_click=lambda: island.start_pomodoro("focus")), True, True, 0)
        pomodoro.pack_start(button(text=_("Pause 5"), on_click=lambda: island.start_pomodoro("break")), True, True, 0)
        timer_box.pack_start(pomodoro, False, False, 0)

        presets = Gtk.Box(spacing=6, homogeneous=True)
        for minutes, text in self.PRESETS:
            presets.pack_start(button(text=text, on_click=lambda m=minutes: island.timer.start(m * 60)), True, True, 0)
        timer_box.pack_start(presets, False, False, 0)

        custom = Gtk.Box(spacing=6)
        self.spin = Gtk.SpinButton.new_with_range(1, 600, 1)
        self.spin.set_value(15)
        island.make_typeable(self.spin)
        custom.pack_start(self.spin, True, True, 0)
        custom.pack_start(label("min", ("dim",), ellipsize=False), False, False, 0)
        custom.pack_start(button(text=_("Start"), css=("accent",),
                                 on_click=lambda: island.timer.start(int(self.spin.get_value()) * 60)),
                          False, False, 0)
        timer_box.pack_start(custom, False, False, 0)
        self.stop_btn = button("media-playback-stop-symbolic", _("Stoppen"), on_click=island.timer.cancel)
        self.stop_btn.get_child().show_all()
        self.stop_btn.set_no_show_all(True)
        timer_box.pack_end(self.stop_btn, False, False, 0)
        row.pack_start(timer_box, False, False, 0)
        self.update_timer(island.timer)   # built lazily: a timer may run already

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

    def append(self, text):
        """Add text as a new paragraph at the end of the note (e.g. recognised text)."""
        buf = self.text.get_buffer()
        current = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), True)
        if not current.strip() or current.endswith("\n\n"):
            sep = ""
        else:
            sep = "\n" if current.endswith("\n") else "\n\n"
        buf.insert(buf.get_end_iter(), sep + text)  # "changed" saves it

    def update_timer(self, timer):
        self.remaining.set_text(format_seconds(timer.remaining) if timer.running else "00:00")
        self.mode.set_text(timer.label if timer.running else "")
        ctx = self.remaining.get_style_context()
        (ctx.remove_class if timer.running else ctx.add_class)("dim")
        self.stop_btn.set_visible(timer.running)


# =============================================================================
# To-do with reminders
# =============================================================================
def _due_text(due):
    when = datetime.fromtimestamp(due)
    today = datetime.now().date()
    if when.date() == today:
        return when.strftime("%H:%M")
    if when.date() == today + timedelta(days=1):
        return _("morgen {time}").format(time=when.strftime("%H:%M"))
    return f"{day_month(when)} {when:%H:%M}"


class TodoPage(Page):
    def __init__(self, island):
        super().__init__(island)
        todo = island.todo
        self.count = label("", ("dim",), xalign=1.0, ellipsize=False)
        header = Gtk.Box()
        header.pack_start(label(_("Aufgaben"), ("title",)), True, True, 0)
        header.pack_end(self.count, False, False, 0)
        self.pack_start(header, False, False, 0)

        self.entry = Gtk.Entry(placeholder_text=_("Neue Aufgabe …"), hexpand=True)
        self.due = Gtk.Entry(placeholder_text="14:30", width_chars=9)
        self.due.set_tooltip_text(_("Erinnerung: 14:30 · 9 · in 20 min · in 2 h (leer = keine)"))
        for widget in (self.entry, self.due):
            island.make_typeable(widget)
            widget.connect("activate", lambda *_: self._add())
        add_row = Gtk.Box(spacing=6)
        add_row.pack_start(self.entry, True, True, 0)
        add_row.pack_start(self.due, False, False, 0)
        add_row.pack_start(button("list-add-symbolic", css=("accent",), tooltip=_("Hinzufügen"), on_click=self._add),
                           False, False, 0)
        self.pack_start(add_row, False, False, 0)
        self.hint = label("", ("small", "warning"))
        self.hint.set_no_show_all(True)
        self.pack_start(self.hint, False, False, 0)

        self.listbox = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
        placeholder = label(_("Nichts zu tun – genieß den Moment."), ("dim",), xalign=0.5)
        placeholder.show()
        self.listbox.set_placeholder(placeholder)
        scrolled = Gtk.ScrolledWindow(vexpand=True)
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.add(self.listbox)
        self.pack_start(scrolled, True, True, 0)
        self.todo = todo
        self.rebuild()

    def _add(self):
        text = self.entry.get_text().strip()
        if not text:
            return
        try:
            due = parse_due(self.due.get_text())
        except ValueError:
            self.hint.set_text(_("Zeit nicht verstanden – z. B. 14:30, 9, in 20 min, in 2 h"))
            self.hint.show()
            return
        self.hint.hide()
        self.todo.add(text, due)
        self.entry.set_text("")
        self.due.set_text("")
        self.entry.grab_focus()

    def rebuild(self):
        clear(self.listbox)
        total = len(self.todo.items)
        self.count.set_text(_("{done}/{total} heute erledigt").format(done=self.todo.done_today, total=total)
                            if total else "")
        now = time.time()
        for task in self.todo.sorted_items():
            box = Gtk.Box(spacing=10)
            check = Gtk.CheckButton()
            check.set_can_focus(False)
            check.set_active(bool(task.get("done")))
            check.connect("toggled", lambda _c, t=task: self.todo.toggle(t))
            text = label(task["text"], ("done",) if task.get("done") else ())
            box.pack_start(check, False, False, 0)
            box.pack_start(text, True, True, 0)
            if task.get("due"):
                overdue = not task.get("done") and task["due"] < now
                box.pack_start(label(_due_text(task["due"]), ("small", "warning" if overdue else "dim"),
                                     ellipsize=False), False, False, 0)
            box.pack_start(button("window-close-symbolic", tooltip=_("Löschen"), css=("mini",), size=14,
                                  on_click=lambda t=task: self.todo.remove(t)), False, False, 0)
            row = Gtk.ListBoxRow()
            row.add(box)
            self.listbox.add(row)
        self.listbox.show_all()


# =============================================================================
# Water reminder
# =============================================================================
class WaterPage(Page):
    def __init__(self, island):
        super().__init__(island)
        water = island.water
        self.water = water
        row = Gtk.Box(spacing=12)
        self.pack_start(row, True, True, 0)

        # ---- today ----------------------------------------------------------
        today = css_class(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8), "card")
        today.set_size_request(230, -1)
        today.pack_start(label(_("Wasser"), ("title",)), False, False, 0)
        self.amount = label("", ("huge-sm",), ellipsize=False)
        self.status = label("", ("dim",))
        self.bar = Gtk.ProgressBar()
        today.pack_start(self.amount, False, False, 0)
        today.pack_start(self.status, False, False, 0)
        today.pack_start(self.bar, False, False, 0)
        self.drink_btn = button("list-add-symbolic", _("Trinken"), css=("accent",), on_click=lambda: water.drink())
        actions = Gtk.Box(spacing=6)
        actions.pack_start(self.drink_btn, True, True, 0)
        actions.pack_start(button("edit-undo-symbolic", tooltip=_("Letzten Eintrag zurücknehmen"), on_click=water.undo),
                           False, False, 0)
        actions.pack_start(button("emblem-system-symbolic", tooltip=_("Einstellungen"),
                                  on_click=lambda: self.right.set_visible_child_name(
                                      "settings" if self.right.get_visible_child_name() == "chart" else "chart")),
                           False, False, 0)
        today.pack_end(actions, False, False, 0)
        row.pack_start(today, False, False, 0)

        # ---- chart / settings -----------------------------------------------
        self.chart = BarChart(height=150)
        chart_box = css_class(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6), "card")
        chart_box.pack_start(label(_("Heute pro Stunde (ml)"), ("dim", "small")), False, False, 0)
        chart_box.pack_start(self.chart, True, True, 0)

        settings = css_class(Gtk.Grid(column_spacing=10, row_spacing=8), "card")
        cfg = island.config
        self._spins = {}
        rows = [
            (_("Portion (Flasche/Glas)"), "water_portion_ml", 50, 2000, 50, "ml"),
            (_("Tagesziel"), "water_goal_ml", 500, 6000, 250, "ml"),
            (_("Erinnern alle"), "water_interval_min", 15, 240, 15, "min"),
        ]
        for i, (text, key, lo, hi, step, unit) in enumerate(rows):
            spin = Gtk.SpinButton.new_with_range(lo, hi, step)
            spin.set_value(int(cfg.get(key, lo)))
            island.make_typeable(spin)
            spin.connect("value-changed", lambda s, k=key: self._set(k, int(s.get_value())))
            settings.attach(label(text), 0, i, 1, 1)
            settings.attach(spin, 1, i, 1, 1)
            settings.attach(label(unit, ("dim",), ellipsize=False), 2, i, 1, 1)
        hours = Gtk.Box(spacing=6)
        for key, default in (("water_start", "09:00"), ("water_end", "21:00")):
            entry = Gtk.Entry(text=cfg.get(key, default), width_chars=5)
            island.make_typeable(entry)
            entry.connect("changed", lambda e, k=key: self._set_time(k, e.get_text()))
            hours.pack_start(entry, False, False, 0)
            if key == "water_start":
                hours.pack_start(label(_("bis"), ("dim",), ellipsize=False), False, False, 0)
        reminders = Gtk.Switch(active=cfg.get("water_reminders", True), halign=Gtk.Align.START)
        reminders.connect("notify::active", lambda s, _p: self._set("water_reminders", s.get_active()))
        settings.attach(label(_("Erinnerungen")), 0, 3, 1, 1)
        settings.attach(reminders, 1, 3, 1, 1)
        settings.attach(label(_("Aktive Zeit")), 0, 4, 1, 1)
        settings.attach(hours, 1, 4, 2, 1)

        self.right = Gtk.Stack(transition_type=Gtk.StackTransitionType.CROSSFADE, hexpand=True)
        self.right.add_named(chart_box, "chart")
        self.right.add_named(settings, "settings")
        row.pack_start(self.right, True, True, 0)
        self.update()

    def _set(self, key, value):
        self.island.config[key] = value
        self.island.config.save()
        self.water.schedule()
        self.update()

    def _set_time(self, key, text):
        try:
            datetime.strptime(text, "%H:%M")
        except ValueError:
            return
        self._set(key, text)

    def update(self):
        w = self.water
        drunk, goal = w.today_ml, w.goal
        pct = min(100, round(100 * drunk / goal)) if goal else 0
        self.amount.set_text(f"{decimal(drunk / 1000)} / {decimal(goal / 1000)} L")
        goal_text = _(" · Ziel erreicht 🎉") if drunk >= goal else ""
        self.status.set_text(_("Heute · {pct} %").format(pct=pct) + goal_text)
        self.bar.set_fraction(pct / 100)
        self.drink_btn.get_child().get_children()[-1].set_text(f"+{w.portion} ml")
        hours = w.per_hour()
        first, last = 6, 23
        self.chart.set_data(hours[first:last + 1],
                            [f"{h:02d}" if h % 3 == 0 else "" for h in range(first, last + 1)])


# =============================================================================
# Stretch reminder
# =============================================================================
class StretchPage(Page):
    OUTCOMES = (("done", "Erledigt"), ("unconfirmed", "Unbestätigt"), ("snoozed", "Später"),
                ("skipped", "Übersprungen"), ("missed", "Verpasst"))

    def __init__(self, island):
        super().__init__(island)
        self._syncing = False
        row = Gtk.Box(spacing=12)
        self.pack_start(row, True, True, 0)

        # ---- switches ---------------------------------------------------------
        left = css_class(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10), "card")
        left.set_size_request(270, -1)
        head = Gtk.Box(spacing=8)
        head.pack_start(label("Dehn-Erinnerung", ("title",)), True, True, 0)
        self.switch = Gtk.Switch(valign=Gtk.Align.CENTER)
        self.switch.connect("notify::active", self._on_switch)
        head.pack_end(self.switch, False, False, 0)
        self.status = label("", ("dim",), ellipsize=False)
        self.status.set_line_wrap(True)
        self.status.set_max_width_chars(30)
        self.status.set_yalign(0.0)
        self.off_today = Gtk.ToggleButton(label="Heute aus")
        self.off_today.set_can_focus(False)
        self.off_today.connect("toggled", self._on_today)
        now = button("avatar-default-symbolic", "Jetzt dehnen", css=("accent",), on_click=self._stretch_now)
        actions = Gtk.Box(spacing=6)
        actions.pack_start(now, True, True, 0)
        actions.pack_start(self.off_today, False, False, 0)
        left.pack_start(head, False, False, 0)
        left.pack_start(self.status, True, True, 0)
        left.pack_end(actions, False, False, 0)
        row.pack_start(left, False, False, 0)

        # ---- today's numbers ---------------------------------------------------
        right = css_class(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4), "card")
        right.pack_start(label("Heute", ("dim", "small")), False, False, 0)
        self.counts = {}
        for key, text in self.OUTCOMES:
            line = Gtk.Box(spacing=8)
            number = label("0", ("big-value",), xalign=1.0, ellipsize=False)
            line.pack_start(label(_(text)), True, True, 0)
            line.pack_end(number, False, False, 0)
            right.pack_start(line, False, False, 0)
            self.counts[key] = number
        self.footer = label("", ("dim", "small"), ellipsize=False)
        self.footer.set_line_wrap(True)
        self.footer.set_max_width_chars(30)
        self.footer.set_xalign(0.0)
        right.pack_end(self.footer, False, False, 0)
        row.pack_start(right, True, True, 0)
        self.update()

    def _on_switch(self, switch, _param):
        if not self._syncing:
            self.island.set_option("stretch_enabled", switch.get_active())

    def _on_today(self, toggle):
        if not self._syncing:
            self.island.stretch.on_today(toggle.get_active())

    def _stretch_now(self):
        self.island.collapse()    # the card comes up on the folded island
        self.island.stretch.trigger_now()

    def on_show(self):
        self.update()

    def update(self):
        s, cfg = self.island.stretch, self.island.config
        enabled, off_today = cfg.flag("stretch_enabled"), s.config.get("stretch_off_date") == s.env.today()
        self._syncing = True
        self.switch.set_active(enabled)
        self.off_today.set_active(off_today)
        self._syncing = False
        if not enabled:
            status = "Aus. Es läuft nichts im Hintergrund."
        elif off_today:
            status = "Heute aus. Morgen geht es von selbst wieder los."
        elif s.unavailable:
            status = "Pausiert: die Leerlaufzeit lässt sich nicht messen."
        elif s.round is not None:
            status = "Eine Dehnpause wartet auf dich."
        elif s.pending:
            status = "Fällig: kommt, sobald Vollbild oder Fokus-Timer vorbei sind."
        else:
            status = "Nach {interval} Min. aktiver Zeit am Rechner, bisher {done} Min.".format(
                interval=s.rules.interval_s // 60, done=s.counter.active_s // 60)
        self.status.set_text(status)
        today = s.today()
        for key, number in self.counts.items():
            number.set_text(str(today[key]))
        self.footer.set_text("Eigene Übungen: Tray › Dehnen › Übungen bearbeiten")


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
        setup.pack_start(label(_("Für welchen Ort soll das Wetter angezeigt werden?"), ("title",), xalign=0.5),
                         False, False, 0)
        self.city_entry = Gtk.Entry(placeholder_text=_("z. B. Berlin"), width_chars=24, halign=Gtk.Align.CENTER)
        island.make_typeable(self.city_entry)
        self.city_entry.connect("activate", lambda *_: self._save_city())
        entry_row = Gtk.Box(spacing=8, halign=Gtk.Align.CENTER)
        entry_row.pack_start(self.city_entry, False, False, 0)
        entry_row.pack_start(button(text=_("Speichern"), css=("accent",), on_click=self._save_city), False, False, 0)
        setup.pack_start(entry_row, False, False, 0)
        setup.pack_start(label(_("Vorhersage: MET Norway · Ortssuche: OpenStreetMap · kein Konto nötig"),
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
        top.pack_end(button("document-edit-symbolic", tooltip=_("Ort ändern"), on_click=self._edit_city), False, False, 0)
        top.pack_end(button("view-refresh-symbolic", tooltip=_("Aktualisieren"), on_click=island.weather.refresh),
                     False, False, 0)
        data.pack_start(top, False, False, 0)

        self.hourly = css_class(Gtk.Box(homogeneous=True), "card")
        self.daily = css_class(Gtk.Box(homogeneous=True), "card")
        data.pack_start(self.hourly, False, False, 0)
        data.pack_start(self.daily, False, False, 0)
        self.status = label("", ("dim", "small"), xalign=1.0)
        data.pack_end(self.status, False, False, 0)
        self.stack.add_named(data, "data")
        self.update(island.weather)   # built lazily: the forecast may be in already

    def _save_city(self):
        city = self.city_entry.get_text().strip()
        if city:
            self.island.weather.set_city(city)
            self.status.set_text(_("Lade Wetter …"))
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
                hour = _("{hour} Uhr").format(hour=h["time"])
                self.hourly.pack_start(self._column(hour, h["icon"], f"{h['temp']}°"), True, True, 0)
            clear(self.daily)
            for d in weather.daily:
                self.daily.pack_start(self._column(d["day"], d["icon"], f"{d['max']}° / {d['min']}°"), True, True, 0)
            self.hourly.show_all()
            self.daily.show_all()
            self.status.set_text(_("Daten: MET Norway (CC BY 4.0)"))
        elif weather.error:
            self.now_text.set_text(_("Wetter nicht verfügbar"))
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
            "wifi": self._toggle(grid, "network-wireless-symbolic", _("WLAN"), lambda on: system.wifi_set(on, self._later)),
            "bluetooth": self._toggle(grid, "bluetooth-active-symbolic", "Bluetooth",
                                      lambda on: system.bluetooth_set(on, self._later)),
            "dnd": self._toggle(grid, "notifications-disabled-symbolic", _("Nicht stören"), island.dnd_set),
            "dark": self._toggle(grid, "weather-clear-night-symbolic", "Dark Mode", system.dark_set),
            "mic": self._toggle(grid, "microphone-sensitivity-muted-symbolic", _("Mikro aus"),
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
        # Not homogeneous: five buttons as wide as the longest label ("Ruhezustand") overflow the island
        actions = Gtk.Box(spacing=8)
        actions.pack_start(button("camera-photo-symbolic", "Screenshot", on_click=self._screenshot), True, True, 0)
        actions.pack_start(button("system-lock-screen-symbolic", _("Sperren"),
                                  on_click=lambda: (island.collapse(), system.lock())), True, True, 0)
        for key, icon_name, text, action in (
                ("suspend", "weather-clear-night-symbolic", _("Ruhezustand"), system.suspend),
                ("reboot", "system-reboot-symbolic", _("Neustart"), system.reboot),
                ("poweroff", "system-shutdown-symbolic", _("Aus"), system.poweroff)):
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
        self._set_toggle("dnd", self.island.dnd_get())
        self._set_toggle("dark", system.dark_get())
        system.volume_get(lambda v: self._set_scale(self.volume, v))

        def brightness(v):
            self.brightness_row.set_visible(v is not None)
            self._set_scale(self.brightness, v)

        system.brightness_get(brightness)

    def _screenshot(self):
        self.island.screenshot("area")

    def _on_dangerous(self, btn, key, text, action):
        """Sleep, restart and shut down have to be clicked twice."""
        if key in self._armed:
            GLib.source_remove(self._armed.pop(key))
            self.island.collapse()
            action()
            return
        box = btn.get_child()
        box.get_children()[-1].set_text(_("Nochmal?"))
        css_class(btn, "danger")

        def disarm():
            self._armed.pop(key, None)
            box.get_children()[-1].set_text(text)
            btn.get_style_context().remove_class("danger")
            return GLib.SOURCE_REMOVE

        self._armed[key] = GLib.timeout_add_seconds(3, disarm)
