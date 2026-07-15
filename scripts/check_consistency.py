#!/usr/bin/env python3
"""
check_consistency.py -- drift guard for SOLAR-GLOW DRH.

Cross-checks the human docs and the firmware against the KiCad design, so a
change to one that isn't mirrored in the others fails loudly (in CI or locally):

  [1] PIN CONTRACT  -- the pad -> net map documented in firmware/board.h must
      match the schematic netlist for the MCU (U1).            [ERROR on drift]
  [2] BOM PARITY    -- every reference in the CI-generated BOM must be a real
      component in the netlist (no phantom BOM lines).         [ERROR on drift]
  [3] DOC FILE REFS -- every solar-glow-drh-*.kicad_* file named in board.h,
      README.md, or firmware/README.md must actually exist.    [WARN on drift]

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
# v4_0 board is a copy of v3_0 at scaffold time, so the frozen v3_0 BOM still matches the v4_0
# netlist. kibot regenerates a v4_0 BOM on the next PCB push; bump this to v4_0-bom.csv in lockstep
# with the managed-solar rework (when the netlist actually diverges). See v4-aem10300-prewiring.md.
BOM = os.path.join(ROOT, "Generated", "fabdocs", "solar-glow-drh-v3_0-bom.csv")
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
    """Return (pin->net for the MCU, set of all component refs) from the schematic."""
    with tempfile.TemporaryDirectory() as td:
        out = os.path.join(td, "nl.xml")
        subprocess.run([cli, "sch", "export", "netlist", "--format", "kicadxml",
                        "-o", out, SCH], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        root = ET.parse(out).getroot()
        comps = {c.get("ref") for c in root.find("components").findall("comp")}
        pins = {}
        for net in root.find("nets").findall("net"):
            for node in net.findall("node"):
                if node.get("ref") == MCU:
                    pins[node.get("pin")] = net.get("name")
        return pins, comps


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
    for rel, name in sorted(seen):
        if os.path.exists(os.path.join(ROOT, "PCB", name)):
            ok(f"{name} (in {rel})")
        else:
            warn(f"{rel} references PCB/{name}, which does not exist")


def main():
    cli = find_kicad_cli()
    netpins, comps = export_netlist(cli)
    check_pin_contract(netpins)
    check_bom_parity(comps)
    check_doc_file_refs()
    print(f"\n== {len(errors)} error(s), {len(warnings)} warning(s) ==")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
