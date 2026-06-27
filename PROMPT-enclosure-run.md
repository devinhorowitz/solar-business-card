# SOLAR-GLOW · DRH v2.1 — Enclosure (Hardware) Run

You are designing the **metal back-shell enclosure** for SOLAR-GLOW DRH v2.1, a solar-powered
glowing business-card PCB. The board is built and frozen; the existing enclosure CAD modeled an
**earlier** board and must be **redesigned, not patched**.

Treat the committed files in the repo (https://github.com/devinhorowitz/solar-business-card) as
the **single source of truth**. The board geometry is measured from the committed PCB — do not
trust the old CAD's hardcoded geometry, and do not rely on any prior conversation or assumption.

## The product

A credit-card-sized PCB: a naked show-front (two solar cells + a backlit "DRH" monogram window)
and a populated back. The enclosure is a thin **back-only** metal shell that hugs the rear,
presses over the board edge, and screws down through four M2 corner bosses. Card-thin is the
whole point.

## Read these first (in order)

1. **`solar-glow-drh-v2-mechanical.md`** — THE design input, pulled straight from the committed
   PCB: board envelope (50.80 × 88.90 × 0.8 mm, R3.0 corners), the four M2 mount holes, the
   back-side **height stack** (§5 — U2 at 1.75 mm and the cells at 1.7 mm are the only drivers),
   the big-part placement (§6), the optical **no-pillar keepout** (§7), grounding/isolation (§9),
   programming access (§10), and the variant axes (§11). **Read §8 first** — it lists exactly
   what changed from the old shell.
2. **`ENCLOSURE-NOTES.md`** — the shell design rules: material (Ti-6Al-4V vs 7075-T6), machining
   (photochemical-etch the shallow reliefs, CNC the walls/bosses), the M2 boss-engagement rule,
   the Kapton-isolation fix, and the CAD knob set.
3. **`enclosure/solar-glow-drh-backshell-cad.py`** — the parametric CadQuery fork-base. It is
   **flagged STALE** (it models the old board). Reuse its scaffolding — boss generation, corner
   fillet, press-fit walls, the parameter block — but **replace the geometry** per the mechanical
   brief.
4. **`solar-glow-drh-v2_1.kicad_pcb`** — open only for exact pad/keepout geometry; the mechanical
   brief already distills it.

## What changed from the old shell (mechanical brief §8 — the crux)

- **Four supercaps, not two**, at both ends of the back (~43% of the board). The old single-pair
  pocket field and pillar map are wrong.
- **No edge castellations** — verified zero pads near the rim, so the old wall-short hazard is
  **gone**; the walls press over bare FR4.
- **No U2 pocket** — U2 (1.75 mm) ≈ the cells (1.7 mm), so a uniform ~1.8 mm cavity, no local
  thin skin.
- **No button** — the actuator is the accelerometer tap (the metal back transmits it), so **no
  button hole and no cap-touch window**.
- VQFN-28 MCU (height-irrelevant at 0.9 mm).

Net: the new shell is **simpler** than the old one.

## Hard rules

- **Pull dimensions from the mechanical brief (or the PCB); never invent them.** Heights are
  datasheet figures.
- **Grounding.** The four M2 screws ground the body. Land support pillars **only on GND pour**,
  or spec a die-cut **Kapton (~0.05 mm)** blanket — any exposed copper (untented vias, the VS
  pour) under the metal is a short. Keep pillars out of the §7 optical zone.
- **Front stays naked** (solar cells + glow window exposed); back-only shell.

## Deliverables

1. A redesigned, parametric **CadQuery model** (fork the CAD file) built to the v2.1
   geometry: 50.80 × 88.90 outline with R3.0 corners, four M2 corner bosses, press-fit walls over
   the bare edge, a uniform ~1.8 mm cavity (no U2 pocket), and a pillar/keepout map that lands on
   GND only and clears the central optical band.
2. **STEP + STL** exports.
3. Parameterize the **variants** (mechanical brief §11): material (Ti-6Al-4V / 7075-T6) and skin
   thickness (standard + a thin ~0.2 mm variant), plus the **TC2030 access** decision
   (flash-before-close vs a back-shell programming window).

Work in the project's style: terse, answer-first, engineer-to-engineer; lead with the
model/decision; ground every dimension in the brief or the PCB.
