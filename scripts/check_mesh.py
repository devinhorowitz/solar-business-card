#!/usr/bin/env python3
"""check_mesh.py -- validity gate for the CI-generated STL solids.

These files go to FABRICATION (the Ti shell/brace solid, the pogo test plate),
and until 2026-08-01 nothing checked that they were valid solids at all: a
cadquery/OCC version bump (exactly what the weekly freshness canary proposes)
could emit a broken tessellation and every consumer -- drawings, renders, the
thickness figure -- would swallow it silently. The STEP side is gated at the
B-rep level inside enclosure/fit_rules.py::export_step_stable (OCC BRepCheck,
the one choke point every exported solid passes through); this script gates
the meshes.

Checks per STL, against a per-file BASELINE (the exclusion-ledger shape --
a deliberate geometry change updates the ledger in the same commit):

  watertight/openness -- boundary-edge count and TOTAL OPEN LENGTH. The shell
      carries one KNOWN zero-length boundary edge (a tessellation pinch at a
      single rim point, (24.4, -34.45, 2.7)) plus 3 zero-area facets --
      cosmetic, ledgered, and gated so anything WORSE (a real hole has
      nonzero open length) goes red.
  winding             -- must be consistent (flipped normals break slicers).
  volume              -- +-0.5% of baseline (tessellation is not bit-stable;
      the observed triangle-count jitter is 54,959 -> 54,927 on identical
      geometry, so triangle count is deliberately NOT gated).
  bbox                -- +-0.01 mm per axis (spans WERE byte-stable across
      the same jitter).

A .stl in enclosure/ with no BASELINE entry is an ERROR, not a skip -- the
part_colors doctrine: a new artifact must arrive with its ledger row.
"""

import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# filename -> ledger. (The v3_0 in the shell's name is a naming fossil -- the
# geometry is the current v4 solid; the coordinated rename is a TODO unit.)
BASELINE = {
    "solar-glow-drh-v3_0-backshell-0p6b-brace-Ti-max.stl": dict(
        volume_mm3=5620.24, bbox=(-26.35, -45.4, -0.15, 26.35, 45.4, 3.4),
        max_boundary_edges=1, max_open_len_mm=0.001, max_degenerate=3),
    "solar-glow-drh-pogo-testplate.stl": dict(
        volume_mm3=50860.32, bbox=(-10.4, -10.4, -17.8, 61.2, 99.3, 10.0),
        max_boundary_edges=0, max_open_len_mm=0.0, max_degenerate=0),
    # volume re-ledgered 2026-08-02 with fit_rules.AIR 0.12 -> 0.22 (pockets 0.1 deeper,
    # measured from a local regeneration then restored -- CI owns the artifact). The
    # committed STL reads 2069.74 until the merge-run rebuild, so a local run is red
    # for exactly that one transition.
    #
    # Re-ledgered 2026-08-05, 2032.99 -> 2070.29, and the delta is ITEMISED rather than
    # copied off the failing run: +23.13 mm3 is U6/U9's ceilings (TPS22919 1.10 and
    # TPS7A0233PDQNR 0.40 replaced two 1.45 SOT bodies, so both pockets grew resin roofs
    # -- measured by rebuilding the brace on the same board with the heights reverted),
    # and +14.17 mm3 is the U6/U9 re-route moving the brace's computed footprint. The
    # drift spans THREE board changes, not one, because every kibot run since the
    # 2026-08-04 commit-back died at schematic parity BEFORE reaching this gate -- the
    # first run to get this far carried all of it. Local regeneration reproduces CI's
    # 2070.29 to the hundredth; interference_drc and assembly_drc (skipped when the step
    # died) were run on that geometry and pass. Same transition note as above: the
    # committed STL stays at the old volume until the merge-run rebuild.
    #
    # Re-ledgered again 2026-08-05 (same day), 2070.29 -> 2084.47: DRH deleted SB1-SB4
    # and R12 (TINY mode removed with them), so the brace's pocket count fell 53 -> 48
    # and the five voids' volume returned to resin (+14.18 mm3 total). R3 and R18 moved
    # in the same session -- their pockets relocate but keep their geometry, net ~0.
    # interference_drc (worst margin +0.16, D2) and assembly_drc (0/0) were run on the
    # regenerated solid. Transition note as above: the committed STL reads 2070.29
    # until the merge-run rebuild.
    "solar-glow-drh-diffuser-brace.stl": dict(
        volume_mm3=2084.47, bbox=(-22.85, -42.4, 0.0, 24.35, 42.4, 1.8),
        max_boundary_edges=0, max_open_len_mm=0.0, max_degenerate=0),
}
VOL_TOL = 0.005
BBOX_TOL = 0.01


