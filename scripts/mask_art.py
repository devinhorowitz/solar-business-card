#!/usr/bin/env python3
"""Generate the front "negative routing" cartouche — the ornament IS the wiring.

    python3 scripts/mask_art.py              # report only, touch nothing
    python3 scripts/mask_art.py --apply      # write the art into the board
    python3 scripts/mask_art.py --check      # does the board match current routing?

WHAT IT DRAWS

A cartouche in the left mid-field with the soldermask opened everywhere the copper
underneath is GND, and left in place everywhere a live signal runs. The GND pour
plates gold and reads as a fine mesh (that pour is a CROSSHATCH, so the texture is
inherent, not a choice); the twelve signal nets stay under black mask and read as
dark rivers. The pattern is not drawn — it is the actual circuit, in negative.

WHY IT IS GENERATED AND NOT DRAWN

That field carries ~278 mm of live front routing on twelve nets. Two things follow,
and they are what rule out every ordinary approach:

  * NEW SOLID COPPER would short across those nets, so gold artwork cannot simply be
    added there.
  * A PLAIN MASK WINDOW would expose live signal traces on the show face of a card
    that lives in a wallet. Only GND may be laid bare.

So the opening is computed as (cartouche - live copper), which also means the art
tracks the routing: re-route, re-run, and the ornament is correct again. That is why
check_consistency has a gate for it — art drawn once and left behind would go quietly
wrong the first time a trace moved, and the whole point of this ornament is that it
tells the truth about the board.

MANUFACTURING

Opening edges stand off live copper by KEEP (0.18 mm), so the black rivers are at
least trace + 2 x 0.18 wide — comfortably above any soldermask dam floor. The number
that needs watching is the other one: small gold apertures pinched between two nearby
rivers. --report measures both and prints the worst case.
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



# --- the NFC coil, exposed on the back -------------------------------------------
# The 7-turn antenna is etched copper on B.Cu and was sitting under black soldermask,
# so the finished card never showed it: 81 segments of real spiral, invisible. The
# front's whole argument is that the ornament IS the wiring; the back had 639 apertures
# on F.Mask and exactly one on B.Mask -- the glow window -- and nothing over the coil.
#
# Opening the mask over LA/LB plates the spiral in ENIG and reads as gold on black. Like
# the cartouche it is COMPUTED from the copper, so a re-route or a retune moves the art
# with it rather than leaving a drawing behind.
#
# ONLY LA/LB. Every other B.Cu net stays under mask -- verified below, not assumed,
# because this is the face that sits against a GROUNDED titanium shell and the lip
# already landed on live pad once in this project's history.
COIL_NETS = ("LA", "LB")
COIL_EXPANSION = 0.05        # aperture grown off the copper edge


def coil_aperture(board):
    """Union of the LA/LB back copper, grown by the mask expansion."""
    from shapely.geometry import Point, LineString
    from shapely.ops import unary_union
    IU = 1e6
    bcu = board.GetLayerID("B.Cu")
    parts = []
    for t in board.GetTracks():
        if not t.IsOnLayer(bcu) or t.GetNetname() not in COIL_NETS:
            continue
        s, e = t.GetStart(), t.GetEnd()
        try:
            r = t.GetWidth() / IU / 2.0 + COIL_EXPANSION
        except Exception:
            continue
        a, b = (s.x / IU, s.y / IU), (e.x / IU, e.y / IU)
        parts.append(Point(a).buffer(r) if a == b else
                     LineString([a, b]).buffer(r, cap_style=2))
    if not parts:
        return None
    return unary_union(parts)


def coil_guard(board, ap):
    """Refuse to expose anything that is not the antenna, or anything the grounded Ti
    shell reaches. Returns a list of complaints; empty means safe."""
    from shapely.geometry import box, Point
    IU = 1e6
    bad = []
    bcu = board.GetLayerID("B.Cu")
    for t in board.GetTracks():
        if not t.IsOnLayer(bcu) or t.GetNetname() in COIL_NETS:
            continue
        s, e = t.GetStart(), t.GetEnd()
        from shapely.geometry import LineString, Point as P
        a, b = (s.x / IU, s.y / IU), (e.x / IU, e.y / IU)
        g = P(a).buffer(0.05) if a == b else LineString([a, b]).buffer(0.05)
        if g.intersects(ap):
            bad.append(f"aperture would expose net {t.GetNetname()!r} on B.Cu")
            break
    sys.path.insert(0, str(ROOT / "enclosure"))
    try:
        import fit_rules as fr
        if fr.lip_poly().intersects(ap):
            bad.append("aperture is under the grounded Ti support lip")
        for m in fr.MOUNTS:
            if Point(m).buffer(fr.BOSS_R).intersects(ap):
                bad.append(f"aperture is under the Ti boss annulus at {m}")
                break
    except Exception as exc:
        bad.append(f"could not check the shell against it: {exc}")
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
    """-> (body, cartouche, coil). THE one definition of what this generator writes.

    main() and check_consistency [6] both call this. They used not to: the check rebuilt only
    `emit(build(board))` and compared that against the whole file, which was a second, quieter
    copy of "what the generator emits". It agreed with reality exactly as long as the generator
    owned one thing -- and reported the board STALE the moment the coil aperture made it two,
    while `mask_art --check` on the same board said MATCH. One home instead.
    """
    art = build(board)
    coil = coil_aperture(board)
    if coil is None:
        raise SystemExit("mask_art: no LA/LB copper on B.Cu -- the coil IS the art, so this is fatal")
    return emit(art) + emit(coil, layer="B.Mask", tag=f"{TAG}-coil"), art, coil


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
    art = build(board)
    r = report(art)
    print(f"  cartouche: {r['pieces']} piece(s), {r['area']:.1f} mm² of gold, "
          f"narrowest gold aperture {r['min_aperture']:.3f} mm")
    if r["min_aperture"] < 0.10:
        print(f"  WARNING: {r['min_aperture']:.3f} mm is below a 0.10 mm mask aperture floor")

    body, art2, coil = generate(board)
    complaints = coil_guard(board, coil)
    if complaints:
        for c in complaints:
            print(f"  COIL ABORT: {c}")
        sys.exit("mask_art: refusing to expose the coil")
    print(f"  nfc coil: {len(coil.geoms) if coil.geom_type == 'MultiPolygon' else 1} piece(s), "
          f"{coil.area:.1f} mm² of gold on B.Mask, nothing but {'/'.join(COIL_NETS)} exposed")

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
