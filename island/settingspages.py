"""The three tabs of the settings window: Übersicht, Gesten, Funktionen. Drawing only; the rules are in
settingslogic.py and settingsmeta.py."""

import re
import time

import gi

from island import gestures, hotkeys, settingsmeta
from island.settingslogic import action_choices, action_label, proc_stats
from island.settingsui import TRAY_LINES, bin_dir, clear, css_class, flat_button, label

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa: E402


def scrolled(child):
    box = Gtk.ScrolledWindow(vexpand=True, hexpand=True)
    box.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    box.add(child)
    return box


def page_header(title, trailing=None):
    head = Gtk.Box(spacing=12)
    head.pack_start(label(title, ("page-title",)), False, False, 0)
    if trailing is not None:
        head.pack_end(trailing, False, False, 0)
    return head


class Page(Gtk.Box):
    def __init__(self, window):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.window = window
        self.store = window.store

    def on_show(self):
        """Called every time the tab is shown."""


# =============================================================================
# Übersicht
# =============================================================================
class FunctionRow(Gtk.Box):
    """One function: name (click runs it), description, hotkey (click changes it), switch, status."""

    def __init__(self, page, data):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.page, self.data = page, data
        self.window, self.store = page.window, page.store
        self._pending = None                      # an accelerator captured and waiting for "Speichern"
        self._syncing = False

        grid = css_class(Gtk.Box(spacing=10), "function-row")
        text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        runnable = data["has_action"] or bool(data["tab"])
        self.name_button = flat_button(data["name"], ("name-button",), self._on_run,
                                       "Klick startet die Funktion" if runnable else None)
        self.name_button.set_halign(Gtk.Align.START)
        self.name_button.set_sensitive(runnable)
        text.pack_start(self.name_button, False, False, 0)
        text.pack_start(label(data["description"], ("dim", "small"), wrap=True), False, False, 6)
        grid.pack_start(text, True, True, 0)

        self.status = label("", ("dim", "small"), xalign=1.0, wrap=True)
        self.status.set_max_width_chars(34)
        self.status.set_width_chars(22)
        self.dot = label("●", ("stopped-dot",))
        grid.pack_start(self.dot, False, False, 0)
        grid.pack_start(self.status, False, False, 0)

        self.hotkey_button = flat_button("", ("hotkey",), self._on_hotkey_click, "Klick ändert den Hotkey")
        if data["hotkey_key"]:
            grid.pack_start(self.hotkey_button, False, False, 0)
        else:
            spacer = Gtk.Box()
            spacer.set_size_request(128, 1)
            grid.pack_start(spacer, False, False, 0)

        self.switch = Gtk.Switch(valign=Gtk.Align.CENTER)
        if data["enabled_key"]:
            self.switch.connect("notify::active", self._on_switch)
            grid.pack_start(self.switch, False, False, 0)
        else:
            spacer = Gtk.Box()
            spacer.set_size_request(50, 1)
            grid.pack_start(spacer, False, False, 0)
        self.pack_start(grid, False, False, 0)

        self.editor = self._build_editor()
        self.confirm = self._build_confirm()
        self.pack_start(self.editor, False, False, 0)
        self.pack_start(self.confirm, False, False, 0)
        self.refresh(data)

    # ---- content -------------------------------------------------------------------------------------------------
    def refresh(self, data):
        self.data = data
        shown = hotkeys.pretty(data["hotkey"]) if data["hotkey"] else "–"
        self.hotkey_button.set_label(shown)
        self.hotkey_button.set_tooltip_text("Klick ändert den Hotkey" + (
            f" · Standard: {hotkeys.pretty(data['default_hotkey'])}" if data["default_hotkey"] else ""))
        self.status.set_text(data["status"] or ("Aus" if data["enabled"] is False else ""))
        ctx = self.dot.get_style_context()
        ctx.remove_class("running-dot")
        ctx.remove_class("stopped-dot")
        ctx.add_class("running-dot" if data["running"] else "stopped-dot")
        self._syncing = True
        self.switch.set_active(bool(data["enabled"]))
        self._syncing = False

    def matches(self, query):
        if not query:
            return True
        d = self.data
        hay = " ".join((d["name"], d["description"], d["category"], d["id"], d["status"] or "",
                        hotkeys.pretty(d["hotkey"]) if d["hotkey"] else "")).lower()
        return all(part in hay for part in query.lower().split())

    # ---- switch -------------------------------------------------------------------------------------------------------
    def _on_switch(self, switch, _param):
        if self._syncing:
            return
        ok, message = self.store.set_value(self.data["enabled_key"], switch.get_active())
        if not ok:
            self._syncing = True
            switch.set_active(not switch.get_active())
            self._syncing = False
            self.window.notice(message, error=True)
        else:
            self.window.refresh_banners()
            self.data["enabled"] = switch.get_active()

    # ---- run ------------------------------------------------------------------------------------------------------------
    def _on_run(self):
        if self.data["dangerous"]:
            self.confirm.show()
            return
        self.window.run_function(self.data)

    def _build_confirm(self):
        bar = css_class(Gtk.Box(spacing=10), "confirm")
        bar.pack_start(label(f"„{self.data['name']}“ wirklich ausführen?", ("warn",)), True, True, 0)
        bar.pack_end(flat_button("Abbrechen", (), lambda: bar.hide()), False, False, 0)
        bar.pack_end(flat_button("Ja, ausführen", ("danger",), self._confirmed), False, False, 0)
        bar.show_all()
        bar.set_no_show_all(True)
        bar.hide()
        return bar

    def _confirmed(self):
        self.confirm.hide()
        self.window.run_function(self.data)

    # ---- hotkey editor --------------------------------------------------------------------------------------------------
    def _build_editor(self):
        bar = css_class(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8), "editor")
        self.editor_text = label("", wrap=True)
        self.editor_warn = label("", ("warn",), wrap=True)
        buttons = Gtk.Box(spacing=8)
        self.save_button = flat_button("Speichern", ("accent",), self._save)
        self.again_button = flat_button("Neu aufnehmen", (), self._record)
        self.reset_button = flat_button("Zurücksetzen", (), self._reset, "Zurück zum Standard")
        self.remove_button = flat_button("Entfernen", (), self._remove, "Keinen Hotkey")
        for b in (self.save_button, self.again_button, self.reset_button, self.remove_button):
            buttons.pack_start(b, False, False, 0)
        buttons.pack_end(flat_button("Abbrechen", (), self.cancel), False, False, 0)
        bar.pack_start(self.editor_text, False, False, 0)
        bar.pack_start(self.editor_warn, False, False, 0)
        bar.pack_start(buttons, False, False, 0)
        bar.show_all()
        bar.set_no_show_all(True)
        bar.hide()
        return bar

    def _on_hotkey_click(self):
        if self.editor.get_visible():
            self.cancel()
        else:
            self.page.close_editors(except_row=self)
            self._record()
            self.editor.show()

    def _record(self):
        self._pending = None
        self.hotkey_button.get_style_context().add_class("editing")
        self.editor_text.set_text("Drücke die neue Tastenkombination … (Esc bricht ab)")
        self.editor_warn.hide()
        self.save_button.hide()
        self.window.start_capture(self)

    def captured(self, accel, raw):
        """The window got a key combination for us."""
        self.window.stop_capture()
        self.hotkey_button.get_style_context().remove_class("editing")
        parsed = hotkeys.parse(accel) if accel else None
        if parsed is None or (not (parsed.mods - {"shift"}) and not re.fullmatch(r"f\d{1,2}", parsed.key)):
            self.editor_text.set_text(f"{raw or '?'} – bitte mit Strg, Alt oder Super kombinieren.")
            self.editor_warn.hide()
            self.save_button.hide()
            return
        self._pending = accel
        self.editor_text.set_text(f"Neue Kombination: {hotkeys.pretty(accel)}")
        other = self.store.conflict(self.data["id"], accel)
        if other:
            self.editor_warn.set_text(f"Schon belegt von: {other}")
            self.editor_warn.show()
            self.save_button.set_label("Trotzdem speichern")
        else:
            self.editor_warn.hide()
            self.save_button.set_label("Speichern")
        self.save_button.show()

    def cancel(self):
        self.window.stop_capture()
        self._pending = None
        self.hotkey_button.get_style_context().remove_class("editing")
        self.editor.hide()

    def _save(self):
        if self._pending:
            self._apply(self.store.set_hotkey(self.data["id"], self._pending, bin_dir()))

    def _reset(self):
        self._apply(self.store.reset_hotkey(self.data["id"], bin_dir()))

    def _remove(self):
        self._apply(self.store.set_hotkey(self.data["id"], "", bin_dir()))

    def _apply(self, result):
        ok, message = result
        self.cancel()
        if ok:
            self.window.notice(message or f"Hotkey für „{self.data['name']}“ gespeichert", error=bool(message))
            self.page.reload()
        else:
            self.window.notice(message, error=True)


