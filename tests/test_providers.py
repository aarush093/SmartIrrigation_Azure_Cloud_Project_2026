"""Tests for the weather and soil adapters.

Every response here is mocked with ``respx``. No test in this file reaches the
network; the socket guard in ``conftest.py`` would fail it if it tried. The live
API is exercised only by ``tests/validation/``, which is marked ``integration``.

The unit conversions are the substance of these tests. Open-Meteo reports
precipitation probability as a percentage while the engine works in 0 to 1, and
SoilGrids reports texture in g/kg, organic carbon in dg/kg and bulk density in
cg/cm3. Each of those is a silent-wrong-answer bug if mishandled: the numbers
stay plausible and the irrigation depth is simply incorrect.
"""

from __future__ import annotations

import datetime as dt

import httpx
import pytest
import respx

from irrigation_engine.models import DailyWeather, SoilProfile
from irrigation_engine.providers import (
    FakeSoilProvider,
    FakeWeatherProvider,
    OpenMeteoProvider,
    SoilGridsProvider,
)
from irrigation_engine.providers.openmeteo import ARCHIVE_URL, FORECAST_URL
from irrigation_engine.providers.soilgrids import SOILGRIDS_URL

FORECAST_BODY = {
    "daily": {
        "time": ["2026-09-02", "2026-09-03", "2026-09-04"],
        "et0_fao_evapotranspiration": [5.2, 4.8, 5.5],
        "precipitation_sum": [0.0, 12.4, 2.1],
        "precipitation_probability_max": [5, 80, 30],
        "temperature_2m_max": [34.1, 31.0, 33.2],
        "temperature_2m_min": [24.0, 23.5, 24.2],
    }
}

ARCHIVE_BODY = {
    "daily": {
        "time": ["2025-06-01", "2025-06-02"],
        "et0_fao_evapotranspiration": [6.1, 5.9],
        "precipitation_sum": [0.0, 22.0],
        "temperature_2m_max": [39.0, 37.5],
        "temperature_2m_min": [27.0, 26.5],
    }
}


def soilgrids_body() -> dict[str, object]:
    """A SoilGrids response in the API's own integer units.

    sand 400 g/kg, silt 400 g/kg, clay 200 g/kg, soc 120 dg/kg, bdod 135 cg/cm3,
    identical across all three depths so the depth weighting is exercised without
    the expected value depending on the weights.
    """
    raw = {"sand": 400, "silt": 400, "clay": 200, "soc": 120, "bdod": 135}
    return {
        "properties": {
            "layers": [
                {
                    "name": name,
                    "depths": [
                        {"label": label, "values": {"mean": value}}
                        for label in ("0-5cm", "5-15cm", "15-30cm")
                    ],
                }
                for name, value in raw.items()
            ]
        }
    }


