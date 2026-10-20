"""Déjà-vu Town: a floating isometric island where every building is a project.

Building height follows default-branch commits, a roof flag marks shipped releases,
and the night sky holds one star per GitHub star. Daylight for GitHub's light theme,
night for its dark theme.
"""

from __future__ import annotations

import math

from iso import (Kit, anim, attrs, ball, box, cone, esc, frustum, gable, mix, move, num, poly, pts,
                 pyramid, shade, spin, sway)

LIT = ("#ffd166", "#ffe08a", "#ffc24b")
UNLIT = "#2a3266"
GLASS = "#cfe8ff"


# --- shared details --------------------------------------------------------------

def windows(k, side, x, y, z, span, height, cols, floor_h=.62, door=None, sill=.12, skip_top=0):
    """A grid of windows on the wall whose top-left corner is (x, y, z)."""
    rows = max(1, round((height - sill) / floor_h))
    fh = (height - sill) / rows
    cw = span / cols
    out = [f'<g transform="{k.iso.face(side, x, y, z)}">']
    for row in range(skip_top, rows):
        for col in range(cols):
            if row == rows - 1 and col == door:
                fill = "#ffb347" if k.dark else k.L("#8a5a3c")
                out.append(f'<rect{attrs(x=col*cw+cw*.27, y=height-fh*.8, width=cw*.46, height=fh*.8)} fill="{fill}"/>')
                continue
            wx, wy, ww, wh = col * cw + cw * .25, row * fh + fh * .24, cw * .5, fh * .44
            if k.dark:
                lit = k.r() < .68
                fill = LIT[int(k.r() * 3)] if lit else UNLIT
                extra = ""
                if k.r() < .14:
                    on, off = fill if lit else LIT[0], UNLIT
                    extra = anim("fill", f"{on};{off};{on}", k.r(9, 21), -k.r(0, 20), calcMode="discrete", keyTimes=f"0;{num(k.r(.55, .8))};1")
                out.append(f'<rect{attrs(x=wx, y=wy, width=ww, height=wh)} fill="{fill}">{extra}</rect>' if extra else f'<rect{attrs(x=wx, y=wy, width=ww, height=wh)} fill="{fill}"/>')
            else:
                out.append(f'<rect{attrs(x=wx, y=wy, width=ww, height=wh)} fill="{GLASS}"/>')
                out.append(f'<rect{attrs(x=wx, y=wy, width=ww*.35, height=wh)} fill="#fff" opacity=".55"/>')
    out.append("</g>")
    return out


def flag(k, sx, sy, color, begin=0.0):
    a = f"M{num(sx)},{num(sy-15)} q6,-2 12,1 q-6,3 -12,6z"
    b = f"M{num(sx)},{num(sy-15)} q6,3 12,1 q-6,1 -12,6z"
    return [
        f'<path d="M{num(sx)},{num(sy)}V{num(sy-16)}" stroke="{k.L("#5b5148")}" stroke-width="1.4"/>',
        f'<path d="{a}" fill="{k.L(color)}">{anim("d", f"{a};{b};{a}", 1.6, begin)}</path>',
    ]


def label(k, sx, sy, text, dot):
    w = len(text) * 6.4 + 22
    x = sx - w / 2
    bg, ink, edge = k.L.pick(("#ffffff", "#1f2340", "#1f234022"), ("#0d1117", "#e6edf3", "#ffffff30"))
    return [
        '<g class="label">',
        f'<path d="M{num(sx-4)},{num(sy-1)} l4,5 l4,-5z" fill="{bg}"/>',
        f'<rect{attrs(x=x, y=sy-19, width=w, height=18, rx=9)} fill="{bg}" stroke="{edge}" opacity=".94"/>',
        f'<circle{attrs(cx=x+10, cy=sy-10, r=3)} fill="{dot}"/>',
        f'<text{attrs(x=x+17, y=sy-6)} class="t-label" fill="{ink}">{esc(text)}</text>',
        "</g>",
    ]


def tree(k, x, y, scale=1.0, kind="round"):
    I = k.iso
    sx, sy = I(x, y, 0)
    s = scale
    out = [f'<ellipse{attrs(cx=sx, cy=sy, rx=9*s, ry=4.5*s)} fill="#000" opacity=".12"/>',
           f'<g>{sway(f"-2.5 {num(sx)} {num(sy)};2.5 {num(sx)} {num(sy)};-2.5 {num(sx)} {num(sy)}", k.r(4, 7), -k.r(0, 6))}']
    out.append(f'<rect{attrs(x=sx-1.8*s, y=sy-11*s, width=3.6*s, height=11*s)} fill="{k.L("#8b5e3c")}"/>')
    if kind == "pine":
        green = "#3f9b5a"
        for i, (w, h, o) in enumerate([(11, 13, 9), (9, 12, 17), (6.5, 10, 24)]):
            top, base = sy - (o + h) * s, sy - o * s
            out.append(poly([(sx - w * s, base), (sx, top), (sx, base + 2 * s)], k.L(shade(green, 1.05 - i * .02))))
            out.append(poly([(sx, top), (sx + w * s, base), (sx, base + 2 * s)], k.L(shade(green, .78))))
    else:
        green = ("#6cc56b", "#58b45f", "#7fcf6a")[int(k.r() * 3)]
        out += ball(k, sx - 5 * s, sy - 15 * s, 7 * s, green, gloss=False)
        out += ball(k, sx + 5 * s, sy - 16 * s, 7.5 * s, shade(green, .92), gloss=False)
        out += ball(k, sx, sy - 22 * s, 8.5 * s, green)
    out.append("</g>")
    return out


def bubble(sx, sy, color, begin, dur=6.0, ink="#4b4f6b"):
    body = (f'<rect x="-13" y="-17" width="26" height="15" rx="6" fill="{color}"/>'
            f'<path d="M-4,-2.5 l-2,5 l7,-5z" fill="{color}"/>'
            + "".join(f'<circle cx="{c}" cy="-9.5" r="1.7" fill="{ink}"/>' for c in (-6, 0, 6)))
    return (f'<g transform="translate({num(sx)} {num(sy)})"><g transform="scale(0)">{body}'
            f'<animateTransform attributeName="transform" type="scale" values="0;1.08;1;1;0" keyTimes="0;.08;.12;.7;.78" dur="{num(dur)}s" begin="{num(begin)}s" repeatCount="indefinite"/>'
            f'<animateTransform attributeName="transform" type="translate" values="0 0;0 0;0 -10" keyTimes="0;.12;.78" dur="{num(dur)}s" begin="{num(begin)}s" repeatCount="indefinite" additive="sum"/>'
            "</g></g>")


# --- buildings --------------------------------------------------------------------
# Each builder returns (svg parts, label anchor, flag anchor). Footprints stay within ±0.9.

def house(k, x, y, H, wall="#f4e3c3", roof="#e0745a"):
    I = k.iso
    x0, y0, dx, dy = x - .8, y - .7, 1.6, 1.4
    out = box(k, x0, y0, 0, dx, dy, H, wall)
    out += windows(k, "left", x0, y0 + dy, H, dx, H, 3, door=1)
    out += windows(k, "right", x0 + dx, y0 + dy, H, dy, H, 2)
    out += gable(k, x0, y0, H, dx, dy, .7, roof, wall)
    return out, I(x, y, H + .7), I(x + .55, y, H + .5)


