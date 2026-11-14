#!/usr/bin/env python3
"""
fw_prove.py -- machine-check two pieces of the firmware with CBMC, on the source as written.

Nothing here can be run on hardware yet, and one of the two is interrupt-shared state that
a bench would have to be very lucky to catch misbehaving. So they are PROVED instead, for
every input and every interleaving, on the function text taken verbatim out of the tree.

  [P1] sense_glow_peak() -- the one chokepoint every glow's brightness passes through.
       For all 65,536 rail readings x 256 requested peaks: never brighter than asked; dark
       below the glow floor; full brightness on a healthy rail; the ballast clamp holds
       above its threshold; monotonic in the rail; no overflow, no division by zero.

  [P2] the deferred STO sample service (sense.h / sense.c) -- a four-state machine written
       by both the main loop and the PIT interrupt. Proved as an INDUCTIVE INVARIANT, so
       the result is not bounded by a trace length: from ANY state satisfying the
       invariant, any one main-loop operation, interleaved at every instruction boundary
       with up to two PIT edges, re-establishes it. And inside that:
         - the divider is on at every conversion;
         - a deferred sample is converted only after the divider has been on across one
           whole PIT period, edge to edge -- the property the 2026-08-09 sampler assumed
           and did not have;
         - the divider is never left on with nobody waiting for it.

A proof that cannot fail proves nothing, so each carries CANARIES: the same harness over
a deliberately broken copy of the source, which CBMC must REJECT -- and reject on the
property the mutation attacks, not on a parse error. If a canary verifies, the harness has
stopped looking and this script fails.

What is modelled rather than run, and so NOT proved: the pin (two statement forms are
mapped onto a boolean, and the script refuses the source if it finds a third); the ADC
(any 12-bit value); time (an edge is an event, a period is the gap between two); the
EEPROM writes downstream. Interrupt latency is taken as zero -- microseconds against a
6.7 ms time constant.

  python3 scripts/fw_prove.py [--cbmc cbmc] [--keep DIR]
"""
import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FW = ROOT / "firmware"

CBMC_FLAGS = ["--16",                       # AVR data model: int 16, long 32, pointer 16
              "--unsigned-overflow-check", "--signed-overflow-check",
              "--conversion-check", "--div-by-zero-check",
              "--bounds-check", "--pointer-check"]

PRELUDE = r'''
/* AVR data model with no libc headers: cbmc --16 has none to offer. */
typedef unsigned char uint8_t;
typedef unsigned int  uint16_t;
typedef unsigned long uint32_t;
_Static_assert(sizeof(int) == 2 && sizeof(uint16_t) == 2 && sizeof(uint32_t) == 4,
               "not the AVR data model -- is --16 still passed?");
uint8_t  nondet_u8(void);
uint16_t nondet_u16(void);
#include "board.h"      /* the REAL one: every constant and knob below is the tree's */
'''


# ----------------------------------------------------------------------------- source

def extract(path, signature):
    """The function whose first line is exactly `signature`, through its closing brace at
    column 0. Verbatim. Refuses anything but exactly one match."""
    lines = path.read_text().split("\n")
    hits = [i for i, ln in enumerate(lines) if ln == signature]
    if len(hits) != 1:
        sys.exit(f"fw_prove: expected exactly one `{signature}` in {path.name}, "
                 f"found {len(hits)} -- the harness no longer knows what it is proving")
    i = hits[0]
    if lines[i + 1] != "{":
        sys.exit(f"fw_prove: `{signature}` in {path.name} is not followed by a `{{` line")
    for j in range(i + 2, len(lines)):
        if lines[j] == "}":
            return "\n".join(lines[i:j + 1]) + "\n"
    sys.exit(f"fw_prove: no closing brace for `{signature}` in {path.name}")


def mutate(text, old, new, what):
    """Replace exactly one occurrence, or stop: a canary that silently changed nothing
    would 'fail to fail' for the wrong reason, and one that changed two things is not the
    canary it says it is."""
    if text.count(old) != 1:
        sys.exit(f"fw_prove: canary '{what}' expects exactly one `{old.strip()}` in the "
                 f"source it mutates, found {text.count(old)}")
    return text.replace(old, new)


