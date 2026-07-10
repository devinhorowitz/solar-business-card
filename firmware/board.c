/*
 * board.h  --  SOLAR-GLOW DRH v3.0  as-built pin/route map.
 *
 * Single source of truth = the committed solar-glow-drh-v3_0.kicad_pcb
 * (pad -> pinfunction -> net read directly from the board) cross-checked
 * against solar-glow-drh-v2-hardware.md and the AVR64DD32-28 datasheet
 * (DS40002315). Every PORTMUX/peripheral value below is the value the
 * physical routing requires, not a default.
 *
 * MCU: AVR64DD28, 28-pin VQFN, on the BACK of the board.
 *
 *   pad pinfunc  net      role
 *    26 PA0      LDRV4    LED D5 low-side drive    TCA0 WO0
 *    27 PA1      LDRV3    LED D4                   TCA0 WO1
 *    28 PA2      LDRV2    LED D3                   TCA0 WO2
 *     1 PA3      LDRV1    LED D2                   TCA0 WO3
 *     2 PA4      PA4      spare GPIO  (JP2.1)
 *     3 PA5      BTN      reserved button (stub only; v3 hook)
 *     4 PA6      FD       NFC field-detect in (NT3H2211)  FD-wake, falling; field-powered (works VCC-off)
 *     5 PA7      NFC_EN   NFC VCC load-switch enable (active-HIGH)  output, LOW = NFC off
 *     6 PC0      PC0      spare GPIO  (JP2.2)
 *     7 PC1      PC1      spare GPIO  (JP2.3)
 *     8 PC2      SDA      TWI0 host SDA  (TWIROUTEA=ALT2)  ext 4.7k to VS
 *     9 PC3      SCL      TWI0 host SCL  (TWIROUTEA=ALT2)  ext 4.7k to VS
 *    10 VDDIO2   VDDIO2   tied to VS by SJ1 -> PORTC at rail, MVIO unused
 *    12 PD2      VSENSE   light/rail sense  AIN2 (ADC) + AINP0 (AC0+)
 *    18 VDD      VS       clamped rail <= 3.60V (~3.50 typ)
 *    19 GND      GND
 *    20 PF0      INT2     accel INT2 in  (PORTF pin interrupt)
 *    21 PF1      INT1     accel INT1 in  (PORTF pin interrupt)
 *    23 UPDI     UPDI     program (TC2030 pad TC1 / header J1)
 *    24 VDD      VS
 *    25 GND      GND
 *    EP          GND
 *
 * LED channel map (D1/D9 are Schottkys, NOT LEDs):
 *   D2->LDRV1->PA3/WO3 ; D3->LDRV2->PA2/WO2 ; D4->LDRV3->PA1/WO1 ; D5->LDRV4->PA0/WO0
 *   each LED: anode->ANODE common->SW2->VS ; cathode->Kn->150R ballast->LDRV net->pin (see map above)
 */
#ifndef BOARD_H
#define BOARD_H

#include <avr/io.h>

/* ---- main clock: internal OSCHF at 1 MHz, no crystal fitted ---- */
#define F_CPU 1000000UL   /* OSCHF run frequency; see clocks_init in main.c */

/* ---- LEDs (low-side sink) on PORTA PA0..PA3 = TCA0 WO0..WO3 ----
 * TCA0 split: WO0..WO2 driven by LCMP0..2 (low timer), WO3 by HCMP0 (high timer).
 * PORTMUX.TCAROUTEA = PORTMUX_TCA0_PORTA_gc (0x00): WO0..WO3 land on PA0..PA3. */
#define LED_PORT        PORTA
#define LED_PA0_bm      PIN0_bm   /* LDRV4 / WO0 / LCMP0 */
#define LED_PA1_bm      PIN1_bm   /* LDRV3 / WO1 / LCMP1 */
#define LED_PA2_bm      PIN2_bm   /* LDRV2 / WO2 / LCMP2 */
#define LED_PA3_bm      PIN3_bm   /* LDRV1 / WO3 / HCMP0 */
#define LED_ALL_bm      (LED_PA0_bm | LED_PA1_bm | LED_PA2_bm | LED_PA3_bm)