class TestOpenMeteoForecast:
    """Forecast parsing and unit handling."""

    @respx.mock
    def test_parses_a_forecast_into_daily_weather(self) -> None:
        respx.get(FORECAST_URL).mock(return_value=httpx.Response(200, json=FORECAST_BODY))
        days = OpenMeteoProvider().fetch_weather(12.97, 79.16, days=3)

        assert len(days) == 3
        assert days[0].date == dt.date(2026, 9, 2)
        assert days[0].et0_mm == pytest.approx(5.2)
        assert days[1].precipitation_mm == pytest.approx(12.4)

    @respx.mock
    def test_probability_is_converted_from_percent_to_a_fraction(self) -> None:
        """Open-Meteo reports 80 for 80 percent; the engine works in 0 to 1.

        The calibrated skip rule compares this against a probability threshold,
        so a factor of 100 here would make every skip decision wrong.
        """
        respx.get(FORECAST_URL).mock(return_value=httpx.Response(200, json=FORECAST_BODY))
        days = OpenMeteoProvider().fetch_weather(12.97, 79.16, days=3)
        assert days[1].precipitation_probability == pytest.approx(0.80)
        assert all(0.0 <= d.precipitation_probability <= 1.0 for d in days)  # type: ignore[operator]

    @respx.mock
    def test_forecast_days_are_marked_as_forecasts(self) -> None:
        respx.get(FORECAST_URL).mock(return_value=httpx.Response(200, json=FORECAST_BODY))
        days = OpenMeteoProvider().fetch_weather(12.97, 79.16, days=3)
        assert all(day.is_forecast for day in days)

    @respx.mock
    def test_it_requests_the_fao_et0_variable(self) -> None:
        """ET0 is consumed from the provider, not re-derived. Plan Section 6."""
        route = respx.get(FORECAST_URL).mock(return_value=httpx.Response(200, json=FORECAST_BODY))
        OpenMeteoProvider().fetch_weather(12.97, 79.16, days=3)
        assert "et0_fao_evapotranspiration" in route.calls[0].request.url.params["daily"]

    @respx.mock
    def test_it_requests_the_field_timezone(self) -> None:
        """Daily aggregation must use the farmer's calendar day, not UTC."""
        route = respx.get(FORECAST_URL).mock(return_value=httpx.Response(200, json=FORECAST_BODY))
        OpenMeteoProvider().fetch_weather(12.97, 79.16, days=3)
        assert route.calls[0].request.url.params["timezone"] == "Asia/Kolkata"

    @respx.mock
    def test_days_with_null_et0_are_dropped_not_defaulted(self) -> None:
        """A missing ET0 must never be read as zero.

        Zero ET0 would freeze the water balance and suppress an irrigation the
        crop actually needed, which is the most damaging failure this adapter
        could produce.
        """
        body = {
            "daily": {
                "time": ["2026-09-02", "2026-09-03"],
                "et0_fao_evapotranspiration": [5.2, None],
                "precipitation_sum": [0.0, 1.0],
                "precipitation_probability_max": [5, 10],
                "temperature_2m_max": [34.1, 31.0],
                "temperature_2m_min": [24.0, 23.5],
            }
        }
        respx.get(FORECAST_URL).mock(return_value=httpx.Response(200, json=body))
        days = OpenMeteoProvider().fetch_weather(12.97, 79.16, days=2)
        assert len(days) == 1
        assert days[0].date == dt.date(2026, 9, 2)

    @respx.mock
    def test_an_http_error_propagates(self) -> None:
        """A failed call must not silently yield an empty forecast."""
        respx.get(FORECAST_URL).mock(return_value=httpx.Response(500))
        with pytest.raises(httpx.HTTPStatusError):
            OpenMeteoProvider().fetch_weather(12.97, 79.16)

    @pytest.mark.parametrize("days", [0, -1, 17, 100])
    def test_an_out_of_range_horizon_is_rejected_before_any_call(self, days: int) -> None:
        """Validation happens locally, so a bad horizon never reaches the network."""
        with pytest.raises(ValueError, match="forecast horizon"):
            OpenMeteoProvider().fetch_weather(12.97, 79.16, days=days)

    @respx.mock
    def test_a_malformed_response_is_rejected(self) -> None:
        respx.get(FORECAST_URL).mock(return_value=httpx.Response(200, json={"error": True}))
        with pytest.raises(ValueError, match="no daily block"):
            OpenMeteoProvider().fetch_weather(12.97, 79.16)


class TestOpenMeteoArchive:
    """Archive parsing, used by the simulation study."""

    @respx.mock
    def test_parses_an_archive_range(self) -> None:
        respx.get(ARCHIVE_URL).mock(return_value=httpx.Response(200, json=ARCHIVE_BODY))
        days = OpenMeteoProvider().fetch_archive(
            18.99, 75.76, dt.date(2025, 6, 1), dt.date(2025, 6, 2)
        )
        assert len(days) == 2
        assert days[0].et0_mm == pytest.approx(6.1)

    @respx.mock
    def test_archive_days_carry_no_forecast_probability(self) -> None:
        """Archive rainfall is observed, so a probability would be meaningless."""
        respx.get(ARCHIVE_URL).mock(return_value=httpx.Response(200, json=ARCHIVE_BODY))
        days = OpenMeteoProvider().fetch_archive(
            18.99, 75.76, dt.date(2025, 6, 1), dt.date(2025, 6, 2)
        )
        assert all(day.precipitation_probability is None for day in days)
        assert not any(day.is_forecast for day in days)

    def test_a_reversed_date_range_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="precedes start date"):
            OpenMeteoProvider().fetch_archive(
                18.99, 75.76, dt.date(2025, 6, 2), dt.date(2025, 6, 1)
            )


