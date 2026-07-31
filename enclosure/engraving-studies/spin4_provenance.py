#!/usr/bin/env python3
"""Engraving, spin 4. Same part, same tools -- different WORDS: provenance.

Spins 1-3 all engraved the contact block, because the back's first candidate content was
"who". Spin 4 asks about "what": the things a maker puts on a caseback -- what powers it,
what it speaks, which revision, which unit, which year. Content is orthogonal to
technique: any variant here can be cut with any cutter from spin 1, at any depth spin 3
priced. What these five settle is what the back SAYS, and the facts they say are pulled
from the part where possible rather than typed:

  P CASEBACK    the watch idiom: a centred epitaph stack. Power, radio, revision, unit,
                year, place -- six short lines, one V-bit.
  Q SPEC PLATE  the industrial idiom: a framed data plate with label/value rows and
                rules, all cut by the same bit in one setup (J's argument, applied to
                different words).
  R MARKS       the icon idiom: the SAME contactless waves the front mask art carries --
                imported from scripts/mask_art.py's own generator, not redrawn -- beside
                a sun glyph, over two short lines. The card says what it is without a
                sentence.
  S PROVENANCE LINE  the restraint idiom: the committed maker's mark keeps its slot, its
                caps and its bold name line; only "DESIGNED & MADE BY" swaps for a
                provenance line. The smallest possible change to the shipped part.
  T RING        the caseback ring: text on a closed circle around a serial-number
                centre. The tracking is derived, not chosen -- n chars into 360 deg --
                so the ring closes exactly, the same exact-closure move as the fins.

Serial numbers are VARIABLE DATA: "No 001" is one engraved line that changes per unit
while every other stroke is shared. On a CNC'd cut file that is one text substitution per
part; the studies carry unit 001.

Machinery: tool models / Field / render from spin 1, layout and stack from spin 2. The
ring needs one new trick: _maker_text normalises each STRING's bounds to the cap height,
so a lone "." would blow up into a 2 mm boulder. Every ring character is therefore built
as the pair "H"+ch -- the H pins the scale and the vertical frame -- and only the second
cell's ink is kept.
"""
from __future__ import annotations

import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.dirname(HERE))     # enclosure/, for fit_rules
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "scripts"))   # for mask_art's nfc glyph

import numpy as np
import shapely.affinity as aff
from PIL import Image, ImageDraw
from shapely.geometry import Point, box
from shapely.ops import unary_union

import spin1_cutters as E
import spin2_composition as C
import fit_rules as fr
from mask_art import nfc_mark

OUT = E.OUT
PX = E.PX
CX, CY, ART = E.CX, E.CY, E.ART


def _check(geom, key, margin=0.3):
    b = geom.bounds
    if not (ART[0] + margin <= b[0] and b[2] <= ART[2] - margin
            and ART[1] + margin <= b[1] and b[3] <= ART[3] - margin):
        raise SystemExit(f"{key}: block x[{b[0]:.2f},{b[2]:.2f}] y[{b[1]:.2f},{b[3]:.2f}] "
                         f"leaves the art rect {ART}")


# --- per-character cells, for text that is not set on a line ------------------------

def _advance(cap, weight):
    """The monospace advance at this cap height, measured from the font itself."""
    w2 = E.NS["_maker_text"]("HH", 0.0, 0.0, cap, E.FONT[weight]).bounds
    w3 = E.NS["_maker_text"]("HHH", 0.0, 0.0, cap, E.FONT[weight]).bounds
    return (w3[2] - w3[0]) - (w2[2] - w2[0])


def char_cell(ch, cap, weight="r", min_island=None):
    """One character, upright in board coords, centred on the origin, at true cap scale.

    Built as the pair "H"+ch so the H pins the scale (the generator's _maker_text
    normalises the string bounds to the cap height -- alone, a mid-dot becomes a
    boulder) and pins the vertical frame (the dot stays at mid-x-height instead of
    being re-centred). Only the second cell's ink is returned.

    min_island is the BEARING-PLANE machining rule (spin 10): a detached island
    smaller than this in both dimensions -- an interpunct, a tittle -- would stand as
    an orphan post 0.60 tall, under the shop's ~0.5 min-feature floor. Any such part
    is regrown as a round of exactly min_island at its own centroid: same mark, legal
    post. Letters are connected forms and pass untouched.
    """
    if ch == " ":
        return None
    pair = E.NS["_maker_text"]("H" + ch, 0.0, 0.0, cap, E.FONT[weight])
    if pair is None:
        return None
    b = pair.bounds
    g = aff.scale(pair, xfact=1, yfact=-1, origin=(0, (b[1] + b[3]) / 2.0))
    h_ink = E.NS["_maker_text"]("H", 0.0, 0.0, cap, E.FONT[weight]).bounds
    x_split = b[0] + (h_ink[2] - h_ink[0]) + 0.05
    polys = list(g.geoms) if g.geom_type.startswith("Multi") else [g]
    keep = [p for p in polys if p.centroid.x > x_split]
    if not keep:
        return None
    if min_island:
        from shapely.geometry import Point as _Pt
        keep = [(_Pt(p.centroid).buffer(min_island / 2.0, resolution=32)
                 if (p.bounds[2] - p.bounds[0]) < min_island
                 and (p.bounds[3] - p.bounds[1]) < min_island else p)
                for p in keep]
    gk = unary_union(keep)
    kb = gk.bounds
    return aff.translate(gk, -(kb[0] + kb[2]) / 2.0, -(b[1] + b[3]) / 2.0)


