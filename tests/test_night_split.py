"""Per-flight night split (batch/add_night_split.py)."""
import gzip
import json

import pandas as pd

from batch.add_night_split import CRUISE_FT, cruise_points, trace_path


def _write_trace(tmp_path, hexid, date, base_ts, pts):
    p = tmp_path / f"{hexid}__{date}.json.gz"
    with gzip.open(p, "wt") as fh:
        json.dump({"icao": hexid, "timestamp": base_ts, "trace": pts}, fh)
    return p


def test_trace_path_maps_flight_id_to_the_dashed_date(tmp_path):
    _write_trace(tmp_path, "aa3410", "2025-02-14", 1739491200.0, [])
    assert trace_path("aa3410_20250214", tmp_path) is not None


def test_trace_path_returns_none_when_absent(tmp_path):
    assert trace_path("ffffff_20200101", tmp_path) is None


def test_cruise_points_keeps_only_high_altitude_waypoints(tmp_path):
    base = 1739491200.0
    pts = [
        [0.0, 40.8, -73.9, 500],          # on the ground
        [600.0, 41.0, -74.5, CRUISE_FT],  # exactly at the floor -> kept
        [1200.0, 41.5, -75.0, 38000],     # cruise
    ]
    p = _write_trace(tmp_path, "aa3410", "2025-02-14", base, pts)
    got = cruise_points(p)
    assert len(got) == 2
    lat, lon, when = got[0]
    assert lat == 41.0
    assert lon == -74.5
    assert when == pd.Timestamp(base + 600.0, unit="s", tz="UTC")


def test_cruise_points_falls_back_to_all_points_when_none_reach_cruise(tmp_path):
    pts = [[0.0, 40.8, -73.9, 500], [60.0, 40.9, -74.0, 900]]
    p = _write_trace(tmp_path, "aa3410", "2025-02-14", 1739491200.0, pts)
    assert len(cruise_points(p)) == 2


def test_cruise_points_skips_malformed_rows(tmp_path):
    pts = [[0.0, 40.8], [600.0, 41.0, -74.5, 38000], [700.0, None, -74.6, 38000]]
    p = _write_trace(tmp_path, "aa3410", "2025-02-14", 1739491200.0, pts)
    assert len(cruise_points(p)) == 1
