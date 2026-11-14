#!/usr/bin/env python3
"""
solar-glow-drh-v4_0-backshell-0p6b-brace-cad.py  -  0.6 mm-board DUMB-BOX shell for the resin brace.

Back-only titanium shell for the SOLAR-GLOW DRH PCB. It drops over the populated back and is held by
eight M2 screws (four corner + four panel-corner); the bare show-front (two solar cells + the backlit DRH monogram window) stays
exposed. This is the "dumb box": floor + walls + eight M2 bosses (four corner + four panel-corner) +
no relief pocket, no locator pillars, nothing else. All center support and the window/EMI features live in a separate
dielectric resin brace, so a PCB layout change is a brace reprint, never a shell re-machine.

Z stack (aligned to PCB/solar-glow-drh-v4_0.kicad_pcb, 0.60 mm board; geometry identical to v3):
  floor 1.00  +  cavity 1.80  +  board recess 0.60  =  3.40 field  (3.55 at the 0.15 back frame).
The 0.60 board (vs 0.80) frees 0.20 mm into the floor: 1.00 clears stainless/copper and puts aluminum
past the old titanium-0.75 stiffness, without growing the assembled part. Overall stays 3.55.

Locator pillars: RETIRED (both shipped variants pass locators=False; the H-brace registers by
fitment). The mechanism is kept behind the flag: two Ø3.0 x 0.4 metal pillars on the cavity floor
at board (13,35) and (33,55), engaging Ø3.2 x 0.8 recesses in the brace bottom -- 0.4 engagement,
0.1 radial, ~0.25 axial margin after the brace's ~0.15 bottom-sanding. The floor stays a full
1.00 everywhere either way -- no locating holes, so the back is a uniform engraving surface.

No ribs, no support posts: the resin brace carries center support. The rib/brace machinery is retained
as build() options (ribs=/braces=) for a fallback, but the shipped part uses neither.

The cavity floor is now a TRUE UNIFORM 1.00 mm. U7 used to dip it locally by 0.05 (local floor 0.95),
because U7 was believed to be a 1.75 mm SOIC-8 and so 0.05 taller than the 1.70 caps. The v4 board
carries the 0.90 mm DFN-8 instead: it clears the 1.00 floor by 0.80 and needs no relief, so the pocket
is gone as of 2026-07-28. Watch U7-region flex at bench bring-up -- no rib props it; the fallback if
it matters is a short local rib stub there.

Bench / board-side items (not resolved in CAD):
 - Grounded pillars land on the board back (GND pour with VS mesh + signals). A pillar on GND pour is
   fine (reinforces the tie); on VS or a signal it SHORTS. Nets are name-only in the KiCad-2026 file,
   so guarantee GND-pour-or-bare laminate under each ~Ø3.0 spot board-side.
 - 0.60 board wants a reflow carrier/fixture; bare-board handling is floppier than 0.80.
 - NFC retune: layer-to-layer spacing shrinks 0.80 -> 0.60, nudging the coil tune (brace ferrite + C9).

The 3D STEP governs all geometry; this generator is the source of truth (it prints the full Z-stack and
regenerates the STEP/STL from the PCB anchors).
"""
import os
import sys

import cadquery as cq
from shapely.geometry import Point, box
from shapely.ops import unary_union

# ===== board (committed PCB) =====
W, H, R   = 50.80, 88.90, 3.0
board_th  = 0.60
# THE EIGHT M2 MOUNTS ARE IMPORTED, NOT RE-DECLARED -- see the `MOUNTS as mounts` in the
# fit_rules import further down. `enclosure/fit_rules.py` is their one home, and consistency
# check [16] gates that home against the board's own drills.
#
# This file carried its OWN copy of the list until 2026-08-03, and that copy is what went
# wrong. When the board's mounts were nudged 0.13 mm diagonally to buy the solar cells
# clearance from the screws, the board moved and `fit_rules.MOUNTS` moved with it -- and this
# literal did not. Every boss, tapped hole, back annulus and spotface in the committed
# TITANIUM came out **0.1838 mm** from the drills they have to line up with, against
# **0.100 mm** of radial slack (Ø2.20 board hole on a Ø2.00 screw). The screws bind before
# they seat, eight times over, on the most expensive part in the project.
#
# It survived because check [16] compares fit_rules.MOUNTS against the BOARD and passed green
# the whole time: it had never been told a third copy existed. The brace was fine throughout
# -- it takes its reliefs from `fit_rules.boss_island`, which iterates MOUNTS -- so the brace
# and the shell silently disagreed with each other. Check [16] now refuses any mount list
# declared outside fit_rules, which is why this comment is a comment and not a list.
#
# (The clearance note the old literal carried, kept because it is still live: the W(x,28.63)
# boss r2.6 clears R14 by ~0.34 and U6 by ~0.25 -- TIGHT. A board-side nudge of U6/R14, or a
# local boss trim, buys margin if a fit check ever wants it. The east bosses merge into the
# pinched east lip like the corner bosses.)

# ===== fixed shell knobs =====
# U7 (MB85RC512TY FRAM). 2026-07-28: was 1.75 for a SOIC-8, which the v4 board does not
# carry. It is the DFN-8 -- PCB/solarglow.pretty/U7_DFN8.kicad_mod descr, RAMXEED
# DS501-00087-1v0-E p.21: 5.00 x 6.00 body, 0.90 mm MAX. U7 is NOT the tallest back part
# and never was on v4; the caps are.
#
# Imported, not re-declared: this correction landed here on 2026-07-28 and did NOT reach
# the brace generator's own copy, which kept cutting U7 as a 1.75 mm through-pocket for a
# day. One home now, verified against the part's 3D model by check_consistency [7].
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from part_heights import HEIGHTS as _PART_H, SUPERCAP_H as _CAPH  # noqa: E402
from fit_rules import VARIANTS  # noqa: E402  (single home for per-variant numbers, 2026-08-07)
U7_H       = _PART_H["U7"]         # 0.90
cap_H      = _CAPH                 # WS17 supercaps: the tallest B-side parts (x4) -> set the MAX cavity
kapton_th  = 0.00                  # DROPPED (all contacts on bare laminate). set 0.05 to reinstate.
# The cavity is NOT derived here any more. This file held its own `cap_H + kapton + 0.10`
# formula beside fit_rules' hand-written 1.80 -- two derivations that agreed only
# numerically, the CAVITY-two-homes hazard the 2026-08-07 consumer map named. One home now:
# fit_rules.VARIANTS carries every variant's cavity with its limiter rule spelled out
# (max cap-limited, lite component-limited, air resting-clearance). The 0.10 air over the
# cavity-setting parts lives there as CAP_AIR; the toleranced story (1.80 +-0.05 -> 1.75
# worst-case, minus WS17 1.70 MAX = 0.05 non-contact) is unchanged and lives with it.
cavity     = VARIANTS["max"]["cavity"]   # 1.80 -- module default; per-variant jobs pass their own
# LOCAL RELIEF POCKET -- computed, and as of 2026-07-28 it computes to ZERO, so no pocket is cut.
# The mechanism: if one part stands taller than the cap-limited general cavity, dip the floor locally
# by exactly that excess so it keeps the same air gap, while the GENERAL floor stays thick for
# back-engraving stock. The excess is the ceiling for the trick -- beyond it you would have to pocket
# the caps themselves (17x28.5 mm each, x4 = a second cavity).
#
# It existed for a 1.75 mm SOIC-8 U7, 0.05 taller than the 1.70 caps. The v4 board's U7 is the 0.90 mm
# DFN, which clears the 1.00 mm floor by 0.80 -- so U7_H - cap_H goes negative and the pocket is not
# cut. This is deliberate: the arithmetic removes it, so the mechanism stays here for the next part
# that genuinely needs it rather than being deleted and re-derived from scratch.
U7_POCKET    = max(0.0, round(U7_H - cap_H, 3))   # 0.0 -> no pocket (was 0.05 for the SOIC-8)
U7_POS       = (28.1, 37.3)               # U7 (MB85RC512TY FRAM) origin, board coords (v4 board): re-keyed from the removed U2 balancer, essentially where U2 sat (old (30.10,37.64)). Same SOIC-8_3.9x4.9 package; pad box 6.75 x 4.41 (unchanged footprint), centered here.
U7_POCKET_WH = (7.8, 5.4)                 # pocket size: pad box + ~0.5 margin all round (same SOIC-8, unchanged). At U7_POS the pocket spans y[34.6,40.0] -> N edge ~0.8 clear of the glow window (y40.80); x[24.2,32.0] covers the U7 east pad (~x31.48).

