/*
 * sense.c  --  ADC rail/light reads + EEPROM activation counter.  (AVR-EA ADC)
 *
 * Power policy: the ADC and its 2.048 V reference are powered only for the
 * length of a conversion and shut off immediately after (see adc_read_raw).
 * Between the ~1 s polls the ADC ENABLE bit is 0, which draws no ADC current,
 * and the internal reference is released with it. The analog domain therefore
 * contributes essentially nothing to sleep current.
 *
 * The cost of that policy is that the reference is cold-started on every read.
 * On the EA this wait is sequenced by HARDWARE: with LOWLAT = 0 the analog
 * blocks power up per conversion and the ADC inserts the required start-up /
 * settle time itself, timed off CLKCTRL.MCLKTIMEBASE (set in clocks_init; see
 * DS40002443 12.3.6 and the ADC chapter) -- the DD-era INITDLY sizing is gone.
 *
 * Port note (DD -> EA): same 12-bit result semantics and the same MUXPOS
 * channel numbers (PD1 = AIN1, PD2 = AIN2), so every compile-time COUNT fold
 * below carries over unchanged. The EA's PGA / differential / accumulation
 * modes are deliberately NOT used yet -- these are large ground-referenced
 * divider signals and the poll wants the cheapest possible read; burst
 * accumulation is a bench-era upgrade (see TODO).
 */
#include <avr/io.h>
#include <avr/eeprom.h>
#include <avr/interrupt.h>
#include <avr/sleep.h>
#include "board.h"
#include "sense.h"

/* ADC reference -> mV per LSb at 12-bit = ADC_VREF_MV/4096. Every threshold in
 * this file is folded from this constant at compile time, so the reference and
 * the thresholds can never drift apart.
 *
 * WHY 2.048 V AND NOT 2.500 V (2026-07-26 audit -- this was a SAFETY defect).
 * DS40002443A Table 35-17 constrains the internal references two ways:
 *   - the 2.500 V reference is specified only for "3.0V <= VDD <= 5.5V" (+/-3%,
 *     -40..+85 C; +/-5% to +125 C), and
 *   - VVREF "Internal voltage reference" carries Max = "VDD-0.4" V.
 * This card is DESIGNED to operate below 3.0 V: the glow floor is STO 2.75 V and
 * the BOD does not trip until 2.60 V typ. At VDD = 2.75 V the second constraint
 * caps the reference at 2.35 V, so a 2.500 V selection cannot be delivered -- it
 * sags. A sagging reference inflates every count (count = Vin/VREF * 4096), which
 * makes a LOW rail read HIGH: the exact wrong direction. Worked through, the
 * 2750 mV glow floor actually tripped at ~2582 mV of STO -- BELOW the 2.60 V BOD
 * -- so the brownout guard was inverted and a glow could drive the part into a
 * reset mid-animation, precisely the failure VS_GLOW_FLOOR_MV exists to prevent.
 * The 2.048 V reference is specified for "2.55V <= VDD <= 5.5V" at a TIGHTER
 * +/-2% -- in spec across effectively the whole operating range, with one honest
 * corner (corrected 2026-08-01, pressure test; "stays in spec below the BOD trip"
 * was overstated): BODLEVEL2's falling trip is 2.43 V MIN / 2.60 V typ
 * (DS80001048C clarification), and the ADC chapter's own rule is stricter than
 * the VREF table's VDD-0.4 -- "An internal reference can be used only if it is
 * below VDD - 0.5V" -- so a min-corner part can run VDD 2.43-2.55 V where the
 * 2.048 V reference is out of spec on both counts, and a sagging reference reads
 * a LOW rail HIGH. The exposure is narrow (an LDO-dropout rail inside a 120 mV
 * band on a worst-case BOD part, vs the 450 mV always-on inversion the 2.500 V
 * pick had) and every floor in this file sits at STO >= 2.75 V, comfortably
 * above the band -- but it is a corner, not zero, and it belongs on the page.
 * The reference still clears every divider's full swing:
 *   STO  4.65 V (VOVCH) / 3 = 1.55 V  <  2.048 V   -- no clipping
 *   VIN  4.096 V         / 2 = 2.048 V             -- see the caveat below
 * CAVEAT: VSENSE (VIN/2) now saturates above VIN = 4.096 V, just under the
 * SM141K06TF's 4.15 V Voc. Nothing that matters is affected -- the sun gate is
 * SWEEP_SUN_VIN_MV 3600 (pin 1800 mV) and LIGHT_THRESH_MV 400 -- only the
 * human-readable sense_vin_mv() readout flattens in the last 54 mV below Voc,
 * a node that is only ever near Voc at open circuit. Do NOT "fix" that by going
 * back to 2.500 V: the rail gates matter and the Voc readout does not. */
