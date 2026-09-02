"""Load and cache the YAML parameter files.

Parameters are read once and cached, because they are read on every water
balance step and every scheduling decision and never change at runtime.
"""

from __future__ import annotations

from functools import cache
from importlib import resources
from typing import Any

import yaml

__all__ = ["clear_cache", "load_params"]

_PACKAGE = "irrigation_engine.params"


@cache
def _read(name: str) -> dict[str, Any]:
    """Read and parse one parameter file, cached by name."""
    resource = resources.files(_PACKAGE).joinpath(f"{name}.yaml")
    if not resource.is_file():
        available = sorted(
            p.name.removesuffix(".yaml")
            for p in resources.files(_PACKAGE).iterdir()
            if p.name.endswith(".yaml")
        )
        msg = f"no parameter file named {name!r}; available: {', '.join(available)}"
        raise FileNotFoundError(msg)

    parsed = yaml.safe_load(resource.read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        msg = f"parameter file {name!r} must parse to a mapping, got {type(parsed).__name__}"
        raise ValueError(msg)
    return parsed


def load_params(name: str) -> dict[str, Any]:
    """Load a parameter file from this package by name.

    Args:
        name: File stem, without the extension, for example ``"crops"``.

    Returns:
        The parsed mapping. Callers must treat it as read-only; it is shared
        between every caller and is not copied.

    Raises:
        FileNotFoundError: If no such parameter file exists.
        ValueError: If the file does not parse to a mapping.
    """
    return _read(name)


def clear_cache() -> None:
    """Drop the cached parameter files.

    Used by tests that write a temporary parameter file and need the loader to
    read it again.
    """
    _read.cache_clear()
