/*
 * board.h  --  SOLAR-GLOW DRH v4.0  as-built pin/route map.
 *
 * Single source of truth = the committed solar-glow-drh-v4_0.kicad_pcb
 * (pad -> pinfunction -> net read directly from the board) cross-checked
 * against solar-glow-drh-v2-hardware.md and the AVR64EA28 datasheet
 * (DS40002443). Every PORTMUX/peripheral value below is the value the
 * physical routing requires, not a default.
 *
 * MCU: AVR64EA28, 28-pin VQFN, on the BACK of the board. (v4 family swap from
 * the AVR64DD28: 27/28 pads identical; TWI ALT2, TCA0-on-PORTA, and the
 * PD1/PD2 analog inputs all carry over -- see design-notes 5 addendum.)
 *
 *   pad pinfunc  net      role
 *    26 PA0      LDRV4    LED D5 low-side drive    TCA0 WO0
 *    27 PA1      LDRV3    LED D4                   TCA0 WO1
 *    28 PA2      LDRV2    LED D3                   TCA0 WO2
 *     1 PA3      LDRV1    LED D2                   TCA0 WO3
 *     2 PA4      CHG_DIS_G  Q2 gate: low-side charge-disable buffer (push-pull, HIGH = disable; R18 holds charge ON when MCU dead)
 *     3 PA5      BTN      button pin -- deliberately NO-FIT; a future button = PA5->switch->GND (active-low)
 *     4 PA6      FD       NFC field-detect in (NT3H2211)  FD-wake, both edges; field-powered (works VCC-off)
 *     5 PA7      NFC_EN   NFC VCC load-switch enable (active-HIGH)  output, LOW = NFC off
 *     6 PC0      PC0      spare GPIO  -- deliberately unrouted, no breakout
 *     7 PC1      PC1      spare GPIO  -- deliberately unrouted, no breakout
 *     8 PC2      SDA      TWI0 host SDA  (TWIROUTEA=ALT2)  ext 4.7k to VS
 *     9 PC3      SCL      TWI0 host SCL  (TWIROUTEA=ALT2)  ext 4.7k to VS
 *    10 PD0      VDDIO2   EA GPIO on the old VDDIO2 pad; SJ1 deleted 2026-07-30 (DNP before that), but C3 (100 nF -> GND, the DD-era decoupler) still hangs on the net -- no DC hold, so the internal pull-up (gpio_init) is still required; it just also charges C3 at boot
 *    11 PD1      STO_SNS    supercap-state sense  AIN1 (STO via R15/R16 divide-by-3)
 *    12 PD2      VSENSE   light sense (now SRC) + rail  AIN2 (ADC) + AINP0 (AC0+)
 *    18 VDD      VS       regulated 3.3 V LDO output (U9 TPS7A0233, STO->VS)
 *    19 GND      GND
 *    20 PF0      INT1     accel INT1 in  (PORTF pin interrupt)
 *    21 PF1      INT2     accel INT2 in  (PORTF pin interrupt)
 *    23 UPDI     UPDI     program (TC2030 pad TC1 / header J1)
 *    24 VDD      VS
 *    25 GND      GND
 *    EP          GND
 *
 * LED channel map (D1/D9/D10/D11 Schottkys removed in v4; only D2..D5 remain):
 *   D2->LDRV1->PA3/WO3 ; D3->LDRV2->PA2/WO2 ; D4->LDRV3->PA1/WO1 ; D5->LDRV4->PA0/WO0
 *   each LED: anode->ANODE common->SW2->STO (ON; bridge open = OFF) ; cathode->Kn->RN1 element->LDRV net->pin (see map above).
 *   RN1 is the 4x150R array that replaced discrete R1-R4 (2026-08-07): elements pair pins 1-8/2-7/3-6/4-5,
 *   wired so every K meets its documented LDRV -- the channel map above is unchanged.
 */
#ifndef BOARD_H
#define BOARD_H

#include <avr/io.h>

/* ---- main clock: internal OSCHF at 1 MHz, no crystal fitted ---- */
#ifndef F_CPU             /* the Makefile passes -DF_CPU; guarded so that knob actually
                           * works (unguarded, overriding it warned in every TU -- a hard
                           * FAIL under CI's -Werror -- and split delay calibration across
                           * files by include order; 2026-08-01 pressure test) */
#define F_CPU 1000000UL   /* OSCHF run frequency; see clocks_init in main.c */
#endif

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
#define ACC_INT1_bm     PIN0_bm   /* PF0 <- ADXL367 INT1 (tap, single+double) */
#define ACC_INT2_bm     PIN1_bm   /* PF1 <- ADXL367 INT2 (activity/motion)    */

/* ---- light/rail sense on PD2 ----
 * VSENSE = VIN/2 (R5/R6 = 1M each, C5 = 100nF). ADC sees ~VIN/2; x2 = VIN.
 * PD2 = AIN2 (ADC MUXPOS 0x02) and AINP0 (AC0 MUXPOS 0x00). */
#define VSENSE_AIN          ADC_MUXPOS_AIN2_gc        /* 0x02 */
#define VSENSE_DIVIDER      2                          /* VIN = VSENSE * 2   */

