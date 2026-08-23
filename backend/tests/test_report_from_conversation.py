"""The report request that closes the conversation.

Without this the refactor is a regression: the chat would gather five facts,
say it was done, and deliver nothing — while the questionnaire it replaces did
send an email.

The facts come from the signed envelope, never from the request body. A client
that could post its own facts could put any company in a report we sign our name
to.
"""

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.report_settings import get_report_delivery_settings
from app.main import create_app
from app.services.conversation import ConversationFacts, seal_envelope
from app.services.mailer import NullMailer
from app.services.tokens import issue_access_token

SECRET = "report-from-conversation-secret-32ch!!!"
EMAIL = "ada@example.com"
URL = "/api/v1/contact/report"

COMPLETE = ConversationFacts(
    contact_name="Ada Lovelace",
    company="Analytical Engines",
    website="analyticalengines.example",
    team="tres personas, sin CI",
)


@pytest.fixture(autouse=True)
def _configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CONTACT_TOKEN_SECRET", SECRET)
    monkeypatch.setenv("RESEND_API_KEY", "re_test")
    monkeypatch.setenv("CONTACT_FROM_EMAIL", "noreply@code29.dev")
    monkeypatch.setenv("CONTACT_TO_EMAIL", "hola@code29.dev")
    monkeypatch.setenv("REPORT_GENERATOR", "stub")
    get_report_delivery_settings.cache_clear()
    yield
    get_report_delivery_settings.cache_clear()


def build() -> tuple[TestClient, NullMailer]:
    mailer = NullMailer()
    app = create_app(
        settings=Settings(
            contact_token_secret=SECRET,
            resend_api_key="re_test",
            turnstile_secret_key="ts_test",
            contact_from_email="noreply@code29.dev",
            contact_to_email="hola@code29.dev",
        ),
        mailer=mailer,
    )
    return TestClient(app), mailer


def token() -> str:
    return issue_access_token(EMAIL, secret=SECRET)


def envelope(facts: ConversationFacts = COMPLETE, turns: int = 5) -> str:
    return seal_envelope(facts, turns=turns, secret=SECRET)


class TestHappyPath:
    def test_an_envelope_and_a_verified_token_produce_a_report(self) -> None:
        client, mailer = build()

        response = client.post(
            URL,
            json={
                "envelope": envelope(),
                "consent": {"privacy_accepted": True, "report_accepted": True},
            },
            headers={"Authorization": f"Bearer {token()}"},
        )

        assert response.status_code in {200, 202}, response.text
        assert len(mailer.sent) >= 1

    def test_the_report_goes_to_the_verified_address(self) -> None:
        client, mailer = build()

        client.post(
            URL,
            json={
                "envelope": envelope(),
                "consent": {"privacy_accepted": True, "report_accepted": True},
            },
            headers={"Authorization": f"Bearer {token()}"},
        )

        recipients = [address for message in mailer.sent for address in message.to]
        assert EMAIL in recipients


class TestFactsComeFromTheEnvelope:
    def test_a_company_posted_in_the_body_is_ignored(self) -> None:
        client, mailer = build()

        client.post(
            URL,
            json={
                "envelope": envelope(),
                "contact_name": "Impostor",
                "company": "Not Their Company",
                "consent": {"privacy_accepted": True, "report_accepted": True},
            },
            headers={"Authorization": f"Bearer {token()}"},
        )

        body = "\n".join(message.text for message in mailer.sent)
        assert "Not Their Company" not in body
        assert "Analytical Engines" in body

    def test_a_tampered_envelope_is_refused(self) -> None:
        client, mailer = build()
        payload, signature = envelope().split(".", 1)

        response = client.post(
            URL,
            json={
                "envelope": f"{payload}x.{signature}",
                "consent": {"privacy_accepted": True, "report_accepted": True},
            },
            headers={"Authorization": f"Bearer {token()}"},
        )

        assert response.status_code == 401
        assert mailer.sent == []


class TestRefusals:
    def test_no_token_means_no_report(self) -> None:
        client, mailer = build()

        response = client.post(
            URL,
            json={
                "envelope": envelope(),
                "consent": {"privacy_accepted": True, "report_accepted": True},
            },
        )

        assert response.status_code == 401
        assert mailer.sent == []

    def test_consent_is_required(self) -> None:
        client, mailer = build()

        response = client.post(
            URL,
            json={
                "envelope": envelope(),
                "consent": {"privacy_accepted": False, "report_accepted": False},
            },
            headers={"Authorization": f"Bearer {token()}"},
        )

        assert response.status_code == 400
        assert mailer.sent == []


class TestEmailBody:
    """What the lead actually receives."""

    @staticmethod
    def _report():
        import asyncio

        from app.services.canon_report import TemplateCanonGenerator
        from app.services.report import SiteSignals

        return asyncio.run(
            TemplateCanonGenerator().generate(
                contact_name="Ada",
                company="Analytical Engines",
                locale="es",
                team="tres personas",
                site=SiteSignals(available=False),
            )
        )

    def test_the_body_lists_all_ten_points(self) -> None:
        from app.services.mailer import render_canon_email

        body = render_canon_email(
            report=self._report(),
            consent_statement="consentimiento otorgado",
            generated_at="2026-08-23T12:00:00Z",
        )

        for number in range(1, 11):
            assert f"{number}." in body, f"point {number} missing from the email"

    def test_the_body_closes_on_the_single_proposal(self) -> None:
        from app.services.mailer import render_canon_email

        report = self._report()
        body = render_canon_email(
            report=report,
            consent_statement="consentimiento otorgado",
            generated_at="2026-08-23T12:00:00Z",
        )

        assert report.proposal.headline in body
        for part in report.proposal.parts:
            assert part in body

    def test_the_body_records_consent_and_when(self) -> None:
        # Nothing is persisted: the delivered email IS the record (ADR 0006).
        from app.services.mailer import render_canon_email

        body = render_canon_email(
            report=self._report(),
            consent_statement="consentimiento otorgado el 2026-08-23",
            generated_at="2026-08-23T12:00:00Z",
        )

        assert "consentimiento otorgado el 2026-08-23" in body
        assert "2026-08-23T12:00:00Z" in body

    def test_the_body_names_which_generator_wrote_it(self) -> None:
        # A template and a model are not interchangeable to whoever reads it.
        from app.services.mailer import render_canon_email

        report = self._report()
        body = render_canon_email(
            report=report, consent_statement="c", generated_at="2026-08-23T12:00:00Z"
        )

        assert report.generator in body
