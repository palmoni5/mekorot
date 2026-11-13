"""Niqqud and te'amim drawn in Mekorot's own stroke language.

Mekorot's letters and its original vowels (patah, qamats) are soft brush shapes: round blob
terminals, a thinner waist between them and teardrop ends. The marks here are built from
skeleton strokes swept with a round brush of varying radius, so they share that look, instead
of the monoline geometric outlines borrowed from Noto Rashi Hebrew.

Every design is written for a nominal box (W0 x H0, font units, origin bottom-left) and is
stretched to the box of the glyph it replaces, so mark positioning keeps working unchanged.
"""
import math

from fontTools.pens.ttGlyphPen import TTGlyphPen
from shapely import affinity
from shapely.geometry import Point, Polygon
from shapely.geometry.polygon import orient
from shapely.ops import unary_union

TEAM_D = 54.0        # stroke diameter of the te'amim at Regular weight
DOT_D = 86.0         # dots inside te'amim (same as the niqqud dots)
SIMPLIFY = 0.9


# ---------- brush ----------
def _spline(pts, per=14):
    """Catmull-Rom through pts -> dense list of (x, y, u) with u the control-point parameter."""
    n = len(pts)
    if n == 2:
        return [(pts[0][0] + (pts[1][0] - pts[0][0]) * k / per,
                 pts[0][1] + (pts[1][1] - pts[0][1]) * k / per, k / per) for k in range(per + 1)]
    out = []
    for i in range(n - 1):
        p0 = pts[max(i - 1, 0)]
        p1, p2 = pts[i], pts[i + 1]
        p3 = pts[min(i + 2, n - 1)]
        for k in range(per + (1 if i == n - 2 else 0)):
            t = k / per
            t2, t3 = t * t, t * t * t
            out.append(tuple(
                0.5 * ((2 * p1[a]) + (-p0[a] + p2[a]) * t + (2 * p0[a] - 5 * p1[a] + 4 * p2[a] - p3[a]) * t2
                       + (-p0[a] + 3 * p1[a] - 3 * p2[a] + p3[a]) * t3) for a in (0, 1)) + (i + t,))
    return out


def _poly(pts, per=10):
    out = []
    for i in range(len(pts) - 1):
        for k in range(per + (1 if i == len(pts) - 2 else 0)):
            t = k / per
            out.append((pts[i][0] + (pts[i + 1][0] - pts[i][0]) * t,
                        pts[i][1] + (pts[i + 1][1] - pts[i][1]) * t, i + t))
    return out


def _rad(radii, u):
    i = min(int(u), len(radii) - 2)
    t = u - i
    t = t * t * (3 - 2 * t)      # ease, so the swelling is soft
    return radii[i] + (radii[i + 1] - radii[i]) * t


def stroke(pts, radii, r, smooth=True):
    """Sweep a round brush of radius r * radii[i] along the skeleton."""
    path = _spline(pts) if smooth else _poly(pts)
    discs = [Point(x, y).buffer(max(r * _rad(radii, u), 1.0), 12) for x, y, u in path]
    return unary_union([discs[i].union(discs[i + 1]).convex_hull for i in range(len(discs) - 1)])


def dot(x, y, d):
    return Point(x, y).buffer(d / 2.0, 16)


def ring(cx, cy, rad, r, heavy_at=215, mod=0.14):
    """A brush circle: slightly heavier on one side, like a pen-drawn loop."""
    n = 48
    discs = []
    for k in range(n + 1):
        a = 2 * math.pi * k / n
        w = r * (1.0 + mod * math.cos(a - math.radians(heavy_at)))
        discs.append(Point(cx + rad * math.cos(a), cy + rad * math.sin(a)).buffer(w, 10))
    return unary_union([discs[i].union(discs[i + 1]).convex_hull for i in range(n)])


# ---------- designs ----------
def _mx(pts, w):
    return [(w - x, y) for x, y in pts]


def _my(pts, h):
    return [(x, h - y) for x, y in pts]


def _sh(pts, dx):
    return [(x + dx, y) for x, y in pts]


HOOK = [(30, 264), (25, 165), (58, 75), (130, 26)]        # tipcha: head on top, tail to the right
HOOK_R = [1.34, 1.0, 0.76, 0.78]
HOOK_W, HOOK_H = 155, 290


