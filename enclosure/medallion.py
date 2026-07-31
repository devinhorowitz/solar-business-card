"""The back medallion -- Z9F, graduated from the engraving studies (2026-07-31).

One coin says what the object is: a sunken disc in the clear band between the fin
fields, its crests -- ring text, rim, hoop, monogram, serial -- standing on the SAME
+0.15 bearing plane as the proud frame. Finishing is the whole part face-down on a
lapping plate: the plate touches frame + crests and nothing else, by geometry, so the
bright/dark two-texture contrast is a bench operation that re-does forever. The full
decision trail (ten study spins, every number measured) lives in
enclosure/engraving-studies/.

THE FOUR PARAMETERS -- the agnostic contract. The next maker drops in their own facts:

    RING_TEXT      any string; tracking is DERIVED (n chars into 360 deg), so the ring
                   re-closes itself. The build ASSERTS the envelope: cells must clear
                   glyph ink + the coin tool, ~20..47 characters at this radius.
    RING_ANCHOR    the word or phrase centred on 12 o'clock; the rest of the string
                   follows clockwise, and the year (or whatever ends the string) lands
                   opposite by construction when the separators are symmetric.
    DIAL_MONOGRAM  2-4 initials; the build asserts the dial fits inside the hoop.
    SERIAL         variable data -- one text substitution per unit; the dial line is
                   "No <SERIAL>" (the traditional numero: a full o, not the thin-walled
                   ordinal masculine).

MACHINING RULES THE GEOMETRY ENFORCES (found the hard way in spins 8-10):

  * Islands, not relief: crests are stock-plane islands with VERTICAL walls, cleared by
    straight end mills -- the O0.4 takes the open coin to its floor, the O0.3
    rest-machines only what the O0.4 cannot enter, at its own shallower floor. A
    tapered cutter at these wall heights would knife-edge a 0.30 stroke.
  * MIN_ISLAND: any detached mark smaller than 0.55 in both dimensions (an interpunct
    at O0.41, a lowercase tittle at O0.33) regrows as a O0.55 round at its own
    centroid -- same mark, legal post. This is why RING_TEXT should stay caps: a
    lowercase i's dot sits over a 0.229 gap no tool reaches and WELDS to its stem.
  * DIAL_MIN_MARK: detached marks under 0.35 in the dial are DELETED, not grown --
    JetBrains Mono's coding-font dotted zero floats a O0.29 ornament in every 0's
    counter, and growing it would fill the counter. Plain oval zero, the classical
    engraving form; every serial is safe.
  * THE AUDIT ASSERTS AT BUILD TIME: every standing island must span >= MIN_ISLAND.
    Change a parameter into something unmachinable and the generator refuses to emit
    a STEP, which is the whole point of a contract.

Everything here is shapely on board coordinates; the generator supplies its own text
renderer (_maker_text) and does the CadQuery work. The final X-mirror about the board
centreline (machined from the back) is applied HERE, so the generator cuts the returned
geometry verbatim.
"""
from __future__ import annotations

import math

import shapely.affinity as aff
from shapely.geometry import Point, Polygon
from shapely.ops import unary_union

from fit_rules import W, fin_band

# ---- the four parameters (the agnostic contract) -------------------------------------
RING_TEXT = "SOLAR · NFC · TITANIUM · ATL GA · MMXXVI · "
RING_ANCHOR = "SOLAR · NFC"
DIAL_MONOGRAM = "DRH"
SERIAL = "001"                     # variable data: one substitution per unit

# ---- fixed geometry (the Z9F architecture) --------------------------------------------
CX = W / 2.0
R_TEXT, RING_CAP = 10.8, 1.80      # ring radius / cap height
COIN_R, RIM_W = 12.15, 0.70        # recess inner radius; rim annulus COIN_R..COIN_R+RIM_W
HOOP = (8.75, 9.25)                # the band/dial separator annulus
COIN_D, REST_D = 0.45, 0.25        # floors below the ART FIELD (<= fin-valley ceiling)
PLANE = 0.15                       # the bearing plane == the frame's proudness
TOOL_MAIN_R, TOOL_REST_R = 0.20, 0.15    # O0.4 coin finisher, O0.3 rest pass
MIN_ISLAND = 0.55                  # no detached standing mark smaller than this
DIAL_MIN_MARK = 0.35               # dial marks under this are font ornament: deleted
DIAL = [(DIAL_MONOGRAM, 4.80, -1.6, "b"), (f"No {SERIAL}", 1.80, 3.0, "r")]
_DUST = 0.005                      # sub-0.005 mm2 opening residue: numerical, dropped


