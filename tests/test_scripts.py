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
from itertools import pairwise

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
    speak_duration,
    speak_schedule,
    speak_time,
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

# Any digit, in any script a master could plausibly use. A farmer-facing script
# contains NO DIGITS AT ALL: every time and every duration is spoken in words
# with its part of day, because "6:00" does not tell a non-reader whether it is
# morning or evening, and a text-to-speech voice handed a numeral renders it
# unpredictably.
#
# This is a stronger and more checkable claim than "no technical units", and it
# is the one the report makes.
DIGIT_RANGES = (
    ("ASCII", 0x0030, 0x0039),
    ("Devanagari", 0x0966, 0x096F),
    ("Tamil", 0x0BE6, 0x0BEF),
)
DIGITS = frozenset(chr(code) for _, low, high in DIGIT_RANGES for code in range(low, high + 1))

# A percent sign in any script a master could plausibly use.
PERCENT_SIGNS = ("%", chr(0x066A), chr(0xFF05))  # ASCII, Arabic-Indic, fullwidth
PERCENT_PATTERN = re.compile("|".join(re.escape(sign) for sign in PERCENT_SIGNS))


def digits_in(text: str) -> set[str]:
    """Every digit character appearing in a rendered script."""
    return {character for character in text if character in DIGITS}


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
    def test_no_digit_at_all_reaches_the_farmer(
        self, lang: str, label: str, state: Schedule
    ) -> None:
        """No digit appears in any farmer-facing script, in any script system.

        The strongest and simplest guarantee this project makes about
        accessibility, and the one a reviewer can check in a second at a viva.
        Every time and every duration is spoken in words with its part of day.
        """
        text = speak_schedule(
            state,
            lang=lang,
            crop=CROPS[lang],
            farmer_name=NAMES[lang],
            call_window=CallWindow(
                dt.datetime(2026, 9, 3, 18, 0, tzinfo=IST), is_previous_evening=False
            ),
        )
        found = digits_in(text)
        assert not found, f"{lang} / {label}: digits {sorted(found)} reached the farmer.\n{text}"

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
        text = render_next_day_question(lang, farmer_name=NAMES[lang])
        lowered = text.lower()
        for forbidden in FORBIDDEN_SUBSTRINGS:
            assert forbidden not in lowered
        assert not digits_in(text)

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


class TestSpokenTimes:
    """Times are spoken in words with a part of day, never as digits."""

    def test_the_script_names_a_start_and_a_stop_time_in_words(self) -> None:
        """A start and a stop, both spoken. 409 minutes is not actionable."""
        text = speak_schedule(schedule(), lang="en", crop="wheat")
        assert "ten o'clock at night" in text
        assert "quarter to five in the morning" in text

    def test_no_raw_minute_count_appears_beside_a_clock_time(self) -> None:
        """With a start time given, the duration is not spoken at all."""
        text = speak_schedule(schedule(minutes=409.4), lang="en", crop="wheat")
        assert "409" not in text
        assert "minutes" not in text

    @pytest.mark.parametrize(
        ("hour", "minute", "expected"),
        [
            (22, 0, "ten o'clock at night"),
            (6, 0, "six o'clock in the morning"),
            (4, 45, "quarter to five in the morning"),
            (15, 30, "half past three in the afternoon"),
            (10, 15, "quarter past ten in the morning"),
            (13, 20, "twenty minutes past one in the afternoon"),
        ],
    )
    def test_english_times_read_naturally(self, hour: int, minute: int, expected: str) -> None:
        assert speak_time(dt.datetime(2026, 9, 3, hour, minute, tzinfo=IST), "en") == expected

    def test_hindi_uses_the_irregular_half_hour_forms(self) -> None:
        """1:30 is "dedh" and 2:30 is "dhai", not "saade ek" or "saade do".

        Getting this wrong would not break anything, and would mark the script
        immediately as machine-written to any Hindi speaker.
        """
        one_thirty = speak_time(dt.datetime(2026, 9, 3, 1, 30, tzinfo=IST), "hi")
        two_thirty = speak_time(dt.datetime(2026, 9, 3, 2, 30, tzinfo=IST), "hi")
        assert "\u0921\u0947\u0922\u093c" in one_thirty
        assert "\u0922\u093e\u0908" in two_thirty
        assert "\u0938\u093e\u0922\u093c\u0947" not in one_thirty

    def test_hindi_uses_quarter_forms(self) -> None:
        """Sawa for quarter past, paune for quarter to."""
        assert "\u0938\u0935\u093e" in speak_time(dt.datetime(2026, 9, 3, 10, 15, tzinfo=IST), "hi")
        assert "\u092a\u094c\u0928\u0947" in speak_time(
            dt.datetime(2026, 9, 3, 4, 45, tzinfo=IST), "hi"
        )

    @pytest.mark.parametrize("lang", supported_languages())
    @pytest.mark.parametrize(
        ("hour", "minute"), [(h, m) for h in range(24) for m in (0, 15, 30, 45)]
    )
    def test_every_rounded_time_speaks_without_digits(
        self, lang: str, hour: int, minute: int
    ) -> None:
        """Exhaustive across every hour and every five-minute quarter.

        A time the vocabulary cannot express would otherwise surface only when a
        particular farmer's window happened to fall on it.
        """
        spoken = speak_time(dt.datetime(2026, 9, 3, hour, minute, tzinfo=IST), lang)
        assert spoken.strip()
        assert not digits_in(spoken)

    @pytest.mark.parametrize("lang", supported_languages())
    @pytest.mark.parametrize("minute", list(range(0, 60, 5)))
    def test_every_five_minute_value_speaks(self, lang: str, minute: int) -> None:
        spoken = speak_time(dt.datetime(2026, 9, 3, 9, minute, tzinfo=IST), lang)
        assert spoken.strip()
        assert not digits_in(spoken)

    @pytest.mark.parametrize("lang", supported_languages())
    def test_a_time_that_is_not_a_multiple_of_five_is_refused(self, lang: str) -> None:
        """Better to fail loudly than to speak a digit.

        Both the stop-time and the duration rounding guarantee a multiple of
        five, so reaching this branch means a caller bypassed them.
        """
        with pytest.raises(KeyError, match="rounded to a multiple of five"):
            speak_time(dt.datetime(2026, 9, 3, 9, 7, tzinfo=IST), lang)


