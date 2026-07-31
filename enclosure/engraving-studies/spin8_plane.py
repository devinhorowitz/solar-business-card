#!/usr/bin/env python3
"""Engraving, spin 8. THE GAMEPLAN: every bright feature lives on the bearing plane.

Spin 7 proved the two-texture finish is a bench operation; this spin re-architects the
medallion so the bench operation becomes the SIMPLEST one that exists: the whole part,
face-down, on a lapping plate. The crests -- ring text, rim, hoop, serial -- are raised
to the frame's own +0.15 bearing plane, so the plate touches frame + crests and NOTHING
ELSE, by geometry: the art field sits 0.15 below the plate, the fin ribs 0.05 below, the
coin floor deeper still. No jig, no hand block, no way to scuff what the plate cannot
reach. Re-lapping is the same operation forever.

"Raised" is the wrong word for how it is machined: the crests are LEFT, exactly as the
frame is left -- stock-plane islands the field-facing op steers around, then the coin
recess is sunk around them. Same ops the shell already uses for its border.

THE COIN IS SUNKEN, THE BRIGHT AREA IS SMALL -- both deliberate (the user's call, and
the numbers agree): a large lapped surface (spin 7's bright dial, ~450 mm2) is striking
but scuffs in use and takes real work to restore; these crests total tens of mm2, wear
only where they already bear, and a minute on the plate brings them back.

ONE LAW AMENDED, LOUDLY: the frame stops being the SOLE bearing surface -- the medallion
crests join it, coplanar, finished by the same pass. That is a change to fit_rules'
bearing rule (FIN_PROUD's cap exists to keep rib tops 0.05 UNDER this plane, and ribs
stay under it -- they stay dark). It lands in fit_rules and the generator only when a
variant here ships.

Three takes, same architecture:

  W  SUNKEN COIN        coin floor 0.25 into the field -> 0.40 walls under the crests;
                        full furniture (rim, ring text, hoop, serial)
  X  DEEP COIN          coin floor 0.45 -> 0.60 walls, the full depth budget as shadow
                        under the bright plane; same furniture
  Y  BARE COIN          W's depths, no rim, no hoop -- text and serial alone in the
                        recess, the recess wall is the only circle

Depth accounting: the coin floor is 0.25 / 0.45 below the ART FIELD (the 1.00-floor
reference plane), both within the 0.60 ceiling. Crest walls measure from the +0.15
bearing plane: 0.40 / 0.60.

THE TOOL IS A STRAIGHT END MILL, AND THE PLANE IS WHY. Relief used the 15-deg tapered
cutter; here it would be a mistake: the taper flares wall x tan(15) into every crest
from EACH side, and at these wall heights that is 0.11-0.16 per side against a ~0.30
ring stroke -- the letters would come out knife-edged below the plane and never touch
the plate. Islands want vertical walls, exactly like the frame that shares their plane:
W/Y model a dia 0.3 finisher (1.3xD at the 0.40 walls), X must step up to dia 0.4 (its
0.60 walls put the dia 0.3 at 2xD, which Ti disallows) and pays for its shadow in the
small counters the bigger tool cannot enter -- left standing at the plane, they lap
bright and the tightest digits read as solid marks. Measured and reported per variant.
"""
from __future__ import annotations

import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)

import numpy as np
import vtk
from PIL import Image, ImageDraw
from scipy import ndimage
from shapely.geometry import Point
from shapely.ops import unary_union
from vtk.util.numpy_support import numpy_to_vtk, vtk_to_numpy

import spin1_cutters as E
import spin4_provenance as P4
import spin7_lapped as L7
import fit_rules as fr

OUT = E.OUT
PX = E.PX
CX, CY = E.CX, E.CY

PLANE = 0.15                 # the bearing plane: the frame's proudness over the art field
R_TEXT, CAP = 10.8, 1.80
TXT = "SOLAR POWERED · NFC 13.56 MHz · MMXXVI · "

CENTRE = [("Nº 001", 2.40, -1.6, "b"), ("REV 4.0", 1.40, 2.0, "r"), ("MMXXVI", 1.40, 4.4, "r")]
# Z's centre: the small lines up 1.40 -> 1.60 so their counters clear the O0.3 rest pass
CENTRE_Z = [("Nº 001", 2.40, -1.6, "b"), ("REV 4.0", 1.60, 2.0, "r"), ("MMXXVI", 1.60, 4.4, "r")]


def _annulus(r0, r1):
    return Point(CX, CY).buffer(r1, resolution=128).difference(
        Point(CX, CY).buffer(r0, resolution=128))


