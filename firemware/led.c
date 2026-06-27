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
#include "board.h"
#include "led.h"
#include <util/delay.h>

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

/* 1 ms granularity runtime delay (util/delay wants a compile-time arg). */
static void delay_ms_var(uint16_t ms)
{
    while (ms--) _delay_ms(1);
}

void led_breathe(uint8_t cycles, uint16_t breath_ms, uint8_t peak)
{
    const uint8_t steps = 64;                 /* per half-breath */
    uint16_t step_ms = breath_ms / (uint16_t)(2u * steps);
    if (step_ms == 0) step_ms = 1;

    for (uint8_t c = 0; c < cycles; c++) {
        for (uint8_t i = 0; i <= steps; i++) {              /* in  */
            uint8_t lin = (uint8_t)(((uint16_t)peak * i) / steps);
            led_set_all(gamma2(lin));
            delay_ms_var(step_ms);
        }
        for (uint8_t i = steps; i > 0; i--) {               /* out */
            uint8_t lin = (uint8_t)(((uint16_t)peak * (i - 1)) / steps);
            led_set_all(gamma2(lin));
            delay_ms_var(step_ms);
        }
    }
    led_off();
}
