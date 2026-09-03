"""The missed-call state machine: the only sensor this system has.

After onboarding, every fact the platform learns about a field arrives as a
missed call. There is no soil probe, no flow meter and no controller. That makes
this module the most consequential in the project after the scheduler, and its
two hard requirements follow directly from that:

**Idempotency is mandatory, not defensive.** Event Grid delivers at least once
and says so plainly. A replayed ``WATER_GIVEN`` would credit the water balance
twice and then silently under-irrigate the field for the rest of the interval,
with no error anywhere to notice. Every event carries a deduplication key of
caller number, number called and IST date, and a repeat is a no-op.

**The farmer is always right.** If he says water was given, the balance is
updated at the planned depth even if the model disagrees. Plan Section 5.5,
rule 4. The model's job is to predict; his job is to observe.

**Timing does not matter.** An event that arrives twenty seconds late, or a
minute late because the Function was cold, is worth exactly as much as an instant
one: what it updates is a daily water balance. See
``docs/ACS_MISSED_CALL_FEASIBILITY.md`` Decision 3.

Degraded single-number mode is a first-class configuration, not a fallback. Only
one toll-free number may be provisioned in time for the pilot; in that mode the
single number means "paani de diya" and a power failure is inferred from the
absence of that call plus the next day's confirmation question.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from enum import StrEnum

from irrigation_engine.scheduler.models import IST, Event, EventKind

__all__ = [
    "DAY_START_HOUR",
    "EventLog",
    "EventOutcome",
    "MissedCallRouter",
    "NumberMode",
    "StateChange",
    "deduplication_key",
    "operational_date",
]


class NumberMode(StrEnum):
    """How many toll-free numbers are provisioned.

    THREE is the designed configuration. SINGLE is what the pilot may actually
    get, and the demo must run in either.
    """

    THREE = "three"
    SINGLE = "single"


class EventOutcome(StrEnum):
    """What the handler did with an inbound event."""

    ACCEPTED = "accepted"
    DUPLICATE = "duplicate"
    UNKNOWN_NUMBER = "unknown_number"
    UNKNOWN_CALLER = "unknown_caller"


@dataclass(frozen=True)
class StateChange:
    """What an accepted event asks the rest of the system to do."""

    outcome: EventOutcome
    kind: EventKind | None = None
    farmer_id: str | None = None
    #: Net depth to credit to the water balance, mm. Non-zero only for
    #: WATER_GIVEN and KEYPRESS_YES, and always the depth that was *planned*,
    #: never a depth the farmer estimated.
    credit_mm: float = 0.0
    #: Whether the feeder's reliability should be lowered for the window.
    lower_reliability: bool = False
    #: Whether today's schedule should be recomputed.
    replan: bool = False
    #: Whether to call the farmer back immediately with today's script.
    callback: bool = False

    @property
    def accepted(self) -> bool:
        """Whether the event was acted on."""
        return self.outcome is EventOutcome.ACCEPTED


#: Hour, IST, at which the operational day rolls over.
#:
#: NOT midnight. A Maharashtra night feeder runs 22:00 to 06:00, so a farmer who
#: irrigates on that window and rings to confirm at 00:30 is reporting the SAME
#: irrigation as one who rings at 23:30. Keying on the calendar date would put
#: those two calls on different days, and the second would be accepted as a
#: fresh event and credit the water balance a second time.
#:
#: 06:00 is chosen because it is at or after the close of every night window in
#: the pilot districts, and before the working day begins.
DAY_START_HOUR = 6


def operational_date(occurred_at: dt.datetime) -> dt.date:
    """The irrigation day an instant belongs to.

    Not the calendar date. The day rolls over at :data:`DAY_START_HOUR` IST, so
    that a night window crossing midnight is one operational day rather than two.

    Args:
        occurred_at: A timezone-aware instant.

    Returns:
        The operational date.

    Raises:
        ValueError: If ``occurred_at`` is naive.
    """
    if occurred_at.tzinfo is None:
        msg = "event timestamps must be timezone-aware to derive an operational date"
        raise ValueError(msg)
    local = occurred_at.astimezone(IST)
    if local.hour < DAY_START_HOUR:
        return (local - dt.timedelta(days=1)).date()
    return local.date()


def deduplication_key(
    caller: str,
    number_called: str,
    occurred_at: dt.datetime,
    *,
    day: dt.date | None = None,
) -> str:
    """Build the key that makes a replayed event a no-op.

    Caller number, number called, and the **operational date**. The date rather
    than the timestamp, because two genuine missed calls to the same number on
    the same day carry the same information: the farmer confirming twice that he
    watered has still only watered once.

    The operational date rather than the calendar date, because a night window
    crosses midnight. See :func:`operational_date`.

    IST rather than UTC throughout, because the farmer's day is the unit the
    water balance is kept in.

    Args:
        caller: The farmer's phone number, from ``data.from``.
        number_called: The toll-free number rung, from ``data.to``.
        occurred_at: When the call arrived, timezone-aware.
        day: The operational date to key on, where the caller already knows
            which schedule the event refers to. Supplying it is exact; deriving
            it from the clock is a good approximation with one edge case, a
            confirmation arriving before 06:00 about a window that opened that
            same morning.

    Returns:
        A stable deduplication key.

    Raises:
        ValueError: If ``occurred_at`` is naive.
    """
    resolved = day if day is not None else operational_date(occurred_at)
    return f"{caller}|{number_called}|{resolved.isoformat()}"


@dataclass
class EventLog:
    """Records which deduplication keys have already been acted on.

    In production this is a Cosmos DB container with the key as the document id,
    so the uniqueness constraint is enforced by the database rather than by
    application memory. This in-memory form is what the tests and the simulated
    telephony console use.
    """

    seen: set[str] = field(default_factory=set)

    def is_duplicate(self, key: str) -> bool:
        """Whether this key has already been recorded."""
        return key in self.seen

    def record(self, key: str) -> None:
        """Mark a key as acted on."""
        self.seen.add(key)


class MissedCallRouter:
    """Maps an inbound call to the state change it should cause.

    Deliberately a pure function of its inputs plus the event log: it performs no
    I/O, reads no clock and updates nothing itself. It says what should happen;
    the caller does it. That is what makes every transition unit-testable.
    """

    def __init__(
        self,
        *,
        number_water_given: str,
        number_power_failed: str | None = None,
        number_repeat: str | None = None,
        mode: NumberMode = NumberMode.THREE,
        log: EventLog | None = None,
    ) -> None:
        """Configure the routing table.

        Args:
            number_water_given: Toll-free number A, "paani de diya". Required in
                both modes; in SINGLE mode it is the only number.
            number_power_failed: Number B, "bijli nahi aayi". THREE mode only.
            number_repeat: Number C, "aaj ka plan sunao". THREE mode only.
            mode: Which configuration is provisioned.
            log: Deduplication log. A fresh one is created if not supplied.

        Raises:
            ValueError: If THREE mode is selected without all three numbers.
        """
        if mode is NumberMode.THREE and (number_power_failed is None or number_repeat is None):
            msg = (
                "three-number mode needs all three numbers; "
                "use NumberMode.SINGLE if only one is provisioned"
            )
            raise ValueError(msg)

        self.mode = mode
        self.log = log if log is not None else EventLog()
        self._routes: dict[str, EventKind] = {number_water_given: EventKind.WATER_GIVEN}
        if mode is NumberMode.THREE:
            assert number_power_failed is not None
            assert number_repeat is not None
            self._routes[number_power_failed] = EventKind.POWER_FAILED
            self._routes[number_repeat] = EventKind.REPEAT_REQUEST

    def route(
        self,
        *,
        caller: str,
        number_called: str,
        occurred_at: dt.datetime,
        known_farmers: dict[str, str],
        planned_depth_mm: float = 0.0,
    ) -> StateChange:
        """Decide what an inbound missed call means.

        Args:
            caller: The farmer's number, from the ``IncomingCall`` ``data.from``.
            number_called: The number rung, from ``data.to``.
            occurred_at: When it arrived, timezone-aware.
            known_farmers: Phone number to farmer id. Identity is the phone
                number, verified by the missed call itself; there is no login.
            planned_depth_mm: Depth today's schedule asked for. Credited on a
                WATER_GIVEN, because the planned depth is what was almost
                certainly applied and the farmer cannot estimate millimetres.

        Returns:
            The state change to apply, or a non-accepted outcome explaining why
            nothing should happen.
        """
        key = deduplication_key(caller, number_called, occurred_at)

        kind = self._routes.get(number_called)
        if kind is None:
            return StateChange(outcome=EventOutcome.UNKNOWN_NUMBER)

        farmer_id = known_farmers.get(caller)
        if farmer_id is None:
            return StateChange(outcome=EventOutcome.UNKNOWN_CALLER)

        # A repeat request is the one event that may legitimately recur within a
        # day: a farmer who did not catch the message the first time will ring
        # again, and refusing him would be perverse.
        if kind is not EventKind.REPEAT_REQUEST and self.log.is_duplicate(key):
            return StateChange(outcome=EventOutcome.DUPLICATE, kind=kind, farmer_id=farmer_id)

        self.log.record(key)
        return self._change_for(kind, farmer_id, planned_depth_mm)

    @staticmethod
    def _change_for(kind: EventKind, farmer_id: str, planned_depth_mm: float) -> StateChange:
        """Map an event kind to its effects."""
        if kind is EventKind.WATER_GIVEN:
            return StateChange(
                outcome=EventOutcome.ACCEPTED,
                kind=kind,
                farmer_id=farmer_id,
                credit_mm=planned_depth_mm,
            )
        if kind is EventKind.POWER_FAILED:
            return StateChange(
                outcome=EventOutcome.ACCEPTED,
                kind=kind,
                farmer_id=farmer_id,
                lower_reliability=True,
                replan=True,
            )
        return StateChange(
            outcome=EventOutcome.ACCEPTED,
            kind=kind,
            farmer_id=farmer_id,
            callback=True,
        )

    def route_keypress(
        self,
        *,
        caller: str,
        digit: str,
        occurred_at: dt.datetime,
        known_farmers: dict[str, str],
        planned_depth_mm: float = 0.0,
    ) -> StateChange:
        """Handle the keypress fallback asked when no missed call arrived.

        Keypress is never the primary channel: published evaluations of IVR with
        Indian farmers found very low response to keypress prompts (plan
        reference R18). It exists only for the farmer who neither rang nor was
        reached.

        Args:
            caller: The farmer's number.
            digit: ``"1"`` for yes, ``"2"`` for no.
            occurred_at: When the keypress arrived, timezone-aware.
            known_farmers: Phone number to farmer id.
            planned_depth_mm: Depth today's schedule asked for.

        Returns:
            The state change, treating a yes exactly as a WATER_GIVEN missed call
            and a no as an explicit confirmation that nothing was applied.
        """
        farmer_id = known_farmers.get(caller)
        if farmer_id is None:
            return StateChange(outcome=EventOutcome.UNKNOWN_CALLER)

        kind = EventKind.KEYPRESS_YES if digit == "1" else EventKind.KEYPRESS_NO
        key = deduplication_key(caller, f"keypress:{digit}", occurred_at)
        if self.log.is_duplicate(key):
            return StateChange(outcome=EventOutcome.DUPLICATE, kind=kind, farmer_id=farmer_id)
        self.log.record(key)

        if kind is EventKind.KEYPRESS_YES:
            return StateChange(
                outcome=EventOutcome.ACCEPTED,
                kind=kind,
                farmer_id=farmer_id,
                credit_mm=planned_depth_mm,
            )
        # An explicit "no" is information, not silence: the field was not
        # watered, so the schedule must be recomputed rather than assumed done.
        return StateChange(
            outcome=EventOutcome.ACCEPTED, kind=kind, farmer_id=farmer_id, replan=True
        )

    def infer_power_failure(
        self,
        *,
        water_given_today: bool,
        keypress_answer: EventKind | None,
    ) -> bool:
        """Infer a power failure in single-number mode.

        With only one number provisioned there is no way for the farmer to
        report that the power did not come. It is inferred from the absence of a
        WATER_GIVEN call together with an explicit "no" to the next day's
        question.

        Absence alone is not enough: a farmer who simply forgot to ring looks
        identical to one whose feeder failed, and lowering a feeder's reliability
        on that evidence would degrade every future schedule for the village.

        Args:
            water_given_today: Whether a WATER_GIVEN call arrived.
            keypress_answer: The answer to the next day's question, if any.

        Returns:
            True when a power failure should be inferred.
        """
        if self.mode is not NumberMode.SINGLE:
            return False
        return not water_given_today and keypress_answer is EventKind.KEYPRESS_NO

    def build_event(
        self,
        *,
        change: StateChange,
        caller: str,
        occurred_at: dt.datetime,
        field_id: str | None = None,
        window_start: dt.datetime | None = None,
    ) -> Event:
        """Build the persisted Event record for an accepted change.

        Args:
            change: An accepted state change.
            caller: The farmer's number, used to build the event id.
            occurred_at: When the call arrived.
            field_id: Field the event refers to, where the farmer has more than
                one.
            window_start: Window the event refers to, for POWER_FAILED.

        Returns:
            The record to persist.

        Raises:
            ValueError: If the change was not accepted.
        """
        if not change.accepted or change.kind is None or change.farmer_id is None:
            msg = f"cannot build an event from a {change.outcome.value} change"
            raise ValueError(msg)
        return Event(
            event_id=deduplication_key(caller, change.kind.value, occurred_at),
            farmer_id=change.farmer_id,
            kind=change.kind,
            occurred_at=occurred_at,
            field_id=field_id,
            window_start=window_start,
        )
