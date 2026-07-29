#!/usr/bin/env python3
"""Generate the front soldermask artwork — every opening is computed from the copper.

    python3 scripts/mask_art.py              # report only, touch nothing
    python3 scripts/mask_art.py --apply      # write the art into the board
    python3 scripts/mask_art.py --check      # does the board match current routing?

WHAT IT DRAWS TODAY

One thing: the NFC contactless mark over the antenna (see "the NFC indicator" below).

The left-field CARTOUCHE — the negative-routing ornament that was this script's whole
reason to exist — is switched off (`CARTOUCHE = False`). The generator is intact and
one constant brings it back; see the block above the switch for why it is off.

THE RULE THAT GOVERNS EVERY OPENING HERE

Whatever this script opens, it opens as (shape - live copper). The show face carries
live front routing, and a plain mask window would lay a signal trace bare on a card
that lives in a wallet. Only GND and bare laminate may be exposed. That subtraction is
also why the art has to be GENERATED: it tracks the routing, so a re-route followed by
`--apply` is correct again, and check_consistency [6] gates on it — art drawn once and
left behind goes quietly WRONG the first time a trace moves, rather than merely stale.

MANUFACTURING

Opening edges stand off live copper by KEEP (0.18 mm), and nothing narrower than
MIN_APERTURE (0.12 mm) survives the cleanup pass, so no opening asks the fab for a
gold sliver or a mask dam it cannot image. --report prints the worst case.
"""
from __future__ import annotations

import argparse
import math
import re
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BOARD = ROOT / "PCB" / "solar-glow-drh-v4_0.kicad_pcb"

# Every shape this script emits carries a fixed UUID PREFIX, which is how --apply finds
# and replaces its own previous output without disturbing anything a human drew.
#
# It is a literal prefix, not uuid5(namespace, tag): uuid5 hashes the namespace in, so
# its output shares no leading characters with it and the shapes were unfindable. The
# first cut of this script made exactly that mistake and --check reported DRIFT against
# art it had just written.
MARK = "a17e0000-0000-4000-8000-"
TAG = "maskart"

# --- the left-field cartouche (OFF) -----------------------------------------------
# WHY IT IS OFF, 2026-07-29. The cartouche opened 222 mm2 of mask over the left mid-field
# so the GND crosshatch under it plated ENIG and read as a gold mesh with the signal nets
# as dark rivers. It worked, and against MATTE BLACK mask it was the best thing on the card.
#
# What killed it was the finish study for the transparent-mask variant. Under clear LPI the
# covered copper shows through as bare copper, so the face becomes gold-on-copper-on-tan --
# three warm tones with almost no separation, and 222 mm2 of gold mesh sitting next to the
# gold monogram plate reads as one indistinct field rather than two elements. Gold vs. matte
# black is contrast; gold vs. copper is a smudge. Removing the cartouche is what buys the
# monogram its silence back, on either mask colour.
#
# Nothing about the GENERATOR was wrong, so nothing about it is deleted: flip this to True,
# run --apply, and the ornament comes back exactly as it was. `build()` below and the
# FIELD/RING constants are its whole definition.
CARTOUCHE = False

# --- geometry, in board mm -------------------------------------------------------
# Cartouche sits in the left mid-field: clear of both cells (they occupy y 4.25-27.25
# and 61.65-84.65), clear of the monogram plate, and inside the perimeter frame.
FIELD = (3.30, 29.00, 13.70, 60.10)
FIELD_R = 2.60
RING = (2.85, 28.55, 14.15, 60.55)
RING_R = 2.90
RING_W = 0.16
KEEP = 0.18          # opening-to-live-copper standoff
MIN_APERTURE = 0.12  # narrowest gold the mask may hold; see CLEANUP below


def _uid(tag: str) -> str:
    import hashlib
    return MARK + hashlib.sha1(tag.encode()).hexdigest()[:12]


def rounded(x0, y0, x1, y1, r):
    from shapely.geometry import box
    return box(x0, y0, x1, y1).buffer(-r).buffer(r * 2).intersection(box(x0, y0, x1, y1))


