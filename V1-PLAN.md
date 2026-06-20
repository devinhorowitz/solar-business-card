# SOLAR-GLOW · DRH — V1 redesign plan

Status: **baseline source recovered (§4 resolved); the supercap "land bug" did not reproduce (§1).**
V0/REV J is prototyping. With the land re-verified against the datasheet, V1's supercap axis is now an
*optional* drop-in capacitance upgrade — not a forced re-spin. The open question is whether to cut a
new V1 board at all, and if so whether for **2 or 4** cells (§1a).

---

## 1. Supercap upgrade (land re-verified — no rework needed)

**Part swap.** 3-153-434 (WS10, 300 mF, 1.0 mm) → **3-153-438 (WS17, 1000 mF / 1 F, 1.7 mm)**.
Both are 2.75 V single cells; two in series → **500 mF @ 5.5 V** vs 150 mF today — **3.3×**
the storage, and ESR drops to 40 mΩ (from 50). WS10/WS13/WS17 **share one footprint**, so
board *area* is unchanged — only thickness and capacitance move.

**~~The land is wrong and must be redrawn (the whole reason for V1).~~ Correction — the land
matches SCHURTER's recommended land; the "redraw" was a misread. ⚠ bench-confirm before relying.**
Re-checked against `datasheets/typ_SCPC-2.pdf` and the recovered REV J source:

- **Shared land.** The datasheet gives **one** "Soldering pads to Case WS10, WS13, WS17" land: two
  **3.5 × 3.5 mm** pads on the diagonal, **36.5 × 16 mm** pattern, **centres ±16.5 / ±6.25**. The
  3.5 mm pads are intentionally oversized vs the 1.5 × 3.5 mm bottom terminals and run ~4 mm past the
  28.5 mm body ends **by design**, to catch the folded-edge terminals.
- **Current footprint** `FP("SCPC")` = `[("P",16.5,6.25,3.5,3.5),("N",−16.5,−6.25,3.5,3.5)]`, body
  28.5 × 17 — i.e. **exactly** the datasheet land (the code comment even says "WS10 datasheet land").
  The earlier "pads at (±18.25, ±8), out on the locator tabs" read the **36.5 × 16 outer span**
  (half → 18.25 / 8) as the pad *centres*. The centres are ±16.5 / ±6.25 — ~2.25 mm past the body
  end, squarely on the folded-edge contact, not on a locator tab.
- **Consequence.** WS10 → WS17 is a **drop-in part swap on the existing REV J land** — no redraw, and
  the capacitance upgrade alone needs **no board re-spin** (only +0.7 mm Z, an enclosure-cavity
  change that is parked). The ordered REV J boards carry this exact land (gerber-verified, §4).
- **⚠ One open thread.** The prior note said "confirmed against parts in hand." The gerber + datasheet
  evidence says the pattern is correct, so if a real cell didn't seat on a REV J board the cause is
  **placement/rotation** (SC1 rot 270 / SC2 rot 90), not the pad pattern. **Before treating the land
  as final: set a WS-series cell on a bare REV J board and confirm both terminals sit on copper /
  reflow wets both.** If it genuinely misaligns, revisit SC1/SC2 orientation — not `FP("SCPC")`.

**Enclosure consequence (good):** 1.7 mm ≈ U2 (1.75 mm). Bump `cavity` 1.6 → ~1.8 mm and the
caps *and* U2 clear with no pockets — deletes the marginal 0.3 mm U2 skin. ~+0.2 mm behind the
board for a simpler, stronger floor (also helps 7075). See `enclosure/ENCLOSURE-NOTES.md`.

### 1a. Capacity options for V1 — 2 cells vs 4 cells (open)

With the land no longer blocking, there are two ways to take the upgrade:

| | **2× WS17 (2S)** — drop-in | **4× WS17 (2P2S / 2S2P)** — pulled from V2 |
|---|---|---|
| Energy @ 5.5 V | 500 mF → **~7.6 J** (3.3× v0) | 1 F → **~15 J** (2× the 2-cell) |
| Board work | **none** — same REV J land, taller part only | **full reroute** (4×28.5×17 ≈ 43% of board + centre SMD band) |
| Balancer | existing U2, unchanged | **2P2S → one** (U2 as-is); 2S2P → two, or tie midpoints |
| Supercap cost | ~2× a cell | **~2× the 2-cell** (doubles the dominant BOM line) |
| Buys | a real, near-free upgrade | ~2× dark ride-through; does **not** fix the harvest deficit (§6), and cold-starts ~2× slower |

**Budget.** SCHURTER 3-153-438 (WS17, 1 F) is **~€6.77 in volume** (Schukat); qty-1 runs higher
(DigiKey lists it but the qty-1 figure is **TBD** — JS-only page). Plan on **~$8–12/cell**.
Supercaps already dominate this BOM, so the 2→4 delta is essentially **+2 cells (~$16–24/board)**:
2 cells add ~$16–24 of supercap, 4 cells ~$32–48, pushing supercaps from ~half to **two-thirds+** of
per-board cost — and turning V1 into the V2-scale reroute. **Recommendation:** ship the 2-cell drop-in
as V1 (near-free, no board work); take 4 cells only if you're already committing to a reroute and want
maximum dark endurance — otherwise it stays a V2 item (§6).

---

## 2. MCU — parked, gated

No MCU change goes into copper until the **AVR-DD power-down number** lands (pull `AVR64DD28`,
read Power-Down typ @ 3 V/25 °C and with RTC/PIT). If it clears the 1616's ~0.1 µA → **AVR-DD,
SSOP-28** (height is free behind the 1.7–1.75 mm supercap/U2 floor; MVIO solves the §3
mixed-voltage I²C). Else ATtiny1627 (ADC) or ATtiny3217 (superset). Full analysis: punch-list §7.

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

- Supercap: 3-153-438 row in `datasheets/typ_SCPC-2.pdf` (WS17 case drawing p.4; the shared
  "Soldering pads to Case WS10/13/17" land — diagonal 3.5×3.5 pads, 36.5×16 — is on the last page).
- REV J generator source: `solar-glow-drh-pcb-generator-revJ.zip` (recovered; see §4).
- MCU gate: `AVR64DD28` datasheet — **to pull**.
- `solar-glow-drh-v1-punchlist.md` §7 (MCU), §1–§6 (deferred items, energy budget).
- `enclosure/ENCLOSURE-NOTES.md` (parked).
