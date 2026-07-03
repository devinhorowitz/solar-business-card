#!/usr/bin/env python3
"""
solar-glow-drh-diffuser-brace-cad.py  -  resin/SLA gap-filling diffuser brace (rev B).

REV B folds in the PCB-side notes (PCB/PCB-side-notes-brace-direction.md):
 - Component HEIGHTS replaced with the datasheet-verified table (U6=1.45 not 0.6; U5=0.5 not 1.0;
   solder-bridge blobs budgeted 0.8; U1/U3=1.0; 0402=0.55; U2=1.75).
 - Envelope clipped to the component-free middle band y 31.6-57.4 to KEEP CLEAR OF THE SUPERCAP BAYS
   (cap bodies at y31.15 / y57.75). Caps are no longer cut as through-holes; they are simply outside.
 - FERRITE POCKET added over the NFC coil (Wurth WE-FSFS 364006, DK 732-5049-ND; patch 12 x 24 mm,
   EVEN dims on the sheet's 2mm score grid for clean cutting, centered in the antenna keepout).
   Sheet is 0.38 mm OVERALL STACK (ferrite+PET+PSA, per DK) -> pocket 0.33
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
LOCATOR RECESSES (Ø5.2 x 0.6, INVERTED) in the bottom receive two Ø5.0 x 0.4 metal pillars standing on
the shell floor at (13,35) and (44,54). Inverting keeps the shell floor solid (uniform 0.95 back for
engraving) and -- the point -- leaves the brace BOTTOM clear so it is the face you sand to the height
fit (the component pockets live on the TOP, so the top cannot be sanded without bottoming parts). Pre-
compensate: print the bottom features (recesses, tape recess) ~0.15 deeper for the sanding allowance.

Print ~0.10-0.15 mm PROUD in height, sand the bottom flat to a zero-air fit. Model is the sanded
nominal at the true 1.85 gap.

WINDOW = aluminum-tape bay (PCB §6a, chosen): a through APERTURE opens the light path to a foil-tape
reflector adhered to the shell floor and located by the laser-marked frame; a shallow bottom RECESS
(tape-thick, meeting the frame) seats the tape edge and registers the brace. Trade taken knowingly:
the window center is now unsupported bare 0.6mm FR4 (no traces there; LEDs held by the surrounding
brace ring). Tape: thin foil, ~0.1mm (3M 427 = 0.12; thinner specialty ~0.06); set the recess to the
chosen tape + ~0.03. Resin must be light near the window regardless (avoid black at the LED bays).
"""
import re
import cadquery as cq

PCB = "/home/claude/repo4/sbc/PCB/solar-glow-drh-v3_0.kicad_pcb"
OUT = "/mnt/user-data/outputs/"
BASE = "solar-glow-drh-diffuser-brace"

BX0, BX1, BY0, BY1 = 2.0, 49.0, 31.6, 57.4
GAP   = 1.85
CLR   = 0.25
AIR   = 0.12
GLOW  = (14.95, 40.8, 35.85, 47.0)
FER   = (36.9, 32.5, 48.9, 56.5)   # 12 x 24 (even, on the 2mm score grid), centered in the antenna keepout
FER_T = 0.38                       # OVERALL STACK per DK 732-5049-ND (ferrite+PET+PSA); the "0.3" was the ferrite layer only.
                                   # MEASURE the delivered sheet and set pocket = measured - 0.05 (rule holds for any alternate sheet).
FER_POCKET_DEPTH = FER_T - 0.05    # -> 0.33 nominal (sits ~0.05 proud, seats flush)
FER_CLR = 0.20
# window = aluminum-tape BAY (PCB §6a): through aperture (light to the floor tape) + shallow bottom
# recess meeting the laser frame (seats the tape, registers the brace).
APER_INSET = 0.6                   # aperture is the laser frame inset this much (brace overlaps the tape edge)
TAPE_RECESS_DEPTH = 0.15           # clears a ~0.1mm foil tape (3M 427 = 0.12); set to chosen tape + ~0.03
TAPE_RECESS_MARGIN = 0.20          # recess = laser frame + this (registration + slight tape oversize)
STUBS = [(13.0, 35.0), (44.0, 54.0)]   # diagonal locators (INVERTED): recesses in the brace bottom that
                                       # receive Ø5.0 metal pillars standing on the shell floor.
RECESS_R, RECESS_DEPTH = 2.6, 0.6      # Ø5.2 recess, 0.6 deep: takes a 0.4 pillar with room for ~0.15 bottom sanding
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
    depth=h+AIR; through=depth>=GAP-0.05
    zc=(GAP-depth) if not through else -0.05; dz=(depth+0.05) if not through else GAP+0.10
    brace=brace.cut(cq.Workplane("XY").box(px1-px0,py1-py0,dz,centered=(False,False,False)).translate((wx(px0),wy(py0),zc)))
    cut_log.append((ref,round(depth,2),"THRU" if through else "pkt"))
fx0,fy0,fx1,fy1 = FER[0]-FER_CLR,FER[1]-FER_CLR,FER[2]+FER_CLR,FER[3]+FER_CLR
fx0,fy0,fx1,fy1 = max(fx0,BX0+0.2),max(fy0,BY0+0.2),min(fx1,BX1-0.2),min(fy1,BY1-0.2)
brace=brace.cut(cq.Workplane("XY").box(fx1-fx0,fy1-fy0,FER_POCKET_DEPTH+0.05,centered=(False,False,False))
                  .translate((wx(fx0),wy(fy0),GAP-FER_POCKET_DEPTH)))
