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
    Nothing checked that there is boss material to thread into, that the screw
    length reaches it, or that the screw does not run out the back of the shell.
  * THE Z BUDGET AS A SUM. floor + cavity + board was asserted layer against
    neighbouring layer, never closed against the shell that has to contain it.

WHAT THIS MEASURES

Backward from the ARTIFACTS, in the style interference_drc.py established -- the
committed STLs and the committed board, not the constants that were meant to
produce them. A gate fed by the same numbers as the generator can only prove the
module agrees with itself; check [8]'s own docstring records that failure mode.

Since 2026-08-07 the gate loops every variant in fit_rules.VARIANTS (max / lite /
air), the interference_drc.py pattern: per-variant values come EXPLICITLY from the
table, never from mutated module state, and each variant is measured against ITS
OWN emitted shell (and brace, where one exists):

  shell   enclosure/<shell_name>.stl                ray-cast
  brace   enclosure/brace/<brace_name>.stl or None  ray-cast
  ferrite fit_rules.FER / FER_T / FER_POCKET_DEPTH vs the brace pocket AS EMITTED
  board   fit_rules datums + board_parts (the committed .kicad_pcb)
  screws  fit_rules.MOUNTS / BOSS_R / PILOT_R vs shell material under each mount,
          with the variant's own screw_len from the table

Variant policy, stated rather than implied:
  * max / lite -- every check, parameterized (floor, cavity, screw_len, stack).
  * air -- open_back, no brace: the cavity-floor probe and every brace/ferrite
    check are SKIPPED with a printed reason (open frame -- no floor/brace by
    design). In their place: an upward ray at the cavity centre must hit NOTHING
    (the back really is open), the bosses must span the FULL frame depth (back
    face to board underside -- there is no floor for a stub boss to hide on),
    and the M2x1.6 tip must never pass the resting plane z=0 (ERROR, not warn:
    a proud tip means the frame rocks on the screw, not the table).

WHAT THIS DOES NOT COVER, said plainly so it is not mistaken for total:
  * B-side part bodies vs the brace -- that is interference_drc.py, deliberately
    not duplicated here.
  * Nothing about the resin's print tolerance beyond the RSS stack fit_rules.AIR
    already carries.
"""
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "enclosure"))

TOL = 0.02            # mesh/quantisation tolerance for an equality assertion

# How much proud ferrite the clamp may take up. FER_T is deliberately thicker than its
# pocket -- 0.38 in 0.33 -- because the PSA and PET give a little when the board lands.
# That is a real allowance and a small one: past it the board no longer seats on the
# cavity walls, and tightening the screws bows the PCB over the coil rather than
# clamping the sheet. 2x the ledgered 0.05, so a re-spec has room before it trips.
FER_CRUSH = 0.10

_ERRORS, _WARNS, _NOTES = [], [], []


def _reset():
    """Per-variant accumulator reset -- one variant's errors must not bleed into
    another's verdict."""
    del _ERRORS[:], _WARNS[:], _NOTES[:]


def err(m):
    _ERRORS.append(m); print(f"  ERROR   {m}")


def warn(m):
    _WARNS.append(m); print(f"  warn    {m}")


def ok(m):
    print(f"  ok      {m}")


def note(m):
    _NOTES.append(m); print(f"  note    {m}")


def z_hits(mesh, bx, by, W, H, zhi=60.0):
    """All z crossings under a downward ray at BOARD coords (bx, by), or None.

    The STLs are centred on the origin (the generators emit wx = bx - W/2), so board
    coords are shifted here rather than in every caller.
    """
    o = np.array([[bx - W / 2.0, by - H / 2.0, zhi]])
    d = np.array([[0.0, 0.0, -1.0]])
    loc, _, _ = mesh.ray.intersects_location(o, d)
    return loc[:, 2] if len(loc) else None


def top_at(mesh, bx, by, W, H, zhi=60.0):
    """Material top under a downward ray at BOARD coords (bx, by), or None."""
    z = z_hits(mesh, bx, by, W, H, zhi)
    return float(z.max()) if z is not None else None


