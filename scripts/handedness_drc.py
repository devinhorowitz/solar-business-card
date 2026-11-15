#!/usr/bin/env python3
"""handedness_drc.py -- which HAND are the emitted solids in?  (tier 5 of the solid gates)

Every other gate here reads a solid the way the generators write it. check_mesh.py takes
each file on its own; interference_drc.py and assembly_drc.py set it against the board
through fit_rules.file_xy(), the same statement of the frame the writers use. That makes
them strong tests that shell, brace and board AGREE under the mapping, and no test at all
that the mapping is the real one. Until 2026-11-13 every STEP and STL in enclosure/ was the
MIRROR IMAGE of its part -- modelled in board coordinates (X right, Y down, Z to the card's
front: a left-handed triad) and written as modelled -- and every one of them passed
everything, on every run. fit_rules, THE FILE FRAME, has the story.

What saw it owed this repo nothing: the committed solids set against KiCad's own STEP export
of the populated board, in a CAD program nothing here uses. This is that measurement, in CI.

WHAT IT MEASURES

  KiCad's export   `kicad-cli pcb export step` of the committed board, 3D models and all,
                   from the pinned image. Right-handed by KiCad's construction, and every
                   position in it is KiCad's own reading of the footprints: nothing of
                   board_parts, fit_rules or part_heights went into it.
  the solids       the emitted brace STEPs and shell STLs, placed in KiCad's frame by a
                   TRANSLATION AND NOTHING ELSE -- onto the card's centre as found from the
                   exported substrate, the brace's top and the shell's seat at the board's
                   underside. No reflection is on offer, so a file written in the wrong
                   hand stays in the wrong hand.

  [K]  the export is a board: one substrate the card's size, parts on both faces.
  [P]  board_parts reads the board KiCad exports: every B-side body KiCad places is exactly
       one board_parts body, in the same place, and none is left over either way. That is
       the reader every generator and every other gate shares, held for the first time
       against something it did not write.
  [M]  fit_rules.file_xy() / board_xy(), the mapping the other gates read solids through,
       is KiCad's frame moved by exactly that translation.
  [B]  each brace against every B-side component solid, by OCC boolean: zero, but for
       PROUD_IN_KICAD. CANARY: the same brace MIRRORED must collide, in both placements
       the mount holes allow.
  [S]  each shell, sectioned through its cavity, against every component's plan outline
       and the bare-pad footprints (no model, so KiCad exports no body for them; board_parts
       reads them, the reader [P] holds to KiCad's placement): no contact. CANARY: its
       mirror image must fit WORSE, in both placements.
  [E]  each STEP against its own STL. [B] reads the braces' STEPs and [S] the shells' STLs,
       but the printer is sent the brace's STL and the machinist the shell's STEP -- so the
       two files of every solid, the pogo plate's included, must be the same solid in the
       same hand: no point of either file's surface may stand off the other's by more than
       a tessellation gives up. CANARY: one of the two REFLECTED must stand well off. (Until
       2026-11-14 the hand was read off the centre of mass in y, which a mirror image
       negates -- and which one design change put 0.0003 mm from zero on the max shell.)
  [T]  the pogo plate against KiCad's export of the PANEL it carries. The panel's two
       tooling holes are asymmetric on purpose; with the plate's outline centred under the
       panel's, a dowel bore must sit under each. CANARY: the plate mirrored must miss.

CALIBRATED on the state it exists to catch. On the solids committed at d060215 the max
brace reads 53.109 mm3 over 34 parts and 493.855 mm3 over 29 in its two placements, and
0.047 mm3 over one part for its mirror image. SolidCraft, on DRH's machine, reported 53.1
over 34, 493.9 over 29 and 0.05 over one.

WHAT IT CANNOT SEE, said plainly so it is not mistaken for total:
  * THE SHELL'S HAND IS TOLD BY A SMALL MARGIN, because the shell is nearly symmetric: its
    mirror image overlaps nothing in one placement and merely stood closer to the parts
    beside the west lip (R16 lost 0.18 mm). [S] scores that over every part in reach,
    prints both hands, and fails unless the mirror image fits worse -- it never passes on
    "no collision" alone. SINCE 2026-11-15 THAT PLACEMENT IS NOT TOLD BY FIT AT ALL: the
    west lip is one width, the steps beside R16 and C24 are gone, and top for bottom the
    cavity is its own mirror image wherever a part stands. [S] now has to SHOW that (see
    SAME_ERODE) before it will accept a mirror image that fits no worse, and says which
    gate holds the hand instead: assembly_drc [J], by the two tabs. In the OTHER placement the mirror image's west lip lands on the bare
    JP1 and TP1 pads (8.857 and 1.616 mm2), and nothing else; KiCad exports no body for a
    footprint without a model, so [S] takes those footprints from board_parts. Until
    2026-11-13 it did not need to: a cap-corner flat on each east mid-span boss made the
    mirror crowd SC1 / SC3 there. The Ø2.0 bores that went in that day (fit_rules.boss_cuts)
    carved that corner away, the mirror stopped crowding anything KiCad exports in that
    placement, and the first CI run read the shells as WRITTEN IN THE WRONG HAND -- with every
    other witness of the hand green. assembly_drc [G] is the stronger
    witness (a mirror-image shell has its lip nick 4 mm from where the board wants it);
    [P] and [M] are what tie that gate's frame to this one's.
  * Bare pads. KiCad's export carries component bodies, not copper, so a lip resting on
    JP1's pads is assembly_drc [F]'s to find.
  * Lettering. Nothing HERE reads the medallion or the plate's labels. The medallion is read
    by assembly_drc [L] since 2026-11-15 -- it had to be: see A SHELL WITH NO HAND below --
    and the plate's labels follow from the solid they are cut into, checked by eye when the
    frame was fixed.
  * A SHELL WITH NO HAND (2026-11-15). With the two short-edge tabs cut alike, the inside of
    every shell is its own mirror image top for bottom, and a shell with no rear art -- lite,
    air -- is its own mirror image altogether: there is no wrong hand to write it in. [S] and
    [E] do not look for a tell on those; they ASSERT there is none (fit_rules.shell_has_hand
    is the expectation, the solid is the measurement). The max shell's hand is its medallion
    and nothing else; this gate cannot see it and says so.

USAGE -- two halves, because KiCad lives in the container and cadquery on the runner:

  python3 scripts/handedness_drc.py --export-board /tmp/board.step --export-panel /tmp/panel.step
                                                                        # needs kicad-cli
  python3 scripts/handedness_drc.py --board-step /tmp/board.step --panel-step /tmp/panel.step
                                                                        # needs cadquery, trimesh

The panel is optional in both (it exists only after scripts/panelize.py has run, as it has
in CI); without it [T] is skipped, out loud, and the plate's hand rests on its row in
check_mesh.py alone -- the one solid whose bounding box is not symmetric in y.

REHEARSING [S] WITHOUT KICAD
    python3 scripts/handedness_drc.py --rehearse
[S]'s verdict alone, board_parts' outlines standing in for KiCad's bodies at part_heights'
heights. It reads the shells in the tree it is run from. It exists because the first
rehearsal was a scratch script with a made-up height in it, and passed what CI refused
(2026-11-15, run 663; see SAME_ERODE). A rehearsal, never the gate.
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "enclosure"))

EPS_MM3 = 1e-3        # an OCC common below this is numerical dust, not a collision
SIZE_TOL = 0.01       # mm: the exported substrate against fit_rules' W x H
PLACE_TOL = 0.30      # mm: how far a KiCad body's centre may sit from its board_parts body's
# The canary's bar. A mirror-image brace collides by tens to hundreds of mm3 over thirty
# parts (see CALIBRATED above); this is far below that and far above anything a right
# brace does.
CANARY_MM3 = 5.0
CANARY_PARTS = 5
# THE SHELL'S HAND, AND WHY IT IS NOT READ OFF THE TIGHTEST GAP. A mirror-image shell does
# not collide in one of its two placements; it only stands closer to the parts its lip was
# cut back for. Measured 2026-11-13 against KiCad's outlines, gap as written / mirrored:
#     R16 0.377 / 0.199     C24 0.399 / 0.353     SC1 0.750 / 0.680     SC2 0.266 / 0.239
#     SC3 0.750 / 0.820     SC4 0.250 / 0.274     U10 0.399 / 0.399
# The tightest gap moves 0.250 -> 0.199, but 0.250 is SC4's datum clearance -- a design
# number that has nothing to do with the hand, and one edit to it would hide the 0.18 mm R16
# loses. So the fit is scored over EVERY part in reach: "crowding" is how far inside REACH
# the metal stands, summed over the parts (0.809 mm as written, 1.036 mirrored). A mirror
# image must crowd the board by at least CROWD_MARGIN more, or overlap it.
# Re-measured in CI 2026-11-13 on the solids with the Ø2.0 boss-corner bores, over KiCad's
# bodies alone: as written crowding 0.223 (R16 0.378, C24 0.399); mirrored as written 0.550
# (R16 0.199); mirrored and turned half a turn 0.000 (nearest SC1 0.549) -- better than the
# shell itself, so the gate called the right hand wrong. That placement's mirror lands on
# the bare JP1 / TP1 pads instead, which KiCad exports no body for, so [S] carries the
# bare-pad footprints too: as written they stand 0.300 off the lip (crowding +0.400 on both
# sides of the comparison), and the half-turn mirror overlaps them, 8.857 and 1.616 mm2.
REACH = 0.5
CROWD_MARGIN = 0.05
# A MIRROR IMAGE THAT IS THE SAME CAVITY (2026-11-15). The west lip was cut to one width that
# day (fit_rules.LIP_ONE_WIDTH -- DRH: "smooth contiguous surfaces"), and the two steps beside
# R16 and C24 that the first placement's verdict rested on went with it. Top to bottom, the
# inside of every shell is now its own mirror image but for the two short-edge tabs, 0.5 mm
# apart in width and more than a millimetre from the nearest part. So in that placement the
# mirror image fits the board exactly as well as the shell does -- and it is right that it
# does: wherever a part stands, it is the same metal.
#
# "Fits no worse" used to be an error without exception, because it meant this gate could not
# see. It still is one, unless the gate can SHOW why: the mirrored sections are laid over the
# sections as written, and if no difference between them with any body to it (SAME_ERODE takes
# off the hairlines two tessellations of one arc leave) comes within REACH of a part, the
# placement is a symmetry of the cavity as the parts meet it. That is reported, with what
# does differ and where, and the hand in that placement is then held by the gate that reads
# the metal in board coordinates: assembly_drc [J], which probes each tab's two tip rounds
# and two roots where the board puts them, through the frame [M] ties to KiCad's here.
# TRIED, not assumed (2026-11-15): each rebuilt shell's STL reflected top for bottom fails
# [J] at twelve probes -- the east side of both tabs, at three levels -- and passes every
# other section of that gate, [G] included: a step 0.5 mm from where the lip table puts it
# is inside the blend allowance [G] gives every step. So ONE gate holds that hand, by half a
# millimetre of tab, and if the two tabs are ever made alike nothing will -- nor need to: the
# lite and air shells would then be their own mirror images, and only the max shell's rear
# art, which nothing here reads, would have a hand left.
# A difference a part COULD feel that fit cannot tell is still the old error.
# IT FIRED THE SAME DAY, AND WAS RIGHT (CI run 663). The floor-to-wall fillets went in with
# each run stopping 0.50 short of the feature at either end. East of each short-edge tab that
# is 0.50 past the tab's own root, and the tabs differ by 0.5 mm -- so those two runs began at
# x 28.423 and 28.923, under the edges of SC2 and SC4. Top for bottom the mirror image then
# differed from the shell by 0.109 mm2 of fillet within REACH of a supercap and crowded the
# board no more (0.917 against 0.916): a difference a part could feel that fit could not
# tell. The cure was in the part, not here: fit_rules.floor_runs() evens every run with its
# twin top for bottom, so the fillets are the same metal in both hands and this placement is
# once more a symmetry of the cavity as the parts meet it.
# WHY IT REACHED CI: the rehearsal of this verdict (below) was a scratch script that gave
# every body with no tabled height -- the four supercaps -- 0.5 mm of height, so the cut
# above the floor never passed through one. --rehearse is that rehearsal with the parts'
# own heights, kept here so that it cannot drift from the verdict it rehearses.
# AND THEN THE TABS WERE CUT ALIKE (later the same day, DRH: "yes" to the same width). The
# 1.93 mm2 at the tabs is gone, and with it the last thing [J] held: top for bottom the
# sections of a shell and of its mirror image are now the same sections. So the acceptable
# answers in that placement are two -- fit tells them apart, or they differ by NOTHING -- and
# "differs, but only where no part stands" has become an error again, because no gate is left
# that holds a hand living there (name one if you add such a feature). What the hand then IS
# comes from fit_rules.shell_has_hand(): none at all for a shell with no rear art, which [E]
# proves on the whole solid; the rear art for the max shell, which assembly_drc [L] reads.
SAME_ERODE = 0.03
# --rehearse: how much lower than its tabled height a body is taken to hang. KiCad's bodies
# hang a little lower than part_heights' figures (a model seats on its pads, not on the
# copper): on the max shell the cut above the floor, 1.706 under the board, passes through
# KiCad's supercaps (run 663) and would miss a body of exactly SUPERCAP_H 1.70. A rehearsal
# has to be the stricter of the two.
REHEARSE_DEEPER = 0.10

# [E]: a STEP against its STL. Two questions, two measurements.
# SAME HAND, by SURFACES: the farthest any vertex of either file's surface stands from the
# other file's surface. The STEP is tessellated finer than any STL here is written
# (SURF_TESS against export tolerances of 0.03 and 0.04), so as written that distance is
# what the meshes give up on an arc -- measured 0.0048 mm on the shells and 0.0093 on the
# plate, 2026-11-14 -- and can never exceed the coarser tolerance: SURF_SAME. With one of
# the two REFLECTED it is the size of whatever the solid has on one side and not the other:
# 0.43 mm on the lite and air shells (the strip of lip between the two supercaps on a short
# edge, which the caps' own positions end 0.5 mm farther east at the north than at the
# south), 0.60 on the max shell (the rear art), 1.2 and 2.8 on the braces, 88.9 on the
# plate. SURF_TELL is the least that must be for the comparison to count as able to tell a
# hand.
# SINCE 2026-11-15 TWO OF THE SIX HAVE NO HAND TO TELL. The tabs were cut alike, and the lite
# and air shells measure 0.010 mm off their own reflection (the east wall's blends differ by
# that: the cut outline's own simplify). A solid that is its own mirror image cannot be in the
# wrong hand, and asking it for SURF_TELL would be asking it to be worse. So for a shell that
# fit_rules.shell_has_hand() declares handless the bar turns round: reflected, it must stand
# within SURF_SAME of itself -- and if it does not, it has grown a hand nobody declared, which
# is an error that names itself. The max shell (0.600), the braces and the plate are held to
# SURF_TELL as before.
# WHY NOT THE CENTRE OF MASS, which is what this read until 2026-11-14 (y alone, to 0.001,
# with a bar of 0.003 on how far opposite hands must disagree). A reflection negates it, so
# it tells the hand only as well as the solid is lopsided -- and it is a SUM, so what is on
# one side can be balanced by something else on the other. The shells' stood 0.006 to
# 0.023 mm off the centre line when that bar was set. By `5a36638` the max shell's was at
# 0.0029 and the lite shell's at 0.0053; the boss blends and corner webs then moved them
# to 0.0003 and 0.0024: the self-test went red on a shell in the right hand, and the lite
# shell was passing by 0.002. A distance between surfaces has no such cancellation: it is
# zero only for a solid that IS its own mirror image, and then there is no hand to get
# wrong.
# SAME SOLID, by the centre of mass after all, in all three coordinates and loosely: a
# second witness of a different kind, for what a vertex cannot see (a mesh with the right
# skin and a void inside it). Measured up to 0.0016 mm apart, on the plate's lettering.
SURF_TESS = 0.01
SURF_SAME = 0.05
SURF_TELL = 0.20
COM_SAME = 0.01

# [T]: a tooling hole is found by its size in KiCad's export, and a dowel bore under it by
# position. The plate's bores are modelled on the holes' own coordinates, so a plate in the
# right hand registers to the micron and a mirrored one misses by tens of millimetres.
TOOLING_D = 1.5
TOOLING_TOL = 0.05

# refdes -> (most it may reach into a brace, mm3, and why). KiCad's model of the part is
# what collides here, not the part. The ledger audits itself, interference_drc's rule: an
# entry that excuses nothing on any brace FAILS the gate.
PROUD_IN_KICAD = {
    "L2": (0.10, "KiCad's generic L_1008 body is 1.20 tall and its export seats every part "
                 "0.040 off the board: 1.24 against a 1.22 pocket. The part fitted is a "
                 "DFE252010F, 1.00 max -- part_heights.MODEL_NOTES waives that model by "
                 "name -- so the real margin is +0.18. Measured 0.047 mm3 on the max brace."),
}

_ERRORS, _NOTES = [], []


def err(m):
    _ERRORS.append(m); print(f"  ERROR   {m}")


def ok(m):
    print(f"  ok      {m}")


def note(m):
    _NOTES.append(m); print(f"  note    {m}")


# ---- half one: KiCad's export (runs where kicad-cli is) ---------------------------------
def export_board(out):
    """KiCad's own STEP of the populated board -> `out`. Fails if any 3D model did not
    resolve: a body KiCad could not place is a body this gate cannot see."""
    import render                       # scripts/render.py -- where the 3D models are HERE
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, KICAD10_3DMODEL_DIR=render.stock_model_dir())
    # --no-dnp: the board AS ASSEMBLED, the same reading the populated renders take. No dnp
    # footprint carries a model today (render.py prints the set); if one ever does, [P]
    # says so, because board_parts will have a body KiCad was told to leave out.
    cmd = ["kicad-cli", "pcb", "export", "step", "--no-dnp", "-f", "-o", str(out), str(render.BOARD)]
    try:
        r = subprocess.run(cmd, env=env, capture_output=True, text=True)
    except FileNotFoundError:
        print("handedness_drc: kicad-cli is not on PATH -- run this half inside the pinned "
              "KiCad image (see .github/workflows/kibot.yml)")
        return 1
    log = (r.stdout or "") + (r.stderr or "")
    missing = [ln.strip() for ln in log.splitlines() if "Could not add 3D model" in ln]
    for ln in log.splitlines():
        if ln.strip() and "Font '" not in ln:
            print("  kicad-cli: " + ln.strip())
    if r.returncode or not out.exists():
        print(f"handedness_drc: kicad-cli exited {r.returncode} and wrote "
              f"{'nothing' if not out.exists() else out.name}")
        return 1
    if missing:
        print(f"handedness_drc: {len(missing)} 3D model(s) did not resolve, so their bodies "
              f"are missing from the export -- refusing to gate on a board with holes in it")
        return 1
    print(f"handedness_drc: wrote {out} ({out.stat().st_size:,} bytes), every 3D model resolved")
    return 0


def export_panel(out):
    """KiCad's own STEP of the PANEL's substrate -> `out`. Board only: [T] wants its holes."""
    import render
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    if not render.PANEL.exists():
        print(f"handedness_drc: {render.PANEL.relative_to(ROOT)} does not exist -- "
              f"scripts/panelize.py builds it (it is not committed)")
        return 1
    cmd = ["kicad-cli", "pcb", "export", "step", "--board-only", "-f", "-o", str(out), str(render.PANEL)]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True)
    except FileNotFoundError:
        print("handedness_drc: kicad-cli is not on PATH -- run this half inside the pinned KiCad image")
        return 1
    if r.returncode or not out.exists():
        print((r.stdout or "") + (r.stderr or ""))
        print(f"handedness_drc: kicad-cli exited {r.returncode} exporting the panel")
        return 1
    print(f"handedness_drc: wrote {out} ({out.stat().st_size:,} bytes), the panel's substrate")
    return 0


# ---- half two: the measurement ----------------------------------------------------------
def load_step(path):
    import cadquery as cq
    vals = cq.importers.importStep(str(path)).vals()
    return vals[0] if len(vals) == 1 else cq.Compound.makeCompound(vals)


def silhouette(solid):
    """The plan (XY) outline of an OCC solid, as shapely geometry in the solid's own frame."""
    import numpy as np
    import shapely
    verts, tris = solid.tessellate(0.02)
    pts = np.array([(v.x, v.y) for v in verts])
    polys = shapely.polygons(pts[np.array(tris)])
    return shapely.union_all(polys[shapely.area(polys) > 1e-9])


