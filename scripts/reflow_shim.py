#!/usr/bin/env python3
"""reflow_shim.py -- the supercap reflow index shim, derived from the board.

WHY THIS EXISTS. SC1-SC4 are hand-placed 17 x 39 / 17 x 28.5 mm bodies whose pads sit
UNDER the can, so an iron cannot reach them: reflow is mandatory, and the caps must be
held while the paste is molten. A printed jig cannot do that job -- it does not survive
hotplate temperature -- and the board has no room for on-board index posts (measured:
of the sixteen cap edge-directions, exactly one clears 3.2 mm).

WHAT IT IS. A flat metal plate, laser-cut from the same 316L as the air frame, whose
outline is the board's own part-free area: `fit_rules.brace_footprint(span=0.0)`. span=0
makes EVERY part a blocker, so the plate lands only on bare laminate -- it cannot rest on
a component, and (verified, not assumed) it clears all 208 B-side pads. Run at SHIM_CLR
instead of the brace's hand-solder allowance, the same generator that cuts the diffuser
brace cuts a datum that hugs each cap.

WHAT IT BUYS. Each cap ends up indexed on two orthogonal sides -- one long side at
75-97.5% coverage, which is what kills ROTATION (the dominant placement error: 1 deg
swings a 39 mm cap's corner 0.34 mm), plus an adjacent short side. Contact IS nominal,
so the paste's own self-centring pulls the same way the datum does instead of fighting
it, and slop becomes one-sided. And the indexed sides are, by construction, the four
where a real part sits inside the brace bay (SC4/L2 0.50, SC3/R15 0.57, SC2/C6 0.65,
SC1/C11 0.70): the plate is the complement of the parts, so metal exists exactly where
a close neighbour does, interposing steel between the cap and what it would shear.

WHAT IT DOES NOT DO. It is removed after reflow, so it gives NO field restraint -- the
edge-drop case still loads the brace, and on those four directions a component. That is
the argument for on-board posts, which this does not replace.

THE OPEN NUMBER. Once a cap is datum-referenced the residual is the cap's own body
tolerance, and it is not recorded anywhere in this repo -- the SS17/WS17 bodies are
modelled at nominal 17.00 x 39.00 / 17.00 x 28.50. SHIM_CLR below is a placeholder sized
for handling, NOT a fit computed against a tolerance. Pull the SCHURTER SCPC figure
before cutting metal; it sets this constant and whether the brace bays can come back in.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "enclosure"))

SHIM_CLR = 0.10      # PROVISIONAL -- see "THE OPEN NUMBER" above
THICK = 0.60         # mm, 316L flat stock; must stay under SUPERCAP_H so it never fouls
MATERIAL = "316L stainless, laser-cut, deburred both faces"
COVER_FLOOR = 0.60   # a datum side must face metal over at least this fraction
OPEN_MAX = 0.10      # ...and the opposite side must be this open, or the cap is BOXED
OUT = ROOT / "enclosure" / "shim"


def outline(clr=SHIM_CLR):
    """The shim outline: cavity minus EVERY part, caps held at `clr`."""
    import fit_rules as fr
    from shapely.ops import unary_union
    saved = fr.CLR_EXCEPTIONS
    try:
        fr.CLR_EXCEPTIONS = {r: clr for r in ("SC1", "SC2", "SC3", "SC4")}
        return unary_union(list(fr.brace_footprint(span=0.0)))
    finally:
        fr.CLR_EXCEPTIONS = saved


def coverage(shim):
    """Per-cap, per-side fraction of the cap edge that faces shim metal."""
    import board_parts
    from shapely.geometry import Point
    out = {}
    for ref, poly, _h, _s in board_parts.parts("B"):
        if not ref.startswith("SC"):
            continue
        x0, y0, x1, y1 = poly.bounds
        sides = {}
        for nm, (ax, lo, hi, fx) in {"E": ("x", y0, y1, x1), "W": ("x", y0, y1, x0),
                                     "N": ("y", x0, x1, y1), "S": ("y", x0, x1, y0)}.items():
            n, m = 40, 0
            for i in range(n):
                t = lo + (hi - lo) * (i + 0.5) / n
                pt = Point(fx, t) if ax == "x" else Point(t, fx)
                if pt.buffer(SHIM_CLR + 0.03).intersects(shim):
                    m += 1
            sides[nm] = m / n
        out[ref] = sides
    return out


def pad_overlap(shim):
    """Total B-side pad area the shim would sit on. Must be zero."""
    import re
    import board_parts
    from shapely.geometry import box
    from shapely import affinity
    txt = open(board_parts.PCB, encoding="utf-8", errors="replace").read()
    tot, worst = 0.0, []
    for b in board_parts._blocks(txt):
        if not re.search(r'\(footprint "[^"]+"\s*\(layer "B', b):
            continue
        rm = re.search(r'\(property "Reference" "([^"]+)"', b)
        ref = rm.group(1) if rm else "?"
        if ref.startswith("SC") or ref.startswith("MH"):
            continue
        at = re.search(r"\(at (-?[\d.]+) (-?[\d.]+)(?: (-?[\d.]+))?\)", b)
        fx, fy, rot = float(at.group(1)), float(at.group(2)), float(at.group(3) or 0)
        for pb in board_parts._blocks(b, "pad"):
            pat = re.search(r"\(at (-?[\d.]+) (-?[\d.]+)(?: (-?[\d.]+))?\)", pb)
            sz = re.search(r"\(size ([\d.]+) ([\d.]+)\)", pb)
            if not pat or not sz:
                continue
            px, py = float(pat.group(1)), float(pat.group(2))
            prot = float(pat.group(3) or 0)
            pw, ph = float(sz.group(1)), float(sz.group(2))
            r = box(px - pw / 2, py - ph / 2, px + pw / 2, py + ph / 2)
            if abs(prot - rot) > 1e-9:
                r = affinity.rotate(r, prot - rot, origin=(px, py))
            if rot:
                r = affinity.rotate(r, rot, origin=(0, 0))
            r = affinity.translate(r, xoff=fx, yoff=fy)
            if r.intersects(shim):
                a = r.intersection(shim).area
                if a > 1e-9:
                    tot += a
                    worst.append((ref, a))
    return tot, sorted(worst, key=lambda t: -t[1])[:5]


def write_dxf(shim, path):
    """Minimal DXF (LWPOLYLINE per ring) -- flat stock, so 2D is the whole part."""
    rings = []
    geoms = getattr(shim, "geoms", [shim])
    for g in geoms:
        rings.append(list(g.exterior.coords))
        rings.extend(list(i.coords) for i in g.interiors)
    L = ["0", "SECTION", "2", "ENTITIES"]
    for r in rings:
        L += ["0", "LWPOLYLINE", "8", "SHIM", "90", str(len(r)), "70", "1"]
        for x, y in r:
            L += ["10", f"{x:.4f}", "20", f"{y:.4f}"]
    L += ["0", "ENDSEC", "0", "EOF"]
    path.write_text("\n".join(L) + "\n", encoding="utf-8")
    return len(rings)


def check(verbose=True):
    import fit_rules as fr
    bad = []
    shim = outline()
    n = len(getattr(shim, "geoms", [shim]))
    if n != 1:
        bad.append(f"shim outline is {n} pieces -- a one-piece plate is the whole point "
                   f"(handling, and it cannot be installed in the wrong order)")
    if THICK >= fr._SUPERCAP_H:
        bad.append(f"THICK {THICK} >= supercap height {fr._SUPERCAP_H} -- the plate would "
                   f"stand proud of the caps it is meant to hold down")

    tot, worst = pad_overlap(shim)
    if tot > 1e-6:
        bad.append(f"shim sits on {tot:.3f} mm2 of B-side pad ({worst}) -- it would print "
                   f"through paste and solder itself to the board")

    # Instrument self-test: with EVERY part's clearance at zero the plate must touch pads.
    # If it does not, the pad geometry and the outline are in different frames and the
    # clean result above means nothing. (This is the failure this repo keeps re-finding:
    # an inert measurement reads as a pass.) Zeroing only the CAPS is not a control --
    # their pads sit under the can, which is a blocker at any clearance, so that version
    # of this test could never fire. It was written that way first, and said so.
    from shapely.ops import unary_union
    _saved = fr.clr_for
    try:
        fr.clr_for = lambda _ref: 0.0
        z_tot, _ = pad_overlap(unary_union(list(fr.brace_footprint(span=0.0))))
    finally:
        fr.clr_for = _saved
    if z_tot <= 1e-6:
        bad.append("SELF-TEST: a zero-clearance shim overlaps no pad either, so the pad "
                   "check is measuring nothing -- frames disagree")

    cov = coverage(shim)
    for ref, sides in sorted(cov.items()):
        good = sorted((v, k) for k, v in sides.items())[::-1]
        picked = [k for v, k in good if v >= COVER_FLOOR]
        horiz = {"E", "W"} & set(picked)
        vert = {"N", "S"} & set(picked)
        if not (horiz and vert):
            bad.append(f"{ref}: indexed on {picked or 'nothing'} -- a datum needs two "
                       f"ORTHOGONAL sides above {COVER_FLOOR:.0%}, or rotation is free")
        elif verbose:
            print(f"  {ref}: " + "  ".join(f"{k} {sides[k]:5.1%}" for k in ("E", "W", "N", "S"))
                  + f"   datum {'+'.join(sorted(picked))}")

    # NEVER BOX A CAP. The plate is cut around the NOMINAL body, but the body is
    # 17.0 +-0.5 wide and 39.0/28.5 +0.5/-0.0 long (part_heights.SUPERCAP_BODY_TOL, from
    # the SCPC datasheet). A closed pocket at nominal + SHIM_CLR is 17.20 across and a
    # max-material cap is 17.50: it JAMS by 0.30 mm, and it jams on exactly the units
    # whose caps are biggest. The two-sided datum only works because the OTHER two sides
    # are open for the +0.5 to go somewhere, and today they are open by accident of where
    # the parts happen to sit -- nothing asserted it until this check. A board change that
    # puts a part on a cap's free side turns the locator into a press fit.
    from part_heights import SUPERCAP_BODY_TOL
    for ref, sides in sorted(cov.items()):
        for axis, (a, b) in (("X", ("E", "W")), ("Y", ("N", "S"))):
            if min(sides[a], sides[b]) > OPEN_MAX and SHIM_CLR < SUPERCAP_BODY_TOL:
                bad.append(f"{ref}: both {axis} sides are enclosed ({a} {sides[a]:.0%}, "
                           f"{b} {sides[b]:.0%}) at {SHIM_CLR:.2f} mm clearance, but the "
                           f"body can run {SUPERCAP_BODY_TOL:.2f} mm over nominal -- a "
                           f"max-material cap jams instead of seating")
            elif verbose:
                free = a if sides[a] <= sides[b] else b
                print(f"  {ref} {axis}: datum {a if free == b else b}, {free} open "
                      f"({sides[free]:.0%}) for the +{SUPERCAP_BODY_TOL:.2f} mm growth")

    # The four directions where a real part sits inside the brace bay must be indexed --
    # that is what makes the plate a guard and not just a locator.
    sys.path.insert(0, str(ROOT / "scripts"))
    import cap_clearance as cc
    for (ref, d), (who, mm) in sorted(cc.LEDGER.items()):
        if mm >= fr.clr_for(ref):
            continue
        side = {"+X": "E", "-X": "W", "+Y": "N", "-Y": "S"}[d]
        # Coverage alone does NOT make the plate a guard, and testing only coverage was
        # this check's first bug: the probe is buffered by SHIM_CLR, so opening the
        # clearance to 0.75 kept coverage at 90% while the plate stopped standing between
        # the cap and L2 at all. The plate guards only if it is CLOSER than the part is.
        if SHIM_CLR >= mm:
            bad.append(f"{ref} {d}: shim clearance {SHIM_CLR:.2f} mm is not inside {who} "
                       f"at {mm:.2f} mm -- the cap reaches the part before the plate")
        elif cov[ref][side] < COVER_FLOOR:
            bad.append(f"{ref} {d} reaches {who} at {mm:.2f} mm but the shim covers that "
                       f"side only {cov[ref][side]:.0%} -- nothing between cap and part")
        elif verbose:
            print(f"  guard ok: {ref} {d} -> {who} @ {mm:.2f} mm, shim covers "
                  f"{cov[ref][side]:.0%} of that edge")

    if verbose:
        print(f"reflow_shim: {shim.area:.1f} mm2, {n} piece(s), {THICK} mm {MATERIAL}, "
              f"cap clearance {SHIM_CLR} mm; pad overlap {tot:.3f} mm2 "
              f"(zero-clearance control {z_tot:.3f} mm2)")
    return bad


if __name__ == "__main__":
    if "--dxf" in sys.argv:
        OUT.mkdir(parents=True, exist_ok=True)
        s = outline()
        p = OUT / "solar-glow-drh-reflow-shim.dxf"
        print(f"wrote {p} ({write_dxf(s, p)} rings, {s.area:.1f} mm2)")
    problems = check()
    for b in problems:
        print(f"FAIL: {b}")
    print(f"reflow_shim: {len(problems)} problem(s)")
    sys.exit(1 if problems else 0)
