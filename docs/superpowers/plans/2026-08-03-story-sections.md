# Story Sections Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the project's strongest scientific findings — which currently exist only as prose in `docs/VALIDATION.md` — into six rendered story sections, and stop the export from discarding the data those sections need.

**Architecture:** Two data changes land first (re-export altitude and signed per-segment EF; add a per-flight night classification computed offline from raw traces). Then six frontend sections consume them. All physics stays in the offline batch layer; the React app only reads static JSON. Charts are hand-written inline SVG, not a chart library.

**Tech Stack:** React 18 + Vite 5 + TypeScript; `motion` (via `LazyMotion` + `m`, never `framer-motion`); deck.gl + maplibre (already lazy); Python 3.12 + pandas for the batch layer. Tests: Vitest + Testing Library (frontend), pytest (batch).

## Global Constraints

- **Framing rule.** No surface shows a per-flight ~3× multiplier. Contrail-dominated flights headline absolute tonnes, never a percentage of fuel. Ruled out in `docs/IMPLEMENTATION_PLAN.md` §6.
- **Offline/online split.** Nothing under `frontend/` computes physics. Every new field arrives as static JSON produced by `scripts/` or `batch/`.
- **`prefers-reduced-motion`.** Every scroll-linked effect degrades to a static, fully readable state. Use the existing `reduced()` helper from `src/lib/scroll.ts`.
- **Accessibility.** Every chart carries a visually-hidden text equivalent. Touch targets ≥44 px. Reordering announces through an `aria-live` region.
- **Performance budget.** Critical-path JS ≤ 70 KB gzip (currently 59 KB). Measure, don't estimate.
- **Import rule.** `import { ... } from 'motion/react'`. Never `framer-motion`.
- **British English** in all user-facing copy, matching the existing site.
- **Dependencies:** add `motion` only. Do not add Tailwind, KokonutUI, bklit, anime.js or any chart library.
- **Python invocation:** `.venv/bin/python` from the repo root (this is the batch venv with pandas/pyarrow). `.venv-app` is not used by this work.
- **Node/npm:** run from `frontend/`. Node v20.

---

## File Structure

**Created:**

| Path | Responsibility |
| --- | --- |
| `src/solar.py` | Solar elevation + night classification. The single copy; four duplicates collapse into it. |
| `batch/add_night_split.py` | Offline: raw traces → `night_pct_of_waypoints` + `night_class` on the leaderboard parquet. |
| `tests/test_solar.py` | pytest for `src/solar.py`. |
| `tests/test_export.py` | pytest for the export reshaping. |
| `frontend/src/lib/track.ts` | Parse a track geojson into typed segments (index, ef, altitude, midpoint). |
| `frontend/src/lib/track.test.ts` | Vitest for the above. |
| `frontend/src/lib/data.test.ts` | Vitest for ranking/reshuffle/night-split helpers. |
| `frontend/src/lib/motion.tsx` | `LazyMotion` wrapper so `domMax` stays off the critical path. |
| `frontend/src/components/charts/SegmentBars.tsx` | Sparse per-segment EF bar chart (section 03). |
| `frontend/src/components/charts/Profile.tsx` | Altitude / EF profile with a scrubber (section 04). |
| `frontend/src/components/charts/DivergingBar.tsx` | Day/night diverging bar (section 02). |
| `frontend/src/components/OneSegment.tsx` | Section 03 shell: sticky map + scroll-driven cursor. |
| `frontend/src/components/DayOrNight.tsx` | Section 02 shell. |
| `frontend/src/components/NightWidebodies.tsx` | Section 05. |
| `frontend/src/components/HowWeKnow.tsx` | Section 06. |

**Modified:**

| Path | Change |
| --- | --- |
| `scripts/export_web_data.py:47-56` | Keep altitude + signed EF; restore the comparators export. |
| `frontend/src/lib/data.ts` | `Metric` type, `rankByMetric`, `reshuffleStats`, `nightSplit`, `loadComparators`, two new `Flight` fields. |
| `frontend/src/components/Leaderboard.tsx` | Metric switch, motion reorder, horizon toggle moves in. |
| `frontend/src/components/Explorer.tsx` | Horizon toggle becomes a shared component; `activeSegment` state; profile chart. |
| `frontend/src/components/FlightMap.tsx` | Accept + highlight an `activeSegment` prop. |
| `frontend/src/App.tsx` | Mount the four new sections; renumber eyebrows. |
| `frontend/src/styles.css` | Styles for new sections. |
| `frontend/vite.config.ts` | Vitest config; `motion` manual chunk. |
| `frontend/package.json` | `motion`, vitest devDeps, `test` script. |
| `requirements-batch.in` / `.txt` | `pytest`. |

---

## Task 1: Test harness

Nothing in this repo has tests. Every later task is written TDD-first, so the runners must exist before anything else. This task is complete when both runners execute a trivial passing test.

**Files:**
- Modify: `frontend/package.json`
- Modify: `frontend/vite.config.ts`
- Modify: `requirements-batch.in`
- Create: `frontend/src/lib/smoke.test.ts`
- Create: `tests/test_smoke.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `npm test` (frontend, from `frontend/`), `.venv/bin/python -m pytest` (batch, from repo root).

- [ ] **Step 1: Install the frontend test dependencies**

```bash
cd frontend
npm i -D vitest@^2.1.0 jsdom@^25.0.0 @testing-library/react@^16.0.1 @testing-library/jest-dom@^6.5.0
```

- [ ] **Step 2: Add the `test` script**

In `frontend/package.json`, add to `"scripts"`:

```json
"test": "vitest run",
"test:watch": "vitest"
```

- [ ] **Step 3: Configure Vitest**

Replace `frontend/vite.config.ts` with:

```ts
/// <reference types="vitest" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// base './' so the built SPA works behind nginx at the domain root.
export default defineConfig({
  base: './',
  plugins: [react()],
  server: { host: true, port: 5173 },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test-setup.ts'],
  },
  build: {
    chunkSizeWarningLimit: 1200,
    rollupOptions: {
      output: {
        // keep the heavy map stack out of the entry chunk (it's lazy-loaded with FlightMap)
        manualChunks: {
          maplibre: ['maplibre-gl'],
          deck: ['@deck.gl/core', '@deck.gl/layers', '@deck.gl/geo-layers', '@deck.gl/mapbox'],
        },
      },
    },
  },
})
```

- [ ] **Step 4: Create the test setup file**

Create `frontend/src/test-setup.ts`:

```ts
import '@testing-library/jest-dom/vitest'

// jsdom has no matchMedia; reduced() in lib/scroll.ts calls it.
if (!window.matchMedia) {
  window.matchMedia = ((q: string) => ({
    matches: false,
    media: q,
    onchange: null,
    addListener() {},
    removeListener() {},
    addEventListener() {},
    removeEventListener() {},
    dispatchEvent() {
      return false
    },
  })) as any
}
```

- [ ] **Step 5: Write the frontend smoke test**

Create `frontend/src/lib/smoke.test.ts`:

```ts
import { describe, expect, it } from 'vitest'
import { tonnes } from './data'

describe('test harness', () => {
  it('runs and can import the data layer', () => {
    expect(tonnes(1234)).toBe('1.2')
  })
})
```

- [ ] **Step 6: Run the frontend tests**

Run: `cd frontend && npm test`
Expected: PASS, 1 test.

- [ ] **Step 7: Install pytest**

Add `pytest` on its own line to `requirements-batch.in`, then:

```bash
.venv/bin/pip install pytest
.venv/bin/python -m pip freeze | grep -i "^pytest\|^iniconfig\|^pluggy" >> requirements-batch.txt
```

- [ ] **Step 8: Write the batch smoke test**

Create `tests/test_smoke.py`:

```python
"""Smoke test: the batch venv can import what the offline scripts need."""


def test_batch_deps_import():
    import numpy
    import pandas

    assert pandas.__version__
    assert numpy.__version__
```

- [ ] **Step 9: Run the batch tests**

Run: `.venv/bin/python -m pytest tests/ -v`
Expected: PASS, 1 test.

- [ ] **Step 10: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/vite.config.ts \
        frontend/src/test-setup.ts frontend/src/lib/smoke.test.ts \
        requirements-batch.in requirements-batch.txt tests/test_smoke.py
git commit -m "test: add Vitest (frontend) and pytest (batch) harnesses"
```

---

## Task 2: Shared solar elevation module

`solar_elev()` is currently copy-pasted into four files (`batch/build_comparators.py:52`, `batch/scan_comparators.py:45`, `batch/harvest_more.py:46`, `batch/harvest_drake.py:53`). Collapse it to one and add the night classification the frontend needs.

**Files:**
- Create: `src/solar.py`
- Create: `tests/test_solar.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `solar_elev(lat: float, lon: float, when: pandas.Timestamp) -> float` — degrees above horizon.
  - `NIGHT_ELEV: float = -6.0`
  - `night_pct(points: list[tuple[float, float, pandas.Timestamp]]) -> float` — percentage of points below `NIGHT_ELEV`, 0–100.
  - `classify(pct: float) -> str` — `'night'` if pct ≥ 70, `'day'` if pct ≤ 30, else `'mixed'`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_solar.py`:

```python
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
```

- [ ] **Step 2: Run it to confirm it fails**

Run: `.venv/bin/python -m pytest tests/test_solar.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.solar'`

- [ ] **Step 3: Write the implementation**

Create `src/solar.py`:

```python
"""Solar elevation and day/night classification.

The single copy. `batch/build_comparators.py`, `batch/scan_comparators.py`,
`batch/harvest_more.py` and `batch/harvest_drake.py` each carried an identical
private copy of `solar_elev`; they should import from here instead.

NOAA low-precision solar position algorithm — good to ~0.1 deg, far tighter than
the 6-degree civil-twilight threshold we test against.
"""
import math

# Sun more than 6 degrees below the horizon = night (civil twilight ended).
# Contrail radiative forcing flips sign around here: no shortwave to reflect.
NIGHT_ELEV = -6.0

# A flight is 'night' if at least this share of its cruise waypoints are dark,
# 'day' if at most (100 - this) ... see classify().
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
```

- [ ] **Step 4: Run the tests**

Run: `.venv/bin/python -m pytest tests/test_solar.py -v`
Expected: PASS, 8 tests (the parametrised one counts as 6).

If `src` is not importable, add an empty `tests/__init__.py` and run pytest from the repo root; `src/` already has module files so it resolves as a namespace package.

- [ ] **Step 5: Point the four duplicates at the shared module**

In each of `batch/build_comparators.py`, `batch/scan_comparators.py`, `batch/harvest_more.py`, `batch/harvest_drake.py`: delete the local `def solar_elev(...)` block and add near the other imports:

```python
from src.solar import solar_elev
```

In `batch/harvest_more.py` and `batch/harvest_drake.py` also delete the local `NIGHT_ELEV = -6.0` constant and import it:

```python
from src.solar import NIGHT_ELEV, solar_elev
```

- [ ] **Step 6: Verify the batch scripts still parse**

Run: `.venv/bin/python -m py_compile batch/build_comparators.py batch/scan_comparators.py batch/harvest_more.py batch/harvest_drake.py`
Expected: no output, exit 0.

- [ ] **Step 7: Commit**

```bash
git add src/solar.py tests/test_solar.py batch/build_comparators.py \
        batch/scan_comparators.py batch/harvest_more.py batch/harvest_drake.py
git commit -m "refactor: single solar_elev in src/solar.py, add night classification"
```

---

## Task 3: Per-flight night split

Adds the two fields section 02 needs to `data/processed/leaderboard.parquet`. Pure reshaping — reads raw traces, no network, no ERA5, no pycontrails.

**Files:**
- Create: `batch/add_night_split.py`
- Modify: `data/processed/leaderboard.parquet` (as script output, committed)

**Interfaces:**
- Consumes: `src.solar.classify`, `src.solar.night_pct`.
- Produces: two new columns on the leaderboard parquet — `night_pct_of_waypoints: float | None` and `night_class: str | None` (`'night' | 'mixed' | 'day'`).

- [ ] **Step 1: Write the failing test**

Create `tests/test_night_split.py`:

```python
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
```

- [ ] **Step 2: Run it to confirm it fails**

Run: `.venv/bin/python -m pytest tests/test_night_split.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'batch.add_night_split'`

- [ ] **Step 3: Write the implementation**

Create `batch/add_night_split.py`:

```python
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

import pandas as pd

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
```

- [ ] **Step 4: Run the tests**

Run: `.venv/bin/python -m pytest tests/test_night_split.py -v`
Expected: PASS, 5 tests.

- [ ] **Step 5: Run the script against the real data**

Run: `.venv/bin/python batch/add_night_split.py`
Expected output: `flights: 84, unmatched traces: 0` and classes roughly `{'day': 35, 'night': 29, 'mixed': 20}`.

If `unmatched traces` is not 0, stop and investigate before continuing — section 02's counts depend on full coverage.

- [ ] **Step 6: Verify the sign-flip result the section will claim**

Run:

```bash
.venv/bin/python -c "
import pandas as pd
d = pd.read_parquet('data/processed/leaderboard.parquet')
nz = d[d.contrail_ef_joules != 0]
g = nz.groupby('night_class').agg(
    flights=('flight_id','count'),
    warmed=('contrail_ef_joules', lambda s:(s>0).sum()),
    cooled=('contrail_ef_joules', lambda s:(s<0).sum()),
    co2e_t=('contrail_co2e_central', lambda s: s.sum()/1000))
print(g.round(1).to_string())
"
```

Expected: night = 10 flights, 10 warmed, 0 cooled, +160.7 t; day = 15 flights, 4 warmed, 11 cooled, −54.4 t; mixed = 5, 4, 1, +32.2 t.

- [ ] **Step 7: Commit**

```bash
git add batch/add_night_split.py tests/test_night_split.py data/processed/leaderboard.parquet
git commit -m "data: per-flight night/mixed/day classification from raw traces"
```

---

## Task 4: Re-export altitude, signed EF and the comparators

`scripts/export_web_data.py` discards the altitude and the signed per-segment `ef` that sections 03 and 04 need, and the comparators export was removed as dead code. Restore all three.

**Files:**
- Modify: `scripts/export_web_data.py:47-62`
- Create: `tests/test_export.py`
- Modify: `frontend/public/data/**` (as script output, committed)

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces:
  - `slim_feature(feat: dict) -> dict` — one geojson feature reduced to web form.
  - Exported track features carry `properties = {"ef_share": float, "ef_tj": float}` and 3-element coordinates `[lon, lat, alt_m]`.
  - `frontend/public/data/comparators.json` exists.
  - `manifest.json` gains a `"comparators"` count.