def _mirror(g):
    return aff.scale(g, xfact=-1, yfact=1, origin=(CX, 0.0))


def _regrow(parts, min_island):
    out = []
    for p in parts:
        b = p.bounds
        if (b[2] - b[0]) < min_island and (b[3] - b[1]) < min_island:
            out.append(Point(p.centroid).buffer(min_island / 2.0, resolution=32))
        else:
            out.append(p)
    return out


def _char_cell(text_fn, font, ch, cap):
    """One ring character, upright, centred on the origin, at true cap scale.

    Built as the pair "H"+ch: the H pins the scale (the text renderer normalises each
    STRING's bounds to the cap height -- alone, a mid-dot becomes a boulder) and pins
    the vertical frame. Only the second cell's ink is kept, and the MIN_ISLAND rule
    regrows any detached mark that would stand as an illegal post.
    """
    if ch == " ":
        return None
    pair = text_fn("H" + ch, 0.0, 0.0, cap, font)
    if pair is None:
        return None
    b = pair.bounds
    g = aff.scale(pair, xfact=1, yfact=-1, origin=(0, (b[1] + b[3]) / 2.0))
    h_ink = text_fn("H", 0.0, 0.0, cap, font)
    hb = h_ink.bounds
    x_split = b[0] + (hb[2] - hb[0]) + 0.05
    polys = list(g.geoms) if g.geom_type.startswith("Multi") else [g]
    keep = [p for p in polys if p.centroid.x > x_split]
    if not keep:
        return None
    gk = unary_union(_regrow(keep, MIN_ISLAND))
    kb = gk.bounds
    return aff.translate(gk, -(kb[0] + kb[2]) / 2.0, -(b[1] + b[3]) / 2.0)


def _ring(text_fn, font, cy):
    """RING_TEXT on the circle: derived tracking, RING_ANCHOR centred at 12 o'clock."""
    txt = RING_TEXT
    n = len(txt)
    dphi = 360.0 / n
    i0 = (txt.index(RING_ANCHOR) + (len(RING_ANCHOR) - 1) / 2.0
          if RING_ANCHOR in txt else 0.0)
    parts = []
    for i, ch in enumerate(txt):
        c = _char_cell(text_fn, font, ch, RING_CAP)
        if c is None:
            continue
        phi = (i - i0) * dphi
        c = aff.rotate(c, phi, origin=(0, 0))
        rad = math.radians(phi)
        parts.append(aff.translate(c, R_TEXT * math.sin(rad), -R_TEXT * math.cos(rad)))
    return aff.translate(unary_union(parts), CX, cy)


def _dial(text_fn, fonts, cy):
    """The dial stack, centred on CX, marks under DIAL_MIN_MARK deleted (dotted zero)."""
    out = []
    for txt, cap, dy, w in DIAL:
        g = text_fn(txt, 0.0, cy + dy, cap, fonts[w])
        if g is None:
            continue
        g = aff.scale(g, xfact=1, yfact=-1, origin=(0, cy + dy))
        b = g.bounds
        g = aff.translate(g, CX - (b[0] + b[2]) / 2.0, 0.0)
        parts = list(g.geoms) if g.geom_type.startswith("Multi") else [g]
        parts = [p for p in parts
                 if max(p.bounds[2] - p.bounds[0], p.bounds[3] - p.bounds[1])
                 >= DIAL_MIN_MARK]
        out.append(unary_union(parts))
    return unary_union(out)


def _annulus(cy, r0, r1):
    return (Point(CX, cy).buffer(r1, resolution=64)
            .difference(Point(CX, cy).buffer(r0, resolution=64)))


def _opening(g, r):
    """(g (-) r) (+) r -- what a radius-r cutter can clear inside g."""
    return (g.buffer(-r, join_style=1, resolution=32)
             .buffer(r, join_style=1, resolution=32))


def _parts(g):
    return list(g.geoms) if g.geom_type.startswith("Multi") else ([] if g.is_empty else [g])


