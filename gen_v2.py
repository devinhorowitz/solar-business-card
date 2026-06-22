#!/usr/bin/env python3
"""SOLAR-GLOW DRH v1 - 4-layer Gerber generator (v0 method, ported).
Pulls the verified placement/outline/keepout straight from the .kicad_pcb, adds the
inner GND/VS planes (antipads around off-net vias), hand-routes signals on F/B with
plane-stitch vias, self-checks (connectivity islands + clearance), emits Gerbers."""
import re, math, os
from shapely.geometry import Polygon, Point, LineString, box, MultiPolygon
from shapely.ops import unary_union
import shapely.affinity as aff

PCB = "/home/claude/repo/solar-glow-drh-v1.kicad_pcb"
OUT = "/home/claude/gerber-v2"; os.makedirs(OUT, exist_ok=True)
import glob as _glob
for _f in _glob.glob(os.path.join(OUT,"*")): os.remove(_f)   # clean stale layers

# ---- design rules (PCBWay 4-layer; matches v0 conventions) ----
R_CORNER = 3.0
CLR      = 0.15      # clearance floor for the shorts check
POUR_CLR = 0.16      # plane antipad / pour-to-copper clearance
EDGE_CLR = 0.30      # copper-to-edge pullback
TW, TWP, TWN = 0.22, 0.45, 0.16        # signal / power / narrow-escape trace widths
VIA_D, VIA_PAD = 0.30, 0.55            # plane-stitch + standard signal vias (drill / pad)
VIA_FD, VIA_FPAD = 0.20, 0.40          # fine QFN-escape vias (0.20mm drill class, PCBWay standard)
FINE = set()                           # (x,y) of fine vias (filled during routing)
def vpad(x,y):   return VIA_FPAD if (round(x,3),round(y,3)) in FINE else VIA_PAD
def vdrill(x,y): return VIA_FD  if (round(x,3),round(y,3)) in FINE else VIA_D
ANTIPAD = VIA_PAD/2 + POUR_CLR         # (legacy default; per-via antipad uses vpad below)
GLOW = (14.95, 40.8, 35.85, 47.0)      # DRH window: tracks ok, NO vias/pour/fp

# ===================== PLACEMENT NUDGES (replicate in KiCad) =====================
# (dx,dy) in mm applied to a footprint's pads after parse. Stitch vias auto-follow.
# Rationale: both decoupling caps sit awkwardly far from their pins AND choke the
# pin8/9/10 escape band. Moving them south/east opens the band and shortens decoupling.
NUDGE = {
    # C1 reverted to KiCad position (9.5,45.5): LDRV1 left the front, freeing the escape band; closer to VS pins = better decoupling.
    "C3": (7.5, 3.0),    # VDDIO2 decoupling: (4.0,45.5) -> (11.5,48.5), next to SJ1.2; kills the long west run. KEEP (load-bearing for VDDIO2 route).
}


# ===================== parse the kicad_pcb =====================
txt = open(PCB).read()

def fp_blocks(s, tag="(footprint "):
    out=[]; i=0
    while True:
        i=s.find(tag,i)
        if i<0: break
        d=0;j=i
        while j<len(s):
            if s[j]=='(':d+=1
            elif s[j]==')':
                d-=1
                if d==0: break
            j+=1
        out.append(s[i:j+1]); i=j+1
    return out

def rot(px,py,deg):
    a=math.radians(deg); c,s=math.cos(a),math.sin(a)
    return (px*c - py*s, px*s + py*c)

abs_pads=[]          # (ref,pn,net,cx,cy,w,h,shape,rot_total,side)   side in {F,B}
plated=[]            # (x,y,drill)  plated thru-holes (mounting + via-style)
nonplated=[]         # (x,y,drill)
CUSTOM={}            # (ref,pn) -> shapely polygon for custom-shape pads (SW1 dome)
for b in fp_blocks(txt):
    refm=re.search(r'fp_text\s+reference\s+"([^"]+)"',b); ref=refm.group(1) if refm else "?"
    atm=re.search(r'\(at\s+(-?[\d.]+)\s+(-?[\d.]+)(?:\s+(-?[\d.]+))?\)',b)
    fx,fy,frot=float(atm.group(1)),float(atm.group(2)),float(atm.group(3) or 0)
    fside="B" if re.search(r'\(footprint\s+"[^"]+"\s+\(layer\s+"B',b) else "F"
    for pb in fp_blocks(b, "(pad "):
        pm=re.match(r'\(pad\s+"([^"]*)"\s+(\S+)\s+(\S+)', pb)
        if not pm: continue
        pname,ptype,pshape=pm.group(1),pm.group(2),pm.group(3)
        at=re.search(r'\(at\s+(-?[\d.]+)\s+(-?[\d.]+)(?:\s+(-?[\d.]+))?\)', pb)
        px,py,prot=float(at.group(1)),float(at.group(2)),float(at.group(3) or 0)
        sz=re.search(r'\(size\s+([\d.]+)\s+([\d.]+)\)', pb); w,h=float(sz.group(1)),float(sz.group(2))
        dr=re.search(r'\(drill\s+([\d.]+)\)', pb); drill=float(dr.group(1)) if dr else None
        ly=re.search(r'\(layers\s+([^)]*)\)', pb); layers=ly.group(1) if ly else ""
        nt=re.search(r'\(net\s+\d+\s+"([^"]*)"\)', pb); net=nt.group(1) if nt else ""
        rx,ry=rot(px,py,frot); cx,cy=fx+rx,fy+ry; rtot=(frot+prot)%360
        ndx,ndy=NUDGE.get(ref,(0.0,0.0)); cx,cy=cx+ndx,cy+ndy   # placement nudge (documented above)
        side="B" if '"B.Cu"' in layers else ("F" if '"F.Cu"' in layers else fside)
        sh={"rect":"r","roundrect":"rr","circle":"o","oval":"o","custom":"cust"}.get(pshape,"r")
        if pshape=="custom":
            def _xf(lx,ly,_px=px,_py=py,_pr=prot):
                rlx,rly=rot(lx,ly,_pr); rfx,rfy=rot(_px+rlx,_py+rly,frot); return (fx+rfx,fy+rfy)
            prim=pb[pb.find('(primitives'):] if '(primitives' in pb else ''
            pts=[(float(a),float(b)) for a,b in re.findall(r'\(xy\s+(-?[\d.]+)\s+(-?[\d.]+)\)',prim)]
            if len(pts)>=3: CUSTOM[(ref,pname)]=Polygon([_xf(x,y) for x,y in pts]).buffer(0)
        if ptype=="np_thru_hole":
            if drill: nonplated.append((cx,cy,drill))
            continue                                  # non-plated hole: drill only, no copper pad
        if ptype=="thru_hole" and drill: plated.append((cx,cy,drill))
        abs_pads.append((ref,pname,net if net else "NC",cx,cy,w,h,sh,rtot,side))   # NC pads kept as no-net copper

