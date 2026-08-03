#!/usr/bin/env python3
"""The card face's CONTACT BLOCK — the three lines of type under the DRH monogram.

WHAT THIS REPLACED. The face type used to be 60 F.Mask polygons paired with 60 identical
F.Cu polygons, vectorised once by hand and dropped into the board. Nothing in the tree
said what the string was, what font it was set in, or how big — you could only read it
off a plot. Changing "Georgia" to "Ga" meant hand-authoring new glyph outlines.

So the type is generated now, from the same JetBrains Mono files the medallion uses, and
the strings live up there in LINES where they can be edited. The reconstruction was
exact before anything moved: measured against the board it replaced, line 1 came back
0.0 % off in both ink area and width, line 2 0.0 % in both. That is what licensed the
swap — the generator reproduced the artwork first, and only then changed it.

THE F.Cu COPY IS GONE, AND THAT IS THE POINT. Each glyph used to be a copper island with
a mask opening on top of it. A copper GRAPHIC carries no net in KiCad, so every letter
was electrically isolated, sitting in a moat the GND pour cleared around it — the pour
reached only 14–26 % of each line's bounding box.

That quietly broke the gold request. mask_art's gold_area() unions every front mask
graphic into the User.1 hard-gold drawing wholesale, on the stated ground that "every
front mask GRAPHIC exposes only GND pour or bare laminate". True of the monogram, true
of the NFC mark, FALSE of the type: it exposed isolated islands. So User.1 was asking a
fab to hard-gold three lines that had no path to the plating bus. Electrolytic gold
needs current; ENIG does not, which is why boards came back looking right — the letters
were taking immersion gold, not the hard gold the drawing ordered. Check [14] could not
see it, because it asks "is there copper under this opening", not "is that copper GND".

The fix is a deletion. Drop the copper islands and the priority-1 GND pour — whose
outline covers 100 % of all three lines — fills behind the openings instead. The mask
alone defines the glyph, the copper under it is the plane, and the type is grounded,
plateable, and one object per shape lighter.

ORDER: run this BEFORE `mask_art.py --apply`, because the gold area is derived from the
board's F.Mask drawings and this writes some of them. You do not have to remember —
consistency check [6] recomputes mask_art's own output and goes red until you do.

    python3 scripts/face_art.py --check     # does the board match LINES?
    python3 scripts/face_art.py --apply     # rewrite the contact block
    python3 scripts/face_art.py --preview out.png
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
PCB = os.path.join(ROOT, "PCB", "solar-glow-drh-v4_0.kicad_pcb")
FONTS = os.path.join(ROOT, "enclosure", "fonts")
REGULAR = os.path.join(FONTS, "JetBrainsMono-Regular.ttf")
BOLD = os.path.join(FONTS, "JetBrainsMono-Bold.ttf")

MARK = "face0000-0000-4000-8000-"      # this generator's uuid namespace, as a literal prefix
# lower case deliberately: KiCad rewrites uuids to lower case on save, so an upper-case
# nibble here would make the board differ from what was emitted the moment it is opened in
# the GUI -- the same shape as the `fill solid` -> `fill yes` drift mask_art records.
TAG = "faceart"

# THE BLOCK THIS GENERATOR OWNS. Everything inside it on F.Mask and F.Cu is ours, and
# --apply removes whatever it finds there before writing. Ownership is by region rather
# than by uuid because the artwork being replaced predates any tagging — a uuid rule
# would have had nothing to grab on the first run. The band is bounded well clear of its
# neighbours: the monogram plate ends at y46.68 and the nearest F.Cu graphic outside the
# type is at y47.70, so 48.5 leaves 0.8 mm of daylight.
BLOCK = (13.0, 48.5, 38.0, 57.5)       # x0, y0, x1, y1

CENTRE_X = 25.40                       # the board's own centreline, W/2

# --- the type ------------------------------------------------------------------------
# SIZE IS CAP HEIGHT -- the height of 'H' in the chosen face -- and position is BASELINE.
# Both choices are load-bearing, and the first preview is what proved it.
#
# The obvious parameterisation is the string's own ink bounding box, and it is what the
# original artwork was set on. It reproduces a whole line perfectly and falls apart the
# moment a line is COMPOSED, because "ink height" then means something different for each
# piece: "404-213-8076" is digits with no descender, "Atlanta, Ga" carries a comma below
# the baseline. Normalising each to the same ink height sets the number ~25 % larger than
# the city. The preview showed it immediately -- line 3 burst its block.
#
# Baseline placement is the same bug in the other axis: align two pieces by their own ink
# TOPS and the digits sit proud of the capitals, because 'l' and 't' ascend past '4'.
# A shared baseline is the only thing that makes composed type sit on one line.
#
# Cap heights below were recovered by fitting the board (solve cap such that the rendered
# ink width equals the measured width), so line 1 reproduces its artwork exactly:
#     line 1  Bold     cap 1.3238   line 2  Regular cap 0.8423   line 3  Regular cap 0.8009
# Note lines 2 and 3 were NOT the same size -- both were set to a 1.05 ink box, but their
# different descender profiles made line 2 5 % larger. Unifying them on one cap is part of
# the point of doing this.
#
# Line 1 is deliberately UNCHANGED. It is already 19.4 mm wide against a ~21.5 mm envelope,
# so it cannot grow without going off-centre or into the coil keepout. Lines 2 and 3 go to
# a round 1.00 -- +19 % on line 2, +25 % on line 3 -- which "Georgia" -> "Ga" pays for by
# taking line 3 from 31 characters to 26.
CAP_SMALL = 1.00
LINES = [
    dict(text="Devin@Horowitz.Law", font=BOLD,    cap=1.3238, baseline=51.3252,
         # The rule under the domain, expressed as a TYPESETTING rule rather than as
         # coordinates: it begins at the pen position after "Devin@" and ends flush with
         # the line's right ink edge, so it keeps meaning the same thing if the string
         # changes. The artwork it replaces ran x 22.165..35.107, y 51.850..52.070; the
         # generated rule lands 0.057 mm to the right of that start, because the legacy
         # one was drawn by eye rather than to the font's advance. 57 um, invisible, and
         # the principled rule is the one worth keeping.
         underline_after="Devin@", underline_top=0.5248, underline_thick=0.220),
    dict(text="Attorney",           font=REGULAR, cap=CAP_SMALL, baseline=53.80),
]

# Line 3 is composed rather than set as one string, because the separator has to land on
# the board centreline with the number to its left and the city to its right. Set as a
# single centred string it cannot: "404-213-8076" is 12 characters and "Atlanta, Ga" is
# 11, so centring the STRING puts the dot off-centre, which is exactly what it did.
PHONE = "404-213-8076"
PLACE = "Atlanta, Ga"
LINE3_BASELINE = 55.86                 # keeps the 0.80 mm gap under line 2 once it grows

# The separator is drawn, not set. The font's own middle dot came out ~0.25 mm across --
# under the 0.3 mm drill this board uses, so it read as a via rather than punctuation.
# 0.6 mm would be exactly a via PAD, which is the other thing not to look like; 0.85
# clears both and still sits inside the 1.25 mm ink band.
DOT_D = 0.85
DOT_GAP = 0.90                         # ink-to-ink clear space either side of the dot


def _cap_unit(fontpath):
    """Height of 'H' at size=100 -- the font-intrinsic ruler every string is scaled by."""
    return _outline("H", fontpath).bounds[3] - _outline("H", fontpath).bounds[1]


def _outline(txt, fontpath):
    """Glyph outlines, minus the ornaments this generator does not want.

    The winding-rule fill lives in scripts/glyphs.py, shared with the medallion engraver
    in enclosure/…-backshell-…-cad.py -- both set type from the same JetBrains Mono files,
    both used to fold contours with reduce(symmetric_difference), and that fold is wrong
    for '8'. Having found it here, in "404-213-8076", it had to be fixed in one place
    rather than two; glyphs.py carries the full reasoning.

    What stays here is the POLICY: glyphs.py returns the glyph as the font draws it, and
    dropping the dotted-zero ornament is this generator's own call, not something the
    medallion (which has DIAL_MIN_MARK for the same job) should inherit.
    """
    import sys as _sys, os as _os
    _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
    from glyphs import outline as _o
    g = _o(txt, fontpath)
    if g is None:
        raise SystemExit(f"face_art: {txt!r} produced no outlines")
    return _drop_counter_islands(g)


def _drop_counter_islands(geom):
    """Delete ornaments that float inside a counter -- JetBrains Mono's DOTTED ZERO.

    It is a coding-font affectation: a dot inside every 0, to tell it from O at 11 px in a
    terminal. On a card it is not read as anything, and as MASK it is actively bad. The one
    in "8076" measured 0.164 mm across -- under mask_art's own MIN_APERTURE of 0.12 once
    the fab's registration is spent, and marooned: it sits inside the zero's counter, where
    the surrounding mask is closed, so the GND plane cannot reach it and the fab's plating
    drawing ends up pointing at bare laminate. Consistency check [14] caught exactly that
    on the first apply, which is what this function exists to answer.

    enclosure/medallion.py deletes the same ornament for the same reason (its DIAL_MIN_MARK
    is 'dial marks under this are font ornament: deleted'), so this is the house rule, not
    a new opinion.

    The test is structural rather than a size threshold: drop a piece only when it lies
    inside another piece's HOLE. A size rule would also eat the dot on an 'i' and the full
    stop in "Devin@Horowitz.Law", which are type, not ornament.
    """
    from shapely.geometry import MultiPolygon, Polygon
    from shapely.ops import unary_union
    parts = list(geom.geoms) if isinstance(geom, MultiPolygon) else [geom]
    holes = [Polygon(r) for p in parts for r in p.interiors]
    if not holes:
        return geom
    return unary_union([p for p in parts
                        if not any(h.contains(p) for h in holes)])


def _run(prefix, cap, fontpath):
    """Pen advance across `prefix`, exactly -- sidebearings cancelled.

    Setting the same probe glyph after the prefix and alone, then differencing their ink
    RIGHT edges, removes both bearings: what is left is only the pen travel. Estimating a
    cell as ink("HH") - ink("H") instead is 0.9 % out on this face, which put the rule
    under the domain 0.057 mm off where the artwork has it.
    """
    a = _outline(prefix + "H", fontpath).bounds[2]
    b = _outline("H", fontpath).bounds[2]
    return (a - b) * cap / _cap_unit(fontpath)


def text_geom(txt, cap, fontpath):
    """JetBrains Mono -> shapely at the given CAP height, baseline on y=0, y running DOWN.

    Returning baseline-relative geometry is what lets a line be composed from pieces: two
    strings translated to the same y sit on the same line whatever glyphs they contain.
    """
    import shapely.affinity as aff
    g = _outline(txt, fontpath)
    s = cap / _cap_unit(fontpath)
    g = aff.scale(g, xfact=s, yfact=s, origin=(0, 0))
    return aff.scale(g, xfact=1.0, yfact=-1.0, origin=(0, 0))   # matplotlib y-up -> KiCad y-down


def build():
    """-> shapely geometry of the whole contact block, in board mm. F.Mask openings."""
    import shapely.affinity as aff
    from shapely.geometry import Point
    from shapely.ops import unary_union
    from shapely.geometry import box as sbox
    parts = []
    for ln in LINES:
        g = text_geom(ln["text"], ln["cap"], ln["font"])
        x0, _, x1, _ = g.bounds
        dx = CENTRE_X - (x0 + x1) / 2.0
        parts.append(aff.translate(g, dx, ln["baseline"]))
        if ln.get("underline_after") is not None:
            ux0 = x0 + dx + _run(ln["underline_after"], ln["cap"], ln["font"])
            ux1 = x1 + dx
            uy = ln["baseline"] + ln["underline_top"]
            parts.append(sbox(ux0, uy, ux1, uy + ln["underline_thick"]))

    # Line 3, hung off the centreline: the dot is placed FIRST and the two halves are
    # measured back from its edges, so the centreline is the fixed point of the layout
    # rather than something the string lengths happen to land on.
    dot_l, dot_r = CENTRE_X - DOT_D / 2.0, CENTRE_X + DOT_D / 2.0
    ph = text_geom(PHONE, CAP_SMALL, REGULAR)
    parts.append(aff.translate(ph, (dot_l - DOT_GAP) - ph.bounds[2], LINE3_BASELINE))
    pl = text_geom(PLACE, CAP_SMALL, REGULAR)
    parts.append(aff.translate(pl, (dot_r + DOT_GAP) - pl.bounds[0], LINE3_BASELINE))
    # centred on the cap band, not the ink box: the ink box is dragged down by the comma
    parts.append(Point(CENTRE_X, LINE3_BASELINE - CAP_SMALL / 2.0)
                 .buffer(DOT_D / 2.0, resolution=32))
    return unary_union(parts)


ZONE_NAME = "faceart"      # ownership marker: --apply strips zones carrying this name
ZONE_PRIORITY = 2          # above the hatched GND pour (1), below the teardrops (30000+)


def emit_zones(geom):
    """The letters as SOLID copper on GND -- one zone per glyph piece.

    WHY THIS EXISTS. Deleting the F.Cu islands grounded the type and cost it its finish,
    and CI's regenerated card-face render is where that showed: the front GND pour is
    HATCH_PATTERN, 0.20 mm on a 0.50 mm gap, so the openings came back sitting over mesh
    and the type read as pale screen instead of solid gold. The repo already knew the
    hazard from the other side -- the cartouche was switched off in July because "the GND
    crosshatch under it plated ENIG and read as a gold mesh".

    A zone carries a net, which a graphic does not. So the letters go back to being solid
    copper AND are on GND: solid gold to look at, and a real path to the plating bus, which
    is strictly better than the islands this replaced (solid but ungrounded).

    The outline is each piece's EXTERIOR only -- counters are not cut out. Copper inside the
    'o' is covered by mask either way, so leaving it saves the bridged-hole seam a zone
    outline would otherwise need.

    `filled_polygon` is emitted equal to the outline, which is exact here and not a guess:
    the nearest non-GND copper to any glyph measures 0.350 mm, against a 0.152 mm floor, so
    no part of any letter is clearance-limited and the fill has nothing to cut back from.
    KiBot refills before plotting regardless; this is so the fill stored in the board is
    right for anything that reads it without refilling, check [14] included.
    """
    from shapely.geometry import MultiPolygon
    parts = list(geom.geoms) if isinstance(geom, MultiPolygon) else [geom]
    out = []
    for p in sorted(parts, key=lambda q: (-q.area, q.bounds)):
        pts = "".join(f"\t\t\t\t(xy {x:.4f} {y:.4f})\n" for x, y in list(p.exterior.coords)[:-1])
        out.append(
            '\t(zone\n\t\t(net "GND")\n\t\t(name "' + ZONE_NAME + '")\n'
            '\t\t(layer "F.Cu")\n\t\t(hatch none 0.5)\n'
            f'\t\t(priority {ZONE_PRIORITY})\n'
            '\t\t(connect_pads yes\n\t\t\t(clearance 0)\n\t\t)\n'
            '\t\t(min_thickness 0.0254)\n'
            # NEVER remove islands: every letter is a small shape that merges with the pour
            # only because they share a net. Under the default ALWAYS it would be a candidate
            # for deletion, and a vanished letter is not a failure anyone would see coming.
            '\t\t(fill yes\n\t\t\t(island_removal_mode 1)\n\t\t)\n'
            f'\t\t(polygon\n\t\t\t(pts\n{pts}\t\t\t)\n\t\t)\n'
            f'\t\t(filled_polygon\n\t\t\t(layer "F.Cu")\n\t\t\t(pts\n{pts}\t\t\t)\n\t\t)\n'
            '\t)\n')
    return "".join(out)


def _in_block(x0, y0, x1, y1):
    bx0, by0, bx1, by1 = BLOCK
    return x0 >= bx0 and y0 >= by0 and x1 <= bx1 and y1 <= by1


def board_block(board):
    """-> (F.Mask geometry, F.Cu shape count) currently inside the block."""
    import pcbnew
    from shapely.geometry import Polygon
    from shapely.ops import unary_union
    mm, IU = pcbnew.ToMM, 1e6
    fm, fc = board.GetLayerID("F.Mask"), board.GetLayerID("F.Cu")
    mask, cu = [], 0
    for d in board.GetDrawings():
        lay = d.GetLayer()
        if lay not in (fm, fc):
            continue
        bb = d.GetBoundingBox()
        if not _in_block(mm(bb.GetLeft()), mm(bb.GetTop()),
                         mm(bb.GetRight()), mm(bb.GetBottom())):
            continue
        if lay == fc:
            cu += 1
            continue
        ps = pcbnew.SHAPE_POLY_SET()
        d.TransformShapeToPolygon(ps, fm, 0, pcbnew.FromMM(0.001), pcbnew.ERROR_INSIDE)
        for i in range(ps.OutlineCount()):
            ol = ps.Outline(i)
            pts = [(ol.CPoint(k).x / IU, ol.CPoint(k).y / IU)
                   for k in range(ol.PointCount())]
            if len(pts) >= 3:
                mask.append(Polygon(pts).buffer(0))
    return (unary_union(mask) if mask else None), cu


def strip_block(txt):
    """Remove every gr_poly on F.Mask or F.Cu whose points all fall inside BLOCK."""
    out, removed, i = [], 0, 0
    while True:
        m = re.search(r'(?m)^\t\((?:gr_poly|zone)\n', txt[i:])
        if not m:
            out.append(txt[i:])
            break
        st = i + m.start()
        depth, j, instr = 0, st, False
        while True:
            c = txt[j]
            if instr:
                if c == '"':
                    instr = False
            elif c == '"':
                instr = True
            elif c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        blk = txt[st:j + 1]
        lay = re.search(r'\(layer "([^"]+)"\)', blk)
        xy = [(float(a), float(b)) for a, b in re.findall(r'\(xy (-?[\d.]+) (-?[\d.]+)\)', blk)]
        # a zone is ours by NAME (it may legitimately sit anywhere); a graphic is ours by
        # region, because the artwork this replaced predates any tagging
        if blk.startswith("\t(zone"):
            mine = f'(name "{ZONE_NAME}")' in blk
        else:
            mine = (lay and lay.group(1) in ("F.Mask", "F.Cu") and xy and
                    _in_block(min(p[0] for p in xy), min(p[1] for p in xy),
                              max(p[0] for p in xy), max(p[1] for p in xy)))
        if mine:
            out.append(txt[i:st])
            removed += 1
            i = j + 2 if txt[j + 1:j + 2] == "\n" else j + 1
        else:
            out.append(txt[i:j + 1])
            i = j + 1
    return "".join(out), removed


def preview(path):
    """Old (from the board) against new (from LINES), so a size change is looked at."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import pcbnew
    from shapely.geometry import MultiPolygon
    board = pcbnew.LoadBoard(PCB)
    old, _ = board_block(board)
    new = build()
    fig, axes = plt.subplots(2, 1, figsize=(9, 5.2), dpi=200)
    for ax, geom, title in ((axes[0], old, "on the board now"),
                            (axes[1], new, "generated from LINES")):
        ax.set_facecolor("#141414")
        gs = list(geom.geoms) if isinstance(geom, MultiPolygon) else [geom]
        for p in gs:
            ax.fill(*p.exterior.xy, color="#d4af37", zorder=2)
            for r in p.interiors:
                ax.fill(*r.xy, color="#141414", zorder=3)
        ax.axvline(CENTRE_X, color="#4488ff", lw=0.6, ls="--", zorder=4)
        ax.set_xlim(13.5, 37.5)
        ax.set_ylim(57.0, 49.0)
        ax.set_aspect("equal")
        ax.set_title(title, fontsize=8)
        ax.tick_params(labelsize=6)
    fig.tight_layout()
    fig.savefig(path, facecolor="white")
    print(f"wrote {path}")


