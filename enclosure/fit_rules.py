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

  BOSS    The r2.60 disc cut back to ONE flat for the supercap beside it (boss_flat_d), and
          straight across beside the NFC coil -- never inside THREAD_KEEP. What that costs in
          thread: a boss keeps about 82 % of its r0.80..r2.60 annulus, and the two coil-cut
          ones about 76 % (enclosure/README.md owns the figures; boss_island() is what they
          are measured on). This line said "the worst case keeps 92.4%" from the day the
          bosses were first scalloped until 2026-11-16, through four changes to them.
"""
from __future__ import annotations

import math
import os
import sys

from shapely.geometry import box, LineString, Point, Polygon
from shapely.ops import unary_union
from shapely.affinity import scale as _mirror

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
                           # purpose (the ferrite channel's own walls, the TP2/TP3 neck). Set
                           # 2026-11-13 as the wall a Formlabs Form 3/4-class machine holds; the
                           # printer is Protolabs since 2026-11-15, which states a 0.152 mm
                           # minimum wall for ABS-Like White at high resolution, so 0.25 is
                           # inside what it states with 0.10 to spare and is left where it was
                           # (enclosure/brace/README.md). An exception from 0.60 is not an exception from this --
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
WALL_FIT = 0.07            # brace to shell, a side, on EVERY face the brace reaches: walls,
                           # bosses, tabs. 0.05 until 2026-11-15, when DRH chose the printer
                           # and the fit together ("6A Protolabs, 6B 0.07 everywhere"). A
                           # dimension between two FACING faces of the shell seats if the
                           # print's worst oversize is no more than the fit at both its
                           # ends, 2 x WALL_FIT = 0.14. Against print_xy_tol() below, as
                           # measured on the footprint:
                           #    88.66  nose to nose, the prongs' ends on the recess walls
                           #           +/-0.139   inside by 0.001
                           #    84.76  fork seat to fork seat (the tabs' tips)
                           #           +/-0.135   inside by 0.005  (0.035 OVER at 0.05)
                           #    47.16  wall to wall                +/-0.097
                           #    28.67  the block between two mid-span bosses, at most
                           #           +/-0.079
                           #     3.65  the slot across a tab (an inside dimension: it is
                           #           the worst UNDERSIZE that binds)   +/-0.054
                           # The fork seats and the boss nests are curves and cannot be
                           # sanded; the noses and the long walls are flat and can. The sum
                           # counts the print alone: what the machined cavity is off by
                           # adds to it. check_consistency [8] 4g holds the fit to the
                           # stated tolerance; TODO.md has the services compared.
PRINT_XY_TOL = (0.05, 0.001)   # the printer's stated accuracy in the build plane, as (mm, mm
                           # per mm of length): Protolabs, stereolithography, "X/Y axis:
                           # +/-0.002 in. (+/-0.05mm) for the first inch (25.4mm), plus 0.1%
                           # of nominal length" (their SLA page, read 2026-11-15; one row,
                           # not split by resolution). Taken as 0.05 + 0.1 % of the WHOLE
                           # length, the wider of the two ways that sentence reads. In Z
                           # they state +/-0.127 the same way; no fit here is held to it.
SHIM_INSET = 0.05          # ...and what a plate that is NOT a brace stands inside the same
                           # outline (brace_cavity(nest=False): scripts/reflow_shim.py). It
                           # was WALL_FIT while that was 0.05, and it is a fit to nothing --
                           # the plate lies on the bare board at reflow, with no shell round
                           # it -- so it does not follow the brace's fit to a printer the
                           # plate is not made on. The shim's outline is unchanged.


def print_xy_tol(length):
    """+/- what the printer states it holds on a dimension of `length` mm in the build plane."""
    return PRINT_XY_TOL[0] + PRINT_XY_TOL[1] * length


# ---- shell ----------------------------------------------------------------------------
BOSS_R = 2.60
PILOT_R = 0.80
SPOTFACE_D = 3.0           # the back spotface at each mount hole, where it is cut into the FLOOR
                           # (max, lite): the M2's tip lands flush in it, under the proud annulus.
SPOTFACE_D_OPEN = 2.4      # ...and where it is cut into the BOSS, on an open frame (air), whose
                           # boss foot is the resting face. 3.0 there until 2026-11-16 (DRH:
                           # "6B Ø2.4 air only"). Every boss carries a flat boss_flat_d() =
                           # 1.475 from its axis since the contouring pass of 2026-11-14, and a
                           # r 1.500 spotface reached 0.025 PAST it: a notch 0.545 wide through
                           # the foot of all eight flats, with a knife edge either side, on a
                           # frame whose sheet said nothing of it. Found by the second outside
                           # review; nothing here held a spotface to its boss. At 2.4 it leaves
                           # 0.275 of wall at the flat and 0.20 round the M2's tip.
SPOTFACE_WALL = 0.25       # least metal between a spotface cut into a boss and that boss's flat
SPOTFACE_COVER = 0.10      # least floor left OVER a spotface cut into a floor: the cut must end
                           # inside the floor, not come up into the cavity. Under the boss it is
                           # backed by the boss; it matters only for the 0.025 mm by which the
                           # cut peeks past the boss's flat, where 0.60 (max) and 0.18 (lite) of
                           # floor is all there is over it (spotface_fit)
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
    rw = ring_widths()
    return unary_union([box(0.0, 0.0, rw["W"], H), box(W - rw["E"], 0.0, W, H),
                        box(0.0, 0.0, W, rw["S"]), box(0.0, H - rw["N"], W, H)])


def ring_widths():
    """RING as the shell builds it: held to the lip's own width on an edge whose lip is cut to
    ONE width (LIP_ONE_WIDTH, 2026-11-15). The ring is a guaranteed MINIMUM seat, and on those
    edges the lip is by rule no wider than its narrowest need -- a ring wider than that would
    put back, everywhere but beside the part that set the width, exactly the steps the rule
    was written to remove (it did, on the first run: the west wall came out 2.50 with a
    relief at R16 and C24, as before). The shell CAD reads this, never RING itself."""
    out = dict(RING)
    for e in LIP_ONE_WIDTH:
        out[e] = min(out[e], lip_bands(e)[0][2])
    return out


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
    if ps is None:
        # ...and the ring gives way altogether at the two short-edge tabs (lip_tabs): there the
        # lip the void leaves is the whole tab, and the ring less a supercap's relief used to
        # add a strip to one side of it that the other side did not have
        out += [win for _e, _lo, _hi, _w, win in lip_tabs()]
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
RELIEF_R = BOSS_R + CLR    # 2.85 -- the circle a plate that is NOT nested keeps clear round a
                           # boss axis (brace_footprint(nest=False): the reflow shim, which lies
                           # on the bare board). The BRACE has not used it since 2026-11-15: it
                           # nests against the bosses themselves, at WALL_FIT. Was a flat 3.00,
                           # which pinched every rail to a 0.750 mm waist at all eight bosses.

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
    """The scalar rectangle a brace is cut inside (and then held to the void, brace_cavity()).

    ITS WEST EDGE FOLLOWS THE WEST LIP (2026-11-15). _CAV's 2.50 was the west lip's width
    while that lip was 2.50 wide wherever no part narrowed it; the lip is one width the whole
    edge now (LIP_ONE_WIDTH), 2.25, and a brace still cut at 2.50 would stand 0.30 off a wall
    it is meant to bear on with WALL_FIT -- free to slide a quarter of a millimetre west,
    which is all the clearance its pockets leave round a part. So where an edge's lip is one
    width, that width is the rectangle's edge if it is the smaller."""
    x0, y0, x1, y1 = _CAV
    if "W" in LIP_ONE_WIDTH:
        x0 = min(x0, lip_bands("W")[0][2])
    if "E" in LIP_ONE_WIDTH:
        x1 = max(x1, W - lip_bands("E")[0][2])
    ir = _CAV_IR
    c = box(x0 + ir, y0, x1 - ir, y1).union(box(x0, y0 + ir, x1, y1 - ir))
    for cx, cy in [(x0+ir, y0+ir), (x1-ir, y0+ir), (x0+ir, y1-ir), (x1-ir, y1-ir)]:
        c = c.union(Point(cx, cy).buffer(ir, resolution=64))
    return c


def brace_cavity(nest=True):
    """The outline a brace may fill: the shell's void AS MILLED, inside the recess wall, shrunk
    by the wall fit.

    NESTED SINCE 2026-11-15 (DRH: "I want the brace to get a tighter fit, matching the inverse
    at the ferrite side such that the plastic nests along the curve of the bosses", and "on the
    northern and southern tabs, I want the brace extended such that it hugs either side of the
    tabs along that curve"). Until then the outline was held twice more: inside cavity_rect(),
    whose short edges are the tab TIPS (y 2.00 / 86.90), so the long arm stopped square against
    each tab and never ran beside it; and outside a circle of RELIEF_R round every boss axis,
    which is a full round boss's shape plus CLR -- and the east mid-span bosses are cut straight
    across (boss_coil_cuts), so the brace stood 0.53 mm and more off a face it could lie along.
    Both were approximations of the shell, typed before the shell could be asked. It can be:
    cavity_as_milled() is every boss, blend, flat, round, tab, tab root and lip the cutter
    leaves, so the void less ONE fit is the inverse of all of them.

    ONE FIT, WALL_FIT, ON EVERY FACE. "Let's try to make a somewhat exact fit, since these are
    complex curves that would be hard to sand out of the plastic": the curves are cut at the
    fit the flat walls have, not left fat to be fitted by hand. What that asks of the print is
    in enclosure/brace/README.md -- a flat wall that comes out tight can be sanded, the inside
    of a fork round a tab cannot.

    INSIDE THE RECESS. cavity_as_milled() is board area less metal, and the recess the board
    presses into is EDGE_FIT smaller than the board all round: beside a supercap, where there
    is no lip, the void's own edge is the board's, 0.05 mm outside the wall that is really
    there. Nothing reached those strips while the rectangle held the outline; a brace that
    runs beside a tab does.

    nest=False is the outline as it was: the rectangle, and (in brace_footprint) the boss
    circles. scripts/reflow_shim.py asks for it -- that plate lies on the bare board at reflow,
    with no shell round it, and has no tab to hug or boss to nest against. Nor a fit to hold:
    it stands SHIM_INSET inside the rectangle, where the brace stands WALL_FIT inside the void.

    WHY IT IS THE VOID AND NOT THE RECTANGLE ALONE (2026-11-12). cavity_rect() is the scalar
    rectangle _CAV -- a 1.00 mm east lip -- and the brace used to be cut from it alone. The
    shell is cut from cavity_void_poly(), whose east lip the coil clamp in _lip_reach() sets
    at W - COIL_EAST = 1.25 mm. Same module, two answers: the committed braces came out 0.20
    mm WIDER than the committed cavities along the whole middle band (east face x49.750
    against a wall at x49.550; 9.02 mm3 of overlap on max, 5.94 on lite, measured on the
    STEPs), and check [8] measured the brace against cavity_rect() again, so it agreed.

    AND THE VOID IS THE ONE THE CUTTER LEAVES (2026-11-13). The shell is modelled with its
    boss-to-wall junctions sharp, and the sheet tells the shop to finish them with a O2.0
    tool -- which leaves R1.0 of metal in each. The brace was cut to the sharp model, so at
    the four bosses whose discs meet the cavity wall beside the brace's band it ran 0.225
    mm (east) and 0.055 mm (west) into those fillets: sectioned on the committed STLs, and
    invisible to assembly_drc [B], which measured the sharp shell too. cavity_as_milled()
    is the void with the finisher's radius applied."""
    if nest:
        region = cavity_as_milled().intersection(recess_poly())
        return region.buffer(-WALL_FIT, join_style=1, resolution=64)
    region = cavity_rect().intersection(cavity_as_milled())
    return region.buffer(-SHIM_INSET, join_style=1, resolution=64)


def cavity_as_milled(tool_r=TOOL_R):
    """The cavity void at the board-rest plane AS A RADIUS-tool_r FINISHER LEAVES IT: board
    area less the modelled metal (shell_metal_poly(): the lip, the boss islands, and since
    2026-11-14 the blends and webs that join each boss to the wall), opened by the tool.
    Every inside corner of the metal that the model leaves sharp comes back as a tool_r
    fillet; nothing else moves.

    The brace is cut to this, and scripts/assembly_drc.py [H] applies the same opening to
    the SECTIONED shell, so the rule and the part are measured by two different readers."""
    void = box(0.0, 0.0, W, H).difference(shell_metal_poly())
    return (void.buffer(-tool_r, join_style=1, resolution=48)
                .buffer(tool_r, join_style=1, resolution=48))


def brace_footprint(span=None, keepout=None, nest=True):
    """[polygon] -- the pieces the brace is actually made of, largest first.

    `span=None` is the max variant (module SPAN_LIMIT); per-variant callers pass
    variant_span(name). DROPPED_AREA/DROPPED_COUNT describe the LAST call -- a
    per-variant caller should read them immediately, before any other call.

    `nest` (brace_cavity): True, the brace -- it follows the shell's bosses and tabs at
    WALL_FIT, and the boss is kept off by being metal, not by a circle. False, a plate with no
    shell round it -- the rectangle, and RELIEF_R round every boss axis, as both were until
    2026-11-15."""
    cav = brace_cavity(nest)
    _ko = keepout or part_keepout
    keep = unary_union([_ko(_r, p) for _r, p in blockers(span=span)])
    fp = cav.difference(keep)
    if not nest:
        fp = fp.difference(unary_union([Point(b).buffer(RELIEF_R, resolution=64) for b in MOUNTS]))
    t = SLA_WALL / 2.0
    fp = (fp.buffer(-t, join_style=1, resolution=32)
            .buffer(t, join_style=1, resolution=32)
            .intersection(cav))
    pieces = sorted((list(fp.geoms) if fp.geom_type == "MultiPolygon" else [fp]),
                    key=lambda g: -g.area)
    # 0.01 until the outline nested. A chord across an arc that hugs a CONVEX corner of the
    # shell (a tab's tip, a boss's round) stands nearer the metal than the arc does, by up to
    # the tolerance: at 0.01 the nested outline came 0.040 mm from titanium where WALL_FIT said
    # 0.050. At 0.005 it was 0.045 at the least and 0.055 at the most, on 220 vertices instead
    # of 160 -- and still coarse enough to lose the 0.004 mm nicks the opening leaves at the
    # corners of a through-cut, which a finer pass kept as edges (lite, six of them). (With
    # the fit at 0.07 the same tolerance gives 0.065 at the least.)
    _tol = 0.005 if nest else 0.01
    pieces = [g.simplify(_tol, preserve_topology=True) for g in pieces if g.area >= MIN_PIECE]

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
            coverage_floor=0.32,   # ledgered min. UNCHANGED 2026-11-15 and re-measured: 32.82 %.
                                   # (32.83 % with the fit at 0.07, later that day: brace and
                                   # denominator both stand 0.02 further in, 1331.60 of 4056.5.)
                                   # Both terms moved when the brace nested (brace_cavity):
                                   # the footprint 1319.30 -> 1333.19 mm2, and the floor it is
                                   # a share of 3912.9 -> 4062.1 mm2, because the void beside
                                   # the supercaps out to the recess wall counts now that a
                                   # brace may stand in it. Against the OLD denominator this
                                   # brace would read 34.07 %. Closer to the floor than it has
                                   # been (0.82 of a point), by the denominator alone.
                                   # UNCHANGED 2026-11-12 and re-measured: 33.01 %,
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
            coverage_floor=0.25,   # ledgered min. UNCHANGED 2026-11-15: 27.17 % (footprint
                                   # 1089.83 -> 1103.78 mm2 of a floor 3912.9 -> 4062.1, as
                                   # max; 28.21 % against the old denominator).
                                   # UNCHANGED 2026-11-12: 27.28 % -> 27.25 % of the
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
        d["spotface_d"] = SPOTFACE_D_OPEN if d["open_back"] else SPOTFACE_D
    return v


VARIANTS = _mk_variants()


def spotface_fit(vname):
    """(where, margin) -- what the back spotface at each mount is cut into on this variant,
    and how much metal it leaves there.

    The spotface is a flat-bottomed cut of the variant's spotface_d from the back, to the plane
    the screw's tip reaches (stack - screw_len). On a floored shell that plane is inside the
    floor, and the margin is the floor left over it: the cut must not come up into the cavity,
    where the bosses' flats are. On an open frame there is no floor -- the cut is in the boss
    itself -- and the margin is the wall left between it and the boss's flat. The first must
    be SPOTFACE_COVER or more and the second SPOTFACE_WALL (spotface_need(); check_consistency
    [8]; scripts/assembly_drc.py [D] measures it on the emitted solid). Until 2026-11-16
    nothing asked."""
    v = VARIANTS[vname]
    tip = round(v["stack"] - v["screw_len"], 6)
    if v["open_back"]:
        return "boss", boss_flat_d() - v["spotface_d"] / 2.0
    return "floor", v["floor"] - tip


def spotface_need(where):
    """The least margin spotface_fit() may report for a cut in the "boss" or in the "floor"."""
    return SPOTFACE_WALL if where == "boss" else SPOTFACE_COVER


def variant_span(name):
    s = VARIANTS[name]["span"]
    if s is None:
        raise ValueError(f"variant '{name}' has no brace, so no span limit")
    return s


COIL_REF = "NFC COIL"      # the one lip limiter that is not a part: the coil clamp on the east edge


