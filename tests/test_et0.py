"""Tests for the FAO-56 Penman-Monteith implementation.

The primary test is :class:`TestFao56WorkedExample`, which asserts this
implementation against every printed value of **FAO-56 Example 18**, read from
the published text at https://www.fao.org/4/x0490e/x0490e08.htm. That example
establishes that the implementation is *correct*, which is a separate question
from whether it *agrees with Open-Meteo*; the latter is measured in
``tests/validation/et0_crosscheck.py``.

The remaining tests assert sensitivity in the direction physics requires and
physical bounds on the output, which is what would catch a sign error or a
swapped term introduced later.
"""

from __future__ import annotations

import datetime as dt

import pytest

from irrigation_engine.et0 import (
    atmospheric_pressure,
    extraterrestrial_radiation,
    net_radiation,
    penman_monteith,
    psychrometric_constant,
    saturation_vapour_pressure,
    svp_slope,
)

# Vellore, Tamil Nadu: one of the three pilot districts.
VELLORE_LAT = 12.97
VELLORE_ELEVATION_M = 216.0

MAY_DAY = dt.date(2026, 5, 15)
JANUARY_DAY = dt.date(2026, 1, 15)


def vellore_et0(**overrides: float) -> float:
    """Compute ET0 for a hot dry Vellore day, with named overrides."""
    args: dict[str, float] = {
        "temp_max_c": 38.0,
        "temp_min_c": 26.0,
        "wind_speed_2m": 2.0,
        "relative_humidity_max": 70.0,
        "relative_humidity_min": 30.0,
    }
    args.update(overrides)
    return penman_monteith(
        latitude=VELLORE_LAT,
        date=MAY_DAY,
        elevation_m=VELLORE_ELEVATION_M,
        **args,  # type: ignore[arg-type]
    )


