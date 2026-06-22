# SOLAR-GLOW · DRH — SESSION HANDOFF (2026-06-21)

Snapshot for a **new Claude session** picking up this board. Read this first, then
`V1-SPEC.md`, `V1-PLAN.md`, `solar-glow-drh-v1-punchlist.md`, `ENCLOSURE-NOTES.md`.

> **This is a personal hardware hobby project, NOT legal work.** Do not apply any legal /
> citation / billing skills. Casual engineer-to-engineer tone, concise, lead with the answer,
> user is on mobile and reacts to rendered images each turn. **Hard anti-fabrication rule:**
> never invent specs / pins / geometry / MPNs — verify against the datasheet or source.
> No em-dashes in chat prose (they're fine in `.md`/`.py` files like this one).

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
1. **KiCad replication + DRC is the endgame.** The generator proves the routing clean (21/21,
   no shorts); Devin reproduces it in KiCad with real DRC for sign-off. To apply in KiCad:
   move the board to **6-layer**, apply the **C3 nudge** (12.5, 48.5), **delete the battery**
   (BT1/BT2/D6/D7), and replicate the inner routing + SB-jumper connections + via placements.
2. **Resolve TC1-under-SC1** (Tag-Connect physically under SC1) and confirm the two
   under-supercap vias (TC1.1, BTN @42,78) clear the cell undersides.
3. **Voltage coordination** (still open): shunt clamp vs 5.5 V caps vs lower-VOC solar cell.
4. **Confirm a real ~565 nm reverse-mount LED exists** (flagged sourcing risk).
5. **Accelerometer**: M1 reserves the spot (20, 35.9). Part shortlist in `accelerometers.csv` —
   recommended **ST LIS2DH12** (~$1.79, 2×2 12-LGA, INT1/INT2), I2C on the existing SDA/SCL bus
   + VS/GND + 1–2 INT off spare GPIOs. Not yet placed/wired.
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
- PV1 (solar) → VIN → D1 (blocking Schottky) → VS. Coin-battery option (BT1/BT2 + D6/D7) is
  mutually exclusive with PV1 and is **being removed** (PV1 is the committed source; delete in KiCad).
- RESET (PF6) is NC (UPDI handles reset). 13 spare GPIOs on U1 are NC.
- **SB1–SB4** = per-LED disable jumpers: `SBn.1 = LDRVn`, `SBn.2 = GND`. Bridge to ground a driver
  and disable that LED. **M1** reserves the accelerometer spot (NC keepout, back, (20, 35.9)).

---

## Files (repo)
- `solar-glow-drh-v1.kicad_pcb` — the board.
- `solar-glow-drh-v1-netlist.py` — schematic-level NET dict (the source of truth for nets).
- `solar-glow-drh-v1-pinmap.md` — AVR64DD28 pin map.
- `V1-SPEC.md`, `V1-PLAN.md`, `solar-glow-drh-v1-punchlist.md`, `ENCLOSURE-NOTES.md`.
- `motors___ac__dc.csv` — haptic actuator candidates (this session).
- `microcontrollers.csv`, `motors___ac__dc.csv`, and other DigiKey exports — sourcing shortlists.
- `datasheets/` — `typ_SCPC-2.pdf` (WS17 supercap, p4), AVR64DD28, Snaptron dome
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
