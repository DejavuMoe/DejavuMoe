"""Network-free regression tests for public data, generated markup, and updates."""

import json
from pathlib import Path
import re
import sys
import tempfile
import unittest
from unittest.mock import patch
import urllib.error
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import update_profile as profile
import town
from iso import Iso
from profile_art import picture, project_card, town_plan, wrap_copy

CONFIG = {
    "owner": "DejavuMoe", "blog_url": "https://blog.dejavu.moe",
    "feed_url": "https://blog.dejavu.moe/index.xml", "project_count": 6,
    "post_count": 8, "exclude": ["DejavuMoe"], "descriptions": {},
}
README = """Handwritten introduction and PGP key stay intact.
<!-- PROFILE-HERO:START -->
old hero
<!-- PROFILE-HERO:END -->
<!-- PROJECTS:START -->
old projects
<!-- PROJECTS:END -->
<!-- BLOG-POST-LIST:START -->
old posts
<!-- BLOG-POST-LIST:END -->
<!-- FOOTER:START -->
<!-- FOOTER:END -->
Handwritten footer.
"""


def repo(name="example", **kwargs):
    item = {
        "name": name, "url": f"https://github.com/DejavuMoe/{name}", "description": "A small tool.",
        "homepage": "", "language": "Python", "archived": False, "stars": 3, "commits": 30, "releases": 2,
        "latest_release": "v1.0.0",
    }
    item.update(kwargs)
    return item


def snapshot():
    return {
        "version": 1,
        "github": {"updated": "2026-10-12", "repositories": [repo()]},
        "blog": {"updated": "2026-10-12", "posts": [{"title": "A post", "url": "https://blog.dejavu.moe/posts/a/", "date": "2026-10-08", "summary": "Short."}]},
    }


def view(**kwargs):
    item = profile.project_view(repo(**kwargs), CONFIG)
    return {**item, "height": 2.0}


def connection(nodes, cursor=None):
    return {"nodes": nodes, "pageInfo": {"hasNextPage": bool(cursor), "endCursor": cursor}}


def api_repo(name="example", **kwargs):
    item = {
        "name": name, "url": f"https://github.com/DejavuMoe/{name}", "description": "",
        "isPrivate": False, "isFork": False, "isArchived": False,
        "owner": {"login": "DejavuMoe"}, "stargazerCount": 3, "primaryLanguage": {"name": "Python"},
        "defaultBranchRef": {"target": {"history": {"totalCount": 30}}},
        "releases": connection([]),
    }
    item.update(kwargs)
    return item


def release(tag="v1", draft=False, date="2026-10-01T00:00:00Z", prerelease=False):
    return {"tagName": tag, "isDraft": draft, "publishedAt": date, "isPrerelease": prerelease}


def rss(items):
    return f'<rss version="2.0"><channel>{items}</channel></rss>'.encode()


def item(title="Hello", link="https://blog.dejavu.moe/posts/hello/", date="Thu, 08 Oct 2026 22:25:35 +0800"):
    return f'<item><title>{title}</title><link>{link}</link><pubDate>{date}</pubDate></item>'


