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
BOARD_TH = 0.60
TOOL_R = 1.0               # dia 2.0 finisher -> R1.0 internal corners
CAP_AIR = 0.10             # air over the CAVITY-SETTING parts (the caps in max; the shell
                           # CAD's cav_margin was this same number restated -- collapsed
                           # here 2026-08-07, the CAVITY-two-homes fix)

# CAVITY is DERIVED, never hand-written. Until 2026-08-07 this line read `CAVITY = 1.80`
# -- a literal copy of part_heights.SUPERCAP_H + 0.10 that agreed with the shell CAD's own
# independent derivation only numerically. The duplicate-constant class that produced the
# 0.1838 mm mount-pattern failure, one file over. The import is the fix.
from part_heights import SUPERCAP_H as _SUPERCAP_H, SUPERCAP_H_THIN as _SUPERCAP_H_THIN  # noqa: E402
CAVITY = round(_SUPERCAP_H + CAP_AIR, 2)      # 1.80 -- the MAX variant, cap-limited

# ---- brace ----------------------------------------------------------------------------
GAP = CAVITY               # the brace fills the cavity

# ---- the ferrite behind the NFC coil (Wurth WE-FSFS 364006, FER1) ----------------------
# Moved here 2026-08-03 so it has ONE home, the same rule the rest of this file exists for.
# It was declared in the brace CAD and copied verbatim into the brace DRAWING-gen; the
# assembly render now needs it too, and a third copy is how the first two stop agreeing.
# The brace CAD is not importable (no __main__ guard -- it builds and exports at import),
# so "import it from where it already lives" was not available; this is where it belongs.
#
# The pocket is on the BOARD-FACING face of the brace, so the sheet is sandwiched between
# the brace and the PCB's B-side, directly under the coil.
FER = (36.9, 31.5, 48.9, 57.5)   # x0,y0,x1,y1 -- 12 WIDE (x, CRITICAL, edge-limited) x 26 LONG
FER_T = 0.38                     # OVERALL stack per DK 732-5049-ND (ferrite + PET + PSA)
FER_POCKET_DEPTH = FER_T - 0.05  # 0.33 -- sheet sits ~0.05 proud and seats flush when clamped
FER_CLR = 0.20                   # channel wall clearance on the critical 12 mm width
AIR = 0.22                 # air over a covered part. 0.12 until 2026-08-02 -- that cleared the
                           # TYPICAL assembly stack but not the corner: body-height tol (+-0.10
                           # worst class) + solder standoff (~0.075; part_heights measures the
                           # 3D models, which seat at zero standoff) + resin pocket depth
                           # (+-0.10) RSS to ~0.16. 0.22 covers the RSS stack with margin;
                           # scripts/interference_drc.py carries the same stack as WC_STACK and
                           # reports the worst-case column. If first-article glow suffers from
                           # the diffuser sitting 0.1 farther off D2-D5, the rollback lever is a
                           # per-part AIR exception for the LEDs, not a global revert.
# Per-part AIR exceptions (2026-08-02). D2-D5 will be OPTICALLY GEL-COUPLED to the
# diffuser: an index-matched fill eliminates the air interface, so gap THICKNESS stops
# mattering optically and the constraint flips to mechanical -- the thinnest pocket that
# cannot hard-contact the LED dome at the worst-case corner. 0.16 puts worst-case at
# exactly 0.00 (the RSS stack), and the gel cushions the kiss corner. If bench gel work
# wants thinner still, 0.12 is the floor already proven printable -- accepting a
# gel-cushioned -0.04 corner. scripts/interference_drc.py reads this same dict.
AIR_EXCEPTIONS = {"D2": 0.16, "D3": 0.16, "D4": 0.16, "D5": 0.16}


def air_for(ref):
    return AIR_EXCEPTIONS.get(ref, AIR)
CLR = 0.25                 # in-plane clearance around a part
SLA_WEB = 0.40             # thinnest resin that may remain OVER a pocket
SLA_WALL = 0.60            # thinnest in-plane feature we will print
SPAN_LIMIT = GAP - AIR - SLA_WEB          # 1.18 (comment said 1.28 until 2026-08-07 --
                                          # written when AIR was 0.12 and never updated;
                                          # the number here is DERIVED, trust the formula)
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

