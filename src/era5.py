"""Robust ERA5ARCO loading.

gcsfs has no default request timeout, so a single hung chunk read can block the
whole pipeline forever (observed: 19-min stalls with 0% CPU). We (1) set a gcsfs
timeout via fsspec config so a stuck read RAISES instead of hanging, and (2) retry
the open per-timestep — already-cached timesteps are skipped instantly on retry.
"""
import os
import time

import fsspec

# Make every anonymous GCS read time-bounded (seconds). A hung socket now errors
# and is retried rather than hanging the process indefinitely.
# GCS anonymous egress to the public ARCO bucket is variable/throttled (~0.1-1 MB/s),
# so a whole-globe chunk can take minutes. Generous timeout so slow-but-progressing
# reads aren't killed mid-chunk; retries handle the genuinely-stuck windows.
for _proto in ("gcs", "gs"):
    fsspec.config.conf.setdefault(_proto, {}).update(timeout=600, requests_timeout=600)

CACHE_DIR = os.environ.get("TCOF_CACHE_DIR", os.path.expanduser("~/.cache/tcof_era5"))


def load_arco(time_window, variables, pressure_levels, cachestore, attempts=8):
    """Open an ERA5ARCO MetDataset with retry on transient gcsfs stalls/timeouts."""
    from pycontrails.datalib.ecmwf import ERA5ARCO

    last = None
    for i in range(attempts):
        try:
            src = ERA5ARCO(time=time_window, variables=variables,
                           pressure_levels=pressure_levels, cachestore=cachestore)
            src.download()          # fetch (and cache) any missing timesteps now
            return src.open_metdataset()
        except Exception as e:      # noqa: BLE001 — timeout/HDF/incomplete download
            last = e
            print(f"  [era5 retry {i+1}/{attempts}] {type(e).__name__}: {str(e)[:80]}", flush=True)
            time.sleep(8)
    raise RuntimeError(f"ERA5ARCO load failed after {attempts} attempts") from last
