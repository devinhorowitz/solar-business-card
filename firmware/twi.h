/*
 * twi.h  --  minimal blocking TWI0 host (I2C master) for SOLAR-GLOW DRH.
 *
 * Header-only. One bus (ADXL367 accel @ 0x1D + NT3H tag @ 0x55 + MB85RC512TY FRAM @ 0x50), low speed, no IRQ,
 * no smart mode. Pins are PC2/SDA + PC3/SCL via PORTMUX.TWIROUTEA = ALT2
 * (set in main, not here). External 4.7k pull-ups to VS are fitted, so the
 * internal pull-ups are left off.
 *
 * Bus timing: F_CPU = 1 MHz, target ~100 kHz. The SCL divider has a floor of
 * 10 CLK_PER, so MBAUD = 0 gives 1 MHz / 10 = 100 kHz exactly (same bus speed
 * as the old 4 MHz build, which used MBAUD = 15). 100 kHz is therefore also the
 * ceiling at this clock; 400 kHz fast-mode would need a faster CLK_PER. All
 * transactions are polled; every wait is DOUBLY bounded -- a bus-error /
 * arbitration escape for flagged faults, and a spin budget (TWI_SPIN_MAX) for
 * the un-flagged wedge: a client stretching SCL low forever. The MCTRLA
 * inactive-bus TIMEOUT can NOT bound that case -- per the datasheet (27.5,
 * MCTRLA.TIMEOUT) it is SMBus bus-FREE detection: it only moves the bus state
 * to Idle, sets no MSTATUS flag a wait could see, and a stretched-low SCL is
 * not an "inactive" (idle-high) bus in the first place. It is kept enabled for
 * what it does do: un-sticking the Busy->Idle state so a new transaction can
 * start after a glitch. The stretch hazard is real on this bus -- the NT3H2211
 * stretches by POR default, and NXP warns an interrupted read can leave it
 * stretching "infinitely" -- and before the spin bound it meant a hang: fatal
 * pre-WDT (init/provisioning run before the watchdog is armed, and harvested
 * light can power a spinning core indefinitely), an 8 s WDT reset after.
 *
 * Return convention: 0 = OK, non-zero = fault (NACK or bus error). Callers
 * treat any non-zero as "accel not talking" and skip gracefully.
 */
#ifndef TWI_H
#define TWI_H

#include <avr/io.h>
#include <stdint.h>

#define TWI_MBAUD_100K  0    /* 1 MHz / (10 + 2*0) = 100 kHz @ F_CPU = 1 MHz */

/* Spin budget for the polled MSTATUS waits (see header note): the escape for a
 * clock-stretching client, which sets NO flag and would otherwise spin forever.
 * One twi_wait() iteration is 10 cycles at -Os (LDS+MOV+AND+BRNE+SUBI+SBC+BRNE,
 * disassembly-verified), so 8192 spins ~ 82 ms at 1 MHz -- orders beyond any legitimate
 * transfer (a byte is ~90 us) or NT3H RF-arbitration stretch (~ms), and far
 * under the 8.192 s watchdog even across a multi-wait transaction chain. On
 * expiry the wait reports a plain fault: the caller STOPs and skips, and a
 * still-stretched bus just faults each later transaction the same bounded way
 * -- degraded, never hung. */
#define TWI_SPIN_MAX    8192u

/* Bounded wait for any flag in `bits` (RIF/WIF/BUSERR/ARBLOST): returns the
 * MSTATUS snapshot that satisfied it, or 0 on spin-budget expiry. Callers must
 * still inspect the snapshot -- error flags can arrive TOGETHER with WIF (the
 * datasheet sets WIF alongside ARBLOST/BUSERR, and RXACK is only valid when
 * both are clear), so "the wait ended" never by itself means "success". */
static inline uint8_t twi_wait(uint8_t bits)
{
    for (uint16_t spin = TWI_SPIN_MAX; spin; spin--) {
        uint8_t st = TWI0.MSTATUS;
        if (st & bits) return st;
    }
    return 0;
}

static inline void twi_init(void)
{
    TWI0.MBAUD   = TWI_MBAUD_100K;
    /* host on; enable the inactive-bus timeout so a wedged bus (SCL stuck low)
     * recovers into a BUSERR instead of hanging a polled wait forever. */
    TWI0.MCTRLA  = TWI_TIMEOUT_200US_gc | TWI_ENABLE_bm;
    TWI0.MSTATUS = TWI_BUSSTATE_IDLE_gc;      /* force bus state to IDLE */
}

