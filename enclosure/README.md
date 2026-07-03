# SOLAR-GLOW DRH v3.0 — Titanium Back-Shell (enclosure)

Back-only titanium shell for the SOLAR-GLOW DRH PCB. It drops over the populated back of the
board and is held by four corner M2 screws; the bare show-front (two solar cells + the backlit
DRH monogram window) stays exposed. Retention is the four screws clamping, not a press fit.

This is the **0.6 mm-board "dumb box"** shell. It reduces to a floor, walls, four corner bosses,
a U2 relief pocket, and **two metal locator pillars** — nothing else. All center support and all
optical/EMI features live in a separate **resin diffuser brace** (see `brace/`), so a PCB layout
change is a brace reprint, never a shell re-machine. The shell is aligned to
`PCB/solar-glow-drh-v3_0.kicad_pcb` (bosses on the v3.0 hole pattern, concentric with the r3.0
board-corner fillets).

> **Source of truth.** `solar-glow-drh-v3_0-backshell-0p6b-brace-cad.py` is authoritative for all
> geometry — it prints the full Z-stack when run and regenerates the STEP/STL from the PCB anchors.
> Every number in this README is echoed from that generator; if one ever disagrees, re-run it and
> trust the generator. This README is the **fab + ordering companion**, not an independent spec.

## Files

| File | Purpose |
|---|---|
| `solar-glow-drh-v3_0-backshell-0p6b-brace-cad.py` | Parametric CadQuery generator. **Source of truth** — regenerates the STEP/STL from the PCB anchors. |
| `solar-glow-drh-v3_0-backshell-0p6b-brace-Ti-max.step` | **Send this to the fab.** 0.95 floor, 0.60 board recess, U2 relief pocket, 2 locator pillars, no ribs, 1.0 walls/lip, 3.55 overall. |
| `solar-glow-drh-v3_0-backshell-0p6b-brace-Ti-max.stl` | Same geometry, for a quick plastic dry-fit print before committing to titanium. |
| `solar-glow-drh-v3_0-backshell-0p6b-brace-DRAWING.pdf` / `.png` | **Current** 2D dimensioned drawing (plan + Section A-A + Detail B + critical dims + notes + title block). Attach to the CNC quote. |
| `brace/` | The resin diffuser brace — separate printed part. Has its own README, generator, STEP/STL, and drawing. |
| `solar-glow-drh-v2_1-backshell-DRAWING.pdf` / `.png` | **STALE — v2.1 numbers (0.55 floor / 1.90 cavity / 43.80 pitch / brace posts).** Superseded by the drawing above; do **not** send this. Kept only as history; safe to delete. |

The mating PCB, the resin brace, and the four M2 screws are separate parts, not part of this CNC order.

## What changed from the earlier shells

- **Floor 0.75 → 0.95**, on a **0.60 mm board** (was 0.80). Same 3.55 overall: the thinner board frees the floor, which nearly doubles safe back-engraving depth and clears more machinable metals.
- **Ribs removed; two metal locator pillars added.** The old cap-gap ribs and window posts are gone — the resin brace carries center support. Two Ø3.0 × 0.4 pillars stand on the cavity floor at (13, 35) and (33, 55) (both west of the NFC coil) and locate the brace via matching recesses. They are left as islands in the same cavity pass as the bosses, so the floor stays a full 0.95 everywhere (no locating holes).
- **Reflector frame + floor tape dropped.** The monogram window is now backed by the brace's white LED-hug diffuser face, so the laser-marked reflector frame and the adhesive floor strip are no longer used.

## The 2D drawing

`solar-glow-drh-v3_0-backshell-0p6b-brace-DRAWING.pdf` is current and matches the committed STEP
(0.95 floor / 1.85 cavity / 0.60 board recess / 44.80 × 82.90 pitch / metal pillars / 3.55 overall).
The old `v2_1` drawing is stale and must not be sent. The **STEP governs** all geometry; the drawing
and the notes below flag the few dimensions that need tighter-than-standard control.

## What to send PCBWay

The **`...-0p6b-brace-Ti-max.step`** + the **`...-0p6b-brace-DRAWING.pdf`** + the callouts below.
Material: **Titanium Gr5 (TC4)**.

## Ordering instructions (PCBWay)

Form settings on the CNC quote page (the on-screen selections override the drawing, so set these to match it):

