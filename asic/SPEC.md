# DRH-1 — companion ASIC digital core (experiment)

Target: **wafer.space GF180MCU quarter slot** (4.9 mm², 48 I/O + 8 power pads, ~1.94 × 2.54 mm),
with a **Tiny Tapeout wrapper** so the identical core can be proven on a SKY130 shuttle first.
This directory is the answer to one question, asked 2026-08-10: *can the digital half of a
custom quarter-slot chip be designed, verified and sized directly in this repo, by the agent,
with no external tools beyond what installs in the CI container?* The RTL below absorbs the
board's GREEN set from the ASIC absorb map: U1's application logic, the R15/R16/C24 + U10
sense chain's *sequencing*, Q2+R18's gate, RN1/RN2's function, U6's control. The analog cells
it talks to (RC oscillator, bandgap, comparator + R-2R DAC, 16 mA LED sinks, pass FETs) are
**stubs here by design** — they are schematic-level analog work, not RTL, and are the part
this experiment does NOT claim.

## Global rules (every module)

- Verilog-2001 only. One clock domain: `clk` (nominal 1 MHz on-die RC). Async assert /
  sync release resets are NOT used — plain synchronous logic, `rst_n` sampled on `posedge clk`.
- Every `always @(posedge clk)` block resets every register it owns when `!rst_n`.
- No latches, no `initial` in RTL (testbenches may), no delays in RTL, no tri-state except
  the SDA pad in `i2c_master`. Strobes are exactly one `clk` wide.
- Module headers carry the firmware file they mirror, where one exists (`led.c`, `sense.c`,
  `adxl367.c` equivalents) — the point of this chip is that the card's behaviour is already
  specified by working firmware.

## Module contracts (exact ports — do not deviate)

### rtl/clkdiv.v
```verilog
module clkdiv #(parameter CLK_HZ = 1000000) (
    input  wire clk, input wire rst_n,
    output reg  tick_env,   // 128 Hz, 1-cycle strobe: envelope + settle timing
    output reg  tick_poll   // 1 Hz, 1-cycle strobe: the poll cadence (main.c's PIT)
);
```

