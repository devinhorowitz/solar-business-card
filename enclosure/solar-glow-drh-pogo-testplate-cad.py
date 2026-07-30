#!/usr/bin/env python3
"""Printable pogo test plate for FACE-UP, in-frame bring-up -> STEP + STL + DRAWING.

WHY THIS EXISTS

The B-side test pads (TP1-TP7, plus the JP1 bench strip) answer "can every harvest node
be probed", but the light answers nothing with the board face-down: the solar cells are
on the front, so bench-probing the back the obvious way -- card flipped, pads up -- puts
the cells in the dark, and the ONE measurement this project is gated on (harvest under
real indoor light) cannot run. The standard fix is the standard bed-of-nails orientation:
pins point UP out of a plate, the PANEL drops on face-up, the cells face the light, and
every B-side pad lands on a receptacle. The panel's two tooling holes (TH1/TH2, deliberately
asymmetric) register it; TC1 is F.Cu so the Tag-Connect comes down from the top at the
same time. Program, illuminate, and probe at once -- test as delivered from PCBWay, then
depanel.

Like the brace and the shell, this plate is a FUNCTION OF THE BOARD: probe positions and
net labels are parsed from the committed .kicad_pcb, the tooling-hole and rail geometry
is imported from scripts/panelize.py, and the cavity depth is derived from
enclosure/part_heights.py. Move a pad and CI reprints the plate.

HARDWARE (generic 75-series probes -- the ubiquitous bench line)

  P75 probe    barrel dia 1.02, free length ~16.5, FULL stroke 2.50, spring ~100 g
               (per the vendor listings for P75-E2; the E2 round head suits bare pads).
  R75-3W       wire-wrap receptacle: sleeve OD 1.32, collar height 5.0, total ~26.5,
               vendor mounting hole 1.4 (FR4). Tails hang below the plate for wiring.
  Dowel pins   2x dia 1.5 (steel dowel or drill blank) through TH1/TH2.

The one number no listing publishes is EXPOSED_FREE -- how far the probe tip stands above
the receptacle collar when seated. The default below is a design estimate; MEASURE IT on
one real P75+R75 pair and re-run before printing, it is a one-line edit. Resin bores also
shrink printer-to-printer, so the plate carries a five-bore FIT COUPON (1.25..1.45): press
a receptacle into the coupon first and set RECEPT_BORE to the size that grips.
"""
import os
import re
import sys

import cadquery as cq
import matplotlib
matplotlib.use("Agg")
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
from matplotlib.patches import Circle as MplCircle, Rectangle

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from part_heights import SUPERCAP_H  # noqa: E402  -- tallest B-side parts set the cavity
import panelize  # noqa: E402        -- TH positions + panel frame, the same numbers the fab gets

OUT = os.environ.get("OUT_DIR") or HERE + os.sep
BASE = "solar-glow-drh-pogo-testplate"

# ---- pogo hardware (see module docstring; measure EXPOSED_FREE before printing) ------
RECEPT_BORE = 1.35     # press-fit bore for the R75-3W sleeve in resin; coupon spans 1.25-1.45
RECEPT_BELOW_COLLAR = 26.5 - 5.0   # sleeve length below the collar
COMPRESSION = 1.20     # designed probe compression at rest (~half of the 2.50 full stroke)
EXPOSED_FREE = 5.50    # probe tip above receptacle collar, UNCOMPRESSED -- MEASURE AND SET
DOWEL_D = 1.5          # matches the panel's TH1/TH2 NPTH
DOWEL_BORE = 1.45      # press bore for the dowel in resin
DOWEL_PROUD = 2.5      # dowel above the plate top: 0.6 board + 1.9 of lead-in

# ---- plate geometry ------------------------------------------------------------------
BASE_TH = 4.0          # solid floor under the cavity
LEDGE_H = 6.0          # cavity depth = panel rest plane above the cavity floor
MARGIN = 3.0           # plate beyond the panel outline
CAV_CLR = 0.5          # cavity beyond the moat-outer rect, so only the rails are supported
BOSS_D = 4.0           # receptacle boss
LEG_D = 9.0            # corner legs; must lift the plate more than the receptacle tails hang
FONT = fm.findfont(fm.FontProperties(family="DejaVu Sans"))  # matplotlib bundles it: deterministic in CI

# ---- board + panel data (parsed, not restated) ---------------------------------------
def _blocks(src, opener):
    for m in re.finditer(opener, src):
        i = m.start()
        i = src.index("(", i)
        j, d, instr = i, 0, False
        while True:
            c = src[j]
            if instr:
                if c == "\\":
                    j += 2
                    continue
                if c == '"':
                    instr = False
            elif c == '"':
                instr = True
            elif c == "(":
                d += 1
            elif c == ")":
                d -= 1
                if d == 0:
                    break
            j += 1
        yield src[i:j + 1]


