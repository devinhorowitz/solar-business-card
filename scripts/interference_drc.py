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
            on). Board coordinates reach the mesh through fit_rules.file_xy(),
            the one statement of the file frame -- definitional, not derived
            from the mesh (this line said "DERIVED ... not hard-coded" long
            after the code stopped doing that: a bbox-centre offset ray-cast
            the lite brace half a card away from its parts).
  gate   -- min over samples of (available - height) must be >= 0 for every
            part, and every body polygon must sit inside the cavity rect
            unless EDGE_LEDGER excuses it by name. The ledger is audited on
            every run: an entry that excuses nothing fails too.
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

# ---- THE EDGE LEDGER -------------------------------------------------------------------
# refdes -> why that body may escape the bare cavity rectangle, WITH the measurement. Any
# other body that escapes fails the gate, so a part walking into the lip is caught here.
#
# EMPTY SINCE 2026-11-12, and that is the finding. It held seven entries and had excused
# nothing since 2026-08-08. Re-read off the board at every commit that touched it:
#   2026-08-01  the ledger is written: U6, C27, U9, FB1, C22, R15 -- all six escape
#   2026-08-05  U6 and U9 are moved inboard                        -- four escape
#   2026-08-06  R15 follows; C7 lands 0.0400 mm past the west wall
#   2026-08-07  C7 is ledgered at 03:31, with nine lines of measurement -- and the centre
#               consolidation moves it back inside at 19:10 the same day
#   2026-08-08  C7 is DELETED from the board (the 100 nF census, PCB/README.md), and the
#               LDO island takes C27, FB1 and C22 inboard          -- nothing escapes
# and nothing does at any of the ten board commits from that one to 2026-11-12. On today's
# board the six survivors sit 1.131 (C22), 1.609 (R15), 2.413 (U9), 4.141 (FB1), 13.456 (U6) and
# 14.255 mm (C27) INSIDE the rectangle, under a comment still calling C22/FB1 "the ledgered
# 0.95 mm edge cluster", and the seventh entry named a capacitor that did not exist.
#
# A dead entry is not harmless. It is a standing waiver for whatever that refdes does next:
# had U6 been moved back out to the wall, this gate would have passed it on the strength of
# a measurement taken of a different placement. So the ledger audits itself on every run
# (ledger_status), and an entry that excuses nothing FAILS -- the rule
# scripts/drc_exclusion_key.py --check-dead applies to the board's DRC exclusions, and the
# one check_consistency's PENDING_FOOTPRINT_SYNC applies to itself. A new entry is a refdes,
# a reason, and the escape measured on the board the day it is added; it dies in the commit
# that moves or removes the part.
EDGE_LEDGER = {}


def ledger_status(ledger, bodies, cav):
    """{refdes: (state, detail)} for every ledger entry -- 'live' if it excuses a body that
    really does escape `cav`, otherwise why it is dead. `bodies` is {refdes: outline} for
    the bodies the escape test is actually applied to (the height-less ones are skipped
    before it, so an entry for one of those excuses nothing either)."""
    out = {}
    for ref in sorted(ledger):
        if ref not in bodies:
            out[ref] = ("dead", "names no body this gate tests -- the part is not on the "
                                "board's B side, or has no height and is skipped")
        elif cav.buffer(EPS).contains(bodies[ref]):
            x0, y0, x1, y1 = bodies[ref].bounds
            cx0, cy0, cx1, cy1 = cav.bounds
            out[ref] = ("dead", f"sits {min(x0 - cx0, cx1 - x1, y0 - cy0, cy1 - y1):.3f} mm "
                                f"INSIDE the cavity rectangle -- it escapes nothing")
        else:
            out[ref] = ("live", f"{bodies[ref].difference(cav.buffer(EPS)).area:.4f} mm2 of "
                                f"body outside the rectangle")
    return out