# ---- v1: drop the v0 battery test sub-circuit (BT1/BT2 coin cells + D6/D7). v1 is solar-only; the cells overlapped the supercap real estate. ----
_BATT={"BT1","BT2","D6","D7"}
_batt_holes={(round(r[3],2),round(r[4],2)) for r in abs_pads if r[0] in _BATT}   # coords to also purge from plated/np drill lists
abs_pads=[r for r in abs_pads if r[0] not in _BATT]
plated  =[h for h in plated   if (round(h[0],2),round(h[1],2)) not in _batt_holes]
nonplated=[h for h in nonplated if (round(h[0],2),round(h[1],2)) not in _batt_holes]

# ---- board outline from Edge.Cuts (bbox -> rounded rect, matching v0 style) ----
ec = txt[txt.find('Edge.Cuts')-200:]
exs=[float(a) for a,b in re.findall(r'\((?:start|end|xy)\s+(-?[\d.]+)\s+(-?[\d.]+)\)', txt) ]
eys=[float(b) for a,b in re.findall(r'\((?:start|end|xy)\s+(-?[\d.]+)\s+(-?[\d.]+)\)', txt) ]
# restrict to Edge.Cuts graphic lines/arcs
edge_pts=[]
for m in re.finditer(r'\(gr_(?:line|arc)\b(.*?)\)\s*\(layer\s+"Edge\.Cuts"\)', txt, re.S):
    for a,bb in re.findall(r'\((?:start|mid|end)\s+(-?[\d.]+)\s+(-?[\d.]+)\)', m.group(1)):
        edge_pts.append((float(a),float(bb)))
if edge_pts:
    xs=[p[0] for p in edge_pts]; ys=[p[1] for p in edge_pts]
    BX0,BY0,BX1,BY1=min(xs),min(ys),max(xs),max(ys)
else:
    BX0,BY0,BX1,BY1=0,0,50.8,88.9
W,H = BX1-BX0, BY1-BY0

print(f"parsed: {len(abs_pads)} netted pads, {len(plated)} plated TH, {len(nonplated)} np TH")
print(f"board bbox: ({BX0:.2f},{BY0:.2f}) -> ({BX1:.2f},{BY1:.2f})  = {W:.2f} x {H:.2f} mm")
from collections import Counter
print("pads/side:", dict(Counter(rec[9] for rec in abs_pads)))
print("distinct nets:", len({rec[2] for rec in abs_pads}))
for rec in abs_pads[:4]: print("  ", rec)

# ===================== geometry =====================
def pad_poly(cx,cy,w,h,sh,rt,grow=0.0):
    if sh=="o":
        r=min(w,h)/2
        g=box(-(w/2-r),-(h/2-r),(w/2-r),(h/2-r)).buffer(r+grow,join_style=1,resolution=24)
    elif sh=="rr":
        r=min(w,h)*0.25
        g=box(-(w/2-r),-(h/2-r),(w/2-r),(h/2-r)).buffer(r+grow,join_style=1,resolution=16)
    else:
        g=box(-w/2-grow,-h/2-grow,w/2+grow,h/2+grow)
    if rt: g=aff.rotate(g,rt,origin=(0,0))
    return aff.translate(g,cx,cy)
def trace_poly(pts,wd,grow=0.0): return LineString(pts).buffer(wd/2+grow,cap_style=1,join_style=1,resolution=12)
def via_poly(x,y,grow=0.0): return Point(x,y).buffer(vpad(x,y)/2+grow,resolution=24)
def get_pad_poly(ref,pn,x,y,w,h,sh,rt,grow=0.0):
    if sh=="cust" and (ref,pn) in CUSTOM:
        g=CUSTOM[(ref,pn)]; return g.buffer(grow,join_style=1) if grow else g
    return pad_poly(x,y,w,h,sh,rt,grow)

OUTLINE=box(BX0,BY0,BX1,BY1).buffer(-R_CORNER,join_style=1,resolution=20).buffer(R_CORNER,join_style=1,resolution=20)
CU_CLIP=OUTLINE.buffer(-EDGE_CLR)
GLOWBOX=box(*GLOW)
def in_void(x,y): return GLOW[0]<=x<=GLOW[2] and GLOW[1]<=y<=GLOW[3]

# ---- plane-stitch vias: drop one at each LARGER GND/VS pad (skip fine-pitch QFN pins, thru-hole MH, and void pads -> those are routed) ----
PLANE_VIAS=[]; seen=set()
for ref,pn,net,x,y,w,h,sh,rt,side in abs_pads:
    if net not in ("GND","VS"): continue
    if ref.startswith("MH"): continue
    if ref=="U1": continue                     # U1 EP/pins handled manually (EP stitch + escape vias); skip auto-via on LDRV1's descent
    if in_void(x,y): continue
    if min(w,h)<0.55: continue                 # too small to drop a via in (QFN pins) -> route later
    key=(round(x,2),round(y,2))
    if key in seen: continue
    seen.add(key); PLANE_VIAS.append((net,x,y,side))

