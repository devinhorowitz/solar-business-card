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

- [x] **[PCB/FAB — order blocker] The CPL and the BOM disagreed — FIXED 2026-08-02, gated as check [15]**
  Found while sweeping for order blockers. SC1–4, PV1–2, MH1–4 and TC1 carried `exclude_from_bom`
  **without** `exclude_from_pos_files`, so the pick-and-place file told an assembler to place ten
  parts it had no line item for, plus a DNP footprint — four of them M2 mounting annuli, which are
  not parts at all, while their siblings MP1–4 were correctly excluded from both. The exclusions
  themselves were right (the board is hand-finished, so the supercaps and cells are hand-soldered
  and must not reach the machine); only the second flag was missing. Now 47 placeable footprints
  against 47 BOM lines, matching in both directions. Check [2] could never have seen it — it
  asserts every BOM line is a real component, not that every placeable part has something to buy.

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

- [x] ~~**[FIRMWARE/PRODUCT — needs one fact from you] Card as an office-door credential**~~
  **CLOSED 2026-08-03: the reader is an HID ProX. Not possible on this board, and not close.**
  _(Opened 2026-08-03 from `firmware/NFC Chip Integration Possibilities - Google Gemini.pdf`;
  closed the same day when DRH named the reader — this item existed to hold exactly that one
  fact, and it landed on the dead-end branch.)_

  HID **Prox** is the **125 kHz** low-frequency line (ProxCard / ProxPoint / ProxPro /
  ThinLine / MiniProx), not the 13.56 MHz iCLASS line. The card's whole radio is 13.56 MHz, so
  the gap is physics, not firmware:
  - The coil is **6.5 turns, ~1.09 µH** bare-copper (consistency check `[13]`). Resonating at
    125 kHz against the placed C9 47 pF would need **34.5 mH — 31,644× more inductance.**
    Since L ∝ N² for fixed geometry, that is roughly **1,156 turns** where the card has 6.5.
    An LF antenna is a ferrite rod with a thousand turns of fine wire; it is not a spiral
    etched into a business card.
  - Independently fatal: the **NT3H2211 is an ISO 14443A part with no LF mode at all.** Even
    handed a perfect 125 kHz antenna it cannot speak HID's proprietary Prox modulation, and
    the reader wants Wiegand out of a Prox credential.

  So the two downstream questions are moot: no UID to enroll, and the security trade that made
  this a judgement call (a door credential copyable by anyone you hand a card to) never arises.

  **The one thing that reopens it:** if the door actually carries a **multi-technology** reader
  — HID multiCLASS SE or iCLASS SE, which read 125 kHz Prox *and* 13.56 MHz — then the org is
  merely *issuing* Prox cards while the reader can also take a 14443A UID, and the
  "13.56 MHz UID-only → works today, zero firmware and zero hardware" branch is live again.
  Tell them apart by the model name moulded on the reader body, or by whether a phone wallet
  credential or an iCLASS/Seos card also opens that door. Worth thirty seconds of looking
  before this stays shut.

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

