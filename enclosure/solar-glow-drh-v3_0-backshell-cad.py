#!/usr/bin/env python3
"""
solar-glow-drh-v3_0-backshell-cad.py  -  metal back-shell generator (CadQuery / OpenCASCADE)

v3.0 ALIGNMENT: matches PCB solar-glow-drh-v3_0 (2-layer). The one PCB-driven change from the
enclosure's prior state is the 4 M2 holes moving CONCENTRIC with the r3.0 board corner fillets
(x-insets 3.5 -> 3.0; y already 3.0): mounts (3.0,3.0)/(47.8,3.0)/(3.0,85.9)/(47.8,85.9), matching
the committed PCB MH1-4. The boss (r2.60) now sits 0.40 uniform off the cavity corner wall -- a
sub-Ø2.0-cutter cusp that fuses into the corner (same machining class as the boss-lip junctions;
better tap support). This file supersedes the v3.0-chat enclosure regen, which was forked from an
OLDER generator state (window braces still ON, floor 0.55): this carries the enclosure decisions made
since -- braces removed (ribs+lip hold U2/caps), floor pushed to 0.75 as back-engraving stock, and a
local 0.05 U2 relief pocket so U2 keeps its full 0.15 air. board_th 0.80 (0.8-vs-1.0 still open).

================================================================================================
TITANIUM LIMIT-PUSH (this revision). Final part is Ti-6Al-4V; the audit re-derived every dimension
against datasheet heights + plate mechanics. Findings that drove the numbers below:

  * Cavity is PART-limited, not a lever: U2 (SOIC-8, datasheet max 1.75) and the WS17 caps (1.70,
    locked) set it. General cavity 1.85 = cap 1.70 + 0.15 air; a local 0.05 relief pocket under U2
    (1.90 there) keeps U2's full 0.15 air. Cannot shrink further without pocketing the caps.
  * The floor is the lever, and Ti YIELD is never the limit -- a 0.2 mm Ti floor stays sub-yield
    even at a hard 50 N press. The binding limit is the floor DEFLECTING into the parts (air gap
    0.15 mm to U2, 0.20 mm to the caps).
  * The old lip-only-plus-window-braces left a 19.5 mm-radius UNSUPPORTED floor disk over the cap
    regions; at that span a 0.6 mm floor already TOUCHES a cap at 50 N (needs 0.62). So the prior
    floor was marginal.
  * FIX = stiffen the floor with continuous RIBS in the empty cap-gap corridors (the SC1|SC2 and
    SC3|SC4 channels, x 24.9-25.9, on bare laminate, no pads/vias). With the ribs + the 2 window
    braces the worst span drops to ~11.6 mm. At 0.45 the cap gap already cleared 50 N; the floor is
    now run at 0.75 mm as back-engraving stock (2.5x stiffer than the analyzed 0.55, so every clearance
    margin only improves), with a local 0.05 relief pocket dipping it to 0.70 under U2. The reflector
    frame is LASER-MARKED on the cavity floor, not cut, so it removes no material.
  * Kapton DROPPED: every metal contact (lip in the pad-free rim band, 4 braces, 2 ribs) sits on
    bare laminate -- verified against the PCB -- so the blanket is unnecessary. (Keep a die-cut
    Kapton strip only if a via audit on the rib lines later finds an untented via.)
  * Walls 1.6 -> 1.0 mm: Ti is plenty strong for a press-fit rim on a 0.8 mm FR4 edge; shrinks the
    footprint from 53.9 to 52.8 mm (closer to the 50.8 card).

  Ti-max stack: floor 0.75 + cavity 1.85 + board 0.80 = 3.40 mm field (3.55 at the back frame, with
  the 0.15 mm border). M2 thread is screw-limited, not Ti-limited (~2.2 mm of engagement, unchanged).

BACK FACE = metal rubbing of the interior: 4 screw posts drilled CLEAN THROUGH, a raised frame that
mirrors the inner lip (PCB-perimeter footprint + width), and the bosses as raised annuli fused to
the frame the way the inner bosses fuse to the lip; all raised `border_h` (0.15 mm machined step) so
engraved/laser rear art in the recessed field takes no wear. The frame is milled, not etched; only
the decals inside it are laser work.

ROUND-TOOL MACHINABILITY (both faces): every convex feature (bosses, brace posts, rib ends, the frame
and prism outlines) is clear for a round tool to mill around, and the recess corners (2.95), outer
margin (3.95+) and field inner (1.45) all clear a Ø2.0 cutter. The concave boss-lip / rib-lip and
annulus-frame junctions are left SHARP in the model: a spinning end mill physically leaves its own
tool-radius fillet there, nothing mates in those corners, and modeling them sharp keeps every surface
analytic (a pre-modeled radius could only be a polygon offset here, which exports as faceted faces a
CAM seat cannot measure). `tool_relief=True` re-enables the (faceted) pre-fill if ever wanted; it is
OFF by default. The finishing-tool radii are still called out for reference: cavity TOOL_R R1.0 = Ø2.0,
back field BACK_TOOL_R R0.5 = Ø1.0.

TI EDGE-BREAK (deburr): titanium edges chip and cut, so no corner is left knife-sharp. The outer
top/bottom rim is eased `edge_ease` (0.20); the exposed END-FACE edges -- the proud back frame and
annuli tops (incl. spotface mouths) and the front rim + board-recess mouth -- are broken `EDGE_BREAK`
(0.10). The internal board-rest tops (lip/boss/rib) and hole exits don't take a clean modeled chamfer
in OCC; carry the drawing note "deburr all edges, break sharp corners ~0.1 mm (Ti)".
================================================================================================

All XY in board coords (KiCad: origin top-left, X across 50.80, Y down 88.90). Heights are datasheet
figures. Z=0 = OUTER back face; +Z into the board; raised back features go to -Z.

deps:  pip install --break-system-packages cadquery
"""
import cadquery as cq
from shapely.geometry import Point, box
from shapely.ops import unary_union

