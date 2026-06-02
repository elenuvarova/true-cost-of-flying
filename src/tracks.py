"""Parse adsb.lol / readsb `trace_full_<hex>.json` into clean flight segments.

Trace format (readsb): top-level {icao, r (reg), t (type), desc, timestamp, trace:[...]}.
Each trace point is an array: [secs_after_ts, lat, lon, alt_ft|"ground"|null, gs_kt,
track_deg, flags, baro_rate_fpm, details|null, source_type, geom_alt_ft?, ...].
We use idx 0,1,2,3,4 (time, lat, lon, baro-altitude-ft, groundspeed-kt).
"""
import gzip
import json
import numpy as np
import pandas as pd

FT_TO_M = 0.3048


def _open_maybe_gzip(path):
    """readsb trace files are gzip-compressed despite the .json extension."""
    with open(path, "rb") as f:
        head = f.read(2)
    return gzip.open(path, "rt") if head == b"\x1f\x8b" else open(path)


def load_trace(path):
    """Return (meta dict, points DataFrame[time, latitude, longitude, altitude_m, gs_kt])."""
    with _open_maybe_gzip(path) as f:
        d = json.load(f)
    meta = {"icao": d.get("icao"), "registration": d.get("r"),
            "type": (d.get("t") or "").upper(), "desc": d.get("desc")}
    base = pd.Timestamp(d["timestamp"], unit="s", tz="UTC")
    rows = []
    for p in d.get("trace", []):
        alt = p[3]
        if alt == "ground" or alt is None:
            continue
        lat, lon = p[1], p[2]
        if lat is None or lon is None:
            continue
        gs = p[4] if len(p) > 4 and p[4] is not None else np.nan
        rows.append((base + pd.Timedelta(seconds=p[0]), lat, lon, float(alt) * FT_TO_M, gs))
    df = pd.DataFrame(rows, columns=["time", "latitude", "longitude", "altitude_m", "gs_kt"])
    df = df.sort_values("time").drop_duplicates(subset="time").reset_index(drop=True)
    return meta, df


def split_flights(df, max_gap_s=1800, min_dur_s=3600, min_cruise_m=6000):
    """Split an aircraft's day-trace into individual flights; keep airborne legs."""
    if df.empty:
        return []
    gaps = df["time"].diff().dt.total_seconds().fillna(0)
    seg_id = (gaps > max_gap_s).cumsum()
    flights = []
    for _, g in df.groupby(seg_id):
        dur = (g["time"].iloc[-1] - g["time"].iloc[0]).total_seconds()
        if dur >= min_dur_s and g["altitude_m"].max() >= min_cruise_m:
            flights.append(g.reset_index(drop=True))
    return flights


def longest_flight(df, **kw):
    flights = split_flights(df, **kw)
    if not flights:
        return None
    return max(flights, key=lambda g: (g["time"].iloc[-1] - g["time"].iloc[0]).total_seconds())
