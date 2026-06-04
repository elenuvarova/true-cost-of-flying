# True Cost of Flying

Every jet tracker shows one number — fuel CO₂. Across aviation that is only about **a third** of the
warming; the rest is mostly **contrails**. This shows, for the *same* private-jet flight, **two numbers** —
fuel CO₂ and fuel + contrail CO₂e (computed with CoCiP physics) — with the contrail drawn on a map,
coloured by where the warming actually happened.

**Live:** https://contrails.ontwrpn.com

## Architecture — two strictly-separated halves

- **Offline data pipeline** (`batch/`, `src/`, Python). adsb.lol tracks → OpenAP (fuel → CO₂) → ERA5 +
  `pycontrails` CoCiP (contrails) → `data/processed/leaderboard.parquet` + `tracks/*.geojson`
  (84 flights / 11 public-figure jets). This is the only place the heavy physics runs.
  Dependencies: `requirements-batch.txt`.
- **Frontend** (`frontend/`, React 18 + Vite + TypeScript). A static SPA with **no backend**:
  Lenis smooth-scroll, deck.gl `TripsLayer` + maplibre (dark basemap), the cool→warm "contrail" tonal ramp.
  It reads static JSON produced by `scripts/export_web_data.py` (parquet → `frontend/public/data/`).

## Develop

```bash
# 1. (re)generate the web data from the committed parquet/geojson
python scripts/export_web_data.py
# 2. run the frontend
cd frontend && npm install && npm run dev
```

## Deploy

Static SPA served by nginx in a single Docker image (`frontend/Dockerfile` + `frontend/nginx.conf`),
on the Coolify/Hetzner host at `contrails.ontwrpn.com`. In Coolify set **Base Directory = `frontend`**.
Build = `node` → `vite build` → `nginx:alpine` serving `dist/`.

## The honesty rule (non-negotiable)

The per-flight figure is **fuel CO₂ + contrails only** (typically ~1.3–1.6× fuel at GWP100). It is
**never** presented as the aviation-wide ~3× ERF (which also includes NOx, water vapour and aerosols).
Contrail warming carries ~70% uncertainty (IPCC "low confidence"); business-jet contrails above CoCiP's
~13 km cap are flagged as under-counted, not extrapolated. See `docs/` for the validation write-up.
