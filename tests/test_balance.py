"""Tests for the FAO-56 root-zone water balance.

The central test here is conservation: over any sequence of days, what went into
the root zone minus what left it must equal the change in depletion. If that
identity fails, every downstream number - the irrigation depth, the pump minutes,
the simulated water saving - is wrong by the same amount, silently.
"""

from __future__ import annotations

import datetime as dt

import pytest

from irrigation_engine.balance import WaterBalance, effective_rainfall, scs_runoff
from irrigation_engine.models import CropStage, DailyWeather, GrowthStage

TAW = 150.0

WHEAT_MID = CropStage(
    crop="wheat",
    stage=GrowthStage.MID,
    days_after_sowing=90,
    kc=1.15,
    root_depth_m=1.5,
    depletion_fraction=0.55,
    yield_response_factor=1.0,
)


def weather(
    day: int, et0: float = 5.0, rain: float = 0.0, probability: float | None = None
) -> DailyWeather:
    """Build one forecast day, with the field's date offset by ``day``."""
    return DailyWeather(
        date=dt.date(2026, 3, 1) + dt.timedelta(days=day),
        et0_mm=et0,
        precipitation_mm=rain,
        precipitation_probability=probability,
    )


class TestSingleStep:
    """FAO-56 equation 85, one day at a time."""

    def test_depletion_grows_by_etc_on_a_dry_day(self) -> None:
        """With no rain and no irrigation, depletion increases by exactly ETc."""
        state = WaterBalance().step(20.0, weather(0, et0=5.0), WHEAT_MID, taw_mm=TAW)
        assert state.etc_mm == pytest.approx(1.15 * 5.0)
        assert state.depletion_mm == pytest.approx(20.0 + 1.15 * 5.0)

    def test_etc_is_kc_times_et0(self) -> None:
        """FAO-56 equation 31."""
        state = WaterBalance().step(0.0, weather(0, et0=4.0), WHEAT_MID, taw_mm=TAW)
        assert state.etc_mm == pytest.approx(4.6)

    def test_irrigation_reduces_depletion(self) -> None:
        """Net irrigation is subtracted from depletion, mm for mm."""
        dry = WaterBalance().step(40.0, weather(0, et0=5.0), WHEAT_MID, taw_mm=TAW)
        wet = WaterBalance().step(
            40.0, weather(0, et0=5.0), WHEAT_MID, irrigation_mm=20.0, taw_mm=TAW
        )
        assert wet.depletion_mm == pytest.approx(dry.depletion_mm - 20.0)

    def test_depletion_is_floored_at_zero(self) -> None:
        """Over-irrigating cannot drive the root zone above field capacity."""
        state = WaterBalance().step(
            5.0, weather(0, et0=1.0), WHEAT_MID, irrigation_mm=100.0, taw_mm=TAW
        )
        assert state.depletion_mm == 0.0

    def test_depletion_is_capped_at_taw(self) -> None:
        """The root zone cannot dry beyond empty, however long the drought."""
        balance = WaterBalance()
        depletion = TAW - 1.0
        for day in range(40):
            depletion = balance.step(
                depletion, weather(day, et0=10.0), WHEAT_MID, taw_mm=TAW
            ).depletion_mm
        assert depletion == pytest.approx(TAW)

    def test_excess_water_becomes_deep_percolation(self) -> None:
        """FAO-56 equation 88: water beyond the deficit drains below the root zone."""
        state = WaterBalance().step(
            10.0, weather(0, et0=1.0), WHEAT_MID, irrigation_mm=50.0, taw_mm=TAW
        )
        assert state.deep_percolation_mm > 0.0
        assert state.depletion_mm == 0.0

    def test_no_percolation_when_the_root_zone_can_absorb_the_water(self) -> None:
        """A deficit larger than the water applied leaves nothing to drain."""
        state = WaterBalance().step(
            60.0, weather(0, et0=5.0), WHEAT_MID, irrigation_mm=20.0, taw_mm=TAW
        )
        assert state.deep_percolation_mm == 0.0

    def test_raw_is_reported_with_the_etc_adjustment_applied(self) -> None:
        """RAW uses p adjusted for the day's demand, not the raw table value."""
        low_demand = WaterBalance().step(20.0, weather(0, et0=1.0), WHEAT_MID, taw_mm=TAW)
        high_demand = WaterBalance().step(20.0, weather(0, et0=9.0), WHEAT_MID, taw_mm=TAW)
        # A high-demand day tolerates less depletion before stress.
        assert high_demand.raw_mm < low_demand.raw_mm

    def test_stress_flag_trips_above_raw(self) -> None:
        """The crop is stressed once depletion passes readily available water."""
        state = WaterBalance().step(120.0, weather(0, et0=5.0), WHEAT_MID, taw_mm=TAW)
        assert state.depletion_mm > state.raw_mm
        assert state.is_stressed


