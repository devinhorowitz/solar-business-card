#!/usr/bin/env python3
"""Live bench dashboard for the SOLAR-GLOW DRH pogo plate monitor.

    python3 dashboard.py [SERIAL_PORT] [--raw]

Reads the Pico's JSON telemetry and renders rails / NFC / accel / events live.
Keys while running:
    n  read the NDEF area (the vCard) and save it
    f  dump the first 4 KB of FRAM to a timestamped .bin
    g  show all NFC session registers
    s  accel STATUS (deliberate -- may consume latched bits the card wants)
    r  reset min/max
    q  quit
Requires: pip install pyserial rich
"""
import glob
import json
import sys
import threading
import time
from collections import deque
from datetime import datetime

import serial
from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

RAIL_MAX = {"SRC": 5.0, "VS": 3.6, "STO": 5.0, "STO_LDO": 5.0, "VINT": 4.0,
            "BUFSRC": 5.0, "MID": 3.0, "LX_LOUT": 5.0}


def find_port():
    for pat in ("/dev/ttyACM*", "/dev/tty.usbmodem*", "COM*"):
        hits = sorted(glob.glob(pat))
        if hits:
            return hits[0]
    sys.exit("no serial port found -- pass it explicitly")


class State:
    def __init__(self):
        self.rails = {}
        self.minmax = {}
        self.nfc = None
        self.accel = None
        self.err = 0
        self.events = deque(maxlen=14)
        self.last_field = None
        self.samples = 0
        self.boot = None

    def event(self, msg):
        self.events.append(f"{datetime.now().strftime('%H:%M:%S')}  {msg}")

    def ingest(self, d):
        if d.get("event") == "boot":
            self.boot = d
            self.event(f"monitor boot: card bus {d.get('card_bus')} "
                       f"accel_ok={((d.get('accel') or {}).get('ok'))} fram={d.get('fram')}")
            return
        if "rails" in d:
            self.samples += 1
            self.rails = d["rails"] or {}
            for k, v in self.rails.items():
                if v is None:
                    continue
                lo, hi = self.minmax.get(k, (v, v))
                self.minmax[k] = (min(lo, v), max(hi, v))
            self.nfc = d.get("nfc")
            self.accel = d.get("accel")
            self.err = d.get("err", 0)
            f = (self.nfc or {}).get("field")
            if f is not None and f != self.last_field:
                if self.last_field is not None:
                    self.event("NFC FIELD " + ("PRESENT -- phone on the card" if f else "gone"))
                self.last_field = f


def bar(v, vmax, width=22):
    if v is None:
        return Text("----", style="dim")
    n = max(0, min(width, int(v / vmax * width)))
    return Text("█" * n + "░" * (width - n))


def render(st):
    t = Table(title="rails", expand=True)
    for c in ("net", "volts", "", "min", "max"):
        t.add_column(c, justify="left")
    for net, vmax in RAIL_MAX.items():
        v = st.rails.get(net)
        lo, hi = st.minmax.get(net, (None, None))
        label = f"{net} (duty avg)" if net == "LX_LOUT" else net
        t.add_row(label, "--" if v is None else f"{v:.3f}", bar(v, vmax),
                  "--" if lo is None else f"{lo:.3f}",
                  "--" if hi is None else f"{hi:.3f}")

    nfc = st.nfc or {}
    field = nfc.get("field")
    nfc_txt = Text()
    nfc_txt.append(" NFC FIELD ", style="bold white on green" if field else "bold white on grey37")
    nfc_txt.append("  wr_busy " + ("Y" if nfc.get("wr_busy") else "n"))
    nfc_txt.append("  rf_lock " + ("Y" if nfc.get("rf_locked") else "n"))
    nfc_txt.append("  i2c_lock " + ("Y" if nfc.get("i2c_locked") else "n"))
    if not nfc:
        nfc_txt = Text("card bus unreachable", style="red")

    acc = st.accel or {}
    xyz = acc.get("xyz_g")
    if xyz:
        mag = (xyz[0] ** 2 + xyz[1] ** 2 + xyz[2] ** 2) ** 0.5
        acc_txt = (f"x {xyz[0]:+.3f}  y {xyz[1]:+.3f}  z {xyz[2]:+.3f} g   "
                   f"|g| {mag:.3f}   temp {acc.get('temp_c'):.1f} C"
                   if acc.get("temp_c") is not None else f"|g| {mag:.3f}")
    else:
        acc_txt = "accel unreachable"

    ev = Text("\n".join(st.events) or "--", no_wrap=False)
    foot = (f"samples {st.samples}   card-bus errors {st.err}   "
            "[n]def [f]ram [g]=nfc regs [s]tatus [r]eset [q]uit")
    return Group(t, Panel(nfc_txt, title="NFC (NS_REG live)"),
                 Panel(acc_txt, title="ADXL367"),
                 Panel(ev, title="events"), Text(foot, style="dim"))


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    port = args[0] if args else find_port()
    ser = serial.Serial(port, 115200, timeout=0.2)
    st = State()
    raw = "--raw" in sys.argv

    def send(obj):
        ser.write((json.dumps(obj) + "\n").encode())

    def keys():
        while True:
            k = sys.stdin.read(1)
            if k == "q":
                ser.close()
                sys.exit(0)
            elif k == "n":
                send({"cmd": "ndef_read"})
            elif k == "f":
                send({"cmd": "fram_read", "addr": 0, "len": 4096})
            elif k == "g":
                send({"cmd": "nfc_regs"})
            elif k == "s":
                send({"cmd": "accel_status"})
            elif k == "r":
                st.minmax.clear()

    if not raw:
        import termios
        import tty
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        tty.setcbreak(fd)
        threading.Thread(target=keys, daemon=True).start()

    console = Console()
    try:
        with Live(render(st), console=console, refresh_per_second=4) as live:
            while True:
                line = ser.readline().decode(errors="replace").strip()
                if not line:
                    live.update(render(st))
                    continue
                try:
                    d = json.loads(line)
                except ValueError:
                    continue
                evt = d.get("event")
                if evt == "fram":
                    fn = datetime.now().strftime("fram-%Y%m%d-%H%M%S.bin")
                    open(fn, "wb").write(bytes.fromhex(d["hex"]))
                    st.event(f"FRAM {len(d['hex']) // 2} B @ {d['addr']} -> {fn}")
                elif evt == "ndef":
                    fn = datetime.now().strftime("ndef-%Y%m%d-%H%M%S.bin")
                    open(fn, "wb").write(bytes.fromhex(d["raw_hex"]))
                    st.event(f"NDEF {len(d['raw_hex']) // 2} B -> {fn} "
                             f"({len(d.get('messages_hex', []))} message TLV)")
                elif evt == "nfc_regs":
                    st.event(f"NS regs: {d.get('regs')}")
                elif evt == "accel_status":
                    st.event(f"accel STATUS: {d.get('status')}")
                elif evt == "error":
                    st.event(f"ERROR {d}")
                else:
                    st.ingest(d)
                if raw:
                    print(line)
                else:
                    live.update(render(st))
    finally:
        if not raw:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)


if __name__ == "__main__":
    main()
