#!/usr/bin/env python3
"""Gate firmware/README.md's measured size figures against the just-built ELF.

The README states the build's exact footprint ("N,NNN B flash, NN B RAM
(NNNN text + N data + NN bss, measured ...)"). Those numbers went quietly
stale once already -- the "~2.4 KB flash, 6 B RAM" that outlived the EA port
by weeks (CLAUDE.md carries the story) -- and a stated-but-ungated number is
exactly the drift class this repo automates away. So firmware.yml runs this
after every build: parse the README's claim, run avr-size on the ELF, fail
loudly on any mismatch. A size-changing firmware edit therefore lands with
its README figure update in the same commit, or not at all.

Usage: python3 scripts/check_fw_size.py [path/to/solar-glow.elf]
Requires avr-size on PATH (the same toolchain that built the ELF).
"""

import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
README = os.path.join(ROOT, "firmware", "README.md")

elf = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "firmware", "solar-glow.elf")
if not os.path.exists(elf):
    sys.exit(f"check_fw_size: {elf} not found -- build first (make -C firmware ...)")

out = subprocess.run(["avr-size", elf], capture_output=True, text=True, check=True)
text, data, bss = (int(v) for v in out.stdout.splitlines()[1].split()[:3])
flash, ram = text + data, data + bss

doc = open(README, encoding="utf-8").read()
m = re.search(
    r"([\d,]+)\s*B flash,\s*(\d+)\s*B RAM\s*\((\d+) text \+ (\d+) data \+\s*(\d+) bss",
    doc,
)
if not m:
    sys.exit("check_fw_size: firmware/README.md no longer carries the "
             "'N B flash, N B RAM (N text + N data + N bss' figure -- "
             "restore it (it is the gated single home for the build size)")

claim = {
    "flash": int(m.group(1).replace(",", "")),
    "ram": int(m.group(2)),
    "text": int(m.group(3)),
    "data": int(m.group(4)),
    "bss": int(m.group(5)),
}
actual = {"flash": flash, "ram": ram, "text": text, "data": data, "bss": bss}

drift = {k: (claim[k], actual[k]) for k in claim if claim[k] != actual[k]}
if drift:
    lines = ", ".join(f"{k}: README says {c}, build measures {a}" for k, (c, a) in drift.items())
    sys.exit(
        f"check_fw_size: README size figures are STALE -- {lines}.\n"
        f"Update firmware/README.md's figure to: {flash:,} B flash, {ram} B RAM "
        f"({text} text + {data} data + {bss} bss) and re-date the measurement."
    )
print(f"check_fw_size: README figures match the build "
      f"({text} text + {data} data + {bss} bss = {flash:,} B flash / {ram} B RAM)")
