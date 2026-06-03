"""Grow the CoCiP cache with Drake's "Air Drake" Boeing 767 (hex aa5bc4) flights.

Adapted from batch/harvest_more.py. Drake's 767 (N767CJ, B762->B763 in-domain) flies
INFREQUENTLY, so we do NOT apply the night-only pre-filter: we run CoCiP on every
harvested Air Drake flight regardless of day/night. We still COMPUTE and RECORD the
night share (so day/night is captured) plus fuel CO2 and contrail CO2e (GWP100).

Per date (raw trace must already exist under data/raw/traces/aa5bc4__<date>.json.gz):
  1. longest_flight on the day-trace.
  2. fuel + CO2 via OpenAP.
  3. record night share (informational; NO skip).
  4. tight ERA5 window -> run CoCiP -> write
     ~/.cache/tcof_era5/cocip/<hex>_<YYYYMMDD>.parquet (build_dataset format).
  5. append a row to data/reference/harvest_more_log.csv (same schema).

Does NOT touch leaderboard.parquet, owners.csv, or app.py.

Usage: .venv/bin/python batch/harvest_drake.py 2024-06-09 2024-02-12 ...
       (dates whose raw traces already exist under data/raw/traces/)
"""
import csv, glob, math, os, sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src.tracks import load_trace, longest_flight
from src.fuel import fuel_and_co2, resolve_type
from src.era5 import load_arco
from src.contrails import run_cocip, CAP_M
from src.constants import ef_to_co2e_kg, CO2_PER_KG_FUEL
from pycontrails.models.cocip import Cocip
from pycontrails.core.cache import DiskCacheStore

ROOT = os.path.join(os.path.dirname(__file__), "..")
RAW = os.path.join(ROOT, "data", "raw", "traces")
OWNERS_CSV = os.path.join(ROOT, "data", "reference", "owners.csv")
LOG = os.path.join(ROOT, "data", "reference", "harvest_more_log.csv")
PLS = [150, 175, 200, 225, 250, 300, 350]
NIGHT_ELEV = -6.0          # solar elevation below this = night
NIGHT_SHARE_MIN = 0.5      # >= this fraction of cruise waypoints in night => "night" flight
CRUISE_MIN_M = 8000.0

TARGET_HEX = "aa5bc4"

CACHE_DIR = os.environ.get("TCOF_CACHE_DIR", os.path.expanduser("~/.cache/tcof_era5"))
COCDIR = os.path.join(CACHE_DIR, "cocip")
os.makedirs(COCDIR, exist_ok=True)

with open(OWNERS_CSV) as f:
    OWNERS = {r["hex"].lower(): r for r in csv.DictReader(f)}


def solar_elev(lat, lon, when):
    n = when.dayofyear; frac = (when.hour + when.minute / 60) / 24
    g = 2 * math.pi / 365 * (n - 1 + frac - 0.5)
    dec = (0.006918 - 0.399912 * math.cos(g) + 0.070257 * math.sin(g)
           - 0.006758 * math.cos(2 * g) + 0.000907 * math.sin(2 * g))
    eqt = 229.18 * (0.000075 + 0.001868 * math.cos(g) - 0.032077 * math.sin(g)
                    - 0.014615 * math.cos(2 * g) - 0.040849 * math.sin(2 * g))
    tst = (when.hour * 60 + when.minute) + eqt + 4 * lon
    ha = math.radians(tst / 4 - 180); la = math.radians(lat)
    return math.degrees(math.asin(max(-1, min(1,
        math.sin(la) * math.sin(dec) + math.cos(la) * math.cos(dec) * math.cos(ha)))))


def night_share(fl):
    cr = fl[fl["altitude_m"] >= CRUISE_MIN_M]
    if cr.empty:
        cr = fl
    elevs = np.array([solar_elev(r.latitude, r.longitude, pd.Timestamp(r.time))
                      for r in cr.itertuples()])
    return float(np.mean(elevs < NIGHT_ELEV))


def log_row(d):
    new = not os.path.exists(LOG)
    with open(LOG, "a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["hex", "date", "owner", "night_share", "contrail_ef_J",
                        "contrail_co2e_t", "status"])
        w.writerow([d["hex"], d["date"], d["owner"], f"{d['night_share']:.3f}",
                    f"{d.get('ef', ''):}", f"{d.get('co2e_t', ''):}", d["status"]])


