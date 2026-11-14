#!/usr/bin/env python3
"""
fw_erratum_scan.py -- hold the AVR64EA Rev. B1 erratum 2.2.3 guard to the BINARY.

The erratum (DS80001048C, in datasheets/): an ST / STD / STS to any address >= 64
immediately followed by a write to SLPCTRL.CTRLA LOSES the SLPCTRL write. A dropped
sleep-mode select leaves the core in IDLE instead of Power-Down and quietly burns the
standby budget -- nothing crashes, nothing logs, the card just dies sooner.

firmware/board.h guards it in SOURCE: every SLPCTRL.CTRLA write goes through the
slp_* wrappers, which put a NOP in front. That is a rule about what people type. This
is the check on what the compiler emitted, which is the thing the silicon runs:

  * every direct store to SLPCTRL.CTRLA is found in the disassembly;
  * none may be immediately preceded by a store instruction;
  * there must BE some -- a scan that finds zero writes has stopped looking at the
    right address, and "0 violations" from it would be a quiet lie;
  * and no instruction may load that address into a pointer register, because an
    indirect store through X/Y/Z is a write this scan cannot attribute. avr-gcc does
    not emit one for a constant address at -Os; if a future toolchain does, this goes
    red and says so rather than passing blind.

The address is READ from the device header the firmware is built against, not typed
here. The scanner self-tests on every run against a synthetic violation, a synthetic
clean write and a synthetic indirect load; if it stops telling them apart it fails.

  python3 scripts/fw_erratum_scan.py --dfp /path/to/AVR-Ex_DFP firmware/solar-glow.elf
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

DEVICE = "avr64ea28"
STORES = ("st", "std", "sts")           # the erratum's own list
INSN = re.compile(r"^\s*([0-9a-f]+):\s+(?:[0-9a-f]{2} )+\s*([a-z]+)\s*(.*?)\s*(?:;.*)?$")
FUNC = re.compile(r"^[0-9a-f]+ <(.+)>:$")


def slpctrl_ctrla(dfp):
    """SLPCTRL.CTRLA's data address, from the pack's own device header."""
    hdr = Path(dfp) / "include" / "avr" / f"io{DEVICE}.h"
    if not hdr.is_file():
        sys.exit(f"fw_erratum_scan: no device header at {hdr} -- is --dfp the AVR-Ex pack?")
    text = hdr.read_text(errors="replace")
    m = re.search(r"#define\s+SLPCTRL\s+\(\*\(SLPCTRL_t\s*\*\)\s*(0x[0-9A-Fa-f]+)\)", text)
    if not m:
        sys.exit(f"fw_erratum_scan: SLPCTRL base not found in {hdr.name}")
    base = int(m.group(1), 16)
    # CTRLA must be the first member, or base != CTRLA and every address below is wrong.
    s = re.search(r"typedef struct SLPCTRL_struct\s*\{(.*?)\}\s*SLPCTRL_t;", text, re.S)
    if not s:
        sys.exit(f"fw_erratum_scan: SLPCTRL_struct not found in {hdr.name}")
    first = re.search(r"register8_t\s+(\w+)\s*;", s.group(1))
    if not first or first.group(1) != "CTRLA":
        sys.exit("fw_erratum_scan: CTRLA is not SLPCTRL's first register in this header; "
                 "the scan's address derivation no longer holds")
    return base


def parse(listing):
    """-> [(addr, mnemonic, operands, function)] in listing order."""
    out, fn = [], "?"
    for line in listing.splitlines():
        f = FUNC.match(line)
        if f:
            fn = f.group(1)
            continue
        m = INSN.match(line)
        if m:
            out.append((int(m.group(1), 16), m.group(2), m.group(3), fn))
    return out


def scan(insns, target):
    """-> (writes, violations, indirect). Each entry is (addr, function, detail)."""
    writes, bad, indirect = [], [], []
    lo, hi = target & 0xFF, target >> 8
    for i, (addr, mn, ops, fn) in enumerate(insns):
        if mn == "sts":
            dst = ops.split(",")[0].strip()
            if dst.startswith("0x") and int(dst, 16) == target:
                writes.append((addr, fn, ops))
                if i == 0:
                    bad.append((addr, fn, "first instruction in the listing"))
                else:
                    paddr, pmn, pops, _ = insns[i - 1]
                    if pmn in STORES:
                        bad.append((addr, fn, f"preceded by `{pmn} {pops}` at 0x{paddr:x}"))
        # a pointer register pair loaded with the target address: ldi rLo, lo ; ldi rHi, hi
        if mn == "ldi" and i + 1 < len(insns):
            n = insns[i + 1]
            a = re.match(r"r(26|28|30),\s*0x([0-9A-Fa-f]+)", ops)
            b = re.match(r"r(27|29|31),\s*0x([0-9A-Fa-f]+)", n[2]) if n[1] == "ldi" else None
            if a and b and int(b.group(1)) == int(a.group(1)) + 1 \
                    and int(a.group(2), 16) == lo and int(b.group(2), 16) == hi:
                indirect.append((addr, fn, f"`ldi {ops}` / `ldi {n[2]}`"))
    return writes, bad, indirect


def self_test():
    """The scanner must tell a violation, a clean write and an indirect load apart."""
    t = 0x50
    clean = """
