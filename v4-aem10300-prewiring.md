# v4 AEM10300 pre-wiring plan (net + pin assignments)

Companion to `solar-glow-drh-design-notes.md` -> "Addendum (2026-07-15) -- v4 active-harvest option".
**Status: v4.0 ADOPTED -- the active revision.** This is the executable net/pin list for the manual KiCad respin: add the
new parts off to the side, wire each pin to the net named here (the ratsnest then guides placement), and
delete the parts in section 4. Every net/refdes below was read from the committed
`PCB/solar-glow-drh-v4_0.kicad_pcb`.

## Net model (what changes)

The as-built `VS` net does two jobs at once (storage top AND the MCU/accel supply) because the clamp fuses
them. The AEM splits them:

- **`VS` is redefined as the regulated 3.3 V rail** (the TPS7A02 output). The MCU, accel, I2C pull-ups,
  decoupling, VDDIO2, and the load switch all *stay on `VS`* -- they just get a clean 3.3 V now instead of
  the clamped supercap. This keeps firmware/doc churn minimal ("VS" still means "the MCU rail").
- **`STO` is a new net** = the supercap top (unclamped, 0.2 - 4.65 V). Supercaps, the LED feed, bench power,
  the AEM, and the LDO input live here.
- **`SRC` is a new net** = the merged panel node (old `VIN` + `VINB`) feeding the AEM harvester.
- Vanishing nets (clamp/comparator subcircuit): `CLBASE`, `CLREF`, `REF_TIE`, `VCMP`, `VIN`, `VINB`.

## 1. New components (place to the side)

| Refdes | Part | Package | Role |
|---|---|---|---|
| **U8** | AEM10300 | QFN-28 4x4 | harvest PMIC + 2-cell balancer |
| **U9** | TPS7A0233 (fixed 3.3 V) | SOT-23-5 | MCU + accel LDO (25 nA) |
| **L2** | 10 uH, ISAT >= 1 A, low-profile | ~2016/2020 | buck-boost inductor |
| **C25** (was CSRC) | 22 uF | 0805 | BUFSRC input buffer |
| **C26** (was CINT) | 10 uF | 0603 | VINT buffer |
| **C27** (was CSTO) | 100 uF (optional) | bulk | STO buffer |
| **C22, C23** | 1 uF | 0402 | LDO in / out caps |
| **R15, R16** | 2 M, 1 M | 0402 | STO sense divider (÷3) |
| **C24** | 100 nF | 0402 | STO-sense filter |
| **R17** | 1 M | 0402 | EN_STO_CH pull-up to VINT |
| **FB1** | ferrite bead | 0603 | STO island feed filter |

(Refdes U8/U9/L2/... are suggestions; renumber to your scheme. ST_STO status pins left unpopulated --
charge state comes from the STO ADC read, so the AEM `ST_STO` pin is a test point / DNP.)

## 2. Pin -> net for the new components

**U8 AEM10300** (straps: R_MPP = HLL 80%, T_MPP = LH, STO_CFG = LLHH dual-cell supercap, EN_HP = GND,
EN_STO_FT = GND):

| Pin | Name | Net | | Pin | Name | Net |
|---|---|---|---|---|---|---|
| 1 | ZMPP | *NC (float)* | | 15 | STO_OVDIS | *NC (float)* |
| 2 | SRC | `SRC` | | 16 | STO_RDY | *NC (float)* |
| 3 | GND | `GND` | | 17 | STO_OVCH | *NC (float)* |
| 4 | BUFSRC | `BUFSRC` | | 18 | STO_CFG[3] | `GND` (L) |
| 5 | LIN | `LX_LIN` | | 19 | EN_HP | `GND` |
| 6 | LOUT | `LX_LOUT` | | 20 | T_MPP[0] | `VINT` (H) |
| 7 | GND | `GND` | | 21 | EN_STO_FT | `GND` |
| 8 | R_MPP[2] | `VINT` (H) | | 22 | T_MPP[1] | `GND` (L) |
| 9 | R_MPP[1] | `GND` (L) | | 23 | STO_CFG[0] | `VINT` (H) |
| 10 | VINT | `VINT` | | 24 | STO_CFG[1] | `VINT` (H) |
| 11 | R_MPP[0] | `GND` (L) | | 25 | STO_CFG[2] | `GND` (L) |
| 12 | EN_STO_CH | `EN_STO_CH` | | 26 | ST_STO | *NC / TP (DNP)* |
| 13 | BAL | `MID` | | 27 | GND | `GND` |
| 14 | STO | `STO` | | 28 | CS_IN | `SRC` |
| | | | | EP | pad | `GND` |

