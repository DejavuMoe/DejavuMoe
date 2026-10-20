"""Repository-owned SVG artwork. No remote fonts, scripts, or image services.

Light theme = daytime, dark theme = night. Animation is SMIL, which browsers
play inside <img>; there is nothing to execute.
"""

from __future__ import annotations

import datetime as dt
import html
import math
import unicodedata

from iso import Iso, Kit, Theme, esc, move, num, poly, sway
from town import (BUILDERS, GLOW, PLOTS, birds, cloud, fireflies, flag, island, pebble, shooting_star, sky_defs,
                  stars, sun_or_moon, tram_car, tree)

SANS = ('ui-rounded,"SF Pro Rounded","Segoe UI Variable Display","Segoe UI",system-ui,-apple-system,'
        '"Helvetica Neue",Arial,"PingFang SC","Hiragino Sans GB","Microsoft YaHei","Noto Sans CJK SC",sans-serif')
MONO = 'ui-monospace,SFMono-Regular,"SF Mono",Menlo,Consolas,"Liberation Mono",monospace'
SERIF = ('"Iowan Old Style","Palatino Linotype",Palatino,Georgia,"Times New Roman","Songti SC","Noto Serif CJK SC",'
         '"Source Han Serif SC",SimSun,serif')
STYLE = f"""<style>
text{{font-family:{SANS}}}
.t-name{{font-weight:800;letter-spacing:-1.5px}}
.t-mono{{font-family:{MONO};font-weight:600;letter-spacing:1.4px}}
.t-label{{font-size:11px;font-weight:650}}
.t-tag{{font-size:9px;font-weight:800}}
.t-glyph{{font-weight:800}}
.t-serif{{font-family:{SERIF}}}
</style>"""

ACCENTS = {"cafe": "#f97362", "radio": "#38bdf8", "balloon": "#f5b800", "studio": "#5b8def", "post": "#3f7fd9",
           "lighthouse": "#ef4444", "press": "#8b5cf6", "bucket": "#14b8a6", "house": "#22c55e"}
LANGUAGES = {"TypeScript": "#3178c6", "Go": "#00add8", "Rust": "#dea584", "Python": "#3572a5", "JavaScript": "#f1e05a",
             "C#": "#178600", "HTML": "#e34c26", "Shell": "#89e051", "Vue": "#41b883", "CSS": "#663399"}

UI = {
    "light": {"ink": "#1f2340", "muted": "#4a5578", "soft": "#6b7697", "panel": "#ffffff", "line": "#d0d7de",
              "chip": "#f3f5f9", "paper": "#fbf7ee", "rule": "#1f2340"},
    "dark": {"ink": "#f1f3ff", "muted": "#b3bbe0", "soft": "#8b93ba", "panel": "#111729", "line": "#2b3350",
             "chip": "#1a2138", "paper": "#12172b", "rule": "#d9ddf5"},
}


# --- text helpers --------------------------------------------------------------

def cells(char):
    return 2 if unicodedata.east_asian_width(char) in ("W", "F") else 1


def text_width(value, size):
    """Rough rendered width; CJK is a full em, Latin a little over half."""
    return sum(1.0 if cells(c) == 2 else .56 for c in str(value)) * size


def wrap_copy(value, width, max_lines=2):
    """Wrap by approximate display cells, including CJK, and mark truncation."""
    pending = " ".join(value.split())
    lines = []
    while pending and len(lines) < max_lines:
        used, cut = 0, 0
        for char in pending:
            if used + cells(char) > width:
                break
            used += cells(char)
            cut += 1
        if cut < len(pending) and " " in pending[:cut]:
            cut = pending.rfind(" ", 0, cut) or cut
        lines.append(pending[:cut].rstrip())
        pending = pending[cut:].lstrip()
    if pending:
        lines[-1] = lines[-1].rstrip(".,; ") + "…"
    return lines


