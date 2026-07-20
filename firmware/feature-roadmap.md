# SOLAR-GLOW · DRH -- firmware feature roadmap

Screened brainstorm of firmware-only features for the current **v4.0 hardware**
(AVR64DD28 + ADXL367 + NT3H2211). Source: an external brainstorm (Google Gemini),
screened here against the **as-built pin map** (`firmware/board.h`) and the project's
constraints. Nothing below requires a board re-spin -- see "Trace-change verdict."

> **The screening lens.** Per `../CLAUDE.md`, the #1 open gate is the **energy budget**
> (harvest vs. LED draw under real indoor light has never been measured). So features are
> tiered by their effect on that gate: energy-**saving** features de-risk it and come first;
> energy-**spending** features (any continuous or bursty LED draw) are gated behind the
> bench measurement.

## Disposition (2026-07-12) -- brainstorm resolved

The clean, energy-safe, no-product-decision features are **integrated**; the rest are triaged
below so this is a decision ledger, not an open list. The per-item tiers further down still hold
for detail.

- **Integrated** (default-on `board.h` knobs, all reuse reads the poll already does -- effectively
  free): sun diary, brownout-stretch brightness, face-down dormant, **dark-motion mute** (mute the
  motion breath when dark so a pocket-carry can't drain the reserve; a tap still glows), **NFC-ack
  cooldown** (rate-limit the field-leave glow to one per few seconds so a parked, re-polling phone
  can't bleed the reserve breath by breath), thermal-abuse max-temp log, and the micro-power **black
  box** (lowest-rail-ever + power-cycle count). EEPROM map: tap 0-3, sun-hours 4-5, max-temp 6,
  min-rail 7-8, power-cycles 9-10.
- **Deferred to the energy-budget bench** (the #1 gate -- these spend LED energy or need measured
  constants): zero-CPU reflex glow (EVSYS->TCA0), CCL "heartbeat" glow, ambient auto-brightness (also
  a dim-when-you-want-it risk + a lux->duty curve), shadow-abort / hardware brownout-reflex
  (AC0->CCL, plus the errata), PoV air-message, free-fall catch, FIFO air-gestures, circadian
  duty-cycling.
- **Declined after review -- conflict with the offline-first vCard** (`../TODO.md`): dynamic NDEF
  telemetry and orientation-keyed NFC. Both need a runtime NFC write that rewrites/reshapes the
  contact record. Orientation-keying would *hide* the vCard in one orientation and needs the MCU
  powered during the read (breaking the flat-card RF read -- the dead-signal case). Telemetry-on-the-
  card puts "42 taps / 51 C" on a professional contact and risks the vCard on every rewrite. The only
  safe channel for either is the tag's 64-byte **SRAM mailbox** read by a companion app (leaves the
  offline vCard untouched) -- worth building only if such an app ever exists; until then the counters
  stay UPDI-readable. Kept as a v-next revival hook, not a v4.0 feature.
- **Won't do -- a real conflict or physics wall**: the *naive* "suppress ALL glows when dark" coma
  would kill the dark-room tap-glow (VSENSE can't tell a nightstand from a pocket) -- but its clean
  distillation **shipped** as dark-motion mute above (mute only the *motion* breath when dark, always
  honor a tap; credit: Gemini's sensory-fusion reframe); mains-flicker classification (the ~3 Hz VSENSE
  low-pass attenuates
  100/120 Hz ~30x); cap-touch hover / front-face touch (the ~500 kΩ // 100 nF solar node is a poor,
  noisy electrode); analog PUF / NFC OTA / TOTP (speculative, high-effort); tally-counter LED display
  (collides with tap-to-breathe); "just-handled" thermal sense (marginal); and the novelty set
  (digital dice, secret-knock, two-way guestbook, read-receipt, VLC).

### Edge-case pass (2026-07-12) -- Gemini, verified against source

Five "sub-microamp intersection" edge cases raised; each checked against the actual `.c` / netlist /
BOM rather than the prose docs:

1. **WDT reset in the stowed-motion loop** -- *not a bug.* The watchdog is petted at the main-loop
   **top** (above the dark-motion mute), and the RTC PIT wakes the loop every 1 s in power-down, so
   the 8 s dog is fed at least once a second regardless of motion or muted breaths (animations also
   pet every ~1 ms). The premise (mute path skips the pet) doesn't match the loop structure.
2. **NFC FD interrupt-storm bleed** -- *real, low-severity; **fixed**.* A phone parked in-field keeps
   polling and re-toggles FD; every rising edge fired a fresh ack breath. Bounded by the rail floor
   (no brownout/brick) but a real slow bleed -> shipped `USE_NFC_ACK_COOLDOWN` (one ack per few s).
3. **TINY shared-ballast droop** -- *real physics, not firmware-fixable; documented.* SW2 = TINY
   shares one 220 R (`R12`) across all anodes, so per-LED brightness varies with channel count. The
   firmware can't sense SW2 and can't correct without wrecking ON mode; TINY is a dim hack by design.
   Documented as low-fidelity in `README`; **v4:** move the ballast to the individual cathodes so TINY
   is linear.
4. **Titanium eddy currents kill NFC** -- *already solved.* The `FER1` ferrite (Würth WE-FSFS 364006)
   sits in a dedicated brace channel between coil and shell; physics + no-ferrite fallback are in
   `../PCB/PCB-side-notes-brace-direction.md` §3. Underlying concern correct; the design already
   answers it.
5. **Cold-start slow-ramp stall** -- *legit bench item; captured.* Not "latch-up" but a brown-out
   stall: the MCU released by POR (~1.4 V) can draw more than a dim-light uA harvest supplies and
   stall below the operating point. The mitigation is the sampled BOD at **2.45 V** (`BODCFG=0x2A`;
   holds the core in low-current reset until 2.45 V) -- **program the fuse** (`../TODO.md`) and
   bench-verify a 0 V cold-start under dim light. *(The earlier `0x0A`/1.9 V figure was wrong: LVL=0x0
   is chip-erase-only, so `0x0A` = BOD off. See the design-notes BOD addendum.)*

## Trace-change verdict: none required

Every enabling signal is already routed on v4.0 (verified against `board.h`):

| Signal | Route | Unlocks |
|---|---|---|
| `VSENSE` = SRC/2 | PD2 = ADC **AIN2** + AC0 **AINP0** | ambient brightness, find-the-sun, shadow-abort, wake-on-light, cap-touch |
| Pack **STO** | PD1 = ADC **AIN1** (STO/3 via R15/R16, `sense_vdd_mv()`) | voltage-adaptive brightness / brownout stretch |
| NFC **FD / I²C / NFC_EN** | PA6 / PC2-PC3 / PA7 | telemetry NDEF, gesture/contextual NFC, OTA |
| Accel **INT1/INT2** + I²C | PF0/PF1 + PC2-PC3 | face-down, free-fall, FIFO gestures |
| **LEDs** | PA0-PA3 / TCA0 | all glow, VLC, CCL heartbeat |
| AVR **temp sensor** | internal | thermal logging |

Two caveats are **firmware/silicon, not board traces**: (1) the CCL "heartbeat" depends on
whether a CCL/TCA output can drive all four LED pins autonomously -- verify in firmware;
(2) the `AC0 → EVSYS → CCL` async path carries errata the firmware README already flags.
The only item that could *ever* become a board change is reliable front-face cap-touch,
which would likely want a dedicated electrode rather than reusing the solar node -- noted
under Tier 3, not pursued.

Also note: the ADXL367 **FIFO, free-fall, orientation, and temp** engines are **not
currently configured** (only tap + activity are), so any idea using them is *new firmware*,
not "just enable it."

---

## Tier 1 -- pursue now (energy wins, existing peripherals)

Each of these *reduces* draw and attacks the open energy question directly.

- **Face-down / in-pocket deep sleep.** *(**face-down half implemented** -- `USE_FACEDOWN_DORMANT`,
  `adxl367_read_z()`.)* If the card lies face-down (accel Z clearly negative) for
  `FACEDOWN_DORMANT_S` (~3 min), go dormant: suppress every glow until it is turned face-up
  again, so a stowed card can't drain the ~15 J reserve on false triggers. Reads the accel Z
  directly (no orientation-engine config needed); flip-to-wake is instant (the flip is motion)
  with the poll as a backstop. *Still open:* the `VSENSE`-dark "in a bag/pocket" co-condition.
- **Voltage-adaptive brightness (brownout stretch).** *(**implemented** -- `USE_BROWNOUT_STRETCH`,
  `sense_glow_peak()`.)* Instead of the hard cutoff at `VS_GLOW_FLOOR_MV` (2600), scale the glow
  peak down as the rail drains toward the floor (full at `VS_GLOW_FULL_MV`, dimming to
  `VS_GLOW_DIM_PEAK`). Nearly free: reuses the very rail read that already gated the glow.
- **Ambient auto-brightness.** Use the `VSENSE` ADC as a lux proxy; dim rooms need far less
  PWM through the 0.6 mm FR4. Large reserve savings for equal apparent brightness.

## Tier 2 -- backlog (good value, low / neutral energy)

- **Dynamic telemetry NDEF.** Rewrite the NFC record with lifetime tap-count (the EEPROM
  activation counter exists in `sense.c`), cap-V, and max-temp for zero-teardown health
  checks. Temp needs the internal sensor brought up.
- **"Find the sun" alignment mode.** A gesture turns the 4 LEDs into a `VSENSE` harvest
  bar-graph so a user can find a charging spot -- directly addresses the harvest problem.
- **Thermal-abuse logging.** *(**implemented** -- `USE_TEMP_LOG`, `sense_temp_log()`.)* MCU
  internal temp (pulsed ADC, 2.048 V ref + SIGROW cal per DS40002315 sec 33.3.3.8) → EEPROM
  lifetime max; matches the CLAUDE.md hot-car warning about supercap degradation. Sampled
  sparsely and written only on a new max, so near-zero energy; runs even while face-down dormant.
- **Shipping / "coma" mode.** Halt RTC/ADC, wake only on a sustained solar spike; protects
  the caps during a dark shipping box. Low effort, real value.
- **Shadow-abort (AC0 zero-cross).** Use AC0 (VSENSE on AINP0 vs. internal DAC) to halt an
  in-flight LED animation in µs when a shadow drops SRC, instead of waiting for the 1 s poll.

## Tier 3 -- defer / design-note (ambitious or energy-spending)

Gate these behind the harvest-vs-draw bench measurement or a dedicated prototyping pass.

- **Zero-power CCL "heartbeat" glow.** Elegant (design notes flag it as v-next; zero CPU via
  EVSYS→CCL), but a *continuous* LED draw is the exact energy risk. **Blocked on the budget.**
- **Free-fall "catch" animation**, **air-gestures via FIFO**, **gesture-switched / contextual
  NFC routing.** High wow, but energy bursts + new accel-FIFO / NFC-timing firmware.
- **Front-face cap-touch via AC0**, **NFC OTA firmware update**, **TOTP / crypto token.**
  Real silicon paths but speculative or high-effort; design-note before committing.

## Skip / low priority

Digital dice, secret-knock unlocks, two-way NFC guestbook, read-receipt glow, VLC optical
exfil -- fun, but they spend firmware/energy for novelty and do not move the project forward.

---

## Phase 4 -- original / deep-dive concepts

A deeper round, grounded in the as-built v4.0 (`board.h` pin map + the physical enclosure),
with feasibility limits called out where the hardware fights the idea. Tier tags use the same
energy-gate lens as Phases 1-3.

### Core-independent peripherals (the deepest energy lever)

- **Zero-CPU reflex glow (EVSYS -> TCA0)** -- Tier 1, verify. Today `main.c` wakes the CPU on
  INT1 (tap) and runs the 1.6 s cosine breath as a CPU loop. Route the accel INT1 pin-event
  through the Event System to fire a TCA0 one-shot envelope with the core in power-down.
  *Limit:* a true cosine needs the CPU updating compares, so the CPU-free path trades the
  breath for a hardware triangle/ramp (TCA0 ramp mode, or CCL off the 32 kHz ULP). The payoff
  is a budget-bench question -- the ~16 mA-peak LEDs likely dominate the 1 MHz core, so measure first.
- **Hardware brownout-reflex (AC0 -> EVSYS -> CCL -> TCA0 compares = 0)** -- Tier 2. AC0
  already has `VSENSE` on AINP0; set the internal DAC as a danger floor and force the LED
  compares to zero in hardware the instant the rail sags (µs, zero CPU). Lets animations run
  closer to the edge because the abort is guaranteed. Complements `VS_GLOW_FLOOR_MV`.

### The card as a passive logger

- **"Sun diary"** -- Tier 1, near-zero energy. *(**implemented** -- `USE_SUN_DIARY`,
  `sense_sun_tick()`.)* The poll already reads the strong-sun tell (`SENSE_SUN_bm`); bank it as an
  EEPROM counter of lifetime whole-HOURS. The in-progress hour lives in RAM and flushes once per
  hour, so EEPROM sees ~one write per sun-hour (not per second) -- endurance-safe. Surface "N
  sun-hours banked" in the NDEF later. A keepsake that records its own life in the light.
- **Micro-power "black box"** -- Tier 2. *(**implemented** -- `USE_HEALTH_LOG`, `sense_vmin_tick()` /
  `sense_boot_log()`, joining the tap / sun-hours / max-temp cells.)* An EEPROM lifecycle record:
  max temp, sun-hours, tap count, **lowest-rail-ever**, and **power-cycle (full-drain) count** (a
  cleaner starvation tell than brownout-abort count -- one write per drain, no wear). One UPDI scan
  dumps the card's history; field-failure forensics (heat vs. starved vs. shipped-dark vs. overused).

### Smarter light sensing

- **Mains-flicker light classification** -- Tier 3, hardware-limited. Detect 100/120 Hz
  AC-lighting ripple on `VSENSE` to gate the in-sun sweep to *real* sun (killing the
  bright-office false-positive). *Limit:* the VSENSE divider (~500 kΩ) into C5 = 100 nF is a
  ~3 Hz low-pass, so flicker arrives ~30x attenuated -- marginal, and it fights ADC settling.
  Bench-probe before designing around it.
- **Circadian duty-cycling** -- Tier 1/2. Log `VSENSE` light against the RTC; learn the owner's
  day/night rhythm and deep-coma during learned dark hours. Energy savings + "the card sleeps
  when the office is dark." Uses RTC/PIT + VSENSE history + EEPROM already present.

### Richer accel + LED interaction

- **Persistence-of-vision air message** -- Tier 3, burst energy. On a fast wave (accel X/Y),
  strobe the 4 LEDs timed to the swing velocity to paint the DRH monogram / a short word in the
  air. Rare, user-initiated burst.
- **Orientation-keyed NFC payload** -- Tier 2. A robust replacement for a timing-raced
  double-tap swap: key the NDEF on static orientation at FD-wake (portrait -> vCard,
  landscape -> URL). Stable, no race; the MCU rewrites block 1 before the read completes.
- **Interactive tally / fidget counter** -- Tier 2, sleeper pick. Each tap increments a count
  on the 4 LEDs (4-bit / bar), persisted in EEPROM. Cheapest idea here, maybe the stickiest --
  it keeps the card on the desk being touched, which is the whole point.

### Analog identity & physical sensing

- **Analog "fingerprint" PUF** -- Tier 3. Hash a vector of per-card analog tolerances -- the
  internal-oscillator frequency
  error, the supercap self-discharge slope -- into an EEPROM device fingerprint for an
  anti-clone NFC challenge. *Note:* LED Vf isn't ADC-reachable (LED nodes not routed to an ADC
  pin), so lean on the oscillator/cap entropy that is.
- **Thermal-mass "just handled" sense** -- Tier 2. A warm hand raises the Ti shell temp; a
  rising temp gradient vs. logged ambient, ANDed with an accel pickup, gives a genuine
  human-handoff signal (vs. a bag bump). Cheap (temp on the 1 s poll); gates the greeting glow
  to real handoffs.
- **Capacitive hover-greeting** -- Tier 3, experimental. AC0 on the solar-cell copper to glow
  "hello" as a hand approaches (pre-touch). *Limit:* the ~500 kΩ // 100 nF node (~50 ms RC) is
  a poor cap electrode -- low, noisy sensitivity. Bench-only; do not promise.

### Prioritization
Highest leverage = features that *reduce or characterize* energy while adding magic: **Sun
Diary**, **Circadian**, **zero-CPU reflex glow**. Near-zero-risk wow: **orientation-keyed
NFC**, **PoV air-message**. Sleeper: the **tally counter**.

---

*Firmware roadmap only; nothing here requires a v4.0 board re-spin. Real duty-cycle / glow numbers are
provisional until the energy-budget bench run (README → "The open question").*