PIN_ON = "SNS_EN_PORT.OUTSET = SNS_EN_PIN_bm;"
PIN_OFF = "SNS_EN_PORT.OUTCLR = SNS_EN_PIN_bm;"


def model_pins(text, where):
    """Map the two pin-write statements onto the model. Anything else touching a register
    is a statement the model has no meaning for, so it is refused rather than ignored."""
    out = text.replace(PIN_ON, "model_gate_on();").replace(PIN_OFF, "model_gate_off();")
    code = re.sub(r"/\*.*?\*/", "", out, flags=re.S)
    leftover = re.findall(r"\b(?:SNS_EN_PORT|PORT[A-F]|ADC0|RTC|VREF|NVMCTRL)\b[^;\n]*", code)
    if leftover:
        sys.exit(f"fw_prove: {where} touches hardware the model does not cover: "
                 f"{leftover[0].strip()!r}. Extend the model (and say what it means) "
                 "before trusting the proof.")
    return out


# ----------------------------------------------------------------------------- P1

def harness_glow(fn_text):
    return PRELUDE + r'''
static uint16_t g_mv;
static uint16_t sense_vdd_mv(void) { return g_mv; }

/* ---- verbatim from firmware/sense.c ---- */
''' + fn_text + r'''
int main(void)
{
    uint8_t peak = nondet_u8();
    g_mv = nondet_u16();
    uint16_t mv1 = g_mv;
    uint8_t r1 = sense_glow_peak(peak);
    __CPROVER_assert(r1 <= peak, "never brighter than asked");
    if (mv1 < VS_GLOW_FLOOR_MV)
        __CPROVER_assert(r1 == 0, "dark below the glow floor");
#if USE_BALLAST_GUARD
    if (mv1 >= VS_GLOW_FULL_MV && mv1 <= GLOW_CLAMP_STO_MV)
        __CPROVER_assert(r1 == peak, "full brightness on a healthy rail");
    if (mv1 > GLOW_CLAMP_STO_MV)
        __CPROVER_assert(r1 <= GLOW_CLAMP_PEAK, "ballast clamp holds above its threshold");
#else
    if (mv1 >= VS_GLOW_FULL_MV)
        __CPROVER_assert(r1 == peak, "full brightness on a healthy rail");
#endif
    /* monotonic in the rail, up to the clamp (above it the peak is deliberately cut) */
    g_mv = nondet_u16();
#if USE_BALLAST_GUARD
    __CPROVER_assume(g_mv >= mv1 && g_mv <= GLOW_CLAMP_STO_MV);
#else
    __CPROVER_assume(g_mv >= mv1);
#endif
    uint8_t r2 = sense_glow_peak(peak);
    __CPROVER_assert(r2 >= r1, "monotonic in the rail");
    return 0;
}
'''


# ----------------------------------------------------------------------------- P2

