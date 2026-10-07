"""Objective 6: compare five irrigation policies over two seasons.

Plan Section 12, with the policy set corrected on 5 September 2026.

**The baseline matters more than the metrics.** An unconstrained FAO-56 trigger
assumes the pump can run whenever the crop wants water, which is physically
impossible on a rationed feeder. Beating it is not the claim this project makes,
and losing to it would mean nothing. The baseline the novelty is measured
against is what a farmer using *any existing advisory app* actually experiences:
a correct agronomic instruction he can only execute when the power happens to
arrive.

    P0   Calendar                fixed interval, fixed depth, ignores weather
                                 and power. Traditional practice.
    P1   Unconstrained advisory, an FAO-56 trigger says irrigate at RAW; the
         constrained execution   farmer pumps in the next available window and
                                 applies whatever fits. THE BASELINE.
    P2   Power-window scheduler  Section 7 as corrected, no rain skip.
    P3   P2 + calibrated skip    the full system.
    Pref Unconstrained trigger,  reference upper bound. PHYSICALLY
         unlimited power         UNACHIEVABLE; labelled so in every table.

**No hindsight.** The water balance is driven by the archive, which is observed
weather. Every decision is driven by the forecast **as it was issued that
morning**, from the Open-Meteo Previous Runs API. If the skip decision read the
archive it would be skipping on rain it already knew had fallen, and the result
would be worthless. See :mod:`forecast_source`.

Metrics per policy per site-season: water applied, stress days, maximum deficit
reached, pump hours, estimated kWh, deep percolation, windows used, irrigation
events, and decisions by reason.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
from collections import Counter
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

from forecast_source import fetch_as_issued
from irrigation_engine.balance import WaterBalance
from irrigation_engine.crops import crop_calendar
from irrigation_engine.models import DailyWeather, IrrigationMethod, PumpSpec
from irrigation_engine.providers import OpenMeteoProvider
from irrigation_engine.pump import pump_discharge_l_per_min, resolve_efficiency
from irrigation_engine.scheduler import (
    IST,
    Decision,
    DeclaredRotation,
    FieldState,
    RainForecast,
    plan_day,
)
from irrigation_engine.soil import (
    readily_available_water,
    resolve_soil,
    saxton_rawls,
    total_available_water,
)
from rain_calibration import (
    CalibrationTable,
    brier_score,
    build_table,
    raw_forecast_probability,
)

RESULTS = Path("results")
CALENDAR_INTERVAL_DAYS = 7
SKIP_CONFIDENCE = 0.7
HORIZON_DAYS = 3

#: Confidence thresholds swept for the rain-skip sensitivity table. The point in
#: use is a parameter (``scheduling.yaml``, ``rain_skip.min_confidence``); this
#: shows the curve around it so the pilot picks from evidence rather than from a
#: default.
SKIP_THRESHOLDS = (0.5, 0.6, 0.7, 0.8)

#: Crops normally grown ponded rather than to a depletion trigger.
#:
#: ``params/crops.yaml`` states for rice that "a ponded-paddy mode is a
#: Phase-III item", so a depletion-triggered balance is the wrong model for it
#: and the project already says so. Three of the nine simulated fields are rice,
#: including the largest, so including them would let a model the parameter file
#: calls inapplicable dominate the headline. They are simulated and reported,
#: separately, and excluded from the headline.
PONDED_CROPS = frozenset({"rice"})



class Policy(StrEnum):
    """The five policies compared."""

    P0_CALENDAR = "P0_calendar"
    P1_ADVISORY = "P1_advisory_constrained"
    P2_WINDOW = "P2_window"
    P3_WINDOW_SKIP = "P3_window_skip"
    PREF_UNLIMITED = "Pref_unlimited_power"

    @property
    def achievable(self) -> bool:
        """Whether a farmer could actually execute this policy."""
        return self is not Policy.PREF_UNLIMITED


@dataclass
class Totals:
    """What one policy did to one field over one season."""

    policy: Policy
    site: str
    crop: str
    season: str
    water_mm: float = 0.0
    stress_days: int = 0
    max_deficit_mm: float = 0.0
    pump_minutes: float = 0.0
    energy_kwh: float = 0.0
    deep_percolation_mm: float = 0.0
    windows_used: int = 0
    irrigations: int = 0
    days: int = 0
    reasons: Counter[str] = field(default_factory=Counter)

    @property
    def pump_hours(self) -> float:
        return self.pump_minutes / 60.0

    @property
    def ponded(self) -> bool:
        """Whether this field's crop is normally grown ponded. See PONDED_CROPS."""
        return self.crop in PONDED_CROPS

    @property
    def skips(self) -> int:
        """Days the rain-skip rule fired."""
        return self.reasons["rain_expected"]


