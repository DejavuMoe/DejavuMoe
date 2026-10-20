"""A tiny isometric drawing kit: projection, colour, shading and animation helpers.

Everything returns SVG markup strings. No fonts, scripts or remote resources.
"""

from __future__ import annotations

import html
import math
import random

SQ2 = math.sqrt(2)


def num(value):
    value = round(value, 1)
    return str(int(value)) if value == int(value) else f"{value:.1f}"


def pts(points):
    return " ".join(f"{num(x)},{num(y)}" for x, y in points)


def attrs(**kw):
    return "".join(f' {k.rstrip("_").replace("_", "-")}="{v if isinstance(v, str) else num(v)}"' for k, v in kw.items() if v is not None)


def poly(points, fill, **kw):
    return f'<path d="M{pts(points)}Z" fill="{fill}"{attrs(**kw)}/>'


def esc(value):
    return html.escape(str(value), quote=True)


# --- colour ------------------------------------------------------------------

def rgb(color):
    color = color.lstrip("#")
    return tuple(int(color[i:i + 2], 16) for i in (0, 2, 4))


def hexa(values):
    return "#" + "".join(f"{max(0, min(255, round(v))):02x}" for v in values)


def mix(a, b, t):
    return hexa(x + (y - x) * t for x, y in zip(rgb(a), rgb(b)))


def shade(color, factor):
    """factor < 1 darkens towards black; factor > 1 lightens towards white."""
    return mix(color, "#000000", 1 - factor) if factor <= 1 else mix(color, "#ffffff", factor - 1)


NIGHT_TINT = "#1c2558"


class Theme:
    """Maps daylight colours into the night scene, so one drawing serves both."""

    def __init__(self, name):
        self.name = name
        self.dark = name == "dark"

    def __call__(self, color):
        return mix(shade(color, .62), NIGHT_TINT, .4) if self.dark else color

    def pick(self, day, night):
        return night if self.dark else day


# --- projection --------------------------------------------------------------

class Iso:
    """2:1 isometric projection. x runs right-down, y runs left-down, z runs up."""

    def __init__(self, ox, oy, u=22.0, zu=24.0):
        self.ox, self.oy, self.u, self.zu = ox, oy, u, zu

    def __call__(self, x, y, z=0.0):
        return (self.ox + (x - y) * self.u, self.oy + (x + y) * self.u / 2 - z * self.zu)

    def radii(self, r):
        """Screen radii of a ground circle of grid radius r."""
        return r * self.u * SQ2, r * self.u * SQ2 / 2

    def face(self, side, x, y, z):
        """Matrix mapping local (s along the face, t down from z) onto a wall.

        left:  the wall facing +y, s runs along +x from (x, y, z)
        right: the wall facing +x, s runs along -y from (x, y, z)
        """
        ox, oy = self(x, y, z)
        b = self.u / 2 if side == "left" else -self.u / 2
        return f"matrix({num(self.u)} {num(b)} 0 {num(self.zu)} {num(ox)} {num(oy)})"


class Kit:
    """Drawing context shared by every object in one picture."""

    def __init__(self, iso, theme, seed=7):
        self.iso, self.L, self.dark = iso, theme, theme.dark
        self.rand = random.Random(seed)
        self.defs = []
        self._ids = 0

    def uid(self, prefix):
        self._ids += 1
        return f"{prefix}{self._ids}"

    def r(self, a=0.0, b=1.0):
        return a + (b - a) * self.rand.random()


# --- solids --------------------------------------------------------------------

def box(k, x, y, z, dx, dy, dz, color, top=None):
    I, L = k.iso, k.L
    x1, y1, z1 = x + dx, y + dy, z + dz
    return [
        poly([I(x, y1, z), I(x1, y1, z), I(x1, y1, z1), I(x, y1, z1)], L(shade(color, .9))),
        poly([I(x1, y1, z), I(x1, y, z), I(x1, y, z1), I(x1, y1, z1)], L(shade(color, .72))),
        poly([I(x, y, z1), I(x1, y, z1), I(x1, y1, z1), I(x, y1, z1)], L(shade(top or color, 1.08))),
    ]


def frustum(k, cx, cy, z0, z1, r0, r1, color, top=None):
    """A vertical cylinder (r0 == r1) or cone section, shaded left/right."""
    I, L = k.iso, k.L
    bx, by = I(cx, cy, z0)
    tx, ty = I(cx, cy, z1)
    a, b = k.iso.radii(r0)
    c, d = k.iso.radii(r1)
    left = f"M{num(bx-a)},{num(by)}A{num(a)},{num(b)} 0 0 0 {num(bx)},{num(by+b)}L{num(tx)},{num(ty+d)}A{num(c)},{num(d)} 0 0 1 {num(tx-c)},{num(ty)}Z"
    right = f"M{num(bx)},{num(by+b)}A{num(a)},{num(b)} 0 0 0 {num(bx+a)},{num(by)}L{num(tx+c)},{num(ty)}A{num(c)},{num(d)} 0 0 1 {num(tx)},{num(ty+d)}Z"
    out = [f'<path d="{left}" fill="{L(shade(color, .92))}"/>', f'<path d="{right}" fill="{L(shade(color, .7))}"/>']
    if top is not False and r1 > 0:
        out.append(f'<ellipse{attrs(cx=tx, cy=ty, rx=c, ry=d)} fill="{L(shade(top or color, 1.1))}"/>')
    return out


