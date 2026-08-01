#!/usr/bin/env python3
"""
check_consistency.py -- drift guard for SOLAR-GLOW DRH.

Cross-checks the human docs and the firmware against the KiCad design, so a
change to one that isn't mirrored in the others fails loudly (in CI or locally):

  [1] PIN CONTRACT  -- the pad -> net map documented in firmware/board.h must
      match the schematic netlist for the MCU (U1).            [ERROR on drift]
  [2] BOM PARITY    -- every reference in the CI-generated BOM must be a real
      component in the netlist (no phantom BOM lines).         [ERROR on drift]
  [4] PACKAGE FIT   -- the package the BOM orders must match the land the board
      draws (0402 part on a 0402 land).                        [ERROR on drift]
  [5] MODEL REFS -- every (model ...) path resolves, AND every stock model is
      vendored in PCB/kicad-3dmodels/ (what CI renders from).  [ERROR on drift]
  [6] MASK ART -- the generated front soldermask art still matches the routing it
      depicts (scripts/mask_art.py).                          [ERROR on drift]
  [7] PART HEIGHTS -- every enclosure pocket depth clears the part it is cut
      for, measured against that part's own 3D model.         [ERROR on drift]
  [8] ENCLOSURE FIT -- the brace, the shell lip and all eight M2 bosses clear
      every B-side part in XY, and the bosses keep their thread. [ERROR on drift]
  [9] DOC IMAGERY -- every image any .md displays must exist AND be produced by
      a generator this repo runs, not committed by hand.       [ERROR on drift]
  [10] PART COLOURS -- every project 3D model carries the colour scripts/part_colors.py
      gives it; an uncoloured body renders default grey.       [ERROR on drift]
  [3] DOC FILE REFS -- every solar-glow-drh-*.kicad_* file named in board.h,
      README.md, or firmware/README.md must actually exist.    [WARN on drift]
  [11] CITED PATHS -- every path any .md cites must exist, be marked historical
      in its own sentence, or carry a reason in EXPECTED_ABSENT. [ERROR on drift]
  [12] FOOTPRINT SIDES -- every footprint sits on the side the FRONT_SIDE
      snapshot records; a side flip must update the snapshot.  [ERROR on drift]

Usage:   python3 scripts/check_consistency.py
Exit:    nonzero if any ERROR-level check fails; warnings do not fail the build.
Needs:   kicad-cli (on PATH, in $KICAD_CLI, or the macOS KiCad.app bundle).

The pin map is parsed straight out of board.h's own header table, so this
script never carries a second copy of the truth -- it only checks that the
copies already in the repo agree with the board.
"""
import os
import re
import sys
import csv
import glob
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCH = os.path.join(ROOT, "PCB", "solar-glow-drh-v4_0.kicad_sch")
# The v4_0 managed-solar rework has now diverged from v3_0 (schematic synced to the AEM10300
# board: clamp/blocking parts removed, AEM island added), so parity is checked against the
# CI-regenerated v4_0 BOM. kibot rebuilds it on each PCB push. See v4-aem10300-prewiring.md.
BOM = os.path.join(ROOT, "Generated", "fabdocs", "solar-glow-drh-v4_0-bom.csv")
PCB = os.path.join(ROOT, "PCB", "solar-glow-drh-v4_0.kicad_pcb")
MCU = "U1"

errors, warnings = [], []


def err(m):
    errors.append(m)
    print("  ERROR:  " + m)


def warn(m):
    warnings.append(m)
    print("  WARN:   " + m)


def ok(m):
    print("  ok:     " + m)


def find_kicad_cli():
    for c in (os.environ.get("KICAD_CLI"), "kicad-cli",
              "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"):
        if c and (shutil.which(c) or os.path.exists(c)):
            return c
    sys.exit("FATAL: kicad-cli not found (set $KICAD_CLI).")


