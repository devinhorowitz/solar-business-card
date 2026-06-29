/*
 * nfc.c  --  NT3H2211 bring-up: presence, FD field-wake config, NDEF write.
 *
 * All transactions are the datasheet ones (sec 9.7 block READ/WRITE, sec 9.8
 * register READ/WRITE), built on the twi.h primitives. The reads follow Figures
 * 18/19 exactly: an address phase (SA+W, MEMA[, REGA]) terminated by a STOP, then
 * a fresh START with SA+R for the data phase -- the standard "set the address
 * pointer, then read" idiom the figures draw. The read (START..NACK..STOP) is run
 * to completion every time; the datasheet warns a partial read leaves the tag
 * stretching the clock forever.
 *
 * EEPROM timing (sec 9.7 WARNING): after a block-write STOP, ANY command sent
 * within ~4 ms can terminate and corrupt the in-flight write. So we fix-delay
 * past it rather than polling NS_REG.EEPROM_WR_BUSY (the poll would BE that
 * corrupting early command). Provisioning is one-shot, so a busy delay is fine.
 */
#include "board.h"          /* NT3H_ADDR, F_CPU (needed by util/delay.h) */
#include "nfc.h"
#include "twi.h"
#include <util/delay.h>

#define NFC_EEPROM_WR_MS   6   /* >= ~4 ms datasheet program time, with margin */

/* ---- block READ: START, AA, MEMA, STOP, START, AB, D0..D15(NACK last), STOP ---- */
uint8_t nfc_read_block(uint8_t blk, uint8_t *dst16)
{
    if (twi_start(NT3H_ADDR, 0)) { twi_stop(); return 1; }   /* SA + write   */
    if (twi_write(blk))          { twi_stop(); return 1; }   /* MEMA         */
    twi_stop();                                              /* end addr phase (Fig 18) */
    if (twi_start(NT3H_ADDR, 1)) { twi_stop(); return 1; }   /* START + read */
    for (uint8_t i = 0; i < NFC_BLOCK_SZ; i++)
        if (twi_read((uint8_t)(i < (NFC_BLOCK_SZ - 1)), &dst16[i]))  /* ACK all but last */
            return 1;                                                /* last NACKs + STOPs */
    return 0;
}

/* ---- block WRITE: START, AA, MEMA, D0..D15, STOP, then >=4 ms settle ---- */
uint8_t nfc_write_block(uint8_t blk, const uint8_t *src16)
{
    if (twi_start(NT3H_ADDR, 0)) { twi_stop(); return 1; }   /* SA + write */
    if (twi_write(blk))          { twi_stop(); return 1; }   /* MEMA       */
    for (uint8_t i = 0; i < NFC_BLOCK_SZ; i++)
        if (twi_write(src16[i]))  { twi_stop(); return 1; }
    twi_stop();
    _delay_ms(NFC_EEPROM_WR_MS);   /* sec 9.7: stay off the bus until the write completes */
    return 0;
}

/* ---- sec 9.8 register READ: START, AA, FEh, REGA, STOP, START, AB, DAT(NACK), STOP ---- */
uint8_t nfc_read_reg(uint8_t reg, uint8_t *val)
{
    if (twi_start(NT3H_ADDR, 0))      { twi_stop(); return 1; }
    if (twi_write(NFC_BLK_SESSION))   { twi_stop(); return 1; }   /* MEMA = FEh */
    if (twi_write(reg))               { twi_stop(); return 1; }   /* REGA       */
    twi_stop();                                                   /* end addr phase (Fig 19) */
    if (twi_start(NT3H_ADDR, 1))      { twi_stop(); return 1; }   /* START + read */
    return twi_read(0, val);                                      /* NACK + STOP */
}

