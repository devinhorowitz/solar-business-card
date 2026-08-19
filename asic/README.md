# DRH-1 — the companion-ASIC experiment

**The question this directory answers** (asked 2026-08-12): *if the card's green-set silicon
— the absorb map from the custom-ASIC investigation — were taken all the way to a
wafer.space GF180MCU quarter slot, can the work be done directly, in this repo, by the
agent?*

**The answer: the digital half, yes — designed, simulated, adversarially reviewed, fixed,
and sized, in one session, with tools that install in the CI container (`apt-get install
iverilog yosys`). The analog half and everything after GDS, no — and the boundary is
sharp enough to write down.**

## What exists

| file | mirrors | what it is |
|---|---|---|
| `rtl/clkdiv.v` | main.c's PIT | 1 MHz → 128 Hz env + 1 Hz poll strobes |
| `rtl/gamma_pwm.v` | led.c | 4-ch 8-bit PWM, gamma-2, breathe/sweep/dim + the ballast duty ceiling |
| `rtl/i2c_master.v` | twi.h usage | byte-transaction master, open-drain SDA |
| `rtl/init_seq.v` | adxl367.c | ROM-driven ADXL367 config with one-retry policy |
| `rtl/sar_ctrl.v` | — | 8-bit SAR controller for the analog comparator/DAC pair |
| `rtl/sense_seq.v` | sense.c | **the deferred-read rule, in gates**: arm → settle → convert → gate off; vlow/vcrit/vclamp |
| `rtl/wake_fsm.v` | main.c | tap → glow → sweep; vcrit → dormant + brownout; NFC hold |
| `rtl/drh1_top.v` | — | the chip |
| `rtl/tt_um_drh_solarglow.v` | — | Tiny Tapeout wrapper (their fixed pin interface) |
| `tb/` | — | 6 self-checking benches + a reusable behavioural ADXL367 slave |

`make sim` runs everything (Icarus, `-g2012`); `make synth` / `make gates` write the two
Yosys stat reports (gitignored like every other build product — the numbers below are
quoted from a fresh run; re-derive them with `make gates` rather than trusting this file
if yosys moves).

## What was proven, not asserted

Every testbench is `$fatal`-armed with falsifiable predicates, and the build agents
**mutation-tested their own benches** (broken gamma, removed sweep offsets, suppressed
ack_err, one-clk LED leak — each mutation independently hits `$fatal`). Highlights:

- exact strobe rates and 1-cycle widths out of `clkdiv`; PWM duty monotone-with-gamma,
  4-phase sweep with led0/led2 provably antiphase
- I²C: exact SCL period on every edge, exact rise counts per frame type (29/39/11),
  wrong-address NACK → `ack_err`, clean recovery after
- init: 8 ROM writes in order to 0x1D, injected-NACK retry-once policy both ways
- **sense: the U10 property** — over a full 32-poll run, `sns_en` is high **0.47 %** of
  cycles (bound: 2 %); the divider is provably gated off between samples, and the force
  path now guarantees ≥ SETTLE_ENV_TICKS *full* settle periods (review finding 4)
- **the thresholds are pinned to volts** (2026-08-19). `TH_LOW`/`TH_CRIT` carried a
  "placeholder scaling" tag from the first commit; they are now specified in millivolts
  against `board.h` with the codes derived from one declared full scale, and the bench checks
  the boundaries in millivolts rather than in codes. Full scale is 6000 mV, deliberately
  **above** the AEM's 4.65 V VOVCH ceiling, because `GLOW_CLAMP_STO_MV` 5200 sits above it
  too — a converter saturating at VOVCH would make the ballast guard unreachable, silently,
  with every bench still passing. The bench now also asserts the thing `board.h` only says in
  a parenthetical: a full tank at VOVCH (code 198) never trips the guard (code 221)
- **ballast guard: the ceiling is measured, not asserted.** The unclamped breathe peak is
  taken first (252/256) so the ceiling check cannot pass vacuously; with the guard on, every
  channel of every animation caps at 225/256 *and reaches it*, and mode 00 stays dark.
  `sense_seq`'s thresholds are DISCOVERED by binary search rather than restated in the bench,
  then validated **in millivolts** — within one LSB of their `board.h` numbers, on the
  protective side — which is what catches a rounding rule that is wrong in the bench and the
  DUT at once. `vclamp`'s reset value is proven pessimistic. End to end in `tb_top`: same tap,
  two rails, 225/256 at the 5.5 V abuse corner against 252/256 at the AEM's VOVCH ceiling
- integration: behavioural ADXL367 verifies the init addressing; tap → 197 measured PWM
  edges per LED; mid-glow vcrit → **dark on the same clk edge `brownout` rises**
  (review finding 3 + the 5b scenario that fails without the fix); recovery glows again

