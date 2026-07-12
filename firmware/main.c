/*
 * main.c  --  SOLAR-GLOW DRH v3.0 firmware top level.
 *
 * Behaviour
 * ---------
 * The card sleeps in POWER-DOWN almost all the time. Four things wake it:
 *   - TAP      (ADXL367 tap -> INT1 -> PF0, rising)      -> full breathing glow
 *   - MOTION   (ADXL367 activity -> INT2 -> PF1, rising) -> one soft breath
 *   - NFC      (NT3H2211 field detect -> FD -> PA6, both edges) -> while the reader's
 *                field is present the LEDs are held dark (a clean 13.56 MHz band for the
 *                tag's reply) and the core stays quiet; the acknowledge glow fires when
 *                the field leaves (FD rising), rate-limited by USE_NFC_ACK_COOLDOWN so a
 *                parked, re-polling phone can't bleed the reserve breath by breath
 *   - PIT tick (RTC, ~1 s, runs in power-down)          -> sample light, and
 *                if we just crossed dark->light, do a glow
 * All of these pin interrupts sense fully asynchronously, so they wake the core
 * even with CLK_PER stopped (datasheet 18.3.3.1).
 *
 * The NFC tag (NT3H2211) is power-gated by NFC_EN (PA7) and OFF by default to kill
 * its ~195 uA idle draw; VCC is only switched on around an I2C access (provisioning).
 * FD-wake still works while VCC is gated off: the FD pin is operated from the
 * phone's own field power (datasheet 8.4), so a tap pulls PA6 low with the chip's
 * VCC off, and field-present is the chip's POR/config default (no I2C setup needed).
 * A phone also reads the static vCard via RF with VCC off.
 *
 * Every glow is gated by the rail-voltage floor: if the supercap is below
 * VS_GLOW_FLOOR_MV we stay dark and let it charge, so an animation can never
 * brown the part out mid-breath.
 *
 * Two hardware gates are invisible to this code and documented in the README:
 *   - SW2 (master anode switch): OFF -> no LED current, no matter what TCA does.
 *   - the accel itself is the only "button"; there is no GPIO button in v3.0.
 *
 * Bring-up order below follows hardware doc section 7 exactly.
 */
#include <avr/io.h>
#include <avr/interrupt.h>
#include <avr/sleep.h>
#include <avr/cpufunc.h>
#include <avr/wdt.h>      /* wdt_reset() == WDR; enable is via WDT.CTRLA below */

#include "board.h"
#include "twi.h"
#include "adxl367.h"
#include "led.h"
#include "sense.h"
#include "nfc.h"

static volatile uint8_t f_tap;     /* PF0 click   */
static volatile uint8_t f_motion;  /* PF1 activity */
static volatile uint8_t f_tick;    /* RTC PIT     */
static volatile uint8_t f_nfc;     /* PA6 NFC field-detect (FD, field-powered) */

#if USE_FACEDOWN_DORMANT
/* face-down dormant state (main-context only, not shared with any ISR -> no volatile).
 * dormant = every glow suppressed until turned face-up; facedown_polls = consecutive
 * face-down polls counted toward FACEDOWN_DORMANT_POLLS. */
static uint8_t  dormant;
static uint16_t facedown_polls;
#endif

/* ---------------- init ---------------- */

static void clocks_init(void)
{
    /* internal OSCHF at 1 MHz, no prescaler -> F_CPU = 1 MHz. Chosen over 4 MHz
     * to trim active current: the core only runs in brief bursts (it sleeps
     * through the glow), so a slower clock costs nothing noticeable here while
     * lowering the per-burst draw. Running OSCHF itself at 1 MHz draws less than
     * 4 MHz-plus-prescaler, so set the oscillator low rather than dividing. */
    _PROTECTED_WRITE(CLKCTRL.OSCHFCTRLA, CLKCTRL_FRQSEL_1M_gc);
    _PROTECTED_WRITE(CLKCTRL.MCLKCTRLB, 0);          /* prescaler off (PEN = 0) */
    /* voltage regulator: power-saving in deep sleep (doc section 7 step 1) */
    _PROTECTED_WRITE(SLPCTRL.VREGCTRL, SLPCTRL_PMODE_AUTO_gc);
}

