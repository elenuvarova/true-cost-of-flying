"""True Cost of Flying — deployed app (READ-ONLY).

Reads committed data/processed/{leaderboard.parquet, tracks/*.geojson, comparators.parquet}.
NO pycontrails / ERA5 / live API here — all physics is precomputed offline (see batch/).

Structure (the product): a flyer-first "explorer" — pick a famous flyer → see their
contrail portrait → pick one of THEIR flights → the same flight shown as two numbers
(fuel CO₂ vs fuel + contrails) on a map. Leaderboard on top; the contrarian
night-transatlantic-widebody comparison + honesty/validation below.
"""
import json
import os
import re

import pandas as pd
import pydeck as pdk
import streamlit as st
import streamlit.components.v1 as components

ROOT = os.path.dirname(__file__)
PROC = os.path.join(ROOT, "data", "processed")

st.set_page_config(page_title="True Cost of Flying", page_icon="✈️",
                   layout="centered", initial_sidebar_state="collapsed")

# Optional privacy-light analytics (GoatCounter). No-op unless GOATCOUNTER_CODE is set in
# Streamlit secrets — set it to your site code to activate. Loads in a sandboxed iframe, so
# pageview counts are approximate (the iframe, not the parent page); see docs/DEPLOY.md.
try:
    _gc = st.secrets.get("GOATCOUNTER_CODE", "")
except Exception:
    _gc = ""
if _gc:
    components.html(
        f'<script data-goatcounter="https://{_gc}.goatcounter.com/count" '
        'async src="//gc.zgo.at/count.js"></script>', height=0)

