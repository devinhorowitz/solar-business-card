#!/usr/bin/env python3
"""Split the design into the TWO buy documents an order actually needs.

    python3 scripts/bom_split.py                 # write them into Generated/fabdocs/
    python3 scripts/bom_split.py --boards 10     # quantities for a 10-card build
    python3 scripts/bom_split.py --check         # regenerate in memory, report, write nothing

WHY THIS EXISTS

A card order is two purchases, not one, and they go to different places:

  1. THE ASSEMBLY BOM -> PCBWay. Everything the machine buys and places.
  2. THE HAND-BUY LIST -> your own DigiKey / Mouser carts. Everything else: the
     parts that are deliberately hand-soldered (the supercaps and the solar
     cells), plus the things that never touch a pick-and-place at all -- the UPDI
     programmer, the Tag-Connect cable, the ferrite sheet, the screws, the film.

Before this, only the first existed as a generated artifact. The second was spread
across a spreadsheet's off-board rows, a live availability table, and prose in
TODO -- which is how the two-of-each supercap split nearly became four-of-one.
The card needs SC1/SC3 = SS17 1.8 F (3-153-440) and SC2/SC4 = WS17 1 F
(3-153-438): two MPNs, two stock pools, and no fab file mentions either.

WHERE THE TRUTH COMES FROM

Board parts are read from the SCHEMATIC (MPN / Manufacturer / Supplier /
Supplier P/N per symbol) and classified by the BOARD's own flags -- the same `exclude_from_bom`
and `dnp` attributes consistency check [15] gates. So a part moves between the
two documents by changing the design, never by editing a list:

    on board, not BOM-excluded, not DNP  ->  ASSEMBLY   (PCBWay places it)
    on board, BOM-excluded, not DNP      ->  HAND-BUY   (you solder it)
    DNP / no-part footprints             ->  neither    (bridges, pads, holes)

Items with no schematic symbol cannot be derived, so they are declared once in
OFF_BOARD below, with a reason each -- the exclusion-ledger shape used throughout
this repo. That table is the ONLY hand-maintained data here.
"""
from __future__ import annotations

import argparse
import csv
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCH = os.path.join(ROOT, "PCB", "solar-glow-drh-v4_0.kicad_sch")
PCB = os.path.join(ROOT, "PCB", "solar-glow-drh-v4_0.kicad_pcb")
OUTDIR = os.path.join(ROOT, "Generated", "fabdocs")
STEM = "solar-glow-drh-v4_0"

# --- things with no schematic symbol -------------------------------------------------
# Every row here is bought on the same trip as the supercaps, or is deliberately not
# bought at all. `supplier` routes it to a cart; None means "not a distributor line".
# Quantities are PER BOARD unless the note says otherwise.
OFF_BOARD = [
    # ref,   qty, mpn,                     mfr,                 supplier,   dist_pn,   note
    # The mfr column matters for the same reason it does on a schematic symbol: it is
    # check_stock's only guard against a short/all-numeric MPN matching another
    # vendor's part. "364006" is exactly that shape. Items with no manufacturer are
    # generic by nature (a DIN screw, sheet film) and are not distributor lines, so
    # nothing queries them.
    ("FER1",  1, "364006",                 "Würth Elektronik",  "DigiKey",  "732-5049-ND",
     "Wurth WE-FSFS ferrite sheet behind the coil -- load-bearing for the NFC tune"),
    ("HW1",   4, "DIN 84 M2x3 brass",      "",                  None,       "",
     "shell screws; any DIN 84 M2x3 -- source locally, not a distributor line"),
    ("INS1",  1, "polyimide film 0.05 mm", "",                  None,       "",
     "insulator; cut from stock film -- not a distributor line"),
]
# Bought ONCE for the project, not once per board -- so a --boards multiplier must not
# scale them. Tools and cables, not parts.
OFF_BOARD_ONCE = [
    # Routed DigiKey -> Mouser on 2026-08-02, and the reason is a distinction worth
    # keeping: DigiKey LISTS the UPDI Friend (1528-5879-ND, lifecycle Active) but sits
    # at ZERO stock, while Mouser has it at the same ~$6.95. The note this line carried
    # until today answered the wrong question -- it established that DigiKey resolves a
    # part number for the thing, and called that "DigiKey does stock it". Listing is not
    # stock, and a cart line at a dry distributor buys nothing.
    #
    # BOM/README.md had ALREADY resolved this line at Mouser on its 2026-08-01 run:
    # check_stock queries DigiKey first but keeps a live Mouser hit over a dry DigiKey
    # one (the C26/C27 rule). So the buy list was contradicting the availability table
    # printed beside it, and the table was the one that was right. Lifecycle is still
    # Active at both, so this is a dry spell, not an end-of-life -- if DigiKey refills,
    # moving it back is a one-line change here and nowhere else.
    ("PRG1",  1, "5879",        "Adafruit",     "Mouser",  "485-5879",
     "Adafruit UPDI Friend. 5879 is Adafruit's OWN product number, not a distributor "
     "P/N -- a cart upload of the bare MPN finds nothing; Mouser resolves 485-5879 "
     "(DigiKey would be 1528-5879-ND, dry as of 2026-08-02). Substitute if this one "
     "goes dry too: the HV variant, which does standard UPDI as well -- see SUBS in "
     "BOM/check_stock.py."),
    ("CBL1",  1, "TC2030-MCP",  "Tag-Connect",  None,      "",
     "Tag-Connect TC2030-MCP, the LEGGED cable. Deliberately NOT a cart line: DigiKey "
     "stocks only the legless TC2030-MCP-NL and the legged part is zero/restricted at "
     "Mouser, so order it from Tag-Connect direct. Emitting it into a cart CSV would "
     "just fail at upload, or worse, silently buy the wrong cable."),
]
# Orderable, but not from a distributor -- so it belongs on the page a human reads
# before ordering, not in a cart CSV.
#
# NOTHING UNORDERABLE IS LISTED AT ALL. The old spreadsheet carried rows for `L1`
# (the NFC antenna, which is etched PCB copper) and `SJ1` (deleted from the design
# on 2026-07-30). Neither can be bought from anywhere, so neither appears here or in
# any generated document: a line item you cannot act on is noise in a buy list. The
# same rule is what drops the 20 bridges, pads, mounting holes and unpopulated
# headers -- they are flagged in the schematic and the board, and build() filters on
# those flags rather than on a list kept here.
NOT_DISTRIBUTOR = {
    "ENC1": "the titanium back-shell -- its own fab order, machined from enclosure/*.step",
}