class TestSoilGrids:
    """Depth weighting and the unit rescaling."""

    @respx.mock
    def test_converts_soilgrids_units_to_engine_units(self) -> None:
        """g/kg to fraction, dg/kg to fraction, cg/cm3 to g/cm3.

        Mishandling any of these leaves the numbers plausible and the available
        water wrong, which is why the divisors are named constants and asserted
        here rather than trusted.
        """
        respx.get(SOILGRIDS_URL).mock(return_value=httpx.Response(200, json=soilgrids_body()))
        profile = SoilGridsProvider().fetch_soil(12.97, 79.16)

        assert profile.sand == pytest.approx(0.40)
        assert profile.silt == pytest.approx(0.40)
        assert profile.clay == pytest.approx(0.20)
        assert profile.organic_carbon == pytest.approx(0.012)
        assert profile.bulk_density == pytest.approx(1.35)

    @respx.mock
    def test_the_converted_profile_is_accepted_by_the_pedotransfer(self) -> None:
        """End to end: a real-shaped response produces a usable soil constant.

        This is the test that would have caught a unit error even if the
        divisors above were changed to match a mistake.
        """
        from irrigation_engine.soil import saxton_rawls

        respx.get(SOILGRIDS_URL).mock(return_value=httpx.Response(200, json=soilgrids_body()))
        constants = saxton_rawls(SoilGridsProvider().fetch_soil(12.97, 79.16))
        assert 0.05 < constants.available_water_fraction < 0.30

    @respx.mock
    def test_depth_weighting_favours_the_thicker_layer(self) -> None:
        """The 15-30 cm layer carries three times the weight of the 0-5 cm layer."""
        body = {
            "properties": {
                "layers": [
                    {
                        "name": "sand",
                        "depths": [
                            {"label": "0-5cm", "values": {"mean": 100}},
                            {"label": "5-15cm", "values": {"mean": 100}},
                            {"label": "15-30cm", "values": {"mean": 500}},
                        ],
                    },
                    *[
                        {
                            "name": name,
                            "depths": [
                                {"label": label, "values": {"mean": value}}
                                for label in ("0-5cm", "5-15cm", "15-30cm")
                            ],
                        }
                        for name, value in (
                            ("silt", 400),
                            ("clay", 200),
                            ("soc", 120),
                            ("bdod", 135),
                        )
                    ],
                ]
            }
        }
        respx.get(SOILGRIDS_URL).mock(return_value=httpx.Response(200, json=body))
        profile = SoilGridsProvider().fetch_soil(12.97, 79.16)
        # (100*5 + 100*10 + 500*15) / 30 = 300 g/kg
        assert profile.sand == pytest.approx(0.30)

    @respx.mock
    def test_the_coordinates_are_recorded_on_the_profile(self) -> None:
        """Soil is cached per field permanently, so the profile carries its point."""
        respx.get(SOILGRIDS_URL).mock(return_value=httpx.Response(200, json=soilgrids_body()))
        profile = SoilGridsProvider().fetch_soil(12.97, 79.16)
        assert profile.latitude == pytest.approx(12.97)
        assert profile.longitude == pytest.approx(79.16)

    @respx.mock
    def test_a_missing_property_is_rejected(self) -> None:
        """A partial response must not silently produce a partial profile."""
        body = soilgrids_body()
        body["properties"]["layers"] = body["properties"]["layers"][:2]  # type: ignore[index]
        respx.get(SOILGRIDS_URL).mock(return_value=httpx.Response(200, json=body))
        with pytest.raises(ValueError, match="missing properties"):
            SoilGridsProvider().fetch_soil(12.97, 79.16)

    @respx.mock
    def test_an_empty_response_is_rejected(self) -> None:
        respx.get(SOILGRIDS_URL).mock(return_value=httpx.Response(200, json={}))
        with pytest.raises(ValueError, match="no layers"):
            SoilGridsProvider().fetch_soil(12.97, 79.16)

    @respx.mock
    def test_an_http_error_propagates(self) -> None:
        """ISRIC has been reported as intermittently paused; failure must be visible."""
        respx.get(SOILGRIDS_URL).mock(return_value=httpx.Response(503))
        with pytest.raises(httpx.HTTPStatusError):
            SoilGridsProvider().fetch_soil(12.97, 79.16)


class TestFakes:
    """The offline doubles the rest of the suite depends on."""

    def test_the_weather_fake_replays_and_slices(self) -> None:
        days = [
            DailyWeather(
                date=dt.date(2026, 9, 2) + dt.timedelta(days=i), et0_mm=5.0, precipitation_mm=0.0
            )
            for i in range(7)
        ]
        provider = FakeWeatherProvider(days)
        assert len(provider.fetch_weather(0.0, 0.0, days=3)) == 3
        assert provider.calls == 1

    def test_the_weather_fake_filters_the_archive_by_date(self) -> None:
        days = [
            DailyWeather(
                date=dt.date(2026, 9, 2) + dt.timedelta(days=i), et0_mm=5.0, precipitation_mm=0.0
            )
            for i in range(7)
        ]
        provider = FakeWeatherProvider(days)
        selected = provider.fetch_archive(0.0, 0.0, dt.date(2026, 9, 3), dt.date(2026, 9, 5))
        assert [d.date for d in selected] == [
            dt.date(2026, 9, 3),
            dt.date(2026, 9, 4),
            dt.date(2026, 9, 5),
        ]

    def test_the_soil_fake_returns_the_stored_profile(self) -> None:
        profile = SoilProfile(sand=0.4, silt=0.4, clay=0.2, organic_carbon=0.012, bulk_density=1.35)
        provider = FakeSoilProvider(profile)
        assert provider.fetch_soil(0.0, 0.0) is profile
        assert provider.calls == 1
