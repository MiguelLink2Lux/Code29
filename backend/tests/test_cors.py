"""CORS reflects exactly the configured origins, never `*`."""

from collections.abc import Callable

from fastapi import FastAPI
from fastapi.testclient import TestClient


def test_allowed_origin_echoed(app_with_env: Callable[..., FastAPI]) -> None:
    app = app_with_env(CORS_ORIGINS="http://localhost:4321")
    client = TestClient(app)
    response = client.get("/api/v1/health", headers={"Origin": "http://localhost:4321"})
    assert response.headers.get("access-control-allow-origin") == "http://localhost:4321"


def test_disallowed_origin_not_echoed(app_with_env: Callable[..., FastAPI]) -> None:
    app = app_with_env(CORS_ORIGINS="http://localhost:4321")
    client = TestClient(app)
    response = client.get("/api/v1/health", headers={"Origin": "https://evil.com"})
    allow_origin = response.headers.get("access-control-allow-origin")
    assert allow_origin != "https://evil.com"
    assert allow_origin != "*"


def test_no_wildcard_origin_ever_returned(app_with_env: Callable[..., FastAPI]) -> None:
    # Spec guard: even with multiple configured origins, CORS never grants `*`.
    app = app_with_env(CORS_ORIGINS="http://localhost:4321,https://app.code29.dev")
    client = TestClient(app)
    response = client.get("/api/v1/health", headers={"Origin": "https://other.com"})
    assert response.headers.get("access-control-allow-origin") != "*"


def test_production_origin_can_be_configured(app_with_env: Callable[..., FastAPI]) -> None:
    # The deployed frontend lives on its own Vercel project, so the backend must
    # accept an absolute https origin, not just the local dev server.
    app = app_with_env(CORS_ORIGINS="https://code29.dev,https://www.code29.dev")
    client = TestClient(app)
    response = client.get("/api/v1/health", headers={"Origin": "https://code29.dev"})
    assert response.headers.get("access-control-allow-origin") == "https://code29.dev"


def test_a_wildcard_origin_is_dropped_rather_than_fatal() -> None:
    """The wildcard never survives; the service does.

    This used to assert a raise, and raising here runs during the import of
    app.main — so a CORS setting could take the whole backend down, /health with
    it. A backend that will not start is not safer than one that allows no
    origins: both serve nothing to a browser, and only one can be asked why.
    """
    from app.core.config import Settings

    assert Settings(cors_origins="*").cors_origins == []
    assert Settings(cors_origins="https://code29.dev,*").cors_origins == ["https://code29.dev"]
