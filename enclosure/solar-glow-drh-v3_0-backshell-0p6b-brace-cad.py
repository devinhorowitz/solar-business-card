#!/usr/bin/env python3
"""
solar-glow-drh-v3_0-backshell-0p6b-brace-cad.py  -  0.6 mm-board DUMB-BOX shell for the resin brace.

Back-only titanium shell for the SOLAR-GLOW DRH PCB. It drops over the populated back and is held by
four corner M2 screws; the bare show-front (two solar cells + the backlit DRH monogram window) stays
exposed. This is the "dumb box": floor + walls + four corner bosses + a U2 relief pocket + two metal
locator pillars, nothing else. All center support and the window/EMI features live in a separate
dielectric resin brace, so a PCB layout change is a brace reprint, never a shell re-machine.

Z stack (aligned to PCB/solar-glow-drh-v3_0.kicad_pcb, 0.60 mm board):
  floor 0.95  +  cavity 1.85  +  board recess 0.60  =  3.40 field  (3.55 at the 0.15 back frame).
The 0.60 board (vs 0.80) frees 0.20 mm into the floor: 0.95 clears stainless/copper and puts aluminum
past the old titanium-0.75 stiffness, without growing the assembled part. Overall stays 3.55.

Locator pillars: two Ø3.0 x 0.4 metal pillars stand on the cavity floor at board (13,35) and (33,55)
(both west of the NFC coil), left as islands in the same cavity pass as the four bosses. They engage
Ø3.2 x 0.8 recesses in the brace bottom: 0.4 engagement, 0.1 radial, ~0.25 axial margin after the
brace's ~0.15 bottom-sanding. Height is 0.4 (not 0.6): the recess is 0.8 and the brace bottom is
sanded to fit, so 0.4 preserves the axial margin against sanding variation. The floor stays a full
0.95 everywhere -- no locating holes, so the back is a uniform engraving surface.

No ribs, no support posts: the resin brace carries center support. The rib/brace machinery is retained
as build() options (ribs=/braces=) for a fallback, but the shipped part uses neither.

U2 (SOIC-8, 1.75 mm, the tallest B-side part) sits over a local 0.05 relief pocket in the cavity floor
(local floor 0.90) so it keeps its full 0.15 mm air under its through-cutout. Watch U2-region flex at
bench bring-up -- no rib props it now; the fallback if it matters is a short local rib stub there.

Bench / board-side items (not resolved in CAD):
 - Grounded pillars land on the board back (GND pour with VS mesh + signals). A pillar on GND pour is
   fine (reinforces the tie); on VS or a signal it SHORTS. Nets are name-only in the KiCad-2026 file,
   so guarantee GND-pour-or-bare laminate under each ~Ø3.0 spot board-side.
 - 0.60 board wants a reflow carrier/fixture; bare-board handling is floppier than 0.80.
 - NFC retune: layer-to-layer spacing shrinks 0.80 -> 0.60, nudging the coil tune (brace ferrite + C9).

The 3D STEP governs all geometry; this generator is the source of truth (it prints the full Z-stack and
regenerates the STEP/STL from the PCB anchors).
"""
import cadquery as cq
from shapely.geometry import Point, box
from shapely.ops import unary_union

# ===== board (committed PCB) =====
W, H, R   = 50.80, 88.90, 3.0
board_th  = 0.60
mounts = [(3.0, 3.0), (47.8, 3.0), (3.0, 85.9), (47.8, 85.9),      # 4x corner M2, GND, 2.2 drill -- v3.0: concentric with the r3.0 corner fillets (x-inset 3.5->3.0; matches committed PCB v3_0 MH1-4)
          (3.0, 28.5), (47.8, 28.5), (3.0, 60.4), (47.8, 60.4)]    # +4 panel-corner M2, GND -- match PCB nudge (holes at panel inner corners). 2-col 8-mount pattern. Verified vs committed board: W(3.0,28.5) boss r2.6 clears R14 by 0.34 (R14 y0 31.44, boss top y31.10) and U6 by 0.25 (U6 x0 5.85, boss E x5.60) -- TIGHT; a board-side nudge of U6/R14 (or a local boss trim there) buys margin if a fit check wants it. E bosses at x47.8 merge into the pinched east lip like the corner bosses.

