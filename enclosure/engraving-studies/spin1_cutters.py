#!/usr/bin/env python3
"""SPIN 1 -- five ways to MACHINE the contact block into the titanium back, and the numbers.

NOT laser. A laser mark on bare Ti is an oxide film a few microns thick -- it is a colour,
not a feature, so it cannot be felt and the first refinish takes it off. Everything here
removes metal.

WHAT IS MODELLED, AND WHY IT IS NOT A DRAWING

Each variant is built as the DEPTH FIELD A REAL CUTTER WOULD LEAVE, sampled at 25 um, and
rendered as actual 3D on the actual shell STL. That means the pictures show the machining,
not an impression of it:

  * V-CARVE. A conical bit of included angle A with a flat tip of width t, plunged so that a
    point s away from the nearest stroke edge is cut to z = (s - t/2) / tan(A/2), capped at
    the depth limit. Thin strokes therefore come out SHALLOWER than thick ones -- that is
    what v-carving is, and it is why the numbers below quote achieved depth per line rather
    than one figure.
  * FLAT POCKET. A square-nosed end mill of radius r removes exactly the morphological
    opening of the shape at r: (shape (-) r) (+) r. Corners get the tool radius, and any
    stroke narrower than 2r is NOT CUT AT ALL. The render shows both.
  * RELIEF. The same opening, applied to the NEGATIVE space, because the tool works in the
    field and leaves the letters standing. Here the limit is the counter of an 'a', not the
    width of a stem, and anything the tool cannot reach stays as proud metal bridging the
    letters. That leftover is measured and reported.

THE DEPTH BUDGET, WHICH IS FIXED BY THE PART AND NOT BY TASTE

The back field has 1.00 mm of floor under it (fit_rules: floor=1.00). The fin fields already
cut FIN_VALLEY into that floor (0.30 when this spin ran; 0.60 since the 2026-07-30 fine-
reeding rework -- BUDGET below tracks fit_rules live), so the web under the valleys is
ALREADY the thinnest section of this part by design. Any engraving <= FIN_VALLEY deep
therefore adds no new thin section -- it is free. That is the ceiling every variant here
respects (all of these were computed at, and stay under, the 0.30 of their era; spin 3
spends the doubled ceiling), and it is also comfortably past "easily felt": a fingernail
reads a 0.05 mm step, and refinishing (bead blast, brush, stonewash) takes off order
0.01 mm, so a 0.25 mm cut survives many refinishes.

The text sits in the CLEAR BAND the two fin fields leave open (fit_rules.fin_band()), so it
never lands on a rib and the floor under it is the full 1.00 mm.
"""
from __future__ import annotations

import ast
import math
import os
import sys
import tempfile

sys.path.insert(0, "/home/user/solar-business-card/enclosure")

import numpy as np
import shapely.affinity as aff
import vtk
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage
from shapely.geometry import box
from shapely.ops import unary_union
from vtk.util.numpy_support import numpy_to_vtk, vtk_to_numpy

import fit_rules as fr

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
# Renders land OUTSIDE the repo by default. These are studies, not deliverables: consistency
# check [9] requires every image a doc displays to come from a generator CI runs, and CI does
# not run these (10 raytraced VTK views is ~7 min for work that is a decision aid, not an
# artifact). Set ENGRAVE_OUT to put them somewhere else.
OUT = os.environ.get("ENGRAVE_OUT") or os.path.join(tempfile.gettempdir(), "engraving-studies")
os.makedirs(OUT, exist_ok=True)
GEN = f"{ROOT}/enclosure/solar-glow-drh-v3_0-backshell-0p6b-brace-cad.py"
SHELL_STL = os.path.join(OUT, "shell_nomark.stl")

PX = 0.025                       # depth-field sample pitch, mm
FLOOR = 1.00                     # fit_rules floor under the back field
BUDGET = fr.FIN_VALLEY           # tracks fit_rules live (0.30 then, 0.60 now) -- the
                                 # depth the part already has elsewhere


# --- the generator's own text machinery, so the engraved outlines are the committed ones ---

