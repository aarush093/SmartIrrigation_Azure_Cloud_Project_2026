"""Azure Communication Services telephony adapter.

Behind a feature flag. ``make demo`` uses
:class:`~irrigation_engine.telephony.SimulatedTelephony` and never touches this
module, because the demonstration must not depend on a phone number that may not
be provisioned in time.

Feasibility, and the reasoning behind every decision here, is recorded in
``docs/ACS_MISSED_CALL_FEASIBILITY.md``. The three findings that shape this code:

1. Event Grid delivers ``Microsoft.Communication.IncomingCall`` on ring, with
   ``data.from`` and ``data.to`` populated **before** any answer.
2. ``Reject`` prevents the call connecting at all, so the farmer is never
   charged. This adapter never calls ``AnswerCall`` for an inbound call.
3. Delivery is **at least once**, so the caller must deduplicate. That is
   :class:`~irrigation_engine.events.MissedCallRouter`, not this adapter.

Cold starts are tolerated by design: if the Reject misses the 30-second ring
window the call simply rings out, and the Event Grid event still arrives and is
still recorded. See Decision 1 in the feasibility note.
"""

from __future__ import annotations

import datetime as dt
import logging
from typing import Any

from irrigation_engine.telephony import CallOutcome, CallResult

__all__ = [
    "INCOMING_CALL_EVENT_TYPE",
    "SUBSCRIPTION_VALIDATION_EVENT_TYPE",
    "AcsCallAutomationTelephony",
    "IncomingCallPayload",
    "parse_incoming_call",
    "subscription_validation_response",
]

logger = logging.getLogger(__name__)

INCOMING_CALL_EVENT_TYPE = "Microsoft.Communication.IncomingCall"
SUBSCRIPTION_VALIDATION_EVENT_TYPE = "Microsoft.EventGrid.SubscriptionValidationEvent"


class IncomingCallPayload:
    """The fields of an ``IncomingCall`` event this project uses.

    Only three matter: who called, what they called, and the token needed to
    reject it. Everything else in the payload is ignored.
    """

    def __init__(
        self,
        *,
        caller: str,
        number_called: str,
        incoming_call_context: str | None,
        received_at: dt.datetime,
    ) -> None:
        """Store the parsed fields."""
        self.caller = caller
        self.number_called = number_called
        self.incoming_call_context = incoming_call_context
        self.received_at = received_at

    def __repr__(self) -> str:
        """Readable form for logs."""
        return f"IncomingCallPayload(caller={self.caller!r}, number_called={self.number_called!r})"


def parse_incoming_call(event: dict[str, Any]) -> IncomingCallPayload | None:
    """Extract the caller and the number called from an Event Grid event.

    Both are present before the call is answered, which is what makes the
    missed-call channel possible at all.

    Args:
        event: One Event Grid event, already JSON-decoded.

    Returns:
        The parsed payload, or None if this is not an ``IncomingCall`` event or
        the phone numbers are absent, which happens for calls between
        Communication Services identities rather than PSTN numbers.
    """
    if event.get("eventType") != INCOMING_CALL_EVENT_TYPE:
        return None

    data = event.get("data") or {}
    caller = (data.get("from") or {}).get("phoneNumber", {}).get("value")
    called = (data.get("to") or {}).get("phoneNumber", {}).get("value")
    if not caller or not called:
        return None

    stamp = event.get("eventTime")
    received = (
        dt.datetime.fromisoformat(stamp.replace("Z", "+00:00"))
        if isinstance(stamp, str)
        else dt.datetime.now(tz=dt.UTC)
    )
    return IncomingCallPayload(
        caller=str(caller),
        number_called=str(called),
        incoming_call_context=data.get("incomingCallContext"),
        received_at=received,
    )


def subscription_validation_response(event: dict[str, Any]) -> dict[str, str] | None:
    """Answer Event Grid's subscription handshake.

    Event Grid will not deliver anything until the webhook echoes the validation
    code back. Without this the missed-call channel silently receives nothing,
    which is a failure mode with no error message anywhere.

    Args:
        event: One Event Grid event.

    Returns:
        The body to return, or None if this is not a validation event.
    """
    if event.get("eventType") != SUBSCRIPTION_VALIDATION_EVENT_TYPE:
        return None
    code = (event.get("data") or {}).get("validationCode")
    return {"validationResponse": str(code)} if code else None