/* address phase. read=0 write, read=1 read. returns 0 ok, 1 fault. */
static inline uint8_t twi_start(uint8_t addr7, uint8_t read)
{
    uint8_t st;
    TWI0.MADDR = (uint8_t)((addr7 << 1) | (read & 1u));
    if (read) {
        /* The address phase is a WRITE regardless of direction: if no device
         * ACKs, WIF (not RIF) is set together with RXACK. Wait on WIF/BUSERR/
         * ARBLOST here too -- RIF and WIF are mutually exclusive, so anything
         * but RIF (or a spin expiry, st = 0) is an address-NACK / fault. */
        st = twi_wait(TWI_RIF_bm | TWI_WIF_bm | TWI_BUSERR_bm | TWI_ARBLOST_bm);
        if (!(st & TWI_RIF_bm)) return 1;
    } else {
        st = twi_wait(TWI_WIF_bm | TWI_BUSERR_bm | TWI_ARBLOST_bm);
        if (!(st & TWI_WIF_bm) || (st & (TWI_BUSERR_bm | TWI_ARBLOST_bm)))
            return 1;                     /* wedge (st=0), bus error, or arb lost
                                           * (RXACK is not valid on those) */
        if (st & TWI_RXACK_bm) return 1;  /* address NACKed */
    }
    return 0;
}

/* write one data byte. returns 0 ok (ACK), 1 fault (NACK / bus error). */
static inline uint8_t twi_write(uint8_t b)
{
    uint8_t st;
    TWI0.MDATA = b;
    st = twi_wait(TWI_WIF_bm | TWI_BUSERR_bm | TWI_ARBLOST_bm);
    if (!(st & TWI_WIF_bm) || (st & (TWI_BUSERR_bm | TWI_ARBLOST_bm))) return 1;
    return (st & TWI_RXACK_bm) ? 1 : 0;
}

/* read one data byte into *out. ack=1 -> ACK + clock next byte; ack=0 -> NACK
 * + STOP. returns 0 ok, 1 fault (bus error / arb lost). The status is returned
 * separately from the data so a real 0xFF byte is never confused with an error. */
static inline uint8_t twi_read(uint8_t ack, uint8_t *out)
{
    uint8_t st = twi_wait(TWI_RIF_bm | TWI_BUSERR_bm | TWI_ARBLOST_bm);
    if (!(st & TWI_RIF_bm) || (st & (TWI_BUSERR_bm | TWI_ARBLOST_bm))) return 1;
    *out = TWI0.MDATA;
    if (ack) TWI0.MCTRLB = TWI_MCMD_RECVTRANS_gc;                 /* ACK, go again */
    else     TWI0.MCTRLB = TWI_ACKACT_bm | TWI_MCMD_STOP_gc;      /* NACK + STOP   */
    return 0;
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

/* read n registers starting at reg into dst. burst (n>1) sets sub-addr bit7, an
 * ST/LIS2DH12 auto-increment convention. NOTE: the ADXL367 does NOT use bit7 (it
 * auto-increments natively), so a multi-byte read of the accel would send the wrong
 * sub-address -- the accel driver only reads single bytes, so this never bites.
 * returns 0 ok, 1 fault. */
static inline uint8_t twi_reg_read(uint8_t addr7, uint8_t reg, uint8_t *dst, uint8_t n)
{
    if (n == 0) return 0;
    if (twi_start(addr7, 0))                          { twi_stop(); return 1; }
    if (twi_write((n > 1) ? (uint8_t)(reg | 0x80) : reg)) { twi_stop(); return 1; }
    if (twi_start(addr7, 1))                          { twi_stop(); return 1; }  /* repeated start */
    for (uint8_t i = 0; i < n; i++)
        if (twi_read((uint8_t)(i < (n - 1)), &dst[i])) {  /* ACK all but last; last NACKs + STOPs */
            twi_stop();                                   /* bus fault: STOP so the target can't clock-stretch (dst not trustworthy) */
            return 1;
        }
    return 0;
}

#endif /* TWI_H */
