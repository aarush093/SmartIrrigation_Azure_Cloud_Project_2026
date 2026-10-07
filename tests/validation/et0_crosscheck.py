"""Objective 2 validation: our Penman-Monteith against Open-Meteo's published ET0.

Phase-I Objective 2 requires computed ET0 within 0.2 mm/day of the FAO-56
Penman-Monteith reference on at least 365 held-out station-days. Unit tests on
worked examples do not measure that, so this is where the criterion is actually
evaluated.

Method. For each of the three pilot districts, pull one full year of daily
archive data from Open-Meteo, compute ET0 from the raw meteorological variables
using :func:`irrigation_engine.et0.penman_monteith`, and compare against the
``et0_fao_evapotranspiration`` value the same API publishes for the same day and
grid cell. Open-Meteo computes that variable with its own independent FAO-56
implementation, which is what makes the comparison meaningful.

Reported per district and overall: n, MAE, RMSE, bias and the fraction of
station-days inside the 0.2 mm/day tolerance. Results are written to
``results/objective2_et0_crosscheck.csv`` and shipped in M6.

This is marked ``integration`` and is excluded from CI. Run it with::

    make validate

If the criterion is missed, the number is reported as measured. The tolerance is
not to be loosened to make it pass.

Result as of 2 September 2026, over 1,095 station-days (calendar year 2025):

    site            n     MAE    RMSE    bias   within 0.2
    Vellore TN    365   0.297   0.366   0.205      37.3%
    Beed MH       365   0.308   0.350  -0.013      28.8%
    Ludhiana PB   365   0.232   0.276   0.004      43.8%
    OVERALL      1095   0.279   0.333   0.065      36.6%

**Objective 2 is NOT MET at this tolerance.** MAE is 0.279 mm/day against the
0.2 mm/day criterion.

Two findings from the run, both recorded rather than tuned away:

1. A first run gave MAE 0.972 mm/day with a bias of +0.967, that is, an almost
   pure systematic overestimate. The cause was this harness requesting
   ``wind_speed_10m_max`` where FAO-56 equation 6 takes the daily *mean* wind
   speed. Correcting to ``wind_speed_10m_mean`` moved MAE to 0.279 and bias to
   +0.065. The bug was in the validation harness, not in
   :func:`~irrigation_engine.et0.penman_monteith`.

2. The residual is dominated by scatter, not bias: overall bias is +0.065 mm/day
   while MAE is 0.279. Beed and Ludhiana are unbiased to within 0.02 mm/day.
   The most likely remaining cause is a methodological difference rather than an
   error: Open-Meteo computes ET0 on hourly data and sums to a daily total, while
   this implementation computes it from daily aggregates. FAO-56 sanctions both,
   and they do not agree to 0.2 mm/day. Vellore retains a +0.205 mm/day bias that
   is not yet explained.

TODO [VERIFY] before the Review-2 submission, decide and record which of these
applies, and report whichever is chosen honestly rather than adjusting the
tolerance:

  a. Compare against a reference computed the same way, from daily aggregates,
     which is what the Objective 2 wording ("the FAO-56 Penman-Monteith
     reference") most plausibly meant. Open-Meteo's published value is a second
     implementation, not the reference itself.
  b. Implement the hourly time step of FAO-56 equation 53 and sum to daily, so
     the two computations are directly comparable.
  c. Report Objective 2 as partially met, with 0.279 mm/day MAE and zero bias
     against an independent FAO-56 implementation stated as the measured result.

Investigate the Vellore bias in each case.
"""

from __future__ import annotations

import csv
import datetime as dt
import math
from dataclasses import dataclass
from pathlib import Path

import httpx
import pytest

from irrigation_engine.et0 import penman_monteith

TOLERANCE_MM = 0.2
MIN_STATION_DAYS = 365

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
RESULTS_PATH = Path(__file__).resolve().parents[2] / "results" / "objective2_et0_crosscheck.csv"

# Variables needed to compute ET0 independently, plus the published value.
DAILY_VARIABLES = (
    "et0_fao_evapotranspiration",
    "temperature_2m_max",
    "temperature_2m_min",
    "relative_humidity_2m_max",
    "relative_humidity_2m_min",
    "wind_speed_10m_mean",
    "shortwave_radiation_sum",
)