def export_netlist(cli):
    """Return (MCU pin->net, set of component refs, ref->footprint) from the schematic."""
    with tempfile.TemporaryDirectory() as td:
        out = os.path.join(td, "nl.xml")
        subprocess.run([cli, "sch", "export", "netlist", "--format", "kicadxml",
                        "-o", out, SCH], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        root = ET.parse(out).getroot()
        comps = {c.get("ref") for c in root.find("components").findall("comp")}
        sch_fps = {}
        for c in root.find("components").findall("comp"):
            fp = c.find("footprint")
            if fp is not None and (fp.text or "").strip():
                sch_fps[c.get("ref")] = fp.text.strip()
        pins = {}
        for net in root.find("nets").findall("net"):
            for node in net.findall("node"):
                if node.get("ref") == MCU:
                    pins[node.get("pin")] = net.get("name")
        return pins, comps, sch_fps


def board_h_pins():
    """Parse the 'pad pinfunc net' table in the firmware/board.h header comment.
    Returns {pin: net} for GPIO pins only (P[A-F]n); power/prog pins are skipped."""
    txt = open(os.path.join(ROOT, "firmware", "board.h")).read()
    pat = re.compile(r'^\s*\*?\s*(\d{1,2})\s+(P[A-F][0-7])\s+([A-Za-z0-9_]+)')
    return {g.group(1): g.group(3)
            for g in (pat.match(ln) for ln in txt.splitlines()) if g}


def check_pin_contract(netpins):
    print("[1] firmware pin contract (board.h) vs schematic netlist")
    bh = board_h_pins()
    if len(bh) < 8:
        err(f"parsed only {len(bh)} GPIO pins from board.h -- table format changed?")
        return
    for pin, net in sorted(bh.items(), key=lambda kv: int(kv[0])):
        got = netpins.get(pin)
        if got == net:
            ok(f"pin {pin:>2}: {net}")
        else:
            err(f"pin {pin}: board.h says '{net}', schematic says '{got}'")


def check_bom_parity(comps):
    print("[2] CI-generated BOM vs netlist components")
    bomrefs = set()
    with open(BOM) as f:
        for row in csv.DictReader(f):
            for x in re.split(r'[ ,]+', (row.get("References") or "").strip()):
                if x:
                    bomrefs.add(x)
    phantom = sorted(bomrefs - comps)
    if phantom:
        err(f"BOM lists parts absent from the netlist: {phantom}")
    else:
        ok(f"all {len(bomrefs)} BOM refs exist in the netlist")
    excluded = sorted(comps - bomrefs)
    if excluded:
        print(f"  note:   {len(excluded)} netlist parts not in the CI-generated BOM "
              f"(mechanical / DNP / bare-pad / hand-soldered): {' '.join(excluded)}")


# Board revisions deliberately removed from PCB/ and kept only in git history (see
# PCB/README.md). A history doc that names one is a record, not a broken link, so it must
# not warn forever -- but it must not go silent either, or a genuinely dangling reference
# to the CURRENT revision would be indistinguishable from an intentional one.
RETIRED_REVS = ("v2_1", "v2_2", "v2_3", "v3_0")


def check_model_refs():
    """Does every `(model ...)` on the board point at a file that exists?

    This exists because of U7 (2026-07-28). Its footprint named
    `Package_DFN_QFN.3dshapes/DFN-8-1EP_6x5mm_Pitch1.27mm.step`, which no KiCad 10
    library ships -- the naming convention changed to `..._P1.27mm_EP4x4mm`. KiCad does
    not complain about a model path it cannot resolve; it just draws nothing. So U7 sat
    in the 3D view and the STEP export with NO BODY, while every census in this repo
    counted it as modelled because the footprint did carry a `(model ...)` line.

    Counting model REFERENCES is not the same as counting model BODIES, and only this
    check knows the difference.

    Project models (${KIPRJMOD}) must always resolve -- those files are in this repo, so
    a miss is an error. Stock models (${KICAD10_3DMODEL_DIR}) are only checked when the
    stock library is actually installed, since CI images may omit the ~3 GB package; when
    it is absent the check says so rather than passing quietly.
    """
    print("[5] 3D model refs resolve to real files")
    with open(PCB, encoding="utf-8", errors="replace") as fh:
        refs = re.findall(r'\(model "([^"]+)"', fh.read())
    if not refs:
        warn("no (model ...) refs found on the board at all")
        return

    prj = os.path.join(ROOT, "PCB")
    stock = os.environ.get("KICAD10_3DMODEL_DIR")
    if not stock or not os.path.isdir(stock):
        stock = next((d for d in ("/usr/share/kicad/3dmodels",
                                  "/usr/local/share/kicad/3dmodels",
                                  "/usr/share/kicad/modules/packages3d") if os.path.isdir(d)), None)

    bad, checked, skipped = [], 0, 0
    for ref in refs:
        if "KIPRJMOD" in ref:
            path = ref.replace("${KIPRJMOD}", prj)
        elif stock:
            path = ref.replace("${KICAD10_3DMODEL_DIR}", stock)
        else:
            skipped += 1
            continue
        checked += 1
        if not os.path.exists(path):
            bad.append(ref)
    for ref in sorted(set(bad)):
        err(f"model file does not exist, so the part renders with NO body: {ref}")
    if not bad:
        ok(f"all {checked} of {len(refs)} model refs resolve")
    if skipped:
        print(f"  note:   {skipped} stock model ref(s) not checked -- no KiCad 3D model "
              f"library on this machine (set KICAD10_3DMODEL_DIR to check them)")

    # And separately: is every STOCK model vendored? CI renders in an image that ships no
    # KiCad 3D library, so PCB/kicad-3dmodels/ is what the assembled render actually reads.
    # A machine with KiCad installed will pass the check above while CI still draws nothing,
    # which is exactly how the published render lost 38 bodies. Check the vendored set on its
    # own terms, independent of whatever this host happens to have.
    vend = os.path.join(ROOT, "PCB", "kicad-3dmodels")
    stock_refs = sorted({r for r in refs if "KICAD10_3DMODEL_DIR" in r})
    if not os.path.isdir(vend):
        warn("PCB/kicad-3dmodels/ is missing -- CI renders will have no stock component bodies")
    elif stock_refs:
        gaps = [r for r in stock_refs
                if not os.path.exists(r.replace("${KICAD10_3DMODEL_DIR}", vend))]
        for r in gaps:
            err(f"stock model not vendored, so CI renders it with NO body: {r}")
        if not gaps:
            ok(f"all {len(stock_refs)} stock models vendored in PCB/kicad-3dmodels/")

def check_mask_art():
    """Does the generated front mask art still match the routing it sits on?

    scripts/mask_art.py opens every aperture as (shape - live copper), so the art is a
    function of the wiring. That makes it the one piece of artwork on this board that goes
    WRONG when the board is edited rather than merely stale: move a trace under an opening
    and the committed mask lays a live signal bare on the show face, and nothing else would
    ever say so. Hence a gate.

    Degrades honestly: the check needs pcbnew and shapely, and CI's image may carry
    neither. When they are missing it says so rather than passing quietly.
    """
    print("[6] mask art matches the routing (NFC indicator; cartouche off)")
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    try:
        import pcbnew  # noqa: F401
        import shapely  # noqa: F401
        import mask_art
    except Exception as e:
        print(f"  note:   not checked -- {type(e).__name__}: {e}. "
              f"Needs pcbnew + shapely; run `python3 scripts/mask_art.py --check` locally.")
        return
    import pcbnew
    board = pcbnew.LoadBoard(PCB)
    # generate(), not emit(build()): the generator's own definition of what it writes, and the
    # back coil aperture, and rebuilding only half of it here reported a correct board
    # as STALE while the generator's own --check said MATCH.
    body = mask_art.generate(board)[0]
    with open(PCB, encoding="utf-8") as fh:
        txt = fh.read().replace("\r\n", "\n")
    kept, had = mask_art.strip_existing(txt)
    want = mask_art._splice(kept, body)
    if want == txt:
        ok(f"mask art matches: {had} generated shape(s) agree with current routing")
    elif had == 0:
        warn("no generated mask art in the board -- run `python3 scripts/mask_art.py --apply`")
    else:
        err(f"mask art is STALE: the board carries {had} generated shape(s) that no "
            f"longer match the routing. Re-run `python3 scripts/mask_art.py --apply`.")

def _b_side_parts():
    """(ref, model_basename) for every back-side footprint that carries a 3D model."""
    with open(PCB, encoding="utf-8", errors="replace") as fh:
        s = fh.read()
    out = []
    for m in re.finditer(r'\(footprint ', s):
        d, i = 0, m.start()
        while i < len(s):
            if s[i] == '(':
                d += 1
            elif s[i] == ')':
                d -= 1
                if d == 0:
                    break
            i += 1
        b = s[m.start():i + 1]
        if not re.search(r'\(footprint "[^"]+"\s*\(layer "B', b):
            continue
        rm = re.search(r'\(property "Reference" "([^"]+)"', b)
        mm = re.search(r'\(model "([^"]+)"', b)
        if rm and mm:
            out.append((rm.group(1), os.path.basename(mm.group(1))))
    return out


def _step_body_height(path):
    """Max z of a STEP file's CARTESIAN_POINTs, i.e. how tall the modelled body stands.

    A plain scan, no CAD kernel: KiCad's models sit on z=0 with +z away from the board, so
    the largest z IS the body height. Verified against the datasheet numbers in
    scripts/make_3d_models.py SPECS -- DFN-8 0.900, ADXL367 0.870, LA_P47F 0.830,
    NT3H2211 0.500, AVR64EA28 1.000, SOT-23 1.200 -- all exact.
    """
    with open(path, encoding="utf-8", errors="replace") as fh:
        txt = fh.read()
    zs = [float(m.group(3)) for m in re.finditer(
        r"CARTESIAN_POINT\s*\(\s*'[^']*'\s*,\s*\(\s*(-?[\d.E+-]+)\s*,\s*"
        r"(-?[\d.E+-]+)\s*,\s*(-?[\d.E+-]+)\s*\)", txt)]
    return max(zs) if zs else None


def check_part_heights():
    """Does every enclosure pocket depth actually clear the part it is cut for?

    The enclosure generators cut a pocket per B-side part from a hand-maintained height.
    That number is invisible to every other check here: the generator runs happily on a
    wrong one and prints a part that does not fit. It has gone wrong in both directions --
    U7 kept a removed SOIC-8's 1.75 after the board moved to a 0.90 DFN-8 (pocket cut clean
    THROUGH the brace), while Q2, FB1 and the 0603/0805 capacitors fell through a silent
    0.60/0.55 default and were cut up to 0.58 mm too shallow.

    So compare each height against the z-extent of the part's OWN 3D model on the board --
    the same models check [5] proves resolve, and which the assembled render already draws.
    Short is an error (the part interferes). Wildly generous is an error too: it is how a
    stale height announces itself, and past OVERSHOOT_MAX it changes a blind pocket into a
    hole. Known generic-model overshoot is waived by name in part_heights.MODEL_NOTES.
    """
    print("[7] enclosure part heights clear their 3D models")
    sys.path.insert(0, os.path.join(ROOT, "enclosure"))
    try:
        import part_heights as ph
    except Exception as e:
        err(f"cannot import enclosure/part_heights.py -- {type(e).__name__}: {e}")
        return

    prj = os.path.join(ROOT, "PCB")
    vend = os.path.join(ROOT, "PCB", "kicad-3dmodels")
    index = {}
    for root in (prj, vend):
        for p in glob.glob(os.path.join(root, "**", "*.step"), recursive=True):
            index.setdefault(os.path.basename(p), p)

    short, over, unknown, checked, noted = [], [], [], 0, []
    for ref, model in _b_side_parts():
        try:
            h = ph.part_height(ref)
        except ph.UnknownPart as e:
            unknown.append(e.args[0].split(":")[0])
            continue
        if h is None:
            continue
        path = index.get(model)
        if not path:
            continue
        body = _step_body_height(path)
        if body is None:
            continue
        checked += 1
        if h < body - 1e-6:
            if model in ph.MODEL_NOTES:
                noted.append((ref, model, h, body))
            else:
                short.append((ref, model, h, body))
        elif h - body > ph.OVERSHOOT_MAX:
            over.append((ref, model, h, body))

    for ref in sorted(set(unknown)):
        err(f"{ref} has no height in enclosure/part_heights.py, so no pocket can be cut for it")
    for ref, model, h, body in short:
        err(f"{ref} height {h:.2f} is SHORTER than its model {model} ({body:.3f}) -- the "
            f"enclosure pocket interferes with the part by {body - h:.2f} mm")
    for ref, model, h, body in over:
        err(f"{ref} height {h:.2f} overshoots its model {model} ({body:.3f}) by "
            f"{h - body:.2f} mm (> {ph.OVERSHOOT_MAX}) -- stale number? an over-deep pocket "
            f"can break through the brace")
    if not (short or over or unknown):
        ok(f"all {checked} modelled B-side parts clear their pockets")
    for ref, model, h, body in noted:
        print(f"  note:   {ref} {h:.2f} < modelled {body:.3f} ({model}) -- "
              f"{ph.MODEL_NOTES[model]}")


def check_enclosure_fit():
    """Does the enclosure actually clear the parts on the board it is built for?

    Check [7] proves the pocket DEPTHS clear their parts. Nothing proved the XY footprints
    did, and on 2026-07-29 all three were wrong at once against the committed board:

      * the brace's middle band was sized for supercap bays ending at y31.15/57.75 -- the
        28.5 mm WS17 length -- while SC1/SC3 are 39 mm SS17 cells. 348.83 mm2 / 593 mm3 of
        solid resin inside three 1.70 mm cans in a 1.80 mm cavity. Not installable.
      * the shell's support lip landed on NINE B-side parts, including 4.17 mm2 of LIVE pad
        (STO, STO_LDO, VS, NFC_EN) under grounded titanium. The board sets
        pad_to_mask_clearance = 0, so those pads are bare copper: fitting the shell shorted
        the storage rail to ground.
      * five of the eight M2 bosses fouled a part, two of them on live nets.

    None of it was catchable by eye, and the enclosure generators ran happily on all three.
    They now derive their geometry from enclosure/fit_rules.py; this asserts the invariants
    against those same functions, so it cannot drift into being a third opinion.
    """
    print("[8] enclosure geometry clears the board")
    sys.path.insert(0, os.path.join(ROOT, "enclosure"))
    try:
        import fit_rules as fr
        import board_parts  # noqa: F401
    except Exception as e:
        err(f"cannot import enclosure fit rules -- {type(e).__name__}: {e}")
        return

    ps = board_parts.parts("B")
    bad = 0

    # ---------------------------------------------------------------------------------
    # These assertions are deliberately made against PHYSICS and against the BOARD, not
    # against fit_rules' own outputs. A first cut of this check compared fit_rules geometry
    # to fit_rules blockers and passed happily when SPAN_LIMIT was injected at 1.75 and
    # again when LIP_CLR was injected at -0.50: it only ever proved the module agreed with
    # itself. cavity_void_poly() also REPAIRS any lip-on-part overlap by adding a local
    # relief, so "does the lip overlap a part" cannot fail by construction. What follows
    # can fail.
    # ---------------------------------------------------------------------------------

    # 1. Anything the brace covers must leave a printable web above it. This is the real
    #    constraint; SPAN_LIMIT is just its cached form, and a wrong SPAN_LIMIT fails here.
    pieces = fr.brace_footprint()
    for ref, poly, h, _src in ps:
        if not any(g.intersects(poly) for g in pieces):
            continue
        a = sum(g.intersection(poly).area for g in pieces)
        if a <= 1e-6:
            continue
        if h is None:
            err(f"brace covers {ref} by {a:.3f} mm2 but {ref} has no height, so the resin "
                f"web over it is unknown")
            bad += 1
            continue
        web = fr.GAP - (h + fr.AIR)
        if web < fr.SLA_WEB - 1e-9:
            err(f"brace covers {ref} ({h:.2f} mm) over {a:.2f} mm2, leaving a {web:.2f} mm "
                f"web -- below the {fr.SLA_WEB} mm printable minimum")
            bad += 1

    # 2. Every lip band must stand off the nearest part it runs past. Asserted on the BAND
    #    WIDTH against the part positions, upstream of the self-healing relief.
    MIN_STANDOFF = 0.10
    for edge in ("W", "E", "S", "N"):
        for lo, hi, w in fr.lip_bands(edge):
            if w <= 0:
                continue
            for ref, poly, _h, _src in ps:
                x0, y0, x1, y1 = poly.bounds
                if edge in ("W", "E"):
                    if y1 <= lo or y0 >= hi:
                        continue
                    d = x0 if edge == "W" else (fr.W - x1)
                else:
                    if x1 <= lo or x0 >= hi:
                        continue
                    d = y0 if edge == "S" else (fr.H - y1)
                if w > d - MIN_STANDOFF:
                    err(f"{edge} lip band {lo:.1f}..{hi:.1f} is {w:.2f} mm wide but {ref} "
                        f"starts at {d:.2f} mm -- the grounded lip would land on it")
                    bad += 1

    # 3. The east lip may never overhang the NFC coil (a grounded feature there detunes it).
    #    Compared against the coil copper MEASURED FROM THE BOARD and a standoff this check
    #    owns -- comparing to fr.COIL_EAST would just be fit_rules agreeing with itself, and
    #    that is exactly how the original hardcoded 48.40 hid a real 0.15 mm overhang.
    MIN_COIL_STANDOFF = 0.10
    coil_max = board_parts.coil_extent()[1]
    for lo, hi, w in fr.lip_bands("E"):
        lip_edge = fr.W - w
        if lip_edge < coil_max + MIN_COIL_STANDOFF:
            err(f"E lip band {lo:.1f}..{hi:.1f} reaches x{lip_edge:.2f}, within "
                f"{MIN_COIL_STANDOFF} mm of NFC coil copper measured at x{coil_max:.3f} -- "
                f"grounded titanium there detunes the antenna")
            bad += 1

    # 4. No part inside a boss, and the scallops must not eat the tapped thread.
    import math
    from shapely.geometry import Point as _P
    for mx, my in fr.MOUNTS:
        island = fr.boss_island(mx, my)
        for ref, poly, _h, _src in ps:
            a = island.intersection(poly).area
            if a > 1e-6:
                err(f"M2 boss at ({mx}, {my}) fouls {ref} by {a:.3f} mm2")
                bad += 1
        minr = fr.BOSS_R
        for k in range(360):
            ang = 2 * math.pi * k / 360
            r = 0.0
            while r <= fr.BOSS_R and island.contains(
                    _P(mx + r * math.cos(ang), my + r * math.sin(ang))):
                r += 0.05
            minr = min(minr, r)
        if minr < fr.THREAD_KEEP:
            err(f"boss at ({mx}, {my}) is scalloped to r{minr:.2f}, inside the "
                f"{fr.THREAD_KEEP} mm M2 thread keep-out")
            bad += 1

    if not bad:
        cav = fr.cavity_rect().buffer(-fr.WALL_FIT, join_style=1, resolution=64)
        cov = 100 * sum(g.area for g in pieces) / cav.area
        ok(f"brace {len(pieces)} piece(s), {cov:.1f}% of cavity, every covered part keeps a "
           f">={fr.SLA_WEB} mm web; {sum(len(fr.lip_bands(e)) for e in 'WESN')} lip bands all "
           f"stand off their parts and clear the coil; 8 bosses clear, thread intact")


def check_doc_file_refs():
    print("[3] referenced .kicad_* files exist")
    pat = re.compile(r'solar-glow-drh-v[0-9_]+\.kicad_(?:pcb|sch|pro|prl)')
    files = sorted(os.path.relpath(p, ROOT)
                   for p in glob.glob(os.path.join(ROOT, "**", "*.md"), recursive=True))
    files.append("firmware/board.h")
    seen = set()
    for rel in files:
        try:
            txt = open(os.path.join(ROOT, rel)).read()
        except OSError:
            continue
        for name in pat.findall(txt):
            seen.add((rel, name))
    retired = []
    for rel, name in sorted(seen):
        if os.path.exists(os.path.join(ROOT, "PCB", name)):
            ok(f"{name} (in {rel})")
        elif any(f"-{rev}." in name for rev in RETIRED_REVS):
            retired.append(f"{name} (in {rel})")
        else:
            warn(f"{rel} references PCB/{name}, which does not exist")
    if retired:
        print(f"  note:   {len(retired)} reference(s) to retired revisions, kept in git "
              f"history on purpose (see PCB/README.md): {', '.join(retired)}")


# --- [9] doc imagery ---------------------------------------------------------------
#
# Every producer this repo runs, and the paths it owns. A path is "automated" if some
# entry here claims it. Kept as globs, matching kibot.yml's own $OUTS list, so a NEW
# variant out of an existing generator is covered without editing anything.
#
# These are deliberately the same patterns kibot.yml commits back. If the two drift, the
# check below says so rather than trusting this copy -- see _kibot_outs().
PRODUCERS = {
    ".github/workflows/kibot.yml -> scripts/render.py + kibot": ["Generated/docs/*", "Generated/*"],
    ".github/workflows/kibot.yml -> enclosure/assembly_render.py": [
        "enclosure/solar-glow-drh-assembly*.png",
        "enclosure/solar-glow-drh-assembly*.gif",
        "enclosure/brace/*brace-render.png",
    ],
    ".github/workflows/kibot.yml -> the DRAWING generators (brace, shell, pogo plate)": [
        "enclosure/*DRAWING.png", "enclosure/*DRAWING.pdf",
        "enclosure/brace/*DRAWING.png", "enclosure/brace/*DRAWING.pdf",
        "enclosure/brace/*pocket-map.png",
    ],
    # Redundant with the Generated/docs/* claim above, kept for the WHO: these are not
    # kibot or the raytracer, they are the reference figures drawn from the board and the
    # committed back-shell STL (LED polarity, SW2 bridge, thickness-at-hand-scale) -- the
    # first two replaced hand-uploaded v2 PNGs that went stale invisibly (culled 2026-08-01).
    ".github/workflows/kibot.yml -> scripts/ref_figures.py": [
        "Generated/docs/*-led-orientation.png", "Generated/docs/*-sw2-selector.png",
        "Generated/docs/*-thickness-scale.png",
    ],
}

# Images a doc displays that NOTHING in this repo generates. Each needs a reason, and the
# reason has to be why it CANNOT be generated -- not that nobody has got to it. Anything
# listed here is reported on every run so it stays visible instead of becoming furniture.
#
# The eight below are analysis figures committed on 2026-07-22 with no generator anywhere in
# the tree. They are not renders of the board -- they plot models and measurements (supercap
# endurance vs float voltage, the v3/v4 energy comparison, the e-ink fit studies, the bench
# fixture layout) whose INPUT DATA is not in the repo either. Regenerating them means first
# writing down the parameters they encode; until that happens, a "generator" for them would
# be a script that hard-codes numbers read off a PNG, which is worse than no generator.
UNAUTOMATED = {
    "images/managed-vs-unmanaged.png":
        "v3-vs-v4 energy bar chart; the 2.7/7.8 J and 106/298-tap figures are not sourced in-tree",
    "images/supercap-aging.png":
        "SCHURTER SCPC endurance model; kV band and base life are not written down anywhere",
    "images/eink-card-mockup.png": "e-ink variant study; speculative, no board behind it",
    "images/eink-gap-fit.png": "e-ink variant study; speculative, no board behind it",
    "images/eink-horizontal-fit.png": "e-ink variant study; speculative, no board behind it",
    "images/eink-resolution-workup.png": "e-ink variant study; speculative, no board behind it",
    "images/bench-fixture-floorplan.png": "harvest bench fixture layout; hand-drawn, no CAD source",
    "images/bench-fixture-wiring.png": "harvest bench fixture wiring; hand-drawn, no CAD source",
}

RAW_PREFIX = "https://raw.githubusercontent.com/devinhorowitz/solar-business-card/main/"
BLOB_PREFIX = "https://github.com/devinhorowitz/solar-business-card/blob/main/"


def _kibot_outs():
    """The $OUTS list kibot.yml actually commits, read out of the workflow.

    Read rather than restated: PRODUCERS above is what this check believes is automated, and
    if it claims a path the workflow never commits, the claim is empty -- CI would regenerate
    the file and throw it away. Parsing the real list is what makes the two agree.
    """
    wf = os.path.join(ROOT, ".github", "workflows", "kibot.yml")
    try:
        txt = open(wf).read()
    except OSError:
        return None
    m = re.search(r'^\s*OUTS="(.*?)"', txt, re.S | re.M)
    return m.group(1).split() if m else None


def check_doc_imagery():
    print("[9] every image the docs display comes from a generator")
    import fnmatch
    claimed = [(g, who) for who, globs in PRODUCERS.items() for g in globs]

    outs = _kibot_outs()
    if outs is None:
        warn("could not read the OUTS list from .github/workflows/kibot.yml")
    else:
        # A producer glob is only meaningful if CI commits what it makes. Compare by prefix:
        # OUTS carries "Generated" (a directory) where PRODUCERS carries "Generated/docs/*".
        loose = [g for g, _ in claimed
                 if not any(g.startswith(o.rstrip("/*")) or fnmatch.fnmatch(g, o) for o in outs)]
        if loose:
            err("PRODUCERS claims path(s) that kibot.yml never commits, so CI would "
                f"regenerate and discard them: {', '.join(loose)}")

    refs = {}
    for md in sorted(glob.glob(os.path.join(ROOT, "**", "*.md"), recursive=True)):
        rel_md = os.path.relpath(md, ROOT)
        if rel_md.startswith(".git"):
            continue
        try:
            txt = open(md, errors="replace").read()
        except OSError:
            continue
        # Strip fenced blocks and inline code first. A doc that DOCUMENTS this rule quotes
        # image syntax as an example -- CLAUDE.md's own "add a `![](…)` to any .md" tripped
        # this check the first time it ran -- and an example is not a displayed image.
        txt = re.sub(r"```.*?```", "", txt, flags=re.S)
        txt = re.sub(r"~~~.*?~~~", "", txt, flags=re.S)
        txt = re.sub(r"`[^`\n]*`", "", txt)
        for m in list(re.finditer(r'!\[[^\]]*\]\(([^)\s]+)', txt)) + \
                 list(re.finditer(r'<img[^>]*src="([^"]+)"', txt)):
            u = m.group(1)
            if u.startswith(RAW_PREFIX):
                p = u[len(RAW_PREFIX):]
            elif u.startswith(BLOB_PREFIX):
                p = u[len(BLOB_PREFIX):]
            elif u.startswith(("http://", "https://", "data:")):
                continue
            else:
                p = os.path.normpath(os.path.join(os.path.dirname(rel_md), u))
            refs.setdefault(p.split("#")[0], set()).add(rel_md)

    missing, orphan, auto = [], [], 0
    for p, where in sorted(refs.items()):
        if not os.path.exists(os.path.join(ROOT, p)):
            missing.append(f"{p} (in {', '.join(sorted(where))})")
            continue
        if any(fnmatch.fnmatch(p, g) for g, _ in claimed):
            auto += 1
        elif p not in UNAUTOMATED:
            orphan.append(f"{p} (in {', '.join(sorted(where))})")

    if missing:
        err(f"{len(missing)} image(s) referenced by a doc do not exist: " + "; ".join(missing))
    if orphan:
        err(f"{len(orphan)} image(s) are displayed by a doc but no generator produces them. "
            "Either wire one up, or add the path to UNAUTOMATED in this file with the reason "
            "it cannot be: " + "; ".join(orphan))
    stale = sorted(set(UNAUTOMATED) - set(refs))
    if stale:
        warn(f"{len(stale)} UNAUTOMATED entr(y/ies) no longer referenced by any doc — "
             f"drop them: {', '.join(stale)}")
    if not missing and not orphan:
        ok(f"{auto} of {len(refs)} doc image(s) come from a generator CI runs")
    if UNAUTOMATED:
        print(f"  note:   {len(UNAUTOMATED)} hand-made image(s) still displayed, each with a "
              f"logged reason:")
        for p, why in sorted(UNAUTOMATED.items()):
            if p in refs:
                print(f"            {p} — {why}")


# --- [11] cited paths -------------------------------------------------------------
#
# Check [9] guards images a doc DISPLAYS. Paths a doc merely CITES — in backticks, in
# tree listings, in build instructions — had no guard at all, and 2026-08-01's hunt
# found the class four separate times: a v2-era drawing "kept as history; safe to
# delete" that was already gone, a brace-fit photo named as present after its
# deletion, a design-note pointing at a culled mock-up, and a README step citing a
# TODO item that no longer existed. Each rotted silently because nothing renders a
# citation.
#
# The rule this check enforces is a PROSE DISCIPLINE, not just an inventory: a doc may
# name a file that does not exist only if (a) the sentence itself says so — a history
# marker like "culled", "deleted", "git history" on the same or the previous line, the
# way every closure tonight was written — or (b) the path carries a reason below.
# Anything else is an error: either the file went missing, or the prose is claiming a
# tree that is not there.
EXPECTED_ABSENT = {
    # Build outputs and CI intermediates — gitignored by design, cited as what a
    # command WRITES rather than what the tree holds.
    "firmware/solar-glow.hex": "firmware build output — gitignored (firmware/README `make`)",
    "solar-glow.hex": "same file, cited by basename",
    "Generated/panel/*.kicad_pcb": "CI-built panel intermediate — gitignored; rebuild with scripts/panelize.py",
    # Files that live in the USER'S toolchain, not this repo.
    "avrdude.conf": "ships with the user's avrdude install",
    "ioavr64ea28.h": "AVR-Dx DFP header — part of the toolchain pack, not the repo",
    ".mcp.json": "local config mcp-setup.md instructs the user to create",
    "digikey_mcp_server.py": "external MCP server on the user's machine (mcp-setup.md registration command)",
    # kicad-happy runs from a pinned OUT-OF-REPO clone by rule (docs/kicad-happy.md) — these
    # are its files, cited by the run recipe there.
    "analyze_schematic.py": "kicad-happy analyzer — lives in the pinned external clone (docs/kicad-happy.md)",
    "analyze_pcb.py": "kicad-happy analyzer — lives in the pinned external clone (docs/kicad-happy.md)",
    "cross_analysis.py": "kicad-happy cross-tool — lives in the pinned external clone (docs/kicad-happy.md)",
    "cross_verify.py": "kicad-happy cross-tool — lives in the pinned external clone (docs/kicad-happy.md)",
    "analyze_emc.py": "kicad-happy EMC skill — lives in the pinned external clone (docs/kicad-happy.md)",
    "schematic.json": "kicad-happy analyzer output — scratch, out-of-repo by rule (docs/kicad-happy.md)",
    "pcb.json": "kicad-happy analyzer output — scratch, out-of-repo by rule (docs/kicad-happy.md)",
    "install-guidance.md": "kicad-happy doc — lives in the pinned external clone (docs/kicad-happy.md)",
    # ThomsonLint runs from a pinned OUT-OF-REPO clone by the same rule (docs/thomsonlint.md).
    "tools/kicad-export.py": "ThomsonLint exporter — lives in the pinned external clone (docs/thomsonlint.md)",
    "ontology/ontology.json": "ThomsonLint rule ontology — lives in the pinned external clone (docs/thomsonlint.md)",
    "tools/validate_findings.py": "ThomsonLint coverage validator — lives in the pinned external clone (docs/thomsonlint.md)",
    "tools/gen_report.py": "ThomsonLint report generator — lives in the pinned external clone (docs/thomsonlint.md)",
    "docs/REVIEWER_INSTRUCTIONS.md": "ThomsonLint review contract — lives in the pinned external clone (docs/thomsonlint.md)",
    "-findings.json": "ThomsonLint review output — scratch, out-of-repo by rule (docs/thomsonlint.md)",
    # On-demand analysis outputs that deliberately live OUTSIDE the repo (the same
    # rule that keeps engraving-study renders out — see their README).
    "all_studies.png": "engraving-study sheet — scratch output, out-of-repo by rule",
    "shell_nomark.stl": "engraving-study base solid — scratch output, out-of-repo by rule",
    # Not a file at all: the datasheets/ naming-convention pattern in README's tree
    # ("REF  MPN  $price.pdf") tokenizes to this placeholder.
    "price.pdf": "the datasheets/ naming-convention placeholder, not a path",
}

_CITE_EXTS = ("png gif jpg jpeg svg pdf step stl zip html json csv xlsx md py yml yaml "
              "ttf txt c h rpt drl gbr hex conf "
              "kicad_pcb kicad_sch kicad_pro kicad_prl kicad_mod kicad_dru").split()
_HIST_RE = re.compile(
    r"git history|culled|deleted|removed|replaced|superseded|retired|struck|"
    r"no longer|history only|used to|abandoned|renamed|is gone|went stale|"
    r"there is no|does not exist|never existed|"
    r"\bwas\b|\bold\b|-era\b|until 20|pre-20", re.I)


def check_doc_cited_paths():
    print("[11] every path a doc cites exists — or the sentence says why it does not")
    import fnmatch
    ext_re = "|".join(_CITE_EXTS)
    # a path-ish token: optional dirs, a basename, one of the known extensions
    bare = re.compile(r"(?<![\w./-])((?:[\w.-]+/)*[\w.-]+\.(?:%s))(?![\w/])" % ext_re)
    tick = re.compile(r"`([^`\n]+)`")
    kicad_owned = re.compile(r"solar-glow-drh-v[0-9_]+\.kicad_")   # check [3]'s territory

    # TRACKED files only. os.walk would also see gitignored local artifacts (a
    # firmware/*.hex from a local build, a panel board from a panelize run) and
    # silently pass here what would fail in CI's clean checkout.
    import subprocess
    all_files = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True,
                               text=True).stdout.splitlines()
    tracked = set(all_files)
    basenames = {os.path.basename(p) for p in all_files}

    def tokens(line):
        out = []
        for m in tick.finditer(line):
            body = m.group(1).strip()
            if re.search(r"\.(?:%s)$" % ext_re, body) and (
                    " " not in body or body in tracked
                    or any(f.endswith("/" + body) for f in tracked)):
                out.append(body)          # whole backtick content (datasheet names with spaces)
            else:
                out.extend(t.group(1) for t in bare.finditer(body))
        out.extend(t.group(1) for t in bare.finditer(tick.sub(" ", line)))
        return out

    def expand(tok):
        """'sense.h/.c' and 'fram.c/fram.h' style pairs -> individual names.

        Restricted to the .c/.h shorthand the docs actually use: a general dot-dir
        split would butcher real paths like Capacitor_SMD.3dshapes/C_0805….step."""
        if re.fullmatch(r"[\w.]+\.[ch](?:/(?:[\w.]+)?\.[ch])+", tok):
            parts = tok.split("/")
            outs, stem = [], None
            for p in parts:
                if p.startswith("."):
                    outs.append((stem or "") + p)
                else:
                    outs.append(p)
                    stem = os.path.splitext(p)[0]
            return outs
        return [tok]

    problems, absences = [], {}
    for md in sorted(glob.glob(os.path.join(ROOT, "**", "*.md"), recursive=True)):
        rel_md = os.path.relpath(md, ROOT)
        if rel_md.startswith(".git"):
            continue
        lines = open(md, errors="replace").read().splitlines()
        for i, line in enumerate(lines):
            for raw in tokens(line):
                for tok in expand(raw):
                    if any(c in tok for c in "<>$*{}|") or "…" in tok or "..." in tok \
                       or tok.startswith(("http", "data:")) or kicad_owned.search(tok):
                        continue
                    cands = [os.path.normpath(os.path.join(os.path.dirname(rel_md), tok)),
                             os.path.normpath(tok)]
                    if any(c in tracked or os.path.isdir(os.path.join(ROOT, c))
                           for c in cands):
                        continue
                    if "/" in tok:
                        # partial-path shorthand: quoted relative to some inner dir
                        # (e.g. Capacitor_SMD.3dshapes/C_0805….step under kicad-3dmodels/)
                        if any(f.endswith("/" + tok) for f in tracked):
                            continue
                    elif tok in basenames or any(b.endswith(tok) for b in basenames):
                        continue                      # basename / suffix shorthand
                    hit = next((g for g in EXPECTED_ABSENT
                                if fnmatch.fnmatch(tok, g)
                                or fnmatch.fnmatch(os.path.basename(tok), g)), None)
                    if hit:
                        absences.setdefault(hit, set()).add(rel_md)
                        continue
                    window = line + " " + (lines[i - 1] if i else "")
                    if _HIST_RE.search(window):
                        continue                      # the sentence owns the absence
                    problems.append(f"{tok} (in {rel_md}:{i + 1})")
    if problems:
        err(f"{len(problems)} cited path(s) do not exist and the prose does not say why. "
            "Fix the citation, mark it historical in its own sentence, or add it to "
            "EXPECTED_ABSENT in this file with the reason: " + "; ".join(sorted(set(problems))))
    else:
        ok("every cited path exists, is marked historical, or carries a reason")
    stale_absent = sorted(set(EXPECTED_ABSENT) - set(absences))
    if stale_absent:
        warn(f"{len(stale_absent)} EXPECTED_ABSENT entr(y/ies) no longer cited by any doc — "
             f"drop them: {', '.join(stale_absent)}")
    if absences:
        print(f"  note:   {sum(len(v) for v in absences.values())} citation(s) of "
              f"deliberately-absent files, each with its reason on file:")
        for g, wheres in sorted(absences.items()):
            print(f"            {g} — {EXPECTED_ABSENT[g]}")


