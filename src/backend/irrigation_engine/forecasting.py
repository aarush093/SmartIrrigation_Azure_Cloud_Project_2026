"""Soil-moisture forecasting behind a stable interface.

Phase-I Objective 3 commits to a model forecasting root-zone soil moisture one to
seven days ahead at R-squared of at least 0.80. That model is owned by Krishna
Agrawal (23BIT0428) and is delivered in weeks 4 to 5. To keep it off the critical
path, the scheduler never depends on the model directly: it depends on the
:class:`MoistureForecaster` protocol, and :class:`KcEt0Forecaster` satisfies that
protocol from the first day using nothing but the FAO-56 relation ETc = Kc x ET0.

If the learned model validates, it is swapped in by configuration. If it does not
reach the target by week 5, the shortfall is reported honestly and the fallback
stays active, with no change to the scheduler. See plan Sections 8 and 17.2.

Implemented in M1.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from irrigation_engine.models import CropStage, DailyWeather

__all__ = ["KcEt0Forecaster", "MoistureForecaster"]


@runtime_checkable
class MoistureForecaster(Protocol):
    """Produces the daily crop evapotranspiration series the scheduler projects with.

    Deliberately narrow. The scheduler needs one thing from any moisture model: how
    fast the root zone will dry over the planning horizon. Anything wider would
    couple the scheduler to a particular model's internals.
    """

    @property
    def name(self) -> str:
        """Identifier recorded on every schedule, making a decision traceable to its model."""
        ...

    def forecast_etc(
        self,
        weather: Sequence[DailyWeather],
        stages: Sequence[CropStage],
    ) -> list[float]:
        """Project crop evapotranspiration over the forecast horizon.

        Args:
            weather: Forecast days in chronological order, starting today.
            stages: Crop parameters for the same days, in the same order.

        Returns:
            Crop evapotranspiration per day, mm, the same length as ``weather``.

        Raises:
            ValueError: If the two sequences differ in length.
        """
        ...


class KcEt0Forecaster:
    """The FAO-56 default: ETc = Kc x ET0, with no learned component.

    This is the fallback referenced in plan Section 8, and it is what runs until
    the Objective 3 model validates. It is deterministic, needs no training data
    and cannot fail at inference time, which is precisely why the scheduler is
    built against it rather than against the learned model.
    """

    @property
    def name(self) -> str:
        """Return the model identifier recorded on each schedule."""
        return "kc-et0-fao56"

    def forecast_etc(
        self,
        weather: Sequence[DailyWeather],
        stages: Sequence[CropStage],
    ) -> list[float]:
        """Project crop evapotranspiration as the product of Kc and forecast ET0.

        FAO-56 equation 31: ``ETc = Kc x ET0``.

        Args:
            weather: Forecast days in chronological order, starting today.
            stages: Crop parameters for the same days, in the same order.

        Returns:
            Crop evapotranspiration per day, mm.

        Raises:
            ValueError: If the two sequences differ in length. They are paired
                positionally, so a length mismatch would silently associate a
                day with the wrong growth stage.
        """
        if len(weather) != len(stages):
            msg = (
                f"weather and stages must be the same length, got {len(weather)} and {len(stages)}"
            )
            raise ValueError(msg)
        return [stage.kc * day.et0_mm for day, stage in zip(weather, stages, strict=True)]
