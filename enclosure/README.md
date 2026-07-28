# SOLAR-GLOW DRH v3.0 — Titanium Back-Shell (enclosure)

Back-only titanium shell for the SOLAR-GLOW DRH PCB. It drops over the populated back of the
board and is held by eight M2 screws (four at the board corners + four at the panel inner corners);
the bare show-front (two solar cells + the backlit DRH monogram window) stays exposed. Retention is
the eight screws clamping, not a press fit.

This is the **0.6 mm-board "dumb box"** shell. It reduces to a floor, walls, eight M2 bosses,
a U7 (FRAM) relief pocket -- nothing else. All center support and all
optical/EMI features live in a separate **resin diffuser brace** (see `brace/`), so a PCB layout
change is a brace reprint, never a shell re-machine. The shell is aligned to
`PCB/solar-glow-drh-v3_0.kicad_pcb` (bosses on the v3.0 8-hole pattern: four corner bosses concentric
with the r3.0 board-corner fillets, plus four panel-corner bosses).

> **Source of truth.** `solar-glow-drh-v3_0-backshell-0p6b-brace-cad.py` is authoritative for all
> geometry — it prints the full Z-stack when run and regenerates the STEP/STL from the PCB anchors.
> Every number in this README is echoed from that generator; if one ever disagrees, re-run it and
> trust the generator. This README is the **fab + ordering companion**, not an independent spec.

## Files

| File | Purpose |
|---|---|
| `solar-glow-drh-v3_0-backshell-0p6b-brace-cad.py` | Parametric CadQuery generator. **Source of truth** — regenerates the STEP/STL from the PCB anchors. |
| `solar-glow-drh-v3_0-backshell-0p6b-brace-Ti-max.step` | **Send this to the fab.** 1.00 floor, 1.80 cavity, 0.60 board recess, U7 (FRAM) relief pocket, no ribs, no locator pillars, 1.0 walls, asymmetric lip (W2.5/N2.0/S2.0/E1.0), 8 M2 bosses, 3.55 overall. |
| `solar-glow-drh-v3_0-backshell-0p6b-brace-Ti-max.stl` | Same geometry, for a quick plastic dry-fit print before committing to titanium. |
| `solar-glow-drh-v3_0-backshell-0p6b-brace-DRAWING.pdf` / `.png` | **Current** 2D dimensioned drawing (plan + Section A-A + Detail B + critical dims + notes + title block). Attach to the CNC quote. |
| `brace/` | The resin diffuser brace — separate printed part. Has its own README, generator, STEP/STL, and drawing. |
| `solar-glow-drh-v2_1-backshell-DRAWING.pdf` / `.png` | **STALE — v2.1 numbers (0.55 floor / 1.90 cavity / 43.80 pitch / brace posts).** Superseded by the drawing above; do **not** send this. Kept only as history; safe to delete. |

The mating PCB, the resin brace, and the eight M2 screws are separate parts, not part of this CNC order.

## What changed from the earlier shells

- **Floor 0.75 → 0.95 → 1.00 (true 1 mm)**, on a **0.60 mm board** (was 0.80). Same 3.55 overall. The final 0.95 → 1.00 step comes from trimming the cavity 1.85 → 1.80 (cap air 0.15 → 0.10): the brace and the solar-cell sandwiches carry the board, and the WS17 datasheet confirms 1.70 mm is the cap **max** height (worst-case gap 0.05 mm). A true 1.00 floor also clears aluminium / copper / stainless, not just Ti.
- **Ribs and locator pillars removed.** The old cap-gap ribs and window posts are gone, and the locator pillars are retired — the resin H-brace carries center support and registers to the shell by fitment (its four outboard rails + the component pockets + the board press-fit). The cavity floor stays a full 1.00 everywhere.
- **Support lip widened and made asymmetric.** The old uniform 1.00 lip is now **W 2.5 / N 2.0 / S 2.0** for a stiffer PCB (widths bounded by the nearest B-side part on each edge). **East stays 1.0** through the JP1/TP1 pads, over the NFC coil (a grounded Ti lip would detune it), and past C7 (x49.55, the one east-edge part left after v4 removed the Q1/U4/R7/R9 clamp cluster and the D9/D10/D11 diodes), which overhangs a wider lip, **widening to 2.5 only at the y0–10 end** clear of them. The exterior back border is independent of the lip and **uniform 2.0 on all 4 sides**.
- **Reflector frame + floor tape dropped.** The monogram window is now backed by the brace's white LED-hug diffuser face, so the laser-marked reflector frame and the adhesive floor strip are no longer used.

