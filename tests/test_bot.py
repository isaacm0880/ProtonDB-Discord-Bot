"""Control-flow tests for bot.py.

Run against stand-ins unless discord.py is installed, in which case the real
library is used for imports/decorators (interactions are always fakes).
"""
import asyncio, os, unittest
os.environ.setdefault("DISCORD_TOKEN", "test-token-not-real")
import stubs; stubs.install()
import discord
import bot as B
from models import *


class FakeResponse:
    def __init__(self, log):
        self.log = log

    async def defer(self, **kw):
        self.log.append(("defer", kw))

    def is_done(self):
        return True


class FakeFollowup:
    def __init__(self, log):
        self.log = log

    async def send(self, **kw):
        self.log.append(("followup", kw))


class FakeInteraction:
    id = 1
    type = discord.InteractionType.application_command

    def __init__(self):
        self.log = []
        self.response = FakeResponse(self.log)
        self.followup = FakeFollowup(self.log)

    async def delete_original_response(self):
        self.log.append(("delete_original", {}))

    async def edit_original_response(self, **kw):
        self.log.append(("EDIT_ORIGINAL", kw))   # must never happen


class FakeServices:
    def __init__(self, **over):
        self.over = over
        self.names = {}

    def known_name(self, appid):
        return self.names.get(appid)

    async def resolve_game(self, q):
        r = self.over.get("resolve", ResolvedGame(10, "Game"))
        return r(q) if callable(r) else r

    async def search_games(self, q, fast=False):
        r = self.over.get("search", [])
        if isinstance(r, Exception):
            raise r
        return r

    async def steam_app(self, appid):
        r = self.over.get("app", SteamApp(appid=appid, name="Game", requirements_min="CPU: x"))
        if isinstance(r, Exception):
            raise r
        return r

    async def review_summary(self, appid):
        r = self.over.get("summary", ReviewSummary("Very Positive", 9, 1, 10))
        if isinstance(r, Exception):
            raise r
        return r

    async def recent_reviews(self, appid, limit=5):
        r = self.over.get("reviews", [Review(True, "nice")])
        if isinstance(r, Exception):
            raise r
        return r

    async def news(self, appid, count=5):
        r = self.over.get("news", [NewsItem("1", "T", "https://a.b/c", "text", 5)])
        if isinstance(r, Exception):
            raise r
        return r

    async def protondb_summary(self, appid):
        r = self.over.get("psummary", ProtonSummary("gold", total=5))
        if isinstance(r, Exception):
            raise r
        return r

    async def protondb_reports(self, appid, limit=3):
        return self.over.get("preports", ReportsResult(ok=False, reason="x"))


def run(coro):
    return asyncio.run(coro)


def use(**over):
    B.services = FakeServices(**over)


class Registration(unittest.TestCase):
    def test_commands_and_autocomplete(self):
        cmds = B.bot.tree.commands if hasattr(B.bot.tree, "commands") and isinstance(B.bot.tree.commands, dict) else None
        if cmds is None:
            self.skipTest("real discord.py: registration checked by sync log at runtime")
        self.assertEqual(sorted(cmds), ["news", "protondb", "protondbid", "steam"])
        for name in ("protondb", "steam", "news"):
            self.assertIs(cmds[name].autocompletes["game"], B.game_autocomplete)
        for c in cmds.values():
            self.assertLessEqual(len(c.description), 100)

    def test_button_templates_and_ids(self):
        self.assertEqual(B.RequirementsButton.template, r"steam:req:(?P<appid>[0-9]+)")
        view = B.steam_buttons_view(730)
        ids = [i.custom_id for i in view.children]
        self.assertEqual(ids, ["steam:req:730", "steam:rev:730"])
        self.assertIsNone(view.timeout)
        self.assertEqual(len(view.children), 2)  # no extra buttons


class Autocomplete(unittest.TestCase):
    def test_limits_and_labels(self):
        results = [SearchResult(i, "N" * 300) for i in range(1, 60)]
        use(search=results)
        out = run(B.game_autocomplete(FakeInteraction(), "12"))
        self.assertLessEqual(len(out), 25)
        for c in out:
            self.assertLessEqual(len(c.name), 100); self.assertLessEqual(len(c.value), 100)
        self.assertEqual(out[0].value, "12")  # numeric App ID lookup preserved
        self.assertTrue(any("(App 5)" in c.name for c in out))

    def test_errors_and_short_input(self):
        use(search=UpstreamUnavailable("Steam", "x"))
        self.assertEqual(run(B.game_autocomplete(FakeInteraction(), "half")), [])
        use(search=RuntimeError("boom"))
        self.assertEqual(run(B.game_autocomplete(FakeInteraction(), "half")), [])
        self.assertEqual(run(B.game_autocomplete(FakeInteraction(), "")), [])
        self.assertEqual(run(B.game_autocomplete(FakeInteraction(), "a")), [])


