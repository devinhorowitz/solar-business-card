/*
 * main.c  --  SOLAR-GLOW DRH v4.0 firmware top level.
 *
 * Behaviour
 * ---------
 * The card sleeps in POWER-DOWN almost all the time. Four things wake it:
 *   - TAP      (ADXL367 tap -> INT1 -> PF0, rising)      -> full breathing glow
 *   - MOTION   (ADXL367 activity -> INT2 -> PF1, rising) -> one soft breath
 *   - NFC      (NT3H2211 field detect -> FD -> PA6, both edges) -> while the reader's
 *                field is present the LEDs are held dark (a clean 13.56 MHz band for the
 *                tag's reply) and the core stays quiet; the acknowledge glow fires when
 *                the field leaves (FD rising), rate-limited by USE_NFC_ACK_COOLDOWN so a
 *                parked, re-polling phone can't bleed the reserve breath by breath
 *   - PIT tick (RTC, ~1 s, runs in power-down)          -> sample light, and
 *                if we just crossed dark->light, do a glow
 * All of these pin interrupts sense fully asynchronously, so they wake the core
 * even with CLK_PER stopped (datasheet 18.3.3.1).
 *
 * The NFC tag (NT3H2211) is power-gated by NFC_EN (PA7) and OFF by default to kill
 * its ~195 uA idle draw; VCC is only switched on around an I2C access (provisioning).
 * FD-wake still works while VCC is gated off: the FD pin is operated from the
 * phone's own field power (datasheet 8.4), so a tap pulls PA6 low with the chip's
 * VCC off, and field-present is the chip's POR/config default (no I2C setup needed).
 * A phone also reads the static vCard via RF with VCC off.
 *
 * Every glow is gated by the rail-voltage floor: if the supercap is below
 * VS_GLOW_FLOOR_MV we stay dark and let it charge, so an animation can never
 * brown the part out mid-breath.
 *
 * Two hardware gates are invisible to this code and documented in the README:
 *   - SW2 (master anode switch): OFF -> no LED current, no matter what TCA does.
 *   - the accel itself is the only "button"; there is no GPIO button in v4.0.
 *
 * Bring-up order below follows hardware doc section 7 exactly.
 */
#include <avr/io.h>
#include <avr/interrupt.h>
#include <avr/sleep.h>
#include <avr/cpufunc.h>
#include <avr/wdt.h>      /* wdt_reset() == WDR; enable is via WDT.CTRLA below */

#include "board.h"
#include "twi.h"
#include "adxl367.h"
#include "led.h"
#include "sense.h"
#include "nfc.h"
#include "fram.h"

static volatile uint8_t f_tap;     /* PF0 click   */
static volatile uint8_t f_motion;  /* PF1 activity */
static volatile uint8_t f_tick;    /* RTC PIT     */
static volatile uint8_t f_nfc;     /* PA6 NFC field-detect (FD, field-powered) */
static volatile uint8_t f_fd_arrived;  /* FD fell since the last poll tick -- the held-field
                                        * backstop's arrival record (2026-08-01 pressure-test
                                        * fix): without it, a tick landing mid-read re-enabled
                                        * the DCDC the FD ISR had just quieted, because the
                                        * backstop tested only the instantaneous level while
                                        * its own comment promised "a full poll later". */

#if USE_FACEDOWN_DORMANT
/* face-down dormant state (main-context only, not shared with any ISR -> no volatile).
 * dormant = every glow suppressed until turned face-up; facedown_polls = consecutive
 * face-down polls counted toward FACEDOWN_DORMANT_POLLS. */
static uint8_t  dormant;
static uint16_t facedown_polls;
#endif

#if USE_DARK_DORMANT
/* dark dormant (the in-a-bag/pocket co-condition; board.h has the design). Orientation-
 * independent companion to face-down dormancy: continuously dark for DARK_DORMANT_POLLS
 * -> suppress the MOTION and NFC-ack glows outright, and rate-limit the TAP glow (a tap
 * always glows and ends dormancy, which must then be re-earned). Exits on any lit poll.
 * Main-context only. */
static uint8_t  dark_dormant;
static uint16_t dark_polls;          /* consecutive dark polls toward DARK_DORMANT_POLLS */
#endif

/* (A shipping/"coma" mode lived here for part of 2026-08-02 -- 48 h of dark dropping the
 * accel to standby, disabling the WDT and slowing the PIT to 32 s ticks. Removed: this card
 * is hand-delivered, so the dark-shipping-box premise never occurs, and a mode that changes
 * the poll rate, the watchdog and the accel's power state is a lot of failure surface to
 * carry for a scenario that does not happen. Dark dormancy above is the stowage answer that
 * does. See feature-roadmap.md for the full decision record.) */

/* ---------------- init ---------------- */

static void clocks_init(void)
{
    /* F_CPU = 1 MHz for low per-burst active draw (the core only runs in brief
     * bursts and sleeps through the glow). AVR-EA: OSCHF has NO runtime FRQSEL
     * (unlike the DD) -- the base frequency comes from the OSCCFG fuse
     * (OSCHFFRQ: 20 MHz default, 16 MHz fused) and CLK_PER is set by the main
     * prescaler. The fuse plan sets OSCHFFRQ = 16 MHz (see Makefile `fuses`),
     * so 16 MHz / 16 = exactly 1 MHz here. UNTIL that fuse is burned the base
     * is 20 MHz -> CLK_PER = 1.25 MHz: nothing breaks (TWI runs ~125 kHz, still
     * in every device's spec; delays run ~20% short), but burn the fuse before
     * trusting any timing-derived bench number. */
    _PROTECTED_WRITE(CLKCTRL.MCLKCTRLB, CLKCTRL_PDIV_DIV16_gc | CLKCTRL_PEN_bm);
    /* Timebase: CLK_PER cycles amounting to >= 1 us, used by the ADC's internal
     * start-up/settle sequencing (DS40002443 12.3.6). 2 covers both the fused
     * 1 MHz (2 us) and the pre-fuse 1.25 MHz (1.6 us); a too-large value only
     * lengthens the ADC start-up by microseconds. */
    _PROTECTED_WRITE(CLKCTRL.MCLKTIMEBASE, 2);
    /* (DD-era SLPCTRL.VREGCTRL PMODE tuning removed: the EA has no VREGCTRL --
     * its regulator manages sleep modes automatically.) */
}

