# SOLAR-GLOW · DRH — As-Built Hardware & Wiring Reference (v2.1)

**The single source of truth for firmware.** Every line here is taken from the committed
`solar-glow-drh-v2_1.kicad_pcb` / `.kicad_sch` and cross-checked against the
AVR64DD32-28 datasheet (DS40002315), the LIS2DH12 datasheet (DM00091513), and the
SM141K06TF and SCPC parts. Where a register value is given, it is the value the firmware must
write to match what is physically routed.

MCU: **AVR64DD28**, 28-pin VQFN (footprint `solarglow:U1`). It sits on the **back** of the board.

---

## 1. MCU pin map (complete, as routed)

| Pad | Pin | Net | Function | Peripheral / firmware note |
|----:|------|------|----------|----------------------------|
| 26 | **PA0** | `LDRV1` | LED1 (D2) cathode drive | **TCA0 WO0** — low-side sink, 150 Ω ballast |
| 27 | **PA1** | `LDRV2` | LED2 (D3) drive | **TCA0 WO1** |
| 28 | **PA2** | `LDRV3` | LED3 (D4) drive | **TCA0 WO2** |
| 1  | **PA3** | `LDRV4` | LED4 (D5) drive | **TCA0 WO3** |
| 2  | **PA4** | `PA4` | spare GPIO | broken out on JP2.1 |
| 3  | **PA5** | `BTN` | reserved button | GPIO; only routed to a stub (the one DRC `track_dangling`); v3 hook |
| 4  | **PA6** | — | free | unconnected |
| 5  | **PA7** | — | free | unconnected |
| 6  | **PC0** | `PC0` | spare GPIO | broken out on JP2.2 |
| 7  | **PC1** | `PC1` | spare GPIO | broken out on JP2.3 |
| 8  | **PC2** | `SDA` | I²C data | **TWI0 host SDA** via `TWIROUTEA = ALT2`; 4.7 kΩ pull-up to VS |
| 9  | **PC3** | `SCL` | I²C clock | **TWI0 host SCL** via `TWIROUTEA = ALT2`; 4.7 kΩ pull-up to VS |
| 10 | **VDDIO2** | `VDDIO2` | PORTC I/O supply | tied to VS by SJ1 (0 Ω) — see §5 |
| 11 | **PD1** | — | free | unconnected (AIN1) |
| 12 | **PD2** | `VSENSE` | light / rail sense | **AIN2 (ADC)** + **AINP0 (AC0+)** → wake-on-light (§6) |
| 13 | **PD3** | — | free | unconnected (AIN3 / AINN0) |
| 14 | **PD4** | — | free | unconnected (AIN4) |
| 15 | **PD5** | — | free | unconnected (AIN5) |
| 16 | **PD6** | — | free | unconnected (AIN6 / AINP3 / DAC VOUT) |
| 17 | **PD7** | — | free | unconnected (VREFA / AIN7) |
| 18 | **VDD** | `VS` | core supply | the clamped rail, ≤ 3.47 V |
| 19 | **GND** | `GND` | ground | |
| 20 | **PF0** | `INT2` | accel INT2 input | PORTF pin interrupt |
| 21 | **PF1** | `INT1` | accel INT1 input | PORTF pin interrupt |
| 22 | **PF6/RST** | — | free | defaults to RESET; fuse to GPIO if ever needed |
| 23 | **UPDI** | `UPDI` | programming | TC2030 pad (TC1) + backup header J1 |
| 24 | **VDD** | `VS` | core supply | |
| 25 | **GND** | `GND` | ground | |
| EP | — | `GND` | exposed pad | thermal + ground |

**LED ↔ channel map** (note the off-by-one: D1/D9 are Schottkys, not LEDs):
`D2 → LDRV1 → PA0/WO0`, `D3 → LDRV2 → PA1/WO1`, `D4 → LDRV3 → PA2/WO2`, `D5 → LDRV4 → PA3/WO3`.
Each LED: anode → `ANODE` (common) → **SW2** → VS; cathode → `Kn` → ballast (150 Ω) → `LDRVn` → MCU pin.

---

## 2. Nets & rails

