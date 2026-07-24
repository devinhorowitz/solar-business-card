/*
 * led.c  --  TCA0 split-mode PWM + breathing animation.
 *
 * TCA0 split mode gives six 8-bit PWM channels off one timer. We use four:
 *   WO0 = LCMP0  -> PA0 (LDRV4, D5)
 *   WO1 = LCMP1  -> PA1 (LDRV3, D4)
 *   WO2 = LCMP2  -> PA2 (LDRV2, D3)
 *   WO3 = HCMP0  -> PA3 (LDRV1, D2)
 * LPER = HPER = 255, CLKSEL = DIV1 -> ~3.9 kHz at F_CPU 1 MHz (still well above
 * any flicker the eye resolves; no inductors/piezo, so nothing to whine). PORTMUX.TCAROUTEA = PORTA is the default but is set
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
    /* Pad config, set once: INVEN so bigger duty = brighter AND compare 0 parks the
     * pad HIGH = LED dark during an animation's gaps. INVEN is LOAD-BEARING for that
     * dark-off state: do NOT drop it to "fix" a backwards brightness (that lights
     * every LED at duty 0) -- write 255 - duty instead. See led.h. The input buffer
     * is disabled permanently: these pads are output-or-parked, never read, and a
     * parked pad floats wherever the LED network puts it -- a live buffer would
     * draw shoot-through at mid-rail levels.
     *
     * DIR is NOT set here: between animations the pads are PARKED as inputs
     * (led_park), the 2026-07-23 sub-emission-bias mitigation. Driven-high idle
     * held all four LEDs at up to 1.35 V continuous forward bias (STO at VOVCH
     * 4.65 V vs pads at 3.3 V) -- a bias OSRAM's datasheet explicitly forbids
     * (note 2: migration risk). Tristated, the cathode floats up and the bias
     * drops to the clamp-limited ~1 V worst-case, and to ZERO once STO is below
     * ~VDD+0.3+margin (~3.6 V) -- most of the card's life. WO output needs DIR=1
     * on this part, so animations bracket themselves with led_unpark/led_park. */
    PORTA.PIN0CTRL = PORT_INVEN_bm | PORT_ISC_INPUT_DISABLE_gc;
    PORTA.PIN1CTRL = PORT_INVEN_bm | PORT_ISC_INPUT_DISABLE_gc;
    PORTA.PIN2CTRL = PORT_INVEN_bm | PORT_ISC_INPUT_DISABLE_gc;
    PORTA.PIN3CTRL = PORT_INVEN_bm | PORT_ISC_INPUT_DISABLE_gc;

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

/* park/unpark: the sub-emission-bias mitigation (see led_init). Park = pads to
 * inputs (LED path open, nA clamp leakage at worst); unpark = pads driven again
 * (compare values already parked at 0 = INVEN-high = dark, so no flash). */
static void led_park(void)   { LED_PORT.DIRCLR = LED_ALL_bm; }
static void led_unpark(void) { LED_PORT.DIRSET = LED_ALL_bm; }

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
 * F_CPU so 1 ms holds if the clock changes; at 1 MHz / DIV2 it is 500 counts. */
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

/* Reader-field gate: the NT3H2211's FD pin (PA6) is pulled LOW while an NFC reader's
 * RF field is present. During that window the tag replies by load-modulating at
 * 13.56 MHz, and our LED PWM edges would inject broadband noise across that band, so
 * we hold the LEDs dark for the read (see NFC_BLANK_ON_FIELD in board.h). led.c reads
 * the pin directly -- no shared flag -- so the check is always current. */
#if NFC_BLANK_ON_FIELD
static inline uint8_t reader_field_active(void)
{
    return (uint8_t)((FD_PORT.IN & FD_PIN_bm) == 0);   /* FD low = reader field present */
}
#else
static inline uint8_t reader_field_active(void) { return 0; }
#endif

/* sleep the core in IDLE for `ms` TCB ticks (1 ms each). Only the TCB tick ends
 * a nap; PIT/accel interrupts may wake the core but leave tcb_tick clear, so a
 * wake event during a glow is latched (for the main loop) without cutting the
 * animation short. Requires TCB running (tcb_start_1ms) and interrupts enabled.
 * Returns 1 (and blanks the LEDs) if an NFC reader field appears mid-nap, so the
 * caller can bail out of the animation and let the core go quiet for the read. */
static uint8_t idle_nap_ms(uint16_t ms)
{
    slp_set_mode(SLEEP_MODE_IDLE);
    while (ms--) {
        tcb_tick = 0;
        for (;;) {
            if (reader_field_active()) { led_off(); return 1; }   /* reader up: blank + bail */
            cli();
            if (tcb_tick) { sei(); break; }
            slp_enable();
            sei();                   /* SEI + SLEEP is atomic: no missed tick */
            sleep_cpu();
            slp_disable();
        }
#if USE_WDT
        wdt_reset();                 /* pet across the whole glow, ~1 ms cadence */
#endif
    }
    return 0;
}