def check_ledger():
    """Audit EDGE_LEDGER against the board, once (the outlines do not depend on the variant).
    Returns 1 if any entry is dead, or if the audit fails its own self-test."""
    from shapely.geometry import box
    import board_parts
    import fit_rules
    from part_heights import part_height

    # the audit, audited: three synthetic entries whose answers do not depend on the board
    # -- one that escapes, one well inside, one that names nothing. If ledger_status() stops
    # telling them apart, a clean ledger below means nothing, so say that instead.
    cav0 = box(0.0, 0.0, 10.0, 10.0)
    want = {"OUT": "live", "IN": "dead", "GONE": "dead"}
    got = ledger_status(dict.fromkeys(want, "self-test"),
                        {"OUT": box(9.5, 4.0, 10.5, 5.0), "IN": box(4.0, 4.0, 5.0, 5.0)}, cav0)
    if {k: v[0] for k, v in got.items()} != want or "INSIDE" not in got["IN"][1] \
            or "names no body" not in got["GONE"][1]:
        print(f"  FAIL: SELF-TEST -- ledger_status() no longer tells a live entry from a dead "
              f"one ({got}); the edge-ledger audit is unproven")
        return 1

    bodies = {}
    for ref, poly, h, _source in board_parts.parts("B"):
        if h is None:
            try:
                h = part_height(ref)
            except Exception:
                h = None
        if h is not None:
            bodies[ref] = poly
    rc = 0
    status = ledger_status(EDGE_LEDGER, bodies, fit_rules.cavity_rect())
    for ref, (state, detail) in status.items():
        if state != "live":
            rc = 1
            print(f"  FAIL: EDGE_LEDGER entry {ref} is DEAD: it {detail}. Remove it in this "
                  f"commit (it was: {EDGE_LEDGER[ref]})")
    live = [r for r, (st, _d) in status.items() if st == "live"]
    print(f"edge ledger: {len(EDGE_LEDGER)} entr{'y' if len(EDGE_LEDGER) == 1 else 'ies'}"
          + (f", {len(live)} live ({', '.join(live)})" if EDGE_LEDGER else
             " -- no body is excused, so every escape from the cavity rectangle fails")
          + "; self-test: live / inside / missing told apart")
    return rc


def main():
    sys.path.insert(0, str(ROOT / "enclosure"))
    import fit_rules
    rc = check_ledger()
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
    # The board->mesh transform is DEFINITIONAL, not derived, and it has ONE home:
    # fit_rules.file_xy() (THE FILE FRAME there). It used to be inferred from bbox centres,
    # which is correct only while the brace happens to span the full cavity envelope -- the
    # lite brace does not (its main piece stops at board y 58.4), and the inferred offset
    # would have ray-cast every pocket half a card away from its part. Then it was typed
    # here as "board - (W/2, H/2)", the frame the brace is MODELLED in, which is left-handed:
    # the file was the mirror image of the part and this gate, reading it the same way,
    # agreed with it. The file is right-handed since 2026-11-13 (y runs UP in it), and the
    # mapping is read rather than restated so a writer and this reader cannot drift apart.
    # What pins the mapping itself to the real hand is scripts/handedness_drc.py.
    fx0, fy0 = fit_rules.file_xy(cx0, cy1)        # the cavity rect's corners, in the file frame
    fx1, fy1 = fit_rules.file_xy(cx1, cy0)
    if not (mx0 >= fx0 - 0.5 and mx1 <= fx1 + 0.5 and my0 >= fy0 - 0.5 and my1 <= fy1 + 0.5):
        print(f"  FAIL: brace mesh bbox falls outside the cavity under the definitional "
              f"file frame -- generator frame broke")
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

    # EDGE_LEDGER (module level, audited once in check_ledger) names the bodies allowed past
    # the bare cavity rectangle. Anything else that escapes fails here.
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
            fails.append(f"{ref}: body polygon escapes the cavity rect and is not in "
                         f"EDGE_LEDGER")
        x0, y0, x1, y1 = poly.bounds
        pts = [(x, y) for x in np.arange(x0, x1 + SAMPLE_MM / 2, SAMPLE_MM)
               for y in np.arange(y0, y1 + SAMPLE_MM / 2, SAMPLE_MM)
               if poly.buffer(EPS).contains(Point(x, y))]
        if not pts:
            pts = [(poly.centroid.x, poly.centroid.y)]
        origins = np.array([[*fit_rules.file_xy(x, y), cavity_h + 5.0] for x, y in pts])
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
