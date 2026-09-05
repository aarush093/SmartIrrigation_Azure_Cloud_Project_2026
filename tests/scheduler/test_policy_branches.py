"""Example-based tests for each branch of the Section 7 policy.

The property tests prove the invariants hold everywhere. These prove each branch
fires on the case it was written for, which is what a reviewer will ask about
one branch at a time.

Particular attention to ``CAPACITY_LIMIT``, the branch corrected on 3 September
2026. Its whole purpose is to fire *before* the deficit outgrows what one window
can repay, so a test that only checked it fires afterwards would pass against the
superseded logic.
"""

from __future__ import annotations

import datetime as dt

import pytest

from irrigation_engine.scheduler import (
    IST,
    Decision,
    FieldState,
    PowerWindow,
    RainForecast,
    ReasonCode,
    WindowSource,
    plan_day,
    plan_multi_field,
    window_capacity_mm,
)

TODAY = dt.date(2026, 9, 3)


def window(hours: float = 8.0, reliability: float = 1.0, start_hour: int = 22) -> PowerWindow:
    """A night feeder window, the Maharashtra default."""
    start = dt.datetime(2026, 9, 3, start_hour, 0, tzinfo=IST)
    return PowerWindow(
        start=start,
        end=start + dt.timedelta(hours=hours),
        source=WindowSource.DECLARED_ROTATION,
        reliability=reliability,
    )


def field(
    depletion: float = 25.0,
    *,
    raw: float = 80.0,
    taw: float = 150.0,
    area: float = 4047.0,
    discharge: float = 380.2,
    efficiency: float = 0.65,
    ky: float = 1.0,
    field_id: str = "f1",
) -> FieldState:
    """The worked example field, with overrides."""
    return FieldState(
        field_id=field_id,
        depletion_mm=depletion,
        taw_mm=taw,
        raw_mm=raw,
        area_m2=area,
        irrigation_efficiency=efficiency,
        discharge_l_per_min=discharge,
        yield_response_factor=ky,
    )


DRY = [0.0] * 7
NORMAL = [5.75] * 7


class TestBranches:
    """One test per policy branch."""

    def test_no_need_when_the_field_is_wet_and_demand_is_low(self) -> None:
        schedule = plan_day(
            field(depletion=2.0), today=TODAY, windows=[window()], forecast_etc_mm=DRY
        )
        assert schedule.decision is Decision.WAIT
        assert schedule.reason_code is ReasonCode.NO_NEED
        assert schedule.minutes == 0.0

    def test_stress_imminent_when_the_projection_passes_raw(self) -> None:
        """The mandatory branch: without water the crop will be stressed by W2."""
        schedule = plan_day(
            field(depletion=60.0), today=TODAY, windows=[window()], forecast_etc_mm=NORMAL
        )
        assert schedule.decision is Decision.IRRIGATE
        assert schedule.reason_code is ReasonCode.STRESS_IMMINENT

    def test_opportunistic_topup_above_half_raw(self) -> None:
        """A comfortable field is still topped up while the window is open.

        Chosen so neither branch above can fire: a strong pump makes the window
        capacity 46 mm, above the 35 mm projection, and the projection stays
        below RAW, so only the opportunistic branch is left.
        """
        state = field(depletion=35.0, raw=60.0, discharge=600.0)
        w1, w2 = window(), window()
        assert window_capacity_mm(state, w1) > 35.0, "capacity branch must not fire"
        schedule = plan_day(state, today=TODAY, windows=[w1, w2], forecast_etc_mm=DRY)
        assert schedule.decision is Decision.IRRIGATE
        assert schedule.reason_code is ReasonCode.OPPORTUNISTIC_TOPUP

    def test_skip_when_calibrated_rain_covers_the_deficit(self) -> None:
        schedule = plan_day(
            field(depletion=30.0),
            today=TODAY,
            windows=[window()],
            forecast_etc_mm=NORMAL,
            rain=RainForecast(expected_mm=35.0, confidence=0.9),
        )
        assert schedule.decision is Decision.SKIP
        assert schedule.reason_code is ReasonCode.RAIN_EXPECTED
        assert schedule.minutes == 0.0

    def test_no_skip_when_rain_is_forecast_but_not_trusted(self) -> None:
        """Amount alone is not enough; the calibrated confidence must support it.

        This is the difference between the raw forecast probability and the
        calibrated one. Plan Section 8.
        """
        schedule = plan_day(
            field(depletion=60.0),
            today=TODAY,
            windows=[window()],
            forecast_etc_mm=NORMAL,
            rain=RainForecast(expected_mm=35.0, confidence=0.3),
        )
        assert schedule.decision is Decision.IRRIGATE

    def test_no_skip_when_rain_is_trusted_but_insufficient(self) -> None:
        """A confident forecast of too little rain does not justify a skip."""
        schedule = plan_day(
            field(depletion=60.0),
            today=TODAY,
            windows=[window()],
            forecast_etc_mm=NORMAL,
            rain=RainForecast(expected_mm=3.0, confidence=0.99),
        )
        assert schedule.decision is Decision.IRRIGATE

    def test_no_window_means_wait(self) -> None:
        """With no power there is nothing to instruct, however dry the field."""
        schedule = plan_day(field(depletion=120.0), today=TODAY, windows=[], forecast_etc_mm=NORMAL)
        assert schedule.decision is Decision.WAIT
        assert schedule.reason_code is ReasonCode.NO_WINDOW
        assert schedule.minutes == 0.0


