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


# What a KiCad-library model paints its METAL, as opposed to its body: tinned terminations, and
# the lead frame of a leaded package. Every stock passive carries the first beside its body
# colour, so "the model's colour" has to mean the one that is not this.
_METAL = ((0.824, 0.820, 0.781), (0.691, 0.664, 0.598))
_COLOUR = re.compile(r"COLOUR_RGB\s*\(\s*'[^']*'\s*,\s*([\d.Ee+-]+)\s*,\s*([\d.Ee+-]+)\s*,"
                     r"\s*([\d.Ee+-]+)\s*\)")


def model_color(name: str):
    """(r, g, b) an assembled view should paint a model, read out of the model's own STEP --
    or None if the model is not vendored.

    The colour lives in the model: scripts/part_colors.py writes it into the project's own
    (check [10] holds them to its table) and KiCad's library ships it in the stock ones. So a
    renderer that wants a part's colour reads it here rather than keeping a table of its own.

    A PROJECT model carries exactly one colour, and that is the answer; one that carries
    several RAISES, because a model this cannot read must not come back as a plausible guess
    -- which is how the amber LED spent months as a grey block.

    A STOCK model carries its tinned terminations as well (_METAL), which are dropped. Two of
    them then still carry two colours, and in both the darker one is a coat over a lighter
    substrate: the chip resistor's black overglaze on white ceramic, and the 1008 inductor's
    black cap on its grey body. The coat is the face an assembled board shows, so the DARKEST
    is taken. That is KiCad's library convention read off the six families vendored here, not
    a law -- which is why it is not extended to the project's own models.
    """
    path = _IDX.get(name)
    if not path:
        return None
    with open(path, encoding="utf-8", errors="replace") as fh:
        txt = fh.read()
    cols = []
    for m in _COLOUR.finditer(txt):
        c = tuple(round(float(g), 3) for g in m.groups())
        if c not in cols:
            cols.append(c)
    if not cols:
        raise ValueError(f"{name}: the model carries no colour at all -- give it one in "
                         f"scripts/part_colors.py; it would render default grey")
    if os.path.dirname(path).startswith(_MODEL_DIRS[0]):          # the project's own
        if len(cols) != 1:
            raise ValueError(f"{name}: a project model must carry one colour, found {cols}")
        return cols[0]
    body = [c for c in cols
            if not any(all(abs(a - b) < 0.005 for a, b in zip(c, metal)) for metal in _METAL)]
    return min(body or cols, key=sum)


def _blocks(text: str, tag: str = "footprint"):
    """Balanced-paren s-expression blocks; the board is too big for a naive regex."""
    out = []
    # \s not a literal space: footprints are written "(footprint " but tracks are
    # "(segment\n", so a space-only match silently found zero coil segments.
    for m in re.finditer(r'\(' + tag + r'[\s]', text):
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


def _pad_rects(b: str, rot: float):
    """[(pad name, rectangle)] for one footprint block, in the FOOTPRINT's own frame -- the
    pad's (size w h) box about its (at x y), turned by the pad's own angle less the
    footprint's. parts() unions these into a keep-out; cell_tab_lands() picks pads out by
    name. One loop, so the two cannot read a pad two ways."""
    out = []
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
        nm = re.match(r'\(pad\s+"([^"]*)"', pb)
        out.append((nm.group(1) if nm else "", r))
    return out


def _footprints(side: str, pcb: str | None = None):
    """(ref, footprint block, pad box, body box, model file name) for each footprint on one
    side of the board -- the one reading parts() and bodies() both stand on. The mounting
    holes are skipped. `body` and `model` are None when the footprint carries no model, or
    one that is not vendored."""
    with open(pcb or PCB, encoding="utf-8", errors="replace") as fh:
        text = fh.read()

    for b in _blocks(text):
        if not re.search(r'\(footprint "[^"]+"\s*\(layer "' + side, b):
            continue
        rm = re.search(r'\(property "Reference" "([^"]+)"', b)
        ref = rm.group(1) if rm else "?"
        if ref.startswith("MH"):
            continue
        at = re.search(r'\(at (-?[\d.]+) (-?[\d.]+)(?: (-?[\d.]+))?\)', b)
        fx, fy, rot = float(at.group(1)), float(at.group(2)), float(at.group(3) or 0.0)

        rects = [r for _name, r in _pad_rects(b, rot)]
        padbox = None
        if rects:
            loc = unary_union(rects)
            if rot:
                loc = affinity.rotate(loc, rot, origin=(0, 0))
            padbox = affinity.translate(loc, xoff=fx, yoff=fy).envelope

        body, model = None, None
        mm = re.search(r'\(model "([^"]+)"', b)
        if mm:
            name = os.path.basename(mm.group(1))
            ext = model_extent(name)
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
                model = name
        yield ref, b, padbox, body, model


def parts(side: str = "B", pcb: str | None = None):
    """[(ref, keepout_polygon, height_mm_or_None, source)] for one side of the board.

    `source` is "model" when the body came from a 3D model and "pads" when there was none
    (J1, JP1, TP1, SW2 and the solder-bridge blobs) -- a caller that cares about the
    difference can say so rather than silently treating a pad box as a body.
    """
    from part_heights import part_height, UnknownPart

    out = []
    for ref, _b, padbox, body, _model in _footprints(side, pcb):
        source = "model" if body is not None else "pads"
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


