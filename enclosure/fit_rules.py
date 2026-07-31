#!/usr/bin/env python3
"""The fit rules for the enclosure: ONE home for the geometry both generators obey.

WHY THIS IS A MODULE AND NOT TWO COPIES

The brace and the shell each decide where they may put material, and both decisions are a
function of the same thing: where the parts actually are. When those rules lived inside the
two generators as literal rectangles and four scalar lip widths, they went stale against the
board independently and neither knew:

  * the brace's middle band was sized for supercap bays ending at y31.15/57.75 -- the 28.5 mm
    WS17 length -- while SC1/SC3 are 39 mm SS17 cells, so the brace put 593 mm3 of solid
    resin inside three 1.70 mm cans in a 1.80 mm cavity and could not be installed;
  * the shell's lip landed on nine B-side parts including 4.17 mm2 of LIVE pad under
    grounded titanium, shorting the storage rail on assembly;
  * five of eight M2 bosses fouled a part, two on live nets;
  * and the shell's own comment asserted "R14 y0 31.44" about a part that sits at y4.92.

So the rules live here, the generators import them, and check_consistency [8] asserts the
invariants against these same functions rather than a third copy. A part that moves now
changes the enclosure instead of silently colliding with it.

WHAT THE RULES ARE

  BRACE   A part can be COVERED (pocketed) only if the resin left above it still prints:
          web = GAP - (h + AIR) >= SLA_WEB, i.e. h <= SPAN_LIMIT. Anything taller is a
          BLOCKER and is subtracted from the footprint instead of pocketed. Interference is
          therefore structurally impossible: what would collide is what gets removed.

  LIP     Per band, per edge, backed off LIP_CLR from the nearest part body-or-pad, and
          never overhanging the NFC coil. Wide wherever nothing is in the way, because it
          supports a 0.60 mm board.

  BOSS    The r2.60 disc with any fouling part cut out of it, which costs almost no thread:
          the worst case keeps 92.4% of the r0.80..r2.60 annulus.
"""
from __future__ import annotations

import os
import sys

from shapely.geometry import box, Point, Polygon
from shapely.ops import unary_union

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from board_parts import parts as board_parts   # noqa: E402

# ---- board / cavity -------------------------------------------------------------------
W, H = 50.80, 88.90
CAVITY = 1.80              # cap-limited: SUPERCAP_H 1.70 + 0.10 air
BOARD_TH = 0.60
TOOL_R = 1.0               # dia 2.0 finisher -> R1.0 internal corners

# ---- brace ----------------------------------------------------------------------------
GAP = CAVITY               # the brace fills the cavity
AIR = 0.12                 # air over a covered part
CLR = 0.25                 # in-plane clearance around a part
SLA_WEB = 0.40             # thinnest resin that may remain OVER a pocket
SLA_WALL = 0.60            # thinnest in-plane feature we will print
SPAN_LIMIT = GAP - AIR - SLA_WEB          # 1.28
MIN_PIECE = 25.0           # smaller than this is print debris, not support
SINGLE_PIECE = True        # ship one part; see brace_footprint()
DROPPED_AREA = 0.0         # set by brace_footprint(): support given up to stay single-piece
DROPPED_COUNT = 0
WALL_FIT = 0.05            # brace-to-cavity-wall contact fit

# ---- shell ----------------------------------------------------------------------------
BOSS_R = 2.60
PILOT_R = 0.80
BOSS_CLR = 0.20            # Ti boss to part/pad
THREAD_KEEP = 1.30         # never scallop inside this: the M2 thread lives at r0.80..~1.0
LIP_CLR = 0.30             # lip edge to nearest part body or pad
LIP_MAX = {"W": 2.5, "E": 2.5, "S": 2.0, "N": 2.0}
COIL_CLR = 1.00            # grounded metal to coil copper. Raised from 0.30 on request:
                           # the east lip is the only grounded feature that comes near the
                           # antenna, and 1.00 gives 3.3x the standoff while still leaving a
                           # 1.25 mm lip -- wider than the flat 1.0 the original design used.
                           # The tradeoff is linear and lives on one line: 0.30 -> 1.95 mm
                           # lip / 490 mm2, 1.00 -> 1.25 / 463, 1.25 -> 1.00 / 442, and
                           # 1.50 leaves 0.75 mm, below the design's own floor.
