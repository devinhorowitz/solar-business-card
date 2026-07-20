#!/usr/bin/env python3
"""2D fab drawing for the Ti back-shell v3.0 0.6mm-board DUMB BOX (1.00 floor, 0.60 board, U7 pocket, NO ribs, NO locator
pillars -- the resin H-brace carries center support + registers by fitment) -> PDF + PNG."""
import numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Polygon as MplPoly

W,H,R = 50.80,88.90,3.0
wall,lip_w,floor,cavity,board,border = 1.0,2.5,1.00,1.80,0.60,0.15   # lip_w here = WEST lip shown in Section A-A
lip_W,lip_N,lip_S,lip_E,lip_Ew = 2.5,2.0,2.0,1.0,2.5
bbw = 2.0                                   # SYMMETRIC exterior back-border width (uniform 4 sides); front lip stays asymmetric
Wb,Hb = 50.80,88.90
boss_r,pilot_r,cbore,ease = 2.60,0.80,3.0,0.10
ef=-0.05
cavW,cavH,cavR = W+2*ef,H+2*ef,R+ef
outW,outH,outR = cavW+2*wall,cavH+2*wall,cavR+wall
bb,wt = floor+cavity, floor+cavity+board
lb = 0.10                                  # light interior edge-breaks (felt, not seen), 45deg
mounts=[(3.0,3.0),(47.8,3.0),(3.0,85.9),(47.8,85.9),        # 4 corner M2
        (3.0,28.5),(47.8,28.5),(3.0,60.4),(47.8,60.4)]      # +4 panel-corner M2 (8-mount pattern, matches committed board + cad.py)
oxmin,oymin = -0.95,-0.95

INK="#111111"; GRY="#9a9a9a"; HATCH="#e8e8e8"
fig=plt.figure(figsize=(420/25.4,297/25.4))
ax=fig.add_axes([0,0,1,1]); ax.set_xlim(0,420); ax.set_ylim(0,297)
ax.set_aspect("equal"); ax.axis("off"); fig.patch.set_facecolor("white")
ax.add_patch(Rectangle((8,8),404,281,fill=False,ec=INK,lw=1.2))
ax.add_patch(Rectangle((10,10),400,277,fill=False,ec=INK,lw=0.4))

def rrect(x,y,w,h,r,n=12):
    p=[]; cs=[(x+w-r,y+r),(x+w-r,y+h-r),(x+r,y+h-r),(x+r,y+r)]; a0=[-90,0,90,180]
    for (cx,cy),a in zip(cs,a0):
        for t in np.linspace(np.radians(a),np.radians(a+90),n): p.append((cx+r*np.cos(t),cy+r*np.sin(t)))
    return p
def dim(p0,p1,off,text,vert=False,fs=7,side=1,txtoff=1.6):
    (x0,y0),(x1,y1)=p0,p1
    if vert:
        xd=off
        ax.plot([x0,xd+1.6*side],[y0,y0],lw=0.4,color=INK); ax.plot([x1,xd+1.6*side],[y1,y1],lw=0.4,color=INK)
        ax.annotate("",xy=(xd,y0),xytext=(xd,y1),arrowprops=dict(arrowstyle="<|-|>",lw=0.5,color=INK,mutation_scale=8,shrinkA=0,shrinkB=0))
        ax.text(xd-txtoff*side,(y0+y1)/2,text,ha="right" if side>0 else "left",va="center",fontsize=fs,rotation=90,color=INK)
    else:
        yd=off
        ax.plot([x0,x0],[y0,yd+1.6*side],lw=0.4,color=INK); ax.plot([x1,x1],[y1,yd+1.6*side],lw=0.4,color=INK)
        ax.annotate("",xy=(x0,yd),xytext=(x1,yd),arrowprops=dict(arrowstyle="<|-|>",lw=0.5,color=INK,mutation_scale=8,shrinkA=0,shrinkB=0))
        ax.text((x0+x1)/2,yd+txtoff*side,text,ha="center",va="bottom" if side>0 else "top",fontsize=fs,color=INK)
def leader(xp,yp,xt,yt,text,ha="left",fs=6.6,va="center"):
    ax.annotate("",xy=(xp,yp),xytext=(xt,yt),arrowprops=dict(arrowstyle="-|>",lw=0.45,color=INK,mutation_scale=7,shrinkA=0,shrinkB=2))
    ax.text(xt+(0.8 if ha=='left' else -0.8),yt,text,ha=ha,va=va,fontsize=fs,color=INK)
