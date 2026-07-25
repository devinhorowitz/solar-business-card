# Open items — SOLAR-GLOW DRH

A cross-domain tracker so nothing slips between the firmware, PCB, and enclosure
handoffs. This is an **index of what is left**, not a spec — canonical values
live in the source files it points to (see the "Where the truth lives" table in
`README.md`). Check items off in the GitHub UI as they land.

_Board freeze status (updated 2026-07-25): the 2026-07 audit round reopened the netlist —
pending copper: Q2/R18 placement + routing (cold-start-deadlock buffer) and the U7
footprint-identity swap. A PCB layout change still means a brace reprint, not a shell
re-machine._

## Cross-domain (link two+ teams — easiest to forget)

- [x] **[BOM] Longevity/stability parts pass** — _DONE 2026-07-23._ Full live audit vs DigiKey/Mouser:
  all parts Active; the two zero-stock lines were resolved and the ceramic/resistor set upgraded (same
  footprints + values, so no layout change). **Ceramics GRM→GRT (Murata AEC-Q200 automotive)** with
  voltage/tol bumps where free (100 nF 16→50 V; C4/C13/C27 10→16 V; C23 10→25 V; C26 6.3→10 V; C22/C25
  grade). **Resistors Yageo RC→AC (AEC-Q200)**; the **VSENSE divider R5/R6 → precision Yageo RE
  0.1%/50 ppm** (`RE0402BRE071ML`). **U6 → AEC-Q100 `TPS22918TDBVRQ1`** (pin-identical drop-in — fixes
  the zero-stock DBVR and upgrades grade). _(U6 later re-swapped 2026-07-23 to `TPS22917DBVT` — see
  the 6-pin dark-current audit item below.)_ ~~Note: R15 (2 M) has no 0.1%/50 ppm option in 0402, so the
  STO-sense divider (R15/R16) stays AEC-Q200 grade only.~~ _Superseded 2026-07-23: R15+R16 moved to 0603
  precision — see the rework item below._ Schematic MPNs + BOM + `Supplier P/N` fields all updated;
  schematic↔BOM cross-check clean.
