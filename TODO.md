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

_Purged 2026-07-30 (see the design-notes addendum "TODO purge, 2026-07-30" + git history):
29 completed items culled; 20 open items verified already-resolved against the current board/repo
and culled; 4 declined (cosmetic lib_ids, stencil/copper cosmetics, teardrop completeness — covered
by the README pre-order step, C13's lib_id); the accepted copper trade-offs moved to Locked._

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

- [ ] **[BOM] Buy the low-stock / long-lead parts early** _(2026-07-23; numbers refreshed 2026-07-30
  from a live DUAL-distributor sweep of all 31 orderable MPNs — DigiKey and Mouser, exact-MPN matched.)_
  - **U3 accel `ADXL367BCCZ-RL7` — the new alarm: DigiKey went 731 → 0 in seven days.** Mouser holds
    2,601 ($7.80). The card's only actuator is now single-distributor. Buy from Mouser, early.
  - **Supercaps are the global chokepoint:** SS17 ≈ 400 and WS17 ≈ 393 **combined across both
    distributors** — at 2/board, ~200 boards of world-visible stock per type. SS17 is $0.66 cheaper
    at Mouser. Order with the first cut, from both carts if batching.
  - **FER1 was a false scarcity:** the "41 in stock, 24-week lead" figure was DigiKey's; **Mouser has
    119 at $13.18 vs DK's $17.43**. Buy there.
  - **U1 MCU recovered:** DK 608 → 1,365 (Mouser only 269 — buy DK). **PV cells** 423, DK-only
    (Mouser doesn't list ANYSOLAR). **C11** (mandatory ADXL VREG cap) ~5.1 k combined — fine, order
    with build.
  - **A single-distributor order is impossible:** DK-only = PV, LEDs (`LA P47F`, 11.3 k), U7 FRAM
    `…AWEWE1` (1.5 k), R10/R11, C22. Mouser-only = U3, U8 AEM10300 (553, listed as `AEM10300-QFN`),
    C26/C27 Samsung, PRG1 UPDI Friend (56). Split is forced; assign by depth.
  - **CBL1 trap:** DigiKey's in-stock Tag-Connect item is `TC2030-MCP-NL` (no legs); the legged
    `TC2030-MCP` the BOM specifies is Restricted/zero at Mouser — check Tag-Connect direct at order.
  - Also grab a **spare NT3H2211 or two**: NXP steers new designs to NTAG 5, so NTAG I²C plus carries
    EOL risk on a years horizon (the U5 NFC audit kept it as best-fit, but flagged this).
  - _LCSC pending as a third source (API hookup TBD). Expectation to verify: strong on the Yageo /
    Samsung / TDK passives, useless for the actual chokepoints (SCHURTER, ANYSOLAR, e-peas, RAMXEED,
    Würth FSFS, likely ADXL367)._

- [ ] **[BENCH/PCB] Two designed-but-never-laid-out test boards — the instrument and the go/no-go**
  _(Piped into TODO 2026-08-02; both docs are complete design handoffs that were invisible from
  this list.)_ (a) `docs/harvest-bench-fixture-handoff.md` — the **panel characterization
  fixture** (single-sided, no MCU: 4-wire panel I-V under real light, needs an SMU/DMM); the
  authoritative tables are in the doc, it just needs KiCad layout. (b)
  `docs/harvest-budget-test-board.md` — the **harvest-surplus blinker** (carries two product
  panels + a jumper-selected card-draw emulation load; flash rate ∝ net banked power — the
  glanceable desk answer to "can this light run the card?"). Sequence: fixture first
  (characterize V_mp), then set the blinker's window from it (its §5). Both attack the #1 gate
  from the instrument side and could ride the same fab order as the card panel.

- [ ] **[BENCH] Assemble and bring up the pogo test rig when the panel arrives**
  _(Piped 2026-08-02 — the rig was built in-repo but its bring-up had no entry.)_ Everything is
  generated and committed: the in-frame pogo test plate (`enclosure/solar-glow-drh-pogo-testplate`,
  probes TP2–TP7 + TC1 with the card still in the panel), the Pico monitor firmware and channel
  map, and the host dashboard (`bench/`). Physical work remaining: print/order the plate, fit
  pogo pins, flash the Pico, and smoke-test channels against `bench/README.md` before the first
  card powers up on it.

- [ ] **[V-NEXT, PARKED] E-ink display variant — concept banked, not adopted**
  _(Piped 2026-08-02; `docs/eink-display-variant-notes.md` is the full record: panel survey,
  geometry both directions to scale, 1-bit artwork + QR mockups.)_ A different output modality
  on the same harvest/supercap/NFC/accel platform. Deliberately NOT a v4 item; revisit only
  after the v4 first article proves the platform. The doc is the decision ledger if it wakes.

## Firmware — `firmware/`, `firmware/README.md`

- [ ] **[FIRMWARE] The screened feature ledger's live remainder — imported 2026-08-02**
  _(`firmware/feature-roadmap.md` is the Gemini-brainstorm decision ledger, dispositioned
  2026-07-12: seven features shipped as `board.h` knobs, the rest triaged. It was an ORPHAN —
  nothing here pointed at it. This item is now the single live pointer; the ledger carries the
  detail and stays.)_ The still-open remainder, by gate:
  **(a) Actionable now, energy-safe:** the face-down dormant's missing half (the VSENSE-dark
  "in a bag/pocket" co-condition — the knob shipped with only the accel-Z test); **shipping/coma
  mode** (halt RTC/ADC, wake on sustained solar spike — protects the caps in a dark shipping box).
  **(b) Gated on the energy-budget bench** (the #1 gate — these spend LED energy or need measured
  constants): zero-CPU reflex glow (EVSYS→TCA0), CCL heartbeat, ambient auto-brightness,
  shadow-abort / AC0 brownout-reflex, "find the sun" bar-graph, circadian duty-cycling, PoV
  air-message, free-fall catch, FIFO gestures.
  **(c) Revival hooks only if a companion app ever exists:** SRAM-mailbox telemetry /
  orientation-keyed NFC (declined for v4 — they endanger the offline-first vCard).

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

- [ ] **[BENCH] Tank ceiling and midpoint balance — log STO and MID across full charge cycles**
  _(2026-08-01, ThomsonLint review COMP_CAP_004 — see `docs/thomsonlint.md`.)_ The repo's own
  worst-case math assumes a full tank at 5.5 V, which is the cells' rated voltage with zero
  headroom; EDLC life derates steeply near rating. What actually bounds it is the AEM10300's
  configured storage ceiling — never measured on hardware. During the energy-budget pass, log
  STO and MID (TP3) across full charge cycles: confirm the enforced ceiling and the top-of-charge
  cell balance. If the ceiling lands at rating, consider configuring the harvester one step down
  for cell life.

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

- [ ] **[BENCH] NFC FD-pin leakage — meter the real standby adder** _(2026-08-01 pressure test, the
  panel's one major: NT3H2211 Table 42 specs FD IL at **1.5 µA typ / 10 µA MAX**, flowing from VS
  through PA6's internal pull-up whenever FD idles high — the card's dominant state — independent of
  pull-up value; unbudgeted in the ~2.7 µA standby sum, which is now labeled a 2.0 V-referenced lower
  bound. board.h's FD block carries the full story.)_ Bench: meter VS with FD pulled up vs FD grounded
  (tag VCC gated off, no field) to pin the real leakage; re-check FD's VIH margin at measured IL ×
  measured pull-up R; and while there, meter the gated-VCC SDA/SCL leakage through R10/R11 (same
  table, 10 µA max/pin spec). If the measured adder is real µA, the counter-moves are an external
  weak pull-up on FD or accepting the line item — decide with the energy-budget numbers in hand.

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

- [x] **[PCB/FAB] Panel fiducials — CLOSED 2026-08-01, built into `panelize.py` as specified**
  _(2026-08-01, found by the kicad-happy second-opinion analyzer on its first run — see
  `docs/kicad-happy.md` → "Integrated".)_ Exactly the derivation this item asked for: three
  Ø1.0 mm bare-copper dots with Ø2.0 mm mask openings (via `solder_mask_margin`), both faces,
  three corners of four on the rails' OUTER band (`FID_INSET` 1.0 from the panel edge → dot edge
  0.5 mm clear of the bus-ring copper, asserted in code), clear of the tooling-hole ring dodges,
  with a 180°-asymmetry guard in `main()` mirroring the tooling holes' own. The merge run's
  panel-gerber diff is the verification; local fiducials near U1 stay a
  only-if-PCBWay-asks option.

- [ ] **[PCB — PARKED, decision pending external research] 0.4 mm board thickness (3.55 → 3.35 mm)**
  _(2026-08-01.)_ Held deliberately while the thinness tradeoff is researched. The engineering
  picture as assessed: mechanics fine in-assembly (Ti + brace + 8 screws carry the card; screw
  flushness is already parametric — the shell's `sf_bottom` spotface derives from `board_th`, so
  the same DIN 84 M2×3 stays flush with +0.2 mm MORE Ti engagement); the REAL open questions are
  daylight show-through of B-side copper through the bare-FR4 windows (flagged at 0.6 already),
  panel break-tab redesign for thin FR4, reflow warpage/assembly handling, and the optics/energy
  re-tune (thinner FR4 = brighter glow — possibly the bigger prize than the feel). Do NOT respin
  the verified 0.6 board before first-article optical + energy data. 0.2 mm assessed and advised
  against (depanel fragility + show-through for an imperceptible gain).

- [ ] **[PCB/EMC] EMC pre-compliance — paper half DONE 2026-08-01, measured half open.**
  kicad-happy's `emc` skill ran in full mode (risk score 64.0, 37 findings — every one triaged
  in `docs/kicad-happy.md` → "Deep analysis"): no new real board defect; the plane-gap errors
  are the coil and the glow window measuring as what they are, and the one genuine hygiene item
  (GND stitching vias) is the next bullet. What remains is the **measured** half once the
  first-article exists: near-field probe over the AEM10300 hot loop and the LED string under
  PWM, and a reader-coupling check that the NFC coil's Q survived assembly (Ti shell + ferrite).
  Start the probe at **L2 (26.2, 58.7)** — the tool's own test plan names it the highest-dI/dt
  point on the board; its four FCC Part 15 B radiated bands all rate "risk: none" on paper.
  For the coil check, the paper baseline to measure against (2026-08-01, `scripts/nfc_coil.py`):
  **L ≈ 1.09 µH bare copper, f0 = 15.47 MHz at the placed C9 47 pF** — the ferrite-loaded tank
  should land near 13.56; how far it lands from the bare number IS the measured ferrite factor.

