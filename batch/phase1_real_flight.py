"""Phase 1 — full pipeline on a REAL adsb.lol track.

Usage: phase1_real_flight.py <trace_full.json> [evolution_pad_h]
Steps: parse readsb trace -> longest flight -> resample -> OpenAP fuel CO2
       -> CoCiP contrail EF -> efficacy -> EF->CO2e (GWP100/20) -> two numbers + flags.
ERA5 met window is derived from the flight + a contrail-evolution pad, pulled from ARCO (anon).
"""
import sys, os
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src import constants as C
from src.tracks import load_trace, longest_flight
from src.fuel import fuel_and_co2, resolve_type
from src.era5 import load_arco

from pycontrails import Flight
from pycontrails.models.cocip import Cocip
from pycontrails.models.ps_model import PSFlight
from pycontrails.models.humidity_scaling import ExponentialBoostLatitudeCorrectionHumidityScaling
from pycontrails.core.cache import DiskCacheStore

CAP_M = 13000.0  # CoCiP global calibration ceiling ~13 km (~FL426)

# CoCiP's Poll-Schumann performance model supports fewer types than OpenAP.
# Map OpenAP types it lacks to the nearest PS-supported aircraft (contrail perf only;
# fuel CO2 still uses the OpenAP type). Confirmed PS-supported: B763,B752,B77W,B789,GLF5.
PS_PROXY = {"GLF6": "GLF5", "C550": "E145"}


def ps_type_for(openap_type):
    return PS_PROXY.get(openap_type, openap_type)

trace_path = sys.argv[1]
pad_h = float(sys.argv[2]) if len(sys.argv) > 2 else 5.0

meta, df = load_trace(trace_path)
fl_df = longest_flight(df)
if fl_df is None:
    print("No airborne flight in trace."); sys.exit(1)
typecode = meta["type"]
openap_type, type_source = resolve_type(typecode)
max_alt_ft = fl_df["altitude_m"].max() / 0.3048
print(f"{meta['registration']} ({typecode} -> OpenAP {openap_type}/{type_source}) | "
      f"{len(fl_df)} pts, {(fl_df.time.iloc[-1]-fl_df.time.iloc[0])}, max {max_alt_ft:.0f} ft")

# --- fuel CO2 (OpenAP) ---
fuel_kg, fuel_co2_kg, _, _ = fuel_and_co2(fl_df, typecode)

# --- met window from flight + evolution pad ---
t0 = pd.Timestamp(fl_df.time.iloc[0]).floor("h")
t1 = (pd.Timestamp(fl_df.time.iloc[-1]) + pd.Timedelta(hours=pad_h)).ceil("h")
tw = (t0.strftime("%Y-%m-%dT%H:%M:%S"), t1.strftime("%Y-%m-%dT%H:%M:%S"))
print(f"ERA5 window {tw}")
# Cache MUST live outside the iCloud-synced project dir — syncing GBs of ERA5
# chunks causes file locks / IO stalls that silently kill the process.
cache = DiskCacheStore(cache_dir=os.environ.get("TCOF_CACHE_DIR", os.path.expanduser("~/.cache/tcof_era5")))
pls = [150, 175, 200, 225, 250, 300, 350]
print("  loading met (pressure levels)...", flush=True)
met = load_arco(tw, Cocip.met_variables, pls, cache)
print("  loading rad (single level)...", flush=True)
rad = load_arco(tw, Cocip.rad_variables, -1, cache)

# --- contrail (CoCiP) ---
ps_type = ps_type_for(openap_type)
flight = Flight(longitude=fl_df["longitude"].values, latitude=fl_df["latitude"].values,
                altitude=fl_df["altitude_m"].values, time=fl_df["time"].values,
                aircraft_type=ps_type, flight_id=meta["registration"]).resample_and_fill("60s")
cocip = Cocip(met=met, rad=rad, aircraft_performance=PSFlight(),
              humidity_scaling=ExponentialBoostLatitudeCorrectionHumidityScaling(),
              params={"process_emissions": True})
out = cocip.eval(flight)
o = out.dataframe
ef = float(np.nansum(o["ef"])) if "ef" in o else 0.0

co2e_c = C.ef_to_co2e_kg(ef, C.EFFICACY_CENTRAL, "GWP100")
co2e_lo = C.ef_to_co2e_kg(ef, C.EFFICACY_LOW, "GWP100")
co2e_hi = C.ef_to_co2e_kg(ef, C.EFFICACY_HIGH, "GWP100")
co2e_20 = C.ef_to_co2e_kg(ef, C.EFFICACY_CENTRAL, "GWP20")
ratio = 100 * co2e_c / fuel_co2_kg if fuel_co2_kg else float("nan")

bizjet_flag = max_alt_ft * 0.3048 > CAP_M
print("\n" + "=" * 58)
print(f"PHASE 1 — {meta['registration']} {meta['desc']}")
print("=" * 58)
print(f"  fuel CO2 (OpenAP {openap_type}/{type_source}) : {fuel_co2_kg/1000:7.1f} t")
print(f"  contrail Energy Forcing               : {ef:.2e} J")
print(f"  contrail CO2e GWP100 [low/cen/high]    : {co2e_lo/1000:.1f}/{co2e_c/1000:.1f}/{co2e_hi/1000:.1f} t")
print(f"  contrail CO2e GWP20 (central)          : {co2e_20/1000:.1f} t")
print(f"  combined CO2e (GWP100)                 : {(fuel_co2_kg+co2e_c)/1000:.1f} t")
print(f"  contrail / fuel-CO2 (GWP100)           : {ratio:.0f}%")
flags = []
if type_source not in ("native", "synonym"): flags.append(f"PROXY-TYPE({type_source})")
if bizjet_flag: flags.append(f"BIZJET-ALT>13km(FL{max_alt_ft//100:.0f}): contrail UNDER-counted")
print(f"  flags: {', '.join(flags) if flags else 'none'}")
print("=" * 58)
