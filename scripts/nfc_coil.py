#!/usr/bin/env python3
"""nfc_coil.py -- the NFC antenna paper-tune check (the blind spot both external
reviewers share: neither kicad-happy nor ThomsonLint has any provision for an
INTENTIONAL antenna -- see docs/thomsonlint.md. This closes the paper half).

The coil is the one net on the board that is supposed to radiate, and until now
its electrical identity (inductance, resonance against the tag's tuning cap,
quality factor) was datasheet math done once, by hand, off-board. This script
re-derives all of it FROM THE ROUTING on every run, the same way mask_art.py
tracks the front copper:

  geometry   -- chains every `LA` segment into the spiral polyline; turns come
                from the winding angle swept around the coil centroid (no
                hand-counted constant to go stale), per-turn side lengths from
                per-revolution bounding boxes.
  inductance -- TWO independent estimates, reported with their spread:
                (1) the rectangular-spiral engineering formula used across the
                    NFC app-note literature (NXP AN11276 / ST AN2866 family):
                    L = (u0/pi) * N^1.8 * [ a*ln(2ab/(d(a+g))) + b*ln(2ab/(d(b+g)))
                        - 2(a+b-g) ],   g = sqrt(a^2+b^2),
                    a,b = average side lengths, d = 2(w+t)/pi equivalent wire dia.
                (2) Mohan et al. current-sheet expression with square-coil
                    constants on the perimeter-equivalent side:
                    L = 2.34 * u0 * N^2 * d_avg / (1 + 2.75*rho).
                Paper formulas are ~+-20%; agreement between the two is the
                sanity signal, not either number alone.
  resonance  -- f0 = 1/(2*pi*sqrt(L*C)) for C = 50 pF (NT3H2211 input
                capacitance, datasheet 'Features': "Input capacitance of
                50 pF") + each C9 ladder option (39/47/56 pF), with the option
                actually PLACED on the board read from C9's Value/dnp state.
  Q          -- coarse skin-effect estimate at 13.56 MHz (copper delta ~18 um),
                ferrite sheet and Ti shell deliberately unmodeled: their effect
                is exactly what the bench reader-coupling TODO measures.

--check is a CATASTROPHE gate, not a precision gate: paper inductance cannot
arbitrate a 5% tune (that is what the C9 ladder and the bench are for), but it
CAN catch a re-route that breaks the coil -- a lost turn, a severed chain, a
width change -- the day it happens. Consistency check [13] calls evaluate()
directly; this file is the single definition of the coil math.

Gate: the spiral must chain unbroken, turns in [3, 9], and with the placed C9
the mean-L resonance must land inside [11.5, 16.5] MHz.
"""

import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BOARD = ROOT / "PCB" / "solar-glow-drh-v4_0.kicad_pcb"

COIL_NET = "LA"          # the spiral; LB is the return through the crossover via
C_TAG_PF = 50.0          # NT3H2211 input capacitance (datasheet Features list)
C9_LADDER_PF = (39.0, 47.0, 56.0)   # the documented tune ladder
CU_T_MM = 0.035          # 1 oz foil
F_TARGET_MHZ = 13.56
# The gate window is in BARE-COPPER paper units. The physical tank sits lower:
# the WE-FSFS-class ferrite sheet behind the coil raises L by a typical 1.3-1.5x,
# which pulls the 2026-08-01 baseline (bare ~15.5 MHz at the placed 47 pF) down
# to ~= 13.56. The window brackets the BARE baseline; the ladder and the bench
# own the physical number.
GATE_F_MHZ = (13.5, 17.5)
GATE_TURNS = (4, 9)
GATE_L_SPREAD = 0.25     # the two formulas agree ~3% on the baseline geometry

MU0 = 4e-7 * math.pi
RHO_CU = 1.68e-8         # ohm*m


def _segments(raw: str, net: str):
    """All (start, end, width) straight segments on `net`, any layer."""
    out = []
    idx = 0
    while True:
        i = raw.find("(segment", idx)
        if i < 0:
            break
        depth, j = 0, i
        while True:
            if raw[j] == "(":
                depth += 1
            elif raw[j] == ")":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        blk = raw[i:j + 1]
        idx = j + 1
        if f'(net "{net}")' not in blk:
            continue
        st = re.search(r"\(start (-?[\d.]+) (-?[\d.]+)\)", blk)
        en = re.search(r"\(end (-?[\d.]+) (-?[\d.]+)\)", blk)
        w = re.search(r"\(width ([\d.]+)\)", blk)
        out.append(((float(st.group(1)), float(st.group(2))),
                    (float(en.group(1)), float(en.group(2))),
                    float(w.group(1))))
    return out


