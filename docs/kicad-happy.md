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

**Still open to adopt:** the `emc` skill (EMC pre-compliance pass — this board has a 13.56 MHz
coil, a ≥10 MHz DCDC, and LED PWM, and has never had an EMC review; TODO carries the item).

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
- SC1 ↔ TC1/b courtyard overlap (10.52 mm²) — the ledgered DRC exclusion: bare programming pads
  under the supercap body, nothing fitted while programming.
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
