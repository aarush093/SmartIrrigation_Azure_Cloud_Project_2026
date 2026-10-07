"""Forecasts **as they were issued**, from the Open-Meteo Previous Runs API.

This module exists to keep hindsight out of the simulation.

The water balance is driven by the archive, which is observed weather. If the
skip decision also read the archive it would be skipping on rain it already knew
had fallen, and the whole Objective 6 result would be worthless. The decision
must see only what a forecast issued that morning would have said.

The Previous Runs API serves exactly that: ``precipitation_previous_day1`` at
time *T* is the precipitation forecast for *T* as it stood one day earlier. So a
decision taken on day *D* about day *D + k* reads lead *k*.

**Availability, checked on 5 September 2026:**

| Variable | As-issued available? |
|---|---|
| ``precipitation`` | yes, back to at least July 2024 |
| ``et0_fao_evapotranspiration`` | yes, same range |
| ``precipitation_probability`` | **no**, null for every historical date |

The missing probability is why the skip rule cannot simply read a stored
confidence out of the archive, and why :mod:`rain_calibration` measures it
empirically from forecast-versus-observed pairs instead. That is the calibration
model's whole purpose.

Only hourly variables carry the ``_previous_dayN`` suffix; the daily aggregates
do not. Hourly values are therefore summed to local calendar days here.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

import httpx

PREVIOUS_RUNS_URL = "https://previous-runs-api.open-meteo.com/v1/forecast"

#: Lead times the scheduler actually uses. It projects to the start of the next
#: power window, which in the pilot districts is one to three days out.
LEADS = (1, 2, 3)


@dataclass(frozen=True)
class AsIssued:
    """Forecasts as they stood, keyed by (target date, lead days).

    ``rain_mm[(date, 2)]`` is the rainfall forecast for ``date`` as it stood two
    days before ``date``.
    """

    rain_mm: dict[tuple[dt.date, int], float]
    et0_mm: dict[tuple[dt.date, int], float]

    def rain_over(self, start: dt.date, days: int, issued_on: dt.date) -> float | None:
        """Total forecast rain over a horizon, as known on ``issued_on``.

        Args:
            start: First day of the horizon.
            days: Length of the horizon.
            issued_on: The day the decision is being taken.

        Returns:
            Total forecast rainfall, mm, or None if any day of the horizon has
            no as-issued forecast at the required lead.
        """
        total = 0.0
        for offset in range(days):
            target = start + dt.timedelta(days=offset)
            lead = (target - issued_on).days
            if lead < 1:
                # Today itself is not a forecast; the shortest lead served is
                # one day. Treated as no information rather than as the
                # observation, which would be hindsight.
                continue
            value = self.rain_mm.get((target, lead))
            if value is None:
                return None
            total += value
        return total

    def et0_over(self, start: dt.date, days: int, issued_on: dt.date) -> list[float] | None:
        """Forecast ET0 per day over a horizon, as known on ``issued_on``."""
        series: list[float] = []
        for offset in range(days):
            target = start + dt.timedelta(days=offset)
            lead = max(1, (target - issued_on).days)
            value = self.et0_mm.get((target, lead))
            if value is None:
                return None
            series.append(value)
        return series


def fetch_as_issued(
    latitude: float,
    longitude: float,
    start: dt.date,
    end: dt.date,
    *,
    leads: tuple[int, ...] = LEADS,
    timeout_s: float = 180.0,
) -> AsIssued:
    """Fetch as-issued rain and ET0 forecasts for a date range.

    Args:
        latitude: Site latitude.
        longitude: Site longitude.
        start: First target date.
        end: Last target date.
        leads: Lead times to fetch.
        timeout_s: Request timeout.

    Returns:
        The forecasts, keyed by target date and lead.

    Raises:
        httpx.HTTPError: On transport failure or a non-success status.
        ValueError: If the response carries no hourly block.
    """
    variables = ["precipitation", "et0_fao_evapotranspiration"]
    for lead in leads:
        variables.append(f"precipitation_previous_day{lead}")
        variables.append(f"et0_fao_evapotranspiration_previous_day{lead}")

    with httpx.Client(timeout=timeout_s) as client:
        response = client.get(
            PREVIOUS_RUNS_URL,
            params={
                "latitude": latitude,
                "longitude": longitude,
                "hourly": ",".join(variables),
                "timezone": "Asia/Kolkata",
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
            },
        )
    response.raise_for_status()
    body = response.json()
    if "hourly" not in body:
        msg = f"Previous Runs returned no hourly block: {body.get('reason', body)}"
        raise ValueError(msg)

    hourly = body["hourly"]
    stamps = [dt.datetime.fromisoformat(value) for value in hourly["time"]]

    rain: dict[tuple[dt.date, int], float] = {}
    et0: dict[tuple[dt.date, int], float] = {}
    for lead in leads:
        _accumulate(rain, stamps, hourly.get(f"precipitation_previous_day{lead}"), lead)
        _accumulate(
            et0, stamps, hourly.get(f"et0_fao_evapotranspiration_previous_day{lead}"), lead
        )

    return AsIssued(rain_mm=rain, et0_mm=et0)


def _accumulate(
    into: dict[tuple[dt.date, int], float],
    stamps: list[dt.datetime],
    values: list[float | None] | None,
    lead: int,
) -> None:
    """Sum an hourly series into local calendar days.

    A day is included only if every one of its hours is present. A partial day
    would understate the forecast total and, for rain, would bias the skip rule
    toward irrigating, which is the safe direction but still a silent error.
    """
    if not values:
        return

    totals: dict[dt.date, float] = {}
    counts: dict[dt.date, int] = {}
    for stamp, value in zip(stamps, values, strict=False):
        if value is None:
            continue
        day = stamp.date()
        totals[day] = totals.get(day, 0.0) + float(value)
        counts[day] = counts.get(day, 0) + 1

    for day, total in totals.items():
        if counts[day] >= 24:
            into[(day, lead)] = total
