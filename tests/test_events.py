"""Tests for the missed-call state machine.

Every transition, plus the idempotency that Event Grid's at-least-once delivery
makes mandatory. A replayed WATER_GIVEN that credited the balance twice would
silently under-irrigate the field for the rest of the interval, with no error
anywhere to notice it, so the duplicate tests here carry more weight than their
length suggests.
"""

from __future__ import annotations

import datetime as dt

import pytest

from irrigation_engine.events import (
    EventLog,
    EventOutcome,
    MissedCallRouter,
    NumberMode,
    deduplication_key,
    operational_date,
)
from irrigation_engine.scheduler.models import IST, EventKind

NUMBER_A = "+918000000001"
NUMBER_B = "+918000000002"
NUMBER_C = "+918000000003"
FARMER_PHONE = "+919876543210"
FARMERS = {FARMER_PHONE: "farmer-001"}

# 22:30 IST on 3 September, during a night window.
DURING_WINDOW = dt.datetime(2026, 9, 3, 22, 30, tzinfo=IST)


def router(mode: NumberMode = NumberMode.THREE, log: EventLog | None = None) -> MissedCallRouter:
    """A router in the requested mode."""
    if mode is NumberMode.THREE:
        return MissedCallRouter(
            number_water_given=NUMBER_A,
            number_power_failed=NUMBER_B,
            number_repeat=NUMBER_C,
            mode=mode,
            log=log,
        )
    return MissedCallRouter(number_water_given=NUMBER_A, mode=mode, log=log)


class TestTransitions:
    """One test per transition in the three-number vocabulary."""

    def test_number_a_credits_the_planned_depth(self) -> None:
        """The farmer cannot estimate millimetres, so the PLANNED depth is credited.

        Plan Section 5.5 rule 4: his missed call is always right about whether
        water was given. The model is right about how much.
        """
        change = router().route(
            caller=FARMER_PHONE,
            number_called=NUMBER_A,
            occurred_at=DURING_WINDOW,
            known_farmers=FARMERS,
            planned_depth_mm=25.0,
        )
        assert change.accepted
        assert change.kind is EventKind.WATER_GIVEN
        assert change.credit_mm == pytest.approx(25.0)
        assert change.farmer_id == "farmer-001"
        assert not change.replan

    def test_number_b_lowers_reliability_and_replans(self) -> None:
        """A power failure is the only direct measurement of the feeder we get."""
        change = router().route(
            caller=FARMER_PHONE,
            number_called=NUMBER_B,
            occurred_at=DURING_WINDOW,
            known_farmers=FARMERS,
        )
        assert change.accepted
        assert change.kind is EventKind.POWER_FAILED
        assert change.lower_reliability
        assert change.replan
        assert change.credit_mm == 0.0

    def test_number_c_triggers_an_immediate_callback(self) -> None:
        change = router().route(
            caller=FARMER_PHONE,
            number_called=NUMBER_C,
            occurred_at=DURING_WINDOW,
            known_farmers=FARMERS,
        )
        assert change.accepted
        assert change.kind is EventKind.REPEAT_REQUEST
        assert change.callback
        assert change.credit_mm == 0.0

    def test_an_unknown_number_is_rejected(self) -> None:
        change = router().route(
            caller=FARMER_PHONE,
            number_called="+919999999999",
            occurred_at=DURING_WINDOW,
            known_farmers=FARMERS,
        )
        assert change.outcome is EventOutcome.UNKNOWN_NUMBER
        assert not change.accepted

    def test_an_unknown_caller_is_rejected(self) -> None:
        """Identity is the phone number, verified by the missed call itself."""
        change = router().route(
            caller="+910000000000",
            number_called=NUMBER_A,
            occurred_at=DURING_WINDOW,
            known_farmers=FARMERS,
        )
        assert change.outcome is EventOutcome.UNKNOWN_CALLER
        assert not change.accepted


