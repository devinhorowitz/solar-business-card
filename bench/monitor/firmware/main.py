# SOLAR-GLOW DRH bench monitor -- MicroPython on a Raspberry Pi Pico (W optional).
#
# Streams one JSON telemetry line per sample over USB serial and answers JSON
# commands on stdin. The channel map is NOT written here: deploy copies the
# CI-generated enclosure/solar-glow-drh-pogo-testplate-channels.json to the Pico
# as channels.json, so the plate, the wiring and this firmware can never disagree.
#
# Two I2C buses, deliberately separate:
#   I2C0 GP4/GP5  the two ADS1115s (0x48/0x49)      -- rails, always available
#   I2C1 GP2/GP3  the CARD's bus via the JP1 tails  -- NFC / accel / FRAM
# A wedged card bus therefore never blinds the voltage telemetry.
#
# BUS POLITENESS -- the card's AVR is the bus's real master and this monitor is a
# guest. It spends almost all its life asleep, so collisions are rare, but every
# card-bus access here goes through _guard(): OSError (NACK, arbitration loss,
# clock stretch timeout) is caught, counted, and retried a moment later rather
# than raised. Deep reads (FRAM dump, NDEF) are commands, not telemetry, so the
# human decides when a long bus occupation is safe (card asleep / before flash).
import json
import select
import sys
import time

from machine import I2C, Pin

from ads1115 import ADS1115
from adxl367 import ADXL367
from mb85rc import MB85RC512
from nt3h2211 import NT3H2211

CHAN = json.load(open("channels.json"))
PERIOD_MS = 500

i2c_adc = I2C(0, sda=Pin(4), scl=Pin(5), freq=400_000)
i2c_card = I2C(1, sda=Pin(2), scl=Pin(3), freq=100_000)

ads = {a: ADS1115(i2c_adc, int(a, 16)) for a in ("0x48", "0x49")}
nfc = NT3H2211(i2c_card)
acc = ADXL367(i2c_card)
fram = MB85RC512(i2c_card)

stats = {"card_bus_errors": 0, "samples": 0}


def _guard(fn, *a, default=None, tries=3):
    for k in range(tries):
        try:
            return fn(*a)
        except OSError:
            stats["card_bus_errors"] += 1
            time.sleep_ms(3 + 7 * k)
    return default


def emit(obj):
    print(json.dumps(obj))


def boot_report():
    devs = _guard(i2c_card.scan, default=[])
    rep = {"event": "boot", "card_bus": [hex(d) for d in devs],
           "accel": _guard(acc.ids), "fram": _guard(fram.present),
           "channels": len(CHAN["adc"]["rows"])}
    emit(rep)


def sample():
    rails = {}
    for r in CHAN["adc"]["rows"]:
        try:
            v = ads[r["ads"]].read_se(r["ch"]) * r["scale"]
            rails[r["net"]] = round(v, 4)
        except OSError:
            rails[r["net"]] = None
    ns = _guard(nfc.ns_reg)
    out = {"t": time.ticks_ms(), "rails": rails,
           "nfc": None if ns is None else {
               "field": bool(ns & 0x01), "wr_busy": bool(ns & 0x02),
               "rf_locked": bool(ns & 0x20), "i2c_locked": bool(ns & 0x40),
               "ns_reg": ns},
           "accel": {"xyz_g": _guard(acc.xyz_g), "temp_c": _guard(acc.temp_c)},
           "err": stats["card_bus_errors"]}
    stats["samples"] += 1
    emit(out)


def handle(cmd):
    c = cmd.get("cmd")
    if c == "fram_read":
        addr, n = int(cmd.get("addr", 0)), min(int(cmd.get("len", 256)), 4096)
        out = b""
        for off in range(0, n, 32):
            chunk = _guard(fram.read, addr + off, min(32, n - off))
            if chunk is None:
                emit({"event": "error", "cmd": c, "at": addr + off})
                return
            out += chunk
        emit({"event": "fram", "addr": addr, "hex": out.hex()})
    elif c == "ndef_read":
        got = _guard(nfc.read_ndef)
        if got is None:
            emit({"event": "error", "cmd": c})
        else:
            raw, msgs = got
            emit({"event": "ndef", "raw_hex": raw.hex(),
                  "messages_hex": [m.hex() for m in msgs]})
    elif c == "nfc_regs":
        emit({"event": "nfc_regs", "regs": _guard(nfc.all_session_regs)})
    elif c == "accel_status":
        emit({"event": "accel_status", "status": _guard(acc.status),
              "warning": "STATUS read may consume latched bits the card wants"})
    elif c == "ping":
        emit({"event": "pong", "stats": stats})
    else:
        emit({"event": "error", "msg": "unknown cmd", "cmd": c})


boot_report()
poller = select.poll()
poller.register(sys.stdin, select.POLLIN)
buf = ""
last = 0
while True:
    if time.ticks_diff(time.ticks_ms(), last) >= PERIOD_MS:
        last = time.ticks_ms()
        sample()
    for _ in poller.ipoll(20):
        ch = sys.stdin.read(1)
        if ch in ("\n", "\r"):
            if buf.strip():
                try:
                    handle(json.loads(buf))
                except ValueError:
                    emit({"event": "error", "msg": "bad json"})
            buf = ""
        else:
            buf += ch