- [ ] **Step 1: Write the failing test**

Create `tests/test_export.py`:

```python
"""Track slimming for the web export (scripts/export_web_data.py)."""
from scripts.export_web_data import slim_feature


def _feature(coords, props):
    return {"type": "Feature", "geometry": {"type": "LineString", "coordinates": coords}, "properties": props}


def test_coordinates_keep_altitude_rounded_to_10_m():
    f = slim_feature(_feature([[-115.30643516, 34.06114982, 7559.152472]], {"ef": 0.0, "ef_share": 0.0}))
    assert f["geometry"]["coordinates"] == [[-115.30644, 34.06115, 7560.0]]


def test_missing_altitude_becomes_zero_not_a_short_coordinate():
    f = slim_feature(_feature([[-115.3, 34.0]], {"ef": 0.0, "ef_share": 0.0}))
    assert f["geometry"]["coordinates"] == [[-115.3, 34.0, 0.0]]


def test_signed_ef_is_kept_in_terajoules():
    f = slim_feature(_feature([[0.0, 0.0, 0.0]], {"ef": -4.4761e13, "ef_share": -0.14}))
    assert f["properties"]["ef_tj"] == -44761.0
    assert f["properties"]["ef_share"] == -0.14


def test_absent_properties_default_to_zero():
    f = slim_feature(_feature([[0.0, 0.0, 0.0]], {}))
    assert f["properties"] == {"ef_share": 0.0, "ef_tj": 0.0}


def test_non_linestring_geometry_is_passed_through_untouched():
    f = slim_feature({"type": "Feature", "geometry": {"type": "Point", "coordinates": [1.0, 2.0]}, "properties": {}})
    assert f["geometry"]["coordinates"] == [1.0, 2.0]
```

- [ ] **Step 2: Run it to confirm it fails**

Run: `.venv/bin/python -m pytest tests/test_export.py -v`
Expected: FAIL — `ImportError: cannot import name 'slim_feature'`

- [ ] **Step 3: Extract and rewrite the slimming logic**

In `scripts/export_web_data.py`, replace the whole track-export block (currently lines 44-62, from `src_tracks = ...` through the manifest write) with:

```python
def slim_feature(feat):
    """Reduce one track feature to what the web needs.

    Coordinates keep [lon, lat, alt_m] — lon/lat to 5 dp (~1 m), altitude to the
    nearest 10 m. Properties keep `ef_share` (the map's colour ramp) and `ef_tj`,
    the SIGNED energy forcing in terajoules — signed because the sign is the
    warming/cooling story, terajoules because raw joules are ~1e13 and bloat JSON.
    """
    g = feat.get("geometry") or {}
    if g.get("type") == "LineString":
        g = dict(g, coordinates=[
            [round(p[0], 5), round(p[1], 5), round(p[2], -1) if len(p) > 2 else 0.0]
            for p in g["coordinates"]
        ])
    props = feat.get("properties") or {}
    return {
        "type": feat.get("type", "Feature"),
        "geometry": g,
        "properties": {
            "ef_share": round(float(props.get("ef_share") or 0.0), 5),
            "ef_tj": round(float(props.get("ef") or 0.0) / 1e12, 3),
        },
    }


def export_tracks():
    src_tracks = os.path.join(PROC, "tracks")
    n = 0
    if not os.path.isdir(src_tracks):
        return 0
    for f in os.listdir(src_tracks):
        if not f.endswith(".geojson"):
            continue
        gj = json.load(open(os.path.join(src_tracks, f)))
        gj["features"] = [slim_feature(ft) for ft in gj.get("features", [])]
        json.dump(gj, open(os.path.join(OUT, "tracks", f), "w"), separators=(",", ":"))
        n += 1
    return n


n_tracks = export_tracks()
n_cmp = export_parquet("comparators.parquet")

# A tiny manifest so the frontend knows what's available without a directory listing.
with open(os.path.join(OUT, "manifest.json"), "w") as fh:
    json.dump({"leaderboard": n_lb, "tracks": n_tracks, "comparators": n_cmp}, fh)

print(f"exported: leaderboard={n_lb} flights, comparators={n_cmp}, tracks={n_tracks} geojson -> {OUT}")
```

- [ ] **Step 4: Run the tests**

Run: `.venv/bin/python -m pytest tests/test_export.py -v`
Expected: PASS, 5 tests.

If the import fails because `scripts/` is not a package, add an empty `scripts/__init__.py`.

- [ ] **Step 5: Re-export the real data and measure the size**

```bash
.venv/bin/python scripts/export_web_data.py
du -sh frontend/public/data/tracks
ls -l frontend/public/data/comparators.json
```

Expected: `comparators=5`, `tracks=84`, tracks directory around 2.5–2.8 MB (was 1.9 MB). If it exceeds 3.5 MB, reduce altitude precision to the nearest 50 m and re-run before continuing.

- [ ] **Step 6: Confirm the map still renders with the new geometry**

The map reads `f.geometry.coordinates` and takes `c[0]`, `c[1]` per point (`FlightMap.tsx:67-71`), so a third element is ignored. Verify rather than assume:

```bash
cd frontend && npm run build && npm run preview -- --port 5188
```

Open `http://localhost:5188`, scroll to the map, confirm the contrail still draws. Stop the server.

- [ ] **Step 7: Commit**

```bash
git add scripts/export_web_data.py tests/test_export.py frontend/public/data
git commit -m "data: keep altitude + signed per-segment EF in the web export; restore comparators"
```

---

## Task 5: Ranking metric helpers

The reshuffle is the leaderboard's whole argument, so its numbers get asserted, not eyeballed.

**Files:**
- Modify: `frontend/src/lib/data.ts`
- Create: `frontend/src/lib/data.test.ts`

**Interfaces:**
- Consumes: existing `OwnerAgg`, `Flight`, `Horizon`, `aggregateOwners`.
- Produces:
  - `export type Metric = 'fuel' | 'combined' | 'contrail'`
  - `export const METRIC_LABEL: Record<Metric, string>`
  - `export function metricT(o: OwnerAgg, m: Metric): number`
  - `export function rankByMetric(owners: OwnerAgg[], m: Metric): OwnerAgg[]`
  - `export interface ReshuffleStats { moved: number; total: number; biggest: { owner: string; from: number; to: number } | null }`
  - `export function reshuffleStats(owners: OwnerAgg[], from: Metric, to: Metric): ReshuffleStats`
  - Two new optional fields on `Flight`: `night_pct_of_waypoints`, `night_class`.

- [ ] **Step 1: Write the failing test**

Create `frontend/src/lib/data.test.ts`:

```ts
import { describe, expect, it } from 'vitest'
import { Metric, OwnerAgg, metricT, rankByMetric, reshuffleStats } from './data'

// Minimal owners modelled on the real board: A burns most fuel, B has huge
// contrails, C net-cools. Ranking by fuel and by combined must differ.
const owner = (o: Partial<OwnerAgg> & { owner: string }): OwnerAgg => ({
  ac_type: 'Boeing 757-200',
  flights: 7,
  fuelT: 0,
  contrailT: 0,
  combinedT: 0,
  warm: 0,
  cool: 0,
  zero: 0,
  bizjet: false,
  proxy: false,
  tier: 'med',
  ...o,
})

const OWNERS: OwnerAgg[] = [
  owner({ owner: 'A', fuelT: 300, contrailT: 5, combinedT: 305 }),
  owner({ owner: 'B', fuelT: 100, contrailT: 150, combinedT: 250 }),
  owner({ owner: 'C', fuelT: 280, contrailT: -60, combinedT: 220 }),
]

describe('metricT', () => {
  it('reads the right field per metric', () => {
    expect(metricT(OWNERS[1], 'fuel')).toBe(100)
    expect(metricT(OWNERS[1], 'combined')).toBe(250)
    expect(metricT(OWNERS[1], 'contrail')).toBe(150)
  })
})

describe('rankByMetric', () => {
  it('orders by fuel', () => {
    expect(rankByMetric(OWNERS, 'fuel').map((o) => o.owner)).toEqual(['A', 'C', 'B'])
  })

  it('orders by combined — a different order', () => {
    expect(rankByMetric(OWNERS, 'combined').map((o) => o.owner)).toEqual(['A', 'B', 'C'])
  })

  it('orders contrails signed, so net-cooling sinks to the bottom', () => {
    expect(rankByMetric(OWNERS, 'contrail').map((o) => o.owner)).toEqual(['B', 'A', 'C'])
  })

  it('does not mutate the input array', () => {
    const before = OWNERS.map((o) => o.owner)
    rankByMetric(OWNERS, 'contrail')
    expect(OWNERS.map((o) => o.owner)).toEqual(before)
  })

  it('keeps tier pinned to the owner, not to the row position', () => {
    const ranked = rankByMetric(OWNERS, 'contrail')
    expect(ranked.find((o) => o.owner === 'B')!.tier).toBe(OWNERS[1].tier)
  })
})

describe('reshuffleStats', () => {
  it('counts how many owners change position', () => {
    const s = reshuffleStats(OWNERS, 'fuel', 'combined')
    expect(s.total).toBe(3)
    expect(s.moved).toBe(2) // B 3rd->2nd, C 2nd->3rd; A stays 1st
  })

  it('names the biggest mover with 1-based positions', () => {
    const s = reshuffleStats(OWNERS, 'fuel', 'combined')
    expect(s.biggest).toEqual({ owner: 'B', from: 3, to: 2 })
  })

  it('reports nothing moved when the metrics agree', () => {
    const s = reshuffleStats(OWNERS, 'combined', 'combined')
    expect(s.moved).toBe(0)
    expect(s.biggest).toBeNull()
  })

  it('handles a single owner', () => {
    const s = reshuffleStats([OWNERS[0]], 'fuel', 'combined')
    expect(s).toEqual({ moved: 0, total: 1, biggest: null })
  })
})
```

- [ ] **Step 2: Run it to confirm it fails**

Run: `cd frontend && npm test -- data.test`
Expected: FAIL — `metricT` / `rankByMetric` / `reshuffleStats` are not exported.

- [ ] **Step 3: Write the implementation**

In `frontend/src/lib/data.ts`, add these two fields to the `Flight` interface (after `tier: string`):

```ts
  night_pct_of_waypoints: number | null
  night_class: 'night' | 'mixed' | 'day' | null
```

Then append to the file:

```ts
// ---- ranking metrics ----------------------------------------------------
// Switching the metric reshuffles the board, and that reshuffle IS the thesis:
// fuel CO2 alone tells a different story from fuel + contrails.
export type Metric = 'fuel' | 'combined' | 'contrail'

export const METRIC_LABEL: Record<Metric, string> = {
  fuel: 'Fuel CO₂',
  combined: 'Combined CO₂e',
  contrail: 'Contrails only',
}

export function metricT(o: OwnerAgg, m: Metric): number {
  return m === 'fuel' ? o.fuelT : m === 'contrail' ? o.contrailT : o.combinedT
}

// Signed sort: a net-cooling owner belongs at the bottom of "contrails only",
// not at the top by magnitude. Tier travels with the owner and is NOT
// recomputed from the new position — tier colour means "share of combined
// warming", and that meaning must not change when you look at a sub-metric.
export function rankByMetric(owners: OwnerAgg[], m: Metric): OwnerAgg[] {
  return [...owners].sort((a, b) => metricT(b, m) - metricT(a, m))
}

export interface ReshuffleStats {
  moved: number
  total: number
  biggest: { owner: string; from: number; to: number } | null
}

// How many owners change position between two metrics, and who moves furthest.
// Positions are 1-based because the caption says them out loud.
export function reshuffleStats(owners: OwnerAgg[], from: Metric, to: Metric): ReshuffleStats {
  const posIn = (m: Metric) => new Map(rankByMetric(owners, m).map((o, i) => [o.owner, i + 1]))
  const a = posIn(from)
  const b = posIn(to)
  let moved = 0
  let biggest: ReshuffleStats['biggest'] = null
  let bestDelta = 0
  for (const o of owners) {
    const pa = a.get(o.owner)!
    const pb = b.get(o.owner)!
    const d = Math.abs(pa - pb)
    if (d === 0) continue
    moved++
    if (d > bestDelta) {
      bestDelta = d
      biggest = { owner: o.owner, from: pa, to: pb }
    }
  }
  return { moved, total: owners.length, biggest }
}
```

- [ ] **Step 4: Run the tests**

Run: `cd frontend && npm test -- data.test`
Expected: PASS, 10 tests.

- [ ] **Step 5: Assert it against the real dataset**

Create `frontend/src/lib/data.real.test.ts`:

```ts
// Guards the caption in section 01 against the actual committed board: if a data
// refresh changes the reshuffle, this fails instead of the page lying.
import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'
import { Flight, aggregateOwners, reshuffleStats } from './data'

const flights: Flight[] = JSON.parse(readFileSync('public/data/leaderboard.json', 'utf8'))

describe('the real board', () => {
  it('has 84 flights across 11 owners', () => {
    expect(flights).toHaveLength(84)
    expect(new Set(flights.map((f) => f.owner_label)).size).toBe(11)
  })

  it('reshuffles 5 of 11 at GWP100 when fuel becomes combined', () => {
    const s = reshuffleStats(aggregateOwners(flights, 'GWP100'), 'fuel', 'combined')
    expect(s).toMatchObject({ moved: 5, total: 11 })
    expect(s.biggest).toEqual({ owner: 'Eric Schmidt', from: 7, to: 4 })
  })

  it('reshuffles 6 of 11 at GWP20', () => {
    const s = reshuffleStats(aggregateOwners(flights, 'GWP20'), 'fuel', 'combined')
    expect(s).toMatchObject({ moved: 6, total: 11 })
    expect(s.biggest).toEqual({ owner: 'Eric Schmidt', from: 7, to: 3 })
  })

  it('carries the night classification exported in task 3', () => {
    expect(flights.every((f) => f.night_class !== undefined)).toBe(true)
    const classes = new Set(flights.map((f) => f.night_class))
    expect(classes).toContain('night')
    expect(classes).toContain('day')
  })
})
```

- [ ] **Step 6: Run it**

Run: `cd frontend && npm test -- data.real`
Expected: PASS, 4 tests.