#define ADC_VREF_MV   2048UL

/* ---------- ADC (AVR-EA model: PRESC in CTRLB, REFSEL in CTRLC, SAMPDUR in
 * CTRLE, mode+start in COMMAND; reference settle is hardware-sequenced) ---------- */

void sense_adc_init(void)
{
    ADC0.CTRLB   = ADC_PRESC_DIV2_gc;          /* 1 MHz / 2 = 500 kHz CLK_ADC.
                                                * DIV2 is the ONLY legal prescaler at
                                                * CLK_PER 1 MHz: Table 35-24 specifies
                                                * CLK_ADC as 300..2000 kHz with an
                                                * internal reference, so DIV4 (250 kHz)
                                                * is BELOW the minimum -- an earlier
                                                * comment here called it "also legal",
                                                * which was wrong. DIV1 (1 MHz) is in
                                                * range too but buys nothing. */

    /* Reference: internal 2.048 V (NOT 2.500 V -- see ADC_VREF_MV above; the
     * 2.500 V option is out of spec below VDD 3.0 V and this card runs to 2.6 V).
     * Selected in the ADC itself on the EA. It powers up with the ADC per
     * conversion and is released when the ADC is disabled (LOWLAT stays 0 = no
     * standing analog current). */
    ADC0.CTRLC   = ADC_REFSEL_2V048_gc;

    /* Long sample time. NOTE the often-quoted reason -- "the 1M//1M divider is
     * ~500k source impedance" -- is NOT what governs here: BOTH analog nodes carry a
     * 100 nF reservoir (C5 on VSENSE, C24 on STO_SNS, verified against the board), and
     * 100 nF utterly dominates the few-pF sample capacitor, so charge sharing settles
     * in well under a microsecond regardless of the divider. The real reasons to keep
     * SAMPDUR = 31 (62 us) are that it costs nothing at a 1 Hz poll and that the temp
     * sensor REQUIRES >= 32 us (DS40002443 31.3.3.7). The higher-impedance channel is
     * in fact STO_SNS (2M||1M = 667k), which three of the four rail gates read -- also
     * covered, for the same reason. */
    ADC0.CTRLE   = 31;                         /* SAMPDUR */

    /* Leave the ADC DISABLED between reads: each read enables it, converts,
     * and disables it again. Resolution is per-conversion on the EA (the
     * COMMAND MODE field in adc_read_raw), not a CTRLA setting. */
    ADC0.CTRLA   = 0;                          /* ENABLE = 0, LOWLAT = 0 */
}

/* Result-ready wakes the core out of the IDLE nap in adc_read_raw. The ISR only
 * clears the flag and records completion; the caller reads the result from RES
 * after the wake. */
static volatile uint8_t adc_done;

ISR(ADC0_RESRDY_vect)
{
    ADC0.INTFLAGS = ADC_RESRDY_bm;     /* write-1-to-clear */
    adc_done = 1;
}

