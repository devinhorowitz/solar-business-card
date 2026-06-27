# SOLAR-GLOW · DRH — As-Built Mechanical Reference (v2.1)

**The single source of truth for the enclosure.** Every dimension and coordinate here is read
from the committed `solar-glow-drh-v2_1.kicad_pcb` (KiCad frame: origin top-left, X across the
50.8 mm width, Y down the 88.9 mm length). Heights are datasheet figures for the populated parts.

The board changed materially from the shell modeled in `enclosure/` — **four supercaps instead of
two, no edge castellations, no U2 pocket needed, VQFN-28 not QFN-20, and an accelerometer tap
instead of a button.** The existing CAD therefore has to be **redesigned against the geometry
below, not patched.** §8 lists exactly what changed.

---

## 1. Board envelope

- **50.80 × 88.90 mm**, **0.8 mm** FR4, ENIG finish, matte-black soldermask.
- Rounded rectangle, **corner radius 3.0 mm** on all four corners (verified from Edge.Cuts).
- Front face is the show side (naked); the cover is a **back-only shell** that hugs the populated
  rear and presses over the board edge.

## 2. Mounting (4× M2)

Four plated through-holes, **2.2 mm drill**, all tied to **GND**:

| Hole | (x, y) |
|------|--------|
| MH3 | (3.5, 3.0) |
| MH4 | (47.3, 3.0) |
| MH1 | (3.5, 85.9) |
| MH2 | (47.3, 85.9) |

All four corners, inset 3.5 mm from the long edges and 3.0 mm from the short edges. The screws tie
the metal body to GND (intended — the shell becomes a grounded shield). M2 wants 3–4 mm of thread
engagement, so the **bosses must rise the full cavity height**; a thin floor cannot tap.

## 3. Which side is what

- **FRONT (naked, stays exposed):** the two solar cells, the central glow window (DRH monogram),
  and the four corner mount-hole entries. The shell does not cover the front.
- **BACK (the shell hugs this):** everything else — 4 supercaps, MCU, balancer, accelerometer,
  clamp, diodes, LEDs (reverse-mount), passives, the solder-bridge selectors, and the flat
  programming / breakout pads.

## 4. Front face — keep clear

| Feature | Center (x, y) | Size |
|---------|---------------|------|
| PV1 solar cell | (25.4, 17.0) | ≈42 × 23 mm (SM141K06TF) |
| PV2 solar cell | (25.4, 71.9) | ≈42 × 23 mm |
| Glow window (DRH monogram) | (25.4, ~43.9) | x 14.95–35.85, y 40.8–47.0 (≈20.9 × 6.2 mm) bare-FR4 light window |

The two cells take the two ends; the glow window is dead center, backlit from the rear. Nothing on
the front is covered by the shell.

## 5. Back-side height stack (what the cavity must clear)

Two parts set the cavity; everything else clears under it.

| Part | What | Height | Center (x, y) |
|------|------|--------|---------------|
| **U2** | balancer, SOIC-8 | **~1.75 mm (tallest)** | (28.5, 37.0) |
| **SC1–SC4** | WS17 supercaps | **1.7 mm** | see §6 |
| D1, D9 | blocking Schottky | ~1.1 mm | (44.0, 43.9), (43.5, 53.5) |
| U4 | TLV431, SOT-23 | ~1.1 mm | (43.0, 49.0) |
| U3 | accelerometer, LGA-12 | ~1.0 mm | (20.0, 35.9) |
| U1 | MCU, VQFN-28 (4×4) | ~0.9 mm | (9.5, 40.9) |
| D2–D5 | LEDs, LA P47F (reverse-mount) | ~0.83 mm | row at y 43.9 |
| R / C | 1206 / 0805 | 0.6–0.7 mm | central band, y 32–55 |

→ A **uniform ~1.8 mm cavity** clears U2 and the cells with margin. **No local U2 pocket** is
needed (U2 at 1.75 mm ≈ the cells at 1.7 mm) — this deletes the thin-skin pocket the old CAD
carried. **No through-hole headers exist** (every connector is flat SMD), so nothing else stands
proud; the stack really is U2/cell-limited.

## 6. Big-part placement (what the shell works around)

**Supercaps — the area hogs** (4 × 28.5 × 17 mm ≈ 43% of the board), long axis along the 88.9 mm
length:

- **Top pair:** SC1 (15.5, 16.9), SC2 (35.3, 16.9) — occupy roughly x 7–44, y 2.6–31.2.
- **Bottom pair:** SC3 (15.5, 72.0), SC4 (35.3, 72.0) — occupy roughly x 7–44, y 57.8–86.3.

**Central electronics band (y ≈ 31–58):** MCU (U1, left), balancer (U2, center), accelerometer
(U3), clamp (Q1/U4/R7-9, right), the LED row + monogram (center), the SW2/SB/SJ selectors, the
passive field, and the breakout pads. This band is where all the routing and the optical heart live.

**Corners** (x 3.5 / 47.3, y 3.0 / 85.9): the four M2 holes, clear of the cells.

## 7. Optically-active zone — no pillars here

The LED row (D2–D5 at y 43.9) plus the glow window (x 15–36, y 40.8–47) is the optical heart.
Reverse-mount LEDs sit on the back and emit *through* the board to the front monogram, so an opaque
back shell behind them does not block the glow. But: **do not land support pillars on the LED pads
or the monogram traces**, and clear the ~0.83 mm LED bodies. Treat **x 15–36 / y 40–47 as a
no-pillar keepout**.

## 8. What changed from the shell in `enclosure/` (redesign, don't patch)

- **Four supercaps, not two.** The old CAD models one top pair plus a U2 pocket. v2.1 has four cells
  (both ends, §6). The pocket field, the SC pockets, and the pillar map must be re-laid-out for the
  four-cell footprint.
- **No edge castellations.** Verified: zero pads within 1.5 mm of the rim. The old CAD's biggest
  electrical hazard — press-fit walls shorting the right-edge VS/SDA/SCL castellations — **is gone.**
  Walls can press over the bare-FR4 edge with no edge-pad short.
- **No U2 pocket.** U2 (1.75 mm) ≈ cells (1.7 mm) → uniform ~1.8 mm cavity, no local thin skin.
- **VQFN-28, not QFN-20** (height-irrelevant at 0.9 mm; noted for accuracy).
- **No button.** The actuator is the accelerometer tap, which the metal back-plate *transmits*. No
  dome, no button hole, no cap-touch window.

## 9. Grounding & isolation (still applies)

The four M2 screws ground the body, so it is a defined-potential shield — good — but **any non-GND
copper the metal touches is a short.** Edge castellations are gone (§8), so the wall hazard is moot.
The remaining hazard is **support pillars pressing on the back**: soldermask (~20 µm) is a weak
insulator under load, and any exposed copper (untented vias, the VS pour) shorts to the GND body.
**Land pillars only on GND pour**, or spec a **die-cut Kapton (~0.05 mm)** blanket between the
board back and the shell — the simplest fix, negligible on the thickness budget.

## 10. Programming access

The **TC2030** Tag-Connect pads (TC1) are on the **back** at (13.3, 16.9), tucked beside SC1, with
NPTH alignment/leg holes; pogo flashing is from the back. Decide up front: **flash before closing
the shell** (the pads sit in the program-before-mount dead space between the cells), or **cut a
TC2030 window** in the back shell for field re-flash. The backup UPDI header J1 (4.7, 38.4) is also
back-side flat pads.

## 11. Variants and open axes (the "enclosure(s)")

- **Material:** Ti-6Al-4V (holds 0.3 mm skins, yield ~880 MPa) vs 7075-T6 (cheaper/faster, bump the
  skins). Machining (photochemical-etch the shallow reliefs, CNC the walls/bosses) and the full CAD
  knob set are in `ENCLOSURE-NOTES.md`.
- **Skin thickness:** the repo previously carried a standard and a 0.2 mm-skin variant.
- **Open vs enclosed:** with no castellations, the old "enclosed variant drops the edge bus"
  complication disappears — the enclosed build is simpler than it was.

## Cross-references

- **Shell design rules, material, machining, CAD knobs:** `ENCLOSURE-NOTES.md`.
- **Why four cells / the rear real-estate logic / energy model:** `solar-glow-drh-design-notes.md` §4.
- **Exact pad and keepout geometry:** open `solar-glow-drh-v2_1.kicad_pcb` in KiCad.