def cafe(k, x, y, H):
    """Ecoku: a corner café where conversations keep popping up."""
    I, L = k.iso, k.L
    out, top, fl = house(k, x, y, H, wall="#fbe7d0", roof="#e86a5c")
    x0, x1, yf = x - .8, x + .8, y + .7
    za = min(.78, H * .5)
    stripes = 6
    for i in range(stripes):
        a, b = x0 + (x1 - x0) * i / stripes, x0 + (x1 - x0) * (i + 1) / stripes
        c = "#ffffff" if i % 2 else "#f05a5a"
        out.append(poly([I(a, yf, za), I(b, yf, za), I(b, yf + .3, za - .2), I(a, yf + .3, za - .2)], L(c)))
    out.append(poly([I(x0, yf + .3, za - .2), I(x1, yf + .3, za - .2), I(x1, yf + .3, za - .26), I(x0, yf + .3, za - .26)], L("#c94545")))
    bx, by = top
    colors = ("#ffffff", "#ffe9a8", "#c9f0ff")
    for i, (ox, oy) in enumerate([(-22, -8), (18, -20), (-4, -34)]):
        out.append(bubble(bx + ox, by + oy, colors[i], begin=-i * 2.0))
    return out, (top[0], top[1] - 4), fl


def radio(k, x, y, H):
    """edgeTTS: a broadcast tower turning text into sound waves."""
    I, L = k.iso, k.L
    cx, cy, base, T = x - .2, y - .2, .48, H + 1.6
    out = []
    corners = [(-1, -1), (1, -1), (1, 1), (-1, 1)]

    def leg(i, z):
        r = base * (1 - .82 * z / T)
        return I(cx + corners[i][0] * r, cy + corners[i][1] * r, z)

    red, white = L("#e5483f"), L("#f4f1ea")
    levels = [T * i / 6 for i in range(7)]
    for i in (0, 1, 3):  # back legs first
        out.append(f'<path d="M{pts([leg(i, 0), leg(i, T * .94)])}" stroke="{red}" stroke-width="1.6"/>')
    for a, b in zip(levels, levels[1:]):
        for i, j in ((3, 2), (2, 1)):
            out.append(f'<path d="M{pts([leg(i, a), leg(j, b), leg(j, a), leg(i, b)])}" stroke="{white}" stroke-width=".9" fill="none" opacity=".9"/>')
        out.append(f'<path d="M{pts([leg(0, b), leg(1, b), leg(2, b), leg(3, b)])}Z" stroke="{red}" stroke-width=".9" fill="none"/>')
    out.append(f'<path d="M{pts([leg(2, 0), leg(2, T * .94)])}" stroke="{red}" stroke-width="1.8"/>')
    tx, ty = I(cx, cy, T)
    out.append(f'<path d="M{num(tx)},{num(ty+3)}V{num(ty-12)}" stroke="{red}" stroke-width="1.6"/>')
    glow = ' filter="url(#glow)"' if k.dark else ""
    out.append(f'<circle{attrs(cx=tx, cy=ty-13, r=2.8)} fill="#ff3b30"{glow}>{anim("opacity", "1;.15;1", 1.4)}</circle>')
    wave = "#7fd4ff" if not k.dark else "#8be9ff"
    for i in range(3):
        arcs = "M7,-6A9,9 0 0 1 7,6M-7,-6A9,9 0 0 0 -7,6"
        out.append(f'<g transform="translate({num(tx)} {num(ty-13)})"><path d="{arcs}" stroke="{wave}" stroke-width="2" fill="none" stroke-linecap="round" opacity="0">'
                   f'<animateTransform attributeName="transform" type="scale" values=".6;3.2" dur="2.7s" begin="{num(-i*.9)}s" repeatCount="indefinite"/>'
                   f'{anim("opacity", "0;1;0", 2.7, -i * .9)}</path></g>')
    # the studio hut in front of the tower
    hx, hy = x + .15, y + .2
    out += box(k, hx, hy, 0, .72, .62, .62, "#eef1f7")
    out += windows(k, "left", hx, hy + .62, .62, .72, .62, 2, door=0, floor_h=.6)
    out += box(k, hx - .04, hy - .04, .62, .8, .7, .08, "#3d4f7a")
    dx, dy = I(hx + .45, hy + .3, .7)
    out.append(f'<path d="M{num(dx-6)},{num(dy-6)}a7,4 -25 0 0 12,2" stroke="{L("#d7dce8")}" stroke-width="3" fill="none"/>')
    return out, (tx, ty - 22), I(hx + .2, hy + .1, .7)


def balloon(k, x, y, H):
    """Smoji: a smiling hot-air balloon tethered over a little launch pad."""
    I, L = k.iso, k.L
    out = frustum(k, x, y, 0, .22, .78, .78, "#d39a62", top="#e9c08f")
    px, py = I(x, y, .22)
    float_y = py - (H + .9) * k.iso.zu
    out.append(f'<ellipse{attrs(cx=px, cy=py, rx=12, ry=6)} fill="#000" opacity=".12">{anim("rx", "12;10;12", 5)}</ellipse>')

    def balloon_at(bx, by, r, color, face, dur, begin, lift):
        anchor_a, anchor_b = (px + (bx - px) * .25 - 4, py + 2), (px + (bx - px) * .25 + 4, py + 2)
        knot = by + r + 9
        ropes = []
        for ax, ay in (anchor_a, anchor_b):
            d0 = f"M{num(ax)},{num(ay)}L{num(bx)},{num(knot)}"
            d1 = f"M{num(ax)},{num(ay)}L{num(bx)},{num(knot-lift)}"
            ropes.append(f'<path d="{d0}" stroke="{L("#8d6e55")}" stroke-width=".9">{anim("d", f"{d0};{d1};{d0}", dur, begin, calcMode="spline", keySplines=".45 0 .55 1;.45 0 .55 1")}</path>')
        g = [f'<g>{sway(f"0 0;0 {-lift};0 0", dur, begin, kind="translate")}']
        g += ball(k, bx, by, r, color)
        g.append(f'<path d="M{num(bx-r*.42)},{num(by-r*.92)}Q{num(bx-r*.6)},{num(by)} {num(bx-r*.32)},{num(by+r*.9)}M{num(bx+r*.42)},{num(by-r*.92)}Q{num(bx+r*.6)},{num(by)} {num(bx+r*.32)},{num(by+r*.9)}" stroke="{L(shade(color, .82))}" stroke-width="1" fill="none"/>')
        g.append(f'<path d="M{num(bx-r*.35)},{num(by+r*.9)}L{num(bx-3)},{num(knot-3)}M{num(bx+r*.35)},{num(by+r*.9)}L{num(bx+3)},{num(knot-3)}" stroke="{L("#8d6e55")}" stroke-width=".8"/>')
        g.append(f'<rect{attrs(x=bx-4, y=knot-4, width=8, height=6, rx=1.5)} fill="{L("#b07a4c")}"/>')
        ink = L("#4a2f17")
        if face == "smile":
            s = r / 21
            for ex in (-7 * s, 7 * s):
                g.append(f'<ellipse{attrs(cx=bx+ex, cy=by-4*s, rx=2.4*s, ry=3.2*s)} fill="{ink}">{anim("ry", f"{num(3.2*s)};{num(3.2*s)};{num(.4*s)};{num(3.2*s)}", 4.6, begin, keyTimes="0;.9;.94;1")}</ellipse>')
            g.append(f'<path d="M{num(bx-8*s)},{num(by+3*s)}Q{num(bx)},{num(by+13*s)} {num(bx+8*s)},{num(by+3*s)}" stroke="{ink}" stroke-width="{num(2.4*s)}" fill="none" stroke-linecap="round"/>')
            for ex in (-12 * s, 12 * s):
                g.append(f'<circle{attrs(cx=bx+ex, cy=by+4*s, r=3*s)} fill="#ff7a8a" opacity=".55"/>')
        elif face == "wink":
            g.append(f'<path d="M{num(bx-5)},{num(by-2)}l2.5,-2 2.5,2M{num(bx+1)},{num(by-2.5)}h4M{num(bx-4)},{num(by+2.5)}q4,3.5 8,0" stroke="{ink}" stroke-width="1.4" fill="none" stroke-linecap="round"/>')
        else:
            for ex in (-3.5, 3.5):
                g.append(f'<path d="M{num(bx+ex)},{num(by)}l-1.6,-1.6a1,1 0 0 1 1.6,-1.2a1,1 0 0 1 1.6,1.2z" fill="#e8364f"/>')
            g.append(f'<path d="M{num(bx-3)},{num(by+3)}q3,2.5 6,0" stroke="{ink}" stroke-width="1.2" fill="none" stroke-linecap="round"/>')
        g.append("</g>")
        return ropes + g

    out += balloon_at(px - 22, float_y + 20, 9, "#ff8fb1", "wink", 4.2, -1.3, 4)
    out += balloon_at(px + 21, float_y + 12, 9.5, "#7fd6ff", "love", 3.8, -2.1, 5)
    out += balloon_at(px, float_y, 21, "#ffd23f", "smile", 5.0, 0, 6)
    return out, (px, float_y - 30), I(x + .55, y + .2, .22)