static uint16_t adc_read_raw(uint8_t muxpos)
{
    uint16_t res = 0;

    ADC0.CTRLA   |= ADC_ENABLE_bm;     /* power up ADC (analog start-up is
                                        * hardware-sequenced off MCLKTIMEBASE) */
    ADC0.MUXPOS   = muxpos;            /* single-ended: MUXNEG ignored, DIFF=0 */
    ADC0.INTFLAGS = ADC_RESRDY_bm;     /* clear any stale result-ready flag */
    adc_done      = 0;
    ADC0.INTCTRL  = ADC_RESRDY_bm;     /* wake on result-ready */
    /* one 12-bit single-ended conversion, started now; hardware inserts the
     * cold-start settle before sampling (LOWLAT = 0 path). */
    ADC0.COMMAND  = ADC_MODE_SINGLE_12BIT_gc | ADC_START_IMMEDIATE_gc;

    /* Conversion = start-up + SAMPDUR + ~13.5 CLK_ADC, a few hundred us here.
     * IDLE-sleep through it rather than spinning the core in active mode: the ADC
     * keeps converting in IDLE and RESRDY wakes us (same race-free SEI+SLEEP idiom
     * as the glow). RESRDY is the first wake in the healthy case; a stray PIT/accel
     * wake just re-checks the flag and sleeps again. The guard bounds a stuck ADC
     * (RESRDY never arrives) to 3 wakes, then bails with RESULT 0 -- reads as low
     * rail / dark, fail-safe no glow. NOTE the bound is 3 WAKES, not a time: on a
     * dark, motionless card the only Idle wake is the PIT, so a stuck read costs up
     * to ~3 poll periods, and a tick that chains several reads (temp + vmin + light)
     * can then outrun the 8 s WDT -> watchdog reset. That is the intended recovery
     * for dead analog (reinit everything), not a hang -- the WDT is the designed
     * backstop here, not a bystander. */
    slp_set_mode(SLEEP_MODE_IDLE);
    for (uint8_t guard = 0; guard < 3 && !adc_done; guard++) {
        cli();
        if (adc_done) { sei(); break; }
        slp_enable();
        sei();                         /* SEI + SLEEP is atomic: no missed RESRDY */
        sleep_cpu();
        slp_disable();
    }
    ADC0.INTCTRL = 0;                  /* stop the ADC interrupt */
    if (adc_done)
        res = (uint16_t)ADC0.RESULT;   /* 12-bit single fits the low half; reading
                                        * RESULT also clears RESRDY */

    ADC0.CTRLA   &= ~ADC_ENABLE_bm;    /* power down ADC; reference released */
    return res;
}

uint16_t sense_vin_mv(void)
{
    uint32_t res = adc_read_raw(VSENSE_AIN);                 /* AIN2 = PD2 */
    uint32_t mv  = (res * ADC_VREF_MV) >> 12;                /* /4096 */
    return (uint16_t)(mv * VSENSE_DIVIDER);                  /* x2 -> VIN */
}

/* Light-present threshold as a raw 12-bit ADC count, folded at COMPILE time from
 * the board's mV threshold. VSENSE reads the pin (= VIN/2) and LIGHT_THRESH_MV is
 * that pin threshold, so count c means pin_mv = c*ADC_VREF_MV/4096; thus
 * pin_mv >= LIGHT_THRESH_MV  <=>  c >= ceil(LIGHT_THRESH_MV*4096/ADC_VREF_MV).
 * That is the SAME boolean the old (sense_vin_mv() >= LIGHT_THRESH_MV*VSENSE_DIVIDER)
 * produced (the divider's x2 cancels the threshold's x2), for every threshold value. */
#define LIGHT_COUNT \
    ((uint16_t)(((uint32_t)LIGHT_THRESH_MV * 4096UL + (ADC_VREF_MV - 1UL)) / ADC_VREF_MV))

uint8_t sense_light(void)
{
    /* one ADC read (same sampling as sense_vin_mv), compared raw -- no mV math. */
    return (adc_read_raw(VSENSE_AIN) >= LIGHT_COUNT) ? 1u : 0u;
}

/* Strong-sun threshold as a raw 12-bit count, folded at COMPILE time like LIGHT_COUNT.
 * One wrinkle: LIGHT_THRESH_MV is already a pin voltage, but SWEEP_SUN_VIN_MV is stated
 * at the VIN node, so this also divides by VSENSE_DIVIDER (pin_mv = VIN_mv/VSENSE_DIVIDER).
 * A count c means pin_mv = c*ADC_VREF_MV/4096, so c >= SUN_COUNT is exactly
 * VIN >= SWEEP_SUN_VIN_MV. With ADC_VREF_MV = 2048 and VSENSE_DIVIDER = 2 the fold
 * collapses to count == VIN in mV exactly (3600 mV -> 3600), since (VIN/2)/2048*4096 = VIN.
 * (Was 2950 / the VIN_mV*0.8192 rule under the old 2.500 V reference.) */