# ===== board (committed PCB) =====
W, H, R   = 50.80, 88.90, 3.0
board_th  = 0.80
mounts = [(3.0, 3.0), (47.8, 3.0), (3.0, 85.9), (47.8, 85.9)]      # 4x M2, GND, 2.2 drill -- v3.0: concentric with the r3.0 corner fillets (x-inset 3.5->3.0; matches committed PCB v3_0 MH1-4)

# ===== fixed shell knobs =====
U2_H       = 1.75                  # U2 (SOIC-8 max, datasheet): the single tallest back part
cap_H      = 1.70                  # WS17 supercaps (locked): the 2nd-tallest parts (x4) -> set the GENERAL cavity
kapton_th  = 0.00                  # DROPPED (all contacts on bare laminate). set 0.05 to reinstate.
cav_margin = 0.15                  # air over the cavity-setting parts. general cavity 1.85 = cap_H + air
cavity     = round(cap_H + kapton_th + cav_margin, 3)   # 1.85 general (cap-limited); toleranced 1.85 +-0.05 -> 1.80 min
# U2 alone is 0.05 mm taller than the caps, so a LOCAL relief pocket in the cavity floor under U2 dips
# the floor 0.05 there (local cavity 1.90) to keep U2's full 0.15 air, while the GENERAL floor runs
# 0.05 thicker for back-engraving stock. 0.05 = U2_H - cap_H is the ceiling for this trick: beyond it
# you'd have to pocket the caps (17x28.5 mm each, x4 = a second cavity). Pocket = U2 pad box + margin.
U2_POCKET    = round(U2_H - cap_H, 3)     # 0.05 mm local floor relief under U2
U2_POS       = (28.5, 37.0)               # U2 origin, board coords (committed PCB); pad box 6.8 x 4.4
U2_POCKET_WH = (7.8, 5.4)                 # pocket size: pad box + 0.5 margin all round (clears ribs/frame)

edge_fit   = -0.05                 # press interference on the FLATS
corner_clr = 0.15                  # corner relief so the press grips the flats
edge_ease  = 0.20                  # squared-edge chamfer on the outer top/bottom rim (feel/deburr)
EDGE_BREAK = 0.10                  # Ti deburr: break the sharp END-FACE edges (back proud frame/annuli
                                   # + front rim + recess mouth) so corners are durable, not knife-sharp.
                                   # Ti edges chip and cut; an edge-break also resists nicking. ~0.1 mm.
lip_w      = 1.50                  # perimeter support lip (inner) AND the back-frame width (mirror)
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
# cap-gap stiffening ribs: 1.0 mm wide in the SC1|SC2 / SC3|SC4 corridors (gap x24.0-26.8), giving
# 0.9 mm clearance EACH SIDE to the nominal cap edges (hand-placement tolerance; was 0.6). Run into
# the perimeter lip top+bottom so each rib is a SPUR off the lip (continuous pocket boundary, not a
# free-standing island) -> one roughing + boundary finish, no island plunging, and the lip tie
# stiffens the narrower wall so the span is unchanged. (Drop width to 0.8 for 1.0 mm/side if needed.)
RIBS  = [(24.9, 0.0, 25.9, 33.0), (24.9, 56.0, 25.9, 88.9)]   # (x0,y0,x1,y1)  1.0 wide, lip-tied

