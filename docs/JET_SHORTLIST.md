# True Cost of Flying — Curated Flight Shortlist

*Build input for the leaderboard. Owners are public figures with already-public jet attributions (we reuse public sources; we track aircraft, not people, using historical data with caveats). Tails/hex verified where marked ✅ (adversarial skeptic check); others are research-grade. Resolve any `unknown` hex and confirm continuous cruise coverage from the adsb.lol `globe_history` trace for the chosen date before committing (see IMPLEMENTATION_PLAN §4.1).*

## Leaderboard jets (11)

| # | Owner | Aircraft | Reg | ICAO24 hex | OpenAP type | type_source | Verified | Viral | Legal | Flags |
|---|-------|----------|-----|-----------|-------------|-------------|----------|-------|-------|-------|
| 1 | Elon Musk | Gulfstream G650ER | N628TS | a835af | GLF6 | native | ✅ keep | high | **high** | bizjet-alt |
| 2 | Mark Zuckerberg | Gulfstream G650ER | N68885 | a9247d | GLF6 | native | ✅ keep | high | medium | bizjet-alt |
| 3 | Drake ("Air Drake") | Boeing 767-200ER | N767CJ | aa5bc4 | B763 | native* | research | high | low | **lowest-uncertainty (airliner)** |
| 4 | Bill Gates | Gulfstream G650ER | N887WM | ac39d6 | GLF6 | native | research | high | low | bizjet-alt; "climate advocate flies private" |
| 5 | Kim Kardashian ("Kim Air") | Gulfstream G650ER | N1980K | a18845 | GLF6 | native | research | high | medium | bizjet-alt |
| 6 | Jeff Bezos | Gulfstream G650ER | N756LB | *resolve from trace* | GLF6 | native | ✅ keep_with_caveat | high | medium | bizjet-alt; attribution thinly-sourced |
| 7 | Eric Schmidt | Gulfstream G650ER | N652WE | a89621 | GLF6 | native | ✅ keep | medium | low | bizjet-alt; tops climatejets CO₂ rankings |
| 8 | Donald Trump | Boeing 757-200 | N757AF | aa3410 | B752 | native | ✅ keep | high | medium | airliner, high fuel burn |
| 9 | New England Patriots (R. Kraft) | Boeing 767-300ER | N36NE | a40b24 | B763 | native | research | medium | low | sports-team widebody 🏈 (2nd jet: N225NE / a1f4c5) |
| 10 | Kylie Jenner ("Kylie Air") | Bombardier Global 7500 | N810KJ | ab0a46 | glf6 | **proxy** ⚠️ | research | high | medium | proxy-type; famous 15-min hop (doubles as short-hop low-contrail example) |
| 11 | Taylor Swift | Dassault Falcon 7X | N621MM | a81b13 | glf6 | **proxy** ⚠️ | research | high | **high** 🚨 | proxy-type; prev N898TS Falcon 900LX (sold Feb 2024); C&D'd a jet tracker |

\* Drake's 767-200ER: map via OpenAP `b762`→`b763` native (widebody airliner → essentially native, lowest fuel-burn uncertainty in the set).

## Commercial validation comparators (NOT leaderboard — sanity-check vs Contrails.org Impact Explorer)

| Flight | Route | Aircraft | OpenAP type | Why |
|--------|-------|----------|-------------|-----|
| BA112 | JFK → LHR (evening dep, overnight eastbound) | Boeing 777-300ER | B77W native | Cleanest validation: night N-Atlantic crossing = classic warming-contrail regime |
| VS12 | BOS → LHR (overnight eastbound) | Boeing 787-9 | B789 native | Second independent anchor |
| UA16 (optional) | EWR → LHR | Boeing 767-300ER / 787-9 | B763 / B789 native | Third crossing if wanted |

*Reg + hex are date-dependent — pull the exact tail from the adsb.lol trace for the chosen date.*

## No-contrail teaching flight (honest "not every flight is an offender")

| Flight | Aircraft | OpenAP type | Why |
|--------|----------|-------------|-----|
| Widerøe short Norwegian hop (e.g. BGO↔BOO) | DHC Dash 8-Q400 | C550 proxy | Low cruise altitude → no persistent contrail forms. Primary teaching case. |
| (viral variant) Kylie #10's 15-min hop | Global 7500 | glf6 proxy | Same lesson, more shareable: too short/low to form a warming contrail. |

## Per-row flag meanings (carry into `leaderboard.parquet`)
- **bizjet-alt**: aircraft cruises FL450–510, above CoCiP's ~13 km cap → contrail likely **under-counted**, label "higher uncertainty, outside calibration band."
- **proxy ⚠️**: aircraft type not native/synonym in OpenAP → mapped to nearest proxy (`glf6`) → elevated **fuel-CO₂** uncertainty; label as estimate (`type_source = project_proxy`).
- **Legal high 🚨** (Swift, Musk): use only already-public attribution; historical (not live) data; aircraft-not-person framing; occupancy caveat ("flights associated with this aircraft").

## Open per-flight TODO before committing
1. Pick a specific **date in 2023–2026** per jet; confirm the adsb.lol `globe_history` trace has continuous cruise coverage (US/EU strong; oceanic legs may have gaps).
2. Resolve missing hex (Bezos) via `api.adsb.lol/v2/reg/{reg}` or hexdb (one-time).
3. Prefer dates where the flight crosses cold/humid airspace so the contrail story is non-trivial (transatlantic / northern-latitude legs).