static void gpio_init(void)
{
    /* accel interrupt inputs on PF0/PF1: input (default), rising-edge sense.
     * INT pads are push-pull active-high, so no pull resistor. */
    PORTF.PIN0CTRL = PORT_ISC_RISING_gc;   /* INT1 / tap      */
    PORTF.PIN1CTRL = PORT_ISC_RISING_gc;   /* INT2 / activity */
    /* NFC power-gate enable on PA7 (NFC_EN, active-HIGH): drive LOW = NFC VCC off.
     * Set OUT low first, then DIR out, so the pin never glitches HIGH. VCC is only
     * powered transiently around an I2C access (nfc_power_on/off). */
    NFC_EN_PORT.OUTCLR = NFC_EN_PIN_bm;
    NFC_EN_PORT.DIRSET = NFC_EN_PIN_bm;
    /* NFC field-detect on PA6: input, BOTH-edges sense. FD is field-powered
     * (datasheet 8.4), so it wakes us even with NFC VCC gated off; the chip's
     * POR/config default already pulls FD low on field-present, so no I2C setup is
     * needed. Both edges because we act on each: FALLING (field arrives) -> the LED
     * layer blanks and the core goes quiet for the read; RISING (field leaves) ->
     * fire the acknowledge glow. FD is open-drain with an external 10k (R13) to VS;
     * we ALSO enable PA6's internal pull-up as belt-and-suspenders so the pin can't
     * float, at the cost of a little extra sink only while FD is held low. */
    FD_PORT.PIN6CTRL = PORT_ISC_BOTHEDGES_gc | PORT_PULLUPEN_bm;
    /* PD2 (VSENSE) is analog only: disable its digital input buffer so the
     * Schmitt trigger doesn't toggle (and burn current) on a slow mid-rail
     * analog level. ADC/AC read the analog path regardless of this bit. */
    PORTD.PIN2CTRL = PORT_ISC_INPUT_DISABLE_gc;
    /* LED pins + TCA routing are owned by led_init(); I2C pins by PORTMUX below. */
    PORTMUX.TWIROUTEA = PORTMUX_TWI0_ALT2_gc;   /* SDA=PC2, SCL=PC3 */

    /* Tie down every unused pin. A floating CMOS input draws shoot-through current
     * in its buffer whenever it drifts near mid-rail; a pull-up holds it high at ~0
     * current (and for PA5, the reserved button to GND, and the JP2 breakouts, that
     * is also the useful resting state). The pins configured above (PA6/PA7/PD2/PF0/
     * PF1) and the LED pins (PA0-3, in led_init) are left alone; a pull-up bit on a
     * driven output is ignored anyway. Writes to PORTD pins not bonded on the 28-pin
     * package are harmless. */
    PORTA.PIN4CTRL = PORT_PULLUPEN_bm;   /* PA4 spare (JP2.1)   */
    PORTA.PIN5CTRL = PORT_PULLUPEN_bm;   /* PA5 reserved button */
    PORTC.PIN0CTRL = PORT_PULLUPEN_bm;   /* PC0 spare (JP2.2)   */
    PORTC.PIN1CTRL = PORT_PULLUPEN_bm;   /* PC1 spare (JP2.3)   */
    PORTD.PIN0CTRL = PORT_PULLUPEN_bm;   /* PD0/1/3-7 unused    */
    PORTD.PIN1CTRL = PORT_PULLUPEN_bm;
    PORTD.PIN3CTRL = PORT_PULLUPEN_bm;
    PORTD.PIN4CTRL = PORT_PULLUPEN_bm;
    PORTD.PIN5CTRL = PORT_PULLUPEN_bm;
    PORTD.PIN6CTRL = PORT_PULLUPEN_bm;
    PORTD.PIN7CTRL = PORT_PULLUPEN_bm;
}

static void rtc_pit_init(void)
{
    /* 1.024 kHz internal ULP clock (runs in power-down). Period from the
     * POLL_PERIOD_S knob so the config actually takes effect. */
    RTC.CLKSEL = RTC_CLKSEL_OSC1K_gc;
    while (RTC.PITSTATUS & RTC_CTRLBUSY_bm) { }
    RTC.PITINTCTRL = RTC_PI_bm;
#if   POLL_PERIOD_S == 1
    RTC.PITCTRLA = RTC_PERIOD_CYC1024_gc | RTC_PITEN_bm;   /* 1024 / 1.024 kHz = 1.0 s */
#elif POLL_PERIOD_S == 2
    RTC.PITCTRLA = RTC_PERIOD_CYC2048_gc | RTC_PITEN_bm;   /* 2048 / 1.024 kHz = 2.0 s */
#else
#  error "POLL_PERIOD_S must be 1 or 2 (RTC PIT poll period, seconds)."
#endif
}

