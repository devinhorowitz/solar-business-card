# SOLAR-GLOW · DRH — design notes & posterity

Durable engineering rationale, hard-won findings, and future-variant ideas, distilled from the v0/v1 planning docs (since retired).

**Authority order.** For the *current* design, the committed `solar-glow-drh-v3_0.kicad_pcb` /
`.kicad_sch` (v3.0, 2-layer) plus `README.md`'s current-revision table are ground truth; the 4-layer
`solar-glow-drh-v2_3.kicad_pcb` is the committed fallback. This file is the *reasoning archive* — the
"why" and the "don't do that again" — with the **v3.0 deltas collected in §12**. Where an as-built
doc already owns a topic, this points at it rather than duplicating. (The `solar-glow-drh-v2-*` docs
are v2-era; their v3.0 deltas are banner-noted at their tops.)

---

## 1. The supercap land — the landmine (never reintroduce the old one)

**The v0/REV-J supercap land was WRONG — confirmed against physical parts.** It placed two
3.5 × 3.5 mm pads on a diagonal (36.5 × 16 pattern, centres ±16.5 / ±6.25) that land on the cell's
folded **end tabs**. Those tabs are coated, **non-solderable** mechanical locators, so a board built
to that land makes **zero electrical contact**. The root cause: the datasheet's single generic
"Soldering pads to Case WS10/13/17" diagram (`datasheets/typ_SCPC-2.pdf`) was misread as the WS17
land.

**The correct land (LOCKED).** The real solderable terminals are flat pads **under the body**:

- **P (positive) pad: 7.8 × 3.5 mm**
- **N (negative) pad: 12.2 × 3.5 mm** — the asymmetric widths are the **polarity key**
- Both centred on the cell axis at **±11 mm** from cell centre, ~1.5 mm in from each end, inside the
  28.5 × 17 mm body.
- Protruding end tabs are finish-coated locators only — **not** solder pads.
- Placement rotations as built: SC1/SC4 → 90°, SC2/SC3 → 270°.

Part: **SCHURTER SCPC 3-153-438** (WS17 housing, 1 F, 2.75 V, ESR 40 mΩ, 1.7 mm thick). The
diagonal end-tab land **must never be reintroduced**.

---

## 2. Power-budget model (the framework + the one open gate)

The honest energy model, and the reason a bench bring-up gates any feature decision:

- **Continuous sustainable average draw ≤ harvest.** This — not the cap size — sets the brightness
  you can hold *forever*. Indoor harvest is roughly **0.1–0.5 mA at the rail** (the SM141K06x panel
  is ~185 mW at 1 sun; ordinary office light is 100–500× less).
- **The reserve buys excursions, not steady-state.** The ~15 J tank is how long/bright you can
  *exceed* harvest before it drains, and how long the glow rides through darkness. Recharge scales
  with it: ~15 J / ~1.6 mW ≈ **hours** to refill from empty on office light. A bigger tank = longer
  dark glow **and** longer cold-start. This is the "diminishing returns" point: a 2× bucket buffers
  dark ~2× longer but cold-starts ~2× slower — it **buffers a deficit, it does not cure** the
  harvest-vs-draw ratio.

| reserve | sustained draw it supports |
|---|---|
| v0: 2× WS10, ~150 mF, ~2.3 J | ≤ harvest; ~40–60 s breathing / ~10–15 min refill |
| v2.1: 4× WS17, 1 F @ 5.5 V, ~15 J | ≤ harvest; minutes of breathing per charge; refill ~hours |

**Draw line items** (budget against harvest): accel ≈ **10 µA** (a click-armed LIS2DH12 runs at
100 Hz to time taps — it can't sit at the ~1 µA slow-ODR figure the old docs assumed, so this is
now the dominant always-on load and pegs dark-survival at ~half a day); light-sense divider
sub-µA; MCU sleep ≈ 0.65 µA (AVR-DD power-down, `PMODE=AUTO`). The LEDs are the only mA-scale
load. See `firmware/README.md` "Power notes" for the corrected model.