def fcf(x,y,cells,h=4.6,fs=6.6):
    cx=x
    for c in cells:
        w=max(7.0,2.6+len(c)*1.95); ax.add_patch(Rectangle((cx,y),w,h,fill=False,ec=INK,lw=0.5))
        ax.text(cx+w/2,y+h/2,c,ha="center",va="center",fontsize=fs,color=INK); cx+=w
    return cx,y+h/2

# ===================== PLAN (back face) =====================
S1=1.5; Px,Py=42,112
X=lambda bx:Px+(bx-oxmin)*S1; Y=lambda by:Py+(by-oymin)*S1
ax.add_patch(MplPoly(rrect(X(oxmin),Y(oymin),outW*S1,outH*S1,outR*S1),closed=True,fill=False,ec=INK,lw=1.0))
ax.add_patch(MplPoly(rrect(X(oxmin)+wall*S1,Y(oymin)+wall*S1,cavW*S1,cavH*S1,cavR*S1),closed=True,fill=False,ec=GRY,lw=0.5))
_afw,_afh = cavW-2*bbw, cavH-2*bbw          # symmetric recessed art field (equal 2.0 border all sides)
ax.add_patch(MplPoly(rrect(X(0.05+bbw),Y(0.05+bbw),_afw*S1,_afh*S1,max(cavR-bbw,0.3)*S1),closed=True,fill=False,ec=INK,lw=0.8))
for lx,ly,rot in [(0.05+bbw/2,44,90),(Wb-0.05-bbw/2,44,90),(25.4,0.05+bbw/2,0),(25.4,Hb-0.05-bbw/2,0)]:
    ax.text(X(lx),Y(ly),"2.0",ha="center",va="center",fontsize=4.8,color="#2f5bd0",rotation=rot)
for mx,my in mounts:
    ax.add_patch(plt.Circle((X(mx),Y(my)),boss_r*S1,fill=False,ec=GRY,lw=0.5))
    ax.add_patch(plt.Circle((X(mx),Y(my)),cbore/2*S1,fill=False,ec=GRY,lw=0.5))
    ax.add_patch(plt.Circle((X(mx),Y(my)),pilot_r*S1,fill=False,ec=INK,lw=0.9))
    ax.plot([X(mx)-1.6*S1,X(mx)+1.6*S1],[Y(my),Y(my)],lw=0.4,color=INK)
    ax.plot([X(mx),X(mx)],[Y(my)-1.6*S1,Y(my)+1.6*S1],lw=0.4,color=INK)
# U7 relief pocket (cavity-floor recess; hidden in back-face view -> dashed)
u7x,u7y,pw,ph = 28.1,37.3,7.8,5.4
ax.add_patch(MplPoly(rrect(X(u7x-pw/2),Y(u7y-ph/2),pw*S1,ph*S1,1.0*S1),closed=True,fill=False,ec=GRY,lw=0.6,ls=(0,(4,2))))
leader(X(u7x-pw/2),Y(u7y-ph/2),100,150,"U7 RELIEF POCKET  (NOTE 7)",ha="left",fs=5.8)
dim((X(oxmin),Y(oymin)),(X(51.75),Y(oymin)),Py-20,"52.70",fs=8,side=-1)
dim((X(oxmin),Y(3.0)),(X(3.0),Y(3.0)),Py-8,"3.95",fs=6.3,side=-1)
dim((X(3.0),Y(3.0)),(X(47.8),Y(3.0)),Py-8,"44.80 ±0.05",fs=6.3,side=-1)
dim((X(47.8),Y(3.0)),(X(51.75),Y(3.0)),Py-8,"3.95",fs=6.3,side=-1)
dim((X(oxmin),Y(89.85)),(X(oxmin),Y(oymin)),Px-22,"90.80",vert=True,fs=8,side=1)
# 8-mount y-pattern: 4 rows at y 3.0 / 28.5 / 60.4 / 85.9 -> chained pitch (each row ±0.05, per C3)
dim((X(3.0),Y(28.5)),(X(3.0),Y(3.0)),Px-10,"25.50",vert=True,fs=6.0,side=1)
dim((X(3.0),Y(60.4)),(X(3.0),Y(28.5)),Px-10,"31.90",vert=True,fs=6.0,side=1)
dim((X(3.0),Y(85.9)),(X(3.0),Y(60.4)),Px-10,"25.50",vert=True,fs=6.0,side=1)
dim((X(3.0),Y(85.9)),(X(3.0),Y(3.0)),Px-17,"82.90 ±0.05 (corners)",vert=True,fs=5.6,side=1)
ax.text(X(25.4),Y(89.85)+5,"BACK FACE (outer)   SCALE 1.5:1",ha="center",fontsize=8.5,fontweight="bold",color=INK)
# hole FCF + callout (middle column)
fcf(150,182,["POS","\u00d80.10 (M)","A","B"])
leader(X(47.8),Y(85.9),150,186.3,"",ha="left")
ax.text(150,172,"8\u00d7  M2 THREAD, THRU",fontsize=7.2,fontweight="bold",color=INK)
ax.text(150,167,"\u00d81.6 TAP DRILL  \u2022  TAP FROM BACK FACE",fontsize=6.8,color=INK)
ax.text(150,162,"\u00d83.0 SPOTFACE, BACK (depth per Detail B)",fontsize=6.8,color=INK)
ax.text(150,156,"C3 = hole-pattern pitch \u00b10.05   C4 = M2 thread",fontsize=6.0,color=GRY,style="italic")
ax.text(150,148,"SECTION A-A \u2192 edge profile      DETAIL B \u2192 corner boss",fontsize=6.2,color=GRY,style="italic")