/* ---- supercap-state sense on PD1 (AEM10300 STO via divide-by-3) ----
 * VS is now the regulated 3.3 V LDO output (constant), so the old VDD/10 read no longer tracks
 * the pack. STO (0.2..4.65 V) is divided by 3 into AIN1/PD1; the re-pointed sense_vdd_mv() reads
 * this channel and scales back: STO_mv = pin_mv * STO_DIVIDER. */
#define STO_SNS_AIN     ADC_MUXPOS_AIN1_gc     /* PD1 = AIN1 */
#define STO_DIVIDER     3                       /* R15 / R16 = 2 M / 1 M */

/* ---- AEM10300 charge-disable via Q2 buffer, gate on PA4 (net CHG_DIS_G), ACTIVE-HIGH ----
 * Since the 2026-07-23 cold-start-deadlock fix, PA4 drives the GATE of Q2 (BSS138LT1G
 * low-side buffer -- "2N7002" here until 2026-08-01; the BOM master and board fit the
 * BSS138, an equivalent logic-level NFET, and this file claims to be the as-built map)
 * -- not the AEM pin directly. Gate HIGH = Q2 on = EN_STO_CH pulled to GND = charging
 * DISABLED (quiets the >=10 MHz DCDC for an NFC read); gate LOW = Q2 off = EN_STO_CH floats to
 * its internal pull-up + R17/VINT = charging ENABLED. R18 (1 M gate pulldown) holds Q2 off --
 * charging ON -- whenever the MCU is dead/resetting/UPDI-parked, so a fully discharged card
 * always recharges (the old direct open-drain drive let the dead MCU's pin clamp hold the AEM's
 * enable low forever; see the design-notes second-sift addendum). PA4 is push-pull now and never
 * touches the 2.75 V-max AEM pin. Toggled in the FD both-edge handler in main.c. */
#define ENSTOCH_PORT    PORTA
#define ENSTOCH_PIN_bm  PIN4_bm

/* ---- I2C device: ADI ADXL367 accelerometer (replaces LIS2DH12, backorder) ----
 * SCLK tied low -> I2C mode ; ASEL grounded -> 7-bit address 0x1D. See adxl367.h. */
#define ADXL367_ADDR    0x1D

/* ---- I2C device: NXP NT3H2211 (NTAG I2C plus 2K), v2.2 NFC addition ----
 * 7-bit address 0x55 (write 0xAA / read 0xAB); shares TWI0 with the accel @0x1D,
 * no clash. Antenna is the PCB coil on LA/LB, tuned by the chip's internal 50pF
 * plus C9 -- FITTED at 47 pF since 2026-07-30 (value derived, not trimmed; "C9 =
 * DNP trim" here until 2026-08-01 was two board revisions stale) -- no firmware
 * involvement in the radio.
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

/* FD (field detect, U5 pin4) -> PA6, open-drain; the internal PA6 pull-up holds it (no external FD pull-up fitted).
 * FD-WAKE: a phone's field pulls FD low (FD_ON=00b, field-present = the POR
 * default). Per datasheet 8.4 the FD pin runs on the phone's field power, so it
 * works even with the tag's VCC gated off -- that is why FD-wake survives the
 * power-gate. main.c senses PA6 on BOTH edges: the falling edge (field arrives)
 * wakes the core to blank the LEDs for the read, and the rising edge (field leaves)
 * fires the acknowledge glow (see NFC_BLANK_ON_FIELD below). No I2C setup is needed
 * -- the field-present default does it. Firmware enables PA6's
 * internal pull-up, the SOLE FD pull-up (no external FD resistor in the design).
 * STANDING COST, corrected 2026-08-01 (pressure test; "only sinks current while FD
 * is held low" was wrong): the tag's own FD pin specs IL leakage 1.5 uA typ /
 * 10 uA MAX (NT3H2211 Table 42) with FD HIGH -- the card's dominant state -- so
 * that leakage flows from VS through the pull-up essentially always, independent
 * of the pull-up's value. Unbudgeted, it is +56% typ / +370% max against the
 * README's ~2.7 uA dark-standby sum; the same table specs SDA/SCL IL at 10 uA max
 * each through R10/R11 while VCC is gated. BENCH (beside the FRAM back-power
 * item): meter VS with FD pulled up vs grounded (VCC off, no field) to pin the
 * real leakage, and re-check FD's VIH margin at measured IL x pull-up R. */
#define FD_PORT         PORTA
#define FD_PIN_bm       PIN6_bm

/* ---- I2C device: RAMXEED/Fujitsu MB85RC512TY FRAM (U7), 512 kbit = 64 KB (v4) ----
 * 7-bit address 0x50 (A0/A1/A2 grounded); shares TWI0 with the accel @0x1D and the
 * NFC tag @0x55, no clash. VDD rides the ALWAYS-ON VS rail (2026-07-23 back-power
 * fix: on the gated VNFC its inputs sat above its rail past abs-max whenever the
 * bus idled high -- see the design-notes deep-dive addendum; VNFC now gates the
 * tag alone). Standing cost parked at the part's own I2C SLEEP mode, IZZ 0.20 uA
 * typ / 10 uA max hot (fram_sleep / fram_wake in fram.c; wake costs ~450 us).
 * 64 KB linear space, 16-bit address; FeRAM commits each byte at its ACK (no
 * settle delay, ~1e13 endurance; "commits at the STOP" here until 2026-08-01
 * contradicted fram.c's own header). Runtime archival use stays gated by USE_FRAM_LOG below
 * (headless by default -- but boot ALWAYS parks it; see main.c). */
