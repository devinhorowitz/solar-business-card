# Harvest-budget test board -- design handoff

**Status: design spec / handoff -- not yet laid out.** A small, single-sided PCB that answers
one question at a glance, with no instrument: *at this light, can the two SOLAR-GLOW panels
out-harvest the card's own draw?* It carries the two product panels, top-side probe pads, and
a **self-powered "harvest surplus" blink indicator** whose flash rate is proportional to the
net power the panels bank *over a jumper-selected load that emulates the card's consumption*.

This is the **live-harvest / budget** companion to `harvest-bench-fixture-handoff.md`. That
board is the precise instrument (4-wire panel I-V curve, needs an SMU/DMM); **this** board is
the glanceable go/no-go you leave on the desk. Use them together: characterize V<sub>mp</sub>
with the fixture, then set this board's window around it (section 5).

---

## 1. What it is / is not

- **Is:** 2 panels (parallel = the product's SRC node), a passive reverse-blocking diode into a
  small storage cap, a nanopower relaxation blinker, a **jumper-selected calibration load**, and
  top-side probe pads. Reads out **as a blink rate** (qualitative, glanceable) **and** as a
  scope-able ramp on one pad (quantitative, no series break).
- **Is not:** the product front-end. It deliberately omits the AEM10300 so it stays simple and
  self-powered. That makes it a **conservative proxy**: it parks the panels at V<sub>CAP</sub>
  (~2.2-3.0 V), *below* the MPP the AEM would hold, so it under-reads what the real card
  harvests. **If this board says net-positive, the AEM-boosted card comfortably is** (MPPT gain
  1.3-2.2x, per the fixture doc). For the exact card number, use the fixture's SMU sweep or a
  future AEM-in-the-loop board.

---

## 2. Panels -- same as the product

2x **ANYSOLAR SM141K06TF** (PV1, PV2), wired **parallel** into SRC (the product config; the v3
per-panel blocking diodes are gone). Reuse `solarglow:PV1` / `solarglow:PV2` from
`PCB/solar-glow-drh-v4_0.kicad_pcb` -- do not re-derive the land. Datasheet anchors (1 sun):
Voc 4.15 V, Isc 58.6 mA, V<sub>mp</sub> 3.35 V, I<sub>mp</sub> 55.1 mA, P<sub>max</sub> 184 mW;
indoors these scale ~with lux (desk ~400 lux ~= 0.4 % sun -> ~0.5-1 mW per panel, ~1-2 mW the
pair). **Manual solder only, <= 260 C / 2 s, no reflow** (moisture-sensitive laminate).

---

## 3. How the indicator works

```
 PV1 ||                      D1 (Schottky, reverse block)
 PV2  +----[SRC]----o SRC+----|>|----o VCAP ---+------+-------------+
      |             (probe)          (probe)   |      |             |
     GND                                     C_store  R_load       comparator relaxation
      |                                        |     (jumper       (TLV3691 nanopower) +
      +----------------------------------------+------ bank)------- LED flash + hysteresis
                                               |      |             |
                                              GND    GND           GND
```

- **D1** blocks the cap from back-feeding the panels in the dark (the AEM does this actively in
  the product; a passive board needs the diode). Use a low-V<sub>f</sub> Schottky (e.g. BAT54,
  or the MMSD301 land the card retired).
- **C_store** is the mini "tank." The panels charge it; the blinker dumps a fixed energy quantum
  out of it through the **LED** each time it reaches the upper threshold, then it recharges.
- **The comparator** (nanopower, ~0.15 uA -- e.g. TI **TLV3691**) plus a hysteresis divider make
  a relaxation oscillator on V<sub>CAP</sub>: charge to **V<sub>hi</sub>**, flash + discharge to
  **V<sub>lo</sub>**, repeat. Defaults **V<sub>hi</sub> ~= 3.0 V, V<sub>lo</sub> ~= 2.2 V** --
  chosen to (a) straddle the likely indoor V<sub>mp</sub> so the panels sit near their MPP, and
  (b) stay above the LED forward drop. Retune the divider once the fixture board measures the
  real indoor V<sub>mp</sub>.
- **R_load** (the jumper bank, section 5) sinks a current that **emulates the card's average
  draw**. The blinker only advances when **harvest > R_load**, so *the LED blinking at all means
  the panels are net-positive at that usage level*, and the **rate is the surplus**.

**Blink-rate law (this is the calibration):**
> f_blink = P_net / E_flash,  where  E_flash = 1/2 * C_store * (V<sub>hi</sub>^2 - V<sub>lo</sub>^2)
> and P_net = P_harvest - P_load - P_quiescent.

With **C_store = 1000 uF**, V<sub>hi</sub> 3.0 / V<sub>lo</sub> 2.2 V -> **E_flash ~= 2.1 mJ**:

| Blink rate | Net surplus over the selected load |
|---|---|
| 1 / sec | ~2.1 mW |
| 1 / 10 sec | ~210 uW |
| 1 / min | ~35 uW |
| (no blink, cap stuck low) | harvest < selected load at this light |

Silk-screen that table. Bigger C_store = slower, "chunkier" blinks (more energy per flash);
drop to ~220 uF for livelier blinks in dim light. A small 0.1 F EDLC also works (very slow,
very visible pulses).

---

## 4. Reading it (bench use)

1. Set the panel angle/distance to your real use case; note the lux (phone app is fine) and
   panel temperature (Voc tempco -10.4 mV/K).
2. **Pick the load jumper = the usage you care about** (idle vs light vs active glow, section 5).
3. **Watch the LED:**
   - **Blinking** -> panels are net-positive at that usage; **count the rate -> surplus power**
     from the table. Faster = more margin.
   - **Dark (cap never reaches threshold)** -> harvest is below that usage level here; step the
     load jumper down (to idle) to find where it *does* go net-positive.
4. **For a number, don't break the circuit:** scope the **VCAP** pad. The charging ramp's slope
   gives **I_net = C_store * dV/dt** directly (net harvest current into the cap), and the flash
   interval gives P_net independently -- two cross-checks, no series ammeter.
5. Sanity anchor: at a desk you should see blinks with the idle load and slower/none as you step
   to the active-glow load. In a dim room, expect idle to still blink slowly and light-use to
   stop -- that boundary is the actual answer to the open gate.

---

## 5. Calibration to the card's usage (the load bank)

R_load is a **jumper- or DIP-selected resistor to GND**, sized so its current at the mean
V<sub>CAP</sub> (~2.6 V) equals a card operating average. Representative set (retune to taste):

| Jumper | Emulates | Card avg current | R (@ ~2.6 V) | Meaning if it blinks |
|---|---|---|---|---|
| **OFF** | nothing (raw harvest) | 0 | open | pure panel-into-cap rate; "is there any harvest?" |
| **IDLE** | standing (accel + MCU sleep + poll) | ~2.7 uA (~9 uW) | **~1.0 M** | the card survives here doing nothing |
| **LIGHT** | idle + a few glows/day, averaged | ~30 uA (~90 uW) | **~82 k** | sustains light interactive use |
| **ACTIVE** | frequent glowing | ~300 uA (~0.9 mW) | **~8.2 k** | sustains heavy use |

Notes:
- These currents come from the card's power model (idle ~2.7 uA standing; a breath is ~15-30 mA
  for a few seconds, so the *average* is dominated by how often it glows). Print the assumptions
  on the silk so the load meanings are unambiguous.