# ===================== EDGE SECTION A-A =====================
S2=13.0; EX,EY=265,202
xl=lambda v:EX+v*S2; zl=lambda z:EY+(z+border)*S2
prof=[(0.10,0.0),(wall,0.0),(wall,-border+lb),(wall+lb,-border),(wall+bbw-lb,-border),(wall+bbw,-border+lb),(wall+bbw,0.0),
      (8.5,0.0),(8.5,floor),(wall+lip_w,floor),(wall+lip_w,bb-lb),(wall+lip_w-lb,bb),(wall,bb),
      (wall,wt-ease),(wall-ease,wt),(ease,wt),(0.0,wt-ease),(0.0,0.10)]
ax.add_patch(MplPoly([(xl(x),zl(z)) for x,z in prof],closed=True,fc=HATCH,ec=INK,lw=0.8,hatch="////"))
dim((xl(0.0),zl(-border)),(xl(0.0),zl(wt)),xl(0.0)-7,"3.55",vert=True,fs=7,side=1)
dim((xl(8.5),zl(0.0)),(xl(8.5),zl(floor)),xl(8.5)+7,"1.00",vert=True,fs=6.6,side=-1)
dim((xl(8.5),zl(floor)),(xl(8.5),zl(bb)),xl(8.5)+7,"1.80 ±0.05",vert=True,fs=7,side=-1)
dim((xl(0.0),zl(0.0)),(xl(wall),zl(0.0)),zl(-border)-5,"1.0",fs=6.4,side=-1)
dim((xl(wall),zl(bb)),(xl(wall+lip_w),zl(bb)),zl(bb)+7,"2.5 W-LIP (front; note 8)",fs=5.2,side=1,txtoff=1.0)
leader(xl(2.0),zl(-border+0.06),xl(4.6),zl(-border)-6.5,"2.0 BACK BORDER (UNIFORM, 4 PL)",ha="left",fs=5.0)
dim((xl(wall+lip_w+0.25),zl(-border)),(xl(wall+lip_w+0.25),zl(0.0)),xl(wall+lip_w)+3.0,"0.15",vert=True,fs=5.8,side=-1,txtoff=1.0)
leader(xl(0.05),zl(wt-0.06),xl(1.7),zl(wt)+4.5,"0.10\u00d745\u00b0 RIM (top)",ha="left",fs=5.2)
leader(xl(0.90),zl(wt-0.06),xl(4.2),zl(wt)+9.5,"0.10\u00d745\u00b0 MOUTH",ha="left",fs=5.2)
fcf(xl(3.4),zl(bb)+8,["FLAT","0.05"]); leader(xl(2.2),zl(bb),xl(3.4),zl(bb)+8+2.3,"",ha="left")
leader(xl(3.36),zl(bb-0.04),xl(5.7),zl(2.05),"0.10\u00d745\u00b0 LIP",ha="left",fs=5.2)
leader(xl(0.05),zl(0.06),xl(-2.6),zl(0.55),"0.10\u00d745\u00b0 RIM (btm)",ha="right",fs=5.0)
leader(xl(1.08),zl(-0.10),xl(1.35),zl(-border)-9,"0.10\u00d745\u00b0 FRAME (2 PL)",ha="left",fs=5.0)
leader(xl(3.42),zl(-0.10),xl(1.35),zl(-border)-9,"",ha="left")
ax.text(xl(0.06),zl(floor)+0.8,"  floor 1.00 TRUE (0.95 local under the U7 pocket, note 7)   •   PCB recess 0.60 (0.60 mm board)",fontsize=5.7,color=GRY,va="bottom")
ax.text(EX+2,EY-11,"SECTION A-A  (edge)   SCALE 13:1",fontsize=8.5,fontweight="bold",color=INK)
ax.text(EX+2,EY-16.5,"C1 = cavity depth    C2 = PCB-rest-plane flatness    (back face down; PCB drops in from top)",fontsize=6,color=GRY,style="italic")

