# SOLAR-GLOW · DRH — v1 Punch List

Items deferred from the **REV J (v0)** cut. v0 ships as: code-defined 2-layer board, ATtiny1616 PWM-breathing 4 amber LEDs, indoor solar **or** dual-coin-cell charge into a 2× supercap stack, button dual-mode (snap-dome **or** cap-touch on PA7), and firmware-only supercap-voltage sense. Everything below was held out of v0 deliberately — either to avoid re-cutting verified routing, or pending prototype data.

Pin facts below are confirmed against the ATtiny1614/16/17 datasheet (DS40002204A) pinmux. Part specs are flagged where they're from memory and need a datasheet check before committing. Energy figures are first-order — validate on the prototype.

---

## 1. Light-sense (VIN → ADC) — *deferred: routing*

**Why deferred.** The only free ADC pins are at the MCU (lower-left); VIN lives on the upper board (D1 anode); the solid VS ground-rail at y33 has no gap. A sense trace must therefore cross on the front, through the one channel already packed with the four LED drives, and the front below the rail is boxed by the contact-block mask openings (y27.6–32) and the front QR. No clean corridor in v0.

**v0 stand-in.** VDD proxy — the ADC reads VDD (= VS rail) against the internal reference; the cap charges/holds in light and sags under load in dark, giving a coarse "harvesting vs not." Zero new copper.

**v1 plan.** Rework/widen the rail-crossing channel, then add a ~÷2 resistor divider (2× 0402, MΩ-class to keep standby bleed sub-µA) tapping VIN into **PA5 (pin 6, AIN5)**. The divide keeps the ADC node under VDD (VIN sits ~0.3 V above VS while charging). Lets firmware measure real harvest and adapt LED duty to available light.

---

## 2. Spare-GPIO breakout — *deferred: routing*

**Why deferred.** Same rail crossing + channel congestion, ×3, to reach the mid TP row.

**v1 plan.** Bring out the verified-free pins — **PA3 (pin 2), PB3 (pin 11, also USART0 RxD-default), PC3 (pin 18)** — as MCU-adjacent pads or a small header, designed into the channel rework rather than routed across the board. Leaves **PA6 (7), PB5 (9), PB4 (10), PC1 (16)** free after.

**v0 interim.** Mid TPs stay as the GND/VS/VIN power-probe row; tack onto a pin pad directly if I/O is needed during bring-up.

---

## 3. Accelerometer (motion: wake / tap / tilt) — *deferred: power · GATED on §6*

**Why deferred.** Power budget. The accel's ~1 µA always-on is trivial vs ~300 µA office harvest — fine *if the card sees daily light* — but it drains the supercap in ~2 days in prolonged dark storage (vs ~3 weeks for the sleeping MCU alone). Only worth adding if v0 proves the card lives in light with reserve (see §6).

**v1 parts — candidates, verify datasheets before committing.**
- MEMS accel, LGA ~1 mm: Bosch **BMA400** (~1 µA low-power) or ST **LIS2DW12**, used as the always-on wake source.
- **LDO required** — VS reaches ~3.85 V (solar) / ~5 V (battery), above the accel's ~3.6 V max. Candidate: TI **TPS7A02** (~25 nA Iq).
- **Mixed-voltage I2C fix** — either a level shifter, or regulate the whole logic rail to 3.0 V (which loses the 1.8–3.0 V harvest band — a trade to weigh), **or move to an MVIO MCU (AVR-DD)**, which gives PORTC its own I/O voltage — no shifter, no harvest-band loss (see §7).

**Interim.** Touch-to-wake via the dual-mode pad is the zero-cost, motion-free alternative.

---

## 4. More LED channels — *held for discussion · weigh with §6*

Four independent channels today: D3–D5 on TCA0 split WO0–2, and D2 on PC0/TCB0 (PB3/pad 11 is only TCA0 WO0-*alternate*, not a 4th independent channel, which is why D2 moved to TCB0). More independent PWM would need careful timer/PORTMUX planning **and** deepens the power constraint — four LEDs full-on is already ~5 mA vs ~0.3 mA indoor harvest. Decide alongside the energy result.

---

## 5. Touch tuning — *validate on v0, may feed v1*

The dual-mode electrode (Ø4.9 bare-gold center on PA7 + GND horseshoe) is a usable self-cap target as-is. Validate PTC sensitivity on the prototype. If marginal, v1 options: enlarge the electrode (deliberate footprint change — **protect the snap-dome fit**) and/or clear the back GND pour behind the electrode to cut parasitic Cp. **Note:** if the enclosure goes **metal** (see `enclosure/ENCLOSURE-NOTES.md`), a grounded back-plate behind the electrode largely kills self-cap touch — plan on the dome as the button and treat touch as expendable.

---

## 6. Energy-budget validation — *the gating question*

**Confirm on the v0 prototype: does the card stay lit in ordinary indoor light with reserve?** First-order budget (datasheet-grounded, validate empirically):