#define FRAM_ADDR       0x50

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
 * more even, so the PWM duty wants a first-light re-check enclosed. */
#define GLOW_PEAK       220   /* 0..255 peak duty per LED at full bright.
                                 Ballast (150R) sets the PEAK current ceiling;
                                 the LED anode is fed from the STO supercap tank
                                 via SW2 (amber Vf~2.25V), so the ceiling tracks
                                 STO (e.g. ~16 mA at STO~4.65V VOVCH, (4.65-2.25)/150);
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
 * led.c maps to channels 3,2,1,0. WIRED: main.c's ~1 s poll fires it when
 * sense_vin_flags() reports SENSE_SUN_bm (VIN past SWEEP_SUN_VIN_MV) with the caps
 * full (sense_caps_full()); the two thresholds are just below. */
#define SWEEP_PASSES    2     /* left->right wipes per invocation */
#define SWEEP_PASS_MS   800   /* ms per wipe (lower = faster "loading" feel) */
#define SWEEP_PEAK      235   /* peak per-LED brightness at each bump centre (0..255) */
#define SWEEP_OVERLAP   320   /* bump half-width, Q8 spacing: 256 = cross ~50%, >256 = softer */

/* Master enable for the in-sun sweep. 1 = wired (default); set 0 to compile the
 * trigger out of the poll path entirely (led_sweep() stays linked as library code).
 * The one flag to flip if the tell ever proves visually busy on the bench. */
#define USE_SUN_SWEEP   1

/* SWEEP_SUN_VIN_MV -- the in-sun trigger: VIN (the raw SRC solar node, no blocking
 * diode in v4; = VSENSE pin x2) at/above which we call it "strong sun." This is the
 * number the PCB side owed firmware; derived here, bench-tunable (it sets feel, not
 * safety -- SWEEP_CAPS_FULL_MV below is the hard gate).
 *
 * WHAT THIS ACTUALLY MEASURES (corrected 2026-07-26 PCB audit -- the old derivation
 * below was wrong and the consequence is real, so it is written out in full).
 *
 * The OLD reasoning was: "the panel is a current source rolling off toward Voc, so
 * under load the SRC node self-settles below Voc; VIN >= 3.60 V therefore means
 * strong sun." That models SRC as a PASSIVE node. It is not. While the AEM10300 is
 * harvesting it ACTIVELY REGULATES SRC to a fixed fraction of the panel's open-
 * circuit voltage: "the voltage on SRC is regulated by an internal Maximum Power
 * Point Tracking (MPPT) module ... as a given fraction of the open-circuit voltage"
 * (AEM10300 sec 8.4), the fraction being R_ZMPP = V_MPP/V_OC, set by the R_MPP[2:0]
 * straps. This board straps R_MPP[2:0] = H,L,L (read off the .kicad_pcb: R_MPP2 ->
 * VINT, R_MPP1 -> GND, R_MPP0 -> GND) = 80% (Table 9).
 *
 * So while CHARGING, SRC = 0.80 x Voc. Reaching 3600 mV would need Voc >= 4500 mV,
 * above the SM141K06TF's 4.15 V Voc -- so in ordinary charging this threshold is
 * UNREACHABLE in any light, however bright. It trips in only two situations:
 *   1. Caps full. At VOVCH the DCDC stops and "the SRC pin is set to high impedance"
 *      (sec 8.3.2), so the unloaded panel rises to Voc (4.15 V in sun) -> pin 2.075 V,
 *      which also SATURATES the 2.048 V reference -> 4095 counts, far above SUN_COUNT.
 *   2. Briefly, during an MPP evaluation, when the AEM disconnects the source to
 *      measure Voc. T_MPP[1:0] straps H,L on this board = 70.8 ms every 4.5 s
 *      (Table 10) = a 1.6% duty window in which SRC reads Voc even while charging.
 *
 * CONSEQUENCE, and why it is left as-is for now: SENSE_SUN_bm is therefore NOT a
 * "strong sun" tell -- it is very nearly a "the harvester has stopped charging" tell,
 * i.e. the same condition SWEEP_CAPS_FULL_MV already gates on. The two sweep co-gates
 * are not independent as the comment below once claimed. The SWEEP still behaves
 * correctly (it fires when the tank is full and the panel is unloaded, which is
 * exactly when surplus light is free), so this is a wrong RATIONALE rather than a
 * broken feature -- but SWEEP_SUN_VIN_MV is close to meaningless as a tunable: any
 * value from ~3.4 V to 4.096 V behaves identically. To make it mean "strong sun"
 * again it must sit BELOW 0.8 x Voc, i.e. nearer 3000-3200 mV, which would let it
 * discriminate bright from dim while charging (Voc does rise with illumination).
 * That is a feel-and-energy retune, so it waits for the bench (see TODO) rather than
 * being changed blind. The SAME correction applies to USE_SUN_DIARY: it counts polls
 * where this flag is set, so it is banking "caps-full time" plus a ~1.6% sampling
 * artifact, NOT hours of sun.
 *
 * ADC: VSENSE pin = VIN/2 vs the 2.048 V ref, so 3.60 V -> 3600 counts, which sense.c
 * folds at compile time (SUN_COUNT) so the poll compares raw, no per-poll mV math.
 * (Ref changed from 2.500 V in the 2026-07-26 audit -- see the ADC_VREF_MV block in
 * sense.c; the fold tracks the constant automatically.) */