def crest_glyphs(rim, hoop, coin_r, centre=CENTRE, ring_txt=TXT, ring_anchor=None):
    ring, _ = P4.ring_text(ring_txt, R_TEXT, CAP,
                           word_top=ring_anchor if ring_anchor else "SOLAR POWERED")
    parts = [ring] + [E.line_geom(t, CX, CY + dy, cap, w) for t, cap, dy, w in centre]
    if hoop:
        parts.append(_annulus(8.75, 9.25))
    if rim:
        parts.append(_annulus(coin_r, coin_r + 0.70))
    return unary_union(parts)


def build_plane(coin_d, rim, hoop, coin_r=12.15, rest_d=None, centre=CENTRE, ring_txt=TXT,
                ring_anchor=None):
    """Depth field with z = 0 AT THE BEARING PLANE (the stock the frame is left from).

    field cells -> PLANE (the facing op), coin cells -> PLANE + coin_d, crest cells -> 0.
    Rendered with z_lift = PLANE so the field lands on the shell's own art-field level
    and the crests stand proud at the frame's height. Vertical walls -- these are milled
    islands cleared by a straight end mill, not tapered relief -- so the crest top IS
    the full stroke, and the tool radius is set by the wall height: dia 0.3 at 0.40
    walls (1.3xD), dia 0.4 at 0.60 (the dia 0.3 would run 2xD in Ti).

    rest_d enables the two-tool cascade (variant Z): the primary tool takes the open
    coin to coin_d, then the O0.3 rest-machines ONLY what the primary could not enter,
    stopping at rest_d -- counters open at 0.40-wall depth while every visible edge
    keeps the full-depth shadow.
    """
    tool_r = 0.15 if coin_d <= 0.30 else 0.20
    f = E.Field(E.ART, pad=0.0)
    gm = f.raster(crest_glyphs(rim, hoop, coin_r, centre, ring_txt, ring_anchor))
    coin = f.raster(Point(CX, CY).buffer(coin_r + (0.70 if rim else 0.0), resolution=128))
    field = np.ones_like(gm)
    reach_coin = E.Field.opening(coin & ~gm, tool_r)
    reach_step = E.Field.opening(field & ~gm & ~coin, 0.15)
    f.z = np.where(reach_coin, PLANE + coin_d, np.where(reach_step, PLANE, 0.0)).astype(np.float32)
    rest_a = 0.0
    if rest_d is not None:
        # rest machining: the O0.3 goes back ONLY where the primary tool could not,
        # and stops at its own 1.3xD wall (rest_d into the field). Confined by
        # construction to counters and sub-O0.4 channels -- invisible from outside
        # the letterforms, and exactly what turns 'solid marks' back into digits.
        rest = E.Field.opening(coin & ~gm, 0.15) & ~reach_coin
        f.z = np.maximum(f.z, np.where(rest, PLANE + rest_d, 0.0).astype(np.float32))
        reach_coin = reach_coin | rest
        rest_a = float(rest.sum()) * PX * PX
    webs = (field & ~gm) & ~reach_coin & ~reach_step        # uncut metal AT THE PLANE
    tops = (f.z < 0.015)
    return f, gm, tops, webs, tool_r, rest_a


def plane_surfaces(f, tops, thr=0.015):
    ok = np.ones((f.ny - 1, f.nx - 1), bool)
    tp = tops[:-1, :-1] & tops[:-1, 1:] & tops[1:, 1:] & tops[1:, :-1]
    return (E._sheet(f, ok & ~tp, PLANE), E._sheet(f, ok & tp, PLANE))


_SHELL_SPLIT = None


def shell_split(zthr=-(PLANE - 0.005)):
    """(rest, frame_tops): the shell with its bearing-plane faces peeled into their own
    actor, because the plate laps the frame bright along with the crests."""
    global _SHELL_SPLIT
    if _SHELL_SPLIT is not None:
        return _SHELL_SPLIT
    tf = vtk.vtkTriangleFilter()
    tf.SetInputData(E.SHELL)
    tf.Update()
    q = tf.GetOutput()
    pts = vtk_to_numpy(q.GetPoints().GetData())
    tris = vtk_to_numpy(q.GetPolys().GetConnectivityArray()).reshape(-1, 3)
    top = (pts[tris, 2] < zthr).all(axis=1)

    def sub(mask):
        t = tris[mask]
        ca = vtk.vtkCellArray()
        ca.SetData(numpy_to_vtk(np.arange(len(t) + 1, dtype=np.int64) * 3, deep=1,
                                array_type=vtk.VTK_ID_TYPE),
                   numpy_to_vtk(t.ravel().astype(np.int64), deep=1, array_type=vtk.VTK_ID_TYPE))
        p = vtk.vtkPolyData()
        p.SetPoints(q.GetPoints())
        p.SetPolys(ca)
        n = vtk.vtkPolyDataNormals()
        n.SetInputData(p)
        n.ConsistencyOn()
        n.AutoOrientNormalsOn()
        n.Update()
        return n.GetOutput()

    _SHELL_SPLIT = (sub(~top), sub(top))
    return _SHELL_SPLIT


