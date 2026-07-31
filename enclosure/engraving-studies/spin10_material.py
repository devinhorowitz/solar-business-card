#!/usr/bin/env python3
"""Engraving, spin 10. The ring earns the metal by NAMING it -- and stays agnostic.

Two rulings from the user, folded together:

  * CALL OUT THE MATERIAL. Watches do, and here it is the whole story -- this run
    happens in titanium exactly once. TITANIUM spelled, or Ti, the symbol.
  * STAY AGNOSTIC. The next person should be able to drop in their own facts and have
    them "neatly fit correctly". The ring machinery already guarantees this: tracking
    is DERIVED (n characters into 360 deg), so any string re-closes the circle. What
    this spin adds is the measured envelope, so the promise is a contract:

      at R 10.8 / cap 1.80 the ring accepts up to 47 CHARACTERS before adjacent
      letters choke the O0.4 (cell >= 1.02 glyph + 0.40 tool = 1.42 mm); below ~20 the
      air goes slack. ATL GA fits. NY NY fits. SAN FRANCISCO CA, in the longest
      wording here, lands at exactly 47 -- the envelope holds every plausible city.

    The dial has the same contract: 2-4 initials fit at cap <= 13/(0.822 x n), and the
    serial is one text substitution per unit. When this graduates to the generator,
    RING_TEXT / RING_ANCHOR / DIAL_MONOGRAM / SERIAL become its parameters.

Architecture locked from spin 8 Z (bearing plane, rest-machined coin, rim + hoop); dial
locked from the Z4 pick (DRH over No 001); the frequency stays gone (NFC is
single-frequency -- the number carried nothing the word did not). Only the ring moves:

  Z6  MATERIAL, SPELLED   SOLAR . NFC . TITANIUM . MMXXVI
  Z7  MATERIAL, SYMBOL    SOLAR . NFC . Ti . MMXXVI          (the watch shorthand)
  Z8  FULL EPITAPH        SOLAR . NFC . Ti . ATL GA . MMXXVI (power, radio, metal,
                                                              place, year -- all of it)
  Z9  SPELLED + PLACE     SOLAR . NFC . TITANIUM . ATL GA . MMXXVI (the dense limit)
"""
from __future__ import annotations

import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)

from PIL import Image, ImageDraw

import spin1_cutters as E
import spin8_plane as Z

OUT = E.OUT
PX = E.PX

COIN_D, REST_D = 0.45, 0.25
DIAL = [("DRH", 4.80, -1.6, "b"), ("Nº 001", 1.80, 3.0, "r")]

VARIANTS = [
    ("Z6-ti-spelled", "MATERIAL, SPELLED",
     "SOLAR · NFC · TITANIUM · MMXXVI · ", "SOLAR · NFC",
     "the watch move at full length: the metal named in the metal, year opposite"),
    ("Z7-ti-symbol", "MATERIAL, SYMBOL",
     "SOLAR · NFC · Ti · MMXXVI · ", "SOLAR · NFC",
     "the chemist's shorthand watches also use -- two characters of lowercase in a ring "
     "of caps, quietly correct"),
    ("Z8-full-epitaph", "FULL EPITAPH",
     "SOLAR · NFC · Ti · ATL GA · MMXXVI · ", "SOLAR · NFC · Ti",
     "power, radio, metal, place, year -- everything the object is, one orbit; the "
     "symbol keeps room for the city"),
    ("Z9-spelled-place", "SPELLED + PLACE",
     "SOLAR · NFC · TITANIUM · ATL GA · MMXXVI · ", "SOLAR · NFC",
     "the dense limit: TITANIUM and the city both spelled into a 43-character ring, "
     "Z1's density with better words"),
]

if __name__ == "__main__":
    E.ensure_shell()
    E.SHELL = E.clip_back_face(E.shell_actor(), E.ART)
    adv = 1.02
    n_max = int((2 * math.pi * Z.R_TEXT) // (adv + 2 * 0.20))
    made = []
    for key, title, ring_txt, anchor, why in VARIANTS:
        f, gm, tops, webs, tool_r, rest_a = Z.build_plane(
            COIN_D, True, True, rest_d=REST_D, centre=DIAL, ring_txt=ring_txt,
            ring_anchor=anchor)
        n = len(ring_txt)
        arc = 2 * math.pi * Z.R_TEXT / n
        crest_a = float(tops.sum()) * PX * PX
        webs_a = float(webs.sum()) * PX * PX
        notes = [
            f"ring: {ring_txt.strip()}   (anchor: {anchor} at 12 o'clock)",
            f"{n} chars into 360 deg -> {360.0/n:.2f} deg/char, {arc:.2f} mm cells; the "
            f"envelope runs ~20..{n_max} chars at this radius before the O0.4 chokes "
            f"between letters -- SAN FRANCISCO CA in Z8's wording lands at {n_max} exactly",
            f"crest tops {crest_a:.0f} mm2; webs after the cascade {webs_a:.2f} mm2",
            "agnostic by construction: ring text, anchor, dial initials and serial are "
            "the four parameters; any string re-closes the circle at its own tracking",
        ]
        surf = Z.plane_surfaces(f, tops)
        p1, p2 = f"{OUT}/spin10_{key}.png", f"{OUT}/spin10_{key}_graze.png"
        Z.shot_plane(surf, p1)
        Z.shot_plane(surf, p2, crop=15.0, grazing=True, az=2.0, el=5.0)
        made.append((title, why, p1, p2, notes))
        print(f"=== {key}  {title}")
        for ln in notes:
            print("    " + ln)
        print(f"    wrote {os.path.basename(p1)}, {os.path.basename(p2)}\n")

    ims = [(t, s, Image.open(a).convert("RGB"), Image.open(b).convert("RGB"), nn)
           for t, s, a, b, nn in made]
    cw = max(max(a.width, b.width) for _t, _s, a, b, _n in ims)
    ch = max(max(a.height, b.height) for _t, _s, a, b, _n in ims)
    pad, head, gap, foot = 26, 104, 12, 300
    sheet = Image.new("RGB", (len(ims) * (cw + pad) + pad, head + ch * 2 + gap + foot),
                      (247, 247, 245))
    d = ImageDraw.Draw(sheet)
    ft, fs, fm = E.label_font(40), E.label_font(24), E.label_font(19)
    for i, (t, s, a, b, notes) in enumerate(ims):
        x = pad + i * (cw + pad)
        d.text((x, 16), t, font=ft, fill=(20, 20, 24))
        for j, w in enumerate(E._wrap(s, 58)[:2]):
            d.text((x, 60 + 22 * j), w, font=fm, fill=(92, 92, 100))
        sheet.paste(a, (x + (cw - a.width) // 2, head))
        sheet.paste(b, (x + (cw - b.width) // 2, head + ch + gap))
        y = head + ch * 2 + gap + 16
        d.line([(x, y - 8), (x + cw - 6, y - 8)], fill=(206, 206, 202), width=2)
        for ln in notes:
            for w in E._wrap(ln, 74):
                d.text((x, y), w, font=fm,
                       fill=(70, 70, 78) if ln.startswith("ring:") else (118, 118, 126))
                y += 24
    d.text((pad, head + ch * 2 + gap + foot - 34),
           "SPIN 10 -- the material named in the metal, and the agnostic contract: any "
           "string 20-47 chars re-closes the ring at its own tracking. Dial locked: DRH / No 001.",
           font=fs, fill=(92, 92, 100))
    sheet.save(f"{OUT}/spin10_material.png")
    print("wrote", f"{OUT}/spin10_material.png", sheet.size)