## The 2D drawing

`solar-glow-drh-v3_0-backshell-0p6b-brace-DRAWING.pdf` is current and matches the committed STEP
(1.00 floor / 1.80 cavity / 0.60 board recess / 8-hole mount pattern [x 44.80; y rows 3.0/28.5/60.4/85.9] / 3.55 overall).
The old `v2_1` drawing is stale and must not be sent. The **STEP governs** all geometry; the drawing
and the notes below flag the few dimensions that need tighter-than-standard control.

## What to send PCBWay

The **`...-0p6b-brace-Ti-max.step`** + the **`...-0p6b-brace-DRAWING.pdf`** + the callouts below.
Material: **Titanium Gr5 (TC4)**.

## Ordering instructions (PCBWay)

Form settings on the CNC quote page (the on-screen selections override the drawing, so set these to match it):

- **Process:** CNC machining, 3-axis milling.
- **Material:** Titanium → **Titanium Gr5 (TC4)**. **Color:** Silver (natural Ti). *(Bare metal — the shell ties to board GND through the eight screws; do not anodize/plate.)*
- **Units:** mm. **Quantity:** 1 (prototype).
- **Technical drawing:** attach `...-0p6b-brace-DRAWING.pdf`; do not attach the stale v2.1 file.
- **Threads / tapped holes: Yes** — `8× M2×0.4 tapped through, from the back face`.
- **Tolerance: leave on standard / ISO 2768** — do **not** enable "Tighter tolerances required." That toggle trips an automated review gate that rejects the order with a templated "tighter tolerance not specified at position" message even though the drawing marks it. Marked callouts govern regardless of the toggle. Two dims are marked **±0.05**: **C1 cavity depth 1.80 ±0.05** (Section A-A) and **C3 mounting-hole pattern pitch (x 44.80; y rows 3.0/28.5/60.4/85.9) ±0.05** (plan, 8 holes). **C1 is the non-negotiable one.** Flatness C2 = 0.05 rides along as a form callout. Paste into the notes box: *"Two dimensions are marked ±0.05 and must be held as marked: cavity depth 1.80 ±0.05 (Section A-A), and the 8-hole mounting pattern pitch x 44.80 / y rows 3.0/28.5/60.4/85.9 ±0.05 (plan). All other dimensions per ISO 2768-1 medium."*
- **Surface finish: Bead blasting** (matte, uniform on the stepped back face) — **not Brushed.** The back face is stepped (recessed art field, raised frame and boss annuli), so a brushed grain cannot run continuously; bead-blast covers into the corners and gives better laser-mark contrast.
- **Surface roughness:** 250 µin / 6.3 µm Ra (default).
- **Finished appearance: Standard** for the first article.
- **Inspection: Standard Inspection with Formal Report** (you want the measured cavity depth and floor thickness back). CMM-with-report if you also want flatness and hole position verified.
- **Part marking:** none (rear branding/art is a later laser step).
- **Product description:** DIY / Demonstration model.

Paste into **Other special request**:

```
- Cavity floor is a uniform 1.00 mm, with one shallow relief pocket under U7 that
  takes the local floor to 0.95 mm over a 7.8 x 5.4 mm area only. If you cannot
  reliably hold 1.00 mm titanium over this ~48 x 86 mm pocket, advise the minimum
  floor you can hold and we will re-issue the STEP.
- No locator pillars: the resin H-brace registers by fitment (4 outboard rails +
  component pockets + board press-fit). Cavity floor is a full 1.00 everywhere.
- 8x M2 x 0.4 tapped through-holes, tapped from the back face. (M2 x 0.4 is a
  standard coarse thread; please tap per this note rather than letting the 0.6 mm
  minimum-pitch auto-checker reject it.)
- Break all sharp edges ~0.1 mm (titanium).
```

Expect the instant price to move: the thin floor routes this to manual engineering review, which is where the floor answer comes from.

---

## CNC fabrication notes / drawing callouts

### Title / process

| Field | Value |
|---|---|
| Part | SOLAR-GLOW DRH v3.0 back-shell — 0.6 mm-board dumb box (single piece) |
| Revision | v3.0 (0.6-board dumb box: 1.00 floor, 1.80 cavity, no ribs, no locator pillars) |
| Material | **Titanium Gr5 (TC4) = Ti-6Al-4V Grade 5** (PCBWay stock) |
| Process | 3-axis CNC milling, 2 setups (cavity face + back face) |
| Finish | Bead-blast matte. Rear art laser-marked in the recessed field after finishing. |
| Source model | `solar-glow-drh-v3_0-backshell-0p6b-brace-Ti-max.step` |
| Units | mm |