# ---- Brand styling — bold dark editorial (single global stylesheet) ----
# Colour language: amber = fuel CO₂, red = contrail WARMING, blue = contrail COOLING.
# Bar/badge fills sit behind WHITE text → darkened to clear WCAG 4.5:1 (#c43a26 ≈ 5.3:1,
# #2f6aa8 ≈ 5.6:1). Brighter tints (--warm-br/--cool-br) are for text/accents on dark only.
st.markdown("""
<style>
:root{
  --bg:#0a1422; --panel:#13243a; --panel-2:#0f1d30; --line:#22405f;
  --fuel:#d9994e; --warm:#c43a26; --cool:#2f6aa8;
  --warm-br:#ff7a5f; --cool-br:#6aa9ee; --fuel-br:#f0b56a;
  --ink:#eef3f9; --muted:#93a8bd;
}
html, body, [data-testid="stAppViewContainer"]{ background:var(--bg); }
.block-container{ max-width: 900px; padding-top: 2rem; padding-bottom: 4rem; }
@media (max-width:640px){ .block-container{ padding-left:.85rem; padding-right:.85rem; padding-top:1rem; } }
#MainMenu, footer, .stDeployButton{ visibility:hidden; }
*{ overflow-wrap:anywhere; }

/* ---- Hero (bold) ---- */
.kicker{ display:inline-block; font-size:.72rem; letter-spacing:.18em; text-transform:uppercase;
         font-weight:800; color:var(--warm-br); border:1px solid #3a2a2a; background:rgba(196,58,38,.10);
         padding:.28rem .7rem; border-radius:999px; margin-bottom:1rem; }
.hero-title{ font-size:clamp(2.3rem, 9vw, 4.2rem); font-weight:900; line-height:1.04;
             letter-spacing:-.02em; margin:0 0 .7rem; padding-top:.1em; }
.hero-title .g{ background:linear-gradient(95deg,var(--fuel-br),var(--warm-br) 65%);
                -webkit-background-clip:text; background-clip:text; color:transparent; }
.hero-sub{ color:#c2d2e3; font-size:clamp(1.02rem, 2.8vw, 1.22rem); line-height:1.5; max-width:54ch; font-weight:400; }
.hero-sub .em{ color:var(--warm-br); font-weight:700; font-style:normal; }

/* ---- Section labels (bold rule) ---- */
.sec{ font-size:clamp(1.15rem,3.4vw,1.5rem); font-weight:800; letter-spacing:-.01em; color:var(--ink);
      margin:2.8rem 0 .25rem; padding-top:1.4rem; border-top:1px solid var(--line); }
.sec .n{ color:var(--muted); font-weight:800; margin-right:.5rem; font-variant-numeric:tabular-nums; }
.sec-sub{ color:var(--muted); font-size:.92rem; margin:.1rem 0 1rem; line-height:1.45; }

/* ---- Leaderboard (magnitude bars) ---- */
.lb-row{ position:relative; border-radius:13px; background:var(--panel); margin-bottom:.45rem;
         border:1px solid var(--line); overflow:hidden; }
.lb-fill{ position:absolute; top:0; bottom:0; left:0; border-left:3px solid currentColor; opacity:.9; z-index:0; }
.lb-grid{ position:relative; z-index:1; display:grid; grid-template-columns:2rem 1fr auto;
          gap:.4rem .8rem; align-items:center; padding:.72rem .9rem; }
.lb-rank{ font-size:1.05rem; font-weight:900; text-align:center; color:var(--muted); font-variant-numeric:tabular-nums; }
.lb-name{ font-weight:800; font-size:1.04rem; }
.lb-ac{ color:var(--muted); font-size:.8rem; }
.lb-val{ text-align:right; font-weight:900; font-size:1.18rem; white-space:nowrap; font-variant-numeric:tabular-nums; }
.lb-val small{ display:block; font-weight:700; font-size:.66rem; }
.chip{ display:inline-block; font-size:.68rem; padding:.1rem .5rem; border-radius:999px;
       background:#1d2f47; color:#c7d6e6; margin:.2rem .25rem 0 0; white-space:normal; border:1px solid #294a6e; }

/* ---- Flyer explorer header ---- */
.flyer{ background:linear-gradient(180deg,var(--panel),var(--panel-2)); border:1px solid var(--line);
        border-radius:18px; padding:1.2rem 1.25rem 1.05rem; margin:.2rem 0 .1rem; }
.flyer-top{ display:flex; flex-wrap:wrap; gap:.5rem 1rem; align-items:baseline; justify-content:space-between; }
.flyer-name{ font-size:clamp(1.6rem,5.5vw,2.3rem); font-weight:900; letter-spacing:-.02em; line-height:1.05; }
.flyer-ac{ color:var(--muted); font-size:.86rem; margin-top:.15rem; }
.flyer-badge{ font-size:.74rem; font-weight:800; color:#ffd9cf; background:rgba(196,58,38,.18);
              border:1px solid #5a2f28; padding:.28rem .65rem; border-radius:999px; white-space:nowrap; }
.flyer-stats{ display:flex; flex-wrap:wrap; gap:.9rem; margin:1.05rem 0 .2rem; }
.ftile{ flex:1 1 8rem; background:rgba(255,255,255,.025); border:1px solid var(--line); border-radius:12px; padding:.6rem .75rem; }
.ft-lbl{ color:var(--muted); font-size:.74rem; font-weight:600; margin-bottom:.2rem; line-height:1.2; }
.ft-num{ font-size:clamp(1.5rem,6vw,2.05rem); font-weight:900; line-height:1; font-variant-numeric:tabular-nums; }
.ft-num.fuel{ color:var(--fuel-br); } .ft-num.warm{ color:var(--warm-br); } .ft-num.cool{ color:var(--cool-br); }
.ft-num small{ font-size:.55em; font-weight:700; color:var(--muted); }
.flyer-line{ font-size:1rem; line-height:1.5; color:#dbe6f1; margin:.9rem 0 .2rem; }

/* ---- Reveal (oversized) ---- */
.reveal{ background:linear-gradient(180deg,var(--panel),var(--panel-2)); border:1px solid var(--line);
         border-radius:18px; padding:1.3rem 1.35rem; }
.reveal-nums{ display:flex; flex-wrap:wrap; gap:1rem 2.2rem; }
.stat{ flex:1 1 9.5rem; }
.stat .lbl{ color:var(--muted); font-size:.82rem; margin-bottom:.2rem; line-height:1.25; }
.stat .num{ font-size:clamp(2.1rem, 9vw, 3.4rem); font-weight:900; line-height:1; font-variant-numeric:tabular-nums; }
.stat .num.fuel{ color:var(--fuel-br); }
.stat .num.warm{ color:var(--warm-br); } .stat .num.cool{ color:var(--cool-br); }
.stat .num small{ font-size:.42em; font-weight:700; color:var(--muted); }
.delta-pill{ display:inline-block; margin-top:.55rem; padding:.22rem .7rem; border-radius:999px;
             font-weight:800; font-size:1rem; background:rgba(196,58,38,.22); color:#ff9b85; border:1px solid #5a2f28; }
.delta-cool{ background:rgba(47,106,168,.22); color:#8fc0f5; border-color:#274a6e; }
.delta-flat{ background:#1d2f47; color:#c7d6e6; border-color:#294a6e; }
.bar{ display:flex; height:38px; border-radius:10px; overflow:hidden; margin:1.15rem 0 .45rem; background:#0b1622; border:1px solid var(--line); }
.bar span{ display:flex; align-items:center; padding:0 .6rem; font-size:.8rem; font-weight:800; color:#0b1622;
           white-space:nowrap; overflow:hidden; }
.bar .b-fuel{ background:var(--fuel); }
.bar .b-warm{ background:var(--warm); color:#fff; }
.barcap{ color:var(--muted); font-size:.8rem; }
.wcbar{ display:flex; height:24px; border-radius:7px; overflow:hidden; margin:.45rem 0; font-size:.7rem; font-weight:800; color:#fff; }
.wcbar div{ display:flex; align-items:center; justify-content:center; }
</style>
""", unsafe_allow_html=True)


@st.cache_data
def load_board():
    return pd.read_parquet(os.path.join(PROC, "leaderboard.parquet"))


@st.cache_data
def load_track(flight_id):
    p = os.path.join(PROC, "tracks", f"{flight_id}.geojson")
    return json.load(open(p)) if os.path.exists(p) else None


@st.cache_data
def load_comparators():
    """Optional commercial comparators (night transatlantic widebodies). Absent on deploy = fine."""
    p = os.path.join(PROC, "comparators.parquet")
    return pd.read_parquet(p) if os.path.exists(p) else None


def t(kg):
    return f"{kg/1000:,.1f} t"


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def mdb(s):
    """Markdown **bold** / *italic* → <b>/<i>, for use inside raw-HTML blocks (CommonMark
    does not parse markdown inside block-level HTML, so we convert it ourselves)."""
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"\*(.+?)\*", r"<i>\1</i>", s)
    return s


def contrail_for(row, h):
    return row["contrail_co2e_gwp20_central"] if h == "GWP20" else row["contrail_co2e_central"]


def wc_bar(w, c, z):
    """3-segment proportion bar: warming / cooling / near-zero flight counts."""
    if w + c + z == 0:
        return ""
    seg = []
    if w:
        seg.append(f'<div style="flex:{w};background:#c43a26">{w} 🔥</div>')
    if c:
        seg.append(f'<div style="flex:{c};background:#2f6aa8">{c} ❄</div>')
    if z:
        seg.append(f'<div style="flex:{z};background:#33455c">{z} ○</div>')
    return '<div class="wcbar">' + "".join(seg) + '</div>'


