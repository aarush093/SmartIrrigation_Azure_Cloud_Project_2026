"""Azure Functions app, Python v2 programming model.

**This file must sit at the deployment root.** The v2 model discovers triggers by
importing ``function_app.py`` from the root of the deployed package, so
``src/azure/functions/`` is the deployable unit and is what ``func azure
functionapp publish`` is pointed at. The course-mandated folder structure is not
disturbed to achieve that; see ``README.md`` in this directory for how the engine
is packaged alongside it.

Hosting is the **consumption plan**, decided in
``docs/ACS_MISSED_CALL_FEASIBILITY.md`` Decision 1. Microsoft warns against
consumption for incoming-call webhooks, but that warning is written for
applications that must *answer* inside the 30-second ring. This one never
answers: if a cold start means the Reject misses the window, the call rings out
and the Event Grid event still arrives and is still recorded. Nothing is lost.

Triggers:

* ``daily_plan``   timer, once an hour; plans for farmers whose call is due
* ``keep_warm``    timer, every five minutes; comfort only, never correctness
* ``acs_events``   HTTP, Event Grid webhook for IncomingCall and validation
* ``onboard``      HTTP, POST a farmer profile
* ``today``        HTTP, GET the day's schedule for the PWA

The FastAPI application is mounted through ``AsgiFunctionApp`` so that the
Phase-I declared stack, FastAPI on the Azure Functions Python worker, is exactly
what runs. Plan Section 17.4.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
import os
from typing import Any

import azure.functions as func

from irrigation_engine.events import EventLog, MissedCallRouter, NumberMode
from irrigation_engine.scheduler.models import IST

from api import app as fastapi_app  # isort: skip
from adapters.acs_telephony import (  # isort: skip
    AcsCallAutomationTelephony,
    parse_incoming_call,
    subscription_validation_response,
)

logger = logging.getLogger(__name__)

app = func.AsgiFunctionApp(app=fastapi_app, http_auth_level=func.AuthLevel.ANONYMOUS)


def _flag(name: str, default: str = "false") -> bool:
    """Read a boolean feature flag from the environment."""
    return os.environ.get(name, default).strip().lower() in {"1", "true", "yes"}


def _router() -> MissedCallRouter:
    """Build the missed-call router from configuration.

    Falls back to single-number mode when only one number is provisioned, which
    is what the pilot may actually get.
    """
    number_a = os.environ.get("MISSEDCALL_NUMBER_WATER_GIVEN", "")
    number_b = os.environ.get("MISSEDCALL_NUMBER_POWER_FAILED") or None
    number_c = os.environ.get("MISSEDCALL_NUMBER_REPEAT") or None

    if number_b and number_c:
        return MissedCallRouter(
            number_water_given=number_a,
            number_power_failed=number_b,
            number_repeat=number_c,
            mode=NumberMode.THREE,
            log=EventLog(),
        )
    return MissedCallRouter(number_water_given=number_a, mode=NumberMode.SINGLE, log=EventLog())


@app.timer_trigger(schedule="0 0 * * * *", arg_name="timer", run_on_startup=False, use_monitor=True)
def daily_plan(timer: func.TimerRequest) -> None:
    """Plan and call for every farmer whose call is due this hour.

    Runs hourly rather than once a day because the call time depends on each
    farmer's own power window and on quiet hours, so different farmers are due at
    different times. The planning itself is deterministic and idempotent: running
    it twice for the same farmer and day produces the same schedule.

    Args:
        timer: The timer request, unused beyond its past-due flag.
    """
    now = dt.datetime.now(tz=IST)
    if timer.past_due:
        logger.warning("daily_plan is running late; schedules may be delayed")
    logger.info("daily_plan tick at %s", now.isoformat())
    # Farmer iteration, Cosmos reads and call dispatch are wired in M5 alongside
    # the Cosmos bindings. The planning logic itself is complete and tested in
    # irrigation_engine.scheduler.


@app.timer_trigger(
    schedule="0 */5 * * * *", arg_name="timer", run_on_startup=True, use_monitor=False
)
def keep_warm(timer: func.TimerRequest) -> None:
    """Keep the host warm so more inbound calls receive an instant Reject.

    **Comfort, not correctness.** Removing this trigger changes the share of
    calls rejected inside the ring window; it never changes whether an event is
    recorded. ``docs/ACS_MISSED_CALL_FEASIBILITY.md`` Decision 3, and
    ``tests/test_events.py::test_timing_within_the_day_does_not_change_the_outcome``
    is the test that holds that line.

    Args:
        timer: The timer request, unused.
    """
    del timer


@app.route(route="acs_events", methods=["POST"])
def acs_events(req: func.HttpRequest) -> func.HttpResponse:
    """Event Grid webhook for inbound missed calls.

    Handles three things, in order:

    1. The subscription validation handshake. Event Grid delivers nothing until
       the code is echoed back, and the failure mode without it is silence with
       no error anywhere.
    2. ``IncomingCall`` events: reject the call so the farmer is never charged,
       and record the missed call as a field observation.
    3. Anything else: acknowledge and ignore.

    Always returns 200 for a well-formed request. A non-200 makes Event Grid
    retry, and a retry of an event we have already deduplicated is wasted work.

    Args:
        req: The HTTP request carrying one or more Event Grid events.

    Returns:
        The validation response, or a summary of what was processed.
    """
    try:
        body: Any = req.get_json()
    except ValueError:
        return func.HttpResponse("expected a JSON array of Event Grid events", status_code=400)

    # Event Grid posts an array, but the portal's test-send posts a single
    # object. Accepting both means a manual test does not look like a bug.
    events: list[dict[str, Any]] = [body] if isinstance(body, dict) else list(body)

    for event in events:
        validation = subscription_validation_response(event)
        if validation is not None:
            logger.info("answering Event Grid subscription validation")
            return func.HttpResponse(
                json.dumps(validation), mimetype="application/json", status_code=200
            )

    router = _router()
    telephony = AcsCallAutomationTelephony(
        connection_string=os.environ.get("ACS_CONNECTION_STRING", ""),
        caller_id=os.environ.get("ACS_CALLER_ID", ""),
        callback_url=os.environ.get("ACS_CALLBACK_URL", ""),
        enabled=_flag("ACS_ENABLED"),
    )

    processed = 0
    for event in events:
        payload = parse_incoming_call(event)
        if payload is None:
            continue

        # Reject first, so the farmer's line is freed as early as possible. A
        # failure here means the ring window had already closed, which is
        # tolerated: the call rings out and the event is still recorded below.
        if payload.incoming_call_context:
            telephony.reject(payload.incoming_call_context)

        change = router.route(
            caller=payload.caller,
            number_called=payload.number_called,
            occurred_at=payload.received_at,
            known_farmers=_known_farmers(),
            planned_depth_mm=0.0,
        )
        logger.info(
            "missed call from %s to %s: %s",
            payload.caller,
            payload.number_called,
            change.outcome.value,
        )
        processed += 1

    return func.HttpResponse(
        json.dumps({"processed": processed}), mimetype="application/json", status_code=200
    )


def _known_farmers() -> dict[str, str]:
    """Phone number to farmer id.

    Read from Cosmos in M5. Identity is the phone number, verified by the missed
    call itself; there is no login anywhere in the farmer-facing path.
    """
    return {}
