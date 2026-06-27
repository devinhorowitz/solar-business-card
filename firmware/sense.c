/*
 * sense.c  --  ADC rail/light reads, AC0 light-wake (VDD ref), EEPROM counter.
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
    ADC0.CTRLC   = ADC_PRESC_DIV4_gc;          /* 4 MHz / 4 = 1 MHz CLK_ADC */
    /* long sample time: the VSENSE divider is 1M//1M ~ 500k source impedance,
     * far above the SAR's comfort zone, so stretch acquisition. C5 holds the
     * charge between the ~1 s polls; this just covers the sample window. */
    ADC0.SAMPCTRL = 31;
    ADC0.CTRLA   = ADC_RESSEL_12BIT_gc | ADC_ENABLE_bm;   /* single-ended, 12-bit */
}

static uint16_t adc_read_raw(uint8_t muxpos)
{
    ADC0.MUXPOS   = muxpos;
    ADC0.COMMAND  = ADC_STCONV_bm;
    while (!(ADC0.INTFLAGS & ADC_RESRDY_bm)) { }
    return ADC0.RES;            /* INTFLAGS RESRDY clears on RES read */
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

/* ---------- AC0 light wake (option A), VDD-referenced ---------- */

/* threshold = DACREF/256 * VDD. VDD ~3.4 V clamped; LIGHT_THRESH_MV ~0.4 V.
 * DACREF = LIGHT_THRESH_MV * 256 / VDD_nominal. Computed against a 3400 mV
 * nominal rail; tracks the rail since the ref IS the rail. */
#define VDD_NOMINAL_MV   3400UL
#define LIGHT_DACREF     ((uint8_t)((LIGHT_THRESH_MV * 256UL) / VDD_NOMINAL_MV))

void sense_light_arm(void)
{
    VREF.ACREF   = VREF_ALWAYSON_bm | VREF_REFSEL_VDD_gc;    /* <-- VDD, no bandgap (~0 uA) */
    AC0.DACREF   = LIGHT_DACREF;                             /* ~0.4 V threshold */
    AC0.MUXCTRL  = AC_MUXPOS_AINP0_gc | AC_MUXNEG_DACREF_gc; /* + = PD2, - = DACREF */
    AC0.INTCTRL  = AC_INTMODE_POSEDGE_gc | AC_CMP_bm;        /* IRQ on dark->light edge */
    /* slowest comparator profile (plenty fast for light) + run in standby */
    AC0.CTRLA    = AC_RUNSTDBY_bm | AC_POWER_PROFILE3_gc |
                   AC_HYSMODE_MEDIUM_gc | AC_ENABLE_bm;      /* hysteresis kills flicker chatter */
}

void sense_light_disarm(void)
{
    AC0.CTRLA   = 0;                       /* comparator off */
    AC0.INTCTRL = 0;
    VREF.ACREF  = 0;                       /* drop the (VDD) ref enable */
    AC0.STATUS  = AC_CMPIF_bm;             /* clear any pending flag */
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
