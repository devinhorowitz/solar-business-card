#!/usr/bin/env python3
"""Live stock check for the SOLAR-GLOW DRH v4.0 BOM -> BOM/README.md.

Reads every orderable line from the DESIGN (via scripts/bom_split.py, which
derives them from the schematic and the board's own flags -- there is no
hand-authored BOM any more),
asks DigiKey (Product Information v4) and Mouser (Search API) what each MPN
costs and whether it is still in production, and rewrites BOM/README.md as a
purely derived availability table. The point is the years-later glance: run
this once and know, without opening a distributor site, which parts are still
orderable -- and where a line is dead AND its documented substitutes are dead
too, a red X says so.

Sources of truth:
  - line items and quantities ................... scripts/bom_split.py, i.e. the
    schematic + the board's exclude_from_bom / dnp flags. A part enters or leaves
    this table by changing the DESIGN, never by editing a sheet.
  - manufacturers ............................... the schematic's own Manufacturer
    property, via the same split. Not decoration: it is the hard filter that keeps a
    short or all-numeric MPN from matching another vendor's part (see MOUSER_FIRST).
  - substitutes ................................. SUBS below, the one piece of
    hand-kept sourcing knowledge left (the xlsx that used to carry it was retired
    2026-08-02); each entry cites where its alternate came from
  - live numbers ................................ the distributor APIs at run
    time; nothing is cached

Verdicts:
  OK   primary MPN in stock and not end-of-life/obsolete/NRND
  SUB  primary unavailable, but at least one documented substitute is
  DEAD primary unavailable and no substitute available either (the red X)
  ?    a query failed -- "could not check" is reported as itself, never as DEAD

The datasheets/ filenames carry a "$price" segment (the convention is
"REF  MPN  $price.pdf") that is a copy of a live number and therefore rots.
Every run audits those names against the same live data and reports drift in
its own README section;  --fix-names  renames the drifted files AND rewrites
every citation of them -- the schematic and board Datasheet properties
(byte-safe, CRLF preserved), the BOM master's cells, and any tracked .md --
in one act, the same manual-apply shape as scripts/mask_art.py --apply.
A $0 price in a name is a deliberate no-ordered-part marker and is skipped;
names with no price segment (errata, the TIM pad) are listed, not judged.

Credentials come from the environment and are never printed or written:
  DIGIKEY_CLIENT_ID / DIGIKEY_CLIENT_SECRET   (OAuth2 client-credentials)
  MOUSER_PART_API_KEY

Refresh:  python3 BOM/check_stock.py     (~1 min; Mouser is rate-limited to
~30 calls/min, so Mouser-sourced rows pause between requests)
"""

import datetime
import os
import re
import sys
import time

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(HERE, "README.md")
DATASHEETS = os.path.join(ROOT, "datasheets")

# Datasheet-name price drift beyond this fraction gets the DRIFT verdict
# (under it, the name is "close enough for the magnitude it exists to give").
NAME_PRICE_TOL = 0.05

DK_TOKEN_URL = "https://api.digikey.com/v1/oauth2/token"
DK_SEARCH_URL = "https://api.digikey.com/products/v4/search/keyword"
MOUSER_URL = "https://api.mouser.com/api/v1/search/partnumber"

# Master column layout (0-based): Ref(s), Qty, Function, Value,
# Package/Footprint, Mfr, MPN, ~$/ea, Ext $, Status, Sourcing note,
# Datasheet, Distributor P/N.
COL_REFS, COL_QTY, COL_FUNC, COL_VALUE = 0, 1, 2, 3
COL_MFR, COL_MPN, COL_PRICE, COL_DKPN = 5, 6, 7, 12

# Rows whose MPN is prose-in-parentheses carry no ordered part (PCB bridges,
# bare pads, drills, the machined shell); they are listed, not queried.
# These two are orderable-shaped but still not distributor lines:
NO_API = {
    "HW1": "generic fastener (DIN 84 M2x3 brass) -- any fastener house; "
    "precision alt Accu SFE-M2-3 (master row note)",
}

