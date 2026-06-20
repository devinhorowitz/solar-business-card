# SOLAR-GLOW · DRH — V1 redesign plan

Status: **kicked off, blocked on baseline source (see §4).** V0/REV J is prototyping;
V1 is the real re-spin, led by the supercapacitor change.

---

## 1. Priority change — supercap upgrade + land rework

**Part swap.** 3-153-434 (WS10, 300 mF, 1.0 mm) → **3-153-438 (WS17, 1000 mF / 1 F, 1.7 mm)**.
Both are 2.75 V single cells; two in series → **500 mF @ 5.5 V** vs 150 mF today — **3.3×**
the storage, and ESR drops to 40 mΩ (from 50). WS10/WS13/WS17 **share one footprint**, so
board *area* is unchanged — only thickness and capacitance move.

**The land is wrong and must be redrawn (the whole reason for V1).** Confirmed against the
datasheet *and* the parts in hand:

- **Real terminals:** two **1.5 × 3.5 mm** pads on the *underside*, diagonal — negative at one
  short-end, positive at the opposite — sitting **within** the 28.5 × 17 mm body.
- **Current footprint** `FP("SCPC")`: 3.5 × 3.5 pads at `(±18.25, ±8)` → a **36.5 × 16 mm span**,
  ~4 mm beyond each body end. Those land on the **folded-edge locator tabs**, not the terminals.
- **Fix:** redraw to the bottom-face terminals. Pull SCHURTER's official WS17 land (or SnapEDA /
  Ultra Librarian), or measure the in-hand part — do **not** ship guessed sub-mm centers to fab.
  Datasheet locating dims (WS17 bottom view): pad 1.5 × 3.5; references 12.25 / 14.1 / 7.75.
  The corner tabs are mechanical locators → keep-clear, no copper.

**V0 / REV J bodge (to prove the stack electrically on the protos in hand):** tack a short
copper lead from each bottom terminal to its net; easiest if you tin/wire the terminal *before*
setting the cap down, since it's captured under the body.

**Enclosure consequence (good):** 1.7 mm ≈ U2 (1.75 mm). Bump `cavity` 1.6 → ~1.8 mm and the
caps *and* U2 clear with no pockets — deletes the marginal 0.3 mm U2 skin. ~+0.2 mm behind the
board for a simpler, stronger floor (also helps 7075). See `enclosure/ENCLOSURE-NOTES.md`.

---

## 2. MCU — parked, gated

No MCU change goes into copper until the **AVR-DD power-down number** lands (pull `AVR64DD28`,
read Power-Down typ @ 3 V/25 °C and with RTC/PIT). If it clears the 1616's ~0.1 µA → **AVR-DD,
SSOP-28** (height is free behind the 1.7–1.75 mm supercap/U2 floor; MVIO solves the §3
mixed-voltage I²C). Else ATtiny1627 (ADC) or ATtiny3217 (superset). Full analysis: punch-list §7.

---

## 3. Deferred-routing items

Fold into the V1 re-route as the channel rework allows: §1 light-sense (VIN÷2 → ADC),
§2 spare-GPIO breakout, §3 accelerometer (gated on the §6 energy result). Details in the punch list.

---

## 4. ⚠ Baseline source gap — decision required before any V1 copper

The board generator source is **not in the repo** (only enclosure CAD + gerber zips), and the
only board source that exists anywhere reachable (`handoff.zip` → `solar-glow-drh-source.zip`)
is **REV I**, one full architecture revision behind the ordered REV J:

| | REV I (the source we have) | REV J (ordered; gerbers only) |
|---|---|---|
| Nets | 8 | 16 |
| LED drive | all four cathodes on one `LRET`→ballast→`RET` low-side path | four **independent** MCU-PWM channels |
| MCU wiring | GND / VS / UPDI / RETD only | full pin map (PC0 / PB0 / PB1 / PB2 drives, etc.) |
| LED positions | x = 13.7 / 21.7 / 29.1 / 37.1 | x = 18.2 / 23 / 27.8 / 32.6 |

