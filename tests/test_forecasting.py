"""Tests for the MoistureForecaster interface and its FAO-56 default.

This interface is the contract between the engine and Krishna Agrawal's
Objective 3 soil-moisture model. Its whole purpose is that the scheduler never
depends on the learned model directly: if that model misses its R-squared target,
:class:`KcEt0Forecaster` stays active and nothing downstream changes.

Plan Sections 8 and 17.2.
"""

from __future__ import annotations

import datetime as dt

import pytest

from irrigation_engine.forecasting import KcEt0Forecaster, MoistureForecaster
from irrigation_engine.models import CropStage, DailyWeather, GrowthStage


def stage(kc: float) -> CropStage:
    """Build a crop stage carrying the given crop coefficient."""
    return CropStage(
        crop="wheat",
        stage=GrowthStage.MID,
        days_after_sowing=90,
        kc=kc,
        root_depth_m=1.5,
        depletion_fraction=0.55,
        yield_response_factor=1.0,
    )


def day(index: int, et0: float) -> DailyWeather:
    """Build a forecast day with the given reference evapotranspiration."""
    return DailyWeather(
        date=dt.date(2026, 3, 1) + dt.timedelta(days=index),
        et0_mm=et0,
        precipitation_mm=0.0,
        precipitation_probability=0.1,
    )


def test_the_default_forecaster_satisfies_the_protocol() -> None:
    """Structural typing: no inheritance is required to be a MoistureForecaster.

    Krishna's model will be checked the same way, so this is the contract.
    """
    assert isinstance(KcEt0Forecaster(), MoistureForecaster)


def test_etc_is_kc_times_et0_for_every_day() -> None:
    """FAO-56 equation 31, applied elementwise across the horizon."""
    weather = [day(0, 5.0), day(1, 4.0), day(2, 6.0)]
    stages = [stage(1.15), stage(1.15), stage(1.10)]

    assert KcEt0Forecaster().forecast_etc(weather, stages) == pytest.approx([5.75, 4.6, 6.6])


def test_the_horizon_length_is_preserved() -> None:
    """One ETc per forecast day, so the scheduler can project day by day."""
    weather = [day(i, 5.0) for i in range(7)]
    stages = [stage(1.15) for _ in range(7)]
    assert len(KcEt0Forecaster().forecast_etc(weather, stages)) == 7


def test_a_length_mismatch_is_rejected() -> None:
    """The sequences are paired positionally, so a mismatch would misalign stages.

    Silently zipping to the shorter list would associate a day with the wrong
    growth stage and understate demand at exactly the wrong point in the season.
    """
    with pytest.raises(ValueError, match="same length"):
        KcEt0Forecaster().forecast_etc([day(0, 5.0), day(1, 5.0)], [stage(1.15)])


def test_an_empty_horizon_is_allowed() -> None:
    """A zero-length forecast is empty, not an error."""
    assert KcEt0Forecaster().forecast_etc([], []) == []


def test_the_model_name_is_reported() -> None:
    """Every schedule records the model that produced it, for traceability."""
    assert KcEt0Forecaster().name == "kc-et0-fao56"


def test_the_forecaster_is_deterministic() -> None:
    """Identical inputs give identical output, which the scheduler relies on."""
    weather = [day(i, 5.0 + i * 0.1) for i in range(7)]
    stages = [stage(1.15) for _ in range(7)]
    forecaster = KcEt0Forecaster()
    assert forecaster.forecast_etc(weather, stages) == forecaster.forecast_etc(weather, stages)


def test_a_substitute_implementation_also_satisfies_the_protocol() -> None:
    """Proves the interface is genuinely open, not accidentally tied to the default.

    This stands in for Krishna's model until it arrives: if this passes, a
    learned forecaster can be swapped in by configuration with no engine change.
    """

    class ConstantForecaster:
        """A stand-in learned model that always predicts 4 mm/day."""

        @property
        def name(self) -> str:
            return "test-constant"

        def forecast_etc(
            self,
            weather: list[DailyWeather],
            stages: list[CropStage],
        ) -> list[float]:
            return [4.0] * len(weather)

    substitute = ConstantForecaster()
    assert isinstance(substitute, MoistureForecaster)
    assert substitute.forecast_etc([day(0, 5.0)], [stage(1.15)]) == [4.0]
