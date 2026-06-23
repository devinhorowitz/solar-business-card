# SOLAR-GLOW DRH — KiCad Replication Punch List (v2)

Single ordered list of everything to change in the KiCad source to match `gen_v2.py`
(the audited, 25/25-clean v2 design). Work top to bottom, then run DRC. Coordinates are
KiCad mm, all parts **back side (B)** unless noted. This is the delta only — the rest of the
board already matches.

> Decisions folded in: **second panel PV2 added** (front bottom third, parallel — §4); **button
> deleted** for accelerometer-tap actuation, BTN reserved to the front middle-third (§1); **Q1 →
> WDFNW3 BCP5316MTWG** (the second panel ~doubles the clamp's worst-case shunt to ~335–435 mW, past
> SOT-23 — §6); **TC1 stays** (confirm the connector variant — §1); **U4 TLV431 cathode/anode wiring
> corrected** (the audit bug — §2).

---

## FRONT-END: per-panel Schottkys + clamp on VS (newest, session 6)
Front-end re-netted (per-panel blocking diodes; clamp moved off VIN onto VS). Mirror in KiCad:
- [ ] **Add D9** (2nd MMSD301T1G, same footprint as D1) at B (43.5, 53.5): D9.K = VS (41.65, 53.5), D9.A = VINB (45.35, 53.5).
- [ ] **PV2 positive -> VINB** (new net): re-net PV2.P / PV2.Pt from VIN to VINB; route PV2.Pt -> In3 down the E margin (E of SC4) -> D9.A.
- [ ] **Clamp onto VS**: re-net Q1.2, R9.1, R7.1, C7.1 from VIN to VS. **Delete the whole VIN rail at y44.8 + the E detour**
  into Q1.2's emitter. R9.1/R7.1/C7.1 (0805) stitch to the In4 VS plane; Q1.2 gets one VS via at (41.5, 51.0).
- [ ] D1 stays as-is (PV1 -> VS). C7 becomes VS decoupling. VSENSE unchanged (R5.1 taps VIN = PV1 node).
- [ ] **BOM**: R7 -> 1.8M (RC0805FR-071M8L), R8 -> 1M (RC0805FR-071ML); D1 line is now qty 2 (D1, D9). Clamp trip = 3.47 V on VS.

See SESSION-HANDOFF session-6 for the full rationale.

---

## 0. FOOTPRINT UPSIZE → 0805 (newest, session 5)
All sub-0805 passives are now **0805** in the gerbers (pads 1.0 × 1.2 mm, centers 1.9 mm) for
hand-soldering, and Q1 is on the **WDFN 2×2**. The board re-runs 25/25 single-island, zero shorts.
**The exact (x, y) for every moved pad — clamp (Q1/U4/R7/R8/R9/C7), C6, the VSENSE divider (R5/R6/C5),
C4, and the vertical SJ1 — is the coordinate table in `SESSION-HANDOFF.md` (session-5 section).** Mirror
those, then DRC. Quick orientation notes:
- [ ] Clamp passives R7/R8/R9/C7 → 0805 **vertical** (pads stacked in y); re-space per the table. Keep
  the VIN rail's east detour into Q1.2 (the emitter is boxed in).
- [ ] C6 (accel decoupling) → 0805 horiz; VS/GND auto-stitch, no re-route.
- [ ] VSENSE divider: R5/R6 in a row at y50.4, **C5 dropped to y52.6** as the filter cap; all 0805 horiz.
- [ ] C4 (VS decoupling, E of U2) → 0805 horiz; auto-stitch.
- [ ] **SJ1 → 0805 vertical** at x13.3 (VS top / VDDIO2 bottom). It does **not** fit horizontal — the
  U1-to-D2 gap is 2.8 mm vs an 0805's 2.9 mm width. VDDIO2 wraps into SJ1.2 from the south.
- [ ] **R10/R11 (I2C pull-ups) — now 0805**: R10 (15.05, 32.40)/(16.95, 32.40), R11 (15.05, 34.96)/(16.95, 34.96),
  beside JP1 (R10.1 abuts JP1.1, R11.1 abuts JP1.2). To make them fit, the **U3↔JP1 SDA/SCL runs moved off B
  onto inner layers** (SDA → In3, SCL → In2, crossing the freed band into JP1's surfacing vias); the VS pads
  auto-stitch. Mirror the two parts + re-route those two nets onto inner layers. BOM already lists them as
  0805, so no BOM change.

---

## 1. DELETE
- [ ] **BT1, BT2, D6, D7** — the battery sub-circuit (the v2 design is supercap-only).
- [ ] **M1** — the `ACCEL_reserved` 2×2 keepout. U3 now occupies that spot.
- [ ] **TC1 — keep it** (do not delete). It's programmed before the supercap + solar panel are
  installed, then deliberately covered (the cap/panel hide the locator holes — by design). The one
  real action: **confirm TC1 is the correct Tag-Connect variant** so the footprint's *locator
  holes* and *locking-leg holes* match the plug you'll use — TC2030-IDC-NL ("no legs", hand-held
  for the one-time program, only the 2 alignment holes) vs the legged TC2030-IDC (adds 3 retention-
  leg holes for hands-free). Cross-check against `datasheets/TC2030-MCP.pdf`. Its under-SC1 vias
  stay with it.