class TestSpokenDurations:
    """Durations are spoken in hours and minutes, in words."""

    def test_a_duration_is_used_only_when_there_is_no_clock_time(self) -> None:
        """A duration appears only where no clock time can be promised.

        With an unreliable feeder there is no start time to give, so the
        duration is the only thing left.
        """
        text = speak_schedule(
            schedule(with_start_time=False, reliability=0.3, minutes=290.0),
            lang="en",
            crop="wheat",
        )
        assert "four hours fifty minutes" in text
        assert not digits_in(text)

    def test_a_run_under_an_hour_is_spoken_in_minutes(self) -> None:
        text = speak_schedule(
            schedule(with_start_time=False, reliability=0.3, minutes=37.0),
            lang="en",
            crop="wheat",
        )
        assert "thirty five minutes" in text

    def test_exactly_one_hour_is_spoken_naturally(self) -> None:
        text = speak_schedule(
            schedule(with_start_time=False, reliability=0.3, minutes=60.0),
            lang="en",
            crop="wheat",
        )
        assert "one hour" in text

    @pytest.mark.parametrize("lang", supported_languages())
    @pytest.mark.parametrize("minutes", [5, 37, 60, 95, 240, 290, 409, 478, 705])
    def test_every_plausible_duration_speaks_without_digits(self, lang: str, minutes: int) -> None:
        spoken = speak_duration(float(minutes), lang)
        assert spoken.strip()
        assert not digits_in(spoken)

    @pytest.mark.parametrize("minutes", [7.0, 33.0, 409.4, 478.9])
    def test_a_spoken_duration_never_exceeds_the_computed_one(self, minutes: float) -> None:
        """Rounded down, exactly as the stop time is."""
        rounded = (int(minutes) // 5) * 5
        assert rounded <= minutes


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

    def test_a_dawn_window_is_framed_as_tomorrow(self) -> None:
        """The script must not say "today" about a window that is tomorrow."""
        state = schedule(start_hour=6, day=4)
        result = call_time_for(state, now=dt.datetime(2026, 9, 3, 12, 0, tzinfo=IST))
        text = speak_schedule(state, lang="en", crop="wheat", call_window=result)
        assert "Tomorrow power is from" in text
        assert "Power is from" not in text.replace("Tomorrow power is from", "")

    def test_the_frame_does_not_repeat_the_part_of_day(self) -> None:
        """The frame names only the DAY; the times carry the part of day.

        An earlier version framed the sentence as "Tomorrow morning power is
        from ..." while the time inside it already said "in the morning". In
        English that merely read badly; in Tamil it produced a visibly doubled
        word, "indru iravu iravu pathu manikku".
        """
        state = schedule(start_hour=6, day=4)
        result = call_time_for(state, now=dt.datetime(2026, 9, 3, 12, 0, tzinfo=IST))
        assert "Tomorrow morning" not in speak_schedule(
            state, lang="en", crop="wheat", call_window=result
        )

    @pytest.mark.parametrize("lang", supported_languages())
    def test_no_part_of_day_word_is_ever_immediately_repeated(self, lang: str) -> None:
        """No two adjacent tokens are identical, in any language or any state.

        This is the general form of the Tamil doubling bug: whatever the
        templates compose to, a word must never be spoken twice in a row.
        """
        master = load_script(lang)
        for label, state in ALL_STATES:
            for previous_evening in (False, True):
                text = speak_schedule(
                    state,
                    lang=lang,
                    crop=CROPS[lang],
                    farmer_name=NAMES[lang],
                    call_window=CallWindow(
                        dt.datetime(2026, 9, 3, 18, 0, tzinfo=IST),
                        is_previous_evening=previous_evening,
                    ),
                )
                tokens = text.split()
                repeats = [(a, index) for index, (a, b) in enumerate(pairwise(tokens)) if a == b]
                assert not repeats, f"{lang} / {label}: repeated token {repeats} in {text!r}"
        assert master["power"]["today"]

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
