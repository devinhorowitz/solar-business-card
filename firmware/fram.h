/*
 * fram.h  --  RAMXEED/Fujitsu MB85RC512TY (512 kbit = 64 KB I2C FeRAM) driver.
 *
 * U7 is an I2C target on the same TWI0 host bus as the accel and the NFC tag
 * (SDA=PC2, SCL=PC3, TWIROUTEA=ALT2, ext 4.7k pull-ups to VS). 7-bit address
 * 0x50 (A0/A1/A2 grounded); no clash with the accel (0x1D) or NT3H tag (0x55).
 *
 * Power: VDD is on VNFC -- the SAME U6 high-side load switch that gates the NFC
 * tag (enable = NFC_EN / PA7, active-HIGH; see board.h). So the FRAM is only
 * alive while VNFC is up. fram_power_on() raises NFC_EN and ACK-polls the FRAM;
 * fram_power_off() drops it. If the NFC tag is used in the same window, one
 * power-on covers both parts.
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
#include "board.h"          /* FRAM_ADDR, NFC_EN_PORT / NFC_EN_PIN_bm */

#define FRAM_SIZE   65536u   /* 512 kbit = 64 KB, 16-bit address space */

/* ---- API ----  0 = OK, non-zero = fault (bus/NACK), same as twi.h / nfc.h ---- */

/* power-gate control (shares VNFC / NFC_EN with the NFC tag; see board.h).
 * fram_power_on(): raise NFC_EN, then bounded ACK-poll of FRAM_ADDR after the
 *   load-switch soft-start. Returns 0 when the FRAM answers, non-zero on timeout
 *   (absent / EN not wired / VNFC dead). Idempotent with nfc_power_on(): if the
 *   tag was already powered, the FRAM is up too and this just re-confirms.
 * fram_power_off(): drive NFC_EN LOW (VNFC off). Only call when neither the FRAM
 *   nor the NFC tag is needed. */
uint8_t fram_power_on(void);
void    fram_power_off(void);

/* presence: 1 if the FRAM ACKs its address, else 0. VNFC must already be up. */
uint8_t fram_present(void);

/* read/write `len` bytes at 16-bit `addr`. Both reject addr+len > FRAM_SIZE.
 * VNFC must be up (call fram_power_on() first). */
uint8_t fram_read (uint16_t addr, uint8_t *dst, uint16_t len);
uint8_t fram_write(uint16_t addr, const uint8_t *src, uint16_t len);

#endif /* FRAM_H */