VIAS=list(PLANE_VIAS)          # + signal/escape vias added in the routing stage
PAD={(r,pn):(x,y) for r,pn,n,x,y,w,h,sh,rt,s in abs_pads}
def P(ref,pn): return PAD[(ref,pn)]
# ===================== TRACES (net, side, [pts], width) =====================
T=[
 # ---- LED cathodes K2-K5: each LED cathode -> its ballast top (back, local; trace crosses the void edge, allowed) ----
 ("K2","B",[P("D2","K"),P("R1","1")],TW),
 ("K3","B",[P("D3","K"),P("R2","1")],TW),
 ("K4","B",[P("D4","K"),P("R3","1")],TW),
 ("K5","B",[P("D5","K"),P("R4","1")],TW),
 # ---- LED anodes (VS): stub each anode straight down out of the window to its own VS via -> In2 plane (left of the cathode traces, no crossing) ----
 ("VS","B",[P("D2","A"),(14.8,47.6)],TW),
 ("VS","B",[P("D3","A"),(21.1,47.6)],TW),
 ("VS","B",[P("D4","A"),(27.4,47.6)],TW),
 ("VS","B",[P("D5","A"),(33.4,47.6)],TW),
 # ---- U1 QFN GND/VS escape (TWN): GND pins fold into the EP (which carries stitch vias -> In1); VS pins fan out to escape vias -> In2 ----
 ("GND","B",[P("U1","19"),(10.4,40.5)],TWN),     # right-edge GND pin -> into EP
 ("GND","B",[P("U1","25"),(9.5,40.05)],TWN),     # bottom-edge GND pin -> up into EP
 ("VS","B",[P("U1","18"),(12.2,40.9),(13.0,43.0)],TWN),  # right-edge VS pin -> B due-E at y40.9 (clears pin17 NC) -> SE to escape via (clear of SCL F corridor)
 ("VS","B",[P("U1","24"),(9.9,38.3)],TWN),       # bottom-edge VS pin -> fine escape via -> In2
 # ---- MID bus: 4 supercap mid taps (SC1.N/SC2.P top, SC3.N/SC4.P bottom) + 3 U2 balancer pins. Open-area routing, skirting RIGHT of the glow window. ----
 # ---- MID balance bus: moved to In2 (back-side cleanup). 6 surfacing vias; SC1.N/SC2.P land @y26 (UNDER panel -> hidden), U2.4/U2.6 fine via-in-pad, SC3.N/SC4.P @y57.5. U2.6-U2.7 stay bridged on B so one via serves the pair. ----
 ("MID","In2",[(15.5,26.0),(35.3,26.0)],TW),                                         # top pair bus on In2 (y26 = under panel, both vias hidden)
 ("MID","In2",[(35.3,26.0),(38.5,26.0),(38.5,41.8),P("U2","4")],TW),                 # down right margin (E of glow window) -> U2.4 via
 ("MID","In2",[P("U2","4"),(40.4,45.0),(47.0,45.0),(47.0,40.5),P("U2","6")],TW),     # around U2 bottom (y45) -> right trunk -> U2.6 via
 ("MID","B",[P("U2","6"),P("U2","7")],TW),                                           # U2.6 - U2.7 bridged on B (one via serves both)
 ("MID","In2",[(47.0,45.0),(47.0,61.0),(35.3,61.0),(15.5,61.0)],TW),                 # trunk down -> along y61 (SC3.N/SC4.P pads are horizontal) -> SC4.P via @(35.3,61) -> SC3.N via @(15.5,61)
 # ---- VIN solar input: PV1 + pads tied on front; Pt -> down east region (dodging MH4) -> via -> D1.A. (R5.1 divider tap deferred.) ----
 ("VIN","F",[P("PV1","P"),P("PV1","Pt")],TW),                                        # PV1 + pads tied (front, top)
 ("VIN","F",[P("PV1","Pt"),(45.5,25.0)],TW),                                         # short F stub from PV1.Pt, stays under panel
 ("VIN","In3",[(45.5,25.0),(44.8,28.0),(44.8,43.5)],TW),                             # In3 descent W of MH4 (drops to inner AT panel edge -> exposed part hidden)
 ("VIN","B",[(44.8,43.5),P("D1","A")],TW),                                           # via drop -> D1.A
 ("VIN","In3",[(44.8,43.5),(44.8,56.0),(3.3,56.0),(3.3,51.0),P("R5","1")],TW),       # In3: drop S of D1, W across the bottom lane (y56, S of JP2 / N of MID trunk), up W of JP2.1, into R5.1
 # ---- U1 bottom-edge signal escape: fine 0.20mm staggered vias -> hop to F -> non-art corridors -> drop back to B. ----
 # NOTE: LDRV1/2/3/4 reverse (pin x-order opposite ballast x-order). Resolved WITHOUT schematic reassignment by the layer trick: F descents run all the way south PAST the back-side caps/cathodes (F is clear there), drop to B *south* of the ballast row, and return E in nested lanes (cathode K-diagonals are all N of the ballasts, so zero collisions / zero reversal dips).
 ("LDRV1","B",[P("U1","26"),(9.3,37.6)],TWN),                                        # dog-bone NE -> outer-row fine via
 ("LDRV1","In2",[(9.3,37.6),(9.3,50.3),(16.6,50.3),P("R1","2")],TW),                 # In2: descend x9.3 -> N-corridor y50.3 -> up onto R1.2 (via-in-pad) [F-free]
 # ---- LDRV2/3/4: reversal handled by descend->parallel-lane->rise topology (no crossing). Descents on inner layers clear the B-side caps' pads; only via rings to dodge. ----
 ("LDRV2","B",[P("U1","27"),(8.7,38.0)],TWN),                                        # pin27 dog-bone N -> fine escape via
 ("LDRV2","In3",[(8.7,38.0),(9.3,39.0),(9.3,50.5),(22.91,50.5),P("R2","2")],TW),     # In3: thread EP gap x9.3, N-corridor y50.5 (N of SB bridges), up onto R2.2 (via-in-pad)
 ("LDRV3","B",[P("U1","28"),(8.0,37.7)],TWN),                                        # pin28 dog-bone N -> fine escape via (staggered N of LDRV2)
 ("LDRV3","In2",[(8.0,37.7),(7.9,39.0),(7.9,50.95),(29.2,50.95),P("R3","2")],TW),    # In2: descend W of EP, N-corridor y50.95 (clears C5.2 GND via + SB), up onto R3.2
 ("LDRV4","B",[P("U1","1"),(6.8,39.3)],TWN),                                         # left-edge pin1 -> fine escape via (W)
 ("LDRV4","In3",[(6.8,39.3),(7.9,41.2),(7.9,51.25),(35.2,51.25),P("R4","2")],TW),    # In3: W descent, N-corridor y51.25 (N of SB), up onto R4.2
 # ---- SB1-4 disable jumpers: each ballast (LDRVn) also feeds SBn.1; SBn.2 is GND. Short B stub ballast -> bridge pad. ----
 ("LDRV1","B",[P("R1","2"),P("SB1","1")],TW),
 ("LDRV2","B",[P("R2","2"),P("SB2","1")],TW),
 ("LDRV3","B",[P("R3","2"),P("SB3","1")],TW),
 ("LDRV4","B",[P("R4","2"),P("SB4","1")],TW),
 # ---- VSENSE: pin3 -> In2 W-zone descent -> divider node R6.1; node tied R5.2 (direct) + C5.1 (B dip under R6.2 GND) ----
 ("VSENSE","B",[P("U1","3"),(6.0,40.7)],TWN),                                        # pin3 escape W -> fine via
 ("VSENSE","In2",[(6.0,40.7),(5.5,41.0),(5.5,50.4)],TW),                            # In2 W-zone descent -> R6.1 (VSENSE node)
 ("VSENSE","B",[P("R6","1"),P("R5","2")],TWN),                                       # R6.1 - R5.2 (adjacent VSENSE pads)
 ("VSENSE","B",[P("R6","1"),(5.69,51.5),(7.69,51.5),P("C5","1")],TWN),               # R6.1 - C5.1 (B dip y51.5 dodges R6.2 GND pad)
 # ---- PC0: pin6 -> In3 W-zone descent (between R5.2/R6.1) -> JP2.2 ----
 ("PC0","B",[P("U1","6"),(7.0,41.7),(5.0,42.4)],TWN),                                           # pin6 escape W -> fine via
 ("PC0","In3",[(5.0,42.4),(4.9,43.5),(4.9,54.0),P("JP2","2")],TW),                   # In3 W-zone -> divider gap -> JP2.2
 # ---- PC1: pin7 -> In2 middle-zone descent (between R6.2/C5.2 GND) -> JP2.3 ----
 ("PC1","B",[P("U1","7"),(7.3,42.8)],TWN),                                           # pin7 escape W -> fine via
 ("PC1","In2",[(7.3,42.8),(7.4,44.5),(7.4,52.5),(6.63,53.8),P("JP2","3")],TW),       # In2 mid-zone -> below divider -> JP2.3
 # UPDI: fine via -> F T-junction (north to TC1.1, west to J1.1)
 ("UPDI","B",[P("U1","23"),(10.5,37.6)],TWN),                                        # dog-bone NE -> outer-row fine via
 ("UPDI","In3",[(10.5,37.6),(11.5,37.0),(11.5,16.2),(10.87,15.63)],TW),              # In3 north up x11.5 (E of TC1.3 GND via) -> TC1.1 (via-in-pad) [F-free; mostly under panel]
 ("UPDI","In3",[(10.5,37.6),(9.0,36.0),(4.7,36.0)],TW),                              # In3 west (N of C2 VS via) to J1 column [F-free]
 ("UPDI","B",[(4.7,36.0),P("J1","1")],TW),                                           # via drop -> J1.1
 # ---- SDA: route like SCL/VDDIO2 - stay on B under LDRV1/2/3's F descents (free, diff layer), then pop to F for the north-run. No escape/dip vias to crowd the SW corridor. ----
 ("SDA","B",[P("U1","8"),(8.3,44.5),(12.0,44.5)],TWN),                               # B: S off pin8 -> E under LDRV1/2/3 F descents -> F-transition
 ("SDA","In3",[(12.0,44.5),(12.0,36.7),P("JP1","1")],TW),                            # In3 diagonal up (W of JP1.3 GND via + JP1.2 via) -> JP1.1 drop [F-free]
 # ---- SCL: pin9 (B) runs on B under LDRV1's F descent AND SDA's F north-run (both free, diff layer), then pops to F for a clean north-run up the corridor -> JP1.2 ----
 ("SCL","B",[P("U1","9"),(8.7,44.0),(12.5,44.0)],TWN),                               # B: S off pin9 -> E under LDRV1(F) + SDA(F) -> F-transition
 ("SCL","In2",[(12.5,44.0),(12.3,43.0),(12.3,39.2),P("JP1","2")],TW),                            # In2 diagonal up (E of SDA, W of GND via) -> JP1.2 drop [F-free]
 # ---- VDDIO2: pin10 (B) diagonals E of LDRV1 (S of SCL's deeper run, so no cross), E to SJ1.2; C3 (nudged next to SJ1.2) chains off SJ1.2 ----
 ("VDDIO2","B",[P("U1","10"),(9.1,43.55),(13.71,43.55),P("SJ1","2")],TWN),           # SJ1 branch: S off pin10 (clear pin11) -> E (threads NC pins / SCL via) -> S into SJ1.2
 ("VDDIO2","B",[P("SJ1","2"),(12.6,47.0),P("C3","1")],TWN),                          # C3 branch: SJ1.2 -> SW hop -> C3.1
 # ---- PA4: left-edge pin2 -> fine escape -> F west (between J1.2/J1.3) -> far-west descent -> JP2.1 via-in-pad ----
 ("PA4","B",[P("U1","2"),(6.0,40.1)],TWN),                                           # escape west off pin2
 ("PA4","In2",[(6.0,40.1),(3.0,40.1),(3.0,54.0),(4.09,54.9)],TW),                     # In3 west (thread J1) -> descend far-west -> JP2.1 via-in-pad [F-free]
 # ---- BTN: left-edge pin5 -> escape -> F down west edge -> across south of supercaps -> SW1.1 (front-side dome pad) ----
 ("BTN","B",[P("U1","5"),(6.0,41.3)],TWN),                                           # escape west off pin5
 ("BTN","In2",[(6.0,41.3),(6.05,42.5),(6.05,71.0),(42.0,71.0),(42.0,77.9)],TW),      # In2: down W margin (threads divider/JP2 via gaps @x6.05) -> across y71 (S of MID, between SC3/SC4 pad rows) -> E of dome GND via [F-free]
 ("BTN","F",[(42.0,77.9),P("SW1","1")],TW),                                          # short F stub into SW1.1 (via-near-pad: snap dome needs a flat contact, no via-in-pad)
]
VIAS += [("VS",14.8,47.6,"B"),("VS",21.1,47.6,"B"),("VS",27.4,47.6,"B"),("VS",33.4,47.6,"B"),   # LED-anode VS stitch
         ("GND",8.55,40.9,"B"),("GND",10.1,40.9,"B"),                                           # U1 EP GND stitch vias (left one W of LDRV1 F descent)
         ("VS",13.0,43.0,"B"),("VS",9.9,38.3,"B"),                                               # U1 VS escape vias (pin18 relocated clear of SCL; bottom = fine)
         ("GND",40.4,73.5,"F"),                                                                   # SW1 dome GND return -> In1 (on the horseshoe, clear of BTN)
         ("VIN",45.5,25.0,"FB"),("VIN",44.8,43.5,"FB"),("VIN",3.69,50.4,"FB"),                                          # VIN F->B at D1.A + In3->B at R5.1
         ("MID",15.5,26.0,"FB"),("MID",35.3,26.0,"FB"),("MID",40.4,41.8,"FB"),("MID",45.6,40.5,"FB"),("MID",15.5,61.0,"FB"),("MID",35.3,61.0,"FB"),  # MID bus -> In2 surfacing vias (SC1.N/SC2.P hidden @y26; U2.4/U2.6 fine; SC3.N/SC4.P @y57.5)
         ("LDRV1",9.3,37.6,"FB"),("LDRV1",16.6,49.6,"FB"),                                        # LDRV1 fine escape + drop at R1.2
         ("UPDI",10.5,37.6,"FB"),("UPDI",10.87,15.63,"FB"),("UPDI",4.7,36.0,"FB"),                # UPDI fine escape + drops at TC1.1 / J1.1
         ("PA4",6.0,40.1,"FB"),("PA4",4.09,54.9,"FB"),                                           # PA4 escape + JP2.1 via-in-pad
         ("BTN",6.0,41.3,"FB"),("BTN",42.0,77.9,"FB"),                                                                    # BTN escape (B->F); SW1.1 is front-side, no drop via
         ("SDA",12.0,44.5,"FB"),("SDA",13.7,36.36,"FB"),                                          # SDA F-transition (fine) + JP1.1
         ("SCL",12.5,44.0,"FB"),("SCL",13.7,38.9,"FB"),                                          # SCL F-transition (fine) + JP1.2
         ("LDRV2",8.7,38.0,"B"),("LDRV2",22.91,49.6,"FB"),                                         # LDRV2 fine escape + riser
         ("LDRV3",8.0,37.7,"B"),("LDRV3",29.2,49.6,"FB"),                                          # LDRV3 fine escape + riser
         ("LDRV4",6.8,39.3,"B"),("LDRV4",35.2,49.6,"FB"),                                         # LDRV4 fine escape + riser
         ("VSENSE",6.0,40.7,"B"),("VSENSE",5.5,50.4,"FB"),                                                                 # VSENSE pin3 escape
         ("PC0",5.0,42.4,"B"),("PC0",5.37,54.9,"FB"),                                             # PC0 escape + JP2.2 via-in-pad
         ("PC1",7.3,42.8,"B"),("PC1",6.63,54.9,"FB")]                                             # PC1 escape + JP2.3 via-in-pad
