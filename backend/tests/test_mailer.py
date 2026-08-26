"""The mail port, the Resend implementation, and the delivered report body.

Delivery is where the legal obligations live: the email must carry the consent
statement the visitor granted, the full transcript of what they told us, and a
UTC timestamp. Those cannot be reconstructed later — nothing is persisted — so
the email itself is the record.

No test performs network I/O: the Resend client is driven through an httpx
MockTransport.
"""

import asyncio
import json

import httpx
import pytest

from app.services.mailer import (
    EmailMessage,
    MailDeliveryError,
    NullMailer,
    ResendMailer,
    render_report_email,
)
from app.services.report import ReportFacts, SiteSignals, TemplateReportGenerator, WorkflowAnswers

FACTS = ReportFacts(
    contact_name="Ada Lovelace",
    company="ACME Logistics",
    locale="es",
    workflow=WorkflowAnswers(
        practices=["code_review"],
        team_size="6-15",
        notes="Deploys are manual and happen on Fridays.",
    ),
    site=SiteSignals(available=False, url="https://acme.example"),
)

TRANSCRIPT = [
    ("name", "Ada Lovelace"),
    ("company", "ACME Logistics"),
    ("email", "ada@example.com"),
    ("workflow", "Manual deploys, no monitoring"),
]

CONSENT = "I accept that my answers are used to produce this report and sent to me by email."


def report() -> object:
    return asyncio.run(TemplateReportGenerator().generate(FACTS))


def rendered() -> str:
    return render_report_email(
        report=report(),  # type: ignore[arg-type]
        transcript=TRANSCRIPT,
        consent_statement=CONSENT,
        generated_at="2026-08-22T10:15:00Z",
    )


class TestRenderedBody:
    def test_carries_the_summary(self) -> None:
        body = rendered()
        assert "ACME Logistics" in body
        assert "Ada Lovelace" in body

    def test_carries_every_recommendation_with_its_priority(self) -> None:
        body = rendered()
        for recommendation in report().recommendations:  # type: ignore[attr-defined]
            assert recommendation.action in body
            assert recommendation.priority.value.upper() in body

    def test_carries_the_full_transcript_verbatim(self) -> None:
        # A normalised summary is not enough: the visitor must be able to see
        # exactly what they told us.
        body = rendered()
        for _step, answer in TRANSCRIPT:
            assert answer in body

    def test_carries_the_consent_statement_and_a_utc_timestamp(self) -> None:
        body = rendered()
        assert CONSENT in body
        assert "2026-08-22T10:15:00Z" in body

    def test_states_which_generator_wrote_it(self) -> None:
        # A template-written report must not be passed off as model-written.
        assert "template" in rendered()


class TestNullMailer:
    def test_records_instead_of_sending(self) -> None:
        mailer = NullMailer()
        message = EmailMessage(to=["ada@example.com"], subject="Report", text="body")

        asyncio.run(mailer.send(message))

        assert mailer.sent == [message]


class TestResendMailer:
    def _mailer(self, handler: object) -> ResendMailer:
        transport = httpx.MockTransport(handler)  # type: ignore[arg-type]
        return ResendMailer(
            api_key="re_test_key",
            sender="noreply@code29.dev",
            transport=transport,
        )

    def test_posts_to_resend_with_the_api_key_and_sender(self) -> None:
        captured: dict[str, object] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["url"] = str(request.url)
            captured["auth"] = request.headers.get("authorization")
            captured["body"] = json.loads(request.content)
            return httpx.Response(200, json={"id": "email-1"})

        asyncio.run(
            self._mailer(handler).send(
                EmailMessage(to=["ada@example.com"], subject="Report", text="body")
            )
        )

        assert captured["url"] == "https://api.resend.com/emails"
        assert captured["auth"] == "Bearer re_test_key"
        assert captured["body"] == {
            "from": "noreply@code29.dev",
            "to": ["ada@example.com"],
            "subject": "Report",
            "text": "body",
        }

    def test_includes_reply_to_only_when_given(self) -> None:
        bodies: list[dict] = []

        def handler(request: httpx.Request) -> httpx.Response:
            bodies.append(json.loads(request.content))
            return httpx.Response(200, json={"id": "email-1"})

        mailer = self._mailer(handler)
        asyncio.run(mailer.send(EmailMessage(to=["a@example.com"], subject="s", text="t")))
        asyncio.run(
            mailer.send(
                EmailMessage(
                    to=["a@example.com"], subject="s", text="t", reply_to="ada@example.com"
                )
            )
        )

        assert "reply_to" not in bodies[0]
        assert bodies[1]["reply_to"] == "ada@example.com"

    def test_a_5xx_raises_a_delivery_error_naming_the_status(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(503, text="upstream unavailable")

        with pytest.raises(MailDeliveryError, match="503"):
            asyncio.run(
                self._mailer(handler).send(
                    EmailMessage(to=["ada@example.com"], subject="s", text="t")
                )
            )

    def test_a_transport_failure_raises_a_delivery_error(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectTimeout("timed out")

        with pytest.raises(MailDeliveryError):
            asyncio.run(
                self._mailer(handler).send(
                    EmailMessage(to=["ada@example.com"], subject="s", text="t")
                )
            )

    def test_the_error_message_does_not_leak_the_api_key(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, text="boom")

        with pytest.raises(MailDeliveryError) as error:
            asyncio.run(
                self._mailer(handler).send(
                    EmailMessage(to=["ada@example.com"], subject="s", text="t")
                )
            )

        assert "re_test_key" not in str(error.value)

    def test_the_error_message_does_not_leak_the_recipient(self) -> None:
        # Delivery errors surface in logs and in API responses; the address is PII.
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, text="boom")

        with pytest.raises(MailDeliveryError) as error:
            asyncio.run(
                self._mailer(handler).send(
                    EmailMessage(to=["ada@example.com"], subject="s", text="t")
                )
            )

        assert "ada@example.com" not in str(error.value)

    def test_the_error_message_carries_the_reason_resend_gave(self) -> None:
        """A 502 with no reason is a 502 nobody can act on.

        Resend answers a refused send with a typed JSON body: `name` says which
        rule was broken, `message` says how to fix it. Dropping it is what turned
        a misconfigured sender into an opaque "could not send".
        """

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                403,
                json={
                    "statusCode": 403,
                    "name": "validation_error",
                    "message": "The code29.dev domain is not verified.",
                },
            )

        with pytest.raises(MailDeliveryError) as error:
            asyncio.run(
                self._mailer(handler).send(
                    EmailMessage(to=["ada@example.com"], subject="s", text="t")
                )
            )

        message = str(error.value)
        assert "403" in message
        assert "validation_error" in message
        assert "The code29.dev domain is not verified." in message

    def test_the_reason_never_carries_the_recipient_back(self) -> None:
        """Resend echoes the payload in some errors, and the payload holds the address."""

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                422,
                json={
                    "name": "validation_error",
                    "message": "Invalid `to` field: ada@example.com is not allowed.",
                },
            )

        with pytest.raises(MailDeliveryError) as error:
            asyncio.run(
                self._mailer(handler).send(
                    EmailMessage(to=["ada@example.com"], subject="s", text="t")
                )
            )

        assert "ada@example.com" not in str(error.value)
        assert "validation_error" in str(error.value)

    def test_a_non_json_error_body_still_names_the_status(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(502, text="<html>gateway</html>")

        with pytest.raises(MailDeliveryError, match="502"):
            asyncio.run(
                self._mailer(handler).send(
                    EmailMessage(to=["ada@example.com"], subject="s", text="t")
                )
            )
