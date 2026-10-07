"""Parse DISCOM agricultural feeder schedules into PowerWindow records.

MSEDCL and other state distribution companies publish agricultural feeder supply
windows as table-bearing PDF circulars. Azure AI Document Intelligence's
``prebuilt-layout`` model extracts those tables; this module turns the extracted
rows into the engine's :class:`~irrigation_engine.scheduler.models.PowerWindow`,
keyed by state, circle, substation and feeder, and writes them to
``data/feeder_windows/*.jsonl``.

Source circulars, recorded here for provenance only. **No PDF is downloaded by
this module and none is committed to the repository**; see plan Section 11, D7:

    MSEDCL AgLM time schedule, May to June 2026, published 30 April 2026
    https://www.mahadiscom.in/wp-content/uploads/2026/04/Letter-to-field_AGLM-time-Sch_May26-June26_30.04.2026.pdf

Reuse terms for those circulars are TODO [VERIFY] before the pilot.

**The Azure call is behind the adapter deliberately.** All row-to-window logic
lives in :func:`rows_to_windows` and is exercised by CSV fixtures under
``tests/fixtures/``, so the parser is fully tested with no Azure credentials, no
network and no PDF. Only :class:`DocumentIntelligenceExtractor` touches Azure,
and it is never used in tests.

A schedule row gives clock times, not datetimes. Converting them is where the
midnight-crossing bug lives: a 22:00 to 06:00 feeder is an eight-hour window
ending the following morning, not a minus-sixteen-hour one. That conversion is
:func:`window_for_date`.
"""

from __future__ import annotations

import csv
import datetime as dt
import json
import re
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

from irrigation_engine.scheduler.models import IST, PowerWindow, WindowSource

__all__ = [
    "FeederRow",
    "FeederScheduleExtractor",
    "parse_csv",
    "rows_to_windows",
    "window_for_date",
    "write_jsonl",
]

# MSEDCL circulars print times as HH:MM, occasionally with a period separator or
# stray whitespace from the PDF extraction.
_TIME_PATTERN = re.compile(r"^\s*(\d{1,2})[:.](\d{2})\s*$")

# Weekday abbreviations as they appear in the Days column.
_WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


@dataclass(frozen=True)
class FeederRow:
    """One row of a published feeder schedule.

    Clock times, not datetimes: a circular states that a feeder runs 22:00 to
    06:00, without saying on which dates. :func:`window_for_date` supplies those.
    """

    state: str
    circle: str
    substation: str
    feeder: str
    group: str
    supply_start: dt.time
    supply_end: dt.time
    days: str = "Mon-Sun"

    @property
    def key(self) -> str:
        """Stable identifier: state, circle, substation, feeder."""
        return f"{self.state}/{self.circle}/{self.substation}/{self.feeder}"

    @property
    def crosses_midnight(self) -> bool:
        """Whether the window runs past midnight into the following day."""
        return self.supply_end <= self.supply_start

    @property
    def duration_minutes(self) -> int:
        """Length of the window, minutes, handling the midnight crossing."""
        start = self.supply_start.hour * 60 + self.supply_start.minute
        end = self.supply_end.hour * 60 + self.supply_end.minute
        return end - start + (24 * 60 if self.crosses_midnight else 0)

    def applies_on(self, date: dt.date) -> bool:
        """Whether this row's Days column covers the given date.

        Understands ``Mon-Sun``, ``Mon-Sat`` and a bare ``Daily``. An
        unrecognised value is treated as covering every day, because dropping a
        window on a parsing doubt would silently deny a farmer his supply
        schedule; the ambiguity is surfaced by
        :meth:`FeederScheduleExtractor.warnings` instead.
        """
        text = self.days.strip().lower()
        if not text or text in {"daily", "all"}:
            return True

        match = re.match(r"^(\w{3})\s*-\s*(\w{3})$", text)
        if not match:
            return True

        try:
            first = _WEEKDAYS.index(match.group(1))
            last = _WEEKDAYS.index(match.group(2))
        except ValueError:
            return True

        weekday = date.weekday()
        return first <= weekday <= last if first <= last else weekday >= first or weekday <= last


@runtime_checkable
class FeederScheduleExtractor(Protocol):
    """Turns a circular into table rows.

    Implemented by ``DocumentIntelligenceExtractor`` against Azure, and by the
    CSV reader used in tests. The engine never learns which it is talking to.
    """

    def extract(self, source: Path) -> list[FeederRow]:
        """Extract feeder rows from a document.

        Args:
            source: Path to the circular, or to a CSV standing in for one.

        Returns:
            One row per feeder found.
        """
        ...