FINE.update({(9.9,38.3),(9.3,37.6),(10.5,37.6),(6.0,40.1),(6.0,41.3),(13.0,43.0),(12.0,44.5),(12.5,44.0),
             (8.7,38.0),(8.0,37.7),(6.8,39.3),
             (6.0,40.7),(5.0,42.4),(7.3,42.8),(5.5,50.4),
             (40.4,41.8),(45.6,40.5)})  # QFN-edge + left-escape + pin18-VS + SDA/SCL-transition + LDRV2/3/4 escapes + VSENSE/PC0/PC1 escapes + MID U2.4/U2.6 via-in-pad

# thru-hole features for plane antipad logic: (net,x,y). MH are GND.
THRU=[("GND",x,y) for x,y,d in plated] + [(n,x,y) for (n,x,y,_) in VIAS]

# ===================== copper per (net, side) =====================
def build_copper(grow=0.0):
    cu={}
    def add(net,side,g): cu.setdefault((net,side),[]).append(g)
    for ref,pn,net,x,y,w,h,sh,rt,side in abs_pads:
        add(net,side,get_pad_poly(ref,pn,x,y,w,h,sh,rt,grow))
    for net,side,pts,wd in T: add(net,side,trace_poly(pts,wd,grow))
    for net,x,y,lands in VIAS:                  # 6-layer: ALL vias are through -> annular ring on every signal layer
        for L in ("F","In2","In3","B"): add(net,L,via_poly(x,y,grow))
    return {k:unary_union(v) for k,v in cu.items()}