def probe_points(src):
    """[(label, x, y)] for every pad of TP1-TP7 and JP1, in board coordinates."""
    import math
    pts = []
    for b in _blocks(src, r'\n\t\(footprint "'):
        mref = re.search(r'\(property "Reference" "([^"]+)"', b)
        if not mref or not re.match(r"^(TP[1-7]|JP1)$", mref.group(1)):
            continue
        at = re.search(r'\n\t\t\(at ([-\d.]+) ([-\d.]+)(?: ([-\d.]+))?\)', b).groups()
        fx, fy, frot = float(at[0]), float(at[1]), float(at[2] or 0)
        for pb in _blocks(b, r'\n\t\t\(pad "'):
            pat = re.search(r'\(at ([-\d.]+) ([-\d.]+)(?: ([-\d.]+))?\)', pb).groups()
            px, py = float(pat[0]), float(pat[1])
            c, s = math.cos(math.radians(frot)), math.sin(math.radians(frot))
            gx, gy = fx + px * c + py * s, fy - px * s + py * c   # KiCad y-down rotation
            net = re.search(r'\(net (?:\d+ )?"((?:[^"\\]|\\.)*)"\)', pb)
            pts.append((net.group(1) if net else "?", round(gx, 3), round(gy, 3)))
    return pts


board_src = open(os.path.join(ROOT, "PCB", "solar-glow-drh-v4_0.kicad_pcb")).read()
PROBES = probe_points(board_src)
assert len(PROBES) == 11, f"expected 11 probe pads (TP1-TP7 + JP1 x4), found {len(PROBES)}"

card = panelize.card_polygon(board_src.replace("\r\n", "\n"))
frame, _slots, (bx0, by0, bx1, by1) = panelize.build(card)
px0, py0, px1, py1 = frame.bounds
DOWELS = [(px0 + panelize.BUS_INSET, panelize.TH_LEFT_Y),
          (px1 - panelize.BUS_INSET, panelize.TH_RIGHT_Y)]

# moat-outer rect: everything inboard of the rails, i.e. what must hang over the cavity
mx0, my0, mx1, my1 = px0 + panelize.RAIL_W, py0 + panelize.RAIL_W, px1 - panelize.RAIL_W, py1 - panelize.RAIL_W

# ---- derived Z stack -----------------------------------------------------------------
Z_REST = BASE_TH + LEDGE_H                    # panel underside rests here
BOSS_TOP = Z_REST + COMPRESSION - EXPOSED_FREE
BOSS_H = BOSS_TOP - BASE_TH
LEG_H = round(RECEPT_BELOW_COLLAR - BOSS_H - BASE_TH + 2.0, 1)   # tails clear the bench by 2
PART_DROP = SUPERCAP_H + 0.15                 # tallest part + solder below the board
assert BOSS_H >= 1.0, f"boss only {BOSS_H:.2f} above the cavity floor -- raise LEDGE_H or re-measure EXPOSED_FREE"
assert Z_REST - BOSS_TOP >= PART_DROP + 0.5, "bosses reach into component territory"
assert LEDGE_H >= PART_DROP + 1.0, "cavity too shallow for the supercaps"

PLATE_X0, PLATE_Y0 = px0 - MARGIN, py0 - MARGIN
PLATE_X1, PLATE_Y1 = px1 + MARGIN, py1 + MARGIN
CAV_X0, CAV_Y0, CAV_X1, CAV_Y1 = mx0 - CAV_CLR, my0 - CAV_CLR, mx1 + CAV_CLR, my1 + CAV_CLR

for lab, x, y in PROBES:
    assert CAV_X0 + BOSS_D / 2 < x < CAV_X1 - BOSS_D / 2 and CAV_Y0 + BOSS_D / 2 < y < CAV_Y1 - BOSS_D / 2, \
        f"probe {lab} at ({x},{y}) not inside the cavity"
for x, y in DOWELS:
    assert not (CAV_X0 < x < CAV_X1 and CAV_Y0 < y < CAV_Y1), f"dowel at ({x},{y}) must be in the ledge"

# fit coupon: five bores in the plate's front margin band, clear of the panel's seat
COUPON = [1.25, 1.30, 1.35, 1.40, 1.45]
COUPON_XY = [(PLATE_X0 + 14 + i * 4.0, PLATE_Y0 + 1.5) for i in range(len(COUPON))]
for d, (cx, cy) in zip(COUPON, COUPON_XY):
    assert cy + d / 2 < py0, "coupon under the panel seat"

# ---- solid ---------------------------------------------------------------------------
W, H = PLATE_X1 - PLATE_X0, PLATE_Y1 - PLATE_Y0
CX, CY = (PLATE_X0 + PLATE_X1) / 2, (PLATE_Y0 + PLATE_Y1) / 2

