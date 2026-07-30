# MB85RC512TY FRAM -- bench-side reads of the card's 64 KB log memory.
#
# Board facts (from the committed .kicad_pcb): A0-A2 all grounded -> slave 0x50;
# WP is also grounded, so writes are electrically possible and it is POLICY that
# keeps the bench read-only -- there is deliberately no write method here. The
# card's log belongs to the card.
# Addressing: two address bytes, then sequential reads with auto-increment.

ADDR = 0x50
SIZE = 64 * 1024


class MB85RC512:
    def __init__(self, i2c):
        self.i2c = i2c

    def read(self, addr, n):
        if addr < 0 or addr + n > SIZE:
            raise ValueError("out of range")
        self.i2c.writeto(ADDR, bytes([addr >> 8, addr & 0xFF]), False)
        return self.i2c.readfrom(ADDR, n)

    def present(self):
        try:
            self.read(0, 1)
            return True
        except OSError:
            return False
