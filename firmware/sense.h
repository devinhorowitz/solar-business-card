/*
 * sense.h  --  analog housekeeping: rail/light ADC + EEPROM counter.
 *
 * One pin does the light + rail-voltage sensing: PD2 = VSENSE = VIN/2 (R5/R6
 * divider, C5 filter), tapped off the SRC (solar) node, so it
 * sits near 0 V in the dark and rises with light. PD2 is ADC AIN2.
 *
 * Light is read by the ADC on the ~1 s PIT poll: a dark->light rise drives the
 * glow. (There is deliberately NO AC0-comparator "instant" light wake: on this
 * part the AC interrupt/flags do not update with CLK_PER stopped, so an AC
 * interrupt cannot wake from Standby or Power-Down -- see datasheet 32.3.5 vs.
 * the AC.CTRLA.RUNSTDBY bit description and the Table 13-4 wake-source list,
 * which omits the AC. Instant interaction-wake is covered by the accelerometer
 * motion interrupt instead. See README.)
 *
 * STO (the supercap tank) is read on PD1/AIN1 through the R15/R16 (2M/1M)
 * divide-by-3 against the 2.048 V reference and scaled back by STO_DIVIDER,
 * giving tank millivolts for the glow floor check (VS is now the constant LDO rail).
 */
#ifndef SENSE_H
#define SENSE_H

#include <stdint.h>

/* Configure the ADC: 12-bit, DIV2 presc, 2.048 V reference (NOT 2.500 V -- that
 * option is out of spec below VDD 3.0 V and this card runs to 2.6 V; see the
 * ADC_VREF_MV block in sense.c), long SAMPDUR (1M
 * source Z); reference settling is hardware-sequenced into each conversion on
 * the EA. Leaves the ADC disabled; each read powers it (and the reference) up
 * for the conversion and back down after, so the analog domain draws nothing
 * between polls. */
void     sense_adc_init(void);

/* one-shot reads, in millivolts at the real-world node:
 *   sense_vin_mv() : VIN (already x2 for the divider).
 *   sense_vdd_mv() : the supercap tank STO (via the R15/R16 divide-by-3 on PD1/AIN1).
 * Both power the ADC + reference up for the conversion and back down after.
 * NOTE the recurring paths deliberately do NOT use these: the poll reads light+sun
 * via sense_vin_flags() and the rail/caps gates via sense_rail_ok()/sense_caps_full(),
 * all raw-count (no mV math). These mV accessors are the human-readable siblings --
 * sense_vdd_mv() backs the boot wink; sense_vin_mv() mirrors, in real millivolts, the
 * exact VIN the sweep trigger tests (SWEEP_SUN_VIN_MV) for UPDI/debug readout, so it
 * reads as uncalled on-chip BY DESIGN (like sense_count_get); keep it. */
uint16_t sense_vin_mv(void);
uint16_t sense_vdd_mv(void);

/* light-present predicate for the ~1 s poll: compares the raw VSENSE ADC count
 * against LIGHT_THRESH_MV folded to a count at COMPILE time, so the hot path
 * skips the per-poll mV conversion. Bit-identical result to the old
 * (sense_vin_mv() >= LIGHT_THRESH_MV * VSENSE_DIVIDER). */
uint8_t  sense_light(void);

/* sense_vin_flags(): one VSENSE read returning both predicates as bit flags, for the
 * poll spot that needs light AND strong-sun together (the in-sun sweep). Both are
 * raw-count compares (no mV math); SENSE_SUN_bm implies SENSE_LIGHT_bm. */
#define SENSE_LIGHT_bm  0x01u   /* VSENSE pin >= LIGHT_THRESH_MV (VIN/2)  (any light)  */
#define SENSE_SUN_bm    0x02u   /* VIN >= SWEEP_SUN_VIN_MV                (strong sun) */
uint8_t  sense_vin_flags(void);

/* true if the rail is above the glow floor (safe to run the animation). */
uint8_t  sense_rail_ok(void);