def gen_ns(full=False):
    """Exec the shell generator's DEFINITIONS, never its output loop.

    That module writes its STEP/STL at import time -- the export loop is not behind an
    `if __name__ == "__main__"` guard -- so importing it normally would rewrite two committed
    CI-owned artifacts as a side effect of asking it what its font is. Executing node by node
    and stopping short of the loop is what avoids that.
    """
    ns = {"__name__": "_probe", "__file__": GEN}
    want = {"_maker_text", "MAKER_FONT_R", "MAKER_FONT_B"}
    for node in ast.parse(open(GEN).read()).body:
        # the export loop, by name rather than by position, so a reordered file still stops
        if isinstance(node, ast.For) and getattr(node.iter, "id", "") == "jobs":
            break
        try:
            exec(compile(ast.Module(body=[node], type_ignores=[]), "g", "exec"), ns)
        except Exception:
            if full:
                raise
        if not full and want <= set(ns):
            break
    return ns


def ensure_shell():
    """Build the finned back-shell WITHOUT its maker's mark, once, into OUT.

    No mark, because the committed mark sits at y 51.5/54.1 -- inside the very clear band
    every study lays type into. Studying an engraving on top of another engraving tells you
    nothing.
    """
    if os.path.exists(SHELL_STL):
        return SHELL_STL
    print(f"  building {os.path.basename(SHELL_STL)} (one-off, ~40 s) ...")
    ns = gen_ns(full=True)
    solid = ns["build"](maker_mark=False)
    ns["cq"].exporters.export(solid, SHELL_STL, tolerance=0.04, angularTolerance=0.2)
    return SHELL_STL


NS = gen_ns()
FONT = {"r": NS["MAKER_FONT_R"], "b": NS["MAKER_FONT_B"]}


def line_geom(txt, cx, cy, cap, weight):
    """One line of engraved text, CENTRED on (cx, cy), in board coords, ready to cut.

    Two transforms, both load-bearing and both already proven on the maker's mark:
      1. flip Y about the line's own centreline -- font outlines are Y-UP and board space is
         Y-DOWN, so dropping them in raw engraves every letter upside down while leaving the
         word order right (the tell is V as a lambda and W as an M).
      2. mirror X about the board centreline -- the part is machined from the back, so the
         cut has to be laid out mirrored to read correctly once the card is turned over.
    """
    g = NS["_maker_text"](txt, 0.0, cy, cap, FONT[weight])
    if g is None:
        return None
    g = aff.scale(g, xfact=1, yfact=-1, origin=(0, cy))
    x0, _, x1, _ = g.bounds
    g = aff.translate(g, cx - (x0 + x1) / 2.0, 0.0)
    return aff.scale(g, xfact=-1, yfact=1, origin=(fr.W / 2.0, fr.H / 2.0))


def block(lines, cx, cy):
    """Stack (text, cap, weight, gap-before) around centre (cx, cy). -> (union, per-line)."""
    heights = [cap for _t, cap, _w, _g in lines]
    gaps = [g for _t, _c, _w, g in lines]
    total = sum(heights) + sum(gaps[1:])
    y = cy - total / 2.0
    out = []
    for (txt, cap, weight, gap), h in zip(lines, heights):
        y += gap if out else 0.0
        g = line_geom(txt, cx, y + h / 2.0, cap, weight)
        if g is not None:
            out.append((txt, cap, weight, g))
        y += h
    return unary_union([g for _t, _c, _w, g in out]), out


# --- rasterised depth fields ------------------------------------------------------