#define SWEEP_SUN_VIN_MV   3600

/* SWEEP_CAPS_FULL_MV -- the sweep's HARD safety gate: sweep only when the TANK (STO)
 * is at/above this. Read via the R15/R16 divide-by-3 on PD1/AIN1, sense_caps_full().
 *
 * RE-DERIVED 2026-07-26 (audit): was 3300, which was a STALE v3 VALUE and no longer a
 * fullness criterion at all. In v3 the sensed rail WAS the supercap node, held by the
 * (now deleted) TLV3011B clamp at ~3.5 V, so 3300 mV was ~94% of full -- a real "caps
 * full" test. v4 re-pointed this channel to STO, whose ceiling is the AEM10300's
 * VOVCH = 4.65 V (Table 8, STO_CFG[3:0] = L,L,H,H "Dual-cell supercapacitor", matching
 * the board straps). The other three floors were re-derived for the STO range during
 * that rework; this one was carried over unchanged. At 3300 mV the tank is only 71% of
 * VOVCH and, since energy goes as V^2, just 50% of stored charge-energy -- so the gate
 * that documented itself as ensuring the animation "can never draw the pack down" in
 * fact permitted it to spend down to half the tank, repeatedly (main.c re-arms the
 * sweep every poll while the light holds).
 * 4400 mV = 94.6% of VOVCH: the band where the AEM has essentially finished charging
 * and the surplus really is free, which is what the comment always claimed. It is kept
 * BELOW VOVCH for MEASUREMENT margin, not because charging tapers -- the AEM does not
 * taper, it hard-cuts: "If STO is fully charged, the DCDC converter is disabled to
 * prevent over-charging the storage element, and the SRC pin is set to high impedance"
 * (AEM10300 sec 8.3.2). The 250 mV of headroom is thinner than it looks: the reference
 * is +/-2% (-40..+85 C), so the worst-case arm point is ~4.49 V against a VOVCH whose
 * datasheet row carries NO min/max at all. BENCH (see TODO): confirm a real card in
 * strong sun actually reaches this. If it proves marginal, 4300 mV is still 92.5% of
 * VOVCH and buys back roughly double the tolerance headroom -- but do NOT drop back
 * toward 3300, which is not a fullness criterion at all. */
#define SWEEP_CAPS_FULL_MV 4400

/* Sun diary: bank lifetime whole-HOURS of strong sun (the SENSE_SUN_bm tell the poll
 * already reads) into EEPROM, so a card that lives on harvested light also records how
 * much light it has seen -- read out over UPDI, or surfaced in the NDEF later. Free:
 * no extra sensing (the sun flag is already in hand each poll), and the in-progress
 * hour is counted in RAM so EEPROM is written only once per banked hour (endurance-safe;
 * see sense_sun_tick). 1 = on; 0 = compile it out entirely. */
#define USE_SUN_DIARY      1

/* Thermal-abuse log: keep the lifetime MAX die temperature (deg C) in EEPROM -- the hot-car
 * supercap-degradation tell (see ../solar-glow-drh-design-notes.md sec 7 "Supercap thermal").
 * Uses the MCU's OWN sensor via a PULSED ADC read (no standing current, unlike the accel's
 * TEMP_EN), sampled every TEMP_SAMPLE_POLLS polls since abuse temps move over minutes; EEPROM
 * is written only on a NEW max, so after the first warm spell it essentially never writes.
 * Near-zero energy; runs even while face-down dormant (a baking stowed card is the point).
 * 1 = on. */
#define USE_TEMP_LOG       1
#define TEMP_SAMPLE_POLLS  64   /* polls between temp samples (64 s at POLL_PERIOD_S=1) */

/* Field "black box" -- the starvation companions to the max-temp heat log: the lowest TANK
 * voltage (STO) ever seen and the power-cycle (full-drain) count. (This line said "VS" until
 * the 2026-08-01 firmware audit -- a v3 leftover: on v4 VS is the constant LDO output, and the
 * code has always read STO here via sense_vdd_mv(), which is also the informative node -- VS
 * would log 3300 forever until terminal collapse.) Both near-free: vmin samples STO every
 * VMIN_SAMPLE_POLLS (the supercap sags over minutes) and writes EEPROM only on a new low; the
 * power-cycle count writes once per cold boot (POR). Together they answer "did this card fail from
 * heat, starvation, or overuse?" from one UPDI read. Runs even while face-down dormant. 1 = on. */