| Net | What it is |
|------|-----------|
| `VIN` | PV1 (+) solar node, **before** blocking diode D1. ~0 V in the dark, rises with light. Feeds the VSENSE divider and D1 anode. |
| `VINB` | PV2 (+) solar node, before blocking diode D9. |
| `VS` | The storage rail (after D1/D9). = MCU VDD, accel VDD, LED anode source, supercap top. **Clamped ≤ 3.47 V** by the TLV431+PNP shunt (U4/Q1). |
| `GND` | Ground — inner plane In1, EP, the four M2 mount holes. |
| `MID` | Supercap series midpoint, balanced by U2 (ALD910025 dual SAB). |
| `CLBASE` / `CLREF` | Clamp internals — Q1 base / TLV431 reference divider tap. |
| `ANODE` | Common LED-anode node, switched by SW2. |
| `TINY` | Dim-mode node: LED anodes → VS through R12 (220 Ω) when SW2 = TINY. |
| `LDRV1‒4` | LED cathode drives → MCU PA0‒PA3. |
| `K2‒K5` | Individual LED-cathode-to-ballast nets. |
| `SDA` / `SCL` | I²C bus (accel + JP1 breakout). |
| `INT1` / `INT2` | Accel interrupt lines → PF1 / PF0. |
| `VSENSE` | Light/rail sense → PD2. = VIN/2 (R5/R6 = 1 MΩ each), filtered by C5 (10 nF). |
| `PA4` / `PC0` / `PC1` | Spare GPIO, broken out on JP2. |

Inner copper: **In1 = GND plane, In4 = VS plane**, In2/In3 = signal. (6-layer, 0.8 mm.)

---

## 3. Peripheral setup cheat-sheet (what firmware must configure)

**These are not defaults — they are the settings that match the routing.**

- **LED PWM — TCA0, split mode.**
  Keep `PORTMUX.TCAROUTEA = DEFAULT` (WO0‒WO3 already land on PA0‒PA3). Run TCA0 in
  **split mode** to get six 8-bit channels; WO0‒WO3 are the four LEDs, each with independent
  duty and a shared period. Set PA0‒PA3 as outputs. The 150 Ω ballast fixes the **peak**
  current (~9 mA on the clamped rail); PWM only trims the **average** below that, so brightness
  can be set freely but cannot exceed the ballast ceiling.
  *Gotcha:* the LEDs only light if **SW2 is bridged ON or TINY**. If SW2 = OFF (unbridged),
  no PWM will produce light — that's the hardware master switch.

- **I²C — TWI0, host mode.**
  **`PORTMUX.TWIROUTEA = ALT2`** (puts host SDA/SCL on PC2/PC3 — the default routes to
  PA2/PA3, which are LED pins). External 4.7 kΩ pull-ups are fitted, so don't enable internal
  ones. Bus is the accelerometer plus the JP1 breakout.

- **Accelerometer wake — PORTF pin interrupts.**
  Configure **PF1** (INT1) and **PF0** (INT2) as inputs with edge interrupts to match whatever
  the LIS2DH12 INT pins are programmed to assert (tap, double-tap, activity). These are the
  wake source for tap-to-glow.

- **Light sense / wake-on-light — PD2.**
  PD2 is both **AIN2** (ADC) and **AINP0** (AC0 positive input). See §6 for the validated
  options. The divider is VIN/2, so the ADC reading is `2 × VSENSE` ≈ VIN.

- **Free expansion ADC/analog** (all unconnected, available): PD1 (AIN1), PD3 (AIN3/AINN0),
  PD6 (AIN6/AINP3/DAC out), PD7 (VREFA/AIN7).

---

## 4. Devices on the board

**U3 — LIS2DH12 accelerometer (the actuator).**
- Interface: **I²C** (CS = pin 2 → VS selects I²C mode).
- **Address: `0x18`** 7-bit (SDO/SA0 = pin 3 → GND = address LSB 0). 8-bit: write 0x30 / read 0x31.
- Interrupts: **INT1 (pin 12) → PF1**, **INT2 (pin 11) → PF0**.
- Supply Vdd/Vdd_IO → VS; SCL → PC3, SDA → PC2. Decoupled by C6.
- Role: tap / double-tap / activity → INT → wakes the MCU. A tap is vibration, so the metal
  back-plate transmits it in the enclosed build.

**LEDs — 4× ams OSRAM LA P47F (amber, reverse-mount).** Low-side driven on PA0‒PA3 (§1/§3),
150 Ω ballast each, anodes commoned to `ANODE` and switched by SW2.

**SW2 — LED master selector (3-pad solder bridge).** `ANODE` common; bridge to **VS = ON**
(full), to `TINY` = **TINY** (anodes → VS via R12 220 Ω, dim/long-runtime), unbridged = **OFF**
(true hardware off). Also `SB1‒SB4` are per-LED disable bridges in series with each ballast.

**Breakouts / programming.**
- `TC1` — TC2030 Tag-Connect (UPDI): hands-free flashing. `J1` — backup UPDI header.
- `JP1` — I²C breakout: 1 = SDA, 2 = SCL, 3 = GND.
- `JP2` — GPIO breakout: 1 = PA4, 2 = PC0, 3 = PC1, 4 = GND.

---

## 5. Power & sensing

