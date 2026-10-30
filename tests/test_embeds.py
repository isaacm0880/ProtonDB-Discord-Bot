import unittest
import stubs; stubs.install()
import config, embeds
from models import *

BAD = "@everyone <@123456789012345678> **bold** [x](http://evil.example) " + "lorem ipsum " * 400


def all_text(e):
    parts = [e.title or "", e.description or "", e.footer.text or ""]
    for f in e.fields:
        parts += [f.name, f.value]
    return "\n".join(parts)


def app(**kw):
    base = dict(appid=10, name="Game", short_description=BAD, header_image="https://x/h.jpg",
                developers=["D"] * 50, publishers=["P"], genres=["G"] * 80, release_date="1 Jan, 2020",
                price=Price("GBP", 2999, 1499, 50, "£29.99", "£14.99"),
                requirements_min="<ul><li><strong>OS:</strong> " + "w" * 3000 + "</li></ul>",
                requirements_rec="<b>Recommended:</b><br>RAM: 8 GB")
    base.update(kw)
    return SteamApp(**base)


class Embeds(unittest.TestCase):
    def check(self, e):
        self.assertEqual(stubs.validate_embed(e), [])
        self.assertEqual(e.colour.value, 0xB45D1F)
        t = all_text(e)
        self.assertNotIn("@e", t); self.assertNotIn("<@1", t); self.assertNotIn("](http://evil", t)

    def test_steam_main(self):
        e = embeds.build_steam_embed(app(), ReviewSummary("Very Positive", 90, 10, 100), False)
        self.check(e)
        names = [f.name for f in e.fields]
        for n in ("Steam App ID", "Price", "Release date", "Steam user reviews", "Developer", "Publisher", "Genres", "Store page"):
            self.assertIn(n, names)
        t = all_text(e)
        self.assertIn("90% positive", t); self.assertIn("~~£29.99~~ **£14.99** (-50%)", t)
        self.assertEqual(e.image.url, "https://x/h.jpg")

    def test_steam_free_missing_and_review_states(self):
        e = embeds.build_steam_embed(SteamApp(appid=1, is_free=True), None, True)
        self.check(e)
        t = all_text(e)
        self.assertIn("Free to Play", t); self.assertIn("Currently unavailable from Steam", t)
        self.assertIn("Not available", t)
        self.assertIn("No user reviews yet", embeds.review_summary_text(ReviewSummary(None, 0, 0, 0)))
        self.assertIn("Price unavailable", embeds.price_text(SteamApp(appid=1)))
        self.assertIn("Not yet released", embeds.price_text(SteamApp(appid=1, coming_soon=True)))
        self.assertIn("19.99 GBP", embeds.price_text(SteamApp(appid=1, price=Price("GBP", None, 1999))))

    def test_requirements(self):
        e = embeds.build_requirements_embed(app())
        self.check(e)
        self.assertEqual([f.name for f in e.fields], ["Minimum", "Recommended"])
        self.assertTrue(e.fields[1].value.startswith("RAM"))  # header line removed
        none = embeds.build_requirements_embed(SteamApp(appid=1, name="X"))
        self.check(none); self.assertIn("doesn't list", none.description)
        only_min = embeds.build_requirements_embed(SteamApp(appid=1, requirements_min="CPU: x"))
        self.assertEqual(only_min.fields[1].value, "Not published.")

    def test_reviews(self):
        revs = [Review(True, BAD, 1700000000, 1234, 3), Review(False, "bad", None, None), Review(None, "x")]
        e = embeds.build_reviews_embed("G", 10, ReviewSummary("Mixed", 5, 5, 10), False, revs, False)
        self.check(e)
        t = all_text(e)
        self.assertIn("Recommended", t); self.assertIn("Not recommended", t)
        self.assertIn("steamcommunity.com/app/10/reviews", t)
        for r, u in ((None, True), ([], False)):
            e = embeds.build_reviews_embed("G", 10, None, True, r, u)
            self.check(e)

    def test_news(self):
        items = [NewsItem("123", BAD[:300], "https://steamstore-a.akamaihd.net/news/externalpost/steam_community_announcements/123",
                          "[p]" + BAD + "[/p]", 1700000000, "Community Announcements", "steam_community_announcements"),
                 NewsItem("9", "Ext", "https://site.example/a(b)", "<p>Hello</p>", 1700000001, "PC Site", "pcsite")] * 3
        e = embeds.build_news_embed("G" * 300, 10, items)
        self.check(e)
        self.assertEqual(len(e.fields), 5)
        t = all_text(e)
        self.assertIn("store.steampowered.com/news/app/10/view/123", t)
        self.assertIn("https://site.example/a%28b%29", t)
        empty = embeds.build_news_embed("G", 10, [])
        self.check(empty); self.assertIn("No recent", empty.description)

    def test_protondb(self):
        reports = ReportsResult([ProtonReport(1700000000, "yes", None, "9.0-4", "RX 7800 · Arch", BAD),
                                 ProtonReport(None, "no", "borked", None, None, None)], True)
        e = embeds.build_protondb_embed(10, "G", ProtonSummary("gold", "platinum", "platinum", "strong", 0.71, 3441),
                                        None, reports, app())
        self.check(e)
        t = all_text(e)
        self.assertIn("Gold", t); self.assertIn("3,441", t); self.assertIn("protondb.com/app/10", t)
        self.assertIn("Proton 9.0-4", t); self.assertIn("PROTON_LOG=1", t)
        self.assertNotIn("deck", t.lower())

    def test_protondb_degraded(self):
        for summary, err, rep in ((None, None, ReportsResult(ok=False, reason="x")),
                                  (None, "ProtonDB is rate limiting requests", ReportsResult(ok=True)),
                                  (ProtonSummary(), None, ReportsResult(ok=False)),
                                  (ProtonSummary(tier="weird"), None, ReportsResult(ok=False))):
            e = embeds.build_protondb_embed(10, "G", summary, err, rep, None)
            self.check(e)
            self.assertIn("protondb.com/app/10", all_text(e))
            self.assertNotIn("deck", all_text(e).lower())

    def test_enforce_limits_shrinks_huge_embed(self):
        e = embeds.new_embed(title="t" * 500, description="d" * 9000)
        for i in range(30):
            e.add_field(name="n" * 300, value="v" * 1000, inline=False)
        embeds.enforce_limits(e)
        self.assertEqual(stubs.validate_embed(e), [])

    def test_error_embed_uses_colour(self):
        e = embeds.error_embed("x" * 5000)
        self.check(e)


if __name__ == "__main__":
    unittest.main()
