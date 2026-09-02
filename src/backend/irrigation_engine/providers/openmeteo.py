"""Open-Meteo weather provider (datasets D1, D2 and D8).

Uses the forecast API for the daily loop and the historical archive API for the
simulation study. ET0 is taken from the published
``et0_fao_evapotranspiration`` daily variable rather than re-derived; see plan
Section 6 and :mod:`irrigation_engine.et0` for the cross-check.

No API key is required. Data is CC BY 4.0 and attribution to Open-Meteo.com is
carried in the application footer and the report.

Endpoints:
    forecast  https://api.open-meteo.com/v1/forecast
    archive   https://archive-api.open-meteo.com/v1/archive

Implemented in M1.
"""

from __future__ import annotations

import datetime as dt

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
                throughout the pilot.
            timeout_s: Per-request timeout, seconds.
        """
        raise NotImplementedError("M1")

    def fetch_weather(self, lat: float, lon: float, days: int = 7) -> list[DailyWeather]:
        """Fetch the daily forecast for a point.

        Args:
            lat: Latitude, decimal degrees.
            lon: Longitude, decimal degrees.
            days: Forecast horizon, 1 to 16.

        Returns:
            One entry per day in chronological order, starting today.

        Raises:
            ValueError: If ``days`` is outside 1 to 16.
            httpx.HTTPError: On transport failure or a non-success status.
        """
        raise NotImplementedError("M1")

    def fetch_archive(
        self, lat: float, lon: float, start: dt.date, end: dt.date
    ) -> list[DailyWeather]:
        """Fetch observed daily weather for a past date range.

        Args:
            lat: Latitude, decimal degrees.
            lon: Longitude, decimal degrees.
            start: First date, inclusive.
            end: Last date, inclusive.

        Returns:
            One entry per day in chronological order.

        Raises:
            ValueError: If ``end`` precedes ``start``.
            httpx.HTTPError: On transport failure or a non-success status.
        """
        raise NotImplementedError("M1")


def fetch_weather(lat: float, lon: float, days: int = 7) -> list[DailyWeather]:
    """Fetch the daily forecast using a default provider instance.

    Convenience wrapper over :class:`OpenMeteoProvider` for scripts and demos.
    Production code takes a provider by injection so it can be faked.

    Args:
        lat: Latitude, decimal degrees.
        lon: Longitude, decimal degrees.
        days: Forecast horizon in days.

    Returns:
        One entry per day in chronological order, starting today.
    """
    raise NotImplementedError("M1")


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
    raise NotImplementedError("M1")