def _hook(r, mirror=False, flip=False, dx=0):
    p = HOOK
    if mirror:
        p = _mx(p, HOOK_W)
    if flip:
        p = _my(p, HOOK_H)
    return stroke(_sh(p, dx), HOOK_R, r)


def _telisha(r, gedola, dx=0):
    """Loop with a tail; gedola: tail down-left, qetana: tail down-right."""
    w = 288
    cx, cy, rad = 172, 172, 74
    tail = [(cx - rad * 0.74, cy - rad * 0.74), (60, 62), (30, 30)]
    lp = ring(cx, cy, rad, r * 0.9, mod=0.22)
    tl = stroke(tail, [0.72, 0.85, 1.32], r)
    g = unary_union([lp, tl])
    if not gedola:
        g = affinity.scale(g, xfact=-1, yfact=1, origin=(w / 2.0, 0))
    return affinity.translate(g, dx, 0)


def _angle(r, w=190, h=272):
    """yetiv / mahpakh / ole: an open wedge, lower arm heavier."""
    return stroke([(w - 26, h - 24), (w * 0.52, h * 0.70), (26, h / 2.0), (w * 0.52, h * 0.30), (w - 26, 24)],
                  [0.7, 0.72, 1.0, 1.0, 1.38], r, smooth=False)


def _corner(r):
    """munah / iluy: upright thin, foot heavy, soft corner."""
    return stroke([(187, 182), (184, 100), (178, 30), (100, 27), (27, 30)],
                  [0.78, 0.68, 0.9, 1.0, 1.4], r, smooth=False)


def _wish(r, up):
    """etnahta (up=True: stem on top) / atnah hafukh, galgal (stem below)."""
    arch = stroke([(30, 30), (34, 100), (72, 166), (134, 198), (196, 166), (234, 100), (238, 30)],
                  [1.38, 0.9, 0.74, 0.8, 0.74, 0.9, 1.38], r)
    stem = stroke([(134, 196), (134, 262)], [0.74, 1.05], r)
    g = unary_union([arch, stem])
    if not up:
        g = affinity.scale(g, xfact=1, yfact=-1, origin=(0, 145))
    return g


def _wave(r):
    return stroke([(46, 58), (30, 122), (72, 178), (140, 176), (212, 108), (284, 40), (352, 36), (396, 92),
                   (376, 166)], [1.36, 0.95, 0.8, 0.8, 0.72, 0.8, 0.8, 0.95, 1.36], r)


