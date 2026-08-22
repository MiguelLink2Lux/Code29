"""POST /api/v1/contact/report — the gate, the failure contracts, the delivery.

The rule the whole flow rests on: the *verification token*, never anything in
the request body, is what authorises generating a report and sending email. A
caller without a valid token must not cause an outbound email or an outbound
HTTP request of any kind.

Every collaborator is injected, so these tests exercise the real routing,
validation and error mapping with no network and no key.
"""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.api.v1.contact_report import (
    ReportDeliveryUnavailable,
    get_mailer,
    get_report_generator,
    get_settings,
    get_site_analyzer,
    get_token_verifier,
)
from app.core.report_settings import ReportDeliverySettings, get_report_delivery_settings
from app.main import create_app
from app.services.mailer import MailDeliveryError, NullMailer
from app.services.report import SiteSignals, TemplateReportGenerator
from app.services.tokens_port import InvalidVerificationToken

VERIFIED_EMAIL = "ada@example.com"
GOOD_TOKEN = "good-token"

PAYLOAD = {
    "contact_name": "Ada Lovelace",
    "company": "ACME Logistics",
    "locale": "es",
    "workflow": {
        "practices": ["code_review"],
        "team_size": "6-15",
        "notes": "Deploys are manual and happen on Fridays.",
    },
    "site_url": "https://acme.example",
    "transcript": [
        {"step_id": "name", "answer": "Ada Lovelace"},
        {"step_id": "workflow", "answer": "Manual deploys"},
    ],
    "consent": {"privacy_accepted": True, "report_accepted": True},
}


def stub_verifier(token: str) -> str:
    if token != GOOD_TOKEN:
        raise InvalidVerificationToken("bad token")
    return VERIFIED_EMAIL


async def unavailable_site(url: str | None) -> SiteSignals:
    """Stands in for phase B's analyser: no network in tests."""
    return SiteSignals(available=False, url=url)


@pytest.fixture
def mailer() -> NullMailer:
    return NullMailer()


CONFIGURED = ReportDeliverySettings(
    report_generator="stub",
    resend_api_key="re_test_key",
    contact_from_email="noreply@code29.dev",
    contact_to_email="hola@code29.dev",
    verification_secret="x" * 32,
)


@pytest.fixture
def client(mailer: NullMailer) -> Iterator[TestClient]:
    app = create_app()
    # A fully configured deployment: the owner copy needs CONTACT_TO_EMAIL, and
    # relying on the ambient environment would make these tests machine-dependent.
    app.dependency_overrides[get_settings] = lambda: CONFIGURED
    app.dependency_overrides[get_token_verifier] = lambda: stub_verifier
    app.dependency_overrides[get_mailer] = lambda: mailer
    app.dependency_overrides[get_report_generator] = TemplateReportGenerator
    app.dependency_overrides[get_site_analyzer] = lambda: unavailable_site

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def post(client: TestClient, token: str | None = GOOD_TOKEN, **overrides: object) -> object:
    payload = {**PAYLOAD, **overrides}
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    return client.post("/api/v1/contact/report", json=payload, headers=headers)


class TestVerifiedTokenGate:
    def test_no_token_is_rejected_and_nothing_is_sent(
        self, client: TestClient, mailer: NullMailer
    ) -> None:
        response = post(client, token=None)

        assert response.status_code == 401
        assert mailer.sent == []

    def test_a_bad_token_is_rejected(self, client: TestClient, mailer: NullMailer) -> None:
        response = post(client, token="forged")

        assert response.status_code == 401
        assert mailer.sent == []

    def test_a_non_bearer_scheme_is_rejected(
        self, client: TestClient, mailer: NullMailer
    ) -> None:
        response = client.post(
            "/api/v1/contact/report",
            json=PAYLOAD,
            headers={"Authorization": f"Basic {GOOD_TOKEN}"},
        )

        assert response.status_code == 401
        assert mailer.sent == []

    def test_the_error_body_does_not_echo_the_token(self, client: TestClient) -> None:
        response = post(client, token="forged-secret-value")

        assert "forged-secret-value" not in response.text


class TestConsent:
    def test_a_refused_report_consent_is_rejected(
        self, client: TestClient, mailer: NullMailer
    ) -> None:
        response = post(
            client, consent={"privacy_accepted": True, "report_accepted": False}
        )

        assert response.status_code == 400
        assert mailer.sent == []

    def test_a_refused_privacy_consent_is_rejected(
        self, client: TestClient, mailer: NullMailer
    ) -> None:
        response = post(
            client, consent={"privacy_accepted": False, "report_accepted": True}
        )

        assert response.status_code == 400
        assert mailer.sent == []

    def test_a_malformed_body_is_rejected_before_any_work(
        self, client: TestClient, mailer: NullMailer
    ) -> None:
        response = client.post(
            "/api/v1/contact/report",
            json={"company": "ACME"},
            headers={"Authorization": f"Bearer {GOOD_TOKEN}"},
        )

        # Schema-level rejection is FastAPI's 422; semantic rejection is our 400.
        assert response.status_code == 422
        assert mailer.sent == []