def text(x, y, value, size, fill, cls="", weight=None, anchor=None):
    c = f' class="{cls}"' if cls else ""
    w = f' font-weight="{weight}"' if weight else ""
    a = f' text-anchor="{anchor}"' if anchor else ""
    return f'<text x="{num(x)}" y="{num(y)}" font-size="{num(size)}" fill="{fill}"{c}{w}{a}>{esc(value)}</text>'


def svg(w, h, title, defs, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-labelledby="title">\n'
            f'<title id="title">{esc(title)}</title>\n{STYLE}\n<defs>{GLOW}{"".join(defs)}</defs>\n'
            + "\n".join(body) + "\n</svg>\n")


def tint(color, panel, amount=.82):
    from iso import mix
    return mix(color, panel, amount)


# --- small icons (drawn, never font-dependent) -----------------------------------

def icon(kind, x, y, color, size=1.0):
    s = size
    if kind == "star":
        p = [(x + math.cos(math.pi / 2 + i * math.pi / 5) * (6.2 if i % 2 == 0 else 2.7) * s,
              y - math.sin(math.pi / 2 + i * math.pi / 5) * (6.2 if i % 2 == 0 else 2.7) * s) for i in range(10)]
        return poly(p, color)
    if kind == "commit":
        return (f'<path d="M{num(x-7*s)},{num(y)}H{num(x+7*s)}" stroke="{color}" stroke-width="{num(1.8*s)}"/>'
                f'<circle cx="{num(x)}" cy="{num(y)}" r="{num(3.4*s)}" fill="#fff" fill-opacity="0" stroke="{color}" stroke-width="{num(1.8*s)}"/>')
    if kind == "flag":
        return (f'<path d="M{num(x-4*s)},{num(y+7*s)}V{num(y-7*s)}" stroke="{color}" stroke-width="{num(1.8*s)}" stroke-linecap="round"/>'
                f'<path d="M{num(x-4*s)},{num(y-7*s)}h{num(9*s)}l{num(-2.5*s)},{num(3.5*s)} {num(2.5*s)},{num(3.5*s)}h{num(-9*s)}z" fill="{color}"/>')
    if kind == "link":
        return (f'<path d="M{num(x-5*s)},{num(y+5*s)}L{num(x+5*s)},{num(y-5*s)}M{num(x-1*s)},{num(y-5*s)}H{num(x+5*s)}V{num(y+1*s)}" '
                f'stroke="{color}" stroke-width="{num(1.9*s)}" fill="none" stroke-linecap="round" stroke-linejoin="round"/>')
    if kind == "globe":
        r = 6 * s
        return (f'<circle cx="{num(x)}" cy="{num(y)}" r="{num(r)}" fill="none" stroke="{color}" stroke-width="{num(1.5*s)}"/>'
                f'<ellipse cx="{num(x)}" cy="{num(y)}" rx="{num(r*.45)}" ry="{num(r)}" fill="none" stroke="{color}" stroke-width="{num(1.2*s)}"/>'
                f'<path d="M{num(x-r)},{num(y)}H{num(x+r)}" stroke="{color}" stroke-width="{num(1.2*s)}"/>')
    if kind == "tower":
        return "".join(f'<rect x="{num(x-7*s+i*5*s)}" y="{num(y+6*s-h*s)}" width="{num(3.6*s)}" height="{num(h*s)}" rx="1" fill="{color}"/>'
                       for i, h in enumerate((5, 9, 13)))
    if kind == "sparkle":
        r = 7 * s
        return f'<path d="M{num(x)},{num(y-r)}Q{num(x)},{num(y)} {num(x+r)},{num(y)}Q{num(x)},{num(y)} {num(x)},{num(y+r)}Q{num(x)},{num(y)} {num(x-r)},{num(y)}Q{num(x)},{num(y)} {num(x)},{num(y-r)}Z" fill="{color}"/>'
    raise ValueError(kind)


def chip(x, y, kind, label, ui, color, size=13):
    w = text_width(label, size) + 36
    return [f'<rect x="{num(x)}" y="{num(y-13)}" width="{num(w)}" height="26" rx="13" fill="{ui["chip"]}" stroke="{ui["line"]}"/>',
            icon(kind, x + 15, y, color, .85),
            text(x + 28, y + 4.5, label, size, ui["ink"], weight=600)], w


