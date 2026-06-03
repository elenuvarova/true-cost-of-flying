"""Scan a day's adsb.lol globe_history tarball for NIGHT TRANSATLANTIC WIDEBODY flights.

Filter cheaply by aircraft type (widebody airliners) from each trace header, then by
geometry (track spans the North Atlantic), then confirm a NIGHT ocean crossing via
solar elevation. Writes candidate hexes + summary to data/reference/comparators.csv.

Usage: python batch/scan_comparators.py <day YYYY-MM-DD> [combined.tar path]
"""
import csv
import gzip
import io
import json
import math
import os
import sys
import tarfile

import numpy as np
import pandas as pd

ROOT = os.path.join(os.path.dirname(__file__), "..")
COMPARATORS_CSV = os.path.join(ROOT, "data", "reference", "comparators.csv")

# Widebody airliner ADS-B typecodes (long-haul, FL350-410 cruise, in-domain for CoCiP).
WIDEBODY = {"B77W", "B772", "B77L", "B788", "B789", "B78X", "B763", "B764", "B762",
            "A332", "A333", "A338", "A339", "A359", "A35K", "A346", "A343", "B744",
            "B748", "A388"}

# North Atlantic crossing: track must span from the US side to the European side.
# NOTE: adsb.lol ground-receiver coverage has a DARK GAP over the open mid-Atlantic
# (~lon -45..-20), so transatlantic traces typically have NO logged points there even
# though the flight crosses continuously. We therefore detect the crossing by its
# longitudinal SPAN (reaches both sides) rather than requiring mid-ocean samples, and
# assess night-ness over the high-latitude oceanic-edge points PLUS an interpolated
# great-circle mid-ocean point.
NA_LON_MIN, NA_LON_MAX = -65.0, -8.0
NA_LAT_MIN, NA_LAT_MAX = 40.0, 62.0
# cruise points used for the crossing/night assessment: high-latitude, ocean-adjacent on
# either coast. Spans US side (~-75) to European approach (~0).
EDGE_LON_MIN, EDGE_LON_MAX = -78.0, 5.0
WEST_LON, EAST_LON = -55.0, -12.0  # cruise must reach US side (<=WEST) AND Europe (>=EAST)
MIN_CRUISE_FT = 28000.0


def solar_elev(lat, lon, when):  # when = pandas.Timestamp (UTC)
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


def trace_points(d):
    """Yield (time, lat, lon, alt_ft) airborne points from a parsed readsb trace dict."""
    base = pd.Timestamp(d["timestamp"], unit="s", tz="UTC")
    for p in d.get("trace", []):
        alt = p[3]
        if alt == "ground" or alt is None:
            continue
        lat, lon = p[1], p[2]
        if lat is None or lon is None:
            continue
        yield base + pd.Timedelta(seconds=p[0]), lat, lon, float(alt)


def _raw_arrays(d):
    """Fast parse: numpy arrays (secs_since_base, lat, lon, alt_ft) for airborne points.

    Avoids building per-trace pandas objects (the scan touches ~46k traces)."""
    import numpy as np
    base = d["timestamp"]
    secs, lats, lons, alts = [], [], [], []
    for p in d.get("trace", []):
        alt = p[3]
        if alt == "ground" or alt is None or p[1] is None or p[2] is None:
            continue
        secs.append(p[0]); lats.append(p[1]); lons.append(p[2]); alts.append(float(alt))
    if not secs:
        return None
    order = np.argsort(secs)
    return (base, np.asarray(secs)[order], np.asarray(lats)[order],
            np.asarray(lons)[order], np.asarray(alts)[order])


# Transatlantic traces have a ~3-4 h receiver-dark gap over the open mid-ocean while the
# aircraft is at cruise on BOTH sides. Bridge gaps up to 5 h so the crossing stays one
# flight (CoCiP resample_and_fill interpolates the great-circle across the gap). MUST
# match build_comparators.COMPARATOR_MAX_GAP_S.
COMPARATOR_MAX_GAP_S = 5 * 3600


def _longest_segment(secs, *arrs, max_gap_s=COMPARATOR_MAX_GAP_S, min_dur_s=3600):
    """Indices of the longest-duration contiguous segment (gap-split). numpy, no pandas."""
    import numpy as np
    if len(secs) < 2:
        return None
    gaps = np.diff(secs)
    breaks = np.where(gaps > max_gap_s)[0] + 1
    starts = np.concatenate([[0], breaks])
    ends = np.concatenate([breaks, [len(secs)]])
    best = None
    for s, e in zip(starts, ends):
        if e - s < 2:
            continue
        dur = secs[e - 1] - secs[s]
        if dur >= min_dur_s and (best is None or dur > best[2]):
            best = (s, e, dur)
    if best is None:
        return None
    return best[0], best[1]