from fit_rules import EDGE_FIT as _EDGE_FIT, BOARD_R as _BOARD_R   # noqa: E402 -- one home
edge_fit   = _EDGE_FIT                # press interference on the FLATS -- a PRESS FIT BY DECISION
                                      # (DRH 2026-11-13; fit_rules.EDGE_FIT carries why)
assert R == _BOARD_R, "board corner radius: fit_rules.BOARD_R is its home" 
corner_clr = 0.15                  # corner relief so the press grips the flats
edge_ease  = 0.10                  # light edge-break on the outer rim + recess mouth (felt, not seen)
lip_break  = 0.10                  # light 45deg edge-break on the inner (cavity-side) lip edge (felt, not seen)
EDGE_BREAK = 0.10                  # Ti deburr: break the sharp END-FACE edges (back proud frame/annuli
                                   # + front rim + recess mouth) so corners are durable, not knife-sharp.
                                   # Ti edges chip and cut; an edge-break also resists nicking. ~0.1 mm.
# ASYMMETRIC support lip (per side) -- wider = more board-edge support = stiffer PCB. Widths bounded
# by the nearest B-side part on each edge (v3.0 board, measured):
from fit_rules import RING as _RING                        # noqa: E402 -- single home; the
                                                           # main fit_rules import sits below
                                                           # the geometry helpers, after these
                                                           # scalars are needed
lip_W, lip_N, lip_S = _RING["W"], _RING["N"], _RING["S"]
lip_E      = _RING["E"]                # E stays narrow through the JP1/TP1 pads (reach x49.6) AND clear of the NFC coil (~x49): lip_E=1.0 -> wall x49.8, east of both. A grounded Ti lip over the coil would detune it.
# The old hand-typed 2.5/2.0/2.0 carried a v3-era justification ("body max edge ~2.35 from
# the board edge... 2.0 clears by ~0.35") that the v4 relayout silently falsified: SC1
# reached y1.75 and the ring CRUSHED three caps and three west-edge passives on every
# committed shell (probed 2026-08-07 on the STL). The widths now live in fit_rules.RING,
# and build() cuts fit_rules.ring_reliefs() out of the ring -- a part-aware relief, sized
# LIP_CLR + TOOL_R, that follows the board. check [8] gates the result.
# The scalar east widening (lip_E_wide / EAST_WIDE_Y) and its outline _lip_void_P() were
# deleted 2026-11-13. They were the last thing in this file that still drew the lip from
# four scalars, and the lip edge-break was cut from them: on the east, where the per-band
# lip is really 1.25 (the coil clamp, fit_rules.COIL_EAST), the 45-degree cutter took the
# top 0.10 off its inner 0.25 and the board rested on 0.85 mm of east lip, not 1.25 --
# measured on SolidCraft and here, TODO.md C1/B8. The break now follows the void the shell
# is actually cut to (_lip_break_cut below).
lip_w      = lip_E                      # legacy min-lip alias (only the dormant tool_relief helper still reads it)
back_border = 2.0                      # SYMMETRIC proud back-frame border, equal on all 4 sides (decoupled from the asymmetric front lip). Front lip stays asymmetric (it clears B-side parts); this is the cosmetic exterior back border only.
boss_r     = 2.60                  # M2 boss / back annulus outer radius
pilot_r    = 0.80                  # M2 tap-drill hole, CLEAN THROUGH. Boss is TAPPED M2 (brass is soft --
                                   # never let a brass screw thread-form into Ti; cut the threads first).
# corner fasteners: brass M2x3, pan head <= Ø4.0 (cell-limited; absolute Ø5.3 touches the cell at 2.66 mm).
SCREW_LEN  = VARIANTS["max"]["screw_len"]   # bare-build() fallback = the max variant; jobs pass per-variant (was a literal 3.0 -- second-home class)
CBORE_D    = 3.0                   # back spotface dia at each hole; depth auto-set so the M2x3 tip is flush.

# glow-window reflector registration frame (on the cavity FLOOR): a LASER-MARKED outline showing where
# the Al reflector strip is placed -- behind the monogram window, facing the reverse-mount LEDs -- so
# stray back-emission bounces forward through the FR4 letters and lifts the glow. Marked, NOT cut: the
# floor stays a full 1.00 mm under the frame (the only relief is the 0.05 U7 pocket, well clear of it).
# GLOW_WIN is the monogram footprint from the committed PCB.
GLOW_WIN   = (14.95, 40.8, 35.85, 47.0)   # board coords (x0,y0,x1,y1); 20.9 x 6.2 mm, centered (25.4,43.9)
MARK_W     = 0.25                  # frame outline width (in-plane), hairline -- laser-marked, no material removed
MARK_DEPTH = 0.00                  # 0 = laser mark (no cut). >0 would engrave a groove (thins the floor); kept off.
# ---- rear MEDALLION (replaced the two-line maker's mark, 2026-07-31): the Z9F coin from the
# engraving studies. A sunken disc in the clear band; ring text, rim, hoop, monogram and serial
# stand as stock-plane ISLANDS on the same +0.15 bearing plane as the frame, so the whole part
# laps face-down on a plate (frame + crests take the film; nothing else can be touched). All
# geometry, the four agnostic parameters (RING_TEXT / RING_ANCHOR / DIAL_MONOGRAM / SERIAL) and
# the machining contract (min-island audit, tool cascade) live in medallion.py -- it ASSERTS at
# build time, so an unmachinable parameter refuses to generate. Decision trail with every number:
# enclosure/engraving-studies/ (culled 2026-08-02; git history). ----
# The exact glyph outlines end up cut into the titanium, so the font is part of the deliverable,
# not a styling choice -- it is vendored in enclosure/fonts/ (JetBrains Mono, SIL OFL 1.1,
# license bundled alongside as the OFL requires). These paths used to point at /home/claude/fonts/,
# which exists on nobody's checkout, so the generator could not regenerate its own STEP. Set
# MAKER_FONT_DIR to override.
_FONT_DIR = os.environ.get("MAKER_FONT_DIR") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
MAKER_FONT_R = os.path.join(_FONT_DIR, "JetBrainsMono-Regular.ttf")
MAKER_FONT_B = os.path.join(_FONT_DIR, "JetBrainsMono-Bold.ttf")
for _f in (MAKER_FONT_R, MAKER_FONT_B):
    if not os.path.exists(_f):
        raise SystemExit(f"maker font missing: {_f}\n"
                         "  the engraved text is part of the machined part, so this is not "
                         "substitutable -- set MAKER_FONT_DIR to a directory holding JetBrains Mono.")

