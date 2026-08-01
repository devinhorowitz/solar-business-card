# ThomsonLint — the ontology-guided second reviewer

**What it is:** [holla2040/ThomsonLint](https://github.com/holla2040/ThomsonLint) — an AI
hardware-design-review *framework*: a deterministic KiCad exporter (`tools/kicad-export.py`,
KiCad 9/10), a 172-rule ontology (`ontology/ontology.json` — Power, Analog, EMC, Thermal,
Mechanical, Component, Schematic, Production, and a 41-rule DFT battery), and a review contract
(`docs/REVIEWER_INSTRUCTIONS.md`) executed by an AI reviewer. The outputs are gated
deterministically: a findings JSON checked by `tools/validate_findings.py` (schema + **citation
coverage** — every input file consumed must be cited in evidence, or the review fails) and a
self-contained HTML triage report from `tools/gen_report.py`. Evaluated 2026-08-01 at commit
`df6bbf9f73972a07eca94422cfbd817dead04b2e` — **pin that SHA when running; a floating clone is an
unpinned toolchain.**

## How it complements kicad-happy

The two reviewers split the work at exactly the line this repo already draws:

| | kicad-happy | ThomsonLint |
|---|---|---|
| Extraction | deterministic Python analyzers | deterministic exporter |
| Findings | computed by the tool | reasoned by the AI reviewer against the ontology |
| Gate | our triage doc diffs future runs | citation-coverage validator + findings schema |
| Blind spot covered | geometry/topology measurements | ontology breadth: derating, DFT, sourcing, production readiness |

Both run **on demand, out of repo, pinned** — clone to scratch, run, read, and the *triage
record* (this file) is what the repo keeps. The review artifacts (exports, findings JSON, HTML
report) are regenerated on demand, never committed.

## Run recipe

```sh
git clone https://github.com/holla2040/ThomsonLint /tmp/ThomsonLint \
  && git -C /tmp/ThomsonLint checkout df6bbf9f73972a07eca94422cfbd817dead04b2e
python3 /tmp/ThomsonLint/tools/kicad-export.py <repo>/PCB/solar-glow-drh-v4_0.kicad_pro \
  --output /tmp/tl-exports
cp <repo>/datasheets/*.pdf /tmp/tl-exports/   # the validator gates citations against exports/
# ...the AI reviewer follows docs/REVIEWER_INSTRUCTIONS.md against the ontology, writes
#    /tmp/tl-exports/<project>-findings.json, then:
python3 /tmp/ThomsonLint/tools/validate_findings.py /tmp/tl-exports/solar-glow-drh-v4_0-findings.json
python3 /tmp/ThomsonLint/tools/gen_report.py /tmp/tl-exports/solar-glow-drh-v4_0-findings.json --output /tmp/tl-exports/
```

Copying `datasheets/` into the exports dir is deliberate: the coverage validator then *requires*
every part's datasheet to be cited in evidence — which turns this repo's curated datasheet set
into a hard completeness gate on the review.

**Not adopted:** the Fusion Electronics / EAGLE ULP path (we are KiCad), and vendoring its
skills — the same rule as kicad-happy.

## First review — 2026-08-01 (validator: PASS, 19/19 inputs cited, 41/172 rules)

Exporter agreed with the tree on everything it measures (73/78 components, 59 nets, 119 vias,
50.8 × 88.9 mm), and its own analysis found **0 floating inputs** and only *named* no-connect
single-pin nets. The 131 uncited ontology rules are N/A domains for this board: DDR/SerDes/
crystal (no crystal exists — internal oscillator), aerospace, 4+ layer stackups, relays, forced
cooling.

**Issues (6) — 2 already tracked, 2 genuinely new, 2 known-and-accepted:**

| Severity | Rule | Finding | Status |
|---|---|---|---|
| Major | PROD_ENV_001 | Energy budget never measured under real indoor light | The repo's own #1 open gate, restated through their lens — bench fixture exists, run it |
| Minor | COMP_RES_003 | R1–R4 at ~110% of rating at the worst corner | Already ledgered in TODO with the firmware duty-clamp guard named |
| Advisory | COMP_CAP_004 | **NEW nuance:** worst-case tank sits at the cells' 5.5 V rating; the AEM10300's *actual* enforced ceiling and MID balance are unmeasured | Added to the bench list: log STO + MID across full charge cycles |
| Advisory | PROD_SOURCE_001 | Six sole-source anchors (AEM10300, NT3H2211, ADXL367, LA P47F, SM141K06TF, tank cells) | Known posture, now stated plainly; live BOM gate + documented subs are the mitigation |
| Advisory | DFM_LABEL_001 | **NEW, fixed same day:** the bare card carried no revision ID — five functional pad labels and otherwise anonymous | `DRH v4.0` added on B.SilkS at (37.9, 75.4) — the documented former-NPTH spot under SC4's body; invisible assembled (the back lives inside the shell), readable at fab/assembly QA |
| Advisory | SCH_I2C_001 | I²C addresses live in `firmware/board.h`, not on the schematic sheet | Annotate at the next real schematic edit; not worth churning a verified sheet alone |

**Verified checks (21) and cross-checks (4):** the review's second deliverable is consolidation —
the session audit trail (passives derating, protocol audits, firmware pressure test, EMC pass,
stitching integration, enclosure chain, DFT posture) rolled into one citation-gated artifact:
per-IC decoupling distances, Q2's defined gate state, INVEN dark-idle, the planar AEM hot loop
(LX nets carry zero vias), MPP 80% strapping, NFC chain end-to-end (tune, ferrite, integrated
ESD, FD budget), thermal reality (mW-class, TIM-coupled shell), test access (TP1–TP7 = SRC, VS,
MID, LX_LOUT, VINT, BUFSRC, STO_LDO; SDA/SCL on silk-labeled straps; TC1 GND pad as scope
ground), and the CI gates as DFT_DRC_002/DFT_CONN_001 compliance.

**A future ThomsonLint run diffs against this table — a finding not on it is a real find.**

## The shared blind spot, closed — 2026-08-01

Neither reviewer has any provision for an **intentional antenna**: kicad-happy's geometry
checks report the coil as a plane-gap defect and a keepout violation (triaged as the tool
measuring an antenna and calling it one), and this ontology's three "antenna" mentions are all
`antenna_effect` failure-mode tags — unintentional-radiator language. The coil was the one
subsystem no tool could check. `scripts/nfc_coil.py` now closes the paper half in-repo:
deterministic geometry extraction from the routing (6.5 turns, run-pairing + winding-angle
cross-check), two independent inductance formulas agreeing to 3% (~1.09 µH bare), the
resonance table across the C9 ladder (bare 15.47 MHz at the placed 47 pF — the ferrite's
~1.3–1.5× L pulls the physical tank to ≈13.56, which is why the ferrite is load-bearing for
*tune*), and consistency check [13] gates it on every board edit. The bench reader-coupling
TODO still owns the measured half.
