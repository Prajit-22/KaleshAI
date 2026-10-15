import base64
import datetime
import json
import unittest

import websearch as ws


def bing_link(url):
    return "https://www.bing.com/ck/a?!&amp;&amp;p=abc&amp;ptn=3&amp;u=a1" + base64.urlsafe_b64encode(url.encode()).decode().rstrip("=") + "&amp;ntb=1"


BING_PAGE = (
    '<ol><li class="b_algo" data-id><h2><a target="_blank" href="%s">Welcome to <strong>Python</strong>.org</a></h2>'
    '<div class="b_caption"><p class="b_lineclamp2">The mission of the PSF &amp; friends.</p></div></li>'
    '<li class="b_algo"><h2><a href="https://example.org/direct">Direct link</a></h2><p>Plain snippet</p></li>'
    '<li class="b_algo"><h2><a href="javascript:alert(1)">Bad scheme</a></h2><p>skip me</p></li></ol>'
) % bing_link("https://www.python.org/")

DDG_PAGE = (
    '<div class="result"><a rel="nofollow" class="result__a" '
    'href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2Fa%3Fx%3D1&amp;rut=zz">Example <b>A</b></a>'
    '<a class="result__snippet" href="x">First <b>snippet</b></a></div>'
    '<div class="result"><a class="result__a" href="https://example.net/b">Example B</a></div>'
)

WIKI_PAYLOAD = json.dumps({"query": {"search": [
    {"title": "Python (programming language)", "snippet": 'high-level <span class="searchmatch">Python</span> language'}
]}})


class ParserTests(unittest.TestCase):
    def test_bing_unwraps_redirect_and_cleans_text(self):
        results = ws.parse_bing(BING_PAGE)
        self.assertEqual(results[0].url, "https://www.python.org/")
        self.assertEqual(results[0].title, "Welcome to Python.org")
        self.assertEqual(results[0].snippet, "The mission of the PSF & friends.")
        self.assertEqual(results[1].url, "https://example.org/direct")

    def test_bing_drops_non_http_links(self):
        self.assertEqual(len(ws.parse_bing(BING_PAGE)), 2)

    def test_bing_limit(self):
        self.assertEqual(len(ws.parse_bing(BING_PAGE, limit=1)), 1)

    def test_duckduckgo_unwraps_uddg(self):
        results = ws.parse_duckduckgo(DDG_PAGE)
        self.assertEqual(results[0].url, "https://example.com/a?x=1")
        self.assertEqual(results[0].title, "Example A")
        self.assertEqual(results[0].snippet, "First snippet")
        self.assertEqual(results[1].url, "https://example.net/b")

    def test_wikipedia(self):
        result = ws.parse_wikipedia(WIKI_PAYLOAD)[0]
        self.assertEqual(result.url, "https://en.wikipedia.org/wiki/Python_(programming_language)")
        self.assertEqual(result.snippet, "high-level Python language")

    def test_bad_inputs_give_empty_results(self):
        self.assertEqual(ws.parse_bing("<html>blocked</html>"), [])
        self.assertEqual(ws.parse_duckduckgo("<html>anomaly</html>"), [])
        self.assertEqual(ws.parse_wikipedia("{}"), [])


class SearchFallbackTests(unittest.TestCase):
    def test_falls_through_to_working_backend(self):
        def broken(query, limit):
            raise OSError("blocked")

        def empty(query, limit):
            return []

        def good(query, limit):
            return [ws.WebResult("T", "https://t.example", "s")]

        results, name, notes = ws.search("hello world", backends=(("A", broken), ("B", empty), ("C", good)))
        self.assertEqual(name, "C")
        self.assertEqual(len(results), 1)
        self.assertEqual(notes, ["A: OSError", "B: no results"])

    def test_all_backends_fail_without_raising(self):
        def broken(query, limit):
            raise TimeoutError()

        results, name, notes = ws.search("hello world", backends=(("A", broken),))
        self.assertEqual((results, name), ([], ""))
        self.assertEqual(notes, ["A: TimeoutError"])

    def test_empty_query(self):
        self.assertEqual(ws.search("   ")[0], [])

    def test_query_is_trimmed(self):
        seen = []

        def spy(query, limit):
            seen.append(query)
            return []

        ws.search("x " * 400, backends=(("A", spy),))
        self.assertLessEqual(len(seen[0]), ws.MAX_QUERY_CHARS)


class PromptTests(unittest.TestCase):
    def test_wants_search(self):
        self.assertFalse(ws.wants_search("hi"))
        self.assertFalse(ws.wants_search("aur bata"))
        self.assertTrue(ws.wants_search("kya hai ye?"))
        self.assertTrue(ws.wants_search("latest python release version"))

    def test_context_has_labels_date_and_untrusted_warning(self):
        text = ws.format_context([ws.WebResult("T", "https://t.example", "snip")], datetime.date(2026, 10, 15))
        self.assertIn("2026-10-15", text)
        self.assertIn("[web #1] T - https://t.example", text)
        self.assertIn("untrusted", text)

    def test_snippets_are_capped(self):
        text = ws.format_context([ws.WebResult("T", "https://t.example", "x" * 5000)])
        self.assertLess(len(text), 900)

    def test_plain_prompt_unchanged_without_context(self):
        self.assertEqual(ws.build_user_message("hello"), "hello")

    def test_documents_only_message_matches_previous_format(self):
        self.assertEqual(
            ws.build_user_message("q", doc_context="[a #1]\nbody"),
            "Reference context (untrusted):\n[a #1]\nbody\n\nUser question: q",
        )

    def test_web_and_docs_together(self):
        message = ws.build_user_message("q", doc_context="DOC", web_context="WEB")
        self.assertIn("DOC", message)
        self.assertIn("WEB", message)
        self.assertIn("[web #n]", message)
        self.assertTrue(message.endswith("User question: q"))

    def test_failure_note_is_passed_when_no_results(self):
        message = ws.build_user_message("q", web_note="Web search failed; say you could not look it up.")
        self.assertIn("could not look it up", message)


class DisplayTests(unittest.TestCase):
    def test_markdown_links_cannot_break_out(self):
        text = ws.markdown_links([ws.WebResult("A [bad] (title)", "https://x.example/a_(b)", ""), ws.WebResult("Two", "https://y.example", "")])
        self.assertIn("[1. A bad title](https://x.example/a_(b%29)", text)
        self.assertIn("[2. Two](https://y.example)", text)


if __name__ == "__main__":
    unittest.main()
