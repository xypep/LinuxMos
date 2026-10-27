"""The chat tab: questions to an OpenAI-compatible server (own API key), answers as they stream in.

Built the first time the tab opens (see LazyPage). The conversation lives in memory only: it is gone
when the island restarts or "New conversation" is pressed, and nothing is written to disk.
"""

from gi.repository import GLib, Gtk, Pango

from island.i18n import _
from island.pages import Page
from island.services import chat, keyring, ocr
from island.widgets import button, clear, css_class, label

BUBBLE_CHARS = 58          # text width of a bubble, in characters
COPIED_MS = 1500


class ChatPage(Page):
    def __init__(self, island):
        super().__init__(island, spacing=8)
        self.history = []            # {"role": "user" | "assistant", "content": text}
        self._request = None         # the running ChatRequest
        self._state = "idle"         # idle | waiting (for the keyring) | streaming
        self._answer = ""
        self._bot_label = None       # the label the answer streams into
        self._has_key = None         # None until the keyring answered

        top = Gtk.Box(spacing=4)
        self.status = label("", ("dim", "small"))
        top.pack_start(self.status, True, True, 0)
        top.pack_end(button("emblem-system-symbolic", tooltip=_("Verbindung & API-Key …"), css=("mini",), size=14,
                            on_click=island.ai_settings), False, False, 0)
        top.pack_end(button("edit-clear-all-symbolic", tooltip=_("Neues Gespräch"), css=("mini",), size=14,
                            on_click=self.new_chat), False, False, 0)
        self.pack_start(top, False, False, 0)

        self.messages = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.hint = label(_("Frag etwas. Der Chat spricht mit dem Server aus den Einstellungen (Zahnrad), "
                            "das Gespräch bleibt nur im Arbeitsspeicher."), ("dim",), xalign=0.5)
        self.hint.set_line_wrap(True)
        self.hint.set_justify(Gtk.Justification.CENTER)
        self.hint.set_valign(Gtk.Align.CENTER)
        self.scrolled = Gtk.ScrolledWindow(vexpand=True)
        self.scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        body.pack_start(self.hint, True, True, 0)
        body.pack_start(self.messages, False, False, 0)
        self.scrolled.add(body)
        self.pack_start(self.scrolled, True, True, 0)

        self.entry = Gtk.Entry(placeholder_text=_("Frag etwas …  (↵ sendet)"), hexpand=True)
        css_class(self.entry, "command")
        island.make_typeable(self.entry)
        self.entry.connect("activate", lambda *_: self.send())
        self.mic = button("audio-input-microphone-symbolic", tooltip=_("Diktat  (Ctrl+Alt+M)"), css=("circle",),
                          on_click=island.voice)
        self.send_button = button("mail-send-symbolic", css=("circle", "accent"), on_click=self._send_or_stop)
        row = Gtk.Box(spacing=6)
        row.pack_start(self.entry, True, True, 0)
        row.pack_start(self.mic, False, False, 0)
        row.pack_start(self.send_button, False, False, 0)
        self.pack_start(row, False, False, 0)

        self.mic.get_child().show()    # show_all() skips a no_show_all widget's children
        self.mic.set_no_show_all(True)
        self.refresh()

    # ---- state ---------------------------------------------------------------------
    def refresh(self):
        """Server or key changed: show where the questions go (and whether a key is missing)."""
        self.mic.set_visible(self.island.config.get("ai_voice", False))
        self._update_status()
        keyring.lookup(self._on_key_known)

    def _on_key_known(self, key):
        self._has_key = bool(key)
        self._update_status()

    def _update_status(self):
        config = self.island.config
        where = f"{chat.model(config)} · {chat.host(config)}"
        if self._has_key is False and not chat.is_local(config):
            where = _("Noch kein API-Key – Zahnrad oben rechts")
        self.status.set_text(where)

    def on_show(self):
        if self.island.is_active():
            self.focus_entry()

    def focus_entry(self):
        self.entry.grab_focus_without_selecting()
        self.entry.set_position(-1)

    def insert_text(self, text):
        """Dictated text goes into the question field, to be read before it is sent."""
        current = self.entry.get_text().strip()
        self.entry.set_text(f"{current} {text}".strip())
        self.focus_entry()

    # ---- conversation ---------------------------------------------------------------
    def new_chat(self):
        self._stop()
        self._finish()                    # whatever was still on its way is dropped (its callbacks see "idle")
        self.history.clear()
        clear(self.messages)
        self.hint.show()
        self.entry.set_text("")
        self.focus_entry()

    def _send_or_stop(self):
        if self._state == "idle":
            self.send()
        else:
            self._stop()

    def send(self):
        text = self.entry.get_text().strip()
        if not text or self._state != "idle":
            return
        self.entry.set_text("")
        self.hint.hide()
        self.history.append({"role": "user", "content": text})
        self._add_bubble("user", text)
        self._bot_label = self._add_bubble("assistant", "…")
        self._answer = ""
        self._state = "waiting"          # for the keyring, then "streaming"
        self._set_busy(True)
        keyring.lookup(lambda key: self._start(key, text))

    def _start(self, key, text):
        if self._state != "waiting":
            return    # stopped while the keyring was answering
        self._has_key = bool(key)
        if not key and not chat.is_local(self.island.config):
            self._fail(_("Kein API-Key gespeichert. Zahnrad oben rechts: „Verbindung & API-Key …“"), text)
            return
        self._state = "streaming"
        self._request = chat.ChatRequest(self._on_delta, lambda error: self._on_done(error, text))
        self._request.start(self.island.config, key, self.history)

    def _stop(self):
        """Stop button (or a new conversation) while an answer is on its way."""
        if self._state == "streaming":
            self._request.cancel()        # ends in _on_done()
        elif self._state == "waiting":
            self._withdraw(self.history[-1]["content"])

    def _on_delta(self, piece):
        self._answer += piece
        if self._bot_label is not None:
            self._bot_label.set_text(self._answer)
            self._scroll_down()

    def _on_done(self, error, text):
        self._request = None
        if self._state == "idle":
            return
        kind = error[0] if error else None
        if kind == "cancelled" and not self._answer:
            self._withdraw(text)          # nothing came: forget the question
        elif error and kind != "cancelled":
            self._fail(chat.describe(error), text)
        else:
            self.history.append({"role": "assistant", "content": self._answer})
            self._add_copy_button(self._bot_label, self._answer)
            self._finish()

    def _withdraw(self, text):
        """Take the last question and its empty answer back out and give the text to the entry."""
        for _i in range(2):
            rows = self.messages.get_children()
            if rows:
                rows[-1].destroy()
        if self.history and self.history[-1]["role"] == "user":
            self.history.pop()
        if not self.messages.get_children():
            self.hint.show()
        if not self.entry.get_text():
            self.entry.set_text(text)
        self._finish()

    def _fail(self, message, text):
        """Replace the waiting bubble by the error and give the question back to the entry."""
        if self._bot_label is not None:
            self._bot_label.set_text(message)
            css_class(self._bot_label, "chat-error")
        if self.history and self.history[-1]["role"] == "user":
            self.history.pop()
        if not self.entry.get_text():
            self.entry.set_text(text)
        self._finish()

    def _finish(self):
        self._state = "idle"
        self._bot_label = None
        self._set_busy(False)

    def _set_busy(self, busy):
        self.send_button.get_child().set_from_icon_name("media-playback-stop-symbolic" if busy
                                                        else "mail-send-symbolic", Gtk.IconSize.MENU)
        self.send_button.set_tooltip_text(_("Stopp") if busy else _("Senden"))

    # ---- bubbles ---------------------------------------------------------------------
    def _add_bubble(self, role, text):
        """A row with one bubble (and later a copy button); returns the bubble's label."""
        user = role == "user"
        lbl = Gtk.Label(label=text, xalign=0, selectable=True, wrap=True, wrap_mode=Pango.WrapMode.WORD_CHAR)
        lbl.set_max_width_chars(BUBBLE_CHARS)
        css_class(lbl, "chat-bubble", "chat-user" if user else "chat-bot")
        row = Gtk.Box(spacing=4)
        row.pack_start(lbl, False, False, 0)
        row.set_halign(Gtk.Align.END if user else Gtk.Align.START)
        self.messages.pack_start(row, False, False, 0)
        row.show_all()
        self._scroll_down()
        return lbl

    def _add_copy_button(self, bubble, text):
        btn = button("edit-copy-symbolic", tooltip=_("Antwort kopieren"), css=("mini",), size=14)

        def copy():
            if ocr.copy_text(text):
                btn.get_child().set_from_icon_name("object-select-symbolic", Gtk.IconSize.MENU)
                GLib.timeout_add(COPIED_MS, lambda: btn.get_child().set_from_icon_name(
                    "edit-copy-symbolic", Gtk.IconSize.MENU) or GLib.SOURCE_REMOVE)

        btn.connect("clicked", lambda *_: copy())
        btn.set_valign(Gtk.Align.END)
        bubble.get_parent().pack_start(btn, False, False, 0)
        btn.show_all()

    def _scroll_down(self):
        def go():
            adj = self.scrolled.get_vadjustment()
            adj.set_value(adj.get_upper() - adj.get_page_size())
            return GLib.SOURCE_REMOVE

        GLib.idle_add(go)