# ===================== DETAIL B (corner boss, section) =====================
S3=13.0; BX,BY=312,112
bx=lambda v:BX+v*S3; bz=lambda z:BY+(z+border)*S3
ax.add_patch(MplPoly([(bx(-4),bz(0)),(bx(4),bz(0)),(bx(4),bz(floor)),(bx(-4),bz(floor))],closed=True,fc=HATCH,ec=INK,lw=0.6,hatch="////"))
for s in (1,-1):
    ax.add_patch(MplPoly([(bx(x),bz(z)) for x,z in [(s*0.8,0.20),(s*1.5,0.20),(s*1.5,bb),(s*0.8,bb)]],closed=True,fc=HATCH,ec=INK,lw=0.7,hatch="////"))
    ax.add_patch(MplPoly([(bx(x),bz(z)) for x,z in [(s*1.5,-border+lb),(s*(1.5+lb),-border),(s*(2.6-lb),-border),(s*2.6,-border+lb),(s*2.6,bb),(s*1.5,bb)]],closed=True,fc=HATCH,ec=INK,lw=0.7,hatch="////"))
ax.add_patch(Rectangle((bx(-4),bz(bb)),8*S3,board*S3,fill=False,ec=GRY,lw=0.6,ls=(0,(5,3))))
ax.add_patch(Rectangle((bx(-1.0),bz(wt)),2.0*S3,1.6*S3,fill=False,ec=GRY,lw=0.6,ls=(0,(5,3))))
ax.add_patch(Rectangle((bx(-0.9),bz(0.20)),1.8*S3,(wt-0.20)*S3,fill=False,ec=GRY,lw=0.6,ls=(0,(5,3))))
ax.plot([bx(0),bx(0)],[bz(-border)-3,bz(wt)+1.6*S3+3],lw=0.4,color=INK,ls=(0,(8,3,1,3)))
dim((bx(-2.6),bz(-border)),(bx(2.6),bz(-border)),bz(-border)-12,"\u00d85.20",fs=6.8,side=-1)
dim((bx(-1.5),bz(-border)),(bx(1.5),bz(-border)),bz(-border)-5,"\u00d83.0 SPOTFACE (BACK)",fs=6.3,side=-1)
dim((bx(2.6),bz(-border)),(bx(2.6),bz(0.0)),bx(2.6)+3,"0.15",vert=True,fs=5.8,side=-1,txtoff=1.0)
leader(bx(0.0),bz(1.5),bx(4.6),bz(1.9),"M2 THREAD\n\u00d81.6 TAP DRILL, THRU\nTAP FROM BACK",ha="left",fs=6.2)
leader(bx(1.0),bz(0.20),bx(3.0),bz(0.20)-7,"spotface bottom = M2\u00d73\nscrew-tip plane (flush)",ha="left",fs=5.7)
ax.text(bx(0),bz(wt)+1.6*S3+4,"PCB + M2\u00d73 BRASS SCREW \u2014 REF, NOT THIS PART",ha="center",fontsize=5.7,color=GRY,style="italic")
leader(bx(2.6),bz(-0.07),bx(4.4),bz(-border)-2,"0.10\u00d745\u00b0 BOSS/SPOTFACE (typ)",ha="left",fs=5.0)
ax.text(BX-92,BY-25,"DETAIL B   (corner boss)   13:1",fontsize=8.5,fontweight="bold",color=INK)

