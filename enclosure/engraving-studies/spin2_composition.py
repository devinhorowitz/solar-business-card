#!/usr/bin/env python3
"""Engraving, spin 2. Same part, same tool physics -- a different QUESTION.

Spin 1 asked which CUTTER: V-carve vs flat pocket vs relief vs plaque. That question is
mostly answered, so nothing here re-litigates it. Spin 2 asks about COMPOSITION, HIERARCHY
and REGISTRATION, and it settles the one loose end spin 1 left:

  F REGISTERED   DRH stands in relief inside EXACTLY the front's glow-window footprint --
                 GLOW_WIN (14.95, 40.8) .. (35.85, 47.0) straight out of the generator. The
                 letters that glow through the front are the letters you feel on the back,
                 same size, same place. The window is centred on x = W/2, so the machining
                 mirror maps it onto itself and the registration is free.
  G FIN RHYTHM   Left-aligned, and every baseline sits on the fin pitch (FIN_PITCH = 3.2 mm)
                 with two hairline rules on the same grid. The back's own geometry sets the
                 typography instead of the type being dropped onto it.
  H TWO-DEPTH    A hierarchy you can feel, not just see: the name is flat-pocketed the full
                 0.30 mm with a hard edge, everything under it is a fine 0.15 mm V-groove.
                 One fingertip pass tells you which line is the name.
  I RELIEF/TAPER Spin 1's pick, re-cut with the tool it should have had. A 15 deg TAPERED
                 engraving cutter with a 0.2 mm tip is rigid because of the taper, so it
                 enters counters a straight dia 0.3 cannot, and it leaves a small flare at
                 the base of every letter. Measured against spin 1's 3.545 mm2 of webs.
  J FRAMED       A machined groove frame around a left-aligned block, echoing the front's
                 own perimeter frame. Frame and text cut with the same bit in one setup.

Everything else -- the tool models, the 25 um depth field, the 0.30 mm budget set by the fin
valleys, the art rect clear of all four in-band bosses -- is imported from spin 1 unchanged.
"""
from __future__ import annotations

import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))     # enclosure/, for fit_rules
sys.path.insert(0, HERE)

import numpy as np
import shapely.affinity as aff
from PIL import Image, ImageDraw
from scipy import ndimage
from shapely.geometry import box
from shapely.ops import unary_union

import spin1_cutters as E
import fit_rules as fr

OUT = E.OUT
PX = E.PX
CX, CY, ART = E.CX, E.CY, E.ART

# straight out of the shell generator -- the monogram footprint on the committed PCB
GLOW_WIN = (14.95, 40.8, 35.85, 47.0)
LEFT = 8.6                      # left margin for the left-aligned variants


# --- extra layout primitives -------------------------------------------------------

def letterspaced(txt, x0, x1, cy, cap, weight):
    """Set `txt` with even letterspacing so it spans exactly x0..x1.

    The front's DRH is letterspaced across the glow window; matching it by cap height alone
    would not fit -- 3 bold characters tall enough to fill the 6.2 mm window are only 10.4 mm
    wide against the window's 20.9. The spacing is the point, so it is a parameter.
    """
    glyphs = [E.line_geom(c, 0.0, cy, cap, weight) for c in txt]
    widths = [(g.bounds[2] - g.bounds[0]) if g is not None else 0.0 for g in glyphs]
    n = len(txt)
    gap = ((x1 - x0) - sum(widths)) / (n - 1) if n > 1 else 0.0
    out, x = [], x0
    for g, w in zip(glyphs, widths):
        if g is not None:
            # line_geom already mirrored about W/2; place in that mirrored frame
            b = g.bounds
            out.append(aff.translate(g, (fr.W - (x + w)) - b[0], 0.0))
        x += w + gap
    return unary_union(out)


def rule(x0, x1, y, w=0.30):
    """A hairline rule -- a thin box, cut like any other shape."""
    return box(x0, y - w / 2.0, x1, y + w / 2.0)


def frame(rect, w=0.30, r=0.8):
    """A groove frame: the boundary of a rounded rect, given a width."""
    x0, y0, x1, y1 = rect
    outer = box(x0, y0, x1, y1).buffer(-r).buffer(r * 2).intersection(box(x0, y0, x1, y1))
    return fr._dedupe(outer.exterior.buffer(w / 2.0))