# --- [12] footprint sides ----------------------------------------------------------
#
# Nothing else in CI notices a footprint changing SIDES: DRC has no opinion, schematic
# parity has no layer concept, and check [1] compares refdes and footprint assignment,
# not side. TC1's 2026-07-30 front-flip was caught only as a side effect (the brace's
# pocket list changed underneath), and TODO's tooling item spells out the stakes: a side
# flip is one keystroke in KiCad, it moves every pad and mask aperture to the other
# face, and for a B-side part it silently deletes that part's brace pocket -- the
# enclosure failure mode part_heights exists to prevent from the other direction.
#
# There is no source of truth to COMPARE against, so this is a SNAPSHOT, the exclusion-
# ledger shape: deliberate moves update the dict in the same commit that makes the move,
# undeliberate ones stop being invisible. Snapshot taken 2026-08-01 (post TC1/b).
FRONT_SIDE = {
    "?": 1, "MH1": 1, "MH2": 1, "MH3": 1, "MH4": 1, "MP1": 1, "MP2": 1, "MP3": 1, "MP4": 1, "PV1": 1, "PV2": 1, "TC1": 1
}
# everything else on the board is expected on B.Cu.


def check_footprint_sides():
    print("[12] every footprint sits on the side the snapshot says")
    try:
        board = glob.glob(os.path.join(ROOT, "PCB", "*.kicad_pcb"))[0]
        b = open(board, newline="").read()
    except (IndexError, OSError) as e:
        warn(f"not checked -- {type(e).__name__}: {e}")
        return
    marks = [m.start() for m in re.finditer(r'\(footprint "', b)] + [len(b)]
    moved, seen = [], set()
    for i in range(len(marks) - 1):
        fp = b[marks[i]:marks[i + 1]]
        rm = re.search(r'\(property "Reference"\s+"([^"]+)"', fp)
        lm = re.search(r'\(layer\s+"([^"]+)"\)', fp)
        ref = rm.group(1) if rm else "?"
        seen.add(ref)
        want = "F.Cu" if ref in FRONT_SIDE else "B.Cu"
        if lm and lm.group(1) != want:
            moved.append(f"{ref} ({want} -> {lm.group(1)})")
    ghosts = sorted(set(FRONT_SIDE) - seen)
    if moved:
        err("footprint(s) changed SIDES since the snapshot -- a deliberate move must "
            "update FRONT_SIDE in this file in the same commit (and re-check the brace "
            "pocket list); an undeliberate one just stopped being invisible: "
            + ", ".join(sorted(moved)))
    if ghosts:
        warn(f"FRONT_SIDE lists refdes no longer on the board -- prune: {', '.join(ghosts)}")
    if not moved and not ghosts:
        ok(f"all {len(seen)} footprints on their snapshotted side ({len(FRONT_SIDE)} front)")


