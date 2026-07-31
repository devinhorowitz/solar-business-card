#!/usr/bin/env python3
"""One sheet, every study: the twenty variants of spins 1-4 in a 4 x 5 grid.

Reads the diffuse-light render of each variant out of $ENGRAVE_OUT and lays them out one
spin per row, titles pulled from each spin module's own VARIANTS list so the sheet can
never drift from the scripts. Run the four spins first -- this composes, it does not
render:

    for s in spin1_cutters spin2_composition spin3_reeded spin4_provenance; do
        python3 enclosure/engraving-studies/$s.py
    done
    python3 enclosure/engraving-studies/all_studies.py     # -> $ENGRAVE_OUT/all_studies.png

Like every render here, the output stays OUTSIDE the repo (consistency check [9]).
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)

from PIL import Image, ImageDraw

import spin1_cutters as E
import spin2_composition as C
import spin3_reeded as R3
import spin4_provenance as R4
import spin5_t_relief as R5
import spin8_plane as R8
import spin9_words as R9
import spin10_material as R10

OUT = E.OUT

ROWS = [
    ("SPIN 1 -- WHICH CUTTER", "spin1", [(v["key"], v["title"]) for v in E.VARIANTS]),
    ("SPIN 2 -- COMPOSITION, HIERARCHY, REGISTRATION", "spin2",
     [(k, t) for k, t, *_ in C.VARIANTS]),
    ("SPIN 3 -- MEETING THE FINE REEDING", "spin3",
     [(k, t) for k, t, *_ in R3.VARIANTS]),
    ("SPIN 4 -- PROVENANCE: WHAT THE BACK SAYS", "spin4",
     [(k, t) for k, t, *_ in R4.VARIANTS]),
    ("SPIN 5 -- T IN RELIEF", "spin5",
     [(k, t) for k, t, *_ in R5.VARIANTS]),
    ("SPIN 8 -- THE BEARING PLANE (the gameplan; 6-7 are finish states, not variants)",
     "spin8", [(k, t) for k, t, *_ in R8.VARIANTS]),
    ("SPIN 9 -- Z'S WORDS", "spin9", [(k, t) for k, t, *_ in R9.VARIANTS]),
    ("SPIN 10 -- THE MATERIAL, NAMED; THE RING, AGNOSTIC", "spin10",
     [(k, t) for k, t, *_ in R10.VARIANTS]),
]

TH = 620            # uniform thumbnail height
PAD, BAND, CAP = 22, 64, 46
BG, INK, DIM = (247, 247, 245), (20, 20, 24), (98, 98, 106)

if __name__ == "__main__":
    cells = []
    for label, pref, variants in ROWS:
        row = []
        for key, title in variants:
            p = f"{OUT}/{pref}_{key}.png"
            if not os.path.exists(p):
                raise SystemExit(f"missing {p} -- run {pref}'s script first")
            im = Image.open(p).convert("RGB")
            im = im.resize((round(im.width * TH / im.height), TH), Image.LANCZOS)
            row.append((f"{key.split('-')[0]}  {title}", im))
        cells.append((label, row))

    cw = max(im.width for _l, row in cells for _t, im in row) + PAD
    ncol = max(len(row) for _l, row in cells)
    rowh = BAND + TH + CAP
    sheet = Image.new("RGB", (ncol * cw + PAD, len(cells) * rowh + PAD + 60), BG)
    d = ImageDraw.Draw(sheet)
    f_band, f_cap, f_foot = E.label_font(34), E.label_font(24), E.label_font(22)
    for r, (label, row) in enumerate(cells):
        y0 = PAD + r * rowh
        d.text((PAD, y0 + 10), label, font=f_band, fill=INK)
        d.line([(PAD, y0 + BAND - 8), (ncol * cw - PAD, y0 + BAND - 8)],
               fill=(206, 206, 202), width=2)
        for c, (title, im) in enumerate(row):
            x = PAD + c * cw + (cw - PAD - im.width) // 2
            sheet.paste(im, (x, y0 + BAND))
            d.text((PAD + c * cw, y0 + BAND + TH + 10), title, font=f_cap, fill=DIM)
    d.text((PAD, len(cells) * rowh + PAD + 8),
           "SOLAR-GLOW DRH -- back-shell engraving studies, spins 1-4. Every panel is a real "
           "tool's depth field at 25 um on the real finned shell STL, diffuse light.",
           font=f_foot, fill=DIM)
    sheet.save(f"{OUT}/all_studies.png")
    print("wrote", f"{OUT}/all_studies.png", sheet.size)
