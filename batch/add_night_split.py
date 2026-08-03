"""Offline: classify each leaderboard flight as night / mixed / day.

Reads the committed raw ADS-B traces, computes solar elevation at every cruise
waypoint, and writes `night_pct_of_waypoints` + `night_class` back onto
data/processed/leaderboard.parquet.

Pure reshaping: no network, no ERA5, no pycontrails. Safe to re-run.

    .venv/bin/python batch/add_night_split.py

NOTE this does NOT produce night_ef_joules / day_ef_joules. Splitting EF by time
of day needs per-waypoint EF from inside the CoCiP run, which is not in any
committed file. The frontend uses the flight-level signed contrail_ef_joules
that is already on the board, grouped by night_class.
"""
import glob
import gzip
import json
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src.solar import classify, night_pct

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRACES = os.path.join(ROOT, "data", "raw", "traces")
BOARD = os.path.join(ROOT, "data", "processed", "leaderboard.parquet")

# Contrails form at cruise. Filtering to cruise stops taxi/climb/descent —
# which can be a third of the waypoints — from diluting the classification.
CRUISE_FT = 20000


def trace_path(flight_id, traces_dir=TRACES):
    """`aa3410_20250214` -> the matching data/raw/traces/aa3410__2025-02-14.json.gz."""
    hexid, _, date = flight_id.partition("_")
    if len(date) != 8:
        return None
    dashed = f"{date[:4]}-{date[4:6]}-{date[6:]}"
    hits = sorted(glob.glob(os.path.join(str(traces_dir), f"{hexid}__{dashed}.json*")))
    return hits[0] if hits else None


def cruise_points(path):
    """[(lat, lon, utc_timestamp), ...] for the cruise portion of a trace.

    adsb.lol trace rows are [t_offset_s, lat, lon, alt_ft, ...] against a
    file-level epoch `timestamp`. Falls back to every valid row if nothing
    reached cruise (short hops, truncated traces).
    """
    with gzip.open(path, "rt") as fh:
        doc = json.load(fh)
    base = doc.get("timestamp")
    rows = doc.get("trace") or []
    if base is None:
        return []

    def valid(r):
        return (
            len(r) > 3
            and all(isinstance(r[i], (int, float)) for i in (0, 1, 2))
            and isinstance(r[3], (int, float))
        )

    ok = [r for r in rows if valid(r)]
    cruise = [r for r in ok if r[3] >= CRUISE_FT]
    use = cruise or ok
    return [(float(r[1]), float(r[2]), pd.Timestamp(base + float(r[0]), unit="s", tz="UTC")) for r in use]


def main():
    df = pd.read_parquet(BOARD)
    pcts, classes, missing = [], [], 0
    for fid in df["flight_id"]:
        path = trace_path(fid)
        if not path:
            missing += 1
            pcts.append(None)
            classes.append(None)
            continue
        pts = cruise_points(path)
        if not pts:
            missing += 1
            pcts.append(None)
            classes.append(None)
            continue
        pct = round(night_pct(pts), 1)
        pcts.append(pct)
        classes.append(classify(pct))
    df["night_pct_of_waypoints"] = pcts
    df["night_class"] = classes
    df.to_parquet(BOARD, index=False)

    counts = df["night_class"].value_counts(dropna=False).to_dict()
    print(f"night split written to {BOARD}")
    print(f"  flights: {len(df)}, unmatched traces: {missing}")
    print(f"  classes: {counts}")


if __name__ == "__main__":
    main()
