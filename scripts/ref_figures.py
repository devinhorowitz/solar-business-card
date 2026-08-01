#!/usr/bin/env python3
"""Reference figures for PCB/README.md's assembly steps, drawn FROM the board file.

Two figures, both consumed by the PCBA instructions:

  Generated/docs/<stem>-led-orientation.png   D2-D5 reverse-mount polarity (the check the
                                              assembler runs before reflow: anode side,
                                              cathode side, rotation, board side)
  Generated/docs/<stem>-sw2-selector.png      the SW2 LED master bridge: which pad pair is
                                              ON, which is TINY, and through what

They replaced two hand-uploaded v2-era PNGs (PCB/led-orientation-D2-D5.png,
PCB/sw2-anode-selector.png, culled 2026-08-01) that had gone stale three ways at once with
nothing to notice: a ghost SJ1 (removed from schematic and board 2026-07-30), SW2/R12 drawn
at pre-move positions, and dead net names ("In2", "VS") from two rail redesigns ago. Every
geometric and electrical fact below -- positions, pad offsets, rotations, sides, net names,
R12's value and what it bridges -- is read out of the one committed .kicad_pcb, so the
figures cannot silently disagree with the board. What little prose they carry (what ON/OFF
*mean* for the supercap) is copy, not data.

The asserts are the point: if a re-route rotates an LED, moves the dim path off R12, or
renames the anode rail, this script fails the CI job loudly instead of drawing yesterday's
board with today's date. Fix the figure's assumptions, not the assert.

Read-only on the board. Runner-side matplotlib, nothing KiCad. Wired into kibot.yml (its
own edit is a trigger there -- the #132 lesson: a generator edit must regenerate).
"""

import glob
import math
import os
import re

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, Rectangle

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "Generated", "docs")

# ---- the one board -------------------------------------------------------------------------
# PCB/ holds exactly one revision by rule (CLAUDE.md); glob rather than hard-code the name so
# a future rev rename follows automatically instead of drawing a board that left the tree.
_boards = sorted(glob.glob(os.path.join(ROOT, "PCB", "*.kicad_pcb")))
assert len(_boards) == 1, f"PCB/ must hold exactly one board revision, found {len(_boards)}: {_boards}"
BOARD = _boards[0]
STEM = os.path.basename(BOARD)[: -len(".kicad_pcb")]


def _block(s, start):
    """The balanced-paren s-expression starting at s[start] == '('."""
    depth, in_str = 0, False
    for j in range(start, len(s)):
        c = s[j]
        if c == '"' and s[j - 1] != "\\":
            in_str = not in_str
        elif not in_str:
            if c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
                if depth == 0:
                    return s[start : j + 1]
    raise ValueError("unbalanced s-expression")


def footprint(board_text, ref):
    """One footprint's placement, value and pads -- everything the figures consume."""
    m = re.search(r'\(property "Reference"\s+"%s"' % re.escape(ref), board_text)
    assert m, f"{ref} not found on {os.path.basename(BOARD)}"
    fp = _block(board_text, board_text.rfind("(footprint", 0, m.start()))
    at = re.search(r"\(at\s+([-\d.]+)\s+([-\d.]+)(?:\s+([-\d.]+))?\)", fp)
    layer = re.search(r'\(layer\s+"([^"]+)"\)', fp)
    value = re.search(r'\(property "Value"\s+"([^"]+)"', fp)
    out = {
        "ref": ref,
        "x": float(at.group(1)),
        "y": float(at.group(2)),
        "rot": float(at.group(3) or 0),
        "layer": layer.group(1),
        "value": value.group(1) if value else "",
        "pads": [],
    }
    for pm in re.finditer(r'\(pad\s+"([^"]*)"', fp):
        pd = _block(fp, pm.start())
        pat = re.search(r"\(at\s+([-\d.]+)\s+([-\d.]+)(?:\s+([-\d.]+))?\)", pd)
        psz = re.search(r"\(size\s+([-\d.]+)\s+([-\d.]+)", pd)
        # this board writes nets as (net "NAME"); accept the numbered form too
        pnet = re.search(r'\(net\s+(?:\d+\s+)?"([^"]+)"\)', pd)
        ox, oy = float(pat.group(1)), float(pat.group(2))
        # pad offsets are in the footprint frame; rotate into board coords
        a = math.radians(out["rot"])
        gx = out["x"] + ox * math.cos(a) + oy * math.sin(a)
        gy = out["y"] - ox * math.sin(a) + oy * math.cos(a)
        out["pads"].append(
            {
                "name": pm.group(1),
                "gx": gx,
                "gy": gy,
                "w": float(psz.group(1)),
                "h": float(psz.group(2)),
                "net": pnet.group(1) if pnet else None,
            }
        )
    return out


def pad(fp, name):
    hits = [p for p in fp["pads"] if p["name"] == name]
    assert len(hits) == 1, f'{fp["ref"]} pad "{name}": expected exactly one, found {len(hits)}'
    return hits[0]