/* Rail-adaptive glow peak: returns `peak` scaled down by how close the rail sits to
 * the glow floor (brownout stretch, see USE_BROWNOUT_STRETCH), or 0 below the floor so
 * a caller keeps the `if (peak) glow` shape. One STO/3 read (PD1/AIN1) -- the SAME cost as the
 * sense_rail_ok() gate it replaces at the breath sites. With USE_BROWNOUT_STRETCH=0 it
 * is exactly that gate: `peak` above the floor, 0 below. */
uint8_t  sense_glow_peak(uint8_t peak);

/* true if the caps are full (VS >= SWEEP_CAPS_FULL_MV): the in-sun sweep's hard gate,
 * so the animation can never draw the pack down. Raw-count, same STO/3 channel as
 * sense_rail_ok(). */
uint8_t  sense_caps_full(void);

/* EEPROM lifetime activation counter (survives power loss). */
uint32_t sense_count_get(void);
void     sense_count_inc(void);

/* EEPROM sun diary (USE_SUN_DIARY): lifetime whole-hours of strong sun.
 *   sense_sun_tick() : call once per poll while the SENSE_SUN_bm tell is set; it counts
 *                      the partial hour in RAM and writes EEPROM only on each hour rolled
 *                      over (so ~one write per banked hour, not per poll -- endurance).
 *   sense_sun_hours_get() : the banked whole-hour count (survives power loss; the
 *                      in-progress partial hour is RAM-only and lost on a full drain).
 * Like sense_count_get, the getter is uncalled on-chip BY DESIGN (UPDI/NDEF readout);
 * --gc-sections drops it if nothing references it. */
uint16_t sense_sun_hours_get(void);
void     sense_sun_tick(void);

/* MCU internal die temperature + EEPROM lifetime-max log (USE_TEMP_LOG).
 *   sense_temp_c()       : one-shot die temperature in degrees C (pulsed ADC read against
 *                          the internal 1.024 V ref + SIGROW cal, per DS40002443 sec 31.3.3.7).
 *                          Returns INT16_MIN on a stuck ADC.
 *   sense_temp_log()     : call every poll; samples sparsely (every TEMP_SAMPLE_POLLS) and
 *                          writes EEPROM only when a new lifetime max is seen.
 *   sense_temp_max_get() : the stored lifetime max in degrees C (signed; erased EEPROM = -1).
 *                          Uncalled on-chip BY DESIGN (UPDI/NDEF readout), like sense_count_get. */
int16_t  sense_temp_c(void);
void     sense_temp_log(void);
int8_t   sense_temp_max_get(void);

/* EEPROM "black box" (USE_HEALTH_LOG): lowest rail ever + power-cycle count. Both defer their EEPROM
 * write to a healthy rail (>= EE_WRITE_FLOOR_MV) so a write never lands on a collapsing rail (the
 * corruption window, DS40002443 sec 11.3.3): the min-rail is tracked in RAM and committed on recovery,
 * and the power-cycle count is flagged at boot and committed once the rail has charged.
 *   sense_vmin_tick()      : call every poll; samples VS every VMIN_SAMPLE_POLLS, keeps the RAM min, commits when safe.
 *   sense_vmin_get()       : lowest rail mV ever seen (0xFFFF = never sampled).
 *   sense_boot_log()       : call once at boot; flags a power-on reset (POR) for a deferred +1 to the power-cycle count.
 *   sense_boot_commit()    : call every poll; writes the flagged power cycle once the rail is safe.
 *   sense_boot_count_get() : power-cycle (full-drain) count (erased EEPROM = 0).
 * The getters are uncalled on-chip BY DESIGN (UPDI/NDEF readout), like sense_count_get. */
uint16_t sense_vmin_get(void);
void     sense_vmin_tick(void);
void     sense_boot_log(void);
void     sense_boot_commit(void);
uint16_t sense_boot_count_get(void);

#endif /* SENSE_H */
