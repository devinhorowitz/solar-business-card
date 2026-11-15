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
      single rim point, (24.4, -34.45, 2.7)) plus 1 zero-area facet (3 until
      the 2026-11 medallion fix) -- cosmetic, ledgered, and gated so anything
      WORSE (a real hole has nonzero open length) goes red.
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

# filename -> ledger. (The shell's name said v3_0 until the 2026-08-19 rename, while the
# geometry had been the current v4 solid throughout; these keys moved with it.)
BASELINE = {
    "solar-glow-drh-v4_0-backshell-0p6b-brace-Ti-max.stl": dict(
        # re-ledgered 2026-08-07 (cap scoot + part-aware ring reliefs, fit_rules.RING --
    # the ring gave up 191.3 mm2 x 1.8 around ten parts, six of which it had been
    # CRUSHING; volume was 5620.24 pre-scoot):
    # re-ledgered 2026-08-07 night (RN1 array consolidation: R1-R4 keepouts returned,
    # RN1 0.45 pocket cut; prior: center consolidation; ring reliefs follow the
    # moved caps; was 5257.58 after the scoot, 5620.24 before):
    # re-ledgered 2026-08-08 (moat round: SC3 -1.52 mm west + the LDO island's move into
    # the SC3/SC4 bay re-carved the S-band ring reliefs; was 5266.02):
    # re-ledgered 2026-11-12, 5289.20 -> 5320.50, with the three fixes that came out of an
    # independent measurement of the committed STEPs. ITEMISED by building each state, and
    # the starting point is not assumed: this toolchain rebuilds main's five solids
    # byte-identical to the committed ones (the STL here read 5290.34, inside the old
    # tolerance), so every delta below is this generator's, not the measurer's.
    #
    #   -14.51  the eight mount bosses are finally scalloped (fit_rules.boss_fouls). The
    #           keep-outs cover 8.186 mm2 of the eight discs; x 1.80 is 14.73, and the
    #           0.22 short of that is the 0.10 boss-top chamfer, already gone there.
    #   +44.79  the cavity void no longer runs under the rim wall: 24.896 mm2 x 1.80 =
    #           44.81 predicted. Those were the four downward faces at seat level.
    #    -0.12  the medallion's three families simplified as one coverage: 804 island
    #           slivers stop poking into cuts, and the cut areas shift by a hair.
    #
    # 5290.34 - 14.51 + 44.79 - 0.12 = 5320.50. bbox unchanged. The rim pinch is still
    # there (1 zero-length boundary edge at (24.4, -34.45, 2.7)); the zero-area facets
    # fell 3 -> 1, and max_degenerate follows the measurement down so that a return to 3
    # is a finding rather than a pass. Triangles 55,245 -> 47,767, not gated.
    # Transition note, as every entry here carries: the COMMITTED STL reads 5290.34 until
    # the merge-run rebuild, so a local check_mesh is red for exactly that one transition.
    # re-ledgered 2026-11-13, 5320.50 -> 5292.87: the supercaps take their own bay
    # clearance out of the bosses (fit_rules.boss_fouls -> part_keepout), 0.75 off a free
    # edge where it was 0.20 off a nominal can. 15.404 mm2 more of the eight discs x 1.80 =
    # 27.73 predicted, 27.63 measured; the 0.10 short is the boss-top chamfer, as above.
    # bbox, the rim pinch and the 1 degenerate facet unchanged; triangles 47,501, ungated.
    # re-ledgered 2026-11-13 (later, the enclosure calls round), 5292.87 -> 5289.66, NOT
    # itemised by building each state (a build is ~13 min); the plan-area terms are
    # computed from fit_rules and sum to within 0.15 of the measured delta:
    #   -6.98  cavity-level metal: the lip bands step a tool radius past every part and measure
    #           the caps at max material (void +5.270 mm2), and six Ø2.0 bores reach the boss
    #           keep-out corners (boss islands -2.477): net -3.880 mm2 x 1.80.
    #   +1.97  the rim top and recess mouth lose their second facet: 0.00355 mm2 back per mm of
    #           edge, ~554 mm of it.
    #   +1.65  the east lip's top is no longer stepped: the break that took 0.25 x 0.10 off its
    #           inner edge over 65.86 mm takes a 0.10 x 0.10 triangle now.
    # bbox unchanged. THE PINCH MOVED: the one at (24.4, -34.45) was the notch of the scalar lip
    # outline at board (49.80, 10.00), and went with it. Each edge-break cutter now leaves ONE
    # zero-length seam where the south band-step fillet at x 27.0 meets its wall, board
    # (27.05, 0.78), with the three zero-area facets of the same seam beside it --
    # one cutter here, the lip break, at z 2.65.
    # Open length 0.000; more seams, or one with length, is a finding.
    # re-ledgered 2026-11-14, 5289.66 -> 5289.51: the two east mid-span bosses hollowed back to
    # COIL_CLR from the NFC coil (fit_rules.boss_coil_cuts). 0.0759 + 0.0091 mm2 of boss x 1.80
    # = 0.153 predicted, 0.150 measured. bbox, seam and facets unchanged.
    # re-ledgered 2026-11-14 (later), 5289.51 -> 5307.10: each boss is joined to the wall
    # (fit_rules "BLENDS and WEBS"). Twelve blends where a boss crosses the lip's wall -- ten
    # at R2.00, two at R1.00 beside the ferrite sheet -- 8.271 mm2, and four webs in the
    # slots beside the corner bosses, 1.370 mm2: 9.641 mm2 x 1.80 = 17.35 predicted, 17.59
    # measured. The 0.24 over is the lip's and the bosses' edge-breaks along the stretches
    # that are inside metal now. bbox, seam and facets unchanged. Triangles 48,801, ungated.
    # re-ledgered 2026-11-14 (later still), 5307.10 -> 5312.64: each back annulus is joined to
    # the proud frame (fit_rules.back_blends). Sixteen R2.00 blends, 10.678 mm2 x 0.15 = 1.60,
    # and the reeded valleys give way to them (fin_runs): 12.693 mm2 less valley x 0.60 = 7.62,
    # less the rib metal that went with it, 5.382 mm2 x 0.70 = 3.77. 1.60 + 7.62 - 3.77 = 5.45
    # predicted, 5.54 measured (the rest is edge-break). bbox, seam and facets unchanged.
    # Triangles 52,505, ungated.
    # re-ledgered 2026-11-14 (the contouring pass), 5312.64 -> 5301.51: the bosses and the two
    # short-edge tabs made even, symmetric and round-cornered (fit_rules "EVEN AND SYMMETRIC",
    # "ROUNDS", tab_rounds). Only ever less metal: 6.260 mm2 in plan -- 3.720 off the eight
    # boss islands (one flat distance, full-chord flats, the coil hollow mirrored, twenty R1.00
    # rounds), 1.361 less blend (the twins of the two the ferrite holds to R1.00), 0.983 off
    # the lip (the ring's strip beside the south tab, four R1.00 tip rounds) -- x 1.80 = 11.27
    # predicted, 11.13 measured (the difference is edge-break that went with the metal). bbox,
    # seam and facets unchanged. Triangles 53,372, ungated.
    # re-ledgered 2026-11-15 (the simpler cuts), 5301.51 -> 5269.77: DRH asked for "smooth
    # contiguous surfaces for the milling to be done simpler". Three things, 17.590 mm2 less
    # metal in plan: the west lip one width the whole edge, 2.25 (it was 2.50 with a step at
    # R16 and one at C24 -- fit_rules.LIP_ONE_WIDTH); the two east mid-span bosses cut straight
    # across for the coil, 2.32 from the axis on both sides, in place of a hollow and a hump
    # (boss_coil_cuts; the islands lose 1.854, their blends 0.161); and the four tab roots
    # true R1.00 cylinders on the recess wall (tab_roots; +0.18, they are laid out 0.05
    # further in). x 1.80 = 31.66 predicted, 31.74 measured. bbox unchanged.
    # AND THE SEAM IS GONE. The one zero-length seam and its three zero-area facets were "where
    # the south band-step fillet at x 27.0 meets its wall" -- the kink the old tab root made
    # with the recess wall. With the root tangent to that wall there is nothing for the break
    # cutter to pinch: 0 open edges, 0 degenerate, and the ledger holds it there now.
    # Triangles 52,608, ungated.
    # re-ledgered 2026-11-15 (the floor fillets), 5269.77 -> 5296.11: the floor meets the wall
    # through an R1.00 on the eight long straight walls of the supercap bays
    # (fit_rules.floor_runs), 133.37 mm of it. The fillet's section as cut is 0.2108 mm2 (a
    # tangent one's is 0.2146; each cylinder is set 0.002 into wall and floor), so 28.11 mm3
    # before the sixteen run ends are scooped; 26.23 measured on the STEP, 26.34 here.
    # bbox unchanged; 0 open edges, 0 degenerate. Triangles 53,712, ungated.
    # re-ledgered the same day (the runs evened top for bottom), 5296.11 -> 5296.00: the run
    # east of the south tab starts 0.5 mm later, to match its twin on the north wall
    # (fit_rules.floor_runs, EVENED -- CI run 663's handedness gate). 132.86 mm of fillet;
    # 0.2108 mm2 x 0.5 = 0.105 predicted, 0.109 measured on the STEP and 0.11 here. Inside this
    # ledger's tolerance, so the gate did not ask; re-ledgered so the number is the part's.
    volume_mm3=5296.00, bbox=(-26.35, -45.4, -0.15, 26.35, 45.4, 3.4),
        max_boundary_edges=0, max_open_len_mm=0.0, max_degenerate=0),
    "solar-glow-drh-pogo-testplate.stl": dict(
        # re-ledgered 2026-11-13: the y range flips, -10.4..99.3 -> -99.3..10.4, and nothing
        # else moves (the rebuilt STL measures the same volume as the one it replaces, to
        # 1e-4 mm3). The plate is modelled in bare board coordinates, y DOWN, and every solid
        # is written right-handed now -- file y = -board y (fit_rules, THE FILE FRAME).
        # THIS ROW IS THE PLATE'S OWN HANDEDNESS GATE: it is the one un-centred solid here, so
        # its box is not symmetric in y and a plate written in the old frame lands 89 mm
        # outside it. The shells' and braces' boxes ARE symmetric in y and cannot tell either
        # hand from the other; scripts/handedness_drc.py holds those to KiCad's own export.
        # re-ledgered 2026-11-13, 50860.32 -> 50867.96. Not a geometry change: this gate's own
        # trimesh reads 50867.96 on the committed bytes at 4e88213, 575be73 and 9a90a36 -- every
        # plate committed since the old figure was written -- and SolidCraft, a kernel that owes
        # this repo nothing, measures the same. The old figure matched no committed plate and
        # passed only inside VOL_TOL. TODO.md's 9a90a36 record, D1.
        volume_mm3=50867.96, bbox=(-10.4, -99.3, -17.8, 61.2, 10.4, 10.0),
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
    # re-ledgered 2026-08-07 evening (center consolidation: footprint 1486.7 -> 1374.8,
    # leg area traded to the horizontal cap scoots by design; was 2227.07):
    # re-ledgered 2026-08-08 (RN2 consolidation + the C8 scoot to U5's west quadrant:
    # R10/R11/C7 pockets out, RN2 pocket in, C8's pocket moved -- and the RN2-C8
    # thin-wall bridge left with it; 48 pockets, footprint 1374.3 mm2; was 2055.08):
    # re-ledgered 2026-08-08 (LDO-island migration + DRH's Q2/R18/RN1/SW2 re-spread:
    # footprint 1374.3 -> 1316.7 mm2, coverage 34.4% -> 32.9%, floor re-ledgered 0.33 -> 0.32
    # in fit_rules WITH the trade named -- the same round raised the LITE brace; was 2058.35):
    # re-ledgered 2026-08-08 late (DRH's post-shrink compaction: SC3 -0.457 west restoring
    # the cap-scoot standoff -- SC3 is a brace BLOCKER, so the footprint recomputed
    # 1316.7 -> 1329.6 mm2, coverage 32.9% -> 33.2%, 50 pockets; value is the pinned CI
    # run's own measurement, local rebuild agreed to the digit; was 1938.74):
    # re-ledgered 2026-08-23 evening (ANISOTROPIC bays: the uniform 0.75 became CLR_DATUM
    # 0.25 on the two shim-indexed edges and CLR_FREE 0.75 on the two that absorb the can's
    # +0.50 body tolerance. Footprint 1218.4 -> 1320.3 mm2, coverage 30.46% -> 33.01%, floor
    # restored 0.30 -> 0.32; 101.9 of the 111.2 mm2 the widening cost is back, 92%. Value is
    # CI's own measurement -- cadquery is absent from the dev container. Run 622 reports
    # 1945.61: +176.66 mm3 against +183.42 predicted (101.9 mm2 x 1.80), a 3.7% residual,
    # the same shape as the widening round's 3.4% -- footprint that sits under a pocket
    # rather than cutting through. Was 1768.95):
    # re-ledgered 2026-08-23 (CLR_EXCEPTIONS: SC1-SC4 given 0.75 mm in-plane clearance for
    # HAND-SOLDER slop, vs 0.25 for machine-placed parts -- fit_rules has the rotation
    # arithmetic that sized it. Footprint 1329.6 -> 1218.4 mm2, coverage 33.25% -> 30.46%,
    # floor re-ledgered 0.32 -> 0.30 WITH the reason. The caps cut THROUGH, so the loss is
    # full-thickness: 111.2 mm2 x 1.80 = 200.2 mm3 predicted vs 193.45 measured, the 3.4%
    # residual being footprint that sat under a pocket rather than through. bbox unchanged
    # (only interior bays widened); still watertight, 0 open edges, 0 degenerate, 1 piece.
    # THIS GATE IS WHY THE VALUE IS TRUSTWORTHY: cadquery is absent from the dev container,
    # so the solid could not be rebuilt locally -- the number below is CI's own measurement
    # off the regenerated STL; was 1962.40):
    # re-ledgered 2026-11-12, 1945.61 -> 1933.44, AND THE BBOX MOVES, which is the point:
    # x1 24.35 -> 24.10. The brace was 0.20 mm wider than the cavity it drops into (east
    # face board x 49.750 against a shell wall at 49.550), because it was cut from the
    # scalar rectangle fit_rules._CAV while the shell was cut from cavity_void_poly(). It
    # is cut from fit_rules.brace_cavity() now: east face x 49.500, 0.05 inside the wall.
    # Footprint 1320.346 -> 1313.584 mm2; 6.762 x 1.80 = 12.17 predicted, 12.17 measured
    # -- no residual this time, because the strip that went is full-height resin with no
    # pocket in it. Coverage reads 33.01 % before and after: the denominator lost the same
    # strip. This one was rebuilt locally (cadquery 2.8.0, the pin CI uses) and the build
    # of main it was compared against is byte-identical to the committed STL. Still one
    # piece, watertight, 0 open edges, 0 degenerate. Transition note as above.
    # re-ledgered 2026-11-13, 1933.44 -> 1919.16, ITEMISED by building each state:
    #    -7.38  the pocket-pair pass bridges at SLA_WALL 0.60, not a bare 0.40 (25 pairs).
    #    -6.90  every level opened at SLA_WALL -- 6.90 predicted from the opened plan of
    #           each band, 6.90 measured. This is what removed the 0.0068 mm wall (C24's
    #           pocket against SC3's bay) and every other sub-0.10 wall SolidCraft found.
    # bbox unchanged; still one piece, watertight, 0 open edges, 0 degenerate, and no
    # facet that is neither horizontal nor vertical (a grid-snapped cutter once put one
    # there by inflating a vertex tolerance; the brace CAD's comment has it).
    # re-ledgered 2026-11-13 (later), 1919.16 -> 1918.42: the brace is cut to the cavity AS
    # MILLED (fit_rules.cavity_as_milled) -- it had run 0.225 mm into the R1.0 the Ø2.0 leaves
    # at the east boss-to-wall corners. Footprint 1313.584 -> 1313.172 mm2; 0.413 x 1.80 = 0.74
    # predicted, 0.74 measured. bbox unchanged; one piece, watertight, 0 open, 0 degenerate.
    # re-ledgered 2026-11-14, 1918.42 -> 1917.48, ITEMISED by building the middle state: the
    # part_heights 0603 row corrected to datasheet max (C4/C13 0.90 -> 0.95, C23 0.90 -> 1.00;
    # the part_heights comment has the sweep that found them):
    #    -0.470  C4/C13 pockets 0.05 deeper. 2 x 4.28 mm2 (0603 pad box + 0.25) x 0.05 = 0.43
    #            predicted; the rest is the U6-C4, C6-C4 and C13-RN1 bridges, which take the
    #            deeper pocket's depth.
    #    -0.467  C23's pocket 0.10 deeper. 4.28 x 0.10 = 0.43 predicted; the rest is the
    #            FB1-C23 and C23-U9 bridges.
    # Still blind pockets (1.00 <= SPAN_LIMIT 1.18), through-holes still none. The LITE brace
    # is byte-identical: all four 0603s were already through-holes at its 0.60 span. bbox
    # unchanged; one piece, watertight, 0 open, 0 degenerate. Transition note as above.
    # re-ledgered 2026-11-14 (later), 1917.48 -> 1917.45: the ridge east of the ferrite channel
    # ends square where it would be under fit_rules.PRINT_WALL -- its two feather tips, y 31.40-
    # 31.67 and 57.23-57.50, 0.036 mm2 each over the channel's 0.33. The lite brace loses the
    # same two tips. bbox unchanged; watertight, 0 open, 0 degenerate.
    # re-ledgered 2026-11-14 (later still), 1917.45 -> 1916.61: the brace is cut to the cavity
    # as milled, and at the two WEST bosses beside its band the cavity now has an R2.00 blend
    # where it had the finisher's R1.00. Footprint 1313.17 -> 1312.70 mm2; x 1.80 is 0.85,
    # measured 0.84. The two east corners -- and with them the ridge east of the ferrite
    # channel, y 31.68-57.22 -- did not move: the blends there are held to R1.00 by the
    # ferrite sheet. bbox unchanged; watertight, 0 open, 0 degenerate.
    # re-ledgered 2026-11-15 (the simpler cuts), 1916.61 -> 1926.67, and the bbox's west face
    # -22.85 -> -23.10: the west lip is 2.25 wide the whole edge now, and the brace follows
    # the wall it bears on (fit_rules.cavity_rect -- left at the old 2.50 it would have stood
    # 0.30 off that wall, free to slide the quarter millimetre its pockets clear a part by).
    # Footprint 1312.70 -> 1319.30 mm2: +6.04 the strip down the west side, +0.56 beside the
    # two east mid-span bosses, now cut straight. x 1.80 would be 11.88; 10.06 measured, the
    # rest being the pockets of the parts the new strip reaches. Watertight, 0 open, 0
    # degenerate.
    volume_mm3=1926.67, bbox=(-23.10, -42.4, 0.0, 24.10, 42.4, 1.8),
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
        # re-ledgered 2026-08-08 (moat round, same reliefs story as max; was 3905.03):
        # re-ledgered 2026-11-12, 3920.73 -> 3942.06 (the committed STL read 3921.50):
        # -9.80 the boss scallops (8.186 mm2 x 1.22 = 9.99 less the boss-top chamfer),
        # +30.36 the void out from under the rim wall (24.896 x 1.22 = 30.37). No
        # medallion here, so no third term. The max entry has the story.
        # re-ledgered 2026-11-13, 3942.06 -> 3923.35: the free-edge boss flats, 15.404 mm2
        # x 1.22 = 18.79 predicted, 18.71 measured (the max entry has the reason).
        # re-ledgered 2026-11-13 (later, the enclosure calls round), 3923.35 -> 3922.31, NOT
        # itemised by building each state (a build is ~13 min); the plan-area terms are
        # computed from fit_rules and sum to within 0.07 of the measured delta:
        #   -4.73  cavity-level metal: the lip bands step a tool radius past every part and measure
        #           the caps at max material (void +5.270 mm2), and six Ø2.0 bores reach the boss
        #           keep-out corners (boss islands -2.477): net -3.880 mm2 x 1.22.
        #   +1.97  the rim top and recess mouth lose their second facet: 0.00355 mm2 back per mm of
        #           edge, ~554 mm of it.
        #   +1.65  the east lip's top is no longer stepped: the break that took 0.25 x 0.10 off its
        #           inner edge over 65.86 mm takes a 0.10 x 0.10 triangle now.
        # bbox unchanged. THE PINCH MOVED: the one at (24.4, -34.45) was the notch of the scalar lip
        # outline at board (49.80, 10.00), and went with it. Each edge-break cutter now leaves ONE
        # zero-length seam where the south band-step fillet at x 27.0 meets its wall, board
        # (27.05, 0.78), with the three zero-area facets of the same seam beside it --
        # one cutter, z 1.67.
        # Open length 0.000; more seams, or one with length, is a finding.
        # re-ledgered 2026-11-14, 3922.31 -> 3922.21: the coil relief in the two east mid-span
        # bosses, as the max shell. 0.085 mm2 x 1.22 = 0.104 predicted, 0.100 measured.
        # re-ledgered 2026-11-14 (later), 3922.21 -> 3934.15: the twelve blends and four webs
        # that join each boss to the wall, 9.641 mm2 x 1.22 = 11.76 predicted, 11.94 measured
        # (the rest is buried edge-break, as on max). bbox, seam and facets unchanged.
        # re-ledgered 2026-11-14 (later still), 3934.15 -> 3935.83: the sixteen back blends,
        # 10.678 mm2 x 0.15 = 1.60 predicted, 1.68 measured. No rear art here, so nothing
        # gives way. bbox, seam and facets unchanged.
        # re-ledgered 2026-11-14 (the contouring pass), 3935.83 -> 3928.31: bosses and tabs
        # even, symmetric and round-cornered, 6.260 mm2 x 1.22 = 7.64 predicted, 7.52 measured.
        # bbox, seam and facets unchanged.
        # re-ledgered 2026-11-15 (the simpler cuts), 3928.31 -> 3906.80: one-width west lip,
        # straight cuts on the two east mid-span bosses, true tab roots -- as the max shell.
        # 17.590 mm2 x 1.22 = 21.46 predicted, 21.51 measured. bbox unchanged. The seam at the
        # old tab root's kink is gone: 0 open edges, 0 degenerate, held there now.
        # re-ledgered 2026-11-15 (the floor fillets), 3906.80 -> 3933.15: the same eight runs
        # as the max shell, +26.23 on the STEP and +26.35 here; 0.67 % of this shell, so the
        # tolerance caught it. bbox unchanged; 0 open edges, 0 degenerate.
        # re-ledgered the same day (the runs evened top for bottom), 3933.15 -> 3933.04: as the
        # max shell, the south run east of the tab 0.5 mm shorter. Inside the tolerance.
        volume_mm3=3933.04, bbox=(-26.35, -45.4, -0.15, 26.35, 45.4, 2.42),
        max_boundary_edges=0, max_open_len_mm=0.0, max_degenerate=0),
    "solar-glow-drh-frame-air-316L.stl": dict(
        # air: OPEN frame, no floor -- walls + recess + 8 bosses only, z 0..1.80 exactly
        # (nothing below the resting plane; the M2x1.6 tip hides 0.20 inside the boss
        # spotface). Verified open: a ray up through the card centre hits zero surfaces.
        # re-ledgered 2026-08-07 (cap scoot + ring reliefs; was 1182.62):
        # re-ledgered 2026-08-08 (moat round: SC3 nudge re-keyed the frame's ring reliefs;
        # was 960.49):
        # re-ledgered 2026-11-12, 975.93 -> 996.92 (the committed STL read 976.68):
        # +29.86 the void out from under the rim wall (24.896 mm2 x 1.20 = 29.88), -9.62
        # the boss scallops WITH their 45-degree feet (8.186 x 1.20 = 9.82 less the
        # boss-top chamfer). The feet are specific to this variant: on an open frame the
        # boss foot is the resting face, and OCC's chamfer cannot break an end face once a
        # boss on it carries a flat, so the scallop cutter carries the break itself (shell
        # CAD, _boss_scallop_tool). A build that reads ~999.8 here has LOST the resting-face
        # edge-break -- that is what the first draft of the scallop did, silently.
        # re-ledgered 2026-11-13, 996.92 -> 978.57: the free-edge boss flats, 15.404 mm2 x
        # 1.20 = 18.48 predicted, 18.35 measured; the feet came with them (the shortfall is
        # the same chamfer-and-foot share as before), so the warning above still holds.
        # re-ledgered 2026-11-13 (later, the enclosure calls round), 978.57 -> 978.58, NOT
        # itemised by building each state (a build is ~13 min); the plan-area terms are
        # computed from fit_rules and sum to within 0.06 of the measured delta:
        #   -4.66  cavity-level metal: the lip bands step a tool radius past every part and measure
        #           the caps at max material (void +5.270 mm2), and six Ø2.0 bores reach the boss
        #           keep-out corners (boss islands -2.477): net -3.880 mm2 x 1.20.
        #   +2.96  the rim top and recess mouth lose their second facet: 0.00355 mm2 back per mm of
        #           edge, ~554 mm of it, and the resting rim's, ~280 mm more.
        #   +1.65  the east lip's top is no longer stepped: the break that took 0.25 x 0.10 off its
        #           inner edge over 65.86 mm takes a 0.10 x 0.10 triangle now.
        # bbox unchanged. THE PINCH MOVED: the one at (24.4, -34.45) was the notch of the scalar lip
        # outline at board (49.80, 10.00), and went with it. Each edge-break cutter now leaves ONE
        # zero-length seam where the south band-step fillet at x 27.0 meets its wall, board
        # (27.05, 0.78), with the three zero-area facets of the same seam beside it --
        # TWO cutters here, the lip break (z 1.05) and the resting face's (z 0.15), so two
        # seams and four facets.
        # Open length 0.000; more seams, or one with length, is a finding.
        # The resting-face break is a boolean now (the shell CAD, _resting_face_break): ~999.8 here
        # still means it was lost.
        # re-ledgered 2026-11-14, 978.58 -> 978.48: the coil relief in the two east mid-span
        # bosses, with its 45-degree foot at the resting face. 0.085 mm2 x 1.20 = 0.102
        # predicted, 0.099 measured. Still two seams and four facets.
        # re-ledgered 2026-11-14 (later), 978.48 -> 990.31: the twelve blends and four webs,
        # 9.641 mm2 x 1.20 = 11.57 predicted, 11.83 measured. More over than on the floored
        # shells because here the buried edge-breaks are at both ends: the seat and the
        # resting face. Both seams and the four facets are where they were.
        # re-ledgered 2026-11-14 (the contouring pass), 990.31 -> 982.99: bosses and tabs even,
        # symmetric and round-cornered, 6.260 mm2 x 1.20 = 7.51 predicted, 7.32 measured -- and
        # 0.74 % of this frame, so the tolerance caught it, as it should. Both seams and the
        # four facets are where they were.
        # re-ledgered 2026-11-15 (the simpler cuts), 982.99 -> 961.83: one-width west lip,
        # straight cuts on the two east mid-span bosses, true tab roots -- as the max shell.
        # 17.590 mm2 x 1.20 = 21.11 predicted, 21.16 measured; 2.15 % of this frame. bbox
        # unchanged. BOTH seams (the lip break's and the resting face's, at the old tab
        # root's kink) and their four facets are gone: 0 open edges, 0 degenerate, held there.
        volume_mm3=961.83, bbox=(-26.35, -45.4, 0.0, 26.35, 45.4, 1.8),
        max_boundary_edges=0, max_open_len_mm=0.0, max_degenerate=0),
    "solar-glow-drh-diffuser-brace-lite.stl": dict(
        # the lite brace: gap 1.22, span 0.60, 31 pockets, 0 through-holes, single piece
        # (307.2 mm2 dropped post-consolidation -- recovery plan: TODO.md's lite-brace
        # relocation entry). bbox y1 is NOT the cavity edge: the main piece only reaches
        # the full cavity span -- the center spine is continuous since the 2026-08-07 consolidation.
        # re-ledgered 2026-08-07 (cap scoot: footprint 935.7 -> 1078.2 mm2, dropped islands
        # 344.6 -> 277.0 in 3; main piece now reaches board y 59.2; was 935.48):
        # re-ledgered 2026-08-07 evening: the consolidation CONNECTED the north corridors --
        # the lite main piece now spans the full cavity length (bbox y1 14.76 -> 42.4),
        # one continuous center spine; was 1098.51:
        # re-ledgered 2026-08-08 (RN2 consolidation + the C8 scoot: R10/R11/C7 pockets
        # out, RN2 pocket in, C8's pocket moved; 30 pockets, footprint 1060.2 mm2,
        # dropped 307.2 in 4; was 1111.05):
        # re-ledgered 2026-08-08 (the island's blockers left the west corridor for the
        # SC bay: footprint 1060.2 -> 1087.2 mm2, coverage 26.5% -> 27.2% -- the campaign's
        # target variant GAINED; was 1114.04):
        # re-ledgered 2026-08-08 late (DRH's post-shrink compaction: SC3 -0.457 west, a
        # lite-brace blocker too -- footprint 1087.2 -> 1100.2 mm2, coverage 27.2% -> 27.5%,
        # still 30 pockets; the target variant gained AGAIN. Value is the pinned CI run's
        # own measurement, local rebuild agreed to the digit; was 1147.82):
        # re-ledgered 2026-08-23 evening (same anisotropy round: footprint 990.9 -> 1090.9
        # mm2, coverage 24.78% -> 27.28%, floor restored 0.24 -> 0.25. CI run 622 measures
        # 1152.51: +116.22 against +122.00 predicted (100.0 mm2 x 1.22), 4.7% residual.
        # Was 1036.29):
        # re-ledgered 2026-08-23 (same CLR_EXCEPTIONS round -- the caps are hand-soldered in
        # this variant too: footprint 1100.2 -> 990.9 mm2, coverage 27.51% -> 24.78%, floor
        # 0.25 -> 0.24. 109.3 mm2 x 1.22 = 133.3 mm3 predicted vs 127.62 measured; was 1163.91):
        # re-ledgered 2026-11-12, 1152.51 -> 1144.28, bbox x1 24.35 -> 24.10: the same
        # 0.25 mm east strip as the max brace, for the same reason. Footprint 1090.875 ->
        # 1084.123 mm2; 6.752 x 1.22 = 8.24 predicted, 8.23 measured. Coverage 27.28 % ->
        # 27.25 % of the true cavity, floor kept at 0.25.
        # re-ledgered 2026-11-13, 1144.28 -> 1136.29: the level opening at SLA_WALL, all of
        # it -- no lite pocket pair sat between 0.40 and 0.60, so the threshold change alone
        # moves nothing here (measured: 1144.28 exactly). The max entry has the story.
        # re-ledgered 2026-11-13 (later), 1136.29 -> 1135.81: cut to the cavity as milled, as
        # the max brace. Footprint 1084.123 -> 1083.728; 0.395 x 1.22 = 0.48, 0.48 measured.
        # re-ledgered 2026-11-14, 1135.81 -> 1135.78: the channel ridge's two feather tips,
        # as the max brace.
        # re-ledgered 2026-11-14 (later still), 1135.78 -> 1135.28: the same two west corners
        # cut back to the R2.00 blends, as on the max brace. bbox unchanged; watertight.
        # re-ledgered 2026-11-15 (the simpler cuts), 1135.28 -> 1141.41, west face -22.85 ->
        # -23.10: the brace follows the west wall to the one-width lip, as the max brace.
        # Footprint 1083.31 -> 1089.83 mm2; x 1.22 would be 7.95, 6.13 measured (pockets).
        volume_mm3=1141.41, bbox=(-23.10, -42.4, 0.0, 24.10, 42.4, 1.22),
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
