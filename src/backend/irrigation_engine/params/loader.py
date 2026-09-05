"""Load and cache the YAML parameter files.

Parameters are read once and cached, because they are read on every water
balance step and every scheduling decision and never change at runtime.
"""

from __future__ import annotations

from functools import cache
from importlib import resources
from typing import Any

import yaml

__all__ = ["clear_cache", "load_params", "load_script"]

_PACKAGE = "irrigation_engine.params"
_SCRIPTS_PACKAGE = "irrigation_engine.scripts"


@cache
def _read(name: str, package: str = _PACKAGE) -> dict[str, Any]:
    """Read and parse one YAML file from a package, cached by name."""
    resource = resources.files(package).joinpath(f"{name}.yaml")
    if not resource.is_file():
        available = sorted(
            p.name.removesuffix(".yaml")
            for p in resources.files(package).iterdir()
            if p.name.endswith(".yaml")
        )
        msg = f"no YAML file named {name!r} in {package}; available: {', '.join(available)}"
        raise FileNotFoundError(msg)

    parsed = yaml.safe_load(resource.read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        msg = f"{name!r} must parse to a mapping, got {type(parsed).__name__}"
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


def load_script(lang: str) -> dict[str, Any]:
    """Load a farmer-facing script master by language code.

    Kept separate from :func:`load_params` because the two hold different kinds
    of thing and are governed by different rules: parameters carry agronomic
    constants with a citation, while script masters carry every word a farmer
    hears and are governed by the no-technical-units rule in CLAUDE.md.

    Args:
        lang: Language code, for example ``"hi"``, ``"en"`` or ``"ta"``.

    Returns:
        The parsed script master. Callers must treat it as read-only.

    Raises:
        FileNotFoundError: If no master exists for that language.
        ValueError: If the file does not parse to a mapping.
    """
    return _read(lang, _SCRIPTS_PACKAGE)