# ---- the shell's GUARANTEED lip ring (2026-08-07) --------------------------------------
# The back-shell unions a scalar lip ring on top of the per-band lip system -- the ring is
# the guaranteed minimum board seat on each edge. Until 2026-08-07 its widths lived only in
# the shell CAD, sized against a v3-era measurement ("body max edge ~2.35 from the board
# edge"), and the v4 relayout walked SIX parts into it: the ring CRUSHED SC1/SC3/SC4
# (0.25/0.08/0.15 mm plan overlap, full cap height) and C27/C22/FB1 (up to 1.35 mm deep on
# the west edge) on every committed shell variant. Found by probing the committed STL;
# invisible to every gate because interference_drc SKIPs SC and nothing compared part
# bodies to the ring. The fix is cavity_void_poly's stuck-clause discipline applied to the
# ring: any part whose poly comes within LIP_CLR of ring metal gets a relief cut, buffered
# by LIP_CLR + TOOL_R so the cut is tool-reachable by construction. The shell cuts
# ring_reliefs() from the ring solid before the union; check [8] asserts the RESULT clears
# every part and self-tests the mechanism with a synthetic in-ring part. The ring widths
# are deliberately NOT shrunk: the relief yields locally, the seat stays maximal everywhere
# parts allow, and a future part move is handled by construction instead of by comment.
RING = {"W": 2.5, "N": 2.0, "S": 2.0, "E": 1.0}   # guaranteed ring widths (were shell-local)


def ring_metal_poly():
    """Board-coords union of the guaranteed lip-ring metal: four strips. (The shell's
    east wide-END blocks are NOT here: `_east_blocks` in the shell CAD is defined but
    never called -- the wide east ends migrated into the per-band system and the def is
    a fossil, so modelling them would assert metal that does not exist.)"""
    return unary_union([box(0.0, 0.0, RING["W"], H), box(W - RING["E"], 0.0, W, H),
                        box(0.0, 0.0, W, RING["S"]), box(0.0, H - RING["N"], W, H)])


def ring_reliefs(ps=None):
    """Relief polygons the shell must cut from the ring: one per REAL BODY (src "model")
    whose poly comes within LIP_CLR of ring metal, buffered LIP_CLR + TOOL_R
    (tool-reachable by construction, the same rule cavity_void_poly applies to its stuck
    parts). Bare-pad items (src "pads" -- J1, JP1, TP*, dnp SW2) are deliberately NOT
    relieved: flat copper under or beside the ring cannot be crushed, and the east lip's
    0.20 standoff from the JP1/TP1 pads is a recorded design decision this mechanism must
    not undo. `ps` takes the parts-list shape so the check can feed a synthetic part."""
    ring = ring_metal_poly()
    out = []
    for _r, p, _h, src in (ps if ps is not None else _cached_parts()):
        if src == "model" and p.distance(ring) < LIP_CLR:
            out.append(p.buffer(LIP_CLR + TOOL_R, join_style=1, resolution=48))
    return out
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
# NUDGED 0.13 mm DIAGONALLY OUTBOARD, 2026-08-03, off a bench fit. Every mount moved 0.13 in
# BOTH axes, away from the nearest solar cell corner: x away from the board centreline, y away
# from that cell. The move is diagonal because the binding dimension is diagonal -- the screw
# sits outside the cell's CORNER, not beside an edge -- so 0.13 on each axis buys 0.1836 mm of
# actual clearance, not 0.13. Head cap goes Ø3.754 -> Ø4.121, which is what takes a stock M2
# head off the cell: an ISO 4762 / DIN 84 Ø3.8 was touching by 0.023 mm and now clears by 0.160.
# The 0.13 is not arbitrary -- it is the largest nudge that moves NO trace. Beyond it MP1 runs
# into UPDI on F.Cu. Symmetry is exact: still mirrored about x25.4 and y44.45.
# KEEP IN STEP WITH THE BOARD -- these eight are the same eight drills in the .kicad_pcb, and
# check [16] is what makes that true rather than hoped-for.
MOUNTS = [(2.87, 2.87), (47.93, 2.87), (2.87, 86.03), (47.93, 86.03),
          (2.87, 28.63), (47.93, 28.63), (2.87, 60.27), (47.93, 60.27)]
