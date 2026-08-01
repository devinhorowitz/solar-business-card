# kicad-happy — the external second-opinion analyzer

**What it is:** [aklofas/kicad-happy](https://github.com/aklofas/kicad-happy) (MIT) — deterministic
Python extractors that parse `.kicad_sch` / `.kicad_pcb` into auditable JSON (net graph by
union-find, power domains, subcircuit/divider detection, keepout occupancy, DFM measurements,
thermal-via and fiducial audits), packaged as agent skills plus a GitHub Action. The philosophy is
this repo's own: deterministic data extraction, reasoning layered on top, every finding carrying
its evidence. Evaluated 2026-08-01 at commit `c6b504ac91f18c24ee909ded4c00f409f07dcbff`
(2026-07-24) — **pin that SHA when running; a floating clone is an unpinned toolchain.**

## How we use it

**On demand, out of repo** — the same rule as the engraving studies. Clone to a scratch area,
run the two analyzers, read the JSON. It is a *review instrument*, not a pipeline stage:

```sh
git clone https://github.com/aklofas/kicad-happy /tmp/kicad-happy \
  && git -C /tmp/kicad-happy checkout c6b504ac91f18c24ee909ded4c00f409f07dcbff
cd /tmp/kicad-happy/skills/kicad/scripts
python3 analyze_schematic.py <repo>/PCB/solar-glow-drh-v4_0.kicad_sch > /tmp/happy-sch.json
python3 analyze_pcb.py       <repo>/PCB/solar-glow-drh-v4_0.kicad_pcb > /tmp/happy-pcb.json
```

Both analyzers parse the KiCad 10 files clean (stdlib Python, seconds, no network). The JSON is
the deliverable; the `skills/` directory also works as Claude Code skills if installed per its
`install-guidance.md`.

**What we deliberately do NOT adopt:**
- **The GitHub Action** (LLM PR review): a nondeterministic reviewer conflicts with this repo's
  CI doctrine — every merge gate here is pinned and reproducible. Advisory-only value doesn't
  justify an API-key secret in CI. Re-visit if that calculus changes.
- **Its BOM / distributor / datasheet skills**: this repo's own tooling is deeper for this board
  (`BOM/check_stock.py` is live-queried with documented substitutes; `datasheets/` is curated and
  named by refdes; the BOM master carries per-row provenance).
- **Vendoring `skills/` into the tree**: a pinned out-of-repo clone gives the same result without
  carrying a second project.

**Adopted on demand (2026-08-01):** the `emc` skill and the rest of the cross-tool battery —
see "Deep analysis" below for the full-battery recipe and the triaged results. The measured
half of the EMC item (first-article numbers) stays in TODO.

## Baseline triage — 2026-08-01 run against the v4 board

100 findings (24 schematic / 76 PCB). Everything at `error`/`warning`, triaged so the next run
diffs against a known baseline (the exclusion-ledger shape). **A future finding not on this list
is a real find.**

**Real find, actioned (TODO):**
- `analyze_fiducials`: **no fiducials on the board — and none on the PCBWay panel either**
  (verified against `scripts/panelize.py`: tooling holes only). 47 machine-placed parts including
  two 0.4 mm-pitch QFNs (U1, U8) with no optical registration marks. Panel-rail fiducials are the
  fix; TODO carries the derivation constraints.

**Known-intentional (matches this repo's own exclusion ledger / design intent):**
- D2–D5 centers inside `optical_window` / `KO_WIN_B` keepouts — the reverse-mount LEDs *live in*
  the glow window by design; the keepouts exist to keep copper/vias out, not the LEDs.
- SC1 ↔ TC1/b1 courtyard overlap (10.52 mm²) — the ledgered DRC exclusion: bare programming pads
  under the supercap body, nothing fitted while programming. (Named `TC1/b` when this baseline
  was taken; the 2026-08-01 GUI session re-annotated it to `TC1/b1`.)
- Via at (42.9, 38.0) inside the NFC coil keepouts — the coil's own crossover via; KiCad's zone
  settings permit it (DRC: 0 errors), the analyzer's bbox check is coarser.
- U9/C22, U9/FB1, U7/U3 courtyard grazes (≤0.014 mm²) — known, sub-threshold in KiCad.
- U1 EP 2 vias / U8 EP 0 vias "thermal" warnings — both parts mount on the B side, where the EP
  lands directly on the B.Cu ground pour: lateral same-layer connection, no vias needed, and
  thermal load is milliwatt-class.
- C22/FB1 ~0.95 mm from the east board edge — the known tight east lip; the panel rails carry the
  board through depanel.
- Test-point coverage 13% — the TP set is deliberate and the pogo plate covers bring-up.

**Quality spot-checks that passed:** power-domain extraction is exactly right (U6 straddling
VNFC/VS, U5 on the gated rail, U3's VREG_OUT domain, everything else on VS);
`passive_warnings: 0` agrees with the 2026-07-30 passives audit.

## Deep analysis — 2026-08-01 (the full battery)

Second pass, same pinned clone: every tool in `skills/kicad/scripts` plus the `emc` skill, run
against the v4 board and the CI-owned gerbers. Two plumbing lessons the README above doesn't
mention, learned the hard way:

- **The cross-tools consume the analyzers' JSON, not the KiCad files.** `cross_analysis.py`,
  `cross_verify.py`, `analyze_emc.py` etc. take `schematic.json` / `pcb.json` as input; feeding
  them a `.kicad_*` file is a JSONDecodeError.
- **Outputs land in a timestamped `--analysis-dir` subdir** (this run: `2026-08-01_2000/`),
  not wherever `--output` points. Point later tools at that cache.
- The EMC skill has two depths: with the basic `pcb.json` it scores geometry-lite (this board:
  **91.0/100**, 8 findings); with `analyze_pcb.py --full` output it adds reference-plane and
  return-path tracing (**risk score 64.0**, 37 findings: 4 error / 27 warning / 6 info). The
  full mode is the one worth running.

### Results by tool

| Tool | Result |
|---|---|
| `cross_analysis` | 1 info: MP1–MP4 in PCB but not schematic — the board-only mounting holes, expected |
| `cross_verify` | **73/73 footprints matched, 0 value mismatches** — an independent confirmation of consistency check [1]; its DNP-but-placed warnings are our deliberate no-fit class |
| `analyze_gerbers` (on `Generated/gerbers`) | **zero findings** |
| `analyze_thermal` | skipped itself: "No components had quantifiable power dissipation data" (wants its own datasheet cache). Fine — this board is milliwatt-class |
| DFM (in `--full`) | **0 violations**; measured min track 0.152 mm, min drill 0.3 mm |
| `analyze_emc` (full) | risk score 64.0 — every finding triaged below, **no new real board defect**, one respin-hygiene item extracted to TODO |

### EMC triage — the full-mode findings

The score drop (91 → 64) is the plane/return-path detectors meeting a board whose central
features are *deliberate copper voids*. Classified, with the board as evidence:

**GP-001 "reference plane gap" (4 error + 4 warning) — all by design.**
- `LA` at 6.9% coverage over 384.5 mm **is the NFC coil spiral**; `LB` (90.6%) is its return.
  The keepouts under the coil are deliberate on both layers — a reference plane under an
  antenna is a shorted transformer turn, and the 2026-07-29 mask experiment already documented
  why nothing conductive goes there. The tool is correctly measuring an antenna and calling it
  an antenna ("creating a loop antenna" — yes; it's load-modulated at 13.56 MHz by the
  reader's own field, the one net on the board that is *supposed* to radiate).
- `K3` (50%), `K4` (62.5%), `ANODE` (68.5%), `K2` (88.2%): the LED string. The four light
  paths are voided through both layers (the glow window / monogram — the product), and the
  cathode stubs cross them. K5, the fourth cathode, isn't flagged because its stub happens to
  sit over copper. These nets carry 3.9 kHz PWM through 150 R ballasts at mA scale.
- `VNFC` (83.7%), `STO_LDO` (88.9%): DC rails skirting the same voids, decoupled at their loads.

**RP-001 "missing stitching via at layer transition" (22 nets) — factually correct, and the
one genuine hygiene item.** Independently re-measured from the board file rather than trusting
the tool: 110 vias total, **28 GND stitching vias, 82 signal vias; only 2/82 have a GND via
within the tool's 1.0 mm radius** (24/82 within 2 mm, median nearest distance 2.75 mm, worst
19.25 mm — the `SRC` via at (46.5, 69.5)). So the report is true. What it lacks is spectrum:
the sharpest edges on this board — the AEM10300's ≥10 MHz switch nodes `LX_LIN`/`LX_LOUT` —
have **zero vias** (the hot loop never changes layers), I²C is ~100 kHz (`firmware/twi.h`),
LED PWM is 3.9 kHz, UPDI is bench-only, and everything else flagged is DC or quasi-static.
Add no cables (nothing conducted), harvest power, and a grounded Ti shell over the whole back,
and this is not a compliance risk for the product class. It IS cheap hygiene for the next
deliberate copper change: a handful of GND vias beside the worst clusters. TODO carries the
item with the measured worst offenders; the coil crossover via at (42.9, 38.0) — 10.9 mm from
the nearest GND via — is the one spot that must **stay** unstitched (it's inside the coil
keepout for a reason).

**GP-004 "low ground fill" (F.Cu 45%, B.Cu 38% + 41% — the pour reports as two zones):
architectural.** The monogram cut, the glow window, and the coil keepouts *are* the missing
fill. The recommendation ("reduce routing density") would delete the product.

**IO-001 (PV1/PV2, info):** no filter at the harvest inputs — the cells are board-mounted
(no cable, mm-scale leads) and the input is buffered on `BUFSRC` + the AEM10300 input caps.

**SU-001 (info):** "adjacent signal layers F.Cu/B.Cu" — it's a 2-layer card. Architectural.

**EE-001 (info):** shell cavity resonances ≥795 MHz. Nothing on board puts meaningful energy
within an order of magnitude of that (highest fundamentals: 13.56 MHz coil, ≥10 MHz DCDC).

### Schematic full-mode warnings (5) — all resolved against the design

- **PU-001 U1 PF6/RST "missing pull-up":** PF6 has no external net *by design* — RSTPINCFG=0
  makes it plain GPIO and `firmware/main.c` holds it with the internal pull-up
  (`PORTF.PIN6CTRL = PORT_PULLUPEN_bm`, with the comment saying exactly this).
- **PU-001 U8 VINT:** VINT is the AEM10300's *internal LDO output*, decoupled per datasheet —
  it's the rail other things pull up **to** (R17 1 M takes EN_STO_CH to VINT). The detector
  fires because the symbol declares the pin `passive`, so it can't see a driver.
- **PU-001 U8 STO_RDY:** a deliberately unread status output, left NC (the v4 prewiring
  picked which of the four status pins get pins on U1 — `docs/v4-aem10300-prewiring.md`).
  Same `passive`-pin root cause.
- **PU-001 U9 EN:** strapped to `STO_LDO` — "U9's IN and EN both sit on STO_LDO"
  (`solar-glow-drh-design-notes.md`), so the LDO tracks its own input rail. Deliberate.
- **RS-001 "VREG has no declared source":** VREG is U3's VREG_OUT with C11 220 nF — a mapping
  the suite itself gets right twice (its power-domain extractor names the domain; its PDN
  module models VREG/C11), but the rail-source auditor doesn't consume either.

**Declined:** retagging the symbol pin types (VINT/STO_RDY → power-out/open-drain) purely to
silence PU-001 — that edits a verified schematic and churns the ledgered ERC baseline for a
third-party heuristic. The 12 `label_shape_warnings` (mixed label glyphs, "input" labels on
passive-driven nets like the LX nodes) are cosmetic with zero electrical meaning — same call.

**Lifecycle (LC-006, 3 warnings):** BSS138LT1G 52-week, CL21B106KOQNNNG 30-week,
MCT0603MD2004BP500 40-week lead times. Complements rather than contradicts `BOM/README.md`
(the live stock view says all three are on the shelf **today**) — lead time bites
production-scale orders, stock-now covers onesies. Worth re-reading before any real
production run.

**Baseline statement:** with the 100 basic-mode findings above and the 37+5 full-mode findings
here triaged, a future run of the full battery diffs against a fully-classified baseline.
**Any finding not on these lists is a real find.**

## Integrated — 2026-08-01 (both actionable findings are now in the copper)

The user's same-day GUI edits opened the board, so both real finds rode along:

- **Nine GND stitching vias** (the RP-001 item), each landed on a hatch-stroke crossing of both
  GND lattices beside a worst-offender cluster: SRC (45.4, 70.14), VNFC (6.51, 9.17),
  CHG_DIS_G (44.07, 61.78), MID (39.29, 65.19), STO (11.89, 11.86), NFC_EN (3.28, 30.04),
  VSENSE (24.41, 37.41), SDA-side (40.97, 30.1), VS (1.67, 39.87). The coil crossover via
  stays unstitched, as specified.
- **Three panel fiducials** (the `analyze_fiducials` item): Ø 1.0 mm copper / Ø 2.0 mm mask,
  both faces, three corners of four on the rails' outer band — built into `scripts/panelize.py`
  with the clearance and 180°-asymmetry guards asserted in code, per the TODO derivation.

Two placement lessons, recorded because the *first* via placement drew 3 DRC errors:
- **Both GND pours are hatched** (0.2 mm strokes / 0.5 mm gaps — the card-face texture), so
  "inside the pour" is meaningless for a via: it must land ON a stroke crossing of both layers'
  lattices or it connects nothing.
- **Tracks cross the hatch corridors.** A placement model that only checks pour membership puts
  vias on top of tracks (first attempt: one clearance hit on SCL, one genuine GND–UPDI short).
  The full model checks every other-net track/pad/via on both layers; `kicad-cli pcb drc` is the
  ground truth that gates the result.

Verification after integration: DRC `Errors: 0 (+11 excluded)`, **zero F.Mask hits**, mask art
regenerated through `generate()` and `--check` = MATCH. After-census (37 GND vias): worst
nearest-GND-via distance fell **19.25 → 8.13 mm**, and the 8.13 IS the coil crossover; every
non-coil signal via is now within 5.1 mm (median 2.38, 80/82 within 5).
