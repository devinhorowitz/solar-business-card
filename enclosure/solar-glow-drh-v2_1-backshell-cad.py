#!/usr/bin/env python3
"""
solar-glow-drh-v2_1-backshell-cad.py  —  metal back-shell generator (CadQuery / OpenCASCADE)

REDESIGN of solar-glow-drh-backshell-cad.py for the as-built v2.1 board. The old file is STALE
(single supercap pair, U2 floor pocket, right-edge castellations, QFN-20, snap-dome button); none
of that exists on v2.1. This is a ground-up re-lay-out against `solar-glow-drh-v2-mechanical.md`,
which is itself pulled from the committed `solar-glow-drh-v2_1.kicad_pcb`. The CadQuery
scaffolding (parameter block, boss generation, corner fillet, press-fit walls) is reused; the
geometry/pockets/pillar-map are rebuilt.

WHAT THE v2.1 REDESIGN DROPS vs the old shell (mechanical brief sec.8):
  - U2 floor pocket .......... GONE. U2 (1.75) ~= the supercaps (1.7) -> ONE uniform cavity clears
                               everything, no local thin skin, no `u2_skin`, no `WINDOW_U2`.
  - SC pockets ............... GONE. Old 1.6 cavity was diode-set and under the 1.7 caps, so caps
                               needed pockets. New cavity clears the caps directly -> flat floor.
  - edge-castellation relief . GONE. Verified zero pads within 1.5 mm of the rim -> walls press
                               bare FR4, no wall-short, no enclosed-variant edge-bus drop.
  - snap-dome button + post .. GONE. Actuator is the accel tap (the metal back transmits it) ->
                               no dome post, no button hole, no cap-touch window.
  - perimeter seating shelf .. GONE. Board seats on the boss + pillar tops (deterministic Z),
                               located in X-Y by the press-fit walls. One pocket, not recess+shelf.

ISOLATION (mechanical brief sec.9): the 4 M2 screws tie the body to GND, so any non-GND copper the
metal touches is a short. With castellations gone, the only remaining hazard is support pillars on
the back. Default fix here = a die-cut **Kapton (~0.05 mm) blanket** between board-back and shell
(brief's "simplest fix"); the cavity is sized to swallow it. Pillars then land for floor stiffness
only, in component-free zones, and are electrically safe regardless of the pour beneath. (Alt: skip
Kapton and audit pillar landings onto GND pour only — left as a knob, not the default.)

PROGRAMMING (mechanical brief sec.10): TC2030 pads (TC1) are back-side at (13.3,16.9). Default =
**flash before closing** (pads sit in the dead space beside SC1; nothing to cut). `PROG_WINDOW`
opens a back-shell hole over TC1 for field re-flash, at the cost of a skin penetration.

All XY in board coordinates (KiCad frame: origin top-left, X across 50.80 width, Y down 88.90
length). Heights are datasheet figures for the populated parts. Z=0 is the OUTER (visible) face of
the back skin; +Z goes into the board.

deps:  pip install --break-system-packages cadquery
"""
import numpy as np
import cadquery as cq

# =============================== board (read from the committed PCB) ===============================
W, H, R   = 50.80, 88.90, 3.0      # envelope + corner radius (Edge.Cuts; bbox + R confirmed)
board_th  = 0.80                   # FR4 thickness (fixed; the 0.2 mm-board variant is retired)

# --- the four M2 mounts, all on GND, 2.2 mm drilled (confirmed from the PCB) ---
mounts = [(3.5, 3.0), (47.3, 3.0), (3.5, 85.9), (47.3, 85.9)]

# =============================== shell knobs ===============================
# height stack: ONLY U2 (1.75) and the supercaps (1.7) drive the cavity. Everything else clears.
U2_H       = 1.75                  # tallest back part, SOIC-8 balancer (datasheet)
kapton_th  = 0.05                  # die-cut isolation blanket (assembly spec; not metal, but the
                                   #   cavity swallows it). 0.0 => no Kapton (then pillars MUST land
                                   #   on GND pour only -- audit before trusting).
cav_margin = 0.05                  # air over the tallest part after Kapton
cavity     = round(U2_H + kapton_th + cav_margin, 3)   # board-back -> floor-inner ; ~1.85 (== "~1.8")

