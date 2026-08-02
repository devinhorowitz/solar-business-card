#!/usr/bin/env python3
"""Build the PCBWay 1-up fabrication panel from the committed board file.

    python3 scripts/panelize.py                       # -> Generated/panel/<board>-panel.kicad_pcb
    python3 scripts/panelize.py --out /tmp/p.kicad_pcb
    python3 scripts/panelize.py --check               # geometry only, writes nothing

WHY THIS EXISTS
---------------
v4.0 orders selective hard (electrolytic) gold on the F.Cu art set, and electrolytic
plating needs a current path from the plating rack to every surface being plated. The
board therefore carries two 0.4 mm plating-bus stubs that cross the outline at x = 25.4
(bottom and top). On a bare board those stubs dangle: they end 0.4 mm outside the
outline and connect to nothing. They only do their job inside a panel, where they run
across a break-off tab onto a frame rail the rack can clip. PCB/README.md's special
request already tells the fab to "retain to panel rail and rout at depanel" -- this
script is the panel that sentence assumes.

WHY IT IS A SCRIPT AND NOT A SECOND .kicad_pcb
----------------------------------------------
The board is ~9.7 MB, most of it the monogram artwork. A hand-maintained panel file
would be a byte-for-byte duplicate of all of it that has to be re-synced on every
copper edit -- the exact drift this repo's "each fact has exactly one home" rule
exists to prevent. So the panel is a DERIVED artifact: CI runs this, drops the result
in Generated/panel/, and KiBot plots fab data from it. The board file stays the single
source of truth and stays 1-up, so the 3D view, pcbdraw images and iBOM keep showing a
card rather than a panel.

The transform is purely additive apart from one deletion: the board's own Edge.Cuts is
replaced, because in a panel the card outline is implied by the boundaries of the two
routed slots (this is how the v0 panel's .GKO was structured too -- three contours:
panel rectangle plus two slots).

LINEAGE
-------
v0 shipped a working panel, emitted directly as gerber by "v0-prototype"'s (culled 2026-08-02; git history)
gerber_export.py (MOAT_W/RAIL_W/TAB_W = 2.4/3.0/3.0, four 0.5 mm mouse bites at 0.8 mm
pitch per tab). Panel outline was 61.6 x 99.7 mm. Two constants are deliberately
different here, both for the same reason -- v0 had no rail copper and this panel does:

  RAIL_W 3.0 -> 5.0   A 3 mm rail cannot hold a plating bus plus panel silkscreen with
                      any margin. 5 mm is also the width fabs expect on an assembly
                      rail, so this is the conventional value, not an inflated one.
                      Costs ~11% panel area, i.e. cents at prototype quantity.

  TAB_W  3.0 -> 5.0   The bus has to cross the tab at x = 25.4, and v0's mouse-bite
                      pattern puts hole edges 0.15 mm either side of that line. Widening
                      the tab opens a hole-free corridor for the bus and still leaves
                      room for two bites per side. See BUS_CORRIDOR below.
"""

from __future__ import annotations

import argparse
import math
import re
import sys
import uuid
from pathlib import Path

from shapely.geometry import LineString, Polygon, box
from shapely.ops import polygonize, unary_union

ROOT = Path(__file__).resolve().parent.parent
BOARD = ROOT / "PCB" / "solar-glow-drh-v4_0.kicad_pcb"

# ---------------------------------------------------------------- panel geometry (mm)
MOAT_W = 2.4        # routed slot between card and frame -- v0's value, a standard 2.4 mm router bit
RAIL_W = 5.0        # frame rail material outside the moat (v0: 3.0; see module docstring)
TAB_W = 5.0         # break-off bridge width, one per short edge (v0: 3.0; see module docstring)
TAB_X = 25.4        # tab centre = where the plating stubs already cross the outline

