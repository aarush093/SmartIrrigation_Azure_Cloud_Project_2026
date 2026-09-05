"""What a farmer's ``WATER_GIVEN`` missed call credits to the water balance.

The credit must be the depth the scheduled run could actually *deliver* inside
the window, not the depth it asked for. A truncated run leaves its shortfall in
the depletion, and that is exactly where the next day's requirement reads it
from; crediting the full requirement would erase the shortfall from the balance
and put it back in play as a separate carry-over quantity, which is the double
count removed on 5 September 2026.

Two things are pinned here: that the handler reads ``delivered_mm``, and that it
keys on the **operational** day, so a night run confirmed after midnight is
credited against the schedule it belongs to.
"""

from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

import pytest

from irrigation_engine.scheduler.models import IST

FUNCTIONS = Path(__file__).resolve().parents[1] / "src" / "azure" / "functions"
if str(FUNCTIONS) not in sys.path:
    sys.path.insert(0, str(FUNCTIONS))

from function_app import _planned_depth_mm  # noqa: E402

from adapters.cosmos_store import InMemoryStore  # noqa: E402

FARMER = "farmer-1"


def _store_with(*, delivered: float, required: float, day: dt.date) -> InMemoryStore:
    """A store holding one field with one schedule for ``day``."""
    store = InMemoryStore()
    store.fields.append({"field_id": "f1", "farmer_id": FARMER})
    store.save_schedule(
        {
            "field_id": "f1",
            "date": day.isoformat(),
            "delivered_mm": delivered,
            "required_mm": required,
        }
    )
    return store


class TestPlannedDepth:
    """The credit is the delivered depth, on the operational day."""

    def test_it_credits_the_delivered_depth_not_the_requirement(self) -> None:
        day = dt.date(2026, 6, 15)
        store = _store_with(delivered=18.0, required=45.0, day=day)
        at = dt.datetime(2026, 6, 15, 19, 0, tzinfo=IST)
        assert _planned_depth_mm(store, FARMER, at) == pytest.approx(18.0)

    def test_a_night_run_confirmed_after_midnight_is_still_credited(self) -> None:
        """The operational day rolls at 06:00 IST, not at midnight.

        A Maharashtra night feeder runs 22:00 to 06:00. A farmer ringing at 00:30
        is confirming the run planned for the previous calendar date, and keying
        on the calendar date would find no schedule and credit nothing.
        """
        day = dt.date(2026, 6, 15)
        store = _store_with(delivered=18.0, required=45.0, day=day)
        after_midnight = dt.datetime(2026, 6, 16, 0, 30, tzinfo=IST)
        assert _planned_depth_mm(store, FARMER, after_midnight) == pytest.approx(18.0)

    def test_it_sums_across_a_farmers_fields(self) -> None:
        day = dt.date(2026, 6, 15)
        store = _store_with(delivered=18.0, required=45.0, day=day)
        store.fields.append({"field_id": "f2", "farmer_id": FARMER})
        store.save_schedule({"field_id": "f2", "date": day.isoformat(), "delivered_mm": 7.5})
        at = dt.datetime(2026, 6, 15, 19, 0, tzinfo=IST)
        assert _planned_depth_mm(store, FARMER, at) == pytest.approx(25.5)

    def test_an_unknown_caller_credits_nothing(self) -> None:
        store = _store_with(delivered=18.0, required=45.0, day=dt.date(2026, 6, 15))
        at = dt.datetime(2026, 6, 15, 19, 0, tzinfo=IST)
        assert _planned_depth_mm(store, None, at) == 0.0

    def test_no_schedule_credits_nothing_rather_than_guessing(self) -> None:
        """Silence is not evidence of a depth. A missing plan credits zero."""
        store = InMemoryStore()
        store.fields.append({"field_id": "f1", "farmer_id": FARMER})
        at = dt.datetime(2026, 6, 15, 19, 0, tzinfo=IST)
        assert _planned_depth_mm(store, FARMER, at) == 0.0
