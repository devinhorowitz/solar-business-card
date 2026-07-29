#!/usr/bin/env python3
"""
solar-glow-drh-diffuser-brace-cad.py  -  resin/SLA gap-filling diffuser brace (rev B).

REV B folds in the PCB-side notes (PCB/PCB-side-notes-brace-direction.md):
 - Component HEIGHTS replaced with a datasheet-verified table. That table now lives in
   enclosure/part_heights.py -- ONE home, shared with the backshell generator and both drawing
   sheets, and verified against each part's own 3D model by check_consistency [7]. It is not
   restated here on purpose: the copy that used to sit in this file went stale on U7 (kept 1.75
   for a SOIC-8 the v4 board does not carry) and cut it as a through-hole for a day.
 - Envelope COMPUTED from the board (enclosure/fit_rules.py), not hand-placed. This line used to
   read "clipped to the component-free middle band y 31.6-57.4 ... (cap bodies at y31.15 / y57.75)",
   which is the 28.5 mm WS17 length; SC1/SC3 are 39 mm SS17 cells, so that band drove straight
   through both of them. The footprint now subtracts every part it cannot span, so the caps are
   outside it by construction rather than by an assumption about where they end.
 - FERRITE CHANNEL over the NFC coil (Wurth WE-FSFS 364006, DK 732-5049-ND). The pocket is an OPEN-ENDED
   CHANNEL: the WIDTH (12 mm, x) is walled and critical -- it is edge-limited by the board/coil east edge;
   the LENGTH (y) is open at both ends, so the ferrite (nominal 12 x 26 mm, even on the 2mm score grid) can
   be cut long/short and extend slightly past the brace into the cap clearance (clears the cap bodies by
   ~0.3). Two enclosed edges + the PSA + light clamp pressure from the PCB retain it; 4-edge capture is not
   needed. Sheet is 0.38 mm OVERALL STACK (ferrite+PET+PSA, per DK) -> pocket 0.33
   (stack - 0.05); measure the delivered sheet and re-cut if an alternate is used (3641014 x3, Laird
   MHLL6060-300). With the ferrite between coil and floor the brace may now span the coil band
   (reverses the earlier "end west of x36.8"). Pocket is on the BOARD-FACING face; ferrite sits
   ~0.05 mm proud (PSA into pocket, PET film to the board) and seats flush when assembled.
 - Pillar-grounding coordination is CLOSED: the PCB net audit rejected 3 of 4 metal-pillar spots
   (NW on accel INT2; NE/SE on the NFC coil). The inert brace dissolves all three by construction.

Material (PCB §4): NON-CONDUCTIVE resin only -- NO carbon/graphite fill (weakly conductive, would
lie across the antenna and every trace). Unfilled or glass/mineral-filled SLA, and a TOUGH white
grade (standard SLA is glassy and cracks as a thin-walled part).

Removable, not bonded (PCB §5): the brace seats and lifts off for the iterative C9 NFC trim; C9's
cutout must clear tweezers-and-iron. The ferrite travels captive in its pocket.

Registration: pockets key it laterally to the board (nests over U7, U6, U1, U3); PLUS two diagonal
LOCATOR RECESSES (Ø3.2 x 0.8, INVERTED) in the bottom -- (13,35) round + (33,55) slotted 4.0 along the pin axis --
receive two Ø3.0 x 0.4 metal pillars standing on
the shell floor at (13,35) and (33,55). Inverting keeps the shell floor solid (uniform 0.95 back for
engraving) and -- the point -- leaves the brace BOTTOM clear so it is the face you sand to the height
fit (the component pockets live on the TOP, so the top cannot be sanded without bottoming parts). Pre-
compensate: print the bottom features (the recesses) ~0.15 deeper for the sanding allowance.

Print ~0.10-0.15 mm PROUD in height, sand the bottom flat to a zero-air fit. Model is the sanded
nominal at the true 1.80 gap.

WINDOW = LED-HUG DIFFUSER BACKING (replaces the earlier open tape bay): the white resin fills the window
region right up behind the FR4, with only the tight D2-D5 LED pockets cut into it. It reads as an even
lightbox back-panel -- opaque-white resin scatters the LEDs into a uniform sheet and recovers the FR4's
backscatter a mm away instead of losing it on a round trip to a floor mirror -- and it now BACKS the thin
0.6mm FR4 window that the open bay had left unsupported. The floor tape + bottom recess are DROPPED (opaque
resin makes them redundant; a reflective floor can return if a bench test wants more punch). Optional:
pre-fill the LED pockets with a viscous (non-curing) optical gel at final assembly to index-match + diffuse
at the die -- removable-ish, but re-apply each time the brace comes off, so dry-fit while iterating C9.
Resin must be white/translucent near the window (never black at the LED pockets).
"""
import os
import re
import sys