RELIEF_R = BOSS_R + CLR    # 2.85 -- brace relief around a boss; was a flat 3.00, which
                           # pinched every rail to a 0.750 mm waist at all eight bosses.

# the shell's own cavity void, before the lip is applied
_CAV = (2.50, 2.00, 49.80, 86.90)
_CAV_IR = 1.95


def _cached_parts(_cache={}):
    if "B" not in _cache:
        _cache["B"] = board_parts("B")
    return _cache["B"]


def blockers(ps=None, span=None):
    """Parts the brace cannot cover: taller than the span limit, or with no height at all.

    `span` defaults to the module SPAN_LIMIT (the max variant). Per-variant callers pass
    variant_span(name) EXPLICITLY -- there is deliberately no mutable configure(): the
    2026-08-07 consumer map showed both CAD generators freeze fit_rules values at import,
    so mutated module state would build one variant's geometry under another's name."""
    ps = ps or _cached_parts()
    lim = SPAN_LIMIT if span is None else span
    return [(r, p) for r, p, h, _s in ps if h is None or h > lim]


def spannable(ps=None, span=None):
    ps = ps or _cached_parts()
    lim = SPAN_LIMIT if span is None else span
    return [(r, p, h) for r, p, h, _s in ps if h is not None and h <= lim]


def cavity_rect():
    x0, y0, x1, y1 = _CAV
    ir = _CAV_IR
    c = box(x0 + ir, y0, x1 - ir, y1).union(box(x0, y0 + ir, x1, y1 - ir))
    for cx, cy in [(x0+ir, y0+ir), (x1-ir, y0+ir), (x0+ir, y1-ir), (x1-ir, y1-ir)]:
        c = c.union(Point(cx, cy).buffer(ir, resolution=64))
    return c


def brace_footprint(span=None):
    """[polygon] -- the pieces the brace is actually made of, largest first.

    `span=None` is the max variant (module SPAN_LIMIT); per-variant callers pass
    variant_span(name). DROPPED_AREA/DROPPED_COUNT describe the LAST call -- a
    per-variant caller should read them immediately, before any other call."""
    cav = cavity_rect().buffer(-WALL_FIT, join_style=1, resolution=64)
    keep = unary_union([p.buffer(CLR, join_style=2) for _r, p in blockers(span=span)])
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


# ---- enclosure VARIANTS (2026-08-07) ----------------------------------------------------
# The single home for what distinguishes max / lite / air. Everything here is either
# DERIVED (cavity, screw length, span) or a per-variant DECISION with its reason beside it.
# No geometry lives in this table -- MOUNTS, lips, the cavity rectangle and the board are
# shared and live above. There is deliberately NO configure(): the generators freeze
# fit_rules values at import (consumer map, 2026-08-07), so per-variant numbers flow as
# EXPLICIT arguments from this table into build()/footprint calls, never as module state.
#
# Cavity rules differ BY LIMITER, not by formula fudging:
#   max  -- cap-limited:        SUPERCAP_H 1.70 + CAP_AIR 0.10             = 1.80
#   lite -- component-limited:  max(thin cap 1.00 + CAP_AIR,
#                                   tallest part 1.00 + AIR 0.22)          = 1.22
#           (AIR, not CAP_AIR: 1.22 is the smallest cavity whose span limit
#            1.22 - AIR - SLA_WEB = 0.60 still covers the 0.55/0.60 passive
#            field -- at cap-limited 1.10 the span falls to 0.48, the blocker
#            set explodes 24 -> 50 and the brace collapses. Measured, not
#            asserted: 935.7 mm2 vs a fragmented remnant.)
#   air  -- open frame, resting-clearance-limited: tallest part 1.00 + 2*CAP_AIR = 1.20
#           (no floor, no brace; the 0.20 is table-to-component daylight)
#
# Screw lengths are CHOSEN from stock sizes by the same rule everywhere: the longest
# length whose tip stays >= 0.15 inside the stack (max spotfaces the tip; air's tip must
# never pass the resting plane). part_heights.SUPERCAP_H_THIN is PROVISIONAL until the
# thin-cap MPN lands -- see its comment.

