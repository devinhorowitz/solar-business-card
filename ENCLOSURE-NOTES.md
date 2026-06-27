# Enclosure design notes — metal back-shell

> **STATUS: PARKED** — on ice pending v2.1 board bring-up (and the programming phase). CAD +
> STEP/STL preserved in this folder; resume after the PCB is validated. The board carries
> **4× WS17 supercaps (3-153-438, 1.7 mm)** arranged around the central glow band (see
> `solar-glow-drh-design-notes.md` §4). Because the cells (1.7 mm) sit just under U2 (1.75 mm),
> the cavity can be a uniform ~1.8 mm with **no U2 pocket** — but the height stack, pillar/
> keepout audit, and SC pockets below still reflect the older single-pair CAD and must be
> re-laid-out for the four-cell placement when this resumes.

Engineering notes for taking the drafted back-shell (`solar-glow-drh-backshell-cad.py`)
to a thin **machined-metal** production part. The CadQuery model is material-agnostic;
these are the decisions and gotchas the material choice forces. Read alongside the
README's enclosure section.

## Concept

A back-only cover that hugs the populated rear of the board: naked front (solar cells and LED apertures exposed), PCB screwed down through the four M2 bosses, four walls
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
| SC1–SC4 supercaps | WS17 (3-153-438) | **1.7 mm** (just under U2) |
| U1 MCU | VQFN-28 (4×4) | ~0.9 mm |
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

## Actuation behind a metal back

Cap-touch was considered and ruled out: a grounded back-plate swamps any self-capacitive
electrode, and the AVR-DD has no PTC hardware anyway. The actuator is the **accelerometer tap**
(U3, LIS2DH12) — and a metal back-plate *helps* here, transmitting the tap as vibration to the
sensor. No electrode, window, or air gap is needed; PA7 is unconnected on the board.

## Mounting

M2 threads want ~3–4 mm of engagement, which a 0.3–0.6 mm floor can't give — so the four
`boss_r` 2.6 mm bosses (which rise the full cavity height) are the right approach; keep
screw features in the thick rails, never in the thin pocket zones. The current blind M2
pilots (`pilot_r` 0.85, tapped from the cavity side) are fine for the metal build.

## MCU package

The MCU is the **28-VQFN (4×4)**, chosen on footprint, not height — U2 sets the ~1.75 mm
floor regardless of the 0.9 mm QFN. Full rationale (why VQFN over SSOP, given the cells eat
~43% of the board) is in `solar-glow-drh-design-notes.md` §5.

## CAD follow-ups (when this gets cut)

- Add an enclosed-variant flag that **drops the right-edge castellations** (or relieves the
  wall over them).
- Spec the **Kapton isolation layer** in assembly (or add a `kapton_th` knob).
- If **7075, not Ti:** bump `u2_skin` / `floor_th`, or default `WINDOW_U2 = True`.
- Re-confirm `cavity` (1.6) against D1's SOD-123 height in `datasheets/MMSD301T1-D.PDF`.
