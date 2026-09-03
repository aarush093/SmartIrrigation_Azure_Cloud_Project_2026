"""Tests for the crop calendar and the depletion fraction adjustment.

The parameter values themselves are not asserted against printed tables here,
because ``params/crops.yaml`` is marked ``verified: false`` and no copy of
FAO-56, FAO-33 or FAO-66 was consulted during this build. What is asserted is the
structure the tables must have and the interpolation that consumes them.

TODO [VERIFY] once the parameter file is checked against the printed tables,
add assertions on the specific Kc, Zr, p and Ky values and flip ``verified``.
"""

from __future__ import annotations

import datetime as dt

import pytest

from irrigation_engine.crops import (
    adjust_depletion_fraction,
    available_crops,
    crop_calendar,
    growing_period_days,
)
from irrigation_engine.models import GrowthStage
from irrigation_engine.params import load_params

SOWN = dt.date(2026, 11, 15)

# The nine crops the build brief requires.
REQUIRED_CROPS = (
    "wheat",
    "maize",
    "rice",
    "cotton",
    "sugarcane",
    "groundnut",
    "tomato",
    "onion",
    "chickpea",
)


class TestParameterFile:
    """The shape and honesty of params/crops.yaml."""

    def test_every_required_crop_is_present(self) -> None:
        """All nine crops from the build brief are seeded."""
        assert set(REQUIRED_CROPS) <= set(available_crops())

    @pytest.mark.parametrize("crop", REQUIRED_CROPS)
    def test_every_crop_carries_the_full_parameter_set(self, crop: str) -> None:
        """No crop is missing a parameter the engine will read at runtime."""
        entry = load_params("crops")["crops"][crop]
        for field in (
            "kc_initial",
            "kc_mid",
            "kc_end",
            "stage_days",
            "root_depth_m",
            "root_depth_initial_m",
            "depletion_fraction",
            "ky",
        ):
            assert field in entry, f"{crop} is missing {field}"
        for stage in ("initial", "development", "mid", "late"):
            assert stage in entry["stage_days"], f"{crop} is missing stage {stage}"

    @pytest.mark.parametrize("crop", REQUIRED_CROPS)
    def test_parameters_are_physically_ordered(self, crop: str) -> None:
        """Kc peaks at mid-season, and roots start shallower than they finish."""
        entry = load_params("crops")["crops"][crop]
        assert entry["kc_mid"] >= entry["kc_initial"]
        assert entry["kc_mid"] >= entry["kc_end"]
        assert 0.0 < entry["root_depth_initial_m"] < entry["root_depth_m"]
        assert 0.0 < entry["depletion_fraction"] < 1.0
        assert entry["ky"] > 0.0

    def test_verification_is_recorded_per_field(self) -> None:
        """Every crop declares which of its fields were checked against a source.

        This is the guard on the project's own citation discipline. Granularity
        matters: Kc, Zr and p were read off the printed FAO-56 tables, while the
        Indian stage lengths and Ky were not, and the file must be able to say
        so field by field rather than crop by crop.
        """
        for crop in REQUIRED_CROPS:
            verified = load_params("crops")["crops"][crop]["verified"]
            for field in ("kc", "root_depth", "depletion_fraction", "stage_days", "ky"):
                assert field in verified, f"{crop} does not declare verification of {field}"
                assert isinstance(verified[field], bool)

    def test_zr_and_p_are_verified_for_every_crop(self) -> None:
        """Rooting depth and depletion fraction were confirmed against FAO-56 Table 22.

        Checked on 3 September 2026 against the printed table at
        https://www.fao.org/4/x0490e/x0490e0e.htm. All nine crops matched.
        """
        for crop in REQUIRED_CROPS:
            verified = load_params("crops")["crops"][crop]["verified"]
            assert verified["root_depth"] is True, f"{crop} rooting depth is unverified"
            assert verified["depletion_fraction"] is True, f"{crop} p is unverified"

    def test_stage_lengths_and_ky_remain_unverified(self) -> None:
        """Indian stage lengths and Ky are honestly still marked unverified.

        FAO-56 Table 11 has no Indian row, and Ky does not appear in FAO-56 at
        all. Neither can be closed by reading FAO-56, so both stay false. If a
        future session confirms them against ICAR, a state package of practice,
        FAO-33 or FAO-66, this test inverts for the fields it confirmed.
        """
        for crop in REQUIRED_CROPS:
            verified = load_params("crops")["crops"][crop]["verified"]
            assert verified["stage_days"] is False
            assert verified["ky"] is False

    def test_verified_all_is_false_while_any_field_is_unverified(self) -> None:
        """The summary flag cannot claim more than the per-field flags support."""
        params = load_params("crops")
        every_field = all(
            value for crop in params["crops"].values() for value in crop["verified"].values()
        )
        assert params["verified_all"] == every_field
        assert params["verified_all"] is False