# The one line whose MPN no distributor query can resolve: Mouser lists the mfr P/N as
# AEM10300-QFN, not the e-peas ordering code the design carries, so the SKU is pinned
# and matched on MouserPartNumber.
#
# NOTHING ELSE IS PINNED, and that is deliberate -- the collision problem this table
# used to absorb is now solved upstream. pick_match() treats the manufacturer as a HARD
# filter for collision-prone MPNs (short or all-numeric), and mfr_ok()'s docstring names
# the case exactly: "a bare '5879' is both the Adafruit programmer and a Pomona test
# clip". That filter was inert for as long as the design had no manufacturer to give it.
# When the xlsx master carrying the Mfr column was culled on 2026-08-02, load_lines()
# started sending mfr="" for every line, and mfr_ok() returns True on an empty
# manufacturer -- the filter was not bypassed, it was starved.
#
# It bit immediately: the 2026-08-02 run resolved PRG1 to Mouser 243-5879 -- a Pomona
# clip, $88.96, 0 in stock -- and published it as the UPDI Friend, downgrading the row
# to substitute-only while the real part (485-5879) had 54 in stock at $6.95.
#
# The repair is upstream, where it belongs: every placed symbol now carries a
# Manufacturer property in the schematic (and mirrored onto its footprint, so DRC's
# schematic-parity check holds the two together), bom_split.build() FAILS on a part that
# has an MPN but no manufacturer, and load_lines() passes it through. Measured on the
# same query: starved -> 243-5879 @ $88.96/0 stock; fed "Adafruit" -> 485-5879 @
# $6.95/54 stock. A SKU pin for PRG1 would work too, but it would be redundant cover
# that hides a regression -- if the field were ever lost, the pinned line would keep
# looking correct while every other collision-prone MPN (FER1's 364006, the Schurter
# supercaps) quietly went wrong.
MOUSER_FIRST = {
    "U8": "120-AEM10300-QFN",
}

# Documented substitutes, transcribed from the master's own sourcing notes --
# (mpn, mfr, query_source, mouser_sku_or_None, note). A substitute here is
# what the master says to order when the primary runs dry, not an invitation
# to re-engineer; C9's are the same-series tuning ladder, U6's is an explicit
# last resort.
SUBS = {
    "U1": [
        ("AVR64EA28T-E/STX", "Microchip", "digikey", None,
         "tape-reel variant, same die (U1 row note)"),
    ],
    "C9": [
        ("QSCT251Q390G1GV001E", "Johanson", "digikey", None,
         "39 pF same-series ladder -- raises the enclosed resonance if the first card tunes low (C9 row note)"),
        ("QSCT251Q560G1GV001E", "Johanson", "digikey", None,
         "56 pF same-series ladder -- lowers it if the first card tunes high (C9 row note)"),
    ],
    "U6": [
        ("TPS22918TDBVRQ1", "Texas Instruments", "digikey", None,
         "pin-identical AEC-Q100 sibling, ~50x the OFF leakage -- last resort only; NEVER TPS22917L (inverted EN) (U6 row note)"),
    ],
    "C23": [
        ("GRT188R61E225KE13D", "Murata", "digikey", None,
         "AEC-Q200 alternate; X5R, the dielectric trade the master documents (C23 row note)"),
    ],
    "U7": [
        ("MB85RC512TYPNGA1", "Fujitsu/RAMXEED", "mouser", "249-MB85RC512TYPNGA1",
         "same die, Mouser listing (U7 row note)"),
    ],
    "FER1": [
        ("3641014", "Würth Elektronik", "digikey", None,
         "0.14 mm sheet -- stack 3x for equivalent ferrite thickness (FER1 row note)"),
        ("MHLL6060-300", "Laird", "digikey", None,
         "Laird 0.09 mm -- weakest shielding, last resort (FER1 row note)"),
    ],
    # Not from the retired master -- this one cites its own source, which is the
    # convention for anything added after the xlsx was culled. Added 2026-08-02, the
    # day the primary went dry at DigiKey, so the NEXT dry-out reports SUB instead of
    # sending someone back to the distributor sites to rediscover the alternate.
    "PRG1": [
        ("5893", "Adafruit Industries LLC", "digikey", None,
         "HV UPDI Friend -- does STANDARD serial UPDI as well (the high-voltage pulse "
         "is an added capability, not a replacement), with the same switchable 3 V/5 V "
         "supply at up to 500 mA and the same built-in loop-back resistor, so it drives "
         "a flat card identically at the 3 V setting. ~$3 dearer and its HV feature is "
         "never needed here (UPDIPINCFG stays at default). "
         "Source: adafruit.com/product/5893, checked 2026-08-02"),
    ],
}