# --- [13] NFC coil paper tune -------------------------------------------------------
#
# The antenna is the one subsystem NEITHER external reviewer can see as a designed
# object (docs/thomsonlint.md): kicad-happy reports the coil as a plane-gap defect,
# ThomsonLint's ontology only knows antennas as accidents. Until 2026-08-01 the coil's
# electrical identity was hand math done once, off-board -- a re-route could lose a
# turn and nothing would say so. scripts/nfc_coil.py re-derives L and the paper
# resonance FROM THE ROUTING; evaluate() is the single definition, this check calls it.
# The gate is a CATASTROPHE gate in bare-copper units (the ferrite pulls the physical
# tank down toward 13.56 MHz; the C9 ladder and the bench own the real tune).
def check_nfc_coil():
    print("[13] NFC coil geometry and paper tune (bare-copper catastrophe gate)")
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    try:
        import nfc_coil
    except Exception as e:
        warn(f"not checked -- {type(e).__name__}: {e}")
        return
    try:
        r = nfc_coil.evaluate()
    except ValueError as e:
        err(f"coil extraction failed: {e}")
        return
    probs = []
    if not (nfc_coil.GATE_TURNS[0] <= r["turns"] <= nfc_coil.GATE_TURNS[1]):
        probs.append(f"turns {r['turns']:.2f} outside {nfc_coil.GATE_TURNS}")
    if abs(r["turns"] - r["turns_winding"]) > 1.2:
        probs.append(f"turn counts disagree ({r['turns']:.2f} runs vs "
                     f"{r['turns_winding']:.2f} winding)")
    if r["C9_dnp"]:
        probs.append("C9 is dnp -- no placed tune")
    if r["L_spread"] > nfc_coil.GATE_L_SPREAD:
        probs.append(f"L formulas disagree by {r['L_spread'] * 100:.0f}%")
    f_placed = r["f0_MHz"].get(r["C9_placed_pF"])
    if f_placed is None:
        probs.append(f"placed C9 {r['C9_placed_pF']:g} pF is not a ladder value")
    elif not (nfc_coil.GATE_F_MHZ[0] <= f_placed <= nfc_coil.GATE_F_MHZ[1]):
        probs.append(f"paper f0 {f_placed:.2f} MHz outside {nfc_coil.GATE_F_MHZ}")
    if probs:
        err("the coil no longer matches its baseline: " + "; ".join(probs) +
            " -- run `python3 scripts/nfc_coil.py` for the full table")
    else:
        ok(f"{r['turns']:.1f} turns, L ~{r['L_mean_uH']:.2f} uH (formulas agree to "
           f"{r['L_spread'] * 100:.0f}%), bare f0 {f_placed:.2f} MHz at the placed "
           f"C9 {r['C9_placed_pF']:g} pF")