_b = open(BOARD).read()
LEDS = [footprint(_b, r) for r in ("D2", "D3", "D4", "D5")]
SW2 = footprint(_b, "SW2")
R12 = footprint(_b, "R12")

# ---- the facts both figures assert before drawing ------------------------------------------
ANODE_NET = pad(SW2, "2")["net"]
for led in LEDS:
    assert pad(led, "A")["net"] == ANODE_NET, (
        f'{led["ref"]} anode is on "{pad(led, "A")["net"]}", not the SW2 center-pad rail '
        f'"{ANODE_NET}" -- the master-switch story changed; redraw, do not patch'
    )
assert len(SW2["pads"]) == 3, f'SW2 has {len(SW2["pads"])} pads, the 3-pad bridge story is dead'
ON_NET, TINY_NET = pad(SW2, "1")["net"], pad(SW2, "3")["net"]
_r12_nets = {p["net"] for p in R12["pads"]}
assert _r12_nets == {TINY_NET, ON_NET}, (
    f"R12 bridges {sorted(_r12_nets)}, not the TINY->{ON_NET} dim path the figure explains"
)

_rots = {led["rot"] for led in LEDS}
assert len(_rots) == 1, f"D2-D5 no longer share one rotation ({_rots}); give each its own label"
LED_ROT = _rots.pop()
_layers = {led["layer"] for led in LEDS} | {SW2["layer"], R12["layer"]}
assert _layers == {"B.Cu"}, f"expected everything here on B.Cu, found {_layers}"
SIDE_NOTE = "back side, board coords -- as drawn in KiCad; mirror left-right when holding the board back-up"

GOLD, RED, BODY = "#c9a227", "#d0421b", "#262626"


def _save(fig, name):
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, name)
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"wrote {os.path.relpath(path, ROOT)}")


# ---- figure 1: D2-D5 polarity ---------------------------------------------------------------
def led_orientation():
    fig, ax = plt.subplots(figsize=(11.5, 4.2))
    ax.set_aspect("equal")
    ax.axis("off")

    ka = pad(LEDS[0], "K")["gx"] - pad(LEDS[0], "A")["gx"]
    for led in LEDS:
        d = pad(led, "K")["gx"] - pad(led, "A")["gx"]
        assert d * ka > 0, f'{led["ref"]} cathode points the other way from D2 -- per-LED arrows needed'
    k_dir = "+X" if ka > 0 else "-X"
    a_side, k_side = ("LEFT", "RIGHT") if ka > 0 else ("RIGHT", "LEFT")

    for led in LEDS:
        pa, pk = pad(led, "A"), pad(led, "K")
        xs = [p["gx"] for p in led["pads"]]
        ys = [p["gy"] for p in led["pads"]]
        bw = (max(xs) - min(xs)) + 1.6           # body from the pad extent, not a datasheet
        bh = (max(ys) - min(ys)) + 1.7
        ax.add_patch(Rectangle((led["x"] - bw / 2, led["y"] - bh / 2), bw, bh,
                               facecolor=BODY, edgecolor="black", zorder=1))
        for p, col, lbl in ((pa, GOLD, "A"), (pk, RED, "K")):
            ax.add_patch(Rectangle((p["gx"] - p["w"] / 2, p["gy"] - p["h"] / 2), p["w"], p["h"],
                                   facecolor=col, edgecolor="black", lw=0.6, zorder=2))
            # smaller y is UP the display once the axis inverts; va="bottom" keeps the
            # label wholly above the body instead of bleeding into it
            ax.text(p["gx"], led["y"] - bh / 2 - 0.35, lbl, ha="center", va="bottom",
                    fontsize=13, fontweight="bold", color=col)
        bar_x = led["x"] + (bw / 2 - 0.25) * (1 if ka > 0 else -1)
        ax.plot([bar_x, bar_x], [led["y"] - bh / 2 + 0.25, led["y"] + bh / 2 - 0.25],
                color=RED, lw=2.2, zorder=3)
        ax.text(led["x"], led["y"] + bh / 2 + 0.75, led["ref"], ha="center", va="bottom",
                fontsize=13, fontweight="bold")

    x0 = min(led["x"] for led in LEDS) - 2.5
    x1 = max(led["x"] for led in LEDS) + 2.5
    y_arrow = LEDS[0]["y"] + 4.6
    tail, head = ((x0, y_arrow), (x1, y_arrow)) if ka > 0 else ((x1, y_arrow), (x0, y_arrow))
    ax.add_patch(FancyArrowPatch(tail, head, arrowstyle="-|>", mutation_scale=18,
                                 color=RED, lw=1.8))
    far = max(LEDS, key=lambda l: l["x"] * (1 if ka > 0 else -1))["ref"]
    ax.text((x0 + x1) / 2, y_arrow - 0.35,      # above the arrow line (display up = smaller y)
            f"cathode (K) side  →  {k_dir}  (toward {far})",
            ha="center", va="bottom", fontsize=13, color=RED, fontweight="bold")

    ax.text((x0 + x1) / 2, LEDS[0]["y"] - 4.6,  # title at the display TOP
            f"{STEM}  —  D2–D5 reverse-mount LED polarity  ({SIDE_NOTE})",
            ha="center", va="bottom", fontsize=12.5)
    ax.text((x0 + x1) / 2, y_arrow + 1.6,       # derived-facts footer under the arrow
            f"anode (A) on the {a_side}  •  cathode (K) on the {k_side}  •  "
            f"all four at rotation {LED_ROT:g}  •  common anode rail “{ANODE_NET}”"
            f"  •  REVERSE-MOUNT (emit through the board to the front)",
            ha="center", va="top", fontsize=10.5)
    ax.set_xlim(x0 - 2, x1 + 2)
    ax.set_ylim(LEDS[0]["y"] - 6.4, y_arrow + 3.4)
    ax.invert_yaxis()                            # KiCad board coords: +y is DOWN the board
    _save(fig, f"{STEM}-led-orientation.png")