# A distributor P/N is an IDENTIFIER, not a description: it is submitted verbatim and
# either resolves or silently vanishes from the upload. Whitespace or a parenthetical
# means prose leaked into the field.
#
# C26/C27 carried "187-CL21B106KOQNNNG (Mouser)" in BOTH the schematic and the board
# until 2026-08-02, and the origin is legible: BOM/README.md renders that column as
# `{dist_pn} ({source})`, so a live-availability CELL was copied back into the field
# it was derived FROM -- the report's own source annotation glued onto the part number.
# A generated display string round-tripped into a source of truth, which is the failure
# this repo's one-home rule exists to prevent.
#
# It was invisible because C26/C27 sit on the ASSEMBLY side, where PCBWay buys by MPN
# and never reads the field. It was not harmless: the grouping key is (mpn, supplier,
# dist_pn), so the suffix also split one 2-off capacitor line into two 1-off lines.
# The same string on the hand-buy side is the UPDI Friend failure again.
_MALFORMED_PN = re.compile(r"[\s()]")


def _sch_parts():
    """{ref: (mpn, mfr, supplier, dist_pn, value)} for every placed schematic symbol."""
    text = open(SCH, encoding="utf-8", errors="replace").read()
    out = {}
    for blk in re.split(r"\n\t\(symbol\n", text):
        rm = re.search(r'\(property "Reference"\s+"([^"]+)"', blk)
        if not rm:
            continue

        def g(name):
            m = re.search(r'\(property "' + name + r'"\s+"([^"]*)"', blk)
            return m.group(1).strip() if m else ""

        ref = rm.group(1)
        if ref.startswith("#"):
            continue                      # power flags
        if ref in out and out[ref][0]:
            continue                      # keep the first instance that carries an MPN
        out[ref] = (g("MPN"), g("Manufacturer"), g("Supplier"), g("Supplier P/N"),
                    g("Value"))
    return out


def _board_flags():
    """{ref: (excluded_from_bom, dnp, footprint)} straight from the board."""
    import pcbnew
    b = pcbnew.LoadBoard(PCB)
    return {f.GetReference(): (f.IsExcludedFromBOM(), f.IsDNP(), f.GetFPIDAsString())
            for f in b.GetFootprints() if f.GetReference()}


