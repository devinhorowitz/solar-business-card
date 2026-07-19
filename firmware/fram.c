/*
 * fram.c  --  MB85RC512TY (512 kbit = 64 KB I2C FeRAM) bring-up + linear R/W.
 *
 * Transactions are the datasheet ones, built on the twi.h primitives. The read
 * follows the standard "set the 16-bit address pointer, then read" idiom: an
 * address phase (SA+W, addrHi, addrLo) followed by a repeated START with SA+R
 * for the data phase. Unlike the NFC EEPROM there is NO post-write settle delay
 * -- FeRAM commits at the STOP (datasheet: "does not need a polling sequence
 * after writing"), so fram_write returns as soon as the STOP is on the wire.
 *
 * Power: VDD rides VNFC, the SAME high-side load switch (NFC_EN / PA7) that
 * gates the NFC tag. fram_power_on() raises NFC_EN and ACK-polls; the poll is
 * bounded so an absent part / unwired EN returns a fault instead of hanging.
 * fram_power_off() drops it -- only call when neither the FRAM nor the NFC tag
 * is needed (they share the gate). See board.h / fram.h.
 */
#include "board.h"          /* FRAM_ADDR, NFC_EN_PORT / NFC_EN_PIN_bm, F_CPU */
#include "fram.h"
#include "twi.h"
#include <util/delay.h>

/* ---- power-gate timing (shared VNFC switch; mirrors nfc.c's soft-start) ---- */
#define FRAM_SOFTSTART_US     200   /* switch turn-on + FeRAM POR before first poll */
#define FRAM_BOOT_POLL_US     250   /* spacing between ACK-poll attempts            */
#define FRAM_BOOT_POLL_TRIES  20    /* ~5 ms budget for the part to answer its addr */

/* presence: 1 if the FRAM ACKs its address, else 0. Address-only ping
 * (START, SA+W, [N]ACK, STOP) -- no data written. VNFC must already be up. */
uint8_t fram_present(void)
{
    uint8_t up = (twi_start(FRAM_ADDR, 0) == 0);
    twi_stop();
    return up ? 1u : 0u;
}

void fram_power_off(void)
{
    NFC_EN_PORT.OUTCLR = NFC_EN_PIN_bm;   /* VNFC off -> FRAM (and tag) VCC off */
}

uint8_t fram_power_on(void)
{
    /* Same gate as nfc_power_on(): if the tag is already powered, VNFC is up and
     * this just re-confirms the FRAM answers. Bounded ACK-poll so an absent part
     * or an unwired EN returns a fault rather than hanging the core. */
    NFC_EN_PORT.OUTSET = NFC_EN_PIN_bm;
    _delay_us(FRAM_SOFTSTART_US);
    for (uint8_t t = 0; t < FRAM_BOOT_POLL_TRIES; t++) {
        if (fram_present()) return 0;      /* address ACKed -> FRAM is up */
        _delay_us(FRAM_BOOT_POLL_US);
    }
    return 1;                               /* timed out: absent / EN not wired */
}

/* Open the address phase and leave it running: SA+W then the 16-bit pointer.
 * Caller continues with data bytes (write) or a repeated START (read), and
 * STOPs on the fault path. Returns 0 ok, 1 fault. */
static uint8_t fram_setaddr(uint16_t addr)
{
    if (twi_start(FRAM_ADDR, 0))         return 1;   /* SA + write */
    if (twi_write((uint8_t)(addr >> 8))) return 1;   /* addr[15:8] */
    if (twi_write((uint8_t)(addr)))      return 1;   /* addr[7:0]  */
    return 0;
}

uint8_t fram_write(uint16_t addr, const uint8_t *src, uint16_t len)
{
    if (len == 0) return 0;
    if ((uint32_t)addr + len > FRAM_SIZE) return 1;      /* reject overrun */
    if (fram_setaddr(addr)) { twi_stop(); return 1; }
    for (uint16_t i = 0; i < len; i++)
        if (twi_write(src[i])) { twi_stop(); return 1; }
    twi_stop();                 /* FeRAM commits at STOP -- no settle delay to wait out */
    return 0;
}

uint8_t fram_read(uint16_t addr, uint8_t *dst, uint16_t len)
{
    if (len == 0) return 0;
    if ((uint32_t)addr + len > FRAM_SIZE) return 1;
    if (fram_setaddr(addr))      { twi_stop(); return 1; }   /* set the pointer   */
    if (twi_start(FRAM_ADDR, 1)) { twi_stop(); return 1; }   /* repeated START + read */
    for (uint16_t i = 0; i < len; i++)
        if (twi_read((uint8_t)(i < (len - 1)), &dst[i])) {   /* ACK all but last (NACK+STOP) */
            twi_stop();                                       /* bus fault: STOP so the part can't clock-stretch */
            return 1;
        }
    return 0;                    /* last twi_read already issued the NACK + STOP */
}
