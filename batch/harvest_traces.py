"""Harvest target aircraft traces from adsb.lol globe_history daily tarballs.

For each day: download the ~2 GB tarball (gh release download), extract ONLY the
registry hexes that flew that day, keep the good airborne flights, then delete the
tarball (disk stays bounded). Saved traces feed batch/build_dataset.py.

Usage: python batch/harvest_traces.py 2024-12-30 2024-12-27 ...
"""
import csv, glob, gzip, json, os, subprocess, sys, tarfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src.tracks import load_trace, longest_flight

ROOT = os.path.join(os.path.dirname(__file__), "..")
RAW = os.path.join(ROOT, "data", "raw", "traces")
OWNERS_CSV = os.path.join(ROOT, "data", "reference", "owners.csv")
os.makedirs(RAW, exist_ok=True)

with open(OWNERS_CSV) as f:
    OWNERS = {r["hex"].lower(): r["owner"] for r in csv.DictReader(f)}

DAYS = sys.argv[1:] or ["2024-12-30"]


def member_names(hexid):
    return {f"./traces/{hexid[-2:]}/trace_full_{hexid}.json",
            f"traces/{hexid[-2:]}/trace_full_{hexid}.json"}


def download_day(day, dldir):
    """Return path to a combined .tar for the day (download if needed)."""
    os.makedirs(dldir, exist_ok=True)
    # special-case the already-downloaded 2024-12-30 prod tarball
    pre = "/tmp/globe2024"
    if day == "2024-12-30" and os.path.exists(f"{pre}/d.tar.aa"):
        parts = sorted(glob.glob(f"{pre}/d.tar.a*"))
    else:
        year = day[:4]
        tag = f"v{day.replace('-', '.')}-planes-readsb-prod-0"
        repo = f"adsblol/globe_history_{year}"
        # Some days ship a single `*.tar`, others split into `*.tar.aa`/`*.tar.ab`.
        # `*.tar*` matches both shapes.
        if not glob.glob(f"{dldir}/*.tar*"):
            print(f"  downloading {tag} ...", flush=True)
            r = subprocess.run(["gh", "release", "download", tag, "-R", repo,
                                "-D", dldir, "-p", "*.tar*"],
                               capture_output=True, text=True)
            if r.returncode != 0:
                print(f"  !! download failed: {r.stderr.strip()[:160]}"); return None
        parts = sorted(glob.glob(f"{dldir}/*.tar*"))
    if not parts:
        return None
    combined = os.path.join(dldir, "combined.tar")
    if not os.path.exists(combined):
        with open(combined, "wb") as out:
            for p in parts:
                with open(p, "rb") as fp:
                    while chunk := fp.read(1 << 24):
                        out.write(chunk)
    return combined


def harvest_day(day):
    dldir = f"/tmp/globe_dl/{day}"
    combined = download_day(day, dldir)
    if not combined:
        print(f"  {day}: no tarball"); return []
    found = []
    with tarfile.open(combined) as tf:
        names = set(tf.getnames())
        for hexid, owner in OWNERS.items():
            mname = next((m for m in member_names(hexid) if m in names), None)
            if not mname:
                continue
            raw = tf.extractfile(mname).read()
            out = os.path.join(RAW, f"{hexid}__{day}.json.gz")
            # store gzip-compressed (the source bytes are already gzip)
            with open(out, "wb") as fo:
                fo.write(raw if raw[:2] == b"\x1f\x8b" else gzip.compress(raw))
            # quality check
            try:
                meta, df = load_trace(out)
                fl = longest_flight(df)
            except Exception as e:
                print(f"  {owner} {hexid}: parse err {e}"); os.remove(out); continue
            if fl is None:
                os.remove(out); print(f"  {owner} {hexid}: no real flight {day}"); continue
            dur = (fl.time.iloc[-1] - fl.time.iloc[0]).total_seconds() / 3600
            found.append((owner, hexid, day, len(fl), fl.altitude_m.max() / 0.3048, dur))
            print(f"  ✓ {owner:<24} {hexid} {day}  {len(fl)}pts FL{fl.altitude_m.max()/0.3048//100:.0f} {dur:.1f}h", flush=True)
    # free disk: drop the big tarball(s) (keep the pre-existing /tmp/globe2024 originals)
    for p in glob.glob(f"{dldir}/*"):
        os.remove(p)
    return found


def main():
    allf = []
    for day in DAYS:
        print(f"== {day} ==", flush=True)
        allf += harvest_day(day)
    owners_hit = sorted(set(o for o, *_ in allf))
    print(f"\n=== coverage: {len(owners_hit)}/{len(set(OWNERS.values()))} distinct owners, {len(allf)} flights ===")
    for o in owners_hit:
        print(f"  {o}")
    missing = sorted(set(OWNERS.values()) - set(owners_hit))
    if missing:
        print("MISSING:", ", ".join(missing))


if __name__ == "__main__":
    main()