def check_one(path, base):
    import numpy as np
    import trimesh
    m = trimesh.load(str(path), force="mesh")
    probs = []

    e = m.edges_sorted
    uniq, cnt = np.unique(e, axis=0, return_counts=True)
    open_e = uniq[cnt == 1]
    open_len = float(np.linalg.norm(
        m.vertices[open_e[:, 0]] - m.vertices[open_e[:, 1]], axis=1).sum()) if len(open_e) else 0.0
    degen = int((m.area_faces < 1e-9).sum())

    if len(open_e) > base["max_boundary_edges"]:
        probs.append(f"{len(open_e)} boundary edges (ledger allows {base['max_boundary_edges']})")
    if open_len > base["max_open_len_mm"]:
        probs.append(f"open-edge length {open_len:.3f} mm (ledger allows "
                     f"{base['max_open_len_mm']}) -- that is a real hole")
    if degen > base["max_degenerate"]:
        probs.append(f"{degen} degenerate facets (ledger allows {base['max_degenerate']})")
    if not m.is_winding_consistent:
        probs.append("winding is INCONSISTENT (flipped normals)")

    dv = abs(m.volume - base["volume_mm3"]) / base["volume_mm3"]
    if dv > VOL_TOL:
        probs.append(f"volume {m.volume:.2f} mm3 is {dv * 100:.2f}% from baseline "
                     f"{base['volume_mm3']} (tol {VOL_TOL * 100:.1f}%)")
    bb = list(m.bounds.flatten())
    for got, want, ax in zip(bb, base["bbox"], ("x0", "y0", "z0", "x1", "y1", "z1")):
        if abs(got - want) > BBOX_TOL:
            probs.append(f"bbox {ax} = {got:.4f} vs baseline {want} (tol {BBOX_TOL})")

    tag = "ok" if not probs else "FAIL"
    print(f"  {tag}: {path.name} -- {len(m.faces)} tris (not gated), "
          f"vol {m.volume:.2f} mm3, open edges {len(open_e)} ({open_len:.3f} mm), "
          f"degenerate {degen}")
    for p in probs:
        print(f"        {p}")
    return probs


def main():
    stls = sorted((ROOT / "enclosure").glob("*.stl")) + sorted((ROOT / "enclosure" / "brace").glob("*.stl"))
    fails = []
    seen = set()
    for p in stls:
        base = BASELINE.get(p.name)
        if base is None:
            fails.append(f"{p.name}: no BASELINE ledger entry -- a new artifact "
                         "must arrive with its row (measure it, add it, same commit)")
            print(f"  FAIL: {p.name} -- unledgered STL")
            continue
        seen.add(p.name)
        fails.extend(f"{p.name}: {x}" for x in check_one(p, base))
    for name in BASELINE:
        if name not in seen:
            fails.append(f"{name}: ledgered but missing from enclosure/")
            print(f"  FAIL: {name} -- ledgered but not found")
    if fails:
        print(f"check_mesh: {len(fails)} problem(s)")
        return 1
    print(f"check_mesh: {len(seen)} STL(s) match their ledger")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
