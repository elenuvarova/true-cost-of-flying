"""Offline batch: curated traces -> leaderboard.parquet + decimated track GeoJSON.

This is the only place CoCiP/ERA5 run. The deployed app reads the committed outputs only.
Seed registry is inline for now (Phase 2); Phase 3 expands to the full curated set.
"""
import sys, os, json, csv, glob
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src.tracks import load_trace, longest_flight
from src.fuel import fuel_and_co2, resolve_type
from src.era5 import load_arco
from src.contrails import run_cocip
from src.fuse import build_row, assign_tiers
from pycontrails.models.cocip import Cocip
from pycontrails.core.cache import DiskCacheStore

ROOT = os.path.join(os.path.dirname(__file__), "..")
OUT = os.path.join(ROOT, "data", "processed")
TRACKS = os.path.join(OUT, "tracks")
RAW = os.path.join(ROOT, "data", "raw", "traces")
PLS = [150, 175, 200, 225, 250, 300, 350]
MAX_VTX = 500

with open(os.path.join(ROOT, "data", "reference", "owners.csv")) as f:
    OWNERS = {r["hex"].lower(): r for r in csv.DictReader(f)}


def decimate(df, n=MAX_VTX):
    if len(df) <= n:
        return df
    idx = np.linspace(0, len(df) - 1, n).round().astype(int)
    return df.iloc[np.unique(idx)].reset_index(drop=True)


def track_geojson(o, row):
    """Per-segment LineStrings coloured by each segment's contrail EF share."""
    o = o.dropna(subset=["longitude", "latitude"]).reset_index(drop=True)
    o = decimate(o)
    ef = o["ef"].fillna(0.0).values if "ef" in o else np.zeros(len(o))
    ef_max = float(np.nanmax(np.abs(ef))) or 1.0
    feats = []
    for i in range(len(o) - 1):
        share = float(ef[i]) / ef_max  # -1..1 (cooling..warming)
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


def process_trace(path, cache):
    """One harvested trace (hex__YYYY-MM-DD.json.gz) -> (row, cocip_waypoints) or None."""
    base = os.path.basename(path)
    hexid = base.split("__")[0].lower()
    owner = OWNERS.get(hexid)
    if not owner:
        return None
    meta, df = load_trace(path)
    fl = longest_flight(df)
    if fl is None:
        return None
    openap_type, type_source = resolve_type(meta["type"])
    max_alt_m = float(fl["altitude_m"].max())
    t0 = pd.Timestamp(fl.time.iloc[0]).floor("h")
    print(f"  {owner['owner']:<24} {hexid} {t0.date()} {meta['type']}->{openap_type}/{type_source} "
          f"FL{max_alt_m/0.3048//100:.0f} {len(fl)}pts", flush=True)

    fuel_kg, fuel_co2_kg, _, _ = fuel_and_co2(fl, meta["type"])
    fid = f"{hexid}_{t0.strftime('%Y%m%d')}"

    # Cache the CoCiP waypoints (incl. per-point `ef`) per flight so re-runs after
    # adding owners don't recompute ERA5+CoCiP. Small (~hundreds of rows).
    cocdir = os.path.join(os.path.expanduser(os.environ.get("TCOF_CACHE_DIR", "~/.cache/tcof_era5")), "cocip")
    os.makedirs(cocdir, exist_ok=True)
    cpath = os.path.join(cocdir, f"{fid}.parquet")
    if os.path.exists(cpath):
        o = pd.read_parquet(cpath)
        ef = float(np.nansum(o["ef"])) if "ef" in o else 0.0
        print("    (cached CoCiP)", flush=True)
    else:
        t1 = (pd.Timestamp(fl.time.iloc[-1]) + pd.Timedelta(hours=5)).ceil("h")
        tw = (t0.strftime("%Y-%m-%dT%H:%M:%S"), t1.strftime("%Y-%m-%dT%H:%M:%S"))
        met = load_arco(tw, Cocip.met_variables, PLS, cache)
        rad = load_arco(tw, Cocip.rad_variables, -1, cache)
        ef, o = run_cocip(fl, openap_type, met, rad, flight_id=fid)
        keep = [c for c in ("longitude", "latitude", "altitude", "ef") if c in o]
        o[keep].to_parquet(cpath, index=False)
    route = (f"{fl.latitude.iloc[0]:.1f},{fl.longitude.iloc[0]:.1f}"
             f"->{fl.latitude.iloc[-1]:.1f},{fl.longitude.iloc[-1]:.1f}")
    row = build_row(
        icao24=hexid, flight_id=fid,
        owner_label=owner["owner"], owner_confidence=owner["owner_confidence"],
        registration=owner["registration"], ac_type=owner["ac_type"],
        openap_type=openap_type, type_source=type_source,
        dep_time=str(fl.time.iloc[0]), route=route,
        fuel_kg=fuel_kg, fuel_co2_kg=fuel_co2_kg, ef_joules=ef, max_alt_m=max_alt_m,
    )
    return row, o


def main():
    os.makedirs(TRACKS, exist_ok=True)
    cache = DiskCacheStore(cache_dir=os.environ.get("TCOF_CACHE_DIR", os.path.expanduser("~/.cache/tcof_era5")))
    traces = sorted(glob.glob(os.path.join(RAW, "*.json.gz")))
    print(f"processing {len(traces)} harvested traces...")
    rows, geos = [], []
    for p in traces:
        try:
            res = process_trace(p, cache)
        except Exception as e:
            print(f"  !! {os.path.basename(p)}: {type(e).__name__}: {str(e)[:100]}"); continue
        if res:
            rows.append(res[0]); geos.append(res)

    rows = assign_tiers(rows)
    pd.DataFrame(rows).to_parquet(os.path.join(OUT, "leaderboard.parquet"), index=False)
    for row, o in geos:
        with open(os.path.join(TRACKS, f"{row['flight_id']}.geojson"), "w") as f:
            json.dump(track_geojson(o, row), f)

    print(f"\nWrote leaderboard.parquet ({len(rows)} rows) + {len(geos)} track GeoJSONs to {OUT}")
    for r in rows:
        print(f"  [{r['tier']:>6}] {r['owner_label']:<32} {r['combined_co2e_central']/1000:6.1f} t "
              f"(fuel {r['fuel_co2_kg']/1000:.1f} + contrail {r['contrail_co2e_central']/1000:.1f}, "
              f"+{r['contrail_pct_of_fuel']:.0f}%) flags:"
              f"{'P' if r['proxy_type_flag'] else ''}{'B' if r['bizjet_alt_flag'] else ''}")


if __name__ == "__main__":
    main()
