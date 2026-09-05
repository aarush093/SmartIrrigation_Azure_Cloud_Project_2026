"""Write every rendered script to a UTF-8 file for native-speaker review.

Console output cannot settle whether a Devanagari or Tamil string is correct: a
terminal codepage, a font without the right conjuncts, or a copy-paste through a
tool that mangles combining marks will all corrupt the display while the bytes
stay intact. The only reliable way to review the wording is to write it to a file
and open it in something that renders Indic scripts properly.

This module produces ``results/script_samples.txt``: every schedule state, in
every language, with the operator-facing state printed alongside so a reviewer
can see what the farmer was told and why.

**Neither the author of this code nor its reviewer can sign off the Hindi or
Tamil wording.** Until a native speaker reads this file, every non-English master
stays marked ``TODO [VERIFY native speaker]`` and the report says so.

Run with ``make script-samples``.
"""

from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

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
    supported_languages,
)

__all__ = ["build_samples", "main", "write_samples"]

# Crop and farmer names as each language would actually say them.
CROPS = {"en": "wheat", "hi": "गेहूँ", "ta": "கோதுமை"}
NAMES = {"en": "Ram", "hi": "राम", "ta": "முருகன்"}

TODAY = dt.date(2026, 9, 4)


def _window(
    *, start_hour: int = 22, hours: float = 8.0, reliability: float = 1.0, day: int = 4
) -> PowerWindow:
    start = dt.datetime(2026, 9, day, start_hour, 0, tzinfo=IST)
    return PowerWindow(
        start=start,
        end=start + dt.timedelta(hours=hours),
        source=WindowSource.DECLARED_ROTATION,
        reliability=reliability,
    )


def _schedule(
    decision: Decision = Decision.IRRIGATE,
    reason: ReasonCode = ReasonCode.STRESS_IMMINENT,
    *,
    minutes: float = 409.4,
    window: PowerWindow | None = None,
    with_start_time: bool = True,
    carry_over: float = 0.0,
) -> Schedule:
    return Schedule(
        field_id="sample",
        date=TODAY,
        decision=decision,
        reason_code=reason,
        minutes=minutes if decision is Decision.IRRIGATE else 0.0,
        window=window,
        start_time=(window.start if (window is not None and with_start_time) else None),
        delivered_mm=25.0,
        carry_over_mm=carry_over,
        required_mm=25.0 + carry_over,
    )


# Every case a farmer could plausibly hear, with a plain description of the
# situation so a reviewer knows what the words are meant to convey.
CASES: tuple[tuple[str, str, Schedule, EventKind | None, bool], ...] = (
    (
        "Night feeder, clock time given, field is dry",
        "Power tonight 22:00 to 06:00. Run the pump from 22:00 for about 6h 49m.",
        _schedule(window=_window()),
        None,
        False,
    ),
    (
        "Same, after the farmer reported he watered yesterday",
        "Opens by acknowledging his missed call, which is the only confirmation he gets.",
        _schedule(window=_window()),
        EventKind.WATER_GIVEN,
        False,
    ),
    (
        "Same, after he reported the power did not come",
        "Opens by acknowledging the power failure he reported.",
        _schedule(window=_window()),
        EventKind.POWER_FAILED,
        False,
    ),
    (
        "Morning feeder, called the previous evening",
        "Power 07:30 to 15:30 TOMORROW. The script must say tomorrow morning, not today.",
        _schedule(reason=ReasonCode.CAPACITY_LIMIT, window=_window(start_hour=7, day=5)),
        None,
        True,
    ),
    (
        "Unreliable feeder, no clock time can be promised",
        "Reliability below threshold. Says 'when the power comes' with a duration instead.",
        _schedule(window=_window(reliability=0.3), with_start_time=False, minutes=290.0),
        None,
        False,
    ),
    (
        "Window too short, run is truncated",
        "Only four hours of power. Runs the whole window and explains the rest follows.",
        _schedule(window=_window(hours=4.0), minutes=240.0, carry_over=12.5),
        None,
        False,
    ),
    (
        "Opportunistic top-up while power is available",
        "Field is not yet stressed, but there is power, so top it up.",
        _schedule(reason=ReasonCode.OPPORTUNISTIC_TOPUP, window=_window()),
        None,
        False,
    ),
    (
        "Short run, under an hour",
        "A small deficit on a strong pump.",
        _schedule(window=_window(reliability=0.3), with_start_time=False, minutes=37.0),
        None,
        False,
    ),
    (
        "Skip: rain is expected",
        "Do not run the pump. No window is named because none is being used.",
        _schedule(Decision.SKIP, ReasonCode.RAIN_EXPECTED),
        None,
        False,
    ),
)