class TestFao56WorkedExample:
    """FAO-56 Example 18, "Determination of ETo with daily data".

    Source: FAO Irrigation and Drainage Paper 56, Chapter 4, published at
    https://www.fao.org/4/x0490e/x0490e08.htm and read directly from that page.

    Uccle (Brussels, Belgium), 50 deg 48 min N, 100 m elevation, 6 July
    (day of year 187). Tmax 21.5 degC, Tmin 12.3 degC, RHmax 84 percent,
    RHmin 63 percent, wind 10 km/h measured at 10 m, sunshine 9.25 h.

    Every intermediate the example prints is asserted, not only the final ETo,
    so that a regression identifies the term that moved. The example derives
    solar radiation from sunshine hours by the Angstrom formula, which this
    module does not implement; the printed Rs of 22.07 MJ/m2/day is therefore
    supplied directly, and the radiation chain from Rs onward is still asserted.
    """

    LATITUDE = 50 + 48 / 60
    ELEVATION_M = 100.0
    DATE = dt.date(2026, 7, 6)
    TMAX = 21.5
    TMIN = 12.3
    RH_MAX = 84.0
    RH_MIN = 63.0
    U2 = 2.078
    RS_MJ = 22.07

    def test_day_of_year_is_187(self) -> None:
        """The example states day of year 187 for 6 July."""
        assert self.DATE.timetuple().tm_yday == 187

    def test_atmospheric_pressure_is_100_1_kpa(self) -> None:
        """FAO-56 Example 18 prints P = 100.1 kPa."""
        assert atmospheric_pressure(self.ELEVATION_M) == pytest.approx(100.1, abs=0.05)

    def test_psychrometric_constant_is_0_0666(self) -> None:
        """FAO-56 Example 18 prints gamma = 0.0666 kPa/degC."""
        gamma = psychrometric_constant(atmospheric_pressure(self.ELEVATION_M))
        assert gamma == pytest.approx(0.0666, abs=0.0001)

    def test_svp_slope_is_0_122(self) -> None:
        """FAO-56 Example 18 prints Delta = 0.122 kPa/degC at the mean temperature."""
        assert svp_slope((self.TMAX + self.TMIN) / 2) == pytest.approx(0.122, abs=0.0005)

    def test_saturation_vapour_pressures_match(self) -> None:
        """The example prints e0(Tmax) = 2.564 kPa and e0(Tmin) = 1.431 kPa."""
        assert saturation_vapour_pressure(self.TMAX) == pytest.approx(2.564, abs=0.001)
        assert saturation_vapour_pressure(self.TMIN) == pytest.approx(1.431, abs=0.001)

    def test_mean_saturation_vapour_pressure_is_1_997(self) -> None:
        """The example prints es = 1.997 kPa, the mean of the two extremes."""
        es = (saturation_vapour_pressure(self.TMAX) + saturation_vapour_pressure(self.TMIN)) / 2
        assert es == pytest.approx(1.997, abs=0.001)

    def test_actual_vapour_pressure_is_1_409(self) -> None:
        """The example prints ea = 1.409 kPa, from FAO-56 equation 17."""
        ea = (
            saturation_vapour_pressure(self.TMIN) * self.RH_MAX / 100.0
            + saturation_vapour_pressure(self.TMAX) * self.RH_MIN / 100.0
        ) / 2
        assert ea == pytest.approx(1.409, abs=0.001)

    def test_extraterrestrial_radiation_is_41_09(self) -> None:
        """The example prints Ra = 41.09 MJ/m2/day."""
        ra = extraterrestrial_radiation(self.LATITUDE, self.DATE)
        assert ra == pytest.approx(41.09, abs=0.02)

    def test_clear_sky_radiation_is_30_90(self) -> None:
        """The example prints Rso = 30.90 MJ/m2/day, FAO-56 equation 37."""
        ra = extraterrestrial_radiation(self.LATITUDE, self.DATE)
        assert (0.75 + 2e-5 * self.ELEVATION_M) * ra == pytest.approx(30.90, abs=0.02)

    def test_net_radiation_is_13_28(self) -> None:
        """The example prints Rns 17.00, Rnl 3.71 and Rn 13.28 MJ/m2/day.

        This is the strongest single assertion in the module: net radiation
        exercises the albedo, the clear-sky ratio, the cloudiness factor, the
        Stefan-Boltzmann term and the humidity correction together.
        """
        ea = (
            saturation_vapour_pressure(self.TMIN) * self.RH_MAX / 100.0
            + saturation_vapour_pressure(self.TMAX) * self.RH_MIN / 100.0
        ) / 2
        ra = extraterrestrial_radiation(self.LATITUDE, self.DATE)
        rn = net_radiation(
            solar_radiation_mj=self.RS_MJ,
            ra_mj=ra,
            temp_max_c=self.TMAX,
            temp_min_c=self.TMIN,
            actual_vapour_pressure_kpa=ea,
            elevation_m=self.ELEVATION_M,
        )
        assert pytest.approx(17.00, abs=0.02) == 0.77 * self.RS_MJ
        assert 0.77 * self.RS_MJ - rn == pytest.approx(3.71, abs=0.02)
        assert rn == pytest.approx(13.28, abs=0.02)

    def test_eto_matches_the_printed_value(self) -> None:
        """FAO-56 Example 18 prints ETo = 3.9 mm/day.

        The paper prints one decimal place, so the tolerance is the half-unit of
        that precision: this implementation returns 3.88, which is 3.9 as
        printed. This is the assertion that establishes the implementation is
        correct, independently of whether it agrees with any other provider.
        """
        et0 = penman_monteith(
            temp_max_c=self.TMAX,
            temp_min_c=self.TMIN,
            latitude=self.LATITUDE,
            date=self.DATE,
            elevation_m=self.ELEVATION_M,
            wind_speed_2m=self.U2,
            relative_humidity_max=self.RH_MAX,
            relative_humidity_min=self.RH_MIN,
            solar_radiation_mj=self.RS_MJ,
        )
        assert et0 == pytest.approx(3.9, abs=0.05)
        assert round(et0, 1) == 3.9