class OverviewPage(Page):
    def __init__(self, window):
        super().__init__(window)
        self.search = Gtk.SearchEntry(placeholder_text="Suchen: Funktion, Hotkey, Beschreibung, Status …",
                                      width_chars=34)
        self.search.connect("search-changed", lambda *_: self._filter())
        self.pack_start(page_header("Übersicht", self.search), False, False, 0)
        self.body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.pack_start(scrolled(self.body), True, True, 0)
        self.rows = []
        self.groups = []                          # (category header, [FunctionRow])

    def on_show(self):
        self.reload()

    def close_editors(self, except_row=None):
        for row in self.rows:
            if row is not except_row and row.editor.get_visible():
                row.cancel()

    def reload(self):
        """Read the register and the status again and draw everything (also the 'Aktualisieren' button)."""
        self.window.stop_capture()
        self.store.reload()
        data = self.window.island_registry()
        status = self.window.island_status()
        self.window.refresh_banners()
        clear(self.body)
        self.rows, self.groups = [], []
        self.body.pack_start(self._status_card(data, status), False, False, 0)
        order = []
        for row in data:
            if row["category"] not in order:
                order.append(row["category"])
        for category in order:
            header = label(category.upper(), ("cat-title",))
            self.body.pack_start(header, False, False, 0)
            rows = []
            for row_data in (r for r in data if r["category"] == category):
                widget = FunctionRow(self, row_data)
                rows.append(widget)
                self.rows.append(widget)
                self.body.pack_start(widget, False, False, 0)
            self.groups.append((header, rows))
        self.body.pack_start(self._gestures_tray(), False, False, 0)
        self.body.show_all()
        for row in self.rows:
            row.editor.hide()
            row.confirm.hide()
        self._filter()

    def _filter(self):
        query = self.search.get_text().strip()
        for header, rows in self.groups:
            shown = 0
            for row in rows:
                match = row.matches(query)
                row.set_visible(match)
                shown += match
            header.set_visible(bool(shown))

    # ---- what is running now ---------------------------------------------------------------------------------------------
    def _status_card(self, data, status):
        card = css_class(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6), "card")
        head = Gtk.Box(spacing=10)
        head.pack_start(label("Was läuft gerade", ("section-title",)), True, True, 0)
        head.pack_end(flat_button("Aktualisieren", (), self.reload), False, False, 0)
        card.pack_start(head, False, False, 0)
        if status is None:
            card.pack_start(label("MosIsland läuft nicht – kein Status.", ("dim",)), False, False, 0)
        else:
            running = [r for r in data if r["running"]]
            for r in running:
                line = Gtk.Box(spacing=8)
                line.pack_start(label("●", ("running-dot",)), False, False, 0)
                line.pack_start(label(f"{r['name']} – {r['status']}" if r["status"] else r["name"], wrap=True),
                                False, False, 0)
                card.pack_start(line, False, False, 0)
            if not running:
                card.pack_start(label("Gerade läuft nichts Besonderes.", ("dim",)), False, False, 0)
            off = [r["name"] for r in data if r["enabled"] is False]
            if off:
                card.pack_start(label("Ausgeschaltet: " + ", ".join(off), ("dim", "small"), wrap=True),
                                False, False, 4)
            card.pack_start(label(self._island_line(status), ("dim", "small"), wrap=True), False, False, 4)
        return card

    @staticmethod
    def _island_line(status):
        stats = proc_stats(status["pid"])
        up = status["uptime_s"]
        since = f"{up // 3600} h {up % 3600 // 60} min" if up >= 3600 else f"{max(1, up // 60)} min"
        if stats is None:
            return f"MosIsland {status['version']} · läuft seit {since}"
        return (f"MosIsland {status['version']} · läuft seit {since} · CPU Ø {stats['cpu_avg']:.1f} % seit dem Start · "
                f"RAM {stats['rss_mb']:.0f} MB" + (f" (PSS {stats['pss_mb']:.0f} MB)" if stats["pss_mb"] else "")
                + f" · gelesen um {time.strftime('%H:%M:%S')}")

    # ---- gestures and tray ---------------------------------------------------------------------------------------------------
    def _gestures_tray(self):
        card = css_class(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6), "card")
        head = Gtk.Box(spacing=10)
        head.pack_start(label("Gesten und Tray", ("section-title",)), True, True, 0)
        head.pack_end(flat_button("Gesten bearbeiten", (), lambda: self.window.show_tab("gestures")), False, False, 0)
        card.pack_start(head, False, False, 0)
        mapping = self.store.gesture_map()
        names = {fn.id: fn.name for fn in self.store.registry}
        if not self.store.config.flag("gestures_enabled"):
            card.pack_start(label("Gesten sind ausgeschaltet.", ("warn",)), False, False, 0)
        grid = Gtk.Grid(column_spacing=18, row_spacing=3)
        for i, (gesture, (title, _kind, _default)) in enumerate(gestures.GESTURES.items()):
            grid.attach(label(title), 0, i, 1, 1)
            grid.attach(label(action_label(gestures.action_for(gesture, mapping), names), ("dim",)), 1, i, 1, 1)
        card.pack_start(grid, False, False, 4)
        card.pack_start(label("Tray-Menü", ("title",)), False, False, 4)
        for line in TRAY_LINES:
            card.pack_start(label(line, ("dim", "small"), wrap=True), False, False, 0)
        return card