# ===== fixed shell knobs =====
U2_H       = 1.75                  # U2 (SOIC-8 max, datasheet): the single tallest back part
cap_H      = 1.70                  # WS17 supercaps (locked): the 2nd-tallest parts (x4) -> set the GENERAL cavity
kapton_th  = 0.00                  # DROPPED (all contacts on bare laminate). set 0.05 to reinstate.
cav_margin = 0.10                  # air over the cavity-setting parts. general cavity 1.80 = cap_H + air. Reduced 0.15->0.10 now the brace + cell-sandwiches carry the board: cavity 1.80 +-0.05 -> 1.75 worst-case, minus WS17 1.70 MAX (datasheet Case WS17: height max 1.7) = 0.05 non-contact. The freed 0.05 goes into the floor.
cavity     = round(cap_H + kapton_th + cav_margin, 3)   # 1.85 general (cap-limited); toleranced 1.85 +-0.05 -> 1.80 min
# U2 alone is 0.05 mm taller than the caps, so a LOCAL relief pocket in the cavity floor under U2 dips
# the floor 0.05 there (local cavity 1.90) to keep U2's full 0.15 air, while the GENERAL floor runs
# 0.05 thicker for back-engraving stock. 0.05 = U2_H - cap_H is the ceiling for this trick: beyond it
# you'd have to pocket the caps (17x28.5 mm each, x4 = a second cavity). Pocket = U2 pad box + margin.
U2_POCKET    = round(U2_H - cap_H, 3)     # 0.05 mm local floor relief under U2
U2_POS       = (30.10, 37.64)             # U2 origin, board coords (committed PCB v3.0, re-derived): part shifted +1.60 E / +0.64 S in the passive-consolidation reflow. Pad box 6.75 x 4.41 (unchanged footprint), centered here.
U2_POCKET_WH = (7.8, 5.4)                 # pocket size: pad box + ~0.5 margin all round. At the new U2_POS the pocket spans y[34.94,40.34] -> N edge 0.46 clear of the glow window (y40.80); E edge x34.0 covers the U2 east pad (x33.48).

edge_fit   = -0.05                 # press interference on the FLATS
corner_clr = 0.15                  # corner relief so the press grips the flats
edge_ease  = 0.10                  # light edge-break on the outer rim + recess mouth (felt, not seen)
lip_break  = 0.10                  # light 45deg edge-break on the inner (cavity-side) lip edge (felt, not seen)
EDGE_BREAK = 0.10                  # Ti deburr: break the sharp END-FACE edges (back proud frame/annuli
                                   # + front rim + recess mouth) so corners are durable, not knife-sharp.
                                   # Ti edges chip and cut; an edge-break also resists nicking. ~0.1 mm.
# ASYMMETRIC support lip (per side) -- wider = more board-edge support = stiffer PCB. Widths bounded
# by the nearest B-side part on each edge (v3.0 board, measured):
lip_W, lip_N, lip_S = 2.5, 2.0, 2.0   # W: long west edge, nearest B-part R14/J1 ~3.4 -> 2.5 clears by ~0.9 (big rigidity gain). N/S: bounded by SC1-4 caps (body max edge ~2.35 from the board edge; datasheet WS17 body 28.5 +0.5/-0.0 long) -> 2.0 clears by ~0.35.
lip_E      = 1.0                       # E stays narrow through the JP1/TP1 pads (reach x49.6) AND clear of the NFC coil (~x49): lip_E=1.0 -> wall x49.8, east of both. A grounded Ti lip over the coil would detune it.
lip_E_wide = 2.5                       # E END zones (clear of pads+coil) widen to match the west
EAST_WIDE_Y = [(0.0, 10.0)]   # board-y bands the E lip widens to 2.5 (else pinched to 1.0, wall x49.8).
# 2026-07-11: NORTH wide band (72,88.9) REMOVED -> east lip is now pinched (1.0, wall x49.8) over all of
# y10-88.9. The relocated clamp cluster (owner's board edit: Q1/U4/R7/R9/C7 moved to clear the PV2-corner
# screw; C10 was DELETED in the passive consolidation) sits in y72-88.9 with east edges C7 @ x49.55, U4 49.16,
# R7/R9 48.98, Q1 48.51 -- these overhang the old 2.5 wide lip (wall x48.3). Re-verified vs the committed board:
# the tightest east part overall is D10 @ x49.58 (y64.86, in the mid pinch band, not the clamp cluster); the
# 1.0 pinch (wall x49.8) clears D10 by 0.22 and C7 by 0.25 -- the SAME tolerance class as the JP1/TP1 pinch at
# x49.6. The NFC coil (east copper ~x48.4) stays well clear of the x49.8 wall. Edge-support lost under the pinch
# is picked up by the brace east rail (RAIL_E_N extended to x49.70, in the brace generator).
lip_w      = lip_E                      # legacy min-lip alias (only the dormant tool_relief helper still reads it)
back_border = 2.0                      # SYMMETRIC proud back-frame border, equal on all 4 sides (decoupled from the asymmetric front lip). Front lip stays asymmetric (it clears B-side parts); this is the cosmetic exterior back border only.
boss_r     = 2.60                  # M2 boss / back annulus outer radius
pilot_r    = 0.80                  # M2 tap-drill hole, CLEAN THROUGH. Boss is TAPPED M2 (brass is soft --
                                   # never let a brass screw thread-form into Ti; cut the threads first).
