/*
 * twi.h  --  minimal blocking TWI0 host (I2C master) for SOLAR-GLOW DRH.
 *
 * Header-only. One bus, one device (LIS2DH12 @ 0x18), low speed, no IRQ,
 * no smart mode. Pins are PC2/SDA + PC3/SCL via PORTMUX.TWIROUTEA = ALT2
 * (set in main, not here). External 4.7k pull-ups to VS are fitted, so the
 * internal pull-ups are left off.
 *
 * Bus timing: F_CPU = 4 MHz, target ~100 kHz. MBAUD = 15 is the standard
 * AVR-Dx value for 100 kHz at 4 MHz with default rise time (datasheet
 * TWI baud equation). All transactions are polled; every wait has a
 * bus-error / arbitration escape so a wedged bus cannot hang the core.
 *
 * Return convention: 0 = OK, non-zero = fault (NACK or bus error). Callers
 * treat any non-zero as "accel not talking" and skip gracefully.
 */
#ifndef TWI_H
#define TWI_H

#include <avr/io.h>
#include <stdint.h>

#define TWI_MBAUD_100K  15   /* @ F_CPU = 4 MHz */

static inline void twi_init(void)
{
    TWI0.MBAUD   = TWI_MBAUD_100K;
    TWI0.MCTRLA  = TWI_ENABLE_bm;             /* host on, no IRQ, no smart mode */
    TWI0.MSTATUS = TWI_BUSSTATE_IDLE_gc;      /* force bus state to IDLE */
}

/* address phase. read=0 write, read=1 read. returns 0 ok, 1 fault. */
static inline uint8_t twi_start(uint8_t addr7, uint8_t read)
{
    TWI0.MADDR = (uint8_t)((addr7 << 1) | (read & 1u));
    if (read) {
        while (!(TWI0.MSTATUS & TWI_RIF_bm))
            if (TWI0.MSTATUS & (TWI_BUSERR_bm | TWI_ARBLOST_bm)) return 1;
    } else {
        while (!(TWI0.MSTATUS & TWI_WIF_bm))
            if (TWI0.MSTATUS & (TWI_BUSERR_bm | TWI_ARBLOST_bm)) return 1;
        if (TWI0.MSTATUS & TWI_RXACK_bm) return 1;   /* address NACKed */
    }
    return 0;
}

/* write one data byte. returns 0 ok (ACK), 1 fault (NACK / bus error). */
static inline uint8_t twi_write(uint8_t b)
{
    TWI0.MDATA = b;
    while (!(TWI0.MSTATUS & TWI_WIF_bm))
        if (TWI0.MSTATUS & (TWI_BUSERR_bm | TWI_ARBLOST_bm)) return 1;
    return (TWI0.MSTATUS & TWI_RXACK_bm) ? 1 : 0;
}

/* read one data byte. ack=1 -> ACK + clock next byte; ack=0 -> NACK + STOP. */
static inline uint8_t twi_read(uint8_t ack)
{
    while (!(TWI0.MSTATUS & TWI_RIF_bm))
        if (TWI0.MSTATUS & TWI_BUSERR_bm) return 0xFF;
    uint8_t b = TWI0.MDATA;
    if (ack) TWI0.MCTRLB = TWI_MCMD_RECVTRANS_gc;                 /* ACK, go again */
    else     TWI0.MCTRLB = TWI_ACKACT_bm | TWI_MCMD_STOP_gc;      /* NACK + STOP   */
    return b;
}

static inline void twi_stop(void)
{
    TWI0.MCTRLB = TWI_MCMD_STOP_gc;
}

/* write one register. returns 0 ok, 1 fault. */
static inline uint8_t twi_reg_write(uint8_t addr7, uint8_t reg, uint8_t val)
{
    if (twi_start(addr7, 0)) { twi_stop(); return 1; }
    if (twi_write(reg))      { twi_stop(); return 1; }
    if (twi_write(val))      { twi_stop(); return 1; }
    twi_stop();
    return 0;
}

/* read n registers starting at reg into dst. burst sets sub-addr bit7
 * (LIS2DH12 auto-increment). returns 0 ok, 1 fault. */
static inline uint8_t twi_reg_read(uint8_t addr7, uint8_t reg, uint8_t *dst, uint8_t n)
{
    if (n == 0) return 0;
    if (twi_start(addr7, 0))                          { twi_stop(); return 1; }
    if (twi_write((n > 1) ? (uint8_t)(reg | 0x80) : reg)) { twi_stop(); return 1; }
    if (twi_start(addr7, 1))                          { twi_stop(); return 1; }  /* repeated start */
    for (uint8_t i = 0; i < n; i++)
        dst[i] = twi_read((uint8_t)(i < (n - 1)));    /* ACK all but last; last NACKs + STOPs */
    return 0;
}

#endif /* TWI_H */
