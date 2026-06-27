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

static uint16_t adc_read_raw(uint8_t muxpos)
{
    uint16_t res = 0;

    ADC0.CTRLA   |= ADC_ENABLE_bm;     /* power up ADC; reference begins start-up */
    ADC0.MUXPOS   = muxpos;
    ADC0.INTFLAGS = ADC_RESRDY_bm;     /* clear any stale result-ready flag */
    ADC0.COMMAND  = ADC_STCONV_bm;     /* INITDLY warm-up is inserted before the sample */

    /* A conversion is INITDLY + (2 + SAMPLEN + 13.5) CLK_ADC cycles, ~350 us
     * here with DLY128 and SAMPLEN = 31. Bound the wait so a misconfigured or
     * stuck ADC cannot hang the core; 8000 loops is tens of ms at 1 MHz, well
     * beyond the conversion. On timeout RES stays 0, which reads as low rail /
     * dark and fails safe (no glow). */
    for (uint16_t guard = 0; guard < 8000; guard++)
        if (ADC0.INTFLAGS & ADC_RESRDY_bm) {   /* reading RES also clears RESRDY */
            res = ADC0.RES;
            break;
        }

    ADC0.CTRLA   &= ~ADC_ENABLE_bm;    /* power down ADC; reference released */
    return res;
}

uint16_t sense_vin_mv(void)
{
    uint32_t res = adc_read_raw(VSENSE_AIN);                 /* AIN2 = PD2 */
    uint32_t mv  = (res * ADC_VREF_MV) >> 12;                /* /4096 */
    return (uint16_t)(mv * VSENSE_DIVIDER);                  /* x2 -> VIN */
}

uint16_t sense_vdd_mv(void)
{
    uint32_t res = adc_read_raw(ADC_MUXPOS_VDDDIV10_gc);     /* internal VDD/10 */
    uint32_t mv  = (res * ADC_VREF_MV) >> 12;
    return (uint16_t)(mv * 10UL);                            /* undo /10 */
}

uint8_t sense_rail_ok(void)
{
    return (sense_vdd_mv() >= VS_GLOW_FLOOR_MV) ? 1u : 0u;
}

/* ---------- EEPROM lifetime activation counter ---------- */

#define EE_COUNT_ADDR  ((uint32_t *)0)     /* 4 bytes at EEPROM offset 0 */

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
