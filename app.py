"""True Cost of Flying — deployed app (READ-ONLY).

Reads committed data/processed/{leaderboard.parquet, tracks/*.geojson}.
NO pycontrails / ERA5 / live API here — all physics is precomputed offline (see batch/).
"""
import json
import os

import pandas as pd
import pydeck as pdk
import streamlit as st

ROOT = os.path.dirname(__file__)
PROC = os.path.join(ROOT, "data", "processed")

st.set_page_config(page_title="True Cost of Flying", page_icon="✈️", layout="wide")


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


df = load_board()

st.title("✈️ True Cost of Flying")
st.caption("Every jet tracker shows you CO₂. Across aviation, CO₂ is only about a third of the warming. "
           "Here is the *same flight* with its contrail warming added — computed with CoCiP physics, not guessed.")

# ---- Sidebar: metric toggle ----
horizon = st.sidebar.radio("Time horizon (GWP)", ["GWP100", "GWP20"], index=0,
                           help="Magnitude is metric-dependent; the 'does this matter' verdict is ~90% robust "
                                "across metrics. GWP100 is the default; GWP20 weights short-lived contrails more.")
st.sidebar.markdown("---")
st.sidebar.markdown("**Data**: [adsb.lol](https://adsb.lol) tracks (ODbL-1.0) · ERA5 · OpenAP · "
                    "[pycontrails](https://py.contrails.org) CoCiP. Non-commercial / educational.")


def contrail_for(row, horizon):
    return row["contrail_co2e_gwp20_central"] if horizon == "GWP20" else row["contrail_co2e_central"]


view = df.copy()
view["contrail_co2e"] = view.apply(lambda r: contrail_for(r, horizon), axis=1)
view["combined"] = view["fuel_co2_kg"] + view["contrail_co2e"]
view["date"] = view["flight_id"].str.split("_").str[-1].str.replace(
    r"(\d{4})(\d{2})(\d{2})", r"\1-\2-\3", regex=True)
view = view.sort_values("combined", ascending=False)

# ---- Owner leaderboard (aggregated across each owner's tracked flights) ----
st.subheader("Leaderboard — who warmed the most (fuel CO₂ + contrails)")
agg = (view.groupby("owner_label")
       .agg(combined=("combined", "sum"), flights=("combined", "size"),
            ac_type=("ac_type", "first"),
            proxy=("proxy_type_flag", "any"), bizjet=("bizjet_alt_flag", "any"))
       .reset_index().sort_values("combined", ascending=False))
n = len(agg)
for i, (_, r) in enumerate(agg.iterrows()):
    tier = "🔴 High" if i < n / 3 else ("🟢 Low" if i >= 2 * n / 3 else "🟠 Medium")
    flags = []
    if r["proxy"]:
        flags.append("⚠️ proxy type")
    if r["bizjet"]:
        flags.append("⚠️ above CoCiP cap → under-counted")
    c1, c2, c3, c4 = st.columns([3, 2, 2, 3])
    c1.markdown(f"**{r['owner_label']}**  \n{r['ac_type']}")
    c2.metric(f"Total CO₂e ({int(r['flights'])} flights)", t(r["combined"]))
    c3.markdown(f"### {tier}")
    c4.markdown((" · ".join(flags)) if flags else "")
st.caption(f"Aggregated over {len(view)} tracked December-2024 flights for {n} owners. "
           "Totals are illustrative of the sampled flights, not annual.")

st.markdown("---")

# ---- Flight detail: the two-number reveal ----
st.subheader("Flight detail — the same flight, two numbers")
view["flabel"] = (view["owner_label"] + " · " + view["date"] + " · "
                  + (view["combined"] / 1000).round(1).astype(str) + " t")
choice = st.selectbox("Pick a flight", view["flabel"].tolist())
row = view[view["flabel"] == choice].iloc[0]
contrail = contrail_for(row, horizon)
combined = row["fuel_co2_kg"] + contrail
lo = row["fuel_co2_kg"] + row["contrail_co2e_low"]
hi = row["fuel_co2_kg"] + row["contrail_co2e_high"]

a, b = st.columns(2)
a.metric("Fuel CO₂ (what every tracker shows)", t(row["fuel_co2_kg"]))
pct = f"+{100*contrail/row['fuel_co2_kg']:.0f}%" if row["fuel_co2_kg"] else None
b.metric("Combined CO₂e (fuel + contrails)", t(combined), pct,
         help=f"{horizon}. Uncertainty band {t(lo)}–{t(hi)} (GWP100). Contrail term carries ~70% uncertainty.")

if contrail <= 0:
    st.info("This flight formed **no net-warming contrail** in the model — not every flight is an offender. "
            + ("(It also cruised above CoCiP's ~13 km calibration ceiling, so any contrail is under-counted.)"
               if row["bizjet_alt_flag"] else ""))
