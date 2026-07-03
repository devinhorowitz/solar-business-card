#!/usr/bin/env python3
"""
solar-glow-drh-diffuser-brace-cad.py  -  resin/SLA gap-filling diffuser brace (rev B).

REV B folds in the PCB-side notes (PCB/PCB-side-notes-brace-direction.md):
 - Component HEIGHTS replaced with the datasheet-verified table (U6=1.45 not 0.6; U5=0.5 not 1.0;
   solder-bridge blobs budgeted 0.8; U1/U3=1.0; 0402=0.55; U2=1.75).
 - Envelope clipped to the component-free middle band y 31.6-57.4 to KEEP CLEAR OF THE SUPERCAP BAYS
   (cap bodies at y31.15 / y57.75). Caps are no longer cut as through-holes; they are simply outside.
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

Registration: pockets key it laterally to the board (nests over U2, U6, U1, U3); PLUS two diagonal
LOCATOR RECESSES (Ø3.2 x 0.8, INVERTED) in the bottom -- (13,35) round + (33,55) slotted 4.0 along the pin axis --
receive two Ø3.0 x 0.4 metal pillars standing on
the shell floor at (13,35) and (33,55). Inverting keeps the shell floor solid (uniform 0.95 back for
engraving) and -- the point -- leaves the brace BOTTOM clear so it is the face you sand to the height
fit (the component pockets live on the TOP, so the top cannot be sanded without bottoming parts). Pre-
compensate: print the bottom features (the recesses) ~0.15 deeper for the sanding allowance.

Print ~0.10-0.15 mm PROUD in height, sand the bottom flat to a zero-air fit. Model is the sanded
nominal at the true 1.85 gap.

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
import re
import cadquery as cq

PCB = "/home/claude/repo4/sbc/PCB/solar-glow-drh-v3_0.kicad_pcb"
OUT = "/mnt/user-data/outputs/"
BASE = "solar-glow-drh-diffuser-brace"

BX0, BX1, BY0, BY1 = 2.0, 49.0, 31.6, 57.4
GAP   = 1.80
CLR   = 0.25
AIR   = 0.12
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
STUBS = [(13.0, 35.0), (33.0, 55.0)]   # diagonal locators (INVERTED): recesses in the brace bottom that
                                       # receive Ø3.0 metal pillars standing on the shell floor.
RECESS_R, RECESS_DEPTH = 1.6, 0.8      # Ø3.2 x 0.8 deep: (13,35) round datum + (33,55) slotted 4.0 along the pin axis (see loop). Takes the shell's Ø3.0 x 0.4 pillar; ~0.15 bottom-sanding leaves ~0.25 axial margin
W, H = 50.80, 88.90
def wx(bx): return bx - W/2
def wy(by): return by - H/2

def part_height(ref):
    if ref == "U2": return 1.75
    if ref == "U6": return 1.45
    if ref == "U1": return 1.00
    if ref == "U3": return 1.00
    if ref == "U5": return 0.50
    r = ref.rstrip("0123456789")
    if r == "SC": return None
    if r == "D":  return 0.83
    if r in ("SW","SB","SJ"): return 0.80
    if r in ("J","JP","TC","TP"): return 0.20
    if r in ("R","C"): return 0.55
    return 0.60

s = open(PCB).read()
def fp_blocks():
    out=[]
    for m in re.finditer(r'\(footprint ', s):
        d=0;i=m.start()
        while i<len(s):
            if s[i]=='(':d+=1
            elif s[i]==')':
                d-=1
                if d==0:break
            i+=1
        out.append(s[m.start():i+1])
    return out
comps=[]
for b in fp_blocks():
    rm=re.search(r'\(property "Reference" "([^"]+)"',b); ref=rm.group(1) if rm else "?"
    if ref.startswith("MH"): continue
    at=re.search(r'\(at (-?[\d.]+) (-?[\d.]+)',b); fx,fy=float(at.group(1)),float(at.group(2))
    if not re.search(r'\(footprint "[^"]+"\s*\(layer "B', b): continue
    xs=[];ys=[]
    for pm in re.finditer(r'\(pad ', b):
        dd=0;j=pm.start()
        while j<len(b):
            if b[j]=='(':dd+=1
            elif b[j]==')':
                dd-=1
                if dd==0:break
            j+=1
        pb=b[pm.start():j+1]
        pat=re.search(r'\(at (-?[\d.]+) (-?[\d.]+)',pb); px,py=float(pat.group(1)),float(pat.group(2))
        sz=re.search(r'\(size ([\d.]+) ([\d.]+)\)',pb); w,h=(float(sz.group(1)),float(sz.group(2))) if sz else (0.3,0.3)
        rr=max(w,h)/2; xs+=[fx+px-rr,fx+px+rr]; ys+=[fy+py-rr,fy+py+rr]
    if xs: comps.append((ref, min(xs),max(xs),min(ys),max(ys)))

brace = cq.Workplane("XY").box(BX1-BX0, BY1-BY0, GAP, centered=(False,False,False)).translate((wx(BX0), wy(BY0), 0))
cut_log=[]
for ref,x0,x1,y0,y1 in comps:
    h=part_height(ref)
    if h is None: continue
    ix0,ix1=max(x0,BX0),min(x1,BX1); iy0,iy1=max(y0,BY0),min(y1,BY1)
    if ix0>=ix1 or iy0>=iy1: continue
    px0,px1,py0,py1=ix0-CLR,ix1+CLR,iy0-CLR,iy1+CLR
    depth=h+AIR; through=depth>=GAP-0.05 or ref=="U6"   # U6 forced THRU: blind web would be 0.28mm (<SLA min); U6 tops at 1.45 in 1.85 -> 0.40 air to the shell floor when through
    zc=(GAP-depth) if not through else -0.05; dz=(depth+0.05) if not through else GAP+0.10
    brace=brace.cut(cq.Workplane("XY").box(px1-px0,py1-py0,dz,centered=(False,False,False)).translate((wx(px0),wy(py0),zc)))
    cut_log.append((ref,round(depth,2),"THRU" if through else "pkt"))
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

cq.exporters.export(brace, OUT+BASE+".step")
cq.exporters.export(brace, OUT+BASE+".stl", tolerance=0.03, angularTolerance=0.2)
try:
    from OCP.GProp import GProp_GProps
    from OCP.BRepGProp import BRepGProp
    g=GProp_GProps(); BRepGProp.VolumeProperties_s(brace.val().wrapped,g)
    print(f"brace volume {g.Mass()/1000:.2f} cm^3 (~{g.Mass()/1000*1.15:.1f} g tough white SLA)")
except Exception as e: print("vol:",e)
print(f"envelope {BX1-BX0:.1f} x {BY1-BY0:.1f} x {GAP} (y31.6-57.4, clears cap bays); {len(cut_log)} pockets")
print(f"through-holes: {[c[0] for c in cut_log if c[2]=='THRU']}")
print(f"ferrite CHANNEL {fx1-fx0:.1f} wide (walled) x open-ended x {FER_POCKET_DEPTH} deep; ferrite {FER[2]-FER[0]:.0f}x{FER[3]-FER[1]:.0f} nominal (width critical / length forgiving, may overhang)")

import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle
import matplotlib.patches as mp
fig,ax=plt.subplots(figsize=(9,5)); ax.set_facecolor("#0d0d10"); fig.patch.set_facecolor("#0d0d10")
ax.add_patch(Rectangle((BX0,BY0),BX1-BX0,BY1-BY0,fc="#e8e4d8",ec="#fff",lw=1.5,alpha=0.28))
ax.text((BX0+BX1)/2,BY1-0.9,"WHITE RESIN BRACE (fills the gap, y31.6-57.4)",color="#eee",ha="center",fontsize=7,fontweight="bold")
ax.add_patch(Rectangle((FER[0]-FER_CLR,BY0),FER[2]-FER[0]+2*FER_CLR,BY1-BY0,fc="#2a2140",ec="#7e57c2",lw=0.9,ls=(0,(3,2)),alpha=0.6))   # open channel (walled x, open y)
ax.add_patch(Rectangle((FER[0],FER[1]),FER[2]-FER[0],FER[3]-FER[1],fc="#3a2b55",ec="#b39ddb",lw=1.3,alpha=0.9))                                # ferrite 12x26 (runs past the brace y-edges)
ax.text((FER[0]+FER[2])/2,(FER[1]+FER[3])/2,"FERRITE 12x26\nwidth CRITICAL\nlength forgiving\n(open channel)",color="#d1c4e9",ha="center",va="center",fontsize=5.2,fontweight="bold")
ax.add_patch(Rectangle((GLOW[0],GLOW[1]),GLOW[2]-GLOW[0],GLOW[3]-GLOW[1],fc="#f5efdc",ec="#d9c98a",lw=1.0,alpha=0.20))   # SOLID white resin backing behind the FR4 window (LEDs hug into it)
ax.text((GLOW[0]+GLOW[2])/2,GLOW[3]+0.5,"LED-HUG DIFFUSER BACKING (solid resin; no aperture, no tape)",color="#d9c98a",ha="center",va="top",fontsize=4.7,fontweight="bold")
for ref,x0,x1,y0,y1 in comps:
    h=part_height(ref)
    if h is None: continue
    ix0,ix1=max(x0,BX0),min(x1,BX1); iy0,iy1=max(y0,BY0),min(y1,BY1)
    if ix0>=ix1 or iy0>=iy1: continue
    depth=h+AIR; thru=depth>=GAP-0.05
    col="#e0483a" if thru else ("#e08a3a" if depth>1.0 else "#43a047")
    ax.add_patch(Rectangle((ix0-CLR,iy0-CLR),(ix1-ix0)+2*CLR,(iy1-iy0)+2*CLR,fc=col,ec="#222",lw=0.3,alpha=0.9))
    if (ix1-ix0)>1.8 and (iy1-iy0)>1.3: ax.text((ix0+ix1)/2,(iy0+iy1)/2,ref,color="#111",ha="center",va="center",fontsize=4.6)
for sx,sy in STUBS:
    ax.add_patch(Circle((sx,sy),RECESS_R,fc="#4a86e8",ec="#fff",lw=0.8)); ax.text(sx,sy+1.9,"pillar\nhole",color="#8ab",ha="center",fontsize=4.6)
leg=[mp.Patch(fc="#e0483a",label="through-hole (U2, tall)"),mp.Patch(fc="#e08a3a",label="deep (U6 1.45, U1/U3 1.0)"),
     mp.Patch(fc="#43a047",label="shallow (0402, LEDs hug window, bridges)"),mp.Patch(fc="#3a2b55",label="ferrite pocket"),mp.Patch(fc="#4a86e8",label="pillar hole (Ø3.2)")]
ax.legend(handles=leg,loc="upper left",fontsize=5.2,facecolor="#1a1a1f",edgecolor="#444",labelcolor="#ddd",framealpha=0.9)
ax.set_xlim(BX0-2,BX1+2); ax.set_ylim(BY0-2,BY1+2); ax.set_aspect("equal"); ax.invert_yaxis(); ax.axis("off")
ax.set_title("Diffuser brace rev B - pocket map (board-facing face)\nverified heights + ferrite pocket over the coil + cap-bay clearance",color="#d9a23a",fontsize=8)
fig.tight_layout(); fig.savefig(OUT+BASE+"-pocket-map.png",dpi=150,facecolor="#0d0d10")
print("saved pocket map")