# round-tool relief: a spinning end mill cannot cut a sharp INTERNAL (concave) corner -- it always
# leaves its own radius. Convex features (the bosses, brace posts, rib ends) are fine; the tool just
# rides around them. The only un-machinable spots are the concave junctions where the bosses and the
# ribs merge into the lip. We RADIUS those corners to the finishing-tool radius so the pocket clears
# in single passes -- i.e. we draw the corner the tool actually leaves, so nothing in the model is
# smaller than the cutter. R1.0 = Ø2.0 mm finisher; the cavity inner corners (ir=1.45) already clear
# it. Shop roughs the open pocket with a Ø3-4 mm tool and finishes corners/walls with the Ø2.0.
TOOL_R     = 1.00
# the BACK field is only 0.15 mm deep, so it gets finished with a smaller cutter than the 1.90 mm
# cavity. A finer tool radius tightens the (cosmetic) annulus-frame junction relief on the art face.
# R0.5 = Ø1.0 mm finisher. (Drop to 0.25 for a Ø0.5 cutter if crisper corners are wanted.)
BACK_TOOL_R = 0.50

# window braces (disk clears the glow window + every back pad; from the PCB):
# window braces: E + W flanked the optical-window keepout (between side lip and window edge).
# NE(35,37) + SW(19.2,50.9) were REDUNDANT once the ribs went in -> removed. Then E+W removed too
# (braces=False default): U7 + caps are held by the ribs+lip (U7's support is the rib end, unchanged);
# the braces only propped the window / bare-laminate spans. Removing frees board (13.6,40.1)/(39.5,40.0).
BRACE = [(39.5,40.0,1.0),(13.6,40.1,1.0)]   # E, W posts -- retained as defs; re-enable via build(braces=True)
# 4 window-support pillars: RETIRED (the PCB net audit rejected 3 of 4 spots; the resin brace carries
# center support now). Kept as an empty list so build(pillars=True) is a no-op and no stale coords mislead.
PILLARS = []
# cap-gap stiffening ribs: 1.0 mm wide in the SC1|SC2 / SC3|SC4 corridors (gap x24.0-26.8), giving
# 0.9 mm clearance EACH SIDE to the nominal cap edges (hand-placement tolerance; was 0.6). Run into
# the perimeter lip top+bottom so each rib is a SPUR off the lip (continuous pocket boundary, not a
# free-standing island) -> one roughing + boundary finish, no island plunging, and the lip tie
# stiffens the narrower wall so the span is unchanged. (Drop width to 0.8 for 1.0 mm/side if needed.)
RIBS  = [(24.9, 0.0, 25.9, 33.0), (24.9, 56.0, 25.9, 88.9)]   # (x0,y0,x1,y1)  1.0 wide, lip-tied

wx = lambda x: x - W/2
wy = lambda y: y - H/2
cavW, cavH, cavR = W + 2*edge_fit, H + 2*edge_fit, R + edge_fit
IR = max(cavR - lip_E, 0.5)            # cavity inner-corner radius (>= tool R); tied to the min lip so it clears the Ø2.0 finisher
# ---- asymmetric cavity: per-side lips + east-END wide-lip blocks. Round-tool-friendly: every concave
# junction (block-to-wall, boss-to-wall) is left SHARP so the STEP stays analytic and the finisher just
# leaves its own radius there (nothing mates in those corners); no acute pockets, no step-down tooling. ----
def _cav_inner(z0, dz, grow=0.0):
    """asymmetric inner cavity void (per-side lips), corners filleted to IR. `grow` moves
    every inner face outward by that much -- the ring cut passes RING_FUSE_EPS so the BUILT
    ring is a hair slimmer than fit_rules.RING: the W/N/S ring faces otherwise land exactly
    on the plane where full-reach lip bands end (both derive from the same width), and once
    ring reliefs segment the ring, OCC's fuse leaves an open seam along the split coincident
    plane -- measured 2026-08-07 as a 27.69 mm boundary edge at x2.500/z1.000. Slimmer-than-
    model is the safe direction: check [8] asserts part clearance against the WIDER model."""
    cx, cy = wx((lip_W + W - lip_E)/2.0), wy((lip_N + H - lip_S)/2.0)
    return (cq.Workplane("XY").workplane(offset=z0).center(cx, cy)
              .rect(W - lip_E - lip_W + 2*grow, H - lip_S - lip_N + 2*grow)
              .extrude(dz).edges("|Z").fillet(IR))


RING_FUSE_EPS = 0.01
def _lip_break_cut(bb, c, taper):
    """45deg edge-break on the lip inner top edge: taper-extrude the void outline over the top c mm so it
    grows outward into the lip, and cut it -> the sharp top-inner lip edge is knocked back at 45deg.

    The outline is the void the shell is CUT to (_void_in_recess), not a scalar stand-in for it, so
    every lip edge gets the break and no edge loses bearing to it.

    Two things keep it a clean cut. Where the void already reaches the recess wall (beside the
    supercaps, where there is no lip) there is no lip edge to break, and a frustum grown there
    would undercut the wall the board presses into -- so the outline is first held c + 0.02 inside
    the recess. And the frustum starts _BREAK_DIP BELOW the break, shrunk by the same, so its
    drafted faces CROSS the void's vertical walls at 45 degrees instead of lying on them: built on
    the wall outline itself (first cut, 2026-11-13) the boolean left 45 zero-length seams round the
    max shell at z seat - 0.10, and check_mesh refused them."""
    v = _void_in_recess().intersection(_recess_fp().buffer(-(c + 0.02), join_style=2))
    return _frustum(v.buffer(-_BREAK_DIP, join_style=2), bb - c - _BREAK_DIP, c + _BREAK_DIP + 0.01, taper)

_BREAK_DIP = 0.05        # how far an edge-break frustum starts inside the void (see _lip_break_cut)

def _frustum(poly, z0, h, taper):
    """Taper-extrude every polygon in `poly` (board coords) from z0 by h; union of the pieces."""
    out = None
    for g in (poly.geoms if poly.geom_type == "MultiPolygon" else [poly]):
        if g.is_empty or g.area < 1e-4:
            continue
        # 0.02 off the exact outline at most, on a 0.10 break: without it the near-tangent run where
        # a band-step fillet meets its wall left two zero-length seams per frustum; with it, one
        g = g.simplify(0.02, preserve_topology=True)
        xy = [(wx(x), wy(y)) for x, y in list(g.exterior.coords)[:-1]]
        f = cq.Workplane("XY").workplane(offset=z0).polyline(xy).close().extrude(h, taper=taper)
        out = f if out is None else out.union(f)
    return out

def _resting_face_break(c):
    """OPEN FRAME ONLY: the c x 45deg break on the cavity wall's edge at the resting face (z = 0),
    cut by boolean like the lip break -- and, like it, BEFORE the bosses are unioned, so it never
    touches them (each boss cylinder carries its own foot chamfer, and each spotface mouth its own
    cone, _spotface_mouth_break).

    This was faces('<Z').edges().chamfer() until 2026-11-13, when the lip bands began stepping a
    tool radius past every part (fit_rules._lip_limits): the new outline put OCC's chamfer into
    StdFail_NotDone on the whole face, with no single region to blame (excluding any one stretch of
    the west wall still failed; excluding all of it passed) -- the OCC limit _recess_mouth_ease and
    _lip_break_cut already route round. The outer edge is not in here: edge_ease broke it when the
    block was made, and breaking it again is the double break the rim top had (SolidCraft B5).
    The frustum is _lip_break_cut's own, on the same void outline, mirrored to grow DOWNWARD; a
    taper on a re-offset outline was tried first and OCC's offset-wire builder refused it."""
    # built growing UP from the void shrunk by _BREAK_DIP (so it crosses the wall, as the lip break
    # does), then mirrored to grow DOWN: the shrunk outline lands at z = c + dip, the void's own
    # outline at z = c, the break at c out from the wall at z = 0, and c + 0.02 at z = -0.02.
    v = _void_in_recess()
    h = c + _BREAK_DIP + 0.02
    up = _frustum(v.buffer(-_BREAK_DIP, join_style=2), 0.0, h, -45)
    return up.mirror("XY", basePointVector=(0, 0, 0)).translate((0, 0, c + _BREAK_DIP))