def _group(rows):
    """Collapse [(ref, mpn, mfr, supplier, dist_pn, value, fp)] into per-MPN lines."""
    by = {}
    for ref, mpn, mfr, sup, dpn, val, fp in rows:
        k = (mpn, sup, dpn)
        e = by.setdefault(k, {"refs": [], "value": val, "fp": fp, "mfr": mfr})
        e["refs"].append(ref)
    out = []
    for (mpn, sup, dpn), e in by.items():
        refs = sorted(e["refs"], key=lambda r: (re.sub(r"\d", "", r),
                                                int(re.sub(r"\D", "", r) or 0)))
        out.append({"mpn": mpn, "mfr": e["mfr"], "supplier": sup, "dist_pn": dpn,
                    "refs": refs, "qty": len(refs), "value": e["value"],
                    "footprint": e["fp"]})
    return sorted(out, key=lambda d: (d["supplier"] or "~", d["mpn"]))


def build():
    """-> (assembly, handbuy, offboard, offboard_once, problems). THE one definition."""
    sch, flags = _sch_parts(), _board_flags()
    asm_rows, hand_rows, problems = [], [], []
    for ref, (exbom, dnp, fp) in sorted(flags.items()):
        mpn, mfr, sup, dpn, val = sch.get(ref, ("", "", "", "", ""))
        # A "no part" placeholder MPN is how this schematic marks bridges, pads,
        # mounting holes and unpopulated headers. They order nothing, by design.
        placeholder = mpn.startswith("(") or not mpn
        if dnp or placeholder:
            continue
        row = (ref, mpn, mfr, sup, dpn, val, fp)
        if exbom:
            hand_rows.append(row)
        else:
            asm_rows.append(row)
        # A missing Manufacturer is a GATE, not a cosmetic gap. pick_match() in
        # BOM/check_stock.py treats the manufacturer as a hard filter for
        # collision-prone MPNs (short or all-numeric), and an empty one makes
        # mfr_ok() return True unconditionally -- the filter is not bypassed, it is
        # starved. That is exactly how the 2026-08-02 run published a Pomona test
        # clip as the UPDI Friend. Failing here means the availability table can
        # never again silently lose its only defence against a wrong match.
        if not mfr:
            problems.append(f"{ref} ({mpn}) has an MPN but no Manufacturer -- "
                            f"check_stock's collision filter needs it to tell this "
                            f"part from another vendor's identically-numbered one")
        if not sup:
            problems.append(f"{ref} ({mpn}) has an MPN but no Supplier -- cannot be routed to a cart")
        elif not dpn:
            problems.append(f"{ref} ({mpn}) is sourced from {sup} but carries no Supplier P/N -- "
                            f"a cart upload cannot resolve a bare MPN")
        elif _MALFORMED_PN.search(dpn):
            problems.append(f'{ref} ({mpn}) has a Supplier P/N that is not a part number: '
                            f'"{dpn}". A distributor resolves the identifier verbatim, so a '
                            f'parenthetical or a trailing note makes the line unresolvable.')
    return _group(asm_rows), _group(hand_rows), OFF_BOARD, OFF_BOARD_ONCE, problems


def _w(path, header, rows):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        wr = csv.writer(fh)
        wr.writerow(header)
        wr.writerows(rows)
    return f"{os.path.relpath(path, ROOT)} ({len(rows)} line(s))"


