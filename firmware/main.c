/*
 * main.c  --  SOLAR-GLOW DRH v2.1 firmware top level.
 *
 * Behaviour
 * ---------
 * The card sleeps in POWER-DOWN almost all the time. Three things wake it:
 *   - TAP      (LIS2DH12 click -> INT1 -> PF1, rising)  -> full breathing glow
 *   - MOTION   (LIS2DH12 activity -> INT2 -> PF0, rising) -> one soft breath
 *   - PIT tick (RTC, ~1 s, runs in power-down)          -> sample light, and
 *                if we just crossed dark->light, do a glow
 * All PORT pins sense fully asynchronously, so the rising-edge accel
 * interrupts wake the core even with CLK_PER stopped (datasheet 18.3.3.1).
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

#include "board.h"
#include "twi.h"
#include "lis2dh12.h"
#include "led.h"
#include "sense.h"

/* VIN threshold (mV) for "light present". LIGHT_THRESH_MV is defined at the
 * VSENSE pin (= VIN/2); sense_vin_mv() already returns VIN, so scale up. */
#define LIGHT_VIN_MV  ((uint16_t)(LIGHT_THRESH_MV * VSENSE_DIVIDER))

static volatile uint8_t f_tap;     /* PF1 click   */
static volatile uint8_t f_motion;  /* PF0 activity */
static volatile uint8_t f_tick;    /* RTC PIT     */

/* ---------------- init ---------------- */

static void clocks_init(void)
{
    /* internal OSCHF at 4 MHz, no prescaler -> F_CPU = 4 MHz */
    _PROTECTED_WRITE(CLKCTRL.OSCHFCTRLA, CLKCTRL_FRQSEL_4M_gc);
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
    /* PD2 (VSENSE) is analog only: disable its digital input buffer so the
     * Schmitt trigger doesn't toggle (and burn current) on a slow mid-rail
     * analog level. ADC/AC read the analog path regardless of this bit. */
    PORTD.PIN2CTRL = PORT_ISC_INPUT_DISABLE_gc;
    /* LED pins + TCA routing are owned by led_init(); I2C pins by PORTMUX below. */
    PORTMUX.TWIROUTEA = PORTMUX_TWI0_ALT2_gc;   /* SDA=PC2, SCL=PC3 */
}

static void rtc_pit_init(void)
{
    /* 1.024 kHz internal ULP clock (runs in power-down). CYC1024 -> 1.0 s. */
    RTC.CLKSEL = RTC_CLKSEL_OSC1K_gc;
    while (RTC.PITSTATUS & RTC_CTRLBUSY_bm) { }
    RTC.PITINTCTRL = RTC_PI_bm;
    RTC.PITCTRLA   = RTC_PERIOD_CYC1024_gc | RTC_PITEN_bm;
}

/* ---------------- sleep ---------------- */

static void go_to_sleep(void)
{
    /* Power-Down is the baseline: lowest current, and it still wakes on the
     * accel pin interrupts (async, all sense modes) and the RTC PIT. */
    set_sleep_mode(SLEEP_MODE_PWR_DOWN);
    cli();
    if (!f_tap && !f_motion && !f_tick) {
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

    rtc_pit_init();       /* 5/6. baseline poll + housekeeping clock */

    /* the accel INT lines were indeterminate until configured just above; drop
     * any edge they may have latched into PORTF before we arm interrupts. */
    PORTF.INTFLAGS = ACC_INT1_bm | ACC_INT2_bm;
    f_tap = f_motion = f_tick = 0;

    sei();

    /* power-on wink so a freshly programmed card shows life (if rail allows) */
    if (sense_rail_ok())
        led_breathe(1, GLOW_BREATH_MS, GLOW_PEAK);

    for (;;) {
        if (f_tap) {
            f_tap = 0;
            if (sense_rail_ok()) {
                led_breathe(GLOW_CYCLES, GLOW_BREATH_MS, GLOW_PEAK);
                sense_count_inc();           /* lifetime activation tally */
            }
            lis2dh12_clear_click();          /* drop the latched INT1 */
            prev_light = (sense_vin_mv() >= LIGHT_VIN_MV);
        }
        else if (f_motion) {
            f_motion = 0;
            if (sense_rail_ok())
                led_breathe(1, GLOW_BREATH_MS, (uint8_t)(GLOW_PEAK / 2));
            /* activity int is not latched; nothing to clear */
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

ISR(RTC_PIT_vect)
{
    RTC.PITINTFLAGS = RTC_PI_bm;
    f_tick = 1;
}