# ---- figure 2: the SW2 master bridge --------------------------------------------------------
def sw2_selector():
    fig, ax = plt.subplots(figsize=(10.5, 5.2))
    ax.set_aspect("equal")

    for fp, col in ((SW2, "#3a7ca5"), (R12, "#b0813a")):
        xs = [p["gx"] for p in fp["pads"]]
        ys = [p["gy"] for p in fp["pads"]]
        bw, bh = (max(xs) - min(xs)) + 1.1, (max(ys) - min(ys)) + 1.1
        ax.add_patch(Rectangle((fp["x"] - bw / 2, fp["y"] - bh / 2), bw, bh,
                               facecolor="none", edgecolor=col, lw=1.4, zorder=1))
        label = fp["ref"] if fp is SW2 else f'{fp["ref"]} ({fp["value"]})'
        ax.text(fp["x"], fp["y"] + bh / 2 + 0.35, label, ha="center", va="top",
                fontsize=11, fontweight="bold", color=col)
        for p in fp["pads"]:
            ax.add_patch(Rectangle((p["gx"] - p["w"] / 2, p["gy"] - p["h"] / 2), p["w"], p["h"],
                                   facecolor=col, edgecolor="black", lw=0.5, alpha=0.85, zorder=2))
            # rotated so 0.9 mm-pitch neighbours cannot collide
            ax.annotate(f'{p["name"]}: {p["net"]}', (p["gx"], p["gy"] - p["h"] / 2 - 0.25),
                        ha="left", va="bottom", fontsize=9.5, fontweight="bold",
                        rotation=40, rotation_mode="anchor")

    p1, p2, p3 = (pad(SW2, n) for n in ("1", "2", "3"))
    for pa, pb, txt, dy in (
        (p1, p2, f"bridge = ON   ({ANODE_NET} → {ON_NET}, full rail)", 1.15),
        (p2, p3, f"bridge = TINY   ({ANODE_NET} → {TINY_NET} → R12 {R12['value']} → {ON_NET})", 2.15),
    ):
        mx = (pa["gx"] + pb["gx"]) / 2
        ax.annotate("", (pa["gx"], pa["gy"] + 0.55), (pb["gx"], pb["gy"] + 0.55),
                    arrowprops=dict(arrowstyle="-", color="black", lw=2.4,
                                    connectionstyle="arc3,rad=-0.55"))
        ax.annotate(txt, (mx, SW2["y"] + dy), ha="center", va="top", fontsize=10.5)

    rt = next(p for p in R12["pads"] if p["net"] == TINY_NET)
    ax.plot([p3["gx"], rt["gx"]], [p3["gy"], rt["gy"]], ls=":", color="#3a7ca5", lw=1.4, zorder=0)

    ax.set_title(f"{STEM}  —  SW2 LED master selector  ({SIDE_NOTE})", fontsize=12)
    ax.set_xlabel("board x (mm)")
    ax.set_ylabel("board y (mm)")
    ax.text(0.5, -0.24,
            f"unbridged = OFF — a true hardware off, supercap-safe for storage; "
            f"firmware cannot sense SW2 (board dark? check SW2 first)",
            transform=ax.transAxes, ha="center", va="top", fontsize=10)
    x0 = min(p["gx"] for p in SW2["pads"] + R12["pads"]) - 2.2
    x1 = max(p["gx"] for p in SW2["pads"] + R12["pads"]) + 2.2
    ax.set_xlim(x0, x1)
    ax.set_ylim(SW2["y"] + 3.4, SW2["y"] - 3.4)  # inverted: KiCad +y is down the board
    ax.grid(True, lw=0.3, alpha=0.5)
    _save(fig, f"{STEM}-sw2-selector.png")


if __name__ == "__main__":
    led_orientation()
    sw2_selector()
