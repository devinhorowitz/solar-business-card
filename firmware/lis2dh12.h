/*
 * lis2dh12.h  --  ST LIS2DH12 3-axis accel: register map + tap/activity config.
 *
 * Verified against datasheet en.DM00091513 (LIS2DH12). I2C, CS=VS so I2C mode,
 * SA0=GND so 7-bit address 0x18. INT1 -> MCU PF1, INT2 -> MCU PF0, both
 * active-HIGH (default INT polarity), so the MCU pins use a RISING edge sense.
 *
 * Wake model:
 *   - CLICK (single-tap, all axes, high-pass filtered) -> INT1 -> PF1.
 *     This is the primary "tap the card to light it up" gesture.
 *   - MOTION (inertial wake-up via the INT2 generator, INT2_CFG/THS/DURATION)
 *     -> INT2 -> PF0. A softer "the card moved / was picked up" nudge. Not
 *     latched, so it self-clears when motion stops. (The sleep-to-wake activity
 *     function is deliberately NOT used: it forces the ODR to 10 Hz when idle,
 *     which is exactly when a tap arrives, and the click engine cannot time a
 *     tap at 10 Hz. Keeping the data path at 100 Hz makes tap-from-rest work.)
 *
 * Running mode: low-power, 100 Hz ODR (CTRL_REG1 = 0x5F). Datasheet current
 * for LP is a few uA; see README power notes. ODR and click threshold are the
 * two knobs most likely to need a bench tweak.
 */
#ifndef LIS2DH12_H
#define LIS2DH12_H

#include <stdint.h>
#include "board.h"          /* LIS2DH12_ADDR */

/* ---- register addresses (verified) ---- */
#define LIS_WHO_AM_I        0x0F   /* -> 0x33 */
#define LIS_CTRL_REG0       0x1E
#define LIS_TEMP_CFG_REG    0x1F
#define LIS_CTRL_REG1       0x20
#define LIS_CTRL_REG2       0x21
#define LIS_CTRL_REG3       0x22
#define LIS_CTRL_REG4       0x23
#define LIS_CTRL_REG5       0x24
#define LIS_CTRL_REG6       0x25
#define LIS_REFERENCE       0x26   /* HP-filter reference; read to zero the filter (HPM=00) */
#define LIS_STATUS_REG      0x27
#define LIS_OUT_X_L         0x28
#define LIS_INT2_CFG        0x34
#define LIS_INT2_SRC        0x35
#define LIS_INT2_THS        0x36
#define LIS_INT2_DURATION   0x37
#define LIS_CLICK_CFG       0x38
#define LIS_CLICK_SRC       0x39
#define LIS_CLICK_THS       0x3A
#define LIS_TIME_LIMIT      0x3B
#define LIS_TIME_LATENCY    0x3C
#define LIS_TIME_WINDOW     0x3D
#define LIS_ACT_THS         0x3E
#define LIS_ACT_DUR         0x3F

#define LIS_WHO_AM_I_VAL    0x33

/* ---- config values (verified bit-by-bit; see .c for the full decode) ---- */
#define LIS_CFG_CTRL_REG0   0x90   /* SDO_PU_DISC=1 (SA0 grounded, drop pull-up); mandatory low bits = 0010000 */
#define LIS_CFG_CTRL_REG1   0x5F   /* ODR=100Hz (0101), LPen=1, Zen/Yen/Xen=1  -> low-power, all axes */
#define LIS_CFG_CTRL_REG2   0x06   /* HPCLICK=1 (bit2) + HP_IA2=1 (bit1): high-pass BOTH the click path
                                      and the INT2 motion path, so the static 1g gravity DC is stripped
                                      and a tilt cannot hold either interrupt asserted */
#define LIS_CFG_CTRL_REG3   0x80   /* I1_CLICK=1: click interrupt -> INT1 pad */
#define LIS_CFG_CTRL_REG4   0x80   /* BDU=1, FS=+/-2g, HR=0 (LP mode); 1 LSb(click) ~= 16 mg */
#define LIS_CFG_CTRL_REG5   0x00   /* no reboot/FIFO; click has its own latch via CLICK_THS bit7 */
#define LIS_CFG_CTRL_REG6   0x20   /* I2_IA2=1 (bit5): inertial wake-up (INT2 generator) -> INT2 pad;
                                      INT_POLARITY=0 active-high. NOT I2_ACT: the sleep-to-wake activity
                                      function dropped the ODR to 10 Hz when idle, which broke tap
                                      detection from rest, so motion is sourced from the IA2 generator
                                      and the data path stays at 100 Hz (see header). */

/* ---- tunables (bench-set; safe starting points) ----
 * At +/-2g, click threshold step ~= 16 mg/LSb. At 100 Hz ODR the TIME_*
 * registers step at 1/ODR = 10 ms each. */
#if USE_DOUBLE_TAP
#define LIS_CLICK_CFG_VAL   0x3F   /* single + double, X+Y+Z (firmware picks which fired via CLICK_SRC) */
#else
#define LIS_CLICK_CFG_VAL   0x15   /* single-click X+Y+Z (XS|YS|ZS) only */
#endif
#define LIS_CLICK_THS_RAW   0x30   /* ~0.75 g. lower = more sensitive. (bit7 LIR_Click added in .c) */
#define LIS_TIME_LIMIT_VAL  0x0A   /* 100 ms: max over-threshold dwell still counted as a click */
#define LIS_TIME_LATENCY_VAL 0x05  /* 50 ms: dead time after a click (debounce / spacing floor) */
#define LIS_TIME_WINDOW_VAL 0x0A   /* 100 ms: 2nd-tap window. Worst-case DCLICK assertion =
                                    * LATENCY+WINDOW+LIMIT = 50+100+100 = 250 ms, which must stay
                                    * UNDER board.h DTAP_WINDOW_MS or a slow double reads as single.
                                    * Widen this only if DTAP_WINDOW_MS is widened to match. */
/* Motion wake (INT2 inertial-wake generator). Replaces the old sleep-to-wake
 * activity engine. INT2_CFG ORs the three high-event axis bits so any-axis
 * motion above INT2_THS for INT2_DURATION raises INT2. The threshold runs on
 * high-pass-filtered data (gravity removed, see CTRL_REG2), so it reads dynamic
 * motion only, not tilt. */
#define LIS_INT2_CFG_VAL    0x2A   /* ZHIE|YHIE|XHIE, AOI=0 (OR) -> any-axis motion */
#define LIS_INT2_THS_VAL    0x10   /* ~0.25 g at +/-2g (1 LSb = 16 mg); lower = more sensitive */
#define LIS_INT2_DUR_VAL    0x00   /* 0 = fire on first over-threshold sample; raise (x10 ms @100Hz) to debounce */

/* CLICK_SRC (0x39) bits */
#define LIS_CLICK_IA_bm     0x40
#define LIS_CLICK_DCLICK_bm 0x20   /* double-click detected */
#define LIS_CLICK_SCLICK_bm 0x10   /* single-click detected */

/* ---- API ---- 0 = OK, non-zero = fault (bus/NACK) ---- */
uint8_t lis2dh12_present(void);      /* 1 if WHO_AM_I == 0x33, else 0 */
uint8_t lis2dh12_init_tap(void);     /* full config: tap->INT1, activity->INT2 */
uint8_t lis2dh12_read_click(void);   /* read CLICK_SRC (clears the latch); returns the bits */
void    lis2dh12_clear_click(void);  /* read CLICK_SRC to drop the latched INT1 (discards value) */

#endif /* LIS2DH12_H */