def live_copper(board, keep=KEEP):
    """Union of every non-GND front-copper item, grown by the standoff."""
    from shapely.geometry import box, Point, LineString
    from shapely.ops import unary_union
    IU = 1e6
    fcu = board.GetLayerID("F.Cu")
    parts = []
    for t in board.GetTracks():
        if not t.IsOnLayer(fcu) or t.GetNetname() == "GND":
            continue
        s, e = t.GetStart(), t.GetEnd()
        r = t.GetWidth() / IU / 2 + keep
        a, b = (s.x / IU, s.y / IU), (e.x / IU, e.y / IU)
        parts.append(Point(a).buffer(r) if a == b else LineString([a, b]).buffer(r))
    for z in board.Zones():
        if not z.IsOnLayer(fcu) or z.GetNetname() in ("GND", ""):
            continue
        bb = z.GetBoundingBox()
        parts.append(box(bb.GetLeft() / IU, bb.GetTop() / IU,
                         bb.GetRight() / IU, bb.GetBottom() / IU).buffer(keep))
    for f in board.GetFootprints():
        for p in f.Pads():
            if not p.IsOnLayer(fcu) or p.GetNetname() == "GND":
                continue
            bb = p.GetBoundingBox()
            parts.append(box(bb.GetLeft() / IU, bb.GetTop() / IU,
                             bb.GetRight() / IU, bb.GetBottom() / IU).buffer(keep))
    return unary_union(parts) if parts else None


def build(board):
    """The mask opening, as a shapely geometry."""
    from shapely.ops import unary_union
    live = live_copper(board)
    win = rounded(*FIELD, FIELD_R)
    ring = rounded(*RING, RING_R).exterior.buffer(RING_W / 2.0)
    art = unary_union([win, ring])
    art = art.difference(live) if live is not None else art
    # CLEANUP — morphological opening at half the aperture floor.
    #
    # Subtracting the routing leaves hair-thin gold slivers wherever two traces run
    # close together; the first run of this generator produced one 0.002 mm wide.
    # Slivers that fine either fail to image or come out ragged, so erode-then-dilate
    # removes anything narrower than MIN_APERTURE and rounds the necks it leaves.
    # It also reads better: those slivers were visual noise, not pattern.
    t = MIN_APERTURE / 2.0
    art = art.buffer(-t, join_style=1).buffer(t, join_style=1)
    return art



# --- the NFC indicator ------------------------------------------------------------
# A quiet contactless mark on the SHOW FACE, over the antenna, so the card says what it is
# and where to tap.
#
# IT IS ON THE FRONT BECAUSE THE FRONT IS THE ONLY FACE ANYONE SEES. The shell is back-only:
# the whole rear of the board lives inside titanium. Art on B.Mask is invisible in the
# assembled card -- which is what made exposing the coil a bad trade, and is why that was
# reverted (see below).
#
# THE COIL STAYS UNDER MASK. Opening it plated the turns with ENIG, and nickel is exactly the
# wrong thing to put in an RF conductor: ~7x copper's resistivity, ferromagnetic, and at
# 13.56 MHz its skin depth (~3-4 um) is THINNER than the plated layer (3-6 um), so the current
# crowding into the surface crowds into nickel. It raises the coil's AC resistance and costs Q.
# Soldermask, by contrast, is non-magnetic and non-conductive -- it does nothing to the flux
# path, so removing it never helped the ferrite. Gold coil: invisible, and slightly worse.
#
# Generic contactless waves, NOT the NFC Forum N-Mark: that mark is licensed, and this is a
# personal card. Same rule as the cartouche -- the opening is (glyph - live copper), so it can
# only ever lay GND or bare laminate bare, never a signal.
NFC_ORIGIN = (41.00, 44.45)     # board coords: over the antenna box, right of the monogram
NFC_RADII = (0.55, 1.35, 2.15, 2.95)
NFC_W = 0.38                    # wave stroke
NFC_SPAN = 46.0                 # half-angle in degrees, opening +X


