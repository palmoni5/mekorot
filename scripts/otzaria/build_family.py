"""Builds static Mekorot weights (Light..ExtraBold) with:
 - lighter Light weight (axis extrapolation below wght 400)
 - wider word space and slight letter tracking
 - missing Hebrew punctuation (maqaf, geresh, gershayim, sof pasuq, paseq, nun hafukha)
 - missing niqqud/te'amim, taken from Noto Rashi Hebrew (OFL) and positioned with GPOS
 - zero-width / spacing format characters
Usage: build_family.py <variable.ttf> <noto_rashi.ttf> <out_dir>
"""
import copy
import sys

from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont, newTable
from fontTools.ttLib.tables import otTables as ot
from fontTools.ttLib.tables._g_l_y_f import GlyphCoordinates
from fontTools.otlLib import builder as otl
from fontTools.varLib import instancer

VAR, NOTO, OUT = sys.argv[1], sys.argv[2], sys.argv[3]

SPACE = 340
TRACK = 15
LIGHT_K = 0.4
WEIGHTS = [  # name, wght (None = extrapolated light), weight class
    ('Light', None, 300),
    ('Regular', 400, 400),
    ('Medium', 500, 500),
    ('SemiBold', 600, 600),
    ('Bold', 700, 700),
    ('ExtraBold', 800, 800),
]
ABOVE_GAP, BELOW_GAP, STACK_GAP = 55, 55, 35
CID = {'above': 0, 'below': 1}


def extrapolate_light():
    a = instancer.instantiateVariableFont(TTFont(VAR), {'wght': 400})
    b = instancer.instantiateVariableFont(TTFont(VAR), {'wght': 800})
    ga, gb, ha, hb = a['glyf'], b['glyf'], a['hmtx'], b['hmtx']
    for name in a.getGlyphOrder():
        x, y = ga[name], gb[name]
        if x.isComposite():
            for ca, cb in zip(x.components, y.components):
                ca.x = round(ca.x - LIGHT_K * (cb.x - ca.x))
                ca.y = round(ca.y - LIGHT_K * (cb.y - ca.y))
            x.recalcBounds(ga)
        elif x.numberOfContours != 0:
            ca, _, _ = x.getCoordinates(ga)
            cb, _, _ = y.getCoordinates(gb)
            new = [(round(p - LIGHT_K * (q - p)), round(r - LIGHT_K * (s - r)))
                   for (p, r), (q, s) in zip(ca, cb)]
            x.coordinates = GlyphCoordinates(new[:len(x.coordinates)])
            x.recalcBounds(ga)
        adv = max(0, round(ha[name][0] - LIGHT_K * (hb[name][0] - ha[name][0])))
        ha[name] = (adv, ga[name].xMin if ga[name].numberOfContours else 0)
    return a


def add_glyph(font, cp, name, glyph, adv):
    glyf, hmtx = font['glyf'], font['hmtx']
    glyf[name] = glyph
    if glyph.numberOfContours != 0:
        glyph.recalcBounds(glyf)
    order = font.getGlyphOrder()
    if name not in order:
        order.append(name)
        font.setGlyphOrder(order)
    hmtx[name] = (adv, glyph.xMin if glyph.numberOfContours else 0)
    if cp is not None:
        for t in font['cmap'].tables:
            if t.isUnicode():
                t.cmap[cp] = name
    font['maxp'].numGlyphs = len(order)


def empty_glyph():
    return Glyph0()


def Glyph0():
    from fontTools.ttLib.tables._g_l_y_f import Glyph
    g = Glyph()
    g.numberOfContours = 0
    return g


def copy_shifted(font, src, dy=0):
    g = copy.deepcopy(font['glyf'][src])
    if dy and g.numberOfContours > 0:
        g.coordinates.translate((0, dy))
        g.recalcBounds(font['glyf'])
    return g


TRAIL_PAD = 50     # extra space between a word and a trailing . , : ; ! ? sof pasuq
TICK_SLANT = 0.34  # shear of geresh/gershayim ticks
BRACKET_PAD = 30   # extra space on each side of brackets


def shift_glyph_x(font, name, dx):
    g = font['glyf'][name]
    if g.numberOfContours > 0:
        g.coordinates.translate((dx, 0))
    elif g.isComposite():
        for comp in g.components:
            comp.x += dx
    g.recalcBounds(font['glyf'])


DOT_D = 86             # diameter of the dots of niqqud and te'amim
PERIOD_D = 124         # the period
PERIOD_SCALE = PERIOD_D / 122.0
QAMATS_HEIGHT = 0.80    # vertical scale of the qamats (kept hanging from its top)
PATAH_THIN = 0.80      # vertical scale of the patah bar
SEMICOLON_RAISE = 50    # upper dot of the semicolon started too low
NARROW_VOWELS = {0x5b7: 0.64, 0x5b8: 0.64}   # patah, qamats were wider than most letters


DOT_GAP = 34
DOT_VOWELS = [0x5b0, 0x5b1, 0x5b2, 0x5b3, 0x5b4, 0x5b5, 0x5b6, 0x5b9, 0x5ba, 0x5c1, 0x5c2]


