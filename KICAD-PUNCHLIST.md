## session 15: VSENSE -> PC3 for comparator wake-on-light (+ BTN -> PC1)

PIN CHANGE (do in the KiCad symbol/schematic): move **VSENSE to PC3 (pad5)** and the reserved **BTN to PC1
(pad3)**. PC3 = AIN31 (keeps the ADC voltage sense) + AINP4 (adds the AC0 wake comparator) -> one pin, both
jobs. AC0 negative input = internal DACREF (no pin, no parts). This is the wake-on-light feature: AC0 wakes
the MCU from sleep when the solar cell sees light; DAC sets the threshold.
 - FUSE: disable MVIO (SYSCFG1) so PC3's analog (AIN31/AINP4) works - VDDIO2 is already tied to VS, so PORTC
   already sits at VDD; no downside.
 - Alternative if a PORTD pin is preferred (no MVIO fuse): PD6 (pad12) = AIN6 + AINP3 + VOUT. But its S edge
   is congested; PC3 routed clean, PD6 did not.
 - LED PWM (firmware-only, no board change): LDRV1-4 are on PA4-PA7 = TCD0 WOA-WOD -> brightness/breathing
   via TCD; note in the firmware plan.

ROUTING NOTE for the W-margin re-lay: J1 (backup UPDI header) pads are 1.5x2.0mm and reach x5.45 - they
dominate the left margin. J1.3 GND is B-only, so route VSENSE's In2 trace THROUGH that zone but keep its
via off it (drop to In2 at the pad). VSENSE @x5.5 descent, BTN @x6.05 (briefly In3 up top to clear VSENSE's
crossing). gen_v2 has a clean reference layout; KiCad's interactive router will do this corner better.

---
## session 14: hand-soldering items (placement + via-in-pad)

VIPPO LIST - EXTEND for hand-solderability. Current: U2, U4, Q1, TC1.1/2/3, JP2, D9.A, R2.2.
ADD (7 in-pad vias on small normally-soldered parts that will otherwise wick): C6 (VS+GND), R1/R3/R4
(LDRV risers), R5 (VIN+VSENSE). OR dog-bone these instead. If PCBWay via-fill is board-wide -> already covered.
Leave the rest as-is: large pads/ICs (SC, U1.EP, U2 pins) reflow fine; SB1-4/SJ1/SW2 are flooded bridge pads;
JP1/JP2/J1 are robust header joints; TC1's fill is for pogo-contact flatness (never soldered).

PLACEMENT: R9 nudged up 0.4 in gen_v2 (Q1/R9 0.35->0.73). Still to handle in KiCad: R2/SW2 (0.27, vertical
overlap) - when upsizing R1-R4 to 1206, nudge SW2 up ~0.4mm or re-space the LED/selector row so the 1206 R2
body clears SW2. U3/C6 (0.38) left as-is (decoupling proximity + U3 is hot-air).
FINE-PITCH: U1 QFN-28 + U3 LGA-12 = hot-air/hotplate.

---

## session 13: Option-2 screw symmetry + TC1 east-shift (UPDATES session-12 TC1 coords + PV1/MH placement)

SCREW SYMMETRY (mirror the bottom half about mid-y 44.45):
 - PV1 footprint origin -> (25.4, 17.0)  [was 15.9; down 1.1mm]. Now mirrors PV2 (25.4,71.9) and centers over SC1/SC2.
   PV1 pads follow: P(43.4,17.0) N(7.4,17.0) Pt(46.5,17.0) Nt(4.3,17.0).
 - MH3 -> (3.5, 3.0), MH4 -> (47.3, 3.0)  [were (3.5/47.3, 29.9)]. Exact mirror of MH1(3.5,85.9)/MH2(47.3,85.9).
   M2 2.2mm, GND, 3.6x3.6 pad. Screws now at all 4 corners.

TC1 SHIFTED EAST 1.8mm (clears PV1.N from the left leg-latch hole). New absolute geometry (supersedes session-12):
 - contact cluster center (13.3, 16.9)  [was 11.5,16.9]. Drop the official footprint here.
 - 6 contact pads: col1 x12.665 / col2 x13.935 ; rows y15.63 / 16.9 / 18.17. (pin1=UPDI at 12.665,15.63)
 - leg-latch Ø2.3749 NPTH: (10.76,14.36)(15.84,14.36)(10.76,17.54)(15.84,17.54)
 - alignment Ø0.9906 NPTH: (12.28,19.44)(14.32,19.44)(13.3,14.36)
 - UPDI In3 route to TC1.1: down x11.5 past JP1, jog E below it, thread the upper alignment holes @x13.3, down to
   y15.63, W into TC1.1. Via at TC1.1 = (12.665,15.63).
 - Old TC2030-NL SMD footprint NPTH holes (11.5,13.3)/(11.5,20.5) deleted - do not recreate.

Clearances verified in gen_v2 (edge-to-edge, > 0.15 floor): PV1.N<->leg hole 0.46; SC1.P/N >5.1; contact pads 0.43.
WATCH (tight, legal): UPDI vertical 0.21mm to the TC1.2/TC1.3 VS/GND vias (1.27mm pitch); align-hole thread 0.40mm.

---

## TC1 (session 12): TC2030-MCP-FP legged footprint - EXACT geometry (supersedes session-11 counts)

Use the official KiCad footprint Tag-Connect_TC2030-IDC-FP (Connectors.pretty); board-side == TC2030-MCP-FP.
Place at the locked TC1 center; TC1 pads are this footprint rotated 90deg CCW.
 - 6 contact pads Ø0.7874mm, mask opening = pad, NO paste. Pins 1=UPDI 2=VS 3=GND 4-6 NC.
 - 4 leg-latch holes Ø2.3749mm NPTH (the 4 clipping points).
 - 3 alignment holes Ø0.9906mm NPTH.
gen_v2 carries the 7 holes (B-NPTH.XLN), absolute:
 leg Ø2.3749: (8.96,14.36)(14.04,14.36)(8.96,17.535)(14.04,17.535)
 align Ø0.9906: (10.484,19.44)(12.516,19.44)(11.5,14.36)
To-dos: VIPPO TC1.1/2/3 (or plate the alignment holes per note5 + route VS/GND there to keep pads solid);
keep-out (no tracks/vias in shaded area, no signal within 0.508mm of a pad); UPDI In3 trace clears the upper
alignment holes by 0.40mm. DNL in BOM. Holes clear SC1.P/N by >5mm.

---

