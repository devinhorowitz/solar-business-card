#!/usr/bin/env python3
"""Engraving, spin 9. Z is the architecture -- now WHAT DOES IT SAY.

Everything mechanical is settled and locked from spin 8's Z: bearing-plane crests,
rest-machined coin (O0.4 to 0.45, O0.3 rest pass at 0.25), rim + hoop furniture, ring at
R 10.8 cap 1.80, small caps 1.60. This spin only moves WORDS, applying three editorial
rulings:

  * THE YEAR APPEARS ONCE. Z said MMXXVI on the ring and in the dial; a coin says its
    year in one place.
  * SOLAR, NOT SOLAR POWERED. The claim is the word; POWERED was scaffolding. The
    13.56 MHz stays -- it is the one number on the back that is strictly useful (it
    tells a stranger what radio to expect).
  * THE VERSION NUMBER GOES. REV 4.0 beside No 001 mixed two counting systems: the
    BOARD is the fourth revision, but the OBJECT is the first one made. The board
    already wears its rev in copper and silk and the tag can report it digitally; the
    shell counts in one currency, the serial.

Because the ring's tracking is DERIVED (n characters into 360 deg), shorter strings get
airier letterspacing for free -- the density is part of what each candidate looks like,
so it is reported per variant:

  Z1 MINT      ring: SOLAR . NFC 13.56 MHz . ATLANTA GEORGIA     dial: No 001 / MMXXVI
               the full caseback grammar -- claim, radio, place around; serial and
               year minted in the middle
  Z2 MAKER     ring: SOLAR . NFC 13.56 MHz . DEVIN HOROWITZ      dial: No 001 / MMXXVI
               the medallion replaces the committed maker's mark, so the name takes
               the ring -- a signature you can feel
  Z3 PURE      ring: SOLAR . NFC 13.56 MHz . MMXXVI              dial: No 001
               the airiest ring and the strongest object statement: the one line that
               differs on every card sits alone in the dial
  Z4 MONOGRAM  ring: SOLAR . NFC 13.56 MHz . MMXXVI              dial: DRH / No 001
               the back answers the front's monogram -- the glow letters and the
               struck letters are the same three
"""
from __future__ import annotations

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

COIN_D, REST_D = 0.45, 0.25          # Z's cascade, locked

VARIANTS = [                     # (key, title, ring text, ring anchor, dial, why)
    ("Z1-mint", "MINT",
     "SOLAR · NFC 13.56 MHz · ATLANTA GEORGIA · ", "SOLAR",
     [("Nº 001", 2.40, -1.2, "b"), ("MMXXVI", 1.60, 2.6, "r")],
     "claim, radio and place around; serial and year minted in the middle -- the full "
     "caseback grammar"),
    ("Z2-maker", "MAKER",
     "SOLAR · NFC 13.56 MHz · DEVIN HOROWITZ · ", "SOLAR",
     [("Nº 001", 2.40, -1.2, "b"), ("MMXXVI", 1.60, 2.6, "r")],
     "the medallion replaces the committed maker's mark, so the name takes the ring -- "
     "a signature you can feel"),
    ("Z3-pure", "PURE",
     "SOLAR · NFC 13.56 MHz · MMXXVI · ", "SOLAR",
     [("Nº 001", 2.60, 0.6, "b")],
     "the airiest ring, the strongest object statement: the one line that differs on "
     "every card, alone in the dial"),
    ("Z4-monogram", "MONOGRAM",
     "SOLAR · NFC 13.56 MHz · MMXXVI · ", "SOLAR",
     [("DRH", 4.80, -1.6, "b"), ("Nº 001", 1.80, 3.0, "r")],
     "the back answers the front: the glow letters and the struck letters are the same "
     "three, serial beneath"),
    ("Z5-final", "Z4, SANS FREQUENCY",
     "SOLAR · NFC · MMXXVI · ", "SOLAR · NFC",
     [("DRH", 4.80, -1.6, "b"), ("Nº 001", 1.80, 3.0, "r")],
     "the frequency failed the test every other cut passed: NFC is a single-frequency "
     "standard, so 13.56 carried no information the word did not. Anchored on the "
     "PHRASE, the separators fall symmetric: SOLAR · NFC crowns the top arc and MMXXVI "
     "lands dead-centre at six o'clock"),
]

if __name__ == "__main__":
    E.ensure_shell()
    E.SHELL = E.clip_back_face(E.shell_actor(), E.ART)
    made = []
    for key, title, ring_txt, anchor, centre, why in VARIANTS:
        f, gm, tops, webs, tool_r, rest_a = Z.build_plane(
            COIN_D, True, True, rest_d=REST_D, centre=centre, ring_txt=ring_txt,
            ring_anchor=anchor)
        n = len(ring_txt)
        arc = 2 * 3.141592653589793 * Z.R_TEXT / n
        crest_a = float(tops.sum()) * PX * PX
        webs_a = float(webs.sum()) * PX * PX
        notes = [
            f"ring: {ring_txt.strip()}",
            f"dial: {'  /  '.join(t for t, _c, _dy, _w in centre)}",
            f"{n} chars into 360 deg -> {360.0/n:.2f} deg/char, {arc:.2f} mm cells "
            f"(glyphs ~1.02): {'airy, letterspaced' if arc > 1.8 else 'set close'}",
            f"crest tops {crest_a:.0f} mm2; webs after the O0.4 -> O0.3 cascade "
            f"{webs_a:.2f} mm2",
            "the year appears ONCE; POWERED is gone; REV is gone -- the board wears "
            "its own rev in copper, the shell counts in serials",
        ]
        surf = Z.plane_surfaces(f, tops)
        p1, p2 = f"{OUT}/spin9_{key}.png", f"{OUT}/spin9_{key}_graze.png"
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
                       fill=(70, 70, 78) if ln.startswith(("ring:", "dial:")) else (118, 118, 126))
                y += 24
    d.text((pad, head + ch * 2 + gap + foot - 34),
           "SPIN 9 -- Z's words. Architecture locked (bearing plane, rest-machined coin); "
           "only the text moves. Year once, SOLAR not SOLAR POWERED, no REV beside a serial.",
           font=fs, fill=(92, 92, 100))
    sheet.save(f"{OUT}/spin9_words.png")
    print("wrote", f"{OUT}/spin9_words.png", sheet.size)
