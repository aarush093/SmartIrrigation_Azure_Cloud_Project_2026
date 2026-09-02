"""Load and cache the YAML parameter files.

Parameters are read once and cached, because they are read on every water
balance step and every scheduling decision, and they never change at runtime.

Implemented in M1.
"""

from __future__ import annotations

from typing import Any

__all__ = ["clear_cache", "load_params"]


def load_params(name: str) -> dict[str, Any]:
    """Load a parameter file from this package by name.

    Args:
        name: File stem, without the extension, for example ``"crops"``.

    Returns:
        The parsed mapping. Callers must treat it as read-only; it is shared.

    Raises:
        FileNotFoundError: If no such parameter file exists.
        ValueError: If the file does not parse to a mapping.
    """
    raise NotImplementedError("M1")


def clear_cache() -> None:
    """Drop the cached parameter files.

    Used by tests that write a temporary parameter file and need the loader to
    read it again.
    """
    raise NotImplementedError("M1")