### 1. Overall dimensions and datum

- Bounding box: **52.70 × 90.80 × 3.55 mm**.
- Datum **Z0 = outer back face**. +Z is into the part toward the PCB.
- Z stack from the back face:
  - back frame and 4 boss annuli: **proud 0.15 mm** (to Z −0.15)
  - recessed rear art field: at Z 0
  - cavity floor: at **Z +1.00** (0.95 local under the U7 pocket)
  - boss / lip tops (the PCB rest plane): **Z +2.80**
  - PCB recess: Z +2.80 to +3.40 (receives the 0.60 mm board)
- Wall 1.00 mm. **Asymmetric perimeter lip: W 2.5 / N 2.0 / S 2.0 / E 1.0 mm (E widens to 2.5 at the N/S ends).** Exterior back border is **uniform 2.0 on all 4 sides** (independent of the lip).** Back-frame step 0.15 mm. **No internal ribs or posts.**

### 2. Critical dimensions — flag these for tighter control

Default everything to ISO 2768-1 general. Control **only** the items below.

| # | Feature | Nominal | Requested tolerance | Why |
|---|---|---|---|---|
| C1 | Cavity depth (boss-top plane → cavity floor) | **1.80 mm** | **±0.05** | Range 1.75–1.85. Air gap over the four 1.70 mm WS17 supercaps (datasheet **max** height): 0.05–0.15 mm. Must not be under 1.70 or the floor contacts the caps. |
| C2 | PCB-rest plane flatness (lip + 8 bosses, coplanar at Z +2.80) | — | flatness **0.05 mm** | Board must seat flat so the screws clamp evenly. |
| C3 | 8× mounting-hole pattern (pitch, linear) | x 44.80 / y rows 3.0·28.5·60.4·85.9 mm | **±0.05** | Must align with the PCB's 8 M2 holes (MH1–4 corners + 4 panel-corner). |
| C4 | Mounting-hole diameter (tapped) | **M2** (tap-drill Ø1.6, through) | standard | Thread fit for the M2 screws. |

> **Cavity note.** The cavity is **cap-limited**: the four WS17 supercaps set it. The SCHURTER SCPC datasheet (Case WS17) gives height **max 1.7 mm** and body 28.5 +0.5/−0.0 long, so the general cavity is **1.80 mm** (0.10 nominal air; worst-case 1.75 − 1.70 = 0.05, non-contact). ~~U7 (FRAM, SOIC-8, 1.75 mm) is the single tallest part but sits over the local relief pocket (note 7), which drops the floor 0.05 mm there so U7 keeps a 0.10 mm air gap.~~ The freed 0.05 mm went into the floor (0.95 → 1.00).
>
> **⚠ Superseded 2026-07-28 — U7 is no longer a tall pole, and this was written when it was.** The v4
> board carries the **DFN-8**, not a SOIC-8: `PCB/solarglow.pretty/U7_DFN8.kicad_mod` `descr` quotes
> RAMXEED DS501-00087-1v0-E p.21 for a **5.00 × 6.00 mm body, 0.90 mm MAX** height, and
> `PCB/README.md` agrees. That is **0.85 mm shorter** than the 1.75 assumed here, and well under the
> 1.70 mm the supercaps already demand — so U7 clears the uniform 1.00 mm floor with 0.80 mm to
> spare and the note-7 relief pocket is **not needed for clearance**. The cavity stays cap-limited
> at 1.80 either way, so nothing here is unsafe; the pocket is simply machining that buys nothing.
> **Decide before the next fab order** whether to keep it (harmless, already modelled and quoted) or
> drop it and take the floor back to a true uniform 1.00 mm. Tracked in `TODO.md`.

### 3. Thin-wall advisory (read before quoting)

The cavity floor is a **uniform 1.00 mm** (0.95 mm over the small U7 relief pocket only). That is
still below the titanium min-wall guidance (~1.0 mm) but a healthy step above the earlier 0.55/0.75.
The floor no longer has ribs behind it (the resin brace carries center support in service, but is
not present during machining). Please proceed one of two ways and note which on the quote:

- **(A)** Machine the uniform 1.00 mm floor **as-is**; or
- **(B)** If you cannot reliably hold 1.00 mm, advise the **minimum floor you will hold** in Ti-6Al-4V for this ~48 × 86 mm pocket, and we will re-issue the model.

### 4. Brace registration (no locator pillars)