# --- the town ----------------------------------------------------------------------

def town_plan(town):
    """Turn public metrics into buildings: height from commits, a flag for releases."""
    projects = town["projects"]
    logs = [math.log1p(p["commits"]) for p in projects] or [0]
    lo, hi = min(logs), max(logs)
    plan = []
    for p in projects:
        norm = (math.log1p(p["commits"]) - lo) / (hi - lo) if hi > lo else .5
        plan.append({**p, "height": round(1.25 + 2.4 * norm, 3)})
    return plan


def accent(kind):
    return ACCENTS.get(kind, ACCENTS["house"])


def hero(town, theme="light", compact=False):
    t = UI[theme]
    w, h = (600, 1030) if compact else (1000, 620)
    ox, oy = (300, 700) if compact else (712, 262)
    k = Kit(Iso(ox, oy, 26, 28), Theme(theme), seed=2019)
    sky, clip = sky_defs(k, w, h)
    body = [f'<g clip-path="url(#{clip})">', f'<rect width="{w}" height="{h}" fill="url(#{sky})"/>']
    star_total = town["stars"]
    if k.dark:
        body += stars(k, min(star_total, 900), w, h)
        body += shooting_star(k, w * .55, 40, 3)
        body += shooting_star(k, w * .2, 70 if not compact else 440, 7.5)
    body += sun_or_moon(k, w - 72, 72 if not compact else 470)
    lift = 380 if compact else 0
    for y, s, dur, phase, op in ((50, 1.1, 95, .1, .95), (150, .8, 120, .55, .8), (470, 1.3, 140, .3, .5), (330, .7, 80, .8, .7)):
        body += cloud(k, 0, y + lift, s, w, dur, phase, op * (.55 if k.dark else 1))
    if not k.dark:
        body += birds(k, w * .45 if not compact else -40, w + 40, 64 + lift, -6)
        body += birds(k, w * .5 if not compact else -40, w + 40, 150 + lift, -21, 36)
    for i, (dx, dy, s) in enumerate(((-262, 150, 1.25), (235, 190, .95), (-200, 262, .75), (245, 52, .7))):
        body += pebble(k, ox + dx, oy + dy, s, i, plant=i in (0, 1))
    # tallest buildings stand at the back so nothing hides behind them
    plan = sorted(town_plan(town), key=lambda p: -p["height"])
    buildings = []
    for plot, p in enumerate(plan[:len(PLOTS)]):
        builder = BUILDERS.get(p["kind"], BUILDERS["house"])
        buildings.append((plot, builder, p["height"], accent(p["kind"]) if p["releases"] else None, p["name"], accent(p["kind"])))
    body.append(f'<g>{sway("0 0;0 -7;0 0", 7, kind="translate")}')
    scene, labels, _ = island(k, buildings)
    body += scene
    if k.dark:
        body += fireflies(k, ox, oy - 40, 230, 110)
    body += labels
    body.append("</g>")
    body += copy_block(t, k, town, compact)
    body.append("</g>")
    body.append(f'<rect x=".5" y=".5" width="{w-1}" height="{h-1}" rx="18" fill="none" stroke="{t["line"]}" opacity=".7"/>')
    title = (f"Déjà-vu Town: a floating island where each building is one of Dejavu Moe's projects. "
             f"{len(plan)} buildings, {star_total} GitHub stars.")
    return svg(w, h, title, k.defs, body)


