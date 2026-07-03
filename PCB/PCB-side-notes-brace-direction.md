# PCB-side notes for the enclosure team — resin-brace / ferrite / 0.6 mm direction

From the PCB side, responding to "Coordination items for the PCB side", the pivot from four
Ti pillars to a resin sandwich brace, and the ferrite-backing addition. The committed
`PCB/solar-glow-drh-v3_0.kicad_pcb` remains the source of truth; nothing below changes the
board. Sections 1–2 close out your items; 3 is the new ferrite pocket spec (build this);
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

| Item | Location (x, y) | Height | Note |
|---|---|---|---|
| U2 (SOIC-8, cap balancer) | 28.5, 37 | **1.75** | Tall pole — brace thickness derives from it (existing relief pocket logic carries over) |
| U6 (SOT-23-6) | 6.34, 32.2 | 1.45 | TI DBV, with leads |
| U1 (VQFN-28) | 9.5, 40.9 | 1.0 | |
| U3 (LGA-12 accel) | 20, 35.9 | 1.0 | |
| D2–D5 (reverse-mount LEDs) | 16.1 / 22.4 / 28.7 / 34.7, y 43.9 | 0.83 | Inside the window bay — see §6 |
| U5 (XQFN8, NFC) | 34.8, 34 | 0.5 | SOT902-3, 1.6 × 1.6 × 0.5 verbatim |
| All 0402 R/C | various | 0.55 budget | Includes solder |
| SW2, SB1–SB4, SJ1 solder-bridge pads | SW2 ~24–25, y 48.6; others per CPL | **0.8 budget, variable** | Bare pads until an operator bridges them; blob height is uncontrolled. Generous cutouts; never load-bearing. |
| C9 (0402 trim, NFC tank) | 32.01, 38.5 | 0.55 | Bench-fitted — see §5 |

Outside the brace zone (top third): TC1 land, JP1/TP1 bench strip (x 47.55–49.25, TP1 y 12,
JP1 y 14.54–22.16 — the 0.50 mm shell clearance already agreed for the lip still applies),
and the supercap bays. Keep the brace clear of all of these.

## 3. Ferrite pocket over the antenna — spec (new; build this)

A flexible sintered-ferrite patch between the coil and everything behind it gives the flux
a low-reluctance return path: the floor stops seeing the field, the eddy detune and the
Q loss both largely vanish, and read range approaches bare-card. The manufacturer's app
note (Würth ANP022) describes exactly this metal-behind-antenna fix. Ferrite raises the
coil inductance above bare — the C9 trim absorbs it (see §5).

**Part** (on the project BOM as FER1): Würth **WE-FSFS 364006** — material 364 (their
13.56 MHz redirection grade), 60 × 60 × 0.3 mm sheet, PET film one face, PSA the other,
laser-scored in a 2 × 2 mm grid so it cuts cleanly to size. One sheet yields four patches.
Non-conductive as supplied. Alternates: MARUWA FSF131/FSF151, Fair-Rite flexible sheets.

**Patch size and position (board coords):** cut to **12.2 × 25.8 mm**, covering
**x 36.8–49.0, y 31.6–57.4** — exactly the antenna keepout box. That is component-free,
flat board back (mask over coil traces + bare laminate). Margins past the outer turn are
~0.45 mm on all sides; more would be better but board features cap it (supercap bodies at
y 31.15 and y 57.75, lip seat east of x 49.8).

**Pocket in the brace (board-facing surface):**
- Outline: patch outline + 0.2 mm cut clearance per side.
- Depth: **t_sheet − 0.05 mm** (nominal sheet 0.30 → pocket 0.25), so the ferrite sits
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

## 5. C9 trim workflow — brace must be removable

The NFC tank is trimmed iteratively: fit C9, assemble, measure, refit. Computed/estimated
trim windows: **~90 pF** bare; **up to ~150 pF** enclosed with no ferrite; **~52–77 pF**
enclosed with the 0.3 mm ferrite (inductance rises above bare, so the trim drops). One
stocked C0G ladder (68/82/100/120/150 pF) covers all three. Two asks:

1. The brace is **seated, not bonded** to the board — removable and reseatable. (PSA-ing
   the ferrite into the brace pocket per §3 keeps this true.)
2. C9's cutout allows tweezers-and-iron access with the brace out.

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
perfect-conductor floor at 1.85 mm bounds L_eff at 0.68 µH (70 % kept). Every option works
for tap-range; with the ferrite, every option approaches bare-card.

## 8. Remaining 0.6 mm items and small notes

- **Cavity math confirmed from your own stack** (0.95 + 1.85 + 0.60 + 0.15 = 3.55): the
  coil-to-floor standoff is unchanged by the thickness change, and the spiral is entirely
  B.Cu — only the ~30 mm F.Cu bridge moves 0.2 mm closer. Sub-1 % inductance effect. No new
  retune burden beyond the parked bench item.
- **TC2030 leg retention at 0.6 mm — verify.** The legged programming cable latches through
  the board; the repo TC2030-MCP.pdf is silent on minimum board thickness. Confirm against
  Tag-Connect's footprint documentation (or bench) before the thickness locks. PCB side
  flagged, either side can close it.
- **Reflow carrier** at 0.6 mm: acknowledged as a PCB-side/order item.
- **Thinner window web is a glow bonus**: 0.8 → 0.6 mm of FR4 under the monogram transmits
  more light.
- **Isolation layering — don't double-stack.** Insulating layers now in the system:
  soldermask (always), the brace + ferrite (middle third), and the optional Kapton blanket.
  The brace-covered middle third needs no Kapton. In the supercap bays the caps sit
  1.70 mm tall under a 1.85 mm cavity — 0.15 mm air; a 0.05 mm Kapton sheet there eats a
  third of that headroom. Decide blanket extent vs brace extent as one plan and send the
  final stack; the PCB side will sanity-check clearances.
- **Shell grounding is unchanged**: the shell ties to board GND through the four corner M2
  screws (3,3 / 47.8,3 / 3,85.9 / 47.8,85.9). The brace and ferrite being inert does not
  affect this; no other contact should be relied on for ground.
- **Freed rib strip** (x 24.9–25.9, y 0–33 and 56–88.9) and the un-locked supercap
  constraint are recorded on the PCB ledger for future revs. No v3.0 action.

— PCB side