def studio(k, x, y, H):
    """PicForge: a photo workshop with a giant lens and a busy chimney."""
    I, L = k.iso, k.L
    x0, y0, dx, dy = x - .8, y - .7, 1.6, 1.4
    wall = "#dfe9f3"
    out = []
    cx, cy = x0 + .2, y0 + .2
    out += box(k, cx, cy, H, .32, .32, .75, "#c8644a")
    sx, sy = I(cx + .16, cy + .16, H + .75)
    for i in range(3):
        b = -i * 1.4
        out.append(f'<circle cx="{num(sx)}" cy="{num(sy)}" r="3" fill="{k.L.pick("#ffffff", "#8a93c4")}" opacity="0">'
                   f'{anim("cy", f"{num(sy)};{num(sy-38)}", 4.2, b)}{anim("cx", f"{num(sx)};{num(sx+14)}", 4.2, b)}'
                   f'{anim("r", "3;10", 4.2, b)}{anim("opacity", "0;.85;0", 4.2, b)}</circle>')
    out += box(k, x0, y0, 0, dx, dy, H, wall)
    out.append(poly([I(x0 + .1, y0 + .1, H), I(x0 + dx - .1, y0 + .1, H), I(x0 + dx - .1, y0 + dy - .1, H), I(x0 + .1, y0 + dy - .1, H)], L("#b9c7d6")))
    out += box(k, cx, cy, H, .32, .32, .75, "#c8644a")
    out += windows(k, "right", x0 + dx, y0 + dy, H, dy, H, 2)
    # the lens, drawn in the wall's own plane
    lc, lt, r = dx * .56, H * .5, min(.46, H * .3)
    g = [f'<g transform="{k.iso.face("left", x0, y0 + dy, H)}">']
    g.append(f'<rect{attrs(x=.12, y=H-.5, width=.3, height=.5)} fill="{"#ffb347" if k.dark else L("#6b4a3a")}"/>')
    g.append(f'<ellipse{attrs(cx=lc, cy=lt, rx=r*1.12, ry=r*1.12*.92)} fill="{L("#2b2e3b")}"/>')
    g.append(f'<ellipse{attrs(cx=lc, cy=lt, rx=r*.86, ry=r*.86*.92)} fill="{L("#4a5a8a")}"/>')
    g.append(f'<ellipse{attrs(cx=lc, cy=lt, rx=r*.6, ry=r*.6*.92)} fill="{"#7dd3fc" if k.dark else "#3d7fe0"}"/>')
    g.append(f'<ellipse{attrs(cx=lc, cy=lt, rx=r*.3, ry=r*.3*.92)} fill="{L("#13204a")}"/>')
    g.append(f'<ellipse{attrs(cx=lc-r*.25, cy=lt-r*.28, rx=r*.16, ry=r*.12)} fill="#fff" opacity=".8"/>')
    g.append(f'<ellipse{attrs(cx=lc, cy=lt, rx=r*1.12, ry=r*1.12*.92)} fill="#fff" opacity="0">{anim("opacity", "0;0;.95;0", 5.5, -1, keyTimes="0;.88;.9;1")}</ellipse>')
    g.append(f'<rect{attrs(x=dx-.42, y=.16, width=.22, height=.14, rx=.03)} fill="#ff5c5c">{anim("opacity", "1;.2;1", 1.2)}</rect>')
    g.append("</g>")
    out += g
    return out, I(x, y, H + .2), I(x + .5, y + .4, H)


def post(k, x, y, H):
    """sani: the post office, where short links fly off as paper planes."""
    I = k.iso
    x0, y0, dx, dy = x - .75, y - .7, 1.5, 1.4
    wall = "#fff4e2"
    out = box(k, x0, y0, 0, dx, dy, H, wall)
    out += windows(k, "left", x0, y0 + dy, H, dx, H, 3, door=1)
    out += windows(k, "right", x0 + dx, y0 + dy, H, dy, H, 2)
    out += pyramid(k, x0, y0, H, dx, dy, .8, "#3f7fd9")
    # a blue mailbox by the door
    mx, my = x + .85, y + .55
    out += box(k, mx - .14, my - .12, 0, .28, .24, .38, "#e5483f")
    ax, ay = I(x, y, H + .8)
    for i in range(2):
        b = -i * 3
        d = "M0,0 C30,-30 70,-20 110,-60"
        plane = '<path d="M5,0L-6,-4.5L-3,0L-6,4.5Z" fill="#ffffff"/><path d="M5,0L-3,0" stroke="#9fb3c8" stroke-width=".7"/>'
        out.append(f'<g transform="translate({num(ax)} {num(ay-4)})"><g opacity="0">{plane}{move(d, 6, b, rotate="auto")}{anim("opacity", "0;1;1;0", 6, b, keyTimes="0;.08;.6;.8")}</g></g>')
    return out, (ax, ay - 6), I(x + .45, y + .1, H + .35)