def shot_plane(surfaces, path, size=1500, az=5.0, el=13.0, dist=232.0, grazing=False, crop=None):
    """Blast everywhere; the bearing plane -- frame tops AND crest tops -- lapped bright."""
    rest, frame_top = shell_split()
    dark, bright = surfaces
    ren = vtk.vtkRenderer()
    ren.SetBackground(*E.BG)
    rw = vtk.vtkRenderWindow()
    rw.SetOffScreenRendering(1)
    rw.AddRenderer(ren)
    rw.SetSize(size, size)
    ren.AddActor(E.mat(rest,      E.TI_BLAST, diff=0.88, spec=0.13, pw=16, amb=0.07))
    ren.AddActor(E.mat(dark,      E.TI_BLAST, diff=0.90, spec=0.04, pw=12, amb=0.07))
    ren.AddActor(E.mat(frame_top, L7.TI_LAP,  diff=0.50, spec=0.92, pw=70, amb=0.05))
    ren.AddActor(E.mat(bright,    L7.TI_LAP,  diff=0.50, spec=0.92, pw=70, amb=0.05))
    lights = ([((fr.W / 2 - 900, CY - 250, -150), 1.25),
               ((fr.W / 2 + 500, CY + 300, -700), 0.26),
               ((fr.W / 2, CY, -900), 0.20)] if grazing else
              [((fr.W / 2 - 340, CY - 400, -430), 0.98),
               ((fr.W / 2 + 430, CY + 300, -420), 0.34),
               ((fr.W / 2 - 30, CY + 50, -900), 0.22)])
    for pos, i in lights:
        Lt = vtk.vtkLight()
        Lt.SetPosition(*pos)
        Lt.SetFocalPoint(fr.W / 2, fr.H / 2, 0.0)
        Lt.SetIntensity(i)
        Lt.SetLightTypeToSceneLight()
        ren.AddLight(Lt)
    cam = ren.GetActiveCamera()
    a, e = math.radians(az), math.radians(el)
    fx, fy = (fr.W / 2, CY) if crop else (fr.W / 2, fr.H / 2)
    cam.SetPosition(fx + dist * math.cos(e) * math.sin(a), fy - dist * math.sin(e),
                    -dist * math.cos(e) * math.cos(a))
    cam.SetFocalPoint(fx, fy, 0)
    cam.SetViewUp(0, -1, 0)
    cam.SetViewAngle(crop or 25)
    ren.ResetCameraClippingRange()
    rw.Render()
    w = vtk.vtkWindowToImageFilter()
    w.SetInput(rw)
    w.Update()
    arr = vtk_to_numpy(w.GetOutput().GetPointData().GetScalars())
    arr = arr.reshape(size, size, -1)[::-1, :, :3]
    bg = np.array(E.BG) * 255
    fg = np.abs(arr.astype(np.int16) - bg.astype(np.int16)).max(axis=2) > 6
    ys, xs = np.nonzero(fg)
    im = Image.fromarray(arr[max(0, ys.min() - 14):ys.max() + 15,
                             max(0, xs.min() - 14):xs.max() + 15])
    im = im.transpose(Image.FLIP_LEFT_RIGHT)
    im.save(path)
    return im


VARIANTS = [
    ("W-sunken-coin", "SUNKEN COIN", 0.25, True, True, None, CENTRE,
     "coin floor 0.25 into the field -> 0.40 walls; rim + ring + hoop + serial on the plane"),
    ("X-deep-coin", "DEEP COIN", 0.45, True, True, None, CENTRE,
     "coin floor 0.45 -> 0.60 walls, the full budget as shadow under the bright plane"),
    ("Y-bare-coin", "BARE COIN", 0.25, False, False, None, CENTRE,
     "no rim, no hoop -- text and serial alone; the recess wall is the only circle"),
    ("Z-rest-machined", "REST-MACHINED COIN", 0.45, True, True, 0.25, CENTRE_Z,
     "X's 0.60 field, W's counters: O0.4 to 0.45, then O0.3 ONLY where it couldn't go"),
]

