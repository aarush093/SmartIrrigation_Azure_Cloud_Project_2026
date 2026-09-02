"""Tests for the depth-to-pump-minutes conversion.

The worked example is asserted at every intermediate step, not only at the total,
so that each number is defensible on its own at the viva. If the total is ever
wrong, these tests say which step moved.

Worked example, plan Section 6: wheat at mid-season, one acre (4,047 m2),
depletion 25 mm, furrow irrigation (Ea 0.65), 5 HP pump against 30 m head with
combined efficiency 0.5.
"""

from __future__ import annotations

import pytest

from irrigation_engine.models import BucketTest, IrrigationMethod, PumpSpec
from irrigation_engine.pump import (
    PumpRunTooLongError,
    gross_depth_mm,
    pump_discharge_l_per_min,
    pump_minutes,
    required_pump_minutes,
    resolve_efficiency,
)

ONE_ACRE_M2 = 4047.0
WHEAT_DEPLETION_MM = 25.0
FIVE_HP_AT_30M = PumpSpec(hp=5.0, head_m=30.0, eta=0.5)

# Two percent, as specified in the M1 amendment. Wide enough to absorb the
# rounding in the plan's stated figures, tight enough that a wrong constant or a
# dropped unit conversion fails.
TOLERANCE = 0.02


class TestWorkedExample:
    """Each link in the chain from depletion to running minutes."""

    def test_furrow_efficiency_is_0_65(self) -> None:
        """FAO Training Manual 4 furrow efficiency, from params/irrigation.yaml."""
        assert resolve_efficiency(IrrigationMethod.FURROW) == pytest.approx(0.65)

    def test_gross_depth_is_38_46_mm(self) -> None:
        """25 mm net at Ea 0.65 requires 38.46 mm gross to leave the pump."""
        gross = gross_depth_mm(WHEAT_DEPLETION_MM, 0.65)
        assert gross == pytest.approx(38.46, rel=TOLERANCE)

    def test_discharge_is_380_l_per_min(self) -> None:
        """Q = HP x 746 x eta / (9.81 x H), converted to litres per minute."""
        discharge = pump_discharge_l_per_min(FIVE_HP_AT_30M)
        assert discharge == pytest.approx(380.2, rel=TOLERANCE)

    def test_volume_is_about_155_654_litres(self) -> None:
        """One millimetre over one square metre is exactly one litre."""
        volume_l = gross_depth_mm(WHEAT_DEPLETION_MM, 0.65) * ONE_ACRE_M2
        assert volume_l == pytest.approx(155_654.0, rel=TOLERANCE)

    def test_running_time_is_about_409_minutes(self) -> None:
        """The full chain: about 409 minutes, which fits inside an 8-hour window."""
        minutes = pump_minutes(
            WHEAT_DEPLETION_MM, ONE_ACRE_M2, IrrigationMethod.FURROW, FIVE_HP_AT_30M
        )
        assert minutes == pytest.approx(409.0, rel=TOLERANCE)

    def test_the_worked_example_fits_an_eight_hour_window(self) -> None:
        """The whole point of the example: 409 minutes fits 480 with margin.

        At 45 mm depletion the same field needs roughly 740 minutes and spills
        into a second window, which is the situation the scheduler exists to
        avoid (plan Section 6).
        """
        minutes = pump_minutes(
            WHEAT_DEPLETION_MM, ONE_ACRE_M2, IrrigationMethod.FURROW, FIVE_HP_AT_30M
        )
        assert minutes < 8 * 60

    def test_deeper_depletion_overruns_a_single_window(self) -> None:
        """45 mm of depletion needs more than one 8-hour window on the same field.

        Plan Section 6 states about 740 minutes for this case. It is computed
        through ``required_pump_minutes`` rather than ``pump_minutes`` because it
        exceeds the 720-minute single-run ceiling: that is precisely the
        situation the scheduler exists to handle, by filling one window and
        carrying the remainder to the next.
        """
        minutes = required_pump_minutes(45.0, ONE_ACRE_M2, IrrigationMethod.FURROW, FIVE_HP_AT_30M)
        assert minutes > 8 * 60
        assert minutes == pytest.approx(737.0, rel=TOLERANCE)


