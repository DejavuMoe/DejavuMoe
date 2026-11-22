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
from profile_art import pin_card, pin_grid, text_width, wrap

CONFIG = {
    "owner": "DejavuMoe", "blog_url": "https://blog.dejavu.moe",
    "feed_url": "https://blog.dejavu.moe/index.xml", "post_count": 8,
    "pins": ["example", {"repo": "other/tool", "title": "Tool", "description": "Custom text.", "badge": "Friend"}],
}
README = """Handwritten introduction and PGP key stay intact.
<!-- PINS:START -->
old pins
<!-- PINS:END -->
<!-- BLOG-POST-LIST:START -->
old posts
<!-- BLOG-POST-LIST:END -->
Handwritten footer.
"""


def repo(name="example", owner="DejavuMoe", **kwargs):
    item = {
        "pinned_as": f"{owner}/{name}", "owner": owner, "name": name, "url": f"https://github.com/{owner}/{name}",
        "description": "A small tool.", "homepage": "", "language": "Python", "language_color": "#3572a5",
        "stars": 3, "forks": 1, "archived": False, "template": False, "parent": None,
    }
    item.update(kwargs)
    return item


def snapshot():
    return {
        "version": 2,
        "github": {"updated": "2026-10-12", "repositories": [repo(), repo("tool", "other")]},
        "blog": {"updated": "2026-10-12", "posts": [{"title": "A post", "url": "https://blog.dejavu.moe/posts/a/", "date": "2026-10-08", "summary": "Short."}]},
    }


def api_repo(name="example", owner="DejavuMoe", **kwargs):
    item = {
        "name": name, "url": f"https://github.com/{owner}/{name}", "description": "  A   tool. ",
        "homepageUrl": None, "isPrivate": False, "isArchived": False, "isFork": False, "isTemplate": False,
        "owner": {"login": owner}, "stargazerCount": 3, "forkCount": 1,
        "primaryLanguage": {"name": "Go", "color": "#00ADD8"}, "parent": None,
    }
    item.update(kwargs)
    return item


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




class HttpTests(unittest.TestCase):
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


class PinConfigTests(unittest.TestCase):
    def test_strings_owner_prefix_and_overrides(self):
        specs = profile.pin_specs(CONFIG)
        self.assertEqual([(s["owner"], s["name"]) for s in specs], [("DejavuMoe", "example"), ("other", "tool")])
        self.assertEqual(specs[1]["title"], "Tool")

    def test_invalid_duplicate_and_unknown_pins_fail(self):
        for pins in (["../x"], ["a/b/c"], ["x", "X"], [{"repo": "x", "colour": "red"}], [],
                     [{"repo": "x", "link": "javascript:alert(1)"}], [{"repo": "x", "link": "http://a.example"}]):
            with self.subTest(pins=pins), self.assertRaises(ValueError):
                profile.pin_specs({**CONFIG, "pins": pins})

    def test_safe_custom_link(self):
        self.assertEqual(profile.safe_link("https://demo.example/app?x=1#frag"), "https://demo.example/app?x=1")
        self.assertEqual(profile.safe_link("https://u:p@demo.example"), "")


class CollectTests(unittest.TestCase):
    def test_one_request_with_variables_and_clean_fields(self):
        data = {"r0": api_repo(), "r1": api_repo("tool", "other", isFork=True, parent={"nameWithOwner": "up/tool"}, primaryLanguage=None)}
        with patch.object(profile, "graphql", return_value=data) as fetch:
            repos = profile.collect_pins(profile.pin_specs(CONFIG), "test-token")
        fetch.assert_called_once()
        query, variables = fetch.call_args.args[:2]
        self.assertNotIn("DejavuMoe", query)  # names travel as variables, never spliced into the query
        self.assertEqual(variables, {"o0": "DejavuMoe", "n0": "example", "o1": "other", "n1": "tool"})
        self.assertEqual(repos[0]["description"], "A tool.")
        self.assertEqual(repos[0]["language_color"], "#00add8")
        self.assertEqual(repos[1]["parent"], "up/tool")
        self.assertEqual(repos[1]["language"], "")

    def test_private_repository_is_refused(self):
        with patch.object(profile, "graphql", return_value={"r0": api_repo(isPrivate=True), "r1": api_repo("tool", "other")}):
            with self.assertRaises(ValueError):
                profile.collect_pins(profile.pin_specs(CONFIG), "test-token")

    def test_missing_repository_is_named(self):
        body = b'{"data":{"r0":null,"r1":{}},"errors":[{"type":"NOT_FOUND","path":["r0"],"message":"x"}]}'
        with patch.object(profile, "request", return_value=body):
            with self.assertRaises(ValueError) as raised:
                profile.collect_pins(profile.pin_specs(CONFIG), "test-token")
        self.assertIn("DejavuMoe/example", str(raised.exception))

    def test_unsafe_language_colour_is_dropped(self):
        data = {"r0": api_repo(primaryLanguage={"name": "Go", "color": "red;x"}), "r1": api_repo("tool", "other")}
        with patch.object(profile, "graphql", return_value=data):
            self.assertEqual(profile.collect_pins(profile.pin_specs(CONFIG), "test-token")[0]["language_color"], "")