/* ---- accel interrupt inputs on PORTF (no crystal -> PF0/PF1 are GPIO) ---- */
#define ACC_PORT        PORTF
#define ACC_INT1_bm     PIN1_bm   /* PF1 <- ADXL367 INT1 (tap, single+double) */
#define ACC_INT2_bm     PIN0_bm   /* PF0 <- ADXL367 INT2 (activity/motion)    */

/* ---- light/rail sense on PD2 ----
 * VSENSE = VIN/2 (R5/R6 = 1M each, C5 = 10nF). ADC sees ~VIN/2; x2 = VIN.
 * PD2 = AIN2 (ADC MUXPOS 0x02) and AINP0 (AC0 MUXPOS 0x00). */
#define VSENSE_AIN          ADC_MUXPOS_AIN2_gc        /* 0x02 */
#define VSENSE_DIVIDER      2                          /* VIN = VSENSE * 2   */

/* ---- I2C device: ADI ADXL367 accelerometer (replaces LIS2DH12, backorder) ----
 * SCLK tied low -> I2C mode ; ASEL grounded -> 7-bit address 0x1D. See adxl367.h. */
#define ADXL367_ADDR    0x1D

/* ---- I2C device: NXP NT3H2211 (NTAG I2C plus 2K), v2.2 NFC addition ----
 * 7-bit address 0x55 (write 0xAA / read 0xAB); shares TWI0 with the accel @0x1D,
 * no clash. Antenna is the PCB coil on LA/LB, tuned by the chip's internal 50pF
 * (C9 = DNP trim) -- no firmware involvement in the radio.
 *
 * POWER-GATED: the chip draws ~195 uA continuously from VCC (datasheet Table 42,
 * 3.3V idle) with NO sleep state -- the dominant idle drain on the supercaps. A
 * high-side load switch now gates its VCC; enable is NFC_EN (PA7, active-HIGH),
 * default LOW = VCC off (~0 draw). Raise HIGH only while the MCU needs the I2C
 * side (provisioning / read / write), then drop it LOW again. NFC_EN gates ONLY
 * the MCU<->tag I2C path: a phone reading the static vCard, and the FD field-
 * detect wake (see below), both run on the phone's field power and work with VCC
 * OFF (datasheet 8.4). */
#define NT3H_ADDR       0x55

/* NFC_EN: high-side load-switch enable for the NT3H2211 VCC. ACTIVE-HIGH.
 *   1 = NFC powered (I2C reachable).   0 = VCC off (default; ~0 draw). */
#define NFC_EN_PORT     PORTA
#define NFC_EN_PIN_bm   PIN7_bm

/* FD (field detect, U5 pin4) -> PA6, open-drain, external 10k (R13) to VS.
 * FD-WAKE: a phone's field pulls FD low (FD_ON=00b, field-present = the POR
 * default). Per datasheet 8.4 the FD pin runs on the phone's field power, so it
 * works even with the tag's VCC gated off -- that is why FD-wake survives the
 * power-gate. main.c senses a FALLING edge on PA6 and runs the tap glow; no I2C
 * setup is needed (the field-present default does it). Firmware also enables PA6's
 * internal pull-up as belt-and-suspenders. R13 ties FD to VS on the v3.0 board
 * (confirmed from copper), so the pull-up is redundant insurance -- it only sinks
 * current while FD is held low. */
#define FD_PORT         PORTA
#define FD_PIN_bm       PIN6_bm

/* NFC read SNR: while a reader's field is present (FD low), hold the LEDs dark so
 * their PWM edges don't inject broadband noise into the 13.56 MHz band the tag
 * replies on. 1 = blank during the read (best SNR; the acknowledge glow fires when
 * the field leaves). 0 = ignore FD and glow through the read. led.c reads FD live
 * and aborts an in-flight breath; main.c fires the post-read glow on FD's rising
 * edge. To DIM instead of fully blank, the FD path would run a reduced-peak breath
 * instead -- kept simple (blank) here since a read is only milliseconds. */
#define NFC_BLANK_ON_FIELD  1

/* One-shot NDEF provisioning. The tag is RF-powered by the phone, so the NDEF is
 * read even with the supercap flat, and it only has to be written once. Set to 1
 * for a SINGLE flash to write the NDEF into the tag EEPROM, confirm the phone
 * reads it, then set back to 0 and reflash (avoids re-writing EEPROM every boot).
 * The NDEF stays re-writable -- bump this to 1 again to rewrite. nfc_provision_default()
 * powers the tag on (NFC_EN high) for the write and drops it back off afterward. */
