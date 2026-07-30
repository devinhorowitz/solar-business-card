# Open items — SOLAR-GLOW DRH

A cross-domain tracker so nothing slips between the firmware, PCB, and enclosure
handoffs. This is an **index of what is left**, not a spec — canonical values
live in the source files it points to (see the "Where the truth lives" table in
`README.md`). Check items off in the GitHub UI as they land; **completed items are
culled** — the record lives in git history + the `solar-glow-drh-design-notes.md`
addenda.

_Board freeze status (updated 2026-07-25): the 2026-07 audit round reopened the
netlist and it is now closing again — Q2/R18 (the cold-start-deadlock buffer) and
the FRAM VS re-rail are placed, routed, and verified on the board; the U7
footprint-identity swap and DNP clear have since landed too (2026-07-26). A PCB layout change still means
a brace reprint, not a shell re-machine._

_Completed & culled 2026-07-25 (see git history + design-notes addenda for the
full reasoning): the AVR64DD28→AVR64EA28 family swap + firmware port; the U5 NFC
and U6 load-switch (→TPS22917) silicon audits; the U7 FRAM DFN-repackage and the
VS-rail back-power fix (schematic + firmware + board all landed — the FRAM
bench-verify is still open, see the items above); the Q2/R18 cold-start-deadlock buffer (schematic + firmware + board); the
passive longevity/precision upgrades (X7R / AEC-Q200, 0603 & 0805 upsizes,
thin-film dividers); the full live DigiKey/Mouser BOM sourcing pass; the
SUN-threshold derivation and the solar-cell-thickness resolution; and the
STO_LDO island / led_sweep / MPN-grouped-BOM work._

## Cross-domain (link two+ teams — easiest to forget)

- [x] **[TOOLING] `check_consistency.py` now guards the schematic↔board boundary**
  _(2026-07-26; DONE.)_ Four losses happened at this seam (U9's Footprint property, U7's DNP
  flag twice, C29 absent from the schematic, the U7 land mismatch). The checker now compares
  board refdes against schematic refdes and fails on anything present only on the board — a
  sync would DELETE those — and compares footprint assignments, since a mismatch MOVES pads.
  The footprint check was a warning while U7 was open; **since 2026-07-26 it is a hard error**
  (U7 is settled — see the PCB section).

- [x] **[ENCL] U7 shell-pocket recheck — the last piece of the FRAM repackage**
  _(2026-07-29; DONE.)_ U7 is the 0.90 mm DFN, not the 1.75 mm SOIC. The backshell's 0.95 mm floor
  pocket went away by arithmetic on 2026-07-28 (`U7_POCKET = max(0, U7_H - cap_H)` → 0), and the
  2D drawing that still showed it in Detail B has now been regenerated to match — it reads "NO U7
  RELIEF POCKET".
  The recheck turned up a second, worse instance the item did not anticipate: the **brace**
  generator kept its own `part_height()` copy at 1.75, so it was cutting U7 as a **through-hole**
  (depth 1.87 ≥ GAP−0.05) instead of a 1.02 blind pocket — a hole through a part, from a number
  corrected everywhere else a day earlier. Heights now live once in `enclosure/part_heights.py`,
  every generator imports them, and `check_consistency` **[7]** measures each against that part's
  own 3D model so neither direction of drift can go quiet again. The brace STEP/STL and both
  drawing sheets are regenerated; `through-holes: ['U6']` is now the complete list.

- [ ] **[BOM] Buy the low-stock / long-lead parts early** _(2026-07-23)._ Thin at audit: **supercaps**
  SC1–4 (~195–200), **FER1** ferrite (41), **U3** accel (731), **U1** MCU (608), **PV** cells (423).
  Supercaps + ferrite are the historical long-lead items — order with the first cut. Also grab a
  **spare NT3H2211 or two**: NXP steers new designs to NTAG 5, so NTAG I²C plus carries EOL risk on a
  years horizon (the U5 NFC audit (now in git history / design-notes) kept it as best-fit, but flagged this).

- [ ] **[PCB] Silk legend height on the STO_LDO upload** _(2026-07-21)._ Two B.Silk legends
  (`TINY MODE` @ (31.75, 50.95), `ENABLE` @ (27.5, 49.63)) sit at 0.5 mm and trip the 0.8 mm
  min-silk-text DRC rule (2 `text_height` warnings, not errors). Decide: bump both to ≥ 0.8 mm if they
  fit the switch cluster, else add to the README / kibot intentional-exceptions list so the next DRC
  review doesn't read them as a new find.

- [ ] **[PCB→KiCad] Sync SC1/SC3 footprint metadata to SS17** _(2026-07-22)._ PR #52 corrected the
  hybrid tank in the schematic + BOM + docs (SC1/SC3 = SS17 `3-153-440` 1.8 F, SC2/SC4 = WS17
  `3-153-438` 1.0 F), but the board `.kicad_pcb` SC1/SC3 footprint Value/MPN still read WS17. In KiCad,
  update SC1/SC3 (or pull the schematic) → **Update PCB from Schematic** → re-upload. Metadata only —
  nets and copper unaffected.

## Firmware — `firmware/`, `firmware/README.md`

- [ ] **[FIRMWARE] Functional audit findings never filed — carried over honestly**
  _(2026-07-26; surfaced by the pass-3/pass-4 firmware audits, actioned in docs only.)_ Each is real,
  each survived adversarial verification, none is fixed:
  (a) **`adc_read_raw`'s guard is a WAKE COUNT, not a time bound** (sense.c). Three unrelated
  interrupts inside one ~212 µs conversion make a *healthy* ADC return 0, which every caller reads as
  "rail below floor / dark". Fail-safe for the glow, but it also clears `prev_light`, so it is not
  fail-safe for the light edge. Bounding by time instead of wakes is the fix.
  (b) **ADXL367 configured inside its 100 ms data-valid window** (adxl367.c:62). `POWER_CTL` enters
  MEASURE and the latch clears run immediately after, inside the window the datasheet says must
  elapse before acceleration data is valid. The 10 ms reset-latency fix did not address this.
  (c) **Tap tally wears one EEPROM cell** (sense.c). It is the only writer with a user-driven,
  unbounded rate, and byte 0 of the dword at offset 0 changes on every tallied tap → a hard 100 k
  ceiling on that byte. A rotating/gray-coded counter or a wear-levelled slot would remove it.
  (d) **`EE_WRITE_FLOOR_MV` is derived against VDD hazards but compared against STO** — different
  nodes. Harmless below 3.3 V where STO ≈ VS, but the derivation should say so.
  (e) **`twi_bus_clear()` ends with START-immediately-followed-by-STOP**, which the EA datasheet
  itself names an illegal bus operation. Benign for the targets, but worth a deliberate comment or a
  reordered terminating sequence.
  (f) **`ndef_default[]` has no Lock Control TLV**, which the NT3H datasheet says a Type-2 tag needs
  for full NFC-Forum compliance. Phones read it fine without one; strict validators may not.


- [ ] **[BENCH/DESIGN] SWEEP_SUN_VIN_MV measures the wrong thing — retune or retire it**
  _(2026-07-26 PCB audit; board.h comment already corrected in full, constant deliberately left
  at 3600 pending this decision.)_ The AEM10300 does not let SRC float to a light-dependent
  voltage: while charging it **regulates SRC to 0.80 × Voc** (R_MPP[2:0] = H,L,L → 80%, Table 9,
  read off the board straps). Reaching 3600 mV would need Voc ≥ 4500 mV, above the SM141K06TF's
  4.15 V — so the SUN flag is unreachable while charging in ANY light. It sets only when the tank
  is full (DCDC off, SRC high-Z → Voc, which also saturates the 2.048 V ref) or during the 70.8 ms
  MPP-evaluation window every 4.5 s (T_MPP = H,L, Table 10) — a 1.6% duty artifact.
  Consequences: (a) the sweep's two co-gates are really one condition, so the sweep still behaves
  correctly but for the wrong stated reason; (b) **the sun diary does not bank sun-hours** — it
  banks caps-full time plus that 1.6% artifact, which is a second independent error on top of the
  poll-counting one already filed. Decide at the bench: set the threshold below 0.8 × Voc
  (~3000–3200 mV) so it genuinely discriminates bright from dim while charging, or drop the
  co-gate and re-scope the diary to what it actually measures.


- [ ] **[BENCH/CALIBRATION] VS_GLOW_FLOOR_MV vs the STO-channel accuracy stack-up**
  _(2026-07-26 pass 4; the highest-value open firmware item.)_ Pass 3 removed the *systematic*
  error (the 2.500 V reference sagged below its 3.0 V spec floor and inverted the guard). What
  remains is ordinary tolerance: reference ±2% (−40..+85 °C, ±5% to 125 °C) + ADC offset/gain/INL
  + divider, which at the extended-temperature corner still lets `VS_GLOW_FLOOR_MV = 2750` permit
  a glow at a true STO **below the 2.60 V BOD**. Restoring the intended 150 mV of sag margin at
  the worst corner implies a floor near **2900 mV**, at the cost of usable range. **Measure it**:
  read `sense_vdd_mv()` against a meter across 2.6–4.65 V and over temperature, then set the floor
  from data. Do not fold in a datasheet corner blind — it trades real runtime for paper margin.
  Same stack-up applies to `EE_WRITE_FLOOR_MV` (2850 vs erratum 2.2.1's 2.7 V) and
  `SWEEP_CAPS_FULL_MV` (4400 vs VOVCH 4.65 V, whose datasheet row has no min/max).

- [ ] **[BENCH] Confirm the reordered NFC provisioning end to end** _(2026-07-26 pass 4.)_
  Provisioning now writes the NDEF first and the CC **last**, so a partial write leaves a tag
  readers ignore rather than one advertising garbage. Verify on a real tag: (a) the phone offers
  the vCard after a clean run; (b) `nfc_present()` still ACKs at 0x55 after the block-0 write
  (datasheet sec 8.3.8 warns the address byte and static lock bytes live in that block); (c) an
  interrupted run leaves the tag inert rather than half-published.

- [ ] **[FIRMWARE] Residual efficiency items, each already quantified** _(2026-07-26 pass 4;
  none applied — they need the energy budget measured first to know if they are worth it.)_
  `adxl367_clear_activity()` fires unconditionally in the tap and NFC-ack branches (~367 µs of
  ACTIVE I2C each) even when INT2 never asserted; `adxl367_read_z()` runs every poll though
  dormancy integrates over 180 s; the TCB ticks at 1 ms while the animation only updates duty
  every 12 ms (11 of 12 wakes do nothing); `gamma2()` floors inputs ≤ 15 to zero so ~7.8% of every
  breath is a black hold; TWI waits and the fram_sleep retry busy-spin in ACTIVE where they could
  IDLE-sleep.


- [ ] **[BENCH] ADC reference moved 2.500 V -> 2.048 V — re-verify every gate on silicon**
  _(2026-07-26 deep audit; fix LANDED.)_ The 2.500 V reference is spec'd only for VDD >= 3.0 V
  and `VVREF` max is VDD-0.4, so below ~2.9 V it sagged and every rail gate read HIGH — the
  2750 mV glow floor actually tripped at ~2582 mV, **below the 2.60 V BOD**. Now on 2.048 V
  (valid to VDD 2.55 V, ±2%). Bench: (a) confirm measured STO/VIN mV against a meter across
  2.6–4.65 V; (b) confirm the glow floor now genuinely stops the glow above the BOD;
  (c) confirm `sense_vin_mv()` saturation above VIN 4.096 V is acceptable in practice.

- [ ] **[BENCH] SWEEP_CAPS_FULL_MV 3300 -> 4400 — confirm the sweep still arms**
  _(2026-07-26 deep audit; fix LANDED.)_ 3300 was a stale v3 value (when the sensed rail was the
  clamped ~3.5 V supercap node); against STO's VOVCH 4.65 V ceiling it was only 71% of full /
  50% of energy, so the "hard safety gate" allowed spending half the tank, re-armed every poll.
  Bench: confirm a real card in strong sun actually reaches 4400 mV STO and plays the sweep —
  if the AEM's charge taper makes 4400 unreachable in practice, tune down toward ~4300, but do
  NOT return to a value that is not a fullness criterion.

- [x] **[SOURCING] Unsourced numbers in comments — retired** _(2026-07-26; DONE.)_ Every claim
  below was checked against its primary source and corrected in place: the **"~13 ms EEPROM write"**
  (6 sites) → ~4 ms, since DS Table 35-8 gives tD_BPW 2 ms + tD_BPE 2 ms; **"256 B"** EEPROM → 512 B;
  **"~21 J reserve"** → dropped (nameplate, not the ~9.6 J actually spendable above the glow floor);
  **"8.192 s"** watchdog → 8.0 s (WDT.CTRLA PERIOD 0xB); **0.89 µA** for the ADXL367 now carries its
  test condition (2.0 V supply, while this board runs the part at 3.3 V); the **SUN_COUNT** comment's
  2.500 V-era arithmetic (2950 / ×0.8192) → the fold now collapses to count == VIN in mV exactly;
  **`sense_caps_full`** doc said "VS ≥" → STO; the **SAMPDUR** rationale blamed divider impedance when
  both nodes carry a 100 nF reservoir (C5 / C24) that dominates by orders of magnitude — real reason
  is the temp sensor's ≥32 µs rule; **`nfc.h`'s block map** (write "MUST stop below 0x3A" → the first
  non-user block is 0x38; "raw ceiling 0x7A" → 0x7F; "NO sector-select" was never the reason — the I2C
  side addresses 0x00–0x7F linearly); **`firmware/README`** still claimed the tag ships with a valid CC
  and that firmware "never touches block 0", both false since the pass-2 CC fix; the **`LIGHT_THRESH_MV`
  light-range** and the SWEEP_SUN range contradicted each other ~3× for the same node — both now flagged
  as unsourced bench items rather than asserted; and the **tap tally's RAM bank** now states that
  `pending` lives in .bss and does not survive a reset.
- [ ] **[BENCH/DESIGN] Sun diary counts POLLS, not TIME — and is least accurate while measuring**
  _(2026-07-26 deep audit.)_ `SUN_POLLS_PER_HOUR` assumes one poll == POLL_PERIOD_S exactly, but
  (a) OSC32K total error is <1% only at 25 °C/3.0 V and **<10% over the full range** (Table 35-10),
  and (b) the in-sun sweep fires on the same condition the diary counts and stretches the loop
  period, so a banked "hour" is long by the sweep duty in exactly the state being logged. Decide:
  either re-label the diary as approximate in the docs/NDEF, or count elapsed PIT ticks
  independently of loop servicing. Do not present it as a measurement until one of those is done.

- [ ] **[BENCH] The MCU energy budget cannot be given a worst case from current sources**
  _(2026-07-26 deep audit.)_ DS40002443**A** is a *Preliminary* datasheet: its power tables state
  "not tested and are for design guidance only", every sleep-current Max column is **empty**, and
  there is no 1 MHz IDD row (lowest is 5 MHz). So the standing-current figure is a typ-only
  extrapolation. This must be **measured**, not derived, before the energy budget is called
  closed — and re-checked against a non-preliminary datasheet revision if one ships.

- [ ] **[EFFICIENCY] Quantified idle-draw levers, if the bench budget comes in tight**
  _(2026-07-26 deep audit; all measured-on-paper, none applied.)_ Ranked: `POLL_PERIOD_S` 1 -> 2
  halves the ~1 Hz housekeeping cost; `FRAM_RESLEEP_EVERY_POLL` -> 0 removes the defensive re-park
  (already ~halved by dropping its trailing busy-delay); `adxl367_read_z()` runs every poll though
  dormancy only needs 180 s of evidence; the TWI/`_delay_us` waits busy-spin in ACTIVE where they
  could IDLE-sleep. Also **hardware, not firmware**: the R15/R16 STO divider is 3 MΩ across the
  tank = **1.1–1.55 µA continuously**, comparable to the whole MCU standing budget and larger
  than the accelerometer — worth revisiting if the budget is tight.


- [ ] **[BENCH] NFC Capability Container write — confirm the tag survives at 0x55**
  _(2026-07-26 firmware audit; fix LANDED in `nfc_write_cc()`.)_ The tag ships with CC = all-00h
  (datasheet 8.3.10), so provisioning now writes `E1 10 6D 00` into I2C block 0 — the block whose
  byte 0 is the I²C address. We write `NT3H_ADDR << 1` = 0xAA there, the only value correct under
  both of the datasheet's two contradictory statements (8.3.2's "MS 7 bits are the address" rule vs.
  its trailing REMARK recommending 04h). **On the first provisioned tag, verify `nfc_present()` still
  ACKs at 0x55 after the CC write.** If it does not, the tag moved to 0x02 — repoint `NT3H_ADDR`;
  RF/vCard is unaffected either way. Then confirm a phone actually offers the vCard (the whole point
  of the fix — before it, no phone would).

