# SOLAR-GLOW · DRH — SESSION HANDOFF (2026-06-22)

Snapshot for a **new Claude session** picking up this board. Read this first, then
`V1-SPEC.md`, `V1-PLAN.md`, `solar-glow-drh-v1-punchlist.md`, `ENCLOSURE-NOTES.md`.

> **This is a personal hardware hobby project, NOT legal work.** Do not apply any legal /
> citation / billing skills. Casual engineer-to-engineer tone, concise, lead with the answer,
> user is on mobile and reacts to rendered images each turn. **Hard anti-fabrication rule:**
> never invent specs / pins / geometry / MPNs — verify against the datasheet or source.
> No em-dashes in chat prose (they're fine in `.md`/`.py` files like this one).

---

## ⭐⭐ NEWEST STATE (2026-06-22, session 2) — accelerometer + VS-rail clamp integrated

Two substantial additions on top of the 6-layer routing checkpoint described below. **Routing is now
25/25 nets single-island, zero shorts** (was 21/21). `gen_v2.py` models both; Devin replicates
**placement + netlist** in KiCad by hand (the exact prototype trace shapes don't transfer — he
re-routes from the schematic).

### Accelerometer placed + wired — U3 = ST LIS2DH12 (12-LGA, 2.0 × 2.0 × 1.0 mm)
- **Placed at (20, 35.9), back side, rotated 180°** — exactly the spot M1 had reserved. The serial
  column (SDA / SCL / CS / SDO) faces **west** toward JP1 (clean I2C escape); the INT pins face the QFN.
- **Datasheet confirmed** (`datasheets/en.DM00091513.pdf`): **Vdd AND Vdd_IO max 3.6 V** — this is the
  constraint that drives the clamp below. LGA-12, 0.5 mm pitch, 4×4 grid, center 2×2 empty. Pinout
  (Table 2): 1=SCL, 2=CS, 3=SDO/SA0, 4=SDA, 5=Res, 6/7/8=GND, 9=Vdd, 10=Vdd_IO, 11=INT2, 12=INT1.
- **Wiring:** CS tied **HIGH (VS)** → I2C. SA0/SDO tied **GND** → address **0x18** (flip to VS for 0x19).
  I2C on the existing SDA/SCL bus. Vdd + Vdd_IO → VS, pins 5–8 → GND (ties cross the hollow LGA center).
- **INT routing — the unlock:** two interrupts needed two MCU pins. Committed **PF1 (pin 21) → INT1**
  and **PF0 (pin 20) → INT2** (renamed at the QFN NE corner, which faces the accel). **Tradeoff: gives
  up the 32.768 kHz RTC crystal** — fine with wake-on-motion. Each INT routes B-stub → In3 → B-stub
  through the freed JP1 slot (fine vias 19.4/37.6, 13.3/39.6, 20.7/37.6, 13.5/40.2).
- **C6 = 100 nF** decoupling (VS-GND, 0402) just east of U3 at (22.2 / 23.2, 36.4).
- **JP1 (I2C breakout) relocated ~5 mm NORTH** → SDA(13.7, 32.42) / SCL(13.7, 34.96) / GND(13.7, 37.50).
  Its old 3 big SMD pads sat on the only INT-escape slot; moving it opened the corridor. The SDA In3
  wall (x12.0) and SCL In2 wall (x12.3) just extend up to reach the new position.
- **Recommend 2× ~4.7 k I2C pull-ups** (SDA→VS, SCL→VS) — not yet placed.

### VS-rail shunt clamp — voltage coordination RESOLVED (was open item #3)
The accel's 3.6 V ceiling vs the cell's ~3.85 V open-circuit (VOC 4.15 − D1) needed resolving.
**Decision: a boosted shunt clamp on VIN (solar side, BEFORE D1), holding VS ≈ 3.42 V.** Placed SE of
D1 (~7 × 4 mm cluster), back side.

```
Q1  PNP (MMBT3906 / SOT-23, or BCP53 / SOT-89 for thermal margin)   E→VIN   B→CLBASE   C→GND
U4  TLV431A (SOT-23, 1.24 V adjustable shunt ref)                   K→CLBASE  ref→CLREF  A→GND
R9  1 k    (0402)   VIN ↔ CLBASE   (base pull-up + TLV431 cathode current path)
R7  20 k   (0402)   VIN ↔ CLREF    (divider top)
R8  10 k   (0402)   CLREF ↔ GND    (divider bottom)
C7  100 nF (0402)   VIN ↔ GND      (local decoupling / stability)
new internal nets: CLBASE, CLREF
```
- **Setpoint:** V(VIN) = 1.24 × (1 + 20/10) = **3.72 V** → VS = 3.72 − 0.3 (D1) ≈ **3.42 V**
  (worst-case ~3.48 V with ±1% tol, still under the 3.6 V accel max).
- **Why VIN-side, not VS:** a divider on VS leaks ~120 µA continuously → drains the WS17 stack flat
  in ~11 min in the dark. On VIN, D1 reverse-blocks the caps, so in the dark VIN = 0 and the clamp
  draws **nothing** from storage; it only burns power while the cell produces (exactly when
  overcharge would occur). Doesn't interfere with MPP charging (Vmpp 3.35 V; clamp engages only
  above 3.72 V when the caps are full).
