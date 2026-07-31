#!/usr/bin/env python3
"""Engraving, spin 5. One question: T's ring, set in RELIEF.

Spin 4's T cut the ring text INTO the back. This spin turns it around -- the letters left
standing while the metal around them comes out -- because relief is what the studies keep
converging on (C -> I -> M) and the ring is the composition the caseback idiom keeps
converging on. Two honest readings of "the ring in relief", built side by side:

  U MEDALLION   one disc recessed, everything stands from ONE floor: the rim shoulder,
                the ring text, a hoop separating band from dial, and the serial stack.
                The strongest object-quality -- the whole medallion is a coin.
  V SUNKEN BAND only the text band and the serial dial recess; the border rings stay
                FLUSH, as shoulders between the two recesses. No free-standing thin
                feature anywhere -- every ridge is a plateau between pockets, which is
                the kindest possible geometry to machine and to refinish.

THE DEPTH IS 0.25 AND THE RING'S OWN GEOMETRY SAYS SO. The tapered cutter that makes
relief crisp (I/M) flares depth x tan(15 deg) into every standing edge. At cap 1.80 the
ring cells advance 2*pi*R/41 = 1.66 mm and the ink is ~1.1 wide, so adjacent letters
stand ~0.55 apart. At 0.60 deep the two facing flares take 2 x 0.161 = 0.32 of that 0.55
and the letters fuse at the base; at 0.25 they take 2 x 0.067 and the gaps survive. The
doubled budget spin 3 priced is real -- but cap-1.8 relief cannot spend it. (M spends it
at cap 4.4, where the flare is noise.)

Everything else -- ring_text's derived tracking, the per-character H-reference cells, the
serial-in-the-dial centre, the tool physics -- is imported from spins 1/2/4 unchanged.
"""
from __future__ import annotations

import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)

import numpy as np
from PIL import Image, ImageDraw
from shapely.geometry import Point
from shapely.ops import unary_union

import spin1_cutters as E
import spin2_composition as C
import spin4_provenance as P4
import fit_rules as fr

OUT = E.OUT
CX, CY, ART = E.CX, E.CY, E.ART

R_TEXT, CAP = 10.8, 1.80
TXT = "SOLAR POWERED · NFC 13.56 MHz · MMXXVI · "
DEPTH, R_TIP, TAPER = 0.25, 0.10, 15.0

CENTRE = [("Nº 001", 2.40, -1.6, "b"),
          ("REV 4.0", 1.40, 2.0, "r"),
          ("MMXXVI", 1.40, 4.4, "r")]


def _disc(r):
    return Point(CX, CY).buffer(r, resolution=128)


def _annulus(r0, r1):
    return _disc(r1).difference(_disc(r0))


def _centre_glyphs():
    return unary_union([E.line_geom(t, CX, CY + dy, cap, w) for t, cap, dy, w in CENTRE])


def _flare_note():
    ink = P4.char_cell("H", CAP).bounds
    adv = 2 * math.pi * R_TEXT / len(TXT)
    gap = adv - (ink[2] - ink[0])
    f060 = 2 * 0.60 * math.tan(math.radians(TAPER))
    f025 = 2 * DEPTH * math.tan(math.radians(TAPER))
    return (f"why 0.25, not the 0.60 budget: cells advance {adv:.2f}, ink {ink[2]-ink[0]:.2f} "
            f"-> letters stand {gap:.2f} apart; facing flares take {f060:.2f} of that at "
            f"0.60 (fused) vs {f025:.2f} at {DEPTH:.2f} (clear)")


def v_medallion(f):
    """U -- one disc recessed, rim + ring text + hoop + serial all standing from one floor."""
    ring, dphi = P4.ring_text(TXT, R_TEXT, CAP)
    glyph = unary_union([ring, _annulus(8.75, 9.25), _centre_glyphs()])
    panel = _disc(12.85)
    P4._check(panel.buffer(0.1), "U", margin=0.15)
    pm, gm = f.raster(panel), f.raster(glyph)
    reach, miss, flare = C.relief_taper(f, pm, gm, DEPTH, R_TIP, TAPER)
    notes = [
        f"one Ø{2*12.85:.1f} disc down {DEPTH:.2f} over {f.area(reach):.0f} mm2; rim "
        f"shoulder, ring text, Ø18.0-18.5 hoop and serial stack all stand from one floor",
        f"{len(TXT)} chars at {dphi:.2f} deg -- T's derived tracking, letters now PROUD",
        f"standing letters keep the bead-blast; the floor mills bright -- C's two-texture "
        f"contrast on a coin",
        f"metal the Ø0.2 tip cannot reach, left webbing the letters: {f.area(miss):.3f} mm2"
        + ("" if not miss.any() else f", widest blob {f.widest(miss):.3f} mm "
           f"(the 0/6/R counters at cap 1.4-1.8 -- they read as solid digits)"),
        f"flare at every standing base: {flare*1000:.0f} um",
        _flare_note(),
    ]
    return notes, DEPTH