class TestCropCalendar:
    """Stage resolution and Kc interpolation, FAO-56 Figure 34."""

    def test_sowing_day_is_the_initial_stage_at_kc_ini(self) -> None:
        """On day zero the crop sits at its initial crop coefficient."""
        stage = crop_calendar("wheat", SOWN, SOWN)
        entry = load_params("crops")["crops"]["wheat"]
        assert stage.stage is GrowthStage.INITIAL
        assert stage.kc == pytest.approx(entry["kc_initial"])
        assert stage.days_after_sowing == 0

    def test_kc_is_flat_through_the_initial_stage(self) -> None:
        """Kc does not move until the development stage begins."""
        first = crop_calendar("wheat", SOWN, SOWN + dt.timedelta(days=1))
        last = crop_calendar("wheat", SOWN, SOWN + dt.timedelta(days=20))
        assert first.kc == pytest.approx(last.kc)

    def test_kc_ramps_monotonically_through_development(self) -> None:
        """Kc rises steadily from Kc_ini to Kc_mid across the development stage."""
        entry = load_params("crops")["crops"]["wheat"]
        start = int(entry["stage_days"]["initial"])
        end = start + int(entry["stage_days"]["development"])

        values = [
            crop_calendar("wheat", SOWN, SOWN + dt.timedelta(days=d)).kc
            for d in range(start, end + 1)
        ]
        assert values == sorted(values)
        assert values[0] == pytest.approx(entry["kc_initial"], abs=0.05)
        assert values[-1] == pytest.approx(entry["kc_mid"])

    def test_kc_is_flat_at_the_maximum_through_mid_season(self) -> None:
        """Mid-season holds Kc_mid, the peak of the curve."""
        entry = load_params("crops")["crops"]["wheat"]
        start = int(entry["stage_days"]["initial"]) + int(entry["stage_days"]["development"])
        mid_point = start + int(entry["stage_days"]["mid"]) // 2

        stage = crop_calendar("wheat", SOWN, SOWN + dt.timedelta(days=mid_point))
        assert stage.stage is GrowthStage.MID
        assert stage.kc == pytest.approx(entry["kc_mid"])

    def test_kc_declines_through_the_late_season_to_kc_end(self) -> None:
        """Kc falls to Kc_end as the crop senesces."""
        entry = load_params("crops")["crops"]["wheat"]
        total = growing_period_days("wheat")
        final = crop_calendar("wheat", SOWN, SOWN + dt.timedelta(days=total))
        assert final.stage is GrowthStage.LATE
        assert final.kc == pytest.approx(entry["kc_end"])

    def test_all_four_stages_are_reachable(self) -> None:
        """Every stage occurs somewhere in the growing period."""
        total = growing_period_days("wheat")
        seen = {
            crop_calendar("wheat", SOWN, SOWN + dt.timedelta(days=d)).stage
            for d in range(total + 1)
        }
        assert seen == set(GrowthStage)

    def test_kc_never_leaves_the_range_the_table_defines(self) -> None:
        """Interpolation cannot produce a Kc outside the tabulated extremes."""
        for crop in REQUIRED_CROPS:
            entry = load_params("crops")["crops"][crop]
            low = min(entry["kc_initial"], entry["kc_end"])
            high = entry["kc_mid"]
            for day in range(growing_period_days(crop) + 1):
                kc = crop_calendar(crop, SOWN, SOWN + dt.timedelta(days=day)).kc
                assert low - 1e-9 <= kc <= high + 1e-9, f"{crop} day {day}: Kc {kc}"