BUS_CORRIDOR = 1.0  # hole-free band centred on TAB_X: 0.4 mm bus + 0.30 mm drill-to-copper either side
MB_D = 0.5          # mouse-bite drill (v0)
MB_PITCH = 1.0      # centre-to-centre within one side of the corridor
MB_PER_SIDE = 2     # bites left of the corridor and right of it, per tab
MB_EDGE_MARGIN = 0.4  # minimum material between the outermost bite and the tab edge

BUS_W_SPUR = 0.4    # across tab and rail -- matches the board-side stub width exactly, no neck-down
BUS_W_RAIL = 1.0    # the ring the plating rack clips onto
BUS_INSET = 2.5     # ring centreline inset from the panel edge (rail is RAIL_W wide)

# Two 1.5 mm NPTH tooling holes in the side rails let a pogo fixture register to the
# panel and land on the board's B-side test pads (TP2-TP7) while the card is still
# attached -- test as delivered, then depanel. The rail centreline is where a tooling
# hole wants to be, but it is also exactly where the plating-bus ring runs (BUS_INSET
# = RAIL_W/2), so the ring takes a rectangular jog around each hole -- outward, where
# the rail has 0.45 mm to spare -- rather than the hole squeezing beside the ring.
# The y positions are DELIBERATELY not 180-degree symmetric about the panel centre:
# two symmetric holes would let the panel drop onto the fixture backwards. main()
# asserts the asymmetry so nobody "tidies" these into symmetry later.
TH_D = 1.5          # NPTH drill
TH_LEFT_Y = 20.0    # hole centre on the left rail's ring line, board-frame y
TH_RIGHT_Y = 85.0   # hole centre on the right rail's ring line, board-frame y
TH_DODGE = 1.55     # jog offset and half-height: hole r 0.75 + 0.30 hole-to-copper
                    # + ring half-width 0.50; leaves 0.45 mm copper-to-panel-edge

# Three fiducials for the pick-and-place vision system -- the panel had NONE, and PCBWay
# machine-places 47 parts including two 0.4 mm-pitch QFNs (U1, U8); the gap was found by the
# kicad-happy fiducial audit (docs/kicad-happy.md, 2026-08-01). Each is a 1.0 mm bare copper
# dot with a 2.0 mm mask opening (solder_mask_margin carries the difference), at the same X/Y
# on BOTH faces because both sides carry placed parts. They live in the rail's OUTER band,
# outside the plating-bus ring: dot centre FID_INSET from the panel edge puts the dot edge
# (BUS_INSET - BUS_W_RAIL/2 - FID_INSET - FID_D/2) = 0.5 mm clear of the ring copper, and
# main() asserts that so a constant "tidy" cannot silently close the gap. Three corners of
# four, so a rotated panel cannot fool the vision system -- the tooling holes' asymmetry
# doctrine, guarded the same way. Kept clear of the tooling-hole ring dodges, which jog
# OUTWARD into this same band (TH_DODGE).
FID_D = 1.0         # bare copper dot
FID_MASK_D = 2.0    # mask opening -- IPC-ish 2:1 keeps mask registration out of the vision fit
FID_INSET = 1.0     # dot centre from the panel edge
FID_SETBACK = 6.0   # dot centre from the panel corner, along the rail

# The ring is useless buried under soldermask -- a plating rack needs bare copper to clip. So the
# ring gets an F.Mask opening along its whole length, which also lets the fab pick its own contact
# point. Exposing all of it does risk the gold bath reaching it, but that is ~319 mm^2 at ~1 um,
# i.e. about 6 mg of gold (well under a dollar) on copper that gets routed away at depanel. The
# special request in PCB/README.md names the gold set as card artwork and excludes the rail
# explicitly, so this should not happen anyway; it is priced in rather than engineered around.
BUS_MASK_EXPAND = 0.1

SILK_SIZE = 1.0
SILK_THICK = 0.15

# Deterministic UUIDs: CI regenerates this file on every PCB/** push, and random UUIDs
# would make every regeneration a full-file diff.
NS = uuid.UUID("5f3a1c96-0f8e-5c1a-9a2b-2a0d6f1b7c44")


