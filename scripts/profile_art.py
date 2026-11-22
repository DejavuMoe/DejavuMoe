"""Repository-owned SVG pin cards. No remote fonts, scripts, or image services.

Each card mirrors GitHub's own pinned-repository card in both themes, and has a
compact variant with larger lettering that GitHub swaps in on narrow screens.
"""

from __future__ import annotations

import html
import unicodedata

SANS = ('-apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans",Helvetica,Arial,"PingFang SC",'
        '"Hiragino Sans GB","Microsoft YaHei","Noto Sans CJK SC",sans-serif')
MONO = 'ui-monospace,SFMono-Regular,"SF Mono",Menlo,Consolas,"Liberation Mono",monospace'

# GitHub's Primer colours for the profile page background each card sits on.
UI = {
    "light": {"bg": "#ffffff", "border": "#d1d9e0", "link": "#0969da", "text": "#59636e", "icon": "#59636e"},
    "dark": {"bg": "#0d1117", "border": "#3d444d", "link": "#4493f8", "text": "#9198a1", "icon": "#9198a1"},
}
FALLBACK_LANGUAGE = "#8b949e"

# Octicons (MIT licensed), 16px grid.
REPO = ("M2 2.5A2.5 2.5 0 0 1 4.5 0h8.75a.75.75 0 0 1 .75.75v12.5a.75.75 0 0 1-.75.75h-2.5a.75.75 0 0 1 0-1.5h1.75v-2h-8"
        "a1 1 0 0 0-.714 1.7.75.75 0 1 1-1.072 1.05A2.495 2.495 0 0 1 2 11.5Zm10.5-1h-8a1 1 0 0 0-1 1v6.708A2.486 2.486 0 0 1 "
        "4.5 9h8ZM5 12.25a.25.25 0 0 1 .25-.25h3.5a.25.25 0 0 1 .25.25v3.25a.25.25 0 0 1-.4.2l-1.45-1.087a.25.25 0 0 0-.3 0"
        "L5.4 15.7a.25.25 0 0 1-.4-.2Z")
STAR = ("M8 .25a.75.75 0 0 1 .673.418l1.882 3.815 4.21.612a.75.75 0 0 1 .416 1.279l-3.046 2.97.719 4.192a.751.751 0 0 1"
        "-1.088.791L8 12.347l-3.766 1.98a.75.75 0 0 1-1.088-.79l.72-4.194L.818 6.374a.75.75 0 0 1 .416-1.28l4.21-.611L7.327"
        ".668A.75.75 0 0 1 8 .25Zm0 2.445L6.615 5.5a.75.75 0 0 1-.564.41l-3.097.45 2.24 2.184a.75.75 0 0 1 .216.664l-.528 "
        "3.084 2.769-1.456a.75.75 0 0 1 .698 0l2.77 1.456-.53-3.084a.75.75 0 0 1 .216-.664l2.24-2.183-3.096-.45a.75.75 0 0 1"
        "-.564-.41L8 2.694Z")
FORK = ("M5 5.372v.878c0 .414.336.75.75.75h4.5a.75.75 0 0 0 .75-.75v-.878a2.25 2.25 0 1 1 1.5 0v.878a2.25 2.25 0 0 1-2.25 "
        "2.25h-1.5v2.128a2.251 2.251 0 1 1-1.5 0V8.5h-1.5A2.25 2.25 0 0 1 3.5 6.25v-.878a2.25 2.25 0 1 1 1.5 0ZM5 3.25a.75.75"
        " 0 1 0-1.5 0 .75.75 0 0 0 1.5 0Zm6.75.75a.75.75 0 1 0 0-1.5.75.75 0 0 0 0 1.5Zm-3 8.75a.75.75 0 1 0-1.5 0 .75.75 0 "
        "0 0 1.5 0Z")

# Wide cards sit two to a row at about 415px; compact cards are what phones get.
LAYOUT = {
    False: {"w": 440, "h": 144, "pad": 16, "name": 15, "badge": 12, "desc": 13.5, "lead": 20, "lines": 3, "meta": 12.5, "icon": 1.0},
    True: {"w": 300, "h": 170, "pad": 16, "name": 22, "badge": 0, "desc": 16, "lead": 22, "lines": 2, "meta": 16, "icon": 1.25},
}


def esc(value):
    return html.escape(str(value), quote=True)


def num(value):
    value = round(value, 1)
    return str(int(value)) if value == int(value) else f"{value:.1f}"


def text_width(value, size):
    """Rough rendered width; CJK is a full em, Latin a little over half."""
    return sum(char_width(c) for c in str(value)) * size


def char_width(c):
    if unicodedata.east_asian_width(c) in ("W", "F"):
        return 1.0
    if c in "ijlI.,:;'|!" or c == " ":
        return .28
    if c in "frt()-":
        return .36
    if c in "mwMW":
        return .82
    return .64 if c.isupper() else .54


def wrap(value, size, width, max_lines):
    """Greedy wrap by estimated pixel width (breaking at spaces when possible); mark truncation."""
    pending = " ".join(str(value).split())
    lines = []
    while pending and len(lines) < max_lines:
        used, cut = 0.0, 0
        for char in pending:
            step = text_width(char, size)
            if used + step > width:
                break
            used += step
            cut += 1
        if cut < len(pending) and " " in pending[:cut]:
            cut = pending.rfind(" ", 0, cut) or cut
        lines.append(pending[:cut].rstrip())
        pending = pending[cut:].lstrip()
    if pending:
        last = lines[-1]
        while last and text_width(last + "…", size) > width:
            last = last[:-1]
        lines[-1] = last.rstrip(".,;:， ") + "…"
    return lines


