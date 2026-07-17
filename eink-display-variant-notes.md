# E-ink display variant -- concept notes

**Status: concept exploration, not adopted.** Food-for-thought captured so the reasoning,
geometry, and panel survey do not evaporate. This is a *variant* idea (a different output
modality on the same harvest / supercap / NFC / accel platform), not a v4 feature and not a
v3.0 change. Nothing here is committed to the board.

## 1. The idea in one line

Add a **bistable e-paper panel** as a persistent visual layer on the card face -- a name + a
scannable QR + the live tap-counter -- so the card is still *a business card* when it is flat
and dark, and lights up (glow + NFC) only when it has harvested enough.

## 2. Why e-paper fits a harvested card unusually well

- **Bistable = the ethos made visible.** Every other output here is a *while-powered* one: the
  LEDs breathe only while the caps hold charge, the NFC tag answers only when a phone energizes
  it. E-paper is the opposite -- spend energy **once** to write an image, then it holds forever
  at zero draw. "Harvest a little, write once, display free" is exactly this card's premise.
- **Zero idle draw, for free.** The board already power-gates the NFC tag with a TPS22918 load
  switch. The same pattern hard-powers the EPD off between updates and loses nothing -- the image
  persists with the panel fully unpowered. Not low standby; **zero**.
- **Reflective, no backlight.** E-paper is read by ambient light, which suits an indoor/desk
  card and adds no lighting load. (The amber LED monogram is the *active* drama; the EPD is the
  *passive* always-there layer -- different jobs.)

## 3. The role it plays

A persistent face that mirrors the NFC vCard visually: **name + title + a QR that encodes the
same contact** (scan to save, tap to save -- two independent paths), plus the **"times-activated"
counter** from the telemetry backlog, finally made visible. The functional win: a fully dead
SOLAR-GLOW card is blank and silent today; an e-paper card is still readable and scannable with a
flat tank, and only *adds* glow + NFC once it harvests.

## 4. Geometry -- what actually fits between the panels

Measured from `PCB/solar-glow-drh-v4_0.kicad_pcb` (the panels reuse `solarglow:PV1/PV2`):

- Card outline **50.8 x 88.9 mm** (US business card, portrait).
- **PV1** centered at Y=17.0 -> occupies Y **5.5-28.5**; **PV2** at Y=71.9 -> Y **60.4-83.4**;
  both 42 mm wide, centered (X ~4.4-46.4).
- **Clear window between the panels: Y 28.5-60.4 = 31.9 mm tall x ~48 mm usable wide** (the
  panels do not intrude into that Y-band, so nearly the full card width is open there).

Two hard walls fall out of this:
- **The 31.9 mm gap height** gates the panel's short dimension.
- **The 50.8 mm card width** gates the long dimension -- anything with an outline longer than
  ~49 mm is out in *every* orientation.

That central band is also the busiest real estate on the card today (DRH monogram + LEDs + MCU +
NFC coil), so "fits the gap" and "is free to use" are different questions -- see the variants.

## 5. Panel survey -- smallest off-the-shelf graphic e-paper

Dimensions are **bare-panel outline** (what you embed), verified against vendor datasheets
(sources at the bottom). Breakout *modules* carry a larger PCB (e.g. the 1.02" Waveshare module
is ~42 x 27 mm) -- prototype on those, embed the bare panel.

| Panel | Res | Outline W x H (mm) | Active (mm) | Thick | Driver / temp | Fit in the gap |
|---|---|---|---|---|---|---|
| **1.02"** (GDEW0102) | 128 x 80 | 32.57 x 18.6 | 21.76 x 14 | glass ~0.7 / **flex 0.3** | UC8175, 0-50 C | fits easily, any orientation |
| **0.97"** (GDEM0097T61) | 184 x 88 strip | ~27 x 15 | ~22 x 11 | ~0.9 | SSD1680, 0-50 C | fits (narrow banner) |
| **1.54"** (GDEY0154D67) | 200 x 200 | 37.32 x 31.8 | 27.6 x 27.6 | ~1.05 | SSD1681, 0-50 C | **fits only rotated** (31.8 into 31.9) |
| 1.9" **segment** | 91 segs | 49.35 x 32.11 | 41.35 x 28.11 | ~1.1 | I2C, 0-50 C | borderline (32.11 > 31.9 by 0.2) |
| 2.13" (GDEY0213B74) | 250 x 122 | **59.2** x 29.2 | 48.55 x 23.7 | ~1.05 | SSD1680, 0-50 C | **too long** (59.2 > 50.8 card) |

**Key findings:**
- **The floor for a graphic (pixel-grid) panel is ~1.0".** Below that it is segmented /
  electrochromic only (simple digits/icons, sub-mJ, any size, ~1 V drive) -- fine for a counter
  or icon, no QR or arbitrary text.
- **Orientation is decisive for the 1.54".** It is nearly square; laid vertically its 37.32 mm
  side overflows the 31.9 mm gap, but **rotated horizontally its 31.8 mm side just clears**
  (0.1 mm to spare) and its 37.32 mm side sits easily within the width. That upgrades the max
  graphic panel from 128 x 80 to **200 x 200 -- ~4x the pixels** (enough for a real QR + name +
  icon together).
- **The card width is the ceiling.** The 2.13" name-badge strip (the obvious "bigger" step) has
  a 59.2 mm glass -- longer than the whole 50.8 mm card, so it overhangs both edges in any
  orientation. To go past 1.54" you widen the card.