# =============================================================================
# Gesten
# =============================================================================
class GesturesPage(Page):
    def __init__(self, window):
        super().__init__(window)
        self.pack_start(page_header("Gesten"), False, False, 0)
        self.body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.pack_start(scrolled(self.body), True, True, 0)
        self._syncing = False

    def on_show(self):
        self.store.reload()
        self._syncing = True
        clear(self.body)
        top = css_class(Gtk.Box(spacing=12), "card")
        self.main_switch = Gtk.Switch(valign=Gtk.Align.CENTER, active=self.store.config.flag("gestures_enabled"))
        self.main_switch.connect("notify::active", self._on_main)
        top.pack_start(self.main_switch, False, False, 0)
        top.pack_start(label("Gesten auf der Pille", ("title",)), False, False, 0)
        top.pack_start(label("Wirken auf die eingeklappte Pille. Wer länger als einen Moment auf ihr verweilt, "
                             "klappt sie per Hover auf. Ein einfacher Klick öffnet sie immer.", ("dim", "small"),
                             wrap=True), True, True, 0)
        self.body.pack_start(top, False, False, 0)
        mapping = self.store.gesture_map()
        for gesture, (title, kind, default) in gestures.GESTURES.items():
            row = css_class(Gtk.Box(spacing=12), "function-row")
            text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            text.pack_start(label(title, ("title",)), False, False, 0)
            text.pack_start(label("Standard: " + action_label(default, {}), ("dim", "small")), False, False, 0)
            row.pack_start(text, True, True, 0)
            combo = Gtk.ComboBoxText()
            choices = action_choices(gesture, self.store.registry)
            for action_id, text_ in choices:
                combo.append(action_id, text_)
            combo.set_active_id(mapping[gesture])
            combo.connect("changed", self._on_changed, gesture)
            row.pack_start(combo, False, False, 0)
            self.body.pack_start(row, False, False, 0)
        self.body.show_all()
        self._syncing = False

    def _on_main(self, switch, _param):
        if self._syncing:
            return
        ok, message = self.store.set_value("gestures_enabled", switch.get_active())
        if not ok:
            self._syncing = True
            switch.set_active(not switch.get_active())
            self._syncing = False
        self.window.notice(message, error=True) if not ok else self.window.refresh_banners()

    def _on_changed(self, combo, gesture):
        if self._syncing or combo.get_active_id() is None:
            return
        ok, message = self.store.set_gesture(gesture, combo.get_active_id())
        self.window.notice(message, error=True) if not ok else self.window.refresh_banners()