def _spotface_mouth_break(c):
    """OPEN FRAME ONLY: a true 45deg cone at each spotface mouth on the resting face."""
    tool = None
    for mx, my in mounts:
        cone = (cq.Workplane("XY").workplane(offset=-0.02).moveTo(wx(mx), wy(my))
                  .circle(CBORE_D / 2 + c + 0.02).extrude(c + 0.02, taper=45))
        tool = cone if tool is None else tool.union(cone)
    return tool

def _recess_mouth_ease(wt, c):
    """45deg ease on the recess-mouth top-inner edge, around the board opening. Filleted (cavR) rounded-rect
    frustum so the ease FOLLOWS the rounded recess corners instead of cutting a straight diagonal across
    them. At wt-c it is the nominal recess (interior already void -> no-op); at wt it grows outward by c into
    the wall, beveling only the wall inner-top corner. Robust boolean (no OCC edge-chamfer)."""
    sk = cq.Sketch().rect(cavW, cavH).vertices().fillet(cavR)
    for mx, my in [(R, R), (W - R, R), (R, H - R), (W - R, H - R)]:   # ONLY the 4 board CORNERS carry the corner_clr relief (same set build() cuts). The 4 panel-corner mounts sit mid-edge; stamping a circle there bulged the recess-mouth outline into a semicircle -> the "semi-moon" crescents on the top lip. They get no relief circle.
        sk = sk.push([(wx(mx), wy(my))]).circle(R + corner_clr, mode="a")   # ACTUAL opening (relief r=R+corner_clr at the corners), not the cavR fillet the relief cuts through
    return cq.Workplane("XY").workplane(offset=wt-c).placeSketch(sk).extrude(c, taper=-45)

# ---- round-tool corner relief (pure-2D, matches the CAD cavity cut exactly) ----
# ---------------------------------------------------------------------------------------
# THE SUPPORT LIP IS COMPUTED PER BAND FROM THE BOARD, NOT FOUR SCALARS.
#
# It used to be lip_W/N/S/E = 2.5/2.0/2.0/1.0 with one hand-written east widening. Measured
# against the committed board that lip lands on NINE B-side parts -- and the board sets
# pad_to_mask_clearance = 0, so those pads are bare copper and this lip is grounded
# titanium. 4.17 mm2 of LIVE pad sits under it (U6 VS + NFC_EN, C27 STO, FB1 STO/STO_LDO,
# C22 STO_LDO, R15 STO). Fitting the shell shorts the storage rail to ground.
#
# So derive the width. For each span of each edge, take the nearest part body-or-pad and
# back off LIP_CLR. Everywhere no part intrudes, the lip stays at its structural maximum --
# the point is to keep the lip WIDE (it supports a 0.60 mm board) and pinch it only where
# something is actually in the way.
#
# The east edge gains the most: it was pinched to a flat 1.0 for parts that have since
# moved, and the real constraint there is the NFC coil (east copper ~x48.40), which a
# grounded lip must never overhang or it detunes the antenna. That allows 2.40 over most
# of the edge instead of 1.00.
# ---------------------------------------------------------------------------------------
# The lip bands, the cavity void and the boss scallops are all computed in
# enclosure/fit_rules.py -- ONE home, shared with the brace generator and asserted by
# check_consistency [8]. See that module for why they are not four scalars any more.
from fit_rules import (lip_bands, cavity_void_poly as _cavity_void_poly,
                       boss_island as _boss_island, boss_fouls as _boss_fouls,
                       LIP_CLR, LIP_MAX, COIL_EAST,
                       ring_reliefs as _ring_reliefs,
                       BOSS_CLR, THREAD_KEEP, export_solid,
                       boss_cuts as _boss_cuts, boss_coil_cuts as _boss_coil_cuts,
                       recess_poly as _recess_poly, TOOL_R as _TOOL_R,
                       fin_region as _fin_region, fin_ribs as _fin_ribs,
                       FIN_PROUD, FIN_VALLEY,
                       MOUNTS as mounts)                                      # noqa: E402

def _inner_pocket():
    """pocket-interior (void) footprint in BOARD coords, identical to the CAD cavity cut:
    centered iw x ih rect inset by lip_w, corner radius ir."""
    iw, ih, ir = cavW - 2*lip_w, cavH - 2*lip_w, max(cavR - lip_w, 0.5)
    x0, y0, x1, y1 = W/2 - iw/2, H/2 - ih/2, W/2 + iw/2, H/2 + ih/2
    b = box(x0+ir, y0, x1-ir, y1).union(box(x0, y0+ir, x1, y1-ir))
    for cx, cy in [(x0+ir,y0+ir),(x1-ir,y0+ir),(x0+ir,y1-ir),(x1-ir,y1-ir)]:
        b = b.union(Point(cx, cy).buffer(ir, resolution=48))
    return b

def _relief_for(islands, tool_r=TOOL_R):
    """material a round tool of radius tool_r CANNOT clear in a pocket around `islands` =
    void - open(void). These are the concave island-to-wall junction fills (board coords)."""
    void  = _inner_pocket().difference(unary_union(islands))
    vopen = void.buffer(-tool_r, join_style=1, resolution=32).buffer(tool_r, join_style=1, resolution=32)
    added = void.difference(vopen).buffer(0)
    geoms = list(added.geoms) if added.geom_type.startswith("Multi") else ([added] if not added.is_empty else [])
    return [g.simplify(0.01, preserve_topology=True) for g in geoms if g.geom_type == "Polygon" and g.area > 0.01]

def _cavity_islands(ribs_on, braces_on=False):
    """interior pocket islands: bosses (+ optional brace posts) (+ cap-gap ribs)."""
    isl  = [_boss_island(mx, my) for mx, my in mounts]
    if braces_on:
        isl += [Point(x, y).buffer(rr, resolution=48) for x, y, rr in BRACE]
    if ribs_on:
        isl += [box(x0, y0, x1, y1) for x0, y0, x1, y1 in RIBS]
    return isl

def _back_islands():
    """back recessed-field islands: just the 4 raised boss annuli (no ribs/braces on the back)."""
    return [Point(mx, my).buffer(boss_r, resolution=64) for mx, my in mounts]

def _poly_solid(poly, z0, dz):
    """extrude a simple shapely polygon (board coords) into a CadQuery prism, z0 .. z0+dz."""
    xy = [(wx(x), wy(y)) for x, y in list(poly.exterior.coords)[:-1]]
    return cq.Workplane("XY").workplane(offset=z0).polyline(xy).close().extrude(dz)

def _recess_fp():
    """The board recess in plan, board coords -- fit_rules.recess_poly(), the one statement of it."""
    return _recess_poly()

def _void_in_recess():
    """fit_rules' cavity void, held inside the board recess. edge_fit is NEGATIVE (a press fit),
    so the recess is 0.05 mm smaller than the board on every flat and a void that runs out to
    the board edge would still be cut 0.05 mm under the recess wall. Clipping to the recess
    footprint (same rounded rectangle build() cuts at the seat) means the floor-to-seat cut can
    never pass beneath the wall above it."""
    v = _cavity_void_poly().intersection(_recess_fp())
    if v.geom_type != "Polygon":                 # a clip can shed dust; the void is the big piece
        v = max((g for g in v.geoms if g.geom_type == "Polygon"), key=lambda g: g.area)
    return v

def _axis_piece(wp, x, y, z):
    """Of the solids a scallop cut can leave, keep the one the boss axis runs through --
    the rule fit_rules.boss_island() applies to its polygon (a crumb the cut detaches is
    not a boss). A cut that leaves one solid, the normal case, is returned untouched."""
    sols = wp.solids().vals()
    if len(sols) <= 1:
        return wp
    pt = cq.Vector(wx(x), wy(y), z)
    keep = [s for s in sols if s.isInside(pt)] or sols[:1]
    return cq.Workplane("XY").newObject(keep[:1])

