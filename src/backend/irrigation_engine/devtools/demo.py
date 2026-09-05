"""End-to-end demonstration of the daily loop, with no Azure resource.

Seeds the three pilot farmers, pulls **real** Open-Meteo forecast and ISRIC
SoilGrids data for their actual fields, runs the full chain, and prints the
scripts each farmer would hear in his own language.

    weather + soil -> Saxton-Rawls -> water balance -> depletion
                   -> pump minutes -> power-window scheduler -> spoken script

Everything Azure is behind a feature flag and off. The simulated telephony
records what would have been said and writes the browser call console, which is
what a reviewer is actually shown.

Run it with ``make demo``.
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from dataclasses import dataclass
from pathlib import Path

from irrigation_engine.balance import WaterBalance
from irrigation_engine.crops import crop_calendar
from irrigation_engine.forecasting import KcEt0Forecaster
from irrigation_engine.models import (
    CropStage,
    DailyWeather,
    IrrigationMethod,
    PumpSpec,
    SoilProfile,
    SoilWaterConstants,
)
from irrigation_engine.providers import OpenMeteoProvider, SoilGridsProvider
from irrigation_engine.pump import pump_discharge_l_per_min, resolve_efficiency
from irrigation_engine.scheduler import (
    IST,
    Decision,
    DeclaredRotation,
    FieldState,
    Schedule,
    plan_day,
)
from irrigation_engine.scripts_render import call_time_for, should_call, speak_schedule
from irrigation_engine.soil import (
    SoilSource,
    resolve_soil,
    saxton_rawls,
    total_available_water,
)
from irrigation_engine.telephony import FakeSpeech, SimulatedTelephony

__all__ = ["PILOT_FARMERS", "DemoFarmer", "main", "run_demo"]


@dataclass(frozen=True)
class DemoFarmer:
    """One of the three pilot farmers, from plan Section 12."""

    farmer_id: str
    name: str
    village: str
    phone: str
    language: str
    crop: str
    crop_spoken: str
    latitude: float
    longitude: float
    area_m2: float
    method: IrrigationMethod
    pump: PumpSpec
    sowing_date: dt.date
    rotation: DeclaredRotation
    initial_depletion_mm: float
    #: What the farmer said about his own soil at onboarding. Primary input;
    #: SoilGrids only prefills it. See params/soil_texture_classes.yaml.
    declared_soil: str


def _night_rotation(anchor: dt.date, *, night_first: bool = True) -> DeclaredRotation:
    """An eight-hour day/night rotation on a weekly cycle."""
    return DeclaredRotation(
        day_start=dt.time(7, 30),
        day_end=dt.time(15, 30),
        night_start=dt.time(22, 0),
        night_end=dt.time(6, 0),
        rotation_days=7,
        anchor_date=anchor,
        anchor_is_day_shift=not night_first,
    )


def _daytime_solar(anchor: dt.date) -> DeclaredRotation:
    """A daytime solar feeder: eight hours of day supply, every day."""
    return DeclaredRotation(
        day_start=dt.time(7, 30),
        day_end=dt.time(15, 30),
        night_start=dt.time(7, 30),
        night_end=dt.time(15, 30),
        rotation_days=1,
        anchor_date=anchor,
        anchor_is_day_shift=True,
    )


ANCHOR = dt.date(2026, 9, 1)

# The three pilot farmers from plan Section 12.
#
# Crop, sowing date and district are chosen so that each is genuinely plausible
# on the demonstration date in early September, because an agriculture-literate
# reviewer will check exactly that and a wrong one would undermine everything
# correct behind it.
#
#   Vellore, Tamil Nadu   GROUNDNUT, kharif, sown mid-June. Groundnut is widely
#                         grown in the northern Tamil Nadu districts; wheat is
#                         not grown there at all, and is in any case a rabi crop
#                         sown in November. By 4 September a mid-June sowing is
#                         about 80 days old, which is mid-season.
#
#   Beed, Maharashtra     COTTON, kharif, sown mid-June with the monsoon. Beed
#                         is in the Marathwada cotton belt. About 80 days old on
#                         the demonstration date, which is mid-season.
#
#   Ludhiana, Punjab      RICE, kharif, transplanted late June. Punjab paddy is
#                         transplanted from mid-June once the canal and tubewell
#                         supply allows. About 70 days old, which is mid-season,
#                         and the highest-demand point of the crop.
PILOT_FARMERS = (
    DemoFarmer(
        farmer_id="farmer-vellore-01",
        name="Murugan",
        village="Vellore, Tamil Nadu",
        phone="+919000000001",
        language="ta",
        crop="groundnut",
        crop_spoken="\u0b95\u0b9f\u0bb2\u0bc8",
        latitude=12.97,
        longitude=79.16,
        area_m2=4047.0,
        method=IrrigationMethod.FURROW,
        pump=PumpSpec(hp=5.0, head_m=30.0, eta=0.5),
        sowing_date=dt.date(2026, 6, 16),
        rotation=_night_rotation(ANCHOR, night_first=False),
        initial_depletion_mm=32.0,
        declared_soil="sandy",
    ),
    DemoFarmer(
        farmer_id="farmer-beed-01",
        name="राम",
        village="Beed, Maharashtra",
        phone="+919000000002",
        language="hi",
        crop="cotton",
        crop_spoken="\u0915\u092a\u093e\u0938",
        latitude=18.99,
        longitude=75.76,
        area_m2=8094.0,
        method=IrrigationMethod.FLOOD,
        pump=PumpSpec(hp=7.5, head_m=45.0, eta=0.5),
        sowing_date=dt.date(2026, 6, 15),
        # A daytime solar feeder, as in the ADB Maharashtra solarisation
        # programme referenced in plan Section 2.
        rotation=_daytime_solar(ANCHOR),
        initial_depletion_mm=58.0,
        declared_soil="clayey",
    ),
    DemoFarmer(
        farmer_id="farmer-ludhiana-01",
        name="Gurpreet",
        village="Ludhiana, Punjab",
        phone="+919000000003",
        language="hi",
        crop="rice",
        crop_spoken="\u0927\u093e\u0928",
        latitude=30.90,
        longitude=75.86,
        area_m2=12141.0,
        method=IrrigationMethod.FLOOD,
        pump=PumpSpec(hp=10.0, head_m=40.0, eta=0.5),
        sowing_date=dt.date(2026, 6, 25),
        # An eight-hour rotation, night shift this week.
        rotation=_night_rotation(ANCHOR, night_first=True),
        initial_depletion_mm=22.0,
        declared_soil="loamy",
    ),
)


def run_demo(*, today: dt.date, offline: bool = False, out_dir: Path | None = None) -> int:
    """Run the daily loop for all three pilot farmers.

    Args:
        today: The date to plan for. An argument rather than a clock read, so a
            demonstration is reproducible.
        offline: Skip the live API calls and use fixed weather and soil, so the
            demo still runs on a machine with no network.
        out_dir: Where to write the call console. Defaults to ``results/``.

    Returns:
        A process exit code: 0 if every farmer produced a decision.
    """
    telephony = SimulatedTelephony()
    speech = FakeSpeech()
    forecaster = KcEt0Forecaster()
    balance = WaterBalance()

    # The daily loop runs in the morning, before any window has opened.
    planning_instant = dt.datetime.combine(today, dt.time(9, 0), tzinfo=IST)

    weather_provider = None if offline else OpenMeteoProvider()
    soil_provider = None if offline else SoilGridsProvider()

    print()
    print("=" * 78)
    print("  Smart Irrigation: daily loop for the three pilot farmers")
    print(f"  planning date {today.isoformat()}   mode: {'offline' if offline else 'live data'}")
    print("=" * 78)

    for farmer in PILOT_FARMERS:
        print()
        print(f"--- {farmer.name}, {farmer.village} ({farmer.crop}, {farmer.language})")

        weather = _fetch_weather(weather_provider, farmer, today)
        prefill = _fetch_soil(soil_provider, farmer)
        soil, soil_source = resolve_soil(
            declared_class=farmer.declared_soil, soilgrids_profile=prefill
        )
        if soil_source is SoilSource.FALLBACK:
            print("  WARNING:   soil is a GUESS. Ask the farmer before trusting the depth.")

        constants = saxton_rawls(soil)
        stage = crop_calendar(farmer.crop, farmer.sowing_date, today)
        taw = total_available_water(constants, stage.root_depth_m)

        stages = [
            crop_calendar(farmer.crop, farmer.sowing_date, today + dt.timedelta(days=offset))
            for offset in range(len(weather))
        ]
        etc = forecaster.forecast_etc(weather, stages)

        state_today = balance.step(
            min(farmer.initial_depletion_mm, taw), weather[0], stage, taw_mm=taw
        )
        field_state = FieldState(
            field_id=f"{farmer.farmer_id}-f1",
            depletion_mm=state_today.depletion_mm,
            taw_mm=taw,
            raw_mm=state_today.raw_mm,
            area_m2=farmer.area_m2,
            irrigation_efficiency=resolve_efficiency(farmer.method),
            discharge_l_per_min=pump_discharge_l_per_min(farmer.pump),
            yield_response_factor=stage.yield_response_factor,
        )

        # Plan from the actual planning instant, not from midnight. A window
        # that has already opened cannot be scheduled into, and offering one
        # would produce a call about a window that closed hours ago.
        windows = farmer.rotation.windows(planning_instant, days=3)
        schedule = plan_day(field_state, today=today, windows=windows, forecast_etc_mm=etc)

        _print_state(constants, soil_source, stage, taw, field_state, schedule)

        if not should_call(schedule):
            print("  call:      none. Nothing is being asked of the farmer today.")
            continue

        when = call_time_for(schedule, now=planning_instant)
        text = speak_schedule(
            schedule,
            lang=farmer.language,
            crop=farmer.crop_spoken,
            farmer_name=farmer.name,
            call_window=when,
        )
        rendered = speech.synthesise(text, lang=farmer.language)
        telephony.place_call(farmer.phone, rendered.text, audio_url=rendered.audio_url)

        print(f"  call at:   {when.at.strftime('%H:%M')} IST")
        print(f"  script:    {text}")

    destination = (out_dir or Path("results")) / "call_console.html"
    _write_console(telephony, destination, today)
    print()
    print(f"  call console written to {destination}")
    print(f"  {len(telephony.placed)} call(s) placed, none of them real")
    print()
    return 0


def _fetch_weather(
    provider: OpenMeteoProvider | None, farmer: DemoFarmer, today: dt.date
) -> list[DailyWeather]:
    """Fetch the forecast, falling back to a fixed series when offline."""
    if provider is not None:
        try:
            days = provider.fetch_weather(farmer.latitude, farmer.longitude, days=7)
            if days:
                return days
        except Exception as error:  # a demo must not die on a network blip
            print(f"  note:      Open-Meteo unavailable ({error}); using fixed weather")

    from irrigation_engine.models import DailyWeather

    return [
        DailyWeather(
            date=today + dt.timedelta(days=offset),
            et0_mm=5.4,
            precipitation_mm=0.0,
            precipitation_probability=0.05,
        )
        for offset in range(7)
    ]


def _fetch_soil(provider: SoilGridsProvider | None, farmer: DemoFarmer) -> SoilProfile | None:
    """Try SoilGrids as a PREFILL for the farmer's declared texture.

    Returns None where it is unavailable, which on 3 September 2026 was every
    pilot point. The farmer's own answer is the primary input and stands on its
    own; see ``params/soil_texture_classes.yaml`` for why that is the better
    design and not merely a workaround.
    """
    if provider is None:
        return None
    try:
        return provider.fetch_soil(farmer.latitude, farmer.longitude)
    except Exception as error:  # a demo must not die on a bad point
        print(f"  note:      SoilGrids prefill unavailable ({error}); the farmer's answer stands")
        return None


def _print_state(
    constants: SoilWaterConstants,
    source: SoilSource,
    stage: CropStage,
    taw_mm: float,
    state: FieldState,
    schedule: Schedule,
) -> None:
    """Print the operator-facing view.

    Technical units are used freely here: this is what an agronomist or a
    reviewer reads, not what the farmer hears. The farmer-facing rendering is
    ``speak_schedule``, and a test enforces that none of these units reach it.
    """
    print(
        f"  soil:      {source.value}, field capacity {constants.theta_fc:.3f}, "
        f"wilting point {constants.theta_wp:.3f} m3/m3"
    )
    print(
        f"  crop:      {stage.stage.value}, Kc {stage.kc:.2f}, "
        f"Zr {stage.root_depth_m:.2f} m, Ky {stage.yield_response_factor:.2f}"
    )
    print(
        f"  balance:   depletion {state.depletion_mm:.1f} mm, "
        f"RAW {state.raw_mm:.1f} mm, TAW {taw_mm:.1f} mm"
    )
    print(f"  decision:  {schedule.decision.value.upper()} ({schedule.reason_code.value})")

    if schedule.decision is not Decision.IRRIGATE or schedule.window is None:
        return

    window = schedule.window
    print(
        f"  window:    {window.start.strftime('%d %b %H:%M')} to "
        f"{window.end.strftime('%H:%M')} IST "
        f"({window.duration_minutes:.0f} min, source {window.source.value})"
    )
    print(f"  run:       {schedule.minutes:.0f} minutes")
    if schedule.carry_over_mm > 0:
        print(f"  carry:     {schedule.carry_over_mm:.1f} mm to the next window")


def _write_console(telephony: SimulatedTelephony, destination: Path, today: dt.date) -> None:
    """Write the browser call console for the placed calls."""
    from irrigation_engine.devtools.console import render_console

    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(render_console(telephony, today), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    """Command-line entry point.

    Args:
        argv: Arguments, defaulting to ``sys.argv``.

    Returns:
        Process exit code.
    """
    parser = argparse.ArgumentParser(description="Run the daily loop for the pilot farmers.")
    parser.add_argument(
        "--date",
        type=dt.date.fromisoformat,
        default=dt.date.today(),  # a demo date, not a decision input
        help="Planning date, ISO format. Defaults to today.",
    )
    parser.add_argument(
        "--offline", action="store_true", help="Skip live API calls and use fixed data."
    )
    parser.add_argument("--out", type=Path, default=None, help="Where to write the call console.")
    args = parser.parse_args(argv)

    # The scripts are Hindi and Tamil; a Windows console defaults to a codepage
    # that cannot encode them and would crash on the first print.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    return run_demo(today=args.date, offline=args.offline, out_dir=args.out)


if __name__ == "__main__":
    raise SystemExit(main())
