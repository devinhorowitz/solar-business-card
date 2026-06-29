# Makefile -- SOLAR-GLOW DRH v2.1 firmware
#
# Targets a MODERN avr-gcc (>= ~12, with AVR-Dx support) plus Microchip's
# AVR-Dx Device Family Pack (DFP). The DFP supplies the avr64dd28 device
# header, startup, and linker spec that stock avr-libc may lack.
#
#   make                # build solar-glow.hex
#   make flash          # UPDI flash via avrdude (set PROG/PORT below)
#   make fuses          # (optional) set fuses (sampled BOD, MVSYSCFG, EESAVE), see note
#   make clean
#
# Point DFP at your pack, e.g.:
#   make DFP=$HOME/.local/share/packs/Microchip/AVR-Dx_DFP/2.x.x
# (Packs install from the Microchip pack server or via the toolchain IDE.)
#
# NOTE: this tree was written and verified at the register level but was NOT
# compile-tested in its authoring environment (no AVR-Dx DFP available there).
# Expect to point DFP at a real pack; the code uses only standard DFP macros.

MCU      = avr64dd28
F_CPU    = 1000000

DFP      ?= /usr/share/microchip/packs/AVR-Dx_DFP
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

SRC      = main.c led.c lis2dh12.c nfc.c sense.c
OBJ      = $(SRC:.c=.o)
TARGET   = solar-glow

.PHONY: all flash fuses clean

all: $(TARGET).hex

%.o: %.c
	$(CC) $(CFLAGS) -c -o $@ $<

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

# Optional: enable BOD as a SAMPLED brown-out (low duty) so it guards the rail
# without the ~17 uA of continuous BOD. Confirm the exact BODCFG byte for your
# desired level/sample-rate against the datasheet before flashing this.
#   ACTIVE=SAMPLED, SLEEP=SAMPLED, SAMPFREQ + LVL bits -> see BODCFG fuse table.
fuses:
	@echo "Set fuses deliberately; see README 'Fuses' section for the full set."
	@echo "Compute whole-byte values from the datasheet fuse tables, then e.g.:"
	@echo "  avrdude -c $(PROG) -P $(PORT) -p $(MCU) -U bodcfg:w:0xXX:m   # sampled BOD"
	@echo "  avrdude -c $(PROG) -P $(PORT) -p $(MCU) -U syscfg1:w:0xXX:m  # MVSYSCFG=SINGLE"
	@echo "  avrdude -c $(PROG) -P $(PORT) -p $(MCU) -U syscfg0:w:0xXX:m  # EESAVE (keep counter)"

clean:
	rm -f $(OBJ) $(TARGET).elf $(TARGET).hex $(TARGET).eep