class FeedTests(unittest.TestCase):
    def test_rss_dates_titles_and_links(self):
        posts = profile.parse_feed(rss(item("寒露与幻梦 &amp; life")), CONFIG["blog_url"])
        self.assertEqual(posts[0]["date"], "2026-10-08")
        self.assertEqual(posts[0]["title"], "寒露与幻梦 & life")

    def test_atom(self):
        xml = b'''<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Atom</title>
        <link rel="self" href="https://wrong.example"/><link href="https://blog.dejavu.moe/posts/a/"/>
        <updated>2026-10-08T01:00:00Z</updated></entry></feed>'''
        self.assertEqual(profile.parse_feed(xml, CONFIG["blog_url"])[0]["date"], "2026-10-08")

    def test_deduplicates_and_filters_non_posts(self):
        xml = rss(item() + item() + item(link="https://blog.dejavu.moe/about/") + item(link="https://evil.example/posts/a/"))
        self.assertEqual(len(profile.parse_feed(xml, CONFIG["blog_url"])), 1)

    def test_newest_first_and_limit(self):
        xml = rss(item("old", date="Wed, 07 Oct 2026 22:25:35 +0800") + item("new", link="https://blog.dejavu.moe/posts/new/"))
        self.assertEqual(profile.parse_feed(xml, CONFIG["blog_url"], 1)[0]["title"], "new")

    def test_rejects_empty_feed_and_entities(self):
        for xml in (rss(""), b'<!DOCTYPE rss [<!ENTITY x "oops">]><rss/>'):
            with self.subTest(xml=xml), self.assertRaises(ValueError):
                profile.parse_feed(xml, CONFIG["blog_url"])

    def test_utf16_cannot_bypass_entity_guard(self):
        xml = '<!DOCTYPE rss [<!ENTITY x "injected">]><rss><channel><item><title>&x;</title><link>https://blog.dejavu.moe/posts/a/</link></item></channel></rss>'
        for encoding in ("utf-16", "utf-16-le", "utf-16-be"):
            with self.subTest(encoding=encoding), self.assertRaises(ValueError):
                profile.parse_feed(xml.encode(encoding), CONFIG["blog_url"])

    def test_rejects_unsafe_urls(self):
        for url in ("javascript:alert(1)", "http://blog.dejavu.moe/posts/a/", "https://blog.dejavu.moe.evil/posts/a/", "https://u:p@blog.dejavu.moe/posts/a/"):
            with self.subTest(url=url):
                self.assertIsNone(profile.safe_post_url(url, CONFIG["blog_url"]))

    def test_encodes_link_delimiters(self):
        url = profile.safe_post_url("https://blog.dejavu.moe/posts/a(b)/#x", CONFIG["blog_url"])
        self.assertEqual(url, "https://blog.dejavu.moe/posts/a%28b%29/")

    def test_invalid_date_is_not_invented(self):
        self.assertEqual(profile.parse_date("not a date"), "")

    def test_summary_is_plain_text(self):
        xml = rss('<item><title>T</title><link>https://blog.dejavu.moe/posts/t/</link>'
                  '<description>&lt;p&gt;Hello &lt;b&gt;world&lt;/b&gt;&lt;/p&gt; &amp;amp; more</description></item>')
        self.assertEqual(profile.parse_feed(xml, CONFIG["blog_url"])[0]["summary"], "Hello world & more")

    def test_summary_is_capped(self):
        self.assertEqual(len(profile.plain_summary("字" * 500)), 160)
        self.assertTrue(profile.plain_summary("字" * 500).endswith("…"))


