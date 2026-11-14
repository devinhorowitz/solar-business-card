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

import math
import os
import sys

from shapely.geometry import box, LineString, Point, Polygon
from shapely.ops import unary_union

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from board_parts import parts as board_parts   # noqa: E402

# ---- board / cavity -------------------------------------------------------------------
W, H = 50.80, 88.90
BOARD_TH = 0.60
BOARD_R = 3.0              # the board's corner radius (was the shell CAD's own `R`)
TOOL_R = 1.0               # dia 2.0 finisher -> R1.0 internal corners
# THE BOARD IS A PRESS FIT IN ITS RECESS, BY DECISION (DRH, 2026-11-13). The recess is cut
# 0.05 smaller than the board on every flat (relieved at the four corners, corner_clr in the
# shell CAD). Until then this number had three homes -- the shell CAD, its DRAWING-gen and
# _back_field() below -- and the repo described it three ways (press fit, "treat as a slip
# fit", "SLIP FIT, NOT A PRESS FIT"). Against a routed outline of +-0.1 to +-0.2 a board at
# the top of its tolerance will not enter titanium: its FR4 EDGE is sanded at assembly, and
# enclosure/README.md says so. The interference is the intent; the sanding is the step.
EDGE_FIT = -0.05


def recess_poly():
    """The board recess in plan, board coords: the board outline moved EDGE_FIT on every
    flat, corners at BOARD_R + EDGE_FIT -- the rounded rectangle the shell cuts at the seat
    and the floor-to-seat cavity is held inside."""
    e, r = max(0.0, -EDGE_FIT), BOARD_R + EDGE_FIT
    return (box(e, e, W - e, H - e).buffer(-r, join_style=1, resolution=48)
            .buffer(r, join_style=1, resolution=48))
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


# Per-part IN-PLANE clearance exceptions (2026-08-23), the XY twin of AIR_EXCEPTIONS.
# CLR is one number for every part, which silently equated two very different risks:
# a machine-placed 0402 lands within a few hundredths, while SC1-SC4 are HAND-SOLDERED
# (they are on the hand-buy list, not the PCBWay CPL -- scripts/bom_split.py) and carry
# human placement slop on a 17 x 39 mm body.
#
# ROTATION dominates, not translation: 1 deg of tweezer rotation swings the corner of a
# 39 mm cap by 19.5 * sin(1 deg) = 0.340 mm, and 1.5 deg by 0.510 mm. 0.75 covers 1.5 deg
# plus ~0.24 mm of translation. The caps cut THROUGH (h + air > gap), so this widens the
# open bays they sit in rather than any pocket -- no web is affected, only footprint area.
# Cost is bounded and was measured before choosing: 222.1 mm of the caps' 406 mm perimeter
# faces brace material (the rest already faces open bay), so +0.50 costs ~111 mm2 and the
# narrowest web goes 2.29 -> 1.79 mm (west rail), still one connected piece.
# WHAT THE TRADE COSTS, measured from the BOARD rather than from this constant: in four of
# the sixteen cap edge-directions 0.75 is now WIDER than the distance to a real neighbouring
# part, so in those four the lateral backstop MOVED FROM RESIN TO A COMPONENT --
#     SC4 -X -> L2   0.50 mm   (the AEM10300's power inductor)
#     SC3 -Y -> R15  0.57 mm   (STO sense divider, upper leg)
#     SC2 -X -> C6   0.65 mm
#     SC1 +X -> C11  0.70 mm
# At CLR 0.25 the brace caught the cap first in all four; ray-cast on the pre-change mesh read
# 0.25/0.26 in every closed direction and >2.00 in every open one, which also cross-checks the
# bays against the board's own openings. This is NOT a placement constraint -- the brace is
# fitted after reflow, so bay width governs whether the brace fits over an off-nominal cap, and
# lateral restraint only afterwards. It does mean an edge drop now loads L2/R15/C6/C11 instead
# of resin. Accepted: a bay too narrow to fit over a hand-placed cap is the worse failure, and
# PCB/README.md's HAND-SOLDER CAUTION carries the assembly-side half.
# DNP FOOTPRINTS ARE NOT STOPS -- J1 sits 0.49 mm off SC1 and TP2/TP4 likewise, but all 13 dnp
# parts (C30, J1, JP1, SW2, TC1, TC1/b1, TP1-7) are bare pads on a standard build. Reading them
# as stops overstates SC1's restraint and understates its rotation limit by 2x.
# AND 0.75 IS NEAR-MINIMAL, NOT GENEROUS -- the paragraphs above sized it from HAND SLOP
# (rotation plus translation) and that was only half the reason. The SCPC datasheet gives
# the cans as 17.0 +-0.5 wide and 39.0 / 28.5 +0.5/-0.0 long (part_heights.SUPERCAP_BODY_TOL,
# recorded 2026-08-23 from the same drawing as the 1.70 height). BOTH in-plane dimensions
# can run 0.50 over nominal. A cap indexed on two edges -- which is what the reflow shim
# does, scripts/reflow_shim.py -- puts that entire +0.50 onto its two free edges, so a free
# side needs 0.50 + the 0.10 datum gap = 0.60 before any placement error at all. 0.75 leaves
# 0.15 mm on a free edge. The sentence here used to end "THIS IS WHY THE 111 mm2 IS NOT
# COMING BACK" -- that was true only of SHRINKING the number, and it was superseded the same
# day by making it directional (below). ANISOTROPY RECOVERED 101.9 of the 111.2 mm2 on the
# max brace and 100.0 of 109.3 on the lite, 92% and 91%, still one piece. What it does NOT
# recover is the narrowest web: the pinch at (3.45, 32.33) is on SC1's WEST edge, which is a
# FREE side, so it holds 0.75 and the neck stays 1.80 mm (was 2.28 before #249).
# ANISOTROPIC, since 2026-08-23. A uniform 0.75 was the right total but the wrong shape:
# the reflow shim (scripts/reflow_shim.py) indexes each cap against TWO orthogonal edges,
# so those edges are located to the shim's own 0.10 mm datum gap while the body tolerance
# -- all +0.50 of it -- lands on the two FREE edges. Spending 0.75 on all four sides pays
# the tolerance price four times for a part that can only grow twice.
#
# Splitting it recovers the two datum sides AND undoes the backstop trade recorded above:
# the four at-risk parts all sit on DATUM edges (SC4/L2 W, SC3/R15 S, SC2/C6 W, SC1/C11 E),
# so at CLR_DATUM the resin catches the cap before the component does again, in every one.
#
# THIS COUPLES THE BRACE TO THE SHIM. A cap seated without the shim can sit anywhere in the
# old envelope and the brace will not go on. That is a deliberate trade, not an oversight:
# these pads are under the can, so the caps cannot be hand-seated with an iron anyway, and
# the shim is now the specified way to reflow them.
CAP_DATUM = {"SC1": ("E", "N"), "SC2": ("W", "N"),
             "SC3": ("E", "S"), "SC4": ("W", "S")}
