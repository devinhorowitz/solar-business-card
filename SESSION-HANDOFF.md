# SOLAR-GLOW · DRH — SESSION HANDOFF (2026-06-21)

Snapshot for a **new Claude session** picking up this board. Read this first, then
`V1-SPEC.md`, `V1-PLAN.md`, `solar-glow-drh-v1-punchlist.md`, `ENCLOSURE-NOTES.md`.

> **This is a personal hardware hobby project, NOT legal work.** Do not apply any legal /
> citation / billing skills. Casual engineer-to-engineer tone, concise, lead with the answer,
> user is on mobile and reacts to rendered images each turn. **Hard anti-fabrication rule:**
> never invent specs / pins / geometry / MPNs — verify against the datasheet or source.
> No em-dashes in chat prose (they're fine in `.md`/`.py` files like this one).

---

## Where the board is

`solar-glow-drh-v1.kicad_pcb` — 4-layer, 0.4 mm, PCBWay. **39 footprints. Pad-clean and
courtyard-clean** (verified at the pad level, not just courtyards). Portrait 50.8 × 88.9 mm,
0.8 mm FR4, ENIG. Stackup: L1 F.Cu signal/parts, L2 In1.Cu GND plane, L3 In2.Cu VS plane,
L4 B.Cu signal/parts. MCU = AVR64DD28 VQFN28. 4× WS17 supercaps (2P2S → ~500 mF @ 5.5 V),
U2 (ALD810025 SOIC-8) balances the shared MID. Glow = 4 rear LEDs (LA P47F) backlighting a
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
1. **Routing** is the endgame — interactive KiCad + DRC. (Standing principle: hand-coded
   polygon routing is NOT the tool for final copper sign-off on a board this dense. Claude's
   job is to get it routable-clean, which it now is, and optionally rough-in short/obvious nets.)
   No vias to the inner planes are placed yet; every VS/GND pad needs one. LED anodes sit inside
   the glow void (VS voided there) so each needs a short VS trace out to a via.
2. **SW2 net assignment** once the TINY decision is made (footprint ready, 3-pad solder jumper).
3. **PV1 solar tabs sit 2.3 mm from the side edges (front).** Front is naked so lower risk, but
   confirm the enclosure's front-wrap width — if the wall wraps onto the front by >2 mm it could
   touch them. Cell body clears any reasonable wrap; only the tabs are borderline. Not moved
   (would mean reworking the 42×23 solar footprint).
4. **Front art → real F.Cu zones** (shaped GND pour + DRH letterforms + QR + frame + contact
   block). Preserve the aesthetic already confirmed.
5. **Haptic / actuator decision** — see next section.

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
  mutually exclusive with PV1.
- RESET (PF6) is NC (UPDI handles reset). 13 spare GPIOs on U1 are NC.

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