@dataclass(frozen=True)
class SimField:
    """One field in the simulation."""

    site: str
    latitude: float
    longitude: float
    crop: str
    sowing_month_day: tuple[int, int]
    area_m2: float
    method: IrrigationMethod
    pump: PumpSpec
    soil_class: str
    night_first: bool


# Three districts, three crops each, all genuinely grown there in that season.
FIELDS = (
    SimField("Vellore TN", 12.97, 79.16, "groundnut", (6, 16), 4047.0,
             IrrigationMethod.FURROW, PumpSpec(hp=5.0, head_m=30.0, eta=0.5), "sandy", False),
    SimField("Vellore TN", 12.97, 79.16, "rice", (6, 20), 4047.0,
             IrrigationMethod.FLOOD, PumpSpec(hp=5.0, head_m=30.0, eta=0.5), "loamy", False),
    SimField("Vellore TN", 12.97, 79.16, "tomato", (6, 25), 2000.0,
             IrrigationMethod.DRIP, PumpSpec(hp=3.0, head_m=25.0, eta=0.5), "loamy", False),
    SimField("Beed MH", 18.99, 75.76, "cotton", (6, 15), 8094.0,
             IrrigationMethod.FLOOD, PumpSpec(hp=7.5, head_m=45.0, eta=0.5), "clayey", False),
    SimField("Beed MH", 18.99, 75.76, "sugarcane", (6, 1), 8094.0,
             IrrigationMethod.FURROW, PumpSpec(hp=7.5, head_m=45.0, eta=0.5), "clayey", False),
    SimField("Beed MH", 18.99, 75.76, "chickpea", (10, 20), 6000.0,
             IrrigationMethod.FURROW, PumpSpec(hp=5.0, head_m=45.0, eta=0.5), "clayey", False),
    SimField("Ludhiana PB", 30.90, 75.86, "rice", (6, 25), 12141.0,
             IrrigationMethod.FLOOD, PumpSpec(hp=10.0, head_m=40.0, eta=0.5), "loamy", True),
    SimField("Ludhiana PB", 30.90, 75.86, "wheat", (11, 15), 12141.0,
             IrrigationMethod.FURROW, PumpSpec(hp=10.0, head_m=40.0, eta=0.5), "loamy", True),
    SimField("Ludhiana PB", 30.90, 75.86, "maize", (10, 10), 8000.0,
             IrrigationMethod.FURROW, PumpSpec(hp=7.5, head_m=40.0, eta=0.5), "sandy", True),
)


def rotation_for(field_spec: SimField, anchor: dt.date) -> DeclaredRotation:
    """Eight hours of supply on a weekly day/night rotation."""
    return DeclaredRotation(
        day_start=dt.time(7, 30), day_end=dt.time(15, 30),
        night_start=dt.time(22, 0), night_end=dt.time(6, 0),
        rotation_days=7, anchor_date=anchor,
        anchor_is_day_shift=not field_spec.night_first,
    )


def next_window_after(rotation: DeclaredRotation, day: dt.date):  # type: ignore[no-untyped-def]
    """The first power window opening at or after 09:00 on ``day``."""
    windows = rotation.windows(dt.datetime.combine(day, dt.time(9, 0), tzinfo=IST), days=8)
    return windows[0] if windows else None


