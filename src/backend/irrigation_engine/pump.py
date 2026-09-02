"""Convert an irrigation depth into pump running minutes.

This is the translation the project exists to perform. A depth in millimetres is
not actionable by a farmer with a pump and a rationed power supply; a number of
minutes is. Expressing the recommendation in minutes for a specific pump also
removes the largest practical error source, which is the farmer's own estimate of
how long to run it (plan Section 4).

    gross depth = net depth / Ea
    volume (L)  = gross depth (mm) x area (m2)
    minutes     = volume / Q

Application efficiency Ea defaults are FAO Training Manual 4 midpoints and live
in ``params/irrigation.yaml``.

Implemented in M1.
"""

from __future__ import annotations

from irrigation_engine.models import IrrigationMethod, PumpCharacterisation

__all__ = ["gross_depth_mm", "pump_discharge_lpm", "pump_minutes"]


def pump_discharge_lpm(pump: PumpCharacterisation) -> float:
    """Establish pump discharge in litres per minute.

    For a :class:`~irrigation_engine.models.BucketTest` this is a direct
    measurement, ``litres / seconds * 60``. For a
    :class:`~irrigation_engine.models.PumpSpec` it is estimated hydraulically as
    ``Q = HP x 746 x eta / (9.81 x H)`` litres per second, converted to litres
    per minute; see plan Section 6.

    The bucket test is preferred wherever it exists. The specification route
    depends on a declared head and an assumed combined efficiency, and its error
    propagates directly into the running time the farmer is told.

    Args:
        pump: Either a measured bucket test or a nameplate specification.

    Returns:
        Discharge, litres per minute.

    Raises:
        ValueError: If the resulting discharge is not positive, which indicates
            an implausible head or efficiency.
    """
    raise NotImplementedError("M1")


def gross_depth_mm(net_depth_mm: float, efficiency: float) -> float:
    """Inflate a net depth to the gross depth that must leave the pump.

    Args:
        net_depth_mm: Depth that must reach the root zone, mm.
        efficiency: Application efficiency Ea, 0 to 1.

    Returns:
        Gross depth to apply, mm.

    Raises:
        ValueError: If efficiency is outside the open interval 0 to 1.
    """
    raise NotImplementedError("M1")


def pump_minutes(
    net_depth_mm: float,
    area_m2: float,
    efficiency: float | IrrigationMethod,
    pump: PumpCharacterisation,
) -> float:
    """Compute how many minutes the pump must run to apply a net depth.

    Worked example from plan Section 6, which is the M1 acceptance test: wheat at
    mid-season on one acre (4,047 m2) with a depletion of 25 mm, furrow
    irrigation (Ea 0.65), and a 5 HP pump against 30 m of head (Q approximately
    380 L/min) gives a gross depth of 38.5 mm, a volume of about 155,800 L and a
    running time of roughly 410 minutes, which fits inside an 8-hour window.

    Args:
        net_depth_mm: Depth that must reach the root zone, mm. Normally the
            root-zone depletion, or the window capacity where the depletion
            exceeds what one window can deliver.
        area_m2: Field area, m2.
        efficiency: Application efficiency as a fraction, or an
            :class:`~irrigation_engine.models.IrrigationMethod` whose default
            efficiency is read from ``params/irrigation.yaml``.
        pump: Pump characterisation.

    Returns:
        Required running time, minutes.

    Raises:
        ValueError: If the area or the net depth is negative.
    """
    raise NotImplementedError("M1")