ROUND_TRIP = 0.02      # mm2 -- see check_state()


def check_state():
    """-> (ok, message). THE one definition of 'does the board carry what LINES says'.

    consistency check [17] calls this rather than rebuilding the comparison, so the gate
    and the generator cannot drift apart -- the failure mode [6] had before mask_art grew
    its own generate().

    The area bar is a TOLERANCE, not exactness, because this compares GEOMETRY across a
    lossy round trip: emit() writes vertices at 4 decimal places and _bridge() splices
    interior rings into the exterior with a seam, so reading the board back never returns
    the shapely input to the bit. Measured round-trip noise on this block is 0.0050 mm2 out
    of 19.02 -- 0.026 %. The bar sits 4x above that and is still ~0.1 % of the block, so
    anything an editor would actually do (a cap change, a re-word, a baseline nudge) clears
    it by orders of magnitude.

    mask_art compares TEXT instead, which is exact, and that does not work here: two
    generators now splice into the same file, so block order depends on which ran last and
    a string compare would report drift on a board nobody touched.
    """
    import pcbnew
    new = build()
    old, cu = board_block(pcbnew.LoadBoard(PCB))
    if cu:
        return False, (f"STALE -- {cu} F.Cu graphic(s) in the contact block; the type is "
                       f"not grounded, and User.1 is ordering hard gold on isolated copper")
    sym = new.symmetric_difference(old).area if old else new.area
    if sym > ROUND_TRIP:
        return False, (f"STALE -- board and LINES differ by {sym:.4f} mm2 "
                       f"(round-trip noise is under {ROUND_TRIP}); run face_art --apply")

    # AND THE LETTERS MUST BE SOLID COPPER ON GND. Openings alone are not enough: with the
    # copper islands deleted and no zone under them, the type sits on the front pour, which
    # is HATCH_PATTERN -- 0.20 mm on a 0.50 mm gap -- and plates as mesh. That shipped once,
    # and only CI's regenerated card-face render showed it, because the fill stored in the
    # board still carried the moats from the islands. A number is cheaper than a picture.
    from shapely.geometry import Polygon
    from shapely.ops import unary_union
    import pcbnew as _p
    fc = _p.LoadBoard(PCB).GetLayerID("F.Cu")
    board = _p.LoadBoard(PCB)
    fill = []
    for z in board.Zones():
        if z.GetZoneName() != ZONE_NAME:
            continue
        if z.GetFillMode() != 0:
            return False, f"the {ZONE_NAME} zones are not SOLID fill -- the type would plate as mesh"
        ps = z.GetFilledPolysList(fc)
        for i in range(ps.OutlineCount()):
            ol = ps.Outline(i)
            pts = [(ol.CPoint(k).x / 1e6, ol.CPoint(k).y / 1e6) for k in range(ol.PointCount())]
            if len(pts) >= 3:
                fill.append(Polygon(pts).buffer(0))
    if not fill:
        return False, ("no solid GND zone under the type -- the openings would sit on the "
                       "hatched pour and plate as mesh; run face_art --apply")
    covered = new.intersection(unary_union(fill)).area / new.area * 100
    if covered < 99.0:
        return False, (f"solid GND copper reaches only {covered:.1f}% of the type; the rest "
                       f"would plate as hatch")
    return True, (f"the contact block matches LINES ({len(list(getattr(new, 'geoms', [new])))} "
                  f"opening(s), {new.area:.2f} mm2), carries no F.Cu island, and sits on "
                  f"{covered:.1f}% solid GND copper")