**U9 TPS7A0233:** 1 IN -> `STO`, 2 GND -> `GND`, 3 EN -> `STO` (always-on), 4 NC, 5 OUT -> `VS`.
**L2:** 1 -> `LX_LIN`, 2 -> `LX_LOUT`.
**C25/CSRC:** 1 -> `BUFSRC`, 2 -> `GND`. **C26/CINT:** 1 -> `VINT`, 2 -> `GND`. **C27/CSTO:** 1 -> `STO`, 2 -> `GND`.
**C22 (LDO in):** 1 -> `STO`, 2 -> `GND`. **C23 (LDO out):** 1 -> `VS`, 2 -> `GND`.
**R15:** 1 -> `STO`, 2 -> `STO_SNS`. **R16:** 1 -> `STO_SNS`, 2 -> `GND`. **C24:** 1 -> `STO_SNS`, 2 -> `GND`.
**R17 (EN_STO_CH pull-up):** 1 -> `VINT`, 2 -> `EN_STO_CH`.
**FB1:** in series on the STO feed leaving the island (AEM-local STO <-> board `STO`); a layout element,
net stays `STO` both sides for schematic parity.

## 3. Existing pins that re-net

**Move off `VS` -> `STO`** (storage / LED feed / bench power entry):

| Pin | Was | Now | note |
|---|---|---|---|
| SC1.P, SC2.P | VS | `STO` | pack top-stage positives |
| SW2.1 | VS | `STO` | LED full-bright feed |
| R12.2 | VS | `STO` | SW2 TINY-mode ballast (R12 stays) |
| J1.2, JP1.2, TC1.2 | VS | `STO` | bench / prog power -> storage (update bench pad-strip labels) |

**Merge panels -> `SRC`** (old `VIN` + `VINB` collapse; blocking diodes gone):

| Pin | Was | Now |
|---|---|---|
| PV1.P, PV1.Pt | VIN | `SRC` |
| PV2.P, PV2.Pt | VINB | `SRC` |
| R5.1 | VIN | `SRC` (VSENSE light divider now senses SRC) |
| TP1.1 | VIN | `SRC` |

**`MID`:** add **U8.13 (BAL)**; drop U2.4/6/7 (U2 deleted). Supercap taps (SC1.N, SC2.N, SC3.P, SC4.P) stay.

**Stay on `VS` (now the regulated 3.3 V rail)** -- no wire change, but confirm intent:
U1.18, U1.24 (MCU VDD); U3.10, U3.12 (accel VDD); R10.2, R11.2 (I2C pull-ups); C1.1, C4.1, C6.1, C7.1,
C12.1 (decoupling); SJ1.1 (-> VDDIO2); U6.1 (NFC/FRAM load-switch input). Add **U9.5 (LDO OUT)** and
**C23.1** here as the rail's source.

## 4. MCU spare-pin assignments (new signals)

| MCU pin | Pad | Net | Direction | Role |
|---|---|---|---|---|
| PD1 (AIN1) | 11 | `STO_SNS` | ADC in | supercap-state sense (÷3 divider) |
| PA4 | 2 | `EN_STO_CH` | GPIO out, open-drain | gate AEM charging low during NFC read |
| PC0 | 6 | *(reserved)* | -- | optional ST_STO if ever populated |

PD1 is currently `unconnected-(U1-PD1-Pad11)`; PA4 is the JP2.1 spare. EN_STO_CH is 2.75 V-max -> the MCU
drives it open-drain (low = disable) and R17 pulls it to VINT (2.2 V) when released.

## 5. Delete these (with the nets they take with them)