def build_samples() -> str:
    """Render every case in every language into a reviewable document."""
    lines: list[str] = []
    lines.append("=" * 78)
    lines.append("FARMER-FACING SCRIPT SAMPLES")
    lines.append("=" * 78)
    lines.append("")
    lines.append("Every line below is what a farmer HEARS, spoken by Azure AI Speech.")
    lines.append("")
    lines.append("Please check, for Hindi and Tamil:")
    lines.append("  1. Is every word complete and correctly spelled?")
    lines.append("  2. Are the word boundaries right, nothing run together?")
    lines.append("  3. Is the register right for speaking to a farmer, not a bank customer?")
    lines.append("  4. Are the clock times natural? For example 'raat das baje', not '10:00'.")
    lines.append("  5. Would a listener know what to do after hearing it once?")
    lines.append("")
    lines.append("There are deliberately NO DIGITS anywhere. Every time and duration is")
    lines.append("spoken in words with its part of day, because a non-reader cannot tell")
    lines.append("whether '6:00' means morning or evening.")
    lines.append("")

    for index, (title, situation, schedule, acknowledge, previous_evening) in enumerate(
        CASES, start=1
    ):
        lines.append("-" * 78)
        lines.append(f"CASE {index}: {title}")
        lines.append(f"  Situation: {situation}")
        lines.append("-" * 78)
        call_window = CallWindow(
            dt.datetime(2026, 9, 4, 18, 0, tzinfo=IST),
            is_previous_evening=previous_evening,
        )
        for lang in supported_languages():
            text = speak_schedule(
                schedule,
                lang=lang,
                crop=CROPS[lang],
                farmer_name=NAMES[lang],
                acknowledge=acknowledge,
                call_window=call_window,
            )
            lines.append(f"  [{lang}] {text}")
        lines.append("")

    lines.append("-" * 78)
    lines.append("CASE 10: Next-day question, asked when no missed call arrived")
    lines.append("  Situation: The keypress fallback. Never the primary channel.")
    lines.append("-" * 78)
    for lang in supported_languages():
        lines.append(f"  [{lang}] {render_next_day_question(lang, farmer_name=NAMES[lang])}")
    lines.append("")

    lines.append("=" * 78)
    lines.append("Until a native speaker has read this file, the Hindi and Tamil masters")
    lines.append("remain marked TODO [VERIFY native speaker] and the report says so.")
    lines.append("=" * 78)
    lines.append("")
    return "\n".join(lines)


def write_samples(destination: Path) -> Path:
    """Write the samples to a UTF-8 file.

    Args:
        destination: Where to write.

    Returns:
        The path written.
    """
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(build_samples(), encoding="utf-8")
    return destination


def main(argv: list[str] | None = None) -> int:
    """Command-line entry point.

    Args:
        argv: Unused; present for symmetry with the other devtools.

    Returns:
        Process exit code.
    """
    del argv
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    path = write_samples(Path("results") / "script_samples.txt")
    print(f"wrote {path}")
    print("Open it in an editor that renders Devanagari and Tamil before reviewing.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
