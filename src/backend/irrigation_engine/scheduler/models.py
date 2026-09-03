"""Data model for the power-window scheduler.

Pydantic throughout, so every record serialises to JSON for Cosmos DB without a
separate mapping layer.

**Windows are datetimes, never clock times.** A Maharashtra night feeder running
22:00 to 06:00 crosses midnight, and modelling it as a pair of times-of-day is
the classic source of a silent off-by-one-day error: the duration comes out
negative, or sixteen hours instead of eight, and the farmer is told to run his
pump through a window that has already closed. Both ends carry a date and an
IST offset, and the model refuses a window whose end does not follow its start.
"""

from __future__ import annotations

import datetime as dt
import zoneinfo
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

__all__ = [
    "IST",
    "Decision",
    "Event",
    "EventKind",
    "Farmer",
    "FieldState",
    "IrrigatedField",
    "PowerWindow",
    "Pump",
    "ReasonCode",
    "Schedule",
    "WindowSource",
]

IST = zoneinfo.ZoneInfo("Asia/Kolkata")


class WindowSource(StrEnum):
    """Where a power window came from.

    The order here is the precedence order used when sources disagree, most
    trusted first: what the farmer reported today beats a published schedule,
    which beats a declared rotation. Plan Section 7.
    """

    FARMER_REPORT = "farmer_report"
    DISCOM_SCHEDULE = "discom_schedule"
    DECLARED_ROTATION = "declared_rotation"


class Decision(StrEnum):
    """What the scheduler decided to do today."""

    IRRIGATE = "irrigate"
    SKIP = "skip"
    WAIT = "wait"


class ReasonCode(StrEnum):
    """Why the scheduler decided it.

    An enumeration rather than free text, so the call script maps
    deterministically from decision to spoken words and the simulation study can
    count decisions by reason. Plan Section 7.
    """

    RAIN_EXPECTED = "rain_expected"
    STRESS_IMMINENT = "stress_imminent"
    CAPACITY_LIMIT = "capacity_limit"
    OPPORTUNISTIC_TOPUP = "opportunistic_topup"
    NO_NEED = "no_need"
    NO_WINDOW = "no_window"
    BELOW_MINIMUM = "below_minimum"


class EventKind(StrEnum):
    """A thing the farmer told us, or a thing we asked and he answered.

    These are the only state inputs after onboarding. There is no sensor: the
    missed call is the measurement. Plan Section 9.
    """

    WATER_GIVEN = "water_given"
    POWER_FAILED = "power_failed"
    REPEAT_REQUEST = "repeat_request"
    KEYPRESS_YES = "keypress_yes"
    KEYPRESS_NO = "keypress_no"


class _Model(BaseModel):
    """Base: reject unexpected fields rather than silently ignoring them."""

    model_config = ConfigDict(extra="forbid")


class PowerWindow(_Model):
    """One period during which the feeder is expected to carry power.

    Both ends are timezone-aware datetimes. See the module docstring for why a
    pair of clock times would be wrong.
    """

    start: dt.datetime = Field(description="Window opens, timezone-aware, normally IST.")
    end: dt.datetime = Field(description="Window closes, timezone-aware, normally IST.")
    source: WindowSource
    reliability: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Probability this window actually carries power, learned from "
        "POWER_FAILED missed calls.",
    )
    feeder_id: str | None = Field(default=None, description="Substation or feeder identifier.")

    @field_validator("start", "end")
    @classmethod
    def _must_be_aware(cls, value: dt.datetime) -> dt.datetime:
        """Reject a naive datetime, which carries no timezone and cannot be ordered."""
        if value.tzinfo is None:
            msg = (
                "power window bounds must be timezone-aware; a naive datetime "
                "silently assumes the server's timezone, which is not the field's"
            )
            raise ValueError(msg)
        return value

    @model_validator(mode="after")
    def _end_must_follow_start(self) -> PowerWindow:
        """A window must have positive duration.

        This is the check that catches a midnight-crossing window built from two
        clock times: 22:00 to 06:00 on the same date has a negative duration.
        """
        if self.end <= self.start:
            msg = (
                f"window end {self.end.isoformat()} does not follow start "
                f"{self.start.isoformat()}. A window crossing midnight must carry "
                f"the next day's date on its end, not the same day's."
            )
            raise ValueError(msg)
        return self

    @property
    def duration_minutes(self) -> float:
        """Length of the window, minutes. Always positive."""
        return (self.end - self.start).total_seconds() / 60.0

    @property
    def effective_duration_minutes(self) -> float:
        """Window length scaled by feeder reliability, minutes.

        An unreliable feeder cannot be planned against at its nominal length, so
        capacity is computed on the expected duration rather than the promised
        one. Plan Section 7.
        """
        return self.duration_minutes * self.reliability

    @property
    def crosses_midnight(self) -> bool:
        """Whether the window spans a date boundary in its own timezone."""
        return self.start.date() != self.end.date()

    def is_low_reliability(self, threshold: float) -> bool:
        """Whether the call should say "when power comes" instead of a clock time."""
        return self.reliability < threshold