def kinds(i):
    return [k for k, _ in i.log]


class Commands(unittest.TestCase):
    def call(self, name, **kw):
        i = FakeInteraction()
        run(B.bot.tree.commands[name].callback(i, **kw) if isinstance(B.bot.tree.commands, dict) else None)
        return i

    def test_steam_success_has_two_buttons_and_defers_first(self):
        use()
        i = self.call("steam", game="10")
        self.assertEqual(kinds(i), ["defer", "followup"])
        kw = i.log[1][1]
        self.assertEqual(len(kw["view"].children), 2)
        self.assertEqual(kw["embed"].colour.value, 0xB45D1F)
        self.assertFalse(kw["ephemeral"])

    def test_steam_failures_are_private_error_embeds(self):
        for over in ({"app": None}, {"app": UpstreamUnavailable("Steam", "t")}, {"resolve": None}):
            use(**over)
            i = self.call("steam", game="x")
            self.assertEqual(kinds(i), ["defer", "delete_original", "followup"], over)
            kw = i.log[-1][1]
            self.assertTrue(kw["ephemeral"]); self.assertEqual(kw["embed"].colour.value, 0xB45D1F)

    def test_steam_review_failure_still_shows_embed(self):
        use(summary=RateLimited("Steam", 30))
        i = self.call("steam", game="10")
        self.assertEqual(kinds(i), ["defer", "followup"])
        self.assertIn("unavailable", i.log[1][1]["embed"].fields[3].value)

    def test_unexpected_exception_is_handled(self):
        use(app=RuntimeError("bug"))
        i = self.call("steam", game="10")
        self.assertEqual(kinds(i)[-1], "followup"); self.assertTrue(i.log[-1][1]["ephemeral"])

    def test_protondb_and_id(self):
        use()
        for name, kw in (("protondb", {"game": "10"}), ("protondbid", {"appid": 10})):
            i = self.call(name, **kw)
            self.assertEqual(kinds(i), ["defer", "followup"])
            self.assertIn("Gold", i.log[1][1]["embed"].fields[0].value)
        use(app=None, psummary=None)
        self.assertEqual(kinds(self.call("protondb", game="10")), ["defer", "delete_original", "followup"])
        use(psummary=RateLimited("ProtonDB", 30))
        i = self.call("protondb", game="10")
        self.assertIn("rate limiting", i.log[1][1]["embed"].fields[0].value)

    def test_news(self):
        use()
        i = self.call("news", game="10")
        self.assertEqual(kinds(i), ["defer", "followup"])
        use(news=[])
        self.assertIn("No recent", self.call("news", game="10").log[1][1]["embed"].description)
        use(news=UpstreamUnavailable("Steam", "x"))
        self.assertEqual(kinds(self.call("news", game="10"))[-1], "followup")


class Buttons(unittest.TestCase):
    def click(self, button):
        i = FakeInteraction()
        run(button.callback(i))
        return i

    def test_requirements_sends_new_private_embed_and_never_edits(self):
        use()
        i = self.click(B.RequirementsButton(10))
        self.assertEqual(kinds(i), ["defer", "followup"])
        self.assertTrue(i.log[0][1]["ephemeral"])
        self.assertTrue(i.log[1][1]["ephemeral"])
        self.assertEqual(i.log[1][1]["embed"].fields[0].name, "Minimum")
        self.assertNotIn("EDIT_ORIGINAL", kinds(i))

    def test_requirements_missing(self):
        use(app=SteamApp(appid=1, name="X"))
        self.assertIn("doesn't list", self.click(B.RequirementsButton(1)).log[1][1]["embed"].description)
        use(app=None)
        i = self.click(B.RequirementsButton(1))
        self.assertTrue(i.log[-1][1]["ephemeral"]); self.assertNotIn("delete_original", kinds(i))

    def test_reviews(self):
        use()
        i = self.click(B.ReviewsButton(10))
        self.assertEqual(kinds(i), ["defer", "followup"])
        e = i.log[1][1]["embed"]
        self.assertTrue(i.log[1][1]["ephemeral"])
        self.assertIn("steamcommunity.com/app/10/reviews", "".join(f.value for f in e.fields))
        for over in ({"reviews": []}, {"reviews": UpstreamUnavailable("Steam")}, {"summary": UpstreamUnavailable("Steam")}):
            use(**over)
            i = self.click(B.ReviewsButton(10))
            self.assertEqual(kinds(i), ["defer", "followup"], over)

    def test_both_buttons_independent(self):
        use(reviews=UpstreamUnavailable("Steam"), summary=UpstreamUnavailable("Steam"))
        self.assertEqual(kinds(self.click(B.RequirementsButton(10))), ["defer", "followup"])


if __name__ == "__main__":
    unittest.main()