class TestDelivery:
    def test_the_happy_path_mails_the_visitor_and_the_owner(
        self, client: TestClient, mailer: NullMailer
    ) -> None:
        response = post(client)

        assert response.status_code == 200
        assert len(mailer.sent) == 2

        recipients = [message.to for message in mailer.sent]
        assert [VERIFIED_EMAIL] in recipients

    def test_the_report_goes_to_the_verified_address_not_a_body_field(
        self, client: TestClient, mailer: NullMailer
    ) -> None:
        # A body claiming another address must not redirect the report.
        post(client, contact_name="Ada", email="attacker@example.com")

        visitor_message = mailer.sent[0]
        assert visitor_message.to == [VERIFIED_EMAIL]

    def test_the_owner_copy_can_be_replied_to_directly(
        self, client: TestClient, mailer: NullMailer
    ) -> None:
        post(client)

        owner_copy = mailer.sent[1]
        assert owner_copy.reply_to == VERIFIED_EMAIL

    def test_the_delivered_body_carries_consent_transcript_and_timestamp(
        self, client: TestClient, mailer: NullMailer
    ) -> None:
        post(client)
        body = mailer.sent[0].text

        assert "Manual deploys" in body
        assert "CONSENT AND PROVENANCE" in body
        assert "Generated at (UTC):" in body

    def test_the_response_confirms_without_resending_the_whole_report(
        self, client: TestClient
    ) -> None:
        payload = post(client).json()

        assert payload["delivered"] is True
        assert payload["recommendation_count"] > 0
        assert "ACME Logistics" in payload["title"]


class TestFailureContainment:
    def test_a_generator_failure_is_502_and_mails_nothing(
        self, client: TestClient, mailer: NullMailer
    ) -> None:
        class Exploding:
            async def generate(self, facts: object) -> object:
                raise RuntimeError("model exploded")

        client.app.dependency_overrides[get_report_generator] = Exploding  # type: ignore[attr-defined]

        response = post(client)

        assert response.status_code == 502
        assert mailer.sent == []

    def test_a_mail_failure_is_502_and_says_so(self, client: TestClient) -> None:
        class Failing:
            async def send(self, message: object) -> None:
                raise MailDeliveryError("mail transport rejected the message with 503")

        client.app.dependency_overrides[get_mailer] = Failing  # type: ignore[attr-defined]

        response = post(client)

        assert response.status_code == 502
        assert "retry" in response.text.lower()

    def test_an_unconfigured_flow_is_503(self, client: TestClient, mailer: NullMailer) -> None:
        def unavailable() -> None:
            raise ReportDeliveryUnavailable("RESEND_API_KEY is not set")

        client.app.dependency_overrides[get_mailer] = unavailable  # type: ignore[attr-defined]

        response = post(client)

        assert response.status_code == 503
        assert mailer.sent == []

    def test_an_analysis_failure_degrades_instead_of_failing(
        self, client: TestClient, mailer: NullMailer
    ) -> None:
        async def exploding_analyzer(url: str | None) -> SiteSignals:
            raise TimeoutError("site timed out")

        client.app.dependency_overrides[get_site_analyzer] = lambda: exploding_analyzer  # type: ignore[attr-defined]

        response = post(client)

        # The report is the product; a site we could not read must not lose it.
        assert response.status_code == 200
        assert len(mailer.sent) == 2


class TestUnconfiguredDeployment:
    """The state the backend is actually deployed in today: nothing configured."""

    def test_the_endpoint_answers_503_rather_than_crashing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        for variable in [
            "RESEND_API_KEY",
            "CONTACT_FROM_EMAIL",
            "CONTACT_TO_EMAIL",
            "CONTACT_TOKEN_SECRET",
            "EMAIL_VERIFICATION_SECRET",
        ]:
            monkeypatch.delenv(variable, raising=False)
        get_report_delivery_settings.cache_clear()

        with TestClient(create_app()) as bare_client:
            response = bare_client.post(
                "/api/v1/contact/report",
                json=PAYLOAD,
                headers={"Authorization": "Bearer whatever"},
            )

        get_report_delivery_settings.cache_clear()

        assert response.status_code == 503
        # The operator must be told which variable is missing.
        assert "CONTACT_TOKEN_SECRET" in response.json()["detail"]

    def test_health_still_answers_with_the_contact_router_mounted(self) -> None:
        with TestClient(create_app()) as bare_client:
            assert bare_client.get("/api/v1/health").status_code == 200
