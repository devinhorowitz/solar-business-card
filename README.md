# SOLAR-GLOW · DRH

A business card that runs on light. An AVR microcontroller breathes four amber LEDs
*through* the board — a monogram cut into the front copper that glows when the rear LEDs
backlight it through the bare fiberglass — while a pair of indoor solar cells trickle-charge
a supercapacitor bank that holds the charge.

![SOLAR-GLOW · DRH — front and back, gold ENIG on black soldermask](docs/board-preview.png)

> **Status: v3.0 — fully routed, audit-clean. Not yet fabbed.**
> Two-layer, 0.8 mm FR4, bound for PCBWay, with the 4-layer **v2.3** kept as the committed fallback.
> The one thing standing between here and a build is the **energy budget** — harvest vs. draw under
> real indoor light has never been measured. See *“The open question.”*

### Current revision — the one canonical summary

| What | Current | Notes / fallback |
|---|---|---|
| **PCB** | **v3.0 — 2-layer** (F / B) | GND = full-board B.Cu pour; VS = routed B mesh. **v2.3 (4-layer: F / In1 GND / In2 VS / B) is the committed fallback.** v2.1 was 6-layer (history). |
| Board | 50.80 × 88.90 mm, r3.0 corners, **0.80 mm** FR4, ENIG, matte-black mask | 0.8-vs-1.0 mm thickness still open |
| Mounting holes | 4× M2, GND, at **(3.0, 3.0) / (47.8, 3.0) / (3.0, 85.9) / (47.8, 85.9)**, pitch **44.80 × 82.90 mm** | concentric with the r3.0 corner fillets |
| **Enclosure** | **v3.0 Ti back-shell** — 0.75 floor, 1.85 cavity (1.90 local under U2), overall **3.55 mm**, braces off | matches the v3.0 hole pattern; see `enclosure/README.md` |
| BOM | **unchanged across v2.1 → v3.0** | master is `PCB/solar-glow-drh-v2_1-BOM.xlsx`; no per-revision BOM |
| Firmware | register-verified C, not yet on hardware | LED pin map re-mapped in v3.0 (see `firmware/README.md`) |

### Where the truth lives — how these docs stay from drifting

Each fact has exactly one home; everything else points at it rather than restating it.

| Domain | Source of truth |
|---|---|
| Board copper / geometry / holes | `PCB/solar-glow-drh-v3_0.kicad_pcb` + `.kicad_sch` |
| Enclosure geometry | `enclosure/solar-glow-drh-v3_0-backshell-cad.py` (prints the Z-stack; regenerates the STEP) |
| Firmware pin map + knobs | `firmware/README.md` (matches the schematic) |
| BOM | `PCB/solar-glow-drh-v2_1-BOM.xlsx` (unchanged through v3.0) |
| Design *reasoning* / lineage | `solar-glow-drh-design-notes.md` |

When a number here disagrees with a source-of-truth file, the source file wins and this table is the
thing to correct. The `solar-glow-drh-v2-*` docs are v2-era history (banner-marked at the top of
each); read them for lineage, not for current values.

---

## What it is

A business-card-sized PCB — **50.8 × 88.9 mm, 0.8 mm FR4, ENIG, rounded corners** — that:

- **Harvests** indoor light with **two** ANYSOLAR solar cells wired in parallel, each behind
  its own blocking diode so a half-shadow on one can’t back-feed the other.
- **Stores** energy in **four** series-parallel supercapacitors — **1 F at 5.5 V, ≈ 15 J** —
  kept balanced by a dual SAB-MOSFET, and held to a safe voltage by a shunt clamp.
- **Glows** by back-lighting a **“DRH” monogram** that’s cut into the front copper: a gold
  ENIG field with the three letters opened to bare FR4. Four reverse-mounted amber LEDs on the
  back fire up through the translucent substrate, so the letters themselves light up — and PWM
  on the LED drives makes them breathe.
- **Wakes** to a **tap.** A 3-axis accelerometer feels you pick the card up (or the enclosure
  being tapped) and interrupts the MCU out of sleep — no button, no moving parts.

The front face stays naked — solar cells and the glowing monogram exposed — and the dense work
all lives on the back, ready for an optional machined-metal back-shell.