# ===================== inner planes (In1=GND, In4=VS) with antipads; In2/In3 are signal =====================
def build_pours():
    region=CU_CLIP.difference(GLOWBOX)          # board interior, void carved out
    in1=region; in4=region
    apd=[]
    for net,x,y in THRU:
        c=Point(x,y).buffer(vpad(x,y)/2+POUR_CLR,resolution=20)
        if net!="GND": in1=in1.difference(c)    # off-net through-via -> antipad on GND plane (In1)
        if net!="VS":  in4=in4.difference(c)    # off-net through-via -> antipad on VS plane (In4)
    for x,y,d in nonplated:                      # non-plated holes antipad both
        c=Point(x,y).buffer(d/2+POUR_CLR,resolution=20); in1=in1.difference(c); in4=in4.difference(c)
    return {"In1":in1,"In4":in4}

print("plane-stitch vias:", len(PLANE_VIAS), " (GND",sum(1 for n,*_ in PLANE_VIAS if n=='GND'),"/ VS",sum(1 for n,*_ in PLANE_VIAS if n=='VS'),")")
_p=build_pours()
print(f"In1 GND plane area={_p['In1'].area:.0f}mm2   In4 VS plane area={_p['In4'].area:.0f}mm2")

# ===================== assemble layers =====================
cu=build_copper(0.0); pours=build_pours()
def cu_side(side): return unary_union([g for (n,s),g in cu.items() if s==side])
Fcu, Bcu = cu_side("F"), cu_side("B")
In2cu, In3cu = cu_side("In2"), cu_side("In3")     # inner SIGNAL layers
In1, In4 = pours["In1"], pours["In4"]              # GND / VS planes
# soldermask: open over component pads on each outer side + the bare-FR4 glow window. Vias are TENTED (cleaner card face).
Fpads=unary_union([get_pad_poly(r,p,x,y,w,h,sh,rt) for r,p,n,x,y,w,h,sh,rt,s in abs_pads if s=="F"])
Bpads=unary_union([get_pad_poly(r,p,x,y,w,h,sh,rt) for r,p,n,x,y,w,h,sh,rt,s in abs_pads if s=="B"])
Fmask=unary_union([Fpads,GLOWBOX]); Bmask=unary_union([Bpads,GLOWBOX])

