# SOLAR-GLOW · DRH — design notes & posterity

Durable engineering rationale, hard-won findings, and future-variant ideas, distilled from the v0/v1 planning docs (since retired).

**Authority order.** For the *current* design, the committed `solar-glow-drh-v3_0.kicad_pcb` /
`.kicad_sch` (v3.0, 2-layer) plus `README.md`'s current-revision table are ground truth; the 4-layer v2.3
(in git history) is the fallback design. This file is the *reasoning archive* — the
"why" and the "don't do that again" — with the **v3.0 deltas collected in §12**. Where an as-built
doc already owns a topic, this points at it rather than duplicating. (The `solar-glow-drh-v2-*` docs
are v2-era; their v3.0 deltas are banner-noted at their tops.)

---

## 1. The supercap land — the landmine (never reintroduce the old one)

**The v0/REV-J supercap land was WRONG — confirmed against physical parts.** It placed two
3.5 × 3.5 mm pads on a diagonal (36.5 × 16 pattern, centres ±16.5 / ±6.25) that land on the cell's
folded **end tabs**. Those tabs are coated, **non-solderable** mechanical locators, so a board built
to that land makes **zero electrical contact**. The root cause: the datasheet's single generic
"Soldering pads to Case WS10/13/17" diagram (`datasheets/SC1-SC4  SCHURTER 3-153-438  $15.48.pdf`) was misread as the WS17
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

**Draw line items** (budget against harvest): accel ≈ **0.89 µA** (an ADI ADXL367, always-on at
100 Hz for this figure — the LIS2DH12 it replaced drew ~10 µA click-armed); light-sense divider
sub-µA; MCU sleep ≈ 0.65 µA (AVR-DD power-down, `PMODE=AUTO`). With the accel this low, dark
standby is **~2.7 µA** and no single part dominates. The LEDs are the only mA-scale load. See
`firmware/README.md` "Power notes" for the model.

> **Ballast caveat — re-derive the LED numbers for v2.1.** The LED-draw figures used throughout the
> old docs (≈5 mA for 4 LEDs full-on, ≈3 mA breathing, +1.25 mA per added LED) were computed at
> v0's **1 kΩ** ballast. The v2.1 BOM carries a **different ballast (150 Ω, flagged bench-pending)**,
> which at the same ~3.5 V rail raises per-LED current several-fold. The schematic leaves R1–R4 as a
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
  predict it. (v2.1 is 0.8 mm, the same as v0, so v0 predicted the v2.1 look — but **v3.0 is now 0.6 mm**,
  thinner than both, so v0 no longer predicts it and the appearance gate **re-opens**: the amber
  glow through 0.6 mm FR4 will read brighter/sharper at the strokes than the 0.8 mm coupons, so
  validate the *look* on a **0.6 mm** coupon before committing the diffuser/window.)
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
  holds the whole VS rail ≤ 3.60 V worst-case and VDDIO2 is tied to VS via SJ1, so the accel is protected by
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
- **Internal temperature sensor** is available if wanted -- and by design it is the card's *only*
  thermal sensor (per-cap thermistors are unwarranted, and no spare pin is ADC-capable anyway; see §7
  "Supercap thermal").

Not useful on this part: ZCD (mains only), op-amps (the DD family lacks them), PTC cap-touch (see §5).

---

## 7. Enclosure — board-side rules to honor now (full detail in enclosure/README.md)

The Ti rear-shell is parked, but a few rules must be baked into the board so it never needs a
re-spin for the enclosure:

- **Grounded body → short risk.** In the enclosed variant, **drop the right-edge castellations**;
  land support pillars **only on GND pour**; keep a **die-cut Kapton (~0.05 mm)** blanket isolation
  layer in reserve if a later via audit on the rib lines finds an untented via.
