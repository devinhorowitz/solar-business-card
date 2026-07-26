/*
 * fram.c  --  MB85RC512TY (512 kbit = 64 KB I2C FeRAM) bring-up + linear R/W.
 *
 * Transactions are the datasheet ones, built on the twi.h primitives. The read
 * follows the standard "set the 16-bit address pointer, then read" idiom: an
 * address phase (SA+W, addrHi, addrLo) followed by a repeated START with SA+R
 * for the data phase. Unlike the NFC EEPROM there is NO post-write settle delay
 * and no busy poll (datasheet: "does not need a polling sequence after
 * writing"), so fram_write returns as soon as the STOP is on the wire.
 * Precisely: each byte is committed as it is acknowledged -- "the data will be
 * written to FeRAM right after the ACK response finished" (Page Write section)
 * -- NOT batched to the STOP. The practical difference is failure atomicity: a
 * multi-byte fram_write aborted mid-way (bus fault) leaves the bytes already
 * ACKed permanently in memory, so a record that must not be read half-written
 * needs its own valid/commit marker written last. The boot record is safe by
 * construction (its magic is re-checked and re-seeded on read).
 *
 * Power (option A, 2026-07-23 back-power fix): VDD rides the ALWAYS-ON VS rail
 * -- not the gated VNFC -- so the bus pull-ups (also on VS) can never sit above
 * the part's own rail (abs-max VIN <= VDD+0.5; design-notes deep-dive addendum).
 * Standing cost is held at IZZ (0.20 uA typ / 10 uA max hot) by parking the part
 * in its I2C SLEEP mode: fram_sleep() issues the datasheet entry sequence
 * (S + F8h, device-address word, Sr + 86h), fram_wake() ACK-polls through the
 * ~450 us regulator recovery that a START at its address triggers. Both are
 * bounded and NACK-tolerant -- an absent part faults instead of hanging.
 */
#include "board.h"          /* FRAM_ADDR, F_CPU */
#include "fram.h"
#include "twi.h"
#include <util/delay.h>

/* ---- Sleep-mode timing (datasheet SLEEP section) ---- */
#define FRAM_TREC_US        600   /* regulator recovery after a wake (tREC 450 us + margin) */
#define FRAM_WAKE_TRIES     8     /* bounded ACK-poll budget (absent part -> fault, no hang) */

/* presence: 1 if the FRAM ACKs its address, else 0. Address-only ping
 * (START, SA+W, [N]ACK, STOP) -- no data written. NOTE a SLEEPING part NACKs
 * (reads absent) while the START itself begins its recovery -- use fram_wake()
 * for the settled answer. */
uint8_t fram_present(void)
{
    uint8_t up = (twi_start(FRAM_ADDR, 0) == 0);
    twi_stop();
    return up ? 1u : 0u;
}

void fram_sleep(void)
{
    /* Datasheet sleep entry: S + F8h, ACK; device-address word, ACK; Sr + 86h,
     * ACK -> sleep. Best-effort BY DESIGN: an already-sleeping part (if its wake
     * is address-selective) NACKs the F8h frame and simply stays asleep, while a
     * part our own F8h frame just woke (if wake is address-indiscriminate) NACKs
     * until its regulator recovers -- so one retry after tREC puts it back down.
     * Every path leaves a STOP on the wire; nothing here can hang. (F8h/86h are
     * reserved-address frames: 0x7C<<1|W and 0x43<<1|W -- no clash with the
     * accel @0x1D or tag @0x55, which simply don't ACK them.) */
    for (uint8_t t = 0; t < 2; t++) {
        if (twi_start(0x7C, 0) == 0 &&                      /* F8h frame        */
            twi_write((uint8_t)(FRAM_ADDR << 1)) == 0 &&    /* device addr word */
            twi_start(0x43, 0) == 0) {                      /* Sr + 86h frame   */
            twi_stop();
            return;                       /* all three ACKed -> part is asleep */
        }
        twi_stop();
        /* Only delay if another attempt will actually use it. The common case on
         * this card is the per-poll defensive re-park (FRAM_RESLEEP_EVERY_POLL) of
         * an ALREADY-sleeping part, which NACKs both attempts -- so a delay after
         * the final one was pure busy-wait: 600 us of ACTIVE-mode spin, every poll,
         * forever, for nothing. Halving it here costs nothing in behaviour (the
         * retry still gets its full tREC settle). */
        if (t == 0)
            _delay_us(FRAM_TREC_US);      /* maybe mid-recovery: settle, retry once */
    }
}

uint8_t fram_wake(void)
{
    /* A sleeping part NACKs until its regulator recovers, and the very START
     * that addresses it begins that recovery (datasheet: exit on START +
     * device-address word, standby after tREC). Bounded poll: an awake part
     * ACKs on the first try, an absent part returns a fault, never a hang. */
    for (uint8_t t = 0; t < FRAM_WAKE_TRIES; t++) {
        if (fram_present()) return 0;     /* address ACKed -> awake in standby */
        _delay_us(FRAM_TREC_US);
    }
    return 1;                             /* absent / dead bus */
}

/* Open the address phase and leave it running: SA+W then the 16-bit pointer.
 * Caller continues with data bytes (write) or a repeated START (read), and
 * STOPs on the fault path. Returns 0 ok, 1 fault. */
static uint8_t fram_setaddr(uint16_t addr)
{
    if (twi_start(FRAM_ADDR, 0))         return 1;   /* SA + write */
    if (twi_write((uint8_t)(addr >> 8))) return 1;   /* addr[15:8] */
    if (twi_write((uint8_t)(addr)))      return 1;   /* addr[7:0]  */
    return 0;
}

uint8_t fram_write(uint16_t addr, const uint8_t *src, uint16_t len)
{
    if (len == 0) return 0;
    if ((uint32_t)addr + len > FRAM_SIZE) return 1;      /* reject overrun */
    if (fram_setaddr(addr)) { twi_stop(); return 1; }
    for (uint16_t i = 0; i < len; i++)
        if (twi_write(src[i])) { twi_stop(); return 1; }
    twi_stop();                 /* FeRAM commits at STOP -- no settle delay to wait out */
    return 0;
}

uint8_t fram_read(uint16_t addr, uint8_t *dst, uint16_t len)
{
    if (len == 0) return 0;
    if ((uint32_t)addr + len > FRAM_SIZE) return 1;
    if (fram_setaddr(addr))      { twi_stop(); return 1; }   /* set the pointer   */
    if (twi_start(FRAM_ADDR, 1)) { twi_stop(); return 1; }   /* repeated START + read */
    for (uint16_t i = 0; i < len; i++)
        if (twi_read((uint8_t)(i < (len - 1)), &dst[i])) {   /* ACK all but last (NACK+STOP) */
            twi_stop();                                       /* bus fault: STOP so the part can't clock-stretch */
            return 1;
        }
    return 0;                    /* last twi_read already issued the NACK + STOP */
}
