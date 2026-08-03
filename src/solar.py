"""Solar elevation and day/night classification.

The single copy. `batch/build_comparators.py`, `batch/scan_comparators.py`,
`batch/harvest_more.py` and `batch/harvest_drake.py` each carried an identical
private copy of `solar_elev`; they import from here instead.

NOAA low-precision solar position algorithm — good to ~0.1 deg, far tighter than
the 6-degree civil-twilight threshold we test against.
"""
import math

# Sun more than 6 degrees below the horizon = night (civil twilight ended).
# Contrail radiative forcing flips sign around here: no shortwave to reflect.
NIGHT_ELEV = -6.0

# A flight is 'night' if at least NIGHT_SHARE of its cruise waypoints are dark,
# 'day' if at most DAY_SHARE are. See classify().
NIGHT_SHARE = 70.0
DAY_SHARE = 30.0


def solar_elev(lat, lon, when):
    """Solar elevation in degrees at (lat, lon) at UTC timestamp `when`."""
    n = when.dayofyear
    frac = (when.hour + when.minute / 60) / 24
    g = 2 * math.pi / 365 * (n - 1 + frac - 0.5)
    dec = (0.006918 - 0.399912 * math.cos(g) + 0.070257 * math.sin(g)
           - 0.006758 * math.cos(2 * g) + 0.000907 * math.sin(2 * g))
    eqt = 229.18 * (0.000075 + 0.001868 * math.cos(g) - 0.032077 * math.sin(g)
                    - 0.014615 * math.cos(2 * g) - 0.040849 * math.sin(2 * g))
    tst = (when.hour * 60 + when.minute) + eqt + 4 * lon
    ha = math.radians(tst / 4 - 180)
    la = math.radians(lat)
    return math.degrees(math.asin(max(-1, min(1, math.sin(la) * math.sin(dec)
                                              + math.cos(la) * math.cos(dec) * math.cos(ha)))))


def night_pct(points):
    """Percentage (0-100) of (lat, lon, when) points that are in darkness."""
    if not points:
        return 0.0
    dark = sum(1 for lat, lon, when in points if solar_elev(lat, lon, when) < NIGHT_ELEV)
    return 100.0 * dark / len(points)


def classify(pct):
    """'night' | 'mixed' | 'day' from a night percentage."""
    if pct >= NIGHT_SHARE:
        return "night"
    if pct <= DAY_SHARE:
        return "day"
    return "mixed"
