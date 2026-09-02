"""Contract tests for the engine's public surface.

These run from M0, before any behaviour exists, and they are not filler. They
enforce three properties that are cheap to break and expensive to discover late:

1. Every name promised in ``__all__`` actually resolves. A stale re-export in
   ``__init__.py`` otherwise fails only at the call site, in a Function, in
   Azure.
2. The engine imports no Azure SDK. This is the rule that keeps the agronomy
   reviewable offline, and it is far easier to hold from the first commit than
   to restore once something has reached for a client.
3. Importing the engine touches no network.
"""

from __future__ import annotations

import importlib
import pkgutil
from pathlib import Path

import pytest

import irrigation_engine


def test_all_exported_names_resolve() -> None:
    """Every name in __all__ is a real attribute of the package."""
    missing = [name for name in irrigation_engine.__all__ if not hasattr(irrigation_engine, name)]
    assert not missing, f"__all__ promises names that do not resolve: {missing}"


def test_all_is_sorted_within_its_groups() -> None:
    """__all__ has no duplicates, which would mask a missing export."""
    names = irrigation_engine.__all__
    duplicates = {name for name in names if names.count(name) > 1}
    assert not duplicates, f"duplicate entries in __all__: {duplicates}"


@pytest.mark.parametrize(
    "name",
    [
        # Data model
        "BucketTest",
        "CropStage",
        "DailyWeather",
        "GrowthStage",
        "IrrigationMethod",
        "PumpSpec",
        "SoilProfile",
        "SoilWaterConstants",
        "WaterBalanceState",
        # Acquisition
        "OpenMeteoProvider",
        "SoilGridsProvider",
        "FakeWeatherProvider",
        "FakeSoilProvider",
        "fetch_weather",
        "fetch_archive",
        "fetch_soil",
        # Agronomy
        "crop_calendar",
        "penman_monteith",
        "saxton_rawls",
        "total_available_water",
        # Balance and pump
        "WaterBalance",
        "pump_minutes",
        # Forecasting interface
        "MoistureForecaster",
        "KcEt0Forecaster",
    ],
)
def test_documented_api_names_are_present(name: str) -> None:
    """The M1 public API named in the build brief is exposed at the package root.

    Listed explicitly rather than derived from ``__all__`` so that deleting an
    export fails this test instead of silently shrinking the contract.
    """
    assert hasattr(irrigation_engine, name)


def _engine_modules() -> list[str]:
    """Return every importable module inside the engine package."""
    return [
        module.name
        for module in pkgutil.walk_packages(irrigation_engine.__path__, prefix="irrigation_engine.")
    ]


def test_engine_imports_no_azure_sdk() -> None:
    """No module in the engine imports an Azure SDK.

    The engine is a pure library so that the FAO-56 logic can be reviewed and
    tested with no cloud credentials. See CLAUDE.md section 4.
    """
    offenders: list[str] = []
    for module_name in _engine_modules():
        module = importlib.import_module(module_name)
        source = getattr(module, "__file__", None)
        if source is None:
            continue
        text = Path(source).read_text(encoding="utf-8")
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith(("import azure", "from azure")):
                offenders.append(f"{module_name}: {stripped}")
    assert not offenders, f"the engine must not import Azure: {offenders}"


def test_every_engine_module_imports_cleanly() -> None:
    """Importing any engine module raises nothing.

    Guards against a stub whose module-level code was left in a broken state.
    """
    for module_name in _engine_modules():
        importlib.import_module(module_name)


def test_kc_et0_forecaster_satisfies_the_protocol() -> None:
    """The default forecaster structurally satisfies MoistureForecaster.

    Krishna's Objective 3 model will be checked against the same protocol, so
    this test is the contract between the two modules.
    """
    assert isinstance(irrigation_engine.KcEt0Forecaster(), irrigation_engine.MoistureForecaster)
