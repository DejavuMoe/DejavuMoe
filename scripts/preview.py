#!/usr/bin/env python3
"""Build a local preview of the profile as GitHub would show it.

Writes .preview/site/: light.html and dark.html render README.md through GitHub's
own Markdown API (sanitizer included) when a token is available, and
gallery.html shows every generated SVG in both themes and both widths. Python
3.11+, standard library only. Nothing here touches the committed profile.
"""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
import re
import shutil
import sys
import urllib.error
import urllib.request

from update_profile import ROOT, get_token

MARKDOWN_API = "https://api.github.com/markdown"
CSS = "https://cdn.jsdelivr.net/npm/github-markdown-css@5.8.1/github-markdown-{theme}.min.css"
PAGE = """<!doctype html>
<html lang="en" data-theme="{theme}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Profile preview — {theme}</title>
<link rel="stylesheet" href="{css}">
<style>
body{{margin:0;background:{bg}}}
.markdown-body{{box-sizing:border-box;max-width:1012px;margin:0 auto;padding:32px 24px}}
@media (max-width:767px){{.markdown-body{{padding:16px}}}}
a[href$="#gh-{hidden}-mode-only"]{{display:none}}
</style></head>
<body><article class="markdown-body">{body}</article></body></html>
"""


def render_markdown(source, token):
    payload = json.dumps({"text": source, "mode": "gfm", "context": "DejavuMoe/DejavuMoe"}).encode()
    req = urllib.request.Request(MARKDOWN_API, data=payload, headers={
        "Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
        "Content-Type": "application/json", "User-Agent": "DejavuMoe-profile-preview/1.0"})
    with urllib.request.urlopen(req, timeout=40) as response:
        return response.read().decode("utf-8")


def localise(body):
    """GitHub rewrites relative image paths to the repository; point them back at the working tree."""
    return re.sub(r'(src|srcset)="https://github\.com/DejavuMoe/DejavuMoe/(?:raw|blob)/[^/]+/', r'\1="', body)


def gallery(names):
    rows = []
    for theme, bg in (("light", "#ffffff"), ("dark", "#0d1117")):
        rows.append(f'<section style="background:{bg};padding:24px"><h2 style="color:{"#1f2328" if theme == "light" else "#e6edf3"};font:600 18px system-ui">{theme}</h2>')
        for name in names:
            if f"-{theme}" in name and not name.endswith("-mobile.svg"):
                mobile = name.replace(".svg", "-mobile.svg")
                rows.append(f'<div style="display:flex;gap:24px;align-items:flex-start;margin:0 0 16px">'
                            f'<img src="assets/generated/{html.escape(name)}" style="width:820px">'
                            f'<img src="assets/generated/{html.escape(mobile)}" style="width:360px"></div>')
        rows.append("</section>")
    return f'<!doctype html><meta charset="utf-8"><title>Profile artwork</title><body style="margin:0">{"".join(rows)}</body>'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=str(ROOT / ".preview" / "site"), help="Output directory")
    parser.add_argument("--no-api", action="store_true", help="Skip GitHub's Markdown API; build the artwork gallery only")
    args = parser.parse_args(argv)
    out = Path(args.out)
    if out.exists():
        shutil.rmtree(out)
    (out / "assets").mkdir(parents=True)
    shutil.copytree(ROOT / "assets" / "generated", out / "assets" / "generated")
    names = sorted(p.name for p in (ROOT / "assets" / "generated").glob("*.svg"))
    (out / "gallery.html").write_text(gallery(names), encoding="utf-8")
    pages = ["gallery.html"]
    if not args.no_api:
        try:
            body = localise(render_markdown((ROOT / "README.md").read_text(encoding="utf-8"), get_token()))
        except (RuntimeError, OSError, urllib.error.URLError) as error:
            print(f"GitHub Markdown API unavailable ({error.__class__.__name__}); gallery only.", file=sys.stderr)
        else:
            for theme, bg, hidden in (("light", "#ffffff", "dark"), ("dark", "#0d1117", "light")):
                page = PAGE.format(theme=theme, css=CSS.format(theme=theme), bg=bg, hidden=hidden, body=body)
                (out / f"{theme}.html").write_text(page, encoding="utf-8")
                pages.append(f"{theme}.html")
    print(f"Preview written to {out}: {', '.join(pages)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