CLR_DATUM = 0.25   # datum edge: located by the shim, so machine-placed precision applies
CLR_FREE = 0.75    # free edge: SUPERCAP_BODY_TOL 0.50 + the 0.10 datum gap + 0.15 margin


def clr_sides(ref):
    """Per-edge in-plane clearance. Machine-placed parts are uniform CLR."""
    d = CAP_DATUM.get(ref)
    if d is None:
        return {s: CLR for s in "EWNS"}
    return {s: (CLR_DATUM if s in d else CLR_FREE) for s in "EWNS"}


def clr_for(ref):
    """The scalar, worst-case answer -- what a caller that cannot be directional must use."""
    return max(clr_sides(ref).values())


# ---- the MAX-MATERIAL outline (2026-11-13) ----------------------------------------------
# The datum gap is the reflow shim's own constant, read out of its source rather than copied
# (scripts/ is not on this module's import path, and the shim imports this module lazily).
# ast, not exec: nothing in that file runs to get one number out of it.
def _shim_clr():
    import ast
    src = os.path.join(os.path.dirname(HERE), "scripts", "reflow_shim.py")
    for node in ast.parse(open(src, encoding="utf-8").read()).body:
        if (isinstance(node, ast.Assign) and len(node.targets) == 1
                and getattr(node.targets[0], "id", None) == "SHIM_CLR"):
            return float(ast.literal_eval(node.value))
    raise RuntimeError("scripts/reflow_shim.py has no SHIM_CLR -- the datum gap has no home")


from part_heights import SUPERCAP_BODY_TOL as _BODY_TOL      # noqa: E402
SHIM_DATUM_GAP = _shim_clr()


def part_envelope(ref, poly):
    """The largest outline the part can have ON THE BOARD -- what metal must clear, as
    opposed to part_keepout(), which is what the RESIN keeps off it.

    A machine-placed part is its nominal outline. A supercap is not: its body runs up to
    SUPERCAP_BODY_TOL over nominal on both in-plane axes, and the reflow shim indexes it on
    its two DATUM edges, so the whole tolerance lands on its two FREE edges (+TOL + the
    shim's datum gap) and the datum edges move by the gap alone. On this board every cap's
    FREE edge faces the nearest board edge (CAP_DATUM: the shim indexes from inside), so a
    max-material can stands 1.00 - 0.60 = 0.40 mm off the north or south edge, not 1.00.
    Everything that puts titanium near a cap -- the lip bands, the boss flats -- reads this,
    or it is clearing a can that may not be the one on the board."""
    d = CAP_DATUM.get(ref)
    if d is None:
        return poly
    return part_keepout(ref, poly, sides={s: (SHIM_DATUM_GAP if s in d
                                              else _BODY_TOL + SHIM_DATUM_GAP) for s in "EWNS"})


def part_keepout(ref, poly, sides=None):
    """The in-plane keepout for ONE part, and the single definition of it.

    Every consumer goes through here -- brace_footprint and both brace-CAD call sites --
    so a directional clearance cannot be applied in one place and a uniform one in
    another. `sides` overrides the table (scripts/reflow_shim.py cuts the same geometry
    at its own uniform gap); it is an explicit argument rather than module state, the
    same rule VARIANTS follows.
    """
    c = clr_sides(ref) if sides is None else sides
    if len(set(c.values())) == 1:
        return poly.buffer(next(iter(c.values())), join_style=2)
    x0, y0, x1, y1 = poly.bounds
    # Mitred buffer of a rectangle IS the offset rectangle, so clipping the largest
    # offset to the per-edge box gives exact square-cornered per-side growth. The
    # intersection keeps this honest for a non-rectangular body too.
    return poly.buffer(max(c.values()), join_style=2).intersection(
        box(x0 - c["W"], y0 - c["S"], x1 + c["E"], y1 + c["N"]))
CLR = 0.25                 # in-plane clearance around a part
SLA_WEB = 0.40             # thinnest resin that may remain OVER a pocket
SLA_WALL = 0.60            # thinnest in-plane feature we will print
PRINT_WALL = 0.25          # ...and the floor UNDER that, for the few features let off SLA_WALL on
                           # purpose (the ferrite channel's own walls, the TP2/TP3 neck): the wall
                           # the print spec's printer class holds (enclosure/brace/README.md, DRH
                           # 2026-11-13). An exception from 0.60 is not an exception from this --
                           # the channel's east ridge tapered to NOTHING at both ends until
                           # 2026-11-14, two feather tips no printer class holds.
SPAN_LIMIT = GAP - AIR - SLA_WEB          # 1.18 (comment said 1.28 until 2026-08-07 --
                                          # written when AIR was 0.12 and never updated;
                                          # the number here is DERIVED, trust the formula)
MIN_PIECE = 25.0           # smaller than this is print debris, not support
SINGLE_PIECE = True        # ship one part; see brace_footprint()
DROPPED_AREA = 0.0         # set by brace_footprint(): support given up to stay single-piece
DROPPED_COUNT = 0
DROPPED = []               # ...and the pieces themselves, so a caller can say WHAT was given up
                           # (the brace drawing: all four solar-cell tab rails, 2026-11-12)
WALL_FIT = 0.05            # brace-to-cavity-wall contact fit

# ---- shell ----------------------------------------------------------------------------
BOSS_R = 2.60
PILOT_R = 0.80
BOSS_CLR = 0.20            # Ti boss to part/pad
THREAD_KEEP = 1.30         # never scallop inside this: the M2 thread lives at r0.80..~1.0
LIP_CLR = 0.30             # lip edge to nearest part body or pad
LIP_MAX = {"W": 2.5, "E": 2.5, "S": 2.0, "N": 2.0}
LIP_MIN = 0.30             # a band narrower than this is cut as NO lip (2026-11-13). Beside the
                           # supercaps the honest band is 0.10: a max-material can stands 0.40
                           # off the edge (part_envelope) and the lip stands LIP_CLR off that.
                           # Of 0.10, 0.05 is under the press-fit recess wall and the rest is
                           # the lip's own 0.10 edge break, so it seats nothing, and the 0.17
                           # slot it leaves under a corner boss is too narrow for the Ø2.0 to
                           # enter -- the slot's fill reached 0.066 into a max-material can.
                           # Same as LIP_CLR, so "no lip" and "a lip a part can trust" are the
                           # only two answers.

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
    for r, p, _h, src in (ps if ps is not None else _cached_parts()):
        # the max-material outline, not the nominal one (2026-11-13): sized from a nominal
        # SC1 the relief left ring metal whose fillet reached 0.011 mm2 into the can that
        # the cap's own tolerance allows, at all four caps' outer corners
        p = part_envelope(r, p)
        if src == "model" and p.distance(ring) < LIP_CLR:
            out.append(p.buffer(LIP_CLR + TOOL_R, join_style=1, resolution=48))
    return out
