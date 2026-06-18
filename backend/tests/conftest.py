"""Shared test fixtures: a TestClient and an env-override helper.

The env helper sets environment variables, clears the cached settings so the
next `get_settings()` re-reads the environment, and rebuilds the app — the
supported way to test env-driven config without a live settings dependency.
"""

from collections.abc import Callable, Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import create_app


@pytest.fixture
def client() -> TestClient:
    """TestClient over a freshly built app using current (default) settings."""
    get_settings.cache_clear()
    return TestClient(create_app())


@pytest.fixture
def app_with_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[Callable[..., FastAPI]]:
    """Return a builder that applies env vars, clears the settings cache, and
    rebuilds the app so the new environment takes effect."""

    def _build(**env: str) -> FastAPI:
        for key, value in env.items():
            monkeypatch.setenv(key, value)
        get_settings.cache_clear()
        return create_app()

    yield _build
    # Ensure later tests start from a clean cache.
    get_settings.cache_clear()
