/*
 * adxl367.h  --  ADI ADXL367 3-axis accel: register map + tap/activity config.
 *
 * Replaces the LIS2DH12 (backorder). ADI register map, not the ST femto map.
 * ASEL grounded on the board -> 7-bit I2C address 0x1D (see board.h). INT1 -> MCU
 * PF1, INT2 -> MCU PF0 (same pins the LIS2DH12 used). SCLK tied low = I2C mode.
 * Values below are verified against the ADXL367 data sheet (Rev. B, Table 11 map;
 * the per-register bit tables for the config words).
 *
 * Two engines, mapped to the two INT pins (config while in standby, then MEASURE):
 *   - TAP (single + double, Z-axis) -> INT1 -> PF1. The ADXL367 resolves
 *     single-vs-double IN HARDWARE: with both functions enabled, the single-tap
 *     interrupt fires only after the double-tap window validates/invalidates, so
 *     firmware reads STATUS_2 once on the interrupt (TAP_TWO set = double) with NO
 *     software window. Reading STATUS_2 clears the tap flags and re-arms.
 *   - ACTIVITY (referenced, gravity-removed motion) -> INT2 -> PF0. Must be acked
 *     by reading STATUS (LINKLOOP = 00). Drives the motion soft-breath.
 *
 * Running mode: measurement, +/-2 g, 100 Hz (FILTER_CTL = 0x23, the reset default
 * written explicitly). Data-sheet current 0.89 uA @ 100 Hz. Tap/activity thresholds
 * are BARE-CARD starting points; re-tune enclosed (same flow as the LIS2DH12).
 */
#ifndef ADXL367_H
#define ADXL367_H

#include <stdint.h>

/* ---- register addresses (ADXL367 data sheet Rev. B, Table 11) ---- */
#define ADXL_DEVID_AD       0x00   /* -> 0xAD                                         */
#define ADXL_PART_ID        0x02   /* -> 0xF7 (ADXL362 is 0xF2; check 0xF7 specifically) */
#define ADXL_STATUS         0x0B   /* ERR(7) AWAKE(6) INACT(5) ACT(4) ... DATA_RDY(0) */
#define ADXL_SOFT_RESET     0x1F   /* write 0x52 ('R') to reset                       */
#define ADXL_THRESH_ACT_H   0x20   /* THRESH_ACT[12:6]                                */
#define ADXL_THRESH_ACT_L   0x21   /* THRESH_ACT[5:0] << 2                            */
#define ADXL_TIME_ACT       0x22
#define ADXL_ACT_INACT_CTL  0x27
#define ADXL_INTMAP1_LOWER  0x2A   /* INT_LOW(7) ... ACT(4) ... DATA_RDY(0)          */
#define ADXL_INTMAP2_LOWER  0x2B
#define ADXL_FILTER_CTL     0x2C   /* RANGE[7:6] I2C_HS(5) EXT_SAMPLE(3) ODR[2:0]     */
#define ADXL_POWER_CTL      0x2D   /* NOISE[5:4] WAKEUP(3) AUTOSLEEP(2) MEASURE[1:0]  */
#define ADXL_TAP_THRESH     0x2F
#define ADXL_TAP_DUR        0x30   /* 625 us/LSB max tap width                        */
#define ADXL_TAP_LATENT     0x31   /* 1.25 ms/LSB; 0 disables double-tap             */
#define ADXL_TAP_WINDOW     0x32   /* 1.25 ms/LSB double-tap window                   */
#define ADXL_INTMAP1_UPPER  0x3A   /* ... TAP_TWO(1) TAP_ONE(0)                       */
#define ADXL_INTMAP2_UPPER  0x3B
#define ADXL_AXIS_MASK      0x43   /* TAP_AXIS[5:4] ; ACT_INACT_{Z,Y,X}[2:0] block   */
#define ADXL_STATUS_2       0x45   /* ... TAP_TWO(1) TAP_ONE(0)                       */

/* ---- expected read-only ID values ---- */
#define ADXL_DEVID_AD_VAL   0xAD
#define ADXL_PART_ID_VAL    0xF7

/* ---- bit masks (bit0/bit1 shared by STATUS_2 and INTMAP*_UPPER; bit4 by STATUS
 *      and INTMAP*_LOWER, which is why these double as routing values) ---- */