COIL_CLR = 1.00            # grounded metal to coil copper. Raised from 0.30 on request:
                           # the east lip is the only grounded feature that comes near the
                           # antenna [NOT SO -- the two east mid-span bosses do too, and stood
                           # 0.874 / 0.966 off it until 2026-11-14: boss_coil_cuts() below],
                           # and 1.00 gives 3.3x the standoff while still leaving a
                           # 1.25 mm lip -- wider than the flat 1.0 the original design used.
                           # The tradeoff is linear and lives on one line: 0.30 -> 1.95 mm
                           # lip / 490 mm2, 1.00 -> 1.25 / 463, 1.25 -> 1.00 / 442, and
                           # 1.50 leaves 0.75 mm, below the design's own floor.
# MEASURED from the board, not asserted. The hard-coded 48.40 was 0.15 mm optimistic --
# LA/LB copper reaches x48.550 -- so the lip sized against it overhung the antenna.
from board_parts import coil_extent as _coil_extent, coil_tracks as _coil_tracks   # noqa: E402
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


def brace_cavity():
    """The outline a brace may fill: cavity_rect() cut back to the shell's ACTUAL void, then
    shrunk by the wall fit.

    cavity_rect() is the scalar rectangle _CAV -- a 1.00 mm east lip -- and the brace used
    to be cut from it alone. The shell is cut from cavity_void_poly(), whose east lip the
    coil clamp in _lip_reach() sets at W - COIL_EAST = 1.25 mm. Same module, two answers:
    the committed braces came out 0.20 mm WIDER than the committed cavities along the whole
    middle band (east face x49.750 against a wall at x49.550; 9.02 mm3 of overlap on max,
    5.94 on lite, measured on the STEPs 2026-11-12), and check [8] measured the brace
    against cavity_rect() again, so it agreed. Wherever the per-band lip is no wider than
    the ring -- west, north, south today -- the intersection changes nothing.

    AND THE VOID IS THE ONE THE CUTTER LEAVES (2026-11-13). The shell is modelled with its
    boss-to-wall junctions sharp, and the sheet tells the shop to finish them with a Ø2.0
    tool -- which leaves R1.0 of metal in each. The brace was cut to the sharp model, so at
    the four bosses whose discs meet the cavity wall beside the brace's band it ran 0.225
    mm (east) and 0.055 mm (west) into those fillets: sectioned on the committed STLs, and
    invisible to assembly_drc [B], which measured the sharp shell too. cavity_as_milled()
    is the void with the finisher's radius applied."""
    return (cavity_rect().intersection(cavity_as_milled())
            .buffer(-WALL_FIT, join_style=1, resolution=64))


def cavity_as_milled(tool_r=TOOL_R):
    """The cavity void at the board-rest plane AS A RADIUS-tool_r FINISHER LEAVES IT: board
    area less the lip metal and the boss islands, opened by the tool. Every inside corner of
    the metal that the model leaves sharp comes back as a tool_r fillet; nothing else moves.

    The brace is cut to this, and scripts/assembly_drc.py [H] applies the same opening to
    the SECTIONED shell, so the rule and the part are measured by two different readers."""
    void = (box(0.0, 0.0, W, H).difference(lip_metal_poly())
            .difference(unary_union([boss_island(mx, my) for mx, my in MOUNTS])))
    return (void.buffer(-tool_r, join_style=1, resolution=48)
                .buffer(tool_r, join_style=1, resolution=48))


def brace_footprint(span=None, keepout=None):
    """[polygon] -- the pieces the brace is actually made of, largest first.

    `span=None` is the max variant (module SPAN_LIMIT); per-variant callers pass
    variant_span(name). DROPPED_AREA/DROPPED_COUNT describe the LAST call -- a
    per-variant caller should read them immediately, before any other call."""
    cav = brace_cavity()
    _ko = keepout or part_keepout
    keep = unary_union([_ko(_r, p) for _r, p in blockers(span=span)])
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
    global DROPPED_AREA, DROPPED_COUNT, DROPPED
    DROPPED_AREA = sum(g.area for g in pieces[1:])
    DROPPED_COUNT = len(pieces) - 1
    DROPPED = list(pieces[1:])
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
            shell_name="solar-glow-drh-v4_0-backshell-0p6b-brace-Ti-max",
            brace_name="solar-glow-drh-diffuser-brace",
            coverage_floor=0.32,   # ledgered min. UNCHANGED 2026-11-12 and re-measured: 33.01 %,
                                   # the same figure as before by coincidence of two moves.
                                   # The footprint lost the 0.25 mm east strip it never had
                                   # room for (1320.3 -> 1313.6 mm2, see brace_cavity()), and
                                   # the denominator is now that same true cavity (3978.9 mm2,
                                   # was the 3999.5 rectangle) instead of a cavity the shell
                                   # does not have. Against the OLD denominator this brace
                                   # would read 32.84 %. DROPPED_AREA 213.1 -> 202.6 mm2.
                                   # RESTORED 2026-08-23 evening, 0.30 -> 0.32:
                                   # the anisotropic bays put coverage back to 33.01% (it was
                                   # 33.25% before #249 widened them), so the floor returns to
                                   # what it was before the widening rather than staying at the
                                   # relaxed value. History of the round trip follows.
                                   # RE-LEDGERED 2026-08-23, 0.32 -> 0.30, and
                                   # DELIBERATELY, not because a board change eroded it: CLR_EXCEPTIONS
                                   # bought SC1-SC4 0.75 mm of in-plane clearance for HAND-SOLDER slop,
                                   # which costs 111 mm2 of footprint and measures 30.46%. The floor is
                                   # a regression tripwire (see the check's own text: "re-ledger
                                   # coverage_floor WITH the reason"), not a structural spec -- nothing
                                   # states a required support area. What was checked instead: the
                                   # footprint stays ONE piece, the narrowest web goes 2.29 -> 1.79 mm
                                   # (west rail), and DROPPED_AREA actually FELL 255.6 -> 213.1 mm2
                                   # because the slivers it used to discard no longer form.
                                   # Prior text: (measures 0.329 after the 2026-08-08 LDO-island
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
            coverage_floor=0.25,   # ledgered min. UNCHANGED 2026-11-12: 27.28 % -> 27.25 % of the
                                   # true cavity (footprint 1090.9 -> 1084.1 mm2, same east
                                   # strip as max; 27.11 % against the old rectangle).
                                   # RESTORED 2026-08-23 evening, 0.24 -> 0.25 --
                                   # anisotropy took the lite brace back to 27.28% (27.51% pre-#249).
                                   # RE-LEDGERED 2026-08-23, 0.25 -> 0.24, same cause
                                   # as max: the caps are hand-soldered in this variant too, so they
                                   # take the same 0.75 mm. Measures 24.78%, one piece.
                                   # Prior text: (measures 0.272 after the 2026-08-08 island
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


