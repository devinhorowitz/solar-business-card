# Firmware → PCB / Hardware — open cross-team items (SOLAR-GLOW DRH v3.0)

**From:** Firmware
**Date:** 2026-07-10
**Re:** one number we need to finish the in-sun "loading" tell, plus two confirmations

## Where firmware stands
Firmware is code-complete and link-clean — every module symbol resolves, `led.c`
is intact, and it reviews warning-free. It has **not** been through a real AVR-Dx
build + bench yet; that gap is on us (toolchain / DFP), not you. One feature is
fully built but **intentionally left unwired**, waiting on a single number from
your side.

---

## 1. Primary ask — VIN at the clamp point (for the in-sun sweep)

We have an optional UX "tell": in **strong sun with the caps full**, the card
plays a left→right "loading" sweep across the DRH LEDs (`led_sweep`, already
written and tuned). It only ever runs when the caps are *already* full, so it
can't drain the pack — it just spends free solar. The **trigger is the only
missing piece**, and it needs one threshold from you.

**What we need:** the value of **VIN — the solar-node voltage on the panel side
of blocking diode D1, i.e. the node R5/R6 (1 MΩ each) divide into PD2 —** *when
the TLV3011B clamp is actively holding VS at its trip point under strong sun.*

- Firmware reads this as `sense_vin_mv()` ( = the PD2 reading × 2 ), in millivolts.
- You've re-anchored the clamp to the TLV3011B at **VS ≈ 3.5 V nominal /
  3.60 V worst case.** Assuming that's firm, we want the **corresponding VIN** at
  that operating point. Our rough placeholder is ~3.9 V (VS + a Schottky drop
  across D1) — but we don't want to ship a guess. Please give us the real figure
  from the board / sim.
- If you can, give us **two points**: VIN as the clamp *just* begins to engage,
  and VIN under *hard* clamp in bright sun. That spread lets us set the threshold
  with sensible hysteresis so the sweep doesn't chatter at the boundary.

**Why the exact number is feel-critical, not safety-critical:** the sweep's hard
safety gate is `sense_vdd_mv() ≥ 3300 mV` (caps full), measured against VS and
**independent of the clamp**. Even if the VIN figure is a little off, the
animation can never drain the pack — your number only sets *when in the sun* it
kicks in, i.e. how it feels.

---

## 2. Please confirm — the Q1 thermal fix is the plan of record

Our understanding: Q1's over-temp is being fixed **on the copper** — solid
pad-3-to-pour, a GND thermal-via cluster, and a top-side GND flood over Q1
(θ_JA ~206 → ~90 °C/W, bringing Q1 in spec at full 385 mW across the hot-car
range) — and the **45 Ω ballast swap stays shelved.**

If that's still the plan, **firmware keeps the 150 Ω ballast assumption and ships
no brightness retune and no cap-drain interlock** (the interlock only ever
existed to guard a firmware power-dump we are no longer doing). Please flag us if
the ballast or pour plan changes — that's the one thing that would force a
firmware brightness/interlock rework.

---

## 3. Minor — C13 footprint field mislabel (non-electrical)

Heads-up for your next schematic touch: **C13**'s footprint *field* reads
`solarglow:C7`, while the reference designator itself is correctly "C13". No
electrical impact — just a stale field to correct while you're in there.

---

## Appendix — ADC conversion (for sanity-checking your numbers)
12-bit ADC against the **2.500 V** internal reference:

| Path | Formula | Example |
|------|---------|---------|
| **VIN** (VSENSE = VIN/2 on PD2) | `counts = VIN_mV × 0.8192` | VIN 3.90 V → 3195 counts (valid to VIN 5.00 V, where pin = 2.5 V = ref) |
| **VDD / VS** | `counts = VDD_mV × 0.16384` | VS 3.30 V → 541 counts |

So whatever VIN you hand us, we can convert straight to the compare value the
poll loop tests. The number we ultimately drop into `board.h` is
`SWEEP_SUN_VIN_MV` (name TBD), in millivolts at the VIN node.