#define ADXL_STATUS2_TAP_ONE_bm  (1u << 0)   /* single-tap flag / route bit */
#define ADXL_STATUS2_TAP_TWO_bm  (1u << 1)   /* double-tap flag / route bit */
#define ADXL_STATUS_ACT_bm       (1u << 4)   /* activity flag / route bit   */

/* ---- config words ---- */
#define ADXL_SOFT_RESET_CODE 0x52

/* FILTER_CTL: RANGE=00 (+/-2 g), I2C_HS=1 (bit5, keep default), ODR=011 (100 Hz).
 * Equals the reset default 0x23; written explicitly so the intent is on the page. */
#define ADXL_CFG_FILTER_CTL  0x23

/* POWER_CTL: MEASURE[1:0]=10 (measurement mode); NOISE=00, WAKEUP=0, AUTOSLEEP=0.
 * Always-measurement (0.89 uA) -- no wake-up mode, so no first-tap-on-motion corner. */
#define ADXL_CFG_POWER_CTL   0x02

/* ACT_INACT_CTL: LINKLOOP=00, INACT_EN=00 (off), ACT_EN=11 (referenced activity).
 * Referenced activity removes the static 1 g so motion, not gravity, trips INT2. */
#define ADXL_CFG_ACT_INACT   0x03

/* AXIS_MASK: TAP_AXIS=10 (Z, a tap on the card face/back); activity on all axes.
 * BARE-CARD: the ADXL367 taps ONE axis (unlike the ST multi-axis click), so Z is a
 * choice -- confirm the real tap direction on the bench. */
#define ADXL_CFG_AXIS_MASK   0x20

/* INT routing: TAP_ONE -> INT1 (UPPER bit0); ACTIVITY -> INT2 (LOWER bit4).
 * INT_LOW (LOWER bit7) left 0 = active-high push/pull, matching PF0/PF1 rising-edge. */
#define ADXL_CFG_INTMAP1_UPPER  ADXL_STATUS2_TAP_ONE_bm   /* 0x01: tap  -> INT1 */
#define ADXL_CFG_INTMAP2_LOWER  ADXL_STATUS_ACT_bm        /* 0x10: motion -> INT2 */

/* ---- tunables (BARE-CARD starting points; re-tune with brace + shell) ----
 * The enclosed stack makes taps sharper/lower-amplitude, so these will feel wrong
 * bare; re-tune on the bench (seat -> test -> lift -> adjust). Non-zero TAP_LATENT
 * is what enables double-tap. Exact g / ms mapping per the data sheet tap section. */
#define ADXL_CFG_TAP_THRESH  0x30   /* 8-bit tap threshold (mid); bench-tune         */
#define ADXL_CFG_TAP_DUR     0x10   /* 16 * 625 us = 10 ms max tap width; bench-tune */
#define ADXL_CFG_TAP_LATENT  0x20   /* 32 * 1.25 ms = 40 ms latency (non-zero = double-tap on) */
#define ADXL_CFG_TAP_WINDOW  0xC0   /* 192 * 1.25 ms = 240 ms double-tap window      */

/* THRESH_ACT (13-bit referenced-activity threshold) + TIME_ACT confirm samples.
 * Sets motion sensitivity for the soft-breath; BARE-CARD, bench-tune. */
#define ADXL_CFG_THRESH_ACT_H 0x00
#define ADXL_CFG_THRESH_ACT_L 0xC8   /* THRESH_ACT[5:0]=0x32 (=50 counts) << 2       */
#define ADXL_CFG_TIME_ACT     0x02   /* activity confirm samples; bench-tune         */

/* ---- API (mirrors the old LIS2DH12 shape so main.c changes stay small) ---- */
uint8_t adxl367_present(void);        /* 0 = DEVID_AD + PART_ID match           */
uint8_t adxl367_init_tap(void);       /* full config: tap->INT1, activity->INT2 */
uint8_t adxl367_read_tap(void);       /* read STATUS_2 (clears+re-arms); tap flags */
void    adxl367_clear_tap(void);      /* read STATUS_2 to drop the tap latch      */
void    adxl367_clear_activity(void); /* read STATUS to ack the INT2 activity     */

#endif /* ADXL367_H */