COIL_REF = "NFC COIL"      # the one lip limiter that is not a part: the coil clamp on the east edge


def _lip_limits(edge, lo, hi, ps=None):
    """(width, [limiter...]) for the stretch lo..hi of `edge` -- the ONE statement of how
    wide the lip may be there and of what stops it being wider.

    The limiters are the parts (by refdes) and, on the east edge, the coil clamp (COIL_REF)
    whose own reach, cut to the same 0.01 the lip is, IS the width returned; an unlimited
    stretch (LIP_MAX) has none. _lip_reach() is the first half of this and lip_band_limits()
    the second, so anything that has to say in WORDS why a band is the width it is -- the
    shell drawing's lip note -- reads the name out of the loop that sized the band, the way
    boss_foul_refs() does for the boss flats. That note was typed until 2026-11-12, and what
    it had typed was "C7 (x49.55, THE ONE EAST-EDGE PART LEFT ...)": a capacitor that had
    not been on the board for three months."""
    ps = ps or _cached_parts()
    cands = []
    for ref, poly, _h, _src in ps:
        # TWO THINGS this used to get wrong, both found 2026-11-13 by opening the cut void
        # by TOOL_R and measuring it against the parts (TODO.md, the C24 and supercap items):
        #  * A supercap was measured at NOMINAL. Its free edge faces the board edge, so the
        #    0.70 / 0.72 bands it "allowed" sat inside the can's own tolerance -- titanium
        #    where a max-material can may be. part_envelope() is the can that has to fit.
        #  * A part only narrowed the stations it OVERLAPPED, so a wide band could start at
        #    the next 0.5 station -- 0.10 past C24's end -- and the finisher's R1.0 fillet in
        #    the step corner then reached to 0.099 of a live STO_SNS pad, against LIP_CLR
        #    0.30. Growing the part's along-edge extent by TOOL_R puts the step at least a
        #    tool radius past it: the corner fillet's arc is then >= LIP_CLR off a part that
        #    stands LIP_CLR off the narrow band ((R - LIP_CLR)^2 + 0 <= (R - LIP_CLR)^2).
        x0, y0, x1, y1 = part_envelope(ref, poly).bounds
        if edge in ("W", "E"):
            if y1 + TOOL_R <= lo or y0 - TOOL_R >= hi:
                continue
            d = x0 if edge == "W" else (W - x1)
        else:
            if x1 + TOOL_R <= lo or x0 - TOOL_R >= hi:
                continue
            d = y0 if edge == "S" else (H - y1)
        cands.append((d - LIP_CLR, ref))
    if edge == "E":
        cands.append((W - COIL_EAST, COIL_REF))
    cut = lambda v: max(0.0, round(v, 2))
    width = cut(min([LIP_MAX[edge]] + [v for v, _n in cands]))
    who = [] if width >= LIP_MAX[edge] else [n for v, n in cands if cut(v) == width]
    if width < LIP_MIN:          # a sliver is not a seat -- see LIP_MIN; the limiter keeps its name
        width = 0.0
    return width, who


def _lip_reach(edge, lo, hi, ps=None):
    return _lip_limits(edge, lo, hi, ps)[0]


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


def lip_band_limits(edge, step=0.5):
    """[(lo, hi, width, [limiter...])] -- lip_bands(), each band with what limits it.

    The bands and widths ARE lip_bands(); the names are _lip_limits() over the same
    stations, so a band and its reason cannot be read from two different computations."""
    out = []
    for lo, hi, w in lip_bands(edge, step):
        who, a = [], lo
        while a < hi - 1e-9:
            b = min(a + step, hi)
            who += [n for n in _lip_limits(edge, a, b)[1] if n not in who]
            a = b
        out.append((lo, hi, w, who))
    return out


def _void_opened(tool_r=TOOL_R):
    """The board rect inset by the per-band lip and opened by the finisher radius: the void
    BEFORE any relief. Split out of cavity_void_poly() so lip_relieved() can be asked which
    parts that opening leaves metal on without cutting the void a second way."""
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
    return (void.buffer(-tool_r, join_style=1, resolution=48)
                .buffer(tool_r, join_style=1, resolution=48))


def _lip_relief(poly, tool_r=TOOL_R):
    """The keep-out cavity_void_poly() opens around one relieved part."""
    return poly.buffer(LIP_CLR + tool_r, join_style=1, resolution=48)


def lip_relieved(tool_r=TOOL_R, _opened=None):
    """[(refdes, outline)] -- the parts cavity_void_poly() relieves: those the tool-radius
    opening would otherwise leave lip metal on. The one statement of it; the void is cut by
    this list and lip_as_cut() names from it.

    WHY ANYTHING OUTSIDE THE VOID NEEDS THE NAMES. The relief is LIP_CLR + tool_r = 1.30 mm
    all round, sized for "a few parts near a step" and a 0.088 mm2 overlap. All four
    supercaps trip it -- the fillet a band step leaves clips each can's corner -- and they
    sit 1.00 mm off the north and south edges, so 1.30 takes the WHOLE strip beside them:
    the 0.70 / 0.72 mm bands lip_bands() reports there are not in the metal. Sectioned
    2026-11-12 on all three variants' STLs, the committed ones and a rebuild: the board edge
    is bare from x4.3 to 22.9 and x27.7 to 46.3 on the south, x4.3 to 23.0 and x27.8 to 46.5
    on the north -- 74.6 of the 101.6 mm of short edge. lip_bands() is the INPUT to the cut,
    not a description of the part, and a sheet that recited it would dimension a ledge that
    does not exist.

    SINCE 2026-11-13 THIS RETURNS NOTHING, and that is the design working. The relief above
    was doing by accident what the caps' tolerance requires on purpose: a max-material can
    stands 0.40 off the edge, not 1.00. _lip_limits() measures a cap at part_envelope() and
    cuts a band under LIP_MIN to none, and steps every band a tool radius past its part, so
    no band-step fillet lands on a part and nothing is left to relieve. It stays as the
    backstop for a part the band rules do not anticipate."""
    opened = _void_opened(tool_r) if _opened is None else _opened
    lip_now = box(0.0, 0.0, W, H).difference(opened)
    return [(r, p) for r, p, _h, _s in _cached_parts() if lip_now.intersection(p).area > 1e-6]


