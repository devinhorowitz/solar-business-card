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

  shell   enclosure/<shell_name>.stl                ray-cast, and SECTIONED in plan
  brace   enclosure/brace/<brace_name>.stl or None  ray-cast, and SECTIONED in plan
  ferrite fit_rules.FER / FER_T / FER_POCKET_DEPTH vs the brace pocket AS EMITTED
  board   fit_rules datums + board_parts (the committed .kicad_pcb)
  screws  fit_rules.MOUNTS / BOSS_R / PILOT_R vs shell material under each mount,
          with the variant's own screw_len from the table

THE PLAN-VIEW SECTIONS ([B] and [F], 2026-11-12) exist because of two failures that
passed every gate here, both found by an independent measurement of the committed STEPs:

  * all four supercaps sat INSIDE mount bosses, 0.17 to 0.375 mm deep. fit_rules had
    always described a boss as a disc scalloped clear of whatever fouls it, check [8]
    gated that polygon, and the shell CAD unioned a plain cylinder. The polygon was
    clear by construction; the titanium was never looked at.
  * both braces were 0.20 mm WIDER than the cavities they drop into, over 26 mm of the
    east wall. The brace was cut from the scalar rectangle fit_rules._CAV, the shell
    from cavity_void_poly(), and [B] below compared the brace's bounding box to that
    same rectangle -- so it agreed, every run.

Same shape both times, and the same shape as the MOUNTS incident: one generator used
the shared definition, the other did not, and the gate checked the shared definition.
A gate of that kind cannot be fixed by pointing it at a better definition. So these two
do not read one: they slice the emitted meshes at heights inside the cavity and compare
the metal that is actually there against the part outlines read from the board, and
against the brace that is actually there. Each carries a canary -- a synthetic part
planted in a boss, the brace pushed a millimetre into the wall -- that must go red on
every run, because a section taken in the wrong frame reads as a clean pass.

THE LIP CHECK ([G], 2026-11-12) is the same lesson applied before it could bite. The
shell drawing's lip note is no longer typed: it is written from fit_rules.lip_as_cut(),
which is a DESCRIPTION -- per-band widths, the stretches a relief removes, the part
behind each -- and a description computed in the module that cuts the part is exactly
the kind of thing this file exists to distrust. The first one written recited
fit_rules.lip_bands() and would have put a 0.70 mm ledge on the sheet under each
supercap, where every shell this repo has built has none: 74.6 mm of bare board edge.
So [G] sections the emitted shell and measures, every 0.1 mm along all four edges, how
far the metal stands in from the board edge, and holds lip_as_cut() to it. Its canary is
the same measurement against a description half a millimetre too wide.

THE AS-MILLED CHECK ([H], 2026-11-13) is [B] and [F] again with the finisher's radius
applied: each section's void is opened by fit_rules.TOOL_R -- the radius the sheet tells the
shop to finish the inside corners with -- before the brace, every B-side body and the four
supercaps at MAX MATERIAL (fit_rules.part_envelope) are held to it. It exists because the
STEP keeps those corners sharp and both earlier checks measured the STEP: the brace ran
0.225 mm into the east boss-to-wall fillets and a max-material SC2 / SC4 sat 0.113 / 0.130
inside the mid-span boss corners on every committed shell, all of it green.

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
  * HANDEDNESS, on its own. Until 2026-11-13 every solid was written in the frame it is
    modelled in -- board coordinates, X right, Y down, Z to the card's front, which is
    LEFT-handed -- and every reader in this repo, this one included, loaded them the same
    way, so a mirror-image part passed all of it. The files are right-handed now
    (fit_rules, THE FILE FRAME) and this gate reads them through fit_rules.file_xy() /
    board_geom(), the one statement of that mapping. That makes it a strong test that the
    shell and the brace agree with the BOARD under the mapping ([F] and [G] go red on a
    shell written in the other hand: its lip nick is 4 mm from where the board puts it) --
    and no test at all that the mapping is the right-handed one. A reader and a writer
    flipped together still agree. scripts/handedness_drc.py closes that: it places the
    emitted solids against KiCad's own STEP export of the board by a translation alone.
  * The part outlines are board_parts' reading of the .kicad_pcb. An error in THAT
    reader is shared with the generators and is invisible here too.
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

