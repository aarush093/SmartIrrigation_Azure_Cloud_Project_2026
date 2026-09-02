"""Pedotransfer from soil texture to plant-available water.

Converts the SoilGrids texture and bulk density of a field into the volumetric
water contents at field capacity and permanent wilting point, which is what
turns an evapotranspiration deficit into an irrigation depth. This is the step
that lets the system work on a field with no instrumentation at all.

Reference: K. E. Saxton and W. J. Rawls, "Soil water characteristic estimates by
texture and organic matter for hydrologic solutions", Soil Science Society of
America Journal, 70(5), pp. 1569-1578, 2006.

Implemented in M1.
"""

from __future__ import annotations

from irrigation_engine.models import SoilProfile, SoilWaterConstants

__all__ = ["saxton_rawls", "total_available_water"]


def saxton_rawls(soil: SoilProfile) -> SoilWaterConstants:
    """Estimate field capacity and wilting point from texture and organic matter.

    Applies the Saxton and Rawls (2006) regression equations for the -33 kPa and
    -1500 kPa moisture retention points, including the density adjustment. The
    regression coefficients live in ``params/soil.yaml`` with their equation
    numbers cited, never inline here.

    Args:
        soil: Depth-weighted 0 to 30 cm profile, normally from SoilGrids.

    Returns:
        Volumetric water content at field capacity and at wilting point.

    Raises:
        ValueError: If the sand, silt and clay fractions do not sum to
            approximately 1.0, which indicates a unit error upstream.
    """
    raise NotImplementedError("M1: Saxton and Rawls 2006")


def total_available_water(constants: SoilWaterConstants, root_depth_m: float) -> float:
    """Compute total available water in the root zone.

    FAO-56 equation 82: ``TAW = 1000 (theta_FC - theta_WP) Zr``.

    Args:
        constants: Field capacity and wilting point for the soil.
        root_depth_m: Effective rooting depth Zr for the current growth stage, m.

    Returns:
        Total available water, mm.
    """
    raise NotImplementedError("M1: FAO-56 equation 82")