import cadquery as cq

PCB = os.path.join(os.path.dirname(__file__), "..", "..", "PCB", "solar-glow-drh-v4_0.kicad_pcb")
# Write next to this script by default (override with $OUT_DIR) -- see the backshell
# generator for why the old hardcoded /mnt/user-data/outputs/ had to go.
OUT = os.environ.get("OUT_DIR") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "")
BASE = "solar-glow-drh-diffuser-brace"

# The five literal rectangles that used to define the footprint (BX*/RAIL_W/RAIL_E_*) are
# GONE, with the in_fp rectangle test that went with them. They encoded supercap bays ending
# at y31.15/57.75 -- the 28.5 mm WS17 length -- while SC1/SC3 are 39 mm SS17 cells, so the
# brace put 593 mm3 of solid resin inside three 1.70 mm cans and could not be installed.
# The footprint is computed from the board now; see enclosure/fit_rules.py.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from fit_rules import GAP, CLR, AIR, export_step_stable                                          # noqa: E402
GLOW  = (14.95, 40.8, 35.85, 47.0)
FER   = (36.9, 31.5, 48.9, 57.5)   # 12 WIDE (x, CRITICAL -- edge-limited) x 26 LONG (y, nominal; length is
                                   # forgiving -- open-ended channel, may run long/short and extend slightly past the brace).
                                   # 26 fully covers the coil turns; clears the cap bodies (y31.15/57.75) by ~0.3.
FER_T = 0.38                       # OVERALL STACK per DK 732-5049-ND (ferrite+PET+PSA); the "0.3" was the ferrite layer only.
                                   # MEASURE the delivered sheet and set pocket = measured - 0.05 (rule holds for any alternate sheet).
FER_POCKET_DEPTH = FER_T - 0.05    # -> 0.33 nominal (sits ~0.05 proud, seats flush)
FER_CLR = 0.20
# window = LED-HUG DIFFUSER BACKING (implemented below). The old aluminum-tape bay (through aperture +
# tape recess) is retired, so its APER_/TAPE_ constants are removed.
STUBS = []                             # LOCATOR RECESSES RETIRED (H-brace): the 4 rails + the component pockets + the
                                       # board press-fit register the brace to the shell by fitment. No metal pillars / recesses.
RECESS_R, RECESS_DEPTH = 1.6, 0.8      # unused now; kept so the (empty) STUBS loops below stay valid
W, H = 50.80, 88.90
def wx(bx): return bx - W/2
def wy(by): return by - H/2

# Component heights live in ONE place, enclosure/part_heights.py, and are verified there
# against each part's 3D model by check_consistency [7]. They used to be inlined here as a
# `part_height()` ladder ending in a silent `return 0.60`; that copy went stale on U7 (1.75,
# a SOIC-8 the v4 rework removed -> a pocket cut clean THROUGH the brace) and defaulted Q2
# and FB1 too shallow. Import, do not re-declare.
from part_heights import part_height  # noqa: E402

from board_parts import parts as _board_parts  # noqa: E402

# Part outlines come from board_parts, which reads the TRUE body (3D model extents, with the
# model's own (rotate ..)/(offset ..) applied on top of the footprint's (at x y rot)) unioned
# with the pads. The loop that used to live here ignored footprint rotation and inflated every
# pad to a max(w,h)/2 SQUARE, so 35 of 61 rotated B-side footprints got a pocket turned 90
# degrees off the part -- and L2's pad box started at exactly y57.400000, tying with the old
# band edge BY1 and being dropped by a `y0 >= r[3]` comparison, so it got no pocket at all.
comps = [(ref, poly.bounds[0], poly.bounds[2], poly.bounds[1], poly.bounds[3])
         for ref, poly, _h, _src in _board_parts("B")]