def round_holes(mesh, z, trimesh):
    """[(x, y, diameter)] -- every closed empty region of `mesh`'s section at height z, with
    the diameter of the circle of the same area, plus the section's own bounding box."""
    import numpy as np
    import shapely
    from shapely.ops import polygonize
    segs = trimesh.intersections.mesh_plane(mesh, [0.0, 0.0, 1.0], [0.0, 0.0, z])
    if len(segs) == 0:
        return [], None
    xy = segs[:, :, :2].reshape(-1, 2)
    bbox = (xy[:, 0].min(), xy[:, 1].min(), xy[:, 0].max(), xy[:, 1].max())
    faces = [f for f in polygonize(shapely.union_all(shapely.linestrings(segs[:, :, :2]), grid_size=1e-5))
             if f.area > 1e-9]
    probe = np.array([[*f.representative_point().coords[0], z] for f in faces])
    return [(f.centroid.x, f.centroid.y, 2.0 * (f.area / np.pi) ** 0.5)
            for f, solid in zip(faces, mesh.contains(probe)) if not solid], bbox


def off_surface(points, mesh, trimesh):
    """How far each of `points` stands from `mesh`'s surface, mm. A point more than SURF_TELL
    outside the mesh's bounding box is not searched for: its distance to the box is returned
    instead, which is never more than its distance to the surface -- so the figure is exact
    wherever it is small, and a lower bound where it is already past every bar. (The plate
    and its mirror image do not overlap at all; searching that is a minute spent on 88.9.)"""
    import numpy as np
    points = np.asarray(points, dtype=float)
    lo, hi = mesh.bounds
    d = np.linalg.norm(np.maximum(np.maximum(lo - points, points - hi), 0.0), axis=1)
    near = d <= SURF_TELL
    if near.any():
        d[near] = trimesh.proximity.closest_point(mesh, points[near])[1]
    if not np.isfinite(d).all():
        # a NaN compares False against every bar in [E]: it would PASS. Refuse instead.
        raise ValueError(f"{int((~np.isfinite(d)).sum())} of {len(d)} distances to a surface "
                         f"came back undefined -- a triangle with no area is still in the mesh")
    return d


