# Open items — SOLAR-GLOW DRH

A cross-domain tracker so nothing slips between the firmware, PCB, and enclosure
handoffs. This is an **index of what is left**, not a spec — canonical values
live in the source files it points to (see the "Where the truth lives" table in
`README.md`). Check items off in the GitHub UI as they land.

_Board is electrically frozen: a PCB layout change means a brace reprint, not a
shell re-machine. Updated 2026-07-10._

## Cross-domain (link two+ teams — easiest to forget)

- [x] **VIN-at-clamp / SUN_THRESHOLD** — _PCB → firmware. DONE 2026-07-10._ Derived
  VIN **>= 3.60 V** as the strong-sun trigger (above the held VS ~3.50 V so there is
  real forward current through D1, below panel Voc 4.15 V; full derivation at
  `firmware/board.h` `SWEEP_SUN_VIN_MV`). Firmware is now **wired**: the ~1 s poll
  fires `led_sweep` on strong-sun + caps-full via `sense_vin_flags()` /
  `sense_caps_full()`, behind the `USE_SUN_SWEEP` gate. Feel-tunable on the bench;
  the caps-full gate is the hard safety, so the number only sets when-in-sun it kicks.
- [x] **Solar-cell thickness** — _hardware → enclosure. DONE 2026-07-10._ ANYSOLAR
  SM141K06TF body is **1.2 mm ± 0.3 mm** thick (datasheet page 1 "W x L x H = 42 x 23
  x 1.2 ± 0.3" and the page-3 mechanical drawing; `datasheets/PV1,PV2  SM141K06TF
  $6.98.pdf`). Enclosure fence designs to 1.2 mm nominal; the ± 0.3 mm spread is wide
  for a "melted-in" fit, so a caliper check on the actual cells at bring-up before
  cutting fence height is still wise.
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
- [x] **Wire `led_sweep`** — DONE: fires on strong sun (VIN >= `SWEEP_SUN_VIN_MV`)
  with caps full, one VSENSE read via `sense_vin_flags()`, gated by `USE_SUN_SWEEP`
  (see the cross-domain item above).
- Recently closed: real AVR-Dx compile (green in CI), bus-fault STOP hardening,
  compile-time ADC-threshold efficiency, documentary-clarity pass, in-sun `led_sweep`
  wired (SUN threshold derived).

## PCB — `PCB/solar-glow-drh-v3_0.kicad_pcb` / `.kicad_sch`

- [ ] **Q1 thermal copper** _(owner: Devin, manual push)._ Solid pad3→pour
  (`zone_connect 1`→`2`) + a GND thermal-via cluster **adjacent to** pad3 (not
  in-pad, to avoid solder wicking) + a top-side GND flood over Q1 biased east
  into the x46.4–50.3 strip (clear of the PV2 cell), inside 9.7 mm of the coil
  keepout and clear of the x50.8 edge. Layout mockup:
  `docs/solar-glow-drh-q1-thermal-via-mockup.svg`. Still open (Q1 region has
  zero vias; pad3 is still thermal-relief).
- [ ] **PCBWay orders** — confirm both replies sent (`W567099ASH69` bare fab,
  `T-H70W567099A` PCBA); get the LED package dimension answer (1.25 vs 1.9 mm)
  and the merged PCB+PCBA total; decide the U2 spare (8-week lead); ensure the PO
  uses the confirmed C11/C13 MPNs.
- [x] KiBot group-by-MPN BOM grouping (`group_fields: ['MPN']` in
  `PCB/solar-glow-drh.kibot.yaml`) — DONE: identical parts now collapse to one CI-BOM
  line + qty. Safe because every component carries a non-empty MPN (checked); grouped
  on MPN alone so a stale footprint *field* (e.g. C13's) cannot split a real pair.
- Recently closed: C13 footprint id, C11 value (200→220 nF), L1 value, MPN-grouped CI
  BOM — merged, CI-green. Left by design: R5/R6 "VSENSE div" etc. are intentional
  house-style value labels; the origin `NPTH_mech` footprint carries real non-plated holes.

## Enclosure — `enclosure/…-backshell-…-cad.py`, `enclosure/brace/`

- [ ] **[BLOCKER before machining] Human-verify the rear maker's-mark orientation.**
  Render committed at `docs/solar-glow-drh-maker-mark-preview.png`. Numeric checks
  can't catch a mirror/flip error. First-pass read: right-side-up + horizontally
  mirrored (consistent with the intended left-to-right flip); still needs the real
  physical/STEP flip confirmed. Knob: maker-mark `aff.scale(xfact=-1, yfact=1, …)`
  (set `yfact=-1` for a top-bottom flip).
- [ ] **Front solar-panel fence** — concept only. Panel height now known (cell
  1.2 mm ± 0.3 mm, cross-domain item above); still blocked on attachment (M2 screws /
  adhesive / snap-fit) and direction A (full-perimeter, recommended) vs B (per-panel rings).
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