class TestCapacityLimitBranch:
    """The branch corrected on 3 September 2026, and the reason for the correction."""

    def test_capacity_limit_fires_before_the_deficit_outgrows_the_window(self) -> None:
        """The heart of the novelty.

        A small pump on a large field: one 8-hour window delivers only a limited
        depth. The scheduler must act while the deficit is still repayable in one
        window, not after. The superseded condition ``D >= C`` would have waited
        until the deficit had already passed capacity, which is exactly too late.
        """
        # The worked example field: one 8-hour window delivers about 29 mm.
        state = field(depletion=20.0, raw=80.0, taw=150.0)
        w1 = window()
        capacity = window_capacity_mm(state, w1)

        # The precondition that makes this test meaningful: today's deficit is
        # still inside one window's capacity, so the old rule would not fire.
        assert state.depletion_mm < capacity

        # Two windows a week apart, so the projection has time to grow past it.
        w2 = PowerWindow(
            start=w1.start + dt.timedelta(days=7),
            end=w1.end + dt.timedelta(days=7),
            source=WindowSource.DECLARED_ROTATION,
        )
        schedule = plan_day(state, today=TODAY, windows=[w1, w2], forecast_etc_mm=[5.0] * 7)

        projected = state.depletion_mm + sum([5.0] * 7)
        assert projected > capacity, "projection must outgrow capacity for this branch"
        assert projected <= state.raw_mm, "must not trip the stress branch instead"

        assert schedule.decision is Decision.IRRIGATE
        assert schedule.reason_code is ReasonCode.CAPACITY_LIMIT

    def test_below_minimum_application_suppresses_the_call(self) -> None:
        """The min_app guard.

        Without it a small pump on a large field makes capacity tiny, the
        capacity branch fires almost daily, and the farmer is told to run his
        pump for a few minutes every night. That is worse than silence: it
        trains him to ignore the calls.
        """
        state = field(depletion=1.5, raw=80.0, area=20_000.0, discharge=60.0)
        w1 = window()
        w2 = PowerWindow(
            start=w1.start + dt.timedelta(days=7),
            end=w1.end + dt.timedelta(days=7),
            source=WindowSource.DECLARED_ROTATION,
        )
        schedule = plan_day(state, today=TODAY, windows=[w1, w2], forecast_etc_mm=[0.2] * 7)
        assert schedule.decision is not Decision.IRRIGATE
        assert schedule.reason_code in {ReasonCode.NO_NEED, ReasonCode.BELOW_MINIMUM}


class TestTruncationAndCarryOver:
    """A window too short to repay the deficit."""

    def test_a_long_requirement_is_truncated_to_the_window(self) -> None:
        state = field(depletion=90.0, raw=100.0, taw=150.0)
        w = window(hours=4.0)
        schedule = plan_day(state, today=TODAY, windows=[w], forecast_etc_mm=NORMAL)

        assert schedule.decision is Decision.IRRIGATE
        assert schedule.minutes == pytest.approx(w.duration_minutes)
        assert schedule.was_truncated
        assert schedule.carry_over_mm > 0.0

    def test_delivered_plus_carry_over_equals_the_requirement(self) -> None:
        state = field(depletion=90.0, raw=100.0, taw=150.0)
        schedule = plan_day(state, today=TODAY, windows=[window(hours=4.0)], forecast_etc_mm=NORMAL)
        assert schedule.delivered_mm + schedule.carry_over_mm == pytest.approx(schedule.required_mm)

    def test_the_requirement_is_the_depletion_and_nothing_else(self) -> None:
        """Carry-over is never added on top; the depletion already contains it.

        Regression test for the double count removed on 5 September 2026, which
        cost the two-season simulation 1,467 mm of water and 1,452 mm of deep
        percolation. See ``TestTruncatedRunAccounting`` for the invariant this
        protects.
        """
        state = field(depletion=20.0)
        schedule = plan_day(state, today=TODAY, windows=[window()], forecast_etc_mm=NORMAL)
        assert schedule.required_mm == pytest.approx(20.0)

    def test_a_full_window_run_leaves_no_carry_over(self) -> None:
        state = field(depletion=25.0)
        schedule = plan_day(state, today=TODAY, windows=[window()], forecast_etc_mm=NORMAL)
        assert not schedule.was_truncated
        assert schedule.carry_over_mm == pytest.approx(0.0)
        assert schedule.minutes == pytest.approx(409.4, rel=0.02)