> **A note on lineage:** earlier revisions (REV J and before) were *generated from Python* —
> geometry and Gerbers emitted by script, no layout tool in the loop. **v2.1 is a full KiCad
> design** (schematic + board), continued through v3.0. The old generators are kept only as
> history; the KiCad files are the source of truth.

---

## How it works

| Block | Part | Notes |
|---|---|---|
| MCU | **AVR64DD28** (28-VQFN) | TCA0 hardware PWM, I²C to the accel, charge/sleep logic; MVIO-capable |
| Solar | **2× ANYSOLAR SM141K06TF** | monocrystalline indoor cells (Voc 4.15 V), in parallel — two panels ≈ 2× the harvest |
| Blocking diodes | **2× onsemi MMSD301T1G** | Schottky, one per panel; isolates the cells *and* the supercaps |
| Storage | **4× SCHURTER 3-153-438** (WS17) | 1 F / 2.75 V each, wired 2P2S → **1 F @ 5.5 V ≈ 15 J** on one balanced node |
| Balancer | **ALD910025SALI** | dual SAB MOSFET — the low-leakage way to hold the series midpoint |
| Rail clamp | **TI TLV431 + onsemi BCP53 PNP** | shunt clamp holds the rail **≤ ~3.47 V** so the accel stays inside its 3.6 V max |
| LEDs | **4× ams OSRAM LA P47F** (amber) | reverse-mount; glow through the FR4 window, **150 Ω** ballast each |
| LED master switch | **SW2** (solder-bridge) + **R12** | OFF / ON / TINY — TINY routes the LEDs through a 220 Ω ballast for a dim, long-runtime glow |
| Motion | **ST LIS2DH12** | 3-axis accel; tap / double-tap wakes the MCU via interrupts |
| Light sense | **R5 / R6 divider → PD2** | VIN ÷ 2 off the *solar input* (not the rail) — tracks light directly; doubles as wake-on-light |
| NFC | **NXP NT3H2211** (NTAG I²C plus 2K) | present from v3.0 — a contact **vCard** a phone taps to save; field-detect (FD, PA6) also wakes the glow — I²C `0x55`, shares the accel's bus |

**Breakouts and features:** a **TC2030** Tag-Connect pad (`TC1`) for hands-free UPDI
programming, a backup UPDI header (`J1`), an I²C expansion header (`JP1`), a spare-GPIO header
(`JP2`), per-LED disable jumpers (`SB1–4`), a VDDIO2 tie jumper (`SJ1`), and **four grounded
M2 mounting holes** at the corners.

Full part numbers, pricing, and per-part datasheet links are in
**`PCB/solar-glow-drh-v2_1-BOM.xlsx`** — the master BOM, **unchanged across v2.1 → v3.0** (same parts).

---

## The board

- **Two copper layers** on 0.8 mm FR4 (v3.0): **F.Cu** signal/parts and **B.Cu**. **GND is a
  full-board B.Cu pour** (`GND_B` zone) with stitch straps, and **VS is a routed mesh on B** — the
  4→2-layer conversion of v2.3, whose internal GND/VS *planes* moved onto the back copper. The
  4-layer **v2.3** (F · In1 GND · In2 VS · B) is the committed fallback if the back-side trace
  texture showing faintly on the naked front reads wrong.
- **The glow window is a keepout on every layer.** The monogram cutout and the four LED
  light-paths are voided through both layers so nothing — copper pour, trace, or via —
  shadows the light between the rear LEDs and the front face. The rear soldermask is left
  *open* over the window on purpose: bare ENIG reflects the LEDs’ light forward instead of
  absorbing it.
- **Rail discipline.** The supercap stack can sit near 5.5 V, but the accelerometer tops out at
  3.6 V — so a TLV431-referenced PNP shunt clamp sits on the **VS rail** (after the blocking
  diodes) and holds VS ≤ ~3.47 V, directly limiting what the accelerometer sees. Its sense
  divider draws a standing microamp or two from the rail — small against the other always-on
  loads, and the trade for regulating VS itself rather than the solar input.
- **Power planes** carry the supercap charge/discharge currents; the four cells eat the better
  part of the back, so the layout is geometry-bound and the planes earn their layers.

---

## The open question — read this before building a batch

The board is well-verified; the **energy budget is not.** A solar cell’s headline rating is a
full-sun number, and indoor light delivers a small fraction of it, while four breathing LEDs
average several milliamps. The two-panel harvest and the 15 J tank are sized to **harvest
slowly and glow in bursts** — but that bet has never been put on a meter.