# MEASURED from the board, not asserted. The hard-coded 48.40 was 0.15 mm optimistic --
# LA/LB copper reaches x48.550 -- so the lip sized against it overhung the antenna.
from board_parts import coil_extent as _coil_extent          # noqa: E402
COIL_EAST = round(_coil_extent()[1] + COIL_CLR, 3)
MOUNTS = [(3.0, 3.0), (47.8, 3.0), (3.0, 85.9), (47.8, 85.9),
          (3.0, 28.5), (47.8, 28.5), (3.0, 60.4), (47.8, 60.4)]
RELIEF_R = BOSS_R + CLR    # 2.85 -- brace relief around a boss; was a flat 3.00, which
                           # pinched every rail to a 0.750 mm waist at all eight bosses.

# the shell's own cavity void, before the lip is applied
_CAV = (2.50, 2.00, 49.80, 86.90)
_CAV_IR = 1.95


def _cached_parts(_cache={}):
    if "B" not in _cache:
        _cache["B"] = board_parts("B")
    return _cache["B"]


def blockers(ps=None):
    """Parts the brace cannot cover: taller than SPAN_LIMIT, or with no height at all."""
    ps = ps or _cached_parts()
    return [(r, p) for r, p, h, _s in ps if h is None or h > SPAN_LIMIT]


def spannable(ps=None):
    ps = ps or _cached_parts()
    return [(r, p, h) for r, p, h, _s in ps if h is not None and h <= SPAN_LIMIT]


def cavity_rect():
    x0, y0, x1, y1 = _CAV
    ir = _CAV_IR
    c = box(x0 + ir, y0, x1 - ir, y1).union(box(x0, y0 + ir, x1, y1 - ir))
    for cx, cy in [(x0+ir, y0+ir), (x1-ir, y0+ir), (x0+ir, y1-ir), (x1-ir, y1-ir)]:
        c = c.union(Point(cx, cy).buffer(ir, resolution=64))
    return c


def brace_footprint():
    """[polygon] -- the pieces the brace is actually made of, largest first."""
    cav = cavity_rect().buffer(-WALL_FIT, join_style=1, resolution=64)
    keep = unary_union([p.buffer(CLR, join_style=2) for _r, p in blockers()])
    boss = unary_union([Point(b).buffer(RELIEF_R, resolution=64) for b in MOUNTS])
    fp = cav.difference(keep).difference(boss)
    t = SLA_WALL / 2.0
    fp = (fp.buffer(-t, join_style=1, resolution=32)
            .buffer(t, join_style=1, resolution=32)
            .intersection(cav))
    pieces = sorted((list(fp.geoms) if fp.geom_type == "MultiPolygon" else [fp]),
                    key=lambda g: -g.area)
    pieces = [g.simplify(0.01, preserve_topology=True) for g in pieces if g.area >= MIN_PIECE]

    # SINGLE PIECE ONLY. The computation naturally yields a second island east of SC4 (~85
    # mm2) which cannot reach the main body without crossing SC4. It is real support, but a
    # loose part in an assembly that must come apart for C9 NFC trim is a thing to lose and a
    # thing to reassemble wrong, so it is dropped by decision, not by accident. Cost is
    # recorded rather than hidden: DROPPED_AREA is what the choice gave up.
    global DROPPED_AREA, DROPPED_COUNT
    DROPPED_AREA = sum(g.area for g in pieces[1:])
    DROPPED_COUNT = len(pieces) - 1
    return pieces[:1]


def _lip_reach(edge, lo, hi, ps=None):
    ps = ps or _cached_parts()
    lim = LIP_MAX[edge]
    for _ref, poly, _h, _src in ps:
        x0, y0, x1, y1 = poly.bounds
        if edge in ("W", "E"):
            if y1 <= lo or y0 >= hi:
                continue
            d = x0 if edge == "W" else (W - x1)
        else:
            if x1 <= lo or x0 >= hi:
                continue
            d = y0 if edge == "S" else (H - y1)
        lim = min(lim, d - LIP_CLR)
    if edge == "E":
        lim = min(lim, W - COIL_EAST)
    return max(0.0, round(lim, 2))


