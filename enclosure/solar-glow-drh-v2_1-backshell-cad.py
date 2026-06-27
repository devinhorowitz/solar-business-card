#!/usr/bin/env python3
"""
solar-glow-drh-v2_1-backshell-cad.py  -  metal back-shell generator (CadQuery / OpenCASCADE)

REDESIGN of the stale pre-v2.1 shell, built to the as-built `solar-glow-drh-v2-mechanical.md`
(distilled from the committed `solar-glow-drh-v2_1.kicad_pcb`). See sec.8 of that brief for the
deltas. v2.1 drops the U2 pocket, the SC pockets, the edge-castellation relief, and the button.

------------------------------------------------------------------------------------------------
REV-B support + finish changes (this revision):

  EDGE SUPPORT = a CONTINUOUS PERIMETER LIP, not scattered edge pillars. A `lip_w` (1.5 mm) ledge
  rings the inside of the cavity and joins all four M2 bosses, so EVERY section of the board edge
  is seated, the board goes from corner-supported to fully edge-supported (far stiffer center
  deflection), and it is one contour pass to mill instead of many plunged posts. The lip sits inside
  the pad-free 1.5 mm rim band (mechanical brief sec.8), so it never lands on a pad and clears the
  nearest body (top/bottom supercaps at 2.65 mm from the rim) by >1 mm.

  CENTER ANTI-TRAMPOLINE = brace pillars ringing the glow window. The window panel is the most
  flex-prone span, but sec.7 forbids pillars on the LED pads / monogram (x 15-36 / y 40.8-47). The
  four `BRACE_PILLARS` below were found by scanning the committed back-side copper for points whose
  full r=1.0 disk clears BOTH the glow window and every pad; each ended up with >=1.5 mm clearance.
  They cannot sit dead-center (the window blocks it); they bracket it N/E/S/W as close as the
  keepout allows, and the lip carries the rest.

  CORNERS / EDGE PROFILE = R3 plan corners kept (to match the PCB outline); edges SQUARED with a
  small `edge_ease` chamfer (0.20 mm) for feel/deburr. A true 3 mm radius rolled into the ~3.25 mm
  thickness is geometrically a near-full bullnose (one R3 round-over eats 3.0 of 3.25 mm) -> egg
  shaped, the opposite of the "flat like a business card" goal -> squared is the right call.

  BACK BORDER = a raised perimeter frame on the outer (visible) back face, `border_h` (0.15 mm)
  proud, `border_w` (1.0 mm) wide, following the rounded outline. Two jobs: (1) front/back symmetry
  -- it echoes the front soldermask edge frame; (2) a wear standoff -- rear art is engraved into the
  recessed central field, so the raised border (not the art) takes contact when the card is set
  down or stacked.
------------------------------------------------------------------------------------------------

ISOLATION (brief sec.9): the 4 M2 screws tie the body to GND; with castellations gone the only
short hazard is the lip/pillars on the back. Default = die-cut Kapton (~0.05 mm) blanket; cavity
swallows it. The lip also lands inside the pad-free band, so it is safe even without Kapton.
PROGRAMMING (brief sec.10): default = flash-before-close; `PROG_WINDOW` opens a TC2030 hole.

All XY in board coords (KiCad frame: origin top-left, X across 50.80, Y down 88.90). Heights are
datasheet figures. Z=0 = OUTER back face; +Z into the board.

deps:  pip install --break-system-packages cadquery
"""
import numpy as np
import cadquery as cq

# =============================== board (read from the committed PCB) ===============================
W, H, R   = 50.80, 88.90, 3.0
board_th  = 0.80
mounts = [(3.5, 3.0), (47.3, 3.0), (3.5, 85.9), (47.3, 85.9)]      # 4x M2, GND, 2.2 mm drill

# =============================== shell knobs ===============================
U2_H       = 1.75                  # tallest back part (SOIC-8 balancer) -> sets the cavity
kapton_th  = 0.05                  # isolation blanket (assembly spec; cavity swallows it). 0 => none.
cav_margin = 0.05
cavity     = round(U2_H + kapton_th + cav_margin, 3)   # ~1.85 (== brief's "~1.8")

floor_th   = 0.60                  # outer-skin thickness (Ti std 0.6 / thin 0.2; 7075 bumps it)
wall_th    = 1.60                  # press-fit wall thickness (rings the board edge)
edge_fit   = -0.05                 # interference on the FLATS
corner_clr = 0.15                  # corner relief so the press grips the flats, not the corners
edge_ease  = 0.20                  # squared-edge chamfer (feel/deburr). 0 => dead square.

lip_w      = 1.50                  # continuous perimeter support lip (joins the bosses)
boss_r     = 2.60                  # M2 boss radius (top annulus > the 2.2 mm board hole)
pilot_r    = 0.80                  # M2 thread-forming pilot, tapped from the boss top
skin_keep  = 0.20                  # floor left under the pilot so it never pierces the back skin

# brace pillars ringing the glow window (disk clears the window + every back-side pad; from the PCB):
BRACE_PILLARS = [(35.0, 37.0, 1.0),    # NE of window  (clr 2.93)
                 (39.5, 40.0, 1.0),    # E  of window  (clr 3.69)
                 (19.2, 50.9, 1.0),    # SW of window  (clr 2.32)
                 (13.6, 40.1, 1.0)]    # W  of window  (clr 1.50)

# back-face raised border (wear standoff + front/back symmetry):
border_h, border_w, border_inset = 0.15, 1.0, 0.30