#define SUN_COUNT \
    ((uint16_t)(((uint32_t)SWEEP_SUN_VIN_MV * 4096UL + (VSENSE_DIVIDER * ADC_VREF_MV - 1UL)) \
                / (VSENSE_DIVIDER * ADC_VREF_MV)))

/* One VSENSE read -> both the light and strong-sun predicates (SENSE_LIGHT_bm /
 * SENSE_SUN_bm), each a raw-count compare so the ~1 s poll does no mV math. SUN
 * implies LIGHT (SUN_COUNT > LIGHT_COUNT). The poll uses this where it needs both;
 * the pure-light baselines keep sense_light(). */
uint8_t sense_vin_flags(void)
{
    uint16_t raw = adc_read_raw(VSENSE_AIN);
    uint8_t  f   = 0;
    if (raw >= LIGHT_COUNT) f |= SENSE_LIGHT_bm;
    if (raw >= SUN_COUNT)   f |= SENSE_SUN_bm;
    return f;
}

uint16_t sense_vdd_mv(void)
{
    /* v4: VS is now the regulated LDO rail (constant), so read the supercap top STO
     * instead -- via the R15/R16 (2M/1M) divider on PD1/AIN1 (pin sees STO/STO_DIVIDER).
     * Same divider-pin form as sense_vin_mv(): STO_mv = pin_mv * STO_DIVIDER. */
    uint32_t res = adc_read_raw(STO_SNS_AIN);               /* PD1/AIN1 = STO / STO_DIVIDER */
    uint32_t mv  = (res * ADC_VREF_MV) >> 12;
    return (uint16_t)(mv * STO_DIVIDER);                    /* undo the divider -> STO mV */
}

/* Rail-floor threshold as a raw STO-divider count, folded at COMPILE time (same
 * divider-pin form as SUN_COUNT). STO_mv = c*ADC_VREF_MV/4096 * STO_DIVIDER, so
 *   sense_vdd_mv() >= VS_GLOW_FLOOR_MV  <=>  c >= ceil(VS_GLOW_FLOOR_MV*4096/(STO_DIVIDER*ADC_VREF_MV)).
 * Same fail-safe: a stuck ADC reads 0 -> below floor -> no glow. */
#define RAIL_COUNT ((uint16_t)(((uint32_t)VS_GLOW_FLOOR_MV * 4096UL + (STO_DIVIDER*ADC_VREF_MV - 1UL)) \
                               / (STO_DIVIDER*ADC_VREF_MV)))

uint8_t sense_rail_ok(void)
{
    /* raw STO-divider (PD1/AIN1) count vs compile-time floor -- same result as sense_vdd_mv() >= floor,
     * same fail-safe (a stuck ADC reads 0 -> not ok -> no glow). */
    return (adc_read_raw(STO_SNS_AIN) >= RAIL_COUNT) ? 1u : 0u;
}

/* Caps-full gate for the in-sun sweep: STO at/above SWEEP_CAPS_FULL_MV. Same STO-divider
 * channel and compile-time fold as RAIL_COUNT, just a higher floor; same fail-safe (a stuck
 * ADC reads 0 -> not full -> no sweep). Only ever called after the SUN flag is set, so the
 * extra STO read stays off the common poll path. */
#define CAPS_FULL_COUNT ((uint16_t)(((uint32_t)SWEEP_CAPS_FULL_MV * 4096UL + (STO_DIVIDER*ADC_VREF_MV - 1UL)) \
                                    / (STO_DIVIDER*ADC_VREF_MV)))

uint8_t sense_caps_full(void)
{
    return (adc_read_raw(STO_SNS_AIN) >= CAPS_FULL_COUNT) ? 1u : 0u;
}

/* EEPROM write-safety gate: rail at/above EE_WRITE_FLOOR_MV, so a ~4 ms EEPROM write can start and
 * finish without the rail collapsing through it (the corruption window, DS40002443 sec 11.3.3,
 * "Preventing Flash/EEPROM Corruption"; the DD documents the same window). The
 * BOD only ABORTS an in-progress write; this is the firmware "don't start near the edge" guard (the
 * VLM's role), so it holds between the sampled BOD's checks. Same STO-divider channel and compile-time
 * fold as the other rail gates; same fail-safe -- a stuck ADC reads 0 -> not safe -> no write. */