static void gpio_init(void)
{
    /* accel interrupt inputs on PF0/PF1: input (default), rising-edge sense.
     * INT pads are push-pull active-high, so no pull resistor. */
    PORTF.PIN0CTRL = PORT_ISC_RISING_gc;   /* INT1 / tap      */
    PORTF.PIN1CTRL = PORT_ISC_RISING_gc;   /* INT2 / activity */
    /* NFC power-gate enable on PA7 (NFC_EN, active-HIGH): drive LOW = NFC VCC off.
     * Set OUT low first, then DIR out, so the pin never glitches HIGH. VCC is only
     * powered transiently around an I2C access (nfc_power_on/off). */
    NFC_EN_PORT.OUTCLR = NFC_EN_PIN_bm;
    NFC_EN_PORT.DIRSET = NFC_EN_PIN_bm;
    /* NFC field-detect on PA6: input, BOTH-edges sense. FD is field-powered
     * (datasheet 8.4), so it wakes us even with NFC VCC gated off; the chip's
     * POR/config default already pulls FD low on field-present, so no I2C setup is
     * needed. Both edges because we act on each: FALLING (field arrives) -> the LED
     * layer blanks and the core goes quiet for the read; RISING (field leaves) ->
     * fire the acknowledge glow. FD is open-drain; PA6's internal pull-up is the SOLE
     * hold (no external FD pull-up in the design) so the pin can't float, at the cost
     * of a little extra sink only while FD is held low. */
    FD_PORT.PIN6CTRL = PORT_ISC_BOTHEDGES_gc | PORT_PULLUPEN_bm;
    /* PD2 (VSENSE) is analog only: disable its digital input buffer so the
     * Schmitt trigger doesn't toggle (and burn current) on a slow mid-rail
     * analog level. ADC/AC read the analog path regardless of this bit. */
    PORTD.PIN2CTRL = PORT_ISC_INPUT_DISABLE_gc;
    /* LED pins + TCA routing are owned by led_init(); I2C pins by PORTMUX below. */
    PORTMUX.TWIROUTEA = PORTMUX_TWI0_ALT2_gc;   /* SDA=PC2, SCL=PC3 */

    /* Tie down every unused pin. A floating CMOS input draws shoot-through current
     * in its buffer whenever it drifts near mid-rail; a pull-up holds it high at ~0
     * current (and for PA5, the no-fit button pin whose future switch ties to GND, and the unrouted PC0/PC1 spares, that
     * is also the useful resting state). The pins configured above (PA6/PA7/PD2/PF0/
     * PF1) and the LED pins (PA0-3, in led_init) are left alone; a pull-up bit on a
     * driven output is ignored anyway. On the AVR-EA, PD0 IS bonded (pin 10 -- the
     * pad that was VDDIO2 on the DD28). The DD-era SJ1 strap is gone outright
     * (deleted from schematic and board 2026-07-30; was DNP before that), but the
     * pad is NOT bare: C3 (100 nF to GND, the DD-era VDDIO2 decoupler) still hangs
     * on its net. A capacitor defines no DC level, so the pull-up below is still
     * the required hold -- it just also charges C3 once at boot (~3.5 ms through
     * the ~26k pull). ("Floats / no external connection" here until the 2026-08-01
     * pressure test; C3 is a cull candidate for the next passives pass.)
     * PD3..PD7 exist on the 28-pin EA and are unused. */
    /* EN_STO_CH gate (PA4): push-pull drive of Q2, the low-side charge-disable buffer
     * (cold-start-deadlock fix -- board.h has the full story). Gate LOW at init = Q2 off =
     * AEM charging ENABLED (also the R18-pulled dead-MCU state, so init changes nothing
     * observable). The FD ISR raises it to quiet the DCDC during an NFC read. */
    ENSTOCH_PORT.OUTCLR = ENSTOCH_PIN_bm;    /* gate low = charging enabled */
    ENSTOCH_PORT.DIRSET = ENSTOCH_PIN_bm;    /* push-pull from here on */
    PORTA.PIN5CTRL = PORT_PULLUPEN_bm;   /* PA5/BTN no-fit button pin: pull-up is the active-low hold for a future PA5->GND switch */
    PORTC.PIN0CTRL = PORT_PULLUPEN_bm;   /* PC0 spare, unrouted */
    PORTC.PIN1CTRL = PORT_PULLUPEN_bm;   /* PC1 spare, unrouted */
    PORTD.PIN0CTRL = PORT_PULLUPEN_bm;   /* PD0/3-7 unused      */
    PORTD.PIN1CTRL = PORT_ISC_INPUT_DISABLE_gc;   /* PD1 = AIN1 STO_SNS analog in (R15/R16 divider) */
    PORTD.PIN3CTRL = PORT_PULLUPEN_bm;
    PORTD.PIN4CTRL = PORT_PULLUPEN_bm;
    PORTD.PIN5CTRL = PORT_PULLUPEN_bm;
    PORTD.PIN6CTRL = PORT_PULLUPEN_bm;
    PORTD.PIN7CTRL = PORT_PULLUPEN_bm;
    PORTF.PIN6CTRL = PORT_PULLUPEN_bm;   /* PF6/RST: input-only GPIO (RSTPINCFG=0), no external net -- hold it */
}

/* PIT period selectors, named once so rtc_pit_init() and the face-down deep-sleep
 * transition cannot drift apart. The PIT runs off the 1.024 kHz ULP oscillator, so
 * the cycle count IS the period in units of ~0.977 ms; CYC1024 ~ 1 s. */
