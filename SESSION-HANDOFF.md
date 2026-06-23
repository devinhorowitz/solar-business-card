## session 9 - SW2 LED master selector (OFF/ON/TINY) + R12 TINY ballast

Closed the last open design item. SW2 design decision: LED anode-supply selector (NOT an MCU mode
input), chosen because it is firmware-independent, gives a true hardware OFF (supercap-safe for
storage), costs no MCU pin, and pairs with the SB1-4 per-LED force-on jumpers.

Topology: the 4 LED anodes left VS and now share a new ANODE net (In2 rail joining the 4 anode
vias). SW2 (3-pad B solder bridge, K3-K4 cathode gap @ ~24,48.6) selects ANODE common to:
 - VS direct   (bridge center-ON)    = full glow
 - VS via R12  (bridge center-TINY)  = dim, long runtime
 - open        (unbridged)           = OFF (true hardware off)
R12 (TINY ballast, 0805, K4-K5 gap @ ~30-32,48.6; 220R placeholder, TUNABLE). SW2.3->R12.1 hops on
In3 to clear the K4 cathode (B). R12.2 VS auto-dog-bones. SW2.1 VS is a manual-bridge via-in-pad
(tolerant like SB/SJ, no VIPPO).

New nets ANODE + TINY -> 28 nets total. Self-DRC: 28/28 single-island, zero shorts.

Changes (gen_v2.py): anode pad re-net VS->ANODE (after _renet); SW2+R12 pads appended after D9;
anode stubs + anode vias VS->ANODE; ANODE In2 rail + SW2.2 via + SW2.1 VS via + TINY In3 hop added
before the dog-bone block (so R12.2 auto-dog-bones). BOM: R12 + SW2 added. Render: sw2-anode-selector.png.

Open design items: NONE. (Front art remains deferred to the very end -> soldermask window over FR4.)

---

