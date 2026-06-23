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