def run_policy(  # one branch per policy is the point
    policy: Policy,
    field_spec: SimField,
    weather: dict[dt.date, DailyWeather],
    as_issued,
    calibration: CalibrationTable,
    sowing: dt.date,
    season: str,
    skip_confidence: float = SKIP_CONFIDENCE,
) -> Totals:
    """Run one policy over one field for one season."""
    totals = Totals(policy=policy, site=field_spec.site, crop=field_spec.crop, season=season)

    soil, _ = resolve_soil(declared_class=field_spec.soil_class)
    constants = saxton_rawls(soil)
    efficiency = resolve_efficiency(field_spec.method)
    discharge = pump_discharge_l_per_min(field_spec.pump)
    balance = WaterBalance()
    rotation = rotation_for(field_spec, sowing)

    depletion = 0.0
    days_since = CALENDAR_INTERVAL_DAYS
    steps = 0  # balance steps taken; must equal totals.days at the end
    pending: dict[dt.date, float] = {}  # P1: depth owed, waiting for a window

    day = sowing
    while True:
        try:
            stage = crop_calendar(field_spec.crop, sowing, day)
        except ValueError:
            break
        observed = weather.get(day)
        if observed is None:
            break

        taw = total_available_water(constants, stage.root_depth_m)
        raw = readily_available_water(taw, stage.depletion_fraction)
        depletion = min(depletion, taw)
        totals.days += 1

        applied = 0.0
        minutes = 0.0
        window = next_window_after(rotation, day)
        window_today = window is not None and window.start.date() == day

        if policy is Policy.P0_CALENDAR:
            # Fixed interval, FIXED DEPTH. Traditional practice is not "refill
            # to field capacity every seven days", which would require knowing
            # the depletion; it is "when the power comes on my day, run the pump
            # until it goes off again". The depth applied is therefore whatever
            # one full window delivers, regardless of what the crop needs.
            #
            # An earlier version applied `depletion` here, which is need-based
            # and made the baseline better than the practice it is meant to
            # represent, flattering it against every other policy.
            if days_since >= CALENDAR_INTERVAL_DAYS and window is not None:
                capacity = _capacity(window.duration_minutes, field_spec, efficiency, discharge)
                applied = capacity
                minutes = window.duration_minutes
                days_since = 0
                totals.windows_used += 1
            else:
                days_since += 1

        elif policy is Policy.PREF_UNLIMITED:
            # Physically unachievable: assumes power on demand.
            if depletion >= raw:
                applied = depletion
                minutes = _minutes(applied, field_spec, efficiency, discharge)

        elif policy is Policy.P1_ADVISORY:
            # The status quo for a farmer using any existing advisory app. The
            # app tells him to irrigate when depletion reaches RAW; he can only
            # pump when the feeder is live, and he applies whatever fits.
            if depletion >= raw:
                pending[day] = depletion
            if pending and window_today and window is not None:
                owed = max(pending.values())
                capacity = _capacity(window.duration_minutes, field_spec, efficiency, discharge)
                applied = min(owed, capacity)
                minutes = _minutes(applied, field_spec, efficiency, discharge)
                pending.clear()
                totals.windows_used += 1

        else:
            horizon = [day + dt.timedelta(days=k) for k in range(HORIZON_DAYS)]
            etc = _forecast_etc(as_issued, day, horizon, field_spec, sowing, weather)
            if etc is None:
                # No usable projection: the scheduler cannot decide, so nothing
                # is applied. It does NOT mean the day did not happen. This
                # branch used to `continue`, skipping the balance step entirely,
                # so that day's ETc and rain never reached the depletion and the
                # next morning planned from a stale root zone.
                etc = []

            windows = rotation.windows(
                dt.datetime.combine(day, dt.time(9, 0), tzinfo=IST), days=8
            )
            # Depletion alone. The balance below is stepped with the depth
            # DELIVERED, so a truncated run leaves its shortfall inside the
            # depletion; adding carry-over on top asked for the same water
            # twice. Measured 5 September 2026: 1,467 mm of water and 1,452 mm
            # of deep percolation, 99 percent of the excess draining past the
            # root zone. See the build log entry of that date.
            required = depletion
            rain = RainForecast()
            if policy is Policy.P3_WINDOW_SKIP and required > 0:
                forecast_rain = as_issued.rain_over(
                    day + dt.timedelta(days=1), HORIZON_DAYS, day
                )
                if forecast_rain is not None:
                    confidence = calibration.probability(forecast_rain, required, 1)
                    rain = RainForecast(
                        expected_mm=forecast_rain,
                        confidence=confidence,
                        min_confidence=skip_confidence,
                    )

            state = FieldState(
                field_id=f"{field_spec.site}-{field_spec.crop}",
                depletion_mm=depletion, taw_mm=taw, raw_mm=raw,
                area_m2=field_spec.area_m2, irrigation_efficiency=efficiency,
                discharge_l_per_min=discharge,
                yield_response_factor=stage.yield_response_factor,
            )
            schedule = (
                plan_day(state, today=day, windows=windows, forecast_etc_mm=etc, rain=rain)
                if etc
                else None
            )
            if schedule is not None:
                totals.reasons[schedule.reason_code.value] += 1
            else:
                totals.reasons["no_forecast"] += 1

            # Carry-over is the depth a TRUNCATED RUN failed to deliver. It is
            # therefore updated only when a run actually happened. Setting it
            # from a schedule whose window is still in the future would record a
            # debt for water that was never withheld, and the next day would add
            # it to the depletion that already includes the same shortfall,
            # double-counting the deficit and driving steady over-irrigation.
            if (
                schedule is not None
                and schedule.decision is Decision.IRRIGATE
                and schedule.window is not None
                and schedule.window.start.date() == day
            ):
                applied = schedule.delivered_mm
                minutes = schedule.minutes
                totals.windows_used += 1

        after = balance.step(depletion, observed, stage, applied, taw_mm=taw)
        depletion = after.depletion_mm
        steps += 1

        totals.water_mm += applied
        totals.pump_minutes += minutes
        totals.energy_kwh += field_spec.pump.hp * 0.746 * (minutes / 60.0)
        totals.deep_percolation_mm += after.deep_percolation_mm
        totals.max_deficit_mm = max(totals.max_deficit_mm, depletion)
        if applied > 0:
            totals.irrigations += 1
        if after.is_stressed:
            totals.stress_days += 1

        day += dt.timedelta(days=1)

    # Every simulated day must advance the balance exactly once, under every
    # policy. A policy branch that returns early without stepping leaves the
    # depletion stale and silently understates the next day's requirement.
    if steps != totals.days:
        msg = (
            f"{policy.value} on {field_spec.site}/{field_spec.crop} {season}: "
            f"{steps} balance steps for {totals.days} simulated days"
        )
        raise AssertionError(msg)

    return totals