#define EE_SAFE_COUNT ((uint16_t)(((uint32_t)EE_WRITE_FLOOR_MV * 4096UL + (STO_DIVIDER*ADC_VREF_MV - 1UL)) \
                                  / (STO_DIVIDER*ADC_VREF_MV)))

static uint8_t sense_ee_safe(void)
{
    return (adc_read_raw(STO_SNS_AIN) >= EE_SAFE_COUNT) ? 1u : 0u;
}

/* ---------- rail-adaptive glow brightness (brownout stretch) ---------- */

/* Scale a requested glow peak by rail headroom: full `peak` at/above VS_GLOW_FULL_MV, a
 * straight-line ramp down to a dim floor as the rail sags to VS_GLOW_FLOOR_MV, and 0 below
 * the floor (the caller then skips the glow). This turns the old hard cliff -- full peak
 * right up to the floor, then nothing -- into a graceful fade that also stretches the
 * reserve, since a dimmer near-empty breath spends less charge. The dim floor is
 * VS_GLOW_DIM_PEAK on GLOW_PEAK's scale, re-scaled here to whatever base `peak` was asked
 * for, so a half-bright breath (the motion soft breath) dims in proportion too. Costs one
 * STO-divider read -- the same read sense_rail_ok() did at these sites; with the stretch off it
 * IS sense_rail_ok() (peak above the floor, 0 below). */
uint8_t sense_glow_peak(uint8_t peak)
{
#if USE_BROWNOUT_STRETCH
    uint16_t mv = sense_vdd_mv();
    if (mv <  VS_GLOW_FLOOR_MV) return 0;                     /* below floor: dark, let it charge */
    if (mv >= VS_GLOW_FULL_MV)  return peak;                  /* healthy rail: full brightness    */
    /* linear ramp between the dim floor and `peak`. dim < peak always (VS_GLOW_DIM_PEAK <
     * GLOW_PEAK), so peak-dim never underflows; span is a positive compile-time constant. */
    uint8_t  dim  = (uint8_t)(((uint16_t)peak * VS_GLOW_DIM_PEAK) / GLOW_PEAK);
    uint16_t over = mv - VS_GLOW_FLOOR_MV;
    uint16_t span = VS_GLOW_FULL_MV - VS_GLOW_FLOOR_MV;
    return (uint8_t)(dim + (uint32_t)(peak - dim) * over / span);
#else
    return sense_rail_ok() ? peak : 0u;                      /* original hard cutoff at the floor */
#endif
}

/* ---------- EEPROM lifetime activation counter ---------- */

/* Address 0 in the EEPROM address space -- NOT a RAM null pointer. avr-libc's
 * eeprom_*_dword take an address within EEPROM, where 0 is the first cell; the
 * (uint32_t *) cast is the avr-libc idiom for that, not a null-pointer deref. */
#define EE_COUNT_ADDR  ((uint32_t *)0)     /* 4-byte counter at EEPROM offset 0 */

/* Read the lifetime tap counter. The firmware only ever increments it at runtime
 * (sense_count_inc); this reader exists for external readout over UPDI/debug and
 * future use -- uncalled on-chip BY DESIGN, kept as API (--gc-sections drops it if
 * it stays unused). Not dead code. */
uint32_t sense_count_get(void)
{
    return eeprom_read_dword(EE_COUNT_ADDR);
}

void sense_count_inc(void)
{
    /* The tap tally honors the same EE_WRITE_FLOOR_MV discipline as the other
     * writers (it was historically the ONE ungated site): a glow is allowed from
     * the 2750 mV glow floor, but with the rail in [glow floor, EE floor) the
     * write would start at VDD ~2.7 V -- erratum 2.2.1 territory on Rev. B1 until
     * the BODLEVEL2 fuse (its sanctioned workaround) is burned, and outside
     * board.h's stated invariant either way. So: bank the tap in RAM and flush
     * the batch on a later tap from a healthy rail. Only a card whose last-ever
     * taps all landed in that 100 mV band loses counts -- a keepsake-grade loss.
     * NOTE `pending` is a plain static in .bss, so it does NOT survive a reset: a
     * brown-out or watchdog reset between banking and flushing drops up to 255 taps.
     * Deliberate -- the alternative (an EEPROM write per tap) is the wear the RAM
     * bank exists to avoid, and the counter is a keepsake, not an odometer.
     * Costs one extra STO read per tap, trivial next to the glow it precedes. */
    static uint8_t pending;                /* taps banked below the EE write floor */
    if (pending < 0xFFu) pending++;        /* saturate: 255 unflushed taps is already pathological */
    if (!sense_ee_safe())
        return;
    uint32_t c = eeprom_read_dword(EE_COUNT_ADDR);
    if (c == 0xFFFFFFFFUL) c = 0;          /* erased EEPROM reads all-ones */
    c += pending;
    pending = 0;
    eeprom_update_dword(EE_COUNT_ADDR, c); /* update = no write if unchanged */
}

