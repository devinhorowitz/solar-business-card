#!/usr/bin/env python3
"""Engraving, spin 3. The PART changed under the first two spins -- this one catches up.

Spin 1 asked which CUTTER, spin 2 which COMPOSITION. Both were computed against the back
as it stood then: FIN_PITCH = 3.20 mm and FIN_VALLEY = 0.30 mm. On 2026-07-30 the fin
fields were reworked into fine reeding (pitch 1.392, derived by exact closure) and the
valleys deepened to 0.60. That did three things to the engraving question, and each one
is a variant family here:

  * It KILLED G's premise. Baselines on the fin pitch only work while the pitch clears a
    cap height; 1.392 mm is below every cap in the contact block, so no line of type can
    sit on every pitch line any more. O re-founds the idea on the only grid that survives:
    type takes TWO units.
  * It DOUBLED the depth ceiling. H spent 0.30/0.15 because 0.30 was the budget; the
    honest re-ask (L) finds the budget is no longer the binding constraint -- the tool is.
    And F's registered relief (M) can now take its floor to the fin valleys' own 0.60,
    where the recess leaves exactly the 0.40 web the part already stands on everywhere.
  * It turned the texture into a possible GROUND. At 3.2 mm the fins were stripes; at
    1.392 they are reeding -- fine enough to run *through* the art band and carry flush
    information as islands, the way the pour wraps a boss (K, N).

The reeding transplanted here is fit_rules' own pour, re-closed over the studies' panel:
same rib (FIN_RIB_W), same groove floor (FIN_GROOVE_MIN), same min-width opening
(_BACK_CUT_R), same boss clearance around every island (FIN_BOSS_CLR). The panel closes
its own span -- N ribs, N-1 grooves and two equal gutters consume it exactly -- and lands
at pitch 1.405 vs the fields' 1.392: the same texture to the eye, cut by the same O0.6.

One honesty note on K and N: an engraving only removes metal, so the band's ribs sit AT
the art-field surface -- 0.10 below the fin fields' rib tops, which stand proud. If a
reeded variant ships, the band joins the generator's CAD (it is geometry, not a mark) and
its ribs can go proud to match; the studies model the subtractive version.

Depths, budget, tool models, the art rect, the render machinery: imported from spin 1
unchanged. Layout primitives and the tapered cutter: from spin 2.
"""
from __future__ import annotations

import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))     # enclosure/, for fit_rules
sys.path.insert(0, HERE)

import numpy as np
import shapely.affinity as aff
from PIL import Image, ImageDraw
from shapely.geometry import LineString, Polygon, box
from shapely.ops import unary_union

import spin1_cutters as E
import spin2_composition as C
import fit_rules as fr

OUT = E.OUT
PX = E.PX
CX, CY, ART = E.CX, E.CY, E.ART
LEFT = C.LEFT

# the panel every prior panel variant used (spin 1 C/D, spin 2 I) -- 37.0 x 26.1
PANEL = (6.9, 31.4, 43.9, 57.5)
PANEL_R = 1.6


def _rounded(rect, r):
    return fr._dedupe(box(*rect).buffer(-r).buffer(r * 2).intersection(box(*rect)))


# --- the pour, transplanted ---------------------------------------------------------