def copy_block(t, k, town, compact):
    x = 40 if compact else 52
    y = 70 if compact else 118
    out = [text(x, y, "HELLO, WORLD — WELCOME TO", 12 if not compact else 14, t["soft"], "t-mono"),
           text(x - 3, y + 62 if not compact else y + 70, "Déjà-vu Town", 60 if not compact else 68, t["ink"], "t-name")]
    lines = ["Hi, I'm Dejavu Moe — a curious explorer", "who builds small, self-hosted tools.",
             "Every building on this island is one of", "my projects, rebuilt from GitHub daily."]
    size, gap, top = (17, 24, y + 104) if not compact else (21, 30, y + 120)
    for i, line in enumerate(lines):
        out.append(text(x, top + i * gap, line, size, t["ink"] if i < 2 else t["muted"], weight=600 if i < 2 else 400))
    ly = top + 4 * gap + 26
    star = town["stars"]
    legend = [("tower", "Taller building = more commits", "#5b8def"),
              ("flag", "Flag on the roof = shipped releases", "#ef4444"),
              ("sparkle", f"{star:,} stars in the sky — one per GitHub ★" if k.dark else f"Dark mode turns on {star:,} stars ✦", "#f5b800")]
    step, fs = (30, 14) if not compact else (36, 17)
    for i, (kind, label, color) in enumerate(legend):
        yy = ly + i * step
        out.append(f'<rect x="{x}" y="{num(yy-13)}" width="26" height="26" rx="8" fill="{tint(color, t["panel"])}"/>')
        out.append(icon(kind, x + 13, yy, color, .85))
        out.append(text(x + 38, yy + 5, label, fs, t["ink"], weight=600))
    stamp = f"REBUILT {town['updated']} · {town['repositories']} REPOS · JUST FOR FUN."
    out.append(text(x, 584 if not compact else 996, stamp, 11 if not compact else 13, t["soft"], "t-mono"))
    return out


# --- project cards -----------------------------------------------------------------

def mini_scene(k, project):
    """One building on its own floating tile, centred on the kit's origin."""
    I, L = k.iso, k.L
    a = 1.3
    tile = [I(-a, -a), I(a, -a), I(a, a), I(-a, a)]
    th = 12
    tip = (I.ox + 6, I.oy + I.u * a + 70)
    out = [poly([tile[1], (tile[1][0], tile[1][1] + th), (tile[1][0] - 14, tile[1][1] + 40), tip,
                 (tile[3][0] + 16, tile[3][1] + 38), (tile[3][0], tile[3][1] + th), tile[3]], L("#8f6e5e")),
           poly([tile[1], (tile[1][0], tile[1][1] + th), (tile[1][0] - 14, tile[1][1] + 40), tip], "#000", opacity=".18"),
           poly([tile[3], tile[2], (tile[2][0], tile[2][1] + th), (tile[3][0], tile[3][1] + th)], L("#c8925e")),
           poly([tile[2], tile[1], (tile[1][0], tile[1][1] + th), (tile[2][0], tile[2][1] + th)], L("#9a6644")),
           poly(tile, L("#93d06c")),
           poly([tile[3], tile[2], (tile[2][0], tile[2][1] + 3), (tile[3][0], tile[3][1] + 3)], L("#5fae4f")),
           poly([tile[2], tile[1], (tile[1][0], tile[1][1] + 3), (tile[2][0], tile[2][1] + 3)], L("#4f9a45"))]
    builder = BUILDERS.get(project["kind"], BUILDERS["house"])
    parts, _, flag_at = builder(k, 0, 0, min(project["height"], 3.0))
    out += parts
    if project["releases"] and flag_at:
        out += flag(k, flag_at[0], flag_at[1], accent(project["kind"]))
    return out