If the night-class assertion fails, Task 3's script ran but the export in Task 4 did not pick it up — re-run `.venv/bin/python scripts/export_web_data.py`.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/lib/data.ts frontend/src/lib/data.test.ts frontend/src/lib/data.real.test.ts
git commit -m "feat: ranking metric helpers + reshuffle stats, asserted against the real board"
```

---

## Task 6: Leaderboard — metric switch and animated reorder

**Files:**
- Create: `frontend/src/lib/motion.tsx`
- Create: `frontend/src/components/HorizonToggle.tsx`
- Modify: `frontend/src/components/Leaderboard.tsx`
- Modify: `frontend/src/components/Explorer.tsx:91-103`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/styles.css`
- Modify: `frontend/vite.config.ts`
- Create: `frontend/src/components/Leaderboard.test.tsx`

**Interfaces:**
- Consumes: `Metric`, `METRIC_LABEL`, `rankByMetric`, `reshuffleStats`, `metricT` (Task 5).
- Produces:
  - `<Motion>{children}</Motion>` from `lib/motion.tsx` — a `LazyMotion` wrapper.
  - `<HorizonToggle horizon={h} onHorizon={fn} note={string} />`.
  - `<Leaderboard owners={OwnerAgg[]} total={number} horizon={Horizon} onHorizon={(h)=>void} />` — note the two new props.

- [ ] **Step 1: Install motion**

```bash
cd frontend && npm i motion@^11.11.0
```

- [ ] **Step 2: Write the failing test**

Create `frontend/src/components/Leaderboard.test.tsx`:

```tsx
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { OwnerAgg } from '../lib/data'
import Leaderboard from './Leaderboard'

const owner = (o: Partial<OwnerAgg> & { owner: string }): OwnerAgg => ({
  ac_type: 'Boeing 757-200',
  flights: 7,
  fuelT: 0,
  contrailT: 0,
  combinedT: 0,
  warm: 0,
  cool: 0,
  zero: 0,
  bizjet: false,
  proxy: false,
  tier: 'med',
  ...o,
})

const OWNERS: OwnerAgg[] = [
  owner({ owner: 'Alpha', fuelT: 300, contrailT: 5, combinedT: 305 }),
  owner({ owner: 'Bravo', fuelT: 100, contrailT: 150, combinedT: 250 }),
  owner({ owner: 'Charlie', fuelT: 280, contrailT: -60, combinedT: 220 }),
]

const names = () => screen.getAllByTestId('lb-name').map((el) => el.textContent)

const setup = () =>
  render(<Leaderboard owners={OWNERS} total={84} horizon="GWP100" onHorizon={vi.fn()} />)

describe('Leaderboard', () => {
  it('opens ranked by combined CO₂e', () => {
    setup()
    expect(names()).toEqual(['Alpha', 'Bravo', 'Charlie'])
  })

  it('reorders when the metric switches to fuel', async () => {
    setup()
    await userEvent.click(screen.getByRole('button', { name: /Fuel CO₂/ }))
    expect(names()).toEqual(['Alpha', 'Charlie', 'Bravo'])
  })

  it('marks the active metric with aria-pressed', async () => {
    setup()
    const fuel = screen.getByRole('button', { name: /Fuel CO₂/ })
    expect(fuel).toHaveAttribute('aria-pressed', 'false')
    await userEvent.click(fuel)
    expect(fuel).toHaveAttribute('aria-pressed', 'true')
  })

  it('states how many owners moved', async () => {
    setup()
    await userEvent.click(screen.getByRole('button', { name: /Fuel CO₂/ }))
    expect(screen.getByTestId('reshuffle-note')).toHaveTextContent(/2 of 3/)
    expect(screen.getByTestId('reshuffle-note')).toHaveTextContent(/Bravo/)
  })

  it('announces the new order to screen readers', async () => {
    setup()
    await userEvent.click(screen.getByRole('button', { name: /Fuel CO₂/ }))
    const live = screen.getByTestId('lb-live')
    expect(live).toHaveAttribute('aria-live', 'polite')
    expect(live).toHaveTextContent(/Alpha/)
  })

  it('renders the horizon toggle in this section', () => {
    setup()
    expect(within(screen.getByRole('group', { name: /Time horizon/ })).getByText('GWP20')).toBeInTheDocument()
  })
})
```

- [ ] **Step 3: Install the testing-library user-event package**

```bash
cd frontend && npm i -D @testing-library/user-event@^14.5.2
```

- [ ] **Step 4: Run the test to confirm it fails**

Run: `cd frontend && npm test -- Leaderboard`
Expected: FAIL — `Leaderboard` does not accept `horizon`, and there is no metric switch.

- [ ] **Step 5: Create the LazyMotion wrapper**

Create `frontend/src/lib/motion.tsx`:

```tsx
// Motion, kept off the critical path.
//
// `motion.div` pulls the whole feature set into the entry chunk (~34 KB gzip),
// which would blow the 70 KB budget. `LazyMotion` + `m` ships a ~5 KB stub and
// fetches the rest as its own chunk after first paint. domMax (not domAnimation)
// because the leaderboard reorder needs layout animations.
import { LazyMotion } from 'motion/react'

const loadFeatures = () => import('motion/react').then((mod) => mod.domMax)

export { m } from 'motion/react'

export default function Motion({ children }: { children: React.ReactNode }) {
  return (
    <LazyMotion features={loadFeatures} strict>
      {children}
    </LazyMotion>
  )
}
```

- [ ] **Step 6: Extract the horizon toggle**

Create `frontend/src/components/HorizonToggle.tsx`:

```tsx
import { Horizon } from '../lib/data'

// Lifted out of Explorer so the ranking section can carry the same control:
// the reshuffle caption changes with the horizon (5 of 11 at GWP100, 6 at
// GWP20), so the reader needs the control where they read the claim.
export default function HorizonToggle({
  horizon,
  onHorizon,
  note,
}: {
  horizon: Horizon
  onHorizon: (h: Horizon) => void
  note?: string
}) {
  return (
    <div className="hzrow">
      <div className="hztoggle" role="group" aria-label="Time horizon">
        {(['GWP100', 'GWP20'] as Horizon[]).map((h) => (
          <button
            key={h}
            className={h === horizon ? 'on' : ''}
            aria-pressed={h === horizon}
            onClick={() => onHorizon(h)}
          >
            {h}
          </button>
        ))}
      </div>
      {note && <p className="hz-note">{note}</p>}
    </div>
  )
}
```

- [ ] **Step 7: Rewrite the Leaderboard**

Replace `frontend/src/components/Leaderboard.tsx` with:

```tsx
import { useState } from 'react'
import {
  Horizon,
  METRIC_LABEL,
  Metric,
  OwnerAgg,
  metricT,
  rankByMetric,
  reshuffleStats,
  tonnes,
} from '../lib/data'
import { reduced } from '../lib/scroll'
import Motion, { m } from '../lib/motion'
import HorizonToggle from './HorizonToggle'
import Appear from './Appear'

const METRICS: Metric[] = ['fuel', 'combined', 'contrail']

const stripeColor = (t: OwnerAgg['tier']) =>
  t === 'high' ? 'var(--warm-deep)' : t === 'med' ? 'var(--fuel)' : 'var(--cool)'

function Chips({ o }: { o: OwnerAgg }) {
  return (
    <div className="chips">
      <span className={`tier ${o.tier}`}>{o.tier === 'high' ? 'High' : o.tier === 'med' ? 'Med' : 'Low'}</span>
      {o.proxy && <span className="chip">⚠ proxy type</span>}
      {o.bizjet && <span className="chip">⚠ above cap · under-counted</span>}
    </div>
  )
}

// Signed magnitude bar. Cooling owners get a blue bar growing the other way, so
// "contrails only" never renders a negative as a stubby positive.
function Mag({ value, max, cool }: { value: number; max: number; cool: boolean }) {
  const pct = max > 0 ? Math.max(2, (Math.abs(value) / max) * 100) : 2
  return (
    <div className="mag">
      <i
        style={{
          width: `${pct}%`,
          background: cool
            ? 'linear-gradient(90deg,var(--cool),#2f6aa8)'
            : 'linear-gradient(90deg,var(--fuel),var(--warm) 78%,var(--warm-deep))',
        }}
      />
    </div>
  )
}

function Row({ o, rank, metric, max }: { o: OwnerAgg; rank: number; metric: Metric; max: number }) {
  const v = metricT(o, metric)
  const hero = rank === 1
  const unit = metric === 'contrail' ? 't CO₂e contrails' : hero ? 't CO₂e' : 't'
  const sign = metric === 'contrail' && v > 0 ? '+' : metric === 'contrail' && v < 0 ? '−' : ''
  return (
    <m.div
      layout={!reduced()}
      transition={{ type: 'spring', stiffness: 260, damping: 30 }}
      className={`lb-card ${hero ? 'lb-hero' : 'lb-row'}`}
    >
      <span className="stripe" style={{ background: stripeColor(o.tier) }} />
      <div className="lb-top">
        <div>
          <div className="lb-rank">Rank {String(rank).padStart(2, '0')}</div>
          <div className="lb-name" data-testid="lb-name">
            {o.owner}
          </div>
          <div className="lb-ac">
            {o.ac_type} · {o.flights} flights
            {hero && ` · ${o.warm} warmed · ${o.cool} cooled · ${o.zero} ~none`}
          </div>
        </div>
        <div className="lb-val" style={{ textAlign: 'right' }}>
          <div className="t">
            {sign}
            {tonnes(Math.abs(v) * 1000)} <span className="u">{unit}</span>
          </div>
        </div>
      </div>
      <Mag value={v} max={max} cool={v < 0} />
      <Chips o={o} />
    </m.div>
  )
}

export default function Leaderboard({
  owners,
  total,
  horizon,
  onHorizon,
}: {
  owners: OwnerAgg[]
  total: number
  horizon: Horizon
  onHorizon: (h: Horizon) => void
}) {
  const [metric, setMetric] = useState<Metric>('combined')
  if (!owners.length) return null

  const ranked = rankByMetric(owners, metric)
  const max = Math.max(...ranked.map((o) => Math.abs(metricT(o, metric))))
  const shuffle = reshuffleStats(owners, 'fuel', 'combined')

  return (
    <section className="lb wrap" id="leaderboard">
      <Appear>
        <div className="eyebrow">01 — The ranking</div>
        <h2 className="sec-head" style={{ marginTop: '.6rem' }}>
          Who warmed the most
        </h2>
        <p className="sec-sub">
          {total} tracked flights across {owners.length} public-figure jets. Switch the metric and watch the order
          change — that change is the whole point.
        </p>
        <HorizonToggle
          horizon={horizon}
          onHorizon={onHorizon}
          note="GWP20 weights short-lived contrails heavier than the 100-year basis. (A time-horizon choice, not the aviation-wide ~3× ERF.)"
        />
      </Appear>

      <div className="metricrow">
        <div className="hztoggle" role="group" aria-label="Ranking metric">
          {METRICS.map((mm) => (
            <button key={mm} className={mm === metric ? 'on' : ''} aria-pressed={mm === metric} onClick={() => setMetric(mm)}>
              {METRIC_LABEL[mm]}
            </button>
          ))}
        </div>
        <p className="hz-note" data-testid="reshuffle-note">
          {shuffle.biggest ? (
            <>
              Counting contrails moves <b>{shuffle.moved} of {shuffle.total}</b> — {shuffle.biggest.owner} goes from{' '}
              {shuffle.biggest.from}th to {shuffle.biggest.to}
              {shuffle.biggest.to === 2 ? 'nd' : shuffle.biggest.to === 3 ? 'rd' : 'th'} at {horizon}.
            </>
          ) : (
            <>At {horizon}, counting contrails leaves the order unchanged.</>
          )}
        </p>
      </div>

      <Motion>
        <div className="lb-grid">
          {ranked.map((o, i) => (
            <Row key={o.owner} o={o} rank={i + 1} metric={metric} max={max} />
          ))}
        </div>
      </Motion>

      <span className="sr-only" role="status" aria-live="polite" data-testid="lb-live">
        Ranked by {METRIC_LABEL[metric]}: {ranked.map((o, i) => `${i + 1}. ${o.owner}`).join(', ')}.
      </span>
    </section>
  )
}
```

- [ ] **Step 8: Remove the duplicated toggle from Explorer**

In `frontend/src/components/Explorer.tsx`, replace the `<div className="hzrow">…</div>` block (lines 91-103) with:

```tsx
        <HorizonToggle
          horizon={horizon}
          onHorizon={onHorizon}
          note="Watch the contrail number move — GWP20 weights short-lived contrails heavier than the 100-year basis."
        />
```

and add to its imports:

```tsx
import HorizonToggle from './HorizonToggle'
```

- [ ] **Step 9: Pass the new props from App**

In `frontend/src/App.tsx`, change the Leaderboard call to:

```tsx
            <Leaderboard owners={owners} total={flights.length} horizon={horizon} onHorizon={setHorizon} />
```

- [ ] **Step 10: Add the styles**

Append to `frontend/src/styles.css`:

```css
/* metric switch above the ranking grid */
.metricrow{ display:flex; flex-wrap:wrap; align-items:center; gap:.7rem 1.2rem; margin:1.6rem 0 .4rem; }
.metricrow .hztoggle button{ font-size:.8rem; padding:.42rem .9rem; }
.lb-grid .lb-hero{ grid-column:span 12; }
.lb-grid .lb-row{ grid-column:span 6; }
@media (max-width:720px){ .lb-grid .lb-row{ grid-column:span 12; } }
```

- [ ] **Step 11: Give motion its own chunk**

In `frontend/vite.config.ts`, add to `manualChunks`:

```ts
          motion: ['motion/react'],
```

- [ ] **Step 12: Run the tests**

Run: `cd frontend && npm test`
Expected: PASS, all suites.

- [ ] **Step 13: Typecheck and measure the bundle**

```bash
cd frontend && npm run typecheck && npm run build
ls -l dist/assets/*.js | sort -k5 -n
gzip -c dist/assets/index-*.js | wc -c
```

Expected: typecheck clean; the gzipped entry chunk ≤ 70 000 bytes. Record the number. If it exceeds the budget, confirm `motion` landed in its own chunk rather than the entry.

- [ ] **Step 14: Commit**

```bash
git add frontend/src frontend/vite.config.ts frontend/package.json frontend/package-lock.json frontend/src/styles.css
git commit -m "feat(01): metric switch with animated reorder; horizon toggle moves to the ranking"
```

---

## Task 7: Track segment parsing

Sections 03 and 04 both need a flight's track as typed segments. One parser, one cursor concept, shared.

**Files:**
- Create: `frontend/src/lib/track.ts`
- Create: `frontend/src/lib/track.test.ts`

