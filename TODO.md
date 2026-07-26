# Open items — SOLAR-GLOW DRH

A cross-domain tracker so nothing slips between the firmware, PCB, and enclosure
handoffs. This is an **index of what is left**, not a spec — canonical values
live in the source files it points to (see the "Where the truth lives" table in
`README.md`). Check items off in the GitHub UI as they land; **completed items are
culled** — the record lives in git history + the `solar-glow-drh-design-notes.md`
addenda.

_Board freeze status (updated 2026-07-25): the 2026-07 audit round reopened the
netlist and it is now closing again — Q2/R18 (the cold-start-deadlock buffer) and
the FRAM VS re-rail are placed, routed, and verified on the board; the only
pending board edit is the U7 footprint-identity swap (+ DNP-flag clear). A PCB layout change still means
a brace reprint, not a shell re-machine._

_Completed & culled 2026-07-25 (see git history + design-notes addenda for the
full reasoning): the AVR64DD28→AVR64EA28 family swap + firmware port; the U5 NFC
and U6 load-switch (→TPS22917) silicon audits; the U7 FRAM DFN-repackage and the
VS-rail back-power fix (schematic + firmware + board all landed — the U7
footprint-identity swap and the FRAM bench-verify are still open, see the items
above); the Q2/R18 cold-start-deadlock buffer (schematic + firmware + board); the
passive longevity/precision upgrades (X7R / AEC-Q200, 0603 & 0805 upsizes,
thin-film dividers); the full live DigiKey/Mouser BOM sourcing pass; the
SUN-threshold derivation and the solar-cell-thickness resolution; and the
STO_LDO island / led_sweep / MPN-grouped-BOM work._

## Cross-domain (link two+ teams — easiest to forget)

