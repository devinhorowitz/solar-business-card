#!/usr/bin/env python3
"""Generate STEP bodies for the parts KiCad has no model for.

    pip install cadquery
    python3 scripts/make_3d_models.py            # -> PCB/solarglow.3dshapes/*.step
    python3 scripts/make_3d_models.py --list

WHY THESE EXIST

The brace and back-shell are dimensioned against the parts they clear, so the
board's 3D view and its STEP export have to carry real bodies. KiCad ships models
for its own footprints, but every `solarglow:*` footprint is drawn for this
project and has none, so the tallest, most fit-critical parts — the supercaps and
the solar cells — were simply absent from the model.

WHAT THESE ARE, AND ARE NOT

Envelope solids, not cosmetic models. Each is the part's **maximum** outline at its
**maximum** height, because the only question being asked is "does the enclosure
clear it?". A pretty model at the wrong height would be worse than useless here.
Do not read them as appearance references.

WHERE THE NUMBERS COME FROM — every dimension below is traceable, none invented:

  SCPC SS17/WS17   PCB/solarglow.pretty/SCHURTER_SCPC_*.kicad_mod `descr`, which
                   quotes the SCHURTER datasheet: cells 39.0 x 17.0 and 28.5 x 17.0,
                   both **1.70 mm max** thick, with finish-coated locator tabs
                   ~2.75 mm past each end that are NOT solder pads. The 1.70 is the
                   same number enclosure/README.md builds the 1.80 mm cavity on.
  SM141K06TF       datasheet: "Dimensions (W x L x H): 42 x 23 x 1.2 +/- 0.3 [mm]".
                   Modelled at the +0.3 worst case = 1.5 mm, since this is a
                   clearance solid.

THE END TABS ARE DELIBERATELY NOT MODELLED — and that is a finding, not laziness.

The footprint `descr` puts the locator tabs ~2.75 mm past each end. Modelled flat
and in-plane, that makes **all four supercaps overhang the board edge**:

    SC1  cell y  1.75..40.75   with tabs -1.00..43.50   ->  1.00 mm past y=0
    SC2  cell y  2.65..31.15   with tabs -0.10..33.90   ->  0.10 mm past y=0
    SC3  cell y 47.98..86.98   with tabs 45.23..89.73   ->  0.83 mm past y=88.9
    SC4  cell y 58.55..87.05   with tabs 55.80..89.80   ->  0.90 mm past y=88.9

PCB/README.md describes them as "**folded** end tabs ... coated, non-solderable
locators", i.e. they do not lie flat in the board plane, and the footprint's own
courtyard covers the 39.0 mm cell and NOT the tabs. So a flat 2.75 mm extension is
almost certainly the wrong shape, and shipping it would invent a board-edge
overhang for the enclosure to design around.

The cell body is the number that is solidly sourced, so that is what these solids
are. **Open question for the enclosure work: what is the tabs' real folded
geometry, and do they in fact reach past the board edge?** Until that is measured
on a real cell, treat the envelope near the short edges as unverified.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "PCB" / "solarglow.3dshapes"

# name -> (builder, human description)
#   All solids are centred on the footprint origin in X/Y and sit on z=0 growing +Z,
#   which is what KiCad expects for a part on the board's top surface; KiCad mirrors
#   it automatically for footprints placed on the back.
SPECS = {
    "SCHURTER_SCPC_SS17": dict(
        body=(39.0, 17.0, 1.70), tab=None,
        desc="SCPC SS17 supercap, 1.8 F — cell 39.0 x 17.0 x 1.70 max (tabs excluded, see header)",
    ),
    "SCHURTER_SCPC_WS17": dict(
        body=(28.5, 17.0, 1.70), tab=None,
        desc="SCPC WS17 supercap, 1.0 F — cell 28.5 x 17.0 x 1.70 max (tabs excluded, see header)",
    ),
    "SM141K06TF": dict(
        body=(42.0, 23.0, 1.50), tab=None,
        desc="ANYSOLAR SM141K06TF cell — 42 x 23 x 1.2 +0.3 (modelled at max 1.5)",
    ),
}


def build(name: str, spec: dict):
    import cadquery as cq
    L, W, H = spec["body"]
    solid = cq.Workplane("XY").box(L, W, H, centered=(True, True, False))
    if spec["tab"]:
        tl, tw, th = spec["tab"]
        # Tabs sit centred on the cell's thickness, projecting past each end.
        z0 = (H - th) / 2.0
        for sign in (1, -1):
            solid = solid.union(
                cq.Workplane("XY")
                .box(tl, tw, th, centered=(True, True, False))
                .translate((sign * (L + tl) / 2.0, 0, z0))
            )
    return solid


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()

    if args.list:
        for n, s in SPECS.items():
            L, W, H = s["body"]
            print(f"{n:24s} {L} x {W} x {H} mm   {s['desc']}")
        return 0

    try:
        import cadquery  # noqa: F401
    except ImportError:
        sys.exit("make_3d_models: needs cadquery  ->  pip install cadquery")

    import cadquery as cq
    OUT.mkdir(parents=True, exist_ok=True)
    for name, spec in SPECS.items():
        solid = build(name, spec)
        dest = OUT / f"{name}.step"
        cq.exporters.export(solid, str(dest))
        bb = solid.val().BoundingBox()
        print(f"  {dest.relative_to(ROOT)}  "
              f"{bb.xlen:.2f} x {bb.ylen:.2f} x {bb.zlen:.2f} mm  "
              f"({dest.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