00000100 <ok>:
     100:\t00 00       \tnop
     102:\t80 93 50 00 \tsts\t0x0050, r24\t; 0x800050 <x>
"""
    dirty = """
00000100 <bad>:
     100:\t80 93 10 68 \tsts\t0x6810, r24\t; 0x806810 <f>
     104:\t80 93 50 00 \tsts\t0x0050, r24\t; 0x800050 <x>
"""
    ptr = """
00000100 <ind>:
     100:\te0 e5       \tldi\tr30, 0x50\t; 80
     102:\tf0 e0       \tldi\tr31, 0x00\t; 0
     104:\t80 83       \tst\tZ, r24
"""
    w, b, i = scan(parse(clean), t)
    if not (len(w) == 1 and not b and not i):
        return "a clean guarded write was not read as clean"
    w, b, i = scan(parse(dirty), t)
    if not (len(w) == 1 and len(b) == 1):
        return "a store-then-SLPCTRL pair was NOT flagged"
    w, b, i = scan(parse(ptr), t)
    if not (not w and len(i) == 1):
        return "a pointer load of the SLPCTRL address was NOT flagged"
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("elf")
    ap.add_argument("--dfp", required=True, help="AVR-Ex device pack root (the Makefile's DFP)")
    ap.add_argument("--objdump", default="avr-objdump")
    a = ap.parse_args()

    err = self_test()
    if err:
        sys.exit(f"fw_erratum_scan: SELF-TEST FAILED -- {err}. The scanner is broken; "
                 "its verdict on the firmware means nothing.")

    target = slpctrl_ctrla(a.dfp)
    try:
        listing = subprocess.run([a.objdump, "-d", a.elf], check=True,
                                 capture_output=True, text=True).stdout
    except (OSError, subprocess.CalledProcessError) as e:
        sys.exit(f"fw_erratum_scan: could not disassemble {a.elf}: {e}")
    insns = parse(listing)
    if len(insns) < 100:
        sys.exit(f"fw_erratum_scan: only {len(insns)} instructions parsed from {a.elf} -- "
                 "the listing format has changed under the parser")

    writes, bad, indirect = scan(insns, target)
    print(f"erratum 2.2.3: SLPCTRL.CTRLA = 0x{target:04x} (from the {DEVICE} header); "
          f"{len(insns)} instructions scanned")
    by_fn = {}
    for _, fn, _ in writes:
        by_fn[fn] = by_fn.get(fn, 0) + 1
    print(f"  {len(writes)} direct write(s): " +
          ", ".join(f"{fn} x{n}" for fn, n in sorted(by_fn.items())))

    ok = True
    if not writes:
        print("  FAIL: no write to SLPCTRL.CTRLA found. This firmware sleeps, so a scan that "
              "finds none has lost the address, not proved the guard.")
        ok = False
    for addr, fn, why in bad:
        print(f"  FAIL: 0x{addr:x} in {fn}: {why} -- the erratum drops this write. "
              "Route it through board.h's slp_* wrappers.")
        ok = False
    for addr, fn, why in indirect:
        print(f"  FAIL: 0x{addr:x} in {fn}: {why} loads the SLPCTRL address into a pointer "
              "register. A store through it is a write this scan cannot check.")
        ok = False
    if ok:
        print("  OK: self-test passed; none is preceded by a store, none is indirect")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
