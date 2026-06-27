# SOLAR-GLOW DRH v2.1 — firmware

Bare-metal C for the AVR64DD28 on the SOLAR-GLOW DRH v2.1 card. The card
harvests light into a supercap tank, sleeps in deep power-down, and lights the
backlit **DRH** monogram with a breathing glow when you tap it (or when it is
carried from dark into light). There is **no button** in v2.1 — the
accelerometer is the actuator.

> Status: verified at the **register level** against the AVR64DD32/28 datasheet
> (DS40002315) and the LIS2DH12 datasheet (DM00091513); the pin map is read
> directly from the committed `.kicad_pcb`; and every `_gc`/`_bm` macro, SFR
> field, struct member, and ISR vector used here was checked against the actual
> Microchip `ioavr64dd28.h` from the current AVR-Dx pack. It was **not
> compile-tested** in the authoring environment (no toolchain+DFP there), so
> build against a real DFP as below before trusting it on hardware.

## Files

| file | what it is |
|------|------------|
| `board.h` | as-built pin/route map + tunables. Single source of truth is the PCB. |
| `twi.h` | header-only blocking I2C host (TWI0), one device. |
| `lis2dh12.h/.c` | accelerometer: presence, tap→INT1, activity→INT2, latch clear. |
| `led.h/.c` | TCA0 split-mode PWM on PA0–PA3 + gamma breathing animation. |
| `sense.h/.c` | ADC rail/light reads + EEPROM activation counter. |
| `main.c` | init (per hardware doc §7), sleep/wake state machine, ISRs. |
| `Makefile` | build + UPDI flash. |

## Build & flash

Needs a modern `avr-gcc` (AVR-Dx capable) and the Microchip **AVR-Dx DFP**:

```sh
make DFP=/path/to/Microchip/AVR-Dx_DFP/<version>
make flash DFP=/path/to/... PROG=serialupdi PORT=/dev/ttyUSB0
```

UPDI lands on pin 23, broken out to the **TC2030 pad (TC1)** and header **J1**.
`serialupdi` (USB-serial + 4.7 kΩ series resistor) or a PICkit/SNAP both work.

## Pin map (read from `solar-glow-drh-v2_1.kicad_pcb`)

AVR64DD28, VQFN-28, on the **back** of the board.

| pin | func | net | role |
|----:|------|-----|------|
| 26 | PA0 | LDRV1 | LED D2, low-side, TCA0 WO0 |
| 27 | PA1 | LDRV2 | LED D3, TCA0 WO1 |
| 28 | PA2 | LDRV3 | LED D4, TCA0 WO2 |
| 1 | PA3 | LDRV4 | LED D5, TCA0 WO3 |
| 8 | PC2 | SDA | TWI0 host (PORTMUX **ALT2**), ext 4.7k → VS |
| 9 | PC3 | SCL | TWI0 host (ALT2), ext 4.7k → VS |
| 10 | VDDIO2 | VS | tied to VS by SJ1; PORTC at rail, MVIO unused |
| 12 | PD2 | VSENSE | light/rail sense: ADC AIN2 + AC0 AINP0 |
| 20 | PF0 | INT2 | accel activity in (rising) |
| 21 | PF1 | INT1 | accel tap in (rising) |
| 23 | UPDI | UPDI | program |
| 18,24 | VDD | VS | clamped rail ≤ 3.47 V |
| 19,25,EP | GND | GND | |

LEDs are **low-side**: each lights when its PA pin pulls LOW, current set by a
150 Ω ballast on the clamped rail (~8 mA peak per LED: amber Vf≈2.25 V over
(3.4−2.25)/150). PWM only trims the
average below that ballasted ceiling. `D1`/`D9` are Schottkys, not LEDs.

Spare/free: PA4, PC0, PC1 (on JP2); PA5 (`BTN`, reserved stub for v3); PA6, PA7,
PD1, PD3–PD7, PF6/RST.

## Behaviour

Baseline = **POWER-DOWN**. Wakes:

- **Tap** (LIS2DH12 single-click, all axes, high-pass filtered) → INT1 → PF1 →
  full breathing glow (`GLOW_CYCLES` breaths) + EEPROM activation count++.
- **Motion** (LIS2DH12 activity) → INT2 → PF0 → one softer breath.
- **PIT tick** (~1 s, RTC off the internal ULP, runs in power-down) → ADC-sample
  the light level; on a dark→light edge, glow.

All PORT pins sense fully asynchronously, so the rising-edge accel interrupts
wake the core from power-down with the peripheral clock stopped (datasheet
§18.3.3.1). Every glow is gated by `sense_rail_ok()`: below `VS_GLOW_FLOOR_MV`
the card stays dark and charges, so an animation can't brown out the part.

### Two hardware gates (not visible to firmware)

