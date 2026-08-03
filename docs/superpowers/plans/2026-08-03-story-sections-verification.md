# Story Sections — Verification Record

Measured on 2026-08-03 against the built site (`npm run build` + `vite preview`),
branch `worktree-story-sections`. Numbers, not adjectives.

## Test suites

| Suite | Result |
| --- | --- |
| Vitest (frontend) | **72 passed**, 10 files |
| pytest (batch) | **24 passed** |
| `tsc --noEmit` | clean |

The repository had zero tests before this branch.

## Bundle

Budget: entry chunk ≤ 70 000 bytes gzip. Baseline before this work: **59 133 B**.

| Chunk | gzip B | On initial load? |
| --- | --- | --- |
| `index` (entry) | **65 679** | yes |
| `motion-features` | 31 158 | no — deferred by LazyMotion |
| `Explorer` | 4 167 | no |
| `FlightMap` | 2 415 | no |
| `OneSegment` | 1 805 | no |
| `HowWeKnow` | 1 711 | no |
| `DayOrNight` | 1 583 | no |
| `NightWidebodies` | 1 116 | no |
| `track` | 567 | no |
| `maplibre` / `deck` / `jet3d` | 216 729 / 185 904 / 155 884 | lazy (deck is modulepreloaded — see below) |

Entry grew 59 133 → **65 679 B** (+6 546) for six sections plus Motion. Within
budget with 4 321 B of headroom.

Two things were needed to get there, neither of which the plan anticipated:

1. The plan's `manualChunks: { motion: ['motion/react'] }` bundled `LazyMotion`
   and `domMax` into one chunk that `index.html` modulepreloads — defeating
   `LazyMotion` entirely and putting 50 KB on the critical path. Replaced with
   `src/lib/motion-features.ts`, a distinct module the dynamic import can
   actually split on.
2. The five sections below the ranking are now `React.lazy`. Eager, they put the
   entry at 72 759 B — over budget. This is what the spec's §7.5 ("new sections
   below the fold mount lazily") asked for.

**Pre-existing observation, not introduced here:** `index.html` modulepreloads
the 185 KB `deck` chunk, a side effect of `React.lazy(() => import('./FlightMap'))`.
It predates this branch. Worth a look, but out of scope.

## Data

| Item | Before | After |
| --- | --- | --- |
| `frontend/public/data/tracks` | 1.9 MB | **2.2 MB** (plan estimated 2.5–2.8 MB) |
| Non-zero segments preserved | 406 | **406** (3 dp lost one; raised to 6 dp) |
| `comparators.json` | absent | 5 flights, 4.7 KB |
| Raw traces matched for night split | — | **84 of 84**, 0 unmatched |

## Responsive

Full page walked so every lazy section mounts, then `scrollWidth` compared to
the viewport.

| Width | scrollWidth | Horizontal overflow |
| --- | --- | --- |
| 390 | 375 | **no** |
| 768 | 753 | **no** |
| 1440 | 1425 | **no** |

All six sections mount at every width.

## Reduced motion

Emulated `prefers-reduced-motion: reduce`:

- hero: `.hero-stage` 900 px, `.hero-pin` `position: relative` — un-pinned
- section 02: background settled at `rgb(4, 8, 15)`, the dark end — **not** stuck
  mid-transition
- section 03: `.oneseg-stage` height auto (732 px), `.oneseg-pin` `relative`,
  caption reads *"Segment 18 of 169 — this is the one"* — parked on the peak
  rather than an empty cursor at index 0
- all six sections mount

## Contrast (WCAG AA, 4.5:1 body / 3:1 large)

Section 02's background is scroll-linked, so every token was checked at **both**
ends of its range.

| Token | on lightest `rgb(17,35,58)` | on darkest `rgb(4,8,15)` |
| --- | --- | --- |
| `--muted` | 6.01 | 7.61 |
| `--ink-2` | 11.45 | 14.49 |
| `--ink` | 14.20 | 17.98 |
| `--cool` | 6.69 | 8.46 |
| `--warm` | **5.14** | 6.51 |

Worst case 5.14:1 against 4.5 required. **Pass.**

## Accessibility

- 35 focusable elements; every new control ≥ 40 px. The only sub-40 px hits are
  maplibre's CARTO/OpenStreetMap attribution links (third-party, licence-required,
  pre-existing) and an inline footer link (WCAG 2.5.8 exempts inline text links).
- Heading structure: one `h1` + six `h2`, in page order.
- Two `aria-live="polite"` regions; the ranking's updates on metric change
  (verified: keyboard `Enter` produced *"Ranked by Contrails only: 1. Donald
  Trump, 2. Eric Schmidt, …"*).
- Chart text equivalents present for all three charts: `seg-bars-alt`,
  `diverging-alt`, and `aria-valuetext` on the profile slider.
- Decorative SVGs carry `aria-hidden`/`role="presentation"`.
- Keyboard: profile scrubber responds to arrows (segment 24 → 29) and Home
  (→ segment 1); focus ring computes to 3 px solid.

## Framing rule

Every occurrence of "3×", "aviation-wide" and `contrail_pct_of_fuel` in
`src/components/` was read.

- All prose mentions are **disclaimers** that this is *not* the aviation-wide
  figure (Leaderboard note, HowWeKnow, Reveal).
- Section 05 shows per-flight contrail÷fuel ratios (max 82%), each with the
  test-locked caveat "not a per-flight multiplier and not the aviation-wide
  figure". Designed this way in spec §4.5.
- The extreme-ratio guard survives the Explorer restructure — verified live:
  Trump 14 Feb 2025 (contrails 239% of that flight's fuel) headlines
  **"+90.2 t contrails — contrail-dominated"**, tonnes not a percentage.
- The cool-side guard and permanence caveat survive: Musk reads "contrails
  cooled by 19.2 t" with the "CO₂ warms for centuries" note.

## Claims locked by tests

These would fail loudly rather than let the page state something untrue after a
data refresh:

- ranking reshuffles 5 of 11 at GWP100, 6 of 11 at GWP20; Schmidt 7→4 / 7→3
- 84 flights, 11 owners, night classification present
- Swift 2024-12-10: 169 segments, exactly 1 non-zero
- Trump 2025-02-14 recovers FL395–405
- 30 flights formed a contrail; median 8 live segments of ~156; top-5 median
  share 94–97%
- section 05's aggregate is computed from the rows, not hardcoded
