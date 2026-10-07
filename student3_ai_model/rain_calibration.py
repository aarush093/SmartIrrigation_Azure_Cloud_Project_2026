"""Measure how far a rain forecast can be trusted to cover a deficit.

The scheduler's skip rule needs a probability, and the historical archive does
not carry one: ``precipitation_probability`` is null for every past date in the
Previous Runs API. So the confidence is **measured** here rather than read.

What is estimated, empirically, from forecast-versus-observed pairs:

    P(observed rain over the horizon >= deficit | forecast rain, lead time)

Method, deliberately simple: bin the as-issued forecast total, and within each
bin count how often the observed total actually reached the deficit. A binned
empirical frequency is a legitimate calibration and has one large advantage over
a fitted model here, which is that it cannot be over-confident about a bin it
has never seen. It is also **monotone by construction** once the bins are
ordered, which a fitted model would need a constraint to guarantee.

**Split is chronological.** The table is built on the earlier season and
evaluated on the later one. Fitting and scoring on the same data would report a
Brier score that describes memorisation rather than skill.

This is the interim calibration the simulation uses. The trained model is
Krishna's deliverable in ``train_calibration.py``; when it lands it replaces
this table and should beat it, and the comparison is the acceptance criterion.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

__all__ = ["CalibrationTable", "brier_score", "build_table"]

#: Forecast-total bins, mm over the horizon. Chosen so the lowest bin is "the
#: forecast says essentially nothing" and the highest is "the forecast is
#: confident about a substantial event".
FORECAST_BINS_MM = (0.0, 1.0, 5.0, 10.0, 20.0, 40.0)

#: Deficits to calibrate against. "Will it rain enough" is only answerable
#: relative to how much water the field is short.
DEFICIT_BINS_MM = (5.0, 10.0, 20.0, 40.0)


def _bin_index(value: float, edges: tuple[float, ...]) -> int:
    """Index of the bin a value falls in, clamped to the ends."""
    for index in range(len(edges) - 1, -1, -1):
        if value >= edges[index]:
            return index
    return 0


@dataclass
class CalibrationTable:
    """Empirical P(observed covers deficit | forecast bin, deficit bin, lead)."""

    counts: dict[tuple[int, int, int], list[int]] = field(default_factory=dict)
    #: Fallback used for a cell with too little evidence to trust.
    min_samples: int = 20
    #: What to answer when a cell is unseen or too thin. Deliberately low: an
    #: unknown cell must not authorise a skip, because a wrong skip costs the
    #: farmer a whole irrigation interval.
    prior: float = 0.0

    def observe(self, forecast_mm: float, deficit_mm: float, lead: int, covered: bool) -> None:
        """Record one forecast-versus-observed pair."""
        key = (_bin_index(forecast_mm, FORECAST_BINS_MM), _bin_index(deficit_mm, DEFICIT_BINS_MM), lead)
        cell = self.counts.setdefault(key, [0, 0])
        cell[0] += 1
        cell[1] += int(covered)

    def probability(self, forecast_mm: float, deficit_mm: float, lead: int) -> float:
        """Calibrated probability that the forecast rain covers the deficit.

        Returns the prior for a cell with fewer than ``min_samples``
        observations, which keeps the rule from skipping on evidence it does not
        have.
        """
        key = (_bin_index(forecast_mm, FORECAST_BINS_MM), _bin_index(deficit_mm, DEFICIT_BINS_MM), lead)
        cell = self.counts.get(key)
        if cell is None or cell[0] < self.min_samples:
            return self.prior
        return cell[1] / cell[0]

    @property
    def cells(self) -> int:
        """How many cells carry enough evidence to be used."""
        return sum(1 for cell in self.counts.values() if cell[0] >= self.min_samples)

    @property
    def samples(self) -> int:
        """Total pairs observed."""
        return sum(cell[0] for cell in self.counts.values())


def build_table(pairs: list[tuple[float, float, int, bool]]) -> CalibrationTable:
    """Build a calibration table from forecast-versus-observed pairs.

    Args:
        pairs: ``(forecast_mm, deficit_mm, lead, covered)`` tuples.

    Returns:
        The fitted table.
    """
    table = CalibrationTable()
    for forecast_mm, deficit_mm, lead, covered in pairs:
        table.observe(forecast_mm, deficit_mm, lead, covered)
    return table


def brier_score(predictions: list[float], outcomes: list[bool]) -> float:
    """Mean squared error of a probabilistic forecast. Lower is better.

    Args:
        predictions: Probabilities in 0 to 1.
        outcomes: What actually happened.

    Returns:
        The Brier score.

    Raises:
        ValueError: If the two lists differ in length or are empty.
    """
    if len(predictions) != len(outcomes):
        msg = f"length mismatch: {len(predictions)} predictions, {len(outcomes)} outcomes"
        raise ValueError(msg)
    if not predictions:
        msg = "cannot score an empty set of predictions"
        raise ValueError(msg)
    return sum((p - float(o)) ** 2 for p, o in zip(predictions, outcomes, strict=True)) / len(
        predictions
    )


def raw_forecast_probability(forecast_mm: float, deficit_mm: float) -> float:
    """The naive baseline the calibration must beat.

    "The forecast says enough rain, so it will rain enough." This is what a
    system with no calibration effectively believes, and it is the comparison
    the acceptance criterion is stated against.
    """
    return 1.0 if forecast_mm >= deficit_mm else 0.0


def chronological_split(
    dates: list[dt.date], test_fraction: float = 0.5
) -> tuple[list[int], list[int]]:
    """Split indices by time. Never shuffle.

    Fitting and scoring on the same season would report memorisation rather than
    skill, and the resulting Brier score would be meaningless.
    """
    order = sorted(range(len(dates)), key=lambda index: dates[index])
    cut = int(len(order) * (1.0 - test_fraction))
    return order[:cut], order[cut:]