def lighthouse(k, x, y, H):
    """romi: a lighthouse keeping watch, its heartbeat lamp always blinking."""
    I, L = k.iso, k.L
    cx, cy, T = x - .25, y - .25, H + 1.0
    out = []
    bands = 5
    for i in range(bands):
        z0, z1 = T * i / bands, T * (i + 1) / bands
        r0, r1 = .55 - .17 * z0 / T, .55 - .17 * z1 / T
        out += frustum(k, cx, cy, z0, z1, r0, r1, "#e5483f" if i % 2 == 0 else "#f6f1e8", top=False)
    out += frustum(k, cx, cy, T, T + .09, .52, .52, "#3a3f52")
    out += frustum(k, cx, cy, T + .09, T + .55, .27, .27, "#fff2b3" if k.dark else "#d8f0ff", top=False)
    for a in (-.7, 0, .7):
        sx0, sy0 = I(cx, cy, T + .09)
        rx, _ = k.iso.radii(.27)
        out.append(f'<path d="M{num(sx0 + a*rx)},{num(sy0+2)}V{num(sy0 - .46*k.iso.zu + 2)}" stroke="{L("#3a3f52")}" stroke-width="1"/>')
    out += cone(k, cx, cy, T + .55, T + .95, .34, "#c23b33")
    lx, ly = I(cx, cy, T + .32)
    alpha = .55 if k.dark else .28
    beam_id = k.uid("beam")
    k.defs.append(f'<linearGradient id="{beam_id}"><stop offset="0" stop-color="#fff6b0" stop-opacity="{alpha}"/><stop offset="1" stop-color="#fff6b0" stop-opacity="0"/></linearGradient>')
    beam = f'<path d="M0,-3L170,-26L170,18L0,3Z" fill="url(#{beam_id})"/>'
    out.append(f'<g transform="translate({num(lx)} {num(ly)})"><g>{beam}<g transform="scale(-1 1)">{beam}</g>'
               f'<animateTransform attributeName="transform" type="scale" values="1 1;0 1;-1 1;0 1;1 1" dur="7s" repeatCount="indefinite"/></g></g>')
    if k.dark:
        out.append(f'<circle{attrs(cx=lx, cy=ly, r=9)} fill="#fff3a0" opacity=".55" filter="url(#glow)"/>')
    # keeper's cottage with the status light
    hx, hy = x + .2, y + .15
    out += box(k, hx, hy, 0, .66, .66, .55, "#f1ede4")
    out += windows(k, "left", hx, hy + .66, .55, .66, .55, 2, door=0, floor_h=.55)
    out += gable(k, hx, hy, .55, .66, .66, .35, "#4b5d8c", "#f1ede4", axis="y")
    gx, gy = I(hx + .66, hy + .35, .4)
    out.append(f'<circle{attrs(cx=gx+2, cy=gy, r=2.4)} fill="#34d399">{anim("opacity", "1;1;.15;1;.15;1", 2.2, keyTimes="0;.6;.68;.76;.84;1")}</circle>')
    tx, ty = I(cx, cy, T + .95)
    return out, (tx, ty - 4), I(hx + .33, hy + .33, .9)


def press(k, x, y, H):
    """webfont-slice: a type foundry whose billboard cycles through scripts."""
    I, L = k.iso, k.L
    x0, y0, dx, dy = x - .7, y - .7, 1.4, 1.4
    wall = "#ebe6fa"
    out = box(k, x0, y0, 0, dx, dy, H, wall)
    out += windows(k, "left", x0, y0 + dy, H, dx, H, 3, door=1)
    out += windows(k, "right", x0 + dx, y0 + dy, H, dy, H, 2)
    out += box(k, x0 + .1, y0 + .1, H, dx - .2, dy - .2, .1, "#9a8fc7")
    bz, by = H + .1, y + .1
    for px in (x0 + .25, x0 + dx - .25):
        a, b = I(px, by, bz), I(px, by, bz + .4)
        out.append(f'<path d="M{pts([a, b])}" stroke="{L("#55507a")}" stroke-width="2"/>')
    g = [f'<g transform="{k.iso.face("left", x0 + .05, by, bz + 1.35)}">',
         f'<rect x="0" y="0" width="{num(dx-.1)}" height=".98" fill="{k.L.pick("#ffffff", "#141938")}"/>',
         f'<rect x="0" y=".9" width="{num(dx-.1)}" height=".08" fill="{L("#6c5ce7")}"/>']
    glyphs = [("字", "#6c5ce7"), ("Aa", "#e5483f"), ("あ", "#0ea5e9"), ("한", "#10b981")]
    n = len(glyphs)
    for i, (glyph, color) in enumerate(glyphs):
        values = ";".join("1" if j == i else "0" for j in range(n)) + (";1" if i == 0 else ";0")
        g.append(f'<text x="{num((dx-.1)/2)}" y=".72" class="t-glyph" font-size=".7" text-anchor="middle" fill="{color}" opacity="{1 if i == 0 else 0}">{esc(glyph)}'
                 f'{anim("opacity", values, 8, 0, calcMode="discrete", keyTimes=";".join(num(j / n) for j in range(n)) + ";1")}</text>')
    g.append("</g>")
    out += g
    return out, I(x0 + dx / 2, by, bz + 1.45), I(x + .5, y + .5, H + .1)


def bucket(k, x, y, H):
    """Pail: a water tower that is quite literally an S3 bucket."""
    I, L = k.iso, k.L
    steel = L("#6f7d92")
    lz = H
    out = [f'<path d="M{pts([I(x + lx * .5, y + ly * .5, 0), I(x + lx * .38, y + ly * .38, lz)])}" stroke="{steel}" stroke-width="2.2"/>'
           for lx, ly in ((-1, -1), (1, -1), (-1, 1), (1, 1))]
    a, c = I(x - .5, y + .5, 0), I(x + .5, y + .5, 0)
    out.append(f'<path d="M{pts([a, I(x + .44, y + .44, lz * .55)])}M{pts([c, I(x - .44, y + .44, lz * .55)])}" stroke="{steel}" stroke-width="1" opacity=".8"/>')
    out += frustum(k, x, y, lz, lz + .12, .44, .44, "#59657a")
    z0, z1 = lz + .12, lz + 1.12
    out += frustum(k, x, y, z0, z1, .56, .78, "#9cc3dc", top=False)
    for f in (.3, .7):
        zz, rr = z0 + (z1 - z0) * f, .56 + .22 * f
        bx, by = I(x, y, zz)
        rx, ry = k.iso.radii(rr)
        out.append(f'<path d="M{num(bx-rx)},{num(by)}A{num(rx)},{num(ry)} 0 0 0 {num(bx+rx)},{num(by)}" stroke="{L("#6f93ad")}" stroke-width="1.6" fill="none"/>')
    tx, ty = I(x, y, z1)
    rx, ry = k.iso.radii(.78)
    out.append(f'<ellipse{attrs(cx=tx, cy=ty, rx=rx, ry=ry)} fill="{L("#5f86a3")}"/>')
    out.append(f'<ellipse{attrs(cx=tx, cy=ty+1.5, rx=rx-3, ry=ry-2)} fill="{L("#3d9bf0")}"/>')
    out.append(f'<ellipse{attrs(cx=tx-6, cy=ty, rx=6, ry=1.6)} fill="#fff" opacity=".6">{anim("cx", f"{num(tx-8)};{num(tx+6)};{num(tx-8)}", 4)}</ellipse>')
    out.append(f'<path d="M{num(tx-rx)},{num(ty)}C{num(tx-rx)},{num(ty-44)} {num(tx+rx)},{num(ty-44)} {num(tx+rx)},{num(ty)}" stroke="{L("#4d5466")}" stroke-width="2.2" fill="none"/>')
    mx, my = I(x, y, (z0 + z1) / 2)
    out.append(f'<text x="{num(mx)}" y="{num(my+5)}" class="t-tag" text-anchor="middle" fill="{L("#2e4a66")}">S3</text>')
    dx, dy = I(x + .3, y + .3, lz)
    ground = I(x + .3, y + .3, 0)[1]
    out.append(f'<path d="M0,-4q3,4 0,6q-3,-2 0,-6z" fill="#5ab8ff" opacity="0" transform="translate({num(dx)} 0)">'
               f'<animateTransform attributeName="transform" type="translate" values="{num(dx)} {num(dy)};{num(dx)} {num(ground)}" dur="2.6s" repeatCount="indefinite" calcMode="spline" keySplines=".5 0 1 1"/>'
               f'{anim("opacity", "0;1;1;0", 2.6, keyTimes="0;.1;.9;1")}</path>')
    return out, (tx, ty - 38), I(x - .5, y - .5, lz + .3)


