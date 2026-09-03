"""Farmer-facing script tests.

The centrepiece is :class:`TestNoTechnicalUnitsLeak`. **That test is the direct
evidence for the accessibility claim in the report**, so it is deliberately more
thorough than the rest: it renders every language across a spread of schedule
states and asserts that nothing a farmer hears contains a technical unit, a
percentage, or a decimal number, in English or in the target language.

If the report says a non-literate farmer can act on this system, that claim rests
on this test passing.
"""

from __future__ import annotations

import datetime as dt
import re

import pytest

from irrigation_engine.params import load_script
from irrigation_engine.scheduler.models import (
    IST,
    Decision,
    EventKind,
    PowerWindow,
    ReasonCode,
    Schedule,
    WindowSource,
)
from irrigation_engine.scripts_render import (
    QUIET_END,
    QUIET_START,
    CallWindow,
    call_time_for,
    render_next_day_question,
    round_stop_time,
    should_call,
    speak_schedule,
    supported_languages,
)

TODAY = dt.date(2026, 9, 3)

# Words that must never reach a farmer, in every language with a master.
# Plan Section 5.5, rule 1.
FORBIDDEN_SUBSTRINGS = (
    # English technical vocabulary
    "millimet",
    "mm",
    "evapotranspiration",
    "depletion",
    "percent",
    "moisture",
    "et0",
    "etc",
    "kc",
    "coefficient",
    "deficit",
    "root zone",
    "litre",
    "liter",
    "cubic",
    "hectare",
    # Hindi
    "मिलीमीटर",
    "प्रतिशत",
    "वाष्पीकरण",
    "नमी",
    "लीटर",
    # Tamil
    "மில்லிமீட்டர்",
    "சதவீதம்",
    "ஆவியாதல்",
    "லிட்டர்",
)

# A decimal number. "45.5 minutes" is not something a farmer can act on, and its
# presence means a raw computed quantity has leaked into speech.
DECIMAL_PATTERN = re.compile(r"\d+\.\d+")

# A percent sign in any script the three masters could plausibly use. The
# fullwidth and Arabic-Indic forms are matched by codepoint so the linter does
# not read them as an ambiguous character in source.
PERCENT_SIGNS = ("%", chr(0x066A), chr(0xFF05))  # ASCII, Arabic-Indic, fullwidth
PERCENT_PATTERN = re.compile("|".join(re.escape(sign) for sign in PERCENT_SIGNS))


def window(
    *, start_hour: int = 22, hours: float = 8.0, reliability: float = 1.0, day: int = 3
) -> PowerWindow:
    start = dt.datetime(2026, 9, day, start_hour, 0, tzinfo=IST)
    return PowerWindow(
        start=start,
        end=start + dt.timedelta(hours=hours),
        source=WindowSource.DECLARED_ROTATION,
        reliability=reliability,
    )


def schedule(
    decision: Decision = Decision.IRRIGATE,
    reason: ReasonCode = ReasonCode.STRESS_IMMINENT,
    *,
    minutes: float = 409.4,
    with_window: bool = True,
    with_start_time: bool = True,
    carry_over: float = 0.0,
    **window_kwargs: float | int,
) -> Schedule:
    w = window(**window_kwargs) if with_window else None  # type: ignore[arg-type]
    return Schedule(
        field_id="f1",
        date=TODAY,
        decision=decision,
        reason_code=reason,
        minutes=minutes if decision is Decision.IRRIGATE else 0.0,
        window=w,
        start_time=(w.start if (w is not None and with_start_time) else None),
        delivered_mm=25.0,
        carry_over_mm=carry_over,
        required_mm=25.0 + carry_over,
    )


