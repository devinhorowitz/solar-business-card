# DRH-1 — the LED sink cells

**What this is.** The specification the four on-die LED sink cells must meet, and the
operating envelope that forces it. Every number here is computed by
`asic/analog/sink_budget.py` from constants this repo already owns — the LED's binning, RN1's
value and tolerance, the AEM's rail limits, the firmware's glow gate — rather than
asserted. Run it to regenerate; `--check` gates this file against it.

**What this is NOT.** A sized transistor. That needs the GF180MCU PDK, Xschem and
ngspice, none of which are in this container, and `asic/README.md` is right that the
analog half is the project's real risk. Nothing here has been simulated. What is
pinned is the box the analog designer has to fit inside — which was previously
unwritten, so "16 mA sink cells" in `SPEC.md` was a target with no corners attached.

## Operating envelope

Series loop: `STO → LED → RN1 → sink`. Current is `(STO − Vf − Vsink) / R`, so the worst
corner for current is **min Vf, min R, min sink drop** — and each figure below is solved
on its own corner rather than at one convenient typical.

| rail | STO | I min | I typ | I max | ballast @ I max |
|---|---|---|---|---|---|
| glow floor | 2.75 V | **0.00 mA** | 0.67 mA | 3.16 mA | 1.4 mW (2 %) |
| VOVCH (full tank) | 4.65 V | 10.79 mA | 13.33 mA | 16.49 mA | 38.8 mW (62 %) |
| abuse corner | 5.50 V | 16.19 mA | 19.00 mA | **22.46 mA** | 71.9 mW (**115 %**) |

`I typ` at VOVCH is 13.33 mA, which is where SPEC's "16 mA" comes from — that is the
*max*-corner figure at the full tank, not a typical.

## Three findings the envelope forces out

**[F1] The ballast guard is ~1.4 % short at RN1's tolerance corner.** `board.h` sizes the
clamp on the *nominal* 150 Ω: 68.3 mW × 225/255 = 60.2 mW, under the 62.5 mW element
rating. RN1 is ±5 %, and the −5 % corner is the current-worst one: 71.9 mW × 225/255 =
**63.4 mW, 1.4 % over rating**. The largest `GLOW_CLAMP_PEAK` that still holds there is
**221**. This is a card finding, not an ASIC one — `GLOW_CLAMP_PEAK` lives in `board.h`
and `gamma_pwm`'s `CLAMP_PEAK` mirrors it. **Not changed here**: it is a firmware
constant on a board about to be ordered, and the call is the user's.

**[F2] A worst-bin LED cannot light at the glow floor at all.** Vf is unbinned across
3B–5A at **1.95–2.55 V**. The glow gate opens at 2.75 V, leaving 200 mV for ballast *and*
sink — and a 0.4 V sink alone needs twice that. A max-Vf part is simply dark there. Any
sink drop above 200 mV makes the bottom of the glow range unreachable for part of the
bin distribution.

**[F3] A stronger sink is worse, not better.** `Vsink` sits in series with the LED, so
lowering it *raises* loop current and the ballast dissipates I²R. Dropping 0.50 → 0.05 V
takes current 21.8 → 24.9 mA and the ballast 67 → 88 mW — **108 % → 142 %** of rating.
`R_on` therefore has a **floor as well as a ceiling** while the 150 Ω ballast stands.
This is the opposite of the usual "minimise R_on" instinct and is the single most
important constraint on this cell.

F2 and F3 pull in opposite directions — F2 wants a small drop, F3 wants a large one —
across a rail range spanning 2.75–5.5 V. That tension is the cell's real design problem.

## The specification

| parameter | value | why |
|---|---|---|
| I_max, DC, worst corner | **22.46 mA** | STO 5.5 V, Vf 1.90 V, R −5 %, Vsink 0.4 V |
| R_on ceiling | **17.8 Ω** | 0.4 V at I_max, matching the VOL the board was sized against |
| R_on floor | set by F3 | below ~0.4 V drop the ballast exceeds rating faster than the clamp recovers |
| drain standoff, LED off | ≥ 5.50 V | drain floats near STO when dark → **a 5 V-class device**, not a 1.8/3.3 V one |
| die dissipation, 4 ch | **35.9 mW** (31.7 mW clamped) | 4 × 0.4 V × I_max; on-die, unlike RN1's share |
| off-state leakage | ≤ 1 nA/ch at 5.5 V, 85 °C | the AEM's own dark IQ is 6 nA — four leaky sinks must not dominate the standby ledger |
| matching, 4 ch | tighter than the LED bin spread | brightness uniformity is visible; Vf already varies 1.95–2.55 V |

## Switch or current source

Specified above as a **switch**, mirroring the card, and that is the right call for first
silicon for three reasons. The duty-clamp guard already exists in `gamma_pwm`, so the
abuse corner is covered. The dissipation stays mostly in RN1, off-die. And rail-dependent
brightness is a *feature* here — `USE_BROWNOUT_STRETCH` deliberately dims as the tank
sags, and a current source would fight it.

A **current-source** sink (mirror in saturation) is the upgrade path: it removes the
abuse corner at its root, since I stops depending on STO, and it fixes F3. It does not
save energy — the drop moves from RN1 to the die, same I·V — so it *worsens* the thermal
picture, and it needs Vdsat headroom exactly where F2 says there is none. Worth revisiting
only with bench data on the energy budget.

## What still needs the PDK

None of the following is answerable here, and none should be guessed:

- W/L for the output device meeting the R_on window at 5 V-class Vds, over PVT
- the actual leakage at 5.5 V / 85 °C against the 1 nA/ch budget
- matching analysis across four instances, and the layout that achieves it
- ESD and abs-max on a pin that floats to STO
- thermal: 35.9 mW across four cells on a die also carrying the digital core

Re-derive the numbers above with `python3 asic/analog/sink_budget.py`.