- **General cavity 1.80 mm (cap-limited), plus a U2 relief pocket** — the four **1.70 mm WS17
  supercaps** set the general cavity (1.80 = cap + 0.10 mm air, toleranced 1.80 ±0.05). U2 (SOIC-8,
  1.75 mm) is the single tallest part but sits over a **local 0.05 mm relief pocket** (floor 0.95 mm
  there vs 1.00 general), so it keeps 0.10 mm air while the general cavity stays 1.80. The
  0.9 mm QFN is irrelevant. ("Cells" elsewhere can mean the 1.2 mm **solar** cells on the front — a
  different part; don't conflate the two.)
- **No tall back-side parts.** The cavity budget assumes the tallest *populated* rear part is U2 at
  1.75 mm. The v2-era 2.54 mm breakout headers (old JP1/JP2) are gone in v3.0; the reused-`JP1`
  bench strip + `TP1` are flat SMD pads (nothing to populate — a soldered header would stop the
  shell closing, same as ever). J1/TC2030 are flat back-side pads.
- **The button is the accel tap** (cap-touch dies behind a grounded plate; the old "snap-dome"
  actuator is superseded).
- **Shell, current approach (v3.0):** Ti-6Al-4V Grade 5, **fully 3-axis CNC-milled** (no etching),
  **bead-blast** finish, with a **1.00 mm floor** (0.95 under the U2 pocket), **no ribs** — center
  support comes from a separate resin diffuser brace — and the window is backed by the brace's white
  diffuser face (the laser-marked reflector frame is dropped). Overall height
  3.55 mm; the four bosses sit on the **v3.0 hole pattern** (concentric with the r3.0 fillets),
  retained by four corner M2 screws (~2.2 mm Ti engagement). The earlier 0.3 mm-skin / 7075-fallback /
  photochemical-etch plan is dropped. Full CAD, callouts, and fab notes are in `enclosure/README.md`.
- **Supercap thermal -- vulnerability, sensing, and why no per-cap thermistors.** The four WS17
  EDLCs are the heat-sensitive parts (a 2.75 V cell derates in both working voltage and life with
  temperature; EDLC life roughly halves per ~10 °C, Arrhenius rule of thumb), so "how hot do the caps
  get, and must we measure them *there*?" is a fair question. Answer: **no dedicated per-cap
  thermistors.**
  - *The single internal sensor suffices.* There is no internal heat source of consequence -- the only
    dissipators are the Q1/TLV3011 shunt clamp (≤~0.2 W, and only under strong direct sun) and the brief
    LED breaths -- so in the failure mode that actually matters (hot car / sun-soak) the whole 54 x 86 mm
    card floats to ambient and sits near-isothermal. Across 0.6 mm FR4 with a thermally-coupled Ti shell,
    any MCU-to-cap gradient collapses well within the max-temp logging timescale. The cap centers are
    25-40 mm from U1 (SC1 24.7, SC3 31.7, SC2 35.2, SC4 40.4 mm), but the long cap bodies reach within a
    few mm of the MCU at their near ends. A max-temp / derating flag needs only coarse accuracy (±5 °C),
    which the AVR internal sensor (§6) meets after a one-point cal.
  - *And an NTC has nowhere to land.* No spare pin is ADC-capable -- the free GPIO (PA4 / PC0 / PC1) are
    not on PORT D/E/F, the only ADC-input ports on this AVR-Dx -- so an analog thermistor cannot be added
    without a re-spin. If a future rev ever needs a genuine per-cap reading, add **one I²C temp sensor**
    on the existing PC2/PC3 bus near the cap cluster, not analog NTCs. Either path: bench-confirm the
    isothermal assumption once (two thermocouples -- a cap can vs the MCU die, under a heat-soak) before
    trusting the single-sensor proxy in firmware.
- **Optional supercap-to-shell thermal-interface material (TIM).** A compliant gap-filler could bridge
  each supercap can to the Ti shell floor across the ~0.10 mm cavity air gap (the caps hang 1.70 mm off
  the B-side into the 1.80 mm cavity; the brace's H-band and edge rails deliberately clear the cap bays,
  so the space directly behind each can is air to the shell floor, *not* resin -- so a TIM there couples
  the cap to the shell, not to the inert brace). A nice-to-have, not a requirement; if ever added, spec
  it against these traps:
  - *Compliant gap-filler, NOT a fixed-thickness pad.* The gap is ~0.10 mm nominal and **0.05-0.15 mm**
    across the cavity tolerance alone (1.80 ±0.05 over the 1.70 mm-**max** WS17 can; `enclosure/README.md`
    C1), and opens further if a production can sits below its datasheet-max height. A hard 0.10 mm pad
    would either float on a tall gap (no contact, useless) or jack the board off its brace/lip seat at
    z2.80 on a tight one. Use a conformal filler that spans the range at low force.
  - *Electrically insulating -- mandatory.* The Ti body is GND (see the "grounded body → short risk" rule
    above); a live cap can shorted to it through a conductive TIM is a dead short. Same reflex as the
    reserved Kapton blanket.
  - *Low compression force + serviceable.* Do not preload the board off its z2.80 rest, and keep it
    re-applyable -- the shell opens on four M2 screws, so a cured RTV is a teardown hazard where a
    re-usable gap pad/putty is not.
  - *What it buys, and what it does not.* Ti-6Al-4V is a poor conductor (~6.7 W/m·K, ~1/20th of aluminium)
    but a real thermal **mass**: the TIM buffers transients (a warm hand, a sun-driven clamp burst) into
    the shell and homogenizes the card -- which usefully tightens the cap-to-internal-sensor coupling and
    makes the single-sensor proxy above a better one. It does **not** lower steady-state temperature under
    sustained hot ambient: there the shell is the heat *ingress*, not a sink, so coupling to it cannot cool
    the caps. Treat it as a transient buffer + sensing aid held in reserve (like the Kapton), not a hot-car
    survival fix -- survival stays the cap's own temperature rating and "don't bake the card."

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
| Accel rail handling | n/a | planned LDO (TPS7A02) for the 3.6 V-max accel | **TLV3011 comparator+ref shunt clamp holds VS ≤ 3.60 V worst-case** (no LDO); supersedes the TLV431 divider (Iref over-voltage) |
| Accelerometer | none | BMA400 / LIS2DW12 (candidates) | **ADXL367, I²C addr 0x1D** (swapped from LIS2DH12 on backorder; 0.89 µA vs ~10 µA) |
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
| **v2.3** | **4-layer** — F · In1 GND · In2 VS · B | **fallback** design (git history) |
| **v3.0** | **2-layer** — F · B | **current** — GND = full-board B.Cu pour, VS = routed B mesh (the 4→2 conversion of v2.3). See §12. |


---

## 10. Two corrections worth keeping explicit

- **The "4 farad" energy myth.** Four 1 F cells read as 4 F *only* all-parallel at 2.75 V. The 5.5 V
  rail needs two-in-series, so the array is 1 F *effective* at 5.5 V. What is fixed is **energy**:
  4 × ½ · 1 F · 2.75² ≈ **15 J**. Farads at 2.75 V vs 5.5 V are not comparable joules — quote the
  energy, not the farads.
- **Pin authority — one source only.** Earlier drafts of this design carried two *different* pin
  assignments (VSENSE on PA5 with BTN on PA7; and the LEDs on PA4–PA7 / TCD0 with VSENSE on PC3)
  — **neither matches the board.** The committed `solar-glow-drh-v3_0.kicad_sch` and
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
corners, and the **same BOM**. It is the current board; **v2.3 (4-layer) is the fallback design, in git history.**

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
  crossing and the Ti-shell proximity); scope PA6/FD on a real tap with VCC gated off; **NFC_EN pulldown — resolved this session (R14; see the addendum below)**; LED PWM INVEN polarity in `led.c`; `twi.c` presence; plastic dry-fit;
  **Ti-shell-behind-coil L/Q** — enclosure-relevant: metal behind the NFC coil pulls its inductance
  and Q, and could force a local change over the coil area if it detunes (measurement, not a CAD
  change yet).