# cp -> (W0, H0, builder(r) -> shapely geometry)
DESIGNS = {
    0x591: (269, 289, lambda r: _wish(r, True)),
    0x592: (273, 227, lambda r: unary_union([dot(136, 184, DOT_D), dot(43, 43, DOT_D), dot(230, 43, DOT_D)])),
    0x593: (209, 323, lambda r: stroke([(172, 300), (32, 244), (178, 190), (32, 132), (178, 78), (52, 24)],
                                       [1.25, 0.7, 1.0, 0.7, 1.0, 1.3], r, smooth=False)),
    0x594: (93, 227, lambda r: unary_union([dot(46, 184, DOT_D), dot(46, 43, DOT_D)])),
    0x595: (237, 255, lambda r: unary_union([stroke([(30, 228), (30, 130), (30, 32)], [0.72, 0.72, 1.36], r),
                                             dot(194, 208, DOT_D), dot(194, 47, DOT_D)])),
    0x596: (HOOK_W, HOOK_H, lambda r: _hook(r)),
    0x597: (209, 233, lambda r: Polygon([(104, 200), (176, 116), (104, 33), (33, 116)]).buffer(r * 1.3, 12)),
    0x598: (424, 215, _wave),
    0x599: (HOOK_W, HOOK_H, lambda r: _hook(r, mirror=True, flip=True)),
    0x59a: (190, 272, _angle),
    0x59b: (226, 285, lambda r: unary_union([affinity.translate(_hook(r, mirror=True), 72, 0),
                                             dot(44, 238, DOT_D)])),
    0x59c: (HOOK_W, HOOK_H, lambda r: _hook(r, flip=True)),
    0x59d: (HOOK_W, HOOK_H, lambda r: _hook(r, flip=True)),
    0x59e: (337, 290, lambda r: unary_union([_hook(r, flip=True), _hook(r, flip=True, dx=182)])),
    0x59f: (620, 289, lambda r: unary_union([_telisha(r, False), _telisha(r, True, dx=332)])),
    0x5a0: (288, 289, lambda r: _telisha(r, True)),
    0x5a1: (234, 251, lambda r: unary_union([stroke([(30, 226), (28, 125), (30, 30)], [0.78, 0.72, 1.36], r),
                                             stroke([(204, 226), (200, 160), (140, 116), (36, 110)],
                                                    [1.36, 0.95, 0.72, 0.7], r)])),
    0x5a2: (269, 290, lambda r: _wish(r, False)),
    0x5a3: (213, 205, _corner),
    0x5a4: (190, 272, _angle),
    0x5a5: (HOOK_W, HOOK_H, lambda r: _hook(r, mirror=True)),
    0x5a6: (334, 291, lambda r: unary_union([_hook(r, mirror=True), _hook(r, mirror=True, dx=179)])),
    0x5a7: (192, 245, lambda r: stroke([(168, 220), (30, 194), (164, 52), (26, 26)],
                                       [1.2, 0.78, 0.78, 1.38], r, smooth=False)),
    0x5a8: (HOOK_W, HOOK_H, lambda r: _hook(r, mirror=True, flip=True)),
    0x5a9: (288, 289, lambda r: _telisha(r, False)),
    0x5aa: (269, 290, lambda r: _wish(r, False)),
    0x5ab: (190, 272, _angle),
    0x5ac: (213, 205, _corner),
    0x5ad: (HOOK_W, HOOK_H, lambda r: _hook(r)),
    0x5ae: (424, 215, _wave),
    0x5af: (249, 251, lambda r: ring(124, 125, 92, r * 0.9, mod=0.22)),
}


# ---------- vowels that are bars ----------
def bar(w, h, waist=0.86):
    """patah / rafe: a pill with blob ends and a slight waist, as in the original Mekorot patah."""
    r = h / 2.0
    return stroke([(r, r), (w / 2.0, r), (w - r, r)], [1.0, waist, 1.0], r)


def qamats(w, h, bar_h, drop=True):
    """Bar with a stem hanging from its middle; the regular qamats ends in a teardrop."""
    r = bar_h / 2.0
    top = affinity.translate(bar(w, bar_h), 0, h - bar_h)
    if drop:
        rd = r * 1.22
        stem = stroke([(w / 2.0, h - bar_h), (w / 2.0, (h - bar_h) * 0.62), (w / 2.0, rd)], [0.7, 0.55, 1.22], r)
    else:
        stem = stroke([(w / 2.0, h - bar_h), (w / 2.0, r * 0.8)], [0.62, 0.8], r)
    return unary_union([top, stem])


def meteg(w, h):
    r = w / 2.0
    return stroke([(r, h - r * 0.85), (r, h / 2.0), (r, r)], [0.85, 0.78, 1.0], r)


# ---------- geometry -> glyph ----------
def to_glyph(geom):
    """Shapely geometry -> TrueType glyph of smooth quadratic contours."""
    geom = geom.simplify(SIMPLIFY)
    polys = [geom] if geom.geom_type == 'Polygon' else list(geom.geoms)
    pen = TTGlyphPen(None)
    for p in polys:
        p = orient(p, -1)       # TrueType: outer contours clockwise, holes counter-clockwise
        for rg in [p.exterior] + list(p.interiors):
            v = list(rg.coords)[:-1]
            n = len(v)
            if n < 3:
                continue
            mid = lambda i: ((v[i][0] + v[(i + 1) % n][0]) / 2.0, (v[i][1] + v[(i + 1) % n][1]) / 2.0)
            pen.moveTo(mid(n - 1))
            for i in range(n):
                pen.qCurveTo(v[i], mid(i))
            pen.closePath()
    return pen.glyph()


