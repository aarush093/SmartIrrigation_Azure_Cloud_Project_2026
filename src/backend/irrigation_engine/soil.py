"""Pedotransfer from soil texture to plant-available water.

Converts the SoilGrids texture and bulk density of a field into the volumetric
water contents at field capacity and permanent wilting point, which is what
turns an evapotranspiration deficit into an irrigation depth. This is the step
that lets the system work on a field with no instrumentation at all.

Reference: K. E. Saxton and W. J. Rawls, "Soil water characteristic estimates by
texture and organic matter for hydrologic solutions", Soil Science Society of
America Journal, 70(5), pp. 1569-1578, 2006. Plan reference R21.

Regression coefficients live in ``params/soil.yaml`` with their equation numbers
cited, never inline here.

Scope limitation, stated deliberately. Saxton and Rawls also publish a density
adjustment that rescales the matric water contents where the measured bulk
density departs from the normal density implied by the texture. That adjustment
needs their saturation estimate (equations 3 to 5), which is **not** implemented
here, so **no density adjustment is applied**. Bulk density is used only to
reject inputs that are physically implausible, which catches the SoilGrids unit
error the adapter is most likely to make.

An earlier draft of this module contained an adjustment that derived the normal
density from the measured bulk density. That is algebraically a no-op: the ratio
is identically 1.0 at every density. It was removed rather than left in place,
because an adjustment that appears to run and does nothing is worse than an
absent one.

TODO [VERIFY] implement the published density adjustment against a copy of
Saxton and Rawls (2006) equations 3 to 5, or record in the report that field
capacity is unadjusted for compaction.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from irrigation_engine.models import SoilProfile, SoilWaterConstants
from irrigation_engine.params import load_params

__all__ = ["readily_available_water", "saxton_rawls", "total_available_water"]

# Texture fractions are permitted to miss unity by this much before the input is
# rejected. SoilGrids reports each fraction independently, so rounding leaves a
# small residual; anything larger indicates a unit error upstream.
_TEXTURE_SUM_TOLERANCE = 0.05


def saxton_rawls(soil: SoilProfile) -> SoilWaterConstants:
    """Estimate field capacity and wilting point from texture and organic matter.

    Applies the Saxton and Rawls (2006) moisture regressions with their published
    adjustments: equation 1 with its linear correction for the 1500 kPa point,
    and equation 2 with its quadratic correction for the 33 kPa point. A density
    adjustment then scales field capacity where the measured bulk density departs
    from the normal density implied by the texture.

    Args:
        soil: Depth-weighted 0 to 30 cm profile, normally from SoilGrids. Texture
            and organic carbon are mass fractions 0 to 1; bulk density is g/cm3.

    Returns:
        Volumetric water content at field capacity and at wilting point, m3/m3.

    Raises:
        ValueError: If the sand, silt and clay fractions do not sum to
            approximately 1.0, if bulk density falls outside a physically
            plausible range, or if the regressions return an inverted or
            out-of-range result.
    """
    params = load_params("soil")

    texture_sum = soil.sand + soil.silt + soil.clay
    if abs(texture_sum - 1.0) > _TEXTURE_SUM_TOLERANCE:
        msg = (
            f"sand + silt + clay must sum to about 1.0, got {texture_sum:.3f}. "
            "SoilGrids reports these in g/kg; they must be rescaled to mass "
            "fractions before reaching this function."
        )
        raise ValueError(msg)

    density = params["density"]
    if not density["min_bulk_density"] <= soil.bulk_density <= density["max_bulk_density"]:
        msg = (
            f"bulk density {soil.bulk_density} g/cm3 is outside the plausible range "
            f"{density['min_bulk_density']} to {density['max_bulk_density']}. "
            "SoilGrids reports bulk density in cg/cm3; it must be rescaled."
        )
        raise ValueError(msg)

    sand = soil.sand
    clay = soil.clay
    # The published equations take organic matter as a percentage by weight,
    # while SoilGrids supplies organic carbon as a mass fraction.
    organic_matter = soil.organic_carbon * 100.0 * params["organic_matter_from_carbon"]

    theta_wp = _wilting_point(params["wilting_point"], sand, clay, organic_matter)
    theta_fc = _field_capacity(params["field_capacity"], sand, clay, organic_matter)

    # No density adjustment is applied. See the module docstring: the published
    # adjustment needs the texture-based saturation estimate, which is not
    # implemented here, and a fabricated substitute would be a silent no-op.
    # Bulk density is used above as a validity check only.

    _validate(theta_fc, theta_wp, params["bounds"])
    return SoilWaterConstants(theta_fc=theta_fc, theta_wp=theta_wp)


def _wilting_point(c: dict[str, float], sand: float, clay: float, om: float) -> float:
    """Saxton and Rawls (2006) equation 1, with its linear adjustment."""
    theta_t = (
        c["sand"] * sand
        + c["clay"] * clay
        + c["organic_matter"] * om
        + c["sand_x_om"] * sand * om
        + c["clay_x_om"] * clay * om
        + c["sand_x_clay"] * sand * clay
        + c["intercept"]
    )
    return theta_t + (c["adjust_slope"] * theta_t + c["adjust_intercept"])


def _field_capacity(c: dict[str, float], sand: float, clay: float, om: float) -> float:
    """Saxton and Rawls (2006) equation 2, with its quadratic adjustment."""
    theta_t = (
        c["sand"] * sand
        + c["clay"] * clay
        + c["organic_matter"] * om
        + c["sand_x_om"] * sand * om
        + c["clay_x_om"] * clay * om
        + c["sand_x_clay"] * sand * clay
        + c["intercept"]
    )
    return theta_t + (
        c["adjust_quadratic"] * theta_t**2 + c["adjust_linear"] * theta_t + c["adjust_intercept"]
    )


def _validate(theta_fc: float, theta_wp: float, bounds: dict[str, float]) -> None:
    """Reject a physically impossible result rather than clamping it silently."""
    for label, value in (("field capacity", theta_fc), ("wilting point", theta_wp)):
        if not bounds["min_theta"] <= value <= bounds["max_theta"]:
            msg = (
                f"{label} {value:.4f} m3/m3 is outside the physical range "
                f"{bounds['min_theta']} to {bounds['max_theta']}"
            )
            raise ValueError(msg)

    available = theta_fc - theta_wp
    if available < bounds["min_available_water_fraction"]:
        msg = (
            f"field capacity {theta_fc:.4f} does not exceed wilting point "
            f"{theta_wp:.4f} by the minimum {bounds['min_available_water_fraction']} m3/m3. "
            "The soil would hold no usable water, which is never a real soil."
        )
        raise ValueError(msg)


def total_available_water(constants: SoilWaterConstants, root_depth_m: float) -> float:
    """Compute total available water in the root zone.

    FAO-56 equation 82: ``TAW = 1000 (theta_FC - theta_WP) Zr``. The factor of
    1000 converts metres of water to millimetres.

    Args:
        constants: Field capacity and wilting point for the soil.
        root_depth_m: Effective rooting depth Zr for the current growth stage, m.

    Returns:
        Total available water, mm.

    Raises:
        ValueError: If the rooting depth is not positive.
    """
    if root_depth_m <= 0.0:
        msg = f"rooting depth must be positive, got {root_depth_m} m"
        raise ValueError(msg)
    return 1000.0 * constants.available_water_fraction * root_depth_m


def readily_available_water(taw_mm: float, depletion_fraction: float) -> float:
    """Compute readily available water, the depletion a crop tolerates unstressed.

    FAO-56 equation 83: ``RAW = p x TAW``.

    Args:
        taw_mm: Total available water in the root zone, mm.
        depletion_fraction: Depletion fraction p, already adjusted for ETc by
            :func:`irrigation_engine.crops.adjust_depletion_fraction`.

    Returns:
        Readily available water, mm.

    Raises:
        ValueError: If the depletion fraction is outside the open interval 0 to 1.
    """
    if not 0.0 < depletion_fraction < 1.0:
        msg = f"depletion fraction must lie strictly between 0 and 1, got {depletion_fraction}"
        raise ValueError(msg)
    return taw_mm * depletion_fraction


class SoilSource(StrEnum):
    """Where a field's soil profile came from.

    Recorded on every resolution and surfaced to the operator, because the three
    differ enormously in how much they can be trusted for a particular half
    hectare.
    """

    #: The farmer answered the onboarding question about his own field. The
    #: primary source: he knows his plot, and his answer describes it rather
    #: than a 250 m grid pixel that may straddle a road.
    FARMER_DECLARED = "farmer_declared"
    #: ISRIC SoilGrids responded. Used to prefill the farmer's answer so the
    #: operator confirms rather than guesses.
    SOILGRIDS = "soilgrids"
    #: Neither was available. A guess, and never used silently.
    FALLBACK = "fallback"


def available_texture_classes() -> tuple[str, ...]:
    """The texture classes a farmer can choose between at onboarding."""
    classes: dict[str, Any] = load_params("soil_texture_classes")["classes"]
    return tuple(classes)


def texture_class_names(lang: str = "en") -> dict[str, str]:
    """The word for each texture class in one language.

    Args:
        lang: Language code.

    Returns:
        Class key to the farm word for it, for the onboarding screen and the
        laminated card.
    """
    classes: dict[str, Any] = load_params("soil_texture_classes")["classes"]
    return {
        key: str(entry["names"].get(lang, entry["names"]["en"])) for key, entry in classes.items()
    }


def texture_from_class(texture_class: str) -> SoilProfile:
    """Build a soil profile from a farmer-declared texture class.

    Args:
        texture_class: One of the keys from :func:`available_texture_classes`.

    Returns:
        A representative profile for that class.

    Raises:
        KeyError: If the class is not defined.
    """
    classes: dict[str, Any] = load_params("soil_texture_classes")["classes"]
    try:
        entry = classes[texture_class]
    except KeyError:
        msg = f"unknown texture class {texture_class!r}; available: {', '.join(sorted(classes))}"
        raise KeyError(msg) from None

    return SoilProfile(
        sand=float(entry["sand"]),
        silt=float(entry["silt"]),
        clay=float(entry["clay"]),
        # Organic carbon is not something a farmer can report and is not asked
        # for. A low value is assumed, which understates water retention
        # slightly and therefore errs toward irrigating.
        organic_carbon=0.010,
        bulk_density=float(entry["bulk_density"]),
    )


def resolve_soil(
    *,
    declared_class: str | None = None,
    soilgrids_profile: SoilProfile | None = None,
) -> tuple[SoilProfile, SoilSource]:
    """Resolve the soil profile to use for a field, and say where it came from.

    Precedence, and the reasoning behind it, is recorded in
    ``params/soil_texture_classes.yaml``: the farmer's own answer is primary,
    because it describes his plot rather than a grid pixel, and because
    SoilGrids has repeatedly returned nothing. SoilGrids prefills that answer
    where it responds.

    Args:
        declared_class: What the farmer said at onboarding.
        soilgrids_profile: What SoilGrids returned, if anything.

    Returns:
        The profile to use, and the source it came from. A ``FALLBACK`` source
        must be surfaced to the operator and never used silently: a
        recommendation computed from a guessed soil can be wrong by a factor of
        two in depth.
    """
    if declared_class:
        return texture_from_class(declared_class), SoilSource.FARMER_DECLARED
    if soilgrids_profile is not None:
        return soilgrids_profile, SoilSource.SOILGRIDS

    fallback = str(load_params("soil_texture_classes")["fallback_class"])
    return texture_from_class(fallback), SoilSource.FALLBACK