def unify_dots(font, name, d=DOT_D):
    """Resize every round dot contour of a glyph to diameter d (keeping centres, pushing apart if they would touch)."""
    glyf = font['glyf']
    g = glyf[name]
    if g.numberOfContours <= 0:
        return
    coords, ends = g.coordinates, g.endPtsOfContours
    spans, start = [], 0
    for e in ends:
        spans.append((start, e))
        start = e + 1
    dots = []
    for a, b in spans:
        xs = [coords[i][0] for i in range(a, b + 1)]
        ys = [coords[i][1] for i in range(a, b + 1)]
        w, h = max(xs) - min(xs), max(ys) - min(ys)
        if 50 <= w <= 160 and 50 <= h <= 160 and 0.75 <= w / h <= 1.33:
            dots.append((a, b, (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, (w + h) / 2))
    if not dots:
        return
    cx = sum(x[2] for x in dots) / len(dots)
    cy = sum(x[3] for x in dots) / len(dots)
    f = 1.0
    for i in range(len(dots)):
        for j in range(i + 1, len(dots)):
            dist = ((dots[i][2] - dots[j][2]) ** 2 + (dots[i][3] - dots[j][3]) ** 2) ** 0.5
            if dist < d + DOT_GAP:
                f = max(f, (d + DOT_GAP) / max(dist, 1))
    pts = list(coords)
    for a, b, x0, y0, dia in dots:
        k = d / dia
        nx, ny = cx + (x0 - cx) * f, cy + (y0 - cy) * f
        for i in range(a, b + 1):
            px, py = pts[i]
            pts[i] = (round(nx + (px - x0) * k), round(ny + (py - y0) * k))
    g.coordinates = GlyphCoordinates(pts)
    g.recalcBounds(glyf)


def resize_punct_and_vowels(font):
    c = font.getBestCmap()
    glyf = font['glyf']
    g = glyf[c[0x2e]]
    g.recalcBounds(glyf)
    xc, y0 = (g.xMin + g.xMax) / 2, g.yMin
    g.coordinates = GlyphCoordinates(
        [(round(xc + (x - xc) * PERIOD_SCALE), round(y0 + (y - y0) * PERIOD_SCALE))
         for x, y in g.coordinates])
    g.recalcBounds(glyf)
    sc = glyf[c[0x3b]]
    if sc.isComposite():
        for comp in sc.components:
            if comp.glyphName == c[0x2e]:
                comp.y += SEMICOLON_RAISE
        sc.recalcBounds(glyf)
    for cp in DOT_VOWELS:
        if cp in c:
            unify_dots(font, c[cp])
    for cp, k in NARROW_VOWELS.items():
        v = glyf[c[cp]]
        v.recalcBounds(glyf)
        xm = (v.xMin + v.xMax) / 2
        ym = (v.yMin + v.yMax) / 2
        ky = PATAH_THIN if cp == 0x5b7 else 1.0
        if cp == 0x5b8:
            # same waist in the qamats bar: straighten it, then shorten the whole sign from its top
            half = (v.xMax - v.xMin) / 2
            v.coordinates = GlyphCoordinates(
                [(x, (v.yMax if y > v.yMax - 40 else v.yMax - 76)
                  if (v.yMax - 80 <= y <= v.yMax + 5 and abs(x - xm) <= 0.75 * half) else y)
                 for x, y in v.coordinates])
            ym, ky = v.yMax, QAMATS_HEIGHT
        if cp == 0x5b7:
            # the bar has a concave waist that reads as a notch at small sizes: make both edges straight
            half = (v.xMax - v.xMin) / 2
            v.coordinates = GlyphCoordinates(
                [(x, v.yMax if (y > ym and abs(x - xm) <= 0.75 * half)
                  else v.yMin if (y < ym and abs(x - xm) <= 0.75 * half) else y)
                 for x, y in v.coordinates])
        v.coordinates = GlyphCoordinates(
            [(round(xm + (x - xm) * k), round(ym + (y - ym) * ky)) for x, y in v.coordinates])
        v.recalcBounds(glyf)


def pad_punctuation(font):
    c = font.getBestCmap()
    hmtx = font['hmtx']
    for cp in (0x2e, 0x2c, 0x3a, 0x3b, 0x21, 0x3f, 0x5c3):
        adv, lsb = hmtx[c[cp]]
        hmtx[c[cp]] = (adv + TRAIL_PAD, lsb)
    # Space only on the side facing the bracketed text (RTL: the '(' glyph closes, ')' opens),
    # so a bracket followed by a comma does not stack two paddings.
    for cp in (0x28, 0x5b, 0x7b):
        n = c[cp]
        adv, lsb = hmtx[n]
        hmtx[n] = (adv + BRACKET_PAD, lsb)
    for cp in (0x29, 0x5d, 0x7d):
        n = c[cp]
        adv, lsb = hmtx[n]
        shift_glyph_x(font, n, BRACKET_PAD)
        hmtx[n] = (adv + BRACKET_PAD, lsb + BRACKET_PAD)


def slant_ticks(font):
    """Rashi-script geresh/gershayim are slanted ticks (top leaning right), not upright sticks."""
    c = font.getBestCmap()
    glyf = font['glyf']
    for cp in (0x27, 0x5f3, 0x22, 0x5f4):
        g = glyf[c[cp]]
        if g.numberOfContours <= 0:
            continue
        g.recalcBounds(glyf)
        ym = (g.yMin + g.yMax) / 2
        g.coordinates = GlyphCoordinates(
            [(round(x + TICK_SLANT * (y - ym)), y) for x, y in g.coordinates])
        g.recalcBounds(glyf)


def fix_spacing_and_punct(font):
    c = font.getBestCmap()
    glyf, hmtx = font['glyf'], font['hmtx']
    for cp in range(0x5d0, 0x5eb):
        n = c[cp]
        hmtx[n] = (hmtx[n][0] + TRACK, hmtx[n][1])
    for cp in (0x20, 0xa0):
        hmtx[c[cp]] = (SPACE, 0)
    hy = glyf[c[0x2d]]
    hy.recalcBounds(glyf)
    dy = 330 - (hy.yMin + hy.yMax) // 2
    add_glyph(font, 0x5be, 'maqafhb', copy_shifted(font, c[0x2d], dy), hmtx[c[0x2d]][0])
    q = glyf[c[0x27]]
    q.recalcBounds(glyf)
    dyq = 560 - q.yMax
    add_glyph(font, 0x5f3, 'gereshhb', copy_shifted(font, c[0x27], dyq), hmtx[c[0x27]][0])
    add_glyph(font, 0x5f4, 'gershayimhb', copy_shifted(font, c[0x22], dyq), hmtx[c[0x22]][0])
    add_glyph(font, 0x5c3, 'sofpasuqhb', copy_shifted(font, c[0x3a]), hmtx[c[0x3a]][0])
    add_glyph(font, 0x2010, 'uni2010', copy_shifted(font, c[0x2d]), hmtx[c[0x2d]][0])
    add_glyph(font, 0x2011, 'uni2011', copy_shifted(font, c[0x2d]), hmtx[c[0x2d]][0])
    for cp, adv in ((0x200c, 0), (0x200d, 0), (0x200e, 0), (0x200f, 0), (0x202a, 0),
                    (0x202b, 0), (0x202c, 0), (0x2066, 0), (0x2067, 0), (0x2068, 0),
                    (0x2069, 0), (0x2002, 500), (0x2003, 1000), (0x2005, 250)):
        if cp not in c:
            add_glyph(font, cp, 'uni%04X' % cp, Glyph0(), adv)
    resize_punct_and_vowels(font)
    pad_punctuation(font)
    slant_ticks(font)


# ---------- niqqud / te'amim ----------
def noto_instance(wght):
    wght = max(100, min(900, wght))
    return instancer.instantiateVariableFont(TTFont(NOTO), {'wght': wght})


def noto_glyph_as_tt(noto, cp, scale=1.0):
    name = noto.getBestCmap()[cp]
    pen = TTGlyphPen(None)
    rec = DecomposingRecordingPen(noto.getGlyphSet())
    noto.getGlyphSet()[name].draw(rec)
    from fontTools.pens.transformPen import TransformPen
    tpen = TransformPen(pen, (scale, 0, 0, scale, 0, 0))
    rec.replay(tpen)
    g = pen.glyph()
    return g, noto['hmtx'][name][0]


def glyph_bounds(font, name):
    g = font['glyf'][name]
    if g.numberOfContours == 0:
        return None
    g.recalcBounds(font['glyf'])
    return g.xMin, g.yMin, g.xMax, g.yMax


TEAMIM_SCALE = 1.55
TEAMIM_EXTRA_WGHT = 130   # te'amim are lighter than before (+250) to sit better with the letters
BELOW_VOWELS = [0x5b0, 0x5b1, 0x5b2, 0x5b3, 0x5b4, 0x5b5, 0x5b6, 0x5b7, 0x5b8, 0x5bb, 0x5c7]
ABOVE_VOWELS = [0x5b9, 0x5ba]
REL_X = {0x5b9: 0.22, 0x5ba: 0.22, 0x5bb: 0.42, 0x5bd: 0.30}
HOLAM_ON_LAMED = -0.20   # holam sits left of the lamed's ascender, at the normal vowel height
DOTS = [0x5c1, 0x5c2]
SHIN = 'uni05E9'
LEVEL_TOP = 700          # normal letters share one height level above
LEVEL_BASE = -30         # ... and one level below


VOWEL_GAP = 40      # minimum gap between below-vowels of neighbouring letters
INK_PAD = 30       # clearance between a mark and the letter's own ink
ROUND_R = 60        # corner radius of the Noto-derived marks, in font units
ROUND_MIN_ANGLE = 30


def _segments(contour):
    """TrueType contour (list of (pt, on)) -> list of segments ('l', p0, p1) / ('q', p0, c, p1)."""
    pts = list(contour)
    # rotate so that we start on an on-curve point
    k = next((i for i, (_, on) in enumerate(pts) if on), None)
    if k is None:
        return None
    pts = pts[k:] + pts[:k]
    segs = []
    cur = pts[0][0]
    i = 1
    n = len(pts)
    pend = []
    for j in range(1, n + 1):
        pt, on = pts[j % n]
        if on:
            if not pend:
                segs.append(('l', cur, pt))
            else:
                offs = [q for q in pend]
                for m, c in enumerate(offs):
                    nxt = pt if m == len(offs) - 1 else ((c[0] + offs[m + 1][0]) / 2, (c[1] + offs[m + 1][1]) / 2)
                    segs.append(('q', cur, c, nxt))
                    cur = nxt
                pend = []
            cur = pt
        else:
            pend.append(pt)
    return segs


def _dir(a, b):
    import math
    d = math.hypot(b[0] - a[0], b[1] - a[1]) or 1
    return ((b[0] - a[0]) / d, (b[1] - a[1]) / d)


def _seg_len(sg):
    import math
    pts = [x for x in sg[1:]]
    return sum(math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1]) for i in range(len(pts) - 1))