# ---- THE TWO SHORT EDGES ARE CUT ALIKE (2026-11-15, DRH: "yes" to making the two tabs the
# same width) ----------------------------------------------------------------------------
# The lip between the two supercaps on each short edge stands as a tab, and the two tabs came
# out 3.5 mm (south) and 4.0 mm (north) wide, because SC2 and SC4 stand 0.152 mm apart in x and
# the bands are cut on 0.5 mm stations. After the west wall went straight that half millimetre
# was the ONLY thing that made the inside of a shell differ top for bottom -- and so the only
# thing that gave the lite and air shells a hand at all. A short edge's lip at a station is now
# the lesser of what that edge and its twin allow there, so the two edges are one table: the
# north tab is 3.5 mm too (0.5 x 2.0 less the root fillet: about 1 mm2 of a 340 mm2 seat).
# Only ever less metal, the contouring pass's rule.
#
# WHAT FOLLOWS FROM IT, each held somewhere:
#   * the floor fillets' evening rule (floor_runs) gives nothing up: both runs east of the tabs
#     stop FLOOR_STOP short again;
#   * the LITE and AIR shells are their own mirror images top for bottom -- they have no hand,
#     and cannot be cut in the wrong one. scripts/handedness_drc.py [S] and [E] ASSERT that
#     now instead of looking for a tell that is no longer there (shell_has_hand, below);
#   * the MAX shell's hand is its rear art and nothing else, so something has to read the rear
#     art: scripts/assembly_drc.py [L].
LIP_TWIN = {"S": "N", "N": "S"}


def _lip_limits(edge, lo, hi, ps=None):
    """_lip_limits_own() for `edge`, EVENED with its twin edge where it has one (LIP_TWIN):
    the lesser width of the two, named by whichever edge's parts set it (both, if they agree)."""
    w, who = _lip_limits_own(edge, lo, hi, ps)
    twin = LIP_TWIN.get(edge)
    if twin is None:
        return w, who
    wt, whot = _lip_limits_own(twin, lo, hi, ps)
    if wt < w - 1e-9:
        return wt, list(whot)
    if abs(wt - w) <= 1e-9:
        return w, who + [n for n in whot if n not in who]
    return w, who


def _lip_limits_own(edge, lo, hi, ps=None):
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


# ---- ONE WIDTH ALONG A LONG EDGE (2026-11-15, DRH, circling the west wall on a plan of the
# cavity: "mill away material so they are smooth contiguous surfaces for the milling to be done
# simpler") ---------------------------------------------------------------------------------
# The west lip was cut per 0.5 mm station like every other, so it stepped in twice -- 2.50 to
# 2.32 beside R16 and 2.25 beside C24 -- and out again, with an R1.0 blend at each step: four
# little faces in a wall 84 mm long, for 0.25 mm of seat over 6 mm of it. A long edge's lip is
# now ONE width for its whole length: the narrowest any part along it asks for. The east lip
# already was (the coil clamps all of it). Only ever less metal.
#
# The whole edge, not just the stretch between the two mid-span bosses: a wall that changed
# width behind a boss would give that boss a different blend on each side, and the bosses are
# their own mirror images by rule (EVEN AND SYMMETRIC, below).
LIP_ONE_WIDTH = ("W", "E")


def lip_bands(edge, step=0.5):
    """[(lo, hi, width)] along `edge`, merged. Computed, so it cannot go stale."""
    span = H if edge in ("W", "E") else W
    if edge in LIP_ONE_WIDTH:
        return [(0.0, span, _lip_reach(edge, 0.0, span))]
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
    if edge in LIP_ONE_WIDTH:
        # one band, sized over the whole edge in one call -- so the limiter named is the part
        # that sets THAT width, not every part that would have narrowed its own station
        span = H if edge in ("W", "E") else W
        w, who = _lip_limits(edge, 0.0, span)
        return [(0.0, span, w, who)]
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


def cavity_void_poly(tool_r=TOOL_R, simplify=True, _trims=True):
    """Cavity void in board coords: the board rect inset by the per-band lip, opened by the
    finisher radius, plus local reliefs for what the tool then cannot reach, plus what makes
    the two short-edge tabs symmetric and round-cornered (tab_trims), less the true fillet at
    each tab root (tab_roots). `_trims` False is the void with the tabs left SQUARE at root
    and tip -- what the shell cuts first (void_as_cut), and what both are laid out on."""
    opened = _void_opened(tool_r)

    # A dia 2.0 finisher cannot reach the concave corners a band step leaves, so the opening
    # puts material back over a few parts near a step -- a fixed 0.088 mm2 worst case that
    # does NOT improve at any band clearance (swept 0.30..0.80, identical). Dilating a
    # keep-out by the tool radius makes it tool-reachable by construction.
    stuck = [p for _r, p in lip_relieved(tool_r, opened)]
    if stuck:
        opened = opened.union(unary_union([_lip_relief(p, tool_r) for p in stuck]))
    if _trims and tool_r == TOOL_R:
        # the two short-edge tabs as the part has them: tips rounded, and at each root the
        # true fillet on the wall that is really there in place of the one the opening left
        opened = (opened.union(unary_union(_tab_squares()[0] + tab_trims()))
                        .difference(unary_union(tab_root_metal())))
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
    if simplify:
        opened = opened.simplify(0.01, preserve_topology=True)
    if not _trims and tool_r == TOOL_R:
        opened = _tabs_squared(opened)
    return opened


def lip_poly(simplify=True, _trims=True):
    """The support ledge itself -- what a B-side part would be crushed by / shorted on."""
    return box(0.0, 0.0, W, H).difference(cavity_void_poly(simplify=simplify, _trims=_trims))


# ---- THE TWO SHORT-EDGE TABS, SYMMETRIC AND ROUND-CORNERED (2026-11-14, DRH) -----------------
# Between the two supercaps on each short edge the lip stands as a tab (lip_bands: the one
# band on S or N that reaches neither corner). Its two sides came from two different rules --
# one from a band step opened by the finisher, the other from the guaranteed ring less a
# supercap's relief, which left a strip 0.1 mm wide down one side of the south tab -- and its
# two tip corners were square. DRH asked for every boss and tab to be symmetric and for the
# hard corners to be R1.
#
#   * SYMMETRIC: the ring gives way at a tab (ring_reliefs), so the tab is what the void
#     leaves, and that is a band with the same finisher fillet at both roots. tab_rounds()
#     refuses a tab that does not mirror itself about its own centre line.
#   * ROUND-CORNERED: each tip corner is a round of CONTOUR_R, and a TRUE CYLINDER in the
#     shell, exactly as a boss's outside corners are (boss_rounds, below): the void is cut
#     with the tips square (void_as_cut) and a round tool takes each corner off. The first
#     build of this put the rounds into the void's own polygon instead, and that outline is
#     simplified to 0.01 for the kernel: the four rounds came out as three or four flats
#     each, a different three or four at each corner, on a pass whose point was symmetry.
#
# Only ever less metal. A tab is 2 * TOOL_R deep, so its root fillet ends where its tip round
# begins: the side of a tab is an ogee with no straight in it.
def lip_tabs():
    """[(edge, lo, hi, width, window)] -- each short-edge lip band that reaches neither
    corner, with the box of board the tab and its two root fillets stand in."""
    reach = LIP_CLR + 2.0 * TOOL_R + 0.5
    out = []
    for e in ("S", "N"):
        for lo, hi, w in lip_bands(e):
            if w > 0 and lo > 1e-9 and hi < W - 1e-9:
                y0, y1 = (0.0, w + 0.5) if e == "S" else (H - w - 0.5, H)
                out.append((e, lo, hi, w, box(lo - reach, y0, hi + reach, y1)))
    return out


def tab_rounds(_c={}):
    """[round] -- the tip corners of the short-edge tabs, two a tab, each a dict as
    boss_rounds() gives them (O, r, A, B, cover, cut) plus `edge`. Board coords.

    Laid out on the lip AS CUT (void_as_cut: the simplified polygon, tips square), for the
    reason the blends are: the cylinder has to cross the faces the cutter is actually given.
    It raises rather than return a round on a tab that is lopsided, too narrow for two
    rounds, or whose tip is not the square corner the layout assumes."""
    if "t" not in _c:
        R, d = CONTOUR_R, CONTOUR_R - BLEND_BITE
        metal = box(0.0, 0.0, W, H).difference(void_as_cut())
        out = []
        for edge, lo, hi, w, win in lip_tabs():
            at = f"the {edge} tab (x{lo:g}..{hi:g})"
            if hi - lo < 2.0 * R + 1e-9:
                raise RuntimeError(f"{at} is narrower than two tip rounds of R{R:g}: no flat "
                                   f"would be left to seat a board on")
            tab = metal.intersection(win)
            lop = tab.symmetric_difference(_mirror(tab, -1.0, 1.0, origin=((lo + hi) / 2.0, 0.0)))
            if lop.buffer(-0.011).area > 0:      # the outline is simplified to 0.01
                raise RuntimeError(f"{at} does not mirror itself about x{(lo + hi) / 2.0:g}: "
                                   f"{lop.area:.4f} mm2 differs, near "
                                   f"({lop.centroid.x:.2f}, {lop.centroid.y:.2f})")
            yt, sy = (w, 1.0) if edge == "S" else (H - w, -1.0)      # the tip, and which way it faces
            for xs, sx in ((lo, 1.0), (hi, -1.0)):
                O = (xs + sx * d, yt - sy * d)
                A, B = (xs, O[1]), (O[0], yt)
                cover = _round_cover(O, A, B, R, math.hypot(xs - O[0], yt - O[1]) + 0.05)
                cut = cover.difference(Point(O).buffer(R, resolution=256))
                took = cut.intersection(metal)
                # what a round of R takes off a square corner, as near as BLEND_BITE lets it
                want = (box(min(xs, xs + sx * R), min(yt, yt - sy * R), max(xs, xs + sx * R), max(yt, yt - sy * R))
                        .difference(Point(xs + sx * R, yt - sy * R).buffer(R, resolution=256)))
                odd = took.symmetric_difference(want).buffer(-_ROUND_TOL / 2.0)
                if not odd.is_empty:
                    raise RuntimeError(f"{at}: the round about ({O[0]:.3f}, {O[1]:.3f}) would take "
                                       f"{took.area:.4f} mm2 where a square corner gives up "
                                       f"{want.area:.4f}: the tip is not square there, near "
                                       f"({odd.centroid.x:.3f}, {odd.centroid.y:.3f})")
                # the cover's straight sides must run out through the void, or the tool that
                # is extruded from it cuts a step where one enters metal
                for F in (A, B):
                    ux, uy = (F[0] - O[0]) / d, (F[1] - O[1]) / d
                    ray = LineString([(O[0] + (R + 1e-4) * ux, O[1] + (R + 1e-4) * uy),
                                      (O[0] + (R + 0.6) * ux, O[1] + (R + 0.6) * uy)])
                    if ray.intersection(metal).length > 1e-9:
                        raise RuntimeError(f"{at}: the side of the round about ({O[0]:.3f}, "
                                           f"{O[1]:.3f}) through ({F[0]:.3f}, {F[1]:.3f}) runs "
                                           f"into metal")
                out.append({"O": (round(O[0], 9), round(O[1], 9)), "r": R, "A": A, "B": B,
                            "cover": cover, "cut": cut, "took": took, "area": took.area,
                            "edge": edge})
        _c["t"] = out
    return _c["t"]


def tab_trims():
    """[polygon] -- what tab_rounds() takes off the tab tips, for the 2D void (the brace, the
    gates and the sheet read the lip from cavity_void_poly(), and it has to have the rounds)."""
    return [rd["cut"] for rd in tab_rounds()]


# ---- ...AND THEIR ROOTS (2026-11-15, DRH: "see if there are any others ... that could be made
# to be simpler cuts"). Each tab met the short-edge wall through the fillet the finisher-radius
# opening leaves (_void_opened), and that fillet had two things wrong with it, both in the
# model and neither in the part. It was laid out from the BOARD edge, but the cavity's wall on
# a short edge is the RECESS wall, EDGE_FIT inside it -- so the curve met the wall it was
# supposed to be tangent to at a 19-degree kink, 0.31 mm short of its own foot. And it lived
# in the void's polygon, which is simplified for the kernel: three or four flats where a
# cutter leaves an arc. A Ø2.0 finisher running along that wall and up the tab leaves R1.00
# tangent to the wall, whatever the model says; now the model says that.
#
# Same construction as a boss blend (boss_blends), and for the same reasons: the void is cut
# with each root SQUARE (_tabs_squared), and a cover holding the corner, less a TRUE
# CYLINDER set BLEND_BITE past tangent to the wall and to the tab's side, is added after. A
# tab is 2 * TOOL_R deep from the BOARD edge, so from the wall it is EDGE_FIT short of that:
# the root's cylinder and the tip round's overlap by a hair, and the side of the tab between
# them is a flat 0.08 mm wide that both cross. Only the model moves; the part does not.
def _tab_squares():
    """([box], [box]) -- board that goes back into the void at each tab root (the fillet
    _void_opened() leaves there), and the tabs themselves as exact rectangles."""
    g = TOOL_R + 0.30
    add, keep = [], []
    for e, lo, hi, w, _win in lip_tabs():
        y0, y1 = (0.0, w) if e == "S" else (H - w, H)       # the whole side, root to tip
        add += [box(lo - g, y0, lo, y1), box(hi, y0, hi + g, y1)]
        keep.append(box(lo, 0.0, hi, w) if e == "S" else box(lo, H - w, hi, H))
    return add, keep


def _tabs_squared(v):
    """The void `v` with each short-edge tab an EXACT RECTANGLE: square at the roots, square
    at the tips, sides straight. Applied AFTER the kernel's simplify, on purpose -- that pass
    may move an outline 0.01, and on a tab it did: it kept a vertex 0.008 mm along the tip in
    place of the corner, so one side of the south tab leaned 0.23 degrees and the other did
    not, under four cylinders laid out as if both were square (found 2026-11-15, laying out
    the roots). Refuses to square a root that holds anything but the opening's own fillet."""
    add, keep = _tab_squares()
    if not add:
        return v
    r = TOOL_R
    for b in add:
        x0, y0, x1, y1 = b.bounds
        had = b.difference(v)                                          # the metal this box takes away
        xr = x1 if any(abs(x1 - k.bounds[0]) < 1e-9 for k in keep) else x0      # the tab's side
        yr = y0 if y0 < 1e-9 else y1                                             # the board edge
        zone = box(min(xr, xr + (r + 0.02) * (-1 if xr == x1 else 1)), min(yr, yr + (r + 0.02) * (1 if yr == y0 else -1)),
                   max(xr, xr + (r + 0.02) * (-1 if xr == x1 else 1)), max(yr, yr + (r + 0.02) * (1 if yr == y0 else -1)))
        # ...but for a sliver the simplify itself can leave along the tab's side (0.01 at most)
        stray = had.difference(zone).buffer(-0.011)
        if not stray.is_empty or had.area > (1.0 - math.pi / 4.0) * r * r + 0.03:
            raise RuntimeError(f"tab root near ({xr:g}, {yr:g}): squaring it would take "
                               f"{had.area:.4f} mm2 of lip, {had.difference(zone).area:.4f} of it "
                               f"outside the R{r:g} fillet the opening leaves -- something else "
                               f"stands there")
    out = v.union(unary_union(add)).difference(unary_union(keep))
    if out.geom_type != "Polygon":
        out = max((g for g in out.geoms if g.geom_type == "Polygon"), key=lambda g: g.area)
    # the boxes leave vertices where they cross the old outline, lying ON the new straight
    # sides: each would split a flat wall into two faces. Moves nothing.
    return out.simplify(1e-7, preserve_topology=True)


