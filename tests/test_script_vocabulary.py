"""Every token a farmer hears must come from a known vocabulary.

Console output cannot distinguish three different failures that all look alike:

* **missing separators**, where two words concatenate into ``raatbijli``;
* **truncation**, where ``bijli`` renders as ``bij``;
* **terminal mangling**, where the bytes are correct and only the display is not.

These tests separate them at the data level, where the display cannot interfere.
The vocabulary is derived from the master itself, so it needs no maintenance: a
token that is not in it is either a concatenation of two vocabulary words, a
fragment of one, or a value the renderer invented.

The prefix test is what catches truncation specifically. ``bij`` is not in the
vocabulary AND is a strict prefix of ``bijli``, which distinguishes a truncated
word from a merely unknown one.
"""

from __future__ import annotations

import datetime as dt
import re
from typing import Any

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
    CallWindow,
    render_next_day_question,
    speak_schedule,
    speak_time,
    supported_languages,
)

# Values the renderer injects that are not in the master.
CROPS = {"en": "wheat", "hi": "गेहूँ", "ta": "கோதுமை"}
NAMES = {"en": "Ram", "hi": "राम", "ta": "முருகன்"}

PLACEHOLDER = re.compile(r"\{[a-z_]+\}")

# Punctuation is stripped from both the vocabulary and the rendered output before
# comparison, because a word and its trailing punctuation come from different
# templates: the greeting supplies the comma after a name, and the sentence form
# supplies the full stop after a part of day. Comparing them attached would fail
# on punctuation placement rather than on the wording, which is what is being
# checked here.
#
# U+0964 is the Devanagari danda, the Hindi full stop.
PUNCTUATION = ",.;:!?'\"()।॥"


def tokens_of(text: str) -> list[str]:
    """Split into words, with punctuation stripped from either end."""
    return [
        stripped for stripped in (token.strip(PUNCTUATION) for token in text.split()) if stripped
    ]


def _strings(node: Any, skip_keys: frozenset[str] = frozenset()) -> list[str]:
    """Every string value in a master, skipping metadata keys."""
    found: list[str] = []
    if isinstance(node, dict):
        for key, value in node.items():
            if key in skip_keys:
                continue
            found.extend(_strings(value, skip_keys))
    elif isinstance(node, str):
        found.append(node)
    return found


def vocabulary(lang: str) -> set[str]:
    """Every token the master can legitimately produce.

    Built from the master's own strings with placeholders stripped, plus the
    injected crop and farmer names. Deriving it rather than listing it means the
    test cannot drift out of date when a line is reworded.
    """
    master = load_script(lang)
    tokens: set[str] = set()
    for value in _strings(master, skip_keys=frozenset({"language", "name", "voice"})):
        tokens.update(tokens_of(PLACEHOLDER.sub(" ", value)))

    for injected in (CROPS[lang], NAMES[lang]):
        tokens.update(tokens_of(injected))
    return tokens


def window(*, start_hour: int = 22, hours: float = 8.0, reliability: float = 1.0) -> PowerWindow:
    start = dt.datetime(2026, 9, 4, start_hour, 0, tzinfo=IST)
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
    **kwargs: float,
) -> Schedule:
    w = window(**kwargs) if with_window else None  # type: ignore[arg-type]
    return Schedule(
        field_id="f1",
        date=dt.date(2026, 9, 4),
        decision=decision,
        reason_code=reason,
        minutes=minutes if decision is Decision.IRRIGATE else 0.0,
        window=w,
        start_time=(w.start if (w is not None and with_start_time) else None),
        delivered_mm=25.0,
        carry_over_mm=carry_over,
        required_mm=25.0 + carry_over,
    )


ALL_STATES = [
    ("night, clock time", schedule()),
    ("capacity limit", schedule(reason=ReasonCode.CAPACITY_LIMIT)),
    ("opportunistic", schedule(reason=ReasonCode.OPPORTUNISTIC_TOPUP)),
    ("when power comes", schedule(with_start_time=False, reliability=0.3, minutes=290.0)),
    ("truncated", schedule(minutes=240.0, carry_over=12.5, hours=4.0)),
    ("morning window", schedule(start_hour=7)),
    ("short run", schedule(with_start_time=False, reliability=0.3, minutes=37.0)),
    ("skip for rain", schedule(Decision.SKIP, ReasonCode.RAIN_EXPECTED, with_window=False)),
]

CALL_WINDOW = CallWindow(dt.datetime(2026, 9, 4, 18, 0, tzinfo=IST), is_previous_evening=False)


def render(lang: str, state: Schedule, acknowledge: EventKind | None = None) -> str:
    return speak_schedule(
        state,
        lang=lang,
        crop=CROPS[lang],
        farmer_name=NAMES[lang],
        acknowledge=acknowledge,
        call_window=CALL_WINDOW,
    )