def _tallest_part_h():
    """Tallest measured B-side body (the caps are height-None by design)."""
    return max(h for _r, _p, h, _s in _cached_parts() if h is not None)


_SCREW_STOCK = (3.0, 2.5, 2.0, 1.6)   # lengths we can actually buy (M2, under-head, mm)


def _pick_screw(stack):
    for L in _SCREW_STOCK:
        if stack - L >= 0.15 - 1e-9:
            return L
    raise ValueError(f"no stock M2 length fits a {stack:.2f} stack")


def _mk_variants():
    tall = _tallest_part_h()                                   # 1.00 today (U1/L2)
    cav_max = CAVITY                                            # 1.80, derived above
    cav_lite = round(max(_SUPERCAP_H_THIN + CAP_AIR, tall + AIR), 2)   # 1.22
    # air clears BOTH the tallest measured part and the thin caps -- the caps are
    # height-None in the parts table (by design), so _tallest_part_h() alone would let a
    # >1.00 thin-cap MPN stand past the resting clearance. (2026-08-07 review finding:
    # without the max() the one-edit re-derivation promise held for lite but not air.)
    depth_air = round(max(tall, _SUPERCAP_H_THIN) + 2 * CAP_AIR, 2)    # 1.20
    v = {
        "max": dict(
            cap_h=_SUPERCAP_H, cavity=cav_max, floor=1.00, wall_th=1.00, border_h=0.15,
            open_back=False, brace=True, medallion=True, fins=True,
            material="Ti Gr5 (reference; brass or 6061 acceptable -- non-magnetic, machinable)",
            shell_name="solar-glow-drh-v3_0-backshell-0p6b-brace-Ti-max",
            brace_name="solar-glow-drh-diffuser-brace",
            coverage_floor=0.32,   # ledgered min (measures 0.329 after the 2026-08-08 LDO-island
                                   # migration to the SC3/SC4 bay: the island's five pockets and
                                   # DRH's Q2/R18/RN1/SW2 re-spread cost the max brace 58 mm2 of
                                   # field BY DESIGN -- the same round RAISED the lite brace
                                   # 26.5% -> 27.2%, the variant the campaign optimizes for.
                                   # Was 0.33 (measured 0.343 after the 2026-08-07 center
                                   # consolidation: cap scoots traded LEG area for center room;
                                   # legs are lip/cap/cell-backstopped)
        ),
        "lite": dict(
            cap_h=_SUPERCAP_H_THIN, cavity=cav_lite, floor=0.60, wall_th=1.00, border_h=0.15,
            open_back=False, brace=True, medallion=False, fins=False,
            # medallion/fins are PHYSICS-forced off, not styling: the fin valley is 0.60
            # deep and the coin floors ~0.55-0.75 -- both cut a 0.60 floor clean through.
            material="Ti Gr5 (thinned floor; the 0.60 is the shop-minimum conversation)",
            shell_name="solar-glow-drh-shell-lite-Ti",
            brace_name="solar-glow-drh-diffuser-brace-lite",
            coverage_floor=0.25,   # ledgered min (measures 0.272 after the 2026-08-08 island
                                   # migration -- UP from 0.264: the island's blockers left the
                                   # west corridor for the SC bay; floor deliberately kept at 0.25)
        ),
        "air": dict(
            cap_h=_SUPERCAP_H_THIN, cavity=depth_air, floor=0.00, wall_th=1.00, border_h=0.00,
            open_back=True, brace=False, medallion=False, fins=False,
            # 316L austenitic stainless, DELIBERATELY not a free choice: mu_r ~1.02. A
            # ferromagnetic steel beside the NFC coil adds hysteresis loss the ferrite
            # cannot shield (there is no ferrite pocket here) -- the ENIG-over-coil
            # lesson, one material over. Bench re-tune note lives in enclosure/README.
            material="316L stainless (austenitic, mu_r~1.02 -- NOT carbon/martensitic steel)",
            shell_name="solar-glow-drh-frame-air-316L",
            # NOTE the name dodges 'backshell' ON PURPOSE: scripts/ref_figures.py asserts
            # exactly one enclosure/*backshell*.stl and dies inside the fab job otherwise.
            brace_name=None,       # nothing retains a brace without a floor
            coverage_floor=None,
        ),
    }
    for name, d in v.items():
        d["stack"] = round(d["floor"] + d["cavity"] + BOARD_TH, 2)   # 3.40 / 2.42 / 1.80
        d["screw_len"] = _pick_screw(d["stack"])                     # 3.0  / 2.0  / 1.6
        d["span"] = round(d["cavity"] - AIR - SLA_WEB, 2) if d["brace"] else None
    return v