- [x] **[SCH→PCB] Place + route the second upsize set: C22/C23 → 0603, C26/C27 → 0805, R5/R6 → 0603**
  — _DONE + VERIFIED 2026-07-23. All five refs fit — nothing reverted._ Board upload verified: C22/C23
  on stock `C_0603_1608Metric` (0.90×0.95 @ 1.55), C26/C27 on `C_0805_2012Metric` (1.00×1.45 @ 1.90),
  R5/R6 on `R_0603_1608Metric` (0.80×0.95 @ 1.65). Nets exact: **VSENSE** = {C5.1, R5.2, R6.1, U1.12}
  with R5.1→SRC, R6.2→GND; **STO_LDO** = {C22.1, FB1.2, U9.1, U9.3} (the FB1-island intent held through
  the land swap); **VINT** = {C26.1, R17.1, U8.8/10/20/23/24}; C23.1→VS, C27.1→STO; **STO_SNS**
  unchanged from the R15/R16 verification. DRC + ERC re-run post-route: 0 unconnected pads, and both
  reports byte-identical to pre-rework except timestamps — no new violations, schematic parity clean.
  _(Original scope note:_ Stability upsizing, all CT/MOQ-1 parts, live-verified:
  **C22** → `GRT188R71E105KE13D` (1 µF 25 V **X7R** 0603, stays GRT/AEC, `490-GRT188R71E105KE13DCT-ND`);
  **C23** → `GRM188Z71E225ME43D` (2.2 µF 25 V **X7R** 0603 — LDO-loop stability; the GRT 0603 2.2 µF is
  X5R-only, so dielectric won over grade); **C26 + C27** merge onto one 0805 line →
  `GRM21BR71A106KA73L` (10 µF 10 V **X7R** 0805, `490-10516-1-ND`) — note the AEC 0805 option (Cal-Chip
  `GMT21X7R106K16NT3`) is **reel-only MOQ 3000**, rejected for a one-of-one; **R5/R6** →
  `RT0603BRD071ML` (0.1%/**25 ppm** thin film, same MPN as R16 — three refs share one line). Heights:
  0603 ≈ 0.8 mm, 0805 ≈ 1.25 mm max — still under the 1.7 mm supercaps, but eyeball the brace/ferrite
  clearance over C26/C27 before committing the 0805s.)
- [x] **[SCH→PCB] Place + route the R15/R16 0603 lands (STO-sense divider precision rework)** —
  _DONE + VERIFIED 2026-07-23._ Board upload verified: both on stock `R_0603_1608Metric` (0.80×0.95
  pads @ 1.65 pitch); nets exact — `STO_SNS` = {C24.1, R15.2, R16.1, U1.11} and nothing else, R15.1 →
  STO, R16.2 → GND, 12 routed segments; DRC re-run clean (0 unconnected, no new violations vs
  pre-rework). Divider is now 0.1%/25 ppm end-to-end.
  _(2026-07-23; schematic + BOM DONE, board pending)._ R15 and R16 moved to
  `Resistor_SMD:R_0603_1608Metric` in the schematic with matched 0603 thin-film 0.1% / 25 ppm parts:
  **R15 = Vishay `MCT0603MD2004BP500`** (2 M, DK `541-MCT0603MD2004BP500CT-ND`, $0.22) and
  **R16 = Yageo `RT0603BRD071ML`** (1 M, DK `YAG4498CT-ND`, $0.10) — takes the STO_SNS divider ratio
  from ~1%/100 ppm to ~0.1%/25 ppm with matched tempco (STO gates the charge/sleep logic). R17 split to
  its own BOM line (stays 0402 `AC0402FR-071ML` — non-critical pull-up). Land audit 2026-07-23 confirmed
  the old `solarglow:C1` lands are true 0402-class (0.59×0.66 pads @ 1.02 pitch, ~6% over stock — the
  hand-solder upsizing never went a size class), so this IS a real land change: in KiCad, **Update PCB
  from Schematic**, place the two 0603s, re-route, re-DRC. Height ~0.55 mm vs 0.5 mm — enclosure-benign.
  Beware the metric-name trap when picking any footprint by hand: imperial 0603 = `R_0603_1608Metric`;
  anything named `*_0603Metric` is an 0201.
- [ ] **[SCH→PCB+ENCL] U7 FRAM repackage: SOP-8 → DFN (0.90 mm) — land ROUTED + VERIFIED; footprint
  identity swap + shell-pocket recheck remain** _(2026-07-23; schematic + BOM + board copper DONE —
  pads/nets/stubs electrically verified, 0 unconnected. Remaining: Change Footprint U7 →
  `solarglow:U7_DFN8` (`PCB/fp-lib-table` now registers the lib; reopen project first), optionally
  re-snap the 3 signal stub ends to the new pad centers, re-DRC; then the enclosure recheck.)_ U7 swapped to
  **`MB85RC512TYPN-GS-AWEWE1`** — the same MB85RC512TY die in the **DFN LCC-8P-M05** (5.0×6.0 mm,
  **0.90 mm MAX** vs 1.75 mm SOP-8; identical electricals/price, DK `865-MB85RC512TYPN-GS-AWEWE1CT-ND`,
  1500 stock). Board: the footprint is now **in the repo:
  `PCB/solarglow.pretty/U7_DFN8.kicad_mod`** — generated from the datasheet drawing (p.21) and
  numerically verified (100% terminal coverage at nominal AND both tolerance extremes; 0.35–0.45 mm
  hand-solder toe outside the body; no EP — the package has none; stock KiCad DFN numbering, pin 1
  top-left). No professional footprint exists for LCC-8P-M05: official KiCad lib + DigiKey KiCad lib
  searched (absent), SnapEDA/SamacSys unreachable, RAMXEED publishes no CAD. `PCB/fp-lib-table` (committed 2026-07-23) registers `solarglow` for the project — reopen the
  project, Change Footprint on U7, re-DRC. (Stubs already re-dragged; the hand-made pad array sits
  +0.15 mm off the anchor, so the library pads land 0.15 mm over — all stub ends stay on-pad.) Reflow/hot-air is the intended process; the long toe is the iron fallback. Enclosure:
  U7 was the tallest rear part and drove the backshell's dedicated 0.95 mm floor pocket — at 0.90 mm
  the cavity driver likely becomes the 0805s (~1.25 mm), so **the U7 pocket may be deletable**; recheck
  `enclosure/*cad.py` after the board lands. (Correction from the p.21 drawing: the terminals are
  recessed bottom contacts, NOT side-wettable — hence the extended-toe land.)
- [x] **[BOM] U6 → TPS22917DBVT (ultra-low-leakage drop-in) — the 6-pin silicon dark-current audit**
  — _DONE 2026-07-23 (sch+BOM; same land, no board change)._ Audit of the two SOT-23-6 parts: **U9
  (TPS7A0233, 25 nA) is already the class floor** (nearest stocked alternative is 25× worse) — kept;
  X2SON 1×1 miniaturization exists but adds hand-assembly pain for zero mechanical gain. **U6 was the
  board's largest standing silicon drain**: TPS22918 OFF-state I_SD = 0.5 µA typ / 3.5 µA MAX @3.3 V
  (repo datasheet §6.5), energized on VS 24/7 and off ~always. Swapped to **`TPS22917DBVT`** — TI's
  pin-identical ultra-low-leakage sibling, **I_SD 10 nA typ (~50×)**, ON-state 0.5 vs 8.3 µA, 125 °C,
  always-on reverse-current blocking; board config (CT float, QOD→VOUT, active-high ON) explicitly
  sanctioned (SLVSDW8B Table 6-1, saved to `datasheets/`). Trades away AEC-Q100 (no -Q1 exists) per
  the dark-current-over-grade call. **Never substitute `TPS22917L`** (active-LOW ON). DK
  `296-48370-1-ND` $1.14 (7.2k stock); Mouser `595-TPS22917DBVT` (13k).
- [x] **[BOM] U5 NFC chip audit — NT3H2211 confirmed best-fit, KEPT** — _DONE 2026-07-23 (no change)._
  Live compare vs the modern field: **NXP NTAG 5 link** (`NTP53321G0JHKZ`, $1.79, 1.3k DK) and
  **ST ST25DV04KC/64KC** ($0.60–1.01, thin/zero DK stock; the older `ST25DV04K` is flagged **NRND at
  Mouser**). Both are ISO 15693 / **Type 5** — swapping would (1) reduce tap universality vs Type 2
  (ISO 14443A), which older phones background-read far more reliably — the core dead-battery vCard tap
  is THE requirement; (2) force an antenna retune: the etched coil + FER1 system is designed around the
  NT3H2211's ~50 pF internal cap (C9's own description), and the Type-5 parts sit near ~24–29 pF
  (flagged: from vendor datasheets not re-verified today) → C9 would need populating + bench re-verify
  of range/Q; (3) add features the card never uses (AES, bigger EH, I²C master). **NT3H2111** (1 KB,
  $1.37) rejected: the design notes already earmark the 2211's ~1.7 KB spare. NT3H2211W0FHKH: Active,
  DK 15.1k / Mouser 15.8k, $1.50–1.56 — deeply stocked. **Watch item:** NXP steers new designs to
  NTAG 5, so NTAG I²C plus carries EOL risk on a years horizon — buy a spare or two with the order.
- [x] **[BOM] U1 MCU audit — grade bump executed: `AVR64DD28-I/STX` → `AVR64DD28-E/STX`** _(superseded same-day by the AVR-EA family swap below)_ — _DONE
  2026-07-23 (sch+BOM; same die/land/firmware)._ Family sweep confirmed the AVR-DD28 is still the right
  part (design-notes §5 rationale stands: only superset for the mixed-voltage I²C; the newer EA
  (12-bit ADC+PGA) and DU (USB) siblings are zero-stock at DK and would be real firmware ports for
  features the card doesn't need; 64 KB is the family max, ~2.4 KB used; /STX VQFN kept per the height
  rationale). The finding was **doc↔BOM drift**: the design-notes thermal audit ("Bumped to
  automotive/higher temp… taken") already committed to the **-E extended grade (−40…+125 °C)** alongside
  the FRAM-TY bump, but the BOM/schematic still carried -I (85 °C). Executed: **$1.24 (+$0.07)**, DK
  `150-AVR64DD28-E/STX-ND` (319, tube) / deep-stock tape alt `AVR64DD28T-E/STX` (DK 3.3k, Mouser 3.1k,
  same price). MCU no longer the first thing to give out at the supercap's 85 °C ceiling.
- [x] **[SCH+FW] U1 family swap `AVR64DD28` → `AVR64EA28-E/STX` — DONE (sch+BOM and firmware)**
  _(2026-07-23; board copper UNCHANGED by design — 27/28 pads identical, SJ1 → DNP.
  Firmware port landed: `-mmcu=avr64ea28` + AVR-Ex DFP, EA ADC model in `sense.c`
  (single-ended 12-bit; the diff+PGA+accumulation upgrade deliberately deferred to the
  bench era — tracked under Firmware below), EA temp-sensor math (1.024 V ref, `(raw+offset)×slope/4096`),
  `clocks_init` → `PDIV=DIV16` + `MCLKTIMEBASE`, floors re-derived for the 2.60 V BOD
  (`VS_GLOW_FLOOR_MV` 2750, `EE_WRITE_FLOOR_MV` 2850), fuses 0x4A/0x08/0xD1, README ported.
  Compile-verified warning-free: 3,960 B text / 23 B RAM.)_ Datasheet-verified decision
  (DS40002443A in `datasheets/`, note PRELIMINARY rev; pin diff from Microchip's own atdf files):
  **verified wins** — diff 12-bit ADC + PGA + 1024-sample accumulation (pairs with the 0.1%/25 ppm
  dividers), VREF ±2% vs DD ±4% (1.024/2.048 V, ≤85 °C), base power-down **0.08 µA vs 0.65 µA**,
  EEPROM **512 B vs 256 B**, cheaper + deeper stocked (DK `150-AVR64EA28-E/STX-ND` $1.23, 1.4k; tape
  6.6k more). **Copper-compatible**: 27/28 pads identical; pin 10 VDDIO2→PD0 → **SJ1 now DNP** (0R
  stays a spare if the DD is reinstated). TWI `ALT2` (PC2/PC3), TCA0 PORTA (WO0–3 = PA0–3), PD1/PD2
  AINP/AINN all confirmed. **Firmware-port scope:** `Makefile` `-mmcu=avr64ea28` + AVR-Ex DFP;
  `sense.c` rewrite for the EA ADC (different register model — use diff mode + accumulation);
  **fuses recomputed: the EA has NO 2.45 V BOD level — ladder is 1.90/2.60/4.30, use BODLEVEL2 =
  2.60 V** and re-derive the EEPROM-floor constants; drop `MVSYSCFG` (no MVIO); `board.h` pin-10
  comment + init PD0 input-disabled; re-verify AC0 mux index for PD2/AINP0; sleep numbers are
  typ-only in the preliminary DS — re-measure at bench. Bench re-verify all tunables after port.
- [ ] **[BOM] Buy the low-stock / long-lead parts early** _(2026-07-23)._ Not zero, but thin at audit:
  **supercaps** SC1–4 (~195–200), **FER1** ferrite (41), **U3** accel (731), **U1** MCU (608), **PV**
  cells (423). The supercaps + ferrite are the historical long-lead items — order with the first cut.
- [x] **[PCB] Route the new `STO_LDO` island (FB1 series filter)** _-- DONE 2026-07-21 (routed in
  KiCad, uploaded to `main` at 0b7cb13)._ FB1 is now a live series element: the board copper carries
  `STO_LDO` from FB1.2 to U9.1/U9.3 + C22.1, with FB1.1 left on raw STO. Verified against the uploaded
  board: `STO_LDO` = {C22.1, FB1.2, U9.1, U9.3} (exactly 4 pads), STO keeps FB1.1 + the rest, MID
  intact; the CI DRC reports **0 unconnected pads** with no new errors and clean schematic parity.
  Design intent realized: STO --FB1--> STO_LDO, C22 (1 uF) as the filtered LDO-input cap, isolating
  U9 from the AEM10300 DCDC switching ripple.
- [ ] **[PCB] Silk legend height on the STO_LDO upload** _(2026-07-21)._ The same upload added two
  B.Silk legends (`TINY MODE` @ (31.75, 50.95), `ENABLE` @ (27.5, 49.63)) at 0.5 mm, which trip the
  0.8 mm min-silk-text DRC rule (2 new `text_height` warnings, not errors). Decide: bump both to
  >=0.8 mm if they fit the switch cluster, else add to the README / kibot intentional-exceptions list
  so the next DRC review does not read them as a new find.
- [ ] **[PCB->KiCad] Sync SC1/SC3 footprint metadata to SS17** _(2026-07-22)._ PR #52 corrected the
  hybrid tank in the schematic + BOM + docs (SC1/SC3 = SS17 `3-153-440` 1.8 F, SC2/SC4 = WS17
  `3-153-438` 1.0 F), but the board `.kicad_pcb` SC1/SC3 footprint Value/MPN still read WS17. In KiCad,
  update SC1/SC3 (or pull the schematic), then **Update PCB from Schematic** and re-upload. Metadata
  only -- nets and copper are unaffected.
- [x] **[BOM] Fill the SS17 `3-153-440` price (TBC) via DigiKey** — _DONE 2026-07-22._ Both gates
  (egress to `api.digikey.com`/`api.mouser.com`, and the three API creds) came up green in a fresh
  container. DigiKey OAuth + Product Information V4 returned live data: **SS17 `3-153-440` = $17.16 @ 1**
  (DK `486-3-153-440-ND`, 200 in stock) and **WS17 `3-153-438` = $16.69 @ 1** (DK `486-3-153-438-ND`,
  up from $15.48). Written into `PCB/solar-glow-drh-v4_0-BOM.xlsx` (SC1/SC3 filled, SC2/SC4 refreshed;
  subtotal later superseded by the full-BOM sourcing pass below). Data pulled directly through the
  proxy CA; no MCP wrapper required. See `mcp-setup.md` → Status.
- [x] **[BOM] Re-source three v4-new caps flagged by the live DigiKey pass** — _DONE 2026-07-22._
  The whole master BOM was re-verified live against DigiKey: format-derived DK P/Ns replaced with the
  real ones (e.g. R1–R4 150 Ω is `311-150LRCT-ND`, **not** `RC0402FR-07150RL-ND`), prices refreshed
  (PV1/PV2 $6.98→$7.61, U3 $7.50→$7.80, U5 $1.38→$1.56, SJ1 $0.05→$0.10), and the C5 DK P/N corrected
  off the stale 10 nF part onto the 100 nF `490-3261-1-ND`. Three v4 caps were **not orderable at
  DigiKey as specified** and have been re-sourced — MPN changed in **both** the schematic
  (`(property "MPN" …)`, the fab-BOM source) and the master xlsx:
  - **C22** (LDO input on the STO island ~5.5 V): `GRM155R61A105KE15D` (1 µF 10 V) was obsolete + the
    whole GRM155 1 µF 10 V family EOL → **`GRM155R61E105MA12D`** (1 µF **25 V** X5R 0402,
    `490-10018-1-ND`, $0.10). 25 V picked for DC-bias headroom on the 5.5 V node.
  - **C23** (LDO output on VS 3.3 V): `GRM155R61A225KE11D` (no DK results) →
    **`GRM155R61A225KE01J`** (2.2 µF 10 V X5R 0402, `490-GRM155R61A225KE01JCT-ND`, $0.10).
  - **C26** (VINT buffer 6.3 V): `GRM155R60J106ME44D` (discontinued) →
    **`GRM155R60J106ME05D`** (10 µF 6.3 V X5R 0402, `490-GRM155R60J106ME05DCT-ND`, $0.10).
  Also re-sourced **C4/C13/C27** (`GRM188R61A106KE69D`, 10 µF 10 V 0603): Active but DigiKey stocks/prices
  no variation (order-only) → **`GRM188R61A106ME69D`** (same 10 µF/10 V/X5R/0603, tol K→M, DK
  `490-10475-1-ND`, $0.12, 578k in stock). kibot CI regenerates
  `Generated/fabdocs/solar-glow-drh-v4_0-bom.csv` from the updated schematic. Only ordered line still
  unpriced: **U8/AEM10300** (Mouser-pending).
- [x] **[BOM] Fill the U8 `10AEM10300C0000` (AEM10300) price via Mouser** — _DONE 2026-07-22._ U8 is
  Mouser-only (DigiKey returns 0 results). The Mouser Search API key came live; queried the part and
  filled U8 (`R35`): Mouser **`120-AEM10300-QFN`**, **553 in stock**, 16-day lead, **$3.77 @ 1**
  (breaks 10@$2.81, 100@$2.31, 1000@$1.85). With this, **every ordered on-board line is priced**
  (indicative subtotal → $138.67). Detail in `mcp-setup.md`.
- [x] **VIN-at-clamp / SUN_THRESHOLD** — _PCB → firmware. DONE 2026-07-10._ Derived
  VIN **>= 3.60 V** as the strong-sun trigger (above the held VS ~3.50 V so there is
  the SRC (merged-panel) node lifted well above its indoor level (VSENSE now divides SRC), below panel Voc 4.15 V; full derivation at
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

- [ ] **[FW+BOM DONE -> SCH+PCB] EN_STO_CH cold-start deadlock fix: NFET buffer CHOSEN (Q2 BSS138LT1G
  + R18 1M gate pulldown) — SCH fully wired (direct edit); ONLY the PCB copper remains** _(decision 2026-07-23: option (ii).
  FW inverted for the buffer (PA4 push-pull, HIGH = disable; init + FD ISR reworked, build clean
  4,234 B); BOM carries Q2 (BSS138LT1G — 2N7002 was zero-stock — DK BSS138LT1GOSCT-ND \$0.34, 204.9k)
  and R18 on the shared 1M line. SCH: Q2 + R18 symbols injected 2026-07-23 (parked in free space at (934.7, 372.1)/(934.7, 391.2), right of the EN_STO_CH area -- drag into place while wiring). SCH wiring DONE 2026-07-25 (wires + global labels drawn; the U1-side EN_STO_CH label renamed CHG_DIS_G; temp ERC filter removed so CI verifies for real). Net map now: CHG_DIS_G = {U1.PA4, Q2.G, R18.1},
  drain -> EN_STO_CH (keep the label on the U8/R17 side), source -> GND, R18 gate-to-GND. PLACEMENT:
  at the old PA4/net junction near U8/R17 — the 1M-class drain net stays short, the driven gate line
  may run long; SOT-23 joins the back-side brace height map (~1.1 mm, same class as U9).)_ ORIGINAL:
  _(2026-07-23 second-sift audit; full analysis in the design-notes second-sift addendum)._ A fully
  dead card's PA4 clamp pins the AEM10300's charge-enable at ~0.6 V (the TPS7A0233P's active
  discharge holds VS at GND below UVLO, so there is no float-up escape); if that decodes LOW the card
  is an unrecoverable no-charge brick after its first deep discharge — and deep discharge is a normal
  state. Invisible on a UPDI-powered bench. **Option (i) RECOMMENDED: sever PA4 from the net** (EN
  floats on internal pull-up + R17 = always-enabled; PA4 becomes a pulled-up spare; loses only the
  speculative NFC-read charge-quieting). Option (ii): 2N7002-class low-side buffer (gate from PA4 +
  1M pull-DOWN, HIGH = disable) — keeps the feature with the correct dead-MCU-safe polarity, +2
  parts. Firmware follows the choice (drop or invert the FD-ISR EN_STO_CH toggling + gpio_init).
- [ ] **[FW DONE -> DOC+BENCH] LED sub-emission idle bias — Hi-Z park LANDED, stow-rule + bench remain**
  _(2026-07-23; fw executed same day: LED pads now park as inputs (input buffers off, INVEN kept)
  between animations — led_park/led_unpark bracket led_breathe/led_sweep on every path incl. the NFC
  aborts; bias drops to clamp-limited ~1 V worst-case, zero below STO~3.6 V. Remaining: (b) doc the
  SW2-OFF stow discipline where SW2 is described; (c) bench-measure real idle LED current; (d) VOVCH
  re-strap only with energy data.)_ ORIGINAL: OSRAM forbids continuous sub-emission forward bias (migration risk);
  idle card holds 4 LEDs at up to 1.35 V (STO 4.65 vs pads parked 3.3). (a) firmware: Hi-Z the LED
  pads between animations (DIR-gate around glows; INVEN stays for active PWM) — cuts bias to
  clamp-limited ~1.0 V, zero below STO≈3.6; (b) docs: SW2 OFF is the stow-the-card discipline (TINY
  does not help); (c) bench: measure real idle LED current; (d) only if energy budget allows,
  consider a VOVCH re-strap one step down (E ~ V², costly). Anode-switch topology rejected (dead-MCU
  gate fail-state inverts).
- [ ] **[BENCH RULES] Cross-domain bench-procedure set** _(2026-07-23 second-sift)._ (1) JP1 SCL/SDA:
  external I2C adapters only with the card powered and the adapter referenced to VS — the ADXL367
  (and now the FRAM) digital abs-max is zero-headroom "-0.3 to VDDIO". (2) STO injection: SW2 OFF
  first (lit injection >≈2.5 V forward-drives the LEDs into the dead MCU's clamps, ~16 mA/pin).
  (3) Dark bench-charging of STO: pre-balance the 2S midpoint or charge under light (BAL active).
  (4) UPDI into a flat card: power the card via the programmer (README rule; ~0.5 mA PF7 clamp
  current if ignored — bounded but pointless).

- [ ] **[SCH+FW DONE -> PCB] FRAM back-power fix (option A) ADOPTED -- U7 re-railed to VS + Sleep-parked;
  board copper re-net pending** _(2026-07-23 deep-dive + same-day execution. SCH: the two VNFC global
  labels at U7.VDD and C28.1 renamed to VS (tag side untouched). FW: fram.c rebuilt on a wake/sleep
  model (fram_wake / fram_sleep, NACK-tolerant + bounded), main.c parks U7 unconditionally at boot --
  power-critical, it cold-boots into 10 uA standby -- and defensively re-parks each poll tick
  (`FRAM_RESLEEP_EVERY_POLL`, flip to 0 if the bench proves address-selective wake). Build clean at
  4,154 B. REMAINING: (1) user re-routes U7 pad 8 + C28.1 copper from VNFC to VS ("Update PCB from
  Schematic" will flag the two pads), re-DRC; (2) bench: verify IZZ, wake selectivity, VS idle current.
  Original analysis follows.)_ Research flipped the
  working assumption to **"the VDD clamp is real until proven otherwise"** (MB85RC lacks the fail-safe
  SCL/SDA exemption its Ramtron-lineage competitors print; industry consensus + a 0.88 mA field
  measurement of the same architecture). The current netlist (U7 on gated VNFC, R10/R11 on VS) likely
  stands **~0.5-1.1 mA** -- treat as a design defect, not a curiosity. **Recommended fix (option A):
  re-net U7 pad 8 + C28.1 from VNFC to VS and park the FRAM in its I2C Sleep mode (IZZ 0.20 uA typ /
  10 uA max at 125 degC; enter S+F8h, addr, S+86h; ~450 us wake)** -- kills the abs-max exposure by
  construction, is power-ramp-compliant (same-rail pull-ups track VDD; tr/tf are minimums), and keeps
  the tag's proven gate untouched. Firmware half: fram.c drops NFC_EN coupling, sleeps U7 at boot +
  re-sleeps after every bus use (wake-address selectivity is ambiguous in the datasheet -- defensive
  re-sleep covers it). Alternatives ranked in the addendum (switched-pullup GPIO / TCA4311A isolator /
  ST M24M01-A125 fallback part). _The earlier "bus-park low" idea is retracted -- driving the bus low
  against VS pull-ups burns ~1.4 mA._ Bench then **verifies** (IZZ, wake behavior, VS idle current)
  instead of gating. The NT3H2211 remains unexposed (no input-voltage limit; VCC-off is its design mode).
- [ ] **[BENCH] Read + log the EA silicon revision (B1 vs B2)** _(2026-07-23)._ Errata 2.2.1-2.2.3
  (DS80001048C, now in `datasheets/`) are Rev. B1-only; the firmware carries the 2.2.3 SLPCTRL
  NOP-guard workaround either way (one cycle on B2) and `EE_WRITE_FLOOR_MV` covers 2.2.1. Read
  SYSCFG.REVID over UPDI at first connect so we know which part we actually got.

- [ ] **Program fuses on hardware** (EA values, computed from DS40002443A -- verify before burning):
  **`bodcfg 0x4A`** = 2.60 V sampled BOD (BODLEVEL2; the EA has no 2.45 V level). **NOT `0x0A`** --
  that is `LVL=0x0` = BODLEVEL0 = 1.75 V, chip-erase-only, so `0x0A` ships the card with the BOD
  *off*. **`osccfg 0x08`** = OSCHF base 16 MHz, so `clocks_init`'s ÷16 lands on exactly 1 MHz
  (pre-fuse it runs a harmless 1.25 MHz). **`syscfg0 0xD1`** = factory `0xD0` + EESAVE (keeps the
  black box across a reflash; UPDI stays enabled). **`syscfg1`: leave at factory default** (the EA
  has no MVSYSCFG). Fuses are not in the flash image; `make fuses` prints the commands. The 2.60 V
  BOD is also the cold-start guard (below) and the hardware backstop to the software EEPROM-write
  floor (`EE_WRITE_FLOOR_MV`, 2.85 V).
- [ ] **Bench-verify a dead-battery cold-start.** From supercaps at 0 V under *dim*
  indoor light (worst harvest), confirm the rail climbs cleanly past the 2.60 V BOD
  release without stalling -- i.e. the AVR's reset-state draw on a very slow (mV/s)
  ramp stays below the harvest current so it never sticks at an intermediate voltage.
  (Raised by Gemini as "cold-start latch-up"; it's a brown-out *stall*, not latch-up.
  Program the BOD fuse first -- it's the guard.)
- [ ] **Bench validation** (bare-card starting points, re-tune enclosed): tap
  axis (Z), tap/activity thresholds, INT edge/polarity, LED `INVEN` polarity.
- [ ] **[EA upgrade, bench-era] Use the EA ADC's differential mode + PGA + burst
  accumulation for the rail/light reads** _(2026-07-23, deferred from the EA port)._
  The port keeps the DD-shaped single-ended 12-bit reads so behaviour is 1:1 and every
  constant carries over; the EA silicon can do better (diff mode against GND kills
  common-mode offset on the ~500 kΩ dividers, PGA relaxes the source-impedance math,
  ×N accumulation averages divider noise for free — it pairs with the 0.1 %/25 ppm
  thin-film dividers already on the board). Do it after the energy-budget measurement,
  with the meter attached: each knob changes conversion time and therefore poll energy.
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

- [ ] ~~Q1 thermal copper~~ - DROP (v4): Q1 (v3 BCP5316 shunt transistor) was deleted in the AEM10300 managed-solar redesign; there is no shunt device to heatsink. Solid pad3→pour
  (`zone_connect 1`→`2`) + a GND thermal-via cluster **adjacent to** pad3 (not
  in-pad, to avoid solder wicking) + a top-side GND flood over Q1 biased east
  into the x46.4–50.3 strip (clear of the PV2 cell), inside 9.7 mm of the coil
  keepout and clear of the x50.8 edge. Layout mockup:
  `docs/solar-glow-drh-q1-thermal-via-mockup.svg`. Still open (Q1 region has
  zero vias; pad3 is still thermal-relief).
- [ ] **PCBWay orders** — confirm both replies sent (`W567099ASH69` bare fab,
  `T-H70W567099A` PCBA); get the LED package dimension answer (1.25 vs 1.9 mm)
  and the merged PCB+PCBA total; ensure the PO
  uses the confirmed C11/C13 MPNs.
- [ ] **BOM completeness - recount the machine-place BOM against the v4 net** - D10/D11 (v3 comparator-supply OR diodes) were removed with the U4 comparator; only LEDs D2-D5 remain as diodes, so the earlier '42' count is stale. Regenerate the counts and the -BOM-assembly.xlsx master against the v4 schematic. _(audit find,
  2026-07-11)._ `PCB/README.md` order table + counts and root `README.md` were
  previously "fixed to 42" off the pre-redesign parts list, so they likely carry the
  same stale count and must be re-verified against the recomputed v4 count; the
  `-BOM-assembly.xlsx` master then needs regenerating to match (binary; owner: Devin).
- [ ] **DRC/ERC prose vs the committed reports** _(audit find)._ The board is DRC/ERC
  **clean** (0 unexcluded errors). But `PCB/README.md` + `solar-glow-drh-design-notes.md`
  describe "~61 marginal-band warnings" present in neither committed report (GUI: 5
  violations / 3 excluded; CI: 6 clearance + 62 MPN-parity). Decide whether the two-tier
  `.kicad_dru` rules should be loaded in the run, then align the prose. Minor: the ERC
  `isolated_pin_label` (PC0/PC1) + `endpoint_off_grid` (JP1/TP1) aren't catalogued.
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
- [ ] **[geometry] Floor relief re-key — now likely a relief DELETE (U7 went DFN)** - U2 (v3 ALD910025 balancer) is gone, and U7 (MB85RC512TY FRAM, at (28.1, 37.3) B.Cu) is the **0.90 mm DFN** since the 2026-07-23 repackage, not the 1.75 mm SOIC-8 the pocket was sized for — at 0.90 mm it needs no relief, same as the ~0.9 mm U8 QFN. Re-derive the tallest rear part (U9 SOT-23 / the 0805 caps) and most likely delete the pocket.
  `…-backshell-…-cad.py` still carries `U2_POS = (30.10, 37.64)` for the deleted part; re-key it to
  U7's (28.1, 37.3) (rename `U2_POS` -> `U7_POS`), then regen the STEP/STL and the derived
  drawing/README note-7 copies. PCB is frozen truth. _(audit find)._
- [ ] **[geometry] Repoint the brace generator to the v4 board + fill `part_height` for the v4 parts** _(audit find)._ `…-diffuser-brace-cad.py` line 54 hardcodes a v3_0 path (`PCB = ".../solar-glow-drh-v3_0.kicad_pcb"`, an absolute path that also does not resolve here), so its pocket map is still v3. `part_height()` has entries only for U2/U6/U1/U3/U5 -- the v4 additions fall through to the 0.60 default, too shallow for the tall ones (U9 LDO SOT-23 ~1.45, L2 2520 ~1.0, the 0805 caps C26/C27 ~1.25, and the 0603 bulk caps C4/C13/C25 ~0.9; U7 is the 0.90 mm DFN since 2026-07-23 — no longer tall). Repoint to the v4 board, drop the U2 entry, add U7/U9/L2 + a 0603-cap height, then regen the brace STEP/STL and confirm no pocket collisions / thin-wall merges broke.
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
- Supercap footprints are a **hybrid**: SC1/SC3 = SS17 land (3-153-440, 39 mm), SC2/SC4 = WS17
  land (3-153-438, 28.5 mm); flat under-body pads, asymmetric widths = polarity key. The old REV-J diagonal-pad land is WRONG -- never reuse.
- Ti-6Al-4V (Grade 5); grounded M2 bosses tie the body to GND.
- **NFC contact is offline-first.** The full vCard is **embedded** in the tag (`text/vcard`
  NDEF, `nfc.c`), read RF-powered by the phone with the card's supercap flat and **no
  reception** (the dead-signal courtroom case). A URL / App Clip is only ever an OPTIONAL
  rich-content extra -- **never** a dependency for the contact import. Do not swap the embedded
  vCard for a URL-only record.
