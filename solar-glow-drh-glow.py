"""
solar-glow-drh-glow.py  —  V1 glow geometry (parametric, importable)

Folds the validated V1 glow design out of the throwaway layout study into one
reusable generator module. It produces, for any initials, the three pieces the
board needs:

    1. front_cut   - the monogram polygon to subtract from FRONT copper
                     (respaced to track 0.23 so each window nestles a boundary)
    2. windows     - the 4 reverse-mount LED window centres on the centreline
                     (2 inter-letter gaps + 2 outer flanks), Ø1.64 back-copper holes
    3. keepaway    - one tight rectangle (window span x letter height + clearance),
                     subtract from EVERY layer's copper + mark a routing keepout
                     so nothing wires across the light path

This is the V1 glow only. The ordered REV J board (v0) is frozen at track 0.12 in
`solar-glow-drh-pcb-generator-revJ.zip` and is byte-identical to the OSH Park
gerbers; do NOT change that. This module is what a V1 generator imports.

Plugging into a V1 gerber_export (after the reroute lands the real placement):

    from glow import glow_geometry, WIN_D
    g   = glow_geometry("DRH")                      # or any initials
    Fcu = Fcu.difference(g["front_cut"])            # cut letters on the front
    back_holes = [Point(x, y).buffer(WIN_D/2) for x, y in g["windows"]]
    # -> place D2..Dn LED footprints at g["windows"], Ø1.64 holes in BACK copper
    keepout = keepout.union(g["keepaway"])          # all-layer void + route keepout

The 4 window centres are also the LED-footprint origins, and the printed corner
coords feed a KiCad keepout zone directly. Geometry/font logic is identical to the
generator's `text_shapely` (S=72, adv=S*(0.6+track), even-odd via symmetric_difference).

Run directly to print coords and render a preview:  python3 solar-glow-drh-glow.py
"""

import os
import numpy as np
from functools import reduce
from matplotlib.textpath import TextPath
from matplotlib.font_manager import FontProperties
from matplotlib.path import Path as MP
from shapely.geometry import Polygon as SPoly, Point, box
from shapely import affinity as aff

# ---- V1 glow parameters (the locked design) --------------------------------
INITIALS   = "DRH"     # reference design; swap for any monogram
CX, CY     = 25.4, 45.0  # monogram centre on the board (mm)
LETTER_H   = 5.5       # cap height (mm)
TRACK      = 0.23      # inter-letter spacing -> windows nestle the boundaries
WIN_D      = 1.64      # LED back-window diameter (mm); matches FP("LED")
WIN_R      = WIN_D / 2
FLANK_GAP  = 0.43      # window-edge-to-letter gap for the 2 outer flank windows
KEEP_CLR   = 0.35      # keepaway clearance past windows (x) and letters (y)

# ---- font resolver (portable: repo checkout, or this container) -------------
def _font(fname="JetBrainsMono-ExtraBold.ttf"):
    here = os.path.dirname(os.path.abspath(__file__))
    for p in (os.environ.get("GLOW_FONT"),
              os.path.join(os.getcwd(), "fonts", fname),
              os.path.join(here, "fonts", fname),
              os.path.join(here, fname),
              f"/home/claude/revj/fonts/{fname}",
              f"/home/claude/fonts/{fname}"):
        if p and os.path.exists(p):
            return FontProperties(fname=p)
    raise FileNotFoundError(f"{fname} not found; set GLOW_FONT or place it in ./fonts/")

JBM_XB = _font()


def text_shapely(txt, cx, cy, h, ha="center", track=0.04, prop=JBM_XB):
    """Identical to the generator's text_shapely: vector glyphs -> even-odd
    Shapely polygon, scaled to cap height h, anchored at (cx, cy)."""
    S = 72.0; adv = S * (0.6 + track); vv = []; cc = []; xo = 0.0
    for ch in txt:
        if ch != " ":
            t = TextPath((0, 0), ch, size=S, prop=prop)
            if len(t.vertices):
                vv.append(t.vertices + [xo, 0]); cc.append(t.codes)
        xo += adv
    path = MP(np.vstack(vv), np.concatenate(cc))
    contours = [c for c in path.to_polygons(closed_only=True) if len(c) >= 4]
    polys = [SPoly(c).buffer(0) for c in contours]
    geom = reduce(lambda a, b: a.symmetric_difference(b), polys)
    minx, miny, maxx, maxy = geom.bounds; sc = h / (maxy - miny)
    geom = aff.scale(geom, xfact=sc, yfact=sc, origin=(minx, miny))
    minx, miny, maxx, maxy = geom.bounds
    dx = {"center": cx - (minx + maxx) / 2, "left": cx - minx, "right": cx - maxx}[ha]
    return aff.translate(geom, dx, cy - (miny + maxy) / 2)


