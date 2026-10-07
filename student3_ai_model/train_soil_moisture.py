"""Objective 3: forecast root-zone soil moisture one to seven days ahead.

Retained from Phase-I. The acceptance criterion is R-squared at or above 0.80 on
a held-out season.

**This model is deliberately not on the critical path.** The scheduler talks to
the engine's ``MoistureForecaster`` protocol, whose default implementation is
``KcEt0Forecaster`` (ETc = Kc x ET0) and always works. If this model misses its
target, the fallback stays active and nothing downstream changes.

That is why reporting a shortfall honestly costs the project nothing, and why
inflating a number would cost it everything. This project has already reported
one objective as not met, with the measurement behind it, and it strengthened
the work rather than weakening it.

To put this model into the engine, satisfy the same protocol:

    class LstmForecaster:
        @property
        def name(self) -> str:
            return "lstm-v1"

        def forecast_etc(self, weather, stages) -> list[float]:
            ...

``tests/test_forecasting.py`` already contains a test asserting that a
substitute implementation satisfies the protocol, so there is a working example
to copy.

Two rules that matter more than the architecture:

1. **Chronological split, by season, never random.** A random split lets
   tomorrow's weather train the model that predicts tomorrow. The resulting
   R-squared looks excellent and means nothing. Enforced by
   :func:`chronological_split` below; do not replace it with a shuffled split.
2. **Free inputs only.** No feature may require a soil moisture sensor, or the
   sensor-optional claim at the centre of this project becomes false.
"""

from __future__ import annotations

import argparse
import datetime as dt
from dataclasses import dataclass
from pathlib import Path

RESULTS = Path("results")

# Features obtainable at zero cost from public APIs. Adding anything here that
# needs on-farm hardware breaks the project's central claim.
FEATURES = (
    "et0_mm",
    "precipitation_mm",
    "temp_max_c",
    "temp_min_c",
    "kc",
    "root_depth_m",
    "theta_fc",
    "theta_wp",
    "cumulative_deficit_mm",
    "antecedent_rain_1d",
    "antecedent_rain_3d",
    "antecedent_rain_7d",
    "days_after_sowing",
)

HORIZONS_DAYS = (1, 2, 3, 4, 5, 6, 7)
TARGET_R2 = 0.80


@dataclass(frozen=True)
class Scores:
    """Held-out performance at one forecast horizon."""

    horizon_days: int
    r2: float
    rmse: float
    n: int

    @property
    def meets_target(self) -> bool:
        """Whether this horizon reaches the Objective 3 criterion."""
        return self.r2 >= TARGET_R2


def chronological_split(
    dates: list[dt.date], test_fraction: float = 0.3
) -> tuple[list[int], list[int]]:
    """Split indices by time, never at random.

    The last ``test_fraction`` of the record by date is held out, so the model
    is always predicting forward. Shuffling here would leak future information
    into training and inflate every metric that follows it.

    Args:
        dates: Observation dates, one per row.
        test_fraction: Share of the record held out, taken from the end.

    Returns:
        Training and test index lists, both in date order.

    Raises:
        ValueError: If the fraction is not strictly between 0 and 1, or leaves
            one side empty.
    """
    if not 0.0 < test_fraction < 1.0:
        msg = f"test_fraction must lie strictly between 0 and 1, got {test_fraction}"
        raise ValueError(msg)

    order = sorted(range(len(dates)), key=lambda index: dates[index])
    cut = int(len(order) * (1.0 - test_fraction))
    if cut in (0, len(order)):
        msg = "the split leaves one side empty; supply a longer record"
        raise ValueError(msg)
    return order[:cut], order[cut:]


def report(scores: list[Scores]) -> None:
    """Print the result, whatever it is.

    Prints the measured R-squared per horizon against the target, and says
    plainly whether the objective is met. If it is not, that is the number that
    goes in the report.
    """
    print(f"  {'horizon':>8}{'n':>8}{'R2':>9}{'RMSE':>9}   verdict")
    for score in scores:
        verdict = "meets 0.80" if score.meets_target else "BELOW TARGET"
        print(
            f"  {score.horizon_days:>8}{score.n:>8}{score.r2:>9.3f}"
            f"{score.rmse:>9.3f}   {verdict}"
        )

    met = [s for s in scores if s.meets_target]
    print()
    if len(met) == len(scores):
        print("  Objective 3 MET at every horizon.")
    elif met:
        horizons = ", ".join(str(s.horizon_days) for s in met)
        print(f"  Objective 3 met at horizons {horizons} only. Report the rest as measured.")
    else:
        print("  Objective 3 NOT MET at any horizon.")
        print("  The engine falls back to Kc x forecast ET0, so the system keeps working.")
        print("  Report the measured numbers and the fallback; do not adjust the target.")


def main(argv: list[str] | None = None) -> int:
    """Train and evaluate, and report whatever number comes out.

    TODO Krishna: implement. The feature list, the split rule and the reporting
    contract are fixed here so the result is comparable and honest whatever
    architecture you choose.
    """
    parser = argparse.ArgumentParser(description="Train the Objective 3 soil-moisture model.")
    parser.add_argument("--out", type=Path, default=RESULTS)
    parser.add_argument("--test-fraction", type=float, default=0.3)
    args = parser.parse_args(argv)

    print("Objective 3: root-zone soil moisture, one to seven days ahead")
    print(f"  target R-squared:  {TARGET_R2}")
    print(f"  features:          {len(FEATURES)}, all free, none requiring a sensor")
    print(f"  split:             chronological, last {args.test_fraction:.0%} held out")
    print(f"  output:            {args.out}")
    print()
    print("  NOT IMPLEMENTED.")
    print("  Report the R-squared you actually obtain, per horizon. If it is")
    print("  below target, say so: the engine falls back to Kc x forecast ET0")
    print("  and nothing else changes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
