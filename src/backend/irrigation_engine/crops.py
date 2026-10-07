"""Crop calendar: FAO-56 stage parameters for a given crop on a given day.

Resolves the crop coefficient Kc, rooting depth Zr, allowable depletion fraction
p and yield response factor Ky for the day, by interpolating across the four
FAO-56 growth stages according to days after sowing.

Kc follows the standard FAO-56 shape: constant at ``Kc_ini`` through the initial
stage, a linear ramp to ``Kc_mid`` across the development stage, constant at
``Kc_mid`` through mid-season, and a linear ramp to ``Kc_end`` across the late
season. Rooting depth grows linearly from its value at emergence to the stage
maximum by the end of the development stage, since a crop cannot draw on water
its roots have not yet reached.

All values come from ``params/crops.yaml``. Sources: FAO-56 Table 11 for stage
lengths, Table 12 for Kc, Table 22 for Zr and p, and FAO-33 with FAO-66 updates
for Ky. **Ky does not appear in FAO-56.** Stage lengths for Indian conditions
carry ``TODO [VERIFY]`` in that file pending confirmation against ICAR and state
agricultural university packages of practice; see plan Sections 6 and 15.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

from irrigation_engine.models import CropStage, GrowthStage
from irrigation_engine.params import load_params

__all__ = ["adjust_depletion_fraction", "available_crops", "crop_calendar", "growing_period_days"]


def _crop_entry(crop: str) -> dict[str, Any]:
    """Fetch one crop's parameter block, or raise naming the alternatives."""
    crops: dict[str, Any] = load_params("crops")["crops"]
    try:
        entry: dict[str, Any] = crops[crop]
    except KeyError:
        msg = f"unknown crop {crop!r}; available: {', '.join(sorted(crops))}"
        raise KeyError(msg) from None
    return entry


def available_crops() -> tuple[str, ...]:
    """List the crop keys defined in ``params/crops.yaml``.

    Returns:
        Crop keys in the order they appear in the parameter file.
    """
    crops: dict[str, Any] = load_params("crops")["crops"]
    return tuple(crops)


def growing_period_days(crop: str) -> int:
    """Total length of the crop's growing period.

    Args:
        crop: Crop key as it appears in ``params/crops.yaml``.

    Returns:
        Sum of the four FAO-56 stage lengths, days.

    Raises:
        KeyError: If the crop is not present in ``params/crops.yaml``.
    """
    stages = _crop_entry(crop)["stage_days"]
    return int(stages["initial"] + stages["development"] + stages["mid"] + stages["late"])


def crop_calendar(crop: str, sowing_date: dt.date, today: dt.date) -> CropStage:
    """Resolve the FAO-56 stage parameters for a crop on a specific day.

    Args:
        crop: Crop key as it appears in ``params/crops.yaml``, for example
            ``"wheat"``.
        sowing_date: Date the crop was sown.
        today: Date to resolve parameters for.

    Returns:
        The crop's Kc, Zr, p and Ky for that day, with the stage it falls in.
        The stage name is returned alongside the numbers so that a call script
        can name the growth stage to the farmer in plain language.

    Raises:
        KeyError: If the crop is not present in ``params/crops.yaml``.
        ValueError: If ``today`` precedes ``sowing_date``, or falls beyond the
            end of the crop's total growing period.
    """
    entry = _crop_entry(crop)
    days = (today - sowing_date).days

    if days < 0:
        msg = f"{today} precedes the sowing date {sowing_date} for {crop!r}"
        raise ValueError(msg)

    lengths = entry["stage_days"]
    l_ini = int(lengths["initial"])
    l_dev = int(lengths["development"])
    l_mid = int(lengths["mid"])
    l_late = int(lengths["late"])
    total = l_ini + l_dev + l_mid + l_late

    if days > total:
        msg = (
            f"{today} is {days} days after sowing, beyond the {total}-day growing "
            f"period for {crop!r}. The field needs a new sowing date, or the crop "
            f"has been harvested."
        )
        raise ValueError(msg)

    stage, kc = _stage_and_kc(entry, days, l_ini, l_dev, l_mid)
    root_depth_m = _root_depth(entry, days, l_ini, l_dev)

    return CropStage(
        crop=crop,
        stage=stage,
        days_after_sowing=days,
        kc=kc,
        root_depth_m=root_depth_m,
        depletion_fraction=float(entry["depletion_fraction"]),
        yield_response_factor=float(entry["ky"]),
    )


def _stage_and_kc(
    entry: dict[str, Any], days: int, l_ini: int, l_dev: int, l_mid: int
) -> tuple[GrowthStage, float]:
    """Locate the day in the four-stage curve and interpolate Kc.

    FAO-56 Figure 34: flat at Kc_ini, linear ramp through development, flat at
    Kc_mid, linear ramp through late season to Kc_end.
    """
    kc_ini = float(entry["kc_initial"])
    kc_mid = float(entry["kc_mid"])
    kc_end = float(entry["kc_end"])

    if days <= l_ini:
        return GrowthStage.INITIAL, kc_ini

    if days <= l_ini + l_dev:
        fraction = (days - l_ini) / l_dev if l_dev > 0 else 1.0
        return GrowthStage.DEVELOPMENT, kc_ini + fraction * (kc_mid - kc_ini)

    if days <= l_ini + l_dev + l_mid:
        return GrowthStage.MID, kc_mid

    l_late = int(entry["stage_days"]["late"])
    fraction = (days - l_ini - l_dev - l_mid) / l_late if l_late > 0 else 1.0
    return GrowthStage.LATE, kc_mid + fraction * (kc_end - kc_mid)


def _root_depth(entry: dict[str, Any], days: int, l_ini: int, l_dev: int) -> float:
    """Interpolate rooting depth from emergence to the stage maximum.

    Roots reach their maximum depth by the end of the development stage and hold
    it thereafter. Modelling this matters: crediting a seedling with a mature
    root zone would overstate available water and delay the first irrigation.
    """
    z_max = float(entry["root_depth_m"])
    z_ini = float(entry["root_depth_initial_m"])
    growth_period = l_ini + l_dev

    if days >= growth_period or growth_period <= 0:
        return z_max
    return z_ini + (days / growth_period) * (z_max - z_ini)


def adjust_depletion_fraction(p_table: float, etc_mm: float) -> float:
    """Adjust the tabulated depletion fraction for the day's evaporative demand.

    FAO-56 Table 22 accompanying note: ``p = p_table + 0.04 (5 - ETc)``, clamped
    to 0.1 to 0.8. A crop tolerates proportionally less depletion on a
    high-demand day, because the soil cannot deliver water to the roots fast
    enough to meet the atmospheric demand.

    Args:
        p_table: Tabulated depletion fraction for the crop.
        etc_mm: Crop evapotranspiration for the day, mm.

    Returns:
        The adjusted depletion fraction, dimensionless, in the range 0.1 to 0.8.

    Raises:
        ValueError: If ``etc_mm`` is negative.
    """
    if etc_mm < 0.0:
        msg = f"crop evapotranspiration cannot be negative, got {etc_mm} mm"
        raise ValueError(msg)

    adjustment = load_params("crops")["depletion_adjustment"]
    p_adj = p_table + float(adjustment["coefficient"]) * (
        float(adjustment["reference_etc_mm"]) - etc_mm
    )
    return min(max(p_adj, float(adjustment["min_p"])), float(adjustment["max_p"]))