class TestIdempotency:
    """Event Grid delivers at least once, and says so."""

    def test_a_replayed_event_is_a_no_op(self) -> None:
        """The single most important test in this module.

        Crediting the balance twice would under-irrigate the field for the rest
        of the interval, silently.
        """
        r = router()
        first = r.route(
            caller=FARMER_PHONE,
            number_called=NUMBER_A,
            occurred_at=DURING_WINDOW,
            known_farmers=FARMERS,
            planned_depth_mm=25.0,
        )
        replay = r.route(
            caller=FARMER_PHONE,
            number_called=NUMBER_A,
            occurred_at=DURING_WINDOW,
            known_farmers=FARMERS,
            planned_depth_mm=25.0,
        )

        assert first.accepted
        assert first.credit_mm == pytest.approx(25.0)
        assert replay.outcome is EventOutcome.DUPLICATE
        assert replay.credit_mm == 0.0
        assert not replay.accepted

    def test_a_replay_at_a_different_time_on_the_same_day_is_still_a_duplicate(self) -> None:
        """Two genuine calls on one operational day carry the same information.

        The second call here lands at 00:00, after midnight but still inside the
        same 22:00 to 06:00 night window. That is exactly the case the
        operational day boundary exists to handle: without it the balance would
        be credited twice for one irrigation.
        """
        r = router()
        r.route(
            caller=FARMER_PHONE,
            number_called=NUMBER_A,
            occurred_at=DURING_WINDOW,
            known_farmers=FARMERS,
            planned_depth_mm=25.0,
        )
        later = r.route(
            caller=FARMER_PHONE,
            number_called=NUMBER_A,
            occurred_at=DURING_WINDOW + dt.timedelta(minutes=90),
            known_farmers=FARMERS,
            planned_depth_mm=25.0,
        )
        assert later.outcome is EventOutcome.DUPLICATE

    def test_timing_within_the_day_does_not_change_the_outcome(self) -> None:
        """A cold-start delay must not change what the event means.

        This is the test that lets the system run on a consumption plan: an
        event arriving a minute after the ring is worth exactly as much as one
        arriving instantly. See docs/ACS_MISSED_CALL_FEASIBILITY.md Decision 3.
        """
        instant = router().route(
            caller=FARMER_PHONE,
            number_called=NUMBER_A,
            occurred_at=DURING_WINDOW,
            known_farmers=FARMERS,
            planned_depth_mm=25.0,
        )
        delayed = router().route(
            caller=FARMER_PHONE,
            number_called=NUMBER_A,
            occurred_at=DURING_WINDOW + dt.timedelta(seconds=75),
            known_farmers=FARMERS,
            planned_depth_mm=25.0,
        )
        assert instant.outcome == delayed.outcome
        assert instant.kind == delayed.kind
        assert instant.credit_mm == delayed.credit_mm
        assert instant.replan == delayed.replan

    def test_the_next_day_is_a_new_event(self) -> None:
        """Deduplication is per day, not forever. He waters again tomorrow."""
        r = router()
        r.route(
            caller=FARMER_PHONE,
            number_called=NUMBER_A,
            occurred_at=DURING_WINDOW,
            known_farmers=FARMERS,
            planned_depth_mm=25.0,
        )
        tomorrow = r.route(
            caller=FARMER_PHONE,
            number_called=NUMBER_A,
            occurred_at=DURING_WINDOW + dt.timedelta(days=1),
            known_farmers=FARMERS,
            planned_depth_mm=25.0,
        )
        assert tomorrow.accepted

    def test_a_repeat_request_may_legitimately_recur(self) -> None:
        """Refusing a second listen would be perverse.

        A farmer who did not catch the message will ring again, and that is the
        one event that should not be deduplicated.
        """
        r = router()
        first = r.route(
            caller=FARMER_PHONE,
            number_called=NUMBER_C,
            occurred_at=DURING_WINDOW,
            known_farmers=FARMERS,
        )
        second = r.route(
            caller=FARMER_PHONE,
            number_called=NUMBER_C,
            occurred_at=DURING_WINDOW + dt.timedelta(minutes=5),
            known_farmers=FARMERS,
        )
        assert first.accepted
        assert second.accepted
        assert second.callback

    def test_different_farmers_do_not_collide(self) -> None:
        log = EventLog()
        r = router(log=log)
        others = dict(FARMERS)
        others["+919111111111"] = "farmer-002"

        first = r.route(
            caller=FARMER_PHONE,
            number_called=NUMBER_A,
            occurred_at=DURING_WINDOW,
            known_farmers=others,
            planned_depth_mm=25.0,
        )
        second = r.route(
            caller="+919111111111",
            number_called=NUMBER_A,
            occurred_at=DURING_WINDOW,
            known_farmers=others,
            planned_depth_mm=30.0,
        )
        assert first.accepted
        assert second.accepted
        assert second.credit_mm == pytest.approx(30.0)

    def test_different_numbers_do_not_collide(self) -> None:
        """The same farmer may report both that he watered and that power failed."""
        r = router()
        a = r.route(
            caller=FARMER_PHONE,
            number_called=NUMBER_A,
            occurred_at=DURING_WINDOW,
            known_farmers=FARMERS,
            planned_depth_mm=25.0,
        )
        b = r.route(
            caller=FARMER_PHONE,
            number_called=NUMBER_B,
            occurred_at=DURING_WINDOW,
            known_farmers=FARMERS,
        )
        assert a.accepted
        assert b.accepted


