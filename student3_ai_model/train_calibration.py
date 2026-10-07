"""Train the calibrated rain probability that the forecast-skip rule consumes.

The raw forecast probability is not directly usable. "Eighty percent chance of
rain" from a numerical weather model is not the same statement as "eighty
percent of the time, in this district, in this month, at this lead time, enough
rain fell to cover the deficit". This model learns the second from the first.

The output feeds ``RainForecast.covers`` in the engine, which requires **both**
that the expected amount covers the deficit **and** that the calibrated
confidence clears a threshold. Either alone is not enough: a confident forecast
of insufficient rain does not justify a skip, and neither does a large forecast
the model does not trust.

**Prefer under-confidence.** A needless irrigation costs water. A wrongly
skipped one costs the crop, because the next power window may be three days
away. Where the model is uncertain it should say so, and the scheduler will
irrigate.

Report, against the raw forecast probability as the baseline:

    Brier score           lower is better; the headline number
    reliability diagram   shows whether a stated 0.8 actually means 0.8
    sharpness             a model that always answers 0.5 is perfectly
                          calibrated and completely useless, so calibration
                          alone is not sufficient

A **monotone** model is preferred over a black box. The probability that rain
covers a deficit must not fall as the forecast amount rises, and a monotone
constraint makes that impossible rather than merely unlikely. A monotone
gradient-boosted classifier or a logistic model on monotone features both work;
a plain neural network does not give the guarantee.

TODO Krishna: implement.
"""

from __future__ import annotations

import argparse
from pathlib import Path

RESULTS = Path("results")

# Features, in the order the monotone constraints below apply to them.
FEATURES = (
    "forecast_probability",  # monotone increasing
    "forecast_amount_mm",  # monotone increasing
    "lead_time_days",  # monotone decreasing: a longer lead is less trustworthy
    "deficit_mm",  # monotone decreasing: a larger deficit is harder to cover
    "month",  # categorical
    "district",  # categorical
)

# +1 increasing, -1 decreasing, 0 unconstrained.
MONOTONE_CONSTRAINTS = (1, 1, -1, -1, 0, 0)

# The threshold the engine applies to this model's output. Set deliberately
# high: below it, the scheduler irrigates rather than skipping.
ENGINE_CONFIDENCE_THRESHOLD = 0.7


def main(argv: list[str] | None = None) -> int:
    """Fit and evaluate the calibration model."""
    parser = argparse.ArgumentParser(description="Train the rain calibration model.")
    parser.add_argument("--out", type=Path, default=RESULTS)
    parser.add_argument("--data", type=Path, default=Path("data/raw"))
    args = parser.parse_args(argv)

    print("Forecast calibration")
    print("  learns: P(observed rain covers the deficit | forecast, lead, month, district)")
    print(f"  features: {len(FEATURES)}, monotone constraints {MONOTONE_CONSTRAINTS}")
    print("  baseline: the raw forecast probability")
    print(f"  engine threshold: {ENGINE_CONFIDENCE_THRESHOLD}")
    print(f"  data in {args.data}, results to {args.out}")
    print()
    print("  NOT IMPLEMENTED.")
    print("  Beating the raw forecast on Brier score is the acceptance criterion.")
    print("  If it is not beaten, say so; the scheduler keeps its conservative")
    print("  default and the skip rule simply fires less often.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
