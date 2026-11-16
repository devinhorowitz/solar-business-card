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

THE COIL CHECK ([I], 2026-11-14) holds the one clearance on the sheet that is not to a
part: grounded metal stands fit_rules.COIL_CLR off NFC coil copper, because titanium over
the antenna detunes it. The rule was written for the east lip, and the lip was the only
feature ever held to it -- check [8] compares the lip bands with the coil's east edge and
nothing else. The two east mid-span bosses are the same metal at the same height, and on
every committed shell they stood 0.874 and 0.966 mm from the coil, under a note printing
1.00. An independent measurement of the STEP found it (SolidCraft, 0.877); nothing here
could have, because nothing here measured it. So [I] takes the copper off the board and
the metal out of the sections -- every level, and again as the finisher leaves it -- and
measures one against the other. Its canary is a coil 0.25 mm fatter, which must read as
too close at the east lip and at each boss the cut was made in, separately.

THE JUNCTION CHECK ([J], 2026-11-14) holds the newest thing the sheet says about a boss:
that it meets the lip's wall in a modelled blend, twelve of them (fit_rules.BLEND_R, or
the finisher's own radius where the ferrite sheet stands beside one), and that each corner
boss is solid to the recess wall. Until that day every such junction was
a sharp inside corner in the STEP and each corner boss stood beside a 0.17 mm slot no tool
could enter; DRH saw both in a render. The blends and webs are laid out in fit_rules and
cut by the shell CAD -- two files, and "the rule moved into fit_rules" is exactly the
sentence that preceded the boss and brace findings above. So [J] probes the sectioned
shell: just outside each blend's circle there must be metal and just inside it air, at
three places along the arc on every level, and the middle of each web's pocket must be
metal. Its canary is the same section with the junctions put back the way they were --
the blend's own region and the pocket taken out of the metal -- which must fail. The BACK
FACE has the junction too (each proud annulus against the proud frame, sixteen blends,
fit_rules.back_blends) and [J] probes it the same way, on a cut through the frame's own
0.15 mm of height, wherever the variant has a back face.

THE FLOOR FILLETS ([K], 2026-11-15). The floor meets the wall through an R1.00 on eight
straight runs (fit_rules.floor_runs: the long walls of the supercap bays, nowhere a brace
bears), each ending in a flat cutter's scoop. [K] probes them on the one cut that passes
through them, just above the floor: metal inside each fillet's edge, air outside it, air
at and beyond both ends of every run; its canary is that cut with the fillet taken out.
It also PRINTS what the rule rests on and no section can show -- the supercaps' edges
stand over four of the runs, a square-edged can at max material is not cleared, and the
margin a foil pouch is taken to have is PROVISIONAL (TODO.md). And because a fillet of
R1.00 is still metal at mid-height on the 1.22 cavity, [G] reads the lip just under the
seat, above them.

THE CORNER-BOSS ROOTS (2026-11-15) are in [J] and in [H]. Each corner boss's flat runs to
the short-edge wall through a plain R of the finisher (fit_rules.boss_roots) where a Ø2.0
bore used to stand clear of the supercap; [J] probes the four arcs as it does a tab's
root. [H] is where the cost shows: that corner stands up to 0.07 mm into the corner of a
square-cornered can at MAX MATERIAL, which the bore existed to prevent. DRH took the
simpler cut on the floor fillet's ground, so [H] holds it the floor fillet's way: only
metal inside a root fit_rules lays out is let off (by construction, never a coordinate),
the can's BODY -- taken to stand FLOOR_CAP_MARGIN inside its max-material outline,
PROVISIONAL -- must clear the as-milled shell instead, the measured depth is printed, and
the gate fails if the rule and the part disagree about what the corner costs or if
fit_rules says a root reaches a can and the section saw nothing there.

THE REAR ART ([L], 2026-11-15) exists because the two short-edge tabs were cut alike that
day. Until then the inside of a shell differed top for bottom by half a millimetre of tab,
and [J] held that -- which was the whole of what told a shell's hand in the one placement
where a mirror image fits the board. With the tabs alike, a shell with no rear art has no
hand at all (scripts/handedness_drc.py [E] proves each is its own reflection), and the
max shell's hand is its medallion and nothing else. Nothing had ever read the medallion.
[L] sections the proud face and holds the coin's standing islands to medallion.geometry()
through fit_rules.board_geom(), with the shell reflected top for bottom as its canary; and
it reads the monogram as a person sees the back, against the letters as the font draws
them -- which owes medallion.py's own mirror nothing. A variant with no rear art gets a
note saying it has no hand, not a skipped check.

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
# ---- the coil check ([I]) ----------------------------------------------------------------
# What a section of a HOLLOW arc can resolve. The boss relief is an R1.15 hollow, the STL
# inscribes it with chords, and a chord of a hollow lies on the metal's side: at the 0.2 rad
# the shell is tessellated to that is R(1 - cos 0.1) = 0.006 mm of metal the STEP does not
# have. Three times that, and still under the 0.034 mm the shallower of the two original
# violations stood inside the rule by.
COIL_TOL = 0.02
# The canary's coil is this much fatter than the board's. The lip is cut to stand EXACTLY the
# clearance off, so any growth past COIL_TOL must read as a violation there; a quarter
# millimetre leaves no doubt which side of it we are. A boss cut STRAIGHT for the coil
# (fit_rules.boss_coil_cuts, 2026-11-15) stands a little further off than the rule asks --
# 0.07 and 0.17 mm today -- and the quarter millimetre has to cover that too: [I] refuses to
# call the canary proven on a boss that stands COIL_FAT or more past the clearance.
COIL_FAT = 0.25
# ---- the channel ridge ([C]) -------------------------------------------------------------
# The ridge's faces are planes and section exactly; this is headroom for the 0.005 mm the
# generator samples its width at, not a clearance.
RIDGE_TOL = 0.01
# [J]: how far each side of a blend's circle the probes stand. More than the shell STL's
# 0.04 chord error (a concave cylinder's facets lie on the AIR side of it), and less than
# the thinnest a blend is at the stations probed (0.13 mm, the west bosses at 0.3 of the arc).
JUNC_PROBE = 0.06
JUNC_AT = (0.3, 0.5, 0.7)
# [J], the outside rounds: how far each side of a round's circle the probes stand. A round is
# a CONVEX cylinder of R1.0, and at the STL's 0.2 rad its facets stand at most 0.005 inside
# it, so these can stand closer than a blend's -- and have to, because a round on a shallow
# corner takes little: 0.075 mm deep where a flat meets a bore. ROUND_IN is how far inside
# the removed corner an air probe has to stand before a section is trusted to see it.
ROUND_PROBE = 0.03
ROUND_IN = 0.01
# [J] on the back face: where the cut is taken, as a fraction of the frame's height measured
# from the art field. The frame's 0.10x45 edge-break takes the outer two thirds of a 0.15
# frame; at 0.2 of the height the outline is still the blend's own circle.
BACK_CUT_FRAC = 0.2
# [K], the floor fillets: how far each side of a fillet's edge the probes stand, on the cut just
# above the floor. A lying concave cylinder sections as a straight line, and its facets stand at
# most R(1 - cos 0.1) = 0.005 on the air side of it; at that cut the fillet reaches 0.57 mm from
# the wall, so 0.06 either side is far inside what is there and far outside the error.
FLOOR_PROBE = 0.06
FLOOR_AT = (0.2, 0.5, 0.8)
RIDGE_STEP = 0.02
OVERLAP_EPS = 1e-3    # mm2 of plan overlap that counts as metal inside a body, not noise
# [L], the rear art. Measured 2026-11-15 on the max shell: the standing islands in the metal
# differ from medallion.geometry()'s by 0.0006 mm2 of 136 before the erosion and nothing after
# it; reflected top for bottom, by 88.5. The monogram matches the font's own letters 0.998 as
# seen from the back, 0.638 mirrored left for right, 0.795 top for bottom, 0.587 turned half a
# turn (intersection over union, each normalised to its own box).
ART_ERODE = 0.02      # mm: takes the tessellation's hairlines off a difference of two outlines
ART_OFF_MAX = 0.05    # mm2 of standing art that may differ from the layout
ART_TELL = 10.0       # mm2 the reflected art must differ by, or the art tells no hand
ART_READS = 0.95      # the monogram against the font's letters, as seen from the back
ART_MISREADS = 0.90   # ...and the most any mirrored reading may score
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


