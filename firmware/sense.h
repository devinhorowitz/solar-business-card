/*
 * sense.h  --  analog housekeeping: rail/light ADC + EEPROM counter.
 *
 * One pin does the light + rail-voltage sensing: PD2 = VSENSE = VIN/2 (R5/R6
 * divider, C5 filter), wired to VIN *before* the blocking Schottky D1, so it
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
 * VDD itself is read via the ADC's internal VDD/10 channel against the 2.500 V
 * reference, giving rail millivolts for the glow floor check.
 */
#ifndef SENSE_H
#define SENSE_H

#include <stdint.h>

/* Configure the ADC: 12-bit, DIV2 presc, 2.500 V reference, long sample (1M
 * source Z), reference-settling INITDLY. Leaves the ADC disabled; each read
 * powers it (and the reference) up for the conversion and back down after, so
 * the analog domain draws nothing between polls. */
void     sense_adc_init(void);

/* one-shot reads, in millivolts at the real-world node:
 *   sense_vin_mv() : VIN (already x2 for the divider).
 *   sense_vdd_mv() : the MCU/supercap rail VDD (via VDD/10 channel).
 * Both power the ADC + reference up for the conversion and back down after;
 * cheap enough to call from the poll path. */
uint16_t sense_vin_mv(void);
uint16_t sense_vdd_mv(void);

/* true if the rail is above the glow floor (safe to run the animation). */
uint8_t  sense_rail_ok(void);

/* EEPROM lifetime activation counter (survives power loss). */
uint32_t sense_count_get(void);
void     sense_count_inc(void);

#endif /* SENSE_H */
