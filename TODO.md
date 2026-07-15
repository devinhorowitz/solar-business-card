# Open items — SOLAR-GLOW DRH

A cross-domain tracker so nothing slips between the firmware, PCB, and enclosure
handoffs. This is an **index of what is left**, not a spec — canonical values
live in the source files it points to (see the "Where the truth lives" table in
`README.md`). Check items off in the GitHub UI as they land.

_Board is electrically frozen: a PCB layout change means a brace reprint, not a
shell re-machine. Updated 2026-07-11._

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

- [ ] **Program fuses on hardware** (values now computed from DS40002315C -- verify before burning):
  **`bodcfg 0x2A`** = 2.45 V sampled BOD. **NOT `0x0A`** -- that is `LVL=0x0` = BODLEVEL0, which is
  chip-erase-only, so `0x0A` ships the card with the BOD *off* (DS40002315C p.207). **`syscfg0 0xD1`**
  = factory `0xD0` + EESAVE (keeps the black box across a reflash; UPDI stays enabled). **`syscfg1
  0x10`** = MVSYSCFG=SINGLE. Fuses are not in the flash image; `make fuses` prints the commands. The
  2.45 V BOD is also the cold-start guard (below) and the hardware backstop to the software
  EEPROM-write floor (`EE_WRITE_FLOOR_MV`).
- [ ] **Bench-verify a dead-battery cold-start.** From supercaps at 0 V under *dim*
  indoor light (worst harvest), confirm the rail climbs cleanly past the 2.45 V BOD
  release without stalling -- i.e. the AVR's reset-state draw on a very slow (mV/s)
  ramp stays below the harvest current so it never sticks at an intermediate voltage.
  (Raised by Gemini as "cold-start latch-up"; it's a brown-out *stall*, not latch-up.
  Program the BOD fuse first -- it's the guard.)
- [ ] **Bench validation** (bare-card starting points, re-tune enclosed): tap
  axis (Z), tap/activity thresholds, INT edge/polarity, LED `INVEN` polarity.
- [ ] **Energy-budget bench measurement** — the project's #1 gate; sets the real
  achievable glow duty.
- [x] **Wire `led_sweep`** — DONE: fires on strong sun (VIN >= `SWEEP_SUN_VIN_MV`)
  with caps full, one VSENSE read via `sense_vin_flags()`, gated by `USE_SUN_SWEEP`
  (see the cross-domain item above).
- Recently closed: real AVR-Dx compile (green in CI), bus-fault STOP hardening,
  compile-time ADC-threshold efficiency, documentary-clarity pass, in-sun `led_sweep`
  wired (SUN threshold derived), cross-pillar harmony pass, and the NFC NDEF-write
  guard bounded to the sector-0 top (`NFC_BLK_NDEF_TOP` 0x37, was 0x7A — now rejects a
  write before the 0x3A config block; latent-only, current vCard unaffected).

## PCB — `PCB/solar-glow-drh-v4_0.kicad_pcb` / `.kicad_sch`

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
- [ ] **BOM completeness — D10/D11/C10 absent from the orderable BOMs** _(audit find,
  2026-07-11)._ The board (schematic / CI BOM) carries D10, D11 (MMSD301T1G,
  comparator-supply OR) and C10 (100 nF) as fitted SMD, but `-BOM-assembly.xlsx` lists
  only 39 (missing all three) and the docs said "36". Correct machine-place count =
  **42**. `PCB/README.md` order table + counts and root `README.md` are now fixed to 42;
  **the `-BOM-assembly.xlsx` master still needs regenerating to 42** (binary; owner: Devin).
- [ ] **DRC/ERC prose vs the committed reports** _(audit find)._ The board is DRC/ERC
  **clean** (0 unexcluded errors). But `PCB/README.md` + `solar-glow-drh-design-notes.md`
  describe "~61 marginal-band warnings" present in neither committed report (GUI: 5
  violations / 3 excluded; CI: 6 clearance + 62 MPN-parity). Decide whether the two-tier
  `.kicad_dru` rules should be loaded in the run, then align the prose. Minor: the ERC
  `isolated_pin_label` (PA4/PC0/PC1) + `endpoint_off_grid` (JP1/TP1) aren't catalogued.
- [ ] _(Cosmetic)_ C13 schematic `lib_id` is still `solarglow:C11` (clone leftover);
  surfaces as Part="C11" in the CI BOM. Same class as the C13 footprint-field fix.
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
- [ ] **[geometry] Brace↔shell mating walls disagree by 0.05 mm** _(audit find,
  2026-07-11)._ The brace models the flat cavity walls 0.05 mm inboard of where the
  shell places them, so the brace edges sit **0.10 mm** off each true wall — double the
  intended ~0.05 mm no-rattle contact the brace's fit relies on. Shell is source-of-truth;
  resolve the brace rail coords (or add `edge_fit` to the shell `_cav_inner`), then regen.
  (`…-backshell-…-cad.py` vs `…-diffuser-brace-cad.py`.)
- [ ] **[geometry] U2 relief pocket is 1.0 mm east of the real U2** _(audit find)._ PCB
  has U2 at (27.5, 37); `…-backshell-…-cad.py` `U2_POS = (28.5, 37)`. ~0.5 mm of the
  tallest B-side part overhangs the un-relieved floor. PCB is frozen truth → fix `U2_POS`
  + regen the STEP/STL (and the derived drawing/README note-7 copies).
- [ ] **Fab drawing still renders the retired locator pillars** _(audit find)_ + NOTE 4
  (Ø3.2 recesses), contradicting the pillar-free STEP — and it's the file attached to the
  PCBWay CNC quote. De-pillar `…-backshell-…-DRAWING-gen.py` and regenerate the PDF/PNG.
  (Also low: several generator docstrings still cite the pre-redesign floor 0.95 / cavity
  1.85 / two locator pillars, and "four" vs "two" outboard rails.)
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
- **NFC contact is offline-first.** The full vCard is **embedded** in the tag (`text/vcard`
  NDEF, `nfc.c`), read RF-powered by the phone with the card's supercap flat and **no
  reception** (the dead-signal courtroom case). A URL / App Clip is only ever an OPTIONAL
  rich-content extra -- **never** a dependency for the contact import. Do not swap the embedded
  vCard for a URL-only record.