class TestConservation:
    """The identity that makes every downstream number trustworthy."""

    def test_water_is_conserved_over_a_mixed_sequence(self) -> None:
        """Inputs minus outputs equals the change in depletion, to float tolerance.

        Depletion is a deficit, so it falls as water arrives:

            Dr_end - Dr_start = ETc - effective rain - irrigation + deep percolation

        The sequence deliberately mixes dry days, light rain that must be
        discarded, heavy rain, and an irrigation, and avoids the bounds so that
        no clamping masks a leak.
        """
        balance = WaterBalance()
        schedule = [
            (weather(0, et0=5.0), 0.0),
            (weather(1, et0=6.0, rain=2.0), 0.0),  # light rain, discarded
            (weather(2, et0=4.0, rain=12.0), 0.0),  # effective rain
            (weather(3, et0=5.0), 25.0),  # irrigation
            (weather(4, et0=7.0), 0.0),
            (weather(5, et0=3.0, rain=8.0), 0.0),
        ]

        start = 60.0
        depletion = start
        total_etc = total_rain = total_irrigation = total_percolation = 0.0

        for day, irrigation in schedule:
            state = balance.step(depletion, day, WHEAT_MID, irrigation, taw_mm=TAW)
            depletion = state.depletion_mm
            total_etc += state.etc_mm
            total_rain += state.effective_rain_mm
            total_irrigation += state.irrigation_mm
            total_percolation += state.deep_percolation_mm

        assert 0.0 < depletion < TAW, "sequence must not hit a bound, or it proves nothing"
        expected_change = total_etc - total_rain - total_irrigation + total_percolation
        assert depletion - start == pytest.approx(expected_change, abs=1e-9)

    def test_conservation_holds_with_runoff_enabled(self) -> None:
        """Enabling the runoff term does not break the identity."""
        balance = WaterBalance(use_scs_runoff=True, curve_number=80.0)
        depletion = 70.0
        start = depletion
        total_etc = total_rain = total_percolation = 0.0

        for day in range(6):
            state = balance.step(depletion, weather(day, et0=4.0, rain=6.0), WHEAT_MID, taw_mm=TAW)
            depletion = state.depletion_mm
            total_etc += state.etc_mm
            total_rain += state.effective_rain_mm
            total_percolation += state.deep_percolation_mm

        assert 0.0 < depletion < TAW
        assert depletion - start == pytest.approx(
            total_etc - total_rain + total_percolation, abs=1e-9
        )