1. **SW2**, the master anode switch, is pure hardware. With SW2 **OFF** the LED
   anodes are disconnected and nothing lights regardless of what the firmware
   does. There is no GPIO sense for it; the code just drives PWM. If the board
   is dark, check SW2 first.
2. The **accelerometer is the only actuator** in v2.1. `PA5/BTN` is a routed
   stub for a future revision, not populated.

## Power notes / wake architecture (these correct the hardware doc's §6)

The rail is tiny (clamped ≤ 3.47 V supercap, sub-mA indoor harvest), so standing
current is the whole game, and the wake architecture has to live within it. Two
things here diverge from the hardware doc's §6:

- **Accelerometer idle is ~6 µA, not ~2 µA.** A *click-armed* LIS2DH12 must run
  at ≥ ~50 Hz ODR; datasheet low-power current there is ~6 µA. The ~2 µA figure
  is normal-mode-1 Hz, too slow to detect a tap. We run **LP, 100 Hz** by
  default (`CTRL_REG1 = 0x5F`). Drop to 50 Hz to trim current if the budget is
  tight.
- **There is no AC0 "instant" wake-on-light** (the hardware doc's option A).
  On this part the analog comparator keeps running in Standby with `RUNSTDBY`,
  but its **interrupt and status flags do not update while `CLK_PER` is stopped**
  (datasheet AC `CTRLA.RUNSTDBY` bit description), so an AC interrupt cannot wake
  the core from Standby — and Table 13-4 omits the AC from the Standby/Power-Down
  wake sources entirely. (The AC "Sleep Mode Operation" prose claims otherwise;
  it contradicts the bit description and the wake table, and is not relied on.)
  The original option A would have silently never fired. It is removed.

So wake-on-light is done by the **ADC on the ~1 s PIT poll** (a dark→light rise
drives a glow): deepest Power-Down sleep, dark-tolerant, ~1–2 s latency. Instant
response is not lost — the **accelerometer motion/tap interrupt** wakes the core
immediately from Power-Down (a real, async PORT-pin interrupt, confirmed a
Power-Down wake source), and picking the card up to bring it into the light is
exactly that motion. If a true zero-latency *light* trigger is ever wanted, the
supported path on this silicon is AC0 → Event System → CCL (asynchronous LUT,
`FILTSEL=0`/`EDGEDET=0`) → CCL interrupt, which Table 13-4 does list as a
Standby wake source. That is a v-next exercise, not built here.

**The energy-budget bench measurement is still the project's #1 gate.** It sets
the indoor harvest number and therefore the achievable LED duty; treat the
tunables below as starting points until that measurement lands. When you make
that measurement, confirm sleep current with the ADC configured: `sense_adc_init`
leaves the ADC enabled and selects the internal 2.500 V reference with
`ALWAYSON` set so a periodic sample reads true without re-settling. In
power-down both should be off, but verify it on the meter; if the reference adds
standing current, gate it (clear `ALWAYSON` and add a short settling delay
before each conversion, or disable the ADC between samples).

## What to tune (all in `board.h` unless noted)

- **`GLOW_PEAK`** (0–255): peak LED duty. Ballast fixes peak current; this trims
  the average. Lower it to stretch the energy budget.
- **`GLOW_BREATH_MS` / `GLOW_CYCLES`**: breath speed and count per tap.
- **`VS_GLOW_FLOOR_MV`**: rail floor below which the card refuses to glow.
- **`LIGHT_THRESH_MV`**: dark→light trip point at the VSENSE pin (≈ VIN/2).
- **LED PWM polarity** (`led_init` in `led.c`): the four LED pins use pad
  **INVEN**. This is analyzed-correct for a low-side LED on TCA split mode
  (which down-counts: output cleared at BOTTOM, set on compare match), giving
  larger duty = brighter. INVEN is also **load-bearing for the dark idle
  state**: at duty 0 the WO output is low, so INVEN parks the pad HIGH and the
  LED is off. Do **not** "fix" an apparent inversion by removing INVEN — that
  would also turn every LED ON at rest. If a bench check somehow shows
  brightness running backwards, invert the value instead (write `255 - duty`
  in `led_set`/`led_set_all`), which keeps the idle state dark.
- **Accel sensitivity** (`lis2dh12.h`): `LIS_CLICK_THS_RAW` (~16 mg/LSb at ±2 g;
  lower = more sensitive), `LIS_CLICK_CFG_VAL` (`0x15` single / `0x2A` double /
  `0x3F` both), and `LIS_CFG_CTRL_REG1` ODR vs. current.

## Brown-out

`sense_rail_ok()` is a *software* floor checked before each glow. For a true
hardware guard, enable BOD as a **sampled** brown-out (low duty) via the
`BODCFG` fuse rather than continuous BOD (~17 µA is too heavy for this rail).
See the `fuses` target; pick the level/sample-rate byte from the datasheet
BODCFG table deliberately before flashing.