_SCALLOP_FAT = 0.02      # the scallop tool is cut from a cylinder this much fatter than the
                         # boss, and taller wherever there is only air to be taller into, so
                         # no face of the tool lies ON a curved face of the boss

def _boss_scallop_tool(x, y, floor, cavity, foot=0.0):
    """What has to come OUT of the boss at (x, y) for it to be fit_rules.boss_island():
    its keep-outs, plus any crumb they detach from the piece the axis runs through.
    None if nothing fouls this boss.

    Built on a lone cylinder and cut from the finished shell, not from the boss before it is
    unioned -- which is where the first draft of this put it, and what the first generator
    run rejected. OCC's chamfer cannot break the edges of an end face once a boss on that
    face carries a flat: lip + full cylinder chamfers, lip + flatted cylinder is
    StdFail_NotDone in every construction order tried, down to a ten-line reproduction. On
    max and lite that never shows, because their bosses stand on the cavity floor. On the
    open frame the boss foot IS the resting face, the deburr pass below is all-or-nothing
    per face, and it quietly dropped the edge-break from the whole face.

    So the deburr runs first, on the full-round bosses it has always handled, and the
    keep-outs come out afterwards by boolean -- the same answer _lip_break_cut and
    _recess_mouth_ease already give to the same OCC limit. `foot` > 0 (open frame only)
    grows each keep-out by that much at the resting face and tapers it back at 45 degrees,
    so the new flat gets the break every other edge of that face has.

    Every cut face is a plane or a true cylinder: square-cornered part outlines against the
    original cylinder, and an R = TOOL_R bore for each dogbone (fit_rules.boss_cuts -- where the
    Ø2.0 finisher has to go to reach a keep-out corner), nothing faceted for a CAM seat to choke on.

    THE COIL'S KEEP-OUT COMES OUT THE SAME WAY (2026-11-14, fit_rules.boss_coil_cuts): the
    straight band beside a track is one more plane-sided polygon, and the round end about a
    track's corner is one more bore -- of its own radius, the clearance plus half the track,
    which is why a bore here is (x, y, r) and not a centre with TOOL_R understood."""
    kps, dbs = _boss_cuts(x, y)
    coil_discs, coil_slabs = _boss_coil_cuts(x, y)
    fouls = [g for kp in list(kps) + coil_slabs
             for g in (kp.geoms if kp.geom_type == "MultiPolygon" else [kp])]
    bores = [(cx, cy, _TOOL_R) for d in dbs for cx, cy in d] + list(coil_discs)
    if not fouls and not bores:
        return None
    # Upward the tool overshoots into the board recess, which is air. Downward it may only
    # overshoot on the open frame: anywhere else `floor` is the cavity FLOOR, and a tool that
    # started below it would mill a 0.02 mm pocket into the floor under every scallop (it
    # did, on the first build of this -- 0.18 mm3 the lite shell had no reason to lose).
    z0 = floor - (_SCALLOP_FAT if floor == 0 else 0.0)
    dz = floor + cavity + _SCALLOP_FAT - z0
    fat = (cq.Workplane("XY").workplane(offset=z0).moveTo(wx(x), wy(y))
             .circle(boss_r + _SCALLOP_FAT).extrude(dz))
    island = fat
    for g in fouls:
        island = island.cut(_poly_solid(g, z0 - 0.01, dz + 0.02))
    for cx, cy, br in bores:
        island = island.cut(cq.Workplane("XY").workplane(offset=z0 - 0.01)
                              .moveTo(wx(cx), wy(cy)).circle(br).extrude(dz + 0.02))
    island = _axis_piece(island, x, y, floor + cavity / 2)
    tool = fat.cut(island)
    if foot > 0:
        for g in fouls:
            grown = g.buffer(foot, join_style=2)
            xy = [(wx(px), wy(py)) for px, py in list(grown.exterior.coords)[:-1]]
            wedge = (cq.Workplane("XY").workplane(offset=floor).polyline(xy).close()
                       .extrude(foot, taper=45))
            wedge = wedge.union(_poly_solid(grown, z0, floor - z0))    # ...and on down past the face
            tool = tool.union(wedge.intersect(fat))
        for cx, cy, br in bores:
            cone = (cq.Workplane("XY").workplane(offset=floor).moveTo(wx(cx), wy(cy))
                      .circle(br + foot).extrude(foot, taper=45))
            cone = cone.union(cq.Workplane("XY").workplane(offset=z0).moveTo(wx(cx), wy(cy))
                                .circle(br + foot).extrude(floor - z0))
            tool = tool.union(cone.intersect(fat))
    return tool

def _maker_text(txt, lx, cy, capH, fontpath):
    """Readable all-caps engraving text: LEFT edge at x=lx, vertically centered at y=cy, cap height ~capH.
    Returns shapely geometry in BOARD coords (pre-mirror)."""
    # Outlines come from scripts/glyphs.py, which fills by the NONZERO WINDING rule a font
    # is drawn to. This used to fold the contours with reduce(symmetric_difference), and
    # that is wrong for exactly one glyph in everything these generators set: '8'.
    # JetBrains Mono draws it as two closed, SELF-INTERSECTING loops, one per bowl;
    # buffer(0) floods each and the XOR eats the overlap at the waist, so the eight came
    # back as two solid lumps with no counters -- +56.9 % ink in Regular, +28.8 % in Bold.
    # A survey of 89 glyphs found no other character affected in either weight.
    #
    # THE RING TEXT NEVER CONTAINED ONE. The dial does: DIAL is [monogram, "No <SERIAL>"],
    # and SERIAL is variable data, one substitution per unit. Serial 008 would have been
    # the first blob engraved into titanium, and nothing here would have caught it -- the
    # mesh gate checks that the solid is watertight, not that the digits are digits.
    # (Found 2026-08-03 from the same bug in scripts/face_art.py, which set the card face's
    # phone number and rendered the 8 in "404-213-8076" as a blob in its first preview.)
    import shapely.affinity as _aff
    import sys as _sys, os as _os
    _sys.path.insert(0, _os.path.join(
        _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "scripts"))
    from glyphs import outline as _outline
    geom = _outline(txt, fontpath)
    if geom is None or geom.is_empty: return None
    mnx,mny,mxx,mxy=geom.bounds; sc=capH/(mxy-mny)
    geom=_aff.scale(geom,xfact=sc,yfact=sc,origin=(mnx,mny)); mnx,mny,mxx,mxy=geom.bounds
    return _aff.translate(geom, lx-mnx, cy-(mny+mxy)/2)

# ===== build =====
_LIPSUM = {e: len(lip_bands(e)) for e in ('W', 'E', 'S', 'N')}
# Edge-break groups build() had to skip. The try/except around the deburr exists so that an
# EXPERIMENT (ribs, pillars, a relief flag) still returns a solid, and for a shipped variant
# it was a way to lose geometry without anyone knowing: one line in a build log, and a frame
# whose drawing goes on calling its edge-breaks MODELED. It happened once -- the open frame,
# the first time its bosses were scalloped -- and no gate could have seen it: the missing
# chamfers are 2.9 mm3 of a 997 mm3 part, 0.29 %, inside check_mesh's 0.5 % volume tolerance.
# build() still only records the skip; the jobs loop below makes it fatal for what ships.
_DEBURR_SKIPS = []