def check_part_colors():
    print("[10] every 3D model carries the colour the parts table gives it")
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    try:
        import part_colors
    except Exception as e:
        warn(f"not checked -- {type(e).__name__}: {e}")
        return
    stray = sorted({p.stem for p in part_colors.SHAPES.glob("*.step")} - set(part_colors.COLORS))
    if stray:
        err("3D model(s) with no entry in part_colors.COLORS — an uncoloured body renders as "
            f"the renderer's default grey and no other check would notice: {', '.join(stray)}")
        return
    drift = []
    for stem, (rgb, _why) in sorted(part_colors.COLORS.items()):
        _p, src = part_colors.read(stem)
        have = part_colors.current(src)
        if have is None or not all(abs(a - b) < 5e-3 for a, b in zip(have, rgb)):
            drift.append(f"{stem} ({'no colour' if have is None else part_colors.hexof(have)} "
                         f"!= {part_colors.hexof(rgb)})")
    if drift:
        err("3D model colour(s) differ from part_colors.COLORS — run "
            f"`python3 scripts/part_colors.py --apply`: {'; '.join(drift)}")
    else:
        ok(f"all {len(part_colors.COLORS)} project model(s) carry their table colour")


def board_footprints():
    """Return {refdes: (lib_id, is_board_only)} for every footprint in the .kicad_pcb.

    Hand-rolled paren-balanced scan rather than a real parser: we only need the
    Reference property, the lib_id, and the attr flags of each (footprint ...)
    block, and adding a dependency for that is not worth it in CI.

    Two things this has to get right, both learned the hard way on 2026-07-26:

    * The lib_id can be the EMPTY string. MP1-MP4 (the corner mounting pads) are
      stored as `(footprint ""`. An earlier `"([^"]+)"` here silently dropped
      them, so the board map held 67 of the board's 71 refdes and nothing said so
      -- a checker that quietly ignores four parts is worse than no checker.
    * `attr ... board_only` is KiCad's own marker for "this footprint exists only
      on the board; a schematic sync must not delete it." Those parts are
      SUPPOSED to be absent from the schematic, so they must not trip the
      board-only error below. MP1-MP4 carry it, which is why nothing was ever
      lost there. (The NPTH_mech hole set is board_only too but has no Reference
      property at all, so it falls out here for want of a refdes to key on --
      there is nothing a refdes-based parity check can say about it.)"""
    with open(PCB, encoding="utf-8", errors="replace") as fh:
        s = fh.read()
    out = {}
    for m in re.finditer(r"\(footprint ", s):
        depth, i = 0, m.start()
        while i < len(s):
            c = s[i]
            if c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
                if depth == 0:
                    break
            elif c == '"':
                i += 1
                while i < len(s) and s[i] != '"':
                    if s[i] == "\\":
                        i += 1
                    i += 1
            i += 1
        blk = s[m.start():i + 1]
        ref = re.search(r'\(property "Reference" "([^"]+)"', blk)
        lib = re.match(r'\(footprint "([^"]*)"', blk)
        if ref and lib:
            attr = re.search(r"\(attr ([^)]*)\)", blk)
            board_only = bool(attr) and "board_only" in attr.group(1)
            out[ref.group(1)] = (lib.group(1), board_only)
    return out