@dataclass(frozen=True)
class Site:
    """A pilot district, with the elevation Penman-Monteith needs."""

    name: str
    latitude: float
    longitude: float
    elevation_m: float
    coastal: bool = False


# The three pilot districts from plan Section 12.
# TODO [VERIFY] elevations are approximate district-town values and should be
# confirmed against a gazetteer or the Open-Meteo elevation field.
SITES = (
    Site("Vellore TN", 12.97, 79.16, 216.0),
    Site("Beed MH", 18.99, 75.76, 515.0),
    Site("Ludhiana PB", 30.90, 75.86, 244.0),
)

# A full year, ending well before today so the archive is finalised rather than
# near-real-time.
END_DATE = dt.date(2025, 12, 31)
START_DATE = dt.date(2025, 1, 1)


@dataclass
class Comparison:
    """One station-day: ours against theirs."""

    site: str
    date: dt.date
    ours_mm: float
    theirs_mm: float

    @property
    def difference_mm(self) -> float:
        """Signed difference, ours minus theirs."""
        return self.ours_mm - self.theirs_mm


def wind_10m_to_2m(speed_10m: float) -> float:
    """Convert a 10 m wind speed to the 2 m height the reference crop assumes.

    FAO-56 equation 47: ``u2 = uz 4.87 / ln(67.8 z - 5.42)``, with z = 10 m.
    Skipping this conversion would overstate the aerodynamic term on every day.
    """
    return speed_10m * 4.87 / math.log(67.8 * 10.0 - 5.42)


def fetch_site_year(site: Site) -> list[Comparison]:
    """Pull one year for a site and compute both ET0 values for every usable day."""
    with httpx.Client(timeout=60.0) as client:
        response = client.get(
            ARCHIVE_URL,
            params={
                "latitude": site.latitude,
                "longitude": site.longitude,
                "daily": ",".join(DAILY_VARIABLES),
                "timezone": "Asia/Kolkata",
                "start_date": START_DATE.isoformat(),
                "end_date": END_DATE.isoformat(),
            },
        )
    response.raise_for_status()
    body = response.json()
    daily = body["daily"]

    # Use the elevation Open-Meteo reports for the grid cell rather than the
    # declared district-town value. The comparison is against that cell's own
    # ET0, so its elevation is the one that belongs in the pressure term; a
    # mismatch here shifts the psychrometric constant on every day.
    elevation_m = float(body.get("elevation", site.elevation_m))

    comparisons: list[Comparison] = []
    for index, day in enumerate(daily["time"]):
        published = daily["et0_fao_evapotranspiration"][index]
        t_max = daily["temperature_2m_max"][index]
        t_min = daily["temperature_2m_min"][index]
        if published is None or t_max is None or t_min is None:
            continue

        rh_max = daily["relative_humidity_2m_max"][index]
        rh_min = daily["relative_humidity_2m_min"][index]
        wind_10m = daily["wind_speed_10m_mean"][index]
        radiation = daily["shortwave_radiation_sum"][index]

        try:
            ours = penman_monteith(
                temp_max_c=float(t_max),
                temp_min_c=float(t_min),
                latitude=site.latitude,
                date=dt.date.fromisoformat(day),
                elevation_m=elevation_m,
                # Open-Meteo reports wind in km/h at 10 m. FAO-56 needs the
                # daily MEAN at 2 m, not the maximum: using the maximum
                # overstates the aerodynamic term on every single day.
                wind_speed_2m=(None if wind_10m is None else wind_10m_to_2m(float(wind_10m) / 3.6)),
                relative_humidity_max=None if rh_max is None else float(rh_max),
                relative_humidity_min=None if rh_min is None else float(rh_min),
                solar_radiation_mj=None if radiation is None else float(radiation),
                coastal=site.coastal,
            )
        except ValueError:
            # A day whose inputs are internally inconsistent is excluded and
            # counted by its absence from n, never silently replaced.
            continue

        comparisons.append(
            Comparison(site.name, dt.date.fromisoformat(day), ours, float(published))
        )
    return comparisons