- [x] **[FIRMWARE] Functional audit findings — ALL SIX CLOSED 2026-08-02** _(2026-07-26; surfaced
  by the pass-3/pass-4 firmware audits, carried honestly, now landed in one batch. Build verified
  warning-free under `WERROR=1` on the pinned toolchain; README size figure updated in the same
  commit per the gate.)_
  (a) **`adc_read_raw` wake-count guard** → FIXED: the 3-wake sleep loop stays as the cheap common
  path, and a ~20 ms bounded-spin tail is now the actual TIME bound — three co-arriving interrupts
  (a phone tap is PIT+accel+FD at once) can no longer make a healthy ADC read as "dark" and eat a
  light edge. A dead ADC still exits 0; the WDT stays the recovery.
  (b) **ADXL367 config inside the 100 ms data-valid window** → FIXED: `_delay_ms(140)` after
  MEASURE (datasheet: "a 100 ms wait time must be observed before reading acceleration data"
  + 1/ODR). **140, not 110**, because `_delay_ms` bakes in a 1 MHz cycle count and an un-fused part
  runs CLK_PER at 1.25 MHz — 110 would elapse in 88 ms and land back inside the window on exactly
  the un-fused first article that matters most. _Severity corrected 2026-08-02 after review: the
  original filing (and my first comment) said this risked a phantom tap from settling data. It does
  not — `TAP_THRESH` is 1.5 g, above anything a stationary settle reaches, and a non-zero
  `TAP_LATENT` arms the hardware double-tap engine so a single-tap interrupt cannot surface for
  `TAP_LATENT + TAP_WINDOW` = 280 ms, long after the latch clears at any clock speed. The wait is
  datasheet compliance for the acceleration-data path (`adxl367_read_z`), cheaply bought at boot;
  it was never the tap guard it was described as._
  (c) **Tap tally single-cell wear** → FIXED: wear-levelled 8-slot ring at EEPROM 12–43 (monotonic
  counter, max = latest, no sequence field) — ~800 k tap ceiling instead of 100 k. Offsets 0–3
  retired (no fielded card ever wrote them; no migration needed).
  (d) **`EE_WRITE_FLOOR_MV` node mismatch** → DOCUMENTED in board.h: below ~3.3 V the LDO is in
  dropout so VDD tracks STO within mV; above, VDD is regulated — the compare guards the hazard's
  node across the whole range, only the label was loose.
  (e) **`twi_bus_clear()` START-then-STOP** → FIXED: SDA now drops under a LOW SCL (data move, not
  a START) before the STOP is formed — one clean STOP, no illegal sequence.
  (f) **No Lock Control TLV** → RESOLVED DELIBERATE, not a defect: NXP AN11786 Table 2 gives this
  exact no-TLV init (CC `E1 10 6D 00` + NDEF TLV) as the one "recommended … unless there are
  special needs" on NTAG I²C plus 1k/2k; the TLV becomes required only if the CC size byte ever
  grows past 6Dh (recorded beside `ndef_default[]` with the revisit trigger).


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

- [ ] **[PCB — superseded reference] U6 alternatives considered**
  _(2026-08-05. The first-pass answer said "no clean option"; that was wrong — it searched inside
  TI's TPS229xx family and stopped. The decision has since LANDED — TPS22919 is U6 on the board
  and schematic as of 2026-08-05; this table stays as the do-not-re-research record.)_
  TPS22917 exists in exactly ONE package (SOT-23-6/DBV, drawing
  DBV0006A "SOT-23 - 1.45 mm max height") and has **no `-Q1` in any package** — so the temp-grade-up
  policy recorded for `TPS22918 -> TPS22918-Q1` was silently dropped when U6 became TPS22917. Both
  candidates below restore or improve on something the incumbent lacks.

  | | TPS22917 (now) | **TPS22919** SC-70-6 | **MIC94085** UDFN |
  |---|---|---|---|
  | Height | 1.45 | **1.10** | **0.60** |
  | ISD typ | 10 nA | **2 nA** | 20 nA |
  | ISD max | 250 nA (only to +105 °C) | 20 nA @25 °C; 800 nA to +125 °C | 1 µA |
  | IQ (ON) | **0.5 µA** | 8 µA | 8 µA |
  | Turn-on | 100 µs (CT open) | 1.75 ms fixed | 120 µs |
  | QOD | 150 Ω pin→VOUT | 24 Ω internal | 250 Ω internal |
  | Reverse blocking | yes | no | no |
  | AEC-Q100 | **none exists** | **yes** (`TPS22919QDCKRQ1`) | no |
  | Price / stock | $1.14 / 9,265 | **$0.23 / 45,198** | $0.60 / 21,246 + 6,107 |

  **The temperature comparison is not apples-to-apples and it favours TPS22919.** The incumbent's
  table simply STOPS at +105 °C — it guarantees nothing above that. TPS22919 specifies to +125 °C,
  and at 25 °C promises **≤20 nA** where the incumbent only promises ≤100 nA. The 800 nA is a
  +125 °C corner figure for a card that lives in a wallet. Its real cost is **IQ: 8 µA vs 0.5 µA**
  during NFC windows (N-channel charge pump), plus no reverse blocking and a fixed 1.75 ms ramp.
  There is precedent — the notes accepted TPS22918's 8.3 µA — but the swap TO TPS22917 was made
  deliberately to escape it, so this reopens a closed decision.

  **Neither buys thickness while C25/C26/C27 hold 1.45.** Decide on leakage, price, AEC-Q100 and
  area, not on millimetres. _(2026-08-06: that hold broke — C25–C27 moved to the low-profile
  1206 GRM319 at 0.95 max, so the non-supercap wall is now C9/Q2 at 1.25/1.20.)_

