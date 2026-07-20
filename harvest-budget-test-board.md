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
- **Take it to KiCad:** say the word and I'll draft the schematic (reusing the `solarglow` panel
  footprint and the retired Schottky land) as a starting point for your layout.
