"""Extract the comparator candidate traces from a day's combined.tar into
data/raw/traces/<hex>__<day>.json.gz (gzip), so build_comparators.py can process them.

Reads the hex list from data/reference/comparators.csv. Optional positional args restrict
to specific hexes (for the one-flight smoke test).

Usage:
  python batch/extract_comparators.py [hex ...]
"""
import csv
import gzip
import os
import sys
import tarfile

ROOT = os.path.join(os.path.dirname(__file__), "..")
RAW = os.path.join(ROOT, "data", "raw", "traces")
COMPARATORS_CSV = os.path.join(ROOT, "data", "reference", "comparators.csv")
os.makedirs(RAW, exist_ok=True)


def member_names(hexid):
    return {f"./traces/{hexid[-2:]}/trace_full_{hexid}.json",
            f"traces/{hexid[-2:]}/trace_full_{hexid}.json"}


def main():
    with open(COMPARATORS_CSV) as f:
        rows = list(csv.DictReader(f))
    want = {a.lower() for a in sys.argv[1:]}
    if want:
        rows = [r for r in rows if r["hex"].lower() in want]
    if not rows:
        print("no matching comparator rows")
        return
    # group by day -> tarball
    by_day = {}
    for r in rows:
        by_day.setdefault(r["day"], []).append(r)

    for day, drows in by_day.items():
        combined = f"/tmp/globe_dl/{day}/combined.tar"
        if not os.path.exists(combined):
            print(f"!! no combined.tar for {day} at {combined}; cannot extract")
            continue
        with tarfile.open(combined) as tf:
            names = set(tf.getnames())
            for r in drows:
                hexid = r["hex"].lower()
                mname = next((m for m in member_names(hexid) if m in names), None)
                if not mname:
                    print(f"  {hexid}: not found in {day} tarball")
                    continue
                raw = tf.extractfile(mname).read()
                out = os.path.join(RAW, f"{hexid}__{day}.json.gz")
                with open(out, "wb") as fo:
                    fo.write(raw if raw[:2] == b"\x1f\x8b" else gzip.compress(raw))
                print(f"  extracted {hexid} ({r['registration']} {r['type']}) -> {out}")


if __name__ == "__main__":
    main()
