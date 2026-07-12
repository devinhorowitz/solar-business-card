# SOLAR-GLOW · DRH -- firmware feature roadmap

Screened brainstorm of firmware-only features for the **frozen v3.0 hardware**
(AVR64DD28 + ADXL367 + NT3H2211). Source: an external brainstorm (Google Gemini),
screened here against the **as-built pin map** (`firmware/board.h`) and the project's
constraints. Nothing below requires a board re-spin -- see "Trace-change verdict."

> **The screening lens.** Per `../CLAUDE.md`, the #1 open gate is the **energy budget**
> (harvest vs. LED draw under real indoor light has never been measured). So features are
> tiered by their effect on that gate: energy-**saving** features de-risk it and come first;
> energy-**spending** features (any continuous or bursty LED draw) are gated behind the
> bench measurement.

## Trace-change verdict: none required

Every enabling signal is already routed on v3.0 (verified against `board.h`):

| Signal | Route | Unlocks |
|---|---|---|
| `VSENSE` = VIN/2 | PD2 = ADC **AIN2** + AC0 **AINP0** | ambient brightness, find-the-sun, shadow-abort, wake-on-light, cap-touch |
| Rail **VS** | ADC internal **VDD/10** (`sense_caps_full()`) | voltage-adaptive brightness / brownout stretch |
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

- **Face-down / in-pocket deep sleep.** Read the accel gravity vector (needs orientation
  config) + `VSENSE`-dark; if the card is face-down or bagged, lock out tap/motion glow so
  false triggers cannot drain the ~15 J reserve. Combines Gemini's face-down + pocket ideas.
- **Voltage-adaptive brightness (brownout stretch).** Instead of the hard cutoff at
  `VS_GLOW_FLOOR_MV` (2600), linearly scale `GLOW_PEAK` down as the rail drains toward the
  floor. Nearly free: the firmware already reads the rail via VDD/10 for the floor check.
- **Ambient auto-brightness.** Use the `VSENSE` ADC as a lux proxy; dim rooms need far less
  PWM through the 0.6 mm FR4. Large reserve savings for equal apparent brightness.

## Tier 2 -- backlog (good value, low / neutral energy)

- **Dynamic telemetry NDEF.** Rewrite the NFC record with lifetime tap-count (the EEPROM
  activation counter exists in `sense.c`), cap-V, and max-temp for zero-teardown health
  checks. Temp needs the internal sensor brought up.
- **"Find the sun" alignment mode.** A gesture turns the 4 LEDs into a `VSENSE` harvest
  bar-graph so a user can find a charging spot -- directly addresses the harvest problem.
- **Thermal-abuse logging.** AVR internal temp → EEPROM lifetime max; matches the CLAUDE.md
  hot-car warning about supercap degradation.
- **Shipping / "coma" mode.** Halt RTC/ADC, wake only on a sustained solar spike; protects
  the caps during a dark shipping box. Low effort, real value.
- **Shadow-abort (AC0 zero-cross).** Use AC0 (VSENSE on AINP0 vs. internal DAC) to halt an
  in-flight LED animation in µs when a shadow drops VIN, instead of waiting for the 1 s poll.

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

A deeper round, grounded in the as-built v3.0 (`board.h` pin map + the physical enclosure),
with feasibility limits called out where the hardware fights the idea. Tier tags use the same
energy-gate lens as Phases 1-3.

### Core-independent peripherals (the deepest energy lever)

- **Zero-CPU reflex glow (EVSYS -> TCA0)** -- Tier 1, verify. Today `main.c` wakes the CPU on
  INT1 (tap) and runs the 1.6 s cosine breath as a CPU loop. Route the accel INT1 pin-event
  through the Event System to fire a TCA0 one-shot envelope with the core in power-down.
  *Limit:* a true cosine needs the CPU updating compares, so the CPU-free path trades the
  breath for a hardware triangle/ramp (TCA0 ramp mode, or CCL off the 32 kHz ULP). The payoff
  is a budget-bench question -- the ~8 mA LEDs likely dominate the 1 MHz core, so measure first.
- **Hardware brownout-reflex (AC0 -> EVSYS -> CCL -> TCA0 compares = 0)** -- Tier 2. AC0
  already has `VSENSE` on AINP0; set the internal DAC as a danger floor and force the LED
  compares to zero in hardware the instant the rail sags (µs, zero CPU). Lets animations run
  closer to the edge because the abort is guaranteed. Complements `VS_GLOW_FLOOR_MV`.

### The card as a passive logger

- **"Sun diary"** -- Tier 1, near-zero energy. The firmware already detects basking (VIN past
  `SWEEP_SUN_VIN_MV` + `sense_caps_full()`). Accumulate that condition as an EEPROM sun-seconds
  counter on the existing 1 s poll; surface "N sun-hours banked" in the NDEF. A keepsake that
  records its own life in the light.
- **Micro-power "black box"** -- Tier 2. Extend telemetry into an EEPROM lifecycle record: max
  temp, sun-hours, tap count, lowest-rail-ever, brownout-abort count. One scan dumps the card's
  history; doubles as field-failure forensics (heat vs. shipped-dark).

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
  TLV3011 clamp trip (AC0/DAC sweep vs. the held rail), the internal-oscillator frequency
  error, the supercap self-discharge slope -- into an EEPROM device fingerprint for an
  anti-clone NFC challenge. *Note:* LED Vf isn't ADC-reachable (LED nodes not routed to an ADC
  pin), so lean on the clamp/oscillator/cap entropy that is.
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

*Firmware roadmap only; the v3.0 hardware stays frozen. Real duty-cycle / glow numbers are
provisional until the energy-budget bench run (README → "The open question").*
