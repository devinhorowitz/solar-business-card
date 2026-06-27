# SOLAR-GLOW · DRH — PCB (v2.1): Order & Build Guide

This folder holds the **board** for SOLAR-GLOW · DRH — the KiCad project, the bill of
materials, and the artwork reference for the SW2 selector. It is the thing you fab and
populate. This README is the procedure: **how to order the bare PCB, how to order the
parts, and how to build the assembly.**

```
PCB/
├── solar-glow-drh-v2_1.kicad_pro     # KiCad project (open this)
├── solar-glow-drh-v2_1.kicad_sch     # schematic
├── solar-glow-drh-v2_1.kicad_pcb     # board — 6-layer, routed, DRC-clean (source of truth)
├── solar-glow-drh-v2_1.kicad_prl     # local project state
├── solar-glow-drh-v2_1-BOM.xlsx      # bill of materials — parts, prices, DigiKey P/Ns (master)
└── sw2-anode-selector.png            # how to read/set the SW2 OFF/ON/TINY bridge
```

> **The board is the source of truth.** `solar-glow-drh-v2_1.kicad_pcb` / `.kicad_sch`
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
| Layers | **6 copper**: F.Cu · **In1 = GND plane** · In2 sig · In3 sig · **In4 = VS plane** · B.Cu |
| Finished thickness | **0.8 mm** FR4 |
| Surface finish | **ENIG** (gold — it is both the look and the reflector behind the glow window) |
| Soldermask | **Matte black**, both sides |
| Silkscreen | White (back-side identifiers / logos); front face is intentionally bare |
| Components | All on the **back**; the **front is naked** (two solar cells + the glowing monogram) |
| Indicative parts cost | **≈ $93/board** at qty 1–10; supercaps + solar cells are most of it |

**Glow window — the one feature a fab must not "clean up."** A rectangle at
**x 14.95–35.85, y 40.8–47.0** (≈ 20.9 × 6.2 mm, board center) is a **keepout on all six
copper layers** and has the **soldermask opened over it on both faces**. The rear LEDs fire
*through* the bare FR4 to light the front monogram; the open rear mask lets the gold ENIG
reflect that light forward instead of absorbing it. Tracks are allowed inside the window;
**vias, copper pour, and footprints are not.** Do not let a DFM auto-edit flood mask back
over it.

---

## Step 1 — Open the project and run DRC

1. Open `solar-glow-drh-v2_1.kicad_pro` in **KiCad** (designed in the 2026 file format).
2. Register the footprint library: the board uses a local `solarglow` library that is not
   registered on a fresh machine. Add it under **Preferences → Manage Footprint Libraries**
   (or accept KiCad's prompt) so the footprints resolve.
3. **Run DRC.** It is clean apart from two expected, benign items, both already set to
   *warning* (not error) severity in the project:
   - **`lib_footprint_issues`** — the `solarglow` footprints differ from a registered library
     copy because the library is local. Cosmetic; expected.
   - **One `track_dangling`** on the **`BTN`** net — `BTN` (PA5) is a *reserved* button stub
     for a future revision and is deliberately routed only to a landing. Expected.

   The rear soldermask "bridges" over the reflective window are **intentional**, not errors.

---

## Step 2 — Generate the fab outputs (do this in KiCad, not from a script)

There are **no Gerbers committed in this folder** — generate them fresh.

> **Use KiCad's own Fabrication Outputs exporter.** Older revisions of this project emitted
> geometry-derived Gerbers from a Python preview script; **do not fab from those.** A preview
> emitter lacks real thermal-relief spokes, exact mask expansion, and proper non-functional-pad
> removal. Plot from **File → Fabrication Outputs → Gerbers…** so the production set carries
> what the board actually specifies.

**Plot (Gerbers):**
- Layers: **F.Cu, In1.Cu, In2.Cu, In3.Cu, In4.Cu, B.Cu** (all 6), **F.Mask, B.Mask**,
  **F.SilkS, B.SilkS**, **Edge.Cuts**, and **F.Paste / B.Paste** (for the stencil — Step 5).
- Format **Gerber X2** (or whatever PCBWay's order page asks for), millimeters, 4.6 resolution.
- Leave KiCad's mask and via-tenting settings as-is. **Vias are tented** on this board (clean
  card face); confirm the plot keeps them tented and keeps the glow-window mask openings.

**Drill (Excellon):**
- **File → Fabrication Outputs → Drill Files…** Generate Excellon + a drill map.
- The board has both **plated** holes (vias, the M2 mount holes) and **non-plated** holes
  (the TC2030 latch/alignment holes). Export PTH and NPTH per PCBWay's preference (merged or
  separate — their order page states which).