plate = (cq.Workplane("XY").center(CX, CY).rect(W, H).extrude(Z_REST)
         .edges("|Z").fillet(3.0))
# cavity
plate = plate.cut(cq.Workplane("XY").workplane(offset=BASE_TH)
                  .center((CAV_X0 + CAV_X1) / 2, (CAV_Y0 + CAV_Y1) / 2)
                  .rect(CAV_X1 - CAV_X0, CAV_Y1 - CAV_Y0).extrude(LEDGE_H + 1)
                  .edges("|Z").fillet(2.0))
# receptacle bosses + bores
for lab, x, y in PROBES:
    plate = plate.union(cq.Workplane("XY").workplane(offset=BASE_TH)
                        .center(x, y).circle(BOSS_D / 2).extrude(BOSS_H))
for lab, x, y in PROBES:
    plate = plate.cut(cq.Workplane("XY").workplane(offset=-1)
                      .center(x, y).circle(RECEPT_BORE / 2).extrude(BOSS_TOP + 2))
# dowel bores (through, so a pin can be punched back out)
for x, y in DOWELS:
    plate = plate.cut(cq.Workplane("XY").workplane(offset=-1)
                      .center(x, y).circle(DOWEL_BORE / 2).extrude(Z_REST + 2))
# corner legs
LEGS = [(PLATE_X0 + LEG_D / 2 + 1, PLATE_Y0 + LEG_D / 2 + 1), (PLATE_X1 - LEG_D / 2 - 1, PLATE_Y0 + LEG_D / 2 + 1),
        (PLATE_X0 + LEG_D / 2 + 1, PLATE_Y1 - LEG_D / 2 - 1), (PLATE_X1 - LEG_D / 2 - 1, PLATE_Y1 - LEG_D / 2 - 1)]
for x, y in LEGS:
    plate = plate.union(cq.Workplane("XY").workplane(offset=-LEG_H)
                        .center(x, y).circle(LEG_D / 2).extrude(LEG_H))
# fit coupon bores through the full ledge thickness
for d, (x, y) in zip(COUPON, COUPON_XY):
    plate = plate.cut(cq.Workplane("XY").workplane(offset=-1)
                      .center(x, y).circle(d / 2).extrude(Z_REST + 2))

# engraved labels: net names on the cavity floor beside each boss, sizes beside the coupon,
# a title on the top face. All via the matplotlib-bundled DejaVu, so CI and desk agree.
def engrave(txt, x, y, z, h=2.2, depth=0.4, halign="left"):
    global plate
    try:
        t = (cq.Workplane("XY").workplane(offset=z)
             .center(x, y).text(txt, h, -depth, font="DejaVu Sans", fontPath=FONT, halign=halign))
        plate = plate.cut(t)
    except Exception as e:                      # a font hiccup must not cost the geometry
        print(f"  (label '{txt}' skipped: {e})")

# per-label nudges keep the TP4/TP5/TP6 cluster and the right-edge column readable
NUDGE = {"LX_LOUT": (2.6, 2.4), "BUFSRC": (2.6, -3.4)}
for lab, x, y in PROBES:
    dx, dy = NUDGE.get(lab, (2.6, -1.1))
    if x > 42:                                  # JP1/TP1 column: label to the LEFT of the boss
        engrave(lab, x - dx, y - 1.1, BASE_TH, halign="right")
    else:
        engrave(lab, x + dx, y + dy, BASE_TH)
for d, (x, y) in zip(COUPON, COUPON_XY):
    engrave(f"{d:.2f}", x - 1.8, y + 2.6, Z_REST, h=1.6)
engrave("SOLAR-GLOW DRH POGO TEST PLATE - panel face-up",
        PLATE_X0 + 8, PLATE_Y1 - 1.4, Z_REST, h=1.8)

# ---- report --------------------------------------------------------------------------
print(f"plate   {W:.1f} x {H:.1f}, top Z {Z_REST:.2f}, cavity floor Z {BASE_TH:.2f}, legs {LEG_H:.1f}")
print(f"Z stack bench 0 / plate bottom {0.0:.2f} / cavity floor {BASE_TH:.2f} / boss top {BOSS_TOP:.2f} "
      f"/ panel rest {Z_REST:.2f}  (probe compression {COMPRESSION:.2f}, exposed-free {EXPOSED_FREE:.2f})")
print(f"clearance boss-top to parts: {Z_REST - BOSS_TOP - PART_DROP:.2f}  "
      f"(parts drop {PART_DROP:.2f} below the board)")
print(f"receptacle tail below bench-side plate face: {RECEPT_BELOW_COLLAR - BOSS_H - BASE_TH:.1f} "
      f"(legs {LEG_H:.1f} keep it off the bench)")