**Interfaces:**
- Consumes: the geojson shape produced in Task 4 — `properties: { ef_share, ef_tj }`, coordinates `[lon, lat, alt_m]`.
- Produces:
  - `export interface Segment { index: number; efJ: number; efShare: number; lon: number; lat: number; altM: number }`
  - `export interface TrackData { segments: Segment[]; totalAbsEfJ: number; peakIndex: number; nonZero: number; maxAltM: number }`
  - `export function parseTrack(gj: unknown): TrackData`
  - `export const flightLevel = (altM: number): number` — altitude in metres to a flight level (hundreds of feet).

- [ ] **Step 1: Write the failing test**

Create `frontend/src/lib/track.test.ts`:

```ts
import { describe, expect, it } from 'vitest'
import { flightLevel, parseTrack } from './track'

const seg = (lon: number, lat: number, alt: number, ef_tj: number, ef_share = 0) => ({
  type: 'Feature',
  geometry: { type: 'LineString', coordinates: [[lon, lat, alt], [lon + 1, lat + 1, alt]] },
  properties: { ef_tj, ef_share },
})

const track = (...features: unknown[]) => ({ type: 'FeatureCollection', features })

describe('parseTrack', () => {
  it('converts terajoules back to joules', () => {
    const t = parseTrack(track(seg(0, 0, 11000, 44.761)))
    expect(t.segments[0].efJ).toBeCloseTo(4.4761e13, 8)
  })

  it('keeps the sign of a cooling segment', () => {
    const t = parseTrack(track(seg(0, 0, 11000, -12.5)))
    expect(t.segments[0].efJ).toBeLessThan(0)
  })

  it('uses the segment midpoint for position', () => {
    const t = parseTrack(track(seg(-10, 40, 11000, 0)))
    expect(t.segments[0].lon).toBeCloseTo(-9.5)
    expect(t.segments[0].lat).toBeCloseTo(40.5)
  })

  it('averages altitude across the segment points', () => {
    const f = {
      type: 'Feature',
      geometry: { type: 'LineString', coordinates: [[0, 0, 10000], [1, 1, 12000]] },
      properties: { ef_tj: 0, ef_share: 0 },
    }
    expect(parseTrack(track(f)).segments[0].altM).toBe(11000)
  })

  it('finds the peak by absolute forcing, so a big cooling segment wins', () => {
    const t = parseTrack(track(seg(0, 0, 11000, 5), seg(1, 1, 11000, -90), seg(2, 2, 11000, 10)))
    expect(t.peakIndex).toBe(1)
  })

  it('sums absolute forcing and counts non-zero segments', () => {
    const t = parseTrack(track(seg(0, 0, 11000, 5), seg(1, 1, 11000, -10), seg(2, 2, 11000, 0)))
    expect(t.totalAbsEfJ).toBeCloseTo(1.5e13, 8)
    expect(t.nonZero).toBe(2)
  })

  it('reports the maximum altitude reached', () => {
    const t = parseTrack(track(seg(0, 0, 8000, 0), seg(1, 1, 12215, 0)))
    expect(t.maxAltM).toBe(12215)
  })

  it('indexes segments in file order', () => {
    const t = parseTrack(track(seg(0, 0, 1, 0), seg(1, 1, 1, 0), seg(2, 2, 1, 0)))
    expect(t.segments.map((s) => s.index)).toEqual([0, 1, 2])
  })

  it('survives an empty or malformed track', () => {
    expect(parseTrack(null)).toEqual({ segments: [], totalAbsEfJ: 0, peakIndex: -1, nonZero: 0, maxAltM: 0 })
    expect(parseTrack(track({ type: 'Feature', geometry: { type: 'Point', coordinates: [0, 0] } })).segments).toHaveLength(0)
  })

  it('tolerates 2-element coordinates from an older export', () => {
    const f = {
      type: 'Feature',
      geometry: { type: 'LineString', coordinates: [[0, 0], [1, 1]] },
      properties: { ef_share: 0 },
    }
    const t = parseTrack(track(f))
    expect(t.segments[0].altM).toBe(0)
    expect(t.segments[0].efJ).toBe(0)
  })
})

describe('flightLevel', () => {
  it('converts metres to hundreds of feet', () => {
    expect(flightLevel(12215)).toBe(401)
    expect(flightLevel(0)).toBe(0)
  })
})
```

- [ ] **Step 2: Run it to confirm it fails**

Run: `cd frontend && npm test -- track`
Expected: FAIL — cannot resolve `./track`.

- [ ] **Step 3: Write the implementation**

Create `frontend/src/lib/track.ts`:

```ts
// Parse an exported track geojson into typed segments.
//
// One parser for both the "one segment" bar chart and the explorer's altitude
// profile, so a segment index means exactly the same thing in the chart, on the
// map and in the scrubber.

export interface Segment {
  index: number
  efJ: number // signed energy forcing, joules (+ warms, − cools)
  efShare: number // share of the flight's total forcing, as exported
  lon: number // segment midpoint
  lat: number
  altM: number // mean altitude across the segment, metres
}

export interface TrackData {
  segments: Segment[]
  totalAbsEfJ: number
  peakIndex: number // index of the largest |efJ|, or -1 when nothing formed
  nonZero: number
  maxAltM: number
}

const EMPTY: TrackData = { segments: [], totalAbsEfJ: 0, peakIndex: -1, nonZero: 0, maxAltM: 0 }

const num = (v: unknown) => (typeof v === 'number' && Number.isFinite(v) ? v : 0)

export function parseTrack(gj: unknown): TrackData {
  const features = (gj as any)?.features
  if (!Array.isArray(features)) return EMPTY

  const segments: Segment[] = []
  let totalAbsEfJ = 0
  let peakIndex = -1
  let peakAbs = 0
  let nonZero = 0
  let maxAltM = 0

  for (const f of features) {
    const g = f?.geometry
    const coords = g?.coordinates
    if (g?.type !== 'LineString' || !Array.isArray(coords) || coords.length < 2) continue

    const a = coords[0]
    const b = coords[coords.length - 1]
    // ef_tj is terajoules in the export; the science talks in joules.
    const efJ = num(f?.properties?.ef_tj) * 1e12
    const alts = coords.map((c: number[]) => num(c[2]))
    const altM = Math.round(alts.reduce((s: number, v: number) => s + v, 0) / alts.length)

    const index = segments.length
    segments.push({
      index,
      efJ,
      efShare: num(f?.properties?.ef_share),
      lon: (num(a[0]) + num(b[0])) / 2,
      lat: (num(a[1]) + num(b[1])) / 2,
      altM,
    })

    const abs = Math.abs(efJ)
    totalAbsEfJ += abs
    if (abs > 0) nonZero++
    if (abs > peakAbs) {
      peakAbs = abs
      peakIndex = index
    }
    maxAltM = Math.max(maxAltM, ...alts)
  }

  return { segments, totalAbsEfJ, peakIndex, nonZero, maxAltM }
}

// Flight level = altitude in hundreds of feet. FL401 ≈ 12 215 m.
export const flightLevel = (altM: number): number => Math.round((altM * 3.28084) / 100)
```

- [ ] **Step 4: Run the tests**

Run: `cd frontend && npm test -- track`
Expected: PASS, 11 tests.

- [ ] **Step 5: Assert it against a real exported track**

Append to `frontend/src/lib/data.real.test.ts`:

```ts
import { parseTrack } from './track'

describe('a real exported track', () => {
  it('shows Taylor Swift 2024-12-10 concentrating all forcing in one segment', () => {
    const gj = JSON.parse(readFileSync('public/data/tracks/a81b13_20241210.geojson', 'utf8'))
    const t = parseTrack(gj)
    expect(t.segments.length).toBe(169)
    expect(t.nonZero).toBe(1)
    expect(t.peakIndex).toBeGreaterThanOrEqual(0)
  })

  it('recovers altitude for the Trump 2025-02-14 flight (FL401)', () => {
    const gj = JSON.parse(readFileSync('public/data/tracks/aa3410_20250214.geojson', 'utf8'))
    const t = parseTrack(gj)
    expect(flightLevel(t.maxAltM)).toBeGreaterThanOrEqual(395)
    expect(flightLevel(t.maxAltM)).toBeLessThanOrEqual(405)
  })
})
```

Add `flightLevel` to that file's import from `./track`.

- [ ] **Step 6: Run it**

Run: `cd frontend && npm test -- data.real`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/lib/track.ts frontend/src/lib/track.test.ts frontend/src/lib/data.real.test.ts
git commit -m "feat: track segment parser (signed EF, altitude, midpoints)"
```

---

## Task 8: Section 03 — One segment

**Files:**
- Create: `frontend/src/components/charts/SegmentBars.tsx`
- Create: `frontend/src/components/OneSegment.tsx`
- Create: `frontend/src/components/charts/SegmentBars.test.tsx`
- Modify: `frontend/src/components/FlightMap.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/styles.css`

**Interfaces:**
- Consumes: `parseTrack`, `TrackData`, `Segment` (Task 7); `loadTrack` from `lib/data`.
- Produces:
  - `<SegmentBars segments={Segment[]} active={number} peak={number} />`
  - `<OneSegment flights={Flight[]} />`
  - `FlightMap` gains an optional prop `activeSegment?: number` — when set (≥0), the animation stops and the map holds at that segment.

- [ ] **Step 1: Write the failing test**

Create `frontend/src/components/charts/SegmentBars.test.tsx`:

```tsx
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { Segment } from '../../lib/track'
import SegmentBars from './SegmentBars'

const segs = (efs: number[]): Segment[] =>
  efs.map((efJ, index) => ({ index, efJ, efShare: 0, lon: index, lat: index, altM: 11000 }))

describe('SegmentBars', () => {
  it('draws one bar per segment', () => {
    render(<SegmentBars segments={segs([0, 0, 5e13, 0])} active={0} peak={2} />)
    expect(screen.getAllByTestId('seg-bar')).toHaveLength(4)
  })

  it('marks the peak segment', () => {
    render(<SegmentBars segments={segs([0, 5e13, 0])} active={0} peak={1} />)
    expect(screen.getByTestId('seg-bar-peak')).toBeInTheDocument()
  })

  it('marks the active segment separately from the peak', () => {
    render(<SegmentBars segments={segs([0, 5e13, 0])} active={2} peak={1} />)
    expect(screen.getByTestId('seg-bar-active')).toBeInTheDocument()
  })

  it('carries a text equivalent naming the concentration', () => {
    render(<SegmentBars segments={segs([0, 0, 5e13, 0, 0])} active={0} peak={2} />)
    expect(screen.getByTestId('seg-bars-alt')).toHaveTextContent(/1 of 5/)
  })

  it('renders nothing rather than crashing on an empty track', () => {
    const { container } = render(<SegmentBars segments={[]} active={0} peak={-1} />)
    expect(container.querySelectorAll('[data-testid="seg-bar"]')).toHaveLength(0)
  })
})
```

- [ ] **Step 2: Run it to confirm it fails**

Run: `cd frontend && npm test -- SegmentBars`
Expected: FAIL — cannot resolve `./SegmentBars`.

- [ ] **Step 3: Write the chart**

Create `frontend/src/components/charts/SegmentBars.tsx`:

```tsx
import { Segment } from '../../lib/track'