def tab_roots(_c={}):
    """[blend] -- the four tab roots, each a dict as boss_blends() gives them (O, r, F, T, J, t,
    n, cover) plus `edge`: a concave blend of TOOL_R between the short-edge wall AS CUT and the
    side of the tab. Board coords.

    Laid out on void_as_cut(), like every blend. It raises rather than return a root whose
    wall or tab side is not the straight face the layout assumes, whose new metal is not the
    fillet a square corner takes, or that comes within LIP_CLR of a part."""
    if "t" not in _c:
        r, d = TOOL_R, TOOL_R - BLEND_BITE
        v = void_as_cut()
        metal = box(-1.0, -1.0, W + 1.0, H + 1.0).difference(v)
        rx0, ry0, rx1, ry1 = recess_poly().bounds
        out = []
        for edge, lo, hi, w, _win in lip_tabs():
            yw, sy = (ry0, 1.0) if edge == "S" else (ry1, -1.0)       # the wall, and the way the cavity lies
            tip = w if edge == "S" else H - w
            if abs(tip - yw) < d + 0.25:
                raise RuntimeError(f"the {edge} tab stands {abs(tip - yw):.2f} mm off its wall: "
                                   f"no room for an R{r:g} root")
            for xs, sx in ((lo, -1.0), (hi, 1.0)):                    # sx: along the wall, away from the tab
                at = f"the {edge} tab's root at ({xs:g}, {yw:g})"
                J = (xs, yw)
                t, n = (sx, 0.0), (0.0, sy)
                F = (xs + d * sx, yw)
                O = (F[0], yw + d * sy)
                T = (xs, O[1])
                # the two faces it joins must be there, straight, as far as it reaches and beyond
                for a, b, what in ((J, (xs + (r + 0.25) * sx, yw), "the wall"),
                                   (J, (xs, yw + (r + 0.25) * sy), "the tab's side")):
                    run = LineString([a, b])
                    if run.difference(v.exterior.buffer(1e-6)).length > 1e-6:
                        raise RuntimeError(f"{at}: {what} is not a straight face of the void as "
                                           f"cut from ({a[0]:.3f}, {a[1]:.3f}) to ({b[0]:.3f}, {b[1]:.3f})")
                cover = Polygon([O, F,
                                 (F[0], F[1] - _BLEND_LIP * sy),
                                 (xs - _BLEND_LIP * sx, yw - _BLEND_LIP * sy),
                                 (xs - _BLEND_LIP * sx, T[1])])
                b = {"O": (round(O[0], 9), round(O[1], 9)), "r": r, "F": F, "T": T, "J": J,
                     "t": t, "n": n, "cover": cover, "limit": None, "twin": False, "edge": edge}
                new = cover.difference(_blend_disc(b)).difference(metal)
                want = (box(min(xs, xs + r * sx), min(yw, yw + r * sy), max(xs, xs + r * sx), max(yw, yw + r * sy))
                        .difference(Point(xs + r * sx, yw + r * sy).buffer(r, resolution=256)))
                odd = new.symmetric_difference(want).buffer(-_ROUND_TOL / 2.0)
                if not odd.is_empty:
                    raise RuntimeError(f"{at}: the blend adds {new.area:.4f} mm2 where a square "
                                       f"corner takes {want.area:.4f}, near "
                                       f"({odd.centroid.x:.3f}, {odd.centroid.y:.3f})")
                for ref, p, _h, src in _cached_parts():
                    if src == "model" and part_envelope(ref, p).distance(new) < LIP_CLR - 1e-9:
                        raise RuntimeError(f"{at}: its fillet stands "
                                           f"{part_envelope(ref, p).distance(new):.3f} mm from {ref}, "
                                           f"inside LIP_CLR {LIP_CLR}")
                b["area"] = new.area
                out.append(b)
        _c["t"] = out
    return _c["t"]


def tab_root_metal():
    """[polygon] -- each tab root as plan metal, WITH the part of its cover that lies in the
    wall and the tab, so that a union with those is seamless (boss_blend_metal's shape)."""
    return [b["cover"].difference(_blend_disc(b)) for b in tab_roots()]


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
    kps = [_boss_even(mx, my, r, _boss_keepout(r, p)) for r, p in _boss_foul_parts(mx, my)]
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
            cen.append(_park_on_wall(v, best[1], fixed))
        out.append(cen)
    return kps, out


def _park_on_wall(v, cc, fixed):
    """The bore centre `cc` the search above found for keep-out corner `v`, made EXACT where
    the tool is parked against one straight wall.

    The search steps half a degree, so a bore the wall stops comes back up to 0.004 mm short
    of it. Nobody could see that while the sliver of void between a corner boss and the
    recess wall was left in the model. Since 2026-11-14 that sliver is metal (boss_webs), and
    the bore's cylinder is the face that metal ends on: 0.004 short of the wall, it would
    leave a skin of titanium 0.004 mm thick running under the bore. So the centre is put on
    the circle of TOOL_R about the corner, TOOL_R - BLEND_BITE off the wall: the bore then
    CROSSES the wall plane instead of grazing it, which is a join a kernel can build, and the
    shell CAD never cuts the wall with it (the scallop tool is the boss's own cylinder, and a
    web is cut before it is unioned). A bore nothing stops, or one wedged between two walls,
    is returned as found."""
    rings = []
    for g in getattr(fixed, "geoms", [fixed]):
        if g.geom_type == "Polygon":
            rings += [g.exterior] + list(g.interiors)
    hits = []
    for ring in rings:
        cs = list(ring.coords)
        for (x0, y0), (x1, y1) in zip(cs[:-1], cs[1:]):
            L = math.hypot(x1 - x0, y1 - y0)
            if L < 0.5:
                continue
            ux, uy = (x1 - x0) / L, (y1 - y0) / L
            lam = (cc[0] - x0) * ux + (cc[1] - y0) * uy
            if not (0.0 <= lam <= L):
                continue
            nx, ny = -uy, ux
            d = (cc[0] - x0) * nx + (cc[1] - y0) * ny
            if d < 0:
                nx, ny, d = -nx, -ny, -d
            if abs(d - TOOL_R) < 0.01:
                hits.append(((x0, y0), (nx, ny)))
    if len(hits) != 1:
        return (round(cc[0], 6), round(cc[1], 6))
    (ax, ay), (nx, ny) = hits[0]
    k = (TOOL_R - BLEND_BITE - ((v[0] - ax) * nx + (v[1] - ay) * ny)) / TOOL_R
    if abs(k) > 1.0:
        return (round(cc[0], 6), round(cc[1], 6))
    tn, dt = math.atan2(ny, nx), math.acos(k)
    cands = [(v[0] + TOOL_R * math.cos(tn + sg * dt), v[1] + TOOL_R * math.sin(tn + sg * dt))
             for sg in (1.0, -1.0)]
    q = min(cands, key=lambda c: math.hypot(c[0] - cc[0], c[1] - cc[1]))
    if math.hypot(q[0] - cc[0], q[1] - cc[1]) > 0.02:
        raise RuntimeError(f"bore at ({cc[0]:.4f}, {cc[1]:.4f}): parking it against its wall "
                           f"would move it {math.hypot(q[0] - cc[0], q[1] - cc[1]):.4f} mm -- "
                           f"the search and the exact position disagree")
    return (round(q[0], 9), round(q[1], 9))


def _lip_metal_cached(_c={}):
    if "m" not in _c:
        _c["m"] = lip_metal_poly()
    return _c["m"]


def _coil_cached(_c={}):
    if "t" not in _c:
        _c["t"] = _coil_tracks()
    return _c["t"]


def _coil_need(mx, my):
    """([(cx, cy, r)], [band]) -- what COIL_CLR asks of the boss at (mx, my): the coil's copper
    grown by the clearance, in the pieces it is made of. Both lists are empty for a boss the
    coil is nowhere near, which today is six of the eight.

    A track grown by a distance is a round-ended slot: a disc of r = COIL_CLR + half the
    track's width about each end, and the straight band between them."""
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
    return [(px, py, r) for (px, py), r in sorted(discs.items())], slabs


def boss_coil_chord_d(_c={}):
    """How far from its axis a mid-span boss is cut straight across for the coil: the least
    the coil's keep-out leaves any of them, so that all of them are alike. None if the coil
    reaches no mid-span boss."""
    if "d" not in _c:
        ds = []
        for mx, my in MOUNTS:
            if _is_corner_boss(mx, my):
                continue
            discs, slabs = _coil_need(mx, my)
            ds += [abs(cy - my) - r for _cx, cy, r in discs]
            for sl in slabs:
                x0, y0, x1, y1 = sl.bounds
                ds.append(min(abs(y0 - my), abs(y1 - my)) if not (y0 < my < y1) else 0.0)
        _c["d"] = round(min(ds), 6) if ds else None
    return _c["d"]


def boss_coil_cuts(mx, my):
    """([(cx, cy, r)], [slab]) -- what the coil takes out of the boss at (mx, my), as the pieces
    a cutter makes it from: cylinders and plane-sided slabs. Both lists are empty for a boss the
    coil is nowhere near.

    AT A MID-SPAN BOSS IT IS A STRAIGHT CUT (2026-11-15, DRH, circling one on a plan: "smooth
    contiguous surfaces for the milling to be done simpler"). The keep-out itself is a disc
    about the coil's corner (_coil_need), and cut as a disc it left each side of the boss as a
    dip and a hump -- a hollow of R1.15, a rag of the boss's own circle, then the blend to the
    wall: three faces and two more rounds where one plane does. So the boss is cut square
    across, boss_coil_chord_d() from its axis on BOTH sides (the far side for symmetry, as the
    hollow was mirrored before), and that distance is the least the coil leaves either boss,
    so the two are alike. Only ever less metal than the disc took; and it is checked here,
    not assumed, that what is left stands COIL_CLR off the copper.

    A corner boss the coil reached would still get the discs and bands themselves: nothing
    has had to decide what a straight cut means beside a short-edge wall, and none is in
    reach today."""
    discs, slabs = _coil_need(mx, my)
    if not discs and not slabs:
        return [], []
    if _is_corner_boss(mx, my):
        small = [(px, py, r) for px, py, r in discs if r < TOOL_R - 1e-9]
        if small:
            px, py, r = small[0]
            raise RuntimeError(
                f"boss at ({mx}, {my}): the coil keep-out about ({px}, {py}) is R{r:.3f}, a hollow "
                f"the Ø{2 * TOOL_R:g} finisher cannot cut -- COIL_CLR {COIL_CLR} is too small for "
                f"this rule to be machined as modelled")
        return discs, slabs
    d = boss_coil_chord_d()
    far = BOSS_R + 1.0
    cuts = [box(mx - far, my - far, mx + far, my - d), box(mx - far, my + d, mx + far, my + far)]
    left = Point(mx, my).buffer(BOSS_R, resolution=256).difference(unary_union(cuts))
    cu = unary_union([Point(a).buffer(w / 2.0, resolution=64) if a == b_
                      else LineString([a, b_]).buffer(w / 2.0, resolution=64)
                      for a, b_, w in _coil_cached()])
    if left.distance(cu) < COIL_CLR - 1e-6:
        raise RuntimeError(f"boss at ({mx}, {my}): cut straight across {d:.3f} mm from its axis it "
                           f"still stands {left.distance(cu):.3f} mm from NFC coil copper, inside "
                           f"COIL_CLR {COIL_CLR} -- the coil comes at this boss from the side, and "
                           f"a cut parallel to the short edges does not clear it")
    if d < THREAD_KEEP + 0.5:
        raise RuntimeError(f"the coil would cut the mid-span bosses {d:.3f} mm from their axes, "
                           f"within 0.5 of the thread keep-out {THREAD_KEEP}")
    return [], cuts


def boss_coil_keepout(mx, my):
    """The coil keep-out at the boss at (mx, my) as one polygon, or None where the coil is out
    of reach: boss_coil_cuts() united, for boss_fouls(), the drawing and every 2D check."""
    discs, slabs = boss_coil_cuts(mx, my)
    if not discs and not slabs:
        return None
    return unary_union([Point(x, y).buffer(r, resolution=64) for x, y, r in discs] + slabs)


def boss_coil_need(mx, my):
    """The keep-out COIL_CLR itself asks for at the boss at (mx, my) -- the copper grown by the
    clearance -- or None. boss_coil_keepout() is what is CUT, which at a mid-span boss is
    more (a straight cut); this is what a blend may not stand in."""
    discs, slabs = _coil_need(mx, my)
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


# ---- EVEN AND SYMMETRIC (2026-11-14, DRH, looking at the cavity: "as to each boss/tab, make
# them mostly symmetric or even") -----------------------------------------------------------
# Every boss was cut back for its own supercap by that cap's own numbers, so no two came out
# alike: the flats stood 1.475, 1.524, 1.545 and 1.676 mm from their axes, and a mid-span boss
# kept, beyond the end of its cap's keep-out, a lump of boss with a dogbone bored into the
# corner of it -- on one side only, so the boss did not mirror itself either. None of that was
# wrong; all of it was the board's part positions showing through as lumps in the titanium.
#
#   * ONE FLAT DISTANCE. Every cap-facing flat stands boss_flat_d() from its boss axis: the
#     least any cap leaves any boss, so each cap is cleared by at least what its own bay asks.
#   * THE FLAT RUNS THE WHOLE BOSS. At a mid-span boss it is a full chord: no lump beyond the
#     keep-out's end, no inside corner for a dogbone to relieve, and the boss mirrors itself
#     about its own centre line. At a corner boss it runs from the boss out to the short-edge
#     wall and meets it through a true R of the finisher (boss_roots, below). Until 2026-11-15
#     it stopped 0.25 short of that wall and a dogbone was parked in the corner; see there.
#   * ONLY EVER LESS METAL. An evened keep-out is the cap's own keep-out UNITED with the slab
#     that evens it, so nothing a cap was cleared by is given back.
#
# The coil reliefs and the blends follow (boss_coil_cuts, _boss_blends): what one side of a
# mid-span boss has, the other side has too.
def _is_corner_boss(mx, my):
    """True for a boss beside a SHORT edge (the first and last rows of MOUNTS)."""
    ys = sorted({y for _x, y in MOUNTS})
    return my in (ys[0], ys[-1])


def _cap_keepouts(mx, my):
    return [_boss_keepout(r, p) for r, p in _boss_foul_parts(mx, my) if r in CAP_DATUM]


def boss_flat_d(_c={}):
    """The ONE distance from a boss axis to its cap-facing flat: the least any supercap's
    keep-out stands from any boss it fouls. Computed from the board, never typed."""
    if "d" not in _c:
        _c["d"] = min(k.distance(Point(mx, my)) for mx, my in MOUNTS for k in _cap_keepouts(mx, my))
    return _c["d"]


def _boss_even(mx, my, ref, kp):
    """The keep-out `kp` of the part `ref` at the boss at (mx, my), EVENED: a supercap's is
    united with the slab that puts its flat at boss_flat_d() and runs it the whole boss. Any
    other part's is returned as it is."""
    if ref not in CAP_DATUM:
        return kp
    x0, _y0, x1, _y1 = kp.bounds
    sgn = 1.0 if (x0 + x1) / 2.0 > mx else -1.0
    edge = x0 if sgn > 0 else x1
    if abs(abs(edge - mx) - kp.distance(Point(mx, my))) > 1e-6:
        raise RuntimeError(
            f"boss at ({mx}, {my}): {ref}'s keep-out does not face it squarely across x "
            f"(edge {edge:.3f}, {kp.distance(Point(mx, my)):.3f} from the axis) -- the evening "
            f"rule is written for a cap lying between the two long-edge rows of bosses")
    fx = mx + sgn * boss_flat_d()
    far = BOSS_R + 2 * TOOL_R + 1.0                  # past every corner boss_cuts() looks at
    # the same slab at all eight: at a corner boss it runs on THROUGH the short-edge wall, so
    # the flat ends on that wall and nowhere short of it (boss_roots lays the corner)
    ya, yb = my - far, my + far
    out = kp.union(box(min(fx, fx + sgn * far), ya, max(fx, fx + sgn * far), yb))
    if out.geom_type != "Polygon":
        raise RuntimeError(f"boss at ({mx}, {my}): evening {ref}'s keep-out split it in {len(out.geoms)}")
    return out


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


# ---- EVERY OUTSIDE CORNER OF A BOSS IS R(CONTOUR_R) (2026-11-14, DRH) -------------------------
# "Eliminate the hard corners and radius them." A boss cut back by planes and bores ends in
# outside corners: where a flat leaves the boss's own circle, where a flat meets a bore, where
# a coil hollow runs out into the circle. Each is now a round of CONTOUR_R -- the finisher's
# own radius, so every corner in the cavity, inside or outside, is R1.0 or more.
#
# WHAT A ROUND IS: the ball of CONTOUR_R rolled round INSIDE the metal. Where it rests against
# two faces at once it leaves a corner it cannot fill, and that corner is what comes off.
#
# HOW ONE IS FOUND, in two steps, because one instrument cannot do both:
#   1. The metal's polygon is opened (eroded, then dilated) to FIND the corners, however the
#      faces happen to be arranged. That is good to about 0.005 mm -- the outline is
#      simplified, and GEOS simplifies again inside every buffer.
#   2. Each corner is then SOLVED against the faces themselves -- planes and circles, as the
#      shell cuts them -- because the shell cuts the round as a true cylinder, and a cylinder
#      a few microns out of tangent is a step. Of the faces near the corner, the round's two
#      are the pair a ball can touch at once while lying in the metal, each where that face is
#      still the surface. It matters on the west bosses: there the ball stops on the flat and
#      the BLEND, with the boss's own circle 0.0026 mm behind the blend, and the first build of
#      this solved the round against the circle and left a 0.01 mm step in the blend.
#
# BLEND_BITE again: the centre is solved CONTOUR_R - BLEND_BITE inside each face, so the round
# crosses its two neighbours at three or four degrees instead of grazing them.
#
# Only ever less metal, and never near the thread: _boss_rounds() refuses a round that comes
# inside THREAD_KEEP.
#
# EVERY outside corner, however slight. Four of today's twenty are where a coil hollow runs out
# into the boss's circle at 150 degrees or more, and a round there takes under 0.006 mm2. They
# are cut all the same: "every outside corner is R1.0" is a sentence a sheet can carry and a
# gate can hold, and "every outside corner sharper than some angle" is neither.
CONTOUR_R = TOOL_R         # outside corners of a boss, and the tip corners of a lip tab
_ROUND_MIN = 1e-4          # mm2: a corner that gives up less than this is a BLEND_BITE crease
_ROUND_ON = 1e-3           # mm: a contact point this near the surface is on it
_ROUND_TOL = 0.016         # mm: the thickest crescent a round as solved may differ by from the
                           # corner as rolled: 0.005 of polygon, and the centre moving by
                           # BLEND_BITE / sin of half the corner's angle (0.0024 at today's)