/* ---------------- sleep ---------------- */

static void go_to_sleep(void)
{
    /* NFC_EN MUST be LOW before any sleep: cut the tag's VCC so it cannot draw its
     * ~195 uA across the sleep. (After provisioning it is already off; this is the
     * hard guarantee of the invariant.) */
    nfc_power_off();
    /* Power-Down is the baseline: lowest current. It still wakes on the accel pin
     * interrupts and the RTC PIT -- and on FD (PA6), which the phone's field drives
     * even though we just cut the tag's VCC (FD is field-powered, datasheet 8.4). */
    set_sleep_mode(SLEEP_MODE_PWR_DOWN);
    cli();
    if (!f_tap && !f_motion && !f_tick && !f_nfc) {
        sleep_enable();
        sei();              /* SEI + SLEEP is atomic: a pending IRQ runs after SLEEP, no missed wake */
        sleep_cpu();
        sleep_disable();
    } else {
        sei();
    }
}

/* ---------------- main ---------------- */

int main(void)
{
    uint8_t prev_light = 0;
#if USE_NFC_ACK_COOLDOWN
    uint8_t nfc_cooldown = 0;   /* polls remaining before another NFC-ack glow may fire (0 = ready) */
#endif

    clocks_init();        /* 1. clocks / power            */
    gpio_init();          /* 2. GPIO / PORTMUX            */
    led_init();
    sense_adc_init();
#if USE_HEALTH_LOG
    sense_boot_log();     /* black box: +1 the power-cycle count if this was a cold power-on (POR) */
#endif

    twi_init();           /* 3. I2C up, talk to the accel */
    (void)adxl367_init_tap();      /* full accel config; validates DEVID after its soft reset */

    /* 4. NFC tag (shares the bus) is power-gated OFF by default; we do not touch it
     * at boot. FD-wake needs no setup -- it runs on field power and the chip's POR
     * default already pulls FD low on field-present. Provisioning, when enabled,
     * powers VCC on for the write and back off after (nfc_provision_default). */
#if NFC_PROVISION
    (void)nfc_provision_default();   /* one-shot NDEF write; self-powers the tag */
#endif

    rtc_pit_init();       /* 5/6. baseline poll + housekeeping clock */

    /* the accel INT lines were indeterminate until configured just above; drop
     * any edge they may have latched into PORTF before we arm interrupts. Same for
     * any FD edge on PORTA (PA6). */
    PORTF.INTFLAGS = ACC_INT1_bm | ACC_INT2_bm;
    FD_PORT.INTFLAGS = FD_PIN_bm;
    f_tap = f_motion = f_tick = f_nfc = 0;

#if USE_WDT
    /* arm the watchdog last, once the slow bring-up (I2C config) is done so it
     * cannot trip during init. CTRLA is CCP-protected. ~8 s >> poll and glow. */
    _PROTECTED_WRITE(WDT.CTRLA, WDT_PERIOD_8KCLK_gc);
    wdt_reset();
#endif

    sei();

    /* power-on wink so a freshly programmed card shows life. Gated on a margin
     * above the glow floor (WINK_FLOOR_MV), not the floor itself, so a marginal
     * just-charged card cannot wink itself back below the floor. */
    if (sense_vdd_mv() >= WINK_FLOOR_MV)
        led_breathe(1, GLOW_BREATH_MS, GLOW_PEAK);

    /* seed the dark->light detector with the actual boot light level, so a card
     * powered on already in light does not fire a phantom dark->light glow on the
     * first PIT tick (the wink above is the only intended power-on glow). */
    prev_light = sense_light();

    for (;;) {
#if USE_WDT
        wdt_reset();      /* pet from the loop top: a wedged main loop (even one
                           * still taking interrupts) stops petting -> reset. */
#endif
        if (f_tap) {
            f_tap = 0;
            uint8_t dbl = 0;
#if USE_DOUBLE_TAP
            /* The ADXL367 resolves single vs double IN HARDWARE: with both tap
             * functions enabled, the tap interrupt fires only after the double-tap
             * window has validated or invalidated, so we read STATUS_2 once here with
             * no software wait. TAP_TWO set = double. The read clears + re-arms. */
            dbl = (adxl367_read_tap() & ADXL_STATUS2_TAP_TWO_bm) != 0;
#else
            adxl367_clear_tap();                 /* drop the tap latch */
#endif
            uint8_t peak = sense_glow_peak(dbl ? DTAP_PEAK : GLOW_PEAK);
#if USE_FACEDOWN_DORMANT
            if (dormant) peak = 0;   /* face-down: suppress the glow + tally (latches still acked below) */
#endif
            if (peak) {
                /* tally BEFORE the glow: the EEPROM write then happens at the
                 * higher pre-glow rail, not after the glow has sagged it. The
                 * ~13 ms write is imperceptible ahead of the animation. peak is the
                 * rail-scaled brightness (brownout stretch), 0 below the floor. */
                sense_count_inc();
                if (dbl)
                    led_breathe(DTAP_CYCLES, DTAP_BREATH_MS, peak);  /* signature */
                else
                    led_breathe(GLOW_CYCLES, GLOW_BREATH_MS, peak);
            }
            prev_light = sense_light();
            /* a tap is also motion (and, if a phone caused it, a field event), so
             * INT2 and/or FD likely fired too. Clear both here (after the glow) so
             * the next loop does not chase the tap with a redundant breath or glow. */
            f_motion = 0;
            f_nfc = 0;
            adxl367_clear_activity();   /* a tap likely tripped activity too; ack INT2 */
        }
        else if (f_nfc) {
            f_nfc = 0;
            /* the reader's field just LEFT (FD rose): the exchange is done, so it is
             * now safe to light up. Acknowledge the read with the same breath as a
             * single tap, rail-gated. During the read the LEDs were held dark (led.c
             * blanks while FD is low) and the core stayed asleep, keeping the 13.56 MHz
             * band clean for the tag's load-modulation. The phone also jostles the card,
             * so the accel motion int likely set f_motion too -- clear it after so we
             * don't chase this with a soft breath. (Deliberately NOT counted by
             * sense_count_inc(): that tracks physical taps; move it here to count reads.) */
            uint8_t peak = sense_glow_peak(GLOW_PEAK);
#if USE_FACEDOWN_DORMANT
            if (dormant) peak = 0;   /* face-down: no acknowledge glow */
#endif
#if USE_NFC_ACK_COOLDOWN
            /* rate-limit: a phone parked in-field keeps polling and re-toggling FD; ack at most
             * once per NFC_ACK_COOLDOWN_S so a stowed re-poll can't bleed the reserve breath by
             * breath. The cooldown is armed only on an ack that actually fired (below). */
            if (nfc_cooldown) peak = 0;
#endif
            if (peak) {
                led_breathe(GLOW_CYCLES, GLOW_BREATH_MS, peak);
#if USE_NFC_ACK_COOLDOWN
                nfc_cooldown = NFC_ACK_COOLDOWN_POLLS;   /* arm only when we actually acked */
#endif
            }
            f_motion = 0;
            adxl367_clear_activity();
        }
        else if (f_motion) {
            f_motion = 0;
            uint8_t peak = sense_glow_peak((uint8_t)(GLOW_PEAK / 2));
#if USE_FACEDOWN_DORMANT
            if (dormant) {
                /* motion while dormant may be the flip back face-up: re-check Z now for an
                 * instant wake (the ~1 s poll is only a backstop). No glow on the wake
                 * motion itself either way. */
                if (adxl367_read_z() >= FACEDOWN_Z_THRESH) { dormant = 0; facedown_polls = 0; }
                peak = 0;
            }
#endif
#if USE_DARK_MOTION_MUTE
            /* Stowed in the dark (last poll saw no light): mute the *motion* soft-breath so a card
             * jostling in a pocket/bag on a walk can't fire a breath per activity trip and bleed the
             * reserve. A deliberate TAP is untouched (its branch never checks light), so the monogram
             * still lights when tapped in a dark room -- the marquee moment stays. */
            if (!prev_light)
                peak = 0;
#endif
            if (peak)
                led_breathe(1, GLOW_BREATH_MS, peak);
            adxl367_clear_activity();   /* ADXL367 activity latches; read STATUS to ack INT2 */
        }
        else if (f_tick) {
            f_tick = 0;
#if USE_NFC_ACK_COOLDOWN
            if (nfc_cooldown) nfc_cooldown--;   /* age the NFC-ack rate-limit on the poll tick (~1 s) */
#endif
#if USE_TEMP_LOG
            /* lifetime max die temp -- self-rate-limited (samples every TEMP_SAMPLE_POLLS)
             * and writes EEPROM only on a new max. Before the dormancy gate on purpose, so a
             * baking face-down card is still logged. */
            sense_temp_log();
#endif
#if USE_HEALTH_LOG
            /* black box: lowest rail ever (RAM-tracked, committed to EEPROM only from a healthy rail)
             * plus the deferred power-cycle count. Before the dormancy gate, so a quietly-starving
             * stowed card is still tracked. Both defer their EEPROM write off a low/collapsing rail so
             * it can't corrupt (DS40002315 sec 11.3.3). */
            sense_vmin_tick();
            sense_boot_commit();   /* write a boot-flagged power cycle once the rail has charged past the write floor */
#endif
#if USE_FACEDOWN_DORMANT
            /* orientation watch. Accumulate face-down time and go dormant past the timer;
             * clear dormancy once face-up (a backstop to the motion-driven wake). While
             * dormant, skip all light/glow/sun work below -- just watch for face-up. */
            uint8_t skip = 0;
            int8_t z = adxl367_read_z();
            if (dormant) {
                if (z >= FACEDOWN_Z_THRESH) { dormant = 0; facedown_polls = 0; }
                skip = 1;                                    /* resume normal work next poll */
            } else if (z < FACEDOWN_Z_THRESH) {
                if (++facedown_polls >= FACEDOWN_DORMANT_POLLS) { dormant = 1; skip = 1; }
            } else {
                facedown_polls = 0;
            }
            if (!skip)
#endif
            {
                uint8_t vf    = sense_vin_flags();               /* one VSENSE read -> light + sun */
                uint8_t light = (vf & SENSE_LIGHT_bm) ? 1u : 0u;
#if USE_SUN_DIARY
                /* bank strong-sun time -- free: the sun tell is already in vf. Independent of
                 * the glow logic below, so it also counts the greeting-edge poll. EEPROM is
                 * only written once per banked hour (sense_sun_tick handles the wear policy). */
                if (vf & SENSE_SUN_bm)
                    sense_sun_tick();
#endif
                if (light && !prev_light) {
                    uint8_t peak = sense_glow_peak(GLOW_PEAK);            /* rail-scaled (brownout stretch) */
                    if (peak)
                        led_breathe(GLOW_CYCLES, GLOW_BREATH_MS, peak);  /* dark->light greeting */
                }
#if USE_SUN_SWEEP
                /* Already lit and basking: strong sun (VIN past the clamp) with the caps full ->
                 * play the "loading" sweep. Caps-full (sense_caps_full()) is the hard gate, so it
                 * can never draw the pack down; it re-arms each poll, looping while the sun holds
                 * and spending the clamp's excess as light instead of Q1 heat. The greeting above
                 * wins on the entry edge (one breath in), then this runs while the card sits. */
                else if ((vf & SENSE_SUN_bm) && sense_caps_full())
                    led_sweep(SWEEP_PASSES, SWEEP_PASS_MS, SWEEP_PEAK, SWEEP_OVERLAP);
#endif
                prev_light = light;
            }
        }

        go_to_sleep();
    }
}

