"""Env-driven configuration scenarios."""

from collections.abc import Callable

import pytest

from app.core.config import get_settings


@pytest.fixture(autouse=True)
def _clear_cache() -> None:
    get_settings.cache_clear()


def test_defaults_when_env_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    monkeypatch.delenv("APP_ENV", raising=False)
    get_settings.cache_clear()
    settings = get_settings()
    assert settings.cors_origins == ["http://localhost:4321"]
    assert "*" not in settings.cors_origins


def test_comma_separated_origins_parsed(app_with_env: Callable[..., object]) -> None:
    app_with_env(CORS_ORIGINS="https://a.com,https://b.com")
    settings = get_settings()
    assert settings.cors_origins == ["https://a.com", "https://b.com"]


def test_app_env_reflects_environment(app_with_env: Callable[..., object]) -> None:
    app_with_env(APP_ENV="production")
    assert get_settings().app_env == "production"


def test_default_origins_never_wildcard(monkeypatch: pytest.MonkeyPatch) -> None:
    # Explicit guard for the spec rule: defaults must never be `*`.
    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    get_settings.cache_clear()
    assert "*" not in get_settings().cors_origins
