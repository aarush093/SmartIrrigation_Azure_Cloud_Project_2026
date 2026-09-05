"""Provider interfaces for external data.

Every external call in the engine sits behind one of these protocols, and every
protocol has an offline fake in :mod:`irrigation_engine.providers.fakes`. Unit
tests use the fakes and reach no network; the real adapters are selected by
settings. See CLAUDE.md section 4.
"""

from __future__ import annotations

import datetime as dt
from typing import Protocol, runtime_checkable

from irrigation_engine.models import DailyWeather, SoilProfile

__all__ = ["SoilProvider", "WeatherProvider"]


@runtime_checkable
class WeatherProvider(Protocol):
    """Supplies daily forecast and archive weather for a point."""

    def fetch_weather(self, lat: float, lon: float, days: int = 7) -> list[DailyWeather]:
        """Fetch the daily forecast for a point.

        Args:
            lat: Latitude, decimal degrees.
            lon: Longitude, decimal degrees.
            days: Forecast horizon in days, starting today.

        Returns:
            One entry per day in chronological order, starting today.
        """
        ...

    def fetch_archive(
        self, lat: float, lon: float, start: dt.date, end: dt.date
    ) -> list[DailyWeather]:
        """Fetch observed daily weather for a past date range.

        Used by the simulation study and by the forecast calibration training
        set, never by the daily decision loop.

        Args:
            lat: Latitude, decimal degrees.
            lon: Longitude, decimal degrees.
            start: First date, inclusive.
            end: Last date, inclusive.

        Returns:
            One entry per day in chronological order.
        """
        ...


@runtime_checkable
class SoilProvider(Protocol):
    """Supplies the static soil profile for a point.

    Soil properties do not change over the life of the project, so one successful
    retrieval per field is enough and the result is cached permanently. See
    ``dataset/README.md``, D4 operational note.
    """

    def fetch_soil(self, lat: float, lon: float) -> SoilProfile:
        """Fetch the depth-weighted 0 to 30 cm soil profile for a point.

        Args:
            lat: Latitude, decimal degrees.
            lon: Longitude, decimal degrees.

        Returns:
            Sand, silt, clay, organic carbon and bulk density for the root zone.
        """
        ...