class Field:
    """A depth map over a board-coordinate rectangle. z is mm INTO the part (0 = surface)."""

    def __init__(self, bounds, pad=1.5):
        x0, y0, x1, y1 = bounds
        self.x0, self.y0 = x0 - pad, y0 - pad
        self.nx = int(math.ceil((x1 - x0 + 2 * pad) / PX))
        self.ny = int(math.ceil((y1 - y0 + 2 * pad) / PX))
        self.z = np.zeros((self.ny, self.nx), np.float32)

    def raster(self, geom):
        """Fill a shapely geometry into a boolean array on this grid.

        Each polygon is rasterised alone (exterior minus its own holes) and OR-ed in.
        NOT one shared canvas: there, a later polygon's hole erases any earlier
        polygon's ink that lies inside it -- union-order roulette, found when a ring
        variant's separator hoop (an annulus) swallowed the serial digits sitting in
        its hole. OR of per-polygon masks is what union actually means.
        """
        out = np.zeros((self.ny, self.nx), bool)
        polys = list(geom.geoms) if geom.geom_type.startswith("Multi") else [geom]
        for p in polys:
            if p.is_empty:
                continue
            img = Image.new("1", (self.nx, self.ny), 0)
            d = ImageDraw.Draw(img)
            d.polygon([((x - self.x0) / PX, (y - self.y0) / PX) for x, y in p.exterior.coords],
                      fill=1)
            for r in p.interiors:
                d.polygon([((x - self.x0) / PX, (y - self.y0) / PX) for x, y in r.coords], fill=0)
            out |= np.array(img, bool)
        return out

    # -- the three real tool models --------------------------------------------

    def vee(self, mask, depth, incl_deg, tip):
        """Conical bit: z = (s - tip/2)/tan(A/2), capped at `depth`. Returns achieved max."""
        tan = math.tan(math.radians(incl_deg) / 2.0)
        s = ndimage.distance_transform_edt(mask) * PX
        z = np.clip((s - tip / 2.0) / tan, 0.0, depth)
        self.z = np.maximum(self.z, z * mask)
        return float(z[mask].max()) if mask.any() else 0.0

    def pocket(self, mask, depth, tool_r, base=0.0):
        """Square-nosed mill of radius tool_r, confined to `mask`. Returns (cut, unreachable)."""
        cut = self.opening(mask, tool_r)
        self.z = np.maximum(self.z, np.where(cut, base + depth, 0.0))
        return cut, mask & ~cut

    @staticmethod
    def opening(mask, r):
        """(mask (-) r) (+) r -- exactly the metal a radius-r cutter can remove inside mask."""
        if r <= 0:
            return mask.copy()
        eroded = ndimage.distance_transform_edt(mask) >= (r / PX)
        if not eroded.any():
            return np.zeros_like(mask)
        return ndimage.distance_transform_edt(~eroded) <= (r / PX)

    def area(self, mask):
        return float(mask.sum()) * PX * PX

    def widest(self, mask):
        """Diameter of the largest disc inside `mask` -- 0 if empty."""
        if not mask.any():
            return 0.0
        return float(ndimage.distance_transform_edt(mask).max()) * 2.0 * PX


# --- surface geometry from a depth field ------------------------------------------

def _sheet(f: Field, cells: np.ndarray, z_lift: float = 0.0):
    """The depth field as a triangulated sheet, minus the cells `keep` masks out."""
    ys = f.y0 + np.arange(f.ny) * PX
    xs = f.x0 + np.arange(f.nx) * PX
    X, Y = np.meshgrid(xs, ys)
    pts = np.stack([X.ravel(), Y.ravel(), (f.z - z_lift).ravel()], 1).astype(np.float32)

    idx = np.arange(f.nx * f.ny, dtype=np.int64).reshape(f.ny, f.nx)
    a, b = idx[:-1, :-1], idx[:-1, 1:]
    c, d = idx[1:, 1:], idx[1:, :-1]
    a, b, c, d = (v[cells] for v in (a, b, c, d))
    n = a.size
    conn = np.empty(n * 4, np.int64)
    conn[0::4], conn[1::4], conn[2::4], conn[3::4] = a, b, c, d

    vp = vtk.vtkPoints()
    vp.SetData(numpy_to_vtk(pts, deep=1))
    ca = vtk.vtkCellArray()
    ca.SetData(numpy_to_vtk(np.arange(n + 1, dtype=np.int64) * 4, deep=1, array_type=vtk.VTK_ID_TYPE),
               numpy_to_vtk(conn, deep=1, array_type=vtk.VTK_ID_TYPE))
    pd = vtk.vtkPolyData()
    pd.SetPoints(vp)
    pd.SetPolys(ca)
    tri = vtk.vtkTriangleFilter()
    tri.SetInputData(pd)
    tri.Update()
    nrm = vtk.vtkPolyDataNormals()
    nrm.SetInputConnection(tri.GetOutputPort())
    nrm.SplittingOn()
    nrm.SetFeatureAngle(28.0)          # keep pocket walls crisp, keep V-flanks smooth
    nrm.ConsistencyOn()
    # NOT AutoOrientNormals. It is only defined for CLOSED surfaces; on an open sheet like this
    # one it flips normals in patches, and the render came back with a fine checkerboard over
    # the whole art rect plus a stray bright lobe -- both of which look like a surface finish
    # and are neither. The sheet's orientation is known instead: it faces the camera, i.e. -z.
    nrm.AutoOrientNormalsOff()
    nrm.Update()
    out = nrm.GetOutput()
    nz = vtk_to_numpy(out.GetPointData().GetNormals())[:, 2]
    if nz.mean() > 0:
        f2 = vtk.vtkPolyDataNormals()
        f2.SetInputData(out)
        f2.SplittingOn()
        f2.SetFeatureAngle(28.0)
        f2.ConsistencyOn()
        f2.AutoOrientNormalsOff()
        f2.FlipNormalsOn()
        f2.Update()
        out = f2.GetOutput()
    return out