def with_area(mesh, trimesh):
    """`mesh` without its zero-area triangles. Nothing can stand off a triangle that has no
    surface, and trimesh divides by a zero edge length looking for the closest point on one.
    Each shell's STL carries one such triangle pair: the rim pinch check_mesh.py ledgers."""
    keep = mesh.area_faces > 1e-12
    return mesh if keep.all() else trimesh.Trimesh(mesh.vertices, mesh.faces[keep], process=False)


def surface_gaps(solid, stl, trimesh):
    """(as written, reflected): the farthest any vertex of either surface -- `solid` (OCC,
    tessellated here) or `stl` (a mesh) -- stands from the other surface; and the same after
    one of the two has been reflected in y, which is the reflection export_solid() makes."""
    import numpy as np
    verts, tris = solid.tessellate(SURF_TESS, 0.1)
    pts = np.array([(v.x, v.y, v.z) for v in verts])
    # process=False: this mesh is only ever measured TO, triangle by triangle; welding its
    # vertices would be work for nothing
    of_step = with_area(trimesh.Trimesh(pts, np.array(tris), process=False), trimesh)
    of_stl, stl = np.asarray(stl.vertices), with_area(stl, trimesh)
    return tuple(max(off_surface(pts * s, stl, trimesh).max(),
                     off_surface(of_stl * s, of_step, trimesh).max())
                 for s in (np.array([1.0, 1.0, 1.0]), np.array([1.0, -1.0, 1.0])))