# corner fasteners: brass M2x3, pan head <= Ø4.0 (cell-limited; absolute Ø5.3 touches the cell at 2.66 mm).
SCREW_LEN  = 3.0                   # under-head length (M2x3). Head seats on the PCB front.
CBORE_D    = 3.0                   # back spotface dia at each hole; depth auto-set so the M2x3 tip is flush.

# glow-window reflector registration frame (on the cavity FLOOR): a LASER-MARKED outline showing where
# the Al reflector strip is placed -- behind the monogram window, facing the reverse-mount LEDs -- so
# stray back-emission bounces forward through the FR4 letters and lifts the glow. Marked, NOT cut: the
# floor stays a full 0.75 mm under the frame (the only relief is the 0.05 U2 pocket, well clear of it).
# GLOW_WIN is the monogram footprint from the committed PCB.
GLOW_WIN   = (14.95, 40.8, 35.85, 47.0)   # board coords (x0,y0,x1,y1); 20.9 x 6.2 mm, centered (25.4,43.9)
MARK_W     = 0.25                  # frame outline width (in-plane), hairline -- laser-marked, no material removed
MARK_DEPTH = 0.00                  # 0 = laser mark (no cut). >0 would engrave a groove (thins the floor); kept off.
# ---- rear MAKER'S MARK: hard-engraved into the recessed back field (tucked lower-left, asymmetric). Cut
# 0.20mm into the 1.0mm floor stock -> a real machined mark, not a surface etch. Mirrored about the board
# center X so it reads correctly when the card is turned over. Name in Bold, the line above it in Regular. ----
MAKER_DEPTH  = 0.20
MAKER_FONT_R = "/home/claude/fonts/JetBrainsMono-Regular.ttf"
MAKER_FONT_B = "/home/claude/fonts/JetBrainsMono-Bold.ttf"
MAKER_LINES  = [                       # (text, LEFT-edge x, centerline y, cap height, font)  board coords, readable
    ("DESIGNED & MADE BY", 7.0, 79.3, 1.20, MAKER_FONT_R),
    ("DEVIN HOROWITZ",     7.0, 81.9, 1.65, MAKER_FONT_B),
]

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
# (braces=False default): U2 + caps are held by the ribs+lip (U2's support is the rib end, unchanged);
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
def _cav_inner(z0, dz):
    """asymmetric inner cavity void (per-side lips), corners filleted to IR."""
    cx, cy = wx((lip_W + W - lip_E)/2.0), wy((lip_N + H - lip_S)/2.0)
    return (cq.Workplane("XY").workplane(offset=z0).center(cx, cy)
              .rect(W - lip_E - lip_W, H - lip_S - lip_N).extrude(dz).edges("|Z").fillet(IR))
def _east_blocks(z0, dz):
    """solid east-END wide-lip blocks: fill x[W-lip_E_wide, W-lip_E] over the EAST_WIDE_Y bands."""
    out = None
    for ya, yb in EAST_WIDE_Y:
        blk = (cq.Workplane("XY").workplane(offset=z0)
                 .center(wx((2*W - lip_E_wide - lip_E)/2.0), wy((ya + yb)/2.0))
                 .rect(lip_E_wide - lip_E, yb - ya).extrude(dz))
        out = blk if out is None else out.union(blk)
    return out
