"""
SOLAR-GLOW DRH v1 netlist (schematic-level). ref -> {pad: net}.
Basis: v1 pin map (AVR64DD28 VQFN28, datasheet-verified) + v0 REV J topology
(pcb_route.py P entries) + 2P2S quad-supercap (V1-SPEC §1) + new feature parts.

Net glossary:
  VS    supercap-stack top = MCU VDD = LED anodes
  MID   single shared supercap midpoint (all 4 caps' middles); U2 balances it
  GND   ground / In1.Cu plane
  VIN   raw harvest input (solar or battery), pre-Schottky
  UPDI  programming
  SDA/SCL  I2C (TWI0 on PC2/PC3, MVIO host)
  VSENSE   light-sense divider tap -> PA5/AIN25
  BTN   dome SW1 -> PA7
  VDDIO2   PORTC supply (jumpered to VS in v1; LDO in v2)
  RESET PF6 (input-only, pull-up)
  LDRV1..4  LED PWM drive nets (MCU pin -> ballast)
  K2..K5    LED cathode nets (LED -> ballast)
  VBAT/BMID/VBATD  dual-coin battery option (mutually exclusive with PV1)

FLAGS (confirm):
  * SW2 removed. Replaced by 4 per-channel LED test jumpers (SB1-4): 4 independent PWM
    channels retained; each 2-pad solder bridge forces one LED on without the MCU. Bridge
    only when the MCU is not driving that pin high (unpopulated / unflashed bring-up).
  * U2 = ALD910025 (DUAL, 8-pin) -- NOT ALD810025 (that is the QUAD / 16-pin, per the
    shared datasheet title). The SOIC-8 land + single MID node require the dual. Threshold
    ~2.5 V/cell (safe-but-conservative for the 2.75 V WS17; effective stack ~5.0 V). v0 SAB
    pin mapping retained below; verify exact pinout/balance voltage at footprint time.
  * TC1 6-pad order mirrors J1 (1=UPDI,2=VS,3=GND); confirm vs the actual TC2030 UPDI
    cable/adapter convention.
NEW parts to place (not in current placement): R5,R6 (light-sense), C5 (VSENSE filter),
  SJ1 (VDDIO2 0R jumper).
"""

