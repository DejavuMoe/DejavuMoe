"""Repository-owned SVG artwork. No remote fonts, JavaScript, or image services."""

from __future__ import annotations

import html
import math
import unicodedata


def wrap_copy(value, width, max_lines=2):
    """Wrap by approximate display cells, including CJK, and mark truncation."""
    pending = " ".join(value.split())
    lines = []
    while pending and len(lines) < max_lines:
        cells, cut = 0, 0
        for char in pending:
            next_cells = 2 if unicodedata.east_asian_width(char) in ("W", "F") else 1
            if cells + next_cells > width:
                break
            cells += next_cells
            cut += 1
        if cut < len(pending) and " " in pending[:cut]:
            cut = pending.rfind(" ", 0, cut) or cut
        lines.append(pending[:cut].rstrip())
        pending = pending[cut:].lstrip()
    if pending:
        lines[-1] = lines[-1].rstrip(".,; ") + "…"
    return lines

PALETTES = {
    "light": {
        "paper": "#f3f1e9", "ink": "#22251f", "muted": "#62695e",
        "line": "#d4d8cc", "accent": "#c74226", "contour": "#64755c",
    },
    "dark": {
        "paper": "#171b17", "ink": "#f0f1e6", "muted": "#a5b09e",
        "line": "#374132", "accent": "#ff8768", "contour": "#b6c8a5",
    },
}
SANS = "Arial, Helvetica, sans-serif"
MONO = "'Courier New', monospace"


def text(x, y, value, size=16, *, fill="", weight=400, mono=False, extra=""):
    family = MONO if mono else SANS
    return (
        f'<text x="{x}" y="{y}" font-family="{family}" font-size="{size}" '
        f'font-weight="{weight}" fill="{fill}" {extra}>{html.escape(str(value))}</text>'
    )


def svg(width, height, title, body, p):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-labelledby="title">\n'
        f'<title id="title">{html.escape(title)}</title>\n'
        f'<rect width="{width}" height="{height}" fill="{p["paper"]}"/>\n'
        + "\n".join(body) + "\n</svg>\n"
    )


def contours(cx, cy, scale, p):
    """An original topographic loop, not a data visualization."""
    paths = []
    for ring in range(23):
        points = []
        for step in range(181):
            t = step * math.tau / 180
            rx, ry = 132 - ring * 4.4, 145 - ring * 4.8
            x = cx + scale * (rx * math.cos(t) + 23 * math.sin(2 * t + ring * .052))
            y = cy + scale * (ry * math.sin(t) + 14 * math.cos(3 * t + ring * .044))
            points.append(f'{"M" if step == 0 else "L"}{x:.2f},{y:.2f}')
        paths.append(
            f'<path d="{" ".join(points)}Z" fill="none" stroke="{p["contour"]}" '
            f'stroke-width="{1.05 if ring % 4 else 1.7}" opacity="{.72 if ring % 4 else .94}"/>'
        )
    paths.append(f'<path d="M{cx-7},{cy}h14 M{cx},{cy-7}v14" stroke="{p["accent"]}" stroke-width="2"/>')
    return paths


def hero(theme="light", compact=False):
    p = PALETTES[theme]
    w, h = (600, 500) if compact else (1000, 378)
    left = 30 if compact else 42
    body = [
        text(left, 36, "DEJAVU.MOE  /  PERSONAL ARCHIVE", 12 if compact else 13,
             fill=p["muted"], mono=True, extra='letter-spacing="1.1"'),
        f'<path d="M{left},53H{w-left}" stroke="{p["line"]}"/>',
    ]
    if compact:
        body += contours(446, 243, .82, p)
        body += [f'<rect x="24" y="95" width="290" height="300" fill="{p["paper"]}" opacity=".94"/>']
        body += [
            text(left-4, 190, "DEJA", 112, fill=p["ink"], weight=900, extra='letter-spacing="-7"'),
            text(left-4, 287, "VU", 112, fill=p["ink"], weight=900, extra='letter-spacing="-7"'),
            text(left-4, 384, "MOE.", 112, fill=p["ink"], weight=900, extra='letter-spacing="-7"'),
            text(555, 390, "EST. 2019", 12, fill=p["muted"], mono=True, extra='text-anchor="end"'),
        ]
    else:
        body += contours(780, 199, .88, p)
        body += [
            text(left-5, 173, "DEJAVU", 112, fill=p["ink"], weight=900, extra='letter-spacing="-7"'),
            text(left-5, 281, "MOE.", 112, fill=p["ink"], weight=900, extra='letter-spacing="-7"'),
            text(338, 273, "A CURIOUS", 13, fill=p["muted"], mono=True, extra='letter-spacing="1"'),
            text(338, 292, "EXPLORER.", 13, fill=p["muted"], mono=True, extra='letter-spacing="1"'),
            text(958, 81, "EST. 2019", 11, fill=p["muted"], mono=True, extra='text-anchor="end"'),
        ]
    body += [
        f'<path d="M{left},{h-55}H{w-left}" stroke="{p["line"]}"/>',
        f'<rect x="{left}" y="{h-32}" width="8" height="8" fill="{p["accent"]}"/>',
        text(left+20, h-24, "OPEN SOURCE / SMALL TOOLS", 12, fill=p["ink"], mono=True),
        text(w-left, h-24, "JUST FOR FUN.", 12, fill=p["accent"], mono=True, extra='text-anchor="end"'),
    ]
    return svg(w, h, "Dejavu Moe — a curious explorer. Open source, small tools, just for fun.", body, p)