def fit(value, size, width):
    """Shrink a single line until it fits, down to 70%, then ellipsize."""
    for scale in (1, .92, .85, .78, .7):
        if text_width(value, size * scale) <= width:
            return value, size * scale
    return wrap(value, size * .7, width, 1)[0], size * .7


def text(x, y, value, size, fill, weight=None, anchor=None, family=None):
    w = f' font-weight="{weight}"' if weight else ""
    a = f' text-anchor="{anchor}"' if anchor else ""
    f = f' font-family="{esc(family)}"' if family else ""
    return f'<text x="{num(x)}" y="{num(y)}" font-size="{num(size)}" fill="{fill}"{w}{a}{f}>{esc(value)}</text>'


def octicon(path, x, y, color, scale):
    return f'<path transform="translate({num(x)} {num(y)}) scale({scale:g})" d="{path}" fill="{color}"/>'


def compact_number(value):
    if value < 1000:
        return str(value)
    return f"{value / 1000:.1f}".rstrip("0").rstrip(".") + "k"


def pin_card(pin, theme="light", compact=False):
    """One pinned-repository card. `pin` is a validated view from update_profile.pin_view."""
    t, L = UI[theme], LAYOUT[compact]
    w, h, pad, s = L["w"], L["h"], L["pad"], L["icon"]
    inner = w - 2 * pad - 8  # breathing room: widths are estimates
    body = [f'<rect x=".5" y=".5" width="{w-1}" height="{h-1}" rx="6" fill="{t["bg"]}" stroke="{t["border"]}"/>']

    head = pad + 16 * s / 2 + 2
    body.append(octicon(REPO, pad, head - 8 * s, t["icon"], s))
    nx = pad + 16 * s + 8
    badge = pin["badge"] if not compact else ""
    badge_w = text_width(badge, L["badge"]) + 16 if badge else 0
    name, size = fit(pin["title"], L["name"], w - nx - pad - (badge_w + 8 if badge else 0))
    body.append(text(nx, head + size * .36, name, size, t["link"], weight=600))
    if badge:
        bx = nx + text_width(name, size) + 8
        body.append(f'<rect x="{num(bx)}" y="{num(head - 10)}" width="{num(badge_w)}" height="20" rx="10" fill="none" stroke="{t["border"]}"/>')
        body.append(text(bx + badge_w / 2, head + 4.2, badge, L["badge"], t["text"], weight=500, anchor="middle"))

    y = head + 16 * s / 2 + 8
    if pin["parent"] and not compact:
        y += 12
        body.append(text(pad, y, f'Forked from {pin["parent"]}', 12, t["text"]))
        y += 4
    lines = wrap(pin["description"], L["desc"], inner, L["lines"] - (1 if pin["parent"] and not compact else 0))
    for i, line in enumerate(lines):
        body.append(text(pad, y + L["lead"] * (i + .75), line, L["desc"], t["text"]))

    my = h - pad - 2
    x = pad
    ms = L["meta"]
    if pin["language"]:
        r = ms * .48
        body.append(f'<circle cx="{num(x + r)}" cy="{num(my - ms * .34)}" r="{num(r)}" fill="{pin["language_color"] or FALLBACK_LANGUAGE}"/>')
        body.append(text(x + 2 * r + 6, my, pin["language"], ms, t["text"]))
        x += 2 * r + 6 + text_width(pin["language"], ms) + 16
    for path, value in ((STAR, pin["stars"]), (FORK, pin["forks"])):
        if value or path is STAR:
            k = ms / 16 * 1.05
            body.append(octicon(path, x, my - ms * .34 - 8 * k, t["icon"], round(k, 3)))
            label = compact_number(value)
            body.append(text(x + 16 * k + 5, my, label, ms, t["text"]))
            x += 16 * k + 5 + text_width(label, ms) + 16

    title = f'{pin["full_name"]}: {pin["description"]} ({pin["stars"]} stars, {pin["forks"]} forks)'
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-labelledby="title">\n'
            f'<title id="title">{esc(title)}</title>\n<style>text{{font-family:{SANS}}}</style>\n'
            + "\n".join(body) + "\n</svg>\n")


# --- markup ----------------------------------------------------------------------

def themed_image(stem, alt, link, width):
    """GitHub's #gh-*-mode-only links pick the theme; the inner picture picks the layout by width."""
    escaped = html.escape(alt, quote=True)
    target = html.escape(link, quote=True)
    return [
        f'<a href="{target}#gh-{theme}-mode-only"><picture>'
        f'<source media="(max-width: 600px)" srcset="assets/generated/{stem}-{theme}-mobile.svg">'
        f'<img src="assets/generated/{stem}-{theme}.svg" width="{width}" alt="{escaped}">'
        f'</picture></a>'
        for theme in ("light", "dark")
    ]


def pin_grid(pins, columns=2):
    """Cards two to a row, like GitHub's pinned grid; each row is its own paragraph for spacing."""
    rows = []
    for i in range(0, len(pins), columns):
        cells = []
        for pin in pins[i:i + columns]:
            alt = f'{pin["full_name"]} — {pin["description"]} ({pin["stars"]} stars)'
            cells += themed_image(pin["stem"], alt, pin["link"], "49%")
        rows.append("<p>\n" + "\n".join(cells) + "\n</p>")
    return "\n\n".join(rows)