// A flight's per-segment |EF| as a sparse bar field. Almost every bar is zero;
// the point is how few carry the whole effect. Hand-written SVG so it inherits
// the palette and needs no chart library.
export default function SegmentBars({
  segments,
  active,
  peak,
}: {
  segments: Segment[]
  active: number
  peak: number
}) {
  if (!segments.length) return null

  const max = Math.max(...segments.map((s) => Math.abs(s.efJ)), 1)
  const nonZero = segments.filter((s) => s.efJ !== 0).length
  const w = 1000
  const h = 220
  const gap = 1
  const bw = Math.max(1, w / segments.length - gap)

  return (
    <div className="segbars">
      <svg viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" role="presentation" aria-hidden="true">
        <line x1="0" y1={h - 1} x2={w} y2={h - 1} stroke="var(--hair)" strokeWidth="1" />
        {segments.map((s) => {
          const bh = (Math.abs(s.efJ) / max) * (h - 16)
          const isPeak = s.index === peak
          const isActive = s.index === active && !isPeak
          const fill = s.efJ < 0 ? 'var(--cool)' : isPeak ? 'var(--warm-deep)' : 'var(--fuel)'
          return (
            <rect
              key={s.index}
              data-testid={isPeak ? 'seg-bar-peak' : isActive ? 'seg-bar-active' : 'seg-bar'}
              x={s.index * (bw + gap)}
              y={h - 1 - Math.max(bh, s.efJ === 0 ? 1 : 2)}
              width={bw}
              height={Math.max(bh, s.efJ === 0 ? 1 : 2)}
              fill={fill}
              opacity={s.efJ === 0 ? 0.28 : isPeak || isActive ? 1 : 0.75}
            />
          )
        })}
      </svg>
      <p className="sr-only" data-testid="seg-bars-alt">
        Bar chart of contrail energy forcing for each of the {segments.length} track segments. {nonZero} of{' '}
        {segments.length} segments produced any forcing at all; the rest are zero.
      </p>
    </div>
  )
}
```

- [ ] **Step 4: Run the chart tests**

Run: `cd frontend && npm test -- SegmentBars`
Expected: PASS, 5 tests.

- [ ] **Step 5: Let the map hold at a segment**

In `frontend/src/components/FlightMap.tsx`:

Change the component signature to:

```tsx
export default function FlightMap({
  flightId,
  owner,
  date,
  activeSegment,
}: {
  flightId: string
  owner?: string
  date?: string
  activeSegment?: number
}) {
```

Then replace the whole animation `useEffect` (currently lines 181-207) with:

```tsx
  useEffect(() => {
    if (!trips.length) return
    const total = nRef.current
    const overlay = overlayRef.current
    const seeds = seedsRef.current

    // Driven from outside (section 03 scrubs by scroll): hold at that segment
    // instead of running the loop, so the chart and the map show one cursor.
    if (activeSegment !== undefined && activeSegment >= 0) {
      const t = Math.min(total, activeSegment + 1)
      overlay?.setProps({ layers: [...bloomLayers(seeds, t, total), layerAt(trips, total, t), planeLayer(headAt(trips, t))] })
      return
    }

    if (reduced()) {
      // fully drawn, every warming/cooling bloom lit, plane parked at the destination
      overlay?.setProps({ layers: [...bloomLayers(seeds, total, total), layerAt(trips, total, total), planeLayer(headAt(trips, total))] })
      return
    }
    // normalise so the whole contrail draws in ~8s regardless of segment count
    const step = total / (8 * 60)
    let t = 0
    let raf = 0
    let visible = true
    const io = new IntersectionObserver((es) => { visible = es[0]?.isIntersecting ?? true }, { threshold: 0.01 })
    if (elRef.current) io.observe(elRef.current)
    const tick = () => {
      if (visible) {
        t = (t + step) % total
        overlay?.setProps({ layers: [...bloomLayers(seeds, t, total), layerAt(trips, total, t), planeLayer(headAt(trips, t))] })
      }
      raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => { cancelAnimationFrame(raf); io.disconnect() }
  }, [trips, activeSegment])
```

- [ ] **Step 6: Write the section**

Create `frontend/src/components/OneSegment.tsx`:

```tsx
import { Suspense, lazy, useEffect, useRef, useState } from 'react'
import { Flight, loadTrack } from '../lib/data'
import { TrackData, parseTrack } from '../lib/track'
import { reduced } from '../lib/scroll'
import SegmentBars from './charts/SegmentBars'
import Appear from './Appear'

const FlightMap = lazy(() => import('./FlightMap'))

// Taylor Swift, 10 Dec 2024: 1 non-zero segment of 169 — the most extreme
// concentration in the set, and large enough (+12.1 t) not to be noise.
const HERO_FLIGHT = 'a81b13_20241210'

export default function OneSegment({ flights }: { flights: Flight[] }) {
  const stageRef = useRef<HTMLDivElement>(null)
  const [track, setTrack] = useState<TrackData | null>(null)
  const [active, setActive] = useState(0)

  const flight = flights.find((f) => f.flight_id === HERO_FLIGHT)

  useEffect(() => {
    let alive = true
    loadTrack(HERO_FLIGHT).then((gj) => {
      if (alive && gj) setTrack(parseTrack(gj))
    })
    return () => { alive = false }
  }, [])

  // Scroll through the section walks one cursor along the flight. Reduced
  // motion parks it on the peak segment instead of scrubbing.
  useEffect(() => {
    if (!track?.segments.length) return
    if (reduced()) { setActive(Math.max(0, track.peakIndex)); return }
    const el = stageRef.current
    if (!el) return
    let raf = 0
    const onScroll = () => {
      cancelAnimationFrame(raf)
      raf = requestAnimationFrame(() => {
        const r = el.getBoundingClientRect()
        const span = Math.max(1, r.height - window.innerHeight)
        const p = Math.min(1, Math.max(0, -r.top / span))
        setActive(Math.round(p * (track.segments.length - 1)))
      })
    }
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => { window.removeEventListener('scroll', onScroll); cancelAnimationFrame(raf) }
  }, [track])

  if (!flight || !track) return null

  const peakT = Math.abs(flight.contrail_co2e_central) / 1000

  return (
    <section className="oneseg" id="one-segment">
      <div className="wrap">
        <Appear>
          <div className="eyebrow">02 — The concentration</div>
          <h2 className="sec-head" style={{ marginTop: '.6rem' }}>
            One segment out of {track.segments.length}
          </h2>
          <p className="sec-sub">
            Contrail warming is not spread along a flight — it is made in the few minutes an aircraft spends inside
            ice-supersaturated air. On this Falcon 7X leg, {track.nonZero} of {track.segments.length} track segments
            produced any forcing at all, and it came to {peakT.toFixed(1)} t CO₂e. Across every flight here that formed
            a contrail, the median is 8 live segments out of 156, and the top five carry 95% of the effect.
          </p>
        </Appear>
      </div>

      <div className="oneseg-stage" ref={stageRef}>
        <div className="oneseg-pin">
          <div className="oneseg-map">
            <Suspense fallback={null}>
              <FlightMap flightId={HERO_FLIGHT} owner={flight.owner_label} date={flight.date} activeSegment={active} />
            </Suspense>
          </div>
          <div className="wrap">
            <SegmentBars segments={track.segments} active={active} peak={track.peakIndex} />
            <p className="oneseg-cap">
              Segment <b>{active + 1}</b> of {track.segments.length}
              {active === track.peakIndex && <b className="oneseg-hit"> — this is the one</b>}
            </p>
          </div>
        </div>
      </div>
    </section>
  )
}
```

- [ ] **Step 7: Add the styles**

Append to `frontend/src/styles.css`:

```css
/* ============================================================ 03 · ONE SEGMENT */
.oneseg{ padding:6rem 0 0; }
.oneseg-stage{ height:260svh; position:relative; }
.oneseg-pin{ position:sticky; top:0; height:100svh; display:flex; flex-direction:column;
  justify-content:center; gap:1.2rem; overflow:hidden; }
.oneseg-map{ position:relative; height:min(52vh,460px); border-radius:20px; overflow:hidden;
  border:1px solid var(--hair); background:#06101c; margin-inline:var(--pad); }
.segbars{ margin-top:1rem; }
.segbars svg{ width:100%; height:clamp(120px,18vh,220px); display:block; }
.oneseg-cap{ color:var(--muted); font-size:.86rem; margin:.6rem 0 0; font-variant-numeric:tabular-nums; }
.oneseg-cap b{ color:var(--ink); }
.oneseg-hit{ color:var(--warm-deep) !important; }
@media (prefers-reduced-motion:reduce){
  .oneseg-stage{ height:auto; }
  .oneseg-pin{ position:relative; height:auto; padding-block:2rem; }
}
```

- [ ] **Step 8: Mount it**

In `frontend/src/App.tsx`, add the import and place it after `<Leaderboard>`:

```tsx
import OneSegment from './components/OneSegment'
```

```tsx
            <Leaderboard owners={owners} total={flights.length} horizon={horizon} onHorizon={setHorizon} />
            <OneSegment flights={flights} />
            <Explorer flights={flights} horizon={horizon} onHorizon={setHorizon} />
```

Change Explorer's eyebrow in `Explorer.tsx` from `02 — The explorer` to `04 — The explorer`.

- [ ] **Step 9: Run the tests and typecheck**

Run: `cd frontend && npm test && npm run typecheck`
Expected: PASS, clean.

- [ ] **Step 10: Look at it**

```bash
cd frontend && npm run dev -- --port 5188
```

Open `http://localhost:5188`, scroll into section 03. Confirm the cursor advances with scroll, the map's contrail draws to the cursor, and the peak bar turns crimson with the "this is the one" caption. Stop the server.

- [ ] **Step 11: Commit**

```bash
git add frontend/src
git commit -m "feat(03): one-segment section — sparse EF bars scrubbed by scroll over a sticky map"
```

---

## Task 9: Section 04 — altitude / EF profile under the explorer map

**Files:**
- Create: `frontend/src/components/charts/Profile.tsx`
- Create: `frontend/src/components/charts/Profile.test.tsx`
- Modify: `frontend/src/components/Explorer.tsx`
- Modify: `frontend/src/styles.css`

**Interfaces:**
- Consumes: `Segment`, `TrackData`, `parseTrack`, `flightLevel` (Task 7); `FlightMap`'s `activeSegment` prop (Task 8).
- Produces: `<Profile track={TrackData} active={number} onActive={(i:number)=>void} />`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/components/charts/Profile.test.tsx`:

```tsx
import { fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { TrackData } from '../../lib/track'
import Profile from './Profile'

const track = (): TrackData => ({
  segments: [
    { index: 0, efJ: 0, efShare: 0, lon: 0, lat: 0, altM: 3000 },
    { index: 1, efJ: 4e13, efShare: 0.5, lon: 1, lat: 1, altM: 12215 },
    { index: 2, efJ: 0, efShare: 0, lon: 2, lat: 2, altM: 9000 },
  ],
  totalAbsEfJ: 4e13,
  peakIndex: 1,
  nonZero: 1,
  maxAltM: 12215,
})

describe('Profile', () => {
  it('opens on the altitude tab and reports the peak flight level', () => {
    render(<Profile track={track()} active={1} onActive={vi.fn()} />)
    expect(screen.getByRole('button', { name: /Altitude/ })).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByTestId('profile-alt')).toHaveTextContent(/FL401/)
  })

  it('switches to the contrail EF tab', async () => {
    render(<Profile track={track()} active={1} onActive={vi.fn()} />)
    await userEvent.click(screen.getByRole('button', { name: /Contrail EF/ }))
    expect(screen.getByRole('button', { name: /Contrail EF/ })).toHaveAttribute('aria-pressed', 'true')
  })

  it('exposes a slider bound to the active segment', () => {
    render(<Profile track={track()} active={1} onActive={vi.fn()} />)
    const slider = screen.getByRole('slider')
    expect(slider).toHaveValue('1')
    expect(slider).toHaveAttribute('aria-valuemax', '2')
  })

  it('calls onActive when the slider moves', () => {
    const onActive = vi.fn()
    render(<Profile track={track()} active={0} onActive={onActive} />)
    fireEvent.change(screen.getByRole('slider'), { target: { value: '2' } })
    expect(onActive).toHaveBeenCalledWith(2)
  })

  it('carries a text equivalent', () => {
    render(<Profile track={track()} active={1} onActive={vi.fn()} />)
    expect(screen.getByTestId('profile-alt')).toHaveTextContent(/3 segments/)
  })

  it('renders nothing for an empty track', () => {
    const empty: TrackData = { segments: [], totalAbsEfJ: 0, peakIndex: -1, nonZero: 0, maxAltM: 0 }
    const { container } = render(<Profile track={empty} active={0} onActive={vi.fn()} />)
    expect(container).toBeEmptyDOMElement()
  })
})
```

- [ ] **Step 2: Run it to confirm it fails**

Run: `cd frontend && npm test -- Profile`
Expected: FAIL — cannot resolve `./Profile`.

- [ ] **Step 3: Write the chart**

Create `frontend/src/components/charts/Profile.tsx`:

```tsx
import { useState } from 'react'
import { TrackData, flightLevel } from '../../lib/track'

type Tab = 'alt' | 'ef'

// Altitude and contrail-forcing profiles for one flight, sharing the map's
// cursor. The range input is the accessible control; the SVG is decoration.
export default function Profile({
  track,
  active,
  onActive,
}: {
  track: TrackData
  active: number
  onActive: (i: number) => void
}) {
  const [tab, setTab] = useState<Tab>('alt')
  const segs = track.segments
  if (!segs.length) return null

  const w = 1000
  const h = 150
  const last = segs.length - 1
  const maxAlt = Math.max(track.maxAltM, 1)
  const maxEf = Math.max(...segs.map((s) => Math.abs(s.efJ)), 1)

  const x = (i: number) => (i / Math.max(1, last)) * w
  const y = (s: { altM: number; efJ: number }) =>
    tab === 'alt' ? h - (s.altM / maxAlt) * (h - 8) : h - (Math.abs(s.efJ) / maxEf) * (h - 8)

  const d = segs.map((s, i) => `${i === 0 ? 'M' : 'L'}${x(i).toFixed(1)},${y(s).toFixed(1)}`).join(' ')
  const cur = segs[Math.min(last, Math.max(0, active))]

  return (
    <div className="profile">
      <div className="profile-head">
        <div className="hztoggle" role="group" aria-label="Profile metric">
          <button className={tab === 'alt' ? 'on' : ''} aria-pressed={tab === 'alt'} onClick={() => setTab('alt')}>
            Altitude
          </button>
          <button className={tab === 'ef' ? 'on' : ''} aria-pressed={tab === 'ef'} onClick={() => setTab('ef')}>
            Contrail EF
          </button>
        </div>
        <div className="profile-read" data-testid="profile-alt">
          FL{flightLevel(cur.altM)} · segment {cur.index + 1} of {segs.length} · {segs.length} segments tracked
        </div>
      </div>

      <svg viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" role="presentation" aria-hidden="true">
        <path d={d} fill="none" stroke={tab === 'alt' ? 'var(--cool)' : 'var(--warm)'} strokeWidth="2.5" vectorEffect="non-scaling-stroke" />
        <line x1={x(cur.index)} y1="0" x2={x(cur.index)} y2={h} stroke="var(--ink-2)" strokeWidth="1" vectorEffect="non-scaling-stroke" opacity=".7" />
        <circle cx={x(cur.index)} cy={y(cur)} r="4" fill="var(--ink)" />
      </svg>

      <label className="sr-only" htmlFor="profile-scrub">
        Scrub along the flight path
      </label>
      <input
        id="profile-scrub"
        className="profile-scrub"
        type="range"
        min={0}
        max={last}
        step={1}
        value={Math.min(last, Math.max(0, active))}
        aria-valuemin={0}
        aria-valuemax={last}
        aria-valuenow={cur.index}
        aria-valuetext={`Segment ${cur.index + 1} of ${segs.length}, flight level ${flightLevel(cur.altM)}`}
        onChange={(e) => onActive(Number(e.target.value))}
      />
    </div>
  )
}
```

- [ ] **Step 4: Run the chart tests**

Run: `cd frontend && npm test -- Profile`
Expected: PASS, 6 tests.

- [ ] **Step 5: Wire it into the Explorer**

In `frontend/src/components/Explorer.tsx`:

Add to the imports:

```tsx
import { useEffect } from 'react'
import { loadTrack } from '../lib/data'
import { TrackData, parseTrack } from '../lib/track'
import Profile from './charts/Profile'
```

(merge `useEffect` into the existing `react` import, and `loadTrack` into the existing `../lib/data` import.)

Add state next to the existing `const [fid, setFid] = useState<...>`:

```tsx
  const [track, setTrack] = useState<TrackData | null>(null)
  const [active, setActive] = useState(-1)
```

Add this effect immediately after those declarations — note it must sit above the early `return` so hooks order stays stable:

```tsx
  const selId = flights.length ? (flightsFor(flights, ownerSel && owners.includes(ownerSel) ? ownerSel : (FEATURED_ORDER.find((o) => owners.includes(o)) ?? owners[0]), horizon).find((f) => f.flight_id === fid)?.flight_id ?? '') : ''
```

That is fragile. Instead restructure: move the early `return` to the very top of the component body, before any hook that depends on `owner`. Concretely, replace the block

```tsx
  const [ownerSel, setOwner] = useState('')
  const [fid, setFid] = useState<string | undefined>(undefined)

  if (!flights.length || !ordered.length) return <section className="exp wrap" id="explore" />
  const owner = ownerSel && owners.includes(ownerSel) ? ownerSel : ordered[0]

  const myFlights = flightsFor(flights, owner, horizon)
  const standout = standoutFlight(myFlights)
  const sel = myFlights.find((f) => f.flight_id === fid) ?? standout
```

with

```tsx
  const [ownerSel, setOwner] = useState('')
  const [fid, setFid] = useState<string | undefined>(undefined)
  const [track, setTrack] = useState<TrackData | null>(null)
  const [active, setActive] = useState(-1)

  const owner = ownerSel && owners.includes(ownerSel) ? ownerSel : (ordered[0] ?? '')
  const myFlights = owner ? flightsFor(flights, owner, horizon) : []
  const sel = myFlights.length ? myFlights.find((f) => f.flight_id === fid) ?? standoutFlight(myFlights) : null

  // Load the selected flight's track for the profile chart, and reset the
  // cursor to "let the map animate itself" whenever the flight changes.
  useEffect(() => {
    if (!sel) return
    let alive = true
    setActive(-1)
    setTrack(null)
    loadTrack(sel.flight_id).then((gj) => {
      if (alive && gj) setTrack(parseTrack(gj))
    })
    return () => { alive = false }
  }, [sel?.flight_id])

  if (!flights.length || !ordered.length || !sel) return <section className="exp wrap" id="explore" />
```

- [ ] **Step 6: Pass the cursor to the map and render the profile**

In the same file, replace the `<div className="exp-map">…</div>` block with:

```tsx
        <div className="exp-map">
          <Suspense fallback={null}>
            <FlightMap
              flightId={sel.flight_id}
              owner={owner}
              date={prettyDate(sel.date)}
              activeSegment={active >= 0 ? active : undefined}
            />
          </Suspense>
          <div className="map-cap">
            <b>{owner} · {prettyDate(sel.date)}</b> — the contrail inks itself along the real flight path, coloured by where warming happened.
            <div className="legend">
              <span><i style={{ background: rgbCss(RED) }} /> contrail warms</span>
              <span><i style={{ background: rgbCss(AMBER) }} /> fuel-CO₂ baseline</span>
              <span><i style={{ background: rgbCss(BLUE) }} /> contrail cools</span>
            </div>
          </div>
        </div>
        {track && <Profile track={track} active={active >= 0 ? active : track.peakIndex} onActive={setActive} />}
```

- [ ] **Step 7: Add the styles**

Append to `frontend/src/styles.css`:

```css
/* altitude / EF profile under the explorer map */
.profile{ border-top:1px solid var(--hair); padding:1.1rem 1.7rem 1.5rem; background:var(--panel-2); }
.profile-head{ display:flex; flex-wrap:wrap; align-items:center; justify-content:space-between; gap:.6rem 1rem; }
.profile-head .hztoggle button{ font-size:.78rem; padding:.36rem .85rem; min-height:40px; }
.profile-read{ color:var(--muted); font-size:.8rem; font-variant-numeric:tabular-nums; }
.profile svg{ width:100%; height:clamp(90px,14vh,150px); display:block; margin-top:.8rem; }
.profile-scrub{ width:100%; margin-top:.5rem; accent-color:var(--warm); height:44px; touch-action:manipulation; }
```

- [ ] **Step 8: Run the tests and typecheck**

Run: `cd frontend && npm test && npm run typecheck`
Expected: PASS, clean.

- [ ] **Step 9: Check it in the browser**

Run `cd frontend && npm run dev -- --port 5188`. In the explorer, drag the scrubber and confirm the plane on the map moves with it; switch flyers and confirm the map returns to self-animating. Stop the server.

- [ ] **Step 10: Commit**

```bash
git add frontend/src
git commit -m "feat(04): altitude/EF profile with a scrubber sharing the map's cursor"
```

---

## Task 10: Section 02 — Day or night

**Files:**
- Create: `frontend/src/components/charts/DivergingBar.tsx`
- Create: `frontend/src/components/DayOrNight.tsx`
- Create: `frontend/src/components/DayOrNight.test.tsx`
- Modify: `frontend/src/lib/data.ts`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/styles.css`

**Interfaces:**
- Consumes: `Flight.night_class`, `Flight.contrail_ef_joules`, `contrailKg`, `Horizon` (Task 5).
- Produces:
  - `export interface NightGroup { cls: 'night' | 'mixed' | 'day'; flights: number; warmed: number; cooled: number; co2eT: number }`
  - `export function nightSplit(flights: Flight[], h: Horizon): NightGroup[]` — always returns three groups in the order night, mixed, day, counting only flights that formed a contrail.
  - `<DivergingBar groups={NightGroup[]} />`
  - `<DayOrNight flights={Flight[]} horizon={Horizon} />`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/components/DayOrNight.test.tsx`:

```tsx
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { Flight, nightSplit } from '../lib/data'
import DayOrNight from './DayOrNight'

const flight = (o: Partial<Flight>): Flight => ({
  flight_id: 'x_1',
  owner_label: 'X',
  registration: 'N1',
  ac_type: 'Boeing 757-200',
  dep_time: null,
  date: '2025-01-01',
  route: '',
  fuel_co2_kg: 1000,
  contrail_ef_joules: 0,
  contrail_co2e_low: 0,
  contrail_co2e_central: 0,
  contrail_co2e_high: 0,
  contrail_co2e_gwp20_central: 0,
  contrail_pct_of_fuel: 0,
  bizjet_alt_flag: false,
  proxy_type_flag: false,
  coverage_gap_flag: false,
  tier: 'high',
  night_pct_of_waypoints: null,
  night_class: null,
  ...o,
})

const FLIGHTS: Flight[] = [
  flight({ flight_id: 'n1', night_class: 'night', contrail_ef_joules: 3e14, contrail_co2e_central: 90000 }),
  flight({ flight_id: 'n2', night_class: 'night', contrail_ef_joules: 1e14, contrail_co2e_central: 30000 }),
  flight({ flight_id: 'd1', night_class: 'day', contrail_ef_joules: -2e14, contrail_co2e_central: -60000 }),
  flight({ flight_id: 'd2', night_class: 'day', contrail_ef_joules: 5e12, contrail_co2e_central: 1500 }),
  flight({ flight_id: 'z1', night_class: 'day', contrail_ef_joules: 0, contrail_co2e_central: 0 }),
  flight({ flight_id: 'm1', night_class: 'mixed', contrail_ef_joules: 1e13, contrail_co2e_central: 3000 }),
]

describe('nightSplit', () => {
  it('returns night, mixed and day in that order', () => {
    expect(nightSplit(FLIGHTS, 'GWP100').map((g) => g.cls)).toEqual(['night', 'mixed', 'day'])
  })

  it('counts only flights that formed a contrail', () => {
    const day = nightSplit(FLIGHTS, 'GWP100').find((g) => g.cls === 'day')!
    expect(day.flights).toBe(2) // z1 formed nothing and is excluded
  })

  it('splits warmed and cooled by the sign of the forcing', () => {
    const [night, , day] = nightSplit(FLIGHTS, 'GWP100')
    expect(night).toMatchObject({ warmed: 2, cooled: 0 })
    expect(day).toMatchObject({ warmed: 1, cooled: 1 })
  })

  it('sums CO₂e in tonnes for the chosen horizon', () => {
    const night = nightSplit(FLIGHTS, 'GWP100')[0]
    expect(night.co2eT).toBeCloseTo(120)
  })

  it('ignores flights with no classification', () => {
    const unclassified = [...FLIGHTS, flight({ flight_id: 'u1', contrail_ef_joules: 9e14 })]
    const total = nightSplit(unclassified, 'GWP100').reduce((s, g) => s + g.flights, 0)
    expect(total).toBe(5)
  })
})

describe('DayOrNight', () => {
  it('states the night result', () => {
    render(<DayOrNight flights={FLIGHTS} horizon="GWP100" />)
    expect(screen.getByTestId('night-line')).toHaveTextContent(/2 of 2/)
  })

  it('carries a text equivalent for the chart', () => {
    render(<DayOrNight flights={FLIGHTS} horizon="GWP100" />)
    expect(screen.getByTestId('diverging-alt')).toHaveTextContent(/night/i)
  })

  it('renders nothing when no flight is classified', () => {
    const { container } = render(<DayOrNight flights={[flight({})]} horizon="GWP100" />)
    expect(container).toBeEmptyDOMElement()
  })
})
```

- [ ] **Step 2: Run it to confirm it fails**

Run: `cd frontend && npm test -- DayOrNight`
Expected: FAIL — `nightSplit` is not exported and `./DayOrNight` does not resolve.

- [ ] **Step 3: Add the aggregation helper**

Append to `frontend/src/lib/data.ts`:

```ts
// ---- day / night --------------------------------------------------------
// night_class comes from batch/add_night_split.py: the share of a flight's
// CRUISE waypoints with the sun more than 6 degrees below the horizon.
export interface NightGroup {
  cls: 'night' | 'mixed' | 'day'
  flights: number
  warmed: number
  cooled: number
  co2eT: number
}

const NIGHT_ORDER: NightGroup['cls'][] = ['night', 'mixed', 'day']

// Only flights that actually formed a contrail are counted: the ~54 that formed
// nothing say nothing about the sign of the effect and would swamp the ratios.
export function nightSplit(flights: Flight[], h: Horizon): NightGroup[] {
  return NIGHT_ORDER.map((cls) => {
    const fs = flights.filter((f) => f.night_class === cls && f.contrail_ef_joules !== 0)
    return {
      cls,
      flights: fs.length,
      warmed: fs.filter((f) => f.contrail_ef_joules > 0).length,
      cooled: fs.filter((f) => f.contrail_ef_joules < 0).length,
      co2eT: fs.reduce((s, f) => s + contrailKg(f, h), 0) / 1000,
    }
  })
}
```

- [ ] **Step 4: Write the diverging bar**

Create `frontend/src/components/charts/DivergingBar.tsx`:

```tsx
import { NightGroup } from '../../lib/data'

const LABEL: Record<NightGroup['cls'], string> = { night: 'Night', mixed: 'Mixed', day: 'Day' }

// Warming right in crimson, cooling left in blue, from a centre zero axis.
export default function DivergingBar({ groups }: { groups: NightGroup[] }) {
  const max = Math.max(...groups.map((g) => Math.abs(g.co2eT)), 1)

  return (
    <div className="diverge">
      {groups.map((g) => {
        const pct = (Math.abs(g.co2eT) / max) * 50
        const warm = g.co2eT >= 0
        return (
          <div className="diverge-row" key={g.cls}>
            <div className="diverge-label">{LABEL[g.cls]}</div>
            <div className="diverge-track" aria-hidden="true">
              <span className="diverge-axis" />
              <i
                className={warm ? 'warm' : 'cool'}
                style={warm ? { left: '50%', width: `${pct}%` } : { right: '50%', width: `${pct}%` }}
              />
            </div>
            <div className={`diverge-val ${warm ? 'warm' : 'cool'}`}>
              {warm ? '+' : '−'}
              {Math.abs(g.co2eT).toFixed(1)} t
            </div>
            <div className="diverge-count">
              {g.warmed} warmed · {g.cooled} cooled
            </div>
          </div>
        )
      })}
      <p className="sr-only" data-testid="diverging-alt">
        {groups
          .map(
            (g) =>
              `${LABEL[g.cls]} flights: ${g.flights} formed a contrail, ${g.warmed} warmed, ${g.cooled} cooled, ` +
              `net ${g.co2eT >= 0 ? 'plus' : 'minus'} ${Math.abs(g.co2eT).toFixed(1)} tonnes CO₂e.`,
          )
          .join(' ')}
      </p>
    </div>
  )
}
```

- [ ] **Step 5: Write the section**

Create `frontend/src/components/DayOrNight.tsx`:

```tsx
import { useEffect, useRef, useState } from 'react'
import { Flight, Horizon, nightSplit } from '../lib/data'
import { reduced } from '../lib/scroll'
import DivergingBar from './charts/DivergingBar'
import Appear from './Appear'

// The section darkens as you scroll it — the only place the day-to-night colour
// move is used, because here it is the physics rather than decoration.
const DAY_BG = [17, 35, 58]
const NIGHT_BG = [4, 8, 15]

export default function DayOrNight({ flights, horizon }: { flights: Flight[]; horizon: Horizon }) {
  const ref = useRef<HTMLElement>(null)
  const [p, setP] = useState(reduced() ? 1 : 0)

  const groups = nightSplit(flights, horizon)
  const night = groups.find((g) => g.cls === 'night')!
  const day = groups.find((g) => g.cls === 'day')!
  const any = groups.some((g) => g.flights > 0)

  useEffect(() => {
    if (reduced()) return
    const el = ref.current
    if (!el) return
    let raf = 0
    const onScroll = () => {
      cancelAnimationFrame(raf)
      raf = requestAnimationFrame(() => {
        const r = el.getBoundingClientRect()
        const span = Math.max(1, r.height + window.innerHeight)
        setP(Math.min(1, Math.max(0, (window.innerHeight - r.top) / span)))
      })
    }
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => { window.removeEventListener('scroll', onScroll); cancelAnimationFrame(raf) }
  }, [])

  if (!any) return null

  const mix = DAY_BG.map((c, i) => Math.round(c + (NIGHT_BG[i] - c) * p))
  const dayPct = day.flights ? Math.round((100 * day.cooled) / day.flights) : 0

  return (
    <section
      className="dayornight"
      id="day-or-night"
      ref={ref as any}
      style={{ background: `rgb(${mix.join(',')})` }}
    >
      <div className="wrap">
        <Appear>
          <div className="eyebrow">03 — The sign flip</div>
          <h2 className="sec-head" style={{ marginTop: '.6rem' }}>
            Day or night decides the sign
          </h2>
          <p className="sec-sub">
            A contrail traps outgoing heat and reflects incoming sunlight. At night there is no sunlight to reflect, so
            only the trapping remains. Classifying every flight by how much of its cruise happened in darkness, and
            counting only the {groups.reduce((s, g) => s + g.flights, 0)} that formed a contrail at all:
          </p>
        </Appear>

        <DivergingBar groups={groups} />

        <p className="don-line" data-testid="night-line">
          Night flights: <b>{night.warmed} of {night.flights} warmed</b>, none cooled. Day flights:{' '}
          <b>{day.cooled} of {day.flights} cooled</b> ({dayPct}%).
        </p>
        <p className="don-note">
          An earlier waypoint-level analysis of 62 cached runs found 74% day cooling and 100% night warming; this
          flight-level split, computed independently from the raw tracks, lands within a point of it. Note that the
          night flights here were deliberately harvested, so the night share of this sample is not representative of
          aviation — the sign result is, the incidence is not.
        </p>
      </div>
    </section>
  )
}
```

- [ ] **Step 6: Add the styles**

Append to `frontend/src/styles.css`:

```css
/* ============================================================ 02 · DAY OR NIGHT */
.dayornight{ padding:6rem 0; transition:background .2s linear; }
.diverge{ margin-top:2.2rem; display:flex; flex-direction:column; gap:1rem; }
.diverge-row{ display:grid; grid-template-columns:5.5rem 1fr 7rem; grid-template-areas:"label track val" ". count count";
  align-items:center; gap:.35rem .9rem; }
.diverge-label{ grid-area:label; font-family:var(--sans); font-weight:700; font-size:1rem; }
.diverge-track{ grid-area:track; position:relative; height:26px; background:rgba(255,255,255,.04); border-radius:6px; }
.diverge-axis{ position:absolute; left:50%; top:-4px; bottom:-4px; width:1px; background:var(--hair); }
.diverge-track i{ position:absolute; top:3px; bottom:3px; border-radius:4px; }
.diverge-track i.warm{ background:linear-gradient(90deg,var(--warm),var(--warm-deep)); }
.diverge-track i.cool{ background:linear-gradient(270deg,var(--cool),#2f6aa8); }
.diverge-val{ grid-area:val; text-align:right; font-family:var(--sans); font-weight:700;
  font-variant-numeric:tabular-nums; font-size:1.05rem; }
.diverge-val.warm{ color:var(--warm); } .diverge-val.cool{ color:var(--cool); }
.diverge-count{ grid-area:count; color:var(--muted); font-size:.76rem; }
.don-line{ margin-top:2rem; font-size:clamp(1.05rem,2.2vw,1.35rem); line-height:1.55; color:var(--ink-2); }
.don-line b{ color:var(--ink); }
.don-note{ margin-top:1rem; color:var(--muted); font-size:.84rem; line-height:1.6; max-width:70ch; }
@media (max-width:560px){ .diverge-row{ grid-template-columns:4.2rem 1fr 5.5rem; } }
@media (prefers-reduced-motion:reduce){ .dayornight{ transition:none; } }
```

- [ ] **Step 7: Mount it**

In `frontend/src/App.tsx`, import and place it between `Leaderboard` and `OneSegment`:

```tsx
import DayOrNight from './components/DayOrNight'
```

```tsx
            <Leaderboard owners={owners} total={flights.length} horizon={horizon} onHorizon={setHorizon} />
            <DayOrNight flights={flights} horizon={horizon} />
            <OneSegment flights={flights} />
            <Explorer flights={flights} horizon={horizon} onHorizon={setHorizon} />
```

Section eyebrows are now: Leaderboard `01`, DayOrNight `03`… which is wrong. Fix the numbering so it reads in page order: set `OneSegment`'s eyebrow to `02 — The concentration` (already correct), and change `DayOrNight`'s to `03 — The sign flip` only if it sits after OneSegment. Since DayOrNight is mounted *before* OneSegment here, swap the strings: `DayOrNight` → `02 — The sign flip`, `OneSegment` → `03 — The concentration`.

- [ ] **Step 8: Run the tests and typecheck**

Run: `cd frontend && npm test && npm run typecheck`
Expected: PASS, clean.

- [ ] **Step 9: Verify the contrast at both ends of the background range**

Run `cd frontend && npm run dev -- --port 5188`, scroll through section 02 and confirm body text stays legible at the top (light end), the middle, and the bottom (dark end). `--ink-2` on `rgb(17,35,58)` and on `rgb(4,8,15)` must both clear 4.5:1; if the light end fails, darken `DAY_BG`. Stop the server.

- [ ] **Step 10: Commit**

```bash
git add frontend/src
git commit -m "feat(02): day-or-night sign flip with a scroll-darkening background"
```

---

## Task 11: Section 05 — The night widebodies

**Files:**
- Create: `frontend/src/components/NightWidebodies.tsx`
- Create: `frontend/src/components/NightWidebodies.test.tsx`
- Modify: `frontend/src/lib/data.ts`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/styles.css`

**Interfaces:**
- Consumes: `frontend/public/data/comparators.json` (Task 4).
- Produces:
  - `export interface Comparator { flight_id: string; owner_label: string; ac_type: string; fuel_co2_kg: number; contrail_co2e_central: number; contrail_pct_of_fuel: number }`
  - `export async function loadComparators(): Promise<Comparator[]>` — resolves to `[]` on any failure.
  - `<NightWidebodies />`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/components/NightWidebodies.test.tsx`:

```tsx
import { render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import NightWidebodies from './NightWidebodies'

const ROWS = [
  { flight_id: 'a_1', owner_label: 'F-GSQK (B77W)', ac_type: 'BOEING 777-300ER', fuel_co2_kg: 274343.2, contrail_co2e_central: 158633.6, contrail_pct_of_fuel: 57.8 },
  { flight_id: 'b_1', owner_label: 'G-XWBC (A35K)', ac_type: 'AIRBUS A-350-1000', fuel_co2_kg: 234674.8, contrail_co2e_central: 193180.8, contrail_pct_of_fuel: 82.3 },
  { flight_id: 'c_1', owner_label: 'G-ZBKF (B789)', ac_type: 'BOEING 787-9', fuel_co2_kg: 154466.4, contrail_co2e_central: 8737.2, contrail_pct_of_fuel: 5.7 },
]

afterEach(() => vi.unstubAllGlobals())

const stubFetch = (rows: unknown) =>
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => rows }))

describe('NightWidebodies', () => {
  it('lists every comparator flight', async () => {
    stubFetch(ROWS)
    render(<NightWidebodies />)
    await waitFor(() => expect(screen.getAllByTestId('cmp-row')).toHaveLength(3))
  })

  it('shows the aggregate ratio computed from the rows, not a hardcoded number', async () => {
    stubFetch(ROWS)
    render(<NightWidebodies />)
    // (158633.6 + 193180.8 + 8737.2) / (274343.2 + 234674.8 + 154466.4) = 54.4%
    await waitFor(() => expect(screen.getByTestId('cmp-aggregate')).toHaveTextContent('54%'))
  })

  it('renders nothing when the comparators are unavailable', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 404 }))
    const { container } = render(<NightWidebodies />)
    await waitFor(() => expect(container).toBeEmptyDOMElement())
  })

  it('says the ratio is not a per-flight multiplier', async () => {
    stubFetch(ROWS)
    render(<NightWidebodies />)
    await waitFor(() => expect(screen.getByTestId('cmp-caveat')).toHaveTextContent(/not a per-flight multiplier/i))
  })
})
```

- [ ] **Step 2: Run it to confirm it fails**

Run: `cd frontend && npm test -- NightWidebodies`
Expected: FAIL — cannot resolve `./NightWidebodies`.

- [ ] **Step 3: Add the loader**

Append to `frontend/src/lib/data.ts`:

```ts
// ---- night transatlantic comparators ------------------------------------
export interface Comparator {
  flight_id: string
  owner_label: string
  ac_type: string
  fuel_co2_kg: number
  contrail_co2e_central: number
  contrail_pct_of_fuel: number
}