- **Flexible variants (0.3 mm)** are thinner than the FR4 and will not crack in a wallet -- the
  right pick for a card. Glass is ~0.7-1.05 mm (still thin vs the 1.75 mm supercap cavity).

## 6. The two variants (both drawn as to-scale mockups this session)

**A. E-ink HERO (1.54", 200 x 200).** The display *is* the card face: contact QR + DRH monogram
+ name + firm + live tap-counter, all legible. It **fills** the 31.9 mm gap edge-to-edge (needs
the panels nudged ~1 mm apart for assembly clearance -- trivial, there is unused margin at both
card ends). Because it owns the center, it **displaces** the LED monogram and the NFC coil that
live there -- real floorplan work, not a drop-in. This is a genuinely different card.

**B. LED hero + e-ink STRIP (1.02", 128 x 80).** The amber DRH monogram stays the star; the EPD
drops to a tuck-in strip below it (short-URL QR + name + counter, cramped, tiny type, no room for
the monogram). Keeps the signature glow; the e-paper is a footnote sharing the gap.

Decision framing: **hero = new variant** (display is the front, LED monogram retired);
**strip = add-on** (LED stays hero, e-paper is a secondary readout). Neither is a v4 feature --
both reuse the harvest/supercap/NFC/accel platform untouched and only change the center.

## 7. Integration costs (honest)

- **Refresh energy is affordable, not free.** A small mono full-refresh is ~tens of mJ (~2-3 s),
  roughly **one LED tap** (0.026 J). A partial/fast refresh is a few mJ. So refresh on an
  **event** (provisioning, a tap, a daily tick), gated on caps-full -- never continuously. The
  bistable hold and the load-switch gate make the *idle* cost zero.
- **Pins.** A COG panel needs SPI (SCK/MOSI/CS) + DC + RST + BUSY = **~6 GPIO**. Real pressure on
  the AVR64DD28 mid-v4-rework (competes with the LED bank / accel lines). The 1.9" **segment**
  part is I2C (2 pins, shares the existing bus) but segment-only.
- **RAM.** A 200 x 200 mono framebuffer is **5 KB** on an 8 KB-SRAM part -- workable but notable;
  128 x 80 is 1.25 KB, comfortable. Streaming a statically-composed image to the panel's own RAM
  avoids a full local buffer, so this is a consideration, not a blocker.
- **On-panel HV.** COG drivers generate the +/-15 V drive on-glass from a handful of small caps --
  no discrete boost, but a few more passives.
- **Temperature.** Standard EPDs are **0-50 C operating**. Below 0 C the image *holds* but will
  not *refresh* (graceful -- a cold-pocket card just waits to warm). The 50 C top is well under
  the 85 C supercap ceiling, so the EPD is not the new thermal-limiter for storage; refresh just
  wants the card near room temp. Wide-temp EPD variants exist if ever needed.
- **Fragility / thickness.** Prefer a **flexible 0.3 mm** panel (robust, ultra-thin); if glass,
  lean on the titanium frame for protection.
- **Cost.** A small EPD adds ~$5-15; the supercaps already dominate the BOM, so this is real but
  not category-changing.

## 8. Firmware sketch (feasibility, not a design)

Localized and reuses existing patterns:
- **Driver:** a mono EPD SPI driver (init + full/partial refresh); ~1-2 KB flash for a small
  panel. Compose the face (QR + text) either from flash bitmaps or generated, streamed to the
  panel RAM.
- **When to refresh:** on NFC provisioning (new contact), on a tap milestone, and/or a daily tick
  -- always gated on `sense_caps_full`, so a refresh never browns out the MCU. Reuses the same
  cap-state gates the LED glow already respects.
- **Power-gate:** own load switch on a spare GPIO (the FRAM-idea pattern), EPD fully off between
  updates -> zero standby.
- **Counter tie-in:** the EEPROM "times-activated" count (telemetry backlog) becomes the
  displayed `▲ N taps` -- the card visibly records its own life.

## 9. Open questions / what would move this forward

1. **Refresh-energy budget vs desk harvest** -- the gating number: mJ/refresh vs harvested mJ/day
   at desk light says how often it can repaint. This ties directly to the **#1 open gate**
   (unmeasured indoor harvest) and the `harvest-bench-fixture-handoff.md` board -- measure first.
2. **Hero floorplan rework** -- where the NFC coil / MCU / supercaps go once the 1.54" owns the
   front (toward the card ends, under the panels, or the back).
3. **Graphic vs segmented** -- QR/name needs a graphic panel (1.02"/1.54"); a counter/icon alone
   could use a near-free segmented part.
4. **Flexible vs glass** sourcing, and **wide-temp** if outdoor refresh ever matters.

## Sources (panel data)

- Good Display GDEW0102T4 datasheet -- 1.02" outline 32.57 x 18.6, active 21.76 x 14, UC8175.
- Good Display GDEW0102I4FC -- 1.02" flexible (0.3 mm).
- Good Display GDEM0097T61 -- 0.97" 184 x 88, SSD1680.
- Waveshare 1.54" raw panel datasheet -- outline 37.32 x 31.8 x 1.05, active 27.6 x 27.6, 200 x 200.
- Good Display GDEY0154D67 -- 1.54" 200 x 200, SSD1681.
- Good Display / Waveshare GDEY0213B74 -- 2.13" outline 59.2 x 29.2, active 48.55 x 23.7.
- Waveshare 1.9" segment e-paper -- outline 49.35 x 32.11, active 41.35 x 28.11, I2C.