def _lip_void_P():
    """Cavity-void perimeter in BOARD coords: straight W/N/S edges + the NOTCHED east edge, built from
    EAST_WIDE_Y so it is correct for ANY number of wide bands -- one pinch-step for the current single
    south band [(0,10)]; two for the older wide-both-ends layout. East x = W-lip_E_wide inside a wide
    band, else W-lip_E. (Previously this polygon hard-coded EAST_WIDE_Y[0] and [1]; that indexed out of
    range once the north wide band was removed, so the generator could not run until this rewrite.)"""
    y0, y1 = lip_N, H - lip_S
    wide = lambda y: any(a <= y < b for a, b in EAST_WIDE_Y)
    xw, xp = W - lip_E_wide, W - lip_E
    xat = lambda y: (xw if wide(y) else xp)
    east = [(xat(y0 + 1e-6), y0)]
    for by in sorted({b for band in EAST_WIDE_Y for b in band if y0 < b < y1}):
        east += [(xat(by - 1e-6), by), (xat(by + 1e-6), by)]      # step at each wide/pinch boundary
    east.append((xat(y1 - 1e-6), y1))
    return [(lip_W, lip_N)] + east + [(lip_W, y1)]
def _lip_inner_pts():
    """lip inner (cavity void) perimeter, MODEL coords: the notched asymmetric outline. West corners are
    filleted in the real part; here sharp -> a ~lip_break cosmetic over-cut at those 2 corners only."""
    return [(wx(x),wy(y)) for x,y in _lip_void_P()]
def _lip_break_cut(bb, c, taper):
    """45deg edge-break on the lip inner top edge: taper-extrude the void outline over the top c mm so it
    grows outward into the lip, and cut it -> the sharp top-inner lip edge is knocked back at 45deg."""
    sk = cq.Sketch().polygon([(wx(x),wy(y)) for x,y in _lip_void_P()]).reset().vertices("<Y").fillet(IR).reset().vertices(">Y").fillet(IR)
    return cq.Workplane("XY").workplane(offset=bb-c).placeSketch(sk).extrude(c, taper=taper)

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
    isl  = [Point(mx, my).buffer(boss_r, resolution=64) for mx, my in mounts]
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

def _maker_text(txt, lx, cy, capH, fontpath):
    """Readable all-caps engraving text: LEFT edge at x=lx, vertically centered at y=cy, cap height ~capH.
    Returns shapely geometry in BOARD coords (pre-mirror)."""
    import shapely.affinity as _aff
    from shapely.geometry import Polygon as _Poly
    from shapely.ops import unary_union as _uu
    from matplotlib.textpath import TextPath as _TP
    from matplotlib.font_manager import FontProperties as _FP
    from matplotlib.path import Path as _MP
    from functools import reduce as _rd
    tp=_TP((0,0),txt,size=100.0,prop=_FP(fname=fontpath))
    if not len(tp.vertices): return None
    conts=[c for c in _MP(tp.vertices,tp.codes).to_polygons(closed_only=True) if len(c)>=4]
    geom=_rd(lambda a,b:a.symmetric_difference(b),[_Poly(c).buffer(0) for c in conts])
    mnx,mny,mxx,mxy=geom.bounds; sc=capH/(mxy-mny)
    geom=_aff.scale(geom,xfact=sc,yfact=sc,origin=(mnx,mny)); mnx,mny,mxx,mxy=geom.bounds
    return _aff.translate(geom, lx-mnx, cy-(mny+mxy)/2)