# ---- front QR: REMOVED for now (to be recalibrated for placement later). Top copper kept clear for mask/copper art. ----

# ---- front DRH monogram in the TOP COPPER: copper field over the glow window with the letters cut out ----
# (v0-faithful: letters are bare FR4 -> they GLOW when the rear LEDs backlight them; the field reads as gold ENIG)
from matplotlib.textpath import TextPath as _TP
from matplotlib.font_manager import FontProperties as _FP
from matplotlib.path import Path as _MP
from functools import reduce as _reduce
import numpy as _np
_JBX=_FP(fname="/home/claude/revj/fonts/JetBrainsMono-ExtraBold.ttf")
def text_shapely(txt,cx,cy,h,track=0.04,prop=_JBX):
    S=72.0; adv=S*(0.6+track); vv=[]; cc=[]; xo=0.0
    for ch in txt:
        if ch!=" ":
            t=_TP((0,0),ch,size=S,prop=prop)
            if len(t.vertices): vv.append(t.vertices+[xo,0]); cc.append(t.codes)
        xo+=adv
    path=_MP(_np.vstack(vv),_np.concatenate(cc))
    cont=[c for c in path.to_polygons(closed_only=True) if len(c)>=4]
    polys=[Polygon(c).buffer(0) for c in cont]
    geom=_reduce(lambda a,b:a.symmetric_difference(b),polys)
    mnx,mny,mxx,mxy=geom.bounds; sc=h/(mxy-mny)
    geom=aff.scale(geom,xfact=sc,yfact=sc,origin=(mnx,mny)); mnx,mny,mxx,mxy=geom.bounds
    return aff.translate(geom, cx-(mnx+mxx)/2, cy-(mny+mxy)/2)
DRH_CX,DRH_CY = (GLOW[0]+GLOW[2])/2,(GLOW[1]+GLOW[3])/2
DRH=aff.scale(text_shapely("DRH",DRH_CX,DRH_CY,4.6,track=0.20), xfact=1,yfact=-1,origin=(DRH_CX,DRH_CY))  # pre-flip into KiCad Y-down so it's upright after the Gerber flip
DRH_FIELD=box(GLOW[0]+0.25,GLOW[1]+0.25,GLOW[2]-0.25,GLOW[3]-0.25).difference(DRH.buffer(0.12))           # gold plate inside window, letters carved out
Fcu=unary_union([Fcu,DRH_FIELD])            # monogram plate in the top copper (isolated); window mask already open -> gold field + glowing FR4 letters
print(f"DRH monogram: text bounds(kicad)={tuple(round(v,1) for v in DRH.bounds)}  field area={DRH_FIELD.area:.1f}mm2")

# ---- KiCad Y-down -> Gerber Y-up (re-express in Gerber convention; matches KiCad's own export, NOT a mirror) ----
YC=BY0+BY1
def fy(g): return aff.scale(g,xfact=1,yfact=-1,origin=(0,YC/2))
def fyv(x,y): return (x, YC-y)
Fcu_o,Bcu_o,In1_o,In2s_o,In3s_o,In4_o,Fmask_o,Bmask_o,OUT_o=(fy(Fcu),fy(Bcu),fy(In1),fy(In2cu),fy(In3cu),fy(In4),fy(Fmask),fy(Bmask),fy(OUTLINE))