def reeding(blockers=None):
    """fit_rules' fin pour, re-closed over the studies' panel.

    Same derivation, one difference: the fields anchor their grid on the mid-boss lines
    (an asymmetric closure -- flank ON the line, gutter at the far edge), but the band
    has no anchor line, so it closes SYMMETRICALLY: N ribs, N-1 grooves and two equal
    gutters consume the span, every gap identical. The erosion carries fit_rules' own
    EPS backoff -- the outermost flank sits exactly on the eroded boundary, and an
    exact-boundary intersection is numerically empty.
    """
    panel = _rounded(PANEL, PANEL_R)
    y0, y1 = PANEL[1], PANEL[3]
    span = y1 - y0
    rw, gmin = fr.FIN_RIB_W, fr.FIN_GROOVE_MIN
    n = int((span - gmin) // (rw + gmin))
    g = (span - n * rw) / (n + 1)
    pitch = rw + g
    zone = panel.difference(blockers) if blockers is not None else panel
    region = (zone.buffer(-fr._BACK_CUT_R, join_style=1, resolution=32)
                  .buffer(fr._BACK_CUT_R, join_style=1, resolution=32))
    EPS = 0.01
    ero = zone.buffer(-(rw / 2 + g - EPS), join_style=1, resolution=48)
    x0b, _, x1b, _ = panel.bounds
    ribs = []
    for i in range(n):
        cy = y0 + g + rw / 2 + i * pitch
        seg = ero.intersection(LineString([(x0b - 1, cy), (x1b + 1, cy)]))
        if seg.is_empty:
            continue
        segs = (seg.geoms if seg.geom_type in ("MultiLineString", "GeometryCollection")
                else [seg])
        for s in segs:
            if getattr(s, "length", 0.0) < rw:      # a stub shorter than it is wide
                continue
            gg = s.buffer(rw / 2, resolution=32).intersection(region)
            for p in (gg.geoms if gg.geom_type == "MultiPolygon" else [gg]):
                if p.area > 0.2:                    # keep counter chips, drop dust
                    ribs.append(fr._dedupe(p))
    cut = region.difference(unary_union(ribs)) if ribs else region
    return panel, zone, region, ribs, cut, n, g, pitch


def _cut_reeding(f, cut):
    """Raster the pour's cut and take it to valley depth with the O0.6."""
    cm = f.raster(cut)
    got, miss = f.pocket(cm, fr.FIN_VALLEY, fr._BACK_CUT_R)
    return cm, f.area(miss)


# --- variants -----------------------------------------------------------------------

def v_knockout(f):
    """K -- DRH left flush IN the reeding, wrapped at the boss clearance like a pad."""
    glyph, _per = E.block([("DRH", 11.00, "b", 0.00)], CX, CY)
    blockers = glyph.buffer(fr.FIN_BOSS_CLR, join_style=1)
    _panel, _zone, _region, ribs, cut, n, g, pitch = reeding(blockers)
    _cm, miss_a = _cut_reeding(f, cut)
    gm = f.raster(glyph)
    stroke = f.widest(gm)
    polys = list(glyph.geoms) if glyph.geom_type.startswith("Multi") else [glyph]
    holes = [Polygon(r) for p in polys for r in p.interiors]
    counter_reed = cut.intersection(unary_union(holes)).area if holes else 0.0
    notes = [
        f"the pour re-closed over the {PANEL[3]-PANEL[1]:.1f} mm panel: {n} rows, groove "
        f"{g:.3f}, pitch {pitch:.4f} -- the fields run {fr.FIN_ROWS} rows at "
        f"{fr.FIN_PITCH:.4f}; same rib, same O0.6, {abs(pitch-fr.FIN_PITCH)*1000:.0f} um apart",
        f"DRH cap 11.00, stroke {stroke:.2f} -- the letters are the UNCUT surface, wrapped "
        f"at the boss clearance {fr.FIN_BOSS_CLR:.2f} exactly as the pour wraps a boss",
        f"{len(ribs)} rib segments across {n} rows; grooves at {fr.FIN_VALLEY:.2f}, the "
        f"fields' own valley -- the deepest texture on the part frames flush information",
        f"the counters keep their texture: {counter_reed:.1f} mm2 of groove survives inside "
        f"D and R" if counter_reed > 0.05 else
        "the boss-clearance wrap swallows the counters -- they stay flush",
        f"metal past the pour's own min-width rule (raster vs shapely opening): "
        f"{miss_a:.3f} mm2",
    ]
    return notes, fr.FIN_VALLEY


def v_two_depth_ceiling(f):
    """L -- H re-asked at the doubled ceiling; the answer is the TOOL is the ceiling now."""
    notes = []
    name = E.line_geom("DEVIN HOROWITZ", CX, CY - 5.4, 3.40, "b")
    m = f.raster(name)
    _cut, miss = f.pocket(m, 0.45, 0.15)
    notes.append("the ceiling doubled to 0.60 but the tool did not: a O0.3 slotting Ti is "
                 "honest to ~1.5xD, so the name floor is 0.45 in three 0.15 passes -- the "
                 "binding constraint moved from the part to the cutter")
    notes.append(f"{'DEVIN HOROWITZ':<30} cap 3.40  POCKET dia 0.3, flat bottom 0.450 mm"
                 + (f"  ({f.area(miss):.2f} mm2 unreachable)" if miss.any() else ""))
    rest = C.stack([("ATTORNEY", 1.50, "r", 0.00),
                    ("Devin@Horowitz.Law", 2.10, "r", 1.80),
                    ("404-213-8076", 2.10, "r", 1.10),
                    ("Atlanta, Georgia", 1.55, "r", 1.30)], CX, CY + 4.3, "centre")
    for ln in rest:
        got = f.vee(f.raster(ln["geom"]), 0.18, 60.0, 0.10)
        notes.append(f"{ln['txt'][:30]:<30} cap {ln['cap']:4.2f}  V-GROOVE      {got:.3f} mm")
    notes.append("0.45 vs 0.18 -- a 2.5x step, 0.27 mm of shoulder under a fingertip "
                 "(H was 0.30/0.15 with a 0.15 shoulder)")
    return notes, 0.45


def v_registered_deep(f):
    """M -- F's registered relief with its floor at the fin valleys' own 0.60."""
    win = box(*C.GLOW_WIN)
    drh = C.letterspaced("DRH", C.GLOW_WIN[0] + 1.6, C.GLOW_WIN[2] - 1.6,
                         (C.GLOW_WIN[1] + C.GLOW_WIN[3]) / 2.0, 4.40, "b")
    wm, gm = f.raster(win), f.raster(drh)
    _reach, miss, flare = C.relief_taper(f, wm, gm, 0.60, 0.10, 15.0)
    stroke = f.widest(gm)
    notes = [
        "F's exact window and letters, floor taken to 0.60 -- the fin valleys' depth, so "
        "the recess adds no new thin section and stands on the same 0.40 web the whole "
        "part already accepts",
        f"unreachable in the window: {f.area(miss):.3f} mm2 -- reach is set by the 0.2 mm "
        f"tip, so doubling the depth costs no counter",
        f"taper flare at the base: {flare*1000:.0f} um -- at 0.60 the 15 deg wall reads as "
        f"a chamfered window edge; letters keep {stroke-2*flare:.2f} of flat crest on a "
        f"{stroke:.2f} stroke",
        "four ~0.15 stepdowns for the tapered cutter in Ti -- depth is passes, not risk; "
        "the taper is the rigidity",
    ]
    for ln in C.stack([("Devin@Horowitz.Law", 2.10, "r", 0.00),
                       ("404-213-8076  ·  Atlanta, Georgia", 1.55, "r", 1.30)],
                      CX, 51.9, "centre"):
        got = f.vee(f.raster(ln["geom"]), 0.25, 60.0, 0.10)
        notes.append(f"{ln['txt'][:30]:<30} cap {ln['cap']:4.2f}  cut {got:.3f} mm")
    return notes, 0.60


def v_plaque_in_pour(f):
    """N -- reeding floods the band; the contact block rides a flush island in it."""
    lines = [("DEVIN HOROWITZ",     2.60, "b", 0.00),
             ("ATTORNEY",           1.35, "r", 1.15),
             ("Devin@Horowitz.Law", 1.95, "r", 1.75),
             ("404-213-8076",       1.95, "r", 1.00),
             ("Atlanta, Georgia",   1.45, "r", 1.25)]
    glyph, per = E.block(lines, CX, CY)
    b = glyph.bounds
    assert abs((b[0] + b[2]) / 2.0 - CX) < 0.1, "plaque lost x-symmetry -- mirror breaks"
    MX, MY, PR = 1.6, 1.3, 1.0
    plaque = _rounded((b[0] - MX, b[1] - MY, b[2] + MX, b[3] + MY), PR)
    blockers = plaque.buffer(fr.FIN_BOSS_CLR, join_style=1)
    _panel, _zone, _region, ribs, cut, n, g, pitch = reeding(blockers)
    pb = plaque.bounds
    above = sum(1 for r in ribs if r.bounds[3] < pb[1])
    below = sum(1 for r in ribs if r.bounds[1] > pb[3])
    side = len(ribs) - above - below
    assert above >= 2 and below >= 2, "plaque leaves fewer than two full rows of reeding"
    _cm, miss_a = _cut_reeding(f, cut)
    corr = ((PANEL[2] - PANEL[0]) - (pb[2] - pb[0])) / 2.0 - fr.FIN_BOSS_CLR
    need = fr.FIN_RIB_W + 2 * g
    notes = [
        f"plaque {pb[2]-pb[0]:.1f} x {pb[3]-pb[1]:.1f} mm, flush, wrapped at "
        f"{fr.FIN_BOSS_CLR:.2f} -- to the pour it is just another pad",
        f"{n} rows / {len(ribs)} segments, groove {g:.3f}, pitch {pitch:.4f}; "
        f"{above} full rows above the plaque, {below} below"
        + (f", {side} part-rows beside it" if side else
           f"; the {corr:.1f} mm side corridors sit under rib + 2 grooves ({need:.2f}), so "
           f"they carry clean valley channel instead of stub rows -- what the pour "
           f"does at a boss wrap"),
        f"grooves at {fr.FIN_VALLEY:.2f} (raster-vs-shapely residue {miss_a:.3f} mm2)",
    ]
    for txt, cap, _w, geo in per:
        got = f.vee(f.raster(geo), 0.25, 60.0, 0.10)
        notes.append(f"{txt[:30]:<30} cap {cap:4.2f}  cut {got:.3f} mm")
    notes.append("one texture floods everything and one rule wraps every island -- the "
                 "pour philosophy, applied to the information itself")
    return notes, fr.FIN_VALLEY


def v_unit_grid(f):
    """O -- G re-founded: the fine pitch is below every cap, so type takes TWO units."""
    u = fr.FIN_PITCH
    notes = [f"the fine reeding retired G's premise: FIN_PITCH fell 3.20 -> {u:.3f}, "
             f"below every cap in the block, so no line can sit on every pitch line -- "
             f"type takes 2u = {2*u:.3f} mm, the ribs' frequency halved"]
    spec = [("DEVIN HOROWITZ", 2.60, "b"), ("ATTORNEY", 1.40, "r"), (None, 0, None),
            ("Devin@Horowitz.Law", 2.00, "r"), ("404-213-8076", 2.00, "r"),
            ("Atlanta, Georgia", 1.50, "r")]
    ys = [CY + (i - (len(spec) - 1) / 2.0) * 2 * u for i in range(len(spec))]
    for y, (txt, cap, weight) in zip(ys, spec):
        if txt is None:
            g = C.rule(LEFT, ART[2] - 2.6, y, 0.55)
            g = aff.scale(g, xfact=-1, yfact=1, origin=(fr.W / 2.0, fr.H / 2.0))
            got = f.vee(f.raster(g), 0.25, 60.0, 0.10)
            notes.append(f"{'rule 0.55 wide, on the grid':<30} cut {got:.3f} mm")
            continue
        g = E.line_geom(txt, CX, y, cap, weight)
        b = g.bounds
        g = aff.translate(g, (fr.W - LEFT) - b[2], 0.0)
        got = f.vee(f.raster(g), 0.25, 60.0, 0.10)
        notes.append(f"{txt[:30]:<30} cap {cap:4.2f}  cut {got:.3f} mm  "
                     f"({(y-CY)/u:+.0f}u from centre)")
    notes.append(f"leading {2*u:.3f} on a 2.00 cap = {2*u/2.00:.2f}x -- tight but set by "
                 f"the part, which was G's whole argument")
    return notes, 0.25


VARIANTS = [
    ("K-knockout", "REEDED KNOCKOUT", "DRH flush in the pour, wrapped like a boss",
     v_knockout,
     "The inverse of every prior variant: the texture is the cut and the letters are the "
     "surface. You feel smooth islands in a ribbed field, and the monogram is made of the "
     "same rule that wraps the mounting bosses."),
    ("L-two-depth-060", "TWO-DEPTH, RE-ASKED", "name pocketed 0.45 (the O0.3's honest 1.5xD), details 0.18",
     v_two_depth_ceiling,
     "H at the doubled budget -- and the honest answer is that the budget stopped being "
     "the constraint. A O0.3 in Ti runs out of rigidity at ~1.5xD, so the name floor is "
     "0.45, not 0.60, and the note says which limit bound."),
    ("M-registered-deep", "REGISTERED, FULL DEPTH", "F's window relief with its floor at 0.60",
     v_registered_deep,
     "The standing pick, given everything the deepened valleys bought. The glow window "
     "becomes a real recess -- 0.60 under the thumb, 0.40 web underneath, exactly the "
     "section the whole part already stands on -- and the registration argument is "
     "unchanged because the geometry is."),
    ("N-plaque-in-pour", "PLAQUE IN THE POUR", "reeding floods the band; the block rides a flush island",
     v_plaque_in_pour,
     "The whole back becomes one texture with one flush island of information. The plaque "
     "is wrapped at the boss clearance like any pad, so nothing about it is a special "
     "case -- the strongest 'designed, not placed' argument of the ten-and-five."),
    ("O-unit-grid", "UNIT GRID", "baselines on 2x the fine pitch -- G re-founded",
     v_unit_grid,
     "G's idea survives the fine reeding only as a harmonic: type on every SECOND pitch "
     "line. The leading is still inherited from the ribs, just an octave down."),
]


def build(fn):
    f = E.Field(ART, pad=0.0)
    notes, deepest = fn(f)
    notes.append(f"DEEPEST CUT {deepest:.3f} mm -> {E.FLOOR - deepest:.3f} mm floor left "
                 f"({'within' if deepest <= E.BUDGET + 1e-9 else 'PAST'} the {E.BUDGET:.2f} mm "
                 f"the fin valleys already take)")
    return f, np.ones(f.z.shape, bool), notes


if __name__ == "__main__":
    E.ensure_shell()
    E.SHELL = E.clip_back_face(E.shell_actor(), ART)
    print(f"art rect {ART}, clear band y{fr.fin_band()}, field pitch {fr.FIN_PITCH:.4f}, "
          f"valley {fr.FIN_VALLEY}\n")
    made = []
    for key, title, sub, fn, why in VARIANTS:
        f, keep, notes = build(fn)
        print(f"=== {key}  {title} -- {sub}")
        for n in notes:
            print("    " + n)
        surf = E.field_surfaces(f, keep)
        p1, p2 = f"{OUT}/spin3_{key}.png", f"{OUT}/spin3_{key}_graze.png"
        E.shot(surf, p1)
        E.shot(surf, p2, crop=15.0, grazing=True, az=2.0, el=5.0)
        made.append((title, sub, p1, p2, notes))
        print(f"    wrote {os.path.basename(p1)}, {os.path.basename(p2)}\n")

    ims = [(t, s, Image.open(a).convert("RGB"), Image.open(b).convert("RGB"), n)
           for t, s, a, b, n in made]
    cw = max(max(a.width, b.width) for _t, _s, a, b, _n in ims)
    ch = max(max(a.height, b.height) for _t, _s, a, b, _n in ims)
    pad, head, gap, foot = 26, 104, 12, 340
    sheet = Image.new("RGB", (len(ims) * (cw + pad) + pad, head + ch * 2 + gap + foot),
                      (247, 247, 245))
    d = ImageDraw.Draw(sheet)
    ft, fs, fm = E.label_font(40), E.label_font(24), E.label_font(19)
    for i, (t, s, a, b, notes) in enumerate(ims):
        x = pad + i * (cw + pad)
        d.text((x, 16), t, font=ft, fill=(20, 20, 24))
        d.text((x, 64), s, font=fs, fill=(92, 92, 100))
        sheet.paste(a, (x + (cw - a.width) // 2, head))
        sheet.paste(b, (x + (cw - b.width) // 2, head + ch + gap))
        y = head + ch * 2 + gap + 16
        d.line([(x, y - 8), (x + cw - 6, y - 8)], fill=(206, 206, 202), width=2)
        for ln in notes:
            for w in E._wrap(ln, 74):
                d.text((x, y), w, font=fm,
                       fill=(70, 70, 78) if "DEEPEST" in ln else (118, 118, 126))
                y += 24
    d.text((pad, head + ch * 2 + gap + foot - 34),
           "SPIN 3 -- the engraving meets the fine reeding (2026-07-30: pitch 1.392, valley "
           "0.60). Same tool physics: every depth field is a real cut, 25 um, on the real shell.",
           font=fs, fill=(92, 92, 100))
    sheet.save(f"{OUT}/spin3_reeded.png")
    print("wrote", f"{OUT}/spin3_reeded.png", sheet.size)
