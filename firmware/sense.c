/*
 * sense.c  --  ADC rail/light reads + EEPROM activation counter.
 *
 * Power policy: the ADC and its 2.5 V reference are powered only for the
 * length of a conversion and shut off immediately after (see adc_read_raw).
 * Between the ~1 s polls the ADC ENABLE bit is 0, which the datasheet
 * guarantees draws no ADC current, and with VREF_ALWAYSON cleared the
 * reference is released as well. The analog domain therefore contributes
 * essentially nothing to sleep current, independent of how Power-Down would
 * have treated an always-on reference.
 *
 * The cost of that policy is that the reference is cold-started on every read,
 * so the one conversion after each ENABLE must wait out the reference
 * start-up. That wait is inserted automatically by the ADC Initialization
 * Delay (INITDLY) field in CTRLD; see ADC_INITDLY below for the sizing.
 */
#include <avr/io.h>
#include <avr/eeprom.h>
#include <avr/interrupt.h>
#include <avr/sleep.h>
#include "board.h"
#include "sense.h"

/* 2.500 V ADC reference -> mV per LSb at 12-bit = 2500/4096. We compute in
 * integer microvolts-ish by scaling: mv = res * 2500 / 4096. */
#define ADC_VREF_MV   2500UL

/* Reference start-up delay before the first sample. INITDLY counts CLK_ADC
 * cycles and must be >= tVREF_ST x fCLK_ADC, where tVREF_ST is the datasheet
 * "VREF start-up time". On this board the main clock is OSCHF (high frequency),
 * for which tVREF_ST is ~10 us; the 200 us figure in the same table is the
 * 32.768 kHz main-clock case and does not apply here. At CLK_ADC = 500 kHz one
 * cycle is 2 us, so even the worst tabled 200 us needs only 100 cycles. DLY128
 * (= 256 us) covers that with margin. The extra delay is almost free: at
 * IDD_ADC = 1.1 uA, polled about once per second, the difference between this
 * and a tight DLY32 is a fraction of a nanoamp of average current, so there is
 * no reason to trim it closer. */
#define ADC_INITDLY   ADC_INITDLY_DLY128_gc

/* ---------- ADC ---------- */

void sense_adc_init(void)
{
    /* Reference: 2.500 V, NOT always-on. It powers up when the ADC is enabled
     * and is released when the ADC is disabled (see adc_read_raw). */
    VREF.ADC0REF = VREF_REFSEL_2V500_gc;

    ADC0.CTRLC   = ADC_PRESC_DIV2_gc;          /* 1 MHz / 2 = 500 kHz CLK_ADC
                                                * (2 us period; spec is 0.5-8 us).
                                                * DIV4 would also be in spec but
                                                * needlessly slow at this clock. */
    ADC0.CTRLD   = ADC_INITDLY;                /* reference settling before sample */

    /* long sample time: the VSENSE divider is 1M//1M ~ 500k source impedance,
     * far above the SAR's comfort zone, so stretch acquisition. C5 holds the
     * charge between the ~1 s polls; this just covers the sample window. */
    ADC0.SAMPCTRL = 31;

    /* Configure resolution but leave the ADC DISABLED: each read enables it,
     * converts, and disables it again so the reference is off between polls. */
    ADC0.CTRLA   = ADC_RESSEL_12BIT_gc;        /* single-ended, 12-bit, ENABLE = 0 */
}

/* Result-ready wakes the core out of the IDLE nap in adc_read_raw. The ISR only
 * clears the flag and records completion; the caller reads the result from RES
 * after the wake. */
static volatile uint8_t adc_done;

ISR(ADC0_RESRDY_vect)
{
    ADC0.INTFLAGS = ADC_RESRDY_bm;     /* write-1-to-clear */
    adc_done = 1;
}

static uint16_t adc_read_raw(uint8_t muxpos)
{
    uint16_t res = 0;

    ADC0.CTRLA   |= ADC_ENABLE_bm;     /* power up ADC; reference begins start-up */
    ADC0.MUXPOS   = muxpos;
    ADC0.INTFLAGS = ADC_RESRDY_bm;     /* clear any stale result-ready flag */
    adc_done      = 0;
    ADC0.INTCTRL  = ADC_RESRDY_bm;     /* wake on result-ready */
    ADC0.COMMAND  = ADC_STCONV_bm;     /* INITDLY warm-up is inserted before the sample */

    /* The conversion is INITDLY + (2 + SAMPLEN + 13.5) CLK_ADC cycles, ~350 us here.
     * IDLE-sleep through it rather than spinning the core in active mode: the ADC
     * keeps converting in IDLE and RESRDY wakes us (same race-free SEI+SLEEP idiom
     * as the glow). RESRDY is the first wake in the healthy case; the loop is bounded
     * so a stuck ADC (RESRDY never arrives) bails after a few wakes with RES = 0 --
     * reads as low rail / dark, fail-safe no glow, and well under the watchdog -- and
     * a stray PIT/accel wake just re-checks the flag and sleeps again. */
    set_sleep_mode(SLEEP_MODE_IDLE);
    for (uint8_t guard = 0; guard < 3 && !adc_done; guard++) {
        cli();
        if (adc_done) { sei(); break; }
        sleep_enable();
        sei();                         /* SEI + SLEEP is atomic: no missed RESRDY */
        sleep_cpu();
        sleep_disable();
    }
    ADC0.INTCTRL = 0;                  /* stop the ADC interrupt */
    if (adc_done)
        res = ADC0.RES;                /* reading RES also clears RESRDY */

    ADC0.CTRLA   &= ~ADC_ENABLE_bm;    /* power down ADC; reference released */
    return res;
}