#if   POLL_PERIOD_S == 1
#  define NORMAL_PIT_gc  RTC_PERIOD_CYC1024_gc      /* 1024 / 1.024 kHz = 1.0 s */
#elif POLL_PERIOD_S == 2
#  define NORMAL_PIT_gc  RTC_PERIOD_CYC2048_gc      /* 2048 / 1.024 kHz = 2.0 s */
#else
#  error "POLL_PERIOD_S must be 1 or 2 (RTC PIT poll period, seconds)."
#endif

#if USE_FACEDOWN_DEEPSLEEP
#  if   FACEDOWN_POLL_S == 2
#    define FACEDOWN_PIT_gc  RTC_PERIOD_CYC2048_gc
#  elif FACEDOWN_POLL_S == 4
#    define FACEDOWN_PIT_gc  RTC_PERIOD_CYC4096_gc
#  elif FACEDOWN_POLL_S == 8
#    define FACEDOWN_PIT_gc  RTC_PERIOD_CYC8192_gc
#  else
#    error "FACEDOWN_POLL_S must be 2, 4 or 8 -- and <= the ~8 s watchdog period, which stays armed."
#  endif
#  if FACEDOWN_POLL_S < POLL_PERIOD_S
#    error "FACEDOWN_POLL_S below POLL_PERIOD_S would make the OFF state poll FASTER than normal."
#  endif
#endif

static void rtc_pit_init(void)
{
    /* 1.024 kHz internal ULP clock (runs in power-down). Period from the
     * POLL_PERIOD_S knob so the config actually takes effect. */
    RTC.CLKSEL = RTC_CLKSEL_OSC1K_gc;
    while (RTC.PITSTATUS & RTC_CTRLBUSY_bm) { }
    RTC.PITINTCTRL = RTC_PI_bm;
    RTC.PITCTRLA = NORMAL_PIT_gc | RTC_PITEN_bm;
}

#if USE_FACEDOWN_DEEPSLEEP
/* Enter/leave the face-down low-power profile -- the card's off switch. board.h's
 * USE_FACEDOWN_DEEPSLEEP block has the reasoning and the numbers; these are the two
 * transitions, and they must stay exact mirrors of each other or the card comes back
 * from face-down in a half-configured state. */
static void facedown_deepsleep(uint8_t on)
{
    if (on) {
        /* CHARGING FIRST, and this ordering is load-bearing. The FD ISR is what
         * re-enables the AEM after a read (gate LOW = charging on), and we are about
         * to stop servicing FD edges entirely. If a reader's field happened to be
         * present as dormancy began, the gate would be HIGH and nothing would ever
         * lower it -- a card that has quietly stopped harvesting for as long as it
         * lies face-down, which is the exact opposite of what this mode is for.
         * Force it on before the pin goes deaf. */
        ENSTOCH_PORT.OUTCLR = ENSTOCH_PIN_bm;
        FD_PORT.PIN6CTRL = PORT_ISC_INPUT_DISABLE_gc;   /* pull-up + buffer off: kills the FD leak */
        FD_PORT.INTFLAGS = FD_PIN_bm;                   /* drop any edge latched on the way down */
        f_nfc = f_fd_arrived = 0;
        adxl367_lowpower(1);                            /* 12.5 Hz, tap engine off */
        while (RTC.PITSTATUS & RTC_CTRLBUSY_bm) { }
        RTC.PITCTRLA = FACEDOWN_PIT_gc | RTC_PITEN_bm;
    } else {
        while (RTC.PITSTATUS & RTC_CTRLBUSY_bm) { }
        RTC.PITCTRLA = NORMAL_PIT_gc | RTC_PITEN_bm;
        adxl367_lowpower(0);                            /* back to 100 Hz + tap */
        FD_PORT.PIN6CTRL = PORT_ISC_BOTHEDGES_gc | PORT_PULLUPEN_bm;
        FD_PORT.INTFLAGS = FD_PIN_bm;                   /* re-enabling the pull-up lifts the pin;
                                                         * that edge is our own doing, not a field */
        f_nfc = f_fd_arrived = 0;
    }
}
#endif

/* ---------------- sleep ---------------- */

static void go_to_sleep(void)
{
    /* NFC_EN MUST be LOW before any sleep: cut the tag's VCC so it cannot draw its
     * ~195 uA across the sleep. (After provisioning it is already off; this is the
     * hard guarantee of the invariant.) */
    nfc_power_off();
    /* Power-Down is the baseline: lowest current. It still wakes on the accel pin
     * interrupts and the RTC PIT -- and on FD (PA6), which the phone's field drives
     * even though we just cut the tag's VCC (FD is field-powered, datasheet 8.4). */
    slp_set_mode(SLEEP_MODE_PWR_DOWN);
    cli();
    if (!f_tap && !f_motion && !f_tick && !f_nfc) {
        slp_enable();
        sei();              /* SEI + SLEEP is atomic: a pending IRQ runs after SLEEP, no missed wake */
        sleep_cpu();
        slp_disable();
    } else {
        sei();
    }
}

/* ---------------- FRAM archival hook (default OFF; see USE_FRAM_LOG) ---------------- */

#if USE_FRAM_LOG
/* Cold-boot counter in the FRAM "black box" (U7, 64 KB on always-on VS -- this
 * line said VNFC, the pre-2026-07-23 rail, until the 2026-08-01 pressure test;
 * the same paragraph already had it right below). FeRAM has ~1e13
 * write endurance and commits with no settle delay, so -- unlike the 512 B internal-
 * EEPROM loggers -- a plain read-modify-write needs no wear or corruption-window
 * guard. Record layout at addr 0: [0..3] magic 'DRHb', [4..7] big-endian boot count;
 * an absent magic (virgin / garbage FRAM) re-seeds the record at 1. Gated behind
 * USE_FRAM_LOG because archival policy still waits on the unmeasured harvest
 * budget (README "the open question") -- though the cost is now just a wake
 * (~450 us) + bus time, the part riding always-on VS since the back-power fix.
 * This is the integration scaffold: richer per-event archival hangs off the same
 * wake/read/write/sleep cycle once the budget is bench-measured. */