# ===================== RS-274X emit (from v0) =====================
def C(v): return str(int(round(v*1e6)))
def ring(coords):
    pts=list(coords)
    if pts and pts[0]==pts[-1]: pts=pts[:-1]
    out=[f"X{C(pts[0][0])}Y{C(pts[0][1])}D02*"]+[f"X{C(x)}Y{C(y)}D01*" for (x,y) in pts[1:]]
    out.append(f"X{C(pts[0][0])}Y{C(pts[0][1])}D01*"); return out
def polys_of(geom):
    if geom.is_empty: return []
    if geom.geom_type=="Polygon": return [geom]
    out=[]
    for g in getattr(geom,"geoms",[]):
        if g.geom_type=="Polygon" and not g.is_empty: out.append(g)
        elif g.geom_type=="MultiPolygon": out+=[p for p in g.geoms if not p.is_empty]
    return out
def emit_fill(fn,geom,ff):
    L=[f"%TF.FileFunction,{ff}*%","%FSLAX46Y46*%","%MOMM*%","G01*"]
    for pl in sorted(polys_of(geom),key=lambda p:p.area,reverse=True):
        L.append("%LPD*%"); L.append("G36*"); L+=ring(pl.exterior.coords); L.append("G37*")
        if pl.interiors:
            L.append("%LPC*%")
            for r in pl.interiors: L.append("G36*"); L+=ring(r.coords); L.append("G37*")
    L.append("M02*"); open(os.path.join(OUT,fn),"w").write("\n".join(L)+"\n")
def emit_outline(fn,geom):
    L=["%TF.FileFunction,Profile,NP*%","%FSLAX46Y46*%","%MOMM*%","%ADD10C,0.100*%","G01*","D10*"]
    for pl in polys_of(geom):
        for rng in [pl.exterior]+list(pl.interiors):
            pts=list(rng.coords)
            if len(pts)<2: continue
            L.append(f"X{C(pts[0][0])}Y{C(pts[0][1])}D02*"); L+=[f"X{C(x)}Y{C(y)}D01*" for (x,y) in pts[1:]]
    L.append("M02*"); open(os.path.join(OUT,fn),"w").write("\n".join(L)+"\n")
def emit_drill(fn, holes):   # holes: list of (x,y,dia)
    by={}
    for x,y,d in holes: by.setdefault(round(d,3),[]).append((x,y))
    L=["M48",";SOLAR-GLOW DRH v1","METRIC","G90"]
    tools=sorted(by)
    for i,d in enumerate(tools): L.append(f"T{i+1}C{d:.3f}")
    L.append("%")
    for i,d in enumerate(tools):
        L.append(f"T{i+1}")
        L+=[f"X{x:.3f}Y{y:.3f}" for (x,y) in by[d]]
    L.append("M30"); open(os.path.join(OUT,fn),"w").write("\n".join(L)+"\n")

B="solar-glow-drh-v2"
emit_fill(f"{B}.GTL", Fcu_o,  "Copper,L1,Top")
emit_fill(f"{B}.G1",  In1_o,  "Copper,L2,Inr")    # GND plane
emit_fill(f"{B}.G2",  In2s_o, "Copper,L3,Inr")    # signal
emit_fill(f"{B}.G3",  In3s_o, "Copper,L4,Inr")    # signal
emit_fill(f"{B}.G4",  In4_o,  "Copper,L5,Inr")    # VS plane
emit_fill(f"{B}.GBL", Bcu_o,  "Copper,L6,Bot")
emit_fill(f"{B}.GTS", Fmask_o, "Soldermask,Top")
emit_fill(f"{B}.GBS", Bmask_o, "Soldermask,Bot")
emit_outline(f"{B}.GKO", OUT_o)
emit_drill(f"{B}.XLN", [(*fyv(x,y),vdrill(x,y)) for n,x,y,lands in VIAS]+[(*fyv(x,y),d) for x,y,d in plated])
emit_drill(f"{B}-NPTH.XLN", [(*fyv(x,y),d) for x,y,d in nonplated])
print("emitted:", sorted(f for f in os.listdir(OUT)))

# ===================== validate with gerbonara =====================
try:
    from gerbonara import GerberFile, ExcellonFile
    for f in ["GTL","G1","G2","G3","G4","GBL","GTS","GBS","GKO"]:
        g=GerberFile.open(os.path.join(OUT,f"{B}.{f}")); print(f"  {f}: OK, {len(list(g.objects))} objs")
    for f in ["XLN","-NPTH.XLN"]:
        d=ExcellonFile.open(os.path.join(OUT,f"{B}{'.' if not f.startswith('-') else ''}{f}")); print(f"  {f}: OK, {len(list(d.objects))} holes")
except Exception as e:
    print("gerbonara:", repr(e))

# ===================== preview (4 panels) =====================
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.path import Path as MPath; from matplotlib.patches import PathPatch
def fillgeom(ax,geom,color,z=1,alpha=1.0):
    for pl in polys_of(geom):
        verts=[];codes=[]
        for rng in [pl.exterior]+list(pl.interiors):
            cs=list(rng.coords)
            if len(cs)<3: continue
            verts+=cs; codes+=[MPath.MOVETO]+[MPath.LINETO]*(len(cs)-2)+[MPath.CLOSEPOLY]
        if verts: ax.add_patch(PathPatch(MPath(verts,codes),fc=color,ec="none",zorder=z,alpha=alpha))