print("probes:")
for lab, x, y in PROBES:
    print(f"  {lab:8} ({x:7.3f},{y:7.3f})")
print("dowels: " + ", ".join(f"({x:g},{y:g})" for x, y in DOWELS))

from fit_rules import export_step_stable  # noqa: E402
export_step_stable(plate, OUT + BASE + ".step")
cq.exporters.export(plate, OUT + BASE + ".stl", tolerance=0.03, angularTolerance=0.2)
print(f"wrote {BASE}.step / .stl")

# ---- drawing -------------------------------------------------------------------------
fig, (ax, axz) = plt.subplots(1, 2, figsize=(16, 10), width_ratios=[2.1, 1])
ax.add_patch(Rectangle((PLATE_X0, PLATE_Y0), W, H, fill=False, ec="#111", lw=1.4))
ax.add_patch(Rectangle((CAV_X0, CAV_Y0), CAV_X1 - CAV_X0, CAV_Y1 - CAV_Y0, fill=False, ec="#666", lw=1.0, ls="--"))
ax.add_patch(Rectangle((px0, py0), px1 - px0, py1 - py0, fill=False, ec="#2a7", lw=1.0))
ax.add_patch(Rectangle((0, 0), 50.8, 88.9, fill=False, ec="#2a7", lw=0.7, ls=":"))
for lab, x, y in PROBES:
    ax.add_patch(MplCircle((x, y), BOSS_D / 2, fill=False, ec="#c33", lw=1.0))
    ax.add_patch(MplCircle((x, y), RECEPT_BORE / 2, fill=False, ec="#c33", lw=0.6))
    dx, dy = NUDGE.get(lab, (2.4, 1.6))
    if x > 42:
        ax.annotate(f"{lab}", (x, y), (x + 2.4, y + 1.2), fontsize=7, color="#900")
    else:
        ax.annotate(f"{lab}", (x, y), (x + dx, y + dy + (1.4 if lab in NUDGE else 0)),
                    fontsize=7, color="#900")
for x, y in DOWELS:
    ax.add_patch(MplCircle((x, y), DOWEL_BORE / 2, fill=False, ec="#03c", lw=1.2))
    ax.annotate("dowel 1.5", (x, y), (x - 4, y - 3.2), fontsize=7, color="#03c")
for d, (x, y) in zip(COUPON, COUPON_XY):
    ax.add_patch(MplCircle((x, y), d / 2, fill=False, ec="#777", lw=0.8))
    ax.annotate(f"{d:.2f}", (x, y), (x - 1.6, y + 3.0), fontsize=6, color="#555")
for x, y in LEGS:
    ax.add_patch(MplCircle((x, y), LEG_D / 2, fill=False, ec="#999", lw=0.8, ls=":"))
ax.set_xlim(PLATE_X0 - 4, PLATE_X1 + 4)
ax.set_ylim(PLATE_Y1 + 4, PLATE_Y0 - 4)
ax.set_aspect("equal")
ax.set_title("POGO TEST PLATE — top view, board coordinates (green: panel / card; red: probe bosses)")
axz.axis("off")
rows = [("plate top (panel rest)", Z_REST), ("boss top (collar seat)", BOSS_TOP),
        ("cavity floor", BASE_TH), ("plate bottom", 0.0), ("bench (legs)", -LEG_H)]
axz.set_title("Z stack / build notes", loc="left")
txt = "\n".join(f"{n:26} {z:7.2f}" for n, z in rows) + (
    f"\n\nprobe compression   {COMPRESSION:.2f}"
    f"\nEXPOSED_FREE        {EXPOSED_FREE:.2f}  << MEASURE on a real P75+R75 pair"
    f"\nreceptacle bore     {RECEPT_BORE:.2f}  << set from the fit coupon (1.25-1.45)"
    f"\ndowels              2x dia {DOWEL_D} through TH1/TH2 ({DOWELS[0][0]:g},{DOWELS[0][1]:g}) / ({DOWELS[1][0]:g},{DOWELS[1][1]:g})"
    f"\nboss-top to parts   {Z_REST - BOSS_TOP - PART_DROP:.2f} clear (supercaps drop {PART_DROP:.2f})"
    f"\n\nhardware: P75-E2 probes (stroke 2.50 full),"
    f"\nR75-3W wire-wrap receptacles (OD 1.32,"
    f"\ncollar 5.0, ~26.5 long). Set SW2 before"
    f"\nseating the panel; TC1 connects from the top.")
axz.text(0.02, 0.96, txt, va="top", family="monospace", fontsize=9)
fig.tight_layout()
fig.savefig(OUT + BASE + "-DRAWING.png", dpi=160)
fig.savefig(OUT + BASE + "-DRAWING.pdf")
print(f"wrote {BASE}-DRAWING.png / .pdf")
