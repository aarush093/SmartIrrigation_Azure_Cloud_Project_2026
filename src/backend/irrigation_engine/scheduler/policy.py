"""The power-window scheduling policy.

Implements plan Section 7 as corrected on 3 September 2026. This is where the
project's novelty lives: the decision is not "does the crop need water" but
"can this pump repay the deficit inside the electricity the feeder will actually
carry, and if not, when must it start repaying it".

    C       = net depth one full window can deliver for this field   (mm)
    D       = current root-zone depletion                            (mm)
    D_next  = projected depletion at the start of W2 with no irrigation in W1
    min_app = minimum worthwhile net application                     (mm)

    if rain_covers(D, horizon = start of W2, confidence = calibrated):
        SKIP, reason RAIN_EXPECTED
    elif D_next > RAW:
        IRRIGATE in W1, reason STRESS_IMMINENT            (mandatory)
    elif D_next > C:
        IRRIGATE in W1, reason CAPACITY_LIMIT
    elif D >= 0.5 * RAW and D >= min_app:
        IRRIGATE in W1, reason OPPORTUNISTIC_TOPUP
    else:
        WAIT, reason NO_NEED

The ``CAPACITY_LIMIT`` branch is the heart of it. Refilling only once the deficit
has outgrown one window is too late; the branch fires while the deficit can still
be repaid in a single window.

**Determinism is a requirement, not a property.** Nothing in this module reads a
clock, generates a random number or touches ambient state. ``today`` and the
window list are arguments. That is what makes the property tests and the
two-season simulation reproducible, and what lets a reviewer replay any decision
the system ever made.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Sequence

from irrigation_engine.params import load_params
from irrigation_engine.pump import minutes_for_discharge
from irrigation_engine.scheduler.models import (
    Decision,
    FieldState,
    PowerWindow,
    ReasonCode,
    Schedule,
)

__all__ = ["RainForecast", "plan_day", "plan_multi_field", "window_capacity_mm"]


class RainForecast:
    """Calibrated answer to "will rain cover this deficit before the next window".

    Deliberately not the raw forecast probability. Plan Section 8: the skip rule
    needs to know how much to trust "80 percent chance of 20 mm", and that trust
    is learned per district and month by Krishna Agrawal's calibration model. This
    class is the interface the scheduler sees; the default implementation is the
    conservative one used until that model validates.
    """

    def __init__(self, expected_mm: float = 0.0, confidence: float = 0.0) -> None:
        """Configure a forecast.

        Args:
            expected_mm: Effective rainfall expected to reach the root zone
                before the next window, mm.
            confidence: Calibrated probability that it does, 0 to 1.
        """
        self.expected_mm = expected_mm
        self.confidence = confidence

    def covers(self, deficit_mm: float, *, min_confidence: float = 0.7) -> bool:
        """Whether rain can be trusted to cover the deficit.

        Both conditions must hold. A high probability of insufficient rain does
        not justify a skip, and a large forecast amount the model does not trust
        does not either. Skipping wrongly costs the farmer a whole irrigation
        interval, because the next window may be days away.

        Args:
            deficit_mm: Depth that must be covered, mm.
            min_confidence: Calibrated probability required to act.

        Returns:
            True only when the deficit is covered at sufficient confidence.
        """
        return self.expected_mm >= deficit_mm and self.confidence >= min_confidence


def window_capacity_mm(state: FieldState, window: PowerWindow) -> float:
    """Net depth one power window can deliver to this field.

    ``C = Q * effective_duration * Ea / area``, converting litres to millimetres
    over the field area. The window's *effective* duration is used, so an
    unreliable feeder is planned against what it is expected to deliver rather
    than what it promises.

    Args:
        state: The field, supplying discharge, efficiency and area.
        window: The window.

    Returns:
        Net depth deliverable in one window, mm.
    """
    litres = state.discharge_l_per_min * window.effective_duration_minutes
    gross_mm = litres / state.area_m2
    return gross_mm * state.irrigation_efficiency


def plan_day(
    state: FieldState,
    *,
    today: dt.date,
    windows: Sequence[PowerWindow],
    forecast_etc_mm: Sequence[float],
    rain: RainForecast | None = None,
    forecaster: str = "kc-et0-fao56",
) -> Schedule:
    """Decide what this field should do today.

    Args:
        state: Current field state. Its depletion already accounts for any
            truncated earlier run, because the balance is stepped with the depth
            delivered; see the note on ``required`` below.
        today: Local calendar date the decision applies to. An argument, never a
            clock read, so the decision is reproducible.
        windows: Upcoming power windows in chronological order. The first is W1,
            the window this decision may schedule into.
        forecast_etc_mm: Projected crop evapotranspiration per day from today
            onward, mm, normally from a
            :class:`~irrigation_engine.forecasting.MoistureForecaster`.
        rain: Calibrated rain forecast over the horizon to W2. Absent means no
            rain is expected, which is the conservative assumption.
        forecaster: Identifier of the model that produced ``forecast_etc_mm``,
            recorded on the schedule for traceability.

    Returns:
        The decision, with the minutes to instruct, the window, the reason code
        and any carry-over.

    Raises:
        ValueError: If ``forecast_etc_mm`` is empty.
    """
    if not forecast_etc_mm:
        msg = "a forecast of at least one day is required to project depletion"
        raise ValueError(msg)

    scheduling = load_params("scheduling")
    min_application_mm = float(load_params("irrigation")["scheduling"]["min_application_mm"])
    low_threshold = float(scheduling["reliability"]["low_threshold"])

    # The deficit to repay is the current depletion, and nothing else.
    #
    # Carry-over is deliberately NOT added. It is what a truncated run failed to
    # deliver, and the water balance is stepped with the depth actually
    # delivered, so the undelivered part is already inside today's depletion.
    # Adding it again asks the pump for it twice, and because the root zone
    # cannot hold the surplus, almost all of the excess drains straight past it.
    # Measured on 5 September 2026: the double count was 1,467 mm of the
    # simulation's water and 1,452 mm of its deep percolation.
    #
    # Carry-over is a thing the CALL SCRIPT says -- "the rest tomorrow" -- not an
    # accounting quantity the balance needs. It is therefore an output on
    # :class:`Schedule` and not an input on :class:`FieldState`.
    required = state.depletion_mm

    def _no_window(reason: ReasonCode) -> Schedule:
        return Schedule(
            field_id=state.field_id,
            date=today,
            decision=Decision.WAIT,
            reason_code=reason,
            required_mm=required,
            forecaster=forecaster,
        )

    if not windows:
        return _no_window(ReasonCode.NO_WINDOW)

    w1 = windows[0]
    capacity = window_capacity_mm(state, w1)

    # Projected depletion at the start of the next window with no irrigation in
    # W1. Days between W1 and W2 decide how much drying happens in between; with
    # no W2 known, the full forecast horizon is used, which is conservative
    # because it assumes the next opportunity is far away.
    if len(windows) > 1:
        days_to_next = max(1, (windows[1].start.date() - w1.start.date()).days)
    else:
        days_to_next = len(forecast_etc_mm)
    drying_mm = sum(forecast_etc_mm[:days_to_next])
    projected = min(required + drying_mm, state.taw_mm)

    rain_forecast = rain or RainForecast()

    if rain_forecast.covers(required):
        return Schedule(
            field_id=state.field_id,
            date=today,
            decision=Decision.SKIP,
            reason_code=ReasonCode.RAIN_EXPECTED,
            required_mm=required,
            forecaster=forecaster,
        )

    if projected > state.raw_mm:
        reason = ReasonCode.STRESS_IMMINENT
    elif projected > capacity:
        reason = ReasonCode.CAPACITY_LIMIT
    elif required >= 0.5 * state.raw_mm and required >= min_application_mm:
        reason = ReasonCode.OPPORTUNISTIC_TOPUP
    else:
        return _no_window(ReasonCode.NO_NEED)

    # An instruction below the minimum worthwhile application is not worth a
    # call, even when a branch above fired. Without this a small pump on a large
    # field is told to run four minutes every night, which trains the farmer to
    # ignore the calls.
    if required < min_application_mm:
        return _no_window(ReasonCode.BELOW_MINIMUM)

    return _build_irrigation(
        state,
        today=today,
        window=w1,
        reason=reason,
        required_mm=required,
        low_threshold=low_threshold,
        forecaster=forecaster,
    )


def _build_irrigation(
    state: FieldState,
    *,
    today: dt.date,
    window: PowerWindow,
    reason: ReasonCode,
    required_mm: float,
    low_threshold: float,
    forecaster: str,
    available_minutes: float | None = None,
) -> Schedule:
    """Turn a decision to irrigate into minutes, truncating to the window."""
    needed_minutes = minutes_for_discharge(
        required_mm,
        state.area_m2,
        state.irrigation_efficiency,
        state.discharge_l_per_min,
    )
    budget = window.duration_minutes if available_minutes is None else available_minutes
    minutes = min(needed_minutes, budget)

    # Depth actually delivered by the truncated run, and what remains owed.
    delivered_mm = required_mm * (minutes / needed_minutes) if needed_minutes > 0 else 0.0
    carry_over_mm = max(0.0, required_mm - delivered_mm)

    # Below the reliability threshold the call cannot promise a clock time; it
    # says "when power comes, run X minutes" instead. Plan Section 7.
    start_time = None if window.is_low_reliability(low_threshold) else window.start

    return Schedule(
        field_id=state.field_id,
        date=today,
        decision=Decision.IRRIGATE,
        reason_code=reason,
        minutes=minutes,
        window=window,
        start_time=start_time,
        delivered_mm=delivered_mm,
        carry_over_mm=carry_over_mm,
        required_mm=required_mm,
        forecaster=forecaster,
    )


def plan_multi_field(
    states: Sequence[FieldState],
    *,
    today: dt.date,
    windows: Sequence[PowerWindow],
    forecast_etc_mm: Sequence[float],
    rain: RainForecast | None = None,
    forecaster: str = "kc-et0-fao56",
) -> list[Schedule]:
    """Allocate one window across several fields sharing a pump.

    Fields are served in descending order of ``(D / RAW) * Ky``: how far into
    stress the field is, weighted by how much yield that crop loses per unit of
    deficit. Ties break on field id so that identical inputs always produce an
    identical order, which the property tests and the simulation depend on.

    The window is a single shared resource: one pump cannot serve two fields at
    once. Minutes are drawn down as they are allocated, and a field that finds
    nothing left carries its whole requirement forward.

    Args:
        states: Fields sharing the pump.
        today: Local calendar date the decision applies to.
        windows: Upcoming power windows, chronologically.
        forecast_etc_mm: Projected ETc per day from today onward, mm.
        rain: Calibrated rain forecast over the horizon.
        forecaster: Identifier of the model that produced the projection.

    Returns:
        One schedule per field, in the order the fields were served.
    """
    ordered = sorted(states, key=lambda s: (-s.priority, s.field_id))

    if not windows:
        return [
            plan_day(
                state,
                today=today,
                windows=[],
                forecast_etc_mm=forecast_etc_mm,
                rain=rain,
                forecaster=forecaster,
            )
            for state in ordered
        ]

    low_threshold = float(load_params("scheduling")["reliability"]["low_threshold"])
    w1 = windows[0]
    remaining_minutes = w1.duration_minutes

    schedules: list[Schedule] = []
    for state in ordered:
        provisional = plan_day(
            state,
            today=today,
            windows=windows,
            forecast_etc_mm=forecast_etc_mm,
            rain=rain,
            forecaster=forecaster,
        )
        if provisional.decision is not Decision.IRRIGATE:
            schedules.append(provisional)
            continue

        allocated = _build_irrigation(
            state,
            today=today,
            window=w1,
            reason=provisional.reason_code,
            required_mm=provisional.required_mm,
            low_threshold=low_threshold,
            forecaster=forecaster,
            available_minutes=remaining_minutes,
        )
        remaining_minutes = max(0.0, remaining_minutes - allocated.minutes)
        schedules.append(allocated)

    return schedules