/* ---------- EEPROM sun diary (lifetime strong-sun hours) ---------- */

/* A card that runs on harvested light may as well remember how much light it has lived
 * in. The poll already computes the strong-sun tell (SENSE_SUN_bm); main.c calls
 * sense_sun_tick() on every poll where it is set. The catch is EEPROM endurance (~100k
 * writes): ticking a cell once per ~1 s poll would wear it out in a day of sun. So the
 * partial hour is accumulated in RAM (sun_polls) and EEPROM is touched only when a whole
 * hour rolls over -- lifetime writes then equal lifetime sun-hours (tens of thousands
 * across a card's years, comfortably under endurance). The RAM count is lost on a full
 * supercap drain, so at most the current sub-hour (< 1 h) is forgotten across a drain --
 * fine for a whole-hours keepsake. Not shared with any ISR, so no volatile needed. */
#define EE_SUN_HOURS_ADDR  ((uint16_t *)4)   /* 2-byte counter at EEPROM offset 4 (past the dword tap count at 0) */
#define SUN_POLLS_PER_HOUR ((uint16_t)(3600UL / POLL_PERIOD_S))   /* strong-sun polls that make one banked hour */

static uint16_t sun_polls;                   /* strong-sun polls counted in the current partial hour */
static uint8_t  hours_pending;               /* whole hours completed but not yet committed (rail below the EE floor) */

/* Banked whole-hours of strong sun. Erased EEPROM reads all-ones -> report 0. Uncalled
 * on-chip BY DESIGN (UPDI/NDEF readout), like sense_count_get; kept as API. */
uint16_t sense_sun_hours_get(void)
{
    uint16_t h = eeprom_read_word(EE_SUN_HOURS_ADDR);
    return (h == 0xFFFFu) ? 0u : h;
}

void sense_sun_tick(void)
{
    /* Bank COMPLETED HOURS, not just one. The rollover must always reset sun_polls
     * and credit an hour; only the EEPROM COMMIT waits for a safe rail. Getting this
     * wrong (saturating sun_polls at the rollover and returning) silently discarded
     * every hour after the first for as long as the rail stayed low -- exactly the
     * cold-start case of strong sun on a deeply drained tank, where VIN is high while
     * STO is still under the floor, i.e. the longest sun spells were the ones least
     * likely to be counted. Same shape as the tap tally above, for the same reason. */
    if (++sun_polls < SUN_POLLS_PER_HOUR)
        return;                              /* still inside the current hour */
    sun_polls = 0;
    if (hours_pending < 0xFFu) hours_pending++;   /* saturate: 255 unflushed hours is already pathological */
    /* Rail gate, same as every other writer (board.h EE_WRITE_FLOOR_MV). Checked only
     * when there is something to flush, so a low rail costs no ADC conversion here. */
    if (!sense_ee_safe())
        return;                              /* hours stay banked -- retry next rollover */
    uint16_t h = sense_sun_hours_get();
    uint16_t room = (uint16_t)(0xFFFEu - h);   /* headroom to the ceiling; h <= 0xFFFE always
                                                * (the getter maps erased 0xFFFF to 0), so this
                                                * never underflows */
    uint16_t add = (hours_pending < room) ? hours_pending : room;
    /* WRAP-FREE saturation (2026-08-01 pressure test; found independently by two
     * lenses, confirmed by disassembly). The old form `if (h + add > 0xFFFEu)`
     * computed h+add in 16-bit unsigned, so at the ceiling it wrapped instead of
     * clamping: h=0xFFFE with two banked hours summed to 0 -- the guard passed and
     * the diary was OVERWRITTEN WITH ZERO, the one outcome the clamp exists to
     * prevent. sense_boot_commit below always had the wrap-free idiom; now both do.
     * Pending hours are dropped once consumed OR unrecordable-at-ceiling, so a
     * permanently saturated diary stops paying the ee-safe ADC read every hour. */
    if (add)
        eeprom_update_word(EE_SUN_HOURS_ADDR, (uint16_t)(h + add));
    hours_pending = 0;
}

