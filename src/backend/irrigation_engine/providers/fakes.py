"""Offline fakes for every provider.

These are what unit tests use. No test in the default suite may reach the
network; tests that do are marked ``@pytest.mark.integration`` and are skipped
unless asked for. See CLAUDE.md section 4.

The fakes are deliberately plain: they replay data handed to them, so a test's
expected values sit in the test rather than being hidden in a fixture that
quietly changes behaviour. They also count their calls, which is how the caching
requirement on the soil provider is tested.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Sequence

from irrigation_engine.models import DailyWeather, SoilProfile

__all__ = ["FakeSoilProvider", "FakeWeatherProvider"]


class FakeWeatherProvider:
    """Replays a fixed weather series.

    Satisfies :class:`~irrigation_engine.providers.base.WeatherProvider`.
    """

    def __init__(
        self,
        forecast: Sequence[DailyWeather],
        archive: Sequence[DailyWeather] | None = None,
    ) -> None:
        """Store the series to replay.

        Args:
            forecast: Days returned by :meth:`fetch_weather`.
            archive: Days returned by :meth:`fetch_archive`. Defaults to the
                forecast series.
        """
        self.forecast = list(forecast)
        self.archive = list(forecast if archive is None else archive)
        self.calls = 0

    def fetch_weather(self, lat: float, lon: float, days: int = 7) -> list[DailyWeather]:
        """Return the first ``days`` entries of the stored forecast.

        Args:
            lat: Ignored. Present to satisfy the protocol.
            lon: Ignored. Present to satisfy the protocol.
            days: Number of days to return.

        Returns:
            The requested slice of the stored forecast.
        """
        self.calls += 1
        return self.forecast[:days]

    def fetch_archive(
        self, lat: float, lon: float, start: dt.date, end: dt.date
    ) -> list[DailyWeather]:
        """Return stored archive days falling within the range.

        Args:
            lat: Ignored. Present to satisfy the protocol.
            lon: Ignored. Present to satisfy the protocol.
            start: First date, inclusive.
            end: Last date, inclusive.

        Returns:
            Stored days between ``start`` and ``end``.
        """
        self.calls += 1
        return [day for day in self.archive if start <= day.date <= end]


class FakeSoilProvider:
    """Returns a fixed soil profile.

    Satisfies :class:`~irrigation_engine.providers.base.SoilProvider`.
    """

    def __init__(self, profile: SoilProfile) -> None:
        """Store the profile to return.

        Args:
            profile: The profile every call returns.
        """
        self.profile = profile
        self.calls = 0

    def fetch_soil(self, lat: float, lon: float) -> SoilProfile:
        """Return the stored profile.

        Args:
            lat: Ignored. Present to satisfy the protocol.
            lon: Ignored. Present to satisfy the protocol.

        Returns:
            The stored profile.
        """
        self.calls += 1
        return self.profile
