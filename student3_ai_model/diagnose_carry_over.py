"""Diagnostic: is the carry-over double count what drives P2's excess water?

Runs P2 twice over exactly the same data, once with the requirement computed as
``depletion + carry_over`` and once as ``depletion`` alone, and prints Pref
beside them as the physical reference. Nothing else changes between the arms.

The hypothesis being tested is that the water balance is stepped with the depth
actually *delivered*, so the undelivered part of a truncated run is already
inside the next day's depletion, and adding carry-over on top asks for it twice.

Run:  python handoff/student3_ai_model/diagnose_carry_over.py
"""

from __future__ import annotations

import datetime as dt

import simulate_policies as sim
from forecast_source import fetch_as_issued
from irrigation_engine.models import DailyWeather
from irrigation_engine.providers import OpenMeteoProvider

SEASONS = (2024, 2025)


def _totals(rows: list[sim.Totals]) -> tuple[float, float, int, float]:
    return (
        sum(r.water_mm for r in rows),
        sum(r.deep_percolation_mm for r in rows),
        sum(r.stress_days for r in rows),
        sum(r.pump_hours for r in rows),
    )


def main() -> int:
    """Run both arms and print the comparison."""
    provider = OpenMeteoProvider()
    sites = {f.site: (f.latitude, f.longitude) for f in sim.FIELDS}
    start = dt.date(min(SEASONS), 5, 1)
    end = dt.date(max(SEASONS) + 1, 4, 30)

    print("Fetching observed weather and forecasts as issued...")
    archives: dict[str, dict[dt.date, DailyWeather]] = {}
    forecasts: dict[str, object] = {}
    for site, (lat, lon) in sites.items():
        days = provider.fetch_archive(lat, lon, start, end)
        archives[site] = {d.date: d for d in days}
        forecasts[site] = fetch_as_issued(lat, lon, start, end)
        print(f"  {site}: {len(days)} observed days")

    split = dt.date(min(SEASONS) + 1, 5, 1)
    table, _, _, _ = sim.build_calibration(sim.FIELDS, archives, forecasts, split)

    def run(policy: sim.Policy) -> list[sim.Totals]:
        out = []
        for season in SEASONS:
            for spec in sim.FIELDS:
                month, dayof = spec.sowing_month_day
                out.append(
                    sim.run_policy(
                        policy,
                        spec,
                        archives[spec.site],
                        forecasts[spec.site],
                        table,
                        dt.date(season, month, dayof),
                        str(season),
                    )
                )
        return out

    print()
    sim.CARRY_OVER_IN_REQUIREMENT = True
    with_carry = _totals(run(sim.Policy.P2_WINDOW))
    sim.CARRY_OVER_IN_REQUIREMENT = False
    without_carry = _totals(run(sim.Policy.P2_WINDOW))
    pref = _totals(run(sim.Policy.PREF_UNLIMITED))

    print(f"  {'arm':<38}{'water mm':>10}{'perc mm':>10}{'stress':>8}{'pump h':>9}")
    for label, vals in (
        ("P2, required = depletion + carry_over", with_carry),
        ("P2, required = depletion", without_carry),
        ("Pref, unlimited power (reference)", pref),
    ):
        w, p, s, h = vals
        print(f"  {label:<38}{w:>10.0f}{p:>10.0f}{s:>8}{h:>9.0f}")

    dw = with_carry[0] - without_carry[0]
    dp = with_carry[1] - without_carry[1]
    print()
    print(f"  the double count accounts for {dw:.0f} mm of water and {dp:.0f} mm of percolation")
    print(f"  P2 without it is {without_carry[0] - pref[0]:+.0f} mm against Pref")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