NET = {
    # ---- MCU: AVR64DD28 VQFN28 (pad# = VQFN28 pin#; +EP) ----
    "U1": {
        "26": "LDRV1", "27": "LDRV2", "28": "LDRV3", "1": "LDRV4",  # PA0..PA3  TCA0 WO0..WO3
        "3": "VSENSE",                                              # PA5  AIN25 light-sense
        "5": "BTN",                                                 # PA7  dome
        "8": "SDA", "9": "SCL",                                     # PC2/PC3 TWI0 host (MVIO)
        "10": "VDDIO2",                                             # PORTC supply
        "18": "VS", "24": "VS",                                     # VDD x2
        "19": "GND", "25": "GND", "EP": "GND",                      # GND x2 + pad
        "23": "UPDI",                                               # PF7
        "22": "RESET",                                              # PF6 (input-only)
        # spares (unrouted): 2=PA4 4=PA6 6=PC0 7=PC1 11..17=PD1..PD7 20=PF0 21=PF1
    },
    # ---- quad supercap, 2P2S, single MID ----
    "SC1": {"P": "VS",  "N": "MID"},   # top-left   VS-MID
    "SC2": {"P": "MID", "N": "GND"},   # top-right  MID-GND
    "SC3": {"P": "VS",  "N": "MID"},   # bot-left   || SC1
    "SC4": {"P": "MID", "N": "GND"},   # bot-right  || SC2
    # ---- SAB balancer (v0 mapping) ----
    "U2": {"1": "GND", "2": "VS", "3": "VS", "4": "MID", "5": "GND", "6": "MID", "7": "MID", "8": "VS"},
    # ---- input Schottky (MMSD301) ----
    "D1": {"K": "VS", "A": "VIN"},
    # ---- LEDs (anode=VS, low-side drive) + ballast ----
    "D2": {"A": "VS", "K": "K2"}, "D3": {"A": "VS", "K": "K3"},
    "D4": {"A": "VS", "K": "K4"}, "D5": {"A": "VS", "K": "K5"},
    "R1": {"1": "K2", "2": "LDRV1"}, "R2": {"1": "K3", "2": "LDRV2"},
    "R3": {"1": "K4", "2": "LDRV3"}, "R4": {"1": "K5", "2": "LDRV4"},
    # ---- decoupling: VDD pin18, VDD pin24, VDDIO2, bulk ----
    "C1": {"1": "VS", "2": "GND"},        # VDD(18) decouple
    "C2": {"1": "VS", "2": "GND"},        # VDD(24) decouple
    "C3": {"1": "VDDIO2", "2": "GND"},    # VDDIO2 decouple
    "C4": {"1": "VS", "2": "GND"},        # bulk
    # ---- solar (SM141K06L) ----
    "PV1": {"P": "VIN", "N": "GND", "Pt": "VIN", "Nt": "GND"},
    # ---- dual-coin battery option (alt to PV1) ----
    "BT1": {"T1": "BMID", "T2": "BMID", "NEG": "GND"},
    "BT2": {"T1": "VBAT", "T2": "VBAT", "NEG": "BMID"},
    "D6": {"A": "VBAT", "K": "VBATD"}, "D7": {"A": "VBATD", "K": "VS"},
    # ---- button (snap dome, F12340) ----
    "SW1": {"C": "BTN", "RING": "GND"},
    # ---- programming / breakout ----
    "TC1": {"1": "UPDI", "2": "VS", "3": "GND", "4": "NC", "5": "NC", "6": "NC"},  # FLAG: confirm pad order
    "J1":  {"1": "UPDI", "2": "VS", "3": "GND"},
    "JP1": {"1": "SDA", "2": "SCL", "3": "GND"},
    # ---- light-sense divider + VSENSE filter (NEW) ----
    "R5": {"1": "VIN", "2": "VSENSE"},     # top (MΩ-class)
    "R6": {"1": "VSENSE", "2": "GND"},     # bottom
    "C5": {"1": "VSENSE", "2": "GND"},     # ADC node filter
    # ---- VDDIO2 jumper (NEW, 0R) ----
    "SJ1": {"1": "VS", "2": "VDDIO2"},
    # ---- mounting (plated, bond board GND to Ti body) ----
    "MH1": {"1": "GND"}, "MH2": {"1": "GND"}, "MH3": {"1": "GND"}, "MH4": {"1": "GND"},
    # ---- per-channel LED test jumpers (SB1-4, replaces SW2) ----
    # 2-pad solder bridges. OPEN = MCU drives that channel (normal independent PWM).
    # BRIDGED = that LED's drive net pulled to GND => LED forced ON without the MCU.
    # Bridge all 4 = whole-array glow test, MCU absent. Caveat: only bridge when the MCU
    # is NOT actively driving that pin high (unpopulated / unflashed bring-up, or PA0-PA3
    # tristated in firmware), else a forced bridge fights a live high output.
    "SB1": {"1": "LDRV1", "2": "GND"},
    "SB2": {"1": "LDRV2", "2": "GND"},
    "SB3": {"1": "LDRV3", "2": "GND"},
    "SB4": {"1": "LDRV4", "2": "GND"},
}

# unique nets (sanity)
if __name__ == "__main__":
    nets = sorted({n for pads in NET.values() for n in pads.values() if n not in ("NC",)})
    print(f"{len(NET)} components, {len(nets)} nets:")
    print("  " + ", ".join(nets))
    # quick rail fan-out check
    for rail in ("VS", "MID", "GND", "VIN"):
        hits = [f"{r}.{p}" for r, pads in NET.items() for p, n in pads.items() if n == rail]
        print(f"  {rail}: {len(hits)} pads")
