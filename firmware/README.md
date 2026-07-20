# SOLAR-GLOW DRH - firmware (targets the v4.0 card)

Bare-metal C for the AVR64DD28 on the SOLAR-GLOW DRH v4.0 card. The card
harvests light into a supercap tank, sleeps in deep power-down, and lights the
backlit **DRH** monogram with a breathing glow when you tap it (or when it is
carried from dark into light). There is **no button** on this card — the
accelerometer is the actuator.

The board carries an NFC tag (`U5`, NXP NT3H2211, added in v2.2): a phone tap reads a
contact **vCard** from it, and the tag's field-detect line also wakes the glow.
The tag's VCC is **power-gated** by a load switch on `NFC_EN` (PA7) and held off
by default — the chip has no sleep state and would otherwise draw ~195 µA, the
card's largest idle load. See **NFC contact card** below.

> Status: verified at the **register level** against the AVR64DD32/28 datasheet
> (DS40002315) and the ADXL367 datasheet; the pin map is read
> directly from the committed `.kicad_pcb`; and every `_gc`/`_bm` macro, SFR
> field, struct member, and ISR vector used here was checked against the actual
> Microchip `ioavr64dd28.h` from the current AVR-Dx pack. It was **not
> compile-tested** in the authoring environment (no toolchain+DFP there), so
> build against a real DFP as below before trusting it on hardware.
>
> The **NFC** firmware is verified against the NTAG I2C plus datasheet
> (NT3H2111_2211 Rev 3.6), and the whole front-end is on the committed
> `solar-glow-drh-v4_0.kicad_pcb`, verified from its copper: tag `U5`, the `U6`
> (TPS22918) VCC load switch, `R14` and `C8` are placed and wired as this
> firmware assumes — FD→PA6, NFC_EN→PA7→`U6` enable, `U6` gating VS→the switched
> tag rail (`VNFC`), the internal PA6 pull-up holding FD to **VS**, `R14` (1 M) holding NFC_EN low.
> What still needs the bench is electrical, not wiring: that FD swings to a valid
> logic-low on field power with VCC gated off, the phone NDEF read, and the `C9` tune.

## Files

| file | what it is |
|------|------------|
| `board.h` | as-built pin/route map + tunables. Single source of truth is the PCB. |
| `twi.h` | header-only blocking I2C host (TWI0); shared by the accel and NFC tag. |
| `adxl367.h/.c` | accelerometer: presence, tap→INT1, activity→INT2, tap/activity clear. |
| `nfc.h/.c` | NT3H2211 NFC tag (`U5`): NDEF write + VCC power-gate via `NFC_EN`/`U6`. |
| `fram.h/.c` | MB85RC512TY FRAM (`U7`, 64 KB I2C @ 0x50): power/present + 16-bit linear read/write. Shares `VNFC`/`NFC_EN` with the tag; headless by default (`USE_FRAM_LOG`=0). |
| `led.h/.c` | TCA0 split-mode PWM on PA0–PA3 + gamma breathing glow + in-sun loading sweep. |
| `sense.h/.c` | ADC rail/light/temp reads, rail-scaled glow (brownout stretch), EEPROM telemetry: activation counter + sun diary + max-temp log + black box (min-rail, power-cycles). |
| `main.c` | init (per hardware doc §7), sleep/wake state machine, ISRs. |
| `Makefile` | build + UPDI flash. |

## Build & flash