**Bundle** the Gerbers + drill into one zip for upload.

---

## Step 3 — Order the bare board (PCBWay)

Order parameters, from the committed board:

| PCBWay field | Set to |
|---|---|
| Layers | **6** |
| Material / thickness | FR4, **0.8 mm** finished |
| Surface finish | **ENIG** |
| Soldermask color | **Matte black** |
| Silkscreen | White |
| Min track / spacing used | **≈ 0.16 mm** (the tightest QFN-escape traces) |
| Smallest plated via | **0.20 mm drill / 0.40 mm pad** (≈ 0.10 mm annular ring) |
| Standard vias | 0.30 mm drill / 0.60 mm pad |
| Non-plated holes | TC2030: Ø **2.3749 mm** (4× leg-latch) and Ø **0.9906 mm** (3× alignment) |
| Plated mount holes | Ø **2.2 mm** ×4 (M2, corners, tied to GND) |
| Castellations | **None** (verified — no pads within 1.5 mm of the rim) |

**Run PCBWay's DFM / impedance check against these.** The binding features are the
**0.20 mm vias (≈ 0.10 mm annular)** and the **≈ 0.16 mm escapes** — both are inside a
standard 6-layer process but worth confirming on their capability sheet before you commit.
There are no controlled-impedance nets to declare.

**Add to the order notes / gerber review:**
- "**Leave soldermask open over the central window per the mask layers — do not tent or
  flood.**" (The bare-FR4 + open-ENIG window is the whole optical trick.)
- "**Keep vias tented.**"
- **Via-in-pad — resolved against the committed board.** 49 vias land inside a soldered pad.
  The fab question is binary: **if PCBWay plugs-and-caps every via board-wide, this is moot**,
  except for confirming the Tag-Connect pads come out flat. **If it does not, handle these
  four groups:**
  - **Plug & cap regardless** — the Tag-Connect pogo contacts must be flat and hole-free:
    **TC1.1, TC1.2, TC1.3.**
  - **Plug, or babysit during reflow** — small normally-soldered pads that will wick (refs
    **R1–R5, C6, D9, Q1, U2, U4**): exactly R1.2, R2.2, R3.2, R4.2, R5.1, C6.1, C6.2, D9.A,
    Q1.3, U2.1/2/3/4/5/6/8, U4.3.
  - **Leave to fab default** — big pads where the 0.3 mm barrel is negligible: the **U1 QFN
    exposed-pad** stitch vias (×2), the **six supercap under-body pads** (SC1.P, SC2.N, SC3.N,
    SC3.P, SC4.N, SC4.P), and the **four solar-cell pads** (PV1.N/Nt, PV2.N/Nt).
  - **No action** — flooded or hand-soldered: the solder-bridge selectors (SB1–4, SJ1, SW2)
    and the 0.1″ breakout pads (J1, JP1, JP2). *Note:* JP2's pads are small, so if you ever
    *reflow* a header onto JP2 rather than hand-soldering it, treat JP2.1–4 like the wicking
    group above.

A **frameless solder-paste stencil** (from the F.Paste / B.Paste plot) is strongly
recommended — the QFN EP and the LGA accelerometer reflow far more reliably with paste than
hand-tinning. Order it alongside the board.

---

## Step 4 — Order the parts

`solar-glow-drh-v2_1-BOM.xlsx` is the **master** (live prices, full notes, datasheet links).
Summary of the **orderable** lines:

| Ref(s) | Qty | Value | MPN | DigiKey P/N |
|---|---:|---|---|---|
| U1 | 1 | AVR64DD28 (VQFN-28) | `AVR64DD28-I/STX` | by MPN |
| PV1, PV2 | 2 | SM141K06TF solar cell | `SM141K06TF` | by MPN |
| D1, D9 | 2 | Schottky, SOD-123 | `MMSD301T1G` | `MMSD301T1GOSCT-ND` |
| **SC1–SC4** | **4** | **1 F / 2.75 V (WS17)** | `3-153-438` | by MPN |
| U2 | 1 | Dual SAB MOSFET (SOIC-8) | `ALD910025SALI` | `ALD910025SALI-ND` |
| D2–D5 | 4 | Amber LED, reverse-mount | `LA P47F-V2BB-24-3B5A-30-R18-Z` | `475-LAP47F-V2BB-24-3B5A-30-R18-ZCT-ND` |
| R1–R4 | 4 | **150 Ω 1% 0402 — SIZED** | `RC0402FR-07150RL` | by MPN |
| R12 | 1 | 220 Ω 0805 | `RC0805FR-07220RL` | by MPN |
| R5, R6 | 2 | 1 MΩ 0805 | `RC0805FR-071ML` | by MPN |
| R7 | 1 | 1.8 MΩ 0805 | `RC0805FR-071M8L` | by MPN |
| R8 | 1 | 1 MΩ 0805 | `RC0805FR-071ML` | by MPN |
| R9 | 1 | 1 kΩ 0805 | `RC0805FR-071KL` | by MPN |
| R10, R11 | 2 | 4.7 kΩ 0805 (I²C pull-ups) | `RC0805FR-074K7L` | by MPN |
| U3 | 1 | LIS2DH12 accelerometer (LGA-12) | `LIS2DH12TR` | by MPN |
| U4 | 1 | TLV431B reference (SOT-23) | `TLV431BCDBZR` | by MPN |
| Q1 | 1 | PNP, BCP53 family | `BCP5316MTWG` | by MPN |
| C1, C2, C3, C6, C7 | 5 | 100 nF X7R 0805 | `CL21B104KBCWPNC` | `1276-6557-1-ND` |
| C4 | 1 | 1 µF X7S 0805 | `CL21A105KBCLNNC` | by MPN |
| C5 | 1 | 10 nF X7R 0805 | `CL21B103KBANNNC` | by MPN |
| SJ1 | 1 | 0 Ω jumper 0805 | `RC0805JR-070RL` | by MPN |

**No ordered part — these are board features, not BOM line items:**
- **SW2** (LED OFF/ON/TINY) and **SB1–SB4** (per-LED disable) are **solder bridges** on the PCB.
- **TC1** is the **TC2030 footprint** — no soldered part; it mates with a TC2030-MCP pogo
  cable. **Do not load.**
- **J1 / JP1 / JP2** are **optional** 0.1″ headers — fit a header only if you want the wired
  UPDI / I²C / GPIO breakouts (TC1 is the primary programming path; JP1/JP2 are conveniences).
- **MH1–MH4** are plated drills — supply your own **M2 screws** if enclosing.

**Flags to clear before you buy:**
- **R1–R4 package — resolved in the BOM.** The placed land is **0402** (0.59 × 0.66 mm pads at
  1.02 mm pitch), and the BOM now matches it: **Yageo `RC0402FR-07150RL`**, 150 Ω 1% 0402. (The
  old line carried a stale **1206** part, `TNPW1206150RFEEA`, left over from v0's 1 kΩ ballast;
  a 1206 cannot solder to this land.) 1/16 W is ample here (~12 mW peak). The board footprint
  was correct and is unchanged — only the BOM moved. Every other R/C is 0805 and matches.
- **R1–R4 value (150 Ω) is `SIZED`, not locked.** It sets per-LED peak current (~9 mA on the
  clamped rail) and is **bench-pending** — the energy-budget test may re-tune it. Buy a small
  0402 range (e.g. 100 / 150 / 220 / 330 Ω) so you can swap after the measurement. For PCBA,
  any 0402 150 Ω 1% equivalent is fine.
- **SC1–SC4 are the dominant cost** (well over half the BOM). Confirm live pricing; they swing
  the whole board cost.

---

## Step 5 — Assembly order

Everything populates on the **back**; the front stays naked. Work outside-in by heat
sensitivity.