class TestEffectiveRainfall:
    """Light rain is discarded rather than partially credited."""

    def test_rain_at_or_below_the_threshold_is_ignored(self) -> None:
        """Light rain on a dry surface evaporates before it infiltrates."""
        assert effective_rainfall(2.0, threshold_mm=3.0) == 0.0
        assert effective_rainfall(3.0, threshold_mm=3.0) == 0.0

    def test_rain_above_the_threshold_is_credited_in_full(self) -> None:
        """The rule is all-or-nothing, not a subtraction of the threshold."""
        assert effective_rainfall(10.0, threshold_mm=3.0) == 10.0

    def test_the_threshold_is_configurable(self) -> None:
        """A field with a mulch or a heavy soil may credit lighter rain."""
        assert effective_rainfall(2.0, threshold_mm=1.0) == 2.0

    def test_negative_rainfall_is_rejected(self) -> None:
        """Negative precipitation indicates a bad upstream record."""
        with pytest.raises(ValueError, match="precipitation"):
            effective_rainfall(-1.0)

    def test_light_rain_does_not_reduce_depletion(self) -> None:
        """The discard rule reaches the balance, not just the helper."""
        dry = WaterBalance().step(50.0, weather(0, et0=5.0), WHEAT_MID, taw_mm=TAW)
        drizzle = WaterBalance().step(50.0, weather(0, et0=5.0, rain=2.0), WHEAT_MID, taw_mm=TAW)
        assert drizzle.depletion_mm == pytest.approx(dry.depletion_mm)


class TestScsRunoff:
    """Soil Conservation Service curve number method, optional and off by default."""

    def test_runoff_is_off_by_default(self) -> None:
        """The pilot has no per-field curve number, so runoff is not assumed."""
        state = WaterBalance().step(50.0, weather(0, et0=5.0, rain=40.0), WHEAT_MID, taw_mm=TAW)
        assert state.runoff_mm == 0.0

    def test_no_runoff_below_the_initial_abstraction(self) -> None:
        """Light rain is entirely absorbed before any runs off."""
        assert scs_runoff(2.0, 75.0) == 0.0

    def test_runoff_increases_with_rainfall(self) -> None:
        """More rain produces more runoff, monotonically."""
        assert scs_runoff(80.0, 75.0) > scs_runoff(40.0, 75.0) > 0.0

    def test_runoff_never_exceeds_rainfall(self) -> None:
        """More water cannot run off than arrived."""
        for rain in (5.0, 25.0, 60.0, 150.0):
            assert scs_runoff(rain, 85.0) <= rain

    def test_a_higher_curve_number_sheds_more_water(self) -> None:
        """A less permeable surface produces more runoff from the same rainfall."""
        assert scs_runoff(50.0, 90.0) > scs_runoff(50.0, 60.0)

    def test_an_out_of_range_curve_number_is_rejected(self) -> None:
        """Curve numbers are defined on 30 to 100."""
        with pytest.raises(ValueError, match="curve number"):
            scs_runoff(20.0, 120.0)

    def test_enabling_runoff_without_a_curve_number_is_rejected(self) -> None:
        """Silently defaulting the curve number would remove water invisibly."""
        with pytest.raises(ValueError, match="curve_number"):
            WaterBalance(use_scs_runoff=True)


class TestInputValidation:
    """States that cannot physically arise are refused."""

    def test_negative_previous_depletion_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="previous depletion"):
            WaterBalance().step(-1.0, weather(0), WHEAT_MID, taw_mm=TAW)

    def test_previous_depletion_beyond_taw_is_rejected(self) -> None:
        """The root zone cannot be drier than empty."""
        with pytest.raises(ValueError, match="exceeds total available"):
            WaterBalance().step(TAW + 1.0, weather(0), WHEAT_MID, taw_mm=TAW)

    def test_negative_irrigation_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="irrigation"):
            WaterBalance().step(10.0, weather(0), WHEAT_MID, irrigation_mm=-5.0, taw_mm=TAW)

    def test_non_positive_taw_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="total available water"):
            WaterBalance().step(0.0, weather(0), WHEAT_MID, taw_mm=0.0)


def test_the_balance_is_deterministic() -> None:
    """Identical inputs give identical outputs.

    The scheduler's property tests depend on this, and so does the reviewer's
    ability to reproduce any decision the system made.
    """
    balance = WaterBalance()
    first = balance.step(45.0, weather(0, et0=5.5, rain=4.0), WHEAT_MID, 10.0, taw_mm=TAW)
    second = balance.step(45.0, weather(0, et0=5.5, rain=4.0), WHEAT_MID, 10.0, taw_mm=TAW)
    assert first == second