def main():
    import pcbnew
    mode = sys.argv[1] if len(sys.argv) > 1 else "--check"
    if mode == "--preview":
        preview(sys.argv[2] if len(sys.argv) > 2 else "face_art.png")
        return
    sys.path.insert(0, HERE)
    import mask_art
    new = build()
    board = pcbnew.LoadBoard(PCB)
    old, cu = board_block(board)
    r = mask_art.report(new)
    print(f"  contact block: {r['pieces']} piece(s), {r['area']:.2f} mm2 of F.Mask "
          f"opening, narrowest feature {r['min_aperture']:.3f} mm")
    if mode == "--check":
        good, msg = check_state()
        print("  " + msg)
        sys.exit(0 if good else 1)
    if mode != "--apply":
        raise SystemExit(__doc__)
    # NORMALISE THE LINE ENDINGS BEFORE THE SURGERY, restore them after -- mask_art's rule,
    # for mask_art's reason. This board is CRLF, and strip_block anchors on '^\t(gr_poly\n'.
    # Reading it raw, that pattern matches nothing: the first --apply removed 0 shapes and
    # appended 54 on top of the 121 already there, doubling the artwork. Caught because the
    # run reported "removed 0" and the board was restored from a copy taken beforehand.
    raw = open(PCB, "rb").read()
    crlf = raw.count(b"\r\n")
    if crlf and crlf != raw.count(b"\n"):
        sys.exit("face_art: mixed line endings in the board; refusing to touch it")
    nl = "\r\n" if crlf else "\n"
    txt = raw.decode("utf-8").replace("\r\n", "\n")
    stripped, removed = strip_block(txt)
    if not removed:
        sys.exit("face_art: found nothing to replace in the block -- refusing to write, "
                 "since appending to artwork that is still there would double it")
    body = (mask_art.emit(new, layer="F.Mask", tag=TAG).replace(mask_art.MARK, MARK)
            + emit_zones(new))
    out = mask_art._splice(stripped, body)
    open(PCB, "wb").write(out.replace("\n", nl).encode("utf-8"))
    print(f"  removed {removed} shape(s) from the block, wrote {r['pieces']} F.Mask "
          f"opening(s) and {r['pieces']} solid GND zone(s) under them -- the letters are "
          f"copper ON A NET, not graphics, and not the hatched pour")
    print("  NOW RUN: python3 scripts/mask_art.py --apply   (the gold area is derived "
          "from these openings)")


if __name__ == "__main__":
    main()