- [ ] **[PCB — CLOSED, do not re-derive] C26/C27 cannot be thinned *in 0805*; and the old incumbent is nearly out of stock**
  _(2026-08-05. Recorded so this is not researched a third time. 2026-08-06: ESCAPED BY CASE
  SIZE, which this item's verdict never covered — C25–C27 moved to the low-profile **1206**
  Murata GRM319 (22 µF 16 V X5R `GRM319R61C226KE15D`; 10 µF 25 V X5R `GRM319R61E106KA12D`;
  0.85 ±0.10 → 0.95 max, both Active, live-verified). The X7R→X5R trade is deliberate: no
  low-profile 10 µF true-X7R exists in ANY case size, and the supercaps cap the system at
  +85 °C — exactly X5R's window. Everything below stands as the 0805 record, including the
  ORDER-BLOCKING note, which is now MOOT — the CL21B106KOQNNNG is no longer bought.)_
  **No vendor makes a 10 µF / 16 V / true-X7R / 0805 thinner than 1.40 mm max, and our Samsung
  `CL21B106KOQNNNG` is the thinnest that exists.** Every such part industry-wide is the same 1.25 mm
  nominal; only the tolerance grade differs (Samsung ±0.15 → 1.40; everyone else ±0.20 → 1.45). TDK
  and Vishay do not offer it at 16 V in 0805 at all. Dropping to 10 V or 6.3 V buys **0.00 mm** —
  Samsung's 10 V and 6.3 V parts are also 1.40 — so the deliberate 16 V DC-bias choice is
  thickness-free and stands. X7S and X7T also buy nothing (1.40, 1.45). X6S reaches 1.00 mm but
  costs the 125 °C ceiling and is NRND.

  **The `2 × 4.7 µF` route was proposed and is REFUTED, twice over.** The low-profile 0805 class
  (0.85 ±0.10 → 0.95 max) does carry 4.7 µF/16 V/X7R, but: (1) **EOL** — Taiyo Yuden renumbered its
  catalogue, legacy PNs went NRND 2023-04-01 and EOL 2025-04-01, and `EMK212BB7475MD-T`'s own spec
  sheet says *"Lifecycle Stage: New PN available"* on the very page the dimension comes from; the
  successor `MSASE219LB7475MTNA01` is 0 stock everywhere. (2) **Effective capacitance** — the
  datasheet's DC-bias curve reads −55 % at 5.5 V, and STO charges to VOVCH 4.65 V (~−46 %), so the
  pair delivers **~5.1 µF effective against the AEM10300's CINT = 10 µF requirement**. Tolerance
  alone regresses before any bias: incumbent ±10 % → 9.00 µF worst case; the pair at ±20 % → 7.52 µF.
  This is the failure the project already hit once, when C25 was re-picked 2026-07-30 "because the
  0603/10V one derated under the AEM's CSRC minimum."

  Two further blockers if anyone revisits: check [7]'s `MODEL_NOTES` waiver is keyed **by model, not
  refdes**, so waiving `C_0805_2012Metric` to allow a 0.95 declaration would blind the check for C25
  and C9 as well; and C27 sits on the tracked 4.17 mm² live-pad-under-titanium ledger and is named in
  `scripts/interference_drc.py`'s `EDGE_LEDGER`.

  **ORDER-BLOCKING:** `CL21B106KOQNNNG` is **0 stock at DigiKey**, 394 at Mouser. You need 20 for a
  10-card build. Buy them with the order, not after.