def step_vs_stl(trimesh):
    """[E] -- every emitted solid's STEP against its own STL. Needs neither KiCad export."""
    import fit_rules as fr
    pre, pairs, rows, handless = len(_ERRORS), [], [], []
    no_hand = set()                              # labels fit_rules declares to have no hand
    for vname, v in fr.VARIANTS.items():
        pairs.append((f"{vname} shell", ROOT / "enclosure" / v["shell_name"]))
        if fr.shell_has_hand(vname) is None:
            no_hand.add(f"{vname} shell")
        if v["brace_name"]:
            pairs.append((f"{vname} brace", ROOT / "enclosure" / "brace" / v["brace_name"]))
    pairs.append(("pogo plate", ROOT / "enclosure" / "solar-glow-drh-pogo-testplate"))
    for label, stem in pairs:
        step, stl = Path(str(stem) + ".step"), Path(str(stem) + ".stl")
        if not (step.exists() and stl.exists()):
            err(f"{label}: {stem.name}.step / .stl are not both there -- CI emits them together")
            continue
        solid, mesh = load_step(step), trimesh.load(stl, force="mesh")
        written, mirrored = surface_gaps(solid, mesh, trimesh)
        c, m = solid.Center(), mesh.center_mass
        com = max(abs(c.x - m[0]), abs(c.y - m[1]), abs(c.z - m[2]))
        print(f"          {label}: surfaces {written:.4f} mm apart at most as written, "
              f"{mirrored:.3f} with one reflected; centres of mass {com:.4f} apart")
        if written > SURF_SAME and mirrored <= SURF_SAME:
            err(f"{label}: the STEP's surface and the STL's stand {written:.3f} mm apart, and "
                f"within {mirrored:.4f} once one of them is reflected -- THE TWO FILES ARE IN "
                f"OPPOSITE HANDS")
        elif written > SURF_SAME:
            err(f"{label}: the STEP's surface and the STL's stand {written:.3f} mm apart "
                f"({mirrored:.3f} with one reflected; an STL gives up {SURF_SAME} at most) -- "
                f"they are not the same solid")
        elif label in no_hand:
            # A SHELL WITH NO HAND is held to BEING its own reflection, which is a claim a
            # measurement can refuse: the day something on it differs top for bottom, this
            # goes red and asks what holds the hand it has grown.
            if mirrored > SURF_SAME:
                err(f"{label}: fit_rules.shell_has_hand() says it has no hand, and reflected its "
                    f"surface stands {mirrored:.3f} mm off itself (a solid that is its own mirror "
                    f"image gives up {SURF_SAME} at most) -- it HAS one. Either make the feature "
                    f"the same in both hands, or declare the hand and name the gate that holds it")
            elif com > COM_SAME:
                err(f"{label}: the two surfaces agree but the centres of mass are {com:.4f} mm "
                    f"apart -- they are not the same solid")
            else:
                handless.append((mirrored, written, label))
        elif mirrored < SURF_TELL:
            err(f"SELF-TEST: {label}: reflected, its surface stands only {mirrored:.4f} mm off "
                f"itself at most (the bar is {SURF_TELL}) -- the solid is too nearly its own "
                f"mirror image for this to tell a STEP and an STL in opposite hands apart")
        elif com > COM_SAME:
            err(f"{label}: the two surfaces agree but the centres of mass are {com:.4f} mm "
                f"apart (({c.x:.4f}, {c.y:.4f}, {c.z:.4f}) against ({m[0]:.4f}, {m[1]:.4f}, "
                f"{m[2]:.4f})) -- they are not the same solid")
        else:
            rows.append((mirrored, written, label))
    if len(_ERRORS) == pre:
        least = min(rows)
        ok(f"all {len(pairs)} STEP/STL pairs are one solid: no vertex of either "
           f"file stands more than {max(r[1] for r in rows + handless):.4f} mm off the other's "
           f"surface (an STL may give up {SURF_SAME}). {len(rows)} have a hand and are in the same "
           f"one: reflected, the least any of them stands off is {least[0]:.3f} mm, the "
           f"{least[2]} (the bar is {SURF_TELL})"
           + (f". {len(handless)} have NONE, as fit_rules.shell_has_hand() declares -- "
              + ", ".join(f"the {lbl} ({mir:.4f} mm off its own reflection at most)"
                          for mir, _w, lbl in sorted(handless, key=lambda r: r[2]))
              + f" -- each is its own mirror image to within what an STL gives up, so there is "
                f"no wrong hand to write it in" if handless else ""))