uint16_t sense_vin_mv(void)
{
    uint32_t res = adc_read_raw(VSENSE_AIN);                 /* AIN2 = PD2 */
    uint32_t mv  = (res * ADC_VREF_MV) >> 12;                /* /4096 */
    return (uint16_t)(mv * VSENSE_DIVIDER);                  /* x2 -> VIN */
}

/* Light-present threshold as a raw 12-bit ADC count, folded at COMPILE time from
 * the board's mV threshold. VSENSE reads the pin (= VIN/2) and LIGHT_THRESH_MV is
 * that pin threshold, so count c means pin_mv = c*ADC_VREF_MV/4096; thus
 * pin_mv >= LIGHT_THRESH_MV  <=>  c >= ceil(LIGHT_THRESH_MV*4096/ADC_VREF_MV).
 * That is the SAME boolean the old (sense_vin_mv() >= LIGHT_THRESH_MV*VSENSE_DIVIDER)
 * produced (the divider's x2 cancels the threshold's x2), for every threshold value. */
#define LIGHT_COUNT \
    ((uint16_t)(((uint32_t)LIGHT_THRESH_MV * 4096UL + (ADC_VREF_MV - 1UL)) / ADC_VREF_MV))

uint8_t sense_light(void)
{
    /* one ADC read (same sampling as sense_vin_mv), compared raw -- no mV math. */
    return (adc_read_raw(VSENSE_AIN) >= LIGHT_COUNT) ? 1u : 0u;
}

uint16_t sense_vdd_mv(void)
{
    uint32_t res = adc_read_raw(ADC_MUXPOS_VDDDIV10_gc);     /* internal VDD/10 */
    uint32_t mv  = (res * ADC_VREF_MV) >> 12;
    return (uint16_t)(mv * 10UL);                            /* undo /10 */
}

/* Rail-floor threshold as a raw VDD/10-channel count, folded at COMPILE time.
 * sense_vdd_mv() = floor(c*ADC_VREF_MV/4096)*10, so
 *   sense_vdd_mv() >= VS_GLOW_FLOOR_MV
 *     <=> c >= ceil( ceil(VS_GLOW_FLOOR_MV/10) * 4096 / ADC_VREF_MV )
 * -- the inner ceil reproduces the channel's 10 mV quantization exactly, so this
 * is the SAME boolean as the old compare for every floor value, with no mV math. */
#define RAIL_FLOOR_10MV (((uint32_t)VS_GLOW_FLOOR_MV + 9UL) / 10UL)   /* ceil(mV/10) */
#define RAIL_COUNT      ((uint16_t)((RAIL_FLOOR_10MV * 4096UL + (ADC_VREF_MV - 1UL)) / ADC_VREF_MV))

uint8_t sense_rail_ok(void)
{
    /* raw VDD/10 count vs compile-time floor -- same result as sense_vdd_mv() >= floor,
     * same fail-safe (a stuck ADC reads 0 -> not ok -> no glow). */
    return (adc_read_raw(ADC_MUXPOS_VDDDIV10_gc) >= RAIL_COUNT) ? 1u : 0u;
}

/* ---------- EEPROM lifetime activation counter ---------- */

/* Address 0 in the EEPROM address space -- NOT a RAM null pointer. avr-libc's
 * eeprom_*_dword take an address within EEPROM, where 0 is the first cell; the
 * (uint32_t *) cast is the avr-libc idiom for that, not a null-pointer deref. */
#define EE_COUNT_ADDR  ((uint32_t *)0)     /* 4-byte counter at EEPROM offset 0 */

/* Read the lifetime tap counter. The firmware only ever increments it at runtime
 * (sense_count_inc); this reader exists for external readout over UPDI/debug and
 * future use -- uncalled on-chip BY DESIGN, kept as API (--gc-sections drops it if
 * it stays unused). Not dead code. */
uint32_t sense_count_get(void)
{
    return eeprom_read_dword(EE_COUNT_ADDR);
}

void sense_count_inc(void)
{
    uint32_t c = eeprom_read_dword(EE_COUNT_ADDR);
    if (c == 0xFFFFFFFFUL) c = 0;          /* erased EEPROM reads all-ones */
    c++;
    eeprom_update_dword(EE_COUNT_ADDR, c); /* update = no write if unchanged */
}