def _minutes(depth: float, f: SimField, efficiency: float, discharge: float) -> float:
    return 0.0 if depth <= 0 else (depth / efficiency) * f.area_m2 / discharge


def _capacity(window_minutes: float, f: SimField, efficiency: float, discharge: float) -> float:
    return discharge * window_minutes / f.area_m2 * efficiency


def _forecast_etc(
    as_issued,
    day: dt.date,
    horizon: list[dt.date],
    field_spec: SimField,
    sowing: dt.date,
    weather: dict[dt.date, DailyWeather],
) -> list[float] | None:
    """Projected ETc from the ET0 forecast as issued that morning."""
    et0 = as_issued.et0_over(horizon[0], len(horizon), day)
    if et0 is None:
        # Fall back to today's observed ET0 held flat, which is what a system
        # with no forecast would assume. Never uses future observations.
        today = weather.get(day)
        if today is None:
            return None
        et0 = [today.et0_mm] * len(horizon)

    series: list[float] = []
    for target, value in zip(horizon, et0, strict=True):
        try:
            stage = crop_calendar(field_spec.crop, sowing, target)
        except ValueError:
            break
        series.append(stage.kc * value)
    return series or None


def build_calibration(
    fields: tuple[SimField, ...],
    archives: dict[str, dict[dt.date, DailyWeather]],
    forecasts: dict[str, object],
    split_date: dt.date,
) -> tuple[CalibrationTable, float, float, int]:
    """Fit the calibration on the earlier season and score it on the later one.

    Returns:
        The table, its Brier score, the raw forecast's Brier score, and n.
    """
    train: list[tuple[float, float, int, bool]] = []
    test: list[tuple[float, float, bool]] = []

    for site in {f.site for f in fields}:
        archive = archives[site]
        as_issued = forecasts[site]
        for day in sorted(archive):
            forecast = as_issued.rain_over(day + dt.timedelta(days=1), HORIZON_DAYS, day)  # type: ignore[attr-defined]
            if forecast is None:
                continue
            observed = sum(
                archive[day + dt.timedelta(days=k)].precipitation_mm
                for k in range(1, HORIZON_DAYS + 1)
                if day + dt.timedelta(days=k) in archive
            )
            for deficit in (5.0, 10.0, 20.0, 40.0):
                covered = observed >= deficit
                if day < split_date:
                    train.append((forecast, deficit, 1, covered))
                else:
                    test.append((forecast, deficit, covered))

    table = build_table(train)
    if not test:
        return table, float("nan"), float("nan"), 0

    outcomes = [covered for _, _, covered in test]
    calibrated = [table.probability(f, d, 1) for f, d, _ in test]
    raw = [raw_forecast_probability(f, d) for f, d, _ in test]
    return table, brier_score(calibrated, outcomes), brier_score(raw, outcomes), len(test)


