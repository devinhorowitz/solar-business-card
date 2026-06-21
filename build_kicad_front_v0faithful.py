"""
build_kicad_front_v0faithful.py — reproduce the FULL v0 front in KiCad.

Lifts the generator's actual front Shapely geometry (Fcu pour, Fmask openings,
silk) and emits it 1:1, triangulating every polygon so all holes survive
(letter counters, pad clearances, the frame's rounded gaps). The only v1 edit
applied here is the respaced monogram (track 0.23, from the glow module); the
castellation drop and TP-row relocation are left in place (faithful to v0) and
are the next toggle.

Layers:  Edge.Cuts (outline) · F.Cu (copper) · F.Mask (gold openings) · F.SilkS (silk)
"""
import sys, numpy as np
sys.path.insert(0, "/home/claude"); sys.path.insert(0, "/home/claude/revj")
import importlib.util as iu
import mapbox_earcut as earcut
import gerber_export as ge
import pcb_route as pr
from shapely.geometry import box

_s = iu.spec_from_file_location("glow", "/home/claude/solar-glow-drh-glow.py")
glow = iu.module_from_spec(_s); _s.loader.exec_module(glow)

from kiutils.board import Board, Net, GrLine, GrPoly, GrText
from kiutils.items.common import Position, Effects, Font

W, H = pr.W, pr.H
def fy(y): return round(H - y, 4)
def PT(x, y): return Position(round(x, 4), fy(y))

# ---- v1 monogram swap (front only): restore v0 letters in copper, cut v1 letters ----
v0_drh = ge.drh
v1_drh = glow.glow_geometry()["front_cut"]
Fcu_v1   = ge.Fcu.union(v0_drh).difference(v1_drh).simplify(0.02, preserve_topology=True)
Fmask_v1 = ge.Fmask.difference(v0_drh).union(v1_drh).simplify(0.02, preserve_topology=True)

# ---- triangulate a (multi)polygon -> list of (3x2) triangles, holes preserved ----
def tris_of(geom):
    polys = list(geom.geoms) if hasattr(geom, "geoms") else [geom]
    out = []
    for p in polys:
        if p.is_empty or p.area < 1e-6: continue
        rings = [np.array(p.exterior.coords[:-1], dtype=np.float64)]
        for h in p.interiors:
            rings.append(np.array(h.coords[:-1], dtype=np.float64))
        V = np.concatenate(rings)
        ends = np.cumsum([len(r) for r in rings]).astype(np.uint32)
        idx = earcut.triangulate_float64(V, ends)
        for i in range(0, len(idx), 3):
            out.append((V[idx[i]], V[idx[i+1]], V[idx[i+2]]))
    return out

bd = Board().create_new()
bd.nets = [Net(0, "")]

def emit(geom, layer):
    t = tris_of(geom)
    for a, b, c in t:
        bd.graphicItems.append(GrPoly(layer=layer,
            coordinates=[PT(*a), PT(*b), PT(*c)], width=0.0, fill="solid"))
    return len(t)

nF  = emit(Fcu_v1,   "F.Cu")
nM  = emit(Fmask_v1, "F.Mask")

# silk as native KiCad text (was 8k triangles) — strings/positions from the generator
def txt(s, x, y, h, ang=0):
    bd.graphicItems.append(GrText(text=s, position=Position(round(x,3), fy(y), ang),
        layer="F.SilkS", effects=Effects(font=Font(width=h, height=h, thickness=round(h*0.15,3)))))
for s, x in [("GND",5.9),("GND",18.9),("GND",31.9),("VS",38.4),("VIN",44.9)]:
    txt(s, x, 37.6, 0.7)
txt("SOLAR or BATTERY, NOT BOTH", 25.4, 73.0, 1.0, 90)
txt("BT1", 17.4, 86.3, 0.8); txt("BT2", 33.4, 86.3, 0.8)
txt("DOME or TOUCH", 33.0, 11.0, 0.85, 90); txt("SW1", 40.4, 4.8, 0.7)
txt("+", 43.4, 70.5, 1.3); txt("-", 7.4, 70.5, 1.3)
nS = 12

# Edge.Cuts outline
ext = list(ge.outline.exterior.coords)
for (x1, y1), (x2, y2) in zip(ext, ext[1:]):
    bd.graphicItems.append(GrLine(start=PT(x1, y1), end=PT(x2, y2), layer="Edge.Cuts", width=0.12))

out = "/mnt/user-data/outputs/solar-glow-drh-v1.kicad_pcb"
bd.to_file(out)
print(f"triangles  F.Cu={nF}  F.Mask={nM}  F.SilkS={nS}  total={nF+nM+nS}")
bd2 = Board().from_file(out)
print("re-parsed OK:", len(bd2.graphicItems), "graphic items")
print("wrote", out)