def geometry(text_fn, font_r, font_b):
    """-> dict of FINAL machining geometry (already X-mirrored), all board coords:

        standing   islands to leave at the bearing plane (union as proud prisms)
        cut_main   regions the O0.4 clears, COIN_D below the field
        cut_rest   regions only the O0.3 reaches, REST_D below the field
        disc       the medallion's outer footprint (exclude from any field-wide op)
        cy         the medallion centre (the fin fields' clear-band centre)

    Raises if any parameter breaks the machining contract.
    """
    cy = sum(fin_band()) / 2.0
    fonts = {"r": font_r, "b": font_b}

    # ring envelope: the widest glyph plus the REST tool must fit in every cell -- the
    # O0.3 rest pass is what separates the tightest letter pairs (at REST_D), which is
    # half of what the cascade exists for. 'M' alone is full-cap, so its self-normalised
    # bounds are its true ink width.
    mb = text_fn("M", 0.0, 0.0, RING_CAP, font_r).bounds
    ink = mb[2] - mb[0]
    cell = 2 * math.pi * R_TEXT / len(RING_TEXT)
    assert cell >= ink + 2 * TOOL_REST_R, (
        f"RING_TEXT too long: {len(RING_TEXT)} chars -> {cell:.2f} mm cells, "
        f"needs >= {ink + 2*TOOL_REST_R:.2f} (M ink {ink:.2f} + O{2*TOOL_REST_R:.1f})")

    glyphs = unary_union([
        _ring(text_fn, font_r, cy),
        _dial(text_fn, fonts, cy),
        _annulus(cy, *HOOP),
        _annulus(cy, COIN_R, COIN_R + RIM_W),
    ])
    db = _dial(text_fn, fonts, cy).bounds
    corner = max(math.hypot(x - CX, y - cy)
                 for x in (db[0], db[2]) for y in (db[1], db[3]))
    assert corner <= HOOP[0] - 0.4, (
        f"DIAL_MONOGRAM/SERIAL escape the hoop: corner radius {corner:.2f} vs "
        f"{HOOP[0] - 0.4:.2f} allowed -- shrink the caps or the text")

    disc = Point(CX, cy).buffer(COIN_R + RIM_W, resolution=64)
    region = disc.difference(glyphs)
    reach_main = _opening(region, TOOL_MAIN_R)
    rest_raw = _opening(region, TOOL_REST_R).difference(reach_main)

    # The exact reach difference between the two tools is a SLIVER FACTORY: the O0.3
    # hugs every wall ~0.05 closer than the O0.4, so rest_raw fragments into ~900
    # hair-thin arcs around every letter -- unbuildable booleans and a STEP no CAM
    # seat wants. Wall-hug slivers (inscribed width < 0.10: they vanish under a 0.05
    # erosion) are MERGED INTO THE DEEP CUT instead: that claims <= 0.05 mm of extra
    # O0.4 reach at wall bases -- inside ISO 2768 medium and the shop's +-0.05, and it
    # errs toward CLEARANCE, never phantom metal. Real rest features (counters,
    # channels the O0.4 cannot enter at all) keep their own 0.25 floor.
    slivers, rest_keep = [], []
    for p in _parts(rest_raw):
        (slivers if p.buffer(-0.05).is_empty else rest_keep).append(p)
    reach_main = unary_union([reach_main] + slivers)
    reach_rest = unary_union(rest_keep) if rest_keep else Polygon()
    standing = disc.difference(unary_union([reach_main, reach_rest]))
    standing = unary_union([p for p in _parts(standing) if p.area > _DUST])

    # OCC pays per vertex, and the font outlines + two buffer rounds mint thousands of
    # them: one un-simplified coin boolean is a 20-minute build. 8 um is invisible
    # against the shop's +-0.05 and none of this is fit-critical geometry (the
    # fit_rules no-simplify law protects BOSS clearances, which live elsewhere).
    reach_main = reach_main.simplify(0.008)
    reach_rest = reach_rest.simplify(0.008)
    standing = standing.simplify(0.008)

    # THE AUDIT: no detached standing island below MIN_ISLAND, anywhere, ever.
    small = [p for p in _parts(standing)
             if max(p.bounds[2] - p.bounds[0], p.bounds[3] - p.bounds[1])
             < MIN_ISLAND - 0.02]
    assert not small, (
        f"{len(small)} standing island(s) under {MIN_ISLAND} mm -- the parameters "
        f"produce unmachinable orphan posts (first at {small[0].centroid.coords[0]})")

    return dict(
        standing=_mirror(standing),
        cut_main=_mirror(reach_main),
        cut_rest=_mirror(reach_rest),
        disc=_mirror(disc),
        cy=cy,
    )