def main(argv: list[str] | None = None) -> int:
    """Run the five-policy simulation."""
    parser = argparse.ArgumentParser(description="Five-policy irrigation simulation.")
    parser.add_argument("--out", type=Path, default=RESULTS)
    parser.add_argument("--seasons", type=int, nargs="+", default=[2024, 2025])
    args = parser.parse_args(argv)

    provider = OpenMeteoProvider()
    sites = {f.site: (f.latitude, f.longitude) for f in FIELDS}

    start = dt.date(min(args.seasons), 5, 1)
    end = dt.date(max(args.seasons) + 1, 4, 30)

    print("Fetching observed weather and forecasts as issued...")
    archives: dict[str, dict[dt.date, DailyWeather]] = {}
    forecasts: dict[str, object] = {}
    for site, (lat, lon) in sites.items():
        days = provider.fetch_archive(lat, lon, start, end)
        archives[site] = {d.date: d for d in days}
        forecasts[site] = fetch_as_issued(lat, lon, start, end)
        print(f"  {site}: {len(days)} observed days, forecasts as issued loaded")

    split = dt.date(min(args.seasons) + 1, 5, 1)
    table, brier_cal, brier_raw, n_test = build_calibration(FIELDS, archives, forecasts, split)
    print()
    print("Rain calibration, fitted on the earlier season and scored on the later:")
    print(f"  pairs: {table.samples} training, {n_test} test; usable cells: {table.cells}")
    print(f"  Brier score, calibrated:   {brier_cal:.4f}")
    print(f"  Brier score, raw forecast: {brier_raw:.4f}")
    better = "BETTER" if brier_cal < brier_raw else "NOT better"
    print(f"  calibration is {better} than the raw forecast")
    print()

    rows: list[Totals] = []
    for season in args.seasons:
        for field_spec in FIELDS:
            month, dayof = field_spec.sowing_month_day
            sowing = dt.date(season, month, dayof)
            for policy in Policy:
                rows.append(
                    run_policy(
                        policy, field_spec, archives[field_spec.site],
                        forecasts[field_spec.site], table, sowing, str(season),
                    )
                )
        print(f"  season {season} done")

    _write(rows, args.out, brier_cal, brier_raw, n_test)
    _summarise(rows)

    sweep = _skip_sensitivity(FIELDS, archives, forecasts, table, args.seasons)
    _write_sensitivity(sweep, args.out)
    _print_sensitivity(sweep)
    return 0


