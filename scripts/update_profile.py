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

from profile_art import pin_card, pin_grid

ROOT = Path(__file__).resolve().parents[1]
API = "https://api.github.com/graphql"
NAME = re.compile(r"[A-Za-z0-9_.-]{1,100}")
OWNER = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})")
COLOR = re.compile(r"#[0-9a-fA-F]{6}")
FIELDS = """
fragment Pin on Repository {
  name url description homepageUrl isPrivate isArchived isFork isTemplate
  owner { login } stargazerCount forkCount primaryLanguage { name color }
  parent { nameWithOwner }
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
    missing = [e["path"][0] for e in result.get("errors") or [] if e.get("type") == "NOT_FOUND" and e.get("path")]
    if missing and len(missing) == len(result["errors"]):
        raise LookupError(missing)
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


def pin_specs(config):
    """Normalise the `pins` list: "repo", "owner/repo", or {"repo": ..., overrides}."""
    specs, seen = [], set()
    for entry in config["pins"]:
        entry = {"repo": entry} if isinstance(entry, str) else dict(entry)
        owner, _, name = entry["repo"].rpartition("/")
        owner = owner or config["owner"]
        if not OWNER.fullmatch(owner) or not NAME.fullmatch(name) or name in (".", ".."):
            raise ValueError(f"Invalid pinned repository: {entry['repo']!r}")
        key = f"{owner}/{name}".casefold()
        if key in seen:
            raise ValueError(f"Repository pinned twice: {owner}/{name}")
        seen.add(key)
        unknown = set(entry) - {"repo", "title", "description", "badge", "link"}
        if unknown:
            raise ValueError(f"Unknown pin options for {owner}/{name}: {', '.join(sorted(unknown))}")
        if "link" in entry and safe_link(entry["link"]) != entry["link"]:
            raise ValueError(f"Pin links must be plain HTTPS URLs: {owner}/{name}")
        specs.append({**entry, "owner": owner, "name": name, "key": key})
    if not specs:
        raise ValueError("Pin at least one repository")
    return specs


def collect_pins(specs, token):
    """All pinned repositories in one GraphQL request, whoever owns them."""
    params = ", ".join(f"$o{i}: String!, $n{i}: String!" for i in range(len(specs)))
    fields = "\n".join(f"  r{i}: repository(owner: $o{i}, name: $n{i}) {{ ...Pin }}" for i in range(len(specs)))
    variables = {}
    for i, spec in enumerate(specs):
        variables[f"o{i}"], variables[f"n{i}"] = spec["owner"], spec["name"]
    try:
        data = graphql(f"query Pins({params}) {{\n{fields}\n}}\n{FIELDS}", variables, token)
    except LookupError as missing:
        names = [f'{specs[int(a[1:])]["owner"]}/{specs[int(a[1:])]["name"]}' for a in missing.args[0]]
        raise ValueError(f"Pinned repository not found (renamed, deleted or private?): {', '.join(names)}") from None
    repos = []
    for i, spec in enumerate(specs):
        node = data.get(f"r{i}")
        if not node or node["isPrivate"]:
            # Never cache private data, even when a local token could read it.
            raise ValueError(f'Pinned repository is not public: {spec["owner"]}/{spec["name"]}')
        language = node["primaryLanguage"] or {}
        color = language.get("color") or ""
        repos.append({
            "pinned_as": f'{spec["owner"]}/{spec["name"]}',
            "owner": node["owner"]["login"], "name": node["name"], "url": node["url"],
            "description": " ".join((node["description"] or "").split()),
            "homepage": safe_homepage(node.get("homepageUrl")),
            "language": language.get("name", ""),
            "language_color": color.lower() if COLOR.fullmatch(color) else "",
            "stars": node["stargazerCount"], "forks": node["forkCount"],
            "archived": node["isArchived"], "template": node["isTemplate"],
            "parent": (node.get("parent") or {}).get("nameWithOwner") if node["isFork"] else None,
        })
    return repos


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


def safe_homepage(value):
    """A project's public demo or docs site: HTTPS, credential-free, not GitHub itself."""
    if not value:
        return ""
    url = urllib.parse.urlsplit(value.strip())
    host = (url.hostname or "").casefold()
    if url.scheme != "https" or not host or url.username or url.password or url.port:
        return ""
    if host == "github.com" or host.endswith(".github.com") or not re.fullmatch(r"[a-z0-9.-]+", host):
        return ""
    path = urllib.parse.quote(url.path, safe="/%:@-._~!$&'*+,;=")
    return urllib.parse.urlunsplit(("https", host, path.rstrip("/"), "", ""))