class TestOperationalDay:
    """The day boundary that keeps one night's irrigation on one key."""

    def test_a_call_after_midnight_belongs_to_the_previous_operational_day(self) -> None:
        """The whole reason the boundary is not midnight.

        A Maharashtra night feeder runs 22:00 to 06:00. A farmer ringing at
        00:30 reports the same irrigation as one ringing at 23:30, and keying on
        the calendar date would credit the water balance twice.
        """
        assert operational_date(dt.datetime(2026, 9, 4, 0, 30, tzinfo=IST)) == dt.date(2026, 9, 3)
        assert operational_date(dt.datetime(2026, 9, 4, 5, 59, tzinfo=IST)) == dt.date(2026, 9, 3)

    def test_the_day_rolls_over_at_six(self) -> None:
        assert operational_date(dt.datetime(2026, 9, 4, 6, 0, tzinfo=IST)) == dt.date(2026, 9, 4)

    def test_an_evening_call_belongs_to_its_own_calendar_day(self) -> None:
        assert operational_date(DURING_WINDOW) == dt.date(2026, 9, 3)

    def test_the_whole_night_window_maps_to_one_day(self) -> None:
        """Every half hour of a 22:00 to 06:00 window shares an operational date."""
        start = dt.datetime(2026, 9, 3, 22, 0, tzinfo=IST)
        dates = {operational_date(start + dt.timedelta(minutes=m)) for m in range(0, 8 * 60, 30)}
        assert dates == {dt.date(2026, 9, 3)}

    def test_an_explicit_day_overrides_the_derived_one(self) -> None:
        """Where the handler already knows the schedule, keying is exact."""
        key = deduplication_key("a", "b", DURING_WINDOW, day=dt.date(2026, 1, 1))
        assert "2026-01-01" in key


class TestDeduplicationKey:
    """The key itself."""

    def test_the_key_uses_ist_not_utc(self) -> None:
        """The farmer's day is the unit the water balance is kept in."""
        assert "2026-09-03" in deduplication_key("a", "b", DURING_WINDOW)

    def test_the_key_is_stable_for_the_same_inputs(self) -> None:
        assert deduplication_key("a", "b", DURING_WINDOW) == deduplication_key(
            "a", "b", DURING_WINDOW
        )

    def test_a_naive_timestamp_is_rejected(self) -> None:
        """Without a timezone the operational date cannot be derived correctly."""
        with pytest.raises(ValueError, match="timezone-aware"):
            deduplication_key("a", "b", dt.datetime(2026, 9, 3, 22, 30))

    def test_an_event_arriving_in_utc_is_converted(self) -> None:
        """The webhook receives UTC; the key must still be the farmer's day."""
        utc = dt.datetime(2026, 9, 3, 17, 0, tzinfo=dt.UTC)
        assert deduplication_key("a", "b", utc) == deduplication_key("a", "b", DURING_WINDOW)


class TestSingleNumberMode:
    """What the pilot may actually get."""

    def test_single_mode_needs_only_one_number(self) -> None:
        assert router(NumberMode.SINGLE).mode is NumberMode.SINGLE

    def test_three_mode_without_three_numbers_is_rejected(self) -> None:
        """Silently degrading would leave two meanings unreachable and unnoticed."""
        with pytest.raises(ValueError, match="three-number mode"):
            MissedCallRouter(number_water_given=NUMBER_A, mode=NumberMode.THREE)

    def test_the_single_number_still_means_water_given(self) -> None:
        change = router(NumberMode.SINGLE).route(
            caller=FARMER_PHONE,
            number_called=NUMBER_A,
            occurred_at=DURING_WINDOW,
            known_farmers=FARMERS,
            planned_depth_mm=25.0,
        )
        assert change.accepted
        assert change.kind is EventKind.WATER_GIVEN

    def test_the_other_numbers_are_unknown_in_single_mode(self) -> None:
        change = router(NumberMode.SINGLE).route(
            caller=FARMER_PHONE,
            number_called=NUMBER_B,
            occurred_at=DURING_WINDOW,
            known_farmers=FARMERS,
        )
        assert change.outcome is EventOutcome.UNKNOWN_NUMBER

    def test_a_power_failure_is_inferred_from_silence_plus_an_explicit_no(self) -> None:
        r = router(NumberMode.SINGLE)
        assert r.infer_power_failure(water_given_today=False, keypress_answer=EventKind.KEYPRESS_NO)

    def test_silence_alone_does_not_infer_a_power_failure(self) -> None:
        """A farmer who simply forgot to ring looks identical to a failed feeder.

        Lowering a feeder's reliability on that evidence would degrade every
        future schedule for the whole village.
        """
        r = router(NumberMode.SINGLE)
        assert not r.infer_power_failure(water_given_today=False, keypress_answer=None)

    def test_a_yes_answer_does_not_infer_a_power_failure(self) -> None:
        r = router(NumberMode.SINGLE)
        assert not r.infer_power_failure(
            water_given_today=False, keypress_answer=EventKind.KEYPRESS_YES
        )

    def test_three_number_mode_never_infers(self) -> None:
        """With number B provisioned there is no need to guess."""
        r = router(NumberMode.THREE)
        assert not r.infer_power_failure(
            water_given_today=False, keypress_answer=EventKind.KEYPRESS_NO
        )


