/*
 * led.h  --  DRH monogram LEDs on TCA0 split mode (PA0..PA3 = WO0..WO3).
 *
 * 4 low-side LED channels (D2..D5). The LED lights when its PORTA pin pulls
 * LOW (cathode side, through a 150R ballast). The ballast fixes the PEAK
 * current on the clamped rail (~9 mA); PWM only trims the time-average below
 * that ceiling, so duty is purely a brightness/energy control and can never
 * push the LED past its ballasted peak.
 *
 * Polarity: the pins use pad-level invert (PORTA.PINnCTRL INVEN, set in
 * led_init) so a LARGER compare value = brighter (more low-time at the pad).
 * If a bench check shows brightness running backwards, drop INVEN in
 * led_init -- that is the whole fix.
 *
 * SW2 (master anode switch) is pure hardware and invisible to firmware: with
 * SW2 OFF the anodes are disconnected and nothing lights no matter what TCA
 * does. led_* still runs; it just produces no photons. Documented, not sensed.
 */
#ifndef LED_H
#define LED_H

#include <stdint.h>

/* one-time: PORTA dirs, INVEN, PORTMUX TCA0->PORTA, TCA0 split PWM, outputs off. */
void led_init(void);

/* set one channel 0..3 to duty 0..255 (0 = off, 255 = full/ballast-limited). */
void led_set(uint8_t ch, uint8_t duty);

/* set all four channels to the same duty. */
void led_set_all(uint8_t duty);

/* all channels dark. */
void led_off(void);

/* blocking "breathing" glow: `cycles` smooth in/out breaths, each lasting
 * `breath_ms`, peaking at `peak` duty. Returns with LEDs off. Perceptual
 * (gamma-corrected) ramp so it looks like a breath, not a triangle. */
void led_breathe(uint8_t cycles, uint16_t breath_ms, uint8_t peak);

/* Idle-sleep the core for `ms` (LEDs untouched). Same 1 ms TCB timebase as the
 * breathing animation, so it costs the idle tier, not a 4/1 MHz busy-spin.
 * Requires interrupts enabled. Used for the double-tap disambiguation window. */
void led_wait_ms(uint16_t ms);

#endif /* LED_H */
