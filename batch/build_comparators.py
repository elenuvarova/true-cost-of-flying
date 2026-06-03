"""Offline batch driver for the NIGHT-TRANSATLANTIC-WIDEBODY validation comparators.

Mirrors batch/build_dataset.py process_trace(), but:
  - reads its registry from data/reference/comparators.csv (hex,registration,type,...)
  - writes to data/processed/comparators.parquet + data/processed/comparators_tracks/
  - reports night-EF vs day-EF split and CoCiP-cap status per flight.

Does NOT touch owners.csv / leaderboard.parquet / tracks/. Run with .venv/bin/python.

Usage:
  python batch/build_comparators.py <hex>__<day>.json.gz [more traces ...]
  (or no args -> process every trace in data/raw/traces whose hex is in comparators.csv)
"""
import csv
import glob
import json
import math
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src.tracks import load_trace, longest_flight
from src.fuel import fuel_and_co2, resolve_type
from src.era5 import load_arco
from src.contrails import run_cocip, ps_type_for
from src.fuse import build_row, assign_tiers, contrail_co2e_bands
from pycontrails.models.cocip import Cocip
from pycontrails.core.cache import DiskCacheStore

ROOT = os.path.join(os.path.dirname(__file__), "..")
OUT = os.path.join(ROOT, "data", "processed")
TRACKS = os.path.join(OUT, "comparators_tracks")
RAW = os.path.join(ROOT, "data", "raw", "traces")
COMPARATORS_CSV = os.path.join(ROOT, "data", "reference", "comparators.csv")
PLS = [150, 175, 200, 225, 250, 300, 350]
MAX_VTX = 500
CAP_M = 13000.0
# Transatlantic traces have a ~3-4 h receiver-dark gap over the open mid-ocean while the
# aircraft cruises on BOTH sides. Bridge gaps up to 5 h so the crossing stays one flight;
# CoCiP's resample_and_fill("60s") interpolates the great-circle across the gap, recovering
# the (deep-night) mid-ocean cruise where the contrail forms. The default 30-min split
# used for the bizjet dataset would fragment the crossing and drop the ocean middle.
COMPARATOR_MAX_GAP_S = 5 * 3600

with open(COMPARATORS_CSV) as f:
    REG = {r["hex"].lower(): r for r in csv.DictReader(f)}


def solar_elev(lat, lon, when):
    n = when.dayofyear
    frac = (when.hour + when.minute / 60) / 24
    g = 2 * math.pi / 365 * (n - 1 + frac - 0.5)
    dec = (0.006918 - 0.399912 * math.cos(g) + 0.070257 * math.sin(g)
           - 0.006758 * math.cos(2 * g) + 0.000907 * math.sin(2 * g))
    eqt = 229.18 * (0.000075 + 0.001868 * math.cos(g) - 0.032077 * math.sin(g)
                    - 0.014615 * math.cos(2 * g) - 0.040849 * math.sin(2 * g))
    tst = (when.hour * 60 + when.minute) + eqt + 4 * lon
    ha = math.radians(tst / 4 - 180)
    la = math.radians(lat)
    return math.degrees(math.asin(max(-1, min(1, math.sin(la) * math.sin(dec)
                                              + math.cos(la) * math.cos(dec) * math.cos(ha)))))


def decimate(df, n=MAX_VTX):
    if len(df) <= n:
        return df
    idx = np.linspace(0, len(df) - 1, n).round().astype(int)
    return df.iloc[np.unique(idx)].reset_index(drop=True)


def track_geojson(o, row):
    o = o.dropna(subset=["longitude", "latitude"]).reset_index(drop=True)
    o = decimate(o)
    ef = o["ef"].fillna(0.0).values if "ef" in o else np.zeros(len(o))
    ef_max = float(np.nanmax(np.abs(ef))) or 1.0
    feats = []
    for i in range(len(o) - 1):
        share = float(ef[i]) / ef_max
        feats.append({
            "type": "Feature",
            "geometry": {"type": "LineString", "coordinates": [
                [float(o.longitude[i]), float(o.latitude[i]), float(o.altitude[i])],
                [float(o.longitude[i + 1]), float(o.latitude[i + 1]), float(o.altitude[i + 1])]]},
            "properties": {"ef": float(ef[i]), "ef_share": round(share, 3)},
        })
    return {"type": "FeatureCollection",
            "properties": {k: row[k] for k in ("icao24", "registration", "owner_label",
                           "combined_co2e_central", "fuel_co2_kg", "contrail_co2e_central", "tier")},
            "features": feats}


