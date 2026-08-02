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
#include "board.h"          /* ADXL367_ADDR; MUST precede util/delay.h so this TU's
                             * delays calibrate from the same F_CPU as every other
                             * (it was the one file including delay.h first, which
                             * split calibration when -DF_CPU overrode; 2026-08-01) */
#include <util/delay.h>
#include "adxl367.h"
#include "twi.h"

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
    /* MANDATORY 7.5 ms: "A latency of 7.5 ms is required after a software reset"
     * (data sheet Rev. B, Table 37, SOFT_RESET register). 10 ms = spec + margin.
     * The old 2 ms was a guess and under spec: the ID check and all fourteen
     * config writes below could land while the part was still resetting, so the
     * config silently reverted to reset defaults (tap engine OFF, INTs unmapped)
     * -- the card's only input, dead, on a boot that reported success. Cost is
     * 8 ms once per boot, before the watchdog is armed. */
    _delay_ms(10);

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

    /* MANDATORY ~100 ms: "after entering measurement mode, a 100 ms wait time
     * must be observed before reading acceleration data" (data sheet Rev. B,
     * Measurement Mode; Table 1 puts the first valid sample at ~100 ms + 1/ODR).
     * This is audit (b): the config and the latch clears below used to run
     * INSIDE that window (the 10 ms reset-latency fix above covers a different
     * one -- the post-SOFT_RESET latency). We wait it out because the datasheet
     * says to and because adxl367_read_z() is a reader of acceleration data.
     *
     * WHAT THIS DOES NOT BUY, stated honestly because the first draft of this
     * comment claimed it (caught 2026-08-02 by an adversarial review of the fix
     * itself, then verified against the datasheet). It does NOT prevent a phantom
     * tap from settling data, because two configured facts already make that
     * unreachable, and both are worth knowing before anyone "optimizes" this
     * delay away:
     *   - TAP_THRESH = 0x30 at 31.25 mg/LSB is 1.5 g (bits [7:6] are ignored on
     *     the +-2 g range, and both are 0 here, so the value stands). A stationary
     *     card's settle converges on the static ~1 g Z vector and never crosses it.
     *   - TAP_LATENT is non-zero, so the double-tap engine is armed in HARDWARE
     *     regardless of USE_DOUBLE_TAP (that macro only chooses how main.c reads
     *     STATUS_2). The datasheet: "If both single and double tap functions are
     *     in use, the single tap interrupt is triggered when the double tap event
     *     has been either validated or invalidated" -- TAP_LATENT + TAP_WINDOW =
     *     40 + 240 = 280 ms. Any candidate inside the settling window therefore
     *     could not raise INT1 until long after these clears, at any clock speed.
     * So the wait is datasheet compliance for the data path, cheaply bought at
     * boot -- not a guard against a tap race that the tap engine's own timing
     * had already closed.
     *
     * WHY 140 AND NOT 110. The target is 110 ms of REAL time (the 100 ms window
     * plus 1/ODR at the configured 100 Hz), but _delay_ms bakes in a cycle count
     * from the compile-time F_CPU (1 MHz), and this board does not always run at
     * 1 MHz: board.h's clocks_init note is explicit that until the OSCHFFRQ fuse
     * is burned the base is 20 MHz, so CLK_PER is 1.25 MHz and "delays run ~20%
     * short". _delay_ms(110) is 110,000 cycles, which at 1.25 MHz elapses in
     * 88 ms -- back INSIDE the 100 ms window this fix exists to clear, on
     * precisely the parts that matter most: an un-fused first article, straight
     * off the programmer. 140,000 cycles clears the target in both clock states
     * (140 ms fused, 112 ms un-fused). Boot-only, pre-WDT, invisible next to a
     * flash cycle. (The _delay_ms(10) reset latency above survives the same test
     * with less room: 8.0 ms un-fused against a 7.5 ms spec.) */
    _delay_ms(140);

    /* drop any power-on tap / activity latch so the first real event is clean
     * -- NOW the stream behind the engines is valid, so what stays cleared
     * stays cleared. */
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
