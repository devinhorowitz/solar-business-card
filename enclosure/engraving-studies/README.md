# Back-shell engraving studies

Ten ways to put the contact block into the titanium back, parked here so the reasoning
survives the conversation that produced it. **Nothing here ships.** The committed shell still
carries `MAKER_LINES` from `solar-glow-drh-v3_0-backshell-0p6b-brace-cad.py`; when one of
these is chosen it replaces that, and only then does it become part of the CAD chain.

```sh
python3 enclosure/engraving-studies/spin1_cutters.py        # which cutter
python3 enclosure/engraving-studies/spin2_composition.py    # which composition
# renders + numbers land in $ENGRAVE_OUT (default: $TMPDIR/engraving-studies)
```

They write **outside the repo on purpose.** Consistency check [9] requires every image a doc
displays to come from a generator CI runs, and CI does not run these — ten raytraced VTK
views is ~7 min for a decision aid, not an artifact. If one of these becomes the answer, its
render moves into the CAD chain and gets automated then, not before.

First run builds `shell_nomark.stl` (~40 s), the real finned shell **without** its maker's
mark, because the committed mark sits at y 51.5/54.1 — inside the very band every study lays
type into.

## Why laser was rejected

A laser mark on bare Ti is an oxide film a few microns thick. It is a colour, not a feature:
it cannot be felt, and the first refinish takes it off. Everything here removes metal.

## The depth budget is fixed by the part, not by taste

The back field has 1.00 mm of floor under it. The fin fields already cut
`FIN_VALLEY = 0.30 mm` into it, so **0.70 mm is already this part's thinnest section by
design** — an engraving ≤ 0.30 mm deep adds no new thin section and is free. That is the
ceiling every variant respects. It is also well past "easily felt": a fingernail resolves a
0.05 mm step, and refinishing (bead blast, brush, stonewash) removes order 0.01 mm, so a
0.25 mm cut survives many refinishes.

All type sits in the clear band the two fin fields leave open (`fit_rules.fin_band()` →
y 27.25–61.65) inside `ART = (6.0, 30.8, 44.8, 58.1)`, which is bounded by that band in y and
by the four in-band M2 boss annuli (x = 3.0 / 47.8, r 2.6) in x. A block that escapes it
raises rather than silently overlapping a boss.

## What is actually modelled

Each variant is the **depth field a real cutter would leave**, sampled at 25 µm and rendered
as true 3D on the real shell STL — not a drawing of one.

| tool | model |
| --- | --- |
| V-carve | cone of included angle A, flat tip t: a point s from the nearest stroke edge is cut to `z = (s − t/2) / tan(A/2)`, capped. Thin strokes come out **shallower** — that is what v-carving is, so the tables quote achieved depth per line. |
| Flat pocket | a square-nosed mill of radius r removes exactly the morphological opening `(shape ⊖ r) ⊕ r`. Corners take the tool radius; a stroke narrower than 2r is **not cut at all**. |
| Relief | the same opening applied to the **negative** space. The limit becomes the counter of an `a`, not the width of a stem, and whatever the tool cannot reach stays as proud metal webbing the letters. Measured and reported. |
| Tapered | reach at the floor set by the **tip** radius; the taper is what makes a 0.2 mm tip rigid enough for Ti, and it leaves a 67 µm flare at each letter base. |

The two orientation transforms both matter and are both already proven on the shipped maker's
mark: flip Y per line (font outlines are Y-up, board space is Y-down — drop them in raw and
every letter engraves upside down while the word order stays right; the tell is V as a lambda
and W as an M), then mirror X about the board centreline so it reads once the card is turned
over.

## Spin 1 — which cutter

| | tool | depth | note |
| --- | --- | --- | --- |
| **A** V-CARVE | 60° V-bit, 0.10 mm tip | 0.25 max | cheapest, most forgiving in Ti. Depth varies by line: 0.250 on the name, 0.130 on "Atlanta, Georgia" (0.250 mm stroke). |
| **B** FLAT POCKET | Ø0.3 square end mill | 0.30 flat | hardest shoulder, deepest shadow. **The tool picks the type**: Ø0.4 left 18.9 mm² of the e-mail line uncut, so it went to Ø0.3 and everything went bold and larger; the title and city had to go. |
| **C** RELIEF | Ø0.3 end mill | field −0.25 | letters left standing, keeping the bead-blast finish while the floor comes out bright. Two textures, no coating. 3.545 mm² of unreachable metal webs the letters. |
| **D** PLAQUE | panel Ø1.0 + 60° V | 0.12 + 0.18 | two levels; text 0.30 below the field and 0.45 below the border. |
| **E** MONOGRAM | Ø1.0 rough + 60° chamfer | 0.30 | DRH at cap 11 (2.35 mm strokes) — a flat-bottomed pocket with a chamfered edge, not a groove. Restraint: the front already carries the block. |

## Spin 2 — composition, hierarchy, registration

| | idea |
| --- | --- |
| **F** REGISTERED | DRH in relief inside **exactly** the front's glow-window footprint, `GLOW_WIN (14.95, 40.8)–(35.85, 47.0)` straight out of the generator. Not a copy of the front monogram — the same rectangle. It is centred on x = W/2, so the machining mirror maps it onto itself and the registration is exact rather than fitted. 0.012 mm² unreachable. |
| **G** FIN RHYTHM | left-aligned, every baseline on `FIN_PITCH = 3.20 mm`. The leading is inherited from the ribs above and below, so the back is one grid instead of a striped area and a text area. The rule had to widen 0.30 → 0.55 mm: a 60° bit bottoms out in a 0.30 groove at 0.173 mm and it read shallower than the type beside it. |
| **H** TWO-DEPTH | name flat-pocketed 0.30 with a square shoulder, everything under it a 0.15 mm groove. The only variant that spends the depth budget as a design axis rather than uniformly. |
| **I** RELIEF / TAPER | C with the tool it should have had. Webs **3.545 → 0.969 mm²**, widest blob 0.255 → 0.158 mm — 73% less. |
| **J** FRAMED | a 0.28 mm groove frame echoing the show face's perimeter frame; frame and text are the same bit at the same depth, one setup. The name at cap 3.00 ran 0.6 mm **through** the frame on the first pass — it is 2.85 now and the script asserts the clearance (1.50 mm) rather than leaving it to the eye. |

## Standing recommendation

**F for the concept, I's tooling for the cut.** The registration argument is the only one here
that is a fact about this object rather than a preference, and it costs nothing to build.
**G** is the pick if the back should stay purely typographic.
