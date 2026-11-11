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
        if x.isComposite() or x.numberOfContours != 0:
            ca, _, _ = x.getCoordinates(ga)
            cb, _, _ = y.getCoordinates(gb)
            new = [(round(p - LIGHT_K * (q - p)), round(r - LIGHT_K * (s - r)))
                   for (p, r), (q, s) in zip(ca, cb)]
            if x.isComposite():
                for i, comp in enumerate(x.components):
                    comp.x, comp.y = new[i]
            else:
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


def add_marks(font, wght):
    noto = noto_instance(wght)
    c = font.getBestCmap()
    spacing = {0x5c0, 0x5c6}          # paseq, nun hafukha: regular glyphs
    new_marks = []
    for cp in range(0x591, 0x5c8):
        if cp in c or cp in (0x5be, 0x5c3):
            continue
        if cp not in noto.getBestCmap():
            continue
        g, adv = noto_glyph_as_tt(noto, cp)
        name = 'uni%04X' % cp
        add_glyph(font, cp, name, g, adv if cp in spacing else 0)
        if cp not in spacing:
            new_marks.append(name)
    # classify all marks (existing + new) by outline height
    all_marks = [c[cp] for cp in range(0x591, 0x5c8)
                 if cp in c and cp not in spacing and cp not in (0x5be, 0x5c3)]
    cls = {}
    for n in all_marks:
        b = glyph_bounds(font, n)
        if b is None:
            continue
        mid = (b[1] + b[3]) / 2
        cls[n] = 'above' if mid > 250 else ('below' if mid < 60 else 'inside')
    return new_marks, cls


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


def build_gpos(font, new_marks, cls):
    c = font.getBestCmap()
    gm = {n: i for i, n in enumerate(font.getGlyphOrder())}
    gpos = font['GPOS'].table
    base_names = [c[cp] for cp in range(0x5d0, 0x5eb)]
    # base-mark anchors on letters
    bases = {}
    for n in base_names:
        b = glyph_bounds(font, n)
        if b is None:
            continue
        xc = (b[0] + b[2]) // 2
        bases[n] = {
            CID['above']: otl.buildAnchor(xc, b[3] + ABOVE_GAP),
            CID['below']: otl.buildAnchor(xc, min(b[1], 0) - BELOW_GAP),
        }
    marks = {}
    for n in new_marks:
        k = cls.get(n)
        if k not in ('above', 'below'):
            continue
        b = glyph_bounds(font, n)
        xc = (b[0] + b[2]) // 2
        marks[n] = (CID[k], otl.buildAnchor(xc, b[1] if k == 'above' else b[3]))
    mb = otl.buildMarkBasePosSubtable(
        {n: (k, a) for n, (k, a) in marks.items()}, bases, gm)
    # mark-to-mark: any mark (existing or new) can carry a new mark
    mm_marks, mm_base = {}, {}
    for n, k in cls.items():
        if k not in ('above', 'below'):
            continue
        b = glyph_bounds(font, n)
        xc = (b[0] + b[2]) // 2
        if n in marks:
            mm_marks[n] = marks[n]
        mm_base[n] = {
            CID['above']: otl.buildAnchor(xc, b[3] + STACK_GAP),
            CID['below']: otl.buildAnchor(xc, b[1] - STACK_GAP),
        }
    mm = build_mark_mark(mm_marks, mm_base, gm)
    lookups = gpos.LookupList.Lookup
    i_mb = len(lookups)
    lookups.append(otl.buildLookup([mb], flags=0))
    i_mm = len(lookups)
    lookups.append(otl.buildLookup([mm], flags=0))
    gpos.LookupList.LookupCount = len(lookups)
    for fr in gpos.FeatureList.FeatureRecord:
        if fr.FeatureTag == 'mark':
            fr.Feature.LookupListIndex.append(i_mb)
            fr.Feature.LookupCount = len(fr.Feature.LookupListIndex)
        elif fr.FeatureTag == 'mkmk':
            fr.Feature.LookupListIndex.append(i_mm)
            fr.Feature.LookupCount = len(fr.Feature.LookupListIndex)
    # GDEF: mark class
    gd = font['GDEF'].table.GlyphClassDef.classDefs
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
    new_marks, cls = add_marks(font, mark_w)
    build_gpos(font, new_marks, cls)
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
