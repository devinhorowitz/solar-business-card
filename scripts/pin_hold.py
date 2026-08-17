#!/usr/bin/env python3
"""Re-derive a HELD pin's justification from upstream, on every sweep.

WHY THIS EXISTS. `weekly-freshness.yml` lets a pin sit deliberately below latest by
carrying a `# HELD` marker, so a known-intentional gap reports as "held on purpose"
instead of drifting red forever and training the reader to skip the row. That much
was right. What was missing is that the marker was UNCONDITIONAL: it suppressed the
drift verdict whether or not the thing that justified it still existed.

It cost exactly what you would expect. `numpy` was held at 2.4.6 because numba
0.66.0 declares `numpy<2.5`. numba 0.67.0 shipped with `numpy<2.6` -- the ceiling
was lifted upstream -- and the sweep went on printing "held on purpose" every
Monday, because a hold never re-checks its own reason. A silence that cannot expire
is indistinguishable from a silence that should have.

So a hold now NAMES ITS BLOCKER (`# HELD <pkg> BY <blocker>: <reason>`) and this
script re-reads the blocker's live dependency metadata each run and re-decides:

    HELD     the blocker still excludes the latest <pkg> -- the hold is earned
    EXPIRED  the blocker now ALLOWS it -- drop the marker and bump
    UNKNOWN  could not tell: probe failed, unparseable spec, no blocker named, or the
             blocker constrains <pkg> ONLY behind an extras marker. That last one is a
             judgement call made deliberately rather than by omission -- an extras-gated
             requirement does not apply to a plain install, but this script cannot know
             which extras the workflow installs, so calling it EXPIRED would be a guess.
             UNKNOWN says "this hold could not be verified", which is the true statement.

UNKNOWN is deliberately NOT "held". The whole failure mode here is silence read as
safety, so anything this script cannot prove reports as a question, and the sweep
counts it among the probe failures its banner hoists to the top of the issue.

A hold with no `BY <blocker>` is unauditable BY CONSTRUCTION -- the same finding the
action loop already raises for a SHA pinned with no `# vN` comment to check it
against -- and is reported as such rather than honoured.

Version handling is deliberately narrow: plain dotted releases only. Every pin in
this tree is `X.Y.Z`, and a parser that guesses at epochs, wildcards and
pre-releases would be a second silent-failure surface in a script written to close
one. Anything it cannot parse is UNKNOWN, loudly.

    python3 scripts/pin_hold.py --check numpy 2.5.2 numba
    python3 scripts/pin_hold.py --self-test
"""

import json
import re
import sys
import urllib.request

PYPI = "https://pypi.org/pypi/{}/json"
TIMEOUT = 20

# One clause of a specifier: an operator and a version, e.g. "<2.6" or ">=1.22".
_CLAUSE = re.compile(r"^(<=|>=|==|!=|~=|<|>)\s*([^,\s]+)$")
# A plain dotted release and nothing else. Letters (rc/dev/a/b/post), epochs and
# wildcards all fail here on purpose -- see the module docstring.
_PLAIN = re.compile(r"^\d+(?:\.\d+)*$")


def release_tuple(version):
    """'2.5.2' -> (2, 5, 2). Anything not a plain dotted release -> None."""
    if not _PLAIN.match(version or ""):
        return None
    return tuple(int(p) for p in version.split("."))


def _cmp(a, b):
    """Compare release tuples, zero-padding so 2.5 == 2.5.0."""
    n = max(len(a), len(b))
    a = a + (0,) * (n - len(a))
    b = b + (0,) * (n - len(b))
    return (a > b) - (a < b)


def satisfies(version, spec):
    """Does `version` satisfy every clause of `spec` ('<2.6,>=1.22')?

    Returns True / False, or None when any part is outside the narrow grammar --
    never a guess.
    """
    v = release_tuple(version)
    if v is None:
        return None
    for clause in (c.strip() for c in (spec or "").split(",")):
        if not clause:
            continue
        m = _CLAUSE.match(clause)
        if not m:
            return None
        op, bound_s = m.group(1), m.group(2)
        if op == "~=":            # compatible-release: correct handling needs the
            return None           # clause's own precision; not worth guessing here
        bound = release_tuple(bound_s)
        if bound is None:
            return None
        c = _cmp(v, bound)
        ok = {
            "<":  c < 0,
            "<=": c <= 0,
            ">":  c > 0,
            ">=": c >= 0,
            "==": c == 0,
            "!=": c != 0,
        }[op]
        if not ok:
            return False
    return True


