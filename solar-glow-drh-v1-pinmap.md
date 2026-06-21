# SOLAR-GLOW · DRH — v1 MCU pin map (proposed)

**MCU:** AVR64DD28, **VQFN28** (4×4). Pinout + mux verified against
`AVR64DD32-28-Complete-DataSheet-DS40002315.pdf` (Rev C), §2.3 pinout + §3.1 I/O multiplexing.
Pin numbers below are the **VQFN28** column. (SSOP28 numbering differs — noted only if we revert package.)

## Power / fixed
| VQFN28 | Pin | Net | Note |
|---|---|---|---|
| 18, 24 | VDD ×2 | **VS** | both decoupled (C1, Cx) |
| 19, 25 | GND ×2 | **GND** | + **EP = GND** (reflow to plane) |
| 10 | VDDIO2 | **VS** (baseline) | PORTC supply; see MVIO note |
| 23 | PF7 | **UPDI** | → TC1, J1 |
| 22 | PF6 | **RESET** | input-only; internal pull-up, optional ext RC |

## Functional assignment
| VQFN28 | Pin | Function | Net |
|---|---|---|---|
| 26 | PA0 | TCA0 WO0 | LED1 drive → R1 → D2(K) |
| 27 | PA1 | TCA0 WO1 | LED2 drive → R2 → D3(K) |
| 28 | PA2 | TCA0 WO2 | LED3 drive → R3 → D4(K) |
| 1 | PA3 | TCA0 WO3 | LED4 drive → R4 → D5(K) |
| 3 | PA5 | ADC0 AIN25 | **VSENSE** — VIN÷2 light-sense divider |
| 5 | PA7 | digital in | **BTN** — snap-dome SW1 |
| 8 | PC2 | TWI0 SDA(H), alt | **SDA** → JP1 (+ future accel) |
| 9 | PC3 | TWI0 SCL(H), alt | **SCL** → JP1 (+ future accel) |

## Spare / uncommitted (headroom for §2/§3/§4)
PA4 (AIN24), PA6, **PC0/PC1** (MVIO, AIN28/29), **PD1–PD7** (AIN1–7; PD6 has DAC VOUT, PD7 has VREFA),
PF0/PF1 (AIN16/17). Bring 2–3 out as a breakout if wanted.

## Key decisions (confirm before I wire the netlist)
1. **4 LEDs on TCA0 split, WO0–WO3 = PA0–PA3.** Independent duty per LED, shared period (fine for
   synchronized breathing). Mirrors v0's TCA0 usage. *Alt:* TCD0 WOA–WOD = PA4–PA7 for tighter
   4-output coordination, at the cost of more complex setup. Pick one.
2. **I²C (TWI0) on PC2/PC3 = the PORTC/MVIO host position.** Frees PA2/PA3 for the LEDs **and** is the
   exact rail the future 3.0 V accel wants — no level shifter (the §3/§7 MVIO payoff). Brought out to
   JP1 now; accel is a gated v2 populate.
3. **VDDIO2 → VS in the baseline** (PORTC runs at VS, no MVIO benefit yet). Populating the accel later
   means feeding VDDIO2 from a 3.0 V LDO instead — that's the v2 rework, consistent with §3 being
   gated. *Option:* a VS→VDDIO2 solder-jumper + LDO pad now, so v2 needs no trace cut.
4. **Low-side LED drive** (VS → D(A→K) → R(ballast) → MCU pin), same as v0. Pins sink ~1.25 mA each.
5. **VSENSE on PA5/AIN25** (mirrors v0's PA5 intent). Divider is MΩ-class 2×0402, sub-µA bleed.

## Still needs a call (not MCU pins)
- **SW2 (3-pos OFF/ON/TINY):** sits in the LED **return path**, not on a GPIO. Need its exact net
  wiring (what TINY selects) before the LED section closes.
- **RESET (PF6):** leave as RESET w/ internal pull-up (recommended), or fuse to GPIO for a spare.

No AVDD on the 28-pin — ADC runs off VDD, so analog cleanliness rides on the VS plane + decoupling.
