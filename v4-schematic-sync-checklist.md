# v4 schematic sync checklist -- bring `.kicad_sch` up to the routed PCB

> **DONE (kept as the record of what was applied).** The schematic was synced to the board
> programmatically and verified against the PCB netlist; KiCad ERC/DRC pass in CI. Note the three
> AEM bulk caps were renamed to valid KiCad refdes: **CSRC -> C25, CINT -> C26, CSTO -> C27**
> (KiCad rejects letters-only references). This schematic uses a pin -> 5.08 mm stub wire -> global
> label per pin (not label-on-pin), so every added pin carries a stub wire to its label.

**The PCB is the source of truth here.** `PCB/solar-glow-drh-v4_0.kicad_pcb` carries the verified,
fully-routed v4 netlist (0 unconnected pads). The schematic previously reflected v3, which produced 107
footprint parity errors before this checklist was applied; it has since been synced to v4 (the AEM10300/U8
symbol and the EN_STO_CH/STO_SNS/BUFSRC nets are present, and ERC/DRC-parity now pass in CI). This checklist
records how the schematic was made to match the PCB; nothing here is a new decision,
it is `v4-aem10300-prewiring.md` sections 2/3/5 expressed as schematic labels.

**The accelerator:** this schematic is **global-label style (184 global labels), each reached by a 5.08 mm stub wire from its pin (not label-on-pin)**. So a
connection is just a global label placed on a pin -- no wires to draw. Add a part = drop the symbol +
one global label per pin. Re-net a pin = change the label text on that pin.

(Why this is a checklist and not a patched file: kiutils cannot round-trip the KiCad-10 format -- a no-op
load/save dropped 19,741 lines to 6,496 -- and there is no `kicad-cli`/KiCad in the tooling here to
validate a blind hand-edit, so an auto-edited `.kicad_sch` could not be handed back safely.)

## A. Delete these 11 symbols

`U2, U4, Q1, R7, R8, R9, C2, D1, D9, D10, D11`

Their nets `CLBASE, CLREF, REF_TIE, VCMP` disappear with them (delete any leftover labels of those names).

## B. Re-net existing pins

- **Global relabel** (safe, every instance): every `VIN` label -> `SRC`; every `VINB` label -> `SRC`.
  (VIN and VINB fully merge into SRC once the blocking diodes above are gone.)
- **U1 MCU spares:** `PA4` label on **U1 pin 2** -> `EN_STO_CH`. Add a `STO_SNS` label on **U1 pin 11
  (PD1)** (currently unconnected -- remove any no-connect there first).
- **VS -> STO on exactly these 7 pins** (leave every other `VS` label alone -- MCU/accel/decoupling stay VS):
  - SC1 (+), SC2 (+)  -- pack-top positives
  - SW2 (the VS pin)  -- LED full-bright feed
  - R12 (the VS pin)  -- SW2 TINY ballast
  - J1 pin 2, JP1 pin 2, TC1 pin 2  -- bench / prog power
- **PD2 / VSENSE:** no label change (its net stays `VSENSE`); it now divides `SRC` because R5.1 moved to
  SRC in step B. Nothing to do in the schematic.

## C. Add these 13 symbols, one global label per pin

### U8 -- AEM10300 (QFN-28 + EP)

| Pin | Name | Net | | Pin | Name | Net |
|---|---|---|---|---|---|---|
| 1 | ZMPP | **NC** | | 15 | STO_OVDIS | **NC** |
| 2 | SRC | SRC | | 16 | STO_RDY | **NC** |
| 3 | GND | GND | | 17 | STO_OVCH | **NC** |
| 4 | BUFSRC | BUFSRC | | 18 | STO_CFG[3] | GND |
| 5 | LIN | LX_LIN | | 19 | EN_HP | GND |
| 6 | LOUT | LX_LOUT | | 20 | T_MPP[0] | VINT |
| 7 | GND | GND | | 21 | EN_STO_FT | GND |
| 8 | R_MPP[2] | VINT | | 22 | T_MPP[1] | GND |
| 9 | R_MPP[1] | GND | | 23 | STO_CFG[0] | VINT |
| 10 | VINT | VINT | | 24 | STO_CFG[1] | VINT |
| 11 | R_MPP[0] | GND | | 25 | STO_CFG[2] | GND |
| 12 | EN_STO_CH | EN_STO_CH | | 26 | ST_STO | **NC** |
| 13 | BAL | MID | | 27 | GND | GND |
| 14 | STO | STO | | 28 | CS_IN | SRC |
| | | | | EP | pad | GND |

Put a **no-connect flag** on pins **1, 15, 16, 17, 26**. Straps read: R_MPP = HLL (80% Voc),
T_MPP = LH, STO_CFG = LLHH (dual-cell supercap), EN_HP = GND, EN_STO_FT = GND -- these are the VINT/GND
labels above, so nothing extra to set.