- [ ] **[BENCH] I²C bus-clear — exercise the recovery path** _(2026-07-26 firmware audit; fix LANDED
  in `twi_bus_clear()`, called from `twi_init()`.)_ Deliberately wedge the bus (reset the MCU mid-read
  so a target is left driving SDA low) and confirm the 9-pulse + STOP recovery frees it and the accel
  answers on the next boot. Also worth scoping once: that the recovery's 5 µs half-period is really
  ~100 kHz at the fused 1 MHz CLK_PER.

- [ ] **[BENCH] ADXL367 7.5 ms reset latency — confirm config now sticks** _(2026-07-26 firmware audit;
  `_delay_ms(2)` → `_delay_ms(10)`, datasheet Rev. B Table 37.)_ The old under-spec wait could leave the
  part at reset defaults with the tap engine off. After flashing, read back FILTER_CTL / POWER_CTL /
  INTMAP1_UPPER over I²C and confirm they hold the configured values, not 0x00 / reset defaults.


- [ ] **[BENCH] LED sub-emission idle-bias — Hi-Z park + docs LANDED, bench measurement remains**
  _(2026-07-23 fw / 2026-07-25 docs; the pads park as inputs between animations (bias → clamp-limited
  ~1 V worst case, zero below STO ≈ 3.6 V), and both the Hi-Z park and the SW2-OFF stow discipline are
  now documented in `firmware/README.md`.)_ Remaining: (a) bench-measure the real idle LED current;
  (b) only if the energy budget allows, consider a VOVCH re-strap one step down (E ∝ V², costly).

- [ ] **[BENCH] FRAM back-power fix — verify the VS-rail + Sleep-park** _(2026-07-23; sch + fw + board
  all done & verified.)_ Bench-confirm: IZZ standing current (~0.20 µA typ), VS idle current, and
  whether the FRAM's Sleep-exit wake is address-selective — if it is, set `FRAM_RESLEEP_EVERY_POLL 0`
  (the defensive per-poll re-park is then unneeded). Full analysis in the design-notes deep-dive
  addendum.

- [ ] **[BENCH RULES] Cross-domain bench-procedure set** _(2026-07-23 second-sift)._ (1) JP1 SCL/SDA:
  external I²C adapters only with the card powered and the adapter referenced to VS — the ADXL367 (and
  the FRAM) digital abs-max is a zero-headroom "−0.3 to VDDIO". (2) STO injection: SW2 OFF first (a lit
  injection above ~2.5 V forward-drives the LEDs into the dead MCU's clamps, ~16 mA/pin). (3) Dark
  bench-charging of STO: pre-balance the 2S midpoint or charge under light (BAL active). (4) UPDI into
  a flat card: power the card via the programmer (~0.5 mA PF7 clamp current otherwise — bounded but
  pointless).

- [ ] **[BENCH] Read + log the EA silicon revision (B1 vs B2)** _(2026-07-23)._ Errata 2.2.1–2.2.3
  (DS80001048C, in `datasheets/`) are Rev. B1-only; the firmware carries the 2.2.3 SLPCTRL NOP-guard
  either way and `EE_WRITE_FLOOR_MV` covers 2.2.1. Read `SYSCFG.REVID` over UPDI at first connect so we
  know which part we actually got. Also **re-measure the EA sleep/power figures against real
  silicon** — DS40002443A was PRELIMINARY, so its numbers are typ-only — and re-confirm the
  port-derived floors (`VS_GLOW_FLOOR_MV` 2750 / `EE_WRITE_FLOOR_MV` 2850) still hold.

- [ ] **Program fuses on hardware** (EA values, from DS40002443A — verify before burning):
  **`bodcfg 0x4A`** = 2.60 V sampled BOD (BODLEVEL2; the EA has no 2.45 V level). **NOT `0x0A`** =
  BODLEVEL0 1.75 V, chip-erase-only → ships the card BOD-off. **`osccfg 0x08`** = OSCHF base 16 MHz so
  `clocks_init`'s ÷16 lands on exactly 1 MHz (pre-fuse it runs a harmless 1.25 MHz). **`syscfg0 0xD1`**
  = factory + EESAVE (keeps the black box across a reflash). **`syscfg1`: factory default** (the EA has
  no MVSYSCFG). `make fuses` prints the commands. The BOD is also the cold-start guard and the hardware
  backstop to the software EEPROM-write floor (2.85 V).

- [ ] **Bench-verify a dead-battery cold-start.** From supercaps at 0 V under *dim* indoor light (worst
  harvest), confirm the rail climbs cleanly past the 2.60 V BOD release without stalling — the AVR's
  reset-state draw on a slow (mV/s) ramp must stay below the harvest current so it never sticks at an
  intermediate voltage. (It's a brown-out *stall*, not latch-up. Program the BOD fuse first — it's the
  guard. Q2 now also keeps AEM charging enabled while the MCU is in reset — the cold-start-deadlock
  fix.)

- [ ] **Bench validation** (bare-card starting points, re-tune enclosed): tap axis (Z), tap/activity
  thresholds, INT edge/polarity, LED `INVEN` polarity.

- [ ] **[EA upgrade, bench-era] Use the EA ADC's differential mode + PGA + burst accumulation** for the
  rail/light reads _(2026-07-23, deferred from the EA port)._ The port keeps DD-shaped single-ended
  reads so behaviour is 1:1; the EA can do better (diff vs GND kills common-mode offset on the ~500 kΩ
  dividers, PGA relaxes the source-impedance math, ×N accumulation averages divider noise — it pairs
  with the 0.1 %/25 ppm thin-film dividers already on the board). Do it after the energy measurement,
  meter attached: each knob changes conversion time and therefore poll energy.

- [ ] **Energy-budget bench measurement** — the project's **#1 gate**; sets the real achievable glow
  duty. Every firmware duty-cycle / glow constant is provisional until it lands. **Size it to the LED
  brightness FLOOR:** D2–D5 ship unbinned (`V2BB` is a min-to-max span), so output varies ~3× part-to-part
  — V2 = 900 mcd / 3030 mlm (~49 lm/W) up to BB = 2800 mcd / 7560 mlm (~123 lm/W) at 30 mA. Design against
  V2; a kind reel just looks better. (LED-audit addendum, 2026-07-25.)

## PCB — `PCB/solar-glow-drh-v4_0.kicad_pcb` / `.kicad_sch`

- [ ] **[PCB/BOM] C25 re-pick LANDED in sch/BOM — ⚠ THE BOARD IS DELIBERATELY RED until the 0805 land is synced**
  _(Re-pick landed 2026-07-30; only the LAND sync remains, and the tripwire enforces it.)_ The schematic
  now says `Capacitor_SMD:C_0805_2012Metric` + TDK `C2012X5R1C226M125AC` (16 V, DK `445-7647-1-ND`,
  11,799 in stock, $0.56 q1) while the board still carries the 0603 land, so `footprint_symbol_mismatch`
  (error since the C9 episode) and consistency check [1]'s footprint comparison both FAIL ON PURPOSE.
  **To clear:** open the board, *Update PCB from Schematic* (C25 keeps its centroid at (25.15, 55.0) r90;
  verify pad 1 = BUFSRC, pad 2 = GND), re-run DRC, and **in the same commit flip `part_heights.py`
  `"C25": 0.90 → 1.25`** — the file's comment explains why it must wait for the sync (declaring 1.25
  against the 0603 model is a 0.45 overshoot and check [7] would rightly error). The finding it fixes,
  kept for the record:
  _(2026-07-30, second full passive audit.)_ The AEM10300's Recommended Operation Conditions
  table gives **CSRC min 13 µF, typ 22 µF**, and its footnote 1 is explicit: *"Consider all
  component tolerance and deratings. Typically, DC-bias derating has a major impact on
  capacitance on ceramic capacitors."* C25 is `GRT188R61A226ME13D` — 0603, 22 µF, X5R, **10 V**
  — on BUFSRC (pin 4, "connection to an external capacitor buffering the DCDC converter
  input"), which rides the source MPP at ~3.1–3.5 V and reaches V<sub>OC</sub> ≈ 4.15 V during
  MPP evaluation. A 0603 22 µF/10 V X5R typically loses **45–60 %** of its capacitance at
  3.3–4.15 V bias → **~9–12 µF effective, under the 13 µF minimum** the derating footnote is
  about. (Estimate from family curves — a SimSurfing pull or bench C-V would firm the exact
  number, but the margin sign is not in doubt.)
  **Fix, verified in stock:** TDK **`C2012X5R1C226M125AC`** — 0805, 22 µF, X5R, **16 V**,
  1.25 mm max, Active, 11,799 at DigiKey, $0.23@100. At 4.15 V an 0805/16 V part derates
  ~20–30 % → **~15–17 µF effective** ≥ 13. **It fits in place:** measured neighbour gaps at
  C25 are SC3 0.529 / L2 0.575 / SB2 0.776 mm; 0603→0805 growth (~0.25 mm per side wide,
  ~0.22 long) leaves ≥ 0.28 mm everywhere. A 1206 does **not** fit (L2 gap would hit 0.02 mm).
  With the swap: `part_heights.py` **"C25": 0.90 → 1.25** (the generic-0805 figure C26/C27/C9
  use), same mechanism as C9's entry; the brace pocket regenerates from the footprint change.

- [x] **[BOM] C26/C27 re-picked to Samsung `CL21B106KOQNNNG` (16 V) — complete, zero layout change**
  _(Landed 2026-07-30: sch + board metadata + both BOM files + `part_heights` 1.25 → 1.45, all in one
  commit — same 0805 land, so no tripwire needed. Mouser `187-CL21B106KOQNNNG`, 4,292 in stock, $0.22 q1,
  verified live.)_ The finding it fixes, kept for the record:
  _(2026-07-30, same audit.)_ `GRM21BR71A106KA73L` (0805, 10 µF, X7R, 10 V): **0 stock at
  DigiKey across all three package types and no availability at Mouser**; the automotive
  sibling `GRT21BR71A106KE13L` is stocked but **NRND**. Two live candidates:
  Samsung **`CL21B106KOQNNNG`** — 16 V X7R, **4,292 in stock at Mouser**, $0.22 — and Yageo
  `CC0805KKX7R7BB106` (16 V, 92,997 *on order* at Mouser, none in stock today).
  16 V also fixes the quiet derating note: C27 sits on **STO, up to 5.5 V — 55 % of a 10 V
  rating** — where a 10 V X7R gives up ~35–45 % of its capacitance (~5.5–6.5 µF effective; its
  role is local decoupling next to a 1.3 F supercap, so functionally fine, but a 16 V part
  halves the loss). C26 is on VINT (≤ 2.75 V), untroubled either way.
  **The catch, so it does not become a brace defect:** `CL21B106KOQNNNG` is **1.40 mm max** —
  taller than the 1.25 mm package-generic figure `part_heights.py` carries for C26/C27. Adopt
  it and those two entries must go **1.25 → 1.45** in the same commit (check [7] accepts a
  declared height above the generic model by up to 0.35, so 1.45 vs modelled 1.25 passes as
  deliberate air). Same land, zero layout change.

- [ ] **[PCB/FW] R1–R4 exceed their 62.5 mW rating only at the worst corner — note, and one cheap guard**
  _(2026-07-30, same audit.)_ The LED ballasts are `AC0402FR-07150RL` (0402, **1/16 W**). Worst
  DC corner: full tank STO = 5.5 V through SW2, min-bin V<sub>f</sub> 1.9 V (LA P47F 3B bin),
  AVR V<sub>OL</sub> ≈ 0.4 V ⇒ I ≈ 21 mA ⇒ **~68–70 mW ≈ 110 % of rating** at 100 % duty.
  Typical operation (STO 4.5, V<sub>f</sub> 2.2) is ~22 mW. PWM breathing keeps the average
  far below the peak, so this only bites if firmware ever holds 100 % duty with a full tank
  and a low-bin LED. Cheapest guard: clamp duty when STO > ~5.2 V in the glow constants
  (which are provisional pending the energy budget anyway). Alternative if the board is ever
  re-laid: 0402 → 0603 (0.1 W) on the four ballasts. No action on the copper today.

- [x] **[PCB] Second full passive audit — the passes, recorded so the next audit starts from here**
  _(2026-07-30; all 35 passives, sch + board + BOM + datasheets + live sourcing.)_
  **Zero drift** sch↔board on value/MPN/supplier-P/N/footprint/dnp across all 35.
  **AEM10300:** L2 `DFE252010F-100M` I<sub>sat</sub> **1.3 A ≥ the required 1 A** (rated
  900 mA, DCR 600 mΩ), 10 µH ✓; CINT C26 ~9 µF effective at ≤2.75 V ≥ min 5 ✓; CSTO n/a (the
  requirement is for removable storage; ours is a soldered 1.3 F tank, C27 is extra local
  decoupling). **TPS7A02:** C22 1 µF ✓ (25 V part, ~0.9 µF at 5.5 V bias); V<sub>S</sub> rail
  total ≈ 12.8 µF nominal — inside the datasheet's **1–22 µF COUT window**, ≥ 0.5 µF effective ✓.
  **ADXL367:** C11 220 nF = exactly the "external 0.2 µF needed" on VREG_OUT ✓ (its
  `GRT155R71C224KE01D` has only **2,527 in stock** — order with the build). **NT3H2211:** VOUT
  (pad 7) is unconnected, so the 150–220 nF energy-harvest C<sub>load</sub> requirement does
  not apply; C8 100 nF is plain VCC decoupling ✓. **Voltage ratings:** every cap ≥ its node
  max; the tightest is C27 at 55 % (see its item above). **Power:** R12 TINY worst-case 28 mW
  of 62.5 ✓ (the 220 Ω feed is the dimmer by design); dividers are µW. **Lands:** the
  generator-era shared `solarglow:C1` land (C24/C29/R17/R18) measures 0.59×0.66 pads at
  ±0.51 — a hair more generous than the stock 0402's 0.56×0.62 at ±0.48, fine. The refless
  `solarglow:NPTH_mech` at (0,0) (kibot W147) is the deliberate board-only container for the
  7 NPTH holes — benign. **Sourcing:** every MPN Active; the one stock-zero is C26/C27's
  (its own item above). Fixed in this pass: C9's Value `"47pF-NP0"` → `"47pF"` (the suffix
  broke kibot's value parser — W020 on every CI run; NP0 lives in the Description).

- [x] **[PCB] TC1 moved to the front — deliberate, and the docs now say so**
  _(2026-07-30; CONFIRMED deliberate by DRH. Found while checking whether the v4 changes had
  propagated to the READMEs.)_ In `5934b7d` the Tag-Connect programming cluster went **`B.Cu` →
  `F.Cu`** — footprint layer, all five pads, and their mask apertures — plus a 180° rotation. XY
  did not move (13.3, 16.9). At `8e5090ec` it was `B.Cu`; from `5934b7d` on it is `F.Cu`.
  **What it buys.** The blocker used to be **SC1**, a *reflowed* SMD supercap, so the programming
  window closed before the board was finished — you flashed a card with no energy storage on it.
  The blocker is now **PV1**, whose body spans (2.3, 4.25)–(48.5, 27.25) over the pad cluster at
  (12.219, 15.184)–(14.381, 18.616), and the cells are hand-soldered *last*. So the window moved
  to "everything reflowed, cells not yet on", which is the right place for it. PV1's own pads do
  not touch TC1's — 0.0% overlap — so the obstruction is mechanical, not electrical.
  **What it costs.** Five bare ENIG pads on the show face. PV1 covers them in a finished card, so
  they only read on a bare or unpopulated board and in the midnight-variant renders. And lifting a
  heat-sensitive cell (≤ 260 °C / 2 s) to re-program is a worse recovery than lifting a supercap
  was — which is the argument for loading **J1** on any board you expect to iterate firmware on.
  **Docs updated to match:** `PCB/README.md`'s warning box names PV1, and the root README's
  assembly order flashes at step 3 and solders the cells at step 4. It read "cells (3) → flash (4)"
  before, which TC1's new position makes impossible.

- [ ] **[TOOLING] Nothing in CI notices a footprint changing SIDES**
  _(2026-07-30; surfaced by the TC1 move above, which was intended — the point is that an
  unintended one would arrive just as quietly.)_ DRC has no opinion on which side a footprint sits,
  schematic parity has no layer concept, and `check_consistency` **[1]** compares refdes and
  footprint assignment but not side. TC1's flip was caught only as a side effect: `board_parts("B")`
  stopped returning it and the brace's pocket list changed underneath.
  A side flip is a one-keystroke edit in KiCad (`F` on a selected footprint) and it moves every pad
  and mask aperture to the other face — for a B-side part it also silently deletes that part's
  brace pocket, which is the enclosure failure mode `part_heights.py` exists to prevent from the
  other direction.
  There is no schematic-side source of truth to check against, so this cannot be a *comparison*
  the way check [1] is; it has to be a **snapshot**: record refdes → side, fail on any change, and
  update the snapshot in the same commit that makes the move. That is the same shape as the DRC
  exclusion list — deliberate changes stay cheap, undeliberate ones stop being invisible.

- [x] **[PCB] Stitch the stranded GND lobe under C13 / SB2 — one via at (24.707, 49.702)**
  _(2026-07-30; DONE. DRC `unconnected_items` 1 → 0.)_ The board picked up a stranded GND island in
  the 2026-07-30 sync. It was **8.20 mm² of B.Cu**, x[23.33, 28.37] y[47.20, 53.17], and it carried
  two real pins: **C13 pad 2** (the 10 µF LED-rail reservoir) and **SB2 pad 2** (the LED2 jumper).
  Not decorative copper — two ground connections that were not ground.
  **Correcting my own PR #115 report, which said the orphan was the 13.6 mm² F.Cu polygon at
  x[10.13, 35.55] y[39.99, 48.67]:** that was wrong. That island has three GND vias and is fine.
  Every isolated group on this board is on **B.Cu**. The bad read came from a per-island "does this
  island contain a GND via" test; connectivity is a *graph*, and the answer only came out right once
  islands, tracks, vias and pads were unioned across both layers.
  **Why one via, and why that one.** The via pad has to sit in the stranded lobe, touch F.Cu GND,
  and clear every other net on both layers by the 0.152 mm floor. Scanning the whole lobe at 5 µm
  leaves **exactly one pocket**, ~129 sites, all within 0.05 mm of each other. The chosen point is
  its best-centred member:

  | | |
  |---|---|
  | pad on the stranded B.Cu lobe | 75.8 % (0.214 mm²) |
  | pad on main F.Cu GND | 68.0 % (0.192 mm²) |
  | clearance, F.Cu | 0.176 mm — the `ANODE` run at y 49.150 |
  | clearance, B.Cu | 0.175 mm — the corner of `SW2` pad 1 (`STO`) at (25.101, 49.968) |
  | to C13's stranded GND pad | 0.91 mm |

  0.175 mm reads tight until it is put next to the board: **196 different-net copper pairs already
  sit closer than that**, and 128 sit below 0.160 — this board is routed hard against its own floor
  everywhere. The via is looser than most of what is already on it, and it is a plain 0.6/0.3, so
  it adds no second drill size.
  **The trap that nearly shipped, worth knowing about:** the first placement, at (27.22, 51.31),
  looked far better on every number — 100 % pad coverage, 0.24 mm clearances. It was 0.144 mm from
  a letterform. **The front contact block is drawn as unnetted `PCB_SHAPE`s on F.Cu, not as tracks
  or zones**, so an obstacle model built from tracks + pads + zones cannot see it and will happily
  drop a via into the middle of the type. DRC caught it (`clearance … Polygon [<no net>] on F.Cu`).
  Anything that reasons geometrically about this board's front must include copper-layer graphics.

- [x] **[PCB] Cull SJ1**
  _(2026-07-30; DONE — the board sync landed and the tripwire cleared.)_ SJ1 is gone from the board:
  the only `SJ1` left anywhere in the `.kicad_pcb` is the word inside U1's Description text. DRC
  reports **0 `extra_footprint`** and `check_consistency` is green. The tripwire below is kept
  because it is the mechanism, and the next deliberate red should be built the same way.
  **What it was:** SJ1 was gone from the `.kicad_sch`, so the board
  carried a footprint the schematic did not know about, and `extra_footprint` was raised from
  `warning` to `error` in `.kicad_pro` so that shows up as a build failure rather than one line in a
  217-warning list. It was safe to raise: DRC reported **0 footprint errors** before this change, so
  SJ1 is the only extra footprint on the board — the board-only parts (MH1–4, MP1–4, TC1, …) carry
  the `board_only` attribute and do not trip it.
  **To clear it:** open the board, *Update PCB from Schematic* (SJ1 disappears), then *Cleanup
  Tracks & Vias → remove dangling*. Expected after: `extra_footprint` 0, and DRC back to its usual
  14 excluded errors. Both guards say the same thing today —
  `check_consistency` → *"on the BOARD but not in the schematic (a sync will DELETE these): SJ1"*,
  DRC → *"[extra_footprint] … error … @(13.3000 mm, 46.0000 mm): Footprint SJ1"*.
  **What the schematic edit removed** (six blocks, LF endings preserved, 400,716 → 396,212 bytes):
  the `SJ1` symbol instance, its two stub wires at (410.21,160.02)→(405.13,160.02) and
  (410.21,165.1)→(405.13,165.1), the two `global_label`s those stubs landed on (`VS` and `VDDIO2`),
  and the `solarglow:SJ1` lib_symbol. It was a self-contained island — nothing else touched it.
  Verified: ERC **identical** before and after (3 pre-existing excluded warnings on BTN/PC0/PC1,
  none introduced); netlist 67 → 66 components; `VDDIO2` is now exactly `C3.1 + U1.10`, as intended.
  The former verdict, kept because it is the reason this happened:
  **AVR64EA28 datasheet DS40002443A §2.2, 28-pin VQFN — pin 10 is `PD0`.** There is no `VDDIO2` pin
  anywhere on the package; the only supply pins are 18/24 (VDD) and 19/25 (GND), and every I/O is
  marked *"Pin on VDD Power Domain"*. One domain, no MVIO. The board agrees and has already half
  admitted it: `U1` pad 10 carries `pinfunction='PD0_10'` while the **net is still named
  `VDDIO2`** — the pin function was updated in the AVR-EA swap and the net name is a fossil.
  `firmware/board.h` line 27 says the same: *"10 PD0 (n/c) EA GPIO on the old VDDIO2 pad; SJ1 = DNP
  so it floats -> held by internal pull-up"*.
  So SJ1 is not merely unused — **bridging it shorts a GPIO to VS**, which is a footgun sitting
  0.26 mm from SC3 (a 1.8 F supercap) and 0.30 mm from D2. Cull it.
  **What the deletion actually is, measured:** SJ1.1 = `VS` @ (13.30, 45.05), SJ1.2 = `VDDIO2` @
  (13.30, 46.95). On the `VDDIO2` side it is a pure **spur** — C3.1 reaches U1.10 directly along
  y = 48.50 and up x = 7.83, and SJ1 hangs off that run via 7 segments back to the branch at
  (7.83, 48.50). Deleting the footprint cannot break C3↔U1.10. The **`VS` side is not a spur**:
  the B.Cu run (13.16,45.37)→(13.16,45.77)→(12.47,46.46)→(12.47,46.75)→(12.12,47.10)→(10.89,47.10)
  reads as a through-route that merely passes SJ1.1, and there are 41 VS zones besides. **Do this
  in KiCad, not by text surgery** — delete the symbol, Update PCB from Schematic, then
  *Cleanup Tracks & Vias → remove dangling*, and let the connectivity engine decide which copper
  was only ever SJ1's. Text-editing it risks orphaning VS copper that is carrying current elsewhere.
  **`C3` is NOT the other half of this fossil — keep it.** An earlier draft of this entry said it
  was, on the assumption that a 100 nF held charged on a pulled-up pin was costing meaningful
  energy. Computed rather than assumed, it is not: the part is `GRT155R71H104KE01D` (X7R 0402), and
  the MLCC insulation-resistance floor of 500 Ω·F ÷ 100 nF = 5 GΩ gives **0.66 nA at VS = 3.3 V**,
  ~0.8% of the documented 80 nA sleep *at the spec floor* and typically 10–100× better than that;
  the one-time cold-start charge is C·V² = **1.09 µJ** against a 2.7–7.8 J budget. Negligible.
  And PD0 is not a bare GPIO. **Datasheet Table 3-1, VQFN-28 column: pin 10 / PD0 = `AIN0`**, plus
  `AINN1` (AC1 negative input) and the alternate `TCA0 WO0`. `C24` on AIN1 (STO_SNS) is the
  **identical part number**, so AIN0/AIN1 already carry a matched 100 nF pair — the free adjacent
  ADC channel, pre-filtered. That is latent value, not dead weight; deleting it is a sch+board+BOM
  churn to reclaim one 0402 land and 0.66 nA.
  **Fix the NAME, not the part:** rename net `VDDIO2` → `PD0_AIN0`, and re-annotate C3 in the
  schematic as an AIN0 input filter rather than supply decoupling. That removes the actual cost,
  which is that the schematic currently asserts "supply pin needing decoupling" about an ADC input.
  **And record the gotcha, which is currently written down nowhere:** PD0 is the alternate
  `TCA0 WO0`, so **PD0 must never be driven as an output** — each full cycle into that 100 nF costs
  C·V² ≈ 1.09 µJ, i.e. ~1.1 mW at 1 kHz, which would swamp the entire energy budget. Firmware is
  correct today (`PORTD.PIN0CTRL = PORT_PULLUPEN_bm`, held as a pulled-up input) but `board.h`
  line 27 says only "(n/c) … held by internal pull-up" and does not say why that is mandatory.
  Files to follow: `PCB/README.md` (§5 do-not-get-wrong list, the BOM table row, the machine-place
  list), `README.md` (two mentions), `solar-glow-drh-design-notes.md` (three), `firmware/board.h`
  line 27, and U1's own schematic Description string, which still reads *"pin 10 (VDDIO2->PD0: SJ1
  now DNP)"*.