#define USE_HEALTH_LOG     1
#define VMIN_SAMPLE_POLLS  16   /* polls between rail-min samples (16 s at POLL_PERIOD_S=1) */

/* FRAM archival log (U7 MB85RC512TY, 64 KB on always-on VS, sleep-parked; driver in
 * fram.c). The internal-EEPROM loggers above are a 512 B black box; the FRAM is the
 * big-store companion for richer archival (per-event history, larger diaries). Left
 * HEADLESS (0) by default: the driver is built and ready, but the WHAT/WHEN of archival
 * is a policy tied to the unmeasured harvest budget (README "the open question") -- a
 * FRAM access now costs just a ~450 us wake + bus time. Set 1 to compile in the main.c
 * boot-record hook (a cold-boot counter) as the first archival user; expand from there
 * once the budget is measured. */
#define USE_FRAM_LOG       0

/* Defensive re-park of the VS-railed FRAM at the end of every poll tick. The
 * datasheet's Sleep-exit wording ("START + device address word") does not promise
 * ADDRESS-SELECTIVE wake, so each poll's accel traffic might drag U7 back to 10 uA
 * standby; re-issuing the 2-frame sleep sequence (~300 us, NACK-tolerant no-op if it
 * never woke) bounds the exposure to one poll. BENCH: if wake proves address-
 * selective, set 0 and rely on the sleeps already issued after each fram_* use. */
#define FRAM_RESLEEP_EVERY_POLL  1

/* charge floor: skip the glow (stay dark) below this rail voltage, mV.
 * Read via the STO divider channel (PD1/AIN1). Keeps a brown-out from bricking mid-animation.
 * EA re-derivation: the EA's BOD ladder has no 2.45 V level, so the fuse plan uses
 * BODLEVEL2 = 2.60 V typ falling (DS40002443 35.11); the floor keeps the DD design's
 * ~150 mV of glow-sag margin ABOVE the BOD trip -> 2600 + 150 = 2750. */
#define VS_GLOW_FLOOR_MV   2750

/* Brownout stretch: fade the glow as the reserve drains instead of a hard cliff at the
 * floor. Full brightness at/above VS_GLOW_FULL_MV, ramped down to VS_GLOW_DIM_PEAK as the
 * rail sags to VS_GLOW_FLOOR_MV, dark below it. In normal use (rail near the ~3.5 V clamp)
 * this is invisible -- it only bites once the reserve is genuinely low, where a dimmer
 * breath both reads gracefully and spends less charge, so more breaths fit before the
 * floor. Free: reuses the very rail read that already gates the glow (sense_glow_peak
 * replaces the sense_rail_ok gate). 1 = on; 0 = original hard cutoff at the floor.
 * VS_GLOW_FULL_MV is the full-bright knee (>= VS_GLOW_FLOOR_MV, <= the clamped rail);
 * VS_GLOW_DIM_PEAK is the floor brightness on GLOW_PEAK's 0..255 scale (bench-tunable). */
#define USE_BROWNOUT_STRETCH 1
#define VS_GLOW_FULL_MV      3000
#define VS_GLOW_DIM_PEAK     70

/* EEPROM write-safety floor, mV: the rail must be at/above this for firmware to START an EEPROM
 * write (EVERY writer honors it: the telemetry loggers -- min-rail, max-temp, power-cycle count --
 * and the tap tally, which banks taps in RAM below the floor and flushes on a later safe tap). A
 * Flash/EEPROM write on a
 * collapsing rail can corrupt (DS40002443 sec 11.3.3 "Preventing Flash/EEPROM Corruption"; the DD
 * documents the same window); the
 * hardware BOD only *aborts* a write already in progress, so this is the software "don't start a
 * write near the edge" guard -- the job the datasheet assigns to the VLM, done here so it holds
 * between the sampled BOD's checks (and even if the BOD is off). Set comfortably above the BOD level
 * (EA: 2.60 V at BODCFG=0x4A, BODLEVEL2 -- the ladder has no 2.45 V step) so a started ~4 ms write completes above it; the write's MCU-only load
 * -- and on Rev. B1 silicon this floor is also the erratum guard: DS80001048C 2.2.1 says NVM
 * erase/write below 2.7 V may simply FAIL, so 2.85 V is a functional requirement there, not
 * just corruption margin --
 * barely moves the 1 F rail, so the margin is ample. The lifetime-extreme loggers track their value
 * in RAM and only COMMIT here, so a recoverable sag/heat spell is still captured -- only a terminal
 * drain below this floor goes unrecorded, which is unavoidable (you cannot safely write EEPROM as the
 * rail collapses). Sits just above the 2.75 V glow floor, so if the card is healthy enough to have
 * been glowing, it is healthy enough to commit a log entry.
 * NODE NOTE (audit (d)): the hazards this floor is derived from are VDD-side -- NVM
 * corruption (11.3.3) and erratum 2.2.1's 2.7 V write floor are core-supply phenomena --
 * but the COMPARE is against STO (sense_vdd_mv reads the tank divider), a different node.
 * They coincide exactly where the guard matters: below ~3.3 V the TPS7A02 is in dropout,
 * so VDD tracks STO minus the dropout at the write's few-mA load (single-digit mV for
 * this part), and STO >= 2850 implies VDD >= ~2.84 V -- above both hazards. Above 3.3 V
 * the LDO regulates and VDD is a constant 3.3 V, so any STO that passes the gate implies
 * a healthy VDD trivially. The floor therefore guards the node the hazard actually lives
 * on across the whole range; it is only the LABEL ("rail") that is loose. */