- A resistor is a fixed conductance, not a fixed current, so its draw sags a little as
  V<sub>CAP</sub> ramps -- fine for a go/no-go. If you want a true constant-current emulation of
  the card, populate a 2-transistor current sink or a JFET+R in the R_load land instead (DNP
  option).
- **The load bank IS the "calibrated to our setup" part.** Swapping the jumper reframes the
  blink from "is there sun" to "can it run the card *at this duty*."

---

## 6. Probe pads (top side, sized for mini-grabbers)

| Pad | Node | Use |
|---|---|---|
| **SRC+ / GND** | panel output | panel terminal V; DMM Voc with load off |
| **I_SRC** | series break in the SRC leg | open the jumper, insert a uA DMM in series for direct harvest current |
| **VCAP** | storage cap top | scope the ramp (slope = net harvest current) + flash pulses |
| **VLO/VHI** | comparator threshold divider taps | verify/tune the window with a DMM |
| **PV1+/-, PV2+/-** | each panel | per-panel Voc / shading checks, 2-instrument reads |

Keep a **SENSE pair** at the panel lands (Kelvin) if you also want clean 4-wire panel voltage
under load, same as the fixture board.

---

## 7. Bill of materials (minimal, all top-side)

| Ref | Part | Qty | Note |
|---|---|---|---|
| PV1, PV2 | ANYSOLAR SM141K06TF | 2 | reuse `solarglow:PV*`; manual solder, no reflow |
| D1 | Schottky, low Vf (BAT54 / MMSD301) | 1 | reverse block into the cap |
| C_store | 1000 uF (or 220 uF livelier / 0.1 F EDLC slow) | 1 | sets blink energy quantum |
| U1 | TLV3691 nanopower comparator (or equiv.) | 1 | 0.15 uA; the relaxation oscillator |
| LED1 | red/amber high-efficiency LED | 1 | the flash; low Vf so it fires below Vhi |
| R_hys, R_div | comparator hysteresis + threshold divider | ~3-4 | set Vhi/Vlo (~10 M scale to stay sub-uA) |
| R_led | LED series limit | 1 | ~100-330 ohm, sets flash brightness/energy |
| R_load bank | IDLE/LIGHT/ACTIVE resistors + jumpers | 3 + 4 | calibration loads (section 5); DNP current-sink option |
| A/B config + I_SRC | 2-pin headers / solder jumpers | ~3 | parallel-only needed; keep the series break |
| pads / TPs | plated probe pads | ~10 | 2.0-2.5 mm |
| H1-H4 | mounting holes | 4 | stand it at a repeatable angle |

