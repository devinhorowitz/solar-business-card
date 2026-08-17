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
| `rtl/gamma_pwm.v` | led.c | 4-ch 8-bit PWM, gamma-2, breathe/sweep/dim modes |
| `rtl/i2c_master.v` | twi.h usage | byte-transaction master, open-drain SDA |
| `rtl/init_seq.v` | adxl367.c | ROM-driven ADXL367 config with one-retry policy |
| `rtl/sar_ctrl.v` | — | 8-bit SAR controller for the analog comparator/DAC pair |
| `rtl/sense_seq.v` | sense.c | **the deferred-read rule, in gates**: arm → settle → convert → gate off |
| `rtl/wake_fsm.v` | main.c | tap → glow → sweep; vcrit → dormant + chg_dis; NFC hold |
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
- integration: behavioural ADXL367 verifies the init addressing; tap → 197 measured PWM
  edges per LED; mid-glow brownout → **dark on the same clk edge `chg_dis` rises**
  (review finding 3 + the 5b scenario that fails without the fix); recovery glows again

An adversarial review pass confirmed 5 findings (2 critical — a hierarchical `sda_oe`
reference the wrapper leaned on, and the SDA tri-state's flow limits); all 5 fixed and
re-verified the same session. The refuted list (latches, reset gaps, unfailable TBs) is
in the workflow record.

## The number the quarter-slot question wanted

Yosys 0.33, `synth` then `abc -g NAND`, top `drh1_top`:

| | |
|---|---|
| cells (NAND-mapped) | **3,209** = 1,910 NAND2 + 1,049 NOT + 250 DFF |
| largest module | `gamma_pwm` (~54 % — the gamma × PWM datapath) |
| area @ conservative 15–25 kgate/mm² | **0.13–0.25 mm²** |
| **fraction of a 4.9 mm² quarter slot** | **≈ 3–5 %** |

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

Two places where the RTL and the card disagree. Neither is caught by anything in `tb/` --
both benches verify the RTL against its own contract, and the contract is what is wrong.

- **No ballast/thermal guard exists in the RTL.** The card clamps glow duty above an
  abuse-corner STO -- `USE_BALLAST_GUARD`, `GLOW_CLAMP_STO_MV` 5200, `GLOW_CLAMP_PEAK` 225,
  applied in `sense_glow_peak()`, the one chokepoint every animation's peak passes through.
  It exists because RN1's EXB-28V151JX elements are rated **62.5 mW each** and the worst DC
  corner (STO 5.5 V off a bench supply, min-bin Vf 1.9 V, VOL ~0.4 V) draws **~21 mA** for
  **~68-70 mW, about 110 % of rating**; the clamp holds the worst-corner average at
  70 x 225/255 = 61.8 mW. `gamma_pwm.v` has **no equivalent, and no input to build one from**
  -- its only control is `mode`, and mode 01's envelope runs to full scale regardless of rail.
  `sense_seq.v` exposes no threshold for it either.
  The number this lands on is SPEC's **"16 mA sink cells"**, which is the NORMAL ceiling:
  (4.65 - 2.25)/150. At the corner the card already guards, the same 150 ohm ballast passes
  ~21 mA -- a **33 % overshoot** driven straight into an on-die sink. Sizing those cells is
  analog work this experiment does not claim, but the **duty clamp is digital** and belongs
  in this directory. A chip that cannot dim itself at an over-voltage rail has no equivalent
  of the guard the card shipped.

- **`chg_dis` names the same net as the board and means the opposite thing.** In
  `wake_fsm.v` it is a brownout *tell*: asserted entering DORMANT on `vcrit`, released on
  recovery, meaning "tank is at the floor, keep the LED loads off". On the card `CHG_DIS_G`
  (PA4 -> Q2 gate) is a charge-**inhibit control**, driven from the FD both-edge handler to
  quiet the >=10 MHz DC-DC for an NFC read -- nothing to do with brownout.
  Wire the RTL's output to the board's net and a brownout **disables harvest exactly when the
  tank is empty**: the cold-start deadlock that the 2026-07-23 fix and R18's gate pulldown
  exist to prevent, re-introduced in silicon. The danger is that the miswire looks correct --
  the names match. Rename the RTL signal before submission (it is a status output, not a
  charge enable) and it must never reach `EN_STO_CH`.

_(This section is newer than the review pass above: neither item was among the 5 findings,
because both are contract-level and the review checked the RTL against the contract.)_

## Where this goes (if it goes)

The ladder, deadlines and buy decision live in `TODO.md` (V-NEXT: Companion ASIC). Short
form: prove this exact core on a Tiny Tapeout SKY130 shuttle for €70 (the TT wrapper in
`rtl/` is the submission's top), then lift it into a wafer.space quarter slot — whose
padframe TT is deliberately compatible with — with the analog designed against real
silicon experience instead of first-try faith.