def uid(tag: str) -> str:
    return str(uuid.uuid5(NS, tag))


# ------------------------------------------------------------------------ s-expr utils
def sexpr_blocks(src: str, tag: str):
    """(start, end, text) for every '(tag' block, paren-balanced and string-aware."""
    out = []
    for m in re.finditer(r"(?m)^\s*\(" + re.escape(tag) + r"[\s(]", src):
        i = src.index("(", m.start())
        j, depth, instr = i, 0, False
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
                depth += 1
            elif c == ")":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        out.append((i, j + 1, src[i : j + 1]))
    return out


def n(v: float) -> str:
    """KiCad-style number: no trailing zeros, no '-0'."""
    s = f"{v:.6f}".rstrip("0").rstrip(".")
    return "0" if s in ("", "-0") else s


# ------------------------------------------------------------------------ card outline
def card_polygon(src: str) -> Polygon:
    """Rebuild the card outline from Edge.Cuts. Fails loudly rather than guessing."""
    segs = []
    for _, _, b in sexpr_blocks(src, "gr_line"):
        if '(layer "Edge.Cuts")' not in b:
            continue
        a = re.search(r"\(start (-?[\d.]+) (-?[\d.]+)\)", b)
        e = re.search(r"\(end (-?[\d.]+) (-?[\d.]+)\)", b)
        segs.append(LineString([(float(a[1]), float(a[2])), (float(e[1]), float(e[2]))]))
    if not segs:
        sys.exit("panelize: no Edge.Cuts gr_line found -- outline may use arcs now")
    polys = list(polygonize(unary_union(segs)))
    if len(polys) != 1:
        sys.exit(f"panelize: Edge.Cuts did not close into exactly one region ({len(polys)})")
    return polys[0]


def build(card: Polygon):
    moat_outer = card.buffer(MOAT_W, join_style=1, quad_segs=24)
    moat = moat_outer.difference(card)
    x0, y0, x1, y1 = moat_outer.bounds
    frame = box(x0 - RAIL_W, y0 - RAIL_W, x1 + RAIL_W, y1 + RAIL_W)

    # The tab column spans the full height so the difference bites both moat ends at once.
    tab_col = box(TAB_X - TAB_W / 2, y0 - 1, TAB_X + TAB_W / 2, y1 + 1)
    slots = moat.difference(tab_col)
    slots = [g for g in getattr(slots, "geoms", [slots])]
    if len(slots) != 2:
        sys.exit(f"panelize: expected 2 routed slots, got {len(slots)}")
    return frame, slots, card.bounds


def mousebite_x():
    """Bite centres on one tab, left group then right group, mirrored about TAB_X."""
    inner = TAB_X + BUS_CORRIDOR / 2 + MB_D / 2  # first hole edge lands on the corridor boundary
    right = [inner + k * MB_PITCH for k in range(MB_PER_SIDE)]
    outer_edge = right[-1] + MB_D / 2
    if outer_edge > TAB_X + TAB_W / 2 - MB_EDGE_MARGIN:
        sys.exit(f"panelize: mouse bites overrun the tab (edge at {outer_edge:.3f})")
    return [2 * TAB_X - x for x in reversed(right)] + right


# --------------------------------------------------------------------------- emitters
def edge(p0, p1, tag):
    return (
        f"\t(gr_line\n\t\t(start {n(p0[0])} {n(p0[1])})\n\t\t(end {n(p1[0])} {n(p1[1])})\n"
        f"\t\t(stroke\n\t\t\t(width 0.1)\n\t\t\t(type solid)\n\t\t)\n"
        f'\t\t(layer "Edge.Cuts")\n\t\t(uuid "{uid(tag)}")\n\t)\n'
    )


def ring(poly, tag):
    pts = list(poly.exterior.coords)
    return "".join(edge(pts[i], pts[i + 1], f"{tag}-{i}") for i in range(len(pts) - 1))