# Every combination a farmer could plausibly hear, used by the leak test.
ALL_STATES = [
    ("irrigate, clock time", schedule()),
    ("irrigate, capacity limit", schedule(reason=ReasonCode.CAPACITY_LIMIT)),
    ("irrigate, opportunistic", schedule(reason=ReasonCode.OPPORTUNISTIC_TOPUP)),
    ("irrigate, when power comes", schedule(with_start_time=False, reliability=0.3)),
    ("irrigate, truncated", schedule(minutes=240.0, carry_over=12.5)),
    ("irrigate, daytime window", schedule(start_hour=6, hours=8.0)),
    ("irrigate, short run", schedule(minutes=37.0)),
    ("irrigate, long run", schedule(minutes=705.0)),
    ("skip for rain", schedule(Decision.SKIP, ReasonCode.RAIN_EXPECTED, with_window=False)),
]

CROPS = {"en": "wheat", "hi": "गेहूँ", "ta": "கோதுமை"}
NAMES = {"en": "Ram", "hi": "राम काका", "ta": "ராம்"}


class TestNoTechnicalUnitsLeak:
    """The accessibility claim in the report rests on this class."""

    @pytest.mark.parametrize("lang", supported_languages())
    @pytest.mark.parametrize(("label", "state"), ALL_STATES, ids=[s[0] for s in ALL_STATES])
    def test_no_forbidden_word_reaches_the_farmer(
        self, lang: str, label: str, state: Schedule
    ) -> None:
        """No technical unit appears in any rendered script, in any language."""
        text = speak_schedule(
            state,
            lang=lang,
            crop=CROPS[lang],
            farmer_name=NAMES[lang],
            call_window=CallWindow(
                dt.datetime(2026, 9, 3, 18, 0, tzinfo=IST), is_previous_evening=False
            ),
        )
        lowered = text.lower()
        for forbidden in FORBIDDEN_SUBSTRINGS:
            assert forbidden not in lowered, (
                f"{lang} / {label}: forbidden term {forbidden!r} reached the farmer.\n{text}"
            )

    @pytest.mark.parametrize("lang", supported_languages())
    @pytest.mark.parametrize(("label", "state"), ALL_STATES, ids=[s[0] for s in ALL_STATES])
    def test_no_decimal_number_reaches_the_farmer(
        self, lang: str, label: str, state: Schedule
    ) -> None:
        """No decimal number appears. A farmer cannot act on "409.4"."""
        text = speak_schedule(state, lang=lang, crop=CROPS[lang], farmer_name=NAMES[lang])
        found = DECIMAL_PATTERN.search(text)
        assert found is None, f"{lang} / {label}: decimal {found.group()!r} reached the farmer"

    @pytest.mark.parametrize("lang", supported_languages())
    @pytest.mark.parametrize(("label", "state"), ALL_STATES, ids=[s[0] for s in ALL_STATES])
    def test_no_percent_sign_reaches_the_farmer(
        self, lang: str, label: str, state: Schedule
    ) -> None:
        """No percentage appears in any form."""
        text = speak_schedule(state, lang=lang, crop=CROPS[lang])
        assert PERCENT_PATTERN.search(text) is None

    @pytest.mark.parametrize("lang", supported_languages())
    def test_the_next_day_question_is_also_clean(self, lang: str) -> None:
        """The keypress fallback is farmer-facing too and obeys the same rule."""
        text = render_next_day_question(lang, farmer_name=NAMES[lang]).lower()
        for forbidden in FORBIDDEN_SUBSTRINGS:
            assert forbidden not in text
        assert DECIMAL_PATTERN.search(text) is None

    @pytest.mark.parametrize("lang", supported_languages())
    def test_the_master_file_itself_is_clean(self, lang: str) -> None:
        """No forbidden term hides in an unrendered branch of the master.

        The rendering tests only cover the branches they exercise. This checks
        every string in the file, so a case added later cannot smuggle one in.
        """
        master = load_script(lang)
        for key, value in _walk(master):
            if key in {"language", "name", "voice"}:
                continue
            lowered = value.lower()
            for forbidden in FORBIDDEN_SUBSTRINGS:
                assert forbidden not in lowered, f"{lang}: {key} contains {forbidden!r}"


def _walk(node: object, prefix: str = "") -> list[tuple[str, str]]:
    """Flatten a script master into (dotted key, string) pairs."""
    found: list[tuple[str, str]] = []
    if isinstance(node, dict):
        for key, value in node.items():
            found.extend(_walk(value, f"{prefix}.{key}" if prefix else str(key)))
    elif isinstance(node, str):
        found.append((prefix, node))
    return found


