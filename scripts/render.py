#!/usr/bin/env python3
"""Raytrace the board's presentation renders. CI runs this; the README embeds the output.

    python3 scripts/render.py                 # every target -> Generated/docs/
    python3 scripts/render.py --only midnight # one target group
    python3 scripts/render.py --list          # show targets, render nothing

WHAT IT MAKES

  panel-top / panel-bottom      The PCBWay view: the 1-up card still attached to its frame,
                                both faces. This is literally what the fab ships before you
                                snap the tabs, which is why the README leads with it rather
                                than with a bare card.

  midnight-top / midnight-bottom  The OSH Park "After Dark" variant: black substrate, clear
                                soldermask, ENIG, 1.6 mm, and no components at all. Not
                                panelised — OSH Park panelises for you, and the plating bus
                                has no job there.

WHY THE INPUTS ARE REWRITTEN FIRST

Every target renders from a THROWAWAY copy of the board, never the committed file. Two
transforms matter:

  * `(model ...)` blocks are stripped from every footprint. Both of these renders are of a
    BARE FABRICATED board, so component bodies would be a lie. It also makes CI deterministic:
    the output no longer depends on whether the runner image happens to ship kicad-packages3d
    (~3 GB), which the KiBot image may or may not.

  * For midnight, the stackup colours are repainted (black core, near-clear mask), the board
    thickness goes 0.6 -> 1.6 mm, and the two plating-bus stubs at x = 25.4 are deleted. That
    stub deletion is the documented OSH Park delta — see PCB/README.md "Two fabs, one board
    file". Rendering them would show copper crossing the outline, which is exactly the thing
    that variant does not have.

The board file itself is never modified. Verify with `git status` after a run.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BOARD = ROOT / "PCB" / "solar-glow-drh-v4_0.kicad_pcb"
PANEL = ROOT / "Generated" / "panel" / "solar-glow-drh-v4_0-panel.kicad_pcb"
OUTDIR = ROOT / "Generated" / "docs"
STEM = "solar-glow-drh-v4_0"

# Midnight = OSH Park After Dark. Hex carries alpha; the mask is nearly clear so the black
# core reads through it, which is the whole point of that stack.
MIDNIGHT_CORE = "#0D0D0FFF"
MIDNIGHT_MASK = "#20202040"

HEIGHT = 1800  # width is derived per-target from the board's own aspect ratio


def sexpr_blocks(src: str, tag: str):
    """(start, end) for every '(tag' block, paren-balanced and string-aware."""
    out = []
    for m in re.finditer(r"(?m)^\s*\(" + re.escape(tag) + r"[\s(]", src):
        i = src.index("(", m.start())
        j, depth, instr = i, 0, False
        while True:
            c = src[j]
            if instr:
                if c == "\\":
                    j += 2
                    continue
                if c == '"':
                    instr = False
            elif c == '"':
                instr = True
            elif c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        out.append((i, j + 1))
    return out


def drop_blocks(src: str, tag: str) -> tuple[str, int]:
    spans = sexpr_blocks(src, tag)
    out, prev = [], 0
    for i, j in spans:
        ls = src.rfind("\n", 0, i)
        out.append(src[prev : ls + 1])
        prev = j + 1 if src[j : j + 1] == "\n" else j
    out.append(src[prev:])
    return "".join(out), len(spans)


def strip_models(src: str) -> tuple[str, int]:
    return drop_blocks(src, "model")


def strip_plating_stubs(src: str) -> tuple[str, int]:
    """The two 0.4 mm F.Cu gr_line stubs that cross the outline at x = 25.4."""
    spans = [
        (i, j)
        for i, j in sexpr_blocks(src, "gr_line")
        if '(layer "F.Cu")' in src[i:j]
        and re.search(r"\(start 25\.4 ", src[i:j])
        and re.search(r"\(end 25\.4 (-0\.4|89\.3)\)", src[i:j])
    ]
    out, prev = [], 0
    for i, j in spans:
        ls = src.rfind("\n", 0, i)
        out.append(src[prev : ls + 1])
        prev = j + 1 if src[j : j + 1] == "\n" else j
    out.append(src[prev:])
    return "".join(out), len(spans)


def paint_midnight(src: str) -> str:
    src = src.replace('(type "Top Solder Mask")\n\t\t\t\t(color "Black")',
                      f'(type "Top Solder Mask")\n\t\t\t\t(color "{MIDNIGHT_MASK}")')
    src = src.replace('(type "Bottom Solder Mask")\n\t\t\t\t(color "Black")',
                      f'(type "Bottom Solder Mask")\n\t\t\t\t(color "{MIDNIGHT_MASK}")')
    src = src.replace('(color "FR4 natural")', f'(color "{MIDNIGHT_CORE}")')
    # OSH Park After Dark ships 1.6 mm, not the 0.6 mm production stack.
    src = src.replace("(thickness 0.6)\n\t\t(legacy_teardrops", "(thickness 1.6)\n\t\t(legacy_teardrops")
    src = src.replace('(type "core")\n\t\t\t\t(color', '(type "core")\n\t\t\t\t(color')
    src = re.sub(r'(\(type "core"\)\s*\(color "[^"]*"\)\s*\(thickness )0\.51\)', r"\g<1>1.51)", src)
    return src


def board_extent(src: str) -> tuple[float, float]:
    xs, ys = [], []
    for i, j in sexpr_blocks(src, "gr_line"):
        blk = src[i:j]
        if '(layer "Edge.Cuts")' not in blk:
            continue
        for m in re.finditer(r"\((?:start|end) (-?[\d.]+) (-?[\d.]+)\)", blk):
            xs.append(float(m[1]))
            ys.append(float(m[2]))
    if not xs:
        return 50.8, 88.9
    return max(xs) - min(xs), max(ys) - min(ys)


TARGETS = {
    "panel": dict(source=PANEL, midnight=False,
                  desc="PCBWay view — the card still in its frame, both faces"),
    "midnight": dict(source=BOARD, midnight=True,
                     desc="OSH Park After Dark — black core, clear mask, naked, 1-up"),
}


def build_input(name: str, spec: dict, workdir: Path) -> Path:
    with open(spec["source"], newline="") as f:
        raw = f.read()
    nl = "\r\n" if raw.count("\r\n") else "\n"
    src = raw.replace("\r\n", "\n")

    src, n_models = strip_models(src)
    note = f"{name}: stripped {n_models} 3D model refs"
    if spec["midnight"]:
        src, n_stubs = strip_plating_stubs(src)
        src = paint_midnight(src)
        note += f", removed {n_stubs} plating stubs, repainted stackup"
    print("  " + note)

    dest = workdir / f"{name}.kicad_pcb"
    with open(dest, "w", newline="") as f:
        f.write(src.replace("\n", nl) if nl != "\n" else src)
    for ext in ("kicad_pro", "kicad_dru"):
        s = spec["source"].with_suffix("." + ext)
        if not s.exists():
            s = BOARD.with_suffix("." + ext)
        if s.exists():
            shutil.copy(s, dest.with_suffix("." + ext))
    return dest


def render(pcb: Path, out: Path, side: str, w: int, h: int) -> bool:
    cmd = ["kicad-cli", "pcb", "render", "--output", str(out), "--side", side,
           "--quality", "high", "--use-board-stackup-colors", "--background", "opaque",
           "--width", str(w), "--height", str(h), str(pcb)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"  !! {side} failed: {(r.stderr or r.stdout).strip().splitlines()[-1:]}")
        return False
    print(f"  wrote {out.relative_to(ROOT)}  ({out.stat().st_size:,} bytes)")
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=sorted(TARGETS))
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()

    if args.list:
        for k, v in TARGETS.items():
            print(f"{k:10s} {v['desc']}\n{'':10s} source: {v['source'].relative_to(ROOT)}")
        return 0

    if not shutil.which("kicad-cli"):
        sys.exit("render: kicad-cli not found — this needs KiCad 10 (CI runs it in the KiBot image)")

    OUTDIR.mkdir(parents=True, exist_ok=True)
    todo = {args.only: TARGETS[args.only]} if args.only else TARGETS
    ok = True
    with tempfile.TemporaryDirectory() as td:
        work = Path(td)
        for name, spec in todo.items():
            if not spec["source"].exists():
                if name == "panel":
                    sys.exit(f"render: {spec['source']} missing — run scripts/panelize.py first")
                sys.exit(f"render: {spec['source']} missing")
            print(f"[{name}] {spec['desc']}")
            pcb = build_input(name, spec, work)
            with open(pcb, newline="") as f:
                bw, bh = board_extent(f.read().replace("\r\n", "\n"))
            w = max(400, int(round(HEIGHT * bw / bh / 2) * 2))
            for side in ("top", "bottom"):
                out = OUTDIR / f"{STEM}-{name}-{side}.png"
                ok &= render(pcb, out, side, w, HEIGHT)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
