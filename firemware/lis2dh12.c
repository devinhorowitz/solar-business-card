/*
 * lis2dh12.c  --  LIS2DH12 bring-up: presence, tap+activity config, latch clear.
 *
 * Power-up order matters a little: program the data path (REG1/REG4) and the
 * click engine (CLICK_CFG/THS/TIME_*) before arming the routing (REG3/REG6),
 * so the first edge the MCU sees is a real one. CLICK_SRC is read once at the
 * end to clear any power-on latch.
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

    /* activity (wake) engine */
    rc |= twi_reg_write(LIS2DH12_ADDR, LIS_ACT_THS, LIS_ACT_THS_VAL);
    rc |= twi_reg_write(LIS2DH12_ADDR, LIS_ACT_DUR, LIS_ACT_DUR_VAL);

    /* arm routing last: click->INT1, activity->INT2 */
    rc |= twi_reg_write(LIS2DH12_ADDR, LIS_CTRL_REG3, LIS_CFG_CTRL_REG3);
    rc |= twi_reg_write(LIS2DH12_ADDR, LIS_CTRL_REG6, LIS_CFG_CTRL_REG6);

    lis2dh12_clear_click();   /* drop any power-on latch */
    return rc ? 1u : 0u;
}

void lis2dh12_clear_click(void)
{
    uint8_t src;
    (void)twi_reg_read(LIS2DH12_ADDR, LIS_CLICK_SRC, &src, 1);  /* read-to-clear */
}