/* ---------- MCU internal die temperature + lifetime-max log ---------- */

/* One-shot die temperature in degrees C via the on-chip sensor, per DS40002443 sec 31.3.3.7
 * (AVR-EA). The EA specifies the sensor against the internal 1.024 V reference (the DD used
 * 2.048 V), so bracket the read with a CTRLC reference switch and restore it after; SAMPDUR
 * is already 31 cyc = 62 us, satisfying the sensor's >= 32 us rule, so only the reference and
 * MUXPOS change. The per-part factory calibration lives in SIGROW.TEMPSENSE0/1 -- both SIGNED
 * on the EA -- and the datasheet arithmetic is (raw + offset) * slope / 4096 -> Kelvin (note:
 * the DD formula was (offset - raw); they are NOT interchangeable). Widened to int32 so the
 * intermediate cannot wrap. Pulsed like every other read -> no standing current (unlike the
 * accel's TEMP_EN). Returns INT16_MIN on a stuck ADC (RESULT stayed 0). */
int16_t sense_temp_c(void)
{
    ADC0.CTRLC = ADC_REFSEL_1V024_gc;                       /* temp-sensor reference (EA: 1.024 V) */
    uint16_t raw = adc_read_raw(ADC_MUXPOS_TEMPSENSE_gc);   /* 12-bit, right-adjusted */
    ADC0.CTRLC = ADC_REFSEL_2V048_gc;                       /* restore for rail/light reads (see ADC_VREF_MV) */
    if (raw == 0) return INT16_MIN;                         /* stuck ADC -> sentinel (max logger ignores) */
    int32_t offset = (int16_t)SIGROW.TEMPSENSE1;            /* signed offset correction */
    int32_t slope  = (int16_t)SIGROW.TEMPSENSE0;            /* signed gain/slope correction */
    int32_t k = (((int32_t)raw + offset) * slope + 2048) / 4096;   /* -> Kelvin (SCALING_FACTOR 4096) */
    return (int16_t)(k - 273);                              /* Kelvin -> Celsius */
}

/* 1-byte signed lifetime-max temperature (deg C) at EEPROM offset 6 (past the dword tap count
 * at 0 and the sun-hours word at 4-5). Erased EEPROM reads 0xFF = -1 C, a harmless cold floor. */
#define EE_TMAX_ADDR  ((uint8_t *)6)

void sense_temp_log(void)
{
    static uint8_t ctr;
    static int8_t  tmax_ram = -128;                /* session max in RAM; committed to EEPROM only from a safe rail */
    if (++ctr < TEMP_SAMPLE_POLLS)
        return;                                    /* not time to sample yet */
    ctr = 0;
    int16_t c = sense_temp_c();
    if (c == INT16_MIN)                            /* stuck ADC -> skip this sample */
        return;
    if (c > 127) c = 127;                          /* clamp into the signed-byte store */
    if ((int16_t)c > tmax_ram) tmax_ram = (int8_t)c;   /* track the true max in RAM -- wear-free, rail-safe */
    /* commit a new lifetime max only from a healthy rail: a heat spell can coincide with a draining
     * rail (a dark hot car), and an EEPROM write on a collapsing rail can corrupt (DS40002443 sec
     * 11.3.3). The RAM max means a peak-while-low is still written once the rail recovers, not lost. */
    int8_t stored = (int8_t)eeprom_read_byte(EE_TMAX_ADDR);
    if ((int16_t)stored < tmax_ram && sense_ee_safe())
        eeprom_update_byte(EE_TMAX_ADDR, (uint8_t)tmax_ram);
}

int8_t sense_temp_max_get(void)
{
    return (int8_t)eeprom_read_byte(EE_TMAX_ADDR);
}

/* ---------- EEPROM "black box" -- lowest rail ever + power-cycle count ---------- */