- [ ] **[PCB/CI — fab hazard] The PANEL config has no `check_zone_fills`, and the panel is what you upload**
  _(2026-08-04, found by an adversarial re-check of a board change I had already called clean.)_
  `PCB/solar-glow-drh.kibot.yaml:18` sets `check_zone_fills: true`, with a comment naming exactly
  this hazard — without it KiBot "checks whatever fill was last SAVED". **`PCB/solar-glow-drh-panel.kibot.yaml`
  has no preflight block at all.** Its own header explains why it skips ERC/DRC (no schematic,
  the frame's plating bus is deliberately unconnected, "panelising adds frame geometry, it does
  not move a single board object") — sound for DRC, and it misses the fill question entirely:
  the panel plots gerbers from the board's **stored** fill.

  **Demonstrated, not theorised.** A pad moved by text surgery with stale fills left 6.9709 mm²
  of GND pour on `SC4.P` (net `MID`). The 1-up gerbers were clean — its config refills. The panel
  rebuilt from the same board carried **the identical 6.9709 mm²**. `PCB/README.md:336` says to
  upload `Generated/panel/solar-glow-drh-v4_0-panel-fab_zip.zip`, so the shorted set is the one
  that gets ordered.
  Two fab sets that disagree, and the wrong one wins.

  **Fix:** add `preflight: check_zone_fills: true` to the panel config. It restores the source PCB
  afterwards, so it cannot rewrite the board — the same reason it is safe in the 1-up config.
  Cheap, and it closes a gap where the *only* surviving copy of a defect is the file you send out.

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

- [x] **[PCB/FAB] Panel fiducials — CLOSED 2026-08-01, built into `panelize.py` as specified**
  _(2026-08-01, found by the kicad-happy second-opinion analyzer on its first run — see
  `docs/kicad-happy.md` → "Integrated".)_ Exactly the derivation this item asked for: three
  Ø1.0 mm bare-copper dots with Ø2.0 mm mask openings (via `solder_mask_margin`), both faces,
  three corners of four on the rails' OUTER band (`FID_INSET` 1.0 from the panel edge → dot edge
  0.5 mm clear of the bus-ring copper, asserted in code), clear of the tooling-hole ring dodges,
  with a 180°-asymmetry guard in `main()` mirroring the tooling holes' own. The merge run's
  panel-gerber diff is the verification; local fiducials near U1 stay a
  only-if-PCBWay-asks option.

- [x] **[PCB — DECIDED 2026-08-02] Board thickness stays 0.6 mm — locked.**
  The call, in the owner's terms: the added stiffness of 0.6 is worth the 0.2 mm it costs the
  stack — added PCB flex is something that makes the card *feel cheaper*, which is exactly what
  this object must not do; a 3.55 vs 3.35 mm assembled height is not perceptible, flex is. The
  verified 0.6 board ships. The engineering picture that informed it is preserved below as
  history; the open sub-questions (show-through, glow brightness vs FR4 thickness) fold into
  first-article measurement, and the empirical half of the decision moves to the feel-coupon
  item that follows.
  _(Original 2026-08-01 assessment, kept as the record:)_ mechanics fine in-assembly (Ti +
  brace + 8 screws carry the card; the shell's `sf_bottom` spotface derives from `board_th`, so
  the same DIN 84 M2×3 stays flush with +0.2 mm MORE Ti engagement); the real open questions
  were daylight show-through of B-side copper through the bare-FR4 windows (flagged at 0.6
  already), panel break-tab redesign for thin FR4, reflow warpage, and the optics/energy re-tune
  (thinner FR4 = brighter glow). 0.2 mm assessed and advised against (depanel fragility +
  show-through for an imperceptible gain).

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

- [x] **[PCB — ride-along] GND return-path stitching vias — CLOSED 2026-08-01, same day** _(from
  the kicad-happy full-mode EMC pass; measured independently from the board file.)_ The trigger
  condition ("whenever the copper next opens for a real reason") arrived hours later with the
  TC1/b1 GUI session, so the nine vias rode along: one GND via on a hatch-crossing of both
  lattices beside each worst cluster (SRC, VNFC, CHG_DIS_G, MID, STO, NFC_EN, VSENSE, the
  coil-adjacent SDA side, VS — coordinates in `docs/kicad-happy.md` → "Integrated"). Before:
  2/82 signal vias had a GND via within 1.0 mm, median nearest 2.75 mm, worst 19.25 mm. The coil
  crossover via at (42.9, 38.0) stays unstitched — inside the coil keepout deliberately.
  Verified: DRC `Errors: 0 (+11 excluded)`, zero F.Mask hits, mask art re-applied and MATCH.

