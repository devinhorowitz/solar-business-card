/*
 * sense.c  --  ADC rail/light reads + EEPROM activation counter.
 */
#include <avr/io.h>
#include <avr/eeprom.h>
#include "board.h"
#include "sense.h"

/* 2.500 V ADC reference -> mV per LSb at 12-bit = 2500/4096. We compute in
 * integer microvolts-ish by scaling: mv = res * 2500 / 4096. */
#define ADC_VREF_MV   2500UL

/* ---------- ADC ---------- */

void sense_adc_init(void)
{
    VREF.ADC0REF = VREF_ALWAYSON_bm | VREF_REFSEL_2V500_gc;
    ADC0.CTRLC   = ADC_PRESC_DIV2_gc;          /* 1 MHz / 2 = 500 kHz CLK_ADC
                                                * (2 us period; spec is 0.5-8 us).
                                                * DIV4 would also be in spec but
                                                * needlessly slow at this clock. */
    /* long sample time: the VSENSE divider is 1M//1M ~ 500k source impedance,
     * far above the SAR's comfort zone, so stretch acquisition. C5 holds the
     * charge between the ~1 s polls; this just covers the sample window. */
    ADC0.SAMPCTRL = 31;
    ADC0.CTRLA   = ADC_RESSEL_12BIT_gc | ADC_ENABLE_bm;   /* single-ended, 12-bit */
}

static uint16_t adc_read_raw(uint8_t muxpos)
{
    ADC0.MUXPOS  = muxpos;
    ADC0.COMMAND = ADC_STCONV_bm;
    /* A 12-bit conversion is ~(2 + SAMPLEN + 13.5) cycles at 500 kHz CLK_ADC,
     * so ~95 us with SAMPLEN = 31. Bound the wait so a misconfigured/stuck ADC
     * cannot hang the core; 8000 loops is tens of ms at 1 MHz, far beyond the
     * conversion. On timeout return 0, which reads as low rail / dark and fails
     * safe (no glow). */
    for (uint16_t guard = 0; guard < 8000; guard++)
        if (ADC0.INTFLAGS & ADC_RESRDY_bm)
            return ADC0.RES;        /* reading RES clears RESRDY */
    return 0;
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