def build(floor=1.00, wall_th=1.0, border_h=0.15, ribs=False, braces=False, pillars=False, locators=False, prog_window=False, glow_marker=True, maker_mark=True, tool_relief=False, fins=True, cavity=cavity, screw_len=None):
    # `cavity` and `screw_len` are per-variant since 2026-08-07 -- passed EXPLICITLY from
    # fit_rules.VARIANTS by the jobs loop, never smuggled through module state. The
    # defaults are the max variant, so a bare build() means what it always meant.
    if screw_len is None:
        screw_len = SCREW_LEN
    # Floor-stock guards (physics, not policy): the fin valleys are FIN_VALLEY deep and
    # the medallion floors ~0.55-0.75 -- a thinned floor cannot take either. These were
    # unguarded until 2026-08-07; a lite row with the old defaults would have shipped a
    # sieve that was still watertight enough to pass every mesh gate.
    if fins and border_h > 0:
        assert floor - FIN_VALLEY >= 0.40 - 1e-9, \
            f"fins need floor >= {FIN_VALLEY + 0.40:.2f} (valley {FIN_VALLEY} + 0.40 web); got {floor}"
    if maker_mark and border_h > 0:
        assert floor >= 1.00 - 1e-9, f"medallion needs the full 1.00 floor; got {floor}"
    if floor == 0:
        assert border_h == 0 and not fins and not maker_mark and not glow_marker, \
            "open frame (floor 0) has no back face: border/fins/medallion/glow marker must be off"
        assert (floor + cavity + board_th) - screw_len >= 0.15 - 1e-9, \
            f"M2x{screw_len} tip would pass the open frame's resting plane"
    bb = floor + cavity                       # board-back / boss-top / lip-top / rib-top plane
    wt = bb + board_th
    outW, outH, outR = cavW + 2*wall_th, cavH + 2*wall_th, cavR + wall_th
    ir = IR

    res = cq.Workplane("XY").rect(outW, outH).extrude(wt).edges("|Z").fillet(outR)
    if edge_ease > 0:
        res = res.edges(">Z").chamfer(edge_ease).edges("<Z").chamfer(edge_ease)
    # board recess (press fit) + uniform cavity (inset by lip_w)
    res = res.cut(cq.Workplane("XY").workplane(offset=bb).rect(cavW, cavH)
                    .extrude(board_th + 0.02).edges("|Z").fillet(cavR))
    if edge_ease > 0:                                   # ease the recess mouth to match the outer rim (board lead-in)
        res = res.cut(_recess_mouth_ease(wt, edge_ease))
    # At floor 0 (the open air frame) the void cut must start BELOW z0, or the cut face is
    # coincident with the block bottom and OCC's boolean gets to choose what that means.
    _vz0 = floor if floor > 0 else -0.20
    res = res.cut(_poly_solid(_void_in_recess(), _vz0, cavity + (floor - _vz0)))
    # corner relief (recess depth)
    cwp = cq.Workplane("XY").workplane(offset=bb - 0.01)
    for ccx, ccy in [(R, R), (W - R, R), (R, H - R), (W - R, H - R)]:
        cwp = cwp.moveTo(wx(ccx), wy(ccy)).circle(R + corner_clr)
    res = res.cut(cwp.extrude(board_th + 0.04))
    # INNER supports: perimeter lip
    lip = (cq.Workplane("XY").workplane(offset=floor).rect(cavW, cavH)
             .extrude(cavity).edges("|Z").fillet(cavR))
    lip = lip.cut(_cav_inner(floor - 0.01, cavity + 0.02, grow=RING_FUSE_EPS))
    # part-aware ring reliefs (2026-08-07): the ring is a guaranteed-minimum seat, but it
    # must never win against a part. Cut BEFORE the union so only ring metal is given up --
    # the per-band lip metal (block minus void) already stands LIP_CLR off every part.
    for _rp in _ring_reliefs():
        lip = lip.cut(_poly_solid(_rp, floor - 0.01, cavity + 0.02))
    res = res.union(lip)
    # interior lip edge-break, cut BEFORE the bosses. _lip_break_cut is a solid frustum spanning the whole
    # cavity interior, so with the bosses already placed it slices 0.10 off their tops. Cutting it while the
    # cavity is still empty removes only the chamfer rim on the lip inner edge; the bosses are unioned next
    # at full height (2.80) and fill the corner regions the break outline would otherwise reach.
    if lip_break > 0:
        res = res.cut(_lip_break_cut(bb, lip_break, -45))
    if EDGE_BREAK > 0 and floor == 0:                   # open frame: the resting face's wall edge
        res = res.cut(_resting_face_break(EDGE_BREAK))
    # bosses (always) + window braces (optional; OFF by default -- ribs+lip already support U7/caps;
    # the braces only propped the window / bare-laminate spans. Removing them frees board (13.6,40.1) &
    # (39.5,40.0) for future revs. Analysis: U7 floor clearance unchanged (rib end is its support).)
    for x, y, rr in [(mx, my, boss_r) for mx, my in mounts] + (list(BRACE) if braces else []) + (list(PILLARS) if pillars else []):
        b = cq.Workplane("XY").workplane(offset=floor).moveTo(wx(x), wy(y)).circle(rr).extrude(cavity)
        if lip_break > 0:                                   # convex top-edge break that FOLLOWS the boss circle;
            try: b = b.faces(">Z").chamfer(lip_break)       # chamfer the bare cylinder BEFORE the union (OCC won't
            except Exception: pass                          # chamfer the merged internal tops, but a lone cylinder is fine)
        if EDGE_BREAK > 0 and floor == 0:                   # open frame: the boss foot IS the resting face
            b = b.faces("<Z").chamfer(EDGE_BREAK)           # (raises if OCC refuses -- never ship it unbroken)
        res = res.union(b)
    # cap-gap ribs (full-cavity walls; also prop the board along the corridor)
    if ribs:
        for x0, y0, x1, y1 in RIBS:
            res = res.union(cq.Workplane("XY").workplane(offset=floor)
                              .moveTo(wx((x0+x1)/2), wy((y0+y1)/2)).rect(x1-x0, y1-y0).extrude(cavity))
    # round-tool corner relief (OFF by default): pre-filling the concave boss-lip / rib-lip junctions
    # to the tool radius makes the model match what the cutter leaves, but the only clean way to do it
    # here is a polygon offset, which exports as faceted faces a CAM seat cannot measure (PCBWay
    # rejects that). Left sharp, the model is fully analytic and a round tool simply leaves its own
    # radius there (standard practice; nothing mates in those corners). tool_relief=True re-enables it.
    if tool_relief:
        for poly in _relief_for(_cavity_islands(ribs, braces)):
            res = res.union(_poly_solid(poly, floor, cavity))
    # LOCATOR PILLARS (inverted from stub-holes): two Ø3.0 x 0.4 metal pillars left standing on the
    # cavity floor, engaging recesses in the brace bottom. Floor stays a FULL 0.95 everywhere (no holes,
    # uniform back for engraving) + adds metal; and the brace bottom is left clear so it can be sanded
    # flat to the fit (the component pockets are all on the TOP face, so only the bottom is sandable).
    if locators:
        for sx, sy in [(13.0, 35.0), (33.0, 55.0)]:
            res = res.union(cq.Workplane("XY").workplane(offset=floor).moveTo(wx(sx), wy(sy)).circle(3.0/2).extrude(0.4))
    # BACK FACE: frame == lip footprint + boss annuli, raised border_h
    if border_h > 0:
        frame = (cq.Workplane("XY").workplane(offset=-border_h).rect(cavW, cavH)
                   .extrude(border_h).edges("|Z").fillet(cavR))
        # symmetric recessed art field: equal proud border on all 4 sides. Inner fillet is concentric with
        # the outer frame fillet (cavR - back_border) so the border width stays uniform around the corners too.
        af = (cq.Workplane("XY").workplane(offset=-border_h - 0.01)
                .rect(cavW - 2*back_border, cavH - 2*back_border).extrude(border_h + 0.02)
                .edges("|Z").fillet(max(cavR - back_border, 0.3)))
        res = res.union(frame.cut(af))
        bwp = cq.Workplane("XY").workplane(offset=-border_h)
        for mx, my in mounts:
            bwp = bwp.moveTo(wx(mx), wy(my)).circle(boss_r)
        res = res.union(bwp.extrude(border_h))
        # round-tool relief on the BACK (OFF by default, same reason as the cavity): the annulus-frame
        # junctions are left sharp so the back stays analytic; the finisher leaves its own radius.
        if tool_relief:
            for poly in _relief_for(_back_islands(), BACK_TOOL_R):
                res = res.union(_poly_solid(poly, -border_h, border_h))
    # BACK FIN FIELDS: two fields with a clear band between them, texture rather than cooling.
    # Cut the whole field VALLEY deep into the floor, then stand the ribs back up PROUD of it --
    # the rib tops stay 0.05 UNDER the bearing plane, so the texture never scuffs on a desk and
    # never meets the lapping plate. (The bearing plane is the frame PLUS, since 2026-07-31, the
    # medallion crests -- coplanar at +0.15, finished by the same lap; the amendment is recorded
    # in fit_rules at FIN_PROUD.) Geometry is computed in fit_rules from the board: the clear
    # band IS the gap the two solar cells leave on the show face, so it tracks the board.
    if fins and border_h > 0:
        for _p in _fin_region().geoms if _fin_region().geom_type == "MultiPolygon" else [_fin_region()]:
            res = res.cut(_poly_solid(_p, 0.0, FIN_VALLEY))
        for _p in _fin_ribs():
            res = res.union(_poly_solid(_p, -FIN_PROUD, FIN_PROUD + FIN_VALLEY))

    # M2 holes CLEAN THROUGH (boss + skin + back annulus)
    twp = cq.Workplane("XY").workplane(offset=-border_h - 0.1)
    for mx, my in mounts:
        twp = twp.moveTo(wx(mx), wy(my)).circle(pilot_r)
    res = res.cut(twp.extrude(bb + border_h + 0.2))
    # back SPOTFACE at each hole: drop a local flat to exactly where the M2x3 brass tip lands,
    # so the tip sits FLUSH in the spotface while the annulus ring stays proud around it (Ti takes
    # the wear, not the soft brass). Bottom z = front - SCREW_LEN (~0.40 below the back face at this
    # stack); the depth tracks the screw + stack so the fit stays intentional, never almost.
    sf_bottom = (floor + cavity + board_th) - screw_len          # z the tip reaches (head seats on PCB front)
    sf_start  = -border_h - 0.4
    sfp = cq.Workplane("XY").workplane(offset=sf_start)
    for mx, my in mounts:
        sfp = sfp.moveTo(wx(mx), wy(my)).circle(CBORE_D / 2)
    res = res.cut(sfp.extrude(sf_bottom - sf_start))
    if prog_window:
        res = res.cut(cq.Workplane("XY").workplane(offset=-border_h - 0.1)
                        .moveTo(wx(13.3), wy(16.9)).circle(5.5).extrude(floor + border_h + 0.2))
    # glow-window reflector frame: a LASER-MARKED outline on the cavity floor (behind the monogram
    # window) locating the Al reflector strip. Marked, not cut -> the floor stays uniform `floor` mm.
    # Only engrave a real groove if MARK_DEPTH is set > 0 (off by default; it would thin the floor).
    if glow_marker and MARK_DEPTH > 0:
        gx0, gy0, gx1, gy1 = GLOW_WIN
        cx, cy = (gx0 + gx1) / 2, (gy0 + gy1) / 2
        ow, oh = (gx1 - gx0) + MARK_W, (gy1 - gy0) + MARK_W      # outer frame size
        iwd, ihd = (gx1 - gx0) - MARK_W, (gy1 - gy0) - MARK_W    # inner (window minus band)
        outer = (cq.Workplane("XY").workplane(offset=floor - MARK_DEPTH)
                   .moveTo(wx(cx), wy(cy)).rect(ow, oh).extrude(MARK_DEPTH + 0.02))
        inner = (cq.Workplane("XY").workplane(offset=floor - MARK_DEPTH - 0.01)
                   .moveTo(wx(cx), wy(cy)).rect(iwd, ihd).extrude(MARK_DEPTH + 0.04))
        res = res.cut(outer.cut(inner))
    # U7 relief pocket: a local 0.05 mm-deeper cavity floor under U7 (28.1,37.3) so U7 keeps a
    # 0.10 mm air gap (same as the caps) while the GENERAL floor is `floor` mm of back-engraving stock. 0.05 = U7_H-cap_H;
    # the caps (1.70) are the next-tallest, so the general cavity is cap-limited and only U7 needs relief.
    # Sits in the open cavity, clear of the ribs (y33..56 gap), lip, bosses, and the reflector frame.
    if U7_POCKET > 0:
        pw_, ph_ = U7_POCKET_WH
        res = res.cut(cq.Workplane("XY").workplane(offset=floor - U7_POCKET)
                        .moveTo(wx(U7_POS[0]), wy(U7_POS[1])).rect(pw_, ph_)
                        .extrude(U7_POCKET + 0.02).edges("|Z").fillet(TOOL_R))
    # Ti deburr edge-break (last): break the exposed END-FACE edges so no corner is knife-sharp.
    #   faces('<Z') = the proud back frame + annuli top (incl. the spotface mouths)
    #   faces('>Z') = the front rim + the board-recess mouth
    # The outer top/bottom rim is already eased by `edge_ease`. The internal board-rest tops (lip/boss/
    # rib at z=bb) and hole exits won't take a clean OCC chamfer here -> carry a drawing note instead:
    # "deburr all edges, break sharp corners ~0.1 mm (Ti)". Per-group try/except keeps the build robust.
    # NOT faces('>Z') while edge_ease is on (2026-11-13): edge_ease already broke the rim top
    # and the recess mouth, and chamfering them again left TWO facets -- 45 then 22.5 degrees,
    # 0.200 wide by 0.100 tall -- under a sheet that calls a single 0.10x45 (SolidCraft B5,
    # sectioned here at y44.45 on max and lite).
    # On the OPEN FRAME the resting face is broken by boolean instead: the wall's edge before the
    # bosses went on (_resting_face_break), each boss foot on its own cylinder, the spotface
    # mouths here.
    if EDGE_BREAK > 0 and floor == 0:
        res = res.cut(_spotface_mouth_break(EDGE_BREAK))
    if EDGE_BREAK > 0:
        for sel in tuple(s_ for s_ in (("<Z",) if edge_ease > 0 else ("<Z", ">Z"))
                         if not (s_ == "<Z" and floor == 0)):
            try:
                res = res.faces(sel).edges().chamfer(EDGE_BREAK)
            except Exception as e:
                print(f"  [deburr] faces('{sel}') skipped: {type(e).__name__}")
                _DEBURR_SKIPS.append((sel, type(e).__name__))    # the jobs loop refuses these
    # SCALLOP THE MOUNT BOSSES. fit_rules has always described a boss as a disc cut back
    # BOSS_CLR from every part that fouls it (boss_island); the brace reliefs and check [8]
    # both use that -- and the boss loop above unions the bare cylinder, so until 2026-11 the
    # cut never reached the metal (fit_rules.boss_fouls has the measured overlaps). After the
    # deburr on purpose: see _boss_scallop_tool.
    for mx, my in mounts:
        _tool = _boss_scallop_tool(mx, my, floor, cavity, foot=EDGE_BREAK if floor == 0 else 0.0)
        if _tool is not None:
            res = res.cut(_tool)
    # rear MEDALLION (Z9F, replaced the engraved maker's mark 2026-07-31): the coin. Cut
    # AFTER the deburr, deliberately: the 0.1 edge-break must never see the crest edges --
    # on a 0.30 letter stroke it would eat two-thirds of the lap face, and walking OCC
    # through hundreds of glyph edges is also what a 20-minute build looks like. The
    # crests' edge treatment IS the finishing: bead blast, then the plate lap.
    # medallion.py owns the geometry, the four parameters, the per-glyph Y-flip, the
    # machining mirror AND the island audit (it asserts, so an unmachinable RING_TEXT
    # refuses to build). What arrives here is final machining geometry, cut verbatim:
    #   cut_rest -> REST_D  (the O0.3's floors: counters + sub-O0.4 channels)
    #   cut_main -> COIN_D  (the O0.4's open coin floor)
    #   standing -> bearing-plane islands, unioned exactly the way the frame is made --
    #               EXTERIOR MINUS INTERIORS, or the union would fill back the counters
    #               the rest pass just cut.
    if maker_mark and border_h > 0:
        import time as _time
        import medallion as _md
        _t0 = _time.time()
        _mg = _md.geometry(_maker_text, MAKER_FONT_R, MAKER_FONT_B)
        print(f"  [medallion] geometry+audit {_time.time()-_t0:.1f}s")
        # Assemble each family as an OCC COMPOUND (no pre-fusing) so the shell sees
        # exactly two booleans; medallion.py already simplified the outlines (together, to
        # within 8 um), which is what keeps those two booleans from being a 20-minute build.
        _cutsol, _islsol = [], []
        for _geo, _d in ((_mg["cut_rest"], _md.REST_D), (_mg["cut_main"], _md.COIN_D)):
            for _p in (_geo.geoms if _geo.geom_type == "MultiPolygon" else [_geo]):
                if _p.is_empty:
                    continue
                _cut = (cq.Workplane("XY").workplane(offset=-0.02)
                        .polyline([(wx(x), wy(y)) for x, y in list(_p.exterior.coords)])
                        .close().extrude(_d + 0.02))
                for _r in _p.interiors:
                    _cut = _cut.cut(cq.Workplane("XY").workplane(offset=-0.04)
                                    .polyline([(wx(x), wy(y)) for x, y in list(_r.coords)])
                                    .close().extrude(_d + 0.08))
                _cutsol.append(_cut.val())
        _sg = _mg["standing"]
        for _p in (_sg.geoms if _sg.geom_type == "MultiPolygon" else [_sg]):
            _isl = (cq.Workplane("XY").workplane(offset=-border_h)
                    .polyline([(wx(x), wy(y)) for x, y in list(_p.exterior.coords)])
                    .close().extrude(border_h + 0.02))
            for _r in _p.interiors:
                _isl = _isl.cut(cq.Workplane("XY").workplane(offset=-border_h - 0.02)
                                .polyline([(wx(x), wy(y)) for x, y in list(_r.coords)])
                                .close().extrude(border_h + 0.06))
            _islsol.append(_isl.val())
        print(f"  [medallion] {len(_cutsol)} cut + {len(_islsol)} island prisms "
              f"{_time.time()-_t0:.1f}s")
        if _cutsol:
            # FUSE the cut family into one tool before cutting. rest and main share
            # their borders vertex for vertex now (medallion._partition), so the prisms
            # no longer micro-overlap -- but they still TOUCH along every shared wall,
            # and an OCC cut with a compound of touching tools fails SILENTLY and
            # partially (found, in the overlapping era, as a coin floor that never got
            # cut while the counters did). One fused tool, one clean cut.
            _tool = _cutsol[0]
            for _s in _cutsol[1:]:
                _tool = _tool.fuse(_s)
            res = res.cut(_tool)
            print(f"  [medallion] coin cut done {_time.time()-_t0:.1f}s")
        if _islsol:
            res = res.union(cq.Compound.makeCompound(_islsol))
            print(f"  [medallion] crests unioned {_time.time()-_t0:.1f}s")
    return res

