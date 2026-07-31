#!/usr/bin/env python3
"""Engraving, spin 6. Not new variants -- the FINISHING REALITY applied to the leaders.

Every render before this one shaded the machined floors as bright cut metal against the
bead-blasted face: two textures. That is real geometry but an unbuildable ORDER at a
prototype shop. PCBWay's flow (and every shop like it) is machine -> deburr -> ONE
terminal finish over the whole part; the menu (bead blast, brushed, polish, anodize,
blast+anodize colour) sequences within itself but never returns to the mill. Blast media
at 100-250 um reaches every 0.25-0.60 recess on this back, so floors, crests and grooves
come out ONE texture, and the engraving must read by GEOMETRY -- shadow and edge -- not
by surface contrast.

No workaround exists on this part. Selective masking at 0.8 mm scale is not a prototype
service, and the classic post-blast trick -- lap the top plane to re-brighten the crests
-- is blocked by the part's own bearing rule: the frame stands 0.15 proud of everything,
so a flat lap touches only the frame (the same fact that protects the crests from wear).

So this spin re-renders the four standing leaders under the finish they will actually
have -- uniform blast -- next to the as-cut two-tone the earlier sheets showed:

    M  registered relief, 0.60 deep      (walls carry the deepest shadow of the set)
    T  the v-carved ring                 (v-grooves: the classic single-finish engraving)
    U  ring relief, medallion, 0.25      (shoulder shadows only -- the honest stress test)
    V  ring relief, sunken band, 0.25    (same physics as U, kinder geometry)

The one-line change that makes it honest lives in spin 1: shot(..., uniform=True) shades
every surface in the blasted material. Nothing about the depth fields changes -- only the
lie about the floor's brightness.
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)

from PIL import Image, ImageDraw

import spin1_cutters as E
import spin3_reeded as R3
import spin4_provenance as P4
import spin5_t_relief as R5

OUT = E.OUT

CASES = [
    ("M-registered-deep", "M  REGISTERED, 0.60",
     "0.60 walls -- the deepest shadow here", R3, R3.v_registered_deep),
    ("T-ring", "T  RING, V-CARVED",
     "v-grooves: engraving's native single-finish form", P4, P4.v_ring),
    ("U-medallion-relief", "U  MEDALLION RELIEF",
     "0.25 shoulders, no texture help -- the stress test", R5, R5.v_medallion),
    ("V-band-relief", "V  SUNKEN-BAND RELIEF",
     "same 0.25 physics, kinder geometry", R5, R5.v_sunken_band),
]

if __name__ == "__main__":
    E.ensure_shell()
    E.SHELL = E.clip_back_face(E.shell_actor(), E.ART)
    made = []
    for key, title, sub, mod, fn in CASES:
        f, keep, _notes = mod.build(fn)
        surf = E.field_surfaces(f, keep)
        p0 = f"{OUT}/spin6_{key}_twotone.png"
        p1 = f"{OUT}/spin6_{key}_uniform.png"
        p2 = f"{OUT}/spin6_{key}_uniform_graze.png"
        E.shot(surf, p0)
        E.shot(surf, p1, uniform=True)
        E.shot(surf, p2, uniform=True, crop=15.0, grazing=True, az=2.0, el=5.0)
        made.append((title, sub, p0, p1, p2))
        print(f"    {key}: two-tone / uniform / uniform-graze written")

    ims = [(t, s, Image.open(a).convert("RGB"), Image.open(b).convert("RGB"),
            Image.open(c).convert("RGB")) for t, s, a, b, c in made]
    cw = max(max(a.width, b.width, c.width) for _t, _s, a, b, c in ims)
    ch = max(max(a.height, b.height, c.height) for _t, _s, a, b, c in ims)
    pad, head, cols, gap, lab, foot = 26, 116, 78, 30, 44, 64
    sheet = Image.new("RGB", (len(ims) * (cw + pad) + pad,
                              head + cols + (lab + ch + gap) * 3 + foot), (247, 247, 245))
    d = ImageDraw.Draw(sheet)
    ft, fs, fm = E.label_font(40), E.label_font(24), E.label_font(22)
    d.text((pad, 12), "ONE FINISH ONLY -- the shop blasts everything, once",
           font=ft, fill=(20, 20, 24))
    d.text((pad, 64), "machine -> deburr -> one terminal finish; nothing returns to the "
           "mill, so floors, crests and grooves come out ONE texture", font=fs,
           fill=(92, 92, 100))
    for i, entry in enumerate(ims):
        x = pad + i * (cw + pad)
        d.text((x, head + 6), entry[0], font=fs, fill=(20, 20, 24))
        d.text((x, head + 40), entry[1], font=fm, fill=(118, 118, 126))
    row_titles = ["AS-CUT TWO-TONE (real only until the finisher's cabinet)",
                  "UNIFORM BLAST -- diffuse", "UNIFORM BLAST -- raking"]
    for r, (idx, rt) in enumerate(zip([2, 3, 4], row_titles)):
        y0 = head + cols + r * (lab + ch + gap) + lab
        d.text((pad, y0 - lab + 8), rt, font=fs, fill=(70, 70, 78))
        for i, entry in enumerate(ims):
            im = entry[idx]
            x = pad + i * (cw + pad)
            sheet.paste(im, (x + (cw - im.width) // 2, y0))
    d.text((pad, head + cols + 3 * (lab + ch + gap) + 8),
           "Geometry is what survives: depth, walls, shadow. Texture contrast does not.",
           font=fs, fill=(92, 92, 100))
    sheet.save(f"{OUT}/spin6_finish.png")
    print("wrote", f"{OUT}/spin6_finish.png", sheet.size)
