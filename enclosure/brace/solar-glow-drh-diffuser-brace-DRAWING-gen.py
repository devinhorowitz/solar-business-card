#!/usr/bin/env python3
"""2D print/spec sheet for the SOLAR-GLOW DRH resin diffuser brace -> PDF + PNG.
A drop-in insert (NOT a machined part): the 3D STEP/STL governs geometry; this sheet carries the
print-critical callouts (material, ferrite channel, locator recesses, the flat-bottom datum, assembly)."""
import numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, Polygon as MplPoly

# ---- brace geometry (mirrors solar-glow-drh-diffuser-brace-cad.py) ----
BX0,BY0,BX1,BY1 = 2.0,31.6,49.0,57.4          # envelope (fills the cap-gap band)
GAP = 1.85                                     # brace thickness (fills the 1.85 cavity)
FER = (36.9,31.5,48.9,57.5)                    # ferrite 12 wide (x, CRITICAL) x 26 long (y, forgiving)
FER_CLR = 0.20; FER_DEPTH = 0.33               # channel walls + pocket depth
GLOW = (14.95,40.8,35.85,47.0)                 # monogram-window footprint (LED-hug backing behind it)
LOCS = [(13.0,35.0),(33.0,55.0)]              # locator recesses -> shell Ø3.0 pillars
LOC_D, LOC_DEPTH = 3.2, 0.8
U2 = (28.5,37.0,7.8,5.4)                        # U2: the one through-hole (tall)

INK="#111111"; GRY="#9a9a9a"; HATCH="#ededed"; PUR="#6a4fb0"; AMB="#c79a2e"
fig=plt.figure(figsize=(420/25.4,297/25.4))
ax=fig.add_axes([0,0,1,1]); ax.set_xlim(0,420); ax.set_ylim(0,297)
ax.set_aspect("equal"); ax.axis("off"); fig.patch.set_facecolor("white")
ax.add_patch(Rectangle((8,8),404,281,fill=False,ec=INK,lw=1.2))
ax.add_patch(Rectangle((10,10),400,277,fill=False,ec=INK,lw=0.4))

def dimh(x0,x1,y,text,fs=6.4,side=1,txtoff=1.4):
    ax.plot([x0,x0],[y,y+1.4*side],lw=0.4,color=INK); ax.plot([x1,x1],[y,y+1.4*side],lw=0.4,color=INK)
    ax.annotate("",xy=(x0,y),xytext=(x1,y),arrowprops=dict(arrowstyle="<|-|>",lw=0.5,color=INK,mutation_scale=7,shrinkA=0,shrinkB=0))
    ax.text((x0+x1)/2,y+txtoff*side,text,ha="center",va="bottom" if side>0 else "top",fontsize=fs,color=INK)
def dimv(y0,y1,x,text,fs=6.4,side=1,txtoff=1.4):
    ax.plot([x,x+1.4*side],[y0,y0],lw=0.4,color=INK); ax.plot([x,x+1.4*side],[y1,y1],lw=0.4,color=INK)
    ax.annotate("",xy=(x,y0),xytext=(x,y1),arrowprops=dict(arrowstyle="<|-|>",lw=0.5,color=INK,mutation_scale=7,shrinkA=0,shrinkB=0))
    ax.text(x-txtoff*side,(y0+y1)/2,text,ha="right" if side>0 else "left",va="center",fontsize=fs,rotation=90,color=INK)
def leader(xp,yp,xt,yt,text,ha="left",fs=6.0,va="center"):
    ax.annotate("",xy=(xp,yp),xytext=(xt,yt),arrowprops=dict(arrowstyle="-|>",lw=0.45,color=INK,mutation_scale=7,shrinkA=0,shrinkB=2))
    ax.text(xt+(0.8 if ha=='left' else -0.8),yt,text,ha=ha,va=va,fontsize=fs,color=INK)

