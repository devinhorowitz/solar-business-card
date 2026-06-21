# SOLAR-GLOW · DRH — V1 redesign plan

Status: **baseline source recovered (§4 resolved). The supercap land bug is REAL — confirmed against
physical parts (§1), and is the reason V1 exists.** V0/REV J is prototyping only. **V1 is LOCKED as a
4-cell 2P2S full reroute** (see `V1-SPEC.md` §0): 1 F @ 5.5 V ≈ 15 J, redrawn under-body supercap
land, 4-layer planes, AVR64DD28 in 28-VQFN. The 2-cell "drop-in" path below is the rejected
alternative, kept for the record.

---

## 1. Supercap land FIX + 4-cell upgrade (the core reason for V1)

**Part.** 4× **3-153-438 (SCHURTER SCPC WS17, 1 F, 2.75 V, 1.7 mm)**, wired 2P2S → **1 F @ 5.5 V
≈ 15 J** on a single MID node (U2 balances it). ESR 40 mΩ.

**The land WAS wrong on v0/REV J and is redrawn for V1 — confirmed against physical parts.** This is
the landmine; it must never be reintroduced. Per `datasheets/typ_SCPC-2.pdf` (p4, Case WS17) and the
cells in hand:

- **The v0/REV-J land is WRONG.** It placed two 3.5 × 3.5 mm pads on a diagonal (36.5 × 16 pattern,
  centres ±16.5 / ±6.25), landing on the cell's **folded end tabs**. Those tabs are coated /
  **non-solderable** mechanical locators, so a board built to that land makes **zero contact**. The
  datasheet's single "Soldering pads to Case WS10/13/17" diagram is a generic stand-in; reading it
  as the WS17 land is exactly the mistake that shipped on v0.
- **The correct land (LOCKED).** The real solderable terminals are **flat pads UNDER the body**:
  **P pad 7.8 × 3.5 mm, N pad 12.2 × 3.5 mm** (the asymmetric widths are the polarity key), centred
  on the cell axis at **±11 mm** from cell centre, ~1.5 mm in from each end, inside the 28.5 × 17 mm
  body. Rotations SC1/SC4 → 90°, SC2/SC3 → 270°. See the locked footprint block in `SESSION-HANDOFF.md`.
- **Consequence.** This is **not** a drop-in on the REV-J land — it is a redraw, which together with
  the 4-cell array + 4-layer planes + the new features is the whole justification for the V1 re-spin.

**Enclosure consequence (good):** 1.7 mm ≈ U2 (1.75 mm). Bump `cavity` 1.6 → ~1.8 mm and the
caps *and* U2 clear with no pockets — deletes the marginal 0.3 mm U2 skin. ~+0.2 mm behind the
board for a simpler, stronger floor (also helps 7075). See `enclosure/ENCLOSURE-NOTES.md`.

### 1a. Capacity: 4 cells (DECIDED) vs the 2-cell alternative (rejected)

**Decision: 4× WS17 in 2P2S → 1 F @ 5.5 V ≈ 15 J** (locked, `V1-SPEC.md` §0). The 2-cell "drop-in"
was the cheaper alternative but is **rejected**: it rode on the (wrong) belief that the REV-J land
was reusable, and the land is being redrawn regardless, so the "free, no board work" advantage does
not exist. The 4-cell reserve is the power headroom the feature menu (§3) needs.

| | 2× WS17 (2S) — *rejected* | **4× WS17 (2P2S) — DECIDED** |
|---|---|---|
| Energy @ 5.5 V | 500 mF → ~7.6 J | **1 F → ~15 J** (~6.6× v0) |
| Balancer | one (U2) | **one (U2, shared MID)** |
| Board work | redraw anyway (land was wrong) | **full reroute** (4×28.5×17 ≈ 43% + centre SMD band) |
| Buys | less dark ride-through | **the feature menu (§3) + max dark endurance** |

**Cost note.** SCHURTER 3-153-438 (WS17, 1 F) ~€6.77 in volume (Schukat); plan ~$8–12/cell. Four
cells push supercaps to two-thirds+ of per-board BOM — the dominant line, and the reason this is a
deliberate reroute, not a casual upgrade.


---

## 2. MCU — DECIDED (AVR64DD28, 28-VQFN)

Resolved (was "parked, gated"). The AVR-DD power-down number landed — **0.65 µA typ** (DS40002315
Table 38-5, `PMODE=AUTO`, 3 V/25 °C); ~6× the 1616's 0.1 µA but still sub-µA and swamped by supercap
+ U2-balancer leakage. **Package = 28-VQFN** (not SSOP-28): with the four cells eating ~43% of the
board, X/Y is binding, so the QFN's ~16 mm² land wins. MVIO solves the §3 mixed-voltage I²C; ADC
serves §1; flexible TCA/TCB/TCD serves §4. Firmware must-do: `PMODE=AUTO` for sleep. Full analysis:
punch-list §7.

---

## 3. Deferred-routing items

Fold into the V1 re-route as the channel rework allows: §1 light-sense (VIN÷2 → ADC),
§2 spare-GPIO breakout, §3 accelerometer (gated on the §6 energy result). Details in the punch list.

---

## 4. ✅ Baseline source — RESOLVED (REV J generator recovered, gerber-verified)