## Teardrops enabled + post-teardrop audit (2026-07-02)

- **Settings** (`.kicad_pro`): all teardrop targets on — pads, vias, and track-to-track
  (`td_ontrackend: true`) — with curved edges (`td_curve_segcount: 1` on all three shape targets).
  Size defaults kept: length ratio 0.5 / max 1.0 mm, width ratio 1.0 / max 2.0 mm, filter 0.9.
  Schema verified against kicad-source-mirror 10.0 `board_design_settings.cpp` (flags live in the
  project JSON, not the board file).
- **Generated:** 247 teardrop zones = 236 pad/via + 11 track-end, curved, fills stored in the board
  (file ~613 KB → 1.23 MB). KiCad 10 writes them as `(zone … (attr (teardrop (type …))))`.
- **Same commit, Devin's cleanup:** 45°-corner beautification (FD, LDRV3/4, SDA, VS, TINY elbows;
  28 segments removed / 12 added) and deletion of redundant GND scraps **including both former
  bridge straps** — (36.5, 47.55→49.05) and the (12.45, 16.54) pair with the TC1.3 stub. Independent
  union-graph audit: **GND is a single component on both the pre- and post-cleanup boards**, so the
  straps had become redundant after the round-3 rework (TC1.3 rides its solid zone connect). No
  starved-thermal recurrence.