export async function loadComparators(): Promise<Comparator[]> {
  try {
    const r = await fetch('./data/comparators.json')
    return r.ok ? await r.json() : []
  } catch {
    return []
  }
}
```

- [ ] **Step 4: Write the section**

Create `frontend/src/components/NightWidebodies.tsx`:

```tsx
import { useEffect, useState } from 'react'
import { Comparator, loadComparators, tonnes } from '../lib/data'
import Appear from './Appear'

export default function NightWidebodies() {
  const [rows, setRows] = useState<Comparator[] | null>(null)

  useEffect(() => {
    let alive = true
    loadComparators().then((r) => alive && setRows(r))
    return () => { alive = false }
  }, [])

  if (!rows || !rows.length) return null

  const fuel = rows.reduce((s, r) => s + r.fuel_co2_kg, 0)
  const contrail = rows.reduce((s, r) => s + r.contrail_co2e_central, 0)
  const aggregate = fuel ? (100 * contrail) / fuel : 0
  const maxPct = Math.max(...rows.map((r) => r.contrail_pct_of_fuel), 1)

  return (
    <section className="cmp wrap" id="night-widebodies">
      <Appear>
        <div className="eyebrow">05 — The other end of the scale</div>
        <h2 className="sec-head" style={{ marginTop: '.6rem' }}>
          Five night transatlantic widebodies
        </h2>
        <p className="sec-sub">
          Same pipeline, same physics, different regime: {rows.length} scheduled widebodies crossing the North Atlantic
          at night. Where the daytime private jets netted close to zero, these did not.
        </p>
      </Appear>

      <div className="cmp-list">
        {rows.map((r) => (
          <div className="cmp-row" data-testid="cmp-row" key={r.flight_id}>
            <div className="cmp-name">
              <b>{r.owner_label}</b>
              <span>{r.ac_type}</span>
            </div>
            <div className="cmp-bar" aria-hidden="true">
              <i style={{ width: `${Math.max(2, (r.contrail_pct_of_fuel / maxPct) * 100)}%` }} />
            </div>
            <div className="cmp-nums">
              <span className="fuel">{tonnes(r.fuel_co2_kg, 0)} t fuel</span>
              <span className="warm">+{tonnes(r.contrail_co2e_central, 0)} t contrails</span>
              <b>{r.contrail_pct_of_fuel.toFixed(0)}%</b>
            </div>
          </div>
        ))}
      </div>

      <p className="cmp-agg" data-testid="cmp-aggregate">
        Across all {rows.length}, contrail warming came to <b>{aggregate.toFixed(0)}%</b> of their fuel CO₂ — against
        roughly zero for the daytime private jets above. Same code, same ERA5, same CoCiP. The difference is regime:
        night, and crossing ice-supersaturated air.
      </p>
      <p className="cmp-caveat" data-testid="cmp-caveat">
        This is a contrail-to-fuel ratio for these five specific flights, not a per-flight multiplier and not the
        aviation-wide figure. One of the five crossed no ice-supersaturated air at all and came in near zero, which is
        the point: the effect is a lottery of where and when you fly, not a constant.
      </p>
    </section>
  )
}
```

- [ ] **Step 5: Add the styles**

Append to `frontend/src/styles.css`:

```css
/* ============================================================ 05 · COMPARATORS */
.cmp{ padding:6rem 0; }
.cmp-list{ margin-top:2.2rem; display:flex; flex-direction:column; gap:1px; background:var(--hair);
  border:1px solid var(--hair); border-radius:18px; overflow:hidden; }
