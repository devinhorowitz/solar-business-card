# CLAUDE.md — SOLAR-GLOW · DRH

Orientation for Claude Code (and any contributor) working in this repo.

## What this is
A business-card-sized PCB that runs on harvested indoor light: an **AVR64EA28**
breathes four amber LEDs through a "DRH" monogram cut into the front copper
(backlit through bare FR4), while two indoor solar cells trickle-charge a
**1 F / 5.5 V supercap tank**. Tap-to-wake via accelerometer (no button); an NFC
tag serves a contact vCard. Current revision: **v4.0 -- the managed-solar redesign
(AVR64EA28 + AEM10300 active harvest), in progress; the working files are `v4_0`.**
v3.0 (2-layer, fully routed, passive diode feed + shunt clamp) is frozen as the
**final unmanaged-solar revision**. The v4 rework is specified in the v4 addendum of
`solar-glow-drh-design-notes.md` and the net/pin plan `v4-aem10300-prewiring.md`; the
`v4_0` files currently start as a copy of `v3_0` and are being reworked from there.

## Where the truth lives
Each fact has exactly one home; everything else points at it. The canonical map
is the "Where the truth lives" table in `README.md`. In short:
- Board copper / geometry → `PCB/solar-glow-drh-v4_0.kicad_pcb` / `.kicad_sch`
- Firmware pin map + tunables → `firmware/board.h` and `firmware/README.md`
- BOM master → `PCB/solar-glow-drh-v4_0-BOM.xlsx`
- Design reasoning / lineage → `solar-glow-drh-design-notes.md`

When a doc disagrees with a source file, **the source file wins** and the doc is
what gets corrected. The `*-v2-*.md` docs are v2-era history (banner-marked at the
top) — read them for lineage, not for current values.

## Build & verify
**Firmware** (needs an AVR-Dx-capable `avr-gcc` + the AVR-Dx DFP — install per
`firmware/README.md`):
```sh
make -C firmware DFP=/path/to/Microchip/AVR-Dx_DFP      # -> firmware/solar-glow.hex
```
Should compile **warning-free** (`-Wall -Wextra -Wundef`); ~2.4 KB flash, 6 B RAM.

**PCB** (KiCad 10 `kicad-cli`):
```sh
kicad-cli sch erc --severity-all PCB/solar-glow-drh-v4_0.kicad_sch
kicad-cli pcb drc --refill-zones --schematic-parity --severity-all PCB/solar-glow-drh-v4_0.kicad_pcb
```
DRC/ERC are **not** expected to be zero — the intentional exceptions are catalogued
in `README.md` and filtered in `PCB/solar-glow-drh.kibot.yaml`. Every real DRC error
should be `(excluded)` and map to that list; a *new* unexcluded error is a real find.

**Consistency** (drift guard — also runs in CI):
```sh
python3 scripts/check_consistency.py
```
Verifies `board.h` pin map ↔ schematic netlist, CI-generated BOM ↔ netlist, and that
every `.kicad_*` file referenced in the docs exists.

## CI
- `kibot.yml` — regenerates `Generated/` (fab + docs) on `PCB/**` changes and commits
  it back as `kibot-ci`. **Do not hand-edit or commit `Generated/` yourself — CI owns it.**
- `firmware.yml` — builds the firmware on `firmware/**` changes, uploads the hex.
- `consistency.yml` — runs the drift guard on doc/board/firmware changes.

## Gotchas
- **The energy budget is the #1 open gate** — harvest vs. LED draw under real indoor
  light has never been measured. Treat firmware duty-cycle / glow constants as
  provisional until it is. See README → "The open question."
- **SW2** (LED master switch) is pure hardware; firmware can't sense it. Board dark? Check SW2 first.
- The **accelerometer is the only actuator** (no button by design; to add one later: pin 3 / PA5 -> momentary switch -> GND, active-low).
- LED PWM **`INVEN` polarity in `led.c` is load-bearing** for the dark idle state — don't
  remove it to "fix" an apparent inversion (write `255 - duty` instead).
- Don't commit firmware build artifacts (`firmware/*.o|*.elf|*.hex` — gitignored).

## Working style here
This project values **precision over speed**: verify a datasheet/geometry claim against
its source before asserting it, and when something changes, update the single
source-of-truth file — the consistency check is the automated backstop, not a substitute.