def _skip_sensitivity(
    fields: tuple[SimField, ...],
    archives: dict[str, dict[dt.date, DailyWeather]],
    forecasts: dict[str, object],
    table: CalibrationTable,
    seasons: list[int],
) -> dict[float, Totals]:
    """Run P3 at each confidence threshold, on the headline set.

    A single threshold is a single point. This shows the curve around it, so the
    report can say what the skip rule costs and buys at each setting rather than
    asserting that 0.7 is right. Ponded fields are excluded, as they are from the
    headline.

    Returns:
        Aggregate P3 totals per threshold.
    """
    print()
    print("Rain-skip threshold sensitivity, P3 on the six non-ponded fields...")
    out: dict[float, Totals] = {}
    for threshold in SKIP_THRESHOLDS:
        agg = Totals(Policy.P3_WINDOW_SKIP, "ALL", "ALL", "ALL")
        for season in seasons:
            for spec in fields:
                if spec.crop in PONDED_CROPS:
                    continue
                month, dayof = spec.sowing_month_day
                r = run_policy(
                    Policy.P3_WINDOW_SKIP, spec, archives[spec.site], forecasts[spec.site],
                    table, dt.date(season, month, dayof), str(season),
                    skip_confidence=threshold,
                )
                agg.water_mm += r.water_mm
                agg.stress_days += r.stress_days
                agg.pump_minutes += r.pump_minutes
                agg.deep_percolation_mm += r.deep_percolation_mm
                agg.irrigations += r.irrigations
                agg.reasons.update(r.reasons)
        out[threshold] = agg
        print(f"  threshold {threshold:.1f} done")
    return out


def _write_sensitivity(sweep: dict[float, Totals], out: Path) -> None:
    """Write the threshold sweep beside the main comparison."""
    path = out / "objective6_skip_threshold_sensitivity.csv"
    with path.open("w", newline="", encoding="utf-8") as h:
        w = csv.writer(h)
        w.writerow(["# P3 rain-skip confidence threshold sensitivity"])
        w.writerow(["# six non-ponded fields, two seasons; all other parameters unchanged"])
        w.writerow(["# the deployed value is scheduling.yaml rain_skip.min_confidence"])
        w.writerow([])
        w.writerow([
            "min_confidence", "water_mm", "stress_days", "rain_skips",
            "deep_percolation_mm", "pump_hours", "irrigations",
        ])
        for threshold, a in sorted(sweep.items()):
            w.writerow([
                f"{threshold:.2f}", f"{a.water_mm:.1f}", a.stress_days, a.skips,
                f"{a.deep_percolation_mm:.1f}", f"{a.pump_hours:.1f}", a.irrigations,
            ])
    print(f"wrote {path}")


def _print_sensitivity(sweep: dict[float, Totals]) -> None:
    """Print the sweep. No threshold is recommended here; the report decides."""
    print()
    print("  RAIN-SKIP THRESHOLD SENSITIVITY, P3, six non-ponded fields")
    print(f"  {'threshold':>10}{'water mm':>10}{'stress':>8}{'skips':>7}{'perc mm':>9}")
    for threshold, a in sorted(sweep.items()):
        print(
            f"  {threshold:>10.1f}{a.water_mm:>10.0f}{a.stress_days:>8}"
            f"{a.skips:>7}{a.deep_percolation_mm:>9.0f}"
        )
    print("  A lower threshold skips more often: less water, more risk of a skip")
    print("  the rain does not honour. The pilot picks a point from this curve.")


def _write(rows: list[Totals], out: Path, brier_cal: float, brier_raw: float, n: int) -> None:
    out.mkdir(parents=True, exist_ok=True)
    with (out / "objective6_policy_comparison.csv").open("w", newline="", encoding="utf-8") as h:
        w = csv.writer(h)
        w.writerow(["# Objective 6: five-policy comparison"])
        w.writerow(["# decisions use the forecast AS ISSUED (Open-Meteo Previous Runs)"])
        w.writerow(["# the water balance uses observed archive weather"])
        w.writerow([f"# rain calibration Brier {brier_cal:.4f} vs raw forecast {brier_raw:.4f}, n={n}"])
        w.writerow(["# Pref is PHYSICALLY UNACHIEVABLE: it assumes power on demand"])
        w.writerow(["# ponded=True rows are EXCLUDED from the headline: params/crops.yaml"])
        w.writerow(["# states that a depletion-triggered balance is the wrong model for paddy"])
        w.writerow([])
        w.writerow([
            "policy", "achievable", "site", "crop", "ponded", "season", "days", "water_mm",
            "stress_days", "max_deficit_mm", "pump_hours", "energy_kwh",
            "deep_percolation_mm", "windows_used", "irrigations", "rain_skips",
        ])
        for r in rows:
            w.writerow([
                r.policy.value, r.policy.achievable, r.site, r.crop, r.ponded, r.season, r.days,
                f"{r.water_mm:.1f}", r.stress_days, f"{r.max_deficit_mm:.1f}",
                f"{r.pump_hours:.1f}", f"{r.energy_kwh:.1f}",
                f"{r.deep_percolation_mm:.1f}", r.windows_used, r.irrigations, r.skips,
            ])
    print(f"\nwrote {out / 'objective6_policy_comparison.csv'}")


