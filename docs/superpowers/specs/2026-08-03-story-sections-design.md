# Design — Story sections: turning the science into the page

**Date:** 2026-08-03
**Status:** approved, ready for planning
**Scope:** `frontend/`, `scripts/export_web_data.py`, one new offline batch script

---

## 1. Problem

The hero is award-grade. Everything after it is a competent dashboard, and the
site's strongest scientific findings are invisible — they exist only as prose in
[`docs/VALIDATION.md`](../../VALIDATION.md).

Three concrete gaps, each verified against the committed data on 2026-08-03:

**1.1 — No charts.** A data-journalism project with zero charts. The day/night
sign flip, the power-law concentration of contrail forcing, and the 20× swing
between night transatlantic widebodies and daytime bizjets are all computed,
committed, and unrendered.

**1.2 — The export throws away the data the charts need.**
`scripts/export_web_data.py:47-56` drops the third coordinate (altitude, metres)
and the signed per-segment `ef` (joules) from every track geojson, keeping only
`ef_share`. Both are present in `data/processed/tracks/*.geojson`.

**1.3 — The leaderboard is static.** Its single most persuasive property is
unused: switching the ranking metric reshuffles the ranking. That reshuffle *is*
the thesis of the project.

## 2. Verified data facts

Every number below was computed from committed data during design and must be
re-derived at build time, never hardcoded, except where noted as copy.

**2.1 Ranking reshuffle** — aggregating `leaderboard.parquet` by `owner_label`:

| Horizon | Owners whose rank changes | Largest moves |
| --- | --- | --- |
| GWP100, fuel → combined | 5 of 11 | Schmidt 7→4, Trump 3→2, Musk 5→7 |
| GWP20, fuel → combined | 6 of 11 | Schmidt 7→3, Musk 5→8, Drake 2→4 |

**2.2 Power-law concentration** — across the 30 flights with any non-zero EF:

- median flight: **8 non-zero segments out of 156**
- median top-5 segments carry **95.4%** of |EF|
- **6 flights have exactly one non-zero segment** carrying 100%
- best feature case: **Taylor Swift, `a81b13_20241210` — 1 non-zero segment of
  169, +12.1 t CO₂e.** Large enough to matter, extreme enough to be startling.
- Trump `aa3410_20250214` is the *magnitude* case, not the power-law case:
  14 non-zero of 158, top-1 = 14.1%, top-5 = 66.3%, +90.2 t, FL401.

**2.3 Day/night.** Two separate results, and they must not be conflated.

*Prior, waypoint-level* (`docs/VALIDATION.md` §6, 62 cached CoCiP runs): night
waypoints +2.6e14 J, 100% warming (136/136); day −9.6e13 J, 74% cooling. This
requires per-waypoint EF from inside the CoCiP run and **cannot be recomputed
from committed data** — quote it as a prior finding, do not redraw it.

*New, flight-level* — computed during design from `data/raw/traces/` by solar
elevation over cruise waypoints (≥20 000 ft), classifying each flight
night (≥70% night waypoints) / mixed / day (≤30%), then summing the flight-level
`contrail_ef_joules` already in `leaderboard.parquet`. **All 84 flights matched a
raw trace; none missing.** Counting only the 30 flights that formed a contrail:

| Class | Flights w/ contrail | Warmed | Cooled | Σ EF (J) | Σ CO₂e |
| --- | --- | --- | --- | --- | --- |
| Night | 10 | **10** | **0** | +5.65e14 | +160.7 t |
| Mixed | 5 | 4 | 1 | +1.13e14 | +32.2 t |
| Day | 15 | 4 | **11** | −1.91e14 | −54.4 t |

Section 02 is built on **this** table, because it is reproducible from committed
inputs. Day cooling comes out at 73% here against the prior's 74% at waypoint
level — an independent corroboration worth stating in the caption.

**2.4 Night transatlantic comparators** (`data/processed/comparators.parquet`,
5 flights, already committed, currently absent from the frontend):
contrail÷fuel = 53.6 / 57.8 / 76.5 / 82.3 / 5.7 %, aggregate **57.3% GWP100**,
against ~0% for the daytime private jets on the same pipeline.

