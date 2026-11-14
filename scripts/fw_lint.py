#!/usr/bin/env python3
"""
fw_lint.py -- cppcheck over the firmware, as a gate that knows whether it is looking.

The compiler's own warnings are already a gate (-Wall -Wextra -Wundef, WERROR=1 in CI).
cppcheck reads the same source a different way -- value-flow across calls, array bounds,
uninitialised reads, portability traps -- and it is told what the target is: the AVR8
data model (16-bit int) and the real device header out of the pack the firmware is built
against, so `RTC.PITCTRLA` is a register it knows and not an identifier it guesses at.

What GATES: cppcheck's error, warning, performance and portability findings.
What does not: its `style` tier. On this tree that tier is two findings and both are
false: avr-libc declares uint32_t as `unsigned int __attribute__((__mode__(__SI__)))`,
cppcheck reads past the attribute and sees a 16-bit type, and so calls the two overrun
checks in fram.c -- `(uint32_t)addr + len > FRAM_SIZE` -- "always false against 65536".
They are 32-bit compares (a _Static_assert build under avr-gcc confirms the width). A
gate that is red on arrival for a reason nobody can fix is a gate people learn to skip,
so that tier is left out rather than suppressed line by line.

A linter passes when it finds nothing, and it also finds nothing when it has stopped
reading the code -- a header path that no longer resolves leaves every register an
unknown and the analysis quietly shallow. So each run plants two CANARIES and requires
both to be caught with the very flags the firmware gets:
  1. an out-of-bounds write -- cppcheck is running and its exit code is honoured;
  2. an out-of-bounds write that EXISTS ONLY IF the device header resolved -- the bound
     is a register bit mask out of the pack.

  python3 scripts/fw_lint.py --dfp /path/to/AVR-Ex_DFP [--cc avr-gcc] main.c led.c ...
"""
import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

DEVICE = "avr64ea28"
GATING = "warning,performance,portability"        # errors are always on

CANARY_PLAIN = """\
static unsigned char buf[4];
void canary(void) { buf[4] = 1; }
"""
# RTC_PI_bm is 0x01 in the device header. If <avr/io.h> does not resolve to it, the array
# has no known size and there is nothing for cppcheck to flag -- which is the point.
CANARY_HEADER = """\
#include <avr/io.h>
static unsigned char buf[RTC_PI_bm];
void canary(void) { buf[RTC_PI_bm] = 1; }
"""


def toolchain_include(cc):
    """avr-libc's include directory, from the compiler that will build the firmware."""
    exe = shutil.which(cc)
    if not exe:
        sys.exit(f"fw_lint: `{cc}` not on PATH -- the linter reads avr-libc's headers "
                 "from beside the compiler")
    inc = Path(exe).resolve().parent.parent / "avr" / "include"
    if not (inc / "avr" / "io.h").is_file():
        # distro layout (apt's gcc-avr / avr-libc)
        alt = Path("/usr/lib/avr/include")
        if (alt / "avr" / "io.h").is_file():
            return alt
        sys.exit(f"fw_lint: no avr/io.h under {inc} (or {alt})")
    return inc


def device_defines(dfp):
    """The -D flags avr-gcc itself passes for this device, read out of the pack's spec file.

    Not typed here, and that is not fussiness: avr-libc's <avr/io.h> picks the device
    header through __AVR_DEV_LIB_NAME__, a COMPUTED include. The obvious
    -D__AVR_AVR64EA28__ alone selects nothing -- io.h falls through, every register is an
    unknown identifier, and cppcheck reports a clean tree it has not really read. The
    first cut of this gate did exactly that (2026-11-14), and it was the header canary
    below that said so, on its first run."""
    spec = Path(dfp) / "gcc" / "dev" / DEVICE / "device-specs" / f"specs-{DEVICE}"
    if not spec.is_file():
        sys.exit(f"fw_lint: no spec file at {spec} -- is --dfp the AVR-Ex pack?")
    m = re.search(r"^\*cpp:\s*\n(.*)$", spec.read_text(), re.M)
    defs = re.findall(r"-D\S+", m.group(1)) if m else []
    if not any(d.startswith("-D__AVR_DEV_LIB_NAME__=") for d in defs):
        sys.exit(f"fw_lint: {spec.name} has no -D__AVR_DEV_LIB_NAME__ in its *cpp line; "
                 "the device header cannot be selected")
    return defs


def cppcheck(exe, files, defs, dfp_inc, tc_inc, cwd):
    cmd = [exe, "--std=c11", "--platform=avr8",
           f"--enable={GATING}", "--error-exitcode=1", "--inline-suppr", "-q",
           *defs, "-DF_CPU=1000000UL",
           "-I", str(dfp_inc), "-I", str(tc_inc),
           # findings INSIDE vendor headers are not ours to fix
           f"--suppress=*:{dfp_inc}/*", f"--suppress=*:{tc_inc}/*",
           "--suppress=missingIncludeSystem"] + [str(f) for f in files]
    p = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
    return p.returncode, (p.stdout + p.stderr).strip()


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("sources", nargs="+")
    ap.add_argument("--dfp", required=True, help="AVR-Ex device pack root (the Makefile's DFP)")
    ap.add_argument("--cc", default="avr-gcc")
    ap.add_argument("--cppcheck", default="cppcheck")
    a = ap.parse_args()

    if not shutil.which(a.cppcheck):
        sys.exit(f"fw_lint: `{a.cppcheck}` not found. apt-get install cppcheck, or pass --cppcheck.")
    dfp_inc = Path(a.dfp).resolve() / "include"
    if not (dfp_inc / "avr" / "ioavr64ea28.h").is_file():
        sys.exit(f"fw_lint: no device header under {dfp_inc} -- is --dfp the AVR-Ex pack?")
    tc_inc = toolchain_include(a.cc)
    defs = device_defines(a.dfp)
    ver = subprocess.run([a.cppcheck, "--version"], capture_output=True, text=True).stdout.strip()
    print(f"firmware lint ({ver}; platform avr8; gating: error,{GATING})")
    print(f"  device defines from the pack's spec file: {' '.join(defs)}")

    ok = True
    with tempfile.TemporaryDirectory(prefix="fw_lint_") as tmp:
        for name, text, what in (("plain", CANARY_PLAIN, "cppcheck is running and its verdict is honoured"),
                                 ("header", CANARY_HEADER, "the device header resolves")):
            f = Path(tmp) / f"canary_{name}.c"
            f.write_text(text)
            rc, out = cppcheck(a.cppcheck, [f], defs, dfp_inc, tc_inc, tmp)
            if rc == 1 and "arrayIndexOutOfBounds" in out:
                print(f"  OK    canary ({name}): caught -- {what}")
            else:
                print(f"  FAIL  canary ({name}): a planted out-of-bounds write was NOT reported "
                      f"(exit {rc}). Not established: {what}. A clean result below would mean nothing.")
                if out:
                    print("          " + out.replace("\n", "\n          "))
                ok = False

    rc, out = cppcheck(a.cppcheck, a.sources, defs, dfp_inc, tc_inc, None)
    if rc == 0 and not out:
        print(f"  OK    {len(a.sources)} source file(s): no findings")
    else:
        print(f"  FAIL  cppcheck exit {rc}:")
        print("          " + (out or "(no output)").replace("\n", "\n          "))
        ok = False

    print("firmware lint: " + ("PASS" if ok else "FAILED"))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