| Refdes | Part | Why gone |
|---|---|---|
| **U2** | ALD910025 balancer | AEM `BAL` pin does it on-chip |
| **U4** | TLV3011 comparator | AEM `VOVCH` handles overvoltage |
| **Q1** | BCP5316 PNP | shunt clamp removed |
| **R7, R8** | 6.81 M / 3.74 M | clamp reference divider |
| **R9** | 1 k | Q1 base resistor (VS -> CLBASE) |
| **D10, D11** | MMSD301T1G | comparator-supply OR |
| **C2** | 100 nF | VCMP decoupling |
| **D1, D9** | MMSD301T1G | per-panel blocking (AEM has reverse protection; keep panels diode-less for low-V harvest efficiency) |

Nets removed: `CLBASE`, `CLREF`, `REF_TIE`, `VCMP`, `VIN`, `VINB`.

**Keep (do not delete):** R12 (TINY ballast, re-net to STO), C13 (LED anode bulk, on ANODE), R5/R6/C5
(VSENSE divider, now on SRC), R10/R11 (I2C pull-ups), R14 (NFC_EN pulldown), U6 (load switch), SJ1, SW2.

## 6. Verify after wiring

- ERC/DRC: the vanished nets (VCMP/CLBASE/...) leave no dangling pins; `SRC`/`STO`/`VINT`/`LX_*` are new.
- `scripts/check_consistency.py`: board.h pin map picks up PD1/PA4 additions; BOM gains U8/U9/L2/... and loses U2/U4/Q1/R7-9/D1/D9-11/C2.
- Firmware (staged as `v4-aem10300-firmware.patch`, see section 8): re-points `sense_vdd_mv()` + the four
  rail gates from VDD/10 to the `STO_SNS` AIN, re-folds the count macros, and adds the EN_STO_CH
  open-drain gate on the FD edge.

## 7. board.h additions (apply in lockstep with the schematic)

> **STAGED (2026-07-18):** these edits are captured as **`v4-aem10300-boardh.patch`** (repo root),
> verified `git apply --check` clean against the current board.h. **board.h itself is left UNCHANGED
> on purpose** -- applying it before the reworked schematic carries the new nets would fail
> `check_consistency.py` [1] (board.h would claim PA4 -> EN_STO_CH / PD1 -> STO_SNS while the exported
> netlist still says PA4 / unconnected). When the reworked `.kicad_pcb` + `.kicad_sch` land, in the
> **same commit**: run `git apply v4-aem10300-boardh.patch`, and make the schematic put **U1.PA4 on net
> `EN_STO_CH`** and **U1.PD1 on net `STO_SNS`** (exact strings; PD2/`VSENSE` keeps its net name but now
> divides `SRC`). Then the pin contract matches and CI passes. The patch is minimal (pin-map + the two
> `#define` blocks); bumping the board.h header `v3.0 -> v4.0` and swapping residual `VIN` comments to
> `SRC` are cosmetic follow-ups, not in the patch.

`scripts/check_consistency.py` parses board.h's pin-map table and compares it against the **schematic
netlist**, so these edits must land in the **same commit as the schematic net rename** (PD1 -> `STO_SNS`,
PA4 -> `EN_STO_CH`). Do NOT apply them to board.h before the reworked board/schematic is in, or CI will flag
board.h as ahead of the netlist. Staged here so the apply is mechanical.

**Pin-map table** -- change the PA4 line, add a PD1 line (keep the column format the parser reads; net name
must match the schematic exactly):

```
 *     2 PA4      EN_STO_CH  AEM10300 charge gate (open-drain, LOW = disable during NFC read)
 *    11 PD1      STO_SNS    supercap-state sense  AIN1 (STO via R15/R16 divide-by-3)
```

PA4 was `spare GPIO (JP2.1)`; PD1 was unconnected. PD2/`VSENSE` keeps its pin but now senses `SRC` (light) --
update its role comment; no functional change.

**New #defines** (add near the existing sense / NFC blocks):