- [x] **[PCB — ride-along] GND return-path stitching vias — CLOSED 2026-08-01, same day** _(from
  the kicad-happy full-mode EMC pass; measured independently from the board file.)_ The trigger
  condition ("whenever the copper next opens for a real reason") arrived hours later with the
  TC1/b1 GUI session, so the nine vias rode along: one GND via on a hatch-crossing of both
  lattices beside each worst cluster (SRC, VNFC, CHG_DIS_G, MID, STO, NFC_EN, VSENSE, the
  coil-adjacent SDA side, VS — coordinates in `docs/kicad-happy.md` → "Integrated"). Before:
  2/82 signal vias had a GND via within 1.0 mm, median nearest 2.75 mm, worst 19.25 mm. The coil
  crossover via at (42.9, 38.0) stays unstitched — inside the coil keepout deliberately.
  Verified: DRC `Errors: 0 (+11 excluded)`, zero F.Mask hits, mask art re-applied and MATCH.

- [ ] **[PCB/FW] R1–R4 exceed their 62.5 mW rating only at the worst corner — note, and one cheap guard**
  _(2026-07-30, same audit.)_ The LED ballasts are `AC0402FR-07150RL` (0402, **1/16 W**). Worst
  DC corner: full tank STO = 5.5 V through SW2, min-bin V<sub>f</sub> 1.9 V (LA P47F 3B bin),
  AVR V<sub>OL</sub> ≈ 0.4 V ⇒ I ≈ 21 mA ⇒ **~68–70 mW ≈ 110 % of rating** at 100 % duty.
  Typical operation (STO 4.5, V<sub>f</sub> 2.2) is ~22 mW. PWM breathing keeps the average
  far below the peak, so this only bites if firmware ever holds 100 % duty with a full tank
  and a low-bin LED. Cheapest guard: clamp duty when STO > ~5.2 V in the glow constants
  (which are provisional pending the energy budget anyway). Alternative if the board is ever
  re-laid: 0402 → 0603 (0.1 W) on the four ballasts. No action on the copper today.