def bodies(side: str = "B", pcb: str | None = None):
    """[(ref, body_polygon, model file name)] -- every FITTED part on one side that carries a
    3D model, as the model's own outline.

    This is what a picture of the assembled card draws. It is NOT parts(): that returns the
    keep-out (the body grown to its pads' envelope), for everything on the side, pads-only
    footprints included -- right for cutting a pocket, wrong for drawing a part. A `dnp`
    footprint is left out even if it carries a model, because the assembled board will not
    have the part (CLAUDE.md, "A dnp part's model resolves too").
    """
    out = []
    for ref, b, _padbox, body, model in _footprints(side, pcb):
        if body is None:
            continue
        if re.search(r'\(attr\b[^)]*\bdnp\b', b):
            continue
        out.append((ref, body, model))
    return out


CELL_TAB_PADS = ("Nt", "Pt")     # the cell footprints' own names for the two solder-tab lands


def cell_tab_lands(pcb: str | None = None):
    """[(refdes, pad, land polygon)] -- the solar cells' solder-tab lands, read off the board:
    pads Nt and Pt of every PV* footprint, in board coordinates, sorted.

    They are what the brace's rails were put there to back, and until 2026-11-12 the only
    record of where they are was four coordinates typed into the brace drawing generator
    and typed again into the brace CAD's pocket map: (4.3, 17.0) (46.5, 17.0) (4.3, 71.9)
    (46.5, 71.9). The lands are at y 15.75 and 73.15. Both copies were 1.25 mm out, the
    same way, and nothing could have noticed, because nothing compared them to the board.
    Raises rather than return an empty list: "no tabs" is never the answer for this card."""
    with open(pcb or PCB, encoding="utf-8", errors="replace") as fh:
        text = fh.read()
    out = []
    for b in _blocks(text):
        rm = re.search(r'\(property "Reference" "([^"]+)"', b)
        ref = rm.group(1) if rm else "?"
        if not ref.startswith("PV"):
            continue
        at = re.search(r'\(at (-?[\d.]+) (-?[\d.]+)(?: (-?[\d.]+))?\)', b)
        fx, fy, rot = float(at.group(1)), float(at.group(2)), float(at.group(3) or 0.0)
        for name, r in _pad_rects(b, rot):
            if name in CELL_TAB_PADS:
                if rot:
                    r = affinity.rotate(r, rot, origin=(0, 0))
                out.append((ref, name, affinity.translate(r, xoff=fx, yoff=fy)))
    if not out:
        raise RuntimeError(f"no {'/'.join(CELL_TAB_PADS)} pads on any PV* footprint -- the "
                           f"solar cells' tab lands were not found on the board")
    return sorted(out, key=lambda t: (t[0], t[1]))


COIL_NETS = ("LA", "LB")


def coil_tracks(pcb: str | None = None):
    """[((x1, y1), (x2, y2), width)] -- the NFC coil's copper as the board routes it: every
    LA/LB track on either face, and each via as a zero-length piece of its own diameter.

    Both faces on purpose. The coil crosses between F.Cu and B.Cu, and to a grounded shell
    beside it a turn 0.6 mm further away is the same conductor. Pads on these nets are not
    read: they belong to parts (C9, the tag), and parts() is where a part is measured.

    The ONE reader of the coil. coil_extent() below is its bounding box, and
    fit_rules.boss_coil_cuts() offsets these pieces to cut the mount bosses clear -- so the
    lip and the bosses cannot be held to two different ideas of where the antenna is.

    An ARC on a coil net raises. There are none today, nothing here knows how to offset
    one, and a reader that skipped it would go on reporting a clearance to a coil it had
    not finished reading. Teach this function arcs before routing one."""
    with open(pcb or PCB, encoding="utf-8", errors="replace") as fh:
        text = fh.read()
    num = r"(-?[\d.]+)"
    out = []
    for tag in ("segment", "arc", "via"):
        for b in _blocks(text, tag):
            nm = re.search(r'\(net "([^"]*)"', b)
            if not nm or nm.group(1) not in COIL_NETS:
                continue
            if tag == "arc":
                raise RuntimeError(
                    f"the NFC coil (net {nm.group(1)}) has an arc, and board_parts.coil_tracks() "
                    f"reads only straight tracks and vias -- every coil clearance in the "
                    f"enclosure would be measured to an incomplete coil. Teach it arcs first.")
            if tag == "via":
                at = re.search(rf"\(at {num} {num}\)", b)
                sz = re.search(rf"\(size {num}\)", b)
                if not at or not sz:
                    raise RuntimeError(f"coil via with no position or size: {b[:80]!r}")
                p = (float(at.group(1)), float(at.group(2)))
                out.append((p, p, float(sz.group(1))))
                continue
            s = re.search(rf"\(start {num} {num}\)", b)
            e = re.search(rf"\(end {num} {num}\)", b)
            w = re.search(rf"\(width {num}\)", b)
            if not s or not e or not w:
                raise RuntimeError(f"coil track with no start, end or width: {b[:80]!r}")
            out.append(((float(s.group(1)), float(s.group(2))),
                        (float(e.group(1)), float(e.group(2))), float(w.group(1))))
    if not out:
        raise RuntimeError("no LA/LB coil copper found on the board")
    return out


def coil_extent(pcb: str | None = None):
    """(min_x, max_x) of the NFC coil copper, measured from the board.

    The shell hard-coded COIL_EAST = 48.40 as the coil's east edge. The board's LA/LB
    copper actually reaches x 48.550 -- so the constant was 0.15 mm optimistic and the
    grounded titanium lip, sized against it, overhung the antenna. Derive it instead.
    """
    xs = [x + k * w / 2.0 for a, b, w in coil_tracks(pcb) for x in (a[0], b[0]) for k in (-1, 1)]
    return min(xs), max(xs)


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