def cavity_void_poly(tool_r=TOOL_R, simplify=True):
    """Cavity void in board coords: the board rect inset by the per-band lip, opened by the
    finisher radius, plus local reliefs for what the tool then cannot reach."""
    opened = _void_opened(tool_r)

    # A dia 2.0 finisher cannot reach the concave corners a band step leaves, so the opening
    # puts material back over a few parts near a step -- a fixed 0.088 mm2 worst case that
    # does NOT improve at any band clearance (swept 0.30..0.80, identical). Dilating a
    # keep-out by the tool radius makes it tool-reachable by construction.
    stuck = [p for _r, p in lip_relieved(tool_r, opened)]
    if stuck:
        opened = opened.union(unary_union([_lip_relief(p, tool_r) for p in stuck]))
    # The void is BOARD area by definition, and until 2026-11 nothing held it there. A
    # relief dilated by LIP_CLR + tool_r runs past the board edge wherever a part sits
    # closer to it than that -- all four supercaps, 1.00 mm off the N and S edges -- so the
    # polygon reached y-0.30 / y89.20 (21.3 mm2 outside the board). The shell cuts this
    # polygon from floor to seat: 0.30 mm into the perimeter wall and UNDER the board
    # recess, four pockets a cutter coming down the cavity cannot reach. "Tool-reachable
    # by construction" was true in plan and false in section.
    opened = opened.intersection(box(0.0, 0.0, W, H))
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


def lip_metal_poly():
    """The lip the shell is BUILT with, in board coords: the per-band ledge cavity_void_poly()
    leaves, UNION the guaranteed ring less ring_reliefs() -- the two solids the shell CAD
    unions (build(): block minus void, then `lip.cut(reliefs)`, then union). Exact, not
    simplified. Today the ring adds nothing the ledge does not already have; it is in here so
    that the day it does, lip_as_cut() measures the metal and not half of it."""
    ring = ring_metal_poly()
    rel = ring_reliefs()
    if rel:
        ring = ring.difference(unary_union(rel))
    return unary_union([lip_poly(simplify=False), ring])


def _lip_cut_width(edge, t, metal, depth):
    """How far lip metal stands in from `edge` at station t, measured on `metal` (0.0 where
    the void reaches the board edge)."""
    a, b = {"W": ((0.0, t), (depth, t)), "E": ((W, t), (W - depth, t)),
            "S": ((t, 0.0), (t, depth)), "N": ((t, H), (t, H - depth))}[edge]
    hit = metal.intersection(LineString([a, b]))
    best = 0.0
    for seg in getattr(hit, "geoms", [hit]):
        if seg.geom_type != "LineString" or seg.is_empty:
            continue
        if seg.distance(Point(a)) < 1e-6:        # only the run that starts AT the board edge
            best = max(best, seg.length)
    return best


def lip_as_cut(edge):
    """[(lo, hi, width, [limiter...])] along `edge` -- the lip AS THE SHELL IS CUT, in a form
    a sentence can be written from. width 0.0 means no lip at all over that stretch.

    This is lip_band_limits() with the reliefs applied: beside every part lip_relieved()
    names, the lip is whatever LIP_CLR + TOOL_R leaves between that part and the edge --
    nothing, for a part closer than 1.30 mm -- over the stretch of the edge the relief
    reaches, and the limiter there is that part. Bands the relief removes are dropped; they
    are not in the metal.

    AND IT IS CHECKED AGAINST THE POLYGON BEFORE IT IS RETURNED, because a description that
    is merely derived from the same inputs as the cut is the gate this repo keeps being
    bitten by (boss_island() was clear of every part for three months while the titanium was
    not). Every 0.1 mm along the edge, clear of the corners, the width measured on
    lip_metal_poly() must lie between the narrowest and widest row within one relief reach
    of that station -- so it must EQUAL the row's width anywhere a band or a gap runs
    undisturbed, and only a blend or a relief arc is given room. A relief that bites a band
    this function does not know how to describe raises here instead of printing."""
    span = H if edge in ("W", "E") else W
    tool_r = TOOL_R                              # the shell's own; cavity_void_poly()'s default
    reach = LIP_CLR + tool_r
    line = {"W": ((0.0, 0.0), (0.0, H)), "E": ((W, 0.0), (W, H)),
            "S": ((0.0, 0.0), (W, 0.0)), "N": ((0.0, H), (W, H))}[edge]
    bands = lip_band_limits(edge)
    nominal = lambda t: next((w for lo, hi, w, _n in bands if lo - 1e-9 <= t <= hi + 1e-9), 0.0)

    cuts = []                                    # [lo, hi, width left, [refdes]]
    for ref, p in lip_relieved(tool_r):
        x0, y0, x1, y1 = p.bounds
        d = {"W": x0, "E": W - x1, "S": y0, "N": H - y1}[edge]
        left = max(0.0, round(d - reach, 2))
        p_lo, p_hi = (y0, y1) if edge in ("W", "E") else (x0, x1)
        if left > 0.0:
            # the relief stops short of the edge: over the part's own length the lip is cut
            # back to `left` -- if it was wider than that to begin with
            if left >= max(nominal(p_lo), nominal(p_hi), nominal((p_lo + p_hi) / 2.0)):
                continue
            cuts.append([p_lo, p_hi, left, [ref]])
            continue
        hit = _lip_relief(p, tool_r).intersection(LineString(line))
        for seg in getattr(hit, "geoms", [hit]):
            if seg.geom_type != "LineString" or seg.length < 1e-6:
                continue
            ts = [c[1] if edge in ("W", "E") else c[0] for c in seg.coords]
            cuts.append([max(0.0, min(ts)), min(span, max(ts)), 0.0, [ref]])
    cuts.sort()
    merged = []
    for c in cuts:                               # two reliefs that run into each other
        if merged and c[0] <= merged[-1][1] + 1e-9 and abs(c[2] - merged[-1][2]) < 1e-9:
            merged[-1][1] = max(merged[-1][1], c[1])
            merged[-1][3] += [r for r in c[3] if r not in merged[-1][3]]
        else:
            merged.append(c)

    rows = []
    for lo, hi, w, who in bands:
        keep = [(lo, hi)]
        for c_lo, c_hi, left, _refs in merged:
            if left < w:                         # a relief only ever REMOVES lip
                keep = [q for a, b in keep for q in ((a, min(b, c_lo)), (max(a, c_hi), b))
                        if q[1] - q[0] > 1e-9]
        rows += [(a, b, w, list(who)) for a, b in keep]
    rows += [(lo, hi, left, list(refs)) for lo, hi, left, refs in merged
             if left < max(nominal(lo), nominal(hi), nominal((lo + hi) / 2.0))]
    rows.sort()
    out = []
    for r in rows:                               # a band split by nothing rejoins itself
        if out and abs(out[-1][2] - r[2]) < 1e-9 and out[-1][3] == r[3] \
                and abs(out[-1][1] - r[0]) < 1e-9:
            out[-1] = (out[-1][0], r[1], r[2], r[3])
        else:
            out.append(r)

    metal = lip_metal_poly()
    corner = max(LIP_MAX.values()) + tool_r      # inside this the probe runs ALONG the next edge's lip
    depth = max(LIP_MAX.values()) + reach
    t = corner
    while t <= span - corner + 1e-9:
        near = [w for lo, hi, w, _n in out if lo <= t + reach and hi >= t - reach]
        got = _lip_cut_width(edge, t, metal, depth)
        if not (min(near) - 0.005 <= got <= max(near) + 0.005):
            raise RuntimeError(
                f"lip_as_cut('{edge}'): at {'y' if edge in ('W', 'E') else 'x'}{t:.1f} the "
                f"cut lip is {got:.3f} mm wide, outside the {min(near):.2f}..{max(near):.2f} "
                f"this description allows there -- the bands and reliefs no longer describe "
                f"the metal, so nothing may be printed from them until they do")
        t = round(t + 0.1, 6)
    return out