# ===== variants (titanium only; 7075 retired -- final part is Ti) =====
# Write next to this script by default. This used to be a hardcoded /mnt/user-data/outputs/ that
# does not exist in a plain checkout, so the generator could not actually regenerate its own STEP.
OUT = os.environ.get("OUT_DIR") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "")
# The jobs are the VARIANTS (fit_rules owns the numbers; this loop owns only the flags
# that are shell-build mechanics). Names come from the table -- note the max variant keeps
# its historical filename (every ledger, render input and doc points at it), and the air
# frame's name dodges the 'backshell' substring on purpose: scripts/ref_figures.py asserts
# exactly one enclosure/*backshell*.stl and would kill the fab job otherwise.
#
# Ti-max-progwindow RETIRED 2026-08-01 (false affordance over SC1's can + half the CAD
# minutes; one jobs row plus prog_window=True brings it back -- STEP/STL in git history).
# Ti-conservative (0.60 floor / 1.60 wall) struck: if the shop cannot hold the floor we
# re-issue to whatever minimum they will hold, so a pre-baked 0.60 fallback is dead weight.
jobs = []
for _vn, _v in VARIANTS.items():
    jobs.append((
        _vn, _v["shell_name"], _v["floor"], _v["wall_th"], _v["border_h"], _v["cavity"],
        _v["screw_len"],
        not _v["open_back"] and _v["medallion"],          # maker_mark drives the medallion
        not _v["open_back"] and _v["fins"],
        not _v["open_back"],                              # glow marker needs a floor
        _v["material"],
    ))
