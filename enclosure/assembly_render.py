#!/usr/bin/env python3
"""Assembly views: shell + brace + PCB + 8x M2 brass, exploded, closed, and turning.

    python3 enclosure/assembly_render.py            # writes all five views beside this file

      solar-glow-drh-assembly.gif           exploded -> closed
      solar-glow-drh-assembly-exploded.png  first frame of that
      solar-glow-drh-assembly-hero.png      last frame of that
      solar-glow-drh-assembly-reverse.png   closed, from behind: brass flush in its spotfaces
      solar-glow-drh-assembly-spin.gif      one seamless revolution -- the root README hero

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
  * The GIFs are 256-colour, so read them for form and fit, not for colour matching. The
    turntable's palette is sampled around the whole revolution for a reason -- see the note
    at the encode step, and the check that keeps it honest.

Both animations are checked as they are built rather than trusted: the turntable aborts if any
frame touches the render border (a silently cropped hero would ship) or if too much of the loop
moves on quantisation (a silently mis-coloured one would too).
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


GIF_COLORS = 256                       # GIF maximum
GIF_DE = 20                            # a shift this big in a flat area is a visible wrong hue
GIF_DE_FRAC = 0.5                      # ...and this much of the loop moving that far is the bug


def encode_gif(imgs, path, ms, label):
    """Write an animation as ONE palette sampled across the WHOLE sequence, and prove it landed.

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
    srcs = imgs[::max(1, len(imgs) // 10)]
    mont = Image.new("RGB", (imgs[0].width, imgs[0].height * len(srcs)))
    for n, im in enumerate(srcs):
        mont.paste(im, (0, n * imgs[0].height))
    pal = mont.convert("P", palette=Image.ADAPTIVE, colors=GIF_COLORS)
    qs = [im.quantize(palette=pal, dither=Image.Dither.NONE) for im in imgs]

    moved = 0
    for q, s in zip(qs, imgs):
        d = np.abs(np.asarray(q.convert("RGB")).astype(np.int16)
                   - np.asarray(s).astype(np.int16)).max(axis=2)
        moved += int((d > GIF_DE).sum())
    frac = 100.0 * moved / (len(qs) * imgs[0].width * imgs[0].height)
    if frac > GIF_DE_FRAC:
        raise SystemExit(f"{label}: palette is starved -- {frac:.3f}% of the sequence shifts more "
                         f"than {GIF_DE}/255 (limit {GIF_DE_FRAC}%). Widen the palette sample or "
                         f"raise GIF_COLORS; an undithered dark neutral lands on the brass ramp.")
    qs[0].save(path, save_all=True, append_images=qs[1:], duration=ms, loop=0, optimize=True)
    print(f"wrote {os.path.basename(path)}  {imgs[0].width}x{imgs[0].height}  {len(imgs)} frames  "
          f"{os.path.getsize(path) // 1024} KB  {frac:.3f}% of pixels shifted >{GIF_DE}")
    return frac


def cyl(x, y, z0, dz, r, res=28):
    s = vtk.vtkCylinderSource(); s.SetRadius(r); s.SetHeight(dz); s.SetResolution(res)
    s.CappingOn(); s.Update()
    t = vtk.vtkTransform(); t.Translate(x, y, z0 + dz / 2.0); t.RotateX(90)
    f = vtk.vtkTransformPolyDataFilter(); f.SetInputData(s.GetOutput()); f.SetTransform(t); f.Update()
    return f.GetOutput()


# ---- the four things ------------------------------------------------------------------
shell_pd = stl(f"{ROOT}/enclosure/solar-glow-drh-v3_0-backshell-0p6b-brace-Ti-max.stl")
brace_pd = stl(f"{ROOT}/enclosure/brace/solar-glow-drh-diffuser-brace.stl", dz=FLOOR)

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
# row order and KiCad's y-down all interact. All four u/v corner assignments were rendered
# top-down and correlated against the plot itself: this one scores 0.981, the others 0.62-0.82.
# The failure mode is quiet and embarrassing rather than loud: the first attempt textured
# perfectly and rendered the name and number MIRRORED.
_tm.SetOrigin(W, H, Z_FRONT); _tm.SetPoint1(0.0, H, Z_FRONT); _tm.SetPoint2(W, 0.0, Z_FRONT)
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


screws = []
for mx, my in fr.MOUNTS:
    screws.append(("shank", cyl(mx, my, Z_FRONT - SCREW_LEN, SCREW_LEN, SHANK_D / 2.0)))
    screws.append(("head", cyl(mx, my, Z_FRONT, HEAD_H, HEAD_D / 2.0, res=44)))
    screws.append(("slot", slot_bar(mx, my, Z_FRONT)))

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
groups["screw"] = [actor(pd, (0.22, 0.16, 0.07) if k == "slot" else BRASS,
                         spec=0.20 if k == "slot" else 0.70,
                         power=12 if k == "slot" else 55) for k, pd in screws]

for g in groups.values():
    for a in g:
        ren.AddActor(a)

light = vtk.vtkLight(); light.SetPosition(-60, -120, 150); light.SetIntensity(0.9)
light.SetLightTypeToSceneLight(); ren.AddLight(light)
l2 = vtk.vtkLight(); l2.SetPosition(90, 40, 70); l2.SetIntensity(0.45)
l2.SetLightTypeToSceneLight(); ren.AddLight(l2)

cam = ren.GetActiveCamera()
cam.SetFocalPoint(W / 2, H / 2, Z_FRONT / 2)

# base Z of each group in the assembled state
BASE = {"shell": 0.0, "brace": FLOOR, "board": Z_BOARD, "screw": 0.0}
# explode offsets (multiplied by the eased factor)
EXPL = {"shell": -26.0, "brace": -8.0, "board": 10.0, "screw": 30.0}

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
    ang = 208 + 26 * math.sin(2 * math.pi * t)
    for name, acts in groups.items():
        dz = EXPL[name] * e
        for a in acts:
            a.SetPosition(0, 0, dz)
    rad = math.radians(ang)
    dist, elev = 235.0, math.radians(58.0)
    cam.SetPosition(W / 2 + dist * math.sin(elev) * math.cos(rad),
                    H / 2 + dist * math.sin(elev) * math.sin(rad),
                    Z_FRONT / 2 + dist * math.cos(elev) + 14 * e)
    cam.SetFocalPoint(W / 2, H / 2, Z_FRONT / 2 + 3 * e)
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
encode_gif([Image.open(f).convert("RGB") for f in frames], gif, 90, "exploded")
Image.open(frames[-1]).save(os.path.join(HERE, f"{STEM}-hero.png"))
Image.open(frames[0]).save(os.path.join(HERE, f"{STEM}-exploded.png"))

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
for _k, _pd in screws:
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
_wr = vtk.vtkPNGWriter(); _wr.SetFileName(os.path.join(HERE, f"{STEM}-reverse.png"))
_wr.SetInputConnection(_w.GetOutputPort()); _wr.Write()
# ---- turntable: the assembled article, one seamless revolution --------------------------
#
# Same camera family as the hero still (elev 58 deg, view angle 30) so the spin reads as that
# picture rotating rather than a different render. Constant angular velocity and an exclusive
# 0..360 sweep, so the last frame hands off to the first with no stutter -- any easing here
# would make the loop visibly hitch once per revolution.
#
# The frame is CROPPED to the box the part actually sweeps, not to the render window. At this
# elevation the card fills barely half a square frame's height, and on a 60-frame GIF that
# dead background is most of the file. The crop box is measured from the frames themselves
# (union over the whole revolution), so it stays correct if the camera or the board changes.
SPIN_FRAMES = 60
SPIN_SIZE = 1000                       # square render; the crop below sets the real output size
SPIN_DIST, SPIN_ELEV, SPIN_VANG = 215.0, 58.0, 30.0
SPIN_PAD = 22                          # px of background kept around the swept box
SPIN_MS = 70                           # -> 4.2 s per revolution

ren3 = vtk.vtkRenderer(); ren3.SetBackground(0.965, 0.963, 0.955)
rw3 = vtk.vtkRenderWindow(); rw3.SetOffScreenRendering(1); rw3.AddRenderer(ren3)
rw3.SetSize(SPIN_SIZE, SPIN_SIZE)

for _a in ([_mat(shell_pd, TI, 0.85, 0.55, 42, 0.16), _mat(brace_pd, RESIN, 0.85, 0.12, 8, 0.16),
            textured(_mat(board_pd, MASK, 0.85, 0.30, 26, 0.16))]
           + [_mat(p, SOLAR, 0.85, 0.42, 48, 0.16) for p in solar_pds]
           + [_mat(p, SILVER, 0.85, 0.75, 60, 0.16) for p in cap_pds]
           + [_mat(p, IC, 0.85, 0.22, 18, 0.16) for p in ic_pds]
           + [_mat(pd, (0.22, 0.16, 0.07) if k == "slot" else BRASS, 0.85,
                   0.20 if k == "slot" else 0.70, 12 if k == "slot" else 55, 0.16)
              for k, pd in screws]):
    ren3.AddActor(_a)
for _pos, _i in [((-60, -120, 150), 0.90), ((90, 40, 70), 0.45)]:
    _L = vtk.vtkLight(); _L.SetPosition(*_pos); _L.SetIntensity(_i)
    _L.SetLightTypeToSceneLight(); ren3.AddLight(_L)

_BG = np.array([0.965, 0.963, 0.955]) * 255
_cam3 = ren3.GetActiveCamera()
_spin, _boxes = [], []
for _i in range(SPIN_FRAMES):
    _az = math.radians(360.0 * _i / SPIN_FRAMES)      # exclusive of 360 -> seamless loop
    _el = math.radians(SPIN_ELEV)
    _cam3.SetPosition(W / 2 + SPIN_DIST * math.sin(_el) * math.cos(_az),
                      H / 2 + SPIN_DIST * math.sin(_el) * math.sin(_az),
                      Z_FRONT / 2 + SPIN_DIST * math.cos(_el))
    _cam3.SetFocalPoint(W / 2, H / 2, Z_FRONT / 2)
    _cam3.SetViewUp(0, 0, 1); _cam3.SetViewAngle(SPIN_VANG)
    ren3.ResetCameraClippingRange(); rw3.Render()
    _w3 = vtk.vtkWindowToImageFilter(); _w3.SetInput(rw3); _w3.Update()
    _arr = vtk_to_numpy(_w3.GetOutput().GetPointData().GetScalars())
    _arr = _arr.reshape(SPIN_SIZE, SPIN_SIZE, -1)[::-1, :, :3]
    _fg = np.abs(_arr.astype(np.int16) - _BG.astype(np.int16)).max(axis=2) > 6
    _ys, _xs = np.nonzero(_fg)
    if len(_xs) == 0:
        raise SystemExit(f"turntable frame {_i} rendered empty -- the camera is inside the part")
    # A clipped hero is the kind of thing that ships unnoticed, so make it fatal rather than
    # trusting that the framing constants above still suit the geometry.
    if _xs.min() == 0 or _ys.min() == 0 or _xs.max() == SPIN_SIZE - 1 or _ys.max() == SPIN_SIZE - 1:
        raise SystemExit(f"turntable frame {_i} (az {math.degrees(_az):.0f} deg) touches the frame "
                         f"edge -- raise SPIN_DIST or lower SPIN_VANG")
    _boxes.append((_xs.min(), _ys.min(), _xs.max(), _ys.max()))
    _spin.append(Image.fromarray(_arr))

_x0 = max(0, min(b[0] for b in _boxes) - SPIN_PAD)
_y0 = max(0, min(b[1] for b in _boxes) - SPIN_PAD)
_x1 = min(SPIN_SIZE, max(b[2] for b in _boxes) + SPIN_PAD + 1)
_y1 = min(SPIN_SIZE, max(b[3] for b in _boxes) + SPIN_PAD + 1)
_x1 += (_x1 - _x0) & 1                                # even dimensions, for the video encoders
_y1 += (_y1 - _y0) & 1
_spin = [im.crop((_x0, _y0, _x1, _y1)) for im in _spin]

encode_gif(_spin, os.path.join(HERE, f"{STEM}-spin.gif"), SPIN_MS, "turntable")

print(f"wrote {STEM}-hero.png, -exploded.png, -reverse.png, .gif, -spin.gif")

import shutil
shutil.rmtree(OUT, ignore_errors=True)