class TestNoWordCollisionsOrTruncation:
    """The tests that settle whether the wording is intact at the data level."""

    @pytest.mark.parametrize("lang", supported_languages())
    @pytest.mark.parametrize(("label", "state"), ALL_STATES, ids=[s[0] for s in ALL_STATES])
    def test_every_rendered_token_is_in_the_vocabulary(
        self, lang: str, label: str, state: Schedule
    ) -> None:
        """A token outside the vocabulary is a collision, a fragment or an invention.

        This is the test that would have caught two templates concatenating
        without a separator, which console output could not distinguish from a
        terminal rendering fault.
        """
        known = vocabulary(lang)
        unknown = [token for token in tokens_of(render(lang, state)) if token not in known]
        assert not unknown, (
            f"{lang} / {label}: tokens not in the master vocabulary: {unknown}\n"
            f"{render(lang, state)}"
        )

    @pytest.mark.parametrize("lang", supported_languages())
    @pytest.mark.parametrize(("label", "state"), ALL_STATES, ids=[s[0] for s in ALL_STATES])
    def test_no_rendered_token_is_a_truncation_of_a_longer_word(
        self, lang: str, label: str, state: Schedule
    ) -> None:
        """No token is a strict prefix of a vocabulary word it is not equal to.

        This is what distinguishes truncation from a merely unknown token. If
        ``bijli`` were cut to ``bij``, the previous test would report an unknown
        token; this one names it as a truncation of a word the master contains.
        """
        known = vocabulary(lang)
        truncations = []
        for token in tokens_of(render(lang, state)):
            if token in known:
                continue
            longer = [word for word in known if word.startswith(token) and word != token]
            if longer:
                truncations.append((token, longer[:3]))
        assert not truncations, f"{lang} / {label}: truncated tokens {truncations}"

    @pytest.mark.parametrize("lang", supported_languages())
    def test_the_acknowledgement_branch_is_covered_too(self, lang: str) -> None:
        """The opening clause is rendered on a different path and needs checking."""
        known = vocabulary(lang)
        for kind in (EventKind.WATER_GIVEN, EventKind.POWER_FAILED):
            text = render(lang, schedule(), acknowledge=kind)
            unknown = [token for token in tokens_of(text) if token not in known]
            assert not unknown, f"{lang} / {kind.value}: {unknown}"

    @pytest.mark.parametrize("lang", supported_languages())
    def test_the_next_day_question_is_covered_too(self, lang: str) -> None:
        known = vocabulary(lang)
        text = render_next_day_question(lang, farmer_name=NAMES[lang])
        unknown = [token for token in tokens_of(text) if token not in known]
        assert not unknown, f"{lang}: {unknown}"

    @pytest.mark.parametrize("lang", supported_languages())
    @pytest.mark.parametrize("hour", list(range(24)))
    @pytest.mark.parametrize("minute", [0, 15, 30, 45])
    def test_every_spoken_time_uses_only_vocabulary_words(
        self, lang: str, hour: int, minute: int
    ) -> None:
        """Exhaustive over every hour and quarter, in all three languages.

        A time expression that assembled a word incorrectly would otherwise
        appear only when a particular farmer's window fell on that minute.
        """
        known = vocabulary(lang)
        spoken = speak_time(dt.datetime(2026, 9, 4, hour, minute, tzinfo=IST), lang)
        unknown = [token for token in tokens_of(spoken) if token not in known]
        assert not unknown, f"{lang} {hour:02d}:{minute:02d} -> {spoken!r}: {unknown}"


class TestSeparatorsArePresent:
    """Word boundaries survive template composition."""

    @pytest.mark.parametrize("lang", supported_languages())
    @pytest.mark.parametrize(("label", "state"), ALL_STATES, ids=[s[0] for s in ALL_STATES])
    def test_sentences_are_separated_by_whitespace(
        self, lang: str, label: str, state: Schedule
    ) -> None:
        """Clauses are joined with a space, so no sentence runs into the next.

        The renderer joins parts with a single space. If that ever became an
        empty join, the previous tests would catch it as a collision; this one
        states the requirement directly.
        """
        text = render(lang, state)
        assert "  " not in text, f"{lang} / {label}: double space in {text!r}"
        assert not text.startswith(" ")
        assert not text.endswith(" ")

    @pytest.mark.parametrize("lang", supported_languages())
    def test_the_rendered_script_has_several_tokens(self, lang: str) -> None:
        """A fully collapsed script would be one enormous token."""
        assert len(tokens_of(render(lang, schedule()))) >= 10


class TestVocabularyItself:
    """The vocabulary derivation, which the tests above depend on."""

    @pytest.mark.parametrize("lang", supported_languages())
    def test_the_vocabulary_is_not_empty(self, lang: str) -> None:
        assert len(vocabulary(lang)) > 30

    @pytest.mark.parametrize("lang", supported_languages())
    def test_placeholders_do_not_enter_the_vocabulary(self, lang: str) -> None:
        """A stray ``{start}`` in output would otherwise pass unnoticed."""
        assert not [token for token in vocabulary(lang) if "{" in token or "}" in token]

    @pytest.mark.parametrize("lang", supported_languages())
    def test_a_deliberately_concatenated_token_is_caught(self, lang: str) -> None:
        """The test suite's own guard: prove the check can fail.

        Two vocabulary words joined without a separator must not themselves be
        in the vocabulary, or the collision test would be vacuous.
        """
        known = sorted(vocabulary(lang))
        fabricated = known[0] + known[1]
        assert fabricated not in known
