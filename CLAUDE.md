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
- Back-shell medallion (ring text, monogram, serial) → `enclosure/medallion.py`
- Firmware pin map + tunables → `firmware/board.h` and `firmware/README.md`
- BOM → **there is no hand-authored BOM.** Both `*-BOM.xlsx` masters were culled 2026-08-02 and
  live in git history; every line is now derived from the schematic + the board's own flags.
  `BOM/README.md` is the **live availability table** written by `BOM/check_stock.py` (manual-apply
  like the mask art, since it needs distributor API keys; regenerate it, never edit it), and it
  reads its line items from `scripts/bom_split.py` rather than from a sheet
- **The two BUY documents are GENERATED, not maintained** → `scripts/bom_split.py` writes them
  into `Generated/fabdocs/` on every board push: `…-pcbway-assembly.csv` (what the machine buys
  and places) and `…-handbuy-{digikey,mouser}.csv` + `…-handbuy.md` (what **you** buy — the
  hand-soldered supercaps and cells, plus the ferrite, screws, film, UPDI Friend and
  Tag-Connect cable that never reach a pick-and-place). A part moves between the two by
  changing the **design** — the board's own `exclude_from_bom` / `dnp` flags decide — never by
  editing a list. The one hand-maintained input is `OFF_BOARD` in that script, for items with
  no schematic symbol. Check [15] gates the split. **The four supercaps are two MPNs, 2 + 2**
  (SC1/SC3 `3-153-440`, SC2/SC4 `3-153-438`); four of either builds nothing.
- Design reasoning / lineage → `solar-glow-drh-design-notes.md`

When a doc disagrees with a source file, **the source file wins** and the doc is
what gets corrected. The `*-v2-*.md` docs are v2-era history (banner-marked at the
top) — read them for lineage, not for current values.

## Build & verify
**Firmware** (needs a modern `avr-gcc` + the **AVR-Ex** DFP — the EA lives in AVR-Ex_DFP,
NOT AVR-Dx (this paragraph said Dx until the 2026-08-01 sift — pre-EA-port text; firmware.yml
had it right all along); install per `firmware/README.md`):
```sh
make -C firmware DFP=/path/to/Microchip/AVR-Ex_DFP      # -> firmware/solar-glow.hex
```
Should compile **warning-free** (`-Wall -Wextra -Wundef` — a GATE in CI, which builds with
`WERROR=1`); size/RAM figures live in `firmware/README.md` — the "~2.4 KB flash, 6 B RAM"
that used to sit here had quietly gone stale against the EA port's figures, which is why the
numbers now have one home, and since 2026-08-01 that home is GATED: `scripts/check_fw_size.py`
fails the firmware build if the README figure stops matching the ELF.

**PCB** (KiCad 10 `kicad-cli`):
```sh
kicad-cli sch erc --severity-all PCB/solar-glow-drh-v4_0.kicad_sch
kicad-cli pcb drc --refill-zones --schematic-parity --severity-all PCB/solar-glow-drh-v4_0.kicad_pcb
```
DRC/ERC are **not** expected to be zero — the intentional exceptions are catalogued
in `README.md` and filtered in `PCB/solar-glow-drh.kibot.yaml`. Every real DRC error
should be `(excluded)` and map to that list; a *new* unexcluded error is a real find.

**Front mask art** (every opening is computed as `shape − live copper`, so it tracks the routing):
```sh
python3 scripts/mask_art.py --check     # does the board match the current routing?
python3 scripts/mask_art.py --apply     # regenerate after ANY front re-route
```
Today it writes two things: the NFC contactless mark (F.Mask) and, since 2026-08-02, the
**selective hard-gold plating area on `User.1`** — the PCB/README net rule drawn as artwork, so
it plots into both fab sets and cannot drift against the routing. The left-field **cartouche is
off** (`CARTOUCHE = False` in that file, since 2026-07-29) — generator intact, one constant
brings it back; the reason it is off is in the comment above the switch.