def project_card(project, index, total, theme="light", compact=False):
    t = UI[theme]
    w, h = (600, 372) if compact else (1000, 214)
    color = accent(project["kind"])
    scene, fx, fy = (176, 20, 20) if compact else (174, 20, 20)
    k = Kit(Iso(fx + scene / 2, fy + scene * .66, 19, 19), Theme(theme), seed=index * 31)
    sky, clip = sky_defs(k, scene, scene, 14)
    card = k.uid("card")
    k.defs.append(f'<clipPath id="{card}"><rect width="{w}" height="{h}" rx="18"/></clipPath>')
    halo = k.uid("halo")
    k.defs.append(f'<radialGradient id="{halo}" cx="0" cy="0" r="1"><stop offset="0" stop-color="{color}" stop-opacity="{.24 if k.dark else .14}"/><stop offset="1" stop-color="{color}" stop-opacity="0"/></radialGradient>')
    out = [f'<g clip-path="url(#{card})">',
           f'<rect width="{w}" height="{h}" fill="{t["panel"]}"/>',
           f'<ellipse cx="{w}" cy="0" rx="{num(w*.55)}" ry="{num(h*1.1)}" fill="url(#{halo})"/>',
           f'<g transform="translate({fx} {fy})"><g clip-path="url(#{clip})"><rect width="{scene}" height="{scene}" fill="url(#{sky})"/>']
    if k.dark:
        out += stars(Kit(Iso(0, 0), k.L, seed=index), 28, scene, scene * .55)
    else:
        out += cloud(k, 0, 40, .55, scene, 40 + index * 3, index / 9)
    out.append("</g></g>")
    frame = k.uid("frame")
    k.defs.append(f'<clipPath id="{frame}"><rect x="{fx}" y="{fy}" width="{scene}" height="{scene}" rx="14"/></clipPath>')
    out.append(f'<g clip-path="url(#{frame})"><g>{"".join(mini_scene(k, project))}{sway("0 0;0 -4;0 0", 5 + index % 3 * .7, kind="translate")}</g></g>')
    out.append(f'<rect x="{fx}" y="{fy}" width="{scene}" height="{scene}" rx="14" fill="none" stroke="{t["line"]}"/>')
    tx = fx + scene + (28 if not compact else 22)
    name = project["name"]
    language = project["language"] or "Other"
    host = project.get("homepage", "").split("//", 1)[-1].rstrip("/")
    room = w - tx - (80 if not compact else 70)
    rows = (46, 84, 112) if not compact else (52, 96, 132)
    out.append(text(tx, rows[0], f"{index:02d} / {total:02d}", 12 if not compact else 14, color, "t-mono"))
    out.append(text(tx - 1, rows[1], name, min(34, room / max(text_width(name, 1), 1)), t["ink"], "t-name"))
    out.append(f'<circle cx="{tx+6}" cy="{rows[2]-5}" r="6" fill="{LANGUAGES.get(language, "#8b949e")}"/>')
    out.append(text(tx + 18, rows[2], language, 14 if not compact else 16, t["muted"], weight=600))
    if host:
        if compact:
            out.append(icon("globe", tx + 6, rows[2] + 25, t["soft"], .9))
            out.append(text(tx + 18, rows[2] + 30, host, 16, t["soft"], weight=500))
        else:
            hx = tx + 18 + text_width(language, 14) + 18
            out.append(icon("globe", hx + 6, rows[2] - 5, t["soft"], .85))
            out.append(text(hx + 17, rows[2], host, 14, t["soft"], weight=500))
    ax, ay = w - 44, 44
    out.append(f'<circle cx="{ax}" cy="{ay}" r="20" fill="{tint(color, t["panel"])}"/>')
    out.append(icon("link", ax, ay, color, 1.1))
    if compact:
        for i, line in enumerate(wrap_copy(project["description"], 44, 3)):
            out.append(text(22, 238 + i * 27, line, 19, t["muted"]))
        x, y = 22, h - 32
    else:
        for i, line in enumerate(wrap_copy(project["description"], 70)):
            out.append(text(tx, 142 + i * 22, line, 16, t["muted"]))
        x, y = tx, 188 if len(wrap_copy(project["description"], 70)) > 1 else 176
    for kind, label, c in (("star", f'{project["stars"]:,}', "#f5b800"), ("commit", f'{project["commits"]:,} commits', "#5b8def"),
                           ("flag", release_label(project), "#ef4444")):
        parts, width = chip(x, y, kind, label, t, c, 13 if not compact else 15)
        out += parts
        x += width + 8
    out.append("</g>")
    out.append(f'<rect x=".5" y=".5" width="{w-1}" height="{h-1}" rx="18" fill="none" stroke="{t["line"]}"/>')
    title = f'{name}: {project["description"]} — {project["stars"]} stars, {project["commits"]} commits, {project["releases"]} releases.'
    return svg(w, h, title, k.defs, out)


