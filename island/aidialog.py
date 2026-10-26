"""The "AI connection" dialog: server address, models and API key (the key goes to the keyring)."""

from gi.repository import GLib, Gtk

from island.i18n import _
from island.services import chat, keyring


def show(island):
    """Open the dialog; saving writes address and models to config.json and a typed key to the keyring."""
    config = island.config
    dialog = Gtk.Dialog(title=_("KI-Verbindung"))
    dialog.set_default_size(460, -1)
    dialog.add_button(_("Abbrechen"), Gtk.ResponseType.CANCEL)
    save = dialog.add_button(_("Speichern"), Gtk.ResponseType.OK)
    save.get_style_context().add_class("suggested-action")
    dialog.set_default_response(Gtk.ResponseType.OK)

    grid = Gtk.Grid(row_spacing=8, column_spacing=12, margin=16)
    entries = {}

    def row(n, key, text, value, placeholder, tooltip=None):
        lbl = Gtk.Label(label=text, xalign=0)
        entry = Gtk.Entry(text=value, placeholder_text=placeholder, hexpand=True, activates_default=True)
        if tooltip:
            entry.set_tooltip_text(tooltip)
        grid.attach(lbl, 0, n, 1, 1)
        grid.attach(entry, 1, n, 1, 1)
        entries[key] = entry
        return entry

    row(0, "url", _("Adresse"), (config.get("ai_base_url") or "").strip(), chat.DEFAULT_BASE,
        _("OpenAI-kompatibler Server, z. B. http://localhost:11434/v1 für Ollama"))
    row(1, "model", _("Chat-Modell"), (config.get("ai_model") or "").strip(), chat.DEFAULT_MODEL)
    row(2, "stt", _("Modell für Diktat"), (config.get("ai_stt_model") or "").strip(), chat.DEFAULT_STT_MODEL)
    key_entry = row(3, "key", _("API-Key"), "", "")
    key_entry.set_visibility(False)
    key_entry.set_input_purpose(Gtk.InputPurpose.PASSWORD)

    note = Gtk.Label(xalign=0, wrap=True, max_width_chars=58)
    text = _("Der Key liegt im Schlüsselbund, nicht in config.json. Fragen und Diktate gehen an die Adresse "
             "oben. Leer lassen = der gespeicherte Key bleibt. Ein lokaler Server braucht keinen Key.")
    note.set_markup(f"<small>{GLib.markup_escape_text(text)}</small>")
    grid.attach(note, 0, 4, 2, 1)
    remove = Gtk.Button(label=_("Key entfernen"))
    remove.set_halign(Gtk.Align.START)
    remove.set_sensitive(False)
    remove.connect("clicked", lambda _w: (island.remove_ai_key(), dialog.destroy()))
    grid.attach(remove, 0, 5, 2, 1)
    dialog.get_content_area().add(grid)

    # Tell whether a key is stored without ever showing it
    def known(key):
        if key:
            key_entry.set_placeholder_text(_("gespeichert (zum Ändern neuen Key eintippen)"))
            remove.set_sensitive(True)

    keyring.lookup(known)

    def on_response(_dlg, response):
        if response == Gtk.ResponseType.OK:
            island.apply_ai_settings(entries["url"].get_text(), entries["model"].get_text(),
                                     entries["stt"].get_text(), key_entry.get_text())
        dialog.destroy()

    dialog.connect("response", on_response)
    dialog.show_all()
    dialog.present()
