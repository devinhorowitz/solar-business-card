/*
 * lis2dh12.c  --  LIS2DH12 bring-up: presence, tap+activity config, latch clear.
 *
 * Power-up order matters a little: program the data path (REG1/REG4) and the
 * click + motion engines before arming the routing (REG3/REG6), so the first
 * edge the MCU sees is a real one. The shared high-pass filter is primed by
 * reading REFERENCE just before arming (so the motion interrupt does not trip
 * on the static 1g gravity), and CLICK_SRC is read once at the end to clear any
 * power-on latch.
 */
#include "lis2dh12.h"
#include "twi.h"

uint8_t lis2dh12_present(void)
{
    uint8_t id = 0;
    if (twi_reg_read(LIS2DH12_ADDR, LIS_WHO_AM_I, &id, 1)) return 0;
    return (id == LIS_WHO_AM_I_VAL) ? 1u : 0u;
}

uint8_t lis2dh12_init_tap(void)
{
    uint8_t rc = 0;

    /* core data path */
    rc |= twi_reg_write(LIS2DH12_ADDR, LIS_CTRL_REG0, LIS_CFG_CTRL_REG0);
    rc |= twi_reg_write(LIS2DH12_ADDR, LIS_CTRL_REG1, LIS_CFG_CTRL_REG1); /* ODR/LP/axes on */
    rc |= twi_reg_write(LIS2DH12_ADDR, LIS_CTRL_REG4, LIS_CFG_CTRL_REG4); /* BDU, +/-2g */
    rc |= twi_reg_write(LIS2DH12_ADDR, LIS_CTRL_REG2, LIS_CFG_CTRL_REG2); /* HP filter on click */
    rc |= twi_reg_write(LIS2DH12_ADDR, LIS_CTRL_REG5, LIS_CFG_CTRL_REG5);

    /* click (tap) engine */
    rc |= twi_reg_write(LIS2DH12_ADDR, LIS_CLICK_CFG,    LIS_CLICK_CFG_VAL);
    rc |= twi_reg_write(LIS2DH12_ADDR, LIS_CLICK_THS,    (uint8_t)(0x80 | LIS_CLICK_THS_RAW)); /* bit7 = latch */
    rc |= twi_reg_write(LIS2DH12_ADDR, LIS_TIME_LIMIT,   LIS_TIME_LIMIT_VAL);
    rc |= twi_reg_write(LIS2DH12_ADDR, LIS_TIME_LATENCY, LIS_TIME_LATENCY_VAL);
    rc |= twi_reg_write(LIS2DH12_ADDR, LIS_TIME_WINDOW,  LIS_TIME_WINDOW_VAL);

    /* motion (inertial wake-up) engine -> INT2. First make sure the old
     * sleep-to-wake is OFF (ACT_THS = 0) so the accel never auto-drops to 10 Hz;
     * then set the INT2 generator threshold, duration, and axis config. */
    rc |= twi_reg_write(LIS2DH12_ADDR, LIS_ACT_THS,      0x00);   /* no sleep-to-wake */
    rc |= twi_reg_write(LIS2DH12_ADDR, LIS_INT2_THS,      LIS_INT2_THS_VAL);
    rc |= twi_reg_write(LIS2DH12_ADDR, LIS_INT2_DURATION, LIS_INT2_DUR_VAL);
    rc |= twi_reg_write(LIS2DH12_ADDR, LIS_INT2_CFG,      LIS_INT2_CFG_VAL);

    /* prime the shared high-pass filter (HPM=00): reading REFERENCE captures
     * the present acceleration as the filter reference, so the static 1g gravity
     * is removed from both the click and INT2 paths. Do this before arming the
     * routes so INT2 does not assert on gravity the instant it goes live.
     * Assumes the card is roughly at rest at boot (true for a cold / just-charged
     * start; a reset mid-handling simply re-primes on the next boot). */
    {
        uint8_t ref;
        (void)twi_reg_read(LIS2DH12_ADDR, LIS_REFERENCE, &ref, 1);
    }

    /* arm routing last: click->INT1, motion (IA2)->INT2 */
    rc |= twi_reg_write(LIS2DH12_ADDR, LIS_CTRL_REG3, LIS_CFG_CTRL_REG3);
    rc |= twi_reg_write(LIS2DH12_ADDR, LIS_CTRL_REG6, LIS_CFG_CTRL_REG6);

    lis2dh12_clear_click();   /* drop any power-on latch */
    return rc ? 1u : 0u;
}

uint8_t lis2dh12_read_click(void)
{
    uint8_t src = 0;
    if (twi_reg_read(LIS2DH12_ADDR, LIS_CLICK_SRC, &src, 1)) return 0;  /* bus fault -> no bits */
    return src;   /* the read clears the latched INT1 */
}

void lis2dh12_clear_click(void)
{
    (void)lis2dh12_read_click();   /* read-to-clear, value discarded */
}