def release_label(project):
    n = project["releases"]
    if not n:
        return "no releases yet"
    tag = project.get("latest_release")
    return f'{n} release{"s" if n != 1 else ""}' + (f" · {tag}" if tag and len(tag) <= 12 else "")


# --- writing: The Dejavu Times ------------------------------------------------------

def edition(date):
    if not date:
        return ""
    d = dt.date.fromisoformat(date)
    return f"{d:%A}, {d:%B} {d.day}, {d.year}"


def times(posts, theme="light", compact=False):
    t = UI[theme]
    w, h = (600, 600) if compact else (1000, 318)
    k = Kit(Iso(0, 0), Theme(theme), seed=11)
    lead, rest = posts[0], posts[1:4 if not compact else 3]
    ink = t["ink"]
    x0 = 30 if compact else 40
    right = w - x0
    body = [f'<rect x=".5" y=".5" width="{w-1}" height="{h-1}" rx="18" fill="{t["paper"]}" stroke="{t["line"]}"/>']
    body.append(text(x0, 40, "NOTES ON SELF-HOSTING, THINGS I LEARN" + ("" if compact else ", AND LIFE IN BETWEEN"), 11 if not compact else 12, t["soft"], "t-mono"))
    if not compact:
        body.append(text(right, 40, "BLOG.DEJAVU.MOE", 11, t["soft"], "t-mono", anchor="end"))
    body.append(f'<path d="M{x0},54H{right}" stroke="{t["rule"]}" stroke-width="2.5"/><path d="M{x0},59H{right}" stroke="{t["rule"]}" stroke-width=".8"/>')
    body.append(text(x0, 110 if not compact else 114, "The Dejavu Times", 50 if not compact else 54, ink, "t-serif", weight=700))
    rule_y = 128 if not compact else 134
    body.append(f'<path d="M{x0},{rule_y}H{right}" stroke="{t["rule"]}" stroke-width=".8"/>')
    # a paper plane looping over the masthead
    px, py = (right - 120, 84) if not compact else (right - 30, 76)
    plane = '<path d="M7,0L-8,-6L-4,0L-8,6Z" fill="#ffffff" stroke="#8ea4bd" stroke-width=".8"/><path d="M7,0L-4,0" stroke="#8ea4bd" stroke-width=".8"/>'
    loop = "M0,0c40,-30 90,-6 60,16s-90,6 -60,-16z" if not compact else "M0,0c22,-24 44,-4 26,10s-44,4 -26,-10z"
    body.append(f'<g transform="translate({num(px)} {num(py)})"><g>{plane}{move(loop, 7, rotate="auto")}</g></g>')
    col = 600 if not compact else right
    meta_y = rule_y + 26
    body.append(text(x0, meta_y, f"LATEST DISPATCH · {edition(lead['date']).upper()}", 11 if not compact else 13, "#e5483f", "t-mono"))
    size = 34 if not compact else 36
    lines = wrap_copy(lead["title"], 30 if not compact else 28, 2)
    for i, line in enumerate(lines):
        body.append(text(x0, meta_y + 44 + i * (size + 8), line, size, ink, "t-serif", weight=700))
    deck_y = meta_y + 44 + (len(lines) - 1) * (size + 8) + 34
    deck = wrap_copy(lead.get("summary", ""), 62 if not compact else 52, 2 if not compact else 3) if lead.get("summary") else []
    for i, line in enumerate(deck):
        body.append(text(x0, deck_y + i * 26, line, 17 if not compact else 19, t["muted"], "t-serif"))
    body.append(text(x0, h - 30, "Read it on the blog ↗  ·  more stories below ↓", 13 if not compact else 16, t["muted"], weight=600))
    if rest:
        if compact:
            ry = deck_y + len(deck) * 26 + 6
            body.append(f'<path d="M{x0},{ry}H{right}" stroke="{t["line"]}"/>')
            body.append(text(x0, ry + 30, "ALSO IN THIS EDITION", 13, t["soft"], "t-mono"))
            for i, post in enumerate(rest):
                yy = ry + 66 + i * 50
                body.append(text(x0, yy, wrap_copy(post["title"], 40, 1)[0], 21, ink, "t-serif", weight=700))
                body.append(text(x0, yy + 20, post["date"].replace("-", "."), 12, t["soft"], "t-mono"))
        else:
            body.append(f'<path d="M{col+20},{rule_y+14}V{h-22}" stroke="{t["line"]}"/>')
            cx = col + 44
            body.append(text(cx, meta_y, "ALSO IN THIS EDITION", 11, t["soft"], "t-mono"))
            for i, post in enumerate(rest):
                yy = meta_y + 36 + i * 46
                body.append(text(cx, yy, wrap_copy(post["title"], 26, 1)[0], 17, ink, "t-serif", weight=700))
                body.append(text(cx, yy + 17, post["date"].replace("-", "."), 10.5, t["soft"], "t-mono"))
    title = f'The Dejavu Times — latest post: {lead["title"]} ({lead["date"]}).'
    return svg(w, h, title, k.defs, body)


