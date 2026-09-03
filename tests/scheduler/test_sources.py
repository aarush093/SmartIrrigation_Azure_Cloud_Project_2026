"""Tests for window sources, precedence and feeder reliability."""

from __future__ import annotations

import datetime as dt

import pytest

from irrigation_engine.scheduler import (
    IST,
    DeclaredRotation,
    DiscomSchedule,
    PowerWindow,
    ScheduleSource,
    WindowSource,
    apply_precedence,
    update_reliability,
)

ANCHOR = dt.date(2026, 9, 1)


def rotation(**overrides: object) -> DeclaredRotation:
    """A weekly day/night rotation matching the Beed pilot description."""
    kwargs: dict[str, object] = {
        "day_start": dt.time(7, 30),
        "day_end": dt.time(15, 30),
        "night_start": dt.time(22, 0),
        "night_end": dt.time(6, 0),
        "rotation_days": 7,
        "anchor_date": ANCHOR,
        "anchor_is_day_shift": True,
    }
    kwargs.update(overrides)
    return DeclaredRotation(**kwargs)  # type: ignore[arg-type]


class TestDeclaredRotation:
    """The fallback that makes onboarding possible where no circular is published."""

    def test_it_satisfies_the_protocol(self) -> None:
        assert isinstance(rotation(), ScheduleSource)

    def test_the_anchor_week_is_the_day_shift(self) -> None:
        assert rotation().is_day_shift(ANCHOR)

    def test_the_shift_flips_after_the_rotation_length(self) -> None:
        """Seven days on, seven days off."""
        source = rotation()
        assert source.is_day_shift(ANCHOR + dt.timedelta(days=6))
        assert not source.is_day_shift(ANCHOR + dt.timedelta(days=7))
        assert source.is_day_shift(ANCHOR + dt.timedelta(days=14))

    def test_the_rotation_extends_backwards_from_the_anchor(self) -> None:
        """Floor division, so a date before the anchor is placed correctly.

        Integer division truncating toward zero would put the day before the
        anchor in the same block as the day after it.
        """
        source = rotation()
        assert not source.is_day_shift(ANCHOR - dt.timedelta(days=1))
        assert source.is_day_shift(ANCHOR - dt.timedelta(days=14))

    def test_a_day_window_does_not_cross_midnight(self) -> None:
        window = rotation().window_for(ANCHOR)
        assert not window.crosses_midnight
        assert window.duration_minutes == 8 * 60

    def test_a_night_window_carries_the_next_days_date(self) -> None:
        """The Maharashtra night feeder, and the reason windows are datetimes.

        22:00 to 06:00 is eight hours, not minus sixteen. Building it from two
        clock times on one date would give the wrong sign.
        """
        window = rotation().window_for(ANCHOR + dt.timedelta(days=7))
        assert window.crosses_midnight
        assert window.start.hour == 22
        assert window.end.hour == 6
        assert window.end.date() == window.start.date() + dt.timedelta(days=1)
        assert window.duration_minutes == 8 * 60

    def test_windows_are_returned_in_chronological_order(self) -> None:
        start = dt.datetime(2026, 9, 1, 0, 0, tzinfo=IST)
        produced = rotation().windows(start, days=10)
        assert produced == sorted(produced, key=lambda w: w.start)
        assert len(produced) == 10

    def test_windows_never_start_before_the_planning_instant(self) -> None:
        """A window that has already opened cannot be scheduled into."""
        start = dt.datetime(2026, 9, 1, 12, 0, tzinfo=IST)
        for window in rotation().windows(start, days=5):
            assert window.start >= start

    def test_windows_are_tagged_with_their_source(self) -> None:
        assert rotation().window_for(ANCHOR).source is WindowSource.DECLARED_ROTATION

    def test_a_non_positive_rotation_length_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="rotation length"):
            rotation(rotation_days=0)

    def test_an_inverted_day_window_is_rejected(self) -> None:
        """A day window ending before it starts is a night window, mislabelled."""
        with pytest.raises(ValueError, match="positive length"):
            rotation(day_start=dt.time(15, 0), day_end=dt.time(7, 0))