# ===================== CRITICAL DIMS + NOTES =====================
ax.text(20,78,"CRITICAL DIMENSIONS  \u2014  C1 & C3 TOLERANCED \u00b10.05 (MARKED ON VIEWS); ALL OTHER FEATURES PER ISO 2768-1 (MEDIUM)",fontsize=7.4,fontweight="bold",color=INK)
ct=[["C1","Cavity depth  (boss-top plane \u2192 cavity floor)","1.80  ±0.05"],
    ["C2","PCB-rest plane flatness  (lip + 8 bosses)","FLAT  0.05"],
    ["C3","8\u00d7 mounting holes  (x 44.80; y rows 3.0/28.5/60.4/85.9)","\u00b10.05  (linear)"],
    ["C4","Mounting holes \u2014 tapped, thru, from back","M2   /   \u00d81.6 drill"]]
yy=72.5
for r in ct:
    ax.text(20,yy,r[0],fontsize=6.7,fontweight="bold",color=INK)
    ax.text(28,yy,r[1],fontsize=6.5,color=INK); ax.text(120,yy,r[2],fontsize=6.5,color=INK); yy-=4.2
ax.text(20,52.5,"NOTES",fontsize=7.4,fontweight="bold",color=INK)
notes=[
 "1. MATERIAL: TITANIUM Gr5 (TC4) = Ti-6Al-4V GRADE 5.",
 "2. FINISH: BEAD-BLAST MATTE (UNIFORM ON THE STEPPED BACK FACE). REAR ART LASER-MARKED IN THE RECESSED BACK FIELD.",
 "3. GENERAL TOLERANCE PER ISO 2768-1 (MEDIUM). C1-C4 TOLERANCED AS LISTED; C1 & C3 = ±0.05. DATUMS: A = LEFT EDGE, B = BOTTOM EDGE, C = PCB-REST PLANE.",
 "4. BRACE REGISTRATION: THE RESIN H-BRACE REGISTERS TO THIS SHELL BY FITMENT - ITS 4 OUTBOARD RAILS + THE COMPONENT POCKETS + THE BOARD PRESS-FIT. NO LOCATOR PILLARS; THE CAVITY FLOOR IS A FULL 1.00 EVERYWHERE.",
 "5. EDGE BREAKS - ALL 0.10x45°, FELT NOT SEEN, MODELED.  CALLED OUT ON SEC A-A / DETAIL B:  RIM = outer rim (top & bottom);  MOUTH = recess mouth (around PCB);  LIP = inner (cavity-side) lip edge;  FRAME = proud back-frame bottom edges;  BOSS = boss + spotface bottom edges (Detail B).  BREAK ALL OTHER EXPOSED EDGES 0.10x45°.  CONCAVE JUNCTION CORNERS (BOSS-TO-WALL + EAST-LIP STEPS) LEFT SHARP IN THE MODEL: FINISH WITH A Ø2.0 mm TOOL = R1.0 AS-MILLED. THE RESIN BRACE IS RELIEVED TO CLEAR R1.0 AT THESE CORNERS.",
 "6. FLOOR IS NOW A TRUE 1.00 (0.95 LOCAL UNDER THE U7 POCKET), AT THE ~1.0 Ti MIN-WALL GUIDANCE SO IT ALSO CLEARS ALUMINIUM / COPPER / STAINLESS.",
 "    CAVITY 1.80 +-0.05 -> 1.75 WORST-CASE, MINUS WS17 1.70 MAX (DATASHEET CASE WS17 HEIGHT) = 0.05 NON-CONTACT; THE BRACE + SOLAR-CELL SANDWICHES CARRY THE BOARD.",
 "7. U7 RELIEF POCKET: 7.8 x 5.4 CENTERED (28.1, 37.3) ON THE CAVITY FLOOR, 0.05 DEEP (LOCAL FLOOR 0.95) - U7 (1.75) KEEPS 0.10 AIR. GENERAL FLOOR 1.00. MODELED IN THE STEP.",
 "8. FRONT SUPPORT LIP IS ASYMMETRIC (SECTION A-A): WEST 2.5 / NORTH 2.0 / SOUTH 2.0 FOR PCB RIGIDITY; EAST 1.0 CLEARING THE JP1/TP1 PADS, THE NFC COIL (A GROUNDED LIP WOULD DETUNE IT), AND C7 (x49.55, THE ONE EAST-EDGE PART LEFT AFTER v4 REMOVED THE Q1/U4/R7/R9 CLAMP CLUSTER + D9/D10/D11); WIDENING TO 2.5 ONLY AT THE SOUTH END (y0-10, CLEAR OF ALL). THE EXTERIOR BACK BORDER (PLAN) IS INDEPENDENT AND UNIFORM 2.0 ON ALL 4 SIDES.",
 "9. NO INTERNAL RIBS OR SUPPORT POSTS: THE RESIN BRACE (SEPARATE PART) CARRIES CENTER SUPPORT. A PCB LAYOUT CHANGE = A BRACE REPRINT, NOT A SHELL RE-MACHINE.",
 "10. PCB RECESS = 0.60 DEEP (RECEIVES THE 0.60 mm BOARD; SLIP FIT, NOT A PRESS FIT). 3D STEP GOVERNS ALL GEOMETRY; STL NOT FOR CNC.",
 "11. PART = BACK-SHELL ONLY. PCB, RESIN BRACE, AND 8× M2×3 BRASS SLOTTED-CHEESE SCREWS (HEAD Ø3.8) SUPPLIED SEPARATELY.",
]
yy=48.0
for n in notes: ax.text(20,yy,n,fontsize=5.85,color=INK); yy-=3.32

