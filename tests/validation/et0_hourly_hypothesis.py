"""Test the hourly-versus-daily hypothesis for the Objective 2 residual.

The M1 cross-check left a residual of 0.279 mm/day MAE between this project's
daily-aggregate ET0 and Open-Meteo's published daily ET0, with near-zero bias.
The stated suspicion was that Open-Meteo integrates FAO-56 hourly (equation 53)
and sums to a daily total, while this engine computes from daily aggregates
(equation 6). FAO-56 sanctions both and they need not agree.

This settles the question rather than leaving it as a suspicion. One month of
hourly archive data for Beed is pulled, and three series are compared against
Open-Meteo's published daily ET0:

    A. our daily-aggregate ET0   (FAO-56 equation 6)
    B. our hourly-summed ET0     (FAO-56 equation 53, summed over 24 hours)

If B lands inside the 0.2 mm/day tolerance while A does not, the hypothesis is
proven. If it does not close the gap, the hypothesis is dead and the report says
so.

One month is enough to settle it. The full validation is not extended to hourly
unless this proves it.

Marked ``integration``; run with ``make validate-hourly``.
"""

from __future__ import annotations

import csv
import datetime as dt
import math
import zoneinfo
from pathlib import Path

import httpx
import pytest

from irrigation_engine.et0 import penman_monteith
from irrigation_engine.et0_hourly import HourlyWeather, daily_from_hourly

TOLERANCE_MM = 0.2
IST = zoneinfo.ZoneInfo("Asia/Kolkata")

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
RESULTS_PATH = Path(__file__).resolve().parents[2] / "results" / "objective2_hourly_hypothesis.csv"

# Beed, Maharashtra. Chosen because its daily-aggregate comparison was unbiased
# (-0.013 mm/day) with the largest scatter (MAE 0.308), so it isolates the
# scatter the hypothesis is meant to explain.
SITE_NAME = "Beed MH"
LATITUDE = 18.99
LONGITUDE = 75.76

# One month in the dry season, when ET0 is high and a proportional error is
# largest in absolute terms.
START_DATE = dt.date(2025, 4, 1)
END_DATE = dt.date(2025, 4, 30)

HOURLY_VARIABLES = (
    "temperature_2m",
    "relative_humidity_2m",
    "wind_speed_10m",
    "shortwave_radiation",
)
DAILY_VARIABLES = (
    "et0_fao_evapotranspiration",
    "temperature_2m_max",
    "temperature_2m_min",
    "relative_humidity_2m_max",
    "relative_humidity_2m_min",
    "wind_speed_10m_mean",
    "shortwave_radiation_sum",
)


def wind_10m_to_2m(speed_10m: float) -> float:
    """FAO-56 equation 47, for a measurement height of 10 m."""
    return speed_10m * 4.87 / math.log(67.8 * 10.0 - 5.42)


def fetch() -> dict[str, object]:
    """Pull the hourly and daily blocks for the month in one request."""
    with httpx.Client(timeout=90.0) as client:
        response = client.get(
            ARCHIVE_URL,
            params={
                "latitude": LATITUDE,
                "longitude": LONGITUDE,
                "hourly": ",".join(HOURLY_VARIABLES),
                "daily": ",".join(DAILY_VARIABLES),
                "timezone": "Asia/Kolkata",
                "start_date": START_DATE.isoformat(),
                "end_date": END_DATE.isoformat(),
            },
        )
    response.raise_for_status()
    body: dict[str, object] = response.json()
    return body


def build_hours(body: dict[str, object]) -> list[HourlyWeather]:
    """Convert the hourly block into engine records, in engine units."""
    hourly = body["hourly"]
    assert isinstance(hourly, dict)

    hours: list[HourlyWeather] = []
    for index, stamp in enumerate(hourly["time"]):
        temp = hourly["temperature_2m"][index]
        rh = hourly["relative_humidity_2m"][index]
        wind = hourly["wind_speed_10m"][index]
        radiation = hourly["shortwave_radiation"][index]
        if None in (temp, rh, wind, radiation):
            continue
        hours.append(
            HourlyWeather(
                timestamp=dt.datetime.fromisoformat(stamp).replace(tzinfo=IST),
                temp_c=float(temp),
                relative_humidity=float(rh),
                # km/h at 10 m to m/s at 2 m.
                wind_speed_2m=wind_10m_to_2m(float(wind) / 3.6),
                # W/m2 over one hour to MJ/m2/hour.
                solar_radiation_mj=float(radiation) * 3600.0 / 1e6,
            )
        )
    return hours


