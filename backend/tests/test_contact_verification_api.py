"""Contract of the two verification endpoints.

POST /api/v1/contact/verification/request  — Turnstile, then email a code
POST /api/v1/contact/verification/confirm  — exchange a valid code for a token

These are the only doors into the flow, so the assertions here are mostly about
refusal: unconfigured deployment, failed challenge, wrong code, and no leaking of
whether an address exists.
"""

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.services.mailer import NullMailer
from app.services.tokens import derive_code, verify_access_token
from app.services.turnstile import TEST_SECRET_KEY as TURNSTILE_TEST_SECRET_KEY

SECRET = "x" * 40
EMAIL = "ada@example.com"

REQUEST_URL = "/api/v1/contact/verification/request"
CONFIRM_URL = "/api/v1/contact/verification/confirm"


def configured_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "contact_token_secret": SECRET,
        "resend_api_key": "re_test",
        "turnstile_secret_key": "ts_test",
        "contact_from_email": "noreply@code29.dev",
        "contact_to_email": "hola@code29.dev",
    }
    values.update(overrides)
    return Settings(**values)


class _Verifier:
    """Turnstile double: returns a fixed answer or raises."""

    def __init__(self, result: bool = True, error: Exception | None = None) -> None:
        self._result = result
        self._error = error

    async def verify(self, token: str, *, remote_ip: str | None) -> bool:
        if self._error:
            raise self._error
        return self._result


def build_client(
    *,
    settings: Settings | None = None,
    verifier: object | None = None,
    mailer: NullMailer | None = None,
) -> tuple[TestClient, NullMailer]:
    recorder = mailer or NullMailer()
    app = create_app(
        settings=settings or configured_settings(),
        turnstile_verifier=verifier or _Verifier(),
        mailer=recorder,
    )
    return TestClient(app), recorder


class TestRequestCode:
    def test_emails_a_code_and_never_returns_it(self) -> None:
        client, mailer = build_client()

        response = client.post(REQUEST_URL, json={"email": EMAIL, "turnstileToken": "t"})

        assert response.status_code == 202
        assert len(mailer.sent) == 1
        assert mailer.sent[0].to == [EMAIL]
        # The code must travel only by email — returning it would defeat verification.
        assert derive_code(EMAIL, secret=SECRET) not in response.text

    def test_the_email_carries_the_current_code(self) -> None:
        client, mailer = build_client()

        client.post(REQUEST_URL, json={"email": EMAIL, "turnstileToken": "t"})

        assert derive_code(EMAIL, secret=SECRET) in mailer.sent[0].text

    def test_the_test_secret_in_production_sends_nothing(self) -> None:
        # COD-49: production ran on Cloudflare's always-passing secret, so an
        # invented token reached the mailer. The endpoint must refuse before it.
        settings = configured_settings(
            app_env="production", turnstile_secret_key=TURNSTILE_TEST_SECRET_KEY
        )
        client, mailer = build_client(settings=settings, verifier=_Verifier(result=True))

        response = client.post(REQUEST_URL, json={"email": EMAIL, "turnstileToken": "made-up"})

        assert response.status_code == 503
        assert mailer.sent == []
        # The variable at fault belongs in the log, not in the answer: the
        # response must not tell an anonymous caller how this deploy is broken.
        assert "TURNSTILE_SECRET_KEY" not in response.text

    def test_a_failed_challenge_sends_nothing(self) -> None:
        client, mailer = build_client(verifier=_Verifier(result=False))

        response = client.post(REQUEST_URL, json={"email": EMAIL, "turnstileToken": "t"})

        assert response.status_code == 403
        assert mailer.sent == []

    def test_an_unavailable_challenge_sends_nothing(self) -> None:
        from app.services.turnstile import TurnstileUnavailable

        client, mailer = build_client(verifier=_Verifier(error=TurnstileUnavailable("down")))

        response = client.post(REQUEST_URL, json={"email": EMAIL, "turnstileToken": "t"})

        assert response.status_code == 503
        assert mailer.sent == []

    @pytest.mark.parametrize("bad", ["", "   ", "not-an-email", "a@b", "a@b.", "@example.com"])
    def test_rejects_an_invalid_address(self, bad: str) -> None:
        client, mailer = build_client()

        response = client.post(REQUEST_URL, json={"email": bad, "turnstileToken": "t"})

        assert response.status_code == 422
        assert mailer.sent == []

    def test_answers_503_when_the_flow_is_not_configured(self) -> None:
        client, mailer = build_client(settings=Settings(contact_token_secret=""))

        response = client.post(REQUEST_URL, json={"email": EMAIL, "turnstileToken": "t"})

        assert response.status_code == 503
        assert mailer.sent == []


class TestConfirmCode:
    def test_exchanges_a_valid_code_for_a_usable_token(self) -> None:
        client, _ = build_client()

        response = client.post(
            CONFIRM_URL, json={"email": EMAIL, "code": derive_code(EMAIL, secret=SECRET)}
        )

        assert response.status_code == 200
        token = response.json()["accessToken"]
        assert verify_access_token(token, secret=SECRET) == EMAIL

    def test_accepts_the_address_in_any_case(self) -> None:
        client, _ = build_client()

        response = client.post(
            CONFIRM_URL,
            json={"email": " ADA@Example.COM ", "code": derive_code(EMAIL, secret=SECRET)},
        )

        assert response.status_code == 200

    def test_rejects_a_wrong_code(self) -> None:
        client, _ = build_client()
        real = derive_code(EMAIL, secret=SECRET)
        wrong = str((int(real) + 1) % 10**6).zfill(6)

        response = client.post(CONFIRM_URL, json={"email": EMAIL, "code": wrong})

        assert response.status_code == 400
        assert "accessToken" not in response.text

    def test_rejects_another_addresss_code(self) -> None:
        client, _ = build_client()
        other = derive_code("eve@example.com", secret=SECRET)

        response = client.post(CONFIRM_URL, json={"email": EMAIL, "code": other})

        assert response.status_code == 400

    def test_refusal_does_not_reveal_whether_the_address_is_known(self) -> None:
        # Same shape for any refusal: the endpoint is not an address oracle.
        client, _ = build_client()

        first = client.post(CONFIRM_URL, json={"email": EMAIL, "code": "000001"})
        second = client.post(CONFIRM_URL, json={"email": "nobody@example.com", "code": "000001"})

        assert first.status_code == second.status_code == 400
        assert first.json() == second.json()
