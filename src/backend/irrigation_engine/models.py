"""Core data model for the irrigation engine.

Every type here is a pydantic model so that it serialises to JSON for Cosmos DB
without a separate mapping layer. Units are stated in each field description and
are never left implicit: the single largest source of error in an irrigation
calculation is a millimetre that was actually a metre.

Scope note. The models needed by the M2 scheduler (``Farmer``, ``Field``,
``Pump``, ``PowerWindow``, ``Schedule``, ``Event``) are defined in
:mod:`irrigation_engine.scheduler.models`. This module holds the physical
quantities the FAO-56 engine works in.
"""

from __future__ import annotations

import datetime as dt
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class IrrigationMethod(StrEnum):
    """Field application method, which fixes the default application efficiency.

    Efficiency values live in ``params/irrigation.yaml``, not here.
    """

    FLOOD = "flood"
    FURROW = "furrow"
    SPRINKLER = "sprinkler"
    DRIP = "drip"


class GrowthStage(StrEnum):
    """FAO-56 crop growth stage.

    Stage boundaries come from the crop calendar in ``params/crops.yaml``.
    """

    INITIAL = "initial"
    DEVELOPMENT = "development"
    MID = "mid"
    LATE = "late"


class _Frozen(BaseModel):
    """Base for value objects: immutable, and no unexpected fields accepted."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class DailyWeather(_Frozen):
    """One day of forecast or archive weather for a single field.

    ``et0`` is taken from the provider's own FAO-56 calculation where available
    (Open-Meteo publishes ``et0_fao_evapotranspiration``) rather than being
    re-derived, and is cross-checked against
    :func:`irrigation_engine.et0.penman_monteith`. See plan Section 6.
    """

    date: dt.date = Field(description="Local calendar date of the field, IST.")
    et0_mm: float = Field(ge=0.0, description="Reference evapotranspiration, mm/day.")
    precipitation_mm: float = Field(ge=0.0, description="Total precipitation, mm/day.")
    precipitation_probability: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Maximum forecast precipitation probability for the day, 0 to 1. "
        "None for archive data, where the rainfall is observed rather than forecast.",
    )
    temp_max_c: float | None = Field(
        default=None, description="Daily maximum air temperature, degC."
    )
    temp_min_c: float | None = Field(
        default=None, description="Daily minimum air temperature, degC."
    )

    @property
    def is_forecast(self) -> bool:
        """True when this day carries a forecast probability rather than an observation."""
        return self.precipitation_probability is not None


class SoilProfile(_Frozen):
    """Depth-weighted soil properties for the 0 to 30 cm root zone.

    Sourced from ISRIC SoilGrids (dataset D4). Fractions are mass fractions of
    the fine earth and must sum to approximately 1.0; the provider is responsible
    for the depth weighting across the 0-5, 5-15 and 15-30 cm intervals.
    """

    sand: float = Field(ge=0.0, le=1.0, description="Sand mass fraction, 0 to 1.")
    clay: float = Field(ge=0.0, le=1.0, description="Clay mass fraction, 0 to 1.")
    silt: float = Field(ge=0.0, le=1.0, description="Silt mass fraction, 0 to 1.")
    organic_carbon: float = Field(
        ge=0.0, description="Soil organic carbon, mass fraction 0 to 1 (not g/kg)."
    )
    bulk_density: float = Field(gt=0.0, description="Dry bulk density of the fine earth, g/cm3.")
    latitude: float | None = Field(default=None, ge=-90.0, le=90.0)
    longitude: float | None = Field(default=None, ge=-180.0, le=180.0)


class SoilWaterConstants(_Frozen):
    """Volumetric water contents derived from texture by pedotransfer function.

    Produced by :func:`irrigation_engine.soil.saxton_rawls`.
    """

    theta_fc: float = Field(
        gt=0.0, lt=1.0, description="Volumetric water content at field capacity, m3/m3."
    )
    theta_wp: float = Field(
        gt=0.0, lt=1.0, description="Volumetric water content at permanent wilting point, m3/m3."
    )

    @property
    def available_water_fraction(self) -> float:
        """Plant-available water per unit depth, m3/m3."""
        return self.theta_fc - self.theta_wp


class CropStage(_Frozen):
    """The crop's FAO-56 parameters on a specific day.

    Returned by :func:`irrigation_engine.crops.crop_calendar`. Every value here
    originates in ``params/crops.yaml`` with its FAO-56 table cited.
    """

    crop: str = Field(description="Crop key as used in params/crops.yaml.")
    stage: GrowthStage
    days_after_sowing: int = Field(ge=0)
    kc: float = Field(
        gt=0.0, description="Crop coefficient for the day, dimensionless. FAO-56 Table 12."
    )
    root_depth_m: float = Field(
        gt=0.0, description="Effective rooting depth Zr for the day, m. FAO-56 Table 22."
    )
    depletion_fraction: float = Field(
        gt=0.0,
        lt=1.0,
        description="Allowable depletion fraction p, before adjustment for ETc. FAO-56 Table 22.",
    )
    yield_response_factor: float = Field(
        gt=0.0, description="Yield response factor Ky for the stage. FAO-33 / FAO-56 Table 24."
    )


class WaterBalanceState(_Frozen):
    """Root-zone water balance on one day, in millimetres of depth.

    ``depletion_mm`` is FAO-56 ``Dr``: zero at field capacity, rising as the root
    zone dries, bounded above by ``taw_mm``.
    """

    date: dt.date
    depletion_mm: float = Field(ge=0.0, description="Root-zone depletion Dr, mm.")
    taw_mm: float = Field(gt=0.0, description="Total available water in the root zone, mm.")
    raw_mm: float = Field(gt=0.0, description="Readily available water, p adjusted x TAW, mm.")
    etc_mm: float = Field(ge=0.0, description="Crop evapotranspiration for the day, mm.")
    effective_rain_mm: float = Field(ge=0.0, description="Rainfall credited to the root zone, mm.")
    irrigation_mm: float = Field(ge=0.0, description="Net irrigation applied on the day, mm.")
    deep_percolation_mm: float = Field(ge=0.0, description="Water lost below the root zone, mm.")
    runoff_mm: float = Field(ge=0.0, description="Surface runoff, mm.")

    @property
    def is_stressed(self) -> bool:
        """True when depletion has passed readily available water, so the crop is under stress."""
        return self.depletion_mm > self.raw_mm


class BucketTest(_Frozen):
    """Pump discharge measured directly, by timing the filling of a known volume.

    This is the preferred characterisation because it needs no assumption about
    pump efficiency or total head. Measured at onboarding. See plan Section 6.
    """

    litres: float = Field(gt=0.0, description="Volume of the container, litres.")
    seconds: float = Field(gt=0.0, description="Time taken to fill it, seconds.")


class PumpSpec(_Frozen):
    """Pump discharge estimated from the nameplate rating and the head.

    The fallback when no bucket test was performed. Materially less accurate
    than :class:`BucketTest`, because both the combined efficiency and the total
    head are declared rather than measured.
    """

    hp: float = Field(gt=0.0, description="Nameplate rating, horsepower.")
    head_m: float = Field(gt=0.0, description="Total head, m.")
    eta: float = Field(
        default=0.5,
        gt=0.0,
        le=1.0,
        description="Combined pump and motor efficiency, dimensionless. "
        "Default 0.5. TODO [VERIFY] with a local pump dealer or KVK; see plan Section 6.",
    )


PumpCharacterisation = BucketTest | PumpSpec
"""Either way of establishing pump discharge. The scheduler needs only litres per minute."""