def _pct(new_value: float, base: float) -> float:
    """Percentage change from ``base`` to ``new_value``. Negative is a reduction."""
    return float("nan") if base == 0 else (new_value - base) / base * 100.0


def _aggregate(rows: list[Totals], *, ponded: bool | None = None) -> dict[Policy, Totals]:
    """Sum per policy over the selected fields.

    Args:
        rows: Every field-season result.
        ponded: True for ponded crops only, False to exclude them, None for all.

    Returns:
        One aggregate per policy.
    """
    agg: dict[Policy, Totals] = {p: Totals(p, "ALL", "ALL", "ALL") for p in Policy}
    for r in rows:
        if ponded is not None and r.ponded is not ponded:
            continue
        a = agg[r.policy]
        a.water_mm += r.water_mm
        a.stress_days += r.stress_days
        a.pump_minutes += r.pump_minutes
        a.energy_kwh += r.energy_kwh
        a.deep_percolation_mm += r.deep_percolation_mm
        a.irrigations += r.irrigations
        a.reasons.update(r.reasons)
        a.max_deficit_mm = max(a.max_deficit_mm, r.max_deficit_mm)
    return agg


def _print_block(title: str, agg: dict[Policy, Totals]) -> None:
    """Print one policy table."""
    print()
    print(f"  {title}")
    print(f"  {'policy':<26}{'water mm':>10}{'stress':>8}{'pump h':>9}{'kWh':>9}{'perc mm':>9}")
    for policy in Policy:
        a = agg[policy]
        tag = "" if policy.achievable else "  (unachievable)"
        print(
            f"  {policy.value:<26}{a.water_mm:>10.0f}{a.stress_days:>8}"
            f"{a.pump_hours:>9.0f}{a.energy_kwh:>9.0f}{a.deep_percolation_mm:>9.0f}{tag}"
        )


def _sanity_check(agg: dict[Policy, Totals]) -> None:
    """Warn when a constrained policy applies more water than the ideal one.

    Pref irrigates exactly when the crop needs it, with power on demand. A
    constrained policy applying materially more than that is refilling early,
    which is expected; applying so much more that almost all of the excess drains
    below the root zone is not a trade, it is a defect. That signature is what
    exposed the carry-over double count on 5 September 2026, so it is checked on
    every run from now on rather than noticed by eye.
    """
    pref = agg[Policy.PREF_UNLIMITED]
    for policy in (Policy.P2_WINDOW, Policy.P3_WINDOW_SKIP):
        a = agg[policy]
        excess_water = a.water_mm - pref.water_mm
        excess_perc = a.deep_percolation_mm - pref.deep_percolation_mm
        if excess_water <= 0:
            continue
        drained = excess_perc / excess_water
        if drained > 0.75:
            print()
            print(f"  *** WARNING: {policy.value} applies {excess_water:.0f} mm more than Pref")
            print(f"      and {drained * 100:.0f} percent of the excess drains past the root")
            print("      zone. Suspect a double count in the requirement. Investigate before")
            print("      reporting this as a water-for-reliability trade.")