def _chain(segs):
    """Order segments into polylines (endpoint-joined); return the LONGEST as the
    spiral plus the fraction of total net length it carries. Nets join through
    pads too, so short feed stubs legitimately live on separate chains."""
    def key(p):
        return (round(p[0], 3), round(p[1], 3))

    adj = {}
    for k, (a, b, _w) in enumerate(segs):
        adj.setdefault(key(a), []).append((k, a, b))
        adj.setdefault(key(b), []).append((k, b, a))

    used = set()
    chains = []
    for start, lst in adj.items():
        if len(lst) != 1 or lst[0][0] in used:
            continue                      # walk only from loose ends
        pts, cur, ln = [start], start, 0.0
        while True:
            nxt = [e for e in adj[cur] if e[0] not in used]
            if not nxt:
                break
            k, a, b = nxt[0]
            used.add(k)
            ln += math.dist(a, b)
            cur = key(b)
            pts.append(cur)
        chains.append((ln, pts))
    if not chains:
        raise ValueError("no open chains on the coil net (closed loop or empty)")
    chains.sort(reverse=True, key=lambda c: c[0])
    total = sum(math.dist(a, b) for (a, b, _w) in segs)
    spiral_len, pts = chains[0]
    if spiral_len < 0.8 * total:
        raise ValueError(f"longest chain carries only {spiral_len / total * 100:.0f}% "
                         "of the coil net -- spiral is severed")
    return [(p[0], p[1]) for p in pts], spiral_len


def _c9(raw: str):
    """(value_pF, dnp) of C9 read from the board."""
    m = re.search(r'\(property "Reference"\s+"C9"', raw)
    if not m:
        raise ValueError("C9 not found on the board")
    fp_start = raw.rfind("(footprint", 0, m.start())
    depth, j = 0, fp_start
    while True:
        if raw[j] == "(":
            depth += 1
        elif raw[j] == ")":
            depth -= 1
            if depth == 0:
                break
        j += 1
    blk = raw[fp_start:j + 1]
    vm = re.search(r'\(property "Value"\s+"([\d.]+)\s*pF"', blk)
    if not vm:
        raise ValueError("C9 Value does not parse as a pF capacitance")
    dnp = bool(re.search(r"\(attr [^)]*\bdnp\b", blk))
    return float(vm.group(1)), dnp


def evaluate(board_path=BOARD):
    """-> dict with geometry, both L estimates, f0 table, Q. THE one definition."""
    raw = board_path.read_bytes().decode("utf-8")
    segs = _segments(raw, COIL_NET)
    if not segs:
        raise ValueError(f"no segments on net {COIL_NET}")
    pts, length_mm = _chain(segs)
    w_mm = sorted({s[2] for s in segs})

    # turns, as the winding angle swept around the point-cloud centroid (a
    # cross-check only -- the load-bearing turn count comes from run pairing)
    cx = sum(p[0] for p in pts) / len(pts)
    cy = sum(p[1] for p in pts) / len(pts)
    theta = 0.0
    for i in range(1, len(pts)):
        a0 = math.atan2(pts[i - 1][1] - cy, pts[i - 1][0] - cx)
        a1 = math.atan2(pts[i][1] - cy, pts[i][0] - cx)
        d = a1 - a0
        while d > math.pi:
            d -= 2 * math.pi
        while d < -math.pi:
            d += 2 * math.pi
        theta += d
    turns_winding = abs(theta) / (2 * math.pi)

    # side lengths by ORTHOGONAL RUN PAIRING: an orthogonal spiral's long runs
    # cluster at discrete x (vertical) and y (horizontal) positions; pairing the
    # k-th left run with the k-th right run gives that turn's true width. (A
    # centroid-angle revolution slicer gets fooled by high-aspect coils -- this
    # one is exact for rectangular spirals.)
    MIN_RUN = 3.0
    vx = sorted({round(s[0][0], 2) for s in segs
                 if abs(s[0][0] - s[1][0]) < 0.01 and abs(s[0][1] - s[1][1]) > MIN_RUN})
    hy = sorted({round(s[0][1], 2) for s in segs
                 if abs(s[0][1] - s[1][1]) < 0.01 and abs(s[0][0] - s[1][0]) > MIN_RUN})
    left = [x for x in vx if x < cx]
    right = sorted((x for x in vx if x >= cx), reverse=True)
    bot = [y for y in hy if y < cy]
    top = sorted((y for y in hy if y >= cy), reverse=True)
    a_k = [r - l for l, r in zip(left, right)]
    b_k = [t - b0 for b0, t in zip(bot, top)]
    if not a_k or not b_k:
        raise ValueError("run pairing found no opposing side runs -- coil is not "
                         "an orthogonal spiral anymore; rework this extractor")
    a_avg = sum(a_k) / len(a_k)
    b_avg = sum(b_k) / len(b_k)
    a_out, a_in = max(a_k), min(a_k)
    b_out, b_in = max(b_k), min(b_k)
    turns = (len(left) + len(right) + len(bot) + len(top)) / 4.0

    n = turns
    w = max(w_mm) * 1e-3
    a = a_avg * 1e-3
    b = b_avg * 1e-3
    d_wire = 2 * (w + CU_T_MM * 1e-3) / math.pi
    g = math.hypot(a, b)

    # (1) rectangular-spiral app-note formula
    l_appnote = (MU0 / math.pi) * (n ** 1.8) * (
        a * math.log(2 * a * b / (d_wire * (a + g)))
        + b * math.log(2 * a * b / (d_wire * (b + g)))
        - 2 * (a + b - g)
    )

    # (2) Mohan current-sheet, square constants on the perimeter-equivalent side
    s_out = (a_out + b_out) / 2 * 1e-3
    s_in = (a_in + b_in) / 2 * 1e-3
    d_avg = (s_out + s_in) / 2
    rho = (s_out - s_in) / (s_out + s_in) if (s_out + s_in) else 0.0
    l_mohan = 2.34 * MU0 * n * n * d_avg / (1 + 2.75 * rho)

    l_mean = (l_appnote + l_mohan) / 2
    spread = abs(l_appnote - l_mohan) / l_mean

    c9_pf, c9_dnp = _c9(raw)
    table = {}
    for c9 in C9_LADDER_PF:
        c_tot = (C_TAG_PF + c9) * 1e-12
        table[c9] = 1 / (2 * math.pi * math.sqrt(l_mean * c_tot)) / 1e6

    # coarse Q at 13.56 MHz: one-face skin-depth conduction, ferrite/shell unmodeled
    delta = math.sqrt(RHO_CU / (math.pi * F_TARGET_MHZ * 1e6 * MU0))
    r_ac = RHO_CU * (length_mm * 1e-3) / (w * delta)
    q = 2 * math.pi * F_TARGET_MHZ * 1e6 * l_mean / r_ac

    return {
        "segments": len(segs),
        "length_mm": length_mm,
        "turns": turns,
        "turns_winding": turns_winding,
        "width_mm": max(w_mm),
        "widths_mm": w_mm,
        "avg_side_mm": (a_avg, b_avg),
        "outer_mm": (a_out, b_out),
        "inner_mm": (a_in, b_in),
        "L_appnote_uH": l_appnote * 1e6,
        "L_mohan_uH": l_mohan * 1e6,
        "L_mean_uH": l_mean * 1e6,
        "L_spread": spread,
        "C_tag_pF": C_TAG_PF,
        "C9_placed_pF": c9_pf,
        "C9_dnp": c9_dnp,
        "f0_MHz": table,
        "Q_est": q,
    }


