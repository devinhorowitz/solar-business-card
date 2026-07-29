#!/usr/bin/env python3
"""Single home for B-side component heights, in mm above the board's back face.

WHY THIS FILE EXISTS

The enclosure generators cut a clearance pocket per B-side part, and the pocket depth
is a pure function of the part's height. That number used to be hand-carried in three
places -- `part_height()` in the brace generator, `U7_H` in the backshell generator, and
prose in both DRAWING generators -- and they drifted, silently, in the direction that
prints an unusable part:

  * U7 was corrected from 1.75 (a SOIC-8 that the v4 rework replaced) to 0.90 (the
    MB85RC512TY DFN-8) on 2026-07-28 in the backshell generator and enclosure/README.md,
    and NOT in the brace generator. At 1.75 the brace's own arithmetic makes the pocket
    1.87 >= GAP-0.05, which turns it into a THROUGH-hole; at 0.90 it is a 1.02 mm blind
    pocket with a 0.78 mm resin ceiling. One stale constant, one hole through the part.

  * `part_height()` ended in a bare `return 0.60` for any refdes it did not recognise, so
    Q2 (a SOT-23, 1.20) and FB1 (an 0603 inductor, 0.80) were cut 0.48 and 0.08 mm too
    shallow -- no error, no warning, just interference at assembly.

  * The `R`/`C` prefix rule returned the 0402 height for EVERY passive, so the 0603 caps
    (C22, C23) were cut 0.13 short and the 0805s (C26, C27) 0.58 and 0.23 short.

None of that is catchable by eye: the failure is a number in one file disagreeing with a
number in another, and the generator runs happily either way. So the numbers live here,
once, and `scripts/check_consistency.py` check [7] measures them against the z-extent of
each part's own 3D model on the board. That check is the reason this file can be trusted:
it is not another copy of the truth, it is the copy the truth is verified against.

WHAT THE NUMBERS ARE

Body height above the back copper, datasheet MAX where a datasheet applies. They are
deliberately >= the modelled body: a pocket may be generous (it is air), never short.
"""

# ---- explicit, per refdes ---------------------------------------------------------
# Anything whose height is not simply "the default for its passive size" belongs here.
HEIGHTS = {
    "U1":  1.00,   # AVR64EA28 VQFN-28 4x4
    "U3":  0.87,   # ADXL367 CC-12-4 (ADI datasheet Rev.B: 2.2 x 2.3 x 0.87)
    "U5":  0.50,   # NT3H2211 XQFN-8
    "U6":  1.45,   # SOT-23-6 body, datasheet max -- see MODEL_NOTES below
    "U7":  0.90,   # MB85RC512TY FRAM DFN-8. WAS 1.75 here for a SOIC-8 that the v4
                   # rework removed; 1.75 cut this pocket clean through the brace.
    "U8":  0.90,   # AEM10300 QFN-28 4x4 (modelled 0.85)
    "U9":  1.45,   # TPS7A0233 SOT-23-6, same body as U6
    "L2":  1.00,   # Murata DFE252010F-100M, 2.5 x 2.0 x 1.0 -- see MODEL_NOTES
    "Q2":  1.20,   # SOT-23. Was falling through to the 0.60 default.
    "FB1": 0.80,   # 0603 ferrite bead. Was falling through to the 0.60 default.
    # Capacitors above 0402 -- the prefix rule below is the 0402 number and undershoots
    # these. Each is set to cover its modelled body with a little air.
    "C4":  0.90, "C13": 0.90, "C22": 0.90, "C23": 0.90, "C25": 0.90,   # 0603 (0.80)
    "C26": 1.25, "C27": 1.25,                                          # 0805 (1.25)
}

# ---- by refdes prefix -------------------------------------------------------------
PREFIX = {
    "D":  0.83,    # LA_P47F amber LEDs
    "SW": 0.80, "SB": 0.80, "SJ": 0.80,   # switch + solder-bridge blobs (budgeted)
    "J":  0.20, "JP": 0.20, "TC": 0.20, "TP": 0.20,   # bare pads / unpopulated headers
    "R":  0.55, "C":  0.55,   # 0402 default. Every larger R/C is explicit above, and
                              # check [7] catches a new one that is not.
}

# Parts deliberately outside the brace envelope entirely -- no brace pocket is cut for them.
SKIP = ("SC",)

# ...but the four WS17 supercaps are the TALLEST parts on the back, so while the brace
# steps around them, they are what sets the shell's cavity depth (cavity = SUPERCAP_H +
# air). The backshell generator and its 2D drawing both need this number, and it is a
# component height, so it lives here with the rest.
SUPERCAP_H = 1.70   # SS17 (SC1/SC3) and WS17 (SC2/SC4) are different lengths but the same
                    # 1.70 mm max thickness -- solar-glow-drh-design-notes.md line 219.

# ---- known generic-model overshoot ------------------------------------------------
# check [7] compares each height against its 3D model's z-extent and errors when the
# height is SHORT. These models are drawn taller than the part's datasheet maximum, so
# the datasheet wins and the check reports a note instead. Keep this list tiny and
# keep the reason concrete: it is the one place a "too short" verdict can be waived.
MODEL_NOTES = {
    "SOT-23-6.step": "KiCad's generic body measures 1.550; the SOT-23-6 datasheet max "
                     "is 1.45, which is what U6/U9 are set to. The brace adds AIR=0.12 "
                     "on top, so the pocket is 1.57 either way.",
    "L_1008_2520Metric.step":
                     "KiCad's generic 1008 body measures 1.200, but L2 is a Murata "
                     "DFE252010F-100M, and that family's part number is L x W x T -- "
                     "2520/10 = 2.5 x 2.0 x 1.0 mm max. The land is 1008/2520; the part "
                     "on it is 1.0 tall.",
}

# Largest amount a height may exceed its modelled body before check [7] calls it a
# mistake rather than deliberate air. The widest legitimate gap today is the 0402
# default over an 0402 resistor (0.55 vs 0.350 = 0.20); U7's stale SOIC-8 number
# overshot its DFN-8 body by 0.85. 0.35 sits cleanly between the two.
OVERSHOOT_MAX = 0.35


class UnknownPart(KeyError):
    """Raised for a refdes with no height. Deliberately fatal -- see module docstring."""


def part_height(ref):
    """Height in mm, or None for parts that are outside the enclosure envelope.

    Raises UnknownPart rather than guessing. The 0.60 default this replaces is what let
    Q2 and FB1 be cut too shallow with nothing said.
    """
    if ref in HEIGHTS:
        return HEIGHTS[ref]
    prefix = ref.rstrip("0123456789")
    if prefix in SKIP:
        return None
    if prefix in PREFIX:
        return PREFIX[prefix]
    raise UnknownPart(
        f"{ref}: no height in enclosure/part_heights.py. Add it to HEIGHTS (or to "
        f"PREFIX if the whole family shares one) -- do not let it default, that is how "
        f"Q2 and FB1 ended up with pockets 0.48 and 0.08 mm too shallow."
    )