def boss_fouls(mx, my):
    """The keep-outs a boss at (mx, my) has to be cut back for: every part outline within
    BOSS_R of the boss axis, grown by BOSS_CLR with square corners.

    ONE home for the scallop, because it had two and they disagreed. boss_island() below
    subtracted these from its disc, the brace took its reliefs from that island and check
    [8] gated it (step 4 of check_enclosure_fit) -- while the shell CAD unioned a bare
    `circle(boss_r)` and never made the cut. The polygon was clear of every part by
    construction; the titanium was not: the committed shells put SC1 0.375 mm inside the
    two west bosses (SC3 0.305, SC4 0.326, SC2 0.174), found 2026-11-12 by an independent
    measurement of the STEP. The shell now cuts exactly this list out of each boss, so
    what [8] proves about the polygon is meant to hold for the metal -- and whether it
    does is measured, not inferred: scripts/assembly_drc.py [F] sections the emitted STL.

    A SUPERCAP IS CUT BACK BY ITS OWN BAY CLEARANCE, not BOSS_CLR (2026-11-13). BOSS_CLR is
    clearance from a part's NOMINAL outline, right for a machine-placed part; a supercap is
    hand-reflowed, its body tolerance lands on its two FREE edges (CAP_DATUM above), and all
    eight cap-to-boss adjacencies on this board are free edges. Cut back 0.20 from nominal,
    each flat stood 0.40 inside the envelope the brace's own bay already allows for the same
    can -- titanium the resin had been told the cap might occupy. The flat now uses the same
    per-edge numbers as the bay (clr_sides via part_keepout, the ONE definition of a part's
    keep-out), floored at BOSS_CLR, so brace and shell cannot disagree about how big a cap
    can be. Every flat still clears THREAD_KEEP; check_consistency gates that per boss.

    EACH KEEP-OUT CARRIES ITS DOGBONES (2026-11-13). A keep-out corner that lands inside the
    boss is an inside corner of the metal, and the Ø2.0 finisher cannot cut one: it leaves an
    R1.0 fillet there. At the two east mid-span bosses that fillet reached a max-material
    SC2 / SC4 by 0.113 / 0.130 mm (SolidCraft 0.134), while every gate measured the sharp
    corner. boss_cuts() adds the disc the tool sweeps to reach the corner, so the cut is one a
    TOOL_R cutter can make and the polygon is the metal.

    AND THE COIL IS A KEEP-OUT TOO (2026-11-14). COIL_CLR was written for the east lip, "the
    only grounded feature that comes near the antenna" -- and the lip was the only feature
    held to it. The two east mid-span bosses are grounded titanium at the same height, and
    they stood 0.874 and 0.966 mm from coil copper against the 1.00 the sheet prints for the
    lip beside them (ArtCraft measured 0.877 off the STEP; nothing here measured it at all).
    boss_coil_keepout() is the last entry of this list wherever the coil is within reach."""
    kps, dbs = boss_cuts(mx, my)
    out = [kp.union(unary_union([Point(c).buffer(TOOL_R, resolution=64) for c in d]))
           if d else kp for kp, d in zip(kps, dbs)]
    coil = boss_coil_keepout(mx, my)
    return out + ([coil] if coil is not None else [])


def boss_cuts(mx, my):
    """([keep-out], [[(cx, cy)...] per keep-out]) -- what comes out of the boss at (mx, my):
    each fouling part's keep-out, and for each one the centres of its TOOL_R dogbones.

    THE RULE: every corner of a keep-out within a tool's reach of the boss must be a corner
    the Ø2.0 finisher can actually get to. A corner that lands inside the disc is an inside
    corner of the metal; a corner just outside it can sit in a slot too narrow for the tool
    (under a corner boss the disc stands 0.22 mm off the recess wall). Either way the
    finisher leaves an R1.0 fillet there, and at the two east mid-span bosses that fillet
    reached a max-material SC2 / SC4 by 0.113 / 0.130 mm (SolidCraft 0.134) while every gate
    measured the sharp corner.

    A dogbone is the end mill parked so it reaches the corner: a TOOL_R circle through it,
    clear of the lip and the recess wall (it may cut only the boss), and of all such circles
    the one whose centre lies farthest from the boss axis -- so it takes the least metal near
    the thread. Where the line from the axis out through the corner is clear, that is the
    centre; the textbook position on the corner's bisector was the first cut of this, and at
    SC4's mid-span boss it reached 1.269 mm from the axis, inside THREAD_KEEP. The flats stay
    where they were. A corner the tool already reaches gets nothing. The shell CAD cuts the
    centres as true cylinders (a polygon would hand the CAM a faceted bore); everything 2D
    reads boss_fouls(), which carries them as discs."""
    c = Point(mx, my)
    kps = [_boss_keepout(r, p) for r, p in _boss_foul_parts(mx, my)]
    if not kps:
        return kps, []
    reach = BOSS_R + 2 * TOOL_R
    win = c.buffer(reach + 2 * TOOL_R)
    fixed = (box(-5.0, -5.0, W + 5.0, H + 5.0).difference(recess_poly())
             .union(_lip_metal_cached())).intersection(win)
    isl = Point(mx, my).buffer(BOSS_R, resolution=64).difference(unary_union(kps))
    void = win.difference(fixed).difference(isl)
    can = void.buffer(-TOOL_R, join_style=1, resolution=48).buffer(TOOL_R, join_style=1, resolution=48)
    out = []
    for kp in kps:
        pts = list(kp.exterior.coords)[:-1]
        cen, n = [], len(pts)
        for i, v in enumerate(pts):
            if c.distance(Point(v)) >= reach:
                continue
            p, q = pts[i - 1], pts[(i + 1) % n]
            a = (p[0] - v[0], p[1] - v[1]); b = (q[0] - v[0], q[1] - v[1])
            la, lb = math.hypot(*a), math.hypot(*b)
            if la < 1e-9 or lb < 1e-9:
                continue
            bx, by = a[0] / la + b[0] / lb, a[1] / la + b[1] / lb
            if math.hypot(bx, by) < 1e-9:            # straight through: not a corner
                continue
            # only a CONVEX corner of the keep-out is an inside corner of the metal
            if not kp.buffer(1e-6).contains(Point(v[0] + 1e-4 * bx, v[1] + 1e-4 * by)):
                continue
            if can.buffer(1e-4).contains(Point(v)):  # the finisher already gets there
                continue
            best = None
            for k in range(720):
                t = math.radians(k * 0.5)
                cc = (v[0] + TOOL_R * math.cos(t), v[1] + TOOL_R * math.sin(t))
                if Point(cc).buffer(TOOL_R, resolution=48).intersection(fixed).area > 1e-9:
                    continue
                d = c.distance(Point(cc))
                if best is None or d > best[0]:
                    best = (d, cc)
            if best is None:
                raise RuntimeError(f"boss at ({mx}, {my}): no Ø{2 * TOOL_R:g} tool position "
                                   f"reaches keep-out corner ({v[0]:.3f}, {v[1]:.3f}) without "
                                   f"cutting the lip or the recess wall")
            cen.append((round(best[1][0], 6), round(best[1][1], 6)))
        out.append(cen)
    return kps, out


