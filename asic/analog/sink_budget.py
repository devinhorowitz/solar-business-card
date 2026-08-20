#!/usr/bin/env python3
"""
sink_budget.py -- the DRH-1 LED sink cell's operating envelope, derived from the CARD.

SPEC.md says "four 16 mA sink cells" and asic/README.md lists them among the analog
stubs the experiment does not claim. Sizing a transistor needs the GF180 PDK and
ngspice, and neither is here. What CAN be pinned without them is the SPECIFICATION
those cells must meet -- and it is entirely a function of numbers this repo already
owns, so it is computed here rather than asserted in prose.

EVERY INPUT IS SOURCED. No typical-case hand-waving: the worst corner for one figure
is not the worst corner for another, so each is solved separately over the box.

    LED   LA P47F-V2BB-24-3B5A-30-R18-Z, Vf 1.95-2.55 V at 30 mA, UNBINNED across the
          3B-5A groups                                   (PCB/README.md, D2-D5 row + the
          R1-R4 sizing flag). board.h's ballast-guard corner uses 1.9 V, slightly below
          the datasheet floor -- kept as the conservative bound, see VF_GUARD.
    RN1   4 x 150 ohm +/-5% isolated array, EXB-28V151JX, 62.5 mW PER ELEMENT
                                                          (PCB/README.md RN1 row, board.h)
    STO   0.20-4.65 V normal (AEM10300 STO_CFG = LLHH straps VOVDIS/VCHRDY/VOVCH),
          5.5 V only from a bench supply -- the abuse corner the ballast guard exists for
                                            (solar-glow-drh-design-notes.md, board.h)
    gate  glow inhibited below VS_GLOW_FLOOR_MV = 2750    (board.h)
    duty  gamma_pwm clamps peak duty to CLAMP_PEAK/255 while sense_seq.vclamp is high

MODEL VALIDITY -- read this before quoting a row. The loop equation treats Vf as a
CONSTANT, but the only Vf data this repo has is 1.95-2.55 V *at 30 mA*, and a diode's
forward voltage falls with current. So each row is only as good as its distance from
that spec point, and the table prints the ratio so you cannot forget:

    abuse corner   22 mA  0.75x spec   usable
    VOVCH          16 mA  0.55x spec   shaky
    glow floor      3 mA  0.11x spec   NOT USABLE -- a real LED conducts here; this
                                       model says it does not, and the model is wrong

That last row is why this note exists. On 2026-08-19 an earlier version of this file
reported "the worst-bin LED cannot light at the glow floor" as a FINDING. It is not a
finding, it is an artifact of applying a 30 mA number at 0.67 mA. Closing the low-rail
end needs the LED's I-V curve or a bench sweep, not more arithmetic.
"""
import argparse, sys

# ---- sourced inputs ---------------------------------------------------------------
VF_MIN, VF_MAX = 1.95, 2.55      # PCB/README.md: unbinned 3B-5A at 30 mA
VF_SPEC_A      = 0.030           # ...AT 30 mA, and that qualifier is load-bearing --
                                 # see MODEL VALIDITY in the module docstring
VF_TYP         = 2.25            # PCB/README.md D2-D5 row
VF_GUARD       = 1.90            # board.h's ballast-guard corner (below the DS floor)
R_NOM, R_TOL   = 150.0, 0.05     # RN1 EXB-28V151JX, +/-5%
P_ELEM         = 0.0625          # 62.5 mW per element
P_PKG          = 0.250           # Bourns CAY10 structural twin, 4x per-element
STO_FLOOR      = 2.750           # board.h VS_GLOW_FLOOR_MV
STO_VOVCH      = 4.650           # AEM10300 ceiling
STO_ABUSE      = 5.500           # supercap rating; bench-supply only

def _read_clamp_peaks():
    """READ the clamp out of both files rather than carry a third copy of it.

    The value lives twice by necessity -- board.h owns the card's, gamma_pwm.v mirrors
    it for the silicon -- and a third copy here would be the drift this repo keeps
    getting bitten by. So this parses both, and check_clamp() below fails if they ever
    disagree OR if either stops holding the thermal inequality. That guard is not
    decorative: PCB/README.md flags R1-R4's 150 ohm as SIZED, not locked, and
    bench-pending, so a re-tune moves the corner under this constant's feet."""
    import re, pathlib as _p
    root = _p.Path(__file__).resolve().parents[2]
    c = {}
    m = re.search(r'#define\s+GLOW_CLAMP_PEAK\s+(\d+)',
                  (root / "firmware/board.h").read_text())
    if not m: raise SystemExit("cannot find GLOW_CLAMP_PEAK in firmware/board.h")
    c["board.h"] = int(m.group(1))
    m = re.search(r"parameter\s*\[7:0\]\s*CLAMP_PEAK\s*=\s*8'd(\d+)",
                  (root / "asic/rtl/gamma_pwm.v").read_text())
    if not m: raise SystemExit("cannot find CLAMP_PEAK in asic/rtl/gamma_pwm.v")
    c["gamma_pwm.v"] = int(m.group(1))
    return c