class TestReliabilityHandling:
    """What the farmer is told when the feeder cannot be trusted."""

    def test_a_reliable_feeder_gets_a_clock_time(self) -> None:
        schedule = plan_day(
            field(depletion=60.0),
            today=TODAY,
            windows=[window(reliability=0.95)],
            forecast_etc_mm=NORMAL,
        )
        assert schedule.start_time is not None
        assert schedule.start_time.hour == 22

    def test_an_unreliable_feeder_gets_no_clock_time(self) -> None:
        """Below the threshold the call says "when power comes", not a time.

        Promising 22:00 on a feeder that honours it half the time teaches the
        farmer that the advice is unreliable. Plan Section 7.
        """
        schedule = plan_day(
            field(depletion=60.0),
            today=TODAY,
            windows=[window(reliability=0.4)],
            forecast_etc_mm=NORMAL,
        )
        assert schedule.decision is Decision.IRRIGATE
        assert schedule.start_time is None

    def test_capacity_scales_with_reliability(self) -> None:
        """An unreliable feeder is planned against what it is expected to deliver."""
        state = field()
        full = window_capacity_mm(state, window(reliability=1.0))
        half = window_capacity_mm(state, window(reliability=0.5))
        assert half == pytest.approx(full * 0.5)


class TestMultiFieldAllocation:
    """One pump, several fields, one window."""

    def test_the_most_stressed_high_ky_field_is_served_first(self) -> None:
        low = field(depletion=20.0, raw=80.0, ky=0.7, field_id="low")
        high = field(depletion=70.0, raw=80.0, ky=1.25, field_id="high")
        schedules = plan_multi_field(
            [low, high], today=TODAY, windows=[window()], forecast_etc_mm=NORMAL
        )
        assert schedules[0].field_id == "high"

    def test_the_window_is_shared_not_duplicated(self) -> None:
        """Two fields cannot both use the whole window: one pump, one window."""
        a = field(depletion=90.0, raw=100.0, field_id="a")
        b = field(depletion=85.0, raw=100.0, field_id="b")
        w = window(hours=4.0)
        schedules = plan_multi_field([a, b], today=TODAY, windows=[w], forecast_etc_mm=NORMAL)
        assert sum(s.minutes for s in schedules) <= w.duration_minutes + 1e-9

    def test_a_field_that_gets_no_minutes_carries_its_whole_requirement(self) -> None:
        """The starved field is owed the water, not denied it."""
        a = field(depletion=140.0, raw=100.0, taw=150.0, field_id="a")
        b = field(depletion=90.0, raw=100.0, taw=150.0, field_id="b")
        w = window(hours=2.0)
        schedules = plan_multi_field([a, b], today=TODAY, windows=[w], forecast_etc_mm=NORMAL)
        served, starved = schedules[0], schedules[1]
        assert served.minutes > 0.0
        if starved.minutes == 0.0:
            assert starved.carry_over_mm == pytest.approx(starved.required_mm)

    def test_no_window_means_every_field_waits(self) -> None:
        states = [field(field_id="a"), field(field_id="b")]
        schedules = plan_multi_field(states, today=TODAY, windows=[], forecast_etc_mm=NORMAL)
        assert all(s.decision is Decision.WAIT for s in schedules)
        assert all(s.reason_code is ReasonCode.NO_WINDOW for s in schedules)


class TestDeterminism:
    """No clock, no randomness, no ambient state."""

    def test_the_schedule_is_a_pure_function_of_its_arguments(self) -> None:
        state = field(depletion=55.0)
        args = {"today": TODAY, "windows": [window()], "forecast_etc_mm": NORMAL}
        assert plan_day(state, **args) == plan_day(state, **args)  # type: ignore[arg-type]

    def test_an_empty_forecast_is_rejected(self) -> None:
        """A projection needs at least one day; defaulting it would hide the error."""
        with pytest.raises(ValueError, match="at least one day"):
            plan_day(field(), today=TODAY, windows=[window()], forecast_etc_mm=[])

    def test_the_forecaster_is_recorded_on_every_schedule(self) -> None:
        """Untraceable advice is not defensible at review."""
        schedule = plan_day(
            field(depletion=60.0),
            today=TODAY,
            windows=[window()],
            forecast_etc_mm=NORMAL,
            forecaster="lstm-v2",
        )
        assert schedule.forecaster == "lstm-v2"
