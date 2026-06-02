# Phase 1 — Real-track pipeline: PASSED (2026-06-02)

End-to-end on **real adsb.lol `globe_history` tracks** (day 2024-12-30, `prod` release).
No synthetic data. Full chain: gzip readsb trace → flight detection → hex/type from the
trace → OpenAP fuel→CO₂ → ERA5ARCO (anon) → CoCiP → EF → efficacy → EF→CO₂e (GWP100/20)
→ two numbers + uncertainty band + confidence flags.

## Results

| Flight (real) | Aircraft | OpenAP type | Fuel CO₂ | Contrail EF | Contrail CO₂e GWP100 (lo/cen/hi) | Combined | Contrail/Fuel | Flags |
|---|---|---|---|---|---|---|---|---|
| **N225NE** (NE Patriots) | Boeing 767-300, 2h21m, FL370 | B763 native | 43.3 t | 9.48e12 J | 2.2 / 2.7 / 3.3 t | 46.0 t | **6%** | none |
| **N621MM** (Taylor Swift) | Falcon 7X, 2h15m, **FL430** | GLF6 proxy | 9.2 t | **0 J** | 0 / 0 / 0 t | 9.2 t | **0%** | PROXY-TYPE, BIZJET-ALT>13km: UNDER-counted |

## What this validates
- **adsb.lol path is real & free** — both jets pulled from a downloaded daily tarball, traces are gzip JSON, altitude at index 3. The two-of-three shortlist hexes present that day (Patriots, Swift; Musk's jet had only 4 points / no flight).
- **OpenAP fuel** works native (B763, via `use_synonym=True`) and via project proxy (FA7X→GLF6).
- **CoCiP** runs on real tracks; PS-model proxy (GLF6→GLF5, C550→E145) covers types PSFlight lacks.
- **Per-flight variability is real and honest:** Patriots = a low-contrail flight (+6%); Phase 0.5 showed +40-52% at contrail-forming levels. Not every flight is an offender.
- **The bizjet-altitude caveat is demonstrated, not just stated:** Swift at FL430 is above CoCiP's ~13 km/FL426 cap → contrail EF = 0 (excluded/under-counted). The `BIZJET-ALT` flag fires automatically. Per plan decision D2 we keep the cap and flag the row rather than extrapolating.

## Engineering notes / gotchas fixed
- **ERA5 cache MUST be outside the iCloud-synced project dir.** Caching GBs into `data/cache` (under CloudDocs) caused iCloud to lock/truncate files → silent process kills + corrupt `.nc` (HDF errors). Moved to `~/.cache/tcof_era5` (override via `TCOF_CACHE_DIR`).
- **gcsfs has no default timeout** → a hung chunk read blocked forever (observed 19-min 0%-CPU stalls). Fixed in `src/era5.py`: set fsspec gcs `timeout=180` + retry (8 attempts, 8s backoff). A transient DNS/connect blip is now retried, not fatal.
- Dedup duplicate trace timestamps (caused divide-by-zero in vertical-rate gradient).
- rad (TOA tsr/ttr) needs `ERA5ARCO(..., pressure_levels=-1)` (single-level store), separate from pressure-level met.

## Files
`src/tracks.py` (trace parser), `src/fuel.py` (OpenAP + proxy map), `src/era5.py` (robust ARCO loader),
`src/constants.py` (EF→CO₂e bridge), `batch/phase1_real_flight.py`.

## Next (Phase 2)
Productionize `contrails.py` + `fuse.py` (banded CO₂e, GWP100+GWP20), lockfile-pin the batch env,
and the validation milestone (compare a commercial comparator's contrail/fuel ratio vs the 33-63% GWP100
expectation and vs Contrails.org Impact Explorer).