def bom_packages():
    """{refdes: package string} from the BOM master xlsx (BOM/*-BOM.xlsx).

    stdlib only: an .xlsx is a zip of XML, and all we want is column 4 of each
    row. Cells arrive either as inline strings (<is><t>) or via the shared-string
    table, so both are handled. A row's first cell may list several refs
    ("R17, R18"), which is why it is split.
    """
    path = os.path.join(ROOT, "BOM", "solar-glow-drh-v4_0-BOM.xlsx")
    if not os.path.exists(path):
        return {}
    import zipfile
    with zipfile.ZipFile(path) as z:
        shared = []
        if "xl/sharedStrings.xml" in z.namelist():
            sx = z.read("xl/sharedStrings.xml").decode("utf8", "replace")
            shared = re.findall(r"<t[^>]*>([^<]*)</t>", sx)
        sheet = z.read("xl/worksheets/sheet1.xml").decode("utf8", "replace")
    out = {}
    for row in re.findall(r"<row.*?</row>", sheet, re.S):
        cells = []
        for c in re.finditer(r"<c[^>]*?(?:\st=\"(\w+)\")?[^>]*>(.*?)</c>", row, re.S):
            typ, body = c.group(1), c.group(2)
            # Excel splits a styled cell into several <t> runs; take them all, or a
            # cell like "0603 (R_0603_1608Metric)" reads back as just "0603 " -- or
            # as nothing, if the first run is empty.
            inline = "".join(re.findall(r"<t[^>]*>([^<]*)</t>", body))
            if typ == "s":
                v = re.search(r"<v>(\d+)</v>", body)
                cells.append(shared[int(v.group(1))] if v and int(v.group(1)) < len(shared) else "")
            elif inline:
                cells.append(inline)
            else:
                v = re.search(r"<v>([^<]*)</v>", body)
                cells.append(v.group(1) if v else "")
        if not cells:
            continue
        # Find the package cell by CONTENT, not by column index. Some rows carry a
        # leading empty cell, so a fixed index lands on the value column instead
        # ("100 nF, X7R, 50 V") and the row is silently skipped -- which is how the
        # first cut of this check only covered 15 of 32 comparable parts.
        pkg = ""
        for c in cells[1:]:
            if re.match(r"^(0402|0603|0805|1008|1206)\b", c.strip()):
                pkg = c.strip()
                break
        for r in re.split(r"[,/]", cells[0]):
            r = r.strip()
            if re.match(r"^[A-Z]+\d+$", r):
                out[r] = pkg
    return out