- **Dissipation:** worst case (bright sun, caps full, MCU idle) ~167 mW in Q1 (~45 mA × 3.72 V) →
  ~42 °C rise in SOT-23, ~17 °C in SOT-89. Rare / transient.
- **Firmware mitigation:** VSENSE already reads VIN; when it nears the setpoint, **turn the LEDs on**
  to dump the excess as glow instead of heat → the hardware clamp becomes a backstop. SOT-23 Q1 is
  fine with that mitigation; SOT-89 for long bright-idle stretches.

### KiCad to-mirror for these two (in addition to the older list below)
- Add **U3** (LIS2DH12, LGA-12) at (20, 35.9) **rot 180°**, wired per above. **Rename MCU nets**
  PF1 (pin 21) → INT1, PF0 (pin 20) → INT2. Add **C6** (100 nF VS-GND ~22, 36.4). **Move JP1** north.
  Add the 2 I2C pull-ups. **Delete the M1 keepout** — U3 now occupies that spot.
- Add the **clamp** sub-circuit (Q1 / U4 / R7 / R8 / R9 / C7), new nets **CLBASE / CLREF**.

---

## ⭐ LATEST STATE (2026-06-22) — 6-layer, routed, front-trace-hidden

The board **moved from 4-layer to 6-layer** to get two inner *signal* layers for routing. The
routing now lives in a generator, **`gen_v2.py`** (working dir + `/mnt/user-data/outputs/`), which
parses Devin's KiCad `.kicad_pcb` for footprint geometry, defines its own 6-layer stackup, lays
all the copper, runs self-checks (connectivity + shorts), and emits gerbers + a 4-panel preview.
**Devin replicates the final routing in KiCad by hand** (the generator is the prototyping / proving
tool; hand-coded polygon routing is not the sign-off tool on a board this dense).

**6-layer stackup (0.8 mm, PCBWay):** `F(sig) / In1(GND plane) / In2(sig) / In3(sig) / In4(VS plane) / B(sig)`.
Four signal layers (F, In2, In3, B); In1=GND plane, In4=VS plane. The glow window is voided on all
four inner layers (no vias / pour / footprints / inner traces in the GLOW box x14.95–35.85,
y40.8–47.0) for light diffusion. **All vias modeled as through** (a via blocks X/Y on every layer).

**Routing status: 21/21 nets single-island, zero shorts** (`<0.15 mm` checker is authoritative).
*(Superseded: now **25/25** with the accelerometer + clamp — see NEWEST STATE at the top.)*

**Synced to Devin's live repo this session** (the generator had been parsing a stale clone). The
live design added, and the generator now models:
- **SB1–SB4** = per-LED **disable jumpers** (`bridge_2pad`, back side, y52). Each bridges a driver
  line to GND: `SBn.1 = LDRVn`, `SBn.2 = GND`. Solder a bridge to ground that driver and kill its
  LED. Each LDRVn now routes to its ballast **and** its SBn.1 pad (short B stub from the ballast).