> **Ballast caveat — re-derive the LED numbers for v2.1.** The LED-draw figures used throughout the
> old docs (≈5 mA for 4 LEDs full-on, ≈3 mA breathing, +1.25 mA per added LED) were computed at
> v0's **1 kΩ** ballast. The v2.1 BOM carries a **different ballast (150 Ω, flagged bench-pending)**,
> which at the same ~3.47 V rail raises per-LED current several-fold. The schematic leaves R1–R4 as a
> "LED ballast" placeholder, so the BOM is the source of truth for the value. **Re-derive draw and
> duty against the final ballast before trusting any duty-cycle percentage below.**

**Conclusion to test (at 1 kΩ; rescale for the final ballast):** continuous full breathing is *not*
sustainable on office light (~10× short). The natural indoor mode is **harvest-and-pulse (~6–10%
duty)** or **continuous dim (1 LED)**. Continuous full breathing needs a windowsill / daylight.

**#1 open empirical gate: measure real harvest.** Use the **VDD-proxy ADC** during bring-up (read
the rail against the internal reference — it charges in light, sags under load), then the real
light-sense divider once characterised. That single measurement sizes the whole feature envelope.

---

## 3. Glow design + the template concept

- **Glow keepout = one rectangle: x 14.95–35.85, y 40.8–47.0** (the DRH window, ≈20.9 × 6.2 mm).
  It **voids every copper layer** so bare FR4 passes diffuse light. Inside it: **tracks allowed, but
  NO vias, NO copper pour, NO footprints.** Plane voids must be deliberate so the window does not
  *fragment* the GND/VS planes — route supercap power **around** the band, never through it. LED
  anodes that sit inside the window trace out (north of y40.8 or south of y47) before via-ing to a
  plane.
- **Light couples into a stroke only within ~0.7 mm on thin FR4.** So the four Ø1.64 mm LED entry
  windows must **nestle a letter boundary** (snug against the strokes, not centred in a wide gap, or
  the LED is buried under copper and that window dies). The initials are track-widened
  (~0.12 → ~0.23, ~2.5 mm inter-letter gaps) to put a stroke edge at each fixed window.
- **The keepaway is a single letter-agnostic box → the design is a TEMPLATE.** Anyone can drop their
  own initials into the box and keep the four fixed centreline windows. (See
  `docs/solar-glow-drh-glow-window.png`.)