floor_th   = 0.60                  # outer-skin thickness (the visible back). Ti std 0.6 / thin 0.2;
                                   #   7075 wants this bumped (see variants).
wall_th    = 1.60                  # press-fit wall thickness (rings the board edge)
edge_fit   = -0.05                 # interference on the FLATS: negative = press; lap to ease
corner_clr = 0.15                  # corner relief so the grip lands on the flats, not the corners

boss_r     = 2.60                  # M2 boss radius (top annulus > the 2.2 mm board hole -> board rests on it)
pilot_r    = 0.80                  # M2 thread-forming pilot (~1.6 mm) tapped from the boss top
skin_keep  = 0.20                  # blind floor left under the pilot so it never pierces the back skin
pillar_r   = 1.00                  # default support-pillar radius

# =============================== pillar keepout map (board coords) ===============================
# circles: keep pillars off the mount bosses
KEEP_CIRC = [(mx, my, 3.0) for mx, my in mounts]
# rects: (cx, cy, half_w, half_h) -- part bodies pillars must not land on.
KEEP_RECT = [
    # supercaps: 4x 17(X) x 28.5(Y), long axis along the 88.9 length, +~1 mm margin
    (15.5, 16.9, 9.0, 14.6), (35.3, 16.9, 9.0, 14.6),     # SC1, SC2 (top pair)
    (15.5, 72.0, 9.0, 14.6), (35.3, 72.0, 9.0, 14.6),     # SC3, SC4 (bottom pair)
    # central electronics band
    (28.5, 37.0, 3.5, 3.0),                               # U2 balancer SOIC-8
    ( 9.5, 40.9, 3.0, 3.0),                               # U1 MCU VQFN-28
    (20.0, 35.9, 2.0, 2.0),                               # U3 accel LGA-12
    (13.3, 16.9, 5.0, 5.0),                               # TC1 program pads + NPTH legs
    ( 4.7, 38.4, 3.0, 3.0),                               # J1 UPDI backup pads
    (42.5, 49.0, 5.0, 7.0),                               # clamp block: D1 / D9 / U4 / Q1 / R7-9 / C7
    # OPTICAL no-pillar keepout (brief sec.7): LED row D2-D5 + DRH monogram window. HARD.
    (25.4, 43.5, 11.0, 4.0),                              # x 14.4-36.4, y 39.5-47.5
    # selectors / passive leftovers in the band
    (24.0, 49.0, 6.0, 3.0),                               # SW2 + SB1-4 row
    (15.5, 33.0, 3.5, 2.5),                               # R10/R11 + JP1
    (13.3, 46.0, 2.5, 2.5),                               # SJ1 / C3
]

# Sparse default supports: 4 mid-edge pillars in the supercap Y-bands' edge margins -- confidently
# clear of every part and of the optical zone, and they split the long unsupported floor spans.
PILLARS_SPARSE = [(4.0, 16.0, pillar_r), (47.0, 16.0, pillar_r),
                  (4.0, 73.0, pillar_r), (47.0, 73.0, pillar_r)]

# =============================== derived geometry ===============================
cavW, cavH, cavR = W + 2*edge_fit, H + 2*edge_fit, R + edge_fit       # press-fit pocket (board fits here)
outW, outH, outR = cavW + 2*wall_th, cavH + 2*wall_th, cavR + wall_th  # outer prism
board_back = floor_th + cavity                                        # z of the board-back / boss-top plane
wall_top   = board_back + board_th                                    # walls flush with the naked front
wx = lambda x: x - W/2                                                # board-XY -> CadQuery-centered XY
wy = lambda y: y - H/2

def auto_pillars(spacing=8.5, r=0.9, inset=2.0):
    """Grid the floor, drop a pillar wherever it clears every keepout. Used for the thin-skin build."""
    ix0, ix1 = inset, W - inset
    iy0, iy1 = inset, H - inset
    pts = []
    for x in np.arange(ix0, ix1 + 1e-6, spacing):
        for y in np.arange(iy0, iy1 + 1e-6, spacing):
            if any(abs(x-cx) < hw and abs(y-cy) < hh for cx, cy, hw, hh in KEEP_RECT): continue
            if any((x-cx)**2 + (y-cy)**2 < cr*cr for cx, cy, cr in KEEP_CIRC):         continue
            pts.append((float(x), float(y), r))
    return pts

