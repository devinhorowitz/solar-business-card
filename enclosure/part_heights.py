#!/usr/bin/env python3
"""Single home for B-side component heights, in mm above the board's back face.

HEIGHTS ARE BODY-ONLY: each is measured from the part's 3D model, which seats at zero
solder standoff. The real joint adds ~0.05-0.075 mm of paste collapse under every part.
That allowance lives ONCE, in fit_rules.AIR (sized for the full assembly tolerance
stack) -- do not add standoff to a height here, or it gets counted twice.

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
    # U6 moved SC-70-6 -> DSBGA-4 (YFP0004) on 2026-08-06 with the TPS22919 -> TPS22916C
    # ultrathin swap. 0.50 is TI SLVSDO5F's "DSBGA - 0.5 mm max height" INCLUDING balls
    # (4223507/A), and the model is ours (TI_DSBGA4_YFP via scripts/make_3d_models.py),
    # authored to that max -- declaration and model agree by construction, and check [7]
    # measures rather than tolerates this one. Was 1.10 (SC-70 DCK, SLVSEN5B).
    "U6":  0.50,   # DSBGA-4 (YFP0004), 0.5 max height incl. balls
    "U7":  0.90,   # MB85RC512TY FRAM DFN-8. WAS 1.75 here for a SOIC-8 that the v4
                   # rework removed; 1.75 cut this pocket clean through the brace.
    "U8":  0.90,   # AEM10300 QFN-28 4x4 (modelled 0.85)
    # U9 moved SOT-23-5 -> X2SON-4 (DQN) on 2026-08-05. 0.40 is TI SBVS277C package outline
    # DQN0004A (drawing 4215302/E), sheet titled "X2SON - 0.4 mm max height". The model is
    # ours, not KiCad's: the upstream footprint names a Package_SON.3dshapes STEP that does
    # not exist in kicad-packages3D, so U9 rendered with no body until scripts/make_3d_models.py
    # grew TI_X2SON4_DQN. At 0.40 U9 is now the SHORTEST B-side part on the board.
    "U9":  0.40,   # X2SON-4 (DQN), 0.4 max height
    "L2":  1.00,   # Murata DFE252010F-100M, 2.5 x 2.0 x 1.0 -- see MODEL_NOTES
    "Q2":  0.90,   # SOT-523 (DMG1012T-7, 0.90 max) -- 2026-08-06 low-profile respin; was
                   # 1.20 SOT-23, and before that falling through to the 0.60 default.
    "FB1": 0.80,   # 0603 ferrite bead. Was falling through to the 0.60 default.
    # Capacitors above 0402 -- the prefix rule below is the 0402 number and undershoots
    # these. Each is set to cover its modelled body with a little air.
    "C4":  0.90, "C13": 0.90, "C22": 0.90, "C23": 0.90,                # 0603 (0.80)
    # C25 re-picked 2026-07-30 (audit #2) to an 0805/16V part (TDK C2012X5R1C226M125AC)
    # because the 0603/10V one derated under the AEM's CSRC minimum. The land sync landed
    # 2026-07-30 (87f7af1, moved to x 25.875 -- every neighbour gap >=0.525); this entry
    # flipped 0.90 -> 1.25 in the same change, the sequencing C9 established: check [7]
    # measures this number against the model on the board, so the height had to wait for
    # the 0805 body to actually be there.
    #
    # CORRECTED 1.25 -> 1.45 on 2026-08-05. TDK's thickness code is the NOMINAL, not the
    # maximum: C2012X5R1C226M***125***AC is T = 1.25 +/-0.20, so the MAX is 1.45. Verified
    # against TDK's own dimension table and DigiKey's "Thickness (Max) 0.057in (1.45mm)",
    # and cross-checked against the convention -- the 085-code part reads 1.00 max, i.e.
    # 0.85 nominal +0.15. "125" never meant 1.25 max. The old comment said "1.25 max" and
    # was simply wrong.
    #
    # It caused no interference: SPAN_LIMIT is 1.180, so C25 is a THROUGH hole in the
    # brace at both values and there is no pocket ceiling to hit. What it broke was the
    # ARITHMETIC -- C25 belongs on the 1.45 wall beside C26/C27, not in the 1.25 tier, so
    # every thinning estimate that treated it as 1.25 was 0.20 mm optimistic.
    #
    # WHY CHECK [7] CANNOT SEE THIS CLASS, which is the part worth keeping: check [7]
    # compares the DECLARED height against the part's 3D MODEL, and C25 resolves to
    # KiCad's generic C_0805_2012Metric (body 1.25). Declared 1.25 against a 1.25 model is
    # an exact match and passes green forever. NOTHING compares the model against the
    # datasheet. C26/C27 escaped only by luck -- they are declared 1.45 against the same
    # 1.25 model, an overshoot the check permits. The gap class is: a part whose datasheet
    # max EXCEEDS its generic package model, declared at the model's height.
    # C25-C27 moved to the low-profile 1206 Murata GRM319 on 2026-08-06 (0.85 +/-0.10 ->
    # 0.95 MAX) -- the case-size escape from the 1.45 wall, on the room the SB/R12 deletion
    # made. DRH placed the stock HandSolder land; the repo footprint
    # (solarglow:C_1206_3216Metric_HS_LP085) is that land verbatim with the model swapped to
    # MURATA_GRM319_1206LP.step at the 0.95 max, so declaration and model agree exactly and
    # check [7] measures rather than tolerates these. Flipped 1.45 -> 0.95 in the same round
    # the bodies landed on the board -- the C9/C25 sequencing rule, both halves this time.
    "C25": 0.95,                                          # 1206 LP, GRM319 0.85 +/-0.10 -> 0.95 max
    "RN1": 0.45,   # EXB-28V151JX 4x150R ballast array (catalog T 0.35+/-0.10 -> 0.45 MAX;
                   # DigiKey seated-height max agrees. 0.15 under the lite 0.60 span limit.
                   # Replaced R1-R4, 2026-08-07)
    "RN2": 0.45,   # EXB-24V472JX 2x4.7k I2C pull-up array, same EXB catalog T 0.35+/-0.10
                   # -> 0.45 MAX. Replaced R10/R11, 2026-08-08
    # C26/C27: same 2026-08-06 move as C25 above (were Samsung 0805 X7R at 1.40/1.45).
    "C26": 0.95, "C27": 0.95,                             # 1206 LP, GRM319 0.85 +/-0.10 -> 0.95 max
    # C9, the NFC tank trim: 0402 -> 0805 (2026-07-30, hand-rework and Q) -> 0603
    # (2026-08-06 low-profile respin, Johanson QSCP251Q470G1GV001T S-series High-Q,
    # 0.89 max -> 0.90 declared). The 0805 era declared the generic model's 1.25 because
    # the part's own max (1.17) sat UNDER the model and would fail check [7]; the 0603
    # flips that -- part max 0.89 over the generic C_0603_1608Metric body (0.80), the
    # C26/C27-style overshoot the check permits, so the DATASHEET number wins. (The
    # original sin, for the record: before any entry existed C9 fell through the "C"
    # prefix default of 0.55 and the check said "interferes with the part by 0.70 mm".)
    "C9":  0.90,                                                       # 0603, QSCP 0.89 max
}

# ---- by refdes prefix -------------------------------------------------------------
PREFIX = {
    "D":  0.83,    # LA_P47F amber LEDs
    "SW": 0.80, "SJ": 0.80,   # switch + solder-bridge blobs (budgeted; SB1-4 deleted 2026-08-05)
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

# The LITE/AIR enclosure variants (2026-08-07) substitute thin supercaps. PROVISIONAL:
# 1.00 is DRH's working number for a part not yet chosen -- no MPN, no datasheet, so
# unlike every other figure in this file it is NOT verified against a source, and
# check [7] cannot measure it (SC is in SKIP; the one committed board carries the 1.70
# cans). When the MPN lands: verify the max thickness from its datasheet, replace this
# number, and the variant cavities re-derive from it (fit_rules.VARIANTS) -- one edit.
# The pogo testplate deliberately does NOT read this: it pins to SUPERCAP_H (the max
# build) so the bench fixture always clears the tallest caps it could meet.
SUPERCAP_H_THIN = 1.00   # PROVISIONAL -- thin-cap MPN pending (TODO.md carries the item)

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
    # "TC1/b"-style MIRROR refs (since 2026-08-01 the TC2030 land is double-sided; the /b
    # is the B-side twin of an existing land). Height-wise a mirror IS its family: strip
    # the /suffix so "TC1/b" resolves through the same "TC" rule as TC1, instead of
    # raising. This is the documented mirror grammar only -- an entirely new family still
    # has no path around the raise below.
    prefix = ref.split("/", 1)[0].rstrip("0123456789")
    if prefix in SKIP:
        return None
    if prefix in PREFIX:
        return PREFIX[prefix]
    raise UnknownPart(
        f"{ref}: no height in enclosure/part_heights.py. Add it to HEIGHTS (or to "
        f"PREFIX if the whole family shares one) -- do not let it default, that is how "
        f"Q2 and FB1 ended up with pockets 0.48 and 0.08 mm too shallow."
    )
