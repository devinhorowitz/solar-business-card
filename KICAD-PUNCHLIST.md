## SW2 LED MASTER SELECTOR (session 9) - OFF/ON/TINY anode selector + R12

NEW net ANODE (4 LED anodes taken off VS) + NEW net TINY. KiCad steps:
1. Re-net D2-D5 anode pads VS -> ANODE.
2. SW2 = 3-pad solder-bridge footprint @ ~(24,48.6) B, in the K3-K4 cathode gap: pad1=VS(x23.1),
   pad2=ANODE(x24.0), pad3=TINY(x24.9), y48.6, ~0.6x0.8 pads, 0.9mm pitch.
3. R12 = 0805 @ K4-K5 gap: R12.1=TINY(30.0,48.6), R12.2=VS(31.9,48.6). 220R placeholder, tunable.
4. ANODE = In2 rail at y47.6 joining the 4 anode vias + tap to SW2.2 (via @24,48.6).
5. TINY = SW2.3 -> In3 hop (x25.6->29.3 @ y48.6, clears the K4 cathode on B) -> R12.1.
6. SW2.1 -> VS plane via (manual-bridge via-in-pad OK); R12.2 -> VS dog-bone.
Function: bridge center-ON = full glow; center-TINY = dim via R12; unbridged = OFF.

---