BAD_LIFECYCLE = re.compile(
    r"obsolete|end of life|discontinued|last time buy|not recommended", re.I
)


def die(msg):
    sys.exit(f"check_stock: {msg}")


def mfr_ok(master_mfr, hit_mfr):
    """Same-manufacturer heuristic, lenient on naming: token overlap or
    substring either way ('Fujitsu/RAMXEED' vs 'RAMXEED Limited'). Knows it
    can miss honest abbreviations ('TI' shares nothing with 'Texas
    Instruments'), so pick_match() only ENFORCES it where MPN collisions
    actually live -- short or all-numeric MPNs, where a bare '5879' is both
    the Adafruit programmer and a Pomona test clip."""
    if not master_mfr or not hit_mfr:
        return True
    a, b = str(master_mfr).lower(), str(hit_mfr).lower()
    ta = {t for t in re.split(r"[^\w]+", a) if len(t) >= 2}
    tb = {t for t in re.split(r"[^\w]+", b) if len(t) >= 2}
    return bool(ta & tb) or a in b or b in a


def collision_prone(mpn):
    compact = re.sub(r"[^A-Za-z0-9]", "", mpn)
    return compact.isdigit() or len(compact) < 7


def mpn_matches(want, got):
    """Exact, or exact plus a distributor packing suffix (Murata lists
    DFE252010F-100M as DFE252010F-100M=P2)."""
    w = want.replace(" ", "").upper()
    g = (got or "").replace(" ", "").upper()
    return g == w or (g.startswith(w) and len(g) > len(w) and g[len(w)] in "=#")


def pick_match(candidates, mpn, mfr):
    """First candidate whose manufacturer agrees; for distinctive MPNs a
    manufacturer-name mismatch downgrades to a preference (the MPN itself is
    the strong key), for collision-prone ones it stays a hard filter."""
    for c, name in candidates:
        if mfr_ok(mfr, name):
            return c
    if candidates and not collision_prone(mpn):
        return candidates[0][0]
    return None


