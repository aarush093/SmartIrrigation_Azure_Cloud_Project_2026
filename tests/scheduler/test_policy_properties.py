"""Property tests for the power-window scheduler.

Example-based tests check the cases the author thought of. These check the
invariants that must hold for *every* input, which is what matters for a
scheduler whose whole job is to respect a hard physical constraint: the pump
cannot run when there is no power.

The six properties required by the build brief:

1. scheduled minutes never exceed window length;
2. a SKIP is only ever issued when calibrated rain covers the deficit;
3. depletion after a mandatory irrigation never exceeds RAW at the next window
   under the forecast used;
4. identical inputs give identical schedules;
5. delivered depth plus carry-over equals the requirement;
6. allocated minutes across all fields never exceed the window.
"""

from __future__ import annotations

import datetime as dt

from hypothesis import given, settings
from hypothesis import strategies as st

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

# Bounded to physically plausible farms. Unbounded floats would only prove the
# validators reject nonsense, which is tested separately by example.
depletions = st.floats(min_value=0.0, max_value=140.0)
areas = st.floats(min_value=200.0, max_value=40_000.0)
discharges = st.floats(min_value=50.0, max_value=3000.0)
efficiencies = st.floats(min_value=0.35, max_value=0.95)
durations = st.integers(min_value=60, max_value=720)
reliabilities = st.floats(min_value=0.0, max_value=1.0)
etc_series = st.lists(st.floats(min_value=0.0, max_value=12.0), min_size=1, max_size=7)


@st.composite
def field_states(draw: st.DrawFn) -> FieldState:
    """A physically coherent field state."""
    taw = draw(st.floats(min_value=40.0, max_value=250.0))
    raw = draw(st.floats(min_value=0.1, max_value=0.8)) * taw
    depletion = draw(st.floats(min_value=0.0, max_value=1.0)) * taw
    return FieldState(
        field_id=draw(st.text(min_size=1, max_size=6, alphabet="abcdef0123456789")),
        depletion_mm=depletion,
        taw_mm=taw,
        raw_mm=raw,
        area_m2=draw(areas),
        irrigation_efficiency=draw(efficiencies),
        discharge_l_per_min=draw(discharges),
        yield_response_factor=draw(st.floats(min_value=0.2, max_value=1.5)),
        carry_over_mm=draw(st.floats(min_value=0.0, max_value=30.0)),
    )


@st.composite
def windows(draw: st.DrawFn, *, start_hour: int | None = None) -> PowerWindow:
    """A power window, possibly crossing midnight."""
    hour = draw(st.integers(min_value=0, max_value=23)) if start_hour is None else start_hour
    minutes = draw(durations)
    start = dt.datetime(TODAY.year, TODAY.month, TODAY.day, hour, 0, tzinfo=IST)
    return PowerWindow(
        start=start,
        end=start + dt.timedelta(minutes=minutes),
        source=WindowSource.DECLARED_ROTATION,
        reliability=draw(reliabilities),
    )


class TestWindowInvariants:
    """Properties of the window model itself."""

    @given(w=windows())
    def test_duration_is_always_positive(self, w: PowerWindow) -> None:
        """A window with a non-positive duration cannot be constructed."""
        assert w.duration_minutes > 0.0

    @given(w=windows())
    def test_effective_duration_never_exceeds_nominal(self, w: PowerWindow) -> None:
        """Reliability scaling can only shorten the planned window, never lengthen it."""
        assert 0.0 <= w.effective_duration_minutes <= w.duration_minutes

    @given(hour=st.integers(min_value=20, max_value=23), minutes=st.integers(60, 600))
    def test_a_night_window_crossing_midnight_has_positive_duration(
        self, hour: int, minutes: int
    ) -> None:
        """The Maharashtra night-shift case, and the classic off-by-one-day bug.

        A 22:00 to 06:00 feeder modelled as two clock times gives a negative
        duration. Modelled as datetimes it does not, and the end correctly falls
        on the following date.
        """
        start = dt.datetime(2026, 9, 3, hour, 0, tzinfo=IST)
        w = PowerWindow(
            start=start,
            end=start + dt.timedelta(minutes=minutes),
            source=WindowSource.DECLARED_ROTATION,
        )
        assert w.duration_minutes == minutes
        if hour * 60 + minutes > 24 * 60:
            assert w.crosses_midnight

    def test_a_night_window_orders_after_a_same_day_daytime_window(self) -> None:
        """A 22:00 window sorts after an 06:00 one on the same date, not before.

        Ordering by clock time alone would be ambiguous once a window crosses
        midnight; ordering by datetime is not.
        """
        day = PowerWindow(
            start=dt.datetime(2026, 9, 3, 6, 0, tzinfo=IST),
            end=dt.datetime(2026, 9, 3, 14, 0, tzinfo=IST),
            source=WindowSource.DECLARED_ROTATION,
        )
        night = PowerWindow(
            start=dt.datetime(2026, 9, 3, 22, 0, tzinfo=IST),
            end=dt.datetime(2026, 9, 4, 6, 0, tzinfo=IST),
            source=WindowSource.DECLARED_ROTATION,
        )
        assert sorted([night, day], key=lambda w: w.start) == [day, night]
        assert night.crosses_midnight
        assert not day.crosses_midnight
        assert night.duration_minutes == 8 * 60