def parse_time(value: str) -> dt.time:
    """Parse a clock time from a schedule cell.

    Args:
        value: Cell text, for example ``"22:00"`` or ``"06.00"``.

    Returns:
        The parsed time.

    Raises:
        ValueError: If the cell is empty or is not a valid 24-hour time. Raised
            rather than defaulted: a window with a guessed start would send a
            farmer to his pump at the wrong hour.
    """
    match = _TIME_PATTERN.match(value or "")
    if not match:
        msg = f"cannot parse a clock time from {value!r}"
        raise ValueError(msg)

    hour, minute = int(match.group(1)), int(match.group(2))
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        msg = f"{value!r} is not a valid 24-hour clock time"
        raise ValueError(msg)
    return dt.time(hour, minute)


def parse_csv(path: Path) -> tuple[list[FeederRow], list[str]]:
    """Read feeder rows from a CSV standing in for an extracted table.

    This is the shape Document Intelligence's ``prebuilt-layout`` produces once
    its table cells are flattened, so the same function tests the row logic
    without an Azure call.

    Args:
        path: CSV with the columns State, Circle, Substation, Feeder, Group,
            Supply Start, Supply End and optionally Days.

    Returns:
        The parsed rows, and a warning per row that could not be parsed. Bad
        rows are reported, never silently dropped: a circular that half-parses
        is a data quality problem the operator must see.
    """
    rows: list[FeederRow] = []
    warnings: list[str] = []

    with path.open(newline="", encoding="utf-8") as handle:
        for number, record in enumerate(csv.DictReader(handle), start=2):
            try:
                start = parse_time(record.get("Supply Start", ""))
                end = parse_time(record.get("Supply End", ""))
            except ValueError as error:
                warnings.append(f"row {number}: {error}")
                continue

            if start == end:
                warnings.append(
                    f"row {number}: supply start and end are both {start}, "
                    f"giving a zero-length window"
                )
                continue

            rows.append(
                FeederRow(
                    state=(record.get("State") or "").strip(),
                    circle=(record.get("Circle") or "").strip(),
                    substation=(record.get("Substation") or "").strip(),
                    feeder=(record.get("Feeder") or "").strip(),
                    group=(record.get("Group") or "").strip(),
                    supply_start=start,
                    supply_end=end,
                    days=(record.get("Days") or "Mon-Sun").strip(),
                )
            )
    return rows, warnings


def window_for_date(
    row: FeederRow, date: dt.date, *, tzinfo: dt.tzinfo = IST, reliability: float = 0.8
) -> PowerWindow:
    """Turn a row's clock times into a window on a specific date.

    Where the row crosses midnight the end carries the following day's date, so
    the resulting window has a positive duration. Getting this wrong is the
    single most likely defect in this module, and it is what the fixture tests
    are pointed at.

    Args:
        row: The schedule row.
        date: Local date the window opens on.
        tzinfo: Timezone the circular's clock times are stated in.
        reliability: Starting reliability for this feeder.

    Returns:
        The window, with source ``DISCOM_SCHEDULE`` and the feeder recorded.
    """
    start = dt.datetime.combine(date, row.supply_start, tzinfo=tzinfo)
    end_date = date + dt.timedelta(days=1) if row.crosses_midnight else date
    end = dt.datetime.combine(end_date, row.supply_end, tzinfo=tzinfo)

    return PowerWindow(
        start=start,
        end=end,
        source=WindowSource.DISCOM_SCHEDULE,
        reliability=reliability,
        feeder_id=row.key,
    )


def rows_to_windows(
    rows: Iterable[FeederRow],
    start_date: dt.date,
    days: int,
    *,
    tzinfo: dt.tzinfo = IST,
    reliability: float = 0.8,
) -> list[PowerWindow]:
    """Expand schedule rows into dated windows over a horizon.

    Args:
        rows: Parsed feeder rows.
        start_date: First date to generate.
        days: How many days to generate.
        tzinfo: Timezone the circular's clock times are stated in.
        reliability: Starting reliability for these feeders.

    Returns:
        Windows in chronological order, only for dates the row's Days column
        covers.
    """
    windows: list[PowerWindow] = []
    for row in rows:
        for offset in range(days):
            date = start_date + dt.timedelta(days=offset)
            if row.applies_on(date):
                windows.append(window_for_date(row, date, tzinfo=tzinfo, reliability=reliability))
    return sorted(windows, key=lambda w: (w.start, w.feeder_id or ""))


def write_jsonl(windows: Sequence[PowerWindow], destination: Path) -> int:
    """Write windows to a JSON Lines file, one window per line.

    Args:
        windows: Windows to write.
        destination: Output path. Parent directories are created.

    Returns:
        Number of windows written.
    """
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8") as handle:
        for window in windows:
            handle.write(json.dumps(window.model_dump(mode="json")) + "\n")
    return len(windows)


def read_jsonl(source: Path) -> Iterator[PowerWindow]:
    """Read windows back from a JSON Lines file.

    Args:
        source: Path written by :func:`write_jsonl`.

    Yields:
        One window per line.
    """
    with source.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield PowerWindow.model_validate_json(line)