/* ---- sec 9.8 register WRITE (mask): START, AA, FEh, REGA, MASK, DAT, STOP ---- */
uint8_t nfc_write_reg(uint8_t reg, uint8_t mask, uint8_t val)
{
    if (twi_start(NT3H_ADDR, 0))    { twi_stop(); return 1; }
    if (twi_write(NFC_BLK_SESSION)) { twi_stop(); return 1; }   /* MEMA = FEh */
    if (twi_write(reg))             { twi_stop(); return 1; }   /* REGA       */
    if (twi_write(mask))            { twi_stop(); return 1; }   /* MASK: 1=modify */
    if (twi_write(val))             { twi_stop(); return 1; }   /* REGDAT     */
    twi_stop();
    return 0;
}

uint8_t nfc_present(void)
{
    uint8_t b0[NFC_BLOCK_SZ];
    if (nfc_read_block(0x00, b0)) return 0;
    return (b0[0] == 0x04) ? 1u : 0u;   /* byte0 of block0 reads back UID0 = 04h (NXP) */
}

uint8_t nfc_check_cc(void)
{
    uint8_t b0[NFC_BLOCK_SZ];
    if (nfc_read_block(0x00, b0)) return 0;
    return (b0[12] == NFC_CC0 && b0[13] == NFC_CC1 &&
            b0[14] == NFC_CC2 && b0[15] == NFC_CC3) ? 1u : 0u;
}

uint8_t nfc_set_fd_field_mode(void)
{
    /* clear FD_OFF[5:4] and FD_ON[3:2] to 00b -> FD low on field present,
     * released on field absent. Other NC_REG bits left untouched by the mask. */
    return nfc_write_reg(NFC_REG_NC, NFC_NC_FD_msk, NFC_NC_FD_FIELD);
}

uint8_t nfc_write_ndef(const uint8_t *buf, uint16_t len)
{
    uint16_t off = 0;
    uint8_t  blk = NFC_BLK_USER0;
    uint8_t  rc  = 0;

    while (off < len) {
        uint8_t chunk[NFC_BLOCK_SZ];
        if (blk > NFC_BLK_EEPROM_TOP) return 1;   /* NDEF overruns sector-0 EEPROM */
        for (uint8_t i = 0; i < NFC_BLOCK_SZ; i++) {
            uint16_t p = off + i;
            chunk[i] = (p < len) ? buf[p] : 0x00; /* 00h-pad the last partial block */
        }
        rc |= nfc_write_block(blk, chunk);
        off += NFC_BLOCK_SZ;
        blk++;
    }
    return rc ? 1u : 0u;
}

/* -----------------------------------------------------------------------------
 * Built-in default NDEF (one-shot provisioning via nfc_provision_default()).
 *
 * Devin R. Horowitz business-card vCard 3.0, wrapped as an NFC-Forum Type-2 TLV.
 * A phone tap offers "Add to Contacts" with name / title / org / mobile / both
 * emails / website pre-filled. Bytes are machine-generated, not hand-edited;
 * regenerate (do not patch in place) if any field changes.
 *
 * vCard (CRLF line ends; commas in ORG escaped \, per RFC 2426):
 *   BEGIN:VCARD / VERSION:3.0
 *   N:Horowitz;Devin;R.;;     FN:Devin R. Horowitz
 *   ORG:Quintairos\, Prieto\, Wood\, & Boyer\, P.A.     TITLE:Partner
 *   TEL;TYPE=CELL:+14042138076
 *   EMAIL;TYPE=WORK:devin.horowitz@qpwblaw.com
 *   EMAIL;TYPE=HOME:devin@horowitz.law
 *   URL:https://horowitz.law / END:VCARD
 *
 * Framing: TLV 03 FF 01 28 (NDEF message, 296 B) | record C2 0A 00 00 01 18
 * ("text/vcard" MIME, non-short, 280 B payload) | ... | FE terminator. 304 B
 * padded = 19 blocks, written to blocks 0x01..0x13 (sector-0 holds to 0x37 -> fits).
 * --------------------------------------------------------------------------- */