.cmp-row{ background:var(--panel-2); padding:1.1rem 1.3rem; display:grid;
  grid-template-columns:minmax(9rem,1.1fr) minmax(6rem,1.4fr) auto; align-items:center; gap:.6rem 1.2rem; }
.cmp-name b{ display:block; font-family:var(--sans); font-size:1rem; }
.cmp-name span{ color:var(--muted); font-size:.76rem; }
.cmp-bar{ height:10px; background:rgba(255,255,255,.05); border-radius:5px; overflow:hidden; }
.cmp-bar i{ display:block; height:100%; border-radius:5px;
  background:linear-gradient(90deg,var(--fuel),var(--warm) 70%,var(--warm-deep)); }
.cmp-nums{ display:flex; gap:.9rem; align-items:baseline; font-size:.8rem; color:var(--muted);
  font-variant-numeric:tabular-nums; white-space:nowrap; }
.cmp-nums .fuel{ color:var(--fuel); } .cmp-nums .warm{ color:var(--warm); }
.cmp-nums b{ font-family:var(--sans); font-size:1.15rem; color:var(--ink); }
.cmp-agg{ margin-top:1.8rem; font-size:clamp(1.05rem,2.2vw,1.3rem); line-height:1.55; color:var(--ink-2); max-width:70ch; }
.cmp-agg b{ color:var(--warm); }
.cmp-caveat{ margin-top:1rem; color:var(--muted); font-size:.84rem; line-height:1.6; max-width:70ch; }
@media (max-width:640px){ .cmp-row{ grid-template-columns:1fr; } .cmp-nums{ flex-wrap:wrap; white-space:normal; } }
```

- [ ] **Step 6: Mount it after the Explorer**

In `frontend/src/App.tsx`:

```tsx
import NightWidebodies from './components/NightWidebodies'
```

```tsx
            <Explorer flights={flights} horizon={horizon} onHorizon={setHorizon} />
            <NightWidebodies />
```

- [ ] **Step 7: Run the tests and typecheck**

Run: `cd frontend && npm test && npm run typecheck`
Expected: PASS, clean.

- [ ] **Step 8: Commit**

```bash
git add frontend/src
git commit -m "feat(05): night transatlantic widebodies — the 20x regime contrast"
```

---

## Task 12: Section 06 — How we know this

**Files:**
- Create: `frontend/src/components/HowWeKnow.tsx`
- Create: `frontend/src/components/HowWeKnow.test.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/styles.css`

**Interfaces:**
- Consumes: `Flight`, `Horizon`, `contrailKg`, `tonnes` from `lib/data`.
- Produces: `<HowWeKnow flights={Flight[]} horizon={Horizon} />`

- [ ] **Step 1: Write the failing test**

Create `frontend/src/components/HowWeKnow.test.tsx`:

```tsx
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { Flight } from '../lib/data'
import HowWeKnow from './HowWeKnow'

const flight = (o: Partial<Flight>): Flight => ({
  flight_id: 'x_1', owner_label: 'X', registration: 'N1', ac_type: 'B752', dep_time: null,
  date: '2025-01-01', route: '', fuel_co2_kg: 10000, contrail_ef_joules: 0,
  contrail_co2e_low: 0, contrail_co2e_central: 0, contrail_co2e_high: 0,
  contrail_co2e_gwp20_central: 0, contrail_pct_of_fuel: 0, bizjet_alt_flag: false,
  proxy_type_flag: false, coverage_gap_flag: false, tier: 'high',
  night_pct_of_waypoints: null, night_class: null, ...o,
})

const FLIGHTS = [
  flight({ flight_id: 'a', contrail_ef_joules: 1e14, contrail_co2e_central: 30000, contrail_co2e_low: 25000, contrail_co2e_high: 36000 }),
  flight({ flight_id: 'b' }),
  flight({ flight_id: 'c', bizjet_alt_flag: true }),
  flight({ flight_id: 'd', proxy_type_flag: true }),
]