def process_one(path, cache):
    base = os.path.basename(path)
    hexid = base.split("__")[0].lower()
    if hexid != TARGET_HEX:
        return None
    owner = OWNERS.get(hexid)
    if not owner:
        print(f"  {hexid}: not in owners.csv"); return None
    meta, df = load_trace(path)
    fl = longest_flight(df)
    if fl is None:
        print(f"  {hexid} {base}: no real flight", flush=True)
        return None
    t0 = pd.Timestamp(fl.time.iloc[0]).floor("h")
    fid = f"{hexid}_{t0.strftime('%Y%m%d')}"
    cpath = os.path.join(COCDIR, f"{fid}.parquet")
    if os.path.exists(cpath):
        print(f"  {owner['owner']:<10} {fid}: already cached, skip", flush=True)
        return None

    ns = night_share(fl)
    daynight = "night" if ns >= NIGHT_SHARE_MIN else "day"
    openap_type, type_source = resolve_type(meta["type"])
    max_alt_m = float(fl["altitude_m"].max())
    in_domain = max_alt_m <= CAP_M
    dur_h = (fl.time.iloc[-1] - fl.time.iloc[0]).total_seconds() / 3600

    # Fuel + CO2 (OpenAP) on the real cruise track
    fuel_kg, fuel_co2_kg, _ot, _src = fuel_and_co2(fl, meta["type"])

    lat0, lon0 = fl.latitude.iloc[0], fl.longitude.iloc[0]
    lat1, lon1 = fl.latitude.iloc[-1], fl.longitude.iloc[-1]
    print(f"  {owner['owner']:<8} {fid} type={meta['type']}->{openap_type}({type_source}) "
          f"FL{max_alt_m/0.3048//100:.0f} in_domain={in_domain} {len(fl)}pts {dur_h:.1f}h "
          f"night={ns:.0%}({daynight}) fuelCO2={fuel_co2_kg/1000:.1f}t "
          f"[{lat0:.2f},{lon0:.2f}]->[{lat1:.2f},{lon1:.2f}]", flush=True)

    # Tight ERA5 window: flight span + CoCiP advection tail.
    t1 = (pd.Timestamp(fl.time.iloc[-1]) + pd.Timedelta(hours=5)).ceil("h")
    tw = (t0.strftime("%Y-%m-%dT%H:%M:%S"), t1.strftime("%Y-%m-%dT%H:%M:%S"))
    print(f"    ERA5 {tw[0]}..{tw[1]} ({int((t1-t0).total_seconds()//3600)+1} hrs)", flush=True)
    met = load_arco(tw, Cocip.met_variables, PLS, cache)
    rad = load_arco(tw, Cocip.rad_variables, -1, cache)
    ef, o = run_cocip(fl, openap_type, met, rad, flight_id=fid)
    keep = [c for c in ("longitude", "latitude", "altitude", "ef") if c in o]
    o[keep].to_parquet(cpath, index=False)
    co2e_t = ef_to_co2e_kg(ef) / 1000.0
    print(f"    CoCiP done: EF={ef:.3e} J  contrail={co2e_t:.2f} t CO2e (GWP100); "
          f"cached -> {cpath}", flush=True)
    log_row({"hex": hexid, "date": t0.strftime("%Y-%m-%d"), "owner": owner["owner"],
             "night_share": ns, "ef": ef, "co2e_t": round(co2e_t, 3), "status": "cached"})
    return (owner["owner"], t0.strftime("%Y-%m-%d"), daynight, in_domain,
            fuel_co2_kg / 1000.0, co2e_t)


def main():
    dates = sys.argv[1:]
    if not dates:
        print("usage: harvest_drake.py <YYYY-MM-DD> ..."); sys.exit(1)
    cache = DiskCacheStore(cache_dir=CACHE_DIR)
    results = []
    for date in dates:
        path = os.path.join(RAW, f"{TARGET_HEX}__{date}.json.gz")
        if not os.path.exists(path):
            print(f"== {date} == NO raw trace ({os.path.basename(path)}); harvest first", flush=True)
            continue
        print(f"== {date} ==", flush=True)
        try:
            r = process_one(path, cache)
        except Exception as e:
            print(f"  !! {date}: {type(e).__name__}: {str(e)[:200]}", flush=True)
            continue
        if r:
            results.append(r)
    print("\n=== Air Drake flights cached this run ===", flush=True)
    print(f"  {'date':<12} {'day/night':<9} {'in_domain':<10} {'fuelCO2 t':>10} {'contrail CO2e t':>16}")
    for owner, d, dn, indom, fco2, co2e in sorted(results, key=lambda x: x[1]):
        print(f"  {d:<12} {dn:<9} {str(indom):<10} {fco2:>10.2f} {co2e:>16.2f}", flush=True)


if __name__ == "__main__":
    main()