- [ ] **SW1 (snap dome) + D8 (its ESD TVS)** — button removed. Actuation is now an accelerometer
  tap/double-tap (works through the Ti back-plate, which a touch button wouldn't). The BTN net (PA7)
  is reserved out to a landing in the front middle-third (≈ 25.4, 56–57) so a physical button can be
  re-added later without re-routing — keep that corridor clear.

## 1b. NOTE — M1 vs U3
M1's deletion frees the spot U3 occupies; nothing else references M1.

## 2. ADD — the clamp (new nets: **CLBASE**, **CLREF**) — all B side
| Ref | Part / footprint | Pad → net | Center (mm) |
|----|------------------|-----------|-------------|
| Q1 | **BCP5316MTWG / WDFNW3 2×2** | 1=B→CLBASE, 2=E→VIN, 3=C→GND; exposed pad=C→GND+vias | (40.6, 49.0) |
| **U4** | **TLV431B / SOT-23-3 (DBZ)** | **1 REF→CLREF, 2 CATHODE→CLBASE, 3 ANODE→GND** | (43.2, 49.0) |
| R7 | 20 k / 0805 | 1→VIN, 2→CLREF | (44.6, 48.6) |
| R8 | 10 k / 0805 | 1→CLREF, 2→GND | (45.1, 49.6) |
| R9 | 1 k / 0805 | 1→VIN, 2→CLBASE | (41.7, 47.6) |
| C7 | 100 nF / 0805 | 1→VIN, 2→GND | (38.8, 49.0) |

> ⚠️ **U4 is the audit fix.** TI DBZ/SOT-23-3 pinout is pin1=REF, **pin2=CATHODE, pin3=ANODE**.
> Wire the **cathode to CLBASE** and the **anode to GND**. Use a stock TLV431 SOT-23-3
> symbol+footprint so the pad numbers come out right — do **not** hand-number the pads (that's
> what produced the swap that would have latched Q1 on and killed the rail).

## 3. ADD — accelerometer + I²C pull-ups — all B side
| Ref | Part / footprint | Pad → net | Center / notes |
|----|------------------|-----------|----------------|
| U3 | **LIS2DH12 / LGA-12** (2.0×2.0, 0.5 mm) | 1 SCL, 2 CS→VS, 3 SDO/SA0→GND (=addr 0x18), 4 SDA, 5 Res→GND, 6/7/8 GND, 9 Vdd→VS, 10 Vdd_IO→VS, 11 INT2, 12 INT1 | (20, 35.9) **rot 180°** |
| C6 | 100 nF / 0805 | 1→VS, 2→GND | (22.7, 36.4) |
| R10 | 4.7 k / 0805 | 1→SDA, 2→VS | (16.0, 33.0) |
| R11 | 4.7 k / 0805 | 1→SCL, 2→VS | (17.0, 35.3) |

## 4. ADD — second solar panel PV2 (front, bottom third) — wired PARALLEL with PV1
| Ref | Part / footprint | Pad → net | Center |
|----|------------------|-----------|--------|
| PV2 | SM141K06L (42×23) / same footprint as PV1 | P,Pt→VIN ; N,Nt→GND | (25.4, 71.9), **FRONT** |

Mirror of PV1 at the bottom third (clears MH1/MH2 like PV1 clears MH3/MH4). Tie both panels' VIN
together **before D1** — one shared blocking diode is fine; add a per-panel Schottky only if you want
robustness against half-shading the card. Do **not** series them (that doubles the voltage and cooks
the rail). Doubles harvest (sun ~368 mW, office ~0.7 mW) so the card charges in dim light. The front
bottom third was freed by deleting SW1; the supercaps under it are back-side. (The old B-side button
ESD diode D8 is gone with the button.)

## 5. MODIFY
- [ ] **Rename MCU nets:** pin 21 (PF1) → **INT1**, pin 20 (PF0) → **INT2**. Route each to the
  matching U3 pin (INT1↔U3.12, INT2↔U3.11).
- [ ] **Move JP1** (I²C breakout) north → SDA (13.7, 32.42) / SCL (13.7, 34.96) / GND (13.7, 37.5),
  B side. (Its old pads blocked the INT-escape corridor.)
- [ ] **Nudge C3** (VDDIO2 decoupling) → center **(12.5, 48.5)**, B side. Pads VDDIO2 / GND.

## 6. FUSES + FIRMWARE (board is dead without these — most were already noted)
- [ ] **Bridge SJ1** (0 Ω). Ties VDDIO2→VS; otherwise PORTC (and therefore I²C on PC2/PC3) is
  unpowered.
- [ ] **PORTMUX.TWIROUTEA → ALT** so TWI0 lands on PC2/PC3 (PA2/PA3 are used for LED PWM).
- [ ] **PA7 / BTN:** no button is populated (accel tap is the actuator), so PA7 can be left as a
  configured NC pin (input-pullup). If you later fit a button at the reserved front-mid landing,
  enable PORTA.PIN7CTRL.PULLUPEN then.
- [ ] **Internal oscillators only** (select OSCHF). PA0/PA1 (HF-xtal) and PF0/PF1 (32k-xtal) are
  repurposed as PWM / INT, so there are no external crystals.
- [ ] **BODLEVEL ≈ 2.6 V** for a clean cold start from low cap charge.
- [ ] **Configure NC pins** (PA6, PD1–PD7) as input-pullup or output to avoid floating-input
  leakage.
- [ ] **ADC:** VSENSE source impedance is ~500 k → use a long SAMPLEN; C5 is the charge reservoir.
- [ ] **Accel tap = the button.** Configure the LIS2DH12 CLICK engine (CLICK_CFG / CLICK_THS /
  TIME_LIMIT / TIME_LATENCY / TIME_WINDOW) and route the click interrupt to INT1/INT2 → MCU wake →
  glow burst. Reject pocket-bumps with **double-tap** (or arm the tap only after the accel reports
  the card has been still), and rate-limit the glow so a jostled card can't drain the bank.

**Q1 package — WDFNW3 2×2, onsemi BCP5316MTWG** (the BCX53-16 SOT-89 line went out of stock across every brand — Nexperia, Diotec, Diodes, MCC — so we moved to onsemi's WDFN, which has deep stock). With two panels in parallel the clamp's worst case (full sun, caps full, MCU idle) is **~335–435 mW** in Q1 (both cells pushing ~Isc each at the 3.72 V trip). The BCP5316MTWG is rated **875 mW**, so that worst case sits at about half its rating — comfortable, where a SOT-23 would have been at its Tj limit. It is a **wettable-flank** DFN: the plated side flanks wick solder into a visible fillet, so it inspects like a leaded part despite being leadless. **The exposed pad is the collector** — it drops onto the GND pour with a few thermal vias into it (the heatsink that replaces the SOT-89 tab, and the collector tie, in one). The lead pinout is confirmed from onsemi's bcp53m-d.pdf (case 515AA, now in the repo): **pin 1 = Base → CLBASE, pin 2 = Emitter → VIN, pin 3 = Collector → GND** — B-E-C, *not* the B-C-E of the SOT-223 BCP53, so the inferred order was wrong and reading the figure was worth it. Pin 3 (collector) sits on the same GND net as the exposed pad. The 2×2 is smaller than the SOT-89, so it eases the clamp cluster instead of forcing a re-space. Firmware-glow stays the first line of defense; the WDFN + pour + vias is the thermal margin behind it. DS: onsemi bcp53m-d.pdf

## 7. FABRICATION NOTES
- [ ] **Tent the under-panel vias.** The BTN reserve landing via (25.4, 57.0) sits in the SC3/SC4
  gap just under the PV2 body; the MID surfacing vias (15.5/35.3, 61.0) and PV2's own VIN via
  (45.5, 63.0) are under PV2. Tent them all — the ~0.1 mm cell standoff clears a tented via.
- [ ] Consider **tenting/plugging the plane-stitch vias that land in the supercap terminal pads**
  (SC1–4 P/N) to stop solder wicking during reflow, or nudge them just off-pad. Low risk on large
  terminals, but cleaner.
- [ ] Footprints: U1 VQFN-28 · U2 SOIC-8 · U3 LGA-12 · U4 SOT-23-3 · **Q1 WDFNW3 2×2 (BCP5316MTWG, exposed pad=collector→GND+vias)** · PV1/PV2
  SM141K06L · R1–R4 1206 · C1–C3 0805 · C4 0805 · C5/C6/C7 + R5–R11 + SJ1 0805. (D8 removed; sub-0805 passives bumped to 0805 for hand-soldering.)

## 8. VERIFY
- [ ] Run **KiCad DRC** after replication (real DRC is the sign-off; the generator's checker is
  the proving tool).
- [ ] Spot-check **U4**: cathode → CLBASE, anode → GND. (The one that would have killed the board.)
- [ ] Confirm new nets **CLBASE / CLREF / INT1 / INT2** are clean and the I²C bus has its two
  pull-ups.