/* Record layout at addr 0. v1 was magic 'DRHb' + a boot count and nothing else; v2 is
 * 'DRHc' and appends four lifetime event counters. A v1 record is MIGRATED rather than
 * overwritten -- any card already carrying boot counts keeps them, and the new fields
 * start at zero. That matters because this is the black box: its whole value is that it
 * has been counting since the board's first power-up.
 *
 *   [ 0.. 3] magic 'DRHc'
 *   [ 4.. 7] cold boots        u32 BE     (v1 field, preserved across the migration)
 *   [ 8..11] taps              u32 BE
 *   [12..15] double taps       u32 BE
 *   [16..19] NFC field reads   u32 BE
 *   [20..23] motion trips      u32 BE
 */
#define REC_LEN     24
#define EV_TAP       0
#define EV_DBL       1
#define EV_NFC       2
#define EV_MOTION    3
#define EV_N         4

/* RAM shadow, committed on the poll tick. THE COMMIT CADENCE IS THE WHOLE DESIGN.
 *
 * A FRAM cycle is a wake (~450 us of ACK-polling), the bus traffic, and a re-park. Doing
 * that per EVENT would put an I2C transaction inside the tap path -- the one path this
 * firmware is most careful to keep cheap, where even a muted glow is deliberately costed
 * at a byte-compare rather than an ADC conversion. So an event costs a saturating byte
 * increment in RAM, and at most ONE FRAM cycle per ~1 s poll folds whatever accumulated
 * into the lifetime totals. A burst of taps is one cycle, not one per tap.
 *
 * The trade is a loss window: a card whose tank dies between commits loses up to a poll
 * period of events. That is the right way round. These are curios, not telemetry anyone
 * acts on, and the alternative spends real energy from an unmeasured harvest to protect
 * a tap count.
 *
 * u8 saturating: 255 events inside one poll period is already far past anything physical,
 * and saturating beats wrapping -- an implausible 255 reads better than a plausible 3. */
static uint8_t ev_pending[EV_N];

static void ev_note(uint8_t which)
{
    if (ev_pending[which] != 0xFF) ev_pending[which]++;
}

static uint32_t rec_get(const uint8_t *r, uint8_t i)
{
    const uint8_t *p = r + 4 + 4 * i;
    return ((uint32_t)p[0] << 24) | ((uint32_t)p[1] << 16) |
           ((uint32_t)p[2] <<  8) |  (uint32_t)p[3];
}

static void rec_put(uint8_t *r, uint8_t i, uint32_t v)
{
    uint8_t *p = r + 4 + 4 * i;
    p[0] = (uint8_t)(v >> 24); p[1] = (uint8_t)(v >> 16);
    p[2] = (uint8_t)(v >>  8); p[3] = (uint8_t)(v);
}

/* Read the record, migrating v1 -> v2 and re-seeding a virgin/garbage part.
 * Returns 0 on success with `rec` populated; non-zero leaves it undefined. */
static uint8_t rec_load(uint8_t *rec)
{
    if (fram_read(0x0000, rec, REC_LEN)) return 1;
    if (rec[0] == 'D' && rec[1] == 'R' && rec[2] == 'H' && rec[3] == 'c')
        return 0;                                    /* v2 already */
    if (rec[0] == 'D' && rec[1] == 'R' && rec[2] == 'H' && rec[3] == 'b') {
        rec[3] = 'c';                                /* v1: keep [4..7], zero the rest */
        for (uint8_t i = 8; i < REC_LEN; i++) rec[i] = 0;
        return 0;
    }
    rec[0] = 'D'; rec[1] = 'R'; rec[2] = 'H'; rec[3] = 'c';
    for (uint8_t i = 4; i < REC_LEN; i++) rec[i] = 0; /* virgin / garbage: start clean */
    return 0;
}

static void fram_boot_record(void)
{
    uint8_t rec[REC_LEN];

    if (fram_wake()) { fram_sleep(); return; }   /* absent -> best-effort park + skip */
    if (rec_load(rec) == 0) {
        rec_put(rec, 0, rec_get(rec, 0) + 1);    /* field 0 = cold boots */
        (void)fram_write(0x0000, rec, REC_LEN);
    }
    fram_sleep();                 /* re-park: standing cost back to IZZ (0.20 uA typ) */
}

/* Fold the RAM shadow into the lifetime totals. Called from the poll tick, and ONLY when
 * something is pending -- an idle card in a drawer must not pay a FRAM cycle a second to
 * add zero to four counters. Pending counts are cleared only after the write is accepted,
 * so a bus fault defers them to the next tick instead of dropping them. */
static void fram_events_commit(void)
{
    uint8_t rec[REC_LEN];
    uint8_t i, any = 0;

    for (i = 0; i < EV_N; i++) if (ev_pending[i]) { any = 1; break; }
    if (!any) return;

    if (fram_wake()) { fram_sleep(); return; }   /* absent: keep pending, retry next tick */
    if (rec_load(rec) == 0) {
        for (i = 0; i < EV_N; i++)
            if (ev_pending[i]) rec_put(rec, i + 1, rec_get(rec, i + 1) + ev_pending[i]);
        if (fram_write(0x0000, rec, REC_LEN) == 0)
            for (i = 0; i < EV_N; i++) ev_pending[i] = 0;
    }
    fram_sleep();
}
#endif

/* ev_note() is called from the event branches whether or not the log is built, so it has
 * to exist either way. Compiled out, it is a no-op the optimiser deletes -- which keeps
 * the call sites free of #if fences and stops the counting and the not-counting from
 * being two different control flows. */
#if !USE_FRAM_LOG
#define EV_TAP       0
#define EV_DBL       1
#define EV_NFC       2
#define EV_MOTION    3
static inline void ev_note(uint8_t which) { (void)which; }
/* Same reasoning for the commit. Its call site sits inside the FRAM_RESLEEP_EVERY_POLL
 * block, which is a SEPARATE knob -- with the log off and re-park on, an unstubbed call
 * would simply not compile. */