# ===================== PLAN (board-facing face) =====================
S=3.0; Px,Py=42,158
X=lambda bx:Px+(bx-BX0)*S
Y=lambda by:Py+(BY1-by)*S          # flip: board y31.6 at top of the plan, y57.4 at bottom
# envelope
ax.add_patch(Rectangle((X(BX0),Y(BY1)),(BX1-BX0)*S,(BY1-BY0)*S,fill=False,ec=INK,lw=1.1))
# general component-pocket field (schematic hatch, minus the callout features)
ax.add_patch(Rectangle((X(BX0)+1,Y(BY1)+1,),(BX1-BX0)*S-2,(BY1-BY0)*S-2,fc=HATCH,ec="none",alpha=0.5,zorder=0))
# ferrite OPEN CHANNEL (walled x36.7-49, open both y-ends) + the 12x26 ferrite extent
cxl=max(FER[0]-FER_CLR,BX0+0.2)
ax.add_patch(Rectangle((X(cxl),Y(BY1)),(BX1-cxl)*S,(BY1-BY0)*S,fc="#efeaf7",ec=PUR,lw=0.9,ls=(0,(4,2))))
ax.add_patch(Rectangle((X(FER[0]),Y(min(FER[3],BY1))),(FER[2]-FER[0])*S,(min(FER[3],BY1)-max(FER[1],BY0))*S,fc="#d9ccf0",ec=PUR,lw=1.0))
ax.text(X((FER[0]+FER[2])/2),Y(44.5),"FERRITE\nCHANNEL\n(open-ended)",ha="center",va="center",fontsize=5.2,color="#3a2b66",fontweight="bold")
# window LED-hug diffuser backing
ax.add_patch(Rectangle((X(GLOW[0]),Y(GLOW[3])),(GLOW[2]-GLOW[0])*S,(GLOW[3]-GLOW[1])*S,fc="#fbf5df",ec=AMB,lw=1.0))
ax.text(X((GLOW[0]+GLOW[2])/2),Y((GLOW[1]+GLOW[3])/2),"LED-HUG\nBACKING",ha="center",va="center",fontsize=5.0,color="#6b5310",fontweight="bold")
# U2 through
ax.add_patch(Rectangle((X(U2[0]-U2[2]/2),Y(U2[1]+U2[3]/2)),U2[2]*S,U2[3]*S,fc="#f6d6d0",ec="#b23b2a",lw=0.9))
ax.text(X(U2[0]),Y(U2[1]),"U2\nTHRU",ha="center",va="center",fontsize=4.6,color="#7a1f12")
# locator recesses: (13,35) round datum + (33,55) SLOT (Ø3.2 x 4.0 along the 45deg pin-pair axis)
def _obround(cx,cy,length,width,ang,n=14):
    r=width/2.0; d=(length-width)/2.0; ca,sa=np.cos(np.radians(ang)),np.sin(np.radians(ang)); pts=[]
    for t in np.linspace(np.radians(ang-90),np.radians(ang+90),n): pts.append((cx+d*ca+r*np.cos(t),cy+d*sa+r*np.sin(t)))
    for t in np.linspace(np.radians(ang+90),np.radians(ang+270),n): pts.append((cx-d*ca+r*np.cos(t),cy-d*sa+r*np.sin(t)))
    return pts
ax.add_patch(Circle((X(13.0),Y(35.0)),LOC_D/2*S,fc="#d6e2f7",ec="#2f5bd0",lw=1.0))
ax.add_patch(MplPoly([(X(bx),Y(by)) for bx,by in _obround(33.0,55.0,4.0,LOC_D,45)],closed=True,fc="#d6e2f7",ec="#2f5bd0",lw=1.0))
for lx,ly in LOCS:
    ax.plot([X(lx)-1.4,X(lx)+1.4],[Y(ly),Y(ly)],lw=0.4,color="#2f5bd0"); ax.plot([X(lx),X(lx)],[Y(ly)-1.4,Y(ly)+1.4],lw=0.4,color="#2f5bd0")
    ax.plot([X(lx)-1.4,X(lx)+1.4],[Y(ly),Y(ly)],lw=0.4,color="#2f5bd0"); ax.plot([X(lx),X(lx)],[Y(ly)-1.4,Y(ly)+1.4],lw=0.4,color="#2f5bd0")
ax.text(X(25.4),Y(BY1)-6,"BOARD-FACING FACE   SCALE 3.0:1",ha="center",fontsize=8.5,fontweight="bold",color=INK)
# plan dims
dimh(X(BX0),X(BX1),Y(BY1)-3.5,"47.00",fs=7,side=-1)
dimv(Y(BY1),Y(BY0),X(BX0)-3.5,"25.80",fs=7,side=1)
dimh(X(FER[0]),X(FER[2]),Y(BY0)+3.0,"12.0 FERRITE WIDTH (CRITICAL)",fs=5.6,side=1)
dimh(X(BX0),X(13.0),Y(35.0),"13.0",fs=5.4,side=-1,txtoff=1.0)
dimv(Y(BY1),Y(35.0),X(13.0),"3.4",fs=5.0,side=1,txtoff=1.0)
leader(X(33.0),Y(55.0),190,164,"\u00d83.2 LOCATOR RECESS\n2\u00d7 - RECEIVE SHELL\nPILLARS (NOTE 4)",ha="left",fs=5.6)

