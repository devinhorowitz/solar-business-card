# PCB-side notes for the enclosure team — resin-brace / ferrite / 0.6 mm direction

From the PCB side, responding to "Coordination items for the PCB side", the pivot from four
Ti pillars to a resin sandwich brace, and the ferrite-backing addition. The committed
`PCB/solar-glow-drh-v4_0.kicad_pcb` remains the source of truth; nothing below changes the
board. Sections 1–2 close out your items; 3 is the ferrite pocket spec (since built — the brace
carries the 12-wide × 0.33 channel and its drawing calls it out);
4–8 are supporting notes.

---

## 1. Pillar item — formally closed (and why the brace is the right call)

The four pillar centers were audited against the committed copper (1.2 mm probe radius,
all B.Cu segments, pads, and vias, by net):

| Pillar | X, Y | Verdict | Finding |
|---|---|---|---|
| NW | 13.6, 40.1 | **REJECT** | INT2 trace directly under the post (overlapping); INT1 at 0.32 mm. Grounded post = accelerometer interrupts shorted, tap-wake dead. |
| NE | 39.5, 40.0 | **REJECT** | On the NFC coil — LA turns at 0.15 mm both sides, inside the antenna keepout. |
| SW | 13.5, 50.5 | **CONFIRMED** | Solid GND pour, nothing else within 1.2 mm. |
| SE | 39.5, 50.5 | **REJECT** | On the NFC coil — LA turns at 0.15 mm. |

The inert brace dissolves all three rejects by construction: non-conductive resin may rest
on signal traces and on the antenna without consequence, and the load spreads over the
whole middle third instead of four points. No net-confirmation is needed for any brace
contact area. If any future feature is conductive and touches the board back, send
coordinates and the PCB side will return a net verdict same-day — the probe tooling is
built.

## 2. Cutout / height map for the brace (middle third, y 29.6–59.3)

Positions and outlines: take from the committed board (CPL / STEP) as usual. Heights are
the layer you cannot see; these are datasheet-verified maxima in mm:

> **Re-measured against the v4 board 2026-07-28.** Every `(x, y)` below is now the footprint
> origin read out of `solar-glow-drh-v4_0.kicad_pcb` with `pcbnew`, not carried forward. Three had
> drifted since v3 — **U1** (was 9.5, 40.9), **U3** (was 20, 35.9) and especially **U6**, listed at
> 6.34, 32.2 but actually at **3.91, 7.31 — out of the brace zone entirely**. Three v4 parts had
> never been added at all: U8, U9 and L2.

| Item | Location (x, y) | Height | Note |
|---|---|---|---|
| U9 (SOT-23-5, LDO) | 3.90, 55.40 | **1.45** | TPS7A0233 DBV. Datasheet package outline DBV0005A, verbatim: "SOT-23 - 1.45 mm max height". **Tallest component in this zone** now that U7 is 0.90 |
| U7 (DFN-8, FRAM) | 28.21, 37.40 | **0.90** | _(Corrected 2026-07-28: was "SOIC-8, 1.75, tall pole - brace thickness derives from it". The v4 board carries the DFN-8 — `solarglow.pretty/U7_DFN8.kicad_mod` `descr`, RAMXEED DS501-00087-1v0-E p.21: 5.00 × 6.00 body, **0.90 MAX**. **U7 is no longer the tall pole**, and the cavity is cap-limited at 1.70 regardless. Any brace thickness derived from the 1.75 needs re-deriving.)_ |
| U1 (VQFN-28, MCU) | 8.23, 44.07 | **1.00** | AVR64EA28. DS40002443A §38.5: D/E 4.00 BSC, "Overall Height A" 0.80 / 0.90 / **1.00 max** |
| L2 (1008/2520 inductor) | 26.52, 58.50 | **1.00** | Murata DFE252010F-100M, 2.5 × 2.0 × 1.0 — **added 2026-07-28**, this row never existed |
| U8 (QFN-28 4x4, PMIC) | 31.20, 54.00 | **0.85** | AEM10300. DS-AEM10300-v1.4 §15.1 Fig. 17: 4.000 ± 0.05 square, thickness **0.800 ± 0.05** — **added 2026-07-28**, this row never existed |
| U3 (LGA-12 accel) | 25.80, 32.80 | 0.87 | ADXL367 (CC-12-4); was 1.0 for the retired LIS2DH12 |
| D2–D5 (reverse-mount LEDs) | 16.10 / 22.40 / 28.70 / 34.70, y 43.90 | 0.83 | Inside the window bay — see §6 |
| U5 (XQFN8, NFC) | 35.05, 34.00 | 0.5 | SOT902-3, 1.6 × 1.6 × 0.5 verbatim |
| All 0402 R/C | various | 0.55 budget | Includes solder |
| SW2, SB1–SB4, SJ1 solder-bridge pads | SW2 26.35, 50.37; others per CPL | **0.8 budget, variable** | Bare pads until an operator bridges them; blob height is uncontrolled. Generous cutouts; never load-bearing. |
| C9 (0402 trim, NFC tank) | 35.66, 39.14 | 0.55 | Bench-fitted — see §5 |
| ~~U6 (SOT-23-6)~~ | ~~6.34, 32.2~~ → **3.91, 7.31** | 1.45 | TI DBV, with leads. **Not in the brace zone** — it sits at y 7.31, in the top third. Kept here only so the old row is not silently dropped; the brace does not clear it because the brace never reaches it |