# ---- the plan-view sections ([B], [F]) --------------------------------------------------
# What the SECTION can resolve, not a design clearance: the shell is tessellated at 0.04 mm
# and a section inscribes every arc, so two outlines closer than this cannot be told from
# touching. Deliberately NOT fit_rules.BOSS_CLR / LIP_CLR -- a gate that asked the generator
# what the clearance should be is the gate this one replaces. The printed table is where the
# real numbers are read; this only refuses contact.
SECTION_FLOOR = 0.05
# ---- the lip check ([G]) -----------------------------------------------------------------
# A flat wall sections exactly (worst 0.002 mm, measured on five shells), so this is well
# inside the smallest step the description has to tell apart (2.32 from 2.25) and well
# outside the 0.005 the widths are rounded by.
LIP_TOL = 0.03
# How far either side of a described step the metal may be anywhere BETWEEN the two widths:
# the finisher's radius blends a band step and a relief leaves an arc, and neither is in the
# description. Measured on the committed shells the longest transition is 1.30 mm.
LIP_BLEND = 1.35
# Stations this close to a corner are inside the NEXT edge's lip (up to 2.5 wide, plus its
# blend): a probe there runs along metal, and "width" stops meaning anything.
LIP_CORNER = 3.6
LIP_STEP = 0.1
OVERLAP_EPS = 1e-3    # mm2 of plan overlap that counts as metal inside a body, not noise
SECTION_GRID = 1e-5   # mm: snap for stitching section segments into closed outlines
# Heights are fractions of the cavity plus an irrational-looking nudge, so no cut ever lands
# on a mesh vertex or a horizontal face (floor top, seat, chamfer edge) and degenerates.
_NUDGE = 0.0137

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


def _frame():
    """fit_rules -- for file_xy() / board_geom(), THE mapping between board coordinates and an
    emitted solid's (fit_rules, THE FILE FRAME). Imported lazily like every dependency here,
    so main() can report a missing one cleanly; never restated in this file."""
    import fit_rules
    return fit_rules


def z_hits(mesh, bx, by, zhi=60.0):
    """All z crossings under a downward ray at BOARD coords (bx, by), or None.

    Board coordinates are mapped into the solid's file frame here, by fit_rules.file_xy(),
    rather than in every caller.
    """
    o = np.array([[*_frame().file_xy(bx, by), zhi]])
    d = np.array([[0.0, 0.0, -1.0]])
    loc, _, _ = mesh.ray.intersects_location(o, d)
    return loc[:, 2] if len(loc) else None


def top_at(mesh, bx, by, zhi=60.0):
    """Material top under a downward ray at BOARD coords (bx, by), or None."""
    z = z_hits(mesh, bx, by, zhi)
    return float(z.max()) if z is not None else None


def up_hits(mesh, bx, by, zlo=-5.0):
    """z crossings of an UPWARD ray from below at BOARD coords -- the openness probe."""
    o = np.array([[*_frame().file_xy(bx, by), zlo]])
    d = np.array([[0.0, 0.0, 1.0]])
    loc, _, _ = mesh.ray.intersects_location(o, d)
    return loc[:, 2] if len(loc) else None


def ring_spans(mesh, cx, cy, r, n=16):
    """(bottom, top) spans sampled on a circle -- for a boss, whose CENTRE is a
    through bore."""
    out = []
    for i in range(n):
        a = 2.0 * np.pi * i / n
        z = z_hits(mesh, cx + r * np.cos(a), cy + r * np.sin(a))
        if z is not None:
            out.append((float(z.min()), float(z.max())))
    return out


