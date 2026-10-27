"""Text actions for the clipboard: pure functions, nothing runs until one is called.

Each action takes the text and returns a Result (the new text and a short message for the card). An action
that cannot work raises ActionError; its message is shown on a card and the clipboard stays as it is.

The texts are German only, like the clip transfer's (they don't go through island/i18n.py).
"""

import base64
import binascii
import json
import re
from dataclasses import dataclass
from urllib.parse import quote, unquote

# Query parameters that only track you. Functional ones (page, id, q, ref, v, t …) are never touched.
TRACKING_PARAMS = frozenset({
    "fbclid", "gclid", "gclsrc", "dclid", "msclkid", "yclid", "twclid", "ttclid", "li_fat_id", "mc_eid", "mc_cid",
    "igshid", "igsh", "ref_src", "ref_url", "_hsenc", "_hsmi", "mkt_tok", "vero_id", "wickedid", "oly_enc_id",
    "oly_anon_id", "s_cid", "spm", "si", "feature", "pk_campaign", "pk_kwd", "mibextid", "_openstat",
})
TRACKING_PREFIXES = ("utm_", "pk_", "hsa_", "mtm_")
URL_RE = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)


class ActionError(Exception):
    """The action cannot be done; the message tells why (German, one line)."""


@dataclass(frozen=True)
class Result:
    text: str
    message: str            # the card's title, e.g. "Link bereinigt, 3 Parameter entfernt"


# ---- helpers ------------------------------------------------------------------------------------------
def tracking_matcher(extra=()):
    """A function name -> bool for the built-in list plus the config's extra names ('foo' or 'foo_*')."""
    names = set(TRACKING_PARAMS)
    prefixes = list(TRACKING_PREFIXES)
    for entry in extra or ():
        if not isinstance(entry, str) or not entry.strip():
            continue
        entry = entry.strip().lower()
        if entry.endswith("*"):
            prefixes.append(entry[:-1])
        else:
            names.add(entry)
    prefixes = tuple(p for p in prefixes if p)

    def tracked(name):
        name = name.lower()
        return name in names or name.startswith(prefixes)

    return tracked


def clean_url(url, tracked):
    """(url without tracking parameters, how many were removed). Everything else stays byte for byte."""
    base, hash_, fragment = url.partition("#")
    path, question, query = base.partition("?")
    if not question:
        return url, 0
    kept, removed = [], 0
    for part in query.split("&"):
        name = unquote(part.partition("=")[0].replace("+", " "))
        if part and tracked(name):
            removed += 1
        else:
            kept.append(part)
    if not removed:
        return url, 0
    cleaned = path + ("?" + "&".join(kept) if any(kept) else "")
    return cleaned + (hash_ + fragment if hash_ else ""), removed


def _split_tail(match_text):
    """(link, punctuation after it): a link in running text may end in marks that belong to the sentence."""
    link = match_text
    while link:
        last = link[-1]
        if last in ".,;:!?»›":
            link = link[:-1]
        elif last in ")]}" and link.count(last) > link.count({")": "(", "]": "[", "}": "{"}[last]):
            link = link[:-1]       # a bracket without its opening one inside is the sentence's
        else:
            break
    return link, match_text[len(link):]


# ---- the actions ----------------------------------------------------------------------------------------
def strip_formatting(text, **_):
    """Plain text only. The clipboard then holds just this text and no HTML/RTF any more."""
    return Result(text, "Formatierung entfernt")


def clean_links(text, extra_params=(), **_):
    tracked = tracking_matcher(extra_params)
    total, links = 0, 0

    def fix(match):
        nonlocal total, links
        url, tail = _split_tail(match.group(0))
        links += 1
        cleaned, removed = clean_url(url, tracked)
        total += removed
        return cleaned + tail

    result = URL_RE.sub(fix, text)
    if not links:
        raise ActionError("Kein Link gefunden")
    if not total:
        raise ActionError("Der Link ist schon sauber" if links == 1 else "Die Links sind schon sauber")
    return Result(result, f"{'Link' if links == 1 else 'Links'} bereinigt, "
                          f"{total} Parameter entfernt")


def upper(text, **_):
    return Result(text.upper(), "In GROSSBUCHSTABEN")


def lower(text, **_):
    return Result(text.lower(), "In Kleinbuchstaben")


WORD_RE = re.compile(r"[^\W_]+(?:['’][^\W_]+)*")


