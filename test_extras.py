import unittest
from unittest import mock

import extras


class ExtrasTests(unittest.TestCase):
    def test_system_extra_defaults_and_levels(self):
        self.assertTrue("HALKA" in extras.system_extra("Coder", "Halka"))
        self.assertTrue("coding buddy" in extras.system_extra("Coder", "Halka"))
        fallback = extras.system_extra("nope", "nope")
        self.assertTrue("MEDIUM" in fallback and "funny desi friend" in fallback)


    def test_teekha_keeps_safety_limits(self):
        self.assertTrue("protected traits" in extras.ROAST_LEVELS["Teekha"])


    def test_find_urls_dedupes_strips_and_limits(self):
        text = "dekh https://a.com/x. aur https://a.com/x, https://b.org/p?q=1) https://c.io"
        self.assertEqual(extras.find_urls(text), ["https://a.com/x", "https://b.org/p?q=1"])
        self.assertEqual(extras.find_urls("no links"), [])


    def test_html_to_text_drops_scripts_and_keeps_title(self):
        raw = "<html><head><title>Hi &amp; bye</title></head><body><script>x=1</script><p>Hello</p><div>World</div></body></html>"
        title, text = extras.html_to_text(raw)
        self.assertEqual(title, "Hi & bye")
        self.assertEqual(text.split("\n"), ["Hello", "World"])


    def test_private_hosts_blocked(self):
        for host in ("localhost", "127.0.0.1", "10.0.0.5", "169.254.169.254", "192.168.1.1"):
            self.assertFalse(extras.is_public_host(host))
        self.assertFalse(extras.is_public_host(""))


    def test_read_page_rejects_bad_and_private(self):
        self.assertTrue("error" in extras.read_page("ftp://example.com/x"))
        self.assertTrue("error" in extras.read_page("http://127.0.0.1:8501/"))
        self.assertTrue("error" in extras.read_page("http://169.254.169.254/latest/meta-data"))


    def test_read_page_success_and_never_raises(self):
        class Resp:
            headers = {"Content-Type": "text/html; charset=utf-8"}
            def read(self, n): return b"<title>T</title><p>Body text</p>"
            def __enter__(self): return self
            def __exit__(self, *a): return False

        class Opener:
            def open(self, req, timeout=0): return Resp()

        with mock.patch.object(extras, "is_public_host", return_value=True), \
             mock.patch.object(extras.urllib.request, "build_opener", return_value=Opener()):
            page = extras.read_page("https://example.com")
        self.assertEqual(page, {"url": "https://example.com", "title": "T", "text": "Body text"})

        class Boom:
            def open(self, req, timeout=0): raise extras.urllib.error.URLError("down")

        with mock.patch.object(extras, "is_public_host", return_value=True), \
             mock.patch.object(extras.urllib.request, "build_opener", return_value=Boom()):
            self.assertTrue("error" in extras.read_page("https://example.com"))


    def test_format_pages_skips_errors(self):
        self.assertEqual(extras.format_pages([{"url": "u", "error": "x"}]), "")
        out = extras.format_pages([{"url": "https://e.com", "title": "E", "text": "hello"}])
        self.assertTrue("[page #1] E" in out and "untrusted" in out)


if __name__ == '__main__':
    unittest.main()