def lip_bands(edge, step=0.5):
    """[(lo, hi, width)] along `edge`, merged. Computed, so it cannot go stale."""
    span = H if edge in ("W", "E") else W
    out, cur, start = [], None, 0.0
    a = 0.0
    while a < span - 1e-9:
        b = min(a + step, span)
        w = _lip_reach(edge, a, b)
        if cur is None:
            cur, start = w, a
        elif abs(w - cur) > 1e-9:
            out.append((start, a, cur)); cur, start = w, a
        a = b
    out.append((start, span, cur))
    merged = []
    for bnd in out:
        if merged and abs(merged[-1][2] - bnd[2]) < 1e-9:
            merged[-1] = (merged[-1][0], bnd[1], bnd[2])
        else:
            merged.append(bnd)
    return merged


def cavity_void_poly(tool_r=TOOL_R, simplify=True):
    """Cavity void in board coords: the board rect inset by the per-band lip, opened by the
    finisher radius, plus local reliefs for what the tool then cannot reach."""
    strips = []
    for lo, hi, w in lip_bands("W"):
        strips.append(box(0.0, lo, w, hi))
    for lo, hi, w in lip_bands("E"):
        strips.append(box(W - w, lo, W, hi))
    for lo, hi, w in lip_bands("S"):
        strips.append(box(lo, 0.0, hi, w))
    for lo, hi, w in lip_bands("N"):
        strips.append(box(lo, H - w, hi, H))
    void = box(0.0, 0.0, W, H).difference(unary_union(strips))
    opened = (void.buffer(-tool_r, join_style=1, resolution=48)
                  .buffer(tool_r, join_style=1, resolution=48))

    # A dia 2.0 finisher cannot reach the concave corners a band step leaves, so the opening
    # puts material back over a few parts near a step -- a fixed 0.088 mm2 worst case that
    # does NOT improve at any band clearance (swept 0.30..0.80, identical). Dilating a
    # keep-out by the tool radius makes it tool-reachable by construction.
    lip_now = box(0.0, 0.0, W, H).difference(opened)
    stuck = [p for _r, p, _h, _s in _cached_parts() if lip_now.intersection(p).area > 1e-6]
    if stuck:
        opened = opened.union(unary_union(
            [p.buffer(LIP_CLR + tool_r, join_style=1, resolution=48) for p in stuck]))
    if opened.geom_type == "MultiPolygon":
        opened = max(opened.geoms, key=lambda g: g.area)
    # simplify is a CAD-export convenience (it keeps OCC from chewing on thousands of
    # buffer vertices), not geometric truth: it may move a boundary by up to 0.01 mm, which
    # on a 2.45 mm edge is 0.0245 mm2 of phantom overlap. check_consistency [8] asks for the
    # unsimplified polygon so its verdict is exact rather than tolerance-padded.
    return opened.simplify(0.01, preserve_topology=True) if simplify else opened


def lip_poly(simplify=True):
    """The support ledge itself -- what a B-side part would be crushed by / shorted on."""
    return box(0.0, 0.0, W, H).difference(cavity_void_poly(simplify=simplify))


def boss_island(mx, my):
    """A boss disc scalloped clear of anything that fouls it."""
    disc = Point(mx, my).buffer(BOSS_R, resolution=64)
    foul = [p for _r, p, _h, _s in _cached_parts() if p.distance(Point(mx, my)) < BOSS_R]
    if not foul:
        return disc
    scal = disc.difference(unary_union([p.buffer(BOSS_CLR, join_style=2) for p in foul]))
    if scal.geom_type == "MultiPolygon":
        keep = [g for g in scal.geoms if g.contains(Point(mx, my))]
        scal = keep[0] if keep else disc
    return scal.simplify(0.005, preserve_topology=True)