### The rest

| Part | Value | Pin -> net |
|---|---|---|
| **U9** | TPS7A0233 (SOT-23-6 land, 5-pin die) | 1 STO · 2 GND · 3 STO · 4 NC · **5 NC** · **6 VS** |

> **⚠ U9 pin-map trap — corrected 2026-07-26.** This row previously read `5 VS · 6 NC`, which
> put the 3.3 V rail on a pad the physical part does not touch, leaving VS with no source.
> A 5-pin SOT-23 has three leads on one side and **two on the other, level with pins 1 and 3** —
> the middle position opposite pin 2 is **vacant** (TPS7A02 datasheet §5: `IN 1 ↔ 5 OUT`,
> `GND 2` with nothing opposite, `EN 3 ↔ 4 NC`). On the SOT-23-**6** land the pads run
> 1/2/3 down one side and 4/5/6 down the other, so pad 5 is that vacant middle and the OUT
> lead lands on **pad 6**. Die pin 5 (OUT) therefore maps to LAND pad 6, not pad 5.
> DRC cannot catch this: the NC pads are `passive+no_connect`, so it reports zero unconnected
> pads. It is also orientation-independent — IN and EN are both on STO_LDO, so a 180°-rotated
> part still satisfies the three-lead side and lands OUT on pad 4, also an NC net.
| **L2** | 10 uH | 1 LX_LIN · 2 LX_LOUT |
| **C25** | 22 uF | 1 BUFSRC · 2 GND |
| **C26** | 10 uF | 1 VINT · 2 GND |
| **C27** | 10 uF | 1 STO · 2 GND |
| **C22** | 1 uF | 1 STO · 2 GND |
| **C23** | 2.2 uF | 1 VS · 2 GND |
| **C24** | 100 nF | 1 STO_SNS · 2 GND |
| **R15** | 2 M | 1 STO · 2 STO_SNS |
| **R16** | 1 M | 1 STO_SNS · 2 GND |
| **R17** | 1 M | 1 VINT · 2 EN_STO_CH |
| **FB1** | ferrite | 1 STO · 2 STO |

Assign each new symbol the footprint the PCB already uses (so "Update PCB from Schematic" reports no
footprint change): U8 = the QFN-28 land on the board, U9 = its SOT-23, passives = their 0402 lands,
L2 / C25 / C26 / C27 / FB1 = whatever you re-landed them to.

## D. Verify

1. **ERC** -- should be clean of net errors (the `PA4`/spare isolated-label warnings resolve once PA4
   becomes EN_STO_CH with U8.12 + R17.2 on it).
2. **Update PCB from Schematic** -- should report ~0 net/footprint changes, because the PCB already
   matches this. If it wants to change a PCB net, that pin's label is wrong -- fix the label, not the PCB.
3. Re-run **DRC with schematic parity** -- the 107 footprint errors clear (only the pre-existing excluded
   set + the U9/FB1 silk warning remain).
4. Then the staged **`board.h`** + **firmware** patches apply cleanly in one commit (consistency needs
   `EN_STO_CH` on U1.PA4 and `STO_SNS` on U1.PD1 in the schematic netlist, which step B provides).

## Cross-check (net -> the pins that must share the label)

Use this to confirm after capture -- every pin listed for a net must carry that net's label:

- **STO** (11): SC1+, SC2+, SW2, R12, J1.2, JP1.2, TC1.2, U8.14, C27.1, R15.1, FB1.1
- **STO_LDO** (4): FB1.2, U9.1, U9.3, C22.1 -- FB1 series-filters the LDO island: STO --FB1--> STO_LDO, with C22 (1 uF) as the filtered LDO-input cap and U9 IN/EN on the island. (Board copper still needs the trace cut between FB1.1/FB1.2 + STO_LDO routed to U9/C22.)
- **SRC** (8): PV1+, PV1+t, PV2+, PV2+t, R5.1, TP1.1, U8.2, U8.28
- **VINT** (7): U8.8, U8.10, U8.20, U8.23, U8.24, C26.1, R17.1
- **STO_SNS** (4): U1.11, C24.1, R15.2, R16.1
- **EN_STO_CH** (3): U1.2, U8.12, R17.2
- **MID** (5): SC1-, SC2-, SC3+, SC4+, U8.13
- **BUFSRC** (2): U8.4, C25.1 · **LX_LIN** (2): U8.5, L2.1 · **LX_LOUT** (2): U8.6, L2.2
- **VS** keeps: U1.18, U1.24, U3.10, U3.12, R10.2, R11.2, C1.1, C4.1, C6.1, C7.1, C12.1, SJ1.1, U6.1, U9.5, C23.1