def track(p0, p1, w, tag, net="GND", layer="F.Cu"):
    return (
        f"\t(segment\n\t\t(start {n(p0[0])} {n(p0[1])})\n\t\t(end {n(p1[0])} {n(p1[1])})\n"
        f'\t\t(width {n(w)})\n\t\t(layer "{layer}")\n\t\t(net "{net}")\n'
        f'\t\t(uuid "{uid(tag)}")\n\t)\n'
    )


def mask_open(p0, p1, w, tag):
    """Filled F.Mask graphic over a bus run = an opening in the mask (this board already
    uses 605 of them for the monogram artwork, so the convention is established)."""
    x0, x1 = sorted((p0[0], p1[0]))
    y0, y1 = sorted((p0[1], p1[1]))
    e = w / 2 + BUS_MASK_EXPAND
    x0, x1, y0, y1 = x0 - e, x1 + e, y0 - e, y1 + e
    pts = " ".join(
        f"(xy {n(x)} {n(y)})" for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))
    )
    return (
        f"\t(gr_poly\n\t\t(pts\n\t\t\t{pts}\n\t\t)\n"
        f"\t\t(stroke\n\t\t\t(width 0)\n\t\t\t(type solid)\n\t\t)\n"
        f'\t\t(fill yes)\n\t\t(layer "F.Mask")\n\t\t(uuid "{uid(tag)}")\n\t)\n'
    )


def text(s, x, y, tag):
    return (
        f'\t(gr_text "{s}"\n\t\t(at {n(x)} {n(y)} 0)\n\t\t(layer "F.SilkS")\n'
        f'\t\t(uuid "{uid(tag)}")\n\t\t(effects\n\t\t\t(font\n'
        f"\t\t\t\t(size {n(SILK_SIZE)} {n(SILK_SIZE)})\n\t\t\t\t(thickness {n(SILK_THICK)})\n"
        f"\t\t\t)\n\t\t)\n\t)\n"
    )


def bite_footprint(ref, cx, cy, xs, tag, d=MB_D, value="MouseBites"):
    """Mirrors the shape of the board's own MP1-MP4 mechanical footprints exactly:
    empty lib_id, all four properties present, board_only, (embedded_fonts no) last.
    KiCad's parser is strict about the member order, and .kicad_pcb has no comment
    syntax -- nothing here may be annotated in-band. The tooling holes reuse this
    emitter with a single pad, a bigger drill and their own Value."""

    def prop(name, value, layer, tag2):
        return (
            f'\t\t(property "{name}" "{value}"\n\t\t\t(at 0 0 0)\n\t\t\t(layer "{layer}")\n'
            f'\t\t\t(hide yes)\n\t\t\t(uuid "{uid(tag2)}")\n'
            f"\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)\n\t\t\t)\n\t\t)\n"
        )

    pads = "".join(
        f'\t\t(pad "" np_thru_hole circle\n\t\t\t(at {n(x - cx)} 0)\n'
        f"\t\t\t(size {n(d)} {n(d)})\n\t\t\t(drill {n(d)})\n"
        f"\t\t\t(property pad_prop_mechanical)\n"
        f'\t\t\t(layers "*.Cu" "*.Mask")\n\t\t\t(uuid "{uid(f"{tag}-p{k}")}")\n\t\t)\n'
        for k, x in enumerate(xs)
    )
    return (
        f'\t(footprint ""\n\t\t(layer "F.Cu")\n\t\t(uuid "{uid(tag)}")\n'
        f"\t\t(at {n(cx)} {n(cy)})\n"
        + prop("Reference", ref, "F.SilkS", tag + "-ref")
        + prop("Value", value, "F.Fab", tag + "-val")
        + prop("Datasheet", "", "F.Fab", tag + "-ds")
        + prop("Description", "", "F.Fab", tag + "-de")
        + "\t\t(attr board_only exclude_from_pos_files exclude_from_bom)\n"
        + "\t\t(duplicate_pad_numbers_are_jumpers no)\n"
        + pads
        + "\t\t(embedded_fonts no)\n\t)\n"
    )