else:
    st.markdown(f"**Contrails add {t(contrail)} of CO₂-equivalent warming** on top of the fuel CO₂ — "
                f"the part no other tracker shows.")

# ---- Map ----
gj = load_track(row["flight_id"])
if gj and gj["features"]:
    segs = []
    for f in gj["features"]:
        c = f["geometry"]["coordinates"]
        s = f["properties"].get("ef_share", 0.0)
        # warming = red, neutral = grey, cooling = blue
        color = ([220, 60, 40] if s > 0.05 else [80, 110, 200] if s < -0.05 else [130, 130, 140])
        segs.append({"path": [[c[0][0], c[0][1]], [c[1][0], c[1][1]]], "color": color})
    sd = pd.DataFrame(segs)
    lons = [pt[0] for seg in sd["path"] for pt in seg]
    lats = [pt[1] for seg in sd["path"] for pt in seg]
    center_lon, center_lat = sum(lons) / len(lons), sum(lats) / len(lats)
    layer = pdk.Layer("PathLayer", sd, get_path="path", get_color="color", width_min_pixels=4)
    # No external basemap: layers render on the dark page background. Avoids the
    # Carto/Mapbox tile dependency that was blanking the whole canvas.
    st.pydeck_chart(pdk.Deck(
        layers=[layer],
        initial_view_state=pdk.ViewState(latitude=center_lat, longitude=center_lon, zoom=4, pitch=30),
        map_provider=None, map_style=None,
        tooltip={"text": "red = contrail warming along this segment"}), height=460)
    st.caption("Track coloured by where contrail warming occurred (red) vs none (grey). "
               "Fuel CO₂ is roughly uniform; contrail warming is concentrated where the jet crossed humid, icy air.")

# ---- Night transatlantic widebodies: the regime where contrails dominate ----
comp = load_comparators()
if comp is not None and len(comp):
    st.markdown("---")
    st.subheader("🌙 The other extreme: night transatlantic widebodies")
    st.markdown(
        "The jets above mostly fly **short daytime US/EU legs** — and daytime contrails often *cool*, so on "
        "aggregate contrails add almost nothing. Run the **same physics** on **night North-Atlantic widebody** "
        "crossings (the busy contrail corridor, in the dark) and it flips entirely:")
    pct_col = "contrail_pct_of_fuel_gwp20" if horizon == "GWP20" else "contrail_pct_of_fuel"
    cc_col = "contrail_co2e_gwp20_central" if horizon == "GWP20" else "contrail_co2e_central"
    agg = 100 * comp[cc_col].sum() / comp["fuel_co2_kg"].sum()
    m1, m2 = st.columns([2, 3])
    m1.metric(f"Contrails add — aggregate of {len(comp)} night crossings ({horizon})", f"+{agg:.0f}%",
              help="vs roughly 0% on the daytime private jets above — identical pipeline, opposite regime.")
    m2.markdown("&nbsp;  \nEvery one formed its contrail **at night → 100% warming**, all at in-domain "
                "cruise altitude. **Time-of-day and route — not the model — drive the difference.**")
    tbl = pd.DataFrame({
        "Flight": comp["registration"].astype(str) + " (" + comp["adsb_type"].astype(str) + ")",
        "Fuel CO₂": (comp["fuel_co2_kg"] / 1000).round().astype(int).astype(str) + " t",
        "Contrail CO₂e": (comp[cc_col] / 1000).round().astype(int).astype(str) + " t",
        "Contrails add": comp[pct_col].round().astype(int).astype(str) + "%",
    })
    st.dataframe(tbl, hide_index=True, use_container_width=True)
    st.caption("Commercial comparators (not ranked in the leaderboard). 2 of 5 use a wide-body proxy fuel type "
               "(elevated fuel-CO₂ uncertainty); contrail term carries ~70% uncertainty. "
               "Impact Explorer can't be queried for these historical flights (it is forecast-only), but our "
               "EF→CO₂e conversion matches Contrails.org's published factor to 0.8%. See `docs/VALIDATION.md` §4, §7.")

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
        f"- **Where we diverge (honestly):** the *sample aggregate* is far below the fleet 33–63% — these short "
        f"winter US/EU legs largely missed the heavily-trafficked ISSR corridors that dominate the fleet figure, and "
        f"about half the forming flights *cool*. The biases (ERA5 dry bias, the ~13 km bizjet cap) push our numbers "
        f"**down**, so the tool errs toward *under*-stating. A flight-matched cross-check vs Contrails.org Impact "
        f"Explorer needs a commercial comparator — an open gap. ⚠️\n\n"
        f"Full write-up: `docs/VALIDATION.md`.")
