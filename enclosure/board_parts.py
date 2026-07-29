#!/usr/bin/env python3
"""True B-side part outlines, read straight off the committed board.

WHY THIS EXISTS

The enclosure generators used to derive each part's outline from its pads with two bugs
that survived because nothing ever compared the result to the part:

  * FOOTPRINT ROTATION WAS IGNORED, and each pad was inflated to a max(w,h)/2 SQUARE
    rather than its per-axis half sizes. 35 of the 61 B-side footprints are rotated, mostly
    +-90, so every 2:1 chip passive got a pocket rotated 90 degrees off the part it was cut
    for -- and every rectangular pad got a keep-out larger than the pad in one axis and
    correct in the other.

  * THE MODEL'S OWN TRANSFORM WAS IGNORED. A (model ...) block carries its own
    (rotate (xyz ..)) and (offset ..) on top of the footprint's (at x y rot). SC1 is
    (at 15.5 21.25 180) WITH (rotate (xyz 0 0 90)); read the footprint angle alone and a
    39 mm can lies along the wrong axis.

The keep-out returned here is BODY union PADS. Both matter and they are not the same
shape: the can is what a lip or a boss crushes, the pads are bare copper (the board sets
pad_to_mask_clearance = 0) and a grounded titanium feature resting on one shorts it.
For the supercaps the two differ by several mm in both axes.

Heights come from part_heights.py; this module answers WHERE, that one answers HOW TALL.
"""
from __future__ import annotations

import glob
import os
import re

from shapely.geometry import box
from shapely.ops import unary_union
from shapely import affinity

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PCB = os.path.join(ROOT, "PCB", "solar-glow-drh-v4_0.kicad_pcb")

_MODEL_DIRS = (os.path.join(ROOT, "PCB", "solarglow.3dshapes"),
               os.path.join(ROOT, "PCB", "kicad-3dmodels"))
_EXTENT_CACHE: dict[str, tuple | None] = {}


def _model_index() -> dict[str, str]:
    idx: dict[str, str] = {}
    for root in _MODEL_DIRS:
        for p in glob.glob(os.path.join(root, "**", "*.step"), recursive=True):
            idx.setdefault(os.path.basename(p), p)
    return idx


_IDX = _model_index()


def model_extent(name: str):
    """(dx, dy, dz) of a modelled body in mm, or None if the model is not vendored."""
    if name in _EXTENT_CACHE:
        return _EXTENT_CACHE[name]
    path = _IDX.get(name)
    if not path:
        _EXTENT_CACHE[name] = None
        return None
    with open(path, encoding="utf-8", errors="replace") as fh:
        txt = fh.read()
    xs, ys, zs = [], [], []
    for m in re.finditer(r"CARTESIAN_POINT\s*\(\s*'[^']*'\s*,\s*\(\s*(-?[\d.E+-]+)\s*,\s*"
                         r"(-?[\d.E+-]+)\s*,\s*(-?[\d.E+-]+)\s*\)", txt):
        xs.append(float(m.group(1))); ys.append(float(m.group(2))); zs.append(float(m.group(3)))
    if not xs:
        _EXTENT_CACHE[name] = None
        return None
    val = (max(xs) - min(xs), max(ys) - min(ys), max(zs))
    _EXTENT_CACHE[name] = val
    return val


def _blocks(text: str, tag: str = "footprint"):
    """Balanced-paren s-expression blocks; the board is too big for a naive regex."""
    out = []
    for m in re.finditer(r'\(' + tag + r' ', text):
        depth, i = 0, m.start()
        while i < len(text):
            c = text[i]
            if c == '(':
                depth += 1
            elif c == ')':
                depth -= 1
                if depth == 0:
                    break
            i += 1
        out.append(text[m.start():i + 1])
    return out


def parts(side: str = "B", pcb: str | None = None):
    """[(ref, keepout_polygon, height_mm_or_None, source)] for one side of the board.

    `source` is "model" when the body came from a 3D model and "pads" when there was none
    (J1, JP1, TP1, SW2 and the solder-bridge blobs) -- a caller that cares about the
    difference can say so rather than silently treating a pad box as a body.
    """
    from part_heights import part_height, UnknownPart

    with open(pcb or PCB, encoding="utf-8", errors="replace") as fh:
        text = fh.read()

    out = []
    for b in _blocks(text):
        if not re.search(r'\(footprint "[^"]+"\s*\(layer "' + side, b):
            continue
        rm = re.search(r'\(property "Reference" "([^"]+)"', b)
        ref = rm.group(1) if rm else "?"
        if ref.startswith("MH"):
            continue
        at = re.search(r'\(at (-?[\d.]+) (-?[\d.]+)(?: (-?[\d.]+))?\)', b)
        fx, fy, rot = float(at.group(1)), float(at.group(2)), float(at.group(3) or 0.0)

        rects = []
        for pb in _blocks(b, "pad"):
            pat = re.search(r'\(at (-?[\d.]+) (-?[\d.]+)(?: (-?[\d.]+))?\)', pb)
            if not pat:
                continue
            px, py = float(pat.group(1)), float(pat.group(2))
            prot = float(pat.group(3) or 0.0)
            sz = re.search(r'\(size ([\d.]+) ([\d.]+)\)', pb)
            pw, ph = (float(sz.group(1)), float(sz.group(2))) if sz else (0.3, 0.3)
            r = box(px - pw / 2, py - ph / 2, px + pw / 2, py + ph / 2)
            local = prot - rot          # stored pad angle is absolute; strip the footprint's
            if abs(local) > 1e-9:
                r = affinity.rotate(r, local, origin=(px, py))
            rects.append(r)
        padbox = None
        if rects:
            loc = unary_union(rects)
            if rot:
                loc = affinity.rotate(loc, rot, origin=(0, 0))
            padbox = affinity.translate(loc, xoff=fx, yoff=fy).envelope

        body, source = None, "pads"
        mm = re.search(r'\(model "([^"]+)"', b)
        if mm:
            ext = model_extent(os.path.basename(mm.group(1)))
            if ext:
                dx, dy, _dz = ext
                mb = b[b.index('(model '):]
                rz = re.search(r'\(rotate\s*\(xyz\s*(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)', mb)
                off = re.search(r'\(offset\s*\(xyz\s*(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)', mb)
                g = box(-dx / 2, -dy / 2, dx / 2, dy / 2)
                if off:
                    g = affinity.translate(g, xoff=float(off.group(1)), yoff=float(off.group(2)))
                total = rot + (float(rz.group(3)) if rz else 0.0)
                if total:
                    g = affinity.rotate(g, total, origin=(0, 0))
                body = affinity.translate(g, xoff=fx, yoff=fy)
                source = "model"

        keepout = body if body is not None else padbox
        if keepout is None:
            continue
        if body is not None and padbox is not None:
            keepout = body.union(padbox).envelope

        try:
            h = part_height(ref)
        except UnknownPart:
            h = None
        out.append((ref, keepout, h, source))
    return out


if __name__ == "__main__":
    import sys
    sys.path.insert(0, HERE)
    ps = parts("B")
    n_model = sum(1 for p in ps if p[3] == "model")
    print(f"{len(ps)} B-side parts: {n_model} from 3D models, {len(ps) - n_model} from pads")
    for ref, poly, h, src in sorted(ps, key=lambda t: t[0]):
        b = poly.bounds
        hs = "  -  " if h is None else f"{h:5.2f}"
        print(f"  {ref:6}{src:7}h={hs}  x{b[0]:7.2f}..{b[2]:7.2f}  y{b[1]:7.2f}..{b[3]:7.2f}")
