# Supercap reflow index shim

A flat 316L plate that indexes SC1–SC4 while their paste is molten, then comes off.
**Generated, not drawn** — `../../scripts/reflow_shim.py` derives it from the board, and
`../../scripts/reflow_shim.py --dxf` writes `solar-glow-drh-reflow-shim.dxf` on every CI
run. Do not edit the DXF; change the board or the constants and regenerate.

## Why it exists

SC1–SC4 solder to **flat pads underneath the can**, so an iron cannot reach them: reflow
is mandatory, and the caps have to be held while the paste is liquid. Two options were
measured and rejected before this one:

- **A printed jig** does not survive hotplate temperature.
- **On-board index posts** do not fit. Of the sixteen cap edge-directions, exactly **one**
  (SC4 east, 5.14 mm) clears the 3.2 mm a 2512 needs; eleven are under 2.2 mm and six have
  no usable room at all. Posts remain a live idea, but they are a **v5 layout change** —
  see "What this does not do".

## What it is

| | |
|---|---|
| Material | 316L stainless, laser-cut, deburred both faces |
| Thickness | **0.60 mm** — must stay under `part_heights.SUPERCAP_H` (1.70) so it never stands proud of the caps |
| Outline | `fit_rules.brace_footprint(span=0.0)` — `span=0` makes **every** part a blocker, so the plate lands only on bare laminate |
| Cap clearance | **0.10 mm** — `SHIM_CLR`, **PROVISIONAL** (see below) |
| Area | 976.3 mm², one connected piece |
| Pad contact | **zero** across all 208 B-side pads |

Because the outline is the complement of the parts, the plate cannot rest on a component —
that is a property of how it is cut, not something checked afterwards.

## What it buys

Each cap ends up indexed on **two orthogonal sides**:

| cap | datum sides | coverage |
|---|---|---|
| SC1 | E + N | 95.0% / 60.0% |
| SC2 | W + N | 75.0% / 97.5% |
| SC3 | E + S | 97.5% / 75.0% |
| SC4 | W + S | 90.0% / 97.5% |

One long side at 75–97.5% is what matters: two-point contact along the length kills
**rotation**, which is the dominant placement error — 1° swings a 39 mm cap's corner
0.34 mm, and the four caps reach a real part at 2.02–6.71°. Contact **is** nominal, so the
paste's own self-centring pulls the same way the datum does rather than fighting it, and
the residual becomes one-sided.

It is also a **guard**. The four directions where a real part sits inside the brace bay —
SC4→L2 0.50 mm, SC3→R15 0.57, SC2→C6 0.65, SC1→C11 0.70 (`scripts/cap_clearance.py`) — are
all indexed sides, and the plate is nearer the cap than the part is. Steel stands between
the cap and the component it would otherwise shear. This is not luck: metal exists where a
neighbour is close precisely because the plate is the parts' complement.

## What this does not do

**It is removed after reflow, so it gives no field restraint.** The edge-drop case still
loads the brace, and in those four directions a component (see `fit_rules.CLR_EXCEPTIONS`).
That is the argument for on-board index posts, which this does not replace.

## The open number

Once a cap is datum-referenced, the remaining error is the cap's **own body tolerance** —
and that figure is not recorded anywhere in this repo. The SS17/WS17 bodies are modelled at
nominal 17.00 × 39.00 and 17.00 × 28.50 mm. `SHIM_CLR = 0.10` is sized for handling, **not**
computed against a tolerance. Pull the SCHURTER SCPC number before cutting metal: it sets
this constant, and it decides whether the brace bays can come back in from 0.75 mm and
recover the 111 mm² of footprint that clearance costs.

## Gates

`python3 ../../scripts/reflow_shim.py` runs in `consistency.yml` and fails on: more than one
piece, a plate at least as thick as the caps, any pad contact, a cap without two orthogonal
datum sides, or a clearance that no longer stands inside a ledgered neighbour. It self-tests
the pad measurement each run — with every clearance zeroed the plate **must** touch pads
(0.021 mm²), or the check is measuring nothing and says so.
