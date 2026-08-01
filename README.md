# SOLAR-GLOW · DRH

A business card that runs on light. An AVR microcontroller breathes four amber LEDs
*through* the board — a monogram cut into the front copper that glows when the rear LEDs
backlight it through the bare fiberglass — while a pair of indoor solar cells trickle-charge
a supercapacitor bank that holds the charge.

![SOLAR-GLOW · DRH — the assembled card turned over: titanium back-shell, resin brace, PCB, 8× M2 brass](https://raw.githubusercontent.com/devinhorowitz/solar-business-card/main/enclosure/solar-glow-drh-assembly-spin.gif)

<sub>The assembled card — Ti back-shell, resin diffuser brace, 0.60 mm PCB and eight M2 brass screws.
Not an artist's impression: every surface is the committed STEP-derived STL, the outline and the
eight mount positions come straight out of the `.kicad_pcb`, the Z stack is the one
`enclosure/fit_rules.py` enforces, and the show face is the **raytraced board itself** — the
monogram window, the ENIG, the contactless mark and the contact line are the real artwork, not a stand-in.
Re-route the front and this picture follows. Stills, the exploded and reverse views, and the full
respin are in [`enclosure/README.md`](enclosure/README.md).</sub>

![SOLAR-GLOW · DRH — front and back, gold ENIG on black soldermask](https://raw.githubusercontent.com/devinhorowitz/solar-business-card/main/Generated/docs/solar-glow-drh-v4_0-top.png)

> **Status: v4.0 (managed-solar redesign) in progress** -- working files are `v4_0`, currently the v3.0
> baseline being reworked to the AEM10300 active-harvest architecture (see the design-notes v4 addendum +
> `v4-aem10300-prewiring.md`). **v3.0 -- fully routed, audit-clean, not yet fabbed -- is frozen as the final
> unmanaged-solar revision.**
> Two-layer, 0.6 mm FR4, bound for PCBWay; the 4-layer **v2.3** is the fallback design, kept in git history (not the working tree).
> The one thing standing between here and a build is the **energy budget** — harvest vs. draw under
> real indoor light has never been measured. See *“The open question.”*

### Current revision — the one canonical summary

| What | Current | Notes / fallback |
|---|---|---|
| **PCB** | **v4.0 - 2-layer** (F / B) | GND = full-board B.Cu pour; VS = routed B mesh. **v2.3 (4-layer: F / In1 GND / In2 VS / B) is the fallback design, in git history.** v2.1 was 6-layer (history). |
| Board | 50.80 × 88.90 mm, r3.0 corners, **0.60 mm** FR4, ENIG, matte-black mask | 0.6 mm — committed in the board stackup (frees the shell floor to 1.0 mm) |
| Mounting holes | **8× M2, GND** -- 4 corner (MH1-4) at **(3.0, 3.0) / (47.8, 3.0) / (3.0, 85.9) / (47.8, 85.9)** (pitch **44.80 × 82.90 mm**) + 4 panel-corner (MP1-4) at **(3.0, 28.5) / (47.8, 28.5) / (3.0, 60.4) / (47.8, 60.4)** | corners concentric with the r3.0 fillets; MP1-4 at the E/W mid-edges for the shell clamp |
| **Enclosure** | **Ti back-shell** - 1.00 floor, 1.80 cavity, overall **3.55 mm**; center support via the single-piece resin diffuser brace. **Respun 2026-07-29 against the real board** — the brace had 593 mm³ of resin inside three supercaps and the shell lip sat on 4.17 mm² of live pad; both geometries are now computed from the board and gated by `check_consistency` **[8]**. | 8-hole pattern (4 corner + 4 panel-corner); see [`enclosure/README.md`](enclosure/README.md) |
| BOM | **v4_0 master** - fully live-priced (2026-07-23 sourcing pass, ≈ $140); most passives 0402 with the precision/bulk set on **0603** (C4/C13/C25/C22/C23/R5/R6/R15/R16) and **0805** (C26/C27); **SJ1 removed outright 2026-07-30** (lineage row only); Q2 + R18 added by the cold-start-deadlock fix | master is `BOM/solar-glow-drh-v4_0-BOM.xlsx`; placed set in `-BOM-assembly.xlsx`; live availability table in `BOM/README.md` (`python3 BOM/check_stock.py`) |
| Firmware | AVR64EA28 C, register-verified **and compile-verified in CI**; not yet on hardware | LED pin map re-mapped in v3.0 (see `firmware/README.md`) |

### Where the truth lives — how these docs stay from drifting

Each fact has exactly one home; everything else points at it rather than restating it.

| Domain | Source of truth |
|---|---|
| Board copper / geometry / holes | `PCB/solar-glow-drh-v4_0.kicad_pcb` + `.kicad_sch` |
| Back-shell medallion (ring text, monogram, serial №) | `enclosure/medallion.py` — the shell generator and its drawing both import it; bump `SERIAL` there and CI regenerates the STEP/STL/drawing (a kibot trigger since 2026-07-31) |
| Fabrication panel (PCBWay) | `scripts/panelize.py` — derived from the board on every CI run into `Generated/panel/`; never hand-maintained |
| README renders | `scripts/render.py` — raytraced from the board/panel on every CI run into `Generated/docs/`; add a target there rather than committing a hand-made image |
| Enclosure **fit rules** | `enclosure/fit_rules.py` — one home for the brace footprint, the lip bands and the boss scallops; both generators import it and check [8] asserts it |
| Enclosure part positions | `enclosure/board_parts.py` — true body ∪ pads, read from the committed `.kicad_pcb` |
| Enclosure geometry | `enclosure/solar-glow-drh-v3_0-backshell-0p6b-brace-cad.py` (prints the Z-stack; regenerates the STEP) |
| Assembly views | `enclosure/assembly_render.py` — regenerated from the STLs + the board; not hand-made |
| Firmware pin map + knobs | `firmware/board.h` (+ `firmware/README.md`; both match the schematic) |
| BOM | `BOM/solar-glow-drh-v4_0-BOM.xlsx` (v4.0 master -- every ordered line live-priced, 2026-07-23 sourcing pass; see `PCB/README.md` Step 4). `BOM/README.md` is **derived**: a live stock/lifecycle table regenerated by `BOM/check_stock.py` (needs distributor API keys, so manual-apply like the mask art) |
| Design *reasoning* / lineage | `solar-glow-drh-design-notes.md` |
| Open work / cross-domain to-dos | `TODO.md` (an index of what's left; each item points back at the files above) |

When a number here disagrees with a source-of-truth file, the source file wins and this table is the
thing to correct. The `solar-glow-drh-v2-*` docs are v2-era history (banner-marked at the top of
each); read them for lineage, not for current values.

---

## What it is

A business-card-sized PCB — **50.8 × 88.9 mm, 0.6 mm FR4, ENIG, rounded corners** — that:

- **Harvests** indoor light with **two** ANYSOLAR solar cells merged into a single solar node (SRC) that feeds the AEM10300 harvester (U8),
  which runs the MPPT and handles reverse-blocking so neither panel back-feeds the
  other - the v3 per-panel blocking diodes are removed.
- **Stores** energy in **four** series-parallel supercapacitors -- a **hybrid tank** (two larger
  SS17 cells + two WS17), **~1.3 F at 5.5 V, ≈ 21 J** -- with the AEM10300 harvester (U8) balancing
  the series midpoint (MID), which is what lets the two cell sizes share the series stack safely; the safe 3.3 V VS rail
  is set by the U9 TPS7A0233 LDO, not a shunt clamp.
- **Glows** by back-lighting a **“DRH” monogram** that’s cut into the front copper: a gold
  ENIG field with the three letters opened to bare FR4. Four reverse-mounted amber LEDs on the
  back fire up through the translucent substrate, so the letters themselves light up — and PWM
  on the LED drives makes them breathe.
- **Wakes** to a **tap.** A 3-axis accelerometer feels you pick the card up (or the enclosure
  being tapped) and interrupts the MCU out of sleep — no button, no moving parts.

The front face stays naked — solar cells and the glowing monogram exposed — and the dense work
all lives on the back, ready for an optional machined-metal back-shell.

> **A note on lineage:** earlier revisions (REV J and before) were *generated from Python* —
> geometry and Gerbers emitted by script, no layout tool in the loop. **v2.1 is a full KiCad
> design** (schematic + board), continued through v4.0. The old generators are kept only as
> history; the KiCad files are the source of truth.

---

## How it works

| Block | Part | Notes |
|---|---|---|
| MCU | **AVR64EA28** (28-VQFN) | TCA0 hardware PWM, I²C to the accel, charge/sleep logic; 2026-07 family swap from the AVR64DD28 (12-bit diff ADC + PGA; no MVIO on the EA, so the DD-era SJ1 strap was deleted outright, 2026-07-30) |
| Solar | **2× ANYSOLAR SM141K06TF** | monocrystalline indoor cells (Voc 4.15 V), in parallel — two panels ≈ 2× the harvest |
| Harvest PMIC | **e-peas AEM10300** (U8, QFN-28 4×4) | MPPT buck-boost that merges both panels at SRC and charges the supercap tank (STO) - replaces the v3 per-panel blocking diodes |
| Storage | **2× SCHURTER 3-153-440** (SS17, 1.8 F) + **2× 3-153-438** (WS17, 1.0 F) | hybrid tank, 2.75 V/cell, wired 2S2P → **~1.3 F @ 5.5 V ≈ 21 J** on one balanced node (AEM holds MID so the smaller WS pair can't over-volt) |
| Midpoint balance | **AEM10300 (U8) BAL** | the harvester balances the 2S supercap midpoint (MID net) - replaces the v3 ALD910025 dual SAB MOSFET |
| Rail regulator | **TI TPS7A0233** (U9, SOT-23-5) | nanopower LDO (~25 nA Iq) regulates STO down to the fixed **3.3 V VS rail** the MCU + accel run on - replaces the v3 TLV3011 + PNP shunt clamp |
| LEDs | **4× ams OSRAM LA P47F** (amber) | reverse-mount; glow through the FR4 window, **150 Ω** ballast each |
| LED master switch | **SW2** (solder-bridge) + **R12** | OFF / ON / TINY — TINY routes the LEDs through a 220 Ω ballast for a dim, long-runtime glow |
| Motion | **ADI ADXL367** | 3-axis accel; tap / double-tap wakes the MCU via interrupts; 0.89 µA (swapped from LIS2DH12 on backorder) |
| Light sense | **R5 / R6 divider → PD2** | SRC ÷ 2 off the *merged solar input* (not the rail) - tracks light directly; doubles as wake-on-light |
| NFC | **NXP NT3H2211** (NTAG I²C plus 2K) | present from v3.0 - a contact **vCard** a phone taps to save; field-detect (FD, PA6) also wakes the glow - I²C `0x55`, shares the accel's bus; VCC **power-gated by `U6`** (`NFC_EN`/PA7, off by default); the **U7 MB85RC512TY FRAM** (I²C 0x50, C28) rides always-on VS parked in its 0.2 µA I²C Sleep mode (the 2026-07-23 back-power fix - see design notes) |

**Breakouts and features:** a **TC2030** Tag-Connect pad (`TC1`) for hands-free UPDI
programming, a backup UPDI header (`J1`), a **5-pad bench strip** on the back east edge
(`TP1` SRC + `JP1` GND/STO/SCL/SDA - bare SMD probe pads for bench power injection and an I²C
tap; pinout in `solar-glow-drh-v2-hardware.md`), per-LED disable jumpers (`SB1–4`), and **eight grounded M2 mounting holes** (four corners + four panel-corner at the E/W mid-edges). (The DD-era
VDDIO2 tie jumper `SJ1` is gone — DNP'd at the AVR-EA swap, deleted from the schematic and board outright on 2026-07-30. The v2-era
`JP1`/`JP2` 2.54 mm breakout headers are gone; the `JP1` name is reused for the strip.)

Full part numbers, pricing, and per-part datasheet links are in
**`BOM/solar-glow-drh-v4_0-BOM.xlsx`** - the master BOM (v4.0): every orderable line now carries a
live-verified distributor P/N and price (2026-07-23 sweep, subtotal ≈ $139.76). **U6 is the
TPS22917DBVT** (ultra-low-leakage dark-current swap) with **R14 (1 M `NFC_EN` pulldown)**; the stale
JP1/JP2 rows are dropped (the `JP1` designator is reused in v3.0 for the bench pad strip - bare pads,
no BOM part). Passives are X7R / AEC-Q200 / precision grade: most on **0402** lands, with the
stability upsizes on 0603 (C22/C23, R5/R6, R15/R16, plus the bulk caps C4/C13/C25) and 0805
(C26/C27, and C9's NFC tank trim). SJ1 is culled. Lineage: v2.2 added the NFC parts (U5 / C8 / C9 / R13); the `v2 2` and older
BOM files stay in the repo as history.

---

## The board

- **Two copper layers** on 0.6 mm FR4 (v3.0): **F.Cu** signal/parts and **B.Cu**. **GND is a
  full-board B.Cu pour** (`GND_B` zone) with stitch straps, and **VS is a routed mesh on B** — the
  4→2-layer conversion of v2.3, whose internal GND/VS *planes* moved onto the back copper. The
  4-layer **v2.3** (F · In1 GND · In2 VS · B) is the fallback (recoverable from git history) if the
  back-side trace texture showing faintly on the naked front reads wrong.
- **The glow window is a keepout on every layer.** The monogram cutout and the four LED
  light-paths are voided through both layers so nothing — copper pour, trace, or via —
  shadows the light between the rear LEDs and the front face. The rear soldermask is left
  *open* over the window on purpose: bare ENIG reflects the LEDs’ light forward instead of
  absorbing it.
- **Rail discipline.** The supercap stack can sit near 5.5 V, but the accelerometer tops out at
  3.6 V - so the **U9 TPS7A0233 LDO** regulates the supercap tank (STO) down to the fixed
  **3.3 V VS rail**, directly bounding what the accelerometer sees. Its ~25 nA quiescent
  draw is negligible against the other always-on loads, and it regulates VS itself rather
  than the solar input. (v3's TLV3011 + PNP shunt clamp and the per-panel blocking diodes
  are gone - the AEM10300 now owns the harvest path.)
- **Power planes** carry the supercap charge/discharge currents; the four cells eat the better
  part of the back, so the layout is geometry-bound and the planes earn their layers.

---

## The open question — read this before building a batch

The board is well-verified; the **energy budget is not.** A solar cell’s headline rating is a
full-sun number, and indoor light delivers a small fraction of it, while four breathing LEDs
average several milliamps. The two-panel harvest and the ~21 J tank are sized to **harvest
slowly and glow in bursts** — but that bet has never been put on a meter.

What changed the math since the early notes: the LED string is fed from the **STO supercap tank** (through the
SW2 anode switch), which the AEM10300 holds at up to **4.65 V** (VOVCH), and the ballasts are **150 Ω** -- so each
LED peaks near **~16 mA** at a full tank ((4.65 V - amber Vf ≈ 2.25 V)/150 Ω, the figure `firmware/README.md`
quotes), sagging toward zero as STO discharges. (VS, the regulated 3.3 V LDO output, powers the MCU and accel,
not the LEDs.) Four on at once is a real load against an indoor harvest measured in fractions of a milliamp.

**First move when boards arrive:** put the cells under your actual target lighting and measure
**harvest current against LED draw** before you populate a full stack. That single number sizes
the duty cycle, the feature set, and whether the always-on accelerometer earns its microamps.

---

## Repository layout

```
solar-business-card/
├── README.md                       # this file (canonical current-revision summary)
├── PCB/                            # KiCad projects
│   ├── solar-glow-drh-v4_0.kicad_pcb   # the board: v4.0 managed-solar rework (AEM10300), 2-layer (source of truth)
│   ├── solar-glow-drh-v4_0.kicad_sch   # schematic: synced to the v4.0 board netlist
│   └── README.md                       # order & build guide
├── BOM/                            # bill of materials (moved from PCB/ 2026-08-01)
│   ├── solar-glow-drh-v4_0-BOM.xlsx    # v4.0 master (mostly 0402; 0603 and 0805 sets per the table above)
│   ├── solar-glow-drh-v4_0-BOM-assembly.xlsx  # placed-parts BOM for PCBA (the machine-placed 47; rebuilt 2026-07-30)
│   ├── check_stock.py                  # live DigiKey/Mouser availability check -> README.md
│   └── README.md                       # DERIVED: stock/lifecycle/price table with red-X dead lines (regenerate, don't edit)
├── solar-glow-drh-design-notes.md  # design rationale, energy model, lineage (incl. the v3.0 chapter) — the one prose file that stays at root, beside this README
├── docs/                           # project notes & records (moved from root 2026-08-01) + the LED sweep tuner
│   ├── solar-glow-drh-v2-hardware.md    # as-built wiring & pin map (v2-era lineage; banner at top)
│   ├── solar-glow-drh-v2-mechanical.md  # board mechanics, keepouts, access (v2-era lineage; banner at top)
│   ├── v4-aem10300-prewiring.md         # the v4 net/pin plan — applied 2026-07-30, kept as the record
│   ├── v4-schematic-sync-checklist.md   # the sch→board sync procedure — DONE, kept as the record
│   ├── harvest-bench-fixture-handoff.md # the energy-budget bench fixture (the #1 open gate's rig)
│   ├── harvest-budget-test-board.md     # the harvest test-board concept
│   ├── eink-display-variant-notes.md    # e-ink variant study (concept, not adopted)
│   ├── firmware-to-pcb-open-items.md    # v3-era cross-team memo (SUPERSEDED; record only)
│   ├── mcp-setup.md                     # sourcing MCP servers setup (DigiKey/Mouser)
│   └── led-sweep-tuner.html             # interactive LED-constant sandbox (firmware/README links it)
├── firmware/                       # bare-metal C (AVR64EA28); compile-verified, see firmware/README.md
├── bench/                          # pogo-plate bench monitor: Pico firmware + host dashboard (see bench/monitor)
├── datasheets/                     # fitted parts + documented substitutes, named "REF  MPN  $price.pdf"
│                                   #   (survey sheets and replaced-part docs culled 2026-08-01 — git history)
├── enclosure/                      # Ti back-shell + resin brace: CAD / STEP / STL / drawings / assembly views
│                                   #   fit_rules.py + board_parts.py = the geometry both generators derive from
└── v0-prototype/                   # the original prototype, kept for posterity (renamed from "v0 prototype" 2026-08-01)
```

---

## Building the board

The board is a KiCad project — open it, run DRC, and export the fab set:

1. Open `solar-glow-drh-v4_0.kicad_pro` in **KiCad** (2026 file format).
2. **Run DRC.** It comes back clean apart from the intentional exceptions catalogued in
   `PCB/README.md` and `solar-glow-drh-design-notes.md` (the NFC coil `LA`↔`LB` short, the eight
   GND-tie mounting-hole/gold-frame contacts, the two plating-bus stubs crossing Edge.Cuts at
   x=25.4, the illumination copper inside the glow window, and the benign `lib_footprint_issues`
   plus the **intentional** `BTN` global label on PA5 — the documented future-button pin
   (a deliberate no-fit; recipe in `firmware/README.md`), not a loose end). Fill zones (press **B**) before checking.
3. **Plot Gerbers + drill** from KiCad's own Fabrication Outputs and order from **PCBWay**
   (**2-layer**, 0.6 mm; selective hard gold + plating bus + resin-fill/cap per `PCB/README.md`).

> The supercap land is the one thing to never get wrong. **Both** SCPC cells — the 39 mm
> **SS17** (SC1/SC3) and the 28.5 mm **WS17** (SC2/SC4) — solder to **flat pads under the body**
> (the asymmetric P/N widths are the polarity key), **not** to the folded end tabs, which are
> non-solderable mechanical locators. The footprints here are built to the correct under-body
> land; don't substitute an end-tab land.
>
> Mind the two lengths. Assuming every cell was the 28.5 mm WS17 is exactly what put 593 mm³ of
> brace inside SC1 and SC3 — see [`enclosure/README.md`](enclosure/README.md).

---

## Assembly order (when boards arrive)

1. **Validate the energy budget first** — harvest vs. LED draw under real lighting (above).
2. **Reflow the SMD parts** — the QFN MCU and the LGA accelerometer need hot air / a hotplate;
   the EP and the accel pad reflow to their planes.
3. **Flash firmware** over UPDI — the Tag-Connect pad (`TC1`) is the no-header path; `J1` is the
   backup header. **This step moved ahead of the cells on 2026-07-30**, when TC1 was deliberately
   moved to `F.Cu`: PV1's body covers the pad cluster, so a pogo cable cannot reach it once the
   cell is on. The trade is a good one — the old position was under `SC1`, which is *reflowed*, so
   the window used to close before the board was even finished. See the warning box in
   [`PCB/README.md`](PCB/README.md).
4. **Hand-solder last** — the solar cells (heat-sensitive: ≤ 260 °C / 2 s, no IPA), and set the
   **SW2** bridge for OFF / ON / TINY.

---

## Firmware

A first implementation now lives in **`firmware/`** — bare-metal C, **verified at the register
level** against the AVR64EA28 and ADXL367 datasheets and **compile-verified in CI** (warning-free
against the AVR-Ex DFP; not yet run on hardware). Its knobs, wake model, and power notes are in
**`firmware/README.md`** (authoritative); the wiring it targets is **`firmware/board.h`**, which
`check_consistency` **[1]** holds against the schematic netlist pin by pin. (The complete v2-era
pin map in **`solar-glow-drh-v2-hardware.md`** is lineage, not a current source — see the truth
table above.) Final
duty-cycle and feature tuning stay **gated on the energy-budget measurement** below. In short,
the board gives it:

- **LED breathing** — the four LEDs sink into **PA0–PA3 = TCA0 WO0–WO3**, so split-mode PWM
  drives all four as independent 8-bit channels (the 150 Ω ballast sets the peak; PWM sets the
  average, so you trim brightness *below* that ceiling).
- **Tap-to-wake** — the accelerometer’s two interrupts land on **PF1 / PF0**; configure
  tap / double-tap and let it pull the MCU out of sleep.
- **NFC contact tag** — `U5` (NXP NT3H2211, on the board from v3.0) carries a **vCard** a phone reads on a
  tap to save the contact (RF-powered, so it reads with the cap flat), and its **field-detect**
  line wakes the same glow. The tag has no sleep state and would draw **~195 µA** continuously — the
  card's largest idle load — so firmware **power-gates** its VCC through a load switch (`U6`) on
  **NFC_EN (PA7)**, held **off by default** and raised only around an I²C access; the vCard read and
  the FD-wake both run on the phone's field power, so they still work with the tag's VCC off. Shares
  the I²C bus with the accel (`0x55` vs `0x1D`). See `firmware/README.md` → *NFC contact card*.
- **Light sensing** - the divider taps the **merged solar node SRC** (SRC ÷ 2) into **PD2** (AIN2), so it
  reads light directly — ~0 V dark, rising under light; firmware adapts the glow to available
  light and can also read **VDD/10** and the internal temp sensor.
- **Wake-on-light** — the card can also wake when light appears, with no tap. The implemented
  path is an **RTC-timed ADC poll** in deep Power-Down (sample PD2/AIN2 every ~1–2 s, glow on a
  dark→light rise). The tempting *instant* AC0-comparator version was checked against the
  datasheet and found **non-viable on this part** — the AC interrupt doesn't update with the
  peripheral clock stopped, and the AC isn't a Standby/Power-Down wake source, so it would never
  fire. Instant response isn't lost: the accelerometer interrupt wakes from Power-Down, and
  picking the card up to carry it into the light *is* that motion. (Standing current is ~2.7 µA total — the
  always-on accelerometer (ADXL367, ~0.89 µA) no longer dominates it, and neither the poll nor the NFC tag do, the latter being
  power-gated off by default — see `firmware/README.md`.)
- **Low-power housekeeping** — `VREGCTRL.PMODE = AUTO` for sub-µA power-down; RTC/PIT off the
  internal ULP oscillator (no crystal); an EEPROM “times-activated” counter that survives a
  full supercap drain; and the core **IDLE-sleeps through the breathing glow** while TCA0 keeps
  the PWM running, rather than busy-waiting. (An autonomous CCL + EVSYS light-wake is a possible
  v-next, but isn't what the current firmware does.)

Still open (what the bench measurement unlocks): final breathing-curve and tap-gesture tuning,
charge / brown-out management around the supercap bank, and the duty-cycle adaptation the
harvest number sizes.

---

## Enclosure

A back-only **machined-titanium** shell hugs the populated rear; the front stays naked. A
single-piece **resin diffuser brace** fills the cavity, carries centre support, backs the
monogram window and holds the ferrite over the NFC coil. CAD, STEP, STL, fab notes and
dimensioned drawings are in `enclosure/` — full detail in
[`enclosure/README.md`](enclosure/README.md).

![Exploded: titanium shell, resin brace, PCB, 8× M2 brass](enclosure/solar-glow-drh-assembly-exploded.png)

**Respun 2026-07-29 against the real board, because neither part would have assembled.** The
brace's middle band was sized for supercap bays ending at y31.15 / y57.75 — the 28.5 mm WS17
length — while SC1/SC3 are 39 mm SS17 cells, so it put **593 mm³ of solid resin inside three
1.70 mm cans**. The shell's support lip landed on nine B-side parts including **4.17 mm² of
live pad** (`STO`, `STO_LDO`, `VS`, `NFC_EN`) under grounded titanium — fitting it shorted the
storage rail — and five of the eight M2 bosses fouled a part, two on live nets.

Both geometries are now **computed from the board** (`enclosure/fit_rules.py`, reading part
positions from `enclosure/board_parts.py`) rather than hand-placed, and gated by
`check_consistency` **[8]**. Interference is structurally impossible: a part the brace cannot
span is *subtracted* from its footprint rather than pocketed. No board change was required.

The decisions that matter once it's cut: **titanium (Ti-6Al-4V Grade 5)**, **3-axis CNC-milled**
by PCBWay, **bead-blast** finish. The cavity is **cap-limited to 1.80 mm** by the four 1.70 mm
supercaps; the floor is a **true uniform 1.00 mm** (the old 0.05 mm U7 relief pocket was deleted
2026-07-28 — U7 is the 0.90 mm DFN-8, not the 1.75 mm SOIC it was sized for); overall height
**3.55 mm**. **Eight** bosses on the v4 8-hole pattern (four corner, concentric with the r3.0
fillets, plus four panel-corner), each **scalloped** clear of whatever fouls it while keeping
≥ 92.3 % of its M2 thread annulus. Retention is **eight M2×3 slotted brass screws**, not a press
fit; the head is Ø3.0 and the tip lands **flush** in a Ø3.0 back spotface.

The electrical gotchas: the screws tie the metal body to board GND, so the enclosed variant
**drops the edge castellations** (or adds a die-cut Kapton layer) so nothing shorts to the
grounded shell; the **accelerometer tap is the actuator** (cap-touch dies behind a grounded
plate); and the east lip is held **1.00 mm clear of NFC coil copper measured at x48.550** — a
grounded feature over the antenna detunes it, and the constant it used to be sized against
(48.40) was optimistic enough to overhang.

---

## Cost

- **Per board ≈ $100** at quantity one, and the **four supercaps are the dominant line** —
  well over half the BOM. This is a showpiece, not a hand-out-by-the-hundred card.
- The energy tank is where the money goes; everything else is comparatively cheap.

---

*© 2026 Devin R. Horowitz. Released under the [MIT License](LICENSE).*
