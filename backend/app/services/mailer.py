"""Outbound email: the port, the Resend implementation, and the report body.

Nothing about a lead is persisted, so the delivered email *is* the record. It
therefore carries the consent statement the visitor granted, the full transcript
of what they said, and a UTC timestamp — none of which can be reconstructed
afterwards.

Delivery errors never quote the API key or the recipient: they surface in logs
and in API responses, and the address is personal data.
"""

from __future__ import annotations

from typing import Protocol

import httpx
from pydantic import BaseModel, Field

from app.services.report import ContactReport

RESEND_ENDPOINT = "https://api.resend.com/emails"
REQUEST_TIMEOUT_SECONDS = 10.0


class MailDeliveryError(Exception):
    """Raised when the transport refuses or fails to accept a message."""


class EmailMessage(BaseModel):
    to: list[str] = Field(min_length=1)
    subject: str
    text: str
    reply_to: str | None = None


class Mailer(Protocol):
    """Port. Raises MailDeliveryError on failure; never swallows it."""

    async def send(self, message: EmailMessage) -> None: ...


class NullMailer:
    """Records messages instead of sending them. Used by tests and local runs."""

    def __init__(self) -> None:
        self.sent: list[EmailMessage] = []

    async def send(self, message: EmailMessage) -> None:
        self.sent.append(message)


class ResendMailer:
    """Sends through Resend's HTTP API.

    `transport` exists so tests can drive the real request-building code through
    httpx's MockTransport rather than mocking the method away.
    """

    def __init__(
        self,
        *,
        api_key: str,
        sender: str,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._api_key = api_key
        self._sender = sender
        self._transport = transport

    async def send(self, message: EmailMessage) -> None:
        payload: dict[str, object] = {
            "from": self._sender,
            "to": message.to,
            "subject": message.subject,
            "text": message.text,
        }
        if message.reply_to:
            payload["reply_to"] = message.reply_to

        try:
            async with httpx.AsyncClient(
                transport=self._transport, timeout=REQUEST_TIMEOUT_SECONDS
            ) as client:
                response = await client.post(
                    RESEND_ENDPOINT,
                    json=payload,
                    headers={"Authorization": f"Bearer {self._api_key}"},
                )
        except httpx.HTTPError as error:
            # Only the exception type: the message could contain the URL and the
            # request body, which carries the recipient.
            raise MailDeliveryError(
                f"mail transport failed ({type(error).__name__})"
            ) from error

        if response.is_error:
            raise MailDeliveryError(
                f"mail transport rejected the message with {response.status_code}"
            )


def render_report_email(
    *,
    report: ContactReport,
    transcript: list[tuple[str, str]],
    consent_statement: str,
    generated_at: str,
) -> str:
    """Plain-text report body. Deterministic given its inputs."""
    lines: list[str] = [
        report.title,
        "=" * len(report.title),
        "",
        report.summary,
        "",
        "DIAGNOSIS",
        "---------",
    ]

    for section in report.sections:
        lines.append("")
        lines.append(section.heading)
        lines.append(section.diagnosis)
        for item in section.evidence:
            lines.append(f"  - {item}")

    lines += ["", "WHAT TO DO NEXT", "---------------"]
    for index, recommendation in enumerate(report.recommendations, start=1):
        lines.append("")
        lines.append(f"{index}. [{recommendation.priority.value.upper()}] {recommendation.action}")
        lines.append(f"   Why: {recommendation.rationale}")
        lines.append(f"   Related service: {recommendation.service.value}")

    lines += ["", "YOUR ANSWERS", "------------"]
    for step_id, answer in transcript:
        lines.append(f"  {step_id}: {answer}")

    lines += [
        "",
        "CONSENT AND PROVENANCE",
        "----------------------",
        consent_statement,
        f"Generated at (UTC): {generated_at}",
        f"Written by: {report.generator}",
    ]

    return "\n".join(lines)
