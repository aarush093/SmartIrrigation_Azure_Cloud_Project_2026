"""FAO-56 irrigation engine for power-window-aware scheduling.

A pure, dependency-light library: ``numpy``, ``pydantic``, ``httpx`` and
``pyyaml`` only, with no Azure imports anywhere. It stays importable and testable
with no network and no cloud credentials, which is what makes the agronomy
independently reviewable and lets the Azure Functions layer stay a thin shell
over it.

The library answers three questions in sequence:

1. How short is the root zone, in millimetres?  :mod:`~irrigation_engine.balance`
2. How many pump minutes does that shortfall cost?  :mod:`~irrigation_engine.pump`
3. Do those minutes fit inside the next power window?  ``irrigation_engine.scheduler`` (M2)

Specification: ``docs/PHASE2_NOVELTY_AND_PLAN.md``. Standards: ``CLAUDE.md``.
"""

from irrigation_engine.balance import WaterBalance, effective_rainfall, scs_runoff
from irrigation_engine.crops import adjust_depletion_fraction, available_crops, crop_calendar
from irrigation_engine.et0 import penman_monteith
from irrigation_engine.forecasting import KcEt0Forecaster, MoistureForecaster
from irrigation_engine.models import (
    BucketTest,
    CropStage,
    DailyWeather,
    GrowthStage,
    IrrigationMethod,
    PumpCharacterisation,
    PumpSpec,
    SoilProfile,
    SoilWaterConstants,
    WaterBalanceState,
)
from irrigation_engine.providers import (
    FakeSoilProvider,
    FakeWeatherProvider,
    OpenMeteoProvider,
    SoilGridsProvider,
    SoilProvider,
    WeatherProvider,
    fetch_archive,
    fetch_soil,
    fetch_weather,
)
from irrigation_engine.pump import gross_depth_mm, pump_discharge_lpm, pump_minutes
from irrigation_engine.soil import saxton_rawls, total_available_water

__version__ = "0.1.0"

# Grouped by concern rather than sorted: the grouping tells a reviewer what the
# library does, which alphabetical order would destroy.
__all__ = [  # noqa: RUF022
    # Data model
    "BucketTest",
    "CropStage",
    "DailyWeather",
    "GrowthStage",
    "IrrigationMethod",
    "PumpCharacterisation",
    "PumpSpec",
    "SoilProfile",
    "SoilWaterConstants",
    "WaterBalanceState",
    # Weather and soil acquisition
    "FakeSoilProvider",
    "FakeWeatherProvider",
    "OpenMeteoProvider",
    "SoilGridsProvider",
    "SoilProvider",
    "WeatherProvider",
    "fetch_archive",
    "fetch_soil",
    "fetch_weather",
    # Agronomy
    "adjust_depletion_fraction",
    "available_crops",
    "crop_calendar",
    "penman_monteith",
    "saxton_rawls",
    "total_available_water",
    # Water balance
    "WaterBalance",
    "effective_rainfall",
    "scs_runoff",
    # Pump conversion
    "gross_depth_mm",
    "pump_discharge_lpm",
    "pump_minutes",
    # Moisture forecasting interface
    "KcEt0Forecaster",
    "MoistureForecaster",
    "__version__",
]