def build_daily(body: dict[str, object], elevation_m: float) -> dict[dt.date, tuple[float, float]]:
    """Compute our daily-aggregate ET0 and read Open-Meteo's published value."""
    daily = body["daily"]
    assert isinstance(daily, dict)

    results: dict[dt.date, tuple[float, float]] = {}
    for index, day in enumerate(daily["time"]):
        published = daily["et0_fao_evapotranspiration"][index]
        t_max = daily["temperature_2m_max"][index]
        t_min = daily["temperature_2m_min"][index]
        if published is None or t_max is None or t_min is None:
            continue

        wind = daily["wind_speed_10m_mean"][index]
        ours = penman_monteith(
            temp_max_c=float(t_max),
            temp_min_c=float(t_min),
            latitude=LATITUDE,
            date=dt.date.fromisoformat(day),
            elevation_m=elevation_m,
            wind_speed_2m=None if wind is None else wind_10m_to_2m(float(wind) / 3.6),
            relative_humidity_max=(
                None
                if daily["relative_humidity_2m_max"][index] is None
                else float(daily["relative_humidity_2m_max"][index])
            ),
            relative_humidity_min=(
                None
                if daily["relative_humidity_2m_min"][index] is None
                else float(daily["relative_humidity_2m_min"][index])
            ),
            solar_radiation_mj=(
                None
                if daily["shortwave_radiation_sum"][index] is None
                else float(daily["shortwave_radiation_sum"][index])
            ),
        )
        results[dt.date.fromisoformat(day)] = (ours, float(published))
    return results


def statistics(differences: list[float]) -> tuple[float, float, float, float]:
    """Return MAE, RMSE, bias and the within-tolerance fraction."""
    n = len(differences)
    mae = sum(abs(d) for d in differences) / n
    rmse = math.sqrt(sum(d * d for d in differences) / n)
    bias = sum(differences) / n
    within = sum(1 for d in differences if abs(d) <= TOLERANCE_MM) / n
    return mae, rmse, bias, within


@pytest.mark.integration
def test_hourly_versus_daily_hypothesis() -> None:
    """Compare daily-aggregate and hourly-summed ET0 against the published value."""
    body = fetch()
    elevation_m = float(body.get("elevation", 515.0))  # type: ignore[arg-type]

    hours = build_hours(body)
    hourly_totals = daily_from_hourly(
        hours, latitude=LATITUDE, longitude=LONGITUDE, elevation_m=elevation_m
    )
    daily_pairs = build_daily(body, elevation_m)

    rows: list[tuple[dt.date, float, float, float]] = []
    for day in sorted(daily_pairs):
        if day not in hourly_totals:
            continue
        ours_daily, published = daily_pairs[day]
        rows.append((day, ours_daily, hourly_totals[day], published))

    assert rows, "no overlapping days between the hourly and daily blocks"

    daily_diff = [r[1] - r[3] for r in rows]
    hourly_diff = [r[2] - r[3] for r in rows]

    daily_stats = statistics(daily_diff)
    hourly_stats = statistics(hourly_diff)

    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with RESULTS_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["# Objective 2: hourly-versus-daily hypothesis"])
        writer.writerow([f"# {SITE_NAME}, {START_DATE} to {END_DATE}"])
        writer.writerow(["# A = our FAO-56 eq 6 from daily aggregates"])
        writer.writerow(["# B = our FAO-56 eq 53 summed over 24 hours"])
        writer.writerow(["# reference = Open-Meteo published et0_fao_evapotranspiration"])
        writer.writerow([])
        writer.writerow(["series", "n", "mae_mm", "rmse_mm", "bias_mm", "within_0.2"])
        for label, stats in (("A daily-aggregate", daily_stats), ("B hourly-summed", hourly_stats)):
            writer.writerow(
                [
                    label,
                    len(rows),
                    f"{stats[0]:.4f}",
                    f"{stats[1]:.4f}",
                    f"{stats[2]:.4f}",
                    f"{stats[3]:.4f}",
                ]
            )
        writer.writerow([])
        writer.writerow(["date", "et0_daily_aggregate", "et0_hourly_sum", "et0_openmeteo"])
        for day, a, b, ref in rows:
            writer.writerow([day.isoformat(), f"{a:.4f}", f"{b:.4f}", f"{ref:.4f}"])

    print()
    print("Objective 2: hourly-versus-daily hypothesis")
    print(f"  {SITE_NAME}, {START_DATE} to {END_DATE}, n = {len(rows)} days")
    print()
    print(f"  {'series':<22}{'MAE':>9}{'RMSE':>9}{'bias':>9}{'within':>9}")
    print(
        f"  {'A daily-aggregate':<22}{daily_stats[0]:>9.3f}{daily_stats[1]:>9.3f}"
        f"{daily_stats[2]:>9.3f}{daily_stats[3]:>8.1%}"
    )
    print(
        f"  {'B hourly-summed':<22}{hourly_stats[0]:>9.3f}{hourly_stats[1]:>9.3f}"
        f"{hourly_stats[2]:>9.3f}{hourly_stats[3]:>8.1%}"
    )
    print()

    proven = hourly_stats[0] <= TOLERANCE_MM < daily_stats[0]
    if proven:
        verdict = "PROVEN: the hourly sum closes the gap, the daily aggregate does not"
    elif hourly_stats[0] < daily_stats[0]:
        verdict = (
            f"PARTIAL: the hourly sum improves MAE from {daily_stats[0]:.3f} to "
            f"{hourly_stats[0]:.3f} but does not reach {TOLERANCE_MM}"
        )
    else:
        verdict = (
            f"DEAD: the hourly sum does not improve on the daily aggregate "
            f"({hourly_stats[0]:.3f} vs {daily_stats[0]:.3f})"
        )
    print(f"  HYPOTHESIS {verdict}")
    print(f"  written to {RESULTS_PATH}")
    print()
