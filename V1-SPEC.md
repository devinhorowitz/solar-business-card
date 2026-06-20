# SOLAR-GLOW · DRH — V1 design spec (4-layer, quad-supercap)

**Consolidates** `V1-PLAN.md`, `solar-glow-drh-v1-punchlist.md`, and `enclosure/ENCLOSURE-NOTES.md`
under the now-locked V1 direction. Those stay as the detailed source docs; this is the synthesis and
the build order. The numbers here are datasheet-/geometry-grounded; the one open hardware gate (MCU
power-down) and the one open empirical gate (v0 harvest) are called out.

---

## 0. The decision (locked)

- **4-layer, 0.4 mm, PCBWay.** Thinner than today's 0.8 mm 2-layer, with real power planes.
- **4× WS17 supercaps on the rear**, wired **2P2S → 1 F @ 5.5 V ≈ 15 J** — **6.6× the v0 reserve**
  (~2.3 J) and 2× the two-cell drop-in. This is the power headroom that buys the feature menu (§3).
- **Titanium rear-shell** is the end-goal (§6); **front stays naked**; the **"DRH" monogram glow is
  preserved**.
- This is a **full reroute**, justified by the 4-cell energy + the added features — not the drop-in
  the 2-cell path would have been. The recovered REV J generator is the placement/artwork baseline;
  final dense-board copper sign-off goes to KiCad.

Why this is coherent: the 4-cell array needs the reroute *and* benefits from 4-layer planes for
supercap power distribution; the planes also clean up the denser routing; 0.4 mm trims the envelope
toward card-thin. The cost is real (§1, §5) and is the point of the rest of this doc.

---

## 1. The rear real-estate problem (the core layout constraint)

The glow is **central and rear-facing**, which is exactly where 4 big cells want to sit:

- "DRH" is a **front** copper+mask cutout at **(25.4, 45), 5.5 mm tall**, backlit by **D2–D5 on the
  rear at y = 45** through **Ø1.64 mm light-entry holes**. The monogram and its LEDs must stay
  aligned.
- 4× (28.5 × 17) cells = **1938 mm² = 43%** of the 50.8 × 88.9 board.
- **Decorative vs functional:** decorative silk *can* hide under the cells (fine). The **LEDs are on
  the same rear side as the cells and cannot** — and the monogram tracks the LEDs. So a central
  **glow band is protected**; the cells go around it.

**Layout (chosen): mirror the existing top supercap pair to the bottom** (see
`solar-glow-drh-v1-layout-study.png`). SC1/SC2 stay put at y = 67.5; SC3/SC4 reflect them across the
board centerline to y = 21.4. This reuses the proven footprint **and** its power routing, and
electrically it's the minimal extension: the bottom pair joins the **same VS/MID/GND nets** — SC3 ∥
SC1 on VS–MID, SC4 ∥ SC2 on MID–GND — giving **1 F @ 5.5 V on a single MID node**, so **U2 still does
all the balancing (no new nets, no second balancer)**. The reflection leaves a **protected ~17 mm
glow band** through the center (LEDs at y = 45, monogram). Consequence: the SMD now in the lower
third (U1, J1, JP1, some passives) **relocates** up around the glow band + the side margins / center
gap — all SMD is ~120 mm² so it fits, but the placement pass has to (a) pack it around the glow and
(b) run **MID the length of the board** to tie both pairs' midpoints (cheap on 4-layer). The cells
are the area hogs (43%); the SMD is not the constraint, the geometry is.

This is the first thing to settle in the V1 placement pass, and it's the one real cost of going to 4
cells: the glow design and the energy tank now compete for the same rear center.

---

## 2. Power-budget framework (how v0 testing drives the V1 envelope)

The honest model, and the whole reason v0 bring-up gates V1:

- **Continuous sustainable average draw ≤ harvest.** Indoor harvest is **~0.1–0.5 mA at the rail**
  (SM141K06L is 185 mW at 1 sun, 100–500× less indoors). That number — not the cap size — sets the
  brightness you can hold *forever*.
- **The reserve buys excursions.** 15 J is how long/bright you can **exceed** harvest before the cap
  drains, and how long the glow rides through darkness. The catch: recharge scales with it —
  15 J / ~1.6 mW ≈ **hours** to refill from empty on office light. Bigger tank = longer dark glow
  **and** longer cold-start.
- **So "tweaking the envelope" = choosing duty + feature set so average draw ≤ harvest, and spending
  the 15 J reserve on the show's peaks and dark ride-through.**

