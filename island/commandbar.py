"""The command bar: one input field for apps, files, calculations, units, currencies and the web.

Built the first time the "Search" tab opens (see LazyPage), so it costs nothing until then.
Every key press searches again (Gtk.SearchEntry waits 150 ms for the typing to settle);
nothing runs in the background.
"""

import os

from gi.repository import Gdk, Gio, GLib, Gtk

from island import i18n
from island.i18n import _
from island.pages import Page
from island.services import calc, ocr
from island.services.finder import Finder, as_url, search_url, short_path
from island.widgets import clear, css_class, icon, label

ICON_SIZE = 24
APP_LIMIT, FILE_LIMIT = 5, 5


class Result:
    """One row: run() on Enter or click, alt() on Ctrl+Enter (if there is one)."""

    def __init__(self, kind, icon_spec, title, subtitle, run, alt=None):
        self.kind, self.icon, self.title, self.subtitle = kind, icon_spec, title, subtitle
        self.run, self.alt = run, alt


class CommandPage(Page):
    def __init__(self, island):
        super().__init__(island, spacing=8)
        self.finder = Finder(self._on_files_ready)
        self.rates = calc.Rates()

        self.entry = Gtk.SearchEntry(placeholder_text=_("Apps, Dateien, Rechnen, Web …"), hexpand=True)
        css_class(self.entry, "command")
        island.make_typeable(self.entry)
        self.entry.connect("search-changed", lambda *_: self.refresh())
        self.entry.connect("key-press-event", self._on_key)
        self.pack_start(self.entry, False, False, 0)

        self.listbox = Gtk.ListBox(selection_mode=Gtk.SelectionMode.BROWSE)
        self.listbox.set_activate_on_single_click(True)
        self.listbox.connect("row-activated", lambda _lb, row: self._run(row.result))
        hint = label(_("Apps starten · Dateien finden · 12*7 · 5 km in mi · 20 usd in eur · Websuche"),
                     ("dim",), xalign=0.5)
        hint.set_line_wrap(True)
        hint.show()
        self.listbox.set_placeholder(hint)
        self.scrolled = Gtk.ScrolledWindow(vexpand=True)
        self.scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.scrolled.add(self.listbox)
        self.pack_start(self.scrolled, True, True, 0)

        footer = label(_("↵ öffnen · Ctrl+↵ einfügen bzw. im Ordner zeigen · Esc schließt"),
                       ("dim", "small"), xalign=0.5)
        self.pack_end(footer, False, False, 0)
        self.refresh()

    def on_show(self):
        if self.island.is_active():
            self.focus_entry()

    def focus_entry(self):
        self.entry.grab_focus()  # selects the last query: typing replaces it

    # ---- results ---------------------------------------------------------------
    def refresh(self):
        query = self.entry.get_text().strip()
        clear(self.listbox)
        for result in self._results(query):
            self.listbox.add(self._row(result))
        self.listbox.show_all()
        first = next((r for r in self.listbox.get_children() if r.get_sensitive()), None)
        if first is not None:
            self.listbox.select_row(first)
        self.scrolled.get_vadjustment().set_value(0)

    def _results(self, query):
        if not query:
            return [self._app_result(a) for a in self.finder.apps("", APP_LIMIT)]
        answers = self._answers(query)
        results = answers + [self._app_result(a) for a in self.finder.apps(query, APP_LIMIT)]
        # "5 km in mi" is no file name: no file scan for calculations and conversions
        if not answers and self.island.config.get("command_bar_files", True):
            results += [self._file_result(path, is_dir) for path, is_dir in self.finder.files(query, FILE_LIMIT)]
            if self.finder.scanning:
                results.append(Result("", "content-loading-symbolic", _("Dateien werden gesucht …"), "", None))
        url = as_url(query)
        if url:
            results.append(Result(_("Web"), "web-browser-symbolic", _("Website öffnen"), url,
                                  lambda: self._open_uri(url)))
        engine, search = search_url(self.island.config, query)
        results.append(Result(_("Web"), "system-search-symbolic", _("„{query}“ im Web suchen").format(query=query),
                              engine, lambda: self._open_uri(search)))
        return results

    def _answers(self, query):
        """Calculation, unit or currency conversion at the top."""
        comma = i18n.current() == "de"
        value = calc.evaluate(query)
        if value is not None:
            text = calc.format_number(value, comma)
            return [self._copy_result(_("Rechner"), "accessories-calculator-symbolic", f"= {text}", query, text)]
        converted = calc.convert(query)
        if converted:
            amount, src, result, dst = converted
            text = calc.format_number(result, comma, digits=6)
            title = f"{calc.format_number(amount, comma)} {src} = {text} {dst}"
            return [self._copy_result(_("Einheit"), "view-refresh-symbolic", title, _("Umrechnung"), text)]
        if not self.island.config.get("command_bar_currency", True):
            return []
        money = calc.currency_query(query)
        if not money:
            return []
        amount, src, dst = money
        pending = self.rates.ensure(lambda _ok, q=query: self._requery(q))
        result = self.rates.convert(amount, src, dst)
        if result is None:
            text = _("Wechselkurse werden geladen …") if pending else _("Wechselkurse nicht erreichbar (offline?)")
            return [Result(_("Währung"), "network-transmit-receive-symbolic", text, "frankfurter.dev", None)]
        text = f"{result:,.2f}"
        if comma:
            text = text.replace(",", " ").replace(".", ",").replace(" ", ".")
        title = f"{calc.format_number(amount, comma)} {src} = {text} {dst}"
        subtitle = _("EZB-Kurs vom {date}").format(date=self.rates.date) if self.rates.date else ""
        return [self._copy_result(_("Währung"), "accessories-calculator-symbolic", title, subtitle, text)]

    def _requery(self, query):
        if self.get_mapped() and self.entry.get_text().strip() == query:
            self.refresh()

    def _on_files_ready(self):
        self._requery(self.entry.get_text().strip())

    def _copy_result(self, kind, icon_name, title, subtitle, text):
        return Result(kind, icon_name, title, subtitle, lambda: self._copy(text),
                      alt=lambda: self.island.paste_text(text))

    def _app_result(self, app):
        subtitle = app.get_description() or (app.get_generic_name() if isinstance(app, Gio.DesktopAppInfo) else "")
        return Result(_("App"), app.get_icon() or "application-x-executable", app.get_name(), subtitle or "",
                      lambda: self._launch(app))

    def _file_result(self, path, is_dir):
        if is_dir:
            gicon = "folder"
        else:
            content_type, _uncertain = Gio.content_type_guess(path, None)
            gicon = Gio.content_type_get_icon(content_type)
        name = os.path.basename(path)
        return Result(_("Ordner") if is_dir else _("Datei"), gicon, name, short_path(os.path.dirname(path)),
                      lambda: self._open_uri(GLib.filename_to_uri(path)),
                      alt=lambda: self._reveal(path))

    def _row(self, result):
        row = Gtk.ListBoxRow()
        row.result = result
        box = Gtk.Box(spacing=10)
        if isinstance(result.icon, Gio.Icon):
            img = Gtk.Image.new_from_gicon(result.icon, Gtk.IconSize.DND)
            img.set_pixel_size(ICON_SIZE)
        else:
            img = icon(result.icon, ICON_SIZE if not result.icon.endswith("-symbolic") else 18)
            img.set_size_request(ICON_SIZE, ICON_SIZE)
        box.pack_start(img, False, False, 0)
        text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, valign=Gtk.Align.CENTER)
        text.pack_start(label(result.title, max_chars=50), False, False, 0)
        if result.subtitle:
            text.pack_start(label(result.subtitle, ("dim", "small"), max_chars=60), False, False, 0)
        box.pack_start(text, True, True, 0)
        if result.kind:
            box.pack_end(label(result.kind, ("dim", "small"), ellipsize=False), False, False, 0)
        row.add(box)
        row.set_sensitive(result.run is not None)
        return row

    # ---- keyboard ----------------------------------------------------------------
    def _on_key(self, _entry, event):
        key = event.keyval
        if key in (Gdk.KEY_Down, Gdk.KEY_Up):
            self._move(1 if key == Gdk.KEY_Down else -1)
            return True
        if key in (Gdk.KEY_Return, Gdk.KEY_KP_Enter, Gdk.KEY_ISO_Enter):
            row = self.listbox.get_selected_row()
            if row is not None:
                alt = event.state & Gdk.ModifierType.CONTROL_MASK
                self._run(row.result, alt=bool(alt))
            return True
        return False

    def _move(self, step):
        rows = [r for r in self.listbox.get_children() if r.get_sensitive()]
        if not rows:
            return
        current = self.listbox.get_selected_row()
        i = rows.index(current) + step if current in rows else 0
        row = rows[max(0, min(len(rows) - 1, i))]
        self.listbox.select_row(row)
        # Keep the selected row in view; the focus stays in the entry
        alloc, adj = row.get_allocation(), self.scrolled.get_vadjustment()
        adj.clamp_page(alloc.y, alloc.y + alloc.height)

    # ---- actions -------------------------------------------------------------------
    def _run(self, result, alt=False):
        action = result.alt if alt and result.alt else result.run
        if action:
            action()

    def _launch(self, app):
        self.finder.launched(app)
        self.island.leave()
        try:
            app.launch([], self.island.launch_context())
        except GLib.Error:
            self.island.show_activity("dialog-warning-symbolic",
                                      _("{app} lässt sich nicht starten").format(app=app.get_name()), seconds=4)

    def _open_uri(self, uri):
        self.island.leave()
        try:
            Gio.AppInfo.launch_default_for_uri(uri, self.island.launch_context())
        except GLib.Error:
            self.island.show_activity("dialog-warning-symbolic", _("Lässt sich nicht öffnen"), seconds=4)

    def _reveal(self, path):
        self.island.leave()
        self.island.reveal_file(path)

    def _copy(self, text):
        if ocr.copy_text(text):
            self.island.collapse()
            self.island.show_activity("edit-copy-symbolic", _("Kopiert · {text}").format(text=text))