def harness_rail(parts, cancel_on_reconfig=True):
    """parts: dict of verbatim, pin-modelled source fragments."""
    reconfig = "sense_rail_cancel();" if cancel_on_reconfig else "/* canary: no cancel */"
    return PRELUDE + r'''
/* ---------------- the model ---------------- */
static _Bool   gate;             /* U10 on: the divider is connected to STO                */
static _Bool   edge_seen;        /* a PIT edge has passed with the divider continuously on */
static _Bool   full_period;      /* ...and a second one: on across one whole period        */
static _Bool   in_tick;          /* the conversion in progress is the deferred one         */
static _Bool   isr_done;
uint8_t SREG = 0x80;             /* bit 7 = global interrupt enable                        */
#define cli()            (SREG &= 0x7Fu)
#define _delay_ms(ms)    ((void)0)          /* time is edges, not milliseconds */
#define adc_read_raw(ch) model_adc()
_Bool nondet_bool(void);

static void model_gate_on(void)
{
    gate = 1;      /* one store: atomic as it stands. (The ISR calls this from inside its
                    * own atomic section, and CBMC does not nest them.) */
}
static void model_gate_off(void)       /* main loop only -- the ISR never switches it off */
{
    __CPROVER_atomic_begin();
    gate = 0; edge_seen = 0; full_period = 0;      /* the node collapses */
    __CPROVER_atomic_end();
}
static uint16_t model_adc(void)
{
    __CPROVER_atomic_begin();
    __CPROVER_assert(gate, "the divider is on at every conversion");
    if (in_tick)
        __CPROVER_assert(full_period,
            "a deferred sample is converted only after one whole PIT period of settle");
    __CPROVER_atomic_end();
    uint16_t r = nondet_u16();
    __CPROVER_assume(r <= 4095);
    return r;
}

/* ---- verbatim from firmware/sense.h (pin writes mapped onto the model) ---- */
''' + parts["defines"] + r'''
volatile uint8_t sense_rail_state;
static uint16_t  tick_mv;
''' + parts["edge"] + r'''
/* ---- verbatim from firmware/sense.c (pin writes mapped onto the model) ---- */
''' + parts["mv"] + parts["sto_raw"] + parts["request"] + parts["tick"] + parts["cancel"] + r'''
/* ---------------- the PIT interrupt, as a second thread ---------------- */
static void pit_edge(void)
{
    __CPROVER_atomic_begin();                 /* an ISR runs to completion */
    __CPROVER_assume(SREG & 0x80u);           /* and not while main holds cli */
    sense_rail_edge();
    if (gate) {                               /* AFTER the ISR's own action: a divider it
                                               * just switched on is on from THIS edge */
        if (edge_seen) full_period = 1;
        edge_seen = 1;
    }
    __CPROVER_atomic_end();
}
static void isr_thread(void)
{
    if (nondet_bool()) pit_edge();
    if (nondet_bool()) pit_edge();
    isr_done = 1;
}

/* What is true whenever the main loop is between operations. */
static _Bool invariant(void)
{
    uint8_t s = sense_rail_state;
    return s <= RAIL_READY
        && (s >= RAIL_SETTLING ? (gate && edge_seen) : !gate)   /* on iff someone is waiting */
        && (s == RAIL_READY ? full_period : 1)                 /* READY means a whole period */
        && (gate ? 1 : (!edge_seen && !full_period))
        && (full_period ? edge_seen : 1)
        && (SREG & 0x80u);
}

int main(void)
{
    /* ANY state the invariant allows -- so the conclusion is not bounded by a trace */
    sense_rail_state = nondet_u8();
    gate = nondet_bool(); edge_seen = nondet_bool(); full_period = nondet_bool();
    __CPROVER_assume(invariant());

    __CPROVER_ASYNC_1: isr_thread();

    switch (nondet_u8()) {
    case 0:  break;                                   /* asleep, or code that touches none of this */
    case 1:  rail_request(); break;                   /* a logger asks */
    case 2:  in_tick = 1; sense_rail_tick(); in_tick = 0; break;
    case 3:  (void)sto_raw(); break;                  /* an event read borrows the divider */
    case 4:  /* facedown_deepsleep(): the PIT period is rewritten, so the interval in
              * progress is not a whole period and counts for nothing */
             ''' + reconfig + r'''
             __CPROVER_atomic_begin(); edge_seen = 0; full_period = 0; __CPROVER_atomic_end();
             break;
    default: __CPROVER_assume(0);
    }

    __CPROVER_assume(isr_done);                       /* let the interrupt thread finish */
    __CPROVER_assert(invariant(), "the invariant is re-established");
    return 0;
}
'''