def fit(geom, box, side):
    """Place geom on the box of the glyph it replaces: centred, flush with the edge facing the letter."""
    x0, y0, x1, y1 = geom.bounds
    dx = (box[0] + box[2]) / 2.0 - (x0 + x1) / 2.0
    dy = (box[1] - y0) if side == 'above' else (box[3] - y1)
    return affinity.translate(geom, dx, dy)


def team(cp, box, wf):
    """Geometry of te'am cp for the box (xMin, yMin, xMax, yMax) of the outline it replaces."""
    w0, h0, fn = DESIGNS[cp]
    g = fn(TEAM_D * wf / 2.0)
    g = affinity.scale(g, xfact=(box[2] - box[0]) / float(w0), yfact=(box[3] - box[1]) / float(h0), origin=(0, 0))
    side = 'above' if (box[1] + box[3]) / 2.0 > 250 else 'below'
    return fit(g, box, side)


def round_dots(font, name, d=DOT_D, gap=22):
    """Make every dot of a simple glyph a true circle again (earlier narrowing squeezed them to ovals)."""
    glyf = font['glyf']
    g = glyf[name]
    if g.numberOfContours <= 0:
        return
    coords, ends = g.coordinates, g.endPtsOfContours
    cs, start = [], 0
    for e in ends:
        xs = [coords[i][0] for i in range(start, e + 1)]
        ys = [coords[i][1] for i in range(start, e + 1)]
        start = e + 1
        w, h = max(xs) - min(xs), max(ys) - min(ys)
        if not (40 <= w <= 130 and 40 <= h <= 130 and 0.6 <= w / float(h) <= 1.67):
            return                      # something that is not a dot: leave the glyph alone
        cs.append(((min(xs) + max(xs)) / 2.0, (min(ys) + max(ys)) / 2.0))
    for i in range(len(cs)):
        for j in range(i + 1, len(cs)):
            d = min(d, math.hypot(cs[i][0] - cs[j][0], cs[i][1] - cs[j][1]) - gap)
    if d < 50:
        return
    ng = to_glyph(unary_union([dot(x, y, d) for x, y in cs]))
    glyf[name] = ng
    ng.recalcBounds(glyf)


def restyle(font, patah_thin=0.8):
    """Redraw the te'amim and the bar-shaped niqqud of a font in place.
    Each new outline takes the box of the one it replaces, so mark positioning is unaffected."""
    c = font.getBestCmap()
    glyf = font['glyf']

    def bounds(cp):
        g = glyf[c[cp]]
        g.recalcBounds(glyf)
        return g.xMin, g.yMin, g.xMax, g.yMax

    def put(cp, geom):
        box = bounds(cp)
        side = 'above' if (box[1] + box[3]) / 2.0 > 250 else 'below'
        g = to_glyph(fit(geom, box, side))
        glyf[c[cp]] = g
        g.recalcBounds(glyf)

    for cp in (0x5b0, 0x5b1, 0x5b2, 0x5b3, 0x5b4, 0x5b5, 0x5b6, 0x5b9, 0x5ba, 0x5c1, 0x5c2, 0x5c4, 0x5c5):
        if cp in c:
            round_dots(font, c[cp])
    pb = bounds(0x5b7)
    bar_h = pb[3] - pb[1]
    wf = (bar_h / (76.0 * patah_thin)) ** 0.7     # stroke weight follows the font's own patah
    for cp in DESIGNS:
        if cp in c and glyf[c[cp]].numberOfContours > 0:
            g = to_glyph(team(cp, bounds(cp), wf))
            glyf[c[cp]] = g
            g.recalcBounds(glyf)
    put(0x5b7, bar(pb[2] - pb[0], bar_h))
    qb = bounds(0x5b8)
    put(0x5b8, qamats(qb[2] - qb[0], qb[3] - qb[1], bar_h))
    if 0x5c7 in c:
        b = bounds(0x5c7)
        put(0x5c7, qamats(b[2] - b[0], b[3] - b[1], bar_h * 0.9, drop=False))
    if 0x5bf in c:
        b = bounds(0x5bf)
        put(0x5bf, bar(b[2] - b[0], min(b[3] - b[1], bar_h)))
    if 0x5bd in c:
        b = bounds(0x5bd)
        put(0x5bd, meteg(b[2] - b[0], b[3] - b[1]))
