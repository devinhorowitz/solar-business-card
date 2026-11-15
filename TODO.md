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

- [ ] **[DECISION — DRH] The brace against PCBWay, and against five US services: its fit, its thin walls and its layers are finer than what PCBWay states, and nearly inside what Protolabs does**
  _(2026-11-15. DRH: "it's going to be pcbway. Check against their capabilities before we make
  decisions on sizing constraints." Checked; NOTHING is resized yet.)_
  - **What PCBWay states for SLA** (their pages, read 2026-11-15; where two disagree both are
    given):
    - **Accuracy:** "L<100mm, ±0.2mm. L>100mm, ±0.2%*L" (SLA page and 3D-printing page, the
      same table). Their medical-device page gives UTR 8360, UTR 8220 and Somos Ledo "±0.1 per
      100mm"; the SLA page's prose says ±0.004 in per inch. "Improved tolerances may be
      possible with a manual quote review, after successful completion of a prototype build
      ... case-by-case."
    - **Minimum wall:** 0.8 mm (SLA page). The help centre's "Wall thickness issue" has it
      by the wall's size — **0.5 mm at 5 × 5 mm, 0.8 at 10 × 10, 1.0 at 50 × 50, 1.2 at
      100 × 100, 1.5 at 200 × 200** — for SLA and DLP alike. Under it the order is paused,
      they email pictures of the thin places, and you revise or accept the risk; the order
      form has a "Wall thickness risk taken" box that skips the pause.
    - **Layers:** 0.1 mm (UFSH100's page; the medical page's table for the other resins).
    - **Thin flat parts:** "large in size and thin in thickness, distortion can become a
      problem" — the same pause and choice. No number.
    - **White resins:** Standard white UTR 8360 (matte white; 53.7 MPa, 5.1 % elongation,
      Shore D 84; its own page lists "general strength and toughness" as the drawback),
      UFSH100 (white; 65–77 MPa, 6.2–10 %), Somos Ledo (white; 52.3 MPa, 11 %; "high
      toughness and high strength"). Their tough UTR 8220 is yellow-green. Opacity is not
      stated for any.
    - **DLP** is ±0.1 mm under 100 mm, but the only DLP materials listed are a flexible one
      and a dental-model one. Not an option for a rigid white part.
    - **Not published at all:** a minimum feature, slot or gap; which way up a part is
      printed; where the supports go.
  - **What the brace asks** (measured on the solids of `56680ce`: each brace sectioned at
    every level, and the resin's thickness read under every pocket on a 0.1 mm grid):
    - **Fit:** 0.05 mm a side to every face of the shell. Four dimensions seat it, each with
      0.10 mm in all to give: 47.20 wall to wall, 84.80 between the forks' seats, 26.90
      between the two east bosses, 3.60 across a fork's slot. **A print 0.2 over is twice
      that; 0.1 over is all of it.** _(This read "four times ... twice" at first: ±0.2 set
      against the 0.05 at ONE end. A dimension seats if the worst oversize is no more than
      the allowance at both ends together.)_ Two of the four are flat walls and can be sanded. The fork and
      the boss nests cannot.
    - **Walls under 0.5 mm:** four, on both braces, all of them the ferrite channel's own —
      0.33 tall on a 1.47 (max) or 0.89 (lite) base: the ridge east of it, 0.40 wide for
      26.0 mm, and three stretches on its west side, 0.26–0.50 wide and 1.9–2.95 long. These
      are the walls `PRINT_WALL` 0.25 was accepted for on 2026-11-13, **on the strength of a
      Formlabs figure**; they are under the smallest wall in PCBWay's table.
    - **Walls 0.6–0.8 mm:** a dozen or so between pockets, none over 3.2 mm long or 0.78
      tall. Inside the table's 0.5 at 5 × 5.
    - **Webs under pockets, max brace:** thinnest 0.58. Two are under the table: 0.58 over
      12.1 × 11.6 mm near (31, 54) and 0.68 over 9.3 × 7.4 near (28, 37), against 0.8 at
      10 × 10. The rest are small enough to pass.
    - **Webs, lite brace:** thinnest 0.45 — thirteen of them, the largest 4.5 × 4.1 mm,
      against 0.5 at 5 × 5. Its channel floor is 0.89 over 29.4 × 13.5 mm (0.8 at 10 × 10,
      1.0 at 50 × 50) and the whole plate 1.22 over 88.7 × 47.2 (1.2 at 100 × 100).
      **`SLA_WEB` at 0.50 there has a price:** the span limit falls from 0.60 to 0.50, the
      eighteen 0.55 mm passives become blockers (24 → 42), and the footprint goes 1103.8 →
      988.3 mm² — 24.3 % of the floor, under its ledgered 25 %.
    - **Heights finer than a 0.1 mm layer:** the ferrite channel's 0.33 (a 0.38 sheet stands
      0.05 proud by design, 0.10 allowed: at 0.30 it stands 0.08 proud, at 0.40 it is 0.02
      under and nothing clamps it); the LEDs' 0.16 of air; the lite brace's own 1.22.
    - **Height:** the sheet says print 0.1 proud and sand the bottom. The committed STL is
      the sanded size, so there is no file to send that IS proud — and ±0.2 on thickness is
      twice the 0.1.
  - **US services, read the same day** (DRH, on the comparison above: "Let's look for an
    American printer instead that fits our requirements better"). Each one's own published
    figures, with one exception: Stratasys Direct's pages refused the connection, and its row
    is what a search quoted of them. Four of the five list Accura Xtreme White 200 (Stratasys
    Direct's whites were not read), an ABS-like white: 55 ± 10 MPa, 9 ± 5 % elongation,
    heat-deflection 47 °C at 0.46 MPa — "the lowest of all SLA materials", in Protolabs'
    words; opacity is stated by none.

    | service | X/Y tolerance as stated | on 3.60 / 26.90 / 47.20 / 84.80 | fit a side that covers it | minimum wall or feature | layer |
    |---|---|---|---|---|---|
    | **Protolabs, industrial SLA** (its own plants — Raleigh area, NC, by the trade press; its page does not say) | ±0.05 mm for the first inch plus 0.1 % of length | 0.054 / 0.077 / 0.097 / 0.135 | **0.067** — three of the four are inside 0.05 | wall 0.152 mm in ABS-Like White at high resolution (0.305 at normal); feature 0.127 in X–Y, 0.406 in Z | 0.0508 high, 0.1016 normal |
    | Stratasys Direct, HD SL | ±0.005 in or ±0.001 in/in, the greater | 0.127 on all four | 0.064 — none inside 0.05 | feature 0.254, smaller case by case | not read (their pages refused the connection) |
    | Prototek (Contoocook, NH) | ±0.005 in first inch + 0.0015 in/in | 0.127 / 0.129 / 0.160 / 0.216 | 0.108 | feature 0.152 "depends on geometry"; its guide gives walls 0.51 supported, 1.02 unsupported | 0.0508 / 0.1016 |
    | Xometry (partner network; where a part is made is not stated) | ±0.005 in first inch + 0.002 in/in | 0.127 / 0.130 / 0.171 / 0.246 | 0.123 | high res: under 0.51 at risk, under 0.254 will not build | 0.05 / 0.1 |
    | Quickparts | ±0.005 in first inch + 0.002 in/in | as Xometry | 0.123 | high res: wall 0.381, feature 0.254 | 0.051 / 0.102 |
    | PCBWay, for comparison | ±0.2 mm under 100 mm | 0.200 on all four | 0.100 | 0.5 at 5 × 5 mm | 0.1 |

    Ruled out by their own minimum walls: PolyJet white (Protolabs' Digital White, 0.762 mm),
    Carbon DLS (about 1 mm), and Formlabs-machine lines (Protolabs' own: wall 0.5 mm, ±0.3 %
    with a ±0.3 mm floor — and fulfilled through its network, not its US plant).
    - **Closest: Protolabs, industrial SLA, high resolution, ABS-Like White.** Against the
      brace as built: no wall or web is under its minimum (0.26 the thinnest wall, 0.45 the
      thinnest web); layers half PCBWay's; three of the four seating dimensions inside the
      0.05 fit, and the fourth — 84.80 between the forks — over by 0.035 mm in all, which
      0.07 a side covers.
    - **Open at Protolabs:** the channel's walls are 0.33 tall, under its 0.406 minimum
      feature in Z; its Z tolerance is ±0.127 mm for the first inch, on a channel whose depth
      has 0.10 to play with; the resin's 47 °C; and no price has been read — that needs the
      file put into their quoting tool, which is DRH's to do.
  - **To decide (each is DRH's):**
    0. **The printer.** PCBWay, as first said, or Protolabs (above). The other sizes follow
       from it.
    1. **The fit.** Keep 0.05 and let a first print say what PCBWay really holds; or open it
       to 0.10 a side, which covers their stated ±0.2 at its worst; or ask them for a
       tolerance on the four dimensions (their "manual quote review").
    2. **The four channel walls.** Tick "wall thickness risk taken" (they are low ribs on a
       thick base, not free-standing walls); or widen what can be widened; or give the east
       ridge up and let the channel run to the brace's edge.
    3. **The webs.** Accept the risk; or, on the max brace, make the two large ones
       through-pockets; on the lite brace thickening the thirteen costs a tenth of the
       footprint (above).
    4. **The layer.** Put the channel on a layer (0.30) or leave 0.33 to their slicer.
    5. **The resin.** Somos Ledo is the white one sold as tough; UTR 8360 is the cheap one
       and says of itself that it is not.
    6. **The file.** Whether the generator should also write a print file with stock on the
       bottom for sanding.
  - **What would settle most of it at once:** one message to PCBWay with the STL and the four
    dimensions — what will you hold, will your wall analysis pass it, which resin is opaque
    white — and one test print.
  - **Left as it is until this is decided:** `PRINT_WALL`'s comment in `fit_rules` and the
    brace sheet's note 4 ("correct the printer's XY scale") still speak of a printer one sets
    up oneself. Both are rewritten with whichever sizes are chosen.

- [ ] **[BENCH — first brace print] Measure the print over its two forks before trusting the fit, and set the printer's XY scale from it**
  _(2026-11-15, opened when the brace nested.)_ The brace's long arm now runs on either side of
  each short-edge tab, and the outline stands 0.05 mm off every face of the shell it reaches
  (`fit_rules.WALL_FIT`) — the curves round a tab or a boss included, which cannot be sanded to
  fit the way a flat edge can. The two forks' seats are **84.80 mm apart** (y 2.05 and 86.85),
  so the whole allowance along the brace's length is 0.10 mm. The printer is PCBWay (DRH,
  2026-11-15), whose stated SLA accuracy is ±0.2 mm on a length under 100 mm: **a print inside
  that can be 0.2 mm long, and will not seat** (the item above has the whole comparison; this
  one read "Formlabs ... ±0.3 %" for an hour, from a print spec that named the wrong printer).
  So, on the first print, before any filing: **measure seat to seat between the two
  forks (84.80 nominal; 88.70 over the prongs' noses), across the ferrite block between the two
  east bosses (26.90 nominal, y 31.00–57.90, on the 1 mm of flat each side has at x 47.5–48.5),
  and the width from the west face to the east face (47.20 nominal)**. If the long figure is
  out by more than the short ones, in proportion, it is the printer's scale: the MODEL is rescaled
  to answer it (PCBWay prints the file as sent), and reprinted. If a
  print at the right scale still binds on a curve, say so — the fix is then a looser fit
  (`brace_cavity()` shrinks the void by one number, everywhere), which is DRH's call, not a
  file. Tick this when a print has dropped in without being touched.

- [ ] **[BENCH — before the titanium is ordered] Put a caliper on a supercap's edge: the floor fillets stand under it, and the corner-boss roots in its corner**
  _(2026-11-15, opened with the floor fillets.)_ The south and north floor fillets of the max
  and lite shells stand under the outer edge of all four supercaps. A can at nominal clears
  them. A can at max material does so **only if it is thinner than its stated 1.70 mm for the
  first 0.33 mm in from its outline** (max shell; 0.09 on lite) — `fit_rules.floor_cap_margin_needed()`,
  held against `FLOOR_CAP_MARGIN` 0.50, which is an ASSUMPTION about a foil pouch's sealed
  margin that the SCHURTER datasheet does not dimension (DRH's photograph of a WS17F shows the
  margin; nothing here has measured one). **Measure, on an SS17 and a WS17, along a short
  edge: thickness at the edge, and 0.1, 0.2 and 0.35 mm in from it.** On the max shell it
  passes if the can is no thicker than **1.51 mm at its edge, 1.58 at 0.1 mm in, 1.64 at
  0.2**, and reaches its full 1.70 no nearer than 0.33 mm in; the governing figures are
  printed by `scripts/assembly_drc.py` [K] on every run. Then set `FLOOR_CAP_MARGIN` to what
  was measured and delete "PROVISIONAL" where it is said. If the measurement is under the
  need, `floor_runs()` refuses to build — by design, a run is refused, not shortened — and
  the four short-wall runs have to come off; the four long-wall runs stand under nothing and
  stay.
  **And look at one corner of the can in plan** _(added 2026-11-15, with the plain corners at
  the corner bosses)_. Each corner boss's flat now meets the short-edge wall through a plain
  R1.00, where a Ø2.0 bore used to stand clear of the can. That corner stands **0.070 mm into
  the very corner of a square-cornered SC1 at max material** (0.005 mm² in plan; 0.031 into
  SC4, 0.015 into SC3, clear of SC2; a can at nominal is 0.75–0.94 mm away). It clears if the
  can's BODY stays **0.05 mm** inside its max-material outline at that corner
  (`fit_rules.boss_root_cap_need()`), against the same 0.50 assumed above — so the question is
  only whether the pouch's corner is the sealed margin, or rounded, as it looks in the
  photograph. If a can's body really is square and full-size to its corner, the bore has to
  come back (`boss_roots()` refuses to build past the margin; the dogbone is in git history,
  `boss_cuts` at a corner boss before 2026-11-15). `scripts/assembly_drc.py` [H] prints the
  measured figure on every run.

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
  - **The max shell STEP imports with no edge repair.** Expect **30,914 edges, none shared by more
    than two faces; 10,453 faces, 35 of them under 0.001 mm²**; no upward faces at z +0.02. _(Counts
    by OCC on a local build with CI's pins, 2026-11-14, of the shell with each boss joined to the
    wall and each back annulus to the frame — the last two blocks of this item. They were
    28,512 / 9,647 / 35 with the cavity's junctions alone; 28,544 / 9,654 / 36 with the coil relief alone,
    the shell at `5a36638`; 28,526 / 9,648 / 36 on the STEP built at `a4f951e`, which is what the
    2026-11-14 ArtCraft record below measured; and 28,403 / 9,626 / 82 at `9a90a36`, which is what
    the 2026-11-13 MEASURED block reads.)_
  - **Each boss runs into the wall through a blend, and no corner boss stands beside a slot** (max /
    lite / air; since 2026-11-14, the last block of this item). Expect twelve concave cylinders
    where a boss meets the lip's wall — **ten of R2.000 and two of R1.000**, the two on the
    ferrite's side of the bosses at (47.93, 28.63) and (47.93, 60.27) — and solid metal from each
    corner boss to the recess wall, with that boss's Ø2.0 bore running out to the wall. The axes
    are in the last block.
  - **The open frame still has its resting-face edge-break**, including a 45° foot on each boss flat.
  - **No brace resin wall under 0.10 mm**, max and lite, and none under `SLA_WALL` 0.60 except the
    ferrite channel's own walls (x 36.2–36.7 and 49.10, top 0.33 mm only) — **and none of those
    under 0.25** (`fit_rules.PRINT_WALL`): the ridge east of the channel now stops square at y 31.67
    and y 57.23, where it is 0.25 wide, instead of tapering to a point at 31.40 and 57.50. The
    0.0068 mm wall at (4.411, 49.653) is the canary: it must be gone.
  - **The files are the parts, not their mirror images** (written right-handed since 2026-11-13).
    In a shell's or a brace's file a board point (x, y) is at **(x − 25.4, 44.45 − y)**: y runs UP
    now, so every board coordinate in this list reads that way in SolidCraft. Expect:
    - against KiCad's STEP export of the populated board, placed by a translation alone and NOT
      mirrored: the **max brace overlaps one part, L2, by 0.047 mm³** (KiCad's generic 1008 body,
      1.20 tall where the part fitted is 1.00 — the item on L2 below) and the **lite brace
      nothing**. Mirrored, they must collide: 52.8 mm³ over 33 parts and 487.6 over 28 (max),
      52.9 over 34 and 301.5 over 28 (lite). Cutting the two west corners back (the last
      block of this item) did not move them: the gate printed 52.833 over 33, 487.572 over 28,
      52.933 over 34 and 301.511 over 28 on the braces at `c448408`, as it had at `5a36638`
      — no part stands at either corner. The 53.1 / 493.9 SolidCraft first
      reported were the braces at `d060215`, before the level opening;
    - **the medallion reads correctly from behind** — DRH, No 001, and SOLAR · NFC · TITANIUM ·
      ATL GA · MMXXVI clockwise round the ring;
    - **the pogo plate takes the panel face-UP**: its two dowel bores under TH1 and TH2 (file
      (−4.9, −20.0) and (55.7, −85.0); the plate is un-centred, a board point (x, y) is at
      (x, −y)), and its title and net labels reading correctly from above;
    - the max shell STEP's counts are what they were — the reflection changes no face, edge or
      volume (**5312.813 mm³** by OCC with each boss joined to the wall and each back annulus to
      the frame; 5307.193 with the cavity's junctions alone; 5289.748 at `5a36638`,
      with the coil relief alone; 5289.905 at `a4f951e`; 5293.129 was `9a90a36`'s).
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
  - **C4 — two small things, both benign, nothing changed.** _(The first of them WAS changed, on
    2026-11-15: DRH saw it in a render. "THE SEAT IS ONE PLANE" below.)_
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

  **THREE OF THOSE FINDINGS ACTED ON, 2026-11-14 (DRH's call) — SO THE SOLIDS CHANGED ONCE MORE.**
  All three shells and both braces are rebuilt by this change's merge run, and the measurement this
  item waits on is of THOSE solids. Everything in the two "what to expect" lists above stands except
  where a bullet here says otherwise. Board coordinates; this repo's instruments, on a local build
  with CI's pins — none of it is a SolidCraft figure yet.
  - **The two east mid-span bosses stand 1.00 mm from coil copper** (they were 0.874 and 0.966;
    ArtCraft's 0.8772 is the first). `COIL_CLR` was written for the east lip and the lip was the
    only feature held to it. Each boss now carries one hollow, **R1.15, a true cylinder about the
    coil's own corner vertex** — axis (46.9, 56.8) in the boss at (47.93, 60.27), and (46.9, 32.2)
    in the boss at (47.93, 28.63) — full cavity height, with a 45° foot on the air frame. R1.15 is
    the clearance plus half the 0.30 track, so the Ø2.0 finisher cuts it; the boss at y 60.27 also
    takes a sliver of flat at y 57.95 over x 46.76–46.90, the band beside the coil's straight run.
    They take 0.076 and 0.009 mm² off the two bosses, 0.13 and 0.03 mm deep, 2.47 and 2.57 mm from
    the screw axes; the six bores and every flat are where they were. Nothing else on the shell moved: the
    lip, the other six bosses and the void are unchanged, and so is the brace's outline.
    - Volumes by OCC on the STEPs: **5289.748 / 3922.362 / 978.605 mm³** (max / lite / air; they
      were 5289.905 / 3922.466 / 978.708). STL: 5289.51 / 3922.21 / 978.48.
    - The max STEP: **28,544 edges, 9,654 faces**, 36 under 0.001 mm², none shared by more than two
      faces. Lite 1,055 / 390 / 36; air 1,310 / 472 / 38.
    - `scripts/assembly_drc.py` **[I]** now sections every shell and measures its metal against
      the coil's copper read off the board. On the solids as committed before this it is red at
      both bosses (0.870 and 0.966 through the mesh); on the rebuilt ones the bosses read 0.998 /
      0.999 and the lip 1.000. Its canary is a coil 0.25 mm fatter, which must read too close at
      the lip and at each relieved boss separately.
  - **The brace's ridge east of the ferrite channel ends square** (max and lite). The two tips
    ArtCraft found — the ridge following the brace's edge round each boss fillet and tapering to
    nothing at y 31.40 and 57.50 — are cut off where the ridge would be narrower than **0.25 mm**,
    the wall the print spec's printer class holds (`fit_rules.PRINT_WALL`, new: an exception from
    `SLA_WALL` 0.60 is not an exception from that). The ridge now stands **y 31.67–57.23, 0.25 wide
    at each end and 0.40 between**, 0.33 tall. The channel takes the tips with it: one tool, one
    floor. Volumes **1917.453 / 1135.782 mm³** by OCC (were 1917.478 / 1135.807); max 1,035 edges
    / 353 faces, lite 1,143 / 379. `assembly_drc` **[C]** measures the ridge straight across on the
    emitted brace, every 0.02 mm of its length: red on the braces as committed before this
    (thinnest 0.003 mm), 0.257–0.400 on the rebuilt ones.
  - **Max sheet, note 6** no longer says "FLOOR IS A TRUE 1.00, UNIFORM". It says the cavity floor
    is one flat face at 1.00 and what the metal is under it — 1.00 uncut, **0.40 under the reeded
    valleys, 0.55 under the medallion's coin floor** — from `fit_rules.FIN_VALLEY` and
    `medallion.COIN_D`, the constants that make the cuts. Notes 4 and 7 and the caption in Section
    A-A said the same thing in other words and are corrected with it; that caption was also set
    across the wall's hatching, unreadable on every committed sheet, and now sits in the cavity.
    The sheet's boss callout gains the coil relief: how many, the radius, the measured stand-off.
    The lite sheet's floor IS a uniform 0.60 and still says so.
  - **Not acted on, and why:** the other seven ArtCraft items above are instrument differences or
    informational (a one-edge kernel difference, blend radii within a facet, a 0.092 break, the
    five corners SolidCraft cannot fillet, L2's seating, the shim's coverage against KiCad's
    bodies, the 0.0462 closest approach). None changes a part.

  **EACH BOSS JOINED TO THE WALL, 2026-11-14 (DRH, from a render of the bosses) — SO THE SOLIDS
  CHANGED AGAIN.** All three shells and both braces are rebuilt by this change's merge run, and the
  measurement this item waits on is of THOSE solids; an ArtCraft run started against `5a36638`
  measures the shells as they were before it. Everything in the lists above stands except where a
  bullet here says otherwise. Board coordinates; this repo's instruments, on a local build with
  CI's pins — none of it is a SolidCraft figure yet.
  - **Twelve blends.** Where a boss's circle crosses the lip's cavity wall the STEP kept a sharp
    inside corner — 51.5° on the east wall, 81.8° on the west — and left it to the finisher's
    radius. Each is now a modelled concave blend: a true cylinder through the full cavity height,
    carrying the 0.10×45° break of the lip and the boss it joins, and on the air frame the same
    at the resting face. **Ten are R2.00**, axes (4.498, 7.170), (4.498, 24.330), (4.498, 32.930),
    (4.498, 55.970), (4.498, 64.570) and (4.498, 81.730) on the west, (47.552, 7.452),
    (47.552, 24.048), (47.552, 64.852) and (47.552, 81.448) on the east; they meet the wall
    1.73 mm (west) and 2.55 mm (east) beyond the old corner. **Two are R1.00**, axes
    (48.552, 32.174) and (48.552, 56.726): the blends on the ferrite's side of the bosses at
    (47.93, 28.63) and (47.93, 60.27) — the next bullet. Each circle is set 0.002 mm past tangent
    into the lip and the boss, so that a kernel is handed a crossing and not a tangency; the radii
    are exact.
  - **The ferrite sheet is why two are R1.00, and it is a finding of its own.** At R2.00 those two
    blends stood INSIDE the sheet's east corners at (48.9, 31.5) and (48.9, 57.5): 0.035 and
    0.075 mm² of titanium where the ferrite goes. The first full build did exactly that with every
    gate green, because nothing had ever held the sheet against the shell. So a blend that would
    come within `FER_CLR` (0.20) of the sheet is cut at `TOOL_R` instead — the radius the Ø2.0
    leaves in that corner whatever the model says, so the part does not move there, and neither do
    the brace's two east corners or the ridge east of the ferrite channel. `scripts/assembly_drc.py`
    **[F]** and **[H]** now carry the sheet as a body. What they print is new information about
    the shells as they have always been: **the sheet's corners stand 0.24 and 0.15 mm from the
    as-milled titanium**, at the boss at y 28.63 and the one at y 60.27. No rule chose that
    clearance. **The two stay at R1.00 (DRH, 2026-11-14)**: the alternative was R2.00 there as
    well, with about 1 mm snipped off the sheet's two east corners, and it was turned down.
    **Still DRH's call:** whether 0.15 mm is enough for a hand-laid sheet.
  - **Four webs.** Beside each corner boss, on its short-edge side, the STEP had a slot of void
    between the boss and the recess wall — 0.17 mm wide at its narrowest, closed at one end and
    running out into the boss's own Ø2.0 bore. No cutter enters it. It is metal now (0.37, 0.42,
    0.26 and 0.32 mm² in plan): boss, web and wall are one piece, and the bore is an ordinary
    R1.0 relief from the boss's flat out to the wall. **The bore stays**: without it the
    finisher's own radius would leave metal 0.04–0.05 mm inside a max-material supercap's corner.
    The four corner bores are parked exactly against the recess wall now — axes (4.948, 1.048),
    (45.620, 1.048), (5.017, 87.852) and (45.803, 87.852), 0.005–0.010 mm from where a half-degree
    search had left them 0.001–0.004 short of it. They stand 1.76–1.94 mm from the screw axes
    (were 1.75–1.94). The two mid-span bores, every flat and both coil hollows are where they
    were.
  - **The numbers.**
    - Volumes by OCC on the STEPs: **5307.193 / 3934.199 / 990.335 mm³** (max / lite / air; they
      were 5289.748 / 3922.362 / 978.605). STL: 5307.10 / 3934.15 / 990.31. The blends add
      8.271 mm² in plan and the webs 1.370.
    - The max STEP: **28,512 edges, 9,647 faces**, 35 under 0.001 mm², none shared by more than
      two faces. Lite 1,023 / 383 / 35; air 1,244 / 460 / 36. Fewer than before on every shell:
      the webs bury more facets than the blends add.
    - The braces lose the two WEST corners beside their band to the R2.00 blends there
      (footprint 1313.17 → 1312.70 mm²): **1916.609 / 1135.278 mm³** by OCC (were 1917.453 /
      1135.782), max 1,038 edges / 354 faces, lite 1,146 / 380, closest approach to the shell
      0.048. The ridge east of the ferrite channel still stands y 31.67–57.23.
    - The reflow shim's DXF (`enclosure/shim/`) was rebuilt by this change too, and moved: at most
      0.0023 mm, at its two east corners, net area 969.232 → 969.230 mm². _(Added 2026-11-14,
      later: the block went out without saying so.)_
    - `scripts/assembly_drc.py` **[J]**, new: on every level of every shell there is metal
      0.06 mm outside each blend's circle and air 0.06 mm inside it, at three places along the
      arc, and metal in the middle of each web's pocket. Its canary is the same section with
      each junction put back the way it was, which must fail all sixteen. On the shells as
      committed before this it is red at every junction on every level (48 per shell); and on a
      build with all twelve at R2.00, **[F]** and **[H]** are red at the ferrite sheet (0.111 mm²,
      0.187 mm deep).
    - **[G]** skips the stations a blend stands on, as it always has a boss's: 1,880 stations
      where there were 2,102. **[I]**: the two relieved bosses 0.998 / 0.999, the lip 0.999.
  - **The sheet** calls the blends in its boss callout and in note 5 ("BOSS-TO-WALL JUNCTIONS ARE
    MODELED: 10× R2.00 + 2× R1.00 BLEND …"), draws them on the plan with a stub of the wall each
    runs into — hidden behind a floor, visible on the open frame — and no longer calls those
    corners sharp. The tool rule stands for whatever concave corner the model still leaves square.
  **…AND EACH ANNULUS JOINED TO THE FRAME, ON THE BACK, 2026-11-14 (DRH: "give the back face the
  same blends") — SO THE MAX AND LITE SHELLS CHANGED ONCE MORE.** The air frame has no back face
  and the braces sit in the cavity, so those three solids are as the block above leaves them.
  Board coordinates; this repo's instruments, on a local build with CI's pins — none of it is a
  SolidCraft figure yet.
  - **Sixteen blends, all R2.00.** On the back each mount carries a proud annulus (r 2.60, as
    tall as the frame, 0.15), and the annulus crossed the inner edge of the proud frame — the
    edge of the recessed art field, at x 2.05 and 48.75, y 2.05 and 86.85 — at a sharp inside
    corner of 71.6°, left to the back tool's radius on the side of the shell that is seen. Two
    a boss: a mid-span boss crosses its long edge twice, a corner boss crosses both edges it
    sits beside. Each is a modelled concave blend now, a true cylinder as tall as the frame,
    laid out as the cavity's are (`fit_rules.back_blends()`, the same `_blend_at`) and set the
    same 0.002 mm past tangent. **That offset is a crease, on both faces, and a measurement
    will find it:** a blend does not meet its neighbours at a true tangent but at 2.56° to the
    wall and 3.41° to the boss or annulus (3.62° and 4.26° at the cavity's two R1.00). It is
    0.002 mm of metal, there so that a kernel is handed a crossing and not a tangency. Nothing
    limits a radius on the back — no part, no coil, no ferrite — so none is held to R1.00. Axes: at the corner boss at (2.87, 2.87), (4.048, 7.315)
    and (7.315, 4.048), and the same at the other three corners by symmetry — (46.752, 7.315)
    and (43.485, 4.048); (4.048, 81.585) and (7.315, 84.852); (46.752, 81.585) and
    (43.485, 84.852). At the mid-span bosses, x 4.048 on the west and 46.752 on the east, at
    y 24.185, 33.075, 55.825 and 64.715. Each meets the frame 1.977 mm beyond the old corner
    and adds 0.667 mm² in plan, 10.678 in all.
  - **The edge-break is the back's own.** The blends go on before the deburr, so the frame's
    0.10×45° break runs round frame, blend and annulus as one edge. No cone is cut for it.
  - **The reeded fields give way (max only).** Twelve of the sixteen stand in a fin field. The
    pour wraps each at `FIN_BOSS_CLR` 0.40, as it wraps an annulus, so the valley's edge runs
    round boss and blend as one curve and the ribs beside a boss end a little shorter: still
    38 ribs, rib area 979.398 → 974.016 mm², valley 2456.246 → 2443.553. No rib stands closer
    than 1.189 mm to a blend.
  - **The numbers.**
    - Max STEP: **30,914 edges, 10,453 faces**, 35 under 0.001 mm², none shared
      by more than two faces; **5312.813 mm³** (was 28,512 / 9,647 / 35 / 5307.193). STL
      5312.64. Of the 806 faces more, 32 are the blends and their breaks and the rest are the
      valleys' walls where they now run round a blend.
    - Lite STEP: **1,103 edges, 415 faces**, 35 under 0.001 mm²; **3935.970 mm³** (was 1,023 /
      383 / 35 / 3934.199): 32 faces more, a cylinder and a break for each blend. STL 3935.83.
    - `scripts/assembly_drc.py` **[J]** probes the sixteen on a cut through the frame's height,
      as it probes the cavity's twelve: metal 0.06 mm outside each blend's circle, air 0.06 mm
      inside it, at three places along the arc, with the junction put back sharp as its canary.
      `check_consistency` **[8]** counts sixteen, all at `BLEND_R`, and holds the pour to
      `FIN_BOSS_CLR` off them.
  - **The sheet.** The plan's back outline was a rounded rectangle with eight full circles
    drawn across it — two primitives, the outline of neither. It is now the inner outline of
    the proud metal itself (`fit_rules.back_proud_poly()`: frame, annuli and blends, one
    piece), and the rear-art block says "BOSS ANNULUS TO FRAME (PLAN): 16× R2.00 CONCAVE BLEND,
    FRAME HEIGHT, MODELED." on the max and lite sheets. The air sheet is unchanged to the byte.
  - **What the first build got wrong.** The pour's keep-out round each blend was taken as it
    came from the blend metal's outline, which is drawn far finer than the circles beside it,
    and every vertex of a keep-out becomes a wall face of the valley: the max shell came out at
    14,851 faces and a 62 MB STEP, valid, with every gate green. Face count is ungated on
    purpose. The keep-out is drawn at the circles' own chord now (`_FIN_ARC`).
  **THE CONTOURING PASS, 2026-11-14 (DRH, looking at the eight bosses and the two tabs from the
  cavity side: "eliminate the hard corners and radius them … make them mostly symmetric or
  even") — SO ALL THREE SHELLS CHANGED ONCE MORE.** Only ever less metal. The braces and the
  reflow shim move by microns (last bullet). Board coordinates; this repo's instruments, on a
  local build with CI's pins — none of it is a SolidCraft figure yet, and **an ArtCraft or
  SolidCraft run against `466e1de` or earlier measures the bosses and tabs as they were before
  this.**
  - **Even: one flat for all eight.** Each boss was cut back for its own supercap by that cap's
    own numbers, so the flats stood 1.475, 1.524, 1.545 and 1.676 mm from their axes. Every flat
    is now **1.475** (`fit_rules.boss_flat_d()`: the least any cap leaves any boss, so no cap is
    cleared by less than its bay asks). The bosses stand 0.75–0.95 mm off their caps' nominal
    outlines (were 0.75 at all eight), and each keeps 79.8–81.6 % of its annulus (were
    80.4–85.9 %). The thread keep-out is r1.30; nothing comes nearer an axis than the flats.
  - **Symmetric: the flat runs the whole boss.** A mid-span boss kept a lump of itself beyond the
    end of its cap's keep-out, on one side only, with a Ø2.0 bore in the corner. The flat is a
    full chord now, so **the two mid-span bores are gone** (they were at (45.430, 30.341) and
    (45.602, 58.555)) and each mid-span boss is its own mirror image about the line through its
    axis (0.0000 mm² of difference, `check_consistency` [8]). To keep it so:
    - **the coil hollow is cut on both sides** of the two east mid-span bosses — the real one
      about (46.9, 32.2) and (46.9, 56.8), R1.15, and its mirror image about (46.9, 25.06) and
      (46.9, 63.74), where no copper asks for it;
    - **the blend opposite a ferrite-limited one is R1.00 too**: (48.552, 25.086) and
      (48.552, 63.814) join (48.552, 32.174) and (48.552, 56.726). **Eight blends are R2.00 and
      four R1.00** (were ten and two); the sheet says "R1.00 AT THE 2 BOSSES BESIDE FERRITE
      FER1".
    At a corner boss the flat runs out to the short-edge wall, and the one bore a corner boss
    still needs is parked the same distance from that wall at all four: axes (4.947, 1.048),
    (45.853, 1.048), (4.947, 87.852), (45.853, 87.852), each 1.763 mm from its screw axis (were
    1.76–1.94). The four are one shape: north–south pairs mirror exactly, east–west pairs but
    for 0.0016 mm² (next bullet).
  - **Round: twenty R1.00 rounds on the bosses.** Every outside corner of a boss is a round of
    `CONTOUR_R` (the finisher's radius) and a true cylinder in the STEP
    (`fit_rules.boss_rounds()`), 1.081 mm² in plan:
    - 4 where a corner boss's flat meets its bore (0.015 mm² each);
    - 6 where a west boss's flat meets its BLEND (0.070): the west lip is 2.5 wide, the blend
      takes over the boss's circle 0.63 mm from the end of the flat, and the round rests on
      flat and blend with that stretch of circle gone;
    - 2 where an east corner boss's flat meets the boss's own circle (0.071): the east lip is
      1.25 wide, the blend starts farther round, and the round ends on the circle 0.57 mm short
      of it. This is the 0.0016 mm² by which a west corner boss is not the mirror image of an
      east one;
    - 4 where an east mid-span boss's flat meets a coil hollow (0.092 at y 28.63, 0.133 at
      y 60.27 — the coil's two corners are not the same distance from their bosses, 3.57 and
      3.47 mm, so those two bosses differ by 0.1 mm in where the hollow sits);
    - 4 where a coil hollow runs out into the boss's circle, at 150° or more: 0.0005 and
      0.0056 mm², the removed corner 0.007 and 0.035 mm deep. They are cut all the same, so
      that the sheet can say EVERY outside corner.
    Like the blends, a round is set 0.002 mm past tangent into each face it rests on, so it
    meets them at a 3.62° crease and not a tangency. No break is modelled on a round's top
    edge (nor on a flat's or a bore's — the deburr note); on the air frame each carries the
    resting face's 45° break.
  - **The two short-edge tabs.** Between the supercaps on each short edge the lip stands as a
    tab: x 23.5–27.0 on the south, 23.5–27.5 on the north, 2.00 deep. The guaranteed ring used
    to add a strip 0.1 mm wide down one side of the south tab; the ring gives way at a tab now
    (`fit_rules.ring_reliefs()`), so each tab is what the void leaves and mirrors itself. **Four
    R1.00 rounds** take the tip corners (`fit_rules.tab_rounds()`, axes (24.498, 1.002),
    (26.002, 1.002), (24.498, 87.898), (26.502, 87.898); 0.838 mm² in all), true cylinders
    carrying the lip's own 0.10×45° break. A tab is 2 × R1.00 deep, so its root fillet ends
    where its tip round begins: the side of a tab is an ogee with no straight in it. The two
    tabs are still different widths, because the south and north supercaps stand 0.5 mm apart
    in x — which is also the 0.5 mm by which a lite or air shell is not its own mirror image.
  - **The numbers.**
    - Plan metal at the seat 458.431 → **452.171 mm²** (−6.260): 3.720 off the bosses, 1.361
      less blend, 0.983 off the lip, the rest where they overlap.
    - Volumes by OCC on the STEPs: **5301.692 / 3928.453 / 983.025 mm³** (max / lite / air; were
      5312.813 / 3935.970 / 990.335). STL 5301.51 / 3928.31 / 982.99. **That is 0.049 g of a
      23.5 g max shell, 0.033 g of the lite and 0.058 g of the 316L frame** — the pass is for
      the shape; the floor is where a shell's mass is.
    - Max STEP **30,979 edges, 10,476 faces**; lite **1,168 / 438**; air **1,347 / 503**; 35
      faces under 0.001 mm² on each (the air frame had 36), none shared by more than two.
    - `scripts/assembly_drc.py`, all three variants 0 errors. **[H]**: the max-material
      supercaps stand 0.150 (SC1), 0.199 and 0.220 from as-milled metal, or more (all four were
      0.150); the ferrite sheet 0.149, as before. **[I]** 0.999 at both relieved bosses and the
      lip. **[G]** 1,922 stations. **[J]** now probes the rounds as it probes the blends, the
      other way round — metal 0.03 mm inside each circle, air 0.03 mm outside it, with the
      corner put back sharp as its canary: **16 of the 20 boss rounds and all 4 tab tips**. The
      four slight ones take off less than a section of an STL can see, and [J] says so.
    - **So the shell generator holds all 24 itself:** it refuses to export a solid unless each
      round's cylinder — its radius, about its axis — is among the solid's faces, and proves on
      every run that a round moved 0.5 mm is reported missing.
    - `check_consistency` **[8]**, new step 4d: one flat distance; each mid-span boss its own
      mirror image; the corner bosses one shape; and, by an instrument that owes
      `boss_rounds()` nothing, no outside corner left on a boss that a ball of R0.95 cannot
      roll round (0.004 mm² at worst against a bar of 0.02; with the rounds put back sharp all
      eight bosses fail, 0.086–0.281).
    - `handedness_drc` **[E]**, the STEP against its own STL reflected: 0.600 / 0.501 / 0.501 mm
      (were 0.600 / 0.465 / 0.435; the bar is 0.20). **[S], [T], [K], [P], [M] and [B] need
      KiCad's own export and have not been run on these solids here** — the merge run does.
  - **The braces and the shim.** The brace footprint is 1312.70 mm² still. The solids move in
    the sixth figure — **1916.605 / 1135.276 mm³** by OCC (were 1916.609 / 1135.278), same edge
    and face counts — and the reflow shim's outline by at most 0.0079 mm beside the two east
    mid-span bosses (969.230 → 969.229 mm²): both follow the cavity as milled, and that moved
    where two R2.00 blends became R1.00.
  - **The sheet.** The boss callout is one wrapped paragraph now (it was broken by hand, and
    each clause that grew pushed a line into the rim's label beside it): "CUT BACK TO A FLAT
    1.47 FROM ITS HOLE AXIS, ALIKE ON ALL 8 … 0.75–0.95 CLEAR OF THE PART BESIDE IT … 2 ALSO
    HOLLOWED R1.15 … AND THE SAME ON THE FAR SIDE TO MATCH … 8× R2.00, 4× R1.00 BLEND … EVERY
    OUTSIDE CORNER OF A BOSS R1.00 (20×)". Note 8 adds "TAB TIP CORNERS 4× R1.00, MODELED."
    The plan draws each boss's finished outline — flat, hollows and rounds as one line.
  - **What the first builds got wrong.**
    - The rounds were first found AND solved by rolling a ball in polygons. That is good to
      0.005 mm, and on the west bosses the question it had to answer — flat and blend, or flat
      and circle — is decided by 0.0026. It chose the circle and left a 0.01 mm step in each
      of six blends. The polygons find the corners now; the faces themselves decide.
    - The tab tips were first rounded in the void's own polygon, which is simplified to 0.01
      for the kernel: each came out as three or four flats, a different three or four at each
      corner, on a pass whose point was symmetry. They are cylinders now, cut after the void.

  **THE SIMPLER CUTS, 2026-11-15 (DRH, on a plan of the cavity with two places circled: "there
  are two surfaces I want to mill away material so they are smooth contiguous surfaces for the
  milling to be done simpler", and then "see if there are any others just like those") — SO ALL
  THREE SHELLS, BOTH BRACES AND THE SHIM CHANGED ONCE MORE.** Board coordinates; this repo's
  instruments, on a local build with CI's pins. **An ArtCraft or SolidCraft run against
  `2494c9f` or earlier measures the west wall, the two east mid-span bosses and the tab roots
  as they were before this.**
  - **The west wall is one straight face.** The west lip was 2.50 wide and stepped in twice, to
    2.32 beside R16 and 2.25 beside C24 (0.18 and 0.25 mm, over y 44.5–50.5). It is **2.25 the whole
    edge** now — the narrowest any part asks for, `fit_rules.LIP_ONE_WIDTH`; the east lip was
    already one width, 1.25. The sheet's note 8 reads "WEST 2.25 FULL LENGTH (C24)". The
    guaranteed ring is held to the same width there (`ring_widths()`), and the brace's west
    edge follows the wall, x 2.55 → **2.30** (`cavity_rect()`).
  - **The two east mid-span bosses are cut straight.** Each side of each had a hollow (R1.15,
    about the coil's corner) and a hump beyond it; the contouring pass had mirrored that onto
    the side with no coil. Each side is now **one straight cut 2.32 mm from the screw axis**
    (`fit_rules.boss_coil_chord_d()`: the nearest the coil's clearance lets a line come to
    either boss, used on both sides of both), with an R1.00 round where it meets the flat and an
    R1.00 blend into the wall. The four hollows, the four slight rounds at their ends and the
    0.1 mm by which the two bosses differed are gone: the two are one shape, and each is still
    its own mirror image. Sixteen boss rounds now (were twenty); eight R2.00 blends and four
    R1.00 still, the four now joining two planes.
    - The coil stands **1.068 and 1.166 mm** from those bosses in the sectioned metal (was
      0.999 at both; the rule is 1.00).
    - **The ferrite sheet's tight corner stands 0.350 mm from titanium** (was 0.149 — the
      clearance nobody chose; `assembly_drc` [F]). Against `FER_CLR` 0.20 that closes the open
      question of the 2026-11-14 record, unless DRH wants more.
    - The cuts are 2.32 from the axis against a thread keep-out of r1.30. **Those two bosses
      keep 75.8 % of their annulus** (were 81.2 and 80.0); the other six keep 79.8–81.6 as
      before.
  - **The four tab roots are true R1.00, on the wall that is there.** Each tab met the
    short-edge wall through the fillet a finisher-radius opening leaves in the void's polygon,
    laid out from the BOARD edge. The cavity's wall on a short edge is the RECESS wall, 0.05
    inside it, so the curve met its own wall at a 19° kink — and, being polygon, as three or
    four flats. Each root is a cylinder now (`fit_rules.tab_roots()`, axes (22.502, 1.048),
    (27.998, 1.048), (22.502, 87.852), (28.498, 87.852)), tangent to the recess wall and to
    the tab's side, carrying the lip's 0.10×45° break. A Ø2.0 finisher cuts exactly this
    whatever the model says; the model says it now. The tabs themselves are exact rectangles
    under the rounds (next bullet but one).
  - **Asked of DRH — both answered "yes" later the same day and built (THE CORNER BOSSES AND
    THE TWO TABS, below):**
    - **the corner bosses.** Between the short wall and each corner boss's flat there is the
      Ø2.0 bore and a small R1.00 round, 0.66 mm long. Running the flat straight to the wall
      with a plain R1.00 would remove four bores, four rounds and four webs — and leave that
      R1.00 **0.07 mm inside the corner of a max-material supercap** (0.005 mm² in plan; a
      nominal cap clears it by 0.75). The bore exists for exactly that corner. Whether it
      matters rests on the same thing as the floor fillet: is the pouch's extreme corner thin
      foil, as DRH's photograph of a WS17F suggests, or full thickness? The datasheet does not
      dimension it. One caliper check answers both.
    - **the two tabs alike.** Top to bottom, the inside of every shell now differs only by the
      north tab being 0.5 mm wider than the south (4.0 against 3.5). Cut alike they cost about
      1 mm² of seat, and the lite and air shells become their own mirror images.
  - **Looked at and left:** the west mid-span bosses (R2.00 into R1.00 each side), the east
    corner bosses (three arcs, tangent), and the whole back face (straight frame edges, R2.00
    blends, the annuli) — the survey walked both outlines as straights and arcs and flagged
    nothing short or stepped on any of them.
  - **The numbers.**
    - Plan metal at the seat 452.171 → **434.622 mm²** (−17.549).
    - Volumes by OCC on the STEPs: **5269.930 / 3906.929 / 961.850 mm³** (max / lite / air; were
      5301.692 / 3928.453 / 983.025). STL 5269.77 / 3906.80 / 961.83. That is **0.14 g of the
      23.5 g max shell**, 0.10 g of the lite and 0.17 g of the 316L frame.
    - Max STEP **30,711 edges, 10,387 faces** (were 30,979 / 10,476); lite **900 / 349** (were
      1,168 / 438); air **936 / 366** (were 1,347 / 503). 37 faces under 0.001 mm² on each
      (were 35): the two more are at board (3.2, 0.25), 0.01 mm tall, where the ring's relief
      crosses the corner-relief step — three faces there before, one of them 0.0021 mm²; four
      now, all under 0.001. None shared by more than two.
    - **The STLs' one ledgered seam is gone.** `check_mesh` had allowed each shell one
      zero-length open edge and three zero-area facets "where the south band-step fillet at
      x 27.0 meets its wall" (two and four on the air frame). That was the tab root's kink.
      All three shells now read 0 open edges, 0 degenerate, and the ledger holds them there.
    - Braces **1926.670 / 1141.415 mm³** (were 1916.605 / 1135.276), footprint 1312.70 →
      **1319.30 mm²**, envelope 46.95 → **47.20** wide: the strip down the west side. Shim net
      area 969.230 → **969.442 mm²**, its outline moving by at most 0.154 mm, beside the two
      east mid-span bosses; its eight inner contours are identical.
    - `scripts/assembly_drc.py`, all three variants 0 errors. **[G]** "W 2.25; E 1.25; S
      2.00/none; N 2.00/none", 1,926 stations. **[H]** max-material supercaps 0.150 / 0.199 /
      0.220 from as-milled metal, as before. **[I]** as above; its fatter-coil canary still
      reaches both bosses and refuses to call itself proven if one ever stands a quarter
      millimetre past the rule. **[J]** probes the four tab roots as blends between two
      planes: 56 junctions and corners in all, each failing with the corner put back sharp.
    - `check_consistency` **[8]**, new step 4e: each of the two long lips one band and its
      wall one straight run between every pair of bosses (a 0.2 mm step let into the west wall
      must be seen, and is); each coil-cut boss straight on both sides, the same length on
      both; each root R1.00 on the recess wall, and by a rolled ball of R0.95 nothing left
      unreached at a root (0.0003 mm² at worst; with the roots taken out all four fail).
  - **THE HAND.** The west lip's two steps were what `handedness_drc` [S] told a shell from its
    top-for-bottom mirror image by (R16 lost 0.18 mm of clearance). With the wall straight
    that mirror image **is the same cavity wherever a part stands**: the two differ by 1.93 mm²
    on a level, all of it at the tabs and more than 0.5 mm from every part. [S] used to call
    "fits no worse" an error without exception; it now accepts it only if it can show that —
    it lays the mirrored sections over the sections as written and looks for any difference
    within reach of a part — and says which gate holds that hand instead. **That gate is
    `assembly_drc` [J], by the two tabs. Tried, not assumed:** each rebuilt shell's STL
    reflected top for bottom fails [J] at twelve probes (the east side of both tabs, three
    levels) and passes everything else, [G] included — a step 0.5 mm from where the lip table
    puts it is inside the blend allowance [G] gives every step. The half-turn mirror still
    lands its lip on the bare JP1 / TP1 pads (7.7 mm² here, against board_parts' outlines).
    [S]'s verdict was split into a function so that it could be exercised here at all — there
    is no `kicad-cli` outside the pinned image. **Against KiCad's own export, in CI on the
    branch (PCB CI runs 661 on `7d0a776` and 662 on `4955077`, both green): crowding 0.451 mm
    as written and 0.452 for the top-for-bottom mirror image (tightest JP1 / TP1 at 0.300),
    the two differing by 1.93 mm² on a level, all of it within x 26.3–28.2; the half-turn
    mirror 7.714 mm² inside parts; [K] [P] [M] [B] [E] [T] 0 errors.** The merge run measures
    main's own rebuild. `handedness_drc` [E]: 0.600 / 0.500 / 0.500 mm reflected (the bar is
    0.20).
  - **What the first builds got wrong.**
    - **The ring put the steps back.** `RING["W"]` guarantees 2.5 mm of seat; the lip rule
      cut the band to 2.25; the shell unions the two; and the ring is relieved only where a
      part stands. First build: a west wall at 2.50 with a relief at R16 and one at C24 — the
      two steps, exactly as before, from a rule that said there were none. `lip_as_cut()`
      refused it. A guaranteed minimum that is wider than the thing it guarantees is not a
      floor.
    - **The brace did not follow.** It is cut inside a scalar rectangle whose west edge was
      2.50 — the lip's old width, typed. With the wall at 2.25 the brace would have stood
      0.30 mm off a face it is meant to bear on with 0.05, free to slide the quarter
      millimetre its pockets clear a part by. Nothing failed: `assembly_drc` [B] asks whether
      the brace FITS, and a brace that is too small fits. Found adding up the plan areas.
    - **A tab's side leaned.** The void is simplified by 0.01 for the kernel, and on the
      south tab the simplify kept a vertex 0.008 mm along the tip in place of the corner: one
      side leaned 0.23° and the other did not, under four cylinders laid out as if both were
      square. The tabs are made exact rectangles AFTER the simplify now (`_tabs_squared`).
    - **A break with nothing to run into.** A blend carries the lip's 0.10×45° break round it
      as a cone, which at its far end runs into the boss's own chamfer ring. On the two
      straight-cut bosses the far end is the cut — made after the deburr, no break, like a
      flat — so the cone ran on into the boss, was filled back by it, and showed through only
      in the 0.1 mm where the buried chamfer ring had already lowered the boss's top: a notch
      and a three-cornered facet at the end of each of the four breaks. Every gate was green;
      it was seen in a close-up render made for DRH. The cone is held to the blend's side of
      the cut now, and those two bosses are built without a ring that is nowhere on their
      surface (holding the cone alone left a 5×10⁻⁷ mm² face at two of the four, between two
      coplanar faces that could not merge across the ring). The break runs out to nothing
      against the cut's plane, as a west blend's does against its round.
    - Three of the new checks failed on a correct part before they failed on anything else: a
      straight wall has no vertices between its ends to test, a round's arc comes within any
      tolerance of the line it is tangent to, and a rolled ball cannot reach the corners of
      its own window.

  **THE FLOOR MEETS THE WALL THROUGH A RADIUS, 2026-11-15 (DRH: "to have the floor meet the sides
  at a curve using a ball endmill ... to give a slight amount of support to the thin 1mm floor";
  then R1.0, and none "for any place that has an interface between the brace and titanium";
  then, on a prototype of eight straight runs, "apply as you displayed") — SO THE MAX AND LITE
  SHELLS CHANGED ONCE MORE.** The air frame has no floor and did not. Board coordinates; this
  repo's instruments, on a local build with CI's pins.
  - **Eight runs, 132.86 mm** _(133.37 as first pushed; evened the same day, below; **132.28
    since the corner bosses and the tabs**, the next record, which has the runs as they are
    now)_. An R1.00
    fillet (`fit_rules.floor_runs()`) on each long straight stretch of cavity wall that no
    brace comes near anywhere along it — the walls of the four supercap bays:
    - south wall x 5.37–22.08 and x 28.92–45.43; north wall the same two;
    - west wall y 7.65–23.85 and y 65.05–81.25; east wall y 7.86–24.88 and y 64.02–81.04.
    Not the middle of either long wall: the brace bears on the east one from end to end and on
    the middle of the west one, and a run is a whole stretch or none, so no run ends in mid-wall.
    Not round the bosses, whose flats are 2.3–3.2 mm long. The same eight on both shells.
  - **How a run ends.** 0.50 short of the feature at each end of its stretch (a boss's blend, a
    corner boss's bore, a tab's root), in the scoop a FLAT cutter of the same radius leaves where
    it finishes the sharp corner beyond: a vertical R1.00 cylinder. Two cutters of one radius
    leave the last 0.3 mm of each run as a feather against the wall; that is the deburr note's.
  - **EVENED, TOP FOR BOTTOM — the one departure from the prototype picture, and CI asked for
    it.** As first pushed (`de4894c`) every run stopped 0.50 short of its own stretch. The run
    east of each short-edge tab starts from that tab's root, and the tabs differ by 0.5 mm in
    width, so those two runs began at x 28.42 (south) and 28.92 (north).
    - PCB CI run 663 went red at the handedness gate, on the max and lite shells, with the mesh
      gates and `assembly_drc` green: top for bottom, the shell's mirror image fitted KiCad's
      board exactly as well as the shell (crowding 0.917 against 0.916) **though 0.109 mm² of
      its fillet within 0.5 mm of a supercap was not where the shell's is**, near board
      (29.55, 0.56). `[S]` will not accept "fits no worse" unless it can show the two are the
      same cavity wherever a part stands. It was right not to.
    - The cure is in the part: a run reaches no further than its twin under y → H − y. **The
      south run east of the tab now starts at x 28.92, 1.00 short of its tab's root instead of
      0.50** — half a millimetre of fillet, 0.109 mm³, beside SC2's west corner. Only ever less
      fillet, the contouring pass's rule. The east wall's two runs moved by 0.004–0.010 mm for
      the same reason (the cut outline's own simplify). If the two tabs are ever made alike
      the rule gives nothing up and that run goes back to 0.50.
    - `check_consistency` [8] 4f holds the fillets' metal to its own mirror image, by the
      polygon and not by the bookkeeping, with the lost half millimetre put back as its canary.
    - **Why it reached CI.** The local rehearsal of `[S]` was a scratch script that gave any
      body without a tabled height 0.5 mm — and `part_height()` returns `None` for the four
      supercaps, so the cut above the floor passed through none of them. With their own 1.70
      the same script reproduced CI's 0.109 mm² at the same place. It is in the gate now
      (`python3 scripts/handedness_drc.py --rehearse`): the parts' own heights, 0.10 deeper
      (KiCad's bodies hang a little lower than the table), a refusal for a body with no
      height, and a self-test that its lowest cut passes through a supercap on a floored
      shell. On the evened shells it is green and the mirror image differs by 1.93 mm² at the
      tabs, as before the fillet; on `de4894c`'s shells, rebuilt, it is red on max and lite
      with CI's own figure at CI's own place.
    - **In CI, against KiCad's export (run 664 on `8bb76c6`, green):** crowding 0.916 mm as
      written and 0.917 for the top-for-bottom mirror image on max and lite (0.451 / 0.452 on
      air), the two differing by 1.93 mm² at the tabs and by nothing within 0.5 mm of a part;
      the half-turn mirror 7.714 mm² inside parts. Mesh gates and `assembly_drc` 0 errors.
  - **Each run is three true cylinders** — one lying along the wall, one standing at each end —
    each set 0.002 mm past tangent like every blend here, so the fillet as modelled reaches
    0.935 mm from the wall and 0.935 up it. Everything that has to clear it is measured to a
    tangent one, 1.00. The nearest brace is 1.05 mm past that.
  - **WHAT STANDS OVER IT, AND WHAT IS NOT CLEARED.** Nothing machine-placed hangs over any
    run. The south and north runs stand under the supercaps' edges:
    - a can at its nominal outline is 0.95 from the wall, past the toe: **0.050 mm clear** on
      the max shell with the cavity 0.05 shallow (0.170 on lite);
    - a can at MAX MATERIAL, taken as square-edged, stands 0.35 from the wall where the fillet
      is 0.24 high: **0.187 mm into it** on max (0.067 on lite). That is not cleared. DRH's
      answer, with a photograph of a WS17F: the can is a foil pouch — "rectangular pillows with
      a general maximum height ... the thickness is not even, particularly on the extreme
      edges" — and its outline is the sealed margin, not the body;
    - so the rule is stated as what it needs: **the can must still be thinner than its stated
      1.70 for 0.33 mm in from its max-material outline** on the max shell (0.09 on lite,
      `floor_cap_margin_needed()`), against a margin TAKEN to be 0.50
      (`FLOOR_CAP_MARGIN`, **PROVISIONAL**). The datasheet does not dimension the margin. The
      bench item above ("Put a caliper on a supercap's edge") is what makes it a measurement.
  - **The numbers.**
    - OCC on the STEPs: **5296.050 / 3933.050 mm³** (max / lite; were 5269.930 / 3906.929
      before the fillet, and 5296.159 / 3933.158 as first pushed), air 961.850 unchanged. STL
      5296.00 / 3933.04. +26.12 mm³ each, **0.12 g** of titanium: the fillet's section as cut
      is 0.2108 mm², 28.01 mm³ over the eight runs before the sixteen ends are scooped.
    - Max STEP **30,783 edges, 10,411 faces**; lite **972 / 373** (+72 / +24 each: three faces a
      run). 37 faces under 0.001 mm², as before; none shared by more than two.
    - `scripts/assembly_drc.py` **[K]**, new: on the cut just above the floor, metal 0.06 mm
      inside each fillet's edge and air 0.06 mm outside it at three stations, air at both ends
      of every run and beyond them — 80 probes a shell — and the same cut with each fillet
      taken out fails all eight. It prints the three supercap figures above and says
      PROVISIONAL. All three variants 0 errors.
    - **[G] moved up.** The lip check sectioned the shell at mid-cavity; on the lite shell an
      R1.00 fillet is still 0.07 mm of metal there, and the lip note describes the lip. It
      reads the cut just under the seat now, below the lip-break and above the fillets.
    - `check_consistency` **[8]**, new step 4f: eight runs; the fillets' metal against its own
      mirror image top for bottom; each brace's footprint against each run's wall, by an
      instrument that owes `floor_runs()` nothing; the margin needed against the margin taken;
      and a synthetic part planted over a run must be seen.
    - The shell generator refuses to export a floored shell without each run's lying cylinder
      among its faces, and proves a run moved 0.5 mm off its wall is reported missing.
  - **The sheet.** Note 7 is the fillet — "FLOOR MEETS WALL THROUGH R1.00 (Ø2.0 BALL END MILL),
    MODELED, ON 8 RUNS (132.9 mm; HEAVY DASH ON THE PLAN), EACH ENDING 0.50 OR MORE SHORT OF
    THE NEXT BOSS OR TAB. FLOOR CORNER SHARP ELSEWHERE." — the plan draws each run to scale,
    and Section A-A shows the arc. The block was full, so the note that said only "NO U7 RELIEF
    POCKET" gave up its line: the floor note says "NO U7 POCKET" itself. Every later note keeps
    its number. Also moved: the "0.10×45° FRAME (2 PL)" label, which had been set across the
    section's own title on every committed sheet.
  - **What the first build got wrong.** The fillet's toe. A cylinder set 0.002 into wall and
    floor leaves the floor at 0.935 from the wall, dips under it, and comes up again at 1.061;
    the first rules took 1.061 for the toe and cut the cover out to 1.11, which would have left
    a ridge 0.004 mm high along every run. The prototype's cover stopped at 1.05 by luck. The
    cover stops at 1.03 now, on purpose, and says why.
  - **Were DRH's, and the fillet followed:** the bore beside each corner boss and the two
    tabs' widths. Both decided the same day — the next record.

  **THE CORNER BOSSES AND THE TWO TABS, 2026-11-15 (DRH: "Yes to a b and c" — the plain corner,
  the tabs alike, and the pull request) — SO EVERY SHELL CHANGED ONCE MORE, AND TWO OF THE
  THREE NOW HAVE NO HAND.** Board coordinates; this repo's instruments, on a local build with
  CI's pins. The braces did not change (1926.670 / 1141.415 mm³).
  - **A. Each corner boss's flat runs to the short-edge wall through one true R1.00**
    (`fit_rules.boss_roots()`). Until now the flat stopped 0.25 mm short of that wall and three
    things stood in the corner: a Ø2.0 bore parked against the wall, a round 0.66 mm long
    between the bore and the flat, and the web the bore ended.
    - The flat is one plane from the boss's far round to the recess wall, x 4.345 on the west
      bosses and 46.455 on the east. The corner is a true cylinder — axes (5.343, 1.048),
      (45.457, 1.048), (5.343, 87.852), (45.457, 87.852) — tangent to flat and wall but for
      0.002, laid out exactly as a tab's root is, with the lip's 0.10×45° break held to its
      own side of the flat (a flat is cut after the deburr and has none).
    - **Gone:** all four bores (no boss on this shell carries a bore any more) and the four
      short rounds — **12 boss rounds, were 16.** **Still there:** the four webs, which now
      end on the flat instead of on a bore (0.41 / 0.32 mm² in plan, west / east). _(Message
      to DRH had said the webs would go too. They cannot: the boss's circle stands 0.22 mm
      off the recess wall, and that slot is west of the flat.)_
    - **WHAT IT COSTS — PROVISIONAL, like the floor fillet.** The bore was there so that the
      finisher's radius left no metal inside a max-material supercap's corner. The plain
      corner does: **0.070 mm at the very corner of a square-cornered SC1** (0.0053 mm² in
      plan), 0.031 into SC4, 0.015 into SC3, none into SC2. A can at nominal is 0.745–0.945 mm
      away. It clears if the can's body stays **0.05 mm** inside its max-material outline at
      that corner (`boss_root_cap_need()`), against the 0.50 a pouch's sealed margin is TAKEN
      to give — the floor fillet's assumption, and the same bench item above now asks for a
      look at a corner. `assembly_drc` [H] measures it in the sectioned shell (0.050 / 0.022 /
      0.011 mm deep into SC1 / SC4 / SC3 at max material), lets off only metal inside a root
      `fit_rules` lays out, holds the can's BODY to the as-milled metal instead, and fails if
      the rule and the part disagree about the cost.
  - **B. The two short-edge tabs are the same width, 3.5 mm** (x 23.5–27.0 on both edges; the
    north tab was 4.0). The south and north lips are ONE table now (`fit_rules.LIP_TWIN`: a
    station's lip is the lesser of what the two edges allow), so the sheet says them once —
    "SOUTH AND NORTH 2.00; NONE x3.0–23.5 (SC1, SC3), x27.0–47.5 (SC2, SC4)". The north tab
    gave up 1.000 mm² of seat (0.975 in the metal, less its root's arc).
  - **The floor fillets followed, by their own rule:** 132.28 mm (was 132.86). The runs along
    the short walls start 0.50 mm past each corner boss's root now, not past its bore, and the
    evening rule gives nothing up — both runs east of the tabs stop 0.50 short again:
    - south and north walls x 5.77–22.08 and x 28.42–45.03;
    - west wall y 7.65–23.85 and y 65.05–81.25; east wall y 7.86–24.88 and y 64.02–81.04.
  - **THE HAND.** With the tabs alike, the inside of every shell is its own mirror image top
    for bottom — `check_consistency` [8] holds the metal's polygon to its own reflection
    (0.0000 mm² after a 0.02 erosion; a tab half a millimetre wider is its canary).
    - **The lite and air shells have no hand.** Each whole solid stands **0.010 mm** off its
      own reflection at most (the east wall's blends differ by that, the cut outline's own
      simplify); an STL gives up 0.05. They cannot be written, cut or printed in the wrong
      hand. `fit_rules.shell_has_hand()` declares it and `handedness_drc` [E] measures it: a
      shell declared handless that grows a hand goes red and asks what holds it.
    - **The max shell's hand is its rear art and nothing else** (0.600 mm off its own
      reflection). Nothing read the lettering until today — the tabs told the hand, and [J]
      held the tabs — so `assembly_drc` **[L]** is new: the coin's standing islands,
      sectioned through the proud face, lie where `medallion.geometry()` puts them to
      **0.0000 mm² of 136.2** (reflected top for bottom, as a shell written in the wrong hand
      would have them, 77.0 mm² off); and the monogram, seen as a person sees the back,
      matches the font's own "DRH" **0.998** against 0.638 / 0.795 / 0.587 mirrored left for
      right, top for bottom, and turned half a turn. The second measurement owes
      `medallion.py` nothing.
    - `handedness_drc` [S] accepts a mirror image that fits no worse only if its sections
      differ from the shell's by NOTHING; "differs, but only where no part stands" is an
      error again, since no gate is left that would hold a hand living there.
  - **The numbers.**
    - OCC on the STEPs: **5298.696 / 3934.795 / 963.702 mm³** (max / lite / air; were 5296.050
      / 3933.050 / 961.850): +2.646 / +1.745 / +1.852. In plan +2.487 mm² at the four corner
      bosses and −1.000 at the north tab (`shell_metal_poly`, old against new; sectioned on
      the air frame +2.527 and −0.975), less 0.12 mm³ of fillet on the two floored shells:
      +2.55 / +1.69 / +1.78 predicted. STL 5298.64 / 3934.78 / 963.68.
    - Max STEP **30,777 edges, 10,409 faces** (were 30,783 / 10,411); lite **966 / 371** (972 /
      373); air **936 / 366** (unchanged in count). Faces under 0.001 mm²: **33 on each, were
      37**; none shared by more than two.
    - 24 true R1.00 cylinders a shell are checked as faces at export: 12 boss corners, 4 tab
      tips, 4 tab roots, 4 corner-boss roots. `assembly_drc` [J] probes 56 junctions and
      corners a floored shell, the corner-boss roots among them.
    - All local gates 0 errors on all three variants.
  - **What the first build got wrong.**
    - A root's cover reaches 0.20 mm into the WALL so that the kernel unions it cleanly, and
      the plan polygon counted that as the shell's metal: 0.24 mm² a corner that is not
      there. No gate noticed. It was found adding up plan areas against the sectioned shells
      to explain the new volumes — the same way the brace's missing 0.30 mm was found.
    - The corner roots' self-test took the roots out of the finished polygon by subtraction.
      An island's outline is simplified by 0.005, so a slit two microns wide was left up two
      of the four flats, it joined the corner to the test window's own corner, and the test
      read "reachable" where it should have read a sharp corner. The metal is BUILT without
      the roots now, and the corner is measured by area inside its own square.

  **THE SEAT IS ONE PLANE, AND THE BRACE NESTS, 2026-11-15 (DRH, on a render of the brace in the
  shell with the four corner bosses circled: "it looks like something is overlapping on the
  surface"; then "I want the brace to get a tighter fit, matching the inverse at the ferrite
  side such that the plastic nests along the curve of the bosses", "on the northern and
  southern tabs, I want the brace extended such that it hugs either side of the tabs along that
  curve", and "let's try to make a somewhat exact fit, since these are complex curves that
  would be hard to sand out of the plastic") — SO ALL FIVE SOLIDS CHANGED.** The SolidCraft
  re-measure checkbox above is still open and still what an order waits on.
  - **The marks on the corner bosses were a step in the part, not in the picture.**
    - `_corner_relief()` cut the board recess's corner relief — a circle of R + 0.15 round each
      board corner, so the press grips the flats — from **0.01 mm under** the board-rest plane,
      to keep the cutter's end off the recess floor. The lip ring and the bosses are unioned
      afterwards and came back up to the plane. Nothing else inside those four circles did,
      and since 2026-11-14 every blend, web and root there was cut down on purpose to match
      (`_under_corner_relief`).
    - Measured on main's solids: **10.375 mm² of upward flat face at seat − 0.010, 316
      triangles, on the lite shell** (10.16 mm² by a 0.02 mm ray grid on the max shell), in a
      crescent under the relieved wall and two or three patches on each corner boss. That is
      SolidCraft's C4 of 2026-11-13, which this file called benign.
    - The relief starts ON the plane now, as the recess cut it widens always has;
      `_under_corner_relief` is deleted. On the rebuilt shells: **no upward flat face at
      seat − 0.010; in a 6.5 mm square at a corner, 22.69 mm² at 2.800 and nothing else flat
      between the floor and the rim.** What is still outlined there is the 0.10 × 45° break
      on the R1.00 corner and on the blend.
    - **The 33 faces under 0.001 mm² that every shell's STEP carried were all its steps.**
      Max 10,409 → **10,337** faces, 30,777 → 30,565 edges; lite 371 → **299**, 966 → 754;
      air 366 → **294**, 936 → 724; **none under 0.001 mm² on any of the three**, none
      shared by more than two faces. OCC volumes 5298.801 / 3934.900 / 963.806 mm³ (+0.105 /
      +0.105 / +0.104; 10.4 × 0.01 predicted).
    - The lite and air shells stand **0.005 mm** off their own reflection now, by
      `handedness_drc` [E]'s measure; it read 0.010 on main.
  - **The brace is the shell's void as milled, less one fit.**
    - `fit_rules.brace_cavity()` was held twice more than that: inside `cavity_rect()`, whose
      short edges are the tab tips, and outside a circle of `RELIEF_R` 2.85 round every boss
      axis. Both are gone from the brace (`nest=False` still gives them, and
      `scripts/reflow_shim.py` asks for it — that plate lies on the bare board; its outline is
      unchanged to the square micron, 969.437 mm²).
    - **At the two east mid-span bosses** the block now lies along each boss's straight cut
      and follows the round at its corner: it stood 0.317 mm off the corner and 0.53 off the
      cut. +2.00 and +2.03 mm². **At the two west ones** the arm's end pads follow the boss's
      circle and corner round, +0.24 and +0.27 (they already lay along the R2.00 blends).
    - **At each short-edge tab** the arm runs on as a prong on either side, following the
      tip's round, the side and the root's curve, to an R0.30 nose at the recess wall: +4.58
      and +4.75 mm². The prongs are 1.04 to 1.41 mm wide beside the tab — what the supercaps'
      bays leave. The two east ones follow all 90° of their root to the wall; the two west
      ones follow 83° and 77° and stop 0.06 and 0.09 mm short, where they would be thinner
      than `SLA_WALL` 0.60.
    - Footprint **1319.30 → 1333.19 mm²** (max), 1089.83 → 1103.78 (lite); the brace is
      **88.70 mm long, was 84.80**. STEP volumes 1950.663 and 1157.425 mm³ (+23.99, +16.01;
      25.0 less 1.33 under the ferrite channel predicted for max). 474 and 531 faces, none
      under 0.001 mm².
    - **The fit, as built:** `assembly_drc` [B] sections the emitted brace against the emitted
      shell at three levels and finds no overlap, closest **0.045 mm**; [H], with every inside
      corner given the Ø2.0 finisher's radius, 0.045 as well. It read 0.048 on main: the
      outline is a polyline, and a chord across an arc that hugs a convex corner stands
      nearer the metal than the arc. Its tolerance went 0.01 → 0.005 for that; at 0.01 the
      nested outline came to 0.040.
    - Coverage 32.82 % and 27.17 % of a floor that now counts the void beside the supercaps
      (4062.1 mm², was 3912.9): both ledgered floors hold, max by 0.82 of a point.
  - **Three rules that said "nothing stands there", and one that would have cost four fillets.**
    - `floor_runs()` gave a fillet to each stretch of wall no brace came near *anywhere along
      it*. The prongs stand over the last 0.2 mm of the four short-edge stretches, past where
      each run has already ended in its scoop — asked that way, **four of the eight floor
      fillets would have gone**, silently, in a change to the brace. It asks about the run's
      own metal now, scoops taken out: 0.17 mm at the nearest, against `FLOOR_BRACE_CLR`
      0.10. The eight runs are the same eight, 132.28 mm.
    - `check_consistency` [8] 4f measured the brace to a run's wall and took `FLOOR_R` off — a
      fillet with square ends. It lays the scooped fillet out itself now, and plants resin
      within 0.05 mm of one as its canary.
    - `interference_drc` held the brace's bounding box inside `cavity_rect()` as a check on
      the file frame, and read the new brace as "generator frame broke". It holds it inside
      `brace_cavity()`.
    - `cavity_as_milled()` is board area less metal, and beside a supercap there is no lip:
      the void's edge there is the BOARD's, 0.05 mm outside the recess wall. The nested
      outline is clipped to the recess first.
  - **What is not settled: whether a print will drop in.** The two forks' seats are 84.80 mm
    apart and each stands 0.05 mm off its tab; a Form 4's stated tolerance on a feature that
    long is ±0.3 % (lower limit ±0.15 mm), three times the allowance at its smallest. _(That
    was the wrong printer — the brace's print spec named a Formlabs class. It is PCBWay, whose
    stated ±0.2 mm is twice the allowance on all four seating dimensions, not just this
    one: the DECISION item above.)_ The
    square-ended arm had the same 0.05 at each tip, and could be sanded. DRH asked for the
    exact fit knowing the curves cannot be ("let's try"), so it is cut as asked, and the bench
    item above ("Measure the print over its two forks") is what turns the first print into a
    measurement of the printer instead of a part that will not go in. A looser nest is one
    number — but one number everywhere: a second fit for the curves alone would put a step in
    the outline wherever a curve meets a flat.
  - **All local gates 0 errors** on the rebuilt solids: `check_mesh` (five re-ledgered, each
    itemised), `interference_drc`, `assembly_drc` on all three variants, the handedness
    rehearsal and [E], and the kicad-free part of `check_consistency`. The merge run's
    handedness gate, with KiCad's export, is still the gate.

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
    class that holds 0.25 mm walls (`enclosure/brace/README.md`; `fit_rules.PRINT_WALL` since
    2026-11-14, when the ridge's two tapering ends were cut back to it). Re-open only if no such
    service will print it.
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
