#!/usr/bin/env python3
"""
solar-glow-drh-v2_1-backshell-cad.py  -  metal back-shell generator (CadQuery / OpenCASCADE)

Built to the as-built `solar-glow-drh-v2-mechanical.md` (from the committed PCB). v2.1 drops the
U2 pocket, SC pockets, edge castellations, and the button (brief sec.8).

================================================================================================
TITANIUM LIMIT-PUSH (this revision). Final part is Ti-6Al-4V; the audit re-derived every dimension
against datasheet heights + plate mechanics. Findings that drove the numbers below:

  * Cavity is PART-limited, not a lever: U2 (SOIC-8, datasheet max 1.75) and the WS17 caps (1.70,
    locked) set it. Cavity 1.85 = 1.75 + 0.10 air. Cannot shrink without shorter parts.
  * The floor is the lever, and Ti YIELD is never the limit -- a 0.2 mm Ti floor stays sub-yield
    even at a hard 50 N press. The binding limit is the floor DEFLECTING into the parts (air gap
    0.10 mm to U2, 0.15 mm to the caps).
  * The old lip-only-plus-window-braces left a 19.5 mm-radius UNSUPPORTED floor disk over the cap
    regions; at that span a 0.6 mm floor already TOUCHES a cap at 50 N (needs 0.62). So the prior
    floor was marginal.
  * FIX = stiffen the floor with continuous RIBS in the empty cap-gap corridors (the SC1|SC2 and
    SC3|SC4 channels, x 24.6-26.2, on bare laminate, no pads/vias). With the ribs + the 4 window
    braces the worst span drops to 11.6 mm -> a 0.45 mm Ti floor is 50 N-safe. THINNER AND STRONGER.
  * Kapton DROPPED: every metal contact (lip in the pad-free rim band, 4 braces, 2 ribs) sits on
    bare laminate -- verified against the PCB -- so the blanket is unnecessary. (Keep a die-cut
    Kapton strip only if a via audit on the rib lines later finds an untented via.)
  * Walls 1.6 -> 1.0 mm: Ti is plenty strong for a press-fit rim on a 0.8 mm FR4 edge; shrinks the
    footprint from 53.9 to 52.8 mm (closer to the 50.8 card).

  Ti-max stack: floor 0.45 + cavity 1.85 + board 0.80 = 3.10 mm field (3.20 at the back frame),
  vs the conservative 3.25. M2 thread is screw-limited, not Ti-limited (2.6 mm of engagement).

BACK FACE = metal rubbing of the interior: 4 screw posts drilled CLEAN THROUGH, a raised frame that
mirrors the inner lip (PCB-perimeter footprint + width), and the bosses as raised annuli fused to
the frame the way the inner bosses fuse to the lip; all raised `border_h` so engraved rear art in
the recessed field takes no wear.
================================================================================================

All XY in board coords (KiCad: origin top-left, X across 50.80, Y down 88.90). Heights are datasheet
figures. Z=0 = OUTER back face; +Z into the board; raised back features go to -Z.

deps:  pip install --break-system-packages cadquery
"""
import cadquery as cq

# ===== board (committed PCB) =====
W, H, R   = 50.80, 88.90, 3.0
board_th  = 0.80
mounts = [(3.5, 3.0), (47.3, 3.0), (3.5, 85.9), (47.3, 85.9)]      # 4x M2, GND, 2.2 mm drill

# ===== fixed shell knobs =====
U2_H       = 1.75                  # tallest back part (SOIC-8 max, datasheet) -> sets the cavity
kapton_th  = 0.00                  # DROPPED (all contacts on bare laminate). set 0.05 to reinstate.
cav_margin = 0.10                  # air over the tallest part
cavity     = round(U2_H + kapton_th + cav_margin, 3)   # 1.85

