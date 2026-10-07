"""Where power windows come from.

Three sources, in precedence order (plan Section 7):

1. What the farmer reported today. A POWER_FAILED missed call is a direct
   observation of the feeder and beats any published schedule.
2. The DISCOM published schedule, parsed from circular PDFs.
3. The farmer's declared rotation, "day shift this week, night next week".

The declared rotation is the fallback that makes onboarding possible in a
district whose DISCOM publishes nothing, which is most of them.
"""

from __future__ import annotations

import datetime as dt
from typing import Protocol, runtime_checkable

from irrigation_engine.params import load_params
from irrigation_engine.scheduler.models import IST, PowerWindow, WindowSource

__all__ = [
    "DeclaredRotation",
    "DiscomSchedule",
    "ScheduleSource",
    "apply_precedence",
    "update_reliability",
]


@runtime_checkable
class ScheduleSource(Protocol):
    """Supplies the power windows expected for a field over a horizon."""

    def windows(self, start: dt.datetime, days: int) -> list[PowerWindow]:
        """Return windows opening within ``days`` of ``start``, chronologically.

        Args:
            start: Timezone-aware instant to plan from.
            days: How many days ahead to enumerate.

        Returns:
            Windows in chronological order of their start.
        """
        ...


class DeclaredRotation:
    """Windows from a farmer-declared day/night rotation.

    The common case in the pilot: the farmer knows he gets day supply one week
    and night supply the next, on a fixed rotation length, and can say so at
    onboarding without anyone consulting a circular.

    Night windows crossing midnight are constructed with the following day's
    date on their end, which is the whole reason windows are datetimes.
    """

    def __init__(
        self,
        *,
        day_start: dt.time,
        day_end: dt.time,
        night_start: dt.time,
        night_end: dt.time,
        rotation_days: int,
        anchor_date: dt.date,
        anchor_is_day_shift: bool = True,
        reliability: float = 0.8,
        tzinfo: dt.tzinfo = IST,
    ) -> None:
        """Configure the rotation.

        Args:
            day_start: Clock time the day window opens.
            day_end: Clock time the day window closes, later than ``day_start``.
            night_start: Clock time the night window opens.
            night_end: Clock time the night window closes, normally the next
                morning and therefore earlier than ``night_start``.
            rotation_days: Length of one shift block, days.
            anchor_date: A date whose shift is known.
            anchor_is_day_shift: Whether ``anchor_date`` falls in a day block.
            reliability: Starting reliability for this feeder.
            tzinfo: Timezone the clock times are expressed in.

        Raises:
            ValueError: If the rotation length is not positive, or the day
                window does not have positive length.
        """
        if rotation_days <= 0:
            msg = f"rotation length must be positive, got {rotation_days} days"
            raise ValueError(msg)
        if day_end <= day_start:
            msg = (
                f"day window {day_start} to {day_end} does not have positive length. "
                f"A day window that appears to end before it starts is a night window."
            )
            raise ValueError(msg)

        self.day_start = day_start
        self.day_end = day_end
        self.night_start = night_start
        self.night_end = night_end
        self.rotation_days = rotation_days
        self.anchor_date = anchor_date
        self.anchor_is_day_shift = anchor_is_day_shift
        self.reliability = reliability
        self.tzinfo = tzinfo

    def is_day_shift(self, date: dt.date) -> bool:
        """Whether the feeder is on day supply on a given date.

        Uses floor division so the rotation extends correctly backwards from the
        anchor as well as forwards.
        """
        blocks = (date - self.anchor_date).days // self.rotation_days
        return self.anchor_is_day_shift if blocks % 2 == 0 else not self.anchor_is_day_shift

    def window_for(self, date: dt.date) -> PowerWindow:
        """Build the window for one date.

        Args:
            date: Local calendar date the window opens on.

        Returns:
            The day or night window for that date. A night window carries the
            following day's date on its end.
        """
        if self.is_day_shift(date):
            start = dt.datetime.combine(date, self.day_start, tzinfo=self.tzinfo)
            end = dt.datetime.combine(date, self.day_end, tzinfo=self.tzinfo)
        else:
            start = dt.datetime.combine(date, self.night_start, tzinfo=self.tzinfo)
            end_date = date if self.night_end > self.night_start else date + dt.timedelta(days=1)
            end = dt.datetime.combine(end_date, self.night_end, tzinfo=self.tzinfo)

        return PowerWindow(
            start=start,
            end=end,
            source=WindowSource.DECLARED_ROTATION,
            reliability=self.reliability,
        )

    def windows(self, start: dt.datetime, days: int) -> list[PowerWindow]:
        """Enumerate windows opening within ``days`` of ``start``.

        Args:
            start: Timezone-aware instant to plan from.
            days: How many days ahead to enumerate.

        Returns:
            Windows opening at or after ``start``, chronologically.
        """
        local = start.astimezone(self.tzinfo)
        candidates = [
            self.window_for(local.date() + dt.timedelta(days=offset))
            for offset in range(-1, days + 1)
        ]
        return sorted(
            (w for w in candidates if w.start >= start),
            key=lambda w: w.start,
        )[:days]