# =============================== build ===============================
def build(floor, pillars, prog_window=False):
    bb = floor + cavity                 # board-back plane for THIS floor
    wt = bb + board_th                  # wall top (flush with front)
    # outer prism, vertical edges filleted
    res = (cq.Workplane("XY").rect(outW, outH).extrude(wt)
             .edges("|Z").fillet(outR))
    # ONE pocket: board recess (top board_th, press fit on the flats) + the uniform cavity below it.
    res = res.cut(cq.Workplane("XY").workplane(offset=floor)
                    .rect(cavW, cavH).extrude(cavity + board_th)
                    .edges("|Z").fillet(cavR))
    # corner relief: clear the 4 board corners so the press grips the flats, not the corners
    cwp = cq.Workplane("XY").workplane(offset=floor - 0.01)
    for ccx, ccy in [(R, R), (W - R, R), (R, H - R), (W - R, H - R)]:
        cwp = cwp.moveTo(wx(ccx), wy(ccy)).circle(R + corner_clr)
    res = res.cut(cwp.extrude(cavity + board_th + 0.02))
    # supports: 4 M2 bosses + pillars, all rising the FULL cavity to the board-back plane
    sup = [(mx, my, boss_r) for mx, my in mounts] + list(pillars)
    wp = cq.Workplane("XY").workplane(offset=floor)
    for x, y, rr in sup:
        wp = wp.moveTo(wx(x), wy(y)).circle(rr)
    res = res.union(wp.extrude(cavity))
    # blind M2 pilots, tapped from the boss top downward; never pierces the back skin
    pilot_depth = cavity + max(floor - skin_keep, 0.0)
    wp2 = cq.Workplane("XY").workplane(offset=bb - pilot_depth)
    for mx, my in mounts:
        wp2 = wp2.moveTo(wx(mx), wy(my)).circle(pilot_r)
    res = res.cut(wp2.extrude(pilot_depth))
    # optional TC2030 re-flash window: a clearance hole through the back skin over TC1
    if prog_window:
        res = res.cut(cq.Workplane("XY").workplane(offset=-0.1)
                        .moveTo(wx(13.3), wy(16.9)).circle(5.5)        # ~11 mm clear for the pogo nose
                        .extrude(floor + 0.2))
    return res

# =============================== variants ===============================
# material -> recommended outer-skin floor (ENCLOSURE-NOTES.md):
#   Ti-6Al-4V holds 0.3 mm skins (yield ~880 MPa) -> std 0.6, thin 0.2.
#   7075-T6 is marginal at 0.3 -> bump the floor; thin is not advised in 7075.
OUT = "/mnt/user-data/outputs/"
B = "solar-glow-drh-v2_1-backshell"
jobs = [
    # name suffix              floor  pillars                prog_window  note
    ("Ti-std",                 0.60,  PILLARS_SPARSE,        False, "Ti-6Al-4V, standard 0.6 skin"),
    ("Ti-thin",                0.20,  auto_pillars(),         False, "Ti-6Al-4V, thin 0.2 skin (densified pillars)"),
    ("7075-std",               0.80,  PILLARS_SPARSE,        False, "7075-T6, bumped 0.8 skin"),
    ("Ti-std-progwindow",      0.60,  PILLARS_SPARSE,        True,  "Ti-6Al-4V std + TC2030 re-flash window"),
]
print(f"cavity={cavity}  (U2 {U2_H} + Kapton {kapton_th} + margin {cav_margin})")
for suf, floor, pil, pw, note in jobs:
    solid = build(floor, pil, prog_window=pw)
    total = floor + cavity + board_th
    name = f"{B}-{suf}"
    cq.exporters.export(solid, OUT + name + ".step")
    cq.exporters.export(solid, OUT + name + ".stl", tolerance=0.04, angularTolerance=0.2)
    print(f"  {name:38s} floor={floor:.2f}  cavity={cavity:.2f}  total={total:.2f} mm  "
          f"pillars={len(pil):2d}  progwin={pw}  | {note}")
print("done")