/* ---------------- ISRs ---------------- */

/* accel interrupts share PORTF: PF0 = tap, PF1 = activity. */
ISR(PORTF_PORT_vect)
{
    uint8_t fl = PORTF.INTFLAGS;
    if (fl & ACC_INT1_bm) f_tap = 1;       /* PF0 */
    if (fl & ACC_INT2_bm) f_motion = 1;    /* PF1 */
    PORTF.INTFLAGS = fl;                   /* write-1-to-clear */
}

/* NFC field-detect on PA6 (PORTA pin-interrupt vector), both edges. FD is field-
 * powered (datasheet 8.4), so this fires even with the tag's VCC gated off, and
 * wakes the core from Power-Down. We flag f_nfc only on the RISING edge (field
 * gone) to schedule the post-read acknowledge glow. A FALLING edge (field present)
 * sets no flag -- it just wakes the core so an in-flight breath can blank (led.c
 * reads FD live) and the loop falls back to sleep, keeping the MCU quiet for the read. */
ISR(PORTA_PORT_vect)
{
    uint8_t fl = PORTA.INTFLAGS;
    if (fl & FD_PIN_bm) {
        if (FD_PORT.IN & FD_PIN_bm) f_nfc = 1;   /* pin high now = rising = field left */
    }
    PORTA.INTFLAGS = fl;                   /* write-1-to-clear */
}

ISR(RTC_PIT_vect)
{
    RTC.PITINTFLAGS = RTC_PI_bm;
    f_tick = 1;
}