```c
/* ---- supercap-state sense on PD1 (AEM10300 STO via divide-by-3) ----
 * VS is now the regulated 3.3 V LDO output (constant), so the old VDD/10 read no longer tracks
 * the pack. STO (0.2..4.65 V) is divided by 3 into AIN1/PD1; the re-pointed sense_vdd_mv() reads
 * this channel and scales back: STO_mv = pin_mv * STO_DIVIDER. */
#define STO_SNS_AIN     ADC_MUXPOS_AIN1_gc     /* PD1 = AIN1 */
#define STO_DIVIDER     3                       /* R15 / R16 = 2 M / 1 M */

/* ---- AEM10300 charge gate on PA4 (EN_STO_CH), ACTIVE-LOW, emulated open-drain ----
 * Drive OUTPUT-LOW to disable AEM charging -> the >=10 MHz DCDC goes quiet for an NFC read;
 * RELEASE (set INPUT / Hi-Z) to re-enable (R17 pulls it to VINT). Driven from the FD both-edge
 * handler in main.c (FD falling -> low, FD rising -> release). Open-drain because EN_STO_CH is
 * 2.75 V-max while the MCU rail is 3.3 V. */
#define ENSTOCH_PORT    PORTA
#define ENSTOCH_PIN_bm  PIN4_bm
```

**Re-scale, do not add:** the existing glow gates (`VS_GLOW_FLOOR_MV`, `VS_GLOW_FULL_MV`,
`SWEEP_CAPS_FULL_MV`, `EE_WRITE_FLOOR_MV`, `VS_GLOW_DIM_PEAK`) are now read against STO's 0.2..4.65 V range
instead of the old clamped 2.6..3.5 V rail (the sense.c re-point makes `sense_vdd_mv()` return STO).
Bench-tune the values; no new symbols needed.

When the reworked board lands, I apply the two table lines + the #defines to board.h and make the matching
`STO_SNS` / `EN_STO_CH` net names in the schematic in one commit, and `check_consistency.py` passes.

## 8. Firmware re-point (staged as `v4-aem10300-firmware.patch`)

Companion to the board.h patch above -- the sense/gate code the new rail topology needs. **Staged, not
applied:** it references the board.h patch's `STO_SNS_AIN` / `STO_DIVIDER` / `ENSTOCH_*` defines, so it only
compiles once board.h is patched; landing it early would fail the firmware CI build. Apply it in the **same
commit** as the board.h patch + reworked board/schematic: `git apply v4-aem10300-firmware.patch`.

What it changes:
- **`sense.c` (7 hunks):** re-points `sense_vdd_mv()` and the four rail gates (`sense_rail_ok`,
  `sense_caps_full`, `sense_ee_safe`, and `sense_glow_peak` via `sense_vdd_mv`) from the internal **VDD/10**
  channel to the **STO divider on PD1/AIN1** (`STO_SNS_AIN`), scaling by `STO_DIVIDER` (x3) -- the same
  divider-pin form `sense_vin_mv()` already uses. The compile-time count macros (`RAIL_COUNT`,
  `CAPS_FULL_COUNT`, `EE_SAFE_COUNT`) are re-folded for the STO/3 channel (like `SUN_COUNT`), dropping the
  old VDD/10 10-mV-quantization intermediates.
- **`main.c` (3 hunks):** PD1 pull-up -> `PORT_ISC_INPUT_DISABLE_gc` (analog input); PA4 spare pull-up ->
  the **EN_STO_CH open-drain gate** (OUT latch LOW, DIR toggled -- Hi-Z = charge on via R17 -> VINT, driven
  LOW = charge off; never driven HIGH into the 2.75 V-max pin); and the FD ISR (`PORTA_PORT_vect`) drives it
  -- LOW on the falling edge (field present, silence the >=10 MHz DCDC for the read), released on the rising
  edge.

Verified (no AVR toolchain here -- CI does the real cross-compile at apply time): `git apply --check` clean,
brace/paren balanced, and the re-folded count macros are in-range and monotonic across STO's 0.2-4.65 V span
(VS_GLOW_FLOOR 2600 -> 1420, EE_WRITE_FLOOR 2700 -> 1475, SWEEP_CAPS_FULL 3300 -> 1803; max STO count ~2540,
all < 4096, no saturation).

**Bench-tune after wiring:** the threshold *values* (`VS_GLOW_FLOOR_MV`, `VS_GLOW_FULL_MV`,
`SWEEP_CAPS_FULL_MV`, `EE_WRITE_FLOOR_MV`, `VS_GLOW_DIM_PEAK`) are still the v3 clamped-rail numbers; they now
act on STO's wider 0.2-4.65 V range and want re-tuning (e.g. caps-full nearer VOVCH 4.65 V, not 3.3 V).
Cosmetic follow-up not in the patch: a few residual "VDD/10" mentions in `sense.h` and `sense_glow_peak`.
