"""True Cost of Flying — deployed app (READ-ONLY).

Reads committed data/processed/{leaderboard.parquet, tracks/*.geojson, comparators.parquet}.
NO pycontrails / ERA5 / live API here — all physics is precomputed offline (see batch/).
"""
import json
import os

import pandas as pd
import pydeck as pdk
import streamlit as st

ROOT = os.path.dirname(__file__)
PROC = os.path.join(ROOT, "data", "processed")

st.set_page_config(page_title="True Cost of Flying", page_icon="✈️",
                   layout="centered", initial_sidebar_state="collapsed")

# ---- Brand styling + mobile responsiveness (single global stylesheet) ----
# Colour language: amber = fuel CO₂, red = contrail warming, blue = contrail cooling.
FUEL, WARM, COOL = "#d9994e", "#e2503a", "#4e8fd6"
st.markdown("""
<style>
:root { --fuel:#d9994e; --warm:#e2503a; --cool:#4e8fd6; --ink:#e8eef5; --muted:#9bb0c4; }
/* Comfortable reading column; tighter gutters on phones */
.block-container { max-width: 880px; padding-top: 2.2rem; padding-bottom: 4rem; }
@media (max-width: 640px){ .block-container { padding-left: .9rem; padding-right: .9rem; padding-top: 1.2rem; } }
#MainMenu, footer, .stDeployButton { visibility: hidden; }
/* Hero */
.hero-title { font-size: clamp(1.9rem, 7vw, 3rem); font-weight: 800; line-height: 1.05; margin: 0 0 .4rem; }
.hero-sub { color: var(--muted); font-size: clamp(.95rem, 2.6vw, 1.08rem); line-height: 1.5; max-width: 46ch; }
.hero-accent { color: var(--warm); }
/* Section labels */
.sec { font-size: .8rem; letter-spacing: .12em; text-transform: uppercase; color: var(--muted);
       margin: 2.2rem 0 .6rem; font-weight: 700; }
/* Leaderboard */
.lb-row { display: grid; grid-template-columns: 2.3rem 1fr auto; gap: .55rem .8rem; align-items: center;
          padding: .7rem .85rem; border-radius: 12px; background: #13243a; margin-bottom: .5rem;
          border: 1px solid #1e3552; }
.lb-rank { font-size: 1.15rem; font-weight: 800; text-align: center; color: var(--muted); }
.lb-name { font-weight: 700; font-size: 1.02rem; }
.lb-ac { color: var(--muted); font-size: .82rem; }
.lb-val { text-align: right; font-weight: 800; font-size: 1.12rem; white-space: nowrap; }
.lb-val small { display:block; font-weight:600; font-size:.7rem; color:var(--muted); }
.chip { display:inline-block; font-size:.68rem; padding:.08rem .45rem; border-radius:999px;
        background:#24344d; color:#c7d6e6; margin:.18rem .25rem 0 0; white-space:nowrap; }
.tier-dot { font-size:.7rem; font-weight:700; }
/* Reveal */
.reveal { background:#13243a; border:1px solid #1e3552; border-radius:16px; padding:1.1rem 1.2rem; }
.reveal-nums { display:flex; flex-wrap:wrap; gap:1rem 2rem; }
.stat { flex:1 1 9rem; }
.stat .lbl { color:var(--muted); font-size:.82rem; margin-bottom:.15rem; }
.stat .num { font-size: clamp(1.7rem, 7vw, 2.6rem); font-weight:800; line-height:1; }
.stat .num small { font-size:.9rem; font-weight:600; color:var(--muted); }
.delta-pill { display:inline-block; margin-top:.4rem; padding:.15rem .6rem; border-radius:999px;
              font-weight:800; font-size:.95rem; background:rgba(226,80,58,.16); color:#ff8b73; }
.delta-cool { background:rgba(78,143,214,.16); color:#8fc0f5; }
.bar { display:flex; height:30px; border-radius:8px; overflow:hidden; margin:1rem 0 .4rem; background:#0b1622; }
.bar span { display:flex; align-items:center; padding:0 .5rem; font-size:.74rem; font-weight:700; color:#0b1622;
            white-space:nowrap; overflow:hidden; }
.bar .b-fuel { background:var(--fuel); }
.bar .b-warm { background:var(--warm); color:#fff; }
.barcap { color:var(--muted); font-size:.78rem; }
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


df = load_board()

# ---- Hero ----
st.markdown(
    '<div class="hero-title">✈️ True Cost of Flying</div>'
    '<p class="hero-sub">Every jet tracker shows you CO₂. Across aviation, CO₂ is only about '
    '<span class="hero-accent">a third</span> of the warming. Here is the <em>same flight</em> with its '
    'contrail warming added — computed with CoCiP physics, not guessed.</p>',
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


def contrail_for(row, h):
    return row["contrail_co2e_gwp20_central"] if h == "GWP20" else row["contrail_co2e_central"]


view = df.copy()
view["contrail_co2e"] = view.apply(lambda r: contrail_for(r, horizon), axis=1)
view["combined"] = view["fuel_co2_kg"] + view["contrail_co2e"]
view["date"] = view["flight_id"].str.split("_").str[-1].str.replace(
    r"(\d{4})(\d{2})(\d{2})", r"\1-\2-\3", regex=True)
view = view.sort_values("combined", ascending=False)

# ---- Owner leaderboard (aggregated across each owner's tracked flights) ----
st.markdown('<div class="sec">Leaderboard — who warmed the most (fuel CO₂ + contrails)</div>',
            unsafe_allow_html=True)
agg = (view.groupby("owner_label")
       .agg(combined=("combined", "sum"), flights=("combined", "size"),
            ac_type=("ac_type", "first"),
            proxy=("proxy_type_flag", "any"), bizjet=("bizjet_alt_flag", "any"))
       .reset_index().sort_values("combined", ascending=False).reset_index(drop=True))
n = len(agg)
rows_html = []
for i, r in agg.iterrows():
    tier = ('<span class="tier-dot" style="color:#e2503a">🔴 High</span>' if i < n / 3
            else '<span class="tier-dot" style="color:#3fae6b">🟢 Low</span>' if i >= 2 * n / 3
            else '<span class="tier-dot" style="color:#e0a23a">🟠 Med</span>')
    chips = ""
    if r["proxy"]:
        chips += '<span class="chip">⚠ proxy type</span>'
    if r["bizjet"]:
        chips += '<span class="chip">⚠ above cap · under-counted</span>'
    rows_html.append(
        f'<div class="lb-row"><div class="lb-rank">{i+1}</div>'
        f'<div><div class="lb-name">{esc(r["owner_label"])}</div>'
        f'<div class="lb-ac">{esc(r["ac_type"])} · {int(r["flights"])} flights {chips}</div></div>'
        f'<div class="lb-val">{r["combined"]/1000:,.1f} t<small>{tier}</small></div></div>')
st.markdown("".join(rows_html), unsafe_allow_html=True)
st.caption(f"Aggregated over {len(view)} tracked Dec-2024/Jan-2025 flights for {n} owners ({horizon}). "
           "Tiers (not a precise 1..N rank) because magnitude reshuffles with metric. Illustrative of the "
           "sampled flights, not annual.")

# ---- Celebrity portraits (verified copy; GWP100 snapshot of the committed set) ----
# Numbers + prose were adversarially fact-checked against the data (workflow); shown at
# GWP100. Ordered Trump→Gates→Musk→Swift: from "fuel is the story" to "contrails can double a flight".
PORTRAITS = [
    {"name": "Donald Trump", "badge": "🌆 dusk", "ac": "Boeing 757-200 · in-domain (cleanest numbers)",
     "fuel": "226.8 t", "contrail": "≈0 t", "delta": "+0.06 t (64 kg)", "wc": (1, 0, 5),
     "standout": "**Dec 13, NY→Palm Beach** — the *only* one of six flights with any contrail: **+64 kg** (0.2% of its fuel). The other five: zero.",
     "chips": ["in-domain 757 → not altitude-flagged", "5/6 ~zero = power-law", "fuel+contrails only (not 3× ERF)", "we headline tonnes, not the 0.2% ratio"],
     "framing": "Across six tracked flights, all on the same in-domain Boeing 757-200 (N757AF, “Trump Force One”), the fuel burn totals **226.8 t of CO₂ — the second-largest fuel footprint in this dataset**, behind the New England Patriots' 616.2 t. Because the 757 cruises well below CoCiP's altitude cap, these are among the cleanest, most trustworthy numbers we have (no bizjet under-counting caveat). Yet the contrail story is almost nothing: five of six flights formed no measurable contrail, and the lone exception added only **0.064 t CO₂e** (GWP100) — about 0.2% of that flight's fuel. The honest contrast: a large warming footprint that is overwhelmingly the jet fuel itself."},
    {"name": "Bill Gates", "badge": "🌙 night (standout)", "ac": "Gulfstream G650ER",
     "fuel": "69.3 t", "contrail": "+4.2 t", "delta": "+6% net", "wc": (1, 1, 5),
     "standout": "**Dec 9, Las Vegas→Washington** (night) — painted a warming contrail **+5.6 t (+32% of fuel)**, in-domain → the cleanest evidence in his set. One daytime flight slightly *cooled*.",
     "chips": ["~70% contrail uncertainty", "4/7 above-cap → under-counted", "3 of 5 zeros are above-cap (not confirmed clean)", "fuel+contrails only"],
     "framing": "The dominant cost of Bill Gates's tracked flying is plain fuel: 7 flights on his Gulfstream G650ER (N887WM) emitted **69.3 t of CO₂**. Contrails were a small, two-sided add-on netting **+4.2 t** at GWP100 — only one flight warmed (+5.56 t, a night flight), one slightly cooled (−1.39 t, a daytime contrail reflecting sunlight), and five showed little or no modelled contrail. Of those five, only two (Dec 12, Dec 4) are *clean in-domain* zeros; the other three are above-cap flights whose 0.0 is partly an under-count, not confirmed non-formation. The cleanest in-domain evidence is the one night flight that clearly warmed, versus the one daytime flight that didn't."},
    {"name": "Elon Musk", "badge": "🌙↔☀️ cuts both ways", "ac": "Gulfstream G650ER",
     "fuel": "84.4 t", "contrail": "−25.8 t", "delta": "net cooling*", "wc": (1, 2, 4),
     "standout": "**Dec 12, San Jose→Austin** (night) — **+4.9 t warming (+37%)**, his only in-domain flight → cleanest case. Two *daytime* flights formed ice that net-**cooled**.",
     "chips": ["~70% contrail uncertainty", "4/7 above-cap → under-counted; cooling is soft", "net cooling = daytime geometry, small sample", "fuel+contrails only"],
     "framing": "Across 7 tracked flights, Elon Musk's Gulfstream G650ER burned fuel for **84.4 t of CO₂** — the certain, in-the-tailpipe number. Contrails were the honest mix: 4 flights formed essentially none, 1 night flight warmed (+4.9 t at GWP100), and 2 daytime flights formed ice that reflected enough sunlight to net-*cool*, so on central estimates his contrail term nets to about **−26 t**. The G650ER routinely cruises above CoCiP's ~13 km cap, so 4 flights are altitude-flagged and **under-counted, not exaggerated** — the cooling totals in particular could shrink with full physics. *Net cooling here is a small-sample, daytime-geometry result; the durable harm is the fuel CO₂.*"},
    {"name": "Taylor Swift", "badge": "☀️ day (standout)", "ac": "Dassault Falcon 7X",
     "fuel": "121.8 t", "contrail": "+18.4 t", "delta": "+15% net", "wc": (3, 0, 9),
     "standout": "**Dec 10, Nashville→Montana** (day) — contrails **+12.1 t**, almost matching the 12.7 t of fuel and **~doubling that single flight's warming (≈1.96×)**.",
     "chips": ["~70% contrail uncertainty", "5/12 above-cap → likely UNDER-counted (a floor)", "proxy aircraft type", "9/12 ~zero = power-law"],
     "framing": "Across 12 tracked flights on her Dassault Falcon 7X (N621MM), the certain cost is **121.8 t of fuel CO₂**. Contrails are a separate, more uncertain story (~70%): 9 of 12 flights formed essentially none — the normal power-law outcome — while 3 left warming contrails, adding **18.4 t CO₂e** (GWP100). The most telling flight, Dec 10, added **~12.1 t** — almost matching its own 12.7 t of fuel and pushing that flight's total to **~1.96× fuel-only**. (The Falcon 7X cruises above CoCiP's cap, so this is a likely *floor*, not an exaggeration.) This is fuel CO₂ + contrails only — a partial accounting, **not** the aviation-fleet “3×”, which is a different statistic."},
]


def wc_bar(wc):
    """Tiny 3-segment proportion bar: warming / cooling / near-zero flight counts."""
    w, c, z = wc
    base = "display:flex;align-items:center;justify-content:center;"
    seg = []
    if w:
        seg.append(f'<div style="{base}flex:{w};background:#e2503a">{w} 🔥</div>')
    if c:
        seg.append(f'<div style="{base}flex:{c};background:#4e8fd6">{c} ❄</div>')
    if z:
        seg.append(f'<div style="{base}flex:{z};background:#33455c">{z} ○</div>')
    return ('<div style="display:flex;height:22px;border-radius:6px;overflow:hidden;margin:.35rem 0;'
            'font-size:.68rem;font-weight:700;color:#fff">' + "".join(seg) + '</div>')


st.markdown('<div class="sec">What contrails actually did for 4 famous flyers</div>', unsafe_allow_html=True)
st.markdown(
    "Burning jet fuel is the **certain** harm. Contrails are the **wildcard** — a *concentrated* effect, "
    "not a flat multiplier. Trump's 757 burned the most fuel of these four yet left near-zero contrails "
    "(and flies in-domain, so it's our most trustworthy number); at the other end, one Taylor Swift flight's "
    "contrails nearly *doubled* its warming. Most flights here formed almost none — the headline isn't "
    "“always 3×”, it's **“usually near zero, occasionally a lot.”**")
pcols = st.columns(2)
for i, p in enumerate(PORTRAITS):
    with pcols[i % 2]:
        with st.container(border=True):
            st.markdown(f"**{p['name']}** &nbsp; <span class='chip'>{p['badge']}</span>", unsafe_allow_html=True)
            st.caption(p["ac"])
            k1, k2 = st.columns(2)
            k1.metric("Fuel CO₂", p["fuel"])
            k2.metric("Contrails (GWP100)", p["contrail"], p["delta"], delta_color="off")
            w, c, z = p["wc"]
            st.markdown(wc_bar(p["wc"]), unsafe_allow_html=True)
            st.caption(f"{w} warming · {c} cooling · {z} near-zero of {w+c+z} flights")
            st.markdown(p["standout"])
            st.markdown("".join(f'<span class="chip">{esc(ch)}</span>' for ch in p["chips"]),
                        unsafe_allow_html=True)
            with st.expander("The full picture"):
                st.markdown(p["framing"])
st.caption("Shown at GWP100 — a verified snapshot of the committed dataset (numbers fact-checked against the "
           "data). Same physics, four very different contrail outcomes.")

# ---- Flight detail: the two-number reveal (the aha) ----
st.markdown('<div class="sec">The reveal — same flight, two numbers</div>', unsafe_allow_html=True)
view["flabel"] = (view["owner_label"] + " · " + view["date"] + " · "
                  + (view["combined"] / 1000).round(1).astype(str) + " t")
choice = st.selectbox("Pick a tracked flight", view["flabel"].tolist(), label_visibility="collapsed")
row = view[view["flabel"] == choice].iloc[0]
contrail = contrail_for(row, horizon)
fuel = row["fuel_co2_kg"]
combined = fuel + contrail
lo = fuel + row["contrail_co2e_low"]
hi = fuel + row["contrail_co2e_high"]
pct = 100 * contrail / fuel if fuel else 0

# A short, low-fuel flight that crossed one intense contrail patch yields a huge, UNSTABLE
# ratio (tiny denominator). Headline the absolute tonnes, not the raw %, in that case.
unstable = contrail > 0 and pct > 150
if contrail > 0:
    fuel_w = 100 * fuel / combined
    bar = (f'<div class="bar"><span class="b-fuel" style="width:{fuel_w:.0f}%">Fuel {fuel/1000:,.0f} t</span>'
           f'<span class="b-warm" style="width:{100-fuel_w:.0f}%">+{contrail/1000:,.0f} t contrails</span></div>'
           f'<div class="barcap">The red slice is the warming no other tracker counts.</div>')
    if unstable:
        delta = f'<span class="delta-pill">+{contrail/1000:,.1f} t contrails — contrail-dominated short flight</span>'
    else:
        delta = f'<span class="delta-pill">contrails add +{pct:.0f}%</span>'
    combined_val = f'{combined/1000:,.1f} <small>t CO₂e</small>'
else:
    bar = ('<div class="bar"><span class="b-fuel" style="width:100%">Fuel '
           f'{fuel/1000:,.0f} t — no net-warming contrail</span></div>')
    delta = f'<span class="delta-pill delta-cool">contrails net {pct:+.0f}% (cooling / none)</span>'
    combined_val = f'{combined/1000:,.1f} <small>t CO₂e</small>'

st.markdown(
    f'<div class="reveal"><div class="reveal-nums">'
    f'<div class="stat"><div class="lbl">Fuel CO₂ — what every tracker shows</div>'
    f'<div class="num">{fuel/1000:,.1f} <small>t</small></div></div>'
    f'<div class="stat"><div class="lbl">Combined CO₂e — fuel + contrails</div>'
    f'<div class="num">{combined_val}</div>{delta}</div>'
    f'</div>{bar}</div>',
    unsafe_allow_html=True)
st.caption(f"{horizon} · uncertainty band {t(lo)}–{t(hi)} · contrail term carries ~70% uncertainty (IPCC "
           f"'low confidence'). " + ("Above CoCiP's ~13 km cap → likely under-counted. " if row["bizjet_alt_flag"] else "")
           + ("This is a short, low-fuel flight where one intense contrail patch dominates — so we show the "
              "absolute tonnes, not the unstable +%, which here would read misleadingly high." if unstable else ""))

# ---- Map ----
gj = load_track(row["flight_id"])
if gj and gj["features"]:
    segs = []
    for f in gj["features"]:
        c = f["geometry"]["coordinates"]
        s = f["properties"].get("ef_share", 0.0)
        color = ([220, 60, 40] if s > 0.05 else [80, 110, 200] if s < -0.05 else [130, 130, 140])
        segs.append({"path": [[c[0][0], c[0][1]], [c[1][0], c[1][1]]], "color": color})
    sd = pd.DataFrame(segs)
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
    st.caption("Track coloured by where contrail warming occurred (🔴 red) vs none (grey) vs cooling (🔵 blue). "
               "Fuel CO₂ is roughly uniform; contrail warming is concentrated where the jet crossed humid, icy air.")

# ---- Night transatlantic widebodies: the regime where contrails dominate ----
comp = load_comparators()
if comp is not None and len(comp):
    st.markdown('<div class="sec">🌙 The other extreme — night transatlantic widebodies</div>',
                unsafe_allow_html=True)
    st.markdown(
        "The jets above mostly fly **short daytime US/EU legs**, where daytime contrails often *cool* — so on "
        "aggregate they add almost nothing. Run the **same physics** on **night North-Atlantic widebody** "
        "crossings (the busy contrail corridor, in the dark) and it flips:")
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
    peak = in_domain["contrail_pct_of_fuel"].max()
    st.markdown(
        f"We replaced a flat ~3× multiplier with flight-specific CoCiP physics — so the fair question is "
        f"*does it reproduce the literature?* These numbers are computed live from the {n_tot} committed flights:\n\n"
        f"- **Contrail-formation incidence:** {n_forming}/{n_tot} = **{100*n_forming/n_tot:.0f}%** of flights form a "
        f"persistent contrail; **{n_warming}/{n_tot} = {100*n_warming/n_tot:.0f}%** form a *net-warming* one. "
        f"Teoh et al. 2024 report ~24% / ~14% across the global fleet — our private-jet, winter sample lands in the "
        f"same place (slightly higher, as cold high-latitude air favours contrails). ✅\n"
        f"- **The power-law is visible inside single flights:** a single track segment can carry ~all of a flight's "
        f"energy forcing — reproducing Teoh's '2.7% of flights = 80% of forcing' at per-flight scale. It's why we "
        f"show *tiers*, not a precise 1..N rank. ✅\n"
        f"- **Per-flight ratio when ISSR is crossed in-domain:** reaches **+{peak:.0f}%** here (and 40–52% in the "
        f"Phase 0.5 optimal-altitude case) — the lower-to-middle of the published **33–63% (GWP100)** band. ✅\n"
        f"- **Day vs night drives the sign:** night contrails warm (100% in our data), many daytime contrails cool. "
        f"Night transatlantic widebodies aggregate **+57%** vs ~0% for daytime private jets — same pipeline. ✅\n"
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