class TestBucketTest:
    """The measured route, which is preferred over the nameplate estimate."""

    def test_discharge_is_litres_per_second_scaled_to_minutes(self) -> None:
        """15 litres in 2.4 seconds is 375 litres per minute."""
        assert pump_discharge_l_per_min(BucketTest(litres=15.0, seconds=2.4)) == pytest.approx(
            375.0
        )

    def test_bucket_test_drives_the_full_conversion(self) -> None:
        """A bucket test gives a running time without any efficiency assumption."""
        minutes = pump_minutes(
            WHEAT_DEPLETION_MM,
            ONE_ACRE_M2,
            IrrigationMethod.FURROW,
            BucketTest(litres=15.0, seconds=2.4),
        )
        expected = (WHEAT_DEPLETION_MM / 0.65 * ONE_ACRE_M2) / 375.0
        assert minutes == pytest.approx(expected)

    def test_a_slower_fill_means_a_longer_run(self) -> None:
        """Halving the discharge doubles the running time.

        The slow case exceeds the single-run ceiling, so it goes through
        ``required_pump_minutes``; a weak pump on an acre is exactly the field
        the scheduler must split across windows.
        """
        fast = required_pump_minutes(
            WHEAT_DEPLETION_MM,
            ONE_ACRE_M2,
            IrrigationMethod.FURROW,
            BucketTest(litres=15.0, seconds=2.4),
        )
        slow = required_pump_minutes(
            WHEAT_DEPLETION_MM,
            ONE_ACRE_M2,
            IrrigationMethod.FURROW,
            BucketTest(litres=15.0, seconds=4.8),
        )
        assert slow == pytest.approx(fast * 2.0)


class TestEfficiency:
    """Application efficiency resolution and its effect on the running time."""

    @pytest.mark.parametrize(
        ("method", "expected"),
        [
            (IrrigationMethod.FLOOD, 0.55),
            (IrrigationMethod.FURROW, 0.65),
            (IrrigationMethod.SPRINKLER, 0.75),
            (IrrigationMethod.DRIP, 0.90),
        ],
    )
    def test_method_defaults_match_the_parameter_file(
        self, method: IrrigationMethod, expected: float
    ) -> None:
        """FAO Training Manual 4 defaults, as fixed in plan Section 6."""
        assert resolve_efficiency(method) == pytest.approx(expected)

    def test_drip_needs_less_running_time_than_flood(self) -> None:
        """A more efficient method delivers the same net depth in fewer minutes."""
        flood = pump_minutes(
            WHEAT_DEPLETION_MM, ONE_ACRE_M2, IrrigationMethod.FLOOD, FIVE_HP_AT_30M
        )
        drip = pump_minutes(WHEAT_DEPLETION_MM, ONE_ACRE_M2, IrrigationMethod.DRIP, FIVE_HP_AT_30M)
        assert drip < flood

    def test_an_implausible_efficiency_override_is_rejected(self) -> None:
        """A farmer-supplied efficiency outside the bounds is a data entry error."""
        with pytest.raises(ValueError, match="application efficiency"):
            resolve_efficiency(0.05)


class TestDomainErrors:
    """Inputs that must fail rather than produce a confident wrong instruction."""

    def test_a_run_longer_than_the_ceiling_is_refused(self) -> None:
        """No published feeder window is twelve hours, so such a run is not advice.

        Telling a farmer to run his pump for nineteen hours would be worse than
        telling him nothing: it means the area, depth or discharge is wrong.
        """
        with pytest.raises(PumpRunTooLongError, match="single-run ceiling"):
            pump_minutes(60.0, 10_000.0, IrrigationMethod.FLOOD, FIVE_HP_AT_30M)

    def test_required_minutes_has_no_ceiling(self) -> None:
        """The arithmetic helper computes the requirement however long it is.

        Without this the scheduler could not fill a window and carry a remainder,
        because it would never learn the size of the remainder.
        """
        minutes = required_pump_minutes(120.0, ONE_ACRE_M2, IrrigationMethod.FLOOD, FIVE_HP_AT_30M)
        assert minutes > 720.0

    def test_the_ceiling_is_configurable(self) -> None:
        """The scheduler lowers the ceiling to the window length it is filling."""
        with pytest.raises(PumpRunTooLongError):
            pump_minutes(
                WHEAT_DEPLETION_MM,
                ONE_ACRE_M2,
                IrrigationMethod.FURROW,
                FIVE_HP_AT_30M,
                max_minutes=120.0,
            )

    def test_zero_area_is_rejected(self) -> None:
        """A field with no area cannot be irrigated."""
        with pytest.raises(ValueError, match="field area"):
            pump_minutes(WHEAT_DEPLETION_MM, 0.0, IrrigationMethod.FURROW, FIVE_HP_AT_30M)

    def test_negative_net_depth_is_rejected(self) -> None:
        """A negative depth would compute a negative running time."""
        with pytest.raises(ValueError, match="net depth"):
            gross_depth_mm(-5.0, 0.65)

    def test_zero_depletion_needs_no_running_time(self) -> None:
        """A full root zone needs no water, and that is a valid answer, not an error."""
        assert pump_minutes(0.0, ONE_ACRE_M2, IrrigationMethod.FURROW, FIVE_HP_AT_30M) == 0.0

    def test_an_implausible_head_is_rejected(self) -> None:
        """An extreme head drives the estimated discharge below the plausible floor."""
        with pytest.raises(ValueError, match="discharge"):
            pump_discharge_l_per_min(PumpSpec(hp=0.5, head_m=3000.0, eta=0.5))
