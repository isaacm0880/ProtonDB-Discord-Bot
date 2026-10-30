import unittest
import stubs; stubs.install()
from models import BadResponse
from parsers import *


class Steam(unittest.TestCase):
    def test_search_filters_and_dedupes(self):
        p = {"items": [{"type": "app", "id": 730, "name": "CS2"}, {"type": "app", "id": 730, "name": "dup"},
                       {"type": "bundle", "id": 5, "name": "B"}, {"id": "x", "name": "bad"}, "junk",
                       {"id": 10, "name": "  "}, {"id": 20, "name": "Ok"}]}
        self.assertEqual([r.appid for r in parse_search(p)], [730, 20])
        self.assertEqual(parse_search(None), [])
        self.assertEqual(parse_search({"items": "x"}), [])
        self.assertEqual(len(parse_search({"items": [{"id": i, "name": "n"} for i in range(1, 60)]}, limit=25)), 25)

    def test_app_full(self):
        data = {"name": "Game", "type": "game", "is_free": False, "short_description": "S &amp; T",
                "header_image": "https://x/h.jpg", "developers": ["D"], "publishers": ["P"],
                "genres": [{"id": "1", "description": "Action"}, {"x": 1}],
                "release_date": {"coming_soon": False, "date": "1 Jan, 2020"},
                "price_overview": {"currency": "GBP", "initial": 2999, "final": 1499, "discount_percent": 50,
                                   "initial_formatted": "£29.99", "final_formatted": "£14.99"},
                "pc_requirements": {"minimum": "<b>Min</b>", "recommended": "<b>Rec</b>"}}
        app = parse_steam_app(1, {"1": {"success": True, "data": data}})
        self.assertEqual(app.price.discount_percent, 50)
        self.assertEqual(app.genres, ["Action"])
        self.assertEqual(app.requirements_rec, "<b>Rec</b>")

    def test_app_missing_and_odd(self):
        self.assertIsNone(parse_steam_app(1, {"1": {"success": False}}))
        self.assertIsNone(parse_steam_app(1, {}))
        app = parse_steam_app(1, {"1": {"success": True, "data": {"name": "X", "pc_requirements": [],
                                                                  "genres": None, "price_overview": "bad"}}})
        self.assertIsNone(app.requirements_min); self.assertIsNone(app.price); self.assertEqual(app.genres, [])
        with self.assertRaises(BadResponse):
            parse_steam_app(1, ["nope"])

    def test_review_summary(self):
        s = parse_review_summary({"success": 1, "query_summary": {"review_score_desc": "Very Positive",
                                  "total_positive": "90", "total_negative": 10, "total_reviews": 100}})
        self.assertEqual(s.percent_positive, 90)
        z = parse_review_summary({"success": 1, "query_summary": {"total_reviews": 0}})
        self.assertIsNone(z.percent_positive)
        for bad in ({"success": 0}, {"success": 1}, [], None):
            with self.assertRaises(BadResponse):
                parse_review_summary(bad)

    def test_reviews(self):
        p = {"success": 1, "reviews": [{"review": "[b]Great[/b] game @everyone", "voted_up": True,
                                         "timestamp_created": 1700000000, "author": {"playtime_forever": 600}},
                                        {"review": "   "}, {"review": "meh", "voted_up": False}, "junk"]}
        r = parse_reviews(p, limit=5)
        self.assertEqual(len(r), 2)
        self.assertEqual(r[0].text, "Great game @everyone")
        self.assertEqual(r[0].playtime_minutes, 600)
        self.assertEqual(parse_reviews({"success": 1}), [])

    def test_news(self):
        p = {"appnews": {"newsitems": [{"title": "Old", "date": 1, "gid": 5}, {"title": "New", "date": 9, "gid": "7"},
                                        {"title": ""}, "x"]}}
        n = parse_news(p)
        self.assertEqual([i.title for i in n], ["New", "Old"])
        self.assertEqual(parse_news({"appnews": {}}), [])
        with self.assertRaises(BadResponse):
            parse_news({"x": 1})


class Proton(unittest.TestCase):
    def test_summary(self):
        s = parse_protondb_summary({"tier": "Gold", "trendingTier": "platinum", "bestReportedTier": "platinum",
                                    "confidence": "strong", "score": 0.7, "total": 3441})
        self.assertEqual((s.tier, s.total), ("gold", 3441))
        e = parse_protondb_summary({})
        self.assertIsNone(e.tier)
        with self.assertRaises(BadResponse):
            parse_protondb_summary([])

    def test_counts(self):
        self.assertEqual(parse_counts({"reports": 5, "timestamp": 9}).timestamp, 9)
        for bad in ({}, {"reports": 5}, {"reports": "x", "timestamp": 1}, {"reports": 1, "timestamp": 0}, []):
            with self.assertRaises(BadResponse):
                parse_counts(bad)

    def test_reports_shapes(self):
        row = {"timestamp": 1700000000, "responses": {"protonVersion": "9.0-4", "verdict": "yes",
               "notes": {"verdict": "Runs great", "extra": "Used GE", "x": "no"}},
               "device": {"inferred": {"steam": {"gpu": "RX 7800", "os": "Arch", "kernel": "6.8"}}}}
        r = parse_protondb_reports({"reports": [row, "junk", {}]})
        self.assertEqual(len(r), 2)
        self.assertEqual(r[0].verdict, "yes")
        self.assertIn("Runs great", r[0].notes)
        self.assertIn("RX 7800", r[0].hardware)
        self.assertIsNone(r[1].timestamp)
        self.assertEqual(len(parse_protondb_reports([row])), 1)
        self.assertEqual(parse_protondb_reports({"reports": []}), [])
        ms = parse_protondb_reports([{"timestamp": 1700000000000}])
        self.assertEqual(ms[0].timestamp, 1700000000)
        for bad in ({"nothing": 1}, "text", None):
            with self.assertRaises(BadResponse):
                parse_protondb_reports(bad)


if __name__ == "__main__":
    unittest.main()