void led_breathe(uint8_t cycles, uint16_t breath_ms, uint8_t peak)
{
    const uint8_t steps = 64;                 /* per half-breath */
    uint16_t step_ms = breath_ms / (uint16_t)(2u * steps);
    if (step_ms == 0) step_ms = 1;

    /* if a reader field is already up, stay dark -- the read owns the RF band. */
    if (reader_field_active()) { led_off(); return; }   /* still parked -- nothing lit */

    led_unpark();
    tcb_start_1ms();                           /* 1 ms timebase for the idle naps */
    for (uint8_t c = 0; c < cycles; c++) {
        for (uint8_t i = 0; i <= steps; i++) {              /* in  */
            uint8_t lin = (uint8_t)(((uint16_t)peak * i) / steps);
            led_set_all(gamma2(lin));
            if (idle_nap_ms(step_ms)) { tcb_stop(); led_off(); led_park(); return; }   /* field: blanked, bail */
        }
        for (uint8_t i = steps; i > 0; i--) {               /* out */
            uint8_t lin = (uint8_t)(((uint16_t)peak * (i - 1)) / steps);
            led_set_all(gamma2(lin));
            if (idle_nap_ms(step_ms)) { tcb_stop(); led_off(); led_park(); return; }   /* field: blanked, bail */
        }
    }
    tcb_stop();
    led_off();
    led_park();
}

/* Sequential "loading" chase for the in-sun tell.
 *
 * WIRED: main.c's ~1 s poll calls this when sense_vin_flags() reports strong sun
 * (VIN >= SWEEP_SUN_VIN_MV) with the caps full (sense_caps_full()). The VIN-at-clamp
 * threshold was derived on the PCB side and lives in board.h SWEEP_SUN_VIN_MV. With
 * USE_SUN_SWEEP 0 the call compiles out but this stays linked as library code, so do
 * not remove it as unused.
 *
 * A bright bump sweeps left->right
 * across the four LEDs, each fading up then down and overlapping its neighbour so
 * that as one dims the next brightens. Physical left->right is D2,D3,D4,D5, which on
 * this board is channel order 3,2,1,0 (the WO/channel numbering runs right->left
 * across the monogram -- see the map at the top of this file). Same 1 ms idle-nap
 * timebase and the same NFC-field abort as led_breathe.
 *   passes  : number of left->right wipes
 *   pass_ms : duration of one wipe
 *   peak    : peak per-LED brightness at the centre of its bump (0..255)
 *   overlap : bump half-width in Q8 units of LED spacing (256 = one full spacing, so
 *             neighbours cross at ~50%; >256 = more overlap/softer; <256 = a gap). */
void led_sweep(uint8_t passes, uint16_t pass_ms, uint8_t peak, uint16_t overlap)
{
    static const uint8_t phys_ch[4] = { 3, 2, 1, 0 };   /* left->right -> WO channel */
    const uint8_t steps = 96;                            /* render steps per wipe */
    uint16_t step_ms = pass_ms / steps;
    if (step_ms == 0) step_ms = 1;
    if (overlap == 0)  overlap = 1;

    if (reader_field_active()) { led_off(); return; }    /* reader up: stay dark */

    /* p sweeps from -overlap to (3*256 + overlap) in Q8 so the bump fades in at the
     * left edge and out past the right. */
    const int16_t p_lo = (int16_t)(-(int16_t)overlap);
    const int16_t p_hi = (int16_t)(3 * 256 + (int16_t)overlap);
    const int32_t span = (int32_t)p_hi - (int32_t)p_lo;

    led_unpark();
    tcb_start_1ms();
    for (uint8_t c = 0; c < passes; c++) {
        for (uint8_t s = 0; s <= steps; s++) {
            int16_t p = (int16_t)(p_lo + (int16_t)((span * s) / steps));
            for (uint8_t i = 0; i < 4; i++) {
                int16_t d = (int16_t)(p - (int16_t)(i * 256));   /* Q8 distance to LED i */
                if (d < 0) d = (int16_t)(-d);
                uint8_t b = (d >= (int16_t)overlap)
                          ? 0
                          : (uint8_t)(255u - (uint16_t)(((uint32_t)(uint16_t)d * 255u) / overlap));
                uint8_t lin = (uint8_t)(((uint16_t)b * peak) / 255u);
                led_set(phys_ch[i], gamma2(lin));
            }
            if (idle_nap_ms(step_ms)) { tcb_stop(); led_off(); led_park(); return; }   /* field: blanked, bail */
        }
    }
    tcb_stop();
    led_off();
    led_park();
}