def clocktower(k, x, y, H=2.9):
    """The town hall in the middle stands for this profile itself."""
    I, L = k.iso, k.L
    out = box(k, x - .7, y - .7, 0, 1.4, 1.4, .7, "#efe3cc")
    out += windows(k, "left", x - .7, y + .7, .7, 1.4, .7, 3, door=1, floor_h=.7)
    out += windows(k, "right", x + .7, y + .7, .7, 1.4, .7, 3, floor_h=.7)
    out += box(k, x - .7, y - .7, .7, 1.4, 1.4, .06, "#b9a27b")
    out += box(k, x - .38, y - .38, .76, .76, .76, H - .76, "#f6ecd8")
    for side, (fx, fy) in (("left", (x - .38, y + .38)), ("right", (x + .38, y + .38))):
        g = [f'<g transform="{k.iso.face(side, fx, fy, H)}">']
        c, t = .38, .42
        g.append(f'<ellipse{attrs(cx=c, cy=t, rx=.3, ry=.28)} fill="{L("#c9a45c")}"/>')
        g.append(f'<ellipse{attrs(cx=c, cy=t, rx=.25, ry=.23)} fill="{"#fff1c1" if k.dark else "#ffffff"}"/>')
        ink = L("#2c2f3e")
        g.append(f'<path d="M{num(c)},{num(t)}V{num(t-.19)}" stroke="{ink}" stroke-width="1.4" vector-effect="non-scaling-stroke" stroke-linecap="round">{spin(10, c, t)}</path>')
        g.append(f'<path d="M{num(c)},{num(t)}V{num(t-.12)}" stroke="{ink}" stroke-width="2" vector-effect="non-scaling-stroke" stroke-linecap="round">{spin(120, c, t)}</path>')
        g.append("</g>")
        out += g
        out += windows(k, side, fx, fy, H - .62, .76, H - 1.5, 1, floor_h=.62)
    out += pyramid(k, x - .38, y - .38, H, .76, .76, 1.0, "#6b5bd6")
    ax, ay = I(x, y, H + 1.0)
    out.append(f'<circle{attrs(cx=ax, cy=ay-2, r=2.6)} fill="#ffd23f"/>')
    return out, (ax, ay - 8), (ax, ay - 4)


BUILDERS = {"house": house, "cafe": cafe, "radio": radio, "balloon": balloon, "studio": studio,
            "post": post, "lighthouse": lighthouse, "press": press, "bucket": bucket}


# --- the island ----------------------------------------------------------------------

def superellipse(S, n, steps=180, wobble=0.0, phase=0.0):
    out = []
    for i in range(steps):
        t = math.tau * i / steps
        c, s = math.cos(t), math.sin(t)
        f = 1 + wobble * (.5 * math.sin(3 * t + phase) + .3 * math.sin(5 * t + 1.7 + phase) + .2 * math.sin(9 * t + .4))
        out.append((S * f * math.copysign(abs(c) ** (2 / n), c), S * f * math.copysign(abs(s) ** (2 / n), s)))
    return out


ISLAND = superellipse(5.9, 3.0, wobble=.035, phase=.8)
RING = superellipse(4.72, 4.2, steps=240)
PLOTS = [(-2.6, -2.6), (0, -2.6), (-2.6, 0), (2.6, -2.6), (-2.6, 2.6), (2.6, 0), (0, 2.6), (2.6, 2.6)]
INNER_TREES = [(1.3, 1.3, "round"), (-1.3, 1.35, "pine"), (1.35, -1.3, "pine"), (-1.3, -1.3, "round")]
OUTER_TREES = [(-5.3, -1.1, "pine"), (-1.0, -5.35, "round"), (-4.95, 1.9, "round"), (1.9, -5.0, "pine"),
               (-3.95, -3.95, "round"), (-5.25, .4, "round"), (.5, -5.4, "pine")]
THICK = .75