def safe_link(value):
    """A custom card link: HTTPS, credential-free, no fragment (the theme marker is appended)."""
    if not isinstance(value, str):
        return ""
    url = urllib.parse.urlsplit(value.strip())
    if url.scheme != "https" or not url.hostname or url.username or url.password:
        return ""
    if not re.fullmatch(r"[a-z0-9.-]+(:[0-9]{1,5})?", url.netloc):
        return ""
    path = urllib.parse.quote(url.path, safe="/%:@-._~!$&'*+,;=")
    query = urllib.parse.quote(url.query, safe="%=&-._~")
    return urllib.parse.urlunsplit(("https", url.netloc, path, query, ""))


def plain_summary(value, limit=160):
    """Feed summaries are HTML in some generators: keep readable text only."""
    value = html.unescape(re.sub(r"<[^>]*>", " ", value or ""))
    value = " ".join(value.replace("\x00", "").split())
    return value if len(value) <= limit else value[:limit - 1].rstrip() + "…"


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
            summary = entry.findtext(f"{atom}summary", "")
        else:
            raw_url = entry.findtext("link", "")
            date = entry.findtext("pubDate", "")
            summary = entry.findtext("description", "")
        url = safe_post_url(raw_url, blog_url)
        if not title or not url or url in seen:
            continue
        seen.add(url)
        posts.append({"title": title, "url": url, "date": parse_date(date), "summary": plain_summary(summary)})
    posts.sort(key=lambda p: p["date"], reverse=True)
    if not posts:
        raise ValueError("Feed contains no valid blog posts; previous list retained")
    return posts[:limit]


def stem(pinned_as, owner):
    """Stable, readable asset names: pin-<repo>, or pin-<owner>--<repo> for other owners."""
    who, name = pinned_as.casefold().split("/")
    slug = re.sub(r"[^a-z0-9_-]+", "-", name).strip("-") or "repo"
    return f"pin-{slug}" if who == owner.casefold() else f"pin-{who}--{slug}"


def badge(repo):
    """GitHub's own wording, unless the pin overrides it."""
    if repo["archived"]:
        return "Public archive"
    return "Public template" if repo["template"] else "Public"


def pin_view(spec, repo, owner):
    """Everything a card needs: live metrics plus this pin's overrides."""
    own = repo["owner"].casefold() == owner.casefold()
    return {
        "title": spec.get("title") or (repo["name"] if own else f'{repo["owner"]}/{repo["name"]}'),
        "full_name": f'{repo["owner"]}/{repo["name"]}',
        "description": " ".join(str(spec.get("description") or repo["description"] or "No description provided.").split()),
        "badge": spec.get("badge", badge(repo)),
        "link": spec.get("link") or repo["url"],
        "language": repo["language"], "language_color": repo["language_color"],
        "stars": repo["stars"], "forks": repo["forks"], "parent": repo["parent"],
        "stem": stem(repo["pinned_as"], owner),
    }


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
    if snapshot.get("version") != 2:
        raise ValueError("Unsupported snapshot version; run a full refresh")
    seen = set()
    for repo in snapshot["github"]["repositories"]:
        owner, name = repo["owner"], repo["name"]
        if not OWNER.fullmatch(owner) or not NAME.fullmatch(name):
            raise ValueError("Invalid repository name")
        pinned_owner, _, pinned_name = repo["pinned_as"].partition("/")
        if not OWNER.fullmatch(pinned_owner) or not NAME.fullmatch(pinned_name) or repo["pinned_as"].casefold() in seen:
            raise ValueError("Invalid or duplicate pin key")
        seen.add(repo["pinned_as"].casefold())
        if repo["url"] != f"https://github.com/{owner}/{name}":
            raise ValueError("Unexpected repository URL")
        for flag in ("archived", "template"):
            if not isinstance(repo[flag], bool):
                raise ValueError(f"Invalid {flag} flag")
        if safe_homepage(repo.get("homepage", "")) != repo.get("homepage", ""):
            raise ValueError("Unexpected homepage URL")
        if repo["language_color"] and not COLOR.fullmatch(repo["language_color"]):
            raise ValueError("Invalid language colour")
        if repo["parent"] is not None and not re.fullmatch(r"[A-Za-z0-9-]+/[A-Za-z0-9_.-]+", repo["parent"]):
            raise ValueError("Invalid fork parent")
        for metric in ("stars", "forks"):
            if type(repo[metric]) is not int or repo[metric] < 0:
                raise ValueError(f"Invalid {metric} count")
    if not snapshot["blog"]["posts"]:
        raise ValueError("Empty blog snapshot")
    for post in snapshot["blog"]["posts"]:
        if not post["title"] or safe_post_url(post["url"], config["blog_url"]) != post["url"]:
            raise ValueError("Invalid cached blog post")
        if plain_summary(post.get("summary", "")) != post.get("summary", ""):
            raise ValueError("Invalid cached post summary")
    for section in ("github", "blog"):
        dt.date.fromisoformat(snapshot[section]["updated"])


