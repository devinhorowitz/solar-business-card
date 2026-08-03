#!/usr/bin/env python3
"""assembly_drc.py -- the ASSEMBLED-STACK gate (tier 4 of the solid gates).

Every existing gate checks one relationship:

  check [7]              a part's declared height vs that part's own 3D model
  check [8]              XY: brace bays, shell lip and the 8 bosses vs B-side bodies
  interference_drc.py    Z: the emitted BRACE mesh vs every B-side body
  check_mesh.py          each solid on its own -- validity, volume, bbox

Each is real, and together they still never answer the question a person asks when
they pick the thing up: DOES IT GO TOGETHER. The strongest of them,
interference_drc.py, covers exactly one interface pair (brace <-> B-side parts).
Three subsystems were in no fit gate at all:

  * THE FERRITE. FER1 appeared only in the buy list, the coil's electrical model and
    a comment. Nothing checked that the pocket the brace is supposed to carry exists
    in the EMITTED mesh, that its depth matches the sheet, or that the deliberate
    0.05 mm proud is inside the budget -- and that sheet sits directly in the clamp
    path between brace and board.
  * THE SCREWS. BOSS_R appeared once, as an XY radius for boss-vs-part fouling.
    Nothing checked that there is boss material to thread into, that SCREW_LEN
    reaches it, or that the screw does not run out the back of the shell.
  * THE Z BUDGET AS A SUM. floor + cavity + board was asserted layer against
    neighbouring layer, never closed against the shell that has to contain it.

WHAT THIS MEASURES

Backward from the ARTIFACTS, in the style interference_drc.py established -- the
committed STLs and the committed board, not the constants that were meant to
produce them. A gate fed by the same numbers as the generator can only prove the
module agrees with itself; check [8]'s own docstring records that failure mode.

  shell   enclosure/...-backshell-...-Ti-max.stl   ray-cast
  brace   enclosure/brace/...-diffuser-brace.stl   ray-cast
  ferrite fit_rules.FER / FER_T / FER_POCKET_DEPTH vs the brace pocket AS EMITTED
  board   fit_rules datums + board_parts (the committed .kicad_pcb)
  screws  fit_rules.MOUNTS / BOSS_R / PILOT_R vs shell material under each mount

WHAT THIS DOES NOT COVER, said plainly so it is not mistaken for total:
  * B-side part bodies vs the brace -- that is interference_drc.py, deliberately
    not duplicated here.
  * Nothing about the resin's print tolerance beyond the RSS stack fit_rules.AIR
    already carries.
"""
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "enclosure"))

SHELL_STL = ROOT / "enclosure" / "solar-glow-drh-v3_0-backshell-0p6b-brace-Ti-max.stl"
BRACE_STL = ROOT / "enclosure" / "brace" / "solar-glow-drh-diffuser-brace.stl"

FLOOR = 1.00          # cavity floor plane; the brace's own z=0 rests on it
TOL = 0.02            # mesh/quantisation tolerance for an equality assertion

# How much proud ferrite the clamp may take up. FER_T is deliberately thicker than its
# pocket -- 0.38 in 0.33 -- because the PSA and PET give a little when the board lands.
# That is a real allowance and a small one: past it the board no longer seats on the
# cavity walls, and tightening the screws bows the PCB over the coil rather than
# clamping the sheet. 2x the ledgered 0.05, so a re-spec has room before it trips.
FER_CRUSH = 0.10

_ERRORS, _WARNS, _NOTES = [], [], []


def err(m):
    _ERRORS.append(m); print(f"  ERROR   {m}")


def warn(m):
    _WARNS.append(m); print(f"  warn    {m}")


def ok(m):
    print(f"  ok      {m}")


def note(m):
    _NOTES.append(m); print(f"  note    {m}")


def top_at(mesh, bx, by, W, H, zhi=60.0):
    """Material top under a downward ray at BOARD coords (bx, by), or None.

    The STLs are centred on the origin (the generators emit wx = bx - W/2), so board
    coords are shifted here rather than in every caller.
    """
    o = np.array([[bx - W / 2.0, by - H / 2.0, zhi]])
    d = np.array([[0.0, 0.0, -1.0]])
    loc, _, _ = mesh.ray.intersects_location(o, d)
    return float(loc[:, 2].max()) if len(loc) else None


