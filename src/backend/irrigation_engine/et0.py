"""FAO-56 Penman-Monteith reference evapotranspiration.

This module is an independent cross-check, not the production path. ET0 in the
daily loop is taken from Open-Meteo's ``et0_fao_evapotranspiration`` variable;
this implementation is what validates that value against the Phase-I Objective 2
acceptance criterion of 0.2 mm/day over at least 365 station-days. The validation
run lives in ``tests/validation/et0_crosscheck.py``.

Reference: R. G. Allen, L. S. Pereira, D. Raes and M. Smith, "Crop
evapotranspiration: Guidelines for computing crop water requirements", FAO
Irrigation and Drainage Paper 56, 1998. Plan reference R20. Equation numbers in
the docstrings below refer to that paper. Constants live in ``params/et0.yaml``.

Every intermediate quantity is a module-level function rather than a local, so
each can be tested and inspected on its own. When the cross-check disagrees with
Open-Meteo it is the intermediates, not the final number, that identify why.
"""

from __future__ import annotations

import datetime as dt
import math
from typing import Any

from irrigation_engine.params import load_params

__all__ = [
    "atmospheric_pressure",
    "extraterrestrial_radiation",
    "net_radiation",
    "penman_monteith",
    "psychrometric_constant",
    "saturation_vapour_pressure",
    "svp_slope",
]


def _params() -> dict[str, Any]:
    """Return the ET0 constant block."""
    return load_params("et0")


def saturation_vapour_pressure(temp_c: float) -> float:
    """Saturation vapour pressure at a given air temperature.

    FAO-56 equation 11: ``e0(T) = 0.6108 exp(17.27 T / (T + 237.3))``.

    Args:
        temp_c: Air temperature, degC.

    Returns:
        Saturation vapour pressure, kPa.
    """
    c = _params()["atmosphere"]
    return float(c["svp_a"]) * math.exp(float(c["svp_b"]) * temp_c / (temp_c + float(c["svp_c"])))


def svp_slope(temp_c: float) -> float:
    """Slope of the saturation vapour pressure curve at a given temperature.

    FAO-56 equation 13: ``D = 4098 e0(T) / (T + 237.3)^2``.

    Args:
        temp_c: Mean air temperature, degC.

    Returns:
        Slope, kPa/degC.
    """
    c = _params()["atmosphere"]
    return (
        float(c["slope_numerator"])
        * saturation_vapour_pressure(temp_c)
        / (temp_c + float(c["svp_c"])) ** 2
    )


def atmospheric_pressure(elevation_m: float) -> float:
    """Atmospheric pressure at a given elevation.

    FAO-56 equation 7: ``P = 101.3 ((293 - 0.0065 z) / 293)^5.26``.

    Args:
        elevation_m: Elevation above mean sea level, m.

    Returns:
        Atmospheric pressure, kPa.
    """
    c = _params()["atmosphere"]
    ratio = (float(c["reference_temperature_k"]) - float(c["lapse_rate"]) * elevation_m) / float(
        c["reference_temperature_k"]
    )
    return float(float(c["sea_level_pressure_kpa"]) * ratio ** float(c["pressure_exponent"]))


def psychrometric_constant(pressure_kpa: float) -> float:
    """Psychrometric constant for a given atmospheric pressure.

    FAO-56 equation 8: ``g = 0.665e-3 P``.

    Args:
        pressure_kpa: Atmospheric pressure, kPa.

    Returns:
        Psychrometric constant, kPa/degC.
    """
    return float(_params()["atmosphere"]["psychrometric_coefficient"]) * pressure_kpa


def extraterrestrial_radiation(latitude: float, date: dt.date) -> float:
    """Extraterrestrial radiation for a latitude and day of year.

    FAO-56 equation 21, with the inverse relative Earth-Sun distance from
    equation 23, solar declination from equation 24 and the sunset hour angle
    from equation 25.

    Args:
        latitude: Latitude in decimal degrees, positive north.
        date: Calendar date, supplying the day of year.

    Returns:
        Extraterrestrial radiation Ra, MJ/m2/day.

    Raises:
        ValueError: If the latitude is outside -90 to 90.
    """
    if not -90.0 <= latitude <= 90.0:
        msg = f"latitude must lie between -90 and 90 degrees, got {latitude}"
        raise ValueError(msg)

    c = _params()["radiation"]
    phi = math.radians(latitude)
    day_of_year = date.timetuple().tm_yday

    inverse_distance = 1.0 + 0.033 * math.cos(2.0 * math.pi * day_of_year / 365.0)
    declination = 0.409 * math.sin(2.0 * math.pi * day_of_year / 365.0 - 1.39)

    # Clamped because within the polar circles the argument leaves [-1, 1],
    # meaning the sun does not set or does not rise.
    sunset_argument = min(max(-math.tan(phi) * math.tan(declination), -1.0), 1.0)
    sunset_hour_angle = math.acos(sunset_argument)

    return (
        (24.0 * 60.0 / math.pi)
        * float(c["solar_constant"])
        * inverse_distance
        * (
            sunset_hour_angle * math.sin(phi) * math.sin(declination)
            + math.cos(phi) * math.cos(declination) * math.sin(sunset_hour_angle)
        )
    )