def section_file(mesh, z, trimesh):
    """The material `mesh` has at height z, as shapely geometry in the solid's OWN (file)
    frame -- nothing is mapped. For scripts/handedness_drc.py, which has to place a solid
    against KiCad's export by a translation alone and so must not borrow this repo's idea
    of where the board is.

    mesh_plane() returns loose segments; they are stitched on a snap grid and polygonized,
    and each resulting face is kept only if the mesh actually contains a point inside it --
    asked of the mesh itself by ray parity, so nothing here guesses at ring nesting."""
    import shapely
    from shapely.geometry import Polygon
    from shapely.ops import polygonize, unary_union
    segs = trimesh.intersections.mesh_plane(mesh, [0.0, 0.0, 1.0], [0.0, 0.0, z])
    if len(segs) == 0:
        return Polygon()
    net = shapely.union_all(shapely.linestrings(segs[:, :, :2]), grid_size=SECTION_GRID)
    faces = [f for f in polygonize(net) if f.area > 1e-9]
    if not faces:
        return Polygon()
    probe = np.array([[*f.representative_point().coords[0], z] for f in faces])
    inside = mesh.contains(probe)
    return unary_union([f for f, k in zip(faces, inside) if k])


def section(mesh, z, trimesh):
    """The material `mesh` has at height z, as shapely geometry in BOARD coordinates:
    section_file(), carried from the solid's file frame to the board's by
    fit_rules.board_geom()."""
    return _frame().board_geom(section_file(mesh, z, trimesh))


def cavity_levels(floor, cavity):
    """[(label, z)] -- three cuts through the cavity: just under the seat (below the 0.10
    lip-break, and inside even a bare pad's 0.20 budget), the middle, just above the floor."""
    seat = floor + cavity
    return [("under the seat", seat - 0.12 - _NUDGE),
            ("mid-cavity", floor + cavity / 2.0 + _NUDGE),
            ("above the floor", floor + 0.08 + _NUDGE)]


def edge_reach(metal, edge, t, W, H, depth=6.0):
    """How far the shell's perimeter metal stands IN from the board edge at station t along
    `edge` ("W"/"E": t is board y; "S"/"N": t is board x), on one section. It is the inner
    end of the run of metal that contains the wall -- found half a millimetre OUTSIDE the
    board edge, where there is always wall -- so it is negative where that run stops short
    of the board edge, and None if there is no wall there at all (a section in the wrong
    frame)."""
    from shapely.geometry import LineString
    a, b = {"W": ((-0.5, t), (depth, t)), "E": ((W + 0.5, t), (W - depth, t)),
            "S": ((t, -0.5), (t, depth)), "N": ((t, H + 0.5), (t, H - depth))}[edge]
    hit = metal.intersection(LineString([a, b]))
    for seg in getattr(hit, "geoms", [hit]):
        if seg.geom_type != "LineString" or seg.is_empty:
            continue
        ins = [(c[0] if edge == "W" else W - c[0]) if edge in "WE" else
               (c[1] if edge == "S" else H - c[1]) for c in seg.coords]
        if min(ins) <= -0.5 + 1e-6:
            return max(ins)
    return None


def lip_disagreements(rows, edge, lip_cut, recess_cut, mounts, boss_r, W, H):
    """([(t, got, lo, hi)], n_stations, worst) -- where the sectioned shell does not have the
    lip `rows` describes along `edge`. `rows` is fit_rules.lip_as_cut()'s shape,
    [(lo, hi, width, names)], width 0.0 meaning no lip.

    A station passes if the metal's reach from the board edge lies between the narrowest and
    the widest row within LIP_BLEND of it -- so it must EQUAL the row's width wherever a row
    runs undisturbed, and only a blend or a relief arc is given room. "No lip" means no
    ledge inboard of the recess wall, which is measured on its own section (the recess is
    not the board outline: it is 0.05 mm inside it today, and that is DRH's open fit
    decision, not something to assume here). Stations a mount boss stands on are skipped --
    a boss is not lip -- and `worst` is the largest error where a single row governs."""
    span = H if edge in "WE" else W
    off = lambda m: (m[0] if edge == "W" else W - m[0]) if edge in "WE" else \
                    (m[1] if edge == "S" else H - m[1])
    along = lambda m: m[1] if edge in "WE" else m[0]
    bosses = [along(m) for m in mounts if off(m) < boss_r + 3.0]
    bad, n, worst = [], 0, 0.0
    t = LIP_CORNER
    while t <= span - LIP_CORNER + 1e-9:
        if not any(abs(t - b) <= boss_r + 0.3 for b in bosses):
            near = [w for lo, hi, w, _n in rows if lo <= t + LIP_BLEND and hi >= t - LIP_BLEND]
            got = edge_reach(lip_cut, edge, t, W, H)
            wall = edge_reach(recess_cut, edge, t, W, H)
            n += 1
            if got is None or wall is None or not near:
                bad.append((t, got, None, None))
            else:
                lo, hi = min(near), max(near)
                top = max(hi, wall) if hi <= 0.0 else hi          # no lip: nothing past the recess wall
                if not ((lo <= 0.0 or got >= lo - LIP_TOL) and got <= top + LIP_TOL):
                    bad.append((t, got, lo, hi))
                elif lo == hi and hi > 0.0:
                    worst = max(worst, abs(got - hi))
        t = round(t + LIP_STEP, 6)
    return bad, n, worst