static inline void fram_events_commit(void) { }
#endif

/* ---------------- main ---------------- */

int main(void)
{
    uint8_t prev_light = 0;
#if USE_NFC_ACK_COOLDOWN
    uint8_t nfc_cooldown = 0;   /* polls remaining before another NFC-ack glow may fire (0 = ready) */
#endif

    clocks_init();        /* 1. clocks / power            */
    gpio_init();          /* 2. GPIO / PORTMUX            */
    led_init();
    sense_adc_init();
#if USE_HEALTH_LOG
    sense_boot_log();     /* black box: +1 the power-cycle count if this was a cold power-on (POR) */
#endif

    twi_init();           /* 3. I2C up, talk to the accel */
    (void)adxl367_init_tap();      /* full accel config; validates DEVID after its soft reset */

#if USE_FRAM_LOG
    fram_boot_record();   /* archival black box: bump the cold-boot counter (wakes + re-parks U7) */
#else
    fram_sleep();         /* POWER-CRITICAL even headless: U7 rides always-on VS and cold-boots
                           * into STANDBY (10 uA typ / 150 uA MAX) -- park it in SLEEP (0.20 uA
                           * typ) or it silently out-draws the whole standby budget. */
#endif

    /* 4. NFC tag (shares the bus) is power-gated OFF by default; we do not touch it
     * at boot. FD-wake needs no setup -- it runs on field power and the chip's POR
     * default already pulls FD low on field-present. Provisioning, when enabled,
     * powers VCC on for the write and back off after (nfc_provision_default). */
#if NFC_PROVISION
    (void)nfc_provision_default();   /* one-shot NDEF write; self-powers the tag */
#endif

    rtc_pit_init();       /* 5/6. baseline poll + housekeeping clock */

    /* the accel INT lines were indeterminate until configured just above; drop
     * any edge they may have latched into PORTF before we arm interrupts. Same for
     * any FD edge on PORTA (PA6). */
    PORTF.INTFLAGS = ACC_INT1_bm | ACC_INT2_bm;
    FD_PORT.INTFLAGS = FD_PIN_bm;
    /* ... and only THEN re-clear the accel's own event latches. Order matters:
     * adxl367_init_tap()'s trailing clears ran BEFORE the flag clear above, so a
     * real tap in between would sit latched (the ADXL367 holds INTn HIGH until
     * STATUS is read) with its one PF0 rising edge just discarded -- no new edge
     * would ever come and tap wake would be dead until the next reset. This
     * second STATUS/STATUS_2 read releases any such latch; a tap from here on
     * lands a fresh edge in the already-cleared INTFLAGS and is served normally
     * once sei() arms the ISRs. (Cost: two I2C byte reads, boot-only.) */
    adxl367_clear_tap();
    adxl367_clear_activity();
    f_tap = f_motion = f_tick = f_nfc = 0;

#if USE_WDT
    /* arm the watchdog last, once the slow bring-up (I2C config) is done so it
     * cannot trip during init. CTRLA is CCP-protected. ~8 s >> poll and glow. */
    _PROTECTED_WRITE(WDT.CTRLA, WDT_PERIOD_8KCLK_gc);
    wdt_reset();
#endif

    sei();

    /* power-on wink so a freshly programmed card shows life. Gated on a margin
     * above the glow floor (WINK_FLOOR_MV), not the floor itself, so a marginal
     * just-charged card cannot wink itself back below the floor.
     * The PEAK goes through sense_glow_peak() like every other animation, so the
     * ballast guard covers this one too. It did not until 2026-08-02: the wink
     * passed a raw GLOW_PEAK, which made "every glow's peak passes through that
     * chokepoint" false for the one glow that fires with the tank at its fullest
     * -- straight off a programmer or a bench supply, exactly the over-voltage
     * case USE_BALLAST_GUARD exists for. Costs one extra STO read at boot;
     * WINK_FLOOR_MV (3000) still gates whether the wink fires at all, since it is
     * a stricter floor than sense_glow_peak's own VS_GLOW_FLOOR_MV (2750). */
    if (sense_vdd_mv() >= WINK_FLOOR_MV) {
        uint8_t wink = sense_glow_peak(GLOW_PEAK);
        if (wink)
            led_breathe(1, GLOW_BREATH_MS, wink);
    }

    /* seed the dark->light detector with the actual boot light level, so a card
     * powered on already in light does not fire a phantom dark->light glow on the
     * first PIT tick (the wink above is the only intended power-on glow). */
    prev_light = sense_light();

    for (;;) {
#if USE_WDT
        wdt_reset();      /* pet from the loop top: a wedged main loop (even one
                           * still taking interrupts) stops petting -> reset. */
#endif
        if (f_tap) {
            f_tap = 0;
            ev_note(EV_TAP);
            uint8_t dbl = 0;
#if USE_DOUBLE_TAP
            /* The ADXL367 resolves single vs double IN HARDWARE: with both tap
             * functions enabled, the tap interrupt fires only after the double-tap
             * window has validated or invalidated, so we read STATUS_2 once here with
             * no software wait. TAP_TWO set = double. The read clears + re-arms. */
            dbl = (adxl367_read_tap() & ADXL_STATUS2_TAP_TWO_bm) != 0;
#else
            adxl367_clear_tap();                 /* drop the tap latch */
#endif
            /* free gate BEFORE the rail read (2026-08-01 pressure-test fix, all three
             * event branches): sense_glow_peak costs a full ADC + reference cold-start
             * per call, and paying it just to zero the result afterwards made every
             * muted event ~0.1 uC -- in exactly the repeat-event scenarios the mutes
             * exist to cheapen. Gate first, convert only if a glow can still fire. */
            uint8_t peak = 0;
            uint8_t mute = 0;
#if USE_FACEDOWN_DORMANT
            if (dormant) mute = 1;   /* face-down: suppress the glow + tally (latches still acked below) */
#endif
#if USE_DARK_DORMANT
            /* DARK DORMANCY RATE-LIMITS THE TAP GLOW; IT NEVER SWALLOWS ONE.
             *
             * A tap always glows and always ends dormancy, which then has to be
             * re-earned by another DARK_DORMANT_S of continuous dark. So a card
             * jostling in a bag glows at most once per ~30 min instead of once per
             * jostle -- essentially all of the leak, closed -- while a person who
             * taps the card in a dark room ALWAYS gets the monogram.
             *
             * The first cut of this required a DOUBLE tap to escape, and that was
             * wrong for a reason worth writing down: it hung the card's PRIMARY
             * interaction on LIGHT_THRESH_MV, a constant board.h itself documents as
             * having no measurement behind it ("the exact trip point is a guess").
             * If that guess reads a dim office as dark, a single tap does nothing,
             * the owner has no way to know why, and the marquee moment silently
             * fails -- a far worse outcome than the handful of stray breaths the
             * mute was saving. A feature that can only cost energy is allowed to
             * lean on an unmeasured constant; one that can silence the product is
             * not. Rate-limiting keeps the saving and removes that failure mode,
             * and it needs no single-vs-double distinction, so it behaves the same
             * with USE_DOUBLE_TAP either way. Revisit the mute only once the bench
             * has measured the dark/light threshold for real. */
            if (dark_dormant) { dark_dormant = 0; dark_polls = 0; }
#endif
            if (!mute)
                peak = sense_glow_peak(dbl ? DTAP_PEAK : GLOW_PEAK);
            if (peak) {
                /* tally BEFORE the glow: the EEPROM write then happens at the
                 * higher pre-glow rail, not after the glow has sagged it. The
                 * ~4 ms write is imperceptible ahead of the animation. peak is the
                 * rail-scaled brightness (brownout stretch), 0 below the floor.
                 * (sense_count_inc also honors EE_WRITE_FLOOR_MV: with the rail in
                 * the [glow floor, EE floor) band it banks the tap in RAM and
                 * flushes on a later safe tap -- erratum 2.2.1 discipline.) */
                sense_count_inc();
                if (dbl)
                    led_breathe(DTAP_CYCLES, DTAP_BREATH_MS, peak);  /* signature */
                else
                    led_breathe(GLOW_CYCLES, GLOW_BREATH_MS, peak);
            }
            prev_light = sense_light();
            /* a tap is also motion (and, if a phone caused it, a field event), so
             * INT2 and/or FD likely fired too. Clear both here (after the glow) so
             * the next loop does not chase the tap with a redundant breath or glow. */
            f_motion = 0;
            f_nfc = 0;
            adxl367_clear_activity();   /* a tap likely tripped activity too; ack INT2 */
        }
        else if (f_nfc) {
            f_nfc = 0;
            ev_note(EV_NFC);   /* a completed read: FD has risen, the exchange is over */
            /* the reader's field just LEFT (FD rose): the exchange is done, so it is
             * now safe to light up. Acknowledge the read with the same breath as a
             * single tap, rail-gated. During the read the LEDs were held dark (led.c
             * blanks while FD is low) and the core stayed asleep, keeping the 13.56 MHz
             * band clean for the tag's load-modulation. The phone also jostles the card,
             * so the accel motion int likely set f_motion too -- clear it after so we
             * don't chase this with a soft breath. (Deliberately NOT counted by
             * sense_count_inc(): that tracks physical taps; move it here to count reads.) */
            /* free gates BEFORE the rail read (see the tap branch): a parked, re-polling
             * phone lands here ~4x a second, and the whole point of the cooldown is that
             * the muted path costs one byte-compare -- not an ADC conversion each time. */
            uint8_t peak = 0;
            uint8_t mute = 0;
#if USE_FACEDOWN_DORMANT
            if (dormant) mute = 1;   /* face-down: no acknowledge glow */
#endif
#if USE_DARK_DORMANT
            if (dark_dormant) mute = 1;   /* stowed dark: read the vCard silently */
#endif
#if USE_NFC_ACK_COOLDOWN
            /* rate-limit: a phone parked in-field keeps polling and re-toggling FD; ack at most
             * once per NFC_ACK_COOLDOWN_S so a stowed re-poll can't bleed the reserve breath by
             * breath. The cooldown is armed only on an ack that actually fired (below). */
            if (nfc_cooldown) mute = 1;
#endif
            if (!mute)
                peak = sense_glow_peak(GLOW_PEAK);
            if (peak) {
                led_breathe(GLOW_CYCLES, GLOW_BREATH_MS, peak);
#if USE_NFC_ACK_COOLDOWN
                nfc_cooldown = NFC_ACK_COOLDOWN_POLLS;   /* arm only when we actually acked */
#endif
            }
            f_motion = 0;
            adxl367_clear_activity();
        }
        else if (f_motion) {
            f_motion = 0;
            ev_note(EV_MOTION);
            /* free gates BEFORE the rail read (see the tap branch): the pocket-walk case
             * this mute exists for fires an activity trip per jostle, and each muted trip
             * must cost a compare, not a conversion. */
            uint8_t peak = 0;
            uint8_t mute = 0;
#if USE_FACEDOWN_DORMANT
            if (dormant) {
                /* motion while dormant may be the flip back face-up: re-check Z now for an
                 * instant wake (the slowed poll is only a backstop). No glow on the wake
                 * motion itself either way. */
                if (adxl367_read_z() >= FACEDOWN_Z_THRESH) {
                    dormant = 0; facedown_polls = 0;
#if USE_FACEDOWN_DEEPSLEEP
                    facedown_deepsleep(0);   /* restore FD, accel profile and poll rate */
#endif
                }
                mute = 1;
            }
#endif
#if USE_DARK_DORMANT
            if (dark_dormant) mute = 1;   /* stowed dark: no motion breath (any orientation) */
#endif
#if USE_DARK_MOTION_MUTE
            /* Stowed in the dark (last poll saw no light): mute the *motion* soft-breath so a card
             * jostling in a pocket/bag on a walk can't fire a breath per activity trip and bleed the
             * reserve. A deliberate TAP is untouched (its branch never checks light), so the monogram
             * still lights when tapped in a dark room -- the marquee moment stays. */
            if (!prev_light)
                mute = 1;
#endif
            if (!mute)
                peak = sense_glow_peak((uint8_t)(GLOW_PEAK / 2));
            if (peak)
                led_breathe(1, GLOW_BREATH_MS, peak);
            adxl367_clear_activity();   /* ADXL367 activity latches; read STATUS to ack INT2 */
        }
        else if (f_tick) {
            f_tick = 0;
            /* Stuck-INT backstop. The ADXL367 holds INTn HIGH until its status
             * register is read, and PF0/PF1 sense RISING edges only -- so if an
             * ack ever fails (a bus fault inside adxl367_read_tap() /
             * clear_activity(), which return quietly by design), the pin stays
             * high, no further edge can ever occur, and that input is dead until
             * the next reset. Tap is the card's PRIMARY input, so it gets a
             * backstop: a pin still asserted at poll time with no flag pending
             * means exactly that failure, and re-reading the status register
             * re-arms the edge. Free in the healthy case (a PORT.IN read, no I2C)
             * and it cannot invent an event -- the glow for that tap already
             * fired; only the latch was left behind. */
            if ((ACC_PORT.IN & ACC_INT1_bm) && !f_tap)     adxl367_clear_tap();
            if ((ACC_PORT.IN & ACC_INT2_bm) && !f_motion)  adxl367_clear_activity();
            /* Held-field release. The FD handler disables AEM charging while a
             * reader's field is present (to quiet the DCDC for the read), and
             * re-enables it on the field-LEAVE edge. A field that never leaves
             * therefore never produces that edge: a phone left sitting on the
             * card, a transit gate, an always-on reader in a drawer -- and the
             * card sits with harvesting DISABLED indefinitely, unable to recharge
             * from the very light it is lying in. A read is milliseconds; a field
             * still present a full poll later is furniture, not a transaction, so
             * stop paying for it and resume charging. If it is genuinely still
             * reading, the only cost is DCDC noise during an exchange the phone
             * will retry anyway -- strictly better than never charging again.
             *
             * "A full poll later" is now actually ENFORCED (2026-08-01 pressure-test
             * fix): the PIT free-runs, so its phase is random against a phone landing
             * on the card, and the old level-only test let a tick firing ~1 ms into a
             * 100-300 ms vCard read force the DCDC back on for the rest of the
             * exchange (~1 read in 5) -- no new falling edge ever came to re-quiet it.
             * f_fd_arrived records the arrival edge; a low FD only counts as furniture
             * on a tick with NO arrival since the previous tick, guaranteeing at least
             * one full poll period of quiet before charging is forced back on. */
            if (!(FD_PORT.IN & FD_PIN_bm)) {
                if (!f_fd_arrived)
                    ENSTOCH_PORT.OUTCLR = ENSTOCH_PIN_bm;   /* held a full poll -> re-enable charging */
            }
            f_fd_arrived = 0;                                /* arm the next tick's arrival window */
#if USE_NFC_ACK_COOLDOWN
            if (nfc_cooldown) nfc_cooldown--;   /* age the NFC-ack rate-limit on the poll tick (~1 s) */
#endif
#if USE_TEMP_LOG
            /* lifetime max die temp -- self-rate-limited (samples every TEMP_SAMPLE_POLLS)
             * and writes EEPROM only on a new max. Before the dormancy gate on purpose, so a
             * baking face-down card is still logged. */
            sense_temp_log();
#endif
#if USE_HEALTH_LOG
            /* black box: lowest rail ever (RAM-tracked, committed to EEPROM only from a healthy rail)
             * plus the deferred power-cycle count. Before the dormancy gate, so a quietly-starving
             * stowed card is still tracked. Both defer their EEPROM write off a low/collapsing rail so
             * it can't corrupt (DS40002443 sec 11.3.3, "Preventing Flash/EEPROM Corruption"; the DD
             * documents the same window). */
            sense_vmin_tick();
            sense_boot_commit();   /* write a boot-flagged power cycle once the rail has charged past the write floor */
#endif
#if USE_FACEDOWN_DORMANT
            /* orientation watch. Accumulate face-down time and go dormant past the timer;
             * clear dormancy once face-up (a backstop to the motion-driven wake). While
             * dormant, skip all light/glow/sun work below -- just watch for face-up. */
            uint8_t skip = 0;
            int8_t z = adxl367_read_z();
            if (dormant) {
                if (z >= FACEDOWN_Z_THRESH) {
                    dormant = 0; facedown_polls = 0;
#if USE_FACEDOWN_DEEPSLEEP
                    facedown_deepsleep(0);
#endif
                }
                skip = 1;                                    /* resume normal work next poll */
            } else if (z < FACEDOWN_Z_THRESH) {
                if (++facedown_polls >= FACEDOWN_DORMANT_POLLS) {
                    dormant = 1; skip = 1;
#if USE_FACEDOWN_DEEPSLEEP
                    facedown_deepsleep(1);   /* the off switch: FD leak, accel and poll all down */
#endif
                }
            } else {
                facedown_polls = 0;
            }
            if (!skip)
#endif
            {
                uint8_t vf    = sense_vin_flags();               /* one VSENSE read -> light + sun */
                uint8_t light = (vf & SENSE_LIGHT_bm) ? 1u : 0u;
#if USE_SUN_DIARY
                /* bank strong-sun time -- free: the sun tell is already in vf. Independent of
                 * the glow logic below, so it also counts the greeting-edge poll. EEPROM is
                 * only written once per banked hour (sense_sun_tick handles the wear policy). */
                if (vf & SENSE_SUN_bm)
                    sense_sun_tick();
#endif
                if (light && !prev_light) {
                    uint8_t peak = sense_glow_peak(GLOW_PEAK);            /* rail-scaled (brownout stretch) */
                    if (peak)
                        led_breathe(GLOW_CYCLES, GLOW_BREATH_MS, peak);  /* dark->light greeting */
                }
#if USE_SUN_SWEEP
                /* Already lit and basking: strong sun (VIN above the sun threshold) with the caps full ->
                 * play the "loading" sweep. Caps-full (sense_caps_full()) is the hard gate, so it
                 * can never draw the pack down; it re-arms each poll, looping while the sun holds
                 * and spending the surplus harvest as light instead of leaving it unharvested. The greeting above
                 * wins on the entry edge (one breath in), then this runs while the card sits.
                 * The peak is routed through sense_glow_peak() -- the same chokepoint as
                 * every other glow -- so the ballast guard's high-STO clamp applies to the
                 * sweep too. At caps-full (>= 4.4 V) the brownout stretch returns full peak,
                 * so normal harvest is unchanged. The cost is honest: this call adds a
                 * second STO conversion on a basking poll, since sense_caps_full() just
                 * read the same node. It buys the guard's coverage on the one animation
                 * that only ever runs with a full tank, and a basking card is by definition
                 * the case where harvest is free. */
                else if ((vf & SENSE_SUN_bm) && sense_caps_full()) {
                    uint8_t sp = sense_glow_peak(SWEEP_PEAK);
                    if (sp)
                        led_sweep(SWEEP_PASSES, SWEEP_PASS_MS, sp, SWEEP_OVERLAP);
                }
#endif
                prev_light = light;
#if USE_DARK_DORMANT
                /* Dark-dormancy clock. Deliberately INSIDE the not-skip path, for two
                 * reasons: `light` is this poll's reading and already in hand, so the
                 * clock costs no extra ADC conversion; and while the card is face-down
                 * dormant every glow is suppressed anyway, so there is nothing for dark
                 * dormancy to add there. A card that is face-down dormant and then
                 * picked up in the dark starts its dark clock from that moment, which
                 * is the honest reading of "continuously dark while awake". */
                if (light) {
                    dark_dormant = 0; dark_polls = 0;      /* any light ends it, ~1 poll */
                } else if (!dark_dormant && ++dark_polls >= DARK_DORMANT_POLLS) {
                    dark_dormant = 1;
                }
#endif
            }
#if FRAM_RESLEEP_EVERY_POLL
            /* Fold this poll's events into the FRAM black box FIRST -- it leaves the
             * part parked on its own, so the defensive re-park below covers the ticks
             * where nothing was pending and the commit returned without touching the
             * bus. */
            fram_events_commit();
            /* Defensive re-park: the accel traffic this tick may have woken the
             * VS-railed FRAM to 10 uA standby (its Sleep-exit wording doesn't
             * promise address-selective wake). Two short frames, NACK-tolerant
             * if it never woke; bench may prove selectivity and flip the knob. */
            fram_sleep();
#endif
        }

        go_to_sleep();
    }
}