def rail_parts():
    sh = (FW / "sense.h").read_text()
    defs = re.findall(r"^#define\s+RAIL_(?:IDLE|WANT|SETTLING|READY)\s+\d+u\s*$", sh, re.M)
    if len(defs) != 4:
        sys.exit(f"fw_prove: expected the four RAIL_* states in sense.h, found {len(defs)}")
    c = FW / "sense.c"
    vref = re.findall(r"^#define\s+ADC_VREF_MV\s+\d+UL\s*$", c.read_text(), re.M)
    if len(vref) != 1:
        sys.exit(f"fw_prove: expected one ADC_VREF_MV in sense.c, found {len(vref)}")
    return {
        "defines": "\n".join(defs + vref) + "\n",
        "edge": model_pins(extract(FW / "sense.h", "static inline void sense_rail_edge(void)"),
                           "sense_rail_edge"),
        "mv": extract(c, "static uint16_t sto_mv_from_raw(uint16_t raw)"),
        "sto_raw": model_pins(extract(c, "static uint16_t sto_raw(void)"), "sto_raw"),
        "request": extract(c, "static void rail_request(void)"),
        "tick": model_pins(extract(c, "void sense_rail_tick(void)"), "sense_rail_tick"),
        "cancel": model_pins(extract(c, "void sense_rail_cancel(void)"), "sense_rail_cancel"),
    }


def reconfig_is_guarded():
    """[P2] case 4 ASSUMES every rewrite of the PIT period is preceded by
    sense_rail_cancel(). That is a fact about main.c, so read it there: each function that
    writes RTC.PITCTRLA must either be the boot-time init (nothing is in flight yet) or
    call sense_rail_cancel() before its first write."""
    text = (FW / "main.c").read_text()
    code = strip_comments(text)
    problems, seen = [], 0
    for m in re.finditer(r"^static \w[\w \*]*?(\w+)\(([^)]*)\)\n\{\n(.*?)^\}", code, re.M | re.S):
        name, body = m.group(1), m.group(3)
        w = body.find("RTC.PITCTRLA =")
        if w < 0:
            continue
        seen += 1
        if name == "rtc_pit_init":
            continue
        c = body.find("sense_rail_cancel();")
        if c < 0 or c > w:
            problems.append(name)
    total = len(re.findall(r"RTC\.PITCTRLA\s*=", code))
    in_funcs = sum(len(re.findall(r"RTC\.PITCTRLA\s*=", m.group(3)))
                   for m in re.finditer(r"^static \w[\w \*]*?(\w+)\(([^)]*)\)\n\{\n(.*?)^\}",
                                        code, re.M | re.S))
    if total == 0 or total != in_funcs:
        problems.append(f"{total - in_funcs} PITCTRLA write(s) this reader could not place "
                        "in a function")
    return seen, problems


def strip_comments(text):
    """Blank out comments, keeping every newline so positions still mean lines."""
    return re.sub(r"/\*.*?\*/", lambda m: re.sub(r"[^\n]", " ", m.group()), text, flags=re.S)


# Everything [P2] proves is about FIVE functions. That is a proof about the machine only
# if nothing else writes its state or its pin -- the "a shared definition protects only
# the caller that uses it" gap. So the tree is read for every other touch, and these are
# the only ones allowed, each for a stated reason.
PROVED = [("sense.h", "static inline void sense_rail_edge(void)"),
          ("sense.c", "static uint16_t sto_raw(void)"),
          ("sense.c", "static void rail_request(void)"),
          ("sense.c", "void sense_rail_tick(void)"),
          ("sense.c", "void sense_rail_cancel(void)")]
ALLOWED_OUTSIDE = [
    (r"^#define\s+SNS_EN_PORT\s+PORTC$", "the pin's definition"),
    (r"^extern volatile uint8_t sense_rail_state;$", "declaration"),
    (r"^volatile uint8_t sense_rail_state;$", "definition (zero-initialised = RAIL_IDLE)"),
    (r"^SNS_EN_PORT\.OUTCLR = SNS_EN_PIN_bm;$", "boot: divider off, before interrupts are on"),
    (r"^SNS_EN_PORT\.DIRSET = SNS_EN_PIN_bm;$", "boot: pin direction"),
]