**Component colours** (the one part of a render that is data, not decoration):
```sh
python3 scripts/part_colors.py --check    # do the STEP bodies match the table?
python3 scripts/part_colors.py --apply    # write the table into them
```
Colour patch only — never geometry, so check [7] stays an independent measurement of height.

**Generated solids** (the STEP/STL that go to fabrication):
```sh
python3 scripts/check_mesh.py          # STL validity + volume/bbox ledger (needs trimesh)
```
```sh
python3 scripts/interference_drc.py    # 3D interference DRC: brace STL ray-cast vs every B-side body
```
STEP validity is gated at export time — OCC `BRepCheck` inside `fit_rules.export_step_stable`,
the one choke point all three CAD generators use. The mesh gate also runs in `kibot.yml`
**before** the commit-back, so a cadquery/OCC bump that breaks a tessellation fails the job
instead of landing. The shell STL carries one ledgered zero-length rim pinch; a real hole
(nonzero open length) goes red. Triangle count is deliberately ungated — it is not bit-stable.

**NFC coil paper tune** (the antenna's L and resonance are re-derived from the routing —
the one subsystem neither external reviewer can see as a designed object):
```sh
python3 scripts/nfc_coil.py --check     # geometry, L (two formulas), bare f0 vs the C9 ladder
```
Outputs are **bare-copper units**: the ferrite sheet raises L ~1.3–1.5×, pulling the physical
tank toward 13.56 MHz — load-bearing for tune, not just shielding. Check [13] gates the
geometry (a re-route that loses a turn or severs the spiral goes red); the C9 ladder and the
bench own the real number.