Optional DNP: a 1 uF film across SRC to average 100/120 Hz room-light flicker for a steady mean.

---

## 8. Layout (single-sided)

- **All assembly + all pads on top; back is routing/vias only** (flat for handling, faces up to
  the light) -- same rule as the fixture board.
- **Outline:** reuse SOLAR-GLOW **50.8 x 88.9 mm** Edge.Cuts so it feels like the product (free
  to shrink; the two 42 x 23 mm panels are the size floor).
- **Floorplan (portrait):** PV1 top, PV2 below (both faces up, centered); bottom strip = the
  indicator cluster (D1, C_store, U1, LED where you'll actually see it) + the load-jumper row +
  the probe-pad field. Put **LED1 near the top edge** so it's visible with the board flat on a
  desk.
- **Silk earns its keep:** the blink-rate table (section 3), the load-jumper legend (section 5),
  and the datasheet anchors (Voc 4.15 / V<sub>mp</sub> 3.35 / Isc 58.6 mA @ 1 sun).

---

## 9. Two indicator tiers (pick one)

- **Tier 1 -- dead simple (~2 parts).** One high-efficiency LED across V<sub>CAP</sub> through a
  large series R: glows when the panels produce, brighter in more light. Zero calibration, but it
  loads the panel and only says "there is light," not "enough for the card." Good as a first cut.
- **Tier 2 -- calibrated (recommended, this doc).** The blink-rate relaxation + load bank above:
  self-powered, rate = surplus, jumper = usage. ~8 parts, still single-sided and simple.

---

## 10. Open choices for you

- **C_store value / type** -- ceramic-tantalum 1000 uF (default), 220 uF (livelier), or a 0.1 F
  EDLC (slow, dramatic pulses). Sets the blink cadence.
- **R_load: resistor (simple) vs a 2-transistor constant-current sink (faithful).** Resistor is
  fine for go/no-go; the sink better mimics the card's flat current draw.
- **Config jumpers** -- parallel is the only product-relevant case, so you can hard-wire PV1||PV2
  and keep just the I_SRC series break + the load bank, or keep the fixture board's full A/B/C/D/S
  set if you want singles/series too.
- **Take it to KiCad:** the capture-ready schematic is **Appendix A** below -- component table,
  full net list, and the threshold math. Capture it as-is; the two analog thresholds want a
  quick LTspice/bench tune (A.4), so treat the resistor values as starting points.

---

## Appendix A -- Schematic (capture-ready)

The Tier-2 (calibrated blink-rate) circuit. This is a **passive solar front-end + a nanopower
voltage-trigger blinker** (the classic "solar-engine" pattern): the panels trickle-charge
C_store; when it reaches V<sub>hi</sub> the trigger flashes the LED and dumps the cap to
V<sub>lo</sub>; it recharges; repeat. Blink rate = net surplus power (section 3).

**Delivered as a capture spec, not a raw `.kicad_sch`, on purpose:** there is no `kicad-cli`
in this environment to ERC-validate a generated file, and the repo's symbol library is
per-refdes custom (no LED / MOSFET / comparator symbols) -- so a hand-built binary would be a
liability, not a head start. The net list below captures cleanly in ~20 min and is unambiguous.

### A.1 Signal flow

`PV1||PV2 -> SRC -> [I_SRC break] -> D1 -> VCAP( C_store )` and off VCAP hang three things:
the **trigger** (U1 divider R1/R2 -> V<sub>REF</sub>, compared to U1's internal 1.182 V), the
**flash path** (R_led -> LED1 -> Q1 to GND, Q1 gated by the trigger output), and the
**calibration load bank** (R_idle / R_light / R_active, each jumper-selected to GND).

### A.2 Components

| Ref | Value | KiCad symbol | Footprint | Note |
|---|---|---|---|---|
| PV1, PV2 | SM141K06TF | `solarglow:PV1` / `PV2` (reuse) | `solarglow:PV1` / `PV2` | panels ||, = product SRC |
| D1 | BAT54 (Schottky) | `Device:D_Schottky` | SOT-23 / SOD-323 (or reuse `solarglow:D2` land) | reverse block into cap |
| C1 | 1000 uF (C_store) | `Device:C_Polarized` | tantalum/elec, or 0.1 F EDLC | blink energy quantum |
| U1 | MAX931 (nanopower comp + 1.182 V ref + hysteresis) | `Comparator:MAX931` (or LTC1540) | SOIC-8 / uMAX-8 | **confirm pinout at capture** |
| Q1 | 2N7002 (N-MOSFET) | `Device:Q_NMOS_GSD` | SOT-23 | flash / discharge switch |
| LED1 | red/amber, high-eff | `Device:LED` | 0805 | the indicator |
| R1 | 6.8 M | `Device:R` | 0402 | divider top (VCAP->VREF) |
| R2 | 4.7 M | `Device:R` | 0402 | divider bottom (VREF->GND) |
| R3 | 10 M | `Device:R` | 0402 | hysteresis (OUT->VREF) |
| R_led | 220 ohm | `Device:R` | 0402 | flash current limit |
| R_idle / R_light / R_active | 1.0 M / 82 k / 8.2 k | `Device:R` | 0402 | calibration loads (section 5) |
| JP1-3 | load select | solder-jumper / 2-pin | -- | one-per-load to GND |
| J_SRC | series I break | 2-pin header | -- | insert uA DMM; default closed |
| TP1-6 | SRC / VCAP / VREF / COMP / GND / panel taps | test point | 2.0-2.5 mm pad | probe |
| PWR1-3 | on SRC, VCAP, GND | `solarglow:PWR_FLAG` (reuse) | -- | ERC (no driven power pin) |
| H1-4 | mounting | `solarglow:MH*` | M2 | stand at a fixed angle |

### A.3 Net list (net : pins)

```
SRC     : PV1.+  PV2.+  J_SRC.1  TP1  PWR1
VIND    : J_SRC.2  D1.A                       (= SRC if J_SRC closed / omitted)
VCAP    : D1.K  C1.+  U1.V+  R1.1  R_led.1  R_idle.1  R_light.1  R_active.1  TP2  PWR2
VREF    : U1.IN+  R1.2  R2.1  R3.2  TP3
UREF    : U1.REF  U1.IN-                       (internal 1.182 V ref tied to IN-)
COMP    : U1.OUT  R3.1  Q1.G  TP4
LED_A   : R_led.2  LED1.A
LED_K   : LED1.K  Q1.D
GND     : PV1.-  PV2.-  C1.-  U1.V-  U1.GND  R2.2  Q1.S  JP1.2  JP2.2  JP3.2  TP5  PWR3
(load bank: R_idle.2->JP1.1, R_light.2->JP2.1, R_active.2->JP3.1; close one jumper)
```

### A.4 Threshold design (the two numbers to tune)

U1 trips when its divider node hits the internal reference: **V<sub>hi</sub> = 1.182 * (1 +
R1/R2)**. With R1 6.8 M / R2 4.7 M -> **V<sub>hi</sub> ~= 2.9 V** (sits near the indoor MPP and
above the LED V<sub>f</sub>). Hysteresis from R3 (OUT->VREF): **ΔV ~= V<sub>hi</sub> * (R1||R2) /
R3**; with R3 10 M -> **ΔV ~= 0.8 V, so V<sub>lo</sub> ~= 2.1 V**. Flash quantum **E =
1/2*C1*(V<sub>hi</sub>^2 - V<sub>lo</sub>^2) ~= 2.0 mJ** at 1000 uF -> the section-3 rate table.

Tune once: (1) re-center V<sub>hi</sub>/V<sub>lo</sub> on the **real indoor V<sub>mp</sub>** the
`harvest-bench-fixture` measures; (2) pick C1 for a comfortable blink cadence (bigger = slower).
Keep the divider in the 5-20 M range so it draws < ~0.5 uA (well under the IDLE load it must not
swamp).

### A.5 ERC / capture notes

- **Passive board, no driven power net** -> KiCad ERC needs a `PWR_FLAG` on SRC, VCAP, and GND
  (reuse `solarglow:PWR_FLAG`), else "input power pin not driven" errors.
- **U1** is the only part whose exact pin numbers I have not pinned to a datasheet here (proxy
  blocked it) -- capture from the KiCad `MAX931` symbol's named pins (V+, GND, IN+, IN-, REF,
  HYST, OUT) and confirm against the datasheet; wire IN- to REF for the internal-reference
  configuration. (If you prefer, `LTC1540` is a drop-in-equivalent nanopower comp+ref.)
- **Q1** body diode points cap->GND; fine (LED_K is always >= GND). No flyback concern (resistive
  LED load).
- No-connects: U1 HYST pin may be left open if you use the external R3 hysteresis shown (or tie
  per the datasheet if you use the internal HYST resistor instead -- pick one path).
- Single-sided: all of the above on top; back is copper/vias only (section 8).
