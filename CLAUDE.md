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
**final unmanaged-solar revision**; its files were removed from `PCB/` on 2026-07-28 and
live in git history only — see `PCB/README.md` for how to get one back. The v4 rework is
specified in the v4 addendum of `solar-glow-drh-design-notes.md` and the net/pin plan
`v4-aem10300-prewiring.md`; the `v4_0` files started as a copy of `v3_0` and have been
reworked from there. **`PCB/` holds exactly one board revision — do not add another.**

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

**Front mask ornament** (the left-field cartouche IS the routing, in negative):
```sh
python3 scripts/mask_art.py --check     # does the board match the current routing?
python3 scripts/mask_art.py --apply     # regenerate after ANY front re-route
```

**Consistency** (drift guard — also runs in CI):
```sh
python3 scripts/check_consistency.py
```
Verifies `board.h` pin map ↔ schematic netlist, CI-generated BOM ↔ netlist, and that
every `.kicad_*` file referenced in the docs exists.

## CI
- `kibot.yml` — regenerates `Generated/` (fab + docs) on `PCB/**` changes and commits
  it back as `kibot-ci`. **Do not hand-edit or commit `Generated/` yourself — CI owns it.**
  The same job also rebuilds the **PCBWay panel** via `scripts/panelize.py` and plots its
  fab set into `Generated/panel/`. The panel is derived from the board, never edited —
  see `PCB/README.md` → "The PCBWay panel".
  It then raytraces the README images via `scripts/render.py` (panel front/back, the depanelised
  card, the **assembled/populated** views, and the OSH Park midnight variant) into `Generated/docs/`.
  It costs **~12 min** across 14 views (the populated target added 3, ~2.5 min). If that ever
  needs trimming, `--quality basic --floor` keeps most of the look for roughly half the time.
  **It then rebuilds the whole enclosure chain**, in dependency order, because every link of it
  is a function of the board: the two CAD generators (brace + back-shell → STEP/STL), both
  dimensioned drawings (→ PDF/PNG), then `enclosure/assembly_render.py`, which loads those very
  STLs *and* textures the card with the card-face plot the raytrace just wrote. Order is
  load-bearing — render before the CAD and you photograph the previous enclosure onto the current
  board. One job produces all of it, in one commit, so no two artifacts can be a revision apart.
  Moving a part on the PCB therefore lands as: new gerbers → new brace and shell → new drawings →
  new imagery, with no human step. ~40 s of CAD on top of the ~12 min raytrace.
  **Everything it writes outside `Generated/` is just as CI-owned** — the STEP/STL, both drawings,
  the six renders — despite living beside the hand-maintained enclosure sources. Run any of them
  locally to check a change, but don't commit the result: VTK's pixels differ across GL stacks and
  a hand-run render churns against CI's forever. The commit-back globs these by *kind*, so a new
  variant out of a generator is picked up without editing the workflow.
  Triggers are `PCB/**`, `scripts/panelize.py`, `scripts/render.py`, the generators' own non-board
  inputs (`enclosure/assembly_render.py`, `fit_rules.py`, `board_parts.py`, `enclosure/**.stl`)
  and the workflow itself — **not** all of `scripts/` or all of `enclosure/`, so editing an
  unrelated script or doc regenerates nothing.
  **The one link that is deliberately manual is `mask_art.py`.** It rewrites the *board file*, so
  auto-applying it in CI would have the job editing a source of truth — and a `.kicad_pcb` whose
  line endings alternate between saves. It stays a guard (check [6]): re-route the front, run
  `--apply` yourself, push, and everything downstream regenerates from there.
- `firmware.yml` — builds the firmware on `firmware/**` changes, uploads the hex.
- `consistency.yml` — runs the drift guard on doc/board/firmware changes, plus
  `scripts/mask_art.py` (check [6] regenerates the cartouche through it) and `enclosure/**`
  (check [7] reads the part-height table). Until 2026-07-29 **nothing in CI triggered on
  `enclosure/` at all**, which is how a stale U7 height survived there for a day.
- **Everything CI runs is pinned.** The KiCad 10 image is pinned by *digest* in both
  `kibot.yml` and `consistency.yml` (keep the two in step), every action by commit SHA,
  shapely and the AVR toolchain/DFP by version. This is not hygiene: DRC is a merge gate
  and `Generated/` is the gerber set that goes to a fab, and the upstream image is a KiCad
  **testing** build. Bumping the digest is a deliberate commit whose `Generated/` diff is
  the upgrade's blast radius. That is also why `kibot.yml` calls the container directly
  instead of `uses: INTI-CMNB/KiBot@v2_k10` — that action's Dockerfile is `FROM
  …kicad10_auto_full:latest` with no version input, so pinning the action would pin the
  wrapper and leave KiCad floating.

## Gotchas
- **Component heights live in `enclosure/part_heights.py`, once.** Every enclosure pocket depth
  is a function of them, and a wrong one prints an unusable part rather than failing: U7 kept a
  removed SOIC-8's 1.75 and the brace cut it clean *through*; Q2/FB1/the 0603-0805 caps fell
  through a silent default and were cut up to 0.58 mm too shallow. Never re-declare a height in a
  generator or a drawing — import it. Check [7] measures each one against that part's own 3D model,
  and `part_height()` **raises** on an unmapped refdes instead of guessing.
- **The front cartouche is generated from the routing.** Move a front trace and the
  ornament no longer describes the copper under it — re-run `scripts/mask_art.py --apply`.
  Consistency check [6] errors if you forget. It is the one artwork here that goes *wrong*,
  not merely stale, when the board is edited.
- **`solder_mask_bridge` DRC was `ignore` until 2026-07-28** and is now `warning`. Everything
  it reports is the single rear glow-window aperture at (35.1, 40.3) spanning the LED nets —
  intentional, nothing is soldered there.
  **Zero come from F.Mask**, so the front art is clean. A *new* F.Mask hit is a real find.
  **Do not treat the hit COUNT as a constant, and never gate on it.** It is not deterministic:
  two runs on byte-identical inputs (same board, `.kicad_pro`, `.kicad_dru` and the same pinned
  image digest) reported **222** and **208**, and a third after the coil landed reported 223
  and 222 again after the coil aperture was reverted. KiCad pairs that aperture against the copper
  items near it, and the set it finds varies run to run — most likely because `check_zone_fills` refills the pours first
  and the fill is not bit-reproducible. What IS stable, and what to assert if this ever gets a
  gate: `Errors: 0 (+11 excluded)`, zero hits on F.Mask, and every hit citing that one aperture.
- **`mask_art.py` owns more than the cartouche** — it also draws the NFC contactless mark — and
  `generate()` is the single definition of what it writes. Check [6] calls that same function.
  It used to rebuild `emit(build(board))` itself, which was a quieter second copy: correct while
  the generator owned one thing, and it declared a correct board STALE the moment a second art
  set appeared, while the generator's own `--check` said MATCH.
- **Do not open soldermask over the NFC coil.** It was tried on 2026-07-29 and reverted the same
  day. Exposed copper gets ENIG, and nickel is the wrong thing in an RF conductor: ~7x copper's
  resistivity, ferromagnetic, and at 13.56 MHz its skin depth (~3-4 µm) is *thinner* than the
  plated layer (3-6 µm), so current crowding into the surface crowds into nickel and the coil
  loses Q. It buys nothing visually either: the shell is back-only, so the entire rear of the
  board is inside titanium and never seen. Soldermask is non-magnetic — removing it never helped
  the ferrite, whose shielding scales with µ′ × thickness.
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
