# Enclosure design notes — metal back-shell

> **STATUS: PARKED** (as of V1 kickoff) — on ice pending V1 board bring-up. CAD + STEP/STL
> preserved in this folder; resume after the V1 PCB is validated. Note: the V1 supercap swap
> to 3-153-438 (1.7 mm) lets `cavity` go to ~1.8 mm and **deletes the U2 pocket** — see
> `../docs/V1-PLAN.md` §1. If V1 instead goes **4-cell** (§1a there), that changes cap
> *placement* (four cells at opposite ends of the back), **not** the 1.7 mm height — but the
> pillar/keepout audit and the SC pockets below would need re-laying-out for four cells.

Engineering notes for taking the drafted back-shell (`solar-glow-drh-backshell-cad.py`)
to a thin **machined-metal** production part. The CadQuery model is material-agnostic;
these are the decisions and gotchas the material choice forces. Read alongside the
README's *"The enclosure"* section.

## Concept

A back-only cover that hugs the populated rear of the board: naked front (solar cell,
dome, LED apertures exposed), PCB screwed down through the four M2 bosses, four walls
press-fit over the board edge. The goal is a card-thin product, so the cover rides as
close to the board back as the tallest part allows, with a **local blind pocket** over
that part rather than lifting the whole floor.

Current profile (from the CAD): `floor_th` 0.6 mm skin + `cavity` 1.6 mm gap =
**~2.2 mm behind the board** (~3.0 mm total over the 0.8 mm board). The 1.6 mm cavity is
set by the SOD-123 blocking diode (D1, ~1.1–1.35 mm); the one part taller than the cavity
— **U2, the supercap balancer at 1.75 mm** — sits in a floor pocket that thins the outer
skin to `u2_skin` 0.3 mm locally.

## Back-side height stack

What the cover has to clear, tallest first (max heights; datasheet-grounded where checked):

| Part | Package | Height |
|---|---|---|
| U2 balancer | SOIC-8 | **~1.75 mm** ← gets a local pocket |
| D1 blocking diode | SOD-123 | ~1.1–1.35 mm ← sets the 1.6 mm cavity |
| SC1 / SC2 supercaps | WS10 → **WS17** (v1) | 1.0 → **1.7** mm (just under U2) |
| U1 MCU | QFN-20 | ~0.9 mm |
| D2–D5 LEDs | LA P47F | 0.83 mm (datasheet) |
| C1–C3 | 0805 | ~0.7 mm |
| R1–R4 | 1206 | ~0.6 mm |

U2 is the height floor; everything else lives under the 1.6 mm cavity.

## Material

Going **metal** is what lets the skin be thin enough to stay card-like, and strength is
the lever. The thin spots in the current model — `floor_th` 0.6 mm overall, `u2_skin`
**0.3 mm** over the U2 pocket — are the constraint:

- **Titanium (Ti-6Al-4V, Grade 5)** — the pick for max strength + stiffness at minimum
  thickness/weight. Yield ~880 MPa and ~1.6× stiffer than aluminum, so the 0.3 mm U2 skin
  and 0.6 mm floor hold without denting. ~23 g for the solid.
- **7075-T6 aluminum** — the value alternative. Yield ~500 MPa (vs ~276 for 6061),
  anodizes well, and is **far** cheaper/faster to machine. At a 0.3 mm skin it's marginal —
  bump `u2_skin` / `floor_th` if you go 7075, or default the U2 *window* (below). ~14 g.
- **6061-T6** — too soft at these skins; needs a thicker floor, which kills the profile.
- **Brass** — show-piece only; heavy (~44 g) and soft.

**Machining reality:** blind pockets in titanium are slow and tool-hungry (Ti work-hardens
and eats end mills) → it's the expensive option to mill. Two softeners: machine it in
**7075** instead, or keep titanium but cut the shallow reliefs (the U2 pocket, the cavity
floor) by **photochemical etching** — cheap for thin sheet and well-suited to relief
features — then finish-machine only the walls and bosses.

## Electrical: the body grounds to the board

The gotcha metal forces and the CAD doesn't yet handle. The four M2 bosses land on the
board's **grounded** mounting holes, so the screws tie the whole metal body to board GND.
That's good — it becomes a shield at a defined potential — but it means **every non-GND
feature the metal touches is a short to ground.** Two concrete hits in the current geometry:

1. **The press-fit walls short the castellated edge pads.** The right-edge castellations
   are VS / SDA / SCL / GND / GND (y ≈ 22–31 mm). The walls run interference against that
   edge (`edge_fit` −0.05) and contact the plated half-holes → VS, SDA, and SCL short to the
   GND body. **Fix (cleanest): drop the edge castellations in the enclosed variant** — a
   boxed module doesn't need an edge bus. Otherwise relieve the wall locally over y ≈ 22–32
   on the right edge, or insulate the edge.
2. **Support pillars / shelf can land on live copper.** The pillar field avoids parts,
   headers, and vias, but still presses on soldermask over whatever pour or trace is beneath.
   Mask (~20 µm) is a weak insulator under a press-fit load, and any *exposed* copper (test
   points, untented vias, the VS pour) is a direct short to the GND body. **Audit pillar/
   shelf landings against the VS pour** — land them only on GND pour (harmless) — or add a
   die-cut **Kapton film (~0.05 mm)** between board back and cover, the simplest blanket fix
   and negligible against the thickness budget.

## Cap-touch fights the metal

A grounded plate directly behind the **PA7 self-cap electrode** swamps it with capacitance
to ground — touch sensitivity likely dies. With a metal back, treat the **snap dome as the
real button** and cap-touch as expendable (this settles the dual-mode-button question for
the enclosed build). To keep touch, the electrode needs a clear window + air gap in the
metal directly behind it, and even then the nearby grounded metal hurts. See punch-list §5.

## Mounting

M2 threads want ~3–4 mm of engagement, which a 0.3–0.6 mm floor can't give — so the four
`boss_r` 2.6 mm bosses (which rise the full cavity height) are the right approach; keep
screw features in the thick rails, never in the thin pocket zones. The current blind M2
pilots (`pilot_r` 0.85, tapped from the cavity side) are fine for the metal build.

## MCU package interplay

Because U2 already puts 1.75 mm on the back, a leaded **v1 MCU costs almost nothing in
height**: SSOP-28 (~2.0 mm) is ~+0.25 mm over U2, SOIC-28 (~2.65 mm) ~+0.9 mm, and a QFN's
thinness is wasted while U2 sits at 1.75 mm. The thin enclosure does **not** argue for a QFN
MCU unless U2 is also re-spec'd to a thinner balancer (a DFN/SOT-23-class part). See
punch-list §7 for the part/package decision.

## CAD follow-ups (when this gets cut)

- Add an enclosed-variant flag that **drops the right-edge castellations** (or relieves the
  wall over them).
- Spec the **Kapton isolation layer** in assembly (or add a `kapton_th` knob).
- If **7075, not Ti:** bump `u2_skin` / `floor_th`, or default `WINDOW_U2 = True`.
- Re-confirm `cavity` (1.6) against D1's SOD-123 height in `datasheets/MMSD301T1-D.PDF`.