def fid_footprint(ref, cx, cy, tag):
    """Same skeleton as bite_footprint (empty lib_id, four properties, board_only,
    strict member order): one SMD circle pad per face, bare FID_D copper with a
    FID_MASK_D mask opening via solder_mask_margin, flagged pad_prop_fiducial_glob
    so the fab's vision system finds them in the drill/placement data."""

    def prop(name, value, layer, tag2):
        return (
            f'\t\t(property "{name}" "{value}"\n\t\t\t(at 0 0 0)\n\t\t\t(layer "{layer}")\n'
            f'\t\t\t(hide yes)\n\t\t\t(uuid "{uid(tag2)}")\n'
            f"\t\t\t(effects\n\t\t\t\t(font\n\t\t\t\t\t(size 1.27 1.27)\n\t\t\t\t)\n\t\t\t)\n\t\t)\n"
        )

    margin = (FID_MASK_D - FID_D) / 2
    pads = "".join(
        f'\t\t(pad "" smd circle\n\t\t\t(at 0 0)\n'
        f"\t\t\t(size {n(FID_D)} {n(FID_D)})\n"
        f"\t\t\t(property pad_prop_fiducial_glob)\n"
        f'\t\t\t(layers "{side}.Cu" "{side}.Mask")\n'
        f"\t\t\t(solder_mask_margin {n(margin)})\n"
        f'\t\t\t(uuid "{uid(f"{tag}-p{side}")}")\n\t\t)\n'
        for side in ("F", "B")
    )
    return (
        f'\t(footprint ""\n\t\t(layer "F.Cu")\n\t\t(uuid "{uid(tag)}")\n'
        f"\t\t(at {n(cx)} {n(cy)})\n"
        + prop("Reference", ref, "F.SilkS", tag + "-ref")
        + prop("Value", "Fiducial", "F.Fab", tag + "-val")
        + prop("Datasheet", "", "F.Fab", tag + "-ds")
        + prop("Description", "", "F.Fab", tag + "-de")
        + "\t\t(attr board_only exclude_from_pos_files exclude_from_bom)\n"
        + "\t\t(duplicate_pad_numbers_are_jumpers no)\n"
        + pads
        + "\t\t(embedded_fonts no)\n\t)\n"
    )


def ring_run_with_dodge(a, b, holes):
    """Points of one straight bus-ring run from a to b, jogging OUTWARD around each
    tooling hole whose centre sits on the run. Vertical runs only -- the holes live
    on the side rails. The jog is rectangular so every emitted segment stays
    axis-aligned and mask_open()'s bounding-box expansion stays exact."""
    (x0, y0), (x1, y1) = a, b
    if not holes:
        return [a, b]
    assert x0 == x1, "tooling-hole dodge is only implemented for vertical ring runs"
    sgn = 1 if y1 > y0 else -1                    # travel direction along the run
    out = 1 if x0 > TAB_X else -1                 # outward = away from the panel centre
    pts = [a]
    for hx, hy in sorted(holes, key=lambda h: sgn * h[1]):
        assert hx == x0 and min(y0, y1) < hy < max(y0, y1)
        pts += [
            (x0, hy - sgn * TH_DODGE),
            (x0 + out * TH_DODGE, hy - sgn * TH_DODGE),
            (x0 + out * TH_DODGE, hy + sgn * TH_DODGE),
            (x0, hy + sgn * TH_DODGE),
        ]
    pts.append(b)
    return pts