# ---- back-side fin fields ----------------------------------------------------------------
# Texture on the exterior back: two fin fields with a clear band between them. Called "cooling
# fins" and they cool nothing -- Ti-6Al-4V conducts at ~6.7 W/m*K against aluminium's ~150, and
# this card's entire budget is microwatts. They are grip and they are aggression; the surface-area
# story is a joke the geometry is in on. Saying so here rather than in the part name.
#
# HORIZONTAL (ribs across X). Held in portrait the card wants to slide down through the fingers,
# and ridges perpendicular to that slide are the ones that stop it. The trade is real: ribs across
# the short axis do NOT stiffen the card against its dominant flex, which is curling along its
# length -- lengthwise ribs would. Grip wins because the plate is screwed to a PCB at eight points,
# not carried bare, and 0.70 mm of floor survives under the valleys.
FIN_PITCH  = 3.2           # centre-to-centre; coarser reads as fins, finer reads as knurl
FIN_RIB_W  = 2.0           # rib width; the rest of the pitch is valley. Was 1.7 -- widened
                           # 2026-07-30 on request for more rib surface (grip): rib-top area
                           # 1026 -> 1207 mm^2 (+18%) with pitch, rib POSITIONS and the boss
                           # keepouts all unchanged. The floor of this number is the VALLEY:
                           # 3.2 - 2.0 = 1.2 leaves the O1.0 back cutter 0.2 of side clearance;
                           # 2.2 would make the valley exactly cutter-width -- zero-clearance
                           # slotting that burnishes in Ti and goes undersize with tool wear.
FIN_PROUD  = 0.10          # rib tops stand this proud of the art field...
FIN_VALLEY = 0.30          # ...and valleys are cut this far into the 1.00 floor -> 0.40 relief
FIN_BOSS_CLR = 0.40        # rib to back boss annulus
BACK_BORDER = 2.0          # the proud back frame's width (mirrors the generator's own constant)


def _dedupe(poly):
    """Drop zero-length edges. Buffer operations leave coincident consecutive vertices, and OCC
    turns one of those into `BRepAdaptor_Curve::No geometry` the moment it tries to build a face
    -- which is exactly how the first finned build died. Deliberately NOT simplify(): that moves
    vertices, and these polygons are holding a boss clearance that is exactly 3.000 mm.
    """
    def ring(cs):
        out = [cs[0]]
        for c in cs[1:]:
            if abs(c[0] - out[-1][0]) > 1e-9 or abs(c[1] - out[-1][1]) > 1e-9:
                out.append(c)
        if len(out) > 1 and abs(out[0][0] - out[-1][0]) < 1e-9 and abs(out[0][1] - out[-1][1]) < 1e-9:
            out.pop()
        return out
    ext = ring(list(poly.exterior.coords))
    ints = [ring(list(r.coords)) for r in poly.interiors]
    return Polygon(ext, [r for r in ints if len(r) >= 3])


def _back_field():
    """The recessed back art field AS THE GENERATOR MACHINES IT: a CARD-CENTRED rectangle.

    This used to be cavity_rect().buffer(-2.0) -- the LIP MOUTH inset by the border. The
    mouth is deliberately x-asymmetric (W lip 2.5, E lip 1.0 for the NFC coil), so the fin
    fields inherited a 0.75 mm x-offset onto the card's EXTERIOR: flush side margins of
    2.45 vs 0.95 mm inside an art field the generator cuts dead-centred ("SYMMETRIC proud
    back-frame border, equal on all 4 sides (decoupled from the asymmetric front lip)" --
    the generator's own back_border comment). Reviewer-visible as uneven side spacing.
    Now mirrors the generator's art-field rect exactly: centred, cavW-2*border wide,
    fillet concentric with the frame fillet.
    """
    W, H, EF, CAVR = 50.80, 88.90, -0.05, 2.95      # board + edge_fit, as the generator uses
    hw, hh = (W + 2 * EF) / 2 - BACK_BORDER, (H + 2 * EF) / 2 - BACK_BORDER
    cx, cy = W / 2, H / 2
    r = max(CAVR - BACK_BORDER, 0.3)
    c = box(cx - hw, cy - hh, cx + hw, cy + hh)
    return c.buffer(-r, join_style=1, resolution=64).buffer(r, join_style=1, resolution=64)