print(f"cavity={cavity} general (max; per-variant from fit_rules.VARIANTS); U7 pocket {U7_POCKET} deep "
      f"({'NO POCKET -- uniform floor' if U7_POCKET == 0 else 'local relief'})  lip PER-BAND from the board (W {_LIPSUM['W']} / E {_LIPSUM['E']} / S {_LIPSUM['S']} / N {_LIPSUM['N']} bands)  "
      f"braces=OFF (removed; {len(BRACE)} defs retained) ribs={len(RIBS)}  border=0.15  "
      f"cavity tool R{TOOL_R} (Ø{2*TOOL_R}) / back tool R{BACK_TOOL_R} (Ø{2*BACK_TOOL_R}) / fin groove tool Ø0.6 (grooves 0.8, its work alone) / "
      f"medallion Ø0.4 coin + Ø0.3 rest (islands, vertical walls; crests ON the bearing plane -- lap after blast)  "
      f"deburr: outer rim {edge_ease}, ends {EDGE_BREAK}  reflector-frame {GLOW_WIN[2]-GLOW_WIN[0]:.1f}x{GLOW_WIN[3]-GLOW_WIN[1]:.1f} laser-marked (full floor under it)  "
      f"relief: OFF (concave junctions left sharp -> clean analytic STEP; round tool leaves its radius)")
for _vn, name, fl, wl, bd, cav_v, sl, mk, fn, gm, mat in jobs:
    del _DEBURR_SKIPS[:]
    solid = build(floor=fl, wall_th=wl, border_h=bd, cavity=cav_v, screw_len=sl,
                  maker_mark=mk, fins=fn, glow_marker=gm)
    if _DEBURR_SKIPS:
        raise SystemExit(f"[{_vn}] the edge-break was skipped on {_DEBURR_SKIPS} -- OCC could "
                         f"not chamfer that end face, so the solid would ship without breaks "
                         f"its drawing calls MODELED. Not exporting {name}; see _DEBURR_SKIPS.")
    field = fl + cav_v + board_th                       # per-variant, NOT the module cavity
    foot = (W + 2*edge_fit + 2*wl)
    # Modelled in board coordinates, which are LEFT-handed; written right-handed. export_solid
    # reflects once on the way out (fit_rules, THE FILE FRAME) -- never call an exporter here.
    export_solid(solid, OUT + name, 0.04)
    print(f"  {name:38s} [{_vn}] floor={fl:.2f} cavity={cav_v:.2f} wall={wl:.2f} "
          f"field={field:.2f} at-frame={field+bd:.2f} foot={foot:.1f}mm M2x{sl} "
          f"medallion={mk} fins={fn} | {mat}")
print("done")
