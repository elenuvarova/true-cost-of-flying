"""Contrail energy forcing via CoCiP — reusable module (offline batch only).

Returns total Energy Forcing (Joules) plus the per-waypoint CoCiP dataframe (carries
per-waypoint `ef`, used to colour the track by WHERE warming happened).
"""
from pycontrails import Flight
from pycontrails.models.cocip import Cocip
from pycontrails.models.ps_model import PSFlight
from pycontrails.models.humidity_scaling import ExponentialBoostLatitudeCorrectionHumidityScaling
import numpy as np

CAP_M = 13000.0  # CoCiP global calibration ceiling ~13 km (~FL426)

# PSFlight (Poll-Schumann) supports fewer types than OpenAP. Map OpenAP types it lacks
# to the nearest PS-supported aircraft for the contrail-performance step ONLY
# (fuel CO2 still uses the OpenAP type). Confirmed PS-supported incl. B763/B752/B77W/B789/GLF5.
PS_PROXY = {"GLF6": "GLF5", "C550": "E145"}


def ps_type_for(openap_type):
    return PS_PROXY.get(openap_type, openap_type)


def run_cocip(flight_df, openap_type, met, rad, flight_id="flight"):
    """Run CoCiP on a track. Returns (ef_total_J, waypoints_df) where waypoints_df has
    longitude/latitude/altitude/ef per resampled waypoint."""
    fl = Flight(
        longitude=flight_df["longitude"].values, latitude=flight_df["latitude"].values,
        altitude=flight_df["altitude_m"].values, time=flight_df["time"].values,
        aircraft_type=ps_type_for(openap_type), flight_id=str(flight_id),
    ).resample_and_fill("60s")
    cocip = Cocip(
        met=met, rad=rad, aircraft_performance=PSFlight(),
        humidity_scaling=ExponentialBoostLatitudeCorrectionHumidityScaling(),
        params={"process_emissions": True},
    )
    out = cocip.eval(fl)
    o = out.dataframe
    ef_total = float(np.nansum(o["ef"])) if "ef" in o else 0.0
    return ef_total, o
