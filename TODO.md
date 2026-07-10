# Open items — SOLAR-GLOW DRH

A cross-domain tracker so nothing slips between the firmware, PCB, and enclosure
handoffs. This is an **index of what is left**, not a spec — canonical values
live in the source files it points to (see the "Where the truth lives" table in
`README.md`). Check items off in the GitHub UI as they land.

_Board is electrically frozen: a PCB layout change means a brace reprint, not a
shell re-machine. Updated 2026-07-10._

## Cross-domain (link two+ teams — easiest to forget)

- [ ] **VIN-at-clamp / SUN_THRESHOLD** — _PCB → firmware._ Firmware's in-sun
  `led_sweep` glow is built but intentionally **unwired** until the PCB side
  gives the VIN level at which the TLV3011B clamp holds (VS ~3.50 V nominal).
  Then firmware wires the trigger. See `firmware-to-pcb-open-items.md` and the
  `SWEEP_*` knobs in `firmware/board.h`.
- [ ] **Solar-cell thickness** — _hardware → enclosure._ The front panel fence
  needs the **actual** ANYSOLAR SM141K06TF cell thickness (est ~1.2 mm) from the
  datasheet or a caliper — do not guess. The fence top must land on the panel top
  or the "melted-in" look fails.
- [ ] **Physical button (BTN / PA5)** — _all three._ Reserved net only,
  unpopulated. If ever fitted: PCB placement (a "v2.2 surgery"), the firmware
  `PA5` stub becomes real, and the enclosure needs a pocket/hole plus front-fence
  clearance.

## Firmware — `firmware/`, `firmware/README.md`

- [ ] **Program fuses on hardware.** BOD `bodcfg 0x0A` is decided, but
  `syscfg0`/`syscfg1` are still `0xXX` placeholders in the Makefile `fuses`
  target — compute the real bytes from the AVR64DD28 datasheet (MVSYSCFG=SINGLE,
  EESAVE). Fuses are not in the flash image.
- [ ] **Bench validation** (bare-card starting points, re-tune enclosed): tap
  axis (Z), tap/activity thresholds, INT edge/polarity, LED `INVEN` polarity.
- [ ] **Energy-budget bench measurement** — the project's #1 gate; sets the real
  achievable glow duty.
- [ ] **Wire `led_sweep`** once SUN_THRESHOLD lands (see cross-domain).
- Recently closed: real AVR-Dx compile (green in CI), bus-fault STOP hardening,
  compile-time ADC-threshold efficiency, documentary-clarity pass.

## PCB — `PCB/solar-glow-drh-v3_0.kicad_pcb` / `.kicad_sch`

- [ ] **Q1 thermal copper** _(owner: Devin, manual push)._ Solid pad3→pour
  (`zone_connect 1`→`2`) + a GND thermal-via cluster on pad3 + a top-side GND
  flood over Q1, inside 9.7 mm of the coil keepout and clear of the x50.8 east
  edge. Still open (Q1 region has zero vias; pad3 is still thermal-relief).
- [ ] **PCBWay orders** — confirm both replies sent (`W567099ASH69` bare fab,
  `T-H70W567099A` PCBA); get the LED package dimension answer (1.25 vs 1.9 mm)
  and the merged PCB+PCBA total; decide the U2 spare (8-week lead); ensure the PO
  uses the confirmed C11/C13 MPNs.
- [ ] _Optional:_ KiBot group-by-MPN BOM grouping (`group_fields: ['MPN']` in
  `PCB/solar-glow-drh.kibot.yaml`) so identical parts collapse in the CI BOM.
- Recently closed: C13 footprint id, C11 value (200→220 nF), L1 value — merged,
  CI-green. Left by design: R5/R6 "VSENSE div" etc. are intentional house-style
  value labels; the origin `NPTH_mech` footprint carries real non-plated holes.

## Enclosure — `enclosure/…-backshell-…-cad.py`, `enclosure/brace/`

- [ ] **[BLOCKER before machining] Human-verify the rear maker's-mark orientation.**
  Render committed at `docs/solar-glow-drh-maker-mark-preview.png`. Numeric checks
  can't catch a mirror/flip error. First-pass read: right-side-up + horizontally
  mirrored (consistent with the intended left-to-right flip); still needs the real
  physical/STEP flip confirmed. Knob: maker-mark `aff.scale(xfact=-1, yfact=1, …)`
  (set `yfact=-1` for a top-bottom flip).
- [ ] **Front solar-panel fence** — concept only. Blocked on: panel height
  (cross-domain), attachment (M2 screws / adhesive / snap-fit), and direction A
  (full-perimeter, recommended) vs B (per-panel rings).
- [ ] Add the maker's mark to `enclosure/README.md` once the wording is locked.
- [ ] Confirm the committed `.step`/`.stl` match the current generators (running
  a generator clobbers its STEP/STL).
- [ ] _(Cosmetic)_ brace drawing silhouettes still show the pre-DFM-clip outline.

## Locked — do NOT re-open

- Board electrically frozen; PCB change = brace reprint, not shell re-machine.
- Enclosure STEP stays **analytic-sharp**: r1.0 internal corners are a DRAWING
  spec; do **not** enable `tool_relief` (produces a faceted STEP the fab rejects).
- East cavity lip pinched to 1.0 mm over y10–72 (NFC detune) — do not widen.
- NFC tuning at bring-up needs the brace **removable** — don't defeat it.
- Supercap footprint SCHURTER SCPC 3-153-438 (flat under-body pads, asymmetric
  widths = polarity key). The old REV-J diagonal-pad land is WRONG — never reuse.
- Ti-6Al-4V (Grade 5); grounded M2 bosses tie the body to GND.
