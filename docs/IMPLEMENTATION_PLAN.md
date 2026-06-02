# True Cost of Flying — Implementation Plan

*Decision-ready build plan. Derived from `docs/RESEARCH_BRIEF.md` (ground truth; section 6 "Corrected-Claims List" overrides any contradicting statement). Dual goals, equal weight: (1) a strong PM case study, (2) defensible scientific accuracy. Virality secondary. Hard constraint: free tools/data, no paid APIs, free hosting. Audience: a PM building the prototype with AI assistance — concrete, conventional, buildable in steps.*

---

## What changed after review

This version fixes every blocker and major issue raised by the three reviewers (architecture, climate-science, PM-scope):

1. **Headline-vs-displayed-number mismatch (BLOCKER, science).** The "~3x / CO₂ is a third" figure is the **global fleet ERF share** (includes NOx, water vapor, aerosols). The app fuses **only fuel-CO₂ + contrail-CO₂e**, which at the GWP100 default is **~1.3–1.6x**, not ~3x. The plan now keeps these two numbers strictly separate: ~3x is a *context* stat about aviation as a whole; the per-flight reveal honestly says "contrails add ~30–60% on top of fuel-CO₂ at GWP100 (and swing toward 2–3x at GWP20)." We also now **explicitly disclose on-screen that the fused total omits NOx / water vapor / aerosols.**
2. **CoCiP output is Energy Forcing (EF, Joules), not RF (BLOCKER-adjacent, science).** Renamed throughout to `contrail_ef`. The ~0.42 ERF/RF ratio is now labeled a **global-mean efficacy scalar applied as a first-order approximation** to per-flight EF, and the **EF→CO₂e-mass bridge is specified explicitly** (use pycontrails' own helper; do not apply GWP to a raw Joule figure).
3. **0.42 efficacy is a range, not a clean constant (MAJOR, science).** 57/111 = 0.51, not 0.42; the literature spans **~0.35 (Bickel) to ~0.51 (Lee-implied)**. We default 0.42, expose it as a sensitivity parameter, and **fold its spread into the displayed uncertainty band** alongside the ~70% contrail uncertainty.
4. **Riskiest thing first (BLOCKER, PM).** Added **Phase 0.5 — physics spike**: run CoCiP on one hard-coded real flight (no OpenSky), validate the number against a published comparator, before any UI/plumbing. The novel risk is now retired in week one, not last.
5. **Cut scope (MAJOR, PM).** MVP metric toggle is now **GWP100 + GWP20 only** (GWP* and 500-yr → LATER; GWP* is a flow metric and must never drive a per-flight stock number). MVP flight count cut to **~10–12** (was 20–40). 3D extrusion/animation deferred; a flat colored path satisfies the aha.
6. **Leaderboard ranking is metric-unstable (MAJOR, PM).** Replaced the spurious 1..N ordinal with **tiers (high/medium/low total warming)** sorted at the GWP100 default, leaning on the brief's ~90% cross-metric agreement on the binary "does this matter" verdict.
7. **Validation is now a milestone (MAJOR, PM).** Added an explicit "validation & where we diverge" step comparing our output to Impact Explorer, the 33–63% GWP100 ratio, and the ~2.9x fleet ERF central.
8. **OpenSky `/tracks` ≠ `/states` (MAJOR, arch).** Corrected the credit budget (track geometry comes from `/tracks` at **4 credits/call**, separate 4,000/day bucket) and reconciled the **30-day `/tracks` window vs ~2–3-month ARCO lag** (use recent flights + ERA5T ~1-week-lag met).
9. **Streamlit RAM corrected (MAJOR, arch).** **~690 MB guaranteed, 2.7 GB best-effort max** (not a 2.7 GB floor). Live CoCiP on Streamlit is **infeasible**, not "tight." The read-only app fits the 690 MB guarantee comfortably.
10. **Reproducibility (MAJOR, arch).** Batch env is now **lockfile-pinned** (numpy-2 era, forced by openap ≥2.5.0); pinning is a Phase-2 done-criterion, not a "Low" risk row.
11. **Smaller fixes:** pydeck PathLayer data-shape footgun + per-segment color mechanism specified; what-if altitude noted as a full extra CoCiP run that may cross the 13 km cap; netcdf4 conditionality; ERA5 batch wall-clock / GB estimate + chunk-reuse strategy; Colab free-tier ceilings checked; git file-size budget; deployed-app deps pinned; ARCO Plan B; net-cooling flights handled; named user/JTBD added; committed-artifact licensing addressed; "13 km ≈ FL426, just under FL430" anchor restored; plan now *decides* hosting/cap/batch-host rather than punting them.

---

> **Note on existing repo state.** The current repo is an unrelated React + Express + Sequelize + Render template (top-level `README.md`, `backend/`, `frontend/`, `render.yaml`, `Dockerfile`). That stack is **discarded**: Render free is 512 MB (too small) and the app is read-only Python viz. We keep only the repo + `docs/`. Section 8 specifies the replacement tree.

---

## 1. Executive summary & positioning

**The product.** A web app that takes real, identifiable flights — privately-owned jets first — and shows, for the *same flight*, **two numbers side by side**:

1. **Fuel CO₂** — the only number every existing tracker shows.
2. **Combined CO₂e (fuel + contrail warming)** — fuel CO₂ **fused with flight-specific contrail warming**, computed with real CoCiP physics, presented with a metric/time-horizon toggle and an uncertainty band.

Fronted by a **tiered private-jet leaderboard** ("which tracked jets did the most total warming"), with a **pydeck/deck.gl flight track** colored by combined CO₂e.

**Who it's for (user / JTBD).** Primary: the climate-curious public, journalists and accountability advocates who want a credible, citable answer to "how bad was *that* flight, really?" Secondary (and honestly: the real audience for this artifact): a **hiring manager evaluating PM + technical judgment**. The job-to-be-done: *quickly grasp that the headline CO₂ number understates a named jet's warming, and trust the figure enough to cite or share it.* Every scope cut below is justified against that job.

**The wedge (confirmed white space, brief §1, §6.5).** No public tool does *both*: (a) fuse fuel-CO₂ + contrail warming into one combined CO₂e number, **and** (b) rank it per-aircraft/per-owner/per-tail — especially for private jets.

**Be honest — each half already ships separately (the moat is the fusion + framing + physics, not novelty of either piece):**
- ATP-DEC (Nature 2025) fuses CO₂ + non-CO₂ into one per-passenger figure — but no ranking, commercial-only.
- Sweeney's Celebrity Private Jet Tracker ranks owners — but CO₂-only (`fuel_used_kg * 3.15 / 907.185`, a flat per-type table).
- Contrails.org Impact Explorer **does** rank individual flights by contrail CO₂e (GWP100) — but contrail-only, by flight/route not owner, commercial not private. (Per §6.5 it renders; do not call it "unverified". **It is also our prime validation comparator** — see §9 / §13.)
- Victor/4AIR (Oct 2025) **already applies CoCiP to private jets** — but a static, anonymized, once-yearly PDF; CO₂ and contrails kept separate. So "nobody applies CoCiP to private jets" is **false** (§6.6); our interactive, per-owner, fused niche still stands.

**Why defensible / why now.**
- **The aviation context is mainstream and arguably conservative.** Across the global fleet, non-CO₂ effects are **~66% (~2/3)** of aviation ERF; contrail-cirrus ERF (~57.4 mW/m², range 17–98) is **larger than CO₂ ERF** (~34.3 mW/m²). The honest **fleet-aggregate** total-warming multiplier is **~2.9x (≈3x) on an ERF basis** (brief §5, §6.10). *This ~3x is a statement about aviation as a whole and includes NOx + water vapor + aerosols — it is NOT what a single flight in this app will display (see the framing rule in §6 and §11.0).*
- **The differentiator vs every tracker/calculator is flight-specific CoCiP physics**, not a flat RFI multiplier (atmosfair/myclimate x3), a fleet-average constant (Yard 2.7x), or risk buckets (Google TIM Low/Med/High). This is the genuine moat and directly serves the scientific-accuracy goal.
- **Concentration hook (Teoh et al. 2024, verbatim):** "~2.7% of all flights (or 11% of contrail-forming flights) accounted for 80% of the global annual EF_contrail in 2019." *This is time-integrated **annual energy forcing (Joules), not instantaneous RF**, and 2.7% is of **all** flights.* A leaderboard/tiering is the *right* shape for a power-law problem.
- **Mitigation precedent:** Google + American Airlines cut contrails 54% (2023) / 62% (2025) for ~2% extra fuel on deviated flights — the problem is *addressable*, which makes transparency actionable, not just doom.

**One-line positioning:** *"Every jet tracker shows you CO₂. Across aviation, CO₂ is barely a third of the warming. Here's the same flight with its contrail warming added — computed, not guessed."*

---

## 2. Product scope — ruthless MVP (the walking skeleton)

**The single user-facing "aha":** *same flight, two numbers.* A user clicks one tracked jet and sees Fuel CO₂ vs Combined CO₂e on one screen, with the track colored by the combined figure. Everything else is in service of that moment.

### IN / OUT / LATER

| Status | Item | Why |
|---|---|---|
| **IN (MVP)** | Curated, manually-verified set of **~10–12 flights** (3–5 hero public-figure jets shown in detail + 5–7 for tier shape, **including 2–3 commercial comparators for validation**) | Power-law + attribution risk + heavy offline cost mean a small *verified* set beats a large noisy one; 10–12 makes the tiering point and keeps batch iteration fast |
| **IN** | **Precomputed** fuel CO₂ (OpenAP) + contrail CO₂e (CoCiP) shipped as committed static Parquet/GeoJSON | The binding architecture constraint (§3) |
| **IN** | **Tiered leaderboard** (high/medium/low total warming) sorted at GWP100, with per-row confidence flags (proxy-type, owner-confidence, bizjet-altitude) | Framing moat + honesty; tiers avoid a spurious metric-dependent 1..N rank (§7) |
| **IN** | **Flight detail = the two numbers** + GWP100 default, **GWP100/GWP20 toggle**, **uncertainty band**, ERF/RF efficacy applied | The aha + the mandatory science presentation (§5/§6/§11) |
| **IN** | **pydeck `PathLayer`** of the track colored by combined CO₂e (flat/2.5D) | The open viz lane |
| **IN** | **On-screen caveats** (the full §11 list, incl. the "fused total omits NOx/H₂O/aerosols" disclosure) | Non-negotiable for the scientific-accuracy goal |
| **IN** | Bundled cached OpenSky-derived sample so the deployed app makes **zero live API calls** | OpenSky licensing hedge (§4) |
| **IN** | One **net-zero / near-zero contrail flight** in the set, shown as "not every flight is a contrail offender" | Honest teaching example; brief §5.4 |
| **OUT (MVP)** | Any live flight API in the deployed app | Tracks come from the committed adsb.lol static archive; zero live calls |
| **OUT** | Live CoCiP / ERA5 in the deployed app | Infeasible on free host (§3) — the hard rule |
| **OUT** | **GWP\* and 500-yr** in the toggle | GWP* is a flow/rate metric, **not** a per-flight stock number → would be scientifically wrong as a selectable CO₂e (§6, §11.1); 500-yr adds QA surface for marginal aha → LATER |
| **OUT** | NOx / water-vapor / aerosol non-CO₂ terms in the fused number | Out of scope for MVP; their absence is **disclosed on-screen** (§11.0). Adding them is the path to a legitimate per-flight ~3x (LATER) |
| **OUT** | Auto "name-and-shame" of arbitrary tails | Attribution astroturf/LLC/PIA risk (§6.9) — public-figure, corroborated only |
| **OUT** | 3D `ColumnLayer` altitude extrusion, camera/animation polish | Don't let viz fiddliness block the aha; a flat colored path is enough |
| **OUT** | Global coverage; oceans/Africa/E-Asia | Coverage gaps + power-law; scope to US/Europe |
| **OUT** | User accounts, search-any-flight, offsets/payments | Not needed for the aha |
| **LATER** | "What-if altitude" as **precomputed scenarios** (≤2 alts, 1–2 hero flights) | Each scenario is a **full extra CoCiP run** (§7) — powerful but not cheap |
| **LATER** | GWP\* (as an **annotation**, never a per-flight number) + 500-yr + adding NOx so the per-flight number can legitimately approach ~3x | Deepens the science story |
| **LATER** | Optional **live single-flight drill-down** on HF Spaces (16 GB), best-effort, falls back to cached | Profile first (§3, §12) |
| **LATER** | CesiumJS true-globe; time slider over a day/region | Adds JS/token burden; nice-to-have |

---

## 3. System architecture

**Two strictly separated halves. The deployed app never runs CoCiP or touches ERA5.** This is the single most important architectural rule (brief §3, §6.1).

```
┌─────────────────────────── OFFLINE BATCH (your machine / Colab / GitHub Action) ───────────────────────────┐
│                                                                                                             │
│  1. Track fetch        adsb.lol globe_history (free, no auth, unfiltered → bizjets not blocked)             │
│     (one-time/curated)  download day tarball → extract trace_full_<hex>.json.gz → lat/lon/alt_ft/time       │
│                         (no API, no OAuth2, no credit budget, any date 2023+; decimate + commit)            │
│                                                                                                             │
│  2. Aircraft join      icao24 → typecode (cached OpenSky aircraftDatabase.csv snapshot)                     │
│                        registration → owner/name (FAA Releasable DB, public-figure, corroborated)           │
│                                                                                                             │
│  3. OpenAP (light)     FuelFlow(ac).enroute(mass, tas, alt, vs) → kg/s → integrate → fuel_kg → ×3.16 = CO₂  │
│                                                                                                             │
│  4. pycontrails CoCiP   ERA5ARCO(token='anon') pull met+rad (ERA5T, ~1-wk lag) → Cocip(...lowmem)           │
│     (HEAVY — offline)    → per-flight ENERGY FORCING ef (Joules) → ×~0.42 efficacy → EF→CO₂e-mass bridge     │
│                          → CO₂e via GWP100 (+ GWP20 variant), low/central/high band                         │
│                                                                                                             │
│  5. Fuse + emit         combined CO₂e = fuel CO₂ + contrail CO₂e; attach band + confidence flags + tier     │
│                         → leaderboard.parquet  +  tracks/<icao24>_<flightid>.geojson (decimated)            │
│                                                                                                             │
└──────────────────────────────────────────────┬──────────────────────────────────────────────────────────┘
                                                │  git commit  (static files in repo, ~single-digit MB)
                                                ▼
┌──────────────────────── DEPLOYED APP (Streamlit Community Cloud, read-only) ───────────────────────────────┐
│  app.py:  load_parquet(leaderboard) → render tiered leaderboard → on select: load track →                   │
│           st.pydeck_chart(PathLayer colored by combined CO₂e) + two-number panel + GWP100/20 toggle + caveats│
│  NO pycontrails, NO ERA5, NO live OpenSky in the request path. Deps: streamlit, pandas, pydeck (pinned).     │
└─────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

**Where each free tool runs:**
- **adsb.lol `globe_history` download** — offline only (one-time curated fetch, decimated + committed). Not in deployed app; no API in the request path at all.
- **OpenAP** — offline (cheap enough to also run live, but no reason to in MVP).
- **pycontrails CoCiP + ERA5ARCO** — offline only. Never deployed.
- **pydeck/deck.gl + Streamlit** — deployed app, read-only.

**Why CoCiP must be offline (the receipts, brief §3):**
- A single flight's CoCiP run loads ~1 GB of ERA5 meteorology (cached-disk size of the upfront request; working set large) plus the xarray/dask/scipy footprint.
- **Spatial subsetting does NOT shrink the fetch** — the ARCO store is chunked **whole-globe per timestep** (`{time:1, level:37, lat:721, lon:1440}` ≈ **154 MB decompressed per pressure-level variable-hour**; model-level store ≈ 75 MB/chunk). A tiny flight box still pulls the global field. **Important corollary:** selecting *fewer pressure levels does not shrink the fetch* (you still pull whole-globe per level) — **only reducing the number of timesteps (hours) helps.**
- **Free-host ceilings (corrected, §6.1):** Streamlit Community Cloud guarantees **~690 MB RAM**, best-effort up to **2.7 GB**, **0.078–2 CPU** (the 2.7 GB is a *maximum*, not a floor; ~1 GB is the realistic working figure community threads still cite). HF Spaces free CPU-basic = **16 GB**. **Render free = 512 MB** (unusable for live met). → A single CoCiP run (~1 GB working set) does **not** fit the 690 MB Streamlit guarantee and is unreliable even against the 2.7 GB best-effort ceiling → **live CoCiP on Streamlit is effectively infeasible — do not attempt it there.** HF Spaces 16 GB is the only free host with headroom, and even there **profile peak RSS first.**
- pycontrails maintainers' own recommended pattern is **precompute + cache** (NetCDF disk cache, `lowmem`/`preprocess_lowmem` mode holding ≤2 timesteps).

**The deployed app stays trivially within the 690 MB guarantee** because it only `pd.read_parquet` + render decimated geometry.

### 3.4 Optional live single-flight drill-down (LATER, HF only)
If attempted at all: HF Spaces (16 GB), **profile peak RSS before relying on it.** Scope is bounded **only by reducing the number of timesteps (hours)** — not pressure levels (whole-globe-per-timestep chunking; see corollary above). Budget ≈ 154 MB/pressure-level-var-hour decompressed × ~9 variables × N hours, so a 2–3 hour flight ≈ a few GB working set → fits 16 GB with margin but must be measured. Cache aggressively; always fall back to a precomputed example on any failure.

---

## 4. Data layer

### 4.1 Flight tracks — adsb.lol `globe_history` static archive (PRIMARY; replaces the OpenSky API)

**Decision (revised after the data-source verification workflow):** the track source is a **committed static historical archive, not a live API.** Because the curated set is ~10–12 flights fetched ONCE offline and cached, a live API buys nothing — and a static archive **eliminates OAuth2, credit budgets, and the OpenSky `/tracks` ≤30-day cliff entirely.** ERA5 reanalysis covers any past date, so old flight dates are unproblematic (note: this is a property of the *met* data; the ADS-B archive itself only reaches ~2023).

**Source: adsb.lol `globe_history`** (`github.com/adsblol/globe_history_<year>` Releases) — daily tarball releases, 2023→present.
- **Fully free, no auth, no API key** (anonymous GitHub Releases).
- **Unfiltered** — adsb.lol does **not** honor FAA LADD / privacy opt-outs, so **private jets are NOT blocked** (a concrete advantage over OpenSky, which hid some celebrity tails).
- Per-aircraft historical tracks with **altitude**.

**How to pull ~10–12 specific jet flights (offline, once):**
1. Build the target list of jet **registrations → ICAO24 hex** (via the keyless live helper `api.adsb.lol/v2/reg/{reg}` or hexdb.io — a one-time lookup; no live calls ship in the demo).
2. Pick a flight **date in 2023–2026**; download that day's release tarball (~1.6–1.8 GB, sometimes split `.tar.aa`/`.tar.ab` → `cat … | tar -xf -`).
3. Extract only the target traces: `traces/<last-2-of-hex>/trace_full_<hex>.json.gz`.
4. Parse each trace point: `[secs_offset, lat, lon, altitude_ft|"ground"|null, gs, track, flags, vrate, …]` — **index 3 = barometric altitude in feet** (geometric altitude also available). Convert ft→m and knots→m/s for OpenAP; document in `fuel.py`.
5. **Decimate** (~30–60 s spacing) and commit.

**Coverage caveat (verify before committing):** adsb.lol coverage is **feeder-dependent** — strong US/Europe, sparse over oceans. A specific tail+day leg may have gaps. **Before committing a flight, confirm it has continuous cruise-altitude coverage.** Scope the demo to US/Europe.

**License — ODbL-1.0 (manageable, not a blocker).** The published adsb.lol database is **ODbL-1.0** (the CC0 file in the repo is the *inbound feeder* waiver, **not** a downstream escape hatch — adversarially confirmed). For a tiny committed decimated set the practical effect is light: **attribute "Flight data: adsb.lol, ODbL-1.0"** and treat the committed derived tracks as ODbL (attribution + share-alike). This is **cleaner than OpenSky's non-commercial/research terms** and removes OpenSky licensing from the critical path.

**Fallbacks (only if needed):**
- **`traffic` library MIT samples** — cleanest license (commit freely), ship offline in pip, but are **airliners/test flights, NOT business jets**. Use only if the demo can accept "any identifiable aircraft with a real cruise track" (good for the commercial comparators).
- **ADS-B Exchange free 1st-of-month samples** (`samples.adsbexchange.com`, back to 2016) — same trace format, but **dates must be the 1st of a month**, geometric altitude only 2022+, and **redistribution is restricted by JETNET ToU** (license-risky — prefer adsb.lol).
- **OpenSky REST API** — demoted to optional fallback only. If ever used: OAuth2 client-credentials (since ~Mar 2025), `/tracks` ≤30 days / 4 credits/call, non-commercial/research license; same zero-live-calls + attribution posture applies.

### 4.2 FAA Releasable Aircraft Database (tail → owner)
Public, downloadable. Use for **naming** (registration → registered owner) so naming does not depend on a crowdsourced owner field. Caveats baked into the pipeline: registered owners are frequently **trusts/LLCs** masking the beneficial owner; FAA §803 PII removals (since 2025-04-24) are eroding the registry (§6.9). → Naming is **best-effort, corroborated, public-figure-only**, with a confidence flag on every row.

### 4.3 Aircraft type mapping (icao24 → typecode → OpenAP type)
- **Join source:** OpenSky `aircraftDatabase.csv` (`typecode` field), downloadable **without an account**, updated irregularly (live file `last-modified 2024-11-04`; newest snapshot 2025-02 as of mid-2026). **Cache a snapshot** in the repo. Recently-registered jets will be missing.
- **OpenAP coverage is thin for bizjets (§2.69, §6.12):** ships **36** native types; only **two bizjets** — `GLF6` (Gulfstream G650), `C550` (Cessna Citation II). Default `_synonym.csv` covers some (Global Express `gl5t`→`glf6`, Learjet 45→`glf6`, PC-24/CJ→`c550`) but **lacks** Bombardier Challenger (`cl30/cl35/cl60`) and Embraer Legacy/Praetor.
- **Action:** maintain a project-owned `data/reference/type_map.csv` with explicit additional mappings (e.g. Challenger → nearest proxy), and **label every proxy-mapped type as an estimate** (`type_source = native | synonym | project_proxy`).
- **"type unknown → default proxy" path:** the pipeline must **never hard-fail** on an unknown type. Fall back to a documented default bizjet proxy (e.g. `glf6`), set `type_source = default_proxy`, surface "type unknown" on the row.

---

## 5. Contrail physics layer (offline batch)

**Install (confirmed clean from wheels, §2.55, manylinux Python 3.11–3.13):**
```
pip install 'pycontrails[zarr]' netcdf4 openap
```
No eccodes compilation (eccodes lives only in the unused `[ecmwf]`/`[dwd]`/`[gfs]` extras). **`netcdf4` is required only if you enable pycontrails' local NetCDF disk cache** (recommended, so re-runs do not re-pull ARCO); it is **not** needed merely to read the ARCO zarr store. We keep it because we cache.

**ERA5 access (the key free win, §2.52, §6.2):** ARCO-ERA5 needs **no Copernicus CDS account and no GCP billing** — public bucket `gs://gcp-public-data-arco-era5`, anonymously readable. **Pass `token='anon'` explicitly** to `ERA5ARCO`/gcsfs — the auto-fallback to anon **fails (RefreshError → 401) if stale Google creds are present** (§6.2, §7.7).
> **Plan B (single free-access linchpin — hedge it).** If Google ever changes the bucket's access terms or makes it requester-pays, fall back to the **classic Copernicus CDS path** (free account + queue) via `pycontrails`'s CDS interface. One-line note in `contrails.py`; do not build it now, but know it exists.

**Variables CoCiP needs (all present in ARCO, §2.54) — 9 total:**
- 6 pressure-level: `temperature`, `specific_humidity`, `u_component_of_wind`, `v_component_of_wind`, `vertical_velocity`, `specific_cloud_ice_water_content`.
- 2 top-of-atmosphere radiation (2D single-level, no vertical interp): `top_net_solar_radiation`, `top_net_thermal_radiation`.
- surface pressure.
- The model-level store gives fine ~10 hPa cruise-band resolution.

**The whole-globe-chunk reality (§2.58):** spatial subsetting does NOT shrink the fetch — `{time:1, level:37, lat:721, lon:1440}` ≈ 154 MB/var-hour (pressure-level) or ~75 MB (model-level). Official example warns "~1 GB" even for a tiny region. **Use `lowmem` / `preprocess_lowmem`** so CoCiP holds ≤2 timesteps in memory.

**Batch cost estimate + caching strategy (so the heaviest stage isn't a surprise):**
- Rough decompressed pull ≈ **154 MB × 9 vars × (hours per flight)**. A ~6–10 hour flight ≈ **~8–14 GB** decompressed working pull *before caching reuse*.
- **Curate flights that share dates/regions so they reuse the same downloaded met** — this is the single biggest cost lever. Cluster the ~10–12 flights onto a few common days; flights on the same day/region reuse the cached NetCDF, cutting total batch cost by a large factor.
- **Wall-clock:** expect the full ~10–12-flight batch to run in **roughly a few hours** end-to-end on a clip-along connection with caching, dominated by ARCO download, not compute.
- **Where it runs (decided — see §14):** **free Colab** for the ERA5 pulls. Colab free gives ~12 h sessions but can disconnect and has limited ephemeral disk — fine for a clustered, cached ~10–12-flight batch run in one or two sittings; mount Drive or commit intermediate caches so a disconnect doesn't restart the download. Local machine or a manually-dispatched GitHub Action are equivalent fallbacks.

**Data lag (§2.59, §7.6):** ARCO *final* lags ~2–3 months; **ERA5T lags ~1 week** and is what we use (see §4.1 reconciliation). ERA5 has known **upper-troposphere dry biases** that propagate into ISSR/contrail predictions. → Disclose the bias on-screen.

**Bizjet altitude cap (critical accuracy point, §5.5, §7.3):** global CoCiP runs cap at **~13 km (≈ FL426, just under FL430)**, calibrated on commercial ADS-B + IAGOS airliner humidity. Business jets cruise **FL450–FL510**, partly *above* the modeled domain — contrails there are **excluded/terminated, i.e. likely under-counted, NOT extrapolated** (authors' own wording: "small underestimation… by private jets"). **Decision (§14): keep the default ~13 km cap and flag affected rows prominently as under-counted** — raising `max_altitude_m` only pushes further outside calibration; revisit only if a reviewer specifically pushes. Use `max_altitude_m` **consistently** between baseline and any what-if scenarios.

**Output artifacts (committed to repo):**
- `data/processed/leaderboard.parquet` — one row per flight (see §6 schema).
- `data/processed/tracks/<icao24>_<flightid>.geojson` — **decimated** track + per-segment combined CO₂e for coloring.
- Optional `data/processed/scenarios/<flightid>_alt<FL>.geojson` — precomputed what-if-altitude variants (LATER).

---

## 6. CO₂e fusion & metrics module

### The framing rule (non-negotiable — fixes the headline/display mismatch)
There are **two different numbers** and they must never be conflated:
- **Context stat (aviation-wide):** "~3x / CO₂ is only ~⅓ of aviation's warming." This is the **global fleet ERF share** and includes **contrail cirrus + NOx + water vapor + aerosols**. Use it as background framing only.
- **Per-flight product number (what the app computes):** fuses **only fuel-CO₂ + contrail-CO₂e**. At the GWP100 default, contrail warming is **~33–63% of the flight's fuel-CO₂ warming**, so **combined ÷ fuel ≈ 1.3–1.6x**. At GWP20 it swings toward **~2–3x**. The detail screen says, honestly: *"Contrails add roughly 30–60% on top of fuel-CO₂ at GWP100 (and the gap widens to ~2–3x on a GWP20 basis)."*

**Never display ~1.5x under a "~3x" headline.** If a *legitimate* per-flight ~3x is wanted later, compute the other non-CO₂ terms too (NOx via OpenAP emission indices first) — that is a LATER item, and until then the app **discloses on-screen that the fused total omits NOx / water vapor / aerosols** (§11.0).

### Fuel CO₂ half (OpenAP, confirmed §2.65–66)
```
fuelflow = FuelFlow(ac)                       # ac = OpenAP type (native/synonym/proxy)
mdot = fuelflow.enroute(mass, tas, alt, vs)   # kg/s, vectorized over the track
fuel_kg = ∫ mdot dt                            # integrate over track timestamps
fuel_CO2_kg = fuel_kg * 3.16                   # EXACTLY 3160 g CO₂ / kg fuel (openap/emission.py v2.5.0)
```

### Contrail CO₂e half (CoCiP → EF → efficacy → EF→CO₂e bridge → GWP)
1. Run CoCiP → per-flight **Energy Forcing `ef` (Joules)** — pycontrails exposes the column as `ef`. **This is time-integrated radiative forcing over the contrail lifetime, NOT instantaneous RF (W/m²).** Name the variable `contrail_ef` everywhere.
2. **Apply the ERF/RF efficacy factor as a first-order scalar.** The ~**0.42** central is a **global-mean ERF/RF *radiative* ratio** (Lee's global mW/m² numbers; literature spans **~0.35 Bickel to ~0.51 Lee-implied** — note 57/111 ≈ 0.51, so 0.42 is a chosen central, not an exact derivation). Applying a global radiative scalar to a single flight's EF is an **acknowledged approximation** (a per-flight EF→ERF efficacy is not separately resolved). `contrail_ef_erf = contrail_ef * EFFICACY` with `EFFICACY = 0.42` default, **exposed as a sensitivity parameter**.
3. **EF→CO₂e-mass bridge (specify it; do not apply GWP to raw Joules).** Use **pycontrails' own EF-to-emissions / CO₂e helper** to convert energy forcing to an equivalent CO₂ mass at the chosen GWP horizon (the bridge is EF → equivalent sustained forcing → GWP-weighted CO₂ mass). The 0.42 efficacy and the GWP factor must be applied to *compatible* quantities — this step is exactly where the unit error the plan warns against would otherwise creep in.
4. **GWP horizon:** **GWP100 (default)** + **GWP20 (the contrast)**. (GWP\* and 500-yr → LATER; GWP\* is a flow metric and must never be a selectable per-flight CO₂e.) The contrail-vs-fuel-CO₂ ratio swings **~33–63% (GWP100)**, **>100% / 1.2–2.3x (GWP20)** — *carry the swing into the UI* (§11.1).
5. **Uncertainty band — two stacked sources:** (a) contrail-cirrus ERF carries **~70% uncertainty** (IPCC "low confidence"; the underlying ERF range is **17–98** mW/m² around the 57.4 central) and (b) the **efficacy spread ~0.35–0.51**. Fold **both** into `contrail_co2e_low / _central / _high`. CO₂ ERF is "high confidence" → no band on the fuel term. Show error bars on the contrail/combined term only.

### Fusion
```
combined_co2e_central = fuel_CO2_kg + contrail_co2e_central
combined_co2e_low     = fuel_CO2_kg + contrail_co2e_low
combined_co2e_high    = fuel_CO2_kg + contrail_co2e_high
```
A flight whose CoCiP `ef` is ~0 or net-cooling (some day contrails cool) yields `contrail_co2e ≈ 0` or slightly negative → `combined ≈ fuel`. **Display such a flight honestly** ("no significant warming contrail on this flight") and place it in the **low tier** as a teaching example.

### Constants (single source of truth in `src/constants.py`)
| Constant | Value | Source |
|---|---|---|
| `CO2_PER_KG_FUEL` | `3.16` (3160 g/kg) | openap/emission.py v2.5.0 (§2.65) |
| `EFFICACY` | `0.42` central; band `0.35–0.51` | Lee 2021 / Bickel (§5.3); applied to per-flight EF as a first-order scalar |
| `GWP100`, `GWP20` | per chosen metric set | RFF/Teoh/Lee 2025 (§5.1) |
| Contrail ERF | central `57.4`, range `17–98` mW/m² | Lee 2021 (§5) — basis for the ~70% band |
| Net aviation ERF (context only) | `100.9` (55–145) mW/m² | Lee 2021 (§5) — fleet context, not per-flight |

> **Headline framing constant (context, not per-flight):** fleet-aggregate total-warming multiplier ≈ **2.9x (≈3x) ERF central**, including NOx/H₂O/aerosols (§6.10). Do not present the "1.2–4.7" span as one uncertainty band — it mixes metrics (RFI ~1.9, GWP\* rate, scenario ERF).

### `leaderboard.parquet` schema (one row/flight)
`icao24, flight_id, owner_label, owner_confidence, registration, ac_type, openap_type, type_source, dep_time, route, fuel_kg, fuel_co2_kg, contrail_ef_joules, contrail_co2e_central, contrail_co2e_low, contrail_co2e_high, combined_co2e_central, combined_co2e_low, combined_co2e_high, metric (GWP100), horizon, tier (high|medium|low), bizjet_alt_flag, coverage_gap_flag, geometry_path`.
> **Git size budget:** decimate each track to **≤ ~500 vertices**; target the whole `data/processed/` tree at **< ~10 MB total** (well under GitHub's 50 MB warning / 100 MB hard limit per file). At 10–12 flights this is trivially met.

---

## 7. Visualization & UX

**Primary viz (the open lane, §4):** **pydeck `PathLayer`** inside Streamlit via `st.pydeck_chart`, the track **colored by combined CO₂e**. Flat/2.5D for the MVP; defer `ColumnLayer` extrusion and camera/animation polish (the aha does not depend on them).

**pydeck data-shape footguns (specify the shape — this is the one viz that *is* the aha):**
- `PathLayer.get_path` does **NOT** accept a raw GeoJSON LineString geometry — passing `get_path='geometry'` renders an **empty map with no error**. Feed records shaped as `{"path": [[lon,lat,alt], ...], "color": [r,g,b]}` (extract `geometry.coordinates` into an array of points).
- **Per-segment color** is not a vanilla `PathLayer` property (PathLayer colors per-path). Mechanism: emit **one short PathLayer record per decimated segment**, each with its own color — this matches the planned decimation and keeps it simple. (Alternative: `GeoJsonLayer` with per-feature properties.)
- **How combined CO₂e is distributed along the track for coloring:** CoCiP gives a per-flight EF total; we attribute color **per segment in proportion to that segment's energy-forcing contribution** (CoCiP produces a per-waypoint/segment EF that we carry into the GeoJSON), so the color genuinely reflects where warming happened — not a flat per-flight tint. Fuel-CO₂ is roughly uniform along the segment, contrail EF is concentrated where ISSR was crossed; the contrast is itself a teaching point.
- **Pin pydeck/streamlit** (§8) and **test `st.pydeck_chart` rendering on the actual Streamlit Cloud build**, not just locally — deck.gl version drift can silently break the one load-bearing viz.

**Screen flow (3 surfaces):**
1. **Tiered leaderboard (landing).** Grouped into **high / medium / low total-warming tiers** (sorted within tier by `combined_co2e_central` at GWP100). Each row: owner label, type, combined CO₂e (with band), and **visible confidence flags** (proxy-type chip, owner-confidence chip, bizjet-altitude chip). Tiers — not a precise 1..N rank — because the *magnitude* reshuffles with metric while the binary "does this matter" verdict is **~90% robust across metrics** (RFF/Azar-Johansson-Pettersson-Sterner 2025). This is the framing moat *and* the honesty surface.
2. **Flight detail (the aha).** **Two numbers, same flight:** Fuel CO₂ first (the familiar number), then Combined CO₂e → "**contrails add ~30–60% on top at GWP100**" (honest per-flight framing, **not** "~3x" — see §6). Includes:
   - **GWP100/GWP20 toggle.** When toggled, the combined number and band move — *that motion is the teaching moment* (magnitude is metric-dependent; the "does this matter" verdict is ~90% robust — say so, cited).
   - **Uncertainty band** on the contrail/combined number (error bars from §6.5).
   - The pydeck track colored by combined CO₂e.
   - The §11.0 disclosure that the total omits NOx/H₂O/aerosols.
3. **What-if altitude (LATER, precomputed).** A selector among **≤2 pre-baked** cruise-altitude scenarios on **1–2 hero flights**. **Each scenario is a full additional offline CoCiP run** (the heaviest stage × N) — scope it tightly. If a scenario altitude **exceeds ~13 km**, label it "outside CoCiP calibration" exactly like the baseline bizjet figures; if it **drops below ~13 km**, note the result becomes **in-domain and thus more comparable** — that contrast is the teaching point. UI states clearly: precomputed scenarios, not live recompute.

**The "reveal" copy:** lead with the familiar (fuel CO₂), then reveal the combined figure and the ~30–60% (GWP100) uplift, band + caveats visible at the moment of reveal, not buried.

---

## 8. Tech stack & repo structure

**Runtime:** Python **3.11–3.13** (pycontrails needs ≥3.11; §7.8). Pin it (`runtime.txt` / `.python-version`).

**Pinned deps — split by where they run, both lockfile-pinned.**

> **Reproducibility (was a "Low" risk, now a Phase-2 done-criterion).** **openap ≥2.5.0 hard-requires `numpy>=2.1` and `scipy>=1.14`**, so the *entire* batch stack (gcsfs, zarr, netcdf4, dask, geopandas, pyarrow) is **numpy-2-ABI-coupled**. pycontrails 0.63.x has no upper numpy bound, so they co-resolve on numpy 2.x today — but any future dep pinning `numpy<2` will silently conflict. **Ship a lockfile** (`pip-compile requirements-batch.in → requirements-batch.txt` with hashes, or `uv.lock`). The deployed-app deps are pinned too.

`requirements-batch.in` → compiled to `requirements-batch.txt` (offline only):
```
pycontrails[zarr]    # CoCiP, ERA5ARCO; outputs energy forcing
netcdf4              # local disk cache for ERA5 re-runs
openap               # >=2.5.0 → forces numpy>=2.1 / scipy>=1.14 (whole env is numpy-2)
gcsfs                # anonymous ARCO access (token='anon')
xarray
dask
pandas
geopandas
pyarrow
requests             # OpenSky OAuth2 + REST
```

`requirements.txt` (deployed app — pinned, kept tiny):
```
streamlit==<pin>
pydeck==<pin>
pandas==<pin>
pyarrow==<pin>
# geopandas only if reading GeoJSON via gpd; else drop for plain json
```

**Free hosting choice — DECIDED: Streamlit Community Cloud for the MVP (§14).** The deployed app is pure read-only Python viz with `st.pydeck_chart`; the ~690 MB guaranteed RAM is ample for loading a single-digit-MB Parquet + decimated geometry, it deploys straight from GitHub, single-Python-host simplicity. **HF Spaces (16 GB) only if** you later attempt the live single-flight drill-down (§3.4) — profile on the host first. **Never Render free (512 MB).**

**Repo tree (replaces the current React/Express template):**
```
.
├── docs/
│   ├── RESEARCH_BRIEF.md          # ground truth
│   └── IMPLEMENTATION_PLAN.md     # this file
├── app.py                         # deployed Streamlit app (read-only)
├── requirements.txt               # app deps only (pinned)
├── requirements-batch.in          # batch deps source
├── requirements-batch.txt         # batch deps LOCKED (pip-compile / hashes)
├── runtime.txt                    # python-3.11.x
├── .env.example                   # OPENSKY_CLIENT_ID / _SECRET (never commit real)
├── src/
│   ├── constants.py               # 3.16, 0.42 (+0.35–0.51 band), GWP100/20 — single source of truth
│   ├── tracks.py                  # adsb.lol globe_history download + trace_full parse (OFFLINE); ft→m
│   ├── aircraft.py                # icao24→type (cached csv) + FAA owner join + confidence flags
│   ├── fuel.py                    # OpenAP FuelFlow → fuel_kg → CO₂ (unit conversions documented)
│   ├── contrails.py               # ERA5ARCO(token='anon') + CoCiP(lowmem) → ef → ×0.42 → EF→CO₂e bridge
│   ├── fuse.py                    # combine halves, GWP100/20, stacked uncertainty band, tiers, schema
│   └── viz.py                     # pydeck PathLayer builders (per-segment records, not raw LineString)
├── batch/
│   └── build_dataset.py           # orchestrates opensky→aircraft→fuel→contrails→fuse→emit
├── data/
│   ├── raw/                       # cached OpenSky-derived sample, aircraftDatabase snapshot
│   ├── reference/ type_map.csv    # project proxy mappings + curated FAA-derived owner list
│   └── processed/                 # leaderboard.parquet + tracks/*.geojson  (COMMITTED, <~10 MB)
├── .github/workflows/
│   └── build_dataset.yml          # optional: manually-dispatched batch run
└── README.md                      # rewrite: non-commercial/educational + OpenSky attribution
```

---

## 9. Build milestones (each phase = a shippable increment; riskiest thing first)

**Phase 0.5 — Physics spike (DO THIS FIRST; retires the novel risk).**
- No UI, no OpenSky. Hard-code **one real flight track** (paste a lat/lon/alt/time series). Pull ERA5 via `ERA5ARCO(token='anon')`, run `Cocip(...lowmem)` → `ef`, apply `×0.42`, run the EF→CO₂e bridge → GWP100.
- **Done when:** the ARCO fetch completes on the actual batch host (Colab) in tolerable wall-clock, the lockfile installs cleanly on Python 3.11, **and** the resulting contrail CO₂e lands **within an order of magnitude of a published comparator** (Impact Explorer for a comparable commercial flight, and/or the ~33–63%-of-fuel-CO₂ GWP100 expectation). If it produces garbage, you learn it in week one.

**Phase 0 — Walking skeleton (the aha, faked physics, synthetic data).**
- Hard-code 1–2 flights with *placeholder* numbers and **fully synthetic/placeholder tracks (no OpenSky-derived positions)**. Build `app.py`: leaderboard → flight detail with **two numbers** + pydeck track + GWP100 label + caveat block.
- **Done when:** the app deploys to Streamlit Cloud, a viewer sees "same flight, two numbers" with a colored track, **and the first public deploy contains zero OpenSky-derived data** (real tracks appear only after §4.1 framing/attribution are in place).

**Phase 1 — Real fuel CO₂.**
- Implement `tracks.py` (download an adsb.lol `globe_history` day tarball, extract `trace_full_<hex>` for ~3–5 jets, parse lat/lon/alt, decimate; verify cruise coverage), `aircraft.py` (type join + proxy fallback + confidence flags), `fuel.py` (OpenAP integrate ×3.16).
- **Done when:** leaderboard shows *real* fuel CO₂ for ~3–5 verified jets; "type unknown → proxy" path never crashes; confidence flags render.

**Phase 2 — Real contrail physics (offline) + reproducibility + validation.**
- Productionize `contrails.py` (9 variables, `lowmem`, `ef`) and `fuse.py` (×0.42 band 0.35–0.51 → EF→CO₂e bridge → GWP100 + GWP20 + low/central/high). Run `batch/build_dataset.py` on the ~3–5 flights; commit `leaderboard.parquet` + track GeoJSON.
- **Done when:** combined CO₂e is real, banded, EF-correct (output labeled energy forcing, no RF/ERF mislabeling); **the locked `requirements-batch.txt` is verified to co-install on Python 3.11**; **each commercial comparator's combined/fuel ratio sits in the 33–63% GWP100 expectation** (validation), divergences noted; the app reads only committed files.

**Phase 3 — Full curated set + tiered leaderboard + flags.**
- Expand to **~10–12 flights** (US/Europe; 3–5 hero jets + 5–7 for tier shape incl. 2–3 commercial comparators **and one net-zero-contrail flight**). FAA owner join, bizjet-altitude flag, coverage-gap flag, tier assignment. **Cluster flights by date** to reuse cached ERA5. Decimate geometry (≤~500 vtx); per-segment color.
- **Done when:** the leaderboard renders in tiers, every row carries confidence/altitude flags, the net-zero flight displays honestly, all §11 caveats are on-screen.

**Phase 4 — Polished demo + metric toggle.**
- Wire the **GWP100/GWP20 toggle** to precomputed variants; the "reveal" UX (honest ~30–60% framing); instrument metrics (§10). (What-if-altitude scenarios are LATER — each is a full extra CoCiP run.)
- **Done when:** toggling GWP100↔GWP20 visibly moves the number+band; analytics events fire; `st.pydeck_chart` verified rendering on the live Streamlit build.

**Phase 5 (LATER, optional) — Live single-flight drill-down on HF Spaces.**
- Only if desired; **profile peak RSS on HF first**; scope by reducing *hours* (not levels); cache; fall back to cached examples on failure (§3.4, §7.4).

---

## 10. Metrics architecture (PM case)

**Be honest about context:** this is a zero-/low-traffic portfolio prototype with no accounts, so the *primary* success signal is **qualitative** — does a reviewer reach the two-number reveal, understand the framing, see the uncertainty, and **trust the figure because the validation section (§13) shows it agrees with a published comparator?** The quantitative tree below is presented as **"how I would instrument this at scale"** plus the few events that are genuinely measurable now.

**North-Star Metric (NSM):** **"reveal reached"** — flight-detail views per session (a *real page/DOM event*, instrumentable via a free analytics tier — not a session_state guess). Proxy for "people who saw that contrails add to the headline number."

**Input metrics (genuinely instrumentable via free analytics):**
- Leaderboard → flight-detail click-through.
- **GWP100/GWP20 toggle clicks per session** (engagement with the nuance) — a real event.
- Track interactions (rotate/zoom) — best-effort.

**Guardrail metrics (computed deterministically from the committed Parquet — always available, not a live event):**
- **% of leaderboard flights flagged low-confidence** (proxy-type OR owner-confidence OR bizjet-altitude), **shown in the UI footer** — a rising number is a data-quality signal to surface, not hide.
- % flights with `type_source = default_proxy` (extrapolation exposure).
- % flights with `coverage_gap_flag` (track-completeness risk).

**Instrumentation (free, real events):** a free privacy-light analytics tier (**Plausible free tier or GoatCounter**) for page-views and toggle-click DOM events. **Drop** the `st.session_state`/CSV-counter "caveat-view-rate" ideas — Streamlit reruns make them unreliable and statistically meaningless at this traffic. Guardrails come from the Parquet, deterministically.

---

## 11. Scientific-accuracy safeguards & mandatory on-screen caveats

Implement all as **always-visible UI**, not a hidden methodology page (from brief §5, plus the review fixes):

0. **The fused total is fuel-CO₂ + contrails ONLY.** It **omits NOx, water vapor, and aerosols** (~18 mW/m² of NOx plus others at the fleet level). State this on the detail screen: the app's "total warming" is "CO₂ + contrails," and the aviation-wide ~3x context number includes terms this flight figure does not. **This prevents the headline (~3x) from implying the per-flight number is more complete than it is.**
1. **Never a single contrail CO₂e number without metric + horizon.** Default **GWP100**, expose **GWP20**, **show a range**. State the **contrail-as-a-fraction-of-fuel-CO₂** numbers explicitly as a *ratio, not a share of total*: contrails add **~33–63% on top of fuel-CO₂ at GWP100**, **>100% (1.2–2.3x) at GWP20**. IPCC AR6 deliberately recommended **no single metric**. Reassure: the binary "is this flight worth caring about" verdict is **~90% robust across metrics** (RFF/Azar-Johansson-Pettersson-Sterner 2025) even though the magnitude is not.
2. **The two numbers are not equally certain.** Contrail-cirrus ERF ~**70% uncertainty** (IPCC "low confidence"; ERF range 17–98 around 57.4); CO₂ ERF "high confidence." Show **error bars on the contrail term only**, widened by the **efficacy spread 0.35–0.51** (§6.5).
3. **CoCiP outputs Energy Forcing (Joules), discounted to ERF by a ~0.42 global-mean efficacy.** Disclose that ~0.42 is a global-mean ERF/RF scalar applied as a first-order approximation to per-flight EF (range 0.35–0.51), and that **EF is converted to CO₂e via an explicit accounting bridge** — we do **not** apply GWP to a raw forcing. We do not mix RF and ERF.
4. **Per-flight contrails are weather-dependent and probabilistic.** A flight may form no warming contrail; night contrails warm, some day contrails cool. Numbers are **climatological estimates, not measurements**. (Our net-zero example flight illustrates this.)
5. **Bizjet figures = higher uncertainty (display prominently on the leaderboard).** Global CoCiP caps at **~13 km (≈ FL426, just under FL430)**; bizjets cruise **FL450–FL510**, partly above the modeled domain → contrails there **excluded/under-counted, NOT extrapolated**. Label: "higher uncertainty, outside CoCiP's primary calibration altitude band."
6. **Occupancy caveat.** Frame as "**flights associated with this aircraft**" — a tracked tail ≠ owner aboard (Swift's jet is loaned out; Jay-Z "does not own").
7. **ERA5 upper-troposphere dry bias + data lag** — demo uses historical/ERA5T flights; bias disclosed.

---

## 12. Risks & mitigations

| Risk | Severity | Mitigation |
|---|---|---|
| **Track-data licensing** (committing derived tracks publicly) | **Low–Medium** (resolved by source switch) | **Switched primary source to adsb.lol `globe_history` (ODbL-1.0)** — attribution + share-alike on the committed set, cleaner than OpenSky's non-commercial terms. Zero live calls; attribute "Flight data: adsb.lol, ODbL-1.0". OpenSky demoted to optional fallback. (§4.1) |
| **adsb.lol coverage gaps** (feeder-dependent; a chosen tail+day leg may be incomplete, esp. oceanic) | Medium | Verify continuous cruise coverage per flight **before committing**; scope to US/Europe; `coverage_gap_flag` per row (§4.1) |
| **Owner attribution fragility** (astroturfed OpenSky DB, trusts/LLCs, PIA rotation, opt-outs) | High (narrative) | Curated, manually-verified ICAO24→owner→type; **public-figure, corroborated only**; per-row owner-confidence flag; occupancy caveat; FAA registry as naming source (§4.2, §6.9) |
| **Headline ~3x vs displayed ~1.5x mismatch** | High (accuracy) | Strict separation: ~3x = aviation context (incl. NOx/H₂O/aerosols); per-flight = "+30–60% at GWP100"; on-screen disclosure the fused total omits NOx/H₂O/aerosols (§6, §11.0) |
| **EF-vs-RF mislabeling + EF→CO₂e unit error** | High (accuracy) | Label CoCiP output as Energy Forcing (Joules); 0.42 = global-mean efficacy applied as approximation; explicit EF→CO₂e bridge via pycontrails helper (§6) |
| **Bizjet contrail under-count** (FL450–510 above CoCiP's ~13 km / FL426 cap) | High (accuracy) | **Keep the cap**, flag rows likely *under*-counted (not extrapolated); consistent `max_altitude_m` baseline↔scenario; own it in the case study (§5, §7.3) |
| **Live-CoCiP infeasibility on free host** | Resolved by design | **Precompute offline, ship static files**; Streamlit guarantees only ~690 MB → live CoCiP **infeasible there**; live drill-down only LATER on HF after profiling (§3) |
| **Batch env reproducibility** (numpy-2-coupled stack, openap forces numpy≥2.1) | **Medium** | **Lockfile** (`pip-compile`/hashes or `uv.lock`); co-install verification is a Phase-2 done-criterion (§8) |
| **Heavy/slow ERA5 batch** (whole-globe chunks, Colab session limits) | Medium | Cluster flights by date to reuse cached met; Colab + Drive-mounted cache; ~few-hour wall-clock budgeted (§5) |
| **CO₂e single-number contestation** (IPCC declined a metric; TIM warns against this conversion) | Medium | Never a bare number — toggle, range, ~0.42 efficacy, prominent caveat; framed as illustrative, uncertainty-bounded (§5.1, §11) |
| **ARCO anon access regresses** | Medium | Pass `token='anon'`; documented Plan B = free Copernicus CDS path (§5) |
| **pydeck PathLayer silent-empty / version drift** | Medium | Feed `{path:[...], color:[...]}` records (not raw LineString); per-segment records for color; pin pydeck/streamlit; verify on live Streamlit build (§7) |
| **ERA5/ARCO dry bias + lag** | Medium | Historical/ERA5T flights; disclose bias (§7.6) |
| **gcsfs anon fallback fails on stale creds** | Low | Pass `token='anon'` explicitly (§6.2) |
| **Deployed wheel install / Python version** | Low | Pin 3.11–3.13; verify app deps install from wheels on the host (§7.8) |
| **OpenAP thin bizjet coverage / unknown type** | Low | `type_map.csv` proxies + no-fail default-proxy path; label non-native types (§4.3) |

---

## 13. PM case-study write-up structure (portfolio artifact)

Mirror the dual goal — a clean PM narrative that *also* demonstrates scientific honesty:

1. **Problem & user/JTBD.** Every jet tracker / most calculators show CO₂ only; across aviation CO₂ is ~⅓ of the warming. **Who:** climate-curious public + journalists/advocates wanting an accountability lens (secondary: the hiring manager). **Job:** grasp that the headline number understates a named jet's warming, and trust the figure enough to cite/share.
2. **Secondary demand / competitive white space.** The three non-overlapping clusters (B2B contrail science, jet trackers, CO₂ calculators) and the precise gap (fuse + per-owner tiering + flight-specific physics). **Be explicit that each half ships separately** — the moat is the combination + framing + physics. Cite ATP-DEC, Sweeney, Impact Explorer, Victor/4AIR, Google TIM honestly.
3. **Scope decisions.** The IN/OUT/LATER table and the *single aha*. Justify the two hard constraints designed around: (a) precompute contrails offline; (b) treat OpenSky licensing + attribution as the real risks, not the physics. Show what you cut (GWP*/500-yr, 20–40→10–12 flights, 3D extrusion) and why — ruthless MVP.
4. **Solution / demo.** The two-number reveal (honest ~30–60% GWP100 framing, not a fake ~3x), the tiered leaderboard, the colored pydeck track, the GWP100/20 toggle. Link the live Streamlit app.
5. **Validation & where we diverge.** The differentiating section: our combined/fuel ratio vs the **33–63% GWP100** expectation and vs **Impact Explorer** for comparable commercial flights; our implied fleet multiplier vs the **~2.9x** ERF central; explain divergences (bizjet cap under-count, ERA5 dry bias, single-flight efficacy approximation). This converts the biggest reviewer objection — "you replaced a flat 3x with a black box" — into a strength.
6. **Metrics.** The NSM tree (§10), honest about tiny traffic, and especially the *guardrail you chose to surface* (% low-confidence flights) — surfacing data-quality honestly is itself a product decision.
7. **Honest learnings & what's next.** Where the science is thin (bizjet altitude cap → under-counting; contrail ~70% uncertainty + efficacy spread; metric-dependence of magnitude; omitted NOx/H₂O/aerosols); next steps (add NOx for a legitimate per-flight ~3x; ISSR/SAC teaching layer; what-if-altitude scenarios; live drill-down on HF; broader verified jet set; written OpenSky permission). Knowing the limits is the strongest signal.

**Success bar for the artifact (distinct from per-phase done-criteria):** *a reviewer reaches the two-number reveal, understands that contrails add ~30–60% at GWP100 (and why the aviation-wide figure is ~3x), sees the uncertainty band, and trusts the number because the validation section shows it agrees with a published comparator.*

---

## 14. Decisions the plan made (override if you disagree)

These were previously "open" but are implementation/science calls the plan should own:
- **D1. Hosting = Streamlit Community Cloud** for the read-only MVP (HF only if you later attempt live drill-down). (§8)
- **D2. Bizjet altitude = keep CoCiP's ~13 km / FL426 cap**, flag affected rows as under-counted; do not raise `max_altitude_m` (it only pushes further outside calibration). Revisit only if a reviewer pushes. (§5)
- **D3. Batch host = free Colab** for the ERA5 pulls (Drive-mounted cache against disconnects); local / dispatched GitHub Action are equivalent fallbacks. (§5)
- **D4. Metric toggle = GWP100 (default) + GWP20 only** for the MVP; GWP\* (annotation-only) and 500-yr are LATER. (§6)
- **D5. MVP flight count = ~10–12**, clustered by date for met reuse. (§2, §5)
- **D6. Track source = adsb.lol `globe_history` static archive** (free, no auth, unfiltered bizjets, ODbL-1.0), NOT the OpenSky live API. This removes OAuth2, credit budgets, and the 30-day window. OpenSky/ADS-B Exchange/`traffic` are fallbacks. (§4.1)

## 14b. Open decisions for the user (genuine taste/judgment calls)

1. **Region & date window** for the curated set (recommend US/Europe; **any date in 2023–2026** works — the 30-day limit is gone now that we use the static archive; cluster flights onto a few common days to reuse cached ERA5 met). — *Any preference, or shall I pick recent US/EU dates?*
2. **Which jets/tails to seed** the leaderboard (public-figure, corroborated, US/Europe coverage, resolvable OpenAP/proxy type) — plus the **commercial comparators** for validation and the **one net-zero-contrail** teaching flight. This carries reputational/legal taste the builder shouldn't decide alone. — *Provide the shortlist.*

> **Decided, not open:** track source switched to adsb.lol (D6) → OpenSky written permission is **moot** (we're not using OpenSky data as primary). adsb.lol just needs ODbL attribution.