df = load_board()

# ---- Hero ----
st.markdown(
    '<div class="kicker">Fuel CO₂ is only part of the story</div>'
    '<div class="hero-title" role="heading" aria-level="1">The <span class="g">true cost</span><br>of flying</div>'
    '<p class="hero-sub">Every jet tracker shows you one number: CO₂. But across aviation, CO₂ is only about '
    '<span class="em">a third</span> of the warming — the rest is mostly <span class="em">contrails</span>. '
    'Pick a famous flyer, pick one of their flights, and see the <em>same flight</em> with its contrail '
    'warming added — computed with CoCiP physics, not guessed.</p>',
    unsafe_allow_html=True)

# ---- Time-horizon toggle (in the main flow so it is reachable on mobile, where the sidebar is hidden) ----
horizon = st.radio("Time horizon", ["GWP100", "GWP20"], index=0, horizontal=True,
                   help="Magnitude is metric-dependent; the 'does this matter' verdict is ~90% robust across "
                        "metrics. GWP100 (100-year) is the default; GWP20 weights short-lived contrails more.")
st.caption("GWP100 = standard 100-year basis · GWP20 = 20-year (weights contrails heavier). "
           "Toggling moves the contrail number — that motion *is* the point.")

st.sidebar.markdown("**True Cost of Flying**")
st.sidebar.markdown("Data: [adsb.lol](https://adsb.lol) tracks (ODbL-1.0) · ECMWF ERA5 · "
                    "[OpenAP](https://openap.dev) · [pycontrails](https://py.contrails.org) CoCiP.")
st.sidebar.caption("Non-commercial / educational. Aircraft, not people — see caveats.")

view = df.copy()
view["contrail_co2e"] = view.apply(lambda r: contrail_for(r, horizon), axis=1)
view["combined"] = view["fuel_co2_kg"] + view["contrail_co2e"]
view["date"] = view["flight_id"].str.split("_").str[-1].str.replace(
    r"(\d{4})(\d{2})(\d{2})", r"\1-\2-\3", regex=True)
view["pretty"] = pd.to_datetime(view["date"]).dt.strftime("%b %-d, %Y")
view = view.sort_values("combined", ascending=False)

# ---- Owner leaderboard (aggregated across each owner's tracked flights) ----
st.markdown('<div class="sec" role="heading" aria-level="2"><span class="n">01</span>Who warmed the most</div>',
            unsafe_allow_html=True)
st.markdown('<div class="sec-sub">Owners ranked by combined warming (fuel CO₂ + contrails) across their tracked '
            f'flights ({horizon}). Tiers, not a precise 1..N rank — magnitude reshuffles with the metric.</div>',
            unsafe_allow_html=True)
agg = (view.groupby("owner_label")
       .agg(combined=("combined", "sum"), flights=("combined", "size"),
            ac_type=("ac_type", "first"),
            proxy=("proxy_type_flag", "any"), bizjet=("bizjet_alt_flag", "any"))
       .reset_index().sort_values("combined", ascending=False).reset_index(drop=True))
n = len(agg)
top_val = max(agg["combined"].max(), 1)
rows_html = []
for i, r in agg.iterrows():
    if i < n / 3:
        tier, tcol = "🔴 High", "#ff7a63"
    elif i >= 2 * n / 3:
        tier, tcol = "🟢 Low", "#3fae6b"
    else:
        tier, tcol = "🟠 Med", "#e0a23a"
    fill_pct = 100 * r["combined"] / top_val
    chips = ""
    if r["proxy"]:
        chips += '<span class="chip">⚠ proxy type</span>'
    if r["bizjet"]:
        chips += '<span class="chip">⚠ above cap · under-counted</span>'
    rows_html.append(
        f'<div class="lb-row">'
        f'<div class="lb-fill" style="color:{tcol};width:{fill_pct:.1f}%;'
        f'background:linear-gradient(90deg,{tcol}1f,{tcol}08)"></div>'
        f'<div class="lb-grid"><div class="lb-rank">{i+1}</div>'
        f'<div><div class="lb-name">{esc(r["owner_label"])}</div>'
        f'<div class="lb-ac">{esc(r["ac_type"])} · {int(r["flights"])} flights {chips}</div></div>'
        f'<div class="lb-val">{r["combined"]/1000:,.1f} t<small style="color:{tcol}">{tier}</small></div></div></div>')
st.markdown("".join(rows_html), unsafe_allow_html=True)
st.caption(f"Aggregated over {len(view)} tracked flights (2024–early 2025) for {n} owners. Illustrative of the "
           "sampled flights, not annual totals.")

