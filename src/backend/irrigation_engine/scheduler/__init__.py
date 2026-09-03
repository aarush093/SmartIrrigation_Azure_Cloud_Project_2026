"""Power-window scheduler.

The project's novelty: irrigation timed to the electricity the feeder actually
carries, not to the crop's demand alone. Policy in
``docs/PHASE2_NOVELTY_AND_PLAN.md`` Section 7.
"""

from irrigation_engine.scheduler.models import (
    IST,
    Decision,
    Event,
    EventKind,
    Farmer,
    FieldState,
    IrrigatedField,
    PowerWindow,
    Pump,
    ReasonCode,
    Schedule,
    WindowSource,
)
from irrigation_engine.scheduler.policy import (
    RainForecast,
    plan_day,
    plan_multi_field,
    window_capacity_mm,
)
from irrigation_engine.scheduler.sources import (
    DeclaredRotation,
    DiscomSchedule,
    ScheduleSource,
    apply_precedence,
    update_reliability,
)

__all__ = [
    "IST",
    "Decision",
    "DeclaredRotation",
    "DiscomSchedule",
    "Event",
    "EventKind",
    "Farmer",
    "FieldState",
    "IrrigatedField",
    "PowerWindow",
    "Pump",
    "RainForecast",
    "ReasonCode",
    "Schedule",
    "ScheduleSource",
    "WindowSource",
    "apply_precedence",
    "plan_day",
    "plan_multi_field",
    "update_reliability",
    "window_capacity_mm",
]