def field_surfaces(f: Field, keep: np.ndarray, thr=0.015):
    """Split the sheet into (as-finished face, machined surface).

    Not a rendering trick: a milled floor and a bead-blasted face are DIFFERENT SURFACES.
    The cutter leaves bright, directional, near-specular metal; the blasted face is matte and
    diffuse. On bare titanium with no coating, that difference IS the contrast the engraving
    reads by -- so the two have to be shaded as two materials or the picture lies about how
    legible the part is. Cells that straddle the threshold are walls, and walls belong to the
    cut.
    """
    ok = keep[:-1, :-1] & keep[:-1, 1:] & keep[1:, 1:] & keep[1:, :-1]
    lo = f.z < thr
    flat = lo[:-1, :-1] & lo[:-1, 1:] & lo[1:, 1:] & lo[1:, :-1]
    return _sheet(f, ok & flat), _sheet(f, ok & ~flat)


# --- the variants -----------------------------------------------------------------
# Content is the front of the card, verbatim, in the same vendored JetBrains Mono the
# maker's mark already cuts. Where a variant carries less, it is because the TOOL said so,
# and the note says which tool.

CY = sum(fr.fin_band()) / 2.0        # centre of the clear band the fins leave open
CX = fr.W / 2.0

# THE ART RECT. One rectangle for every variant, so the comparison is about the engraving and
# not about where it sits. Its limits are the part's, not a layout choice: the clear band the
# two fin fields leave open sets y, and the four in-band M2 bosses at x = 3.0 / 47.8 (r 2.6,
# so they reach x 5.6 and 45.2) set x. Nothing here may touch a boss annulus.
ART = (6.0, 30.8, 44.8, 58.1)

FULL = [("DEVIN HOROWITZ",   3.00, "b", 0.00),
        ("ATTORNEY",         1.50, "r", 1.30),
        ("Devin@Horowitz.Law", 2.20, "r", 2.00),
        ("404-213-8076",     2.20, "r", 1.10),
        ("Atlanta, Georgia", 1.60, "r", 1.40)]

VARIANTS = [
    dict(key="A-vcarve", title="V-CARVE",
         sub="60 deg V-bit, 0.10 mm tip, 0.25 mm cap",
         kind="vee", lines=FULL, depth=0.25, incl=60.0, tip=0.10,
         why="True v-carving: the bit rides to whatever depth the stroke width allows, so the "
             "strokes taper and the depth VARIES by line. Cheapest to cut, most forgiving in "
             "Ti, and the flanks throw a bright line under raking light."),
    dict(key="B-pocket", title="FLAT POCKET",
         sub="dia 0.3 square end mill, 0.30 mm flat bottom",
         kind="pocket", depth=0.30, tool_r=0.15,
         lines=[("DEVIN HOROWITZ",     3.40, "b", 0.00),
                ("DEVIN@HOROWITZ.LAW", 2.60, "b", 2.40),
                ("404-213-8076",       2.60, "b", 1.40)],
         why="Square shoulders and a flat floor at the full 0.30 mm budget -- the most positive "
             "fingernail catch of the five, and the deepest shadow. The tool sets the type: a "
             "0.3 mm cutter cannot enter a stroke narrower than 0.3 mm and rounds every corner "
             "to 0.15, which is why every line here is BOLD, larger, and why the title and the "
             "city had to go."),
    dict(key="C-relief", title="RELIEF",
         sub="dia 0.3 end mill, field down 0.25 mm, letters left standing",
         kind="relief", depth=0.25, tool_r=0.15, panel=(6.9, 31.4, 43.9, 57.5), panel_r=1.6,
         lines=FULL,
         why="Cut the FIELD, not the letters. The letters stay at the original face -- still "
             "0.15 mm below the proud back border, so nothing ever rubs them -- and they keep "
             "the bead-blast finish while the milled floor comes out bright. Two textures, no "
             "coating, and the most refinish-proof of the five."),
    dict(key="D-plaque", title="PLAQUE",
         sub="panel 0.12 mm + 60 deg V-carve 0.18 mm inside it",
         kind="plaque", d_panel=0.12, panel_r=0.50, depth=0.18, incl=60.0, tip=0.10,
         panel=(6.9, 31.4, 43.9, 57.5), lines=FULL,
         why="Two levels. A shallow rectangular panel gives the block a hard edge and a second "
             "shoulder, and the text is carved inside it, so the letters sit 0.30 mm below the "
             "field and 0.45 mm below the border. Frames the block without adding a single line "
             "of ornament."),
    dict(key="E-monogram", title="MONOGRAM",
         sub="dia 1.0 rough + 60 deg chamfer, 0.30 mm",
         kind="vee", depth=0.30, incl=60.0, tip=0.10,
         lines=[("DRH", 11.00, "b", 0.00),
                ("Devin@Horowitz.Law", 2.00, "r", 3.40)],
         why="Restraint. The front already carries the contact block and the tap serves the "
             "vCard, so the back says the mark and one line. At cap 11 the strokes are 2.2 mm "
             "wide, so this is a flat-bottomed pocket with a 60 deg chamfered edge -- roughed "
             "with a dia 1.0 and edged with the V -- not a carved groove."),
]