class TestKeypressFallback:
    """The fallback for the farmer who neither rang nor was reached."""

    def test_a_yes_credits_the_planned_depth(self) -> None:
        change = router().route_keypress(
            caller=FARMER_PHONE,
            digit="1",
            occurred_at=DURING_WINDOW,
            known_farmers=FARMERS,
            planned_depth_mm=25.0,
        )
        assert change.accepted
        assert change.kind is EventKind.KEYPRESS_YES
        assert change.credit_mm == pytest.approx(25.0)

    def test_a_no_triggers_a_replan_rather_than_being_ignored(self) -> None:
        """An explicit no is information, not silence."""
        change = router().route_keypress(
            caller=FARMER_PHONE, digit="2", occurred_at=DURING_WINDOW, known_farmers=FARMERS
        )
        assert change.accepted
        assert change.kind is EventKind.KEYPRESS_NO
        assert change.credit_mm == 0.0
        assert change.replan

    def test_a_replayed_keypress_is_a_no_op(self) -> None:
        r = router()
        r.route_keypress(
            caller=FARMER_PHONE,
            digit="1",
            occurred_at=DURING_WINDOW,
            known_farmers=FARMERS,
            planned_depth_mm=25.0,
        )
        replay = r.route_keypress(
            caller=FARMER_PHONE,
            digit="1",
            occurred_at=DURING_WINDOW,
            known_farmers=FARMERS,
            planned_depth_mm=25.0,
        )
        assert replay.outcome is EventOutcome.DUPLICATE

    def test_an_unknown_caller_is_rejected(self) -> None:
        change = router().route_keypress(
            caller="+910000000000",
            digit="1",
            occurred_at=DURING_WINDOW,
            known_farmers=FARMERS,
        )
        assert change.outcome is EventOutcome.UNKNOWN_CALLER


class TestEventRecord:
    """The persisted record."""

    def test_an_accepted_change_builds_an_event(self) -> None:
        r = router()
        change = r.route(
            caller=FARMER_PHONE,
            number_called=NUMBER_A,
            occurred_at=DURING_WINDOW,
            known_farmers=FARMERS,
            planned_depth_mm=25.0,
        )
        event = r.build_event(change=change, caller=FARMER_PHONE, occurred_at=DURING_WINDOW)
        assert event.farmer_id == "farmer-001"
        assert event.kind is EventKind.WATER_GIVEN
        assert event.occurred_at == DURING_WINDOW

    def test_a_duplicate_cannot_build_an_event(self) -> None:
        r = router()
        r.route(
            caller=FARMER_PHONE,
            number_called=NUMBER_A,
            occurred_at=DURING_WINDOW,
            known_farmers=FARMERS,
        )
        duplicate = r.route(
            caller=FARMER_PHONE,
            number_called=NUMBER_A,
            occurred_at=DURING_WINDOW,
            known_farmers=FARMERS,
        )
        with pytest.raises(ValueError, match="duplicate"):
            r.build_event(change=duplicate, caller=FARMER_PHONE, occurred_at=DURING_WINDOW)

    def test_the_event_serialises_for_cosmos(self) -> None:
        r = router()
        change = r.route(
            caller=FARMER_PHONE,
            number_called=NUMBER_B,
            occurred_at=DURING_WINDOW,
            known_farmers=FARMERS,
        )
        event = r.build_event(
            change=change,
            caller=FARMER_PHONE,
            occurred_at=DURING_WINDOW,
            window_start=DURING_WINDOW,
        )
        payload = event.model_dump(mode="json")
        assert payload["kind"] == "power_failed"
        assert payload["farmer_id"] == "farmer-001"