1. **Stencil + paste, then reflow the SMD parts.** Print paste, place, reflow (hot
   air / hotplate / oven). The **QFN-28 MCU (U1)** has an exposed pad that reflows to the GND
   plane, and the **LGA-12 accelerometer (U3)** has a ground pad under the body — both want
   paste and reflow, not iron-tinning. All the passives, the diodes, U2, U4, Q1, and the
   reverse-mount LEDs go down in this pass.
   - **LEDs are reverse-mount** (`LA P47F`) — they emit *down* through the FR4 to the front.
     Mind the cathode mark and the reverse footprint orientation; the cathode goes to `Kn` →
     ballast → `LDRVn`, the anode to the common `ANODE` node.
2. **Hand-solder the solar cells last (heat-sensitive).** PV1 / PV2 (`SM141K06TF`) are the
   most fragile parts: keep iron contact to **≤ 260 °C for ≤ 2 s per joint**, and **do not
   clean them with IPA** (it can damage the cell). Solder to the custom land; mind cell
   polarity.
3. **Set the LED master switch (SW2).** It is a 3-pad solder bridge — see
   `sw2-anode-selector.png`:
   - bridge **center–left (to VS) = ON** (full brightness),
   - bridge **center–right (to TINY) = TINY** (LEDs through R12 = dim, long runtime),
   - **unbridged = OFF** (a true hardware off — good for storage; supercap-safe).
   - Leave **SB1–SB4 bridged** unless you want to disable a specific LED channel.
4. **Tie VDDIO2 (SJ1).** SJ1 is the 0 Ω part above; it bonds VDDIO2 to VS (MVIO unused). Make
   sure it is placed/bridged, or PORTC has no I/O supply.

**Critical, do-not-get-wrong items** (full rationale in `../solar-glow-drh-design-notes.md`):

> - **Supercap land:** the WS17 cell solders to **flat pads under its body** — the
>   **asymmetric P/N widths (P = 7.8 mm, N = 12.2 mm) are the polarity key**. It does **not**
>   solder to the folded end tabs; those are coated, non-solderable mechanical locators.
>   Placement rotations as built: **SC1/SC4 = 90°, SC2/SC3 = 270°.** The wrong (end-tab) land
>   makes zero electrical contact — never substitute it.
> - **LEDs are reverse-mount**; an LED placed face-up will not glow through the board.
> - **Glow-window mask must be open** (Step 3) — a tented window kills the optics.

---

## Step 6 — First power & bring-up

1. **Measure the energy budget first — this is the project's #1 gate.** Before populating a
   second board, put the cells under your **actual target lighting** and measure **harvest
   current vs. LED draw**. That single number sizes the duty cycle and the feature set. (You
   can read the rail with the MCU's ADC against the internal reference during bring-up, then
   the real VSENSE divider once characterized.) See `../solar-glow-drh-design-notes.md` §2 and
   the open-question section in `../README.md`.
2. **Confirm SW2 is ON or TINY.** If SW2 is OFF, no firmware and no PWM will light the LEDs —
   that is the hardware master switch by design.
3. **Flash firmware over UPDI.** Use a **TC2030-MCP** pogo cable on `TC1` (hands-free), or
   solder a 3-pin header on `J1` as the backup. Firmware lives in **`../firmware/`** and is
   register-verified against the AVR64DD28 and LIS2DH12 datasheets; its knobs and wake model
   are in `../firmware/README.md`, and the pin map it targets is
   `../solar-glow-drh-v2-hardware.md`.
4. **Sanity-check the rail clamp.** The TLV431 + PNP shunt (U4/Q1) is meant to hold **VS ≤
   ~3.47 V** so the accelerometer stays inside its 3.6 V max. Verify VS does not climb past
   ~3.5 V under light before trusting the accelerometer.
5. **Bring up I²C and the accelerometer** at address **`0x18`** (firmware sets
   `TWIROUTEA = ALT2` → SDA/SCL on PC2/PC3), then confirm a physical **tap** fires the PF1/PF0
   interrupts. The accelerometer tap is the actuator — there is no button.

---

## Enclosure note

An optional machined-titanium back-shell is parked in `../enclosure/` (see its README and
`../solar-glow-drh-v2-mechanical.md`). It is **on ice until the board is validated**, and the
mechanical doc flags that the existing CAD must be **redesigned** against this four-supercap
board, not patched. Nothing about ordering or building the bare board depends on it.

---

*Part of SOLAR-GLOW · DRH. © 2026 Devin R. Horowitz. MIT License (see `../LICENSE`).*