def stack(lines, x, cy, align="left"):
    """Lay out (text, cap, weight, gap) with a fixed left edge or centred. -> per-line list."""
    total = sum(c for _t, c, _w, _g in lines) + sum(g for _t, _c, _w, g in lines[1:])
    y = cy - total / 2.0
    out = []
    for i, (txt, cap, weight, gap) in enumerate(lines):
        y += gap if i else 0.0
        g = E.line_geom(txt, CX, y + cap / 2.0, cap, weight)
        if g is not None:
            if align == "left":
                # line_geom mirrors about W/2, so a left edge at x becomes a RIGHT edge there
                b = g.bounds
                g = aff.translate(g, (fr.W - x) - b[2], 0.0)
            out.append(dict(txt=txt, cap=cap, weight=weight, geom=g))
        y += cap
    return out


def baseline_grid(n, cy, pitch=fr.FIN_PITCH):
    """n baselines centred on cy, spaced on the fin pitch."""
    return [cy + (i - (n - 1) / 2.0) * pitch for i in range(n)]


# --- the tapered engraving cutter, which spin 1 owed --------------------------------

def relief_taper(f, panel_mask, glyph_mask, depth, r_tip, taper_deg):
    """Relief cut with a TAPERED engraving cutter: rigid shank, small tip.

    Reach at the floor is set by the TIP radius, so it enters counters a straight end mill of
    the same rigidity could not. The taper then means the tool is wider higher up, so it
    removes a little extra beside each letter on the way out and leaves a small FLARE at the
    letter's base -- 0.067 mm of it at 15 deg and 0.25 mm deep. That flare is not a defect;
    it is why relief cut this way reads crisper than a straight wall, and it is modelled here
    rather than assumed away.
    """
    field = panel_mask & ~glyph_mask
    reach = E.Field.opening(field, r_tip)
    f.z = np.maximum(f.z, np.where(reach, depth, 0.0))
    tan = math.tan(math.radians(taper_deg))
    s = ndimage.distance_transform_edt(glyph_mask) * PX
    flare = np.clip(depth - s / tan, 0.0, depth)
    f.z = np.maximum(f.z, flare * glyph_mask)
    return reach, field & ~reach, depth * tan


# --- variants -----------------------------------------------------------------------

FULL = [("DEVIN HOROWITZ",     3.00, "b", 0.00),
        ("ATTORNEY",           1.50, "r", 1.30),
        ("Devin@Horowitz.Law", 2.20, "r", 2.00),
        ("404-213-8076",       2.20, "r", 1.10),
        ("Atlanta, Georgia",   1.60, "r", 1.40)]


def v_registered(f):
    """F -- DRH in relief inside the front's own glow window; contact V-carved below."""
    notes = []
    win = box(*GLOW_WIN)
    drh = letterspaced("DRH", GLOW_WIN[0] + 1.6, GLOW_WIN[2] - 1.6,
                       (GLOW_WIN[1] + GLOW_WIN[3]) / 2.0, 4.40, "b")
    wm, gm = f.raster(win), f.raster(drh)
    reach, miss, flare = relief_taper(f, wm, gm, 0.25, 0.10, 15.0)
    notes.append(f"DRH relief inside GLOW_WIN {GLOW_WIN[2]-GLOW_WIN[0]:.2f} x "
                 f"{GLOW_WIN[3]-GLOW_WIN[1]:.2f} mm at the front monogram's exact footprint")
    notes.append(f"window is centred on x = {(GLOW_WIN[0]+GLOW_WIN[2])/2:.2f} = W/2, so the "
                 f"machining mirror maps it onto itself -- registration is exact, not fitted")
    notes.append(f"unreachable metal in the window: {f.area(miss):.3f} mm2")
    lines = stack([("Devin@Horowitz.Law", 2.10, "r", 0.00),
                   ("404-213-8076  ·  Atlanta, Georgia", 1.55, "r", 1.30)], CX, 51.9, "centre")
    for ln in lines:
        m = f.raster(ln["geom"])
        got = f.vee(m, 0.25, 60.0, 0.10)
        notes.append(f"{ln['txt'][:30]:<30} cap {ln['cap']:4.2f}  cut {got:.3f} mm")
    return notes, 0.25