- **Process:** CNC machining, 3-axis milling.
- **Material:** Titanium → **Titanium Gr5 (TC4)**. **Color:** Silver (natural Ti). *(Bare metal — the shell ties to board GND through the four screws; do not anodize/plate.)*
- **Units:** mm. **Quantity:** 1 (prototype).
- **Technical drawing:** attach `...-0p6b-brace-DRAWING.pdf`; do not attach the stale v2.1 file.
- **Threads / tapped holes: Yes** — `4× M2×0.4 tapped through, from the back face`.
- **Tolerance: leave on standard / ISO 2768** — do **not** enable "Tighter tolerances required." That toggle trips an automated review gate that rejects the order with a templated "tighter tolerance not specified at position" message even though the drawing marks it. Marked callouts govern regardless of the toggle. Two dims are marked **±0.05**: **C1 cavity depth 1.85 ±0.05** (Section A-A) and **C3 mounting-hole pattern pitch 44.80 / 82.90 ±0.05** (plan). **C1 is the non-negotiable one.** Flatness C2 = 0.05 rides along as a form callout. Paste into the notes box: *"Two dimensions are marked ±0.05 and must be held as marked: cavity depth 1.85 ±0.05 (Section A-A), and mounting-hole pattern pitch 44.80 / 82.90 ±0.05 (plan). All other dimensions per ISO 2768-1 medium."*
- **Surface finish: Bead blasting** (matte, uniform on the stepped back face) — **not Brushed.** The back face is stepped (recessed art field, raised frame and boss annuli), so a brushed grain cannot run continuously; bead-blast covers into the corners and gives better laser-mark contrast.
- **Surface roughness:** 250 µin / 6.3 µm Ra (default).
- **Finished appearance: Standard** for the first article.
- **Inspection: Standard Inspection with Formal Report** (you want the measured cavity depth and floor thickness back). CMM-with-report if you also want flatness and hole position verified.
- **Part marking:** none (rear branding/art is a later laser step).
- **Product description:** DIY / Demonstration model.

Paste into **Other special request**:

```
- Cavity floor is a uniform 0.95 mm, with one shallow relief pocket under U2 that
  takes the local floor to 0.90 mm over a 7.8 x 5.4 mm area only. If you cannot
  reliably hold 0.95 mm titanium over this ~48 x 86 mm pocket, advise the minimum
  floor you can hold and we will re-issue the STEP.
- Two Ø3.0 x 0.4 mm metal pillars stand on the cavity floor (locators for a resin
  insert). Leave them as islands in the cavity pass; do not drill them through.
- 4x M2 x 0.4 tapped through-holes, tapped from the back face. (M2 x 0.4 is a
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
| Revision | v3.0 (0.6-board dumb box: 0.95 floor, metal locator pillars, no ribs) |
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
  - cavity floor: at **Z +0.95** (0.90 local under the U2 pocket)
  - locator pillar tops: at **Z +1.35** (0.4 tall, on the cavity floor)
  - boss / lip tops (the PCB rest plane): **Z +2.80**
  - PCB recess: Z +2.80 to +3.40 (receives the 0.60 mm board)
- Wall 1.00 mm, perimeter lip 1.00 mm, back-frame step 0.15 mm. **No internal ribs or posts.**

### 2. Critical dimensions — flag these for tighter control

Default everything to ISO 2768-1 general. Control **only** the items below.

| # | Feature | Nominal | Requested tolerance | Why |
|---|---|---|---|---|
| C1 | Cavity depth (boss-top plane → cavity floor) | **1.85 mm** | **±0.05** | Range 1.80–1.90. Air gap over the four 1.70 mm WS17 supercaps: 0.10–0.20 mm. Must not be under 1.80 or the floor contacts the caps. |
| C2 | PCB-rest plane flatness (lip + 4 corner bosses, coplanar at Z +2.80) | — | flatness **0.05 mm** | Board must seat flat so the screws clamp evenly. |
| C3 | 4× mounting-hole pattern (pitch, linear) | 44.80 × 82.90 mm | **±0.05** | Must align with PCB mounts MH1–4 (v3.0 positions). |
| C4 | Mounting-hole diameter (tapped) | **M2** (tap-drill Ø1.6, through) | standard | Thread fit for the M2 screws. |

> **Cavity note.** The cavity is **cap-limited**: the four WS17 supercaps (1.70 mm) are the tallest cavity-setting parts, so the general cavity is 1.85 mm. U2 (SOIC-8, 1.75 mm) is the single tallest part but sits over the local relief pocket (note 7), which drops the floor 0.05 mm there so U2 keeps its full 0.15 mm air. That is why the general cavity can be 1.85 rather than 1.90.

### 3. Thin-wall advisory (read before quoting)

The cavity floor is a **uniform 0.95 mm** (0.90 mm over the small U2 relief pocket only). That is
still below the titanium min-wall guidance (~1.0 mm) but a healthy step above the earlier 0.55/0.75.
The floor no longer has ribs behind it (the resin brace carries center support in service, but is
not present during machining). Please proceed one of two ways and note which on the quote:

- **(A)** Machine the uniform 0.95 mm floor **as-is**; or
- **(B)** If you cannot reliably hold 0.95 mm, advise the **minimum floor you will hold** in Ti-6Al-4V for this ~48 × 86 mm pocket, and we will re-issue the model.

### 4. Locator pillars

- **2× Ø3.0 × 0.4 mm** metal pillars standing on the cavity floor at board **(13, 35)** and **(33, 55)** — both west of the NFC coil region. Left as **islands** in the cavity milling pass (the four bosses are already islands, so no new operation). Modeled in the STEP.
- They locate the resin brace via matching recesses, brace-side (one round datum + one slot). **Do not drill them through** — the floor stays a full 0.95 mm beneath them.

### 5. Threads / tapped holes

- 4× **M2** tapped, **through-holes**, drilled Ø1.6 then tapped, from the **back face**. Engagement ~2.2 mm.
- M2 coarse pitch is 0.4 mm, below the 0.6 mm minimum-pitch gate on the quote form — tap per this note.
- Bosses (r2.60) sit a uniform 0.40 mm off the cavity corner wall (a sub-Ø2.0-cutter cusp that fuses into the corner).
- Customer-supplied fasteners: 4× **brass M2 × 3 mm slotted cheese head**, head Ø3.8 (DIN 84). Tip seats flush in the back spotface (note 6).

### 6. Spotfaces

- 4× back-face spotface **Ø3.0 mm**, concentric with the mounting holes, depth ~0.2 mm (screw tip seats flush below the proud boss annulus). Modeled.

### 7. U2 relief pocket

- **7.8 × 5.4 mm** in the cavity floor, centered at board **(28.5, 37.0)**, **0.05 mm deep** (local floor 0.90), R1.0 corners. Clearance for U2 (1.75). General floor stays 0.95. Modeled.

### 8. Press fit — do NOT rely on it

PCB recess flats are modeled 0.05 mm interference (below CNC tolerance) — treat as a **slip fit**; the four screws retain and clamp.

### 9. Internal radii and tooling

Internal concave junctions are modeled **sharp**; a round tool leaves its own fillet (standard for a milled pocket). The whole solid is analytic (planes, cylinders, cones) — verified 139 analytic faces, zero spline/Bezier. Rough the cavity with a Ø3–4 mm tool; finish corners/walls with a Ø2.0.

### 10. Edge break / deburr (note, do not model)

**Break all sharp edges ~0.1 mm (titanium).** Outer top/bottom rim eased 0.20 × 45° (modeled). Deburr all other exposed edges and hole exits.

### 11. Inspection

- Report C1–C3 on the FAI. Confirm the achieved cavity floor thickness (the at-risk dimension).

---

## Board-side electrical caveats (grounded shell)

The four M2 screws thread into the titanium body, and the PCB mount pads (MH1–4) are **GND** and
overlap the front-side gold plating frame, so the shell is tied to board GND through the screws. Two
consequences the board must respect in an enclosed build:

- **Edge castellations** (any VS/SDA/SCL at the board rim) would short against the grounded press-fit walls — drop them or add a die-cut ~0.05 mm Kapton isolation layer.
- **Capacitive touch is dead** behind a grounded metal plate — the actuator is the accelerometer tap, not a self-cap button.

## Design lineage

- **v2.1 shell** (`solar-glow-drh-v2_1-backshell-*`): 0.55 floor, 1.90 cavity, brace posts, old 3.5 mm hole inset. Matches the old PCB hole positions. **Superseded.**
- **v3.0 0.75-floor ribbed shell** (interim, not in this folder): floor pushed to 0.75, braces removed, two cap-gap ribs added, U2 pocket added, holes re-symmetrized to the v3.0 pattern. **Superseded** by the dumb box.
- **v3.0 0.6-board dumb box** (this README, `...-0p6b-brace-*`): 0.60 board frees the floor to 0.95; ribs removed; two metal locator pillars added; the resin brace (`brace/`) carries center support and the window/EMI features; reflector frame and floor tape dropped. Overall stays 3.55.

---

*Part of SOLAR-GLOW · DRH. © 2026 Devin R. Horowitz. MIT License (see `../LICENSE`).*