# ===== build =====
def build(floor=1.00, wall_th=1.0, border_h=0.15, ribs=False, braces=False, pillars=False, locators=False, prog_window=False, glow_marker=True, maker_mark=True, tool_relief=False):
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
    res = res.cut(_cav_inner(floor, cavity)).union(_east_blocks(floor, cavity))
    # corner relief (recess depth)
    cwp = cq.Workplane("XY").workplane(offset=bb - 0.01)
    for ccx, ccy in [(R, R), (W - R, R), (R, H - R), (W - R, H - R)]:
        cwp = cwp.moveTo(wx(ccx), wy(ccy)).circle(R + corner_clr)
    res = res.cut(cwp.extrude(board_th + 0.04))
    # INNER supports: perimeter lip
    lip = (cq.Workplane("XY").workplane(offset=floor).rect(cavW, cavH)
             .extrude(cavity).edges("|Z").fillet(cavR))
    lip = lip.cut(_cav_inner(floor - 0.01, cavity + 0.02))
    res = res.union(lip)
    # interior lip edge-break, cut BEFORE the bosses. _lip_break_cut is a solid frustum spanning the whole
    # cavity interior, so with the bosses already placed it slices 0.10 off their tops. Cutting it while the
    # cavity is still empty removes only the chamfer rim on the lip inner edge; the bosses are unioned next
    # at full height (2.80) and fill the corner regions the break outline would otherwise reach.
    if lip_break > 0:
        res = res.cut(_lip_break_cut(bb, lip_break, -45))
    # bosses (always) + window braces (optional; OFF by default -- ribs+lip already support U2/caps;
    # the braces only propped the window / bare-laminate spans. Removing them frees board (13.6,40.1) &
    # (39.5,40.0) for future revs. Analysis: U2 floor clearance unchanged (rib end is its support).)
    for x, y, rr in [(mx, my, boss_r) for mx, my in mounts] + (list(BRACE) if braces else []) + (list(PILLARS) if pillars else []):
        b = cq.Workplane("XY").workplane(offset=floor).moveTo(wx(x), wy(y)).circle(rr).extrude(cavity)
        if lip_break > 0:                                   # convex top-edge break that FOLLOWS the boss circle;
            try: b = b.faces(">Z").chamfer(lip_break)       # chamfer the bare cylinder BEFORE the union (OCC won't
            except Exception: pass                          # chamfer the merged internal tops, but a lone cylinder is fine)
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
    # M2 holes CLEAN THROUGH (boss + skin + back annulus)
    twp = cq.Workplane("XY").workplane(offset=-border_h - 0.1)
    for mx, my in mounts:
        twp = twp.moveTo(wx(mx), wy(my)).circle(pilot_r)
    res = res.cut(twp.extrude(bb + border_h + 0.2))
    # back SPOTFACE at each hole: drop a local flat to exactly where the M2x3 brass tip lands,
    # so the tip sits FLUSH in the spotface while the annulus ring stays proud around it (Ti takes
    # the wear, not the soft brass). Bottom z = front - SCREW_LEN (~0.40 below the back face at this
    # stack); the depth tracks the screw + stack so the fit stays intentional, never almost.
    sf_bottom = (floor + cavity + board_th) - SCREW_LEN          # z the tip reaches (head seats on PCB front)
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
    # rear MAKER'S MARK: engrave into the recessed back field, mirrored about board center X so it reads
    # right when the card is turned over to the back. Lower-left, clear of the bottom boss annuli (y<83.3).
    if maker_mark:
        import shapely.affinity as _aff
        from shapely.ops import unary_union as _uu
        _mk=[g for g in (_maker_text(t,lx,cy,cH,fp) for t,lx,cy,cH,fp in MAKER_LINES) if g is not None]
        if _mk:
            _mg=_aff.scale(_uu(_mk), xfact=-1, yfact=1, origin=(25.4,44.45))
            for _p in (_mg.geoms if _mg.geom_type=="MultiPolygon" else [_mg]):
                _cut=(cq.Workplane("XY").workplane(offset=-0.05)
                        .polyline([(wx(x),wy(y)) for x,y in list(_p.exterior.coords)]).close().extrude(MAKER_DEPTH+0.05))
                for _r in _p.interiors:
                    _cut=_cut.cut(cq.Workplane("XY").workplane(offset=-0.10)
                            .polyline([(wx(x),wy(y)) for x,y in list(_r.coords)]).close().extrude(MAKER_DEPTH+0.20))
                res=res.cut(_cut)
    # U2 relief pocket: a local 0.05 mm-deeper cavity floor under U2 (30.10,37.64) so U2 keeps a
    # 0.10 mm air gap (same as the caps) while the GENERAL floor is `floor` mm of back-engraving stock. 0.05 = U2_H-cap_H;
    # the caps (1.70) are the next-tallest, so the general cavity is cap-limited and only U2 needs relief.
    # Sits in the open cavity, clear of the ribs (y33..56 gap), lip, bosses, and the reflector frame.
    if U2_POCKET > 0:
        pw_, ph_ = U2_POCKET_WH
        res = res.cut(cq.Workplane("XY").workplane(offset=floor - U2_POCKET)
                        .moveTo(wx(U2_POS[0]), wy(U2_POS[1])).rect(pw_, ph_)
                        .extrude(U2_POCKET + 0.02).edges("|Z").fillet(TOOL_R))
    # Ti deburr edge-break (last): break the exposed END-FACE edges so no corner is knife-sharp.
    #   faces('<Z') = the proud back frame + annuli top (incl. the spotface mouths)
    #   faces('>Z') = the front rim + the board-recess mouth
    # The outer top/bottom rim is already eased by `edge_ease`. The internal board-rest tops (lip/boss/
    # rib at z=bb) and hole exits won't take a clean OCC chamfer here -> carry a drawing note instead:
    # "deburr all edges, break sharp corners ~0.1 mm (Ti)". Per-group try/except keeps the build robust.
    if EDGE_BREAK > 0:
        for sel in ("<Z", ">Z"):
            try:
                res = res.faces(sel).edges().chamfer(EDGE_BREAK)
            except Exception as e:
                print(f"  [deburr] faces('{sel}') skipped: {type(e).__name__}")
    return res