class DigiKey:
    def __init__(self):
        self.cid = os.environ.get("DIGIKEY_CLIENT_ID")
        secret = os.environ.get("DIGIKEY_CLIENT_SECRET")
        if not (self.cid and secret):
            die("DIGIKEY_CLIENT_ID / DIGIKEY_CLIENT_SECRET not set")
        r = requests.post(
            DK_TOKEN_URL,
            data={"client_id": self.cid, "client_secret": secret,
                  "grant_type": "client_credentials"},
            timeout=30,
        )
        if not r.ok:
            die(f"DigiKey token request failed: HTTP {r.status_code}")
        self.token = r.json()["access_token"]

    def _keyword(self, keywords):
        time.sleep(0.6)
        r = requests.post(
            DK_SEARCH_URL,
            json={"Keywords": keywords, "Limit": 25},
            headers={
                "Authorization": f"Bearer {self.token}",
                "X-DIGIKEY-Client-Id": self.cid,
                "X-DIGIKEY-Locale-Site": "US",
                "X-DIGIKEY-Locale-Language": "en",
                "X-DIGIKEY-Locale-Currency": "USD",
            },
            timeout=30,
        )
        if not r.ok:
            raise RuntimeError(f"DigiKey search HTTP {r.status_code} for {keywords}")
        return r.json().get("Products") or []

    def lookup(self, mpn, mfr=None):
        """-> dict(status, qty, price, dist_pn) or None if not found."""
        match = None
        for keywords in (mpn, f"{mfr} {mpn}" if mfr else None):
            if keywords is None:
                continue
            candidates = [
                (p, (p.get("Manufacturer") or {}).get("Name"))
                for p in self._keyword(keywords)
                if mpn_matches(mpn, p.get("ManufacturerProductNumber"))
            ]
            match = pick_match(candidates, mpn, mfr)
            if match:
                break
        if match is None:
            return None
        qty = match.get("QuantityAvailable") or 0
        status = ((match.get("ProductStatus") or {}).get("Status")) or "?"
        # q1 price: cheapest BreakQuantity==1 across variations (CT vs reel),
        # falling back to the product-level unit price.
        q1 = []
        pn = None
        for var in match.get("ProductVariations") or []:
            for brk in var.get("StandardPricing") or []:
                if brk.get("BreakQuantity") == 1:
                    q1.append(brk.get("UnitPrice"))
            if pn is None and var.get("MinimumOrderQuantity") in (0, 1):
                pn = var.get("DigiKeyProductNumber")
        price = min([p for p in q1 if p is not None], default=match.get("UnitPrice"))
        if pn is None:
            vars_ = match.get("ProductVariations") or []
            pn = vars_[0].get("DigiKeyProductNumber") if vars_ else None
        return {"source": "DigiKey", "status": status, "qty": qty,
                "price": price, "dist_pn": pn or "?"}


class Mouser:
    def __init__(self):
        self.key = os.environ.get("MOUSER_PART_API_KEY")
        if not self.key:
            die("MOUSER_PART_API_KEY not set")

    def lookup(self, query, mfr=None, match_sku=None):
        """Query by part number; match on mfr P/N == query, or on
        MouserPartNumber == match_sku when given. ~30 req/min limit."""
        time.sleep(2.1)
        r = requests.post(
            f"{MOUSER_URL}?apiKey={self.key}",
            json={"SearchByPartRequest": {"MouserPartNumber": query}},
            timeout=30,
        )
        if not r.ok:
            raise RuntimeError(f"Mouser search HTTP {r.status_code} for {query}")
        body = r.json()
        if body.get("Errors"):
            raise RuntimeError(f"Mouser API error for {query}: {body['Errors']}")
        parts = (body.get("SearchResults") or {}).get("Parts") or []
        candidates = []
        for p in parts:
            sku = (p.get("MouserPartNumber") or "").replace(" ", "").upper()
            sku_hit = sku == query.replace(" ", "").upper() or (
                match_sku and sku == match_sku.replace(" ", "").upper()
            )
            if mpn_matches(query, p.get("ManufacturerPartNumber")) or sku_hit:
                candidates.append((p, p.get("Manufacturer")))
        match = pick_match(candidates, query, mfr)
        if match is None:
            return None
        avail = match.get("AvailabilityInteger")
        if avail is None:
            m = re.match(r"\s*([\d,]+)", match.get("Availability") or "")
            avail = int(m.group(1).replace(",", "")) if m else 0
        lifecycle = match.get("LifecycleStatus") or "Active (listed)"
        price = None
        for brk in match.get("PriceBreaks") or []:
            if brk.get("Quantity") == 1:
                m = re.search(r"[\d.]+", brk.get("Price") or "")
                price = float(m.group(0)) if m else None
                break
        return {"source": "Mouser", "status": lifecycle, "qty": avail,
                "price": price, "dist_pn": match.get("MouserPartNumber") or "?"}


def is_available(hit):
    return bool(hit) and hit["qty"] > 0 and not BAD_LIFECYCLE.search(hit["status"])


_CACHE = {}


