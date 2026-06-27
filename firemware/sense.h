/*
 * sense.h  --  analog housekeeping: rail/light ADC, AC0 light-wake, EEPROM counter.
 *
 * One pin does the light + rail-voltage sensing: PD2 = VSENSE = VIN/2 (R5/R6
 * divider, C5 filter), wired to VIN *before* the blocking Schottky D1, so it
 * sits near 0 V in the dark and rises with light. PD2 is both ADC AIN2 and
 * AC0 positive input AINP0 -- same wire, two ways to read it:
 *
 *   - sense_adc_*  : 12-bit ADC, used for the periodic poll (option B) and for
 *                    the rail-voltage brown-out guard. Enabled only for the
 *                    sample, then disabled, so it costs ~0 standing current.
 *   - sense_light_arm() : AC0 comparator (option A) for an instant light wake.
 *                    IMPORTANT: it uses VDD as the comparator reference, NOT an
 *                    internal bandgap. A bandgap ACREF would burn ~71 uA
 *                    standing (datasheet IDD_VREF) and blow the dark budget; VDD
 *                    ref is ~free. Threshold therefore tracks the rail (~12% of
 *                    VDD with the default DACREF), which is fine for light/dark.
 *
 * VDD itself is read via the ADC's internal VDD/10 channel against the 2.500 V
 * reference, giving rail millivolts for the glow floor check.
 */
#ifndef SENSE_H
#define SENSE_H

#include <stdint.h>

/* ADC: enable, 12-bit, DIV4 presc, 2.500 V ref, long sample (1M source Z). */
void     sense_adc_init(void);

/* one-shot reads, in millivolts at the real-world node:
 *   sense_vin_mv() : VIN (already x2 for the divider).
 *   sense_vdd_mv() : the MCU/supercap rail VDD (via VDD/10 channel).
 * Both enable->convert->return; cheap enough to call from the poll path. */
uint16_t sense_vin_mv(void);
uint16_t sense_vdd_mv(void);

/* true if the rail is above the glow floor (safe to run the animation). */
uint8_t  sense_rail_ok(void);

/* AC0 light wake (option A). arm before sleeping in STANDBY for instant wake
 * when light appears; disarm before deep POWER-DOWN (AC0 is off there anyway).
 * Uses VDD reference (no bandgap). */
void     sense_light_arm(void);
void     sense_light_disarm(void);

/* EEPROM lifetime activation counter (survives power loss). */
uint32_t sense_count_get(void);
void     sense_count_inc(void);

#endif /* SENSE_H */