# =============================== derived geometry ===============================
cavW, cavH, cavR = W + 2*edge_fit, H + 2*edge_fit, R + edge_fit
outW, outH, outR = cavW + 2*wall_th, cavH + 2*wall_th, cavR + wall_th
wx = lambda x: x - W/2
wy = lambda y: y - H/2

# =============================== build ===============================
def build(floor, prog_window=False, brace=BRACE_PILLARS):
    bb = floor + cavity                 # board-back / boss-top / lip-top plane
    wt = bb + board_th                  # wall top (flush with the naked front)

    # 1) outer prism; vertical edges -> outR plan corners; top+bottom outer edges -> squared ease
    res = cq.Workplane("XY").rect(outW, outH).extrude(wt).edges("|Z").fillet(outR)
    if edge_ease > 0:
        res = res.edges(">Z").chamfer(edge_ease)     # front rim outer edge
        res = res.edges("<Z").chamfer(edge_ease)     # back outer edge
    # 2a) board recess (full width, press fit on the flats) -- the top board_th
    res = res.cut(cq.Workplane("XY").workplane(offset=bb)
                    .rect(cavW, cavH).extrude(board_th + 0.02).edges("|Z").fillet(cavR))
    # 2b) component cavity (inset by lip_w -> leaves the lip) -- depth `cavity` from the floor
    iw, ih, ir = cavW - 2*lip_w, cavH - 2*lip_w, max(cavR - lip_w, 0.5)
    res = res.cut(cq.Workplane("XY").workplane(offset=floor)
                    .rect(iw, ih).extrude(cavity).edges("|Z").fillet(ir))
    # 3) corner relief over the recess depth so the board corners are not gripped
    cwp = cq.Workplane("XY").workplane(offset=bb - 0.01)
    for ccx, ccy in [(R, R), (W - R, R), (R, H - R), (W - R, H - R)]:
        cwp = cwp.moveTo(wx(ccx), wy(ccy)).circle(R + corner_clr)
    res = res.cut(cwp.extrude(board_th + 0.04))
    # 4) supports (added AFTER the cuts): perimeter lip + 4 bosses + window braces, all floor->bb
    lip = (cq.Workplane("XY").workplane(offset=floor).rect(cavW, cavH)
             .extrude(cavity).edges("|Z").fillet(cavR))
    lip = lip.cut(cq.Workplane("XY").workplane(offset=floor - 0.01).rect(iw, ih)
                    .extrude(cavity + 0.02).edges("|Z").fillet(ir))
    res = res.union(lip)
    sup = [(mx, my, boss_r) for mx, my in mounts] + list(brace)
    wp = cq.Workplane("XY").workplane(offset=floor)
    for x, y, rr in sup:
        wp = wp.moveTo(wx(x), wy(y)).circle(rr)
    res = res.union(wp.extrude(cavity))
    # 5) blind M2 pilots, tapped from the boss top down; never pierces the back skin
    pilot_depth = cavity + max(floor - skin_keep, 0.0)
    wp2 = cq.Workplane("XY").workplane(offset=bb - pilot_depth)
    for mx, my in mounts:
        wp2 = wp2.moveTo(wx(mx), wy(my)).circle(pilot_r)
    res = res.cut(wp2.extrude(pilot_depth))
    # 6) raised back border on the outer face (z=0), rising out the back (-Z)
    if border_h > 0:
        bo_w, bo_h, bo_r = outW - 2*border_inset, outH - 2*border_inset, outR - border_inset
        bi_w, bi_h, bi_r = bo_w - 2*border_w, bo_h - 2*border_w, max(bo_r - border_w, 0.5)
        frame = (cq.Workplane("XY").workplane(offset=-border_h).rect(bo_w, bo_h)
                   .extrude(border_h).edges("|Z").fillet(bo_r))
        frame = frame.cut(cq.Workplane("XY").workplane(offset=-border_h - 0.01).rect(bi_w, bi_h)
                            .extrude(border_h + 0.02).edges("|Z").fillet(bi_r))
        res = res.union(frame)
    # 7) optional TC2030 re-flash window through the back skin over TC1
    if prog_window:
        res = res.cut(cq.Workplane("XY").workplane(offset=-border_h - 0.1)
                        .moveTo(wx(13.3), wy(16.9)).circle(5.5).extrude(floor + border_h + 0.2))
    return res

# =============================== variants ===============================
OUT = "/mnt/user-data/outputs/"
B = "solar-glow-drh-v2_1-backshell"
jobs = [
    ("Ti-std",            0.60, False, "Ti-6Al-4V, standard 0.6 skin"),
    ("Ti-thin",           0.20, False, "Ti-6Al-4V, thin 0.2 skin"),
    ("7075-std",          0.80, False, "7075-T6, bumped 0.8 skin"),
    ("Ti-std-progwindow", 0.60, True,  "Ti-6Al-4V std + TC2030 re-flash window"),
]
print(f"cavity={cavity}  lip_w={lip_w}  edge_ease={edge_ease}  border={border_h}x{border_w}mm")
for suf, floor, pw, note in jobs:
    solid = build(floor, prog_window=pw)
    field = floor + cavity + board_th
    name = f"{B}-{suf}"
    cq.exporters.export(solid, OUT + name + ".step")
    cq.exporters.export(solid, OUT + name + ".stl", tolerance=0.04, angularTolerance=0.2)
    print(f"  {name:38s} floor={floor:.2f}  field={field:.2f}  at-border={field+border_h:.2f} mm  "
          f"progwin={pw}  | {note}")
print("done")
