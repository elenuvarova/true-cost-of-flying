# Phase 2 + app skeleton — DONE (2026-06-02)

## Reusable modules (offline batch)
- `src/contrails.py` — `run_cocip()`: CoCiP on a track → (EF Joules, per-waypoint df). Handles PS-model proxy (GLF6→GLF5, C550→E145) + humidity scaling + resample.
- `src/fuse.py` — `build_row()` (full leaderboard schema, GWP100+GWP20, low/central/high band, proxy/bizjet/coverage flags) + `assign_tiers()` (high/med/low, not a spurious 1..N rank).
- `batch/build_dataset.py` — orchestrates trace → fuel → met → CoCiP → fuse → **writes `data/processed/leaderboard.parquet` + `tracks/<id>.geojson`** (decimated ≤500 vtx, per-segment EF for colouring). This is the only place CoCiP/ERA5 run.

## Reproducibility
- `requirements-batch.txt` — 68 pkgs pinned (numpy 2.4.6, pycontrails 0.63.1, openap 2.5.0, scipy 1.17.1, xarray 2026.4, zarr 3.2.1). numpy-2-coupled stack locked.
- `requirements.txt` — 41 pkgs, app only (streamlit 1.58, pydeck, pandas, pyarrow) in a separate `.venv-app` (no pycontrails/ERA5 → tiny deploy).

## Artifacts produced (real, committed-ready)
`leaderboard.parquet` 16 KB (2 rows), 2 track GeoJSONs ~31 KB each (140/134 segments). Well under the <10 MB git budget.

| Owner | Combined CO₂e (GWP100) | Contrails add (GWP100 / GWP20) | Tier | Flags |
|---|---|---|---|---|
| NE Patriots (767) | 46.0 t | +6% / +23% | high | — |
| Taylor Swift (Falcon 7X, FL430) | 9.2 t | +0% / +0% | medium | proxy, bizjet-alt under-count |

## App (Phase 4 walking skeleton, built early for visibility)
`app.py` — read-only Streamlit. Reads the committed parquet/geojson, **zero physics/API at runtime**. Features: tiered leaderboard, the "same flight, two numbers" reveal (Fuel CO₂ vs Combined CO₂e with +% delta), GWP100/GWP20 toggle (visibly moves the number), uncertainty band, pydeck PathLayer track coloured by per-segment contrail warming, and the full mandatory caveat block (§11). Smoke-tested headless: HTTP 200, health ok, clean logs, core logic verified.

**Run locally:** `.venv-app/bin/streamlit run app.py` → http://localhost:8501

## Validation status
Physics reproduces the literature expectation: contrail/fuel-CO₂ = 40–52% (GWP100) at contrail-forming levels (Phase 0.5 altitude sweep), within the 33–63% expected band; real flights show honest variability (Patriots +6% low-contrail; Swift 0 above-cap). Cross-check vs Contrails.org Impact Explorer by specific commercial flight number → Phase 3 curation task.

## Next
- **Phase 3** — expand curated set to ~10–12 flights (more shortlist jets on their real flight dates + commercial comparators + the Impact Explorer cross-check), real tiers.
- **Deploy** — push to GitHub, Streamlit Community Cloud (reads committed artifacts; `.venv-app` deps).
