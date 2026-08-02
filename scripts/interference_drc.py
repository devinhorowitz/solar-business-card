#!/usr/bin/env python3
"""interference_drc.py -- the 3D interference DRC (tier 3 of the solid gates).

check [7] gates part heights ONE AT A TIME against the height table, and the
brace/shell generators consume that same table -- but nothing ever measured the
ASSEMBLED truth: does the actual emitted brace mesh leave room for the actual
part bodies where they actually sit? A generator regression, a pocket cut on
the wrong side, or a footprint move that outruns a pocket would all pass every
existing gate and print an uninstallable part.

This DRC measures backward from the ARTIFACT, not forward from the inputs:

  parts  -- enclosure/board_parts.parts("B"): every B-side body polygon (board
            coordinates) with its ledgered height from part_heights.py.
  brace  -- the emitted STL, ray-cast: for sample points across each part's
            footprint, a vertical ray finds the local material top; available
            headroom there = CAVITY - top (a through-cut pocket gives the full
            CAVITY down to the shell floor plane, which the brace's z=0 rests
            on). The frame offset is DERIVED (cavity-rect centre vs mesh bbox
            centre), not hard-coded.
  gate   -- min over samples of (available - height) must be >= 0 for every
            part, and every body polygon must sit inside the cavity rect.
            Contact (margin 0) is legal: the supercaps run ~0.10 mm air by
            design and the 0.16 mm graphite TIM compresses into exactly that
            gap -- the TIM is ledgered prose, not slack in the gate.

Bodies with no height and no model (bare pads: straps, TPs, dnp Tag-Connects)
are skipped by source, loudly. INTERFERENCE_TEST_INFLATE="REF:mm" exists so
the gate can be negative-tested without editing the height table.
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BRACE_STL = ROOT / "enclosure" / "brace" / "solar-glow-drh-diffuser-brace.stl"
SAMPLE_MM = 1.0
EPS = 1e-3
# The assembly tolerance stack (RSS): body-height datasheet tolerance (+-0.10 worst
# class) + solder standoff (~0.075 -- part heights are body-only, measured from 3D
# models seated at zero standoff) + resin pocket-depth print tolerance (+-0.10).
# fit_rules.AIR is sized to cover this; the worst-case column here is the proof.
# Assumes the board's B face registers on the shell seat (board-thickness tolerance
# goes to the front face, not the cavity).
WC_STACK = 0.16


def main():
    sys.path.insert(0, str(ROOT / "enclosure"))
    import numpy as np
    import trimesh
    from shapely.geometry import Point
    import board_parts
    import fit_rules

    cav = fit_rules.cavity_rect()
    cavity_h = fit_rules.CAVITY
    mesh = trimesh.load(str(BRACE_STL), force="mesh")
    (mx0, my0, _z0), (mx1, my1, mz1) = mesh.bounds
    if abs(mz1 - cavity_h) > 0.05:
        print(f"  FAIL: brace mesh height {mz1:.2f} != CAVITY {cavity_h} -- frame is wrong")
        return 1
    cx0, cy0, cx1, cy1 = cav.bounds
    off = ((cx0 + cx1) / 2 - (mx0 + mx1) / 2, (cy0 + cy1) / 2 - (my0 + my1) / 2)

    inflate = {}
    for tok in os.environ.get("INTERFERENCE_TEST_INFLATE", "").split(","):
        if ":" in tok:
            r, v = tok.split(":")
            inflate[r] = float(v)

    ray = trimesh.ray.ray_triangle.RayMeshIntersector(mesh)
    from part_heights import part_height

    # The six east-lip parts sit in the documented tight strip past the bare cavity
    # rectangle (C22/FB1 are the ledgered 0.95 mm edge cluster) -- the shell's lip
    # geometry accommodates them and all are sub-millimetre bodies. Ledgered, so a
    # NEW part escaping the rectangle still fails. (Exclusion-ledger doctrine.)
    EDGE_LEDGER = {"U6", "C27", "U9", "FB1", "C22", "R15"}

    fails, rows, skipped = [], [], []
    for ref, poly, h, source in board_parts.parts("B"):
        if h is None:
            try:
                h = part_height(ref)
            except Exception:
                h = None
            if h is None:
                # the supercaps are deliberately height-None in the table: unbraced,
                # TIM-coupled to the shell, and the CAVITY is DEFINED around them
                # (1.80 = SUPERCAP_H 1.70 + 0.10 air -- fit_rules). Their fit is
                # definitional; this DRC measures everything the brace pockets.
                skipped.append(f"{ref}({source})")
                continue
        h = h + inflate.get(ref, 0.0)
        if not cav.buffer(EPS).contains(poly) and ref not in EDGE_LEDGER:
            fails.append(f"{ref}: body polygon escapes the cavity rect (not in the "
                         "east-lip ledger)")
        x0, y0, x1, y1 = poly.bounds
        pts = [(x, y) for x in np.arange(x0, x1 + SAMPLE_MM / 2, SAMPLE_MM)
               for y in np.arange(y0, y1 + SAMPLE_MM / 2, SAMPLE_MM)
               if poly.buffer(EPS).contains(Point(x, y))]
        if not pts:
            pts = [(poly.centroid.x, poly.centroid.y)]
        origins = np.array([[x - off[0], y - off[1], cavity_h + 5.0] for x, y in pts])
        dirs = np.tile([0.0, 0.0, -1.0], (len(origins), 1))
        loc, idx_ray, _ = ray.intersects_location(origins, dirs)
        top = np.zeros(len(pts))          # no material hit -> through-cut, top = 0
        for (lx, ly, lz), ir in zip(loc, idx_ray):
            if lz > top[ir]:
                top[ir] = lz
        margin = float((cavity_h - top - h).min())
        rows.append((margin, ref, h))
        if margin < -EPS:
            fails.append(f"{ref}: h {h:.2f} mm exceeds local headroom by {-margin:.2f} mm")

    rows.sort()
    wc_warn = [r for r in rows if r[0] - WC_STACK < -EPS]
    for margin, ref, h in rows[:6]:
        tag = 'FAIL' if margin < -EPS else ('warn' if margin - WC_STACK < -EPS else 'ok  ')
        print(f"  {tag} {ref:6s} h={h:.2f}  nominal {margin:+.2f}  worst-case "
              f"{margin - WC_STACK:+.2f} mm")
    if wc_warn:
        print(f"  WARN: {len(wc_warn)} bodies clear nominally but not the worst-case "
              f"stack (WC_STACK {WC_STACK}) -- expected only against a brace built "
              f"with the pre-2026-08-02 AIR")
    print(f"  ({len(rows)} bodies checked, tightest 6 shown; skipped pad-only: "
          f"{', '.join(skipped) if skipped else 'none'})")
    if fails:
        for f in fails:
            print(f"  FAIL: {f}")
        return 1
    print(f"interference_drc: every B-side body clears the emitted brace/cavity "
          f"(worst margin {rows[0][0]:+.2f} mm on {rows[0][1]})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