- **Geometric ledger** (independent Shapely engine, identical code on both boards): pairs < 0.1524 mm
  went 100 → 103; below the 0.126 hard floor there is exactly one item on both boards — the
  intentional LA↔LB coil junction. Deltas: +3 marginal from the FD 45° reroute (FD↔BTN / LDRV1 /
  PA4), −3 removed with the GND scraps (GND↔UPDI, GND↔VS, SCL↔SDA), +4 teardrop-involved (below).
- **Teardrop marginals KiCad cannot see** — KiCad's DRC does not apply clearance rules to teardrop
  zones, so these exist only in this ledger; all PCBWay-legal, no action:
  CLREF-teardrop ↔ VS pad 0.141 @(46.0, 72.0); NFC_EN-teardrop ↔ PC1 pad 0.143 @(7.5, 42.1);
  SCL-teardrop ↔ VDDIO2 pad 0.145 @(9.1, 42.9); UPDI-teardrop ↔ GND pad 0.150 @(10.0, 36.6).
- **DRC row-count jitter caveat:** on the long parallel 0.127 corridors (the SDA/VIN/VS west bus)
  KiCad enumerates one row per segment-pair at minimum distance, and the count oscillates between
  runs and engines on physically identical geometry (CI 50 → GUI 64 → CI 61 clearance rows). Judge
  the marginal ledger by the geometric pair scan, not by row counts.
- **CI on the teardrop board: green.** Errors 0 (+2 excluded plating stubs), warnings 61
  (+1 excluded coil crossing).
- Parser conventions used for the audit are the ones in the "KiCad-2026 pad convention" trap above,
  re-verified this session against the 10.0 parser and `pad.cpp`: pad `(at x y angle)` angle is
  absolute (board frame); position is footprint-relative.

## R14 patch — NFC_EN pulldown + NPTH cleanup (2026-07-02)

- **R14 (1 MΩ, 0402)** added at **(4.39, 29.4)** rot 0, in the north pocket between the MID bus and
  U6's top pad row: pad 1 = `NFC_EN` (3.88, 29.4), pad 2 = `GND` (4.9, 29.4) dropping straight into
  the existing GND via at (4.9, 28.5). `NFC_EN` reaches the U6-side stub through a **new via pair**
  (3.88, 30.6) → F.Cu → (3.88, 33.35); the F crossing threads west of SCL's F column. Why the hop:
  the B-side **VS wall at y = 32.2** (x 3.35 → 7.29, w 0.4) seals the pocket off from the stub, and
  the west GND corridor to J1.3 is fenced by the J1.2 VS feed at y 38.4 and a VS via at (3.6, 40.8) —
  two earlier placements died on exactly those two features.
