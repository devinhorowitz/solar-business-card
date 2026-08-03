#!/usr/bin/env python3
"""Assembly views: shell + brace + PCB + 8x M2 brass, exploded, closed, and turning.

    python3 enclosure/assembly_render.py            # writes all seven views

CI OWNS THESE OUTPUTS. The PCB CI workflow runs this script after rebuilding the enclosure CAD
and raytracing the card face -- both of which it consumes -- and commits the files below with
the rest of the generated set, so changing the board updates the imagery automatically. Run it
locally to check a change by all means, but do not COMMIT the result: VTK does not produce
identical pixels across GL stacks, so a hand-run render and CI's will churn against each other.

      solar-glow-drh-assembly.gif           exploded -> closed
      solar-glow-drh-assembly-exploded.png  first frame of that
      solar-glow-drh-assembly-hero.png      last frame of that
      solar-glow-drh-assembly-reverse.png   closed, from behind: brass flush in its spotfaces
      solar-glow-drh-assembly-spin.gif      the card flip -- hero of the root README
      solar-glow-drh-assembly-shell-spin.gif  the same flip, bare titanium -- enclosure/README.md
      brace/…-diffuser-brace-render.png     the brace alone -- hero of enclosure/brace/README.md

WHAT MAKES THIS TRUSTWORTHY

Every dimension comes from something already committed, not from a mock-up:

  * both enclosure bodies are the real STEP-derived STLs;
  * the board outline, the 8 mount positions and every part footprint come from
    enclosure/board_parts.py, which reads the committed .kicad_pcb;
  * the Z stack (floor 1.00 / cavity 1.80 / board 0.60) and the screw arithmetic come from
    enclosure/fit_rules.py and the shell generator's own constants;
  * the show face is the RAYTRACED CARD ITSELF, textured on -- monogram window, name, number,
    cartouche, ENIG -- not a black rectangle standing in for a PCB.

So if the board moves, these pictures move with it. That is the point -- the previous
enclosure drawings were hand-restated and quietly went on describing a part that had
changed underneath them.

CAVEATS, because a render invites more trust than it has earned:
  * B-side parts are drawn as bounding boxes -- exact for the supercap cans, slightly
    conservative for small passives.
  * This is VTK Phong shading, NOT the raytracer. It is a fit and material check; the
    photographic article is what scripts/render.py produces into Generated/docs/.
  * The screwdriver slot is drawn as a recessed element rather than cut, because
    vtkBooleanOperationPolyDataFilter returns an empty mesh on these coarse cylinders --
    it did exactly that once and silently left a plain puck.
  * The GIFs are palette-limited, so read them for form and fit, not for colour matching. The
    palette is sampled across the whole sequence and sized to the error budget -- see the note
    at the encode step, and the check that keeps it honest.

Every animation is checked as it is built rather than trusted: a flip aborts if any frame touches
the render border (a silently cropped hero would ship), if the camera-distance probe cannot frame
the part at all angles, or if too much of the loop moves on quantisation (a silently mis-coloured
hero would ship just as quietly).
"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vtk
from vtk.util.numpy_support import vtk_to_numpy
import numpy as np
from PIL import Image
import fit_rules as fr
import board_parts as bp
from shapely.geometry import box as sbox, Point as spt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HERE = os.path.dirname(os.path.abspath(__file__))
STEM = "solar-glow-drh-assembly"   # NOT `BASE`: that name is already the explode-base dict below
OUT = os.path.join(HERE, "_frames")
os.makedirs(OUT, exist_ok=True)

W, H = fr.W, fr.H
FLOOR, CAVITY, BOARD = 1.00, fr.CAVITY, fr.BOARD_TH
SCREW_LEN, BOSS_R, PILOT_R = 3.0, fr.BOSS_R, fr.PILOT_R
Z_BOARD = FLOOR + CAVITY                     # board underside
Z_FRONT = Z_BOARD + BOARD                    # show face

# ---- materials -----------------------------------------------------------------------
TI      = (0.70, 0.71, 0.74)
RESIN   = (0.94, 0.93, 0.89)
MASK    = (0.075, 0.075, 0.080)              # matte black soldermask
SOLAR   = (0.045, 0.055, 0.090)              # near-black, hint of blue
SILVER  = (0.780, 0.790, 0.810)
BRASS   = (0.78, 0.60, 0.24)
IC      = (0.100, 0.100, 0.105)


def poly_prism(shape, z0, dz):
    """shapely polygon (with holes) -> closed vtkPolyData prism."""
    pts = vtk.vtkPoints()
    cell = vtk.vtkCellArray()
    rings = [list(shape.exterior.coords)[:-1]] + [list(r.coords)[:-1] for r in shape.interiors]
    poly = vtk.vtkPolyData()
    idx = 0
    for ring in rings:
        cell.InsertNextCell(len(ring))
        for x, y in ring:
            pts.InsertNextPoint(x, y, z0)
            cell.InsertCellPoint(idx); idx += 1
    poly.SetPoints(pts); poly.SetPolys(cell)
    tri = vtk.vtkTriangleFilter(); tri.SetInputData(poly); tri.Update()
    ext = vtk.vtkLinearExtrusionFilter()
    ext.SetInputConnection(tri.GetOutputPort())
    ext.SetExtrusionTypeToVectorExtrusion(); ext.SetVector(0, 0, dz); ext.CappingOn(); ext.Update()
    nrm = vtk.vtkPolyDataNormals(); nrm.SetInputConnection(ext.GetOutputPort())
    nrm.ConsistencyOn(); nrm.AutoOrientNormalsOn(); nrm.Update()
    return nrm.GetOutput()


def stl(path, dz=0.0):
    """STLs are CENTRED ON THE ORIGIN (the generators use wx = bx - W/2), while the board,
    screws and parts below are in board coords 0..W / 0..H. Shift to board coords here."""
    r = vtk.vtkSTLReader(); r.SetFileName(path); r.Update()
    t = vtk.vtkTransform(); t.Translate(W / 2.0, H / 2.0, dz)
    f = vtk.vtkTransformPolyDataFilter(); f.SetInputData(r.GetOutput()); f.SetTransform(t); f.Update()
    r = f
    n = vtk.vtkPolyDataNormals(); n.SetInputConnection(r.GetOutputPort())
    n.ConsistencyOn(); n.AutoOrientNormalsOn(); n.Update()
    return n.GetOutput()


def actor(pd, rgb, spec=0.25, power=20, opacity=1.0):
    m = vtk.vtkPolyDataMapper(); m.SetInputData(pd)
    a = vtk.vtkActor(); a.SetMapper(m)
    p = a.GetProperty()
    p.SetColor(*rgb); p.SetSpecular(spec); p.SetSpecularPower(power)
    p.SetDiffuse(0.85); p.SetAmbient(0.16); p.SetOpacity(opacity)
    return a


# THE SCENE IS LEFT-HANDED, so every render leaves here mirrored unless we say otherwise.
# Board coords are X-right, Y-down, Z-front -- x_hat cross y_hat = -z_hat -- and dropping that
# straight into a right-handed renderer mirrors the picture. Probed rather than assumed: with the
# camera in front and up = -Y, a marker at board x=45 lands on the LEFT of frame, where the real
# card puts it on the right. You cannot fix it with the up vector either; up = +Y rights the X
# axis and stands the card on its head.
#
# It hid for so long because the shell is X-symmetric -- outline, eight bosses, both cell cutouts.
# The only tells are the rear engraving (the maker's-mark lines of the day; the medallion has
# since replaced them), which read backwards in every hero we shipped, and
# the asymmetric support lip (2.5 west against 1.0 east), which sat on the wrong side in every
# cavity view.
#
# Mirroring the finished image is exactly equivalent to mirroring the scene, because that is all
# the defect is. Two cosmetic consequences, neither factual: the turntables now turn the other
# way, and the key light appears to come from the other side.
def present(img):
    return img.transpose(Image.FLIP_LEFT_RIGHT)


GIF_COLORS = 256                       # GIF maximum
GIF_DE = 20                            # a shift this big in a flat area is a visible wrong hue
GIF_DE_FRAC = 0.5                      # ...and this much of the loop moving that far is the bug

# Re-render noise floor, measured between two consecutive CI runs on IDENTICAL inputs (main
# f841b95 -> 7963c0f): 0.0317% of pixels moved more than 8, worst single pixel 54, mean absolute
# difference 0.0072. The thresholds below sit ~16x and ~70x above that.
NOISE_DE = 8
NOISE_FRAC = 0.5                       # % of pixels allowed past NOISE_DE
NOISE_MEAN = 0.5                       # mean absolute channel difference


def _is_noise(old_frames, new_frames):
    """True if two renders differ only by re-render noise, not by anything anyone can see.

    THE RAYTRACER IS NOT BIT-REPRODUCIBLE. Generated/docs/…-card-face.png comes back a few
    hundred bytes different on every run with the same board, and that plot is the TEXTURE on
    the show face here -- so every textured view inherits the wobble, and GIF encoding turns a
    handful of jittered pixels into a wholly different byte stream. The result was ~7 MB of
    binary rewritten on every kibot run for no visible change, which is both repo bloat and the
    thing that makes a REAL change impossible to spot in a diff.
    (The tell that this is the mechanism and not a GL difference: the brace render, which is the
    only output with no raytraced texture, comes back byte-identical across those same runs.)
    """
    if len(old_frames) != len(new_frames) or old_frames[0].size != new_frames[0].size:
        return False
    moved = 0
    total = 0.0
    for o, n in zip(old_frames, new_frames):
        d = np.abs(np.asarray(o).astype(np.int16) - np.asarray(n).astype(np.int16))
        moved += int((d.max(axis=2) > NOISE_DE).sum())
        total += float(d.mean())
    frac = 100.0 * moved / (len(new_frames) * new_frames[0].width * new_frames[0].height)
    # Always show the numbers behind a keep/write decision. The 2026-08-01 shell-spin hunt
    # burned a full instrumented re-render to learn that the medallion had measured 0.4751%
    # against the 0.5% threshold; with this line, the CI log would have said so at the time.
    print(f"  [gate] {len(new_frames)} frame(s) {new_frames[0].size}: "
          f"{frac:.4f}% past dE{NOISE_DE} (limit {NOISE_FRAC}%), mean {total / len(new_frames):.4f}")
    return frac <= NOISE_FRAC and total / len(new_frames) <= NOISE_MEAN


def _frames_of(path):
    """Decode a committed GIF or PNG to RGB frames; [] if it is missing or unreadable."""
    if not os.path.exists(path):
        return []
    try:
        im = Image.open(path)
        out = []
        for i in range(getattr(im, "n_frames", 1)):
            im.seek(i)
            out.append(im.convert("RGB"))
        return out
    except Exception:
        return []


def save_png_stable(img, path, gate=True):
    """Same noise gate as the GIFs, for the textured stills.

    `gate=False` for an output with NO raytraced texture. The gate exists because the card-face
    plot comes back a few hundred bytes different every run, so every view wearing it as a
    texture inherits a wobble that is not a change. An UNTEXTURED view has no such wobble: render
    the same STL twice and the PNG is byte-identical (measured -- 0.0000 % of pixels past ΔE 12,
    0.0000 mean). For those the gate has no upside and one downside, because git already
    suppresses a byte-identical write; all the gate can add is the power to suppress a REAL one.

    It did exactly that. The 2026-07-30 respin cut SJ1's pocket out of the brace and grew C9's
    to the 0805 land, CI committed the new .stl -- and kept the old …-brace-render.png, because
    rendering the two STLs in one process moves 0.4333 % of pixels at max ΔE 89, and the gate
    fires below NOISE_FRAC = 0.5 %. A pocket appearing or vanishing is small in area and huge in
    contrast, which is the one signature a fraction-of-frame test cannot see. So the brace shipped
    a portrait of a brace that no longer existed -- the same failure the comment at BRACE_PNG
    describes from before there was a generator at all, arriving this time through the gate.

    Raising NOISE_FRAC is not the fix: cross-runner noise on the TEXTURED views has been measured
    at 1.4189 %, above this 0.5 % as it stands, so the noise and real-change populations already
    overlap and no single threshold separates them. What separates them is whether the view
    carries the texture, and that is known per call site.

    IT HAPPENED A SECOND TIME before that rule reached the GIFs (2026-08-01): the whole rear
    MEDALLION -- 25.7 mm of new engraving, ring text, monogram, serial -- measured 0.4751 %
    against the 0.5 % limit on the shell-spin sequence, and the pre-medallion gif survived
    four CI runs as "raytracer noise". Flat-shaded relief moves only its EDGE pixels (the
    crest tops and coin floor shade almost exactly like the flat back they replaced), and the
    back faces the camera for only half the revolution -- big change, thin footprint, exactly
    the brace-pocket signature again. encode_gif() now takes the same gate switch, and the
    bare-shell flip -- untextured, so its re-render is deterministic -- passes gate=False.
    """
    img = present(img)
    if gate and _is_noise(_frames_of(path), [img]):
        print(f"kept {os.path.basename(path)}  (re-render differs only by raytracer noise)")
        return False
    img.save(path)
    return True


def encode_gif(imgs, path, ms, label, gate=True):
    """Write an animation as ONE palette sampled across the WHOLE sequence, and prove it landed.

    `gate=False` for a sequence with NO raytraced texture, same rule as save_png_stable and for
    the same reason -- see the second-occurrence note there: the untextured shell flip re-renders
    deterministically, so the noise gate had nothing to suppress and used its one power to keep
    a pre-medallion shell for four CI runs (0.4751 % measured vs the 0.5 % limit).

    Per-frame ADAPTIVE palettes -- PIL's default when handed RGB frames, and what this script
    used to do at 192 colours -- cost a colour table per frame and make flat areas shimmer,
    because the palette is re-derived from each frame's own histogram. A palette from frame 0
    alone is worse still: these scenes are nearly all neutral darks (black soldermask, near-black
    cells, titanium in shadow) with one small warm brass ramp, and frame 0 shows least of it.
    Fitting 128 colours to that one histogram left the shell's dark greys with no near neighbour
    and, undithered, they snapped onto the brass browns -- the titanium rim came out visibly TAN
    while the render behind it was neutral.

    The gate is HOW MUCH of the picture moves, not the single worst pixel: across tens of frames
    of half-megapixel there is always a specular outlier, and a max-shift gate fired at 70/255 on
    a sequence whose flat areas were already clean.
    """
    imgs = [present(i) for i in imgs]
    srcs = imgs[::max(1, len(imgs) // 10)]
    mont = Image.new("RGB", (imgs[0].width, imgs[0].height * len(srcs)))
    for n, im in enumerate(srcs):
        mont.paste(im, (0, n * imgs[0].height))

    def _pal(n):
        return mont.convert("P", palette=Image.ADAPTIVE, colors=n)

    def _err(pal, sample):
        moved = px = 0
        for s in sample:
            d = np.abs(np.asarray(s.quantize(palette=pal, dither=Image.Dither.NONE).convert("RGB"))
                       .astype(np.int16) - np.asarray(s).astype(np.int16)).max(axis=2)
            moved += int((d > GIF_DE).sum()); px += d.size
        return 100.0 * moved / px

    # SPEND THE SMALLEST PALETTE THAT STILL MEETS THE BUDGET. These sequences differ enormously
    # in how much colour they actually contain -- the textured card carries gold, copper and
    # soldermask, while the bare titanium shell is very nearly one grey ramp and quantises to
    # 0.000% error at any size. Fixing everything at 256 makes the cheap ones pay the expensive
    # one's price for nothing, and those bytes are better spent on RESOLUTION, which is what
    # decides whether the name and number on the card are legible at all.
    # Chosen on a subsample for speed, then verified on every frame below -- the choice being
    # cheap does not make the guarantee cheap.
    _probe = imgs[::max(1, len(imgs) // 12)]
    pal, colors = _pal(GIF_COLORS), GIF_COLORS
    for _n in (48, 64, 96, 128, 192):
        if _n >= GIF_COLORS:
            break
        _p = _pal(_n)
        if _err(_p, _probe) <= GIF_DE_FRAC * 0.6:      # headroom, since this is a subsample
            pal, colors = _p, _n
            break
    qs = [im.quantize(palette=pal, dither=Image.Dither.NONE) for im in imgs]

    frac = _err(pal, imgs)
    if frac > GIF_DE_FRAC:
        raise SystemExit(f"{label}: palette is starved -- {frac:.3f}% of the sequence shifts more "
                         f"than {GIF_DE}/255 (limit {GIF_DE_FRAC}%) at {colors} colours. Widen the "
                         f"palette sample; an undithered dark neutral lands on the brass ramp.")
    if gate and _is_noise(_frames_of(path), [q.convert("RGB") for q in qs]):
        print(f"kept {os.path.basename(path)}  (re-render differs only by raytracer noise)")
        return False
    qs[0].save(path, save_all=True, append_images=qs[1:], duration=ms, loop=0, optimize=True)
    print(f"wrote {os.path.basename(path)}  {imgs[0].width}x{imgs[0].height}  {len(imgs)} frames  "
          f"{os.path.getsize(path) // 1024} KB  {colors} colours  "
          f"{frac:.3f}% shifted >{GIF_DE}")
    return True


def cyl(x, y, z0, dz, r, res=28):
    s = vtk.vtkCylinderSource(); s.SetRadius(r); s.SetHeight(dz); s.SetResolution(res)
    s.CappingOn(); s.Update()
    t = vtk.vtkTransform(); t.Translate(x, y, z0 + dz / 2.0); t.RotateX(90)
    f = vtk.vtkTransformPolyDataFilter(); f.SetInputData(s.GetOutput()); f.SetTransform(t); f.Update()
    return f.GetOutput()


# ---- the four things ------------------------------------------------------------------
shell_pd = stl(f"{ROOT}/enclosure/solar-glow-drh-v3_0-backshell-0p6b-brace-Ti-max.stl")
brace_pd = stl(f"{ROOT}/enclosure/brace/solar-glow-drh-diffuser-brace.stl", dz=FLOOR)

# ---- FER1, the ferrite sheet behind the NFC coil ----------------------------------------
# It was missing from this animation entirely, which made the stack a lie by omission: the
# card cannot read through titanium without it, and the brace carries a pocket machined
# specifically to hold it. Extent and depth come from fit_rules (ONE home) rather than being
# re-typed here.
#
# Z: the pocket is cut into the brace's BOARD-FACING face, so the sheet's top face is the
# brace top -- which is exactly Z_BOARD, the PCB underside. Drawn filling the pocket
# (Z_BOARD - FER_POCKET_DEPTH -> Z_BOARD) rather than its full 0.38: the extra 0.05 is the
# proud-then-compressed allowance, and drawing it would interpenetrate the board and z-fight.
FERRITE = (0.24, 0.235, 0.25)    # flexible ferrite: dark neutral grey, matte, no sheen
_fx0, _fy0, _fx1, _fy1 = fr.FER
ferrite_pd = poly_prism(sbox(_fx0, _fy0, _fx1, _fy1),
                        Z_BOARD - fr.FER_POCKET_DEPTH, fr.FER_POCKET_DEPTH)

# board outline: 50.8 x 88.9, R3 corners, 8 x M2 clearance holes
R = 3.0
out = sbox(R, 0, W - R, H).union(sbox(0, R, W, H - R))
for cx, cy in [(R, R), (W - R, R), (R, H - R), (W - R, H - R)]:
    out = out.union(spt(cx, cy).buffer(R, resolution=48))
for mx, my in fr.MOUNTS:
    out = out.difference(spt(mx, my).buffer(1.10, resolution=32))
board_pd = poly_prism(out, Z_BOARD, BOARD)

# ---- the show face, textured with the real card ----------------------------------------
# A flat black slab is honest about the STACK and says nothing about what this OBJECT IS -- no
# monogram window, no name, no number. The raytraced card-face plot is an orthographic view of
# the front at the board's own aspect (1008x1768 against 50.8 x 88.9, 0.2% off), so it maps
# straight onto the show face with a planar projection and no distortion.
#
# NOTE this is the one input here that does NOT come from a file this repo hand-maintains:
# Generated/ is CI's, and CI regenerates it from the board on every PCB/** change. That is the
# right dependency direction -- re-route the front and this hero follows -- but it does mean a
# clone that has never run CI has nothing to texture with, so say so plainly rather than
# rendering a silently blank card.
TEX = f"{ROOT}/Generated/docs/solar-glow-drh-v4_0-card-face.png"
if not os.path.exists(TEX):
    raise SystemExit(f"missing {TEX} -- it is generated by the KiBot workflow on PCB/** changes; "
                     f"fetch a branch that has it rather than rendering a blank card")

_tm = vtk.vtkTextureMapToPlane()
_tm.SetInputData(board_pd)
# Orientation is not guessable from VTK's conventions -- the texture origin, the PNG reader's
# row order and KiCad's y-down all interact -- so all four u/v corner assignments were rendered
# top-down and correlated against the plot itself. This corner assignment is the one that is
# correct once `present()` undoes the scene's left-handedness; the opposite one was correct
# BEFORE that, because it cancelled the mirror. Change one and you must change the other.
_tm.SetOrigin(0.0, H, Z_FRONT); _tm.SetPoint1(W, H, Z_FRONT); _tm.SetPoint2(0.0, 0.0, Z_FRONT)
_tm.Update()
board_pd = _tm.GetOutput()

_tr = vtk.vtkPNGReader(); _tr.SetFileName(TEX); _tr.Update()
board_tex = vtk.vtkTexture(); board_tex.SetInputConnection(_tr.GetOutputPort())
board_tex.InterpolateOn(); board_tex.EdgeClampOn(); board_tex.MipmapOn()


def textured(a):
    """Give a board actor the card plot. White base, so the plot's own colours come through
    untinted -- leaving it at MASK would multiply the gold down to nearly nothing."""
    a.GetProperty().SetColor(1.0, 1.0, 1.0)
    a.SetTexture(board_tex)
    return a


# front-side parts (solar cells) and the back-side blockers, for material colour
front = bp.parts("F")
back = bp.parts("B")


def part_boxes(plist, refs, zbase, up=True):
    outp = []
    for ref, poly, h, _s in plist:
        if ref not in refs:
            continue
        x0, y0, x1, y1 = poly.bounds
        hh = h if h else 1.70
        outp.append(poly_prism(sbox(x0, y0, x1, y1), zbase if up else zbase - hh, hh))
    return outp


solar_refs = {r for r, *_ in front if r.startswith("PV")}
solar_pds = part_boxes(front, solar_refs, Z_FRONT)        # stand on the show face
cap_pds = part_boxes(back, {"SC1", "SC2", "SC3", "SC4"}, Z_BOARD, up=False)
ic_pds = part_boxes(back, {"U1", "U7", "U8", "U6", "U9"}, Z_BOARD, up=False)

# M2x3 SLOTTED brass. Head sized to the back spotface, CBORE_D = 3.0 -- the shell's own
# constant -- rather than the Ø3.7 pan head first drawn. The design notes cap it at
# "pan head <= Ø4.0 (cell-limited; absolute Ø5.3 touches the cell at 2.66 mm)", so smaller
# is strictly more cell clearance. Shank is Ø2.0 nominal.
HEAD_D, HEAD_H, SHANK_D = 3.0, 0.90, 2.00
SLOT_W, SLOT_DEEP = 0.45, 0.35

def slot_bar(x, y, z0):
    """The screwdriver slot, drawn as its own recessed dark element.

    A CSG difference is the 'right' way, but vtkBooleanOperationPolyDataFilter wants two
    clean closed manifolds and quietly returns an empty mesh on these coarse cylinders --
    it did exactly that, and the head silently fell back to a plain puck. A thin box seated
    just below the head's top face is the same picture with none of the fragility.
    """
    c = vtk.vtkCubeSource()
    c.SetXLength(HEAD_D * 0.86); c.SetYLength(SLOT_W); c.SetZLength(SLOT_DEEP)
    c.SetCenter(x, y, z0 + HEAD_H - SLOT_DEEP / 2.0 - 0.02); c.Update()
    return c.GetOutput()


M2_PITCH = 0.40                  # ISO metric coarse for M2
THREAD_R = 0.105                 # ridge tube radius; M2 crest-to-root is ~0.245 total


def thread_helix(x, y, z0, dz, r_major, pitch=M2_PITCH, seg=18):
    """The helical thread ridge, as a swept tube around a helix.

    The shank was a bare cylinder -- a dowel, not a screw. A real thread form is a swept
    trapezoid and a CSG job; vtkBooleanOperationPolyDataFilter is already documented in
    slot_bar() as unreliable on these coarse cylinders, so this takes the same way out it
    does: a tube on a helical polyline sitting proud of a slightly undersized shank reads as
    a thread at every size this render is ever viewed at, with none of the fragility.
    """
    n = max(8, int(round(dz / pitch * seg)))
    pts = vtk.vtkPoints()
    line = vtk.vtkPolyLine()
    line.GetPointIds().SetNumberOfIds(n + 1)
    r = r_major - THREAD_R * 0.55
    for i in range(n + 1):
        z = z0 + dz * i / n
        a = 2.0 * math.pi * (z - z0) / pitch
        pts.InsertNextPoint(x + r * math.cos(a), y + r * math.sin(a), z)
        line.GetPointIds().SetId(i, i)
    cells = vtk.vtkCellArray(); cells.InsertNextCell(line)
    pd = vtk.vtkPolyData(); pd.SetPoints(pts); pd.SetLines(cells)
    tube = vtk.vtkTubeFilter()
    tube.SetInputData(pd); tube.SetRadius(THREAD_R); tube.SetNumberOfSides(10); tube.CappingOn()
    tube.Update()
    return tube.GetOutput()


# Each entry carries its OWN axis, because the screws now rotate about it (see the render
# loop). Without the axis a screw would spin about the scene origin and orbit the card.
screws = []
for mx, my in fr.MOUNTS:
    screws.append(("shank", cyl(mx, my, Z_FRONT - SCREW_LEN, SCREW_LEN,
                                SHANK_D / 2.0 - THREAD_R * 0.55), mx, my))
    screws.append(("thread", thread_helix(mx, my, Z_FRONT - SCREW_LEN, SCREW_LEN,
                                          SHANK_D / 2.0), mx, my))
    screws.append(("head", cyl(mx, my, Z_FRONT, HEAD_H, HEAD_D / 2.0, res=44), mx, my))
    screws.append(("slot", slot_bar(mx, my, Z_FRONT), mx, my))

# ---- render ---------------------------------------------------------------------------
ren = vtk.vtkRenderer(); ren.SetBackground(0.965, 0.963, 0.955)
rw = vtk.vtkRenderWindow(); rw.SetOffScreenRendering(1); rw.AddRenderer(ren); rw.SetSize(900, 1000)

groups = {}
groups["shell"] = [actor(shell_pd, TI, spec=0.55, power=42)]
groups["brace"] = [actor(brace_pd, RESIN, spec=0.12, power=8)]
groups["board"] = ([textured(actor(board_pd, MASK, spec=0.30, power=26))]
                   + [actor(p, SOLAR, spec=0.42, power=48) for p in solar_pds]
                   + [actor(p, SILVER, spec=0.75, power=60) for p in cap_pds]
                   + [actor(p, IC, spec=0.22, power=18) for p in ic_pds])
groups["ferrite"] = [actor(ferrite_pd, FERRITE, spec=0.06, power=6)]
groups["screw"] = []
for k, pd, mx, my in screws:
    a = actor(pd, (0.22, 0.16, 0.07) if k == "slot" else BRASS,
              spec=0.20 if k == "slot" else 0.70,
              power=12 if k == "slot" else 55)
    a.SetOrigin(mx, my, 0.0)     # spin about the screw's own axis, not the scene origin
    groups["screw"].append(a)

for g in groups.values():
    for a in g:
        ren.AddActor(a)

light = vtk.vtkLight(); light.SetPosition(-60, -120, 150); light.SetIntensity(0.9)
light.SetLightTypeToSceneLight(); ren.AddLight(light)
l2 = vtk.vtkLight(); l2.SetPosition(90, 40, 70); l2.SetIntensity(0.45)
l2.SetLightTypeToSceneLight(); ren.AddLight(l2)
# Below-side lights (2026-07-31): the camera moved under the horizon, and with both lights
# on the front side the shell's back rendered in flat ambient -- 0.15-0.6 mm of fins and
# medallion, invisible. A low raking key plus a soft fill from below make the relief read;
# the two front lights stay, they carry the board/brace faces the explode gap exposes.
l3 = vtk.vtkLight(); l3.SetPosition(-70, -50, -170); l3.SetIntensity(0.85)
l3.SetLightTypeToSceneLight(); ren.AddLight(l3)
l4 = vtk.vtkLight(); l4.SetPosition(130, 110, -90); l4.SetIntensity(0.30)
l4.SetLightTypeToSceneLight(); ren.AddLight(l4)

cam = ren.GetActiveCamera()
cam.SetFocalPoint(W / 2, H / 2, Z_FRONT / 2)

# base Z of each group in the assembled state
BASE = {"shell": 0.0, "brace": FLOOR, "board": Z_BOARD,
        "ferrite": Z_BOARD - fr.FER_POCKET_DEPTH, "screw": 0.0}
# Explode offsets (multiplied by the eased factor). The ferrite gets its OWN offset, between
# the brace's and the board's, so it separates into a visible third layer instead of riding
# the brace. It is PSA'd into the brace pocket and travels captive with it in real assembly --
# but an exploded view exists to show what the closed stack hides, and a sheet that never
# leaves its pocket is a sheet nobody can see.
EXPL = {"shell": -26.0, "brace": -8.0, "board": 10.0, "ferrite": 2.5, "screw": 30.0}

SCREW_TURNS = 2.0                # see the rotation note in the frame loop
FRAMES = 44
frames = []
for i in range(FRAMES):
    t = i / (FRAMES - 1)
    # ease: fully exploded -> assembled -> hold
    if t < 0.62:
        u = 1.0 - (t / 0.62)
        e = u * u * (3 - 2 * u)          # smoothstep in
    else:
        e = 0.0
    # SCREWS TURN AS THEY DRIVE IN (2026-08-03). They used to translate rigidly -- eight
    # brass dowels sliding into holes. The slot is what makes the rotation legible: a smooth
    # cylinder spinning about its own axis is indistinguishable from a still one, so the
    # visible cue is the driver slot sweeping round.
    #
    # The rate is CHOSEN, not physical, and that is deliberate. At the real M2 pitch (0.40)
    # the 30 mm approach is 75 turns, and even the 3 mm of actual thread engagement is 7.5 --
    # at 90 ms/frame either one aliases into strobing jitter that reads as vibration, not
    # driving. SCREW_TURNS is set to what a viewer parses as "being screwed down".
    ang = -360.0 * SCREW_TURNS * e
    for name, acts in groups.items():
        dz = EXPL[name] * e
        for a in acts:
            a.SetPosition(0, 0, dz)
            if name == "screw":
                a.SetOrientation(0.0, 0.0, ang)
    # STILL CAMERA, ANGLED FROM BELOW (2026-07-31). Two findings, one fix: the old view
    # swung +-26 deg and dollied while the parts translated, so the whole assembly seemed
    # to float and wander; and it looked DOWN from the screw side, so the shell's back --
    # the medallion -- was never in frame, and neither was the interface this animation
    # exists to show: the brace's pockets meeting the PCB's B-side parts. Now the camera
    # holds one position and one focal point for the whole sequence -- the PARTS do the
    # moving -- pitched 22 deg BELOW the horizon, so the explode gap opens straight onto
    # the board's underside components over the brace, and the closed hold presents the
    # medallion face.
    rad = math.radians(208.0)
    dist, pitch = 252.0, math.radians(22.0)
    cam.SetPosition(W / 2 + dist * math.cos(pitch) * math.cos(rad),
                    H / 2 + dist * math.cos(pitch) * math.sin(rad),
                    Z_FRONT / 2 - dist * math.sin(pitch))
    cam.SetFocalPoint(W / 2, H / 2, Z_FRONT / 2)
    cam.SetViewUp(0, 0, 1)
    cam.SetViewAngle(26)
    ren.ResetCameraClippingRange()
    rw.Render()
    wif = vtk.vtkWindowToImageFilter(); wif.SetInput(rw); wif.Update()
    wr = vtk.vtkPNGWriter(); wr.SetFileName(f"{OUT}/f{i:03d}.png")
    wr.SetInputConnection(wif.GetOutputPort()); wr.Write()
    frames.append(f"{OUT}/f{i:03d}.png")
print(f"rendered {len(frames)} frames")

gif = os.path.join(HERE, f"{STEM}.gif")
# THE TWO STILLS BELOW ARE FRAMES OF THIS GIF -- frames[-1] and frames[0] of the very
# sequence just encoded. They are not an independent observation of the scene, so they must
# not get an independent verdict: they follow the SEQUENCE's decision instead of running a
# fresh fraction-of-frame test on one frame.
#
# THIRD OCCURRENCE, found 2026-08-03. save_png_stable's docstring records the first two
# (brace-render 07-30, shell-spin 08-01). This one: the 08-02 fit change -- AIR 0.12 -> 0.22
# plus the per-part 0.16 for the LED pockets -- moved the diffuser brace's pockets, CI
# committed the new .stl and a new gif on every run since, and kept hero.png from 07-31 and
# exploded.png from 08-01. Two portraits of a brace that no longer exists, exactly the
# failure the docstring already describes twice.
#
# The signature is the one it predicts: small in area, huge in contrast. A single still
# spreads that change across one frame and lands under NOISE_FRAC; the 60-frame sequence
# accumulates it past the threshold. So the gif passed while its own endpoints were
# suppressed -- and a gif disagreeing with its first and last frames about whether anything
# changed is not a judgement call, it is an inconsistency. Raising the threshold would not
# fix it (the docstring measured why); tying the derived stills to the source does.
_gif_wrote = encode_gif([Image.open(f).convert("RGB") for f in frames], gif, 90, "exploded")
save_png_stable(Image.open(frames[-1]).convert("RGB"),
                os.path.join(HERE, f"{STEM}-hero.png"), gate=not _gif_wrote)
save_png_stable(Image.open(frames[0]).convert("RGB"),
                os.path.join(HERE, f"{STEM}-exploded.png"), gate=not _gif_wrote)

# ---- reverse side, fully closed: the 8 brass tips flush in their CBORE_D spotfaces -------
ren2 = vtk.vtkRenderer(); ren2.SetBackground(0.965, 0.963, 0.955)
rw2 = vtk.vtkRenderWindow(); rw2.SetOffScreenRendering(1); rw2.AddRenderer(ren2); rw2.SetSize(940, 1040)


def _mat(pd, rgb, diff, spec, pw, amb):
    m = vtk.vtkPolyDataMapper(); m.SetInputData(pd)
    a = vtk.vtkActor(); a.SetMapper(m); p = a.GetProperty()
    p.SetColor(*rgb); p.SetDiffuse(diff); p.SetSpecular(spec)
    p.SetSpecularPower(pw); p.SetAmbient(amb); p.SetSpecularColor(1, 1, 1)
    return a


ren2.AddActor(_mat(shell_pd, (0.68, 0.69, 0.72), 0.60, 0.62, 46, 0.13))
ren2.AddActor(textured(_mat(board_pd, MASK, 0.85, 0.30, 26, 0.14)))
for _p in solar_pds:
    ren2.AddActor(_mat(_p, SOLAR, 0.75, 0.45, 55, 0.10))
for _k, _pd, _mx, _my in screws:
    ren2.AddActor(_mat(_pd, (0.22, 0.16, 0.07) if _k == "slot" else (0.74, 0.56, 0.21),
                       0.70, 0.18 if _k == "slot" else 0.82, 12 if _k == "slot" else 62, 0.11))
for _pos, _i in [((-80, -130, -170), 0.80), ((120, 80, -100), 0.36), ((0, 0, -240), 0.30)]:
    _L = vtk.vtkLight(); _L.SetPosition(*_pos); _L.SetIntensity(_i)
    _L.SetLightTypeToSceneLight(); ren2.AddLight(_L)
_c2 = ren2.GetActiveCamera()
_d, _el, _az = 205.0, math.radians(133.0), math.radians(212)
_c2.SetPosition(W / 2 + _d * math.sin(_el) * math.cos(_az),
                H / 2 + _d * math.sin(_el) * math.sin(_az), Z_FRONT / 2 + _d * math.cos(_el))
_c2.SetFocalPoint(W / 2, H / 2, Z_FRONT / 2); _c2.SetViewUp(0, 0, 1); _c2.SetViewAngle(25)
ren2.ResetCameraClippingRange(); rw2.Render()
_w = vtk.vtkWindowToImageFilter(); _w.SetInput(rw2); _w.Update()
_rv = vtk_to_numpy(_w.GetOutput().GetPointData().GetScalars())
_rv = _rv.reshape(rw2.GetSize()[1], rw2.GetSize()[0], -1)[::-1, :, :3]
# gate=False: the textured board actor is in this scene but fully occluded by the closed
# shell, so no raytraced pixel reaches the frame and the render is deterministic (measured:
# byte-stable across runs). Gated, this view would silently keep a SERIAL bump -- "No 001" ->
# "No 002" moves a few hundred pixels on a 940x1040 still, far under the 0.5 % limit.
save_png_stable(Image.fromarray(_rv), os.path.join(HERE, f"{STEM}-reverse.png"), gate=False)
# ---- card flip: upright, front -> back -> front ------------------------------------------
#
# NOT a turntable. Spinning the card flat about its thickness axis is the pizza view: it never
# shows the back, and it presents a business card in an orientation nobody holds one in. This
# rotates about the card's LONG axis with that axis vertical -- front, edge, back, edge, front --
# which is what a hand does when someone turns a card over, and it puts the artwork upright.
#
# Screen-up is board -Y, because the card-face plot's row 0 (the top of the artwork) maps to
# board y=0. Constant angular velocity over an exclusive 0..360 sweep, so the last frame hands
# off to the first with no hitch; easing would stutter once per revolution.
FLIP_FRAMES = 96                       # 3.75 deg/frame
FLIP_MS = 70                           # -> 6.7 s per revolution
FLIP_SIZE = 980                        # square render; the crop below sets the real output size
FLIP_VANG = 26.0
FLIP_TILT = 21.0                       # above dead-on, so it reads as a solid, not a sprite
FLIP_EASE = 0.18                       # linger on the faces, hurry through the edges
FLIP_PAD = 20                          # px of background kept around the swept box

_BG = np.array([0.965, 0.963, 0.955]) * 255


def card_flip(actor_list, path, label, frames=FLIP_FRAMES, ms=FLIP_MS, size=FLIP_SIZE,
              animate=None, gate=True):
    """One seamless revolution about the long axis, held upright. Returns nothing; writes a GIF.

    animate = (actor, [vtkTexture per frame]) swaps the actor's texture before each frame --
    how the hero's LEDs breathe. The list is indexed by frame and may reuse texture objects.
    gate=False when nothing in actor_list wears the raytraced texture (see encode_gif)."""
    ren = vtk.vtkRenderer(); ren.SetBackground(0.965, 0.963, 0.955)
    rw = vtk.vtkRenderWindow(); rw.SetOffScreenRendering(1); rw.AddRenderer(ren)
    rw.SetSize(size, size)
    for a in actor_list:
        ren.AddActor(a)

    _bs = [a.GetBounds() for a in actor_list]
    b = [min(v[0] for v in _bs), max(v[1] for v in _bs), min(v[2] for v in _bs),
         max(v[3] for v in _bs), min(v[4] for v in _bs), max(v[5] for v in _bs)]
    cx, cy, cz = (b[0] + b[1]) / 2, (b[2] + b[3]) / 2, (b[4] + b[5]) / 2

    # Lights are fixed in the WORLD, not carried on the camera, so turning the part changes how
    # it catches them -- that is most of what makes a rotation read as solid rather than as a
    # flat sprite being warped. The two behind the part matter more than they look: without
    # them the entire back half of the revolution is a silhouette.
    for pos, inten in [((cx - 90, cy - 130, cz + 150), 0.85),
                       ((cx + 110, cy - 40, cz + 70), 0.40),
                       ((cx - 40, cy - 90, cz - 160), 0.60),
                       ((cx + 80, cy + 60, cz - 60), 0.25)]:
        L = vtk.vtkLight(); L.SetPosition(*pos); L.SetIntensity(inten)
        L.SetLightTypeToSceneLight(); ren.AddLight(L)

    cam = ren.GetActiveCamera()
    tilt = math.radians(FLIP_TILT)

    def place(theta, dist):
        cam.SetPosition(cx + dist * math.cos(tilt) * math.sin(theta),
                        cy - dist * math.sin(tilt),
                        cz + dist * math.cos(tilt) * math.cos(theta))
        cam.SetFocalPoint(cx, cy, cz)
        cam.SetViewUp(0, -1, 0)        # board -Y is up: y=0 is the top of the artwork
        cam.SetViewAngle(FLIP_VANG)
        ren.ResetCameraClippingRange()

    def shoot():
        rw.Render()
        w = vtk.vtkWindowToImageFilter(); w.SetInput(rw); w.Update()
        a = vtk_to_numpy(w.GetOutput().GetPointData().GetScalars())
        a = a.reshape(size, size, -1)[::-1, :, :3]
        return a, np.abs(a.astype(np.int16) - _BG.astype(np.int16)).max(axis=2) > 6

    # Fit the distance to the part rather than hardcoding one: this runs over both the assembled
    # card and the bare shell, which are different sizes, and whichever it is has to clear the
    # frame at EVERY angle. Probed every 30 deg, then every rendered frame is checked below.
    span = max(b[1] - b[0], b[3] - b[2], b[5] - b[4])
    dist = None
    for trial in [span * k for k in (2.2, 2.4, 2.6, 2.9, 3.2, 3.6)]:
        worst = size
        for probe in range(0, 360, 30):
            place(math.radians(probe), trial)
            _, fg = shoot()
            if not fg.any():
                worst = -1
                break
            ys, xs = np.nonzero(fg)
            worst = min(worst, xs.min(), ys.min(), size - 1 - xs.max(), size - 1 - ys.max())
        if worst >= FLIP_PAD:
            dist = trial
            break
    if dist is None:
        raise SystemExit(f"{label}: no camera distance frames the part at every angle")

    # THETA IS EASED, and the easing is what makes this read as a reveal rather than a spin.
    # A constant sweep spends a full quarter of the loop on the edge -- a 3.55 mm sliver of a
    # 88.9 mm card -- and hurries past the two faces that are the entire point. theta(t) =
    # 2*pi*t - A*sin(2*2*pi*t) slows to 0.64x at the front and back and runs 1.36x through the
    # edges. It stays PERIODIC and monotonic (1 - 2A > 0), so the loop still hands off with no
    # hitch: the usual objection to easing an animation loop does not apply to this form.
    imgs, boxes = [], []
    for i in range(frames):
        _t = i / frames                               # exclusive of 1.0 -> seamless loop
        if animate is not None:
            animate[0].SetTexture(animate[1][i])
        place(2.0 * math.pi * _t - FLIP_EASE * math.sin(2.0 * 2.0 * math.pi * _t), dist)
        arr, fg = shoot()
        if not fg.any():
            raise SystemExit(f"{label} frame {i} rendered empty -- the camera is inside the part")
        ys, xs = np.nonzero(fg)
        # A clipped hero is the kind of thing that ships unnoticed, so make it fatal.
        if xs.min() == 0 or ys.min() == 0 or xs.max() == size - 1 or ys.max() == size - 1:
            raise SystemExit(f"{label} frame {i} touches the frame "
                             f"edge -- the distance probe above picked too tight a fit")
        boxes.append((xs.min(), ys.min(), xs.max(), ys.max()))
        imgs.append(Image.fromarray(arr))

    x0 = max(0, min(v[0] for v in boxes) - FLIP_PAD)
    y0 = max(0, min(v[1] for v in boxes) - FLIP_PAD)
    x1 = min(size, max(v[2] for v in boxes) + FLIP_PAD + 1)
    y1 = min(size, max(v[3] for v in boxes) + FLIP_PAD + 1)
    x1 += (x1 - x0) & 1                               # even dimensions, for the video encoders
    y1 += (y1 - y0) & 1
    encode_gif([im.crop((x0, y0, x1, y1)) for im in imgs], path, ms, label, gate=gate)


# ---- THE LEDS BREATHE IN THE HERO (2026-07-31). The card's whole point is four amber LEDs
# glowing through the DRH cut in the front copper, and the hero never showed it. The glow is
# painted into the TEXTURE per frame: inside GLOW_WIN the monogram's letter cutouts are told
# apart from the gold plate by the window's own pixels (see the yellowness note below), so
# there is no second source of truth about where the letters are -- the card-face plot the
# board is textured with IS the mask. Amber is added through it with a two-stage bloom (tight core
# + wide halo), on a cosine eased with gamma 1.6 -- an approximation of led.c's PWM ramp, by
# eye, not a claim about the firmware. FOUR full breaths per revolution, an integer, so the
# loop still hands off seamlessly; 16 quantised levels keep it to 16 textures instead of 160.
GLOW_WIN_FRONT = (14.95, 40.8, 35.85, 47.0)      # the monogram window, board coords
HERO_FRAMES, HERO_MS, BREATHS = 160, 80, 4       # 12.8 s/rev, 3.2 s/breath (was 96 x 70ms)
AMBER = np.array([255.0, 168.0, 38.0])

_base = np.asarray(Image.open(TEX).convert("RGB")).astype(np.float32)
_th, _tw = _base.shape[:2]
_sx, _sy = _tw / W, _th / H                      # plot row 0 = board y 0 (top of artwork)
_wx0, _wy0 = int(GLOW_WIN_FRONT[0] * _sx), int(GLOW_WIN_FRONT[1] * _sy)
_wx1, _wy1 = int(GLOW_WIN_FRONT[2] * _sx), int(GLOW_WIN_FRONT[3] * _sy)
_win = _base[_wy0:_wy1, _wx0:_wx1]
# The letters are NOT the dark pixels -- a luminance threshold catches only their outline
# shadows (verified against the plot: interiors are mid-bright gray-green laminate). What
# separates cutout from plate is YELLOWNESS: the gold plate runs (R+G)/2 - B ~ 185, the
# bare-laminate letters ~ 30. A 0.5 mm margin keeps the dark board slivers at the window
# corners -- outside the plate, where no light exits -- from leaking.
_yel = (_win[..., 0] + _win[..., 1]) / 2.0 - _win[..., 2]
_letters = (_yel < 90.0).astype(np.float32)
_m = max(4, int(0.5 * _sx))
_letters[:_m, :] = 0; _letters[-_m:, :] = 0; _letters[:, :_m] = 0; _letters[:, -_m:] = 0

def _blur(m, r):
    k = np.exp(-0.5 * (np.arange(-3 * r, 3 * r + 1) / r) ** 2); k /= k.sum()
    m = np.apply_along_axis(lambda v: np.convolve(v, k, "same"), 0, m)
    return np.apply_along_axis(lambda v: np.convolve(v, k, "same"), 1, m)

_glow_mask = np.clip(_blur(_letters, max(2, int(0.12 * _sx))) * 1.0
                     + _blur(_letters, max(4, int(0.55 * _sx))) * 0.55, 0.0, 1.4)

def _breath_texture(level):
    img = _base.copy()
    img[_wy0:_wy1, _wx0:_wx1] = np.clip(
        _win + _glow_mask[..., None] * AMBER[None, None, :] * level, 0, 255)
    vi = vtk.vtkImageData()
    vi.SetDimensions(_tw, _th, 1)
    arr = np.ascontiguousarray(img[::-1].reshape(-1, 3).astype(np.uint8))
    from vtk.util.numpy_support import numpy_to_vtk as _n2v
    va = _n2v(arr, deep=1, array_type=vtk.VTK_UNSIGNED_CHAR); va.SetNumberOfComponents(3)
    vi.GetPointData().SetScalars(va)
    tx = vtk.vtkTexture(); tx.SetInputData(vi); tx.InterpolateOn()
    return tx

_LEVELS = 16
_breath_tex = [_breath_texture(q / (_LEVELS - 1)) for q in range(_LEVELS)]
_tex_seq = []
for _i in range(HERO_FRAMES):
    _b = (0.5 - 0.5 * math.cos(2 * math.pi * BREATHS * _i / HERO_FRAMES)) ** 1.6
    _tex_seq.append(_breath_tex[min(_LEVELS - 1, int(round(_b * (_LEVELS - 1))))])

_board_actor = textured(_mat(board_pd, MASK, 0.85, 0.30, 26, 0.16))
card_flip([_mat(shell_pd, TI, 0.85, 0.55, 42, 0.16), _mat(brace_pd, RESIN, 0.85, 0.12, 8, 0.16),
           _board_actor]
          + [_mat(p, SOLAR, 0.85, 0.42, 48, 0.16) for p in solar_pds]
          + [_mat(p, SILVER, 0.85, 0.75, 60, 0.16) for p in cap_pds]
          + [_mat(p, IC, 0.85, 0.22, 18, 0.16) for p in ic_pds]
          + [_mat(pd, (0.22, 0.16, 0.07) if k == "slot" else BRASS, 0.85,
                  0.20 if k == "slot" else 0.70, 12 if k == "slot" else 55, 0.16)
             for k, pd, _mx, _my in screws],
          os.path.join(HERE, f"{STEM}-spin.gif"), "card flip",
          frames=HERO_FRAMES, ms=HERO_MS, animate=(_board_actor, _tex_seq))

# ---- the bare shell, same motion: the hero of enclosure/README.md ------------------------
# Naked titanium, nothing in it. The same rotation shows what a still cannot: the machined
# cavity with its bosses and lip on the way round, and the medallion back coming after.
# gate=False: no texture in this scene, so the re-render is deterministic and the noise gate
# has nothing to do here but harm -- it sat on the pre-medallion gif for four CI runs at a
# measured 0.4751 % vs the 0.5 % limit (the brace-pocket failure shape, second occurrence).
card_flip([_mat(shell_pd, TI, 0.82, 0.60, 46, 0.15)],
          os.path.join(HERE, f"{STEM}-shell-spin.gif"), "shell flip", gate=False)

# ---- the brace alone: the hero of enclosure/brace/README.md ------------------------------
# That image shipped in the repo's initial import with NO generator behind it, so while the
# brace was respun against the real board it went on showing the OLD one -- the H with the
# straight middle band, the geometry that put 593 mm3 of resin inside SC1/SC3/SC4. A doc hero
# nothing can regenerate is a doc hero that goes quietly wrong, which is the failure this whole
# pipeline exists to stop. It is now built from the same STL the assembly views load.
BRACE_PNG = os.path.join(HERE, "brace", "solar-glow-drh-diffuser-brace-render.png")
BRACE_SIZE = 960

ren4 = vtk.vtkRenderer(); ren4.SetBackground(0.965, 0.963, 0.955)
rw4 = vtk.vtkRenderWindow(); rw4.SetOffScreenRendering(1); rw4.AddRenderer(ren4)
rw4.SetSize(BRACE_SIZE, BRACE_SIZE)
ren4.AddActor(_mat(brace_pd, RESIN, 0.88, 0.16, 12, 0.20))
for _pos, _i in [((-70, -120, 140), 0.85), ((110, 60, 90), 0.40), ((0, 0, -120), 0.18)]:
    _L = vtk.vtkLight(); _L.SetPosition(*_pos); _L.SetIntensity(_i)
    _L.SetLightTypeToSceneLight(); ren4.AddLight(_L)

_c4 = ren4.GetActiveCamera()
_az4, _el4 = math.radians(232.0), math.radians(56.0)
_c4.SetPosition(math.sin(_el4) * math.cos(_az4), math.sin(_el4) * math.sin(_az4), math.cos(_el4))
_c4.SetFocalPoint(0, 0, 0); _c4.SetViewUp(0, 0, 1); _c4.SetViewAngle(26)
# Frame from the part's own bounds rather than a hand-tuned distance: the brace footprint is
# computed from the board and changes shape when the board does, so a fixed camera would crop it.
ren4.ResetCamera()
_base4 = _c4.GetParallelScale(), _c4.GetPosition()


def _shot4(zoom):
    """Render at a zoom and report (image, margin in px). Negative margin means it is clipped."""
    ren4.ResetCamera()
    _c4.Zoom(zoom)
    ren4.ResetCameraClippingRange(); rw4.Render()
    w = vtk.vtkWindowToImageFilter(); w.SetInput(rw4); w.Update()
    a = vtk_to_numpy(w.GetOutput().GetPointData().GetScalars())
    a = a.reshape(BRACE_SIZE, BRACE_SIZE, -1)[::-1, :, :3]
    fg = np.abs(a.astype(np.int16) - _BG.astype(np.int16)).max(axis=2) > 6
    if not fg.any():
        return a, -1
    ys, xs = np.nonzero(fg)
    return a, min(xs.min(), ys.min(), BRACE_SIZE - 1 - xs.max(), BRACE_SIZE - 1 - ys.max())


# Pick the tightest framing that still leaves a margin, rather than hand-tuning a constant: the
# brace footprint is COMPUTED from the board and changes shape when the board does, so whatever
# number looked right today is wrong after the next re-route. The guard below already caught
# exactly that -- a zoom of 1.18 clipped the legs.
BRACE_MARGIN = 18
_best4 = None
for _z in (1.20, 1.15, 1.10, 1.05, 1.00, 0.95, 0.90, 0.85):
    _img4, _m4 = _shot4(_z)
    if _m4 >= BRACE_MARGIN:
        _best4 = (_img4, _z, _m4)
        break
if _best4 is None:
    raise SystemExit("brace render never fits the frame -- the part is far larger than expected")
_img4, _z4, _m4 = _best4
_fg4 = np.abs(_img4.astype(np.int16) - _BG.astype(np.int16)).max(axis=2) > 6
# Crop to the part. A brace that is mostly long thin legs occupies ~11% of a square frame, and
# the rest is background nobody asked for; the bbox is measured, so it follows the geometry.
_ys4, _xs4 = np.nonzero(_fg4)
_p4 = 24
_img4 = _img4[max(0, _ys4.min() - _p4):min(BRACE_SIZE, _ys4.max() + _p4 + 1),
              max(0, _xs4.min() - _p4):min(BRACE_SIZE, _xs4.max() + _p4 + 1)]
_fg4 = np.abs(_img4.astype(np.int16) - _BG.astype(np.int16)).max(axis=2) > 6
# gate=False: this is the ONE output with no raytraced texture, so it is bit-reproducible and
# the noise gate can only ever hide a real respin from it. See save_png_stable's docstring for
# the run where it did.
_wrote4 = save_png_stable(Image.fromarray(_img4), BRACE_PNG, gate=False)
if _wrote4:
    print(f"wrote brace/{os.path.basename(BRACE_PNG)}  {_img4.shape[1]}x{_img4.shape[0]}  "
          f"zoom {_z4:.2f}, margin {_m4}px, fills {100.0 * _fg4.sum() / _fg4.size:.1f}% of frame")


import shutil
shutil.rmtree(OUT, ignore_errors=True)