class GitHubTests(unittest.TestCase):
    def test_query_explicitly_limits_to_public_owned_nonforks(self):
        for constraint in ("privacy: PUBLIC", "isFork: false", "ownerAffiliations: [OWNER]"):
            self.assertIn(constraint, profile.QUERY)
        # Explicit CREATED_AT ordering returned old Smoji releases that the public
        # REST/default GraphQL connection did not expose. Keep the default connection.
        self.assertIn("releases(first: 100)", profile.QUERY)
        self.assertIn("releases(first: 100, after: $cursor)", profile.RELEASE_QUERY)

    def test_repository_pagination_and_visibility_filter(self):
        first = [api_repo("first"), api_repo("secret", isPrivate=True), api_repo("fork", isFork=True), api_repo("foreign", owner={"login": "other"})]
        responses = [{"user": {"repositories": connection(first, "next")}}, {"user": {"repositories": connection([api_repo("second")])}}]
        with patch.object(profile, "graphql", side_effect=responses) as fetch:
            result = profile.collect_repositories("DejavuMoe", "test-token")
        self.assertEqual([r["name"] for r in result], ["first", "second"])
        self.assertEqual(fetch.call_args_list[1].args[1]["cursor"], "next")

    def test_release_pagination_and_published_only(self):
        node = api_repo(releases=connection([release("v1"), release("draft", draft=True), release("unpublished", date=None)], "next"))
        responses = [
            {"user": {"repositories": connection([node])}},
            {"repository": {"isPrivate": False, "releases": connection([release("v2-beta", date="2026-10-10T00:00:00Z", prerelease=True)])}},
        ]
        with patch.object(profile, "graphql", side_effect=responses):
            result = profile.collect_repositories("DejavuMoe", "test-token")[0]
        self.assertEqual(result["releases"], 2)
        self.assertEqual(result["latest_release"], "v2-beta")

    def test_empty_repository_is_counted_as_zero_commits(self):
        data = {"user": {"repositories": connection([api_repo(defaultBranchRef=None, primaryLanguage=None)])}}
        with patch.object(profile, "graphql", return_value=data):
            result = profile.collect_repositories("DejavuMoe", "test-token")[0]
        self.assertEqual(result["commits"], 0)
        self.assertEqual(result["language"], "")

    def test_repeated_repository_cursor_fails(self):
        response = {"user": {"repositories": connection([api_repo()], "repeat")}}
        with patch.object(profile, "graphql", return_value=response), self.assertRaises(ValueError):
            profile.collect_repositories("DejavuMoe", "test-token")

    def test_repeated_release_cursor_fails(self):
        releases = connection([], "repeat")
        responses = [
            {"user": {"repositories": connection([api_repo(releases=releases)])}},
            {"repository": {"isPrivate": False, "releases": releases}},
        ]
        with patch.object(profile, "graphql", side_effect=responses), self.assertRaises(ValueError):
            profile.collect_repositories("DejavuMoe", "test-token")

    def test_graphql_partial_errors_fail_without_leaking_response(self):
        with patch.object(profile, "request", return_value=b'{"errors":[{"message":"secret detail"}],"data":{}}'):
            with self.assertRaises(RuntimeError) as raised:
                profile.graphql("query", {}, "test-token")
        self.assertNotIn("secret detail", str(raised.exception))

    def test_github_token_cannot_be_sent_to_feed(self):
        with self.assertRaises(ValueError):
            profile.request(CONFIG["feed_url"], token="test-token")

    def test_homepage_is_https_and_credential_free(self):
        self.assertEqual(profile.safe_homepage("https://Smoji.zsh.moe/"), "https://smoji.zsh.moe")
        self.assertEqual(profile.safe_homepage("https://picforge.de/app?x=1#y"), "https://picforge.de/app")
        for url in (None, "", "http://a.example", "javascript:alert(1)", "https://u:p@a.example",
                    "https://github.com/DejavuMoe/sani", "https://a.example:8443", 'https://a"b.example'):
            with self.subTest(url=url):
                self.assertEqual(profile.safe_homepage(url), "")

    def test_homepage_is_collected(self):
        data = {"user": {"repositories": connection([api_repo(homepageUrl="https://demo.example/")])}}
        with patch.object(profile, "graphql", return_value=data):
            self.assertEqual(profile.collect_repositories("DejavuMoe", "test-token")[0]["homepage"], "https://demo.example")

    def test_authenticated_redirect_is_rejected(self):
        req = profile.urllib.request.Request(profile.API, headers={"Authorization": "Bearer test-token"})
        with self.assertRaises(RuntimeError):
            profile.GuardedRedirects().redirect_request(req, None, 302, "redirect", {}, "https://evil.example/")

    def test_insecure_feed_redirect_is_rejected(self):
        req = profile.urllib.request.Request(CONFIG["feed_url"])
        with self.assertRaises(RuntimeError):
            profile.GuardedRedirects().redirect_request(req, None, 302, "redirect", {}, "http://blog.dejavu.moe/index.xml")

    def test_transient_failure_is_retried(self):
        error = urllib.error.HTTPError(profile.API, 503, "unavailable", {}, None)
        with patch.object(profile.HTTP, "open", side_effect=error) as fetch, patch.object(profile.time, "sleep") as sleep:
            with self.assertRaises(RuntimeError):
                profile.request(profile.API)
        self.assertEqual(fetch.call_count, 3)
        self.assertEqual(sleep.call_count, 2)

    def test_auth_failure_is_not_retried(self):
        error = urllib.error.HTTPError(profile.API, 401, "unauthorized", {}, None)
        with patch.object(profile.HTTP, "open", side_effect=error) as fetch:
            with self.assertRaises(RuntimeError):
                profile.request(profile.API)
        self.assertEqual(fetch.call_count, 1)


