# ADXL367 -- bench-side READ-ONLY access. The accelerometer is the card's only
# actuator (tap-to-wake); the card firmware owns its configuration, so the bench
# never writes a register here. One caution carried up to the UI: reading STATUS
# (0x0B) can consume latched activity bits the card may be about to look at, so
# telemetry sticks to IDs / data / temp and STATUS is a deliberate command.
#
# Facts verified against the ADI datasheet: I2C address 0x1D on this board (ASEL
# grounded). DEVID_AD 0x00 = 0xAD, DEVID_MST 0x01 = 0x1D, PART_ID 0x02 = 0xF7.
# XDATA_H..ZDATA_L at 0x0E..0x13, TEMP at 0x14/0x15 -- all 14-bit left-justified.
# Scale 0.25 mg/LSB at +-2 g (0.5 at 4 g, 1.0 at 8 g; range = FILTER_CTL[7:6]).
# Temperature: 54 LSB/degC, bias 165 LSB at 25 degC.

ADDR = 0x1D
_SCALE_MG = (0.25, 0.5, 1.0, 1.0)


def _s14(hi, lo):
    v = ((hi << 8) | lo) >> 2
    return v - 0x4000 if v & 0x2000 else v


class ADXL367:
    def __init__(self, i2c):
        self.i2c = i2c

    def _read(self, reg, n=1):
        self.i2c.writeto(ADDR, bytes([reg]), False)
        return self.i2c.readfrom(ADDR, n)

    def ids(self):
        d = self._read(0x00, 3)
        return {"DEVID_AD": d[0], "DEVID_MST": d[1], "PART_ID": d[2],
                "ok": d[0] == 0xAD and d[1] == 0x1D and d[2] == 0xF7}

    def range_mg_per_lsb(self):
        return _SCALE_MG[(self._read(0x2C)[0] >> 6) & 0b11]

    def xyz_g(self):
        d = self._read(0x0E, 6)
        s = self.range_mg_per_lsb() / 1000.0
        return tuple(_s14(d[i], d[i + 1]) * s for i in (0, 2, 4))

    def temp_c(self):
        d = self._read(0x14, 2)
        return (_s14(d[0], d[1]) - 165) / 54.0 + 25.0

    def status(self):
        """Deliberate command only -- see module docstring. Bit 6 AWAKE."""
        s = self._read(0x0B)[0]
        return {"raw": s, "AWAKE": bool(s & 0x40), "ACT": bool(s & 0x10),
                "INACT": bool(s & 0x20), "DATA_READY": bool(s & 0x01)}
