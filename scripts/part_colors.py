#!/usr/bin/env python3
"""One home for the colour of every project 3D model, and the tool that writes it.

    python3 scripts/part_colors.py             # report what each model currently carries
    python3 scripts/part_colors.py --check     # do the models match this table?  (CI gate)
    python3 scripts/part_colors.py --apply     # write the table into the STEP files

WHY THIS EXISTS

`scripts/render.py`'s `populated` target is the one render that keeps its component bodies,
so it is the only README image where a part's COLOUR is data rather than decoration. The nine
models in PCB/solarglow.3dshapes/ are simple 6-face bodies, and a STEP body with no
presentation block gets whatever grey the renderer defaults to.

That is not hypothetical. LA_P47F -- the amber LED, four of them, the single component this
whole card exists to drive -- carried NO colour entity at all and rendered as a grey block in
every assembled view we publish. Nothing caught it because a missing colour is not a missing
file: render.py's `_report_model_resolution` gate counts models that RESOLVE, and an
uncoloured model resolves perfectly.

WHY IT PATCHES COLOUR AND NOTHING ELSE

The bodies are also the reference geometry for consistency check [7], which measures each
part's declared height in enclosure/part_heights.py against that part's own 3D model. If this
script rebuilt the solids, that check would be comparing a height against a model derived
from the same table -- circular, and it would stop being able to catch a wrong height. So
--apply rewrites the COLOUR_RGB triple in place, or appends a presentation block where none
exists, and touches no geometry entity. The bounding boxes come out byte-identical.

WHERE THE COLOURS COME FROM

Each is the part's actual body colour, with the part noted. Package colour is not a styling
choice here -- these renders are what somebody reads to know what the assembled card looks
like.

Eight of the nine entries RECORD a colour the model already carried; they are written down so
there is somewhere for the value to live and something to gate on, not because they were
changed. Exactly one entry -- LA_P47F -- is new, because that model had no colour at all.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHAPES = ROOT / "PCB" / "solarglow.3dshapes"

# model stem -> (r, g, b) 0..1, why
COLORS = {
    # Moulded epoxy IC packages. Near-black with a hint of warmth, which is what a matte
    # QFN/DFN body actually looks like under diffuse light -- not pure #000.
    "AVR64EA28_VQFN28":   ((0.100, 0.100, 0.105), "MCU, matte black epoxy QFN"),
    "AEM10300_QFN28":     ((0.100, 0.100, 0.105), "harvester, matte black epoxy QFN"),
    "MB85RC512TY_DFN8":   ((0.100, 0.100, 0.105), "FRAM, matte black epoxy DFN"),
    "TI_X2SON4_DQN":      ((0.100, 0.100, 0.105), "LDO, matte black epoxy X2SON"),
    "NT3H2211_XQFN8":     ((0.100, 0.100, 0.105), "NFC tag, matte black epoxy XQFN"),
    "ADXL367_CC12":       ((0.100, 0.100, 0.105), "accelerometer, LGA/CC ceramic-black"),
    # The two EXB resistor arrays, 2026-08-08: these REPLACED the vendored KiCad-library
    # models (R_Array_Convex_*.step, multi-colour, 113/221 colour entities). Those were
    # "pre-coloured" and therefore lived outside this table -- and their near-black bodies
    # rendered indistinguishable from bare mask at README scale, so both arrays READ AS
    # EMPTY LANDS in every populated view. The LA_P47F lesson, one ring out: a model can
    # carry colour and still be illegible, and only a table entry gives it a gate. House
    # 6-face bodies now, white-ceramic like the real EXB substrate (and like the discrete
    # R bodies, which is why those always read).
    "EXB28V_4x0402":      ((0.850, 0.850, 0.820), "RN1 4x150R ballast array, EXB white ceramic"),
    "EXB24V_2x0402":      ((0.850, 0.850, 0.820), "RN2 2x4.7k pull-up array, EXB white ceramic"),

    # THE FIX. Amber InGaAlP LED in a water-clear-to-amber lens. This is the one part whose
    # colour is the product: four of them backlight the monogram. It carried no colour entity
    # at all, so every assembled render published it as a grey block.
    "LA_P47F":            ((0.960, 0.620, 0.090), "amber LED lens (OSRAM LA P47F, 590 nm)"),

    # SCHURTER SCPC supercaps: laser-marked aluminium can, mid grey. Two of the four are the
    # tall WS17 and two the SS17; same finish.
    "SCHURTER_SCPC_WS17": ((0.580, 0.590, 0.610), "supercap, bare aluminium can"),
    "SCHURTER_SCPC_SS17": ((0.580, 0.590, 0.610), "supercap, bare aluminium can"),

    # MONOCRYSTALLINE silicon (ANYSOLAR IXOLAR SolarMD). This said "indoor amorphous-Si PV"
    # until 2026-08-09 and was wrong on BOTH counts, in the inverted direction: c-Si is not
    # a-Si, and it is the WRONG absorber for room light, not a cell chosen for it. ~35-40% of
    # its photocurrent comes from beyond 700 nm, where LED and fluorescent lighting emit
    # essentially nothing, and at indoor irradiance its fill factor collapses (measured
    # mono-Si: 59-67% at 7200 lux -> 36-42% at 220 lux). ANYSOLAR publishes NO indoor or
    # low-lux data for any IXOLAR part -- the "low light" line is marketing with no datasheet
    # behind it. Kept as a comment rather than deleted because a render colour table is
    # exactly where a wrong part story survives unchallenged.
    # The COLOUR is unchanged and still correct: an AR-coated mono cell is near-black with a
    # blue cast, which is what these numbers say.
    "SM141K06TF":         ((0.045, 0.055, 0.090), "monocrystalline PV cell, dark blue-black"),

    # The C25-C27 low-profile 1206 (2026-08-06): fired-ceramic MLCC body, light tan. Exported
    # with this colour by make_3d_models.py; recorded here so check [10] gates it like the rest.
    "MURATA_GRM319_1206LP": ((0.520, 0.420, 0.300), "MLCC ceramic body, GRM319 LP 1206 (C25-C27)"),
    "TI_DSBGA4_YFP":      ((0.100, 0.100, 0.105), "load switch, bare-die DSBGA (U6 ultrathin swap)"),
    "DIODES_SOT523":      ((0.100, 0.100, 0.105), "Q2 gate FET, moulded SOT-523 (missing-stock-model class, 3rd arrival)"),
}

# \s* between the components: STEP wraps long lines, and several of these files split the
# triple across two. A regex without it reported "NO COLOUR" for five models that had one.
RGB = re.compile(r"(COLOUR_RGB\('[^']*',)\s*([\d.Ee+-]+)\s*,\s*([\d.Ee+-]+)\s*,\s*([\d.Ee+-]+)\s*(\))", re.S)
ENTITY = re.compile(r"^#(\d+)\s*=", re.M)
BREP = re.compile(r"^#(\d+)\s*=\s*MANIFOLD_SOLID_BREP", re.M)
# The context must come from the shape representation that OWNS the solid, not from the first
# GEOMETRIC_REPRESENTATION_CONTEXT in the file. LA_P47F's first one is #42, a 2D PARAMETRIC
# context used by its p-curves; styling a 3D solid against it is wrong, and the eight models
# that already carry colour all point at the 3D context their ADVANCED_BREP_SHAPE_REPRESENTATION
# names. Matched across newlines because STEP wraps these.
ASBR = re.compile(r"ADVANCED_BREP_SHAPE_REPRESENTATION\('[^']*',\s*\(([^)]*)\)\s*,\s*#(\d+)\s*\)", re.S)


def read(stem: str) -> tuple[Path, str]:
    p = SHAPES / f"{stem}.step"
    if not p.exists():
        sys.exit(f"part_colors: {p.relative_to(ROOT)} is missing")
    return p, p.read_text(errors="strict")


def current(src: str):
    m = RGB.search(src)
    return (float(m.group(2)), float(m.group(3)), float(m.group(4))) if m else None


def presentation_block(src: str, rgb) -> str:
    """Append a STYLED_ITEM chain for a body that has none, numbered after the last entity.

    The chain is the same one the other eight models already carry -- copied in structure so a
    reader diffing two of these files sees identical shapes. It attaches to the file's
    MANIFOLD_SOLID_BREP and reuses its GEOMETRIC_REPRESENTATION_CONTEXT, because a
    presentation representation has to live in the same context as the geometry it styles.
    """
    brep = BREP.search(src)
    if not brep:
        sys.exit("part_colors: no MANIFOLD_SOLID_BREP to attach a colour to")
    b = brep.group(1)
    ctx = next((m.group(2) for m in ASBR.finditer(src)
                if f"#{b}" in re.split(r"[,\s]+", m.group(1).strip())), None)
    if ctx is None:
        sys.exit(f"part_colors: no ADVANCED_BREP_SHAPE_REPRESENTATION lists #{b}")
    n = max(int(m.group(1)) for m in ENTITY.finditer(src))
    c = ctx
    r, g, bl = rgb
    return (
        f"#{n+1} = MECHANICAL_DESIGN_GEOMETRIC_PRESENTATION_REPRESENTATION('',(#{n+2})\n"
        f"  ,#{c});\n"
        f"#{n+2} = STYLED_ITEM('color',(#{n+3}),#{b});\n"
        f"#{n+3} = PRESENTATION_STYLE_ASSIGNMENT((#{n+4}));\n"
        f"#{n+4} = SURFACE_STYLE_USAGE(.BOTH.,#{n+5});\n"
        f"#{n+5} = SURFACE_SIDE_STYLE('',(#{n+6}));\n"
        f"#{n+6} = SURFACE_STYLE_FILL_AREA(#{n+7});\n"
        f"#{n+7} = FILL_AREA_STYLE('',(#{n+8}));\n"
        f"#{n+8} = FILL_AREA_STYLE_COLOUR('',#{n+9});\n"
        f"#{n+9} = COLOUR_RGB('',{r:.12g},{g:.12g},{bl:.12g});\n"
    )


def apply_one(src: str, rgb) -> tuple[str, str]:
    r, g, b = rgb
    if RGB.search(src):
        return RGB.sub(lambda m: f"{m.group(1)}{r:.12g},{g:.12g},{b:.12g}{m.group(5)}", src, count=1), "recoloured"
    i = src.rindex("ENDSEC;")
    return src[:i] + presentation_block(src, rgb) + src[i:], "colour ADDED (had none)"


def hexof(rgb):
    return "#" + "".join(f"{round(255 * c):02X}" for c in rgb)


PRESENTATION = re.compile(
    r"^(MECHANICAL_DESIGN_GEOMETRIC_PRESENTATION_REPRESENTATION|STYLED_ITEM"
    r"|PRESENTATION_STYLE_ASSIGNMENT|SURFACE_STYLE_USAGE|SURFACE_SIDE_STYLE"
    r"|SURFACE_STYLE_FILL_AREA|FILL_AREA_STYLE|FILL_AREA_STYLE_COLOUR|COLOUR_RGB)")


def entities(src: str):
    """Split the DATA section into whole entities: `#n = ...;` plus any wrapped lines.

    Entity-wise, not line-wise. A line-based split cannot tell a STEP continuation line
    (`  ,#345);`) from its own entity, and the first cut of geometry_digest below did exactly
    that -- so appending a presentation block, whose header wraps, changed the "geometry"
    hash and the safety check refused a write that was in fact geometry-clean. The guard was
    right to fire; the guard was what was wrong.
    """
    out, cur = [], None
    for ln in src.splitlines():
        # Section markers END an entity; they are not continuations of it. Without this,
        # ENDSEC; glued itself onto whichever entity happened to be last, so inserting a
        # block before it moved ENDSEC to a different parent and changed the hash of an
        # entity nothing had touched.
        if re.match(r"^#\d+\s*=", ln) or re.match(r"^(ENDSEC;|END-ISO|DATA;|HEADER;|ISO-)", ln):
            if cur is not None:
                out.append(cur)
            cur = ln if ln.startswith("#") else None
            if cur is None:
                out.append(ln)
        elif cur is not None:
            cur += "\n" + ln
        else:
            out.append(ln)
    if cur is not None:
        out.append(cur)
    return out


def geometry_digest(src: str) -> str:
    """Hash of every NON-presentation entity, so --apply can prove it changed no geometry."""
    import hashlib
    keep = [e for e in entities(src)
            if not PRESENTATION.match(re.sub(r"^#\d+\s*=\s*", "", e))]
    return hashlib.sha1("\n".join(keep).encode()).hexdigest()[:12]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    stray = sorted({p.stem for p in SHAPES.glob("*.step")} - set(COLORS))
    if stray:
        print(f"  ERROR: {len(stray)} model(s) in {SHAPES.relative_to(ROOT)} have no entry in "
              f"COLORS -- they would render whatever grey the renderer defaults to: "
              f"{', '.join(stray)}")

    drift = []
    for stem, (rgb, why) in sorted(COLORS.items()):
        path, src = read(stem)
        have = current(src)
        same = have is not None and all(abs(a - b) < 5e-3 for a, b in zip(have, rgb))
        state = "ok" if same else ("NO COLOUR" if have is None else f"is {hexof(have)}")
        print(f"  {stem:22} {hexof(rgb)}  {state:12} {why}")
        if same:
            continue
        drift.append(stem)
        if args.apply:
            before = geometry_digest(src)
            out, what = apply_one(src, rgb)
            if geometry_digest(out) != before:
                sys.exit(f"part_colors: {stem} -- geometry digest changed; refusing to write")
            path.write_text(out)
            print(f"  {'':22} -> {what}, geometry unchanged ({before})")

    if stray:
        return 1
    if args.check:
        print(f"  {'MATCH' if not drift else 'DRIFT — run --apply'}"
              + ("" if not drift else f": {', '.join(drift)}"))
        return 0 if not drift else 1
    if not args.apply and drift:
        print(f"  ({len(drift)} model(s) differ from the table — pass --apply to write)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
