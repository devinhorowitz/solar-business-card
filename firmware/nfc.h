/*
 * nfc.h  --  NXP NT3H2211 (NTAG I2C plus, 2K) driver: power-gated NDEF write.
 *
 * Verified against datasheet NT3H2111_2211 Rev 3.6 (datasheets/NT3H2111_2211.pdf).
 * U5 is an I2C TARGET on the same TWI0 host bus as the accel (SDA=PC2, SCL=PC3,
 * TWIROUTEA=ALT2, ext 4.7k pull-ups). 7-bit address 0x55 (no clash with the accel
 * at 0x18). We reuse the twi.h primitives directly for the NT3H block/register
 * transactions -- NOT twi_reg_read(), whose bit7 sub-address auto-increment is a
 * LIS2DH12-ism the NT3H does not use.
 *
 * The tag's VCC is power-gated by a high-side load switch enabled on NFC_EN (PA7,
 * active-HIGH); see board.h. The chip has no sleep state and draws ~195 uA from
 * VCC continuously, so VCC is kept OFF and only switched on around an I2C access.
 * nfc_power_on() raises NFC_EN and waits for the tag to boot (bounded ACK-poll);
 * nfc_power_off() drops it. Both the RF read of the static NDEF by a phone AND the
 * FD field-detect wake run on the phone's field power and need NO VCC (datasheet
 * 8.4) -- power-gating only affects the MCU<->tag I2C side.
 *
 * Job: write a contact NDEF into the tag EEPROM (one-time provisioning). The NDEF
 * is RF-readable by a phone even with the supercap flat, and is re-writable.
 * (FD-wake itself needs no driver code: the chip's POR/config default pulls FD low
 * on field-present, and main.c senses the PA6 falling edge -- see board.h/main.c.)
 *
 * --- memory model (datasheet, I2C perspective; Table 6/7, sec 8.3.2/8.3.8/9.7) ---
 *   - access is in 16-byte BLOCKS, addressed by a 1-byte block address (MEMA).
 *   - block 0x00: I2C-addr byte (byte0, reads back 04h) + UID + lock + the
 *     Capability Container (CC) at bytes 12..15. WRITING block 0 changes the I2C
 *     address (byte0), so we NEVER touch it. The CC ships = E1 10 6D 00
 *     (NDEF-capable, 872 B in sector 0), so no CC write is needed.
 *   - block 0x01 = first user-memory block = WHERE THE NDEF STARTS (NFC page 04h).
 *   - the NDEF is an NFC-Forum Type-2 TLV: 03h, <len>, <NDEF message>, FEh, padded
 *     to a whole block with 00h. <len> is 1 byte if <255, else FFh + 2-byte BE.
 *   - EEPROM block program = ~4 ms; SRAM = ~0.4 ms. After a block-write STOP the
 *     host MUST stay off the bus >= ~4 ms or the write is corrupted (sec 9.7
 *     WARNING) -- so we delay, we do NOT poll EEPROM_WR_BUSY right after a write.
 *
 * --- registers ---
 *   - config registers (EEPROM, default-after-POR) live at I2C block 0x3A.
 *   - session registers (volatile, loaded from config at POR) live at I2C block
 *     0xFE and are reachable ONLY via the sec 9.8 register op (MEMA=FEh).
 *   - NC_REG is at register offset 0x00; NS_REG (session only) at offset 0x06.
 *     (FD-output config in NC_REG is left at its POR default -- FD is not used.)
 */
#ifndef NFC_H
#define NFC_H

#include <stdint.h>
#include "board.h"          /* NT3H_ADDR */

/* ---- block addresses (I2C perspective; verified Table 6/7, sec 8.3.12) ---- */
#define NFC_BLK_USER0     0x01   /* first user block = NDEF start (NFC page 04h) */
#define NFC_BLK_CONFIG    0x3A   /* configuration registers (EEPROM) -- untouched */
#define NFC_BLK_SESSION   0xFE   /* session registers (via sec 9.8 register op)  */
#define NFC_BLK_EEPROM_TOP 0x7A  /* last EEPROM user block, 2K part (sec 9.7)     */
#define NFC_BLOCK_SZ      16

