#!/usr/bin/env python3
"""
solar-glow-drh-v2_1-backshell-cad.py  -  metal back-shell generator (CadQuery / OpenCASCADE)

REDESIGN of the stale pre-v2.1 shell, built to the as-built `solar-glow-drh-v2-mechanical.md`
(distilled from the committed `solar-glow-drh-v2_1.kicad_pcb`). v2.1 drops the U2 pocket, the SC
pockets, the edge-castellation relief, and the button (mechanical brief sec.8).

------------------------------------------------------------------------------------------------
SUPPORT + FINISH:

  EDGE SUPPORT = a CONTINUOUS PERIMETER LIP (`lip_w` 1.5 mm) that rings the inside of the cavity and
  joins all four M2 bosses -> the board is fully edge-supported, not corner-supported, and it is one
  contour pass to mill. The lip sits inside the pad-free 1.5 mm rim band (brief sec.8): never on a
  pad, clears the nearest body (supercaps, 2.65 mm from the rim) by >1 mm.

  CENTER ANTI-TRAMPOLINE = four brace pillars ringing the glow window. Sec.7 forbids pillars on the
  LED pads / monogram (the window), so dead-center is out; these were found by scanning the committed
  back copper for points whose full r=1.0 disk clears BOTH the window and every pad, and bracket it
  N/E/S/W (clearances 1.5-3.7 mm). The lip carries the rest of the span.

  CORNERS / EDGES = R3 plan corners (match the PCB); edges SQUARED + a 0.20 mm `edge_ease`. A true
  3 mm vertical radius on a ~3.25 mm edge is a full bullnose -> egg, not flat -> squared is correct.

  BACK FACE = a literal metal "rubbing" of the interior structure (`echoes the interior machining`):
    * the 4 M2 screw posts drill CLEAN THROUGH (boss + skin + back annulus) -> 4 holes on the back;
    * a raised back FRAME that MIRRORS the inner lip exactly -- same footprint (PCB perimeter) and
      same width (`lip_w`) -- a literal representation of the card outline in metal;
    * the 4 bosses rendered on the back as raised annuli (outer r = `boss_r`, the screw hole through
      the centre), fused into the back frame THE SAME WAY the inner bosses fuse into the inner lip;
    * all raised `border_h` (0.15 mm) proud, so the central field is recessed -> engraved rear art
      lives in the field and the raised frame/bosses take the wear when the card is set down/stacked.

ISOLATION (sec.9): the 4 M2 screws ground the body; with castellations gone the only short hazard is
the lip/pillars on the back. Default = die-cut Kapton (~0.05 mm); cavity swallows it. The lip is also
inside the pad-free band, so safe even without Kapton.
PROGRAMMING (sec.10): default flash-before-close; `PROG_WINDOW` opens a TC2030 hole in the field.

All XY in board coords (KiCad frame: origin top-left, X across 50.80, Y down 88.90). Heights are
datasheet figures. Z=0 = OUTER back face; +Z into the board; the raised back features go to -Z.

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

lip_w      = 1.50                  # perimeter support lip (inner) AND the back frame width (they mirror)
boss_r     = 2.60                  # M2 boss radius (inner post AND the back annulus outer radius)
pilot_r    = 0.80                  # M2 thread-forming hole (~1.6 mm), now CLEAN THROUGH the boss+skin
border_h   = 0.15                  # raised height of the back frame + back boss annuli

# brace pillars ringing the glow window (disk clears the window + every back-side pad; from the PCB):
BRACE_PILLARS = [(35.0, 37.0, 1.0),    # NE of window  (clr 2.93)
                 (39.5, 40.0, 1.0),    # E  of window  (clr 3.69)
                 (19.2, 50.9, 1.0),    # SW of window  (clr 2.32)
                 (13.6, 40.1, 1.0)]    # W  of window  (clr 1.50)

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
    # 4) INNER supports (after the cuts): perimeter lip + 4 bosses + window braces, all floor->bb
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
    # 5) BACK FACE structure (mirror of the interior): frame == lip footprint, + boss annuli
    if border_h > 0:
        # frame: raised ring at the PCB perimeter, width lip_w (exact mirror of the inner lip)
        frame = (cq.Workplane("XY").workplane(offset=-border_h).rect(cavW, cavH)
                   .extrude(border_h).edges("|Z").fillet(cavR))
        frame = frame.cut(cq.Workplane("XY").workplane(offset=-border_h - 0.01).rect(iw, ih)
                            .extrude(border_h + 0.02).edges("|Z").fillet(ir))
        res = res.union(frame)
        # boss annuli on the back: raised disks r=boss_r at the mounts (holes cut in step 6)
        bwp = cq.Workplane("XY").workplane(offset=-border_h)
        for mx, my in mounts:
            bwp = bwp.moveTo(wx(mx), wy(my)).circle(boss_r)
        res = res.union(bwp.extrude(border_h))
    # 6) M2 holes drilled CLEAN THROUGH: boss + skin + back annulus, in one cut
    twp = cq.Workplane("XY").workplane(offset=-border_h - 0.1)
    for mx, my in mounts:
        twp = twp.moveTo(wx(mx), wy(my)).circle(pilot_r)
    res = res.cut(twp.extrude(bb + border_h + 0.2))
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
print(f"cavity={cavity}  lip_w={lip_w}  edge_ease={edge_ease}  back-frame=mirror(lip)  border_h={border_h}  thru-holes=ON")
for suf, floor, pw, note in jobs:
    solid = build(floor, prog_window=pw)
    field = floor + cavity + board_th
    name = f"{B}-{suf}"
    cq.exporters.export(solid, OUT + name + ".step")
    cq.exporters.export(solid, OUT + name + ".stl", tolerance=0.04, angularTolerance=0.2)
    print(f"  {name:38s} floor={floor:.2f}  field={field:.2f}  at-frame={field+border_h:.2f} mm  "
          f"progwin={pw}  | {note}")
print("done")
