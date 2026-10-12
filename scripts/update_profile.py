#!/usr/bin/env python3
"""Update the profile from public GitHub metadata and the blog RSS feed.

Python 3.11+, standard library only. Fetch and validate everything before writing;
an upstream failure leaves the last good profile untouched.
"""

from __future__ import annotations

import argparse
import datetime as dt
import email.utils
import html
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

from profile_art import hero, picture, project_card

ROOT = Path(__file__).resolve().parents[1]
API = "https://api.github.com/graphql"
QUERY = """
query Profile($login: String!, $cursor: String) {
  user(login: $login) {
    repositories(first: 50, after: $cursor, privacy: PUBLIC, isFork: false,
                 ownerAffiliations: [OWNER], orderBy: {field: NAME, direction: ASC}) {
      pageInfo { hasNextPage endCursor }
      nodes {
        name url description isPrivate isFork isArchived owner { login }
        stargazerCount primaryLanguage { name }
        defaultBranchRef { target { ... on Commit { history(first: 1) { totalCount } } } }
        releases(first: 100) {
          pageInfo { hasNextPage endCursor }
          nodes { isDraft isPrerelease publishedAt tagName }
        }
      }
    }
  }
}
"""
RELEASE_QUERY = """
query Releases($login: String!, $name: String!, $cursor: String!) {
  repository(owner: $login, name: $name) {
    isPrivate
    releases(first: 100, after: $cursor) {
      pageInfo { hasNextPage endCursor }
      nodes { isDraft isPrerelease publishedAt tagName }
    }
  }
}
"""


class GuardedRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if req.has_header("Authorization"):
            raise RuntimeError("Refusing to redirect a credential-bearing request")
        if urllib.parse.urlsplit(newurl).scheme != "https":
            raise RuntimeError("Refusing a non-HTTPS feed redirect")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


HTTP = urllib.request.build_opener(GuardedRedirects())


def request(url, *, payload=None, token=None):
    headers = {"User-Agent": "DejavuMoe-profile/1.0", "Accept": "application/json" if payload else "application/rss+xml, application/atom+xml, text/xml"}
    if token:
        # Never forward a GitHub token to the feed or any other host.
        if url != API:
            raise ValueError("Refusing to send credentials outside the GitHub GraphQL endpoint")
        headers["Authorization"] = f"Bearer {token}"
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, data=data, headers=headers)
            with HTTP.open(req, timeout=40) as response:
                content = response.read(8_000_001)
                if len(content) > 8_000_000:
                    raise ValueError("Response exceeds the 8 MB safety limit")
                return content
        except urllib.error.HTTPError as exc:
            status = exc.code
            exc.close()
            if status not in (429, 500, 502, 503, 504) or attempt == 2:
                raise RuntimeError(f"Upstream HTTP {status} from {urllib.parse.urlsplit(url).hostname}") from None
        except (urllib.error.URLError, TimeoutError):
            if attempt == 2:
                raise RuntimeError(f"Upstream unavailable: {urllib.parse.urlsplit(url).hostname}") from None
        time.sleep(2 ** attempt)
    raise RuntimeError("Unreachable retry state")


def graphql(query, variables, token):
    result = json.loads(request(API, payload={"query": query, "variables": variables}, token=token))
    if result.get("errors"):
        # Do not log raw responses, which may contain authentication details.
        raise RuntimeError("GitHub GraphQL returned errors; previous profile retained")
    if not isinstance(result.get("data"), dict):
        raise ValueError("Invalid GraphQL response")
    return result["data"]