Outside the brace zone (top third): TC1 land, JP1/TP1 bench strip (x 47.55–49.25, TP1 y 12,
JP1 y 14.54–22.16 — the 0.50 mm shell clearance already agreed for the lip still applies),
and the supercap bays. Keep the brace clear of all of these.

## 3. Ferrite pocket over the antenna — spec _(BUILT: the brace generator carries the open-ended
12-wide × 0.33-deep channel and the DRAWING dimensions it; this section stays as the spec's
rationale record)_

A flexible sintered-ferrite patch between the coil and everything behind it gives the flux
a low-reluctance return path: the floor stops seeing the field, the eddy detune and the
Q loss both largely vanish, and read range approaches bare-card. The manufacturer's app
note (Würth ANP022) describes exactly this metal-behind-antenna fix. Ferrite raises the
coil inductance above bare — the C9 trim absorbs it (see §5).

**Part** (on the project BOM as FER1): Würth **WE-FSFS 364006**, DigiKey **732-5049-ND**
(verified: Active, 51 in stock, $17.43, tray; 24-week mfr lead once depleted — order with
the build). Material 364 is their 13.56 MHz redirection grade. 60.00 × 60.00 mm ×
**0.38 mm overall stack** (ferrite + PET film + single-sided non-conductive PSA, per the DK
detailed description — the bare-ferrite "0.3 mm" figure floating around is the layer, not
the stack). Laser-scored 2 × 2 mm grid cuts cleanly to size; one sheet yields four patches.
Non-conductive as supplied; all three datasheets now committed in `datasheets/`.

**Alternates, now verified (both are THIN variants, not cheaper equals):** shield strength
scales with µ′ × ferrite thickness, and the machined pocket makes thickness free — so the
thick sheet wins outright. Würth 3641014 (DK 732-13935-ND, $4.19, 379 in stock): same
µ′ = 150 / µ″ = 3 @ 13.56 MHz material, but only 0.1 mm of ferrite in a 0.14 mm stack —
about 1/3 the shield. Legitimate fallback if 364006's 51-unit stock dries: **stack three
3641014 layers** (~$12.57, ~0.42 mm stack) to rebuild ~0.3 mm of ferrite; cut the pocket to
the measured 3-layer stack − 0.05. Laird MHLL6060-300 (DK 240-2791-ND, $6.40, 4,778 in
stock): 0.09 mm overall, µ′ published as a graph only — thinnest and weakest, last resort.
DK also lists mid-family 364103/364104/364105 ($7.46/$8.85/$11.18, thicknesses unverified).
Whichever sheet is chosen, the pocket rule is the same: depth = measured stack − 0.05 mm.

**Patch size and position (board coords):** cut to **12.2 × 25.8 mm**, covering
**x 36.8–49.0, y 31.6–57.4** — exactly the antenna keepout box. That is component-free,
flat board back (mask over coil traces + bare laminate). Margins past the outer turn are
~0.45 mm on all sides; more would be better but board features cap it (supercap bodies at
y 31.15 and y 57.75, lip seat east of x 49.8).

