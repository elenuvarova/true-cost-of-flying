"""Fuse fuel CO2 + contrail CO2e into a leaderboard row, with bands, GWP toggle, tiers.

CO2e is NEVER a bare number: GWP100 default + GWP20, low/central/high band from the
efficacy spread (0.35-0.51) stacked with the contrail ERF uncertainty implicit in the
range. See docs/IMPLEMENTATION_PLAN §6 and §11.
"""
from src import constants as C

CAP_M = 13000.0


def contrail_co2e_bands(ef_joules):
    """Return {GWP100:{low,central,high}, GWP20:{low,central,high}} in kg."""
    out = {}
    for horizon in ("GWP100", "GWP20"):
        out[horizon] = {
            "low": C.ef_to_co2e_kg(ef_joules, C.EFFICACY_LOW, horizon),
            "central": C.ef_to_co2e_kg(ef_joules, C.EFFICACY_CENTRAL, horizon),
            "high": C.ef_to_co2e_kg(ef_joules, C.EFFICACY_HIGH, horizon),
        }
    return out


def build_row(*, icao24, flight_id, owner_label, owner_confidence, registration,
              ac_type, openap_type, type_source, dep_time, route,
              fuel_kg, fuel_co2_kg, ef_joules, max_alt_m, coverage_gap=False):
    bands = contrail_co2e_bands(ef_joules)
    g100, g20 = bands["GWP100"], bands["GWP20"]
    combined_c = fuel_co2_kg + g100["central"]
    row = {
        "icao24": icao24, "flight_id": flight_id,
        "owner_label": owner_label, "owner_confidence": owner_confidence,
        "registration": registration, "ac_type": ac_type,
        "openap_type": openap_type, "type_source": type_source,
        "dep_time": dep_time, "route": route,
        "fuel_kg": round(fuel_kg, 1), "fuel_co2_kg": round(fuel_co2_kg, 1),
        "contrail_ef_joules": ef_joules,
        "contrail_co2e_low": round(g100["low"], 1),
        "contrail_co2e_central": round(g100["central"], 1),
        "contrail_co2e_high": round(g100["high"], 1),
        "contrail_co2e_gwp20_central": round(g20["central"], 1),
        "combined_co2e_central": round(combined_c, 1),
        "combined_co2e_low": round(fuel_co2_kg + g100["low"], 1),
        "combined_co2e_high": round(fuel_co2_kg + g100["high"], 1),
        "contrail_pct_of_fuel": round(100 * g100["central"] / fuel_co2_kg, 1) if fuel_co2_kg else 0.0,
        "metric": "GWP100", "horizon_years": 100,
        "bizjet_alt_flag": bool(max_alt_m > CAP_M),
        "proxy_type_flag": type_source not in ("native", "synonym"),
        "coverage_gap_flag": bool(coverage_gap),
    }
    return row


def assign_tiers(rows):
    """Tier by combined_co2e_central (GWP100). Tiers, not a spurious 1..N rank, because
    magnitude reshuffles with metric while the binary 'matters?' verdict is ~90% robust."""
    if not rows:
        return rows
    vals = sorted(r["combined_co2e_central"] for r in rows)
    n = len(vals)
    hi_cut = vals[int(n * 2 / 3)] if n >= 3 else vals[-1]
    lo_cut = vals[int(n * 1 / 3)] if n >= 3 else vals[0]
    for r in rows:
        v = r["combined_co2e_central"]
        r["tier"] = "high" if v >= hi_cut else ("low" if v < lo_cut else "medium")
    return sorted(rows, key=lambda r: r["combined_co2e_central"], reverse=True)
