"""Convert an irrigation depth into pump running minutes.

This is the translation the project exists to perform. A depth in millimetres is
not actionable by a farmer with a pump and a rationed power supply; a number of
minutes is. Expressing the recommendation in minutes for a specific pump also
removes the largest practical error source, which is the farmer's own estimate of
how long to run it (plan Section 4).

    gross depth (mm) = net depth (mm) / Ea
    volume (L)       = gross depth (mm) x area (m2)
    minutes          = volume (L) / Q (L/min)

The volume identity holds because one millimetre of depth over one square metre
is exactly one litre.

Application efficiency Ea defaults are from the FAO Irrigation and Drainage
Training Manual 4 (Brouwer, Prins and Heibloem, 1989) and live in
``params/irrigation.yaml``.
"""

from __future__ import annotations

from irrigation_engine.models import BucketTest, IrrigationMethod, PumpCharacterisation
from irrigation_engine.params import load_params

__all__ = [
    "PumpRunTooLongError",
    "gross_depth_mm",
    "pump_discharge_l_per_min",
    "pump_minutes",
    "resolve_efficiency",
]


class PumpRunTooLongError(ValueError):
    """A single continuous run exceeds the configured ceiling.

    Raised rather than returned, because a run longer than any published DISCOM
    agricultural window is not a usable instruction: it means the area, the depth
    or the discharge is wrong, and telling a farmer to run his pump for nineteen
    hours would be worse than telling him nothing.
    """


def resolve_efficiency(efficiency: float | IrrigationMethod) -> float:
    """Resolve an application efficiency from a method or a literal fraction.

    Args:
        efficiency: Either a fraction between 0 and 1, or an
            :class:`~irrigation_engine.models.IrrigationMethod` whose default is
            read from ``params/irrigation.yaml``.

    Returns:
        Application efficiency Ea as a fraction.

    Raises:
        ValueError: If a literal efficiency falls outside the permitted bounds.
    """
    params = load_params("irrigation")
    if isinstance(efficiency, IrrigationMethod):
        return float(params["application_efficiency"][efficiency.value])

    bounds = params["efficiency_bounds"]
    if not bounds["min"] <= efficiency <= bounds["max"]:
        msg = (
            f"application efficiency {efficiency} is outside the plausible range "
            f"{bounds['min']} to {bounds['max']}"
        )
        raise ValueError(msg)
    return float(efficiency)


def pump_discharge_l_per_min(pump: PumpCharacterisation) -> float:
    """Establish pump discharge in litres per minute.

    For a :class:`~irrigation_engine.models.BucketTest` this is a direct
    measurement, ``litres / seconds x 60``. For a
    :class:`~irrigation_engine.models.PumpSpec` it is estimated hydraulically:
    hydraulic power ``P = rho g Q H`` rearranged to
    ``Q = HP x 746 x eta / (9.81 x H)`` litres per second, then converted to
    litres per minute (plan Section 6).

    The bucket test is preferred wherever it exists. The specification route
    depends on a declared head and an assumed combined efficiency, and its error
    propagates directly into the running time the farmer is told.

    Args:
        pump: Either a measured bucket test or a nameplate specification.

    Returns:
        Discharge, litres per minute.

    Raises:
        ValueError: If the resulting discharge is outside plausible bounds,
            which indicates an implausible head or efficiency.
    """
    if isinstance(pump, BucketTest):
        discharge = pump.litres / pump.seconds * 60.0
    else:
        constants = load_params("irrigation")["pump"]
        watts = pump.hp * float(constants["watts_per_hp"]) * pump.eta
        litres_per_second = watts / (
            float(constants["gravity"]) * pump.head_m * float(constants["water_density_kg_per_l"])
        )
        discharge = litres_per_second * 60.0

    bounds = load_params("irrigation")["pump"]["discharge_bounds_l_per_min"]
    if not bounds["min"] <= discharge <= bounds["max"]:
        msg = (
            f"computed discharge {discharge:.1f} L/min is outside the plausible range "
            f"{bounds['min']} to {bounds['max']} L/min; check the head and efficiency"
        )
        raise ValueError(msg)
    return discharge