/* ---- register offsets within a register block (Table 11/12) ---- */
#define NFC_REG_NC          0x00   /* NC_REG  */
#define NFC_REG_LAST_NDEF   0x01   /* LAST_NDEF_BLOCK */
#define NFC_REG_NS          0x06   /* NS_REG (session block only) */

/* ---- NC_REG bit fields (Table 13) ---- */
#define NFC_NC_FD_OFF_msk   0x30   /* bits 5:4 */
#define NFC_NC_FD_ON_msk    0x0C   /* bits 3:2 */
#define NFC_NC_FD_msk       (NFC_NC_FD_OFF_msk | NFC_NC_FD_ON_msk)  /* 0x3C */
/* FD_ON=00b (field on) + FD_OFF=00b (field off): the field-present mode. */
#define NFC_NC_FD_FIELD     0x00

/* ---- NS_REG bits (Table 14, session block offset 0x06) ---- */
#define NFC_NS_NDEF_DATA_READ_bm   0x80
#define NFC_NS_I2C_LOCKED_bm       0x40
#define NFC_NS_RF_LOCKED_bm        0x20
#define NFC_NS_SRAM_I2C_READY_bm   0x10
#define NFC_NS_SRAM_RF_READY_bm    0x08
#define NFC_NS_EEPROM_WR_ERR_bm    0x04
#define NFC_NS_EEPROM_WR_BUSY_bm   0x02
#define NFC_NS_RF_FIELD_PRESENT_bm 0x01

/* factory CC (block 0 bytes 12..15) for an NDEF-capable tag (sec 8.3.8/8.3.10) */
#define NFC_CC0  0xE1
#define NFC_CC1  0x10
#define NFC_CC2  0x6D
#define NFC_CC3  0x00

/* ---- API ---- 0 = OK, non-zero = fault (bus/NACK), same convention as twi.h ---- */

/* presence: read block 0, byte0 reads back 04h (UID0 = NXP). 1 if seen, else 0. */
uint8_t nfc_present(void);

/* read/write one 16-byte block. dst/src point at NFC_BLOCK_SZ bytes.
 * nfc_write_block enforces the >=4 ms post-write EEPROM settle internally. */
uint8_t nfc_read_block(uint8_t blk, uint8_t *dst16);
uint8_t nfc_write_block(uint8_t blk, const uint8_t *src16);

/* session-register access via the sec 9.8 register op (MEMA = 0xFE).
 * write: only the bits set in `mask` are changed to the matching bits of `val`. */
uint8_t nfc_read_reg(uint8_t reg, uint8_t *val);
uint8_t nfc_write_reg(uint8_t reg, uint8_t mask, uint8_t val);

/* power-gate control (NFC_EN = PA7, active-HIGH; see board.h).
 * nfc_power_on(): drive NFC_EN HIGH, then wait for the tag to answer its I2C
 *   address (bounded ACK-poll after a short load-switch soft-start). Returns 0
 *   when the tag is up and reachable, non-zero on timeout (absent / EN not wired).
 * nfc_power_off(): drive NFC_EN LOW (VCC off). Call immediately after any I2C
 *   access; it MUST be low before sleep. */
uint8_t nfc_power_on(void);
void    nfc_power_off(void);

/* read-only CC check: 1 if block-0 bytes 12..15 == E1 10 6D 00 (NDEF-capable). */
uint8_t nfc_check_cc(void);

/* write a pre-built, TLV-wrapped NDEF (03h,len,..,FEh) into user memory starting
 * at block 1. `len` need not be a block multiple; the last block is 00h-padded.
 * Whole 16-byte blocks are written (the tag has no partial-block write). */
uint8_t nfc_write_ndef(const uint8_t *buf, uint16_t len);

/* write the built-in default NDEF (see nfc.c). One-shot provisioning helper. */
uint8_t nfc_provision_default(void);

#endif /* NFC_H */