_KEEPOUT = {ref: poly for ref, poly, _h, _src in _board_parts("B")}

# ---------------------------------------------------------------------------------------
# FOOTPRINT IS COMPUTED FROM THE BOARD, NOT HAND-PLACED.
#
# It used to be an "H" of five literal rectangles whose constants encoded a board that no
# longer exists: the band was sized for supercap bays ending at y31.15/57.75, which is the
# 28.5 mm WS17 length, while SC1/SC3 are 39 mm SS17 cells (the hybrid tank landed in
# docs+sch+BOM and never reached the enclosure). Measured against the committed board, the
# shipped brace put 348.83 mm2 / 593 mm3 of SOLID resin inside three 1.70 mm cans in a
# 1.80 mm cavity -- SC1 155.55, SC3 160.13, SC4 33.15. The part could not be inserted.
#
# So derive it. A part can be COVERED (pocketed) only if the resin left above it is still
# printable:  web = GAP - (h + AIR) >= SLA_WEB  ->  h <= GAP - AIR - SLA_WEB = SPAN_LIMIT.
# Anything taller is a BLOCKER and is subtracted from the footprint instead. That makes
# interference structurally impossible: the thing that would collide is the thing removed.
#
#   footprint = cavity - blockers(+CLR) - boss reliefs, morphologically opened at SLA_WALL
#
# Opening is what keeps it printable: subtracting round reliefs from rails leaves slivers,
# and the opening deletes anything narrower than SLA_WALL and rounds the necks it leaves.
# ---------------------------------------------------------------------------------------
from shapely.geometry import box as _bx2                                     # noqa: E402
from fit_rules import (brace_footprint as _brace_footprint, cavity_rect as _cavity_rect,
                       blockers as _fit_blockers, SPAN_LIMIT, SLA_WEB, SLA_WALL,
                       WALL_FIT as _WCLR, RELIEF_R, BOSS_R)                   # noqa: E402

# The rules live in enclosure/fit_rules.py, shared with the shell generator and asserted by
# check_consistency [8]. They are NOT restated here: the copy that used to sit in this file
# is what went stale against the supercaps.
_pieces = _brace_footprint()
_cav = _cavity_rect().buffer(-_WCLR, join_style=1, resolution=64)
_blockers = _fit_blockers()
# The ferrite channel and the window backing below are still expressed relative to the
# brace's outer extent, so publish it -- derived from the computed footprint rather than
# from the retired hand-placed band constants of the same name.
BX0, BY0, BX1, BY1 = _pieces[0].bounds

brace=None
for _g in _pieces:
    _solid=(cq.Workplane("XY")
            .polyline([(wx(x),wy(y)) for x,y in list(_g.exterior.coords)]).close()
            .extrude(GAP))
    for _ring in _g.interiors:
        _solid=_solid.cut(cq.Workplane("XY").workplane(offset=-0.1)
                          .polyline([(wx(x),wy(y)) for x,y in list(_ring.coords)]).close()
                          .extrude(GAP+0.2))
    brace=_solid if brace is None else brace.union(_solid)

def in_fp(x0,x1,y0,y1):
    """Is any of this part's keep-out actually under the brace? (was a rectangle test that
    tied on L2 at exactly y57.400000 and silently gave it no pocket)"""
    return any(g.intersects(_bx2(x0,y0,x1,y1)) for g in _pieces)

