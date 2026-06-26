# SOLAR-GLOW · DRH — Repo Audit (v2.1 reconciliation)

## The core finding

Every `.md` in the repo describes the design **as planned** (the v0/REV J → "V1" era).
The committed board — `solar-glow-drh-v2_1.kicad_pcb`, 6-layer / 0.8 mm — moved well past
that, and **the docs were never updated to as-built**. The specific engine of the drift is
**`gen_v2.py`**: it reads the *v1* board and applies v2 deltas in Python, so its pin and
spec assignments disagree with the committed KiCad files. That divergence is the same root
cause behind the earlier BOM 1k-vs-150 Ω mixup and the pin-map confusion below.

So this isn't "one stray note." It's a doc set that lags the board, with a handful of
genuinely load-bearing items that need to be lifted into an **as-built v2.1 spec**.

---

## Part A — Notes left behind that need elevating

### A1. The authoritative pin map is fragmented, and the *newest* copy is wrong — HIGH
Three pin maps exist; the board is the tiebreaker:

| Source | LED drive | VSENSE | BTN | I²C |
|---|---|---|---|---|
| `solar-glow-drh-v1-pinmap.md` | **PA0–PA3 = TCA0 WO0–3** | PA5 | PA7 | PC2/PC3 |
| `SESSION-HANDOFF.md` / `KICAD-PUNCHLIST.md` §15 | **PA4–PA7 = TCD0** | PC3 | PC1 | PC2/PC3 |
| **Committed `v2_1.kicad_pcb` (ground truth)** | **PA0–PA3** | **PD2** | **PA5** | PC2/PC3 |

The newest doc (handoff §15) says LEDs are on **PA4–PA7 / TCD0**. The board has them on
**PA0–PA3**, which is **TCA0 WO0–3** — so firmware following the handoff would configure the
wrong timer and the LEDs wouldn't drive. **Action:** publish one as-built pin map; retire the
§15 LED/VSENSE/BTN lines. (This also confirms the PWM-brightness plan we built: PA0–PA3 =
TCA0 split mode = 4 independent 8-bit channels, exactly what the dimming needs.)

