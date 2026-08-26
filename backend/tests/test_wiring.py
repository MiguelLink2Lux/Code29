"""The app must WIRE the phases together, not just contain them.

Every phase was built against a Protocol with a refusing default so it could
ship alone. That is safe, but it means an unwired route answers 503 to a caller
holding a perfectly valid token — which is exactly what a local run found after
the phases were merged. These tests assert the wiring itself.
"""

import pytest
from fastapi.testclient import TestClient

from app.api.v1.site_analysis import (
    UnconfiguredVerifier,
    get_access_token_verifier,
)
from app.core.config import Settings
from app.core.report_settings import get_report_delivery_settings
from app.main import create_app
from app.services.extraction import GeminiFactExtractor, StubFactExtractor
from app.services.tokens import issue_access_token

SECRET = "wiring-secret-of-at-least-32-characters!"
EMAIL = "ada@example.com"


def configured() -> Settings:
    return Settings(
        contact_token_secret=SECRET,
        resend_api_key="re_test",
        turnstile_secret_key="ts_test",
        contact_from_email="noreply@code29.dev",
        contact_to_email="hola@code29.dev",
    )


def test_site_analysis_verifier_is_not_the_refusing_default() -> None:
    app = create_app(settings=configured())

    resolved = app.dependency_overrides.get(get_access_token_verifier, get_access_token_verifier)()

    assert not isinstance(resolved, UnconfiguredVerifier), (
        "site-analysis still uses the refusing placeholder: a valid token would get 503"
    )


def test_a_valid_token_is_accepted_by_site_analysis() -> None:
    app = create_app(settings=configured())
    client = TestClient(app)
    token = issue_access_token(EMAIL, secret=SECRET)

    # A private target must be refused by the SSRF guard (400), NOT by the
    # authorisation layer (401/503): that difference proves the token was read.
    response = client.post(
        "/api/v1/contact/site-analysis",
        json={"url": "http://127.0.0.1/"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 400, response.text


def test_a_forged_token_is_still_rejected_after_wiring() -> None:
    app = create_app(settings=configured())
    client = TestClient(app)

    response = client.post(
        "/api/v1/contact/site-analysis",
        json={"url": "https://example.com"},
        headers={"Authorization": "Bearer forged.token"},
    )

    assert response.status_code == 401, response.text


def test_an_unconfigured_deployment_still_refuses() -> None:
    app = create_app(settings=Settings(contact_token_secret=""))
    client = TestClient(app)

    response = client.post(
        "/api/v1/contact/site-analysis",
        json={"url": "https://example.com"},
        headers={"Authorization": "Bearer whatever"},
    )

    assert response.status_code in {401, 503}, response.text


def test_the_gemini_extractor_is_wired_when_a_key_is_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A configured GEMINI_API_KEY must reach the conversation, not just the report.

    `_build_extractor` guarded on `hasattr(settings, "gemini_api_key")`, and
    `Settings` never declared that field — so the guard was permanently false and
    every deployment conducted the conversation with the stub, key or no key.
    """
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-test-key")
    get_report_delivery_settings.cache_clear()

    app = create_app(settings=configured())

    assert isinstance(app.state.fact_extractor, GeminiFactExtractor), (
        "a configured GEMINI_API_KEY must select the model extractor"
    )

    get_report_delivery_settings.cache_clear()


def test_the_stub_extractor_is_wired_when_no_key_is_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No key is not an error: the conversation still runs, it just extracts less."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    get_report_delivery_settings.cache_clear()

    app = create_app(settings=configured())

    assert isinstance(app.state.fact_extractor, StubFactExtractor)

    get_report_delivery_settings.cache_clear()