- [ ] **[PCB] C9 0402 → 0805 — LAND IS PLACED; the pad toe + thermal relief are still open**
  _(2026-07-30; the footprint swap is DONE, the two follow-ons at the end of this item are not.)_
  The board now carries `Capacitor_SMD:C_0805_2012Metric` at (35.52, 37.88, 90°), the
  `footprint_symbol_mismatch` tripwire has cleared, and `part_heights.py` has its `"C9": 1.25`.
  **The 3D side is verified and needs nothing** _(2026-07-30)_: the footprint references
  `${KICAD10_3DMODEL_DIR}/Capacitor_SMD.3dshapes/C_0805_2012Metric.step`, the same string C26/C27
  carry; that model is vendored, measures **2.00 × 1.25 × 1.25 mm**, and carries its colours
  (#614537 body, #D2D1C7 terminations), so it is not the grey-block case `LA_P47F` was.
  `render.py` reports **53/53 models resolve** and check [7] measures C9 among the 47 modelled
  B-side parts.
  **C9 is no longer DNP** _(2026-07-30)_: it is **47 pF**, `QSCT251Q470G1GV001E`, placed by the
  assembler. The value is derived rather than trimmed — the full derivation is in
  `PCB/PCB-side-notes-brace-direction.md` §5, and the short version is L = 0.958 µH by Greenhouse
  on the board's own 7 rails, +10–36 % from the ferrite, Ci = 50 pF, Cc = 6 pF, targeting
  AN11276 §4.2.1's 14.5 MHz single-tag nominal. 47 pF lands 14.45 MHz and never drops under the
  13.56 carrier anywhere in the ferrite range; the old 82 pF sat at 12.48 MHz enclosed, under the
  carrier in every scenario. It now appears in the populated renders, which is how it should read.
  _(While it was DNP it was correctly absent, and proving that took a controlled render pair: the
  board rendered twice unchanged moves 2 px over ΔE 40, and clearing only `dnp` put a single
  528 px blob, 20 × 37, on that land. That measurement is what confirmed the 0805 model was
  right, and it is why `render.py` now names the DNP set beside the resolve count — an empty land
  reads the same whether a part is DNP or its model silently failed.)_
  Still to do: **the +0.4 mm pad toe and the thermal-relief spokes** described at the end of this
  item. Kept below, as written, because it is the record of why 0805 and why that part:
  the schematic said
  `Capacitor_SMD:C_0805_2012Metric` (the same stock land C26/C27 already use) while the board
  still had `solarglow:C9`, and `footprint_symbol_mismatch` was raised `warning` → `error` in
  `.kicad_pro` so that is a build failure rather than one line in a 237-warning report. Targeted,
  not blanket: C9 is its only instance. `footprint_symbol_field_mismatch` was deliberately **left
  at warning** — it fires on any text difference (Description, MPN, Datasheet), which is
  documentation drift; a wrong *footprint* is a manufacturing fault.
  DRC now reads *"[footprint_symbol_mismatch]: solarglow:C9 doesn't match footprint given by symbol
  (Capacitor_SMD:C_0805_2012Metric) … error … @(35.6600 mm, 39.1400 mm)"*.
  **To clear it:** place the 0805 land (rotate 90°, grow vertically — see the clearances below),
  re-route the two short stubs to the coil, and re-run. Still outstanding with it: the
  `part_heights.py` entry and the pad toe/thermal-relief work, both below.
  Schematic side already carries `MPN QSCT251Q820G1GV001E`, `Supplier DigiKey`,
  `Supplier P/N 712-QSCT251Q820G1GV001ETR-ND`, and a Description that says DNP means *hand-fit at
  bench trim*, not unused. ERC unchanged (3 pre-existing excluded warnings, none introduced).

  The reasoning, kept because it is what the board edit has to satisfy:
  C9 is the NFC tank trim across the coil
  terminals (`LA`/`LB`) and the one part that gets reworked *repeatedly* — you tune resonance by
  fitting a value, measuring, and fitting another. On an 0402 that is miserable.
  **It must not move.** Its position and the loop area of its connection are part of the tank being
  trimmed. It does not need to: measured clearances are C28 1.17 mm to the left, U5 3.64 mm below,
  D5 3.41 mm above, so **rotating it 90° and growing vertically** takes 0805 with 2.4/2.1 mm clear
  (1206 would fit too, at 2.0/1.7). C9 already sits inside the hot-plate-safe band **x 26–46,
  y 31.5–58** — the only region with no supercap on the back and no PV cell on the front — 7.4 mm
  clear of SC2.
  **Part (DigiKey, live 2026-07-30): `QSCT251Q820G1GV001E`** — **Johanson Technology S-series**,
  82 pF, **C0G/NP0**, **±2%**, 250 V, 0805, body 2.03 × 1.27 mm, **thickness 1.17 mm max**,
  −55…+150 °C, DigiKey Features *"High Q, Low Loss, **Ultra Low ESR**"*, 3,522 in stock, $1.49 @1,
  DK `712-QSCT251Q820G1GV001ETR-ND`. Johanson's S-series is the family built for 13.56 MHz
  RFID/NFC tank tuning — this is the part for the job, not a general-purpose cap that fits.
  **Buy the spread, not the value** — 68 (±1%, 9,901) / 75 (±2%, 7,815) / 82 (±2%, 3,522) /
  91 (±2%, 3,543) / 100 pF (±1%, 5,160), **$8.65** for one of each, all in stock:
  `QSCT251Q680F1GV001E`, `QSCT251Q750G1GV001E`, `QSCT251Q820G1GV001E`, `QSCT251Q910G1GV001E`,
  `QSCT251Q101F1GV001E`.
  **SUPERSEDES an earlier pick of KEMET `C0805C820G5GACTU`, which rested on a wrong claim.** That
  entry said the high-Q RF families "are not stocked across the trim range". They are — the check
  behind that claim only queried Kyocera's `KGQ21` line, found gaps at 75/91/100 pF, and
  generalised from one family to all of them. Re-checked properly: Johanson S, Murata GQM and
  Kyocera AVX 600F are **each** stocked across all five values in 0805.
  **What the upgrade is actually worth, computed not asserted.** At 13.56 MHz an 82 pF tank has
  Xc = 143.1 Ω against a resonant L of 1.68 µH, and the PCB spiral's ~2 Ω ESR is ~93% of the loss:
  | | cap ESR | unloaded Q | loaded Q (IC ≈ 30) |
  | --- | --- | --- | --- |
  | 0402 C0G (today) | 0.20 Ω | 65.0 | 20.53 |
  | 0805 standard C0G | 0.10 Ω | 68.1 | 20.83 |
  | **0805 premium RF** | 0.030 Ω | **70.5** | **21.04** |
  | 1206 premium RF | 0.020 Ω | 70.8 | 21.08 |
  So the move is **+8.4% unloaded Q, +2.5% loaded** — real, worth $1.49, and *not* a step change in
  read range. Anyone expecting more should be told the coil is the limit.
  **0805 is the knee — do NOT go to 1206.** It buys +0.6% unloaded Q and costs more ESL, more stray
  capacitance to the pour beneath it (which shifts the tune), and clearance margin (1.7 mm vs
  0805's 2.1 mm). There is no rework benefit past 0805 either.
  **Non-magnetic terminations were considered and are not available.** Ni-barrier terminations sit
  in the tank's magnetic circuit — the same objection that killed exposing the coil to ENIG. A
  search of 0603/0805/1206 high-Q parts returned **zero** non-mag options in stock at any value, so
  this is closed, not ignored. The effect is in any case inside the part's measured ESR spec.
  Kyocera AVX **600F** (porcelain, the best ESR available) was the runner-up at $2.45–3.54 — 2× the
  price for the last +0.6% of unloaded Q, and its in-stock 75/91 pF are only ±5%, so the spread's
  tolerance would be inconsistent. Murata **GQM** is cheapest ($0.84–1.51, full ±2% spread) but is
  not flagged Ultra-Low-ESR.
  **Two things that must land with the footprint swap, or the enclosure is cut wrong:**
  (1) `enclosure/part_heights.py` needs an explicit **`"C9": 1.25`** — the package-generic 0805
  number that C26/C27 already use, not the part's own 0.88, because check [7] measures the declared
  height against the generic `C_0805_2012Metric` model and a 0.88 declaration would fail it. Leaving
  C9 on the `"C"` prefix default of 0.55 is the exact failure the file's own docstring warns about —
  the brace would be cut 0.70 mm too shallow. (2) Extend each pad's outer toe by **+0.4 mm** and put
  **thermal-relief spokes** on both pads: they land in the `LA`/`LB` pours, and a pad tied straight
  into a pour is why an iron feels like it never wets. Four 0.4 mm spokes are nothing against the
  coil's own inductance.

- [ ] **[PCB/BENCH] Six B-side test pads — the whole harvest chain is unprobeable**
  _(2026-07-30.)_ Auditing every net for probe access turned up the gap: **`GND`, `SRC`, `STO`,
  `SCL`, `SDA`, `UPDI` are reachable** (TP1, JP1, TC1, J1) and **nothing else is**. Missing, in
  bring-up order: **`VS`** (is the logic rail up at all), **`MID`** (the SC1–SC4 stack midpoint —
  if it drifts, a cell goes overvoltage, so this is a safety node, not a convenience one),
  **`LX_LOUT`** (the AEM10300 switch node — the one scope point that answers "is the boost
  running"), **`VINT`**, **`BUFSRC`**, **`STO_LDO`**. That is the entire harvester subsystem, which
  is also the project's #1 open gate (energy budget). Put them on **B.Cu**, which is 100% inside
  titanium and therefore costs nothing in artwork — the only reason the rail was ever considered.
  Candidate zone from the free-space map: **x 40–46, y 36–52**, clear radius 5.5 mm, which is also
  the hot-plate-safe band (see the C9 entry). Ø0.9–1.0 mm bare pads take a pogo or a probe tip.

- [ ] **[PANEL] Two tooling holes in the rail, so the card can be tested IN the frame**
  _(2026-07-30.)_ Pairs with the entry above and is the *safe* half of the "test points on the
  breakaway" idea. Two Ø1.5 mm NPTH in the 5.0 mm rail let a pogo fixture register to the panel
  and land on the B-side pads while the card is still attached — test as it arrives from PCBWay,
  then depanel. Free to add: `scripts/panelize.py` generates the panel, so this is a constant and
  an emitter, not a file edit.
  **Signals must NOT cross the outline, and that is settled, not a preference.** `edge_fit = −0.05`
  makes the board a *press fit* into the cavity, and all eight mount holes are plated **GND** with
  brass M2 screws into tapped titanium — the shell is bonded to GND at eight points. Any non-GND
  copper reaching the outline is a hard short once assembled. The design already made this call
  once: the only two nets crossing today are the plating stubs, **both GND**, both sitting in DRC
  as `copper_edge_clearance … actual 0.0000 mm`, *excluded*. Separately there is no room — the
  5.0 mm tab's four Ø0.5 bites leave four 0.50 mm webs plus the 1.00 mm bus corridor, and at a
  normal 0.2–0.25 mm hole-to-copper a 0.50 mm web has 0.0–0.1 mm left, under the board's own
  0.152 mm clearance floor.

- [x] **[SCH/PCB] U7 footprint identity — DISARMED; the two lands were the same land**
  _(2026-07-26; DONE.)_ The trap was real but the geometries were not actually in conflict. Comparing
  every stored coordinate, the board footprint was **exactly the library footprint, Y-mirrored (U7 is
  on B.Cu, the `.kicad_mod` declares `F.Cu`) and translated +0.15 mm in X** — pads *and* silk *and*
  courtyard *and* fab, uniformly. The apparent "asymmetric X" (−1.95 / +2.25) was that same +0.15
  offset on a symmetric ±2.1 land, and the "reversed Y order" was just the back-side flip. So the
  RAMXEED-verified land and the library land never disagreed; only the footprint's local origin did.
  Resolved by adopting the library frame with an origin compensation, so **no copper moved**:
  every local X −0.15, footprint origin 28.059412 → **28.209412** (which is the true package centre),
  `lib_id` → `solarglow:U7_DFN8`. Verified by recomputing the absolute position of all 26 pad and
  graphic vertices against the pre-change file: **zero changed**. The board footprint is now
  bit-identical to a fresh library placement at that origin, so Update-from-Library is a no-op and
  Update-from-Schematic-with-footprint-replacement is safe for U7. Schematic and board now agree on
  all 67 footprint assignments, and `check_consistency.py`'s footprint check is an **error**, not a
  warning, as of this change.

- [ ] **[PCB — housekeeping, low priority] 46 `solarglow:<refdes>` lib_ids have no backing
  `.kicad_mod`** _(noticed 2026-07-26 while settling U7.)_ The board (and the matching schematic
  `Footprint` properties) name footprints like `solarglow:C1`, `solarglow:R10`, `solarglow:U1` —
  one per refdes — but `PCB/solarglow.pretty/` contains only four files
  (`U7_DFN8`, `U9_SOT23_5`, and the two SCHURTER cells). Nothing is broken today: a `.kicad_pcb`
  stores each footprint's full geometry inline, so the lib_id is only consulted by
  *Update Footprints from Library* / footprint replacement — which simply finds nothing and leaves
  those parts alone. Two consequences worth knowing: (1) the sync trap this repo has been burned by
  is **narrower than it looks** — footprint replacement can only actually move the parts whose
  lib_id resolves, i.e. U7, U9, and the stock-library parts; (2) if anyone ever creates a file at
  one of those 46 names, it silently becomes authoritative for that refdes. Cheap fix if it ever
  matters: repoint them at the real stock-library lands (`Capacitor_SMD:C_0402_1005Metric`, etc.) in
  the schematic and re-sync. Not urgent — flagged so it is a known state, not a surprise.


- [x] **[SCH] C29 added to the schematic — board and netlist now agree** _(2026-07-26; DONE.)_
  `solarglow:C29` lib symbol + instance at (410.21, 261.62), Reference C29, Value 100nF, Footprint
  `solarglow:C1` to match the board, wired VS/GND with the project's stub-and-global-label pattern.
  Verified paren-balanced, 24,909 lines, zero bare LF *at the time* (the file was CRLF then; it became LF in the 2026-07-27 upload — see the repo item below).

- [x] **[BOM] C29 added to the master, and two stale rows corrected** _(2026-07-26; DONE.)_
  C29 is now its own row in `solar-glow-drh-v4_0-BOM.xlsx`, directly after C28. (An earlier note here
  said it should "join the existing 100 nF 0402 line, not a new row" — **that was wrong**: the sheet
  keeps one row per refdes and already carries nine separate rows for this same MPN, C5/C1/C3/C6/C12/
  C7/C8/C24/C28. C29 makes ten.) Subtotal is a hardcoded number rather than a formula, so it was
  updated by hand: **140.20 → 140.30**. Two corrections found while placing it:
  - **C28's Function read "FRAM VNFC decoupling"** — stale. That predates the 2026-07-23 back-power
    fix; U7 was re-railed to always-on VS and C28 followed it. Board pad 1 is on **VS**, not VNFC.
    Now "FRAM (U7) decoupling — on VS". (VNFC decoupling is C8's job, on U5, and C8 *is* on VNFC.)
  - **C1's Function** now names which pair it serves. Measured off the board: C29 pad 1 sits 1.00 mm
    from U1 pin 18 (VS) and 1.27 mm from pin 19 (GND); C1 pad 1 sits 1.97 mm from pin 24 and 2.32 mm
    from pin 25. So C29 serves 18/19 and C1 serves 24/25 — the split the decoupling finding asked for.

- [x] **[TOOLING] `check_consistency.py` was blind to 4 of the board's 71 footprints**
  _(2026-07-26; DONE — found while cross-checking BOM coverage against the board.)_ `board_footprints()`
  matched the lib_id with `"([^"]+)"`, which cannot match an **empty** lib_id — and **MP1–MP4** (the
  corner mounting pads) are stored as `(footprint ""`. They were silently dropped, so the map held 67
  of 71 refdes and said nothing about it. My "all 67 footprints agree" claim was really "all 67 that
  the regex could see." Fixed to `[^"]*`. The same pass added the flag that makes the board-only check
  correct rather than merely quiet: all four carry **`attr board_only`**, KiCad's own "exists only on
  the board, a sync must not delete it" marker, so they are *supposed* to be absent from the schematic
  and must not trip the delete-warning. The checker now exempts by that flag and **prints the exempt
  list every run**, so if one ever loses the flag it reappears as a real error instead of vanishing.
  (`NPTH_mech` is board_only too but has no Reference property, so a refdes-keyed check cannot see it.)
- [ ] **[COPPER] U1 has one decoupling cap for two VDD/GND pin pairs** — ⚠️ **looks STALE, re-check
  before spending effort on it**
  _(2026-07-26 copper audit; moderate effort.)_ Contrary to an explicit datasheet requirement, and it
  bears on the ADC noise floor — which now matters more than it used to, since the glow floor, the
  EEPROM floor and the caps-full gate are all decided from ADC reads. Worth pricing before fab.
  **2026-07-30, measured off the current board:** U1 now has **two**. Pin pair 18/19 has **C29 at
  1.46 mm**; pin pair 24/25 has **C1 at 2.42 mm**. C29 was added on 2026-07-26 (see the closed
  "[SCH] C29 added to the schematic" item above), which is almost certainly the fix for this very
  finding — the two items were never linked. Confirm the intent, then close this rather than adding
  a third cap. Full VS-cap census by distance to the nearest U1 supply pin: C29 1.46, C1 2.42,
  C23 14.94, C12 20.80, C28 23.01, C7 32.01, C4 33.87, C6 34.68 mm.

- [ ] **[COPPER] Tag-Connect keep-out violated by the ground pour**
  _(2026-07-26 copper audit.)_ B.Cu ground comes within **0.127 mm** of every TC1 contact pad against a
  **0.508 mm** datasheet keep-out. Paste on those pads is already fixed; this is the other half.

- [ ] **[COPPER — judgement calls, effort disputed by the verifiers]** _(2026-07-26 copper audit; all
  were pitched as "trivial" but re-rated as needing neighbour reroutes.)_ No analog net class (both ADC
  nodes sit at the 0.126 mm clearance floor against active nets); F.Cu pour under L2 and under 93 % of
  the switching-node copper, with B.Cu hugging LIN/LOUT at 0.20 mm; LIN/LOUT/BUFSRC at the 0.15 mm
  minimum width, adding ~47 mΩ in series with the inductor; CINT (C26) 12.3 mm of 0.15 mm track from
  the real VINT pin; STO feed to U8 pin 14 necking to 0.3 mm for 15.8 mm. Each is defensible to leave.

- [ ] **[COPPER — cosmetic/low]** _(2026-07-26 copper audit.)_ Stencil area ratio falls below the 0.66
  laser-cut floor for U1/U8/U5 at TI's recommended 0.125 mm foil (same conversation as the exposed-pad
  window-paning); four 45° copper corners and eight ~34° cusps where the gold frame clips the monogram;
  seven sub-micron degenerate track segments (I declined to strip these — no manufacturing effect and a
  small connectivity risk; note the audit's claim of 8 duplicate tracks does not reproduce, an
  exact-endpoint test finds zero); and `PCB/README`'s via-in-pad list is v3-era — two new
  via-touching-pad cases, zero true via-in-pad remaining.


- [x] **[COPPER] U9 moved to a genuine 5-pin land — the pin-map trap is now structurally impossible**
  _(2026-07-26; DONE.)_ U9 was on `Package_TO_SOT_SMD:SOT-23-6` for a 5-lead part, which is what let
  OUT be netted to a pad no lead touches. Now on project-local **`solarglow:U9_SOT23_5`** with
  standard numbering (1 IN / 2 GND / 3 EN / 4 NC / **5 OUT**, pad 5 opposite pad 1 — where the OUT
  lead actually lands). The land geometry is carried over verbatim from the routed SOT-23-6 pattern
  minus the vacant middle pad, so every remaining pad is bit-identical in position and **no trace
  moved**. Symbol renumbered to match and its 6th pin deleted; orphaned instance pin entry removed;
  `PCB/solarglow.pretty/U9_SOT23_5.kicad_mod` created so the lib_id resolves. Re-verified after the
  swap: copper lands on the OUT pad from both layers, 93 VS nodes joined to it, C23 and the MCU-side
  VS run both reachable, no stale copper at the old vacant land.
- [x] **[COPPER] AEM10300 CSRC ground return — FIXED, and it was fixed on 2026-07-26**
  _(closed 2026-07-27 after re-measuring; the work landed in the `3803c18` board upload and was never
  ticked off here.)_ The finding was real. At `2b65aef`, C25's (22 µF CSRC) GND pad sat on its **own
  99.4 mm² B.Cu island**, separate from the 2544.3 mm² main pour carrying U8's thermal pad — so there
  was **no B.Cu return path at all** between them, board-wide, and the return had to cross to F.Cu and
  back. That is what the "~42 mm of pour" figure was describing. The AEM10300 datasheet §14.1 is
  explicit here: *"The GND return path between the DCDC decoupling capacitors (CSRC - CSTO) and the
  AEM10300 thermal pad … must be as direct and short as possible."*

  **What fixed it:** a GND stitching via now sits at **(29.125, 56.15)** — 0.33 mm from the audit's
  suggested (29.18, 55.82) — and the island merged into the main pour. Re-measured on the current
  board by rasterising the B.Cu GND copper (pour + GND tracks) and running a shortest-path search:

  | | C25.GND → U8.EP, path *in copper* |
  |---|---|
  | `2b65aef` (audit) | **no path** — different islands |
  | `3803c18` onward  | **8.78 mm** (straight line 5.37 mm, 1.6×) |

  **Residual, and why I would leave it:** the audit's *second* suggested via at (25.12, 54.22) was
  never placed. It would not shorten the B.Cu path — both pads are already on the same island — it
  would only add a parallel return through F.Cu. **F.Cu is now a 47%-copper crosshatch**, so that
  parallel path is a mesh rather than a plane and buys materially less than it would have when the
  audit was written. The real return is the 8.78 mm run on solid B.Cu, and 1.6× detour on a
  low-power harvester's DCDC input loop is comfortable. Adding the via is optional, not indicated.

- [ ] **[COPPER — yours] U1 / U8 exposed-pad stencil apertures are 1:1 with the copper**
  _(2026-07-26 copper audit.)_ U1's EP is 2.65 × 2.65 mm (7.02 mm²) and U8's is 2.3 × 2.3 mm
  (5.29 mm²), each with a single full-size B.Paste aperture. IPC-7093 practice is to window-pane a
  thermal pad to ~50–80 % paste coverage in an array, so the part does not float on excess solder and
  outgassing has a path. **Deliberately not changed by me**: the right percentage depends on the
  stencil foil thickness the assembler actually uses (the audit separately flagged apertures falling
  under the 0.66 area-ratio floor at 0.125 mm foil), and PCBWay often supplies its own stencil data.
  Worth one question to them before editing the footprints.

- [ ] **[COPPER — yours] Two tight spots, each needing a part nudge rather than a reroute**
  _(2026-07-26 copper audit.)_ R10 and C8 pads sit **0.159 mm** apart on different nets — the
  tightest inter-component gap on the board. C13's pads leave a **0.075 mm** solder-mask sliver
  against the glow-window opening, below a typical 0.1 mm (4 mil) dam minimum, so the web there will
  likely not survive. Both want a small component move, which is why they are yours and not mine.

- [ ] **[COPPER — low value] Teardrops applied to roughly half the board**
  _(2026-07-26 copper audit.)_ 143 of 290 track-to-pad/via junctions have none. Teardrops are already
  enabled in the board settings, so this is a regenerate-and-refill in KiCad, not hand work. Cosmetic
  for reliability at this scale — do it only if you are in there anyway.


- [x] **[BOARD — FAB CORRECTNESS] DNP attributes corrected in BOTH .kicad_sch and .kicad_pcb**
  _(2026-07-26 PCB audit; DONE — attribute/metadata only, no copper touched.)_ The two files disagreed
  with each other and with intent. **U7** (MB85RC512TY FRAM) carried `(attr smd dnp)` in the .kicad_pcb
  though the schematic correctly had `(dnp no)`; cleared to `(attr smd)`. *(Consequence stated
  accurately: this did NOT threaten the fab output — `solar-glow-drh.kibot.yaml` marks the pick+place
  CSV "informational, the fab CPL follows the pre-order checklist", and the generated CPL in fact lists
  U7 and every other DNP part. The real point is that the schematic is UPSTREAM: on the next
  "Update PCB from Schematic" the board's stray flag would have been overwritten anyway, while SJ1's
  do-not-populate intent — which lived only in a Value string — would have been silently lost.)* **SJ1** was wrong in *both* files — `(dnp no)` in the schematic and a bare
  `(attr smd)` in the board, with the intent recorded only in its Value text; set to `(dnp yes)` /
  `(attr smd dnp)`, matching C9's in-BOM-but-not-placed pattern so its documented "(DNP — not ordered)"
  BOM row survives. Every part's sch and pcb flags now agree. Schematic edited byte-safe: 24,650 CRLF (the file was CRLF then; now LF)
  line endings preserved, zero bare LF. PCB/README's machine-place list corrected to match (SJ1 removed,
  Q2/R18 added).
- [x] **[BOARD — FAB CORRECTNESS] Paste removed from the hand-soldered PV and SC lands**
  _(2026-07-26, Devin's call; DONE — paste layer only, no copper and no mask touched.)_ The stencil
  now opens only where paste is actually wanted. Stripped **16 pads**:
  - **PV1, PV2** (solar cells) — **8 pads, not 4.** Worth recording, because the request said "all 4
    large pads": each cell has **four** pads, a Ø3.5 mm terminal *plus* a 4 × 3 mm tab 3.1 mm
    outboard, per polarity. Pasting the tab while sparing the terminal would make no sense, so all
    eight went.
  - **SC1–SC4** (supercaps) — 8 pads, 2 each, matching the request exactly.

  These are the largest apertures on the board by a wide margin: **≈ 366 mm²** (PV ≈ 86.5, SC = 280),
  about 1,200 0402 pads' worth. Both part families are hand-soldered and `exclude_from_bom`
  (the BOM calls the supercaps "solder to under-body pads"), so that paste was never going to be
  reflowed — it was solder volume waiting to float a hand-placed part. Copper and mask are unchanged,
  so every land hand-solders exactly as before. Board-wide SMD paste tally is now 176 pasted / 45 bare
  (was 192 / 29). Documented in `PCB/README.md` under the stencil note.

- [x] **[PCB] LED land pattern D2–D5 corrected — pads to X = ±1.55** _(2026-07-26; DONE.)_
  A and K moved from ±1.300 to ±1.550 local (C-C 2.60 → 3.10 mm), ±0.4 stagger kept — the
  stagger was always correct, the terminals are diagonal. Applied identically to all four
  footprints. **No re-routing was needed**: the old trace endpoints sat at the former pad
  centres, 0.25 mm away, which still falls inside the 0.65 mm-wide pads at their new
  positions — verified all 8 pads retain a trace endpoint within their bounds.

- [ ] **[PCB — IN PROGRESS] Re-space the board to the dual-fab envelope (PCBWay ∩ OSH Park)**
  _(2026-07-27; the DRU gate and board settings are DONE, the routing is not — **PCB CI is expected
  RED until it is**.)_ Goal: order the same board from either fab without re-checking anything.
  PCBWay for fast/cheap local prototypes and small batches; OSH Park **After Dark** (black FR4 +
  clear mask, verified from their docs) for the naked "midnight" variant.

  **The envelope is a genuine per-parameter intersection, not "OSH Park's rule sheet":**

  | | PCBWay | OSH Park | governs | gate |
  |---|---|---|---|---|
  | trace / space | 0.100 | **0.1524** | OSH Park | 0.152 |
  | drill | 0.200 | **0.254** | OSH Park | 0.254 |
  | annular | **0.150** | 0.127 | **PCBWay** | 0.1499 |
  | copper → edge | n/s | **0.381** | OSH Park | 0.381 |

  Annular inverts — OSH Park is *looser* there. Relaxing it to 0.127 "because that's what the OSH
  Park page says" would put the board out of spec at PCBWay.

  **Scope, measured rather than guessed — 1,444 copper pairs sit under 0.1524 mm, but 75% is free:**

  | between | count | |
  |---|---|---|
  | track/pad/via/zone ↔ **zone** | **1,083** | clears on a re-fill, no manual work |
  | track ↔ track | 212 | hand |
  | pad ↔ track | 87 | hand |
  | track ↔ via | 51 | hand |
  | pad↔via, via↔via, pad↔pad | 11 | hand |

  So the real worklist is **361 pairs**, and fewer edits than that since one nudged trace clears
  several. Spread across signal routing (SDA 19, UPDI 18, K2 17, SCL 16, INT1+INT2 27) rather than
  one bad corner. **The 2 pad↔pad pairs cannot be routed away** — they need a component move or a
  footprint change, so identify those first in case they constrain placement.

  **Order of operations:**
  1. ~~DRU gate + board `min_clearance`/`min_track_width`/`min_through_hole_diameter`/
     `min_via_annular_width`~~ — DONE. `min_clearance` had been **0.0**, i.e. nothing enforced
     spacing during interactive routing, which is *why* the board drifted to 0.126–0.145. It is
     0.152 now, so the router holds the line live instead of DRC catching it afterwards.
  2. ~~Fill All Zones~~ — DONE in the 2026-07-27 upload. Predicted ~1,083 of 1,444 would clear on
     the re-fill; KiCad came back with **420 violations**, so that held.
  3. ~~Re-verify the CSRC return~~ — DONE, **it survived**. C25.GND and U8.EP are still on the same
     island (2,609.7 mm²) and the return measures **8.87 mm** against 8.78 before (straight line
     5.37). The pour-fragmentation regression I flagged did not materialise.
  4. ~~Width-only pass~~ — DONE (see the sub-item below).
  5. **Route out what's left.** After the width pass: **146 segments** with sub-0.152 clearance to
     fixed copper (was 262) and **74** still under 0.152 wide (was 231). The U8 pocket is still a
     **re-route, not a re-width** — that corridor was 0.150 + 0.126 = 0.276 mm against the 0.304 mm
     now required.
  6. Fold in the two already-filed D2 items (the exactly-0.126 clearance, the anode across the
     light window) since the work is in that area anyway.
  7. **Zone housekeeping:** the re-fill left 3 orphan GND_B islands (3.71 / 1.51 / 1.09 mm², up from
     1). That is what the single `unconnected_items` error reports — GND_B unconnected to itself.
     Isolated ground copper: harmless electrically, untidy. Turning on island removal clears it.

  - [x] **DUAL-FAB COMPLIANCE AUDIT — rule by rule, both fab sheets** _(2026-07-27, against
    `85f3d64`; PCB CI green.)_ Checked every published rule, not just trace/space:

    | # | rule | limit (whose) | board | |
    |---|---|---|---|---|
    | 1 | trace width | 0.1524 (OSH Park) | 0 under | **PASS** |
    | 2 | clearance | 0.1524 (OSH Park) | 0 real¹ | **PASS** |
    | 3 | drill | 0.254 (OSH Park) | 0.300 PTH / 0.9906 NPTH | **PASS** |
    | 4 | annular ring | 0.150 (**PCBWay**) | exactly 0.150 | **PASS, zero margin** |
    | 5 | copper → board edge | 0.381 (OSH Park) | **0.000, ×2** | **FAIL** |
    | 6 | hole-to-hole | 0.127 | 0.4634 | **PASS** |
    | 7 | silk line width | 0.0762 hard / 0.127 rec | 0.100 min | **PASS**² |
    | 8 | mask web | 0.1016 (OSH Park) | 0.0750 B / 0.0801 F | **REVIEW** |
    | 9 | board size | — | 50.8 × 88.9 mm | **PASS** |

    ¹ the only sub-floor pair is LA↔LB at 0.000 — the NFC coil junction, intentional and filtered.
    ² 56 elements sit below the 0.127 *recommendation* but above the 0.0762 hard minimum; cosmetic,
      and the silk pass will pick them up.

    **Row 5 is the only hard failure, and it is the known one:** the two 0.4 mm plating-bus stubs
    crossing the outline at x = 25.4 (y −0.6…1.45 and 87.45…89.5). Required at PCBWay to feed
    electrolytic hard gold, prohibited at OSH Park, which needs 0.381 mm of pullback and offers ENIG
    only. **This cannot be edited into compliance — it is a product decision** (see below).

    **Row 4 deserves a note:** the uniform 0.6/0.3 vias give exactly 0.150 mm of annular ring, which
    is precisely PCBWay's stated minimum with nothing to spare. Widening the via pad to 0.65 would
    cost clearance board-wide on a board that was just re-spaced, so it stays — but it is the one
    parameter with no margin at either fab.

    **Row 8, characterised:** exactly one pad-to-pad web is short on B.Mask — **SC1.N ↔ D2.K at
    0.0750 mm** — plus one 0.0801 mm web inside the F.Mask artwork. Low severity: SC1 carries no
    paste (hand-soldered) so a merged opening there does not raise bridging risk, and the artwork web
    is cosmetic. Worth telling the fab rather than fixing.

  - [x] **REGRESSION FIXED: the width audit broke VNFC** _(2026-07-27; found by CI after #86 merged.)_
    Narrowing a trace can sever a connection when two segments never actually met — when they only
    *overlapped by virtue of their width*. Exactly one net on this board was held together that way:
    - The 0.0394 mm **VNFC** stub on B.Cu ended at y = 32.4610; the run it feeds sits at y = 32.6150.
      That is a **0.154 mm gap between endpoints**. At 0.300 mm wide, each half-width of 0.15 mm
      closed it with 0.146 mm to spare. At 0.152 mm the copper falls **0.002 mm short** and the net
      splits in two.
    - VNFC is the NFC tag's gated supply, so the break would have left **U5 unpowered** — silent,
      because nothing in firmware can sense it.
    - **Fixed at the cause, not the symptom:** the stub's end moved from y 32.4610 → **32.6150**, so
      it now lands on the run's centreline. The joint is geometric and no longer depends on width —
      the same edit would have been correct at any width. Tightest VNFC clearance after: 0.209 mm.
    - **Swept every net** the same way (per-net connected-component count, before vs after, tracks +
      vias + pads across both layers): **VNFC was the only one**. All others unchanged.

    Lesson for the next width pass: a narrowing is only safe once you have re-counted per-net
    connected components, not merely re-checked clearance. Width changes are not purely subtractive.

  - [x] **Full-board width audit — every trace justified or reduced to the floor** _(2026-07-27;
    DONE.)_ Went net by net asking whether the width buys anything: ampacity, IR drop, inductance,
    RF, or signal integrity. **564 segments normalised to 0.152 mm**, track copper 532 → 361 mm²
    (−32%). Two numbers decided almost all of it:
    - **Ampacity at the floor is 610 mA** (IPC-2221, 1 oz, 10 °C rise). The board's largest current
      is **ANODE at 64 mA** — four LEDs × ~16 mA at a full tank, (4.65 V − 2.25 V)/150 Ω. That is
      **10% of capacity**, and the IR drop over a 40 mm run is **8.2 mV**, which through a 150 Ω
      ballast shifts LED current by 0.05 mA out of 16. Ampacity binds nowhere on this board.
    - **Inductance depends on width only logarithmically.** 0.500 → 0.152 mm costs **+22–30%** on a
      5–20 mm trace. Length dominates; width is a weak lever even where inductance matters at all.

    **Kept wide, with the reason:**

    | net | mm | why |
    |---|---|---|
    | `LA` / `LB` | 0.300 | the trace **is** the NFC coil — width sets inductance, Q and self-resonance |
    | `LX_LIN` / `LX_LOUT` | 0.200 | DCDC switch node, the one place di/dt is real (10 µH at ns edges) |
    | `GND` | mixed | return path — and already 52.3 of 55.4 mm at the floor anyway |

    **Reversed on inspection, because the per-net heuristic was too coarse:** `SRC` (128 mm at
    0.375) is the *cell* input — DC, MPPT-sampled every 4.5 s; the converter's pulsed current comes
    from C25 on BUFSRC, not from this run, so it narrowed. Likewise one `BUFSRC` segment (the cap
    feed, not the switch node — it was violating against `LX_LIN`, so narrowing one fixed both at
    ~1% of loop inductance) and one `LB` segment at (33.98, 33.08), which is **outside the coil
    region entirely** — a feed trace, where +0.133 nH against a µH-scale coil is ~5 parts in 100,000.

    Result: **segments under 0.152 mm wide: 22 → 0.** Under-clearance 61 → **49**. Narrowing can
    only increase clearance, so nothing was created. Widths now: 781 at 0.152, 13 at 0.2 (the switch
    node), 93 at 0.3 (the coil), 1 at 0.4 (a GND stub).

  - [x] **The monogram's GND tie widened 0.150 → 0.200 mm** _(2026-07-27; investigated in full.)_
    Chasing the lone `unconnected_items` error (`Polygon [GND] on F.Cu @ (17.709, 46.104)` vs zone
    `GND_A`) turned into a useful map of how the front artwork is actually wired:
    - The F.Cu artwork is **351 `gr_poly` + 17 `gr_line`**. The monogram is drawn as ~0.108 mm
      scanline slivers at 0.1 mm pitch, so adjacent slivers overlap by ~0.008 mm to form the field.
    - **104 of the 351 polygons carry no net at all**; 247 are net GND. All 17 `gr_line` are GND —
      those are the perimeter frame, the bus taps, and the two plating stubs at x = 25.4.
    - The monogram field is **not** touched by the pour (the `optical_window` keepout forbids it,
      overlap exactly 0.00 mm²). It reaches GND through **one deliberate tie**: a `gr_line` at
      x ≈ 34.82 running y 46.45 → 47.60, i.e. from the table's lower-right corner down past the
      window edge (y 47.2) into the pour.
    - That tie was **0.150 mm — under the new 0.152 mm floor**, so it was a real violation of the
      dual-fab envelope independent of the connectivity question. Widened to **0.200 mm**, matching
      the hatch strand width so it reads consistently. Room was never tight: nearest non-GND copper
      is 0.608 mm (an LDRV4 via), so at 0.2 mm the clearance is 0.508 mm. Contact with the pour goes
      from 0.152 mm to 0.202 mm wide (overlap 0.0545 → 0.0747 mm²).

    **What this does not settle:** the copper is physically continuous — the tie genuinely bridges
    the field to the pour, verified by geometry — so the fab and the plating see one connected mass
    and hard gold reaches the monogram either way. KiCad still reporting the polygon as unconnected
    is most likely its connectivity engine not fully traversing graphic-to-graphic contact on copper
    layers, rather than a real break. **Confirm after the next Fill All Zones**: if the error
    persists at 0.2 mm with 0.2 mm of contact, it is a KiCad model artifact and belongs in the
    exclusions list with this note attached, not in the fix list. Do not "fix" it by moving copper
    until that is established.

  - [x] **`GND_B_DCDC_SOLID` added — solid return plane under the converter** _(2026-07-27; the zone
    is in the board, but it is **unfilled until you open KiCad and Fill All Zones** — KiCad computes
    `filled_polygon`, a text edit cannot.)_ B.Cu, net GND, **priority 1** so it wins the area from
    GND_B (priority 0), solid fill, rectangle **x 23.4–37.7, y 50.3–61.7 mm** (14.3 × 11.4 mm,
    163 mm²). That is the combined extent of **U8 + L2 + C25 + C26** (12.26 × 9.33 mm) plus 1.0 mm,
    so it covers the whole switching loop — input cap → converter → inductor → VINT cap — and the
    return between them. Inside that rectangle the hatch currently leaves **49.5 mm²** of copper;
    solid gives roughly **117 mm²**, so about **+68 mm² of return plane exactly where the di/dt is**.
    Pad-connection settings match GND_B (thermal relief, 0.2 gap / 0.25 bridge) so SB2 and SW2 stay
    hand-solderable; U8's exposed pad already carries `zone_connect=2` (solid), so the node that
    matters most is directly bonded either way.

    Why it was needed: the 2026-07-27 upload hatched B.Cu as well (GND_B 2874 → 1668 mm²). The CSRC
    return *survived* that — C25.GND and U8.EP stayed on one island and the path measures **8.97 mm**
    (8.78 solid, 8.87 after the first re-fill) — but it now runs through a 0.2/0.5 mesh rather than a
    plane. Connectivity was never the worry; impedance is.

  - [x] **Second width pass + 2 dangling stubs removed** _(2026-07-27; DONE.)_ 51 more widened to
    0.152, 8 more narrowed to buy clearance (VS ×3, VSENSE ×3, SDA, SCL), same rules as the first
    pass. Deleted two re-route leftovers KiCad flagged as `track_dangling`: **VSENSE** at
    (12.900, 42.416), 0.383 mm, and **SDA** at (16.271, 31.923), 0.176 mm. Both verified as true
    stubs first — one anchored end, one free end touching no same-net copper — so removing them
    cannot break a connection. Running totals: segments under 0.152 wide **73 → 22**, under 0.152
    clearance **71 → 61**.

  - [x] **Width-only pass — 246 edits, no copper moved** _(2026-07-27; DONE.)_ Purely `(width …)`
    values: no trace re-routed, no via/pad/net touched, so there is no collateral to review.
    - **157 widened to 0.152.** Only segments with ≥ 0.153 mm to *fixed* copper were touched —
      clearance to the pour does not constrain this, because the pour re-fills around whatever it
      is given. That distinction is what made 157 safe instead of 59.
    - **89 narrowed to buy clearance**, each to the *widest* width that still clears 0.152 with
      5 µm to spare, snapped down to 0.005 mm. Rounding down only adds clearance, and it keeps the
      power rails fat: the 0.5 mm runs came back at 0.435–0.465, not at the floor.
    - **Deliberately not narrowed**, whatever the clearance gain: `GND` (return path), `LA`/`LB`
      (NFC coil — Q depends on the conductor), and `LX_LIN`/`LX_LOUT`/`BUFSRC`/`SRC`/`VINT` (the
      AEM10300 switching loop, where width is loop inductance, not ampacity). 16 segments that
      *could* have been resolved this way were left alone for that reason.
    - Ampacity is never the constraint here — 0.152 mm at 1 oz carries ~0.7 A and nothing on this
      board exceeds ~20 mA — so the only reasons to keep a trace wide are the ones above.

  **Also worth knowing:** 106 pairs measure between 0.100 and 0.126 mm — below even the *old* floor
  — while DRC reports clean and only 11 exclusions are stored in the project file. Either they are
  artifacts of my pad-geometry model or they are real and being missed. Step 4 settles it; do not
  chase it before then.

- [x] **[PCB — AESTHETIC] F.Cu ground pour crosshatched** _(2026-07-27 upload; DONE.)_
  45° crosshatch, **0.2 mm strand / 0.5 mm gap** (0.7 mm pitch, 46 cells/inch), smoothing level 3.
  Reads as a woven texture in the hand and blends to flat tone past ~700 mm — the intended "fine
  stitch that melts." The parameters dodge both traps that a finer 0.15/0.4 setting would have hit:
  the hole is 0.25 mm² against `hatch_min_hole_area` 0.15 (a 0.4 mm gap gives 0.16 mm², close enough
  to the cull threshold to risk silently filling back to solid), and the 0.2 mm strand clears the
  zone's `min_thickness` 0.15 by 0.05 mm (an at-minimum strand gets pruned wherever geometry pinches
  it, which shows up as blotches in a texture). **Copper balance held up far better than projected:**
  F.Cu pour 2660 → 2028 mm², so front/back is **0.84** (was 1.06 solid; a 0.5/1.0 hatch would have
  been 0.37) — the warp concern on the 0.51 mm core is largely moot. Note only ~45% of the card face
  shows it: PV1/PV2 cover 1932 mm² and the optical window another 146. Knock-on effects are filed
  separately below (gold-frame merge).

  **DESIGN INTENT — read this before "cleaning up" the pour.** The crosshatch is a *functional
  ornament*, and specifically a **sub-mask** one: it is meant to be read softly THROUGH the matte
  black solder mask, giving the face a woven texture instead of a flat matte plane interrupted by
  traces. **89.6% of it (1816.9 of 2028.1 mm²) is under mask by design**; only 211.2 mm² is exposed,
  and that is hatch falling inside the monogram / frame / ornament mask windows. Three things follow,
  none of them obvious from the board file alone:
  - The effect depends on the mask **telegraphing the 35 µm copper step**. Anything that flattens
    that — a thicker mask, a fab "evening out" the surface — kills the feature. The plating request
    now says so explicitly.
  - It is **not** a plating surface and must not be mask-opened. Do not "fix" the pour by exposing it.
  - Electrically it is still just the F.Cu ground pour. Nothing here is decorative-only copper that
    can be deleted; changing it changes the ground plane.

- [x] **[SCH] Removed an orphaned no-connect flag** _(2026-07-27; DONE.)_ ERC reported
  `no_connect_dangling` at (490.22, 397.51) mm — a flag sitting in empty schematic space with no pin
  or wire within 3 mm (nearest symbol is U9, 25.4 mm away). **Not caused by the U9 six-pin deletion**,
  which was the obvious suspect: the flag is present at `2b65aef`, before that edit. It surfaced only
  because the committed `ERC.rpt` was stale (dated 2026-07-25) and got regenerated. Deleted; 18 → 17
  no-connects, file paren-balanced.

- [x] **[REPO] The schematic is now LF, not CRLF** _(2026-07-27 upload; recorded, no action.)_ The
  upload rewrote all 24,909 line endings CRLF → LF, which is essentially the entire 49,818-line
  schematic diff. **Semantically identical** — same 160 lib_symbols, same 67 components, same values,
  footprints, no-connect count and global labels; verified structurally, not by eyeballing the diff.
  Nothing to fix, but worth recording so nobody "restores" CRLF and produces another whole-file diff.
  The byte-safe **CRLF** preservation discipline referenced in older entries here is obsolete; the
  rule that still matters is byte-safe editing (don't reflow the file), now against LF.

- [x] **[PCB] GND_B refilled — the two stale-fill errors are gone** _(2026-07-27 upload; DONE.)_
  D2 pad A and D5 pad K no longer sit inside the stored pour (overlap 0.000 mm², was ~0.091 each).
  Both now clear it by **0.1265 mm**, measured against true roundrect pad geometry. That is the
  `clearance-hard-floor` value plus 0.5 µm — normal for a zone fill (KiCad fills to exactly the
  effective clearance), and it passes. Worth knowing the zone's own `clearance` is set to 0.254 mm
  but the achieved gap is 0.126: the `.kicad_dru` custom rule resolves as the effective clearance and
  overrides the zone setting, so raising the zone number alone would not widen it. PCB CI went green
  with this, and `Generated/` regenerated at `fdb4d18` after being 8 commits stale.

- [ ] **[PCB, PRE-FAB] D2's ANODE trace still crosses D2's own light window — the reroute fixed
  only the short** _(2026-07-25 LED audit; re-verified against the 2026-07-27 crosshatch upload.)_
  The 2026-07-27 reroute added a detour at x = 18.201 that cleared the `shorting_items (K2/ANODE)`
  error — **that half is done**. But it only touched the run east of D2. The diagonal off D2's A pad,
  `(14.8, 44.3) → (16.176, 42.924)`, is untouched and still passes **0.536 mm** (copper edge) /
  0.636 mm (centreline) from D2's emitter centre (16.1, 43.9) — inside the Ø2.1 aperture (r = 1.05),
  so it still shadows the brightest part of D2's cone. Checked whether the upload made it worse: it
  did not — that trace was already 0.2 mm wide, so the geometry is unchanged. (The older "0.636 mm"
  figure in this item was a *centreline* measure; 0.536 mm is the same trace measured to its copper
  edge, which is the number that matters optically.) **D3/D4/D5 remain clear** — they route straight
  out of the window, the documented rule. Fix: take D2's anode out of the window the way its siblings
  do, rather than across it.

- [ ] **[PCB, MARGIN] D2's new K-pad clearance is exactly 0.126000 mm — zero margin**
  _(2026-07-27 upload.)_ The reroute put the ANODE run's left edge at x = 18.101 and D2 pad K's right
  edge at x = 17.975: a gap of **precisely** the `clearance-hard-floor` minimum. DRC compares `>=`, so
  it passes and CI is green — but this is the exact hazard the `.kicad_dru` header itself calls out,
  where the annular floor was deliberately set to 0.1249 "so an at-spec via does not coin-flip on
  floating-point rounding." The clearance rule carries no such margin, so this one sits on a knife
  edge across KiCad versions and rounding. Not a fab risk (PCBWay's floor is 0.1 mm, so there is 26%
  headroom); it is our own gate that is fragile. ~0.025 mm more would settle it — and the D2 anode
  rework above is the natural time to do it.

- [x] **[PCB/FAB] Plating request renamed the gold area by mask opening, not by connectivity**
  _(2026-07-27; DONE — and my first read of this was overstated, corrected below.)_ The hatch rework
  enlarged the F.Cu pour outline to 0.5 mm from the board edge (was ~3.65 mm in), so the pour now
  overlaps the gold artwork by **157.3 mm² — 52% of the frame + ornament copper**, where it used to
  graze it over 0.069 mm². The request's old phrase "all connected copper on F.Cu" therefore stopped
  naming anything useful. **But the consequence was ambiguity, not expense:** a fab plates only what
  the mask exposes, and this crosshatch is a *sub-mask* ornament — **89.6% of it (1816.9 of
  2028.1 mm²) is under solder mask** and cannot be plated at all. Only 211.2 mm² is exposed, all of
  it inside the monogram / frame / ornament windows where plating it alongside them is correct. An
  earlier version of this item said the old wording would have gold-plated ~2,400 mm² of pour; that
  ignored the mask and was wrong. The monogram field is untouched either way (0.00 mm² overlap — the
  `optical_window` keepout excludes the pour). Request now names the gold area by **F.Mask opening**,
  which is what physically governs it, and tells the fab the pour is decorative and must stay masked.

- [ ] **[PCB — aesthetic, your call] Should the frame contain the texture, or should the texture run
  over it?** _(2026-07-27.)_ `hatch_border_algorithm` is `hatch_thickness`, so the pour edge is
  hatched rather than solid, and the enlarged outline runs the mesh right up to and over the gold
  frame. Reading it as a solid border that frames the texture means pulling the zone outline back off
  the artwork. Purely a look decision — no electrical or fab consequence either way now that the
  plating request is defined by mask opening.

- [ ] **[PCB/FAB — durability] Define the gold area on a user layer instead of in prose**
  _(2026-07-27.)_ `User.1` is empty. Drawing the gold region there and plotting it as its own gerber
  makes the area artwork rather than a paragraph, so it cannot drift the next time a pour outline
  moves — which is exactly what just happened. Adds one file to the fab package, so it needs a
  deliberate yes before the order goes out.

- [ ] **[3D] Component models — 45 of 72 done, and the rest is what the enclosure work needs**
  _(2026-07-28; the passives and the fit-critical bodies are done, the small actives are not.)_
  The renders and, more importantly, **the brace / back-shell fit check** depend on footprints
  carrying `(model ...)`. At the start only **17 of 72** did, all KiCad stock parts; every custom
  `solarglow:*` footprint had none, so KiCad's 3D viewer and any STEP export showed a bare board.

  **Done — 22 assigned, mechanically, not by guesswork.** Every one of C1/C3/C5–C9/C11/C12/C24/C29,
  R1–R4/R10–R12/R14/R17/R18 and FB1 sits on one land: **pitch 1.02 mm, pads 0.59 × 0.66**. Measured
  against the footprints that already had models — `C_0402_1005Metric` is pitch 0.96 / 0.56 × 0.62,
  `C_0603_1608Metric` is 1.55 / 0.9 × 0.95 — that is unambiguously **0402 class on a slightly
  enlarged hand-solder land**. They now point at the stock 0402 C/R/L models. **39 of 72.**

  **Done — the 6 bodies that set the enclosure envelope.** KiCad ships no model for any
  `solarglow:*` footprint, so `scripts/make_3d_models.py` generates them with cadquery:
  `SCHURTER_SCPC_SS17` (39.0 × 17.0 × 1.70) on SC1/SC3, `SCHURTER_SCPC_WS17` (28.5 × 17.0 × 1.70)
  on SC2/SC4, `SM141K06TF` (42.0 × 23.0 × 1.50) on PV1/PV2, into `PCB/solarglow.3dshapes/`. These
  are **maximum-envelope clearance solids, not cosmetic models** — every dimension traces to a
  footprint `descr` or a datasheet line, and the script header records which. **45 of 72.**

  > **Open question the models raised: the supercap locator tabs are not modelled.** The footprint
  > `descr` puts them ~2.75 mm past each end. Modelled flat and in-plane they push all four caps
  > past the board edge (SC1 by 1.00 mm, SC3 by 0.83, SC4 by 0.90, SC2 by 0.10) — but `PCB/README.md`
  > calls them **folded**, and the footprint courtyard covers only the cell. So a flat extension is
  > the wrong shape and shipping it would invent an overhang for the enclosure to design around.
  > **Until a real cell is measured, treat the envelope near the two short edges as unverified.**

  **The 17 that correctly have no body:** MH1–4, MP1–4, SB1–4, SJ1, SW2, TP1, JP1, TC1. Holes,
  solder bridges and pad-only features. Not a gap; do not "fix" these.

  **Attached 2026-07-28 — 8 more solids, board is now 53 of 72.** Every remaining
  height was already in this repo, so nothing here needed a fresh datasheet dig:

  | part | solid | source of the height |
  |---|---|---|
  | **D2–D5** | `LA_P47F` 3.4 × 1.9 × **0.83** | brace height map §2; outline from the BOM table + datasheet p.12 |
  | **U1** | `AVR64EA28_VQFN28` 4.0 × 4.0 × **1.00** | DS40002443A §38.5, "Overall Height A" max |
  | **U8** | `AEM10300_QFN28` 4.0 × 4.0 × **0.85** | DS-AEM10300-v1.4 §15.1 Fig. 17, 0.800 ± 0.05 |
  | **U3** | `ADXL367_CC12` 2.2 × 2.3 × **0.87** | `PCB/README.md` BOM table, corroborated by the height map |
  | **U5** | `NT3H2211_XQFN8` 1.6 × 1.6 × **0.50** | `PCB/README.md` + height map, "SOT902-3 … verbatim" |
  | ~~**J1**~~ | — | **closed 2026-07-28: J1 is DNP.** A UPDI header, never populated — leads get hand-soldered to the pads if it is ever wanted. A DNP part needs no clearance solid, so this is not a gap |

  `python3 scripts/make_3d_models.py` generates them; `--attach` writes the `(model ...)` lines into
  the board, byte-safely and idempotently. The attach was held back while the FB1 land was drawn in
  KiCad — a KiCad save drops anything written underneath it — and **ran on 2026-07-28 once that
  landed**, taking the board from 45 to **53 of 72**. CRLF was preserved (129,143 lines, zero bare
  LF) and DRC was byte-for-byte unchanged: 14 violations, all excluded, 0 unconnected, 0 parity.

  **What legitimately still has no body: 19 footprints, and that is the finished state** — MH1–4,
  MP1–4, SB1–4, SJ1, SW2, TP1, JP1, TC1 (holes, solder bridges, pad-only features), the unnamed
  `NPTH_mech` hole set, and **J1, which is DNP** (UPDI header; hand-soldered leads if ever wanted).
  Nothing that gets populated is missing a body. **This item is done.**

  > **A stock model is not automatically the right model.** KiCad ships
  > `QFN-28-1EP_4x4mm_P0.4mm_EP2.4x2.4mm.step` and it is prettier than a box — but measured it is
  > **4.000 × 4.000 × 0.770 mm**, 0.23 mm short of U1's max and 0.08 mm short of U8's. For a solid
  > whose entire job is "does the brace clear it?", understating height is worse than having no
  > model, so both get a box at their own documented maximum.
  >
  > **And U1 and U8 are not the same height** — 1.00 vs 0.85, each off its own datasheet. They share
  > a 4×4 QFN-28 land and even a footprint *name*, which is exactly why one shared "QFN-28 4×4"
  > solid looked reasonable and was wrong by 0.15 mm on U8. It no longer exists.

  > **The two QFN-28 lands are correct, and they are not identical.** Measured on the board: U1's
  > exposed pad is **2.65 × 2.65**, matching DS40002443A §38.5's nominal D2/E2 of 2.65; U8's is
  > **2.30 × 2.30**, matching the AEM10300 datasheet's recommended board layout (§15.2 Fig. 18)
  > exactly. Both right for their own part — but they shared the footprint name `solarglow:U1`, so
  > one name described two different lands.
  >
  > **Fixed 2026-07-28.** U8 now has its own `solarglow:U8_QFN28`, written from its actual board land
  > and checked by loading it back through KiCad (29 pads: 14 × 0.8 × 0.2, 14 × 0.2 × 0.8, EP
  > 2.3 × 2.3, 4.000 pad-centre span). Board `lib_id` and both schematic Footprint fields (placed
  > instance + `lib_symbols` cache) point at it; U1 keeps `solarglow:U1`. It is a real library file in
  > `PCB/solarglow.pretty/`, so it is also the first of these two that a library update could safely
  > act on. _(Most `solarglow:*` footprints are still board-embedded only, with no library file —
  > that is pre-existing and unchanged here.)_

  For the enclosure the *height* is the whole point, so a plain box at the datasheet dimension beats
  a pretty model at the wrong one.

- [x] **[ENCLOSURE] U7 relief pocket removed — the floor is a true uniform 1.00 mm** _(done 2026-07-28)_
  Two docs described U7 as a **SOIC-8 at 1.75 mm** and built on it: `enclosure/README.md` called it
  "the single tallest part" and specced a **7.8 × 5.4 × 0.05 mm relief pocket** at board (28.1, 37.3)
  purely to clear it — machined into the STEP marked *"Send this to the fab"* — and
  `PCB-side-notes-brace-direction.md` §2 called it the "tall pole" brace thickness derives from.

  The v4 board carries the **DFN-8 at 0.90 mm MAX** (`U7_DFN8.kicad_mod` `descr`, RAMXEED
  DS501-00087-1v0-E p.21), which clears the 1.00 mm floor by 0.80. The pocket cleared nothing.

  **Removed by arithmetic, not deletion.** The generator's `U7_H` is now 0.90, so
  `U7_POCKET = max(0, U7_H - cap_H)` evaluates to 0 and the existing `if U7_POCKET > 0` guard skips
  the cut. The mechanism stays for the next part that genuinely needs local relief.

  **Verified on the regenerated solid:** volume 6524.4817 → 6526.5447 mm³, **+2.0631 mm³** back,
  against a nominal pocket of 7.8 × 5.4 × 0.05 = 2.1060 — the 0.043 difference is the R1.0 corner
  fillets. Bounding box unchanged. STEP and STL are regenerated and committed.

  Two blockers had to be cleared to regenerate at all, and both were the same bug class — a path
  that only ever existed on one machine:
  - `OUT` was hardcoded to `/mnt/user-data/outputs/`, so the generator could not write its own STEP.
    Now defaults next to the script, `OUT_DIR` overrides.
  - The maker-text fonts pointed at `/home/claude/fonts/`. The engraved glyphs are cut into the
    titanium, so the font is part of the deliverable and not substitutable — JetBrains Mono is now
    **vendored in `enclosure/fonts/`** under its SIL OFL 1.1 licence (bundled, as the OFL requires),
    with `MAKER_FONT_DIR` to override. Missing fonts now fail loudly instead of mid-build.

- [ ] **[BOARD — DO THIS IN KiCad] Regenerate teardrops after the PV1/PV2 re-centring**
  _(2026-07-28.)_ Re-centring the solar cells moved their SRC pads, so **6 F.Cu teardrop zones on
  the PV1/PV2 pads were deleted** rather than translated — a teardrop's shape is derived from a
  pad/track relationship, and that relationship changed, so shifting the polygon would have shipped
  a wrong-shaped fillet. The board is DRC-clean without them (teardrops are a robustness nicety,
  not connectivity). **Open the board and run Tools → Add Teardrops before plotting** — which
  `PCB/README.md` already lists as a pre-plot step. Count is 298 now; it was 304 before.

- [x] **[BOARD] Solar cells re-centred between their mounting holes** _(done 2026-07-28)_
  The cells' inner edges sat exactly on the centreline of the four middle screw holes — PV1's top
  edge at y 28.50 against MP1/MP2 at y 28.50, PV2's bottom edge at y 60.40 against MP3/MP4 — so a
  screw head would foul the cell corner nearest the glow window.

  | | corner → hole centre | vs Ø3.8 head (r 1.90) |
  |---|---|---|
  | before | 1.400 mm | **interferes 0.500 mm** |
  | after | 1.877 mm | grazes 0.023 mm |

  **PV1 → (25.40, 15.750)** (−1.25 mm), **PV2 → (25.40, 73.150)** (+1.25 mm). All eight corners are
  now equidistant at 1.877 mm, which is what "even" means here. **Centring is provably optimal** —
  it maximises the minimum clearance, so no other position does better.

  > **It does not fully clear, and that is a fastener question, not a placement one.** Clearing both
  > ends needs 2 × 1.285 = 2.569 mm of slack; the hole box offers 2.50. The 0.023 mm residual assumes
  > the head is at its **Ø3.8 maximum** — DIN 84 is a max with negative tolerance, so a real screw
  > measures under it and clears. If you want it guaranteed rather than tolerance-dependent, spec a
  > head of **Ø3.75 or less**; the alternative is moving MP1–MP4, which re-opens the 8-hole pattern
  > the shell was verified against.

  Carried with the move: the F.Cu GND/SRC feeds on 5 tracks, and one **GND stitching via** at
  x 46.334 that PV1's Pt pad landed on top of — it shifted the same −1.25 mm, which preserves its
  original relationship to the pad. That via was caught by DRC as an SRC/GND **short**, not by eye.

- [ ] **[ENCLOSURE] Regenerate the 2D drawing — its Detail B still shows the removed pocket**
  _(2026-07-28.)_ `...-DRAWING.pdf/.png` was not regenerated with the STEP, so it draws a floor
  relief pocket the model no longer has. **The STEP governs, so the part is correct**, but the PDF
  goes to the shop — `enclosure/README.md` now carries a line to add to the order saying so. The
  real fix is to re-run `...-DRAWING-gen.py`, which still writes to a hardcoded
  `/mnt/user-data/outputs/` path (same bug the CAD generator just had; fix it the same way).

- [ ] **[BOARD — ACTION NEEDED] FB1 needs its 0603 land drawn; CI is red until it is**
  _(2026-07-28. Found while assigning 3D models; the 0603 choice was deliberate and simply never
  reached the copper.)_ The decision to make FB1 a **0603** bead exists in **three** places —
  `solar-glow-drh-design-notes.md` L157 ("a 0603 ferrite FB1"), the BOM (`BLM18PG221SN1D`; Murata's
  `BLM18` series is 1608 metric = 0603), and even the schematic symbol's own Value string
  (`"ferrite *0603"`) and Description ("Ferrite bead 0603"). The one field never updated was the
  **Footprint**, so schematic and board both still carried `solarglow:C1` — pads 0.59 × 0.66 at
  pitch 1.02, the 0402 land shared with C1/C24/C29/R17/R18. A real 0603 land is 0.9 × 0.95 at
  pitch 1.55 (see C13). A 0603 body there sits with its terminations ~0.165 mm outboard of the pad
  centres and almost no fillet.

  **Done here:** the schematic now names `Inductor_SMD:L_0603_1608Metric` (both the placed instance
  and the cached `lib_symbols` copy). The other 17 `solarglow:C1` references are untouched.

  **Still to do — in KiCad, by hand. It is NOT a drop-in: the land does not fit where FB1 sits.**
  Measured against the actual copper (pcbnew, 2026-07-28), the widened land lands 0.075 mm from
  U9's left pad column — under the 0.152 mm dual-fab floor, on **both** pads:

  | land | pad1 → U9.1 (STO_LDO) | pad2 → U9.5 (VS) | → board edge |
  |---|---|---|---|
  | today's 0402, at (2.10, 54.65) | **0.220 mm** | 0.430 mm | 1.770 mm |
  | IPC 0603, same centre | **0.075 mm** ❌ | **0.075 mm** ❌ | 1.625 mm |
  | IPC 0603, centre (1.95, 54.65) | **0.225 mm** ✓ | 0.225 mm ✓ | 1.475 mm |

  So **move FB1 0.15 mm in −X, to (1.95, 54.65)**, and give it a 0603 land. Either vintage works,
  and they are **geometrically interchangeable here** — FB1 is rotated −90°, so the dimension facing
  U9 is the pad's 0.95 mm cross-width in both, and both put pad2's outer edge at y 55.875:

  - today's `Inductor_SMD:L_0603_1608Metric` — pads 0.875 × 0.95 at ±0.7875, pitch **1.575**
  - what this board's other 0603s draw (C13/C22/C23/C25, an older library cut) — 0.9 × 0.95 at
    ±0.775, pitch **1.55**

  Both satisfy both gates: parity compares the footprint *name*, and check [4]'s 0603 band is
  1.45–1.75 mm. Matching C13 keeps every 0603 on the board identical; placing the library part
  fresh is less work. Either way the clearance result above is unchanged, it restores exactly the
  clearance FB1 has today (0.225 vs 0.220), and it needs **no rerouting**: the
  existing STO and STO_LDO track ends at (2.100, 54.140) and (2.100, 55.160) still terminate inside
  the enlarged pads, and U9 is untouched. Placing the library footprint also brings the correct
  `L_0603_1608Metric.step` model with it.

  A narrower house land (cross-dimension 0.80 instead of 0.95, shifted only 0.10) buys 0.250 mm
  instead, but costs a `solarglow:L_0603` footprint that the schematic then has to name in place of
  the stock library part — more custom geometry for 25 µm. Not worth it.

  This deliberately leaves **two red gates** that name the work and clear themselves when it is done:
  - `kicad-cli pcb drc --schematic-parity` → `footprint_symbol_mismatch: solarglow:C1 doesn't match
    footprint given by symbol (Inductor_SMD:L_0603_1608Metric) — Footprint FB1`
  - `scripts/check_consistency.py` → check [4], `FB1: BOM orders a 0603 part but the board land is
    0402`

  The 3D model on FB1 is still the 0402 one; placing the library footprint swaps it to
  `L_0603_1608Metric.step` automatically.

  > **Why this is the whole argument for the 3D/model work.** Nothing in the toolchain caught this.
  > KiCad's schematic parity only compares the schematic to the board, and those two agreed —
  > *with each other, and both were wrong.* The BOM was the only copy that was right, and no check
  > read it. Chasing 3D models is what surfaced it, because a model forces the question "does the
  > part we ordered actually fit the land we drew?". Check [4] in `check_consistency.py` now asks
  > that question of every two-pad part on every CI run.

- [x] **[CI/AUDIT] Went through all 14 excluded DRC findings — two were hiding something**
  _(2026-07-28; DONE. Method: `kicad-cli pcb drc --severity-all --refill-zones`, KiCad 10.0.5.)_

  **Retired permanently — CI is now strictly tighter, with zero change to what passes:**
  - **Both broad regex filters deleted from `solar-glow-drh.kibot.yaml`.** They were redundant
    *and* dangerous. Redundant because `kicad-cli` reads only `.kicad_pro` `drc_exclusions`, and a
    bare run already returns all 14 findings with `excluded=true`; KiBot's filters only ever ADD
    exclusions (`kibot/pre_drc.py` → `apply_filters`). Dangerous because they matched by error
    *type* + a generic message regex, not by instance: `'edge clearance'` swallowed **every**
    `copper_edge_clearance` anywhere on the board, `'Tracks crossing'` every crossing. A new short
    at the rim or a new crossing would have vanished in CI. Verified after removal: 14 violations,
    **all still excluded**, 0 unconnected.
  - **The `unconnected_items` exclusion deleted from `.kicad_pro`** — dead since the GND island fix
    above. `drc_exclusions` is now 14 entries for 14 findings, one-to-one.

  **The 14 that legitimately stay:** 2 plating stubs crossing the outline at x = 25.4 (required for
  hard gold), 1 courtyard overlap + 7 NPTH-inside-courtyard (TC1 under SC1), 3 silkscreen clips,
  1 LA/LB coil junction.

  **Finding 1 — TC1 is 100% underneath SC1, and nothing said so.** Pad cluster
  (12.215, 15.18)–(14.385, 18.62), **5.465 mm inside** SC1's outline, both on B.Cu. TC1 is *the
  primary programming path* (`PCB/README.md`). Once the supercap is soldered, a TC2030-MCP cable
  cannot reach it. The geometry was an accepted decision; the **assembly-order consequence was
  undocumented**. Now a warning block in `PCB/README.md` → "Finishing the board by hand":
  **flash before fitting SC1**, or load J1. Not a defect — but it was one bad assembly order away
  from a bricked-feeling board.

  **Finding 2 — 3 of the 4 LED orientation markers will not print.** Each `D2`/`D3`/`D4` B.SilkS
  marker is a 1.6 × 0.15 mm segment = **0.2400 mm²**, and the area clipped by the B.Mask window
  (14.445, 40.3)–(36.345, 47.5) is **also 0.2400 mm²** — the whole thing. **D5 survives only
  because its marker sits at x = 36.7, 0.355 mm past the window edge.** That asymmetry is the tell
  that this was never intentional. `PCB/README.md` calls a flipped LED "the single most common PCBA
  defect on this board", so losing 3 of 4 orientation marks is worth something.
  **Not fixed — it needs a judgement call**, because the window spans the whole LED row: there is
  no spot within ~3.6 mm of D2/D3/D4 that is outside it. Options: (a) move the three markers below
  y = 40.3 or above y = 47.5 and accept the distance, (b) notch the B.Mask window around each
  marker, (c) leave it and rely on `led-orientation-D2-D5.png`, which is what actually gets handed
  to the assembler today. **(c) is the status quo and is defensible — but it should be a decision,
  not an accident.**

- [x] **[COPPER] The GND net was in two pieces — a 45.2 µm gap on B.Cu, not a monogram problem**
  _(2026-07-28; DONE, verified against KiCad 10.0.5.)_ The `unconnected_items` DRC error that turned
  PCB CI red reported **"Zone GND_A [GND] on F.Cu ↔ Polygon [GND] on F.Cu @(17.7091, 46.104)"**, which
  reads like a monogram-artwork defect. It is not. KiCad names one member of the floating cluster as
  the marker endpoint, and the cluster's real severance is on the **back**: a 13.69 mm² GND_B pour
  island (x 8.858–15.266, y 32.904–42.145, carrying **C1 pad 2**) cut off from the main pour by a
  **45.2 µm gap at (15.2658, 32.9834)**. The GND net had exactly two clusters.

  **Why it could not simply be bridged.** The corridor there is 0.449 mm — pinched between the MID
  via at (15.2908, 33.5) above and the VS track at y = 32.675 below — and a 0.152 mm track at
  0.152 mm clearance needs 0.456 mm. Short by **7 µm**. Lowering the bridge made it worse
  (0.143 → 0.123 → 0.103 mm); no legal stitching via exists either, because both pours are hatched
  so a 0.6 mm pad cannot find copper in U1's fanout.

  **The fix: move the MID via up 50 µm, then bridge.** The via is a plain layer change with both
  tracks vertical at x = 15.2908, so moving it to y = **33.55** carries the whole junction and keeps
  MID geometrically continuous (verified: MID stays **1** connected piece, area unchanged at
  26.2366 mm²). Corridor opens to 0.499 mm; a 0.152 mm B.Cu GND bridge at
  **(15.2, 33.0) → (15.38, 33.0)** then clears the via by 174 µm and the VS track by 173 µm.
  Result: **unconnected 1 → 0, violations 14, all excluded** — the pre-existing set, nothing new.

  **CI had to learn to refill.** KiBot builds `kicad-cli pcb drc --severity-all` with **no
  `--refill-zones`**, so it checks the last *saved* fill. Moving a via makes the stored fill stale and
  the via then reads as a clearance error against a pour that would recede on any refill (0.1025 mm
  vs GND_A, 0.1329 mm vs GND_B). `check_zone_fills: true` is now set in
  `PCB/solar-glow-drh.kibot.yaml` — it fills for the checks and plots, then restores, so CI never
  rewrites the board. This also makes CI agree with the board's own documented command in `CLAUDE.md`,
  which has always used `--refill-zones`. **Refill zones in KiCad before judging a DRC result here.**

  > **Lesson worth keeping: a geometric model is not KiCad's connectivity model.** Four independent
  > analyses (and my own) concluded the 241-polygon monogram plate was floating, all by running
  > union-find over `gr_poly` only. Wrong: deleting the 0.200 mm `gr_line` tie at x = 34.82 takes
  > unconnected **1 → 2**, so that graphic *does* carry connectivity. The only thing that settled any
  > of this was running the real checker. `kicad-cli` is installable from the KiCad PPA — use it
  > before moving copper on the strength of a shapely result.

- [x] **[FAB] PCBWay fabrication panel — the stubs finally connect to something**
  _(2026-07-28; DONE.)_ The two plating stubs at x = 25.4 had been drawn for a panel rail since v4
  began, but no panel existed, so on a 1-up board they ended 0.4 mm outside the outline and connected
  to nothing — an ENIG-only run would have left them dead copper and the face with no wear surface.
  `scripts/panelize.py` now derives the panel from the committed board; CI runs it and plots the fab
  set into `Generated/panel/`.

  **65.6 × 103.7 mm, 1-up.** Moat 2.4 mm, rail 5.0 mm, two 5.0 mm break tabs centred on x = 25.4,
  8 × Ø0.5 mm mouse bites, and a 1.0 mm GND bus ring on the frame joined to both stubs.

  **The ring is mask-opened along its whole length**, which was nearly missed: a bus buried under
  soldermask gives the plating rack nothing bare to clip, so it would have been decoration. Cost of
  exposing all of it is ~319 mm² of copper in reach of the gold bath ≈ 6 mg of gold, under a dollar,
  on material that is routed away — priced in rather than engineered around.

  **Derived, not duplicated.** A hand-maintained panel file would be a byte-for-byte copy of a
  9.7 MB board that has to be re-synced on every copper edit — precisely the drift the repo's
  one-fact-one-home rule exists to stop. So the panel is a script output, and the board file stays
  1-up (the 3D view, pcbdraw renders and iBOM keep showing a card). The script is purely additive
  apart from replacing Edge.Cuts, which was verified by diffing the panel minus every generated
  object against the board minus Edge.Cuts: **identical**.

  **Two constants differ from v0's working panel**, both because v0 had no rail copper and this one
  does: rail 3.0 → 5.0 mm (a 3 mm rail cannot hold a bus plus panel silk with any margin; 5 mm is
  also what fabs expect, at ~11% more panel area), and tab 3.0 → 5.0 mm (v0's bite pattern puts hole
  edges 0.15 mm either side of x = 25.4; the wider tab opens a **1.0 mm hole-free web** for the bus
  at 0.30 mm drill-to-copper, and still fits two bites per side).

  Left off deliberately: fiducials, tooling holes, copper thieving. The first two want a wider rail
  than the bus leaves, and the board is hand-finished, not machine-placed.

- [ ] **[MIDNIGHT — THE DECISION THAT GATES THE REST] Hard gold, or one truly identical file?**
  _(2026-07-27; revised 2026-07-28 — the panel changed the price of option (a).)_
  The compliance audit above found exactly one hard failure: the two 0.4 mm plating-bus stubs
  crossing the outline at x = 25.4. They are **required at PCBWay** (electrolytic hard gold needs a
  path to the panel rail during plating) and **prohibited at OSH Park** (0.381 mm pullback, ENIG
  only). No edit satisfies both — it is a product call:

  **(a) Keep hard gold. PCBWay orders the panel; OSH Park orders the 1-up set minus two objects.**
  Production keeps its wear surface. The panel above did most of the work here: the PCBWay side is
  now a finished, CI-built artifact rather than something to remember, so what is left is a 2-object
  delete on the OSH Park side only. That delete is still manual — automating it (a `--variant
  oshpark` mode on `panelize.py`, or a `check_consistency.py` assertion that the OSH Park upload
  differs by exactly those two objects) would close the gap entirely and is maybe twenty lines. Cost
  as it stands: one thing to remember, on one of the two fabs.

  **(b) Drop hard gold, delete the stubs, ship ENIG everywhere.** One file, genuinely
  interchangeable, nothing to remember. Cost: the monogram table becomes ENIG (~0.05–0.1 µm gold)
  rather than electrolytic hard gold (~0.5–1.5 µm). Worth being honest about the real difference:
  hard gold exists for **connector insertion wear**, which a monogram never sees. ENIG is still
  gold-coloured and perfectly serviceable for handling; it tarnishes sooner over years. `PCB/README`
  currently says "do not ship without it", which was written when the bus had no downside.

  **(c) Keep the stubs and let OSH Park route through them.** Not recommended — they cut copper at
  the board edge, which risks burrs and edge shorts on a card people handle.

  Everything else about the midnight variant is a fab *order option*, not artwork: substrate colour,
  mask colour, thickness, and whether the Ti shell is fitted. So this one decision is the whole
  remaining gap.

- [x] **[COPPER] VINT / EN_STO_CH necked back to 0.15 mm through the U8 pocket** _(2026-07-26; DONE.)_
  The 2026-07-26 board upload widened 39 segments from 0.15 to 0.20 mm — VINT ×24, EN_STO_CH ×12, plus
  one each on VS / STO_SNS / LX_LOUT. That broke `clearance-hard-floor` (0.126 mm) in **11 places**
  around U8 / R17 / C26, and it turned PCB CI red for three commits before anyone noticed. The cause
  is arithmetic, not routing: +0.05 mm of width is +0.025 mm per side, and every violation came back
  at 0.101–0.104 mm — i.e. exactly 0.022–0.025 mm short of the floor. The neighbouring copper had been
  placed for the board's documented uniform 0.15 mm trace/space (see the `.kicad_dru` header), so
  0.20 mm does not fit there. 0.101 mm is also right *at* PCBWay's stated 0.1 mm floor with zero
  process margin. Fixed by necking **only the 9 congested segments** (8 VINT + 1 EN_STO_CH, matched
  one-to-one against the CI violation list) back to 0.15 mm — standard practice for a run passing
  between pads — and leaving the widening on the other 30 segments, where it is legal and harmless.
  **Confirmed by CI at `b674f68`: DRC errors 15 → 4.** All 11 cleared. The 4 that remain are exactly
  the two KiCad-requiring items above — 2× `shorting_items` for D2's anode/K2 short, and 2×
  `clearance 0.0000` for D2.A / D5.K against the stale `GND_B` fill. **PCB CI stays red until both
  are done**, and the D2 reroute forces a refill anyway, so they are one sitting.

- [ ] **PCBWay orders** — confirm both replies sent (`W567099ASH69` bare fab, `T-H70W567099A` PCBA);
  get the LED package dimension answer (1.25 vs 1.9 mm) and the merged PCB+PCBA total; ensure the PO
  uses the confirmed MPNs.

- [ ] **BOM completeness — recount the machine-place BOM against the v4 net** _(audit find,
  2026-07-11)._ D10/D11 (v3 comparator-supply OR diodes) were removed with the U4 comparator; only LEDs
  D2–D5 remain as diodes, so the earlier "42" count is stale. Root `README.md` + `PCB/README.md` order
  table/counts were "fixed to 42" off the pre-redesign list and likely carry it too — re-verify against
  the recomputed v4 count, then regenerate the `-BOM-assembly.xlsx` master (binary; owner: Devin).
  Note **Q2 + R18 are now new machine-place parts** to include.

- [ ] **DRC/ERC prose vs the committed reports** _(audit find)._ The board is DRC/ERC clean (0
  unexcluded errors), but `PCB/README.md` + `solar-glow-drh-design-notes.md` describe "~61
  marginal-band warnings" present in neither committed report. Decide whether the two-tier `.kicad_dru`
  rules load in the run, then align the prose. Minor: the ERC `isolated_pin_label` (PC0/PC1) +
  `endpoint_off_grid` (JP1/TP1) aren't catalogued.

- [ ] _(Low)_ **`PCB/README.md`'s parts table is a hand-maintained duplicate of the BOM master** and has
  now drifted twice (it was still listing `AVR64DD28-I/STX`, `TPS22918DBVR`, the SOIC-8 FRAM and
  pre-longevity-pass passives when caught on 2026-07-25). It was regenerated from the xlsx and marked
  as a dated derived snapshot, but the structural fix is to **generate it in CI** from the master
  (kibot already regenerates `Generated/fabdocs/…-bom.csv`) or to cut it down to a pointer plus the
  order-time hazards. Until then, re-check it whenever the BOM changes.

- [ ] _(Cosmetic)_ **C13 schematic `lib_id` is still `solarglow:C11`** (clone leftover); surfaces as
  Part="C11" in the CI BOM. Fixing means repointing the instance to a `C13` lib symbol — mind the
  MPN-grouped BOM when doing it.

## Enclosure — `enclosure/…-backshell-…-cad.py`, `enclosure/brace/`

- [ ] **[BLOCKER before machining] Human-verify the rear maker's-mark orientation.** Render committed
  at `docs/solar-glow-drh-maker-mark-preview.png`. Numeric checks can't catch a mirror/flip error.
  First-pass read: right-side-up + horizontally mirrored (consistent with the intended left-to-right
  flip); still needs the real physical/STEP flip confirmed. Knob: maker-mark
  `aff.scale(xfact=-1, yfact=1, …)` (set `yfact=-1` for a top-bottom flip).

- [ ] **Front solar-panel fence** — concept only. Panel height known (**cell 1.2 mm ± 0.3 mm**,
  SM141K06TF datasheet p.1 + p.3 drawing — caliper-check the actual cells before cutting fence height;
  the ± 0.3 mm spread is wide for a melted-in fit). Still blocked on attachment (M2 screws / adhesive /
  snap-fit) and direction A (full-perimeter, recommended) vs B (per-panel rings).

- [ ] Add the maker's mark to `enclosure/README.md` once the wording is locked.

- [ ] Confirm the committed `.step`/`.stl` match the current generators (running a generator clobbers
  its STEP/STL).

- [ ] **[geometry] Brace↔shell mating walls disagree by 0.05 mm** _(audit find, 2026-07-11)._ The brace
  models the flat cavity walls 0.05 mm inboard of where the shell places them, so the brace edges sit
  **0.10 mm** off each true wall — double the intended ~0.05 mm no-rattle contact the brace's fit
  relies on. Shell is source-of-truth; resolve the brace rail coords (or add `edge_fit` to the shell
  `_cav_inner`), then regen. (`…-backshell-…-cad.py` vs `…-diffuser-brace-cad.py`.)

- [ ] **[geometry] Floor relief re-key — now likely a relief DELETE (U7 went DFN)** _(audit find)._ U2
  (the v3 ALD910025 balancer) is gone, and U7 (MB85RC512TY FRAM, at (28.1, 37.3) B.Cu) is the **0.90 mm
  DFN** since the repackage — not the 1.75 mm SOIC-8 the pocket was sized for — so at 0.90 mm it needs
  no relief, like the ~0.9 mm U8 QFN. Re-derive the tallest rear part (U9 SOT-23 / the 0805 caps) and
  most likely delete the pocket. `…-backshell-…-cad.py` still carries `U2_POS = (30.10, 37.64)` for the
  deleted part; re-key/rename or remove, then regen the STEP/STL and update the derived drawing / README
  NOTE-7 pocket-description copies. PCB is frozen truth.

- [ ] **[geometry] U7's 3D model is the wrong package and is rotated 90°** _(noticed 2026-07-26 during
  the footprint-identity fix — anything that reads part height from the board STEP is reading this.)_
  The board footprint still points at
  `${KICAD10_3DMODEL_DIR}/Package_DFN_QFN.3dshapes/DFN-8-1EP_6x5mm_Pitch1.27mm.step`, left over from
  the old `Package_DFN_QFN` identity. Two problems: it is a **6 mm(X) × 5 mm(Y)** body while the land is
  **5 mm(X) × 6 mm(Y)** (so it renders rotated 90°, overhanging ~0.5 mm one way and under-filling the
  other), and it models an **exposed pad** the LCC-8P-M05 does not have. `solarglow:U7_DFN8` declares
  no model at all, so an Update-from-Library would strip U7 from the 3D/STEP export entirely — which
  is worse, since a missing part reads as "no collision". Fix properly before the enclosure pass:
  either add a correct model to `U7_DFN8.kicad_mod` or substitute a generic 5×6×0.9 mm block. The
  reference is deliberately left in place until then. Height impact is small (the KiCad DFN model is
  ~0.9 mm, which happens to match), so this is a footprint/outline error, not a height error.

- [ ] **[geometry] Repoint the brace generator to the v4 board + fill `part_height`** _(audit find)._
  `…-diffuser-brace-cad.py` line 54 hardcodes a v3_0 PCB path (an absolute path that also doesn't
  resolve here), so its pocket map is still v3. `part_height()` has entries only for U2/U6/U1/U3/U5 —
  the v4 additions fall through to the 0.60 default, too shallow for the tall ones (U9 LDO SOT-23 ~1.45,
  L2 2520 ~1.0, the 0805 caps C26/C27 ~1.25, the 0603 bulk caps C4/C13/C25 ~0.9, **Q2 SOT-23 ~1.1**;
  U7 is the 0.90 mm DFN — no longer tall). Repoint to the v4 board, drop the U2 entry, add
  U7/U9/L2/Q2 + a 0603-cap height, then regen the brace STEP/STL and confirm no pocket collisions /
  thin-wall merges broke.

- [ ] **Fab drawing still renders the retired locator pillars** _(audit find)_ + NOTE 4 (Ø3.2
  recesses), contradicting the pillar-free STEP — and it's the file attached to the PCBWay CNC quote.
  De-pillar `…-backshell-…-DRAWING-gen.py` and regenerate the PDF/PNG. (Also low: several generator
  docstrings still cite the pre-redesign floor 0.95 / cavity 1.85 / two locator pillars, and "four" vs
  "two" outboard rails.)

- [ ] **`PCB/PCB-side-notes-brace-direction.md` still calls U7 the tall pole at "SOIC-8 / 1.75 mm"**
  _(repo audit 2026-07-25)._ U7 has been the 0.90 mm DFN since the repackage, so that doc's height
  table and any brace-thickness reasoning derived from it are stale. Left untouched on purpose —
  it folds into the enclosure pass with the other geometry items (floor-relief re-key, brace
  `part_height` map), which all need re-deriving from one recomputed tallest-part list.

- [ ] _(Cosmetic)_ brace drawing silhouettes still show the pre-DFM-clip outline.

## Locked — do NOT re-open

- Board electrically frozen; PCB change = brace reprint, not shell re-machine.
- Enclosure STEP stays **analytic-sharp**: r1.0 internal corners are a DRAWING
  spec; do **not** enable `tool_relief` (produces a faceted STEP the fab rejects).
- East cavity lip pinched to 1.0 mm over y10–72 (NFC detune) — do not widen.
- NFC tuning at bring-up needs the brace **removable** — don't defeat it.
- Supercap footprints are a **hybrid**: SC1/SC3 = SS17 land (3-153-440, 39 mm), SC2/SC4 = WS17
  land (3-153-438, 28.5 mm); flat under-body pads, asymmetric widths = polarity key. The old REV-J diagonal-pad land is WRONG -- never reuse.
- Ti-6Al-4V (Grade 5); grounded M2 bosses tie the body to GND.
- **NFC contact is offline-first.** The full vCard is **embedded** in the tag (`text/vcard`
  NDEF, `nfc.c`), read RF-powered by the phone with the card's supercap flat and **no
  reception** (the dead-signal courtroom case). A URL / App Clip is only ever an OPTIONAL
  rich-content extra -- **never** a dependency for the contact import. Do not swap the embedded
  vCard for a URL-only record.
- **Physical button — deliberately NOT fitted** (the accelerometer tap is the only actuator). This is
  a design decision, not a loose end. To add a hardware button in a future revision: route **pin 3
  (PA5)** to a momentary switch to **GND**; firmware reads it **active-low** (LOW = pressed) — `gpio_init`
  already enables PA5's internal pull-up. The schematic keeps a `BTN` label on PA5 as the on-board
  record of that pin; its lone-label ERC note is intentional. No power/analog net is affected.
- **Intentional / do-not-fix (so a future BOM/DRC pass doesn't re-flag them):** the R5/R6
  "VSENSE div" (and similar) value fields are deliberate house-style labels, not errors; the
  origin `NPTH_mech` footprint carries real non-plated mounting holes by design.
