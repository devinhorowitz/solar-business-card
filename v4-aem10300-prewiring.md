# v4 AEM10300 pre-wiring plan (net + pin assignments)

Companion to `solar-glow-drh-design-notes.md` -> "Addendum (2026-07-15) -- v4 active-harvest option".
**Status: v4 OPTION, not adopted.** This is the executable net/pin list for a manual KiCad respin: add the
new parts off to the side, wire each pin to the net named here (the ratsnest then guides placement), and
delete the parts in section 4. Every net/refdes below was read from the committed
`PCB/solar-glow-drh-v3_0.kicad_pcb`.

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
| **CSRC** | 22 uF | 0805 | BUFSRC input buffer |
| **CINT** | 10 uF | 0603 | VINT buffer |
| **CSTO** | 100 uF (optional) | bulk | STO buffer |
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
**CSRC:** 1 -> `BUFSRC`, 2 -> `GND`. **CINT:** 1 -> `VINT`, 2 -> `GND`. **CSTO:** 1 -> `STO`, 2 -> `GND`.
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
- Firmware (see the design-notes addendum firmware section): re-point `sense_vdd_mv()` from VDD/10 to the
  `STO_SNS` AIN, re-scale glow thresholds, add the EN_STO_CH gate on the FD edge.
