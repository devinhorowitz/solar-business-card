## session 14 - hand-soldering pass: B-side placement + via-in-pad review (DRC clean)

Goal: confirm the dense back side is hand/hot-air assemblable; nudge the easy wins, flag the rest.

PLACEMENT (pad-to-pad gaps): dense but manageable. The tightest pairs are mostly SAME-net shared nodes
(safe to sit close - a bridge there is harmless): R7/R8 0.00 & R5/R6 0.20 (divider taps = CLREF/VSENSE),
JP1/R10 & JP1/R11 0.10 (the I2C bus shares SDA/SCL with its own pull-ups). Only 3 DIFFERENT-net pairs are
tight, and all mild/solderable with flux: R2/SW2 0.27 (LDRV2 vs VS), Q1/R9 0.35 (GND vs CLBASE), U3/C6 0.38
(GND vs VS - left as-is, C6 is U3's decoupling so proximity is wanted, and U3 is hot-air anyway).
 - NUDGED: R9 up 0.4mm (40.5,45.55/47.45 -> 45.15/47.05) -> Q1/R9 0.35 -> 0.73mm. Clean (R9.1 VS dog-bone
   auto-follows; CLBASE trace start at L425 updated to 47.05; R9<->U2 2.55, R9<->C7 0.80 still fine).
 - TRIED + REVERTED: R2 west 0.5. Ineffective - R2 sits BELOW SW2 so the overlap is vertical; sliding R2
   sideways doesn't separate them (0.27 -> 0.29). And a 1206-sized R2 would still overlap SW2 in x. This one
   belongs in KiCad with the R1-R4 1206 upsize (nudge SW2 up ~0.4, or re-space the LED/selector row).

VIA-IN-PAD (the bigger hand-solder lever; Devin's "vias" concern): 48 own-net in-pad B-side vias total.
Classified: 15 large-pad/IC (SC terminals, U1.EP thermal, U2 - standard reflow, low wick risk), 8 solder-
bridge pads (SB1-4/SJ1/SW2 - flooded with solder anyway), 10 header breakouts (JP1/JP2/J1 - robust joints),
3 TC1 (pogo connector - NEVER soldered, fill is for contact flatness only, already VIPPO). That leaves the
GENUINE uncovered wicking risk = 7 vias on 5 small normally-soldered parts NOT in the VIPPO plan:
   C6 (VS+GND), R1/R3/R4 (LDRV risers), R5 (VIN+VSENSE).
Note the inconsistency: R2.2 IS on the VIPPO list but its siblings R1/R3/R4 are NOT. The dog-bone routine
only offsets R/C/D pads on GND/VS nets (21 of 21 done); signal risers (LDRV/VIN/VSENSE) and non-R/C/D parts
keep their via in-pad by design.
 -> RECOMMENDATION for KiCad/fab: VIPPO-fill (resin-fill + cap) C6 + R1 + R3 + R4 + R5 in addition to the
    existing list (U2/U4/Q1/TC1/JP2/D9.A/R2.2), OR dog-bone them. If PCBWay's via-fill is board-wide,
    they're already covered; if selective, extend the spec. This is a fab-spec choice, not gen_v2 geometry.

FINE-PITCH: U1 (AVR64DD28 QFN-28) and U3 (LIS2DH12 LGA-12) need hot-air/hotplate regardless of spacing -
no nudge changes the pitch. Render: outputs/solder-map.png (green=hand-solder OK, blue=hot-air, red=fill).

NEXT (unchanged): silkscreen pass on the REAR + instructions on the FRONT under the panels.

---

## session 13 - Option-2 screw symmetry + TC1 east-shift to clear PV1.N (DRC clean)

Two changes, both in gen_v2 (constants DXTC=1.8, DYPV1=1.1 near top; shift block after the PV2 append).

(1) SCREW SYMMETRY (Option 2 of the two Devin weighed). Root cause of the old asymmetry: PV1 sat 1.1mm
    high of its mirror (ctr 15.9 vs the mirror-of-PV2 = 17.0), leaving no room above it, so the top screws
    were tucked INBOARD at y29.9 while the bottom screws were OUTBOARD at y85.9. Option 1 (mirror the inboard
    top screws -> bottom screws to y59) was rejected: inboard screws leave both ends of the 89mm card
    unsupported (bad for the Ti back-plate) and y59 lands in the 2.65mm gap between the middle band (ends
    57.75) and PV2 (starts 60.4) -> no room for an M2 head. Option 2 = mirror the (clean) bottom half:
      - PV1 SOUTH by DYPV1=1.1 -> ctr 17.0 (now mirrors PV2 about mid-y 44.45; also centers PV1 over SC1/SC2,
        which it was 1mm high of). PV1 cell bottom 27.4 -> 28.5, still clear of the middle band (31.15).
      - MH3 -> (3.5,3.0), MH4 -> (47.3,3.0) = EXACT mirror of MH1(3.5,85.9)/MH2(47.3,85.9). Screws now at all
        4 corners (proper back-plate support). Moved in BOTH abs_pads (GND pads) and the plated drill list.
    No reroute needed for the MH moves (old y29.9 spots freed; the VIN In3 descent at x44.8 that used to dodge
    MH4 still clears since MH4 left y29.9; new corner spots are clear).

(2) TC1 EAST by DXTC=1.8 (Devin caught: PV1.N land intersects the connector's left leg-latch hole). PV1.N is
    a fixed Ø3.5 panel terminal at (7.4,17.0) -> can't move it, so move TC1. The overlap existed even before
    the PV1 shift (and got worse after). Shifted: TC1.* contact pads (abs_pads x+=DXTC) + all 7 _TC2030_FP
    holes (x+=DXTC). Shifted positions:
      - contact pads col1 x12.665 / col2 x13.935; rows y15.63 / 16.9 / 18.17
      - leg-latch Ø2.3749: (10.76,14.36)(15.84,14.36)(10.76,17.54)(15.84,17.54)
      - alignment Ø0.9906: (12.28,19.44)(14.32,19.44)(13.3,14.36)
    UPDI re-routed (north branch + via at TC1.1): the old vertical at x11.5 would now pass through the shifted
    left leg hole, so the new In3 route runs x11.5 down PAST JP1 (the x13.7 column, pads at y32.42/34.96/37.5),
    jogs E below JP1 to x13.3, threads between the two upper alignment holes @x13.3 (0.40mm each side), straight
    down to y15.63, then W into the shifted TC1.1 (12.665,15.63). UPDI via moved 10.87 -> 12.665.

ALSO PURGED: the 2 leftover NPTH holes from the OLD TC1 footprint (TC2030-NL SMD board-side, holes at the old
    center +/-3.6 = (11.5,13.3)/(11.5,20.5)) that the legged MCP-FP replaced last session but never removed.
    Filter added just before `nonplated += _TC2030_FP`. (SW1's own 0.89mm locating hole at (37.9,75.4) is
    legitimate v1 - left alone.)

DRC: 28/28 single-island, zero shorts. Clearances (edge-to-edge, all > 0.15 fab floor):
    PV1.N <-> nearest leg hole = 0.46mm (was overlapping). TC1 holes <-> SC1.P 5.16 / SC1.N 5.15.
    TC1 holes <-> contact pads 0.43. Render: outputs/tc1-pv1-clearance.png + screw-symmetry-options.png.
KiCad WATCH-ITEMS (tight, all still legal): UPDI vertical threads the contact-pad column at ~0.21mm to the
    TC1.2/TC1.3 VS/GND vias (inherent to the 1.27mm pitch); alignment-hole threading 0.40mm each side.

NEXT (unchanged): silkscreen pass on the REAR + instructions on the FRONT under the panels.

---

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