def gross_depth_mm(net_depth_mm: float, efficiency: float) -> float:
    """Inflate a net depth to the gross depth that must leave the pump.

    Args:
        net_depth_mm: Depth that must reach the root zone, mm.
        efficiency: Application efficiency Ea, 0 to 1.

    Returns:
        Gross depth to apply, mm.

    Raises:
        ValueError: If the net depth is negative, or efficiency is outside the
            open interval 0 to 1.
    """
    if net_depth_mm < 0.0:
        msg = f"net depth cannot be negative, got {net_depth_mm} mm"
        raise ValueError(msg)
    if not 0.0 < efficiency <= 1.0:
        msg = f"application efficiency must lie in (0, 1], got {efficiency}"
        raise ValueError(msg)
    return net_depth_mm / efficiency


def required_pump_minutes(
    net_depth_mm: float,
    area_m2: float,
    efficiency: float | IrrigationMethod,
    pump: PumpCharacterisation,
) -> float:
    """Compute the running time a net depth requires, with no ceiling applied.

    The pure arithmetic, separated from the safety check in :func:`pump_minutes`.
    The scheduler needs this: when a deficit exceeds what one power window can
    deliver, it must still know the full requirement in order to fill the window,
    truncate, and carry the remainder forward. Refusing to compute the number
    would make that impossible.

    Use :func:`pump_minutes` for anything that becomes an instruction to a
    farmer; use this only where the caller will itself bound the result.

    Args:
        net_depth_mm: Depth that must reach the root zone, mm.
        area_m2: Field area, m2.
        efficiency: Application efficiency as a fraction, or an
            :class:`~irrigation_engine.models.IrrigationMethod`.
        pump: Pump characterisation.

    Returns:
        Required running time, minutes, however long.

    Raises:
        ValueError: If the area is not positive or the net depth is negative.
    """
    if area_m2 <= 0.0:
        msg = f"field area must be positive, got {area_m2} m2"
        raise ValueError(msg)

    ea = resolve_efficiency(efficiency)
    gross_mm = gross_depth_mm(net_depth_mm, ea)

    # One millimetre over one square metre is exactly one litre.
    volume_l = gross_mm * area_m2
    return volume_l / pump_discharge_l_per_min(pump)


def pump_minutes(
    net_depth_mm: float,
    area_m2: float,
    efficiency: float | IrrigationMethod,
    pump: PumpCharacterisation,
    *,
    max_minutes: float | None = None,
) -> float:
    """Compute how many minutes the pump must run to apply a net depth.

    Worked example from plan Section 6, which is the M1 acceptance test: wheat at
    mid-season on one acre (4,047 m2) with a depletion of 25 mm, furrow
    irrigation (Ea 0.65), and a 5 HP pump against 30 m of head gives a gross
    depth of about 38.5 mm, a volume of about 155,700 L, a discharge of about
    380 L/min and a running time of about 409 minutes, which fits inside an
    8-hour window with margin.

    Args:
        net_depth_mm: Depth that must reach the root zone, mm. Normally the
            root-zone depletion, or the window capacity where the depletion
            exceeds what one window can deliver.
        area_m2: Field area, m2.
        efficiency: Application efficiency as a fraction, or an
            :class:`~irrigation_engine.models.IrrigationMethod`.
        pump: Pump characterisation.
        max_minutes: Ceiling on a single continuous run. Defaults to the value
            in ``params/irrigation.yaml``, currently 720 minutes.

    Returns:
        Required running time, minutes.

    Raises:
        ValueError: If the area or the net depth is negative.
        PumpRunTooLongError: If the run exceeds the ceiling.
    """
    minutes = required_pump_minutes(net_depth_mm, area_m2, efficiency, pump)

    ceiling = (
        float(load_params("irrigation")["pump"]["max_single_run_minutes"])
        if max_minutes is None
        else max_minutes
    )
    if minutes > ceiling:
        msg = (
            f"required run of {minutes:.0f} minutes exceeds the single-run ceiling of "
            f"{ceiling:.0f} minutes. No published agricultural feeder window is that "
            f"long, so the depth, area or discharge is wrong, or the deficit must be "
            f"split across windows by the scheduler."
        )
        raise PumpRunTooLongError(msg)
    return minutes
