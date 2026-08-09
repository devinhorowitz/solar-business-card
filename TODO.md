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

_Purged 2026-08-09: 18 completed `[x]` items culled (the file's own policy — the record is in git
history and the design-notes addenda); the panel `check_zone_fills` fab hazard culled because it was
FIXED the same day (`PCB/solar-glow-drh-panel.kibot.yaml` now carries the preflight); and two
"decided, do not re-derive" reference items (U6 alternatives, C26/C27 thinning) moved to Locked,
where verdicts of that shape belong. 1,116 → 636 lines. What survives is almost entirely
bench-gated: it needs the first article, a light meter, or a scope._

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
  - **THE SUPERCAPS ARE TWO DIFFERENT PARTS, 2 + 2 — NOT four of one.** _(Called out 2026-08-02;
    now printed on every consistency run and gated by check [15].)_
    **SC1, SC3 = SS17 1.8 F 2.75 V = `3-153-440`** (DigiKey `486-3-153-440-ND`) and
    **SC2, SC4 = WS17 1 F 2.75 V = `3-153-438`** (DigiKey `486-3-153-438-ND`). Two MPNs, two
    separate stock pools, two of each per board — ordering 4× either one builds nothing.
    Board and schematic have always agreed on this; what invites the mistake is that
    `datasheets/` holds exactly one supercap PDF and its filename reads
    **`SC1-SC4  SCHURTER 3-153-438`**, i.e. the wrong belief written down, with no datasheet
    on file for `3-153-440` at all. (`BOM/README`'s generated table is correct — it maps that
    PDF to SC2, SC4 by MPN, not by the filename.) Fix the filename and fetch the missing
    datasheet at order time; do not let the folder be the source.
  - **Supercaps are the global chokepoint:** SS17 ≈ 400 and WS17 ≈ 393 **combined across both
    distributors** — at 2/board, ~200 boards of world-visible stock per type. SS17 is $0.66 cheaper
    at Mouser. Order with the first cut, from both carts if batching.
  - **Nothing in the fab package buys the hand-soldered parts.** SC1–4 and PV1–2 are excluded
    from the assembly BOM *and* (since 2026-08-02) from the CPL — correct, they are hand-soldered
    — which means **no fab file orders them**. `BOM/README`'s table is the only document that
    does, so check [15] now holds it against the board and prints the buy list every run:
    `3-153-438 ×2 (SC2, SC4); 3-153-440 ×2 (SC1, SC3); SM141K06TF ×2 (PV1, PV2)`.
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