class TestClockTimesNotDurations:
    """The farmer is told when to start and when to stop."""

    def test_the_script_names_a_start_and_a_stop_time(self) -> None:
        """409 minutes is useless; "10:00" and "4:45" are actionable."""
        text = speak_schedule(schedule(), lang="en", crop="wheat")
        assert "Start the pump at 10:00" in text
        assert "stop it at 4:45" in text

    def test_a_raw_minute_count_never_appears_with_a_clock_time(self) -> None:
        """When a start time exists, the duration is not spoken at all."""
        text = speak_schedule(schedule(minutes=409.4), lang="en", crop="wheat")
        assert "409" not in text
        assert "minutes" not in text

    def test_when_power_is_unreliable_the_duration_is_given_in_hours(self) -> None:
        """With no clock time to promise, a duration is the only option left.

        It is still given in hours and minutes, never as a raw minute count.
        """
        text = speak_schedule(
            schedule(with_start_time=False, reliability=0.3, minutes=290.0),
            lang="en",
            crop="wheat",
        )
        assert "4 hours 50 minutes" in text
        assert "290" not in text

    def test_a_run_under_an_hour_is_spoken_in_minutes(self) -> None:
        text = speak_schedule(
            schedule(with_start_time=False, reliability=0.3, minutes=37.0),
            lang="en",
            crop="wheat",
        )
        assert "37 minutes" in text

    def test_exactly_one_hour_is_spoken_naturally(self) -> None:
        text = speak_schedule(
            schedule(with_start_time=False, reliability=0.3, minutes=60.0),
            lang="en",
            crop="wheat",
        )
        assert "one hour" in text


class TestStopTimeRounding:
    """Rounded to five minutes, always in the farmer's favour."""

    def test_the_stop_time_is_rounded_down_to_five_minutes(self) -> None:
        start = dt.datetime(2026, 9, 3, 22, 0, tzinfo=IST)
        assert round_stop_time(start, 409.4) == dt.datetime(2026, 9, 4, 4, 45, tzinfo=IST)

    @pytest.mark.parametrize("minutes", [1.0, 7.0, 34.9, 59.0, 120.5, 409.4, 478.0])
    def test_rounding_never_lengthens_the_run(self, minutes: float) -> None:
        """The pump must never be asked to run past what was computed.

        Rounding up could push the stop past the end of a truncated window,
        asking the farmer to draw power that has already gone.
        """
        start = dt.datetime(2026, 9, 3, 22, 0, tzinfo=IST)
        stop = round_stop_time(start, minutes)
        assert (stop - start).total_seconds() / 60.0 <= minutes

    @pytest.mark.parametrize("minutes", [10.0, 35.0, 120.0, 480.0])
    def test_an_exact_multiple_of_five_is_unchanged(self, minutes: float) -> None:
        start = dt.datetime(2026, 9, 3, 22, 0, tzinfo=IST)
        stop = round_stop_time(start, minutes)
        assert (stop - start).total_seconds() / 60.0 == minutes

    def test_the_stop_time_lands_on_a_five_minute_boundary(self) -> None:
        start = dt.datetime(2026, 9, 3, 22, 3, tzinfo=IST)
        stop = round_stop_time(start, 409.4)
        assert ((stop - start).total_seconds() / 60.0) % 5 == 0