def query_part(dk, mouser, mpn, mfr=None, source_hint=None, mouser_sku=None):
    """Both distributors, preferred source first. Returns the first hit that
    is actually AVAILABLE; a listed-but-dry hit is kept only if the other
    source has nothing better (a DigiKey row at 0 stock must not mask live
    Mouser stock -- the C26/C27 lesson). Returns (hit_or_None, err_or_None)."""
    key = (mpn, mfr, mouser_sku)
    if key in _CACHE:
        return _CACHE[key]
    order = ["mouser", "digikey"] if source_hint == "mouser" else ["digikey", "mouser"]
    best, err = None, None
    for src in order:
        try:
            if src == "digikey":
                hit = dk.lookup(mpn, mfr=mfr)
            else:
                hit = mouser.lookup(mouser_sku or mpn, mfr=mfr, match_sku=mouser_sku)
        except RuntimeError as e:
            err = str(e)
            continue
        if is_available(hit):
            _CACHE[key] = (hit, None)
            return hit, None
        if hit and best is None:
            best = hit
    _CACHE[key] = (best, None if best else err)
    return _CACHE[key]


def load_lines():
    """Every ORDERABLE line, derived from the design.

    scripts/bom_split.py owns the split (assembly / hand-solder / off-board) and
    reads it from the schematic plus the board's own flags, so this script cannot
    disagree with what the fab documents say. Only lines with a supplier are
    returned: a screw sourced locally or the machined shell have nothing for a
    distributor API to answer about, and a stock table that lists them is lying
    about what it checked.
    """
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    import bom_split
    asm, hand, off, once, problems = bom_split.build()
    if problems:
        sys.exit("check_stock: the design cannot be split cleanly -- " + "; ".join(problems))
    out = []
    for kind, rows in (("assembly", asm), ("hand-solder", hand)):
        for r in rows:
            out.append({"refs": ", ".join(r["refs"]), "qty": r["qty"], "mfr": r["mfr"],
                        "mpn": r["mpn"], "kind": kind})
    for ref, qty, mpn, mfr, sup, _dpn, _note in list(off) + list(once):
        if sup:
            out.append({"refs": ref, "qty": qty, "mfr": mfr, "mpn": mpn,
                        "kind": "off-board"})
    return out


def fmt_price(p):
    return f"${p:.2f}" if isinstance(p, (int, float)) else "--"


def fmt_qty(q):
    return f"{q:,}"


def _compact(s):
    return re.sub(r"[^A-Za-z0-9]", "", s).upper()


_NAME_PRICE_RE = re.compile(r"\$(\d+(?:\.\d+)?)\.pdf$")


def audit_datasheet_names(results):
    """Check every datasheets/ filename's $price segment against the live
    numbers just fetched. Returns rows of
    (filename, label, name_price|None, live_price|None, verdict) where
    verdict is 'ok' | 'drift' | 'zero' ($0 marker) | 'noprice' | 'unmapped'."""
    live = {}  # compacted MPN -> (label, live q1 price)
    for entry, hit, _err, _verdict, sub_hits in results:
        live[_compact(entry["mpn"])] = (entry["refs"], hit["price"] if hit else None)
        for smpn, _note, shit, _serr in sub_hits:
            live.setdefault(_compact(smpn), (f"{entry['refs']} sub",
                                             shit["price"] if shit else None))
    rows = []
    for fn in sorted(os.listdir(DATASHEETS)):
        if not fn.lower().endswith(".pdf"):
            continue
        cfn = _compact(fn)
        # longest live MPN that appears in the compacted filename wins
        best = max((m for m in live if m in cfn), key=len, default=None)
        m = _NAME_PRICE_RE.search(fn)
        name_price = float(m.group(1)) if m else None
        if best is None:
            # price-less and unmapped = a secondary/reference doc (errata,
            # the TIM pad) -- informational, not a mapping failure
            verdict = "noprice" if name_price is None else "unmapped"
            rows.append((fn, "(secondary/reference doc)", name_price, None, verdict))
            continue
        label, live_price = live[best]
        if name_price is None:
            rows.append((fn, label, None, live_price, "noprice"))
        elif name_price == 0:
            rows.append((fn, label, 0.0, live_price, "zero"))
        elif live_price is None:
            rows.append((fn, label, name_price, None, "unmapped"))
        else:
            drift = abs(live_price - name_price) / name_price
            rows.append((fn, label, name_price, live_price,
                         "ok" if drift <= NAME_PRICE_TOL else "drift"))
    return rows