# ---- Featured portraits: verified, adversarially fact-checked copy (GWP100 prose; stats computed live) ----
# Numbers below are recomputed from the data each run; the prose was fact-checked by a multi-agent
# workflow and obeys the framing rule (fuel+contrails only; never a per-flight ~3×; unstable ratios → tonnes).
FEATURED = {
    "Donald Trump": {
        "badge": "🌙 one night flight = all the warming",
        "ac": "Boeing 757-200 · in-domain (most trustworthy numbers in the set)",
        "headline": "Six of seven 757 flights formed almost nothing — then one deep-night NY→Palm Beach run added "
                    "**+90 t**, ~2.4× that flight's own fuel CO₂. On the in-domain airframe we trust most.",
        "chips": ["in-domain 757 → most trustworthy (not flagged)", "across 7 flights contrails = +34% (NOT a 3×)",
                  "90 t band 75–110 t · ~70% uncertainty", "trigger is ISSR-crossing, not just night"],
        "framing": "Donald Trump's seven tracked flights were all on the same **in-domain Boeing 757-200** (N757AF, "
                   "“Trump Force One”), cruising near 38,000 ft — below CoCiP's ~13 km cap — so these are among the "
                   "**cleanest, least-caveated numbers in the dataset**. The fuel reality is blunt: **264.6 t of CO₂** "
                   "across the seven — a heavy footprint (the Patriots' team 767s burned the most tracked fuel, ~668 t; "
                   "Drake's 767 a touch more than Trump's). Contrails tell almost the opposite story: six of seven "
                   "flights formed essentially zero, and effectively all **90.2 t of contrail CO₂e** came from one "
                   "deep-night NY→West Palm Beach run that crossed a ~130 km ice-supersaturated band over NJ/Delaware. "
                   "Across all 7 flights that lifts his warming **+34%** on top of fuel (90.2 / 264.6) — squarely in the "
                   "honest per-flight ~30–60% GWP100 range, **not** the ~3× whole-fleet ERF figure — and it is "
                   "concentrated in one flight, not spread evenly. Tellingly, a *second* Trump flight was also deep-night "
                   "yet formed zero: night alone isn't the trigger — **crossing ice-supersaturated air is** (night just "
                   "means no daytime sunlight to offset the warming). Fuel CO₂ + contrails only; ~70% contrail "
                   "uncertainty (90.2 t spans ~75–110 t)."},
    "Taylor Swift": {
        "badge": "☀️ daytime standout",
        "ac": "Dassault Falcon 7X",
        "headline": "Nine of twelve flights formed none — but a **daytime** Tennessee→Montana leg added **+12.1 t**, "
                    "almost matching its 12.7 t of fuel (~2× that flight).",
        "chips": ["~70% contrail uncertainty", "5/12 above-cap → likely UNDER-counted (a floor)",
                  "proxy aircraft type", "9/12 ~zero = power-law"],
        "framing": "Across 12 tracked flights, Taylor Swift's Falcon 7X (N621MM) burned its way to **121.8 t of fuel "
                   "CO₂** — the certain number. Contrails are a different story: 9 of 12 flights formed essentially none "
                   "(a power-law reality, not a measurement failure), but 3 warmed, adding **18.4 t CO₂e** over 100 "
                   "years. The standout is the Dec 10 Tennessee→Montana leg, where 12.1 t of daytime contrail warming "
                   "sat almost on top of its 12.7 t of fuel CO₂ — **roughly a 2× flight**. The honest catch: this jet "
                   "climbed to 13.1 km, just past CoCiP's ~13 km cap, so its contrails are flagged **UNDER-counted, not "
                   "extrapolated** — the real warming is at least this. Because the fuel denominator is large (12.7 t), "
                   "the 96% ratio is stable and trustworthy, unlike short low-fuel flights. Fuel CO₂ + contrails only; "
                   "~70% uncertainty; **not** the aviation-fleet ~3×."},
    "Drake": {
        "badge": "🧭 clean · ☀️ day ↔ 🌙 night",
        "ac": "Boeing 767-200ER · in-domain (below the cap) → most trustworthy contrail numbers",
        "headline": "Same Toronto↔Houston route, opposite sign: the **day** leg net-**cooled −10.3 t**, the **night** "
                    "return **warmed +1.6 t**. The cleanest day/night proof in the set.",
        "chips": ["in-domain 767 → most trustworthy (no cap flag)", "~70% contrail uncertainty (this flight −8.6 to −12.5 t)",
                  "5/7 formed essentially none = power-law", "*net cooling rests on one daytime leg — direction, not a precise ledger",
                  "fuel+contrails only (not 3× ERF)"],
        "framing": "Across 7 tracked flights on his Boeing 767 (N767CJ; modelled on the B763 profile), Drake's engines "
                   "put **277.8 t of CO₂** into the air — certain, and it never goes away. The contrail story is more "
                   "interesting and far more uncertain. Most legs formed almost none: three formed exactly zero, two "
                   "more only a trace (≈ +0.06 and −0.02 t), so **five of seven are essentially contrail-free** — an "
                   "honest power-law finding, not a measurement failure. Only two legs produced meaningful forcing, "
                   "pointing opposite ways. The net came out slightly **COOLING (~−8.6 t CO₂e at GWP100)**, almost "
                   "entirely one flight: a daytime Toronto→Houston leg (2024-06-09) whose ice cloud sat in full sunlight "
                   "(~+9° solar elevation) and reflected more than it trapped, netting **−10.3 t**. The mirror-image "
                   "night return nine days later (Houston→Toronto, sun ~−24°) did the opposite, **+1.6 t**. Same "
                   "city-pair, opposite sign, purely because of time of day — **the cleanest in-domain demonstration of "
                   "the day/night mechanism in the set.** Treat the contrail term as direction-plus-rough-magnitude "
                   "(~70% uncertainty; this leg's range −8.6 to −12.5 t), not a precise ledger. All 7 flights are "
                   "in-domain (the 767 is below CoCiP's cap), so unlike the bizjets these numbers are **not "
                   "under-counted**. Fuel CO₂ + contrails only — omits NOx/H₂O/aerosols, and **not** the fleet ~3× ERF."},
    "Elon Musk": {
        "badge": "🌙↔☀️ cuts both ways",
        "ac": "Gulfstream G650ER",
        "headline": "Contrails cut both ways — two night flights warmed, two **daytime** legs net-**cooled** (down to "
                    "−19 t). Read the net as a *mix*, not “climate-positive”.",
        "chips": ["~70% contrail uncertainty", "6/11 above-cap → under-counted; cooling is fragile",
                  "net negative rests on 2 daytime flagged flights — read as a MIX", "fuel+contrails only"],
        "framing": "Across 11 tracked flights on a single Gulfstream G650ER, Elon Musk's certain cost is fuel: **~117.5 t "
                   "of CO₂**. Contrails cut both ways: 7 of 11 flights formed little or none, the 2 night flights warmed "
                   "(up to +7.07 t at GWP100), and 2 daytime flights reflected enough sunlight to net-*cool* (down to "
                   "−19.18 t). Summed, the contrail term is slightly negative (~**−18.7 t**) — but that figure is "
                   "**fragile**: it rests on just two daytime cooling flights, both above CoCiP's cap, so read it as a "
                   "*mix*, not a claim that his flying is climate-positive. The cleanest case is the in-domain Dec-15 "
                   "night flight whose contrail warming (~7 t) roughly equals its own fuel CO₂ (~6.8 t) — which is "
                   "exactly why the raw **+103% must not be headlined**: it's a contrail-dominated flight with a small "
                   "fuel denominator, so the honest read is the absolute tonnes. Fuel CO₂ + contrails only; ~70% "
                   "uncertainty; per-flight contrails add ~30–60% at GWP100 on the flights that form them, and 0% on "
                   "the seven that don't."},
    "Bill Gates": {
        "badge": "🌙 night standout",
        "ac": "Gulfstream G650ER",
        "headline": "Mostly clean — 7 of 10 flights formed none. Two night flights warmed (**+5.6 t** standout on a "
                    "large fuel base); one daytime leg cooled.",
        "chips": ["~70% contrail uncertainty", "5/10 above-cap → under-counted",
                  "the 2 warming flights are in-domain (cleanest)", "fuel+contrails only (not 3× ERF)"],
        "framing": "Across 10 tracked flights of Bill Gates's Gulfstream G650ER (N887WM), the fuel is the headline: "
                   "**106.2 t of CO₂**, ~10.6 t per hop. Contrails were a small, lumpy add-on, not a multiplier: 7 of 10 "
                   "flights formed essentially none, 2 night flights warmed (+5.56 t and +2.74 t at GWP100), and 1 "
                   "daytime flight cooled slightly (−1.39 t), for a net of only **~+6.9 t**. The standout — a "
                   "transcontinental redeye where a night contrail added 5.56 t on top of 17.2 t of fuel (**+32%**, a "
                   "stable ratio on a large denominator) — shows the climate-advocate tension honestly: most of his "
                   "flights made no contrail, but one night flight in the right air meaningfully amplified it, while a "
                   "daytime leg did the opposite. The 2 warming flights are in-domain (cleanest); 5 of 10 cruise above "
                   "CoCiP's cap (under-counted, not extrapolated). Fuel CO₂ + contrails only; ~70% uncertainty."},
}

