# True Cost of Flying — product case study

*A PM + technical case study. Dual goal, equal weight: (1) a clear product narrative, (2) defensible climate science. Traces to `docs/RESEARCH_BRIEF.md` (science ground truth), `docs/IMPLEMENTATION_PLAN.md` (build plan), and `docs/VALIDATION.md` (the numbers). The live app is read-only; all physics is precomputed offline.*

---

## 1. Problem & user

Every flight tracker and carbon calculator shows one number: **fuel CO₂**. But across aviation, CO₂ is only about **a third** of the warming — the larger share is **non-CO₂ effects, dominated by contrails** (the white lines behind jets, which spread into heat-trapping cirrus). Contrail-cirrus ERF alone (~57 mW/m²) is *larger* than aviation's CO₂ ERF (~34 mW/m²). Yet **no consumer tool counts contrails per flight.**

**Primary user:** the climate-curious public, plus journalists and accountability advocates who want a credible, citable answer to *"how bad was that flight, really?"*
**Honest secondary user (the real audience for this artifact):** a hiring manager evaluating product + technical judgment.

**Job to be done:** *quickly grasp that the headline CO₂ number understates a named jet's warming — and trust the figure enough to cite or share it.* Every scope decision below is justified against that job.

---

## 2. Secondary demand & competitive white space

There are three non-overlapping clusters, and **each half of this product already ships separately** — the moat is the *combination + framing + flight-specific physics*, not novelty of either piece (stated honestly, per the brief):

| Who | What they do | What they don't |
|---|---|---|
| Contrails.org **Impact Explorer** | ranks individual *commercial* flights by contrail CO₂e | contrail-only; by flight/route not owner; forecast-window only |
| Sweeney **Celebrity Jet Tracker** | ranks *owners* | CO₂-only (flat per-type table) |
| **ATP-DEC** (Nature 2025) | fuses CO₂ + non-CO₂ into one figure | no ranking; commercial-only |
| **Victor / 4AIR** (2025) | applies CoCiP to private jets | static annual PDF; CO₂ & contrails kept separate |

**The gap:** nobody does *both* — (a) fuse fuel-CO₂ + flight-specific contrail CO₂e into one combined number, **and** (b) rank it per-owner, **for private jets**. That is the wedge.

**One-line positioning:** *"Every jet tracker shows you CO₂. Across aviation, CO₂ is barely a third of the warming. Here's the same flight with its contrail warming added — computed, not guessed."*

---

## 3. Scope decisions — the ruthless MVP

**The single aha:** *same flight, two numbers.* A user picks a tracked jet and sees Fuel CO₂ vs Combined CO₂e on one screen, with the track coloured by where the warming happened. Everything else serves that moment.

Two hard constraints shaped the architecture:
1. **CoCiP + ERA5 cannot run on a free host** (a single flight loads ~1 GB of whole-globe meteorology; Streamlit Cloud guarantees ~690 MB). → **Split the system in two:** a heavy *offline batch* precomputes everything into small static files; the *deployed app is read-only* (`pd.read_parquet` + render, zero physics, zero API keys). This is the binding decision the whole project rests on.
2. **Attribution + licensing are the real risks, not the physics.** → public-figure, corroborated tails only; aircraft-not-people framing; tracks from adsb.lol (ODbL-1.0, attributed), zero live calls.

**What I cut, and why (the discipline is the point):**

| Cut | Why |
|---|---|
| GWP* and 500-yr from the metric toggle | GWP* is a *flow/rate* metric — using it as a per-flight *stock* number would be scientifically wrong. Kept GWP100 + GWP20 only. |
| 20–40 flights → started at ~10–12 | A small *verified* set beats a large noisy one given attribution + power-law + heavy offline cost. (Grew to 84 flights / 11 owners once the batch was cheap, cached, and night-targeted.) |
| 3D extrusion / camera animation | The aha is the two numbers; a flat coloured path delivers it. Don't let viz fiddliness block the point. |
| A spurious 1..N rank | Magnitude reshuffles with the metric, so the leaderboard uses **tiers** (high/med/low) — leaning on the brief's finding that the binary "does this matter" verdict is ~90% robust across metrics even when the magnitude isn't. |
| NOx / H₂O / aerosols | Out of MVP scope; their absence is **disclosed on-screen** so the per-flight number is never implied to be the full ~3×. |

---

## 4. The solution

**A flyer-first explorer, one page.** The product is built around a single interaction — *pick a famous flyer, pick one of their flights, see the same flight as two numbers* — wrapped in three surfaces:
1. **Tiered leaderboard** — the 11 owners ranked by combined warming (fuel CO₂ + contrails), each row a magnitude bar with visible confidence chips (proxy-type, above-CoCiP-cap).
2. **The flyer explorer** — pick a flyer (the 5 headliners carry verified, adversarially fact-checked portraits; the other 6 show stats computed straight from the data), see their whole-fleet contrail portrait (fuel total, net contrail, a warmed/cooled/near-zero split), then pick one of *their* flights from a scoped list that defaults to their most telling one. This **merges the "celebrity hook" and the "reveal" into one coherent flow** instead of two disconnected surfaces — the structural fix that ties the product back to its job-to-be-done.
3. **The reveal + map** — for the chosen flight: Fuel CO₂ vs Combined CO₂e in oversized numerals, a proportion bar showing the red "contrail" slice no tracker counts, the **+X%** uplift (or absolute tonnes when contrails exceed fuel), a **GWP100/GWP20 toggle** whose motion *is* the teaching moment, an uncertainty band, and a track coloured per segment by where the warming actually occurred (red) vs none (grey) vs cooling (blue).