def build_variant(v):
    """-> (Field, keep-mask, notes[]) . Notes are the machining facts, measured not assumed."""
    glyph, per_line = block(v["lines"], CX, CY)
    b = glyph.bounds
    if not (ART[0] <= b[0] and b[2] <= ART[2] and ART[1] <= b[1] and b[3] <= ART[3]):
        raise SystemExit(f"{v['key']}: block x[{b[0]:.2f},{b[2]:.2f}] y[{b[1]:.2f},{b[3]:.2f}] "
                         f"escapes the art rect {ART} -- it would run into a boss or a fin")
    f = Field(ART, pad=0.0)
    g_mask = f.raster(glyph)
    notes, deepest = [], 0.0

    if v["kind"] == "vee":
        for txt, cap, weight, geo in per_line:
            m = f.raster(geo)
            got = f.vee(m, v["depth"], v["incl"], v["tip"])
            deepest = max(deepest, got)
            need = v["tip"] + 2 * v["depth"] * math.tan(math.radians(v["incl"]) / 2.0)
            stroke = f.widest(m)
            notes.append(f"{txt[:22]:<22} cap {cap:4.2f}  stroke {stroke:5.3f}  "
                         f"cut {got:4.3f} mm" + ("" if got >= v["depth"] - 1e-6 else
                                                 f"  (stroke < {need:.3f}, bit bottoms early)"))
        keep = np.ones_like(g_mask)

    elif v["kind"] == "pocket":
        for txt, cap, weight, geo in per_line:
            m = f.raster(geo)
            cut, miss = f.pocket(m, v["depth"], v["tool_r"])
            stroke = f.widest(m)
            tag = "" if not miss.any() else f"  ({f.area(miss):.2f} mm2 unreachable)"
            notes.append(f"{txt[:22]:<22} cap {cap:4.2f}  stroke {stroke:5.3f}  "
                         f"cut {v['depth']:4.3f} mm{tag}")
        deepest = v["depth"]
        keep = np.ones_like(g_mask)

    elif v["kind"] == "relief":
        panel = fr._dedupe(box(*v["panel"]).buffer(-v["panel_r"]).buffer(v["panel_r"] * 2)
                           .intersection(box(*v["panel"])))
        p_mask = f.raster(panel)
        field = p_mask & ~g_mask
        cut, miss = f.pocket(field, v["depth"], v["tool_r"])
        deepest = v["depth"]
        notes.append(f"panel {v['panel'][2]-v['panel'][0]:.1f} x {v['panel'][3]-v['panel'][1]:.1f} mm, "
                     f"floor down {v['depth']:.2f} mm over {f.area(cut):.1f} mm2")
        notes.append(f"tightest counter the dia {2*v['tool_r']:.1f} tool must enter: "
                     f"{f.widest(field & ndimage.binary_dilation(g_mask, iterations=8)):.3f} mm")
        notes.append(f"metal it cannot reach, left proud between letters: {f.area(miss):.3f} mm2"
                     + ("  -- none" if not miss.any() else
                        f", widest blob {f.widest(miss):.3f} mm"))
        keep = np.ones_like(g_mask)

    else:  # plaque
        panel = fr._dedupe(box(*v["panel"]).buffer(-v["panel_r"]).buffer(v["panel_r"] * 2)
                           .intersection(box(*v["panel"])))
        p_mask = f.opening(f.raster(panel), v["panel_r"])
        f.z = np.maximum(f.z, np.where(p_mask, v["d_panel"], 0.0))
        base = f.z.copy()
        for txt, cap, weight, geo in per_line:
            m = f.raster(geo)
            tan = math.tan(math.radians(v["incl"]) / 2.0)
            s = ndimage.distance_transform_edt(m) * PX
            z = np.clip((s - v["tip"] / 2.0) / tan, 0.0, v["depth"])
            f.z = np.maximum(f.z, np.where(m, base + z, 0.0))
            got = float(z[m].max())
            notes.append(f"{txt[:22]:<22} cap {cap:4.2f}  stroke {f.widest(m):5.3f}  "
                         f"cut {got:4.3f} below panel = {v['d_panel']+got:4.3f} total")
        deepest = v["d_panel"] + v["depth"]
        keep = np.ones_like(p_mask)

    notes.append(f"DEEPEST CUT {deepest:.3f} mm -> {FLOOR - deepest:.3f} mm floor left "
                 f"({'within' if deepest <= BUDGET + 1e-9 else 'PAST'} the {BUDGET:.2f} mm the "
                 f"fin valleys already take)")
    b = glyph.bounds
    notes.append(f"block x[{b[0]:.1f},{b[2]:.1f}] y[{b[1]:.1f},{b[3]:.1f}] -- clear band is "
                 f"y[{fr.fin_band()[0]:.2f},{fr.fin_band()[1]:.2f}]")
    return f, keep, notes