class DiscomSchedule:
    """Windows from rows parsed out of a DISCOM published schedule.

    Rows normally arrive from ``src/azure/document_intelligence`` having been
    extracted from a circular PDF. This class holds them and answers the
    ``ScheduleSource`` protocol; it neither downloads nor parses anything.
    """

    def __init__(self, windows: list[PowerWindow]) -> None:
        """Store the parsed windows.

        Args:
            windows: Windows for one feeder, in any order.
        """
        self._windows = sorted(windows, key=lambda w: w.start)

    def windows(self, start: dt.datetime, days: int) -> list[PowerWindow]:
        """Return stored windows opening within the horizon.

        Args:
            start: Timezone-aware instant to plan from.
            days: How many days ahead to enumerate.

        Returns:
            Windows opening at or after ``start`` and before the horizon ends.
        """
        end = start + dt.timedelta(days=days)
        return [w for w in self._windows if start <= w.start < end]


def apply_precedence(
    *,
    farmer_reported: list[PowerWindow] | None = None,
    discom: list[PowerWindow] | None = None,
    declared: list[PowerWindow] | None = None,
) -> list[PowerWindow]:
    """Resolve windows from several sources by precedence.

    Precedence, from plan Section 7: what the farmer reported today, then the
    DISCOM published schedule, then the declared rotation. A lower-precedence
    window is dropped when a higher-precedence one already covers the same local
    date, rather than merged: two sources disagreeing about one day means one of
    them is wrong, and the more trusted one wins outright.

    Args:
        farmer_reported: Windows derived from today's farmer reports.
        discom: Windows from the published schedule.
        declared: Windows from the declared rotation.

    Returns:
        One window per covered date, chronologically.
    """
    resolved: dict[dt.date, PowerWindow] = {}
    for tier in (declared or [], discom or [], farmer_reported or []):
        for window in tier:
            resolved[window.start.date()] = window
    return sorted(resolved.values(), key=lambda w: w.start)


def update_reliability(previous: float, power_arrived: bool) -> float:
    """Update a feeder's reliability from one observed window.

    ``r_new = alpha * outcome + (1 - alpha) * r_old``, where outcome is 0 when a
    POWER_FAILED missed call arrived for the window and 1 otherwise. Constants
    live in ``params/scheduling.yaml``.

    There is no other sensor. The missed call is the measurement.

    Args:
        previous: Reliability before this observation, 0 to 1.
        power_arrived: Whether the window carried power.

    Returns:
        Updated reliability, 0 to 1.

    Raises:
        ValueError: If ``previous`` is outside 0 to 1.
    """
    if not 0.0 <= previous <= 1.0:
        msg = f"reliability must lie between 0 and 1, got {previous}"
        raise ValueError(msg)
    alpha = float(load_params("scheduling")["reliability"]["alpha"])
    return alpha * (1.0 if power_arrived else 0.0) + (1.0 - alpha) * previous