def v_sunken_band(f):
    """V -- band and dial recess; the border rings stay flush as plateau shoulders."""
    ring, _dphi = P4.ring_text(TXT, R_TEXT, CAP)
    panel = unary_union([_annulus(9.15, 12.55), _disc(8.65)])
    glyph = unary_union([ring, _centre_glyphs()])
    P4._check(panel.buffer(0.1), "V", margin=0.15)
    pm, gm = f.raster(panel), f.raster(glyph)
    reach, miss, flare = C.relief_taper(f, pm, gm, DEPTH, R_TIP, TAPER)
    notes = [
        f"two recesses -- band Ø{2*9.15:.1f}-{2*12.55:.1f} and dial Ø{2*8.65:.1f} -- "
        f"down {DEPTH:.2f} over {f.area(reach):.0f} mm2; the 0.50 ring between them and "
        f"the outer field stay FLUSH",
        "no free-standing thin feature anywhere: every ridge is a plateau between "
        "pockets -- the kindest relief geometry to machine and to refinish",
        f"unreachable webs: {f.area(miss):.3f} mm2"
        + ("" if not miss.any() else f", widest blob {f.widest(miss):.3f} mm"),
        f"flare at every standing base: {flare*1000:.0f} um",
        _flare_note(),
    ]
    return notes, DEPTH


VARIANTS = [
    ("U-medallion-relief", "RING RELIEF / MEDALLION", "one disc recessed, all standing from one floor",
     v_medallion,
     "T turned inside out at its strongest: the whole Ø25.7 medallion is a coin struck "
     "in the back -- rim, ring text, hoop and serial all proud of one bright floor, all "
     "keeping the blasted face on their crests."),
    ("V-band-relief", "RING RELIEF / SUNKEN BAND", "band + dial recess, flush shoulder rings",
     v_sunken_band,
     "The watch answer. Raised lettering in a sunken band, serial raised in a sunken "
     "dial, and the rings between them are not features -- they are simply the metal "
     "the pockets did not take. Nothing thin stands alone."),
]


def build(fn):
    f = E.Field(ART, pad=0.0)
    notes, deepest = fn(f)
    notes.append(f"DEEPEST CUT {deepest:.3f} mm -> {E.FLOOR - deepest:.3f} mm floor left "
                 f"({'within' if deepest <= E.BUDGET + 1e-9 else 'PAST'} the {E.BUDGET:.2f} mm "
                 f"the fin valleys already take)")
    return f, np.ones(f.z.shape, bool), notes


if __name__ == "__main__":
    E.ensure_shell()
    E.SHELL = E.clip_back_face(E.shell_actor(), ART)
    print(f"art rect {ART}, centre ({CX:.2f}, {CY:.2f})\n")
    made = []
    for key, title, sub, fn, why in VARIANTS:
        f, keep, notes = build(fn)
        print(f"=== {key}  {title} -- {sub}")
        for n in notes:
            print("    " + n)
        surf = E.field_surfaces(f, keep)
        p1, p2 = f"{OUT}/spin5_{key}.png", f"{OUT}/spin5_{key}_graze.png"
        E.shot(surf, p1)
        E.shot(surf, p2, crop=15.0, grazing=True, az=2.0, el=5.0)
        made.append((title, sub, p1, p2, notes))
        print(f"    wrote {os.path.basename(p1)}, {os.path.basename(p2)}\n")

    ims = [(t, s, Image.open(a).convert("RGB"), Image.open(b).convert("RGB"), n)
           for t, s, a, b, n in made]
    cw = max(max(a.width, b.width) for _t, _s, a, b, _n in ims)
    ch = max(max(a.height, b.height) for _t, _s, a, b, _n in ims)
    pad, head, gap, foot = 26, 104, 12, 380
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
                       fill=(70, 70, 78) if "DEEPEST" in ln or "why 0.25" in ln
                       else (118, 118, 126))
                y += 24
    d.text((pad, head + ch * 2 + gap + foot - 34),
           "SPIN 5 -- T's ring in relief: letters standing, field milled bright. Tapered "
           "Ø0.2 cutter; depth capped at 0.25 by the ring's own letter gaps, not by the part.",
           font=fs, fill=(92, 92, 100))
    sheet.save(f"{OUT}/spin5_t_relief.png")
    print("wrote", f"{OUT}/spin5_t_relief.png", sheet.size)