# --- render -----------------------------------------------------------------------

TI_BLAST = (0.520, 0.528, 0.552)      # bead-blasted Ti-6Al-4V: matte, slightly cool, DARK
TI_CUT   = (0.880, 0.884, 0.900)      # freshly milled: much brighter and strongly specular
BG = (0.960, 0.958, 0.952)


def shell_actor():
    r = vtk.vtkSTLReader()
    r.SetFileName(SHELL_STL)
    r.Update()
    t = vtk.vtkTransform()
    t.Translate(fr.W / 2, fr.H / 2, 0)
    ff = vtk.vtkTransformPolyDataFilter()
    ff.SetInputData(r.GetOutput())
    ff.SetTransform(t)
    ff.Update()
    n = vtk.vtkPolyDataNormals()
    n.SetInputConnection(ff.GetOutputPort())
    n.ConsistencyOn()
    n.AutoOrientNormalsOn()
    n.Update()
    return n.GetOutput()


SHELL = None


def clip_back_face(pd, rect, z0=-0.02, z1=0.6, levels=5):
    """Cut the shell's flat back face out of `rect` so the depth field can supply it.

    Without this every recess renders BEHIND the shell's own surface and the part comes out
    blank -- which is exactly what the first pass of this script produced.

    The subdivision is the whole trick, and it is why the second pass came out blank TOO.
    Implicit-function clipping only cuts a triangle whose vertices STRADDLE the surface, and
    the shell's back field is a handful of triangles tens of mm across: not one vertex of it
    falls inside the art rect, so vtkClipPolyData evaluated every corner as "outside", found
    nothing to cut, and handed back all 12,216 cells unchanged. Subdividing just that face
    first gives the clip vertices on both sides, and the cut boundary then lands exactly on
    the rect because the filter interpolates along the implicit surface.

    Only the flat back face is subdivided -- everything else keeps its original tessellation.
    The z band is tight around that face, so the cavity floor at z = 1.00 and every feature
    inside the shell survive, and `rect` is already clear of all four in-band boss annuli.
    """
    pts = vtk_to_numpy(pd.GetPoints().GetData())
    tris = vtk_to_numpy(pd.GetPolys().GetConnectivityArray()).reshape(-1, 3)
    flat = (np.abs(pts[tris, 2]) < 1e-4).all(axis=1)

    def sub(mask, n):
        ca = vtk.vtkCellArray()
        t = tris[mask]
        ca.SetData(numpy_to_vtk(np.arange(len(t) + 1, dtype=np.int64) * 3, deep=1,
                                array_type=vtk.VTK_ID_TYPE),
                   numpy_to_vtk(t.ravel().astype(np.int64), deep=1, array_type=vtk.VTK_ID_TYPE))
        q = vtk.vtkPolyData()
        q.SetPoints(pd.GetPoints())
        q.SetPolys(ca)
        cl = vtk.vtkCleanPolyData()
        cl.SetInputData(q)
        cl.Update()
        if n == 0:
            return cl.GetOutput()
        sd = vtk.vtkLinearSubdivisionFilter()
        sd.SetInputConnection(cl.GetOutputPort())
        sd.SetNumberOfSubdivisions(n)
        sd.Update()
        return sd.GetOutput()

    app = vtk.vtkAppendPolyData()
    app.AddInputData(sub(flat, levels))
    app.AddInputData(sub(~flat, 0))
    app.Update()

    bx = vtk.vtkBox()
    bx.SetBounds(rect[0], rect[2], rect[1], rect[3], z0, z1)
    c = vtk.vtkClipPolyData()            # keeps f > 0, and vtkBox is negative INSIDE
    c.SetInputConnection(app.GetOutputPort())
    c.SetClipFunction(bx)
    c.SetValue(0.0)
    c.Update()
    n = vtk.vtkPolyDataNormals()
    n.SetInputConnection(c.GetOutputPort())
    n.ConsistencyOn()
    n.AutoOrientNormalsOn()
    n.Update()
    print(f"    shell {pd.GetNumberOfCells()} tris ({flat.sum()} on the back face) -> "
          f"{c.GetOutput().GetNumberOfCells()} after subdivide+clip")
    return n.GetOutput()