- **Harvest:** 2× SM141K06TF (Voc 4.15 V, Vmp 3.35 V, Isc 58.6 mA at 1 sun), in parallel,
  each behind its own Schottky — **PV1 → D1 → VS** and **PV2 → D9 → VS** (both MMSD301T1G) —
  so a shadow on one panel can't back-drive the other.
- **Storage:** 4× SCHURTER WS17 (P/N 3-153-438), wired **2P2S → 1 F @ 5.5 V ≈ 15 J**, on one
  node balanced by **U2 (ALD910025)** at the midpoint.
- **Rail clamp:** TLV431 (U4) + PNP (Q1) shunt holds **VS ≤ ~3.47 V** so the accelerometer
  stays inside its 3.6 V max. Divider R7 (1.8 M) / R8 (1 M) sets the trip; it sits on VS.
- **VDDIO2 = VS** via SJ1, so PORTC runs at the rail and **MVIO is unused** (no separate I/O
  voltage, no MVIO fuse to manage). PORTC pins are valid up to VS.
- **Sense:** `VSENSE = VIN / 2` (R5/R6 = 1 MΩ, C5 = 10 nF, ~5 ms filter) into PD2. Reads the
  *solar input*, not the stored rail — see §6.

---

## 6. Wake-on-light — validated, viable as wired (no board change)

Confirmed electrically this revision. The divider sits on **VIN (before D1)**, so VSENSE
collapses to ~0 V in the dark and rises with light; **PD2 = AINP0** is a real AC0 input and
**AIN2** is a real ADC input. Signal swing: ~0 V dark → ~1.2–2.1 V in light (dim-indoor to
sun), against an easily-set threshold near ~0.4 V. AC0 input range is −0.2 V…VDD, so VSENSE
fits. Two implementations, same wiring — choose per use:

**A) AC0 comparator — instant wake.**
- AC0 `MUXPOS = AINP0` (PD2); `MUXNEG = DACREF`; set threshold `DACREF × VREF` ≈ 0.4 V.
- Enable hysteresis (10/25/50 mV) so a flickering source doesn't chatter the interrupt.
- `CTRLA.RUNSTDBY = 1`, sleep in **Standby**; the AC0 CMP interrupt wakes the core the moment
  light appears. Use `CTRLA.POWER = 0x2` (slowest, plenty fast for light) ≈ **~12 µA** standing.
- Dark tolerance: AC0 (~12 µA) + accel (~2 µA) + standby (~3 µA) ≈ ~16 µA against ~4 J usable
  → roughly **a day** of total darkness before the tank is flat.

**B) RTC/PIT poll + ADC — dark-tolerant.**
- Sleep in **Power-Down**; wake every ~1–2 s off the internal-ULP RTC/PIT; ADC-sample PD2
  (AIN2); escalate to full wake only when the reading clears the light threshold.
- Average **~1–3 µA → ~5–7 days** of darkness, at the cost of ~1–2 s detection latency.
- Note: in the deepest Power-Down the AC0 is off, so this is the only wake-on-light that works
  in that mode — and it's the better fit for "card sat in a drawer."

Both recharge instantly when light returns. A reasonable firmware default: run **B** as the
always-on baseline and arm **A** only when the card is in active use and instant response is
wanted.

*Open empirical item:* the indoor VIN figures are estimated from the panel's logarithmic
Voc-vs-illumination behavior; the dark (0 V) and sun (datasheet) endpoints are firm. The
energy-budget bench measurement (still the project's #1 gate) will confirm the indoor middle
and set the achievable duty cycle.

---

## 7. Firmware bring-up order

1. **Clocks/power:** set `VREGCTRL.PMODE = AUTO`; pick the main clock (internal OSC, no crystal
   fitted); plan to sleep aggressively (the rail is tiny).
2. **GPIO/PORTMUX:** `TCAROUTEA = DEFAULT`, `TWIROUTEA = ALT2`; PA0‒PA3 outputs (LEDs),
   PF0/PF1 inputs w/ interrupt (accel), PD2 left to the analog peripheral.
3. **I²C up, talk to the accel** at `0x18`; configure tap/activity → INT1/INT2; verify the
   PF1/PF0 interrupts fire on a physical tap.
4. **TCA0 split-mode PWM** on the LEDs; **confirm SW2 is ON/TINY** or nothing lights.
5. **Wake-on-light** (§6) — bring up option B first (simplest, deepest sleep), then A if instant
   wake is wanted.
6. **Housekeeping:** ADC read of VSENSE (×2 = VIN) and VDD/10 for charge state; optional EEPROM
   activation counter; brown-out behavior around the supercap rail.

**Pins free for new features:** PA6, PA7, PD1, PD3, PD4, PD5, PD6, PD7, PF6/RST (9 GPIO, most
ADC-capable; PD6 can be a DAC output), plus PA4/PC0/PC1 already on JP2 and PA5 (`BTN`) reserved.