def coverage():
    """-> list of problems. Empty means the proved functions are the whole machine."""
    problems = []
    for f in sorted(FW.glob("*.[ch]")):
        text = f.read_text()
        for name, sig in PROVED:
            if f.name == name:
                body = extract(f, sig)
                text = text.replace(body, "\n" * body.count("\n"))
        for n, line in enumerate(strip_comments(text).split("\n"), 1):
            if not re.search(r"\b(sense_rail_state|SNS_EN_PORT)\b", line):
                continue
            stmt = line.strip()
            if not any(re.match(pat, stmt) for pat, _ in ALLOWED_OUTSIDE):
                problems.append(f"{f.name}:{n}: `{stmt}` touches the sample service's state "
                                "or pin outside the proved functions")
    # the interrupt half: exactly one call, and it is in the PIT handler
    main_c = strip_comments((FW / "main.c").read_text())
    isr = re.search(r"^ISR\(RTC_PIT_vect\)\n\{\n(.*?)^\}", main_c, re.M | re.S)
    calls = sum(len(re.findall(r"\bsense_rail_edge\s*\(\s*\)\s*;", strip_comments(f.read_text())))
                for f in FW.glob("*.[ch]"))
    if not isr or isr.group(1).count("sense_rail_edge();") != 1:
        problems.append("main.c: ISR(RTC_PIT_vect) does not call sense_rail_edge() exactly once")
    elif calls != 1:
        problems.append(f"sense_rail_edge() is called {calls} times; [P2] models exactly one, "
                        "from the PIT interrupt")
    return problems


# ----------------------------------------------------------------------------- run

