"""Clipboard text actions: every action with an example, bad input, tracking parameters that must stay."""

import unittest

from tests import _sandbox  # noqa: F401  (must come first)
from island.services import textactions as t


def run(action, text, **kw):
    return t.apply(action, text, **kw)


class Actions(unittest.TestCase):
    def test_plain_keeps_the_text(self):
        self.assertEqual(run("plain", "Hallo\nWelt").text, "Hallo\nWelt")

    def test_case_actions(self):
        self.assertEqual(run("upper", "straße und mehr").text, "STRASSE UND MEHR")
        self.assertEqual(run("lower", "Über ALLES").text, "über alles")
        self.assertEqual(run("title", "don't PANIC, über-alles").text, "Don't Panic, Über-Alles")

    def test_json_pretty_and_compact_keep_the_order_and_umlauts(self):
        pretty = run("json-pretty", '{"b":1,"a":["ä",2]}').text
        self.assertEqual(pretty, '{\n  "b": 1,\n  "a": [\n    "ä",\n    2\n  ]\n}')
        self.assertEqual(run("json-compact", pretty).text, '{"b":1,"a":["ä",2]}')

    def test_broken_json_names_the_place_and_raises(self):
        with self.assertRaises(t.ActionError) as ctx:
            run("json-pretty", '{"a": 1,\n "b": }')
        self.assertIn("Zeile 2", str(ctx.exception))

    def test_url_encode_decode_round_trip(self):
        text = "a b&c=d/ü?"
        encoded = run("url-encode", text).text
        self.assertEqual(encoded, "a%20b%26c%3Dd%2F%C3%BC%3F")
        self.assertEqual(run("url-decode", encoded).text, text)

    def test_url_decode_of_invalid_utf8_is_refused(self):
        with self.assertRaises(t.ActionError):
            run("url-decode", "%FF%FE")

    def test_base64_round_trip_and_url_safe_alphabet_and_missing_padding(self):
        encoded = run("base64-encode", "Grüße ÿ").text
        self.assertEqual(run("base64-decode", encoded).text, "Grüße ÿ")
        self.assertEqual(run("base64-decode", "aGFsbG8").text, "hallo")            # no padding
        self.assertEqual(run("base64-decode", "Pz8_Pw").text, "????")              # '-' and '_' alphabet

    def test_base64_decode_of_rubbish_or_binary_is_refused(self):
        for bad in ("this is not base64!", "/9j/4AAQ"):                         # the second one is a JPEG header
            with self.assertRaises(t.ActionError):
                run("base64-decode", bad)

    def test_tidy_whitespace(self):
        text = "  Zeile   eins \t\n\n\n\n zwei  drei  \r\n"
        self.assertEqual(run("tidy", text).text, "Zeile eins\n\nzwei drei")

    def test_sort_and_unique_lines(self):
        self.assertEqual(run("sort", "b\nA\nc\na").text, "A\na\nb\nc")
        result = run("unique", "x\ny\nx\nz\ny")
        self.assertEqual(result.text, "x\ny\nz")
        self.assertIn("2 doppelte Zeilen", result.message)
        with self.assertRaises(t.ActionError):
            run("unique", "a\nb")
        with self.assertRaises(t.ActionError):
            run("sort", "only one line")

    def test_empty_clipboard_and_unknown_action(self):
        with self.assertRaises(t.ActionError):
            run("upper", "   \n ")
        with self.assertRaises(t.ActionError):
            run("nope", "x")


class TrackingLinks(unittest.TestCase):
    def test_removes_tracking_and_counts(self):
        text = "https://example.com/a?utm_source=x&id=5&fbclid=abc&utm_medium=m#top"
        result = run("clean-links", text)
        self.assertEqual(result.text, "https://example.com/a?id=5#top")
        self.assertEqual(result.message, "Link bereinigt, 3 Parameter entfernt")

    def test_functional_parameters_stay(self):
        text = "https://github.com/x/y/blob/main/a.py?ref=main&page=2&q=utm_source&v=1&t=30s"
        with self.assertRaises(t.ActionError):           # nothing to remove
            run("clean-links", text)

    def test_all_the_usual_suspects(self):
        for name in ("gclid", "mc_eid", "igshid", "ref_src", "msclkid", "utm_campaign", "UTM_Term"):
            url = f"https://e.org/?{name}=1&keep=2"
            self.assertEqual(run("clean-links", url).text, "https://e.org/?keep=2", name)

    def test_the_whole_query_can_go(self):
        self.assertEqual(run("clean-links", "https://e.org/p?utm_source=a&fbclid=b").text, "https://e.org/p")

    def test_links_in_running_text_and_punctuation_after_them(self):
        text = "Sieh https://a.org/x?utm_source=1, und (https://b.org/y?gclid=2). Fertig."
        self.assertEqual(run("clean-links", text).text, "Sieh https://a.org/x, und (https://b.org/y). Fertig.")

    def test_a_bracket_inside_the_link_stays(self):
        url = "https://de.wikipedia.org/wiki/Foo_(Bar)?utm_source=x"
        self.assertEqual(run("clean-links", url).text, "https://de.wikipedia.org/wiki/Foo_(Bar)")

    def test_the_configured_list_extends_the_builtin_one(self):
        url = "https://e.org/?affil=7&partner_id=3&keep=1"
        self.assertEqual(run("clean-links", url, extra_params=["affil", "partner_*"]).text, "https://e.org/?keep=1")
        self.assertEqual(run("clean-links", url, extra_params=["affil", 5, None, ""]).text,
                         "https://e.org/?partner_id=3&keep=1")

    def test_encoded_names_and_order_are_kept(self):
        url = "https://e.org/?b=%C3%A4&utm%5Fsource=1&a=2"
        self.assertEqual(run("clean-links", url).text, "https://e.org/?b=%C3%A4&a=2")

    def test_no_link_is_an_error(self):
        with self.assertRaises(t.ActionError):
            run("clean-links", "kein Link hier")


if __name__ == "__main__":
    unittest.main()