def _solar_radiation_from_temperature_range(
    temp_max_c: float, temp_min_c: float, ra_mj: float, *, coastal: bool
) -> float:
    """Estimate solar radiation from the diurnal temperature range.

    FAO-56 equation 50, the Hargreaves radiation formula. A fallback: a clear day
    has a wide temperature range, a cloudy one a narrow range.
    """
    c = _params()["fallbacks"]
    krs = float(
        c["hargreaves_coefficient_coastal"] if coastal else c["hargreaves_coefficient_interior"]
    )
    return krs * math.sqrt(max(temp_max_c - temp_min_c, 0.0)) * ra_mj


def net_radiation(
    *,
    solar_radiation_mj: float,
    ra_mj: float,
    temp_max_c: float,
    temp_min_c: float,
    actual_vapour_pressure_kpa: float,
    elevation_m: float,
) -> float:
    """Net radiation at the reference crop surface.

    Net shortwave from FAO-56 equation 38, net longwave from equation 39, and
    their difference from equation 40.

    Args:
        solar_radiation_mj: Incoming shortwave radiation Rs, MJ/m2/day.
        ra_mj: Extraterrestrial radiation Ra, MJ/m2/day.
        temp_max_c: Daily maximum air temperature, degC.
        temp_min_c: Daily minimum air temperature, degC.
        actual_vapour_pressure_kpa: Actual vapour pressure ea, kPa.
        elevation_m: Elevation above mean sea level, m.

    Returns:
        Net radiation Rn, MJ/m2/day.
    """
    c = _params()["radiation"]

    net_shortwave = (1.0 - float(c["albedo"])) * solar_radiation_mj

    clear_sky = (float(c["clear_sky_a"]) + float(c["clear_sky_b"]) * elevation_m) * ra_mj
    # On a polar night Ra is zero, so the cloudiness ratio is undefined; FAO-56
    # advises carrying the previous day's ratio. Full cloudiness is the
    # conservative substitute here, and Indian latitudes never reach this branch.
    cloudiness = (
        float(c["cloudiness_a"]) * (solar_radiation_mj / clear_sky) + float(c["cloudiness_b"])
        if clear_sky > 0.0
        else 0.0
    )
    cloudiness = min(max(cloudiness, 0.0), 1.0)

    kelvin_max = temp_max_c + 273.16
    kelvin_min = temp_min_c + 273.16
    net_longwave = (
        float(c["stefan_boltzmann"])
        * ((kelvin_max**4 + kelvin_min**4) / 2.0)
        * (
            float(c["net_longwave_a"])
            + float(c["net_longwave_b"]) * math.sqrt(max(actual_vapour_pressure_kpa, 0.0))
        )
        * cloudiness
    )

    return net_shortwave - net_longwave