def fix_datasheet_names(name_rows):
    """Rename DRIFTed datasheets to their live price and rewrite every
    citation: sch (LF) and pcb (CRLF) byte-safely, the BOM master's string
    cells, and any tracked .md. git-mv keeps the renames tracked."""
    import subprocess
    renames = []
    for fn, _label, name_price, live_price, verdict in name_rows:
        if verdict != "drift":
            continue
        new_fn = _NAME_PRICE_RE.sub(f"${live_price:.2f}.pdf", fn)
        renames.append((fn, new_fn))
    if not renames:
        print("--fix-names: nothing drifted, nothing to do")
        return
    for old, new in renames:
        subprocess.run(["git", "mv", os.path.join("datasheets", old),
                        os.path.join("datasheets", new)], cwd=ROOT, check=True)
        print(f"renamed: {old} -> {new}")
    # citations: board/sch as bytes (the pcb is CRLF and must stay CRLF --
    # the swap is within a line, so EOLs are untouched by construction)
    kicad = [os.path.join(ROOT, "PCB", f) for f in os.listdir(os.path.join(ROOT, "PCB"))
             if f.endswith((".kicad_sch", ".kicad_pcb"))]
    for path in kicad:
        b = open(path, "rb").read()
        n0 = b
        for old, new in renames:
            b = b.replace(old.encode(), new.encode())
        if b != n0:
            open(path, "wb").write(b)
            print(f"citations updated: {os.path.relpath(path, ROOT)}")
    # tracked markdown
    ls = subprocess.run(["git", "ls-files", "*.md"], cwd=ROOT,
                        capture_output=True, text=True, check=True)
    for rel in ls.stdout.split():
        path = os.path.join(ROOT, rel)
        t = open(path, encoding="utf-8").read()
        t0 = t
        for old, new in renames:
            t = t.replace(old, new)
        if t != t0:
            open(path, "w", encoding="utf-8").write(t)
            print(f"citations updated: {rel}")
    print(f"--fix-names: {len(renames)} file(s) renamed; re-run this script "
          "so README reflects the new names, then run scripts/check_consistency.py")


