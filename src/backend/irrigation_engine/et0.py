"""FAO-56 Penman-Monteith reference evapotranspiration.

This module exists as an independent cross-check, not as the production path.
ET0 in the daily loop is taken from Open-Meteo's ``et0_fao_evapotranspiration``
variable; this implementation is what validates that value against the Phase-I
Objective 2 acceptance criterion of +/- 0.2 mm/day over at least 365 station-days.

Reference: R. G. Allen, L. S. Pereira, D. Raes and M. Smith, "Crop
evapotranspiration: Guidelines for computing crop water requirements", FAO
Irrigation and Drainage Paper 56, 1998, equation 6.

Implemented in M1.
"""

from __future__ import annotations

import datetime as dt

__all__ = ["penman_monteith"]


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
) -> float:
    """Compute daily reference evapotranspiration by FAO-56 Penman-Monteith.

    Keyword-only because the argument list is long and positionally ambiguous;
    swapping ``temp_max_c`` and ``temp_min_c`` would otherwise be silent.

    Where an optional argument is not supplied, the FAO-56 fallback estimation
    procedure for that term is used (Chapter 3, "Missing climatic data"), and the
    result is correspondingly less accurate.

    Args:
        temp_max_c: Daily maximum air temperature at 2 m, degC.
        temp_min_c: Daily minimum air temperature at 2 m, degC.
        latitude: Field latitude in decimal degrees, positive north.
        date: Calendar date, used for the day of year in the extraterrestrial
            radiation term.
        elevation_m: Elevation above mean sea level, m, used for atmospheric
            pressure and the psychrometric constant.
        wind_speed_2m: Mean wind speed at 2 m, m/s. Defaults to the FAO-56
            recommended 2.0 m/s when unavailable.
        relative_humidity_max: Daily maximum relative humidity, percent.
        relative_humidity_min: Daily minimum relative humidity, percent.
        solar_radiation_mj: Incoming shortwave radiation, MJ/m2/day. Estimated by
            the Hargreaves radiation formula from the temperature range when
            unavailable.

    Returns:
        Reference evapotranspiration for a short green grass cover, mm/day.

    Raises:
        ValueError: If ``temp_min_c`` exceeds ``temp_max_c``, or latitude is
            outside -90 to 90.
    """
    raise NotImplementedError("M1: FAO-56 equation 6")