- **Ø 0.89 mm NPTH at (37.9, 75.4) deleted** — undocumented, under SC4's body, claimed by nothing in
  the repo. One git revert away if it turns out to have had a purpose.
- **Verification** (same engine as the electrical sift, true pad shapes, hole-decoded pour): all nets
  single-component (`NFC_EN` = U1.5 + U6.3 + R14.1); shorts = the intentional LA/LB junction + three
  new-copper-vs-stale-pour overlaps that the zone refill resolves; **min new-copper clearance vs
  foreign non-pour = 0.2197 mm** (via F-ring → SCL) — every new gap ≥ 0.22, so **zero new
  marginal-ledger entries** and the DRC warning count should not move. Counts: 564 → 569 segments,
  87 → 89 vias, 54 → 55 footprints.
- **Schematic:** R14 cloned in R13's per-ref lib-symbol idiom, placed off-sheet-right at
  (685.8, 69.85) with its own `NFC_EN` / `GND` global labels — reposition freely. If you ever re-run
  update-from-schematic, add R14 to the local `solarglow` footprint lib first (the repo carries no
  `.pretty`; footprints live embedded in the board file).
- **Handoff ritual:** open the board → **refill zones (B.Cu)** → run DRC (expect the same 0 err /
  ~61 warn) → **Tools → Add Teardrops** so R14 *and the reworked U6 area* get their teardrops → commit. The
  U6 pin-map check is **closed** — see the U6 pin-map addendum below.

---

## Addendum — U6 pin-map defect + fix (2026-07-02)

**The check that had been open since U6 landed is closed, and it caught a fabrication-fatal
defect.** The citation of record is TI **SLVSD76C** (`datasheets/U6  TPS22918DBVR  $0.55.pdf` —
TPS22918 Rev C, the doc for the ordered `TPS22918DBVR`). The **SLVSCZ8B** -Q1 automotive twin has an
identical pin table and every §6.5 number (compared and verified at the time); it is not kept in the repo. The DBV pin table reads: **1 = VIN, 2 = GND, 3 = ON, 4 = CT, 5 = QOD, 6 = VOUT.** The board's
symbol had **1 = VOUT, 2 = QOD, 5 = GND, 6 = VIN** — VIN/VOUT and GND/QOD transposed across
the package; only ON (3) and CT (4) were right. As routed, the chip would have had **no
ground** and VS driven into VOUT. Two design choices survived the check unchanged: **CT may
float** ("Can be left floating") and **QOD tied to VOUT** is one of TI's three sanctioned QOD
configs (discharge through the internal R_PD, 25 Ω typ at 3.3 V).

**Fix strategy — renet, don't move.** U6 stays at (6.3425, 32.2) rot 90 (CPL unchanged). The
four power pads were **reassigned to TI truth** (pad 1 → `VS`/VIN_1, pad 2 → `GND`/GND_2,
pad 5 → `VNFC`/QOD_5, pad 6 → `VNFC`/VOUT_6; pads 3/4 untouched), and the **schematic lib
pins were renumbered 1↔6, 2↔5** — the lib pin *names* were correct all along, only their
numbers were mirrored, so no wire or label moved.