def deepest(overlap, body):
    """How far the overlap reaches into `body`, and where -- (depth mm, (x, y)).

    The depth is the largest inset of the body that the overlap still touches, found by
    bisection. (Measuring the overlap's own vertices against the body's edge reads 0.000
    for a strip of metal that crosses a part from side to side: every vertex of such a
    strip lies ON the edge.)"""
    x0, y0, x1, y1 = body.bounds
    lo, hi = 0.0, min(x1 - x0, y1 - y0) / 2.0
    for _ in range(24):
        mid = (lo + hi) / 2.0
        core = body.buffer(-mid)
        if not core.is_empty and core.intersects(overlap):
            lo = mid
        else:
            hi = mid
    core = body.buffer(-lo * 0.999) if lo > 0 else body
    at = overlap.intersection(core)
    at = overlap if at.is_empty else at
    return lo, at.representative_point().coords[0]


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
        z = up_hits(shell, W / 2.0, H / 2.0)
        if z is not None:
            err(f"open frame: an upward ray at the cavity centre hits frame material at "
                f"z={float(z.min()):.3f} -- the back is not open")
        else:
            ok("open frame: an upward ray at the cavity centre hits nothing -- "
               "the back really is open")
    else:
        floor_z = top_at(shell, W / 2.0, H / 2.0)
        if floor_z is None:
            err("no shell material under the cavity centre -- cannot locate the floor plane")
        elif abs(floor_z - floor) <= TOL:
            ok(f"cavity floor measures {floor_z:.3f}, the {floor} the brace is built to rest on")
        else:
            err(f"cavity floor measures {floor_z:.3f}, not {floor} -- every Z below is off by "
                f"{floor_z - floor:+.3f}")

    # the shell, sliced once: [B] and [F] both read these
    shell_cuts = [(lbl, z, section(shell, z, trimesh)) for lbl, z in cavity_levels(floor, cavity)]

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

        # THE BRACE AGAINST THE CAVITY THE SHELL ACTUALLY HAS. This used to compare the
        # brace's bounding box with fit_rules.cavity_rect() -- the rectangle the brace was
        # cut from -- and so reported "sits inside the cavity" on every run while the
        # emitted brace overhung the emitted east wall by 0.20 mm (see the docstring).
        # Now both sides are the artifacts: the same horizontal cut through each.
        from shapely.affinity import translate
        worst_gap, pre = None, len(_ERRORS)
        for lbl, z, metal in shell_cuts:
            resin = section(brace, z - floor, trimesh)
            if resin.is_empty:
                err(f"brace has no material at z {z - floor:.3f} of its own {cavity} height "
                    f"({lbl}) -- nothing to compare")
                continue
            over = metal.intersection(resin)
            if over.area > OVERLAP_EPS:
                x0, y0, x1, y1 = over.bounds
                err(f"brace and shell occupy the same {over.area:.3f} mm2 {lbl} (z {z:.2f}): "
                    f"board x {x0:.3f}..{x1:.3f}, y {y0:.2f}..{y1:.2f} -- the brace is "
                    f"{min(x1 - x0, y1 - y0):.3f} mm too big there and will not drop in")
            else:
                gap = metal.distance(resin)
                worst_gap = gap if worst_gap is None else min(worst_gap, gap)
            # canary: the same cut, the brace pushed 1 mm east, MUST collide with the wall
            if metal.intersection(translate(resin, 1.0, 0.0)).area <= OVERLAP_EPS:
                err(f"SELF-TEST: the brace shifted 1 mm east still clears the shell {lbl} -- "
                    f"the two sections are not in one frame, so a clean result means nothing")
        if len(_ERRORS) == pre:
            bb = brace.bounds
            ok(f"brace drops into the emitted cavity at all {len(shell_cuts)} "
               f"levels: no plan overlap with shell metal, closest approach {worst_gap:.3f} mm "
               f"(brace spans board x {fr.board_xy(bb[0][0], 0.0)[0]:.3f}.."
               f"{fr.board_xy(bb[1][0], 0.0)[0]:.3f}); "
               f"canary collides as it must")

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
            t = top_at(brace, px, py)
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
        spans = ring_spans(shell, mx, my, probe_r)
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
                t = top_at(shell, fx, fy)
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

    # ---- 6. the shell against every B-side body, in plan -----------------------------
    # interference_drc.py casts the BRACE against the parts and skips the supercaps (their
    # height is None by design); check [8] proves fit_rules' polygons clear them. Neither
    # ever looked at the SHELL's metal -- which is how four cans sat inside eight bosses.
    # Every body here, the caps included, at every cut that passes through it.
    print("[F] shell metal vs B-side bodies (sectioned)")
    from shapely.geometry import box as _box
    seat = floor + cavity
    rows, pre = [], len(_ERRORS)
    for ref, poly, h, src in bp.parts("B"):
        if h is None and ref.startswith("SC"):
            h = v["cap_h"]               # the supercaps: None in the table, the cavity is built on them
        if h is None:
            err(f"{ref}: no height in part_heights, so where its body ends is unknown -- "
                f"cannot be checked against the shell")
            continue
        hit = None
        gap = None
        for lbl, z, metal in shell_cuts:
            if z <= seat - h:            # this cut passes UNDER the part: nothing of it down here
                continue
            over = metal.intersection(poly)
            if over.area > OVERLAP_EPS:
                depth, (px, py) = deepest(over, poly)
                if hit is None or over.area > hit[0]:
                    hit = (over.area, depth, px, py, lbl, z)
            else:
                d = metal.distance(poly)
                gap = d if gap is None else min(gap, d)
        if hit is not None:
            area, depth, px, py, lbl, z = hit
            err(f"{ref}: {area:.3f} mm2 of shell metal INSIDE its {h:.2f} mm body {lbl} "
                f"(z {z:.2f}), reaching {depth:.3f} mm in at board ({px:.2f}, {py:.2f})"
                + (" -- and it is bare copper, so that is a short as well as a crush"
                   if src == "pads" else ""))
        elif gap is None:
            err(f"{ref}: no section passes through its {h:.2f} mm body -- cannot be checked")
        else:
            rows.append((gap, ref, h, src))
            if gap < SECTION_FLOOR:
                err(f"{ref}: shell metal stands {gap:.3f} mm from its body -- inside the "
                    f"{SECTION_FLOOR} mm this section can resolve, i.e. contact")
    if not rows and len(_ERRORS) == pre:
        err("no B-side bodies came back from board_parts -- nothing was checked")
    rows.sort()
    for gap, ref, h, src in rows[:6]:
        print(f"          {ref:6s} h={h:.2f} {'body' if src == 'model' else 'pads'}  "
              f"nearest shell metal {gap:.3f} mm")
    # canary: a 0.3 mm "part" planted in the thread land of each boss -- between the bore
    # and THREAD_KEEP, the one ring no scallop is ever allowed into -- must read as
    # metal-inside-a-body. Taken at the cut under the seat, above every spotface.
    blind = []
    for mx, my in fr.MOUNTS:
        r = (fr.PILOT_R + fr.THREAD_KEEP) / 2.0
        fake = _box(mx - 0.15, my + r - 0.15, mx + 0.15, my + r + 0.15)
        if shell_cuts[0][2].intersection(fake).area <= OVERLAP_EPS:
            blind.append((mx, my))
    if blind:
        err(f"SELF-TEST: a synthetic part planted in the boss at {blind} reads as CLEAR -- "
            f"the section does not see the shell there, so every 'clear' above is unproven")
    if len(_ERRORS) == pre:
        ok(f"all {len(rows)} B-side bodies clear the shell's metal at every cut through "
           f"them (tightest {rows[0][1]} at {rows[0][0]:.3f} mm; six tightest above); "
           f"{len(fr.MOUNTS)} planted canaries all read as collisions")

    # ---- 7. the lip the shell drawing describes is the lip the shell has -------------
    # fit_rules.lip_as_cut() is what the drawing's lip note is written from. It is checked
    # against fit_rules' own polygon where it is computed; this is the check that matters,
    # against the metal. Mid-cavity, clear of the lip-break at the seat.
    print("[G] support lip vs its description (sectioned)")
    pre = len(_ERRORS)
    lip_cut = shell_cuts[1][2]
    recess_cut = section(shell, seat + fr.BOARD_TH / 2.0 + _NUDGE, trimesh)
    n_all, worst_all, canary_hits, said = 0, 0.0, 0, []
    for edge in "WESN":
        rows = fr.lip_as_cut(edge)
        bad, n, worst = lip_disagreements(rows, edge, lip_cut, recess_cut,
                                          fr.MOUNTS, fr.BOSS_R, W, H)
        n_all += n
        worst_all = max(worst_all, worst)
        if n < 100:
            err(f"{edge} edge: only {n} stations could be measured -- too few to say the lip "
                f"matches anything")
        if bad:
            ax = "y" if edge in "WE" else "x"
            t, got, lo, hi = bad[0]
            what = ("the section has no wall there" if got is None or lo is None else
                    f"metal reaches {got:.3f} mm in from the board edge, description allows "
                    f"{lo:.2f}..{hi:.2f}")
            err(f"{edge} edge: the shell's lip is not the lip fit_rules.lip_as_cut() describes "
                f"at {len(bad)} of {n} stations (first at {ax}{t:.1f}: {what}; last at "
                f"{ax}{bad[-1][0]:.1f}) -- the drawing's lip note is written from that "
                f"description, so the sheet and the STEP it says governs disagree")
        said.append(f"{edge} " + "/".join(dict.fromkeys(
            "none" if w == 0.0 else f"{w:.2f}" for _lo, _hi, w, _n in rows)))
        # canary: the same measurement against a description 0.5 mm too wide on every row
        wide = [(lo, hi, w + 0.5, names) for lo, hi, w, names in rows]
        canary_hits += len(lip_disagreements(wide, edge, lip_cut, recess_cut,
                                             fr.MOUNTS, fr.BOSS_R, W, H)[0])
    if canary_hits < n_all / 2.0:
        err(f"SELF-TEST: a lip description 0.5 mm too wide on every row disagrees with the "
            f"shell at only {canary_hits} of {n_all} stations -- the section is not measuring "
            f"the lip, so agreement above means nothing")
    if len(_ERRORS) == pre:
        ok(f"the lip in the metal is the lip the drawing's note describes ({'; '.join(said)}): "
           f"{n_all} stations on four edges, worst {worst_all:.3f} mm off where one width "
           f"governs; a description 0.5 mm too wide disagrees at {canary_hits}, as it must")

    # ---- 8. the shell AS A ROUND CUTTER LEAVES IT -----------------------------------
    # The STEP keeps every inside corner of the cavity sharp, and the sheet tells the shop to
    # finish them with a Ø(2 x TOOL_R) tool -- which leaves TOOL_R of metal in each. [B] and
    # [F] measure the sharp model, so two findings of 2026-11-13 passed both: the brace ran
    # 0.225 mm into the fillets at the east boss-to-wall corners, and at the east mid-span
    # bosses the fillet reached a max-material SC2 / SC4 by 0.113 / 0.130 (SolidCraft 0.134).
    # Same sections; the void is opened by the radius before anything is compared.
    print(f"[H] the shell as milled (every sharp inside corner given the Ø{2 * fr.TOOL_R:g} "
          f"finisher's radius)")
    from shapely.geometry import box as _box2
    pre = len(_ERRORS)
    R = fr.TOOL_R
    room = _box2(-1.0, -1.0, W + 1.0, H + 1.0)
    milled = []
    for lbl, z, metal in shell_cuts:
        void = room.difference(metal)
        opened = (void.buffer(-R, join_style=1, quad_segs=32)
                      .buffer(R, join_style=1, quad_segs=32))
        milled.append((lbl, z, metal, room.difference(opened)))
    # canary: the radius must add metal somewhere, and a speck planted in the largest fillet
    # must read clear of the sharp metal and inside the milled metal -- or this check cannot
    # tell the two shells apart and every 'clear' below is the sharp model again
    _l, _z, sharp0, milled0 = milled[0]
    fil = milled0.difference(sharp0)
    pieces = [g for g in getattr(fil, "geoms", [fil]) if g.geom_type == "Polygon"]
    if not pieces or max(g.area for g in pieces) < 0.02:
        err("SELF-TEST: the finisher's radius adds no metal at any corner of the section -- "
            "the opening is not being applied, so this check is [F] again")
    else:
        big = max(pieces, key=lambda g: g.area)
        sp = big.representative_point().buffer(0.01)
        if sharp0.intersection(sp).area > 1e-9 or milled0.intersection(sp).area < sp.area * 0.99:
            err("SELF-TEST: a speck planted in the largest fillet does not read as "
                "milled-metal-only -- the two shells are not being told apart")
    if brace is not None:
        worst = None
        for lbl, z, _metal, mm in milled:
            resin = section(brace, z - floor, trimesh)
            over = mm.intersection(resin)
            for g in getattr(over, "geoms", [over]):
                if g.area > OVERLAP_EPS:
                    c = g.centroid
                    err(f"brace and the AS-MILLED shell occupy the same {g.area:.3f} mm2 {lbl} "
                        f"(z {z:.2f}) at board ({c.x:.2f}, {c.y:.2f}) -- the brace runs into "
                        f"the R{R:g} the finisher leaves in that corner")
            if over.area <= OVERLAP_EPS:
                d = mm.distance(resin)
                worst = d if worst is None else min(worst, d)
        if worst is not None and len(_ERRORS) == pre:
            ok(f"brace clears the as-milled shell at all {len(milled)} levels "
               f"(closest {worst:.3f} mm)")
    rows = []
    seat = floor + cavity
    for ref, poly, h, src in bp.parts("B"):
        if h is None and ref.startswith("SC"):
            h = v["cap_h"]
        if h is None:
            continue
        env = fr.part_envelope(ref, poly)
        for name, shape in ((ref, poly),) + (((ref + " max-material", env),) if env is not poly else ()):
            gap = None
            for lbl, z, _metal, mm in milled:
                if z <= seat - h:
                    continue
                over = mm.intersection(shape)
                if over.area > OVERLAP_EPS:
                    depth, (px, py) = deepest(over, shape)
                    err(f"{name}: {over.area:.4f} mm2 of AS-MILLED metal inside it {lbl} "
                        f"(z {z:.2f}), {depth:.3f} mm deep at board ({px:.2f}, {py:.2f}) -- "
                        f"the R{R:g} the finisher leaves in a corner the model keeps sharp")
                    gap = -1.0
                    break
                d = mm.distance(shape)
                gap = d if gap is None else min(gap, d)
            if gap is not None and gap >= 0:
                rows.append((gap, name))
                if gap < SECTION_FLOOR:
                    err(f"{name}: as-milled metal stands {gap:.3f} mm from it -- contact")
    rows.sort()
    for gap, name in rows[:6]:
        print(f"          {name:18s} nearest as-milled metal {gap:.3f} mm")
    if len(_ERRORS) == pre:
        ok(f"{len(rows)} bodies (the supercaps also at max material, fit_rules.part_envelope) "
           f"clear the shell as an R{R:g} finisher leaves it (tightest {rows[0][1]} "
           f"{rows[0][0]:.3f}); the planted fillet speck reads as milled metal, as it must")

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
