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

_Culled 2026-11-13: the two enclosure "DRH's calls" items — eleven open sub-items from the
2026-11-12 measurement, the prose clean-up and the SolidCraft hand-back. Six were fixed in the
generators, four decided by DRH and one (L2) closed as KiCad's model; the record, with both numbers for each, is the design-notes addendum "The
enclosure calls, settled (2026-11-13)", and the verdicts are under Locked._

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

- [ ] **[CI — HELD until the three personal builds are done] Bump the six drifted pip pins**
  _(2026-11-14; DRH's call)._ As of 2026-11-14 the weekly freshness report showed matplotlib
  3.11.1 → 3.11.2, numpy 2.5.2 → 2.5.4, pillow 12.3.0 → **13.0.0** (a major), shapely 2.1.2 →
  2.2.0, trimesh 5.0.0 → 5.2.1 and vtk 9.6.2 → 9.7.2 — re-read the standing "Weekly freshness
  report" issue for today's numbers rather than these. **Why held:** every one of them feeds a
  render or a solid. shapely is pinned in the CAD step beside cadquery, so a bump can move the
  enclosure STEP/STL, not just the pictures; the three units (max Ti, lite brass, air Al) should be
  made from the files that were checked, not from a regeneration in flight. **When the builds are
  done:** move all six in one PR — they are pinned in `.github/workflows/kibot.yml` (five lines)
  and `.github/workflows/consistency.yml` (matplotlib) — and read the merge run's `Generated/`
  diff before calling it done. Expect `scripts/check_mesh.py` re-ledgers if a solid moves, and
  byte-churn in every render and drawing. The KiCad image digest has drifted too; that is the
  same kind of call (dispatch the freshness workflow with `bump_kicad=true`) and is NOT part of
  this item unless DRH adds it.

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

- [ ] **[BENCH/CROSS-DOMAIN — first-article gate] Measure NFC read range, in the shell**
  _(2026-08-09. Added when the U5 VOUT decline was Locked and its reopen condition turned out to
  name a number nobody was scheduled to produce. Searching the tracker for "read range" returned
  the Locked entry and nothing else.)_
  The card's contact story is Locked as **offline-first**: the vCard is embedded in the tag and read
  RF-powered with the supercap flat. That premise assumes a 13.56 MHz link that survives a ferrite
  sheet and a **titanium** back shell, and no one has put a number on it. It is the second-riskiest
  physics on the card after the energy budget, and unlike the energy budget it has no entry.
  Measure, at bring-up, with the brace removable (already Locked as a requirement) and the C9 ladder
  in play:
  - **Baseline sweep:** bare board, then + ferrite, then + shell — max / lite / **air** (the air frame
    is 316L specifically for the coil; this is the run that shows whether that choice paid).
  - Report **millimetres of read distance** per configuration against 2–3 real phones, plus the
    resonance the coil actually lands on. `scripts/nfc_coil.py --check` gives bare-copper L and a
    predicted f0; the ferrite raises L ~1.3–1.5×. **The bench owns the real number** — this is the
    measurement that closes that gap.
  - Record the margin, not just pass/fail. Margin is what every future range-costing decision gets
    judged against, and right now there is nothing to judge against.

  **Gates:** the Locked `U5` VOUT decline reopens only on a margin figure from this; the C9 trim
  value; and whether the air variant earns its existence.

- [ ] **[BENCH — first-article gate] Press-test the solar-cell tab joints: nothing backs them, by decision**
  _(DRH, 2026-11-13, closing the "brace backs none of the four tabs" item.)_ No brace has backed
  the four PV solder tabs since 2026-08-08: the outboard rails that would are cut off from the
  body by the boss reliefs, and the one-piece rule drops them (`fit_rules.DROPPED`). The air
  variant has no brace at all, so the design has to tolerate unbacked tabs regardless — and that
  is what this test establishes, rather than a resin part assumed to. On the first assembled
  card in each shell (max, lite, air): press each cell with a thumb, straight down, at the end
  over its tab land (PV1 / PV2, pads `Nt` and `Pt`: x 4.30 and 46.50, y 15.75 and 73.15), firm
  enough to flex the board visibly, ten times. Then inspect all four joints under magnification
  for a crack line round the fillet or a lifted tab, and re-read each cell's open-circuit voltage
  against its pre-test value. **Fails if** any joint cracks or a cell's V_oc moves. If it fails,
  the options are the ones the decision passed over: print the four rails as separate pieces, or
  bridge each past its mid-edge boss.

- [ ] **[BENCH — first-article gate] Sweep the LED's I-V curve, and the loop current in situ**
  _(2026-08-20. Added after an ASIC-side analysis published a wrong finding off the back of the
  gap: `asic/analog/README.md` briefly claimed a worst-bin LED cannot light at the 2.75 V glow
  floor. It was the 30 mA Vf applied at 0.67 mA. Retracted — but the retraction only says the
  low rail is UNMODELLED, and nothing in the tree can model it.)_
  **The whole repo has exactly one Vf datum: `1.95-2.55 V at 30 mA`** (unbinned 3B-5A,
  `PCB/README.md`). Every current figure the card and the ASIC compute leans on it, and most of
  them lean on it far from 30 mA. `asic/analog/sink_budget.py` now prints each row's distance
  from that spec point, and the glow-floor row is **0.11x — not usable**. This is the
  measurement that makes the bottom of the operating range real.

  **(a) The part, on a breakout — the curve itself.** Sweep If from **~10 uA to 30 mA** (3.5
  decades; the same wide-dynamic-range problem `docs/harvest-bench-fixture-handoff.md` §2 calls
  out for the panel) and record Vf at each point, at room temperature. **Sample several parts**:
  the LA P47F is shipped UNBINNED across 3B-5A, so bin spread — not measurement error — is the
  dominant uncertainty, and one part tells you almost nothing about the corner.

  **(b) The loop, on a real card — what the energy budget actually needs.** With SW2 on, sweep
  STO from the **2.75 V glow floor to the 4.65 V VOVCH ceiling** and record per-LED current at
  100 % duty. That folds in the ballast, the sink drop and Vf together, which is the number the
  budget wants; the part curve in (a) is what lets you attribute a surprise to the right term.

  **What it settles, each of which is currently an assumption:**
  - **The low-rail end.** Does a max-Vf part conduct at 2.75 V, and how brightly? `board.h`'s
    `VS_GLOW_FLOOR_MV` was chosen without this, and if the answer is "barely", the floor is
    mis-set for part of the bin distribution. **This converges with the
    `VS_GLOW_FLOOR_MV` vs STO-channel accuracy item below**, which reaches the same
    constant from the opposite side — sense tolerance, not LED physics — and lands on a floor
    near **2900 mV**. Two independent arguments pointing the same way; take both
    measurements before moving the constant once.
  - **`VF_GUARD` = 1.90 V.** F1's clamp margin (`GLOW_CLAMP_PEAK` 221) rests on it, and 1.90 is
    *below* the 1.95 V datasheet floor **at 30 mA**. It is plausibly right at 22 mA because Vf
    falls with current — i.e. the margin currently holds by two errors cancelling, not by
    derivation. **Do not "correct" 1.90 to 1.95 without this curve**: that lowers the computed
    current and makes the clamp look safer than it is.
  - **The published "~16 mA".** `README.md`'s "The open question" computes it as
    `(4.65 - 2.25)/150` — **no sink drop at all**. With the AVR's ~0.4 V VOL the same loop gives
    **13.3 mA**. Both numbers are in the tree; the sweep says which one the budget should use.
  - **Whether 150 ohm is right.** `PCB/README.md` flags R1-R4 as **SIZED, not locked** and
    bench-pending. A re-tune moves the corner `sink_budget.py` gates the clamp against — the
    guard will go red rather than drift, but only this measurement tells you where to move it.

  **Where the results land:** `PCB/README.md`'s Vf row (add the low-current points and the spec
  condition), `asic/analog/sink_budget.py`'s `VF_*` constants and its MODEL VALIDITY note, and
  the envelope table's "not usable" row — which should stop saying that.

  **Gates:** the #1 energy-budget item's draw side; F1's margin; the retracted F2; and any
  future re-tune of the 150 ohm ballast.

