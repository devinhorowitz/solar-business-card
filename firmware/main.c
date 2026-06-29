/*
 * main.c  --  SOLAR-GLOW DRH v2.1 firmware top level.
 *
 * Behaviour
 * ---------
 * The card sleeps in POWER-DOWN almost all the time. Four things wake it:
 *   - TAP      (LIS2DH12 click -> INT1 -> PF1, rising)  -> full breathing glow
 *   - MOTION   (LIS2DH12 inertial wake-up -> INT2 -> PF0, rising) -> one soft breath
 *   - NFC      (NT3H2211 field detect -> FD -> PA6, falling) -> the tap glow:
 *                a phone's RF field pulls FD low (NC_REG FD_ON=00b, the POR default)
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
 *   - the accel itself is the only "button"; there is no GPIO button in v2.1.
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
#include "lis2dh12.h"
#include "led.h"
#include "sense.h"
#include "nfc.h"

/* VIN threshold (mV) for "light present". LIGHT_THRESH_MV is defined at the
 * VSENSE pin (= VIN/2); sense_vin_mv() already returns VIN, so scale up. */
#define LIGHT_VIN_MV  ((uint16_t)(LIGHT_THRESH_MV * VSENSE_DIVIDER))

static volatile uint8_t f_tap;     /* PF1 click   */
static volatile uint8_t f_motion;  /* PF0 activity */
static volatile uint8_t f_tick;    /* RTC PIT     */
static volatile uint8_t f_nfc;     /* PA6 NFC field-detect (FD, field-powered) */

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
    PORTF.PIN0CTRL = PORT_ISC_RISING_gc;   /* INT2 / activity */
    PORTF.PIN1CTRL = PORT_ISC_RISING_gc;   /* INT1 / tap      */
    /* NFC power-gate enable on PA7 (NFC_EN, active-HIGH): drive LOW = NFC VCC off.
     * Set OUT low first, then DIR out, so the pin never glitches HIGH. VCC is only
     * powered transiently around an I2C access (nfc_power_on/off). */
    NFC_EN_PORT.OUTCLR = NFC_EN_PIN_bm;
    NFC_EN_PORT.DIRSET = NFC_EN_PIN_bm;
    /* NFC field-detect on PA6: input, falling-edge sense. FD is field-powered
     * (datasheet 8.4), so it wakes us on a phone tap even with NFC VCC gated off;
     * the chip's POR/config default already pulls FD low on field-present, so no
     * I2C setup is needed. FD is open-drain with an external 10k (R13) to VS; we
     * ALSO enable PA6's internal pull-up as belt-and-suspenders so the pin can't
     * float (covers a marginal R13, or R13 tied to the switched rail), at the cost
     * of a little extra sink only while FD is held low (i.e. during a tap). */
    FD_PORT.PIN6CTRL = PORT_ISC_FALLING_gc | PORT_PULLUPEN_bm;
    /* PD2 (VSENSE) is analog only: disable its digital input buffer so the
     * Schmitt trigger doesn't toggle (and burn current) on a slow mid-rail
     * analog level. ADC/AC read the analog path regardless of this bit. */
    PORTD.PIN2CTRL = PORT_ISC_INPUT_DISABLE_gc;
    /* LED pins + TCA routing are owned by led_init(); I2C pins by PORTMUX below. */
    PORTMUX.TWIROUTEA = PORTMUX_TWI0_ALT2_gc;   /* SDA=PC2, SCL=PC3 */
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

    clocks_init();        /* 1. clocks / power            */
    gpio_init();          /* 2. GPIO / PORTMUX            */
    led_init();
    sense_adc_init();

    twi_init();           /* 3. I2C up, talk to the accel */
    (void)lis2dh12_present();      /* WHO_AM_I sanity (ignored if bus dead) */
    (void)lis2dh12_init_tap();     /* tap->INT1, activity->INT2             */

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

    for (;;) {
#if USE_WDT
        wdt_reset();      /* pet from the loop top: a wedged main loop (even one
                           * still taking interrupts) stops petting -> reset. */
#endif
        if (f_tap) {
            f_tap = 0;
            uint8_t dbl = 0;
#if USE_DOUBLE_TAP
            /* Resolve single vs double BEFORE glowing: idle-wait the window so a
             * second tap can land, then read CLICK_SRC once (this also clears the
             * latch). Reading only after the window avoids disturbing the accel's
             * in-progress double-click timing. */
            led_wait_ms(DTAP_WINDOW_MS);
            dbl = (lis2dh12_read_click() & LIS_CLICK_DCLICK_bm) != 0;
#else
            lis2dh12_clear_click();              /* drop the latched INT1 */
#endif
            if (sense_rail_ok()) {
                /* tally BEFORE the glow: the EEPROM write then happens at the
                 * higher pre-glow rail, not after the glow has sagged it. The
                 * ~13 ms write is imperceptible ahead of the animation. */
                sense_count_inc();
                if (dbl)
                    led_breathe(DTAP_CYCLES, DTAP_BREATH_MS, DTAP_PEAK);  /* signature */
                else
                    led_breathe(GLOW_CYCLES, GLOW_BREATH_MS, GLOW_PEAK);
            }
            prev_light = (sense_vin_mv() >= LIGHT_VIN_MV);
            /* a tap is also motion (and, if a phone caused it, a field event), so
             * INT2 and/or FD likely fired too. Clear both here (after the glow) so
             * the next loop does not chase the tap with a redundant breath or glow. */
            f_motion = 0;
            f_nfc = 0;
        }
        else if (f_nfc) {
            f_nfc = 0;
            /* a phone's field woke us via FD (the tag's VCC stays gated off; FD runs
             * on field power). Same glow as a single accel tap, rail-gated. The phone
             * also jostles the card, so the accel motion int likely set f_motion too
             * -- clear it after so we don't chase this with a soft breath. (Deliberately
             * NOT counted by sense_count_inc(): that tracks physical taps; move it here
             * if you'd rather count every interaction.) */
            if (sense_rail_ok())
                led_breathe(GLOW_CYCLES, GLOW_BREATH_MS, GLOW_PEAK);
            f_motion = 0;
        }
        else if (f_motion) {
            f_motion = 0;
            if (sense_rail_ok())
                led_breathe(1, GLOW_BREATH_MS, (uint8_t)(GLOW_PEAK / 2));
            /* motion int (IA2) is not latched; nothing to clear */
        }
        else if (f_tick) {
            f_tick = 0;
            uint8_t light = (sense_vin_mv() >= LIGHT_VIN_MV);
            if (light && !prev_light && sense_rail_ok())
                led_breathe(GLOW_CYCLES, GLOW_BREATH_MS, GLOW_PEAK);   /* dark->light edge */
            prev_light = light;
        }

        go_to_sleep();
    }
}

/* ---------------- ISRs ---------------- */

/* accel interrupts share PORTF: PF1 = tap, PF0 = activity. */
ISR(PORTF_PORT_vect)
{
    uint8_t fl = PORTF.INTFLAGS;
    if (fl & ACC_INT1_bm) f_tap = 1;       /* PF1 */
    if (fl & ACC_INT2_bm) f_motion = 1;    /* PF0 */
    PORTF.INTFLAGS = fl;                   /* write-1-to-clear */
}

/* NFC field-detect on PA6 (PORTA pin-interrupt vector). A phone's RF field pulls
 * FD low (FD_ON=00b, field-present); FD is field-powered, so this fires even with
 * the tag's VCC gated off. Wakes the core from Power-Down. */
ISR(PORTA_PORT_vect)
{
    uint8_t fl = PORTA.INTFLAGS;
    if (fl & FD_PIN_bm) f_nfc = 1;
    PORTA.INTFLAGS = fl;                   /* write-1-to-clear */
}

ISR(RTC_PIT_vect)
{
    RTC.PITINTFLAGS = RTC_PI_bm;
    f_tick = 1;
}