/* ---------------- ISRs ---------------- */

/* accel interrupts share PORTF: PF0 = tap, PF1 = activity. The snapshot ->
 * write-back order is SAFE here (unlike the FD ISR below, which must clear
 * first): a same-pin re-edge inside the ISR is impossible because the ADXL367
 * LATCHES INTn high until its STATUS/STATUS_2 register is read in the main
 * loop, and a cross-pin edge landing mid-ISR sets a bit that is 0 in `fl`, so
 * the write-1-to-clear below leaves it pending and the vector re-runs. */
ISR(PORTF_PORT_vect)
{
    uint8_t fl = PORTF.INTFLAGS;
    if (fl & ACC_INT1_bm) f_tap = 1;       /* PF0 */
    if (fl & ACC_INT2_bm) f_motion = 1;    /* PF1 */
    PORTF.INTFLAGS = fl;                   /* write-1-to-clear */
}

/* NFC field-detect on PA6 (PORTA pin-interrupt vector), both edges. FD is field-
 * powered (datasheet 8.4), so this fires even with the tag's VCC gated off, and
 * wakes the core from Power-Down. We flag f_nfc only on the RISING edge (field
 * gone) to schedule the post-read acknowledge glow. A FALLING edge (field present)
 * sets no flag -- it just wakes the core so an in-flight breath can blank (led.c
 * reads FD live) and the loop falls back to sleep, keeping the MCU quiet for the read. */
