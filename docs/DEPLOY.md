# Deploy & analytics

The deployed app is **read-only** (`pd.read_parquet` + render — no pycontrails, no ERA5, no API keys, no database), so it fits a free host comfortably and needs no secrets.

## Deploy to Streamlit Community Cloud (the decided host)

Everything in the repo is already deploy-ready:
- `app.py` — the entrypoint.
- `requirements.txt` — app-only deps, pinned (streamlit 1.58, pydeck 0.9.2, pandas, pyarrow, numpy 2.4). **Not** `requirements-batch.txt` (that heavy stack stays offline).
- `.streamlit/config.toml` — the dark brand theme (also makes the no-basemap map render predictably).
- `data/processed/{leaderboard.parquet, tracks/*.geojson, comparators.parquet}` — committed, <1 MB.

**The one manual step (needs your GitHub/Streamlit login — can't be scripted):**
1. Go to <https://share.streamlit.io> → sign in with GitHub.
2. **New app** → repository `elenuvarova/true-cost-of-flying`, branch `main`, main file `app.py`.
3. Under **Advanced settings**, set **Python 3.12** (Streamlit Cloud's picker; it doesn't always read `.python-version`).
4. **Deploy.** No secrets/env vars are required.

**After it's live, verify the one load-bearing thing:** open the deployed URL and confirm the **pydeck flight-track map renders** (deck.gl version drift across the Cloud build can silently blank it — test on the real build, not just locally). Then check the GWP100↔GWP20 toggle visibly moves the contrail number, and the reveal renders on a phone-width screen.

**Resource note:** Streamlit Community Cloud guarantees ~690 MB RAM; this app loads a ~20 KB Parquet + decimated GeoJSON, so it sits far under that. Cold starts (free tier sleeps after inactivity) take a few seconds — expected.

## Analytics — options and the honest Streamlit limitation

**What ships today (no account needed):** a **data-quality guardrail** in the app footer — `% of leaderboard flights carrying a low-confidence flag`, computed deterministically from the committed Parquet. Surfacing data quality is itself the product decision (plan §10); it needs no third party and can't be gamed by traffic.

**Page-view / event analytics (needs your account + a caveat):** the plan calls for a privacy-light tier (**Plausible free** or **GoatCounter**) for page-views and GWP-toggle clicks. The honest catch is that **vanilla Streamlit can't host a normal tracking snippet**:
- `st.markdown(..., unsafe_allow_html=True)` **strips `<script>`** — the snippet won't execute.
- `st.components.v1.html(...)` runs in a **sandboxed iframe**, so a pageview script there measures the iframe, not the parent page/URL.

So the realistic choices, in order of effort:
1. **Skip client analytics** and rely on the deterministic guardrail + qualitative review (right call for a zero-traffic portfolio piece — recommended).
2. **GoatCounter via `components.html`** for a coarse hit counter (accepts the iframe-referrer caveat) — **already wired in `app.py`**, gated behind a secret. To activate: create a free GoatCounter site, then in the Streamlit Cloud app's **Settings → Secrets** add `GOATCOUNTER_CODE = "yoursitecode"` (the `<code>` from `<code>.goatcounter.com`). With no secret set it's a no-op. Counts are approximate (iframe referrer).
3. **Custom domain + reverse proxy** (e.g. Cloudflare) that injects the Plausible script into the served HTML — the only way to get clean parent-page pageviews, but overkill here.

The hook is a no-op locally and on deploy until you set the secret, so it ships safely either way.

> Dropped on purpose (plan §10): `st.session_state` / CSV "caveat-view" counters — Streamlit reruns make them unreliable and meaningless at this traffic.
