"""FAO-56 Penman-Monteith at the hourly time step, and its daily sum.

Exists to answer one question: whether the residual disagreement between this
project's daily-aggregate ET0 and Open-Meteo's published daily ET0 is explained
by Open-Meteo integrating hourly and summing, while this engine computes from
daily aggregates. FAO-56 sanctions both, and they need not agree.

Reference: FAO Irrigation and Drainage Paper 56, equation 53, read from
https://www.fao.org/4/x0490e/x0490e08.htm:

    ET0hr = [0.408 D (Rn - G) + g (37 / (Thr + 273)) u2 (e0(Thr) - ea)]
            / [D + g (1 + 0.34 u2)]

Two differences from the daily form matter and are the usual sources of error:

1. The wind coefficient is **37**, not 900. It is also not 900/24 = 37.5; the
   paper prints 37.
2. Soil heat flux is no longer negligible. FAO-56 equation 45 gives
   ``Ghr = 0.1 Rn`` during daylight and equation 46 gives ``Ghr = 0.5 Rn`` at
   night (Chapter 3, https://www.fao.org/4/x0490e/x0490e07.htm). Omitting G
   would overstate the hourly total.

Vapour pressure at this step uses the hourly temperature directly:
``es = e0(Thr)`` and, by equation 54, ``ea = e0(Thr) RHhr / 100``.
"""

from __future__ import annotations

import datetime as dt
import math
from dataclasses import dataclass
from typing import Any

from irrigation_engine.et0 import (
    atmospheric_pressure,
    psychrometric_constant,
    saturation_vapour_pressure,
    svp_slope,
)
from irrigation_engine.params import load_params

__all__ = [
    "HourlyWeather",
    "daily_from_hourly",
    "hourly_extraterrestrial_radiation",
    "penman_monteith_hourly",
    "seasonal_correction",
]


@dataclass(frozen=True)
class HourlyWeather:
    """One hour of observations at a point.

    Attributes:
        timestamp: Local wall-clock time at the midpoint convention used by the
            provider, timezone-aware.
        temp_c: Mean hourly air temperature at 2 m, degC.
        relative_humidity: Mean hourly relative humidity, percent.
        wind_speed_2m: Mean hourly wind speed at 2 m, m/s.
        solar_radiation_mj: Incoming shortwave radiation over the hour,
            MJ/m2/hour.
    """

    timestamp: dt.datetime
    temp_c: float
    relative_humidity: float
    wind_speed_2m: float
    solar_radiation_mj: float


def seasonal_correction(day_of_year: int) -> float:
    """Seasonal correction for solar time, FAO-56 equation 33.

    Args:
        day_of_year: Day of the year, 1 to 366.

    Returns:
        Seasonal correction Sc, hours.
    """
    b = 2.0 * math.pi * (day_of_year - 81) / 364.0
    return 0.1645 * math.sin(2.0 * b) - 0.1255 * math.cos(b) - 0.025 * math.sin(b)


def hourly_extraterrestrial_radiation(
    latitude: float,
    longitude: float,
    timestamp: dt.datetime,
    *,
    timezone_centre_longitude_west: float | None = None,
) -> float:
    """Extraterrestrial radiation over one hour, FAO-56 equation 28.

    Uses the solar time angle at the midpoint of the hour (equation 31) with the
    seasonal correction of equation 33, and the period bounds of equation 29.

    Args:
        latitude: Latitude in decimal degrees, positive north.
        longitude: Longitude in decimal degrees, positive east.
        timestamp: Local standard clock time at the **start** of the hour.
        timezone_centre_longitude_west: Longitude of the centre of the local time
            zone, degrees west of Greenwich. Defaults to the IST value in
            ``params/et0.yaml``.

    Returns:
        Extraterrestrial radiation for the hour, MJ/m2/hour. Zero at night.
    """
    params = load_params("et0")
    lz = (
        float(params["hourly"]["timezone_centre_longitude_west"])
        if timezone_centre_longitude_west is None
        else timezone_centre_longitude_west
    )
    gsc = float(params["radiation"]["solar_constant"])

    phi = math.radians(latitude)
    day_of_year = timestamp.timetuple().tm_yday

    inverse_distance = 1.0 + 0.033 * math.cos(2.0 * math.pi * day_of_year / 365.0)
    declination = 0.409 * math.sin(2.0 * math.pi * day_of_year / 365.0 - 1.39)

    # FAO-56 works in degrees west of Greenwich.
    lm = (360.0 - longitude) % 360.0
    midpoint_hour = timestamp.hour + 0.5
    solar_time_angle = (math.pi / 12.0) * (
        midpoint_hour + 0.06667 * (lz - lm) + seasonal_correction(day_of_year) - 12.0
    )

    # Equation 29: bounds of the one-hour period.
    half_period = math.pi / 24.0
    omega_1 = solar_time_angle - half_period
    omega_2 = solar_time_angle + half_period

    # Clip to the daylight arc; outside it the sun is below the horizon.
    sunset_argument = min(max(-math.tan(phi) * math.tan(declination), -1.0), 1.0)
    sunset_hour_angle = math.acos(sunset_argument)
    omega_1 = max(omega_1, -sunset_hour_angle)
    omega_2 = min(omega_2, sunset_hour_angle)
    if omega_2 <= omega_1:
        return 0.0

    return max(
        0.0,
        (12.0 * 60.0 / math.pi)
        * gsc
        * inverse_distance
        * (
            (omega_2 - omega_1) * math.sin(phi) * math.sin(declination)
            + math.cos(phi) * math.cos(declination) * (math.sin(omega_2) - math.sin(omega_1))
        ),
    )