class TestKnownQuantities:
    """Intermediates FAO-56 states in its text, recomputed from the formula."""

    def test_saturation_vapour_pressure_at_20c(self) -> None:
        """e0(20 degC) is 2.338 kPa.

        FAO-56 Annex 2 Table 3 tabulates this value, and equation 11 reproduces
        it. Asserted because it is the one number in this module that can be
        confirmed two independent ways.
        """
        assert saturation_vapour_pressure(20.0) == pytest.approx(2.338, abs=0.001)

    def test_psychrometric_constant_at_sea_level(self) -> None:
        """At 101.3 kPa the psychrometric constant is about 0.067 kPa/degC.

        FAO-56 equation 8 with the standard atmosphere of equation 7.
        """
        assert atmospheric_pressure(0.0) == pytest.approx(101.3, abs=0.01)
        assert psychrometric_constant(101.3) == pytest.approx(0.0674, abs=0.0005)

    def test_pressure_falls_with_elevation(self) -> None:
        """FAO-56 equation 7 is monotonically decreasing in elevation."""
        assert atmospheric_pressure(0.0) > atmospheric_pressure(1000.0)
        assert atmospheric_pressure(1000.0) > atmospheric_pressure(3000.0)

    def test_svp_slope_rises_with_temperature(self) -> None:
        """The saturation curve steepens as air warms, so evaporation accelerates."""
        assert svp_slope(35.0) > svp_slope(20.0) > svp_slope(5.0)

    def test_saturation_vapour_pressure_is_monotonic(self) -> None:
        """Warmer air holds more moisture at saturation, at every temperature."""
        values = [saturation_vapour_pressure(t) for t in range(0, 50, 5)]
        assert values == sorted(values)


class TestExtraterrestrialRadiation:
    """FAO-56 equation 21 and its astronomy."""

    def test_northern_summer_exceeds_northern_winter(self) -> None:
        """At 40 N, June receives far more extraterrestrial radiation than December."""
        june = extraterrestrial_radiation(40.0, dt.date(2026, 6, 21))
        december = extraterrestrial_radiation(40.0, dt.date(2026, 12, 21))
        assert june > december
        assert june / december > 2.5

    def test_the_seasonal_swing_reverses_across_the_equator(self) -> None:
        """At 40 S the same two dates swap places."""
        june = extraterrestrial_radiation(-40.0, dt.date(2026, 6, 21))
        december = extraterrestrial_radiation(-40.0, dt.date(2026, 12, 21))
        assert december > june

    def test_the_tropics_vary_far_less_than_the_mid_latitudes(self) -> None:
        """Near the equator Ra is nearly constant, which is why Indian ET0 is stable."""
        equator = [extraterrestrial_radiation(0.0, dt.date(2026, m, 15)) for m in range(1, 13)]
        mid = [extraterrestrial_radiation(45.0, dt.date(2026, m, 15)) for m in range(1, 13)]
        assert (max(equator) - min(equator)) < (max(mid) - min(mid))

    def test_values_stay_in_the_physical_range(self) -> None:
        """Ra never goes negative and never exceeds the solar constant's daily bound."""
        for latitude in (-60.0, -30.0, 0.0, 13.0, 31.0, 60.0):
            for month in range(1, 13):
                ra = extraterrestrial_radiation(latitude, dt.date(2026, month, 15))
                assert 0.0 <= ra <= 50.0

    def test_the_poles_do_not_raise(self) -> None:
        """The sunset hour angle is clamped, so polar day and night are handled."""
        assert extraterrestrial_radiation(89.0, dt.date(2026, 6, 21)) > 0.0
        assert extraterrestrial_radiation(89.0, dt.date(2026, 12, 21)) == pytest.approx(
            0.0, abs=1.0
        )

    def test_an_impossible_latitude_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="latitude"):
            extraterrestrial_radiation(120.0, MAY_DAY)


