## session 12 - TC2030-MCP-FP legged footprint IMPLEMENTED in gen_v2 (exact KiCad geometry)

Devin confirmed TC2030-MCP (legged = hands-free latch, no scaffold). Pulled the AUTHORITATIVE geometry
from the official KiCad footprint Tag-Connect_TC2030-IDC-FP (KiCad/Connectors.pretty; board-side ==
TC2030-MCP-FP). Corrects session-11: it is 4 leg-latch + 3 alignment holes (not "2 alignment").

Exact footprint, rel contact-cluster center, +y up (KiCad native orientation):
 - 6 contact pads Ø0.7874mm, F.Cu+F.Mask, NO paste:
     1(-1.27,.635) 2(-1.27,-.635) 3(0,.635) 4(0,-.635) 5(1.27,.635) 6(1.27,-.635)   [3col x 2row, 1.27 pitch]
 - 4 leg-latch holes Ø2.3749mm NPTH (the "4 clipping points"): (-2.54,2.54)(-2.54,-2.54)(.635,2.54)(.635,-2.54)
 - 3 alignment holes Ø0.9906mm NPTH: (2.54,1.016)(2.54,-1.016)(-2.54,0)
TC1's existing pads == this footprint rotated 90deg CCW; pin map matches (TC1.n <-> pin n).

IMPLEMENTED: appended the 7 holes (rotated 90CCW, at locked TC1 center 11.5,16.9) to gen_v2 `nonplated`
list -> emit to B-NPTH.XLN + auto antipads on GND/VS planes. Absolute coords:
 - leg-latch Ø2.3749: (8.96,14.36)(14.04,14.36)(8.96,17.535)(14.04,17.535)
 - alignment Ø0.9906: (10.484,19.44)(12.516,19.44)(11.5,14.36)
DRC 28/28 single-island, zero shorts. Clearances (edge-to-edge): SC1.P >=5.4mm, SC1.N >=6.2mm, contact
pads >=0.37mm, UPDI In3 trace 0.40mm (threads between the two upper alignment holes). All > 0.15 floor.
Render: outputs/tc2030-footprint.png (footprint tucked between SC1.P/N = the program-before-mount dead space).

KiCad to-dos:
 - Drop in the official Tag-Connect_TC2030-IDC-FP footprint at the locked center; do NOT hand-draw.
 - Contact pads must stay SOLID for the spring pins (note4: no hole >0.008"). TC1.1/2/3 carry via-in-pad
   (UPDI/VS/GND) -> VIPPO them (resin-fill+cap = flat) OR per note5 plate the 3 alignment holes and route
   TC1.2 VS + TC1.3 GND to them so the pads stay hole-free (UPDI still needs its In3 via).
 - Keep-out (note2 no tracks/vias in shaded area; note3 no signal within 0.508mm of a contact pad).
 - Leg holes are the hands-free latch; non-plated is fine. Finger-squeeze access on 2 sides is available on
   the bare board (before SC1 mounts).

NEXT (footprint now finalized): silkscreen pass on the REAR + instructions on the FRONT under the panels.

---