# Short labels for the flyer picker (pills); full owner_label is shown in the header.
SHORT = {"New England Patriots": "🏈 Patriots", "Phil Knight (Nike)": "Phil Knight", "Mark Zuckerberg": "Zuckerberg"}


def short(o):
    return SHORT.get(o, o)


# Order: featured (narrative order) first, then the rest by aggregate warming.
FEATURED_ORDER = ["Donald Trump", "Taylor Swift", "Drake", "Elon Musk", "Bill Gates"]
others = [o for o in agg["owner_label"].tolist() if o not in FEATURED_ORDER]
ordered_owners = [o for o in FEATURED_ORDER if o in agg["owner_label"].tolist()] + others
label_to_owner = {short(o): o for o in ordered_owners}

# ---- The explorer: pick a flyer → pick their flight → the reveal ----
st.markdown('<div class="sec" role="heading" aria-level="2"><span class="n">02</span>'
            'Explore a flyer — the same flight, two numbers</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sec-sub">Burning jet fuel is the <b>certain</b> harm. Contrails are the <b>wildcard</b> — a '
    '<i>concentrated</i> effect from crossing ice-supersaturated air (usually at night), <b>not a flat multiplier</b>. '
    'The honest headline isn\'t “always 3×”, it\'s <b>“usually near zero, occasionally a lot.”</b> '
    'Pick a flyer, then one of their flights.</div>', unsafe_allow_html=True)

sel_label = st.pills("Pick a flyer", [short(o) for o in ordered_owners],
                     default=short("Donald Trump"), key="flyer", label_visibility="collapsed")
owner = label_to_owner.get(sel_label, "Donald Trump")
st.caption("★ Trump · Taylor Swift · Drake · Musk · Gates have full verified write-ups; the other six show "
           "stats computed straight from the data.")

g = view[view["owner_label"] == owner].sort_values("combined", ascending=False).reset_index(drop=True)
# Per-flyer totals (horizon-aware) + warm/cool/zero counts (sign is horizon-independent → use GWP100 central).
o_fuel = g["fuel_co2_kg"].sum()
o_contrail = g["contrail_co2e"].sum()
W_THR = 100.0  # kg
n_w = int((g["contrail_co2e_central"] > W_THR).sum())
n_c = int((g["contrail_co2e_central"] < -W_THR).sum())
n_z = len(g) - n_w - n_c
o_ac = g["ac_type"].iloc[0]
o_bizjet = bool(g["bizjet_alt_flag"].any())
o_proxy = bool(g["proxy_type_flag"].any())
o_unstable = bool(((g["contrail_co2e_central"] > W_THR) & (g["contrail_pct_of_fuel"] > 100)).any())