cut_log=[]; pk=[]
for ref,x0,x1,y0,y1 in comps:
    h=part_height(ref)
    if h is None: continue
    if not in_fp(x0,x1,y0,y1): continue                 # only parts under the H (band + rails); SCs/TC1 in the open middle are skipped
    px0,px1,py0,py1=x0-CLR,x1+CLR,y0-CLR,y1+CLR         # full pad box + CLR; the cut is a no-op where there is no brace
    depth=h+AIR; through=(GAP-depth) < SLA_WEB       # THROUGH whenever the blind web would be
                                                     # unprintable. This was hardcoded `or ref=="U6"`,
                                                     # so U9 -- same 1.45 SOT-23-6, same 1.57 pocket --
                                                     # silently kept a 0.23 mm ceiling the code itself
                                                     # calls too thin. The rule now names the reason,
                                                     # not the part.
    zc=(GAP-depth) if not through else -0.05; dz=(depth+0.05) if not through else GAP+0.10
    brace=brace.cut(cq.Workplane("XY").box(px1-px0,py1-py0,dz,centered=(False,False,False)).translate((wx(px0),wy(py0),zc)))
    cut_log.append((ref,round(depth,2),"THRU" if through else "pkt")); pk.append((ref,px0,px1,py0,py1,round(depth,2),through))

# THIN-WALL ELIMINATION: any two pockets separated by a sub-SLA-min wall would print as a fragile fin (or fail
# to form and shed into the pocket). Bridge each such pair so it merges into one clean recess. The wall stands
# full fin-height on the solid base, so the bridge goes to the DEEPER pocket's depth (through, if either neighbour
# is a through-pocket -> the blind recess opens into that hole). Only clearance pockets are merged; the window
# diffuser backing is untouched (it is solid resin OUTSIDE these pocket boxes). Threshold 0.40 sits in the clean
# gap between the real thin walls (<=0.16) and the next-nearest (>=0.49), so marginal-but-printable walls stay.
WALL_MIN=0.40; nbridge=0; _bl=[]; bridges=[]
for i in range(len(pk)):
    for j in range(i+1,len(pk)):
        ra,ax0,ax1,ay0,ay1,da,ta=pk[i]; rb,bx0,bx1,by0,by1,db,tb=pk[j]
        ox=min(ax1,bx1)-max(ax0,bx0); oy=min(ay1,by1)-max(ay0,by0)
        if ox>=0 and oy>=0: continue                                  # already touching/overlapping -> no wall
        gx=max(0.0,max(ax0,bx0)-min(ax1,bx1)); gy=max(0.0,max(ay0,by0)-min(ay1,by1))
        wall=(gx*gx+gy*gy)**0.5
        if not (0.0<wall<WALL_MIN): continue
        if ta or tb: bz,bdz=-0.05,GAP+0.10                            # through neighbour -> full-height bridge
        else: bd=max(da,db); bz,bdz=GAP-bd,bd+0.05                    # blind -> deeper pocket depth (removes full fin)
        if oy>0 and gx>0:   bxr=(min(ax1,bx1)-0.02,max(ax0,bx0)+0.02); byr=(max(ay0,by0),min(ay1,by1))   # x-wall
        elif ox>0 and gy>0: bxr=(max(ax0,bx0),min(ax1,bx1)); byr=(min(ay1,by1)-0.02,max(ay0,by0)+0.02)   # y-wall
        else: continue                                                # diagonal corner nick, not a face wall
        w=bxr[1]-bxr[0]; hh=byr[1]-byr[0]
        if w<=0 or hh<=0: continue
        brace=brace.cut(cq.Workplane("XY").box(w,hh,bdz,centered=(False,False,False)).translate((wx(bxr[0]),wy(byr[0]),bz)))
        nbridge+=1; _bl.append(f"{ra}-{rb}({wall:.2f})"); bridges.append((bxr[0],byr[0],w,hh))
print(f"thin-wall bridges (<{WALL_MIN}mm): {nbridge}  {_bl}")
# ferrite pocket = OPEN CHANNEL: WIDTH (x) walled (critical, edge-limited); LENGTH (y) OPEN at both ends
# so the ferrite can be cut long/short and extend slightly past the brace. Two walls + PSA + the clamped
# PCB overhead retain it (PCB: full 4-edge capture unnecessary).
fx0,fx1 = max(FER[0]-FER_CLR, BX0+0.2), min(FER[2]+FER_CLR, BX1)   # width walls (east meets the brace edge)
fy0,fy1 = BY0-1.0, BY1+1.0                                          # y open: the cut clears both brace edges
brace=brace.cut(cq.Workplane("XY").box(fx1-fx0,fy1-fy0,FER_POCKET_DEPTH+0.05,centered=(False,False,False))
                  .translate((wx(fx0),wy(fy0),GAP-FER_POCKET_DEPTH)))