Generating V1 from the REV I source would **regress the board to single-channel**. The REV J
generator source appears lost — only `solar-glow-drh-gerbers-revJ.zip` survives.

**Pick one to unblock V1:**

1. **Provide the REV J generator source** (the `pcb_route.py` / `gerber_export.py` REV J was
   actually routed from), if it still exists anywhere. → cleanest, fastest correct path.
2. **Rebuild V1 in KiCad** with real footprints + DRC — the established plan for final routing on
   a board this dense. Reconstruct placement/netlist from the REV J gerbers; the corrected SCPC
   land and the real AVR-DD footprint drop straight in. More setup, right long-term tool.
3. *Reconstruct REV J onto the REV I generator* — **not recommended**: error-prone, regresses
   unless fully rebuilt, and the wrong tool for final V1.

---

## 5. Enclosure — on ice

Parked pending V1 board bring-up. CAD + STEP/STL are preserved in `enclosure/`; the design notes
(material, isolation, cap-touch, machining, height stack) are in `enclosure/ENCLOSURE-NOTES.md`,
now marked PARKED. The supercap change *simplifies* it (uniform ~1.8 mm cavity, no U2 pocket).

---

## 6. Looking further out — V2 (quad-cell, thin 4-layer)

Concept: **4× WS17** on a **0.4 mm 4-layer** board (thinner than today's 0.8 mm 2-layer), cells
paired at opposite ends of the back with the SMD parts clustered in the center; front stays naked;
a full trace redesign.

**Energy (correcting the "4 F"):** that 4 F holds only all-parallel at 2.75 V. The 5.5 V rail needs
two-in-series, so four cells wire 2S2P/2P2S → **1 F effective at 5.5 V**. What's fixed is energy:
4 × ½·1F·2.75² ≈ **15 J = 2× the two-cell V1** (~7.6 J), ~6–7× the original WS10 board. Farads at
2.75 V vs 5.5 V aren't comparable joules; the honest spec is **2× the V1 reserve**.

Notes:
- **Still thin.** The 1.7 mm cells set the back-side height either way; a 0.4 mm board *trims* the
  envelope vs 0.8 mm. Stays in the thin-showpiece lane — and a 0.4 mm board leans on the metal
  back-shell + its pillar field for rigidity (good synergy with the parked enclosure; cf. the
  existing 0.2 mm enclosure variant).
- **4-layer is the right call** — dedicated VS/GND planes clean up supercap power distribution and
  the reroute, and earn their cost on a denser build.
- **Fab:** 0.4 mm 4-layer is a thin stackup → a PCBWay/JLC custom job (OSH Park's 4-layer is a fixed
  thicker stackup). Aligns with the PCBWay route already planned for the locked design.
- **Layout:** 4× (28.5 × 17) cells + a center SMD cluster on 50.8 × 88.9 is tight but workable
  (two cells per end, ~28 mm center band) — confirm with a placement pass. "Opposite sides" =
  opposite *ends* of the back keeps the front clean; opposite *faces* would put cells on the
  glow/solar front (conflict).
- **Balancing:** 2P2S → one midpoint balancer; 2S2P → two, or tie the midpoints.
- **Diminishing returns:** a 2× bucket buffers dark ~2× longer but cold-starts ~2× slower on indoor
  light and doesn't change the harvest-vs-draw ratio (§6) — buffers a deficit, doesn't cure it.

Verdict: a thin, denser, ~2× energy evolution of the V1 board — files as **V2**, after the V1 land
fix and the MCU decision (full reroute + 4-layer + 4 cells, not a drop-in).

---

## References

- Supercap: 3-153-438 row in `datasheets/typ_SCPC-2.pdf` (WS17 dimension page = PDF p.4).
- MCU gate: `AVR64DD28` datasheet — **to pull**.
- `solar-glow-drh-v1-punchlist.md` §7 (MCU), §1–§6 (deferred items, energy budget).
- `enclosure/ENCLOSURE-NOTES.md` (parked).