def v_fin_rhythm(f):
    """G -- left-aligned, every baseline on the 3.2 mm fin pitch, rules on the same grid."""
    notes = [f"baselines on FIN_PITCH = {fr.FIN_PITCH:.2f} mm, the pitch of the ribs above "
             f"and below -- the back's own geometry sets the leading"]
    ys = baseline_grid(6, CY)
    spec = [("DEVIN HOROWITZ", 2.80, "b"), ("ATTORNEY", 1.40, "r"), (None, 0, None),
            ("Devin@Horowitz.Law", 2.00, "r"), ("404-213-8076", 2.00, "r"),
            ("Atlanta, Georgia", 1.50, "r")]
    for y, (txt, cap, weight) in zip(ys, spec):
        if txt is None:
            g = rule(LEFT, ART[2] - 2.6, y, 0.55)
            g = aff.scale(g, xfact=-1, yfact=1, origin=(fr.W / 2.0, fr.H / 2.0))
            got = f.vee(f.raster(g), 0.25, 60.0, 0.10)
            notes.append(f"{'rule 0.55 wide':<30} {ART[2]-2.6-LEFT:5.1f} mm long   "
                         f"cut {got:.3f} mm -- widened from 0.30, which a 60 deg bit "
                         f"bottoms out in at 0.173 and leaves reading shallower than the type")
            continue
        g = E.line_geom(txt, CX, y, cap, weight)
        b = g.bounds
        g = aff.translate(g, (fr.W - LEFT) - b[2], 0.0)
        got = f.vee(f.raster(g), 0.25, 60.0, 0.10)
        notes.append(f"{txt[:30]:<30} cap {cap:4.2f}  cut {got:.3f} mm")
    return notes, 0.25


def v_two_depth(f):
    """H -- the name pocketed 0.30 with a hard edge, the details a 0.15 mm groove."""
    notes = []
    name = E.line_geom("DEVIN HOROWITZ", CX, CY - 5.4, 3.40, "b")
    m = f.raster(name)
    cut, miss = f.pocket(m, 0.30, 0.15)
    notes.append(f"{'DEVIN HOROWITZ':<30} cap 3.40  POCKET dia 0.3, flat bottom 0.300 mm"
                 + (f"  ({f.area(miss):.2f} mm2 unreachable)" if miss.any() else ""))
    rest = stack([("ATTORNEY", 1.50, "r", 0.00),
                  ("Devin@Horowitz.Law", 2.10, "r", 1.80),
                  ("404-213-8076", 2.10, "r", 1.10),
                  ("Atlanta, Georgia", 1.55, "r", 1.30)], CX, CY + 4.3, "centre")
    for ln in rest:
        got = f.vee(f.raster(ln["geom"]), 0.15, 60.0, 0.10)
        notes.append(f"{ln['txt'][:30]:<30} cap {ln['cap']:4.2f}  V-GROOVE      {got:.3f} mm")
    notes.append("0.30 vs 0.15 is a 2x step -- a fingertip resolves it without looking")
    return notes, 0.30


def v_relief_taper(f):
    """I -- spin 1's relief, re-cut with a 15 deg tapered 0.2 mm-tip engraving cutter."""
    panel = fr._dedupe(box(6.9, 31.4, 43.9, 57.5).buffer(-1.6).buffer(3.2)
                       .intersection(box(6.9, 31.4, 43.9, 57.5)))
    glyph, per = E.block(FULL, CX, CY)
    pm, gm = f.raster(panel), f.raster(glyph)
    reach, miss, flare = relief_taper(f, pm, gm, 0.25, 0.10, 15.0)
    notes = [f"panel 37.0 x 26.1 mm, floor down 0.250 mm over {f.area(reach):.1f} mm2",
             f"tapered cutter: dia 0.2 tip, 15 deg -- reach at the floor is set by the TIP, "
             f"and the taper is what makes it rigid enough to run in Ti",
             f"metal it cannot reach, left proud between letters: {f.area(miss):.3f} mm2"
             + (", none" if not miss.any() else f", widest blob {f.widest(miss):.3f} mm"),
             f"SPIN 1 with a straight dia 0.3 left 3.545 mm2 (blobs to 0.255 mm) -- this is "
             f"{100*(1-f.area(miss)/3.545):.0f}% less",
             f"flare left at each letter base: {flare*1000:.0f} um wide"]
    return notes, 0.25