The REV J generator source is **recovered** and packaged for the repo as
`solar-glow-drh-pcb-generator-revJ.zip`: `pcb_route.py` + `gerber_export.py` + deps
(`qr_front.py`, `qr_back.py`, `logos.py`, `logos_cache.wkt`, `rg.py`, `fonts/` = JetBrains Mono
under OFL). **Proof:** re-running `gerber_export.py` regenerates **all nine ordered gerbers
byte-for-byte identical** to `solar-glow-drh-gerbers-revJ.zip` (ignoring `G04` comment/timestamp
lines) — GTL/GBL/GTO/GBO/GTS/GBS/GKO + both drills. DRC clean (all nets connected, no shorts). It is
unambiguously REV J: four independent LED channels (L2–L5 on PC0/PB0/PB1/PB2), ballasts at
x = 18.2 / 23 / 27.8 / 32.6.

→ **Option 1 (provide the REV J source) is satisfied.** Any supercap land tweak — though §1 now says
none is needed — would drop straight onto this source. KiCad (option 2) remains the planned tool for
*final* dense-board copper sign-off, but is **not** required for the part swap.

**Caution for posterity:** an older `solar-glow-drh-source.zip` (in `handoff.zip`) is **REV I** —
single-`LRET` low-side path, ~8 nets, ballasts x = 13.7 / 21.7 / 29.1 / 37.1, one architecture behind.
Generating from it would regress the board to single-channel. Use the recovered REV J source above.

---

## 5. Enclosure — on ice

Parked pending V1 board bring-up. CAD + STEP/STL are preserved in `enclosure/`; the design notes
(material, isolation, cap-touch, machining, height stack) are in `enclosure/ENCLOSURE-NOTES.md`,
now marked PARKED. The supercap change *simplifies* it (uniform ~1.8 mm cavity, no U2 pocket).

---

## 6. Looking further out — V2 (quad-cell, thin 4-layer)

Concept: **4× WS17** on a **0.4 mm 4-layer** board (thinner than today's 0.8 mm 2-layer), cells
paired at opposite ends of the back with the SMD parts clustered in the center; front stays naked;
a full trace redesign.

**Energy (correcting the "4 F"):** that 4 F holds only all-parallel at 2.75 V. The 5.5 V rail needs
two-in-series, so four cells wire 2S2P/2P2S → **1 F effective at 5.5 V**. What's fixed is energy:
4 × ½·1F·2.75² ≈ **15 J = 2× the two-cell V1** (~7.6 J), ~6–7× the original WS10 board. Farads at
2.75 V vs 5.5 V aren't comparable joules; the honest spec is **2× the V1 reserve**.

Notes:
- **Still thin.** The 1.7 mm cells set the back-side height either way; a 0.4 mm board *trims* the
  envelope vs 0.8 mm. Stays in the thin-showpiece lane — and a 0.4 mm board leans on the metal
  back-shell + its pillar field for rigidity (good synergy with the parked enclosure; cf. the
  existing 0.2 mm enclosure variant).
- **4-layer is the right call** — dedicated VS/GND planes clean up supercap power distribution and
  the reroute, and earn their cost on a denser build.
- **Fab:** 0.4 mm 4-layer is a thin stackup → a PCBWay/JLC custom job (OSH Park's 4-layer is a fixed
  thicker stackup). Aligns with the PCBWay route already planned for the locked design.
- **Layout:** 4× (28.5 × 17) cells + a center SMD cluster on 50.8 × 88.9 is tight but workable
  (two cells per end, ~28 mm center band) — confirm with a placement pass. "Opposite sides" =
  opposite *ends* of the back keeps the front clean; opposite *faces* would put cells on the
  glow/solar front (conflict).
- **Balancing:** 2P2S → one midpoint balancer; 2S2P → two, or tie the midpoints.
- **Diminishing returns:** a 2× bucket buffers dark ~2× longer but cold-starts ~2× slower on indoor
  light and doesn't change the harvest-vs-draw ratio (§6) — buffers a deficit, doesn't cure it.

Verdict: a thin, denser, ~2× energy evolution — naturally a **V2** (full reroute + 4-layer + 4 cells,
not a drop-in). **But** with the land no longer forcing a V1 re-spin (§1), the 4-cell array is now the
main thing that *would* justify cutting a new V1 board — so it has become an explicit V1-vs-V2 fork,
see **§1a**. If V1 stays a drop-in (2 cells, existing REV J board), this whole 4-cell program is V2.

---

## References

- Supercap: 3-153-438 row in `datasheets/typ_SCPC-2.pdf` (WS17 case drawing p.4). The generic
  "Soldering pads to Case WS10/13/17" diagram is a stand-in — the real WS17 solderable pads are the
  under-body flats (P 7.8×3.5, N 12.2×3.5, ±11 mm), NOT the diagonal end-tab land. See §1.
- REV J generator source: `solar-glow-drh-pcb-generator-revJ.zip` (recovered; see §4).
- MCU gate: `AVR64DD28` datasheet — **to pull**.
- `solar-glow-drh-v1-punchlist.md` §7 (MCU), §1–§6 (deferred items, energy budget).
- `enclosure/ENCLOSURE-NOTES.md` (parked).
