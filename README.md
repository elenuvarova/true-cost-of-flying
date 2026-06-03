# True Cost of Flying ✈️

**The CO₂ number every flight tracker shows you is only about a third of the warming.** This tool takes a real flight and shows, for the *same flight*, two numbers side by side: **fuel CO₂** (what everyone shows) and **combined CO₂e = fuel CO₂ + contrail warming**, computed with real contrail physics (CoCiP), fronted by a private-jet leaderboard.

> Contrails — the white lines behind jets — spread into heat-trapping cirrus. Across aviation their warming is **larger than all the CO₂ from jet fuel**, yet no consumer tool counts it per flight. This does.

Built entirely on **free** data and tools (no paid APIs, no database). A portfolio / product case study balancing product thinking with defensible climate science.

**What's in the demo:** 44 real flights from 9 public-figure jets (Dec 2024 – Jan 2025), tracked via [adsb.lol](https://adsb.lol): New England Patriots, Donald Trump, Taylor Swift, Eric Schmidt, Bill Gates, Elon Musk, Kylie Jenner, Phil Knight (Nike), Mark Zuckerberg. The physics is honest, not theatrical — some daytime contrails **cool** (Musk −19 t on one flight), while a single Taylor Swift flight's contrails **more than doubled** its fuel-CO₂ warming (+105 % at GWP20). Business-jet figures above CoCiP's ~13 km calibration ceiling are flagged as under-counted, not extrapolated.

## How it works

```
OFFLINE BATCH (this repo, run once)                    DEPLOYED APP (read-only)
adsb.lol globe_history  ── real flight tracks          app.py (Streamlit)
   → OpenAP             ── fuel burn → CO₂        ┐       reads committed
   → ERA5 (ARCO, anon)  ── humidity/met           ├──►   data/processed/*.parquet
   → pycontrails CoCiP  ── contrail energy forcing │      + tracks/*.geojson
   → fuse + GWP + bands ── combined CO₂e           ┘      → leaderboard + map + reveal
        ↓
   data/processed/leaderboard.parquet + tracks/*.geojson  (committed, < 1 MB)
```

The heavy physics (CoCiP + ERA5) runs **offline** and is precomputed into small static files. The deployed app only reads them — no live compute, no API keys, no DB. That's why it deploys free.

## Run the app locally

```bash
python3.12 -m venv .venv-app && . .venv-app/bin/activate
pip install -r requirements.txt
streamlit run app.py        # → http://localhost:8501
```

## Regenerate the data (offline batch — optional)

Needs the heavier batch environment (pycontrails, OpenAP, ERA5 access — all free):

```bash
python3.12 -m venv .venv && . .venv/bin/activate
pip install -r requirements-batch.txt
python batch/build_dataset.py     # writes data/processed/{leaderboard.parquet, tracks/*.geojson}
```

ERA5 is read anonymously from the public ARCO bucket (no Copernicus/Google account). The ERA5 cache lives outside the repo (`~/.cache/tcof_era5`, override with `TCOF_CACHE_DIR`) — **keep it off iCloud-synced folders**.

## Project layout

| Path | What |
|------|------|
| `app.py` | Deployed Streamlit app (read-only) |
| `src/` | `tracks.py` (adsb.lol parser), `fuel.py` (OpenAP), `contrails.py` (CoCiP), `fuse.py` (CO₂e + tiers), `era5.py`, `constants.py` |
| `batch/build_dataset.py` | Offline pipeline → static artifacts |
| `data/processed/` | Committed leaderboard + track GeoJSON (what the app serves) |
| `docs/` | `RESEARCH_BRIEF.md`, `IMPLEMENTATION_PLAN.md`, `JET_SHORTLIST.md`, `PHASE_*_RESULT.md`, `VALIDATION.md` |

## Honest caveats (built into the UI)

CO₂e is never shown as a bare number: GWP100 default + GWP20 toggle + uncertainty band. The fused total is **fuel CO₂ + contrails only** (omits NOx / water vapour / aerosols — the aviation-wide "~3×" includes those). Contrail warming carries ~70% uncertainty (IPCC "low confidence"). Business jets cruise above CoCiP's ~13 km calibration ceiling, so their contrails are **under-counted, not extrapolated** (flagged). Figures are for *flights associated with an aircraft* — not proof of who was aboard.

## Does the model agree with published science?

Yes — and where it doesn't, [`docs/VALIDATION.md`](docs/VALIDATION.md) says so in numbers (and a condensed version ships in-app). On this 44-flight set, **32% of flights form a persistent contrail and 16% form a net-warming one** — matching Teoh et al. 2024's fleet figures (~24% / ~14%) on a completely different (private-jet, winter) sample. Per-flight contrail-vs-fuel ratios reach the published **33–63% (GWP100)** band when a jet crosses ice-supersaturated air below the calibration cap, and a *single track segment* often carries a flight's entire warming — reproducing the known power-law. The sample aggregate sits *below* the fleet figure (short winter US/EU legs largely miss the busy contrail corridors; about half the forming flights cool), and the biases (ERA5 dry bias, the bizjet altitude cap) push the numbers **down** — so the tool errs toward *under*-stating.

## Data & credits

Flight tracks: [adsb.lol](https://adsb.lol) (ODbL-1.0) · Meteorology: ECMWF ERA5 (ARCO) · Performance: [OpenAP](https://openap.dev) · Contrail physics: [pycontrails / CoCiP](https://py.contrails.org). Non-commercial / educational.
