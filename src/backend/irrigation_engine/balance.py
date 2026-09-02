"""Root-zone water balance.

Tracks depletion ``Dr`` day by day. This is the state the whole system turns on:
the scheduler asks how much water the root zone is short, and the pump-minutes
conversion turns that shortfall into a running time.

Reference: FAO-56 equation 85,

    Dr,i = Dr,i-1 - (P - RO)i - Ii + ETc,i + DPi

bounded to ``0 <= Dr <= TAW``. Rainfall below a configurable threshold is not
credited to the root zone at all, because light rain on a dry surface evaporates
before it infiltrates; the default threshold is 3 mm/day (plan Section 6).

Implemented in M1.
"""

from __future__ import annotations

from irrigation_engine.models import CropStage, DailyWeather, WaterBalanceState

__all__ = ["WaterBalance", "effective_rainfall", "scs_runoff"]


class WaterBalance:
    """Stateless stepper for the FAO-56 root-zone water balance.

    Deliberately stateless: each call takes the previous depletion and returns
    the next, so the same object drives the live daily loop, the seven-day
    forward projection inside the scheduler, and the two-season simulation
    without any of them contaminating each other.
    """

    def __init__(
        self,
        *,
        min_effective_rain_mm: float = 3.0,
        use_scs_runoff: bool = False,
        curve_number: float | None = None,
    ) -> None:
        """Configure the balance.

        Args:
            min_effective_rain_mm: Daily rainfall at or below this depth is
                ignored entirely. Default 3.0 mm; see plan Section 6.
            use_scs_runoff: Whether to subtract a Soil Conservation Service curve
                number runoff term from rainfall. Off by default, because it
                needs a curve number the pilot does not yet have per field.
            curve_number: SCS curve number for the field. Required when
                ``use_scs_runoff`` is set.

        Raises:
            ValueError: If runoff is enabled without a curve number.
        """
        raise NotImplementedError("M1")

    def step(
        self,
        prev_depletion_mm: float,
        weather_day: DailyWeather,
        stage: CropStage,
        irrigation_mm: float = 0.0,
        *,
        taw_mm: float,
    ) -> WaterBalanceState:
        """Advance the balance by one day.

        Args:
            prev_depletion_mm: Depletion Dr at the end of the previous day, mm.
            weather_day: The day's ET0 and rainfall.
            stage: Crop parameters for the day, supplying Kc and p.
            irrigation_mm: Net irrigation depth applied on the day, mm. Net, not
                gross: application efficiency is handled in
                :mod:`irrigation_engine.pump`.
            taw_mm: Total available water in the root zone, mm.

        Returns:
            The full balance state for the day, including the deep percolation
            and runoff terms, which the simulation study reports separately.

        Raises:
            ValueError: If ``prev_depletion_mm`` is negative or exceeds
                ``taw_mm``.
        """
        raise NotImplementedError("M1: FAO-56 equation 85")


def effective_rainfall(precipitation_mm: float, *, threshold_mm: float = 3.0) -> float:
    """Credit rainfall to the root zone, discarding depths below the threshold.

    Args:
        precipitation_mm: Gross rainfall for the day, mm.
        threshold_mm: Depth at or below which rainfall is ignored, mm.

    Returns:
        Rainfall credited to the root zone, mm.
    """
    raise NotImplementedError("M1")


def scs_runoff(precipitation_mm: float, curve_number: float) -> float:
    """Estimate surface runoff by the Soil Conservation Service curve number method.

    Args:
        precipitation_mm: Gross rainfall for the day, mm.
        curve_number: SCS curve number for the soil and cover, 30 to 100.

    Returns:
        Surface runoff, mm.

    Raises:
        ValueError: If the curve number falls outside 30 to 100.
    """
    raise NotImplementedError("M1")
