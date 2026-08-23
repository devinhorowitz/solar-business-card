#!/usr/bin/env python3
"""cap_clearance.py -- what actually stops a hand-placed supercap, measured from the board.

SC1-SC4 are the only hand-soldered parts on the B side, and `fit_rules` buys them
directional in-plane brace clearance (CLR_DATUM on the two shim-indexed edges,
CLR_FREE on the two that absorb the body tolerance). That number is a
DESIGN INPUT; this module measures the CONSEQUENCE -- how far each cap can actually
travel, and what it reaches when it does.

Two facts this exists to keep honest, both of which have already been published wrong:

  1. DNP FOOTPRINTS ARE NOT STOPS. J1 sits 0.49 mm off SC1's -X edge and reads like a
     hard stop on any plot, but it is bare pads on a standard build. Counting it halved
     SC1's published rotation limit (1.48 deg vs the real 3.13 deg into C11). The dnp
     set is read from the board's own `(attr ... dnp)`, never from a list here.

  2. TRAVEL IS A SWEEP, NOT A BOUNDING-BOX GAP. Both the cap and its neighbours are
     rectangles, so the two agree while everything stays axis-aligned -- and diverge
     silently the moment a neighbour is placed at an angle. This translates the real
     polygon and bisects on first contact.

The LEDGER below is the published set; `check()` re-derives it from the board and fails
on any disagreement, on a NEW neighbour that has come closer than the brace clearance,
and on a ledgered pair that has drifted apart. Same shape as the FRONT_SIDE snapshot:
a deliberate board move updates the ledger in the same commit.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "enclosure"))

DIRS = {"+X": (1.0, 0.0), "-X": (-1.0, 0.0), "+Y": (0.0, 1.0), "-Y": (0.0, -1.0)}
WINDOW = 2.5        # publish/gate every real neighbour within this far
TOL = 0.011         # mm; the ledger carries 2 decimals

# (cap, direction) -> (reference, travel_mm).  Absent means "nothing real within WINDOW".
LEDGER = {
    ("SC1", "+X"): ("C11", 0.70),
    ("SC1", "+Y"): ("C1", 0.92),
    ("SC2", "-X"): ("C6", 0.65),
    ("SC2", "+Y"): ("C8", 1.53),
    ("SC3", "+X"): ("C22", 2.20),
    ("SC3", "-X"): ("C24", 1.01),
    ("SC3", "-Y"): ("R15", 0.57),
    ("SC4", "-X"): ("L2", 0.50),
    ("SC4", "-Y"): ("R17", 1.98),
}

# Rotation about the cap centre, degrees to first contact with a real part.
ROT_LEDGER = {"SC1": ("C11", 3.13), "SC2": ("R5", 6.71),
              "SC3": ("C24", 3.00), "SC4": ("L2", 2.02)}


def dnp_refs(pcb=None):
    """The board's own DNP set. Read, never listed -- a part that stops being dnp
    becomes a stop, and this must notice without an edit here."""
    import board_parts
    txt = open(pcb or board_parts.PCB, encoding="utf-8", errors="replace").read()
    out = set()
    for b in board_parts._blocks(txt):
        if re.search(r"\(attr[^)]*\bdnp\b", b):
            m = re.search(r'\(property "Reference" "([^"]+)"', b)
            if m:
                out.add(m.group(1))
    return out


def _real_parts():
    import board_parts
    dnp = dnp_refs()
    return [(r, p) for r, p, _h, s in board_parts.parts("B")
            if not r.startswith("SC") and r not in dnp and s == "model"], dnp


def _caps():
    import board_parts
    return {r: p for r, p, _h, _s in board_parts.parts("B") if r.startswith("SC")}


def _first_contact(cap_poly, others, place, lim, coarse):
    """First contact scanning OUTWARD from zero, then bisected.

    Deliberately NOT "does it still overlap at the limit, then bisect": a rectangle
    swept past a small neighbour overlaps for an interval and is clear on both sides
    of it, so a limit-probe skips exactly the parts that are closest. That bug read
    SC3's rotation as 5.63 deg into U10 -- it had swept straight through C24 at 3.00.
    The coarse step must therefore be finer than the narrowest neighbour's own width.
    """
    from shapely.ops import unary_union
    union = unary_union([p for _r, p in others])
    n = int(lim / coarse) + 1
    prev = 0.0
    for i in range(1, n + 1):
        t = min(i * coarse, lim)
        if place(cap_poly, t).intersects(union):
            lo, hi = prev, t
            for _ in range(48):
                mid = (lo + hi) / 2
                if place(cap_poly, mid).intersects(union):
                    hi = mid
                else:
                    lo = mid
            moved = place(cap_poly, hi)
            who = [r for r, p in others if moved.intersects(p)]
            return (who[0] if who else "?", lo)
        prev = t
    return None


def travel(cap_poly, others, dx, dy, limit=None):
    """Distance the cap may translate along (dx,dy) before touching anything real."""
    from shapely import affinity
    lim = WINDOW if limit is None else limit
    return _first_contact(cap_poly, others,
                          lambda g, t: affinity.translate(g, xoff=dx * t, yoff=dy * t),
                          lim, 0.02)


def rotation(cap_poly, others, limit=8.0):
    """Degrees about the cap centroid to first contact, either sense."""
    from shapely import affinity
    c = cap_poly.centroid
    best = None
    for sgn in (1.0, -1.0):
        r = _first_contact(cap_poly, others,
                           lambda g, a, _s=sgn: affinity.rotate(g, _s * a, origin=c),
                           limit, 0.01)
        if r is not None and (best is None or r[1] < best[1]):
            best = r
    return best


def measure():
    caps = _caps()
    others, dnp = _real_parts()
    tr, rot = {}, {}
    for ref in sorted(caps):
        for dname, (dx, dy) in DIRS.items():
            h = travel(caps[ref], others, dx, dy)
            if h is not None:
                tr[(ref, dname)] = (h[0], round(h[1], 2))
        r = rotation(caps[ref], others)
        if r is not None:
            rot[ref] = (r[0], round(r[1], 2))
    return tr, rot, dnp


def check(verbose=True):
    import fit_rules as fr
    tr, rot, dnp = measure()
    bad = []

    for key in sorted(set(tr) | set(LEDGER)):
        got, want = tr.get(key), LEDGER.get(key)
        if got is None:
            bad.append(f"{key[0]} {key[1]}: ledger claims {want[0]} @ {want[1]:.2f} mm "
                       f"but nothing real is within {WINDOW} mm any more")
        elif want is None:
            bad.append(f"{key[0]} {key[1]}: {got[0]} has come within {got[1]:.2f} mm and is "
                       f"NOT ledgered -- a board move created a new cap neighbour")
        elif got[0] != want[0] or abs(got[1] - want[1]) > TOL:
            bad.append(f"{key[0]} {key[1]}: board says {got[0]} @ {got[1]:.2f} mm, "
                       f"ledger says {want[0]} @ {want[1]:.2f} mm")

    for ref in sorted(set(rot) | set(ROT_LEDGER)):
        got, want = rot.get(ref), ROT_LEDGER.get(ref)
        if got is None or want is None or got[0] != want[0] or abs(got[1] - want[1]) > TOL:
            bad.append(f"{ref} rotation: board says {got}, ledger says {want}")

    # The whole point of the exception: which directions has 0.75 outrun?
    # Per-EDGE since the bays went anisotropic (2026-08-23): "inside the bay" is a
    # question about ONE side, and comparing against the scalar worst case (clr_for, the
    # 0.75 free-side figure) would keep reporting the four datum-side parts as unguarded
    # long after CLR_DATUM started catching the cap before them.
    SIDE = {"+X": "E", "-X": "W", "+Y": "N", "-Y": "S"}
    exceeded = [(k, v) for k, v in sorted(LEDGER.items())
                if v[1] < fr.clr_sides(k[0])[SIDE[k[1]]]]
    if verbose:
        print(f"cap_clearance: {len(tr)} real neighbours within {WINDOW} mm; "
              f"{len(dnp)} dnp footprints excluded ({', '.join(sorted(dnp))})")
        for (ref, d), (who, mm) in sorted(LEDGER.items()):
            bay = fr.clr_sides(ref)[SIDE[d]]
            flag = ("  <-- INSIDE the bay, the part is the backstop" if mm < bay
                    else f"  (bay {bay:.2f}, resin catches the cap first)"
                    if ref in fr.CAP_DATUM else "")
            print(f"  {ref} {d}: {who} @ {mm:.2f} mm{flag}")
        for ref, (who, deg) in sorted(ROT_LEDGER.items()):
            print(f"  {ref} rotation: {who} @ {deg:.2f} deg")
        print(f"  {len(exceeded)} direction(s) where the brace bay outruns a real part")

    # Self-test: counting dnp parts MUST change the answer, or the exclusion is inert
    # and this gate would pass while silently reading phantom stops as real ones.
    import board_parts
    with_dnp = [(r, p) for r, p, _h, s in board_parts.parts("B")
                if not r.startswith("SC") and s in ("model", "pads")]
    caps = _caps()
    naive = travel(caps["SC1"], with_dnp, -1.0, 0.0)
    if naive is None or naive[0] not in dnp:
        bad.append("SELF-TEST: including dnp footprints no longer changes SC1 -X, so the "
                   "dnp exclusion is not being exercised -- the gate has gone inert")
    elif verbose:
        print(f"  self-test ok: with dnp included SC1 -X reads {naive[0]} @ "
              f"{naive[1]:.2f} mm (phantom); excluded, it is open")
    return bad


if __name__ == "__main__":
    problems = check()
    for b in problems:
        print(f"FAIL: {b}")
    print(f"cap_clearance: {len(problems)} problem(s)")
    sys.exit(1 if problems else 0)
