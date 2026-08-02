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

/* ---- power-gate timing (high-side load switch on NFC_EN; see board.h) ---- */
#define NFC_SOFTSTART_US     200   /* switch turn-on + tag POR before the first ACK-poll */
#define NFC_BOOT_POLL_US     250   /* spacing between ACK-poll attempts                   */
#define NFC_BOOT_POLL_TRIES  20    /* ~5 ms total budget for the tag to answer its addr   */

/* ---- block READ: START, AA, MEMA, STOP, START, AB, D0..D15 (ACK all, incl. the
 * last, then STOP -- Figure 18 draws the host ACKing the FINAL byte too, and the
 * prose is explicit: "the bus master/host will acknowledge it and issue a Stop
 * condition". Until 2026-08-01 this NACKed the last byte -- the FRAM's convention,
 * not this tag's -- on exactly the sequence whose WARNING says it must be executed
 * completely or the tag "stretches the clock infinitely". Safe to ACK-then-STOP
 * because the read is fixed-length: the tag ends on its own 16-byte count.) ---- */
uint8_t nfc_read_block(uint8_t blk, uint8_t *dst16)
{
    if (twi_start(NT3H_ADDR, 0)) { twi_stop(); return 1; }   /* SA + write   */
    if (twi_write(blk))          { twi_stop(); return 1; }   /* MEMA         */
    twi_stop();                                              /* end addr phase (Fig 18) */
    if (twi_start(NT3H_ADDR, 1)) { twi_stop(); return 1; }   /* START + read */
    for (uint8_t i = 0; i < NFC_BLOCK_SZ; i++) {
        uint8_t rc = (i < NFC_BLOCK_SZ - 1) ? twi_read(1, &dst16[i])
                                            : twi_read_last_ack(&dst16[i]);
        if (rc) {
            twi_stop();       /* bus fault: STOP so the tag can't clock-stretch forever */
            return 1;
        }
    }
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

/* Session-register access (nfc_read_reg / nfc_write_reg) and the CC check
 * (nfc_check_cc) are provided API that the default one-shot provisioning does NOT
 * call -- FD-wake uses the tag's POR default, so no NC_REG write is needed (nfc.h).
 * Kept for config/diagnostic use; --gc-sections drops whatever stays uncalled.
 * Intentional, not dead code. */

/* ---- sec 9.8 register READ: START, AA, FEh, REGA, STOP, START, AB, DAT(ACK), STOP
 * (Figure 19's host ACKs the single data byte before the STOP, same as the block
 * read -- was NACK here until 2026-08-01, see nfc_read_block) ---- */
uint8_t nfc_read_reg(uint8_t reg, uint8_t *val)
{
    if (twi_start(NT3H_ADDR, 0))      { twi_stop(); return 1; }
    if (twi_write(NFC_BLK_SESSION))   { twi_stop(); return 1; }   /* MEMA = FEh */
    if (twi_write(reg))               { twi_stop(); return 1; }   /* REGA       */
    twi_stop();                                                   /* end addr phase (Fig 19) */
    if (twi_start(NT3H_ADDR, 1))      { twi_stop(); return 1; }   /* START + read */
    if (twi_read_last_ack(val))       { twi_stop(); return 1; }   /* fault mid-read: force the
                                                                   * STOP ourselves (success
                                                                   * already ACKed + STOPped) */
    return 0;
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

/* ---- power-gate (NFC_EN = PA7, active-HIGH high-side load switch) ---- */

void nfc_power_off(void)
{
    NFC_EN_PORT.OUTCLR = NFC_EN_PIN_bm;   /* EN low -> switch off -> tag VCC off (~0) */
}

uint8_t nfc_power_on(void)
{
    /* Raise EN, let the switch turn on and the tag run its POR, then ACK-poll the
     * tag's address until it answers (or give up). The tag has no published boot
     * time, so poll rather than guess a fixed delay; the bounded budget means an
     * absent tag or an unwired EN returns a fault instead of hanging. Each attempt
     * is an address-only ping (START, SA+W, [N]ACK, STOP) -- no data written. */
    NFC_EN_PORT.OUTSET = NFC_EN_PIN_bm;
    _delay_us(NFC_SOFTSTART_US);
    for (uint8_t t = 0; t < NFC_BOOT_POLL_TRIES; t++) {
        if (twi_start(NT3H_ADDR, 0) == 0) {   /* address ACKed -> tag is up */
            twi_stop();
            return 0;
        }
        twi_stop();                            /* release the bus after the NACK/fault */
        _delay_us(NFC_BOOT_POLL_US);
    }
    return 1;                                   /* timed out: absent or EN not wired */
}

uint8_t nfc_write_ndef(const uint8_t *buf, uint16_t len)
{
    uint16_t off = 0;
    uint8_t  blk = NFC_BLK_USER0;
    uint8_t  rc  = 0;

    while (off < len) {
        uint8_t chunk[NFC_BLOCK_SZ];
        if (blk > NFC_BLK_NDEF_TOP) return 1;     /* NDEF overruns sector-0 -> reject before the 0x3A config block */
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
 *
 * NO LOCK CONTROL TLV -- RESOLVED DELIBERATE, 2026-08-02 (audit (f)). The datasheet's
 * blanket line (8.3.7: the tag "needs a Lock Control TLV ... to ensure NFC Forum Type 2
 * Tag compliancy") reads as if one belongs in front of this message. NXP's own memory-
 * configuration app note says otherwise for exactly this layout: AN11786 Table 2 gives
 * CC E1 10 6D 00 + a bare NDEF TLV + FE -- no Lock Control TLV -- as the initialization
 * "recommended to be used on NTAG I2C plus 1k/2k unless there are special needs", and
 * lists the Lock Control TLV among the changes needed only "when NDEF messages need
 * more space" than that NTAG216-like T2T_Area. The CC this driver writes (nfc_write_cc)
 * IS that recommended 6Dh profile, and this 304 B message sits comfortably inside its
 * 872 B area, so the compliant-by-app-note configuration is the one WITHOUT the TLV --
 * adding one would deviate from NXP's recommended profile, with hand-derived granularity
 * bytes no validator has blessed. THE TRIGGER TO REVISIT: if the CC size byte is ever
 * raised past 6Dh to claim more of the 2k memory, the Lock Control TLV (and a Memory
 * Control TLV excluding the config/SRAM area) becomes REQUIRED per that same app note --
 * do not enlarge the CC without adding both. */
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

/* ---- Capability Container: REQUIRED, the tag does not ship with one ----
 *
 * Datasheet sec 8.3.10 ("Memory content at delivery") is explicit: "the CC in
 * page 03h is set to all 00h to keep the full flexibility. To allow NFC Forum
 * NDEF message reading and writing page 03h (CC) and the following data page
 * (NDEF TLV) ... need to be initialized by the user". A CC of 00 00 00 00 means
 * NO phone recognises the tag as NDEF-capable -- the vCard would be written,
 * intact, and simply never offered to anyone. (nfc.h previously asserted the CC
 * "ships = E1 10 6D 00"; that is Table 8's REQUIRED target value, not the
 * delivery state. nfc_check_cc() would have caught it -- it was never called.)
 *
 * The CC lives in NFC page 03h = I2C block 0 bytes 12..15, so this is a
 * read-modify-write of block 0 -- the one block the driver otherwise never
 * touches, because byte 0 is the I2C address:
 *
 *   "I2C slave address is stored in most significant 7 bits of byte 0 in block
 *    0. However, when reading block 0, NTAG I2C plus always returns 04h for
 *    byte 0. WARNING: When configuring Static lock bytes and Capability
 *    container, Address byte gets updated, too." (sec 8.3.2)
 *
 * Section 9.6 ("Addressing") resolves this AUTHORITATIVELY in favour of what we
 * write (comment corrected 2026-08-01 -- the old text here treated it as an
 * unresolved datasheet self-contradiction needing a bench ruling; it is not):
 * "Byte 0 of block 0 is used to configure the device address. The 7-bit device
 * address needs to be programmed in the 7 most significant bits ... E.g. to keep
 * default device address of 55h, byte 0 of block 0 needs to be set to AAh." And
 * 9.6 decodes the 04h recommendation as a deliberate ADDRESS CHANGE, not a no-op:
 * "it is recommended to use 04h as I2C write address (02h device address)" --
 * i.e. NXP's suggestion is to accept relocating to 0x02 so that read-back-and-
 * rewrite (which reads 04h) is idempotent. We keep 0x55 instead, by the book:
 * (NT3H_ADDR << 1) = 0xAA. Bytes 1..11 (UID, internal, lock bytes) are written
 * back exactly as read.
 *
 * BENCH (demoted to a routine post-write check, not a semantics question): after
 * this write the tag must still ACK at 0x55 (nfc_present()); a NACK would mean a
 * garbled write, not an ambiguity -- re-read block 0 and re-provision. RF/vCard
 * is unaffected either way; the RF side never uses the I2C address. */
static uint8_t nfc_write_cc(void)
{
    uint8_t b0[NFC_BLOCK_SZ];

    if (nfc_read_block(0x00, b0)) return 1;
    if (b0[12] == NFC_CC0 && b0[13] == NFC_CC1 &&
        b0[14] == NFC_CC2 && b0[15] == NFC_CC3)
        return 0;                      /* already provisioned -- no EEPROM wear */

    b0[0]  = (uint8_t)(NT3H_ADDR << 1); /* keep the tag at its current address */
    b0[12] = NFC_CC0; b0[13] = NFC_CC1; /* E1 10 6D 00: NDEF-capable, 872 B in */
    b0[14] = NFC_CC2; b0[15] = NFC_CC3; /* sector 0 (Table 8)                  */
    return nfc_write_block(0x00, b0);
}

uint8_t nfc_provision_default(void)
{
    uint8_t rc;

    /* power the tag on for the write and drop it back off on EVERY path. */
    if (nfc_power_on()) { nfc_power_off(); return 1; }   /* tag never came up  */
    if (!nfc_present()) { nfc_power_off(); return 1; }   /* up, but wrong part */
    /* NDEF FIRST, CC LAST. The CC is what makes a phone parse the user pages at
     * all, so publishing it before the payload is written is publishing a promise
     * we have not kept: if the NDEF write then faults partway (a bus glitch, or --
     * per nfc_write_cc's own documented risk -- the tag having moved to another I2C
     * address so every following block NACKs), the tag advertises itself as
     * NDEF-capable over pages whose content the datasheet says is undefined at
     * delivery, and a phone shows the user garbage. Ordered this way the failure
     * mode is a tag that readers simply ignore, which is recoverable by re-running
     * provisioning. Costs nothing: the NDEF is invisible until the CC lands either
     * way. Bail before the CC if the payload did not land. */
    rc = nfc_write_ndef(ndef_default, (uint16_t)sizeof ndef_default);
    if (rc == 0)
        rc = nfc_write_cc();      /* publish only once the payload behind it is good */
    nfc_power_off();
    return rc ? 1u : 0u;
}