VARIANTS = _mk_variants()


def variant_span(name):
    s = VARIANTS[name]["span"]
    if s is None:
        raise ValueError(f"variant '{name}' has no brace, so no span limit")
    return s


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
# not carried bare, and 0.40 mm of waffle-backed floor survives under the valleys.
# AS FINE AS THE MACHINING HONESTLY GOES (2026-07-30, on request). Every number below
# is a floor with an owner:
#   groove 0.8 = O0.6 tool + 0.2 side clearance. O0.6 solid carbide slotting 0.30 deep
#     (0.5xD) across ~40 mm runs in Ti-6Al-4V is routine engraving-grade work; O0.5
#     would buy 0.1 mm of fineness at real breakage-and-cycle risk over ~36 long slots,
#     and zero-clearance slotting stays banned (burnishes in Ti, undersizes with wear
#     -- the same rejection recorded when the O1.0 groove was sized).
#   rib 0.6 = tolerance + refinish. +-0.05 per wall puts +-0.1 on a rib: at 0.6 that is
#     +-17%, the finest width where row-to-row variation stays invisible and a bead
#     blast does not knife-edge the top. Relief 0.40 on 0.6 wide = 0.67 aspect: rigid.
#   pitch 1.4 = the sum. 2.3x finer than the 3.2 it replaces; 18 rows per field. The
#     old note said "finer reads as knurl" -- at 1.4 it reads as reeding, and that is
#     now the point. Coarser fallbacks if the shop balks, in order: groove 1.0 (O0.8),
#     groove 1.2 (O1.0, the previous sizing). Cycle-time cost of O0.6: the groove
#     network is that tool's work alone, roughly +30-60 min of spindle time on the Ti
#     quote. The G engraving study aligned its baselines to FIN_PITCH; it re-derives
#     from these constants when it is picked.
# The pitch is DERIVED, not declared. A declared pitch leaves a remainder, and the
# remainder pools at the outer edge as a gutter wider than every other gap -- 2.05
# against 0.8 at the last sizing, reviewer-visible as "room for one more fin". So the
# layout closes exactly instead: from the boss-line anchor to the field edge, N ribs
# and N equal gaps consume the span completely, N maximised subject to the groove
# floor. The derived gap lands at 0.792: 8 um under the 0.80 target, 0.192 of side
# clearance for the O0.6 (16% of diameter, comfortably normal practice), floored at
# FIN_GROOVE_MIN with the DRU's hair-under philosophy so at-spec geometry cannot
# coin-flip. Result: EVERY gap on the back -- grooves, outer gutter, boss-line gutter
# -- is the same number. FIN_PITCH / FIN_GROOVE / FIN_ROWS are computed at the bottom
# of this section and stay importable (the G engraving study reads FIN_PITCH).
FIN_RIB_W  = 0.6           # rib width: tolerance + refinish floor (see commit trail)
FIN_GROOVE_MIN = 0.78      # groove floor: O0.6 tool + 0.18 clearance floor (target 0.2)
FIN_PROUD  = 0.10          # rib tops stand this proud of the art field. CAPPED here by
                           # law: the +0.15 BEARING PLANE stays above them (tops 0.05
                           # under it), so extra relief goes DOWN, never up. The law was
                           # AMENDED 2026-07-31: the bearing plane is the frame PLUS the
                           # medallion crests (medallion.py), coplanar by a shared
                           # finishing pass and lapped together after the blast -- the
                           # crests wear only where the part already bears, and a
                           # minute on the plate restores them. Ribs stay under it.