def boss_rounds(mx, my):
    """[round] -- the outside corners of the boss at (mx, my), each a dict:

        O, r     the round's circle, a TRUE cylinder in the shell (r is CONTOUR_R)
        A, B     where it leaves the two faces it rests on (the tangent points, but for
                 BLEND_BITE)
        cover    a sector of board about O holding the corner: the shell CAD takes
                 `cover less the cylinder` out of the boss
        cut      that, in 2D: what boss_island() loses to this round
        took     the metal it actually removes (cut, less the air it also covers)
        faces    the two faces, as _round_faces() gives them"""
    return _rounds_cached()[(mx, my)]


def _rounds_cached(_c={}):
    if "r" not in _c:
        _c["r"] = {}
        _c["r"] = {m: _boss_rounds(*m) for m in MOUNTS}
    return _c["r"]


def _round_cover(O, A, B, R, rout):
    """The sector of board about O between the rays through A and B, from well inside the
    round's cylinder (R - 0.30) out past `rout`: what a round's corner stands in. The shell
    CAD extrudes it and takes the cylinder out; its two straight sides run along the normals
    of the two faces the round rests on."""
    ta = math.atan2(A[1] - O[1], A[0] - O[0])
    da = (math.atan2(B[1] - O[1], B[0] - O[0]) - ta + math.pi) % (2.0 * math.pi) - math.pi
    nseg = max(2, int(math.ceil(abs(da) / math.radians(10.0))))
    rr = rout / math.cos(abs(da) / nseg / 2.0)      # the outer polyline stays outside rout
    rin = R - 0.30
    return Polygon([(O[0] + rin * math.cos(ta), O[1] + rin * math.sin(ta)),
                    (O[0] + rr * math.cos(ta), O[1] + rr * math.sin(ta))]
                   + [(O[0] + rr * math.cos(ta + da * (k + 0.5) / nseg),
                       O[1] + rr * math.sin(ta + da * (k + 0.5) / nseg)) for k in range(nseg)]
                   + [(O[0] + rr * math.cos(ta + da), O[1] + rr * math.sin(ta + da)),
                      (O[0] + rin * math.cos(ta + da), O[1] + rin * math.sin(ta + da))])


def _round_faces(mx, my):
    """The faces a round on the boss at (mx, my) can rest against, as the shell cuts them:
    ("in", (cx, cy), r)  a cylinder with the metal inside it -- the boss itself;
    ("out", (cx, cy), r) a cylinder with the metal outside it -- a dogbone or a coil hollow;
    ("line", (px, py), (nx, ny)) a plane through p with the metal on the n side -- a flat."""
    c = Point(mx, my)
    faces = [("in", (mx, my), BOSS_R)]
    kps, dbs = boss_cuts(mx, my)
    cdiscs, cslabs = boss_coil_cuts(mx, my)
    for g in list(kps) + list(cslabs):
        for poly in getattr(g, "geoms", [g]):
            cs = list(poly.exterior.coords)
            for (x0, y0), (x1, y1) in zip(cs[:-1], cs[1:]):
                L = math.hypot(x1 - x0, y1 - y0)
                if L < 1e-6 or LineString([(x0, y0), (x1, y1)]).distance(c) > BOSS_R:
                    continue
                n = (-(y1 - y0) / L, (x1 - x0) / L)
                if poly.contains(Point((x0 + x1) / 2 + 1e-4 * n[0], (y0 + y1) / 2 + 1e-4 * n[1])):
                    n = (-n[0], -n[1])
                faces.append(("line", (x0, y0), n))
    faces += [("out", (qx, qy), TOOL_R) for d in dbs for qx, qy in d]
    faces += [("out", (x, y), r) for x, y, r in cdiscs]
    # ...and the blends that join this boss to the wall. A west boss's blend takes over the
    # boss's circle 0.63 mm from the end of the flat, less than a round needs: the round there
    # rests on the flat and the blend, and that last stretch of circle is gone. On the east
    # the lip is narrower, the blend starts farther round, and the round ends on the circle
    # 0.57 mm short of it.
    faces += [("out", b["O"], b["r"]) for b in boss_blends(mx, my)]
    return faces


def _face_depth(f, o):
    """How far the point o stands inside the metal from the face f (negative: outside)."""
    if f[0] == "line":
        return (o[0] - f[1][0]) * f[2][0] + (o[1] - f[1][1]) * f[2][1]
    d = math.hypot(o[0] - f[1][0], o[1] - f[1][1])
    return f[2] - d if f[0] == "in" else d - f[2]


def _face_foot(f, o):
    """The point of the face f nearest o."""
    if f[0] == "line":
        d = _face_depth(f, o)
        return (o[0] - d * f[2][0], o[1] - d * f[2][1])
    d = math.hypot(o[0] - f[1][0], o[1] - f[1][1])
    return (f[1][0] + f[2] * (o[0] - f[1][0]) / d, f[1][1] + f[2] * (o[1] - f[1][1]) / d)


def _depth_locus(f, d):
    """The points standing d inside the metal from f: ("line", p, u) or ("circle", c, r)."""
    if f[0] == "line":
        return ("line", (f[1][0] + d * f[2][0], f[1][1] + d * f[2][1]), (-f[2][1], f[2][0]))
    return ("circle", f[1], f[2] - d if f[0] == "in" else f[2] + d)


def _locus_meet(a, b):
    """Where two loci from _depth_locus() cross: 0, 1 or 2 points."""
    if a[0] == "circle" and b[0] == "line":
        a, b = b, a
    if a[0] == "line" and b[0] == "line":
        (px, py), (ux, uy) = a[1], a[2]
        (qx, qy), (vx, vy) = b[1], b[2]
        den = ux * vy - uy * vx
        if abs(den) < 1e-12:
            return []
        t = ((qx - px) * vy - (qy - py) * vx) / den
        return [(px + t * ux, py + t * uy)]
    if a[0] == "line":
        (px, py), (ux, uy) = a[1], a[2]
        (cx, cy), r = b[1], b[2]
        fx, fy = px - cx, py - cy
        bq = fx * ux + fy * uy
        disc = bq * bq - (fx * fx + fy * fy - r * r)
        if disc < 0:
            return []
        return [(px + t * ux, py + t * uy) for t in (-bq + math.sqrt(disc), -bq - math.sqrt(disc))]
    (ax, ay), ra = a[1], a[2]
    (bx, by), rb = b[1], b[2]
    d = math.hypot(bx - ax, by - ay)
    if d < 1e-12 or d > ra + rb or d < abs(ra - rb):
        return []
    k = (ra * ra - rb * rb + d * d) / (2 * d)
    h = math.sqrt(max(ra * ra - k * k, 0.0))
    mx_, my_ = ax + k * (bx - ax) / d, ay + k * (by - ay) / d
    return [(mx_ + sg * h * (by - ay) / d, my_ - sg * h * (bx - ax) / d) for sg in (1.0, -1.0)]