def _lip_metal_cached(_c={}):
    if "m" not in _c:
        _c["m"] = lip_metal_poly()
    return _c["m"]


def _coil_cached(_c={}):
    if "t" not in _c:
        _c["t"] = _coil_tracks()
    return _c["t"]


def boss_coil_cuts(mx, my):
    """([(cx, cy, r)], [slab]) -- what COIL_CLR takes out of the boss at (mx, my): the coil's
    copper grown by the clearance, as the pieces a cutter makes it from. Both lists are empty
    for a boss the coil is nowhere near, which today is six of the eight.

    A track grown by a distance is a round-ended slot: a disc of r = COIL_CLR + half the
    track's width about each end, and the straight band between them. They are handed over
    separately because the shell CAD cuts the discs as true cylinders and the bands as
    planes (the rule boss_cuts() already keeps: nothing faceted for a CAM seat to choke on);
    everything 2D reads boss_coil_keepout(), their union.

    NO DOGBONES, and the reason is geometry rather than luck. The union of a track's discs
    and bands has no outward-pointing corner -- every band end is buried in a disc of its own
    half-width -- so the metal it leaves has no inside corner, only arcs of radius r hollowed
    into the boss. A TOOL_R finisher cuts those exactly so long as r >= TOOL_R, and that is
    checked below rather than assumed: with COIL_CLR at 1.00 the smallest r on this board is
    1.076."""
    c = Point(mx, my)
    disc = c.buffer(BOSS_R, resolution=64)
    win = box(mx - BOSS_R - 1.0, my - BOSS_R - 1.0, mx + BOSS_R + 1.0, my + BOSS_R + 1.0)
    discs, slabs = {}, []
    for a, b, w in _coil_cached():
        r = round(w / 2.0 + COIL_CLR, 6)
        for p in {a, b}:
            if c.distance(Point(p)) < BOSS_R + r - 1e-9:
                discs[p] = max(r, discs.get(p, 0.0))
        if a != b:
            band = LineString([a, b]).buffer(r, cap_style=2)        # flat ends: the band alone
            if band.intersection(disc).area > 1e-9:
                slabs.append(band.intersection(win))
    small = [(p, r) for p, r in discs.items() if r < TOOL_R - 1e-9]
    if small:
        (px, py), r = small[0]
        raise RuntimeError(
            f"boss at ({mx}, {my}): the coil keep-out about ({px}, {py}) is R{r:.3f}, a hollow "
            f"the Ø{2 * TOOL_R:g} finisher cannot cut -- COIL_CLR {COIL_CLR} is too small for "
            f"this rule to be machined as modelled")
    return [(px, py, r) for (px, py), r in sorted(discs.items())], slabs


def boss_coil_keepout(mx, my):
    """The coil keep-out at the boss at (mx, my) as one polygon, or None where the coil is out
    of reach: boss_coil_cuts() united, for boss_fouls(), the drawing and every 2D check."""
    discs, slabs = boss_coil_cuts(mx, my)
    if not discs and not slabs:
        return None
    return unary_union([Point(x, y).buffer(r, resolution=64) for x, y, r in discs] + slabs)


def boss_coil_gap(mx, my):
    """How far the finished boss at (mx, my) stands from coil copper, or None where the coil
    took nothing out of it. MEASURED island-to-copper, for the sheet's callout -- the same
    reason boss_cutbacks() measures instead of printing BOSS_CLR."""
    if boss_coil_keepout(mx, my) is None:
        return None
    cu = unary_union([Point(a).buffer(w / 2.0, resolution=64) if a == b
                      else LineString([a, b]).buffer(w / 2.0, resolution=64)
                      for a, b, w in _coil_cached()])
    return boss_island(mx, my).distance(cu)


def _boss_keepout(ref, poly):
    """What one fouling part takes out of a boss: BOSS_CLR all round, or -- for a part with a
    directional bay (the supercaps) -- that bay's own per-edge clearance where it is larger."""
    if ref in CAP_DATUM:
        return part_keepout(ref, poly, sides={s: max(BOSS_CLR, v) for s, v in clr_sides(ref).items()})
    return poly.buffer(BOSS_CLR, join_style=2)


def _boss_foul_parts(mx, my):
    """[(refdes, outline)] -- the parts within BOSS_R of the boss axis at (mx, my). The one
    statement of what "fouls a boss" means; boss_fouls() and boss_foul_refs() are two views
    of it, so a sheet that NAMES the parts cannot disagree with the solid that is cut."""
    c = Point(mx, my)
    return [(r, p) for r, p, _h, _s in _cached_parts() if p.distance(c) < BOSS_R]


def boss_foul_refs(mx, my):
    """The refdes of the parts boss_fouls(mx, my) cuts the boss back for. For anything that
    has to say WHICH part in words -- the shell drawing's boss-flat callout -- so the word
    is read off the board with the numbers beside it and never typed."""
    return [r for r, _p in _boss_foul_parts(mx, my)]


def boss_cutbacks(mx, my):
    """[(refdes, gap)] -- how far the boss at (mx, my) actually stands off each part it was cut
    back for, MEASURED from the part's nominal outline to the finished island. For the shell
    drawing's callout, which printed BOSS_CLR as "the" cut-back and became false the day the
    supercaps took their own bay clearance: a number read off the geometry cannot go stale
    against the rule that made it."""
    isl = boss_island(mx, my)
    return [(r, p.distance(isl)) for r, p in _boss_foul_parts(mx, my)]


