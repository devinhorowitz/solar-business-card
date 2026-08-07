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
# Since 2026-08-07 the gate loops every variant that HAS a brace (fit_rules.VARIANTS):
# each brace STL is ray-cast against ITS OWN cavity depth. One hardcoded STL here used
# to be the whole gate -- the consumer map's "gating silently shrinks to a fraction of
# what ships" hazard.
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
    rc = 0
    sys.path.insert(0, str(ROOT / "enclosure"))
    import fit_rules
    for vname, v in fit_rules.VARIANTS.items():
        if not v["brace"]:
            print(f"  [{vname}] no brace by design (open frame) -- nothing to ray-cast")
            continue
        print(f"== variant {vname}: {v['brace_name']}.stl vs cavity {v['cavity']} ==")
        rc |= check_variant(vname, v)
    return rc


def check_variant(vname, v):
    import numpy as np
    import trimesh
    from shapely.geometry import Point
    import board_parts
    import fit_rules

    cav = fit_rules.cavity_rect()
    cavity_h = v["cavity"]
    mesh = trimesh.load(str(ROOT / "enclosure" / "brace" / (v["brace_name"] + ".stl")),
                        force="mesh")
    (mx0, my0, _z0), (mx1, my1, mz1) = mesh.bounds
    if abs(mz1 - cavity_h) > 0.05:
        print(f"  FAIL: brace mesh height {mz1:.2f} != cavity {cavity_h} -- frame is wrong")
        return 1
    cx0, cy0, cx1, cy1 = cav.bounds
    # The board->mesh transform is DEFINITIONAL, not derived: the brace CAD builds at
    # wx/wy = board - (W/2, H/2). It used to be inferred from bbox centres, which is
    # correct only while the brace happens to span the full cavity envelope -- the lite
    # brace does not (its main piece stops at board y 58.4), and the inferred offset
    # would have ray-cast every pocket half a card away from its part.
    off = (fit_rules.W / 2, fit_rules.H / 2)
    if not (mx0 >= cx0 - off[0] - 0.5 and mx1 <= cx1 - off[0] + 0.5
            and my0 >= cy0 - off[1] - 0.5 and my1 <= cy1 - off[1] + 0.5):
        print(f"  FAIL: brace mesh bbox falls outside the cavity under the definitional "
              f"board-centre transform -- generator frame broke")
        return 1
    if v["cap_h"] != fit_rules._SUPERCAP_H:
        print(f"  note: thin-cap variant -- SC1-SC4 assumed {v['cap_h']:.2f} mm "
              f"(PROVISIONAL, no MPN/model yet; this gate cannot measure them)")

    inflate = {}
    for tok in os.environ.get("INTERFERENCE_TEST_INFLATE", "").split(","):
        if ":" in tok:
            _iref, _imm = tok.split(":")     # NOT r/v -- v is the variant row here
            inflate[_iref] = float(_imm)

    ray = trimesh.ray.ray_triangle.RayMeshIntersector(mesh)
    from part_heights import part_height

    # The edge parts sit in the documented tight strip past the bare cavity rectangle
    # (C22/FB1 are the ledgered 0.95 mm edge cluster) -- the shell's lip geometry
    # accommodates them and all are sub-millimetre bodies. Ledgered, so a NEW part
    # escaping the rectangle still fails. (Exclusion-ledger doctrine.)
    #
    # C7 joined 2026-08-07, and it is the smallest entry here by a wide margin. DRH's
    # rework moved it (5.25, 12.45) -> (2.96, 10.07); its body now starts at x = 2.4600
    # against the cavity's west wall at x = 2.5000, so it escapes by 0.0400 mm --
    # 0.0672 mm2 of body outside the rectangle. It is the SAME west edge FB1 and C22
    # already overhang by 1.2976 / 1.3000 mm with the lip accommodating them, i.e. C7 is
    # 32x further inside the envelope this ledger was written for. Measured, not assumed:
    # its 3D ray-cast margin never enters the tightest-six, and assembly_drc is 0/0 on the
    # same geometry. Ledgered rather than nudged so DRH's copper is not re-terminated for
    # 40 um -- if C7 ever moves again, this entry should be re-measured, not inherited.
    EDGE_LEDGER = {"U6", "C27", "U9", "FB1", "C22", "R15", "C7"}

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
    print(f"interference_drc[{vname}]: every B-side body clears the emitted brace/cavity "
          f"(worst margin {rows[0][0]:+.2f} mm on {rows[0][1]})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
