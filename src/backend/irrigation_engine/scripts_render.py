"""Render a schedule into the words a farmer actually hears.

**The farmer is told when to start and when to stop, never a raw duration.**
Telling him to run the pump for 409 minutes is useless: he cannot convert it, and
he will be asleep. The script gives a start time and a stop time; the duration
follows second, in hours and minutes, as reassurance rather than instruction.

Two rounding rules, both in the farmer's favour:

* the stop time is rounded to the nearest five minutes, because no one watches a
  clock to the minute at four in the morning;
* rounding always favours a **shorter** run, so a truncated window is never
  overrun and the pump is never asked to draw power that has stopped.

**Quiet hours.** Calls are placed only between 07:00 and 21:00 IST. A window
opening at 06:00 therefore gets its call the previous evening, and the script
says "tomorrow morning" rather than "today". Published evaluations of voice
advisory in India found evening calls were answered best (plan reference R19), so
where the timing is free the 18:00 to 20:00 slot is preferred.

**A call is placed only when there is something to act on.** IRRIGATE and SKIP
produce a call; WAIT does not. This is a stated design decision, not an accident:
a farmer who is called on days when nothing is being asked of him stops listening
on the days when something is.

Farmer-facing strings live in ``scripts/{hi,en,ta}.yaml``. Nothing in this module
may introduce a number or a unit that is not already in those files.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

from irrigation_engine.params import load_params, load_script
from irrigation_engine.scheduler.models import IST, Decision, EventKind, ReasonCode, Schedule

__all__ = [
    "CallWindow",
    "call_time_for",
    "render_next_day_question",
    "round_stop_time",
    "should_call",
    "speak_schedule",
    "supported_languages",
]

# Quiet hours, IST. Outside these a call is not placed.
QUIET_START = dt.time(7, 0)
QUIET_END = dt.time(21, 0)

# Preferred slot when the timing is free. Plan reference R19: evening calls were
# answered best in published Indian IVR evaluations.
PREFERRED_START = dt.time(18, 0)
PREFERRED_END = dt.time(20, 0)

STOP_ROUNDING_MINUTES = 5


def supported_languages() -> tuple[str, ...]:
    """Languages with a committed script master."""
    return ("en", "hi", "ta")


def _script(lang: str) -> dict[str, Any]:
    """Load one script master, or raise naming the alternatives."""
    try:
        return load_script(lang)
    except FileNotFoundError:
        msg = f"no script master for {lang!r}; available: {', '.join(supported_languages())}"
        raise KeyError(msg) from None


class CallWindow:
    """When the call for a schedule should be placed, and how it refers to time.

    Attributes:
        at: The instant to place the call, inside quiet hours.
        is_previous_evening: Whether the call happens the evening before the
            power window, which changes "today" to "tomorrow morning" in the
            script.
    """

    def __init__(self, at: dt.datetime, *, is_previous_evening: bool) -> None:
        """Store the call timing."""
        self.at = at
        self.is_previous_evening = is_previous_evening

    def __repr__(self) -> str:
        """Readable form for the call console and test failures."""
        return f"CallWindow(at={self.at.isoformat()}, previous_evening={self.is_previous_evening})"

    def __eq__(self, other: object) -> bool:
        """Two call windows are equal when both fields match."""
        if not isinstance(other, CallWindow):
            return NotImplemented
        return self.at == other.at and self.is_previous_evening == other.is_previous_evening


def should_call(schedule: Schedule) -> bool:
    """Whether this schedule warrants placing a call.

    IRRIGATE and SKIP produce a call, because both ask the farmer to do or not do
    something today. WAIT does not: nothing is being asked, and calling anyway
    trains him to stop answering.

    Args:
        schedule: The day's decision.

    Returns:
        True when a call should be placed.
    """
    return schedule.decision in (Decision.IRRIGATE, Decision.SKIP)


def call_time_for(schedule: Schedule, *, now: dt.datetime) -> CallWindow:
    """Choose when to place the call, respecting quiet hours.

    The call is placed a configured lead time before the window opens. If that
    lands outside 07:00 to 21:00 IST, it moves to the preferred evening slot on
    the previous day, and the script then refers to the window as tomorrow
    morning rather than today.

    Args:
        schedule: The day's decision, supplying the window if there is one.
        now: Current instant, timezone-aware. An argument rather than a clock
            read, so the choice is reproducible and testable.

    Returns:
        The instant to call, and whether it falls the previous evening.

    Raises:
        ValueError: If ``now`` is naive.
    """
    if now.tzinfo is None:
        msg = "now must be timezone-aware"
        raise ValueError(msg)

    lead = int(load_params("scheduling")["horizon"]["call_lead_minutes"])
    local_now = now.astimezone(IST)

    if schedule.window is None:
        # A SKIP has no window. Call in the preferred evening slot today if it
        # has not passed, otherwise as soon as quiet hours allow.
        return CallWindow(_preferred_slot(local_now), is_previous_evening=False)

    ideal = schedule.window.start.astimezone(IST) - dt.timedelta(minutes=lead)
    if _inside_quiet_hours(ideal.time()):
        return CallWindow(ideal, is_previous_evening=False)

    # Outside quiet hours: fall back to the evening before the window opens.
    evening = dt.datetime.combine(
        schedule.window.start.astimezone(IST).date() - dt.timedelta(days=1),
        PREFERRED_START,
        tzinfo=IST,
    )
    if ideal.time() >= QUIET_END:
        # A late-evening window: call the same day, in the preferred slot.
        evening = dt.datetime.combine(ideal.date(), PREFERRED_START, tzinfo=IST)
        return CallWindow(evening, is_previous_evening=False)
    return CallWindow(evening, is_previous_evening=True)


def _inside_quiet_hours(when: dt.time) -> bool:
    """Whether a clock time falls inside the permitted calling hours."""
    return QUIET_START <= when < QUIET_END


def _preferred_slot(local_now: dt.datetime) -> dt.datetime:
    """The next preferred evening slot at or after ``local_now``."""
    today = dt.datetime.combine(local_now.date(), PREFERRED_START, tzinfo=IST)
    if local_now <= today:
        return today
    if _inside_quiet_hours(local_now.time()):
        return local_now
    return dt.datetime.combine(local_now.date() + dt.timedelta(days=1), PREFERRED_START, tzinfo=IST)


def round_stop_time(start: dt.datetime, minutes: float) -> dt.datetime:
    """Compute a stop time rounded to five minutes, never rounding up.

    Rounding down means the pump always stops at or before the moment the
    calculation called for. Rounding up could push the stop past the end of a
    truncated window, asking the farmer to run a pump on power that has gone.

    Args:
        start: When the pump starts.
        minutes: Required running time, minutes.

    Returns:
        The stop time, floored to a five-minute boundary of running time.
    """
    rounded = (int(minutes) // STOP_ROUNDING_MINUTES) * STOP_ROUNDING_MINUTES
    return start + dt.timedelta(minutes=rounded)


def _format_clock(when: dt.datetime, lang: str) -> str:
    """Render a clock time for speech.

    Twelve-hour form without a leading zero, since that is how the time is said
    aloud in all three languages. The period of day is carried by the surrounding
    sentence ("tonight", "tomorrow morning") rather than by an AM or PM marker,
    which a non-literate listener would not parse.
    """
    del lang  # All three masters currently share the numeric form.
    hour = when.hour % 12 or 12
    return f"{hour}:{when.minute:02d}"


def _format_duration(minutes: float, script: dict[str, Any]) -> str:
    """Render a running time in hours and minutes, never as raw minutes.

    "Four hours fifty minutes" is something a farmer can hold in his head. "Two
    hundred and ninety minutes" is not.
    """
    total = int(minutes)
    hours, remainder = divmod(total, 60)
    forms = script["duration"]

    if hours == 0:
        return str(forms["minutes_only"]).format(minutes=remainder)
    if hours == 1 and remainder == 0:
        return str(forms["one_hour"])
    if remainder == 0:
        return str(forms["hours_only"]).format(hours=hours)
    return str(forms["hours_and_minutes"]).format(hours=hours, minutes=remainder)


def speak_schedule(
    schedule: Schedule,
    *,
    lang: str = "hi",
    crop: str = "",
    farmer_name: str | None = None,
    acknowledge: EventKind | None = None,
    call_window: CallWindow | None = None,
    include_repeat_prompt: bool = True,
) -> str:
    """Render the words the farmer hears for one day's decision.

    Args:
        schedule: The decision to speak.
        lang: Script master to use, one of ``en``, ``hi``, ``ta``.
        crop: Crop name as the farmer would say it, already in his language.
        farmer_name: Name to greet him by. Omitted greeting if absent.
        acknowledge: An event reported since the last call, acknowledged in the
            opening clause. This is the only confirmation the farmer ever
            receives that his missed call registered, and it lets him correct us
            if we logged the wrong thing. See
            ``docs/ACS_MISSED_CALL_FEASIBILITY.md`` Decision 4.
        call_window: When the call is being placed, which decides whether the
            window is referred to as tonight, today or tomorrow morning.
        include_repeat_prompt: Whether to close with the press-one-to-repeat
            prompt.

    Returns:
        The full spoken script, one sentence per instruction.

    Raises:
        KeyError: If no script master exists for ``lang``.
        ValueError: If the schedule is a WAIT, which produces no call.
    """
    if not should_call(schedule):
        msg = (
            f"a {schedule.decision.value} decision produces no call; "
            f"check should_call() before rendering"
        )
        raise ValueError(msg)

    script = _script(lang)
    parts: list[str] = []

    if farmer_name:
        parts.append(str(script["greeting"]).format(name=farmer_name))
    else:
        parts.append(str(script["greeting_no_name"]))

    if acknowledge is EventKind.WATER_GIVEN:
        parts.append(str(script["acknowledge"]["water_given"]))
    elif acknowledge is EventKind.POWER_FAILED:
        parts.append(str(script["acknowledge"]["power_failed"]))

    if schedule.decision is Decision.SKIP:
        parts.append(str(script["skip"]["opening"]))
        parts.append(str(script["skip"]["rain"]))
        parts.append(str(script["skip"]["followup"]))
    else:
        parts.extend(_irrigation_clauses(schedule, script, lang, crop, call_window))

    if include_repeat_prompt:
        parts.append(str(script["repeat"]))

    return " ".join(part for part in parts if part)


def _irrigation_clauses(
    schedule: Schedule,
    script: dict[str, Any],
    lang: str,
    crop: str,
    call_window: CallWindow | None,
) -> list[str]:
    """Build the power, need, instruction and reason clauses for an IRRIGATE."""
    parts: list[str] = []
    window = schedule.window

    if window is not None:
        start_text = _format_clock(window.start, lang)
        end_text = _format_clock(window.end, lang)
        if schedule.start_time is None:
            parts.append(str(script["power"]["unreliable"]))
        elif call_window is not None and call_window.is_previous_evening:
            parts.append(
                str(script["power"]["tomorrow_morning"]).format(start=start_text, end=end_text)
            )
        elif window.crosses_midnight or window.start.hour >= 18:
            parts.append(str(script["power"]["tonight"]).format(start=start_text, end=end_text))
        else:
            parts.append(str(script["power"]["today"]).format(start=start_text, end=end_text))

    if crop:
        parts.append(str(script["crop_needs_water"]).format(crop=crop))

    if schedule.start_time is not None:
        stop = round_stop_time(schedule.start_time, schedule.minutes)
        parts.append(
            str(script["instruction"]["with_time"]).format(
                start=_format_clock(schedule.start_time, lang),
                stop=_format_clock(stop, lang),
            )
        )
    else:
        parts.append(
            str(script["instruction"]["when_power_comes"]).format(
                duration=_format_duration(schedule.minutes, script)
            )
        )

    reason = script["reason"].get(schedule.reason_code.value)
    if reason:
        parts.append(str(reason))
    if schedule.was_truncated:
        parts.append(str(script["reason"]["carry_over"]))

    return parts


def render_next_day_question(lang: str = "hi", farmer_name: str | None = None) -> str:
    """Render the follow-up asked when no missed call arrived.

    Keypress is the fallback and never the primary channel: published
    evaluations of IVR with Indian farmers found very low response to keypress
    prompts (plan reference R18). It is asked only when the missed call, which
    costs the farmer nothing, did not arrive.

    Args:
        lang: Script master to use.
        farmer_name: Name to greet him by.

    Returns:
        The spoken question.
    """
    script = _script(lang)
    parts: list[str] = []
    if farmer_name:
        parts.append(str(script["greeting"]).format(name=farmer_name))
    else:
        parts.append(str(script["greeting_no_name"]))
    parts.append(str(script["question"]["did_you_water"]))
    return " ".join(parts)


def reason_is_speakable(reason: ReasonCode, lang: str = "hi") -> bool:
    """Whether a reason code has spoken words in a script master.

    WAIT reasons deliberately have none, because a WAIT produces no call.

    Args:
        reason: The reason code.
        lang: Script master to check.

    Returns:
        True when the master carries words for that reason.
    """
    return reason.value in _script(lang)["reason"]
