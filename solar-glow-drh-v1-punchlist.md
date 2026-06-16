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
- **Mixed-voltage I2C fix** — either a level shifter, or regulate the whole logic rail to 3.0 V (which loses the 1.8–3.0 V harvest band — a trade to weigh).

**Interim.** Touch-to-wake via the dual-mode pad is the zero-cost, motion-free alternative.

---

## 4. More LED channels — *held for discussion · weigh with §6*

Four independent channels today: D3–D5 on TCA0 split WO0–2, and D2 on PC0/TCB0 (PB3/pad 11 is only TCA0 WO0-*alternate*, not a 4th independent channel, which is why D2 moved to TCB0). More independent PWM would need careful timer/PORTMUX planning **and** deepens the power constraint — four LEDs full-on is already ~5 mA vs ~0.3 mA indoor harvest. Decide alongside the energy result.

---

## 5. Touch tuning — *validate on v0, may feed v1*

The dual-mode electrode (Ø4.9 bare-gold center on PA7 + GND horseshoe) is a usable self-cap target as-is. Validate PTC sensitivity on the prototype. If marginal, v1 options: enlarge the electrode (deliberate footprint change — **protect the snap-dome fit**) and/or clear the back GND pour behind the electrode to cut parasitic Cp.

---

## 6. Energy-budget validation — *the gating question*

**Confirm on the v0 prototype: does the card stay lit in ordinary indoor light with reserve?** First-order budget (datasheet-grounded, validate empirically):

- SM141K06L at 1 sun ≈ 185 mW (3.35 V × 55.1 mA); office light ≈ 100–500× less → **~0.1–0.5 mA at the rail**.
- 4 amber LEDs through 1 kΩ ≈ **~5 mA full-on, ~3 mA average breathing**.
- Supercap ~0.2 C → **~40–60 s breathing per charge, ~10–15 min refill**.
- **Conclusion to test:** continuous full breathing is *not* sustainable on office light (~10× short). Natural indoor mode is harvest-and-pulse (~6–10 % duty) or continuous *dim* (1 LED, ~0.3 mA). Continuous full breathing needs a windowsill / daylight.

This result **gates §3 (accel) and §4 (more LEDs)**. Measure it with the VDD proxy (§1 stand-in) and, once added, the real light-sense.

---

## Firmware track — *parked until boards arrive*

PWM breathing; button mode-select (digital-input vs QTouch); ADC VDD-sense; light-sense ADC (once §1 lands); duty-cycle adaptation to measured harvest.