wx = lambda x: x - W/2
wy = lambda y: y - H/2
cavW, cavH, cavR = W + 2*edge_fit, H + 2*edge_fit, R + edge_fit

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

# ===== build =====
def build(floor=0.75, wall_th=1.0, border_h=0.15, ribs=True, braces=False, prog_window=False, glow_marker=True, tool_relief=False):
    bb = floor + cavity                       # board-back / boss-top / lip-top / rib-top plane
    wt = bb + board_th
    outW, outH, outR = cavW + 2*wall_th, cavH + 2*wall_th, cavR + wall_th
    iw, ih, ir = cavW - 2*lip_w, cavH - 2*lip_w, max(cavR - lip_w, 0.5)

    res = cq.Workplane("XY").rect(outW, outH).extrude(wt).edges("|Z").fillet(outR)
    if edge_ease > 0:
        res = res.edges(">Z").chamfer(edge_ease).edges("<Z").chamfer(edge_ease)
    # board recess (press fit) + uniform cavity (inset by lip_w)
    res = res.cut(cq.Workplane("XY").workplane(offset=bb).rect(cavW, cavH)
                    .extrude(board_th + 0.02).edges("|Z").fillet(cavR))
    res = res.cut(cq.Workplane("XY").workplane(offset=floor).rect(iw, ih)
                    .extrude(cavity).edges("|Z").fillet(ir))
    # corner relief (recess depth)
    cwp = cq.Workplane("XY").workplane(offset=bb - 0.01)
    for ccx, ccy in [(R, R), (W - R, R), (R, H - R), (W - R, H - R)]:
        cwp = cwp.moveTo(wx(ccx), wy(ccy)).circle(R + corner_clr)
    res = res.cut(cwp.extrude(board_th + 0.04))
    # INNER supports: perimeter lip
    lip = (cq.Workplane("XY").workplane(offset=floor).rect(cavW, cavH)
             .extrude(cavity).edges("|Z").fillet(cavR))
    lip = lip.cut(cq.Workplane("XY").workplane(offset=floor - 0.01).rect(iw, ih)
                    .extrude(cavity + 0.02).edges("|Z").fillet(ir))
    res = res.union(lip)
    # bosses (always) + window braces (optional; OFF by default -- ribs+lip already support U2/caps;
    # the braces only propped the window / bare-laminate spans. Removing them frees board (13.6,40.1) &
    # (39.5,40.0) for future revs. Analysis: U2 floor clearance unchanged (rib end is its support).)
    wp = cq.Workplane("XY").workplane(offset=floor)
    for x, y, rr in [(mx, my, boss_r) for mx, my in mounts] + (list(BRACE) if braces else []):
        wp = wp.moveTo(wx(x), wy(y)).circle(rr)
    res = res.union(wp.extrude(cavity))
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
    # BACK FACE: frame == lip footprint + boss annuli, raised border_h
    if border_h > 0:
        frame = (cq.Workplane("XY").workplane(offset=-border_h).rect(cavW, cavH)
                   .extrude(border_h).edges("|Z").fillet(cavR))
        frame = frame.cut(cq.Workplane("XY").workplane(offset=-border_h - 0.01).rect(iw, ih)
                            .extrude(border_h + 0.02).edges("|Z").fillet(ir))
        res = res.union(frame)
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
    # U2 relief pocket: a local 0.05 mm-deeper cavity floor under U2 (28.5,37) so U2 keeps its full
    # 0.15 mm air gap while the GENERAL floor is `floor` mm of back-engraving stock. 0.05 = U2_H-cap_H;
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
B = "solar-glow-drh-v3_0-backshell"
jobs = [
    # name                 floor wall  border ribs  prog   note
    ("Ti-max",             0.75, 1.00, 0.15, True,  False, "RECOMMENDED: 0.75 floor (back-engraving stock) + U2 0.05 relief pocket + cap-gap ribs + 1.0 walls"),
    ("Ti-max-progwindow",  0.75, 1.00, 0.15, True,  True,  "Ti-max + TC2030 re-flash window"),
]
# Ti-conservative (0.60 floor / 1.60 wall) struck: if the shop cannot hold the floor we
# re-issue to whatever minimum they will hold, so a pre-baked 0.60 fallback is dead weight.
print(f"cavity={cavity} general (cap {cap_H}+air {cav_margin}; kapton {kapton_th}); U2 pocket {U2_POCKET} deep "
      f"-> 1.90 local (U2 keeps 0.15)  lip/frame={lip_w}  "
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