ISR(PORTA_PORT_vect)
{
    /* Clear FIRST, then act on the LIVE pin level. The old snapshot -> act ->
     * write-back order ate edges: a second FD edge landing inside the ISR set
     * the SAME already-set flag bit, and the trailing write-1 then cleared it
     * unseen -- no re-run. Losing a rising edge that chased a falling one left
     * EN_STO_CH latched high (CHARGING DISABLED) until the next NFC tap came
     * to toggle it, or until a full drain killed the MCU and R18 rescued the
     * gate. Cleared up front, any edge from here on re-pends the vector and
     * this handler runs again; acting on the level (not the edge direction)
     * makes the re-run converge on the correct final state even for a fast
     * fall+rise pair. PA6 is the only PORTA pin with interrupts enabled, and
     * an edge with the pin now high implies a field DID leave, so the ack
     * semantics of f_nfc are preserved (main rate-limits the glow anyway). */
    PORTA.INTFLAGS = FD_PIN_bm;
    if (FD_PORT.IN & FD_PIN_bm) {
        f_nfc = 1;                              /* high = field left -> post-read ack glow */
        ENSTOCH_PORT.OUTCLR = ENSTOCH_PIN_bm;   /* gate low -> Q2 off -> AEM charge resumes */
    } else {
        ENSTOCH_PORT.OUTSET = ENSTOCH_PIN_bm;   /* field present -> Q2 on -> quiet the DCDC */
        f_fd_arrived = 1;                       /* arrival record for the tick backstop: a low
                                                 * FD is only "furniture" once it has been held
                                                 * across a whole poll with no fresh arrival */
    }
}

ISR(RTC_PIT_vect)
{
    RTC.PITINTFLAGS = RTC_PI_bm;
    f_tick = 1;
}