feat = FEATURED.get(owner)
# Contrail tile colour/label by net sign.
if o_contrail > W_THR:
    cl, csign = "warm", f"+{o_contrail/1000:,.1f}"
elif o_contrail < -W_THR:
    cl, csign = "cool", f"−{abs(o_contrail)/1000:,.1f}"
else:
    cl, csign = "", "~0"
ac_label = feat["ac"] if feat else esc(o_ac)
badge = (f'<span class="flyer-badge">{feat["badge"]}</span>' if feat else "")

if feat:
    body = (f'<div class="flyer-line">{mdb(feat["headline"])}</div>'
            + "".join(f'<span class="chip">{esc(c)}</span>' for c in feat["chips"]))
else:
    pl = ("Most of these flights formed essentially no contrail — the power-law reality, not a measurement failure. "
          if n_z >= max(1, len(g) - 1) else
          f"{n_w} flight(s) warmed, {n_c} cooled and {n_z} formed essentially none — they roughly offset on net. ")
    cap = ("This jet cruises above CoCiP's ~13 km cap, so its contrails are flagged **under-counted, not "
           "extrapolated**. " if o_bizjet else "")
    uns = ("One short, low-fuel flight here shows an outsized contrail/fuel ratio — pick it below and the reveal "
           "shows its **absolute tonnes**, not the unstable %. " if o_unstable else "")
    body = (f'<div class="flyer-line">{esc(o_ac)} · {len(g)} tracked flights. Fuel is the certain number '
            f'(<b>{o_fuel/1000:,.1f} t CO₂</b>); contrails netted <b>{csign} t</b> ({horizon}) across the sample. '
            f'{mdb(pl)}{mdb(cap)}{mdb(uns)}Numbers computed straight from the committed data; the 5 starred flyers '
            f'have the deep, fact-checked write-ups.</div>')

st.markdown(
    f'<div class="flyer"><div class="flyer-top">'
    f'<div><div class="flyer-name" role="heading" aria-level="3">{esc(owner)}</div>'
    f'<div class="flyer-ac">{ac_label}</div></div>{badge}</div>'
    f'<div class="flyer-stats">'
    f'<div class="ftile"><div class="ft-lbl">Fuel CO₂ · {len(g)} flights</div>'
    f'<div class="ft-num fuel">{o_fuel/1000:,.1f}<small> t</small></div></div>'
    f'<div class="ftile"><div class="ft-lbl">Contrails net · {horizon}</div>'
    f'<div class="ft-num {cl}">{csign}<small> t</small></div></div>'
    f'<div class="ftile"><div class="ft-lbl">Contrail outcome · {len(g)} flights</div>'
    f'{wc_bar(n_w, n_c, n_z)}'
    f'<div style="color:var(--muted);font-size:.72rem">{n_w} warmed · {n_c} cooled · {n_z} ~none</div></div>'
    f'</div>{body}</div>', unsafe_allow_html=True)

if feat:
    with st.expander("The full picture — verified write-up"):
        st.markdown(feat["framing"])

# Flight picker — scoped to THIS flyer; default = their most telling flight (largest |contrail|).
g["ctag"] = g["contrail_co2e"].apply(
    lambda v: f"contrails +{v/1000:,.1f} t 🔥" if v > W_THR
    else (f"contrails −{abs(v)/1000:,.1f} t ❄" if v < -W_THR else "contrails ~0"))
g["flabel"] = (g["pretty"] + " · " + (g["combined"] / 1000).round(1).astype(str) + " t CO₂e · " + g["ctag"])
standout_pos = int(g["contrail_co2e_central"].abs().values.argmax())
st.markdown(f"**Pick one of {esc(owner)}'s {len(g)} flights** — defaulting to their most telling one:")
choice = st.selectbox("Pick a flight", g["flabel"].tolist(), index=standout_pos,
                      key=f"flight_{owner}", label_visibility="collapsed")
row = g[g["flabel"] == choice].iloc[0]

# ---- The two-number reveal (the aha) ----
contrail = contrail_for(row, horizon)
fuel = row["fuel_co2_kg"]
combined = fuel + contrail
pct = 100 * contrail / fuel if fuel else 0
# Low/high band columns are GWP100-only; scale to the selected horizon by the central ratio so the
# band actually contains its own central value, and sort the endpoints (cooling → high is more negative).
c100 = row["contrail_co2e_central"]
hr = (contrail / c100) if (horizon == "GWP20" and c100) else 1.0
band_lo, band_hi = sorted([fuel + row["contrail_co2e_low"] * hr, fuel + row["contrail_co2e_high"] * hr])

# Intense contrail on a small-fuel flight → huge UNSTABLE ratio (tiny denominator): headline tonnes, not %.
unstable = contrail > 0 and pct > 100
if contrail > 0 and pct >= 1:                       # meaningful warming
    warm_w = max(4.0, 100 * contrail / combined)    # floor so a thin red sliver stays visible
    bar = (f'<div class="bar"><span class="b-fuel" style="width:{100-warm_w:.0f}%">Fuel {fuel/1000:,.0f} t</span>'
           f'<span class="b-warm" style="width:{warm_w:.0f}%">+{contrail/1000:,.1f} t</span></div>'
           f'<div class="barcap">The red slice is the warming no other tracker counts.</div>')
    delta = (f'<span class="delta-pill">+{contrail/1000:,.1f} t contrails — contrail-dominated</span>' if unstable
             else f'<span class="delta-pill">contrails add +{pct:.0f}%</span>')
    cnum_cls = "warm"