# ------------------------------------------------------------------------------- main
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--board", type=Path, default=BOARD)
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--check", action="store_true", help="report geometry, write nothing")
    args = ap.parse_args()

    with open(args.board, newline="") as f:
        src = f.read()
    nl = "\r\n" if src.count("\r\n") > src.count("\n") - src.count("\r\n") else "\n"
    src = src.replace("\r\n", "\n")

    card = card_polygon(src)
    frame, slots, (bx0, by0, bx1, by1) = build(card)
    px0, py0, px1, py1 = frame.bounds
    xs = mousebite_x()

    ring_x0, ring_x1 = px0 + BUS_INSET, px1 - BUS_INSET
    ring_y0, ring_y1 = py0 + BUS_INSET, py1 - BUS_INSET
    th = [(ring_x0, TH_LEFT_Y), (ring_x1, TH_RIGHT_Y)]
    # Rotating one hole 180 degrees about the panel centre must NOT land on the other,
    # or a backwards panel seats on the fixture pins. Guarded here because the y values
    # up top LOOK arbitrary and a symmetric "cleanup" would break this silently.
    rot = (px0 + px1 - th[0][0], py0 + py1 - th[0][1])
    mis = math.hypot(rot[0] - th[1][0], rot[1] - th[1][1])
    if mis < 5.0:
        sys.exit(f"panelize: tooling holes are {mis:.1f} mm from 180-degree symmetric "
                 "-- a backwards panel would seat on the fixture")

    # ---- fiducials: three corners of four, in the rails' outer band
    fids = [
        (px0 + FID_INSET, py0 + FID_SETBACK),   # left rail, top corner
        (px0 + FID_INSET, py1 - FID_SETBACK),   # left rail, bottom corner
        (px1 - FID_INSET, py0 + FID_SETBACK),   # right rail, top corner
    ]
    fid_clear = BUS_INSET - BUS_W_RAIL / 2 - FID_INSET - FID_D / 2
    if fid_clear < 0.5:
        sys.exit(f"panelize: fiducial-to-ring clearance {fid_clear:.2f} < 0.5 mm "
                 "-- the vision system needs bare board around the dot")
    # a 180-degree rotation must NOT map the fiducial set onto itself (same doctrine
    # as the tooling holes: the pattern is what makes panel orientation unambiguous)
    rot_fids = {(round(px0 + px1 - x, 1), round(py0 + py1 - y, 1)) for x, y in fids}
    if rot_fids == {(round(x, 1), round(y, 1)) for x, y in fids}:
        sys.exit("panelize: fiducial pattern is 180-degree symmetric -- a rotated "
                 "panel would pass vision alignment")
    for fx, fy in fids:
        for hx, hy in th:
            if abs(fx - hx) < RAIL_W and abs(fy - hy) < TH_DODGE + FID_D / 2 + 1.0:
                sys.exit(f"panelize: fiducial ({fx:g},{fy:g}) collides with the "
                         f"tooling-hole ring dodge at ({hx:g},{hy:g})")

    print(f"card   {bx1 - bx0:.1f} x {by1 - by0:.1f} mm   ({bx0:g},{by0:g})-({bx1:g},{by1:g})")
    print(f"panel  {px1 - px0:.1f} x {py1 - py0:.1f} mm   ({px0:g},{py0:g})-({px1:g},{py1:g})")
    print(f"moat {MOAT_W} / rail {RAIL_W} / tab {TAB_W} at x={TAB_X}")
    print(f"mouse bites per tab: {len(xs)} x d{MB_D} at x = " + ", ".join(f"{x:g}" for x in xs))
    web = (xs[MB_PER_SIDE] - MB_D / 2) - (xs[MB_PER_SIDE - 1] + MB_D / 2)
    print(f"hole-free bus web: {web:.2f} mm centred on x={TAB_X} (bus {BUS_W_SPUR} mm)")
    print(f"tooling holes d{TH_D}: left rail ({th[0][0]:g},{th[0][1]:g}), "
          f"right rail ({th[1][0]:g},{th[1][1]:g}); 180-degree mismatch {mis:.1f} mm; "
          f"ring dodge +-{TH_DODGE} -> hole-to-ring "
          f"{TH_DODGE - TH_D / 2 - BUS_W_RAIL / 2:.2f}, "
          f"ring-to-edge {BUS_INSET - TH_DODGE - BUS_W_RAIL / 2:.2f}")
    print(f"fiducials d{FID_D} cu / d{FID_MASK_D} mask, both faces, at "
          + ", ".join(f"({x:g},{y:g})" for x, y in fids)
          + f"; dot-to-ring {fid_clear:.2f} mm")
    if args.check:
        return 0

    # ---- Edge.Cuts: card outline out, panel rectangle + two routed slots in
    kill = [(i, j) for i, j, b in sexpr_blocks(src, "gr_line") if '(layer "Edge.Cuts")' in b]
    out = []
    prev = 0
    for i, j in kill:
        ls = src.rfind("\n", 0, i)  # swallow the indentation on the object's line
        out.append(src[prev:ls + 1])
        prev = j + 1 if src[j : j + 1] == "\n" else j
    out.append(src[prev:])
    body = "".join(out)

    add = [ring(frame, "frame")]
    for k, s in enumerate(slots):
        add.append(ring(s, f"slot{k}"))

    # ---- mouse bites, on the card outline exactly as v0 did (break is flush, no nub)
    for k, y in enumerate((by0, by1)):
        add.append(bite_footprint(f"MB{k + 1}", TAB_X, y, xs, f"mb{k}"))

    # ---- tooling holes, on the ring line in each side rail (the ring jogs around them)
    for ref, (hx, hy) in zip(("TH1", "TH2"), th):
        add.append(bite_footprint(ref, hx, hy, [hx], f"th-{ref}", d=TH_D, value="ToolingHole"))

    # ---- fiducials, outer band of the rails, three corners of four
    for k, (fx, fy) in enumerate(fids):
        add.append(fid_footprint(f"FID{k + 1}", fx, fy, f"fid{k}"))

    # ---- plating bus: stub -> across tab and rail -> ring around the frame
    add.append(track((TAB_X, by0), (TAB_X, ring_y0), BUS_W_SPUR, "spur-b"))
    add.append(track((TAB_X, by1), (TAB_X, ring_y1), BUS_W_SPUR, "spur-t"))
    for k, (a, b) in enumerate(
        [
            ((ring_x0, ring_y0), (ring_x1, ring_y0)),
            ((ring_x1, ring_y0), (ring_x1, ring_y1)),
            ((ring_x1, ring_y1), (ring_x0, ring_y1)),
            ((ring_x0, ring_y1), (ring_x0, ring_y0)),
        ]
    ):
        run_holes = [h for h in th if a[0] == b[0] == h[0]]
        pts = ring_run_with_dodge(a, b, run_holes)
        for i in range(len(pts) - 1):
            plain = len(pts) == 2          # undodged runs keep their original tags/uuids
            add.append(track(pts[i], pts[i + 1], BUS_W_RAIL,
                             f"ring{k}" if plain else f"ring{k}-{i}"))
            add.append(mask_open(pts[i], pts[i + 1], BUS_W_RAIL,
                                 f"ringmask{k}" if plain else f"ringmask{k}-{i}"))

    # ---- panel silkscreen, both rails, clear of the bus ring
    add.append(text("SOLAR-GLOW DRH v4.0 - PCBWay 1-up panel", TAB_X, ring_y0 + 1.5, "t0"))
    add.append(text("Generated by scripts/panelize.py - do not edit by hand", TAB_X, ring_y0 - 1.5, "t1"))
    add.append(text("HARD-GOLD PLATING BUS - RETAIN THROUGH PLATING", TAB_X, ring_y1 - 1.5, "t2"))
    add.append(text("Break tabs at x=25.4 carry the bus - rout at depanel", TAB_X, ring_y1 + 1.5, "t3"))

    end = body.rstrip().rfind(")")
    panel = body[:end] + "".join(add) + body[end:]

    dest = args.out or ROOT / "Generated" / "panel" / (args.board.stem + "-panel.kicad_pcb")
    dest.parent.mkdir(parents=True, exist_ok=True)
    with open(dest, "w", newline="") as f:
        f.write(panel.replace("\n", nl) if nl != "\n" else panel)
    print(f"wrote {dest}  ({len(panel):,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
