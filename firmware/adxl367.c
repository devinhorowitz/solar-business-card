/*
 * adxl367.c  --  ADXL367 bring-up: soft reset, ID check, tap + activity config,
 * enter measurement.
 *
 * Config-before-MEASURE (data-sheet rule): everything is programmed while the part
 * is in standby, then POWER_CTL flips MEASURE last. Single-vs-double tap is resolved
 * in hardware, so main.c just reads STATUS_2 on the INT1 event; the INT2 activity
 * interrupt is acked by reading STATUS. Bus faults degrade safe (present() /
 * read_tap() return the "absent / no bits" value rather than blocking).
 */
#include <avr/io.h>
#include <util/delay.h>
#include "adxl367.h"
#include "twi.h"
#include "board.h"          /* ADXL367_ADDR */

uint8_t adxl367_present(void)
{
    uint8_t ad = 0, pid = 0;
    if (twi_reg_read(ADXL367_ADDR, ADXL_DEVID_AD, &ad,  1)) return 1;  /* bus fault */
    if (twi_reg_read(ADXL367_ADDR, ADXL_PART_ID,  &pid, 1)) return 1;
    return (ad == ADXL_DEVID_AD_VAL && pid == ADXL_PART_ID_VAL) ? 0 : 1;
}

uint8_t adxl367_init_tap(void)
{
    uint8_t rc = 0;

    /* soft reset -> all registers cleared, part left in standby. Belt-and-suspenders
     * against a warm MCU reset (UPDI / watchdog) where the accel kept its old config. */
    rc |= twi_reg_write(ADXL367_ADDR, ADXL_SOFT_RESET, ADXL_SOFT_RESET_CODE);
    _delay_ms(2);                       /* conservative reset settle */

    if (adxl367_present()) return 1;    /* wrong / absent part after reset */

    /* ---- config while in standby (MEASURE still 0) ---- */
    /* ODR / range */
    rc |= twi_reg_write(ADXL367_ADDR, ADXL_FILTER_CTL,    ADXL_CFG_FILTER_CTL);
    /* tap engine (single + double, one axis) */
    rc |= twi_reg_write(ADXL367_ADDR, ADXL_TAP_THRESH,    ADXL_CFG_TAP_THRESH);
    rc |= twi_reg_write(ADXL367_ADDR, ADXL_TAP_DUR,       ADXL_CFG_TAP_DUR);
    rc |= twi_reg_write(ADXL367_ADDR, ADXL_TAP_LATENT,    ADXL_CFG_TAP_LATENT);
    rc |= twi_reg_write(ADXL367_ADDR, ADXL_TAP_WINDOW,    ADXL_CFG_TAP_WINDOW);
    rc |= twi_reg_write(ADXL367_ADDR, ADXL_AXIS_MASK,     ADXL_CFG_AXIS_MASK);
    /* activity engine (referenced motion -> INT2) */
    rc |= twi_reg_write(ADXL367_ADDR, ADXL_THRESH_ACT_H,  ADXL_CFG_THRESH_ACT_H);
    rc |= twi_reg_write(ADXL367_ADDR, ADXL_THRESH_ACT_L,  ADXL_CFG_THRESH_ACT_L);
    rc |= twi_reg_write(ADXL367_ADDR, ADXL_TIME_ACT,      ADXL_CFG_TIME_ACT);
    rc |= twi_reg_write(ADXL367_ADDR, ADXL_ACT_INACT_CTL, ADXL_CFG_ACT_INACT);
    /* interrupt routing: tap -> INT1, activity -> INT2 (active-high push/pull default) */
    rc |= twi_reg_write(ADXL367_ADDR, ADXL_INTMAP1_UPPER, ADXL_CFG_INTMAP1_UPPER);
    rc |= twi_reg_write(ADXL367_ADDR, ADXL_INTMAP2_LOWER, ADXL_CFG_INTMAP2_LOWER);

    /* ---- arm last: enter measurement mode ---- */
    rc |= twi_reg_write(ADXL367_ADDR, ADXL_POWER_CTL,     ADXL_CFG_POWER_CTL);

    /* drop any power-on tap / activity latch so the first real event is clean */
    adxl367_clear_tap();
    adxl367_clear_activity();
    return rc;
}

uint8_t adxl367_read_tap(void)
{
    uint8_t s2 = 0;
    if (twi_reg_read(ADXL367_ADDR, ADXL_STATUS_2, &s2, 1)) return 0;  /* bus fault -> no bits */
    return s2;   /* TAP_ONE (bit0) / TAP_TWO (bit1); the read clears the flags and re-arms */
}

void adxl367_clear_tap(void)
{
    (void)adxl367_read_tap();   /* read-to-clear, value discarded */
}

void adxl367_clear_activity(void)
{
    uint8_t st;
    (void)twi_reg_read(ADXL367_ADDR, ADXL_STATUS, &st, 1);   /* reading STATUS acks ACT */
}

int8_t adxl367_read_z(void)
{
    /* One 8-bit Z sample: the card-face normal (same axis the tap engine watches). At
     * rest it reads ~+1 g (~+64) face-up and ~-1 g (~-64) face-down. Reading a data
     * register does not disturb the tap/activity latches. On a bus fault return 0 (level),
     * which the face-down logic treats as "not face-down" -- a glitch can't force dormancy. */
    uint8_t z = 0;
    if (twi_reg_read(ADXL367_ADDR, ADXL_ZDATA8, &z, 1)) return 0;
    return (int8_t)z;
}