def tram_route(iso):
    """Screen route starting at the far left, running the back half first.

    Returns (path, length, back_fraction). The tram is drawn twice, behind and in
    front of the buildings, and each copy is only visible on its half of the loop.
    """
    screen = [iso(x, y) for x, y in RING]
    n = len(screen)
    left = min(range(n), key=lambda i: screen[i][0])
    screen = screen[left:] + screen[:left]
    right = max(range(n), key=lambda i: screen[i][0])
    if screen[right // 2][1] > screen[0][1]:
        screen = [screen[0]] + screen[1:][::-1]
        right = max(range(n), key=lambda i: screen[i][0])
    lengths = [0.0]
    for a, b in zip(screen, screen[1:] + screen[:1]):
        lengths.append(lengths[-1] + math.dist(a, b))
    return "M" + pts(screen) + "Z", lengths[-1], lengths[right] / lengths[-1]


def tram_car(k, lead):
    L = k.L
    body = L("#ff6b6b") if lead else L("#ffa94d")
    win = "#ffe08a" if k.dark else "#e8f6ff"
    out = [f'<rect x="-10" y="-15" width="20" height="13" rx="4" fill="{body}"/>',
           f'<rect x="-10" y="-6" width="20" height="2.2" fill="{L("#fff4e0")}"/>',
           f'<rect x="-8" y="-12.5" width="16" height="5" rx="1.5" fill="{win}"/>',
           f'<path d="M-3,-12.5v5M3,-12.5v5" stroke="{body}" stroke-width="1"/>',
           f'<rect x="-6" y="-17" width="12" height="2.4" rx="1" fill="{L("#3a3f52")}"/>',
           f'<circle cx="-5.5" cy="-1.6" r="1.8" fill="{L("#3a3f52")}"/><circle cx="5.5" cy="-1.6" r="1.8" fill="{L("#3a3f52")}"/>']
    if k.dark and lead:
        out.append('<circle cx="0" cy="-5" r="3" fill="#fff6c2" opacity=".7" filter="url(#glow)"/>')
    return "".join(out)


def tram(k, layer, dur=30.0):
    route, length, back = tram_route(k.iso)
    out = []
    for i in range(3):
        begin = -i * 23 / length * dur
        values, times = ("1;0", f"0;{back:.4f}") if layer == "back" else ("0;1", f"0;{back:.4f}")
        out.append(f'<g opacity="{values[0]}">{tram_car(k, i == 2)}{move(route, dur, begin)}'
                   f'{anim("opacity", values, dur, begin, calcMode="discrete", keyTimes=times)}</g>')
    return out


def island(k, buildings, hall=True):
    """The whole floating island. `buildings` holds (plot index, builder, height, flag colour, name, dot)."""
    I, L = k.iso, k.L
    top = [I(x, y) for x, y in ISLAND]
    bottom = [(sx, sy + THICK * I.zu) for sx, sy in top]
    out, labels = [], []
    left_i = min(range(len(top)), key=lambda i: top[i][0])
    right_i = max(range(len(top)), key=lambda i: top[i][0])
    # front chain of the bottom rim, left to right
    chain, i = [], left_i
    step = 1 if bottom[(left_i + 1) % len(bottom)][1] > bottom[(left_i - 1) % len(bottom)][1] else -1
    while True:
        chain.append(bottom[i])
        if i == right_i:
            break
        i = (i + step) % len(bottom)
    # rocky underside: an inverted, terraced mountain tapering to a point
    cx = I.ox
    rim_y = max(p[1] for p in chain)
    depth = 5.2 * I.zu
    tip = (cx + I.u * .5, rim_y + depth)
    rock_id, earth_id, shadow_id = k.uid("rock"), k.uid("earth"), k.uid("shade")
    k.defs.append(f'<linearGradient id="{rock_id}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{L("#a5826a")}"/><stop offset=".55" stop-color="{L("#86685c")}"/><stop offset="1" stop-color="{L("#5a4752")}"/></linearGradient>')
    k.defs.append(f'<linearGradient id="{earth_id}" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{L("#cf9a63")}"/><stop offset=".5" stop-color="{L("#b47b4f")}"/><stop offset="1" stop-color="{L("#8a5a3b")}"/></linearGradient>')
    k.defs.append(f'<linearGradient id="{shadow_id}" x1="0" y1="0" x2="1" y2="0"><stop offset=".35" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".28"/></linearGradient>')

    def flank(a, sign, n=11):
        seg = []
        for j in range(1, n):
            t = j / n
            x = a[0] + (tip[0] - a[0]) * math.sin(t * math.pi / 2) ** .9
            y = a[1] - 6 + (tip[1] - a[1] + 6) * t ** 1.25
            seg.append((x + sign * k.r(0, 8) * (1 - t * .6), y + k.r(-3, 3)))
        return seg

    left_flank, right_flank = flank(chain[0], -1), flank(chain[-1], 1)
    shape = chain + right_flank + [tip] + left_flank[::-1]
    out.append(poly(shape, f"url(#{rock_id})"))
    out.append(poly(shape, f"url(#{shadow_id})"))

    def width_at(f):
        j = min(len(left_flank) - 1, int(f * len(left_flank)))
        return left_flank[j], right_flank[j]

    for f in (.18, .42, .66):
        (lx_, ly_), (rx_, ry_) = width_at(f)
        out.append(f'<path d="M{num(lx_+3)},{num(ly_)}Q{num((lx_+rx_)/2)},{num((ly_+ry_)/2 + 22 * (1 - f))} {num(rx_-3)},{num(ry_)}" stroke="{L("#5d4645")}" stroke-width="1.3" fill="none" opacity=".45"/>')
    # glowing crystals in the rock
    for f, u, h, c in ((.2, .2, 17, "#8b5cf6"), (.24, .28, 11, "#22d3ee"), (.32, .7, 14, "#22d3ee"), (.28, .78, 9, "#a78bfa"), (.55, .45, 13, "#8b5cf6"), (.5, .56, 8, "#f472b6")):
        (lx_, ly_), (rx_, ry_) = width_at(f)
        px, py = lx_ + (rx_ - lx_) * u, ly_ + (ry_ - ly_) * u + 14
        col = c if k.dark else mix(c, "#ffffff", .2)
        glow = ' filter="url(#glow)"' if k.dark else ""
        out.append(f'<path d="M{num(px)},{num(py)}l-4,{num(-h*.45)} 4,{num(-h*.55)} 4,{num(h*.55)}z" fill="{col}"{glow}>{anim("opacity", "1;.5;1", k.r(2.5, 4.5), -k.r(0, 3))}</path>')
        out.append(f'<path d="M{num(px)},{num(py)}l4,{num(-h*.45)} 0,{num(-h*.55)}z" fill="#fff" opacity=".3"/>')
    # hanging roots
    for j in range(7):
        p = chain[int(len(chain) * (j + .5) / 7)]
        length = k.r(14, 30)
        out.append(f'<path d="M{num(p[0])},{num(p[1]-2)}q{num(k.r(-6, 6))},{num(length*.5)} {num(k.r(-4, 4))},{num(length)}" stroke="{L("#6b4a35")}" stroke-width="1.3" fill="none" opacity=".8"/>')
    # earth skirt
    for a, b, c, d in zip(top, top[1:] + top[:1], bottom[1:] + bottom[:1], bottom):
        out.append(poly([a, b, c, d], f"url(#{earth_id})"))
    out.append(poly(chain, f"url(#{earth_id})"))
    grass_lip = [(sx, sy + 5) for sx, sy in top]
    for a, b, c, d in zip(top, top[1:] + top[:1], grass_lip[1:] + grass_lip[:1], grass_lip):
        out.append(poly([a, b, c, d], L("#5fae4f")))
    # strata line
    mid = [(sx, sy + THICK * I.zu * .62) for sx, sy in chain]
    out.append(f'<path d="M{pts(mid)}" stroke="{L("#7a4f33")}" stroke-width="1" fill="none" opacity=".35"/>')
    # grass top
    grass_id = k.uid("grass")
    k.defs.append(f'<radialGradient id="{grass_id}" cx=".45" cy=".4" r=".7"><stop offset="0" stop-color="{L("#a6e07a")}"/><stop offset="1" stop-color="{L("#7cc35f")}"/></radialGradient>')
    out.append(poly(top, f"url(#{grass_id})"))
    # paths and plaza
    sand = L("#ecd9a8")
    out.append(poly([I(-4.4, -.28), I(4.4, -.28), I(4.4, .28), I(-4.4, .28)], sand))
    out.append(poly([I(-.28, -4.4), I(.28, -4.4), I(.28, 4.4), I(-.28, 4.4)], sand))
    pxr, pyr = I.radii(1.15)
    out.append(f'<ellipse{attrs(cx=I.ox, cy=I.oy, rx=pxr, ry=pyr)} fill="{L("#e3cf9b")}"/>')
    out.append(f'<ellipse{attrs(cx=I.ox, cy=I.oy, rx=pxr*.8, ry=pyr*.8)} fill="none" stroke="{L("#d1b97f")}" stroke-dasharray="3 4"/>')
    # ring road with rails and sleepers
    outer = superellipse(4.72 + .34, 4.2, steps=240)
    inner = superellipse(4.72 - .34, 4.2, steps=240)
    out.append(f'<path d="M{pts([I(x, y) for x, y in outer])}ZM{pts([I(x, y) for x, y in inner])}Z" fill="{L("#cdbb9c")}" fill-rule="evenodd"/>')
    centre = [I(x, y) for x, y in RING]
    out.append(f'<path d="M{pts(centre)}Z" stroke="{L("#8a6f55")}" stroke-width="6" stroke-dasharray="1.6 4.2" fill="none"/>')
    for off in (-.13, .13):
        rail = superellipse(4.72 + off, 4.2, steps=240)
        out.append(f'<path d="M{pts([I(x, y) for x, y in rail])}Z" stroke="{L("#6f6a73")}" stroke-width="1.1" fill="none"/>')
    # pond and waterfall on the front-left edge
    pond = (1.0, 4.95)
    ppx, ppy = I(*pond)
    prx, pry = I.radii(.55)
    edge = max(top, key=lambda p: p[1] - (p[0] - ppx) ** 2 * .02 if abs(p[0] - ppx) < 30 else -1e9)
    water = "#4fb3ff" if not k.dark else "#3b82f6"
    out.append(f'<ellipse{attrs(cx=ppx, cy=ppy, rx=prx+3, ry=pry+2)} fill="{L("#d9c48f")}"/>')
    out.append(f'<ellipse{attrs(cx=ppx, cy=ppy, rx=prx, ry=pry)} fill="{water}"/>')
    out.append(poly([(ppx - 4, ppy + 3), (ppx + 4, ppy + 3), (edge[0] + 5, edge[1] + 1), (edge[0] - 5, edge[1] + 1)], water))
    fall_id = k.uid("fall")
    k.defs.append(f'<linearGradient id="{fall_id}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{water}"/><stop offset=".75" stop-color="{water}" stop-opacity=".5"/><stop offset="1" stop-color="{water}" stop-opacity="0"/></linearGradient>')
    fx, fy = edge
    fall = depth * 1.05
    out.append(f'<rect{attrs(x=fx-5, y=fy, width=10, height=fall)} fill="url(#{fall_id})"/>')
    for j, ox in enumerate((-2.5, 0, 2.5)):
        out.append(f'<path d="M{num(fx+ox)},{num(fy)}v{num(fall*.8)}" stroke="#ffffff" stroke-width="1.1" stroke-dasharray="9 12" opacity=".7">{anim("stroke-dashoffset", "0;-42", .9 + j * .15)}</path>')
    out.append(f'<ellipse{attrs(cx=fx, cy=fy+2, rx=7, ry=2.5)} fill="#ffffff" opacity=".6"/>')
    # grass tufts and flowers
    blocked = [(px, py, 1.15) for px, py in PLOTS] + [(0, 0, 1.3)]
    for j in range(70):
        gx, gy = k.r(-5.4, 5.4), k.r(-5.4, 5.4)
        if (abs(gx / 5.6) ** 3 + abs(gy / 5.6) ** 3) > .92:
            continue
        ring_r = (abs(gx / 4.72) ** 4.2 + abs(gy / 4.72) ** 4.2) ** (1 / 4.2)
        if abs(ring_r - 1) < .1 or abs(gx) < .4 or abs(gy) < .4 or any(abs(gx - bx) < r and abs(gy - by) < r for bx, by, r in blocked):
            continue
        sx, sy = I(gx, gy)
        if j % 4 == 0:
            color = ("#ff6b9a", "#ffd23f", "#ffffff", "#b388ff")[j % 3 + (j // 7) % 2]
            out.append(f'<circle{attrs(cx=sx, cy=sy, r=1.8)} fill="{L(color)}"/>')
        else:
            out.append(f'<path d="M{num(sx-2.5)},{num(sy)}l1,-3.5M{num(sx)},{num(sy)}v-4.5M{num(sx+2.5)},{num(sy)}l-1,-3.5" stroke="{L("#4f9a45")}" stroke-width="1"/>')
    # back scenery, the tram behind, the town, the tram in front
    for tx_, ty_, kind in sorted(OUTER_TREES, key=lambda t: t[0] + t[1]):
        out += tree(k, tx_, ty_, .95, kind)
    out += tram(k, "back")
    objects = []
    if hall:
        objects.append((0.0, clocktower(k, 0, 0), None))
    for tx_, ty_, kind in INNER_TREES:
        objects.append((tx_ + ty_, (tree(k, tx_, ty_, .85, kind), None, None), None))
    used = set()
    for plot, builder, height, flag_color, name, dot in buildings:
        bx, by = PLOTS[plot]
        used.add(plot)
        objects.append((bx + by, builder(k, bx, by, height), (flag_color, name, dot)))
    for plot, (bx, by) in enumerate(PLOTS):
        if plot not in used:
            objects.append((bx + by, (tree(k, bx - .3, by + .2, 1.0, "round") + tree(k, bx + .35, by - .25, .9, "pine"), None, None), None))
    pending = []
    for depth, (parts, anchor, flag_at), meta in sorted(objects, key=lambda o: o[0]):
        out += parts
        if meta and flag_at and meta[0]:
            out += flag(k, flag_at[0], flag_at[1], meta[0], begin=-k.r(0, 1.6))
        if meta and anchor:
            pending.append((anchor[0], anchor[1] - 6, meta[1], meta[2]))
    out += tram(k, "front")
    for x, y, ly, name, dot in place_labels(pending):
        if ly < y - 1:
            out_line = k.L.pick("#1f234055", "#ffffff40")
            labels.append(f'<path d="M{num(x)},{num(y)}V{num(ly)}" stroke="{out_line}" stroke-dasharray="2 2"/>')
        labels += label(k, x, ly, name, dot)
    return out, labels, tip


def place_labels(pending, height=20, gap=4):
    """Greedy de-overlap: lift a label until its pill clears every placed one."""
    placed, result = [], []
    for x, y, name, dot in sorted(pending, key=lambda p: -p[1]):
        w = len(name) * 6.4 + 22
        ly = y
        while any(abs(x - px) < (w + pw) / 2 + gap and abs(ly - py) < height + gap - 2 for px, py, pw in placed):
            ly -= 4
        placed.append((x, ly, w))
        result.append((x, y, ly, name, dot))
    return result


# --- sky -----------------------------------------------------------------------------

def sky_defs(k, w, h, rx=18):
    sky = k.uid("sky")
    stops = k.L.pick(("#79c3ff", "#bfe6ff", "#fff1d6"), ("#060a22", "#141a48", "#3a2766"))
    k.defs.append(f'<linearGradient id="{sky}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{stops[0]}"/><stop offset=".62" stop-color="{stops[1]}"/><stop offset="1" stop-color="{stops[2]}"/></linearGradient>')
    clip = k.uid("frame")
    k.defs.append(f'<clipPath id="{clip}"><rect width="{w}" height="{h}" rx="{rx}"/></clipPath>')
    return sky, clip


def sun_or_moon(k, sx, sy):
    if not k.dark:
        rays = "".join(f'<path d="M{num(sx + math.cos(a)*44)},{num(sy + math.sin(a)*44)}L{num(sx + math.cos(a)*56)},{num(sy + math.sin(a)*56)}" stroke="#ffd54f" stroke-width="3" stroke-linecap="round"/>'
                       for a in (i * math.tau / 12 for i in range(12)))
        return [f'<circle{attrs(cx=sx, cy=sy, r=58)} fill="#fff3b0" opacity=".35"/>',
                f'<g>{rays}{spin(80, sx, sy)}</g>',
                f'<circle{attrs(cx=sx, cy=sy, r=34)} fill="#ffd54f"/>',
                f'<circle{attrs(cx=sx-9, cy=sy-10, r=10)} fill="#fff8d6" opacity=".6"/>']
    mask = k.uid("moon")
    k.defs.append(f'<mask id="{mask}"><rect x="{num(sx-40)}" y="{num(sy-40)}" width="80" height="80" fill="#fff"/><circle cx="{num(sx+13)}" cy="{num(sy-9)}" r="25" fill="#000"/></mask>')
    return [f'<circle{attrs(cx=sx, cy=sy, r=52)} fill="#fff3c4" opacity=".08"/>',
            f'<circle{attrs(cx=sx, cy=sy, r=30)} fill="#fff6d5" mask="url(#{mask})" filter="url(#glow)"/>']


def stars(k, count, w, h, avoid=None):
    out = []
    for i in range(count):
        x, y = k.r(6, w - 6), k.r(6, h * .92) ** 1.0
        y = 6 + (h * .9) * (k.r() ** 1.35)
        r = k.r(.45, 1.35)
        o = k.r(.35, 1)
        if k.r() < .13:
            out.append(f'<circle{attrs(cx=x, cy=y, r=r+.2)} fill="#fff">{anim("opacity", f"{num(o)};.1;{num(o)}", k.r(2, 5), -k.r(0, 5))}</circle>')
        else:
            out.append(f'<circle{attrs(cx=x, cy=y, r=r)} fill="#fff" opacity="{num(o)}"/>')
    for i in range(min(6, count)):
        x, y, s = k.r(20, w - 20), k.r(15, h * .5), k.r(3, 5.5)
        out.append(f'<path d="M{num(x)},{num(y-s)}Q{num(x)},{num(y)} {num(x+s)},{num(y)}Q{num(x)},{num(y)} {num(x)},{num(y+s)}Q{num(x)},{num(y)} {num(x-s)},{num(y)}Q{num(x)},{num(y)} {num(x)},{num(y-s)}Z" fill="#fff8d6">{anim("opacity", "1;.25;1", k.r(2.5, 4.5), -k.r(0, 4))}</path>')
    return out


def shooting_star(k, x, y, begin=2.0):
    sid = k.uid("streak")
    k.defs.append(f'<linearGradient id="{sid}"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset="1" stop-color="#fff"/></linearGradient>')
    return [f'<g transform="translate({num(x)} {num(y)}) rotate(28)"><g opacity="0"><rect x="-70" y="-1" width="70" height="2" rx="1" fill="url(#{sid})"/><circle r="1.8" fill="#fff"/>'
            f'<animateTransform attributeName="transform" type="translate" values="0 0;0 0;220 0;220 0" keyTimes="0;.7;.8;1" dur="9s" begin="{num(begin)}s" repeatCount="indefinite"/>'
            f'{anim("opacity", "0;0;1;0;0", 9, begin, keyTimes="0;.7;.74;.8;1")}</g></g>']


def cloud(k, x, y, s, w, dur, phase, opacity=1.0):
    color = k.L.pick("#ffffff", "#2d3570")
    shadow = k.L.pick("#e3f1fb", "#262d62")
    parts = (f'<ellipse cx="0" cy="6" rx="{num(30*s)}" ry="{num(9*s)}" fill="{shadow}"/>'
             f'<circle cx="{num(-14*s)}" cy="0" r="{num(13*s)}" fill="{color}"/><circle cx="{num(4*s)}" cy="{num(-8*s)}" r="{num(17*s)}" fill="{color}"/>'
             f'<circle cx="{num(20*s)}" cy="{num(1*s)}" r="{num(11*s)}" fill="{color}"/><rect x="{num(-28*s)}" y="0" width="{num(56*s)}" height="{num(9*s)}" rx="{num(4.5*s)}" fill="{color}"/>')
    span = w + 160
    return [f'<g opacity="{num(opacity)}"><g>{parts}<animateTransform attributeName="transform" type="translate" from="{num(-80)} {num(y)}" to="{num(span-80)} {num(y)}" dur="{num(dur)}s" begin="{num(-phase*dur)}s" repeatCount="indefinite"/></g></g>']


def birds(k, x0, x1, y, begin=0.0, dur=30.0):
    out = []
    for i, (dx, dy) in enumerate(((0, 0), (-16, 8), (-30, -3))):
        a = f"M{dx-6},{dy}Q{dx-3},{dy-4} {dx},{dy}Q{dx+3},{dy-4} {dx+6},{dy}"
        b = f"M{dx-6},{dy-3}Q{dx-3},{dy+2} {dx},{dy}Q{dx+3},{dy+2} {dx+6},{dy-3}"
        out.append(f'<path d="{a}" stroke="#3b4a6b" stroke-width="1.5" fill="none" stroke-linecap="round">{anim("d", f"{a};{b};{a}", .7 + i * .08)}</path>')
    mid = (x0 + x1) / 2
    return [f'<g><g opacity="0">{"".join(out)}<animateTransform attributeName="transform" type="translate" values="{num(x0)} {num(y)};{num(mid)} {num(y-22)};{num(x1)} {num(y)}" dur="{num(dur)}s" begin="{num(begin)}s" repeatCount="indefinite"/>'
            f'{anim("opacity", "0;1;1;0", dur, begin, keyTimes="0;.08;.9;1")}</g></g>']


def pebble(k, sx, sy, s, i, plant=False):
    """A small floating rock with a grassy top."""
    from iso import Iso
    k2 = Kit(Iso(sx, sy, 10 * s, 11 * s), k.L, seed=40 + i)
    top = [k2.iso(x, y) for x, y in ((-1, -.8), (.9, -1), (1.1, .9), (-.8, 1.1))]
    under = (sx + 2 * s, sy + 34 * s)
    out = [poly([top[1], top[2], top[3], (top[3][0] + 2, top[3][1] + 8 * s), under, (top[1][0] - 1, top[1][1] + 9 * s)], k.L("#8c6c5c")),
           poly([top[2], top[3], (top[3][0] + 2, top[3][1] + 8 * s), under], k.L("#a5826a")),
           poly(top, k.L("#8fd16a"))]
    if plant:
        k2.iso.oy -= 1
        out += tree(k2, 0, 0, .55 * s, "pine")
    return [f'<g>{"".join(out)}{sway(f"0 0;0 {num(-3-i*1.5)};0 0", 4 + i * .9, -i, kind="translate")}</g>']


def fireflies(k, cx, cy, spread_x, spread_y, n=12):
    out = []
    for i in range(n):
        x, y = cx + k.r(-spread_x, spread_x), cy + k.r(-spread_y, spread_y)
        r = k.r(10, 26)
        d = f"M0,0c{num(r)},{num(-r*.4)} {num(r*.6)},{num(r)} 0,{num(r*.6)}s{num(-r*.8)},{num(-r)} 0,{num(-r*.6)}"
        out.append(f'<g transform="translate({num(x)} {num(y)})"><circle r="1.7" fill="#fff59d" filter="url(#glow)">{move(d, k.r(6, 11), -k.r(0, 8))}{anim("opacity", "0;1;.2;1;0", k.r(3, 6), -k.r(0, 6))}</circle></g>')
    return out


GLOW = ('<filter id="glow" x="-100%" y="-100%" width="300%" height="300%"><feGaussianBlur stdDeviation="2.4" result="b"/>'
        '<feMerge><feMergeNode in="b"/><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>')