# ===== variants (titanium only; 7075 retired -- final part is Ti) =====
OUT = "/mnt/user-data/outputs/"
B = "solar-glow-drh-v3_0-backshell-0p6b-brace"
jobs = [
    # name                 floor wall  border ribs  prog   note
    ("Ti-max",             1.00, 1.00, 0.15, False, False, "0.6mm-board DUMB BOX for the resin brace: TRUE 1.00 floor (cavity 1.80, cap gap 0.10) + U2 relief pocket + 1.0 walls + 8 bosses (4 corner + 4 panel-corner). NO locator pillars (retired: the H-brace registers by fitment). NO ribs (the brace carries center support). Overall 3.55."),
    ("Ti-max-progwindow",  1.00, 1.00, 0.15, False, True,  "0.6mm-board / ribs-trimmed + TC2030 re-flash window"),
]
# Ti-conservative (0.60 floor / 1.60 wall) struck: if the shop cannot hold the floor we
# re-issue to whatever minimum they will hold, so a pre-baked 0.60 fallback is dead weight.
print(f"cavity={cavity} general (cap {cap_H}+air {cav_margin}; kapton {kapton_th}); U2 pocket {U2_POCKET} deep "
      f"-> 1.85 local (U2 keeps 0.10)  lips W/N/S/E={lip_W}/{lip_N}/{lip_S}/{lip_E} (E ends {lip_E_wide})  "
      f"braces=OFF (removed; {len(BRACE)} defs retained) ribs={len(RIBS)}  border=0.15  "
      f"cavity tool R{TOOL_R} (Ø{2*TOOL_R}) / back tool R{BACK_TOOL_R} (Ø{2*BACK_TOOL_R})  "
      f"deburr: outer rim {edge_ease}, ends {EDGE_BREAK}  reflector-frame {GLOW_WIN[2]-GLOW_WIN[0]:.1f}x{GLOW_WIN[3]-GLOW_WIN[1]:.1f} laser-marked (full floor under it)  "
      f"relief: OFF (concave junctions left sharp -> clean analytic STEP; round tool leaves its radius)")
for name_suf, fl, wl, bd, rb, pw, note in jobs:
    solid = build(floor=fl, wall_th=wl, border_h=bd, ribs=rb, prog_window=pw)
    field = fl + cavity + board_th
    foot = (W + 2*edge_fit + 2*wl)
    name = f"{B}-{name_suf}"
    cq.exporters.export(solid, OUT + name + ".step")
    cq.exporters.export(solid, OUT + name + ".stl", tolerance=0.04, angularTolerance=0.2)
    print(f"  {name:34s} floor={fl:.2f} wall={wl:.2f} field={field:.2f} at-frame={field+bd:.2f} foot={foot:.1f}mm "
          f"ribs={rb} prog={pw} | {note}")
print("done")
