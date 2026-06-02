"""Fuel burn -> CO2 via OpenAP, with a bizjet proxy-type fallback.

OpenAP ships 36 native types incl. only 2 bizjets (GLF6, C550). For types not native
or in OpenAP's synonym table we map to a documented proxy and flag it as an estimate.
"""
import numpy as np
from openap import FuelFlow, prop

from src.constants import CO2_PER_KG_FUEL

# Project proxy map for types OpenAP lacks natively (extends OpenAP's own synonyms).
# Each: ADS-B/typecode -> (openap_type, source). source: native|synonym|project_proxy.
TYPE_MAP = {
    "GLF6": ("GLF6", "native"), "GLF5": ("GLF6", "synonym"), "GLF4": ("GLF6", "project_proxy"),
    "GL7T": ("GLF6", "project_proxy"), "GL5T": ("GLF6", "synonym"), "GLEX": ("GLF6", "project_proxy"),
    "CL30": ("C550", "project_proxy"), "CL35": ("C550", "project_proxy"), "CL60": ("GLF6", "project_proxy"),
    "C550": ("C550", "native"), "C56X": ("C550", "synonym"), "C525": ("C550", "project_proxy"),
    "E55P": ("C550", "project_proxy"), "E545": ("C550", "project_proxy"), "E550": ("E145", "project_proxy"),
    "E35L": ("E145", "project_proxy"), "FA7X": ("GLF6", "project_proxy"), "FA8X": ("GLF6", "project_proxy"),
    "F900": ("GLF6", "project_proxy"), "F2TH": ("GLF6", "project_proxy"),
    # converted airliners (native)
    "B762": ("B763", "synonym"), "B763": ("B763", "native"), "B752": ("B752", "native"),
    "B738": ("B738", "native"), "BBJ2": ("B738", "synonym"), "A319": ("A319", "native"),
    "B77W": ("B77W", "native"), "B789": ("B789", "native"), "DH8D": ("C550", "project_proxy"),
}
DEFAULT_PROXY = ("GLF6", "default_proxy")


def resolve_type(typecode):
    return TYPE_MAP.get((typecode or "").upper(), DEFAULT_PROXY)


def fuel_and_co2(df, typecode):
    """Integrate OpenAP fuel flow over a track DataFrame -> (fuel_kg, co2_kg, openap_type, source).

    df needs columns: time, altitude_m, gs_kt. TAS is approximated by groundspeed
    (no wind correction) — a documented first-order assumption for the fuel estimate.
    """
    openap_type, source = resolve_type(typecode)
    ac = prop.aircraft(openap_type)
    mtow, oew = ac["limits"]["MTOW"], ac["limits"]["OEW"]
    mass = 0.85 * mtow  # mid-cruise mass assumption (constant); refine later if needed

    ff = FuelFlow(ac=openap_type, use_synonym=True)
    alt_ft = (df["altitude_m"].values / 0.3048)
    tas_kt = df["gs_kt"].values.copy()
    # fill missing groundspeed with a type-typical cruise TAS
    cruise_tas = 480.0 if mtow > 100000 else 440.0
    tas_kt = np.where(np.isnan(tas_kt) | (tas_kt <= 0), cruise_tas, tas_kt)
    vs_fpm = np.gradient(alt_ft, df["time"].values.astype("datetime64[s]").astype(float) / 60.0)

    fflow = np.array([ff.enroute(mass=mass, tas=float(t), alt=float(a), vs=float(v))
                      for t, a, v in zip(tas_kt, alt_ft, vs_fpm)])
    fflow = np.nan_to_num(fflow, nan=0.0)
    dt_s = np.diff(df["time"].values).astype("timedelta64[s]").astype(float)
    fuel_kg = float(np.sum(fflow[:-1] * dt_s))
    return fuel_kg, fuel_kg * CO2_PER_KG_FUEL, openap_type, source