**Pocket in the brace (board-facing surface):**
- Outline: patch outline + 0.2 mm cut clearance per side.
- Depth: **t_sheet − 0.05 mm** (nominal stack 0.38 → pocket 0.33; measure the delivered
  sheet and cut to measured − 0.05), so the ferrite sits
  ~0.05 mm proud and seating the brace presses it flush against the board back. Target
  0.03–0.08 mm proud; do not exceed ~0.1 mm compression — the sheet is bend-rated
  (segmented grid), not crush-rated.
- Adhesion: **PSA side into the pocket, PET face against the board.** The board stays
  clean, the brace stays removable per §5, and the ferrite travels captive with the brace.

With the ferrite in place, the brace *should* span the coil band (this reverses the earlier
"end the brace west of x 36.8" suggestion — that advice applied only to a lossy resin with
no ferrite). Resin RF loss over the coil stops mattering; the ferrite sits between.

## 4. Brace material constraints (electrical)

- **"Inert" must exclude conductive fill.** No carbon- or graphite-filled resins — they are
  weakly conductive and would lie across the antenna and every signal trace. Unfilled or
  glass/mineral-filled only. This applies regardless of the ferrite.
- **Dielectric detune is expected and absorbed.** Resin (εr ≈ 3–4) and the ferrite both
  shift the tank; the C9 trim ladder covers the whole family of builds. Consequence: final
  trim happens with the full stack installed — see §5.

## 5. C9 is now a derived value, reflowed — not a trim

**Changed 2026-07-30.** C9 was DNP and hand-fitted against a measurement. It is now **47 pF,
placed by the assembler**, because the value can be computed and the computation lands well
inside the window a trim would have searched.

**Coil.** L is not estimated from a spiral fit — every closed form (Wheeler, Mohan,
Jenei) is fitted to square spirals and this coil is 11.0 × 24.6 mm outer, aspect 2.2. It is
computed by **Greenhouse** on the board's own rails (7 turns at x 37.4–41.0 / 44.8–48.4 and
y 32.2–35.8 / 53.2–56.8, 0.30 mm trace on 0.60 mm pitch): self-inductance of all 28 straight
segments plus the signed mutual inductance of every parallel pair, GMD-corrected for strip
width, 45° corners taken off first order.

> **L = 0.958 µH** bare — 404 nH of self, 606 nH of mutual, so 60 % of this coil's
> inductance is turn-to-turn coupling.

Two independent checks: the same code agrees with Mohan's current-sheet fit to within 2–6 %
on square spirals, and the **"~90 pF bare"** figure this section used to quote implies
L = 0.957 µH at 13.56 MHz — the same coil to three digits, arrived at by whoever wrote that
line without this calculation.

**The rest of the tank.** Tag Ci = **50 pF** (NT3H2211 datasheet Table 42, LA–LB on-chip,
13.56 MHz, V<sub>LA-LB</sub> = 2.4 V<sub>RMS</sub>, min 44 / max 56). Antenna Cc ≈ **6 pF**
(AN11276 Table 2: etched inter-turn 2–4 pF, plus 1–5 pF for the bridge — this coil's inner
end does return across the front on LB, which is that bridge).

**Target frequency, and why it is not 13.56.** AN11276 §4.2.1, verbatim: *"For single tag
operation, a tuning slightly above 13.56 MHz would lead to maximum read-/write distance. Due
to manufacturing tolerances, a nominal frequency of 14.5 MHz for single tag operation is
recommended."* The asymmetry behind that: presenting the card couples the two antennas and
pulls the tag's resonance **down**, so a tag already under the carrier gets worse as it
approaches, while one above it moves toward the carrier.

**The ferrite is a scenario, not a tolerance.** The old 52–77 pF enclosed window is an
inductance window in disguise: 77 pF ⇒ 1.052 µH, 52 pF ⇒ 1.300 µH, i.e. **+10 % to +36 %**.
Every board shares whichever multiplier is real, so it is spanned, not stacked in quadrature
with the component spreads.

| C9 | ferrite +10 % | +23 % | +36 % | verdict |
| --- | --- | --- | --- | --- |
| 39 pF | 15.91 | 15.05 | 14.31 MHz | safe, but 2.2 bandwidths above the carrier |
| **47 pF** | **15.28** | **14.45** | **13.74 MHz** | **+0.05 MHz off AN11276's target; never under the carrier** |
| 56 pF | 14.65 | 13.86 | 13.18 MHz | high-ferrite case falls under the carrier |
| 82 pF *(old)* | 13.20 | 12.48 | 11.87 MHz | under the carrier in every scenario |