**v0 measures the one unknown — actual harvest — via the VDD-proxy ADC** (reads the rail vs the
internal reference; charges in light, sags under load). That single measurement sizes everything
below.

| | reserve | sustained draw it supports |
|---|---|---|
| v0 (2× WS10, 150 mF) | ~2.3 J | ≤ harvest; ~40–60 s breathing / ~10–15 min refill |
| V1 (4× WS17, 1 F) | ~15 J | ≤ harvest; minutes of breathing per charge; refill ~hours |

Draw items to budget against harvest: **4 LEDs ≈ 5 mA full / ~3 mA breathing; +1 LED ≈ +1.25 mA;
accel ≈ 1 µA; light-sense divider sub-µA; MCU sleep ≈ 0.1 µA.** The LEDs are the only mA-scale load;
everything else is noise on the budget.

---

## 3. Feature menu (gated on v0 + the new headroom)

What the 15 J + the measured harvest let you spend on. Passive sensors are ~free on current; the
LEDs are the budget.

- **Light-sense (VIN ÷2 → ADC).** Sub-µA standby, two 0402s. **Strongly recommended** — it's the
  sensor that makes "adapt the glow to available light" real, and it closes the loop the whole
  power model depends on. Taps VIN into an ADC pin (PA5/AIN5 on the 1616; trivially routed on
  4-layer).
- **Accelerometer (BMA400 / LIS2DW12, ~1 µA).** Wake / tap / tilt. Needs an **LDO** (VS reaches
  ~5 V > the accel's 3.6 V max; e.g. TPS7A02 ~25 nA Iq) and **I²C voltage handling** — solved
  cleanly by an MVIO MCU (§4). The ~1 µA is trivial against harvest but drains the tank in ~days of
  *prolonged dark* (vs ~weeks for the sleeping MCU) — gate on whether the card lives in light.
- **More LEDs.** +~1.25 mA each full-on; raises the draw ceiling. The 15 J reserve buffers a bigger
  "show," but continuous all-on stays harvest-bound. Independent PWM needs timer/PORTMUX planning
  (AVR-DD's flexible routing helps). *Specific v2 lever:* vertical LED **pairs in the two inter-letter
  gaps** (→ 6 total) for more inner-stroke glow — defer past the v0 harvest result (it's **+50% peak
  draw**), and it grows the keepaway box taller. Even then it won't light the D/R **bowls** (a diffuser
  film is the lever for full-letter evenness, not more boundary LEDs). **4 is the v1 baseline** — the
  proven minimum for even back-diffusion.
- **Brighter / longer glow.** *Brighter* continuous is harvest-limited; *brighter peaks* and
  *longer dark glow* are exactly what the 4-cell reserve buys.
- **Touch.** A grounded Ti back-plate swamps the PA7 self-cap electrode → **the dome is the button**;
  treat cap-touch as expendable in the shelled build.

---

## 4. MCU — the one pending hardware gate

**Target: AVR-DD (AVR64DD28), SSOP-28.** It serves the whole menu: **MVIO** (PORTC on a separate
VDDIO2 → core stays on the 5 V rail for full harvest band while I²C/PORTC sits at 3.0 V for the
accel — no level shifter, no harvest-band loss), ADC (light-sense), flexible TCA/TCB/TCD PWM (more
LEDs), and 28-pin GPIO headroom (§1/§2/§3). 4-layer makes the extra routing easy, and the height is
free behind the 1.7 mm cells.

**The gate:** confirm its **power-down current ≤ the 1616's ~0.1 µA** before committing (dark-storage
reserve hinges on it). Pull the `AVR64DD28` datasheet → Electrical Characteristics → Power
Consumption: **Power-Down typ (3 V / 25 °C)**, and **with RTC/PIT running**. If it clears → AVR-DD.
If not → **ATtiny1627** (better ADC, near drop-in) or **ATtiny3217** (strict 1616 superset, bigger
package). Package height is a non-issue: SSOP-28 (~2.0 mm) is ~+0.25 mm over the cells; a QFN buys
nothing while the cells/U2 are the tall parts.

---

## 5. 4-layer stackup + the glow windows (new work the 4-layer brings)

- **Stackup:** L1 top signal/parts · **L2 GND plane** · **L3 VS plane** · L4 bottom signal/parts.
  The planes are the reason to go 4-layer — low-impedance VS/GND for the supercap charge/discharge
  currents, plus shielding and a cleaner reroute.