def nfc_mark(board=None, keep=KEEP):
    """The contactless waves, minus any live front copper."""
    import math
    from shapely.geometry import Point, Polygon
    from shapely.ops import unary_union
    cx, cy = NFC_ORIGIN
    a0, a1 = math.radians(-NFC_SPAN), math.radians(NFC_SPAN)
    wedge = Polygon([(cx, cy)] + [(cx + 9 * math.cos(a0 + (a1 - a0) * i / 64.0),
                                   cy + 9 * math.sin(a0 + (a1 - a0) * i / 64.0))
                                  for i in range(65)])
    parts = []
    for r in NFC_RADII:
        ring = (Point(cx, cy).buffer(r + NFC_W / 2, resolution=64)
                .difference(Point(cx, cy).buffer(max(r - NFC_W / 2, 0.0), resolution=64)))
        g = ring.intersection(wedge)
        if not g.is_empty:
            parts.append(g)
    glyph = unary_union(parts)
    if board is not None:
        live = live_copper(board, keep)
        if live is not None:
            glyph = glyph.difference(live)
    t = MIN_APERTURE / 2.0
    return glyph.buffer(-t, join_style=1).buffer(t, join_style=1)


def nfc_guard(board, glyph):
    """Refuse to lay any live front net bare. Returns complaints; empty means safe."""
    live = live_copper(board, 0.0)
    bad = []
    if live is not None and live.intersects(glyph):
        bad.append(f"the mark would expose {live.intersection(glyph).area:.3f} mm2 of live front copper")
    return bad


# --- emit ------------------------------------------------------------------------

def _bridge(poly):
    """Splice interior rings into the exterior; gr_poly carries no holes."""
    ext = list(poly.exterior.coords)[:-1]
    for ring in poly.interiors:
        pts = list(ring.coords)[:-1]
        best = None
        for i, e in enumerate(ext):
            for j, r in enumerate(pts):
                d = (e[0] - r[0]) ** 2 + (e[1] - r[1]) ** 2
                if best is None or d < best[0]:
                    best = (d, i, j)
        _, i, j = best
        ext = ext[:i + 1] + pts[j:] + pts[:j + 1] + [ext[i]] + ext[i + 1:]
    return ext


def emit(geom, layer="F.Mask", tag=None) -> str:
    from shapely.geometry import MultiPolygon
    out = []
    geoms = list(geom.geoms) if isinstance(geom, MultiPolygon) else [geom]
    for k, p in enumerate(sorted(geoms, key=lambda q: (-q.area, q.bounds))):
        if p.is_empty or p.area <= 1e-9:
            continue
        body = "".join(f"\t\t\t(xy {x:.4f} {y:.4f})\n" for x, y in _bridge(p))
        out.append(f'\t(gr_poly\n\t\t(pts\n{body}\t\t)\n'
                   f'\t\t(stroke\n\t\t\t(width 0)\n\t\t\t(type solid)\n\t\t)\n'
                   # (fill yes), not (fill solid): KiCad REWRITES solid -> yes on every
                   # save, so emitting `solid` made --check report DRIFT after any GUI save
                   # even with the routing untouched -- a gate that cries wolf, and an
                   # --apply that produces a no-op-but-noisy board diff to silence it.
                   # Matching KiCad's own canonical form makes the check stable.
                   f'\t\t(fill yes)\n\t\t(layer "{layer}")\n'
                   f'\t\t(uuid "{_uid(f"{tag or TAG}-{k}")}")\n\t)\n')
    return "".join(out)


def strip_existing(txt: str) -> tuple[str, int]:
    """Remove a previous generation, identified by its uuid namespace prefix."""
    pref = MARK
    out, n, i = [], 0, 0
    while True:
        m = re.search(r'(?m)^\t\(gr_poly\n', txt[i:])
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
        if f'(uuid "{pref}' in blk:
            out.append(txt[i:st])
            n += 1
            i = j + 2 if txt[j + 1:j + 2] == "\n" else j + 1
        else:
            out.append(txt[i:j + 1])
            i = j + 1
    return "".join(out), n