class TestQuietHours:
    """Calls only between 07:00 and 21:00 IST."""

    def test_an_evening_window_is_called_the_same_day(self) -> None:
        """A 22:00 window less one hour of lead is 21:00, which is the boundary."""
        result = call_time_for(
            schedule(start_hour=22), now=dt.datetime(2026, 9, 3, 12, 0, tzinfo=IST)
        )
        assert QUIET_START <= result.at.time() < QUIET_END
        assert not result.is_previous_evening

    def test_a_dawn_window_is_called_the_previous_evening(self) -> None:
        """A 06:00 window would otherwise be called at 05:00, inside quiet hours."""
        result = call_time_for(
            schedule(start_hour=6, day=4), now=dt.datetime(2026, 9, 3, 12, 0, tzinfo=IST)
        )
        assert result.is_previous_evening
        assert result.at.date() == dt.date(2026, 9, 3)
        assert QUIET_START <= result.at.time() < QUIET_END

    def test_a_dawn_window_says_tomorrow_morning(self) -> None:
        """The script must not say "today" about a window that is tomorrow."""
        state = schedule(start_hour=6, day=4)
        result = call_time_for(state, now=dt.datetime(2026, 9, 3, 12, 0, tzinfo=IST))
        text = speak_schedule(state, lang="en", crop="wheat", call_window=result)
        assert "Tomorrow morning" in text
        assert "Today power" not in text

    def test_a_midday_window_is_called_within_quiet_hours(self) -> None:
        result = call_time_for(
            schedule(start_hour=13), now=dt.datetime(2026, 9, 3, 8, 0, tzinfo=IST)
        )
        assert QUIET_START <= result.at.time() < QUIET_END
        assert not result.is_previous_evening

    @pytest.mark.parametrize("start_hour", list(range(24)))
    def test_no_window_ever_produces_a_call_outside_quiet_hours(self, start_hour: int) -> None:
        """The boundary cases, exhaustively.

        Whatever hour the feeder opens, the farmer's phone never rings before
        07:00 or after 21:00.
        """
        state = schedule(start_hour=start_hour, day=4)
        result = call_time_for(state, now=dt.datetime(2026, 9, 3, 12, 0, tzinfo=IST))
        assert QUIET_START <= result.at.time() < QUIET_END, (
            f"window opening at {start_hour}:00 produced a call at {result.at}"
        )

    def test_a_skip_is_called_in_the_preferred_evening_slot(self) -> None:
        """With no window to precede, the evening slot answered best (R19)."""
        result = call_time_for(
            schedule(Decision.SKIP, ReasonCode.RAIN_EXPECTED, with_window=False),
            now=dt.datetime(2026, 9, 3, 9, 0, tzinfo=IST),
        )
        assert result.at.time() == dt.time(18, 0)

    def test_a_naive_now_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="timezone-aware"):
            call_time_for(schedule(), now=dt.datetime(2026, 9, 3, 12, 0))


class TestWhenACallHappens:
    """A call is placed only when something is being asked of the farmer."""

    def test_irrigate_produces_a_call(self) -> None:
        assert should_call(schedule())

    def test_skip_produces_a_call(self) -> None:
        """A skip asks him NOT to do something he would otherwise do."""
        assert should_call(schedule(Decision.SKIP, ReasonCode.RAIN_EXPECTED, with_window=False))

    def test_wait_produces_no_call(self) -> None:
        """Calling on a day when nothing is asked trains him to stop answering."""
        assert not should_call(
            schedule(Decision.WAIT, ReasonCode.NO_NEED, minutes=0.0, with_window=False)
        )

    def test_rendering_a_wait_raises(self) -> None:
        """The design decision is enforced, not merely documented."""
        with pytest.raises(ValueError, match="produces no call"):
            speak_schedule(
                schedule(Decision.WAIT, ReasonCode.NO_NEED, minutes=0.0, with_window=False),
                lang="en",
            )