- [ ] **[SCH→PCB+ENCL] U7 FRAM footprint-identity swap + DNP clear + shell-pocket recheck**
  _(sch + BOM + board land all DONE & verified — the DFN land is placed, routed, 0 unconnected;
  what remains is the footprint identity, a stray flag, and the enclosure.)_ In KiCad: **Change
  Footprint U7 → `solarglow:U7_DFN8`** (`PCB/fp-lib-table` registers the lib; reopen the project
  first) — the board still carries the old `Package_DFN_QFN:DFN-8-1EP_6x5mm_P1.27mm_EP4x4mm` identity,
  which the swap resolves. The **same step clears U7's stray DNP flag**: the #73 upload left U7
  `(attr smd dnp)` — accidentally Do-Not-Populate — while the schematic says populate, so
  Change-Footprint / Update-PCB re-syncs `dnp=no` (or untick it manually). Re-snap the 3 signal stub
  ends to the new pad centers if needed, re-DRC (confirm both the "Do not populate settings differ"
  and the footprint-mismatch warnings clear). **Enclosure knock-on:** U7 is now the 0.90 mm DFN (was
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

- [ ] **[COPPER — optional cleanup] U9 sits on a SOT-23-6 land for a 5-pin part**
  _(2026-07-26; the electrical defect is FIXED — this is the tidy-up.)_ The OUT-on-the-wrong-pad bug
  is resolved (symbol OUT = pin 6, board pad 6 = VS), and pad 5's paste aperture is removed so the
  vacant middle land cannot form a loose solder ball under the package. What remains is cosmetic:
  the footprint still carries a 6th land for a part with 5 leads. **Do not simply delete pad 5** —
  the symbol has a pin 5, so deleting the pad orphans it and KiCad will complain on the next netlist
  update. The proper cure is to move U9 to a genuine `Package_TO_SOT_SMD:SOT-23-5` footprint and
  renumber the symbol to the standard 1 IN / 2 GND / 3 EN / 4 NC / 5 OUT, where pad 5 sits opposite
  pad 1 exactly where the OUT lead lands — which also makes the original mistake impossible to
  repeat. Check first whether that footprint's pads sit at the same X as the current ±1.1375 mm; if
  they are narrower, the three STO_LDO/GND/VS connections need touching up, which makes this a
  moderate job rather than a swap. Low priority: the board is electrically correct as it stands.

- [ ] **[COPPER — yours] AEM10300 CSRC ground return runs the long way round**
  _(2026-07-26 copper audit; you said you'd take this one.)_ C25's (22 µF CSRC) GND pad sits on a
  B.Cu ground island whose only layer transition is ~11 mm away, so the return to U8's thermal pad —
  6 mm in a straight line — travels ~42 mm of pour. This is the input side of the DCDC's high-di/dt
  loop, and the AEM10300 datasheet §14.1 is explicit: *"The GND return path between the DCDC
  decoupling capacitors (CSRC - CSTO) and the AEM10300 thermal pad … must be as direct and short as
  possible."* Fix is a couple of stitching vias near **(25.12, 54.22)** and **(29.18, 55.82)**.
  ⚠ I measured the nearest non-GND copper at **0.281 mm** from the first location and 0.465 mm from
  the second — both legal against the 0.126 mm floor but tighter than the audit claimed, so place
  them with the pour visible and DRC live rather than from these coordinates alone.

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
  BOM row survives. Every part's sch and pcb flags now agree. Schematic edited byte-safe: 24,650 CRLF
  line endings preserved, zero bare LF. PCB/README's machine-place list corrected to match (SJ1 removed,
  Q2/R18 added).
- [ ] **[PCB, PRE-FAB] LED land pattern D2–D5: pads sit 0.25 mm too far inward** _(2026-07-25 LED audit;
  full derivation in the design-notes LED-audit addendum)._ The `solarglow:D2..D5` pads are at
  **C-C 2.60 mm** (centers ±1.30) and **0.65 mm wide**; the ams-OSRAM reverse-mount recommended land
  (E062 3010 19B-01, datasheet p.13) is **C-C 3.10 mm** (centers ±1.55) and **0.50 mm wide**. Root cause:
  the drawing's `2.6` is the **inner-edge-to-inner-edge** span, not a pitch — confirmed by the outer span
  `3.6` ((3.6−2.6)/2 = 0.50 pad) and decisively by the stencil view (`2.65`/`0.65` = a 0.025 mm per-side
  reduction off 2.6/0.7, which only parses if 2.6 is an inner span). Consequence vs the real terminal
  (spans r 1.25→1.70 per p.12): our pad covers **83 %** of the terminal with a **−0.075 mm toe deficit**
  (the terminal overhangs the pad's outer edge) and protrudes 0.075 mm into the Ø2.1 optical aperture;
  the correct land covers 89 % with a +0.10 mm toe. **Not fatal — it would still solder** — but it is a
  real land deviation on the card's marquee feature, and the board is not fabbed yet, so fix it now.
  **Fix:** move each pad to **X = ±1.55** (keep Y = ∓0.375–0.40 — the diagonal stagger is CORRECT and
  matches the package's diagonal terminals), optionally narrow to 0.50 mm; then re-route the 8 stubs
  (ANODE + K2/K3/K4/K5) and re-DRC. _(Stagger was audited and is right — do not "fix" it.)_

- [ ] **[PCB, PRE-FAB] D2's ANODE trace crosses D2's own light window** _(2026-07-25 LED audit)._ On
  B.Cu — the emitting face — the ANODE segments `(14.8, 44.3)→(16.176, 42.924)` and
  `(16.176, 42.924)→(17.727924, 42.924)` pass **0.636 mm** from D2's emitter center (16.1, 43.9),
  i.e. *inside* the Ø2.1 aperture (r = 1.05), partially shadowing the brightest part of D2's cone.
  **D3/D4/D5 are clear** — they route their pads straight out of the window, which is the documented
  rule (design-notes: LED anodes trace out of the window). Re-route D2's anode to exit the window the
  way its siblings do. Verified numerically against the committed board.

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