### 1. Install the toolchain
- **avr-gcc with AVR-Dx/DD support**, plus **avr-binutils** / **avr-libc**. The test
  is DD support, not a version number: Microchip's AVR-GCC toolchain is the safe
  cross-platform pick, and a distro `gcc-avr` that is Atmel/Microchip-patched also
  recognizes the DD parts (Ubuntu's `gcc-avr` 7.3.0+Atmel does — verified). A
  *mainline* (unpatched) avr-gcc needs >= 12. It finds the device through the DFP's
  specs either way.
  - Debian/Ubuntu: `sudo apt install gcc-avr binutils-avr avr-libc avrdude` — the
    packaged `gcc-avr` already knows `avr64dd28`; add the DFP (below) for specs/headers.
  - macOS: `brew tap osx-cross/avr && brew install avr-gcc avrdude`.
  - Windows: Microchip's AVR-GCC toolchain, or MSYS2.
  - If `make` reports an *unknown MCU* (rather than just a missing `specs-avr64dd28`
    file, which the DFP supplies), that avr-gcc lacks DD support — use Microchip's.
- A flasher: **avrdude >= 7.1** (its `avrdude.conf` ships the AVR-DD parts and the
  `serialupdi` programmer — verified; stock Ubuntu 7.1 works) *or* **pymcuprog**
  (`pip install pymcuprog`, Microchip's UPDI tool). This guide drives the
  **Adafruit UPDI Friend** (step 3); its CH340E enumerates as a USB serial port
  (built into modern Linux; macOS/Windows may want WCH's CH340 driver).
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
Tag-Connect cable latches hands-free) and the backup header **J1**.

This guide uses the **[Adafruit UPDI Friend](https://www.digikey.com/en/products/detail/adafruit-industries-llc/5879/22596413)**
(DigiKey 5879) — a USB-C serial-UPDI programmer with the loop-back resistor *and* a
switchable **3 V / 5 V** supply built in, so there's no resistor to wire and it can
power the card itself. Its 3-pin JST-SH cable is colour-coded **white = UPDI**,
**black = GND**, **red = PWR** (same three signals on the 0.1" header).

1. **Set the voltage switch to 3 V.** VS is the LDO's regulated 3.3 V rail (U9 TPS7A0233), so 3 V power and
   logic are safe; **never 5 V** - it over-drives the UPDI pin and exceeds the 3.3 V parts.
2. Wire by signal to TC1 (or J1): **white/UPDI → UPDI**, **black/GND → GND**, and
   **red/PWR → the connector's Vcc pin** (it sits on VS). Confirm the TC1/J1 pin
   order against the schematic — a 3-contact UPDI Tag-Connect carries UPDI, GND, Vcc.
3. On 3 V the UPDI Friend's supply (up to 500 mA) powers the card for programming —
   which matters because a flat solar card has no power of its own for UPDI. If your
   connector doesn't break out Vcc, charge the cap in light first and wire only
   UPDI + GND (still on the 3 V setting, so the logic level matches).
4. Plug in USB-C; the green PWR LED lights and the red TX LED blinks on transfers.

Other serial-UPDI adapters, or a PICkit 4/5 / MPLAB SNAP, also work
(`PROG=serialupdi` or `PROG=pickit4_updi` / `snap_updi`); a bare USB-serial adapter
would need a 4.7 kΩ resistor between TX and the joined RX/UPDI node — exactly what the
UPDI Friend builds in. We leave `UPDIPINCFG` at default (UPDI stays active on pin 23),
so the standard (non-HV) UPDI Friend is the right one — the High-Voltage variant is
only needed if UPDI has been fused off.

Refs: [UPDI Friend guide](https://learn.adafruit.com/adafruit-updi-friend) ·
[what UPDI is (Microchip)](https://onlinedocs.microchip.com/oxy/GUID-DDB0017E-84E3-4E77-AAE9-7AC4290E5E8B-en-US-4/index.html).

### 4. Flash
```sh
make flash DFP=/path/to/... PROG=serialupdi PORT=/dev/ttyUSB0
```
Find the port after plugging in the UPDI Friend: Linux `ls /dev/ttyUSB*` (the CH340E
shows as `ttyUSB0`, occasionally `ttyACM0`), macOS `ls /dev/cu.usbserial-*`, Windows =
the new `COMx` in Device Manager. The Makefile sends `-b 230400` (the UPDI Friend's
documented speed; override with `BAUD=57600` if a long cable is flaky), and avrdude
verifies after the write. On Linux, a *Permission denied* on the port means you need
serial access: add yourself to the `dialout` group (`sudo usermod -aG dialout $USER`,
then log out/in) or run the command with `sudo`. (pymcuprog equivalent, verified flags:
`pymcuprog -d avr64dd28 -t uart -u <port> -c 230400 write -f solar-glow.hex --erase
--verify`.)

### 5. Set the fuses (once)
Flashing does not touch fuses. Set them deliberately per the **Fuses** section
below — sampled `BODCFG`, `SYSCFG1.MVSYSCFG = SINGLE`, and optionally
`SYSCFG0.EESAVE` to keep the tap counter across reflashes. `make fuses` prints the
avrdude pattern; fill in the bytes from the datasheet fuse tables.

> **v3.0 LED pin map — the one firmware-facing change.** v3.0 permuted the LDRV nets at U1 (the fan
> untangle) so the schematic matches the as-routed copper: **pin 1/PA3/WO3 = LDRV1 → D2; pin 28/PA2/WO2
> = LDRV2 → D3; pin 27/PA1/WO1 = LDRV3 → D4; pin 26/PA0/WO0 = LDRV4 → D5** (v2.3 was the reverse at the
> U1 end). The table below is the v3.0 map, and `led.c`'s channel table must match it. TCA0 split on
> PA0–PA3 and the LED placements (D2–D5) are unchanged. (The PWM `INVEN` polarity in `led.c` is a
> carried bench item — a one-line fix if the glow reads inverted.)

## Pin map (read from `solar-glow-drh-v4_0.kicad_pcb`)

AVR64DD28, VQFN-28, on the **back** of the board.

| pin | func | net | role |
|----:|------|-----|------|
| 26 | PA0 | LDRV4 | LED D5, low-side, TCA0 WO0 |
| 27 | PA1 | LDRV3 | LED D4, TCA0 WO1 |
| 28 | PA2 | LDRV2 | LED D3, TCA0 WO2 |
| 1 | PA3 | LDRV1 | LED D2, TCA0 WO3 |
| 2 | PA4 | EN_STO_CH | AEM10300 charge gate, open-drain, LOW = disable charge during NFC read |
| 4 | PA6 | FD | NFC field-detect in (`U5`); PORTA pin int, **both edges**; field-powered (works VCC-off); int pull-up on (sole FD pull-up; no external FD resistor) |
| 5 | PA7 | NFC_EN | Enables the NFC VCC load switch (`U6`, TPS22918), **active-HIGH**; init LOW = NFC off. (`R14`, 1 M, holds `U6` off while PA7 tristates during reset/UPDI/brown-out -- at (5.35, 4.92) on the board. Firmware also drives PA7 low-before-output and low-before-sleep, so the window is covered both ends.) |
| 8 | PC2 | SDA | TWI0 host (PORTMUX **ALT2**), ext 4.7k → VS |
| 9 | PC3 | SCL | TWI0 host (ALT2), ext 4.7k → VS |
| 10 | VDDIO2 | VS | tied to VS by SJ1; PORTC at rail, MVIO unused |
| 11 | PD1 | STO_SNS | supercap sense: STO/3 (R15/R16) into ADC AIN1 |
| 12 | PD2 | VSENSE | light/rail sense: ADC AIN2 + AC0 AINP0 |
| 20 | PF0 | INT1 | accel tap in (rising) |
| 21 | PF1 | INT2 | accel motion in (rising) |
| 23 | UPDI | UPDI | program |
| 18,24 | VDD | VS | regulated 3.3 V LDO output (U9 TPS7A0233) |
| 19,25,EP | GND | GND | |

LEDs are **low-side**: each lights when its PA pin pulls LOW, current set by a
150 Ω cathode ballast off the STO supercap tank (~16 mA peak per LED: amber Vf≈2.25 V over
(4.65−2.25)/150, STO topping at the AEM10300 VOVCH of 4.65 V). PWM only trims the
average below that ballasted ceiling. The only D-parts on the v4 board are the LEDs D2–D5.

Spare/free: PC0, PC1 (on JP2); PA5 (`BTN`, reserved stub);
PD3–PD7, PF6/RST. (PA6 = NFC `FD`, PA7 = `NFC_EN`.) All of these unused pins
get internal pull-ups in `gpio_init` so a floating input can't leak current — see
*Power notes*.

## Behaviour

Baseline = **POWER-DOWN**. Wakes:

- **Tap** (ADXL367 tap, Z-axis, single+double resolved in hardware) → INT1 → PF0 → full
  breathing glow (`GLOW_CYCLES` breaths) + EEPROM activation count++. With
  `USE_DOUBLE_TAP`, a double-tap plays a brighter/longer signature glow instead.
- **Motion** (ADXL367 referenced activity) → INT2 → PF1 → one softer breath — **muted when the
  card is in the dark** (`USE_DARK_MOTION_MUTE`), so a card jostling in a pocket can't bleed the
  reserve on repeated motion breaths; a deliberate tap still glows.
- **NFC** (NT3H2211 field detect, `U5`) → FD → PA6 → LEDs held dark during the read
  (clean 13.56 MHz for the tag reply), acknowledge glow when the field leaves. FD runs
  on the reader's field power (datasheet §8.4), so it works even though the tag's VCC is
  gated **off**; field-present is the chip's
  POR default (`NC_REG.FD_ON = 00b`), so no setup is needed. Detail under **NFC
  contact card** below.
- **PIT tick** (~1 s, RTC off the internal ULP, runs in power-down) → ADC-sample
  the light level; on a dark→light edge, glow. In **strong sun with the caps full**
  it instead plays the in-sun "loading" sweep (`USE_SUN_SWEEP`; see *What to tune*) —
  free solar spent as light, and gated so it can never drain the pack. The same poll
  banks **sun-hours** to EEPROM whenever the strong-sun tell is set (`USE_SUN_DIARY`),
  so the card keeps a lifetime tally of the light it has lived in.

All PORT pins sense fully asynchronously, so the rising-edge accel interrupts and
the falling-edge FD interrupt wake the core from power-down with the peripheral
clock stopped (datasheet §18.3.3.1). Every glow is gated on the rail (`sense_glow_peak()`):
below `VS_GLOW_FLOOR_MV` the card stays dark and charges, and with `USE_BROWNOUT_STRETCH`
the breath *fades* toward the floor rather than cutting off at it — so an animation can't
brown out the part, and a low reserve degrades gracefully instead of hitting a cliff.

**Face-down dormant** (`USE_FACEDOWN_DORMANT`). If the card lies face-down (accel Z clearly
negative) for `FACEDOWN_DORMANT_S` (~3 min), it goes dormant and suppresses *every* glow —
tap, motion, NFC-ack, greeting, sweep — until it is turned face-up again, so a stowed card
(face-down in a drawer, under papers) can't bleed the reserve on false triggers. Flipping it
face-up wakes it at once (the flip is motion; the ~1 s poll re-checks orientation as a
backstop). The passive RF vCard read is unaffected (it's hardware). Net energy win — the only
cost is one accel Z read per poll.

### Two hardware gates (not visible to firmware)

1. **SW2**, the master anode switch, is pure hardware. With SW2 **OFF** the LED
   anodes are disconnected and nothing lights regardless of what the firmware
   does. There is no GPIO sense for it; the code just drives PWM. If the board
   is dark, check SW2 first.
   *TINY is a low-fidelity mode by design.* SW2 = **TINY** feeds all four anodes
   through one **shared** 220 Ω (`R12`) -- unlike **ON**, which ties the common
   anode straight to STO (the supercap tank) and leaves each LED independent on its own 150 Ω cathode
   ballast. Sharing R12 makes per-LED brightness depend on how many channels are
   lit at once (a single lit LED sees ~3× the current of all four lit), so a
   `led_breathe` (all four together) and the tail of a `led_sweep` (one at a time)
   won't match in TINY the way they do in ON. The firmware **cannot** correct this:
   it can't sense SW2, and scaling duty by active-channel count would wreck ON mode
   (where no correction is wanted). TINY is the dim/long-runtime hack; treat animation
   fidelity as an ON-mode property. *(v4: move the ballast to the individual cathodes
   so TINY is linear -- see design notes.)*
2. The **accelerometer is the only actuator** on this card. `PA5/BTN` is a routed
   stub for a future revision, not populated.

## NFC contact card (`NT3H2211`, `U5`)

`U5` is an NXP **NT3H2211** (NTAG I2C plus, 2 KB) — an NFC Forum Type-2 tag on the
**same TWI0 bus** as the accel, 7-bit address **0x55** (no clash with the accel's
0x1D or the FRAM's 0x50). Its antenna is a PCB coil on `LA`/`LB` tuned to 13.56 MHz by the chip's
internal 50 pF (`C9` is a do-not-populate trim); the radio is invisible to firmware.
**Power-gate (`NFC_EN`, PA7).** The chip has no sleep state and draws ~195 µA from
VCC continuously (datasheet Table 42, 3.3 V idle) — the card's largest idle load. A
high-side load switch gates its VCC; enable is `NFC_EN` (PA7, **active-HIGH**), held
**LOW (off) by default**. Firmware raises it only around an MCU↔tag I2C access
(`nfc_power_on()` → ACK-poll the tag's address until it boots → access →
`nfc_power_off()`), and `go_to_sleep()` forces it low before every sleep, so VCC is
off essentially all the time. `NFC_EN` gates **only** the MCU↔tag I2C path — the next
two points still work with VCC off.

**Contact vCard (RF-powered).** A phone tap reads the vCard (name / title / firm /
mobile / work + personal email / website) and offers "Add to Contacts." The tag is
powered by the **phone's field**, so the read works with VCC off and even with the
supercap flat. Written once, re-writable.

**Field-detect wake + read blanking (VCC-off).** FD (`U5` pin 4 → **PA6**) pulls LOW
when a reader's field appears. Per datasheet §8.4 the FD pin **runs on the reader's field
power**, so this works with the tag's VCC gated off — that is why it survives the
power-gate. Field-present (`NC_REG.FD_ON = 00b`) is the chip's POR/config default, so no
I2C setup is needed. PA6 is a **both-edges** interrupt with an **internal pull-up** that is
the **sole** FD pull-up (no external FD resistor in the v4 design; the internal pull-up only
passes current while FD is held low).
The two edges do different jobs: on the **falling** edge (field arrives) the LEDs are held
dark and the core stays asleep for the read — `led.c` reads FD live and aborts any in-flight
breath — so the card's PWM/switching don't inject broadband noise into the 13.56 MHz band
the tag replies on (raising read SNR and range at zero cost); on the **rising** edge (field
leaves) the card fires the acknowledge glow -- **rate-limited** to one per `NFC_ACK_COOLDOWN_S`
(`USE_NFC_ACK_COOLDOWN`), so a phone parked in-field and re-polling can't fire a breath per pulse
and drain the reserve. Set `NFC_BLANK_ON_FIELD = 0` (`board.h`) to
disable blanking and glow through the read instead. A hard tap that trips both the accel and
FD still resolves to one interaction (priority is tap → nfc → motion → tick).

### Writing the NDEF (one-time)

The contact NDEF lives in `nfc.c` as a byte array, machine-generated from the vCard
fields — **regenerate, don't hand-edit**. Memory facts (NT3H2111_2211 Rev 3.6): the tag
ships with a valid Capability Container (`E1 10 6D 00`, 872 B in sector 0), so firmware
writes **only the NDEF into user memory from block 1** and never touches block 0
(writing block 0 would change the I2C address). `nfc_provision_default()` runs the
whole sequence: raise `NFC_EN`, ACK-poll until the tag boots, confirm it's present,
write the NDEF, drop `NFC_EN`. To provision:

1. Set **`NFC_PROVISION 1`** in `board.h`.
2. Flash with the card **powered** (the write needs the rail up — provisioning
   switches VCC on via `NFC_EN`; the ~300-byte vCard is 19 EEPROM blocks, ~120 ms).
3. Tap a phone to confirm the contact card appears.
4. Set `NFC_PROVISION` back to **0** and reflash, so it doesn't rewrite EEPROM every
   boot. Bump to 1 again any time to update the contact.

Block read/write are the datasheet transactions (§9.7). After an EEPROM block-write
STOP the code **fix-delays** ≥4 ms rather than polling `EEPROM_WR_BUSY`: §9.1/§9.2
say the chip stops monitoring SDA during the write and a command sent inside that
window can corrupt it, so the poll would itself be the corrupting command. The vCard
MIME type is `text/vcard`; if a reader doesn't auto-offer the contact, the legacy
fallback `text/x-vCard` is a one-line change in the generator.

## Power notes / wake architecture (these correct the hardware doc's §6)

The rail is tiny (VS is the LDO's regulated 3.3 V, fed from an unclamped ~1 F supercap tank on sub-mA indoor harvest), so standing
current is the whole game, and the wake architecture has to live within it. Two
things here diverge from the hardware doc's §6:

- **The accelerometer is no longer the sleep floor.** The board now carries an ADI
  **ADXL367** (the LIS2DH12 went to backorder). In always-measurement at 100 Hz it
  draws **0.89 µA** (datasheet), against **~10 µA** for a click-armed LIS2DH12 at the
  same rate. That one swap drops dark standby from ~11.8 µA to **~2.7 µA**, and now
  *no single part dominates*: the accel (0.89 µA), the MCU power-down (~1 µA), and the
  rest of the board leakage are all the same order. Because the ADXL367's floor is
  already this low, we run it **always-on in measurement** — there is no ODR-drop /
  sleep-to-wake trade to make, so the LIS2DH12's "a still card can't time a cold tap"
  corner does not exist here: tap and activity run continuously and a cold tap from
  rest is just a tap. Two knock-on effects: (1) the µA-level fixes elsewhere in this
  doc — unused-pin pull-ups, ADC idle-sleep — now move the needle *proportionally more*,
  since the accel no longer swamps them; (2) BOD-in-power-down (~20 µA if left on, see
  *Fuses*) is now the single largest *avoidable* draw on the board, so keeping it
  sampled/off matters more than it did. Tap is single-axis (Z) and the single-vs-double
  decision is made in the ADXL367's own hardware window; see *What to tune → Tap*.
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
delay costs a fraction of a nanoamp averaged over the 1 s poll. The conversion
itself is waited out in **IDLE sleep** rather than a busy-poll — the ADC keeps
converting with the core clock gated and its result-ready interrupt wakes the core,
so the ~350 µs poll costs the idle tier, not active-mode current (the wait is bounded
and falls back to a fail-safe 0 if a conversion never completes). So the
sleep-current question the old design flagged is **closed in code**; the bench
run now just *confirms* it (expect the analog domain to be a rounding error,
~1 µA total in power-down) rather than deciding whether there is a bug to gate.

**Unused pins don't float.** Every pin the firmware doesn't drive - PA5, PC0,
PC1 and the PORTD spares — is given an internal pull-up in `gpio_init` (PD2, the
analog sense pin, instead has its digital input buffer disabled). A floating CMOS
input draws shoot-through current in its input buffer whenever it drifts near
mid-rail; pulling the spares high removes that, so the idle draw is deterministic
rather than board- and humidity-dependent. A pulled-up pin with no load draws ~0, so
it costs nothing and changes no behaviour.

## What to tune (all in `board.h` unless noted)

Starting points, not gospel. **The tap and glow constants below are bare-card
values — re-tune them with the diffuser brace and Ti shell installed.** The full
stack changes the physics: the resin sandwich + shell mass make taps sharper and
lower-amplitude (so the accel click threshold / time windows shift), and the white
diffuser backing makes the window brighter and more even (so the glow PWM duty
shifts). Use a seat-stack -> test -> lift-stack -> adjust loop. The energy-budget
bench run fixes the real power numbers, and the accel thresholds want a real tap on
the *assembled* card — the Ti back-plate changes how a tap and vibration couple into
the sensor.

### LED glow (`board.h`; animation in `led.c`)
- **`GLOW_PEAK`** (0–255, default 220): peak LED duty for a normal tap. The 150 Ω
  ballast fixes the *peak current* on the STO tank (the LED supply rail); duty only trims the
  average, so this is brightness/energy and can't exceed the ballasted ceiling.
  It is **pre-gamma**: the animation runs `gamma2(v) = v²/256`, so 220 lands at a
  189 actual peak duty (and even 255 maps to 254). Lower it to stretch the budget.
- **`GLOW_BREATH_MS`** (1600) **/ `GLOW_CYCLES`** (2): breath duration and breaths
  per tap.
- **`USE_BROWNOUT_STRETCH`** (0/1, default 1) **/ `VS_GLOW_FULL_MV`** (3000) **/
  `VS_GLOW_DIM_PEAK`** (70): fade the glow as the reserve drains instead of a hard
  cutoff at `VS_GLOW_FLOOR_MV`. Full brightness at/above `VS_GLOW_FULL_MV`, ramped down
  to `VS_GLOW_DIM_PEAK` (on `GLOW_PEAK`'s scale) at the floor, dark below it. Invisible
  with a healthy rail; near-empty it both reads gracefully and stretches the reserve (a
  dimmer breath spends less charge, so more breaths fit before the floor). Reuses the very
  rail read that already gated the glow — free. 0 restores the original hard cutoff.
- **LED PWM polarity** (`led_init`): the LED pins use pad **INVEN**. It is
  analyzed-correct for a low-side LED on TCA split mode (which down-counts),
  giving larger duty = brighter, and it is **load-bearing for the dark idle
  state** — at duty 0 the pad parks HIGH so the LED is off. Do **not** remove
  INVEN to "fix" an apparent inversion; that lights every LED at rest. If
  brightness ever runs backwards, write `255 - duty` in `led_set`/`led_set_all`
  instead, which keeps idle dark.

### Tap (`adxl367.h`)
- **`ADXL_CFG_TAP_THRESH`** (`0x30`, 8-bit): tap sensitivity, lower = more
  sensitive. The single most likely knob to need a real-hardware tweak. All the tap
  tunables are annotated **BARE-CARD** — the enclosed stack changes the tap impulse,
  so re-tune on the bench (seat → test → lift → adjust).
- **`ADXL_CFG_TAP_DUR`** (`0x10` = 10 ms; 625 µs/LSb): the max over-threshold dwell
  still counted as a tap. Raise if firm taps are missed, lower to reject presses.
- **`ADXL_CFG_TAP_LATENT` / `ADXL_CFG_TAP_WINDOW`** (`0x20` = 40 ms / `0xC0` =
  240 ms; 1.25 ms/LSb): the double-tap window — wait after the first tap, then how
  long the second may land. **`TAP_LATENT = 0` disables double-tap.** This window
  lives in the accel now, not the firmware (see below).
- **Tap axis** is **`ADXL_CFG_AXIS_MASK`** (`0x20` = Z). Unlike the LIS2DH12's
  all-axis click, the ADXL367 watches **one** axis; Z is the card-face normal. If
  bench taps come in off-axis, this is the knob.
- ODR / current is **`ADXL_CFG_FILTER_CTL`** (`0x23` = ±2 g, 100 Hz). Lowering it is
  now *safe* — the ADXL367 is always-on at 0.89 µA with no sleep-to-wake trap — but
  the tap engine still wants enough rate to resolve the impulse, so 100 Hz stays.

### Double-tap signature (`board.h`)
- **`USE_DOUBLE_TAP`** (0/1, default 1): when on, a double-tap plays a distinct
  brighter/longer signature glow. The ADXL367 resolves single-vs-double **in
  hardware** — with both functions enabled its tap interrupt only fires after its own
  `TAP_LATENT + TAP_WINDOW` has validated or invalidated a double — so the firmware
  reads `STATUS_2` once on the interrupt (no software wait). Set 0 for an instant
  single tap with no double-tap. **Latency note:** a single tap still glows ~one
  window (`LATENT + WINDOW`, ~280 ms here) after the tap, because the hardware must
  rule out a second tap first; a double glows as soon as it validates. That window is
  set by `ADXL_CFG_TAP_LATENT/WINDOW` in `adxl367.h`, not by any firmware timer.
- **`DTAP_CYCLES` / `DTAP_BREATH_MS` / `DTAP_PEAK`** (3 / 1600 / 255): the
  signature glow — one more breath and brighter than a single tap.

### Motion / "picked up" wake (`adxl367.h`) — referenced activity
- **`ADXL_CFG_THRESH_ACT_H/L`** (13-bit; `0x00`/`0xC8` ≈ 50 counts): motion
  threshold for the soft breath. Lower if a gentle pickup doesn't wake it, raise if
  it's twitchy. BARE-CARD; bench-tune.
- **`ADXL_CFG_TIME_ACT`** (`0x02` samples): how many samples over threshold confirm
  activity — the debounce. Raise a few steps if vibration false-triggers, or if
  sustained motion gives repeated breaths.
- **Gravity is removed by the mode, not a separate filter.** `ADXL_CFG_ACT_INACT`
  (`0x03`) selects **referenced** activity (`ACT_EN = 11`): the part compares against
  a reference sample it takes itself, so the static 1 g doesn't pin INT2 — there's no
  `REFERENCE`-read priming step and no at-rest-at-boot assumption the LIS2DH12 needed.
  Activity is acknowledged by **reading `STATUS`** (the firmware does this in the
  motion / tap / nfc paths); leave it unacked and INT2 stays high and stops re-firing.

### Light & rail sensing (`board.h`; ADC in `sense.c`)
- **`VS_GLOW_FLOOR_MV`** (2600): rail floor below which a glow is refused, so an
  animation can't brown the part out mid-breath. With `USE_BROWNOUT_STRETCH` (LED glow
  section) the breath fades down to this floor rather than cutting off at it.
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
- **EEPROM counter** (`sense.c`) rewrites the same 4-byte cell (offset 0) every tap;
  only a concern past ~100 k lifetime taps, where you'd rotate the cell address.
- **`USE_SUN_DIARY`** (0/1, default 1): bank lifetime whole-hours of strong sun to a
  2-byte EEPROM cell (offset 4), read out over UPDI or surfaced in the NDEF later. The
  in-progress hour is counted in RAM and written only once per banked hour, so EEPROM sees
  ~one write per sun-hour (endurance-safe); a full supercap drain forgets at most the
  current sub-hour. Free — the poll already reads the strong-sun tell.
- **`USE_TEMP_LOG`** (0/1, default 1) **/ `TEMP_SAMPLE_POLLS`** (64): keep the lifetime **max
  die temperature** in a 1-byte EEPROM cell (offset 6) — the hot-car supercap-degradation tell.
  Uses the MCU's own sensor via a **pulsed** ADC read (2.048 V ref + `SIGROW` cal per
  DS40002315 §33.3.3.8 — no standing current, unlike the accel's `TEMP_EN`), sampled every
  `TEMP_SAMPLE_POLLS` polls (abuse temps move over minutes) and written only on a new max, so
  it essentially never writes after the first warm spell. Runs even while face-down dormant.
  Read it back with `sense_temp_max_get()` over UPDI.
- **`USE_HEALTH_LOG`** (0/1, default 1) **/ `VMIN_SAMPLE_POLLS`** (16): the field **black box** —
  the *lowest rail (VS) ever* (2-byte cell, offset 7; sampled every `VMIN_SAMPLE_POLLS`, written only
  on a new low) and the *power-cycle / full-drain count* (2-byte cell, offset 9; +1 per cold power-on
  reset, gated on `RSTCTRL.RSTFR` PORF so watchdog/UPDI resets don't count). With max-temp, that's the
  four-way forensic — heat vs. starvation vs. shipped-dark vs. overuse — from one UPDI scan
  (`sense_vmin_get()` / `sense_boot_count_get()`). Both near-free and run even while dormant.

### In-sun loading sweep (`board.h`; animation in `led.c`)
The "charging in the sun" tell: on the ~1 s poll, when the SRC solar node is under
strong illumination **and** the caps are full, the card plays a left→right loading sweep across
D2–D5. The caps-full gate is the hard safety — the sweep can never draw the pack down;
it only spends solar that would otherwise go unharvested once the tank is full. One VSENSE read yields
both the light and strong-sun predicates (`sense_vin_flags()`, raw-count, no mV math).
- **`USE_SUN_SWEEP`** (0/1, default 1): master enable. 0 compiles the trigger out of
  the poll path entirely (`led_sweep` stays linked as library code) — the one flag to
  flip if the tell proves visually busy on the bench.
- **`SWEEP_SUN_VIN_MV`** (3600): the strong-sun trip, VIN in mV (the SRC solar node,
  = VSENSE ×2 via R5/R6). Derived to sit above the indoor SRC range (~0.8–2.1 V) so it
  means the panel is under strong illumination, below panel Voc (4.15 V), and independent
  of the AEM10300 MPPT and the regulated 3.3 V VS rail. Sets
  *feel*, not safety — bench-tunable. Folded to a raw ADC count at compile time (`sense.c`).
- **`SWEEP_CAPS_FULL_MV`** (3300): the hard caps-full gate, VS in mV. Independent of
  the harvest control/regulator and of `SWEEP_SUN_VIN_MV`, so the animation can never draw the pack down.
- **`SWEEP_PASSES` / `SWEEP_PASS_MS` / `SWEEP_PEAK` / `SWEEP_OVERLAP`** (2 / 800 / 235 /
  320): wipes per invocation, ms per wipe, per-LED peak duty, and bump half-width (Q8
  units of LED spacing; 256 = neighbours cross ~50%). Tune the feel with
  `docs/led-sweep-tuner.html`.

### System (`board.h` / `main.c`)
- **`USE_WDT`** (0/1, default 1): the watchdog (see Robustness below).
- **`USE_FACEDOWN_DORMANT`** (0/1, default 1) **/ `FACEDOWN_DORMANT_S`** (180) **/
  `FACEDOWN_Z_THRESH`** (−32): lie the card face-down for `FACEDOWN_DORMANT_S` seconds and it
  goes dormant — every glow suppressed until it is turned face-up — so a stowed card can't
  drain the reserve on false triggers. `FACEDOWN_Z_THRESH` is the ADXL367 8-bit Z below which
  it reads face-down (~64 LSB/g, so −32 ≈ −0.5 g). **Bench-confirm the sign:** read Z face-up
  (should be ~+64); if it reads ~−64, this board's accel has +Z reversed, so negate the byte in
  `adxl367_read_z`. Net energy win — one accel read per poll, dwarfed by the glows it suppresses.
- **`USE_DARK_MOTION_MUTE`** (0/1, default 1): mute the *motion* soft-breath when the last poll
  saw no light (card stowed in a dark pocket/bag), closing a real carry-drain — a jostling card
  would otherwise fire a ~1.6 s breath on every activity trip and empty the reserve on a walk. The
  deliberate **tap** glow is untouched (dark or light), so the dark-room tap-to-glow moment stays.
  Near-free (reuses the cached poll light); complements face-down dormant by covering *any*
  orientation a pocket leaves the card in.
- **`USE_NFC_ACK_COOLDOWN`** (0/1, default 1) **/ `NFC_ACK_COOLDOWN_S`** (3): rate-limit the
  field-leave acknowledge glow to at most one per `NFC_ACK_COOLDOWN_S`. The `FD` pin tracks the
  reader's field, and a phone parked in-field keeps *polling* (its NFC discovery loop pulses the
  carrier a few times a second), so every pulse's trailing edge would otherwise fire a fresh ack
  breath -- a phone left face-down on top of the card could bleed the reserve breath by breath. The
  first read still acks instantly; re-polls inside the window are muted (the RF vCard read itself is
  hardware and untouched). The rail floor already stops a brownout; this stops the wasteful bleed
  *to* the floor. Near-free (one main-local byte, aged one count per poll tick).
- **Core clock** is 1 MHz OSCHF (`clocks_init`, see Robustness for the why and the
  knock-ons). Note VREF start-up time — and therefore the `INITDLY` sizing above —
  depends on this being the high-frequency clock, not a 32 kHz main clock.

## Robustness / hardening

- **Watchdog (`USE_WDT`, on by default).** An ~8 s WDT (runs in every sleep mode
  off the ULP oscillator) recovers the card from an unexpected lockup. It is
  petted from the **main-loop top** and from **inside the animation naps**
  (`idle_nap_ms`, shared by `led_breathe` and `led_sweep`; ~1 ms cadence), never from
  an ISR — petting from an ISR would mask a wedged main loop, which is exactly the
  failure to catch. The PIT wakes the loop every `POLL_PERIOD_S`, so power-down sleep
  never trips it. The timeout must stay well above both the poll period and the longest
  animation (the double-tap glow, `DTAP_CYCLES * DTAP_BREATH_MS` ≈ 4.8 s); at the 8 s
  setting and the defaults there is wide margin.
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
  through the glow — and idle-sleeps through the ADC conversion (see *Power
  notes*) — it is only active in brief bursts (the wake/compare overhead around
  each poll plus the one-time boot config), so a slower clock trims the per-burst
  active current for no behaviour cost here. The knock-ons were handled so nothing actually
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
the `fuses` target prints the exact `avrdude` commands (all three values derived below):

- **`BODCFG` -- brown-out, corrected.** `sense_rail_ok()` / `sense_glow_peak()` are only a
  *software* floor checked before each glow; for a hardware guard against the rail collapsing
  mid-operation the BOD runs as a **sampled** brown-out. **Value: `BODCFG = 0x2A`** = `LVL = 0x1`
  (**2.45 V**), `SAMPFREQ = 0` (**128 Hz**), `ACTIVE = SAMPLE`, `SLEEP = SAMPLE`.
  **Do NOT use `0x0A`.** That is `LVL = 0x0` = BODLEVEL0 = 1.9 V, which the datasheet
  (DS40002315C p.207) enables **only during chip erase** -- in normal operation writing `LVL = 0x0`
  is **the same as disabling the BOD**. A card burned with `0x0A` ships with *no* brown-out detection
  and *no* VLM, not a 1.9 V guard. The lowest real normal-op level is `LVL = 0x1` = **2.45 V**.
  2.45 V is the right pick: it sits **below** the 2.6 V glow floor (`VS_GLOW_FLOOR_MV`), so a
  glow-load sag never trips a spurious reset (glows already stop at 2.6 V), and **above** the 1.8 V
  core minimum, so it resets before the CPU can misexecute. It also **holds the core in low-current
  reset until 2.45 V**, which is the mitigation for the slow-ramp cold-start stall (a dead-battery
  card can't release the CPU into an active draw the µA harvest can't sustain). Continuous BOD
  (`ENABLE`) is ~17 µA, far too heavy for this rail; sampled costs a small fraction. `SAMPFREQ = 1`
  (32 Hz → `0x3A`) shaves a little more standby at ~31 ms detection latency. Do **not** use
  2.70/2.85 V -- above the glow floor, they would reset the card before it could glow.
- **EEPROM-write safety (a software VLM).** Even a correct 2.45 V BOD does not fully protect a write:
  the BOD only *aborts* a write already in progress (DS40002315C sec 11.3.3), and the sampled BOD checks
  at just 128 Hz. So firmware refuses to **start** a telemetry write unless the rail is above
  **`EE_WRITE_FLOOR_MV`** (2.7 V) -- the job the datasheet assigns to the VLM, done in software so it holds
  between BOD samples and even if the BOD is off. The two lifetime-extreme loggers (min-rail, max-temp)
  track their value in RAM and only *commit* above the floor, so a recoverable sag or heat spell is still
  captured; the power-cycle count is flagged at boot and committed once the rail has charged (a cold boot
  lands right at the reset-release voltage). Only a terminal drain below the floor goes unrecorded --
  unavoidable, since you cannot safely write EEPROM as the rail collapses.
- **`SYSCFG1.MVSYSCFG` -- MVIO. Value: `SYSCFG1 = 0x10`** (`MVSYSCFG = SINGLE`, `SUT = 0`; factory
  default is `0x08` = DUAL). The board ties VDDIO2 to VS, so PORTC runs off the main rail with no
  separate I/O voltage, which is what SINGLE means. (DUAL also works here since VDDIO2 sits at a
  valid voltage, but SINGLE is the correct intent. Note: PORTC ADC/AC inputs would *require* SINGLE --
  this design doesn't use them, VSENSE is on PD2.)
- **`SYSCFG0.EESAVE` -- keep the black box across reflashes. Value: `SYSCFG0 = 0xD1`** = factory
  default `0xD0` **+ EESAVE** (bit 0). A UPDI chip-erase (every reflash) wipes EEPROM unless `EESAVE`
  is set, which skips EEPROM on erase -- without it a reflash wipes the tap counter, sun diary,
  max-temp, and black box, so the "lifetime" framing only holds with this set. `0xD1` leaves
  `UPDIPINCFG = 1` (UPDI stays usable) and `RSTPINCFG = 0` (PF6 input, factory default) untouched.
  (A *locked* device erases EEPROM regardless; this board isn't locked.)
- **`SYSCFG0.UPDIPINCFG` — leave UPDI alone.** UPDI on pin 23 (TC2030 pad / J1) is
  the only program path; do not repurpose that pin or you lose programming access.
- **`OSCCFG`** can stay at default — the firmware selects the 1 MHz OSCHF clock in
  software (`clocks_init`), so no clock fuse change is needed.