# ===================== TITLE BLOCK =====================
tb_x,tb_y,tb_w,tb_h=288,12,120,46
ax.add_patch(Rectangle((tb_x,tb_y),tb_w,tb_h,fill=False,ec=INK,lw=0.9))
for yl in (tb_y+34,tb_y+24,tb_y+15,tb_y+8): ax.plot([tb_x,tb_x+tb_w],[yl,yl],lw=0.4,color=INK)
ax.plot([tb_x+60,tb_x+60],[tb_y,tb_y+15],lw=0.4,color=INK)
ax.text(tb_x+tb_w/2,tb_y+40,"SOLAR-GLOW DRH v3.0  —  Ti BACK-SHELL (0.6mm-BOARD DUMB BOX)",ha="center",va="center",fontsize=7.5,fontweight="bold",color=INK)
ax.text(tb_x+3,tb_y+29,"DWG  solar-glow-drh-v3_0-backshell-0p6b-brace",fontsize=5.9,va="center",color=INK)
ax.text(tb_x+tb_w-3,tb_y+29,"REV  v3.0",ha="right",fontsize=6.6,va="center",color=INK)
ax.text(tb_x+3,tb_y+19.5,"MATERIAL  Ti Gr5 (TC4)",fontsize=6.6,va="center",color=INK)
ax.text(tb_x+tb_w-3,tb_y+19.5,"FINISH  BEAD-BLAST",ha="right",fontsize=6.6,va="center",color=INK)
ax.text(tb_x+3,tb_y+11.2,"UNITS  mm",fontsize=6.4,va="center",color=INK)
ax.text(tb_x+63,tb_y+11.2,"SCALE  AS NOTED",fontsize=6.4,va="center",color=INK)
ax.text(tb_x+3,tb_y+4,"BBOX 52.70 x 90.80 x 3.55   3rd-angle",fontsize=6.0,va="center",color=INK)
ax.text(tb_x+tb_w-3,tb_y+4,"SHEET 1/1",ha="right",fontsize=6.4,va="center",color=INK)

# ===================== TOLERANCE BLOCK (above title block) =====================
tx,ty,tw,th=288,61,120,33
ax.add_patch(Rectangle((tx,ty),tw,th,fill=False,ec=INK,lw=0.9))
ax.plot([tx,tx+tw],[ty+th-6.5,ty+th-6.5],lw=0.4,color=INK)
ax.text(tx+tw/2,ty+th-3.3,"GENERAL TOLERANCES  (UNLESS OTHERWISE NOTED, mm)",ha="center",va="center",fontsize=6.2,fontweight="bold",color=INK)
tol=[("LINEAR & HOLE-POSITION DIMS","ISO 2768-m"),
     ("CAVITY DEPTH  C1  (SECTION A-A)","1.80 \u00b10.05"),
     ("HOLE-PATTERN PITCH  C3  (8 HOLES)","x 44.80 / y 25.5-31.9-25.5  \u00b10.05"),
     ("PCB-REST FLATNESS  C2","FLAT 0.05")]
yt=ty+th-11.5
for lab,val in tol:
    ax.text(tx+3,yt,lab,fontsize=5.85,va="center",color=INK)
    ax.text(tx+tw-3,yt,val,ha="right",fontsize=5.85,va="center",fontweight="bold",color=INK)
    yt-=5.3

fig.savefig("/mnt/user-data/outputs/solar-glow-drh-v3_0-backshell-0p6b-brace-DRAWING.pdf",facecolor="white")
fig.savefig("/mnt/user-data/outputs/solar-glow-drh-v3_0-backshell-0p6b-brace-DRAWING.png",dpi=150,facecolor="white")
print("saved")