class RankingTests(unittest.TestCase):
    def test_excludes_archives_profile_and_empty_repositories(self):
        repos = [repo(), repo("old", archived=True), repo("dejavumoe"), repo("empty", commits=0)]
        self.assertEqual([r["name"] for r in profile.rank_repositories(repos, CONFIG)], ["example"])

    def test_each_metric_can_increase_score(self):
        base = repo()
        for field in ("stars", "commits", "releases"):
            extra = {**base, field: base[field]+1}
            self.assertGreater(profile.score(extra), profile.score(base))

    def test_commits_and_releases_can_outweigh_stars(self):
        active = repo("active", stars=0, commits=127, releases=2)
        resource = repo("resource", stars=18, commits=1, releases=0)
        self.assertEqual(profile.rank_repositories([resource, active], CONFIG)[0]["name"], "active")

    def test_ties_are_stable(self):
        self.assertEqual([r["name"] for r in profile.rank_repositories([repo("z"), repo("a")], CONFIG)], ["a", "z"])

    def test_featured_first_then_filled_by_score(self):
        ranked = profile.rank_repositories([repo("big", commits=500), repo("mid", commits=50), repo("tiny", commits=2)], CONFIG)
        config = {**CONFIG, "project_count": 2, "featured": ["tiny", "gone"]}
        self.assertEqual([r["name"] for r in profile.select_featured(ranked, config)], ["tiny", "big"])

    def test_archived_featured_project_is_skipped(self):
        ranked = profile.rank_repositories([repo("a"), repo("old", archived=True)], CONFIG)
        self.assertEqual([r["name"] for r in profile.select_featured(ranked, {**CONFIG, "featured": ["old"]})], ["a"])

    def test_building_height_follows_commits(self):
        plan = town_plan({"projects": [view(name="a", commits=10), view(name="b", commits=1000)]})
        heights = {p["name"]: p["height"] for p in plan}
        self.assertLess(heights["a"], heights["b"])


class TownTests(unittest.TestCase):
    def test_tram_switches_layers_between_far_left_and_far_right(self):
        iso = Iso(500, 300, 26, 28)
        route, length, back = town.tram_route(iso)
        self.assertTrue(route.startswith("M") and route.endswith("Z"))
        self.assertGreater(length, 0)
        self.assertGreater(back, .3)
        self.assertLess(back, .7)

    def test_labels_never_overlap(self):
        pending = [(100, 100, "edgeTTS", "#000"), (110, 102, "Ecoku", "#000"), (95, 98, "romi", "#000"), (300, 100, "far", "#000")]
        placed = town.place_labels(pending)
        for i, (x, _, y, name, _) in enumerate(placed):
            for x2, _, y2, name2, _ in placed[i + 1:]:
                overlap_x = abs(x - x2) < (len(name) + len(name2)) * 3.2 + 22
                self.assertFalse(overlap_x and abs(y - y2) < 20, (name, name2))

    def test_every_building_kind_renders(self):
        for kind in town.BUILDERS:
            with self.subTest(kind=kind):
                svg = project_card({**view(), "kind": kind}, 1, 1)
                ET.fromstring(svg)