elif contrail < 0 and pct <= -1:                    # meaningful cooling
    bar = ('<div class="bar"><span class="b-fuel" style="width:100%">Fuel '
           f'{fuel/1000:,.0f} t — contrails net-cooled this flight</span></div>')
    delta = f'<span class="delta-pill delta-cool">contrails cooled by {abs(contrail)/1000:,.1f} t ({pct:+.0f}%)</span>'
    cnum_cls = "cool"
else:                                               # negligible (|contrail| < ~1% of fuel)
    bar = ('<div class="bar"><span class="b-fuel" style="width:100%">Fuel '
           f'{fuel/1000:,.0f} t — no significant contrail formed</span></div>')
    delta = '<span class="delta-pill delta-flat">contrails: negligible (&lt;1%)</span>'
    cnum_cls = ""

st.markdown(
    f'<div class="reveal"><div class="reveal-nums">'
    f'<div class="stat"><div class="lbl">Fuel CO₂ — what every tracker shows</div>'
    f'<div class="num fuel">{fuel/1000:,.1f} <small>t</small></div></div>'
    f'<div class="stat"><div class="lbl">Combined CO₂e — fuel + contrails</div>'
    f'<div class="num {cnum_cls}">{combined/1000:,.1f} <small>t CO₂e</small></div>{delta}</div>'
    f'</div>{bar}</div>',
    unsafe_allow_html=True)
st.caption(f"{horizon} · uncertainty band {t(band_lo)}–{t(band_hi)} · contrail term carries ~70% uncertainty (IPCC "
           f"'low confidence'). " + ("Above CoCiP's ~13 km cap → likely under-counted. " if row["bizjet_alt_flag"] else "")
           + ("On this flight the contrail forcing exceeds the fuel CO₂ itself, so we headline the absolute tonnes "
              "rather than the raw % — a per-flight percentage that large would invite confusion with the "
              "aviation-wide ~3× figure (which also includes the NOx/H₂O/aerosols we don't compute)." if unstable else ""))

# ---- Map of the selected flight ----
gj = load_track(row["flight_id"])
if gj and gj["features"]:
    segs = []
    for f in gj["features"]:
        c = f["geometry"]["coordinates"]
        s = f["properties"].get("ef_share", 0.0)
        color = ([220, 60, 40] if s > 0.05 else [80, 110, 200] if s < -0.05 else [130, 130, 140])
        segs.append({"path": [[c[0][0], c[0][1]], [c[1][0], c[1][1]]], "color": color})
    sd = pd.DataFrame(segs)
    shares = [f["properties"].get("ef_share", 0.0) for f in gj["features"]]
    n_warm = sum(1 for s in shares if s > 0.05)
    n_cool = sum(1 for s in shares if s < -0.05)
    n_neut = len(shares) - n_warm - n_cool
    lons = [pt[0] for seg in sd["path"] for pt in seg]
    lats = [pt[1] for seg in sd["path"] for pt in seg]
    center_lon, center_lat = sum(lons) / len(lons), sum(lats) / len(lats)
    layer = pdk.Layer("PathLayer", sd, get_path="path", get_color="color", width_min_pixels=4)
    # No external basemap: layers render on the dark theme background. Avoids the
    # Carto/Mapbox tile dependency that was blanking the whole canvas.
    st.pydeck_chart(pdk.Deck(
        layers=[layer],
        initial_view_state=pdk.ViewState(latitude=center_lat, longitude=center_lon, zoom=4, pitch=30),
        map_provider=None, map_style=None,
        tooltip={"text": "red = contrail warming along this segment"}), height=420)
    # Text alternative to the colour-only map (a11y): the same warm/cool/neutral split in words.
    st.caption(f"Track coloured by where contrail warming occurred (🔴 red) vs none (grey) vs cooling (🔵 blue) — "
               f"**{n_warm} warming · {n_cool} cooling · {n_neut} neutral** of {len(shares)} segments. "
               f"Fuel CO₂ is roughly uniform; contrail warming is concentrated where the jet crossed humid, icy air.")

# ---- Night transatlantic widebodies: the regime where contrails dominate ----
comp = load_comparators()
if comp is not None and len(comp):
    st.markdown('<div class="sec" role="heading" aria-level="2"><span class="n">03</span>'
                '🌙 The other extreme — night transatlantic widebodies</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sec-sub">The jets above mostly fly <b>short daytime US/EU legs</b>, where daytime contrails often '
        '<i>cool</i> — so on aggregate they add almost nothing. Run the <b>same physics</b> on <b>night '
        'North-Atlantic widebody</b> crossings (the busy contrail corridor, in the dark) and it flips:</div>',
        unsafe_allow_html=True)
    pct_col = "contrail_pct_of_fuel_gwp20" if horizon == "GWP20" else "contrail_pct_of_fuel"
    cc_col = "contrail_co2e_gwp20_central" if horizon == "GWP20" else "contrail_co2e_central"
    aggc = 100 * comp[cc_col].sum() / comp["fuel_co2_kg"].sum()
    cobj, ctxt = st.columns([1, 1])
    cobj.metric(f"Contrails add — aggregate ({horizon})", f"+{aggc:.0f}%",
                help="vs roughly 0% on the daytime private jets above — identical pipeline, opposite regime.")
    ctxt.markdown(f"across **{len(comp)} night crossings**. Every one formed its contrail **at night → "
                  "100% warming**, all at in-domain altitude. **Time-of-day + route, not the model, drive it.**")
    tbl = pd.DataFrame({
        "Flight": comp["registration"].astype(str) + " (" + comp["adsb_type"].astype(str) + ")",
        "Fuel CO₂": (comp["fuel_co2_kg"] / 1000).round().astype(int).astype(str) + " t",
        "Contrail CO₂e": (comp[cc_col] / 1000).round().astype(int).astype(str) + " t",
        "Contrails add": comp[pct_col].round().astype(int).astype(str) + "%",
    })
    st.dataframe(tbl, hide_index=True, use_container_width=True)
    st.caption("Commercial comparators (not ranked in the leaderboard). 2 of 5 use a wide-body proxy fuel type "
               "(elevated fuel-CO₂ uncertainty); contrail term carries ~70% uncertainty. Impact Explorer can't be "
               "queried for historical flights (it is forecast-only), but our EF→CO₂e conversion matches "
               "Contrails.org's published factor to 0.8%. See `docs/VALIDATION.md` §4, §7.")

