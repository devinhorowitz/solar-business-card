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
        # re-ledgered 2026-08-07 (cap scoot + part-aware ring reliefs, fit_rules.RING --
    # the ring gave up 191.3 mm2 x 1.8 around ten parts, six of which it had been
    # CRUSHING; volume was 5620.24 pre-scoot):
    volume_mm3=5257.58, bbox=(-26.35, -45.4, -0.15, 26.35, 45.4, 3.4),
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
    # Re-ledgered 2026-08-07, 2084.47 -> 2102.49, and ITEMISED by rebuilding the brace on
    # each intermediate state rather than copying the failing run's number. The baseline
    # state (b953334's board + b953334's part_heights) rebuilds to 2084.19 here, 0.28 mm3
    # (0.013%) off the ledgered 2084.47 -- tessellation noise, well inside VOL_TOL -- so
    # the decomposition below starts from a reproduced baseline, not an assumed one:
    #
    #   -8.02  the BOARD alone (current board, b953334 heights = 2076.17). Dominated by
    #          C25-C27's 0805 -> low-profile 1206 lands: physically bigger footprints, and
    #          at the then-declared 1.45 they were still THROUGH-holes, so the bigger
    #          voids removed more resin. U6's SC-70 -> DSBGA and Q2's SOT-23 -> SOT-523
    #          land shrinkage push the other way but are much smaller.
    #  +22.30  C25/C26/C27 1.45 -> 0.95 (the low-profile 1206 respin). THE DOMINANT TERM,
    #          and it is a state change, not a depth change: 1.45 > SPAN_LIMIT 1.18 made
    #          each a through-hole; 0.95 < 1.18 makes each a blind pocket with a resin
    #          roof. Three roofs came back.
    #   +2.90  C9 1.25 -> 0.90 (0805 -> 0603 respin). Same threshold crossing: one more
    #          through-hole became a blind pocket.
    #   +1.12  U6 1.10 -> 0.50 (SC-70 -> DSBGA). Already a pocket either way; this is just
    #          0.60 mm less depth over the DSBGA's small footprint.
    #   +0.00  Q2 1.20 -> 0.90 -- EXACTLY zero, measured, not assumed. Q2 sits OUTSIDE
    #          brace_footprint() (it falls in the NFC coil notch, east of COIL_EAST), so
    #          it has no pocket and the brace never reads its height. Reverting Q2 alone
    #          reproduces 2102.49 to the hundredth. Its part_heights entry is still
    #          correct and load-bearing for check [7] and interference_drc -- just not
    #          for this solid.
    #
    # Net 2084.19 -> 2102.49 = +18.30. The drift again spans SEVERAL board changes rather
    # than one, for the same reason as the 2026-08-05 entry above: every kibot run between
    # the C25-C27 respin and now died before reaching this gate -- first at schematic
    # parity, then at the 5h29m GitHub Actions outage of 2026-08-06. This was the first run
    # to get here, so it carried the whole accumulation.
    #
    # Transition note, as above: the COMMITTED STL still reads 2084.47 until the merge-run
    # rebuild, so a local check_mesh is red for exactly this one transition. Verified on
    # the regenerated solid: watertight, 0 open edges, 0 degenerate, bbox unchanged, and
    # assembly_drc 0/0. (interference_drc has its own NEW, unrelated failure on C7 -- see
    # the C7 note wherever that lands; it is a board-geometry question, not a mesh one.)
    "solar-glow-drh-diffuser-brace.stl": dict(
        # re-ledgered 2026-08-07 (cap scoot: footprint 1413.8 -> 1486.7 mm2; was 2102.49):
    volume_mm3=2227.07, bbox=(-22.85, -42.4, 0.0, 24.35, 42.4, 1.8),
        max_boundary_edges=0, max_open_len_mm=0.0, max_degenerate=0),
    # ---- the 2026-08-07 enclosure variants (fit_rules.VARIANTS) --------------------------
    # Ledgered from local builds in the variants commit itself -- the chicken-and-egg rule:
    # an unledgered STL fails inside the same kibot job that first creates it. The STL
    # FILES land via CI's commit-back (kibot builds before this gate runs, so CI is never
    # missing them); a LOCAL run between the variants commit and that commit-back reports
    # the three new files missing -- build them locally or wait for the merge run, the
    # same transition every re-ledgered volume above documents. Both new shells carry the
    # SAME zero-length rim pinch class as Ti-max (1 boundary edge, 0.0000 mm open) plus
    # one degenerate sliver from the tessellator; a real hole (nonzero open length) still
    # goes red.
    "solar-glow-drh-shell-lite-Ti.stl": dict(
        # lite: floor 0.60 + cavity 1.22 (component-limited) + recess 0.60 = 2.42, border
        # 0.15 below z0. No fins, no medallion (physics-forced: valley 0.60 / coin floors
        # would cut a 0.60 floor through).
        # re-ledgered 2026-08-07 (cap scoot + ring reliefs; was 4130.76):
        volume_mm3=3899.32, bbox=(-26.35, -45.4, -0.15, 26.35, 45.4, 2.42),
        max_boundary_edges=1, max_open_len_mm=0.001, max_degenerate=1),
    "solar-glow-drh-frame-air-316L.stl": dict(
        # air: OPEN frame, no floor -- walls + recess + 8 bosses only, z 0..1.80 exactly
        # (nothing below the resting plane; the M2x1.6 tip hides 0.20 inside the boss
        # spotface). Verified open: a ray up through the card centre hits zero surfaces.
        # re-ledgered 2026-08-07 (cap scoot + ring reliefs; was 1182.62):
        volume_mm3=954.90, bbox=(-26.35, -45.4, 0.0, 26.35, 45.4, 1.8),
        max_boundary_edges=1, max_open_len_mm=0.001, max_degenerate=1),
    "solar-glow-drh-diffuser-brace-lite.stl": dict(
        # the lite brace: gap 1.22, span 0.60, 31 pockets, 0 through-holes, single piece
        # (277.0 mm2 dropped in 3 islands post-scoot -- recovery plan: TODO.md's lite-brace
        # relocation entry). bbox y1 is NOT the cavity edge: the main piece only reaches
        # board y ~59 -- the north corridors are the dropped islands.
        # re-ledgered 2026-08-07 (cap scoot: footprint 935.7 -> 1078.2 mm2, dropped islands
        # 344.6 -> 277.0 in 3; main piece now reaches board y 59.2; was 935.48):
        volume_mm3=1098.51, bbox=(-22.85, -42.4, 0.0, 24.35, 14.76, 1.22),
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
