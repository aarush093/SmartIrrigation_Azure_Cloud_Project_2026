"""Propagate the measured ET0 error through to pump minutes.

"MAE 0.279 mm/day, criterion not met" is not a useful statement on its own. The
question a reviewer asks next is whether it matters to the farmer, and the only
answer that means anything is expressed in the unit the farmer acts on: minutes
of pump running time.

This harness propagates each measured ET0 error term through the full chain
(ET0 -> ETc -> net depth -> gross depth -> volume -> minutes) on the worked
example field, and sets the result beside the uncertainty the recommendation
already carries from application efficiency and pump discharge.

Field, from plan Section 6: wheat at mid-season (Kc 1.15), one acre (4,047 m2),
furrow irrigation (Ea 0.65), 5 HP pump against 30 m head giving 380.2 L/min, on
a seven-day irrigation interval.

Bias and scatter do not propagate the same way, and the distinction is the
substance of this analysis. A bias accumulates linearly across the interval,
because every day's error points the same way. Random scatter accumulates as the
square root of the number of days, because errors partly cancel. A water balance
integrates, so it is bias, not scatter, that matters.

Needs no network: it consumes the error statistics measured by
``et0_crosscheck.py`` and runs the engine. Marked ``integration`` only to keep it
out of the CI unit suite alongside the other validation harnesses.
"""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path

import pytest

from irrigation_engine.models import IrrigationMethod, PumpSpec
from irrigation_engine.pump import pump_minutes, required_pump_minutes, resolve_efficiency

RESULTS_PATH = Path(__file__).resolve().parents[2] / "results" / "objective2_sensitivity.csv"

# The worked example field.
KC_MID = 1.15
AREA_M2 = 4047.0
METHOD = IrrigationMethod.FURROW
PUMP = PumpSpec(hp=5.0, head_m=30.0, eta=0.5)
INTERVAL_DAYS = 7
BASELINE_DEPLETION_MM = 25.0

# Measured by tests/validation/et0_crosscheck.py over 1,095 station-days in 2025.
OVERALL_BIAS = 0.065
VELLORE_BIAS = 0.205
OVERALL_MAE = 0.279

# Application efficiency range across methods, FAO Training Manual 4, used to
# put the ET0 uncertainty in proportion.
EA_LOW = 0.55  # flood or basin
EA_HIGH = 0.75  # sprinkler


@dataclass(frozen=True)
class Term:
    """One error term and how it accumulates over the irrigation interval."""

    label: str
    et0_error_mm_per_day: float
    correlated: bool

    @property
    def etc_error_mm(self) -> float:
        """Accumulated ETc error over the interval, mm.

        A correlated (bias) term accumulates linearly. An independent (scatter)
        term accumulates as the square root of the number of days.
        """
        days = INTERVAL_DAYS if self.correlated else math.sqrt(INTERVAL_DAYS)
        return self.et0_error_mm_per_day * KC_MID * days


TERMS = (
    Term(f"Overall bias +{OVERALL_BIAS} mm/day", OVERALL_BIAS, correlated=True),
    Term(f"Vellore bias +{VELLORE_BIAS} mm/day", VELLORE_BIAS, correlated=True),
    Term(f"MAE {OVERALL_MAE} mm/day, fully correlated", OVERALL_MAE, correlated=True),
    Term(f"MAE {OVERALL_MAE} mm/day, independent across days", OVERALL_MAE, correlated=False),
)


def minutes_for_depth(net_depth_mm: float) -> float:
    """Running time for a net depth on the worked example field."""
    return required_pump_minutes(net_depth_mm, AREA_M2, METHOD, PUMP)


