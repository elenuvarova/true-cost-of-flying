"""Solar elevation + night classification (src/solar.py)."""
import pandas as pd
import pytest

from src.solar import NIGHT_ELEV, classify, night_pct, solar_elev


def test_london_noon_midsummer_is_high_in_the_sky():
    when = pd.Timestamp("2025-06-21T12:00:00Z")
    assert solar_elev(51.5, 0.0, when) > 55


def test_london_midnight_midsummer_is_below_the_horizon():
    when = pd.Timestamp("2025-06-22T00:00:00Z")
    assert solar_elev(51.5, 0.0, when) < 0


def test_new_york_deep_night_is_below_the_night_threshold():
    # 02:00 UTC on 14 Feb is ~21:00 local the previous evening in New York.
    when = pd.Timestamp("2025-02-14T02:00:00Z")
    assert solar_elev(40.8, -73.9, when) < NIGHT_ELEV


def test_elevation_is_bounded():
    for lat in (-89.0, 0.0, 89.0):
        for hour in range(0, 24, 3):
            e = solar_elev(lat, 0.0, pd.Timestamp(f"2025-03-15T{hour:02d}:00:00Z"))
            assert -90.0 <= e <= 90.0


def test_night_pct_all_night():
    pts = [(40.8, -73.9, pd.Timestamp("2025-02-14T02:00:00Z"))] * 10
    assert night_pct(pts) == 100.0


def test_night_pct_empty_is_zero():
    assert night_pct([]) == 0.0


@pytest.mark.parametrize(
    "pct,expected",
    [(100.0, "night"), (70.0, "night"), (69.9, "mixed"), (30.1, "mixed"), (30.0, "day"), (0.0, "day")],
)
def test_classify_thresholds(pct, expected):
    assert classify(pct) == expected