Loaded Q is ~15–30 (R<sub>p</sub> 1.5–3 kΩ), so the −3 dB bandwidth is 0.45–0.91 MHz. 47 pF
sits **1.3 bandwidths** above the carrier; 39 pF sits 2.2, which is real range given away for
a corner case. The only way 47 pF goes under is ferrite at its maximum estimate *and*
components at 2σ together — 13.31 MHz.

**Part:** Johanson **QSCT251Q470G1GV001E**, DigiKey **712-QSCT251Q470G1GV001ETR-ND** — 0805
C0G/NP0, ±2 %, 250 V, High-Q / Ultra-Low-ESR, 1.17 mm max, Active, **10,809 in stock**
(the 82 pF it replaces had 3,522). Cut-tape **712-QSCT251Q470G1GV001ECT-ND** is MOQ 1 if the
4,000-piece reel is wrong for the run.

**Validation (2026-07-30, second pass).** The 47 pF derivation was re-checked against
NXP's own hardware and against other vendors before trusting it:

- **The Greenhouse code reproduces NXP's Class 5 reference antenna.** The AN11276 package
  ships the Gerbers of the reference coil NXP designed for exactly this 50 pF chip family
  with **no external capacitor** (the demo board is titled "Class 5 Antenna – 50 pF #01",
  one part on LA–LB). Parsing that Gerber — 6 turns, 0.30 mm trace, 0.75 mm pitch,
  39.25 × 24.00 mm outer — and running it through the same code used on our coil gives
  **L = 2.24 µH**, which with Ci = 50 pF and NXP's own 2.5–6 pF parasitic range resonates at
  **14.22–14.69 MHz**: centered on the 14.5 MHz their app note names. The methodology
  reproduces NXP's design intent on NXP's board to a quarter of a megahertz.
- **The NXP Class Design Guide calculator agrees on every input.** Its sheet takes a
  threshold-frequency target, chip capacitance "(17pF or 50pF)", connection capacitance
  0.5–2 pF, etched coil capacitance 2–4 pF — and has an explicit **"Parallel Cap"** input
  row, so an added tuning capacitor is part of NXP's own flow, not a workaround. Our
  Cc = 6 pF sits at the top of their 2.5–6 pF total; using 4 pF instead moves the mid
  scenario 14.45 → 14.59 MHz, which changes nothing.
- **Cross-vendor and measured practice agree on the direction.** ST's guidance for the
  ST25 family is to tune above 13.56 to compensate reader-proximity coupling, and surveys
  of real cards and readers measure resonances of ~13.5–15 MHz with the majority near
  14 MHz. Our enclosed span (13.74–15.28 MHz across the ferrite scenarios) sits inside
  that band, and its two ends land respectively on ST's mild figure and the top of
  measured practice.
- **The old numbers weren't wrong — they had a different target.** The retired 52–77 pF
  window solves this same tank for **13.56 exactly** (so does the old 82 pF part, bare:
  0.958 µH + 138 pF = 13.8 MHz). The whole delta between that window and 47 pF is the
  target frequency, and the target is the sourced part: AN11276 §4.2.1, ST, and practice
  all say above the carrier, never below.
- **The ladder is real.** Same Johanson S-series, ±2 % C0G 0805, all Active at DigiKey:
  39 pF (808), **47 pF (10,809)**, 56 pF (11,258), 68 pF (17,236).

**Measure ENCLOSED.** Bare on the bench this reads ~16.7 MHz and that is not a fault — the
ferrite is what brings it down. A bare-board measurement will look alarming and mean nothing.

**Still worth keeping, now as insurance rather than workflow:**

1. The brace is **seated, not bonded** to the board — removable and reseatable. (PSA-ing
   the ferrite into the brace pocket per §3 keeps this true.)
2. C9's cutout allows tweezers-and-iron access with the brace out.

If the first assembled card measures outside ~13.6–15.3 MHz, the ferrite multiplier is
outside the assumed range and the neighbours on the C0G ladder are 39 and 56 pF.

## 6. Window bay decision needed — reflector strategy

The brace occupies the space where the adhesive reflector strip (RFL1, located by the
laser-marked 20.9 × 6.2 frame on the cavity floor) was planned. Three options; pick one and
the PCB side adjusts the aux BOM:

