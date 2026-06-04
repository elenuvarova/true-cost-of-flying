"""Build-time export: precomputed parquet/geojson -> static JSON the React frontend fetches.

Run with the batch venv (has pandas/pyarrow):  .venv/bin/python scripts/export_web_data.py
(or .venv-app/bin/python). No network, no physics — pure reshaping of committed data.
Outputs into frontend/public/data/ so Vite serves them as static assets.
"""
import json
import os
import shutil

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROC = os.path.join(ROOT, "data", "processed")
OUT = os.path.join(ROOT, "frontend", "public", "data")
os.makedirs(os.path.join(OUT, "tracks"), exist_ok=True)


def _clean(df):
    df = df.copy()
    # ISO dates the browser can parse; derive a short YYYY-MM-DD from the flight_id tail.
    df["date"] = (df["flight_id"].str.split("_").str[-1]
                  .str.replace(r"(\d{4})(\d{2})(\d{2})", r"\1-\2-\3", regex=True))
    if "dep_time" in df.columns:
        df["dep_time"] = pd.to_datetime(df["dep_time"], errors="coerce").dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    # JSON-safe: NaN -> None
    return df.where(pd.notnull(df), None)


def export_parquet(name):
    p = os.path.join(PROC, name)
    if not os.path.exists(p):
        print(f"  skip {name} (absent)")
        return 0
    df = _clean(pd.read_parquet(p))
    out = os.path.join(OUT, name.replace(".parquet", ".json"))
    df.to_json(out, orient="records")
    return len(df)


n_lb = export_parquet("leaderboard.parquet")

# Per-flight track geojson, slimmed for the web: round coords to 5 dp (~1 m), drop the
# unused altitude (3rd element) and keep only `ef_share` (the only field the map reads), minified.
src_tracks = os.path.join(PROC, "tracks")
n_tracks = 0
if os.path.isdir(src_tracks):
    for f in os.listdir(src_tracks):
        if not f.endswith(".geojson"):
            continue
        gj = json.load(open(os.path.join(src_tracks, f)))
        for feat in gj.get("features", []):
            g = feat.get("geometry", {})
            if g.get("type") == "LineString":
                g["coordinates"] = [[round(p[0], 5), round(p[1], 5)] for p in g["coordinates"]]
            feat["geometry"] = g
            feat["properties"] = {"ef_share": (feat.get("properties") or {}).get("ef_share", 0.0)}
        json.dump(gj, open(os.path.join(OUT, "tracks", f), "w"), separators=(",", ":"))
        n_tracks += 1

# A tiny manifest so the frontend knows what's available without a directory listing.
with open(os.path.join(OUT, "manifest.json"), "w") as fh:
    json.dump({"leaderboard": n_lb, "tracks": n_tracks}, fh)

print(f"exported: leaderboard={n_lb} flights, tracks={n_tracks} geojson -> {OUT}")
