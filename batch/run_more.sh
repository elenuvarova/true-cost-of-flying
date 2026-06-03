#!/bin/zsh
# Orchestrate: for each NEW winter date, harvest owner tails (download->extract->delete
# tarball) then run the night-filtered CoCiP driver. Per-date interleave keeps disk
# bounded and checkpoints completed work (cache + harvest_more_log.csv) as we go.
set -u
cd "$(dirname "$0")/.."
PY=.venv/bin/python

DATES=(
  2024-12-15 2024-12-20 2024-12-07 2024-12-24 2024-12-28
  2025-01-09 2025-01-13 2025-01-18 2025-01-22 2025-01-26
  2025-02-02 2025-02-06 2025-02-10 2025-02-14 2025-02-18
)

for d in $DATES; do
  echo "########## HARVEST $d ##########"
  $PY batch/harvest_traces.py "$d" 2>&1
  echo "########## COCIP $d ##########"
  $PY batch/harvest_more.py "$d" 2>&1
done
echo "########## ALL DATES DONE ##########"
