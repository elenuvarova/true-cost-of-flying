# True Cost of Flying — Research Brief

*Synthesis of per-dimension research + adversarial verdicts. Prepared 2026-06-02. This brief drives an implementation plan whose dual goals are (a) a strong PM case study and (b) defensible scientific accuracy. It is honest about uncertainty where the evidence is thin.*

---

## 1. Competitive Landscape & Confirmed White Space

The space splits into three non-overlapping clusters. None of them occupies the project's target niche.

### B2B / scientific contrail players (airline & ANSP facing)
- **Breakthrough Energy / Contrails.org** is the central actor. It open-sourced **pycontrails** (Apache-2.0: CoCiP, CocipGrid, ISSR/SAC, emissions, PS-model, OpenAP integration) — i.e. the project's planned modeling layer is already built and free (https://github.com/contrailcirrus/pycontrails, https://py.contrails.org/). It also runs an access-gated forecast API and public educational tools (Map, Navigator, Impact Explorer) (https://contrails.org/, https://apidocs.contrails.org/). Crucially these tools **separate** CO2 and contrail metrics — they do not sum them into one CO2e number, and there is no per-aircraft/owner leaderboard.
- **Google Research Project Contrails** released open CC-BY datasets (OpenContrails on GOES-16, the Kaggle benchmark) and proved operational avoidance with American Airlines + Flightkeys (54% reduction on 70 flights in 2023; 62% on ~2,400 transatlantic flights in 2025) (https://sites.research.google/gr/contrails/public-datasets/, https://blog.google/innovation-and-ai/models-and-research/google-research/contrail-avoidance-research/). These are satellite-*detection* / *avoidance* products, not consumer transparency.
- **SATAVIA** (acquired by GE Aerospace, Sept 2024) and **Estuaire** (Paris, Safran-backed) are B2B avoidance + carbon-credit SaaS with proprietary NWP models. No public consumer map, no open code (https://business.esa.int/projects/decisionxnetzero, https://estuaire.aero/products/contrail-mitigation).

### Jet trackers
Every consumer tracker stops at CO2. Jack Sweeney's open-source `plane-notify` uses a trivial `fuel_used_kg * 3.15 / 907.185` formula with a per-type fuel-burn table — no non-CO2 (https://github.com/Jxck-S/plane-notify/blob/multi/fuel_calc.py). climatejets.org and celebplanes.com are CO2-only emissions dashboards (https://climatejets.org/methodology, https://www.celebplanes.com/methodology). The viral Yard study applied a flat 2.7x RF multiplier — the closest anyone gets, and it is a fleet-average constant, not physics (https://weareyard.com/insights/worst-celebrity-private-jet-co2-emission-offenders).

### CO2 calculators
- **atmosfair** and **myclimate** include non-CO2 via a flat **x3 RFI multiplier**, not flight-specific physics (https://www.myclimate.org/en/information/about-myclimate/downloads/flight-emission-calculator/).
- **ICAO ICEC** is strictly CO2-only — confirmed by full-text scan of methodology v13.1 (https://icec.icao.int/Documents/Methodology%20ICAO%20Carbon%20Emissions%20Calculator_v13_Final.pdf).
- **Google Travel Impact Model (TIM)** is the most sophisticated incumbent and the best comparison target. Its headline CO2e includes CO2/CH4/N2O via a CORSIA lifecycle factor but **deliberately excludes contrails**, surfacing them as Low/Medium/High buckets and explicitly warning: *"Do not convert contrail impact levels into a CO2e value. This can create a misleading impression of precision."* TIM also does **not** support private/charter/cargo flights or past flights (https://github.com/google/travel-impact-model, https://developers.google.com/travel/impact-model).

### Confirmed white space (precise statement)
No public tool does **both**: (a) fuse fuel-CO2 + contrail/non-CO2 warming into a single combined CO2e "total warming" number, **and** (b) present it as a per-aircraft / per-owner / per-tail-number ranking — especially for private jets.

Be honest in the case study: **each half already ships separately.** ATP-DEC (Nature, 2025) combines CO2 + non-CO2 into one per-passenger figure but has no ranking and is commercial-only (https://www.nature.com/articles/s43247-025-02847-4). Sweeney's Celebrity Private Jet Tracker is a per-owner leaderboard but CO2-only (https://celebrityprivatejettracker.com/leaderboard/). The Contrails.org Impact Explorer **does** rank individual commercial flights by contrail CO2e (GWP100) — but contrail-only, by flight number/route not aircraft/owner, and commercial not private (https://explore.contrails.org/explorer). The 4AIR/Victor 2025 report applied CoCiP to private jets but is a static annual PDF, anonymized, keeping CO2 and contrails separate (https://www.4air.aero/press/victor-and-4air-voluntarily-publish-contrails-report-disclosing-the-non-co2-impact-of-on-demand-private-jet-charters).

**The moat is the fusion + private-jet leaderboard framing, not novelty of the underlying science or either capability alone.** The "CO2 is only half the truth" narrative is mainstream. The differentiator vs every tracker/calculator is **flight-specific CoCiP contrail physics** rather than a flat RFI multiplier or risk bucket.

---

## 2. Data Sources Feasibility

### OpenSky Network — **CAUTION (verdict: usable but with real licensing + attribution caveats)**

**Verified facts:**
- Free, self-service registration; **OAuth2 client-credentials is now mandatory** (basic auth removed ~mid-March 2025, tokens expire 30 min) (https://openskynetwork.github.io/opensky-api/rest.html).
- Credit model (verified verbatim, March 2026 docs): **4,000 credits/day for a registered Standard user, in three INDEPENDENT buckets** (`/states/*`, `/tracks/*`, `/flights/*`) — effectively 4,000 *each*, ~12,000/day total. Anonymous = 400/day; active feeder (own receiver ≥30% uptime) = 8,000. A small-bounding-box `/states/all` (≤25 sq°) costs exactly **1 credit**. This linchpin "free feasibility" fact is **confirmed** (https://raw.githubusercontent.com/openskynetwork/opensky-api/master/docs/free/rest.rst).
- State vectors carry everything needed for a 3D altitude profile (icao24, lat/lon, baro + geo altitude, velocity, vertical_rate, true_track). Units are metric — convert for OpenAP.

**Blockers / gotchas (2024–2025):**
- **Licensing is the sharpest risk.** The Data License Agreement grants use **"solely for non-profit research, non-profit education, or government purposes… No license is granted for any other purpose and there are no implied licenses."** Worse, *operational* use — "integration into a live product, service, or automated system (even internal)" — requires a **prior written agreement**. A publicly hosted Streamlit demo plausibly counts as operational. The earlier claim that a portfolio demo "is permitted without a written license" was **refuted**. (License text: https://s3.opensky-network.org/data-samples/raw/LICENSE.txt) → **Action: email contact@opensky-network.org for permission, or keep it explicitly non-commercial/educational and lean on separately-public FAA registry data for naming.**
- **REST history is shallow.** `/tracks` is experimental, ≤30 days back, only where receivers saw the aircraft; `/flights/aircraft` ≤2-day windows; authenticated state history only ~1 hour back. Deep aggregation needs the Trino DB, which is **off-limits** to a portfolio project (university/government/aviation only). A leaderboard must therefore be built from **curated, pre-fetched/cached flights**, not live polling.
- **Coverage** is strong over US/Europe, weak over oceans/Africa/East Asia — exactly where long contrail-forming flights occur; the contrail step must tolerate gaps.
- **Owner attribution is fragile and is the riskiest narrative dependency, not a data-volume problem.** Position tracks usually survive FAA LADD/§803 (those only filter the FAA feed, not the raw 1090 MHz broadcast OpenSky hears) — so jets remain *visible*. But (i) the crowdsourced OpenSky aircraft DB is community-editable and **documented as astroturfed on owner/model fields** (https://www.mdpi.com/2673-4591/28/1/7); (ii) registered owners are frequently trusts/LLCs masking the beneficial owner; (iii) the PIA program rotates the broadcast hex; (iv) OpenSky (unlike ADS-B Exchange) **honors some opt-outs**, so some celebrity tails will be simply absent. Treat owner labels as best-effort, corroborated, public-figure-only.

### pycontrails + ERA5ARCO — **GO (with a hard architecture constraint, see §3)**

**Verified facts:**
- pycontrails is Apache-2.0, pure-Python, no GPU, Python ≥3.11, current ~v0.63 (2026).
- **ARCO-ERA5 needs NO Copernicus CDS account AND NO Google Cloud account/billing.** This is the key free-access win and was **confirmed by live test**: the public bucket `gs://gcp-public-data-arco-era5` is readable anonymously (`gcsfs token='anon'`, non-requester-pays). The classic CDS path, by contrast, *does* need a free Copernicus account + queue (https://docs.cloud.google.com/storage/docs/public-datasets/era5).
- **Gotcha (confirmed):** pycontrails relies on gcsfs's *default* credential fallback to anon, which **does not fire if stale/invalid Google credentials are present** in the environment (raises RefreshError → 401). On a clean free host this is fine; for robustness, pass `token='anon'` explicitly.
- CoCiP needs ~6 pressure-level variables (temperature, specific humidity, u/v wind, vertical velocity, specific cloud ice water content) + 2 top-of-atmosphere radiation fields (`top_net_solar_radiation`, `top_net_thermal_radiation`) + surface pressure. The model-level store gives fine ~10 hPa cruise-band resolution; the radiation fields are 2D single-level (no vertical interpolation). All required variables are present in ARCO. **Confirmed.**
- Install is clean from wheels on manylinux Python 3.11–3.13 with `pip install 'pycontrails[zarr]'` + `netcdf4` (needed for the disk cache); **no eccodes compilation** (eccodes lives only in the unused `[ecmwf]` extra). **Confirmed.**

**Gotchas:**
- **Spatial subsetting does not shrink the fetch** (confirmed via live zarr metadata): the analysis-ready store is chunked whole-globe per timestep (`{time:1, level:37, lat:721, lon:1440}` ≈ 154 MB decompressed per pressure-level variable-hour; the model-level store ≈ 75 MB/chunk). A small flight box still pulls the global field. This is why the official example warns "~1 GB" even for a tiny region.
- ARCO lags real time ~2–3 months (ERA5T ~1 week) — use historical dates for the demo.

### OpenAP — **GO (cleanest of the three)**

**Verified facts:**
- LGPL-3.0, fully free **and redistributable** (data bundled in the pip package, no registration/no gated files) — unlike BADA, whose performance datasets require a signed EUROCONTROL agreement and **cannot be shipped in a public app**. PIANO is commercial. **Confirmed.**
- CO2 conversion is **exactly 3160 g/kg fuel (= 3.16)** — confirmed in `emission.py` source on the current v2.5.0 release. Matches the project's "3.16x" assumption exactly (https://github.com/junzis/openap/blob/v2.5.0/openap/emission.py).
- Pipeline: `FuelFlow(ac).enroute(mass, tas, alt, vs)` → kg/s; integrate over the track; `* 3.16` for CO2. Compute is trivially light (vectorized polynomial eval). **Confirmed** — OpenAP is *not* a hosting risk.

**Gotchas:**
- **Business-jet coverage is thin.** OpenAP ships 36 native types; only **two are bizjets**: `GLF6` (Gulfstream G650) and `C550` (Cessna Citation II). The default `_synonym.csv` fallback covers some (Global Express `gl5t`→glf6, Learjet 45→glf6, PC-24/CJ-series→c550) but **lacks** Bombardier Challenger (cl30/cl35/cl60) and Embraer Legacy/Praetor — you must add your own mappings and **label proxy types as estimates**.
- "NumPy only" was **wrong**: OpenAP v2.5.0 hard-requires numpy, scipy, pandas, pyyaml, **and matplotlib**. Still light, but the dependency footprint is a few hundred MB.
- icao24 → type needs an external join. The free OpenSky `aircraftDatabase.csv` (with the `typecode` field) is downloadable without an account, but is **updated only irregularly** — confirmed: live file `last-modified 2024-11-04`, newest monthly snapshot 2025-02 as of mid-2026. Recently-registered jets will be missing. Cache a snapshot; design a "type unknown → default proxy" path so the pipeline never hard-fails (https://opensky-network.org/data/aircraft).

---

## 3. The Critical Compute-Architecture Finding

**Question:** Can CoCiP run at request time on free hosting, or must contrail results be precomputed offline?

**Finding (confirmed, with corrected premises):** A general, live, on-request CoCiP service is **not feasible** on free hosting; the leaderboard **must be precomputed offline and shipped as static files**. But the binary "1 GB host" framing in the original brief was wrong:

- The real free-host ceilings are **Streamlit Community Cloud ~2.7 GB RAM / 2 CPU** (not 1 GB; the 1 GB figure was a stale 2021 number) and **Hugging Face Spaces free CPU-basic 16 GB RAM** (https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app, https://huggingface.co/docs/hub/en/spaces-overview). Note: a **Render free web service is only 512 MB** — too small for any live met load.
- A *single* flight's CoCiP run loads ~1 GB of ERA5 meteorology (the "~1 GB" is cached disk size of the upfront request, not strictly peak RAM, but the working set is large) and competes with the xarray/dask/scipy footprint. The whole-globe chunk geometry means you cannot make the per-variable-hour fetch smaller than ~75–154 MB regardless of how small the flight box is.
- pycontrails' maintainers' own recommended pattern is **precompute + cache** (local NetCDF cache, `lowmem`/`preprocess_lowmem` mode that holds ≤2 timesteps in memory).

### Recommended architecture
1. **Offline batch job** (your machine, free Colab, or a GitHub Action): `pip install 'pycontrails[zarr]' netcdf4` on Python 3.11+. Pull met + rad via `ERA5ARCO` (pass `token='anon'` explicitly for robustness). Run CoCiP for the fixed leaderboard flight set + any pre-baked routes. Persist results as small static files (**Parquet** for the leaderboard table, **GeoJSON/Parquet** for contrail geometry) and commit them to the repo.
2. **OpenAP** runs in the same batch job (or even live — it's cheap) to produce the fuel/CO2 half.
3. **Deployed app** (Streamlit on Community Cloud, or **Hugging Face Spaces if any live-compute headroom is wanted**) only *loads and visualizes* the cached files. Keep ARCO/CoCiP entirely out of the request hot path.
4. **Optional "live single flight"** drill-down: treat as best-effort, scope to a couple of hours + a handful of pressure levels, cache aggressively, fall back to precomputed examples on failure. Host on HF Spaces (16 GB) if you attempt this at all.

The OpenSky fetch and OpenAP compute are both light and fit free hosting easily — **the only heavy stage is pycontrails+ERA5, and precompute removes it from the live app.**

---

## 4. Visualization Recommendation

**Primary: pydeck / deck.gl 3D flight-track visualization inside Streamlit**, with each track colored by combined CO2e warming, fronted by the ranked leaderboard.

**Rationale:**
- This is the genuinely **open lane** — competitors render 2D forecast heat-grids, avoidance polygons, or satellite masks; **none do a 3D per-flight track colored by full warming for consumers.** It directly serves the "two numbers, same flight" narrative.
- pydeck is the official open-source Python binding to deck.gl (OpenJS/vis.gl), free, no sign-up, and integrates natively into Streamlit (`st.pydeck_chart`) — keeping the whole stack in one free Python host.

**Free-hosting constraints:**
- Render only **precomputed** track + contrail geometry (GeoJSON/Parquet) — no live compute. This keeps the deployed app within the ~2.7 GB Streamlit ceiling.
- Keep the leaderboard small and the geometry decimated; a 3D `PathLayer`/`ColumnLayer` over a few dozen cached flights is light.
- CesiumJS is a credible alternative if a true globe is wanted, but it adds a JS/token integration burden and breaks the single-Python-host simplicity — recommend it only as a stretch goal.

---

## 5. Verified Science Numbers + Exact Caveats to Display

**Hard-codeable best estimates (Lee et al. 2021, 2018, ERF basis) — confirmed:**
- Net aviation ERF ≈ **100.9 mW/m²** (5–95%: 55–145).
- **Contrail cirrus ERF ≈ 57.4 mW/m² (range 17–98)** — the single largest term, **larger than CO2**.
- **CO2 ERF ≈ 34.3 mW/m²** (~34% of total).
- NOx net ERF ≈ 17.5 mW/m².
- **Non-CO2 effects ≈ 66% (~2/3) of total aviation ERF.**
- Sources: https://www.sciencedirect.com/science/article/pii/S1352231020305689, https://csl.noaa.gov/news/2020/287_0903.html

So "the CO2 number is only half the truth" is **defensible and arguably conservative** — CO2 is closer to a *third* of the warming. The central total-warming multiplier on an ERF basis is **~2.9x (≈3x), not ~2x**.

**Concentration stat (Teoh et al. 2024, ACP 24:6071) — confirmed verbatim:** *"Around 2.7% of all flights (or 11% of contrail-forming flights) accounted for 80% of the global annual EFcontrail in 2019."* This is **annual energy forcing (time-integrated, Joules), not instantaneous RF**, and the 2.7% is of **all** flights. (~24% of flights form persistent contrails; ~14% form a net-warming one.) This is the scientific basis for the leaderboard hook (https://acp.copernicus.org/articles/24/6071/2024/).

**Mitigation precedent (confirmed):** Google + American Airlines trials cut contrails 54% (2023) and 62% (2025) for ~2% extra fuel on deviated flights (~0.3% fleet-wide) (https://blog.google/technology/ai/ai-airlines-contrails-climate-change/).

### Mandatory on-screen caveats
1. **Never show a single contrail CO2e number without its metric + time horizon.** The conversion swings hugely: contrail warming is **~33–63% of aviation CO2 warming at GWP100, >100% (1.2–2.3x) at GWP20, ~10–20% at 500-yr** (RFF brief, Azar/Johansson/Pettersson/Sterner 2025 — note this is RFF/Teoh/Lee, **not** "Bickel"; https://www.rff.org/publications/issue-briefs/contrails-aviation-and-climate-change/). IPCC AR6 deliberately recommended **no** single metric. Implement a **metric/time-horizon toggle**, show a range, default to GWP100. Reassuringly, the binary "is this flight worth caring about" decision is robust (~90% agreement) across metrics even though the magnitude is not.
2. **The two numbers are not equally certain.** Contrail cirrus ERF carries ~70% uncertainty (IPCC "low confidence"); CO2 ERF is "high confidence." Show error bars on the contrail term.
3. **Apply the ERF/RF efficacy factor.** pycontrails/CoCiP outputs RF-style energy forcing; Lee's headline 57 mW/m² ERF derives from 111 mW/m² RF via an ERF/RF ratio of **~0.42** (Bickel et al. give ~0.35). Without this discount, contrail warming is overstated ~2x relative to ERF. **Do not mix RF and ERF.**
4. **Per-flight contrails are weather-dependent and probabilistic** — a given flight may form no warming contrail at all (night contrails warm; some day contrails cool). State that numbers are climatological estimates, not measured.
5. **Bizjet uncertainty (display prominently on the leaderboard).** Global CoCiP runs cap at **~13 km (≈ FL426, just under FL430)** and are calibrated on commercial ADS-B + IAGOS airliner humidity data. Business jets cruise **FL450–FL510**, partly *above* the modeled domain — contrails there are **excluded (terminated), i.e. likely under-counted, NOT extrapolated.** The 13 km cap and the explicit "small underestimation… by private jets" wording are the authors' own (https://acp.copernicus.org/articles/24/6071/2024/). Label bizjet figures "higher uncertainty, outside CoCiP's primary calibration altitude band."
6. **Occupancy caveat:** frame as "flights associated with this aircraft" — a tracked tail ≠ the owner was aboard (Swift's jet "is loaned out regularly"; Jay-Z "does not own").

---

## 6. Corrected-Claims List

Where adversarial verdicts refuted or qualified an original claim, the corrected version is below. **Use these, not the originals.**

1. **Free-host RAM is NOT ~1 GB.** Streamlit Community Cloud is up to **2.7 GB RAM / 2 CPU**; Hugging Face Spaces free is **16 GB RAM**; Render free is **512 MB**. Live single-flight CoCiP is workable on HF, tight on Streamlit, impossible on Render free.

2. **ARCO-ERA5 access** needs no CDS account and no GCP billing (only the ARCO path; the classic CDS path needs a free Copernicus account). Pass `token='anon'` explicitly — gcsfs auto-fallback fails if stale Google creds are present.

3. **Contrails.org API is "free-for-now," not unconditionally free/open.** It requires an approved application (email api@contrails.org), is licensed non-commercial-only, and BE reserves the right to charge. It is **not reserved for airlines/ANSPs** (any approved key holder qualifies). There is **no true real-time tier** (forecasts are forecast products; ADS-B is hourly historical). Do **not** rely on it as a free live source — run pycontrails yourself.

4. **OpenSky free tier does NOT cleanly cover a hosted leaderboard.** Data license is non-profit research/education/government only; *operational* (live product) use needs a prior written agreement; full-history aggregation requires academic-gated Trino. "Free, no account" is also outdated — OAuth2 is mandatory since ~March 2025. Get written permission, or scope as explicitly non-commercial and build from curated/cached flights.

5. **No tool fuses fuel-CO2 + contrail-CO2e into a per-owner ranking** — but each half ships separately (ATP-DEC combines both into one figure but doesn't rank; Sweeney ranks owners but CO2-only; Impact Explorer ranks flights by contrail CO2e but contrail-only/commercial). The moat is the *combination + private-jet framing*, not novelty of either piece. The Impact Explorer **does render** and should no longer be treated as "unverified."

6. **At least one private-jet contrail analysis already uses CoCiP:** the Victor/4AIR Oct-2025 annual report. It is a static, anonymized, once-yearly PDF — not an interactive per-owner tool — so the project's interactive niche stands, but "nobody applies CoCiP to private jets" is false.

7. **Google TIM is not "CO2-only."** Its CO2e folds in CO2/CH4/N2O via a CORSIA lifecycle factor (**not** a general GWP conversion of the full Kyoto basket); it excludes **contrails + short-lived pollutants** from CO2e, shown only as Low/Med/High buckets, with an explicit "do not convert to CO2e" warning.

8. **"Standard calculators omit non-CO2" is false as a blanket claim.** atmosfair and myclimate include non-CO2 via a flat x3 RFI. ICAO ICEC and TIM's *headline* number omit contrails. The accurate framing: incumbents use either nothing, a crude flat multiplier, or risk buckets — none use flight-specific physics.

9. **Owner attribution is NOT reliable enough to auto-"name names."** The crowdsourced OpenSky aircraft DB is astroturfed; FAA owners are often trusts/LLCs; FAA §803 (processing PII removals since 2025-04-24) is eroding the registry. Limit naming to high-confidence, corroborated, public-figure tails with explicit caveats.

10. **The total-warming multiplier is ~3x (ERF central), not ~2x;** non-CO2 is ~66% of ERF. The "1.2–4.7" span is **not one uncertainty band** — it mixes metrics (RFI ~1.9, GWP* rate, scenario-dependent ERF). Don't present it as a single range.

11. **ADS-B Exchange is not free** (min $10/mo via RapidAPI; enterprise = annual contracts; free flight-sim API discontinued 2025-03-01). Do not design around it. **OpenSky is the free path.**

12. **OpenAP is not "NumPy only"** (requires scipy, pandas, pyyaml, matplotlib too), ships **36** types not "~37", and its synonym table **does** include Bombardier Global Express (`gl5t`→glf6) — though it still lacks Challenger and Embraer Legacy/Praetor.

13. **OpenContrails (~1.25 TB GOES-16 imagery, CC-BY 4.0) is license-compatible but cannot be hosted/processed on free tier** and contains **no private-jet data**. Use it only as an optional validation/visual asset, subsampled; contrail physics comes from pycontrails/CoCiP, not this dataset.

---

## 7. Open Risks / Unknowns the Implementation Plan Must Hedge

1. **OpenSky operational-use licensing (highest non-technical risk).** A hosted public demo may breach the non-profit/operational terms. **Hedge:** obtain written permission from OpenSky, OR keep the deploy explicitly non-commercial/educational, ship a bundled cached sample dataset so the demo works without live calls, and attribute OpenSky. Use separately-public FAA registry data for any naming.

2. **Private-jet coverage + attribution may blunt the viral hook.** OpenSky honors some opt-outs (jets absent), the aircraft DB is astroturfed, owners hide behind LLCs/PIA, and bizjet types are thin in OpenAP. **Hedge:** build the leaderboard from a **curated, manually-verified ICAO24→owner→type list** of well-known jets; scope the demo to US/Europe; tag every proxy type and every owner label with a confidence flag.

3. **Bizjet contrail figures are extrapolations beyond the validated regime** (FL450–510 above CoCiP's 13 km cap; calibrated on commercial fleet). Numbers are plausible and likely *under*stated but carry elevated uncertainty. **Hedge:** prominent uncertainty labeling; consider raising CoCiP's `max_altitude_m` and flagging those results separately. This is the area most exposed to scientific-accuracy criticism in a case study.

4. **Live single-flight CoCiP feasibility on a chosen free host is unprofiled.** Peak RSS during CoCiP eval was inferred, not measured. **Hedge:** default to fully-precomputed; if attempting live drill-down, profile on the actual host first, prefer HF Spaces (16 GB), and always fall back to cached examples.

5. **CO2e single-number presentation is scientifically contested** (IPCC declined to pick a metric; TIM authors warn against the exact conversion the project performs). **Hedge:** never a single hard number — metric/time-horizon toggle, displayed range, prominent caveat, apply the ~0.42 ERF/RF efficacy factor. Frame the CO2e as an *illustrative, uncertainty-bounded scenario*.

6. **ERA5/ARCO has known upper-troposphere dry biases** that propagate into ISSR/contrail predictions, plus a ~2–3 month data lag. **Hedge:** disclose the bias; use historical (not last-few-weeks) flights for the demo.

7. **gcsfs anonymous fallback fragility** if the host carries stale Google credentials. **Hedge:** pass `token='anon'` explicitly rather than relying on the default chain.

8. **Deployed-host Python version is unconfirmed** (repo currently has no pinned runtime). pycontrails needs **≥3.11**. **Hedge:** pin Python 3.11–3.13 and verify `pip install 'pycontrails[zarr]' netcdf4 openap` installs from wheels (no eccodes/musllinux compile) on the chosen host before relying on it.

---

*Bottom line: the concept is buildable on free tools, the white space is real (fusion + private-jet leaderboard), and the science is defensible IF the contrail number is always shown with metric/horizon/uncertainty and the ERF/RF efficacy discount. The two binding constraints to design around are (1) precompute contrail results offline — never run CoCiP live in the deployed app — and (2) treat OpenSky licensing + owner attribution as the real project risks, not the physics.*