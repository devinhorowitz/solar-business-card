#!/usr/bin/env python3
"""
solar-glow-drh-backshell-cad.py  —  B-rep back-shell generator (CadQuery / OpenCASCADE)

Real-solid build so STEP carries true faces/edges (Fusion/SolidWorks editable), plus STL.
Supports reference the board BACK, so they're invariant to PCB thickness; only the wall lip
tracks `board_th`.

Raised-edge FIT: the four straight walls are run slightly UNDER the board (interference /
press fit) and the four corners are relieved so the grip lands on the flats. Lap the wall
faces with fine film to dial in a clean slip-press. Engagement = board_th, so the press is
real on the 0.8 mm board (0.8 mm of edge) and only a locator on the 0.2 mm board (lean on screws).

Builds: default (board_th 0.8, sparse 9 pillars) and 0.2 mm (auto-densified pillars).

deps:  pip install --break-system-packages cadquery
"""
import numpy as np
import cadquery as cq

# ----------------------------- parameters -----------------------------
W, H, R   = 50.8, 88.9, 3.0
wall_th   = 1.6
floor_th  = 0.6          # metal final; plastic test print -> ~1.0
cavity    = 1.6          # board-back -> floor-inner (set by SOD-123 diodes, 1.35)
edge_fit  = -0.05        # raised-edge fit on the FLATS: negative = interference (press), sand to ease (~2 thou/side)
corner_clr = 0.15        # corner relief so the four corners clear; grip stays on the flat sides
clr       = edge_fit     # drives the pocket; walls/shelf shift trivially with it
shelf_w   = 2.0
u2_skin   = 0.3
boss_r, post_r, pilot_r = 2.6, 2.6, 0.85

mounts = [(3.5, 3.0), (47.3, 3.0), (3.5, 59.0), (47.3, 59.0)]
dome   = (40.4, 11.0)
u2     = (30.0, 50.7)
pillars_sparse = [(13,11,1.25),(26,10,1.25),(19,31,1.25),(41,31,1.25),(9,44,1.25),
                  (41,44,1.25),(25.4,68,1.0),(16,84,1.25),(35,84,1.25)]

cavW, cavH, cavR = W + 2*clr, H + 2*clr, R + clr
outW, outH, outR = cavW + 2*wall_th, cavH + 2*wall_th, cavR + wall_th
innerW, innerH = cavW - 2*shelf_w, cavH - 2*shelf_w
wx = lambda x: x - W/2
wy = lambda y: y - H/2

KEEP_RECT = [(30,50.7,5.5,5.0),(15.5,67.5,9.5,15.7),(35.3,67.5,9.5,15.7),(11.5,27,2.5,2.5),
             (30,35.5,3.0,1.8),(25.4,76,3.0,1.8),(25.4,70,3.0,1.8),(9.3,24,2.0,1.5),
             (14.5,50.5,1.8,1.3),(6.6,27,3.0,2.5),(38,26,3.0,2.5),(25.4,45,9.0,2.0)]
KEEP_CIRC = [(40.4,11,4.5)] + [(mx,my,4.5) for mx,my in mounts]

def auto_pillars(spacing=9.0, r=1.1):
    ix0, ix1 = W/2 - innerW/2 + 1, W/2 + innerW/2 - 1
    iy0, iy1 = H/2 - innerH/2 + 1, H/2 + innerH/2 - 1
    pts = []
    for x in np.arange(ix0, ix1 + 1e-6, spacing):
        for y in np.arange(iy0, iy1 + 1e-6, spacing):
            if any(abs(x-cx) < hw and abs(y-cy) < hh for cx,cy,hw,hh in KEEP_RECT): continue
            if any((x-cx)**2 + (y-cy)**2 < cr*cr for cx,cy,cr in KEEP_CIRC):       continue
            pts.append((float(x), float(y), r))
    return pts

def build(board_th, pillars, window=False):
    board_back = floor_th + cavity
    wall_top   = board_back + board_th
    res = cq.Workplane("XY").rect(outW, outH).extrude(wall_top).edges("|Z").fillet(outR)
    # board recess (top) — interference on the flats
    res = res.cut(cq.Workplane("XY").workplane(offset=board_back).rect(cavW, cavH)
                  .extrude(board_th).edges("|Z").fillet(cavR))
    # corner relief: clear the 4 board corners so the press grips the flats, not the corners
    cwp = cq.Workplane("XY").workplane(offset=board_back - 0.01)
    for ccx, ccy in [(R, R), (W - R, R), (R, H - R), (W - R, H - R)]:
        cwp = cwp.moveTo(wx(ccx), wy(ccy)).circle(R + corner_clr)
    res = res.cut(cwp.extrude(board_th + 0.02))
    # component cavity (deeper, inside the shelf)
    res = res.cut(cq.Workplane("XY").workplane(offset=floor_th).rect(innerW, innerH)
                  .extrude(cavity).edges("|Z").fillet(max(cavR - shelf_w, 0.6)))
    # supports (bosses + dome post + pillars)
    sup = list(pillars) + [(dome[0], dome[1], post_r)] + [(mx, my, boss_r) for mx, my in mounts]
    wp = cq.Workplane("XY").workplane(offset=floor_th)
    for x, y, rr in sup:
        wp = wp.moveTo(wx(x), wy(y)).circle(rr)
    res = res.union(wp.extrude(cavity))
    # U2: pocket (skin) or window (flush)
    if window:
        res = res.cut(cq.Workplane("XY").moveTo(wx(u2[0]), wy(u2[1])).rect(8, 7).extrude(wall_top))
    else:
        res = res.cut(cq.Workplane("XY").workplane(offset=u2_skin).moveTo(wx(u2[0]), wy(u2[1]))
                      .rect(8, 7).extrude(floor_th - u2_skin + 0.5))
    # blind M2 pilots (from the cavity side)
    wp2 = cq.Workplane("XY").workplane(offset=u2_skin)
    for mx, my in mounts:
        wp2 = wp2.moveTo(wx(mx), wy(my)).circle(pilot_r)
    res = res.cut(wp2.extrude(board_back - u2_skin + 0.01))
    return res

OUT = "/mnt/user-data/outputs/"
jobs = [("solar-glow-drh-backshell",        0.8, pillars_sparse),
        ("solar-glow-drh-backshell-0p2mm",  0.2, auto_pillars())]
for name, bt, pil in jobs:
    solid = build(bt, pil)
    cq.exporters.export(solid, OUT + name + ".step")
    cq.exporters.export(solid, OUT + name + ".stl", tolerance=0.04, angularTolerance=0.2)
    print(f"{name}: board_th={bt}  edge_fit={edge_fit}  corner_clr={corner_clr}  pillars={len(pil)}")
print("done")