def ring_tops(mesh, cx, cy, r, W, H, n=16):
    """Tops sampled on a circle -- for a boss, whose CENTRE is a through bore."""
    out = []
    for i in range(n):
        a = 2.0 * np.pi * i / n
        t = top_at(mesh, cx + r * np.cos(a), cy + r * np.sin(a), W, H)
        if t is not None:
            out.append(t)
    return out


def main():
    try:
        import trimesh
        import fit_rules as fr
        import board_parts as bp
    except Exception as e:                                        # noqa: BLE001
        print(f"assembly_drc: cannot import ({type(e).__name__}: {e})")
        return 1

    W, H = fr.W, fr.H
    for p in (SHELL_STL, BRACE_STL):
        if not p.exists():
            print(f"assembly_drc: missing {p.relative_to(ROOT)} -- CI emits it on PCB/** changes")
            return 1
    shell = trimesh.load(SHELL_STL)
    brace = trimesh.load(BRACE_STL)

    print("assembly_drc -- the assembled stack, measured from the emitted artifacts\n")

    # ---- 1. the Z budget closes against the shell that has to contain it -------------
    print("[A] Z budget")
    want_rim = FLOOR + fr.CAVITY + fr.BOARD_TH
    rim = float(shell.bounds[1][2])
    if abs(rim - want_rim) <= TOL:
        ok(f"shell rim {rim:.3f} == floor {FLOOR} + cavity {fr.CAVITY} + board {fr.BOARD_TH} "
           f"= {want_rim:.3f} -- the card's front face finishes flush with the rim")
    else:
        err(f"shell rim is {rim:.3f} but the stack needs {want_rim:.3f} "
            f"(floor {FLOOR} + cavity {fr.CAVITY} + board {fr.BOARD_TH}) -- "
            f"{'the card stands proud' if rim < want_rim else 'the rim overhangs the card'} "
            f"by {abs(rim - want_rim):.3f}")

    floor_z = top_at(shell, W / 2.0, H / 2.0, W, H)
    if floor_z is None:
        err("no shell material under the cavity centre -- cannot locate the floor plane")
    elif abs(floor_z - FLOOR) <= TOL:
        ok(f"cavity floor measures {floor_z:.3f}, the {FLOOR} the brace is built to rest on")
    else:
        err(f"cavity floor measures {floor_z:.3f}, not {FLOOR} -- every Z below is off by "
            f"{floor_z - FLOOR:+.3f}")

    # ---- 2. the brace fills the cavity it was cut for --------------------------------
    print("[B] brace vs cavity")
    bz0, bz1 = float(brace.bounds[0][2]), float(brace.bounds[1][2])
    if abs(bz0) <= TOL and abs(bz1 - fr.GAP) <= TOL:
        ok(f"brace spans z {bz0:.3f}..{bz1:.3f} = GAP {fr.GAP} -- seats on the floor, "
           f"tops out at the board's underside")
    else:
        err(f"brace spans z {bz0:.3f}..{bz1:.3f}, not 0..{fr.GAP} -- it does not fill the cavity")

    cav = fr.cavity_rect()
    cx0, cy0, cx1, cy1 = cav.bounds
    bb = brace.bounds
    bx0, by0 = bb[0][0] + W / 2.0, bb[0][1] + H / 2.0
    bx1, by1 = bb[1][0] + W / 2.0, bb[1][1] + H / 2.0
    if bx0 >= cx0 - TOL and by0 >= cy0 - TOL and bx1 <= cx1 + TOL and by1 <= cy1 + TOL:
        ok(f"brace footprint [{bx0:.2f},{by0:.2f}]..[{bx1:.2f},{by1:.2f}] sits inside the "
           f"cavity [{cx0:.2f},{cy0:.2f}]..[{cx1:.2f},{cy1:.2f}]")
    else:
        err(f"brace footprint [{bx0:.2f},{by0:.2f}]..[{bx1:.2f},{by1:.2f}] escapes the cavity "
            f"[{cx0:.2f},{cy0:.2f}]..[{cx1:.2f},{cy1:.2f}] -- it will not drop in")

    # ---- 3. the ferrite: the pocket, the sheet, and the clamp ------------------------
    print("[C] ferrite (FER1) in its pocket")
    fx0, fy0, fx1, fy1 = fr.FER
    probes = [("centre", (fx0 + fx1) / 2, (fy0 + fy1) / 2),
              ("west", fx0 + 0.6, (fy0 + fy1) / 2),
              ("east", fx1 - 0.6, (fy0 + fy1) / 2),
              ("south", (fx0 + fx1) / 2, fy0 + 0.6),
              ("north", (fx0 + fx1) / 2, fy1 - 0.6)]
    tops, missing = {}, []
    for lbl, px, py in probes:
        t = top_at(brace, px, py, W, H)
        tops[lbl] = t
        if t is None:
            missing.append(lbl)
    if missing:
        err(f"no brace material under the ferrite extent at {missing} -- the sheet has "
            f"nothing to seat against there")
    else:
        want_top = fr.GAP - fr.FER_POCKET_DEPTH
        worst = max(abs(t - want_top) for t in tops.values())
        if worst <= TOL:
            ok(f"pocket floor {want_top:.3f} across the whole {fx1-fx0:.0f}x{fy1-fy0:.0f} mm "
               f"extent (measured {min(tops.values()):.3f}..{max(tops.values()):.3f}) "
               f"= GAP {fr.GAP} - {fr.FER_POCKET_DEPTH} deep")
        else:
            err(f"the ferrite pocket is not {fr.FER_POCKET_DEPTH} deep everywhere: tops "
                f"{ {k: round(v,3) for k,v in tops.items()} }, wanted {want_top:.3f}. "
                f"A sheet PSA'd onto an uneven floor will not lie flat under the coil")

        # the sheet is thicker than its pocket ON PURPOSE -- it seats flush when clamped
        proud = fr.FER_T - fr.FER_POCKET_DEPTH
        seated = want_top + fr.FER_T
        if proud < -TOL:
            err(f"pocket {fr.FER_POCKET_DEPTH} is DEEPER than the {fr.FER_T} sheet -- the "
                f"ferrite would sit {-proud:.3f} below the brace face and never touch the board")
        elif seated <= fr.GAP + TOL:
            ok(f"sheet {fr.FER_T} lies flush or below the brace face")
        elif proud <= FER_CRUSH + TOL:
            ok(f"sheet {fr.FER_T} stands {proud:.3f} proud of the brace face "
               f"(top {seated:.3f} vs GAP {fr.GAP}) -- inside the {FER_CRUSH} the PSA/PET "
               f"gives up when the board clamps it")
        else:
            err(f"sheet {fr.FER_T} stands {proud:.3f} proud of a {fr.FER_POCKET_DEPTH} pocket, "
                f"past the {FER_CRUSH} crush allowance: the board cannot seat on the cavity "
                f"walls, so tightening the screws bows the PCB over the coil instead of "
                f"clamping the sheet. Deepen the pocket or thin the stack")

    # ---- 4. the screws have something to bite, and stop before the back --------------
    print("[D] screws")
    probe_r = (fr.PILOT_R + fr.BOSS_R) / 2.0     # between the bore and the boss OD
    back = float(shell.bounds[0][2])
    for mx, my in fr.MOUNTS:
        ts = ring_tops(shell, mx, my, probe_r, W, H)
        if not ts:
            err(f"mount ({mx},{my}): no shell material in the boss annulus at r={probe_r:.2f} "
                f"-- nothing for an M2 to thread into")
            continue
        boss_top = max(ts)
        # A BOSS MUST REACH THE BOARD. This is the assertion that separates a boss from
        # the cavity floor, and it is the one that matters: the PCB is clamped between the
        # screw head and the boss top, so a boss that stops short leaves the board spanning
        # air and the screw BENDS it instead of holding it. Measured, every real boss tops
        # out at FLOOR + CAVITY exactly -- flush with the board's underside. A first cut of
        # this check only compared thread engagement, and happily passed a mount relocated
        # into open cavity, where the "boss" it found was the floor 1.8 mm below.
        want_boss = FLOOR + fr.CAVITY
        if boss_top < want_boss - TOL:
            err(f"mount ({mx},{my}): material under the mount tops out at {boss_top:.3f}, "
                f"not the {want_boss:.3f} that meets the board"
                + (" -- that is the cavity floor, there is no boss here"
                   if abs(boss_top - FLOOR) <= TOL else
                   f" -- the board spans {want_boss - boss_top:.3f} of air over it"))
            continue
        # the screw enters at the board's front face and drives down
        entry = FLOOR + fr.CAVITY + fr.BOARD_TH
        engage = boss_top - (entry - 3.0)        # SCREW_LEN 3.0, matching the render
        if engage <= 0:
            err(f"mount ({mx},{my}): a 3.0 mm screw entering at {entry:.2f} never reaches the "
                f"boss top {boss_top:.2f} -- it clamps nothing")
        elif engage < 1.0:
            warn(f"mount ({mx},{my}): only {engage:.2f} mm of thread engagement into the boss "
                 f"(top {boss_top:.2f}); M2 wants ~1.5x diameter for full strength")
        if (entry - 3.0) < back - TOL:
            err(f"mount ({mx},{my}): the screw tip reaches {entry-3.0:.2f}, past the shell's "
                f"back face {back:.2f} -- it would stand proud of the medallion")
    if not _ERRORS:
        ok(f"all {len(fr.MOUNTS)} mounts: boss material present, 3.0 mm screw lands inside "
           f"the shell (back face {back:.3f})")

    # ---- 5. the front side: nothing of the shell may stand over it -------------------
    # THE CELLS ARE THE WHOLE POINT. This card harvests indoor light through two cells
    # that between them cover most of the show face, so titanium standing over any part
    # of one is not a fit problem, it is lost harvest -- and it would be invisible in
    # every gate here, all of which look at the B side.
    #
    # The assertion is the artifact's, not the intent's: ray-cast the SHELL over each
    # front body and require that it finds nothing at or above the board's front face.
    # That is the plane the rim is built to finish flush with ([A] proves it does), so
    # any material there is the rim or the lip reaching over the board instead of
    # stopping at its edge. It generalises past the cells for free -- TC1's pad field
    # gets the same guarantee, and so does anything placed on the front later.
    print("[E] front side clear of the shell")
    board_front = FLOOR + fr.CAVITY + fr.BOARD_TH
    fronts = [(r, p) for r, p, _h, _s in bp.parts("F") if r and not r.startswith("?")]
    if not fronts:
        err("no front-side bodies found -- board_parts returned nothing to check")
    for ref, poly in fronts:
        x0, y0, x1, y1 = poly.bounds
        nx = max(3, min(9, int((x1 - x0) / 5) + 3))
        ny = max(3, min(15, int((y1 - y0) / 5) + 3))
        shaded = []
        for fx in np.linspace(x0 + 0.2, x1 - 0.2, nx):
            for fy in np.linspace(y0 + 0.2, y1 - 0.2, ny):
                t = top_at(shell, fx, fy, W, H)
                if t is not None and t > board_front - TOL:
                    shaded.append((round(float(fx), 1), round(float(fy), 1), round(t, 3)))
        if shaded:
            frac = 100.0 * len(shaded) / (nx * ny)
            what = ("that is harvest area lost to titanium"
                    if ref.startswith("PV") else "the shell fouls it")
            err(f"{ref}: shell material stands at/above the board's front face "
                f"{board_front:.3f} over {frac:.0f}% of its footprint "
                f"(e.g. {shaded[:3]}) -- {what}")
        else:
            ok(f"{ref}: clear -- no shell material at or above {board_front:.3f} anywhere "
               f"over its {x1-x0:.1f} x {y1-y0:.1f} mm footprint")

    print()
    print(f"== {len(_ERRORS)} error(s), {len(_WARNS)} warning(s) ==")
    return 1 if _ERRORS else 0


if __name__ == "__main__":
    sys.exit(main())
