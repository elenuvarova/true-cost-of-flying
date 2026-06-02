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


# ---- Leaderboard by tier ----
st.subheader("Leaderboard — total warming (fuel CO₂ + contrails)")
view = df.copy()
view["contrail_co2e"] = view.apply(lambda r: contrail_for(r, horizon), axis=1)
view["combined"] = view["fuel_co2_kg"] + view["contrail_co2e"]
view = view.sort_values("combined", ascending=False)

TIER_LABEL = {"high": "🔴 High", "medium": "🟠 Medium", "low": "🟢 Low"}
for _, r in view.iterrows():
    flags = []
    if r["proxy_type_flag"]:
        flags.append("⚠️ proxy type")
    if r["bizjet_alt_flag"]:
        flags.append("⚠️ above CoCiP cap → under-counted")
    c1, c2, c3, c4 = st.columns([3, 2, 2, 3])
    c1.markdown(f"**{r['owner_label']}**  \n{r['ac_type']} · {r['registration']}")
    c2.metric("Combined CO₂e", t(r["combined"]))
    c3.metric("Contrails add", f"+{100*r['contrail_co2e']/r['fuel_co2_kg']:.0f}%" if r["fuel_co2_kg"] else "—")
    c4.markdown(f"{TIER_LABEL.get(r['tier'], r['tier'])}  \n" + (" · ".join(flags) if flags else ""))

st.markdown("---")

# ---- Flight detail: the two-number reveal ----
st.subheader("Flight detail — the same flight, two numbers")
owner = st.selectbox("Pick a flight", view["owner_label"].tolist())
row = view[view["owner_label"] == owner].iloc[0]
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