def v_framed(f):
    """J -- a groove frame echoing the front's perimeter frame, left-aligned block inside."""
    fr_rect = (7.2, 32.6, 43.8, 56.3)
    inner_r = fr_rect[2] - 0.34 / 2 - 0.6          # frame groove inner edge, minus a margin
    lines = [("DEVIN HOROWITZ",     2.85, "b", 0.00),
             ("ATTORNEY",           1.45, "r", 1.25),
             ("Devin@Horowitz.Law", 2.05, "r", 1.90),
             ("404-213-8076",       2.05, "r", 1.05),
             ("Atlanta, Georgia",   1.50, "r", 1.30)]
    g = aff.scale(frame(fr_rect, 0.34, 1.2), xfact=-1, yfact=1, origin=(fr.W / 2.0, fr.H / 2.0))
    got = f.vee(f.raster(g), 0.28, 60.0, 0.10)
    notes = [f"frame {fr_rect[2]-fr_rect[0]:.1f} x {fr_rect[3]-fr_rect[1]:.1f} mm, "
             f"0.34 mm groove   cut {got:.3f} mm -- same bit as the text, one setup"]
    widest = 0.0
    for ln in stack(lines, LEFT + 2.2, CY, "left"):
        got = f.vee(f.raster(ln["geom"]), 0.25, 60.0, 0.10)
        b = ln["geom"].bounds
        widest = max(widest, fr.W - b[0])          # right edge, back in reading orientation
        notes.append(f"{ln['txt'][:30]:<30} cap {ln['cap']:4.2f}  cut {got:.3f} mm")
    notes.append(f"longest line ends at x {widest:.2f}, frame groove starts at {inner_r+0.6:.2f} "
                 f"-- {inner_r + 0.6 - widest:.2f} mm clear"
                 + ("" if widest < inner_r + 0.6 else "  *** OVERRUNS THE FRAME ***"))
    return notes, 0.28


VARIANTS = [
    ("F-registered", "REGISTERED", "DRH relief in the front's own glow window", v_registered,
     "The back monogram is not a copy of the front one -- it is the SAME RECTANGLE, pulled "
     "from GLOW_WIN in the generator. Hold the card to the light and the letters you see lit "
     "are the letters under your thumb."),
    ("G-fin-rhythm", "FIN RHYTHM", "baselines on the 3.2 mm fin pitch, left-aligned", v_fin_rhythm,
     "The leading is not chosen, it is inherited: every baseline lands on the same pitch as "
     "the ribs above and below, so the whole back is one grid instead of a striped area and "
     "a text area."),
    ("H-two-depth", "TWO-DEPTH", "name pocketed 0.30, details grooved 0.15", v_two_depth,
     "Hierarchy you can feel. The name has a flat floor and a square shoulder; everything "
     "under it is a fine groove at half the depth. This is the only variant that uses the "
     "depth budget as a design axis rather than spending all of it everywhere."),
    ("I-relief-taper", "RELIEF / TAPER", "dia 0.2 tip, 15 deg tapered engraving cutter", v_relief_taper,
     "Spin 1's pick with the tool it should have had. The taper is the point: it gives a "
     "0.2 mm tip the rigidity of a much larger cutter, so the counters clear and the webs "
     "between tight letters mostly go away."),
    ("J-framed", "FRAMED", "0.28 mm groove frame + left-aligned block", v_framed,
     "Echoes the perimeter frame on the show face, so front and back are recognisably the "
     "same object. Frame and text are the same bit at the same depth -- one setup, one tool "
     "change fewer than any two-level variant."),
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
    print(f"art rect {ART}, clear band y{fr.fin_band()}, fin pitch {fr.FIN_PITCH}\n")
    made = []
    for key, title, sub, fn, why in VARIANTS:
        f, keep, notes = build(fn)
        print(f"=== {key}  {title} -- {sub}")
        for n in notes:
            print("    " + n)
        surf = E.field_surfaces(f, keep)
        p1, p2 = f"{OUT}/spin2_{key}.png", f"{OUT}/spin2_{key}_graze.png"
        E.shot(surf, p1)
        E.shot(surf, p2, crop=15.0, grazing=True, az=2.0, el=5.0)
        made.append((title, sub, p1, p2, notes))
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
                       fill=(70, 70, 78) if "DEEPEST" in ln or "SPIN 1" in ln else (118, 118, 126))
                y += 24
    d.text((pad, head + ch * 2 + gap + foot - 34),
           "SPIN 2 -- composition, hierarchy and registration. Same tool physics as spin 1: "
           "every depth field is the cut a real bit leaves, sampled at 25 um, on the real shell STL.",
           font=fs, fill=(92, 92, 100))
    sheet.save(f"{OUT}/spin2_composition.png")
    print("wrote", f"{OUT}/spin2_composition.png", sheet.size)