def lip_disagreements(rows, edge, lip_cut, recess_cut, mounts, boss_r, W, H, skip=None):
    """([(t, got, lo, hi)], n_stations, worst) -- where the sectioned shell does not have the
    lip `rows` describes along `edge`. `rows` is fit_rules.lip_as_cut()'s shape,
    [(lo, hi, width, names)], width 0.0 meaning no lip.

    A station passes if the metal's reach from the board edge lies between the narrowest and
    the widest row within LIP_BLEND of it -- so it must EQUAL the row's width wherever a row
    runs undisturbed, and only a blend or a relief arc is given room. "No lip" means no
    ledge inboard of the recess wall, which is measured on its own section (the recess is
    not the board outline: it is 0.05 mm inside it today, and that is DRH's open fit
    decision, not something to assume here). Stations a mount boss stands on are skipped --
    a boss is not lip -- and `worst` is the largest error where a single row governs.

    `skip` is {mount: half-width} for the bosses whose footprint along this edge is wider
    than the disc: since 2026-11-14 a boss runs into the lip's wall through a blend
    (fit_rules.boss_blends), and the blend is not lip either. What it IS is [J]'s to hold."""
    span = H if edge in "WE" else W
    off = lambda m: (m[0] if edge == "W" else W - m[0]) if edge in "WE" else \
                    (m[1] if edge == "S" else H - m[1])
    along = lambda m: m[1] if edge in "WE" else m[0]
    bosses = [(along(m), max(boss_r + 0.3, (skip or {}).get(m, 0.0)))
              for m in mounts if off(m) < boss_r + 3.0]
    bad, n, worst = [], 0, 0.0
    t = LIP_CORNER
    while t <= span - LIP_CORNER + 1e-9:
        if not any(abs(t - b) <= hw for b, hw in bosses):
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