FIN_VALLEY = 0.60          # ...and valleys cut this far into the 1.00 floor -> 0.70 felt
                           # relief, 0.40 web. Was 0.30/0.70-web; deepened 2026-07-30
                           # after a depth-budget analysis. The 0.40 web is the honest
                           # maximum, each line item owned: it matches SLA_WEB = 0.40
                           # (the resin floor -- Ti at 0.40 is enormously stronger than
                           # resin at 0.40); the web is a WAFFLE strip 0.79 wide between
                           # ribs backed by the brace-filled cavity (t/span 0.5), not a
                           # membrane; and the fins are machined BEFORE the cavity is
                           # hollowed, so cutting never happens on a diaphragm (op-order
                           # callout in enclosure/README). Costs accepted: two O0.6
                           # passes (1xD) instead of one, and residual-stress bow risk
                           # on the 43 mm field -- countered by the stress-relieved
                           # stock callout. Below a 0.40 web there is no precedent floor
                           # left to stand on: do not go deeper without a new analysis.
                           # Bonus this buys: the engraving depth ceiling (any cut <=
                           # FIN_VALLEY adds no new thinnest section) rises with it.
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


# ---- fin fields as a POUR: the texture floods the band, edge to edge -----------------
# The model is a copper fill. The zone is the ENTIRE art-field band -- ribs run from the
# frame base on one side to the frame base on the other, and the field's own rounded
# corners clip them -- and the boss keepouts are the pads: the texture wraps each one at
# the uniform BOSS_R + FIN_BOSS_CLR clearance arc, as far in as the tool can reach.
# What makes this read designed rather than accidental is that ONE rule governs every
# boundary interaction: same clearance at every boss, same termination at every edge,
# and the pour's min-width discipline (the O1.0 back cutter's opening) decides what is
# too narrow to exist, exactly like a fill's minimum width. Ribs stand 0.10 proud and
# die into the frame base 0.05 below the frame top, so the fins grow out of the border
# instead of stopping short of it. The rib grid's remainder is NOT flush: the whole zone
# is cut, so the remainder becomes a valley-depth GUTTER above and below each rib run --
# continuous with the boss-wrap arcs, so a perimeter channel frames the stack and the
# wider edge channel reads as that frame, not as an uneven groove.
_BACK_CUT_R = 0.3          # O0.6 fin finisher: the pour's minimum-width rule. The O1.0
                           # stays for the art field / border; the groove network is the
                           # O0.6's work alone (nothing else fits a 0.8 slot).


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