/* Lowest TANK voltage (STO, mV) ever seen -- the starvation half of the field black box (max-temp
 * is the heat half). ("VS" here until the 2026-08-01 audit -- v3 prose; the read below has always
 * been sense_vdd_mv() = STO, the informative node now that VS is the constant LDO rail.)
 * Sampled sparsely (every VMIN_SAMPLE_POLLS; the supercap sags over minutes). The catch
 * is that a "new low" is by definition the WORST moment to write EEPROM -- a ~4 ms write on a
 * collapsing rail can corrupt (DS40002443 sec 11.3.3; the DD documents the same window). So the running low is tracked in RAM (vmin_ram,
 * wear-free and safe at any rail) and only COMMITTED to EEPROM from a healthy rail (>= EE_WRITE_FLOOR_MV).
 * A recoverable sag is thus captured and written once the rail climbs back; only a terminal drain
 * below the floor goes unrecorded, which is unavoidable. Erased EEPROM reads 0xFFFF, a perfect "no low
 * yet" ceiling. Called every poll before the dormancy gate, so a stowed card quietly starving is still
 * tracked (and committed if it recovers). */
#define EE_VMIN_ADDR  ((uint16_t *)7)   /* 2-byte min-rail mV at EEPROM offset 7 (past max-temp at 6) */

static uint16_t vmin_ctr;
static uint16_t vmin_ram = 0xFFFF;      /* lowest rail this power session, RAM-tracked (no low-rail EEPROM write) */

void sense_vmin_tick(void)
{
    if (++vmin_ctr < VMIN_SAMPLE_POLLS)
        return;                                   /* not time to sample yet */
    vmin_ctr = 0;
    uint16_t mv = sense_vdd_mv();
    if (mv == 0) return;                          /* stuck ADC -> skip */
    if (mv < vmin_ram) vmin_ram = mv;             /* track the true low in RAM -- always safe, wear-free */
    /* commit only from a healthy rail, so the write never lands on the sag itself (the corruption
     * window); erased 0xFFFF is the ceiling -> the first real low wins. */
    if (mv >= EE_WRITE_FLOOR_MV && vmin_ram < eeprom_read_word(EE_VMIN_ADDR))
        eeprom_update_word(EE_VMIN_ADDR, vmin_ram);
}

uint16_t sense_vmin_get(void)
{
    return eeprom_read_word(EE_VMIN_ADDR);        /* 0xFFFF = never sampled */
}

/* Power-cycle (full-drain) count: +1 per cold power-on. A supercap that fully drains and recharges
 * cold-boots the MCU (power-on reset); watchdog / UPDI / brown-out-recovery resets do NOT count.
 * sense_boot_log() reads and clears RSTCTRL.RSTFR at boot so only a genuine POR is flagged, but it
 * DEFERS the EEPROM write: a cold boot happens right at the reset-release voltage (a poor moment for
 * a ~4 ms write), so sense_boot_commit() does the write once the rail has charged past the write
 * floor. One write per drain, and drains are rare, so endurance is a non-issue. */
#define EE_BOOT_ADDR  ((uint16_t *)9)   /* 2-byte power-cycle count at EEPROM offset 9 */

static uint8_t boot_pending;            /* a power-on reset seen at boot, awaiting a safe rail to record */

void sense_boot_log(void)
{
    uint8_t fr = RSTCTRL.RSTFR;
    RSTCTRL.RSTFR = fr;                           /* write-1-to-clear the flags we just latched */
    if (fr & RSTCTRL_PORF_bm)                     /* a power-on reset = a real power cycle */
        boot_pending = 1;                         /* record it once the rail can take a clean write */
}

void sense_boot_commit(void)
{
    if (!boot_pending || !sense_ee_safe())        /* wait for a healthy rail before the write */
        return;
    boot_pending = 0;
    uint16_t n = sense_boot_count_get();
    if (n < 0xFFFEu)                              /* saturate (never store 0xFFFF, which reads as 0) */
        eeprom_update_word(EE_BOOT_ADDR, (uint16_t)(n + 1u));
}

uint16_t sense_boot_count_get(void)
{
    uint16_t n = eeprom_read_word(EE_BOOT_ADDR);
    return (n == 0xFFFFu) ? 0u : n;              /* erased EEPROM reads all-ones */
}
