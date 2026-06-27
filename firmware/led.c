/*
 * led.c  --  TCA0 split-mode PWM + breathing animation.
 *
 * TCA0 split mode gives six 8-bit PWM channels off one timer. We use four:
 *   WO0 = LCMP0  -> PA0 (LDRV1, D2)
 *   WO1 = LCMP1  -> PA1 (LDRV2, D3)
 *   WO2 = LCMP2  -> PA2 (LDRV3, D4)
 *   WO3 = HCMP0  -> PA3 (LDRV4, D5)
 * LPER = HPER = 255, CLKSEL = DIV1 -> ~15.6 kHz at F_CPU 4 MHz (flicker-free,
 * above the audible band). PORTMUX.TCAROUTEA = PORTA is the default but is set
 * explicitly so the routing is self-documenting.
 *
 * Brightness math: duty is written straight to the compare register. With pad
 * INVEN on (see led_init), compare 0 -> pad parked HIGH -> LED off; compare
 * 255 -> pad mostly LOW -> LED full (ballast-limited). Monotonic and intuitive.
 */
#include <avr/io.h>
#include <avr/interrupt.h>
#include <avr/sleep.h>
#include <avr/wdt.h>
#include "board.h"
#include "led.h"

/* perceptual ramp: output ~ input^2, keeps the "breath" from looking
 * top-heavy to the eye without floats or a big LUT. in/out 0..255. */
static inline uint8_t gamma2(uint8_t v)
{
    uint16_t s = (uint16_t)v * (uint16_t)v;   /* 0..65025 */
    return (uint8_t)(s >> 8);                 /* /256 -> 0..254 */
}

void led_init(void)
{
    /* drive the four LED pins; invert at the pad so bigger duty = brighter */
    LED_PORT.DIRSET = LED_ALL_bm;
    PORTA.PIN0CTRL |= PORT_INVEN_bm;
    PORTA.PIN1CTRL |= PORT_INVEN_bm;
    PORTA.PIN2CTRL |= PORT_INVEN_bm;
    PORTA.PIN3CTRL |= PORT_INVEN_bm;

    PORTMUX.TCAROUTEA = PORTMUX_TCA0_PORTA_gc;   /* WO0..WO3 -> PA0..PA3 (default, explicit) */

    /* split mode: two 8-bit timers, six compare outputs */
    TCA0.SPLIT.CTRLD = TCA_SPLIT_SPLITM_bm;
    TCA0.SPLIT.CTRLB = TCA_SPLIT_LCMP0EN_bm | TCA_SPLIT_LCMP1EN_bm |
                       TCA_SPLIT_LCMP2EN_bm | TCA_SPLIT_HCMP0EN_bm;
    TCA0.SPLIT.LPER  = 255;
    TCA0.SPLIT.HPER  = 255;
    TCA0.SPLIT.LCMP0 = 0;
    TCA0.SPLIT.LCMP1 = 0;
    TCA0.SPLIT.LCMP2 = 0;
    TCA0.SPLIT.HCMP0 = 0;
    TCA0.SPLIT.CTRLA = TCA_SPLIT_CLKSEL_DIV1_gc | TCA_SPLIT_ENABLE_bm;
}

void led_set(uint8_t ch, uint8_t duty)
{
    switch (ch) {
        case 0: TCA0.SPLIT.LCMP0 = duty; break;
        case 1: TCA0.SPLIT.LCMP1 = duty; break;
        case 2: TCA0.SPLIT.LCMP2 = duty; break;
        case 3: TCA0.SPLIT.HCMP0 = duty; break;
        default: break;
    }
}

void led_set_all(uint8_t duty)
{
    TCA0.SPLIT.LCMP0 = duty;
    TCA0.SPLIT.LCMP1 = duty;
    TCA0.SPLIT.LCMP2 = duty;
    TCA0.SPLIT.HCMP0 = duty;
}

void led_off(void)
{
    led_set_all(0);
}

/* --- glow timebase -------------------------------------------------------
 * During a breath the LEDs dominate the current; the CPU only needs to update
 * the duty every step_ms. Rather than burn the core in a _delay_ms busy-loop
 * for the whole ~3 s animation, a TCB ticks every 1 ms and the core IDLE-sleeps
 * between updates (TCA keeps the PWM running in idle, so the glow is unbroken).
 * IDLE gates the core clock only -- the oscillator and TCA keep running and the
 * LEDs still dominate -- so the saving is modest (~5% of glow energy), but it
 * costs nothing visually and pets the watchdog along the way.
 *
 * TCB is enabled only for the duration of led_breathe. CCMP is derived from
 * F_CPU so 1 ms holds if the clock changes; at 4 MHz / DIV2 it is 2000 counts. */
static volatile uint8_t tcb_tick;

ISR(TCB0_INT_vect)
{
    TCB0.INTFLAGS = TCB_CAPT_bm;     /* write-1-to-clear */
    tcb_tick = 1;
}

static void tcb_start_1ms(void)
{
    TCB0.CCMP     = (uint16_t)(F_CPU / 2UL / 1000UL);   /* 1 ms at CLK_PER/2 */
    TCB0.CNT      = 0;
    TCB0.INTFLAGS = TCB_CAPT_bm;                        /* drop any stale flag */
    TCB0.INTCTRL  = TCB_CAPT_bm;                        /* IRQ on compare      */
    TCB0.CTRLB    = TCB_CNTMODE_INT_gc;                 /* periodic interrupt  */
    TCB0.CTRLA    = TCB_CLKSEL_DIV2_gc | TCB_ENABLE_bm;
}

static void tcb_stop(void)
{
    TCB0.CTRLA    = 0;               /* disable so it does not tick between glows */
    TCB0.INTCTRL  = 0;
    TCB0.INTFLAGS = TCB_CAPT_bm;
}

/* sleep the core in IDLE for `ms` TCB ticks (1 ms each). Only the TCB tick ends
 * a nap; PIT/accel interrupts may wake the core but leave tcb_tick clear, so a
 * wake event during a glow is latched (for the main loop) without cutting the
 * animation short. Requires TCB running (tcb_start_1ms) and interrupts enabled. */
static void idle_nap_ms(uint16_t ms)
{
    set_sleep_mode(SLEEP_MODE_IDLE);
    while (ms--) {
        tcb_tick = 0;
        for (;;) {
            cli();
            if (tcb_tick) { sei(); break; }
            sleep_enable();
            sei();                   /* SEI + SLEEP is atomic: no missed tick */
            sleep_cpu();
            sleep_disable();
        }
#if USE_WDT
        wdt_reset();                 /* pet across the whole glow, ~1 ms cadence */
#endif
    }
}

void led_breathe(uint8_t cycles, uint16_t breath_ms, uint8_t peak)
{
    const uint8_t steps = 64;                 /* per half-breath */
    uint16_t step_ms = breath_ms / (uint16_t)(2u * steps);
    if (step_ms == 0) step_ms = 1;

    tcb_start_1ms();                           /* 1 ms timebase for the idle naps */
    for (uint8_t c = 0; c < cycles; c++) {
        for (uint8_t i = 0; i <= steps; i++) {              /* in  */
            uint8_t lin = (uint8_t)(((uint16_t)peak * i) / steps);
            led_set_all(gamma2(lin));
            idle_nap_ms(step_ms);
        }
        for (uint8_t i = steps; i > 0; i--) {               /* out */
            uint8_t lin = (uint8_t)(((uint16_t)peak * (i - 1)) / steps);
            led_set_all(gamma2(lin));
            idle_nap_ms(step_ms);
        }
    }
    tcb_stop();
    led_off();
}