def blocker_constraint(blocker, pkg, _fetch=None):
    """Latest `blocker` version and its unconditional requirement on `pkg`.

    Returns (blocker_version, spec) or (None, reason). Requirements carrying an
    environment marker (`; extra == "x"`) are skipped: they do not apply to a plain
    install, and honouring one would overstate the constraint.
    """
    try:
        fetch = _fetch or (lambda u: urllib.request.urlopen(u, timeout=TIMEOUT).read())
        data = json.loads(fetch(PYPI.format(blocker)))
    except Exception as exc:                       # noqa: BLE001 - probes report, never abort
        return None, f"could not reach PyPI for {blocker} ({type(exc).__name__})"

    version = data.get("info", {}).get("version")
    reqs = data.get("info", {}).get("requires_dist") or []
    target = pkg.lower().replace("_", "-")
    for req in reqs:
        if ";" in req:                             # environment-marked: not unconditional
            continue
        m = re.match(r"^\s*([A-Za-z0-9._-]+)\s*(\[[^\]]*\])?\s*(.*)$", req)
        if not m:
            continue
        if m.group(1).lower().replace("_", "-") != target:
            continue
        return version, m.group(3).strip()
    return None, f"{blocker} {version} declares no unconditional requirement on {pkg}"


def check(pkg, latest, blocker, _fetch=None):
    """-> (verdict, detail). verdict is HELD | EXPIRED | UNKNOWN."""
    version, spec = blocker_constraint(blocker, pkg, _fetch=_fetch)
    if version is None:
        return "UNKNOWN", spec
    if not spec:
        return "EXPIRED", f"{blocker} {version} no longer constrains {pkg} at all"
    ok = satisfies(latest, spec)
    if ok is None:
        return "UNKNOWN", f"cannot evaluate {blocker} {version} requirement `{pkg}{spec}`"
    if ok:
        return "EXPIRED", f"{blocker} {version} now allows {pkg} {latest} (`{spec}`)"
    return "HELD", f"{blocker} {version} needs `{pkg}{spec}`, which excludes {latest}"


# --------------------------------------------------------------------------------
# Self-test. The classifier is the part that can rot quietly, so it is exercised
# against the two REAL historical states of this very hold on every run -- the same
# shape as check [20]'s ledger, which re-classifies both of its historical failures
# each time and fails if either stops going red. Fixtures are literal metadata, not
# network calls: this tests the comparison logic, and the network path already has
# the sweep's probe-failure banner watching it.
# --------------------------------------------------------------------------------
_FIXTURES = [
    # (name, blocker_version, requires_dist, pkg, latest, expected verdict)
    ("numba 0.66.0 excluded numpy 2.5.2",
     "0.66.0", ["llvmlite<0.44,>=0.43.0dev0", "numpy<2.5,>=1.22"], "numpy", "2.5.2", "HELD"),
    ("numba 0.67.0 allows numpy 2.5.2",
     "0.67.0", ["llvmlite<0.50,>=0.49.0dev0", "numpy<2.6,>=1.22"], "numpy", "2.5.2", "EXPIRED"),
    # An extras-gated requirement is NOT honoured as a hold, but is not cleared either:
    # this script cannot see which extras the workflow installs. See the docstring.
    ("an extras-gated requirement is a question, not a hold and not a clearance",
     "1.0.0", ['numpy<2.5; extra == "fast"'], "numpy", "2.5.2", "UNKNOWN"),
    ("an unparseable specifier is a question, not a hold",
     "1.0.0", ["numpy==2.*"], "numpy", "2.5.2", "UNKNOWN"),
]


def self_test():
    failures = []
    for name, ver, reqs, pkg, latest, expected in _FIXTURES:
        payload = json.dumps({"info": {"version": ver, "requires_dist": reqs}}).encode()
        verdict, detail = check(pkg, latest, "fixture", _fetch=lambda _u, p=payload: p)
        if verdict != expected:
            failures.append(f"{name}: expected {expected}, got {verdict} ({detail})")

    # Direct comparator cases the fixtures above do not reach.
    for version, spec, expected in [
        ("2.5.2", "<2.6,>=1.22", True),
        ("2.5.2", "<2.5,>=1.22", False),
        ("2.5", "<2.5.0", False),          # zero-padding: 2.5 == 2.5.0
        ("2.5", "<=2.5.0", True),
        ("2.5.2", "~=2.5", None),          # compatible-release: refused, not guessed
        ("2.5.2rc1", "<2.6", None),        # pre-release: refused
    ]:
        got = satisfies(version, spec)
        if got is not expected:
            failures.append(f"satisfies({version!r}, {spec!r}): expected {expected}, got {got}")

    for f in failures:
        print(f"FAIL: {f}")
    if failures:
        print(f"pin_hold self-test: {len(failures)} failure(s)")
        return 1
    print(f"pin_hold self-test: ok ({len(_FIXTURES)} fixtures + 6 comparator cases)")
    return 0


def main(argv):
    if len(argv) == 2 and argv[1] == "--self-test":
        return self_test()
    if len(argv) == 5 and argv[1] == "--check":
        verdict, detail = check(argv[2], argv[3], argv[4])
        print(f"{verdict}\t{detail}")
        return 0                      # probes report, never abort (see weekly-freshness.yml)
    print(__doc__.strip().splitlines()[-3].strip(), file=sys.stderr)
    print("usage: pin_hold.py --check <pkg> <latest> <blocker> | --self-test", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
