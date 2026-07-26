# Makefile -- SOLAR-GLOW DRH v4.0 firmware  (AVR64EA28 -- v4 family swap)
#
# Targets an AVR-Ex-capable avr-gcc (the Atmel-patched 7.3+, or any modern
# build; the EA28 is core avrxmega2) plus Microchip's AVR-Ex Device Family
# Pack (DFP). The DFP supplies the avr64ea28 device header, startup, and
# linker spec that stock avr-libc may lack.
#
#   make                # build solar-glow.hex
#   make flash          # UPDI flash via avrdude (set PROG/PORT below)
#   make fuses          # (optional) set fuses (sampled BOD, 16 MHz OSCHF, EESAVE), see note
#   make clean
#
# Point DFP at your pack, e.g.:
#   make DFP=$HOME/.local/share/packs/Microchip/AVR-Ex_DFP/2.x.x
# (Packs install from https://packs.download.microchip.com/ or via the IDE.)
#
# PORT NOTE (2026-07-23): DD28 -> EA28. This tree was COMPILE-VERIFIED against
# the AVR-Ex DFP (avr-gcc 7.3-Atmel, -Wall -Wextra -Wundef clean); the port's
# register-level changes are confined to clocks_init (fuse-based OSCHF + PDIV +
# MCLKTIMEBASE), sense.c (the EA ADC model), and the fuse plan below.

MCU      = avr64ea28
F_CPU    = 1000000

DFP      ?= /usr/share/microchip/packs/AVR-Ex_DFP
DFP_INC   = $(DFP)/include
DFP_SPEC  = $(DFP)/gcc/dev/$(MCU)

# UPDI programmer + port (TC2030 pad TC1 or header J1 -> UPDI on pin 23).
# Default flow = Adafruit UPDI Friend (DigiKey 5879): a serial-UPDI adapter with
# the loop-back resistor + a 3V/5V supply built in -> set its switch to 3V.
# A bare USB-serial + 4.7k resistor, or a pickit4/snap, also work.
PROG     ?= serialupdi
PORT     ?= /dev/ttyUSB0
BAUD     ?= 230400          # UPDI Friend documented speed; 57600 is the safe fallback

CC       = avr-gcc
OBJCOPY  = avr-objcopy
SIZE     = avr-size

CFLAGS   = -mmcu=$(MCU) -DF_CPU=$(F_CPU)UL -Os -std=gnu11 \
           -Wall -Wextra -Wundef \
           -ffunction-sections -fdata-sections \
           -B $(DFP_SPEC) -I $(DFP_INC)
LDFLAGS  = -mmcu=$(MCU) -B $(DFP_SPEC) -Wl,--gc-sections

SRC      = main.c led.c adxl367.c nfc.c fram.c sense.c
OBJ      = $(SRC:.c=.o)
TARGET   = solar-glow

.PHONY: all flash fuses clean

all: $(TARGET).hex

%.o: %.c
	$(CC) $(CFLAGS) -c -o $@ $<

# Every object depends on every header: blunt but correct for a 6-file tree
# whose headers carry code (twi.h) and tunables (board.h). Without this, an
# edited header silently leaves stale objects in an incremental build.
$(OBJ): $(wildcard *.h)

$(TARGET).elf: $(OBJ)
	$(CC) $(LDFLAGS) -o $@ $(OBJ)
	$(SIZE) $@

$(TARGET).hex: $(TARGET).elf
	$(OBJCOPY) -O ihex -R .eeprom $< $@

# EEPROM activation-counter image (optional; counter also self-seeds at runtime)
$(TARGET).eep: $(TARGET).elf
	$(OBJCOPY) -O ihex -j .eeprom --change-section-lma .eeprom=0 $< $@ || true

flash: $(TARGET).hex
	avrdude -c $(PROG) -P $(PORT) -b $(BAUD) -p $(MCU) -U flash:w:$<:i

# BOD as a SAMPLED brown-out (low duty) so it guards the rail without the continuous-BOD burden
# (EA Table 35-6: 14 uA continuous vs 0.42-0.60 uA sampled including the 32K osc).
# BODCFG (fuse 0x01) = LVL[7:5] SAMPFREQ[4] ACTIVE[3:2] SLEEP[1:0].
#   EA LADDER (DS40002443 p.~65 + 35.11): 0x0 = 1.75 V CHIP-ERASE-ONLY (normal-op LVL=0x0 = BOD
#   DISABLED -- same trap as the DD), 0x1 = 1.90 V, 0x2 = 2.60 V, 0x3 = 4.30 V. There is NO 2.45 V
#   step on the EA. Use LVL=0x2 (2.60 V typ falling, 2.47 min), SAMPFREQ=0 (128 Hz), ACTIVE=0x2
#   (sampled), SLEEP=0x2 (sampled) -> 0x4A.
#   2.60 V sits below the 2.75 V glow floor (VS_GLOW_FLOOR_MV, re-derived for the EA in board.h so a
#   glow-load sag never trips it) and above the 1.8 V core min; it also holds the core in low-current
#   reset on the slow-ramp cold-start. 1.90 V would guard EEPROM writes far too low; 4.30 V is above
#   the rail entirely.
# OSCCFG (0x02): OSCHFFRQ (bit 3) = 1 -> OSCHF base 16 MHz (default 0 = 20 MHz). clocks_init divides
#   by 16 for F_CPU = 1.000 MHz EXACTLY; without this fuse the core runs 1.25 MHz (harmless but all
#   F_CPU-derived timing is 25% fast). Burn before trusting timing-derived bench numbers.
# SYSCFG0 (0x05): factory default 0xD0 (same as the DD); set EESAVE (bit 0) to keep the EEPROM black
#   box across a UPDI chip-erase (reflash) -> 0xD1. UPDI stays usable (UPDIPINCFG default).
# SYSCFG1 (0x06): SUT only on the EA (NO MVSYSCFG -- the EA has no MVIO). Leave at factory default.
fuses:
	@echo "Set fuses deliberately; see README 'Fuses' section for the derivation."
	@echo "  avrdude -c $(PROG) -P $(PORT) -p $(MCU) -U bodcfg:w:0x4A:m   # 2.60 V sampled BOD, 128 Hz  (0x0A/LVL=0 = BOD OFF -- do NOT use)"
	@echo "  avrdude -c $(PROG) -P $(PORT) -p $(MCU) -U osccfg:w:0x08:m   # OSCHF base 16 MHz -> /16 = exactly 1 MHz (see clocks_init)"
	@echo "  avrdude -c $(PROG) -P $(PORT) -p $(MCU) -U syscfg0:w:0xD1:m  # factory 0xD0 + EESAVE (keep the black box across reflash)"
	@echo "  # syscfg1: leave at factory default (EA has no MVSYSCFG; SUT default is fine)"

clean:
	rm -f $(OBJ) $(TARGET).elf $(TARGET).hex $(TARGET).eep
