/*
 * fram.h  --  RAMXEED/Fujitsu MB85RC512TY (512 kbit = 64 KB I2C FeRAM) driver.
 *
 * U7 is an I2C target on the same TWI0 host bus as the accel and the NFC tag
 * (SDA=PC2, SCL=PC3, TWIROUTEA=ALT2, ext 4.7k pull-ups to VS). 7-bit address
 * 0x50 (A0/A1/A2 grounded); no clash with the accel (0x1D) or NT3H tag (0x55).
 *
 * Power (option A, 2026-07-23 back-power fix): VDD is on the ALWAYS-ON VS rail
 * (VNFC now gates the tag alone), parked in the part's own I2C SLEEP mode
 * (IZZ 0.20 uA typ). fram_wake() brings it to standby (~450 us regulator
 * recovery, ACK-polled, bounded); fram_sleep() parks it again -- NACK-tolerant,
 * so calling it on an already-sleeping or absent part is harmless.
 *
 * Memory model: linear 16-bit byte address 0x0000..0xFFFF (64 KB). Unlike the
 * NFC EEPROM, FeRAM writes commit at the STOP -- there is NO post-write settle
 * delay and no busy poll (datasheet: "does not need a polling sequence after
 * writing"). Endurance is ~1e13 cycles, so per-event logging is effectively free.
 *
 * Transactions (datasheet):
 *   write  = [S][0x50|W][addrHi][addrLo][data..][P]
 *   read   = [S][0x50|W][addrHi][addrLo][Sr][0x50|R][data..(NACK last)][P]
 * We use the twi.h primitives directly (twi_reg_* assume an 8-bit sub-address,
 * but the FRAM needs a 16-bit one).
 */
#ifndef FRAM_H
#define FRAM_H

#include <stdint.h>
#include "board.h"          /* FRAM_ADDR */

#define FRAM_SIZE   65536u   /* 512 kbit = 64 KB, 16-bit address space */

/* ---- API ----  0 = OK, non-zero = fault (bus/NACK), same as twi.h / nfc.h ---- */

/* Sleep-mode control (the part rides always-on VS; see board.h).
 * fram_wake():  bounded ACK-poll through the ~450 us Sleep-exit recovery the
 *   addressing START triggers. Returns 0 when the FRAM answers (standby),
 *   non-zero if absent. Safe on a part that was never asleep (first-try ACK).
 * fram_sleep(): datasheet entry sequence (S+F8h, addr word, Sr+86h). Best-effort
 *   and NACK-tolerant with one tREC retry; harmless on a sleeping/absent part.
 *   Call after every use -- and each poll tick re-parks defensively (main.c,
 *   FRAM_RESLEEP_EVERY_POLL) since the wake's address-selectivity is unspec'd. */
uint8_t fram_wake(void);
void    fram_sleep(void);

/* presence: 1 if the FRAM ACKs its address, else 0. A SLEEPING part reads
 * absent (and starts waking) -- use fram_wake() for the settled answer. */
uint8_t fram_present(void);

/* read/write `len` bytes at 16-bit `addr`. Both reject addr+len > FRAM_SIZE.
 * Part must be awake (call fram_wake() first if it may be sleeping). */
uint8_t fram_read (uint16_t addr, uint8_t *dst, uint16_t len);
uint8_t fram_write(uint16_t addr, const uint8_t *src, uint16_t len);

#endif /* FRAM_H */