- [x] **[PCB/FW] R1–R4 62.5 mW worst corner — GUARD BUILT 2026-08-02 (`USE_BALLAST_GUARD`)**
  _(2026-07-30, same audit; the "cheapest guard" below is now firmware.)_ `sense_glow_peak()`
  clamps every glow's peak to 225/255 whenever STO > 5.2 V, and main.c now routes the sweep
  peak through the same chokepoint (it was the one animation outside it) — worst-corner
  average lands at 61.8 mW < 62.5 mW rating. Normal harvest never trips the clamp (VOVCH is
  4.65 V); it is insurance against bench supplies and abuse. _(Original numbers, kept:)_
  ballasts `AC0402FR-07150RL` (0402, **1/16 W**); worst DC corner STO 5.5 V through SW2,
  min-bin V<sub>f</sub> 1.9 V (LA P47F 3B bin), V<sub>OL</sub> ≈ 0.4 V ⇒ I ≈ 21 mA ⇒
  **~68–70 mW ≈ 110 % of rating** at 100 % duty; typical ~22 mW. Alternative if the board is
  ever re-laid: 0402 → 0603 (0.1 W) on the four ballasts. No action on the copper.

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

- [x] **[PCB — aesthetic] Frame contains the texture — DECIDED and DONE 2026-08-02, 0.8 mm reveal.**
  _(2026-07-27.)_ The mesh used to run right up to and over the gold frame, serrating its edge;
  `GND_A`'s outline is now the rectangle (2.4, 2.4)–(48.4, 86.5), which leaves a **0.8 mm dark
  reveal** between the frame's inner edge and the mesh, so the frame reads as one clean unbroken
  line containing the texture. **Front only** — `GND_B` is inside the titanium shell and never
  seen, so shrinking it would cost ground copper for nothing.
  What it cost, measured rather than guessed: the front pour drops 2046 → 1778 mm² (13 %); one
  stitching via at (1.67, 39.87) sat in the band that is now bare and **moved to (6.62, 37.77)**
  — verified on a real crossing of both refilled lattices, 0.534 mm clearance, but **5.4 mm from
  where it was**, so it no longer sits beside the cluster it was placed for (revisit if the EMC
  bench ever cares). 34 signal traces cross the reveal band; they are under mask and read as a
  faint sheen rather than texture, which is why the band still reads as clean.
  Verified: DRC ledger byte-identical (0 errors +11 excluded, 5 silk; only the nondeterministic
  mask-bridge count moved, 223 → 222), `mask_art --check` MATCH (the gold layer derives from
  openings and pads, not the pour, so it is unchanged), and — the load-bearing one — the frame,
  the M2 annuli and the plating-bus stub are still **one connected 2005 mm² group** on F.Cu, so
  the hard-gold chain survives.

- [x] **[PCB/FAB — durability] Define the gold area on a user layer instead of in prose**
  _(2026-07-27; the deliberate yes given and DONE 2026-08-02.)_ `scripts/mask_art.py` now draws
  the net rule's result on `User.1` (72 pieces: every F.Mask graphic opening + the NFC arcs + the
  GND pads with front openings, minus the excepted PV solder lands), and both kibot configs plot
  it, so the `User_1` gerber ships in the 1-up and panel fab sets. **It is 394.2 mm² of OPENING,
  of which ~296 mm² is copper** — the rest is bare laminate inside the openings, mostly the
  monogram backlight window. Do not quote 394 as "mm² of gold". Generated, gated
  by check [6], and the generator refuses an area that overlaps a PV land. The predicted drift
  was already real: the README enumeration said *four* mounting annuli; the board has eight
  (MP1–4 were born after the sentence). Both the drawing and the prose now come from the same
  inventory.

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