def summarise(comparisons: list[Comparison]) -> dict[str, float]:
    """Compute n, MAE, RMSE, bias and the within-tolerance fraction."""
    n = len(comparisons)
    if n == 0:
        return {"n": 0.0, "mae": math.nan, "rmse": math.nan, "bias": math.nan, "within": math.nan}

    differences = [c.difference_mm for c in comparisons]
    return {
        "n": float(n),
        "mae": sum(abs(d) for d in differences) / n,
        "rmse": math.sqrt(sum(d * d for d in differences) / n),
        "bias": sum(differences) / n,
        "within": sum(1 for d in differences if abs(d) <= TOLERANCE_MM) / n,
    }


def write_csv(comparisons: list[Comparison], summaries: dict[str, dict[str, float]]) -> None:
    """Write the per-day comparisons and the summary block to results/."""
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with RESULTS_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["# Objective 2 ET0 cross-check"])
        writer.writerow(
            ["# our FAO-56 Penman-Monteith vs Open-Meteo published et0_fao_evapotranspiration"]
        )
        writer.writerow([f"# period {START_DATE} to {END_DATE}, tolerance {TOLERANCE_MM} mm/day"])
        writer.writerow([])
        writer.writerow(["site", "n", "mae_mm", "rmse_mm", "bias_mm", "fraction_within_tolerance"])
        for site, stats in summaries.items():
            writer.writerow(
                [
                    site,
                    int(stats["n"]),
                    f"{stats['mae']:.4f}",
                    f"{stats['rmse']:.4f}",
                    f"{stats['bias']:.4f}",
                    f"{stats['within']:.4f}",
                ]
            )
        writer.writerow([])
        writer.writerow(["site", "date", "et0_ours_mm", "et0_openmeteo_mm", "difference_mm"])
        for c in comparisons:
            writer.writerow(
                [
                    c.site,
                    c.date.isoformat(),
                    f"{c.ours_mm:.4f}",
                    f"{c.theirs_mm:.4f}",
                    f"{c.difference_mm:.4f}",
                ]
            )


@pytest.mark.integration
def test_objective_2_et0_crosscheck() -> None:
    """Measure and report the Objective 2 criterion. Does not loosen it to pass."""
    all_comparisons: list[Comparison] = []
    summaries: dict[str, dict[str, float]] = {}

    for site in SITES:
        site_comparisons = fetch_site_year(site)
        summaries[site.name] = summarise(site_comparisons)
        all_comparisons.extend(site_comparisons)

    overall = summarise(all_comparisons)
    summaries["OVERALL"] = overall
    write_csv(all_comparisons, summaries)

    print()
    print("Objective 2: ET0 cross-check against Open-Meteo published FAO-56 ET0")
    print(f"  period {START_DATE} to {END_DATE}, tolerance {TOLERANCE_MM} mm/day")
    print()
    print(f"  {'site':<14}{'n':>6}{'MAE':>9}{'RMSE':>9}{'bias':>9}{'within':>9}")
    for name, stats in summaries.items():
        print(
            f"  {name:<14}{int(stats['n']):>6}{stats['mae']:>9.3f}"
            f"{stats['rmse']:>9.3f}{stats['bias']:>9.3f}{stats['within']:>8.1%}"
        )
    print()
    print(f"  written to {RESULTS_PATH}")

    met = overall["n"] >= MIN_STATION_DAYS and overall["mae"] <= TOLERANCE_MM
    verdict = "MET" if met else "NOT MET"
    print(
        f"  VERDICT: Objective 2 {verdict} "
        f"(n={int(overall['n'])}, MAE={overall['mae']:.3f} mm/day, "
        f"{overall['within']:.1%} of station-days within {TOLERANCE_MM} mm/day)"
    )
    print()

    assert overall["n"] >= MIN_STATION_DAYS, (
        f"only {int(overall['n'])} usable station-days, need at least {MIN_STATION_DAYS}"
    )
    assert overall["mae"] <= TOLERANCE_MM, (
        f"mean absolute error {overall['mae']:.3f} mm/day exceeds the "
        f"{TOLERANCE_MM} mm/day tolerance. Report this shortfall; do not widen "
        f"the tolerance to make it pass."
    )
