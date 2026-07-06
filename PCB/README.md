# SOLAR-GLOW · DRH — PCB (v3.0): Order & Build Guide

![Generated/docs/solar-glow-drh-v3_0-bottom.png](https://github.com/devinhorowitz/solar-business-card/blob/main/Generated/docs/solar-glow-drh-v3_0-bottom.png)

This folder holds the **board** for SOLAR-GLOW · DRH — the KiCad project, the bill of
materials, and the artwork reference for the SW2 selector. It is the thing you fab and
populate. This README is the procedure: **how to order the bare PCB, how to order the
parts, and how to build the assembly.**

```
PCB/
├── solar-glow-drh-v3_0.kicad_pro     # KiCad project (open this)
├── solar-glow-drh-v3_0.kicad_sch     # schematic
├── solar-glow-drh-v3_0.kicad_pcb     # board — 2-layer, routed, teardropped (source of truth)
├── solar-glow-drh-v3_0.kicad_prl     # local project state
├── solar-glow-drh-v3_0.kicad_dru     # two-tier design rules (PCBWay floor + marginal band)
├── solar-glow-drh.kibot.yaml         # CI recipe — regenerates ../Generated/ on every push
├── solar-glow-drh-v3_0-BOM.xlsx      # bill of materials — v3.0 master (U6 + R14; all-0402)
├── solar-glow-drh-v3_0-BOM-assembly.xlsx  # trimmed PCBA BOM (36 placed parts)
├── sw2-anode-selector.png            # how to read/set the SW2 OFF/ON/TINY bridge
├── led-orientation-D2-D5.png         # reverse-mount LED rotation reference for PCBA
└── DRC.rpt / ERC.rpt                 # last GUI report exports (CI keeps live copies in ../Generated/)
                                      # (v2_1 / v2_2 / v2_3 revisions live in git history, not this folder)
```

> **The board is the source of truth.** `solar-glow-drh-v3_0.kicad_pcb` / `.kicad_sch`
> govern. The design *reasoning* lives one level up:
> - `../solar-glow-drh-v2-hardware.md` — as-built pin map and net list (the firmware target).
> - `../solar-glow-drh-v2-mechanical.md` — board envelope, heights, mount holes, keepouts.
> - `../solar-glow-drh-design-notes.md` — why each decision was made; the landmines.
> - `../README.md` — the project overview and the standing open question (energy budget).
>
> Where a number here and a number in those files ever disagree, re-read the `.kicad_pcb`.

> **Read this before committing money: the energy budget has never been measured.** Harvest
> under real indoor light versus four breathing LEDs at the current 150 Ω ballast is an
> unproven bet. It does not stop you fabbing one board — it stops you populating a *batch*.
> See **First power & bring-up** below and `../solar-glow-drh-design-notes.md` §2.

---

## Board at a glance

| Parameter | Value |
|---|---|
| Outline | 50.80 × 88.90 mm rounded rectangle, **3.0 mm corner radius** |
| Layers | **2 copper**: F.Cu (cells, plating ties, monogram art) · B.Cu (everything else) |
| Power architecture | **GND = full-board B.Cu pour** (~3000 mm²); **VS = routed B.Cu mesh** |
| Finished thickness | **0.6 mm** FR4 |
| Surface finish | **ENIG** + **selective hard (electrolytic) gold** on the F.Cu gold set — the plating bus exists to feed it (see the order special request) |
| Soldermask | **Matte black**, both sides |
| Silkscreen | White (back-side identifiers / logos); front face is intentionally bare |
| Components | **48 on the back**; the front carries only the two solar cells (PV1/PV2) |
| Teardrops | **Enabled** — 243 curved teardrop zones (pads, vias, and track-ends); R14 and the reworked U6 area (the pin-map fix deleted 4 zones) have none — run Tools → Add Teardrops before plotting |
| NFC | NT3H2211 tag (U5) + **PCB-etched 7-turn coil** on B.Cu, power-gated by U6 |
| Indicative parts cost | **≈ $93/board** at qty 1–10; supercaps + solar cells are most of it |

**Glow window — the one feature a fab must not "clean up."** A rectangle at
**x 14.95–35.85, y 40.8–47.0** (≈ 20.9 × 6.2 mm, board center) is a **keepout on both
copper layers** and has the **soldermask opened over it on both faces**. The rear LEDs fire
*through* the bare FR4 to light the front monogram; the open rear mask lets the gold ENIG
reflect that light forward instead of absorbing it. Tracks are allowed inside the window;
**vias, copper pour, and footprints are not.** Do not let a DFM auto-edit flood mask back
over it.

**NFC coil region — the second feature a fab must not "improve."** The east band at
**x 36.8–49.0, y 31.6–57.4** carries the etched antenna: the B.Cu GND pour is kept out of
it, and F.Cu is a keepout over it. The **LA↔LB track crossing at (41.0, 38.0) is the coil's
electrical junction — intentional, not a short.** Any DFM note offering to "fix" the
crossing or to flood the region gets declined.

---

## Step 1 — Open the project and run DRC

1. Open `solar-glow-drh-v3_0.kicad_pro` in **KiCad** (designed in the 2026 file format).
2. Register the footprint library: the board uses a local `solarglow` library that is not
   registered on a fresh machine. Add it under **Preferences → Manage Footprint Libraries**
   (or accept KiCad's prompt) so the footprints resolve.
3. **Run DRC.** The project carries a two-tier rule file (`solar-glow-drh-v3_0.kicad_dru`):
   - **error tier** = the do-not-ship floor (clearance/track ≥ 0.126 mm, annular ≥ 0.125,
     drill ≥ 0.2) — sized against PCBWay's stated 2-layer capability;
   - **warning tier** = the *marginal band* [0.126, 0.1524): PCBWay-legal geometry that is
     tighter than 6 mil, flagged on purpose so the ledger stays visible.

   **Expected result: 0 errors, ~61 warnings, 3 exclusions.** The exclusions are the two
   gold-plating tie stubs crossing the outline and the LA↔LB coil junction — all intentional.
   The warnings are the marginal-band ledger (mostly the 0.127 mm parallel corridors of the
   west-side bus) plus fourteen 0.15 mm track-width notes. **Do not "fix" warnings blindly**,
   and do not be alarmed if the warning *count* differs slightly between runs — KiCad's
   row enumeration jitters on long parallel runs (see the design notes, "row-count jitter"). After any board edit — including the R14 patch — **refill zones (B.Cu) before running DRC**; the committed fills predate the patch.
4. CI runs the same DRC (plus ERC and the full fab plot) on every push and commits the
   results to `../Generated/`. If your local run and `Generated/` disagree on *substance*
   (not row counts), stop and investigate.

---

## Step 2 — Generate the fab outputs (do this in KiCad, not from a script)

There are **no Gerbers committed in this folder** — generate them fresh (or take the
CI-built set from `../Generated/gerbers/`, which comes from the same exporter).

> **Use KiCad's own Fabrication Outputs exporter.** Older revisions of this project emitted
> geometry-derived Gerbers from a Python preview script; **do not fab from those.** A preview
> emitter lacks real thermal-relief spokes, exact mask expansion, and teardrop fills. Plot
> from **File → Fabrication Outputs → Gerbers…** so the production set carries what the
> board actually specifies.

**Plot (Gerbers):**
- Layers: **F.Cu, B.Cu**, **F.Mask, B.Mask**, **F.SilkS, B.SilkS**, **Edge.Cuts**, and
  **F.Paste / B.Paste** (for the stencil — Step 5).
- Format **Gerber X2** (or whatever PCBWay's order page asks for), millimeters, 4.6 resolution.
- Leave KiCad's mask and via-tenting settings as-is. **Vias are tented** on this board (clean
  card face); confirm the plot keeps them tented and keeps the glow-window mask openings.

**Drill (Excellon):**
- **File → Fabrication Outputs → Drill Files…** Generate Excellon + a drill map.
- Plated holes: the 91 vias (uniform 0.30 mm) and the four M2 mount holes (Ø 2.2 mm).
  Non-plated: the TC2030 latch/alignment holes. Export PTH and NPTH per PCBWay's preference.

**Bundle** the Gerbers + drill into one zip for upload.

---

## Step 3 — Order the bare board (PCBWay)

Order parameters, from the committed board:

| PCBWay field | Set to |
|---|---|
| Layers | **2** |
| Material / thickness | FR4, **0.6 mm** finished |
| Surface finish | **ENIG**, plus **selective hard gold** per the special request below |
| Soldermask color | **Matte black** |
| Silkscreen | White |
| Min track / spacing used | **0.15 mm track / 0.127 mm spacing** (the marginal-band corridors) |
| Vias | **Uniform: 0.30 mm drill / 0.60 mm pad** (0.15 mm annular), 94 total, tented (resin-fill + cap ordered board-wide) |
| Non-plated holes | TC2030: Ø **2.3749 mm** (4× leg-latch) and Ø **0.9906 mm** (3× alignment) |
| Plated mount holes | Ø **2.2 mm** ×4 (M2, corners, tied to GND) |
| Castellations | **None** (verified — only the corner mount holes sit within 1.5 mm of the rim) |

**Run PCBWay's DFM check against these.** The binding features are the **0.127 mm spacing**
and **0.15 mm tracks** — inside PCBWay's stated 0.1 mm/4 mil 2-layer capability, but worth a
glance at their sheet. There are no fine vias in v3.0 (the whole board runs the one 0.30/0.60
via), and no controlled-impedance nets to declare.

**Add to the order notes / gerber review:**
- "**Leave soldermask open over the central window per the mask layers — do not tent or
  flood.**" (The bare-FR4 + open-ENIG window is the whole optical trick.)
- "**Keep vias tented.**"
- **Selective hard gold (the reason the plating bus exists):** paste this verbatim into the
  special-request box —

  > *"Selective hard gold plating on top side: the DRH monogram field, the perimeter frame, and
  > the six edge ornament shapes (all connected copper on F.Cu). Remaining exposed copper: ENIG.
  > The two 0.25 mm traces crossing the board outline at x=25.4 (top and bottom edges) are
  > plating-bus connections; please retain to panel rail and rout at depanel. The gold set is
  > GND-referenced by design (the four M2 mounting-hole pads overlap the frame at all four
  > corners); not floating copper, not a defect. All in-pad vias: resin-filled and copper-capped
  > (POFV, IPC-4761 Type VII)."*

  A DFM reviewer will flag copper-to-edge = 0 at the two stubs; that is by design. (Geometry
  re-verified against the committed board 2026-07-02: the gold set is a single connected F.Cu
  component, both stubs + all four M2 GND pads on it; everything else exposed on F is the solar
  lands, which stay ENIG.) Ordering plain ENIG without this request leaves the bus as dead
  copper and no wear surface on the face — do not ship without it.
- "**The LA/LB track crossing at (41.0, 38.0) is the NFC coil junction — intentional.**"
- **Bench pad strip (`TP1` + `JP1`, back east edge, x 48.4):** five bare 1.7 mm SMD probe pads
  (VIN / GND / VS / SCL / SDA at 2.54 pitch) — no component; they are in the mark-as-DNP list
  above. Pinout and the bench-power ritual live in `solar-glow-drh-v2-hardware.md`.
- **Via-in-pad — 12 vias land inside pads** on this board: 10 in soldered pads (`TC1.1`, `U1.EP`,
  `U5.1`, `D1.K`, `R13.2`, `SW2.1`, `J1.2`, `PV1.N`, `PV2.N`, `PV2.Nt`) plus 2 in the bench-strip
  probe pads (`JP1.3`, `JP1.4` — bare pads, hand-solder optional). The clean answer is
  the same as always: **order resin-fill + cap (via-in-pad process) board-wide.** The one
  that *must* be flat and hole-free is **TC1.1** (a Tag-Connect pogo contact); the rest
  are large or hand-soldered pads where a plugged via is merely tidy.

> **Resolved in the R14 patch:** the previously undocumented Ø 0.89 mm NPTH at (37.9, 75.4)
> (under SC4's body) was **deleted from the board** — nothing in the repo claimed it. If it had a
> purpose, it's one git revert away. *(Lineage re-checked 2026-07-02: absent from the v0
> prototype; entered at v2.1 inside an anonymous `NPTH_mech` footprint; never appeared in the fab
> hole table; the enclosure generator places nothing there. Orphan confirmed — deletion stands.)*

A **frameless solder-paste stencil** (from the F.Paste / B.Paste plot) is strongly
recommended — the QFN EP and the LGA accelerometer reflow far more reliably with paste than
hand-tinning. Order it alongside the board.

---

## Step 4 — Order the parts

**BOM state.** The masters are now **`solar-glow-drh-v3_0-BOM.xlsx`** and
**`solar-glow-drh-v3_0-BOM-assembly.xlsx`**, generated from the v2.2 files with three fixes:
**U6 (TPS22918) and R14 (100 k `NFC_EN` pulldown) added**, the stale **JP1/JP2 rows dropped** (the `JP1` designator is reused for the v3.0 bench pad strip — bare pads, not a BOM part)
(those headers left the board in v3.0), and **every passive except SJ1 converted to 0402** to match
the board's placed lands — the v2.2 file still listed 0805 MPNs for most R/C. Converted and added
lines have their **prices blanked pending a fresh quote**; the old 0805 prices don't carry. The
`v2 2` and older BOM files remain in git history as lineage.

Summary of the **orderable** lines:

| Ref(s) | Qty | Value | MPN |
|---|---:|---|---|
| U1 | 1 | AVR64DD28 (VQFN-28) | `AVR64DD28-I/STX` |
| U2 | 1 | Dual SAB MOSFET (SOIC-8) | `ALD910025SALI` |
| U3 | 1 | ADXL367 accelerometer (LGA-12) | ADI `ADXL367` — confirm order code (was wrongly listed LIS2DH12TR) |
| U4 | 1 | TLV3011 comparator + 1.242 V ref (SOT-23-6, open-drain) | `TLV3011BIDBVR` |
| **U5** | 1 | **NFC tag, NT3H2211 (XQFN8 / SOT902-3)** | `NT3H2211W0FHKH` — matches the placed 0.25×0.4 mm land |
| **U6** | 1 | **Load switch (SOT-23-6) (in the v3_0 BOM)** | `TPS22918DBVR` |
| Q1 | 1 | PNP, BCP53 family | `BCP5316MTWG` |
| PV1, PV2 | 2 | SM141K06TF solar cell | `SM141K06TF` |
| D1, D9 | 2 | Schottky, SOD-123 | `MMSD301T1G` |
| D2–D5 | 4 | Amber LED, reverse-mount | `LA P47F-V2BB-24-3B5A-30-R18-Z` |
| **SC1–SC4** | **4** | **1 F / 2.75 V (WS17)** | `3-153-438` |
| R1–R4 | 4 | **150 Ω 1% 0402 — SIZED** | `RC0402FR-07150RL` |
| R5, R6 | 2 | 1 MΩ 0402 | `RC0402FR-071ML` |
| R7 | 1 | 6.81 MΩ 0402 | `RC0402FR-076M81L` (confirm stock) |
| R8 | 1 | 3.74 MΩ 0402 | `RC0402FR-073M74L` (confirm stock) |
| R9 | 1 | 1 kΩ 0402 | `RC0402FR-071KL` |
| R10, R11 | 2 | 4.7 kΩ 0402 (I²C pull-ups) | `RC0402FR-074K7L` |
| R12 | 1 | 220 Ω 0402 | `RC0402FR-07220RL` |
| **R13** | 1 | **10 kΩ 0402 (FD pull-up to VS)** | `RC0402FR-0710KL` |
| **R14** | 1 | **100 kΩ 0402 (`NFC_EN` pulldown — v3.0 R14 patch)** | `RC0402FR-07100KL` |
| C1, C2, C3, C6, C7, **C8** | 6 | 100 nF X7R 0402 | `GRM155R71C104KA88D` (Murata) |
| C4 | 1 | 1 µF X5R 0402 | `GRM155R61A105KE15D` (Murata) |
| C5 | 1 | 10 nF X7R 0402 | `GRM155R71C103KA01D` (Murata) |
| **C9** | (1) | **NP0 0402, DNP — coil trim** | buy an NP0 range ~47–150 pF for the bench |
| SJ1 | 1 | 0 Ω jumper 0805 | `RC0805JR-070RL` |

**No ordered part — these are board features, not BOM line items:**
- **SW2** (LED OFF/ON/TINY) and **SB1–SB4** (per-LED force-on) are **solder bridges** on the PCB.
- **The NFC antenna is etched copper** — no wound coil to buy.
- **TC1** is the **TC2030 footprint** — no soldered part; it mates with a TC2030-MCP pogo
  cable. **Do not load.**
- **J1** is an **optional** 0.1″ UPDI header — TC1 is the primary programming path.
- **MH1–MH4** are plated drills — supply your own **M2 screws** if enclosing.

**Flags to clear before you buy:**
- **R1–R4 value (150 Ω) is `SIZED`, not locked.** It sets per-LED peak current (~9 mA on the
  clamped rail) and is **bench-pending** — the energy-budget test may re-tune it. Buy a small
  0402 range (e.g. 100 / 150 / 220 / 330 Ω) so you can swap after the measurement.
- **C9 stays DNP** until the coil is trimmed on the bench (resonance target 13.56 MHz with
  the NT3H2211's internal capacitance; the Ti shell behind the coil moves it — measure with
  the shell fitted).
- **SC1–SC4 are the dominant cost** (well over half the BOM). Confirm live pricing.

---

## Step 5 — Assembly (as ordered: PCBWay turnkey)

Ordered as **single-sided turnkey assembly**: PCBWay sources the parts and machine-places
them on the **back**; the front stays naked until you fit the cells. You finish two part
types by hand afterward.

**The split**
- **PCBWay machine-places** (reflow, bottom, **36 parts**): U1–U6, Q1, D1, D9, D2–D5,
  R1–R14, SJ1, C1–C8. `solar-glow-drh-v3_0-BOM-assembly.xlsx` is that trimmed file (36 parts, U6 + R14 included).
- **You hand-solder afterward:** SC1–SC4 supercaps and PV1–PV2 solar cells. They are kept
  **off** the PCBA BOM on purpose — the supercaps are manual-solder only (SCHURTER SCPC),
  and the cells are heat-sensitive.
- **Not placed:** SW2, SB1–SB4 (solder bridges you set), TC1 (Tag-Connect pad), J1
  (optional header), MH1–MH4 (mounting holes), C9 (DNP).

**Sourcing:** turnkey, with the standing instruction that anything PCBWay can't source they
flag and you consign from DigiKey — **no substitutes without approval**. The likeliest to
need consigning are **U1** (AVR64DD28), **U2** (ALD910025SALI), **U5** (NT3H2211 — going
end-of-life in places; check stock early), and **D2–D5** (the ams OSRAM amber bin — confirm
the exact reverse-mount P/N, OSRAM sells top-emit lookalikes).

**Files handed to PCBWay:** the trimmed assembly BOM, the **centroid / pick-and-place**
(KiCad → Fabrication Outputs → Component Placement; **CSV, mm, exclude-DNP** after marking
SC1–SC4 / PV1–PV2 / J1 / C9 / JP1 / TP1 as DNP; **Absolute origin** to match the drills), and
`led-orientation-D2-D5.png`.

**Order-form settings that matter:** bottom side, qty 5, ENIG **+ selective hard gold (special request above)** / matte-black / white silk,
**resin-fill + via-in-pad** (cleans the 10 via-in-pad joints and keeps the TC1 pogo pad
flat), **moisture-sensitive = U1 / U2 / U3 / U5** (U3 is a MEMS part — observe peak reflow
temp, no ultrasonic clean), no China substitutes. **Black-FR4 core stays OFF** — the glow
needs translucent FR4, the black look comes from the soldermask.

> **LED polarity (reverse-mount `LA P47F`):** anode **A** on the left, cathode **K** on the
> right, all four at **rotation 0** (see `led-orientation-D2-D5.png`). They emit *down* through
> the FR4 to the front. A flipped LED will not glow — this is the single most common PCBA
> defect on this board.

### Finishing the board by hand (after PCBWay returns it)

Work outside-in by heat sensitivity:

1. **Supercaps SC1–SC4 — hot air / hotplate, not an iron.** They solder to **flat pads under
   the body**; the **asymmetric P/N widths (P = 7.8 mm, N = 12.2 mm) are the polarity key**.
   The folded end tabs are coated, non-solderable locators — never solder to those. The cells
   sit at the board ends, clear of the central cluster, so localized hot air will not disturb
   the reflowed parts.
2. **Solar cells PV1 / PV2 last (most fragile).** Iron **≤ 260 °C, ≤ 2 s per joint**, and
   **do not clean with IPA**. Mind cell polarity to the custom land.
3. **Set the LED master switch SW2** (3-pad bridge — see `sw2-anode-selector.png`): center–left
   = **ON**, center–right = **TINY** (dim via R12), unbridged = **OFF** (a true hardware off —
   supercap-safe for storage).
4. **SB1–SB4: leave open.** Each is a per-LED *force-on* bridge that shorts that LED's drive
   node (LDRVn) to GND. Open is the normal state (the MCU drives the LED); bridge one only to
   force that LED hard-on without firmware.
5. **Confirm SJ1** (VDDIO2 → VS tie) is present — PCBWay places it, but without it PORTC
   (the I²C port) has no I/O supply.

**Critical, do-not-get-wrong** (full rationale in `../solar-glow-drh-design-notes.md`): the
supercap under-body land and its asymmetric-width polarity key; reverse-mount LED orientation;
and the glow-window mask staying open (Step 3) — a tented window kills the optics.

---

## Step 6 — First power & bring-up

1. **Measure the energy budget first — this is the project's #1 gate.** Before populating a
   second board, put the cells under your **actual target lighting** and measure **harvest
   current vs. LED draw**. That single number sizes the duty cycle and the feature set. See
   `../solar-glow-drh-design-notes.md` §2 and the open-question section in `../README.md`.
2. **Confirm SW2 is ON or TINY.** If SW2 is OFF, no firmware and no PWM will light the LEDs —
   that is the hardware master switch by design.
3. **Flash firmware over UPDI.** Use a **TC2030-MCP** pogo cable on `TC1` (hands-free), or
   solder a 3-pin header on `J1` as the backup. Firmware lives in **`../firmware/`**; its
   knobs and wake model are in `../firmware/README.md`, and the pin map it targets is
   `../solar-glow-drh-v2-hardware.md`.
   > **Programming caution:** `NFC_EN` (PA7) now has a **100 kΩ pulldown (`R14`)** — U6
   > defaults hard-off while PA7 floats during reset / UPDI. Still drive PA7 low early in
   > init as belt-and-suspenders. The **U6 pin-map check is done** — TI SLVSD76C
   > (`../datasheets/tps22918.pdf`; the -Q1 doc in the repo matches identically) showed the symbol had **VIN/VOUT and GND/QOD
   > transposed**; the board was **fixed 2026-07-02** (pads renetted to TI truth, schematic
   > pin numbers corrected, local copper reworked). Details in
   > `../solar-glow-drh-design-notes.md`, U6 pin-map addendum.

---

## Enclosure note

An optional machined-titanium back-shell lives in `../enclosure/` (v3.0 shell committed; see
its README and `../solar-glow-drh-v2-mechanical.md`). It is **on ice until the board is
validated** — and note the shell interacts with the electronics twice: it kills capacitive
sensing (why the actuator is the accelerometer) and it sits behind the NFC coil (why C9 is
trimmed with the shell fitted). Nothing about ordering or building the bare board depends
on it.

---

*Part of SOLAR-GLOW · DRH. © 2026 Devin R. Horowitz. MIT License (see `../LICENSE`).*
