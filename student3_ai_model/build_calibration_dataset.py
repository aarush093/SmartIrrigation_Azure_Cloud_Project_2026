"""Assemble forecast-versus-observed pairs for the rain calibration model.

The skip rule must know how much to trust a forecast before it tells a farmer
not to irrigate. That trust is learned here, per district and month, from what
past forecasts actually turned into.

Each training row pairs a forecast **as it was issued** with what was later
observed over the same horizon:

    features   forecast probability, forecast amount, lead time, month, district
    label      did the observed rain over that horizon cover a given deficit

The Previous Runs API is what makes this possible: it serves the forecast as it
stood on an earlier day, rather than the archive's hindsight. Using the archive
on both sides would train the model on a forecast that was never wrong, which is
the one thing this dataset must not do.

Sources, all in ``dataset/README.md``:

    D8  Open-Meteo Previous Runs        the forecast as issued
    D2  Open-Meteo Historical Archive   what actually happened
    D3  NASA POWER                      an independent check on the observations

Nothing downloaded here goes into git: ``data/raw/`` is already ignored. Only the
trained model summary and the figures reach ``results/``.

TODO Krishna: implement. The Previous Runs API is the part worth reading the
documentation for; the rest is joining on date and grid cell.
"""

from __future__ import annotations

import argparse
from pathlib import Path

PREVIOUS_RUNS_URL = "https://previous-runs-api.open-meteo.com/v1/forecast"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
POWER_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"

# The three pilot districts, from plan Section 12.
SITES = (
    ("Vellore TN", 12.97, 79.16),
    ("Beed MH", 18.99, 75.76),
    ("Ludhiana PB", 30.90, 75.86),
)

# Deficits to label against, mm. "Will it rain enough" is only answerable
# relative to a deficit: a forecast that covers 10 mm may not cover 40.
DEFICIT_THRESHOLDS_MM = (5.0, 10.0, 20.0, 30.0, 40.0)

# Lead times the scheduler actually uses. It projects to the start of the next
# power window, which in the pilot districts is one to three days out.
LEAD_TIMES_DAYS = (1, 2, 3)


def main(argv: list[str] | None = None) -> int:
    """Build the calibration dataset."""
    parser = argparse.ArgumentParser(description="Build forecast-versus-observed pairs.")
    parser.add_argument("--out", type=Path, default=Path("data/raw"))
    args = parser.parse_args(argv)

    print("Calibration dataset: Open-Meteo Previous Runs versus Historical Archive")
    print(f"  sites:      {len(SITES)}")
    print(f"  lead times: {LEAD_TIMES_DAYS} days")
    print(f"  deficits:   {DEFICIT_THRESHOLDS_MM} mm")
    print(f"  output:     {args.out} (gitignored)")
    print()
    print("  NOT IMPLEMENTED.")
    print("  Use Previous Runs for the forecast side. Using the archive on both")
    print("  sides would train the model on a forecast that was never wrong.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