**Consistency** (drift guard — also runs in CI):
```sh
python3 scripts/check_consistency.py
```
Verifies `board.h` pin map ↔ schematic netlist, CI-generated BOM ↔ netlist, that every
`.kicad_*` file referenced in the docs exists, that **every image any `.md` displays comes
from a generator CI runs** (check [9]), that every 3D model carries its table colour
(check [10]), and that **every file path any `.md` cites exists — or the citing sentence
itself says why it does not** (check [11], 2026-08-01: a history marker like "culled"/"git
history" in the sentence, or a reasoned entry in the check's `EXPECTED_ABSENT` list; born
from a night that found four silently-dead citations check [9] could not see, since it
guards only displayed images), and that **no footprint has changed sides** against the
`FRONT_SIDE` snapshot (check [12], 2026-08-01 — closing TODO's named tooling gap: DRC, parity
and check [1] are all side-blind, and a B-side flip silently deletes that part's brace pocket;
a deliberate move updates the snapshot in the same commit, the exclusion-ledger shape), and that
**every opening in the `User.1` plating drawing actually has copper under it, and the fab
request's hand-written gold-set enumeration still matches the board** (check [14], 2026-08-02).
That last one closes a gap class that produced two wrong fab instructions in a week — the request
said *four* M2 annuli when the board has eight, and listed the contactless arcs as gold when they
have no copper at all — because a human list of the gold set sat next to a generated drawing of it
with no gate between. It found a third case on its first run: the D/R/H letter apertures plate
nothing either (bare FR4 *is* the backlight), so they are now a reasoned exception rather than an
unnoticed one. Both exceptions are recognised **by construction** (inside `mask_art`'s own mark, or
inside the `optical_window` keepout), never by coordinates. And **check [15]** holds the other
fab-file pair together: nothing may reach the assembler's pick-and-place without a BOM line to
buy it. It was written after the pre-order sweep found SC1–4, PV1–2, MH1–4 and TC1 excluded from
the BOM but *not* from the position file — a CPL that named ten parts the assembler had never
been sold. Check [2] is the same relationship in the one direction that happened to be guarded.

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
  new imagery, with no human step. ~6.7 min of CAD on top of the ~12 min raytrace (the CAD was
  ~40 s until the medallion graduated 2026-07-31 — its boolean work dominates the step now;
  measured 6 m 42 s on the 2026-08-01 run).
  **Everything it writes outside `Generated/` is just as CI-owned** — the STEP/STL, both drawings,
  the six renders — despite living beside the hand-maintained enclosure sources. Run any of them
  locally to check a change, but don't commit the result: VTK's pixels differ across GL stacks and
  a hand-run render churns against CI's forever. The commit-back globs these by *kind*, so a new
  variant out of a generator is picked up without editing the workflow.
  Triggers are `PCB/**` **minus `PCB/**.md`**, `scripts/panelize.py`, `scripts/render.py`,
  `scripts/ref_figures.py` (the board reference figures — LED polarity, SW2 bridge — drawn from
  the board into `Generated/docs/`), the
  generators' own non-board inputs (`enclosure/assembly_render.py`, `fit_rules.py`,
  `board_parts.py`, `medallion.py`, `part_heights.py` — the last missing until 2026-08-01,
  the #132 gap class again — and `enclosure/**.stl`) **and, since 2026-07-31, the CAD/drawing
  generators themselves** (shell, brace, both DRAWING-gens — before that, a generator-only edit
  regenerated nothing, and PR #129 only rebuilt because `fit_rules.py` shared the diff) and the
  workflow itself — **not** all of `scripts/` or all of `enclosure/`, so editing an unrelated
  script or doc regenerates nothing. The `.md` exclusion
  is new on 2026-07-30 and this sentence was false without it: `PCB/README.md` is prose that lives
  beside the board, `PCB/**` matched it, and merging a docs-only PR ran the full ~16 min pipeline
  and committed 49 files of plot timestamps and one more roll of the raytracer.
  **The one link that is deliberately manual is `mask_art.py`.** It rewrites the *board file*, so
  auto-applying it in CI would have the job editing a source of truth — and a `.kicad_pcb` whose
  line endings alternate between saves. It stays a guard (check [6]): re-route the front, run
  `--apply` yourself, push, and everything downstream regenerates from there.
- `firmware.yml` — builds the firmware on `firmware/**` changes (warning-free is a GATE:
  CI passes `WERROR=1`), uploads the hex, and gates the README's measured size figures
  against the build (`scripts/check_fw_size.py` — a size-changing edit lands with its
  README figure update in the same commit, or fails).
- `weekly-freshness.yml` — the Monday canary + drift report. Pins have two failure modes
  push-CI can't see: **rot** (the pinned artifact stops being fetchable) and **drift**
  (upstream moves on). Weekly, pushes or not: re-fetches the pinned toolchain/DFP and
  builds warning-free, pulls the pinned KiCad image and runs the consistency suite on the
  unchanged tree, then sweeps upstream (KiCad `:latest` digest, the AVR-Ex pack index,
  PyPI for every `pkg==ver` pin it finds in the workflows, latest release tags for pinned
  action SHAs) and upserts one standing issue, "Weekly freshness report". **Nothing moves
  a pin automatically** — rot fails the job red, drift is report-only; the deliberate
  bridge is dispatching it with `bump_kicad=true`, which opens a DRAFT PR moving the KiCad
  digest in all three workflows together, and the merge run's `Generated/` diff is the
  upgrade's blast radius, per the pinning doctrine below.
- `consistency.yml` — runs the drift guard on doc/board/firmware changes, plus
  `scripts/mask_art.py` (check [6] regenerates the mask art through it), `scripts/part_colors.py`
  (check [10]), `kibot.yml` (check [9] parses its `OUTS` list) and `enclosure/**`
  (check [7] reads the part-height table). Until 2026-07-29 **nothing in CI triggered on
  `enclosure/` at all**, which is how a stale U7 height survived there for a day; and it
  triggered on `README.md` **by name** until 2026-07-30, so check [9] — which reads every
  `.md` in the tree — could not have fired on an image added to `PCB/README.md` or
  `enclosure/README.md`. It is `'**.md'` now.
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
- **Every image a doc displays must come from a generator, and check [9] enforces it.** Add
  a `![](…)` to any `.md` and the check fails unless some entry in `PRODUCERS` claims the path
  *and* `kibot.yml`'s own `OUTS` list actually commits it — a producer whose output CI throws
  away is not automation. The eight analysis figures in `images/` are the standing exception,
  each with its reason in `UNAUTOMATED`; they plot data that is not in the repo, so a
  "generator" for them would just hard-code numbers read off a PNG.
- **An uncoloured 3D model renders default grey, and no other check notices.** `LA_P47F` — the
  amber LED, ×4, the component this card exists to drive — carried no STEP colour entity at all
  and shipped as a grey block in every assembled render for months. Check [5] counts models that
  *resolve*, and an uncoloured model resolves perfectly. Colours live once, in
  `scripts/part_colors.py`; check [10] gates them, and a new model with no entry is an error.
- **A `dnp` part's model resolves too — and is still not drawn.** Same blind spot, opposite cause:
  the body is absent from every populated render *correctly*, because the assembled board will not
  have the part, but "resolved and drawn" and "resolved and deliberately absent" look identical —
  an empty land. The class is currently EMPTY on this board (2026-08-01 sift: 16 `dnp`
  footprints — TC1, TC1/b1, SW2, J1, JP1, SB1–4, TP1–7 — and none carries a model), but it was
  not always: **C9** was the dnp-with-a-model until it was placed at 47 pF on 2026-07-30, and
  confirming its 0402→0805 upsize had landed meant re-rendering with `dnp` cleared and diffing:
  528 px, 20×37, an 0805 turned 90°. `render.py` names the DNP set beside the resolve count so
  the next dnp-with-a-model is visible the day it appears.
- **The front mask art is generated from the routing.** Every opening is `shape − live copper`,
  so moving a front trace can put a signal under an aperture — re-run `scripts/mask_art.py
  --apply`. Consistency check [6] errors if you forget. It is the one artwork here that goes
  *wrong*, not merely stale, when the board is edited. (The left-field cartouche this rule was
  written for is now off; the NFC mark it still writes obeys exactly the same rule.)
- **`solder_mask_bridge` DRC was `ignore` until 2026-07-28** and is now `warning`. Everything
  it reports is the single rear glow-window aperture at (35.1, 40.3) spanning the LED nets —
  intentional, nothing is soldered there.
  **Zero come from F.Mask**, so the front art is clean. A *new* F.Mask hit is a real find.
  **Do not treat the hit COUNT as a constant, and never gate on it.** It is not deterministic:
  two runs on byte-identical inputs (same board, `.kicad_pro`, `.kicad_dru` and the same pinned
  image digest) reported **222** and **208**, and a third after the coil landed reported 223
  and 222 again after the coil aperture was reverted. The published runs since have read **223,
  200, 203**, so the observed spread is now **200–223** — a range of 23 on a board whose mask art
  did not move. KiCad pairs that aperture against the copper
  items near it, and the set it finds varies run to run — most likely because `check_zone_fills` refills the pours first
  and the fill is not bit-reproducible. What IS stable, and what to assert if this ever gets a
  gate: `Errors: 0 (+11 excluded)`, zero hits on F.Mask, and every hit citing that one aperture.
  _(Was `+11` until 2026-07-30, `+10` until 2026-08-01. The old 11th was a `courtyards_overlap`
  exclusion the 2026-07-30 board sync made dead, and KiCad pruned it; the new 11th is another
  `courtyards_overlap` — `TC1/b1` (né `TC1/b`; the 2026-08-01 GUI session re-annotated it, and the
  exclusion survived because KiCad keys exclusions by UUID, not refdes), the B-side programming
  mirror added 2026-08-01, sits inside SC1's courtyard by design (bare pads under a part body,
  nothing fitted while programming). The `extra_footprint` parity exclusion added in the same GUI
  session was deliberately NOT kept — the schematic gained a real `TC1/b1` symbol instead, so a
  future sync that loses it goes red rather than silent. The list is 14 → 11 errors plus 5
  `silk_over_copper` warnings (was 3; two new hits arrived with the same GUI session — one B-silk
  segment at (22.93, 48.62) clipping both C13 pads. Cosmetic, ledgered 2026-08-01). Verify the
  number against `Generated/solar-glow-drh-v4_0-drc.html`, which CI writes, rather than trusting
  this line.)_
- **`mask_art.py`'s `generate()` is the single definition of what it writes** — and
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
