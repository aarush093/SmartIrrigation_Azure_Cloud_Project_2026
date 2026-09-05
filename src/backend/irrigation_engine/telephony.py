"""Telephony and speech adapters, with offline fakes.

Both interfaces live in the engine and carry no Azure import. The Azure
implementations live in ``src/azure/`` behind a feature flag, so ``make demo``
runs end to end with no ACS resource, no phone number and no credentials. That
is a hard requirement: the demonstration must not depend on a phone number that
may not be provisioned in time.

The simulated telephony writes to an in-memory queue and to a browser call
console, which is what a reviewer will actually be shown.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Protocol, runtime_checkable

__all__ = [
    "CallOutcome",
    "CallResult",
    "FakeSpeech",
    "PlacedCall",
    "SimulatedTelephony",
    "SpeechAdapter",
    "SpeechResult",
    "TelephonyAdapter",
]


class CallOutcome(StrEnum):
    """How an outbound call ended."""

    ANSWERED = "answered"
    NO_ANSWER = "no_answer"
    BUSY = "busy"
    FAILED = "failed"
    #: The call was never placed because the feature flag is off or no number is
    #: provisioned. Distinct from FAILED, which means it was tried and did not
    #: work.
    NOT_PLACED = "not_placed"


@dataclass(frozen=True)
class CallResult:
    """The outcome of one outbound call."""

    outcome: CallOutcome
    call_id: str | None = None
    #: DTMF digit the farmer pressed, if the call recognised one.
    digit: str | None = None
    duration_seconds: float = 0.0
    error: str | None = None

    @property
    def reached_farmer(self) -> bool:
        """Whether the farmer actually heard the message."""
        return self.outcome is CallOutcome.ANSWERED


@dataclass(frozen=True)
class PlacedCall:
    """A record of a call the simulated adapter was asked to place."""

    phone: str
    text: str
    placed_at: dt.datetime
    dtmf_options: tuple[str, ...] = ()
    audio_url: str | None = None


@dataclass(frozen=True)
class SpeechResult:
    """Rendered speech for one script.

    ``audio_url`` is None where synthesis was faked, in which case ``text`` is
    the whole result and the console simply displays it.
    """

    text: str
    audio_url: str | None = None
    voice: str | None = None
    cache_key: str | None = None

    @property
    def was_synthesised(self) -> bool:
        """Whether real audio exists."""
        return self.audio_url is not None


@runtime_checkable
class TelephonyAdapter(Protocol):
    """Places outbound calls and receives inbound missed calls."""

    def place_call(
        self,
        phone: str,
        script_text: str,
        *,
        audio_url: str | None = None,
        dtmf_options: tuple[str, ...] = (),
    ) -> CallResult:
        """Place one outbound call.

        Args:
            phone: Destination in E.164 format.
            script_text: The words to speak, already rendered and translated.
            audio_url: Pre-synthesised audio to play instead of speaking the
                text, normally a cached blob keyed by script hash.
            dtmf_options: Digits the call should listen for.

        Returns:
            How the call ended.
        """
        ...

    def on_incoming_call(self, number_called: str, caller: str) -> None:
        """Handle an inbound call.

        The call is **rejected, never answered**, so the farmer is not charged
        and the missed call itself carries the information.

        Args:
            number_called: The toll-free number rung.
            caller: The farmer's number.
        """
        ...


@runtime_checkable
class SpeechAdapter(Protocol):
    """Turns a rendered script into speech."""

    def synthesise(self, text: str, *, lang: str, voice: str | None = None) -> SpeechResult:
        """Synthesise one script.

        Args:
            text: The rendered script.
            lang: Language code, for choosing a default voice.
            voice: Explicit neural voice name, overriding the language default.

        Returns:
            The audio location, or the text where synthesis was faked.
        """
        ...


@dataclass
class SimulatedTelephony:
    """In-memory telephony for tests, the demo and the browser call console.

    Records every call it was asked to place and every inbound missed call, so a
    test can assert on the whole day's traffic and the console can render it.

    This is the adapter ``make demo`` uses. ACS is behind a feature flag and is
    never required for a demonstration.
    """

    placed: list[PlacedCall] = field(default_factory=list)
    incoming: list[tuple[str, str, dt.datetime]] = field(default_factory=list)
    #: Outcome returned for the next call, so a test can simulate no answer.
    next_outcome: CallOutcome = CallOutcome.ANSWERED
    #: Digit the simulated farmer presses, if any.
    next_digit: str | None = None
    #: Clock, injected so the simulation is deterministic.
    now: dt.datetime | None = None

    def place_call(
        self,
        phone: str,
        script_text: str,
        *,
        audio_url: str | None = None,
        dtmf_options: tuple[str, ...] = (),
    ) -> CallResult:
        """Record a call rather than placing one.

        Args:
            phone: Destination in E.164 format.
            script_text: The words that would be spoken.
            audio_url: Pre-synthesised audio, recorded but not played.
            dtmf_options: Digits the call would listen for.

        Returns:
            The configured outcome, with the configured digit if the call was
            listening for one.
        """
        placed_at = self.now or dt.datetime(2026, 9, 3, 18, 0, tzinfo=dt.UTC)
        self.placed.append(
            PlacedCall(
                phone=phone,
                text=script_text,
                placed_at=placed_at,
                dtmf_options=dtmf_options,
                audio_url=audio_url,
            )
        )
        digit = self.next_digit if dtmf_options and self.next_digit in dtmf_options else None
        return CallResult(
            outcome=self.next_outcome,
            call_id=f"sim-{len(self.placed)}",
            digit=digit,
            duration_seconds=30.0 if self.next_outcome is CallOutcome.ANSWERED else 0.0,
        )

    def on_incoming_call(self, number_called: str, caller: str) -> None:
        """Record an inbound missed call. The call is never answered.

        Args:
            number_called: The toll-free number rung.
            caller: The farmer's number.
        """
        occurred = self.now or dt.datetime(2026, 9, 3, 18, 0, tzinfo=dt.UTC)
        self.incoming.append((number_called, caller, occurred))

    def last_script(self) -> str | None:
        """The text of the most recent call, for assertions and the console."""
        return self.placed[-1].text if self.placed else None


@dataclass
class FakeSpeech:
    """Returns the text unchanged, with no synthesis.

    Used by every unit test and by ``make demo`` when no Speech key is present,
    so the whole daily loop can be exercised without an Azure resource.
    """

    calls: int = 0

    def synthesise(self, text: str, *, lang: str, voice: str | None = None) -> SpeechResult:
        """Return the text as the result.

        Args:
            text: The rendered script.
            lang: Language code, recorded but unused.
            voice: Voice name, recorded but unused.

        Returns:
            The text, with no audio URL.
        """
        del lang
        self.calls += 1
        return SpeechResult(text=text, audio_url=None, voice=voice)