class Pump(_Model):
    """The farmer's pump, as characterised at onboarding."""

    pump_id: str
    discharge_l_per_min: float = Field(gt=0.0, description="Measured or estimated discharge.")
    measured_by_bucket_test: bool = Field(
        default=False,
        description="True where discharge came from a bucket test rather than a "
        "nameplate estimate. A bucket test needs no efficiency assumption and is "
        "materially more accurate.",
    )


class Farmer(_Model):
    """A registered farmer. Identity is the phone number, verified by the missed call itself."""

    farmer_id: str
    phone: str = Field(description="E.164 format, the identity and the delivery address.")
    language: str = Field(
        default="hi", description="Script master to render, for example hi, en, ta."
    )
    name: str | None = None
    village: str | None = None
    consented_at: dt.datetime | None = Field(
        default=None, description="When spoken consent for the daily call was recorded."
    )


class IrrigatedField(_Model):
    """One irrigated field, as registered at onboarding.

    Not named ``Field``: that is pydantic's own, and shadowing it in a module
    that uses ``Field(...)`` for every attribute would be a trap.
    """

    field_id: str
    farmer_id: str
    pump_id: str
    crop: str
    sowing_date: dt.date
    area_m2: float = Field(gt=0.0)
    latitude: float = Field(ge=-90.0, le=90.0)
    longitude: float = Field(ge=-180.0, le=180.0)
    irrigation_efficiency: float = Field(gt=0.0, le=1.0, description="Application efficiency Ea.")


class FieldState(_Model):
    """Everything the scheduler needs to know about one field today.

    Assembled by the caller from the water balance and the crop calendar, so that
    ``plan_day`` itself reads no state and touches no clock.
    """

    field_id: str
    depletion_mm: float = Field(ge=0.0, description="Current root-zone depletion Dr.")
    taw_mm: float = Field(gt=0.0)
    raw_mm: float = Field(gt=0.0, description="Readily available water, p adjusted x TAW.")
    area_m2: float = Field(gt=0.0)
    irrigation_efficiency: float = Field(gt=0.0, le=1.0)
    discharge_l_per_min: float = Field(gt=0.0)
    yield_response_factor: float = Field(gt=0.0, description="Ky at the current stage.")
    carry_over_mm: float = Field(
        default=0.0, ge=0.0, description="Depth owed from a truncated run in an earlier window."
    )

    @property
    def priority(self) -> float:
        """Allocation priority when fields share a pump: (D / RAW) x Ky.

        How far into stress the field is, weighted by how much yield that crop
        loses per unit of deficit. Plan Section 7.
        """
        return (self.depletion_mm / self.raw_mm) * self.yield_response_factor


class Schedule(_Model):
    """The decision for one field on one day."""

    field_id: str
    date: dt.date = Field(description="Local calendar date the decision applies to.")
    decision: Decision
    reason_code: ReasonCode
    minutes: float = Field(default=0.0, ge=0.0, description="Pump running time to instruct.")
    window: PowerWindow | None = Field(
        default=None, description="Window the run is scheduled in. None for SKIP and WAIT."
    )
    start_time: dt.datetime | None = Field(
        default=None,
        description="Clock time to start the pump. None when feeder reliability is "
        "below threshold, in which case the call says 'when power comes' instead.",
    )
    delivered_mm: float = Field(default=0.0, ge=0.0, description="Net depth the run delivers.")
    carry_over_mm: float = Field(
        default=0.0, ge=0.0, description="Net depth not delivered because the run was truncated."
    )
    required_mm: float = Field(
        default=0.0, ge=0.0, description="Net depth the field actually needed."
    )
    forecaster: str = Field(
        default="kc-et0-fao56", description="Model that produced the ETc projection."
    )

    @property
    def was_truncated(self) -> bool:
        """Whether the window was too short to deliver the full requirement."""
        return self.carry_over_mm > 0.0


class Event(_Model):
    """Something the farmer reported, or answered when asked.

    The farmer's missed call is always right. If he says water was given, the
    balance is updated even if the model disagrees. Plan Section 5.5, rule 4.
    """

    event_id: str
    farmer_id: str
    kind: EventKind
    occurred_at: dt.datetime = Field(description="Timezone-aware.")
    field_id: str | None = Field(
        default=None, description="None where the farmer has only one field."
    )
    window_start: dt.datetime | None = Field(
        default=None, description="Window the event refers to, for POWER_FAILED."
    )

    @field_validator("occurred_at")
    @classmethod
    def _must_be_aware(cls, value: dt.datetime) -> dt.datetime:
        """Reject a naive timestamp."""
        if value.tzinfo is None:
            msg = "event timestamps must be timezone-aware"
            raise ValueError(msg)
        return value