@pytest.mark.integration
def test_et0_error_sensitivity_to_pump_minutes() -> None:
    """Report the ET0 uncertainty budget in pump minutes, against Ea and discharge."""
    baseline_minutes = pump_minutes(BASELINE_DEPLETION_MM, AREA_M2, METHOD, PUMP)

    rows: list[tuple[str, float, float, float]] = []
    for term in TERMS:
        extra_minutes = minutes_for_depth(term.etc_error_mm)
        rows.append(
            (term.label, term.etc_error_mm, extra_minutes, extra_minutes / baseline_minutes)
        )

    # The uncertainty the recommendation already carries, for proportion.
    ea_low_minutes = required_pump_minutes(BASELINE_DEPLETION_MM, AREA_M2, EA_LOW, PUMP)
    ea_high_minutes = required_pump_minutes(BASELINE_DEPLETION_MM, AREA_M2, EA_HIGH, PUMP)
    ea_spread = ea_low_minutes - ea_high_minutes

    # A twenty percent discharge error, which a declared head and an assumed
    # efficiency can easily produce when no bucket test was performed.
    discharge_spread = minutes_for_depth(BASELINE_DEPLETION_MM) * (1.0 / 0.8 - 1.0)

    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with RESULTS_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["# Objective 2 uncertainty budget, expressed in pump minutes"])
        writer.writerow(
            [
                f"# wheat mid-season Kc {KC_MID}, {AREA_M2} m2, furrow Ea "
                f"{resolve_efficiency(METHOD)}, {INTERVAL_DAYS}-day interval"
            ]
        )
        writer.writerow(
            [f"# baseline run for {BASELINE_DEPLETION_MM} mm net = {baseline_minutes:.1f} min"]
        )
        writer.writerow([])
        writer.writerow(
            [
                "error_term",
                "etc_error_mm_over_7_days",
                "extra_pump_minutes",
                "share_of_baseline",
            ]
        )
        for label, etc_error, minutes, share in rows:
            writer.writerow([label, f"{etc_error:.2f}", f"{minutes:.1f}", f"{share:.3f}"])
        writer.writerow([])
        writer.writerow(["comparison_term", "minutes_spread", "share_of_baseline"])
        writer.writerow(
            [
                f"Application efficiency Ea {EA_LOW} vs {EA_HIGH}",
                f"{ea_spread:.1f}",
                f"{ea_spread / baseline_minutes:.3f}",
            ]
        )
        writer.writerow(
            [
                "Pump discharge 20 percent low (no bucket test)",
                f"{discharge_spread:.1f}",
                f"{discharge_spread / baseline_minutes:.3f}",
            ]
        )

    print()
    print("Objective 2 uncertainty budget, expressed in pump minutes")
    print(
        f"  field: wheat mid-season Kc {KC_MID}, one acre, furrow Ea "
        f"{resolve_efficiency(METHOD)}, {INTERVAL_DAYS}-day interval"
    )
    print(
        f"  baseline run for {BASELINE_DEPLETION_MM:.0f} mm net depth: "
        f"{baseline_minutes:.1f} minutes"
    )
    print()
    print(f"  {'error term':<46}{'ETc/7d':>9}{'minutes':>9}{'share':>8}")
    for label, etc_error, minutes, share in rows:
        print(f"  {label:<46}{etc_error:>9.2f}{minutes:>9.1f}{share:>8.1%}")
    print()
    print(f"  {'for comparison, uncertainty already carried':<46}{'':>9}{'minutes':>9}{'share':>8}")
    print(
        f"  {f'application efficiency Ea {EA_LOW} vs {EA_HIGH}':<46}{'':>9}"
        f"{ea_spread:>9.1f}{ea_spread / baseline_minutes:>8.1%}"
    )
    print(
        f"  {'pump discharge 20 percent low (no bucket test)':<46}{'':>9}"
        f"{discharge_spread:>9.1f}{discharge_spread / baseline_minutes:>8.1%}"
    )
    print()

    worst_et0 = max(minutes for _, _, minutes, _ in rows)
    ratio = ea_spread / worst_et0
    print(f"  CONCLUSION: the largest ET0 error term costs {worst_et0:.0f} minutes,")
    print(f"  while application efficiency alone spans {ea_spread:.0f} minutes on the")
    print(f"  same field, a factor of {ratio:.1f}. At this residual, ET0 is not the")
    print("  limiting factor in pump-minute accuracy.")
    print()

    # The claim made in the report must hold, or it is not made.
    assert ea_spread > worst_et0, (
        "the report claims application efficiency dominates the ET0 residual; "
        f"measured Ea spread {ea_spread:.1f} min vs worst ET0 term {worst_et0:.1f} min"
    )
    assert rows[0][3] < 0.05, (
        f"overall bias should cost under 5 percent of the run, measured {rows[0][3]:.1%}"
    )