def ring_text(txt, R, cap, weight="r", word_top="SOLAR POWERED", min_island=None):
    """Text on a closed circle: n characters into 360 deg, tracking derived not chosen.

    Clockwise reading, each character upright on its own radial (top of the letter
    points outward). The seam is invisible because the closure is exact -- the same move as the
    fin layout. `word_top` centres that word on 12 o'clock.
    """
    n = len(txt)
    dphi = 360.0 / n
    i0 = txt.index(word_top) + (len(word_top) - 1) / 2.0 if word_top in txt else 0.0
    parts = []
    for i, ch in enumerate(txt):
        c = char_cell(ch, cap, weight, min_island)
        if c is None:
            continue
        phi = (i - i0) * dphi
        c = aff.rotate(c, phi, origin=(0, 0))
        rad = math.radians(phi)
        parts.append(aff.translate(c, R * math.sin(rad), -R * math.cos(rad)))
    g = aff.translate(unary_union(parts), CX, CY)
    return aff.scale(g, xfact=-1, yfact=1, origin=(fr.W / 2.0, fr.H / 2.0)), dphi


def circle_rule(R, w=0.28):
    return (Point(CX, CY).buffer(R + w / 2.0, resolution=128)
            .difference(Point(CX, CY).buffer(R - w / 2.0, resolution=128)))


def sun_glyph(s=1.0):
    """A sun: ring + 8 rays, strokes sized for the 60 deg bit to reach full depth."""
    ring = (Point(0, 0).buffer(2.05 * s, resolution=64)
            .difference(Point(0, 0).buffer(1.45 * s, resolution=64)))
    rays = []
    for k in range(8):
        a = math.radians(k * 45.0)
        r0, r1, w = 2.75 * s, 4.05 * s, 0.60 * s
        ln = box(r0, -w / 2, r1, w / 2)
        rays.append(aff.rotate(ln, math.degrees(a), origin=(0, 0)))
    return unary_union([ring] + rays)


def left_at(g, x):
    """Reading-left edge at x, in the machining mirror's frame."""
    b = g.bounds
    return aff.translate(g, (fr.W - x) - b[2], 0.0)


# --- variants -----------------------------------------------------------------------

def v_caseback(f):
    """P -- the watch caseback epitaph: six centred lines, one V-bit."""
    lines = [("SOLAR-GLOW · DRH",            2.30, "b", 0.00),
             ("INDOOR SOLAR · 1 F 5.5 V",    1.60, "r", 1.60),
             ("NFC 13.56 MHz · TAP TO WAKE", 1.60, "r", 1.10),
             ("REV 4.0 · Nº 001 · MMXXVI",   1.60, "r", 1.10),
             ("ATLANTA, GEORGIA",            1.40, "r", 1.45)]
    notes = ["the caseback idiom: what powers it, what it speaks, which revision, "
             "which unit, which year -- everything a maker owes the object"]
    placed = C.stack(lines, CX, CY, "centre")
    _check(unary_union([ln["geom"] for ln in placed]), "P")
    for ln in placed:
        got = f.vee(f.raster(ln["geom"]), 0.25, 60.0, 0.10)
        notes.append(f"{ln['txt'][:30]:<30} cap {ln['cap']:4.2f}  cut {got:.3f} mm")
    notes.append("Nº 001 is variable data -- one text substitution per unit in the cut "
                 "file; every other stroke is shared across the run")
    return notes, 0.25