class AcsCallAutomationTelephony:
    """Telephony backed by Azure Communication Services Call Automation.

    Satisfies :class:`~irrigation_engine.telephony.TelephonyAdapter`.

    The SDK is imported lazily inside the methods rather than at module scope, so
    that this module can be imported, type-checked and unit-tested on a machine
    with no ``azure-communication-callautomation`` installed. The engine never
    imports it at all.
    """

    def __init__(
        self,
        *,
        connection_string: str,
        caller_id: str,
        callback_url: str,
        enabled: bool = False,
    ) -> None:
        """Configure the adapter.

        Args:
            connection_string: ACS resource connection string, from Key Vault.
            caller_id: Provisioned PSTN number the outbound call comes from.
            callback_url: HTTPS endpoint for Call Automation webhooks.
            enabled: The feature flag. When False every call returns
                ``NOT_PLACED`` and no Azure call is attempted, which is what
                lets the whole daily loop run in a demo with no ACS resource.
        """
        self.connection_string = connection_string
        self.caller_id = caller_id
        self.callback_url = callback_url
        self.enabled = enabled

    def _client(self) -> Any:  # SDK type is unavailable when not installed
        """Build a Call Automation client, importing the SDK lazily."""
        from azure.communication.callautomation import (
            CallAutomationClient,
        )

        return CallAutomationClient.from_connection_string(self.connection_string)

    def place_call(
        self,
        phone: str,
        script_text: str,
        *,
        audio_url: str | None = None,
        dtmf_options: tuple[str, ...] = (),
    ) -> CallResult:
        """Place the daily outbound call.

        Args:
            phone: Farmer's number in E.164 format.
            script_text: Rendered script, spoken by TextSource if no audio_url.
            audio_url: Cached synthesised audio to play instead.
            dtmf_options: Digits to listen for, for the next-day question.

        Returns:
            The call outcome. ``NOT_PLACED`` when the feature flag is off.
        """
        if not self.enabled:
            logger.info("ACS disabled; would have called %s", phone)
            return CallResult(outcome=CallOutcome.NOT_PLACED)

        try:
            from azure.communication.callautomation import (
                PhoneNumberIdentifier,
            )

            client = self._client()
            result = client.create_call(
                target_participant=PhoneNumberIdentifier(phone),
                callback_url=self.callback_url,
                source_caller_id_number=PhoneNumberIdentifier(self.caller_id),
            )
        except Exception as error:  # any SDK failure is a failed call
            logger.exception("ACS call to %s failed", phone)
            return CallResult(outcome=CallOutcome.FAILED, error=str(error))

        # The script is played and any DTMF recognised on the CallConnected
        # webhook, not here: create_call returns as soon as the call is placed.
        return CallResult(
            outcome=CallOutcome.ANSWERED,
            call_id=getattr(result, "call_connection_id", None),
        )

    def on_incoming_call(self, number_called: str, caller: str) -> None:
        """Reject an inbound missed call without answering it.

        **Never answers.** A connected call would charge the farmer, and the
        information is carried by the fact of the call, not by its contents.

        Args:
            number_called: The toll-free number rung.
            caller: The farmer's number.
        """
        logger.info("missed call from %s to %s", caller, number_called)

    def reject(self, incoming_call_context: str) -> bool:
        """Reject a call so it never connects.

        A best-effort action. If the 30-second ring window has already closed
        because the host was cold, the rejection fails harmlessly: the call has
        rung out on its own and the Event Grid event has still been delivered
        and recorded. See ``docs/ACS_MISSED_CALL_FEASIBILITY.md`` Decision 1.

        Args:
            incoming_call_context: Token from the ``IncomingCall`` event.

        Returns:
            True if the call was rejected inside the window, False otherwise.
        """
        if not self.enabled:
            return False
        try:
            self._client().reject_call(incoming_call_context)
        except Exception:  # a missed window is not an error here
            logger.info("reject missed the ring window; the call rang out instead")
            return False
        return True
