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
BRACKET_PAD = 30   # extra space on each side of brackets


def shift_glyph_x(font, name, dx):
    g = font['glyf'][name]
    if g.numberOfContours > 0:
        g.coordinates.translate((dx, 0))
    elif g.isComposite():
        for comp in g.components:
            comp.x += dx
    g.recalcBounds(font['glyf'])


def pad_punctuation(font):
    c = font.getBestCmap()
    hmtx = font['hmtx']
    for cp in (0x2e, 0x2c, 0x3a, 0x3b, 0x21, 0x3f, 0x5c3):
        adv, lsb = hmtx[c[cp]]
        hmtx[c[cp]] = (adv + TRAIL_PAD, lsb)
    for cp in (0x28, 0x29, 0x5b, 0x5d, 0x7b, 0x7d):
        n = c[cp]
        adv, lsb = hmtx[n]
        shift_glyph_x(font, n, BRACKET_PAD)
        hmtx[n] = (adv + 2 * BRACKET_PAD, lsb + BRACKET_PAD)


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
    pad_punctuation(font)


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
BELOW_VOWELS = [0x5b0, 0x5b1, 0x5b2, 0x5b3, 0x5b4, 0x5b5, 0x5b6, 0x5b7, 0x5b8, 0x5bb, 0x5c7]
ABOVE_VOWELS = [0x5b9, 0x5ba]
REL_X = {0x5b9: 0.22, 0x5ba: 0.22, 0x5bb: 0.42, 0x5bd: 0.30}
LEVEL_TOP = 700          # normal letters share one height level above
LEVEL_BASE = -30         # ... and one level below


def scale_glyph(font, name, k):
    g = font['glyf'][name]
    if g.numberOfContours > 0:
        g.coordinates.scale((k, k))
        g.recalcBounds(font['glyf'])


def add_marks(font, wght):
    noto = noto_instance(wght + 250)
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
    ink = Image.new('1', (int(W * sc), int(H * sc)), 0)
    holes = Image.new('1', ink.size, 0)
    for ct in contours:
        n = len(ct)
        area = sum(ct[k][0] * ct[(k + 1) % n][1] - ct[(k + 1) % n][0] * ct[k][1] for k in range(n))
        pts = [((x - X0) * sc, (H - (y - Y0)) * sc) for x, y in ct]
        ImageDraw.Draw(holes if area > 0 else ink).polygon(pts, fill=1)
    m = np.array(ink) & ~np.array(holes)
    return m, X0, Y0, H, sc


def band_clear(ink, x0, x1, y0, y1):
    m, X0, Y0, H, sc = ink
    c0, c1 = int((x0 - X0) * sc), int((x1 - X0) * sc) + 1
    r0, r1 = int((H - (y1 - Y0)) * sc), int((H - (y0 - Y0)) * sc) + 1
    if c0 < 0 or r0 < 0:
        return True
    return not m[max(r0, 0):r1, max(c0, 0):c1].any()