if __name__ == "__main__":
    E.ensure_shell()
    E.SHELL = E.clip_back_face(E.shell_actor(), E.ART)
    made = []
    for key, title, coin_d, rim, hoop, rest_d, centre, sub in VARIANTS:
        f, gm, tops, webs, tool_r, rest_a = build_plane(coin_d, rim, hoop,
                                                        rest_d=rest_d, centre=centre)
        crest_a = float(tops.sum()) * PX * PX
        webs_a = float(webs.sum()) * PX * PX
        notes = [
            f"crest tops on the bearing plane: {crest_a:.0f} mm2 of lap contact "
            f"(plus the frame) -- small on purpose: scuffs land here and here alone, "
            f"and a minute on the plate restores them",
            f"coin floor {coin_d:.2f} into the field ({0.60 - coin_d:.2f} of ceiling "
            f"left); crest walls {PLANE + coin_d:.2f} from plane to floor, VERTICAL -- "
            f"milled islands, dia {2*tool_r:.1f} finisher at "
            f"{(PLANE + coin_d) / (2 * tool_r):.1f}xD",
        ]
        if rest_d is not None:
            notes.append(f"then the O0.3 rest-machines the {rest_a:.2f} mm2 the O0.4 "
                         f"could not enter, stopping at its own 1.3xD ({rest_d:.2f} "
                         f"into the field) -- counter floors sit {coin_d - rest_d:.2f} "
                         f"above the coin floor, HIDDEN inside the letterforms")
            notes.append(f"small caps up 1.40 -> 1.60 so their counters clear the O0.3; "
                         f"webs left at the plane after the cascade: {webs_a:.2f} mm2")
        else:
            notes.append(f"metal left AT THE PLANE the dia {2*tool_r:.1f} cannot enter "
                         f"(laps bright with the crests): {webs_a:.2f} mm2 -- the "
                         f"tightest counters read as solid marks")
        notes.append("machined as the frame is machined: crests are LEFT from stock "
                     "while the facing op cuts the field 0.15 and the coin sinks "
                     "around them")
        notes.append(f"DEEPEST CUT {PLANE + coin_d:.3f} below the plane -> coin floor "
                     f"{coin_d:.2f} below the field ({'within' if coin_d <= E.BUDGET + 1e-9 else 'PAST'} "
                     f"the {E.BUDGET:.2f} ceiling)")
        surf = plane_surfaces(f, tops)
        p1, p2 = f"{OUT}/spin8_{key}.png", f"{OUT}/spin8_{key}_graze.png"
        shot_plane(surf, p1)
        shot_plane(surf, p2, crop=15.0, grazing=True, az=2.0, el=5.0)
        made.append((title, sub, p1, p2, notes))
        print(f"=== {key}  {title}")
        for n in notes:
            print("    " + n)
        print(f"    wrote {os.path.basename(p1)}, {os.path.basename(p2)}\n")

    ims = [(t, s, Image.open(a).convert("RGB"), Image.open(b).convert("RGB"), n)
           for t, s, a, b, n in made]
    cw = max(max(a.width, b.width) for _t, _s, a, b, _n in ims)
    ch = max(max(a.height, b.height) for _t, _s, a, b, _n in ims)
    pad, head, gap, foot = 26, 104, 12, 340
    sheet = Image.new("RGB", (len(ims) * (cw + pad) + pad, head + ch * 2 + gap + foot),
                      (247, 247, 245))
    d = ImageDraw.Draw(sheet)
    ft, fs, fm = E.label_font(40), E.label_font(24), E.label_font(19)
    for i, (t, s, a, b, notes) in enumerate(ims):
        x = pad + i * (cw + pad)
        d.text((x, 16), t, font=ft, fill=(20, 20, 24))
        d.text((x, 64), s, font=fs, fill=(92, 92, 100))
        sheet.paste(a, (x + (cw - a.width) // 2, head))
        sheet.paste(b, (x + (cw - b.width) // 2, head + ch + gap))
        y = head + ch * 2 + gap + 16
        d.line([(x, y - 8), (x + cw - 6, y - 8)], fill=(206, 206, 202), width=2)
        for ln in notes:
            for w in E._wrap(ln, 74):
                d.text((x, y), w, font=fm,
                       fill=(70, 70, 78) if "DEEPEST" in ln else (118, 118, 126))
                y += 24
    d.text((pad, head + ch * 2 + gap + foot - 34),
           "SPIN 8 -- the bearing plane: crests at the frame's +0.15, so the whole part "
           "laps face-down on a plate. Bright = what the plate can touch. Nothing else can scuff.",
           font=fs, fill=(92, 92, 100))
    sheet.save(f"{OUT}/spin8_plane.png")
    print("wrote", f"{OUT}/spin8_plane.png", sheet.size)