def get_token():
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if token:
        return token
    try:
        result = subprocess.run(
            ["gh", "auth", "token", "--hostname", "github.com"],
            capture_output=True, text=True, check=True, timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        raise RuntimeError("Set GH_TOKEN / GITHUB_TOKEN, or sign in with gh auth login") from None
    if not result.stdout.strip():
        raise RuntimeError("GitHub authentication returned an empty token")
    return result.stdout.strip()


def collect_repositories(owner, token):
    repos, cursor, seen = [], None, set()
    while True:
        user = graphql(QUERY, {"login": owner, "cursor": cursor}, token).get("user")
        if not user:
            raise ValueError("Public GitHub user not found")
        connection = user["repositories"]
        for node in connection["nodes"]:
            # Defense in depth: do not cache private, forked, or foreign data.
            if node["isPrivate"] or node["isFork"] or node["owner"]["login"].casefold() != owner.casefold():
                continue
            release_connection = node["releases"]
            releases = list(release_connection["nodes"])
            release_cursors = set()
            while release_connection["pageInfo"]["hasNextPage"]:
                after = release_connection["pageInfo"]["endCursor"]
                if not after or after in release_cursors:
                    raise ValueError("Invalid releases pagination")
                release_cursors.add(after)
                extra = graphql(RELEASE_QUERY, {"login": owner, "name": node["name"], "cursor": after}, token)["repository"]
                if not extra or extra["isPrivate"]:
                    raise ValueError("Repository visibility changed during collection")
                release_connection = extra["releases"]
                releases.extend(release_connection["nodes"])
            published = [r for r in releases if not r["isDraft"] and r["publishedAt"]]
            published.sort(key=lambda r: r["publishedAt"], reverse=True)
            branch = node.get("defaultBranchRef")
            history = (branch or {}).get("target", {}).get("history", {})
            repos.append({
                "name": node["name"], "url": node["url"],
                "description": node["description"] or "",
                "language": (node["primaryLanguage"] or {}).get("name", ""),
                "archived": node["isArchived"], "stars": node["stargazerCount"],
                "commits": history.get("totalCount", 0), "releases": len(published),
                "latest_release": published[0]["tagName"] if published else None,
            })
        page = connection["pageInfo"]
        if not page["hasNextPage"]:
            break
        cursor = page["endCursor"]
        if not cursor or cursor in seen:
            raise ValueError("Invalid repository pagination")
        seen.add(cursor)
    if not repos:
        raise ValueError("GitHub returned no public original repositories")
    return sorted(repos, key=lambda r: r["name"].casefold())


def parse_date(value):
    if not value:
        return ""
    try:
        date = email.utils.parsedate_to_datetime(value)
    except (TypeError, ValueError):
        try:
            date = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return ""
    return date.date().isoformat()


def safe_post_url(value, blog_url):
    url = urllib.parse.urlsplit(value.strip())
    blog = urllib.parse.urlsplit(blog_url)
    if url.scheme != "https" or url.netloc != blog.netloc or not url.path.startswith("/posts/"):
        return None
    if url.username or url.password:
        return None
    # Encode markdown delimiters while retaining a usable URL.
    path = urllib.parse.quote(url.path, safe="/%:@-._~!$&'*+,;=")
    query = urllib.parse.quote(url.query, safe="%=&-._~")
    return urllib.parse.urlunsplit((url.scheme, url.netloc, path, query, ""))


def parse_feed(content, blog_url, limit=8):
    # The configured Hugo feed is UTF-8. Reject other encodings and NULs before
    # scanning declarations, so UTF-16 cannot bypass the entity-expansion guard.
    xml = content.decode("utf-8-sig")
    if "\x00" in xml or "<!DOCTYPE" in xml.upper() or "<!ENTITY" in xml.upper():
        raise ValueError("Feed document type declarations and non-UTF-8 XML are not supported")
    root = ET.fromstring(xml)
    atom = "{http://www.w3.org/2005/Atom}"
    entries = root.findall("./channel/item")
    is_atom = root.tag == f"{atom}feed"
    if is_atom:
        entries = root.findall(f"{atom}entry")
    posts, seen = [], set()
    for entry in entries:
        prefix = atom if is_atom else ""
        title = entry.findtext(f"{prefix}title", "")
        title = " ".join(html.unescape(title).split())
        if is_atom:
            links = entry.findall(f"{atom}link")
            raw_url = next((a.get("href", "") for a in links if a.get("rel", "alternate") == "alternate"), "")
            date = entry.findtext(f"{atom}published") or entry.findtext(f"{atom}updated", "")
        else:
            raw_url = entry.findtext("link", "")
            date = entry.findtext("pubDate", "")
        url = safe_post_url(raw_url, blog_url)
        if not title or not url or url in seen:
            continue
        seen.add(url)
        posts.append({"title": title, "url": url, "date": parse_date(date)})
    posts.sort(key=lambda p: p["date"], reverse=True)
    if not posts:
        raise ValueError("Feed contains no valid blog posts; previous list retained")
    return posts[:limit]


def score(repo):
    # Logarithmic scaling stops one popular project crowding out sustained work.
    return .35 * math.log1p(repo["stars"]) + .45 * math.log1p(repo["commits"]) + .20 * math.log1p(repo["releases"])


def rank_repositories(repos, config):
    excluded = {name.casefold() for name in config["exclude"]}
    eligible = [r for r in repos if not r["archived"] and r["commits"] > 0 and r["name"].casefold() not in excluded]
    return sorted(eligible, key=lambda r: (-score(r), -r["stars"], -r["commits"], -r["releases"], r["name"].casefold()))


def markdown_text(value):
    value = html.escape(" ".join(str(value).split()), quote=False)
    return re.sub(r"([\\`*_{}\[\]()#+.!|>~-])", r"\\\1", value)


def replace_region(source, marker, replacement):
    start, end = f"<!-- {marker}:START -->", f"<!-- {marker}:END -->"
    if source.count(start) != 1 or source.count(end) != 1:
        raise ValueError(f"Expected exactly one marker pair: {marker}")
    a, b = source.index(start) + len(start), source.index(end)
    if a > b:
        raise ValueError(f"Reversed markers: {marker}")
    return source[:a] + "\n" + replacement.strip() + "\n" + source[b:]


def validate_snapshot(snapshot, config):
    if snapshot.get("version") != 1:
        raise ValueError("Unsupported snapshot version")
    repos = snapshot["github"]["repositories"]
    names = set()
    for repo in repos:
        name = repo["name"]
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", name) or name.casefold() in names:
            raise ValueError("Invalid or duplicate repository name")
        names.add(name.casefold())
        if repo["url"] != f'https://github.com/{config["owner"]}/{name}':
            raise ValueError("Unexpected repository URL")
        if not isinstance(repo["archived"], bool):
            raise ValueError("Invalid archive flag")
        for metric in ("stars", "commits", "releases"):
            if type(repo[metric]) is not int or repo[metric] < 0:
                raise ValueError(f"Invalid {metric} count")
    if not repos or not snapshot["blog"]["posts"]:
        raise ValueError("Empty profile snapshot")
    for post in snapshot["blog"]["posts"]:
        if not post["title"] or safe_post_url(post["url"], config["blog_url"]) != post["url"]:
            raise ValueError("Invalid cached blog post")
    for section in ("github", "blog"):
        dt.date.fromisoformat(snapshot[section]["updated"])


def render(snapshot, config, readme):
    validate_snapshot(snapshot, config)
    ranked = rank_repositories(snapshot["github"]["repositories"], config)
    selected = ranked[:config["project_count"]]
    if not selected:
        raise ValueError("No eligible projects; refusing to empty the profile")
    files = {}
    for theme in ("light", "dark"):
        for compact in (False, True):
            suffix = f'{theme}{"-mobile" if compact else ""}'
            files[f"assets/generated/hero-{suffix}.svg"] = hero(theme, compact)
            for i, repo in enumerate(selected, 1):
                description = config["descriptions"].get(repo["name"], repo["description"] or "An open-source project.")
                files[f"assets/generated/project-{i:02d}-{suffix}.svg"] = project_card(repo, i, description, theme, compact)
    readme = replace_region(readme, "PROFILE-HERO", picture("hero", "Dejavu Moe — a curious explorer. Open source / small tools / just for fun.", f'https://github.com/{config["owner"]}'))
    blocks = []
    for i, repo in enumerate(selected, 1):
        description = config["descriptions"].get(repo["name"], repo["description"] or "An open-source project.")
        alt = f'{repo["name"]} — {description} | {repo["stars"]} stars · {repo["commits"]} commits · {repo["releases"]} releases'
        blocks.append(picture(f"project-{i:02d}", alt, repo["url"]))
    totals = {key: sum(r[key] for r in ranked) for key in ("stars", "commits", "releases")}
    stamp = snapshot["github"]["updated"]
    blocks += [
        f'<sub>Snapshot {stamp} UTC · {len(ranked)} indexed repositories · {totals["stars"]:,} stars across this index</sub>',
        '<details>\n<summary>Selection notes &amp; full project index</summary>\n',
        'Only my public, non-fork, non-archived repositories with commit history are eligible; this profile repository is excluded. '
        f'The {len(selected)} entries above balance stars (35%), default-branch commits (45%) and published releases (20%), using logarithmic scaling. '
        'Commits include **all authors**, not just me. Releases include prereleases, exclude drafts, and are not Git tags.\n',
        '| Project | Stars | Commits | Releases |\n| :--- | ---: | ---: | ---: |',
    ]
    for repo in ranked:
        blocks.append(f'| [{markdown_text(repo["name"])}]({repo["url"]}) | {repo["stars"]:,} | {repo["commits"]:,} | {repo["releases"]:,} |')
    blocks.append('\n[How this profile updates](docs/profile.md) · [Public data snapshot](data/profile.json)\n\n</details>')
    readme = replace_region(readme, "PROJECTS", "\n\n".join(blocks[:len(selected)+3]) + "\n" + "\n".join(blocks[len(selected)+3:]))
    posts = [f'- <sub>{p["date"].replace("-", ".")}</sub> &nbsp; [{markdown_text(p["title"])}](<{p["url"]}>)' for p in snapshot["blog"]["posts"]]
    readme = replace_region(readme, "BLOG-POST-LIST", "\n".join(posts))
    files["README.md"] = readme
    files["data/profile.json"] = json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n"
    return files


def write_outputs(files, root=ROOT):
    changed = []
    for relative, content in files.items():
        path = root / relative
        if path.exists() and path.read_text(encoding="utf-8") == content:
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8", newline="\n")
        changed.append(relative)
    return changed


def check_outputs(files, root=ROOT):
    expected = set(files)
    actual = {"README.md", "data/profile.json"} | {
        path.relative_to(root).as_posix() for path in (root / "assets/generated").glob("*.svg")
    }
    if actual != expected:
        raise ValueError("Generated file inventory differs from the expected manifest")
    for relative, content in files.items():
        path = root / relative
        if not path.is_file() or path.read_bytes() != content.encode("utf-8"):
            raise ValueError(f"Generated content is out of date: {relative}")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--offline", action="store_true", help="Render the committed snapshot without network access")
    mode.add_argument("--blog-only", action="store_true", help="Refresh only RSS; retain the dated GitHub snapshot")
    mode.add_argument("--check", action="store_true", help="Verify all committed output bytes and paths offline, without writing")
    args = parser.parse_args(argv)
    config = json.loads((ROOT / "profile.config.json").read_text(encoding="utf-8"))
    path = ROOT / "data/profile.json"
    snapshot = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"version": 1}
    today = dt.datetime.now(dt.timezone.utc).date().isoformat()
    if not (args.offline or args.check):
        if not args.blog_only:
            snapshot["github"] = {"updated": today, "repositories": collect_repositories(config["owner"], get_token())}
        elif "github" not in snapshot:
            raise ValueError("Run a full refresh before using --blog-only")
        snapshot["blog"] = {"updated": today, "posts": parse_feed(request(config["feed_url"]), config["blog_url"], config["post_count"])}
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    files = render(snapshot, config, readme)
    if args.check:
        check_outputs(files, ROOT)
        print(f"Profile check passed: {len(files)} outputs match the snapshot and source.")
        return 0
    changed = write_outputs(files, ROOT)
    print(f'Profile updated: {len(changed)} changed files; GitHub {snapshot["github"]["updated"]}, blog {snapshot["blog"]["updated"]}.')
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, ValueError, KeyError, OSError, ET.ParseError) as error:
        print(f"Profile update failed: {error}", file=sys.stderr)
        raise SystemExit(1)
