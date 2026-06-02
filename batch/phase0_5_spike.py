"""Phase 0.5 — physics spike.

Goal (IMPLEMENTATION_PLAN §9): on ONE real-ish flight, pull ERA5 via ERA5ARCO(anon),
run CoCiP -> Energy Forcing (J), apply efficacy, bridge to CO2e, and check the
contrail/fuel-CO2 ratio lands in the ~33-63% (GWP100) expectation — within an order
of magnitude. No UI, no OpenSky. If this produces garbage we learn it in week one.
"""
import sys, os
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src import constants as C

from pycontrails import Flight
from pycontrails.models.cocip import Cocip
from pycontrails.models.ps_model import PSFlight
from pycontrails.models.humidity_scaling import ExponentialBoostLatitudeCorrectionHumidityScaling
from pycontrails.datalib.ecmwf import ERA5ARCO
from pycontrails.core.cache import DiskCacheStore


def great_circle_track(lat1, lon1, lat2, lon2, n):
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    d = 2 * np.arcsin(np.sqrt(np.sin((lat2 - lat1) / 2) ** 2 +
                              np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2))
    f = np.linspace(0, 1, n)
    a = np.sin((1 - f) * d) / np.sin(d)
    b = np.sin(f * d) / np.sin(d)
    x = a * np.cos(lat1) * np.cos(lon1) + b * np.cos(lat2) * np.cos(lon2)
    y = a * np.cos(lat1) * np.sin(lon1) + b * np.cos(lat2) * np.sin(lon2)
    z = a * np.sin(lat1) + b * np.sin(lat2)
    return np.degrees(np.arctan2(z, np.sqrt(x ** 2 + y ** 2))), np.degrees(np.arctan2(y, x))


# --- 1. One real-ish flight: JFK -> LHR, winter night (strong warming contrails), FL360 ---
N = 80
lats, lons = great_circle_track(40.64, -73.78, 51.47, -0.45, N)
start = np.datetime64("2024-01-15T22:00:00")
dur_h = 7.0
times = start + (np.arange(N) / (N - 1) * dur_h * 3600).astype("timedelta64[s]")
# cruise FL360 with short climb/descent
alt_ft = np.full(N, 36000.0)
alt_ft[:6] = np.linspace(8000, 36000, 6)
alt_ft[-6:] = np.linspace(36000, 8000, 6)
altitude_m = alt_ft * 0.3048

fl = Flight(
    longitude=lons, latitude=lats, altitude=altitude_m,
    time=times, aircraft_type="B77W", flight_id="spike_BA112",
)
print(f"Flight: {N} pts, JFK->LHR, dep {start}, {dur_h}h, FL360, B77W")
print(f"  bbox lon[{lons.min():.1f},{lons.max():.1f}] lat[{lats.min():.1f},{lats.max():.1f}]")

# --- 2. ERA5ARCO met + rad (anonymous public bucket) ---
cache = DiskCacheStore(cache_dir=os.environ.get("TCOF_CACHE_DIR", os.path.expanduser("~/.cache/tcof_era5")))
time_window = ("2024-01-15T20:00:00", "2024-01-16T06:00:00")
pressure_levels = [150, 175, 200, 225, 250, 300, 350]
print(f"\nPulling ERA5ARCO: {time_window}, levels {pressure_levels} (whole-globe chunks, ~min)...")

era5pl = ERA5ARCO(time=time_window, variables=Cocip.met_variables, pressure_levels=pressure_levels, cachestore=cache)
era5sl = ERA5ARCO(time=time_window, variables=Cocip.rad_variables, pressure_levels=-1, cachestore=cache)
met = era5pl.open_metdataset()
rad = era5sl.open_metdataset()
print("  met/rad MetDatasets loaded.")

# --- 3. Run CoCiP ---
# Resample so segments stay under max_seg_length_m (avoids artificially short contrail life).
fl = fl.resample_and_fill("60s")
print(f"\nResampled flight to {len(fl)} pts. Running CoCiP...")
cocip = Cocip(
    met=met, rad=rad,
    aircraft_performance=PSFlight(),
    humidity_scaling=ExponentialBoostLatitudeCorrectionHumidityScaling(),
    params={"process_emissions": True},
)
out = cocip.eval(fl)
df = out.dataframe

# --- 4. Energy Forcing -> CO2e; fuel -> CO2 ---
ef_total_J = float(np.nansum(df["ef"])) if "ef" in df else 0.0

# fuel: integrate fuel_flow (kg/s) over dt
dt_s = np.diff(df["time"].values).astype("timedelta64[s]").astype(float)
ff = df["fuel_flow"].values[:-1] if "fuel_flow" in df else np.zeros(len(df) - 1)
fuel_kg = float(np.nansum(ff * dt_s))
fuel_co2_kg = fuel_kg * C.CO2_PER_KG_FUEL

co2e_central = C.ef_to_co2e_kg(ef_total_J, C.EFFICACY_CENTRAL, "GWP100")
co2e_low = C.ef_to_co2e_kg(ef_total_J, C.EFFICACY_LOW, "GWP100")
co2e_high = C.ef_to_co2e_kg(ef_total_J, C.EFFICACY_HIGH, "GWP100")
co2e_gwp20 = C.ef_to_co2e_kg(ef_total_J, C.EFFICACY_CENTRAL, "GWP20")

ratio = co2e_central / fuel_co2_kg if fuel_co2_kg else float("nan")

print("\n" + "=" * 60)
print("PHASE 0.5 RESULT")
print("=" * 60)
print(f"  contrail Energy Forcing  : {ef_total_J:.3e} J")
print(f"  fuel burned              : {fuel_kg/1000:.1f} t")
print(f"  fuel CO2                 : {fuel_co2_kg/1000:.1f} t")
print(f"  contrail CO2e (GWP100)   : {co2e_central/1000:.1f} t  [low {co2e_low/1000:.1f} / high {co2e_high/1000:.1f}]")
print(f"  contrail CO2e (GWP20)    : {co2e_gwp20/1000:.1f} t")
print(f"  combined CO2e (GWP100)   : {(fuel_co2_kg+co2e_central)/1000:.1f} t")
print(f"  >>> contrail / fuel-CO2  : {ratio*100:.0f}%   (expectation ~33-63% GWP100)")
ok = 0.05 <= ratio <= 5.0  # order-of-magnitude done-criterion
print(f"  >>> within order of magnitude of expectation: {'YES' if ok else 'NO -- investigate'}")
print("=" * 60)
