"""Shared pytest configuration.

The one rule enforced here is that the default suite reaches no network. Tests
that legitimately need a live API are marked ``@pytest.mark.integration``, are
deselected by default in ``pyproject.toml``, and are the only tests permitted to
open a socket.
"""

from __future__ import annotations

import socket
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def _no_network(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Fail any unit test that tries to open a network connection.

    A provider test that silently reaches Open-Meteo passes locally, then fails
    in CI or on a train. Blocking the socket makes the mistake immediate and
    obvious rather than intermittent.

    Integration tests are exempt.
    """
    if request.node.get_closest_marker("integration"):
        yield
        return

    def _blocked(*args: Any, **kwargs: Any) -> None:
        raise RuntimeError(
            "This test attempted a network connection. Use a fake provider, or "
            "mark the test @pytest.mark.integration if it genuinely needs the "
            "live API."
        )

    monkeypatch.setattr(socket.socket, "connect", _blocked)
    monkeypatch.setattr(socket, "create_connection", _blocked)
    yield


@pytest.fixture
def fixtures_dir() -> Path:
    """Directory holding committed test fixtures."""
    return FIXTURES