# =============================================================================
# Funktionen
# =============================================================================
class FunctionsPage(Page):
    def __init__(self, window):
        super().__init__(window)
        self.pack_start(page_header("Funktionen"), False, False, 0)
        self.body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.pack_start(scrolled(self.body), True, True, 0)
        self._syncing = False

    def on_show(self):
        self.store.reload()
        self._syncing = True
        clear(self.body)
        cfg = self.store.config
        for group, fields in settingsmeta.GROUPS:
            self.body.pack_start(label(group.upper(), ("cat-title",)), False, False, 0)
            for field in fields:
                self.body.pack_start(self._field_row(field, cfg.get(field.key)), False, False, 0)
        self.body.show_all()
        self._syncing = False

    # ---- one row per setting ----------------------------------------------------------------------------------------------
    def _field_row(self, field, value):
        row = css_class(Gtk.Box(orientation=Gtk.Orientation.VERTICAL), "function-row")
        top = Gtk.Box(spacing=12)
        text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        text.pack_start(label(field.label, ("title",)), False, False, 0)
        notes = [n for n in (field.help, "wirkt nach dem Neustart der Insel" if field.restart else "") if n]
        if notes:
            text.pack_start(label(" · ".join(notes), ("dim", "small"), wrap=True), False, False, 0)
        top.pack_start(text, True, True, 0)
        error = label("", ("warn", "small"), wrap=True)
        error.set_no_show_all(True)
        widget = self._input(field, value, error)
        top.pack_end(widget, False, False, 0)
        row.pack_start(top, False, False, 0)
        row.pack_start(error, False, False, 0)
        return row

    def _save(self, field, value, widget, error):
        """Validate and save; an invalid value is marked red and kept out of the file."""
        ok, message = self.store.set_value(field.key, value)
        ctx = widget.get_style_context()
        (ctx.remove_class if ok else ctx.add_class)("invalid")
        error.set_text(message)
        error.set_visible(not ok)
        if not ok:
            self.window.notice(f"{field.label}: {message}", error=True)
        else:
            self.window.refresh_banners()
        return ok

    def _input(self, field, value, error):
        kind = field.kind
        if kind == "bool":
            switch = Gtk.Switch(valign=Gtk.Align.CENTER, active=bool(value))
            switch.connect("notify::active", lambda s, _p: None if self._syncing
                           else self._save(field, s.get_active(), s, error))
            return switch
        if kind in ("int", "float"):
            digits = 0 if kind == "int" else 2
            step = 1 if kind == "int" else 0.1
            adjustment = Gtk.Adjustment(value=float(value if isinstance(value, (int, float)) else field.low),
                                        lower=field.low, upper=field.high, step_increment=step, page_increment=step * 10)
            spin = Gtk.SpinButton(adjustment=adjustment, digits=digits, numeric=False)
            spin.set_width_chars(8)
            spin.connect("changed", lambda s: None if self._syncing else self._save(field, s.get_text(), s, error))
            return spin
        if kind == "choice":
            combo = Gtk.ComboBoxText.new_with_entry() if field.free else Gtk.ComboBoxText()
            for choice, text in field.choices:
                combo.append(str(choice), text)
            current = str(value) if value is not None else ""
            if combo.set_active_id(current) is False and field.free:
                combo.get_child().set_text(current)
            elif combo.get_active_id() is None and not field.free:
                combo.set_active(0)
            if field.free:
                entry = combo.get_child()
                entry.connect("activate", lambda e: self._save(field, e.get_text(), combo, error))
                entry.connect("focus-out-event", lambda e, _ev: self._save(field, e.get_text(), combo, error) and False)
                combo.connect("changed", lambda c: None if self._syncing or c.get_active_id() is None
                              else self._save(field, c.get_active_id(), c, error))
            else:
                combo.connect("changed", lambda c: None if self._syncing or c.get_active_id() is None
                              else self._save(field, c.get_active_id(), c, error))
            return combo
        entry = Gtk.Entry(width_chars=28, text=", ".join(value) if isinstance(value, list) else (value or ""))
        entry.connect("changed", lambda e: self._mark(field, e, error))
        entry.connect("activate", lambda e: self._save(field, e.get_text(), e, error))
        entry.connect("focus-out-event", lambda e, _ev: self._save_if_changed(field, e, error) and False)
        return entry

    def _mark(self, field, entry, error):
        """Live check while typing (red border); the file is written on Enter or when the field is left."""
        ok, _value, message = settingsmeta.validate(field.key, entry.get_text())
        ctx = entry.get_style_context()
        (ctx.remove_class if ok else ctx.add_class)("invalid")
        error.set_text("" if ok else message)
        error.set_visible(not ok)

    def _save_if_changed(self, field, entry, error):
        if not self._syncing:
            ok, _normalized, _message = settingsmeta.validate(field.key, entry.get_text())
            if ok:
                self._save(field, entry.get_text(), entry, error)
        return False