The honest framing is enforced everywhere: the combined number is **fuel-CO₂ + contrails only** (≈1.3–1.6× fuel at GWP100), never dressed up as the aviation-wide ~3× (which includes NOx/H₂O/aerosols). See `docs/IMPLEMENTATION_PLAN.md` §6 for the framing rule.

**Stack:** offline batch in Python (adsb.lol tracks → OpenAP fuel → ERA5/ARCO + pycontrails CoCiP → fuse + GWP + tiers) → committed Parquet/GeoJSON (<1 MB) → read-only Streamlit app on free hosting. No database, no paid APIs.

---

## 5. Validation & where we diverge (the differentiating section)

Replacing a flat ~3× multiplier with an opaque model invites the obvious objection: *"why trust it?"* So I checked it against published science — and the model **reproduces results it was never fit to** (full detail + reproducible code in `docs/VALIDATION.md`):

- **Formation incidence:** on the original random-winter sample, 32% of flights formed a persistent contrail / 16% net-warming — vs Teoh 2024's fleet ~24% / ~14%, the same order of magnitude. (After a deliberately night-enriched expansion to 84 flights it reads ~36% / ~21% — disclosed as an *upper* estimate, not an unbiased fleet match.)
- **The power-law:** a *single* track segment often carries ~all of a flight's energy forcing — Teoh's "2.7% of flights = 80% of forcing" at per-flight scale. (This is *why* the product ships tiers, not a precise rank.)
- **Day vs night controls the sign:** night contrails warm (100% of night waypoints in our data); many daytime contrails cool. Sharpest demonstration: **Drake's in-domain 767 flew the same Toronto↔Houston city-pair by day (net-cooled −10.3 t) and by night (warmed +1.6 t)** — opposite sign, identical route. And night transatlantic widebodies aggregate **+57% contrail/fuel** vs ~0% for daytime private jets — same pipeline, ~20× swing from regime alone (Stuber 2006, reproduced).
- **The headline a model couldn't fake:** a **Donald Trump 757 deep-night flight added +90 t of contrail warming (~2.4× its own fuel CO₂)** — on the *in-domain* airframe where the numbers are most trustworthy — while six of his other seven flights formed essentially none. Contrails are a concentrated wildcard, not a flat multiplier.
- **The EF→CO₂e conversion** matches Contrails.org's own published factor to **0.8%** (independently derived from IPCC AGWP100).

**Where we diverge, named and signed:** the daytime/in-domain aggregate sits *below* the fleet 33–63% band — because daytime cooling cancels night warming, the ~13 km business-jet altitude cap under-counts, and ERA5's upper-troposphere dry bias suppresses contrails. **Every systematic bias pushes the same direction — down — so the tool errs toward *under*-stating**, the conservative direction for an accountability claim. (We also surfaced an *unstable-ratio* trap — short low-fuel flights where contrail ≫ fuel yield absurd %s like +463%; the product headlines absolute tonnes there, not the ratio.) Knowing which way a soft number is wrong is the strongest thing you can say about it.

---

## 6. Metrics

Honest context: this is a zero-traffic portfolio prototype with no accounts, so the *primary* signal is **qualitative** — does a reviewer reach the two-number reveal, toggle the metric, see the band, and trust the figure because the validation section shows it agrees with published science?

- **North-Star (how I'd instrument at scale):** *"reveal reached"* — flight-detail views per session.
- **Input metrics:** leaderboard→detail click-through; GWP100/GWP20 toggle clicks (engagement with the nuance).
- **Guardrail (computed deterministically from the committed data, surfaced in-UI):** % of flights flagged low-confidence (proxy-type / above-cap). *Surfacing data-quality honestly is itself a product decision* — a rising number is a signal to show, not hide.

---

## 7. Honest learnings & what's next

**What the build taught me (the parts worth hiring for):**
- **The riskiest thing first.** A physics spike (one real flight, validated against a comparator) ran in week one — before any UI — so the novel risk was retired early, not discovered late.
- **The pipeline had a silent bug only adversarial data exposed.** Built for private jets, the type-resolver defaulted *unknown wide-bodies to a business-jet proxy* — fine until I ran commercial 777/A350 comparators and got absurd 800% ratios. Fixing it (wide-body proxies; re-running CoCiP, not just fuel) moved a contrail estimate 229→193 t — proof the *aircraft model*, not just the fuel, matters. Validation isn't a checkbox; it finds real defects.
- **Honest framing is a feature.** Keeping the per-flight number (~1.5×) strictly separate from the aviation-wide context number (~3×), and disclosing the omitted terms, is what makes it citable rather than dismissible.

**Where the science is thin (and disclosed):** business-jet altitude cap → under-counting; contrail ERF ~70% uncertainty + the efficacy spread; magnitude is metric-dependent (the verdict isn't); we omit NOx/H₂O/aerosols.

**What's next:** add NOx (via OpenAP emission indices) so a *legitimate* per-flight number can approach ~3×; fold the night-transatlantic commercial comparators into the main view; a live single-flight drill-down on a 16 GB host. The clearest dataset lever proved to be **time-of-day + route** (not season — winter already favours contrails): a night-pre-filtered harvest of busy-corridor flights is exactly what surfaced the Trump +90 t and Drake day/night results, and is the cheapest way to keep growing the verified set.

**The bar for this artifact:** *a reviewer reaches the two-number reveal, understands that contrails add ~30–60% at GWP100 (and why the aviation-wide figure is ~3×), sees the uncertainty, and trusts the number because the validation section shows it agrees with a published comparator.*