def mat(pd, rgb=TI_BLAST, diff=0.66, spec=0.50, pw=44, amb=0.13):
    m = vtk.vtkPolyDataMapper()
    m.SetInputData(pd)
    a = vtk.vtkActor()
    a.SetMapper(m)
    p = a.GetProperty()
    p.SetColor(*rgb)
    p.SetDiffuse(diff)
    p.SetSpecular(spec)
    p.SetSpecularPower(pw)
    p.SetAmbient(amb)
    p.SetSpecularColor(1, 1, 1)
    return a


def shot(surfaces, path, size=1500, az=5.0, el=13.0, dist=232.0, grazing=False, crop=None,
         uniform=False):
    """uniform=True renders every surface in the blasted material -- the SINGLE-FINISH
    reality of a prototype shop: the part is machined, then bead blast (or brush, or
    polish) is applied ONCE, over everything. Floors, crests and grooves come out the
    same texture, and nothing brings the mill back after the finish. The two-material
    default shows the as-cut contrast, which is real only until the finisher's cabinet."""
    ren = vtk.vtkRenderer()
    ren.SetBackground(*BG)
    rw = vtk.vtkRenderWindow()
    rw.SetOffScreenRendering(1)
    rw.AddRenderer(ren)
    rw.SetSize(size, size)
    face, cut = surfaces
    ren.AddActor(mat(SHELL, TI_BLAST, diff=0.88, spec=0.13, pw=16, amb=0.07))
    ren.AddActor(mat(face, TI_BLAST, diff=0.90, spec=0.04, pw=12, amb=0.07))
    if uniform:
        ren.AddActor(mat(cut, TI_BLAST, diff=0.90, spec=0.04, pw=12, amb=0.07))
    else:
        ren.AddActor(mat(cut, TI_CUT, diff=0.60, spec=0.78, pw=40, amb=0.05))
    lights = ([((fr.W / 2 - 900, CY - 250, -150), 1.25),         # hard raking, ~9 deg in-plane
               ((fr.W / 2 + 500, CY + 300, -700), 0.26),
               ((fr.W / 2, CY, -900), 0.20)] if grazing else
              [((fr.W / 2 - 340, CY - 400, -430), 0.98),
               ((fr.W / 2 + 430, CY + 300, -420), 0.34),
               ((fr.W / 2 - 30, CY + 50, -900), 0.22)])
    for pos, i in lights:
        L = vtk.vtkLight()
        L.SetPosition(*pos)
        L.SetFocalPoint(fr.W / 2, fr.H / 2, 0.0)
        L.SetIntensity(i)
        L.SetLightTypeToSceneLight()
        ren.AddLight(L)
    cam = ren.GetActiveCamera()
    a, e = math.radians(az), math.radians(el)
    fx, fy = (fr.W / 2, CY) if crop else (fr.W / 2, fr.H / 2)
    cam.SetPosition(fx + dist * math.cos(e) * math.sin(a), fy - dist * math.sin(e),
                    -dist * math.cos(e) * math.cos(a))
    cam.SetFocalPoint(fx, fy, 0)
    cam.SetViewUp(0, -1, 0)
    cam.SetViewAngle(crop or 25)
    ren.ResetCameraClippingRange()
    rw.Render()
    w = vtk.vtkWindowToImageFilter()
    w.SetInput(rw)
    w.Update()
    arr = vtk_to_numpy(w.GetOutput().GetPointData().GetScalars())
    arr = arr.reshape(size, size, -1)[::-1, :, :3]
    bg = np.array(BG) * 255
    fg = np.abs(arr.astype(np.int16) - bg.astype(np.int16)).max(axis=2) > 6
    ys, xs = np.nonzero(fg)
    im = Image.fromarray(arr[max(0, ys.min() - 14):ys.max() + 15,
                             max(0, xs.min() - 14):xs.max() + 15])
    im = im.transpose(Image.FLIP_LEFT_RIGHT)      # the scene is left-handed
    im.save(path)
    return im