# ---- fin ISLAND: the fins as a designed shape, not a box that fit --------------------
# Each fin field is a soft-cornered island floating in the flush art field, and every
# groove is one constant-width channel: MOAT (= FIN_PITCH - FIN_RIB_W = 1.2) wraps rib
# flanks, rib TIPS and the island boundary identically -- the width one O1.0 pass plus
# finish leaves, so the geometry is what the tool wants to make. Rib ends are full-round
# (stadium) because they are the round-capped buffer of their own centreline. The island
# corner radius is picked so the boss keepouts clear BY CONSTRUCTION (min centre distance
# 3.47 against the required 3.00) -- the corner sweep curves away from each boss instead
# of the keepout arc nibbling the corner rib, which is what read as "a box that fit".
# The price of the uniform channel is one rib row per field (the tip moat consumes what
# the old flush-tangent ends did not); FIN_MARGIN 0.8 would buy the row back at the cost
# of the uniform 2.0 reveal -- recorded here so the trade stays a decision, not a dig.
FIN_MARGIN = 2.0           # flush reveal between island and field edge / clear band --
                           # the same 2.0 as the proud frame border: one rhythm everywhere
FIN_CORNER_R = 4.8         # island corner radius; >= 3.66 clears the corner bosses, 4.8
                           # gives 0.47 spare and sweeps ~1.5 rib rows -- reads designed


def _fin_islands():
    """One rounded-rect island per field, in the true (centred) art field."""
    field = _back_field()
    fx0, fy0, fx1, fy1 = field.bounds
    y0, y1 = fin_band()
    out = []
    for a, b in [(fy0, y0), (y1, fy1)]:
        c = box(fx0 + FIN_MARGIN, a + FIN_MARGIN, fx1 - FIN_MARGIN, b - FIN_MARGIN)
        out.append(c.buffer(-FIN_CORNER_R, join_style=1, resolution=64)
                    .buffer(FIN_CORNER_R, join_style=1, resolution=64))
    return out


def fin_band():
    """The clear centre band, taken from THE FRONT'S OWN LAYOUT rather than invented.

    The two cells leave a gap on the show face; using exactly that gap on the back puts the clear
    field behind the artwork and the fin fields behind the cells, and it tracks the board -- move
    a cell and the bands follow. It also drops the y-mid bosses inside the clear band, so the fin
    fields only have the four corner annuli to work around.
    """
    pv = sorted((p.bounds for r, p, _h, _s in board_parts("F") if r.startswith("PV")),
                key=lambda b: b[1])
    if len(pv) < 2:
        raise SystemExit("fin_band: expected two PV cells on the front to derive the clear band")
    return pv[0][3], pv[1][1]


def fin_runs(pitch=FIN_PITCH, rib_w=FIN_RIB_W):
    """Per-field rib centrelines and the ENVELOPE the valley cut may occupy.

    The rib grid is centred in each field (off = remainder/2) and that is unchanged --
    the G engraving variant's baseline grid and every fin position stay put. What the
    envelope fixes is where the remainder GOES. It used to be cut: the valley field ran
    to the band edge, so each field started and ended with a PARTIAL groove -- 1.175 mm
    against the 1.500 of every interior valley -- and four narrower grooves at the field
    boundaries read as uneven machining (measured on the committed STL by ray-cast, and
    exactly what a reviewer flagged on the elevation render). The cut is now clipped to
    the rib envelope, so every groove that exists is a full 1.500 and the remainder is
    FLUSH art-field margin instead of a squeezed groove.
    """
    moat = pitch - rib_w
    runs = []
    for isl in _fin_islands():
        ero = isl.buffer(-(rib_w / 2 + moat), join_style=1, resolution=64)
        ey0, ey1 = ero.bounds[1], ero.bounds[3]
        span = ey1 - ey0
        n = max(1, int(span / pitch) + 1)
        while (n - 1) * pitch > span:
            n -= 1
        off = (span - (n - 1) * pitch) / 2.0          # centre the run inside its own island
        cys = [ey0 + off + i * pitch for i in range(n)]
        runs.append((isl, ero, cys))
    return runs


