"""Tests for the DISCOM feeder schedule parser.

Driven entirely by hand-made CSV fixtures under ``tests/fixtures/``, which
reproduce the table shape Azure AI Document Intelligence produces from an MSEDCL
circular once its cells are flattened. No PDF is downloaded, none is committed,
and no Azure call is made.

The fixtures deliberately include the two night feeders (22:00 to 06:00 and
23:30 to 07:30) that make midnight crossing the interesting case, and a
malformed file whose bad rows must be reported rather than silently dropped.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest

from document_intelligence.parse_feeder_schedule import (
    FeederRow,
    parse_csv,
    parse_time,
    read_jsonl,
    rows_to_windows,
    window_for_date,
    write_jsonl,
)
from irrigation_engine.scheduler.models import IST, WindowSource

MONDAY = dt.date(2026, 9, 7)


@pytest.fixture
def schedule_rows(fixtures_dir: Path) -> list[FeederRow]:
    """The well-formed MSEDCL-shaped fixture."""
    rows, warnings = parse_csv(fixtures_dir / "msedcl_aglm_schedule.csv")
    assert not warnings
    return list(rows)


class TestTimeParsing:
    """Clock times as they arrive from a PDF extraction."""

    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("06:00", dt.time(6, 0)),
            ("22:00", dt.time(22, 0)),
            ("23:30", dt.time(23, 30)),
            ("6:00", dt.time(6, 0)),
            ("06.00", dt.time(6, 0)),
            ("  14:00  ", dt.time(14, 0)),
        ],
    )
    def test_valid_times_parse(self, text: str, expected: dt.time) -> None:
        assert parse_time(text) == expected

    @pytest.mark.parametrize("text", ["", "   ", "25:00", "12:60", "noon", "12", "-1:00"])
    def test_invalid_times_raise(self, text: str) -> None:
        """A bad cell raises rather than defaulting.

        A window with a guessed start would send a farmer to his pump at the
        wrong hour, which is worse than no schedule at all.
        """
        with pytest.raises(ValueError, match="clock time"):
            parse_time(text)


class TestCsvParsing:
    """Reading the flattened table."""

    def test_all_well_formed_rows_are_parsed(self, schedule_rows: list[FeederRow]) -> None:
        assert len(schedule_rows) == 6

    def test_the_key_identifies_state_circle_substation_and_feeder(
        self, schedule_rows: list[FeederRow]
    ) -> None:
        """Plan Section 7: windows are keyed by state, circle, substation, feeder."""
        assert schedule_rows[0].key == "Maharashtra/Beed/BEED-33/11KV-A/AG-FDR-07"

    def test_day_and_night_feeders_are_both_read(self, schedule_rows: list[FeederRow]) -> None:
        crossing = [r for r in schedule_rows if r.crosses_midnight]
        assert {r.feeder for r in crossing} == {"AG-FDR-11", "AG-FDR-12", "AG-FDR-22"}

    def test_every_window_is_eight_hours(self, schedule_rows: list[FeederRow]) -> None:
        """MSEDCL's April 2026 circular fixes 8-hour agricultural supply.

        Including the two night feeders, which is the assertion that would fail
        if the midnight crossing were mishandled.
        """
        for row in schedule_rows:
            assert row.duration_minutes == 8 * 60, f"{row.feeder} is not 8 hours"

    def test_malformed_rows_are_reported_not_dropped(self, fixtures_dir: Path) -> None:
        """A circular that half-parses is a data quality problem the operator must see."""
        rows, warnings = parse_csv(fixtures_dir / "msedcl_aglm_malformed.csv")
        assert len(rows) == 1
        assert len(warnings) == 3
        assert any("cannot parse" in w for w in warnings)
        assert any("zero-length" in w for w in warnings)

    def test_a_zero_length_window_is_rejected(self, fixtures_dir: Path) -> None:
        """08:00 to 08:00 is not a 24-hour window, it is a bad row."""
        _, warnings = parse_csv(fixtures_dir / "msedcl_aglm_malformed.csv")
        assert any("zero-length" in w for w in warnings)


class TestMidnightCrossing:
    """The defect this module is most likely to have."""

    def test_a_night_row_produces_a_window_ending_the_next_day(
        self, schedule_rows: list[FeederRow]
    ) -> None:
        row = next(r for r in schedule_rows if r.feeder == "AG-FDR-11")
        window = window_for_date(row, MONDAY)

        assert window.start.hour == 22
        assert window.start.date() == MONDAY
        assert window.end.hour == 6
        assert window.end.date() == MONDAY + dt.timedelta(days=1)
        assert window.duration_minutes == 8 * 60
        assert window.crosses_midnight

    def test_a_late_night_row_crosses_correctly(self, schedule_rows: list[FeederRow]) -> None:
        """23:30 to 07:30 is eight hours across the boundary."""
        row = next(r for r in schedule_rows if r.feeder == "AG-FDR-12")
        window = window_for_date(row, MONDAY)
        assert window.duration_minutes == 8 * 60
        assert window.crosses_midnight

    def test_a_day_row_does_not_cross(self, schedule_rows: list[FeederRow]) -> None:
        row = next(r for r in schedule_rows if r.feeder == "AG-FDR-07")
        window = window_for_date(row, MONDAY)
        assert not window.crosses_midnight
        assert window.start.date() == window.end.date()

    def test_windows_carry_the_ist_offset(self, schedule_rows: list[FeederRow]) -> None:
        """A naive datetime would assume the server's timezone, not the field's."""
        window = window_for_date(schedule_rows[0], MONDAY)
        assert window.start.tzinfo is IST
        assert window.start.utcoffset() == dt.timedelta(hours=5, minutes=30)

    def test_windows_are_tagged_as_discom_sourced(self, schedule_rows: list[FeederRow]) -> None:
        """Source drives precedence, so it must be recorded."""
        window = window_for_date(schedule_rows[0], MONDAY)
        assert window.source is WindowSource.DISCOM_SCHEDULE
        assert window.feeder_id == schedule_rows[0].key


class TestDayOfWeekFiltering:
    """The Days column."""

    def test_a_mon_sun_row_applies_every_day(self, schedule_rows: list[FeederRow]) -> None:
        row = next(r for r in schedule_rows if r.feeder == "AG-FDR-07")
        for offset in range(7):
            assert row.applies_on(MONDAY + dt.timedelta(days=offset))

    def test_a_mon_sat_row_skips_sunday(self, schedule_rows: list[FeederRow]) -> None:
        row = next(r for r in schedule_rows if r.feeder == "AG-FDR-21")
        assert row.applies_on(MONDAY)
        assert not row.applies_on(MONDAY + dt.timedelta(days=6))

    def test_an_unrecognised_days_value_covers_everything(self) -> None:
        """Ambiguity does not silently deny a farmer his schedule.

        Dropping a window because the Days cell was not understood would leave
        the farmer with no advice at all; the parser surfaces the doubt as a
        warning instead and keeps the window.
        """
        row = FeederRow(
            state="MH",
            circle="Beed",
            substation="S1",
            feeder="F1",
            group="A",
            supply_start=dt.time(6, 0),
            supply_end=dt.time(14, 0),
            days="alternate days",
        )
        assert row.applies_on(MONDAY)


class TestExpansionAndRoundTrip:
    """From rows to a horizon of windows, and back off disk."""

    def test_rows_expand_over_the_horizon_in_order(self, schedule_rows: list[FeederRow]) -> None:
        windows = rows_to_windows(schedule_rows, MONDAY, days=3)
        assert windows == sorted(windows, key=lambda w: (w.start, w.feeder_id or ""))
        # Four Mon-Sun feeders over three days, plus two Mon-Sat feeders over
        # three days that are all weekdays here.
        assert len(windows) == 18

    def test_every_expanded_window_has_positive_duration(
        self, schedule_rows: list[FeederRow]
    ) -> None:
        for window in rows_to_windows(schedule_rows, MONDAY, days=7):
            assert window.duration_minutes > 0

    def test_a_mon_sat_feeder_is_absent_on_sunday(self, schedule_rows: list[FeederRow]) -> None:
        sunday = MONDAY + dt.timedelta(days=6)
        windows = rows_to_windows(schedule_rows, sunday, days=1)
        assert not any(w.feeder_id and "AG-FDR-21" in w.feeder_id for w in windows)

    def test_windows_round_trip_through_jsonl(
        self, schedule_rows: list[FeederRow], tmp_path: Path
    ) -> None:
        """The on-disk format the ingestion pipeline writes to data/feeder_windows/."""
        windows = rows_to_windows(schedule_rows, MONDAY, days=2)
        destination = tmp_path / "feeder_windows" / "beed.jsonl"

        assert write_jsonl(windows, destination) == len(windows)
        assert list(read_jsonl(destination)) == windows

    def test_a_night_window_survives_the_round_trip(
        self, schedule_rows: list[FeederRow], tmp_path: Path
    ) -> None:
        """Serialisation must not lose the date or the offset."""
        row = next(r for r in schedule_rows if r.feeder == "AG-FDR-11")
        original = window_for_date(row, MONDAY)
        destination = tmp_path / "one.jsonl"
        write_jsonl([original], destination)

        restored = next(iter(read_jsonl(destination)))
        assert restored.duration_minutes == 8 * 60
        assert restored.crosses_midnight
        assert restored.start == original.start
        assert restored.end == original.end