def cone(k, cx, cy, z0, z1, r, color):
    I, L = k.iso, k.L
    bx, by = I(cx, cy, z0)
    ax, ay = I(cx, cy, z1)
    a, b = k.iso.radii(r)
    return [
        f'<path d="M{num(bx-a)},{num(by)}A{num(a)},{num(b)} 0 0 0 {num(bx)},{num(by+b)}L{num(ax)},{num(ay)}Z" fill="{L(shade(color, 1.0))}"/>',
        f'<path d="M{num(bx)},{num(by+b)}A{num(a)},{num(b)} 0 0 0 {num(bx+a)},{num(by)}L{num(ax)},{num(ay)}Z" fill="{L(shade(color, .74))}"/>',
    ]


def gable(k, x, y, z, dx, dy, rise, color, wall, axis="x", eave=.12):
    I, L = k.iso, k.L
    x1, y1, o = x + dx, y + dy, eave
    if axis == "x":
        m = y + dy / 2
        return [
            poly([I(x - o, y - o, z), I(x1 + o, y - o, z), I(x1 + o, m, z + rise), I(x - o, m, z + rise)], L(shade(color, .8))),
            poly([I(x1, y, z), I(x1, y1, z), I(x1, m, z + rise)], L(shade(wall, .72))),
            poly([I(x - o, y1 + o, z), I(x1 + o, y1 + o, z), I(x1 + o, m, z + rise), I(x - o, m, z + rise)], L(shade(color, 1.04))),
        ]
    m = x + dx / 2
    return [
        poly([I(x - o, y - o, z), I(m, y - o, z + rise), I(m, y1 + o, z + rise), I(x - o, y1 + o, z)], L(shade(color, 1.06))),
        poly([I(x1 + o, y - o, z), I(m, y - o, z + rise), I(m, y1 + o, z + rise), I(x1 + o, y1 + o, z)], L(shade(color, .76))),
        poly([I(x, y1, z), I(x1, y1, z), I(m, y1, z + rise)], L(shade(wall, .9))),
    ]


def pyramid(k, x, y, z, dx, dy, rise, color, eave=.1):
    I, L = k.iso, k.L
    x0, y0, x1, y1 = x - eave, y - eave, x + dx + eave, y + dy + eave
    apex = I(x + dx / 2, y + dy / 2, z + rise)
    return [
        poly([I(x0, y0, z), I(x0, y1, z), apex], L(shade(color, 1.08))),
        poly([I(x0, y0, z), I(x1, y0, z), apex], L(shade(color, .86))),
        poly([I(x0, y1, z), I(x1, y1, z), apex], L(shade(color, .98))),
        poly([I(x1, y0, z), I(x1, y1, z), apex], L(shade(color, .74))),
    ]


def ball(k, sx, sy, r, color, gloss=True):
    L = k.L
    out = [f'<circle{attrs(cx=sx, cy=sy, r=r)} fill="{L(color)}"/>',
           f'<path d="M{num(sx-r)},{num(sy)}A{num(r)},{num(r)} 0 0 0 {num(sx+r)},{num(sy)}A{num(r)},{num(r*.55)} 0 0 1 {num(sx-r)},{num(sy)}Z" fill="{L(shade(color, .8))}"/>']
    if gloss:
        out.append(f'<ellipse{attrs(cx=sx-r*.38, cy=sy-r*.42, rx=r*.28, ry=r*.18)} fill="#fff" opacity=".45" transform="rotate(-35 {num(sx-r*.38)} {num(sy-r*.42)})"/>')
    return out


# --- animation (SMIL works inside <img>, unlike scripts) -----------------------

def anim(attr, values, dur, begin=0.0, **kw):
    return f'<animate attributeName="{attr}" values="{values}" dur="{num(dur)}s" begin="{num(begin)}s" repeatCount="indefinite"{attrs(**kw)}/>'


def spin(dur, cx, cy, begin=0.0, reverse=False):
    a, b = (360, 0) if reverse else (0, 360)
    return f'<animateTransform attributeName="transform" type="rotate" from="{a} {num(cx)} {num(cy)}" to="{b} {num(cx)} {num(cy)}" dur="{num(dur)}s" begin="{num(begin)}s" repeatCount="indefinite"/>'


def sway(values, dur, begin=0.0, kind="rotate", additive=False):
    extra = ' additive="sum"' if additive else ""
    return f'<animateTransform attributeName="transform" type="{kind}" values="{values}" dur="{num(dur)}s" begin="{num(begin)}s" repeatCount="indefinite"{extra} calcMode="spline" keySplines="{";".join([".45 0 .55 1"] * (values.count(";")))}"/>'


def move(path_d, dur, begin=0.0, **kw):
    return f'<animateMotion path="{path_d}" dur="{num(dur)}s" begin="{num(begin)}s" repeatCount="indefinite"{attrs(**kw)}/>'