def v_spec_plate(f):
    """Q -- the industrial data plate: label/value rows, rules and text one bit."""
    RECT = (11.0, 35.1, 39.8, 53.7)
    rows = [("MODEL", "SOLAR-GLOW DRH"),
            ("REV",   "4.0 / 0P6B"),
            ("SER",   "Nº 0001"),
            ("PWR",   "SOLAR 1F 5.5V"),
            ("RF",    "NFC 13.56 MHz"),
            ("YEAR",  "MMXXVI / 2026")]
    rh = (RECT[3] - RECT[1]) / len(rows)
    frame = aff.scale(C.frame(RECT, 0.34, 1.0), xfact=-1, yfact=1,
                      origin=(fr.W / 2.0, fr.H / 2.0))
    got_f = f.vee(f.raster(frame), 0.22, 60.0, 0.10)
    notes = [f"plate {RECT[2]-RECT[0]:.1f} x {RECT[3]-RECT[1]:.1f} mm, {len(rows)} rows "
             f"of {rh:.2f}; frame 0.34 cut {got_f:.3f}"]
    rules = [C.rule(RECT[0] + 0.17, RECT[2] - 0.17, RECT[1] + rh * i, 0.30)
             for i in range(1, len(rows))]
    rules.append(box(18.8 - 0.15, RECT[1] + 0.17, 18.8 + 0.15, RECT[3] - 0.17))
    g = aff.scale(unary_union(rules), xfact=-1, yfact=1, origin=(fr.W / 2.0, fr.H / 2.0))
    got_r = f.vee(f.raster(g), 0.22, 60.0, 0.10)
    notes.append(f"{len(rows)-1} row rules + 1 column rule, 0.30 wide, cut {got_r:.3f} "
                 f"-- rules, frame and text are the same 60 deg bit, one setup")
    for i, (lab, val) in enumerate(rows):
        ymid = RECT[1] + rh * (i + 0.5)
        gl = left_at(E.line_geom(lab, CX, ymid, 1.30, "r"), 12.2)
        gv = left_at(E.line_geom(val, CX, ymid, 1.55, "r"), 20.0)
        assert fr.W - gv.bounds[0] < RECT[2] - 0.8, f"Q: value '{val}' overruns the plate"
        dl = f.vee(f.raster(gl), 0.22, 60.0, 0.10)
        dv = f.vee(f.raster(gv), 0.22, 60.0, 0.10)
        notes.append(f"{lab:<6} {val:<15} label cut {dl:.3f} / value cut {dv:.3f}")
    return notes, 0.22


def v_marks(f):
    """R -- iconography: the front mask's own NFC waves + a sun, over two lines."""
    s = 1.29                                   # waves scaled to match the sun's height
    waves = nfc_mark()                         # mask_art's glyph, verbatim
    wb = waves.bounds
    waves = aff.translate(aff.scale(waves, xfact=s, yfact=s, origin=(wb[0], (wb[1] + wb[3]) / 2)),
                          0, 0)
    wb = waves.bounds
    waves = aff.translate(waves, (CX + 6.0) - (wb[0] + wb[2]) / 2.0, (CY - 3.8) - (wb[1] + wb[3]) / 2.0)
    sun = aff.translate(sun_glyph(1.0), CX - 6.5, CY - 3.8)
    icons = aff.scale(unary_union([waves, sun]), xfact=-1, yfact=1,
                      origin=(fr.W / 2.0, fr.H / 2.0))
    got_i = f.vee(f.raster(icons), 0.25, 60.0, 0.10)
    notes = [f"icons cut {got_i:.3f} mm: sun strokes 0.60, wave strokes "
             f"{0.38*s:.2f} -- both wide enough for the 60 deg bit to bottom at 0.25",
             "the waves are scripts/mask_art.py's own contactless glyph, imported, not "
             "redrawn -- front mask and back engraving carry the SAME mark from the "
             "same generator"]
    for txt, cap, gap_y in [("SOLAR POWERED · NFC", 1.70, 3.4),
                            ("Nº 001 · MMXXVI · ATLANTA", 1.45, 6.6)]:
        g = E.line_geom(txt, CX, CY + gap_y, cap, "r")
        got = f.vee(f.raster(g), 0.25, 60.0, 0.10)
        notes.append(f"{txt[:30]:<30} cap {cap:4.2f}  cut {got:.3f} mm")
    _check(icons, "R")
    return notes, 0.25


def v_provenance_line(f):
    """S -- the committed maker's mark keeps its slot; one line swaps for provenance."""
    lines = [("SOLAR POWERED · NFC · Nº 001 · MMXXVI", 7.0, 51.5, 1.20, "r"),
             ("DEVIN HOROWITZ",                        7.0, 54.1, 1.65, "b")]
    notes = ["the smallest change that says everything: the shipped MAKER_LINES slot, "
             "caps and bold name kept verbatim -- only 'DESIGNED & MADE BY' swaps"]
    for txt, x, y, cap, w in lines:
        g = left_at(E.line_geom(txt, CX, y, cap, w), x)
        _check(g, "S", margin=0.25)
        got = f.vee(f.raster(g), 0.20, 60.0, 0.10)
        notes.append(f"{txt[:38]:<38} cap {cap:4.2f}  cut {got:.3f} mm")
    notes.append("drop-in: same x 7.0 left edge, same y 51.5/54.1 centrelines the "
                 "generator already cuts -- a one-list edit in the shell CAD")
    return notes, 0.20


