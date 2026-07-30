# Bench monitor — the pogo plate grows a UI

Live dashboard for a card seated face-up on the pogo test plate: every harvest rail as a
number and a bar, NFC field presence as it happens (phone on the card → indicator lights),
tap/temperature/g-vector from the accelerometer, and command-on-demand deep reads of the
NFC EEPROM (the vCard) and the FRAM log. The full sensor suite of the card, through the
fourteen tails, with **zero board changes**.

```
card on plate ──14 tails──┬── analog front end ── 2× ADS1115 ── I2C0 ──┐
                          │                                            ├── Pico ── USB ── host/dashboard.py
                          └── SCL/SDA (card's own bus) ────── I2C1 ────┘
```

## What it shows / does

| UI element | Source | How |
|---|---|---|
| Rails: `SRC` `VS` `STO` `STO_LDO` `VINT` `BUFSRC` `MID` | ADS1115 ×2 | 2 Hz, min/max tracked |
| Boost activity | `LX_LOUT` tail through an RC average | a duty indicator, deliberately not labelled as a voltage |
| **NFC activation** | NT3H2211 `NS_REG.RF_FIELD_PRESENT` polled over the card's I²C | event log gets "phone on the card" edges; `wr_busy` shows the phone actually writing |
| Tap / orientation / temp | ADXL367 (0x1D), read-only | XYZ + temp in telemetry; `STATUS` only on command (a read can consume latched bits the card wants) |
| vCard readback | NT3H2211 EEPROM blocks, TLV-parsed | `n` key → saved to `ndef-*.bin` |
| FRAM log dump | MB85RC512TY (0x50, 64 KB) | `f` key → `fram-*.bin`; **read-only by policy** — WP is grounded on-board, so nothing but discipline prevents a write, which is why the driver simply has no write method |

## Hardware (all off-the-shelf, no PCB)

| Qty | Part | Role |
|---|---|---|
| 1 | Raspberry Pi Pico (W optional) | brains + USB |
| 2 | ADS1115 breakout (0x48, 0x49) | 8 × 16-bit rail channels on I2C0 (GP4/GP5) |
| 1 | MCP6004 quad op-amp, powered from VBUS 5 V | unity buffers for `SRC`, `VINT`, `BUFSRC`, `MID` |
| 8 | 1 MΩ resistors + 1 × 100 nF | 1M:1M dividers; RC on the `LX_LOUT` channel |

**The wiring table is generated, not written here.** CI emits
`enclosure/solar-glow-drh-pogo-testplate-channels.json` from the plate generator — per
tail: net, position, ADS chip/channel, front-end class, scale. If a pad ever moves, the
map moves with it. The front-end classes it assigns:

- `buffer+div2` — buffer **before** dividing. `SRC` makes single-digit µA in desk light; a
  bare 2 MΩ divider is a measurable parasitic load on the exact measurement this rig
  exists for. `VINT`/`BUFSRC` are AEM-internal nodes, `MID` is the stack balance point.
- `div2` — 1M:1M straight on the stiff rails (`VS`, `STO`, `STO_LDO`); ~1.7 µA, harmless.
- `direct` — `MID` to the ADC pin after its buffer, **no divider**: it never exceeds
  ~2.75 V and must never see a resistive path to ground (a 100 k divider would tilt the
  supercap stack ~24 mV/h).
- `rc-div2` — `LX_LOUT` through 1 M + 1 M‖100 nF: a ~50 ms average of the switch node.
  Scope the tail directly when you care about edges; this channel only answers "is the
  boost switching".

Rails can reach 5 V-class; ADS1115 inputs must stay under VDD+0.3 — hence divide (or
buffer-then-divide) everywhere except MID. Buffers run from VBUS (5 V) so a 4.15 V `SRC`
stays inside their input range.

## Bus politeness — the card's AVR owns its bus

The monitor is a **guest master** on the card's I²C. The AVR sleeps almost always, so
collisions are rare, but every card-bus access retries on NACK/arbitration-loss and is
counted (`err` in telemetry, visible in the dashboard footer). Three rules the firmware
enforces or the UI signposts:

1. **Session-register reads are atomic** (write `[0xFE, reg]`, STOP, read one byte —
   NXP's own warning: interrupt the sequence and the tag clock-stretches forever).
2. **Telemetry never reads what a read can destroy** — accel `STATUS` is a deliberate
   command with a warning attached, never part of the 2 Hz loop.
3. **Deep reads are human-initiated.** A 4 KB FRAM dump occupies the bus for a while; do
   it while the card is asleep or before flashing firmware, not mid-experiment. The
   NT3H2211's own I²C watchdog (20 ms default) bounds how long the tag stays locked.

## Bring-up

```sh
# 1. flash MicroPython onto the Pico (standard UF2), then:
cd bench/monitor
mpremote cp firmware/*.py :
mpremote cp ../../enclosure/solar-glow-drh-pogo-testplate-channels.json :channels.json
mpremote reset

# 2. dashboard (any OS with python3):
pip install pyserial rich
python3 host/dashboard.py            # auto-finds the port; add --raw for plain JSON lines
```

Boot emits a one-line report: card-bus scan (expect 0x1d, 0x50, 0x55 with the card
seated and VS up), accel ID check, FRAM presence, channel count. If the card bus shows
empty, the card has no VS — inject bench power on the `STO` force tail (J1 side) and
watch the LDO bring `VS` up on the dashboard; the sense tail (JP1 side) shows the true
rail while you do it.

## What this is not

Not the harvest characterization rig — `harvest-budget-test-board.md` /
`harvest-bench-fixture-handoff.md` spec that instrument (SMU-grade, µA-honest I-V
curves). This dashboard is qualitative-to-mid-precision *monitoring*: is the chain
alive, in what order do the rails come up, does the field wake the card, does a tap
register, what did the phone write. The two rigs share nothing and disturb nothing.