- **(a) Window cutout in the brace** — preserves the air bay and floor reflector exactly as
  designed. Zero optical change.
- **(b) Brace face becomes the reflector** — white resin, or reflective film applied to the
  brace underside facing the LEDs. Kills the separate floor strip; alignment moves from the
  laser frame to the brace geometry.
- **(c) Solid resin behind the window** — a light-pipe/diffuser. Changes the optics
  entirely (could be brighter and more even, or muddier — depends on resin clarity and
  color). If you want this, send the resin's optical properties and the PCB side will run
  the glow budget before you cut anything.

Brace color matters in all cases: white/clear near the window helps or is neutral; matte
black immediately adjacent to the LED bays absorbs side-light and dims the monogram.
(The ferrite patch is 1 mm east of the window keepout — the two features don't interact.)

## 7. Floor material vs NFC — now a fallback table

**With the §3 ferrite adopted, the floor metal choice decouples from NFC almost entirely**
— the sheet masks the floor, and mass/finish/engraving become free choices on the RF axis.
The table below matters only if the ferrite is omitted. Surface resistance Rs = 1/(σδ) at
13.56 MHz is the loss figure of merit, lower = better:

| Floor | ρ (µΩ·m, approx) | Skin depth @13.56 MHz | Rs (mΩ/sq) | No-ferrite NFC verdict |
|---|---|---|---|---|
| Copper | 0.017 | 18 µm | ~1.0 | Most detune (retrimmed anyway), least loss — best range |
| Aluminum | 0.027 | 22 µm | ~1.2 | Nearly as good as Cu |
| Brass | ~0.065 | ~34 µm | ~2.0 | Good |
| Ti-6Al-4V | ~1.7 | 178 µm | ~9.5 | Baseline — noticeably lossier |
| Stainless 304/316 | ~0.72 | ~116 µm | ~6.0 | Between brass and Ti. **Austenitic only** — ferritic/martensitic grades (410/430) are magnetic (µr ≫ 1); the one genuinely bad choice behind an unshielded coil. |

Computed bounds from the committed coil (no ferrite, retrimmed by C9): bare L₀ = 0.98 µH;
perfect-conductor floor at 1.80 mm bounds L_eff at 0.68 µH (70 % kept). Every option works
for tap-range; with the ferrite, every option approaches bare-card.

## 8. Remaining 0.6 mm items and small notes

- **Cavity math confirmed from your own stack** (1.00 + 1.80 + 0.60 + 0.15 = 3.55): the
  coil-to-floor standoff is unchanged by the thickness change, and the spiral is entirely
  B.Cu — only the ~30 mm F.Cu bridge moves 0.2 mm closer. Sub-1 % inductance effect. No new
  retune burden beyond the parked bench item.
- **TC2030 leg retention at 0.6 mm — verify.** The legged programming cable latches through
  the board; the repo `TC1  Tag-Connect TC2030-MCP  $0.pdf` is silent on minimum board thickness. Confirm against
  Tag-Connect's footprint documentation (or bench) before the thickness locks. PCB side
  flagged, either side can close it.
- **Reflow carrier** at 0.6 mm: acknowledged as a PCB-side/order item.
- **Thinner window web is a glow bonus**: 0.8 → 0.6 mm of FR4 under the monogram transmits
  more light.
- **Isolation layering — don't double-stack.** Insulating layers now in the system:
  soldermask (always), the brace + ferrite (middle third), and the optional Kapton blanket.
  The brace-covered middle third needs no Kapton. In the supercap bays the caps sit
  1.70 mm tall under a 1.80 mm cavity — 0.10 mm air; a 0.05 mm Kapton sheet there eats a
  third of that headroom. Decide blanket extent vs brace extent as one plan and send the
  final stack; the PCB side will sanity-check clearances.
- **Shell grounding is unchanged**: the shell ties to board GND through the four corner M2
  screws (3,3 / 47.8,3 / 3,85.9 / 47.8,85.9). The brace and ferrite being inert does not
  affect this; no other contact should be relied on for ground.
- **Freed rib strip** (x 24.9–25.9, y 0–33 and 56–88.9) and the un-locked supercap
  constraint are recorded on the PCB ledger for future revs. No v4.0 action.

— PCB side