- **Glow windows void ALL FOUR layers.** On 2-layer this was trivial; on 4-layer the **DRH cutout +
  the four Ø1.64 mm LED entry holes must clear L1/L2/L3/L4** so bare FR4 passes diffuse light. Plan
  the GND/VS plane voids deliberately so the central window doesn't **fragment** the planes — route
  the supercap power around the glow band, not through it.
- **Monogram + LED-window placement + keepaway (templated).** Track the initials wider (**0.12 →
  ~0.23**, ~2.5 mm inter-letter gaps) so each **Ø1.64 mm window nestles a letter boundary** — the two
  inter-letter gaps + the two outer flanks — *snug* against the strokes, **not** centered in a wide
  gap. The gaps are front **copper** (only the strokes are cut), and on 0.4 mm FR4 light only couples
  into a stroke within ~0.7 mm, so a wide gap would bury the LED under copper and kill that window.
  The **keepaway is one rectangle**, sized tight to the content (**~20.9 × 6.2 mm** = window span ×
  letter height + 0.35 mm clearance, centered on the monogram), **subtracted from every layer's copper
  and marked a routing keepout** so nothing wires across the light path between the rear windows and the front face. A single box (vs a
  letter-hugging field) is deliberate: it's **letter-agnostic**, so the design is a **template** —
  anyone can drop their own initials in the box and keep the four fixed centerline windows. See
  `solar-glow-drh-glow-window.png`.
- **0.4 mm changes the glow.** Thinner FR4 spreads light **less** than v0's 0.8 mm → a **crisper,
  more edge-lit** monogram (brightest at the strokes nearest each window); evening it out may want
  **more windows or a diffuser film**. **Validate the glow *look* on a 0.4 mm coupon — v0 (0.8 mm)
  will not predict it.** (This is the cost of merging the glow board and the feature board, which the earlier
  plan kept separate precisely to avoid plane-void/diffusion juggling.)

---

## 6. Titanium rear-shell (end-goal; bakes a few rules into V1 now)

Rear-only cover, naked front. With the cells at 1.7 mm they now set the floor; U2 at 1.75, SSOP-28
at ~2.0 → a uniform **~2.2 mm cavity, no U2 pocket**. Build these **shell-ready rules into V1 now**
so the board doesn't need re-spinning for the enclosure:

- **Grounded body → shorts.** **Drop the right-edge castellations** in the enclosed variant; land
  support pillars **only on GND pour**; spec a **die-cut Kapton (~0.05 mm)** isolation layer under
  the shell as the blanket fix. Cap-touch dies → dome (§3).
- **0.3 mm skins** need titanium's strength (yield ~880 MPa); 7075 is the cheaper fallback with
  thicker floors. **Ti mills slow** (work-hardens) → cut the shallow reliefs by **photochemical
  etching**, CNC only the walls/bosses. Keep M2 engagement in the thick bosses, never the thin
  pocket zones.

The detail and the CAD knobs are in `enclosure/ENCLOSURE-NOTES.md` (PARKED); resume after V1 board
bring-up.

---

## 7. Build order

1. **v0 bring-up + harvest measurement** — the gate for everything else. Run `BRINGUP.md`, then
   measure **indoor harvest vs LED draw** via the VDD proxy. The harvest number sizes the §2/§3
   envelope. *(Do first when the v0 boards arrive.)*
2. **Glow-look check on a 0.4 mm coupon** — the 0.8 mm v0 won't predict the 0.4 mm V1 diffusion.
3. **MCU power-down datasheet pull** → lock the MCU (§4).
4. **V1 placement pass** — 4 cells + protected glow band + SMD (§1), on the recovered source or
   straight into KiCad.
5. **4-layer route + DRC in KiCad** — with deliberate plane voids at the glow windows (§5).
6. **Shell-ready rules** baked in (§6): castellation-drop flag, GND-only pillar landings, Kapton.

---

## References

- Recovered generator: `solar-glow-drh-pcb-generator-revJ.zip` (real placement/artwork baseline).
- Layout study: `solar-glow-drh-v1-layout-study.png`.
- Supercap: `datasheets/typ_SCPC-2.pdf` (3-153-438 = WS17; shared WS10/13/17 land).
- Detail docs: `V1-PLAN.md` (§1a options/budget), `solar-glow-drh-v1-punchlist.md` (§1–§7),
  `enclosure/ENCLOSURE-NOTES.md` (parked).
- MCU gate: `AVR64DD28` datasheet — Power-Down current, **to pull**.
