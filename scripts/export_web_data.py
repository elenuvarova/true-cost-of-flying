"""Build-time export: precomputed parquet/geojson -> static JSON the React frontend fetches.

Run with the batch venv (has pandas/pyarrow):  .venv/bin/python scripts/export_web_data.py
(or .venv-app/bin/python). No network, no physics — pure reshaping of committed data.
Outputs into frontend/public/data/ so Vite serves them as static assets.
"""
import json
import os

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROC = os.path.join(ROOT, "data", "processed")
OUT = os.path.join(ROOT, "frontend", "public", "data")


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


def slim_feature(feat):
    """Reduce one track feature to what the web needs.

    Coordinates keep [lon, lat, alt_m] — lon/lat to 5 dp (~1 m), altitude to the
    nearest 10 m. Properties keep `ef_share` (the map's colour ramp) and `ef_tj`,
    the SIGNED energy forcing in terajoules — signed because the sign is the
    warming/cooling story, terajoules because raw joules are ~1e13 and bloat JSON.

    ef_tj keeps 6 dp (1 kJ). 3 dp would be plenty for anything visible, but it
    rounds the smallest real segment in the set (2.4e8 J) to zero, which would
    quietly change a non-zero segment count the story is built on.
    """
    g = feat.get("geometry") or {}
    if g.get("type") == "LineString":
        g = dict(g, coordinates=[
            [round(p[0], 5), round(p[1], 5), round(p[2], -1) if len(p) > 2 else 0.0]
            for p in g["coordinates"]
        ])
    props = feat.get("properties") or {}
    return {
        "type": feat.get("type", "Feature"),
        "geometry": g,
        "properties": {
            "ef_share": round(float(props.get("ef_share") or 0.0), 5),
            "ef_tj": round(float(props.get("ef") or 0.0) / 1e12, 6),
        },
    }


def export_tracks():
    src_tracks = os.path.join(PROC, "tracks")
    n = 0
    if not os.path.isdir(src_tracks):
        return 0
    for f in os.listdir(src_tracks):
        if not f.endswith(".geojson"):
            continue
        gj = json.load(open(os.path.join(src_tracks, f)))
        gj["features"] = [slim_feature(ft) for ft in gj.get("features", [])]
        json.dump(gj, open(os.path.join(OUT, "tracks", f), "w"), separators=(",", ":"))
        n += 1
    return n


def main():
    os.makedirs(os.path.join(OUT, "tracks"), exist_ok=True)
    n_lb = export_parquet("leaderboard.parquet")
    n_cmp = export_parquet("comparators.parquet")
    n_tracks = export_tracks()

    # A tiny manifest so the frontend knows what's available without a directory listing.
    with open(os.path.join(OUT, "manifest.json"), "w") as fh:
        json.dump({"leaderboard": n_lb, "tracks": n_tracks, "comparators": n_cmp}, fh)

    print(f"exported: leaderboard={n_lb} flights, comparators={n_cmp}, tracks={n_tracks} geojson -> {OUT}")


if __name__ == "__main__":
    main()
