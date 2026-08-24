#!/usr/bin/env python3
"""index_posts.py -- candidate sites for the supercap index posts (a v5 STUDY).

NOT a gate: the posts do not exist on the board yet. This is the re-derivation
behind TODO.md's index-post entry, so those coordinates are computed from the
current board rather than typed into a doc and left to rot.

WHAT A POST IS. A cheap chip part, electrically inert, soldered beside a supercap
so the cap seats against it instead of against a live component. Two on each cap's
LONG datum edge (a two-point contact is what constrains ROTATION -- one post stops
translation and does nothing about rotation, which is the dominant placement error)
and one on the short datum edge. The datum edges are fit_rules.CAP_DATUM, i.e. the
same two edges the reflow shim indexes.

NET: GND. Not floating, and NOT a live rail. A part whose job is to be struck by a
17 x 39 mm slab should have a failure mode of "nothing happens electrically" -- tie
it into a live net and a cracked post becomes a fault instead of a blemish. GND is
chosen over floating for MECHANICS, not function: a pad bonded to the ground pour
has more copper anchorage against lateral load. It costs thermal relief to solder.

NOT capacitors. The obvious idea -- give them contributory purpose as energy reserve
-- fails by three orders of magnitude. All ten placeable sites filled with the
largest 6.3 V X5R each is 706 uF nominal, 0.05% of the 1.40 F tank and 4.96 mJ of
its 9.84 J usable; at a realistic 30% DC-bias derating, 0.015%. 1% of the tank would
need 14,000 uF. Nor is there an ESR case: the SCPC cells are 25/40 mOhm, 30.8 mOhm
for the bank, so the 22.46 mA LED envelope droops 0.69 mV. Nor a balancing case: the
AEM10300's BAL pin already holds the midpoint (U2 was deleted in v4 for exactly that).

COLLISION is tested against body UNION pads + COPPER_CLR, dnp included -- a dnp
part's pads are still copper a new footprint may not overlap, and board_parts.parts()
returns the model BODY for parts that have one, which is smaller than their pads.
Testing bodies alone places posts on live copper; it did, on the first cut.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "enclosure"))

GAP = 0.15          # post face to NOMINAL cap edge
EDGE_KEEP = 0.30    # post stays this far inside the board outline
COPPER_CLR = 0.20   # post pads to any existing copper
# name, body L, body W, pad overhang along L
PKG = [("2512", 6.35, 3.20, 0.9), ("2010", 5.00, 2.50, 0.8), ("1210", 3.20, 2.50, 0.8),
       ("1206", 3.20, 1.60, 0.8), ("0805", 2.00, 1.25, 0.6), ("0603", 1.60, 0.80, 0.5)]
# "a 0402 will shear before it indexes a supercap" (PCB/README.md) -- 0603 is barely better
SHEAR = {"2512": "good", "2010": "good", "1210": "good",
         "1206": "adequate", "0805": "marginal", "0603": "INADEQUATE"}
SOLID = {"good", "adequate"}
PLAN = ((0, 0.20), (0, 0.80), (1, 0.50))   # (which datum edge, fraction along it)


def _occupied():
    """Every B-side footprint as body UNION pads, buffered by COPPER_CLR."""
    import board_parts
    from shapely.geometry import box
    from shapely import affinity
    from shapely.ops import unary_union
    txt = open(board_parts.PCB, encoding="utf-8", errors="replace").read()
    by_ref = {}
    for ref, poly, _h, _s in board_parts.parts("B"):
        if not ref.startswith("SC"):
            by_ref.setdefault(ref, []).append(poly)
    for b in board_parts._blocks(txt):
        if not re.search(r'\(footprint "[^"]+"\s*\(layer "B', b):
            continue
        rm = re.search(r'\(property "Reference" "([^"]+)"', b)
        ref = rm.group(1) if rm else "?"
        if ref.startswith("SC"):
            continue
        at = re.search(r"\(at (-?[\d.]+) (-?[\d.]+)(?: (-?[\d.]+))?\)", b)
        if not at:
            continue
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
            by_ref.setdefault(ref, []).append(affinity.translate(r, xoff=fx, yoff=fy))
    return [(r, unary_union(g).buffer(COPPER_CLR)) for r, g in by_ref.items()]


def sites():
    import board_parts
    import fit_rules as fr
    from shapely.geometry import box
    occ = _occupied()
    caps = {r: p for r, p, _h, _s in board_parts.parts("B") if r.startswith("SC")}
    board = box(0, 0, fr.W, fr.H).buffer(-EDGE_KEEP)

    def rect_for(cp, side, t, W, ext):
        x0, y0, x1, y1 = cp.bounds
        if side in ("E", "W"):
            cy = y0 + (y1 - y0) * t
            px = (x1 + GAP) if side == "E" else (x0 - GAP - W)
            return box(px, cy - ext / 2, px + W, cy + ext / 2)
        cx = x0 + (x1 - x0) * t
        py = (y1 + GAP) if side == "N" else (y0 - GAP - W)
        return box(cx - ext / 2, py, cx + ext / 2, py + W)

    def blocker(rect):
        if not board.contains(rect):
            return "board edge"
        for ref, g in occ:
            if rect.intersects(g):
                return ref
        for ref, g in caps.items():
            if rect.intersects(g):
                return ref
        return None

    out = []
    for ref in sorted(caps):
        datum = fr.CAP_DATUM[ref]
        for which, t in PLAN:
            side = datum[which]
            placed = None
            for name, L, W, pad in PKG:
                r = rect_for(caps[ref], side, t, W, L + pad)
                if blocker(r) is None:
                    placed = (name, r)
                    break
            if placed:
                name, r = placed
                out.append(dict(cap=ref, side=side, t=t, pkg=name, shear=SHEAR[name],
                                bounds=[round(v, 3) for v in r.bounds], ok=True))
            else:
                name, L, W, pad = PKG[-1]
                r = rect_for(caps[ref], side, t, W, L + pad)
                out.append(dict(cap=ref, side=side, t=t, pkg=None, shear=None,
                                bounds=[round(v, 3) for v in r.bounds],
                                ok=False, blocker=blocker(r)))
    return out


def main():
    import fit_rules as fr
    rows = sites()
    print(f"index-post sites -- 2 on each cap's long datum edge, 1 on the short; "
          f"gap {GAP} mm, copper clearance {COPPER_CLR} mm, net GND")
    for r in rows:
        tag = f"{r['cap']} {r['side']}@{int(r['t']*100):>2}%"
        if r["ok"]:
            print(f"  {tag}  {r['pkg']:>4}  shear {r['shear']:<10} at {r['bounds']}")
        else:
            print(f"  {tag}  BLOCKED even at {PKG[-1][0]} by {r['blocker']}")
    print()
    for ref in sorted({r["cap"] for r in rows}):
        long_side = fr.CAP_DATUM[ref][0]
        solid = sum(1 for r in rows if r["cap"] == ref and r["side"] == long_side
                    and r["ok"] and r["shear"] in SOLID)
        verdict = "rotation datum OK" if solid == 2 else "NO rotation datum"
        print(f"  {ref}: {solid}/2 solid posts on its long ({long_side}) edge -- {verdict}")
    n = sum(1 for r in rows if r["ok"])
    print(f"\n  {n}/{len(rows)} sites placeable as the board stands")
    return 0


if __name__ == "__main__":
    sys.exit(main())