# ===================== SECTION B-B (across the brace) =====================
S2=13.0; EX,EY=244,206
xl=lambda v:EX+v*S2; zl=lambda z:EY+z*S2
# body outline (bottom z=0 = FLAT datum; top z=GAP faces the board)
ax.add_patch(Rectangle((xl(0),zl(0)),10.5*S2,GAP*S2,fc=HATCH,ec=INK,lw=0.9,hatch="\\\\\\\\"))
# ferrite channel (top recess 0.33) at one end
ax.add_patch(Rectangle((xl(7.2),zl(GAP-FER_DEPTH)),3.0*S2,FER_DEPTH*S2,fc="#d9ccf0",ec=PUR,lw=0.7))
# an LED pocket (top, ~0.83 into the backing)
ax.add_patch(Rectangle((xl(3.6),zl(GAP-0.83)),1.2*S2,0.83*S2,fc="white",ec=INK,lw=0.6))
# a locator recess (bottom, 0.8 up) with the shell pillar shown entering (ref)
ax.add_patch(Rectangle((xl(0.9),zl(0)),1.6*S2,LOC_DEPTH*S2,fc="white",ec="#2f5bd0",lw=0.7))
ax.annotate("",xy=(xl(1.7),zl(0)-0.5),xytext=(xl(1.7),zl(0)-4.5),arrowprops=dict(arrowstyle="-|>",lw=0.5,color=GRY,mutation_scale=6))
ax.text(xl(1.7),zl(0)-5.2,"shell pillar\nenters here",ha="center",va="top",fontsize=4.6,color=GRY)
dimv(zl(0),zl(GAP),xl(0)-4,"1.85",fs=7,side=1)
dimv(zl(GAP-FER_DEPTH),zl(GAP),xl(10.5)+4,"0.33 FERRITE",fs=5.6,side=-1,txtoff=1.0)
dimv(zl(0),zl(LOC_DEPTH),xl(0.9)-2.5,"0.8",fs=5.2,side=1,txtoff=1.0)
leader(xl(4.2),zl(GAP-0.83),xl(5.6),zl(GAP)+9,"D2-D5 LED POCKETS (hug the LEDs)",ha="left",fs=5.6)
ax.annotate("",xy=(xl(0)-1,zl(0)),xytext=(xl(10.5)+1,zl(0)),arrowprops=dict(arrowstyle="-",lw=1.2,color=INK))
ax.text(xl(5.25),zl(0)-3.2,"FLAT BOTTOM = SANDING DATUM (lap to the height fit; all pockets are on the TOP face)",ha="center",va="top",fontsize=5.6,color=INK,fontweight="bold")
ax.text(EX+2,EY-13,"SECTION B-B  (typ., across brace)   SCALE 17:1",fontsize=8.5,fontweight="bold",color=INK)
ax.text(EX+2,EY-18.5,"bottom faces the shell floor \u2022 top faces the board back",fontsize=6,color=GRY,style="italic")