def pins(snapshot, config):
    """Config order and overrides, joined with the snapshot's live metrics."""
    cached = {r["pinned_as"].casefold(): r for r in snapshot["github"]["repositories"]}
    views = []
    for spec in pin_specs(config):
        if spec["key"] not in cached:
            raise ValueError(f'{spec["owner"]}/{spec["name"]} is pinned but not in the snapshot; run a full refresh')
        views.append(pin_view(spec, cached[spec["key"]], config["owner"]))
    return views


def render(snapshot, config, readme):
    validate_snapshot(snapshot, config)
    cards = pins(snapshot, config)
    files = {}
    for pin in cards:
        for theme in ("light", "dark"):
            for compact in (False, True):
                files[f'assets/generated/{pin["stem"]}-{theme}{"-mobile" if compact else ""}.svg'] = pin_card(pin, theme, compact)
    readme = replace_region(readme, "PINS", pin_grid(cards))
    writing = []
    for p in snapshot["blog"]["posts"]:
        line = f'- `{p["date"].replace("-", ".")}` &nbsp; **[{markdown_text(p["title"])}](<{p["url"]}>)**'
        if p.get("summary"):
            line += f'<br><sub>{markdown_text(p["summary"])}</sub>'
        writing.append(line)
    readme = replace_region(readme, "BLOG-POST-LIST", "\n".join(writing))
    files["README.md"] = readme
    files["data/profile.json"] = json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n"
    return files


def step_summary(snapshot, config, changed):
    """Markdown for the Actions run page."""
    lines = ["## 📌 Profile rebuilt", "",
             f'GitHub snapshot **{snapshot["github"]["updated"]}** · blog snapshot **{snapshot["blog"]["updated"]}** · '
             f'**{len(changed)}** changed files', "",
             "| Card | Stars | Forks | Language |", "| :--- | ---: | ---: | :--- |"]
    for pin in pins(snapshot, config):
        lines.append(f'| {markdown_text(pin["title"])} | {pin["stars"]:,} | {pin["forks"]:,} | {markdown_text(pin["language"] or "—")} |')
    lines += ["", f'Latest post: **{markdown_text(snapshot["blog"]["posts"][0]["title"])}**', ""]
    if changed:
        lines += ["<details><summary>Changed files</summary>", ""] + [f"- `{c}`" for c in changed] + ["", "</details>"]
    return "\n".join(lines) + "\n"


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
    parser.add_argument("--summary", metavar="PATH", help="Append a Markdown report (e.g. $GITHUB_STEP_SUMMARY)")
    args = parser.parse_args(argv)
    config = json.loads((ROOT / "profile.config.json").read_text(encoding="utf-8"))
    path = ROOT / "data/profile.json"
    snapshot = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    today = dt.datetime.now(dt.timezone.utc).date().isoformat()
    if not (args.offline or args.check):
        if not args.blog_only:
            snapshot["version"] = 2
            snapshot["github"] = {"updated": today, "repositories": collect_pins(pin_specs(config), get_token())}
        elif snapshot.get("version") != 2:
            raise ValueError("Run a full refresh before using --blog-only")
        snapshot["blog"] = {"updated": today, "posts": parse_feed(request(config["feed_url"]), config["blog_url"], config["post_count"])}
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    files = render(snapshot, config, readme)
    if args.check:
        check_outputs(files, ROOT)
        print(f"Profile check passed: {len(files)} outputs match the snapshot and source.")
        return 0
    changed = write_outputs(files, ROOT)
    if args.summary:
        with open(args.summary, "a", encoding="utf-8") as report:
            report.write(step_summary(snapshot, config, changed))
    print(f'Profile updated: {len(changed)} changed files; GitHub {snapshot["github"]["updated"]}, blog {snapshot["blog"]["updated"]}.')
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, ValueError, KeyError, OSError, ET.ParseError) as error:
        print(f"Profile update failed: {error}", file=sys.stderr)
        raise SystemExit(1)