def felt_difference(cuts_a, cuts_b, bodies):
    """(area mm2, where) -- the part of the difference between two placements of a shell,
    [(z, section)] each, that a body could meet: what is left of their symmetric difference
    once SAME_ERODE has taken the tessellation's hairlines off, within REACH of the outline of
    any body that cut passes through. Also returns the whole difference's area and extent, so
    the caller can say what the two placements DO differ by."""
    from shapely.ops import unary_union
    felt, where, whole, box_ = 0.0, None, 0.0, None
    for (z, a), (_z, b) in zip(cuts_a, cuts_b):
        d = a.symmetric_difference(b).buffer(-SAME_ERODE).buffer(SAME_ERODE)
        if d.is_empty:
            continue
        if d.area > whole:
            whole, box_ = d.area, d.bounds
        near = [o.buffer(REACH) for _ref, o, zlo, zhi in bodies if zlo < z < zhi]
        if not near:
            continue
        f = d.intersection(unary_union(near))
        if f.area > felt:
            felt, where = f.area, f.representative_point()
    return felt, where, whole, box_


def fit(metal_cuts, bodies):
    """How a shell, as [(z, section)] in KiCad's frame, sits against [(ref, outline, zlo, zhi)]:
    (overlap mm2, tightest gap mm, its ref, crowding mm) over every cut that passes through
    each body. Crowding is sum over the parts of max(0, REACH - that part's nearest gap)."""
    overlap, gap, who, crowd = 0.0, None, None, 0.0
    for ref, outline, zlo, zhi in bodies:
        mine = None
        for z, metal in metal_cuts:
            if not (zlo < z < zhi):
                continue
            a = metal.intersection(outline).area
            if a > 1e-3:
                overlap += a
                mine = 0.0
            else:
                d = metal.distance(outline)
                mine = d if mine is None else min(mine, d)
        if mine is None:
            continue
        crowd += max(0.0, REACH - mine)
        if gap is None or mine < gap:
            gap, who = mine, ref
    return overlap, gap, who, crowd


def shell_hand(vname, raw, outlines, dz, kcx, kcy, section_floor):
    """[S] for one shell: `raw` is [(z, section)] in the shell's own file frame, `outlines`
    [(ref, outline, zlo, zhi)] in KiCad's; the shell is placed by (kcx, kcy, dz) alone, as
    written and as each of its two mirror images. Split out of check() so that the verdict
    can be exercised without KiCad's export (there is no kicad-cli outside the pinned image):
    it reads nothing but its arguments."""
    from shapely.affinity import scale, translate
    place = lambda sx, sy: [(z + dz, translate(scale(m, sx, sy, origin=(0, 0)), kcx, kcy)) for z, m in raw]
    pre = len(_ERRORS)
    o_r, g_r, w_r, c_r = fit(place(1.0, 1.0), outlines)
    if o_r > 0.0:
        err(f"the {vname} shell as written has {o_r:.3f} mm2 of metal inside KiCad's part "
            f"bodies -- it does not fit the board KiCad exports")
    elif g_r is None:
        err(f"no cut through the {vname} shell passes through any of KiCad's parts -- "
            f"nothing was measured")
    elif g_r < section_floor:
        err(f"the {vname} shell as written stands {g_r:.3f} mm from {w_r} in KiCad's "
            f"export -- inside the {section_floor} a section resolves, i.e. contact")
    told, same = 0, []
    for label, (sx, sy) in (("as written", (1.0, -1.0)), ("turned half a turn", (-1.0, 1.0))):
        o_m, g_m, w_m, c_m = fit(place(sx, sy), outlines)
        how = (f"{o_m:.3f} mm2 of metal inside parts" if o_m > 0.0 else
               f"tightest {w_m} at {g_m:.3f} mm, crowding {c_m:.3f} mm")
        print(f"          its mirror image, {label}: {how}")
        if o_r > 0.0 or g_r is None:
            continue                                          # already an error
        if o_m > 0.0 or c_m >= c_r + CROWD_MARGIN:
            told += 1
            continue                                          # told apart
        if c_m <= c_r - CROWD_MARGIN:
            err(f"the {vname} shell as written crowds the board KiCad exports MORE than "
                f"its own mirror image does ({c_r:.3f} mm against {c_m:.3f}, {label}; "
                f"tightest {w_r} at {g_r:.3f} against {w_m} at {g_m:.3f}) -- THE FILE IS "
                f"WRITTEN IN THE WRONG HAND")
            continue
        # fits the same. Either this gate cannot see, or there is nothing for it to see:
        # show which (SAME_ERODE, above)
        felt, at, whole, wbox = felt_difference(place(1.0, 1.0), place(sx, sy), outlines)
        if felt > 1e-3:
            err(f"SELF-TEST: the {vname} shell's MIRROR IMAGE, {label}, fits KiCad's board "
                f"no worse than the shell does ({how}, against crowding {c_r:.3f} as "
                f"written; a mirror image must overlap or crowd by {CROWD_MARGIN} more) "
                f"though {felt:.3f} mm2 of its metal within {REACH} of a part is not where "
                f"the shell's is (near KiCad ({at.x:.2f}, {at.y:.2f})) -- this cannot tell "
                f"the shell's hand, and 'no collision' is not evidence")
            continue
        if wbox is not None:
            err(f"the {vname} shell's MIRROR IMAGE, {label}, fits KiCad's board no worse than "
                f"the shell does and differs from it by {whole:.2f} mm2 at most on a level, all "
                f"of it more than {REACH} from every part (within KiCad x {wbox[0]:.1f}.."
                f"{wbox[2]:.1f}, y {wbox[1]:.1f}..{wbox[3]:.1f}) -- so the cavity has a hand that "
                f"fit cannot tell, and since the two tabs were cut alike no gate holds one that "
                f"lives where no part stands. Make the feature the same in both hands, or name "
                f"the gate that reads it (SAME_ERODE, above)")
            continue
        print(f"          ...and that mirror image IS this cavity: at every level the two "
              f"sections differ by nothing a section can see")
        same.append(label)
    if told == 0 and o_r == 0.0 and g_r is not None and len(_ERRORS) == pre:
        err(f"SELF-TEST: neither mirror image of the {vname} shell fits KiCad's board worse "
            f"than the shell does -- nothing here tells its hand at all")
    if len(_ERRORS) == pre:
        import fit_rules as fr
        hand = fr.shell_has_hand(vname)
        ok(f"the {vname} shell as written clears every part KiCad exports (tightest "
           f"{w_r} at {g_r:.3f} mm, crowding {c_r:.3f} mm inside {REACH}); its mirror "
           f"image fits worse in {told} of the 2 placements"
           + ("".join(f". The mirror image {label} is the same cavity at every level: the "
                      f"inside of this shell has no hand in that placement"
                      for label in same))
           + ("" if not same else
              (". Nor has the shell any other (fit_rules.shell_has_hand): [E] holds that the "
               "whole solid is its own reflection, so it cannot be written in the wrong hand"
               if hand is None else
               f". Its hand is its {hand}, which this gate cannot see: assembly_drc [L] reads it")))