**Copper ops.** Deleted: the pad-1↔2 pair seg and the old VNFC diagonal (both fed what is now
VIN), the old VS drop into pad 6, the old GND stub off pad 5, and their 4 teardrop zones.
Added: `a1` VS wall-drop south into pad 1 (w 0.4); `a2` QOD→VOUT strap across pads 5–6
(w 0.25) — the required strap falls exactly on the old pair-seg's mirror; `a3'` VNFC re-anchor
pad 6 → the existing elbow at (9.47, 30.85) (w 0.15, entering *below* the elbow top to keep
0.35 to the VIN diagonal instead of reproducing the ledgered 0.127); `a4`+`V1` GND stub south
from pad 2 to a via at (6.343, 34.5); an F-side GND run west — (9.05, 34.5) → (9.05, 30.2) →
(4.9, 30.2) — threading the free F room between the SCL horizontal and the UPDI column-fence;
and `V2''` at (4.9, 29.9), whose back-side ring lands **directly on R14.2** (the R14 GND
drop), tying U6.2 into the main ground. Eastward routes were exhaustively ruled out: the UPDI
F column (x ≈ 9.94, y 20.4–35.9) fences F, and the VIN elbow + SC1.N pad seal every B lane.

**Verification (geometry engine, post-fix):** every net single-component (GND includes
U6.2 → V1 → F → V2'' → R14.2; VNFC = pads 5+6 + strap + re-anchor + the original artery to
U5); shorts = the intentional LA/LB junction + six stale-pour overlaps that the B.Cu refill
re-carves; **minimum changed-copper clearance 0.200 mm** (the F run vs the SCL via ring —
everything else ≥ 0.275). Counts now: **574 segments, 91 vias, 249 zones** (243 teardrops).

**Datasheet numbers worth keeping** (SLVSD76C §6.5, identical in SLVSCZ8B, V_IN = 3.3 V): I_SD 0.5 µA typ / 3.5 µA
max — this is U6's **standing draw on VS while NFC is off**, the price of the gate (vs the
~195 µA of U5 it removes); I_Q 8.3 µA typ while on (only during I²C windows); R_PD 25 Ω typ;
ON threshold compatible with 1 V+ GPIO, so PA7 at any plausible VS is fine.

**Handoff:** refill zones (B.Cu) → DRC (the deleted teardrops may surface a few new cosmetic
"dangling" notes in the U6 window — expected) → **Tools → Add Teardrops** (covers R14 *and*
the U6 rework) → commit board + schematic together (the sch pin renumber and the pad renet
must land in the same commit or update-from-schematic will fight you).

---

## Addendum (2026-07-02) — bench pad strip (TP1 + JP1) and the enclosure lip

- **Why:** TC1 dies for bench use once PV1 is glued (the TC2030 legs land under the panel), and
  there was no clean power-injection or I²C tap point. Wanted: baked-in bench access.
- **First placement failed on the shell.** A 4-pad THT column in the SC1|SC2 canyon (x 25.4)
  collided with the enclosure's cap-gap **rib** (x 24.9–25.9, full cavity height): pins/pads
  directly under grounded Ti. Scrapped before commit.
- **Shipped placement:** five bare **SMD** pads (1.7 mm sq, 2.54 pitch, B side) at **x 48.4** in
  the SC2-body-to-edge margin — `TP1` VIN (y 12.0), `JP1` 1–4 = GND/VS/SCL/SDA (y 14.54–22.16).
  VIN/VS are local B spurs off the VIN trunk and D1.K; SDA taps a new via at (33.4, 30.78), SCL
  T's off its existing via at (34.37, 35.28); both run east on F at y 29.55/29.1 through the
  channel above the coil's north fence (LA's B turns start at y 32.05), landing on the pads
  through **via-in-pad** on `JP1.3`/`JP1.4` (bare probe pads — via-in-pad is free there).
  Verified: all nets single-component, 0 hard shorts, min changed-copper clearance 0.200; DRC 0.
- **The lip finding:** the shell's perimeter lip was 1.50 mm — inner edge at 50.75 − 1.50 =
  **x 49.25, exactly the strip's east copper edge (0.00 nominal)**. Guaranteed contact once
  pocket (ISO 2768-m) + board-routing (±0.2) tolerances stack. **Fix: lip_w 1.50 → 1.00** →
  inner edge 49.75, **0.50 mm clearance**; floor-span margin absorbs it (the 0.75 floor is 2.5×
  the analyzed 0.55), and the mirrored back frame thins 1.5 → 1.0 (the rear art field grows
  0.5 mm/side). Generator + STEP/STL regenerated and committed; solids valid at 143/144 faces.
- **Housekeeping:** the `JP1` designator is *reused* (the v2-era JP1/JP2 2.54 mm headers are
  gone; JP2 has no successor). JP1/TP1 are bare pads — **no BOM part; mark both DNP in the CPL**
  alongside SC1–SC4 / PV1–PV2 / J1 / C9. Pinout + bench ritual live in
  `solar-glow-drh-v2-hardware.md`; fab-facing notes in `PCB/README.md`.

## Addendum (2026-07-12) -- v4 idea: I²C FRAM for archival / high-rate telemetry

Not a v3.0 change (the board is electrically frozen); logged here as a **v4 consideration**.

- **The limit today.** v3.0 logs telemetry (tap count / sun-hours / max-temp) to the AVR's
  **internal EEPROM**: 256 B, **100k** write cycles, **40 yr retention @ 55 °C** (DS40002315).
  Two ceilings bite for a keepsake: the tap counter can approach 100k over a very active life
  (`firmware/README.md`), and EEPROM retention derates ~2x per 10 °C -- so a card baked on a hot
  dashboard, the exact abuse the temp-logger watches for, can fall well short of 40 yr. A third:
  EEPROM write energy (charge-pump, ~4-13 ms) is *why* the sun diary throttles to one write per
  banked hour and max-temp writes only on a new max.
- **Why FRAM clears all three.** A ferroelectric-RAM part (Infineon FM24V / Fujitsu MB85RC class)
  gives ~10^12-10^14 write endurance (effectively unlimited), **>100 yr** retention that degrades
  far less when hot, and **µs bus-speed writes with no charge pump** (orders of magnitude less
  energy). That would allow a rolling "black box" -- per-brownout, per-tap timestamp, per-second
  sun -- at negligible energy, which the current budget flatly forbids.
- **Net power: an *enabler*, not a reducer.** FRAM does NOT lower the card's baseline draw. The
  internal EEPROM already costs **zero** standby; an added FRAM only *ties* that, and only if
  power-gated (ungated it *adds* µA-class standby to the ~2.7 µA budget). Its energy edge is
  *per-write* (µs bus-speed vs the EEPROM's multi-ms charge-pump write, ~8x less) and only matters
  at high write **volume** -- i.e. the dense-logging case above. Keep the sparse telemetry and FRAM
  saves nothing; log a per-event black box and FRAM is what keeps it inside the budget, where the
  EEPROM's write energy + 100k endurance make it impossible. (A free firmware lever exists first:
  sleep the MCU through the ~few-ms EEPROM write instead of busy-waiting -- skipped today only
  because the writes are so rare.)
- **The v4 hook.** A hard, **I²C-shared, persistent store the MCU owns and a reader can reach** --
  the card as a keepsake that permanently records its own life. The bus already exists: SDA/SCL =
  PC2/PC3, broken out at `JP1.3/JP1.4`.
- **How it fits, cheaply.** An I²C FRAM shares that host bus at a new 7-bit address -- no clash
  with the accel (0x1D) or the NFC tag (0x55), **no new signal pins**. **Power-gate it** like the
  NFC tag (own load switch on a spare GPIO -- PA4 / PC0 / PC1 are free) so its µs writes cost ~0
  standby; the fast write makes gating trivial. ~$1-3 + switch + decoupling.
- **The free near-term alternative (no re-spin).** The `NT3H2211` already carries ~1.7 KB of spare
  EEPROM the MCU can write **and a phone can read over RF with the card unpowered** -- but
  ~10-20 yr retention and ~195 µA/write, so it is the *phone-readable-now* path (= the NDEF
  telemetry idea in `firmware/feature-roadmap.md`), not archival. FRAM is the archival answer, and
  because it is a board add it belongs to **v4**, not a v3.0 respin.
