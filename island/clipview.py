"""The "Transfer" strip of the clipboard and shelf tabs: peer, last transfer, "Einrichten".

Built the first time one of those tabs opens, not at start-up. The choice of a peer is a row of buttons
inside the strip (a popup window would not wear the island's look and would fold the island away).
Texts are German only, like the rest of the clip transfer.
"""

from datetime import datetime

from gi.repository import Gtk, Pango

from island.services import clipcore as core
from island.widgets import button, icon, label


class TransferBar(Gtk.Box):
    def __init__(self, island, always=True):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.island = island
        self.always = always            # False (shelf): only while sending is on
        self._ask = None                # what to do with the chosen peer, while the question is up

        # The question "to which PC?"
        self.picker = Gtk.Revealer(transition_type=Gtk.RevealerTransitionType.SLIDE_UP, transition_duration=120)
        self.choices = Gtk.Box(spacing=6)
        self.picker.add(self.choices)
        self.pack_start(self.picker, False, False, 0)

        self.row = Gtk.Box(spacing=8)
        self.row.pack_start(icon("document-send-symbolic", 14), False, False, 0)
        self.summary = label("", ("small", "dim"), ellipsize=False)
        self.row.pack_start(self.summary, False, False, 0)
        self.peer_button = button(text="", tooltip="Standard-Peer (für den Hotkey) wechseln", css=("mini",),
                                  on_click=self._next_peer)
        self.peer_button.get_child().set_ellipsize(Pango.EllipsizeMode.END)
        self.peer_button.get_child().set_max_width_chars(16)
        self.row.pack_start(self.peer_button, False, False, 0)
        # Capped: a long text must not make the island wider than its window
        self.status = label("", ("small", "dim"), xalign=1.0, max_chars=36)
        self.row.pack_start(self.status, True, True, 0)
        self.setup_button = button(text="Einrichten", tooltip="Anleitung zum Einrichten", css=("mini",),
                                   on_click=self._setup)
        self.row.pack_end(self.setup_button, False, False, 0)
        self.pack_start(self.row, False, False, 0)
        self.show_all()
        self.set_no_show_all(True)
        self.refresh()

    # ---- state -----------------------------------------------------------------
    def refresh(self):
        island = self.island
        cfg = island.config
        send, receive = cfg.flag("clip_send_enabled"), cfg.flag("clip_receive_enabled")
        self.set_visible(self.always or send)
        parts = ["Transfer"] if send or receive else ["Transfer · aus"]
        if send or receive:
            parts += [f"Senden {'an' if send else 'aus'}", f"Empfang {'an' if receive else 'aus'}"]
        self.summary.set_text(" · ".join(parts))
        peers = core.peers(cfg)
        default = core.default_peer(cfg) or (peers[0] if peers else None)
        self.peer_button.set_visible(bool(send and default))
        if send and default:
            self.peer_button.get_child().set_text(f"→ {default['name']}")
            self.peer_button.set_sensitive(len(peers) > 1)
        self.setup_button.set_visible(not peers)
        self._show_status()

    def _show_status(self):
        clip = self.island.clip
        ctx = self.status.get_style_context()
        status = clip.status if clip else None
        ctx.remove_class("warning")
        if status is None:
            self.status.set_text("")
            return
        ok, text, when = status
        if ok is False:
            ctx.add_class("warning")
        stamp = "" if ok is None else f" · {datetime.fromtimestamp(when):%H:%M}"
        self.status.set_text(text + stamp)

    def _next_peer(self):
        peers = core.peers(self.island.config)
        if len(peers) < 2:
            return
        current = (core.default_peer(self.island.config) or peers[0])["name"]
        names = [p["name"] for p in peers]
        following = names[(names.index(current) + 1) % len(names)] if current in names else names[0]
        self.island.set_option("clip_default_peer", following)

    def _setup(self):
        self.island.collapse()
        if self.island.clip is not None:
            self.island.clip.setup_hint()
        else:
            self._lazy_setup_hint()

    def _lazy_setup_hint(self):
        from island.services.clipxfer import ClipTransfer     # the card code lives there
        ClipTransfer(self.island).setup_hint()

    # ---- the question "to which PC?" ----------------------------------------------------
    def request_send(self, do_send):
        """One peer (or none) sends at once; several ask first. do_send(peer) runs with the chosen one."""
        peers = core.peers(self.island.config)
        if len(peers) < 2:
            do_send(peers[0] if peers else None)
            return
        for child in self.choices.get_children():
            child.destroy()
        self.choices.pack_start(label("Senden an:", ("small", "dim"), ellipsize=False), False, False, 0)
        default = core.default_peer(self.island.config)
        for peer in peers:
            self.choices.pack_start(button(text=peer["name"], css=("accent",) if peer == default else (),
                                           on_click=lambda p=peer: self._chosen(do_send, p)), False, False, 0)
        self.choices.pack_start(button(text="Abbrechen", css=("mini",), on_click=self.cancel_question),
                                False, False, 0)
        self.choices.show_all()
        self.picker.set_reveal_child(True)

    def _chosen(self, do_send, peer):
        self.picker.set_reveal_child(False)
        do_send(peer)

    def cancel_question(self):
        self.picker.set_reveal_child(False)
