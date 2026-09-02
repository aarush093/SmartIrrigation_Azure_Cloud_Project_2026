"""Crop calendar: FAO-56 stage parameters for a given crop on a given day.

Resolves the crop coefficient Kc, rooting depth Zr, allowable depletion fraction
p and yield response factor Ky for the day, by interpolating across the four
FAO-56 growth stages according to days after sowing.

All values come from ``params/crops.yaml``. Stage lengths for Indian conditions
are marked ``TODO [VERIFY]`` in that file pending confirmation against ICAR and
state agricultural university packages of practice; see plan Sections 6 and 15.

Implemented in M1.
"""

from __future__ import annotations

import datetime as dt

from irrigation_engine.models import CropStage

__all__ = ["adjust_depletion_fraction", "available_crops", "crop_calendar"]


def crop_calendar(crop: str, sowing_date: dt.date, today: dt.date) -> CropStage:
    """Resolve the FAO-56 stage parameters for a crop on a specific day.

    Kc is interpolated linearly across the development and late-season stages as
    FAO-56 prescribes, and held constant through the initial and mid-season
    stages. Rooting depth is interpolated from the sowing minimum to the stage
    maximum over the initial and development stages.

    Args:
        crop: Crop key as it appears in ``params/crops.yaml``, for example
            ``"wheat"``.
        sowing_date: Date the crop was sown.
        today: Date to resolve parameters for.

    Returns:
        The crop's Kc, Zr, p and Ky for that day, with the stage it falls in.

    Raises:
        KeyError: If the crop is not present in ``params/crops.yaml``.
        ValueError: If ``today`` precedes ``sowing_date``, or falls beyond the
            end of the crop's total growing period.
    """
    raise NotImplementedError("M1: FAO-56 Tables 11, 12 and 22")


def available_crops() -> tuple[str, ...]:
    """List the crop keys defined in ``params/crops.yaml``.

    Returns:
        Crop keys in the order they appear in the parameter file.
    """
    raise NotImplementedError("M1")


def adjust_depletion_fraction(p_table: float, etc_mm: float) -> float:
    """Adjust the tabulated depletion fraction for the day's evaporative demand.

    FAO-56 Table 22 note: ``p = p_table + 0.04 (5 - ETc)``, clamped to the range
    0.1 to 0.8. A crop tolerates proportionally less depletion on a high-demand
    day, because the soil cannot supply water to the roots fast enough.

    Args:
        p_table: Tabulated depletion fraction for the crop.
        etc_mm: Crop evapotranspiration for the day, mm.

    Returns:
        The adjusted depletion fraction, dimensionless.
    """
    raise NotImplementedError("M1: FAO-56 Table 22 footnote")
