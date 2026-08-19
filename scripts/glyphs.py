#!/usr/bin/env python3
"""Text -> shapely outlines, filled by the rule fonts are actually drawn to.

WHY THIS IS ITS OWN MODULE. Two generators set type from the same JetBrains Mono files:
`scripts/face_art.py` opens the card face's soldermask, and
`enclosure/solar-glow-drh-v4_0-backshell-0p6b-brace-cad.py` engraves the medallion's ring
text, monogram and unit serial into titanium. Both need glyph outlines and both got them
by folding the contours with `reduce(symmetric_difference)`, which is wrong, so the bug
existed in two places and was found in only one.

WHAT IS WRONG WITH THE FOLD. It assumes a glyph is one outline plus disjoint counters --
true for 'o', 'e', 'a', and false for '8', which JetBrains Mono draws as TWO closed,
SELF-INTERSECTING loops, one per bowl. `Polygon(c).buffer(0)` floods such a loop, and the
XOR then eats the overlap at the waist. The '8' comes back as two solid lumps with no
counters at all -- measured against the correct fill, +56.9 % ink in Regular and +28.8 %
in Bold. A survey of 89 glyphs (A-Z, a-z, 0-9 and the punctuation these two generators
use, both weights) found '8' to be the ONLY one affected, which is exactly what makes it
dangerous: everything looks right until a serial number contains an eight.

Containment depth with an even-odd rule does not fix it either -- it needs the contours to
be properly nested, and two overlapping bowls are not.

WHAT IS RIGHT. Node the contours into one planar graph, polygonize it into faces, and keep
a face when its winding number is nonzero. That is what a TrueType rasteriser does.
Self-intersection stops being a special case and the counters fall out on their own.

ORNAMENTS ARE THE CALLER'S BUSINESS. This returns the glyph as the font draws it, dotted
zero included. The two callers want opposite things -- face_art drops the ornament (it is
a sub-0.2 mm mask island the pour cannot reach), the medallion deletes marks under its own
DIAL_MIN_MARK -- so neither policy belongs here.
"""


def winding(pt, ring):
    """Signed crossing number of a closed vertex ring about pt (Sunday's algorithm)."""
    x, y = pt
    w = 0
    for i in range(len(ring) - 1):
        x0, y0 = ring[i]
        x1, y1 = ring[i + 1]
        if y0 <= y:
            if y1 > y and (x1 - x0) * (y - y0) - (x - x0) * (y1 - y0) > 0:
                w += 1
        elif y1 <= y and (x1 - x0) * (y - y0) - (x - x0) * (y1 - y0) < 0:
            w -= 1
    return w


def outline(txt, fontpath, size=100.0):
    """-> shapely geometry of `txt` at the font's own scale, y UP (matplotlib's frame).

    Callers scale and flip; this only answers "what shape is this text".
    """
    from shapely.geometry import LineString
    from shapely.ops import unary_union, polygonize
    from matplotlib.textpath import TextPath
    from matplotlib.font_manager import FontProperties
    from matplotlib.path import Path
    tp = TextPath((0, 0), txt, size=size, prop=FontProperties(fname=fontpath))
    rings = [[tuple(p) for p in c] for c in
             Path(tp.vertices, tp.codes).to_polygons(closed_only=True) if len(c) >= 4]
    rings = [r if r[0] == r[-1] else r + [r[0]] for r in rings]
    if not rings:
        return None
    faces = list(polygonize(unary_union([LineString(r) for r in rings])))
    return unary_union([f for f in faces
                        if sum(winding(f.representative_point().coords[0], r)
                               for r in rings) != 0])