What changed the math since the early notes: the rail is now **clamped to ~3.47 V** and the
ballasts are **150 Ω**, so each LED peaks near **~9 mA** rather than the old estimate. Four
on at once is a real load against an indoor harvest measured in fractions of a milliamp.

**First move when boards arrive:** put the cells under your actual target lighting and measure
**harvest current against LED draw** before you populate a full stack. That single number sizes
the duty cycle, the feature set, and whether the always-on accelerometer earns its microamps.

---

## Repository layout

```
solar-business-card/
├── README.md                       # this file (canonical current-revision summary)
├── PCB/                            # KiCad projects + fabrication BOM
│   ├── solar-glow-drh-v3_0.kicad_pcb   # the board — v3.0, 2-layer (source of truth)
│   ├── solar-glow-drh-v3_0.kicad_sch   # schematic (v3.0)
│   ├── solar-glow-drh-v2_3.kicad_pcb   # 4-layer fallback — kept, not deleted
│   ├── solar-glow-drh-v2_1-BOM.xlsx    # bill of materials — parts, prices, links (master; unchanged through v3.0)
│   └── README.md                       # order & build guide
├── solar-glow-drh-v2-hardware.md   # as-built wiring & pin map (v2-era; v3.0 LED-map delta noted at top)
├── solar-glow-drh-v2-mechanical.md # board mechanics, keepouts, access (v2-era; v3.0 hole/enclosure deltas at top)
├── solar-glow-drh-design-notes.md  # design rationale, energy model, lineage (incl. the v3.0 chapter)
├── firmware/                       # bare-metal C (AVR64DD28); register-verified, see firmware/README.md
├── datasheets/                     # every component's datasheet
├── docs/                           # renders and figures
├── enclosure/                      # machined-titanium back-shell: CAD / STEP / STL / README (v3.0 + v2.1 kept)
└── v0 prototype/                   # the original prototype, kept for posterity
```

---

## Building the board

The board is a KiCad project — open it, run DRC, and export the fab set:

1. Open `solar-glow-drh-v3_0.kicad_pro` in **KiCad** (2026 file format).
2. **Run DRC.** It comes back clean apart from the intentional exceptions catalogued in
   `PCB/README.md` and `solar-glow-drh-design-notes.md` (the NFC coil `LA`↔`LB` short, the four
   GND-tie mounting-hole/gold-frame contacts, the two plating-bus stubs crossing Edge.Cuts at
   x=25.4, the illumination copper inside the glow window, and the benign `lib_footprint_issues`
   plus the reserved `BTN` `track_dangling`). Fill zones (press **B**) before checking.
3. **Plot Gerbers + drill** from KiCad's own Fabrication Outputs and order from **PCBWay**
   (**2-layer**, 0.8 mm; selective hard gold + plating bus + resin-fill/cap per `PCB/README.md`).

> The supercap land is the one thing to never get wrong. The WS17 cell solders to **flat pads
> under its body** (the asymmetric P/N widths are the polarity key), **not** to the folded end
> tabs — those are non-solderable mechanical locators. The footprint in this design is built to
> the correct under-body land; don’t substitute an end-tab land.

---

## Assembly order (when boards arrive)

1. **Validate the energy budget first** — harvest vs. LED draw under real lighting (above).
2. **Reflow the SMD parts** — the QFN MCU and the LGA accelerometer need hot air / a hotplate;
   the EP and the accel pad reflow to their planes.
3. **Hand-solder last** — the solar cells (heat-sensitive: ≤ 260 °C / 2 s, no IPA), and set the
   **SW2** bridge for OFF / ON / TINY.
4. **Flash firmware** over UPDI — the Tag-Connect pad (`TC1`) is the no-header path; `J1` is the
   backup header.

---

## Firmware

A first implementation now lives in **`firmware/`** — bare-metal C, **verified at the register
level** against the AVR64DD28 and LIS2DH12 datasheets but **not yet compiled against a real
toolchain or run on hardware**. Its knobs, wake model, and power notes are in
**`firmware/README.md`** (authoritative); the wiring it targets is in
**`solar-glow-drh-v2-hardware.md`** (complete pin map, PORTMUX, the accel at I²C `0x18`). Final
duty-cycle and feature tuning stay **gated on the energy-budget measurement** below. In short,
the board gives it:

- **LED breathing** — the four LEDs sink into **PA0–PA3 = TCA0 WO0–WO3**, so split-mode PWM
  drives all four as independent 8-bit channels (the 150 Ω ballast sets the peak; PWM sets the
  average, so you trim brightness *below* that ceiling).
- **Tap-to-wake** — the accelerometer’s two interrupts land on **PF1 / PF0**; configure
  tap / double-tap and let it pull the MCU out of sleep.
- **NFC contact tag** — `U5` (NXP NT3H2211, on the board from v3.0) carries a **vCard** a phone reads on a
  tap to save the contact (RF-powered, so it reads with the cap flat), and its **field-detect**
  line wakes the same glow. Shares the I²C bus with the accel (`0x55` vs `0x18`). See
  `firmware/README.md` → *NFC contact card*.
- **Light sensing** — the divider taps the **solar input** (VIN ÷ 2) into **PD2** (AIN2), so it
  reads light directly — ~0 V dark, rising under light; firmware adapts the glow to available
  light and can also read **VDD/10** and the internal temp sensor.
- **Wake-on-light** — the card can also wake when light appears, with no tap. The implemented
  path is an **RTC-timed ADC poll** in deep Power-Down (sample PD2/AIN2 every ~1–2 s, glow on a
  dark→light rise). The tempting *instant* AC0-comparator version was checked against the
  datasheet and found **non-viable on this part** — the AC interrupt doesn't update with the
  peripheral clock stopped, and the AC isn't a Standby/Power-Down wake source, so it would never
  fire. Instant response isn't lost: the accelerometer interrupt wakes from Power-Down, and
  picking the card up to carry it into the light *is* that motion. (Standing current is
  dominated by the always-on accelerometer, not the poll — see `firmware/README.md`, and the
  corrected `solar-glow-drh-v2-hardware.md` §6.)
- **Low-power housekeeping** — `VREGCTRL.PMODE = AUTO` for sub-µA power-down; RTC/PIT off the
  internal ULP oscillator (no crystal); an EEPROM “times-activated” counter that survives a
  full supercap drain; and the core **IDLE-sleeps through the breathing glow** while TCA0 keeps
  the PWM running, rather than busy-waiting. (An autonomous CCL + EVSYS light-wake is a possible
  v-next, but isn't what the current firmware does.)

Still open (what the bench measurement unlocks): final breathing-curve and tap-gesture tuning,
charge / brown-out management around the supercap bank, and the duty-cycle adaptation the
harvest number sizes.

---

## Enclosure (parked)

An optional back-only **machined-titanium** shell hugs the populated rear; the front stays naked.
CAD, STEP, STL, fab notes and a dimensioned drawing are in `enclosure/`, on ice until the board is
validated — see `enclosure/README.md`.

![Titanium back-shell (Ti-max) — design render, not yet built](docs/enclosure-hero.png)

The decisions that matter once it’s cut: **titanium (Ti-6Al-4V Grade 5)**, **3-axis CNC-milled** by
PCBWay, **bead-blast** finish; the general cavity is **cap-limited to 1.85 mm** by the four 1.70 mm
supercaps (U2 at 1.75 mm sits over a small **relief pocket** that drops the local floor 0.05 mm so it
still clears), the floor runs to **0.75 mm** of engraving stock backed by ribs, and the overall height
is **3.55 mm**. The four bosses sit on the **v3.0 hole pattern** (concentric with the r3.0 corner
fillets), the internal braces are **removed**, and retention is **four corner M2 screws**, not a press
fit. The electrical gotcha — the screws tie the metal body to board GND, so the enclosed variant
**drops the edge castellations** (or adds a die-cut Kapton layer) so nothing shorts to the grounded
shell, and the **accelerometer tap is the actuator** (cap-touch dies behind a grounded plate). The
dimensioned drawing is mid-regeneration for v3.0 — see `enclosure/README.md`.

---

## Cost

- **Per board ≈ $100** at quantity one, and the **four supercaps are the dominant line** —
  well over half the BOM. This is a showpiece, not a hand-out-by-the-hundred card.
- The energy tank is where the money goes; everything else is comparatively cheap.

---

*© 2026 Devin R. Horowitz. Released under the [MIT License](LICENSE).*