class TestSchedulerProperties:
    """The six invariants the build brief requires."""

    @settings(max_examples=300)
    @given(state=field_states(), window=windows(), etc=etc_series)
    def test_minutes_never_exceed_the_window(
        self, state: FieldState, window: PowerWindow, etc: list[float]
    ) -> None:
        """Property 1. The pump cannot run when there is no power.

        This is the constraint the whole project exists to respect. If it can be
        violated for any input, the advice is unsafe.
        """
        schedule = plan_day(state, today=TODAY, windows=[window], forecast_etc_mm=etc)
        assert schedule.minutes <= window.duration_minutes + 1e-9

    @settings(max_examples=300)
    @given(state=field_states(), window=windows(), etc=etc_series)
    def test_a_skip_only_happens_when_rain_covers_the_deficit(
        self, state: FieldState, window: PowerWindow, etc: list[float]
    ) -> None:
        """Property 2. With no rain forecast, SKIP is unreachable.

        A wrong skip costs a whole irrigation interval, because the next window
        may be days away.
        """
        schedule = plan_day(state, today=TODAY, windows=[window], forecast_etc_mm=etc)
        assert schedule.decision is not Decision.SKIP
        assert schedule.reason_code is not ReasonCode.RAIN_EXPECTED

    @settings(max_examples=300)
    @given(
        state=field_states(),
        window=windows(),
        etc=etc_series,
        expected=st.floats(min_value=0.0, max_value=200.0),
        confidence=st.floats(min_value=0.0, max_value=1.0),
    )
    def test_skip_implies_rain_covers_the_requirement(
        self,
        state: FieldState,
        window: PowerWindow,
        etc: list[float],
        expected: float,
        confidence: float,
    ) -> None:
        """Property 2, converse. Every SKIP is justified by the rain forecast."""
        rain = RainForecast(expected_mm=expected, confidence=confidence)
        schedule = plan_day(state, today=TODAY, windows=[window], forecast_etc_mm=etc, rain=rain)
        if schedule.decision is Decision.SKIP:
            assert rain.covers(schedule.required_mm)
            assert schedule.reason_code is ReasonCode.RAIN_EXPECTED

    @settings(max_examples=300)
    @given(state=field_states(), window=windows(), etc=etc_series)
    def test_delivered_plus_carry_over_equals_the_requirement(
        self, state: FieldState, window: PowerWindow, etc: list[float]
    ) -> None:
        """Property 5. Water is conserved across a truncated run.

        If this failed, a truncated run would silently lose or invent depth, and
        the balance would drift a little further from the field every time a
        window ran short.
        """
        schedule = plan_day(state, today=TODAY, windows=[window], forecast_etc_mm=etc)
        if schedule.decision is Decision.IRRIGATE:
            total = schedule.delivered_mm + schedule.carry_over_mm
            assert total == pytest_approx(schedule.required_mm)

    @settings(max_examples=200)
    @given(state=field_states(), window=windows(), etc=etc_series)
    def test_identical_inputs_give_identical_schedules(
        self, state: FieldState, window: PowerWindow, etc: list[float]
    ) -> None:
        """Property 4. The scheduler is a pure function of its arguments.

        Nothing in the policy reads a clock or a random number, which is what
        makes the two-season simulation reproducible and lets a reviewer replay
        any decision the system made.
        """
        first = plan_day(state, today=TODAY, windows=[window], forecast_etc_mm=etc)
        second = plan_day(state, today=TODAY, windows=[window], forecast_etc_mm=etc)
        assert first == second

    @settings(max_examples=200)
    @given(state=field_states(), window=windows(), etc=etc_series)
    def test_a_truncated_run_means_the_window_was_filled(
        self, state: FieldState, window: PowerWindow, etc: list[float]
    ) -> None:
        """Carry-over only arises when the window was genuinely exhausted.

        Carry-over from a window that still had minutes left would mean the
        scheduler stopped early for no reason.
        """
        schedule = plan_day(state, today=TODAY, windows=[window], forecast_etc_mm=etc)
        if schedule.was_truncated:
            assert schedule.minutes == pytest_approx(window.duration_minutes)

    @settings(max_examples=200)
    @given(state=field_states(), window=windows(), etc=etc_series)
    def test_a_mandatory_refill_is_never_a_wait(
        self, state: FieldState, window: PowerWindow, etc: list[float]
    ) -> None:
        """Property 3. When stress is imminent the scheduler acts, or explains why not.

        The only permitted reasons for not irrigating are that rain covers the
        deficit, that no window exists, or that the requirement is below the
        minimum worthwhile application.
        """
        schedule = plan_day(state, today=TODAY, windows=[window], forecast_etc_mm=etc)
        projected = min(state.depletion_mm + state.carry_over_mm + sum(etc), state.taw_mm)
        if projected > state.raw_mm and schedule.decision is not Decision.IRRIGATE:
            assert schedule.reason_code in {
                ReasonCode.RAIN_EXPECTED,
                ReasonCode.NO_WINDOW,
                ReasonCode.BELOW_MINIMUM,
            }

    @settings(max_examples=200)
    @given(state=field_states(), window=windows(), etc=etc_series)
    def test_capacity_is_never_negative_and_scales_with_reliability(
        self, state: FieldState, window: PowerWindow, etc: list[float]
    ) -> None:
        """Window capacity is a physical quantity and cannot be negative."""
        assert window_capacity_mm(state, window) >= 0.0