#define EE_WRITE_FLOOR_MV  2850

/* wake-on-light threshold on VSENSE (= VIN/2), mV AT THE PIN (so the VIN node is 2x this).
 * ~0 in dark; well above that in any usable light. 400 mV at the pin = VIN 800 mV.
 * SOURCING CAVEAT (2026-07-26 audit): the "~1.2-2.1 V in light" range this line used to
 * assert is unsourced AND contradicts the range asserted for the SAME node in the
 * SWEEP_SUN_VIN_MV block above ("indoor VIN ~0.8-2.1 V") by about 3x once you account for
 * pin-vs-node. Neither figure has a measurement behind it. What IS sourced is the shape:
 * while the AEM is charging it holds SRC at 0.80 x Voc (R_MPP straps; see the
 * SWEEP_SUN_VIN_MV block), and Voc rises with illumination, so this threshold is a
 * genuine dark/light discriminator even though its exact trip point is a guess. Both
 * ranges are bench items; do not quote either as fact. */
#define LIGHT_THRESH_MV    400

/* baseline poll period (option B), seconds (RTC PIT). 1 or 2. */
#define POLL_PERIOD_S      1

/* power-on wink only fires with comfortable headroom above the glow floor,
 * so a freshly-charged-but-marginal card cannot wink itself back below the
 * floor (matters most if BOD is later enabled and the rail hovers near the
 * floor while charging). Set >= VS_GLOW_FLOOR_MV. */
#define WINK_FLOOR_MV      3000

/* watchdog: recover from an unexpected lockup on a fielded card. 1 = on.
 * Petted from the main loop (top) and from inside the animation naps (idle_nap_ms,
 * shared by led_breathe AND led_sweep), never from an ISR. Timeout (~8 s) must stay
 * well above POLL_PERIOD_S and the longest animation (the double-tap glow,
 * DTAP_CYCLES * DTAP_BREATH_MS ~ 4.8 s); the PIT wakes the loop every poll to pet it,
 * so power-down sleep never trips it. */
#define USE_WDT            1

/* Face-down dormant ("dead-man") mode: if the card lies FACE-DOWN (accel Z clearly
 * negative) continuously for FACEDOWN_DORMANT_S seconds, go dormant -- suppress every glow
 * (tap / motion / NFC-ack / greeting / sweep) until it is turned face-up again, so a stowed
 * card (face-down in a drawer, under papers) can't bleed the reserve on false-trigger
 * glows. Flipping it face-up resumes at once (the flip is motion, and the poll re-checks
 * orientation as a backstop). Net ENERGY WIN -- the only overhead is one accel Z read per
 * poll, dwarfed by the glows it suppresses; the passive RF vCard read is untouched (it is
 * hardware). 1 = on.
 *   FACEDOWN_Z_THRESH: face-down when ZDATA_8 < this. Signed, ~64 LSB/g, so -32 ~ -0.5 g.
 *   BENCH-CONFIRM THE SIGN: read Z with the card face-up -- it should be ~+64. If it reads
 *   ~-64, this board's accel has +Z pointing the other way; negate the byte in
 *   adxl367_read_z (do NOT just flip the threshold sign -- the compare direction matters). */
#define USE_FACEDOWN_DORMANT  1
#define FACEDOWN_DORMANT_S     180   /* seconds lying face-down before going dormant (~3 min) */
#define FACEDOWN_Z_THRESH      (-32) /* ZDATA_8 below this = face-down (~-0.5 g)              */
#define FACEDOWN_DORMANT_POLLS (FACEDOWN_DORMANT_S / POLL_PERIOD_S)   /* derived: polls, not seconds */