def _splice(stripped: str, body: str) -> str:
    """Insert the generated block just inside the board's final closing paren."""
    cut = stripped.rstrip().rfind(")")
    return stripped[:cut] + body + stripped[cut:]


def report(geom):
    from shapely.geometry import MultiPolygon
    geoms = list(geom.geoms) if isinstance(geom, MultiPolygon) else [geom]
    radii = []
    for p in geoms:
        lo, hi = 0.0, 1.0
        for _ in range(34):
            mid = (lo + hi) / 2
            if p.buffer(-mid).is_empty:
                hi = mid
            else:
                lo = mid
        radii.append(lo * 2)
    return dict(pieces=len(geoms), area=sum(p.area for p in geoms),
                min_aperture=min(radii) if radii else 0.0)



def generate(board):
    """-> (body, cartouche_or_None, nfc_mark). THE one definition of what this generator writes.

    main() and check_consistency [6] both call this. They used not to: the check rebuilt only
    `emit(build(board))` and compared that against the whole file, which was a second, quieter
    copy of "what the generator emits". It agreed with reality exactly as long as the generator
    owned one thing -- and reported the board STALE the moment the coil aperture made it two,
    while `mask_art --check` on the same board said MATCH. One home instead.
    """
    art = build(board) if CARTOUCHE else None
    mark = nfc_mark(board)
    if mark.is_empty:
        raise SystemExit("mask_art: the NFC mark came out empty -- live copper ate all of it")
    body = emit(art) if art is not None else ""
    return body + emit(mark, tag=f"{TAG}-nfc"), art, mark


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    try:
        import pcbnew  # noqa
    except ImportError:
        sys.exit("mask_art: needs KiCad's pcbnew python module")
    import pcbnew

    board = pcbnew.LoadBoard(str(BOARD))
    body, art, mark = generate(board)
    if art is None:
        print("  cartouche: OFF (CARTOUCHE = False) — the left mid-field stays under mask")
    else:
        r = report(art)
        print(f"  cartouche: {r['pieces']} piece(s), {r['area']:.1f} mm² of gold, "
              f"narrowest gold aperture {r['min_aperture']:.3f} mm")
        if r["min_aperture"] < 0.10:
            print(f"  WARNING: {r['min_aperture']:.3f} mm is below a 0.10 mm mask aperture floor")

    complaints = nfc_guard(board, mark)
    if complaints:
        for c in complaints:
            print(f"  NFC MARK ABORT: {c}")
        sys.exit("mask_art: refusing to write the NFC mark")
    b = mark.bounds
    print(f"  nfc mark: {len(mark.geoms) if mark.geom_type == 'MultiPolygon' else 1} wave(s), "
          f"{mark.area:.2f} mm² on F.Mask at x[{b[0]:.1f},{b[2]:.1f}] y[{b[1]:.1f},{b[3]:.1f}], "
          f"no live copper exposed")

    raw = BOARD.read_bytes()
    crlf = raw.count(b"\r\n")
    if crlf and crlf != raw.count(b"\n"):
        sys.exit("mask_art: mixed line endings in the board; refusing to touch it")
    nl = "\r\n" if crlf else "\n"
    txt = raw.decode("utf-8").replace("\r\n", "\n")
    stripped, had = strip_existing(txt)

    if args.check:
        have_n = had
        # compare the emitted block against what is actually in the file
        kept, _ = strip_existing(txt)
        want = _splice(kept, body)
        same = want.replace("\r\n", "\n") == txt.replace("\r\n", "\n")
        print(f"  board carries {have_n} generated shape(s); regenerated {body.count('(gr_poly')}")
        print("  MATCH" if same else "  DRIFT — the routing changed; re-run with --apply")
        return 0 if same else 1

    if args.apply:
        out = _splice(stripped, body)
        BOARD.write_bytes(out.replace("\n", nl).encode("utf-8"))
        print(f"  replaced {had} previous shape(s) with {body.count('(gr_poly')}; "
              f"wrote {BOARD.relative_to(ROOT)} ({nl!r} preserved)")
    else:
        print(f"  (report only — {had} generated shape(s) currently in the board; "
              f"pass --apply to write)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
