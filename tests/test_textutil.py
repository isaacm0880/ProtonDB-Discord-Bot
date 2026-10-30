import unittest
import stubs; stubs.install()
from textutil import *


class T(unittest.TestCase):
    def test_html(self):
        raw = '<strong>Minimum:</strong><br><ul class="bb_ul"><li><strong>OS *:</strong> Win 10<br></li><li>RAM: 4 GB</li></ul>'
        out = compact_lines(html_to_text(raw))
        self.assertIn("• OS *: Win 10", out)
        self.assertNotIn("<", out)
        self.assertEqual(html_to_text("a &amp; b &quot;c&quot;"), 'a & b "c"')
        self.assertEqual(html_to_text("i < 5 and j > 3"), "i < 5 and j > 3")
        self.assertEqual(html_to_text(None), "")

    def test_bbcode(self):
        out = bbcode_to_text("[h1]Hi[/h1] [img]{STEAM_CLAN_IMAGE}/a.png[/img][url=http://x]link[/url] [b]bold[/b] [url=https://cut")
        self.assertEqual(out, "Hi link bold")

    def test_news_preview_limit_and_urls(self):
        out = news_preview("[p]" + "word " * 200 + " https://spam.example/x[/p]", 100)
        self.assertLessEqual(len(out), 100)
        self.assertNotIn("http", out)

    def test_neutralise(self):
        out = neutralise("@everyone @here <@123456789012345678> [a](http://e.com)")
        self.assertNotIn("@e", out); self.assertNotIn("@h", out); self.assertNotIn("](", out)

    def test_truncate(self):
        for n in (1, 5, 30, 1000):
            self.assertLessEqual(len(truncate("lorem ipsum " * 300, n)), n)
        self.assertEqual(truncate("short", 10), "short")

    def test_choice_label(self):
        label = choice_label("X" * 300, 1245620)
        self.assertLessEqual(len(label), 100)
        self.assertTrue(label.endswith("(App 1245620)"))

    def test_safe_url(self):
        self.assertIsNone(safe_http_url("javascript:alert(1)"))
        self.assertIsNone(safe_http_url("https://a b"))
        self.assertEqual(safe_http_url("https://a.b/x)"), "https://a.b/x%29")


if __name__ == "__main__":
    unittest.main()