edge_fit   = -0.05                 # press interference on the FLATS
corner_clr = 0.15                  # corner relief so the press grips the flats
edge_ease  = 0.20                  # squared-edge chamfer (feel/deburr)
lip_w      = 1.50                  # perimeter support lip (inner) AND the back-frame width (mirror)
boss_r     = 2.60                  # M2 boss / back annulus outer radius
pilot_r    = 0.80                  # M2 thread-forming hole, CLEAN THROUGH

# window braces (disk clears the glow window + every back pad; from the PCB):
# window braces: E + W flank the optical-window keepout (between side lip and window edge).
# NE(35,37) + SW(19.2,50.9) were REDUNDANT once the ribs went in (worst span 11.6 either way) -> removed.
BRACE = [(39.5,40.0,1.0),(13.6,40.1,1.0)]   # E, W
# cap-gap stiffening ribs: 1.0 mm wide in the SC1|SC2 / SC3|SC4 corridors (gap x24.0-26.8), giving
# 0.9 mm clearance EACH SIDE to the nominal cap edges (hand-placement tolerance; was 0.6). Run into
# the perimeter lip top+bottom so each rib is a SPUR off the lip (continuous pocket boundary, not a
# free-standing island) -> one roughing + boundary finish, no island plunging, and the lip tie
# stiffens the narrower wall so the span is unchanged. (Drop width to 0.8 for 1.0 mm/side if needed.)
RIBS  = [(24.9, 0.0, 25.9, 33.0), (24.9, 56.0, 25.9, 88.9)]   # (x0,y0,x1,y1)  1.0 wide, lip-tied

wx = lambda x: x - W/2
wy = lambda y: y - H/2
cavW, cavH, cavR = W + 2*edge_fit, H + 2*edge_fit, R + edge_fit

# ===== build =====
def build(floor=0.45, wall_th=1.0, border_h=0.10, ribs=True, prog_window=False):
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
    # bosses + window braces (full-cavity columns)
    wp = cq.Workplane("XY").workplane(offset=floor)
    for x, y, rr in [(mx, my, boss_r) for mx, my in mounts] + list(BRACE):
        wp = wp.moveTo(wx(x), wy(y)).circle(rr)
    res = res.union(wp.extrude(cavity))
    # cap-gap ribs (full-cavity walls; also prop the board along the corridor)
    if ribs:
        for x0, y0, x1, y1 in RIBS:
            res = res.union(cq.Workplane("XY").workplane(offset=floor)
                              .moveTo(wx((x0+x1)/2), wy((y0+y1)/2)).rect(x1-x0, y1-y0).extrude(cavity))
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
    # M2 holes CLEAN THROUGH (boss + skin + back annulus)
    twp = cq.Workplane("XY").workplane(offset=-border_h - 0.1)
    for mx, my in mounts:
        twp = twp.moveTo(wx(mx), wy(my)).circle(pilot_r)
    res = res.cut(twp.extrude(bb + border_h + 0.2))
    if prog_window:
        res = res.cut(cq.Workplane("XY").workplane(offset=-border_h - 0.1)
                        .moveTo(wx(13.3), wy(16.9)).circle(5.5).extrude(floor + border_h + 0.2))
    return res

# ===== variants (titanium only; 7075 retired -- final part is Ti) =====
OUT = "/mnt/user-data/outputs/"
B = "solar-glow-drh-v2_1-backshell"
jobs = [
    # name                 floor wall  border ribs  prog   note
    ("Ti-max",             0.45, 1.00, 0.10, True,  False, "RECOMMENDED: 0.45 floor + cap-gap ribs + 1.0 walls"),
    ("Ti-max-progwindow",  0.45, 1.00, 0.10, True,  True,  "Ti-max + TC2030 re-flash window"),
    ("Ti-conservative",    0.60, 1.60, 0.15, False, False, "prior build, no ribs (reference / safety)"),
]
print(f"cavity={cavity} (U2 {U2_H} + air {cav_margin}; kapton {kapton_th})  lip/frame={lip_w}  braces={len(BRACE)} ribs={len(RIBS)}")
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