def project_card(repo, index, description, theme="light", compact=False):
    p = PALETTES[theme]
    w, h = (600, 285) if compact else (1000, 152)
    left = 30 if compact else 36
    name = repo["name"]
    language = repo["language"] or "Other"
    title = f'{name}: {description} — {repo["stars"]} stars, {repo["commits"]} commits, {repo["releases"]} releases.'
    body = [
        f'<path d="M0,0H{w}" stroke="{p["line"]}" stroke-width="2"/>',
        text(left, 34, f"{index:02d}", 13, fill=p["accent"], mono=True),
    ]
    if compact:
        size = min(40, 500 / max(len(name), 1) * 1.6)
        body += [
            text(left, 85, name, size, fill=p["ink"], weight=700, extra='letter-spacing="-1"'),
            text(w-left, 34, language.upper(), 17, fill=p["muted"], mono=True, extra='text-anchor="end"'),
            text(w-left, 85, "↗", 35, fill=p["accent"], extra='text-anchor="end"'),
        ]
        for i, line in enumerate(wrap_copy(description, width=44)):
            body.append(text(left, 125 + i*28, line, 22, fill=p["muted"]))
        body.append(f'<path d="M{left},182H{w-left}" stroke="{p["line"]}"/>')
        for x, field, label in [(left, "stars", "STARS"), (225, "commits", "COMMITS"), (418, "releases", "RELEASES")]:
            body += [
                text(x, 227, f'{repo[field]:,}', 34, fill=p["ink"], weight=700),
                text(x, 258, label, 18, fill=p["muted"], mono=True),
            ]
    else:
        size = min(31, 488 / max(len(name), 1) * 1.7)
        body += [
            text(83, 49, name, size, fill=p["ink"], weight=700, extra='letter-spacing="-.8"'),
            text(83, 120, language.upper(), 11, fill=p["accent"], mono=True, extra='letter-spacing=".8"'),
            f'<path d="M604,30V122" stroke="{p["line"]}"/>',
            text(965, 85, "↗", 29, fill=p["accent"], extra='text-anchor="end"'),
        ]
        for i, line in enumerate(wrap_copy(description, width=58)):
            body.append(text(83, 77+i*20, line, 16, fill=p["muted"]))
        for x, field, label in [(637, "stars", "STARS"), (738, "commits", "COMMITS"), (847, "releases", "RELEASES")]:
            body += [
                text(x, 75, f'{repo[field]:,}', 28, fill=p["ink"], weight=700),
                text(x, 99, label, 10, fill=p["muted"], mono=True),
            ]
    return svg(w, h, title, body, p)


def picture(stem, alt, link=None):
    """Separate theme and layout: GitHub's themed-picture rewrites compound media.

    GitHub's native theme-only link CSS honors explicit site themes AND auto mode;
    the inner picture handles viewport width without a color-scheme condition.
    """
    escaped = html.escape(alt, quote=True)
    target = html.escape(link or "https://github.com/DejavuMoe", quote=True)
    variants = []
    for theme in ("light", "dark"):
        variants.append("\n".join([
            f'<a href="{target}#gh-{theme}-mode-only">',
            '<picture>',
            f'  <source media="(max-width: 600px)" srcset="assets/generated/{stem}-{theme}-mobile.svg">',
            f'  <img src="assets/generated/{stem}-{theme}.svg" width="100%" alt="{escaped}">',
            '</picture>',
            '</a>',
        ]))
    return "\n\n".join(variants)