An adversarial review pass confirmed 5 findings (2 critical — a hierarchical `sda_oe`
reference the wrapper leaned on, and the SDA tri-state's flow limits); all 5 fixed and
re-verified the same session. The refuted list (latches, reset gaps, unfailable TBs) is
in the workflow record.

## The number the quarter-slot question wanted

Yosys 0.33, `synth` then `abc -g NAND`, top `drh1_top`:

| | |
|---|---|
| cells (NAND-mapped) | **3,335** = 1,980 NAND2 + 1,104 NOT + 251 DFF |
| largest module | `gamma_pwm` (~58 % — the gamma × PWM datapath, now including the clamp) |
| area @ conservative 15–25 kgate/mm² | **0.13–0.25 mm²** |
| **fraction of a 4.9 mm² quarter slot** | **≈ 3–5 %** |

(Was 3,209 that morning. The ballast guard's duty ceiling cost **+100** and pinning the
thresholds to volts a further **+26** — the comparator constants moved and stopped being
powers of two — for **+126 cells, +3.9 %** total. Neither moves the area band or the slot
fraction at this rounding.)

The digital core is a rounding error against the slot. What actually sizes the chip is
the analog below — and even generous analog budgets leave the quarter slot mostly empty.

## What this experiment deliberately does NOT claim

- **The analog cells are stubs**: RC oscillator, bandgap, comparator + R-2R DAC (the SAR's
  other half), four 16 mA LED sink drivers, two pass FETs, POR. That is schematic-level
  design in the GF180 PDK (Xschem/ngspice/Magic), it is the actual risk in the project,
  and none of it is verified by anything in this directory.
- **No hardening**: RTL→GDS (OpenLane/LibreLane + PDK) was not run here — for the Tiny
  Tapeout rung it runs in *their* GitHub Actions, which is the designed path.
- **No packaging or test plan**: wafer.space delivers bare die; COB/bond-out and a test
  jig are a real sub-project (the pogo-plate work in `enclosure/` is the obvious seed).
- I²C single-master only; arbitration with the AVR sharing the bus is v-next.
- ADXL367 register values in `init_seq.v` are tagged PROVISIONAL — lifted to plausible,
  not bench-verified.

## Fix before any shuttle submission

Nothing outstanding. Both items this section was opened for are closed; it stays as the
place the next contract-level divergence gets written down, because neither of these was a
bug `tb/` could have found — the benches check the RTL against its contract, and in both
cases the contract was what was wrong.

### Closed

- **Ballast/thermal duty guard** (2026-08-19). The card clamps glow duty above an
  abuse-corner STO — `USE_BALLAST_GUARD`, `GLOW_CLAMP_STO_MV` 5200, `GLOW_CLAMP_PEAK` 225,
  applied in `sense_glow_peak()` — because RN1's EXB-28V151JX elements are rated **62.5 mW
  each** and the worst DC corner (STO 5.5 V off a bench supply, min-bin Vf 1.9 V, VOL ~0.4 V)
  draws **~21 mA** for **~68-70 mW, about 110 % of rating**. `gamma_pwm.v` had no equivalent
  *and no input to build one from*: its only control was `mode`, and mode 01's envelope ran
  to full scale regardless of rail. A chip that cannot dim itself at an over-voltage rail has
  no equivalent of the guard the card shipped.
  Both halves now exist. `sense_seq` gained `TH_CLAMP` / `vclamp` (the measurement);
  `gamma_pwm` gained `CLAMP_PEAK` / `clamp_en` and a `ballast()` function every duty passes
  through (the actuation), so a mode added later inherits the ceiling by construction. It is
  a CEILING, not a rescale, because the published bound is computed at a held peak:
  70 mW × 225/255 = 61.8 mW < 62.5 mW, so a flat top at the ceiling *is* the worst case.
  Cost: **+100 cells, +3.1 %** (3,209 → 3,309), one new flop, no latches.
  On SPEC's **"16 mA sink cells"** — that is the NORMAL ceiling, (4.65 − 2.25)/150 — the
  guard changes nothing: at the corner the same 150 Ω ballast still passes ~21 mA, a **33 %
  overshoot** into an on-die sink. Sizing those cells is analog work this experiment does not
  claim; what is now digital is the duty clamp, and it is in this directory.

- **`chg_dis` → `brownout`** (2026-08-19). The RTL's status output named the same net as
  the card and meant the opposite thing. In `wake_fsm.v` it is a brownout *tell*: asserted
  entering DORMANT on `vcrit`, released on recovery, meaning "tank is at the floor, keep the
  LED loads off". On the card `CHG_DIS_G` (PA4 -> Q2 gate) is a charge-**inhibit control**,
  driven from the FD both-edge handler to quiet the >=10 MHz DC-DC for an NFC read --
  nothing to do with brownout. Wire the RTL's output to the board's net and a brownout
  **disables harvest exactly when the tank is empty**: the cold-start deadlock that the
  2026-07-23 fix and R18's gate pulldown exist to prevent, re-introduced in silicon. The
  danger was that the miswire looked correct, *because the names matched*.
  Renamed throughout `rtl/`, `tb/` and `SPEC.md`; the rationale lives in `rtl/wake_fsm.v`'s
  header, where a future reader meets it. **It must never reach `EN_STO_CH`.** A rename is
  worth only as much as whatever keeps it renamed, so `asic.yml` now fails if `chg_dis`
  reappears as an IDENTIFIER in `rtl/` or `tb/` (comments are stripped first, so the header
  may still name it to explain why it is gone).
  Provably a pure rename: cell count unchanged at 3,209 at the time, no latches, 6/6 benches.

_(This section is newer than the review pass above: neither item was among the 5 findings,
because both were contract-level and the review checked the RTL against the contract.)_

## Where this goes (if it goes)

The ladder, deadlines and buy decision live in `TODO.md` (V-NEXT: Companion ASIC). Short
form: prove this exact core on a Tiny Tapeout SKY130 shuttle for €70 (the TT wrapper in
`rtl/` is the submission's top), then lift it into a wafer.space quarter slot — whose
padframe TT is deliberately compatible with — with the analog designed against real
silicon experience instead of first-try faith.