def _slight_depth(rd):
    """How deep the corner a round took off was: the farthest the removed metal stands from
    the round's own circle."""
    ox, oy = rd["O"]
    return max(((x - ox) ** 2 + (y - oy) ** 2) ** 0.5
               for g in getattr(rd["took"], "geoms", [rd["took"]])
               for x, y in g.exterior.coords) - rd["r"]


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

        # THE RIDGE EAST OF THE CHANNEL (2026-11-14). It is let off fit_rules.SLA_WALL on
        # purpose -- it is what locates the ferrite's critical width -- and until this check
        # it was let off everything: at both ends it followed the brace's edge round a boss
        # fillet and tapered to a point, found by measuring the built braces. The floor it
        # is held to is fit_rules.PRINT_WALL, the wall the print spec says the printer must
        # hold. Measured as a wall's thickness is, straight across, on the emitted brace.
        from shapely.geometry import LineString as _Ln, Point as _Pp
        zc = cavity - fr.FER_POCKET_DEPTH / 2.0 + _NUDGE * 0.1
        resin = section(brace, zc, trimesh)
        mid_y = (fy0 + fy1) / 2.0
        # the cut must be IN the channel: the sheet's own centre void, the brace's floor
        # 0.2 mm lower solid at the same spot (a cut above the brace, or under the channel's
        # floor, would read every chord wrong and say nothing)
        under = section(brace, cavity - fr.FER_POCKET_DEPTH - 0.2, trimesh)
        centre = _Pp((fx0 + fx1) / 2.0, mid_y)
        if resin.is_empty or resin.contains(centre) or not under.contains(centre):
            err(f"SELF-TEST: the cut at z {zc:.3f} is not through the ferrite channel (the "
                f"sheet's centre must read as void there, and as resin 0.2 mm under the "
                f"channel's floor) -- the ridge cannot be measured on it")
        else:
            widths = []
            n = int(round((fy1 - fy0 + 2.0) / RIDGE_STEP))
            for k in range(n + 1):
                y = fy0 - 1.0 + k * RIDGE_STEP
                w = resin.intersection(_Ln([(fx1, y), (W + 1.0, y)])).length
                if w > 1e-6:
                    widths.append((y, w))
            if len(widths) < 100:
                err(f"only {len(widths)} stations found resin east of the ferrite at the "
                    f"channel's level -- the ridge that walls the sheet's critical width is "
                    f"not there to measure")
            else:
                need_w = fr.PRINT_WALL - RIDGE_TOL
                thin = [(y, w) for y, w in widths if w < need_w]
                wmax = max(w for _y, w in widths)
                # canary: the same ridge shaved to half the floor must fail at every station
                shave = wmax - fr.PRINT_WALL / 2.0
                if any(w - shave >= need_w for _y, w in widths):
                    err("SELF-TEST: a ridge shaved to half of PRINT_WALL still passes at some "
                        "station -- the width comparison is not live")
                if thin:
                    y, w = min(thin, key=lambda t: t[1])
                    err(f"the ridge east of the ferrite channel is under the "
                        f"{fr.PRINT_WALL} mm wall the print spec's printer holds at "
                        f"{len(thin)} of {len(widths)} stations (y {thin[0][0]:.2f}.."
                        f"{thin[-1][0]:.2f}; thinnest {w:.3f} mm at y {y:.2f}) -- a feather "
                        f"tip that prints as flash or not at all")
                else:
                    ok(f"the ridge east of the channel stands y {widths[0][0]:.2f}.."
                       f"{widths[-1][0]:.2f}, {min(w for _y, w in widths):.3f}..{wmax:.3f} mm "
                       f"wide at {len(widths)} stations -- nowhere under PRINT_WALL "
                       f"{fr.PRINT_WALL}; shaved to half of that it fails everywhere, as it must")

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
    # THE BACK SPOTFACE, IN THE METAL (2026-11-16). Each mount carries a flat-bottomed cut from
    # the back to the plane the screw's tip reaches. On a floored shell it is in the floor. On
    # the open frame it is in the boss, whose flat stands boss_flat_d() from the axis, and until
    # this date the cut was wider than that: it broke out through the foot of all eight flats,
    # 0.545 mm wide, with a knife edge either side (the second outside review; this section
    # of the committed frame reads it too). Sectioned just under the cut's bottom: air inside
    # its radius, and metal ALL THE WAY ROUND just outside it.
    from shapely.geometry import Point as _PtD
    sf_d = v["spotface_d"]
    sf_where, sf_margin = fr.spotface_fit(vname)
    sf_tip = floor + cavity + fr.BOARD_TH - screw_len
    sf_sec = section(shell, sf_tip - 0.04, trimesh)
    sf_out = sf_d / 2.0 + min(0.10, max(sf_margin, 0.02) / 2.0)   # a ring inside the wall it leaves
    sf_in = sf_d / 2.0 - 0.05
    sf_n, sf_bad, sf_blind = 72, [], 0
    for mx, my in fr.MOUNTS:
        ring = lambda r_: [sf_sec.contains(_PtD(mx + r_ * np.cos(2 * np.pi * i / sf_n),
                                                my + r_ * np.sin(2 * np.pi * i / sf_n)))
                           for i in range(sf_n)]
        gone = sf_n - sum(ring(sf_out))
        if gone:
            sf_bad.append((mx, my, gone))
        if any(ring(sf_in)):
            err(f"mount ({mx},{my}): metal inside the Ø{sf_d:g} back spotface at z "
                f"{sf_tip - 0.04:.2f} -- the cut is not there, or not that size")
        sf_blind += 0 if not all(ring(sf_in)) else 1
    if sf_bad:
        err(f"the Ø{sf_d:g} back spotface is not walled all the way round at "
            f"{len(sf_bad)} of {len(fr.MOUNTS)} mounts: at ({sf_bad[0][0]},{sf_bad[0][1]}) "
            f"{sf_bad[0][2]} of {sf_n} probes at r {sf_out:.2f} find air"
            + (" -- the cut breaks out through the boss" if sf_where == "boss" else
               " -- the cut comes up out of the floor"))
    if sf_blind:
        err("SELF-TEST: a ring of probes INSIDE a spotface found metal all the way round -- the "
            "probe cannot tell a cut from metal")
    if len(_ERRORS) == pre_screw_errs:
        extra = (", tip stays >= 0 above the resting plane" if open_back
                 else f" (back face {back:.3f})")
        ok(f"all {len(fr.MOUNTS)} mounts: boss material present, {screw_len} mm screw lands "
           f"inside the shell{extra}; each Ø{sf_d:g} back spotface is cut and is walled all the "
           f"way round ({sf_n} probes at r {sf_out:.2f}; it is in the {sf_where}, with "
           + (f"{sf_margin:.3f} mm of boss wall left round it by rule)" if sf_where == "boss" else
              f"{sf_margin:.3f} mm of floor left over its bottom by rule)"))

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
    # THE FERRITE SHEET IS A BODY TOO (2026-11-14). It is not on the board -- it lies in the
    # brace's channel, under the coil -- so board_parts does not return it, and until that day
    # nothing held it against the shell at all: [C] proved the pocket under it and stopped.
    # The first build of the boss blends put titanium inside both of its east corners (0.035
    # and 0.075 mm2) with every gate green. It is cut here like any other body, over its own
    # thickness under the seat, wherever there is a brace to carry it.
    bodies = list(bp.parts("B"))
    if brace is not None:
        bodies.append((fr.FER_REF, _box(*fr.FER), fr.FER_T, "sheet"))
    kind = {"model": "body", "pads": "pads", "sheet": "sheet"}
    for ref, poly, h, src in bodies:
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
        print(f"          {ref:6s} h={h:.2f} {kind.get(src, src):5s} "
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
        ok(f"all {len(rows)} B-side bodies"
           + (f" (the ferrite sheet {fr.FER_REF} among them)" if brace is not None else "")
           + f" clear the shell's metal at every cut through "
           f"them (tightest {rows[0][1]} at {rows[0][0]:.3f} mm; six tightest above); "
           f"{len(fr.MOUNTS)} planted canaries all read as collisions")

    # ---- 7. the lip the shell drawing describes is the lip the shell has -------------
    # fit_rules.lip_as_cut() is what the drawing's lip note is written from. It is checked
    # against fit_rules' own polygon where it is computed; this is the check that matters,
    # against the metal. Just under the seat: below the lip-break (the break's frustum is still
    # 0.03 inside the void at this level) and ABOVE the floor fillets. It was the mid-cavity
    # cut until 2026-11-15; a fillet of R1.00 on a 1.22 cavity is still 0.07 mm of metal at
    # mid-height, and the lip note describes the lip, not the fillet under it.
    print("[G] support lip vs its description (sectioned)")
    pre = len(_ERRORS)
    lip_cut = shell_cuts[0][2]
    recess_cut = section(shell, seat + fr.BOARD_TH / 2.0 + _NUDGE, trimesh)
    n_all, worst_all, canary_hits, said = 0, 0.0, 0, []
    for edge in "WESN":
        rows = fr.lip_as_cut(edge)
        # how far along this edge each boss's blends run: the foot of each, plus the margin
        # a bare boss already gets
        _along = (lambda q: q[1]) if edge in "WE" else (lambda q: q[0])
        skip = {m: max([abs(_along(b["F"]) - _along(m)) + 0.3 for b in fr.boss_blends(*m)] or [0.0])
                for m in fr.MOUNTS}
        bad, n, worst = lip_disagreements(rows, edge, lip_cut, recess_cut,
                                          fr.MOUNTS, fr.BOSS_R, W, H, skip)
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
                                             fr.MOUNTS, fr.BOSS_R, W, H, skip)[0])
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
    # THE CORNER-BOSS ROOTS ARE THE ONE PLACE A MAX-MATERIAL CAN IS NOT CLEARED (2026-11-15,
    # fit_rules.boss_roots; DRH took the simpler cut). Each corner boss's flat runs to the
    # short-edge wall through a plain R of the finisher, and that corner stands up to 0.07 mm
    # inside the very corner of a square-cornered can at max material. Accepted on the floor
    # fillet's ground -- the outside of a pouch's outline is its sealed margin -- and held the
    # same way: the can's BODY, taken to stand FLOOR_CAP_MARGIN inside that outline
    # (PROVISIONAL), must clear the as-milled metal, and what the square corner costs is
    # measured and printed. Recognised BY CONSTRUCTION -- only metal inside a root fit_rules
    # lays out is let off, never a coordinate -- so anything else inside a can is the old error.
    from shapely.geometry import Point as _PtH
    from shapely.ops import unary_union as _uuH
    rootz = _uuH([b["cover"].difference(_PtH(b["O"]).buffer(b["r"] - 0.03, quad_segs=64)).buffer(0.03)
                  for b in fr.boss_roots()]) if fr.boss_roots() else None
    cost = []                                    # (name, mm2, depth) a root stands inside a max-material can
    for ref, poly, h, src in bodies:             # [F]'s list: the board's parts and the ferrite sheet
        if h is None and ref.startswith("SC"):
            h = v["cap_h"]
        if h is None:
            continue
        env = fr.part_envelope(ref, poly)
        for name, shape in ((ref, poly),) + (((ref + " max-material", env),) if env is not poly else ()):
            gap = None
            let_off = rootz if (rootz is not None and shape is env and ref.startswith("SC")) else None
            for lbl, z, _metal, mm in milled:
                if z <= seat - h:
                    continue
                if let_off is not None:
                    in_root = mm.intersection(shape).intersection(let_off)
                    if in_root.area > 1e-6:
                        depth, _at = deepest(in_root, shape)
                        cost.append((name, in_root.area, depth))
                        body = shape.buffer(-fr.FLOOR_CAP_MARGIN, join_style=2)
                        if mm.intersection(body).area > OVERLAP_EPS or mm.distance(body) < SECTION_FLOOR:
                            err(f"{name}: a corner-boss root reaches the can's BODY {lbl} (z {z:.2f}) "
                                f"-- even {fr.FLOOR_CAP_MARGIN} mm inside its max-material outline, "
                                f"which is all the margin a pouch is taken to have")
                    mm = mm.difference(let_off)
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
    # what the plain corners cost, measured -- and held to what fit_rules says they cost
    worst_cost = {}
    for name, a, d in cost:
        if name not in worst_cost or d > worst_cost[name][1]:
            worst_cost[name] = (a, d)
    for name, (a, d) in sorted(worst_cost.items()):
        print(f"          {name:18s} a corner-boss root stands {d:.3f} mm into its corner ({a:.4f} mm2)"
              f"   <- a square-cornered can at max material; see the note below")
    _bite, _need = fr.boss_root_cap_need()
    if rootz is not None:
        said_area = max(b["cap_bite_area"] for b in fr.boss_roots())
        seen = max([d for _a, d in worst_cost.values()] or [0.0])
        if said_area > OVERLAP_EPS and not worst_cost:
            err(f"SELF-TEST: fit_rules.boss_roots() puts a root {_bite:.3f} mm into a max-material "
                f"supercap's corner ({said_area:.4f} mm2) and this section saw no metal there -- "
                f"the corner is not being measured, so 'clear' below means nothing at the roots")
        if seen > _need + 0.03:
            err(f"a corner-boss root stands {seen:.3f} mm into a max-material supercap in the "
                f"metal, where fit_rules.boss_root_cap_need() says {_need:.3f} -- the rule and "
                f"the part disagree about what the plain corner costs")
        if worst_cost:
            note(f"PROVISIONAL: the plain R{R:g} corner at each corner boss clears a supercap only "
                 f"if the can's body stays {_need:.2f} mm inside its max-material outline at that "
                 f"corner (taken to do so by {fr.FLOOR_CAP_MARGIN:.2f}: a foil pouch's sealed "
                 f"margin, which the datasheet does not dimension) -- TODO.md has the caliper check")
    if len(_ERRORS) == pre:
        ok(f"{len(rows)} bodies (the supercaps also at max material, fit_rules.part_envelope) "
           f"clear the shell as an R{R:g} finisher leaves it (tightest {rows[0][1]} "
           f"{rows[0][0]:.3f})"
           + (f", the {len(fr.boss_roots())} corner-boss roots excepted and held to the cans' "
              f"bodies instead" if rootz is not None else "")
           + "; the planted fillet speck reads as milled metal, as it must")

    # ---- 9. grounded metal against the NFC coil --------------------------------------
    # The number held is fit_rules.COIL_CLR ON PURPOSE: it is what the sheet prints ("THE
    # LIP STOPS 1.00 SHORT OF NFC COIL COPPER"), so this is [G]'s shape -- a printed claim
    # held to the metal. What it owes nothing to is fit_rules' polygons: the metal is the
    # sectioned STL and the copper is read off the board.
    print("[I] grounded metal vs the NFC coil (sectioned)")
    from shapely.geometry import LineString as _LS, Point as _Pt
    from shapely.ops import nearest_points as _near, unary_union as _uu
    pre = len(_ERRORS)
    tracks = bp.coil_tracks()
    cu = _uu([(_Pt(a) if a == b else _LS([a, b])).buffer(w / 2.0, quad_segs=32)
              for a, b, w in tracks])
    fat = cu.buffer(COIL_FAT, quad_segs=32)
    need = fr.COIL_CLR - COIL_TOL
    reach = fr.BOSS_R + 0.1
    relieved = [(mx, my) for mx, my in fr.MOUNTS if any(fr.boss_coil_cuts(mx, my))]
    for mx, my in relieved:
        if fr.boss_coil_gap(mx, my) - need >= COIL_FAT:
            err(f"SELF-TEST: the boss at ({mx}, {my}) is cut to stand "
                f"{fr.boss_coil_gap(mx, my):.3f} mm off the coil, {COIL_FAT} or more past the "
                f"{fr.COIL_CLR:.2f} rule -- the fatter-coil canary cannot reach it, so it "
                f"proves nothing there. Raise COIL_FAT")
    east_by_coil = any(fr.COIL_REF in who for _lo, _hi, _w, who in fr.lip_as_cut("E"))
    all_bosses = _uu([_Pt(mx, my).buffer(reach) for mx, my in fr.MOUNTS])
    tight, blind = {}, []          # site -> [as modelled, as milled, where it was tightest]
    for lbl, z, metal, mm in milled:
        if metal.is_empty:
            err(f"the shell has no metal {lbl} (z {z:.2f}) -- nothing to hold to the coil")
            continue
        # site by site, so the second-worst boss is named too and not hidden under the worst
        for name, cut in [("the lip", None)] + [
                (f"the boss at ({mx}, {my})", _Pt(mx, my).buffer(reach)) for mx, my in fr.MOUNTS]:
            row = tight.setdefault(name, [1e9, 1e9, ""])
            for k, m in enumerate((metal, mm)):
                g = m.difference(all_bosses) if cut is None else m.intersection(cut)
                if g.is_empty:
                    continue
                d = g.distance(cu)
                if d < row[k]:
                    row[k] = d
                    if k == 1:
                        on_metal, _on_cu = _near(g, cu)
                        row[2] = f"{lbl}, z {z:.2f}, at board ({on_metal.x:.2f}, {on_metal.y:.2f})"
        # canary: the fatter coil, at the lip and at each relieved boss SEPARATELY, so a
        # section that has lost one of them cannot hide behind the others
        if east_by_coil and metal.difference(all_bosses).distance(fat) >= need:
            blind.append(f"the east lip {lbl}")
        for mx, my in relieved:
            g = metal.intersection(_Pt(mx, my).buffer(reach))
            if g.is_empty or g.distance(fat) >= need:
                blind.append(f"boss ({mx}, {my}) {lbl}")
    for name, (d_model, d_milled, where) in tight.items():
        if d_milled < need:
            err(f"{name} stands {d_milled:.3f} mm from NFC coil copper ({where}) -- inside the "
                f"{fr.COIL_CLR:.2f} mm the sheet prints, and grounded metal that close to the "
                f"antenna detunes it"
                + ("" if d_model < need else
                   f". The model clears it ({d_model:.3f}); the R{R:g} the finisher leaves in "
                   f"a corner beside it does not"))
    if blind:
        err(f"SELF-TEST: a coil {COIL_FAT} mm fatter than the board's still reads as clear of "
            f"{'; '.join(blind)} -- metal fit_rules says is cut to stand exactly "
            f"{fr.COIL_CLR:.2f} off it. The section is not seeing that metal, so every "
            f"'clear' here is unproven")
    near = sorted((d_milled, n) for n, (_dm, d_milled, _w) in tight.items()
                  if d_milled < fr.COIL_CLR + 1.0)
    for d, n in near:
        print(f"          {n:28s} nearest coil copper {d:.3f} mm")
    if not near and len(_ERRORS) == pre:
        err(f"no shell metal within {fr.COIL_CLR + 1.0:.2f} mm of the coil at any level -- the "
            f"east lip is cut to stand {fr.COIL_CLR:.2f} off it, so the section or the coil "
            f"reader has lost one of them")
    if not relieved:
        note("no boss is within reach of the coil on this board -- the fatter-coil canary "
             "has only the east lip to prove itself on")
    if len(_ERRORS) == pre:
        ok(f"no shell metal within {fr.COIL_CLR:.2f} mm of the coil's {len(tracks)} copper "
           f"pieces at any of {len(milled)} levels, as modelled or as milled (tightest "
           f"{near[0][1]} at {near[0][0]:.3f}); a coil {COIL_FAT} mm fatter reads too close at "
           f"{'the east lip and ' if east_by_coil else ''}{len(relieved)} relieved boss(es), "
           f"as it must")

    # ---- 10. each boss meets the wall the way the sheet says ---------------------------
    print("[J] boss blends, webs, outside rounds, tab roots and corner-boss roots (sectioned)")
    import math as _m
    from shapely.geometry import Polygon as _Poly
    pre = len(_ERRORS)
    blind = []

    def probe_blend(b, mx, my, cuts, canary_cut, where):
        """One blend against the sections `cuts`: metal just outside its circle, air just
        inside, at JUNC_AT along the arc; and the canary -- `canary_cut` with the junction
        put back sharp must lose the metal at the arc's middle."""
        (ox, oy), r = b["O"], b["r"]
        a0 = _m.atan2(b["F"][1] - oy, b["F"][0] - ox)
        a1 = _m.atan2(b["T"][1] - oy, b["T"][0] - ox)
        da = (a1 - a0 + _m.pi) % (2 * _m.pi) - _m.pi
        at = lambda k, rr: _Pt(ox + rr * _m.cos(a0 + k * da), oy + rr * _m.sin(a0 + k * da))
        metal_at = [at(k, r + JUNC_PROBE) for k in JUNC_AT]
        air_at = [at(k, r - JUNC_PROBE) for k in JUNC_AT]
        for lbl, z, metal in cuts:
            gone = [q for q in metal_at if not metal.contains(q)]
            full = [q for q in air_at if metal.contains(q)]
            if gone:
                err(f"{where}: no metal {JUNC_PROBE} mm outside its R{r:g} circle {lbl} "
                    f"(z {z:.2f}) at board ({gone[0].x:.2f}, {gone[0].y:.2f}) -- less metal "
                    f"than the blend the sheet calls: a tighter one, or none")
            if full:
                err(f"{where}: metal {JUNC_PROBE} mm INSIDE its R{r:g} circle {lbl} "
                    f"(z {z:.2f}) at board ({full[0].x:.2f}, {full[0].y:.2f}) -- more metal "
                    f"than the blend the sheet calls: a wider one, or one somewhere else")
        # canary: everything between the wall, the boss and the chord from the foot to the
        # boss taken out again. A blend that joins two PLANES -- a straight cut across a boss,
        # or the side of a tab -- has no boss circle in its corner: the whole triangle goes
        tri = _Poly([b["J"], b["F"], b["T"]])
        if mx is not None and not b.get("chord"):
            tri = tri.difference(_Pt(mx, my).buffer(fr.BOSS_R, quad_segs=64))
        sharp = canary_cut.difference(tri)
        if sharp.contains(metal_at[len(metal_at) // 2]):
            blind.append(where)

    def probe_round(rd, cuts, canary_cut, where):
        """One outside round against the sections `cuts`: metal just inside its circle, and
        air just outside it wherever the corner it took off was deep enough for a section to
        tell (ROUND_IN inside the removed metal). The canary: that corner put back must fill
        those probes. Returns how many stations could be probed for air -- 0 means the round
        is too slight for an STL, and the caller says so instead of calling it checked."""
        (ox, oy), r = rd["O"], rd["r"]
        a0 = _m.atan2(rd["A"][1] - oy, rd["A"][0] - ox)
        a1 = _m.atan2(rd["B"][1] - oy, rd["B"][0] - ox)
        da = (a1 - a0 + _m.pi) % (2 * _m.pi) - _m.pi
        at = lambda k, rr: _Pt(ox + rr * _m.cos(a0 + k * da), oy + rr * _m.sin(a0 + k * da))
        metal_at = [at(k, r - ROUND_PROBE) for k in JUNC_AT]
        deep = rd["took"].buffer(-ROUND_IN)
        air_at = [q for q in (at(k, r + ROUND_PROBE) for k in JUNC_AT) if deep.contains(q)]
        for lbl, z, metal in cuts:
            gone = [q for q in metal_at if not metal.contains(q)]
            full = [q for q in air_at if metal.contains(q)]
            if gone:
                err(f"{where}: no metal {ROUND_PROBE} mm inside its R{r:g} circle {lbl} "
                    f"(z {z:.2f}) at board ({gone[0].x:.2f}, {gone[0].y:.2f}) -- more has come "
                    f"off this corner than the round the sheet calls")
            if full:
                err(f"{where}: metal {ROUND_PROBE} mm OUTSIDE its R{r:g} circle {lbl} "
                    f"(z {z:.2f}) at board ({full[0].x:.2f}, {full[0].y:.2f}) -- the corner is "
                    f"still there, or rounded tighter than the sheet calls")
        sharp = canary_cut.union(rd["took"])
        if any(not sharp.contains(q) for q in air_at):
            blind.append(where)
        return len(air_at)

    n_bl = n_web = 0
    mid = shell_cuts[1][2]
    for mx, my in fr.MOUNTS:
        for b in fr.boss_blends(mx, my):
            n_bl += 1
            probe_blend(b, mx, my, shell_cuts, mid,
                        f"the blend at board ({b['J'][0]:.2f}, {b['J'][1]:.2f}), boss ({mx}, {my})")
        for pocket, _cover in fr.boss_webs(mx, my):
            n_web += 1
            q = pocket.representative_point()
            where = f"the web at board ({q.x:.2f}, {q.y:.2f}), boss ({mx}, {my})"
            for lbl, z, metal in shell_cuts:
                if not metal.contains(q):
                    err(f"{where}: no metal there {lbl} (z {z:.2f}) -- the slot between the "
                        f"boss and the recess wall is still in the solid")
            if mid.difference(pocket.buffer(0.01)).contains(q):
                blind.append(where)
    # THE BACK FACE (2026-11-14): each proud annulus runs into the proud frame through the
    # same blend. Cut through the frame's own height, above its edge-break (the break takes
    # the outer 0.10 of the 0.15, so the base of it is the only level where the outline is
    # the blend's own circle).
    n_back = 0
    border = v["border_h"]
    if border > 0:
        zb = -BACK_CUT_FRAC * border
        back_cut = [("through the back frame", zb, section(shell, zb, trimesh))]
        if back_cut[0][2].is_empty:
            err(f"the shell has no metal at z {zb:.3f} -- the back frame is not where "
                f"VARIANTS puts it ({border} proud), so the back blends cannot be checked")
        else:
            for mx, my in fr.MOUNTS:
                for b in fr.back_blends(mx, my):
                    n_back += 1
                    probe_blend(b, mx, my, back_cut, back_cut[0][2],
                                f"the BACK blend at board ({b['J'][0]:.2f}, {b['J'][1]:.2f}), "
                                f"mount ({mx}, {my})")
            if n_back == 0:
                err("fit_rules.back_blends() returned no blend on a variant with a back face")
    # THE OUTSIDE CORNERS (2026-11-14): every outside corner of a boss, and the tip corners
    # of the two short-edge tabs, are rounds of fit_rules.CONTOUR_R -- on the sheet as a count
    # and a radius. Probed like the blends, the other way round.
    n_rd = n_tab = 0
    slight = []
    for mx, my in fr.MOUNTS:
        for rd in fr.boss_rounds(mx, my):
            n_rd += 1
            where = f"the round about board ({rd['O'][0]:.2f}, {rd['O'][1]:.2f}), boss ({mx}, {my})"
            if probe_round(rd, shell_cuts, mid, where) == 0:
                slight.append(rd)
    for rd in fr.tab_rounds():
        n_tab += 1
        where = f"the tab-tip round about board ({rd['O'][0]:.2f}, {rd['O'][1]:.2f})"
        if probe_round(rd, shell_cuts, mid, where) == 0:
            err(f"{where} takes off too little for a section to see -- a tab tip is a square "
                f"corner, and a round of R{rd['r']:g} on one is 0.41 mm deep")
    if n_rd == 0 or n_tab == 0:
        err(f"fit_rules returned {n_rd} boss rounds and {n_tab} tab-tip rounds -- the sheet "
            f"calls both, and nothing was checked")
    # THE TAB ROOTS (2026-11-15): each tab meets the short-edge wall through a true R of the
    # finisher, tangent to the RECESS wall. A blend between two planes, probed as one.
    n_root = 0
    for b in fr.tab_roots():
        n_root += 1
        probe_blend(b, None, None, shell_cuts, mid,
                    f"the {b['edge']} tab's root at board ({b['J'][0]:.2f}, {b['J'][1]:.2f})")
    if n_root == 0:
        err("fit_rules.tab_roots() returned no root -- the sheet calls them, and nothing was checked")
    # THE CORNER-BOSS ROOTS (2026-11-15): each corner boss's flat runs to the short-edge wall
    # and meets it through the same true R. A blend between two planes again.
    n_broot = 0
    for b in fr.boss_roots():
        n_broot += 1
        probe_blend(b, None, None, shell_cuts, mid,
                    f"the corner-boss root at board ({b['J'][0]:.2f}, {b['J'][1]:.2f}), boss {b['boss']}")
    if n_broot == 0:
        err("fit_rules.boss_roots() returned no root -- the sheet calls them, and nothing was checked")
    if blind:
        err(f"SELF-TEST: with the junction put back sharp, the probe still reads metal at "
            f"{blind[0]}" + (f" and {len(blind) - 1} more" if len(blind) > 1 else "") +
            " -- the section cannot tell a blended shell from the old one, so every pass "
            "above is unproven")
    if n_bl == 0:
        err("fit_rules.boss_blends() returned no blend for any boss -- nothing was checked")
    if len(_ERRORS) == pre:
        said = ", ".join(f"{n} at R{r:g}" for r, n in sorted(fr.blend_radii().items(), reverse=True))
        ok(f"{n_bl} blends are in the metal as the arcs fit_rules lays out ({said}: metal "
           f"{JUNC_PROBE} mm outside "
           f"each circle, air {JUNC_PROBE} mm inside it, at {len(JUNC_AT)} places on "
           f"{len(shell_cuts)} levels) and {n_web} corner webs are solid"
           + (f"; {n_back} back-face blends at R{fr.BLEND_R:g} likewise, on a cut through the "
              f"frame" if n_back else "; no back face on this variant")
           + f"; {n_rd - len(slight)} of the {n_rd} boss rounds and all {n_tab} tab-tip rounds "
           f"are R{fr.CONTOUR_R:g} in the metal (metal {ROUND_PROBE} mm inside each circle, air "
           f"{ROUND_PROBE} mm outside it)"
           + (f", and {len(slight)} take off less than a section can see (the deepest "
              f"{max(_slight_depth(rd) for rd in slight):.3f} mm) -- those are held by the shell "
              f"generator, which refuses to export a solid without each round's cylinder among "
              f"its faces" if slight else "")
           + f"; {n_root} tab roots and {n_broot} corner-boss roots are R{fr.TOOL_R:g} on the "
           f"recess wall; the same sections with "
           f"each junction and corner put back sharp fail all "
           f"{n_bl + n_web + n_back + n_rd - len(slight) + n_tab + n_root + n_broot}, as they must")

    # ---- 11. the floor meets the wall through a radius ---------------------------------
    # fit_rules.floor_runs(): an R1.00 fillet on the long straight walls of the supercap bays,
    # each run ending in a flat cutter's scoop. On the sheet as a count, a radius and a length;
    # here as metal -- on the one cut that passes through it, just above the floor.
    print("[K] floor-to-wall fillets (sectioned)")
    pre = len(_ERRORS)
    if floor <= 0:
        note("open frame -- no floor, so no floor fillet by design")
    else:
        runs = fr.floor_runs()
        lbl, zlow, low = shell_cuts[2]
        zrel = zlow - floor
        blind, n_pr = [], 0
        for run in runs:
            r_ = run["r"]
            dd_ = r_ - fr.BLEND_BITE
            if zrel >= dd_:
                err(f"the cut {lbl} (z {zlow:.2f}) is above a fillet's axis -- nothing of it to probe")
                break
            reach = dd_ - _m.sqrt(r_ * r_ - (dd_ - zrel) ** 2)       # how far from the wall it stands at this cut
            at = (lambda s_, u_, _r=run: _Pt(s_, _r["wall"] + _r["sg"] * u_) if _r["axis"] == "x"
                  else _Pt(_r["wall"] + _r["sg"] * u_, s_))
            where = f"the floor fillet on the {run['edge']} wall, {run['axis']}{run['s0']:.2f}..{run['s1']:.2f}"
            a, b = run["s0"] + r_ + 0.3, run["s1"] - r_ - 0.3         # clear of both scoops
            metal_at = [at(a + k * (b - a), reach - FLOOR_PROBE) for k in FLOOR_AT]
            air_at = [at(a + k * (b - a), reach + FLOOR_PROBE) for k in FLOOR_AT]
            # the ends: air on the scoop's axis line half way out, and air beyond the run
            ends_air = [at(run["s0"], reach / 2.0), at(run["s1"], reach / 2.0),
                        at(run["s0"] - 0.3, 0.3), at(run["s1"] + 0.3, 0.3)]
            n_pr += len(metal_at) + len(air_at) + len(ends_air)
            gone = [q for q in metal_at if not low.contains(q)]
            full = [q for q in air_at if low.contains(q)]
            ended = [q for q in ends_air if low.contains(q)]
            if gone:
                err(f"{where}: no metal {FLOOR_PROBE} mm inside its edge {lbl} (z {zlow:.2f}) at "
                    f"board ({gone[0].x:.2f}, {gone[0].y:.2f}) -- the fillet is not there, or is "
                    f"smaller than the R{r_:g} the sheet calls")
            if full:
                err(f"{where}: metal {FLOOR_PROBE} mm OUTSIDE its edge {lbl} (z {zlow:.2f}) at "
                    f"board ({full[0].x:.2f}, {full[0].y:.2f}) -- more metal than an R{r_:g} leaves")
            if ended:
                err(f"{where}: metal at board ({ended[0].x:.2f}, {ended[0].y:.2f}) {lbl}, where the "
                    f"run has ended -- it runs on past its stop, or ends square instead of in the "
                    f"flat cutter's scoop")
            # canary: the same cut with this run's metal taken out must lose every metal probe
            bare = low.difference(run["reach"].buffer(0.01))
            if any(bare.contains(q) for q in metal_at):
                blind.append(where)
        if not runs:
            err("fit_rules.floor_runs() returned no run on a shell with a floor -- the sheet calls "
                "them, and nothing was checked")
        if blind:
            err(f"SELF-TEST: with the fillet taken out of the section, the probe still reads metal "
                f"at {blind[0]}" + (f" and {len(blind) - 1} more" if len(blind) > 1 else "") +
                " -- the section cannot tell a filleted floor from a sharp one")
        # WHAT HANGS OVER THEM. The rule's own numbers, printed where the metal is checked: a
        # machine-placed part must clear a fillet; a supercap does at nominal, and at max
        # material only if the pouch's edge is the thin margin it is taken to be.
        rows = [(gap, ref, kind) for run in runs for ref, kind, gap in run["under"].get(vname, [])]
        for kind in ("part", "cap nominal", "cap margin", "cap max"):
            sel = sorted(x for x in rows if x[2] == kind)
            if sel:
                print(f"          over a fillet, {kind:11s} tightest {sel[0][1]} {sel[0][0]:+.3f} mm"
                      + ("   <- a square-edged can at max material; see the note below" if kind == "cap max" and sel[0][0] < 0 else ""))
        need = fr.floor_cap_margin_needed().get(vname, 0.0)
        if any(x[2] == "cap max" and x[0] < 0 for x in rows):
            note(f"PROVISIONAL: the fillets under the supercaps' edges clear a can only if it is "
                 f"thinner than its stated maximum for {need:.2f} mm in from its max-material "
                 f"outline (taken to be so for {fr.FLOOR_CAP_MARGIN:.2f}: a foil pouch's sealed "
                 f"margin, which the datasheet does not dimension) -- TODO.md has the caliper check")
        if len(_ERRORS) == pre:
            ok(f"{len(runs)} floor fillets are R{runs[0]['r']:g} in the metal "
               f"({sum(r_['s1'] - r_['s0'] for r_ in runs):.1f} mm of wall; {n_pr} probes {lbl}: metal "
               f"{FLOOR_PROBE} mm inside each edge, air {FLOOR_PROBE} mm outside it and at both "
               f"ends of every run); the same cut with each fillet taken out fails all "
               f"{len(runs)}, as it must")

    # ---- 12. the rear art, where it is the shell's only hand ----------------------------
    # Since 2026-11-15 the inside of every shell is its own mirror image top for bottom (the two
    # short edges are cut alike), so a shell with no rear art has no hand at all, and the one
    # with the medallion has its hand THERE and nowhere else. Until that day nothing read the
    # lettering -- the tabs told the hand, and [J] held the tabs. Two measurements:
    #   WHERE: the standing islands of the coin, sectioned through the proud face, against
    #     medallion.geometry() carried through fit_rules.board_geom() -- the frame every other
    #     section here uses. A shell written in the wrong hand has them reflected top for bottom.
    #   WHICH WAY ROUND: the monogram, looked at as a person holding the card looks at its back
    #     (the part turned over about its long axis), against the same letters as the font draws
    #     them. This one owes medallion.py nothing: it is glyphs.py's outline and three islands.
    print("[L] the rear art (sectioned)")
    pre = len(_ERRORS)
    if fr.shell_has_hand(vname) is None:
        note("no rear art on this variant, and the cavity is its own mirror image top for bottom "
             "(check_consistency [8]): this shell has NO HAND -- there is no wrong one to cut it "
             "in. scripts/handedness_drc.py [E] holds that the solid is its own reflection")
    elif v["border_h"] <= 0:
        err("fit_rules.shell_has_hand() names rear art on a variant with no back face")
    else:
        import os as _os
        import shapely.affinity as _aff
        for _p in (str(ROOT / "enclosure"), str(ROOT / "scripts")):
            if _p not in sys.path:
                sys.path.insert(0, _p)
        import medallion as _md
        from glyphs import outline as _outline
        _fd = _os.environ.get("MAKER_FONT_DIR") or str(ROOT / "enclosure" / "fonts")
        _fr_, _fb_ = _os.path.join(_fd, "JetBrainsMono-Regular.ttf"), _os.path.join(_fd, "JetBrainsMono-Bold.ttf")

        def _text_at(txt, lx, cy_, cap, font):
            # medallion.geometry()'s text contract: left edge at lx, centred on cy_, cap high
            g = _outline(txt, font)
            if g is None or g.is_empty:
                return None
            x0, y0, x1, y1 = g.bounds
            g = _aff.scale(g, xfact=cap / (y1 - y0), yfact=cap / (y1 - y0), origin=(x0, y0))
            x0, y0, x1, y1 = g.bounds
            return _aff.translate(g, lx - x0, cy_ - (y0 + y1) / 2.0)

        mg = _md.geometry(_text_at, _fr_, _fb_)
        zb = -BACK_CUT_FRAC * v["border_h"]
        art = section(shell, zb, trimesh)
        inner = mg["disc"].buffer(-0.05)
        got, want = art.intersection(inner), mg["standing"].intersection(inner)
        off = got.symmetric_difference(want).buffer(-ART_ERODE).area
        flip = _aff.scale(art, xfact=1.0, yfact=-1.0, origin=(0.0, H / 2.0)).intersection(inner)
        off_flip = flip.symmetric_difference(want).buffer(-ART_ERODE).area
        if want.area < 10.0:
            err(f"medallion.geometry() returns {want.area:.2f} mm2 of standing art -- nothing to read")
        elif off > ART_OFF_MAX:
            err(f"the rear art in the metal is not where medallion.geometry() puts it: {off:.3f} mm2 "
                f"of the standing islands differ (z {zb:.3f}), against {off_flip:.3f} with the shell "
                f"reflected top for bottom"
                + (" -- THE FILE IS WRITTEN IN THE WRONG HAND" if off_flip <= ART_OFF_MAX else ""))
        if off_flip < ART_TELL:
            err(f"SELF-TEST: the rear art reflected top for bottom differs from the art as laid out "
                f"by only {off_flip:.3f} mm2 -- it does not tell this shell's hand, and it is the "
                f"only thing that does")
        # ...and which way round it reads. The back as a person sees it: x mirrored, y as drawn.
        hoop = _Pt(_md.CX, mg["cy"]).buffer(_md.HOOP[0] - 0.2, quad_segs=64)
        isl = art.intersection(hoop)
        tall = [g for g in getattr(isl, "geoms", [isl])
                if g.geom_type == "Polygon" and g.bounds[3] - g.bounds[1] > 0.6 * _md.DIAL[0][1]]
        scores = None
        if len(tall) != len(_md.DIAL_MONOGRAM):
            err(f"{len(tall)} tall islands inside the coin's hoop, where the monogram "
                f"{_md.DIAL_MONOGRAM!r} has {len(_md.DIAL_MONOGRAM)} letters -- nothing to read it from")
        else:
            def _unit(g):
                x0, y0, x1, y1 = g.bounds
                return _aff.scale(_aff.translate(g, -x0, -y0), xfact=1.0 / (x1 - x0), yfact=1.0 / (y1 - y0), origin=(0, 0))
            seen = _aff.affine_transform(_uu(tall), [-1.0, 0.0, 0.0, -1.0, W, 0.0])
            ref = _unit(_outline(_md.DIAL_MONOGRAM, _fb_))
            iou = lambda g: (lambda a: a.intersection(ref).area / a.union(ref).area)(_unit(g))
            scores = (iou(seen),
                      iou(_aff.scale(seen, xfact=-1.0, yfact=1.0)),
                      iou(_aff.scale(seen, xfact=1.0, yfact=-1.0)),
                      iou(_aff.scale(seen, xfact=-1.0, yfact=-1.0)))
            if scores[0] < ART_READS:
                err(f"the monogram does not read {_md.DIAL_MONOGRAM!r} from the back: it matches "
                    f"the font's own letters {scores[0]:.3f} as seen, {scores[1]:.3f} mirrored left "
                    f"for right, {scores[2]:.3f} top for bottom, {scores[3]:.3f} turned half a turn "
                    f"(needs {ART_READS})")
            if max(scores[1:]) > ART_MISREADS:
                err(f"SELF-TEST: the monogram reads as well mirrored as it does the right way round "
                    f"({max(scores[1:]):.3f} against {scores[0]:.3f}) -- these letters cannot tell "
                    f"which way the art reads")
        # ...and the reeded ribs, which are rear art too (2026-11-16). The second outside review
        # found one of the 38 a 0.58 mm shorter than its three counterparts -- in the metal, on
        # every max shell since the blends went onto the back, with this check reading only the
        # coin. Two measurements on the same section: the ribs that stand in the valleys against
        # fit_rules.fin_ribs(), and against their own reflections. The mounts are mirrored about
        # both centre lines and the rib grid is anchored on them, so the ribs have no hand: a
        # shell written in the wrong hand passes this, and one with a rib of its own does not.
        rib_txt = ""
        if v.get("fins"):
            from shapely.geometry import box as _boxL
            valley = fr.fin_region().buffer(-0.05)
            want_r = _uu(fr.fin_ribs()).intersection(valley)
            got_r = art.intersection(valley)
            _body = lambda g: g.buffer(-ART_ERODE).area
            _tb = lambda g: _aff.scale(g, xfact=1.0, yfact=-1.0, origin=(0.0, H / 2.0))
            _lr = lambda g: _aff.scale(g, xfact=-1.0, yfact=1.0, origin=(W / 2.0, 0.0))
            rib_off = _body(got_r.symmetric_difference(want_r))
            rib_tb = _body(got_r.symmetric_difference(_tb(got_r)))
            rib_lr = _body(got_r.symmetric_difference(_lr(got_r)))
            if want_r.area < 100.0:
                err(f"fit_rules.fin_ribs() returns {want_r.area:.1f} mm2 of rib on a variant with "
                    f"reeded fields -- nothing to read")
            elif rib_off > ART_OFF_MAX:
                err(f"the reeded ribs in the metal are not the ribs fit_rules.fin_ribs() lays out: "
                    f"{rib_off:.3f} mm2 with body differs (z {zb:.3f})")
            if max(rib_tb, rib_lr) > ART_OFF_MAX:
                err(f"the reeded ribs in the metal are not their own mirror image: {rib_tb:.3f} mm2 "
                    f"with body differs top for bottom and {rib_lr:.3f} left for right -- a rib is "
                    f"longer or shorter than its counterparts")
            # canary: the defect itself, one outermost rib 0.58 mm short at its east end
            _r0 = min(fr.fin_ribs(), key=lambda r_: (round(r_.centroid.y, 1), -r_.bounds[2]))
            _cut = got_r.difference(_boxL(_r0.bounds[2] - 0.58, _r0.bounds[1] - 0.05,
                                          _r0.bounds[2] + 0.05, _r0.bounds[3] + 0.05))
            if _body(_cut.symmetric_difference(_tb(_cut))) <= ART_OFF_MAX:
                err("SELF-TEST: the ribs with one outermost rib cut 0.58 mm short still read as "
                    "their own mirror image top for bottom -- the test above cannot fail")
            rib_txt = (f"; its {len(fr.fin_ribs())} reeded ribs are the ones laid out "
                       f"({rib_off:.4f} mm2 of {want_r.area:.0f} off) and their own mirror images "
                       f"({rib_tb:.4f} top for bottom, {rib_lr:.4f} left for right; one cut 0.58 "
                       f"short is seen)")
        if len(_ERRORS) == pre:
            ok(f"the rear art is in the metal where medallion.geometry() puts it "
               f"({off:.4f} mm2 of {want.area:.1f} off; reflected top for bottom, as a shell "
               f"written in the wrong hand would have it, {off_flip:.1f}), and its monogram reads "
               f"{_md.DIAL_MONOGRAM!r} from the back ({scores[0]:.3f} against the font's letters; "
               f"{scores[1]:.3f} / {scores[2]:.3f} / {scores[3]:.3f} mirrored left for right, top "
               f"for bottom, turned half a turn) -- this shell's hand is its rear art, and this "
               f"is the gate that holds it" + rib_txt)

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