- [ ] **[BENCH/PCB — TABLED 2026-08-02 until the hero project ships] Two designed-but-never-laid-out
  test boards — the instrument and the go/no-go**
  _(Piped into TODO 2026-08-02; tabled the same day: they do NOT ride the card's fab order.)_
  They can be made cheaper at OSH Park, thicker (1.6 mm, no reason to share the card's exotic
  0.6), and they need no assembly service — both are hand-solderable. Deliberately decoupled so
  nothing about them gates the hero order. (a) `docs/harvest-bench-fixture-handoff.md` — the
  **panel characterization fixture** (single-sided, no MCU: 4-wire panel I-V under real light,
  needs an SMU/DMM); the authoritative tables are in the doc, it just needs KiCad layout. (b)
  `docs/harvest-budget-test-board.md` — the **harvest-surplus blinker** (carries two product
  panels + a jumper-selected card-draw emulation load; flash rate ∝ net banked power — the
  glanceable desk answer to "can this light run the card?"). Sequence when picked up: fixture
  first (characterize V_mp), then set the blinker's window from it (its §5).

- [ ] **[BENCH — BLOCKS the pogo rig] The test plate has no hold-down, only registration**
  _(2026-08-04. Raised by DRH while costing the panel; the numbers below confirm it.)_
  `enclosure/solar-glow-drh-pogo-testplate-cad.py` asserts **14 probe pads** (TP1–TP7 + JP1 ×4 +
  J1 ×3) and specs P75 probes at **~100 gf** spring. That is **~9–14 N pushing up**, working to
  full stroke. Its only fasteners are `2x dia 1.5 dowel pins through TH1/TH2` — those *register*
  the panel, nothing *holds it down*. The 1-up panel is 65.6 × 103.7 × 0.6 mm of FR4, ≈ 4.1 cm³
  at ~1.85 g/cm³ ≈ **7.6 g ≈ 0.075 N**. The springs beat gravity by **~120–180×**: the panel
  never seats, it floats off the pins. A thumb is not a test fixture.

  **Fix: clamp through the card's own eight M2 mounts.** `fit_rules.MOUNTS` — Ø2.20 plated
  through-holes, 3.60 mm annuli, all on GND, four corners plus two mid-edge pairs, on a
  **45.06 × 83.16** pattern. Distributed clamping, which also matters because 14 point loads in
  the middle will bow a 0.6 mm board that is only pinned at two rail holes.

  Three things fall out, and the third is the reason to do it even if the rig were fine:

  - **Registration gets SHORTER, not just firmer.** TH1/TH2 are in the *rail*, so the tolerance
    chain is rail → tab → rout → card. The mounts put the datum and the probed part on the same
    piece of copper-clad.
  - **In-panel testing is NOT lost.** The plate is already panel-sized, so the rails just rest on
    it — screw the card down while it is still in the frame and "test as delivered, then depanel"
    survives intact, now with actual clamping.
  - **It decouples the plate from panel topology.** Today it imports `panelize` for `TH_LEFT_Y`,
    `TH_RIGHT_Y`, `BUS_INSET` and `RAIL_W` — a fixture bolted to a frame that gets *routed away*.
    Re-based on `fit_rules.MOUNTS` it stops caring whether the panel is 1-up, 2-up or absent,
    and it sits on the same single source of truth the brace and shell already read. Note
    check [16] bans literal mount lists in `enclosure/`, so this must be an import either way.

  Do this before ordering the plate — it is a generator edit, and CI reprints the STEP/STL/drawing.

- [ ] **[BENCH] Assemble and bring up the pogo test rig when the panel arrives**
  _(Piped 2026-08-02 — the rig was built in-repo but its bring-up had no entry.)_ Everything is
  generated and committed: the in-frame pogo test plate (`enclosure/solar-glow-drh-pogo-testplate`,
  probes TP2–TP7 + TC1 with the card still in the panel), the Pico monitor firmware and channel
  map, and the host dashboard (`bench/monitor/`). Physical work remaining: print/order the plate,
  fit pogo pins, flash the Pico, and smoke-test channels against `bench/monitor/README.md` before
  the first card powers up on it.

- [ ] **[V-NEXT, PARKED] E-ink display variant — concept banked, not adopted**
  _(Piped 2026-08-02; `docs/eink-display-variant-notes.md` is the full record: panel survey,
  geometry both directions to scale, 1-bit artwork + QR mockups.)_ A different output modality
  on the same harvest/supercap/NFC/accel platform. Deliberately NOT a v4 item; revisit only
  after the v4 first article proves the platform. The doc is the decision ledger if it wakes.

## Firmware — `firmware/`, `firmware/README.md`

- [ ] **[FIRMWARE/BENCH] Turn the FRAM event log ON once the harvest budget is measured** —
  _built 2026-08-03, deliberately still `USE_FRAM_LOG 0`._
  The black box at FRAM `0x0000` now counts **taps, double-taps, NFC field reads and motion
  trips** alongside the cold-boot count it already kept. Record v2 (`DRHc`, 24 B); a v1 `DRHb`
  record is **migrated**, not overwritten, so a card already in the field keeps its boot count.
  Design note, because it is the part that matters: events cost a **saturating byte increment
  in RAM**, and at most one FRAM cycle per ~1 s poll folds them into the lifetime totals. A
  burst of taps is one wake/read/write/park, not one per tap — an I2C transaction has no
  business in the tap path, which this firmware costs at a byte-compare even when muted. The
  trade is a loss window of up to one poll if the tank dies mid-interval; these are curios, not
  telemetry, and protecting a tap count with unmeasured energy is the wrong way round.
  **Cost, measured:** shipped build byte-identical (4930 text / 21 bss — `check_fw_size` still
  matches the README); with the log on, **+238 B flash and +4 B RAM** over the same build with
  only the old boot counter. **The gate stays 0** until README's "the open question" — harvest
  vs. draw under real indoor light — has a bench number. Flipping it is then a one-line change.

- [ ] **[FIRMWARE] HOTP authenticator — PARKED behind the VOUT respin item**
  _(2026-08-03, same source.)_ Flash is not the obstacle: ~2.4 KB used of 64 KB, and HMAC-SHA1
  is another 1–2 KB. Three things are.
  (a) **Secret provisioning** — there is no secure path to get a key onto the card, and the FRAM
  is an unencrypted I2C part anyone with a clip can read. (This also sinks the "secure offline
  vault" idea from the same document: "completely isolated and offline" overstates a part you
  can read with a $3 clip.)
  (b) **It needs the card alive.** SRAM pass-through requires `NFC_EN` asserted, so the token is
  unavailable exactly when the tank is flat — the state it would be most wanted in. Routing
  `VOUT` (see the PCB item) removes this.
  (c) **Reach** — WebNFC is Android/Chrome only; iOS will not do raw tag I/O from a browser.
  Revisit when (b) is fixed; (a) still needs an answer.

_(Also from that document, dispositioned 2026-08-03: **light-aware contextual glow** — already
built, `VSENSE` on AIN2 and `STO_SNS` on AIN1, so it was a nod not a proposal. **Gesture-based
NDEF profile switching** — declined; the pieces exist (`nfc_write_ndef()`, hardware single/double
tap) but each switch is a powered NFC session plus a tag-EEPROM write, and it solves a problem
nobody reported. The document's headline **"zero-battery vampire wake, no hardware changes"** is
wrong on this board — see the PCB item; `U5` pin 7 is unconnected.)_

- [ ] **[FIRMWARE] The screened feature ledger's live remainder — imported 2026-08-02**
  _(`firmware/feature-roadmap.md` is the Gemini-brainstorm decision ledger, dispositioned
  2026-07-12: seven features shipped as `board.h` knobs, the rest triaged. It was an ORPHAN —
  nothing here pointed at it. This item is now the single live pointer; the ledger carries the
  detail and stays.)_ The still-open remainder, by gate:
  **(a) Actionable now, energy-safe: one BUILT, one DECLINED, 2026-08-02.** The VSENSE-dark
  co-condition landed as `USE_DARK_DORMANT` (30 min dark → tap/motion/ack glows suppressed in
  any orientation; **double-tap is the deliberate dark-room escape**, answering the won't-do
  note's nightstand objection; light exits in ~1 poll). **Shipping/coma mode is declined** —
  built and removed the same day: the card is hand-delivered, so the dark-shipping-box premise
  never occurs, and what it bought (~1.5–1.7× on box standby, since only ~1 µA of the ~2.7 µA
  dark sum is firmware's to trim) did not justify a mode that changes the poll period, disables
  the watchdog and re-powers the card's only input. Decision record in `feature-roadmap.md`;
  working implementation in git history if a mailed-batch variant ever becomes real.
  **(b) Gated on the energy-budget bench** (the #1 gate — these spend LED energy or need measured
  constants): zero-CPU reflex glow (EVSYS→TCA0), CCL heartbeat, ambient auto-brightness,
  shadow-abort / AC0 brownout-reflex, "find the sun" bar-graph, circadian duty-cycling, PoV
  air-message, free-fall catch, FIFO gestures.
  **(c) Revival hooks only if a companion app ever exists:** SRAM-mailbox telemetry /
  orientation-keyed NFC (declined for v4 — they endanger the offline-first vCard).

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

  **RE-AIMED 2026-08-04, because the phenomenon this was written to catch does not exist.** The
  docs described "unequal series stages" that BAL had to hold apart; the board's stages are
  **equal by construction** — SC1 ∥ SC2 = 2.8 F above `MID`, SC3 ∥ SC4 = 2.8 F below, one SS17 and
  one WS17 in each. So there is no designed capacitance imbalance for a top-of-charge measurement
  to find, and **top-of-charge over-volt is the wrong thing to look for**.
  What BAL actually corrects is **leakage mismatch between two identical stages**, and leakage
  mismatch shows up as **MID drifting away from V/2 in the DARK, over days** — not during a charge
  cycle. Log MID against STO/2 on a charged card left unlit, and give it long enough to diverge;
  a charge-cycle log will look clean whether or not the balancer is doing anything.
  Also worth confirming in the same session: STO caps at the strapped **4.65 V**, not 5.5 V — the
  difference between **15.1 J stored** and the 21 J nameplate, and between 9.8 J and 21 J spendable.

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
  measured pull-up R; and while there, meter the gated-VCC SDA/SCL leakage through RN2 (né R10/R11, consolidated 2026-08-08; same
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

- [ ] **[LAYOUT — lite-brace headroom] Component moves that buy back the lite brace's lost third**
  _(2026-08-07, from the enclosure-variants round. DRH does the moves manually; everything downstream
  regenerates from the board — brace, shells, drawings, renders are all functions of it, so a pushed
  board re-derives the lot with no hand step beyond `mask_art --apply` if front copper moves.)_
  The **lite** variant's cavity is **1.22** (component-limited: thin 1.00 caps + U1/L2 at 1.00 + AIR
  0.22), so `SPAN_LIMIT` falls 1.18 → **0.60** and 24 parts become blockers. The brace drops from
  1413.8 mm² / 35.2 % of the cavity floor (max) to **935.7 / 23.3 %**, giving up **344.6 mm² in four
  islands** — the N/S corridors between the supercap pad zones, each severed at its mouth by one or
  two movable parts. Ranked by measured main-piece gain (re-derive any of this from
  `fit_rules.brace_footprint()` with `CAVITY/GAP/SPAN_LIMIT` set to the lite values; the what-if is
  "exclude the ref from `blockers()` and re-measure"):
  - **U3 (accel) +75.6 mm²** — reconnects island 3 (67 mm², the N corridor between SC1/SC2). The
    freest mover on the board: I²C + INT1/INT2 only, and tap sensing works anywhere on a rigid card.
  - **C23 +103.2 mm²** — reconnects island 0 (100 mm², W corridor at SC3). Constraint: it is U9's
    rail cap — move it **as the U9 cluster**, not alone.
  - **L2 +109.3 mm²** — reconnects island 1 (96 mm², center corridor). Hardest constraint: the
    AEM10300's LX loop inductor — moves only **as a pair with U8** (U8 itself is +30.5 more).
  - U7 +40.9, U1 +29.8: widen the main band only; no island rescue.
  - **Island 2 (81 mm², E corridor) is unrecoverable** — severed by SC4's own pad zone, the max
    variant's known ~85 mm² island wearing its lite face.
  - Combined, measured: U3+C23 → 27.8 %; **U3+C23+L2 → 30.5 %**; all six → 33.0 % (max is 35.2 %).
  - **Bare pads do NOT block the brace** (their 0.20 budget is under even the 0.60 span limit) — the
    pad problem is the **lips**: J1 (optional header), JP1 (bench strip), and TP1/TP2/TP7 sit inside
    lip strips (W edge: 7 bands pinched by J1/TP2/TP7 + the west cap row; E edge: single band, JP1 +
    TP1 inside it, already coil-capped at x 49.55). Moving or deleting those bare-pad items widens
    the lip bands on every variant; moving the four supercaps' zones is the design itself, not a move.
  - Standing rules still apply to the session that does the moves: `mask_art.py --apply` after any
    front re-route (check [6]), and the teardrop-inclusive in-aperture sweep if anything approaches
    the glow window (`PCB/README.md` supercap box).
  - _2026-08-07 addendum: the CAP SCOOT landed first (all four supercaps to a uniform 1.00 mm body
    standoff from their board edge; the shell's lip ring is now part-aware — fit_rules `RING` +
    `ring_reliefs()` — after six probed ring-vs-part collisions). Post-scoot baselines: **max 1486.7
    mm² / 37.1 %**, **lite 1078.2 / 26.9 %** (dropped 277.0 in 3 islands — island 3's corridor
    mouth widened but U3 still severs it). The ranked what-ifs above (U3/C23/L2 gains) were measured
    on the PRE-scoot board — re-derive them before acting; the method line above is unchanged._
  - _2026-08-07 evening: DRH's CENTER CONSOLIDATION superseded most of this plan — eleven parts
    (the U6/C4/C6/C7/R14/TP2 west cluster, the R5/R6/Q2/R18/C5 east cluster) moved into the center
    column x≈25–27, and SC1/SC2/SC4 scooted horizontally (SC1 −1.91, SC2 +1.70, SC4 +0.36). The
    trade, measured and accepted: total brace **max 34.3 % / lite 26.4 %** (leg area given up to
    the cap scoots — legs are lip/cap/cell-backstopped by design) while the **center band y40–48.9
    holds at 91 % (max) / 73.5 % (lite)** — the band was already brace-saturated, so consolidation
    cleaned the legs rather than adding center coverage. C4 and Q2 (0.90) are now mid-board
    lite-blockers, both OUTSIDE the critical band. The U3/C23 island-recovery moves above remain
    UNEXECUTED and the numbers need re-deriving on this board before acting._

- [ ] **[PCB — DRC hygiene] `missing_courtyard` is blind, and it hid a 0.090 mm hazard**
  _(2026-08-04, raised by the SC1↔C1 sweep. The re-measure half of this item closed 2026-08-05:
  the land correction moved SC1's pads ±1.30 mm **symmetrically**, so the can registration did
  not move and SC1↔C1 stands at **0.090 mm** — with SC2 0.350, SC3 0.385, SC4 0.420. It did NOT
  resolve itself; the accepted mitigation remains the caution in `PCB/README.md`'s hand-solder
  step, and the boxed-in-C1 numbers live in that same box so nobody re-derives them.)_

  What stays open is the reason nothing caught this: `missing_courtyard` is `"ignore"` in
  `PCB/solar-glow-drh-v4_0.kicad_pro`, and **39 of 73 footprints carry no courtyard at all,
  19 of them machine-placed** (C1, C11, C12, C24, C29, C3, C5, C6, C7, C8, R1, R10, R11,
  R14, R17, R18, R2, R3, R4 — recounted 2026-08-05: 39 of 73 courtyard-less after SB1–4/R12 left). Turning the rule on without drawing those courtyards just trades
  one silence for 20 false alarms, so it is a two-part job: give the library 0402s courtyards,
  then set the rule to `warning`.

- [ ] **[PCB — respin] Route `U5` pin 7 (`VOUT`) — NFC energy harvesting, currently unconnected**
  _(2026-08-03. Was "bundle with the supercap-land re-route"; that landed 2026-08-05 without
  this — still respin-only, bundle with the next board-edit window.)_
  `U5 pad 7 VOUT_7 -> unconnected-(U5-VOUT-Pad7)`. The NT3H2211 can deliver **up to 15 mW out of
  the reader's field** (datasheet §"Energy harvesting"), and on this board that pin goes nowhere.
  **Size it as a WAKE, not as a charger** — the arithmetic is not close:
  the tank is SC3∥SC4 (2.8 F) in series with SC1∥SC2 (2.8 F) = **1.4 F**, and to the AEM's 4.65 V
  VOVCH ceiling that is **15.1 J**. One tap at the datasheet *maximum* 15 mW for ~1 s is **15 mJ
  — 0.1 % of a full tank, ~1000 taps to fill it from empty**, and 15 mW is best-case Class-5
  coupling that a phone will not deliver. The datasheet also warns that drawing VOUT current
  *reduces read range*, so it is not free even when it works.
  What it IS good for: **~8 LED blinks** (16 mA x 2.25 V x 50 ms = 1.8 mJ each) — a real
  "the card is never dead" flash — and powering the MCU long enough that the **SRAM pass-through
  works on a flat card**, which is what unblocks the HOTP item above.
  **Do not wire it into the tank.** Two reasons: `Vout,max` is **3.3 V** and STO runs to 4.65 V,
  so it cannot push into the top of the stack without a boost; and `MID` is the AEM10300's
  **`BAL`** pin (U8 pad 13), so charge injected into the lower cell alone is partly burned back
  off by the balancer. Give VOUT its own small reservoir feeding the MCU/LED path instead.

- [ ] **[PCB/BENCH — cheap, any time] Feel coupons: bare same-size boards at 0.4 and 0.2 mm**
  _(2026-08-02, born from the thickness decision.)_ Order the cheapest possible bare PCBs at the
  card's exact outline (50.8 × 88.9 mm, any copper, any colour) in **0.4 mm and 0.2 mm** — plus
  the 0.6 reference the real panel already provides — and just *handle* them. If the flex
  difference is imperceptible in hand, a future revision can bank the 0.2 mm; if it reads cheap,
  the 0.6 lock is confirmed by touch, not guesswork — and either way the enclosure work that
  follows is informed **by handling it, not just guessing**. No assembly, no schematic, no panel:
  a one-outline Edge.Cuts board at a budget fab is a few dollars a piece. Decoupled from the
  hero order; do not let it gate anything.

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

- [ ] _(Low)_ **`PCB/README.md`'s parts table is a hand-maintained duplicate of the BOM master** and has
  now drifted twice (it was still listing `AVR64DD28-I/STX`, `TPS22918DBVR`, the SOIC-8 FRAM and
  pre-longevity-pass passives when caught on 2026-07-25). It was regenerated from the xlsx and marked
  as a dated derived snapshot, but the structural fix is to **generate it in CI** from the master
  (kibot already regenerates `Generated/fabdocs/…-bom.csv`) or to cut it down to a pointer plus the
  order-time hazards. Until then, re-check it whenever the BOM changes.

## Enclosure — `enclosure/…-backshell-…-cad.py`, `enclosure/brace/`

- [ ] **[SOURCING — lite/air] Pick the thin supercap MPN**
  _(2026-08-07, opened with the three-variant round.)_ `part_heights.SUPERCAP_H_THIN = 1.00`
  is **PROVISIONAL — DRH's working number, no MPN, no datasheet behind it**, unlike every
  other figure in that file. The lite cavity (1.22) happens to be component-limited so a
  small thickness change is free, but **anything over 1.00 starts moving the lite/air
  numbers** (`fit_rules.VARIANTS` re-derives them — one edit, everything follows: cavity,
  stack, screw pick, ledgers). When chosen: verify max thickness from the datasheet, land
  the number + the datasheet in `datasheets/`, and note the 2+2 capacity split question —
  the buy documents today describe the ONE committed board, which is the 1.70 build;
  thin-cap purchasing for lite/air builds is a manual substitution until then. Also the
  **air NFC re-tune** rides this: open back = no titanium behind the coil = C9's 47 pF
  needs the bench again (`enclosure/README.md` variants table carries the warning).

- [ ] **[ENCLOSURE] Rename the `v3_0-backshell-0p6b` fossil — a coordinated 10-file unit**
  _(2026-08-01, found while building the mesh gate.)_ The shell generator, its DRAWING-gen, and
  the STEP/STL they emit all still carry `v3_0` names although the geometry is the current v4
  solid (the thickness figure measures 3.5500 from it). The rename touches, together, in one
  commit: both generator filenames, `kibot.yml` trigger paths AND its CAD-step commands,
  `assembly_render.py`, `scripts/ref_figures.py` (if it names the file), `check_mesh.py`'s
  BASELINE keys, README + PCB/README + enclosure/README
  prose, and design-notes references (historical mentions keep their history markers; the
  engraving-studies reference this list once carried was culled 2026-08-02). Do it
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
- [ ] **Front solar-panel fence** — concept only. Panel height known (**cell 1.2 mm ± 0.3 mm**,
  SM141K06TF datasheet p.1 + p.3 drawing — caliper-check the actual cells before cutting fence height;
  the ± 0.3 mm spread is wide for a melted-in fit). Still blocked on attachment (M2 screws / adhesive /
  snap-fit) and direction A (full-perimeter, recommended) vs B (per-panel rings).

- [ ] **[ENCLOSURE/TOOLING] A heat-tolerant hand-solder jig for SC1–SC4 and PV1–PV2** — the
  parts the machine never places, held in register through the melt *and the freeze*.
  _(DRH, 2026-08-03. Not scheduled; recorded before it is needed, because one of its inputs is
  not final yet — see SEQUENCING.)_

  **The problem has a number, and the number is `CLR = 0.25`.** `enclosure/fit_rules.py:92`
  sets the brace's in-plane clearance around every part body at 0.25 mm. So a supercap
  hand-soldered more than a quarter of a millimetre off its footprint does not merely look
  crooked — it fouls its own pocket wall, and the brace stops seating. The failure is silent
  at solder time and only shows up at final assembly, on a card that by then has everything
  else on it. Same story for the cells against the eight M2 screws: they already fit "almost
  too exact" (which is why all 8 mounts moved 0.13 mm diagonally on 2026-08-03), so a cell
  soldered a few tenths proud puts lateral load on its own terminals.
  **And the supercap joints are UNDER the body** (`PCB/README.md` → hand-solder order): you
  cannot see them, so you cannot inspect-and-nudge. Alignment has to be mechanical or it is
  nothing.

  **Why a normal print will not do**, which is the whole reason this is its own item. The
  requirement is not "hold it while I solder" — it is **hold it while it cools**, so the part
  cannot shift as the joint freezes and the jig can be lifted off a solid assembly. That means
  the jig is in contact with a part at hotplate temperature for the whole cycle. PLA/PETG/ABS
  and standard SLA resin are all out by a wide margin.

  Real candidates, and they are not equivalent:
  - **FR4, ordered as a PCB from the same fab.** Strongest option and the most repo-idiomatic:
    FR4 survives a 260 °C reflow *by definition*, a milled/routed outline holds ±0.1 mm easily,
    it is nearly free, and it can ride the existing PCBWay panel (`scripts/panelize.py`) so it
    arrives dimensionally matched to the boards it registers. Low thermal conductivity, so it
    does not rob the joint.
  - **PEEK or machinable ceramic (Macor)** — ~250 °C continuous, low conductivity, machinable
    to a fit. Costs real money.
  - **High-temp platinum-cure silicone** — compliant, insulating, forgiving of the cell's
    fragile laminate; poor at holding a hard datum on its own, so it wants a rigid frame.
  - **Aluminium — the tempting wrong answer.** A metal jig sitting on a hotplate is a heat
    sink pressed against the exact joint you are trying to melt; expect cold joints and a
    profile you cannot repeat. If metal, prefer **stainless** (~1/15 the conductivity of Al)
    and minimise contact area.

  **Register off the mounting holes, not the board edge.** MH1–4 / MP1–4 are NPTH at positions
  `enclosure/fit_rules.py` already publishes as `MOUNTS`, gated against the board by
  consistency check `[16]` — so a jig derived from that table cannot drift from the drills.
  The routed outline is the looser datum.

  **The two parts are NOT one jig, because their thermal specs are not the same shape:**
  - **SC1–SC4**: SCHURTER gives `Soldering Methods: Manual` and an operating range of
    −40…+85 °C, and publishes **no peak-temperature or reflow profile at all**
    (`datasheets/SC1-SC4  SCHURTER 3-153-438  $16.69.pdf`). There is no number to design a
    hotplate profile against — establishing a safe one on scrap cells is part of this task,
    not a detail of it.
  - **PV1–PV2**: **≤ 260 °C for ≤ 2 s per joint, no reflow, moisture-sensitive laminate**
    (`docs/harvest-budget-test-board.md`, `PCB/README.md`). A hotplate that soaks the whole
    cell is precisely what this part is not rated for — so the cell jig may need to be a
    *heat-shield-plus-clamp* that keeps the plate off the laminate while a local iron does the
    four joints each, rather than a soak fixture. Decide this before cutting anything.

  **SEQUENCING — the supercap-jig gate LIFTED 2026-08-05.** This paragraph used to block the
  supercap jig on the knowingly-wrong lands (±11.00 / ±16.25 against the datasheet's
  ±12.30 / ±17.55). The land correction landed 2026-08-05 — board pads now at datasheet pitch,
  `x = 0` — so a jig cut from today's board encodes the right pitch. The **cell** jig never had
  the dependency. One residual: the jig generator must read pad positions from the *board*, per
  the "Shape of the work" below, so it inherits any future correction for free.

  **Shape of the work**: follow `enclosure/solar-glow-drh-pogo-testplate-cad.py`, which is
  already exactly this kind of thing — a fixture that is not part of the product, generated
  from the committed board, emitting STEP/STL/drawing, with its own `kibot.yml` trigger. A jig
  generator that reads part positions from `PCB/solar-glow-drh-v4_0.kicad_pcb` and mount
  positions from `fit_rules.MOUNTS` stays correct through every future re-route for free; a
  hand-drawn one starts rotting immediately.

## Locked — do NOT re-open

- **Accepted copper trade-offs (2026-07-26 audit, re-affirmed at the 2026-07-30 purge)** — each
  was pitched as trivial, re-rated as needing neighbour reroutes, and judged defensible to leave:
  no analog net class (ADC nodes at the clearance floor against active nets); F.Cu pour under L2
  and ~93 % of the switching-node copper with B.Cu hugging LIN/LOUT at 0.20 mm; LIN/LOUT/BUFSRC at
  0.15 mm width (~47 mΩ in series with the inductor); CINT 12.3 mm of 0.15 mm track from the real
  VINT pin; the STO feed necking to 0.3 mm for 15.8 mm. Re-open only with a measurement that one
  of them costs something real.

- **U6 = TPS22919, decided 2026-08-05 — do not re-research the family.** The first pass answered
  "no clean option" by searching inside TPS229xx and stopping; that was wrong, and the corrected
  survey is in git history. Note TPS22917 ships in exactly one package (SOT-23-6/DBV) and has no
  `-Q1` in any package, which is how the `TPS22918 → -Q1` temp-grade-up policy got silently
  dropped when U6 was briefly TPS22917.
- **C26/C27 low-profile: solved BY CASE SIZE, not by thinning 0805 — do not re-derive.** No vendor
  makes a 10 µF / 16 V / true-X7R 0805 under 1.40 mm max. C25–C27 are low-profile **1206** Murata
  GRM319 (0.95 mm max). The X7R→X5R trade is deliberate: no low-profile 10 µF true-X7R exists in
  ANY case size, and the supercaps cap the system at +85 °C — exactly X5R's window.
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