# window = LED-HUG DIFFUSER BACKING (replaces the open tape bay): NO aperture, NO tape recess. The white
# resin now fills the window region right up behind the FR4, minus the tight D2-D5 LED pockets (0.25 clr,
# cut in the component loop above). It backs the thin FR4 window, scatters as an even lightbox back-panel,
# and recovers FR4 backscatter locally. The LED pocket clearance doubles as the reservoir if a viscous
# optical gel is pre-filled at final assembly (optional: index-match + diffuse at the die; not needed to iterate).
# (13,35) = round Ø3.2 datum; (33,55) = SLOT Ø3.2 x 4.0 along the 45deg pin-pair axis. Round+slot (not two
# round holes) releases center-distance tolerance (SLA XY shrink + CNC pillar pos + board-in-shell play over
# the 28.3mm span) while the round hole holds the X-Y datum and the slot width holds rotation.
for sx,sy in STUBS:
    wpr=cq.Workplane("XY").workplane(offset=-0.01).moveTo(wx(sx),wy(sy))
    prof=wpr.slot2D(4.0, RECESS_R*2, 45) if (sx,sy)==(33.0,55.0) else wpr.circle(RECESS_R)
    brace=brace.cut(prof.extrude(RECESS_DEPTH+0.01))

export_step_stable(brace, OUT+BASE+".step")
cq.exporters.export(brace, OUT+BASE+".stl", tolerance=0.03, angularTolerance=0.2)
try:
    from OCP.GProp import GProp_GProps
    from OCP.BRepGProp import BRepGProp
    g=GProp_GProps(); BRepGProp.VolumeProperties_s(brace.val().wrapped,g)
    print(f"brace volume {g.Mass()/1000:.2f} cm^3 (~{g.Mass()/1000*1.15:.1f} g tough white SLA)")
except Exception as e: print("vol:",e)
print(f"brace {len(_pieces)} piece(s), {sum(g.area for g in _pieces):.1f} mm2 = "
      f"{100*sum(g.area for g in _pieces)/_cav.area:.1f}% of the {_cav.area:.0f} mm2 cavity floor; "
      f"{len(cut_log)} pockets; footprint COMPUTED from the board (blockers: "
      f"{', '.join(r for r,_ in _blockers)})")
print(f"through-holes: {[c[0] for c in cut_log if c[2]=='THRU']}")
print(f"ferrite CHANNEL {fx1-fx0:.1f} wide (walled) x open-ended x {FER_POCKET_DEPTH} deep; ferrite {FER[2]-FER[0]:.0f}x{FER[3]-FER[1]:.0f} nominal (width critical / length forgiving, may overhang)")

import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle
import matplotlib.patches as mp
fig,ax=plt.subplots(figsize=(9,5)); ax.set_facecolor("#0d0d10"); fig.patch.set_facecolor("#0d0d10")
# the pocket map draws the ACTUAL computed footprint, not the retired FP rectangles -- the
# map disagreeing with the part is how a wrong pocket stays invisible to review
for _g in _pieces:
    ax.add_patch(mp.Polygon(list(_g.exterior.coords), closed=True,
                            fc="#e8e4d8", ec="#fff", lw=1.5, alpha=0.28))
for _tx,_ty,_lb in [(4.3,17.0,"PV1 N-tab"),(46.5,17.0,"PV1 P-tab"),(4.3,71.9,"PV2 N-tab"),(46.5,71.9,"PV2 P-tab")]:
    ax.plot(_tx,_ty,marker="*",ms=9,color="#ff5252",zorder=8); ax.text(_tx,_ty+2.0,_lb,color="#ff8a80",ha="center",va="bottom",fontsize=4.2,zorder=8)