- **FR4 thickness drives the look.** Thinner FR4 spreads light *less* → a crisper, more edge-lit
  monogram (brightest at the strokes nearest each window); thicker diffuses more. **Validate the
  *look* on a coupon of the ACTUAL board thickness** — a coupon of a different thickness will not
  predict it. (v2.1 is 0.8 mm, the same as v0, so v0 *does* predict v2.1; the old "validate the
  0.4 mm look" gate is moot now that the board is 0.8 mm.)
- **A diffuser film is the lever for full-letter evenness** — including lighting the D/R *bowls* —
  not more boundary LEDs.

---

## 4. Rear real-estate constraint + layout strategy

The glow is **central and rear-facing**, which is exactly where the four big cells want to sit:

- 4 × (28.5 × 17 mm) cells = **~43%** of the 50.8 × 88.9 board.
- Decorative silk *can* hide under the cells. The **LEDs are on the same rear side as the cells and
  cannot** — and the monogram tracks the LEDs. So a **protected central glow band (~17 mm)** is
  reserved through the centre, and the cells go around it. This is the first thing to settle in any
  re-spin and the real cost of four cells: the glow and the energy tank compete for the same rear
  centre.
- **Layout strategy: mirror the top supercap pair to the bottom** (reuses the proven footprint and
  its routing). Both pairs join the **same VS / MID / GND nets** (SC3 ∥ SC1, SC4 ∥ SC2) → **1 F @
  5.5 V on a single MID node**, so **U2 alone does all the balancing — no second balancer**. The MID
  net runs the length of the board (cheap on planes) to tie both midpoints.
- **Mounting holes at all four corners.** Inboard screws leave the ends of the 89 mm card
  unsupported — bad for a stiff metal back-plate. Keep M2 engagement at the corners.

**Routing hotspots (where a re-spin will be slow):** (1) the U1 QFN-28 escape — LDRV1–4, UPDI, SDA,
SCL, BTN, VSENSE all leave the same two edges; fan out in pin order, get the VDD/GND/EP plane vias in
first. (2) The MID bus around the glow void. (3) TC1 threaded under SC1. (4) The BTN-to-switch long
net + its layer change. Hand-polygon routing is fine for a prototype but **final copper sign-off
belongs in KiCad** (push-shove router, real thermal reliefs, exact mask expansion).

---

## 5. MCU selection — AVR64DD28 in 28-VQFN (the rationale)

- **Why this part:** **MVIO** (PORTC can run on a separate VDDIO2 — attractive for a mixed-voltage
  rail), **ADC** (light-sense), flexible **TCA/TCB/TCD** PWM (LED breathing / more LEDs), and
  **22 I/O** of headroom. *(As-built, the separate-voltage mode is **not** used: the shunt clamp
  holds the whole VS rail ≤ 3.47 V and VDDIO2 is tied to VS via SJ1, so the accel is protected by
  the clamp rather than by MVIO. Set the `SYSCFG1.MVSYSCFG` fuse to SINGLE — see firmware README
  "Fuses".)*
- **Why VQFN, not SSOP-28:** height is irrelevant (U2 at 1.75 mm sets the cavity floor; the QFN is
  0.9 mm). The binding constraint is **X/Y footprint** — with the cells eating ~43% of the board, the
  QFN's ~16 mm² land beats SSOP-28's ~50 mm². Cost: hot-air + paste, EP reflowed to GND (same as the
  v0 QFN-20).
- **Power-down: 0.65 µA typ** (DS40002315 Table 38-5, `VREGCTRL.PMODE = AUTO`, 3 V/25 °C; +0.6 µA
  for a 32 kHz wake source). That is ~6× the old tinyAVR's 0.1 µA, but still sub-µA and swamped by
  supercap + U2-balancer leakage (µA-class). **Firmware must-do: `PMODE = AUTO` for sleep — FULL
  mode is 160 µA (250×) and would dominate the standby budget.**
- **No AVDD on the 28-pin:** the ADC runs off VDD, so analog cleanliness rides on the VS plane +
  decoupling. θJA ≈ 36.5 °C/W.
- **No PTC:** the AVR-DD has no hardware cap-touch — and a grounded metal back-plate would kill
  self-cap anyway — so **the actuator is the accelerometer tap**, not cap-touch.

(Candidates weighed and rejected: tinyAVR-1/-2 and ATtiny1627/3217 all match the old part on power
but are feature *trades* or lack MVIO; the AVR-DD was the only superset that solves the mixed-voltage
I²C cleanly.)

---

## 6. Firmware ideas worth remembering (beyond the bring-up doc)

All firmware-only, no board change:

- **LED hardware-PWM** for brightness / breathing / fade — big supercap-runtime savings at low duty.
- **CCL + EVSYS could run a glow/blink pattern while the CPU sleeps** — autonomous show, CPU stays
  in low power. *(As-built, the firmware instead IDLE-sleeps through the breath while TCA0 runs the
  PWM; a fully autonomous CCL + EVSYS glow remains a v-next idea.)*
- **RTC/PIT off the internal 32 kHz ULP** (no crystal) for periodic wake.
- **EEPROM "times-activated" counter** that survives a full supercap drain.
- **AC0 wake-on-light — *tried, non-viable on this part.*** The idea (AC0 comparator on the sense
  pin, `MUXNEG = DACREF` for the threshold, AC edge wakes from sleep) was checked against the
  datasheet during firmware bring-up and **doesn't work here**: the AC interrupt doesn't update
  with the peripheral clock stopped, and the AC isn't a Standby/Power-Down wake source, so it would
  never fire. Wake-on-light is instead the **RTC-timed ADC poll** (deep Power-Down), and instant
  pickup response comes from the **accelerometer interrupt**. See the corrected
  `solar-glow-drh-v2-hardware.md` §6 and `firmware/README.md`.
- **Internal temperature sensor** is available if wanted.

Not useful on this part: ZCD (mains only), op-amps (the DD family lacks them), PTC cap-touch (see §5).

---

## 7. Enclosure — board-side rules to honor now (full detail in enclosure/README.md)

The Ti rear-shell is parked, but a few rules must be baked into the board so it never needs a
re-spin for the enclosure:

- **Grounded body → short risk.** In the enclosed variant, **drop the right-edge castellations**;
  land support pillars **only on GND pour**; keep a **die-cut Kapton (~0.05 mm)** blanket isolation
  layer in reserve if a later via audit on the rib lines finds an untented via.
- **General cavity 1.85 mm (cap-limited), plus a U2 relief pocket** — the four **1.70 mm WS17
  supercaps** set the general cavity (1.85 = cap + 0.15 mm air, toleranced 1.85 ±0.05). U2 (SOIC-8,
  1.75 mm) is the single tallest part but sits over a **local 0.05 mm relief pocket** (floor 0.70 mm
  there vs 0.75 general), so it keeps its full 0.15 mm air while the general cavity stays 1.85. The
  0.9 mm QFN is irrelevant. ("Cells" elsewhere can mean the 1.2 mm **solar** cells on the front — a
  different part; don't conflate the two.)
- **No tall back-side parts.** The cavity budget assumes the tallest *populated* rear part is U2 at
  1.75 mm. Keep the 2.54 mm breakout headers (JP1/JP2) **unpopulated** in the enclosed build — a
  populated 0.1 in header is ~8 mm and the shell will not close. J1/TC2030 are flat back-side pads.
- **The button is the accel tap** (cap-touch dies behind a grounded plate; the old "snap-dome"
  actuator is superseded).
- **Shell, current approach (v3.0):** Ti-6Al-4V Grade 5, **fully 3-axis CNC-milled** (no etching),
  **bead-blast** finish, with a **0.75 mm floor** (0.70 under the U2 pocket) backed by two ribs — the
  brace posts are **removed** — and the reflector frame **laser-marked, not cut**. Overall height
  3.55 mm; the four bosses sit on the **v3.0 hole pattern** (concentric with the r3.0 fillets),
  retained by four corner M2 screws (~2.2 mm Ti engagement). The earlier 0.3 mm-skin / 7075-fallback /
  photochemical-etch plan is dropped. Full CAD, callouts, and fab notes are in `enclosure/README.md`.

---

## 8. Fab / assembly craft

- **Via-in-pad on small, normally-soldered parts will wick solder** — VIPPO (resin-fill + cap) or
  dog-bone them. From the v0/v1 layout, the genuine at-risk set beyond the existing VIPPO list
  (U2, U4, Q1, TC1.1/2/3, JP2, D9.A, R2.2) was **C6, R1, R3, R4, R5**. Large pads / ICs / EP / flooded
  solder-bridge pads (SB/SJ/SW) / robust header joints (JP/J1) reflow fine and need no fill.
  **Re-confirm the actual in-pad-via set against the committed KiCad board** — the old list was tied
  to the generator's dog-bone routine, not the KiCad layout. **v3.0 resolves this: all in-pad vias are
  resin-filled + copper-capped (POFV) board-wide** (§12), so the point is moot.
- **TC2030 (Tag-Connect) footprint rules:** use the **official KiCad `Tag-Connect_TC2030-IDC-FP`**
  (Connectors.pretty; board-side == TC2030-MCP-FP) — do **not** hand-draw. 6 contact pads
  Ø0.7874 mm at 1.27 mm pitch (pins 1=UPDI, 2=VS, 3=GND, 4–6 NC), F.Cu+F.Mask, **no paste**; 4
  leg-latch holes Ø2.3749 mm NPTH (the hands-free latch); 3 alignment holes Ø0.9906 mm NPTH. **Contact
  pads must stay SOLID for the spring pins** (no hole > 0.008") → VIPPO TC1.1/2/3, or plate the 3
  alignment holes and route VS/GND to them to keep the pads hole-free. Keep-out: no tracks/vias in the
  shaded area, no signal within 0.508 mm of a contact pad. **DNL** in the BOM (pogo connector, never
  soldered).
- **Production Gerbers come from KiCad's own fabrication-outputs exporter**, not from any preview
  emitter. A geometry-derived preview is great for review but lacks thermal-relief spokes, exact mask
  expansion, and real NFPR.

---

## 9. Design evolution (v0 → v1 plan → v2.1 as-built)

Recorded so the history is legible and the dead branches stay dead:

| topic | v0 (REV J) | v1 plan | **v2.1 as-built** |
|---|---|---|---|
| Stackup | 2-layer, 0.8 mm | 4-layer, 0.4 mm | **6-layer, 0.8 mm** (L1 sig · L2 GND · L3–4 sig · L5 VS · L6 sig) |
| Storage | 2× WS10, ~2.3 J | 4× WS17 2P2S, ~15 J | **4× WS17 2P2S, 1 F @ 5.5 V, ~15 J** |
| Accel rail handling | n/a | planned LDO (TPS7A02) for the 3.6 V-max accel | **TLV431B shunt clamp holds VS ≤ 3.47 V** (no LDO) |
| Accelerometer | none | BMA400 / LIS2DW12 (candidates) | **LIS2DH12, I²C addr 0x18** |
| Button | snap-dome / cap-touch | dome (cap-touch expendable) | **accel tap-wake** |
| Solar | SM141K06L (1.8 mm) | SM141K06L | **SM141K06TF (1.2 mm)** — electrically identical, thinner |
| LED ballast | 1 kΩ | 1 kΩ | **150 Ω per BOM (bench-pending)** — rescale the energy budget (§2) |
| VSENSE pin | — | PA5, later proposed PC3 | **PD2 (AIN2 + AINP0)** |
| LED timer | TCA0 | TCA0, briefly proposed TCD0 | **TCA0 split, WO0–WO3 = PA0–PA3** |

v0 also carried a dual-coin-cell charging option (BT1/BT2 + diodes); **dropped in v2.1** (solar-only).

**Since v2.1** (placements, BOM, and the glow window are unchanged throughout — only the stackup and
the LDRV fan moved):

| rev | stackup | note |
|---|---|---|
| v2.2 | 6-layer | intermediate |
| **v2.3** | **4-layer** — F · In1 GND · In2 VS · B | the committed **fallback** |
| **v3.0** | **2-layer** — F · B | **current** — GND = full-board B.Cu pour, VS = routed B mesh (the 4→2 conversion of v2.3). See §12. |


---

## 10. Two corrections worth keeping explicit

- **The "4 farad" energy myth.** Four 1 F cells read as 4 F *only* all-parallel at 2.75 V. The 5.5 V
  rail needs two-in-series, so the array is 1 F *effective* at 5.5 V. What is fixed is **energy**:
  4 × ½ · 1 F · 2.75² ≈ **15 J**. Farads at 2.75 V vs 5.5 V are not comparable joules — quote the
  energy, not the farads.
- **Pin authority — one source only.** Earlier drafts of this design carried two *different* pin
  assignments (VSENSE on PA5 with BTN on PA7; and the LEDs on PA4–PA7 / TCD0 with VSENSE on PC3)
  — **neither matches the board.** The committed `solar-glow-drh-v2_1.kicad_sch` and
  `solar-glow-drh-v2-hardware.md` are the only authoritative pin reference: LEDs PA0–PA3 / TCA0,
  VSENSE PD2, BTN PA5, I²C PC2/PC3, accel INT PF0/PF1. If anything else disagrees, it is wrong. **v3.0 permuted which LDRV net lands on which of PA0–PA3** (the fan untangle) — the pins are still PA0–PA3/TCA0, but the LDRV↔pin↔LED map changed; see §12 and `firmware/README.md`.

---

## 11. Cost reality

The supercaps dominate the BOM. SCHURTER 3-153-438 (WS17, 1 F) runs ~€6.77 in volume / ~$8–15 per
cell; four of them push the supercaps to **two-thirds or more** of the per-board cost — the single
dominant line, and the reason the 4-cell array is a deliberate reroute rather than a casual upgrade.

---

## 12. v3.0 — the 2-layer redesign (current)

v3.0 re-implements v2.3's 4-layer board on **two layers** (F / B) — same 50.80 × 88.90 card, r3.0
corners, and the **same BOM**. It is the current board; **v2.3 (4-layer) is the committed fallback.**

- **GND and VS come off the inner planes.** In1 (GND plane) becomes a **full-board B.Cu pour**
  (`GND_B` zone) plus stitch straps; In2 (VS plane) becomes a **routed mesh on B** (w0.4 trunk).
  Routing added: ~334 segments, **83 vias** (uniform 0.6/0.3).
- **LDRV fan untangle — the pin-map change firmware must track.** Four U1-proximal LDRV labels were
  permuted so the schematic matches the as-routed copper. As-routed:

  | U1 pin | port | TCA0 | net | LED |
  |---|---|---|---|---|
  | 1 | PA3 | WO3 | LDRV1 | D2 |
  | 28 | PA2 | WO2 | LDRV2 | D3 |
  | 27 | PA1 | WO1 | LDRV3 | D4 |
  | 26 | PA0 | WO0 | LDRV4 | D5 |

  (v2.3 was the reverse at the U1 end: pin 26 = LDRV1 … pin 1 = LDRV4.) The **ballast-side labels are
  untouched** — LDRVn still drives Dn+1 through ballast Rn; only the U1-pin end moved. `led.c`'s pin
  table must match this. The port range PA0–PA3 / TCA0 split (§10) is unchanged; the LED *placements*
  (D2–D5) and reverse-mount orientation are unchanged.
- **Mounting holes symmetrized.** MH1–4 moved concentric with the r3.0 corner fillets — MH1 (3.0,
  85.9), MH2 (47.8, 85.9), MH3 (3.0, 3.0), MH4 (47.8, 3.0); pad Ø3.6, drill 2.2, GND; pitch **44.80 ×
  82.90** (was 43.80 × 82.90). The enclosure was aligned to match (`enclosure/README.md`). The **v2.3
  fallback still carries the old 3.5 mm x-inset holes** — only relevant if v2.3 is ever fabbed (its
  v2.1 enclosure matches the old positions as-is; backport is a carried, undecided question).
- **Selective hard gold + plating bus.** Hard electrolytic gold on the DRH field + letters rim, the
  perimeter frame (inset 1.25 mm, w0.5), and 6 edge ornaments. The frame is the plating-bus backbone;
  6 ornament ties + a field→frame east L-tie feed it; **two 0.25 mm stubs cross Edge.Cuts at x=25.4
  (N/S)** to the panel rail and are milled at depanel. The gold set is **GND-referenced** (the four M2
  GND pads overlap the frame at the corners) — consistent with the grounded Ti shell, not floating
  copper. PCBWay special-request text is in `PCB/README.md`.
- **Two real defects found and fixed** in the final audit: an **NFC_EN 0.27 mm open at U6.3** (the
  4→2 conversion dropped an inner link; the kept B stub ended short of the pad — bridged
  (4.7,33.588)→(5.25,33.588) w0.25), and a **VS feed crossing U6's true bottom-row pads** (ripped and
  re-jogged through the inter-row gap at y32.2). Both had been *masked* by a wrong back-side pad model
  — see the trap below.
- **KiCad-2026 pad convention — the trap that hid the defects.** Nets are **name-only** (no numeric
  net table; old regex breaks). Back-side footprint pad position = `fp_at + Rot(−fp_rot)·pad_offset`,
  and the pad's rect angle is written footprint-composed (use it as-is). Getting this wrong axis-swaps
  14 pads, invents phantom shorts, and masks real opens. And a corollary already burned once on this
  project: **ERC/DRC cannot catch a wrong symbol pin-number-to-function mapping** — only a datasheet
  cross-check does.
- **Face-copper verdict — open, Devin's aesthetic call.** The 2-layer face carries ~333 mm of signal
  copper + via rings in the visible band. Under matte-black mask with resin-filled (tented) vias the
  rings mostly vanish and traces read as faint relief, but it is well past the old "10–20 discreet
  jumpers" guess. Options: **ship v3.0** (treat the trace texture as intentional circuit-aesthetic) or
  **fall back to the clean-face 4-layer v2.3**.
- **DRC intentional exceptions** (do-not-fix): LA↔LB coil short (the antenna); MH↔gold-frame contact
  ×4 (GND tie); the 2 plating stubs crossing Edge.Cuts; the illumination copper inside the glow window
  (D2–D5 pads, K2–K5 diagonals, ANODE stubs/vias); LDRV4 via (35.5, 47.55) rim graze; LB bridge via
  (42.9, 38); east L-tie crossing the coil on F. Plus benign `lib_footprint_issues` + the reserved
  `BTN` `track_dangling`.
- **Carried bench items** (not resolved here): NFC coil L + C9 trim (~100 pF; now includes the F L-tie
  crossing and the Ti-shell proximity); scope PA6/FD on a real tap with VCC gated off; ~100k NFC_EN
  pulldown (tristate default); LED PWM INVEN polarity in `led.c`; `twi.c` presence; plastic dry-fit;
  **Ti-shell-behind-coil L/Q** — enclosure-relevant: metal behind the NFC coil pulls its inductance
  and Q, and could force a local change over the coil area if it detunes (measurement, not a CAD
  change yet).

