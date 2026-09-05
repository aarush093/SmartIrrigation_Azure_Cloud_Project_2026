"""Open-Meteo weather provider (datasets D1, D2 and D8).

Uses the forecast API for the daily loop and the historical archive API for the
simulation study. ET0 is taken from the published ``et0_fao_evapotranspiration``
daily variable rather than re-derived; see plan Section 6 and
:mod:`irrigation_engine.et0` for the cross-check.

No API key is required. Data is CC BY 4.0 and attribution to Open-Meteo.com is
carried in the application footer and the report.

Endpoints:
    forecast  https://api.open-meteo.com/v1/forecast
    archive   https://archive-api.open-meteo.com/v1/archive
"""

from __future__ import annotations

import datetime as dt
from typing import Any

import httpx

from irrigation_engine.models import DailyWeather

__all__ = ["OpenMeteoProvider", "fetch_archive", "fetch_weather"]

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

DAILY_VARIABLES = (
    "et0_fao_evapotranspiration",
    "precipitation_sum",
    "precipitation_probability_max",
    "temperature_2m_max",
    "temperature_2m_min",
)

# The archive carries observations, so it has no forecast probability.
ARCHIVE_VARIABLES = tuple(v for v in DAILY_VARIABLES if v != "precipitation_probability_max")

MAX_FORECAST_DAYS = 16


class OpenMeteoProvider:
    """Weather provider backed by the Open-Meteo public API.

    Satisfies :class:`~irrigation_engine.providers.base.WeatherProvider`.
    """

    def __init__(
        self,
        *,
        client: httpx.Client | None = None,
        timezone: str = "Asia/Kolkata",
        timeout_s: float = 10.0,
    ) -> None:
        """Configure the provider.

        Args:
            client: An httpx client to reuse. One is created if not supplied,
                which is the normal path outside tests.
            timezone: IANA timezone for daily aggregation. The field's local
                calendar day is what the farmer acts on, so this is IST
                throughout the pilot. Aggregating to the wrong day boundary
                shifts every rainfall total by up to a day.
            timeout_s: Per-request timeout, seconds.
        """
        self._client = client
        self._owns_client = client is None
        self.timezone = timezone
        self.timeout_s = timeout_s

    def _get(self, url: str, params: dict[str, Any]) -> dict[str, Any]:
        """Issue one GET and return the decoded body."""
        if self._client is not None:
            response = self._client.get(url, params=params, timeout=self.timeout_s)
        else:
            with httpx.Client(timeout=self.timeout_s) as client:
                response = client.get(url, params=params)
        response.raise_for_status()
        body: dict[str, Any] = response.json()
        return body

    def fetch_weather(self, lat: float, lon: float, days: int = 7) -> list[DailyWeather]:
        """Fetch the daily forecast for a point.

        Args:
            lat: Latitude, decimal degrees.
            lon: Longitude, decimal degrees.
            days: Forecast horizon, 1 to 16.

        Returns:
            One entry per day in chronological order, starting today.

        Raises:
            ValueError: If ``days`` is outside 1 to 16, or the response is
                malformed.
            httpx.HTTPError: On transport failure or a non-success status.
        """
        if not 1 <= days <= MAX_FORECAST_DAYS:
            msg = f"forecast horizon must be 1 to {MAX_FORECAST_DAYS} days, got {days}"
            raise ValueError(msg)

        body = self._get(
            FORECAST_URL,
            {
                "latitude": lat,
                "longitude": lon,
                "daily": ",".join(DAILY_VARIABLES),
                "timezone": self.timezone,
                "forecast_days": days,
            },
        )
        return _parse_daily(body, forecast=True)

    def fetch_archive(
        self, lat: float, lon: float, start: dt.date, end: dt.date
    ) -> list[DailyWeather]:
        """Fetch observed daily weather for a past date range.

        Used by the simulation study and the forecast calibration training set,
        never by the daily decision loop.

        Args:
            lat: Latitude, decimal degrees.
            lon: Longitude, decimal degrees.
            start: First date, inclusive.
            end: Last date, inclusive.

        Returns:
            One entry per day in chronological order.

        Raises:
            ValueError: If ``end`` precedes ``start``, or the response is
                malformed.
            httpx.HTTPError: On transport failure or a non-success status.
        """
        if end < start:
            msg = f"end date {end} precedes start date {start}"
            raise ValueError(msg)

        body = self._get(
            ARCHIVE_URL,
            {
                "latitude": lat,
                "longitude": lon,
                "daily": ",".join(ARCHIVE_VARIABLES),
                "timezone": self.timezone,
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
            },
        )
        return _parse_daily(body, forecast=False)


def _parse_daily(body: dict[str, Any], *, forecast: bool) -> list[DailyWeather]:
    """Convert an Open-Meteo daily block into DailyWeather records.

    Days where ET0 or precipitation is null are dropped rather than defaulted:
    a missing ET0 silently read as zero would freeze the water balance and
    suppress an irrigation the crop needed.
    """
    daily = body.get("daily")
    if not isinstance(daily, dict) or "time" not in daily:
        msg = "Open-Meteo response has no daily block"
        raise ValueError(msg)

    times: list[str] = daily["time"]
    et0 = daily.get("et0_fao_evapotranspiration", [None] * len(times))
    rain = daily.get("precipitation_sum", [None] * len(times))
    probability = daily.get("precipitation_probability_max", [None] * len(times))
    t_max = daily.get("temperature_2m_max", [None] * len(times))
    t_min = daily.get("temperature_2m_min", [None] * len(times))

    records: list[DailyWeather] = []
    for index, day in enumerate(times):
        if et0[index] is None or rain[index] is None:
            continue

        raw_probability = probability[index] if forecast else None
        records.append(
            DailyWeather(
                date=dt.date.fromisoformat(day),
                et0_mm=max(float(et0[index]), 0.0),
                precipitation_mm=max(float(rain[index]), 0.0),
                # Open-Meteo reports probability as a percentage; the engine
                # works in 0 to 1 throughout.
                precipitation_probability=(
                    None if raw_probability is None else float(raw_probability) / 100.0
                ),
                temp_max_c=None if t_max[index] is None else float(t_max[index]),
                temp_min_c=None if t_min[index] is None else float(t_min[index]),
            )
        )
    return records


def fetch_weather(lat: float, lon: float, days: int = 7) -> list[DailyWeather]:
    """Fetch the daily forecast using a default provider instance.

    Convenience wrapper for scripts and demos. Production code takes a provider
    by injection so it can be faked.

    Args:
        lat: Latitude, decimal degrees.
        lon: Longitude, decimal degrees.
        days: Forecast horizon in days.

    Returns:
        One entry per day in chronological order, starting today.
    """
    return OpenMeteoProvider().fetch_weather(lat, lon, days)


def fetch_archive(lat: float, lon: float, start: dt.date, end: dt.date) -> list[DailyWeather]:
    """Fetch archive weather using a default provider instance.

    Args:
        lat: Latitude, decimal degrees.
        lon: Longitude, decimal degrees.
        start: First date, inclusive.
        end: Last date, inclusive.

    Returns:
        One entry per day in chronological order.
    """
    return OpenMeteoProvider().fetch_archive(lat, lon, start, end)