def clear_dx(ink, cx, hw, y0, y1):
    for d in range(0, 400, 10):
        for sgn in ((1, -1) if d else (1,)):
            dx = sgn * d
            if band_clear(ink, cx + dx - hw, cx + dx + hw, y0, y1):
                return dx
    return 0


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
        return (LEVEL_BASE - 70) if b[1] > -50 else (b[1] - 110)

    T_ABOVE_Y = LEVEL_TOP + ABOVE_GAP
    T_BELOW_Y = LEVEL_BASE - 70

    t_above, t_below = [], []
    for cp in list(range(0x591, 0x5b0)) + [0x5bf, 0x5c4, 0x5c5]:
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
    groups = {}
    for cps, cls in ((below_v + [0x5bd], 'below'), (above_v, 'above')):
        for cp in cps:
            if cp not in c:
                continue
            n, b, ma = mark_info(cp, cls)
            groups.setdefault(REL_X.get(cp, 0.5), {})[n] = ma
    for rel, mk in sorted(groups.items()):
        bases = {}
        for n in letters:
            b = lb[n]
            x = round(b[0] + rel * (b[2] - b[0]))
            bases[n] = {CID['above']: otl.buildAnchor(x, level_above(b)),
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

    # vowel + te'am on the same side: the te'am goes to the right of the vowel, the vowel nudges left
    gdef = font['GDEF'].table
    sets = gdef.MarkGlyphSetsDef
    single = {}
    allm = sorted({c[cp] for cp in below_v + above_v + t_above + t_below}, key=lambda n: gm[n])

    def shift_lookup(v):
        if v not in single:
            st = otl.buildSinglePosSubtable(
                {n: otl.buildValue({'XPlacement': v}) for n in allm}, gm)
            single[v] = len(lookups)
            lookups.append(otl.buildLookup([st], flags=0))
        return single[v]

    def q(v):
        return int(round(v / 20.0)) * 20

    ctx_lookups = []
    wgroups = {}
    for L in letters:
        w = lb[L][2] - lb[L][0]
        wgroups.setdefault(int(round(w / 50.0)) * 50, []).append((L, w))
    for vs, ts, side in ((below_v, t_below, 'below'), (above_v, t_above, 'above')):
        sts = []
        if side == 'below':
            groups_ = [(None, 0)]
        else:
            groups_ = [(sorted(x[0] for x in g), sum(x[1] for x in g) / len(g))
                       for g in wgroups.values()]
        for gl, gw in groups_:
            for v in vs:
                bv = glyph_bounds(font, c[v])
                wv = bv[2] - bv[0]
                for t in ts:
                    bt = glyph_bounds(font, c[t])
                    wt = bt[2] - bt[0]
                    need = (wv + wt) / 2 + 30
                    need = max(0, need + (0.5 - REL_X.get(v, 0.5)) * (gw or 380))
                    dv, dt = q(0.4 * need), -q(0.6 * need)
                    if not dv and not dt:
                        continue
                    if gl is None:
                        st = ot.ContextPos()
                        st.Format = 3
                        st.GlyphCount = 2
                        st.Coverage = [otl.buildCoverage([c[v]], gm),
                                       otl.buildCoverage([c[t]], gm)]
                    else:
                        st = ot.ChainContextPos()
                        st.Format = 3
                        st.BacktrackGlyphCount = 1
                        st.BacktrackCoverage = [otl.buildCoverage(
                            sorted(gl, key=lambda n: gm[n]), gm)]
                        st.InputGlyphCount = 2
                        st.InputCoverage = [otl.buildCoverage([c[v]], gm),
                                            otl.buildCoverage([c[t]], gm)]
                        st.LookAheadGlyphCount = 0
                        st.LookAheadCoverage = []
                    recs = []
                    for idx, d in ((0, dv), (1, dt)):
                        if d:
                            r = ot.PosLookupRecord()
                            r.SequenceIndex = idx
                            r.LookupListIndex = shift_lookup(d)
                            recs.append(r)
                    st.PosLookupRecord = recs
                    st.PosCount = len(recs)
                    sts.append(st)
        if sts:
            cov = otl.buildCoverage(sorted({c[x] for x in vs + ts}, key=lambda n: gm[n]), gm)
            sets.Coverage.append(cov)
            sets.MarkSetCount = len(sets.Coverage)
            ctx_lookups.append(len(lookups))
            lookups.append(otl.buildLookup(sts, flags=0x10, markFilterSet=len(sets.Coverage) - 1))
    gpos.LookupList.LookupCount = len(lookups)
    for fr in gpos.FeatureList.FeatureRecord:
        if fr.FeatureTag == 'mark':
            fr.Feature.LookupListIndex += [i_mb] + ctx_lookups
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
    path = '%s/Mekorot-%s.ttf' % (OUT, style)
    font.save(path)
    print('built', path, 'new marks:', len(new_marks))


if __name__ == '__main__':
    only = sys.argv[4:] or None
    for style, wght, wclass in WEIGHTS:
        if only and style not in only:
            continue
        build(style, wght, wclass)
