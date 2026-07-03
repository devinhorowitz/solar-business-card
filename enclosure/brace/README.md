# SOLAR-GLOW DRH — Resin Diffuser Brace

A single printed resin insert that drops into the titanium back-shell cavity, on top of the
populated back of the PCB. It is **not fastened and not bonded** — it is held by the shell clamping
down, and it lifts straight out. It does three jobs the bare shell deliberately does not:

1. **Center support** — fills the 1.85 mm cavity and props the middle of the thin board so the shell's floor can stay a plain 0.95 mm with no internal ribs.
2. **Window backing** — a solid white face sits right behind the FR4 monogram window and turns the four reverse-mount LEDs into an even amber lightbox (no aperture, no reflector tape).
3. **NFC ferrite carrier** — an open channel over the coil holds a ferrite strip that lifts the antenna off the grounded titanium.

> **Source of truth.** `solar-glow-drh-diffuser-brace-cad.py` is authoritative. It reads
> `PCB/solar-glow-drh-v3_0.kicad_pcb`, subtracts every B-side component footprint at its verified
> height, and writes the STEP/STL. Re-run it if the board changes; the brace is a reprint, not a
> shell change.

## Files

| File | Purpose |
|---|---|
| `solar-glow-drh-diffuser-brace-cad.py` | Parametric CadQuery generator. **Source of truth.** |
| `solar-glow-drh-diffuser-brace.step` | Solid model. |
| `solar-glow-drh-diffuser-brace.stl` | **Print this.** SLA mesh. |
| `solar-glow-drh-diffuser-brace-DRAWING.pdf` / `.png` | Print/spec sheet: board-facing plan + Section B-B + the material, ferrite, locator, and assembly notes. |

## Material and printing

- **Process:** SLA / resin print (e.g. PCBWay resin).
- **Material: tough white resin.** It must be **opaque-white and non-conductive** — do **not** use a carbon- or graphite-filled resin. The brace rests directly on GND / VS / signal copper, so it has to be a dielectric; white also drives the window backing.
- **Fit:** print ~0.1 mm proud in height, then **sand the flat bottom (the datum) down** to a zero-air fit in the 1.85 mm cavity. Every pocket is on the **top** face, so the bottom laps flat on glass without touching them. **Do not sand the top** — it sets the pocket depths.
- Mass ~2.2 g.

## Key features

- **Flat bottom = datum.** The board-facing (top) face carries all the pockets; the shell-facing (bottom) face is flat and is the sanding reference (above).
- **Locator recesses:** 2× **Ø3.2 × 0.8 deep** in the flat bottom at board (13, 35) and (33, 55). They receive the shell's 2× **Ø3.0 × 0.6** metal pillars (0.6 engagement, 0.1 radial + 0.2 axial clearance). This is the only tie between the brace and the shell.
- **Ferrite channel** (over the NFC coil): an **open-ended** channel — walled on the **12 mm width (critical, it is edge-limited by the coil/board east edge)** and **open at both ends** (length is forgiving), **0.33 mm** deep. Takes a Würth WE-FSFS 364006 ferrite, nominal **12 × 26 mm** (even on the sheet's 2 mm score grid), PSA'd in; it may overhang the ends slightly.
- **Window = LED-hug diffuser backing:** solid white resin fills the monogram-window footprint behind the FR4, minus tight D2–D5 LED pockets. No aperture, no floor tape. The LED-pocket clearance doubles as a reservoir if a viscous optical gel is pre-filled at final assembly (optional).
- **U2 is the one through-pocket** (it is the tallest B-side part, 1.75 mm). Everything else sits in blind pockets at its verified height.

## Removable — keep it that way during bring-up

The brace must lift out for NFC **C9 trim** during bench bring-up (bare-card first, then re-trim
after the titanium shell is on). Keep it a **dry fit** while iterating; add any optical gel only on
the final card, and re-apply it on every removal.

---

*Part of SOLAR-GLOW · DRH. © 2026 Devin R. Horowitz. MIT License (see `../../LICENSE`).*