#define NFC_PROVISION   0

/* =====================================================================
 * Tunables  (bench-set; see README "What to tune").  All comments here
 * are starting points, not gospel -- the energy-budget bench run is the
 * gate that fixes the real numbers.
 * ===================================================================== */

/* LED glow.  BARE-CARD values: re-check with the diffuser brace + Ti shell
 * installed -- the white LED-hug diffuser backing makes the window brighter and
 * more even, so the PWM duty (and the hardware TINY mode) want a first-light
 * re-check enclosed. */
#define GLOW_PEAK       220   /* 0..255 peak duty per LED at full bright.
                                 Ballast (150R) fixes PEAK current to ~8 mA on
                                 the clamped rail (amber Vf~2.25V, (3.4-2.25)/150);
                                 PWM only trims the average below that, so this
                                 never exceeds the ballasted ceiling. */
#define GLOW_BREATH_MS  1600  /* one breathe-in/out cycle, ms */
#define GLOW_CYCLES     2     /* breaths per tap */

/* Double-tap = a distinct "signature" glow (brighter + longer) on top of the
 * normal single-tap glow. USE_DOUBLE_TAP=1 enables it. The ADXL367 resolves single
 * vs double IN HARDWARE (it waits its own TAP_LATENT + TAP_WINDOW before firing the
 * tap interrupt), so the firmware just reads STATUS_2 once and needs no software
 * window. Set 0 for instant single-tap with no double. The double-tap timing lives
 * in adxl367.h (ADXL_CFG_TAP_LATENT / ADXL_CFG_TAP_WINDOW). */
#define USE_DOUBLE_TAP  1
#define DTAP_CYCLES     3     /* signature glow: more breaths than a single tap */
#define DTAP_BREATH_MS  1600
#define DTAP_PEAK       255   /* and brighter (single tap uses GLOW_PEAK)       */

/* In-sun "loading" chase (the strong-sun + caps-full tell): a bright bump sweeps
 * left->right across D2..D5, each LED fading up then down and overlapping its
 * neighbour so that as one dims the next brightens. Fires only when the caps are
 * full and the panel is in strong sun, so it never drains the pack (power is free in
 * sun). Tune the feel by eye / with the simulator. Physical L->R = D2,D3,D4,D5, which
 * led.c maps to channels 3,2,1,0. */
#define SWEEP_PASSES    2     /* left->right wipes per invocation */
#define SWEEP_PASS_MS   800   /* ms per wipe (lower = faster "loading" feel) */
#define SWEEP_PEAK      235   /* peak per-LED brightness at each bump centre (0..255) */
#define SWEEP_OVERLAP   320   /* bump half-width, Q8 spacing: 256 = cross ~50%, >256 = softer */

/* charge floor: skip the glow (stay dark) below this rail voltage, mV.
 * Read via ADC VDD/10. Keeps a brown-out from bricking mid-animation. */
#define VS_GLOW_FLOOR_MV   2600

/* wake-on-light threshold on VSENSE (= VIN/2), mV at the pin.
 * ~0 in dark, ~1.2-2.1 V in light. ~0.4 V sits comfortably above dark. */
#define LIGHT_THRESH_MV    400

/* baseline poll period (option B), seconds (RTC PIT). 1 or 2. */
#define POLL_PERIOD_S      1

/* power-on wink only fires with comfortable headroom above the glow floor,
 * so a freshly-charged-but-marginal card cannot wink itself back below the
 * floor (matters most if BOD is later enabled and the rail hovers near the
 * floor while charging). Set >= VS_GLOW_FLOOR_MV. */
#define WINK_FLOOR_MV      3000

/* watchdog: recover from an unexpected lockup on a fielded card. 1 = on.
 * Petted from the main loop (top) and from inside led_breathe, never from an
 * ISR. Timeout (~8 s) must stay well above POLL_PERIOD_S and the longest glow
 * (GLOW_CYCLES * GLOW_BREATH_MS); the PIT wakes the loop every poll to pet it,
 * so power-down sleep never trips it. */
#define USE_WDT            1

#endif /* BOARD_H */
