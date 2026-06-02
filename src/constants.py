"""Single source of truth for physical/accounting constants.

See docs/RESEARCH_BRIEF.md §5/§6 and docs/IMPLEMENTATION_PLAN.md §6 for provenance.
"""

# Fuel -> CO2: exactly 3160 g CO2 per kg jet fuel (openap/emission.py v2.5.0; ICAO/EU ETS).
CO2_PER_KG_FUEL = 3.16

# ERF/RF efficacy applied to per-flight contrail Energy Forcing as a first-order
# global-mean scalar. Central 0.42; literature span ~0.35 (Bickel) .. ~0.51 (Lee-implied 57/111).
EFFICACY_CENTRAL = 0.42
EFFICACY_LOW = 0.35
EFFICACY_HIGH = 0.51

# --- EF (Joules) -> CO2-equivalent mass (kg) bridge, GWP100 basis ---
# CoCiP outputs Energy Forcing EF in Joules = globally-integrated (RF x area x time)
# over the contrail lifetime. To express it as an equivalent CO2 mass we divide by the
# globally-integrated time-integrated radiative forcing of 1 kg CO2 over the horizon
# (AGWP), converted from per-area to total Joules:
#   AGWP100(CO2)  = 9.17e-14  W m^-2 yr (kg CO2)^-1   (IPCC AR6 / AR5)
#   Earth area    = 5.101e14  m^2
#   seconds/year  = 3.1557e7  s
#   => J per kg CO2 (global, 100yr) = AGWP100 * area * s_per_yr
AGWP100_CO2_W_M2_YR_PER_KG = 9.17e-14
EARTH_AREA_M2 = 5.101e14
SECONDS_PER_YEAR = 3.1557e7
J_PER_KG_CO2_GWP100 = AGWP100_CO2_W_M2_YR_PER_KG * EARTH_AREA_M2 * SECONDS_PER_YEAR  # ~1.476e9

# GWP20 horizon (AGWP20 of CO2 ~ 2.49e-14 W m^-2 yr / kg -> contrail/CO2e ratio rises)
AGWP20_CO2_W_M2_YR_PER_KG = 2.49e-14
J_PER_KG_CO2_GWP20 = AGWP20_CO2_W_M2_YR_PER_KG * EARTH_AREA_M2 * SECONDS_PER_YEAR


def ef_to_co2e_kg(ef_joules: float, efficacy: float = EFFICACY_CENTRAL, horizon: str = "GWP100") -> float:
    """Convert contrail Energy Forcing (J) to an equivalent CO2 mass (kg)."""
    denom = J_PER_KG_CO2_GWP100 if horizon == "GWP100" else J_PER_KG_CO2_GWP20
    return efficacy * ef_joules / denom
