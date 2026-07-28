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


# Camera notes, so nobody has to re-derive these by eye:
#   * Framing was SOLVED, not guessed. Probes rendered with --background transparent give a
#     clean alpha bounding box; zoom was bisected until the tightest margin hit ~10%, then
#     --pan was calibrated in pixels-per-unit and solved for centre. Angled shots at zoom
#     0.85-0.95 clipped a bottom corner; 0.736 is the value that fits a portrait board in a
#     4:3 frame. Re-solve rather than nudge if you change --rotate.
#   * --floor is the single biggest quality lever: it enables shadows and the post-processing
#     pass. It works even at --quality basic, if CI time ever needs cutting.
#   * The light options take INTENSITIES, not colours — a float or "R,G,B" floats. Hex is
#     rejected outright with "Invalid light top intensity format".
FLAT = []
ANGLE = ["--perspective", "--floor", "--zoom", "0.736"]
WARM = ["--light-top", "0.20,0.18,0.15", "--light-side", "1.0,0.70,0.28",
        "--light-camera", "0.05", "--light-side-elevation", "10"]

TARGETS = {
    "panel": dict(
        source=PANEL, midnight=False,
        desc="PCBWay view — the card still in its frame",
        views=[
            ("top", ["--side", "top", "--floor"], None),
            ("bottom", ["--side", "bottom", "--floor"], None),
            ("angle", ANGLE + ["--side", "top", "--rotate", "-28,0,14",
                               "--pan", "0.27,0.65,0"], (1600, 1200)),
        ],
    ),
    "card": dict(
        source=BOARD, midnight=False,
        desc="The card itself, depanelised — reference faces plus the hero angles",
        views=[
            ("face", ["--side", "top", "--floor"], None),
            ("back", ["--side", "bottom", "--floor"], None),
            ("hero", ANGLE + ["--side", "top", "--rotate", "-25,0,20",
                              "--pan", "-0.05,0.56,0"], (1600, 1200)),
            ("back-angle", ANGLE + ["--side", "bottom", "--rotate", "-25,0,-18",
                                    "--pan", "0.05,0.56,0"], (1600, 1200)),
            # Low raking macro: the monogram sits centre-frame and the crosshatch finally
            # reads as texture rather than a dot screen. This is the main-README hero.
            ("macro", ["--perspective", "--floor", "--side", "top", "--rotate", "-62,0,6",
                       "--zoom", "1.9", "--pan", "0,0.35,0"] + WARM, (1800, 1100)),
            # Near-grazing: sells the 0.6 mm stack and the gold rim. Monogram is unreadable
            # here by design — this is a supporting image, never a hero.
            ("grazing", ["--perspective", "--floor", "--side", "top", "--rotate", "-78,0,0",
                         "--zoom", "1.35", "--pan", "0,0.15,0"] + WARM, (1800, 1100)),
        ],
    ),
    # The only target that KEEPS its component bodies. Everything else here is a bare
    # fabricated board on purpose; this one answers the other question — what the thing
    # looks like assembled. It renders from the same committed board, so the parts you
    # see are the 53 footprints that actually carry a resolvable model, no more.
    "populated": dict(
        source=BOARD, midnight=False, keep_models=True,
        desc="The assembled card — components on, both faces plus a hero angle",
        views=[
            ("back", ["--side", "bottom", "--floor"], None),
            ("face", ["--side", "top", "--floor"], None),
            ("hero", ANGLE + ["--side", "bottom", "--rotate", "-25,0,-18",
                              "--pan", "0.05,0.56,0"], (1600, 1200)),
            # NO macro here, deliberately. The card target's raking -62 deg macro was solved for a
            # FLAT board; with 1.70 mm supercaps standing on it the near cap fills the frame, the
            # monogram window is fully occluded, and the shot becomes a wall of grey slabs. Rendered
            # it to check rather than assuming, and it is unusable. A populated detail shot needs its
            # own camera solve, not this one reused.
        ],
    ),
    "midnight": dict(
        source=BOARD, midnight=True,
        desc="OSH Park After Dark — black core, clear mask, naked, 1-up",
        views=[
            ("top", ["--side", "top", "--floor"], None),
            ("bottom", ["--side", "bottom", "--floor"], None),
        ],
    ),
}


def build_input(name: str, spec: dict, workdir: Path) -> Path:
    with open(spec["source"], newline="") as f:
        raw = f.read()
    nl = "\r\n" if raw.count("\r\n") else "\n"
    src = raw.replace("\r\n", "\n")

    if spec.get("keep_models"):
        note = f"{name}: KEEPING {src.count('(model ')} 3D model refs (assembled view)"
    else:
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
    # ${KIPRJMOD} resolves to whatever directory the board sits in — and the board we render
    # sits in a temp dir, not PCB/. Without this the project's own models (the supercaps, the
    # cells, the LEDs, both QFNs, the FRAM) silently resolve to nothing while the stock KiCad
    # models still load, so an "assembled" render comes back looking half-populated and nothing
    # reports an error. Carry the project 3D library along with the copy.
    shapes = BOARD.parent / "solarglow.3dshapes"
    if shapes.is_dir():
        shutil.copytree(shapes, workdir / shapes.name, dirs_exist_ok=True)
    return dest


def render(pcb: Path, out: Path, cam: list[str], w: int, h: int) -> bool:
    cmd = ["kicad-cli", "pcb", "render", "--output", str(out),
           "--quality", "high", "--use-board-stackup-colors", "--background", "opaque",
           "--width", str(w), "--height", str(h)] + cam + [str(pcb)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        tail = (r.stderr or r.stdout).strip().splitlines()[-1:] or ["(no output)"]
        print(f"  !! {out.name} failed: {tail[0]}")
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
            flat_w = max(400, int(round(HEIGHT * bw / bh / 2) * 2))
            for view, cam, size in spec["views"]:
                w, h = size if size else (flat_w, HEIGHT)
                out = OUTDIR / f"{STEM}-{name}-{view}.png"
                ok &= render(pcb, out, cam, w, h)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
