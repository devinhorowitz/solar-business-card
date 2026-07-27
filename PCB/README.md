# SOLAR-GLOW · DRH - PCB (v4.0): Order & Build Guide

![Generated/docs/solar-glow-drh-v4_0-bottom.png](https://github.com/devinhorowitz/solar-business-card/blob/main/Generated/docs/solar-glow-drh-v4_0-bottom.png)

This folder holds the **board** for SOLAR-GLOW · DRH — the KiCad project, the bill of
materials, and the artwork reference for the SW2 selector. It is the thing you fab and
populate. This README is the procedure: **how to order the bare PCB, how to order the
parts, and how to build the assembly.**

```
PCB/
├── solar-glow-drh-v4_0.kicad_pro     # KiCad project (open this)
├── solar-glow-drh-v4_0.kicad_sch     # schematic
├── solar-glow-drh-v4_0.kicad_pcb     # board — 2-layer, routed, teardropped (source of truth)
├── solar-glow-drh-v4_0.kicad_prl     # local project state
├── solar-glow-drh-v4_0.kicad_dru     # two-tier design rules (PCBWay floor + marginal band)
├── solar-glow-drh.kibot.yaml         # CI recipe — regenerates ../Generated/ on every push
├── solar-glow-drh-v4_0-BOM.xlsx      # bill of materials - v4.0 master (adds the AEM10300 harvest chain: U7 FRAM, U8 PMIC, U9 LDO, L2/FB1, C22–C28, R15–R17; mostly 0402, with C4/C13/C25/C27 on 0603 and SJ1 on its own 0R land)
├── solar-glow-drh-v4_0-BOM-assembly.xlsx  # trimmed PCBA BOM (36 placed parts)
├── sw2-anode-selector.png            # how to read/set the SW2 OFF/ON/TINY bridge
├── led-orientation-D2-D5.png         # reverse-mount LED rotation reference for PCBA
└── DRC.rpt / ERC.rpt                 # last GUI report exports (CI keeps live copies in ../Generated/)
                                      # (v2_1 / v2_2 / v2_3 revisions live in git history, not this folder)
```

> **The board is the source of truth.** `solar-glow-drh-v4_0.kicad_pcb` / `.kicad_sch`
> govern. The design *reasoning* lives one level up:
> - `../firmware/board.h` + `../firmware/README.md` - as-built pin map and net list (the firmware target); `../solar-glow-drh-v2-hardware.md` is frozen v2 lineage only.
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
| Components | **52 on the back**; the front carries only the two solar cells (PV1/PV2) |
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

1. Open `solar-glow-drh-v4_0.kicad_pro` in **KiCad** (designed in the 2026 file format).
2. Register the footprint library: the board uses a local `solarglow` library that is not
   registered on a fresh machine. Add it under **Preferences → Manage Footprint Libraries**
   (or accept KiCad's prompt) so the footprints resolve.
3. **Run DRC.** The project carries a two-tier rule file (`solar-glow-drh-v4_0.kicad_dru`):
   - **error tier** = the do-not-ship floor (clearance/track ≥ 0.126 mm, annular ≥ 0.125,
     drill ≥ 0.2) — sized against PCBWay's stated 2-layer capability;
   - **warning tier** = the *marginal band* [0.126, 0.1524): PCBWay-legal geometry that is
     tighter than 6 mil, flagged on purpose so the ledger stays visible.

   **Expected result: 0 errors, ~61 warnings, 3 exclusions.** The exclusions are the two
   gold-plating tie stubs crossing the outline and the LA↔LB coil junction — all intentional.
   The footprints that shipped without a courtyard (U1, U8, U5, U3, D2-D5, J1, TC1) now carry
   courtyards + pin-1/cathode markers. The one accepted courtyard overlap (the TC1 Tag-Connect
   over the SC1 supercap zone) is excluded in the KiCad DRC (`.kicad_pro`); courtyard-overlap is
   otherwise a hard CI gate. The two proximities this exposed (U8/L2, U1/J1) were resolved in the layout.
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
- Plated holes: the 79 vias (uniform 0.30 mm) and the eight M2 mount holes (Ø 2.2 mm; 4 corner MH1-4 + 4 panel-corner MP1-4).
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
| Vias | **Uniform: 0.30 mm drill / 0.60 mm pad** (0.15 mm annular), 79 total, tented (resin-fill + cap ordered board-wide) |
| Non-plated holes | TC2030: Ø **2.3749 mm** (4× leg-latch) and Ø **0.9906 mm** (3× alignment) |
| Plated mount holes | Ø **2.2 mm** ×4 (M2, corners, tied to GND) |
| Castellations | **None** (verified — only the corner mount holes sit within 1.5 mm of the rim) |

**Run PCBWay's DFM check against these.** The binding features are the **0.127 mm spacing**
and **0.15 mm tracks** — inside PCBWay's stated 0.1 mm/4 mil 2-layer capability, but worth a
glance at their sheet. There are no fine vias on this board (the whole board runs the one 0.30/0.60
via), and no controlled-impedance nets to declare.

**Add to the order notes / gerber review:**
- "**Leave soldermask open over the central window per the mask layers — do not tent or
  flood.**" (The bare-FR4 + open-ENIG window is the whole optical trick.)
- "**Keep vias tented.**"
- **Selective hard gold (the reason the plating bus exists):** paste this verbatim into the
  special-request box —

  > *"Selective hard gold plating on top side, MASKED BY AREA, not by net: plate the DRH monogram
  > field, the perimeter frame, and the six edge ornament shapes — these are the SOLID artwork
  > shapes on F.Cu. Everything else exposed on the top side stays ENIG, including the 45°
  > crosshatched ground pour (0.2 mm strands on a 0.7 mm pitch) that surrounds and abuts the frame
  > and ornaments. The crosshatch and the frame are continuous copper in places, so the gold
  > boundary is the artwork outline, NOT a copper-connectivity boundary — where a hatch strand runs
  > inside the frame/ornament outline, plating it gold is correct and expected. Do not attempt to
  > gold the crosshatch field itself: it is a fine mesh and hard gold on it would band with plating
  > current density. The two 0.25 mm traces crossing the board outline at x=25.4 (top and bottom
  > edges) are plating-bus connections; please retain to panel rail and rout at depanel. The gold
  > set is GND-referenced by design (the four M2 mounting-hole pads overlap the frame at all four
  > corners); not floating copper, not a defect. All in-pad vias: resin-filled and copper-capped
  > (POFV, IPC-4761 Type VII)."*

  A DFM reviewer will flag copper-to-edge = 0 at the two stubs; that is by design. (Geometry
  re-verified against the committed board 2026-07-02: the gold set is a single connected F.Cu
  component, both stubs + all four corner M2 GND pads on it (the 4 panel-corner MP1-4 holes are GND but not on the front gold set); everything else exposed on F is the solar
  lands, which stay ENIG.) Ordering plain ENIG without this request leaves the bus as dead
  copper and no wear surface on the face — do not ship without it.

  > **Why the wording changed (2026-07-27, the crosshatch upload).** The request used to say the
  > gold set was "**all connected copper on F.Cu**." That phrasing was safe while the GND pour
  > merely grazed the artwork — they touched over **0.069 mm²**. The crosshatch rework enlarged the
  > pour outline to 0.5 mm from the board edge, and the pour now overlaps the artwork by
  > **157.3 mm²**, i.e. **52% of the frame + ornament copper (157.3 of 303.8 mm²)**. Read literally,
  > the old sentence would have told the fab to gold ~2,400 mm² of hatched pour instead of the
  > 387.5 mm² artwork. **The monogram field is unaffected** — it sits inside the `optical_window`
  > keepout, which the pour cannot enter, so its overlap is exactly 0.00 mm².
  >
  > Selective plating masks by *area* (a photoimaged plating resist), not by net, so a shared-copper
  > boundary is still platable — the request just has to say where the boundary is. That is what the
  > new wording does. **Durable fix, if you want one:** draw the gold area on a dedicated user layer
  > (`User.1`, empty today) and plot it as its own gerber, so the region is defined by artwork rather
  > than by prose and cannot drift again the next time a pour outline moves. Not done here.
- "**The LA/LB track crossing at (41.0, 38.0) is the NFC coil junction — intentional.**"
- **Bench pad strip (`TP1` + `JP1`, back east edge, x 48.4):** five bare 1.7 mm SMD probe pads
  (SRC / GND / STO / SCL / SDA at 2.54 pitch) - no component; they are in the mark-as-DNP list
  above. Pinout and the bench-power ritual live in `solar-glow-drh-v2-hardware.md` (note: that frozen doc predates the v3->v4 VS->STO change, so JP1.2 is now the STO tank node, not the VS rail).
- **Via-in-pad -- several vias land inside pads** on this board: the soldered pads (`TC1.1`, `U1.EP`,
  `U5.1`, `SW2.1`, `J1.2`, `PV1.N`, `PV2.N`, `PV2.Nt`)  [D1.K and R13.2 removed - D1 and R13 are not on the v4 board; re-verify the full via-in-pad set against the v4 layout, since v4 added U7/U8/U9/L2/FB1] plus 2 in the bench-strip
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

> **What the stencil deliberately does NOT open (2026-07-26).** Paste has been removed from the
> pads of every part that is not reflowed, so the stencil only opens where paste is wanted:
>
> | | pads | why |
> |---|---|---|
> | **PV1, PV2** (solar cells) | 8 | hand-soldered, consigned; **4 pads each** — a Ø3.5 mm terminal plus a 4 × 3 mm tab 3.1 mm outboard |
> | **SC1–SC4** (supercaps) | 8 | hand-soldered to the under-body P/N pads |
> | 10 DNP parts + **TC1** | 29 | not placed / pogo contacts must stay bare |
>
> The PV and SC pads alone are **≈ 366 mm² of aperture** — the largest on the board by a wide
> margin, equivalent to about 1,200 0402 pads. Reflowing that much paste under parts meant to be
> hand-soldered is not a small waste: it is enough solder volume to float the part.
> **Copper and mask are untouched** — only the paste layer was removed, so every pad solders by
> hand exactly as before.

---

## Step 4 — Order the parts

**BOM state.** The masters are now **`solar-glow-drh-v4_0-BOM.xlsx`** and
**`solar-glow-drh-v4_0-BOM-assembly.xlsx`**, reworked for the v4.0 managed-solar redesign - the passive diode/shunt/comparator parts (U2, U4, Q1, D1, D9–D11, R7–R9) are removed and the AEM10300 harvest chain (U7, U8, U9, L2, FB1, C22–C28, R15–R17) is added, on top of the earlier fixes:
**U6 (TPS22917DBVT since the 2026-07-23 dark-current swap) and R14 (1 M `NFC_EN` pulldown) added**, the stale **JP1/JP2 rows dropped** (the `JP1` designator is reused for the v3.0 bench pad strip — bare pads, not a BOM part)
(those headers left the board in v3.0), and **most passives converted to 0402** to match the board's placed lands — the v2.2 file still
listed 0805 MPNs for most R/C. _(Updated 2026-07-25: the 2026-07-23 longevity/precision passes moved
several off 0402 — **0603**: C4, C13, C25, C22, C23, R5, R6, R15, R16; **0805**: C26, C27. SJ1's 0R
land is now **DNP**. New parts since: **Q2** (SOT-23) + **R18** (0402). The table below is the
current truth.)_ Converted and added
lines had their prices blanked at the time; **that is no longer true — every ordered line is now
live-priced** (full DigiKey/Mouser sourcing pass, 2026-07-23, subtotal ≈ $140). The `v2 2` and older
BOM files remain in git history as lineage.

Summary of the **orderable** lines:

> **Derived snapshot, regenerated from the BOM master 2026-07-25.** The master is
> `solar-glow-drh-v4_0-BOM.xlsx` (with `-BOM-assembly.xlsx` for the machine-place set) — order
> from those, not from this table. This copy had drifted badly (it still listed the pre-swap
> `AVR64DD28-I/STX`, `TPS22918DBVR`, the SOIC-8 FRAM and the pre-longevity-pass passives), so
> treat any disagreement as this table being wrong.

| Ref(s) | Qty | Value | Package | MPN |
|---|---:|---|---|---|
| U1 | 1 | AVR64EA28, 64 KB, 20 MHz | VQFN-28 (4×4×1.0 mm, w/ EP) | `AVR64EA28-E/STX` |
| PV1, PV2 | 2 | Voc 4.15 V, 184 mW, mono, 1.2 mm thick | 42×23×1.2 mm, custom land | `SM141K06TF` |
| SC1, SC3 | 2 | 1.8 F, 2.75 V (SS17) | SS17 (under-body P/N pads, 39 mm) | `3-153-440` |
| SC2, SC4 | 2 | 1.0 F, 2.75 V (WS17) | WS17 (under-body P/N pads, 28.5 mm) | `3-153-438` |
| D2–D5 | 4 | Amber 617 nm, Vf≈2.25 V | SMD, 3.4x1.9 mm | `LA P47F-V2BB-24-3B5A-30-R18-Z` |
| R1–R4 | 4 | 150 Ω, ±1% | 0402 | `AC0402FR-07150RL` |
| R12 | 1 | 220 Ω, ±1% | 0402 | `AC0402FR-07220RL` |
| R5, R6 | 2 | 1 MΩ, ±0.1%, 25 ppm, 0603 | 0603 (R_0603_1608Metric) | `RT0603BRD071ML` |
| C5 | 1 | 100 nF, X7R, 50 V | 0402 | `GRT155R71H104KE01D` |
| U3 | 1 | I²C 0x1D, ±2–8 g | LGA-12 CC-12-4 (2.2×2.3×0.87 mm) | `ADXL367BCCZ-RL7` |
| R10, R11 | 2 | 4.7 kΩ, ±1% | 0402 | `AC0402FR-074K7L` |
| C1 | 1 | 100 nF, X7R, 50 V | 0402 | `GRT155R71H104KE01D` |
| C3 | 1 | 100 nF, X7R, 50 V | 0402 | `GRT155R71H104KE01D` |
| C4 | 1 | 10 µF, X5R, 16 V | 0603 | `GRT188R61C106KE13D` |
| C6 | 1 | 100 nF, X7R, 50 V | 0402 | `GRT155R71H104KE01D` |
| C11 | 1 | 0.22 µF (220 nF), X7R, 16 V | 0402 | `GRT155R71C224KE01D` |
| C12 | 1 | 100 nF, X7R, 50 V | 0402 | `GRT155R71H104KE01D` |
| C7 | 1 | 100 nF, X7R, 50 V | 0402 | `GRT155R71H104KE01D` |
| SJ1 | 1 | DNP (was 0 Ω jumper) | 0805 | **(DNP - not ordered)** |
| SW2 | 1 | 3-pad bridge | solder-bridge | **(none — PCB bridge)** |
| SB1–SB4 | 4 | solder-bridge | solder-bridge | **(none — PCB bridge)** |
| TC1 | 1 | TC2030-MCP-FP | TC2030 legged land | **(no part — pogo interface)** |
| J1 | 1 | 1×3, 0.1″ | 0.1″ THT pads | **(unpopulated / 0.1″ header)** |
| JP1 | 1 | 4× bare SMD pads | 1.7 mm sq, 2.54 mm pitch, B side | **(bare pads — no component)** |
| TP1 | 1 | 1× bare SMD pad | 1.7 mm sq, B side | **(bare pad — no component)** |
| MH1–MH4 | 4 | M2 | 2.2 mm plated | **(no part — drill)** |
| U5 | 1 | NTAG I²C plus, 2 KB, I²C 0x55 | XQFN8 (SOT902-3, 1.6×1.6×0.5 mm) | `NT3H2211W0FHKH` |
| C8 | 1 | 100 nF, X7R, 50 V | 0402 | `GRT155R71H104KE01D` |
| C9 | 1 | DNP (NP0/C0G land) | 0402 (NP0/C0G land) | **(DNP — not ordered)** |
| C13 | 1 | 10 µF, X5R, 16 V | 0603 | `GRT188R61C106KE13D` |
| L1 | 1 | 2.76 µH design value | PCB copper — no package | **(no part — PCB feature)** |
| U6 | 1 | Ultra-low-leakage load switch | SOT-23-6 (DBV) | `TPS22917DBVT` |
| R14 | 1 | 1 MΩ, ±1% | 0402 | `AC0402FR-071ML` |
| U8 | 1 | AEM10300 | QFN-28 (4x4 mm, EP land 2.30) | `10AEM10300C0000` |
| U9 | 1 | TPS7A0233, 3.3 V, ~25 nA Iq | SOT-23-5 | `TPS7A0233PDBVR` |
| U7 | 1 | MB85RC512TY | DFN-8 LCC-8P-M05 (5.0×6.0×0.90 mm MAX, 1.27 mm pitch) | `MB85RC512TYPN-GS-AWEWE1` |
| L2 | 1 | 10 uH | 1008/2520 (L_1008_2520Metric), 2.5x2.0 mm | `DFE252010F-100M` |
| FB1 | 1 | 0603 bead | 0603 | `BLM18PG221SN1D` |
| C22 | 1 | 1 uF, 25 V, 0603, X7R | 0603 (C_0603_1608Metric) | `GRT188R71E105KE13D` |
| C23 | 1 | 2.2 µF, 25 V, 0603, X7R | 0603 (C_0603_1608Metric) | `GRM188Z71E225ME43D` |
| C24 | 1 | 100 nF, 0402, X7R | 0402 | `GRT155R71H104KE01D` |
| C25 | 1 | 22 uF, 10 V, 0603, X5R | 0603 | `GRT188R61A226ME13D` |
| C26, C27 | 2 | 10 µF, 10 V, 0805, X7R | 0805 (C_0805_2012Metric) | `GRM21BR71A106KA73L` |
| C28 | 1 | 100 nF, 0402, X7R | 0402 | `GRT155R71H104KE01D` |
| R15 | 1 | 2 M, 0603, ±0.1%, 25 ppm | 0603 (R_0603_1608Metric) | `MCT0603MD2004BP500` |
| R16 | 1 | 1 M, 0603, ±0.1%, 25 ppm | 0603 (R_0603_1608Metric) | `RT0603BRD071ML` |
| R17, R18 | 2 | 1 M, 0402, ±1% | 0402 | `AC0402FR-071ML` |
| Q2 | 1 | N-ch MOSFET, 60 V, logic-level | SOT-23 | `BSS138LT1G` |

**No ordered part — these are board features, not BOM line items:**
- **SW2** (LED OFF/ON/TINY) and **SB1–SB4** (per-LED force-on) are **solder bridges** on the PCB.
- **The NFC antenna is etched copper** — no wound coil to buy.
- **TC1** is the **TC2030 footprint** — no soldered part; it mates with a TC2030-MCP pogo
  cable. **Do not load.**
- **J1** is an **optional** 0.1″ UPDI header — TC1 is the primary programming path.
- **MH1–MH4** are plated drills — supply your own **M2 screws** if enclosing.

**Flags to clear before you buy:**
- **R1–R4 value (150 Ω) is `SIZED`, not locked.** It sets per-LED peak current and is
  **bench-pending** — the energy-budget test may re-tune it. Buy a small 0402 range
  (e.g. 100 / 150 / 220 / 330 Ω) so you can swap after the measurement.
  *(Corrected 2026-07-26 PCB audit: this used to read "~9 mA on the clamped rail", a stale
  v3 figure — v3 fed the LED anodes from a rail the TLV3011B held near 3.5 V, giving
  (3.5−2.25)/150 ≈ 8.3 mA. v4 deleted that clamp: SW2 now feeds ANODE straight from STO, so
  the peak is (STO−Vf)/150 ≈ **14–18 mA** near the 4.65 V VOVCH ceiling — the LA P47F's Vf
  is itself unbinned across the 3B–5A groups, 1.95–2.55 V at 30 mA. The firmware
  (board.h/led.h) already assumes the v4 number; this line did not.)*
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
- **PCBWay machine-places** (reflow, bottom): U1, U3, U5–U9, Q2, D2–D5, R1–R6, R10–R12, R14–R18, L2, FB1,
  C1, C3–C8, C11–C13, C22–C28. (Recompute the placed count from the v4 board; the v3 clamp/comparator
  parts - U2, U4, Q1, D1, D9–D11, R7–R9, C2, C10 - are gone.)
  *(Corrected 2026-07-26: **SJ1 removed** from this list — it is DNP/not-ordered and must be left open,
  so it is never placed; the DNP attribute now says so in both the .kicad_sch and .kicad_pcb. **Q2 and
  R18 added** — the charge-disable buffer from the cold-start-deadlock fix. **U7 is correctly in this
  list**: it carried a stray DNP attribute in the .kicad_pcb, now cleared so the board agrees with the
  schematic. That flag did not affect this project's fab output — the CI pick+place CSV is informational
  and already listed U7 — but the two files must agree, since a schematic sync overwrites the board.)* `solar-glow-drh-v4_0-BOM-assembly.xlsx` is
  that trimmed file - **regenerate it from the v4 board** so it reflects the v4 placed set.
- **You hand-solder afterward:** SC1–SC4 supercaps and PV1–PV2 solar cells. They are kept
  **off** the PCBA BOM on purpose — the supercaps are manual-solder only (SCHURTER SCPC),
  and the cells are heat-sensitive.
- **Not placed:** SW2, SB1–SB4 (solder bridges you set), TC1 (Tag-Connect pad), J1
  (optional header), MH1–MH4 (mounting holes), C9 (DNP).

**Sourcing:** turnkey, with the standing instruction that anything PCBWay can't source they
flag and you consign from DigiKey — **no substitutes without approval**. The likeliest to
need consigning are **U1** (AVR64EA28-E/STX), **U8** (AEM10300 - e-peas harvest PMIC, source early), **U5** (NT3H2211 - going
end-of-life in places; check stock early), and **D2–D5** (the ams OSRAM amber bin — confirm
the exact reverse-mount P/N, OSRAM sells top-emit lookalikes).

**Files handed to PCBWay:** the trimmed assembly BOM, the **centroid / pick-and-place**
(KiCad → Fabrication Outputs → Component Placement; **CSV, mm, exclude-DNP** after marking
SC1–SC4 / PV1–PV2 / J1 / C9 / JP1 / TP1 as DNP; **Absolute origin** to match the drills), and
`led-orientation-D2-D5.png`.

**Order-form settings that matter:** bottom side, qty 5, ENIG **+ selective hard gold (special request above)** / matte-black / white silk,
**resin-fill + via-in-pad** (cleans the 10 via-in-pad joints and keeps the TC1 pogo pad
flat), **moisture-sensitive = U1 / U3 / U5** (U3 is a MEMS part - observe peak reflow
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
5. **SJ1 must be LEFT OPEN (DNP).** ⚠️ This reversed in the 2026-07 AVR-EA swap: SJ1 was the
   VDDIO2→VS tie for the AVR64DD28, but on the **AVR64EA28 pin 10 is plain `PD0`**, not VDDIO2 —
   there is no MVIO and no I/O-supply pin to feed. Bridging SJ1 would tie a GPIO to VS. The land
   stays on the board as a spare only if the DD is ever reinstated. (PORTC needs no separate
   supply on the EA; it runs off the main rail.)

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
   `../firmware/board.h` (with `../firmware/README.md`) - where the v4 additions PA4=EN_STO_CH and PD1=STO_SNS are recorded.
   > **Programming caution:** `NFC_EN` (PA7) now has a **1 MΩ pulldown (`R14`)** — U6
   > defaults hard-off while PA7 floats during reset / UPDI. Still drive PA7 low early in
   > init as belt-and-suspenders. The **U6 pin-map check is done** — TI SLVSD76C
   > (`../datasheets/U6  TPS22918DBVR  $0.55.pdf` — the *then*-fitted part; U6 is now the
   > pin-identical `TPS22917DBVT`, see `../datasheets/U6  TPS22917DBVT  $1.14.pdf`) showed the symbol had **VIN/VOUT and GND/QOD
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