- [ ] **[BENCH — first-article gate] Find the system's true low-rail floor, and set TH_CRIT from it**
  _(2026-08-20. `asic/rtl/sense_seq.v`'s `TH_CRIT_MV` = 2000 is the one threshold in that module
  with **no firmware anchor** — the card has no second rail gate — so it was sourced to the
  AEM10300 selection analysis's "drain to ~2 V at the load". That is a statement about what the
  HARVESTER can deliver, not about what THIS LOAD can still run on, and those are different
  questions.)_

  **It is an energy-budget claim in disguise, and the arithmetic is not small.** On the real tank
  (2S2P, **1.40 F**, 15.14 J at the 4.65 V VOVCH ceiling):

  | spend down to | stored left | spendable |
  |---|---|---|
  | 2.75 V — the card's glow floor | 5.29 J | **9.84 J** (README's "9.8 J spendable") |
  | 2.60 V — the AVR's BOD | 4.73 J | 10.40 J |
  | 2.00 V — `TH_CRIT` as set | 2.80 J | **12.34 J** |

  So `TH_CRIT` = 2000 mV quietly asserts **+25.3 % usable energy** over the number the card
  publishes. Nobody has justified that, and it is exactly the kind of claim the #1 energy-budget
  gate exists to settle.

  **And the ordering argument says 2.0 V is probably wrong in principle.** DORMANT exists to STOP
  SPENDING so the tank can recover — so it has to engage **above** the point where the system
  stops working, not at it. A design that has already browned out cannot execute the transition.
  The card's own floor is the AVR's **BOD at 2.60 V**, and `VS_GLOW_FLOOR_MV` = 2750 is derived
  from it explicitly (`board.h`: 2600 + 150 mV of glow-sag margin). `TH_CRIT` sits 600 mV
  **below** that floor.

  **What has to be established, in order:**
  - **(a) Desk work first, and it has no home yet.** The minimum operating voltage of every part
    still on `VS` once the ASIC replaces U1 — **ADXL367, NT3H2211, MB85RC512TY** — plus what the
    TPS7A0233 does below dropout (`board.h` already notes VS tracks STO under ~3.3 V, so at
    STO 2.0 V every peripheral sees ~2.0 V). The tree currently has exactly one datum near this:
    `adxl367.h`'s 0.89 µA is specified *at a 2.0 V supply*, which shows the accel runs there but
    says nothing about the others. Record the set in one place; today there isn't one.
  - **(b) The ASIC's own Vmin is a GF180/PDK question this experiment does not claim.** It
    blocks a final number, and `asic/README.md` should not pretend otherwise.
  - **(c) Bench, on the first article.** Walk STO down and record where each function actually
    fails — tap detection, NFC read, FRAM write, glow — rather than where a datasheet says it
    might. That floor is the answer, and it feeds the CARD's numbers too, not just the ASIC's.

  **Then** set `TH_CRIT` from it and reconcile against `VS_GLOW_FLOOR_MV`, so both thresholds
  derive from one measured floor instead of two unrelated arguments.

  **Guard already in place:** `tb_sense_seq`'s check D asserts `vcrit < vlow < clamp` on the
  DISCOVERED boundaries, because the likely revision here is *upward* toward the glow floor —
  the direction that breaks the ordering. It goes red rather than producing a supervisor that
  enters dormancy while the glow gate still reads healthy.

  **Converges with** the `VS_GLOW_FLOOR_MV` vs STO-channel-accuracy item and the LED I-V sweep
  above: three separate arguments, all about where the bottom of the operating range really is.
  Take the measurements together.

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