def penman_monteith(
    *,
    temp_max_c: float,
    temp_min_c: float,
    latitude: float,
    date: dt.date,
    elevation_m: float,
    wind_speed_2m: float | None = None,
    relative_humidity_max: float | None = None,
    relative_humidity_min: float | None = None,
    solar_radiation_mj: float | None = None,
    coastal: bool = False,
) -> float:
    """Compute daily reference evapotranspiration by FAO-56 Penman-Monteith.

    FAO-56 equation 6. Keyword-only because the argument list is long and
    positionally ambiguous; swapping ``temp_max_c`` and ``temp_min_c`` would
    otherwise be silent.

    Where an optional argument is not supplied the FAO-56 Chapter 3 fallback for
    that term is used, and the result is correspondingly less accurate: wind
    defaults to 2 m/s (equation 47), solar radiation is estimated from the
    temperature range (equation 50), and actual vapour pressure is taken as the
    saturation vapour pressure at the daily minimum temperature.

    Args:
        temp_max_c: Daily maximum air temperature at 2 m, degC.
        temp_min_c: Daily minimum air temperature at 2 m, degC.
        latitude: Field latitude in decimal degrees, positive north.
        date: Calendar date, used for the day of year in the radiation term.
        elevation_m: Elevation above mean sea level, m.
        wind_speed_2m: Mean wind speed at 2 m, m/s.
        relative_humidity_max: Daily maximum relative humidity, percent.
        relative_humidity_min: Daily minimum relative humidity, percent.
        solar_radiation_mj: Incoming shortwave radiation Rs, MJ/m2/day.
        coastal: Whether the site is coastal, which selects the Hargreaves
            coefficient used when solar radiation is estimated.

    Returns:
        Reference evapotranspiration for a short green grass cover, mm/day.

    Raises:
        ValueError: If ``temp_min_c`` exceeds ``temp_max_c``, if latitude is
            outside -90 to 90, if elevation is below -500 m, or if the computed
            ET0 falls outside physically plausible bounds.
    """
    if temp_min_c > temp_max_c:
        msg = f"minimum temperature {temp_min_c} exceeds maximum {temp_max_c}"
        raise ValueError(msg)
    if not -90.0 <= latitude <= 90.0:
        msg = f"latitude must lie between -90 and 90 degrees, got {latitude}"
        raise ValueError(msg)
    if elevation_m < -500.0:
        msg = f"elevation {elevation_m} m is below any land surface on Earth"
        raise ValueError(msg)

    params = _params()
    comb = params["combination"]
    temp_mean_c = (temp_max_c + temp_min_c) / 2.0

    slope = svp_slope(temp_mean_c)
    pressure = atmospheric_pressure(elevation_m)
    gamma = psychrometric_constant(pressure)

    # FAO-56 equation 12: mean saturation vapour pressure from the daily
    # extremes, not from the mean temperature, because the curve is non-linear.
    svp_max = saturation_vapour_pressure(temp_max_c)
    svp_min = saturation_vapour_pressure(temp_min_c)
    es = (svp_max + svp_min) / 2.0
    ea = _actual_vapour_pressure(
        svp_max, svp_min, relative_humidity_max, relative_humidity_min, params
    )

    ra_mj = extraterrestrial_radiation(latitude, date)
    rs_mj = (
        _solar_radiation_from_temperature_range(temp_max_c, temp_min_c, ra_mj, coastal=coastal)
        if solar_radiation_mj is None
        else solar_radiation_mj
    )

    rn_mj = net_radiation(
        solar_radiation_mj=rs_mj,
        ra_mj=ra_mj,
        temp_max_c=temp_max_c,
        temp_min_c=temp_min_c,
        actual_vapour_pressure_kpa=ea,
        elevation_m=elevation_m,
    )
    soil_heat_flux = float(params["radiation"]["soil_heat_flux_daily"])

    wind = (
        float(params["fallbacks"]["default_wind_speed_2m"])
        if wind_speed_2m is None
        else wind_speed_2m
    )
    if wind < 0.0:
        msg = f"wind speed cannot be negative, got {wind} m/s"
        raise ValueError(msg)

    numerator = float(comb["radiation_conversion"]) * slope * (rn_mj - soil_heat_flux) + gamma * (
        float(comb["wind_numerator"]) / (temp_mean_c + float(comb["temperature_offset"]))
    ) * wind * (es - ea)
    denominator = slope + gamma * (1.0 + float(comb["wind_denominator_coeff"]) * wind)

    et0 = numerator / denominator

    bounds = params["bounds"]
    if not float(bounds["min_et0_mm"]) <= et0 <= float(bounds["max_et0_mm"]):
        msg = (
            f"computed ET0 of {et0:.2f} mm/day is outside the physically plausible "
            f"range {bounds['min_et0_mm']} to {bounds['max_et0_mm']} mm/day; the "
            f"inputs are inconsistent"
        )
        raise ValueError(msg)
    return et0


def _actual_vapour_pressure(
    svp_max: float,
    svp_min: float,
    rh_max: float | None,
    rh_min: float | None,
    params: dict[str, Any],
) -> float:
    """Actual vapour pressure from humidity, with the FAO-56 fallback.

    FAO-56 equation 17 where both humidity extremes are known, equation 18 where
    only one is, and the Chapter 3 dewpoint substitution where neither is.
    """
    if rh_max is not None and rh_min is not None:
        return (svp_min * rh_max / 100.0 + svp_max * rh_min / 100.0) / 2.0
    if rh_max is not None:
        return svp_min * rh_max / 100.0
    if rh_min is not None:
        return svp_max * rh_min / 100.0
    if params["fallbacks"]["dewpoint_equals_tmin"]:
        return svp_min
    msg = "no humidity data supplied and the dewpoint fallback is disabled"
    raise ValueError(msg)