class TestSensitivity:
    """ET0 must respond to each driver in the direction physics requires.

    These are the tests that would catch a sign error or a swapped term, which is
    the realistic failure mode for a hand-implemented combination equation.
    """

    def test_hotter_air_raises_et0(self) -> None:
        assert vellore_et0(temp_max_c=42.0) > vellore_et0(temp_max_c=34.0)

    def test_stronger_wind_raises_et0(self) -> None:
        """The aerodynamic term grows with wind speed."""
        assert vellore_et0(wind_speed_2m=5.0) > vellore_et0(wind_speed_2m=0.5)

    def test_higher_humidity_lowers_et0(self) -> None:
        """A smaller vapour pressure deficit drives less evaporation."""
        humid = vellore_et0(relative_humidity_max=95.0, relative_humidity_min=75.0)
        dry = vellore_et0(relative_humidity_max=50.0, relative_humidity_min=15.0)
        assert humid < dry

    def test_more_radiation_raises_et0(self) -> None:
        """The radiation term dominates ET0 in the tropics."""
        bright = penman_monteith(
            temp_max_c=38.0,
            temp_min_c=26.0,
            latitude=VELLORE_LAT,
            date=MAY_DAY,
            elevation_m=VELLORE_ELEVATION_M,
            solar_radiation_mj=25.0,
        )
        dull = penman_monteith(
            temp_max_c=38.0,
            temp_min_c=26.0,
            latitude=VELLORE_LAT,
            date=MAY_DAY,
            elevation_m=VELLORE_ELEVATION_M,
            solar_radiation_mj=10.0,
        )
        assert bright > dull

    def test_summer_exceeds_winter_at_the_same_site(self) -> None:
        """Seasonality reaches the final number, not just the radiation term."""
        summer = penman_monteith(
            temp_max_c=38.0,
            temp_min_c=26.0,
            latitude=VELLORE_LAT,
            date=MAY_DAY,
            elevation_m=VELLORE_ELEVATION_M,
        )
        winter = penman_monteith(
            temp_max_c=29.0,
            temp_min_c=19.0,
            latitude=VELLORE_LAT,
            date=JANUARY_DAY,
            elevation_m=VELLORE_ELEVATION_M,
        )
        assert summer > winter


class TestPhysicalBounds:
    """ET0 must be plausible across the range of Indian conditions."""

    @pytest.mark.parametrize(
        ("t_max", "t_min", "date"),
        [
            (45.0, 28.0, dt.date(2026, 5, 20)),  # peak summer, north India
            (38.0, 26.0, MAY_DAY),  # hot south Indian summer
            (32.0, 24.0, dt.date(2026, 8, 15)),  # humid monsoon
            (29.0, 19.0, JANUARY_DAY),  # south Indian winter
            (18.0, 4.0, dt.date(2026, 1, 10)),  # north Indian rabi cold spell
        ],
    )
    def test_indian_conditions_give_plausible_daily_et0(
        self, t_max: float, t_min: float, date: dt.date
    ) -> None:
        """Daily ET0 across Indian conditions falls between 0.5 and 15 mm/day.

        Wide on purpose. The point is to catch an implementation that returns a
        negative number, a near-zero, or something on the order of a hundred, not
        to pin an exact figure this build cannot source.
        """
        et0 = penman_monteith(
            temp_max_c=t_max,
            temp_min_c=t_min,
            latitude=28.6 if t_max > 40 else VELLORE_LAT,
            date=date,
            elevation_m=VELLORE_ELEVATION_M,
        )
        assert 0.5 <= et0 <= 15.0, f"implausible ET0 {et0:.2f} mm/day"

    def test_a_hot_dry_day_exceeds_a_cool_humid_one_by_a_wide_margin(self) -> None:
        """The dynamic range across a season is at least a factor of two."""
        hot = vellore_et0(relative_humidity_max=40.0, relative_humidity_min=12.0)
        cool = penman_monteith(
            temp_max_c=24.0,
            temp_min_c=18.0,
            latitude=VELLORE_LAT,
            date=dt.date(2026, 8, 10),
            elevation_m=VELLORE_ELEVATION_M,
            relative_humidity_max=95.0,
            relative_humidity_min=80.0,
            wind_speed_2m=1.0,
        )
        assert hot > 2.0 * cool