- SM141K06L at 1 sun ≈ 185 mW (3.35 V × 55.1 mA); office light ≈ 100–500× less → **~0.1–0.5 mA at the rail**.
- 4 amber LEDs through 1 kΩ ≈ **~5 mA full-on, ~3 mA average breathing**.
- Supercap ~0.2 C → **~40–60 s breathing per charge, ~10–15 min refill**.
- **Conclusion to test:** continuous full breathing is *not* sustainable on office light (~10× short). Natural indoor mode is harvest-and-pulse (~6–10 % duty) or continuous *dim* (1 LED, ~0.3 mA). Continuous full breathing needs a windowsill / daylight.

This result **gates §3 (accel) and §4 (more LEDs)**. Measure it with the VDD proxy (§1 stand-in) and, once added, the real light-sense.

---

## 7. MCU for v1 — part & package — *open; one datasheet check pending*

v1 wants more than the 1616 has room for — light-sense (§1), spare GPIO (§2), an accelerometer (§3), maybe more LED channels (§4) — and possibly mixed-voltage I²C. **Hard constraint:** the v1 MCU must **not** exceed the 1616's power, especially **sleep / power-down** current (the dark-storage reserve §6 and §3 hinge on), while offering more. Candidates were checked against datasheets / vendor data; the power-down number for the front-runner is the one open item.

**Candidates.**
- **tinyAVR-1 (1616, current)** and **tinyAVR-2** — same power (~0.1 µA power-down). The 2-series sheds the DAC, type-D timer, and two comparators for a 2nd USART, 2 CCL, and a better ADC.
- **ATtiny1627** (2-series, 20-pin, near drop-in) — same power, better ADC, but a feature *trade*, not a superset.
- **ATtiny3217** (1-series, 24-pin) — same power, a strict superset of the 1616 plus more I/O and flash; bigger package.
- **AVR-DD (e.g. AVR64DD28)** — roadmap-optimal once non-drop-in rework is acceptable. 1.8–5.5 V, flexible TCA-to-any-port routing, 2× TCB + TCD, and **MVIO**. MVIO is the key: PORTC runs on a separate VDDIO2, so the core stays on the 5 V supercap rail (full harvest band) while I²C/PORTC sits at 3.0 V for the accelerometer — **the §3 mixed-voltage fix with no level-shifter and no harvest-band loss.** Also serves §1 (ADC) and §4 (PWM).

**The one blocker — power-down current.** No clean public side-by-side proves the AVR-DD's power-down ≤ the 1616's ~0.1 µA (Microchip blocks the automated datasheet fetch). **Pull the AVR-DD datasheet (`AVR64DD28`; the doc also covers AVR32DD28 / AVR64DD20 / AVR32DD20) and read Electrical Characteristics → Power Consumption: Power-Down typ (3 V / 25 °C), and Power-Down with RTC/PIT running.** If it clears the 1616 → **v1 MCU = AVR-DD.** If not → ATtiny1627 (for the ADC) or ATtiny3217 (for the superset).

**Package (ties to the enclosure).** U2 (SOIC-8) already sets the ~1.75 mm back-side floor, so a leaded MCU is nearly free on height: **SSOP-28 (~2.0 mm) ≈ +0.25 mm — recommended**; SOIC-28 (~2.65 mm) ≈ +0.9 mm but the easy 1.27 mm pitch matches the SOIC-8 you already hand-place; QFN-28 (~0.9 mm) buys nothing while U2 is the tall part and needs hot air. See `enclosure/ENCLOSURE-NOTES.md`.

**Caveat if AVR-DD.** Likely no dedicated PTC → cap-touch becomes ADC-based, reshaping §5 — though a metal enclosure deprioritizes cap-touch anyway (lean on the dome). Confirm package (lean SSOP-28) and pin count (28 gives headroom for §1/§2/§3/§4) once the power check clears.

---

## 8. Supercap upgrade + land rework — *V1 PRIORITY · drives the re-spin*

The lands are wrong: the SCPC terminals are two **1.5 × 3.5 mm** pads on the *underside*, diagonal, **within** the 28.5 × 17 mm body, but `FP("SCPC")` puts 3.5 × 3.5 pads at `(±18.25, ±8)` — out on the folded-edge locator tabs. Redraw to the bottom-face terminals (SCHURTER official WS17 land / SnapEDA, or measure the part). While reworking, swap **3-153-434 (WS10, 300 mF) → 3-153-438 (WS17, 1 F)** — same footprint family, **3.3× capacitance** (500 mF @ 5.5 V), ESR 40 mΩ, 1.7 mm thick. V0 protos in hand: bodge a copper lead per terminal to prove the stack. Full detail, the enclosure consequence, and the **baseline-source decision that blocks V1 copper**: `docs/V1-PLAN.md`.

---

## Firmware track — *parked until boards arrive*

PWM breathing; button mode-select (digital-input vs QTouch); ADC VDD-sense; light-sense ADC (once §1 lands); duty-cycle adaptation to measured harvest.