- [ ] **[V-NEXT, PARKED] Companion ASIC — Tiny Tapeout proving ground → wafer.space quarter
  slot; the RTL experiment is BUILT (`asic/`)**
  _(Banked 2026-08-10 after the custom-silicon investigation; `asic/README.md` is the
  experiment's verdict and `asic/SPEC.md` the design contract. Deliberately NOT a v4 item —
  nothing here touches the board being ordered.)_
  **The two-rung ladder, with the numbers that matter:**
  - **Rung 1 — Tiny Tapeout (proof, not product):** €70/tile (~1 k gates, SKY130), fixed
    8 in / 8 out / 8 bidir behind a shared-die mux, ~1 year to a demo board. It CANNOT yield
    a shippable part — shared die, and the IHP shuttle's terms ban commercial use outright —
    but it proves a block on real silicon for the price of a datasheet binder.
    Shuttles at banking time: SKY26c closes **2026-09-07**, IHP26b **2026-09-21**.
  - **Rung 2 — wafer.space GF180MCU (the product path):** 180 nm mixed-signal (MIM caps,
    poly + hi-res resistors), **quarter slot = 4.9 mm², $2,000 early / $3,000, 1,000 dies,
    48 I/O + 8 power pads** (~1.94 × 2.54 mm; full slot 20.12 mm² / $7,000 is NOT needed —
    see below). Run 3: early-bird **2026-09-30**, purchase **2026-12-09**, submission
    **2026-12-16**, dies **Q2 2027**. You receive **BARE DIE** — packaging (COB or bond-out)
    and test are the unpriced half of the project. Tiny Tapeout's padframe is deliberately
    wafer.space-compatible, which is what makes rung 1 → rung 2 a straight lift.
  - **What the chip absorbs** (the green set from the absorb-map figure, 2026-08-10):
    U1's application logic, the whole STO sense chain's sequencing (R15/R16/C24 divider in
    hi-res poly + U10's gate + the deferred-read cadence in gates), Q2+R18, RN1, RN2, U6.
    Stretch: U9 (25 nA analog LDO — first-silicon risk). NEVER: U3 (MEMS), U5 (RF+EEPROM),
    U7 (FRAM process), U8+L2 (the harvester and its inductor), supercaps, cells, LEDs.
  - **Quarter over full, decided:** ~25 signals against 48 pads, and the digital core is now
    MEASURED, not estimated: 3,261 NAND-mapped cells / 251 DFFs = 0.13–0.25 mm², **3–5 % of
    the slot** (yosys, regenerate via `make gates` in `asic/`) — the analog is what sizes the chip — and $4k buys TWO quarter-slot attempts across two runs (a respin
    cycle) where $7k buys one full-slot shot with ~80 % of the die empty. First silicon is
    usually wrong somewhere; optionality beats area.
  - **The open question the experiment could not close:** whether the quarter-slot padframe
    exposes enough ANALOG-capable pads (STO sense input, four 16 mA LED sinks) — ask
    wafer.space directly before buying a slot.
  - **Wake this item only after the v4 first article ships.** The card's critical path is
    the energy budget and the read-range sweep; this ladder starts at €70 whenever there is
    slack, and the deadlines above roll over to the next run if missed.
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

- [ ] **[BENCH/FIRMWARE — first-article gate] The linked EEPROM write never issues NOCMD — confirm a multi-byte write lands whole**
  _(2026-11-14 firmware check. A question for silicon, not a known bug; no code was changed for it.)_
  Every EEPROM cell here is written through avr-libc's `eeprom_update_*`, and on this part the body
  of that routine comes out of the AVR-Ex pack. Disassembled from the build (`eeprom_write_r18`): wait
  for `NVMCTRL.STATUS` EEBUSY to clear, store the byte into the page buffer, `CCP = 0x9D`,
  `NVMCTRL.CTRLA = 0x15` (EEPERW). **It never writes NOCMD**, so CTRLA still holds EEPERW when the next
  byte's EEPERW arrives. DS40002443A §11.5.1: _"It is recommended to include a NOCMD or NOOP
  instruction when going from one command to the next to avoid Command Collision error being set"_ —
  and `STATUS.ERROR` = 0x03 is CMDCOLLISION, _"Selecting a new write command while a write command is
  already selected"_. DxCore's EEPROM library for the EA/EB does write 0 to CTRLA before each 0x15
  (its source, read 2026-11-14). The datasheet in `datasheets/` is revision A and marked Preliminary
  (2022), so how binding "recommended" is on real silicon is exactly what is not known.
  - **What it would break.** Every multi-byte cell: the tap ring's dwords, sun hours, min-rail and the
    power-cycle count. `eeprom_update_word` is two byte writes back to back, **high byte first**; if
    the second command is refused, the cell keeps its new high byte over a stale low one — a value
    that looks plausible and is wrong. And if a command is refused whenever CTRLA is not NOCMD, then
    only the first byte written after each reset ever lands.
  - **Bench, with the production image and no special build.** From an erased EEPROM (a fresh part
    is), power up cold, hold STO above `EE_WRITE_FLOOR_MV` (2.85 V) for 20 s without tapping, then
    read offsets 7–10 over UPDI. The first sample writes the min-rail word (7–8) and then the power-cycle word (9–10), four
    byte writes in a row. **Pass: `LL HH 01 00`**, where `HHLL` is the tank in mV (3900 mV reads
    `3C 0F 01 00`). **The collision signature is `FF HH FF FF`**: only the first byte landed.
  - Then tap once and read the ring at 12–43: one slot must read `01 00 00 00`. That write follows
    a sleep rather than a reset, so both cases are covered.
  - If a debugger is on the bench, also read `NVMCTRL.STATUS` (0x1006) straight after a write:
    `ERROR` (bits 6:4) must be 0, not 3.
  - **If it fails:** stop using the library routine. Write a local byte-write that issues
    `NVMCTRL_CMD_NOCMD_gc` under CCP before each EEPERW (the DxCore sequence), point the five writers
    in `sense.c` at it, and take it through `make check` and the size gate. Until then the counters
    cannot be trusted and nothing else on the card is affected.

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
  **Pair this with the LED I-V sweep above** (2026-08-20): that item reaches the same constant
  from the LED side — whether a max-Vf part can conduct at all at 2750 mV — and also lands near
  2900. Independent arguments, same direction; measure both before moving the floor once.

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

- [ ] **[LAYOUT — v5] Inert index posts beside the supercaps, tied to GND**
  _(2026-08-23. DRH places them manually; re-derive every coordinate below with
  `python3 scripts/index_posts.py`, which computes them from the current board — do not
  hand-edit the numbers here.)_
  Cheap chip parts soldered beside SC1–SC4 so a hand-placed cap seats against something
  sacrificial instead of against a live component. **Two on each cap's LONG datum edge, one
  on the short** — a two-point contact is what constrains **rotation**, and rotation is the
  dominant placement error (1° swings a 39 mm cap's corner 0.34 mm; the caps reach a real
  part at 2.02–6.71°). One post stops translation and does nothing about rotation. Datum
  edges are `fit_rules.CAP_DATUM`, i.e. the same two the reflow shim indexes.
  - **Net: GND.** Not floating and **not a live rail** — a part whose job is to be struck by
    a 17 × 39 mm slab should fail cosmetically, not electrically. GND over floating is for
    MECHANICS, not function: a pad bonded to the pour has more copper anchorage against
    lateral load. Costs thermal relief to solder.
  - **Not capacitors.** Contributory energy storage fails by three orders of magnitude: all
    ten placeable sites filled with the largest 6.3 V X5R each is **706 µF nominal = 0.05 %
    of the 1.40 F tank**, 4.96 mJ of its 9.84 J usable, and ~0.015 % after a realistic 30 %
    DC-bias derate. 1 % of the tank would need 14,000 µF. No ESR case either — the SCPC cells
    are 25/40 mΩ (30.8 mΩ for the bank), so the 22.46 mA LED envelope droops **0.69 mV**. No
    balancing case — the AEM10300's BAL pin already holds the midpoint, which is why U2 was
    deleted in v4. Decoupling belongs at the pin: C27 (10 µF) is already 4.84 mm from U8.
  - **Measured today, 10 of 12 sites place** (collision against body ∪ pads + 0.20 mm, dnp
    copper included). **Only SC3 gets a working rotation datum** — 2 solid posts on its long
    edge. SC1 and SC2 get 1 each; SC4 gets 0. `SC1 E@80 %` is blocked by **C11** and
    `SC4 W@20 %` by **Q2**; moving those two is what would give all four caps a datum.
  - Packages fall out of local room, not choice: 2512 → 1206 → 0805 → 0603. **0603 is
    INADEQUATE for shear** (`PCB/README.md`: "a 0402 will shear before it indexes a
    supercap"); 0805 is marginal. Two sites currently land on 0603.
  - **These are real footprints and they are not free.** Each one needs: a
    `part_heights.py` entry (`part_height()` **raises** on an unmapped refdes), a BOM line
    with MPN **and** Manufacturer (`bom_split.build()` fails on an MPN with no manufacturer),
    a CPL row (check [15] gates pick-and-place against BOM), a `part_colors.py` colour
    (check [10]) and a 3D model — and each becomes a brace blocker or pocket, so the
    footprint recomputes. Budget the gate work with the placement.
  - Suggested refdes `MP1`–`MP12` rather than an `R` prefix, so nothing reads them as circuit
    resistors. Value `0R`.
  - **What this does NOT replace:** the reflow shim (`enclosure/shim/README.md`). Posts index
    but cannot clamp, and the caps must be held while the paste is molten. The prize if all
    four caps ever get a real rotation datum is decoupling the brace from the shim — today
    the anisotropic bays mean the brace only fits a cap the shim seated.

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

- [ ] **[ENCLOSURE — BLOCKS EVERY FAB ORDER; first thing after the merge run] Re-measure the rebuilt solids on SolidCraft**
  _(2026-11-12; the frame added 2026-11-13.)_ **Until this is done, do not send any STEP or STL from
  this tree to a shop or a printer.** _(That sentence used to close the entry above this one --
  "The emitted solids are MIRROR IMAGES of the parts: decide the frame" -- which is culled: the
  decision was taken on 2026-11-13, option (a), reflect once at export. `CLAUDE.md` has the three
  rules it left behind, `enclosure/fit_rules.py` the frame, and `scripts/handedness_drc.py` the
  gate.)_ Nothing in the cloud can confirm the fixes: SolidCraft exists only on DRH's
  machine. The cloud session rebuilt everything with CI's pins and measured it with OpenCascade —
  an instrument that reproduces every SolidCraft figure on `main` to the last digit (max shell
  5290.7426 mm³, cap overlaps 2.3122 / 0.7343 / 1.6998 / 1.8132 mm³, brace overlap 9.0186 mm³, 13
  four-face edges, 804 sliver faces, four seat-level faces of 24.896 mm²) — but it is the same kernel
  that wrote the files, which is exactly what the original measurement was designed to avoid. On the
  solids the merge run commits, check:
  - **No supercap-to-boss overlap**, max / lite / air. Expect a flat on every boss, **0.750 mm** off
    the can's free edge (its bay clearance): faces at board x 4.345 (SC1), 4.415 (SC3), 46.254 (SC2),
    46.406 (SC4). The two east mid-span bosses also meet SC2's and SC4's datum ends, 0.25 off.
    _(Was 0.200 off a nominal can until 2026-11-13 — see the boss item below.)_
  - **No brace-to-shell overlap**, max and lite. Expect the brace's east face at x **49.500** against
    a wall at 49.550.
  - **The four downward faces at seat level are gone** (24.896 mm², max and lite; the air frame had
    them too).
  - **The max shell STEP imports with no edge repair.** Expect **28,526 edges, none shared by more
    than two faces; 9,648 faces, 36 of them under 0.001 mm²**; no upward faces at z +0.02. _(Counts
    re-taken 2026-11-14 by OCC on the STEP `main` carries, built at `a4f951e`. The 28,403 / 9,626 /
    82 that stood here until then were of `9a90a36`, the solids before the enclosure-calls round —
    which is why the MEASURED block below, a record of that commit, still reads them.)_
  - **The open frame still has its resting-face edge-break**, including a 45° foot on each boss flat.
  - **No brace resin wall under 0.10 mm**, max and lite, and none under `SLA_WALL` 0.60 except the
    ferrite channel's own walls (x 36.2–36.7 and 49.10, top 0.33 mm only). The 0.0068 mm wall at
    (4.411, 49.653) is the canary: it must be gone.
  - **The files are the parts, not their mirror images** (written right-handed since 2026-11-13).
    In a shell's or a brace's file a board point (x, y) is at **(x − 25.4, 44.45 − y)**: y runs UP
    now, so every board coordinate in this list reads that way in SolidCraft. Expect:
    - against KiCad's STEP export of the populated board, placed by a translation alone and NOT
      mirrored: the **max brace overlaps one part, L2, by 0.047 mm³** (KiCad's generic 1008 body,
      1.20 tall where the part fitted is 1.00 — the item on L2 below) and the **lite brace
      nothing**. Mirrored, they must collide: 52.8 mm³ over 33 parts and 487.6 over 28 (max),
      52.9 over 34 and 301.5 over 28 (lite). Those are this tree's braces; the 53.1 / 493.9
      SolidCraft first reported were the braces at `d060215`, before the level opening;
    - **the medallion reads correctly from behind** — DRH, No 001, and SOLAR · NFC · TITANIUM ·
      ATL GA · MMXXVI clockwise round the ring;
    - **the pogo plate takes the panel face-UP**: its two dowel bores under TH1 and TH2 (file
      (−4.9, −20.0) and (55.7, −85.0); the plate is un-centred, a board point (x, y) is at
      (x, −y)), and its title and net labels reading correctly from above;
    - the max shell STEP's counts are what they were — the reflection changes no face, edge or
      volume (**5289.905 mm³** by OCC on today's STEP; 5293.129 was `9a90a36`'s).
    `scripts/handedness_drc.py` measures the first and third of these on every CI run, in the
    kernel that wrote the files; this is the check in one that did not.

  **MEASURED 2026-11-13 on `9a90a36` — SolidCraft 0.40.1, the files exactly as committed, the board
  re-exported with `kicad-cli` (49 bodies: the PCB and all 48 modelled parts).** _(The box above is
  left open on purpose: one expectation below is not met, two observations are new, and ticking it
  is what releases an order — DRH's call.)_ The instrument was made to fail first: the max brace
  pushed 0.50 mm into the PCB reads 329.2333 mm³ against 329.2333 by hand from its own face areas.
  All six STEPs import closed, one solid each, with no warning (max shell 5293.1293 mm³).
  - Supercap to boss: **met.** No overlap on max / lite / air. Face to face, the eight free-edge
    flats stand 0.7500 mm off the cans (x 4.345, 4.415, 46.254, 46.406) and the two datum ends
    0.2500 (y 29.774 on SC2's boss, y 59.150 on SC4's), identical on all three shells.
  - Brace to shell: **met.** No overlap, max and lite; east face x 49.500 against a wall at 49.550,
    west face 2.550 against 2.500.
  - Seat-level faces: **met.** Gone on max, lite and air. (Three faces of 0.000 mm² remain at the
    seat corners, 0.01 mm tall, as they did before.)
  - Max shell STEP: **met.** No repair needed; 28,403 edges, none shared by four faces; 9,626
    faces, 82 under 0.001 mm²; nothing facing up at z +0.02.
  - Open-frame edge-break: **met.** Each of the ten boss flats carries a 45° face from z 0 to 0.10.
  - Brace walls: **met but for one.** None under 0.10 mm, and the 0.0068 at (4.411, 49.653) is gone.
    Under 0.60 the channel's own five, all 0.33 tall and the same on both braces: 0.2650 (x
    36.435–36.700, y 36.5–39.4), 0.4000 (the east ridge, 25.87 long), and 0.4964 / 0.4980 / 0.5200
    at x 36.2–36.7. **And one that is not the channel's: 0.4632 mm between two pocket corners, from
    (26.600, 11.960) to (26.150, 11.850), both braces.** It is a diagonal neck rather than a
    parallel-faced wall, which may be why rays cast along face normals do not report it.
  - The hand: **met, every figure.** Board placed by a translation alone, nothing mirrored: max
    brace one part, L2, 0.0466 mm³; lite brace nothing. Mirrored: 52.8334 mm³ over 33 parts and
    487.5701 over 28 (max), 52.9328 over 34 and 301.4910 over 28 (lite). From behind the medallion
    reads DRH, No 001, and SOLAR · NFC · TITANIUM · ATL GA · MMXXVI clockwise. The pogo plate's
    Ø1.45 bores are at file (−4.9, −20.0) and (55.7, −85.0), and its title and net labels read from
    above. Hole registration is still 0.000000 mm at all eight mounts on all three shells.

  Two things the list did not ask about, both DRH's to weigh:
  - **Seven zero-radius internal corners now run the full cavity height** (max and lite; six on
    air). Two are 90°, at (46.254, 29.774) and (46.406, 59.150): the corners of SC2's and SC4's
    keep-outs where they cut into the east mid-span bosses. Five are 42–44°, at y 0.050 (x 4.210,
    22.977, 46.357) and y 88.850 (x 4.283, 46.538), where a relief arc meets the straight recess
    line; the air frame has no corner at x 22.977. A round tool leaves its own radius in each.
  - **C24 to the lip reads 0.1574 mm on SolidCraft, where the sectioned gate has 0.097** (KiCad's
    exported pad solid against the lite shell, at (2.558, 49.310)), and no pad of R16 is within
    0.30 mm where the gate has 0.268. C24 is inside `LIP_CLR` either way. Why the two numbers
    differ was not determined.

  Unchanged, and already in the item below: the 0.05 mm press fit (5.89974 mm³, all three shells),
  L2 (0.04661 mm³), and 0.060 mm over the supercaps with KiCad's seating against 0.10 with parts
  flush. One instrument note: a clearance run against a twice-split slab of the max shell returned
  0.1649 mm for SC4 at a point where a probe finds no material; it was discarded in favour of the
  face-to-face figures above. Not re-measured: clearance against the un-split max shell, and wall
  thickness beyond the two surveys used (distances between distinct voids, and opposed
  axis-aligned faces). The east lip's stepped top was measured afterwards: C1 below. The full
  report and every command are kept outside the tree, beside the first review's.

  **MEASURED AFTERWARDS on the same `9a90a36` — SolidCraft's later checks, handed back 2026-11-13,
  each re-checked in this repo with an instrument of its own.** _(SolidCraft's figures as written;
  this repo's beside them, with how. "Inferred" is SolidCraft's arithmetic or code reading on top
  of a measurement. Lite-shell heights unless stated: floor top z 0.600, seat 1.820, rim 2.420.)_
  - **A — agreement, nothing to change.** Every committed STL is the same part as its STEP (largest
    deviation 0.0000 braces, 0.0047 shells, 0.0117 pogo plate over 0.037 mm²; canaried). Every
    dimension on the six sheets matches its STEP but the B items. The pogo plate's 14 bores sit
    0.0000 off KiCad's own pad solids, its dowels on the panel drill file's two Ø1.500 NPTH, and the
    populated card overlaps nothing on it. Not re-checked here beyond what B to D touch.
  - **B — sheet text the solids contradict.** Fixed in the same commit as this record, each
    sentence now computed from what it describes or removed:
    - **B1**, shell note 4: "ITS 4 OUTBOARD RAILS". SolidCraft: no resin within 14.0 of a cell
      pad. Here: each brace STL is one body, and the nearest resin at any height is 14.067 from a
      tab-land centre (sectioned every 0.15 mm). The note now gives the piece count from
      `brace_footprint()` and the outline's `WALL_FIT`.
    - **B2**, note 4 "PRESS-FIT" against note 10 "SLIP FIT, NOT A PRESS FIT". The recess measures
      50.700 × 88.800 here as on SolidCraft (STL sectioned at seat + 0.30, along both centre lines,
      all three shells). Both notes now state the modelled fit computed from the sheet's `ef`:
      "0.05 INTERFERENCE PER FLAT AS MODELLED". DRH decided the same day: a press fit, by design
      (Locked; `enclosure/README.md` §8).
    - **B3**, note 5: "(BOSS-TO-WALL + EAST-LIP STEPS)". The east wall is x 49.550 on every
      0.1 mm row clear of a boss (seat − 0.30). The parenthesis is gone, so the sentence covers every
      concave corner left sharp, which C2 counts.
    - **B4**, brace sheets: "12.0 WIDE (CRITICAL)". The CAD cuts `FER` ± `FER_CLR` =
      x 36.700–49.100, 12.400, as SolidCraft measured. The label and note 5 are computed from it.
    - **B6 — declined.** The sheet's bare-lip stretches come from `lip_as_cut()`, which
      `assembly_drc` [G] holds to the sectioned metal (worst 0.002 where one width governs).
      SolidCraft read them at the recess wall (y 0.050 / 88.850), where the relief arcs flare, so
      the two sets differ by up to 0.15 on different lines and both stand. The "2.25 y48.5–49.5
      (C24)" band has no flat in the metal: one vertex, x 2.259 at y 48.798 (SolidCraft); x 2.259
      at y 48.80 here (0.02 mm rows). The Ø2.0 finisher blends a band narrower than its own radius.
    - **B7**, "NO DETACHED ISLAND UNDER 0.55". SolidCraft: five islands 0.545 × 0.549,
      0.2347 mm². Here, from `medallion.geometry()` with the shell's own text function: the same
      five at the same five places, spans 0.5476–0.5497, 0.2339–0.2347 mm². They are the Ø0.55
      regrown rounds as polygons, and the audit has always enforced `MIN_ISLAND − 0.02`. That
      floor is now `medallion.MIN_ISLAND_AUDIT`, read by the audit and printed on the sheet (0.53).
    - **B8**, the LIP break called MODELED. Sectioned here: present on the west straight run
      (y 20.0, 0.10 × 45°), absent on the R16 step (y 47.0, square). Absent over y 4.787–9.900 on the
      east and 0.25 inboard of the east wall elsewhere: the cause is C1's. Note 5 no longer claims
      it; it says to break every lip edge on the part.
    - **B5** is a decision, in the DRH's-calls item below.
  - **C1 — the east lip's top.** SolidCraft: stepped over y 10.000–26.596, 30.664–58.236 and
    62.304–83.996 (wall top z 1.720, a 0.250 flat, 45° to the seat at x 49.900, 0.850 of bearing);
    not stepped over y 4.787–9.900 (full 1.250, no break), whose first 0.832 (y 4.787–5.619) stands
    at z 1.810. Here, sectioning the lite STL at y 5.0, 5.4, 7.0, 9.5, 10.5, 20.0, 44.45 and 70.0: the
    same profile at every station. **Cause, read from the shell CAD here** (SolidCraft had none):
    `_lip_break_cut` cuts from `_lip_void_P()`, the SCALAR lip outline, whose east edge is
    `W − RING["E"]` = x 49.80 except over `EAST_WIDE_Y = [(0.0, 10.0)]`, where it is
    `W − lip_E_wide` = x 48.30, out in the cavity. From y 10 up the cutter lands 0.25 inside the real
    wall (x 49.55) and takes the top 0.10 off that strip, which is the step. Below y 10 it lands on
    no lip, so there is neither step nor break. The north wide band was removed on 2026-07-11 and
    the south one never was, which is the asymmetry. The z 1.810 stretch is C4's corner relief.
  - **C2 — sharp concave corners.**
    - **SolidCraft:** seven run the full cavity height on max and lite, six on air.
      - Two are 90°, at (46.254, 29.774) and (46.406, 59.150), where SC2's and SC4's keep-outs cut
        the east mid-span bosses. #254's free-edge boss flats made these.
      - Five are 42–44°, where a cap relief arc meets the recess line.
    - **Here, each shell STL sectioned at nine heights:**
      - The two 90° corners are at the same points on all three shells.
      - At mid-cavity there are eight recess-line corners on all three, at x 4.210 / 22.977 /
        27.650 / 46.357 (y 0.050) and 4.283 / 23.047 / 27.774 / 46.538 (y 88.850). A different five
        pass the full-height test here on max. The test is sensitive at the seat and floor breaks,
        so **which corners run the full height is left open.**
      - Four more, about 90–102°, sit where a corner boss meets a relief. They are not in
        SolidCraft's list.
      - Then there are the twelve documented boss-to-wall junctions.
    - **With the sheet's Ø2.0 finisher (R1.0) at the two 90° corners:**
      - SolidCraft, inferred from a square-corner model: a nominal can is 0.209 clear of the
        fillet. A can +0.50 on the free edge is 0.061 inside; with the 0.10 datum gap, 0.134 inside.
      - Here, simulating the R1.0 tool on the exact boss island (polygon opening), SC2 / SC4: a
        nominal can clears by 0.266 / 0.225. +0.50 free is 0.013 / 0.030 inside. +0.50 free + 0.10
        datum is 0.060 / 0.084 inside. +0.60 free + 0.10 datum is 0.113 / 0.130 inside.
      - The two models differ because the corner's end face is 0.66 long, under the tool radius,
        so the tool also reaches the corner from the side. **Both say a nominal can clears and a
        max-material can touches.**
    - **Every other sharp corner at R1.0:** `assembly_drc` [F], re-run here with the tool radius
      applied to every concave corner, still clears every nominal B-side body. The tightest is SC4
      at 0.225, from 0.250 as modelled.
  - **C3 — the 0.4632 neck between TP3's and TP2's pockets.**
    - **Reproduced** with a scan from every convex void corner, through resin only. It is
      calibrated: on the committed pre-#254 brace it finds the 0.0068, 0.0718 and 0.0904 walls, and
      on `9a90a36` it finds this neck. It is the only gap under 0.60 in either brace that is not one
      of the ferrite channel's walls.
    - **This repo's own checks missed it** for two reasons. The level opening in the brace CAD is
      mitred, which measures thickness along x and y only. And the pocket-pair pass skips diagonal
      pairs by name ("diagonal corner nick").
    - **It is a gap, not a wall.** A Ø0.6 disc of resin fits over every point of it. The decision
      is below.
  - **C4 — two small things, both benign, nothing changed.**
    - Faces 0.010 below the seat: SolidCraft has 3.51 mm² in 22 faces. Here, on the lite STL,
      5.217 mm² in 229 triangles sit at z 1.810. The scopes differ: this count likely also takes in
      the corner-relief floors outside the board outline. The cause is confirmed in the shell CAD:
      the board-corner relief is cut from `bb − 0.01`.
    - The west cavity wall's x: 2.50000–2.50199 on SolidCraft, 2.50002–2.50178 here (0.25 mm rows,
      away from bosses and the R16/C24 bands).
  - **D1 — not a disagreement after all.** The ledger has the pogo plate STL at 50860.32;
    SolidCraft measures 50867.96. `check_mesh`'s own pinned trimesh reads **50867.96** on the
    committed bytes at `4e88213`, `575be73` and `9a90a36`, which is every plate committed since the
    ledger was written. The ledger was stale and passed only inside the 0.5 % tolerance. It is
    re-ledgered to the measurement both instruments agree on.
  - **D2 — C24's pad to the lip: three numbers, and the reason for two of them.**
    - The sectioned gate's 0.097 is to `board_parts`' pad RECTANGLES (C24's outline is its pads'
      envelope).
    - The pads are `roundrect` (rratio 0.25, corner r 0.1475). With the rounding put back, this
      repo gets **0.1524** for pad 2 (GND) against the lite STL at z 1.70. SolidCraft has 0.1574
      against KiCad's pad solid.
    - R16's rounded pads measure 0.302 / 0.303 here, where the gate says 0.268 and SolidCraft finds
      none within 0.30.
    - So the gate is conservative wherever a pad is rounded. The 0.005 left between 0.1524 and
      0.1574 was not determined. Nothing changed; C24 is inside `LIP_CLR` 0.30 on every figure.
  - **E — not measured by SolidCraft:** the lip's stand-off from the coil copper (the export used
    carries no copper), the sheets' line work (only numbers and notes were compared), and anything
    physical: a max-material can, a routed outline against the 0.05 press, real part heights, a
    printed brace on a real board.
  - **F2 — declined:** `check_consistency.py`'s doc checks mis-report on Windows (path separators;
    `check_doc_file_refs` needs UTF-8 forced). CI and every session here are Linux. It matters only
    if the suite is run there.

  **THE SOLIDS CHANGED AGAIN AFTER EVERYTHING ABOVE (2026-11-13, later — the enclosure calls
  round; design notes, "The enclosure calls, settled").** Every shell and both braces were
  rebuilt, so the measurement this item waits on is of the solids `main` carries **after that
  round's merge run**, not of `9a90a36`. What to expect, board coordinates as above (all from this
  repo's own instruments — none of it is a SolidCraft figure yet):
  - **Six Ø2.0 bores (R1.0, true cylinders), full cavity height**, one through each supercap
    keep-out corner the finisher could not otherwise reach — at the four corner bosses and the two
    east mid-span ones, centres (4.940, 1.054), (45.624, 1.051), (5.010, 87.846), (45.811, 87.846),
    (45.430, 30.341), (45.602, 58.555), on all three shells. Every flat is where it was,
    **1.475–1.676 mm** from its screw axis; the bores' edges stand **1.754–2.030 mm** off theirs.
    Both are outside `THREAD_KEEP` 1.30. _(This read "no bore comes nearer a boss axis than
    1.475 mm" until 2026-11-14: true, and loose — 1.475 is the nearest FLAT. A bore at 1.50 would
    have passed that sentence and been a quarter of a millimetre from where the rule puts it.)_
  - **With every concave corner of the cavity filled to R1.0** (the Ø2.0 the sheet calls for):
    the brace clear at every level, and each supercap at max material (+0.60 on its two free
    edges, +0.10 on its datum edges, `fit_rules.part_envelope`) **0.150 clear** — S1 and S2 of the
    local ArtCraft review measure exactly this.
  - **The east lip seats the board on its full 1.25**: flat at the seat from x 49.65 to the board
    edge, then a single 0.10 × 45° break down to the wall at x 49.55, at every y.
  - **Rim top and recess mouth: one 0.10 × 45° facet each**, and the air frame's resting rim too.
  - **No lip beside a supercap**, by rule now: south x 3.0–23.5 and 27.0–47.5, north x 3.5–23.5 and
    27.5–47.5, the cavity wall on the recess wall.
  - **C24 to the lip 0.296** to its pad box (more to the rounded pad, by the D2 reasoning above).
  - **The max STEP:** still no edge shared by four faces (the export gate holds it); the
    rim pinch at (24.4, −34.45) is gone with the scalar lip outline, and one zero-length seam per
    break cutter stands at board (27.07, 0.78), z seat − 0.15 (`scripts/check_mesh.py` ledgers it).
  - **The max brace was rebuilt once more, on 2026-11-14 (`6fb264f`)**, when C4, C13 and C23 took
    their datasheet maximum heights (`enclosure/part_heights.py`): the pockets over C4 and C13 are
    0.05 deeper and the one over C23 0.10 deeper. **1917.48 mm³** where it was 1918.42. Its
    footprint did not move — the datum face is the same 1313.172 mm², with no difference between
    the two outlines — so every brace-to-shell figure above stands. Shells, lite brace and shim
    are as that round's merge run left them (`a4f951e`).

  **MEASURED 2026-11-14 on `4b49641` — the local ArtCraft review (SolidCraft 0.40.1, CADCraft,
  PdfCraft; `kicad-cli` 10.0.3 for the board export only).** Every measured file is identical at
  `9e335ef`. _(The box above stays open: releasing an order is DRH's call. The full report, every
  command, raw outputs and canaries are kept outside the tree, beside the earlier reviews'.)_
  Measured unless marked _inferred_; every instrument was made to fail first. The canaries:
  a mirrored brace collides; a brace shifted 0.30 east overlaps 7.86 mm³; the `9a90a36` shell reads
  its old 0.85 bearing; a planted false sheet sentence reads back false; a board lowered into the
  recess stops at the press fit; a 0.2 × 0.2 square subtracted from the shim drops its area by
  exactly 0.04.
  - **Disagree or new — DRH's to weigh:**
    - **Coil stand-off 0.8772, not 1.000** (max and lite). The nearest metal to LA/LB copper is the
      top edge of the east mid-span boss (47.93, 60.27), from board (47.180, 57.781) at z seat −
      0.10 to copper at (46.929, 56.947). The east lip is 1.0026 from the copper's x-max in plan,
      which agrees with `COIL_CLR` as a lip rule.
    - **R1.0 closest approach 0.0462, not 0.048** (max and lite): from the brace vertex at
      (49.109, 31.404) to the fillet of the east mid-span boss-to-wall junction, axis (48.550,
      32.176). **What R1.25 first touches: the four mid-span junctions**, overlapping 0.1467 mm³
      (lite) and 0.2217 (max).
    - **The ferrite channel's east ridge (x 49.10–49.50) ends in ~45° resin wedges** at y ≈ 31.40
      and ≈ 57.50, max and lite. It is 0.2015 thick 0.19 from the tip, and the last facet is 0.009
      off the channel wall. It is the channel's own wall, so it falls inside the stated exception;
      whether a tapering tip counts as "a wall under 0.10" is DRH's call. The 0.4632 neck is
      unchanged.
    - **Max STEP: 28,525 edges in SolidCraft's kernel**, against 28,526. Faces agree (9,648, 36 under
      0.001 mm²); none is shared by more than two faces. SolidCraft lists no zero-length edge;
      there is a vertex at (27.075, 0.785), z 2.65. _Inferred:_ the one-edge difference is that
      degenerate seam.
    - **Max sheet note 6, "FLOOR IS A TRUE 1.00, UNIFORM":** the cavity-side floor is one face at
      z 1.000, but the metal under it is 0.40 at the reeded valleys (1476.85 mm²) and 0.55 under the
      coin. The sheet's own rear-art block says 0.40 web.
    - **"STEPS BLEND AT R1.00"** fits 1.000 / 1.10 / 0.89 through facet vertices. The R16 step and
      both south-lip ends also carry 0.005–0.06 micro-steps.
    - **Air frame, cavity-wall resting break at y 49.0 (C24 band): 0.092 × 45°**, not 0.10.
    - **Five inside corners SolidCraft cannot fillet at R1.0:** four 61–76° wedges where a corner
      boss meets its relief, by the recess line, and one 149° corner at (27.10, 0.56). All are ≥ 1.4
      from the brace; each envelope corner is 0.79 from its bore's axis. _Inferred_ clear.
    - **L2 0.0466 holds only with the repo's card-underside seating.** With the brace mated to
      KiCad's laminate (KiCad 10.0.3 puts parts 0.085 off it) it is 0.1658.
    - **Shim datum coverage reads 0.4–2.6 points off** (SC1 E 92.4 against 95.0). The plate's
      facing edges are 0.0999–0.1092 from KiCad's can bodies and slightly non-parallel.
  - **Agree:**
    - Volumes: all six STEPs to the last digit.
    - The hand: L2, and the four mirrored figures (487.5719/28, 52.8334/33, 301.5107/28,
      52.9328/34).
    - Supercap to boss: no overlap on any shell; caps 0.7500 off metal. With every pair checked on
      the full max shell, the only overlaps are the PCB press fit (5.9307 mm³) and L2.
    - No brace-to-shell overlap; no seat-level downward faces; old rim pinch gone; the 0.0068 wall
      gone.
    - Six bores R1.000 at the listed centres; flats 1.475–1.676 and bore edges 1.7536–2.0296 from
      the screw axes.
    - Air frame: resting break and the eight 45° feet.
    - Medallion and pogo plate read correctly.
    - S2: every max-material envelope 0.1500 clear, sharp and at R1.0, on all three shells.
    - Lips: east 1.25 flat from 49.6497 with one 0.10 × 45° break at every y; west
      2.50 / 2.3214 / 2.2514; south and north 2.00 with no lip beside a can; a break on every lip
      edge.
    - Rim, mouth and frame facets; recess 50.70 × 88.80.
    - C24 0.2962 in plan.
    - Shim: 9 contours, 969.2317 mm², one piece, no pad or body overlap, east edge 49.50.
    - Brace sheets: 12.400 channel, 14.0666 to the nearest tab, both note-8 lists exact. Max sheet:
      island 0.5494, 19 ribs at 1.399.
    - Masses: 23.434 / 17.377 / 7.820 / 2.205 / 1.306 g.
  - **Not measured:**
    - The max brace swept into the full max shell: SolidCraft refuses it (tessellation budget). The
      section proxy clears.
    - The full-board copper export with zones: `kicad-cli` 10.0.3 segfaults.
    - The R1.0 sweeps stop on a mesh-tolerance contact (0.105). The exact seated pose shows no
      overlap, so the sweep is not decisive.

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

