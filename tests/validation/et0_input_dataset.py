"""The final Objective 2 experiment: methodology difference, or input difference?

Two questions were already settled. The implementation is correct: it reproduces
every printed intermediate of FAO-56 Example 18. And the residual is not an
hourly-versus-daily artefact: the hourly sum is worse, not better.

One question remains. Is the 0.279 mm/day residual a difference in *method*
between us and Open-Meteo, or a difference in the *input dataset* each of us
feeds the same method?

The experiment separates them. Our own Penman-Monteith is run twice over the same
year and the same three sites, once on Open-Meteo (ERA5) inputs and once on NASA
POWER (MERRA-2) inputs, and both are compared against Open-Meteo's published ET0:

    A. our PM on Open-Meteo inputs   vs Open-Meteo published
    B. our PM on NASA POWER inputs   vs Open-Meteo published
    C. our PM on POWER inputs        vs our PM on Open-Meteo inputs

If B disagrees by roughly the same amount and with the same seasonal shape as A,
the residual is disagreement between reanalysis products, not a defect in
anything this project built, and there is nothing left to fix. If instead C is
small while A and B are both large, the residual sits in Open-Meteo's own ET0
product. Either outcome is a finished answer.

NASA POWER is dataset D3 in ``dataset/README.md`` and is named in plan Section
17.2 as the independent cross-check source, so this is in scope.

**This is the last ET0 investigation. The question is not reopened after it.**

Marked ``integration``; run with ``make validate-inputs``.
"""

from __future__ import annotations

import csv
import datetime as dt
import math
import statistics
from dataclasses import dataclass
from pathlib import Path

import httpx
import pytest

from irrigation_engine.et0 import penman_monteith

TOLERANCE_MM = 0.2
RESULTS_PATH = Path(__file__).resolve().parents[2] / "results" / "objective2_input_datasets.csv"

OPEN_METEO_URL = "https://archive-api.open-meteo.com/v1/archive"
POWER_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"

START = dt.date(2025, 1, 1)
END = dt.date(2025, 12, 31)

# NASA POWER agroclimatology parameters. WS2M is already at 2 m, so no height
# conversion is needed on this side; ALLSKY_SFC_SW_DWN is MJ/m2/day.
POWER_PARAMETERS = "T2M_MAX,T2M_MIN,RH2M,WS2M,ALLSKY_SFC_SW_DWN"

# POWER uses this sentinel for a missing value. Read as a number it would be a
# temperature of minus a thousand degrees, so it must be filtered explicitly.
POWER_FILL = -999.0

