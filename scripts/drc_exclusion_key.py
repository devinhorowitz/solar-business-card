#!/usr/bin/env python3
"""Derive a KiCad DRC exclusion key from the board, using KiCad's own geometry.

WHY THIS EXISTS
---------------
A `drc_exclusions` entry in the `.kicad_pro` is the string

    <settings_key>|<marker_x_nm>|<marker_y_nm>|<main_item_uuid>|<aux_item_uuid>

(`PCB_MARKER::SerializeToString`). The two UUIDs are readable straight out of
the `.kicad_pcb`, and the DRC report prints both items' positions -- so the key
LOOKS hand-authorable, and for several of this board's exclusions the numbers
happen to match an item's own position, which makes it look confirmed.

It is not. `x|y` is the **DRC marker** position, which the test provider takes
from the collision itself:

    refShape->Collide( testShape, minClearance, &actual, &pos )   // pos -> marker

For a straight silk segment lying inside a large mask polygon that collide
point lands on the segment's own start, which is why D2/D3/D4's window-clip
exclusions look like "first item's position". For Q2's round pin-1 dot against
R18's roundrect pad it lands at (26.26, 62.0525) -- 0.28 mm from the circle
centre the DRC report prints, and *inside* the pad. Hand-authoring it from the
report gives a key that matches nothing.

A key that matches nothing FAILS SILENTLY: the violation simply stays in the
report, and the only symptom is a warning you thought you had ledgered. That is
the same shape as every other trap in this repo -- a human-typed value sitting
next to generated truth with no gate between -- so the value is taken from
KiCad here rather than retyped.

USAGE
-----
    # what is the key for this violation?
    python3 scripts/drc_exclusion_key.py --pair <uuid_a> <uuid_b> --rule silk_over_copper

    # ...and prove it by actually running DRC with it (never touches your tree)
    python3 scripts/drc_exclusion_key.py --pair <uuid_a> <uuid_b> \
            --rule silk_over_copper --verify

    # are any exclusions already in the .kicad_pro dead (matching no violation)?
    python3 scripts/drc_exclusion_key.py --check-dead

SCOPE, HONESTLY
---------------
This covers the two-item rules whose marker is the shape-collision point --
the silk, clearance and courtyard families. It does NOT model every provider:
some place the marker elsewhere (`copper_edge_clearance` puts it on the outline
crossing, `courtyards_overlap` inside the overlap region), and this board's
entries for those were written by the GUI. `--verify` is what tells you which
case you are in: if no candidate takes, add the exclusion in the KiCad GUI
(right-click the marker -> Exclude) and let it write the key.

An exclusion still needs a human REASON. This script deliberately only prints
keys -- it will not edit the `.kicad_pro` for you.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BOARD = REPO / "PCB" / "solar-glow-drh-v4_0.kicad_pcb"


def _pcbnew():
    try:
        import pcbnew  # noqa: PLC0415
    except ImportError:
        sys.exit("pcbnew Python module not found -- run this inside the KiCad image "
                 "(same pinned digest kibot.yml uses) or a local KiCad 10 install.")
    return pcbnew


def resolve(board, uuid):
    """Find any board item by UUID, and report which layers it lives on."""
    pcbnew = _pcbnew()

    def layers_of(item):
        try:
            lays = [lay for lay in item.GetLayerSet().Seq()]
        except Exception:
            lays = []
        return lays or [item.GetLayer()]

    pools = []
    for fp in board.GetFootprints():
        pools += [("pad", p) for p in fp.Pads()]
        pools += [("fp-graphic", d) for d in fp.GraphicalItems()]
        pools.append(("footprint", fp))
    pools += [("track", t) for t in board.GetTracks()]
    pools += [("graphic", d) for d in board.GetDrawings()]
    pools += [("zone", z) for z in board.Zones()]

    for kind, item in pools:
        if item.m_Uuid.AsString() == uuid:
            # dedupe while preserving order; a pad reports Cu + Mask + Paste
            seen, lays = set(), []
            for lay in layers_of(item):
                if lay not in seen:
                    seen.add(lay)
                    lays.append(lay)
            return kind, item, lays
    sys.exit(f"UUID {uuid} not found in {board.GetFileName()}")


def candidate_keys(board_path, rule, uuid_a, uuid_b):
    """Every marker position KiCad's Collide yields across the items' layer pairs."""
    pcbnew = _pcbnew()
    board = pcbnew.LoadBoard(str(board_path))
    kind_a, item_a, layers_a = resolve(board, uuid_a)
    kind_b, item_b, layers_b = resolve(board, uuid_b)

    out = {}
    for la in layers_a:
        for lb in layers_b:
            try:
                sa = item_a.GetEffectiveShape(la)
                sb = item_b.GetEffectiveShape(lb)
            except Exception:
                continue
            loc = pcbnew.VECTOR2I()
            if not sa.Collide(sb, 0, None, loc):
                continue
            key = f"{rule}|{loc.x}|{loc.y}|{uuid_a}|{uuid_b}"
            out.setdefault(key, []).append(
                f"{kind_a} on {board.GetLayerName(la)} vs {kind_b} on {board.GetLayerName(lb)}"
            )
    return out, (kind_a, kind_b)


def run_drc(board_path, out_json):
    subprocess.run(
        ["kicad-cli", "pcb", "drc", "--refill-zones", "--severity-all",
         "--format", "json", "-o", str(out_json), str(board_path)],
        check=True, capture_output=True,
    )
    return json.loads(Path(out_json).read_text())


def verify(board_path, keys):
    """Inject every candidate with a unique comment into a THROWAWAY copy, run DRC once.

    An excluded violation echoes its comment back in the JSON report, so one run
    identifies exactly which candidate matched -- no bisection, and the real tree
    is never written to.
    """
    pro_src = board_path.with_suffix(".kicad_pro")
    with tempfile.TemporaryDirectory() as td:
        tmp_board = Path(td) / board_path.name
        tmp_pro = Path(td) / pro_src.name
        shutil.copy(board_path, tmp_board)
        shutil.copy(pro_src, tmp_pro)
        pro = json.loads(tmp_pro.read_text())
        ds = pro["board"]["design_settings"]
        ds["drc_exclusions"] = ds.get("drc_exclusions", []) + [
            [k, f"CANDIDATE {i}"] for i, k in enumerate(keys)
        ]
        tmp_pro.write_text(json.dumps(pro, indent=2))
        report = run_drc(tmp_board, Path(td) / "drc.json")

    for v in report["violations"]:
        comment = v.get("comment") or ""
        if v.get("excluded") and comment.startswith("CANDIDATE "):
            return keys[int(comment.split()[1])], v
    return None, None


def check_dead(board_path):
    """Report exclusion entries that match no violation in the current DRC run.

    KiCad prunes these on a GUI save, so a hit means either a hand-authored key
    that never matched, or a real geometry change since the last GUI session.

    Matching is EXACT, not heuristic: on a throwaway copy every exclusion's
    comment is replaced by a unique index tag, and an excluded violation echoes
    its comment back in the JSON report. The first cut of this compared the
    comments as they stand, and three of this board's entries share the empty
    comment -- so it named two live window-clip exclusions dead alongside the
    real one. A checker that cries wolf is worse than no checker.
    """
    pro_src = board_path.with_suffix(".kicad_pro")
    entries = json.loads(pro_src.read_text())["board"]["design_settings"].get("drc_exclusions", [])
    if not entries:
        return [], 0, 0

    with tempfile.TemporaryDirectory() as td:
        tmp_board = Path(td) / board_path.name
        tmp_pro = Path(td) / pro_src.name
        shutil.copy(board_path, tmp_board)
        shutil.copy(pro_src, tmp_pro)
        pro = json.loads(tmp_pro.read_text())
        pro["board"]["design_settings"]["drc_exclusions"] = [
            [key, f"TAG {i}"] for i, (key, _) in enumerate(entries)
        ]
        tmp_pro.write_text(json.dumps(pro, indent=2))
        report = run_drc(tmp_board, Path(td) / "drc.json")

    seen = set()
    for v in report["violations"]:
        comment = v.get("comment") or ""
        if v.get("excluded") and comment.startswith("TAG "):
            seen.add(int(comment.split()[1]))
    dead = [key for i, (key, _) in enumerate(entries) if i not in seen]
    return dead, len(entries), len(seen)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--board", type=Path, default=BOARD)
    ap.add_argument("--pair", nargs=2, metavar=("MAIN_UUID", "AUX_UUID"),
                    help="the violation's two item UUIDs, in the order the DRC report lists them")
    ap.add_argument("--rule", default="silk_over_copper",
                    help="the rule's settings key, as printed in [brackets] by the DRC report")
    ap.add_argument("--verify", action="store_true",
                    help="prove the key by running DRC with it on a throwaway copy")
    ap.add_argument("--check-dead", action="store_true",
                    help="flag .kicad_pro exclusions that match no current violation")
    args = ap.parse_args()

    if args.check_dead:
        dead, total, matched = check_dead(args.board)
        print(f"{total} exclusion entries, {matched} matched a violation this run")
        for key in dead:
            print(f"  DEAD: {key}")
        return 1 if dead else 0

    if not args.pair:
        ap.error("--pair is required unless --check-dead is given")

    keys, kinds = candidate_keys(args.board, args.rule, *args.pair)
    if not keys:
        print(f"No collision between {kinds[0]} and {kinds[1]} on any shared layer pair.\n"
              "This rule's marker is probably not the collide point -- use the KiCad GUI.")
        return 1

    print(f"{len(keys)} candidate key(s):")
    for key, why in keys.items():
        print(f"  {key}\n      from {'; '.join(why)}")

    if args.verify:
        winner, violation = verify(args.board, list(keys))
        if not winner:
            print("\nNone matched a live violation. Either the violation is not firing, "
                  "or this rule places its marker elsewhere -- use the KiCad GUI.")
            return 1
        print(f"\nVERIFIED -- this key excludes the violation:\n  {winner}")
        print("  " + "; ".join(i["description"] for i in violation["items"]))
        print("\nPaste it into PCB/*.kicad_pro drc_exclusions WITH A REASON as the "
              "second element. An exclusion without a reason is just a hidden warning.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