def write_all(boards, outdir):
    asm, hand, off, once, problems = build()
    problems = list(problems)
    os.makedirs(outdir, exist_ok=True)
    made = []

    # 1. PCBWay assembly BOM
    # Manufacturer sits beside the MPN because that is the pair an assembler actually
    # buys on: a part number alone is ambiguous exactly where it is short or numeric,
    # which is the same hazard that made the field a hard filter in check_stock.
    made.append(_w(os.path.join(outdir, f"{STEM}-pcbway-assembly.csv"),
                   ["Designator", "Qty per board", "Value", "Footprint", "MPN",
                    "Manufacturer", "Supplier", "Supplier P/N"],
                   [[" ".join(r["refs"]), r["qty"], r["value"], r["footprint"], r["mpn"],
                     r["mfr"], r["supplier"], r["dist_pn"]] for r in asm]))

    # 2/3. Hand-buy carts, one file per distributor, in that distributor's upload shape.
    #      DigiKey wants Quantity,Part Number,Customer Reference; Mouser wants its own
    #      part number first. Anything with no distributor P/N falls back to the MPN,
    #      which both accept.
    carts = {}
    for r in hand + [{"mpn": m, "mfr": mf, "supplier": s, "dist_pn": d, "refs": [ref],
                      "qty": q, "value": n, "footprint": ""}
                     for ref, q, m, mf, s, d, n in off]:
        if r["supplier"]:
            carts.setdefault(r["supplier"], []).append((r, boards))
    for ref, q, m, mf, s, d, n in once:      # tools: quantity does NOT scale with boards
        if s:                                # None == not a cart line; the page carries it
            carts.setdefault(s, []).append(({"mpn": m, "mfr": mf, "supplier": s,
                                             "dist_pn": d, "refs": [ref], "qty": q,
                                             "value": n, "footprint": ""}, 1))
    for sup, items in sorted(carts.items()):
        rows = []
        for r, mult in items:
            # NO MPN FALLBACK. A distributor cart resolves ITS OWN part number; a bare
            # manufacturer product code may or may not match, and when it does not the
            # line simply vanishes from the upload with no error. That is exactly how the
            # UPDI Friend went missing on 2026-08-02: emitted as Adafruit's "5879" when
            # DigiKey wanted "1528-5879-ND". A line without a distributor P/N is a defect
            # in this table, caught here rather than at the checkout page.
            if not r["dist_pn"]:
                problems.append(
                    f"{', '.join(r['refs'])} ({r['mpn']}, {sup}) has no distributor part "
                    f"number -- a cart upload cannot resolve it. Add its P/N, or set its "
                    f"supplier to None so it lands on the readable page instead.")
                continue
            rows.append([r["qty"] * mult, r["dist_pn"], " ".join(r["refs"])])
        made.append(_w(os.path.join(outdir, f"{STEM}-handbuy-{sup.lower()}.csv"),
                       ["Quantity", "Part Number", "Customer Reference"], rows))

    # 4. One human-readable page for the whole hand buy, because a cart CSV cannot
    #    carry the traps (the legless cable, the two-MPN supercap split).
    md = [f"# Hand-buy list — SOLAR-GLOW DRH v4.0 ({boards} board"
          f"{'s' if boards != 1 else ''})", "",
          "GENERATED by `scripts/bom_split.py` — do not edit. Everything here is bought by",
          "**you**, not by PCBWay: the deliberately hand-soldered parts plus the items that",
          "never reach a pick-and-place.", "",
          "| Ref(s) | Qty | MPN | Manufacturer | Supplier | Distributor P/N | What |",
          "|---|---|---|---|---|---|---|"]
    for r in hand:
        md.append(f"| {', '.join(r['refs'])} | {r['qty'] * boards} | `{r['mpn']}` | "
                  f"{r['mfr'] or '—'} | {r['supplier']} | {r['dist_pn']} | {r['value']} |")
    for ref, q, m, mf, s, d, n in off:
        md.append(f"| {ref} | {q * boards} | `{m}` | {mf or '—'} | {s or '—'} | "
                  f"{d or '—'} | {n} |")
    md += ["", f"**Bought once for the project, not per board:**", "",
           "| Ref | Qty | MPN | Manufacturer | Supplier | Distributor P/N | What |",
           "|---|---|---|---|---|---|---|"]
    for ref, q, m, mf, s, d, n in once:
        md.append(f"| {ref} | {q} | `{m}` | {mf or '—'} | {s or '—'} | {d or '—'} | {n} |")
    md += ["", "**Ordered, but not from a distributor:**", ""]
    for ref, why in sorted(NOT_DISTRIBUTOR.items()):
        md.append(f"- `{ref}` — {why}")
    md += ["", "**The supercaps are two different parts.** SC1/SC3 and SC2/SC4 are different",
           "capacitances with different MPNs and separate stock pools; four of either one",
           "builds nothing. Consistency check [15] holds this list against the board."]
    p = os.path.join(outdir, f"{STEM}-handbuy.md")
    open(p, "w", encoding="utf-8").write("\n".join(md) + "\n")
    made.append(f"{os.path.relpath(p, ROOT)} ({len(hand) + len(off) + len(once)} line(s))")
    return asm, hand, problems, made


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--boards", type=int, default=1, help="scale per-board quantities")
    ap.add_argument("--check", action="store_true", help="report only, write nothing")
    ap.add_argument("--outdir", default=OUTDIR)
    a = ap.parse_args()
    if a.check:
        asm, hand, _, _, problems = build()
        print(f"  assembly (PCBWay places): {len(asm)} line(s), "
              f"{sum(r['qty'] for r in asm)} part(s) per board")
        print(f"  hand-buy (you solder):    {len(hand)} line(s), "
              f"{sum(r['qty'] for r in hand)} part(s) per board")
        for r in hand:
            print(f"      {r['mpn']:16} x{r['qty']}  {', '.join(r['refs'])}")
        print(f"  off-board:                {len(OFF_BOARD)} per-board + "
              f"{len(OFF_BOARD_ONCE)} one-off + {len(NOT_DISTRIBUTOR)} non-distributor")
        for p in problems:
            print(f"  PROBLEM: {p}")
        return 1 if problems else 0
    asm, hand, problems, made = write_all(a.boards, a.outdir)
    for m in made:
        print(f"  wrote {m}")
    for p in problems:
        print(f"  PROBLEM: {p}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