def title_case(text, **_):
    """Every word starts with a capital, the rest is small ("don't" stays "Don't", not "Don'T")."""
    return Result(WORD_RE.sub(lambda m: m.group(0)[:1].title() + m.group(0)[1:].lower(), text),
                  "In Titel-Schreibweise")


def _load_json(text):
    try:
        return json.loads(text)
    except json.JSONDecodeError as error:
        raise ActionError(f"Kein gültiges JSON · Zeile {error.lineno}, Spalte {error.colno}: {error.msg}") from None
    except RecursionError:
        raise ActionError("JSON zu tief verschachtelt") from None


def json_pretty(text, **_):
    return Result(json.dumps(_load_json(text), ensure_ascii=False, indent=2), "JSON formatiert")


def json_compact(text, **_):
    return Result(json.dumps(_load_json(text), ensure_ascii=False, separators=(",", ":")), "JSON zusammengefasst")


def url_encode(text, **_):
    return Result(quote(text, safe=""), "URL-kodiert")


def url_decode(text, **_):
    """%XX sequences back to characters."""
    return Result(_unquote_keep(text.strip()), "URL-dekodiert")


def _unquote_keep(text):
    try:
        return unquote(text, errors="strict")
    except UnicodeDecodeError:
        raise ActionError("Kein gültiges UTF-8 in der URL") from None


def base64_encode(text, **_):
    return Result(base64.b64encode(text.encode("utf-8")).decode("ascii"), "Base64-kodiert")


def base64_decode(text, **_):
    compact = re.sub(r"\s+", "", text)
    if not compact:
        raise ActionError("Kein Base64-Text")
    compact = compact.replace("-", "+").replace("_", "/")      # the URL-safe alphabet too
    compact += "=" * (-len(compact) % 4)
    try:
        raw = base64.b64decode(compact, validate=True)
        return Result(raw.decode("utf-8"), "Base64-dekodiert")
    except (binascii.Error, ValueError):
        raise ActionError("Kein gültiger Base64-Text (oder kein UTF-8 darin)") from None


def tidy_whitespace(text, **_):
    """Trailing and doubled spaces go, more than one blank line becomes one, the ends are trimmed."""
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace(" ", " ")
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n")]
    return Result(re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip(), "Leerzeichen und Zeilen bereinigt")


def sort_lines(text, **_):
    lines = text.splitlines()
    if len(lines) < 2:
        raise ActionError("Zum Sortieren braucht es mehrere Zeilen")
    return Result("\n".join(sorted(lines, key=lambda s: (s.casefold(), s))), f"{len(lines)} Zeilen sortiert")


def unique_lines(text, **_):
    lines, seen, kept = text.splitlines(), set(), []
    for line in lines:
        if line not in seen:
            seen.add(line)
            kept.append(line)
    if len(kept) == len(lines):
        raise ActionError("Keine doppelten Zeilen")
    gone = len(lines) - len(kept)
    return Result("\n".join(kept), f"{gone} doppelte {'Zeile' if gone == 1 else 'Zeilen'} entfernt")


# id -> (button label, function). "qr" is not here: it makes a picture and needs qrencode (see qr_available)
ACTIONS = {
    "plain": ("Formatierung entfernen", strip_formatting),
    "clean-links": ("Tracking aus Links entfernen", clean_links),
    "upper": ("GROSS", upper),
    "lower": ("klein", lower),
    "title": ("Titel-Schreibweise", title_case),
    "json-pretty": ("JSON formatieren", json_pretty),
    "json-compact": ("JSON zusammenfassen", json_compact),
    "url-encode": ("URL kodieren", url_encode),
    "url-decode": ("URL dekodieren", url_decode),
    "base64-encode": ("Base64 kodieren", base64_encode),
    "base64-decode": ("Base64 dekodieren", base64_decode),
    "tidy": ("Leerzeichen bereinigen", tidy_whitespace),
    "sort": ("Zeilen sortieren", sort_lines),
    "unique": ("Doppelte Zeilen entfernen", unique_lines),
}
QR_ID = "qr"
QR_LABEL = "QR-Code"
# A QR code holds a few KB at best; qrencode refuses more
QR_MAX_CHARS = 1200


def apply(action_id, text, extra_params=()):
    """Run an action. Returns a Result; raises ActionError (message for the card)."""
    if action_id not in ACTIONS:
        raise ActionError("Unbekannte Aktion")
    if not text or not text.strip():
        raise ActionError("Die Zwischenablage ist leer")
    result = ACTIONS[action_id][1](text, extra_params=extra_params)
    return result
