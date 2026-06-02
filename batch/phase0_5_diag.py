"""Phase 0.5 diagnostics: why is the contrail weak? Inspect formation + sweep altitude.

Reuses the cached ERA5 (data/cache). Shows: SAC/persistent-contrail counts, EF stats,
and an altitude sweep FL320..FL420 (the 'what-if altitude' lever) to find ISSR crossings.
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
    a = np.sin((1 - f) * d) / np.sin(d); b = np.sin(f * d) / np.sin(d)
    x = a * np.cos(lat1) * np.cos(lon1) + b * np.cos(lat2) * np.cos(lon2)
    y = a * np.cos(lat1) * np.sin(lon1) + b * np.cos(lat2) * np.sin(lon2)
    z = a * np.sin(lat1) + b * np.sin(lat2)
    return np.degrees(np.arctan2(z, np.sqrt(x ** 2 + y ** 2))), np.degrees(np.arctan2(y, x))


cache = DiskCacheStore(cache_dir=os.path.join(os.path.dirname(__file__), "..", "data", "cache"))
time_window = ("2024-01-15T20:00:00", "2024-01-16T06:00:00")
pressure_levels = [150, 175, 200, 225, 250, 300, 350]
met = ERA5ARCO(time=time_window, variables=Cocip.met_variables, pressure_levels=pressure_levels, cachestore=cache).open_metdataset()
rad = ERA5ARCO(time=time_window, variables=Cocip.rad_variables, pressure_levels=-1, cachestore=cache).open_metdataset()

N = 80
lats, lons = great_circle_track(40.64, -73.78, 51.47, -0.45, N)
start = np.datetime64("2024-01-15T22:00:00")
times = start + (np.arange(N) / (N - 1) * 7.0 * 3600).astype("timedelta64[s]")

print(f"{'FL':>5} {'EF (J)':>11} {'persist_wp':>11} {'contrail_t':>11} {'CO2e_t(GWP100)':>15} {'ratio%':>7}")
for fl_level in [320, 340, 360, 380, 400, 420]:
    alt_m = fl_level * 100 * 0.3048
    altitude = np.full(N, alt_m)
    altitude[:6] = np.linspace(8000, alt_m, 6)
    altitude[-6:] = np.linspace(alt_m, 8000, 6)
    fl = Flight(longitude=lons, latitude=lats, altitude=altitude, time=times,
                aircraft_type="B77W", flight_id=f"FL{fl_level}").resample_and_fill("60s")
    cocip = Cocip(met=met, rad=rad, aircraft_performance=PSFlight(),
                  humidity_scaling=ExponentialBoostLatitudeCorrectionHumidityScaling(),
                  params={"process_emissions": True})
    out = cocip.eval(fl)
    df = out.dataframe
    ef = float(np.nansum(df["ef"])) if "ef" in df else 0.0
    persist = int(np.nansum(df.get("persistent_contrail", pd.Series([0])))) if "persistent_contrail" in df else (
        int((df["ef"].abs() > 0).sum()) if "ef" in df else 0)
    dt = np.diff(df["time"].values).astype("timedelta64[s]").astype(float)
    ff = df["fuel_flow"].values[:-1] if "fuel_flow" in df else np.zeros(len(df) - 1)
    fuel_co2 = float(np.nansum(ff * dt)) * C.CO2_PER_KG_FUEL
    co2e = C.ef_to_co2e_kg(ef, C.EFFICACY_CENTRAL, "GWP100")
    ratio = 100 * co2e / fuel_co2 if fuel_co2 else float("nan")
    print(f"{fl_level:>5} {ef:>11.2e} {persist:>11} {co2e/1000:>11.2f} {(fuel_co2+co2e)/1000:>15.1f} {ratio:>7.0f}")
