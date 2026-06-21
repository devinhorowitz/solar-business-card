# SOLAR-GLOW DRH v1 — Routing Plan

Board: `solar-glow-drh-v1.kicad_pcb` — 42 footprints, **0 segments / 0 vias (unrouted)**. 4-layer, 0.4 mm, PCBWay. This plan is grounded in the actual placement (every coordinate below is read from the board), so the KiCad pass is mechanical: set rules, stitch the planes, then route signals in the order given.

## Layer stack & power strategy
- **F.Cu** (signal) / **In1.Cu = GND plane** / **In2.Cu = VS plane** / **B.Cu** (signal).
- Almost everything is on **B.Cu** (back). Front (F.Cu) only: PV1, BT1/BT2, SW1, MH1-4.
- GND and VS are **planes, not traces**: every GND pad drops a via to In1, every VS pad drops a via to In2. Signal nets route as copper on B.Cu, with F.Cu as the relief layer for the few long crossings.

## Glow keepout — hard rule
Rectangle **x 14.95–35.85, y 40.8–47.0** (the DRH window). Inside it: **tracks allowed, but NO vias, NO copper pour, NO footprints.**
- Any VS/GND pad inside the window can't via straight down — trace it out first.
- Avoid running signal traces across the window (they shadow the glow). Route around it (y < 40.8 or y > 47).

## Design rules to set first (confirm against PCBWay 4-layer 0.4 mm)
- **Net classes:** POWER = {VS, GND, MID, VIN, VBAT, BMID, VBATD}, wider where it fits (planes carry the current; 0.4 mm traces are plenty). SIGNAL = everything else, fine (0.2 mm typical).
- **Clearance** 0.15 mm (PCBWay 4-layer min is often 0.1–0.127 mm — confirm and you can tighten).
- **Vias** 0.45 / 0.25 mm (pad/drill) for plane stitching — confirm PCBWay min.

## Phase 1 — plane stitching (deterministic bulk; none inside the glow window)
Drop a via next to each pad to tie it to its plane.

**VS → In2 (straight via, 15):** TC1.2, SC1.P, SC3.P, U1.18, U1.24, U2.2, U2.3, U2.8, D1.K, D7.K, C1.1, C2.1, C4.1, J1.2, SJ1.1.

**VS → In2 (LED anodes, trace out of the void first, 4):** D2.A, D3.A, D4.A, D5.A are at y≈44.3 inside the window. Run a short trace north (to y < 40.8) or south (to y > 47), then via. D2.A sits at x 14.8 (just outside) and can via immediately to its left.

**GND → In1 (via, ~25):** every GND pad. Put one or two vias on the U1.EP and let U1.19/U1.25 share it. MH1-4 (front) via to the GND plane. Don't miss C1.2 / C2.2 / C3.2 / C4.2, R6.2, C5.2, JP1.3, JP2.4, SW1.2, BT1.NEG, PV1.N/Nt.

## Phase 2+ — signal nets (by difficulty)

### Easy / local — do first
- **K2–K5** (LED cathode → ballast): short trace south, D2-5.K (y43.5) → R1-4.1 (y49.6), same column. Exits the void going south — fine.
- **LDRV stubs:** R1-4.2 ↔ SB1-4.1 are adjacent (y49.6 ↔ y52). Tiny jumps.
- **VSENSE:** R5.2 / R6.1 / C5.1 / U1.3 all cluster left of U1 (x 4–8, y 40–50). Short.
- **VDDIO2:** SJ1.2 → U1.10 + C3.1. Local.
- **SDA / SCL:** U1.8/9 → JP1.1/2. Adjacent.
- **PA4 / PC0 / PC1:** U1.2/6/7 → JP2.1/2/3, down-left to JP2. Short.

### Medium
- **LDRV1–4 → U1:** four drive nets from the ballast row (R.2 at x 16–35, y 49.6) left to U1's bottom edge (pins 26/27/28/1 at x 7.5–9.1, y 38.9–39.7). Keep them ordered (LDRV1 nearest U1, LDRV4 farthest) to avoid crossings. Part of the U1 escape — see hotspots.
- **UPDI:** U1.23 (10.3, 38.9) → J1.1 (4.7, 35.9, easy) and **down to TC1.1 (10.9, 15.6)**. The TC1 leg runs ~23 mm south on B.Cu at x ≈ 11, threading past SC1 (body x 9.4–21.6, pads at x 15.5) — stays left of SC1's pads. Route it before the MID bus so it owns that lane.

### Hard / long — do last, may want F.Cu
- **MID bus (7):** taps SC1.N (15.5, 27.9), SC2.P (35.3, 27.9), SC3.N (15.5, 61), SC4.P (35.3, 61) + U2.4/6/7 (x 45.6, y 39–42). Bring the right taps (SC2.P, SC4.P) up the right edge into U2; carry the left taps across to MID **around the glow window** (y < 40.8 or y > 47, never through it). Use F.Cu for the left-to-right crossing to keep B.Cu clear. Second-densest after the U1 escape.
- **VIN (4):** input PV1.P/Pt (43–46, 15.9, F.Cu) + D1.A (45.9, 43.9, B.Cu — needs an F→B via) → divider R5.1 (3.7, 50.4, far left). One trace carries raw VIN across to the left divider; run it on F.Cu or the lower B.Cu lane, around the void.
- **BTN (2):** U1.5 (7.5, 41.3, B.Cu) → SW1.1 (40.4, 77.9, F.Cu, far bottom-right). Longest net + a layer change. Via U1.5 to F.Cu and run it down/right to SW1 across the near-empty front below the supercaps, or run B.Cu down the right edge then via. SW1.2 is GND (plane via).

### Battery option — only if populating coins
- **VBAT / BMID / VBATD:** BT1/BT2 (front) + D6/D7 (back) in the top zone. Route F.Cu between the retainers, via to D6/D7. Self-contained — skip on the solar build.

## Hotspots (slow down here)
1. **U1 QFN28 escape (bottom/left edge)** — LDRV1-4, UPDI, SDA, SCL, BTN, VSENSE, VDDIO2, PA4/PC0/PC1 all leave the same two edges. Tightest spot on the board. Fan out in pin order; short F.Cu jogs if B.Cu jams. Get the VDD (18/24) and GND (19/25/EP) plane vias in first so decoupling is solid.
2. **MID bus around the void** — do not shortcut through the DRH window.
3. **TC1 under SC1** — both on B.Cu; thread UPDI/VS/GND to TC1's pads between SC1's P/N pads (x 15.5). Clear per the audit, but tight.
4. **BTN to SW1** — long; plan the layer change early.

## Recommended order
1. Set rules + net classes.
2. Phase 1: plane vias (GND/VS) + LED-anode trace-outs.
3. Easy/local signals (K, LDRV stubs, VSENSE, VDDIO2, SDA/SCL, PA4/PC0/PC1).
4. LDRV1-4 escape to U1.
5. UPDI (including the TC1 run).
6. MID bus.
7. VIN.
8. BTN.
9. Battery nets (if used).
10. Refill GND + VS pours; run DRC; fix; repeat.

## After routing
- Re-pour both planes (In1 GND, In2 VS); confirm the glow keepout still voids them.
- DRC must be clean: clearance, unconnected, and via-in-keepout (the keepout flags any via that strays into the window).
- If any part moves, re-run `connectivity.py` to refresh the worklist.