- **M1** = `M1:ACCEL_reserved`, back side at (20, 35.9), 4 NC corner pads forming a **2×2 mm keepout**
  (the accelerometer's reserved spot — keep clear). See the accelerometer note below.
- The origin `.kicad_pcb` **still has the battery** (BT1/BT2/D6/D7); the generator filters them out
  so gerbers are battery-free regardless. **Devin still must delete BT1/BT2/D6/D7 in KiCad.**

**Front-trace-hiding pass (the display face is the priority surface):** every interconnect that was
on F moved to inner copper. Front trace length **~230 mm → 13.9 mm**, of which 12.3 mm is VIN's PV1
ties *under the panel*; the only exposed front copper is a **1.6 mm stub into the dome pad**.
- LDRV1 → In2, PA4 → In2, SDA → In3, SCL → In2, UPDI → In3 (both legs), VIN → drops to In3 at the
  panel boundary, **BTN → In2** (down the west margin threading the divider/JP2 via gaps at x6.05,
  across y71 between the SC3/SC4 pad rows, surfacing east of the dome GND via).
- BTN surfaces at the dome as a **via-near-pad** (1.6 mm F stub), not via-in-pad — a snap dome needs
  a flat contact.
- **Solar panel hidden zone = x[4.4, 46.4], y[4.4, 27.4]** (top third, ~full width). Anything on F /
  any via inside it is hidden once PV1 mounts. The panel covers only the top third, so center/lower
  vias (QFN escapes, headers, ballasts, dome) cannot be hidden — Devin accepts this.
- **Vias: 67 show on top, but every one sits at a component** (QFN escapes, the
  header/ballast/divider/SB band, D1/U2/J1/dome/supercaps). None float in open copper.
  Lower would need blind/buried vias (cost jump).
- **MID balance bus moved to In2** (back-side cleanup, Devin's call). Back trace length dropped
  **206 → 97 mm** (only the U2.6-U2.7 bridge stays on B). Cost 6 surfacing vias: SC1.N/SC2.P land
  at y26 **under the panel (hidden)**, U2.4/U2.6 are fine via-in-pad, SC3.N/SC4.P land at y61
  (their pads are **horizontal**, y59.25-62.75, unlike the vertical top-cap pads). Net +4 exposed
  front vias, all at components. Low-current series-midpoint tap, so inner is electrically fine.

**C1/C3 placement nudges (in the generator's `NUDGE` dict; Devin replicates in KiCad):**
- **C1 reverted to its KiCad position (9.5, 45.5)** — no nudge needed once LDRV1 left the front, and
  it's closer to the QFN VS pins (better decoupling). **No KiCad move required.**
- **C3 stays nudged to (12.5, 48.5)** beside SJ1 (load-bearing: VDDIO2 decouples pin10→SJ1→C3).
  **Devin applies this one move in KiCad.**

**Two routing-under-supercap consequences to sanity-check** (both hidden, both physical): UPDI drops
a via at TC1.1 and BTN surfaces at (42, 78), and **both sit under a supercap body** (SC1, SC4). WS17
cells are raised on their end pads so a tented via in the body-center should clear, but confirm no
flat underside feature fouls a via bump. (Same neighborhood as the **TC1-under-SC1 placement overlap**
still open in KiCad — TC1 the Tag-Connect is physically under SC1; Devin's placement to resolve.)

**Generator outputs:** `solar-glow-drh-v2-gerbers.zip`, `solar-glow-drh-v2-gerber-preview.png`
(4 signal-layer panels), `gen_v2.py` — all in `/mnt/user-data/outputs/`. `gen_v1.py` (the prior
4-layer generator) is preserved alongside.

---

## Where the board is

> **Note (2026-06-22):** the section below describes the earlier **4-layer KiCad source** and the
> design decisions that produced it. It is still accurate as *history and component rationale*, but
> the live routing target is now **6-layer** per the LATEST section above. Footprint count is up to
> 37+ (SB1–4 and M1 added, battery to be removed).

`solar-glow-drh-v1.kicad_pcb` — 4-layer, 0.4 mm, PCBWay. **39 footprints. Pad-clean and
courtyard-clean** (verified at the pad level, not just courtyards). Portrait 50.8 × 88.9 mm,
0.8 mm FR4, ENIG. Stackup: L1 F.Cu signal/parts, L2 In1.Cu GND plane, L3 In2.Cu VS plane,
L4 B.Cu signal/parts. MCU = AVR64DD28 VQFN28. 4× WS17 supercaps (2P2S → 1 F @ 5.5 V ≈ 15 J),
U2 (ALD910025 SOIC-8, **dual** SAB — NOT the ALD810025, which is the quad/16-pin) balances the
shared MID. Glow = 4 rear LEDs (LA P47F) backlighting a
DRH monogram cutout at y45 through bare FR4; plane keepout voids pour+vias there.

### Changes made this session
- **Supercaps moved toward the top/bottom edges**, leaving a **~2.65 mm lip margin** for the
  enclosure's press-fit wall. This widened the central SMD band from **17.6 → 26.6 mm**.
  TC1 (Tag-Connect, buried under SC1) rode up with SC1.
- **SW2 is now a 3-pad solder-bridge jumper**, placed inboard off the bottom edge (so the
  bottom cells could drop). **Nets still TBD** pending the TINY/part decision.
- **U1 hub cluster re-spaced.** A pad-level audit found real shorts the courtyard check missed:
  J1's GND pad hung **0.54 mm off the board**, JP1's GND overlapped U1's UPDI/VS pins, and the
  0805 decoupling caps touched U1's LED-drive pins. Root cause: the PROG headers are 7 mm wide
  at rot 90. **Fix:** headers rotated vertical (1.5 mm wide) and pulled off the left edge, caps
  re-spaced off U1's pad field, C4 moved above U2. All clean now.
- **Accelerometer reserved** (`M1 ACCEL?`, back side, center-band strip above the LEDs at
  ~(20,53)). Placeholder, NC pads. It rides the existing I2C bus (SDA/SCL) + VS/GND, costs zero
  extra GPIOs, and its position is functionally irrelevant.
- **Light sensing — decided to use the solar cell itself.** `VSENSE` = VIN (solar node, before
  the blocking diode D1) divided by R5/R6, filtered by C5, into PA5/AIN25. R5/R6/C5 already
  exist, so light sensing is free. **A separate photodiode + drilled aperture was considered
  and DROPPED** — solar-as-sensor covers coarse light/dark/charging behavior, and the dedicated
  sensor only wins for precise lux, fast gesture/shadow detection, or a reading decoupled from
  the harvest (none needed). Dropping it also killed a reverse-mount-photodiode sourcing risk.

---

## Open items / next steps
1. **KiCad replication + DRC is the endgame.** The generator proves the routing clean (25/25,
   no shorts); Devin reproduces it in KiCad with real DRC for sign-off. To apply in KiCad:
   move the board to **6-layer**, apply the **C3 nudge** (12.5, 48.5), **delete the battery**
   (BT1/BT2/D6/D7), and replicate the inner routing + SB-jumper connections + via placements.
2. **Resolve TC1-under-SC1** (Tag-Connect physically under SC1) and confirm the two
   under-supercap vias (TC1.1, BTN @42,78) clear the cell undersides.
3. **Voltage coordination — RESOLVED (2026-06-22):** chose the **VIN-side boosted shunt clamp**
   (Q1/U4/R7/R8/R9/C7, VS held ≈3.42 V). See NEWEST STATE. (Rejected alternatives: 5.5 V-only caps
   don't cap the rail; a lower-VOC cell would cut harvest. The clamp-on-VIN avoids dark drain.)
   Remaining: mirror it in KiCad, and pick Q1 package (SOT-23 + firmware-glow mitigation, or SOT-89).
4. **Confirm a real ~565 nm reverse-mount LED exists** (flagged sourcing risk).
5. **Accelerometer — DONE (2026-06-22):** **ST LIS2DH12** placed at (20, 35.9) rot 180°, wired on the
   I2C bus with INT1→PF1 / INT2→PF0 and C6 decoupling; JP1 moved north to open the INT corridor.
   See NEWEST STATE. Remaining: mirror in KiCad and **delete the now-superseded M1 keepout**.
6. **PV1 solar tabs** sit ~2.3 mm from the side edges (front); confirm enclosure front-wrap width.
7. **Front art → real F.Cu zones** (shaped GND pour + DRH letterforms + QR + frame). The front is
   now trace-clear, which is the clean canvas this needs.
8. **Haptic / actuator decision** — see the Haptic section (not committed).

---

## Haptic actuator exploration  (`motors___ac__dc.csv`, in repo)

User is weighing **haptic feedback**, motivated by a possible capacitive-touch interface (which
has no mechanical click). DigiKey lists haptic actuators under "Motors – AC, DC," so that CSV =
the actuator candidates. **276 parts: 203 ERM, 65 LRA, 8 Piezo.** Note the CSV's `Size/Dimension`
column is **diameter only — no thickness**; thickness is in the description or datasheet.

**Key findings from the data:**
- **LRAs** (the resonant actuators): cheap ($1.87–$8), low voltage (1–2.5 VAC), 65–235 Hz,
  5–13 mm diameter. **Thinnest is ~2.5–2.6 mm** — e.g. `HD-LA0503-LW28` (description literally
  "5X2.6MM LRA"). The 8 mm coins (`VG0832*` family, $3–4, 235 Hz, high stock) read ~3.2 mm.
  `JYLRA0825Z` is a cheap ($1.87) Z-axis coin. **Every LRA exceeds the 1.8 mm cavity.**
- **Piezos**: thin actuators but **all need high voltage (0–60 / 0–120 V)** and are pricey
  ($18–$200, TDK PowerHap / PUI PHUA families).
- ERMs are the bulk (cheap, available) but spin-up/down is mushy vs an LRA for a crisp button feel.

**Engineering verdict (for the new session):**
- **The height obstacle is real-world solvable, but thin LRAs trade height for footprint.** A
  lateral-motion LRA is thin because its mass moves *sideways*, so it is physically wide.
  **Candidate on file (user-supplied): NIDEC TapSense** (PDF in `datasheets/`), "world's thinnest
  LRA" — **1.4 mm thick, which fits the 1.8 mm cavity**, 200 Hz, 3.0 Vrms rated / 360 mA peak
  (7 Vrms over-drive needs a boost the 5.5 V rail cannot supply), crisp 6.4 Gp-p over 12 ms.
  **But its footprint is 25 × 25 mm — half the card width — and does NOT fit the current layout:**
  the glow, LED row, and supercaps leave no 25 mm-clear zone without a real rework. **User flags
  sourcing as a likely problem** (specialty tablet/notebook part). The fallback is a small coin
  LRA (>=2.5 mm, e.g. HD-LA0503 at 5 x 2.6 mm), thin-enough only with a local enclosure pocket
  plus air clearance to vibrate (~2.3 mm local bump).
- **Cap-touch is separately blocked** by the titanium back-plate (a grounded plate behind the
  electrode swamps the finger signal — already flagged in `ENCLOSURE-NOTES.md`).
- **Better architecture: pair the haptic with the ACCELEROMETER's tap detection, not cap-touch.**
  The accel works *through* the metal (senses motion, not capacitance), so "tap the card → feel a
  buzz" sidesteps the cap-touch-vs-metal problem. A haptic driver (DRV2605L-class, I2C) would ride
  the same bus as the accel.
- **Thin actuator path = piezo** (trades mechanical height for an HV boost driver, DRV2667-class).
- **Counterpoint:** the snap dome (SW1, on PA7) already gives tactile feedback for free. Haptic
  only earns its complexity for the accel-tap interaction or richer effect patterns.
- **Energy is fine** for occasional clicks: ~10–20 mJ each against ~6–7 J stored → hundreds of
  clicks/charge. Peak current depends on the actuator — a small coin LRA is ~75–100 mA, the
  TapSense is **360 mA**; low-ESR caps handle either on occasional pulses (more rail sag at
  360 mA, but the MCU runs to ~1.8 V). It's a buffer not a budget — continuous buzzing outruns
  the harvest.
- **Status: NOT committed.** No haptic footprint placed yet. Offered to reserve a DRV2605-class
  driver footprint on the I2C bus (parallel to the accel reservation). Open questions: actuator
  choice (TapSense-style thin-but-wide LRA / small coin LRA + pocket / piezo + HV driver), whether
  the layout can host a ~25 mm thin LRA at all, and TapSense sourcing.

---

## 🔒 LOCKED — WS17 supercap footprint (do NOT modify; physically confirmed)

SCHURTER SCPC P/N **3-153-438**, datasheet p4 Case WS17. Solderable terminals are **flat pads
UNDERNEATH the body**, not at the ends. **P pad 7.8 × 3.5 mm; N pad 12.2 × 3.5 mm** (asymmetric
widths are the polarity key). Pad centers at **±11 mm** from cell center, within the 28.5 × 17 mm
body. Protruding end tabs are **coated/non-solderable mechanical locators only**. The old v0/REV-J
diagonal land (two 3.5 × 3.5 pads on the end tabs) is **WRONG — never reintroduce it**. Rotations:
SC1 → 90°, SC2 → 270°, SC3 → 270°, SC4 → 90° (MID terminals inboard toward U2).

---

## Canonical topology checks
- **2P2S** supercaps: SCx P=VS, N=MID; U2 balances the single shared MID.
- **MID bus = exactly 4 cell taps + 3 U2 balancer pins** (U2 pins 4,6,7). Nothing else.
- LED anodes = VS, low-side drive (K2–K5). VDDIO2 jumpered to VS via SJ1 (LDO in v2).
- PV1 (solar) → VIN → D1 (blocking Schottky) → VS. **VS-rail clamp on VIN** (Q1 PNP boosted TLV431
  shunt: VIN clamped 3.72 V → VS ≈ 3.42 V) protects the 3.6 V accel; nets CLBASE/CLREF are internal.
  Coin-battery option (BT1/BT2 + D6/D7) is mutually exclusive with PV1 and is **being removed**
  (PV1 is the committed source; delete in KiCad).
- RESET (PF6) is NC (UPDI handles reset). 13 spare GPIOs on U1 are NC.
- **SB1–SB4** = per-LED disable jumpers: `SBn.1 = LDRVn`, `SBn.2 = GND`. Bridge to ground a driver
  and disable that LED. **U3 (LIS2DH12 accel)** now sits at (20, 35.9), back — the old **M1 keepout
  is superseded and to be deleted**. Accel: CS=VS (I2C), SA0=GND (0x18), INT1→PF1, INT2→PF0, +C6.

---

## Files (repo)
- `solar-glow-drh-v1.kicad_pcb` — the board.
- `solar-glow-drh-v1-netlist.py` — schematic-level NET dict (the source of truth for nets).
- `solar-glow-drh-v1-pinmap.md` — AVR64DD28 pin map.
- `V1-SPEC.md`, `V1-PLAN.md`, `solar-glow-drh-v1-punchlist.md`, `ENCLOSURE-NOTES.md`.
- `motors___ac__dc.csv` — haptic actuator candidates (this session).
- `microcontrollers.csv`, `motors___ac__dc.csv`, and other DigiKey exports — sourcing shortlists.
- `datasheets/` — `typ_SCPC-2.pdf` (WS17 supercap, p4), `en.DM00091513.pdf` (ST LIS2DH12 accel),
  AVR64DD28, Snaptron dome
  (`SW_F12340.kicad_mod`), OSRAM LA P47F, SM141K06L (solar cell), and the **NIDEC TapSense**
  thin-LRA datasheet (1.4 mm / 25×25 mm / 200 Hz / 3 Vrms / 360 mA — see the Haptic section).
- Working-dir Python (renderers `render_back_real.py`/`render_front_real.py`, pad audit
  `pad_sanity.py`, topology `sanity.py`, footprint builders) — regenerate if not present;
  the renderer pad transform is: rotate local pad by footprint angle, translate, swap pad w/h
  on 90/270, `y_gen = 88.9 - (fy + rot_y)`. Back-mirror is baked into stored pad coords.

## Enclosure context
Back-only titanium (Ti-6Al-4V) press-fit cover, naked front (solar/dome/LEDs exposed). Four walls
press-fit over the board edge → **conductive metal at the perimeter can bridge edge pads** (same
failure as dropped castellations; this is why test pads must stay off the edge). Cavity ~1.8 mm
(supercaps at 1.7 mm set it; U2 at 1.75 mm gets a local skin pocket). Metal back kills cap-touch →
snap dome is the primary button. 4× M2 corner bosses (MH1–4).