# Land geometry -> chip package, calibrated against footprints whose class is
# already known from their KiCad lib_id (C_0402 = 0.96 mm pitch, C_0603 = 1.55,
# R_0603 = 1.65, C_0805 = 1.90, L_1008 = 2.15). The bands are deliberately wide:
# this project draws its own hand-solder lands slightly larger than KiCad's, so
# the 0402 band has to admit both 0.96 and the house 1.02.
_LAND_BANDS = ((0.90, 1.10, "0402"), (1.45, 1.75, "0603"),
               (1.80, 2.00, "0805"), (2.05, 2.30, "1008"))


def board_land_classes():
    """{refdes: (package_class, pitch)} for every 2-pad SMD footprint."""
    with open(PCB, encoding="utf-8", errors="replace") as fh:
        s = fh.read()
    out = {}
    for m in re.finditer(r"(?m)^\s*\(footprint ", s):
        depth, i = 0, s.index("(", m.start())
        while i < len(s):
            c = s[i]
            if c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
                if depth == 0:
                    break
            elif c == '"':
                i += 1
                while i < len(s) and s[i] != '"':
                    i += 2 if s[i] == "\\" else 1
            i += 1
        blk = s[m.start():i + 1]
        ref = re.search(r'\(property "Reference" "([^"]+)"', blk)
        pads = re.findall(
            r'\(pad "[^"]*" \w+ \w+\s*\(at (-?[\d.]+) (-?[\d.]+)(?: -?[\d.]+)?\)\s*\(size ([\d.]+) ([\d.]+)\)',
            blk)
        if not ref or len(pads) != 2:
            continue
        (x1, y1, _, _), (x2, y2, _, _) = [tuple(map(float, p)) for p in pads]
        pitch = max(abs(x1 - x2), abs(y1 - y2))
        cls = next((n for lo, hi, n in _LAND_BANDS if lo <= pitch <= hi), None)
        if cls:
            out[ref.group(1)] = (cls, round(pitch, 3))
    return out