def _wrap(text, n):
    out, cur = [], ""
    for w in text.split(" "):
        if cur and len(cur) + 1 + len(w) > n:
            out.append(cur); cur = w
        else:
            cur = f"{cur} {w}".strip()
    return out + ([cur] if cur else [])


def label_font(px):
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
              os.path.join(ROOT, "enclosure", "fonts", "JetBrainsMono-Regular.ttf")):
        if os.path.exists(p):
            return ImageFont.truetype(p, px)
    return ImageFont.load_default()


if __name__ == "__main__":
    ensure_shell()
    SHELL = clip_back_face(shell_actor(), ART)
    print(f"clear band y[{fr.fin_band()[0]:.2f},{fr.fin_band()[1]:.2f}], "
          f"centre y={CY:.2f}; floor {FLOOR:.2f} mm, budget {BUDGET:.2f} mm\n")
    made = []
    for v in VARIANTS:
        f, keep, notes = build_variant(v)
        print(f"=== {v['key']}  {v['title']} -- {v['sub']}")
        for n in notes:
            print("    " + n)
        print()
        surf = field_surfaces(f, keep)
        p1 = f"{OUT}/spin1_{v['key']}.png"
        p2 = f"{OUT}/spin1_{v['key']}_graze.png"
        shot(surf, p1)                                   # whole back, in context
        shot(surf, p2, crop=15.0, grazing=True, az=2.0, el=5.0)
        made.append((v, p1, p2, notes))
        print(f"    wrote {os.path.basename(p1)}, {os.path.basename(p2)}\n")

    # contact sheet: normal light over grazing light, one column per variant
    ims = [(v, Image.open(a).convert("RGB"), Image.open(b).convert("RGB"), n)
           for v, a, b, n in made]
    cw = max(max(a.width, b.width) for _v, a, b, _n in ims)
    ch = max(max(a.height, b.height) for _v, a, b, _n in ims)
    pad, head, gap, foot = 26, 104, 12, 340
    sheet = Image.new("RGB", (len(ims) * (cw + pad) + pad, head + ch * 2 + gap + foot),
                      (247, 247, 245))
    d = ImageDraw.Draw(sheet)
    ft, fs, fm = label_font(40), label_font(24), label_font(19)
    for i, (v, a, b, notes) in enumerate(ims):
        x = pad + i * (cw + pad)
        d.text((x, 16), v["title"], font=ft, fill=(20, 20, 24))
        d.text((x, 64), v["sub"], font=fs, fill=(92, 92, 100))
        sheet.paste(a, (x + (cw - a.width) // 2, head))
        sheet.paste(b, (x + (cw - b.width) // 2, head + ch + gap))
        y = head + ch * 2 + gap + 16
        d.line([(x, y - 8), (x + cw - 6, y - 8)], fill=(206, 206, 202), width=2)
        for ln in notes:
            wrapped = _wrap(ln, 74)
            for w in wrapped:
                d.text((x, y), w, font=fm, fill=(70, 70, 78) if "DEEPEST" in ln else (118, 118, 126))
                y += 24
    d.text((pad, head + ch * 2 + gap + foot - 34),
           "top: diffuse light    |    bottom: hard raking light, which is what an engraving is for."
           "    Every depth field is the cut a real bit leaves, sampled at 25 um, on the real shell STL.",
           font=fs, fill=(92, 92, 100))
    sheet.save(f"{OUT}/spin1_cutters.png")
    print("wrote", f"{OUT}/spin1_cutters.png", sheet.size)