def _hourly_net_radiation(
    hour: HourlyWeather,
    ra_mj: float,
    ea_kpa: float,
    elevation_m: float,
    params: dict[str, Any],
    daylight_cloudiness: float,
) -> float:
    """Net radiation for one hour, FAO-56 equations 38, 39 and 40."""
    c = params["radiation"]

    net_shortwave = (1.0 - float(c["albedo"])) * hour.solar_radiation_mj

    clear_sky = (float(c["clear_sky_a"]) + float(c["clear_sky_b"]) * elevation_m) * ra_mj
    if clear_sky > 0.0:
        cloudiness = float(c["cloudiness_a"]) * (hour.solar_radiation_mj / clear_sky) + float(
            c["cloudiness_b"]
        )
        cloudiness = min(max(cloudiness, 0.0), 1.0)
    else:
        # FAO-56 Chapter 3: at night the ratio Rs/Rso is undefined, and the value
        # from two to three hours before sunset is carried forward.
        cloudiness = daylight_cloudiness

    kelvin = hour.temp_c + 273.16
    # Stefan-Boltzmann is tabulated per day; divide by 24 for an hourly period.
    net_longwave = (
        (float(c["stefan_boltzmann"]) / 24.0)
        * kelvin**4
        * (float(c["net_longwave_a"]) + float(c["net_longwave_b"]) * math.sqrt(max(ea_kpa, 0.0)))
        * cloudiness
    )
    return net_shortwave - net_longwave


def penman_monteith_hourly(
    hour: HourlyWeather,
    *,
    latitude: float,
    longitude: float,
    elevation_m: float,
    daylight_cloudiness: float = 0.5,
) -> float:
    """Reference evapotranspiration for one hour, FAO-56 equation 53.

    Args:
        hour: The hour's observations.
        latitude: Latitude in decimal degrees, positive north.
        longitude: Longitude in decimal degrees, positive east.
        elevation_m: Elevation above mean sea level, m.
        daylight_cloudiness: Cloudiness factor carried into night hours, from the
            last daylight hour of the day. FAO-56 Chapter 3.

    Returns:
        Reference evapotranspiration for the hour, mm.
    """
    params = load_params("et0")
    comb = params["combination"]
    hourly = params["hourly"]

    slope = svp_slope(hour.temp_c)
    gamma = psychrometric_constant(atmospheric_pressure(elevation_m))

    # FAO-56 equation 54: at an hourly step both es and ea come from the hour's
    # own temperature and humidity, not from daily extremes.
    es = saturation_vapour_pressure(hour.temp_c)
    ea = es * hour.relative_humidity / 100.0

    ra_mj = hourly_extraterrestrial_radiation(latitude, longitude, hour.timestamp)
    rn_mj = _hourly_net_radiation(hour, ra_mj, ea, elevation_m, params, daylight_cloudiness)

    # Equations 45 and 46. Daylight is taken as any hour receiving shortwave
    # radiation, which is what the provider's own data reports.
    is_daylight = hour.solar_radiation_mj > 0.0
    ratio = float(
        hourly["soil_heat_flux_daylight"] if is_daylight else hourly["soil_heat_flux_night"]
    )
    soil_heat_flux = ratio * rn_mj

    wind = hour.wind_speed_2m
    numerator = float(comb["radiation_conversion"]) * slope * (rn_mj - soil_heat_flux) + gamma * (
        float(hourly["wind_numerator"]) / (hour.temp_c + float(comb["temperature_offset"]))
    ) * wind * (es - ea)
    denominator = slope + gamma * (1.0 + float(comb["wind_denominator_coeff"]) * wind)

    return numerator / denominator


def daily_from_hourly(
    hours: list[HourlyWeather],
    *,
    latitude: float,
    longitude: float,
    elevation_m: float,
) -> dict[dt.date, float]:
    """Sum hourly ET0 into daily totals.

    Negative hourly values are retained rather than clipped: FAO-56 permits a
    negative hourly ET0 under condensation, and clipping them would bias the
    daily total upward, which is exactly the kind of silent error this
    comparison exists to detect.

    Args:
        hours: Hourly observations in chronological order.
        latitude: Latitude in decimal degrees, positive north.
        longitude: Longitude in decimal degrees, positive east.
        elevation_m: Elevation above mean sea level, m.

    Returns:
        Daily ET0 totals, mm, keyed by local calendar date.
    """
    # The cloudiness factor for night hours is carried from the last daylight
    # hour of the same day, per FAO-56 Chapter 3.
    params = load_params("et0")
    c = params["radiation"]

    by_day: dict[dt.date, float] = {}
    last_cloudiness = 0.5

    for hour in hours:
        ra = hourly_extraterrestrial_radiation(latitude, longitude, hour.timestamp)
        clear_sky = (float(c["clear_sky_a"]) + float(c["clear_sky_b"]) * elevation_m) * ra
        if clear_sky > 0.0 and hour.solar_radiation_mj > 0.0:
            candidate = float(c["cloudiness_a"]) * (hour.solar_radiation_mj / clear_sky) + float(
                c["cloudiness_b"]
            )
            last_cloudiness = min(max(candidate, 0.0), 1.0)

        et0_hr = penman_monteith_hourly(
            hour,
            latitude=latitude,
            longitude=longitude,
            elevation_m=elevation_m,
            daylight_cloudiness=last_cloudiness,
        )
        day = hour.timestamp.date()
        by_day[day] = by_day.get(day, 0.0) + et0_hr

    return by_day