class RenderingTests(unittest.TestCase):
    def test_wrap_copy_accounts_for_cjk_width(self):
        lines = wrap_copy("中文" * 40, width=44)
        self.assertEqual(len(lines), 2)
        self.assertLessEqual(len(lines[0]), 22)
        self.assertTrue(lines[-1].endswith("…"))

    def test_wrap_copy_preserves_short_description(self):
        self.assertEqual(wrap_copy("A small useful tool.", width=44), ["A small useful tool."])

    def test_preserves_all_handwritten_content(self):
        rendered = profile.render(snapshot(), CONFIG, README)["README.md"]
        self.assertTrue(rendered.startswith("Handwritten introduction and PGP key stay intact."))
        self.assertTrue(rendered.endswith("Handwritten footer.\n"))
        self.assertIn("full project index", rendered)

    def test_live_demo_links_are_html_inside_html_blocks(self):
        data = snapshot()
        data["github"]["repositories"][0]["homepage"] = "https://demo.example"
        rendered = profile.render(data, CONFIG, README)["README.md"]
        self.assertIn('<a href="https://demo.example">example</a>', rendered)

    def test_post_summary_is_escaped(self):
        data = snapshot()
        data["blog"]["posts"][0]["summary"] = "[x](javascript:bad) a < b"
        rendered = profile.render(data, CONFIG, README)["README.md"]
        self.assertIn(r"\[x\]", rendered)
        self.assertIn("a &lt; b", rendered)

    def test_cached_summary_with_markup_is_rejected(self):
        data = snapshot()
        data["blog"]["posts"][0]["summary"] = "<b>bold</b>"
        with self.assertRaises(ValueError):
            profile.render(data, CONFIG, README)

    def test_project_count_is_bounded_by_island_plots(self):
        with self.assertRaises(ValueError):
            profile.render(snapshot(), {**CONFIG, "project_count": len(town.PLOTS) + 1}, README)

    def test_unknown_building_kind_is_rejected(self):
        with self.assertRaises(ValueError):
            profile.render(snapshot(), {**CONFIG, "buildings": {"example": "castle"}}, README)

    def test_invalid_cached_homepage_is_rejected(self):
        data = snapshot()
        data["github"]["repositories"][0]["homepage"] = "http://insecure.example"
        with self.assertRaises(ValueError):
            profile.render(data, CONFIG, README)

    def test_repeated_render_is_identical(self):
        first = profile.render(snapshot(), CONFIG, README)
        self.assertEqual(first, profile.render(snapshot(), CONFIG, first["README.md"]))

    def test_invalid_markers_fail(self):
        for source in ("missing", "<!-- X:END --><!-- X:START -->", "<!-- X:START --><!-- X:START --><!-- X:END -->"):
            with self.subTest(source=source), self.assertRaises(ValueError):
                profile.replace_region(source, "X", "new")

    def test_every_generated_svg_is_well_formed_and_script_free(self):
        files = profile.render(snapshot(), CONFIG, README)
        images = {name: value for name, value in files.items() if name.endswith(".svg")}
        self.assertEqual(len(images), 16)  # hero, one card, writing and footer x light/dark x wide/compact
        for name, content in images.items():
            with self.subTest(name=name):
                root = ET.fromstring(content)
                self.assertEqual(root.tag, "{http://www.w3.org/2000/svg}svg")
                self.assertNotIn("<script", content)
                self.assertNotIn("foreignObject", content)
                self.assertNotIn("https://", content)
                self.assertNotIn("href=", content)
                self.assertNotIn("@import", content)
                self.assertEqual(re.findall(r"url\((?!#)", content), [])
                self.assertLess(len(content.encode()), 400_000)

    def test_svg_and_alt_escape_external_text(self):
        hostile = {**view(), "name": "x<y", "description": 'bad <script>alert("x")</script> & text'}
        svg = project_card(hostile, 1, 1)
        ET.fromstring(svg)
        self.assertNotIn("<script>", svg)
        markup = picture("hero", '" onerror="alert(1) <script>')
        self.assertNotIn('alt="" onerror=', markup)
        self.assertIn("&lt;script&gt;", markup)

    def test_markdown_title_is_escaped(self):
        value = profile.markdown_text('[click](javascript:bad) <script> | x')
        self.assertIn(r"\[click\]", value)
        self.assertIn("&lt;script&gt;", value)
        self.assertIn(r"\|", value)

    def test_picture_separates_github_theme_from_responsive_media(self):
        markup = picture("hero", "Hero")
        self.assertLess(markup.index("hero-dark-mobile.svg"), markup.index("hero-dark.svg"))
        self.assertIn('width="100%"', markup)
        self.assertIn("#gh-light-mode-only", markup)
        self.assertIn("#gh-dark-mode-only", markup)
        self.assertNotIn("prefers-color-scheme", markup)

    def test_invalid_metrics_and_urls_rejected(self):
        for change in ({"stars": -1}, {"stars": True}, {"url": "javascript:bad"}):
            data = snapshot()
            data["github"]["repositories"][0].update(change)
            with self.subTest(change=change), self.assertRaises(ValueError):
                profile.render(data, CONFIG, README)

    def test_no_eligible_project_does_not_clear_profile(self):
        data = snapshot()
        data["github"]["repositories"][0]["archived"] = True
        with self.assertRaises(ValueError):
            profile.render(data, CONFIG, README)

    def test_generated_assets_match_picture_references(self):
        files = profile.render(snapshot(), CONFIG, README)
        for name in files:
            if name.endswith(".svg"):
                self.assertIn(name, files["README.md"])

    def test_check_detects_extra_generated_file(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            files = profile.render(snapshot(), CONFIG, README)
            profile.write_outputs(files, root)
            profile.check_outputs(files, root)
            (root / "assets/generated/orphan.svg").write_text("<svg/>", encoding="utf-8")
            with self.assertRaises(ValueError):
                profile.check_outputs(files, root)

    def test_check_detects_changed_output(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            files = profile.render(snapshot(), CONFIG, README)
            profile.write_outputs(files, root)
            (root / "assets/generated/hero-light.svg").write_text("changed", encoding="utf-8")
            with self.assertRaises(ValueError):
                profile.check_outputs(files, root)

    def test_unchanged_outputs_are_not_written(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            files = {"README.md": "a\n", "data/profile.json": "{}\n"}
            self.assertEqual(len(profile.write_outputs(files, root)), 2)
            self.assertEqual(profile.write_outputs(files, root), [])


class UpdateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "data").mkdir()
        (self.root / "README.md").write_text(README, encoding="utf-8")
        (self.root / "profile.config.json").write_text(json.dumps(CONFIG), encoding="utf-8")
        (self.root / "data/profile.json").write_text(json.dumps(snapshot()), encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def test_feed_failure_writes_nothing(self):
        before = {p.name: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        with patch.object(profile, "ROOT", self.root), patch.object(profile, "get_token", return_value="test-token"), patch.object(profile, "collect_repositories", return_value=[repo("new")]), patch.object(profile, "request", side_effect=RuntimeError("offline")), patch.object(profile, "write_outputs") as write:
            with self.assertRaises(RuntimeError):
                profile.main([])
        write.assert_not_called()
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.root.rglob("*") if p.is_file()})

    def test_blog_only_does_not_fetch_github_or_require_token(self):
        with patch.object(profile, "ROOT", self.root), patch.object(profile, "get_token") as token, patch.object(profile, "collect_repositories") as github, patch.object(profile, "request", return_value=rss(item())), patch.object(profile, "write_outputs", return_value=[]) as write:
            profile.main(["--blog-only"])
        token.assert_not_called()
        github.assert_not_called()
        saved = json.loads(write.call_args.args[0]["data/profile.json"])
        self.assertEqual(saved["github"], snapshot()["github"])

    def test_offline_never_uses_network(self):
        with patch.object(profile, "ROOT", self.root), patch.object(profile, "request") as fetch, patch.object(profile, "get_token") as token, patch.object(profile, "write_outputs", return_value=[]):
            profile.main(["--offline"])
        fetch.assert_not_called()
        token.assert_not_called()


if __name__ == "__main__":
    unittest.main()