def fin_region(pitch=FIN_PITCH, rib_w=FIN_RIB_W):
    """Everything the valley cut may occupy: the islands themselves. The boss annuli are
    outside every island by construction (FIN_CORNER_R); the subtraction stays as a
    tripwire for any future geometry change."""
    blockers = unary_union([Point(mx, my).buffer(BOSS_R + FIN_BOSS_CLR, resolution=48)
                            for mx, my in MOUNTS])
    reg = unary_union(_fin_islands()).difference(blockers)
    return unary_union([_dedupe(g) for g in
                        (reg.geoms if reg.geom_type == "MultiPolygon" else [reg])])


def fin_ribs(pitch=FIN_PITCH, rib_w=FIN_RIB_W):
    """Stadium ribs: each rib is its own centreline clipped to the moat-eroded island and
    buffered back with round caps, so the tips are full-radius and every clearance --
    flank, tip, corner sweep -- is the same MOAT. Nothing here is narrower than the O1.0
    cutter plus finish allowance, so no separate sliver opening is needed."""
    from shapely.geometry import LineString
    region = fin_region(pitch, rib_w)
    out = []
    for isl, ero, cys in fin_runs(pitch, rib_w):
        x0, x1 = isl.bounds[0] - 5, isl.bounds[2] + 5
        for cy in cys:
            seg = ero.intersection(LineString([(x0, cy), (x1, cy)]))
            if seg.is_empty:
                continue
            r = seg.buffer(rib_w / 2, resolution=32).intersection(region)
            for g in (r.geoms if r.geom_type == "MultiPolygon" else [r]):
                if g.area > 0.8:
                    out.append(_dedupe(g))
    return out


def export_step_stable(solid, path, **kw):
    """cq.exporters.export to STEP, but leave the file alone if only the timestamp moved.

    OCC stamps a write time into FILE_NAME, so re-running a generator rewrites a 170k-line
    STEP whose geometry is identical -- pure churn on every run, and real geometry changes
    get lost in it. scripts/make_3d_models.py already suppressed this; the enclosure
    generators did not, which is how a rebuild against a front-copper-only re-route showed
    three "changed" STEP files whose STLs were byte-identical.
    """
    import os as _os, re as _re
    import cadquery as _cq
    strip = lambda s: _re.sub(r"(?m)^FILE_NAME\('[^']*','[^']*'", "FILE_NAME(", s)
    tmp = path + ".tmp"
    # exportType is REQUIRED here and was the bug that kept this function from ever running:
    # cq.exporters.export infers the format from the extension, and the extension is ".tmp",
    # so it raised "Unknown extensions, specify export type explicitly" on the first line that
    # mattered. Both enclosure CAD generators died there -- which nothing noticed, because
    # nothing in CI ran them. Wiring them into the pipeline is what surfaced it.
    kw.setdefault("exportType", "STEP")
    _cq.exporters.export(solid, tmp, **kw)
    new = open(tmp, encoding="utf-8", errors="replace").read()
    if _os.path.exists(path):
        old = open(path, encoding="utf-8", errors="replace").read()
        if strip(old) == strip(new):
            _os.remove(tmp)
            return False            # unchanged apart from the write time
    _os.replace(tmp, path)
    return True


if __name__ == "__main__":
    import math
    fp = brace_footprint()
    cav = cavity_rect().buffer(-WALL_FIT, join_style=1, resolution=64)
    print(f"brace: {len(fp)} piece(s), {sum(g.area for g in fp):.2f} mm2 "
          f"({100*sum(g.area for g in fp)/cav.area:.1f}% of {cav.area:.0f} mm2 cavity)")
    print(f"  blockers: {', '.join(r for r, _ in blockers())}")
    lp = lip_poly()
    print(f"lip: {lp.area:.2f} mm2, bands "
          f"W{len(lip_bands('W'))} E{len(lip_bands('E'))} "
          f"S{len(lip_bands('S'))} N{len(lip_bands('N'))}")
    full = math.pi * (BOSS_R**2 - PILOT_R**2)
    for mx, my in MOUNTS:
        a = boss_island(mx, my).area - math.pi * PILOT_R**2
        print(f"  boss ({mx:5.2f},{my:5.2f}): annulus {a:6.2f} mm2 = {100*a/full:5.1f}%")
