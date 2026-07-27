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

- [ ] **[ENCL] U7 shell-pocket recheck — the last piece of the FRAM repackage**
  _(sch + BOM + board land + footprint identity + DNP flag are all DONE & verified; the DFN land is
  placed, routed, 0 unconnected.)_ **Enclosure knock-on only:** U7 is now the 0.90 mm DFN (was the
  1.75 mm SOIC), so the backshell's dedicated 0.95 mm floor pocket is likely deletable — see the
  geometry items under Enclosure.

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
- [ ] **[COPPER] U1 has one decoupling cap for two VDD/GND pin pairs**
  _(2026-07-26 copper audit; moderate effort.)_ Contrary to an explicit datasheet requirement, and it
  bears on the ADC noise floor — which now matters more than it used to, since the glow floor, the
  EEPROM floor and the caps-full gate are all decided from ADC reads. Worth pricing before fab.

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