class TestRootDepth:
    """Roots deepen through establishment and then hold."""

    def test_root_depth_starts_shallow(self) -> None:
        """A seedling is credited only with the water its roots can reach."""
        entry = load_params("crops")["crops"]["wheat"]
        stage = crop_calendar("wheat", SOWN, SOWN)
        assert stage.root_depth_m == pytest.approx(entry["root_depth_initial_m"])

    def test_root_depth_increases_monotonically_then_plateaus(self) -> None:
        """Depth rises to the maximum and never falls."""
        total = growing_period_days("wheat")
        depths = [
            crop_calendar("wheat", SOWN, SOWN + dt.timedelta(days=d)).root_depth_m
            for d in range(total + 1)
        ]
        assert depths == sorted(depths)

    def test_root_depth_reaches_the_maximum_by_mid_season(self) -> None:
        """The root zone is fully developed once the crop reaches mid-season."""
        entry = load_params("crops")["crops"]["wheat"]
        start_of_mid = int(entry["stage_days"]["initial"]) + int(entry["stage_days"]["development"])
        stage = crop_calendar("wheat", SOWN, SOWN + dt.timedelta(days=start_of_mid))
        assert stage.root_depth_m == pytest.approx(entry["root_depth_m"])


class TestCalendarErrors:
    """Dates and crops that cannot be resolved."""

    def test_a_date_before_sowing_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="precedes the sowing date"):
            crop_calendar("wheat", SOWN, SOWN - dt.timedelta(days=1))

    def test_a_date_past_harvest_is_rejected(self) -> None:
        """Past the growing period the crop is harvested and has no parameters."""
        total = growing_period_days("wheat")
        with pytest.raises(ValueError, match="beyond the"):
            crop_calendar("wheat", SOWN, SOWN + dt.timedelta(days=total + 1))

    def test_an_unknown_crop_names_the_alternatives(self) -> None:
        """The error tells the operator what they could have typed."""
        with pytest.raises(KeyError, match="available"):
            crop_calendar("quinoa", SOWN, SOWN)


class TestDepletionFractionAdjustment:
    """FAO-56 Table 22 note: p = p_table + 0.04 (5 - ETc), clamped to 0.1 to 0.8."""

    def test_no_adjustment_at_the_reference_demand(self) -> None:
        """At ETc of 5 mm/day the tabulated value applies unchanged."""
        assert adjust_depletion_fraction(0.55, 5.0) == pytest.approx(0.55)

    def test_high_demand_lowers_the_tolerated_depletion(self) -> None:
        """On a demanding day the crop stresses at a smaller deficit."""
        assert adjust_depletion_fraction(0.55, 9.0) == pytest.approx(0.55 + 0.04 * (5.0 - 9.0))
        assert adjust_depletion_fraction(0.55, 9.0) < 0.55

    def test_low_demand_raises_the_tolerated_depletion(self) -> None:
        """On a mild day the crop tolerates a deeper deficit before stressing."""
        assert adjust_depletion_fraction(0.55, 1.0) == pytest.approx(0.55 + 0.04 * 4.0)

    def test_the_lower_clamp_holds(self) -> None:
        """Extreme demand cannot drive p below 0.1."""
        assert adjust_depletion_fraction(0.20, 50.0) == pytest.approx(0.10)

    def test_the_upper_clamp_holds(self) -> None:
        """Zero demand cannot drive p above 0.8."""
        assert adjust_depletion_fraction(0.78, 0.0) == pytest.approx(0.80)

    @pytest.mark.parametrize("etc", [0.0, 1.0, 3.0, 5.0, 8.0, 15.0, 40.0])
    def test_the_result_always_stays_inside_the_clamps(self, etc: float) -> None:
        """No demand produces a depletion fraction outside 0.1 to 0.8."""
        for p_table in (0.20, 0.30, 0.55, 0.65):
            assert 0.10 <= adjust_depletion_fraction(p_table, etc) <= 0.80

    def test_negative_demand_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="cannot be negative"):
            adjust_depletion_fraction(0.55, -1.0)