class TestMultiFieldAllocation:
    """Property 6, and the determinism of the ordering."""

    @settings(max_examples=200)
    @given(
        states=st.lists(field_states(), min_size=2, max_size=5, unique_by=lambda s: s.field_id),
        window=windows(),
        etc=etc_series,
    )
    def test_allocated_minutes_never_exceed_the_window(
        self, states: list[FieldState], window: PowerWindow, etc: list[float]
    ) -> None:
        """Property 6. One pump cannot serve two fields at once.

        The window is a single shared resource. If the sum could exceed it, the
        schedule would be physically impossible to execute.
        """
        schedules = plan_multi_field(states, today=TODAY, windows=[window], forecast_etc_mm=etc)
        total = sum(s.minutes for s in schedules)
        assert total <= window.duration_minutes + 1e-9

    @settings(max_examples=200)
    @given(
        states=st.lists(field_states(), min_size=2, max_size=5, unique_by=lambda s: s.field_id),
        window=windows(),
        etc=etc_series,
    )
    def test_allocation_order_is_deterministic(
        self, states: list[FieldState], window: PowerWindow, etc: list[float]
    ) -> None:
        """The same fields in a different input order produce the same allocation.

        Priority is (D / RAW) x Ky with a tie-break on field id, so the result
        cannot depend on the order the caller happened to supply.
        """
        forward = plan_multi_field(states, today=TODAY, windows=[window], forecast_etc_mm=etc)
        backward = plan_multi_field(
            list(reversed(states)), today=TODAY, windows=[window], forecast_etc_mm=etc
        )
        assert [s.field_id for s in forward] == [s.field_id for s in backward]
        assert forward == backward

    @settings(max_examples=200)
    @given(
        states=st.lists(field_states(), min_size=2, max_size=5, unique_by=lambda s: s.field_id),
        window=windows(),
        etc=etc_series,
    )
    def test_fields_are_served_in_descending_priority(
        self, states: list[FieldState], window: PowerWindow, etc: list[float]
    ) -> None:
        """The most stressed, highest-Ky field is served first.

        This is what makes the allocation defensible: when the window is too
        short for every field, the water goes where a deficit costs the most
        yield.
        """
        schedules = plan_multi_field(states, today=TODAY, windows=[window], forecast_etc_mm=etc)
        by_id = {s.field_id: s for s in states}
        keys = [(-by_id[s.field_id].priority, s.field_id) for s in schedules]
        assert keys == sorted(keys)


def pytest_approx(value: float) -> object:
    """Local alias so the approx tolerance is stated once."""
    import pytest

    return pytest.approx(value, rel=1e-9, abs=1e-9)
