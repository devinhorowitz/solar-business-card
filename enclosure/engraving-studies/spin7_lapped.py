#!/usr/bin/env python3
"""Engraving, spin 7. The finish spin 6 said no shop can order -- done AT HOME.

Spin 6 established the shop reality: one terminal finish, everything the same texture.
What it did not price is the bench: after the uniform bead blast, a SMALL HAND BLOCK
with fine-grit lapping film, worked inside the clear band, re-brightens the flat crests
against the dark blasted field. This is the classic caseback/coin finish, and this part
is unusually well built for it:

  * A full-part lap is impossible -- the frame stands 0.15 proud and takes the plate
    first. But that is the wrong tool anyway. The right tool is a block smaller than
    the clear band, and for THAT the part's own geometry is the fixture:
  * THE PROUD FEATURES ARE LAP STOPS. The frame (+0.15) and the fin ribs (+0.10) are
    both HIGHER than the engraving crests (0.00, the art-field plane). If the block
    strays off the band it rides up on ribs or frame and lifts clear of the crests --
    the medallion cannot be scratched by a wandering block, only abandoned. The
    failure mode is bright rib tops, which is a look, not a defect.
  * DEPTH IS NOT AT RISK. A film lap removes microns per session; the crests stand
    0.25 mm above their floors. The two-texture contrast survives hundreds of
    touch-ups, and a re-blast + re-lap resets it completely.

What lapping buys, per variant -- and it is not only for relief:

    U / V   bright standing letters, ring and serial against the dark sunken floor
            (the relief story spin 6 took away, restored by hand)
    M       bright DRH crests inside the dark 0.60 window
    T       the INVERSE: lap the flat dial around the v-carved text and the sunk
            letters stay dark in a bright disc -- dark-on-bright instead of
            bright-on-dark, same one blast + ten minutes of film

Rendered as a third finish state: blasted everywhere, bright ONLY on flush cells inside
the lap footprint (a disc over the medallion, the window rect for M). The footprint is
honest -- flush field OUTSIDE the worked area stays dark, because a hand block does not
brighten what it never touches.
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
from shapely.geometry import Point, box

import spin1_cutters as E
import spin3_reeded as R3
import spin4_provenance as P4
import spin5_t_relief as R5
import fit_rules as fr

OUT = E.OUT
CX, CY = E.CX, E.CY

TI_LAP = (0.950, 0.950, 0.970)      # film-lapped flat: near-mirror, the brightest thing here


def lapped_surfaces(f, keep, footprint, thr=0.015):
    """(dark flush, LAPPED flush, cut) -- field_surfaces split again by the lap footprint."""
    lap = f.raster(footprint)
    ok = keep[:-1, :-1] & keep[:-1, 1:] & keep[1:, 1:] & keep[1:, :-1]
    lo = f.z < thr
    flat = lo[:-1, :-1] & lo[:-1, 1:] & lo[1:, 1:] & lo[1:, :-1]
    lp = lap[:-1, :-1] & lap[:-1, 1:] & lap[1:, 1:] & lap[1:, :-1]
    return (E._sheet(f, ok & flat & ~lp), E._sheet(f, ok & flat & lp),
            E._sheet(f, ok & ~flat))


def shot3(surfaces, path, size=1500, az=5.0, el=13.0, dist=232.0, grazing=False, crop=None):
    """E.shot with the third material: blasted face, blasted cut, LAPPED crests."""
    ren = vtk.vtkRenderer()
    ren.SetBackground(*E.BG)
    rw = vtk.vtkRenderWindow()
    rw.SetOffScreenRendering(1)
    rw.AddRenderer(ren)
    rw.SetSize(size, size)
    dark, bright, cut = surfaces
    ren.AddActor(E.mat(E.SHELL, E.TI_BLAST, diff=0.88, spec=0.13, pw=16, amb=0.07))
    ren.AddActor(E.mat(dark,   E.TI_BLAST, diff=0.90, spec=0.04, pw=12, amb=0.07))
    ren.AddActor(E.mat(cut,    E.TI_BLAST, diff=0.90, spec=0.04, pw=12, amb=0.07))
    ren.AddActor(E.mat(bright, TI_LAP,     diff=0.50, spec=0.92, pw=70, amb=0.05))
    lights = ([((fr.W / 2 - 900, CY - 250, -150), 1.25),
               ((fr.W / 2 + 500, CY + 300, -700), 0.26),
               ((fr.W / 2, CY, -900), 0.20)] if grazing else
              [((fr.W / 2 - 340, CY - 400, -430), 0.98),
               ((fr.W / 2 + 430, CY + 300, -420), 0.34),
               ((fr.W / 2 - 30, CY + 50, -900), 0.22)])
    for pos, i in lights:
        L = vtk.vtkLight()
        L.SetPosition(*pos)
        L.SetFocalPoint(fr.W / 2, fr.H / 2, 0.0)
        L.SetIntensity(i)
        L.SetLightTypeToSceneLight()
        ren.AddLight(L)
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
    from vtk.util.numpy_support import vtk_to_numpy
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


DISC = Point(CX, CY).buffer(13.1, resolution=96)     # hand block's worked area, medallion
CASES = [
    ("M-registered-deep", "M  REGISTERED, 0.60",
     "bright DRH crests in the dark window",
     R3, R3.v_registered_deep, box(13.7, 39.6, 37.1, 48.2)),
    ("T-ring", "T  RING, V-CARVED",
     "the inverse: bright dial, sunk letters stay dark",
     P4, P4.v_ring, DISC),
    ("U-medallion-relief", "U  MEDALLION RELIEF",
     "the coin, restored: bright crests on dark floor",
     R5, R5.v_medallion, DISC),
    ("V-band-relief", "V  SUNKEN-BAND RELIEF",
     "bright letters + flush rings, dark band and dial",
     R5, R5.v_sunken_band, DISC),
]

if __name__ == "__main__":
    E.ensure_shell()
    E.SHELL = E.clip_back_face(E.shell_actor(), E.ART)
    made = []
    for key, title, sub, mod, fn, footprint in CASES:
        f, keep, _notes = mod.build(fn)
        surf = lapped_surfaces(f, keep, footprint)
        p1 = f"{OUT}/spin7_{key}_lapped.png"
        p2 = f"{OUT}/spin7_{key}_lapped_graze.png"
        shot3(surf, p1)
        shot3(surf, p2, crop=15.0, grazing=True, az=2.0, el=5.0)
        made.append((title, sub, p1, p2))
        print(f"    {key}: lapped renders written")

    ims = [(t, s, Image.open(a).convert("RGB"), Image.open(b).convert("RGB"))
           for t, s, a, b in made]
    cw = max(max(a.width, b.width) for _t, _s, a, b in ims)
    ch = max(max(a.height, b.height) for _t, _s, a, b in ims)
    pad, head, cols, gap, lab, foot = 26, 116, 78, 30, 44, 96
    sheet = Image.new("RGB", (len(ims) * (cw + pad) + pad,
                              head + cols + (lab + ch + gap) * 2 + foot), (247, 247, 245))
    d = ImageDraw.Draw(sheet)
    ft, fs, fm = E.label_font(40), E.label_font(24), E.label_font(22)
    d.text((pad, 12), "BLAST + HOME LAP -- the two-texture finish, recovered by hand",
           font=ft, fill=(20, 20, 24))
    d.text((pad, 64), "uniform bead blast from the shop, then fine-grit film on a small "
           "block, worked inside the clear band; the proud frame (+0.15) and ribs (+0.10) "
           "are built-in lap stops", font=fs, fill=(92, 92, 100))
    for i, (t, s, _a, _b) in enumerate(ims):
        x = pad + i * (cw + pad)
        d.text((x, head + 6), t, font=fs, fill=(20, 20, 24))
        d.text((x, head + 40), s, font=fm, fill=(118, 118, 126))
    for r, rt in enumerate(["BLAST + LAP -- diffuse", "BLAST + LAP -- raking"]):
        y0 = head + cols + r * (lab + ch + gap) + lab
        d.text((pad, y0 - lab + 8), rt, font=fs, fill=(70, 70, 78))
        for i, entry in enumerate(ims):
            im = entry[2 + r]
            x = pad + i * (cw + pad)
            sheet.paste(im, (x + (cw - im.width) // 2, y0))
    d.text((pad, head + cols + 2 * (lab + ch + gap) + 8),
           "Crests stand 0.25 above their floors; a film lap removes microns per session -- "
           "the contrast survives hundreds of touch-ups, and re-blast + re-lap resets it.",
           font=fs, fill=(92, 92, 100))
    sheet.save(f"{OUT}/spin7_lapped.png")
    print("wrote", f"{OUT}/spin7_lapped.png", sheet.size)