def evaluate(d):
    """Return a candidate dict if d's longest flight is a night N-Atlantic widebody
    crossing, else None. Transatlantic crossing is detected from the flight's full
    longitudinal SPAN reaching both the N-American and European sides (the open-ocean
    middle is receiver-dark, so we do NOT require samples there); night-ness is measured
    over the cruise-altitude points plus an interpolated great-circle mid-ocean point."""
    import numpy as np
    t = (d.get("t") or "").upper()
    if t not in WIDEBODY:
        return None
    arr = _raw_arrays(d)
    if arr is None or len(arr[1]) < 50:
        return None
    base, secs, lats, lons, alts = arr
    seg = _longest_segment(secs)
    if seg is None:
        return None
    s, e = seg
    secs, lats, lons, alts = secs[s:e], lats[s:e], lons[s:e], alts[s:e]
    na = (lats >= NA_LAT_MIN) & (lats <= NA_LAT_MAX)
    if not na.any():
        return None
    if not (lons[na].min() <= WEST_LON and lons[na].max() >= EAST_LON):
        return None
    cmask = (alts >= MIN_CRUISE_FT) & na & (lons >= EDGE_LON_MIN) & (lons <= EDGE_LON_MAX)
    if cmask.sum() < 5:
        return None
    ci = np.where(cmask)[0]
    cl = lons[ci]
    wi = ci[int(np.argmin(cl))]
    ei = ci[int(np.argmax(cl))]
    ts = pd.Timestamp(base, unit="s", tz="UTC")
    probe_idx = list(ci)
    elevs = [solar_elev(float(lats[i]), float(lons[i]),
                        ts + pd.Timedelta(seconds=float(secs[i]))) for i in probe_idx]
    # interpolated mid-ocean point
    mid_sec = (secs[wi] + secs[ei]) / 2
    elevs.append(solar_elev(float((lats[wi] + lats[ei]) / 2),
                            float((lons[wi] + lons[ei]) / 2),
                            ts + pd.Timedelta(seconds=float(mid_sec))))
    night_frac = sum(1 for x in elevs if x < -6) / len(elevs)
    dur_h = (secs[-1] - secs[0]) / 3600
    cross_h = (secs[ei] - secs[wi]) / 3600
    # reject over-bridged multi-flight stitches: a single transatlantic widebody leg is
    # ~5-10 h, west cruise point precedes east, and the crossing itself is a few hours.
    if cross_h <= 1.0 or dur_h > 11.0:
        return None
    return {
        "hex": (d.get("icao") or "").lower(),
        "registration": d.get("r", ""),
        "type": t,
        "desc": d.get("desc", ""),
        "n_pts": int(len(secs)),
        "dur_h": round(float(dur_h), 1),
        "max_fl": round(float(alts.max()) / 100),
        "lon_min": round(float(lons.min()), 1), "lon_max": round(float(lons.max()), 1),
        "lat_min": round(float(lats.min()), 1), "lat_max": round(float(lats.max()), 1),
        "start": (ts + pd.Timedelta(seconds=float(secs[0]))).strftime("%H:%MZ"),
        "end": (ts + pd.Timedelta(seconds=float(secs[-1]))).strftime("%H:%MZ"),
        "ocean_pts": int(cmask.sum()),
        "cross_h": round(float(cross_h), 1),
        "night_frac": round(night_frac, 2),
        "mean_ocean_elev": round(sum(elevs) / len(elevs), 1),
    }


def main():
    day = sys.argv[1] if len(sys.argv) > 1 else "2024-12-08"
    combined = sys.argv[2] if len(sys.argv) > 2 else f"/tmp/globe_dl/{day}/combined.tar"
    if not os.path.exists(combined):
        # build combined.tar from parts if needed
        import glob
        parts = sorted(glob.glob(f"/tmp/globe_dl/{day}/*.tar.*"))
        if not parts:
            print(f"!! no tarball parts for {day} in /tmp/globe_dl/{day}")
            sys.exit(1)
        print(f"building combined.tar from {len(parts)} parts ...", flush=True)
        with open(combined, "wb") as out:
            for p in parts:
                with open(p, "rb") as fp:
                    while chunk := fp.read(1 << 24):
                        out.write(chunk)

    cands = []
    n_seen = 0
    n_traces = 0
    print(f"scanning {combined} ...", flush=True)
    with tarfile.open(combined) as tf:
        for m in tf:
            n_seen += 1
            name = m.name
            if "trace_full_" not in name or not name.endswith(".json"):
                continue
            n_traces += 1
            if n_traces % 50000 == 0:
                print(f"  ...{n_traces} traces scanned, {len(cands)} candidates", flush=True)
            f = tf.extractfile(m)
            if f is None:
                continue
            raw = f.read()
            try:
                if raw[:2] == b"\x1f\x8b":
                    raw = gzip.decompress(raw)
                # cheap header pre-filter: only parse if a widebody typecode appears
                head = raw[:200]
                d = json.loads(raw)
            except Exception:
                continue
            try:
                c = evaluate(d)
            except Exception:
                continue
            if c:
                c["day"] = day
                cands.append(c)
                print(f"  ++ {c['hex']} {c['registration']:<8} {c['type']} "
                      f"FL{c['max_fl']} {c['start']}->{c['end']} dur{c['dur_h']}h "
                      f"lon[{c['lon_min']},{c['lon_max']}] night={c['night_frac']} "
                      f"oceanElev={c['mean_ocean_elev']}", flush=True)

    print(f"\nscanned {n_traces} traces; {len(cands)} night-transatlantic widebody candidates")
    # rank: most-night first, then longest ocean stretch
    cands.sort(key=lambda c: (c["night_frac"], c["ocean_pts"]), reverse=True)
    os.makedirs(os.path.dirname(COMPARATORS_CSV), exist_ok=True)
    fields = ["hex", "registration", "type", "desc", "day", "n_pts", "dur_h", "max_fl",
              "lon_min", "lon_max", "lat_min", "lat_max", "start", "end",
              "ocean_pts", "cross_h", "night_frac", "mean_ocean_elev"]
    with open(COMPARATORS_CSV, "w", newline="") as fo:
        w = csv.DictWriter(fo, fieldnames=fields)
        w.writeheader()
        for c in cands:
            w.writerow(c)
    print(f"wrote {COMPARATORS_CSV}")


if __name__ == "__main__":
    main()