ax.text((BX0+BX1)/2,BY1-0.9,f"WHITE RESIN BRACE ({len(_pieces)} piece(s), computed from the board)",color="#eee",ha="center",fontsize=7,fontweight="bold")
ax.add_patch(Rectangle((FER[0]-FER_CLR,BY0),FER[2]-FER[0]+2*FER_CLR,BY1-BY0,fc="#2a2140",ec="#7e57c2",lw=0.9,ls=(0,(3,2)),alpha=0.6))   # open channel (walled x, open y)
ax.add_patch(Rectangle((FER[0],FER[1]),FER[2]-FER[0],FER[3]-FER[1],fc="#3a2b55",ec="#b39ddb",lw=1.3,alpha=0.9))                                # ferrite 12x26 (runs past the brace y-edges)
ax.text((FER[0]+FER[2])/2,(FER[1]+FER[3])/2,"FERRITE 12x26\nwidth CRITICAL\nlength forgiving\n(open channel)",color="#d1c4e9",ha="center",va="center",fontsize=5.2,fontweight="bold")
ax.add_patch(Rectangle((GLOW[0],GLOW[1]),GLOW[2]-GLOW[0],GLOW[3]-GLOW[1],fc="#f5efdc",ec="#d9c98a",lw=1.0,alpha=0.20))   # SOLID white resin backing behind the FR4 window (LEDs hug into it)
ax.text((GLOW[0]+GLOW[2])/2,GLOW[3]+0.5,"LED-HUG DIFFUSER BACKING (solid resin; no aperture, no tape)",color="#d9c98a",ha="center",va="top",fontsize=4.7,fontweight="bold")
for ref,x0,x1,y0,y1 in comps:
    h=part_height(ref)
    if h is None: continue
    if not in_fp(x0,x1,y0,y1): continue
    depth=h+AIR; thru=depth>=GAP-0.05
    col="#e0483a" if thru else ("#e08a3a" if depth>1.0 else "#43a047")
    ax.add_patch(Rectangle((x0-CLR,y0-CLR),(x1-x0)+2*CLR,(y1-y0)+2*CLR,fc=col,ec="#222",lw=0.3,alpha=0.9))
    if (x1-x0)>1.8 and (y1-y0)>1.3: ax.text((x0+x1)/2,(y0+y1)/2,ref,color="#111",ha="center",va="center",fontsize=4.6)
for _bx0,_by0,_bw,_bh in bridges:                       # thin-wall bridges: where sub-0.4mm walls were merged out
    if _bw<0.35: _bx0-=(0.35-_bw)/2; _bw=0.35
    if _bh<0.35: _by0-=(0.35-_bh)/2; _bh=0.35
    ax.add_patch(Rectangle((_bx0,_by0),_bw,_bh,fc="#00e5ff",ec="#fff",lw=1.0,alpha=0.95,zorder=6))
for sx,sy in STUBS:
    ax.add_patch(Circle((sx,sy),RECESS_R,fc="#4a86e8",ec="#fff",lw=0.8)); ax.text(sx,sy+1.9,"pillar\nhole",color="#8ab",ha="center",fontsize=4.6)
leg=[mp.Patch(fc="#e0483a",label="through-hole (U7, tall)"),mp.Patch(fc="#e08a3a",label="deep (U6 1.45, U1/U3 1.0)"),
     mp.Patch(fc="#43a047",label="shallow (0402, LEDs hug window, bridges)"),mp.Patch(fc="#3a2b55",label="ferrite pocket"),mp.Patch(fc="#00e5ff",label=f"thin-wall bridge (merged, {len(bridges)})")]
ax.legend(handles=leg,loc="upper left",fontsize=5.2,facecolor="#1a1a1f",edgecolor="#444",labelcolor="#ddd",framealpha=0.9)
ax.set_xlim(-1,52); ax.set_ylim(12,77); ax.set_aspect("equal"); ax.invert_yaxis(); ax.axis("off")
ax.set_title("Diffuser brace rev C - H-brace (board-facing face)\nband + outboard rails backing the 4 panel solder tabs; ferrite pocket; thin-wall bridges",color="#d9a23a",fontsize=8)
fig.tight_layout(); fig.savefig(OUT+BASE+"-pocket-map.png",dpi=150,facecolor="#0d0d10")
print("saved pocket map")