class RenderingTests(unittest.TestCase):
    def test_wrap_accounts_for_cjk_width(self):
        lines = wrap("中文" * 40, 10, 200, 2)
        self.assertEqual(len(lines), 2)
        self.assertLessEqual(text_width(lines[0], 10), 200)
        self.assertTrue(lines[-1].endswith("…"))

    def test_wrap_preserves_short_description(self):
        self.assertEqual(wrap("A small useful tool.", 13, 400, 3), ["A small useful tool."])

    def test_preserves_handwritten_content_and_orders_pins(self):
        rendered = profile.render(snapshot(), CONFIG, README)["README.md"]
        self.assertTrue(rendered.startswith("Handwritten introduction and PGP key stay intact."))
        self.assertTrue(rendered.endswith("Handwritten footer.\n"))
        self.assertLess(rendered.index("pin-example-light.svg"), rendered.index("pin-other--tool-light.svg"))

    def test_overrides_and_defaults(self):
        views = profile.pins(snapshot(), CONFIG)
        self.assertEqual((views[0]["title"], views[0]["badge"], views[0]["link"]), ("example", "Public", "https://github.com/DejavuMoe/example"))
        self.assertEqual((views[1]["title"], views[1]["description"], views[1]["badge"]), ("Tool", "Custom text.", "Friend"))

    def test_badges_follow_github_wording(self):
        self.assertEqual(profile.badge(repo(archived=True)), "Public archive")
        self.assertEqual(profile.badge(repo(template=True)), "Public template")

    def test_pin_missing_from_snapshot_fails(self):
        with self.assertRaises(ValueError):
            profile.render(snapshot(), {**CONFIG, "pins": ["example", "new-one"]}, README)

    def test_old_snapshot_version_is_rejected(self):
        data = snapshot()
        data["version"] = 1
        with self.assertRaises(ValueError):
            profile.render(data, CONFIG, README)

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

    def test_invalid_cached_values_are_rejected(self):
        for change in ({"stars": -1}, {"forks": True}, {"url": "javascript:bad"}, {"language_color": "red"},
                       {"homepage": "http://insecure.example"}, {"parent": "../x"}, {"archived": "no"}):
            data = snapshot()
            data["github"]["repositories"][0].update(change)
            with self.subTest(change=change), self.assertRaises(ValueError):
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
        self.assertEqual(len(images), 8)  # two pins x light/dark x wide/compact
        for name, content in images.items():
            with self.subTest(name=name):
                root = ET.fromstring(content)
                self.assertEqual(root.tag, "{http://www.w3.org/2000/svg}svg")
                for banned in ("<script", "foreignObject", "https://", "href=", "@import"):
                    self.assertNotIn(banned, content)
                self.assertEqual(re.findall(r"url\(", content), [])
                self.assertLess(len(content.encode()), 40_000)

    def test_card_and_alt_escape_external_text(self):
        view = profile.pin_view({}, repo(name="x", description='bad <script>alert("x")</script> & text'), "DejavuMoe")
        svg = pin_card(view)
        ET.fromstring(svg)
        self.assertNotIn("<script>", svg)
        markup = pin_grid([{**view, "description": '" onerror="alert(1)'}])
        self.assertNotIn('" onerror=', markup)

    def test_grid_pairs_cards_and_separates_theme_from_width(self):
        markup = profile.render(snapshot(), CONFIG, README)["README.md"]
        self.assertEqual(markup.count("<p>"), 1)
        self.assertIn('width="49%"', markup)
        self.assertIn("#gh-light-mode-only", markup)
        self.assertIn("#gh-dark-mode-only", markup)
        self.assertIn('media="(max-width: 600px)"', markup)
        self.assertNotIn("prefers-color-scheme", markup)

    def test_generated_assets_match_picture_references(self):
        files = profile.render(snapshot(), CONFIG, README)
        for name in files:
            if name.endswith(".svg"):
                self.assertIn(name, files["README.md"])

    def test_check_detects_extra_and_changed_files(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            files = profile.render(snapshot(), CONFIG, README)
            profile.write_outputs(files, root)
            profile.check_outputs(files, root)
            (root / "assets/generated/pin-example-light.svg").write_text("changed", encoding="utf-8")
            with self.assertRaises(ValueError):
                profile.check_outputs(files, root)
            profile.write_outputs(files, root)
            (root / "assets/generated/orphan.svg").write_text("<svg/>", encoding="utf-8")
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
        with patch.object(profile, "ROOT", self.root), patch.object(profile, "get_token", return_value="test-token"), patch.object(profile, "collect_pins", return_value=snapshot()["github"]["repositories"]), patch.object(profile, "request", side_effect=RuntimeError("offline")), patch.object(profile, "write_outputs") as write:
            with self.assertRaises(RuntimeError):
                profile.main([])
        write.assert_not_called()
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.root.rglob("*") if p.is_file()})

    def test_blog_only_does_not_fetch_github_or_require_token(self):
        with patch.object(profile, "ROOT", self.root), patch.object(profile, "get_token") as token, patch.object(profile, "collect_pins") as github, patch.object(profile, "request", return_value=rss(item())), patch.object(profile, "write_outputs", return_value=[]) as write:
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
