"""The scheduler and the water balance must not count the same water twice.

Regression tests for the defect found on 5 September 2026. ``plan_day`` computed
the requirement as ``depletion + carry_over`` while the balance was stepped with
the depth actually *delivered*, so the shortfall of a truncated run sat in the
depletion **and** was added on top of it the next morning. The pump was asked for
water the root zone could not hold, and almost all of the excess drained past it:
1,467 mm of water and 1,452 mm of deep percolation over the two-season, nine-field
simulation, which is roughly 16 percent of the policy's total water use.

These tests close the loop that no single-module test could see. The scheduler in
isolation was self-consistent, and the balance in isolation was correct against
FAO-56 equation 85. Only stepping one into the other exposes the double count,
which is why the tests here drive a real
:class:`~irrigation_engine.balance.WaterBalance` rather than a stub.
"""

from __future__ import annotations

import datetime as dt

import pytest

from irrigation_engine.balance import WaterBalance
from irrigation_engine.models import CropStage, DailyWeather, GrowthStage
from irrigation_engine.scheduler import (
    IST,
    Decision,
    FieldState,
    PowerWindow,
    WindowSource,
    plan_day,
)

TODAY = dt.date(2026, 6, 15)
TAW = 150.0
RAW = 80.0
AREA = 4047.0
DISCHARGE = 380.2
EFFICIENCY = 0.65

#: Enough ETc in the forecast to keep the scheduler out of the NO_NEED branch,
#: and equal to the ETc the balance actually accrues below, so the two-day
#: arithmetic in these tests is exact rather than approximate.
DAILY_ETC = 5.0


def _stage() -> CropStage:
    """A mid-season stage whose Kc times the test ET0 gives exactly DAILY_ETC."""
    return CropStage(
        crop="groundnut",
        stage=GrowthStage.MID,
        days_after_sowing=60,
        kc=1.0,
        root_depth_m=0.6,
        depletion_fraction=0.5,
        yield_response_factor=0.7,
    )


def _weather(day: dt.date, *, rain_mm: float = 0.0) -> DailyWeather:
    """A dry day whose ET0 is DAILY_ETC, so ETc equals it at Kc 1.0."""
    return DailyWeather(date=day, et0_mm=DAILY_ETC, precipitation_mm=rain_mm)


def _field(depletion: float) -> FieldState:
    return FieldState(
        field_id="f1",
        depletion_mm=depletion,
        taw_mm=TAW,
        raw_mm=RAW,
        area_m2=AREA,
        irrigation_efficiency=EFFICIENCY,
        discharge_l_per_min=DISCHARGE,
        yield_response_factor=1.0,
    )


def _window(day: dt.date, hours: float) -> PowerWindow:
    start = dt.datetime.combine(day, dt.time(22, 0), tzinfo=IST)
    return PowerWindow(
        start=start,
        end=start + dt.timedelta(hours=hours),
        source=WindowSource.DECLARED_ROTATION,
        reliability=0.9,
    )


class TestTruncatedRunAccounting:
    """Two days, one truncated run, and no water counted twice."""

    def _two_days(self, *, hours: float, start_depletion: float) -> dict[str, float]:
        """Plan and step two consecutive days, returning what happened.

        The first window is deliberately short enough to truncate the run.
        """
        balance = WaterBalance()
        stage = _stage()
        forecast = [DAILY_ETC] * 7

        day_one = plan_day(
            _field(start_depletion),
            today=TODAY,
            windows=[_window(TODAY, hours)],
            forecast_etc_mm=forecast,
        )
        assert day_one.decision is Decision.IRRIGATE, "the first day must actually irrigate"

        after_one = balance.step(
            start_depletion, _weather(TODAY), stage, day_one.delivered_mm, taw_mm=TAW
        )

        tomorrow = TODAY + dt.timedelta(days=1)
        day_two = plan_day(
            _field(after_one.depletion_mm),
            today=tomorrow,
            windows=[_window(tomorrow, 24.0)],
            forecast_etc_mm=forecast,
        )
        after_two = balance.step(
            after_one.depletion_mm, _weather(tomorrow), stage, day_two.delivered_mm, taw_mm=TAW
        )

        return {
            "carry_over": day_one.carry_over_mm,
            "depletion_after_one": after_one.depletion_mm,
            "required_two": day_two.required_mm,
            "applied": day_one.delivered_mm + day_two.delivered_mm,
            "etc_accrued": after_one.etc_mm + after_two.etc_mm,
            "percolation": after_one.deep_percolation_mm + after_two.deep_percolation_mm,
        }

    def test_the_run_is_actually_truncated(self) -> None:
        """The fixture must exercise the case, or the rest proves nothing."""
        result = self._two_days(hours=3.0, start_depletion=90.0)
        assert result["carry_over"] > 0.0

    def test_the_next_days_requirement_equals_the_new_depletion(self) -> None:
        """The invariant the defect broke.

        After a truncated run and one balance step, the scheduler must ask for
        the depletion it now sees. The undelivered depth is inside that number
        already; asking for depletion plus carry-over asks for it twice.
        """
        result = self._two_days(hours=3.0, start_depletion=90.0)
        assert result["required_two"] == pytest.approx(result["depletion_after_one"])

    def test_the_requirement_does_not_double_count_the_carry_over(self) -> None:
        """Stated the other way round, so a future regression cannot pass both."""
        result = self._two_days(hours=3.0, start_depletion=90.0)
        doubled = result["depletion_after_one"] + result["carry_over"]
        assert result["required_two"] < doubled

    def test_water_applied_never_exceeds_the_deficit_plus_the_drying(self) -> None:
        """Conservation over the two days.

        Nothing may be applied beyond the deficit that existed at the start plus
        the ETc that accrued while irrigating. Anything more is water the root
        zone cannot hold, and the defect produced it on every truncated run.
        """
        result = self._two_days(hours=3.0, start_depletion=90.0)
        ceiling = 90.0 + result["etc_accrued"]
        assert result["applied"] <= ceiling + 1e-9

    @pytest.mark.parametrize("hours", [1.0, 2.0, 3.0, 4.0, 6.0])
    def test_conservation_holds_at_every_degree_of_truncation(self, hours: float) -> None:
        """From barely any window to nearly enough, the ceiling holds."""
        result = self._two_days(hours=hours, start_depletion=90.0)
        assert result["applied"] <= 90.0 + result["etc_accrued"] + 1e-9

    def test_a_truncated_run_wastes_nothing_to_percolation(self) -> None:
        """The observable symptom of the defect, pinned directly.

        A run that could not even fill the deficit has no surplus to lose. Under
        the double count the second day over-applied and the excess drained, so
        percolation on a dry two-day pair was non-zero.
        """
        result = self._two_days(hours=3.0, start_depletion=90.0)
        assert result["percolation"] == pytest.approx(0.0)
