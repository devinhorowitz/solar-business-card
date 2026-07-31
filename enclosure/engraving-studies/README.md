# Back-shell engraving studies

Twenty-five ways to mark the titanium back, parked here so the reasoning survives the
conversation that produced it. **Nothing here ships.** The committed shell still
carries `MAKER_LINES` from `solar-glow-drh-v3_0-backshell-0p6b-brace-cad.py`; when one of
these is chosen it replaces that, and only then does it become part of the CAD chain.

```sh
python3 enclosure/engraving-studies/spin1_cutters.py        # which cutter
python3 enclosure/engraving-studies/spin2_composition.py    # which composition
python3 enclosure/engraving-studies/spin3_reeded.py         # after the fine reeding
python3 enclosure/engraving-studies/spin4_provenance.py     # what the back SAYS
python3 enclosure/engraving-studies/spin5_t_relief.py       # T's ring, set in relief
python3 enclosure/engraving-studies/spin6_finish.py         # the single-finish reality
python3 enclosure/engraving-studies/spin7_lapped.py         # blast + home-lapped crests
python3 enclosure/engraving-studies/spin8_plane.py          # the gameplan: bearing plane
python3 enclosure/engraving-studies/spin9_words.py          # Z's words
python3 enclosure/engraving-studies/spin10_material.py      # the material, named
python3 enclosure/engraving-studies/all_studies.py          # every variant on one sheet
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

## Spin 4 — provenance: what the back says

Spins 1–3 all engraved the contact block; spin 4 asks about the *other* candidate content —
what a maker puts on a caseback: what powers it, what it speaks, which revision, which
unit, which year. Content is orthogonal to technique (any of these cuts with any spin-1
cutter at any spin-3 depth), and the facts are pulled from the part where possible: the
contactless waves in R are `scripts/mask_art.py`'s own glyph, imported, so front mask and
back engraving carry the same mark from the same generator. Serial numbers are **variable
data** — `Nº 001` is one text substitution per unit in the cut file; every other stroke is
shared across the run.

| | idea |
| --- | --- |
| **P** CASEBACK | the watch idiom: a centred epitaph. `SOLAR-GLOW · DRH / INDOOR SOLAR · 1 F 5.5 V / NFC 13.56 MHz · TAP TO WAKE / REV 4.0 · Nº 001 · MMXXVI / ATLANTA, GEORGIA` — six facts, one V-bit, no ornament. |
| **Q** SPEC PLATE | the industrial idiom: a 28.8 × 18.6 data plate, MODEL / REV / SER / PWR / RF / YEAR label-value rows. Frame, rules and type are the same 60° bit in one setup — J's economy, different words. |
| **R** MARKS | the icon idiom: a sun beside the front mask's own contactless waves (imported, not redrawn), two short lines under. Says solar + NFC with no sentence; language-independent at arm's length. |
| **S** PROVENANCE LINE | restraint: the committed `MAKER_LINES` slot, caps and bold name kept verbatim — only "DESIGNED & MADE BY" swaps for `SOLAR POWERED · NFC · Nº 001 · MMXXVI`. A one-list edit in the shell generator, cuttable today. |
| **T** RING | the caseback ring: 41 characters into 360° (tracking **derived**, the ring closes exactly — the fins' own move) around a serial-number centre. The unit number holds the middle of the dial like a watch serial. |

## Spin 5 — T's ring, set in relief

T v-carved the ring; spin 5 leaves the letters standing while the metal around them comes
out — relief is where the studies keep converging (C → I → M), cut with I's tapered Ø0.2
tool. Two honest readings, built side by side:

| | idea |
| --- | --- |
| **U** RING RELIEF / MEDALLION | one Ø25.7 disc down 0.25 over ~453 mm²; rim shoulder, ring text, a Ø18.0–18.5 separator hoop and the serial stack all stand from **one floor**. The whole medallion is a coin; crests keep the bead-blast while the floor mills bright — C's two-texture contrast. |
| **V** RING RELIEF / SUNKEN BAND | the watch answer: raised lettering in a sunken band (Ø18.3–25.1) and a sunken dial (Ø17.3), with the rings between them **flush** — not features, just the metal the pockets didn't take. No free-standing thin feature anywhere; the kindest relief geometry to machine and refinish. |

**The depth is 0.25 and the ring's own geometry says so.** The taper flares
depth × tan 15° into every standing edge; at cap 1.80 the ring letters stand 0.63 mm
apart, and at 0.60 deep the two facing flares take 0.32 of that — the letters fuse at the
base. At 0.25 they take 0.13 and the gaps survive. The doubled budget is real, but
cap-1.8 relief cannot spend it (M spends it at cap 4.4, where the flare is noise).
Webs the Ø0.2 tip cannot clear: 1.39 mm², widest 0.158 — the 0/6/R counters at
cap 1.4–1.8 read as solid digits.

This spin also found and fixed a latent bug in the house rasteriser: `Field.raster` drew
every polygon into one shared canvas, so a later polygon's **hole** erased any earlier
polygon's ink inside it — U's separator hoop (an annulus) swallowed the serial digits
sitting in its hole. It now ORs per-polygon rasters, which is what union means. No earlier
variant had a holed polygon overlapping other geometry in the same raster call, so every
previously quoted number stands.

## Spin 6 — one finish only (2026-07-31)

Every render before spin 6 shaded the machined floors bright against the blasted face:
**two textures**. That is real geometry but an unbuildable *order* at a prototype shop.
The actual flow is machine → deburr → **one terminal finish over the whole part** —
PCBWay's Ti menu is bead blast / brushed / polish / anodize / their fixed
bead-blast-then-anodize combo, and none of it returns the part to the mill afterward.
Blast media (100–250 µm) reaches every 0.25–0.60 mm recess on this back, so floors,
crests and grooves come out **one texture**, and the engraving must read by geometry —
depth, walls, shadow — not by surface contrast.

No **shop** workaround exists on this part: selective masking at 0.8 mm scale is not a
prototype service, and a full-part lap on a plate is blocked by the part's own bearing
rule — the frame stands 0.15 proud of everything, so a flat plate touches only the frame.
(The same fact that protects the crests from wear.) The workaround that does exist is the
bench — see spin 7.

`spin1_cutters.shot()` grew a `uniform=True` mode that shades every surface in the
blasted material, and `spin6_finish.py` re-renders the four leaders (M, T, U, V) three
ways: the as-cut two-tone (real only until the finisher's cabinet), uniform blast under
diffuse light, and uniform blast under raking light. What the sheet shows: **T's
v-grooves and M's 0.60 walls survive one finish best** — v-carving is engraving's native
single-finish form, and depth buys shadow; the 0.25 relief variants (U/V) go quiet in
diffuse light and come back under raking light. The still-uniform options that remain
real: blast (recommended — hides tool marks), brushed/as-machined (bright), or blast +
Ti-anodize for colour (uniform colour; the cut and the crest anodize alike).

## Spin 7 — blast + home lap: the two-texture finish, recovered by hand

The finish spin 6 said no shop can order is a ten-minute bench operation: after the
uniform blast, a **small hand block with fine-grit lapping film, worked inside the clear
band**, re-brightens the flat crests against the dark blasted field — the classic
caseback/coin finish. This part is unusually well built for it:

- **The proud features are lap stops.** The frame (+0.15) and the fin ribs (+0.10) are
  both *higher* than the engraving crests (0.00, the art-field plane). A block that
  strays off the band rides up and lifts clear of the crests — the medallion can't be
  scratched by a wandering block, only abandoned. The failure mode is bright rib tops,
  which is a look, not a defect.
- **Depth is not at risk.** Film removes microns per session; crests stand 0.25 mm above
  their floors. The contrast survives hundreds of touch-ups, and re-blast + re-lap
  resets it entirely.
- **It is not only for relief.** U/V get bright standing letters on the dark floor; M
  gets bright DRH crests in the dark 0.60 window; and T gets the *inverse* — lap the
  flat dial and the v-carved letters stay dark in a bright disc. Dark-on-bright vs
  bright-on-dark, same one blast.

`spin7_lapped.py` renders it as a third finish state via `lapped_surfaces()` — bright
only on flush cells *inside* the lap footprint, because a hand block does not brighten
what it never touches. If a lap jig is ever wanted, a resin ring that registers on the
frame and exposes only the medallion is a trivial addition to the enclosure generators.

## Spin 8 — the gameplan: every bright feature lives on the bearing plane

The decision spin (2026-07-31). The medallion's crests — ring text, rim, hoop, serial —
rise to the frame's own **+0.15 bearing plane**, so the finishing operation becomes the
simplest one that exists: the whole part, face-down, on a lapping plate. The plate
touches frame + crests and *nothing else, by geometry* — the field is 0.15 below it, the
fin ribs 0.05 below, the coin floor deeper still. No jig, no hand block, no way to scuff
what the plate cannot reach, and re-lapping is the same operation forever. The bright
area is small on purpose (~130 mm² + frame): scuffs land only where the part already
bears, and a minute on the plate restores them — the reasoning that picked this over
spin 7's large lapped dial.

"Raised" is the wrong word for how it is machined: the crests are **left**, exactly as
the frame is left — stock-plane islands the facing op steers around before the coin
sinks around them. And the tool is a straight end mill, *not* the tapered relief cutter:
at these wall heights the 15° taper would flare 0.11–0.16 into each side of a ~0.30
stroke and knife-edge the letters below the plane, where the plate could never find
them. Vertical walls keep the full stroke as lap contact.

| | idea |
| --- | --- |
| **W** SUNKEN COIN | coin floor 0.25 into the field → 0.40 walls; rim + ring + hoop + serial on the plane. 129 mm² of lap contact; Ø0.3 finisher at 1.3×D; 3.5 mm² of counter webs lap bright (tight digits read solid). |
| **X** DEEP COIN | coin floor 0.45 → 0.60 walls, the full budget as shadow under the bright plane. The Ø0.3 would run 2×D, so the finisher steps to Ø0.4 and the webs grow to 5.5 mm² — X pays for its shadow in counter legibility. |
| **Y** BARE COIN | W's depths, no rim, no hoop — 45 mm² of lap contact, the recess wall is the only circle. The quietest of the three. |
| **Z** REST-MACHINED COIN | X's drama **and** W's text, by the machinist's standard move: the Ø0.4 takes the open coin to the full 0.45 (0.60 walls at every visible edge), then the Ø0.3 **rest-machines only what the Ø0.4 could not enter** — 2.4 mm² of counters — stopping at its own 1.3×D (0.25 into the field). Counter floors sit 0.20 above the coin floor, hidden *inside* the letterforms where absolute depth is imperceptible; open-vs-solid is what the eye checks, and they come out open. Small caps up 1.40 → 1.60 so their counters clear the Ø0.3; residue after the cascade is 3.0 mm² — *less than W's* 3.5. |

**One law amended, loudly:** the frame stops being the *sole* bearing surface — the
crests join it, coplanar, finished by the same pass. (Ribs stay 0.05 under the plane and
stay dark.) This lands in `fit_rules` and the shell generator when a variant ships, not
before.

`all_studies.py` composes every variant's diffuse-light render into one sheet
(`all_studies.png`), one spin per row, titles pulled from each spin's own `VARIANTS` list
so the sheet cannot drift from the scripts. (Rows before spin 6 still render two-tone
there — they are comparative aids; spins 6–8 are the finish truth.)

## Standing recommendation

**M.** It is F's registration argument — still the only fact-about-this-object in the set —
plus I's tooling, plus the depth the 2026-07-30 rework paid for: the glow window becomes a
real 0.60 recess you find with your thumb, standing on exactly the section the rest of the
part already accepts. If the back should instead read as **one texture**, N is the strongest
"designed, not placed" argument of the twenty; K is its monogram-only reduction. **O**
replaces G as the purely typographic pick — G's grid no longer exists on the part.

Spin 4 picks **words**, not cuts, so it composes with the above rather than competing:
**S** is the zero-cost move (a one-line edit to the committed mark, worth doing whatever
else is decided); **P or T** replace the contact-block idiom entirely if the back should
say what the object *is* rather than who made it — the tap-served vCard already carries
the contact data, which is the strongest argument that the back doesn't have to.

If the ring is the direction, spin 5 is its finished form: **V** if machinability and
refinish-proofness lead (nothing thin stands alone), **U** if the object-quality of a
single struck coin is worth two thin standing rings.

Spin 6 adds the finish-robustness lens: under the one uniform finish the shop applies,
**T (v-carved) and M (0.60 walls) read strongest**; the 0.25 relief variants lean on a
two-texture contrast no shop can order and go quiet in diffuse light.

Spin 7 restores that contrast at the bench — one blast, then hand-lapped crests — and
spin 8 turns that insight into the architecture: crests on the bearing plane, whole-part
plate lap, self-limiting by geometry. **The gameplan is spin 8's sunken coin, and Z is
its resolution of the W-vs-X trade**: the full 0.60 walls everywhere the eye can see,
W-clean counters via the Ø0.3 rest pass, at the cost of one extra tool in a cascade any
CNC shop runs daily.

## Spin 9 — Z's words (architecture locked, only the text moves)

Three editorial rulings applied (2026-07-31): the **year appears once** (Z said MMXXVI
twice); **SOLAR, not SOLAR POWERED** (the claim is the word; the 13.56 MHz stays — the
one strictly useful number on the back); **the version number goes** (REV 4.0 beside
Nº 001 mixed two counting systems — the board is the fourth revision but the object is
the first one made; the board wears its rev in copper, the shell counts in serials).
Because the ring's tracking is derived, shorter strings letterspace themselves — the
density is part of each candidate:

| | ring | dial | character |
| --- | --- | --- | --- |
| **Z1** MINT | `SOLAR · NFC 13.56 MHz · ATLANTA GEORGIA` (42 ch, 1.62 cells) | Nº 001 / MMXXVI | the full caseback grammar: claim, radio, place around; serial and year minted in the middle |
| **Z2** MAKER | `SOLAR · NFC 13.56 MHz · DEVIN HOROWITZ` (41 ch, 1.66) | Nº 001 / MMXXVI | the medallion replaces the maker's mark, so the name takes the ring — a signature you can feel |
| **Z3** PURE | `SOLAR · NFC 13.56 MHz · MMXXVI` (33 ch, 2.06 — airy) | Nº 001 | the strongest object statement: the one line that differs per card, alone in the dial |
| **Z4** MONOGRAM | same ring as Z3 | DRH / Nº 001 | the back answers the front — the glow letters and the struck letters are the same three |

Webs after the tool cascade run 1.75–2.67 mm² across the four (all below Z's 3.0).

The dial was called first: **Z4's — DRH over Nº 001** (the back answers the front's glow
letters), with the frequency removed after it failed the test every other cut passed —
NFC is a single-frequency standard, so 13.56 carried no information the word did not.
Rings gained a **phase anchor** (`ring_anchor`): anchored on a phrase, the separators
fall symmetric — `SOLAR · NFC` crowns the top arc and the year lands dead-centre at six.

## Spin 10 — the material, named; the ring, agnostic

Two rulings folded together (2026-07-31). **Call out the material** — watches do, and
here it is the whole story: this run happens in titanium exactly once. And **stay
agnostic**: the next person should drop in their own facts and have them neatly fit.
The ring machinery already guarantees the second — tracking is derived, any string
re-closes the circle — and this spin turns the promise into a measured contract:

> At R 10.8 / cap 1.80 the ring accepts **~20 to 47 characters** before adjacent
> letters choke the Ø0.4 (cell ≥ 1.02 glyph + 0.40 tool). `ATL GA` fits, `NY NY` fits,
> and `SAN FRANCISCO CA` in Z8's wording lands at 47 exactly. The dial takes 2–4
> initials at cap ≤ 13/(0.822·n); the serial is one substitution per unit. When this
> graduates, `RING_TEXT` / `RING_ANCHOR` / `DIAL_MONOGRAM` / `SERIAL` become generator
> parameters.

| | ring (dial locked: DRH / Nº 001) |
| --- | --- |
| **Z6** MATERIAL, SPELLED | `SOLAR · NFC · TITANIUM · MMXXVI` (34 ch, 2.00 cells) — the watch move at full length |
| **Z7** MATERIAL, SYMBOL | `SOLAR · NFC · Ti · MMXXVI` (28 ch, 2.42 — airiest) — the chemist's shorthand, quietly correct |
| **Z8** FULL EPITAPH | `SOLAR · NFC · Ti · ATL GA · MMXXVI` (37 ch, 1.83) — power, radio, metal, place, year in one orbit; the symbol keeps room for the city |
| **Z9** SPELLED + PLACE | `SOLAR · NFC · TITANIUM · ATL GA · MMXXVI` (43 ch, 1.58) — the dense limit |
| **Z9F** THE RING, CALLED | Z9's wording, **ensured** — see below |

## The call (2026-07-31): Z9F — because the metal, not the taste, decided

The user wanted Z8 (`Ti`), and the render "botching" its lowercase i turned out to be the
render being *honest*: measured, the tittle is a 0.33 island floating over a **0.229 mm
gap** — under both the Ø0.4 primary and the Ø0.3 rest tool, so the gap stays at the
plane, laps bright, and welds the dot to the stem. Rescuing it means lifting the dot
*and* growing it to Ø0.55 (67 % wider than its own stem) — deformed twice and still the
smallest orphan post on a one-shot titanium run. **Z9 spells TITANIUM in caps and the
problem class vanishes**, so by the ensure-at-PCBWay criterion Z9 wins.

The same audit then swept every detached mark on the part and found two more members of
the class, both fixed structurally in **Z9F**:

- **The interpunct separators** measured Ø0.41 — orphan posts under the shop's ~0.5
  floor. `char_cell`/`ring_text` grew a **`min_island` rule**: any detached mark under
  0.55 in both dimensions regrows as a Ø0.55 round at its own centroid. Same dots,
  legal posts. Letters are connected forms and pass untouched.
- **The zeros were booby-trapped**: JetBrains Mono is a coding font with a *dotted
  zero* — a Ø0.29 ornament floating in every 0's counter, meaning **every serial ever
  cut** would carry orphan micro-posts. `crest_glyphs` grew `dial_min_mark`, which
  *deletes* them (growing would fill the counter): the plain oval zero, the classical
  engraving form. And the dial's `º` (0.2 mm loop walls, thinner than any stroke)
  became the full-`o` **"No 001"** — the traditional numero.

Z9F's island audit runs in-script and **asserts**: no standing island under 0.55 mm
anywhere on the coin. That is the shippable claim.

Next step: land Z9F in the shell generator as CAD (replacing `MAKER_LINES`, parameters
`RING_TEXT` / `RING_ANCHOR` / `DIAL_MONOGRAM` / `SERIAL`) and amend the bearing rule in
`fit_rules` — at that point it leaves this directory and joins the part.