**2.5 Availability.** 141 raw traces in `data/raw/traces/` and a working
`solar_elev()` in `batch/build_comparators.py:52`. A per-flight night split is a
pure offline recompute: no network, no ERA5, no physics.

## 3. Information architecture

```text
HERO                        unchanged
01  THE RANKING             + metric switch, cards reorder
02  DAY OR NIGHT            new
03  ONE SEGMENT             new
04  EXPLORE A FLYER         + altitude/EF profile under the map
05  THE NIGHT WIDEBODIES    new
06  HOW WE KNOW THIS        new
FOOTER                      unchanged
```

Sections 02, 03, 05 and 06 are new. The hero is not touched — it works, and
changing it risks the one thing that already lands.

## 4. Section designs

### 4.1 — 01 · The ranking (rebuild)

A segmented control above the existing bento grid: `Fuel CO₂` ·
`Combined CO₂e` · `Contrails only`. Reference pattern:
[Contra Labs](https://mobbin.com/sites/sections/02d9a4e4-1ba1-43d3-a178-de39ac3d5713).

Cards reorder with Motion's `layout` prop inside a `LayoutGroup`. The reorder is
the point, so it must be legible: ~500 ms, spring, staggered by rank.

Under the control, a live caption naming how many owners moved and the largest
mover, computed from the data, e.g. *"Switching to combined CO₂e moves 5 of 11 —
Eric Schmidt climbs from 7th to 4th."* This recomputes for GWP20, where it is 6
of 11.

**The GWP100/GWP20 toggle moves up into this section**, next to the metric
switch. It currently sits in Explore (section 04), which would put the control
*below* the caption that depends on it — the reshuffle is 5 of 11 at GWP100 and
6 of 11 at GWP20, and the reader needs the control in hand when they read that.
`horizon` already lives in `App.tsx:12` and is threaded down as a prop, so this
is a move, not a refactor. Explore keeps a second instance of the same control
bound to the same state, because the reveal there also depends on it; both
instances stay visually and behaviourally identical.

**Framing guard:** the `Contrails only` tab shows tonnes and a signed value. It
must not show a per-flight percentage of fuel — that invites the aviation-wide
~3× misread ruled out in `docs/IMPLEMENTATION_PLAN.md` §6.

### 4.2 — 02 · Day or night (new)

The single most important finding, and currently unrendered.

A diverging bar from a centre zero axis, built on the flight-level table in
§2.3: day to the left in `--cool`, night to the right in `--warm-deep`, labelled
with the summed CO₂e and the warmed/cooled counts. Beneath it, the headline
comparison — *"night: 10 of 10 warmed, none cooled"* against *"day: 11 of 15
cooled"* — and a line noting that the prior waypoint-level analysis found 74%
day cooling, so the two methods agree.

The section background is scroll-linked from the page's daylight blue to near
black across its own scroll range — the only place the day→night colour move is
used, because here it is literal physics rather than decoration. Implemented with
`useScroll({ target, offset: ['start end', 'end start'] })` + `useTransform` on
`backgroundColor`.

Requires a new flight-level `is_night` / `night_pct` field (§5.2).

**Honesty note required in the caption:** the night flights in this dataset were
deliberately harvested (`batch/harvest_more.py`), so night incidence here is an
upper estimate and not an unbiased sample. This disclosure already exists in the
old validation expander and must survive.

### 4.3 — 03 · One segment (new)

Full-bleed bar chart of one flight's per-segment |EF|, most bars at zero, the
one that matters annotated. Reference pattern:
[Sunday](https://mobbin.com/sites/sections/f27977b8-0ee9-46bf-9848-be937411d990).

Hero example: **Taylor Swift `a81b13_20241210`, 1 non-zero segment of 169**.
Copy states the general result too — median 8 non-zero of 156, top-5 = 95.4% —
so the reader understands this is the rule, not a cherry-picked flight.

A sticky map sits above the chart showing the same flight's track. Scroll
progress through the section drives a single `activeSegment` index from 0 to
n-1; that index highlights simultaneously in the bar chart and on the track, so
the bar and the geography are the same object seen twice. Scrolling therefore
walks the reader along the flight, and the moment where the one live segment
lights up is the payoff.

Requires signed per-segment `ef` in the exported geojson (§5.1).

### 4.4 — 04 · Explore a flyer (extend)

Keep the pill → flyer card → flight chips → two-number reveal → map chain
exactly as it is. Add, under the map, a profile chart with two tabs:
`Altitude (FL)` and `Contrail EF`. Reference pattern: Chargetrip's
Elevation/Consumption panel (Refero `a0968ebc-e16f-4e24-860c-d7b62a0176a5`).

The profile has a scrubber. Dragging it moves the plane icon along the deck.gl
track; hovering a map segment moves the scrubber. One shared `activeSegment`
index in `Explorer.tsx` state drives both — the map and the chart are two views
of one cursor, never two independent widgets.

Requires altitude in the exported geojson (§5.1).

### 4.5 — 05 · The night widebodies (new)

The 20× comparison, using data already committed but never shipped to the web.

Reference pattern:
[Superpower](https://mobbin.com/sites/sections/fd1d68ec-2da8-4764-aac6-0393692ac0ee)
— a scroll-linked list of the 5 flights on one side, the active one's track on
the other. Each row: registration, type, fuel CO₂, contrail CO₂e, ratio.

The closing line contrasts the 57.3% aggregate against ~0% for the daytime
private jets on the same pipeline, and names the reason: regime (night + ISSR
crossing), not aircraft.

**Framing guard:** 57.3% is a contrail÷fuel ratio for these specific flights. It
is not a per-flight multiplier and not the aviation-wide figure. Caption says so.

### 4.6 — 06 · How we know this (new)

Replaces nothing; the honesty content currently lives only in the footer.

- reproduction of Teoh 2024 fleet stats (32% vs ~24% form a contrail;
  16% vs ~14% net-warming)
- the EF→CO₂e bridge agreeing with Contrails.org's published factor to 0.8%
- the ±70% uncertainty band, drawn as a shaded reference band behind the
  headline number rather than described in prose (the "Reference Area" idea from
  [bklit](https://bklit.com))
- the night-selection bias disclosure
- what is *not* counted: NOx, water vapour, aerosols — and therefore why this is
  not the aviation-wide ~3× figure

## 5. Data changes

### 5.1 — Re-export what the tracks already contain

`scripts/export_web_data.py` currently rounds coordinates to 5 dp, drops the
altitude, and keeps only `ef_share`. Change to:

- keep the altitude as the third coordinate, rounded to the nearest 10 m
- keep the signed `ef`, in units of 1e12 J rounded to 3 dp, to stay compact
- keep `ef_share`

Estimated size: tracks grow from 1.9 MB to roughly 2.6 MB total. Tracks are
already fetched one flight at a time on demand, so nothing enters the critical
path. Verify the real figure after the change rather than trusting this estimate.

### 5.2 — New offline script: per-flight night split

`batch/add_night_split.py` — reads `data/raw/traces/*.json.gz`, applies the
existing `solar_elev()` (lifted into `src/solar.py` so the four copies collapse
to one), and writes **`night_pct_of_waypoints`** and a derived
**`night_class` ∈ {night, mixed, day}** into
`data/processed/leaderboard.parquet`.

It does **not** write `night_ef_joules` / `day_ef_joules`. Those need
per-waypoint EF from inside the CoCiP run, which is not in any committed file;
`comparators.parquet` has them only because `build_comparators.py` computed them
during its own physics run. Section 02 uses the flight-level split instead
(§2.3), which needs nothing but the raw trace and the signed
`contrail_ef_joules` already on the board.

Waypoints are filtered to cruise (≥20 000 ft) before the solar-elevation test,
so taxi and climb do not dilute the classification. Thresholds: night ≥70% of
cruise waypoints below −6° solar elevation, day ≤30%, mixed in between.

Pure reshaping: no network, no ERA5, no pycontrails. This respects the
project's first rule — heavy physics stays offline, the deployed app only reads.

All 84 flights currently match a raw trace. If one ever does not, the fields are
null and section 02 excludes it from counts rather than assuming a value.

### 5.3 — Export the comparators

`export_parquet("comparators.parquet")` was removed as dead code. Restore it;
section 05 needs it.

## 6. Technical decisions

**Add `motion`, nothing else.** Import from `motion/react` — never
`framer-motion`. Loaded as a lazy chunk alongside deck.gl so the critical path
stays at its current 59 KB gzip. Used for: `layout` reordering (4.1),
`useScroll`/`useTransform` (4.2, 4.3), `whileInView` reveals. Motion runs
scroll-linked animations on the native `ScrollTimeline` where available.

**Rejected dependencies, with reasons:**

- *KokonutUI* — Tailwind + shadcn. This codebase is hand-written CSS with a
  token layer in `src/styles.css`. Adopting it means adopting Tailwind. Not
  worth it for a handful of components. Useful as an idea source only.
- *bklit / any chart library* — the four charts here are narrow and bespoke
  (diverging bar, sparse bar, altitude profile, uncertainty band). Hand-written
  SVG is around a hundred lines each and inherits the palette for free. A chart
  library would be larger and would have to be fought into the design system.
  Kept as a reference for chart *types* (Reference Area, Projection Line).
- *anime.js v4* — genuinely good (24.5 KB modular, `svg.createDrawable`,
  `morphTo`, `createMotionPath`), but the contrail draw is already done in CSS
  `stroke-dashoffset` and works. No second animation engine.

**Charts are inline SVG components** under `src/components/charts/`, one file
each, reading tokens from `src/lib/colors.ts`. Keep `colors.ts` and the CSS
custom properties in sync — they already drift-check by convention.

## 7. Non-negotiables

These are pre-existing project rules that this work must not break.

1. **Framing rule.** No new surface shows a per-flight ~3×. Contrail-dominated
   flights headline absolute tonnes, not a percentage.
2. **Offline/online split.** Nothing in `frontend/` computes physics. All new
   fields come from the batch layer as static JSON.
3. **`prefers-reduced-motion`.** Every new scroll-linked effect degrades to a
   static, fully readable state — including the day→night background, which must
   settle at a legible contrast rather than mid-transition.
4. **Accessibility.** Charts get a text equivalent — a visually-hidden summary
   sentence or a small data table. The reordering leaderboard announces its new
   order through the existing `sr-only` live region. Touch targets stay ≥44 px.
5. **Performance.** Critical-path JS stays under about 70 KB gzip. New sections
   below the fold mount lazily.
6. **Honesty captions survive.** The night-selection bias, the ±70% band, and
   the "not the aviation-wide 3×" disclaimer each appear on the surface that
   could mislead without them.

## 8. Verification

- `npm run typecheck` clean.
- Ranking reshuffle asserted against the data, both horizons, rather than
  eyeballed: the caption's numbers must match a recomputation.
- Charts checked at 390 / 768 / 1440 with Playwright, no horizontal overflow.
- `prefers-reduced-motion: reduce` pass — every section readable, nothing stuck
  mid-scroll-transition.
- Contrast check on the day→night background at both ends of its range and at
  the midpoint, where text is most at risk.
- Bundle size measured before and after; the number goes in the PR, not an
  estimate.

## 9. Sequencing

Six sections is a lot for one plan, so the order matters: each step should leave
the site shippable, and the data work has to land before the sections that read
it.

1. **Data first** — §5.1 re-export, §5.2 night split, §5.3 comparators. Nothing
   visible changes; the frontend keeps working off the same fields it already
   reads. Verify sizes here.
2. **01 · The ranking** — highest payoff per unit of work, no new data needed,
   and it moves the horizon toggle, which everything downstream reads.
3. **03 · One segment** and **04 · profile** — both consume §5.1's re-export and
   share the `activeSegment` cursor idea, so they are cheaper built together.
4. **02 · Day or night** — consumes §5.2.
5. **05 · The night widebodies** — consumes §5.3.
6. **06 · How we know this** — last, because it summarises what the other
   sections claim and should be written against what actually shipped.

## 10. Out of scope

Deliberately excluded to keep this a single implementable plan:

- deck.gl cinematic camera choreography (banking over the ISSR segment)
- a full page-wide art-direction change
- NOx, water vapour or aerosol terms — that is a science change, not a design one
- folding the comparators into the main leaderboard; they stay a separate,
  clearly-labelled section