class TestFallbacks:
    """FAO-56 Chapter 3 substitutions for missing measurements."""

    def test_et0_computes_from_temperature_alone(self) -> None:
        """With only Tmax and Tmin, all three fallbacks engage and still give a number.

        This matters operationally: the archive does not carry every variable for
        every station-day, and the cross-check must still run on those days.
        """
        et0 = penman_monteith(
            temp_max_c=36.0,
            temp_min_c=24.0,
            latitude=VELLORE_LAT,
            date=MAY_DAY,
            elevation_m=VELLORE_ELEVATION_M,
        )
        assert 0.5 <= et0 <= 15.0

    def test_supplying_wind_changes_the_result(self) -> None:
        """The default 2 m/s is a substitute, not a value the caller cannot override."""
        default = penman_monteith(
            temp_max_c=36.0,
            temp_min_c=24.0,
            latitude=VELLORE_LAT,
            date=MAY_DAY,
            elevation_m=VELLORE_ELEVATION_M,
        )
        windy = penman_monteith(
            temp_max_c=36.0,
            temp_min_c=24.0,
            latitude=VELLORE_LAT,
            date=MAY_DAY,
            elevation_m=VELLORE_ELEVATION_M,
            wind_speed_2m=6.0,
        )
        assert windy != default

    def test_the_coastal_flag_changes_the_radiation_estimate(self) -> None:
        """Coastal sites use a different Hargreaves coefficient (FAO-56 equation 50)."""
        interior = penman_monteith(
            temp_max_c=36.0,
            temp_min_c=24.0,
            latitude=VELLORE_LAT,
            date=MAY_DAY,
            elevation_m=VELLORE_ELEVATION_M,
            coastal=False,
        )
        coastal = penman_monteith(
            temp_max_c=36.0,
            temp_min_c=24.0,
            latitude=VELLORE_LAT,
            date=MAY_DAY,
            elevation_m=VELLORE_ELEVATION_M,
            coastal=True,
        )
        assert coastal > interior

    def test_a_single_humidity_extreme_is_enough(self) -> None:
        """FAO-56 equation 18 handles one humidity reading."""
        only_max = vellore_et0(relative_humidity_max=70.0, relative_humidity_min=None)  # type: ignore[arg-type]
        assert 0.5 <= only_max <= 15.0


class TestInputValidation:
    """Inputs that cannot describe a real day."""

    def test_inverted_temperatures_are_rejected(self) -> None:
        """A minimum above the maximum means the arguments were swapped."""
        with pytest.raises(ValueError, match="minimum temperature"):
            penman_monteith(
                temp_max_c=20.0,
                temp_min_c=30.0,
                latitude=VELLORE_LAT,
                date=MAY_DAY,
                elevation_m=VELLORE_ELEVATION_M,
            )

    def test_an_impossible_latitude_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="latitude"):
            penman_monteith(
                temp_max_c=30.0,
                temp_min_c=20.0,
                latitude=100.0,
                date=MAY_DAY,
                elevation_m=0.0,
            )

    def test_an_impossible_elevation_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="elevation"):
            penman_monteith(
                temp_max_c=30.0,
                temp_min_c=20.0,
                latitude=VELLORE_LAT,
                date=MAY_DAY,
                elevation_m=-2000.0,
            )

    def test_negative_wind_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="wind speed"):
            vellore_et0(wind_speed_2m=-1.0)


def test_penman_monteith_is_deterministic() -> None:
    """Identical inputs give an identical result, exactly."""
    first = vellore_et0()
    second = vellore_et0()
    assert first == second
