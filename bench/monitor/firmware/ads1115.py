# Minimal ADS1115 driver -- single-shot, single-ended, MicroPython.
# Only what the bench monitor needs: one conversion at a time on a chosen input,
# PGA fixed at the FSR the generated channel map declares (4.096 V).
import time

_REG_CONV = 0x00
_REG_CONF = 0x01
_PGA_4096 = 0b001


class ADS1115:
    def __init__(self, i2c, addr):
        self.i2c = i2c
        self.addr = addr

    def read_se(self, ch):
        """Single-ended conversion on AINch vs GND, volts. Blocks ~10 ms (128 SPS)."""
        cfg = (1 << 15                  # OS: start single conversion
               | (0b100 | ch) << 12    # MUX: AINch vs GND
               | _PGA_4096 << 9
               | 1 << 8                 # single-shot
               | 0b100 << 5             # 128 SPS
               | 0b11)                  # comparator off
        self.i2c.writeto_mem(self.addr, _REG_CONF, bytes([cfg >> 8, cfg & 0xFF]))
        for _ in range(20):
            time.sleep_ms(2)
            hi, lo = self.i2c.readfrom_mem(self.addr, _REG_CONF, 2)
            if hi & 0x80:               # OS=1: conversion done
                break
        hi, lo = self.i2c.readfrom_mem(self.addr, _REG_CONV, 2)
        raw = (hi << 8) | lo
        if raw & 0x8000:
            raw -= 0x10000
        return raw * 4.096 / 32768.0
