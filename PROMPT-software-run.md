# SOLAR-GLOW · DRH v2.1 — Firmware Run

You are picking up the **firmware** for SOLAR-GLOW DRH v2.1, a solar-powered glowing
business-card PCB. The hardware is built and frozen; this session writes the firmware that
brings it to life.

Treat the committed files in the repo (https://github.com/devinhorowitz/solar-business-card)
as the **single source of truth**. Do not rely on any prior conversation, memory, or
training-data assumption about this board — if a fact isn't in the docs or confirmable from the
schematic / datasheet, verify it or ask before you code it.

## What the card does

A credit-card-sized PCB that harvests indoor/outdoor light into a supercapacitor bank and glows
a backlit "DRH" monogram. It wakes on a tap (accelerometer) or on light, runs an LED animation
(breathing / dim) inside a tiny energy budget, and sleeps aggressively the rest of the time.
There is no button — the actuator is the accelerometer tap.

## Read these first (in order)

1. **`solar-glow-drh-v2-hardware.md`** — THE firmware target. The complete as-built pin map,
   nets/rails, the peripheral config that matches the routing (TCA0 split-mode for the LEDs with
   `TCAROUTEA = DEFAULT`; I²C host with `TWIROUTEA = ALT2`; accel INT1/INT2 on PF1/PF0; light
   sense on PD2), the device list (LIS2DH12 accelerometer at I²C address `0x18`), the validated
   wake-on-light recipe (§6), and a step-by-step bring-up order (§7). Start here and follow §7.
2. **`README.md`** — product overview and feature intent.
3. **`solar-glow-drh-design-notes.md`** — the power-budget model (continuous average draw ≤
   harvest; the ~15 J reserve buys *excursions*, not steady-state), firmware ideas worth using
   (CCL + EVSYS to run a glow pattern while the CPU sleeps; RTC/PIT off the internal 32 kHz ULP;
   an EEPROM activation counter), and the **ballast caveat** — the LED-draw numbers depend on the
   final ballast value, so re-derive the achievable duty against it.
4. **Register reference:** `datasheets/AVR64DD32-28-Complete-DataSheet-DS40002315.pdf` (MCU,
   AVR64DD28) and `datasheets/en.DM00091513.pdf` (LIS2DH12).
5. **`solar-glow-drh-v2_1.kicad_sch` / `.kicad_pcb`** — open only to confirm a specific
   connection; the hardware doc already distills them.

## Hard rules

- **Verify, don't invent.** Never guess a register value, pin assignment, or peripheral route.
  The hardware doc gives the exact PORTMUX / register values the physical routing requires; the
  datasheet gives the rest. If something isn't pinned down, confirm against the schematic or ask.
- **Power is the constraint.** The rail is a clamped supercap (≤ 3.47 V) and indoor harvest is
  sub-milliamp. Sleep aggressively (`VREGCTRL.PMODE = AUTO`), minimize active time, and keep the
  LEDs (the only mA-scale load) duty-limited. Re-derive LED duty against the final ballast.
- **Two hardware gates to respect.** The LEDs light only if SW2 is bridged ON or TINY — a
  hardware master switch, so no PWM produces light when SW2 = OFF. The actuator is the
  accelerometer tap; there is no button input.
- **MVIO is unused** (VDDIO2 is tied to VS), so PORTC runs at the rail — no MVIO fuse to manage.

## Assumed approach (redirect me if you'd rather)

Bare-metal, register-level **C** with **avr-gcc / avr-libc** and the AVR-Dx device pack, flashed
via **UPDI** through the TC2030 pad (TC1) or the J1 header. If you want MPLAB X / XC8, MCC /
Melody, or a different structure, say so before I start.

## Deliverables (follow the bring-up order in the hardware doc, §7)

1. **Clock + power init:** `PMODE = AUTO`, internal oscillator (no crystal fitted), the sleep
   strategy.
2. **GPIO / PORTMUX:** `TCAROUTEA = DEFAULT`, `TWIROUTEA = ALT2`; PA0–PA3 LED outputs; PF0/PF1
   accel-interrupt inputs; PD2 to the analog peripheral.
3. **I²C + LIS2DH12 driver** at `0x18`: configure tap / double-tap / activity → INT1/INT2; verify
   the PF1/PF0 interrupts fire on a physical tap.
4. **TCA0 split-mode LED PWM:** the glow animation (breathing / dim), respecting the SW2 gate and
   the ballast-limited peak current.
5. **Wake-on-light** (hardware doc, §6): RTC/PIT-poll baseline (option B), AC0 instant-wake
   (option A) as an arm-on-demand mode.
6. **Housekeeping:** ADC read of VSENSE (×2 = VIN) and VDD/10 for charge state; optional EEPROM
   activation counter; brown-out behavior at the supercap rail.

Work in the project's style: terse, answer-first, engineer-to-engineer; lead with the
code/decision; verify facts against the datasheet before asserting them.