def rehearse():
    """[S]'s verdict WITHOUT KiCad's export, for a machine with no kicad-cli: board_parts'
    outlines stand in for KiCad's bodies (the reader [P] ties to KiCad's placement in CI),
    each as tall as part_heights says and REHEARSE_DEEPER more. It reads the shells in the
    tree it is run from, like every mesh gate -- after a change to the enclosure, point a copy
    of the tree at freshly built solids (CLAUDE.md). A REHEARSAL: the merge run is the gate.
    It says nothing about [P], [B], [E] or [T]."""
    import trimesh
    import fit_rules as fr
    import board_parts as bp
    import part_heights as ph
    import assembly_drc as adrc
    from shapely.affinity import affine_transform
    from shapely.geometry import Point

    # board -> file, as one affine map; held to fit_rules.file_xy(), the one statement of it
    to_file = lambda g: affine_transform(g, [1.0, 0.0, 0.0, -1.0, -fr.W / 2.0, fr.H / 2.0])
    if tuple(to_file(Point(3.0, 7.0)).coords[0]) != tuple(fr.file_xy(3.0, 7.0)):
        err("SELF-TEST: the rehearsal's board-to-file mapping is not fit_rules.file_xy()")
    print("handedness REHEARSAL -- [S] only, board_parts' outlines standing in for KiCad's bodies")
    for vname, v in fr.VARIANTS.items():
        print(f"[S] {vname}: shell vs board_parts' outlines (rehearsal)")
        path = ROOT / "enclosure" / (v["shell_name"] + ".stl")
        if not path.exists():
            err(f"missing {path.relative_to(ROOT)} -- CI emits it")
            continue
        shell = trimesh.load(path)
        seat = v["floor"] + v["cavity"]
        outlines = []
        for ref, poly, h, src in bp.parts("B"):
            if h is None and src == "model":
                h = ph.SUPERCAP_H if ref.startswith("SC") else None
            if h is None:
                err(f"{ref}: no height to rehearse with (part_heights) -- a body with a made-up "
                    f"height is how the 2026-11-15 rehearsal passed what CI refused")
                continue
            deeper = REHEARSE_DEEPER if src == "model" else 0.0
            outlines.append((ref, to_file(poly), seat - h - deeper, seat))
        raw = [(z, adrc.section_file(shell, z, trimesh)) for _lbl, z in adrc.cavity_levels(v["floor"], v["cavity"])]
        if any(m.is_empty for _z, m in raw):
            err(f"the {vname} shell has no material at one of its cavity cuts -- nothing to compare")
            continue
        low = min(z for z, _m in raw)
        through = [ref for ref, _o, zlo, zhi in outlines if zlo < low < zhi]
        if v["floor"] > 0 and not any(r.startswith("SC") for r in through):
            err(f"SELF-TEST: the {vname} shell's cut above the floor passes through no supercap "
                f"-- the rehearsal is not looking where the floor fillets are")
        shell_hand(vname, raw, outlines, 0.0, 0.0, 0.0, adrc.SECTION_FLOOR)
    print(f"== handedness rehearsal: {len(_ERRORS)} error(s) -- [S] only; the merge run is the gate ==")
    return 1 if _ERRORS else 0