describe('HowWeKnow', () => {
  it('reports how many flights formed a contrail', () => {
    render(<HowWeKnow flights={FLIGHTS} horizon="GWP100" />)
    expect(screen.getByTestId('hwk-incidence')).toHaveTextContent('1 of 4')
  })

  it('reports the flagged share', () => {
    render(<HowWeKnow flights={FLIGHTS} horizon="GWP100" />)
    expect(screen.getByTestId('hwk-flagged')).toHaveTextContent('2 of 4')
  })

  it('draws the uncertainty band around the total', () => {
    render(<HowWeKnow flights={FLIGHTS} horizon="GWP100" />)
    expect(screen.getByTestId('hwk-band')).toHaveTextContent(/25\.0/)
    expect(screen.getByTestId('hwk-band')).toHaveTextContent(/36\.0/)
  })

  it('states what is not counted', () => {
    render(<HowWeKnow flights={FLIGHTS} horizon="GWP100" />)
    expect(screen.getByTestId('hwk-excluded')).toHaveTextContent(/NOx/)
    expect(screen.getByTestId('hwk-excluded')).toHaveTextContent(/not the aviation-wide/i)
  })

  it('discloses the night-selection bias', () => {
    render(<HowWeKnow flights={FLIGHTS} horizon="GWP100" />)
    expect(screen.getByTestId('hwk-bias')).toHaveTextContent(/deliberately harvested/i)
  })
})
```

- [ ] **Step 2: Run it to confirm it fails**

Run: `cd frontend && npm test -- HowWeKnow`
Expected: FAIL — cannot resolve `./HowWeKnow`.

- [ ] **Step 3: Write the section**

Create `frontend/src/components/HowWeKnow.tsx`:

```tsx
import { Flight, Horizon, contrailKg, tonnes } from '../lib/data'
import Appear from './Appear'

export default function HowWeKnow({ flights, horizon }: { flights: Flight[]; horizon: Horizon }) {
  const n = flights.length
  const formed = flights.filter((f) => f.contrail_ef_joules !== 0).length
  const flagged = flights.filter((f) => f.bizjet_alt_flag || f.proxy_type_flag || f.coverage_gap_flag).length

  const contrail = flights.reduce((s, f) => s + contrailKg(f, horizon), 0)
  // Scale the GWP100 low/high endpoints to the chosen horizon, then sort —
  // a negative central would otherwise put "high" below "low".
  const scale = (v: number, f: Flight) => {
    const c100 = f.contrail_co2e_central
    return c100 ? v * (contrailKg(f, horizon) / c100) : v
  }
  const low = flights.reduce((s, f) => s + scale(f.contrail_co2e_low, f), 0)
  const high = flights.reduce((s, f) => s + scale(f.contrail_co2e_high, f), 0)
  const band = [low, high].sort((a, b) => a - b)
  const width = Math.max(1e-6, band[1] - band[0])
  const centrePct = Math.min(100, Math.max(0, ((contrail - band[0]) / width) * 100))

  return (
    <section className="hwk wrap" id="how-we-know">
      <Appear>
        <div className="eyebrow">06 — The honesty section</div>
        <h2 className="sec-head" style={{ marginTop: '.6rem' }}>
          How we know this, and what we don’t
        </h2>
      </Appear>

      <div className="hwk-grid">
        <div className="hwk-card">
          <div className="hwk-l">Contrail incidence</div>
          <div className="hwk-v" data-testid="hwk-incidence">
            {formed} of {n}
          </div>
          <p>
            flights formed a contrail with any measurable forcing — {Math.round((100 * formed) / Math.max(1, n))}%.
            Teoh et al. (2024) find roughly 24% across a whole fleet; ours runs higher because the sample was
            deliberately weighted towards night.
          </p>
        </div>

        <div className="hwk-card">
          <div className="hwk-l">Flagged for caution</div>
          <div className="hwk-v" data-testid="hwk-flagged">
            {flagged} of {n}
          </div>
          <p>
            flights carry at least one caveat: cruising above CoCiP’s ~13 km ceiling (so under-counted), flown on a
            proxy aircraft type, or with a gap in ADS-B coverage. Each is labelled where it appears.
          </p>
        </div>

        <div className="hwk-card hwk-wide">
          <div className="hwk-l">Uncertainty · {horizon}</div>
          <div className="hwk-band" aria-hidden="true">
            <i />
            <span style={{ left: `${centrePct}%` }} />
          </div>
          <div className="hwk-bandnums" data-testid="hwk-band">
            <span>{tonnes(band[0])} t</span>
            <b>{tonnes(contrail)} t central</b>
            <span>{tonnes(band[1])} t</span>
          </div>
          <p>
            The contrail term carries roughly ±70% uncertainty — the IPCC rates confidence in contrail radiative
            forcing as <i>low</i>. Every contrail figure on this page sits inside that band. Fuel CO₂, by contrast, is
            near-certain: it follows from fuel burnt.
          </p>
        </div>

        <div className="hwk-card">
          <div className="hwk-l">The EF → CO₂e bridge</div>
          <div className="hwk-v">0.8%</div>
          <p>
            is how far our energy-forcing-to-CO₂e conversion sits from the factor Contrails.org publishes. We then
            apply a 0.42 efficacy factor on top, making these figures more conservative than a raw radiative-forcing
            basis would be.
          </p>
        </div>

        <div className="hwk-card" data-testid="hwk-bias">
          <div className="hwk-l">Selection bias</div>
          <div className="hwk-v">Night-weighted</div>
          <p>
            Part of this dataset was <b>deliberately harvested</b> for night flights, because that is where the
            physics is most visible. The direction of the day/night result holds; the <i>share</i> of flights forming
            contrails here is an upper estimate, not an unbiased sample of aviation.
          </p>
        </div>

        <div className="hwk-card hwk-wide" data-testid="hwk-excluded">
          <div className="hwk-l">What is not counted</div>
          <p>
            These totals are <b>fuel CO₂ plus contrails only</b>. They omit NOx, water vapour and aerosols. That is
            why this is <b>not the aviation-wide ~3× figure</b> you may have read: that number covers every
            non-CO₂ term across the whole fleet, and adding it here would double-count the contrail effect we already
            compute directly. Aircraft, not people.
          </p>
        </div>
      </div>
    </section>
  )
}
```

- [ ] **Step 4: Add the styles**

Append to `frontend/src/styles.css`:

```css
/* ============================================================ 06 · HOW WE KNOW */
.hwk{ padding:6rem 0 2rem; }
.hwk-grid{ margin-top:2.4rem; display:grid; grid-template-columns:repeat(auto-fit,minmax(260px,1fr)); gap:14px; }
.hwk-card{ border:1px solid var(--hair); border-radius:var(--r); padding:1.3rem 1.4rem;
  background:linear-gradient(180deg,var(--panel),var(--panel-2)); }
.hwk-card p{ color:var(--muted); font-size:.86rem; line-height:1.6; margin:.7rem 0 0; }
.hwk-card p b{ color:var(--ink-2); }
.hwk-wide{ grid-column:1 / -1; }
.hwk-l{ color:var(--muted); font-size:.74rem; letter-spacing:.08em; text-transform:uppercase; }
.hwk-v{ font-family:var(--sans); font-weight:700; font-size:clamp(1.7rem,3.6vw,2.4rem);
  font-variant-numeric:tabular-nums; margin-top:.3rem; letter-spacing:-.02em; }
.hwk-band{ position:relative; height:20px; margin-top:1rem; }
.hwk-band i{ position:absolute; inset:6px 0; border-radius:4px;
  background:linear-gradient(90deg,rgba(79,176,245,.28),rgba(232,178,74,.35),rgba(200,30,58,.28)); }
.hwk-band span{ position:absolute; top:0; bottom:0; width:2px; background:var(--ink);
  box-shadow:0 0 8px rgba(255,255,255,.5); }
.hwk-bandnums{ display:flex; justify-content:space-between; align-items:baseline; gap:.6rem;
  margin-top:.5rem; color:var(--muted); font-size:.78rem; font-variant-numeric:tabular-nums; }
.hwk-bandnums b{ color:var(--ink); font-family:var(--sans); }
```

- [ ] **Step 5: Mount it last, before the footer**

In `frontend/src/App.tsx`:

```tsx
import HowWeKnow from './components/HowWeKnow'
```

```tsx
            <NightWidebodies />
            <HowWeKnow flights={flights} horizon={horizon} />
```

- [ ] **Step 6: Run the tests and typecheck**

Run: `cd frontend && npm test && npm run typecheck`
Expected: PASS, clean.

- [ ] **Step 7: Commit**

```bash
git add frontend/src
git commit -m "feat(06): how-we-know section — incidence, flags, uncertainty band, exclusions"
```

---

## Task 13: Verification pass

Everything is built; now prove the constraints hold. No new features.

**Files:**
- Modify: whichever files the checks turn up
- Create: `docs/superpowers/plans/2026-08-03-story-sections-verification.md`

**Interfaces:**
- Consumes: everything.
- Produces: a short written record of measured results, committed alongside any fixes.

- [ ] **Step 1: Full test run and typecheck**

```bash
cd frontend && npm test && npm run typecheck
.venv/bin/python -m pytest tests/ -v
```

Expected: all green. Fix anything that is not before continuing.

- [ ] **Step 2: Measure the bundle against the budget**

```bash
cd frontend && npm run build
for f in dist/assets/*.js; do echo "$(gzip -c "$f" | wc -c) $f"; done | sort -n
```

Record the entry chunk's gzipped size. Budget: ≤ 70 000 bytes. If over, check that `motion`, `deck` and `maplibre` each landed in their own chunk.

- [ ] **Step 3: Responsive check at three widths**

```bash
cd frontend && npm run preview -- --port 5188
```

With the preview running, in a separate shell:

```bash
node -e "
const {chromium} = require('playwright');
(async () => {
  const b = await chromium.launch();
  for (const w of [390, 768, 1440]) {
    const p = await b.newPage({viewport:{width:w,height:900}});
    await p.goto('http://localhost:5188', {waitUntil:'networkidle'});
    await p.waitForTimeout(1500);
    const over = await p.evaluate(() => document.documentElement.scrollWidth > window.innerWidth);
    console.log(w, 'horizontal overflow:', over);
    await p.screenshot({path:\`/tmp/tcof-\${w}.png\`, fullPage:false});
    await p.close();
  }
  await b.close();
})();
"
```

Expected: `horizontal overflow: false` at all three widths. If Playwright is not installed locally, use the Playwright MCP browser instead — the requirement is the check, not the tool.

- [ ] **Step 4: Reduced-motion check**

In the same preview, open DevTools → Rendering → "Emulate CSS prefers-reduced-motion: reduce", reload, and walk the whole page. Confirm:

- the hero renders un-pinned and fully readable
- section 02's background is settled at a legible value, not stuck mid-transition
- section 03 shows the peak segment highlighted rather than an empty cursor at index 0
- the leaderboard reorders instantly with no layout animation
- the map is fully drawn with the plane parked

- [ ] **Step 5: Keyboard and screen-reader check**

Tab through the whole page. Confirm: every metric button, horizon button, pill, flight chip and the profile scrubber are reachable and show a visible focus ring; the profile slider responds to arrow keys; switching the ranking metric updates the `aria-live` region text.

- [ ] **Step 6: Contrast check on the new surfaces**

Check with DevTools' contrast inspector: `.don-note` and `.don-line` against both ends of section 02's background range; `.cmp-nums` muted text on `--panel-2`; `.hwk-bandnums` on `--panel`. All body text must clear 4.5:1, large text 3:1. Darken tokens rather than adding one-off hex values.

- [ ] **Step 7: Framing-rule audit**

```bash
cd frontend && grep -rn "3×\|3x\|pct_of_fuel\|toFixed(0)}%" src/components/
```

Read every hit. Confirm no surface presents a per-flight percentage of fuel as a headline figure, and that every place the aviation-wide ~3× appears, it appears as a disclaimer that this is *not* that number.

- [ ] **Step 8: Write the verification record**

Create `docs/superpowers/plans/2026-08-03-story-sections-verification.md` with the measured entry-chunk size, the track directory size before and after, the three overflow results, and a line per constraint in the spec's §7 marked pass or fixed-then-pass. Numbers, not adjectives.

- [ ] **Step 9: Commit**

```bash
git add -A
git commit -m "verify: bundle, responsive, reduced-motion, a11y and framing checks for the story sections"
```

---

## Self-Review

**Spec coverage** — every section of the spec maps to a task:

| Spec | Task |
| --- | --- |
| §4.1 ranking + metric switch + horizon move | 5, 6 |
| §4.2 day or night | 3, 10 |
| §4.3 one segment | 4, 7, 8 |
| §4.4 explorer profile | 4, 7, 9 |
| §4.5 night widebodies | 4, 11 |
| §4.6 how we know this | 12 |
| §5.1 re-export altitude + signed EF | 4 |
| §5.2 night split script | 2, 3 |
| §5.3 comparators export | 4 |
| §6 motion only, no other deps | 6 (LazyMotion), 13 step 2 |
| §7.1 framing rule | 6, 11, 12, and audited in 13 step 7 |
| §7.2 offline/online split | 3 (batch only), 4 (build-time only) |
| §7.3 reduced motion | 6, 8, 10, verified in 13 step 4 |
| §7.4 accessibility | 6, 8, 9, 10, verified in 13 step 5 |
| §7.5 performance | 6 step 13, 13 step 2 |
| §7.6 honesty captions | 10, 11, 12 |
| §8 verification | 13 |
| §9 sequencing | task order follows it |

**Known deviation from the spec:** §4.3 specifies a sticky map with the chart below it and Swift's flight as the hero. Task 8 implements exactly that, but drops the spec's phrasing "median 8 non-zero of 156, top-5 = 95.4%" into prose rather than a second chart — one chart per idea. Recorded here rather than silently changed.

**Placeholder scan:** no TBD/TODO; every code step carries real code; no "similar to task N".

**Type consistency:** `Metric`, `OwnerAgg`, `Segment`, `TrackData`, `NightGroup` and `Comparator` are each defined once and used with the same field names throughout. `activeSegment` is the prop name on `FlightMap` in Tasks 8 and 9. The exported geojson property is `ef_tj` in Task 4 and read as `ef_tj` in Task 7. `parseTrack` returns `peakIndex` and it is consumed as `peakIndex` in Tasks 8 and 9.

**One risk to watch:** Task 9 restructures the Explorer's hook order. If the component throws "rendered fewer hooks than expected", the early `return` has drifted back above a hook — all hooks must sit above the guard.