def night_day_ef_split(o, day):
    """Split total CoCiP EF (J) into night/day by solar elevation at each waypoint.

    A waypoint is 'night' if the sun is >6 deg below the horizon at that lat/lon/time.
    Waypoints carry their own time when present; otherwise fall back to interpolation.
    """
    if "ef" not in o or len(o) == 0:
        return 0.0, 0.0, 0.0
    ef = o["ef"].fillna(0.0).values
    # time column may be named 'time'
    times = None
    if "time" in o:
        times = pd.to_datetime(o["time"], utc=True)
    night_ef = day_ef = 0.0
    n_night = 0
    for i in range(len(o)):
        lat = o["latitude"].iloc[i]
        lon = o["longitude"].iloc[i]
        if times is not None and pd.notna(times.iloc[i]):
            when = times.iloc[i]
        else:
            when = None
        if when is None or pd.isna(lat) or pd.isna(lon):
            day_ef += ef[i]
            continue
        e = solar_elev(float(lat), float(lon), pd.Timestamp(when))
        if e < -6:
            night_ef += ef[i]
            n_night += 1
        else:
            day_ef += ef[i]
    night_pct_pts = round(100 * n_night / len(o), 0)
    return float(night_ef), float(day_ef), night_pct_pts


def process_trace(path, cache):
    base = os.path.basename(path)
    hexid = base.split("__")[0].lower()
    reg = REG.get(hexid)
    if not reg:
        print(f"  skip {hexid}: not in comparators.csv")
        return None
    meta, df = load_trace(path)
    fl = longest_flight(df, max_gap_s=COMPARATOR_MAX_GAP_S)
    if fl is None:
        print(f"  {hexid}: no real flight in {base}")
        return None
    typecode = meta["type"] or reg.get("type", "")
    openap_type, type_source = resolve_type(typecode)
    max_alt_m = float(fl["altitude_m"].max())
    t0 = pd.Timestamp(fl.time.iloc[0]).floor("h")
    label = f"{reg.get('registration') or hexid} ({typecode})"
    print(f"  {label:<28} {hexid} {t0.date()} {typecode}->{openap_type}/{type_source} "
          f"PS={ps_type_for(openap_type)} FL{max_alt_m/0.3048//100:.0f} {len(fl)}pts", flush=True)

    # The crossing carries a multi-hour receiver-dark mid-ocean gap. fuel_and_co2 integrates
    # fuel_flow * dt over raw samples, so that one huge dt would inject tens of tonnes of
    # phantom fuel. Resample to 60 s first (great-circle fill, same as CoCiP) so fuel is
    # integrated over a regular cadence. Build a Flight, resample, hand a clean df to fuel.
    from pycontrails import Flight as _Flight
    flr = _Flight(longitude=fl["longitude"].values, latitude=fl["latitude"].values,
                  altitude=fl["altitude_m"].values, time=fl["time"].values,
                  aircraft_type=ps_type_for(openap_type), flight_id=str(hexid)) \
        .resample_and_fill("60s").dataframe
    fl_fuel = pd.DataFrame({"time": pd.to_datetime(flr["time"], utc=True),
                            "altitude_m": flr["altitude"].values,
                            "gs_kt": np.nan})  # gs filled with cruise TAS inside fuel_and_co2
    fuel_kg, fuel_co2_kg, _, _ = fuel_and_co2(fl_fuel, typecode)
    fid = f"{hexid}_{t0.strftime('%Y%m%d')}"

    cocdir = os.path.join(os.path.expanduser(os.environ.get("TCOF_CACHE_DIR", "~/.cache/tcof_era5")), "cocip_comparators")
    os.makedirs(cocdir, exist_ok=True)
    cpath = os.path.join(cocdir, f"{fid}.parquet")
    if os.path.exists(cpath):
        o = pd.read_parquet(cpath)
        ef = float(np.nansum(o["ef"])) if "ef" in o else 0.0
        print("    (cached CoCiP)", flush=True)
    else:
        t1 = (pd.Timestamp(fl.time.iloc[-1]) + pd.Timedelta(hours=5)).ceil("h")
        tw = (t0.strftime("%Y-%m-%dT%H:%M:%S"), t1.strftime("%Y-%m-%dT%H:%M:%S"))
        print(f"    ERA5 window {tw} ...", flush=True)
        met = load_arco(tw, Cocip.met_variables, PLS, cache)
        rad = load_arco(tw, Cocip.rad_variables, -1, cache)
        ef, o = run_cocip(fl, openap_type, met, rad, flight_id=fid)
        keep = [c for c in ("longitude", "latitude", "altitude", "time", "ef") if c in o]
        o[keep].to_parquet(cpath, index=False)

    day = t0.strftime("%Y-%m-%d")
    night_ef, day_ef, night_pct_pts = night_day_ef_split(o, day)

    route = (f"{fl.latitude.iloc[0]:.1f},{fl.longitude.iloc[0]:.1f}"
             f"->{fl.latitude.iloc[-1]:.1f},{fl.longitude.iloc[-1]:.1f}")
    row = build_row(
        icao24=hexid, flight_id=fid,
        owner_label=label, owner_confidence="commercial",
        registration=reg.get("registration") or "", ac_type=reg.get("desc") or typecode,
        openap_type=openap_type, type_source=type_source,
        dep_time=str(fl.time.iloc[0]), route=route,
        fuel_kg=fuel_kg, fuel_co2_kg=fuel_co2_kg, ef_joules=ef, max_alt_m=max_alt_m,
    )
    # comparator-specific extras
    row["adsb_type"] = typecode
    row["night_ef_joules"] = round(night_ef, 3)
    row["day_ef_joules"] = round(day_ef, 3)
    row["night_pct_of_waypoints"] = night_pct_pts
    row["max_fl"] = round(max_alt_m / 0.3048 / 100)
    row["above_cocip_cap"] = bool(max_alt_m > CAP_M)
    bands = contrail_co2e_bands(ef)
    row["contrail_pct_of_fuel_gwp20"] = (round(100 * bands["GWP20"]["central"] / fuel_co2_kg, 1)
                                         if fuel_co2_kg else 0.0)
    return row, o