/* FACE-DOWN DEEP SLEEP -- turning face-down dormancy into the card's OFF SWITCH.
 *
 * Dormancy above already stops every glow. This takes the next step and drops the
 * standing draw too, so laying the card face-down is as close to "off" as a device
 * with no switch can get -- and turning it back over is the "on". A deliberate
 * physical gesture is a far better trigger than any inference: it is unambiguous,
 * the user already knows they did it, and it is instantly reversible. (It is the
 * trigger the deleted shipping-coma mode should have used; that one guessed from
 * 48 h of darkness, which is why it went.)
 *
 * Three levers, in descending order of what they are worth:
 *
 * 1. DROP THE FD PULL-UP (PA6). This is the big one, and it is bigger than the
 *    MCU's own sleep current. The FD block below documents the standing cost: the
 *    NT3H2211's FD pin leaks IL 1.5 uA typ / 10 uA MAX with FD high -- the card's
 *    dominant state -- and that current flows out of VS through PA6's internal
 *    pull-up essentially always, "+56% typ / +370% max against the README's
 *    ~2.7 uA dark-standby sum". Setting PA6 to INPUT_DISABLE removes the pull-up
 *    AND the input buffer, so the path simply is not there. Cost while face-down:
 *    no FD wake, so no NFC acknowledge glow (already suppressed by dormancy) and
 *    no DCDC quieting during a read. The vCard STILL READS -- that is RF and
 *    entirely hardware. So the only real loss is a slightly noisier read of a card
 *    lying face-down, which is not how anyone presents a card.
 * 2. ACCELEROMETER TO LOW POWER: 100 Hz -> 12.5 Hz and the tap engine off
 *    (adxl367_lowpower). Face-down, no tap can produce a glow, so running the tap
 *    detector is pure cost. ACTIVITY stays armed: it is flip-to-wake.
 * 3. SLOW THE POLL to FACEDOWN_POLL_S. Fewer wakes, and the only work left on a
 *    dormant tick is the orientation check plus the self-rate-limited loggers.
 *    Deliberately kept at or under the ~8 s watchdog period so the WDT STAYS
 *    ARMED -- the deleted coma disabled it, and a mode that turns off the
 *    watchdog to save power is a bad trade on a card you cannot power-cycle.
 *
 * WAKE: flipping face-up is motion, so INT2 fires and the motion branch re-reads
 * Z for an immediate wake; the (slower) poll re-checks orientation as a backstop,
 * bounding the worst case to FACEDOWN_POLL_S. Everything is restored on the way
 * out -- pull-up, interrupt, accel profile, poll rate.
 * The loggers keep running, just FACEDOWN_POLL_S/POLL_PERIOD_S times less often:
 * a card baking face-down in a hot car is still recorded, which is the point of
 * having them. 1 = on. */
#define USE_FACEDOWN_DEEPSLEEP 1
#define FACEDOWN_POLL_S        4     /* dormant poll period, s (<= the ~8 s WDT, so it stays armed) */

/* Deep sleep is a RIDER on face-down dormancy -- dormancy is what decides the card is
 * face-down and owns both transitions -- so it cannot mean anything on its own. Say so
 * at compile time rather than letting the knob sit there doing nothing (which is what
 * happened on the first build of this feature: with dormancy off the transition
 * function went uncalled and only -Werror's unused-function caught it). */
#if USE_FACEDOWN_DEEPSLEEP && !USE_FACEDOWN_DORMANT
#  error "USE_FACEDOWN_DEEPSLEEP needs USE_FACEDOWN_DORMANT: dormancy is what detects face-down and drives both transitions. Turn both off, or both on."
#endif

/* R1-R4 ballast power guard: clamp the glow duty when STO sits above GLOW_CLAMP_STO_MV.
 * The ballasts are AC0402FR-07150RL (0402, 1/16 W = 62.5 mW). Worst DC corner from the
 * PCB audit: STO 5.5 V (the supercap RATING -- the AEM's own VOVCH ceiling is 4.65 V, so
 * this corner needs an external/bench supply or abuse, never normal harvest), min-bin
 * Vf 1.9 V (LA P47F 3B bin), VOL ~0.4 V -> I ~21 mA -> ~68-70 mW at 100% duty = ~110%
 * of rating. PWM averages far below that in every shipped animation, so this clamp is
 * dormancy insurance, not a behavior change: above the threshold, peak duty is capped so
 * the worst-corner AVERAGE stays under rating (70 mW x 225/255 = 61.8 mW < 62.5 mW).
 * Applied inside sense_glow_peak(), the one chokepoint every glow's peak passes through
 * (main.c routes the sweep peak through it too). Free: the STO read is already in hand.
 * 1 = on. Alternative if the board is ever re-laid: 0402 -> 0603 (0.1 W) ballasts. */
#define USE_BALLAST_GUARD   1
#define GLOW_CLAMP_STO_MV   5200   /* above this STO, clamp duty (VOVCH 4.65 V never trips it) */
#define GLOW_CLAMP_PEAK     225    /* max peak while clamped: 70 mW x 225/255 < 62.5 mW rating  */

/* Dark-motion mute: suppress the MOTION soft-breath while the card is in the dark (the last poll
 * saw no light, VSENSE < LIGHT_THRESH) -- i.e. stowed in a pocket / bag. This closes a real carry-
 * drain: a charged card jostling in a dark pocket fires a ~1.6 s soft breath on every activity trip
 * and would empty the reserve on a long walk. The deliberate TAP is left untouched by THIS knob (its
 * branch never checks light; USE_DARK_DORMANT below rate-limits it, but never silences it), so the
 * monogram still lights when tapped in a dark room -- the marquee moment stays;
 * only the incidental motion breath is muted, and only when dark. Near-free (reuses the cached poll
 * light). Complements face-down dormant (which needs the card face-down; this works in any orientation
 * a pocket leaves it). 1 = on. (Distilled from Gemini's "sensory fusion": only auto-glow on motion when
 * there is light to see it in; always honor a tap.) */
#define USE_DARK_MOTION_MUTE  1