CLAMP_SRC      = _read_clamp_peaks()
CLAMP_PEAK     = CLAMP_SRC["board.h"]
AEM_DARK_A     = 6e-9            # AEM10300 IQ on STO (DS Table 5)

R_LO, R_HI = R_NOM * (1 - R_TOL), R_NOM * (1 + R_TOL)

def current(sto, vf, r, vsink):
    """Series loop: STO -> LED -> ballast -> sink. Card topology, switch-mode sink."""
    return max(0.0, (sto - vf - vsink) / r)

def rows():
    """Worst-case current is min Vf, min R, min sink drop -- each solved on its own."""
    out = []
    for label, sto in (("glow floor", STO_FLOOR), ("VOVCH (full)", STO_VOVCH),
                       ("abuse corner", STO_ABUSE)):
        i_max = current(sto, VF_GUARD, R_LO, 0.4)
        i_typ = current(sto, VF_TYP,   R_NOM, 0.4)
        i_min = current(sto, VF_MAX,   R_HI, 0.4)
        out.append((label, sto, i_min, i_typ, i_max, i_max**2 * R_LO, i_max / VF_SPEC_A))
    return out

def vsink_sweep():
    """THE COUNTERINTUITIVE ONE: a STRONGER sink burns MORE ballast, not less.
    Vsink is in series with the LED, so lowering it raises loop current, and the
    ballast dissipates I^2R. A 'better' switch pushes RN1 further past its rating."""
    return [(v, current(STO_ABUSE, VF_GUARD, R_LO, v),
             current(STO_ABUSE, VF_GUARD, R_LO, v)**2 * R_LO) for v in
            (0.05, 0.10, 0.20, 0.30, 0.40, 0.50)]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="verify README.md's tables against this computation")
    a = ap.parse_args()

    print("== operating envelope (Vsink = 0.4 V, the AVR's VOL the board was sized against)")
    print(f"{'rail':<14}{'STO':>7}{'I min':>9}{'I typ':>9}{'I max':>9}{'ballast @Imax':>15}"
          f"{'vs 30mA spec':>15}")
    for lbl, sto, imin, ityp, imax, p, ratio in rows():
        trust = "usable" if ratio > 0.6 else ("shaky" if ratio > 0.25 else "NOT USABLE")
        print(f"{lbl:<14}{sto:>6.2f}V{imin*1e3:>8.2f}m{ityp*1e3:>8.2f}m{imax*1e3:>8.2f}m"
              f"{p*1e3:>11.1f}mW {p/P_ELEM*100:>5.0f}%{ratio:>9.2f}x {trust}")

    print("\n== sink compliance sweep at the abuse corner (why Vsink has a FLOOR, not just a ceiling)")
    print(f"{'Vsink':>7}{'I':>10}{'ballast':>11}{'of rating':>11}")
    for v, i, p in vsink_sweep():
        print(f"{v:>6.2f}V{i*1e3:>9.2f}m{p*1e3:>9.1f}mW{p/P_ELEM*100:>10.0f}%")

    i_abuse = current(STO_ABUSE, VF_GUARD, R_LO, 0.4)
    print(f"\n== derived sink-cell requirements")
    print(f"  I_max (DC, worst corner)      {i_abuse*1e3:.2f} mA")
    print(f"  R_on ceiling at 0.4 V         {0.4/i_abuse:.1f} ohm")
    print(f"  die dissipation, 4 ch @0.4 V  {4*0.4*i_abuse*1e3:.1f} mW  "
          f"({4*0.4*i_abuse*CLAMP_PEAK/255*1e3:.1f} mW with the duty clamp)")
    print(f"  drain standoff, LED off       >= {STO_ABUSE:.2f} V  -> a 5 V-class device")
    print(f"  off-state leakage, 4 ch       << {AEM_DARK_A*1e9:.0f} nA (AEM dark IQ) "
          f"-> budget 1 nA/ch at 5.5 V, 85 C")
    print(f"  ballast @Imax, package        {4*i_abuse**2*R_LO*1e3:.1f} mW vs {P_PKG*1e3:.0f} mW")

    print(f"\n== findings the envelope forces out (each is a computed inequality, not an opinion)")

    # [F1] -- was a FINDING on 2026-08-19, is now a GATE. The clamp used to be 225,
    # sized on RN1's NOMINAL 150 ohm; at the -5% corner that averaged 1.4% OVER rating.
    p_nom = current(STO_ABUSE, VF_GUARD, R_NOM, 0.4) ** 2 * R_NOM
    p_tol = current(STO_ABUSE, VF_GUARD, R_LO,  0.4) ** 2 * R_LO
    need  = int(P_ELEM / p_tol * 255)          # largest peak that averages under rating
    ok    = p_tol * CLAMP_PEAK / 255 < P_ELEM
    print(f"  [F1] clamp holds at the RESISTOR TOLERANCE corner")
    for src, v in CLAMP_SRC.items():
        print(f"       {src:<14} CLAMP_PEAK = {v}")
    print(f"       nominal R: {p_nom*1e3:.1f} mW x {CLAMP_PEAK}/255 = "
          f"{p_nom*CLAMP_PEAK/255*1e3:.1f} mW")
    print(f"       R -5%:     {p_tol*1e3:.1f} mW x {CLAMP_PEAK}/255 = "
          f"{p_tol*CLAMP_PEAK/255*1e3:.1f} mW {'<' if ok else '>'} {P_ELEM*1e3:.1f} mW  "
          f"{'OK (' + format(p_tol*CLAMP_PEAK/255/P_ELEM*100, '.1f') + '% of rating)' if ok else 'OVER'}")
    print(f"       package:   {4*p_tol*CLAMP_PEAK/255*1e3:.1f} mW of {P_PKG*1e3:.0f} mW")
    print(f"       ceiling:   largest peak that holds here is {need}")

    # [F2] -- WAS reported as a finding on 2026-08-19 and was WRONG. Kept as a stated
    # limit of the model, because the mistake is easy to make again from this same table.
    hdr = STO_FLOOR - VF_MAX
    print(f"  [F2] the low-rail end of this table is NOT a prediction")
    print(f"       at {STO_FLOOR:.2f} V a MAX-Vf part leaves {hdr*1e3:.0f} mV for ballast + sink "
          f"USING THE 30 mA Vf")
    print(f"       -> the model says dark; a real LED does not, because Vf falls with current")
    print(f"       -> {rows()[0][6]:.2f}x the spec point: needs the I-V curve or a bench sweep")

    # [F3] the inversion
    i_lo = current(STO_ABUSE, VF_GUARD, R_LO, 0.05)
    i_hi = current(STO_ABUSE, VF_GUARD, R_LO, 0.50)
    print(f"  [F3] a STRONGER sink is WORSE for the ballast")
    print(f"       Vsink 0.50 -> 0.05 V raises I {i_hi*1e3:.1f} -> {i_lo*1e3:.1f} mA and "
          f"ballast {i_hi**2*R_LO*1e3:.0f} -> {i_lo**2*R_LO*1e3:.0f} mW "
          f"({i_hi**2*R_LO/P_ELEM*100:.0f}% -> {i_lo**2*R_LO/P_ELEM*100:.0f}% of rating)")
    print(f"       R_on therefore has a FLOOR as well as a ceiling, given the 150 ohm ballast")

    if a.check:
        import pathlib, re
        doc = pathlib.Path(__file__).with_name("README.md")
        if not doc.exists():
            print("::error::asic/analog/README.md missing"); return 1
        txt, bad = doc.read_text(), []
        want = {
            "I_max": f"{i_abuse*1e3:.2f} mA",
            "R_on ceiling": f"{0.4/i_abuse:.1f} Ω",
            "die dissipation": f"{4*0.4*i_abuse*1e3:.1f} mW",
        }
        for k, v in want.items():
            if v not in txt:
                bad.append(f"README.md does not carry the computed {k} = {v}")
        # the two copies of the clamp must agree, and must hold the inequality
        if len(set(CLAMP_SRC.values())) != 1:
            print("::error::the clamp constant disagrees between the card and the RTL: "
                  + ", ".join(f"{k}={v}" for k, v in CLAMP_SRC.items()))
            return 1
        if not (p_tol * CLAMP_PEAK / 255 < P_ELEM):
            print(f"::error::CLAMP_PEAK {CLAMP_PEAK} averages "
                  f"{p_tol*CLAMP_PEAK/255*1e3:.1f} mW at the RN1 -5% corner, over the "
                  f"{P_ELEM*1e3:.1f} mW element rating. Largest that holds: {need}.")
            return 1
        if bad:
            print("::error::asic/analog/README.md disagrees with sink_budget.py")
            print("\n".join("  " + b for b in bad)); return 1
        print("\ncheck: README.md carries every computed figure")
    return 0

sys.exit(main())
