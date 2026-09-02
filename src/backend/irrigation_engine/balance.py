"""Root-zone water balance.

Tracks depletion ``Dr`` day by day. This is the state the whole system turns on:
the scheduler asks how much water the root zone is short, and the pump-minutes
conversion turns that shortfall into a running time.

FAO-56 equation 85:

    Dr,i = Dr,i-1 - (P - RO)i - Ii + ETc,i + DPi

bounded to ``0 <= Dr <= TAW``, with deep percolation from equation 88:

    DP = max(0, (P - RO) + I - ETc - Dr,i-1)

Rainfall below a configurable threshold is not credited to the root zone at all,
because light rain on a dry surface evaporates before it infiltrates; the default
threshold is 3 mm/day (plan Section 6).
"""

from __future__ import annotations

from irrigation_engine.crops import adjust_depletion_fraction
from irrigation_engine.models import CropStage, DailyWeather, WaterBalanceState
from irrigation_engine.params import load_params
from irrigation_engine.soil import readily_available_water

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
        min_effective_rain_mm: float | None = None,
        use_scs_runoff: bool | None = None,
        curve_number: float | None = None,
    ) -> None:
        """Configure the balance.

        Args:
            min_effective_rain_mm: Daily rainfall at or below this depth is
                ignored entirely. Defaults to the value in
                ``params/irrigation.yaml``, currently 3.0 mm.
            use_scs_runoff: Whether to subtract a Soil Conservation Service curve
                number runoff term from rainfall. Defaults to the parameter file,
                where it is off, because the pilot has no per-field curve number
                and a wrong one silently removes water the crop received.
            curve_number: SCS curve number for the field. Required when runoff is
                enabled.

        Raises:
            ValueError: If runoff is enabled without a curve number, or the
                curve number is outside the valid range.
        """
        config = load_params("irrigation")["water_balance"]

        self.min_effective_rain_mm = (
            float(config["min_effective_rain_mm"])
            if min_effective_rain_mm is None
            else min_effective_rain_mm
        )
        self.use_scs_runoff = (
            bool(config["use_scs_runoff"]) if use_scs_runoff is None else use_scs_runoff
        )
        self.curve_number = curve_number

        if self.use_scs_runoff:
            if self.curve_number is None:
                msg = "use_scs_runoff is enabled but no curve_number was supplied"
                raise ValueError(msg)
            bounds = config["curve_number_bounds"]
            if not bounds["min"] <= self.curve_number <= bounds["max"]:
                msg = (
                    f"curve number {self.curve_number} is outside the valid range "
                    f"{bounds['min']} to {bounds['max']}"
                )
                raise ValueError(msg)

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
                ``taw_mm``, if ``irrigation_mm`` is negative, or if ``taw_mm``
                is not positive.
        """
        if taw_mm <= 0.0:
            msg = f"total available water must be positive, got {taw_mm} mm"
            raise ValueError(msg)
        if prev_depletion_mm < 0.0:
            msg = f"previous depletion cannot be negative, got {prev_depletion_mm} mm"
            raise ValueError(msg)
        if prev_depletion_mm > taw_mm:
            msg = (
                f"previous depletion {prev_depletion_mm} mm exceeds total available "
                f"water {taw_mm} mm; the root zone cannot be drier than empty"
            )
            raise ValueError(msg)
        if irrigation_mm < 0.0:
            msg = f"irrigation cannot be negative, got {irrigation_mm} mm"
            raise ValueError(msg)

        etc_mm = stage.kc * weather_day.et0_mm

        runoff_mm = (
            scs_runoff(weather_day.precipitation_mm, self.curve_number)
            if self.use_scs_runoff and self.curve_number is not None
            else 0.0
        )
        rain_after_runoff = weather_day.precipitation_mm - runoff_mm
        effective_rain_mm = effective_rainfall(
            rain_after_runoff, threshold_mm=self.min_effective_rain_mm
        )

        # FAO-56 equation 88. Water arriving in excess of what the root zone can
        # hold drains below it and is lost to the crop.
        deep_percolation_mm = max(
            0.0, effective_rain_mm + irrigation_mm - etc_mm - prev_depletion_mm
        )

        # FAO-56 equation 85.
        depletion_mm = (
            prev_depletion_mm - effective_rain_mm - irrigation_mm + etc_mm + deep_percolation_mm
        )
        depletion_mm = min(max(depletion_mm, 0.0), taw_mm)

        p_adjusted = adjust_depletion_fraction(stage.depletion_fraction, etc_mm)

        return WaterBalanceState(
            date=weather_day.date,
            depletion_mm=depletion_mm,
            taw_mm=taw_mm,
            raw_mm=readily_available_water(taw_mm, p_adjusted),
            etc_mm=etc_mm,
            effective_rain_mm=effective_rain_mm,
            irrigation_mm=irrigation_mm,
            deep_percolation_mm=deep_percolation_mm,
            runoff_mm=runoff_mm,
        )


def effective_rainfall(precipitation_mm: float, *, threshold_mm: float = 3.0) -> float:
    """Credit rainfall to the root zone, discarding depths below the threshold.

    All-or-nothing rather than a subtraction: FAO-56 treats light rainfall as
    lost to evaporation from the surface, not as a partial credit.

    Args:
        precipitation_mm: Rainfall for the day after any runoff, mm.
        threshold_mm: Depth at or below which rainfall is ignored, mm.

    Returns:
        Rainfall credited to the root zone, mm.

    Raises:
        ValueError: If precipitation is negative.
    """
    if precipitation_mm < 0.0:
        msg = f"precipitation cannot be negative, got {precipitation_mm} mm"
        raise ValueError(msg)
    return 0.0 if precipitation_mm <= threshold_mm else precipitation_mm


def scs_runoff(precipitation_mm: float, curve_number: float) -> float:
    """Estimate surface runoff by the Soil Conservation Service curve number method.

    ``S = 25400 / CN - 254`` in millimetres, with initial abstraction
    ``Ia = 0.2 S``; runoff is zero until rainfall exceeds ``Ia``, and thereafter
    ``Q = (P - Ia)^2 / (P - Ia + S)``.

    Args:
        precipitation_mm: Gross rainfall for the day, mm.
        curve_number: SCS curve number for the soil and cover, 30 to 100.

    Returns:
        Surface runoff, mm.

    Raises:
        ValueError: If the curve number falls outside 30 to 100, or precipitation
            is negative.
    """
    bounds = load_params("irrigation")["water_balance"]["curve_number_bounds"]
    if not bounds["min"] <= curve_number <= bounds["max"]:
        msg = (
            f"curve number {curve_number} is outside the valid range "
            f"{bounds['min']} to {bounds['max']}"
        )
        raise ValueError(msg)
    if precipitation_mm < 0.0:
        msg = f"precipitation cannot be negative, got {precipitation_mm} mm"
        raise ValueError(msg)

    potential_retention = 25400.0 / curve_number - 254.0
    initial_abstraction = 0.2 * potential_retention
    if precipitation_mm <= initial_abstraction:
        return 0.0

    excess = precipitation_mm - initial_abstraction
    return excess**2 / (excess + potential_retention)
