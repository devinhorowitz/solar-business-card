#!/usr/bin/env python3
"""Generate STEP bodies for the parts KiCad has no model for.

    pip install cadquery
    python3 scripts/make_3d_models.py            # -> PCB/solarglow.3dshapes/*.step
    python3 scripts/make_3d_models.py --list
    python3 scripts/make_3d_models.py --attach   # write (model ...) into the .kicad_pcb
    python3 scripts/make_3d_models.py --attach --dry-run

WHY THESE EXIST

The brace and back-shell are dimensioned against the parts they clear, so the
board's 3D view and its STEP export have to carry real bodies. KiCad ships models
for its own footprints, but every `solarglow:*` footprint is drawn for this
project and has none, so the tallest, most fit-critical parts — the supercaps and
the solar cells — were simply absent from the model.

WHAT THESE ARE, AND ARE NOT

Envelope solids, not cosmetic models. Each is the part's **maximum** outline at its
**maximum** height, because the only question being asked is "does the enclosure
clear it?". A pretty model at the wrong height would be worse than useless here.
Do not read them as appearance references.

WHERE THE NUMBERS COME FROM — every dimension below is traceable, none invented:

  SCPC SS17/WS17   PCB/solarglow.pretty/SCHURTER_SCPC_*.kicad_mod `descr`, which
                   quotes the SCHURTER datasheet: cells 39.0 x 17.0 and 28.5 x 17.0,
                   both **1.70 mm max** thick, with finish-coated locator tabs
                   ~2.75 mm past each end that are NOT solder pads. The 1.70 is the
                   same number enclosure/README.md builds the 1.80 mm cavity on.
  SM141K06TF       datasheet: "Dimensions (W x L x H): 42 x 23 x 1.2 +/- 0.3 [mm]".
                   Modelled at the +0.3 worst case = 1.5 mm, since this is a
                   clearance solid.
  LA_P47F          outline 3.4 x 1.9 from PCB/README.md's BOM table ("SMD, 3.4x1.9 mm")
                   and solar-glow-drh-design-notes.md, which sources it to the
                   datasheet p.12 dimensional drawing (a 3.4 x 1.9 outline around a
                   Ø2.5 round body). Height 0.83 from
                   PCB/PCB-side-notes-brace-direction.md §2, whose heights are stated
                   to be datasheet-verified maxima.
  ADXL367_CC12     PCB/README.md: "LGA-12 CC-12-4 (2.2x2.3x0.87 mm)". The 0.87 is
                   corroborated by the brace height map.
  NT3H2211_XQFN8   PCB/README.md and the brace height map agree: "SOT902-3,
                   1.6 x 1.6 x 0.5 verbatim".
  AVR64EA28_VQFN28 `datasheets/U1  AVR64EA28-E-STX  $1.23.pdf` §38.5, 28-Pin VQFN:
                   D and E are 4.00 BSC, "Overall Height A" is 0.80 / 0.90 / **1.00
                   MAX**. Modelled at the max, and independently corroborated by
                   PCB-side-notes-brace-direction.md §2, which budgets U1 at 1.0.
  AEM10300_QFN28   `datasheets/U8  10AEM10300C0000  $3.77.pdf` (DS-AEM10300-v1.4) §15.1 Figure 17, the
                   QFN 28-pin 4x4 package drawing: body 4.000 +/- 0.05 square,
                   thickness **0.800 +/- 0.05**. Modelled at the max, 0.85.

U1 AND U8 ARE NOT THE SAME HEIGHT, despite sharing a 4x4 QFN-28 land and a footprint
name: 1.00 max vs 0.85 max, 0.15 mm apart, each read off its own datasheet. They were
briefly modelled with one shared 1.00 mm solid, which overstated U8. A single
"QFN-28 4x4" body is the wrong abstraction and no longer exists here.

WHY NEITHER IS THE STOCK KiCad QFN. KiCad ships
`Package_DFN_QFN.3dshapes/QFN-28-1EP_4x4mm_P0.4mm_EP2.4x2.4mm.step`, and it is a
prettier model. Measured, it is **4.000 x 4.000 x 0.770 mm** — 0.23 mm short of U1's
max and 0.08 mm short of U8's. For a part whose only job in the 3D view is to answer
"does the brace clear it?", a model that understates height is worse than no model,
so both get a box at their own documented maximum instead.

THE END TABS ARE DELIBERATELY NOT MODELLED — and that is a finding, not laziness.

The footprint `descr` puts the locator tabs ~2.75 mm past each end. Modelled flat
and in-plane, that makes **all four supercaps overhang the board edge**:

    SC1  cell y  1.75..40.75   with tabs -1.00..43.50   ->  1.00 mm past y=0
    SC2  cell y  2.65..31.15   with tabs -0.10..33.90   ->  0.10 mm past y=0
    SC3  cell y 47.98..86.98   with tabs 45.23..89.73   ->  0.83 mm past y=88.9
    SC4  cell y 58.55..87.05   with tabs 55.80..89.80   ->  0.90 mm past y=88.9

PCB/README.md describes them as "**folded** end tabs ... coated, non-solderable
locators", i.e. they do not lie flat in the board plane, and the footprint's own
courtyard covers the 39.0 mm cell and NOT the tabs. So a flat 2.75 mm extension is
almost certainly the wrong shape, and shipping it would invent a board-edge
overhang for the enclosure to design around.

The cell body is the number that is solidly sourced, so that is what these solids
are. **Open question for the enclosure work: what is the tabs' real folded
geometry, and do they in fact reach past the board edge?** Until that is measured
on a real cell, treat the envelope near the short edges as unverified.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "PCB" / "solarglow.3dshapes"

# name -> (builder, human description)
#   All solids are centred on the footprint origin in X/Y and sit on z=0 growing +Z,
#   which is what KiCad expects for a part on the board's top surface; KiCad mirrors
#   it automatically for footprints placed on the back.
# ---- appearance ----------------------------------------------------------------------
# STEP carries colour as COLOUR_RGB + STYLED_ITEM, and KiCad's raytracer honours it. Until
# now these solids were exported with cq.exporters.export(), which writes geometry only, so
# every project part rendered in KiCad's default grey regardless of what it actually is.
#
# Values are the real materials, not decoration -- the renders are what the board is judged
# by, and a silver-looking supercap next to a black-looking IC is information.
#
# COLOUR_RGB is a DIFFUSE ALBEDO, and the raytracer's response to it is compressive at the dark
# end and clips hard at the bright end. Measured in the shipped render: albedo 0.045/0.055/0.090
# (the cells) lands at 32/40/47, and 0.100 (the IC bodies) at 47 -- but 0.780 for the supercap
# cans came out at a flat, blown-out 254 on every pixel of all four. That is not "silver", it is
# a hole in the picture: before the colour was set at all they were KiCad's default grey at 197,
# which at least had form. There is no specular or metalness channel in a STEP colour, so the
# only lever for "bright metal" is lightness, and it has to stay clear of the clip to read as a
# surface. 0.58 is a deliberate step back from the ceiling.
COL_SOLAR   = (0.045, 0.055, 0.090)   # monocrystalline cell: near-matte black, hint of blue
COL_IC      = (0.100, 0.100, 0.105)   # moulded black epoxy/polymer IC body
COL_SUPERCAP = (0.580, 0.590, 0.610)  # SCPC can: bright silver, below the raytracer's clip
COL_MLCC    = (0.520, 0.420, 0.300)   # fired ceramic MLCC body: light tan, safely off the clip

SPECS = {
    "SCHURTER_SCPC_SS17": dict(
        color=COL_SUPERCAP,
        body=(39.0, 17.0, 1.70), tab=None,
        desc="SCPC SS17 supercap, 1.8 F — cell 39.0 x 17.0 x 1.70 max (tabs excluded, see header)",
    ),
    "SCHURTER_SCPC_WS17": dict(
        color=COL_SUPERCAP,
        body=(28.5, 17.0, 1.70), tab=None,
        desc="SCPC WS17 supercap, 1.0 F — cell 28.5 x 17.0 x 1.70 max (tabs excluded, see header)",
    ),
    "SM141K06TF": dict(
        color=COL_SOLAR,
        body=(42.0, 23.0, 1.50), tab=None,
        desc="ANYSOLAR SM141K06TF cell — 42 x 23 x 1.2 +0.3 (modelled at max 1.5)",
    ),
    "LA_P47F": dict(
        body=(3.4, 1.9, 0.83), tab=None,
        desc="ams OSRAM LA P47F reverse-mount amber LED — outline 3.4 x 1.9, height 0.83 max",
    ),
    "ADXL367_CC12": dict(
        color=COL_IC,
        body=(2.2, 2.3, 0.87), tab=None,
        desc="ADI ADXL367 accelerometer, LGA-12 CC-12-4 — 2.2 x 2.3 x 0.87",
    ),
    "NT3H2211_XQFN8": dict(
        color=COL_IC,
        body=(1.6, 1.6, 0.50), tab=None,
        desc="NXP NT3H2211 NTAG I2C plus, XQFN8 SOT902-3 — 1.6 x 1.6 x 0.5",
    ),
    "AVR64EA28_VQFN28": dict(
        color=COL_IC,
        body=(4.0, 4.0, 1.00), tab=None,
        desc="U1 AVR64EA28, 28-pin VQFN 4x4 — overall height A max 1.00",
    ),
    "AEM10300_QFN28": dict(
        color=COL_IC,
        body=(4.0, 4.0, 0.85), tab=None,
        desc="U8 AEM10300, QFN-28 4x4 — thickness 0.800 +/- 0.05, modelled at max 0.85",
    ),
    "MB85RC512TY_DFN8": dict(
        color=COL_IC,
        body=(5.0, 6.0, 0.90), tab=None,
        desc="U7 MB85RC512TY FRAM, LCC-8P-M05 DFN-8 — 5.00 x 6.00 x 0.90 MAX",
    ),
    "TI_X2SON4_DQN": dict(
        color=COL_IC,
        body=(1.05, 1.05, 0.40), tab=None,
        desc="U9 TPS7A0233PDQNR, X2SON-4 DQN0004A — 1.05 max square x 0.40 MAX height",
    ),
    # The low-profile 1206 the C25-C27 respin rides on (decided 2026-08-06): Murata GRM319
    # is 3.2 x 1.6 x 0.85 +/-0.10, so 0.95 MAX — modelled at the max, same doctrine as U9/U8:
    # the envelope is the worst case in every axis, which is the only question the brace and
    # interference_drc ask. KiCad's generic C_1206_3216Metric body measures ~1.6, which would
    # (a) fail check [7] against a 0.95 declaration and (b) false-fail interference_drc's
    # ray-cast against a pocket cut for 0.95 — the reason this model exists rather than a
    # MODEL_NOTES waiver (the C9 lesson: waivers are keyed by model and blind every user of it).
    "MURATA_GRM319_1206LP": dict(
        color=COL_MLCC,
        body=(3.2, 1.6, 0.95), tab=None,
        desc="C25/C26/C27 Murata GRM319 low-profile 1206 — 3.2 x 1.6 x 0.85 +/-0.10 (0.95 MAX)",
    ),
    # The ultrathin U6 (2026-08-06): TPS22916C DSBGA-4, TI YFP0004 drawing 4223507/A —
    # body D/E 0.75-0.81 square, "DSBGA - 0.5 mm max height" in the title block (balls
    # included: 0.13-0.19 ball + die). Modelled at the max envelope like every solid here.
    # The model rides in solarglow:TPS22916_YFP0004 itself (no ATTACH entry needed —
    # unlike U9, whose STOCK footprint named a model upstream never shipped).
    "TI_DSBGA4_YFP": dict(
        color=COL_IC,
        body=(0.81, 0.81, 0.50), tab=None,
        desc="U6 TPS22916CYFPR, DSBGA-4 YFP0004 (4223507/A) — 0.75-0.81 sq, 0.5 MAX incl. balls",
    ),
}

# refdes -> (model path as KiCad should store it, Z rotation in degrees)
#
# Every footprint below sits at orientation 0 (U3 at 180, but its body is a box), so
# the solids are built on the footprint's own axes and need no rotation. All are on
# the back — KiCad mirrors a model for a flipped footprint by itself, so these are
# still built growing +Z from z=0.
PRJ = "${KIPRJMOD}/solarglow.3dshapes"
ATTACH = {
    "D2": (f"{PRJ}/LA_P47F.step", 0),
    "D3": (f"{PRJ}/LA_P47F.step", 0),
    "D4": (f"{PRJ}/LA_P47F.step", 0),
    "D5": (f"{PRJ}/LA_P47F.step", 0),
    "U1": (f"{PRJ}/AVR64EA28_VQFN28.step", 0),
    "U8": (f"{PRJ}/AEM10300_QFN28.step", 0),
    "U3": (f"{PRJ}/ADXL367_CC12.step", 0),
    "U5": (f"{PRJ}/NT3H2211_XQFN8.step", 0),
    # U7 already carried a model, and it was BROKEN: it named
    # `Package_DFN_QFN.3dshapes/DFN-8-1EP_6x5mm_Pitch1.27mm.step`, which no KiCad 10 library
    # ships -- the naming convention changed to `..._P1.27mm_EP4x4mm`. So U7 has been rendering
    # and exporting with no body at all. It is also the wrong package family: every `-1EP` model
    # carries an exposed pad and U7's footprint has 8 pads and no EP, and the nearest stock part
    # measures 0.870 tall against U7's 0.90 MAX. Own solid, at the datasheet maximum.
    "U7": (f"{PRJ}/MB85RC512TY_DFN8.step", 0),
    # U9 gained a model reference on 2026-08-05 when it moved to the X2SON package, and that
    # reference was BROKEN ON ARRIVAL -- through no fault of the board. KiCad's own
    # `Package_SON.pretty/Texas_X2SON-4_1x1mm_P0.65mm.kicad_mod` names
    # `${KICAD10_3DMODEL_DIR}/Package_SON.3dshapes/Texas_X2SON-4_1x1mm_P0.65mm.step`, and that
    # file DOES NOT EXIST in kicad-packages3D: the library ships exactly one X2SON solid,
    # `X2SON-8_1.4x1mm_P0.35mm.step`, an 8-pin 1.4x1.0 part. So the upstream footprint carries a
    # dangling model path, the board inherited it verbatim, and U9 rendered with no body at all
    # -- the same failure mode U7 had, arriving by a different route. Own solid, at the
    # datasheet maximum: TI SBVS277C package outline DQN0004A (drawing 4215302/E), sheet titled
    # "X2SON - 0.4 mm max height", body 0.95-1.05 square. Modelled at 1.05 x 1.05 x 0.40 so the
    # envelope is the worst case in every axis, which is the only question the brace asks.
    "U9": (f"{PRJ}/TI_X2SON4_DQN.step", 0),
}


def build(name: str, spec: dict):
    import cadquery as cq
    L, W, H = spec["body"]
    solid = cq.Workplane("XY").box(L, W, H, centered=(True, True, False))
    if spec["tab"]:
        tl, tw, th = spec["tab"]
        # Tabs sit centred on the cell's thickness, projecting past each end.
        z0 = (H - th) / 2.0
        for sign in (1, -1):
            solid = solid.union(
                cq.Workplane("XY")
                .box(tl, tw, th, centered=(True, True, False))
                .translate((sign * (L + tl) / 2.0, 0, z0))
            )
    return solid


BOARD = ROOT / "PCB" / "solar-glow-drh-v4_0.kicad_pcb"


def _blocks(txt: str, tag: str):
    """(start, end) of every top-level `(tag ...)` block, paren-matched, string-aware."""
    import re
    out = []
    for m in re.finditer(r"(?m)^\s*\(%s[\s(]" % tag, txt):
        i = txt.index("(", m.start())
        depth, instr, esc = 0, False, False
        for j in range(i, len(txt)):
            c = txt[j]
            if instr:
                if esc:
                    esc = False
                elif c == "\\":
                    esc = True
                elif c == '"':
                    instr = False
                continue
            if c == '"':
                instr = True
            elif c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
                if depth == 0:
                    out.append((i, j + 1))
                    break
    return out


def _model_span(blk: str):
    """(start, end) of the first `(model ...)` block inside a footprint block."""
    import re
    m = re.search(r'\(model "', blk)
    i = blk.rindex("(", 0, m.end())
    depth, instr, esc = 0, False, False
    for j in range(i, len(blk)):
        c = blk[j]
        if instr:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                instr = False
            continue
        if c == '"':
            instr = True
        elif c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return i, j + 1
    raise ValueError("unbalanced model block")


def attach(dry_run: bool = False) -> int:
    """Write a `(model ...)` into each footprint in ATTACH that has none.

    Byte-safe and idempotent. The board alternates between CRLF and LF depending on
    who saved it last, so the line ending is DETECTED, never assumed, and only the
    inserted text is new — nothing else in the file is rewritten. A footprint that
    already carries a model is left alone and reported, so running this after a
    KiCad round-trip is a no-op rather than a duplicate.
    """
    import re
    raw = BOARD.read_bytes()
    crlf = raw.count(b"\r\n")
    if crlf and crlf != raw.count(b"\n"):
        sys.exit(f"make_3d_models: {BOARD.name} has mixed line endings; refusing to edit")
    nl = "\r\n" if crlf else "\n"
    txt = raw.decode("utf-8").replace("\r\n", "\n")

    edits, skipped, replaced, missing = [], [], [], set(ATTACH)
    for a, b in _blocks(txt, "footprint"):
        blk = txt[a:b]
        m = re.search(r'\(property "Reference" "([^"]+)"', blk)
        if not m or m.group(1) not in ATTACH:
            continue
        ref = m.group(1)
        missing.discard(ref)
        path, rot = ATTACH[ref]
        have = re.search(r'\(model "([^"]+)"', blk)
        if have:
            if have.group(1) == path:
                skipped.append(ref)
                continue
            # Present but NOT what the mapping says. That is drift, and silently leaving it is
            # how U7 spent this long pointing at a model file that does not exist. Replace it.
            span = _model_span(blk)
            replaced.append((ref, have.group(1)))
            edits.append((a + span[0], a + span[1], path, rot, ref))
            continue
        chunk = (
            f'\t\t(model "{path}"{nl}'
            f"\t\t\t(offset{nl}\t\t\t\t(xyz 0 0 0){nl}\t\t\t){nl}"
            f"\t\t\t(scale{nl}\t\t\t\t(xyz 1 1 1){nl}\t\t\t){nl}"
            f"\t\t\t(rotate{nl}\t\t\t\t(xyz 0 0 {rot}){nl}\t\t\t){nl}"
            f"\t\t){nl}"
        )
        # Anchor on the footprint's last child token so the model lands where KiCad
        # writes it; fall back to just inside the closing paren.
        anchor = blk.rfind("(embedded_fonts ")
        if anchor >= 0:
            at = a + blk.index(")", anchor) + 1
        else:
            at = a + blk.rindex(")")
        edits.append((at, at, path, rot, ref))

    if missing:
        sys.exit(f"make_3d_models: refdes not found on the board: {' '.join(sorted(missing))}")
    for ref in sorted(skipped):
        print(f"  skip   {ref}: already has the right model")
    for ref, was in sorted(replaced):
        print(f"  FIX    {ref}: was {was}")
    if not edits:
        print("  nothing to do — every mapped footprint already carries the right model")
        return 0

    def _chunk(path, rot):
        return ('\t\t(model "%s"\n' % path
                + "\t\t\t(offset\n\t\t\t\t(xyz 0 0 0)\n\t\t\t)\n"
                + "\t\t\t(scale\n\t\t\t\t(xyz 1 1 1)\n\t\t\t)\n"
                + "\t\t\t(rotate\n\t\t\t\t(xyz 0 0 %s)\n\t\t\t)\n" % rot
                + "\t\t)\n")

    for st, en, path, rot, ref in sorted(edits, reverse=True):
        body = _chunk(path, rot)
        if st == en:                       # insertion
            txt = txt[:st] + body + txt[st:]
            print(f"  attach {ref}: {path.rsplit('/', 1)[1]}")
        else:                              # replacement of an existing (model ...)
            txt = txt[:st] + body.strip("\n").lstrip("\t") + txt[en:]
            print(f"  replace {ref}: -> {path.rsplit('/', 1)[1]}")
    out = txt.replace("\n", nl).encode("utf-8")
    if dry_run:
        print(f"  --dry-run: would write {len(out):,} bytes ({len(out) - len(raw):+,})")
        return 0
    BOARD.write_bytes(out)
    print(f"  wrote {BOARD.relative_to(ROOT)}  ({len(out) - len(raw):+,} bytes, {nl!r} preserved)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--attach", action="store_true",
                    help="write (model ...) into the board for every refdes in ATTACH")
    ap.add_argument("--dry-run", action="store_true", help="with --attach, do not write")
    args = ap.parse_args()

    if args.attach:
        return attach(dry_run=args.dry_run)

    if args.list:
        for n, s in SPECS.items():
            L, W, H = s["body"]
            print(f"{n:24s} {L} x {W} x {H} mm   {s['desc']}")
        return 0

    try:
        import cadquery  # noqa: F401
    except ImportError:
        sys.exit("make_3d_models: needs cadquery  ->  pip install cadquery")

    import cadquery as cq
    OUT.mkdir(parents=True, exist_ok=True)
    for name, spec in SPECS.items():
        solid = build(name, spec)
        dest = OUT / f"{name}.step"
        before = dest.read_text() if dest.exists() else None
        col = spec.get("color")
        if col:
            # An Assembly is the only export path that writes COLOUR_RGB/STYLED_ITEM.
            assy = cq.Assembly(solid, name=name, color=cq.Color(*col))
            try:
                assy.export(str(dest))          # cadquery >= 2.5
            except AttributeError:
                assy.save(str(dest))
        else:
            cq.exporters.export(solid, str(dest))
        bb = solid.val().BoundingBox()
        # STEP stamps a write time into FILE_NAME, so an unchanged solid still comes
        # back as a modified file. Put the old bytes back when only that line moved —
        # otherwise every run dirties the tree and the real geometry changes hide in
        # the noise.
        if before is not None and _same_geometry(before, dest.read_text()):
            dest.write_text(before)
            print(f"  {dest.relative_to(ROOT)}  unchanged")
            continue
        print(f"  {dest.relative_to(ROOT)}  "
              f"{bb.xlen:.2f} x {bb.ylen:.2f} x {bb.zlen:.2f} mm  "
              f"({dest.stat().st_size:,} bytes)")
    return 0


def _same_geometry(a: str, b: str) -> bool:
    """Equal STEP files ignoring the FILE_NAME write timestamp."""
    import re
    strip = lambda s: re.sub(r"(?m)^FILE_NAME\('[^']*','[^']*'", "FILE_NAME(", s)
    return strip(a) == strip(b)


if __name__ == "__main__":
    raise SystemExit(main())