GLOW_o=fy(GLOWBOX)
fig,axs=plt.subplots(1,4,figsize=(16,9)); fig.patch.set_facecolor("#0a0a0c")
panels=[("F.Cu (GTL)",Fcu_o,"#c9a227"),("In2 sig (G2)",In2s_o,"#5fb87a"),("In3 sig (G3)",In3s_o,"#b87a5f"),("B.Cu (GBL)",Bcu_o,"#c9a227")]
for ax,(ttl,geom,col) in zip(axs,panels):
    fillgeom(ax,OUT_o,"#16161b",0)
    fillgeom(ax,geom,col,2)
    fillgeom(ax,GLOW_o.difference(geom),"#3a2f18",1)         # bare-FR4 window
    for n,x,y,lands in VIAS:
        fx,fyy=fyv(x,y)
        ax.add_patch(plt.Circle((fx,fyy),vpad(x,y)/2,fc="#e8d9a0",ec="none",zorder=4)); ax.add_patch(plt.Circle((fx,fyy),vdrill(x,y)/2,fc="#0a0a0c",zorder=5))
    ax.set_xlim(BX0-2,BX1+2); ax.set_ylim(BY0-2,BY1+2)       # Gerber Y-up
    ax.set_aspect("equal"); ax.axis("off"); ax.set_title(ttl,color="#d9a23a",fontsize=11)
fig.suptitle("SOLAR-GLOW DRH v2 - 6-layer 0.8mm (Y-up): F / In1 GND / In2 sig / In3 sig / In4 VS / B  -- signal layers shown",color="#d9a23a",fontsize=12,y=0.97)
fig.tight_layout(rect=[0,0,1,0.95]); fig.savefig("/mnt/user-data/outputs/solar-glow-drh-v2-gerber-preview.png",dpi=150,facecolor="#0a0a0c")
print("saved preview")

# ===================== self-DRC: connectivity (4-layer) + shorts =====================
from collections import defaultdict
def _explode(g):
    return [gg for gg in (g.geoms if g.geom_type=="MultiPolygon" else [g]) if not gg.is_empty]
def connectivity():
    cu=build_copper(0.0); pours=build_pours()
    pieces=defaultdict(list)                      # net -> [(layer,poly)]
    for (n,s),g in cu.items():
        if n in("?","NC",""): continue
        for gg in _explode(g): pieces[n].append((s,gg))
    for gg in _explode(pours["In1"]): pieces["GND"].append(("In1",gg))
    for gg in _explode(pours["In4"]): pieces["VS"].append(("In4",gg))
    # bridges: through-vias join F+In2+In3+B, plus In1 if GND / In4 if VS; plated MH (GND thru: all sig + In1)
    bridges=[(n,x,y,("F","In2","In3","B")+(("In1",) if n=="GND" else ())+(("In4",) if n=="VS" else ())) for n,x,y,lands in VIAS]
    bridges+=[("GND",x,y,("F","In2","In3","B","In1")) for x,y,d in plated]
    rep={}
    for net,pl in pieces.items():
        par=list(range(len(pl)))
        def find(a):
            while par[a]!=a: par[a]=par[par[a]]; a=par[a]
            return a
        def uni(a,b): par[find(a)]=find(b)
        for bn,bx,by,bl in bridges:
            if bn!=net: continue
            p=Point(bx,by); t=[i for i,(l,poly) in enumerate(pl) if l in bl and poly.distance(p)<vpad(bx,by)/2+0.06]
            for i in t[1:]: uni(t[0],i)
        rep[net]=(len({find(i) for i in range(len(pl))}), len(pl))
    return rep
def shorts():
    cu=build_copper(0.0); pours=build_pours()
    lay=defaultdict(list)
    for (n,s),g in cu.items():
        if n in("?",""): continue          # keep "NC" as an obstacle vs real nets (NC-vs-NC skipped by n1==n2 below)
        lay[s].append((n,g))
    lay["In1"].append(("GND",pours["In1"])); lay["In4"].append(("VS",pours["In4"]))
    viol=[]
    for L,items in lay.items():
        for i in range(len(items)):
            for j in range(i+1,len(items)):
                (n1,g1),(n2,g2)=items[i],items[j]
                if n1==n2 or g1.is_empty or g2.is_empty: continue
                d=g1.distance(g2)
                if d<CLR-1e-3:
                    from shapely.ops import nearest_points
                    a,b=nearest_points(g1,g2)
                    viol.append((L,n1,n2,round(d,3),round((a.x+b.x)/2,1),round((a.y+b.y)/2,1)))
    return viol

print("\n=== CONNECTIVITY (islands / pieces) ===")
rep=connectivity()
allnets=sorted(rep, key=lambda n:(rep[n][0]==1, n))
for net in allnets:
    isl,npc=rep[net]; print(f"  {net:5s} islands={isl:2d} pieces={npc:2d} {'OK' if isl==1 else '<-- '+str(isl)+' islands'}")
nbad=sum(1 for n in rep if rep[n][0]!=1)
print(f"  --> {len(rep)-nbad}/{len(rep)} nets single-island")
print("=== SHORTS (<%.2fmm) ==="%CLR)
sv=shorts()
print("  none" if not sv else "\n".join(f"  {L}: {a}<->{b} {d}mm @({x},{y})" for L,a,b,d,x,y in sv[:40]))

# ===================== package v2 gerbers into outputs =====================
import zipfile as _zip
_zpath="/mnt/user-data/outputs/solar-glow-drh-v2-gerbers.zip"
with _zip.ZipFile(_zpath,"w",_zip.ZIP_DEFLATED) as _z:
    for _fn in [f"{B}.{e}" for e in ("GTL","G1","G2","G3","G4","GBL","GTS","GBS","GKO","XLN")]+[f"{B}-NPTH.XLN"]:
        _fp=os.path.join(OUT,_fn)
        if os.path.exists(_fp): _z.write(_fp, _fn)
print("packaged:", _zpath)