def main():
    os.makedirs(TRACKS, exist_ok=True)
    cache = DiskCacheStore(cache_dir=os.environ.get("TCOF_CACHE_DIR", os.path.expanduser("~/.cache/tcof_era5")))
    if len(sys.argv) > 1:
        traces = []
        for a in sys.argv[1:]:
            traces.append(a if os.path.isabs(a) else os.path.join(RAW, a))
    else:
        traces = [p for p in glob.glob(os.path.join(RAW, "*.json.gz"))
                  if os.path.basename(p).split("__")[0].lower() in REG]
    traces = sorted(traces)
    print(f"processing {len(traces)} comparator traces ...")
    rows, geos = [], []
    for p in traces:
        try:
            res = process_trace(p, cache)
        except Exception as e:
            import traceback
            print(f"  !! {os.path.basename(p)}: {type(e).__name__}: {str(e)[:200]}")
            traceback.print_exc()
            continue
        if res:
            rows.append(res[0])
            geos.append(res)

    if not rows:
        print("no rows produced")
        return
    rows = assign_tiers(rows)
    pd.DataFrame(rows).to_parquet(os.path.join(OUT, "comparators.parquet"), index=False)
    for row, o in geos:
        with open(os.path.join(TRACKS, f"{row['flight_id']}.geojson"), "w") as f:
            json.dump(track_geojson(o, row), f)

    print(f"\nWrote comparators.parquet ({len(rows)} rows) + {len(geos)} track GeoJSONs to {OUT}")
    print(f"\n{'label':<30} {'type':<6} {'FL':>4} {'cap':>4} {'fuelCO2_t':>9} "
          f"{'contr_t':>8} {'pct%':>6} {'gwp20%':>7} {'nightEF':>9} {'dayEF':>9} {'night_pts%':>10}")
    for r in rows:
        print(f"{r['owner_label']:<30} {r['adsb_type']:<6} {r['max_fl']:>4} "
              f"{'OVER' if r['above_cocip_cap'] else 'ok':>4} "
              f"{r['fuel_co2_kg']/1000:>9.1f} {r['contrail_co2e_central']/1000:>8.2f} "
              f"{r['contrail_pct_of_fuel']:>6.1f} {r['contrail_pct_of_fuel_gwp20']:>7.1f} "
              f"{r['night_ef_joules']:>9.2e} {r['day_ef_joules']:>9.2e} {r['night_pct_of_waypoints']:>10.0f}")


if __name__ == "__main__":
    main()