def boss_island(mx, my):
    """A boss disc scalloped clear of anything that fouls it."""
    disc = Point(mx, my).buffer(BOSS_R, resolution=64)
    foul = boss_fouls(mx, my)
    if not foul:
        return disc
    scal = disc.difference(unary_union(foul))
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
    EF, CAVR = EDGE_FIT, BOARD_R + EDGE_FIT          # board + edge_fit, as the generator uses
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


# ---- THE FILE FRAME (2026-11-13) ----------------------------------------------------------
# Every enclosure solid is MODELLED in board coordinates -- X right, Y DOWN, Z toward the card's
# front -- because that is what the .kicad_pcb stores and what every rule above is written in.
# That triad is LEFT-handed (x cross y = -z). STEP and STL are right-handed by definition, so
# a solid written out as modelled is the MIRROR IMAGE of the part, and until this date every
# STEP and STL in enclosure/ was one. Measured on the committed files against KiCad's own
# (right-handed) STEP export of the populated board, first on SolidCraft and then reproduced
# here to the digit: the max brace collided with the board's parts in both rigid placements
# the mount holes allow (53.1 mm3 over 34 parts, 493.9 mm3 over 29) and its mirror image
# fitted (0.05 mm3, one part); the medallion read backwards. It hid because the hole pattern
# is symmetric about both axes, assembly_render.py flips its finished pictures, and every
# gate loaded the solids in the frame the generators wrote them in.
#
# So a solid is reflected ONCE, on its way out, and nowhere else:
#
#     model (x, y, z)   ->   file (x, -y, z)
#
# The shell and the braces are modelled centred on the card (wx = bx - W/2, wy = by - H/2),
# so their files hold the board point (bx, by) at
#
#     (bx - W/2,  H/2 - by)          x right, y UP, z toward the card's front
#
# which is KiCad's own STEP-export convention (its board STEP has the card at x 0..W,
# y -H..0): an enclosure file and KiCad's export differ by a TRANSLATION and nothing else,
# and scripts/handedness_drc.py holds them to exactly that. The pogo plate is modelled
# un-centred, in bare board coordinates, and lands at (bx, -by).
#
# THE MODEL DOES NOT CHANGE. Every rule, pocket and polygon stays in board coordinates, the
# medallion keeps its X-mirror (right for a right-handed part -- it is why the old STEP read
# backwards), and both dimensioned drawings were true views all along.
#
# export_solid() is the one way a solid leaves this repo; file_xy() / board_xy() /
# board_geom() are the one statement of the mapping for anything that READS an emitted solid
# (interference_drc, assembly_drc, assembly_render). A reader that types its own "- W/2,
# - H/2" is the MOUNTS failure again: flip one side and not the other and every gate that
# shares the stale copy still passes.

def shop_frame(solid):
    """`solid` (a cadquery Shape or Workplane, in the MODEL frame) reflected through the XZ
    plane: the frame a file is written in. See THE FILE FRAME above."""
    return solid.mirror("XZ")


def export_solid(solid, stem, stl_tolerance, stl_angular=0.2):
    """Write `solid` as <stem>.step and <stem>.stl IN THE FILE FRAME, and return what was
    written. The one way a solid leaves this repo: reflected exactly once, then through
    export_step_stable (BRepCheck, the manifold gate, the timestamp-stable write) and the STL
    exporter. A generator that calls an exporter directly writes the mirror image."""
    import cadquery as _cq
    shop = shop_frame(solid)
    export_step_stable(shop, stem + ".step")
    _cq.exporters.export(shop, stem + ".stl", tolerance=stl_tolerance, angularTolerance=stl_angular)
    return shop


def file_xy(bx, by):
    """Board (x, y) -> where an emitted shell or brace has that point, in file (x, y)."""
    return bx - W / 2.0, H / 2.0 - by


def board_xy(fx, fy):
    """File (x, y) of an emitted shell or brace -> board (x, y). The inverse of file_xy()."""
    return fx + W / 2.0, H / 2.0 - fy


def board_geom(geom):
    """A shapely geometry in an emitted shell's or brace's file (x, y) -> board coordinates."""
    from shapely.affinity import affine_transform
    return affine_transform(geom, [1.0, 0.0, 0.0, -1.0, W / 2.0, H / 2.0])


def crowded_edges(shape):
    """[(n_faces, (x, y, z), (x, y, z))] -- every edge of an OCC shape that more than two
    faces use, with its end points. A closed solid's edges belong to exactly two faces each;
    one that belongs to four is the solid touching itself along a line."""
    from OCP.BRep import BRep_Tool
    from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE
    from OCP.TopExp import TopExp
    from OCP.TopoDS import TopoDS
    from OCP.TopTools import TopTools_IndexedDataMapOfShapeListOfShape
    uses = TopTools_IndexedDataMapOfShapeListOfShape()
    TopExp.MapShapesAndAncestors_s(shape, TopAbs_EDGE, TopAbs_FACE, uses)
    out = []
    for i in range(1, uses.Extent() + 1):
        n = uses.FindFromIndex(i).Extent()
        if n > 2:
            e = TopoDS.Edge_s(uses.FindKey(i))
            a = BRep_Tool.Pnt_s(TopExp.FirstVertex_s(e))
            b = BRep_Tool.Pnt_s(TopExp.LastVertex_s(e))
            out.append((n, (a.X(), a.Y(), a.Z()), (b.X(), b.Y(), b.Z())))
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
        # MANIFOLD GATE (2026-11-12). BRepCheck is necessary and was not sufficient: it
        # passed the max shell for three months while that solid carried 13 edges each
        # shared by FOUR faces -- titanium touching itself along a line, courtesy of the
        # medallion (medallion._partition has the story). OCC calls that a valid shape.
        # Another CAD kernel would not import the STEP at all, and a STEP the next seat
        # cannot open is not a deliverable, whatever this one thinks of it. So the one
        # choke point every exported solid passes through also asks the cheap question
        # directly. Measured before it was wired in: 13 on the committed max shell, 4 on
        # the first draft of the fix, 0 on the other five shipped solids and on the pogo
        # plate -- red where it should be, silent where it should be, 0.2 s on the largest.
        _crowd = crowded_edges(_shape)
        if _crowd:
            _n, _a, _b = _crowd[0]
            raise SystemExit(
                f"export_step_stable: the solid bound for {path} has {len(_crowd)} edge(s) "
                f"shared by more than two faces (first: {_n} faces along "
                f"({_a[0]:.3f}, {_a[1]:.3f}, {_a[2]:.3f}) .. ({_b[0]:.3f}, {_b[1]:.3f}, "
                f"{_b[2]:.3f}), solid coordinates). OCC accepts a solid that touches itself "
                f"like this; other kernels refuse to open the file -- refusing to export")
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
    cav = brace_cavity()
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
