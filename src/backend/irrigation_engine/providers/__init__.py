"""External data adapters, each with an offline fake."""

from irrigation_engine.providers.base import SoilProvider, WeatherProvider
from irrigation_engine.providers.fakes import FakeSoilProvider, FakeWeatherProvider
from irrigation_engine.providers.openmeteo import (
    OpenMeteoProvider,
    fetch_archive,
    fetch_weather,
)
from irrigation_engine.providers.soilgrids import SoilGridsProvider, fetch_soil

__all__ = [
    "FakeSoilProvider",
    "FakeWeatherProvider",
    "OpenMeteoProvider",
    "SoilGridsProvider",
    "SoilProvider",
    "WeatherProvider",
    "fetch_archive",
    "fetch_soil",
    "fetch_weather",
]