def glow_geometry(initials=INITIALS, cx=CX, cy=CY, h=LETTER_H, track=TRACK,
                  win_r=WIN_R, flank_gap=FLANK_GAP, keep_clr=KEEP_CLR):
    """Return the three glow primitives for a monogram.

    Returns a dict:
        front_cut : shapely (Multi)Polygon  -> subtract from FRONT copper
        windows   : list[(x, y)]            -> 4 LED-window / footprint centres
        keepaway  : shapely box             -> all-layer copper void + route keepout
        bbox      : (x0, y0, x1, y1) of the keepaway
    """
    mono = text_shapely(initials, cx, cy, h, track=track)
    glyphs = sorted(list(mono.geoms), key=lambda p: p.centroid.x)
    edges = [(p.bounds[0], p.bounds[2]) for p in glyphs]  # (minx, maxx) per letter

    # gap windows: centred in each inter-letter gap
    gaps = [(edges[i][1] + edges[i + 1][0]) / 2 for i in range(len(edges) - 1)]
    # flank windows: just outside the outer letter edges, same clearance as the gaps
    off = win_r + flank_gap
    flank_L = edges[0][0] - off
    flank_R = edges[-1][1] + off
    win_x = [flank_L, *gaps, flank_R]
    windows = [(x, cy) for x in win_x]

    # one tight keepaway: window span in x, letter height in y, + clearance
    x0 = min(win_x) - win_r - keep_clr
    x1 = max(win_x) + win_r + keep_clr
    y0 = mono.bounds[1] - keep_clr
    y1 = mono.bounds[3] + keep_clr
    keep = box(x0, y0, x1, y1)

    return {"front_cut": mono, "windows": windows, "keepaway": keep,
            "bbox": (x0, y0, x1, y1)}


def _preview(g, path="/mnt/user-data/outputs/solar-glow-drh-glow-window.png"):
    """Render the same study image (sanity check that the module matches)."""
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle, PathPatch, Rectangle
    from matplotlib.path import Path

    def shp_patch(geom, **kw):
        polys = list(geom.geoms) if geom.geom_type == "MultiPolygon" else [geom]
        verts = []; codes = []
        for poly in polys:
            for ring in [poly.exterior, *poly.interiors]:
                xy = list(ring.coords); verts += xy
                codes += [Path.MOVETO] + [Path.LINETO] * (len(xy) - 2) + [Path.CLOSEPOLY]
        return PathPatch(Path(verts, codes), **kw)

    x0, y0, x1, y1 = g["bbox"]; RW, RH = x1 - x0, y1 - y0
    fig, ax = plt.subplots(figsize=(8.6, 4.8), dpi=160)
    ax.set_xlim(10, 41); ax.set_ylim(37, 53.5); ax.set_aspect("equal"); ax.axis("off")
    fig.patch.set_facecolor("#070d0a"); ax.set_facecolor("#070d0a")
    ax.axhline(53.25, color="#7a8290", lw=8, alpha=0.22)
    ax.text(40.5, 53.0, "top cells \u2192", fontsize=6, color="#9aa", ha="right", va="center")
    ax.axhline(35.65, color="#7a8290", lw=8, alpha=0.22)
    ax.text(40.5, 35.9, "bottom cells \u2192", fontsize=6, color="#9aa", ha="right", va="center")
    ax.add_patch(Rectangle((x0, y0), RW, RH, fc="#163a2c", ec="#37d39a", lw=1.6,
                           ls=(0, (6, 3)), alpha=0.5, zorder=3))
    ax.add_patch(shp_patch(g["front_cut"], fc="#ffb24d", ec="#cc7a1f", lw=0.6, zorder=6))
    for x, y in g["windows"]:
        ax.add_patch(Circle((x, y), WIN_R, fc="#ffe6bf", ec="#a8632a", lw=1.0, zorder=7))
        ax.add_patch(Circle((x, y), 0.12, fc="#a8632a", zorder=8))
    ax.text(CX, y1 + 0.9,
            f"keepaway = ONE rectangle  {RW:.1f}\u00d7{RH:.1f} mm  "
            f"(tight: window span + letter height + {KEEP_CLR} clr)  \u00b7  no copper, all 4 layers",
            ha="center", fontsize=6.8, color="#5fe0b0", zorder=9)
    ax.text(CX, y0 - 1.4, "any initials fit inside \u00b7 4 fixed \u00d81.64 windows on the centerline",
            ha="center", fontsize=7.5, color="#e8a24d", zorder=9)
    ax.text(CX, y1 + 2.6, f"({INITIALS} shown as the reference design)",
            ha="center", fontsize=6.3, color="#789", zorder=9)
    fig.savefig(path, dpi=160, bbox_inches="tight", facecolor="#070d0a")
    return path


if __name__ == "__main__":
    g = glow_geometry()
    x0, y0, x1, y1 = g["bbox"]
    print(f"initials       : {INITIALS}  (track {TRACK}, cap {LETTER_H} mm @ ({CX},{CY}))")
    print(f"window centres : " + ", ".join(f"({x:.2f},{y:.1f})" for x, y in g["windows"]))
    print(f"window dia      : {WIN_D} mm  (back-copper holes + LED footprint origins)")
    print(f"keepaway rect  : x[{x0:.2f},{x1:.2f}]  y[{y0:.2f},{y1:.2f}]   "
          f"({x1-x0:.1f}\u00d7{y1-y0:.1f} mm, {KEEP_CLR} mm clr)")
    out = _preview(g)
    print("preview        :", out)