def up_hits(mesh, bx, by, W, H, zlo=-5.0):
    """z crossings of an UPWARD ray from below at BOARD coords -- the openness probe."""
    o = np.array([[bx - W / 2.0, by - H / 2.0, zlo]])
    d = np.array([[0.0, 0.0, 1.0]])
    loc, _, _ = mesh.ray.intersects_location(o, d)
    return loc[:, 2] if len(loc) else None


def ring_spans(mesh, cx, cy, r, W, H, n=16):
    """(bottom, top) spans sampled on a circle -- for a boss, whose CENTRE is a
    through bore."""
    out = []
    for i in range(n):
        a = 2.0 * np.pi * i / n
        z = z_hits(mesh, cx + r * np.cos(a), cy + r * np.sin(a), W, H)
        if z is not None:
            out.append((float(z.min()), float(z.max())))
    return out


def check_variant(vname, v, fr, bp, trimesh):
    """Run every applicable check for one VARIANTS row. Values come EXPLICITLY from
    the table; nothing here reads a module-level geometry constant that could have
    been mutated. Returns (n_errors, n_warns)."""
    _reset()
    W, H = fr.W, fr.H
    floor = v["floor"]          # cavity floor plane; a brace's own z=0 rests on it
    cavity = v["cavity"]
    screw_len = v["screw_len"]
    open_back = v["open_back"]

    shell_stl = ROOT / "enclosure" / (v["shell_name"] + ".stl")
    brace_stl = (ROOT / "enclosure" / "brace" / (v["brace_name"] + ".stl")
                 if v["brace_name"] else None)
    for p in filter(None, (shell_stl, brace_stl)):
        if not p.exists():
            err(f"missing {p.relative_to(ROOT)} -- CI emits it on PCB/** changes")
            return len(_ERRORS), len(_WARNS)
    shell = trimesh.load(shell_stl)
    brace = trimesh.load(brace_stl) if brace_stl else None

    # ---- 1. the Z budget closes against the shell that has to contain it -------------
    print("[A] Z budget")
    want_rim = floor + cavity + fr.BOARD_TH      # = v["stack"]
    rim = float(shell.bounds[1][2])
    if abs(rim - want_rim) <= TOL:
        ok(f"shell rim {rim:.3f} == floor {floor} + cavity {cavity} + board {fr.BOARD_TH} "
           f"= {want_rim:.3f} -- the card's front face finishes flush with the rim")
    else:
        err(f"shell rim is {rim:.3f} but the stack needs {want_rim:.3f} "
            f"(floor {floor} + cavity {cavity} + board {fr.BOARD_TH}) -- "
            f"{'the card stands proud' if rim < want_rim else 'the rim overhangs the card'} "
            f"by {abs(rim - want_rim):.3f}")

    if open_back:
        note("open frame -- no floor/brace by design: skipping the cavity-floor probe")
        z = up_hits(shell, W / 2.0, H / 2.0, W, H)
        if z is not None:
            err(f"open frame: an upward ray at the cavity centre hits frame material at "
                f"z={float(z.min()):.3f} -- the back is not open")
        else:
            ok("open frame: an upward ray at the cavity centre hits nothing -- "
               "the back really is open")
    else:
        floor_z = top_at(shell, W / 2.0, H / 2.0, W, H)
        if floor_z is None:
            err("no shell material under the cavity centre -- cannot locate the floor plane")
        elif abs(floor_z - floor) <= TOL:
            ok(f"cavity floor measures {floor_z:.3f}, the {floor} the brace is built to rest on")
        else:
            err(f"cavity floor measures {floor_z:.3f}, not {floor} -- every Z below is off by "
                f"{floor_z - floor:+.3f}")

    # ---- 2. the brace fills the cavity it was cut for --------------------------------
    print("[B] brace vs cavity")
    if brace is None:
        note("open frame -- no floor/brace by design: skipping brace-vs-cavity")
    else:
        bz0, bz1 = float(brace.bounds[0][2]), float(brace.bounds[1][2])
        if abs(bz0) <= TOL and abs(bz1 - cavity) <= TOL:
            ok(f"brace spans z {bz0:.3f}..{bz1:.3f} = cavity {cavity} -- seats on the floor, "
               f"tops out at the board's underside")
        else:
            err(f"brace spans z {bz0:.3f}..{bz1:.3f}, not 0..{cavity} -- it does not fill "
                f"the cavity")

        cav = fr.cavity_rect()
        cx0, cy0, cx1, cy1 = cav.bounds
        bb = brace.bounds
        bx0, by0 = bb[0][0] + W / 2.0, bb[0][1] + H / 2.0
        bx1, by1 = bb[1][0] + W / 2.0, bb[1][1] + H / 2.0
        if bx0 >= cx0 - TOL and by0 >= cy0 - TOL and bx1 <= cx1 + TOL and by1 <= cy1 + TOL:
            ok(f"brace footprint [{bx0:.2f},{by0:.2f}]..[{bx1:.2f},{by1:.2f}] sits inside the "
               f"cavity [{cx0:.2f},{cy0:.2f}]..[{cx1:.2f},{cy1:.2f}]")
        else:
            err(f"brace footprint [{bx0:.2f},{by0:.2f}]..[{bx1:.2f},{by1:.2f}] escapes the "
                f"cavity [{cx0:.2f},{cy0:.2f}]..[{cx1:.2f},{cy1:.2f}] -- it will not drop in")

    # ---- 3. the ferrite: the pocket, the sheet, and the clamp ------------------------
    print("[C] ferrite (FER1) in its pocket")
    if brace is None:
        note("open frame -- no floor/brace by design: skipping the ferrite pocket/crush "
             "checks (no brace, no pocket)")
    else:
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
            want_top = cavity - fr.FER_POCKET_DEPTH
            worst = max(abs(t - want_top) for t in tops.values())
            if worst <= TOL:
                ok(f"pocket floor {want_top:.3f} across the whole {fx1-fx0:.0f}x{fy1-fy0:.0f} mm "
                   f"extent (measured {min(tops.values()):.3f}..{max(tops.values()):.3f}) "
                   f"= cavity {cavity} - {fr.FER_POCKET_DEPTH} deep")
            else:
                err(f"the ferrite pocket is not {fr.FER_POCKET_DEPTH} deep everywhere: tops "
                    f"{ {k: round(v,3) for k,v in tops.items()} }, wanted {want_top:.3f}. "
                    f"A sheet PSA'd onto an uneven floor will not lie flat under the coil")

            # the sheet is thicker than its pocket ON PURPOSE -- it seats flush when clamped
            proud = fr.FER_T - fr.FER_POCKET_DEPTH
            seated = want_top + fr.FER_T
            if proud < -TOL:
                err(f"pocket {fr.FER_POCKET_DEPTH} is DEEPER than the {fr.FER_T} sheet -- the "
                    f"ferrite would sit {-proud:.3f} below the brace face and never touch "
                    f"the board")
            elif seated <= cavity + TOL:
                ok(f"sheet {fr.FER_T} lies flush or below the brace face")
            elif proud <= FER_CRUSH + TOL:
                ok(f"sheet {fr.FER_T} stands {proud:.3f} proud of the brace face "
                   f"(top {seated:.3f} vs cavity {cavity}) -- inside the {FER_CRUSH} the "
                   f"PSA/PET gives up when the board clamps it")
            else:
                err(f"sheet {fr.FER_T} stands {proud:.3f} proud of a {fr.FER_POCKET_DEPTH} "
                    f"pocket, past the {FER_CRUSH} crush allowance: the board cannot seat on "
                    f"the cavity walls, so tightening the screws bows the PCB over the coil "
                    f"instead of clamping the sheet. Deepen the pocket or thin the stack")

    # ---- 4. the screws have something to bite, and stop before the back --------------
    print("[D] screws")
    pre_screw_errs = len(_ERRORS)
    probe_r = (fr.PILOT_R + fr.BOSS_R) / 2.0     # between the bore and the boss OD
    back = float(shell.bounds[0][2])
    for mx, my in fr.MOUNTS:
        spans = ring_spans(shell, mx, my, probe_r, W, H)
        if not spans:
            err(f"mount ({mx},{my}): no shell material in the boss annulus at r={probe_r:.2f} "
                f"-- nothing for an M2 to thread into")
            continue
        boss_top = max(t for _b, t in spans)
        # A BOSS MUST REACH THE BOARD. This is the assertion that separates a boss from
        # the cavity floor, and it is the one that matters: the PCB is clamped between the
        # screw head and the boss top, so a boss that stops short leaves the board spanning
        # air and the screw BENDS it instead of holding it. Measured, every real boss tops
        # out at floor + cavity exactly -- flush with the board's underside. A first cut of
        # this check only compared thread engagement, and happily passed a mount relocated
        # into open cavity, where the "boss" it found was the floor 1.8 mm below.
        want_boss = floor + cavity
        if boss_top < want_boss - TOL:
            err(f"mount ({mx},{my}): material under the mount tops out at {boss_top:.3f}, "
                f"not the {want_boss:.3f} that meets the board"
                + (" -- that is the cavity floor, there is no boss here"
                   if not open_back and abs(boss_top - floor) <= TOL else
                   f" -- the board spans {want_boss - boss_top:.3f} of air over it"))
            continue
        if open_back:
            # No floor to stand on: the boss IS the frame here, and must span its full
            # depth -- back face to board underside -- or the screw threads into a stub
            # hanging in open air.
            boss_bot = min(b for b, _t in spans)
            if abs(boss_bot - back) > TOL:
                err(f"mount ({mx},{my}): boss spans z {boss_bot:.3f}..{boss_top:.3f}, not "
                    f"the full frame depth from the back face {back:.3f} -- a stub boss "
                    f"on an open frame")
        # the screw enters at the board's front face and drives down
        entry = floor + cavity + fr.BOARD_TH
        tip = entry - screw_len
        engage = boss_top - tip
        if engage <= 0:
            err(f"mount ({mx},{my}): a {screw_len} mm screw entering at {entry:.2f} never "
                f"reaches the boss top {boss_top:.2f} -- it clamps nothing")
        elif engage + 1e-6 < 1.0:
            warn(f"mount ({mx},{my}): only {engage:.2f} mm of thread engagement into the boss "
                 f"(top {boss_top:.2f}); M2 wants ~1.5x diameter for full strength")
        if open_back:
            # The frame rests back-face-down on the table (z=0 IS the resting plane);
            # a tip past it means the card rocks on a screw point. ERROR, not warn.
            if tip < -1e-6:
                err(f"mount ({mx},{my}): the {screw_len} mm screw tip reaches {tip:.2f}, "
                    f"below the resting plane z=0 -- the frame rocks on the screw, not "
                    f"the table")
        elif tip < back - TOL:
            err(f"mount ({mx},{my}): the screw tip reaches {tip:.2f}, past the shell's "
                f"back face {back:.2f} -- it would stand proud of the medallion")
    if len(_ERRORS) == pre_screw_errs:
        extra = (", tip stays >= 0 above the resting plane" if open_back
                 else f" (back face {back:.3f})")
        ok(f"all {len(fr.MOUNTS)} mounts: boss material present, {screw_len} mm screw lands "
           f"inside the shell{extra}")

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
    board_front = floor + cavity + fr.BOARD_TH
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

    return len(_ERRORS), len(_WARNS)


def main():
    try:
        import trimesh
        import fit_rules as fr
        import board_parts as bp
    except Exception as e:                                        # noqa: BLE001
        print(f"assembly_drc: cannot import ({type(e).__name__}: {e})")
        return 1

    print("assembly_drc -- the assembled stack, measured from the emitted artifacts")

    results = []
    for vname, v in fr.VARIANTS.items():
        brace_lbl = f"{v['brace_name']}.stl" if v["brace_name"] else "none (open frame)"
        print(f"\n== variant {vname}: shell {v['shell_name']}.stl, brace {brace_lbl}, "
              f"floor {v['floor']} + cavity {v['cavity']} + board {fr.BOARD_TH} -> "
              f"stack {v['stack']}, M2x{v['screw_len']} ==")
        ne, nw = check_variant(vname, v, fr, bp, trimesh)
        results.append((vname, ne, nw))

    print()
    for vname, ne, nw in results:
        print(f"== variant {vname}: {ne} error(s), {nw} warning(s) ==")
    return 1 if any(ne for _v, ne, _w in results) else 0


if __name__ == "__main__":
    sys.exit(main())