class TestAcknowledgement:
    """The only confirmation the farmer gets that his missed call registered."""

    def test_a_water_given_report_is_acknowledged(self) -> None:
        """Decision 4 of the ACS feasibility note, carried on the next call."""
        text = speak_schedule(
            schedule(), lang="en", crop="wheat", acknowledge=EventKind.WATER_GIVEN
        )
        assert "Yesterday you told us you watered the field" in text

    def test_a_power_failure_report_is_acknowledged(self) -> None:
        text = speak_schedule(
            schedule(), lang="en", crop="wheat", acknowledge=EventKind.POWER_FAILED
        )
        assert "the power did not come" in text

    def test_no_acknowledgement_when_nothing_was_reported(self) -> None:
        text = speak_schedule(schedule(), lang="en", crop="wheat")
        assert "Yesterday" not in text

    @pytest.mark.parametrize("lang", supported_languages())
    def test_the_acknowledgement_comes_first(self, lang: str) -> None:
        """It opens the call, so he hears it before any instruction."""
        text = speak_schedule(
            schedule(),
            lang=lang,
            crop=CROPS[lang],
            farmer_name=NAMES[lang],
            acknowledge=EventKind.WATER_GIVEN,
        )
        master = load_script(lang)
        ack = str(master["acknowledge"]["water_given"])
        # Anchored on the reason clause, which is a complete literal sentence in
        # every master. The instruction template begins with a placeholder in
        # Hindi and Tamil, so it has no usable literal prefix to search for.
        reason = str(master["reason"]["stress_imminent"])
        assert ack in text
        assert reason in text
        assert text.index(ack) < text.index(reason)


class TestLanguages:
    """Three committed masters, and an honest error for anything else."""

    def test_all_three_masters_render(self) -> None:
        for lang in supported_languages():
            text = speak_schedule(schedule(), lang=lang, crop=CROPS[lang])
            assert text.strip()

    def test_the_masters_differ_from_each_other(self) -> None:
        """Each master renders differently, so none is silently falling back.

        A missing translation quietly serving English would be worse than an
        error, because nobody would notice it.
        """
        rendered = {
            lang: speak_schedule(schedule(), lang=lang, crop=CROPS[lang])
            for lang in supported_languages()
        }
        assert len(set(rendered.values())) == 3

    def test_an_unsupported_language_raises(self) -> None:
        with pytest.raises(KeyError, match="no script master"):
            speak_schedule(schedule(), lang="mr", crop="gehun")

    @pytest.mark.parametrize("lang", supported_languages())
    def test_every_reason_code_that_can_be_spoken_has_words(self, lang: str) -> None:
        """Every reason a call can carry has a plain-language line in every master.

        A missing reason would render a call with an instruction and no
        explanation, breaking plan Section 5.5 rule 3.
        """
        master = load_script(lang)
        for reason in (
            ReasonCode.STRESS_IMMINENT,
            ReasonCode.CAPACITY_LIMIT,
            ReasonCode.OPPORTUNISTIC_TOPUP,
            ReasonCode.RAIN_EXPECTED,
        ):
            assert reason.value in master["reason"], f"{lang} lacks a reason for {reason.value}"

    @pytest.mark.parametrize("lang", supported_languages())
    def test_every_master_declares_a_voice(self, lang: str) -> None:
        """The Speech adapter needs one, and it must be verified at build time."""
        assert load_script(lang)["voice"]


class TestReasonAlwaysSpoken:
    """Plan Section 5.5 rule 3: every recommendation carries a reason."""

    @pytest.mark.parametrize(
        "reason",
        [
            ReasonCode.STRESS_IMMINENT,
            ReasonCode.CAPACITY_LIMIT,
            ReasonCode.OPPORTUNISTIC_TOPUP,
        ],
    )
    def test_each_irrigate_reason_is_spoken(self, reason: ReasonCode) -> None:
        text = speak_schedule(schedule(reason=reason), lang="en", crop="wheat")
        master = load_script("en")
        assert str(master["reason"][reason.value]) in text

    def test_no_reason_asserts_a_day_the_window_may_contradict(self) -> None:
        """A reason must not say "today" when the window is tomorrow morning.

        The capacity-limit branch fires on the projection to the NEXT window, so
        the window it schedules into is often tomorrow. A reason line that said
        "water it today" would contradict the instruction two sentences later,
        which is exactly the kind of thing a farmer notices and a test does not,
        unless the test looks for it.
        """
        master = load_script("en")
        for reason_text in master["reason"].values():
            assert "today" not in str(reason_text).lower()

    def test_a_truncated_run_explains_itself(self) -> None:
        """The farmer is told why he is being asked for a short run."""
        text = speak_schedule(schedule(minutes=240.0, carry_over=12.5), lang="en", crop="wheat")
        assert "finish the rest next time" in text