def v_ring(f):
    """T -- the caseback ring: derived tracking, serial-number centre."""
    R, cap = 10.8, 1.80
    txt = "SOLAR POWERED · NFC 13.56 MHz · MMXXVI · "
    ring, dphi = ring_text(txt, R, cap)
    _check(ring, "T")
    got_t = f.vee(f.raster(ring), 0.25, 60.0, 0.10)
    rules = unary_union([circle_rule(R + 1.9), circle_rule(R - 1.9)])
    got_r = f.vee(f.raster(rules), 0.22, 60.0, 0.10)
    notes = [f"{len(txt)} characters into 360 deg -> {dphi:.2f} deg/char at R {R:.1f} -- "
             f"tracking is derived, the ring closes exactly (the fins' own move)",
             f"ring text cap {cap:.2f} cut {got_t:.3f}; rules at R {R-1.9:.1f} / "
             f"{R+1.9:.1f} cut {got_r:.3f}",
             "reads clockwise, letters upright on their radials -- rotate the card and "
             "the whole sentence passes 12 o'clock"]
    for txt2, cap2, dy, w in [("Nº 001", 2.40, -1.6, "b"),
                              ("REV 4.0", 1.40, 2.0, "r"),
                              ("MMXXVI", 1.40, 4.4, "r")]:
        g = E.line_geom(txt2, CX, CY + dy, cap2, w)
        got = f.vee(f.raster(g), 0.25, 60.0, 0.10)
        notes.append(f"{txt2:<10} cap {cap2:4.2f}  cut {got:.3f} mm  (centre)")
    notes.append("the unit number holds the middle of the dial -- the one line that is "
                 "different on every card sits where a watch puts its serial")
    return notes, 0.25


VARIANTS = [
    ("P-caseback", "CASEBACK", "centred epitaph: power, radio, rev, unit, year, place",
     v_caseback,
     "The watch idiom. Six short lines say what the object is, what it eats, what it "
     "speaks, which one it is and when it was made -- the complete technical epitaph, "
     "one V-bit, no ornament."),
    ("Q-spec-plate", "SPEC PLATE", "framed label/value rows, rules + text one bit",
     v_spec_plate,
     "The industrial idiom. A data plate with MODEL / REV / SER / PWR / RF / YEAR rows "
     "reads as an instrument, not a keepsake -- and frame, rules and type are all the "
     "same bit in one setup, J's economy applied to different words."),
    ("R-marks", "MARKS", "the front mask's NFC waves + a sun, two lines under",
     v_marks,
     "The icon idiom. The contactless waves come from mask_art.py's own generator -- "
     "the front mask and the back engraving carry the same mark -- and the sun says "
     "solar without a word. Language-independent at arm's length."),
    ("S-provenance-line", "PROVENANCE LINE", "the committed mark's slot, one line swapped",
     v_provenance_line,
     "Restraint. The shipped maker's mark already holds the right position at the "
     "right size; swapping its top line for SOLAR POWERED / NFC / unit / year gets "
     "provenance for a one-list edit in the generator, and the back stays quiet."),
    ("T-ring", "RING", "closed circle of text around the serial number",
     v_ring,
     "The caseback ring. Tracking is derived -- n characters into 360 degrees, the "
     "same exact-closure move the fin layout makes -- and the serial sits in the "
     "middle of the dial like a watch number. The most jewellery of the twenty."),
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
        p1, p2 = f"{OUT}/spin4_{key}.png", f"{OUT}/spin4_{key}_graze.png"
        E.shot(surf, p1)
        E.shot(surf, p2, crop=15.0, grazing=True, az=2.0, el=5.0)
        made.append((title, sub, p1, p2, notes))
        print(f"    wrote {os.path.basename(p1)}, {os.path.basename(p2)}\n")

    ims = [(t, s, Image.open(a).convert("RGB"), Image.open(b).convert("RGB"), n)
           for t, s, a, b, n in made]
    cw = max(max(a.width, b.width) for _t, _s, a, b, _n in ims)
    ch = max(max(a.height, b.height) for _t, _s, a, b, _n in ims)
    pad, head, gap, foot = 26, 104, 12, 360
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
           "SPIN 4 -- provenance: what the back SAYS. Solar, NFC, revision, serial, year. "
           "Content is orthogonal to technique -- any of these cuts with any spin-1 cutter.",
           font=fs, fill=(92, 92, 100))
    sheet.save(f"{OUT}/spin4_provenance.png")
    print("wrote", f"{OUT}/spin4_provenance.png", sheet.size)