# ===================== NOTES =====================
ax.text(20,96,"NOTES",fontsize=7.6,fontweight="bold",color=INK)
notes=[
 "1. PART = SOLAR-GLOW DRH DIFFUSER BRACE. A DROP-IN INSERT, NOT A FASTENED OR BONDED PART. 3D STEP GOVERNS ALL GEOMETRY; THE STL IS THE PRINT SOURCE.",
 "2. PROCESS: SLA / RESIN 3D PRINT (e.g. PCBWay). MATERIAL: TOUGH WHITE RESIN. IT MUST BE OPAQUE-WHITE AND NON-CONDUCTIVE - NO CARBON / GRAPHITE-FILLED RESIN",
 "    (WEAKLY CONDUCTIVE): THE BRACE RESTS ON GND / VS / SIGNAL COPPER, SO A DIELECTRIC IS REQUIRED. WHITE ALSO DRIVES THE WINDOW BACKING (NOTE 6).",
 "3. FIT: PRINT ~0.1 PROUD IN HEIGHT AND SAND THE FLAT BOTTOM (DATUM) DOWN TO A ZERO-AIR FIT IN THE 1.85 CAVITY. ALL POCKETS ARE ON THE TOP FACE, SO THE",
 "    BOTTOM LAPS FLAT ON GLASS WITHOUT TOUCHING THEM. DO NOT SAND THE TOP (IT SETS THE POCKET DEPTHS).",
 "4. LOCATOR RECESSES (Ø3.2 × 0.8 DEEP, IN THE FLAT BOTTOM): (13,35) ROUND DATUM + (33,55) SLOTTED Ø3.2 × 4.0 ALONG THE 45° PIN-PAIR AXIS. ROUND+SLOT RELEASES",
 "    CENTER-DISTANCE TOLERANCE (SLA SHRINK + CNC + BOARD-IN-SHELL PLAY OVER THE 28.3 SPAN) YET HOLDS X-Y DATUM + ROTATION. RECEIVES THE SHELL'S 2× Ø3.0 × 0.4 PILLARS (0.4 ENGAGE, ~0.25 AXIAL).",
 "5. FERRITE CHANNEL (OVER THE NFC COIL): OPEN-ENDED CHANNEL, WALLED ON THE 12 WIDTH (CRITICAL - EDGE-LIMITED), OPEN AT BOTH Y-ENDS, 0.33 DEEP.",
 "    FERRITE (Wurth WE-FSFS 364006, NOMINAL 12 \u00d7 26 mm, EVEN ON THE 2mm SCORE GRID) IS PSA'd IN; LENGTH IS FORGIVING AND MAY OVERHANG THE ENDS SLIGHTLY.",
 "6. WINDOW = LED-HUG DIFFUSER BACKING: SOLID WHITE RESIN FILLS THE MONOGRAM-WINDOW FOOTPRINT BEHIND THE FR4, MINUS THE TIGHT D2-D5 LED POCKETS.",
 "    NO APERTURE, NO FLOOR TAPE. THE POCKET CLEARANCE DOUBLES AS A RESERVOIR IF A VISCOUS OPTICAL GEL IS PRE-FILLED AT FINAL ASSEMBLY (OPTIONAL).",
 "7. REMOVABLE / NOT BONDED: THE BRACE MUST LIFT OUT FOR NFC C9 TRIM DURING BENCH BRING-UP. KEEP IT DRY-FIT WHILE ITERATING; ADD ANY GEL ONLY ON THE FINAL CARD.",
 "8. U2 AND U6 ARE THROUGH-POCKETS (U2 TALL AT 1.75; U6 FORCED THROUGH -- ITS BLIND WEB WOULD BE 0.28 < SLA MIN; U6 IS 1.45 IN THE 1.85 CAVITY -> 0.40 AIR TO THE SHELL FLOOR). OTHERS BLIND.",
]
yy=91.5
for n in notes: ax.text(20,yy,n,fontsize=5.9,color=INK); yy-=3.9

# ===================== TITLE BLOCK =====================
tb_x,tb_y,tb_w,tb_h=288,12,120,44
ax.add_patch(Rectangle((tb_x,tb_y),tb_w,tb_h,fill=False,ec=INK,lw=0.9))
for yl in (tb_y+32,tb_y+23,tb_y+14,tb_y+7.5): ax.plot([tb_x,tb_x+tb_w],[yl,yl],lw=0.4,color=INK)
ax.plot([tb_x+60,tb_x+60],[tb_y,tb_y+14],lw=0.4,color=INK)
ax.text(tb_x+tb_w/2,tb_y+38,"SOLAR-GLOW DRH  \u2014  RESIN DIFFUSER BRACE",ha="center",va="center",fontsize=8.0,fontweight="bold",color=INK)
ax.text(tb_x+3,tb_y+27.5,"DWG  solar-glow-drh-diffuser-brace",fontsize=6.0,va="center",color=INK)
ax.text(tb_x+tb_w-3,tb_y+27.5,"REV  A",ha="right",fontsize=6.4,va="center",color=INK)
ax.text(tb_x+3,tb_y+18.5,"MATERIAL  TOUGH WHITE SLA (opaque, non-conductive)",fontsize=5.6,va="center",color=INK)
ax.text(tb_x+3,tb_y+10.5,"UNITS  mm",fontsize=6.2,va="center",color=INK)
ax.text(tb_x+63,tb_y+10.5,"SCALE  AS NOTED",fontsize=6.2,va="center",color=INK)
ax.text(tb_x+3,tb_y+3.7,"ENVELOPE 47.0 x 25.8 x 1.85   process: SLA print",fontsize=5.7,va="center",color=INK)
ax.text(tb_x+tb_w-3,tb_y+3.7,"SHEET 1/1",ha="right",fontsize=6.2,va="center",color=INK)

fig.savefig("/mnt/user-data/outputs/solar-glow-drh-diffuser-brace-DRAWING.pdf",facecolor="white")
fig.savefig("/mnt/user-data/outputs/solar-glow-drh-diffuser-brace-DRAWING.png",dpi=150,facecolor="white")
print("saved brace drawing")
