# Back-shell engraving studies

Fifteen ways to put the contact block into the titanium back, parked here so the reasoning
survives the conversation that produced it. **Nothing here ships.** The committed shell still
carries `MAKER_LINES` from `solar-glow-drh-v3_0-backshell-0p6b-brace-cad.py`; when one of
these is chosen it replaces that, and only then does it become part of the CAD chain.

```sh
python3 enclosure/engraving-studies/spin1_cutters.py        # which cutter
python3 enclosure/engraving-studies/spin2_composition.py    # which composition
python3 enclosure/engraving-studies/spin3_reeded.py         # after the fine reeding
# renders + numbers land in $ENGRAVE_OUT (default: $TMPDIR/engraving-studies)
```

They write **outside the repo on purpose.** Consistency check [9] requires every image a doc
displays to come from a generator CI runs, and CI does not run these — ten raytraced VTK
views is ~7 min for a decision aid, not an artifact. If one of these becomes the answer, its
render moves into the CAD chain and gets automated then, not before.

First run builds `shell_nomark.stl` (~2 min since the fine reeding; ~40 s with the coarse
fins), the real finned shell **without** its maker's
mark, because the committed mark sits at y 51.5/54.1 — inside the very band every study lays
type into.

## Why laser was rejected

A laser mark on bare Ti is an oxide film a few microns thick. It is a colour, not a feature:
it cannot be felt, and the first refinish takes it off. Everything here removes metal.

## The depth budget is fixed by the part, not by taste

The back field has 1.00 mm of floor under it. The fin fields already cut
`FIN_VALLEY = 0.60 mm` into it (deepened from 0.30 on 2026-07-30 after a depth-budget
analysis — the web is a waffle strip backed by the brace, not a membrane), so **0.40 mm is
already this part's thinnest section by design** — an engraving ≤ 0.60 mm deep adds no new
thin section and is free. That is the ceiling every variant respects, and it doubled when
the fins deepened. The spin 1/2 numbers were computed against the old 0.30 ceiling and
remain valid (they are all ≤ 0.30); **spin 3 spends the doubled ceiling** and re-asks the
two variants whose premises it moved. Depth is also well past "easily felt": a fingernail resolves a
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

## Spin 3 — the part changed underneath (2026-07-30), so the studies caught up

The fine-reeding rework moved `FIN_PITCH` 3.20 → 1.392 and `FIN_VALLEY` 0.30 → 0.60. That
killed G's premise (1.392 is below every cap in the block — `baseline_grid` at the live
pitch overlaps its own lines), doubled the ceiling H and F were priced against, and turned
the fins from stripes into a texture fine enough to *carry* information. Spin 3 is those
three consequences, prototyped. The reeding used in K/N is `fit_rules`' own pour re-closed
over the studies' panel — same rib, same groove floor, same Ø0.6 min-width opening, same
0.40 boss clearance around every island — and it closes at 18 rows, pitch 1.4053, 13 µm
off the fields' own. (One honesty note: an engraving only removes metal, so the band's ribs
sit at the field surface, 0.10 below the fin fields' proud tops; if a reeded variant ships,
the band joins the generator's CAD and can go proud to match.)

| | idea |
| --- | --- |
| **K** REEDED KNOCKOUT | DRH (cap 11, 2.35 mm strokes) left **flush in the pour**, wrapped at the 0.40 boss clearance exactly as the pour wraps a boss. The inverse of every other variant: the texture is the cut, the letters are the surface. 32 rib segments across 18 rows; the counters keep 20.8 mm² of live groove; grooves at the fields' own 0.60. |
| **L** TWO-DEPTH, RE-ASKED | H at the doubled budget — and the honest answer is the budget stopped binding: a Ø0.3 slotting Ti is rigid to ~1.5×D, so the name floor is **0.45** (three 0.15 passes), details 0.18. A 2.5× step, 0.27 mm of shoulder under a fingertip (H had 0.15). |
| **M** REGISTERED, FULL DEPTH | F's window relief with its floor at **0.60** — the fin valleys' own depth, standing on the same 0.40 web the whole part accepts. Unreachable stays 0.012 mm² (reach is set by the 0.2 tip, so depth costs no counter); the 15° taper leaves a 161 µm flare that reads as a chamfered window edge; letters keep 0.67 mm of flat crest on a 0.99 stroke. Four ~0.15 stepdowns. |
| **N** PLAQUE IN THE POUR | Reeding floods the band except a flush 31.8 × 17.1 plaque carrying the V-carved contact block — to the pour the plaque is just another pad. Its 2.2 mm side corridors sit a hair under rib + 2 grooves (2.21), so they carry clean valley channel instead of stub rows, which is what the pour does at a boss wrap. |
| **O** UNIT GRID | G re-founded: type takes **2 units** of the fine pitch (2.784 mm leading, 1.39× the email cap — tight, but set by the part, which was G's whole argument). Six rows at −5u…+5u from centre, the rule on the grid like any line. |

## Standing recommendation

**M.** It is F's registration argument — still the only fact-about-this-object in the set —
plus I's tooling, plus the depth the 2026-07-30 rework paid for: the glow window becomes a
real 0.60 recess you find with your thumb, standing on exactly the section the rest of the
part already accepts. If the back should instead read as **one texture**, N is the strongest
"designed, not placed" argument of the fifteen; K is its monogram-only reduction. **O**
replaces G as the purely typographic pick — G's grid no longer exists on the part.
