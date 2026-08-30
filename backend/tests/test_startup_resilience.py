"""The app boots whatever the environment says, and `/health` answers.

On 2026-08-29 every route of the deployed backend returned 500 —
`/api/v1/health` and `/docs` included — because `CONTACT_TOKEN_SECRET` had been
set to a value shorter than the minimum. `create_app()` runs at module level, so
a validator raising there is not a refused feature: it is a service that never
starts, silently, with no HTTP answer to say why.

Two hours went into finding a variable the process already knew the name of.

So the rule this file exists to hold: **a misconfigured variable disables what
depends on it and nothing else.** The flow answers 503, the reason names the
variable in the log, and `/health` stays up so an operator can tell "the service
is running and the contact flow is off" apart from "everything is broken".

The matrix matters more than any single case. The list of variables grows, and
each new one is a new way to take production down at three in the morning.
"""

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.core.report_settings import get_report_delivery_settings
from app.main import create_app

HEALTH = "/api/v1/health"

#: Every variable the backend reads, and every shape of wrong we have seen or can
#: expect from a dashboard: left blank, half-typed, padded, wrong type.
VARIABLES = (
    "APP_ENV",
    "CONTACT_TOKEN_SECRET",
    "RESEND_API_KEY",
    "TURNSTILE_SECRET_KEY",
    "CONTACT_FROM_EMAIL",
    "CONTACT_TO_EMAIL",
    "CORS_ORIGINS",
    "GEMINI_API_KEY",
    "GEMINI_GROUNDING",
    "REPORT_GENERATOR",
)

BAD_VALUES = ("", "   ", "short", "not-a-boolean")


@pytest.fixture(autouse=True)
def _clear_settings_caches():
    """Settings are cached per process; a test that leaves one poisons the next."""
    get_settings.cache_clear()
    get_report_delivery_settings.cache_clear()
    yield
    get_settings.cache_clear()
    get_report_delivery_settings.cache_clear()


class TestNothingInTheEnvironmentCanStopTheApp:
    @pytest.mark.parametrize("name", VARIABLES)
    @pytest.mark.parametrize("value", BAD_VALUES)
    def test_health_answers_whatever_the_variable_says(
        self, monkeypatch: pytest.MonkeyPatch, name: str, value: str
    ) -> None:
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setenv(name, value)

        client = TestClient(create_app(settings=Settings()))

        assert client.get(HEALTH).status_code == 200

    def test_health_answers_with_everything_at_once_wrong(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # The realistic disaster: somebody saves the whole panel half-filled.
        for name in VARIABLES:
            monkeypatch.setenv(name, "")
        monkeypatch.setenv("APP_ENV", "production")

        client = TestClient(create_app(settings=Settings()))

        assert client.get(HEALTH).status_code == 200


class TestAWeakSecretDisablesRatherThanCrashes:
    """The security property is unchanged; only the mechanism is.

    A weak secret used to be a hard failure because it would sign tokens that
    authorise sending email and fetching third-party sites. With the flow
    disabled it signs nothing: the endpoints refuse before reaching any signing
    path. Disabling protects exactly as much, and leaves a service that can say
    which variable is wrong.
    """

    def test_a_short_secret_disables_the_flow_instead_of_raising(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Everything else configured, so the reason names the secret rather than
        # the variables that merely happen to be absent too.
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setenv("CONTACT_TOKEN_SECRET", "too-short")
        monkeypatch.setenv("RESEND_API_KEY", "re_x")
        monkeypatch.setenv("TURNSTILE_SECRET_KEY", "0x4real")
        monkeypatch.setenv("CONTACT_FROM_EMAIL", "noreply@code29.dev")
        monkeypatch.setenv("CONTACT_TO_EMAIL", "hola@code29.dev")

        settings = Settings()

        assert settings.contact_flow_enabled is False
        assert "CONTACT_TOKEN_SECRET" in (settings.contact_flow_disabled_reason or "")

    def test_no_route_issues_a_token_with_a_weak_secret(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # The assertion that carries the security argument: refused BEFORE
        # anything is signed, so the weak secret never authorises anything.
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setenv("CONTACT_TOKEN_SECRET", "too-short")
        monkeypatch.setenv("RESEND_API_KEY", "re_x")
        monkeypatch.setenv("TURNSTILE_SECRET_KEY", "0x4real")
        monkeypatch.setenv("CONTACT_FROM_EMAIL", "noreply@code29.dev")
        monkeypatch.setenv("CONTACT_TO_EMAIL", "hola@code29.dev")

        client = TestClient(create_app(settings=Settings()))

        turn = client.post("/api/v1/contact/conversation/turn", json={"message": "hola"})

        assert turn.status_code == 503
        assert "envelope" not in turn.json()

    def test_the_reason_never_travels_in_the_response(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Naming the variable to an anonymous caller is a configuration oracle.
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.setenv("CONTACT_TOKEN_SECRET", "too-short")

        client = TestClient(create_app(settings=Settings()))
        body = client.post(
            "/api/v1/contact/conversation/turn", json={"message": "hola"}
        ).text

        assert "CONTACT_TOKEN_SECRET" not in body


class TestEmptyMeansAbsent:
    def test_an_empty_boolean_is_the_default_not_an_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # A blank field in a dashboard is what "I have not set this" looks like.
        # It must not be distinguishable from the variable not being there.
        monkeypatch.setenv("GEMINI_GROUNDING", "")

        assert get_report_delivery_settings().gemini_grounding is False

    def test_a_real_boolean_still_works(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GEMINI_GROUNDING", "true")

        assert get_report_delivery_settings().gemini_grounding is True