- [x] **[TOOLING] Nothing in CI notices a footprint changing SIDES — CLOSED 2026-08-01 as
  consistency check [12]**, built to this item's own spec: a `FRONT_SIDE` refdes→side snapshot
  in `check_consistency.py` (12 front footprints, everything else expected B.Cu; 78 verified
  green at install), failing on any change, updated in the same commit as a deliberate move —
  the exclusion-ledger shape this item asked for. TC1/b arrived one day before the guard.
  _(Original item kept as the design record:)_
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

- [x] **[PCB] C9 0402 → 0805 — COMPLETE 2026-08-01: land placed, and the pad toe + thermal
  relief landed too.** Each pad grew +0.4 mm on its outer toe (1 × 1.45 → 1.4 × 1.45 at ±1.15,
  growing along board-Y where the TODO's own clearance survey showed 3.4/3.6 mm of air), and
  both pads now carry per-pad thermal relief into the LA/LB pours — `zone_connect 1`, four
  0.4 mm spokes, 0.4 mm gap — so the iron heats a pad, not the tank pours. Front mask art
  untouched (B-side edit; check [6] MATCH). CI's refill + DRC on this push is the copper gate.
  _(2026-07-30; the footprint swap was DONE first, the two follow-ons landed 2026-08-01.)_
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

- [x] **[COPPER] U1 / U8 exposed-pad stencil apertures — CLOSED 2026-08-01: PCBWay's assembly
  service owns the stencil.** DRH's ruling: with turnkey assembly there is no stencil to order or
  tune on our side — PCBWay's engineering generates their own paste tooling from the B.Paste
  plot and window-panes exposed pads per their process as standard DFM; the board's 1:1
  apertures are their *input*, not the final tooling. No footprint edit, no question needed —
  their DFM round flags it if their process wants something else, which is the check this item
  was fishing for anyway.
  _(Original item kept as the record — 2026-07-26 copper audit: U1 EP 2.65 × 2.65 / U8 2.3 × 2.3,
  single full-size B.Paste apertures; IPC-7093 window-paning to ~50–80 %; the deliberate
  non-edit because coverage depends on the assembler's foil.)_

- [x] **[COPPER] Two tight spots — CLOSED 2026-08-01, one by measurement, one by a 0.1 mm nudge.**
  **R10↔C8 needed nothing**: re-measured against the committed board, the pads sit **0.310 mm**
  apart (nearest foreign track 0.329) — a post-audit upload had already spread the pair, and the
  0.159 belonged to a dead board state. Mask dams ≥0.21; both figures ≥2× the 0.152 floor. Left
  alone on purpose — a nudge would spend clearance elsewhere for nothing.
  **C13 moved (0, +0.100)**: anchor (26, 48.05) → (26, 48.15). The rear glow window's bottom edge
  is dead straight at y = 47.500 across both pads; pad tops move 47.575 → 47.675, sliver
  **0.075 → 0.175 mm**. Zero track edits: the ANODE feed crosses *through* pad 1 on the 45° line
  x + y = 74.825 (chord verified post-move: enters the top edge at x 27.15, exits the bottom at
  x 26.2), and GND is pour-connected — the refill follows. South clearances verified before the
  move: same-net ANODE vertical 0.414 x-gap to the GND pad, K4 0.60, TINY 0.72, STO 0.70.
  _(Original item, 2026-07-26 copper audit: R10/C8 "0.159 mm", C13 "0.075 mm sliver … below a
  typical 0.1 mm dam minimum" — kept as the record of what was measured then.)_

- [x] **[PCB, PRE-FAB] D2's ANODE out of its own light window — CLOSED 2026-08-01, in two
  stages.** Stage 1 (a board upload after this item was written): the 0.536 mm diagonal this
  item describes was already gone — the anode now exits the pad at x = 14.8, *outside* the
  window's x-range, sibling-style. What remained was subtler: its east-bound run sat at
  y = 42.85, **exactly tangent** to the Ø2.1 aperture (centerline at r = 1.05), so 76 µm of
  copper edge still clipped the rim. Stage 2 (2026-08-01): that run lifted to y = 42.7 — the
  copper edge now clears the aperture by 74 µm — with one 0.15 mm stitch at x = 17.904 (outside
  the window) so nothing else moved. Headroom verified before the lift: nearest foreign copper
  above is VSENSE at ~1.9 mm. D2 now leaves its window untouched, the way D3–D5 always did.
  _(Original item kept as the record:)_ _(2026-07-25 LED audit; re-verified against the 2026-07-27 crosshatch upload.)_
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

- [x] **[MIDNIGHT — decided 2026-07-31] Hard gold, or one truly identical file?** **Resolved as
  (a) in net-rule form** (recorded in `solar-glow-drh-design-notes.md` and `PCB/README.md`): all
  top-side F.Mask-exposed GND gets hard gold at PCBWay (solder-land exception for the PV pads),
  base finish ENIG with ENEPIG as the accepted alternate — and the midnight question retired
  itself: OSH Park offers no electrolytic gold, so midnight's monogram is ENIG **by fab
  constraint** and the plating bus has no job there. The one residual mechanical note from
  option (a) survives below as history: an OSH Park upload still needs the two stub objects
  deleted (or a `--variant oshpark` automation, still unbuilt). The quoted `PCB/README` line
  "do not ship without it" no longer exists — that file now states the net rule.
  _(Original text kept as the decision record:)_
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

- ~~**PCBWay orders** — confirm both replies sent (`W567099ASH69` bare fab, `T-H70W567099A` PCBA);
  get the LED package dimension answer (1.25 vs 1.9 mm) and the merged PCB+PCBA total; ensure the PO
  uses the confirmed MPNs.~~ **Struck 2026-07-31: that submission and its order are long abandoned**
  (pre-dates the v4 rework, the panel, the B-side test pads and the hard-gold net rule). The next
  order is a fresh one, placed from `PCB/README.md`'s Step-3 guide against the current `Generated/`
  set — nothing from the `W567099` thread carries over, including its LED-dimension question, which
  dissolved with the confirmed LA_P47F package in the BOM master.

- [ ] _(Low)_ **`PCB/README.md`'s parts table is a hand-maintained duplicate of the BOM master** and has
  now drifted twice (it was still listing `AVR64DD28-I/STX`, `TPS22918DBVR`, the SOIC-8 FRAM and
  pre-longevity-pass passives when caught on 2026-07-25). It was regenerated from the xlsx and marked
  as a dated derived snapshot, but the structural fix is to **generate it in CI** from the master
  (kibot already regenerates `Generated/fabdocs/…-bom.csv`) or to cut it down to a pointer plus the
  order-time hazards. Until then, re-check it whenever the BOM changes.

## Enclosure — `enclosure/…-backshell-…-cad.py`, `enclosure/brace/`

- [x] **[ENCLOSURE/TOOLING] The 3D interference DRC — CLOSED 2026-08-01, built as
  `scripts/interference_drc.py`** _(the tier the mesh gate parked, built the same day.)_
  Ray-casts the emitted brace STL against every B-side body polygon (`board_parts.parts`) +
  ledgered height: 62 bodies measured, worst margin **+0.12 mm on D2–D5** (0.95 mm window
  pockets over 0.83 mm reverse-mount LEDs — tight by design), frame offset derived not
  hard-coded, east-lip six ledgered (a NEW rect escapee still fails), negative-tested via
  `INTERFERENCE_TEST_INFLATE`. Runs in kibot after the CAD step, before the commit-back.
  The supercaps are skipped BY DESIGN and stated loudly: they are height-None in the table
  (unbraced, TIM-coupled) and the CAVITY is *defined* around them (1.80 = 1.70 + 0.10 air);
  if that derivation ever moves into `part_heights.py`, the DRC picks them up automatically.

- [ ] **[ENCLOSURE] Rename the `v3_0-backshell-0p6b` fossil — a coordinated 10-file unit**
  _(2026-08-01, found while building the mesh gate.)_ The shell generator, its DRAWING-gen, and
  the STEP/STL they emit all still carry `v3_0` names although the geometry is the current v4
  solid (the thickness figure measures 3.5500 from it). The rename touches, together, in one
  commit: both generator filenames, `kibot.yml` trigger paths AND its CAD-step commands,
  `assembly_render.py`, `scripts/ref_figures.py` (if it names the file), `check_mesh.py`'s
  BASELINE keys, `engraving-studies/spin1_cutters.py`, README + PCB/README + enclosure/README
  prose, and design-notes references (historical mentions keep their history markers). Do it
  as its own PR — a miss anywhere breaks the CI chain silently.

- [ ] **[ENCLOSURE, cosmetic] The shell STL's one tessellation pinch** _(2026-08-01, found and
  ledgered by `scripts/check_mesh.py` on its first measurement.)_ One zero-length boundary edge
  at a single rim point (24.4, −34.45, 2.7) plus 3 zero-area facets — a cadquery boolean seam
  artifact, invisible to slicers (open length 0.000 mm). Ledgered in the mesh gate so anything
  worse goes red; chase only if a cadquery bump changes the count, and fix belongs in the
  shell generator's tessellation parameters, not the mesh.

  _(Absorbed from the culled cosmetic item, 2026-07-30 purge: the same README's via-in-pad list
  is v3-era — two new via-touching-pad cases exist and zero true via-in-pad remain; correct it
  in the same pass.)_
- [x] **[BLOCKER before machining] Human-verify the rear MEDALLION orientation — CLEARED
  2026-08-01: verified correct by DRH** (human read of the committed STEP, the check numeric
  gates cannot perform). The machining gate on the medallion is open; the Ti order's remaining
  gate is the energy-budget bench (README → "The open question"). _(Retargeted
  2026-07-31: the two-line maker's mark this item was written for was replaced by the Z9F
  medallion — `enclosure/medallion.py`, cut by the shell generator. The gate itself stands for
  any future medallion EDIT: numeric checks cannot catch a mirror/flip error, only a human
  reading the STEP/physical part can — re-run this check after any change to
  `medallion.py`'s text, serial or mirror convention.)_ The medallion carries the same
  per-glyph Y-flip + whole-group X-mirror convention the
  mark used (ring reads clockwise, SOLAR·NFC at 12, MMXXVI inverted at 6 —
  caseback style, correct); the machining mirror lives in `medallion._mirror()`. The check as
  performed: open the committed STEP in a viewer, view the back from OUTSIDE the part, confirm
  DRH / No 001 read correctly and the ring runs clockwise.

- [ ] **Front solar-panel fence** — concept only. Panel height known (**cell 1.2 mm ± 0.3 mm**,
  SM141K06TF datasheet p.1 + p.3 drawing — caliper-check the actual cells before cutting fence height;
  the ± 0.3 mm spread is wide for a melted-in fit). Still blocked on attachment (M2 screws / adhesive /
  snap-fit) and direction A (full-perimeter, recommended) vs B (per-panel rings).

- [x] ~~Add the maker's mark to `enclosure/README.md` once the wording is locked.~~ **Overtaken
  2026-07-31 and closed 2026-08-01:** the two-line mark was replaced by the Z9F medallion, whose
  wording is locked in `enclosure/medallion.py` (the truth home — ring text, monogram, serial)
  and documented in `enclosure/README.md`'s finish/bearing-plane sections and the root README's
  truth table. There is no maker's mark to add.

## Locked — do NOT re-open

- **Accepted copper trade-offs (2026-07-26 audit, re-affirmed at the 2026-07-30 purge)** — each
  was pitched as trivial, re-rated as needing neighbour reroutes, and judged defensible to leave:
  no analog net class (ADC nodes at the clearance floor against active nets); F.Cu pour under L2
  and ~93 % of the switching-node copper with B.Cu hugging LIN/LOUT at 0.20 mm; LIN/LOUT/BUFSRC at
  0.15 mm width (~47 mΩ in series with the inductor); CINT 12.3 mm of 0.15 mm track from the real
  VINT pin; the STO feed necking to 0.3 mm for 15.8 mm. Re-open only with a measurement that one
  of them costs something real.

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