def _summarise(rows: list[Totals]) -> None:
    """Print the aggregate tables and state the result, without spin.

    Every phrase here is computed from the numbers rather than chosen from a
    list of nice-sounding conclusions. An earlier version printed "at comparable
    water use" from a fixed string while the measured difference was 44 percent,
    which would have put a false statement into the report.

    The headline is computed on the non-ponded fields only. See PONDED_CROPS.
    """
    agg = _aggregate(rows, ponded=False)
    all_fields = _aggregate(rows)
    rice = _aggregate(rows, ponded=True)

    _print_block("HEADLINE SET: six non-ponded fields, two seasons", agg)
    _print_block("ALL NINE FIELDS, including three rice (see caveat below)", all_fields)
    _print_block("RICE ONLY, three fields. Depletion-triggered balance is the", rice)
    print("  wrong model for ponded paddy; params/crops.yaml says so. Reported,")
    print("  not used for any claim.")

    _sanity_check(agg)

    p0 = agg[Policy.P0_CALENDAR]
    p1 = agg[Policy.P1_ADVISORY]
    p3 = agg[Policy.P3_WINDOW_SKIP]
    pref = agg[Policy.PREF_UNLIMITED]

    print()
    print("  OBJECTIVE 6, as written: at least 20 percent less water than fixed interval")
    water_change = _pct(p3.water_mm, p0.water_mm)
    met = "MET" if water_change <= -20.0 else "NOT MET"
    direction = "less" if water_change < 0 else "MORE"
    print(f"    P3 vs P0: {abs(water_change):.1f} percent {direction} water -- {met}")
    print(
        f"    P3 also reaches {_pct(p3.stress_days, p0.stress_days):+.1f} percent stress days "
        f"and {_pct(p3.deep_percolation_mm, p0.deep_percolation_mm):+.1f} percent deep percolation."
    )
    a3, a0 = all_fields[Policy.P3_WINDOW_SKIP], all_fields[Policy.P0_CALENDAR]
    print(
        f"    on all nine fields including rice: {_pct(a3.water_mm, a0.water_mm):+.1f} percent "
        f"water, {_pct(a3.stress_days, a0.stress_days):+.1f} percent stress days"
    )

    print()
    print("  NOVELTY CLAIM: P3 versus P1, a conventional advisory under the same")
    print("  power constraint. This is the comparison the contribution rests on.")
    print("  Six non-ponded fields; the all-nine figure follows.")
    print(f"    water          {p3.water_mm:8.0f} vs {p1.water_mm:8.0f}   {_pct(p3.water_mm, p1.water_mm):+7.1f} percent")
    print(f"    stress days    {p3.stress_days:8d} vs {p1.stress_days:8d}   {_pct(p3.stress_days, p1.stress_days):+7.1f} percent")
    print(f"    percolation    {p3.deep_percolation_mm:8.0f} vs {p1.deep_percolation_mm:8.0f}   {_pct(p3.deep_percolation_mm, p1.deep_percolation_mm):+7.1f} percent")
    print(f"    pump hours     {p3.pump_hours:8.0f} vs {p1.pump_hours:8.0f}   {_pct(p3.pump_hours, p1.pump_hours):+7.1f} percent")
    a1 = all_fields[Policy.P1_ADVISORY]
    print(
        f"    all nine:      {_pct(a3.water_mm, a1.water_mm):+.1f} percent water, "
        f"{_pct(a3.stress_days, a1.stress_days):+.1f} percent stress days"
    )

    print()
    print("  PRICE OF RATIONED POWER: P3 versus Pref, the same scheduler with")
    print("  power on demand. Pref is physically unachievable.")
    print(f"    water          {p3.water_mm:8.0f} vs {pref.water_mm:8.0f}   {_pct(p3.water_mm, pref.water_mm):+7.1f} percent")
    print(f"    stress days    {p3.stress_days:8d} vs {pref.stress_days:8d}")

    water_better = p3.water_mm < p1.water_mm
    stress_better = p3.stress_days < p1.stress_days

    print()
    if water_better and stress_better:
        print("  HEADLINE: less water AND fewer stress days than a conventional")
        print("            advisory under the same power constraint.")
    elif stress_better:
        print(
            f"  HEADLINE: {abs(_pct(p3.stress_days, p1.stress_days)):.0f} percent fewer stress days than a conventional"
        )
        print(
            f"            advisory under the same power constraint, at {abs(_pct(p3.water_mm, p1.water_mm)):.0f} percent"
        )
        print("            higher water use. The scheduler buys reliability with water,")
        print("            because it must pre-fill against a window that may not come.")
        print("            Six non-ponded fields, two seasons.")
        print(f"            Objective 6 as written is {met} and is reported as measured.")
    else:
        print("  *** P3 LOSES TO P1 ON BOTH WATER AND STRESS DAYS. ***")
        print("      This is a policy problem, not a reporting one. Escalate.")


if __name__ == "__main__":
    raise SystemExit(main())