def check(board_step, panel_step=None):
    try:
        import numpy as np                                        # noqa: F401
        import trimesh
        from shapely.affinity import scale, translate
        from shapely.geometry import box
        import assembly_drc as adrc
        import board_parts as bp
        import fit_rules as fr
    except Exception as e:                                        # noqa: BLE001
        print(f"handedness_drc: cannot import ({type(e).__name__}: {e})")
        return 1
    W, H = fr.W, fr.H
    print("handedness_drc -- the emitted solids against KiCad's own export of the board")

    # ---- [K] KiCad's frame, read off its own export -----------------------------------
    print("[K] KiCad's export")
    board = load_step(board_step)
    solids = [(s, s.BoundingBox()) for s in board.Solids()]
    subs = [(s, b) for s, b in solids if b.xlen > W - 1.0 and b.ylen > H - 1.0]
    if len(subs) != 1:
        err(f"expected exactly one card-sized substrate in {Path(board_step).name}, found "
            f"{len(subs)} among {len(solids)} solids -- this is not a board export")
        return 1
    sb = subs[0][1]
    if abs(sb.xlen - W) > SIZE_TOL or abs(sb.ylen - H) > SIZE_TOL:
        err(f"the exported substrate is {sb.xlen:.3f} x {sb.ylen:.3f}, not the {W} x {H} "
            f"card fit_rules is built on")
    # Where the card is in KiCad's frame. Its top-left corner -- board (0, 0) -- is at
    # (xmin, ymax): KiCad negates y on export, which is what makes its file right-handed.
    kx0, kytop = sb.xmin, sb.ymax
    kcx, kcy = (sb.xmin + sb.xmax) / 2.0, (sb.ymin + sb.ymax) / 2.0
    # The body KiCad exports is the laminate; copper and mask stand outside it, equally on
    # both faces of a 2-layer board. The card's underside is that much below the body's.
    skin = (fr.BOARD_TH - sb.zlen) / 2.0
    z_under = sb.zmin - skin
    if not (0.0 <= skin <= 0.10):
        err(f"the exported substrate is {sb.zlen:.3f} thick against a {fr.BOARD_TH} board: "
            f"{skin:+.3f} of copper and mask per face is not a stack-up -- cannot place "
            f"anything against its underside")
    back = [(s, b) for s, b in solids if b.zmax <= sb.zmin + 1e-6]
    front = [(s, b) for s, b in solids if b.zmin >= sb.zmax - 1e-6]
    if not back or len(back) + len(front) + 1 != len(solids):
        err(f"{len(solids)} solids: 1 substrate, {len(back)} below it, {len(front)} above -- "
            f"the rest straddle the board, so this is not the frame it looks like")
    ok(f"one {sb.xlen:.2f} x {sb.ylen:.2f} x {sb.zlen:.2f} substrate at x {sb.xmin:.2f}..{sb.xmax:.2f}, "
       f"y {sb.ymin:.2f}..{sb.ymax:.2f} (KiCad's y runs UP: the card's top edge is the high one); "
       f"{len(back)} component solids on the back, {len(front)} on the front; the card's "
       f"underside is at z {z_under:.3f}")
    to_board = lambda x, y: (x - kx0, kytop - y)                  # KiCad (x, y) -> board, for PRINTING only

    # ---- [P] the shared reader against KiCad's reading --------------------------------
    print("[P] board_parts vs KiCad's own placement of the parts")
    pre = len(_ERRORS)
    mine = [(ref, poly) for ref, poly, _h, src in bp.parts("B") if src == "model"]
    in_kicad = lambda poly: scale(translate(poly, kx0, -kytop), 1.0, -1.0, origin=(0, 0))
    mine_k = [(ref, in_kicad(poly)) for ref, poly in mine]
    names, taken, worst_off = {}, {}, 0.0
    for i, (_s, b) in enumerate(back):
        kb = box(b.xmin, b.ymin, b.xmax, b.ymax)
        ref, poly = max(mine_k, key=lambda rp: rp[1].intersection(kb).area)
        if poly.intersection(kb).area < 0.5 * kb.area:
            bx, by = to_board(*kb.centroid.coords[0])
            err(f"KiCad places a {b.xlen:.2f} x {b.ylen:.2f} body at board ({bx:.2f}, {by:.2f}) "
                f"that no board_parts body covers -- the reader the generators share does "
                f"not see this part, or sees it somewhere else")
            continue
        pb = poly.bounds
        off = max(abs((pb[0] + pb[2]) / 2 - kb.centroid.x), abs((pb[1] + pb[3]) / 2 - kb.centroid.y))
        worst_off = max(worst_off, off)
        if off > PLACE_TOL:
            bx, by = to_board(*kb.centroid.coords[0])
            err(f"{ref}: KiCad has its body centred {off:.3f} mm from where board_parts has "
                f"it (board ({bx:.2f}, {by:.2f})) -- past the {PLACE_TOL} a body and its "
                f"pads can differ by")
        if ref in taken:
            err(f"{ref}: two KiCad solids land on this one board_parts body")
        taken[ref] = i
        names[i] = ref
    left = sorted(set(r for r, _p in mine) - set(taken))
    if left:
        err(f"board_parts has model bodies KiCad did not export: {', '.join(left)} -- a dnp "
            f"part that gained a model, or a model that no longer resolves")
    if len(_ERRORS) == pre:
        ok(f"all {len(back)} B-side bodies KiCad exports are board_parts bodies, one to one, "
           f"centres within {worst_off:.3f} mm -- the reader the generators and the other "
           f"gates share reads the board in KiCad's hand")

    # ---- [M] the mapping the other gates read solids through --------------------------
    print("[M] fit_rules' file frame vs KiCad's")
    pre = len(_ERRORS)
    for bx, by in ((0.0, 0.0), (W, 0.0), (0.0, H), (11.3, 67.9)):
        fx, fy = fr.file_xy(bx, by)
        kx, ky = kx0 + bx, kytop - by                             # where KiCad has that board point
        if abs((kx - fx) - kcx) > 1e-9 or abs((ky - fy) - kcy) > 1e-9:
            err(f"fit_rules.file_xy({bx}, {by}) = ({fx:.3f}, {fy:.3f}); KiCad has that point "
                f"at ({kx:.3f}, {ky:.3f}), which is not ({fx:.3f}, {fy:.3f}) moved to the "
                f"card's centre ({kcx:.3f}, {kcy:.3f}) -- the gates that read solids through "
                f"file_xy() are reading them in the other hand")
        rx, ry = fr.board_xy(fx, fy)
        if abs(rx - bx) > 1e-9 or abs(ry - by) > 1e-9:
            err(f"fit_rules.board_xy() does not invert file_xy() at ({bx}, {by})")
    if len(_ERRORS) == pre:
        ok(f"file_xy() is KiCad's frame moved by ({-kcx:+.3f}, {-kcy:+.3f}) and nothing else, "
           f"and board_xy() inverts it -- interference_drc and assembly_drc read the solids "
           f"in the hand KiCad exports the board in")

    # ---- [B] the braces, by boolean -------------------------------------------------
    used_ledger, braces_fit = set(), True
    for vname, v in fr.VARIANTS.items():
        print(f"[B] {vname}: brace vs KiCad's parts")
        if not v["brace_name"]:
            note(f"{vname}: open frame -- no brace by design")
            continue
        path = ROOT / "enclosure" / "brace" / (v["brace_name"] + ".step")
        if not path.exists():
            err(f"missing {path.relative_to(ROOT)} -- CI emits it")
            continue
        brace = load_step(path)
        at = (kcx, kcy, z_under - v["cavity"])                    # top of the brace at the card's underside

        def hits(shape):
            bb, out = shape.BoundingBox(), []
            for i, (s, pb) in enumerate(back):
                if (pb.xmax < bb.xmin or pb.xmin > bb.xmax or pb.ymax < bb.ymin or pb.ymin > bb.ymax
                        or pb.zmax < bb.zmin or pb.zmin > bb.zmax):
                    continue
                vol = shape.intersect(s).Volume()
                if vol > EPS_MM3:
                    out.append((vol, names.get(i, f"?{i}")))
            return sorted(out, reverse=True)

        pre = len(_ERRORS)
        got = hits(brace.translate(at))
        bad = []
        for vol, ref in got:
            if ref in PROUD_IN_KICAD and vol <= PROUD_IN_KICAD[ref][0]:
                used_ledger.add(ref)
                note(f"{ref}: {vol:.3f} mm3 of its KiCad model inside the {vname} brace -- "
                     f"ledgered (PROUD_IN_KICAD)")
            else:
                bad.append((vol, ref))
        mirror = brace.mirror("XZ")
        blind, mirrors = [], []
        for label, placed in (("as written", mirror.translate(at)),
                              ("turned half a turn", mirror.rotate((0, 0, 0), (0, 0, 1), 180).translate(at))):
            m = hits(placed)
            tot = sum(vol for vol, _r in m)
            mirrors.append((label, tot, len(m)))
            if tot < CANARY_MM3 or len(m) < CANARY_PARTS:
                blind.append(f"{label}: {tot:.3f} mm3 over {len(m)} parts")
            print(f"          its mirror image, {label}: {tot:.3f} mm3 over {len(m)} parts"
                  + (f" (worst {m[0][1]} {m[0][0]:.2f})" if m else ""))
        if bad:
            braces_fit = False
            tot_bad = sum(vol for vol, _r in bad)
            # the tell-tale of a file written in the other hand: it collides, its reflection does not
            wrong_hand = any(t < CANARY_MM3 and t < tot_bad / 10.0 for _l, t, _n in mirrors)
            err(f"the {vname} brace as written does not fit the board KiCad exports: "
                f"{tot_bad:.3f} mm3 of KiCad's part bodies is INSIDE it, over {len(bad)} "
                f"part(s) -- worst " + ", ".join(f"{ref} {vol:.2f}" for vol, ref in bad[:5])
                + ("" if len(bad) <= 5 else ", ...")
                + ("; and its MIRROR IMAGE fits -- THE FILE IS WRITTEN IN THE WRONG HAND"
                   if wrong_hand else ""))
        elif blind:
            err(f"SELF-TEST: the {vname} brace's MIRROR IMAGE does not collide with KiCad's "
                f"board ({'; '.join(blind)}; the bar is {CANARY_MM3} mm3 over {CANARY_PARTS} "
                f"parts) -- this measurement cannot tell the hands apart, so the clean "
                f"result above means nothing")
        if len(_ERRORS) == pre:
            tot = sum(vol for vol, _r in got)
            ok(f"the {vname} brace as written fits KiCad's board ({tot:.3f} mm3 over "
               f"{len(got)} part(s), all ledgered); its mirror image collides in both "
               f"placements, as it must")
    # the ledger audits itself -- but only when the braces fit: on a brace in the wrong hand
    # every entry is "unused" for a reason that has nothing to do with the ledger
    for ref in sorted(set(PROUD_IN_KICAD) - used_ledger) if braces_fit else ():
        err(f"PROUD_IN_KICAD names {ref}, which is inside no brace -- a ledger entry that "
            f"excuses nothing is a standing waiver for whatever {ref} does next; remove it")

    # ---- [S] the shells, in section -------------------------------------------------
    outlines = [(names.get(i, f"?{i}"), silhouette(s), pb.zmin, pb.zmax) for i, (s, pb) in enumerate(back)]
    # ...and the bare-pad footprints, which KiCad exports nothing for (no model): bare copper
    # the grounded lip must not land on, and in one placement the only thing a mirror-image
    # shell lands on (see WHAT IT CANNOT SEE). board_parts gives them their pad envelope and a
    # nominal height; [P] above is what ties that reader's placement to KiCad's.
    bare = [(ref, in_kicad(poly), z_under - h, z_under)
            for ref, poly, h, src in bp.parts("B") if src == "pads"]
    if not bare:
        err("board_parts reads no bare-pad footprint on the back -- [S] has lost the one "
            "witness that tells a shell's hand in its second placement")
    outlines += bare
    for vname, v in fr.VARIANTS.items():
        print(f"[S] {vname}: shell vs KiCad's parts")
        path = ROOT / "enclosure" / (v["shell_name"] + ".stl")
        if not path.exists():
            err(f"missing {path.relative_to(ROOT)} -- CI emits it")
            continue
        shell = trimesh.load(path)
        seat = v["floor"] + v["cavity"]
        raw = [(z, adrc.section_file(shell, z, trimesh)) for _lbl, z in adrc.cavity_levels(v["floor"], v["cavity"])]
        if any(m.is_empty for _z, m in raw):
            err(f"the {vname} shell has no material at one of its cavity cuts -- nothing to compare")
            continue
        # shell z -> KiCad z: the seat at the underside
        shell_hand(vname, raw, outlines, z_under - seat, kcx, kcy, adrc.SECTION_FLOOR)

    # ---- [E] each STEP is its own STL, in the same hand ------------------------------
    print("[E] each STEP against its own STL")
    step_vs_stl(trimesh)

    # ---- [T] the pogo plate under the panel -----------------------------------------
    print("[T] the pogo plate vs the tooling holes in KiCad's export of the panel")
    plate_stl = ROOT / "enclosure" / "solar-glow-drh-pogo-testplate.stl"
    if panel_step is None:
        note("no --panel-step given: the plate is NOT held against the panel here; its row in "
             "check_mesh.py (a bounding box that is not symmetric in y) is all that holds its hand")
    elif not plate_stl.exists():
        err(f"missing {plate_stl.relative_to(ROOT)} -- CI emits it")
    else:
        pre = len(_ERRORS)
        panel = load_step(panel_step)
        pbb = panel.BoundingBox()
        pv, pt = panel.tessellate(0.005)
        pmesh = trimesh.Trimesh([(p.x, p.y, p.z) for p in pv], pt)
        holes, _b = round_holes(pmesh, (pbb.zmin + pbb.zmax) / 2.0, trimesh)
        tooling = [(x, y, d) for x, y, d in holes if abs(d - TOOLING_D) <= 0.02]
        plate = trimesh.load(plate_stl, force="mesh")
        # the plate's solid floor: the first cut from the bottom of its body whose outline is the
        # whole plate (the legs below it are four discs, the cavity above it a frame)
        cut = None
        for z in (1.0, 2.0, 3.0):
            bores, sbb = round_holes(plate, z, trimesh)
            if sbb and abs(sbb[0] - plate.bounds[0][0]) < 0.01 and abs(sbb[2] - plate.bounds[1][0]) < 0.01:
                cut = (bores, sbb)
                break
        if len(tooling) != 2:
            err(f"KiCad's export of the panel has {len(tooling)} holes of dia {TOOLING_D}, not "
                f"the two tooling holes the plate's dowels register on ({len(holes)} holes in all)")
        elif cut is None:
            err("no cut through the plate's floor spans the whole plate -- cannot find its bores")
        else:
            bores, sbb = cut
            # translation only: the plate's outline centred under the panel's
            dx = (pbb.xmin + pbb.xmax) / 2.0 - (sbb[0] + sbb[2]) / 2.0
            dy = (pbb.ymin + pbb.ymax) / 2.0 - (sbb[1] + sbb[3]) / 2.0
            cy = (sbb[1] + sbb[3]) / 2.0

            def miss(flip):
                """each tooling hole to the nearest plate bore, the plate as written or mirrored"""
                at = [(x + dx, (2.0 * cy - y if flip else y) + dy) for x, y, _d in bores]
                return [min(((hx - bx) ** 2 + (hy - by) ** 2) ** 0.5 for bx, by in at) for hx, hy, _d in tooling]

            right, wrong = miss(False), miss(True)
            print(f"          its mirror image: the tooling holes are {wrong[0]:.1f} and "
                  f"{wrong[1]:.1f} mm from the nearest bore")
            if max(right) > TOOLING_TOL:
                err(f"the plate as written does not take the panel face-up: with its outline "
                    f"centred under the panel's (moved {dx:+.3f}, {dy:+.3f}), the two tooling "
                    f"holes are {right[0]:.3f} and {right[1]:.3f} mm from the nearest bore"
                    + (" -- and its MIRROR IMAGE registers: THE FILE IS WRITTEN IN THE WRONG HAND"
                       if max(wrong) <= TOOLING_TOL else ""))
            elif min(wrong) < 1.0:
                err(f"SELF-TEST: the plate's MIRROR IMAGE registers on the tooling holes too "
                    f"({wrong[0]:.3f}, {wrong[1]:.3f} mm) -- the holes are not asymmetric enough "
                    f"to tell the plate's hand")
            if len(_ERRORS) == pre:
                ok(f"the plate as written takes the panel face-up: outline centred under the "
                   f"panel's by ({dx:+.3f}, {dy:+.3f}), a bore under each tooling hole within "
                   f"{max(right):.3f} mm; its mirror image misses")

    print()
    print(f"== handedness: {len(_ERRORS)} error(s) ==")
    return 1 if _ERRORS else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--export-board", metavar="STEP",
                    help="write KiCad's STEP export of the populated board here (needs kicad-cli)")
    ap.add_argument("--export-panel", metavar="STEP",
                    help="with --export-board: also write KiCad's STEP of the panel's substrate")
    ap.add_argument("--board-step", metavar="STEP",
                    help="gate the emitted solids against this export (needs cadquery, trimesh)")
    ap.add_argument("--panel-step", metavar="STEP",
                    help="with --board-step: also hold the pogo plate against this panel export")
    ap.add_argument("--rehearse", action="store_true",
                    help="[S] only, without KiCad: board_parts' outlines stand in for its bodies")
    a = ap.parse_args()
    if a.rehearse:
        if a.export_board or a.board_step or a.export_panel or a.panel_step:
            ap.error("--rehearse stands alone")
        return rehearse()
    if bool(a.export_board) == bool(a.board_step):
        ap.error("give exactly one of --export-board (in the KiCad image) or --board-step (on the runner)")
    if a.export_board:
        if a.panel_step:
            ap.error("--panel-step goes with --board-step")
        return export_board(a.export_board) or (export_panel(a.export_panel) if a.export_panel else 0)
    if a.export_panel:
        ap.error("--export-panel goes with --export-board")
    for p in filter(None, (a.board_step, a.panel_step)):
        if not Path(p).exists():
            print(f"handedness_drc: {p} does not exist -- run the export half first")
            return 1
    return check(a.board_step, a.panel_step)


if __name__ == "__main__":
    raise SystemExit(main())