def main():
    ordered = load_lines()
    dk = DigiKey()
    mouser = Mouser()

    results = []  # (entry, hit|None, err|None, verdict, sub_hits)
    for entry in ordered:
        refs, mpn = entry["refs"], entry["mpn"]
        key = refs.split(",")[0].split("–")[0].strip()  # "C26, C27"->"C26", "D2–D5"->"D2"
        if key in NO_API or refs in NO_API:
            results.append((entry, None, None, "manual", []))
            print(f"  {refs:10s} {mpn:32s} manual line, not queried")
            continue
        hint = "mouser" if key in MOUSER_FIRST else None
        hit, err = query_part(dk, mouser, mpn, mfr=entry["mfr"], source_hint=hint,
                              mouser_sku=MOUSER_FIRST.get(key))
        # Substitutes are always queried when documented -- the table shows
        # their live state whether or not the primary needs them today.
        sub_hits = []
        for smpn, smfr, ssrc, ssku, snote in SUBS.get(key, []):
            shit, serr = query_part(dk, mouser, smpn, mfr=smfr,
                                    source_hint=ssrc, mouser_sku=ssku)
            sub_hits.append((smpn, snote, shit, serr))
        if is_available(hit):
            verdict = "ok"
        elif hit is None and err:
            verdict = "unknown"
        elif any(is_available(sh) for _, _, sh, _ in sub_hits):
            verdict = "sub"
        else:
            verdict = "dead"
        results.append((entry, hit, err, verdict, sub_hits))
        stat = (f"{hit['source']}: {hit['status']}, {hit['qty']:,} in stock, "
                f"{fmt_price(hit['price'])}") if hit else f"NOT FOUND ({err or 'no exact match'})"
        print(f"  {refs:10s} {mpn:32s} {stat}")

    name_rows = audit_datasheet_names(results)
    if "--fix-names" in sys.argv:
        fix_datasheet_names(name_rows)
        name_rows = audit_datasheet_names(results)
    n_drift = sum(1 for *_x, v in name_rows if v == "drift")

    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    icon = {"ok": "✅", "sub": "⚠️", "dead": "❌",
            "unknown": "❓", "manual": "—"}
    n_ok = sum(1 for *_, v, _s in results if v == "ok")
    n_sub = sum(1 for *_, v, _s in results if v == "sub")
    n_dead = sum(1 for *_, v, _s in results if v == "dead")
    n_unk = sum(1 for *_, v, _s in results if v == "unknown")
    n_man = sum(1 for *_, v, _s in results if v == "manual")

    lines = []
    a = lines.append
    a("# BOM — live availability")
    a("")
    a("> **GENERATED — do not edit.** Written by [`BOM/check_stock.py`](check_stock.py)")
    a("> from the DESIGN (`scripts/bom_split.py` — the schematic plus the board\'s own")
    a("> flags) plus live DigiKey/Mouser data. There is no hand-authored BOM: the board")
    a("> is the source of truth for what to buy, and this file is the source of nothing —")
    a("> regenerate it, never hand-edit it.")
    a(">")
    a("> Refresh: `python3 BOM/check_stock.py` (needs `DIGIKEY_CLIENT_ID`,")
    a("> `DIGIKEY_CLIENT_SECRET`, `MOUSER_PART_API_KEY` in the environment; ~1 min).")
    a("")
    a(f"**Checked: {now}** · DigiKey Product Information v4 + Mouser Search API, "
      "queried by MPN (stored distributor P/Ns are shown as found live, not trusted from the sheet).")
    a("")
    a(f"**{n_ok} of {len(results)} lines fully available** · "
      f"{n_sub} on substitute only · **{n_dead} dead (❌)** · "
      f"{n_unk} unverifiable this run · {n_man} manual-order.")
    a("")
    # THE P/N GETS ITS OWN CELL, and the source gets a separate one. This column used to
    # render "{dist_pn} ({source})" in one cell, and on 2026-08-02 that cost a fab document:
    # the C26/C27 cell was copied back into the schematic's Supplier P/N field, annotation
    # and all, so the design carried "187-CL21B106KOQNNNG (Mouser)" as a part number. A
    # generated display string must not be paste-compatible with the field it derives from.
    a("| | Ref(s) | Qty | Mfr | MPN | Distributor P/N | Src | Lifecycle | Stock | $ @1 live |")
    a("|---|---|---|---|---|---|---|---|---|---|")
    for entry, hit, err, verdict, _subs in results:
        if verdict == "manual":
            key = entry["refs"].split(",")[0].split("–")[0].strip()
            note = NO_API.get(key, NO_API.get(entry["refs"], "manual order"))
            a(f"| — | {entry['refs']} | {entry['qty'] or ''} | {entry['mfr'] or ''} | "
              f"`{entry['mpn']}` | — | — | {note} | — | — |")
            continue
        if hit:
            a(f"| {icon[verdict]} | {entry['refs']} | {entry['qty'] or ''} | {entry['mfr'] or ''} | "
              f"`{entry['mpn']}` | `{hit['dist_pn']}` | {hit['source']} | {hit['status']} | "
              f"{fmt_qty(hit['qty'])} | {fmt_price(hit['price'])} |")
        else:
            why = "no exact listing found" if not err else "query failed"
            a(f"| {icon[verdict]} | {entry['refs']} | {entry['qty'] or ''} | {entry['mfr'] or ''} | "
              f"`{entry['mpn']}` | — | — | {why} | 0 | — |")
    a("")
    a("**Verdicts** — ✅ primary MPN in stock and in production · "
      "⚠️ primary unavailable, a documented substitute (below) is available · "
      "❌ **primary unavailable and every documented substitute unavailable too** · "
      "❓ the distributor query itself failed (re-run before concluding anything) · "
      "— not a distributor line.")
    a("")
    a("## Documented substitutes")
    a("")
    a("Hand-kept sourcing knowledge — availability shown live. Older entries were "
      "transcribed from the retired xlsx master; anything added since cites its own "
      "source in the note. "
      "These are the master's named fallbacks (C9's are its enclosed-tuning ladder, "
      "U6's an explicit last resort), not re-engineering suggestions.")
    a("")
    a("| For | Substitute MPN | Lifecycle | Stock | $ @1 | Note |")
    a("|---|---|---|---|---|---|")
    for entry, hit, err, verdict, sub_hits in results:
        for smpn, snote, shit, serr in sub_hits:
            if shit:
                a(f"| {entry['refs']} | `{smpn}` | {shit['status']} ({shit['source']}) | "
                  f"{fmt_qty(shit['qty'])} | {fmt_price(shit['price'])} | {snote} |")
            else:
                a(f"| {entry['refs']} | `{smpn}` | not found | 0 | — | {snote} |")
    a("")
    a("## Datasheet filename prices")
    a("")
    a("The `datasheets/` naming convention embeds a `$price` — a copy of a live number, "
      "so it rots. Audited here against the same fetch as the tables above "
      f"(±{NAME_PRICE_TOL:.0%} tolerance); `python3 BOM/check_stock.py --fix-names` renames "
      "drifted files **and rewrites every citation** (board/schematic Datasheet fields, "
      "the master's cells, tracked docs) in one act. A `$0` name is a deliberate "
      "no-ordered-part marker; price-less names (errata, the TIM pad) are informational.")
    a("")
    a("| | File | Maps to | $ in name | $ live |")
    a("|---|---|---|---|---|")
    NAME_ICON = {"ok": "✅", "drift": "🔻", "zero": "—", "noprice": "—", "unmapped": "❓"}
    for fn, label, name_price, live_price, verdict in name_rows:
        note = {"zero": " ($0 marker)", "noprice": " (no price segment)",
                "unmapped": " (no live match)"}.get(verdict, "")
        a(f"| {NAME_ICON[verdict]} | `{fn}` | {label}{note} | "
          f"{fmt_price(name_price) if name_price is not None else '—'} | "
          f"{fmt_price(live_price) if live_price is not None else '—'} |")
    a("")
    if n_drift:
        a(f"**{n_drift} name(s) drifted past ±{NAME_PRICE_TOL:.0%}** — refresh with "
          "`python3 BOM/check_stock.py --fix-names`, re-run the consistency check, commit.")
    else:
        a(f"All priced names within ±{NAME_PRICE_TOL:.0%} of live.")
    a("")
    a("---")
    a("*Prices are qty-1 USD list at the checked timestamp; stock numbers age by the hour "
      "— re-run before ordering. Every line here is derived from the design, so the split "
      "between what PCBWay places and what you hand-solder is the one in "
      "`Generated/fabdocs/` (`…-pcbway-assembly.csv` and `…-handbuy-*.csv`), generated by "
      "the same `scripts/bom_split.py` this table is built from.*")

    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"\nwrote {os.path.relpath(OUT)}: "
          f"{n_ok} ok / {n_sub} sub / {n_dead} dead / {n_unk} unknown / {n_man} manual; "
          f"datasheet names: {n_drift} drifted")
    return 1 if n_dead else 0


if __name__ == "__main__":
    sys.exit(main())
