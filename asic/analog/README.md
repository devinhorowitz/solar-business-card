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

| rail | STO | I min | I typ | I max | ballast @ I max | vs the 30 mA spec point |
|---|---|---|---|---|---|---|
| glow floor | 2.75 V | 0.00 mA | 0.67 mA | 3.16 mA | 1.4 mW (2 %) | 0.11× — **not usable** |
| VOVCH (full tank) | 4.65 V | 10.79 mA | 13.33 mA | 16.49 mA | 38.8 mW (62 %) | 0.55× — shaky |
| abuse corner | 5.50 V | 16.19 mA | 19.00 mA | **22.46 mA** | 71.9 mW (**115 %**) | 0.75× — usable |

> **Model validity — read before quoting a row.** The loop equation treats Vf as a
> constant, but the only Vf data this repo has is **1.95–2.55 V *at 30 mA***, and a
> diode's forward voltage falls with current. Each row is therefore only as good as its
> distance from that spec point, which is why the last column exists. The glow-floor row
> is **not a prediction** — see F2.



`I typ` at VOVCH is 13.33 mA, which is where SPEC's "16 mA" comes from — that is the
*max*-corner figure at the full tank, not a typical.

## Three findings the envelope forces out

**[F1] The ballast guard was ~1.4 % short at RN1's tolerance corner — now fixed.**
`board.h` sized the clamp on the *nominal* 150 Ω: 68.3 mW × 225/255 = 60.2 mW, under the
62.5 mW element rating. But RN1 is ±5 %, and −5 % is the current-worst corner: 71.9 mW ×
225/255 = **63.4 mW, 1.4 % over**. `GLOW_CLAMP_PEAK` and `gamma_pwm`'s `CLAMP_PEAK` are
now **221**, the largest peak that holds there — 62.3 mW, **99.6 %** of the element rating,
with the package at 249.1 mW of 250 mW.

One caveat on F1's own basis, since the same Vf trap is nearby: it is computed with
`VF_GUARD` = 1.90 V, which is *below* the 1.95 V datasheet floor **at 30 mA**. Since Vf
falls with current, 1.90 V is plausibly about right for a min-bin part at 22 mA — so the
margin is likely intact, but by two errors cancelling rather than by derivation. Do not
"correct" 1.90 to 1.95 without the I-V curve: that would lower the computed current and
make the clamp look safer than it is.

That margin is thin on purpose rather than by accident, and it is now **gated** rather than
trusted: `sink_budget.py` reads `GLOW_CLAMP_PEAK` out of `firmware/board.h` and `CLAMP_PEAK`
out of `asic/rtl/gamma_pwm.v` — it does not carry a third copy — and `--check` fails if the
two disagree, or if either stops satisfying the inequality. That guard earns its keep
because `PCB/README.md` flags R1–R4's 150 Ω as **SIZED, not locked** and bench-pending: a
re-tune moves the corner under the constant, and now it cannot move silently.

**[F2] The low-rail end of this table is not a prediction — and was briefly published as
one.** An earlier version of this file reported *"a worst-bin LED cannot light at the glow
floor"* as a finding. **That was wrong.** It applied the 2.55 V figure — specified at
**30 mA** — to an operating point of **0.67 mA**, where a real LED's Vf is materially
lower and the part does conduct. The arithmetic was right and the premise was not.

What is true is narrower and still worth knowing: **the low-rail glow behaviour is
unmodelled here.** At 2.75 V a max-Vf part has only 200 mV for ballast *and* sink using
the 30 mA number, so the margin is genuinely thin — but how thin cannot be settled by more
arithmetic. It needs the LED's I-V curve or a bench sweep. Recorded rather than deleted
because the mistake is easy to make again from this same table.

**[F3] A stronger sink is worse, not better.** `Vsink` sits in series with the LED, so
lowering it *raises* loop current and the ballast dissipates I²R. Dropping 0.50 → 0.05 V
takes current 21.8 → 24.9 mA and the ballast 67 → 88 mW — **108 % → 142 %** of rating.
`R_on` therefore has a **floor as well as a ceiling** while the 150 Ω ballast stands.
This is the opposite of the usual "minimise R_on" instinct and is the single most
important constraint on this cell.

F3 wants a large sink drop; the thin low-rail headroom F2 points at wants a small one,
across a rail spanning 2.75–5.5 V. That tension is the cell's real design problem — though
its low-rail half is only bounded once the I-V curve exists.

## The specification

| parameter | value | why |
|---|---|---|
| I_max, DC, worst corner | **22.46 mA** | STO 5.5 V, Vf 1.90 V, R −5 %, Vsink 0.4 V |
| R_on ceiling | **17.8 Ω** | 0.4 V at I_max, matching the VOL the board was sized against |
| R_on floor | set by F3 | below ~0.4 V drop the ballast exceeds rating faster than the clamp recovers |
| drain standoff, LED off | ≥ 5.50 V | drain floats near STO when dark → **a 5 V-class device**, not a 1.8/3.3 V one |
| die dissipation, 4 ch | **35.9 mW** (31.1 mW clamped) | 4 × 0.4 V × I_max; on-die, unlike RN1's share |
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
picture, and it needs Vdsat headroom at the low rail where there is least of it. Worth
revisiting only with bench data on the energy budget.

## What still needs the PDK

None of the following is answerable here, and none should be guessed:

- W/L for the output device meeting the R_on window at 5 V-class Vds, over PVT
- the actual leakage at 5.5 V / 85 °C against the 1 nA/ch budget
- matching analysis across four instances, and the layout that achieves it
- ESD and abs-max on a pin that floats to STO
- thermal: 35.9 mW across four cells on a die also carrying the digital core

Re-derive the numbers above with `python3 asic/analog/sink_budget.py`.