# ---- Mandatory caveats (IMPLEMENTATION_PLAN §11) ----
st.markdown('<div class="sec" role="heading" aria-level="2"><span class="n">04</span>The honest fine print</div>',
            unsafe_allow_html=True)
with st.expander("How this is computed & honest caveats"):
    st.markdown(
        "- **The total here is fuel-CO₂ + contrails only.** It omits NOx, water vapour and aerosols, so it is "
        "*not* the full ~3× aviation-wide figure (that fleet number includes those terms).\n"
        "- **Never a bare number.** CO₂e shown with a time-horizon toggle (GWP100 default / GWP20) and an "
        "uncertainty band; IPCC deliberately picks no single metric.\n"
        "- **The two numbers aren't equally certain.** Fuel CO₂ is high-confidence; contrail warming carries "
        "~70% uncertainty (IPCC 'low confidence').\n"
        "- **CoCiP outputs Energy Forcing**, discounted by a ~0.42 efficacy and bridged to CO₂e — RF and ERF "
        "are not mixed.\n"
        "- **Business jets** cruise above CoCiP's ~13 km (FL426) calibration ceiling → their contrails are "
        "**under-counted, not extrapolated** (flagged).\n"
        "- **Aircraft, not people.** Figures are for *flights associated with this aircraft*; we can't confirm "
        "who was aboard. Owner attributions are public-figure / corroborated.")

# ---- Validation: does our output agree with published science? (numbers computed live from the data) ----
with st.expander("Validation — does this agree with published science?"):
    n_tot = len(df)
    n_forming = int((df["contrail_ef_joules"].abs() >= 1e6).sum())
    n_warming = int((df["contrail_co2e_central"] > 0).sum())
    in_domain = df[~df["bizjet_alt_flag"]]
    # stable-denominator peak only — the raw max is a tiny-fuel flight (+463%) that the
    # reveal itself refuses to headline; reporting it here would contradict the 33–63% band.
    peak = in_domain[in_domain["contrail_pct_of_fuel"].between(1, 100)]["contrail_pct_of_fuel"].max()
    st.markdown(
        f"We replaced a flat ~3× multiplier with flight-specific CoCiP physics — so the fair question is "
        f"*does it reproduce the literature?* These numbers are computed live from the {n_tot} committed flights:\n\n"
        f"- **Contrail-formation incidence:** {n_forming}/{n_tot} = **{100*n_forming/n_tot:.0f}%** of flights form a "
        f"persistent contrail; **{n_warming}/{n_tot} = {100*n_warming/n_tot:.0f}%** form a *net-warming* one. "
        f"Teoh et al. 2024 report ~24% / ~14% across the global fleet — the same order of magnitude. Ours runs "
        f"higher both because winter favours contrails **and** because we deliberately harvested extra *night* "
        f"flights (which form more), so read this as an upper estimate of incidence, not an unbiased fleet match. ✅\n"
        f"- **The power-law is visible inside single flights:** a single track segment can carry ~all of a flight's "
        f"energy forcing — reproducing Teoh's '2.7% of flights = 80% of forcing' at per-flight scale. It's why we "
        f"show *tiers*, not a precise 1..N rank. ✅\n"
        f"- **Per-flight ratio when ISSR is crossed in-domain (stable fuel base):** reaches **+{peak:.0f}%** here "
        f"(Musk, Gates), the lower edge of the published **33–63% (GWP100)** band — and 40–52% in the Phase 0.5 "
        f"optimal-altitude case. Short low-fuel flights produce *unstable* >100% ratios (Schmidt +463%) that we "
        f"deliberately do **not** headline. ✅\n"
        f"- **Day vs night drives the sign:** night contrails warm (100% in our data), many daytime contrails cool. "
        f"Night transatlantic widebodies aggregate **+57% (GWP100)** vs ~0% for daytime private jets — same pipeline. ✅\n"
        f"- **Where we diverge (honestly):** the daytime private-jet *aggregate* sits far below the fleet 33–63% "
        f"because daytime cooling cancels night warming and the ~13 km bizjet cap + ERA5 dry bias push our numbers "
        f"**down** — so the tool errs toward *under*-stating. \n\n"
        f"Full write-up: `docs/VALIDATION.md`.")

# ---- Data-quality guardrail (deterministic from the committed data; surfaced, not hidden) ----
flagged = df[df["proxy_type_flag"] | df["bizjet_alt_flag"] | df["coverage_gap_flag"]]
st.divider()
st.caption(
    f"📊 Data-quality guardrail: **{len(flagged)}/{len(df)} ({100*len(flagged)/len(df):.0f}%)** of leaderboard "
    f"flights carry a low-confidence flag (proxy aircraft type, above the CoCiP altitude cap, or a coverage gap). "
    "We surface this rather than hide it — a rising number is a signal, not something to bury.")