def run_cbmc(cbmc, src, workdir):
    cmd = [cbmc, str(src), "-I", str(FW), "-I", str(workdir / "stubs")] + CBMC_FLAGS
    p = subprocess.run(cmd, capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def failed_properties(out):
    """Descriptions of the properties CBMC reports as FAILURE."""
    return [m.group(1).strip() for m in
            re.finditer(r"^\[[^\]]+\]\s+(?:line \d+\s+)?(.*?):\s+FAILURE\s*$", out, re.M)]


def expect_success(cbmc, name, text, workdir):
    src = workdir / f"{name}.c"
    src.write_text(text)
    rc, out = run_cbmc(cbmc, src, workdir)
    n = len(re.findall(r":\s+SUCCESS\s*$", out, re.M))
    if rc == 0 and "VERIFICATION SUCCESSFUL" in out and n > 0:
        print(f"  OK    {name}: VERIFICATION SUCCESSFUL, {n} properties")
        return True
    print(f"  FAIL  {name}: cbmc exit {rc}")
    for d in failed_properties(out):
        print(f"          FAILED: {d}")
    if rc not in (0, 10):
        print("          (not a verdict -- cbmc could not process the harness)")
        print("\n".join("          " + ln for ln in out.strip().split("\n")[-12:]))
    return False


def expect_failure(cbmc, name, text, must_fail, workdir):
    """A canary: CBMC must REJECT this, on a property containing `must_fail`."""
    src = workdir / f"{name}.c"
    src.write_text(text)
    rc, out = run_cbmc(cbmc, src, workdir)
    failed = failed_properties(out)
    if rc == 10 and any(must_fail in d for d in failed):
        print(f"  OK    canary {name}: rejected, on \"{must_fail}\"")
        return True
    if rc == 0:
        print(f"  FAIL  canary {name}: the broken source VERIFIED. The harness has stopped "
              "looking; the proofs above mean nothing until this is red again.")
    elif rc == 10:
        print(f"  FAIL  canary {name}: rejected, but not on \"{must_fail}\" -- on {failed}")
    else:
        print(f"  FAIL  canary {name}: cbmc exit {rc}, not a verdict (a parse error is not "
              "a caught bug)")
        print("\n".join("          " + ln for ln in out.strip().split("\n")[-12:]))
    return False


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--cbmc", default="cbmc")
    ap.add_argument("--keep", metavar="DIR", help="write the generated harnesses here and keep them")
    a = ap.parse_args()

    if not shutil.which(a.cbmc):
        sys.exit(f"fw_prove: `{a.cbmc}` not found. Install CBMC (apt-get install cbmc) "
                 "or pass --cbmc.")
    ver = subprocess.run([a.cbmc, "--version"], capture_output=True, text=True).stdout.strip()
    print(f"firmware proofs (CBMC {ver}, 16-bit AVR data model)")

    work = Path(a.keep) if a.keep else Path(tempfile.mkdtemp(prefix="fw_prove_"))
    (work / "stubs" / "avr").mkdir(parents=True, exist_ok=True)
    # board.h includes <avr/io.h> for the register names its macros mention. The proofs
    # expand none of them (model_pins refuses any that survive), so an empty header is
    # the honest stand-in -- and a use that slipped through is a compile error here.
    (work / "stubs" / "avr" / "io.h").write_text("/* fw_prove stand-in: no registers */\n")

    ok = True
    try:
        # ---- P1
        print("[P1] sense_glow_peak()")
        glow = extract(FW / "sense.c", "uint8_t sense_glow_peak(uint8_t peak)")
        ok &= expect_success(a.cbmc, "p1_glow_peak", harness_glow(glow), work)
        ok &= expect_failure(
            a.cbmc, "p1_no_floor",
            harness_glow(mutate(glow, "if (mv < VS_GLOW_FLOOR_MV) return 0;",
                                "if (mv < VS_GLOW_FLOOR_MV) return peak;", "no floor")),
            "dark below the glow floor", work)

        # ---- P2
        print("[P2] deferred STO sample service")
        parts = rail_parts()
        ok &= expect_success(a.cbmc, "p2_rail_service", harness_rail(parts), work)

        # canary A: sto_raw's test-and-switch-off is no longer atomic
        nocli = dict(parts)
        nocli["sto_raw"] = mutate(parts["sto_raw"], "    cli();\n", "", "sto_raw without cli")
        ok &= expect_failure(a.cbmc, "p2_no_cli", harness_rail(nocli),
                             "the invariant is re-established", work)

        # canary B: the divider is switched on from the main loop, as it was until 2026-11-14
        early = dict(parts)
        early["request"] = mutate(
            parts["request"], "        sense_rail_state = RAIL_WANT;",
            "        { model_gate_on(); sense_rail_state = RAIL_SETTLING; }",
            "armed from the main loop")
        ok &= expect_failure(a.cbmc, "p2_main_loop_arm", harness_rail(early),
                             "the invariant is re-established", work)

        # canary D: the conversion does not wait for READY
        hasty = dict(parts)
        hasty["tick"] = mutate(parts["tick"], "if (sense_rail_state != RAIL_READY)",
                               "if (sense_rail_state < RAIL_SETTLING)", "convert while settling")
        ok &= expect_failure(a.cbmc, "p2_convert_early", harness_rail(hasty),
                             "one whole PIT period of settle", work)

        # canary C: a PIT period change that does not drop the sample in flight
        ok &= expect_failure(a.cbmc, "p2_no_cancel", harness_rail(parts, cancel_on_reconfig=False),
                             "the invariant is re-established", work)

        seen, problems = reconfig_is_guarded()
        if problems:
            print("  FAIL  main.c: PIT period rewritten without sense_rail_cancel() first, "
                  f"in: {', '.join(problems)}. [P2] assumes it cannot be.")
            ok = False
        else:
            print(f"  OK    main.c: {seen} function(s) write RTC.PITCTRLA; each is the boot "
                  "init or cancels the sample in flight first")

        cov = coverage()
        for c in cov:
            print(f"  FAIL  {c}")
        if cov:
            ok = False
        else:
            print(f"  OK    coverage: the {len(PROVED)} proved functions are the only code that "
                  "touches the state or the pin (boot init aside)")
    finally:
        if not a.keep:
            shutil.rmtree(work, ignore_errors=True)

    print("firmware proofs: " + ("ALL PASS" if ok else "FAILED"))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