static const uint8_t ndef_default[] = {
    0x03, 0xFF, 0x01, 0x28, 0xC2, 0x0A, 0x00, 0x00,
    0x01, 0x18, 0x74, 0x65, 0x78, 0x74, 0x2F, 0x76,
    0x63, 0x61, 0x72, 0x64, 0x42, 0x45, 0x47, 0x49,
    0x4E, 0x3A, 0x56, 0x43, 0x41, 0x52, 0x44, 0x0D,
    0x0A, 0x56, 0x45, 0x52, 0x53, 0x49, 0x4F, 0x4E,
    0x3A, 0x33, 0x2E, 0x30, 0x0D, 0x0A, 0x4E, 0x3A,
    0x48, 0x6F, 0x72, 0x6F, 0x77, 0x69, 0x74, 0x7A,
    0x3B, 0x44, 0x65, 0x76, 0x69, 0x6E, 0x3B, 0x52,
    0x2E, 0x3B, 0x3B, 0x0D, 0x0A, 0x46, 0x4E, 0x3A,
    0x44, 0x65, 0x76, 0x69, 0x6E, 0x20, 0x52, 0x2E,
    0x20, 0x48, 0x6F, 0x72, 0x6F, 0x77, 0x69, 0x74,
    0x7A, 0x0D, 0x0A, 0x4F, 0x52, 0x47, 0x3A, 0x51,
    0x75, 0x69, 0x6E, 0x74, 0x61, 0x69, 0x72, 0x6F,
    0x73, 0x5C, 0x2C, 0x20, 0x50, 0x72, 0x69, 0x65,
    0x74, 0x6F, 0x5C, 0x2C, 0x20, 0x57, 0x6F, 0x6F,
    0x64, 0x5C, 0x2C, 0x20, 0x26, 0x20, 0x42, 0x6F,
    0x79, 0x65, 0x72, 0x5C, 0x2C, 0x20, 0x50, 0x2E,
    0x41, 0x2E, 0x0D, 0x0A, 0x54, 0x49, 0x54, 0x4C,
    0x45, 0x3A, 0x50, 0x61, 0x72, 0x74, 0x6E, 0x65,
    0x72, 0x0D, 0x0A, 0x54, 0x45, 0x4C, 0x3B, 0x54,
    0x59, 0x50, 0x45, 0x3D, 0x43, 0x45, 0x4C, 0x4C,
    0x3A, 0x2B, 0x31, 0x34, 0x30, 0x34, 0x32, 0x31,
    0x33, 0x38, 0x30, 0x37, 0x36, 0x0D, 0x0A, 0x45,
    0x4D, 0x41, 0x49, 0x4C, 0x3B, 0x54, 0x59, 0x50,
    0x45, 0x3D, 0x57, 0x4F, 0x52, 0x4B, 0x3A, 0x64,
    0x65, 0x76, 0x69, 0x6E, 0x2E, 0x68, 0x6F, 0x72,
    0x6F, 0x77, 0x69, 0x74, 0x7A, 0x40, 0x71, 0x70,
    0x77, 0x62, 0x6C, 0x61, 0x77, 0x2E, 0x63, 0x6F,
    0x6D, 0x0D, 0x0A, 0x45, 0x4D, 0x41, 0x49, 0x4C,
    0x3B, 0x54, 0x59, 0x50, 0x45, 0x3D, 0x48, 0x4F,
    0x4D, 0x45, 0x3A, 0x64, 0x65, 0x76, 0x69, 0x6E,
    0x40, 0x68, 0x6F, 0x72, 0x6F, 0x77, 0x69, 0x74,
    0x7A, 0x2E, 0x6C, 0x61, 0x77, 0x0D, 0x0A, 0x55,
    0x52, 0x4C, 0x3A, 0x68, 0x74, 0x74, 0x70, 0x73,
    0x3A, 0x2F, 0x2F, 0x68, 0x6F, 0x72, 0x6F, 0x77,
    0x69, 0x74, 0x7A, 0x2E, 0x6C, 0x61, 0x77, 0x0D,
    0x0A, 0x45, 0x4E, 0x44, 0x3A, 0x56, 0x43, 0x41,
    0x52, 0x44, 0x0D, 0x0A, 0xFE, 0x00, 0x00, 0x00
};

uint8_t nfc_provision_default(void)
{
    return nfc_write_ndef(ndef_default, (uint16_t)sizeof ndef_default);
}
