"""Grow the CoCiP cache with NEW celebrity night flights (contrail offenders).

Per date:
  1. (harvest separately via harvest_traces.py — downloads/extracts/deletes tarball)
  2. For each owner trace harvested for that date: NIGHT pre-filter on the cruise track.
     Skip mostly-daytime flights BEFORE any ERA5/CoCiP (cost optimisation).
  3. For surviving night flights: fetch the TIGHT union of ERA5 hours, run CoCiP,
     write ~/.cache/tcof_era5/cocip/<hex>_<YYYYMMDD>.parquet (build_dataset format).
  4. Append a row to data/reference/harvest_more_log.csv.

Does NOT touch leaderboard.parquet or owners.csv.

Usage: python batch/harvest_more.py 2024-12-14 2024-12-20 ...
       (dates whose raw traces already exist under data/raw/traces/)
"""
import csv, glob, math, os, sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src.tracks import load_trace, longest_flight
from src.fuel import fuel_and_co2, resolve_type
from src.era5 import load_arco
from src.contrails import run_cocip
from src.constants import ef_to_co2e_kg
from pycontrails.models.cocip import Cocip
from pycontrails.core.cache import DiskCacheStore

ROOT = os.path.join(os.path.dirname(__file__), "..")
RAW = os.path.join(ROOT, "data", "raw", "traces")
OWNERS_CSV = os.path.join(ROOT, "data", "reference", "owners.csv")
LOG = os.path.join(ROOT, "data", "reference", "harvest_more_log.csv")
PLS = [150, 175, 200, 225, 250, 300, 350]
NIGHT_ELEV = -6.0          # solar elevation below this = night
NIGHT_SHARE_MIN = 0.5      # require >= this fraction of cruise waypoints in night
CRUISE_MIN_M = 8000.0      # only consider high-altitude (cruise) waypoints for the filter

CACHE_DIR = os.environ.get("TCOF_CACHE_DIR", os.path.expanduser("~/.cache/tcof_era5"))
COCDIR = os.path.join(CACHE_DIR, "cocip")
os.makedirs(COCDIR, exist_ok=True)

with open(OWNERS_CSV) as f:
    OWNERS = {r["hex"].lower(): r for r in csv.DictReader(f)}


def solar_elev(lat, lon, when):  # when = pandas UTC Timestamp
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
    """Fraction of cruise waypoints (alt>=CRUISE_MIN_M) flown in night (elev<NIGHT_ELEV)."""
    cr = fl[fl["altitude_m"] >= CRUISE_MIN_M]
    if cr.empty:
        cr = fl
    elevs = [solar_elev(r.latitude, r.longitude, pd.Timestamp(r.time))
             for r in cr.itertuples()]
    elevs = np.array(elevs)
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
    date = base.split("__")[1].replace(".json.gz", "")
    owner = OWNERS.get(hexid)
    if not owner:
        return None
    meta, df = load_trace(path)
    fl = longest_flight(df)
    if fl is None:
        print(f"  {hexid} {date}: no real flight", flush=True)
        return None
    t0 = pd.Timestamp(fl.time.iloc[0]).floor("h")
    fid = f"{hexid}_{t0.strftime('%Y%m%d')}"
    cpath = os.path.join(COCDIR, f"{fid}.parquet")
    if os.path.exists(cpath):
        print(f"  {owner['owner']:<22} {fid}: already cached, skip", flush=True)
        return None

    ns = night_share(fl)
    openap_type, type_source = resolve_type(meta["type"])
    max_alt_m = float(fl["altitude_m"].max())
    dur_h = (fl.time.iloc[-1] - fl.time.iloc[0]).total_seconds() / 3600
    print(f"  {owner['owner']:<22} {fid} {meta['type']}->{openap_type} "
          f"FL{max_alt_m/0.3048//100:.0f} {len(fl)}pts {dur_h:.1f}h night={ns:.0%}", flush=True)

    if ns < NIGHT_SHARE_MIN:
        print(f"    -> daytime (night={ns:.0%} < {NIGHT_SHARE_MIN:.0%}); SKIP CoCiP", flush=True)
        log_row({"hex": hexid, "date": t0.strftime("%Y-%m-%d"), "owner": owner["owner"],
                 "night_share": ns, "status": "skip_daytime"})
        return None

    # Tight ERA5 window: flight span + CoCiP advection tail, hour-floored/ceiled.
    t1 = (pd.Timestamp(fl.time.iloc[-1]) + pd.Timedelta(hours=5)).ceil("h")
    tw = (t0.strftime("%Y-%m-%dT%H:%M:%S"), t1.strftime("%Y-%m-%dT%H:%M:%S"))
    print(f"    night flight -> ERA5 {tw[0]}..{tw[1]} ({int((t1-t0).total_seconds()//3600)+1} hrs)", flush=True)
    met = load_arco(tw, Cocip.met_variables, PLS, cache)
    rad = load_arco(tw, Cocip.rad_variables, -1, cache)
    ef, o = run_cocip(fl, openap_type, met, rad, flight_id=fid)
    keep = [c for c in ("longitude", "latitude", "altitude", "ef") if c in o]
    o[keep].to_parquet(cpath, index=False)
    co2e_t = ef_to_co2e_kg(ef) / 1000.0
    print(f"    CoCiP done: EF={ef:.3e} J  contrail={co2e_t:.2f} t CO2e (GWP100)", flush=True)
    log_row({"hex": hexid, "date": t0.strftime("%Y-%m-%d"), "owner": owner["owner"],
             "night_share": ns, "ef": ef, "co2e_t": round(co2e_t, 3), "status": "cached"})
    return (owner["owner"], t0.strftime("%Y-%m-%d"), ns, ef, co2e_t)


def main():
    dates = sys.argv[1:]
    if not dates:
        print("usage: harvest_more.py <YYYY-MM-DD> ..."); sys.exit(1)
    cache = DiskCacheStore(cache_dir=CACHE_DIR)
    results = []
    for date in dates:
        traces = sorted(glob.glob(os.path.join(RAW, f"*__{date}.json.gz")))
        owner_traces = [p for p in traces
                        if os.path.basename(p).split("__")[0].lower() in OWNERS]
        print(f"== {date} == {len(owner_traces)} owner traces", flush=True)
        for p in owner_traces:
            try:
                r = process_one(p, cache)
            except Exception as e:
                print(f"  !! {os.path.basename(p)}: {type(e).__name__}: {str(e)[:140]}", flush=True)
                continue
            if r:
                results.append(r)
    print("\n=== night flights cached this run ===", flush=True)
    for owner, d, ns, ef, co2e in sorted(results, key=lambda x: -x[4]):
        print(f"  {owner:<22} {d}  night={ns:.0%}  {co2e:6.2f} t CO2e", flush=True)


if __name__ == "__main__":
    main()
