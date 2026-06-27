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
| `lis2dh12.h/.c` | accelerometer: presence, tap→INT1, motion (IA2)→INT2, latch clear. |
| `led.h/.c` | TCA0 split-mode PWM on PA0–PA3 + gamma breathing animation. |
| `sense.h/.c` | ADC rail/light reads + EEPROM activation counter. |
| `main.c` | init (per hardware doc §7), sleep/wake state machine, ISRs. |
| `Makefile` | build + UPDI flash. |

## Build & flash

### 1. Install the toolchain
- **avr-gcc** (AVR-Dx capable) plus **avr-binutils** / **avr-libc**. A distro
  `avr-gcc` may be too old for AVR-Dx; the reliable option on any OS is Microchip's
  AVR-GCC toolchain build. A distro `avr-gcc` >= ~12 also works **with the DFP**.
  - Debian/Ubuntu: `sudo apt install gcc-avr binutils-avr avr-libc` (check the version).
  - macOS: `brew tap osx-cross/avr && brew install avr-gcc`.
  - Windows: Microchip's AVR-GCC toolchain, or MSYS2.
- A flasher: **avrdude >= 7.0** (has UPDI / `serialupdi`) *or* **pymcuprog**
  (`pip install pymcuprog`, Microchip's UPDI tool).
- The **AVR-Dx DFP** (device family pack): download the `.atpack` (a zip) from
  Microchip's pack server (`packs.download.microchip.com`), or copy it out of an
  MPLAB X install; unzip it and note the path. It supplies the `avr64dd28` device
  header, startup, and linker spec that stock avr-libc may lack.

### 2. Build
```sh
cd firmware
make DFP=/path/to/Microchip/AVR-Dx_DFP/<version>
```
Produces `solar-glow.hex`; the `avr-size` line reports usage (the part has 64 KB
flash / 8 KB RAM, so this firmware leaves room to spare).

### 3. Wire UPDI and power the board
UPDI is a single wire on **pin 23**, broken out to the **TC2030 pad (TC1)** (a
Tag-Connect cable latches hands-free) and header **J1**. Pick a programmer:
- **SerialUPDI** (cheapest): a **3.3 V** USB-serial adapter — `TX -> 4.7 kΩ -> UPDI`,
  `RX -> UPDI` (joined to the same node), `GND -> board GND`; use `PROG=serialupdi`.
  Do **not** use a 5 V adapter — VDD is clamped to 3.47 V.
- **PICkit 4/5, MPLAB SNAP, or Atmel-ICE**: wire UPDI / GND / Vtarget; use
  `PROG=pickit4_updi` (or `snap_updi`), or drive it with pymcuprog / MPLAB.

**Power the target while flashing.** The card runs off the supercap/solar rail, so
a flat card has no power for UPDI. Either let the programmer supply Vtarget
(PICkit/SNAP, or Vcc on the TC2030), put an external supply on VS, or charge the cap
in light first. VDD is the clamped rail (<= 3.47 V), a valid programming voltage.

### 4. Flash
```sh
make flash DFP=/path/to/... PROG=serialupdi PORT=/dev/ttyUSB0
```
Port: Linux `/dev/ttyUSB0` (or `/dev/ttyACM0`), macOS `/dev/cu.usbserial-*`, Windows
`COMx`. avrdude verifies after the write. (pymcuprog equivalent, roughly:
`pymcuprog -d avr64dd28 -t uart -u <port> write -f solar-glow.hex --erase --verify`.)

### 5. Set the fuses (once)
Flashing does not touch fuses. Set them deliberately per the **Fuses** section
below — sampled `BODCFG`, `SYSCFG1.MVSYSCFG = SINGLE`, and optionally
`SYSCFG0.EESAVE` to keep the tap counter across reflashes. `make fuses` prints the
avrdude pattern; fill in the bytes from the datasheet fuse tables.

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
| 20 | PF0 | INT2 | accel motion in (rising) |
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

- **Tap** (LIS2DH12 click, all axes, high-pass filtered) → INT1 → PF1 → full
  breathing glow (`GLOW_CYCLES` breaths) + EEPROM activation count++. With
  `USE_DOUBLE_TAP`, a double-tap plays a brighter/longer signature glow instead.
- **Motion** (LIS2DH12 inertial wake-up, IA2) → INT2 → PF0 → one softer breath.
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

- **The accelerometer sets the sleep floor, and it runs at 100 Hz on purpose.**
  A click-armed LIS2DH12 has to sample fast enough to *time* a tap, so it runs
  **LP, 100 Hz** (`CTRL_REG1 = 0x5F`) = **~10 µA** (datasheet Table 12: 100 Hz
  LP = 10 µA, 50 Hz = 6 µA, 10 Hz = 3 µA). That ~10 µA dominates the MCU's ~1 µA
  power-down draw, so the accel ODR is the single biggest lever on dark-survival.
  We deliberately do **not** use the sleep-to-wake "activity" function, which
  auto-drops the ODR to 10 Hz when the card is still: the card is *still* exactly
  when a tap arrives, the click engine cannot time a tap at 10 Hz, so a cold tap
  from rest would land as generic motion rather than a click and double-tap would
  be unreachable. Motion / "picked up" is instead sourced from the **IA2 inertial-
  wake generator** (gravity high-passed), which runs alongside the click engine at
  100 Hz. Cost of staying at 100 Hz is roughly the extra ~7 µA vs a 10 Hz idle —
  it about halves dark-survival (order of half a day either way), and any lit use
  the solar harvest covers. See *What to tune → Motion* for the alternative if you
  would rather trade reliable cold-tap for runtime.
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
tunables below as starting points until that measurement lands.

The ADC reference is now run **on demand** so it cannot add standing current:
`sense_adc_init` selects the internal 2.500 V reference **without** `ALWAYSON`
and leaves the ADC **disabled**, and every read enables the ADC, converts, then
disables it again. The datasheet guarantees no ADC current with `ENABLE = 0`,
and the reference is released with it. Because the reference cold-starts on each
read, an initialization delay (`ADC0.CTRLD` `INITDLY = DLY128`, 256 µs at
CLK_ADC = 500 kHz) precedes the sample to cover VREF start-up; that is sized
conservatively — start-up is ~10 µs on this board's high-frequency clock, and the
200 µs datasheet figure is the 32 kHz-clock case, which does not apply — and the
delay costs a fraction of a nanoamp averaged over the 1 s poll. So the
sleep-current question the old design flagged is **closed in code**; the bench
run now just *confirms* it (expect the analog domain to be a rounding error,
~1 µA total in power-down) rather than deciding whether there is a bug to gate.

## What to tune (all in `board.h` unless noted)

Starting points, not gospel. The energy-budget bench run fixes the real power
numbers, and the accel thresholds want a real tap on the *assembled* card — the
Ti back-plate changes how a tap and vibration couple into the sensor.

### LED glow (`board.h`; animation in `led.c`)
- **`GLOW_PEAK`** (0–255, default 220): peak LED duty for a normal tap. The 150 Ω
  ballast fixes the *peak current* on the clamped rail; duty only trims the
  average, so this is brightness/energy and can't exceed the ballasted ceiling.
  It is **pre-gamma**: the animation runs `gamma2(v) = v²/256`, so 220 lands at a
  189 actual peak duty (and even 255 maps to 254). Lower it to stretch the budget.
- **`GLOW_BREATH_MS`** (1600) **/ `GLOW_CYCLES`** (2): breath duration and breaths
  per tap.
- **LED PWM polarity** (`led_init`): the LED pins use pad **INVEN**. It is
  analyzed-correct for a low-side LED on TCA split mode (which down-counts),
  giving larger duty = brighter, and it is **load-bearing for the dark idle
  state** — at duty 0 the pad parks HIGH so the LED is off. Do **not** remove
  INVEN to "fix" an apparent inversion; that lights every LED at rest. If
  brightness ever runs backwards, write `255 - duty` in `led_set`/`led_set_all`
  instead, which keeps idle dark.

### Tap / single-click (`lis2dh12.h`)
- **`LIS_CLICK_THS_RAW`** (`0x30` ≈ 0.75 g; 16 mg/LSb at ±2 g): tap sensitivity,
  lower = more sensitive. The single most likely knob to need a real-hardware
  tweak.
- **`LIS_TIME_LIMIT_VAL` / `LIS_TIME_LATENCY_VAL` / `LIS_TIME_WINDOW_VAL`**
  (100 / 50 / 100 ms; 10 ms per LSb at 100 Hz): click timing — max over-threshold
  dwell still counted as a click, post-click dead time, and the second-tap window.
  Read the double-tap coupling below before changing `TIME_WINDOW`.
- **`LIS_CLICK_CFG_VAL`** is selected automatically from `USE_DOUBLE_TAP`
  (`0x15` single-only / `0x3F` single + double) — don't hand-set it.
- ODR / current is **`LIS_CFG_CTRL_REG1`** (`0x5F` = LP 100 Hz). See the accel
  power note above before lowering it: below ~50 Hz the click engine starts
  missing taps, and the sleep-to-wake trap is the whole reason it sits at 100 Hz.

### Double-tap signature (`board.h`)
- **`USE_DOUBLE_TAP`** (0/1, default 1): when on, a double-tap plays a distinct
  brighter/longer signature glow. **Latency cost:** to tell single from double
  before lighting, *every* tap idle-waits `DTAP_WINDOW_MS` before any glow starts,
  so the common single tap gains that much delay. Set 0 for an instant single tap
  with no double-tap.
- **`DTAP_WINDOW_MS`** (300): how long the firmware waits for the second tap. It
  **must stay ≥** the accel's worst-case double-click assertion time
  (`TIME_LIMIT + TIME_LATENCY + TIME_WINDOW` = 100 + 50 + 100 = 250 ms), or a slow
  double registers as a single. Widen this if you widen the accel `TIME_WINDOW`.
- **`DTAP_CYCLES` / `DTAP_BREATH_MS` / `DTAP_PEAK`** (3 / 1600 / 255): the
  signature glow — one more breath and brighter than a single tap.

### Motion / "picked up" wake (`lis2dh12.h`) — IA2 inertial wake-up
- **`LIS_INT2_THS_VAL`** (`0x10` ≈ 0.25 g; 16 mg/LSb at ±2 g): motion threshold
  for the soft breath. Lower if a gentle pickup doesn't wake it, raise if it's
  twitchy.
- **`LIS_INT2_DUR_VAL`** (`0x00` = immediate; ×10 ms at 100 Hz): debounce. Raise a
  few steps if vibration false-triggers, or if sustained motion gives repeated
  breaths.
- **The motion path must stay high-pass filtered** (`LIS_CFG_CTRL_REG2`, value
  `0x06`, sets `HP_IA2`). Without it the static 1 g gravity exceeds the threshold
  and pins INT2 high. The shared HP filter is primed by one `REFERENCE` read at
  init, which assumes the card is roughly **at rest at boot** — true for a cold /
  just-charged start; a reset mid-handling re-primes on the next boot. If that
  ever bites, `HPM = 11` (autoreset-on-interrupt) is the robust alternative, but
  it is shared with the click filter so it's left at `HPM = 00`.

### Light & rail sensing (`board.h`; ADC in `sense.c`)
- **`VS_GLOW_FLOOR_MV`** (2600): rail floor below which a glow is refused, so an
  animation can't brown the part out mid-breath.
- **`WINK_FLOOR_MV`** (3000, set ≥ floor): the power-on wink only fires with this
  much headroom, so a marginal just-charged card can't wink itself back under the
  floor.
- **`LIGHT_THRESH_MV`** (400): dark→light trip at the VSENSE pin (≈ VIN/2).
- **`POLL_PERIOD_S`** (1 or 2; other values are a compile `#error`): RTC PIT poll
  period. 2 s halves the poll's standby cost for slower dark→light response.
- **ADC internals** (`sense.c`): the reference runs **on demand** (no `ALWAYSON`,
  ADC disabled between polls), with **`INITDLY = DLY128`** (256 µs) covering VREF
  start-up and **`SAMPCTRL = 31`** giving a long sample window for the ~500 kΩ
  divider source impedance. Do **not** re-enable `ALWAYSON` (standing current in
  sleep). If you change CLK_ADC, re-check `INITDLY ≥ tVREF_ST` and keep the long
  sample length.
- **EEPROM counter** (`sense.c`) rewrites the same 4-byte cell every tap; only a
  concern past ~100 k lifetime taps, where you'd rotate the cell address.

### System (`board.h` / `main.c`)
- **`USE_WDT`** (0/1, default 1): the watchdog (see Robustness below).
- **Core clock** is 1 MHz OSCHF (`clocks_init`, see Robustness for the why and the
  knock-ons). Note VREF start-up time — and therefore the `INITDLY` sizing above —
  depends on this being the high-frequency clock, not a 32 kHz main clock.

## Robustness / hardening

- **Watchdog (`USE_WDT`, on by default).** An ~8 s WDT (runs in every sleep mode
  off the ULP oscillator) recovers the card from an unexpected lockup. It is
  petted from the **main-loop top** and from **inside `led_breathe`** (~1 ms
  cadence), never from an ISR — petting from an ISR would mask a wedged main
  loop, which is exactly the failure to catch. The PIT wakes the loop every
  `POLL_PERIOD_S`, so power-down sleep never trips it. The timeout must stay well
  above both the poll period and the longest glow (`GLOW_CYCLES * GLOW_BREATH_MS`);
  at the 8 s setting and the defaults there is wide margin.
- **All hardware waits are bounded.** The I2C paths break on bus timeout /
  arbitration loss (a dead or shorted accel cannot wedge boot), and the ADC
  conversion wait is bounded and returns 0 (reads as low-rail / dark, fails safe)
  if a conversion never completes. After these, the only remaining spin is the
  internal RTC sync at cold boot, which clears in a few cycles.
- **`twi_read` reports faults distinctly.** It returns a status byte separate
  from the data, so a real `0xFF` register value is never confused with a bus
  error (the read helpers all propagate the fault up to the caller).
- **Glow sips, doesn't spin.** During a breath the core IDLE-sleeps between
  1 ms PWM updates (TCA keeps the PWM running in idle) instead of busy-waiting.
  The saving is modest — IDLE gates only the core clock; the oscillator, TCA, and
  especially the LEDs keep drawing — so call it ~5% of glow energy, to be
  confirmed on the bench.
- **Core runs at 1 MHz (`clocks_init`), on purpose.** Once the core sleeps
  through the glow it is only active in brief bursts (a few ~350 µs ADC polls plus
  the one-time boot config), so a slower clock trims the per-burst active current
  for no behaviour cost here. The knock-ons were handled so nothing actually
  changes functionally: I2C is held at 100 kHz via `MBAUD = 0` (the divider floor
  at this clock, so 100 kHz is also the ceiling — 400 kHz fast-mode is unavailable
  below ~4 MHz CLK_PER); the ADC prescaler is `DIV2` so CLK_ADC = 500 kHz stays in
  the 0.5–8 µs-period spec (conversions are ~2x longer in wall-time, still well
  inside the bounded ADC wait); PWM drops to ~3.9 kHz, still flicker-free with no
  audible source on the board; the TCB 1 ms tick and all `_delay`-free timing are
  derived from `F_CPU`, so they track automatically. The RTC PIT and the watchdog
  run off their own low-power oscillators and are unaffected. The absolute energy
  saved is small (the active windows are tiny), but it is free given the above, so
  it is taken deliberately rather than chasing 4 MHz headroom this design never uses.

## Fuses (set at flash time, not by firmware)

Fuses are configuration bytes the **programmer** writes during flashing; the
running firmware can read them but can't change them. Set these deliberately —
the `fuses` Makefile target is a stub, fill in the bytes from the datasheet fuse
tables:

- **`BODCFG` — brown-out (the main one).** `sense_rail_ok()` is only a *software*
  floor checked before each glow; for a hardware guard against the rail collapsing
  mid-operation, enable BOD as a **sampled** brown-out: `ACTIVE = SAMPLE`,
  `SLEEP = SAMPLE`, `SAMPFREQ = 32 Hz` (lower current), `LVL` = a level below the
  3.47 V rail (pick from the BOD level table). Continuous BOD (`ENABLE`) is ~17 µA,
  far too heavy for this rail; sampled costs a small fraction of that.
- **`SYSCFG1.MVSYSCFG` — MVIO.** Set to **SINGLE** (factory default is DUAL). The
  board ties VDDIO2 to VS, so PORTC runs off the main rail with no separate I/O
  voltage, which is what SINGLE means. (DUAL also works here since VDDIO2 sits at a
  valid voltage, but SINGLE is the correct intent. Note: PORTC ADC/AC inputs would
  *require* SINGLE — this design doesn't use them, VSENSE is on PD2.)
- **`SYSCFG0.EESAVE` — keep the tap counter across reflashes.** A UPDI chip-erase
  (every reflash) wipes EEPROM unless `EESAVE` is set, which skips EEPROM on erase.
  Set it if you want `sense`'s activation counter to survive firmware updates. (A
  *locked* device erases EEPROM regardless; this board isn't locked.)
- **`SYSCFG0.UPDIPINCFG` — leave UPDI alone.** UPDI on pin 23 (TC2030 pad / J1) is
  the only program path; do not repurpose that pin or you lose programming access.
- **`OSCCFG`** can stay at default — the firmware selects the 1 MHz OSCHF clock in
  software (`clocks_init`), so no clock fuse change is needed.