class TestDiscomSchedule:
    """Rows parsed out of a published circular."""

    @staticmethod
    def _windows() -> list[PowerWindow]:
        return [
            PowerWindow(
                start=dt.datetime(2026, 9, day, 6, 0, tzinfo=IST),
                end=dt.datetime(2026, 9, day, 14, 0, tzinfo=IST),
                source=WindowSource.DISCOM_SCHEDULE,
                feeder_id="BEED-11KV-07",
            )
            for day in range(1, 8)
        ]

    def test_it_satisfies_the_protocol(self) -> None:
        assert isinstance(DiscomSchedule(self._windows()), ScheduleSource)

    def test_it_returns_windows_inside_the_horizon_only(self) -> None:
        source = DiscomSchedule(self._windows())
        selected = source.windows(dt.datetime(2026, 9, 2, 0, 0, tzinfo=IST), days=3)
        assert [w.start.day for w in selected] == [2, 3, 4]

    def test_unsorted_input_is_returned_in_order(self) -> None:
        """A parsed table need not arrive in date order."""
        shuffled = list(reversed(self._windows()))
        source = DiscomSchedule(shuffled)
        selected = source.windows(dt.datetime(2026, 9, 1, 0, 0, tzinfo=IST), days=7)
        assert selected == sorted(selected, key=lambda w: w.start)


class TestPrecedence:
    """Farmer report beats DISCOM schedule beats declared rotation. Plan Section 7."""

    @staticmethod
    def _window(hour: int, source: WindowSource) -> PowerWindow:
        """A four-hour window opening at the given hour.

        Built with a timedelta rather than by adding to the hour field, so a
        20:00 start correctly rolls into the next day rather than raising.
        """
        start = dt.datetime(2026, 9, 3, hour, 0, tzinfo=IST)
        return PowerWindow(start=start, end=start + dt.timedelta(hours=4), source=source)

    def test_the_farmer_report_wins(self) -> None:
        """A farmer reporting the feeder's actual behaviour beats any document."""
        resolved = apply_precedence(
            farmer_reported=[self._window(20, WindowSource.FARMER_REPORT)],
            discom=[self._window(10, WindowSource.DISCOM_SCHEDULE)],
            declared=[self._window(6, WindowSource.DECLARED_ROTATION)],
        )
        assert len(resolved) == 1
        assert resolved[0].source is WindowSource.FARMER_REPORT

    def test_discom_beats_the_declared_rotation(self) -> None:
        resolved = apply_precedence(
            discom=[self._window(10, WindowSource.DISCOM_SCHEDULE)],
            declared=[self._window(6, WindowSource.DECLARED_ROTATION)],
        )
        assert resolved[0].source is WindowSource.DISCOM_SCHEDULE

    def test_the_rotation_fills_dates_no_higher_source_covers(self) -> None:
        """Precedence is per date: a report about Thursday says nothing about Friday."""
        declared = [
            PowerWindow(
                start=dt.datetime(2026, 9, day, 6, 0, tzinfo=IST),
                end=dt.datetime(2026, 9, day, 14, 0, tzinfo=IST),
                source=WindowSource.DECLARED_ROTATION,
            )
            for day in (3, 4, 5)
        ]
        resolved = apply_precedence(
            farmer_reported=[self._window(20, WindowSource.FARMER_REPORT)], declared=declared
        )
        assert len(resolved) == 3
        assert resolved[0].source is WindowSource.FARMER_REPORT
        assert {w.source for w in resolved[1:]} == {WindowSource.DECLARED_ROTATION}

    def test_no_sources_gives_no_windows(self) -> None:
        assert apply_precedence() == []


class TestReliability:
    """Learned from missed calls. There is no other sensor."""

    def test_a_successful_window_raises_reliability(self) -> None:
        assert update_reliability(0.8, power_arrived=True) == pytest.approx(0.86)

    def test_a_failed_window_lowers_reliability(self) -> None:
        """Alpha 0.3: one failure takes a fresh feeder from 0.80 to 0.56."""
        assert update_reliability(0.8, power_arrived=False) == pytest.approx(0.56)

    def test_one_failure_crosses_the_low_reliability_threshold(self) -> None:
        """Deliberately fast to react.

        Telling a farmer "when power comes" one day too early is a smaller error
        than giving him a clock time the feeder will not honour.
        """
        assert update_reliability(0.8, power_arrived=False) < 0.6

    def test_reliability_stays_within_bounds(self) -> None:
        value = 0.8
        for _ in range(50):
            value = update_reliability(value, power_arrived=False)
            assert 0.0 <= value <= 1.0
        for _ in range(50):
            value = update_reliability(value, power_arrived=True)
            assert 0.0 <= value <= 1.0

    def test_repeated_success_approaches_but_never_exceeds_one(self) -> None:
        value = 0.5
        for _ in range(200):
            value = update_reliability(value, power_arrived=True)
        assert 0.99 < value <= 1.0

    def test_an_out_of_range_previous_value_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="reliability"):
            update_reliability(1.5, power_arrived=True)