def check_package_vs_land():
    """Does the part the BOM orders actually fit the land the board draws?

    This exists because of FB1 (2026-07-28). The design notes, the BOM and even
    the schematic symbol's Value all said "0603 ferrite", but the Footprint field
    was never changed, so a 0603 part was being ordered for a 0402 land -- its
    terminations would sit ~0.165 mm outboard of the pad centres with almost no
    fillet. NOTHING caught it: KiCad's schematic parity only compares the
    schematic to the board, and those two agreed with each other. The BOM master
    is a third copy of the truth, and it was the only one that was right.

    So this compares the ORDERED package against the DRAWN land. Cheap, and it is
    the only check in this repo that can see that class of drift.

    Coverage is partial and SAYS SO: it can only speak for two-pad parts whose BOM
    package cell starts with a size token. About 16 rows word it differently and
    are listed in a note rather than silently dropped. Widen the BOM wording, not
    this parser, if you want them covered.
    """
    print("[4] BOM package vs board land geometry")
    bom, land = bom_packages(), board_land_classes()
    checked, skipped = 0, []
    for ref in sorted(land):
        pkg = bom.get(ref)
        m = re.match(r"^(0402|0603|0805|1008|1206)\b", pkg or "")
        if not m:
            skipped.append(ref)
            continue
        checked += 1
        cls, pitch = land[ref]
        if m.group(1) != cls:
            err(f"{ref}: BOM orders a {m.group(1)} part ({pkg!r}) but the board land "
                f"is {cls} (pad pitch {pitch} mm) -- the part will not fit")
    if not errors or checked:
        ok(f"{checked} of {len(land)} two-pad parts cross-checked, package matches land")
    # Never fail silently: say which parts this check could NOT speak for.
    if skipped:
        print(f"  note:   {len(skipped)} two-pad parts have no size in the BOM package "
              f"column, so they are not covered: {' '.join(sorted(skipped))}")


def check_board_sch_parity(comps, sch_fps):
    """Guard the schematic <-> board boundary.

    The schematic is UPSTREAM of the board, so anything the board has that the
    schematic does not will be DELETED on the next 'Update PCB from Schematic',
    and any footprint assignment that disagrees will MOVE that part's pads. This
    project has lost work to exactly that four times (U9's Footprint property,
    U7's DNP flag twice, C29 missing from the schematic, and the U7 land
    mismatch), which is why this check exists."""
    board = board_footprints()
    # refs that exist only on the board: a sync deletes them -- UNLESS KiCad has
    # been told they are board-only, which is the whole point of that attribute.
    # Report the exempted ones so the exemption stays visible rather than silent:
    # if one ever loses its board_only flag, the count here changes and the
    # missing part shows up in the error above.
    exempt = sorted(r for r, (_, bo) in board.items() if bo and r not in comps)
    board_only = sorted(r for r, (_, bo) in board.items()
                        if not bo and r not in comps)
    if board_only:
        err("on the BOARD but not in the schematic (a sync will DELETE these): "
            + " ".join(board_only))
    else:
        ok("every board refdes is in the schematic or flagged board_only "
           f"({len(exempt)} board_only: {' '.join(exempt) or 'none'})")
    # refs only in the schematic: unplaced parts
    sch_only = sorted(r for r in comps if r not in board
                      and not r.startswith(("#", "TP", "MH", "MP")))
    if sch_only:
        warn("in the schematic but not placed on the board: " + " ".join(sch_only))
    # footprint assignment disagreements: a sync moves pads
    bad = []
    for ref, sch_fp in sorted(sch_fps.items()):
        entry = board.get(ref)
        if entry and entry[0] != sch_fp:
            bad.append(f"{ref}: sch={sch_fp} board={entry[0]}")
    if bad:
        # A hard error since 2026-07-26: U7 was the last known-open disagreement
        # and it is settled (board and library land turned out to be the SAME
        # land -- see TODO), so every remaining mismatch is a real find. A silent
        # footprint swap is exactly the failure this check exists to catch.
        err("footprint assignment differs between schematic and board (a sync "
            "with footprint replacement enabled will MOVE these pads): "
            + "; ".join(bad))
    else:
        ok("schematic and board agree on every footprint assignment")


def main():
    cli = find_kicad_cli()
    netpins, comps, sch_fps = export_netlist(cli)
    check_pin_contract(netpins)
    check_bom_parity(comps)
    check_board_sch_parity(comps, sch_fps)
    check_package_vs_land()
    check_model_refs()
    check_mask_art()
    check_part_heights()
    check_enclosure_fit()
    check_doc_imagery()
    check_part_colors()
    check_doc_file_refs()
    check_doc_cited_paths()
    check_footprint_sides()
    check_nfc_coil()
    print(f"\n== {len(errors)} error(s), {len(warnings)} warning(s) ==")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