# --- footer ------------------------------------------------------------------------

def footer(town, theme="light", compact=False):
    t = UI[theme]
    w, h = (600, 220) if compact else (1000, 170)
    k = Kit(Iso(0, 0), Theme(theme), seed=5)
    sky, clip = sky_defs(k, w, h)
    body = [f'<g clip-path="url(#{clip})">', f'<rect width="{w}" height="{h}" fill="url(#{sky})"/>']
    if k.dark:
        body += stars(k, 70, w, h * .7)
    else:
        body += cloud(k, 0, 34, .7, w, 70, .2)
        body += cloud(k, 0, 70, .5, w, 90, .7)

    def hill(y, amp, phase, color):
        points = "".join(f"L{x},{num(y + amp * math.sin(x / w * math.tau * 1.4 + phase))}" for x in range(0, w + 21, 20))
        return f'<path d="M0,{h}V{num(y)}{points}V{h}Z" fill="{k.L(color)}"/>'

    body.append(hill(h - 64, 10, .6, "#a6dd85"))
    k3 = Kit(Iso(0, 0, 18, 18), k.L, seed=9)
    for i, x in enumerate(range(40, w, 130)):
        k3.iso.ox, k3.iso.oy = x + (17 * i) % 40, h - 44 - (i % 2) * 6
        body += tree(k3, 0, 0, .8, "pine" if i % 2 else "round")
    body.append(hill(h - 38, 6, 2.1, "#7cc35f"))
    track = h - 22
    body.append(f'<path d="M0,{track}H{w}" stroke="{k.L("#8a6f55")}" stroke-width="6" stroke-dasharray="1.6 4.2"/>'
                f'<path d="M0,{track-1.5}H{w}" stroke="{k.L("#6f6a73")}" stroke-width="1"/>')
    cars = "".join(f'<g transform="translate({-i*23} 0)">{tram_car(k, i == 0)}</g>' for i in range(3))
    body.append(f'<g><g>{cars}<animateTransform attributeName="transform" type="translate" from="-20 {track}" to="{w+80} {track}" dur="14s" begin="-4s" repeatCount="indefinite"/></g></g>')
    body.append(text(w / 2, 52 if not compact else 60, "Thanks for visiting Déjà-vu Town", 24 if not compact else 30, t["ink"], "t-name", anchor="middle"))
    body.append(text(w / 2, 78 if not compact else 92, "See you again — it will feel familiar.", 14 if not compact else 18, t["muted"], anchor="middle", weight=500))
    body.append("</g>")
    body.append(f'<rect x=".5" y=".5" width="{w-1}" height="{h-1}" rx="18" fill="none" stroke="{t["line"]}" opacity=".7"/>')
    return svg(w, h, "Thanks for visiting Déjà-vu Town. See you again — it will feel familiar.", k.defs, body)


# --- markup ----------------------------------------------------------------------

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
