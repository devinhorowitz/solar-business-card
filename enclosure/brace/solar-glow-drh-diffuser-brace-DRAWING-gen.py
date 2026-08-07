#!/usr/bin/env python3
"""2D print/spec sheet for the SOLAR-GLOW DRH resin diffuser brace -> PDF + PNG, ONE SHEET PER
VARIANT (every fit_rules.VARIANTS entry with brace=True: max + lite today).
A drop-in insert (NOT a machined part): the 3D STEP/STL governs geometry; this sheet carries the
print-critical callouts (material, ferrite channel, the H rails, the flat-bottom datum, assembly).
Per-variant numbers (gap/span/name) flow as EXPLICIT arguments from the VARIANTS table into
build() -- never via mutated module state, which from-imports freeze at import (same rule as the
brace CAD generator)."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Polygon as MplPoly
import textwrap

# ---- brace geometry (same single home as solar-glow-drh-diffuser-brace-cad.py) ----
# Geometry comes from enclosure/fit_rules.py. The GAP=1.80 / AIR=0.12 literals that used to sit
# here are GONE on purpose: the local AIR froze at the pre-2026-08-02 value while fit_rules moved
# to 0.22, so the committed sheet's U7 pocket text (1.02 deep / 0.78 ceiling) disagreed with the
# committed STEP (1.12 / 0.68). gap is per-variant now (VARIANTS[v]["cavity"]); AIR/air_for and
# the ferrite channel numbers are imported -- restating any of them is the failure mode.
import os as _o0, sys as _s0
_s0.path.insert(0, _o0.path.join(_o0.path.dirname(_o0.path.abspath(__file__)), ".."))
import fit_rules as _fit                        # noqa: E402
from fit_rules import (AIR, air_for, VARIANTS, FER, FER_CLR,           # noqa: E402
                       FER_POCKET_DEPTH as FER_DEPTH, SLA_WEB, WALL_FIT)
YB = 86.80                                      # page anchor for the plan's y-flip (max cavity N
                                                # wall); real extents come from computed bounds
GLOW = (14.95,40.8,35.85,47.0)                  # monogram-window footprint (LED-hug backing behind it)
U7 = (28.1,37.3,7.8,5.4)                        # U7 (MB85RC512TY FRAM DFN-8) pocket footprint. Re-keyed from the removed U2 balancer, essentially where U2 sat (old (30.10,37.64)).
# Heights come from enclosure/part_heights.py -- the single home, verified against each
# part's 3D model by check_consistency [7]. Nothing on this sheet may restate one.
from part_heights import part_height as _ph     # noqa: E402
from shapely.geometry import Point as _spt      # noqa: E402

def _covered(ref, pieces, span):
    """Is this part actually under the brace at all? Tall parts are stepped around now."""
    for r, poly, h, _s in _fit._cached_parts():
        if r != ref:
            continue
        return (h is not None and h <= span
                and any(g.intersects(poly) for g in pieces))
    return False

def _is_thru(ref, pieces, gap, span):
    """A pocket breaks through only if its blind web would be unprintable. Was hardcoded
    `or ref == "U6"`, which kept printing U6 THRU on this sheet after the footprint started
    stepping around U6 entirely. Depth uses air_for(ref) -- the SAME rule the CAD cuts with."""
    h = _ph(ref)
    return (_covered(ref, pieces, span) and h is not None
            and (gap - (h + air_for(ref))) < SLA_WEB)

def _thru_note(pieces, gap, span, blockers):
    thru = [r for r, _p, _h, _s in _fit._cached_parts() if _is_thru(r, pieces, gap, span)]
    if not thru:
        if _covered("U7", pieces, span):
            u7 = ("U7 IS THE %.2f DFN-8 -- A %.2f BLIND POCKET, %.2f RESIN CEILING."
                  % (_ph("U7"), _ph("U7") + air_for("U7"), gap - (_ph("U7") + air_for("U7"))))
        else:
            u7 = ("U7 (THE %.2f DFN-8) IS TALLER THAN THE %.2f SPAN LIMIT HERE, SO IT IS "
                  "STEPPED AROUND, NOT POCKETED." % (_ph("U7"), span))
        return ("8. ALL COMPONENT POCKETS ARE BLIND. PARTS TALLER THAN %.2f CANNOT BE COVERED AT ALL "
                "(WEB WOULD FALL BELOW %.2f), SO THE FOOTPRINT STEPS AROUND THEM: %s. %s"
                % (span, SLA_WEB, ", ".join(blockers), u7))
    return ("8. THROUGH-POCKETS: %s. OTHERS BLIND. STEPPED AROUND (TOO TALL TO COVER): %s."
            % (" AND ".join(thru), ", ".join(blockers)))

INK="#111111"; GRY="#9a9a9a"; HATCH="#ededed"; PUR="#6a4fb0"; AMB="#c79a2e"

def build(vname):
    v = VARIANTS[vname]
    gap, span, base = v["cavity"], v["span"], v["brace_name"]
    # The plan is the COMPUTED footprint from enclosure/fit_rules.py -- the same geometry the
    # STEP is built from. It used to be five literal rectangles restated here (BX*/RW/RE), which
    # is how a sheet keeps describing a part that changed underneath it.
    pieces = _fit.brace_footprint(span=span)
    BX0,BY0,BX1,BY1 = pieces[0].bounds
    blockers = [r for r, _p in _fit.blockers(span=span)]
    led_hug = _covered("D2", pieces, span)      # lite steps around the 0.83 LEDs entirely
    u7_cov = _covered("U7", pieces, span); u7_thru = _is_thru("U7", pieces, gap, span)
    cav_n = _fit.cavity_rect().bounds[3]
    reach_n = BY1 >= cav_n - WALL_FIT - 0.2     # does the footprint still reach the N wall?

    fig=plt.figure(figsize=(420/25.4,297/25.4))
    ax=fig.add_axes([0,0,1,1]); ax.set_xlim(0,420); ax.set_ylim(0,297)
    ax.set_aspect("equal"); ax.axis("off"); fig.patch.set_facecolor("white")
    ax.add_patch(Rectangle((8,8),404,281,fill=False,ec=INK,lw=1.2))
    ax.add_patch(Rectangle((10,10),400,277,fill=False,ec=INK,lw=0.4))

    def dimh(x0,x1,y,text,fs=6.4,side=1,txtoff=1.4):
        ax.plot([x0,x0],[y,y+1.4*side],lw=0.4,color=INK); ax.plot([x1,x1],[y,y+1.4*side],lw=0.4,color=INK)
        ax.annotate("",xy=(x0,y),xytext=(x1,y),arrowprops=dict(arrowstyle="<|-|>",lw=0.5,color=INK,mutation_scale=7,shrinkA=0,shrinkB=0))
        ax.text((x0+x1)/2,y+txtoff*side,text,ha="center",va="bottom" if side>0 else "top",fontsize=fs,color=INK)
    def dimv(y0,y1,x,text,fs=6.4,side=1,txtoff=1.4):
        ax.plot([x,x+1.4*side],[y0,y0],lw=0.4,color=INK); ax.plot([x,x+1.4*side],[y1,y1],lw=0.4,color=INK)
        ax.annotate("",xy=(x,y0),xytext=(x,y1),arrowprops=dict(arrowstyle="<|-|>",lw=0.5,color=INK,mutation_scale=7,shrinkA=0,shrinkB=0))
        ax.text(x-txtoff*side,(y0+y1)/2,text,ha="right" if side>0 else "left",va="center",fontsize=fs,rotation=90,color=INK)
    def leader(xp,yp,xt,yt,text,ha="left",fs=6.0,va="center"):
        ax.annotate("",xy=(xp,yp),xytext=(xt,yt),arrowprops=dict(arrowstyle="-|>",lw=0.45,color=INK,mutation_scale=7,shrinkA=0,shrinkB=2))
        ax.text(xt+(0.8 if ha=='left' else -0.8),yt,text,ha=ha,va=va,fontsize=fs,color=INK)

    # ===================== PLAN (board-facing face) =====================
    S=1.7; Px,Pbot=40,113
    X=lambda bx:Px+(bx-BX0)*S
    Y=lambda by:Pbot+(YB-by)*S          # flip: y15 (top rails / PV N+P tabs) high on the plan, y74 low
    for _k, _g in enumerate(pieces):
        Hxy=[(X(x),Y(y)) for x,y in _g.exterior.coords]
        ax.add_patch(MplPoly(Hxy,closed=True,fc=HATCH,ec="none",alpha=0.5,zorder=0))
        ax.add_patch(MplPoly(Hxy,closed=True,fill=False,ec=INK,lw=1.1,zorder=3))
        for _ring in _g.interiors:      # blockers fully inside the footprint = real holes in the part
            Rxy=[(X(x),Y(y)) for x,y in _ring.coords]
            ax.add_patch(MplPoly(Rxy,closed=True,fc="white",ec=INK,lw=0.7,zorder=2))
        if _k:      # label the separate piece so nobody assembles it as one part
            _c=_g.centroid
            ax.text(X(_c.x),Y(_c.y),"PIECE %d"%(_k+1),color=INK,ha="center",va="center",
                    fontsize=5.0,fontweight="bold")
    # ferrite OPEN CHANNEL (band; walled on the 12 width, open both y-ends) + the 12x26 ferrite extent
    cxl=max(FER[0]-FER_CLR,BX0+0.2)
    ax.add_patch(Rectangle((X(cxl),Y(BY1)),(BX1-cxl)*S,(BY1-BY0)*S,fc="#efeaf7",ec=PUR,lw=0.9,ls=(0,(4,2))))
    ax.add_patch(Rectangle((X(FER[0]),Y(min(FER[3],BY1))),(FER[2]-FER[0])*S,(min(FER[3],BY1)-max(FER[1],BY0))*S,fc="#d9ccf0",ec=PUR,lw=1.0))
    ax.text(X((FER[0]+FER[2])/2),Y(44.5),"FERRITE\nCHANNEL",ha="center",va="center",fontsize=4.6,color="#3a2b66",fontweight="bold")
    # window LED-hug diffuser backing (band) -- on lite the LEDs are BLOCKERS, so the backing
    # carries open cutouts instead of hugging pockets and the label says so.
    ax.add_patch(Rectangle((X(GLOW[0]),Y(GLOW[3])),(GLOW[2]-GLOW[0])*S,(GLOW[3]-GLOW[1])*S,fc="#fbf5df",ec=AMB,lw=1.0))
    ax.text(X((GLOW[0]+GLOW[2])/2),Y((GLOW[1]+GLOW[3])/2),
            "LED-HUG\nBACKING" if led_hug else "WINDOW\nBACKING\n(LED CUTOUTS)",
            ha="center",va="center",fontsize=4.4,color="#6b5310",fontweight="bold")
    # U7 pocket (band) -- blind, through, or STEPPED AROUND is DERIVED, not asserted; it was
    # drawn as a through-hole for a day after U7 became the 0.90 DFN-8, and its depth text was
    # stale for five days after AIR moved to 0.22 (the local-literal bug this rewrite removes).
    _u7fc = "#f6d6d0" if u7_thru else ("#fdebd0" if u7_cov else "#f2f2f2")
    _u7ec = "#b23b2a" if u7_thru else ("#b8860b" if u7_cov else GRY)
    ax.add_patch(Rectangle((X(U7[0]-U7[2]/2),Y(U7[1]+U7[3]/2)),U7[2]*S,U7[3]*S,
                           fc=_u7fc,ec=_u7ec,lw=0.9,ls="-" if u7_cov else (0,(3,2))))
    ax.text(X(U7[0]),Y(U7[1]),
            "U7\n%s" % ("THRU" if u7_thru else
                        ("%.2f" % (_ph("U7")+air_for("U7")) if u7_cov else "OPEN")),
            ha="center",va="center",fontsize=4.0,
            color="#7a1f12" if u7_thru else ("#6b4e00" if u7_cov else "#555555"))
    # the 4 panel solder tabs the rails back (red stars; drawn only inside this plan's extent)
    TABS=[(4.3,17.0),(46.5,17.0),(4.3,71.9),(46.5,71.9)]
    backed=[t for t in TABS if any(g.distance(_spt(*t)) <= 1.5 for g in pieces)]
    for tx,ty in TABS:
        if ty <= BY1 + 3:
            ax.plot(X(tx),Y(ty),marker="*",ms=8,color="#d23b2a",zorder=6)
    ax.text(X(4.4),Y(23.5),"W\nLEG",ha="center",va="center",fontsize=4.4,color=INK)
    ax.text(X(46.5),Y(23.5),"E\nLEG",ha="center",va="center",fontsize=4.4,color=INK)
    ax.text(X(25.4),272,"BOARD-FACING FACE   SCALE 1.7:1",ha="center",fontsize=8.2,fontweight="bold",color=INK)
    # plan dims + leaders
    dimh(X(BX0),X(BX1),Y(BY1)-3.0,f"{BX1-BX0:.2f}",fs=7,side=-1)
    dimv(Y(BY0),Y(BY1),X(BX0)-3.5,f"{BY1-BY0:.2f}",fs=7,side=1)
    leader(X((FER[0]+FER[2])/2),Y(52.0),X(BX1)+9,Y(52.0)+3,"12.0 WIDE\n(CRITICAL)",ha="left",fs=5.0)
    _lty = 71.9 if 71.9 <= BY1 + 3 else 17.0
    _ltxt = ("LEGS BACK THE 4\nPANEL SOLDER TABS\n(NOTE 4)" if len(backed) == 4 else
             "LEGS BACK %d OF THE 4\nPANEL SOLDER TABS\n(NOTE 4)" % len(backed))
    leader(X(46.5),Y(_lty),X(BX1)+9,Y(_lty)-3,_ltxt,ha="left",fs=5.0)

    # ===================== SECTION B-B (across the brace) =====================
    S2=13.0; EX,EY=244,206
    xl=lambda v_:EX+v_*S2; zl=lambda z:EY+z*S2
    # body outline (bottom z=0 = FLAT datum; top z=gap faces the board)
    ax.add_patch(Rectangle((xl(0),zl(0)),10.5*S2,gap*S2,fc=HATCH,ec=INK,lw=0.9,hatch="\\\\\\\\"))
    # ferrite channel (top recess) at one end
    ax.add_patch(Rectangle((xl(7.2),zl(gap-FER_DEPTH)),3.0*S2,FER_DEPTH*S2,fc="#d9ccf0",ec=PUR,lw=0.7))
    # an LED pocket (depth = h + air_for, the CAD's own rule) -- or, where the LEDs are
    # blockers (lite), the open step-around cutout the footprint carries instead.
    if led_hug:
        _dled = _ph("D2") + air_for("D2")
        ax.add_patch(Rectangle((xl(3.6),zl(gap-_dled)),1.2*S2,_dled*S2,fc="white",ec=INK,lw=0.6))
        leader(xl(4.2),zl(gap-_dled),xl(5.6),zl(gap)+9,"D2-D5 LED POCKETS (hug the LEDs)",ha="left",fs=5.6)
    else:
        ax.add_patch(Rectangle((xl(3.6),zl(0)),1.2*S2,gap*S2,fc="white",ec=INK,lw=0.6,ls=(0,(3,2))))
        leader(xl(4.2),zl(gap/2),xl(5.6),zl(gap)+9,"D2-D5 OPEN (LEDs taller than the span limit -- stepped around)",ha="left",fs=5.6)
    dimv(zl(0),zl(gap),xl(0)-4,f"{gap:.2f}",fs=7,side=1)
    dimv(zl(gap-FER_DEPTH),zl(gap),xl(10.5)+4,f"{FER_DEPTH:.2f} FERRITE",fs=5.6,side=-1,txtoff=1.0)
    ax.annotate("",xy=(xl(0)-1,zl(0)),xytext=(xl(10.5)+1,zl(0)),arrowprops=dict(arrowstyle="-",lw=1.2,color=INK))
    ax.text(xl(5.25),zl(0)-3.2,"FLAT BOTTOM = SANDING DATUM (lap to the height fit; all pockets are on the TOP face)",ha="center",va="top",fontsize=5.6,color=INK,fontweight="bold")
    ax.text(EX+2,EY-13,"SECTION B-B  (typ., across brace)   SCALE 17:1",fontsize=8.5,fontweight="bold",color=INK)
    ax.text(EX+2,EY-18.5,"bottom faces the shell floor • top faces the board back",fontsize=6,color=GRY,style="italic")

    # ===================== NOTES =====================
    ax.text(20,96,"NOTES",fontsize=7.6,fontweight="bold",color=INK)
    notes=[
     "1. PART = SOLAR-GLOW DRH DIFFUSER BRACE [%s]. A DROP-IN INSERT, NOT A FASTENED OR BONDED PART. 3D STEP GOVERNS ALL GEOMETRY; THE STL IS THE PRINT SOURCE." % vname.upper(),
     "2. PROCESS: SLA / RESIN 3D PRINT (e.g. PCBWay). MATERIAL: TOUGH WHITE RESIN. IT MUST BE OPAQUE-WHITE AND NON-CONDUCTIVE - NO CARBON / GRAPHITE-FILLED RESIN",
     "    (WEAKLY CONDUCTIVE): THE BRACE RESTS ON GND / VS / SIGNAL COPPER, SO A DIELECTRIC IS REQUIRED. WHITE ALSO DRIVES THE WINDOW BACKING (NOTE 6).",
     f"3. FIT: PRINT ~0.1 PROUD IN HEIGHT AND SAND THE FLAT BOTTOM (DATUM) DOWN TO A ZERO-AIR FIT IN THE {gap:.2f} CAVITY. ALL POCKETS ARE ON THE TOP FACE, SO THE",
     "    BOTTOM LAPS FLAT ON GLASS WITHOUT TOUCHING THEM. DO NOT SAND THE TOP (IT SETS THE POCKET DEPTHS).",
     f"4. PRECISION FIT, NO RATTLE: THE OUTER EDGES CONTACT THE FLAT CAVITY WALLS AT ~{WALL_FIT:.2f} WHERE THE FOOTPRINT REACHES THEM (COMPUTED EXTENT x {BX0:.2f}-{BX1:.2f},",
     f"    y {BY0:.2f}-{BY1:.2f}; E EDGE STEPPED -- THE PLAN IS THE COMPUTED FOOTPRINT). THE FOUR CORNER BOSSES (r{_fit.BOSS_R:.1f}) + ROUNDED CORNERS ARE RELIEVED (NEED NOT"
     f" FIT). RAILS RUN S->{'N WALL' if reach_n else 'y%.1f (SHORT OF THE N WALL)' % BY1} OUTBOARD OF THE CAPS + BACK {'THE 4' if len(backed)==4 else '%d OF THE 4' % len(backed)} PANEL SOLDER TABS; POCKETS KEY TO THE BOARD.",
     f"5. FERRITE CHANNEL (OVER THE NFC COIL): OPEN-ENDED CHANNEL, WALLED ON THE 12 WIDTH (CRITICAL - EDGE-LIMITED), OPEN AT BOTH Y-ENDS, {FER_DEPTH:.2f} DEEP.",
     "    FERRITE (Wurth WE-FSFS 364006, NOMINAL 12 × 26 mm, EVEN ON THE 2mm SCORE GRID) IS PSA'd IN; LENGTH IS FORGIVING AND MAY OVERHANG THE ENDS SLIGHTLY.",
     ("6. WINDOW = LED-HUG DIFFUSER BACKING: SOLID WHITE RESIN FILLS THE MONOGRAM-WINDOW FOOTPRINT BEHIND THE FR4, MINUS THE TIGHT D2-D5 LED POCKETS."
      if led_hug else
      "6. WINDOW BACKING: SOLID WHITE RESIN FILLS THE MONOGRAM-WINDOW FOOTPRINT BEHIND THE FR4, MINUS OPEN D2-D5 CUTOUTS (THE LEDs EXCEED THE SPAN LIMIT: STEPPED AROUND)."),
     "    NO APERTURE, NO FLOOR TAPE. THE POCKET CLEARANCE DOUBLES AS A RESERVOIR IF A VISCOUS OPTICAL GEL IS PRE-FILLED AT FINAL ASSEMBLY (OPTIONAL).",
     "7. REMOVABLE / NOT BONDED: THE BRACE MUST LIFT OUT FOR NFC C9 TRIM DURING BENCH BRING-UP. KEEP IT DRY-FIT WHILE ITERATING; ADD ANY GEL ONLY ON THE FINAL CARD.",
     # Derived, never restated: this note used to read "U7 TALL AT 1.75", which stayed on the
     # drawing for a day after U7 was corrected to the 0.90 DFN-8 everywhere else. Heights come
     # from enclosure/part_heights.py, so the sentence cannot outlive the number it describes.
     # Wrapped because the per-variant blocker list is variant-sized (lite's is much longer).
     *textwrap.wrap(_thru_note(pieces, gap, span, blockers), width=190, subsequent_indent="    "),
    ]
    yy=91.5
    for n in notes: ax.text(20,yy,n,fontsize=5.9,color=INK); yy-=3.9

    # ===================== TITLE BLOCK =====================
    tb_x,tb_y,tb_w,tb_h=288,12,120,44
    ax.add_patch(Rectangle((tb_x,tb_y),tb_w,tb_h,fill=False,ec=INK,lw=0.9))
    for yl in (tb_y+32,tb_y+23,tb_y+14,tb_y+7.5): ax.plot([tb_x,tb_x+tb_w],[yl,yl],lw=0.4,color=INK)
    ax.plot([tb_x+60,tb_x+60],[tb_y,tb_y+14],lw=0.4,color=INK)
    ax.text(tb_x+tb_w/2,tb_y+38,"SOLAR-GLOW DRH  —  RESIN DIFFUSER BRACE [%s]"%vname.upper(),ha="center",va="center",fontsize=8.0,fontweight="bold",color=INK)
    ax.text(tb_x+3,tb_y+27.5,f"DWG  {base}",fontsize=6.0,va="center",color=INK)
    ax.text(tb_x+tb_w-3,tb_y+27.5,"REV  B",ha="right",fontsize=6.4,va="center",color=INK)
    ax.text(tb_x+3,tb_y+18.5,"MATERIAL  TOUGH WHITE SLA (opaque, non-conductive)",fontsize=5.6,va="center",color=INK)
    ax.text(tb_x+3,tb_y+10.5,"UNITS  mm",fontsize=6.2,va="center",color=INK)
    ax.text(tb_x+63,tb_y+10.5,"SCALE  AS NOTED",fontsize=6.2,va="center",color=INK)
    # envelope is COMPUTED from the footprint bounds (the hand-typed "47.1 x 84.7 x 1.80" is
    # gone -- lite's bounds are genuinely different, its main piece stops well short of N)
    ax.text(tb_x+3,tb_y+3.7,f"ENVELOPE {BX1-BX0:.1f} x {BY1-BY0:.1f} x {gap:.2f}   process: SLA print",fontsize=5.7,va="center",color=INK)
    ax.text(tb_x+tb_w-3,tb_y+3.7,"SHEET 1/1",ha="right",fontsize=6.2,va="center",color=INK)

    # Write next to this script by default (override with $OUT_DIR). This used to be a hardcoded
    # /mnt/user-data/outputs/, which exists only on the machine this was first authored on, so a
    # plain checkout could not regenerate the sheet -- same fix as the backshell generator.
    import os as _o
    _OUT = _o.environ.get("OUT_DIR") or _o.path.dirname(_o.path.abspath(__file__))
    _o.makedirs(_OUT, exist_ok=True)
    # CreationDate=None: matplotlib stamps a write time into the PDF, so an unchanged drawing
    # rewrote itself on every run. That is not cosmetic once CI regenerates these -- a job that
    # commits its outputs would produce a "changed drawing" commit for every board edit that did
    # not touch the drawing at all, and a real change would be invisible among them. PNG carries
    # no such stamp and is already reproducible.
    fig.savefig(_o.path.join(_OUT,base+"-DRAWING.pdf"),facecolor="white",
                metadata={"CreationDate": None})
    fig.savefig(_o.path.join(_OUT,base+"-DRAWING.png"),dpi=150,facecolor="white")
    plt.close(fig)
    if u7_cov:
        print(f"[{vname}] U7 pocket: {_ph('U7')+air_for('U7'):.2f} deep "
              f"(h {_ph('U7'):.2f} + air {air_for('U7'):.2f}), "
              f"{gap-(_ph('U7')+air_for('U7')):.2f} resin ceiling"
              f"{' -- THRU' if u7_thru else ''}")
    else:
        print(f"[{vname}] U7 pocket: NONE -- h {_ph('U7'):.2f} > span {span:.2f}, stepped around")
    print(f"[{vname}] window: {'LED-hug pockets' if led_hug else 'open LED cutouts (stepped around)'}; "
          f"tabs backed {len(backed)}/4")
    print(f"[{vname}] saved {base}-DRAWING.pdf/.png "
          f"(envelope {BX1-BX0:.1f} x {BY1-BY0:.1f} x {gap:.2f})")


# Every variant that HAS a brace gets its sheet, in one run -- same loop as the CAD generator.
# Adding a variant to fit_rules.VARIANTS with a brace_name adds its drawing automatically.
for _vname, _v in VARIANTS.items():
    if _v["brace"]:
        build(_vname)