def _start_dir(sg):
    return _dir(sg[1], sg[2])


def _end_dir(sg):
    return _dir(sg[-2], sg[-1])


def _split(sg, t):
    if sg[0] == 'l':
        p0, p1 = sg[1], sg[2]
        m = (p0[0] + (p1[0] - p0[0]) * t, p0[1] + (p1[1] - p0[1]) * t)
        return ('l', p0, m), ('l', m, p1)
    p0, c, p1 = sg[1], sg[2], sg[3]
    a = (p0[0] + (c[0] - p0[0]) * t, p0[1] + (c[1] - p0[1]) * t)
    b = (c[0] + (p1[0] - c[0]) * t, c[1] + (p1[1] - c[1]) * t)
    m = (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
    return ('q', p0, a, m), ('q', m, b, p1)


def round_corners(font, name, r=ROUND_R):
    """Soften sharp corners of a glyph with quadratic fillets (Noto marks are crisper than Mekorot)."""
    import math
    g = font['glyf'][name]
    if g.numberOfContours <= 0:
        return
    coords, ends, flags = g.coordinates, g.endPtsOfContours, g.flags
    pen = TTGlyphPen(None)
    start = 0
    for e in ends:
        cont = [(tuple(coords[i]), bool(flags[i] & 1)) for i in range(start, e + 1)]
        start = e + 1
        segs = _segments(cont)
        if not segs:
            continue
        n = len(segs)
        # per junction: is it a corner
        corner = []
        for i in range(n):
            a, b = _end_dir(segs[i]), _start_dir(segs[(i + 1) % n])
            ang = math.degrees(math.acos(max(-1, min(1, a[0] * b[0] + a[1] * b[1]))))
            corner.append(ang >= ROUND_MIN_ANGLE)
        # trim segments at corners
        trimmed = []
        fill = []   # fillet after segment i (or None)
        for i in range(n):
            sg = segs[i]
            L = _seg_len(sg) or 1
            t0 = 0.0
            t1 = 1.0
            if corner[(i - 1) % n]:
                t0 = min(0.45, r / L)
            if corner[i]:
                t1 = 1 - min(0.45, r / L)
            if t1 < t0 + 0.05:
                t0, t1 = 0.0, 1.0
            if t0 > 0:
                sg = _split(sg, t0)[1]
                t1 = (t1 - t0) / (1 - t0)
            if t1 < 1:
                sg = _split(sg, t1)[0]
            trimmed.append(sg)
        # rebuild
        first = trimmed[0]
        pen.moveTo(first[1])
        for i, sg in enumerate(trimmed):
            if sg[0] == 'l':
                pen.lineTo(sg[2])
            else:
                pen.qCurveTo(sg[2], sg[3])
            nxt = trimmed[(i + 1) % n]
            end = sg[-1]
            if corner[i]:
                # corner point = intersection region: use original junction as control
                ctrl = segs[i][-1]
                pen.qCurveTo(ctrl, nxt[1])
            elif end != nxt[1]:
                pen.lineTo(nxt[1])
        pen.closePath()
    ng = pen.glyph()
    font['glyf'][name] = ng
    ng.recalcBounds(font['glyf'])



def scale_glyph(font, name, k):
    g = font['glyf'][name]
    if g.numberOfContours > 0:
        g.coordinates.scale((k, k))
        g.recalcBounds(font['glyf'])


def add_marks(font, wght):
    noto = noto_instance(wght + TEAMIM_EXTRA_WGHT)
    c = font.getBestCmap()
    spacing = {0x5c0, 0x5c6}
    new_marks = []
    for cp in range(0x591, 0x5c8):
        if cp in c or cp in (0x5be, 0x5c3) or cp not in noto.getBestCmap():
            continue
        g, adv = noto_glyph_as_tt(noto, cp)
        name = 'uni%04X' % cp
        add_glyph(font, cp, name, g, adv if cp in spacing else 0)
        if cp not in spacing:
            new_marks.append(name)
    for cp in range(0x591, 0x5b0):
        if cp in c or ('uni%04X' % cp) in font['glyf']:
            scale_glyph(font, font.getBestCmap().get(cp) or 'uni%04X' % cp, TEAMIM_SCALE)
    for n in new_marks:
        unify_dots(font, n)
        round_corners(font, n)
    return new_marks


def build_mark_mark(marks, base_marks, gm):
    st = ot.MarkMarkPos()
    st.Format = 1
    st.Mark1Coverage = otl.buildCoverage(marks, gm)
    st.Mark2Coverage = otl.buildCoverage(base_marks, gm)
    st.ClassCount = 2
    st.Mark1Array = otl.buildMarkArray(marks, gm)
    arr = ot.Mark2Array()
    arr.Mark2Record = []
    for g in st.Mark2Coverage.glyphs:
        rec = ot.Mark2Record()
        rec.Mark2Anchor = [base_marks[g].get(i) for i in range(2)]
        arr.Mark2Record.append(rec)
    arr.Mark2Count = len(arr.Mark2Record)
    st.Mark2Array = arr
    return st


def letter_ink(font, name):
    """Boolean ink mask of a glyph at 1/4 scale."""
    from PIL import Image, ImageDraw
    import numpy as np
    gs = font.getGlyphSet()
    rec = DecomposingRecordingPen(gs)
    gs[name].draw(rec)
    contours, cur, pos = [], [], None
    for op, args in rec.value:
        if op == 'moveTo':
            cur = [args[0]]
            pos = args[0]
        elif op == 'lineTo':
            cur.append(args[0])
            pos = args[0]
        elif op == 'qCurveTo':
            offs = list(args[:-1])
            end = args[-1]
            p0 = pos
            for k, o in enumerate(offs):
                if k == len(offs) - 1:
                    nxt = end
                else:
                    nxt = ((o[0] + offs[k + 1][0]) / 2, (o[1] + offs[k + 1][1]) / 2)
                for t in range(1, 7):
                    u = t / 6
                    cur.append(((1 - u) ** 2 * p0[0] + 2 * (1 - u) * u * o[0] + u * u * nxt[0],
                                (1 - u) ** 2 * p0[1] + 2 * (1 - u) * u * o[1] + u * u * nxt[1]))
                p0 = nxt
            pos = end
        elif op in ('closePath', 'endPath'):
            if len(cur) > 2:
                contours.append(cur)
            cur = []
    X0, Y0, W, H = -300, -700, 1400, 2200
    sc = 0.25
    m = np.zeros((int(H * sc), int(W * sc)), bool)
    for ct in contours:
        t = Image.new('1', (m.shape[1], m.shape[0]), 0)
        ImageDraw.Draw(t).polygon([((x - X0) * sc, (H - (y - Y0)) * sc) for x, y in ct], fill=1)
        m ^= np.array(t)   # even-odd: outer contours add, holes cancel, whatever the winding
    return m, X0, Y0, H, sc


def band_clear(ink, x0, x1, y0, y1):
    m, X0, Y0, H, sc = ink
    c0, c1 = int((x0 - X0) * sc), int((x1 - X0) * sc) + 1
    r0, r1 = int((H - (y1 - Y0)) * sc), int((H - (y0 - Y0)) * sc) + 1
    if c1 < 0 or r1 < 0:
        return True
    return not m[max(r0, 0):r1, max(c0, 0):c1].any()


def clear_dx(ink, cx, hw, y0, y1):
    for d in range(0, 400, 10):
        for sgn in ((1, -1) if d else (1,)):
            dx = sgn * d
            if band_clear(ink, cx + dx - hw, cx + dx + hw, y0, y1):
                return dx
    return 0


def dot_boxes(font):
    """Boxes of the shin/sin dots on shin, as the font's own mark positioning places them."""
    import io
    import uharfbuzz as hb
    buf = io.BytesIO()
    font.save(buf)
    hf = hb.Font(hb.Face(hb.Blob(buf.getvalue())))
    cm = font.getBestCmap()
    out = {}
    for cp in DOTS:
        b = hb.Buffer()
        b.add_str(chr(0x5e9) + chr(cp))
        b.guess_segment_properties()
        hb.shape(hf, b, {})
        x = 0
        for i, p in zip(b.glyph_infos, b.glyph_positions):
            n = hf.glyph_to_string(i.codepoint)
            if n == cm[cp]:
                g = font['glyf'][n]
                out[cp] = (g.xMin + x + p.x_offset, g.yMin + p.y_offset,
                           g.xMax + x + p.x_offset, g.yMax + p.y_offset)
            x += p.x_advance
    return out


def build_gpos(font, new_marks):
    c = font.getBestCmap()
    gm = {n: i for i, n in enumerate(font.getGlyphOrder())}
    gpos = font['GPOS'].table
    letters = [c[cp] for cp in range(0x5d0, 0x5eb)]
    lb = {n: glyph_bounds(font, n) for n in letters}
    inks = {n: letter_ink(font, n) for n in letters}

    def level_above(b):
        return (LEVEL_TOP if b[3] <= 720 else b[3]) + ABOVE_GAP

    def level_below(b):
        # one level for everyone; letters that dip just under the baseline (shin, samekh) get a
        # small extra gap; real descenders (qof, final letters) keep the level and the vowel
        # moves sideways instead (see the vowel-only rules below)
        if b[1] > -75 or b[1] <= -250:
            return LEVEL_BASE - 70
        return b[1] - 25

    T_ABOVE_Y = LEVEL_TOP + ABOVE_GAP
    T_BELOW_Y = LEVEL_BASE - 70

    t_above, t_below = [], []
    for cp in list(range(0x591, 0x5b0)) + [0x5bd, 0x5bf, 0x5c4, 0x5c5]:
        if cp not in c:
            continue
        b = glyph_bounds(font, c[cp])
        if b is None:
            continue
        (t_above if (b[1] + b[3]) / 2 > 250 else t_below).append(cp)
    below_v = [cp for cp in BELOW_VOWELS if cp in c]
    above_v = [cp for cp in ABOVE_VOWELS if cp in c]

    def mark_info(cp, cls):
        n = c[cp]
        b = glyph_bounds(font, n)
        xc = (b[0] + b[2]) // 2
        anchor = otl.buildAnchor(xc, b[1] if cls == 'above' else b[3])
        return n, b, (CID[cls], anchor)

    subtables = []
    tdx = {}
    groups = {}
    for cps, cls in ((below_v, 'below'), (above_v, 'above')):
        for cp in cps:
            if cp not in c:
                continue
            n, b, ma = mark_info(cp, cls)
            groups.setdefault(REL_X.get(cp, 0.5), {})[n] = ma
    for rel, mk in sorted(groups.items()):
        bases = {}
        for n in letters:
            b = lb[n]
            r_eff = HOLAM_ON_LAMED if (n == 'uni05DC' and rel == REL_X[0x5b9]) else rel
            x = round(b[0] + r_eff * (b[2] - b[0]))
            ya = LEVEL_TOP + ABOVE_GAP if r_eff != rel else level_above(b)
            bases[n] = {CID['above']: otl.buildAnchor(x, ya),
                        CID['below']: otl.buildAnchor(x, level_below(b))}
        subtables.append(otl.buildMarkBasePosSubtable(mk, bases, gm))
    # te'amim: same height on every letter, nudged sideways only to clear the letter's own ink
    for cps, cls in ((t_above, 'above'), (t_below, 'below')):
        for cp in cps:
            n, b, ma = mark_info(cp, cls)
            hw = (b[2] - b[0]) // 2 + 15
            h = b[3] - b[1]
            bases = {}
            for L in letters:
                lbb = lb[L]
                cx = (lbb[0] + lbb[2]) // 2
                if cls == 'above':
                    y0, y1, y = T_ABOVE_Y + 8, T_ABOVE_Y + h, T_ABOVE_Y
                else:
                    y0, y1, y = T_BELOW_Y - h, T_BELOW_Y - 8, T_BELOW_Y
                dx = clear_dx(inks[L], cx, hw, y0, y1)
                lift = 0
                while (not band_clear(inks[L], cx + dx - hw, cx + dx + hw, y0 + lift, y1 + lift)
                       and abs(lift) < 400):
                    lift += 20 if cls == 'above' else -20
                y += lift
                tdx[(L, cp)] = (cx + dx, y)
                bases[L] = {CID[cls]: otl.buildAnchor(cx + dx, y)}
            subtables.append(otl.buildMarkBasePosSubtable({n: ma}, bases, gm))

    # mark-to-mark only between two te'amim on the same side
    mm_marks, mm_base = {}, {}
    for cps, cls in ((t_above, 'above'), (t_below, 'below')):
        for cp in cps:
            n, b, ma = mark_info(cp, cls)
            mm_marks[n] = ma
            xc = (b[0] + b[2]) // 2
            y = b[3] + STACK_GAP if cls == 'above' else b[1] - STACK_GAP
            mm_base.setdefault(n, {})[CID[cls]] = otl.buildAnchor(xc, y)
    mm = build_mark_mark(mm_marks, mm_base, gm)

    lookups = gpos.LookupList.Lookup
    i_mb = len(lookups)
    lookups.append(otl.buildLookup(subtables, flags=0))
    i_mm = len(lookups)
    lookups.append(otl.buildLookup([mm], flags=0))

    # vowel/dot + te'am on the same side: solved per letter against the real letter ink,
    # the other marks and the shin/sin dots; the te'am prefers the left of the vowel
    gdef = font['GDEF'].table
    sets = gdef.MarkGlyphSetsDef
    single = {}
    allm = sorted({c[cp] for cp in below_v + above_v + t_above + t_below + DOTS if cp in c},
                  key=lambda n: gm[n])

    def shift_lookup(v):
        if v not in single:
            st = otl.buildSinglePosSubtable(
                {n: otl.buildValue({'XPlacement': v}) for n in allm}, gm)
            single[v] = len(lookups)
            lookups.append(otl.buildLookup([st], flags=0))
        return single[v]

    dot_box = dot_boxes(font)
    GAP = 30

    def q(v):
        return int(round(v / 20.0)) * 20

    def bbox_at(b, xc_target, y0):
        xc = (b[0] + b[2]) // 2
        return (xc_target + b[0] - xc, y0, xc_target + b[2] - xc, y0 + b[3] - b[1])

    def y_near(a, b):
        return a[1] < b[3] + 20 and b[1] < a[3] + 20

    def x_apart(a, b, dxa, dxb):
        return a[2] + dxa + GAP <= b[0] + dxb or b[2] + dxb + GAP <= a[0] + dxa

    def te_box(L, side, t):
        bt = glyph_bounds(font, c[t])
        tx, ty = tdx[(L, t)]
        xc = (bt[0] + bt[2]) // 2
        h = bt[3] - bt[1]
        y0 = ty - h if side == 'below' else ty
        return (tx + bt[0] - xc, y0, tx + bt[2] - xc, y0 + h)

    def vowel_box(L, side, v):
        lbb = lb[L]
        bv = glyph_bounds(font, c[v])
        rel = REL_X.get(v, 0.5)
        if L == 'uni05DC' and rel == REL_X[0x5b9]:
            rel = HOLAM_ON_LAMED
        vx = round(lbb[0] + rel * (lbb[2] - lbb[0]))
        if side == 'above':
            if rel != REL_X.get(v, 0.5):
                return bbox_at(bv, vx, LEVEL_TOP + ABOVE_GAP)
            return bbox_at(bv, vx, level_above(lbb))
        return bbox_at(bv, vx, level_below(lbb) - (bv[3] - bv[1]))

    def solve(L, side, v, dot, t):
        ink, lbb = inks[L], lb[L]
        tb = te_box(L, side, t)
        vb = vowel_box(L, side, v) if v is not None else None
        db = dot_box.get(dot) if (dot and L == SHIN) else None
        nom_v = nom_t = 0
        if vb is not None:
            need = max(0, ((vb[2] - vb[0]) + (tb[2] - tb[0])) / 2 + 30
                       + (0.5 - REL_X.get(v, 0.5)) * (lbb[2] - lbb[0]))
            nom_v, nom_t = 0.4 * need, -0.6 * need
        best = None
        for dt in range(-700, 501, 20):
            if not band_clear(ink, tb[0] + dt - INK_PAD, tb[2] + dt + INK_PAD, tb[1], tb[3]):
                continue
            if db is not None and y_near(tb, db) and not x_apart(tb, db, dt, 0):
                continue
            for dv in (range(-300, 501, 20) if vb is not None else (0,)):
                if vb is not None:
                    if not band_clear(ink, vb[0] + dv - INK_PAD, vb[2] + dv + INK_PAD, vb[1], vb[3]):
                        continue
                    if y_near(tb, vb) and not x_apart(tb, vb, dt, dv):
                        continue
                    if db is not None and y_near(vb, db) and not x_apart(vb, db, dv, 0):
                        continue
                cost = abs(dv - nom_v) + abs(dt - nom_t)
                if vb is not None and y_near(tb, vb) and tb[0] + dt > vb[0] + dv:
                    cost += 250
                if best is None or cost < best[0]:
                    best = (cost, dv, dt)
        if best is None:
            return 0, 0
        return q(best[1]), q(best[2])

    def solve_v(L, v):
        """Sideways nudge of a lone below-vowel clear of the letter's ink (descenders)."""
        vb = vowel_box(L, 'below', v)
        best = None
        for dv in range(-400, 401, 20):
            if band_clear(inks[L], vb[0] + dv - INK_PAD, vb[2] + dv + INK_PAD, vb[1], vb[3]):
                if best is None or abs(dv) < abs(best):
                    best = dv
        return q(best) if best is not None else 0

    def solve_vd(L, v, dot):
        vb = vowel_box(L, 'above', v)
        db = dot_box[dot]
        for dv in range(0, 501, 20):
            if band_clear(inks[L], vb[0] + dv, vb[2] + dv, vb[1], vb[3]) and (
                    not y_near(vb, db) or x_apart(vb, db, dv, 0)):
                return q(dv)
        return 0

    ctx_lookups = []
    for vs, ts, side in ((below_v, t_below, 'below'), (above_v, t_above, 'above')):
        rules = {}
        for L in letters:
            combos = []
            for t in ts:
                combos.append((None, None, t))
                for v in vs:
                    combos.append((v, None, t))
            if side == 'below':
                for v in vs:
                    dv = solve_v(L, v)
                    if dv:
                        combos.append((v, None, None))
            if side == 'above' and L == SHIN:
                for dot in DOTS:
                    for t in ts:
                        combos.append((None, dot, t))
                        for v in vs:
                            combos.append((v, dot, t))
                    for v in vs:
                        combos.append((v, dot, None))
            for v, dot, t in combos:
                if v is None and dot is None:
                    continue
                if t is None and dot is None:
                    shifts = {v: solve_v(L, v)}
                elif t is None:
                    shifts = {v: solve_vd(L, v, dot)}
                else:
                    dv, dt = solve(L, side, v, dot, t)
                    shifts = {t: dt}
                    if v is not None:
                        shifts[v] = dv
                key = tuple(sorted(shifts.items()))
                # shapers differ on whether the dot comes before or after the vowel
                for order in ((v, dot, t), (dot, v, t)) if (v and dot) else ((v, dot, t),):
                    seq = tuple(x for x in order if x is not None)
                    rules.setdefault((seq, key), []).append(L)
        sts = []
        for (seq, shifts), gl in sorted(rules.items(), key=lambda kv: -len(kv[0][0])):
            sh = dict(shifts)
            if side == 'above' and not any(x in DOTS for x in seq) and not any(sh.values()):
                continue
            st = ot.ChainContextPos()
            st.Format = 3
            st.BacktrackGlyphCount = 1
            st.BacktrackCoverage = [otl.buildCoverage(sorted(gl, key=lambda n: gm[n]), gm)]
            st.InputGlyphCount = len(seq)
            st.InputCoverage = [otl.buildCoverage([c[x]], gm) for x in seq]
            st.LookAheadGlyphCount = 0
            st.LookAheadCoverage = []
            recs = []
            for i, x in enumerate(seq):
                d = sh.get(x, 0)
                if d:
                    r = ot.PosLookupRecord()
                    r.SequenceIndex = i
                    r.LookupListIndex = shift_lookup(d)
                    recs.append(r)
            st.PosLookupRecord = recs
            st.PosCount = len(recs)
            sts.append(st)
        if sts:
            members = {c[x] for x in vs + ts}
            if side == 'above':
                members |= {c[x] for x in DOTS if x in c}
            cov = otl.buildCoverage(sorted(members, key=lambda n: gm[n]), gm)
            sets.Coverage.append(cov)
            sets.MarkSetCount = len(sets.Coverage)
            ctx_lookups.append(len(lookups))
            lookups.append(otl.buildLookup(sts, flags=0x10, markFilterSet=len(sets.Coverage) - 1))
    # neighbouring letters whose below-vowels would touch: widen the second letter's advance
    # (HarfBuzz zeroes mark advances after GPOS, and in RTL a letter's advance spaces it from the
    # letter drawn after it, i.e. the logically earlier one)
    adv_lookups = []
    vset = [c[v] for v in below_v]
    vinfo = {}
    for v in below_v:
        bv = glyph_bounds(font, c[v])
        vinfo[v] = (bv[2] - bv[0])
    advs = {L: font['hmtx'][L][0] for L in letters}
    vcls = {v: (0 if vinfo[v] <= 140 else 1 if vinfo[v] <= 300 else 2 if vinfo[v] <= 380 else 3)
            for v in below_v}
    NCLS = 4
    cls_w = {k: max([vinfo[v] for v in below_v if vcls[v] == k] or [0]) for k in range(NCLS)}
    cls_v = {k: [v for v in below_v if vcls[v] == k] for k in range(NCLS)}
    vpos = {}
    for L in letters:
        for v in below_v:
            w = lb[L][2] - lb[L][0]
            vpos[(L, v)] = round(lb[L][0] + REL_X.get(v, 0.5) * w) + solve_v(L, v)

    def b1(L, k):
        return min(vpos[(L, v)] for v in cls_v[k]) - cls_w[k] / 2

    def a2(L, k):
        return max(vpos[(L, v)] for v in cls_v[k]) - advs[L] + cls_w[k] / 2

    rules = {}
    for k1 in range(NCLS):
        for k2 in range(NCLS):
            if not cls_v[k1] or not cls_v[k2]:
                continue
            buck = {}
            for L1 in letters:
                for L2 in letters:
                    pass
            g1, g2 = {}, {}
            for L in letters:
                g1.setdefault(round(b1(L, k1) / 40), []).append(L)
                g2.setdefault(round(a2(L, k2) / 40), []).append(L)
            for ls1 in g1.values():
                lo = min(b1(L, k1) for L in ls1)
                for ls2 in g2.values():
                    hi = max(a2(L, k2) for L in ls2)
                    extra = int(-(-max(0, hi + VOWEL_GAP - lo) // 10) * 10)
                    if extra:
                        rules.setdefault((k1, k2, tuple(sorted(ls2)), extra), []).extend(ls1)
    if rules:
        sets.Coverage.append(otl.buildCoverage(sorted(vset, key=lambda n: gm[n]), gm))
        sets.MarkSetCount = len(sets.Coverage)
        advval = {}
        sts = []
        for (k1, k2, ls2, extra), ls1 in sorted(rules.items()):
            if extra not in advval:
                st = otl.buildSinglePosSubtable(
                    {n: otl.buildValue({'XAdvance': extra}) for n in letters}, gm)
                advval[extra] = len(lookups)
                lookups.append(otl.buildLookup([st], flags=0))
            st = ot.ChainContextPos()
            st.Format = 3
            st.BacktrackGlyphCount = 0
            st.BacktrackCoverage = []
            st.InputGlyphCount = 4
            st.InputCoverage = [otl.buildCoverage(sorted(ls1, key=lambda n: gm[n]), gm),
                                otl.buildCoverage(sorted((c[v] for v in cls_v[k1]), key=lambda n: gm[n]), gm),
                                otl.buildCoverage(sorted(ls2, key=lambda n: gm[n]), gm),
                                otl.buildCoverage(sorted((c[v] for v in cls_v[k2]), key=lambda n: gm[n]), gm)]
            st.LookAheadGlyphCount = 0
            st.LookAheadCoverage = []
            r = ot.PosLookupRecord()
            r.SequenceIndex = 2
            r.LookupListIndex = advval[extra]
            st.PosLookupRecord = [r]
            st.PosCount = 1
            sts.append(st)
        print('adv rules', len(sts))
        adv_lookups.append(len(lookups))
        lookups.append(otl.buildLookup(sts, flags=0x10, markFilterSet=len(sets.Coverage) - 1))
    gpos.LookupList.LookupCount = len(lookups)
    for fr in gpos.FeatureList.FeatureRecord:
        if fr.FeatureTag == 'mark':
            fr.Feature.LookupListIndex += [i_mb] + ctx_lookups + adv_lookups
            fr.Feature.LookupCount = len(fr.Feature.LookupListIndex)
        elif fr.FeatureTag == 'mkmk':
            fr.Feature.LookupListIndex.append(i_mm)
            fr.Feature.LookupCount = len(fr.Feature.LookupListIndex)
    gd = gdef.GlyphClassDef.classDefs
    for n in new_marks:
        gd[n] = 3
    for n in ('maqafhb', 'gereshhb', 'gershayimhb', 'sofpasuqhb', 'uni05C0', 'uni05C6'):
        if n in gm:
            gd[n] = 1


def set_names(font, style, wclass):
    fam = 'Mekorot'
    ribbi = style in ('Regular', 'Bold')
    nt = font['name']
    for nid in (0, 1, 2, 3, 4, 6, 16, 17, 21, 22):
        nt.removeNames(nameID=nid)
    nt.setName('Copyright 2021 The Mekorot Project Authors (https://github.com/googlefonts/mekorot). '
               'Niqqud and teamim glyphs: Copyright 2022 The Noto Project Authors '
               '(https://github.com/notofonts/hebrew), from Noto Rashi Hebrew.', 0, 3, 1, 0x409)
    full = fam if style == 'Regular' else '%s %s' % (fam, style)
    ps = '%s-%s' % (fam, style)
    nt.setName(fam if ribbi else '%s %s' % (fam, style), 1, 3, 1, 0x409)
    nt.setName(style if ribbi else 'Regular', 2, 3, 1, 0x409)
    nt.setName('%s;%s' % (ps, 'otzaria-fork'), 3, 3, 1, 0x409)
    nt.setName(full if style != 'Regular' else 'Mekorot Regular', 4, 3, 1, 0x409)
    nt.setName(ps, 6, 3, 1, 0x409)
    if not ribbi:
        nt.setName(fam, 16, 3, 1, 0x409)
        nt.setName(style, 17, 3, 1, 0x409)
    os2 = font['OS/2']
    os2.usWeightClass = wclass
    sel = os2.fsSelection & ~(1 | 32 | 64)
    sel |= 32 if style == 'Bold' else 0
    sel |= 64 if style == 'Regular' else 0
    if style not in ('Bold', 'Regular'):
        sel |= 64
    os2.fsSelection = sel
    font['head'].macStyle = 1 if style == 'Bold' else 0


def sync_side_bearings(font):
    """FreeType positions an outline by hmtx lsb, so lsb must equal the real xMin."""
    glyf, hmtx = font['glyf'], font['hmtx']
    for n in font.getGlyphOrder():
        g = glyf[n]
        if g.numberOfContours != 0:
            g.recalcBounds(glyf)
            hmtx[n] = (hmtx[n][0], g.xMin)


def build(style, wght, wclass):
    if wght is None:
        font = extrapolate_light()
        mark_w = 300
    else:
        font = instancer.instantiateVariableFont(TTFont(VAR), {'wght': wght})
        mark_w = wght
    for t in ('STAT', 'avar', 'fvar', 'gvar', 'HVAR', 'MVAR'):
        if t in font:
            del font[t]
    fix_spacing_and_punct(font)
    new_marks = add_marks(font, mark_w)
    build_gpos(font, new_marks)
    set_names(font, style, wclass)
    sync_side_bearings(font)
    # win metrics bound the clip box on GDI; the tallest stack (letter+vowel+te'am) reaches ~1170/-735.
    # hhea/typo stay 900/-300 so line spacing matches the other bundled fonts.
    font['OS/2'].usWinAscent, font['OS/2'].usWinDescent = 1200, 760
    path = '%s/Mekorot-%s.ttf' % (OUT, style)
    font.save(path)
    print('built', path, 'new marks:', len(new_marks))


if __name__ == '__main__':
    only = sys.argv[4:] or None
    for style, wght, wclass in WEIGHTS:
        if only and style not in only:
            continue
        build(style, wght, wclass)