def _boss_rounds(mx, my):
    c = Point(mx, my)
    R = CONTOUR_R
    disc = c.buffer(BOSS_R, resolution=64)
    win = c.buffer(BOSS_R + 2.0 * R + 1.0)
    wallm = box(-5.0, -5.0, W + 5.0, H + 5.0).difference(recess_poly())
    raw = unary_union([_shell_metal(True, rounds=False), wallm]).intersection(win)
    raw = raw.buffer(4e-3, join_style=2).buffer(-4e-3, join_style=2)     # hairlines are not edges
    # The same metal with this boss's island EXACT. Rolling a ball in polygons FINDS the
    # corners and is good to about 0.005 mm: the outline is simplified by that much, and GEOS
    # simplifies again inside every buffer (by a hundredth of the distance). That is not good
    # enough to say which two faces a round rests on -- on the west bosses the ball stops on
    # the flat and the BLEND with the boss's own circle 0.0026 mm behind it -- so that is
    # decided below from the faces themselves, against this.
    rawx = unary_union([_lip_metal_cached(), boss_island(mx, my, rounds=False, exact=True), wallm]
                       + list(boss_blend_metal(mx, my))
                       + [u for u, _cov in boss_webs(mx, my)]).intersection(win)
    rawx = rawx.buffer(1e-4, join_style=2).buffer(-1e-4, join_style=2)
    edge = rawx.boundary
    opened = raw.buffer(-R, join_style=1, resolution=64).buffer(R, join_style=1, resolution=64)
    gone = raw.difference(opened)
    faces = _round_faces(mx, my)
    at = f"boss at ({mx}, {my})"
    out = []
    for K in getattr(gone, "geoms", [gone]):
        if K.geom_type != "Polygon" or K.area < _ROUND_MIN or not disc.buffer(0.15).contains(K):
            continue                 # a crease; or a corner of the lip, which is not this rule's
        # the stretch of K's outline the ball left: on the opened metal, off the raw one
        arc = [q for q in K.exterior.coords[:-1]
               if opened.exterior.distance(Point(q)) < 1e-7 and raw.exterior.distance(Point(q)) > 1e-5]
        if len(arc) < 3:
            raise RuntimeError(f"{at}: the corner at ({K.centroid.x:.3f}, {K.centroid.y:.3f}) "
                               f"({K.area:.5f} mm2) has no arc to read a centre from")
        (x1, y1), (x2, y2), (x3, y3) = arc[0], arc[len(arc) // 2], arc[-1]
        dd = 2.0 * (x1 * (y2 - y3) + x2 * (y3 - y1) + x3 * (y1 - y2))
        if abs(dd) < 1e-12:
            raise RuntimeError(f"{at}: the corner at ({K.centroid.x:.3f}, {K.centroid.y:.3f}) is flat")
        o0 = (((x1 * x1 + y1 * y1) * (y2 - y3) + (x2 * x2 + y2 * y2) * (y3 - y1)
               + (x3 * x3 + y3 * y3) * (y1 - y2)) / dd,
              ((x1 * x1 + y1 * y1) * (x3 - x2) + (x2 * x2 + y2 * y2) * (x1 - x3)
               + (x3 * x3 + y3 * y3) * (x2 - x1)) / dd)
        if abs(math.hypot(x1 - o0[0], y1 - o0[1]) - R) > 2e-3:
            raise RuntimeError(f"{at}: the corner at ({K.centroid.x:.3f}, {K.centroid.y:.3f}) is "
                               f"not one arc of R{R:g} (it reads R{math.hypot(x1 - o0[0], y1 - o0[1]):.4f}): "
                               f"two rounds have run together, and this rule cuts them one at a time")
        # WHICH two faces. Of those the rolled centre stands about CONTOUR_R inside, take
        # them two at a time and put a ball exactly tangent to both: it is the round's ball
        # if it lies in the metal AND touches each face where that face is still the surface.
        # (On a west boss the ball tangent to the flat and the boss's circle lies in the metal
        # too -- but it touches the circle 0.011 mm under the blend, and can roll on.)
        near = [f for f in faces if abs(_face_depth(f, o0) - R) < 0.03]
        ok = []
        for i in range(len(near)):
            for j in range(i + 1, len(near)):
                for Ox in _locus_meet(_depth_locus(near[i], R), _depth_locus(near[j], R)):
                    if math.hypot(Ox[0] - o0[0], Ox[1] - o0[1]) > 0.03:
                        continue
                    if not Point(Ox).buffer(R - _ROUND_ON / 2.0, resolution=256).within(rawx):
                        continue
                    if all(edge.distance(Point(_face_foot(f, Ox))) < _ROUND_ON for f in (near[i], near[j])):
                        ok.append((near[i], near[j]))
        if len(ok) != 1:
            raise RuntimeError(f"{at}: the corner about ({o0[0]:.3f}, {o0[1]:.3f}) rests on "
                               f"{len(ok)} pairs of faces, not one; within reach: "
                               + ", ".join(f"{f[0]} {_face_depth(f, o0):.4f}" for f in near))
        on = ok[0]
        best = None
        for O in _locus_meet(_depth_locus(on[0], R - BLEND_BITE), _depth_locus(on[1], R - BLEND_BITE)):
            if math.hypot(O[0] - o0[0], O[1] - o0[1]) > 0.03:
                continue
            A, B = _face_foot(on[0], O), _face_foot(on[1], O)
            rout = max(math.hypot(qx - O[0], qy - O[1]) for qx, qy in K.exterior.coords) + 0.05
            cover = _round_cover(O, A, B, R, rout)
            if not cover.is_valid:
                continue
            cut = cover.difference(Point(O).buffer(R, resolution=256))
            took = cut.intersection(rawx)
            best = (0.0, O, A, B, cover, cut, took, (on[0], on[1]))
        if best is None:
            raise RuntimeError(f"{at}: no two faces give the round about ({o0[0]:.3f}, {o0[1]:.3f}) "
                               f"({len(near)} within reach of it)")
        off, O, A, B, cover, cut, took, on = best
        # The round as solved sits BLEND_BITE deeper than the ball as rolled, and the ball was
        # rolled in polygons, so the two corners differ by a crescent a few microns thick down
        # each side -- and by nothing with any body to it. A cover reaching other metal has
        # body.
        odd = took.symmetric_difference(K).buffer(-_ROUND_TOL / 2.0)
        if not odd.is_empty:
            raise RuntimeError(f"{at}: the round about ({O[0]:.3f}, {O[1]:.3f}) would take "
                               f"{took.area:.4f} mm2 where the rolled ball leaves {K.area:.4f}, "
                               f"and they differ by more than a crescent near "
                               f"({odd.centroid.x:.3f}, {odd.centroid.y:.3f})")
        if not disc.buffer(0.15).contains(took):
            raise RuntimeError(f"{at}: the round about ({O[0]:.3f}, {O[1]:.3f}) cuts metal that "
                               f"is not this boss's")
        if took.distance(c) < THREAD_KEEP:
            raise RuntimeError(f"{at}: the round about ({O[0]:.3f}, {O[1]:.3f}) comes "
                               f"{took.distance(c):.3f} from the screw axis, inside THREAD_KEEP {THREAD_KEEP}")
        out.append({"O": (round(O[0], 9), round(O[1], 9)), "r": R, "A": A, "B": B,
                    "cover": cover, "cut": cut, "took": took, "faces": on, "area": took.area})
    out.sort(key=lambda rd: math.atan2(rd["O"][1] - my, rd["O"][0] - mx))
    return out


def boss_island(mx, my, rounds=True, exact=False):
    """A boss disc scalloped clear of anything that fouls it, and -- unless `rounds` is False --
    with every outside corner that leaves rounded at CONTOUR_R (boss_rounds).

    The outline is simplified by 0.005, which is nothing to a clearance and everything to a
    tangency: `exact` gives it unsimplified and drawn four times as fine, for the one caller
    that rolls a ball round it (_boss_rounds)."""
    disc = Point(mx, my).buffer(BOSS_R, resolution=256 if exact else 64)
    foul = boss_fouls(mx, my) + ([rd["cut"] for rd in boss_rounds(mx, my)] if rounds else [])
    if not foul:
        return disc
    scal = disc.difference(unary_union(foul))
    if scal.geom_type == "MultiPolygon":
        keep = [g for g in scal.geoms if g.contains(Point(mx, my))]
        scal = keep[0] if keep else disc
    return scal if exact else scal.simplify(0.005, preserve_topology=True)


# ---- where a boss meets the wall: BLENDS and WEBS (2026-11-14) ---------------------------
# Until now the model left two things at every mount boss that no cutter makes.
#
#   * Where the boss's circle crosses the lip's cavity wall -- twelve places: both sides of the
#     four mid-span bosses, and the long-edge side of the four corner bosses -- it kept a sharp
#     inside corner, acute on the east. The sheet told the shop to finish those with the Ø2.0,
#     the brace was cut to the R1.0 that leaves (cavity_as_milled), and assembly_drc [H]
#     measured the part that way; but the solid a shop is handed said "sharp", and a sharp
#     acute corner is a place where a tool dwells and chatters to make its own radius.
#   * Beside each CORNER boss, on the short-edge side, it kept a slot of void between the boss
#     and the recess wall: 0.17 mm wide at its narrowest, closed at one end, and ending at the
#     boss's own Ø2.0 bore. No tool enters it. It is there because the short-edge lip is cut
#     to none beside a supercap (LIP_MIN) while the boss disc stands 0.22 off the wall -- an
#     accident of two rules meeting, not a feature. DRH saw both in a render and asked for the
#     first to be a modelled curve and the second explained.
#
# BLENDS. Each of the twelve junctions gets a concave blend of BLEND_R: a true circle, tangent
# to the wall and to the boss. BLEND_R is twice the finisher's radius on purpose -- the tool
# sweeps it with its centre on an R1.0 arc and never stops in a corner. The wall it is tangent
# to is the one the shell is CUT to (void_as_cut(): cavity_void_poly() is simplified by 0.01
# for the kernel's sake, and its long walls lean by up to 0.0005 mm; a blend laid out on the
# ideal wall met the cut one with a step, and the first prototype of this added 49 sliver
# faces to the max shell that way).
#
# WEBS. The slot beside a corner boss is filled: boss, web and wall are one piece of metal.
# Until 2026-11-15 a web ended on the boss's own Ø2.0 bore; it ends on the boss's FLAT now,
# which runs to the wall (boss_roots: the bore went, on DRH's word, and what that costs is
# stated there).
#
# THE FERRITE LIMITS TWO OF THEM. The sheet behind the coil (FER) lies in the cavity at the
# height the blends stand at, and its two east corners are 0.43 and 0.34 mm from the bosses at
# y28.63 and y60.27. At BLEND_R the blends on the ferrite's side of those two bosses would
# stand INSIDE the sheet's corners -- 0.035 and 0.075 mm2 of titanium where the ferrite goes
# -- and the first full build of this did exactly that with every gate green, because no gate
# had ever held the sheet against the shell (assembly_drc [F] and [H] do now). So a blend
# that would come within FER_CLR of the sheet is cut at TOOL_R instead: the radius the
# finisher leaves in that corner whatever the model says, so the part does not move there.
# That leaves the sheet's corners where they have always been as milled, 0.24 and 0.15 mm
# from titanium -- a clearance nobody chose, now printed by [H] instead of unknown.
#
# BLEND_BITE. A circle exactly tangent to a plane meets it along a line of zero angle, and a
# boolean built on that is a coin toss. So each blend is set BLEND_BITE deeper than tangent
# into the lip and into the boss, and a wall-parked bore the same into its wall
# (_park_on_wall): every join is then a crossing at two to four degrees. Two microns; the
# radius itself is exact.
BLEND_R = 2.00             # concave blend, boss to lip wall. Must exceed TOOL_R (checked).
BLEND_BITE = 0.002         # how far past tangent a blend or a parked bore is set, for the kernel
_BLEND_LIP = 0.20          # how far a blend's cover reaches into the lip   } both more than
_BLEND_BOSS = 0.30         # ...and into the boss                           } the 0.10 edge-break
_BLEND_PAST = 0.60         # ...and along the wall past the old corner, under the boss
_WEB_INTO = 0.20           # how far a web's cover reaches into the metal round it


def void_as_cut(_c={}):
    """The cavity void THE SHELL IS CUT TO, board coords: cavity_void_poly() (simplified, as
    the shell CAD has always cut it; less the tab-tip rounds, which the shell cuts as true
    cylinders afterwards -- tab_rounds) held inside the board recess -- the recess is EDGE_FIT
    smaller than the board, and a void that ran out to the board edge would be cut under the
    recess wall. The shell CAD's own _void_in_recess() until 2026-11-14; here now because the
    blends below have to be laid out on the wall the cutter is actually given."""
    if "v" not in _c:
        # _trims False: the tab tips are cut square here and rounded by tab_rounds(), as true
        # cylinders -- which are laid out on this polygon, so it cannot wait for them
        v = cavity_void_poly(_trims=False).intersection(recess_poly())
        if v.geom_type != "Polygon":             # a clip can shed dust; the void is the big piece
            v = max((g for g in v.geoms if g.geom_type == "Polygon"), key=lambda g: g.area)
        _c["v"] = v
    return _c["v"]


def boss_blends(mx, my):
    """[blend] -- one for each place the boss at (mx, my) crosses a straight run of the lip's
    cavity wall. Each is a dict:

        O, r     the blend's circle, a TRUE cylinder in the shell. r is BLEND_R, or TOOL_R
                 where BLEND_R would bring metal within FER_CLR of the ferrite sheet
        limit    None, or the name of what held r to TOOL_R ("FER1")
        F        its foot on the wall (the tangent point, but for BLEND_BITE)
        T        the point of the boss it is tangent to (likewise)
        J        the sharp corner it replaces
        t, n     unit vectors at J: along the wall away from the boss, and into the cavity
        cover    a straight-sided polygon holding the blend, reaching into the lip and the
                 boss: the shell CAD extrudes this and cuts the cylinder out of it

    The cover's two ends lie on lines through O -- through F square to the wall, and through
    T and the boss axis. Those are meridian planes of the blend AND of the edge-break cones
    the shell cuts round it, so the break on the blend runs into the lip's and the boss's own
    with nothing left standing at either end.

    A crossing whose wall does not run straight as far as the foot gets no blend (the stub of
    short-edge lip under a corner boss, where the wall is a fillet 0.2 mm long). boss_webs()
    then has to account for whatever a tool cannot reach there, and raises if it cannot."""
    return _blends_cached()[(mx, my)]


def _blends_cached(_c={}):
    if "b" not in _c:
        if BLEND_R <= TOOL_R:
            raise RuntimeError(f"BLEND_R {BLEND_R} must exceed the finisher's radius {TOOL_R}")
        _c["b"] = {m: _boss_blends(*m) for m in MOUNTS}
        audit_blends(_c["b"])
    return _c["b"]


def _boss_crossings(mx, my, x0, y0, x1, y1):
    """[(J, t, room)] -- where the straight run (x0, y0)-(x1, y1) crosses the boss circle about
    (mx, my): the crossing J, the unit vector t along the run AWAY from the boss, and how far
    the run goes on straight from J in that direction."""
    L = math.hypot(x1 - x0, y1 - y0)
    if L < 1e-9:
        return []
    ux, uy = (x1 - x0) / L, (y1 - y0) / L
    fx, fy = x0 - mx, y0 - my
    b = fx * ux + fy * uy
    disc = b * b - (fx * fx + fy * fy - BOSS_R * BOSS_R)
    if disc <= 0:
        return []
    out = []
    for sg in (-1.0, 1.0):                           # -1: the run ENTERS the disc here; +1: leaves it
        lam = -b + sg * math.sqrt(disc)
        if 0.0 <= lam <= L:
            out.append(((x0 + lam * ux, y0 + lam * uy), (sg * ux, sg * uy),
                        (L - lam) if sg > 0 else lam))
    return out


def _into(region, J, t):
    """The unit normal to t at J that points INTO `region` (the cavity, or the back's art field)."""
    n = (-t[1], t[0])
    if not region.contains(Point(J[0] + 0.05 * t[0] + 0.05 * n[0], J[1] + 0.05 * t[1] + 0.05 * n[1])):
        n = (-n[0], -n[1])
    return n


def _boss_blends(mx, my):
    v = void_as_cut()
    fer = box(*FER)
    cs = list(v.exterior.coords)
    out, how = [], []
    # a boss the coil has cut straight across (boss_coil_cuts) has no circle left where it meets
    # the wall on that side: the blend there joins two PLANES, the cut and the wall
    chords = [sl for sl in boss_coil_cuts(mx, my)[1]] if not _is_corner_boss(mx, my) else []
    make = (lambda J, t, n, r, room: _blend_chord(mx, my, J, t, n, r, room, chords)) if chords else \
           (lambda J, t, n, r, room: _blend_at(mx, my, J, t, n, r, room))
    for (x0, y0), (x1, y1) in zip(cs[:-1], cs[1:]):
        for J, t, room in _boss_crossings(mx, my, x0, y0, x1, y1):
            n = _into(v, J, t)
            bl = make(J, t, n, BLEND_R, room)
            if bl is None:
                continue                             # the wall turns before the foot: not a blend
            if blend_added(mx, my, bl).distance(fer) < FER_CLR:
                bl = make(J, t, n, TOOL_R, room)
                if bl is None:
                    continue
                bl["limit"] = FER_REF
            out.append(bl); how.append((J, t, n, room))
    # SYMMETRIC (2026-11-14): the two blends of one mid-span boss are alike. Where one is held
    # to a smaller radius, its twin takes that radius too, and says what held the pair.
    if not _is_corner_boss(mx, my) and len({b["r"] for b in out}) > 1:
        small = min(b["r"] for b in out)
        who = next(b["limit"] for b in out if b["r"] == small)
        for i, (J, t, n, room) in enumerate(how):
            if out[i]["r"] > small:
                tw = make(J, t, n, small, room)
                if tw is None:
                    raise RuntimeError(f"boss at ({mx}, {my}): no R{small:g} twin fits at "
                                       f"({J[0]:.2f}, {J[1]:.2f})")
                tw["limit"], tw["twin"] = who, True
                out[i] = tw
    return out


FER_REF = "FER1"           # the ferrite sheet's refdes, for whatever has to say what limited a blend


def _blend_at(mx, my, J, t, n, r, room):
    """One blend of radius r at corner J (wall direction t, cavity side n), or None if the
    wall does not run straight for `room` as far as the blend's foot."""
    # centre: (r - bite) off the wall, (BOSS_R + r - bite) from the boss axis
    dx, dy = J[0] + (r - BLEND_BITE) * n[0] - mx, J[1] + (r - BLEND_BITE) * n[1] - my
    dt = dx * t[0] + dy * t[1]
    rho = BOSS_R + r - BLEND_BITE
    q = dt * dt - (dx * dx + dy * dy) + rho * rho
    if q < 0:
        return None
    s = -dt + math.sqrt(q)
    if not (0.0 <= s <= room):
        return None
    F = (J[0] + s * t[0], J[1] + s * t[1])
    O = (F[0] + (r - BLEND_BITE) * n[0], F[1] + (r - BLEND_BITE) * n[1])
    d = math.hypot(O[0] - mx, O[1] - my)
    u = ((O[0] - mx) / d, (O[1] - my) / d)
    T = (mx + BOSS_R * u[0], my + BOSS_R * u[1])
    cover = Polygon([O, F,
                     (F[0] - _BLEND_LIP * n[0], F[1] - _BLEND_LIP * n[1]),
                     (J[0] - _BLEND_PAST * t[0] - _BLEND_LIP * n[0],
                      J[1] - _BLEND_PAST * t[1] - _BLEND_LIP * n[1]),
                     (mx + (BOSS_R - _BLEND_BOSS) * u[0], my + (BOSS_R - _BLEND_BOSS) * u[1])])
    return {"O": O, "r": r, "F": F, "T": T, "J": J, "t": t, "n": n, "cover": cover, "limit": None,
            "twin": False}


def _blend_chord(mx, my, J, t, n, r, room, chords):
    """One blend of radius r between the wall and a STRAIGHT CUT across the boss (a chord slab
    from boss_coil_cuts), where the wall leaves the boss at J0 = `J`. As _blend_at(), but its
    second face is a plane, not the boss's circle:

        J    the corner the cut and the wall make (what the blend replaces)
        J0   where the boss's circle crosses the wall -- between J0 and J, and between the
             circle and the wall, is a notch of void no cutter enters; the cover fills it
        E0   where the cut leaves the boss's circle

    None if the wall does not run straight as far as the foot. Raises on a wall that is not
    square to the cut: nothing has had to decide what that means."""
    side = [sl for sl in chords if sl.distance(Point(J[0] + 1.5 * t[0], J[1] + 1.5 * t[1])) < 1e-9]
    if len(side) != 1:
        raise RuntimeError(f"boss at ({mx}, {my}): the wall crossing at ({J[0]:.2f}, {J[1]:.2f}) "
                           f"faces {len(side)} straight cuts, not one")
    x0, y0, x1, y1 = side[0].bounds
    yc = y1 if y1 < my else y0                       # the cut's own line, on the boss's side of the slab
    if abs(t[0]) > 1e-3 or abs(n[1]) > 1e-3:
        raise RuntimeError(f"boss at ({mx}, {my}): the wall at ({J[0]:.2f}, {J[1]:.2f}) leans "
                           f"{math.degrees(math.atan2(abs(t[0]), abs(t[1]))):.2f} deg off square to the "
                           f"straight cut -- a blend between them is a rule nobody has written")
    sc = (yc - J[1]) * t[1]                          # from J0 along the wall to the corner
    if sc < 0:
        raise RuntimeError(f"boss at ({mx}, {my}): the straight cut at y{yc:.3f} lies inside the "
                           f"wall crossing at ({J[0]:.2f}, {J[1]:.2f})")
    C = (J[0], yc)
    d = r - BLEND_BITE
    if sc + d > room:
        return None
    F = (C[0] + d * t[0], C[1] + d * t[1])
    O = (F[0] + d * n[0], F[1] + d * n[1])
    T = (C[0] + d * n[0], C[1] + d * n[1])
    half = math.sqrt(max(0.0, BOSS_R * BOSS_R - (yc - my) ** 2))
    E0 = (mx + half * (1.0 if J[0] > mx else -1.0), yc)
    if (T[0] - E0[0]) * n[0] < 0.2:
        raise RuntimeError(f"boss at ({mx}, {my}): an R{r:g} blend at ({C[0]:.2f}, {C[1]:.2f}) would "
                           f"end {abs(T[0] - E0[0]):.2f} mm from where the straight cut leaves the "
                           f"boss -- no flat of the cut left to be tangent to")
    cover = Polygon([O, F,
                     (F[0] - _BLEND_LIP * n[0], F[1] - _BLEND_LIP * n[1]),
                     (J[0] - 0.30 * t[0] - _BLEND_LIP * n[0], J[1] - 0.30 * t[1] - _BLEND_LIP * n[1]),
                     (J[0] - 0.30 * t[0] + 0.20 * n[0], J[1] - 0.30 * t[1] + 0.20 * n[1]),
                     (T[0] - _BLEND_BOSS * t[0], T[1] - _BLEND_BOSS * t[1])])
    return {"O": O, "r": r, "F": F, "T": T, "J": C, "J0": J, "E0": E0, "t": t, "n": n,
            "cover": cover, "limit": None, "twin": False, "chord": True}


def _blend_disc(b, grow=0.0):
    return Point(b["O"]).buffer(b["r"] + grow, resolution=256)


def boss_blend_metal(mx, my):
    """The blends of the boss at (mx, my) as plan polygons, each WITH the part of its cover
    that lies in the lip and the boss -- so a union with those is seamless. For every 2D rule
    and check; the shell CAD builds from boss_blends()."""
    return [b["cover"].difference(_blend_disc(b)) for b in boss_blends(mx, my)]


def blend_added(mx, my, b):
    """What ONE blend adds to the shell in plan: its cover outside the blend's circle, the lip
    and the boss disc -- the new metal, which is what answers to LIP_CLR and COIL_CLR."""
    lip = box(0.0, 0.0, W, H).difference(void_as_cut())
    g = (b["cover"].difference(_blend_disc(b)).difference(lip)
         .difference(Point(mx, my).buffer(BOSS_R, resolution=256)))
    return unary_union([q for q in getattr(g, "geoms", [g]) if q.geom_type == "Polygon" and q.area > 1e-7])


def audit_blends(blends, ps=None):
    """Refuse a blend the shell could not be built from, or that a rule forbids. Run once on
    the real blends; `ps` takes the parts-list shape so check_consistency [8] can plant a
    synthetic part against one and see this refuse it."""
    lip = box(0.0, 0.0, W, H).difference(void_as_cut())
    cu = unary_union([Point(a).buffer(w / 2.0, resolution=64) if a == b_
                      else LineString([a, b_]).buffer(w / 2.0, resolution=64)
                      for a, b_, w in _coil_cached()])
    for (mx, my), bl in blends.items():
        c = Point(mx, my)
        disc = c.buffer(BOSS_R, resolution=256)
        fouls = boss_fouls(mx, my)
        cut = unary_union(fouls) if fouls else None
        for b in bl:
            at = f"blend at ({b['J'][0]:.2f}, {b['J'][1]:.2f}) of the boss at ({mx}, {my})"
            if b.get("chord"):
                # A blend between the wall and a straight cut stands, on purpose, on the far
                # side of that cut -- so what it may not stand in is what the cut was FOR (the
                # coil's own keep-out), and the keep-outs of the parts: not the cut itself.
                kps, dbs = boss_cuts(mx, my)
                real = list(kps) + [Point(q).buffer(TOOL_R, resolution=64) for d_ in dbs for q in d_]
                need = boss_coil_need(mx, my)
                cut = unary_union(real + ([need] if need is not None else [])) if (real or need is not None) else None
            cov = b["cover"]
            if not cov.is_valid or cov.area < 1e-3:
                raise RuntimeError(f"{at}: its cover is not a polygon")
            new = blend_added(mx, my, b)
            if new.is_empty or new.geom_type != "Polygon":
                raise RuntimeError(f"{at}: the cover does not leave ONE piece of new metal")
            # everything of the cover that is not new metal must already be metal (lip or boss)
            stray = cov.difference(_blend_disc(b)).difference(new).difference(lip.buffer(1e-6)) \
                       .difference(disc.buffer(1e-6))
            if stray.area > 1e-6:
                raise RuntimeError(f"{at}: {stray.area:.5f} mm2 of its cover lies in open cavity")
            # the cover may not refill anything cut out of the boss, nor reach the hole
            if cut is not None:
                gone = disc.difference(cut)
                crumbs = unary_union([g for g in getattr(gone, "geoms", [gone]) if not g.contains(c)])
                kept = cov.difference(_blend_disc(b))            # the cover less the blend's own circle
                if kept.intersection(cut).area > 1e-9 or kept.intersection(crumbs).area > 1e-9:
                    raise RuntimeError(f"{at}: a keep-out of this boss reaches the blend -- cutting "
                                       f"a blend back for a part or the coil is a rule nobody has "
                                       f"written; BLEND_R {BLEND_R} is too large here")
            if cov.distance(c) < BOSS_R - 0.75:
                raise RuntimeError(f"{at}: its cover comes within {cov.distance(c):.2f} mm of the "
                                   f"boss axis, where the tapped hole and its spotface are")
            # the edge-break zones the cover has to bury: the lip's strip from the old corner to
            # the foot, and the boss's ring from the old corner to T (each 0.10 wide, taken 0.12)
            J, t, n, F = b.get("J0", b["J"]), b["t"], b["n"], b["F"]
            s = math.hypot(F[0] - J[0], F[1] - J[1])
            strip = Polygon([(J[0] - 0.30 * t[0], J[1] - 0.30 * t[1]),
                             (J[0] + (s - 0.01) * t[0], J[1] + (s - 0.01) * t[1]),
                             (J[0] + (s - 0.01) * t[0] - 0.12 * n[0], J[1] + (s - 0.01) * t[1] - 0.12 * n[1]),
                             (J[0] - 0.30 * t[0] - 0.12 * n[0], J[1] - 0.30 * t[1] - 0.12 * n[1])])
            strip = strip.difference(c.buffer(BOSS_R - 0.12, resolution=256))
            a0 = math.atan2(J[1] - my, J[0] - mx)
            _T = b.get("E0", b["T"])                 # a chord blend: the ring runs to where the cut leaves the circle
            a1 = math.atan2(_T[1] - my, _T[0] - mx)
            da = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
            a1 = a0 + da * (1.0 - 0.01 / max(abs(da) * BOSS_R, 1e-9))     # stop 0.01 short of T
            arc = [(mx + rr * math.cos(a0 + (a1 - a0) * k / 40.0), my + rr * math.sin(a0 + (a1 - a0) * k / 40.0))
                   for rr, ks in ((BOSS_R, range(41)), (BOSS_R - 0.12, range(40, -1, -1))) for k in ks]
            ring = Polygon(arc)
            for name, z in (("lip", strip), ("boss", ring)):
                if z.difference(cov.buffer(1e-9)).area > 1e-7:
                    raise RuntimeError(f"{at}: its cover leaves {z.difference(cov).area:.5f} mm2 of "
                                       f"the {name}'s edge-break standing open beside the blend")
            # the rules new metal answers to: LIP_CLR off every part at its largest, COIL_CLR off copper
            for ref, poly, _h, _s in (ps if ps is not None else _cached_parts()):
                gap = new.distance(part_envelope(ref, poly))
                if gap < LIP_CLR - 1e-6:
                    raise RuntimeError(f"{at}: {gap:.3f} mm from {ref}, inside LIP_CLR {LIP_CLR}")
            if new.distance(cu) < COIL_CLR - 1e-6:
                raise RuntimeError(f"{at}: {new.distance(cu):.3f} mm from NFC coil copper, inside "
                                   f"COIL_CLR {COIL_CLR}")
            # ...and the ferrite sheet: FER_CLR off it, or -- where the blend was already cut
            # back to the finisher's own radius for it -- at least not IN it
            fgap = new.distance(box(*FER))
            if fgap < (1e-6 if b.get("limit") == FER_REF else FER_CLR - 1e-6):
                raise RuntimeError(f"{at}: R{b['r']:g} stands {fgap:.3f} mm from the ferrite sheet "
                                   f"({FER_REF}) -- titanium where the sheet goes")


def blend_radii():
    """{radius: count} over all blends -- for the sheet, which has to say how many of which."""
    out = {}
    for bl in _blends_cached().values():
        for b in bl:
            out[b["r"]] = out.get(b["r"], 0) + 1
    return out


def blend_gaps():
    """(nearest part, gap), coil gap, ferrite gap over all blends -- MEASURED, for the sheet
    and the docs."""
    cu = unary_union([Point(a).buffer(w / 2.0, resolution=64) if a == b_
                      else LineString([a, b_]).buffer(w / 2.0, resolution=64)
                      for a, b_, w in _coil_cached()])
    best, coil, fer = None, None, None
    for (mx, my), bl in _blends_cached().items():
        for b in bl:
            new = blend_added(mx, my, b)
            for ref, poly, _h, _s in _cached_parts():
                g = new.distance(part_envelope(ref, poly))
                if best is None or g < best[1]:
                    best = (ref, g)
            g = new.distance(cu)
            coil = g if coil is None else min(coil, g)
            g = new.distance(box(*FER))
            fer = g if fer is None else min(fer, g)
    return best, coil, fer


_SEAM = 1e-4               # mm: closes a zero-width seam in a union; far under every tolerance here


def _shell_metal(with_webs, rounds=True, _c={}):
    """`rounds` False is the metal BEFORE the outside corners of the bosses are rounded: what
    the webs and the rounds themselves are laid out on (boss_rounds needs it, and would chase
    its own tail through boss_island otherwise)."""
    if (with_webs, rounds) not in _c:
        m = unary_union([_lip_metal_cached()] + [boss_island(mx, my, rounds) for mx, my in MOUNTS]
                        + [g for mx, my in MOUNTS for g in boss_blend_metal(mx, my)])
        if with_webs:
            m = unary_union([m] + [u for mx, my in MOUNTS for u, _cov in boss_webs(mx, my)])
            # A web's pocket is cut out of the void by the very bore it ends on, so the two
            # meet along a line and the union leaves that line in the outline: a slit of no
            # width, 0.06 to 0.35 mm long, beside each corner boss (found 2026-11-15, walking
            # the outline as straights and arcs). It is not in the solid -- the web's COVER is
            # what is built, and that is buried in the boss -- but every reader of this
            # polygon had it. Closed by a ten-thousandth; nothing else moves.
            m = m.buffer(_SEAM, join_style=2).buffer(-_SEAM, join_style=2)
            # ...and the true R at the foot of each corner boss's flat (boss_roots), which
            # stands on the web and the wall. Held to the recess: a root's cover reaches
            # _BLEND_LIP into the WALL, which is not this polygon's to count (0.24 mm2 a
            # corner, found adding up plan areas against the sectioned shells).
            m = unary_union([m] + [g.intersection(recess_poly()) for g in boss_root_metal()])
        if rounds:
            # off the whole union, not just the islands: a round between a flat and a blend
            # takes a hair of the blend with it
            m = m.difference(unary_union([rd["cut"] for mx, my in MOUNTS for rd in boss_rounds(mx, my)]))
        _c[(with_webs, rounds)] = m
    return _c[(with_webs, rounds)]


def shell_metal_poly():
    """The shell's metal at the board-rest plane AS MODELLED, board coords: the lip, the eight
    boss islands, the blends and the webs. What cavity_as_milled() opens, and so what the
    brace is cut clear of."""
    return _shell_metal(True)


def boss_webs(mx, my):
    """[(P, cover)] -- the pockets of void beside the boss at (mx, my) that lie beyond its own
    bores and keep-outs and that no TOOL_R cutter can reach. They stay metal whatever the
    model says, so the model says so: today that is the slot between each corner boss and the
    recess wall. P is the pocket; `cover` is the polygon the shell CAD extrudes and then cuts
    with THIS BOSS'S OWN bores and keep-outs, so the only faces a web adds are those cylinders
    and planes -- everything else of it is buried in the boss, the lip stub or the wall by
    _WEB_INTO.

    The pocket is outlined by the cutters, not by an opening of the void: its edge on the
    bore side is then the bore's own circle, right down to where that crosses the wall, and
    the web ends there with no skin under the bore (_park_on_wall). Whether it is a web is
    decided by the opening: a piece the finisher reaches is cavity and is left alone (there
    is one beside the boss at y60.27, between its bore and its coil flat). It raises rather
    than return a web the cuts do not bound, one a tool half reaches, or one that ends in a
    feather."""
    return _webs_cached()[(mx, my)]


def _webs_cached(_c={}):
    if "w" not in _c:
        _c["w"] = {m: _boss_webs(*m) for m in MOUNTS}
    return _c["w"]


def _boss_webs(mx, my):
    c = Point(mx, my)
    kps, dbs = boss_cuts(mx, my)
    cdiscs, cslabs = boss_coil_cuts(mx, my)
    cutters = (list(kps) + [Point(q).buffer(TOOL_R, resolution=256) for d in dbs for q in d]
               + [Point(x, y).buffer(r, resolution=256) for x, y, r in cdiscs] + list(cslabs))
    if not cutters:
        return []
    cuts = unary_union(cutters)
    win = c.buffer(BOSS_R + 3.2)
    wallm = box(-5.0, -5.0, W + 5.0, H + 5.0).difference(recess_poly())
    metal = unary_union([_shell_metal(False, rounds=False), wallm]).intersection(win)
    isl = boss_island(mx, my, rounds=False)
    void = win.difference(metal)
    reach = void.buffer(-TOOL_R, join_style=1, resolution=64).buffer(TOOL_R, join_style=1, resolution=64)
    left = void.difference(cuts)
    out = []
    for P in getattr(left, "geoms", [left]):
        if (P.geom_type != "Polygon" or P.area < 5e-3 or P.distance(isl) > 1e-3
                or P.distance(win.exterior) < 0.5):
            continue                                  # dust; not this boss's; or the cavity itself
        at = f"boss at ({mx}, {my}): the web at ({P.centroid.x:.2f}, {P.centroid.y:.2f})"
        got = P.intersection(reach).area
        if got > 0.5 * P.area:
            continue                                  # the finisher reaches it: cavity, not a web
        if got > 2e-3:
            raise RuntimeError(f"{at}: the finisher reaches {got:.4f} of its {P.area:.4f} mm2 -- "
                               f"neither a pocket to leave nor a web to fill")
        hull = P.convex_hull
        cover = hull.union(hull.buffer(_WEB_INTO, join_style=2).intersection(metal)).buffer(0)
        # THE COVER STOPS AT THE BORE THAT ENDS THE WEB. Its reach into the wall runs _WEB_INTO
        # past the web's tip, to the far side of the bore -- and on the open frame the wall has
        # an edge-break there that is none of the web's business. The bore's own break cone
        # clears the cover only within 0.07 mm of the bore's centre line, so beyond that the
        # first build left a plug of fill in the wall's break, 0.07 long, ending in a step.
        # Held to the web's side of each such bore's centre line, the cover ends inside the cone.
        others = metal.difference(isl.buffer(1e-3))
        for d in dbs:
            for q in d:
                cb = Point(q)
                if abs(P.distance(cb) - TOOL_R) > 5e-3:
                    continue                          # this bore does not bound the web
                foot = others.exterior.interpolate(others.exterior.project(cb)) \
                    if others.geom_type == "Polygon" else min(
                        (g.exterior.interpolate(g.exterior.project(cb)) for g in others.geoms
                         if g.geom_type == "Polygon"), key=lambda f: f.distance(cb))
                if foot.distance(cb) > TOOL_R + 0.01:
                    continue                          # not parked against anything
                ux, uy = foot.x - cb.x, foot.y - cb.y
                un = math.hypot(ux, uy)
                wx_, wy_ = -uy / un, ux / un          # along the wall
                if (P.centroid.x - cb.x) * wx_ + (P.centroid.y - cb.y) * wy_ < 0:
                    wx_, wy_ = -wx_, -wy_
                big = 4.0 * (BOSS_R + TOOL_R)
                half = Polygon([(cb.x - big * ux / un, cb.y - big * uy / un),
                                (cb.x + big * ux / un, cb.y + big * uy / un),
                                (cb.x + big * ux / un + big * wx_, cb.y + big * uy / un + big * wy_),
                                (cb.x - big * ux / un + big * wx_, cb.y - big * uy / un + big * wy_)])
                if P.difference(half).area > 1e-9:
                    raise RuntimeError(f"{at} lies on both sides of the bore that ends it")
                cover = cover.intersection(half)
        if cover.geom_type != "Polygon":
            cover = max(cover.geoms, key=lambda g: g.area)
        # OCC cannot build a wire through vertices nanometres apart: drop them. The hull's own
        # edges are straight and survive untouched; whatever moves is inside existing metal.
        cover = Polygon(cover.exterior).simplify(1e-3, preserve_topology=True)
        pts = [cover.exterior.coords[0]]
        for q in list(cover.exterior.coords)[1:-1]:
            if math.hypot(q[0] - pts[-1][0], q[1] - pts[-1][1]) > 2e-3:
                pts.append(q)
        cover = Polygon(pts)
        if cover.distance(c) < BOSS_R - 0.75:
            raise RuntimeError(f"{at}: its cover comes within {cover.distance(c):.2f} mm of the "
                               f"boss axis, where the tapped hole and its spotface are")
        made = cover.difference(cuts).difference(metal)
        if made.symmetric_difference(P).area > 2e-3:
            raise RuntimeError(f"{at} is not bounded by this boss's own bores and keep-outs "
                               f"({made.area:.4f} mm2 built against a pocket of {P.area:.4f}, "
                               f"{made.symmetric_difference(P).area:.4f} apart)")
        thin = made.area - made.buffer(-0.002, join_style=2).buffer(0.002, join_style=2).area
        if thin > 5e-4:
            raise RuntimeError(f"{at} ends in a feather ({thin:.4f} mm2 of it is under 0.004 mm "
                               f"thick): a bore that should close it does not reach its wall")
        out.append((P, cover))
    return out


# ---- A CORNER BOSS MEETS THE SHORT-EDGE WALL THROUGH ONE TRUE RADIUS (2026-11-15, DRH: "yes"
# to the simpler cut) ----------------------------------------------------------------------
# Until now each corner boss's flat stopped 0.25 mm short of the short-edge wall, and three
# things stood in the corner: a Ø2.0 bore parked against the wall (boss_cuts' dogbone), a
# round 0.66 mm long between the bore and the flat, and the web the bore ended. The flat now
# runs to the wall and the corner is one R of the finisher -- a true cylinder, tangent to the
# flat and to the recess wall but for BLEND_BITE, laid out exactly as a tab's root is. Four
# bores and four rounds fewer; the web is still there, and ends on the flat.
#
# WHAT IT COSTS, AND WHAT IT RESTS ON. The bore was there so that the finisher's own radius
# left no metal inside the corner of a MAX-MATERIAL supercap (part_envelope). The plain corner
# does: boss_root_cap_need() -- 0.067 mm at the very corner, 0.005 mm2 in plan, on all four.
# A can at its nominal outline clears the corner by 0.75 mm. DRH took the simpler cut on the
# same ground as the floor fillet (floor_runs): the can is a foil pouch and the outside of its
# outline is the sealed margin, not the body. So the rule is stated the same way -- as how far
# in from its max-material outline the can's BODY must stay for the corner to clear it (0.05
# mm) -- against the same FLOOR_CAP_MARGIN a pouch is TAKEN to give, which is PROVISIONAL
# until a caliper has been put on one (TODO.md). boss_roots() refuses a corner that needs more
# than that, or that comes within BOSS_CLR of the can's nominal outline.
def boss_roots(_c={}):
    """[blend] -- one per corner boss, each a dict as tab_roots() gives them (O, r, F, T, J, t,
    n, cover) plus `boss`, `cap` and `chord` True: a concave blend of TOOL_R between the
    short-edge wall AS CUT and the boss's cap-facing flat. Board coords.

    `chord` because the flat is a cut made after the deburr, like a straight cut across a
    mid-span boss: the shell CAD holds the blend's edge-break to the blend's own side of it.

    It raises rather than return a root whose wall or flat is not the straight face the layout
    assumes, whose new metal is not the fillet a square corner takes, that comes within LIP_CLR
    of a machine-placed part or BOSS_CLR of its supercap's NOMINAL outline, or that needs more
    of the pouch's margin than FLOOR_CAP_MARGIN."""
    if "r" not in _c:
        r, d = TOOL_R, TOOL_R - BLEND_BITE
        _rx0, ry0, _rx1, ry1 = recess_poly().bounds
        wallm = box(-5.0, -5.0, W + 5.0, H + 5.0).difference(recess_poly())
        out = []
        for mx, my in MOUNTS:
            if not _is_corner_boss(mx, my):
                continue
            caps = [(ref, p) for ref, p in _boss_foul_parts(mx, my) if ref in CAP_DATUM]
            if not caps:
                continue                                              # no flat here to run to the wall
            if len(caps) != 1:
                raise RuntimeError(f"boss at ({mx}, {my}): {len(caps)} supercaps foul it -- the "
                                   f"corner rule is written for one flat a corner boss")
            ref, p = caps[0]
            sx = 1.0 if p.centroid.x > mx else -1.0                   # along the wall, away from the boss
            xs = mx + sx * boss_flat_d()
            yw, sy = (ry0, 1.0) if my < H / 2.0 else (ry1, -1.0)      # the wall, and the way the cavity lies
            at = f"the corner boss at ({mx}, {my}): its root at ({xs:.3f}, {yw:g})"
            J = (xs, yw)
            t, n = (sx, 0.0), (0.0, sy)
            F = (xs + d * sx, yw)
            O = (F[0], yw + d * sy)
            T = (xs, O[1])
            metal = unary_union([_lip_metal_cached(), wallm, boss_island(mx, my, rounds=False)]
                                + [u for u, _cov in boss_webs(mx, my)])
            metal = metal.buffer(_SEAM, join_style=2).buffer(-_SEAM, join_style=2)
            # the two faces it joins must be there, straight, as far as it reaches and beyond
            for a, b, what in ((J, (xs + (r + 0.25) * sx, yw), "the short-edge wall"),
                               (J, (xs, yw + (r + 0.25) * sy), "the boss's flat")):
                run = LineString([a, b])
                if run.difference(metal.boundary.buffer(1e-5)).length > 1e-5:
                    raise RuntimeError(f"{at}: {what} is not a straight face of the metal from "
                                       f"({a[0]:.3f}, {a[1]:.3f}) to ({b[0]:.3f}, {b[1]:.3f})")
            cover = Polygon([O, F,
                             (F[0], F[1] - _BLEND_LIP * sy),
                             (xs - _BLEND_LIP * sx, yw - _BLEND_LIP * sy),
                             (xs - _BLEND_LIP * sx, T[1])])
            b = {"O": (round(O[0], 9), round(O[1], 9)), "r": r, "F": F, "T": T, "J": J,
                 "t": t, "n": n, "cover": cover, "limit": None, "twin": False, "chord": True,
                 "boss": (mx, my), "cap": ref}
            new = cover.difference(_blend_disc(b)).difference(metal)
            want = (box(min(xs, xs + r * sx), min(yw, yw + r * sy), max(xs, xs + r * sx), max(yw, yw + r * sy))
                    .difference(Point(xs + r * sx, yw + r * sy).buffer(r, resolution=256)))
            odd = new.symmetric_difference(want).buffer(-_ROUND_TOL / 2.0)
            if not odd.is_empty:
                raise RuntimeError(f"{at}: the blend adds {new.area:.4f} mm2 where a square "
                                   f"corner takes {want.area:.4f}, near "
                                   f"({odd.centroid.x:.3f}, {odd.centroid.y:.3f})")
            for oref, op, _h, src in _cached_parts():
                if oref != ref and src == "model" and part_envelope(oref, op).distance(new) < LIP_CLR - 1e-9:
                    raise RuntimeError(f"{at}: its fillet stands "
                                       f"{part_envelope(oref, op).distance(new):.3f} mm from {oref}, "
                                       f"inside LIP_CLR {LIP_CLR}")
            # ...and its supercap. Measured to the TANGENT fillet (`want`), which is what a shop
            # cutting to the note leaves -- the floor fillet's rule.
            gap = p.distance(want)
            if gap < BOSS_CLR - 1e-9:
                raise RuntimeError(f"{at}: {ref} at its NOMINAL outline stands {gap:.3f} mm from "
                                   f"it, inside BOSS_CLR {BOSS_CLR} -- that is the can, not its margin")
            env = part_envelope(ref, p)
            Ot = (xs + r * sx, yw + r * sy)
            hit = env.intersection(want)
            bite = 0.0 if hit.is_empty else max(
                0.0, max(math.hypot(q[0] - Ot[0], q[1] - Ot[1]) for q in hit.exterior.coords) - r)
            lo_m, hi_m = 0.0, 2.0 * TOOL_R
            if hit.is_empty or hit.area < 1e-12:
                need = 0.0
            else:
                for _ in range(40):                                   # the least inset that clears it
                    mid = (lo_m + hi_m) / 2.0
                    if env.buffer(-mid, join_style=2).intersection(want).area > 1e-12:
                        lo_m = mid
                    else:
                        hi_m = mid
                need = hi_m
            if need > FLOOR_CAP_MARGIN + 1e-9:
                raise RuntimeError(f"{at}: {ref}'s body would have to stay {need:.3f} mm inside "
                                   f"its max-material outline to clear it -- more than the "
                                   f"{FLOOR_CAP_MARGIN} a pouch is TAKEN to give (FLOOR_CAP_MARGIN, provisional)")
            b["area"] = new.area
            b["cap_gap"] = gap                    # the can at nominal, to the tangent fillet
            b["cap_bite"] = bite                  # a square-cornered can at max material, into it
            b["cap_bite_area"] = 0.0 if hit.is_empty else hit.area
            b["cap_need"] = need                  # how far inside its max-material outline the body must stay
            out.append(b)
        _c["r"] = out
    return _c["r"]


def boss_root_metal():
    """[polygon] -- each corner-boss root as plan metal, WITH the part of its cover that lies
    in the wall, the web and the boss, so that a union with those is seamless."""
    return [b["cover"].difference(_blend_disc(b)) for b in boss_roots()]


def boss_root_cap_need():
    """(bite, margin needed) over the four corner-boss roots: how far a square-cornered can at
    MAX MATERIAL stands into a root, and how far inside that outline the can's body must stay
    for every root to clear it. The second is what FLOOR_CAP_MARGIN is held against."""
    rs = boss_roots()
    return (max([b["cap_bite"] for b in rs] or [0.0]), max([b["cap_need"] for b in rs] or [0.0]))


# ---- ...and on the BACK FACE (2026-11-14, the same day, DRH: "give the back face the same
# blends") -------------------------------------------------------------------------------
# The back has the junction too, and it is the side that is seen. Each mount carries a proud
# annulus there (r BOSS_R, as tall as the frame), and the annulus crosses the inner edge of the
# proud frame at a sharp inside corner, 71.6 degrees: two per boss, sixteen in all -- a corner
# boss crosses BOTH frame edges it sits beside. They were left to the back tool's own radius.
# Each is a BLEND_R blend now, laid out exactly as the cavity's are (_blend_at) on the art
# field's own straight edges, which the shell CAD draws from the same two numbers
# (_back_field: the board less EDGE_FIT, less BACK_BORDER).
#
# Three things differ from the cavity side, and only three:
#   * nothing limits a radius here -- no part, no coil, no ferrite: all sixteen are BLEND_R;
#   * the edge-break is the one the back already has. The blends go on BEFORE the deburr, so
#     OCC's chamfer runs round frame, blend and annulus as one outline (no cone to cut);
#   * THE REEDED FIELDS GIVE WAY. Twelve of the sixteen stand in a fin field, and the pour
#     wraps each at FIN_BOSS_CLR as it wraps an annulus (fin_runs), so the ribs beside a boss
#     end a little shorter than they did.
# ---- THE FLOOR MEETS THE WALL THROUGH A RADIUS (2026-11-15, DRH) -----------------------------
# "To aid in a small amount of structural rigidity, to have the floor meet the sides at a curve
# using a ball endmill, so as to again eliminate harsh corners and to give a slight amount of
# support to the thin 1mm floor" -- then "stick with a R1.0", "for any place that has an
# interface between the brace and titanium, that's where we simply don't use a R1.0 ball
# endmill", and, on a prototype of eight straight runs, "apply as you displayed".
#
# WHERE. On each long straight stretch of the cavity's wall whose run no brace comes near (since
# 2026-11-15 "near" is FLOOR_BRACE_CLR from the run's own metal -- see floor_runs(); it was the
# whole stretch): the two stretches of each short-edge wall between a corner boss and the tab, and the
# stretch of each long wall between a corner boss and a mid-span boss -- the walls of the four
# supercap bays, where the floor has no brace over it and (on the max shell) the reeded valleys
# behind it leave it thinnest. Not the middle of either long wall: the brace bears on the east
# one from end to end and on the middle of the west one, and a run is a WHOLE stretch or none,
# so that no run ends in mid-wall. Not round the bosses: their flats are 2.3 to 3.2 mm long.
#
# HOW A RUN ENDS. FLOOR_STOP short of the feature at each end of its stretch (a boss's blend, a
# corner boss's bore, a tab's root), in the scoop a FLAT cutter of the same radius leaves where
# it finishes the sharp corner beyond: a vertical cylinder of TOOL_R, set BLEND_BITE past
# tangent to the wall like every other cylinder here. Two cutters of one radius leave the last
# 0.3 mm of a run as a feather against the wall; that is the part, and the deburr note's.
#
# EVENED, TOP FOR BOTTOM. A run reaches no further along its wall than its twin does -- the
# run that the reflection y -> H - y lays on it (south wall and north wall, station for
# station; each long wall onto itself). Only ever LESS fillet, the contouring pass's rule
# (boss_flat_d: "an evened keep-out is the part's own, united with what evens it"). Seven of
# the eight stretches are twins already, to the 0.01 the cut outline is simplified by. The
# eighth is the run east of each short-edge tab: the two tabs differ by 0.5 mm in width, so
# FLOOR_STOP from each tab's own root put those two runs' west ends at x 28.423 and 28.923.
# Both start at 28.923 now, and the south one stops 1.00 short of its tab's root instead of
# 0.50. WHY IT IS A RULE AND NOT A TIDINESS: as first built (0.50 short at every end), the
# shell's top-for-bottom mirror image differed from the shell by 0.109 mm2 of fillet within
# half a millimetre of SC2 / SC4, and fitted the board exactly as well -- so
# scripts/handedness_drc.py [S] could neither tell the hand by fit nor show that the two were
# the same cavity wherever a part stands, and said so (CI run 663, red; the mesh gates were
# green). The hand there is held by the tabs (assembly_drc [J]); nothing a part can feel may
# differ between a shell and its mirror image unless fit can tell them apart. If the two tabs
# are ever made alike, this rule gives nothing up and the south run goes back to 0.50.
#
# WHAT IT STANDS UNDER. On the two short-edge walls, the edge of a supercap: a can at nominal
# stands 0.95 off that wall, past the fillet's toe, and clears it. A can at MAX MATERIAL
# (part_envelope) stands 0.35 off, where the fillet is 0.24 mm high and the can's underside
# 0.05 to 0.10 above the floor. THAT IS NOT CLEARED, AND IS ACCEPTED (DRH, with a photograph
# of a WS17F): the can is a foil pouch, "rectangular pillows with a general maximum height ...
# the thickness is not even, particularly on the extreme edges", and its outline is the sealed
# margin, not the body. The datasheet does not dimension that margin. So the rule is stated as
# what it needs -- floor_cap_margin_needed(): how far in from its max-material outline a can
# must still be thinner than its stated maximum, 0.33 mm on the max shell -- and held to
# FLOOR_CAP_MARGIN, what a can is TAKEN to give, which is PROVISIONAL until a caliper has been
# put on one (TODO.md). Everything else that hangs over a fillet is held to FLOOR_PART_CLR at
# the cavity's worst case, and a run that cannot give it is refused, not shortened.
FLOOR_R = TOOL_R           # the ball end mill's radius; the flat finisher's too, on purpose
FLOOR_STOP = 0.50          # a run stops this far short of the feature at each end of its stretch
FLOOR_MIN_RUN = 5.0        # a straight stretch shorter than this gets no run
FLOOR_BRACE_CLR = 0.10     # air between a fillet's toe and the foot of a brace
FLOOR_PART_CLR = 0.10      # air between a fillet and a part hanging over it, worst case
CAVITY_TOL = 0.05          # the cavity's depth tolerance (the sheet's C1), for that worst case
FLOOR_CAP_MARGIN = 0.50    # PROVISIONAL: a supercap is TAKEN to reach its full thickness no nearer
                           # its max-material outline than this (its sealed margin). See above.
_FLOOR_ON = 8e-4           # mm: an outline vertex this near a wall's line is on it (the east
                           # wall leans 0.0005 end to end, void_as_cut). A blend leaves the wall
                           # at BLEND_BITE's angle, so a stretch reads under 0.02 mm long


def floor_fillet_h(u, r=None):
    """How high above the floor a fillet of radius r stands at distance u from its wall, as
    it is cut: the cylinder is set BLEND_BITE into wall and floor, so it is a hair lower than
    a tangent one would be. 0 beyond its toe."""
    r = FLOOR_R if r is None else r
    dd = r - BLEND_BITE
    if u >= dd:                                                 # past the axis: the far side of the cylinder
        return 0.0
    return max(0.0, dd - math.sqrt(max(0.0, r * r - (dd - max(u, 0.0)) ** 2)))


def floor_fillet_toe(r=None):
    """How far from its wall a fillet's metal ends on the floor, as modelled: BLEND_BITE makes
    it 0.935 for R1.00, where a tangent fillet's would be 1.00. Everything that has to CLEAR
    a fillet is measured to r, the tangent one -- what a shop cutting to the note leaves."""
    r = FLOOR_R if r is None else r
    dd = r - BLEND_BITE
    return dd - math.sqrt(r * r - dd * dd)


def _floor_walls():
    """[(edge, axis, wall, sg)] -- the cavity's four walls at the floor: which coordinate runs
    ALONG each, where the wall is on the other, and the sign that points into the cavity."""
    x0, y0, x1, y1 = recess_poly().bounds
    return [("S", "x", y0, 1.0), ("N", "x", y1, -1.0),
            ("W", "y", lip_as_cut("W")[0][2] if len(lip_as_cut("W")) == 1 else None, 1.0),
            ("E", "y", W - lip_as_cut("E")[0][2] if len(lip_as_cut("E")) == 1 else None, -1.0)]


def _floor_outline():
    """The cavity as it is at the floor, board coords: the recess less every piece of metal
    the shell stands on it (lip, bosses, blends, webs, tab roots, with the rounds taken off)."""
    wall = box(-5.0, -5.0, W + 5.0, H + 5.0).difference(recess_poly())
    v = box(0.0, 0.0, W, H).difference(unary_union([shell_metal_poly(), wall]))
    return max(getattr(v, "geoms", [v]), key=lambda g: g.area)


def floor_runs(_c={}):
    """[run] -- the floor-to-wall fillets, one dict each, board coords:

        edge, axis   which wall, and the coordinate that runs along it ("x" or "y")
        wall, sg     the wall's own coordinate, and +1 / -1 toward the cavity
        lo, hi       the straight stretch of wall the run stands on, feature to feature
        s0, s1       the run itself: FLOOR_STOP in from each end of its stretch, then evened
                     with its twin top for bottom (never longer); the scoops' axes are at these
        twin         the edge and stretch of the run it was evened with, or None
        r            FLOOR_R
        cover        the plan of the block the fillet is cut from: the run's length, from
                     inside the wall out past the toe
        reach        the plan of the fillet's metal as modelled, to its toe (no scoops)

    The same eight on every floored variant: a stretch a brace comes near on ANY variant gets
    no run on any. Raises if a run would stand in anything but void, under a part it cannot
    clear, or under a supercap's NOMINAL outline."""
    if "r" not in _c:
        r, dd = FLOOR_R, FLOOR_R - BLEND_BITE
        toe = r                                                 # the tangent fillet's: what must be cleared
        void = _floor_outline()
        braces = {vn: unary_union(brace_footprint(span=v["span"]))
                  for vn, v in VARIANTS.items() if v["brace"]}
        floored = {vn: v for vn, v in VARIANTS.items() if v["floor"] > 0}
        out, cands = [], []

        def _P(axis, wall, sg):                                 # station along the wall, distance into the cavity
            return lambda s_, u_: (s_, wall + sg * u_) if axis == "x" else (wall + sg * u_, s_)

        for edge, axis, wall, sg in _floor_walls():
            if wall is None:
                continue                                        # a stepped lip: no single wall to run on
            P = _P(axis, wall, sg)
            span = W if axis == "x" else H
            on = void.exterior.intersection(Polygon([P(0.0, -_FLOOR_ON), P(span, -_FLOOR_ON),
                                                     P(span, _FLOOR_ON), P(0.0, _FLOOR_ON)]))
            segs = [g for g in getattr(on, "geoms", [on]) if g.geom_type == "LineString" and g.length > 1e-6]
            ivs = sorted((min(c[0 if axis == "x" else 1] for c in g.coords),
                          max(c[0 if axis == "x" else 1] for c in g.coords)) for g in segs)
            merged = []
            for lo, hi in ivs:
                if merged and lo <= merged[-1][1] + 1e-6:
                    merged[-1][1] = max(merged[-1][1], hi)
                else:
                    merged.append([lo, hi])
            for lo, hi in merged:
                if hi - lo < FLOOR_MIN_RUN:
                    continue
                # A BRACE NEAR THE RUN, NOT NEAR THE STRETCH (2026-11-15). The test used to be the
                # whole stretch, wall to toe: right while no brace came near a supercap bay's wall
                # at all. The brace's long arm now runs on either side of each short-edge tab
                # (brace_cavity), and its prongs stand over the last 0.2 mm of the four short-edge
                # stretches -- past where each run has ALREADY ended, FLOOR_STOP short of the tab's
                # root, in its scoop. So the question is asked of the run's own metal, scoops
                # taken out: a brace within FLOOR_BRACE_CLR of THAT costs the stretch its run,
                # whole (never a shorter one -- no run ends in mid-wall to make room for resin).
                # Asked before the evening below, on the run as first found: evening only ever
                # shortens a run, and a shorter run's metal lies inside the longer one's.
                s0_, s1_ = lo + FLOOR_STOP, hi - FLOOR_STOP
                first = Polygon([P(s0_, 0.0), P(s1_, 0.0), P(s1_, toe), P(s0_, toe)])
                for ax_ in (P(s0_, dd), P(s1_, dd)):
                    first = first.difference(Point(ax_).buffer(r, resolution=128))
                if any(b.distance(first) < FLOOR_BRACE_CLR - 1e-9 for b in braces.values()):
                    continue                                    # a brace bears here: sharp, the whole stretch
                cands.append({"edge": edge, "axis": axis, "wall": wall, "sg": sg, "lo": lo, "hi": hi,
                              "s0": s0_, "s1": s1_})

        # EVENED, TOP FOR BOTTOM (the block above): each run is cut back to what its twin
        # under y -> H - y also covers. Decided on the runs as first found, so that the order
        # the walls are walked in cannot matter.
        _twin_edge = {"S": "N", "N": "S", "W": "W", "E": "E"}
        _mir = lambda c: ((c["s0"], c["s1"]) if c["axis"] == "x" else (H - c["s1"], H - c["s0"]))
        evened = []
        for c in cands:
            best, lap = None, 0.0
            for t in cands:
                if t["edge"] != _twin_edge[c["edge"]]:
                    continue
                m0, m1 = _mir(t)
                o = min(c["s1"], m1) - max(c["s0"], m0)
                if o > lap:
                    best, lap = (t, m0, m1), o
            s0, s1, twin = c["s0"], c["s1"], None
            if best is not None:
                t, m0, m1 = best
                s0, s1 = max(s0, m0), min(s1, m1)
                twin = (t["edge"], round(t["lo"], 6), round(t["hi"], 6))
            if s1 - s0 < FLOOR_MIN_RUN - 2.0 * FLOOR_STOP - 1e-9:
                raise RuntimeError(
                    f"floor fillet on the {c['edge']} wall, {c['axis']}{c['s0']:.2f}..{c['s1']:.2f}: "
                    f"evened with its twin top for bottom it would be {s1 - s0:.2f} mm long, "
                    f"under the {FLOOR_MIN_RUN - 2.0 * FLOOR_STOP:.2f} a run is allowed to be -- "
                    f"the two walls no longer offer the same stretch; decide which gives way")
            evened.append((c, s0, s1, twin))

        for c, s0, s1, twin in evened:
            edge, axis, wall, sg, lo, hi = (c[k] for k in ("edge", "axis", "wall", "sg", "lo", "hi"))
            P = _P(axis, wall, sg)
            at = f"floor fillet on the {edge} wall, {axis}{s0:.2f}..{s1:.2f}"
            reach = Polygon([P(s0, 0.0), P(s1, 0.0), P(s1, toe), P(s0, toe)])
            stray = reach.difference(void.buffer(_FLOOR_ON))
            if stray.area > 1e-6:
                raise RuntimeError(f"{at}: {stray.area:.4f} mm2 of it would stand in metal, near "
                                   f"({stray.centroid.x:.2f}, {stray.centroid.y:.2f}) -- the wall "
                                   f"is not clear to the fillet's toe along the whole run")
            run = {"edge": edge, "axis": axis, "wall": wall, "sg": sg,
                   "lo": round(lo, 6), "hi": round(hi, 6), "s0": round(s0, 6), "s1": round(s1, 6),
                   "twin": twin, "r": r, "reach": reach,
                   # out to r + 0.03 and no further: the cylinder dips BLEND_BITE under the
                   # floor between 0.935 and 1.061 from the wall and comes up again beyond,
                   # so a cover that reached 1.07 would leave a ridge 0.004 mm high there
                   "cover": Polygon([P(s0, -0.20), P(s1, -0.20), P(s1, r + 0.03), P(s0, r + 0.03)])}
            run["scoops"] = [P(s0, dd), P(s1, dd)]
            run["axis_pts"] = (P(s0, dd), P(s1, dd))
            run["under"] = floor_run_clearances(run, floored)
            for vn, rows in run["under"].items():
                for ref, kind, gap in rows:
                    if kind == "part" and gap < FLOOR_PART_CLR - 1e-9:
                        raise RuntimeError(
                            f"{at}: {ref} hangs {gap:.3f} mm over it on the {vn} shell at the "
                            f"cavity's worst case, inside FLOOR_PART_CLR {FLOOR_PART_CLR}")
                    if kind == "cap nominal" and gap < 0.0:
                        raise RuntimeError(
                            f"{at}: {ref} at its NOMINAL outline stands {-gap:.3f} mm into it "
                            f"on the {vn} shell -- that is not the pouch's margin, it is the can")
                    if kind == "cap margin" and gap < 0.0:
                        raise RuntimeError(
                            f"{at}: {ref} stands {-gap:.3f} mm into it on the {vn} shell even "
                            f"{FLOOR_CAP_MARGIN} mm in from its max-material outline -- more than "
                            f"the margin a pouch is TAKEN to have (FLOOR_CAP_MARGIN, provisional)")
            out.append(run)
        _c["r"] = out
    return _c["r"]


def floor_run_gaps():
    """[(run, gap_lo, gap_hi)] -- how far each end of each floor fillet run stands from where
    the NEXT feature on its wall begins: the foot of the nearest boss blend, tab root or
    corner-boss root on that wall, measured along it from the run's end station (the axis of
    the scoop the run ends in).

    THIS IS THE FIGURE A SHOP CAN MEASURE, and FLOOR_STOP is not (2026-11-16). A run stops
    FLOOR_STOP = 0.50 short of the end of its straight stretch, and the stretch is read off
    the cut outline, which hugs the wall for a little way INTO each blend -- an arc set
    BLEND_BITE past tangent leaves a wall slowly. So the scoop's axis stands 0.39 to 0.43 mm
    from the blend's foot, not 0.50, and the shell sheets said "EACH ENDING 0.50 OR MORE SHORT
    OF THE NEXT BOSS OR TAB" until the second outside review measured it. The sheet prints
    the least of these now. Raises if a run's end has no feature beyond it on its wall."""
    feats = ([b for m in MOUNTS for b in boss_blends(*m)] + list(tab_roots()) + list(boss_roots()))
    out = []
    for run in floor_runs():
        along, across = (0, 1) if run["axis"] == "x" else (1, 0)
        feet = [p[along] for f in feats for p in (f["F"], f["T"]) if abs(p[across] - run["wall"]) < 0.01]
        lo = [run["s0"] - s for s in feet if s < run["s0"]]
        hi = [s - run["s1"] for s in feet if s > run["s1"]]
        if not lo or not hi:
            raise RuntimeError(f"the floor fillet run on the {run['edge']} wall, {run['s0']:.3f}.."
                               f"{run['s1']:.3f}, has no blend or root beyond one end of it")
        out.append((run, min(lo), min(hi)))
    return out


def floor_run_clearances(run, variants=None, ps=None):
    """{variant: [(ref, kind, gap)]} -- what hangs over one run, and by how much it clears the
    fillet with the cavity CAVITY_TOL shallow. kind is "part" (a machine-placed body: the gap
    is air, and must be FLOOR_PART_CLR), "cap nominal" (a supercap at its nominal outline),
    "cap margin" (the same can FLOOR_CAP_MARGIN in from its max-material outline -- what the
    PROVISIONAL rule holds) or "cap max" (at max material, square-edged: negative today, and
    printed so that nobody takes the rule for more than it is). `ps` takes the parts-list
    shape so a check can plant a synthetic part."""
    variants = {vn: v for vn, v in VARIANTS.items() if v["floor"] > 0} if variants is None else variants
    wall_line = (LineString([(run["s0"], run["wall"]), (run["s1"], run["wall"])]) if run["axis"] == "x"
                 else LineString([(run["wall"], run["s0"]), (run["wall"], run["s1"])]))
    out = {}
    for vn, v in variants.items():
        rows = []
        for ref, poly, h, src in (ps if ps is not None else _cached_parts()):
            if src != "model":
                continue
            is_cap = ref in CAP_DATUM
            hh = v["cap_h"] if is_cap else h
            under = v["cavity"] - CAVITY_TOL - hh                 # the body's underside above the floor
            shapes = ([("cap nominal", poly), ("cap margin", part_envelope(ref, poly).buffer(-FLOOR_CAP_MARGIN, join_style=2)),
                       ("cap max", part_envelope(ref, poly))] if is_cap else [("part", poly)])
            if not shapes[-1][1].intersects(run["reach"]):
                continue                                          # nothing of it over this run
            for kind, g in shapes:
                over = g.intersection(run["reach"].buffer(1e-9)) if not g.is_empty else g
                u = over.distance(wall_line) if not over.is_empty else run["r"]
                rows.append((ref, kind, round(under - floor_fillet_h(u, run["r"]), 4)))
        out[vn] = rows
    return out


def floor_cap_margin_needed(_c={}):
    """{variant: mm} -- how far in from its max-material outline a supercap must still be
    thinner than its stated maximum for every fillet to clear it, with the cavity CAVITY_TOL
    shallow: the distance from where the can's outline may stand to where the fillet has come
    down to the can's underside. What the caliper check in TODO.md has to beat."""
    if "m" not in _c:
        out = {}
        for vn, v in VARIANTS.items():
            if v["floor"] <= 0:
                continue
            under = v["cavity"] - CAVITY_TOL - v["cap_h"]
            need = 0.0
            for run in floor_runs():
                wall_line = (LineString([(run["s0"], run["wall"]), (run["s1"], run["wall"])]) if run["axis"] == "x"
                             else LineString([(run["wall"], run["s0"]), (run["wall"], run["s1"])]))
                for ref, poly, _h, src in _cached_parts():
                    if src != "model" or ref not in CAP_DATUM:
                        continue
                    env = part_envelope(ref, poly)
                    if not env.intersects(run["reach"]):
                        continue
                    u0 = env.intersection(run["reach"].buffer(1e-9)).distance(wall_line)
                    lo, hi = 0.0, run["r"]                        # bisect: h(u0 + m) = under
                    for _ in range(60):
                        mid = (lo + hi) / 2.0
                        if floor_fillet_h(u0 + mid, run["r"]) > under:
                            lo = mid
                        else:
                            hi = mid
                    need = max(need, hi)
            out[vn] = round(need, 3)
        _c["m"] = out
    return _c["m"]


def floor_fillet_metal():
    """Every run as plan metal, to its toe -- the scoops at the ends taken out. For the sheet
    and the 2D checks; the shell CAD builds from floor_runs()."""
    out = []
    for run in floor_runs():
        g = run["reach"]
        for c in run["scoops"]:
            g = g.difference(Point(c).buffer(run["r"], resolution=128))
        out.append(g)
    return out


def _back_edges():
    """The art field's four straight edges as runs [(x0, y0, x1, y1)], corners excluded."""
    fx0, fy0, fx1, fy1 = _back_field().bounds
    r = max(BOARD_R + EDGE_FIT - BACK_BORDER, 0.3)
    return [(fx0, fy0 + r, fx0, fy1 - r), (fx1, fy0 + r, fx1, fy1 - r),
            (fx0 + r, fy0, fx1 - r, fy0), (fx0 + r, fy1, fx1 - r, fy1)]


def back_frame_poly():
    """The proud back frame in plan: the recess outline less the art field."""
    return recess_poly().difference(_back_field())


def back_blends(mx, my):
    """[blend] -- the back-face blends of the mount at (mx, my): boss_blends()' dicts, one for
    each place its annulus crosses a straight edge of the art field. Every one is BLEND_R."""
    return _back_blends_cached()[(mx, my)]


def _back_blends_cached(_c={}):
    if "b" not in _c:
        field = _back_field()
        out = {}
        for mx, my in MOUNTS:
            bl = []
            for x0, y0, x1, y1 in _back_edges():
                for J, t, room in _boss_crossings(mx, my, x0, y0, x1, y1):
                    b = _blend_at(mx, my, J, t, _into(field, J, t), BLEND_R, room)
                    if b is None:
                        raise RuntimeError(
                            f"back face: no R{BLEND_R:g} blend fits where the annulus at "
                            f"({mx}, {my}) crosses the frame at ({J[0]:.2f}, {J[1]:.2f}) -- the "
                            f"edge turns into the field's corner before the blend's foot")
                    bl.append(b)
            out[(mx, my)] = bl
        _c["b"] = out
        _audit_back_blends(out)
    return _c["b"]


def back_blend_added(mx, my, b):
    """What ONE back blend adds in plan: its cover outside the blend's circle, the frame and
    the annulus -- the new proud metal, which is what the fin fields have to wrap."""
    g = (b["cover"].difference(_blend_disc(b)).difference(back_frame_poly())
         .difference(Point(mx, my).buffer(BOSS_R, resolution=256)))
    return unary_union([q for q in getattr(g, "geoms", [g]) if q.geom_type == "Polygon" and q.area > 1e-7])


def _audit_back_blends(blends):
    frame = back_frame_poly()
    for (mx, my), bl in blends.items():
        c = Point(mx, my)
        disc = c.buffer(BOSS_R, resolution=256)
        for b in bl:
            at = f"back blend at ({b['J'][0]:.2f}, {b['J'][1]:.2f}) of the mount at ({mx}, {my})"
            new = back_blend_added(mx, my, b)
            if new.is_empty or new.geom_type != "Polygon":
                raise RuntimeError(f"{at}: the cover does not leave ONE piece of new metal")
            stray = (b["cover"].difference(_blend_disc(b)).difference(new)
                     .difference(frame.buffer(1e-6)).difference(disc.buffer(1e-6)))
            if stray.area > 1e-6:
                raise RuntimeError(f"{at}: {stray.area:.5f} mm2 of its cover lies in the open art field")
            if b["cover"].distance(c) < BOSS_R - 0.75:
                raise RuntimeError(f"{at}: its cover comes within {b['cover'].distance(c):.2f} mm of "
                                   f"the hole axis, where the back spotface is")


def back_blend_metal():
    """Every back blend's new metal, one geometry: what fin_runs() keeps the pour off."""
    return unary_union([back_blend_added(mx, my, b) for mx, my in MOUNTS for b in back_blends(mx, my)])


def back_proud_poly():
    """Everything on the back that stands at the frame's height, in plan: the frame, the eight
    annuli and the sixteen blends that join them. One piece, and its inner outline is the edge
    of the recessed art field as it is cut -- what the shell drawing draws there."""
    return unary_union([back_frame_poly(), back_blend_metal()]
                       + [Point(mx, my).buffer(BOSS_R, resolution=256) for mx, my in MOUNTS])


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


_FIN_ARC = 0.0005     # mm: (BOSS_R + FIN_BOSS_CLR) * (1 - cos(90 deg / 48 / 2)) = 0.0004


def fin_runs(rib_w=FIN_RIB_W, _parts=False):
    """Per-field rib centrelines and the pour zone.

    `_parts=True` gives each field as (band, pads, centrelines) -- the band the pour floods
    before the pads are taken out of it, and the pads -- for fin_ribs(), which has to erode
    the one and grow the other (see there). The zone is band - pads either way.

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
    # the pads the pour wraps: each annulus, and since 2026-11-14 the blend that joins it to
    # the frame -- same clearance, so the valley's edge runs round boss and blend as one curve.
    # Every vertex of a blocker becomes a wall face of the valley, and the blend metal's
    # outline is drawn far finer than these circles (it is audited to 1e-4): left as it
    # comes, the sixteen blends put 5,172 more faces on the max shell. _FIN_ARC is the chord
    # the circles themselves give up at resolution 48, so blend and annulus are drawn alike
    # (48 vertices a blend).
    blockers = unary_union([Point(mx, my).buffer(BOSS_R + FIN_BOSS_CLR, resolution=48)
                            for mx, my in MOUNTS]
                           + [back_blend_metal().buffer(FIN_BOSS_CLR, join_style=1, resolution=48)
                                                .simplify(_FIN_ARC)])
    ys = sorted({my for _mx, my in MOUNTS})
    inner_bot, inner_top = ys[1], ys[2]               # 28.5 / 60.4: the mid-boss lines
    runs = []
    for outer, inner, sgn in [(fy0, inner_bot, 1), (fy1, inner_top, -1)]:
        cys = sorted(inner - sgn * (rib_w / 2 + i * pitch) for i in range(n))
        z0, z1 = (outer, inner + sgn * g) if sgn > 0 else (inner + sgn * g, outer)
        band = field.intersection(box(fx0 - 1, z0, fx1 + 1, z1))
        if _parts:
            runs.append((band, blockers, cys))
        else:
            runs.append((band.difference(blockers), cys))
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
    # THE ZONE IS NEVER ERODED AS ONE POLYGON (2026-11-16). It was -- zone.buffer(-d) -- and
    # one rib of the 38 came out 0.584 mm shorter than its three counterparts: the outermost
    # row along the y 2.05 edge, at its east end (found by the second outside review as a
    # difference between the max shell and its own mirror image; `main` at 3440af7). The cause
    # is GEOS, not the layout: buffer() first simplifies its input by a hundredth of the
    # distance, 0.0109 mm here, and a vertex of a pad that happens to stand nearer than that
    # to the field's edge takes the corner where pad and edge meet with it. At that one corner
    # the pad's first vertex stood 0.0103 above the edge (0.0234 at its twin -- the pads are
    # simplified to _FIN_ARC, which is not a symmetric operation), the corner went, the
    # field's whole edge became a line tilted by 0.01 mm in 35, and the eroded boundary rose
    # across the outermost row's centreline -- which stands exactly EPS = 0.01 inside it, by
    # design. A tolerance and the thing it must tell apart, the same size. The other forty rib
    # ends the review found differing, by 0.002 to 0.010 mm, were the same tilt.
    # An erosion of (band - pads) is exactly erosion(band) - dilation(pads), and neither of
    # those has a pad's vertex beside a long straight edge: the band is the field's rounded
    # rectangle cut by a box, and a pad is grown, not shrunk. check_consistency [8] holds the
    # ribs to their own mirror images, both ways.
    d = rib_w / 2 + moat - EPS
    for band, pads, cys in fin_runs(rib_w, _parts=True):
        ero = (band.buffer(-d, join_style=1, resolution=48)
                   .difference(pads.buffer(d, join_style=1, resolution=48)))
        zx0, _zy0, zx1, _zy1 = band.bounds
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


def shell_has_hand(vname):
    """What gives the shell of variant `vname` a HAND -- makes it differ from its own mirror
    image -- or None if nothing does.

    Since 2026-11-15 the inside of every shell is its own mirror image top for bottom (the west
    wall one width, the bosses even, the two short edges cut alike), and so is the outside of a
    shell with no rear art. Such a shell cannot be written, cut or printed in the wrong hand:
    there is no wrong hand. The max shell carries the medallion, whose lettering reads one way
    only. This is the EXPECTATION the gates are held to, not a measurement: handedness_drc [E]
    measures each shell against its own reflection and fails if a shell declared handless has
    grown a hand (say what holds it), or if a shell declared handed has lost the tell;
    assembly_drc [L] reads the rear art itself."""
    return "rear art" if VARIANTS[vname]["medallion"] else None


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