- **Retired.** The resin H-brace registers to this shell by **fitment** — its four outboard rails run into the cavity beside the supercaps, the component pockets key it to the board, and the board press-fits into the recess. No pillars, no recesses, no locating holes; the cavity floor is a full **1.00 mm** everywhere.

### 5. Threads / tapped holes

- 8× **M2** tapped, **through-holes**, drilled Ø1.6 then tapped, from the **back face**. Engagement ~2.2 mm.
- M2 coarse pitch is 0.4 mm, below the 0.6 mm minimum-pitch gate on the quote form — tap per this note.
- Bosses (r2.60): the four **corner** bosses sit a uniform 0.40 mm off the cavity corner wall (a sub-Ø2.0-cutter cusp that fuses into the corner); the four **panel-corner** bosses stand in the west field / merge into the pinched east lip.
- Customer-supplied fasteners: 8× **brass M2 × 3 mm slotted cheese head**, head Ø3.8 (DIN 84). Tip seats flush in the back spotface (note 6).

### 6. Spotfaces

- 8× back-face spotface **Ø3.0 mm**, concentric with the mounting holes, depth ~0.2 mm (screw tip seats flush below the proud boss annulus). Modeled.

### 7. U7 (FRAM) relief pocket

- **7.8 × 5.4 mm** in the cavity floor, centered at board **(28.1, 37.3)**, **0.05 mm deep** (local floor 0.95), R1.0 corners. ~~U7 (1.75) keeps 0.10 mm air.~~ General floor stays 1.00. Modeled.
- **⚠ 2026-07-28: this pocket no longer has a reason to exist.** It was cut for a 1.75 mm SOIC-8; the
  v4 board's U7 is the **0.90 mm MAX DFN-8**, which clears the uniform 1.00 mm floor by 0.80 mm. Keep
  it or drop it — see the cavity note in §2. It is already modelled and quoted, so keeping it costs
  nothing but a pocket; dropping it simplifies the floor.

### 8. Press fit — do NOT rely on it

PCB recess flats are modeled 0.05 mm interference (below CNC tolerance) — treat as a **slip fit**; the eight screws retain and clamp.

### 9. Internal radii and tooling

Internal concave junctions are modeled **sharp**; a round tool leaves its own fillet (standard for a milled pocket). The whole solid is analytic (planes, cylinders, cones) — verified 167 analytic faces, zero spline/Bezier. Rough the cavity with a Ø3–4 mm tool; finish corners/walls with a Ø2.0.

### 10. Edge break / deburr (note, do not model)

**Break all sharp edges ~0.1 mm (titanium).** All exposed edges are broken 0.10 × 45°, meant to be felt but not seen (modeled). The named breaks called out on Section A-A / Detail B are: the outer rim (top and bottom), the recess mouth around the board, the inner (cavity-side) lip edge, the proud back-frame bottom edges, and the boss/spotface bottom edges. The concave seat and junction corners are left sharp in the model and take the tool's own radius. Deburr all other exposed edges and hole exits.

### 11. Inspection

- Report C1–C3 on the FAI. Confirm the achieved cavity floor thickness (the at-risk dimension).

---

## Board-side electrical caveats (grounded shell)

The eight M2 screws thread into the titanium body, and the PCB mount pads (the four MH1–4 corners plus
the four panel-corner holes) are **GND** and overlap the front-side gold plating frame, so the shell is
tied to board GND through the screws. Two
consequences the board must respect in an enclosed build:

- **Edge castellations** (any VS/SDA/SCL at the board rim) would short against the grounded press-fit walls — drop them or add a die-cut ~0.05 mm Kapton isolation layer.
- **Capacitive touch is dead** behind a grounded metal plate — the actuator is the accelerometer tap, not a self-cap button.

## Design lineage

- **v2.1 shell** (`solar-glow-drh-v2_1-backshell-*`): 0.55 floor, 1.90 cavity, brace posts, old 3.5 mm hole inset. Matches the old PCB hole positions. **Superseded.**
- **v3.0 0.75-floor ribbed shell** (interim, not in this folder): floor pushed to 0.75, braces removed, two cap-gap ribs added, U2 pocket added, holes re-symmetrized to the v3.0 pattern. **Superseded** by the dumb box.
- **v3.0 0.6-board dumb box** (this README, `...-0p6b-brace-*`): 0.60 board frees the floor to 1.00 (cavity 1.80); ribs and locator pillars removed; the resin H-brace (`brace/`) carries center support and registers by fitment, and the window/EMI features; reflector frame and floor tape dropped. Overall stays 3.55.

---

*Part of SOLAR-GLOW · DRH. © 2026 Devin R. Horowitz. MIT License (see `../LICENSE`).*