### A2. Wake-on-light comparator — status unresolved after VSENSE moved to PD2 — HIGH
Handoff §15 deliberately put VSENSE on **PC3** to land **AC0 AINP4**, enabling a zero-part
"auto-glow on pickup" (AC0 wakes the MCU when the cell sees light; DACREF sets the
threshold). The committed board moved VSENSE to **PD2**. PD2 is the AVR Dx's canonical analog
pin and is **very likely** an AC0 positive input — in which case the feature *survives* and
also **sheds the MVIO-fuse caveat** PC3 carried (PD2 isn't on PORTC). **Action:** confirm
PD2's entry in the AC0.MUXPOS table, then either capture wake-on-light in the firmware spec
or formally drop it. Don't leave it implied-but-unverified.

### A3. VIPPO fab spec — belongs in the PCBWay order, not a session note — MED
Handoff/punchlist §14: resin-fill+cap (or dog-bone) these in-pad vias that will otherwise
wick on hand-solder — **C6, R1, R3, R4, R5** — *in addition to* the existing list
(U2, U4, Q1, TC1.1/2/3, JP2, D9.A, R2.2). This is a **fab-order line item**. If PCBWay's
via-fill is board-wide it's already covered; if selective, it has to be specified or those
joints suffer. Put it in the fab notes / the order, not just the handoff.

### A4. TC2030 KiCad + fab to-dos — punchlist §12–13
Drop in the **official `Tag-Connect_TC2030-IDC-FP`** footprint (don't hand-draw); **VIPPO the
contact pads** (or plate the 3 alignment holes per note 5 and route VS/GND there to keep pads
solid); honor the **keepout** (no tracks/vias in the shaded area, no signal within 0.508 mm of
a contact pad); mark **DNL** in the BOM. Confirm which of these the v2.1 board already
satisfies and carry the rest forward.

### A5. Firmware levers — durable design knowledge, currently scattered
Worth one "Firmware scope" section: **TCA0 split-mode PWM** (4 LEDs); **RTC/PIT off the
internal 32 kHz ULP** (no crystal); **CCL + EVSYS to run a glow/blink pattern while the CPU
sleeps** (big runtime win); **EEPROM "times-activated" counter** (survives supercap drain);
**internal temp sensor** and **VDD/10 ADC** (rail self-measurement for the energy budget).
Explicitly *not* useful on this part: ZCD (mains only), op-amps (DD family lacks them),
hardware cap-touch (DD lacks the PTC, and the Ti plate kills capacitance — accel tap is the
actuator).

### A6. The glow-window template — design IP buried in a stale-stackup doc
`V1-SPEC.md` §5 has the reusable bit: the **~20.9 × 6.2 mm keepaway rectangle** subtracted
from every layer + marked a routing keepout, the four Ø1.64 mm windows **nestled to letter
boundaries** (not centered in gaps), the track-widening, and the **"drop your own initials in
the box"** template logic. This should survive into the current spec even as the doc around it
(4-layer / 0.4 mm) gets corrected.

### A7. The energy budget — still the #1 open gate, and the as-built numbers shifted
Every doc says: **measure indoor harvest vs LED draw on real boards before committing a
supercap stack.** Still unmeasured. And the figures in the docs (4 LEDs ≈ 5 mA, sized against
1 kΩ on a 5.5 V rail) are **now stale**: the as-built board clamps VS to ~3.47 V and we just
set the ballasts to 150 Ω → ~9 mA/LED peak. So the harvest-vs-draw math needs re-running for
the as-built board, not the planned one.

### A8. Enclosure rules — keep the durable, drop the stale
`ENCLOSURE-NOTES.md` + `V1-SPEC.md` §6 are mostly current and good: **grounded body shorts**
(drop the right-edge castellations or add a die-cut **Kapton ~0.05 mm** layer; land pillars on
GND pour only), **Ti-6Al-4V vs 7075** skin tradeoff, **photochemical etching** for the shallow
reliefs. Stale bits to remove: the **snap dome** and **PA7 cap-touch** discussion (no dome on
v2.1; PA7 is unconnected; the accel tap through the plate is the actuator) and the **QFN-20**
height-stack row (it's the AVR64DD28 VQFN28 now).

### A9. As-built features absent from *every* doc
The v2.1 board carries things no `.md` mentions — capture them:
- **Second solar panel PV2 + its own blocking Schottky D9** (docs describe a single panel).
- **Shunt clamp (TLV431 + PNP, Q1/U4/R7–R9/C7)** holding VS ≤ 3.47 V for the accel — the docs
  planned an **LDO** (V1-punchlist §3, TPS7A02) instead. The accel-voltage solution changed and
  no doc reflects it.
- **SW2 OFF/ON/TINY selector + R12** — the v1-pinmap left SW2's wiring as an open question;
  it's resolved on the board (ANODE common → SW2 → VS / R12→VS).
- **Stackup: 6-layer / 0.8 mm**, not the planned 4-layer / 0.4 mm.

---

## Part B — Docs that are stale enough to mislead (rewrite or retire)

- **`README.md`** — describes **REV J**: ATtiny1616, 2-layer, coin cells, snap dome, 1 kΩ
  ballast, `pcb_route.py`/`gerber_export.py` (filenames that no longer exist). The public face
  of the repo is the wrong board. **Full rewrite to v2.1.**
- **`V1-PLAN.md` / `V1-SPEC.md`** — call it "V1," spec 4-layer / 0.4 mm; the board is "v2.1,"
  6-layer / 0.8 mm. Naming + stackup + thickness wrong. The **harvest/energy reasoning and the
  glow template inside are durable** — fold those forward, fix the headline specs.
- **`SESSION-HANDOFF.md` / `KICAD-PUNCHLIST.md`** — the §15 pin map (PA4–7/TCD0, VSENSE PC3,
  BTN PC1) is wrong vs the board (A1). The §12–14 content (TC2030, VIPPO, placement) is fine.
- **`ENCLOSURE-NOTES.md`** — see A8.

---

## Part C — Delete-material

### C1. Pure junk — delete now
- **`motors___ac__dc.csv`** (157 KB) — a dataset about AC/DC motors. Nothing to do with this
  project; an accidental commit.

### C2. Exact duplicates — delete now (md5-confirmed)
- **`board-preview.png`** (root) — byte-identical to `docs/board-preview.png` (the README
  references the `docs/` copy). Delete the root copy.
- **`enclosure-backshell.png`** (root) — byte-identical to `docs/enclosure-backshell.png`.
  Delete the root copy.
- **`datasheets/typ_SCPC`** — same size as `datasheets/typ_SCPC-2.pdf` (the WS17 supercap
  datasheet). Keep the `.pdf`-named one, delete the bare duplicate.

### C3. Orphaned datasheets — parts no longer on the board
- **`ATtiny1614-16-17-DataSheet-…pdf`** — the v0 MCU; replaced by the AVR64DD28 (whose
  datasheet is also present). Gone.
- **`MMSD4148T1-D.PDF`** — the coin-cell-path diode (D6/D7); coin cells removed.
- **`F12340.kicad_sym` + `SW_F12340.kicad_mod` + `K75p11.pdf`** — the Snaptron snap dome and a
  Keystone coin-retainer catalog page; dome + coin path both removed.
- **`SM141K06L`** — the **old** solar-cell variant; the board uses **SM141K06TF** (also
  present). Old variant is dead weight.
- **Verify, don't blind-delete:** **`ALD810025-2.pdf`** is the **quad** SAB datasheet, but U2 is
  the **ALD910025 dual** — confirm it's a leftover wrong-part doc vs a shared family sheet.
- **Inspect:** **`datasheets/The`** — a title-less PDF (1.4 MB) with a truncated filename;
  open it to see if it's a real datasheet or a stray download.

### C4. Superseded-version artifacts — delete unless you want the lineage
These are genuinely dead (the board is v2.1 in KiCad), but they're your version history, so
it's a keep-the-archive call rather than a must-delete:
- **REV J / v0:** `solar-glow-drh-pcb-generator-revJ.zip`, `solar-glow-drh-gerbers-revJ.zip`,
  `solar-glow-drh-gerber-preview-v0.png`, `build_kicad_front_v0faithful.py`.
- **The abandoned v1 (4-layer, *unrouted*) board:** `solar-glow-drh-v1.kicad_pcb`,
  `solar-glow-drh-v1-ROUTING-PLAN.md`, `solar-glow-drh-v1-netlist.py`, and the v1 render PNGs
  (`…-v1-back-kicad`, `…-v1-back-realfp`, `…-v1-front-asfab`, `…-v1-front-realfp`,
  `…-v1-fronttop-clearance`).
- **`gen_v1.py`** — the v1 generator.

### C5. The one that actively confuses — retire `gen_v2.py` and its outputs
`gen_v2.py` is **non-authoritative**: it generates a *different* board than the committed
KiCad files (different VSENSE/BTN pins, the 1k-not-150 ballast, etc.). Its emitted artifacts —
**`solar-glow-drh-v2-gerbers/` (unzipped folder) + `solar-glow-drh-v2-gerbers.zip` +
`solar-glow-drh-v2-gerber-preview.png`** — therefore **do not match the board** and should not
be sent to fab.
- **Minimum:** delete the unzipped `…-v2-gerbers/` folder (redundant with the `.zip`).
- **Right move:** retire `gen_v2.py` (or rename it `gen_v2_LEGACY_DO_NOT_USE.py`), and
  **regenerate gerbers from KiCad** as the authoritative fab output. Keeping it live is what
  produced the BOM and pin-map drift in the first place.

---

## Suggested order of operations

1. **Publish the as-built pin map** (A1) — highest leverage; unblocks firmware and kills the
   §15 error.
2. **Resolve wake-on-light** (A2) — one datasheet lookup; keep or kill.
3. **Rewrite the README to v2.1** (Part B) — the repo's front door.
4. **Fold A3–A9 into a single `V2-SPEC.md`** and mark `V1-PLAN`/`V1-SPEC` superseded.
5. **Retire `gen_v2.py`, regenerate gerbers from KiCad** (C5).
6. **Sweep C1–C3** (safe deletes) and decide on C4 (history).