- [ ] **[ENCLOSURE, cosmetic] The shell STL's one tessellation pinch** _(2026-08-01, found and
  ledgered by `scripts/check_mesh.py` on its first measurement.)_ One zero-length boundary edge
  at a single rim point (24.4, −34.45, 2.7) plus 1 zero-area facet (3 until the 2026-11-12
  medallion fix) — a cadquery boolean seam
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
- **Enclosure verdicts of 2026-11-13 — do not re-derive** (the reasoning and both numbers for each
  are in the design-notes addendum "The enclosure calls, settled (2026-11-13)"):
  - **The board is a 0.05 mm PRESS fit in its recess, by design (DRH).** Against a routed outline
    of ±0.1–0.2 an oversize board has its FR4 edge sanded at assembly (`enclosure/README.md` §8);
    the titanium is never opened up. `fit_rules.EDGE_FIT` is its one home. Re-open only on a
    measured batch of boards where sanding stops being the exception.
  - **The brace backs none of the four solar-cell tabs (DRH).** The air frame has no brace, so the
    card must take unbacked tabs anyway. Re-open only if the first-article press test (BENCH, above)
    cracks a joint.
  - **The brace keeps its four sub-`SLA_WALL` features (DRH):** the ferrite channel's 0.40 east
    ridge and 0.265–0.52 west walls, and the 0.46 TP2/TP3 neck. The print spec names a printer
    class that holds 0.25 mm walls (`enclosure/brace/README.md`). Re-open only if no such service
    will print it.
  - **There is no lip beside a supercap, and there cannot be.** Every cap's free edge faces the
    board edge, so a max-material can stands 0.40 mm off it; `lip_bands()` says none there by rule
    (`fit_rules.part_envelope`, `LIP_MIN`). Not a preference — a can's tolerance owns that strip.
  - **L2's 0.02 mm "proud" is KiCad's model, not the part.** The physical solder standoff is
    already inside `fit_rules.AIR`'s RSS by name; the 0.040 seat is KiCad's export convention, and
    the fitted DFE252010F (1.0 max) clears by 0.18. No separate seating constant.