def _fin_layout(rib_w=FIN_RIB_W, groove_min=FIN_GROOVE_MIN):
    """(rows, groove, pitch): the exact-closure layout, one derivation for everything.

    From the boss-line anchor to the field edge the span is consumed COMPLETELY by
    N ribs and N equal gaps (N-1 grooves + the outer gutter), N maximised subject to
    the groove floor. Both fields have the same span by symmetry -- asserted, because
    the whole point is that no gap anywhere is different from any other.
    """
    f = _back_field()
    ys = sorted({my for _mx, my in MOUNTS})
    s_bot = ys[1] - f.bounds[1]
    s_top = f.bounds[3] - ys[2]
    assert abs(s_bot - s_top) < 1e-9, "fields lost their symmetry"
    n = int(s_bot // (rib_w + groove_min))
    g = (s_bot - n * rib_w) / n
    return n, g, rib_w + g


FIN_ROWS, FIN_GROOVE, FIN_PITCH = _fin_layout()   # 19 / 0.792 / 1.392 today; derived,
                                                  # so a field or rib change re-closes
                                                  # the layout instead of pooling a
                                                  # remainder at the outer edge


def fin_runs(rib_w=FIN_RIB_W):
    """Per-field rib centrelines and the pour zone.

    The grid anchors on the MID-BOSS LINES: the innermost rib's flank sits exactly ON
    the boss centreline -- as close to the card's centre as a row can get without
    crossing the bosses -- and walks outward at the DERIVED pitch, which closes the
    span exactly (see _fin_layout): the outer gutter equals the grooves equals the
    boss-line gutter. (fin_band(), the PV-gap reference, defines the clear centre;
    the medallion -- Ø25.7 on that centre, medallion.py -- spans y 31.6..57.3 and
    stays clear of the zones' inner edges at 29.29/59.61 by >= 1.7.)
    """
    n, g, pitch = _fin_layout(rib_w)
    field = _back_field()
    fx0, fy0, fx1, fy1 = field.bounds
    blockers = unary_union([Point(mx, my).buffer(BOSS_R + FIN_BOSS_CLR, resolution=48)
                            for mx, my in MOUNTS])
    ys = sorted({my for _mx, my in MOUNTS})
    inner_bot, inner_top = ys[1], ys[2]               # 28.5 / 60.4: the mid-boss lines
    runs = []
    for outer, inner, sgn in [(fy0, inner_bot, 1), (fy1, inner_top, -1)]:
        cys = sorted(inner - sgn * (rib_w / 2 + i * pitch) for i in range(n))
        z0, z1 = (outer, inner + sgn * g) if sgn > 0 else (inner + sgn * g, outer)
        zone = field.intersection(box(fx0 - 1, z0, fx1 + 1, z1)).difference(blockers)
        runs.append((zone, cys))
    return runs


def fin_region(rib_w=FIN_RIB_W):
    """The valley cut: the pour zone itself, opened at the cutter radius so the cut is
    what the O0.6 tool can actually make -- narrower nooks stay flush, the fill's
    minimum-width rule."""
    reg = unary_union([z for z, _cys in fin_runs(rib_w)])
    reg = (reg.buffer(-_BACK_CUT_R, join_style=1, resolution=32)
              .buffer(_BACK_CUT_R, join_style=1, resolution=32))
    return unary_union([_dedupe(g) for g in
                        (reg.geoms if reg.geom_type == "MultiPolygon" else [reg])])


def fin_ribs(rib_w=FIN_RIB_W):
    """Stadium ribs in the pour: each rib is its centreline clipped to the moat-eroded
    zone and buffered back with round caps, so every tip is full-radius and keeps the
    same DERIVED groove to every boundary it approaches -- frame base, boss-wrap arc,
    gutter edge. The pour still floods the whole band; the ribs float in it. The
    erosion is backed off by EPS because the innermost row's flank sits exactly ON the
    boss line, i.e. exactly on the eroded boundary, and an exact-boundary intersection
    is numerically empty -- the row would vanish."""
    from shapely.geometry import LineString
    _n, moat, _pitch = _fin_layout(rib_w)
    EPS = 0.01
    region = fin_region(rib_w)
    out = []
    for zone, cys in fin_runs(rib_w):
        ero = zone.buffer(-(rib_w / 2 + moat - EPS), join_style=1, resolution=48)
        zx0, _zy0, zx1, _zy1 = zone.bounds
        for cy in cys:
            seg = ero.intersection(LineString([(zx0 - 1, cy), (zx1 + 1, cy)]))
            if seg.is_empty:
                continue
            segs = seg.geoms if seg.geom_type in ("MultiLineString", "GeometryCollection") else [seg]
            for s in segs:
                if s.length < rib_w:              # a stub shorter than it is wide is debris
                    continue
                g = s.buffer(rib_w / 2, resolution=32).intersection(region)
                for gg in (g.geoms if g.geom_type == "MultiPolygon" else [g]):
                    if gg.area > 0.8:
                        out.append(_dedupe(gg))
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
    # STEP validity gate (2026-08-01): every solid this repo ships passes through this one
    # function, so this is the single place OCC's own B-rep checker runs. An invalid shape
    # (self-intersecting shell, bad orientation, corrupt topology) out of a cadquery/OCC
    # version bump would otherwise flow silently into the STEP the fab receives -- the STL
    # mesh gate (scripts/check_mesh.py) sees only the tessellation, not the B-rep.
    from OCP.BRepCheck import BRepCheck_Analyzer as _BCA
    for _obj in (solid.vals() if hasattr(solid, "vals") else [solid]):
        _shape = getattr(_obj, "wrapped", _obj)
        if not _BCA(_shape).IsValid():
            raise SystemExit(f"export_step_stable: OCC BRepCheck says the solid bound for "
                             f"{path} is INVALID -- refusing to export")
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