# window aluminum-tape bay (PCB §6a): through aperture (light path down to the floor tape)
ax0,ay0,ax1,ay1 = GLOW[0]+APER_INSET, GLOW[1]+APER_INSET, GLOW[2]-APER_INSET, GLOW[3]-APER_INSET
brace=brace.cut(cq.Workplane("XY").box(ax1-ax0,ay1-ay0,GAP+0.10,centered=(False,False,False)).translate((wx(ax0),wy(ay0),-0.05)))
# + shallow bottom recess = laser frame + margin: seats the tape edge, registers the brace to the frame
tx0,ty0,tx1,ty1 = GLOW[0]-TAPE_RECESS_MARGIN, GLOW[1]-TAPE_RECESS_MARGIN, GLOW[2]+TAPE_RECESS_MARGIN, GLOW[3]+TAPE_RECESS_MARGIN
brace=brace.cut(cq.Workplane("XY").box(tx1-tx0,ty1-ty0,TAPE_RECESS_DEPTH+0.01,centered=(False,False,False)).translate((wx(tx0),wy(ty0),-0.005)))
for sx,sy in STUBS:
    brace=brace.cut(cq.Workplane("XY").workplane(offset=-0.01).moveTo(wx(sx),wy(sy)).circle(RECESS_R).extrude(RECESS_DEPTH+0.01))

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
print(f"ferrite pocket {fx1-fx0:.1f} x {fy1-fy0:.1f} x {FER_POCKET_DEPTH} over the coil")

import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle
import matplotlib.patches as mp
fig,ax=plt.subplots(figsize=(9,5)); ax.set_facecolor("#0d0d10"); fig.patch.set_facecolor("#0d0d10")
ax.add_patch(Rectangle((BX0,BY0),BX1-BX0,BY1-BY0,fc="#e8e4d8",ec="#fff",lw=1.5,alpha=0.28))
ax.text((BX0+BX1)/2,BY1-0.9,"WHITE RESIN BRACE (fills the gap, y31.6-57.4)",color="#eee",ha="center",fontsize=7,fontweight="bold")
ax.add_patch(Rectangle((FER[0],FER[1]),FER[2]-FER[0],FER[3]-FER[1],fc="#3a2b55",ec="#b39ddb",lw=1.2,alpha=0.85))
ax.text((FER[0]+FER[2])/2,(FER[1]+FER[3])/2,"FERRITE\nPOCKET\n(over coil)",color="#d1c4e9",ha="center",va="center",fontsize=6,fontweight="bold")
tx0,ty0,tx1,ty1 = GLOW[0]-TAPE_RECESS_MARGIN,GLOW[1]-TAPE_RECESS_MARGIN,GLOW[2]+TAPE_RECESS_MARGIN,GLOW[3]+TAPE_RECESS_MARGIN
ax.add_patch(Rectangle((tx0,ty0),tx1-tx0,ty1-ty0,fill=False,ec="#d9a23a",lw=0.8,ls=(0,(2,2))))     # tape recess (bottom)
ax0,ay0,ax1,ay1 = GLOW[0]+APER_INSET,GLOW[1]+APER_INSET,GLOW[2]-APER_INSET,GLOW[3]-APER_INSET
ax.add_patch(Rectangle((ax0,ay0),ax1-ax0,ay1-ay0,fc="#111",ec="#d9a23a",lw=1.2))                    # open aperture (light path)
ax.text((GLOW[0]+GLOW[2])/2,ay0+0.9,"ALUMINUM-TAPE BAY",color="#d9a23a",ha="center",va="bottom",fontsize=5.6,fontweight="bold")
ax.text((GLOW[0]+GLOW[2])/2,ty1+0.3,"open aperture + tape recess (to laser frame)",color="#d9a23a",ha="center",va="bottom",fontsize=4.8)
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
    ax.add_patch(Circle((sx,sy),STUB_R,fc="#4a86e8",ec="#fff",lw=0.8)); ax.text(sx,sy+1.5,"stub",color="#8ab",ha="center",fontsize=5)
leg=[mp.Patch(fc="#e0483a",label="through-hole (U2, tall)"),mp.Patch(fc="#e08a3a",label="deep (U6 1.45, U1/U3 1.0)"),
     mp.Patch(fc="#43a047",label="shallow (0402, LEDs, bridges)"),mp.Patch(fc="#3a2b55",label="ferrite pocket"),mp.Patch(fc="#4a86e8",label="locator stub")]
ax.legend(handles=leg,loc="upper left",fontsize=5.2,facecolor="#1a1a1f",edgecolor="#444",labelcolor="#ddd",framealpha=0.9)
ax.set_xlim(BX0-2,BX1+2); ax.set_ylim(BY0-2,BY1+2); ax.set_aspect("equal"); ax.invert_yaxis(); ax.axis("off")
ax.set_title("Diffuser brace rev B - pocket map (board-facing face)\nverified heights + ferrite pocket over the coil + cap-bay clearance",color="#d9a23a",fontsize=8)
fig.tight_layout(); fig.savefig(OUT+BASE+"-pocket-map.png",dpi=150,facecolor="#0d0d10")
print("saved pocket map")