- **TWO LAYERS, 0.6 mm — locked 2026-08-10 after an adversarial re-examination. Cost is not the
  reason, and "a dedicated ground plane cuts noise" does not survive contact with this board.**
  The case for 4 layers is the standard one and it is sound in general. It fails here on three
  board-specific facts, two of which a general grounding principle cannot see:
  - **An inner plane sits IN THE LIGHT PATH.** `optical_window` is a copper keepout on **both**
    F.Cu and B.Cu — **144.9 mm², 3.2 % of the board** — because D2–D5 are on B.Cu and backlight
    the front monogram *through the bare FR4*. On 4 layers In1/In2 are physically between the LEDs
    and the monogram: copper there means no glow. So the plane cannot be both dedicated and
    continuous — it must carry the same **21.6 mm-wide slot across the middle of the card**, which
    forces every north–south return in that band to detour around it. That is the exact
    return-path discontinuity a ground plane exists to remove.
  - **It fights the antenna, and read range is an OPEN first-article gate.** The coil is on B.Cu
    and the board already spends ~**7 % of each face** holding copper off it (`NFC_COIL_KEEPOUT`
    317 mm², `NFC_COIL_POUR_KEEPOUT` 330 mm²). At 0.6 mm total, inner layers sit **0.1–0.2 mm**
    from the coil instead of 0.6 — worse coupling per unit area, on all four faces instead of two.
    Four layers does nothing for the energy budget and actively threatens the coil; those are the
    two gates the first article exists to close.
  - **There is no noise for it to fix — and it would UNDERMINE the isolation that is already
    there.** The fast content of this board is: an AVR at **1.25 MHz** on the internal oscillator
    (no crystal), I²C at ~**100 kHz**, LED PWM at ~16 mA, a megohm DC sense divider — and exactly
    one real source, the AEM10300's ≥10 MHz hash. That source is already handled by a LOCAL solid
    island (`GND_B_DCDC_SOLID`) plus the LDO's **moated** island with a single-point tie and a
    ferrite, whose whole purpose is to deny the hash a shared-copper path back in. A continuous
    inner plane would hand it a low-impedance path to everywhere. For a board with one fast
    circuit, local islands are the better topology, and they are built.

  **Manufacturing, secondarily:** 0.6 mm is locked, so 4 layers means ~0.1 mm dielectrics — a
  specialty tier, not a standard one, at all three fabs — and the triple-fab envelope
  (PCBWay ∩ OSH Park ∩ JLC, in `PCB/solar-glow-drh-v4_0.kicad_dru`) was derived against **2-layer**
  capability, so its drill/annular/spacing floors would need re-deriving. Selective hard gold
  narrows the vendor set again. This is re-opening the manufacturing envelope, not paying more for
  the same board. **Cost is the WEAKEST argument against it** — bare PCB is a small fraction of a
  build carrying hard gold, titanium and assembly; if 4 layers were technically right it would be
  worth buying.

  **Reopen only on a measurement, and all three are available from the first article:** an EMC
  pre-compliance failure traceable to ground (that item's measured half is still open); scope
  evidence of AEM switching hash on `VS` or `STO_SNS`; or the design acquiring a genuinely fast
  bus. A 10-card run is an INSTRUMENT — its job is to say what is actually wrong. Buying layers
  now is insurance against an unobserved failure, bought by degrading a function already known to
  be marginal.
- Enclosure STEP stays **analytic-sharp**: r1.0 internal corners are a DRAWING
  spec; do **not** enable `tool_relief` (produces a faceted STEP the fab rejects).
- East cavity lip pinched to 1.0 mm over y10–72 (NFC detune) — do not widen.
  _(2026-11-12: the NUMBER here is stale, the rule is not. The lip has been a single **1.25 mm**
  band over the whole east edge since `fit_rules.COIL_CLR` went to 1.00 — the wall is at x 49.550,
  measured on the STEP — and what holds it is the standoff from coil copper, not the 1.0. The old
  1.0 survived in one more place, `fit_rules._CAV`, and that is what left both braces 0.20 mm wider
  than their cavities. Intent unchanged: do not bring grounded metal nearer the coil.)_
- NFC tuning at bring-up needs the brace **removable** — don't defeat it.
- Supercap footprints are a **hybrid**: SC1/SC3 = SS17 land (3-153-440, 39 mm), SC2/SC4 = WS17
  land (3-153-438, 28.5 mm); flat under-body pads, asymmetric widths = polarity key. The old REV-J diagonal-pad land is WRONG -- never reuse.
- Ti-6Al-4V (Grade 5); grounded M2 bosses tie the body to GND.
- **`U5` pin 7 (`VOUT`) stays UNCONNECTED — declined 2026-08-09 after an independent datasheet
  check, do not re-open without a bench number.** NFC energy harvesting was carried as a respin
  item; the arithmetic in it was right and the conclusion was still wrong, because the cost was
  never priced. **Harvesting current reduces read range** — NT3H2211 datasheet §8.6, verbatim:
  *"increasing the output current on Vout decreases the NFC communication range."* Read range is
  this card's scarcest resource: the coil sits behind a ferrite sheet inside a titanium shell, and
  the offline vCard read on a FLAT card (the entry above) is the one NFC function that must work.
  Trading it for a novelty flash, to unblock a feature (HOTP) that is itself parked, is backwards.
  The three engineering facts that finished the argument, all from the datasheet rather than from
  the item's summary of it:
  - **The VOUT capacitor is mandatory AND capped**: "typically 150 nF up to **220 nF maximum**
    … between VOUT and GND close to the terminals." So "give VOUT its own small reservoir" is not
    permitted as written — 220 nF at 2 V is 0.44 µJ, ~4000× short of one 1.8 mJ blink. A real
    reservoir has to sit behind isolation.
  - **A tap cannot even pay for the glow it triggers.** One glow costs **~0.4 J**
    (`firmware/sense.c:228`), so a full 15.14 J tank is only **38 glows**. A 1 s tap at the
    features-page 15 mW collects 15 mJ = **3.75 % of one glow**; at §8.6's realistic 10 mW it is
    2.5 %. That is **~27 taps to fund a single glow** (40 at the honest figure) — and the tap IS
    the actuator, so every harvest event triggers the spend that dwarfs it. Harvesting here is net
    negative by roughly thirtyfold. (The older "1000 taps to fill the tank" framing was true and
    too kind: it compared against the reservoir instead of against what the card actually does.)
  - **The harvested rail is at or below the LED's forward voltage.** VOUT is typically **2.0 V at
    5 mA** with a phone (§8.6; the "up to 15 mW" figure is the front-page feature bullet, and the
    electrical table's 3.3 V is at **1 mA** into a Class 5 antenna at 14 A/m). `LA P47F` VF is
    min 1.95 / typ 2.05 / max 2.55 V, and the LED path wants 16 mA. So "~8 blinks" needs a BOOST,
    not a reservoir — there is no headroom for a ballast resistor, and VOUT sources a third of the
    current. Buffering 1.8 mJ across those rails is ~1 mF behind a diode, on a frozen board.
  - **It is not one route.** U5's VCC is on `VNFC`, switched from VS by U6 under `NFC_EN`, and the
    datasheet requires VCC tied to VOUT if the tag is also to power the I²C bus — i.e. the flat-card
    case ties VOUT to a node a load switch also drives. That needs ORing/isolation, not a wire.

  Leaving the pin open is sanctioned by omission: the datasheet states no requirement for an unused
  VOUT (searched for "unused" / "left open" / "floating" — nothing), the 150–220 nF is a precaution
  for *operating in harvesting mode*, and ERC/DRC are clean on the unconnected net. **Reopen only
  on a measured read-range figure showing margin to spare** — never on the 15 mW headline.

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