OPEN_METEO_DAILY = (
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
    """A pilot district."""

    name: str
    latitude: float
    longitude: float


SITES = (
    Site("Vellore TN", 12.97, 79.16),
    Site("Beed MH", 18.99, 75.76),
    Site("Ludhiana PB", 30.90, 75.86),
)


def wind_10m_to_2m(speed_10m: float) -> float:
    """FAO-56 equation 47 for a 10 m measurement height."""
    return speed_10m * 4.87 / math.log(67.8 * 10.0 - 5.42)


def fetch_open_meteo(site: Site) -> tuple[dict[dt.date, float], dict[dt.date, float], float]:
    """Return our ET0 on Open-Meteo inputs, their published ET0, and the elevation."""
    with httpx.Client(timeout=90.0) as client:
        response = client.get(
            OPEN_METEO_URL,
            params={
                "latitude": site.latitude,
                "longitude": site.longitude,
                "daily": ",".join(OPEN_METEO_DAILY),
                "timezone": "Asia/Kolkata",
                "start_date": START.isoformat(),
                "end_date": END.isoformat(),
            },
        )
    response.raise_for_status()
    body = response.json()
    elevation = float(body.get("elevation", 200.0))
    daily = body["daily"]

    ours: dict[dt.date, float] = {}
    theirs: dict[dt.date, float] = {}

    for index, day in enumerate(daily["time"]):
        published = daily["et0_fao_evapotranspiration"][index]
        t_max = daily["temperature_2m_max"][index]
        t_min = daily["temperature_2m_min"][index]
        if published is None or t_max is None or t_min is None:
            continue

        wind = daily["wind_speed_10m_mean"][index]
        try:
            value = penman_monteith(
                temp_max_c=float(t_max),
                temp_min_c=float(t_min),
                latitude=site.latitude,
                date=dt.date.fromisoformat(day),
                elevation_m=elevation,
                wind_speed_2m=None if wind is None else wind_10m_to_2m(float(wind) / 3.6),
                relative_humidity_max=_optional(daily["relative_humidity_2m_max"][index]),
                relative_humidity_min=_optional(daily["relative_humidity_2m_min"][index]),
                solar_radiation_mj=_optional(daily["shortwave_radiation_sum"][index]),
            )
        except ValueError:
            continue

        date = dt.date.fromisoformat(day)
        ours[date] = value
        theirs[date] = float(published)

    return ours, theirs, elevation


def fetch_power(site: Site, elevation_m: float) -> dict[dt.date, float]:
    """Return our ET0 computed on NASA POWER inputs."""
    with httpx.Client(timeout=120.0) as client:
        response = client.get(
            POWER_URL,
            params={
                "parameters": POWER_PARAMETERS,
                "community": "AG",
                "latitude": site.latitude,
                "longitude": site.longitude,
                "start": START.strftime("%Y%m%d"),
                "end": END.strftime("%Y%m%d"),
                "format": "JSON",
            },
        )
    response.raise_for_status()
    parameters = response.json()["properties"]["parameter"]

    results: dict[dt.date, float] = {}
    for stamp in parameters["T2M_MAX"]:
        values = {key: parameters[key][stamp] for key in parameters}
        if any(v is None or v <= POWER_FILL for v in values.values()):
            continue

        date = dt.datetime.strptime(stamp, "%Y%m%d").date()
        try:
            # POWER supplies mean relative humidity rather than the daily
            # extremes. Passing it as both max and min reduces FAO-56 equation
            # 17 to equation 19, which is the correct treatment for a mean.
            results[date] = penman_monteith(
                temp_max_c=float(values["T2M_MAX"]),
                temp_min_c=float(values["T2M_MIN"]),
                latitude=site.latitude,
                date=date,
                elevation_m=elevation_m,
                wind_speed_2m=float(values["WS2M"]),
                relative_humidity_max=float(values["RH2M"]),
                relative_humidity_min=float(values["RH2M"]),
                solar_radiation_mj=float(values["ALLSKY_SFC_SW_DWN"]),
            )
        except ValueError:
            continue
    return results


def _optional(value: float | None) -> float | None:
    """Pass a value through, keeping None as None."""
    return None if value is None else float(value)


def summarise(differences: list[float]) -> tuple[int, float, float, float]:
    """Return n, MAE, RMSE and bias."""
    n = len(differences)
    mae = sum(abs(d) for d in differences) / n
    rmse = math.sqrt(sum(d * d for d in differences) / n)
    bias = sum(differences) / n
    return n, mae, rmse, bias


def seasonal_bias(pairs: list[tuple[dt.date, float]]) -> tuple[float, float]:
    """Return the mean bias in the dry season and in the monsoon.

    The seasonal reversal found in the M1 cross-check is the shape being tested
    for here, so it is reported for every series rather than only the annual
    figure.
    """
    dry = [d for date, d in pairs if date.month in (1, 2, 3, 4, 5, 11, 12)]
    monsoon = [d for date, d in pairs if date.month in (6, 7, 8, 9, 10)]
    return (
        statistics.mean(dry) if dry else math.nan,
        statistics.mean(monsoon) if monsoon else math.nan,
    )


@pytest.mark.integration
def test_input_dataset_versus_methodology() -> None:
    """Settle whether the residual is an input-dataset or a methodology difference."""
    rows: list[list[object]] = []
    totals: dict[str, list[float]] = {"A": [], "B": [], "C": []}
    totals_dated: dict[str, list[tuple[dt.date, float]]] = {"A": [], "B": [], "C": []}

    print()
    print("Objective 2, final experiment: input dataset versus methodology")
    print(f"  {START} to {END}")
    print()
    print(
        f"  {'site':<13}{'series':<34}{'n':>6}{'MAE':>8}{'RMSE':>8}{'bias':>8}{'dry':>8}{'wet':>8}"
    )

    for site in SITES:
        ours_om, published, elevation = fetch_open_meteo(site)
        ours_power = fetch_power(site, elevation)

        shared = sorted(set(ours_om) & set(published) & set(ours_power))
        series = {
            "A": [(d, ours_om[d] - published[d]) for d in shared],
            "B": [(d, ours_power[d] - published[d]) for d in shared],
            "C": [(d, ours_power[d] - ours_om[d]) for d in shared],
        }
        labels = {
            "A": "our PM on Open-Meteo vs published",
            "B": "our PM on NASA POWER vs published",
            "C": "our PM: POWER vs Open-Meteo inputs",
        }

        for key in ("A", "B", "C"):
            pairs = series[key]
            differences = [d for _, d in pairs]
            n, mae, rmse, bias = summarise(differences)
            dry, wet = seasonal_bias(pairs)
            print(
                f"  {site.name:<13}{labels[key]:<34}{n:>6}{mae:>8.3f}"
                f"{rmse:>8.3f}{bias:>8.3f}{dry:>8.3f}{wet:>8.3f}"
            )
            rows.append(
                [
                    site.name,
                    labels[key],
                    n,
                    f"{mae:.4f}",
                    f"{rmse:.4f}",
                    f"{bias:.4f}",
                    f"{dry:.4f}",
                    f"{wet:.4f}",
                ]
            )
            totals[key].extend(differences)
            totals_dated[key].extend(pairs)
        print()

    overall: dict[str, tuple[int, float, float, float]] = {}
    for key in ("A", "B", "C"):
        overall[key] = summarise(totals[key])
        dry, wet = seasonal_bias(totals_dated[key])
        n, mae, rmse, bias = overall[key]
        print(
            f"  {'OVERALL':<13}{labels[key]:<34}{n:>6}{mae:>8.3f}"
            f"{rmse:>8.3f}{bias:>8.3f}{dry:>8.3f}{wet:>8.3f}"
        )
        rows.append(
            [
                "OVERALL",
                labels[key],
                n,
                f"{mae:.4f}",
                f"{rmse:.4f}",
                f"{bias:.4f}",
                f"{dry:.4f}",
                f"{wet:.4f}",
            ]
        )

    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with RESULTS_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            ["# Objective 2: is the residual an input-dataset or a methodology difference?"]
        )
        writer.writerow([f"# {START} to {END}, three pilot districts"])
        writer.writerow(["# dry = mean bias Nov-May, wet = mean bias Jun-Oct"])
        writer.writerow([])
        writer.writerow(
            ["site", "series", "n", "mae_mm", "rmse_mm", "bias_mm", "bias_dry", "bias_wet"]
        )
        writer.writerows(rows)

    mae_a, mae_b, mae_c = overall["A"][1], overall["B"][1], overall["C"][1]
    print()
    if mae_c >= mae_a * 0.7:
        verdict = (
            "INPUT DATASET. Our own method disagrees with itself by "
            f"{mae_c:.3f} mm/day across two reanalysis products, comparable to "
            f"the {mae_a:.3f} mm/day residual against Open-Meteo's published "
            "value. The residual is disagreement between reanalysis products, "
            "not a defect in anything this project built. Nothing left to fix."
        )
    elif mae_b <= TOLERANCE_MM < mae_a:
        verdict = (
            f"OPEN-METEO ET0 PRODUCT. Our method on POWER inputs lands inside "
            f"{TOLERANCE_MM} ({mae_b:.3f}) while the comparison against "
            f"Open-Meteo's own published value does not ({mae_a:.3f})."
        )
    else:
        verdict = (
            f"MIXED. A={mae_a:.3f}, B={mae_b:.3f}, C={mae_c:.3f} mm/day. The two "
            "input sets agree more closely with each other than either does with "
            "the published product, so part of the residual sits in that product "
            "and part in the inputs."
        )
    print(f"  CONCLUSION: {verdict}")
    print(f"  written to {RESULTS_PATH}")
    print()

    assert overall["A"][0] > 300, "insufficient overlapping days to conclude anything"
