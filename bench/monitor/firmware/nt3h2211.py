# NT3H2211 (NTAG I2C plus 2k) -- bench-side access over the card's own I2C bus.
#
# Protocol facts, verified against the NXP datasheet (Rev 3.6):
#  - 7-bit slave address 0x55.
#  - Memory is block-addressed: MEMA selects a 16-byte block. Read = write MEMA,
#    repeated-start, read 16 bytes. User memory (NDEF) starts at block 0x01.
#  - Session registers live in block 0xFE and are reachable ONLY via the register
#    operation: write [0xFE, REGA] then STOP, then read one byte. The sequence must
#    be atomic -- interleave nothing, or the tag can clock-stretch forever.
#  - NS_REG is byte 6 of block 0xFE. Bit 0 = RF_FIELD_PRESENT (1: NFC field on the
#    antenna right now), bit 1 = EEPROM_WR_BUSY, bit 5 = RF_LOCKED,
#    bit 6 = I2C_LOCKED, bit 7 = NDEF_DATA_READ.

ADDR = 0x55
NS_REG = 0x06
REG_NAMES = ("NC_REG", "LAST_NDEF_BLOCK", "SRAM_MIRROR_BLOCK", "WDT_LS",
             "WDT_MS", "I2C_CLOCK_STR", "NS_REG", "RFU")


class NT3H2211:
    def __init__(self, i2c):
        self.i2c = i2c

    def session_reg(self, rega):
        self.i2c.writeto(ADDR, bytes([0xFE, rega]))          # STOP per datasheet
        return self.i2c.readfrom(ADDR, 1)[0]

    def ns_reg(self):
        return self.session_reg(NS_REG)

    def field_present(self):
        return bool(self.ns_reg() & 0x01)

    def all_session_regs(self):
        return {REG_NAMES[r]: self.session_reg(r) for r in range(7)}

    def read_block(self, block):
        self.i2c.writeto(ADDR, bytes([block]), False)        # repeated start
        return self.i2c.readfrom(ADDR, 16)

    def read_ndef(self, max_blocks=56):
        """Raw TLV area (block 1 up), stopping at the 0xFE terminator TLV.
        Returns (raw bytes, best-effort decoded text payloads)."""
        raw = b""
        for b in range(1, 1 + max_blocks):
            blk = self.read_block(b)
            raw += blk
            if 0xFE in blk:
                break
        texts = []
        i = 0
        while i < len(raw):
            t = raw[i]
            if t == 0x00:
                i += 1
                continue
            if t == 0xFE:
                break
            if i + 1 >= len(raw):
                break
            ln = raw[i + 1]
            i += 2
            if ln == 0xFF:                                   # 3-byte length form
                ln = (raw[i] << 8) | raw[i + 1]
                i += 2
            if t == 0x03:                                    # NDEF message TLV
                texts.append(raw[i:i + ln])
            i += ln
        return raw, texts
