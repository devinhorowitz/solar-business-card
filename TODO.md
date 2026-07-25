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

- [ ] **Physical button (BTN / PA5)** — _all three domains._ Reserved net only, unpopulated. If ever
  fitted: PCB placement (a "v2.2 surgery"), the firmware `PA5` stub becomes real, and the enclosure
  needs a pocket/hole plus front-fence clearance.

## Firmware — `firmware/`, `firmware/README.md`

- [ ] **[DOC+BENCH] LED sub-emission idle-bias — Hi-Z park LANDED, stow-rule + bench remain**
  _(2026-07-23; fw done — LED pads park as inputs between animations, bias drops to a clamp-limited
  ~1 V worst case and to zero below STO ≈ 3.6 V.)_ Remaining: (a) document the **SW2-OFF stow
  discipline** where SW2 is described (TINY does not help — same DC endpoint through R12); (b)
  bench-measure the real idle LED current; (c) only if the energy budget allows, consider a VOVCH
  re-strap one step down (E ∝ V², costly).

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
  duty. Every firmware duty-cycle / glow constant is provisional until it lands.

## PCB — `PCB/solar-glow-drh-v4_0.kicad_pcb` / `.kicad_sch`

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
- **Intentional / do-not-fix (so a future BOM/DRC pass doesn't re-flag them):** the R5/R6
  "VSENSE div" (and similar) value fields are deliberate house-style labels, not errors; the
  origin `NPTH_mech` footprint carries real non-plated mounting holes by design.
