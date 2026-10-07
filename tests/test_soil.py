"""Tests for the Saxton and Rawls pedotransfer.

Reference: K. E. Saxton and W. J. Rawls, "Soil water characteristic estimates by
texture and organic matter for hydrologic solutions", Soil Science Society of
America Journal, 70(5), pp. 1569-1578, 2006.

No printed value from the paper is asserted here, because no copy was consulted
during this build. The tests instead assert the properties the paper's results
must satisfy: available water ordered correctly across the texture triangle, all
values inside published physical ranges, and correct rejection of impossible
inputs. See the ruling in ``docs/PHASE2_BUILD_LOG.md``.

TODO [VERIFY] replace the range assertions below with the paper's own worked
values for the sand, silt loam and clay examples once a copy is available.
"""

from __future__ import annotations

import pytest

from irrigation_engine.models import SoilProfile
from irrigation_engine.soil import (
    readily_available_water,
    saxton_rawls,
    total_available_water,
)

# Representative points in the USDA texture triangle. Organic carbon and bulk
# density are held constant so that texture is the only variable.
SAND = SoilProfile(sand=0.90, silt=0.05, clay=0.05, organic_carbon=0.012, bulk_density=1.35)
SANDY_LOAM = SoilProfile(sand=0.65, silt=0.25, clay=0.10, organic_carbon=0.012, bulk_density=1.35)
LOAM = SoilProfile(sand=0.40, silt=0.40, clay=0.20, organic_carbon=0.012, bulk_density=1.35)
SILT_LOAM = SoilProfile(sand=0.20, silt=0.65, clay=0.15, organic_carbon=0.012, bulk_density=1.35)
CLAY = SoilProfile(sand=0.20, silt=0.20, clay=0.60, organic_carbon=0.012, bulk_density=1.35)


@pytest.mark.parametrize(
    ("name", "soil", "aw_low", "aw_high"),
    [
        # Available water capacity ranges widely reported for these textures.
        # Deliberately generous: the test is that the model lands in the right
        # physical neighbourhood, not that it reproduces one author's table.
        ("sand", SAND, 0.02, 0.08),
        ("sandy loam", SANDY_LOAM, 0.06, 0.14),
        ("loam", LOAM, 0.10, 0.20),
        ("silt loam", SILT_LOAM, 0.12, 0.24),
        ("clay", CLAY, 0.08, 0.20),
    ],
)
def test_available_water_falls_in_the_published_range(
    name: str, soil: SoilProfile, aw_low: float, aw_high: float
) -> None:
    """Plant-available water for each texture sits in its accepted range."""
    constants = saxton_rawls(soil)
    available = constants.available_water_fraction
    assert aw_low <= available <= aw_high, (
        f"{name}: available water {available:.3f} m3/m3 outside {aw_low} to {aw_high}"
    )


def test_field_capacity_always_exceeds_wilting_point() -> None:
    """Across the texture triangle, field capacity is never below wilting point."""
    for soil in (SAND, SANDY_LOAM, LOAM, SILT_LOAM, CLAY):
        constants = saxton_rawls(soil)
        assert constants.theta_fc > constants.theta_wp


def test_clay_holds_more_water_than_sand_at_both_tensions() -> None:
    """A clay soil retains more water than a sand at field capacity and at wilting.

    This is the ordering that makes the pedotransfer useful at all. If it
    inverted, every irrigation depth on heavy soils would be wrong.
    """
    sand = saxton_rawls(SAND)
    clay = saxton_rawls(CLAY)
    assert clay.theta_fc > sand.theta_fc
    assert clay.theta_wp > sand.theta_wp


def test_sand_holds_the_least_available_water() -> None:
    """Sand has the lowest available water of any texture tested.

    Sand drains freely, so it holds little between field capacity and wilting
    point. This is why a sandy field needs short, frequent irrigations, which is
    exactly the case the power-window scheduler finds hardest.
    """
    available = {
        "sand": saxton_rawls(SAND).available_water_fraction,
        "sandy loam": saxton_rawls(SANDY_LOAM).available_water_fraction,
        "loam": saxton_rawls(LOAM).available_water_fraction,
        "silt loam": saxton_rawls(SILT_LOAM).available_water_fraction,
    }
    assert available["sand"] == min(available.values())


def test_organic_matter_increases_water_retention() -> None:
    """Adding organic matter raises available water, all else equal."""
    poor = SoilProfile(sand=0.40, silt=0.40, clay=0.20, organic_carbon=0.002, bulk_density=1.35)
    rich = SoilProfile(sand=0.40, silt=0.40, clay=0.20, organic_carbon=0.030, bulk_density=1.35)
    assert saxton_rawls(rich).available_water_fraction > saxton_rawls(poor).available_water_fraction


def test_texture_fractions_must_sum_to_one() -> None:
    """A texture that does not sum to unity is rejected, naming the likely cause.

    SoilGrids reports texture in g/kg. Passing those numbers through unscaled is
    the single most likely integration error, and it must fail loudly rather
    than produce a confident wrong answer.
    """
    with pytest.raises(ValueError, match=r"sum to about 1\.0"):
        saxton_rawls(
            SoilProfile(sand=0.40, silt=0.40, clay=0.40, organic_carbon=0.01, bulk_density=1.35)
        )


def test_implausible_bulk_density_is_rejected() -> None:
    """Bulk density outside the physical range is rejected, naming the unit error."""
    with pytest.raises(ValueError, match="bulk density"):
        saxton_rawls(
            SoilProfile(sand=0.40, silt=0.40, clay=0.20, organic_carbon=0.01, bulk_density=135.0)
        )


class TestTotalAvailableWater:
    """FAO-56 equations 82 and 83."""

    def test_taw_scales_linearly_with_root_depth(self) -> None:
        """Doubling the rooting depth doubles total available water."""
        constants = saxton_rawls(LOAM)
        assert total_available_water(constants, 1.0) == pytest.approx(
            total_available_water(constants, 0.5) * 2.0
        )

    def test_taw_uses_millimetres(self) -> None:
        """TAW = 1000 (theta_FC - theta_WP) Zr converts metres of water to mm."""
        constants = saxton_rawls(LOAM)
        expected = 1000.0 * constants.available_water_fraction * 0.8
        assert total_available_water(constants, 0.8) == pytest.approx(expected)

    def test_zero_root_depth_is_rejected(self) -> None:
        """A crop with no root zone has no available water, which is not a state."""
        with pytest.raises(ValueError, match="rooting depth"):
            total_available_water(saxton_rawls(LOAM), 0.0)

    def test_raw_is_the_depletion_fraction_of_taw(self) -> None:
        """FAO-56 equation 83: RAW = p x TAW."""
        assert readily_available_water(150.0, 0.55) == pytest.approx(82.5)

    @pytest.mark.parametrize("p", [0.0, 1.0, -0.1, 1.5])
    def test_depletion_fraction_outside_zero_to_one_is_rejected(self, p: float) -> None:
        """A depletion fraction must lie strictly inside 0 to 1."""
        with pytest.raises(ValueError, match="depletion fraction"):
            readily_available_water(150.0, p)
