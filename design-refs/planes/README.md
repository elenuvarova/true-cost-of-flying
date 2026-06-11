# Plane ideas — prototypes (2026 design pass)

Local prototypes for the four plane ideas. **Not yet committed to the app build** — these are
for review. Static frames under-sell the motion; notes describe what moves.

| File | Idea | What it shows |
| --- | --- | --- |
| `00-before-hero-desktop.png` | — | Baseline hero (before), static SF-glyph plane parked at the trail end. |
| `A-ambient-fleet-hero.png` | **A · Ambient fleet** | Faint aircraft drift across the page background, each inking a thin contrail that fades. Subtle by design; motion carries it. Disabled under `prefers-reduced-motion`. |
| `B-hero-inflight.png` | **B · Hero comes alive** | The hero plane now *flies* the arc and inks the contrail in as it goes (mid-flight frame). |
| `B-hero-arrived.png` | **B · Hero comes alive** | …and parks at the destination, fully drawn — identical to the accepted look — then gently loops. |
| `C-bloom-trump-warm.png` | **C · Contrail bloom** | Trump 14 Feb 2025: a red warming-bloom glows exactly where the deep-night +90 t contrail formed. The rest of the track stays amber baseline. |
| `CD-bloom-musk-mixed-bizjet.png` | **C + D** | Musk "cuts both ways": a red warming bloom *and* a blue cooling bloom near SF; plane silhouette is now the business-jet shape. |
| `D-silhouettes-airliner-vs-bizjet.png` | **D · Real silhouette** | The two shapes at large scale. Airliner (757/767) vs business jet (Falcon 7X / G650) — the honest, visible class distinction. |
| `AB-hero-mobile-390.png` | **A + B** | Mobile (390 px): hero plane mid-flight + faint ambient plane; layout intact, no horizontal scroll. |

## HERO v2 — pinned scroll-scrub flight (awwwards pass)

D was dropped (user call). The hero was rebuilt: the section pins to the screen and **scroll flies the
plane** across the full viewport — "Scroll to fly" is now literal. On load the jet performs a short
autopilot take-off (inks the first ~22% of contrail), then the scroll position scrubs the rest. The
contrail spans the whole sky behind the headline (blue → amber → crimson, soft glow + bright core).
Phones get their own steeper climb path so the jet stays in the cropped frame.

| File | Moment |
| --- | --- |
| `HERO2-desktop-takeoff.png` | Load: autopilot take-off from bottom-left, blue tail, cue pulsing. |
| `HERO2-desktop-midflight.png` | Mid-scrub: trail sweeps the viewport, jet in the amber zone, cue faded. |
| `HERO2-desktop-arrival.png` | End: full blue→amber→crimson contrail behind the headline, jet exits top-right. |
| `HERO2-desktop-handoff-to-leaderboard.png` | The pin releases and the leaderboard takes over. |
| `HERO2-mobile-takeoff.png` | Mobile 390: jet takes off bottom-centre under the cue. |
| `HERO2-mobile-climb.png` | Mobile late-scrub: the climb crosses the headline — full-screen trail. |

## Notes / honest caveats

- **D** (dropped from the build, kept here for the record): at the ~28 px map icon, "757 vs 767" or "trijet vs twin" is imperceptible, so the split is
  **airliner vs business jet** — which also maps correctly to the real fleet (Trump/Drake fly converted
  airliners; Swift/Musk/Gates fly bizjets).
- **C**: bloom intensity/size is tunable; current values are demo-bright. It stays lit once the head passes
  (so the final frame marks every warming/cooling location), then resets with the loop.
- All four respect `prefers-reduced-motion` (A hidden; B/C park fully-drawn).