### rtl/gamma_pwm.v  (mirrors led.c)
```verilog
module gamma_pwm (
    input  wire clk, input wire rst_n,
    input  wire tick_env,
    input  wire [1:0] mode,   // 00 off | 01 breathe (all 4 in phase) | 10 sweep (90° offsets) | 11 dim solid
    output wire [3:0] led     // active-high to the four 16 mA sink cells
);
```
Triangle envelope 0..255..0 stepped on `tick_env`; per-channel phase offset of 64 envelope
steps in sweep mode; gamma via a `function [7:0] gamma(input [7:0] x)` implementing x²/255
(the cheap gamma-2 the firmware's table approximates); free-running 8-bit PWM counter on `clk`.

### rtl/i2c_master.v
```verilog
module i2c_master #(parameter DIV = 5) (   // SCL ≈ clk / (4*DIV) ≈ 50 kHz
    input  wire clk, input wire rst_n,
    input  wire start, input wire [6:0] dev_addr, input wire rw,   // 0 = write
    input  wire [7:0] reg_addr, input wire [7:0] wdata,
    output reg  [7:0] rdata,
    output reg  busy, output reg done, output reg ack_err,         // done: 1-cycle strobe
    output wire sda_oe_o,   // 2026-08-12 amendment: real port for the pad OE — the TT wrapper
    inout  wire sda, output reg scl   // must NOT reach into the hierarchy for it (finding 1)
);
```
Write: START, addr+W, reg, data, STOP. Read: START, addr+W, reg, reSTART, addr+R, byte, NACK,
STOP. SDA open-drain: `assign sda = sda_oe ? 1'b0 : 1'bz;` — sample via the pin.

### rtl/init_seq.v  (mirrors adxl367.c's config-and-verify)
```verilog
module init_seq (
    input  wire clk, input wire rst_n, input wire start,
    output reg  active, output reg done_all, output reg fail,
    output reg  m_start, output reg [6:0] m_dev, output reg m_rw,
    output reg  [7:0] m_reg, output reg [7:0] m_wdata,
    input  wire m_busy, input wire m_done, input wire m_ack_err
);
```
ROM of 6–8 {reg, val} writes to the ADXL367 at 0x1D (soft reset, thresholds, INTMAP1,
FILTER_CTL, POWER_CTL wake-up mode — values PROVISIONAL, tagged in comments), one `m_done`
handshake per entry; any `m_ack_err` → `fail`, retry once, then park.

### rtl/sar_ctrl.v
```verilog
module sar_ctrl (
    input  wire clk, input wire rst_n, input wire go,
    input  wire cmp_in,                  // analog comparator: 1 when Vin > DAC(dac_code)
    output reg  [7:0] dac_code,
    output reg  [7:0] result, output reg done, output reg busy
);
```
8-bit binary search, 2 clk per bit (set, settle, sample), `done` 1-cycle strobe.

### rtl/sense_seq.v  (mirrors sense.c's DEFERRED-READ pattern — the rule in board.h)
```verilog
module sense_seq #(
    parameter SETTLE_ENV_TICKS = 5,      // ~39 ms at 128 Hz — the RC settle, in silicon
    parameter POLLS_PER_SAMPLE = 16,     // sense.c's VMIN_SAMPLE_POLLS
    parameter [7:0] TH_LOW  = 8'd96,     // vlow: below glow floor   (placeholder scaling)
    parameter [7:0] TH_CRIT = 8'd64      // vcrit: brownout floor
)(
    input  wire clk, input wire rst_n,
    input  wire tick_poll, input wire tick_env,
    input  wire force_rd,                // event path: tap is about to spend a glow
    input  wire [7:0] sar_result, input wire sar_done,
    output reg  sar_go, output reg sns_en,
    output reg  [7:0] sto_q, output reg vlow, output reg vcrit
);
```
IDLE → (every 16th `tick_poll`, or `force_rd`) ARM (`sns_en`=1) → SETTLE (count `tick_env`)
→ CONVERT (`sar_go`, wait `sar_done`) → LATCH (update `sto_q`, `vlow`, `vcrit`) → IDLE with
`sns_en`=0. The divider must be gated off between samples — that is the entire point of the
U10 chain this replaces, and the testbench MUST assert the sns_en duty cycle is bounded.

### rtl/wake_fsm.v  (mirrors main.c's dormancy/tap loop)
```verilog
module wake_fsm #(
    parameter GLOW_POLLS = 4, parameter NFC_HOLD_POLLS = 8
)(
    input  wire clk, input wire rst_n,
    input  wire tick_poll,
    input  wire int1, input wire int2, input wire fd_n,
    input  wire vlow, input wire vcrit, input wire init_done,
    output reg  [1:0] led_mode, output reg force_sense,
    output reg  nfc_en, output reg brownout
);
```
WAIT_INIT → IDLE. Rising `int1` in IDLE: `force_sense` strobe, then if `!vlow` glow
(mode 01) for GLOW_POLLS; second `int1` during glow → sweep (mode 10). `vcrit` → DORMANT:
mode 00, taps ignored, `brownout` asserted, exit only when `!vcrit`. `fd_n` low → `nfc_en`
for NFC_HOLD_POLLS (NFC works unpowered; the rail is only for the FD/I²C extras — same as
the card).

`brownout` is a STATUS output, not a charge control, and that distinction is why it is not
called `chg_dis`: the card's `CHG_DIS_G` (PA4 → Q2 gate) is a charge-**inhibit control**
driven from the FD handler to quiet the DC-DC for an NFC read. Tying this pin to that net
would disable harvest exactly when the tank is empty. It must never reach `EN_STO_CH`.
(Renamed 2026-08-19; `asic.yml` fails if the old name returns.)

### rtl/drh1_top.v
Wire all of the above. Ports:
```verilog
module drh1_top (
    input  wire clk, input wire rst_n,
    output wire [3:0] led,
    inout  wire sda, output wire scl,
    input  wire int1, input wire int2, input wire fd_n,
    output wire nfc_en, output wire sns_en, output wire brownout,
    input  wire cmp_in, output wire [7:0] dac_code,
    output wire [7:0] dbg_sto, output wire [1:0] dbg_mode,
    output wire sda_oe        // 2026-08-12 amendment — pass-through of the master's pad OE
);
```
init_seq owns the I²C master (this experiment has no second master; arbitration is v-next).

### rtl/tt_um_drh_solarglow.v — Tiny Tapeout wrapper (their fixed interface)
```verilog
module tt_um_drh_solarglow (
    input  wire [7:0] ui_in, output wire [7:0] uo_out,
    input  wire [7:0] uio_in, output wire [7:0] uio_out, output wire [7:0] uio_oe,
    input  wire ena, input wire clk, input wire rst_n
);
```
ui_in: 0=int1 1=int2 2=fd_n 3=cmp_in. uo_out: 3:0=led 4=nfc_en 5=sns_en 6=brownout 7=scl.
uio 0: SDA (oe from the master's sda_oe); uio 7:1: dac_code[7:1] out (LSB unobservable on
TT — acceptable for the demo board; the wafer.space padframe has pads to spare).

## Verification floor (per module, Icarus `iverilog -g2012`)

Self-checking testbench, `$fatal` on assertion failure, final line `TB PASS: <name>`.
Integration TB (`tb/tb_top.v`) must include a behavioural ADXL367 I²C slave model that
CHECKS the init writes' addressing, then: tap → observe glow PWM activity on all four LEDs;
vcrit scenario via the SAR/comparator model → DORMANT + brownout; sns_en duty bounded.

## Size gate

`yosys: read_verilog rtl/*.v; hierarchy -top drh1_top; synth; stat` — then map through
`abc -g NAND` for a NAND2-equivalent count. Target: comfortably inside a quarter slot
(≈150–200 kgate capacity at 180 nm after the pad ring); expectation is 5–20 kgates.