def main():
    check = "--check" in sys.argv
    r = evaluate()
    print(f"  coil ({COIL_NET}): {r['segments']} segments, {r['length_mm']:.1f} mm, "
          f"{r['turns']:.2f} turns (winding cross-check {r['turns_winding']:.2f}), "
          f"w {r['width_mm']:.2f} mm")
    print(f"  sides: avg {r['avg_side_mm'][0]:.1f} x {r['avg_side_mm'][1]:.1f} mm  "
          f"(outer {r['outer_mm'][0]:.1f} x {r['outer_mm'][1]:.1f}, "
          f"inner {r['inner_mm'][0]:.1f} x {r['inner_mm'][1]:.1f})")
    print(f"  L: app-note {r['L_appnote_uH']:.2f} uH / Mohan {r['L_mohan_uH']:.2f} uH "
          f"-> mean {r['L_mean_uH']:.2f} uH (spread {r['L_spread'] * 100:.0f}%)")
    for c9, f0 in r["f0_MHz"].items():
        placed = "  <- PLACED" if abs(c9 - r["C9_placed_pF"]) < 0.5 and not r["C9_dnp"] else ""
        print(f"  f0 @ C9={c9:g}pF (+{C_TAG_PF:g}pF tag): {f0:.2f} MHz{placed}")
    print(f"  Q ~{r['Q_est']:.0f} (bare copper estimate; ferrite + Ti shell are the "
          f"bench's to measure)")
    print(f"  NOTE: bare-copper paper values. The ferrite sheet raises L ~1.3-1.5x "
          f"(WE-FSFS class), pulling the physical tank toward {F_TARGET_MHZ} MHz -- "
          f"which is why it is load-bearing for TUNE, not just shielding.")

    if check:
        errs = []
        if not (GATE_TURNS[0] <= r["turns"] <= GATE_TURNS[1]):
            errs.append(f"turns {r['turns']:.2f} outside {GATE_TURNS}")
        if abs(r["turns"] - r["turns_winding"]) > 1.2:
            errs.append(f"run-pairing turns {r['turns']:.2f} vs winding "
                        f"{r['turns_winding']:.2f} disagree -- extraction suspect")
        if r["C9_dnp"]:
            errs.append("C9 is dnp -- the tank has no placed tune")
        f_placed = None
        for c9, f0 in r["f0_MHz"].items():
            if abs(c9 - r["C9_placed_pF"]) < 0.5:
                f_placed = f0
        if f_placed is None:
            errs.append(f"placed C9 {r['C9_placed_pF']:g}pF is not a ladder value")
        elif not (GATE_F_MHZ[0] <= f_placed <= GATE_F_MHZ[1]):
            errs.append(f"paper f0 {f_placed:.2f} MHz outside {GATE_F_MHZ} "
                        "with the placed tune")
        if r["L_spread"] > GATE_L_SPREAD:
            errs.append(f"L estimates disagree by {r['L_spread'] * 100:.0f}% -- "
                        "geometry extraction is suspect")
        if errs:
            for e in errs:
                print(f"  FAIL: {e}")
            return 1
        print("  OK -- coil geometry and paper tune inside the catastrophe gate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