/* Dark dormant -- the face-down dormant's missing half (the feature ledger's "VSENSE-dark
 * in-a-bag/pocket co-condition"). Face-down dormancy needs the card face-DOWN; a card in a
 * bag or pocket rides in any orientation and never triggers it, and while the dark-motion
 * mute already silences the incidental MOTION breath there, a jostled bag can still
 * false-fire the TAP engine and glow into fabric, breath by breath. So: continuously dark
 * for DARK_DORMANT_S -> dark-dormant, which suppresses the MOTION and NFC-ack glows
 * outright and RATE-LIMITS the tap glow.
 *
 * THE TAP IS RATE-LIMITED, NEVER SILENCED. A tap always glows and always ends dormancy,
 * which then has to be re-earned by another DARK_DORMANT_S of continuous dark -- so a bag
 * walk glows at most once per ~30 min instead of once per jostle (essentially all of the
 * leak, closed) while a person tapping the card in a dark room ALWAYS gets the monogram.
 * This is deliberate and it replaced a stricter first cut (double-tap-to-escape) for a
 * reason: a mute would hang the card's PRIMARY interaction on LIGHT_THRESH_MV, a constant
 * this very file admits has no measurement behind it. If that guess reads a dim office as
 * dark, a single tap does nothing and the owner cannot tell why -- much worse than the few
 * stray breaths saved. A feature that can only cost energy may lean on an unmeasured
 * constant; one that can silence the product may not. Revisit the stricter mute only once
 * the bench has measured the real dark/light threshold.
 * Any poll that sees light exits dormancy, so a nightstand card is awake the moment morning
 * light lands (~1 poll) and the dark->light greeting still fires. Near-free: reuses the
 * poll's cached light bit, one counter. 1 = on. */
#define USE_DARK_DORMANT      1
#define DARK_DORMANT_S        1800  /* continuous dark before dark-dormant (~30 min) */
#define DARK_DORMANT_POLLS    (DARK_DORMANT_S / POLL_PERIOD_S)   /* derived: polls */

/* (No shipping/"coma" mode. It was built 2026-08-02 and removed the same day: the card is
 * hand-delivered, not boxed and shipped, so the dark-shipping-box premise the feature exists
 * for does not occur. Dark dormancy above covers the stowage case that DOES happen -- a bag,
 * a drawer, a pocket -- at a fraction of the machinery. The decision record, including what
 * the coma actually bought (~1.5-1.7x on box life, not 10x), is in feature-roadmap.md.) */

/* NFC-ack cooldown: rate-limit the field-leave acknowledge glow. The NT3H2211 FD pin (PA6) tracks
 * the reader's field, and a phone that sits in-field and keeps *polling* (its NFC discovery loop
 * pulses the RF carrier a few times a second) toggles FD on every pulse -- each rising edge would
 * otherwise fire a fresh ack breath. A phone parked face-down on top of the card (screen awake, NFC
 * on) could thus bleed the reserve one courtesy breath at a time. This gates the ack to at most one
 * per NFC_ACK_COOLDOWN_S: the first read still acks instantly, re-polls inside the window are muted.
 * The RF vCard read itself is hardware and untouched -- only the courtesy glow is rate-limited. The
 * rail floor already stops a brownout; this stops the wasteful bleed *to* the floor. Near-free: one
 * main-local byte, aged one count per poll tick. 1 = on.
 *   NFC_ACK_COOLDOWN_S should be >= POLL_PERIOD_S (else the derived poll count floors to 0 = no
 *   cooldown, a harmless no-op). A genuine second tap seconds later still acks; only rapid re-polls
 *   inside the window are dropped. */
#define USE_NFC_ACK_COOLDOWN   1
#define NFC_ACK_COOLDOWN_S     3
#define NFC_ACK_COOLDOWN_POLLS (NFC_ACK_COOLDOWN_S / POLL_PERIOD_S)   /* derived: polls, not seconds */

/* ---- AVR64EA Rev. B1 erratum 2.2.3 guard (DS80001048C, datasheets/) ----
 * On Rev. B1 silicon, an ST/STD/STS to any address >= 64 immediately followed
 * by a write to SLPCTRL.CTRLA LOSES the SLPCTRL write. A silently-dropped
 * sleep_enable()/mode select is exactly the failure this card can't afford:
 * a glow nap could leave the core parked in IDLE instead of Power-Down and
 * quietly burn the standby budget. Workaround per the errata sheet: one NOP
 * between the stores. Every SLPCTRL.CTRLA write in this tree goes through
 * these wrappers (use them, never the bare avr/sleep.h calls). The "memory"
 * clobber pins the NOP between the surrounding stores; on fixed Rev. B2 the
 * cost is one cycle. sleep_cpu() itself (the SLEEP opcode) doesn't write
 * SLPCTRL and needs no guard. */
#define EA_B1_NOP()      __asm__ __volatile__("nop" ::: "memory")
#define slp_set_mode(m)  do { EA_B1_NOP(); set_sleep_mode(m); } while (0)
#define slp_enable()     do { EA_B1_NOP(); sleep_enable();    } while (0)
#define slp_disable()    do { EA_B1_NOP(); sleep_disable();   } while (0)

#endif /* BOARD_H */
