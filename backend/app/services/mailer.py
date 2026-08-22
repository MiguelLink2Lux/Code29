"""Outbound email as a port, with a Resend adapter.

Kept behind a Protocol for two reasons: the whole contact flow can be exercised
in tests without sending a single real message, and a Resend outage surfaces as
`MailerUnavailable` — an explicit failure the endpoint can turn into a 502 —
rather than a report that quietly disappears.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

RESEND_URL = "https://api.resend.com/emails"
SEND_TIMEOUT_SECONDS = 10.0


class MailerUnavailable(Exception):
    """Delivery failed. Never carries credentials: exceptions end up in logs."""


@dataclass(frozen=True)
class EmailMessage:
    to: str
    subject: str
    text_body: str
    reply_to: str | None = None


@runtime_checkable
class Mailer(Protocol):
    """Port: something that can deliver an EmailMessage."""

    async def send(self, message: EmailMessage) -> None: ...


class _PostClient(Protocol):
    """The slice of an HTTP client this module needs (httpx.AsyncClient fits)."""

    async def post(
        self, url: str, json: dict, headers: dict, timeout: float | None = None
    ) -> object: ...


class ResendMailer:
    """Delivers through the Resend HTTP API."""

    def __init__(self, *, api_key: str, sender: str, client: _PostClient) -> None:
        self._api_key = api_key
        self._sender = sender
        self._client = client

    async def send(self, message: EmailMessage) -> None:
        payload: dict[str, object] = {
            "from": self._sender,
            "to": [message.to],
            "subject": message.subject,
            "text": message.text_body,
        }
        if message.reply_to:
            payload["reply_to"] = message.reply_to

        try:
            response = await self._client.post(
                RESEND_URL,
                json=payload,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                timeout=SEND_TIMEOUT_SECONDS,
            )
        except Exception as error:  # noqa: BLE001 — any transport failure is a delivery failure
            # Deliberately not chaining the original message into the text: it can
            # contain the request, and the request carries the Authorization header.
            raise MailerUnavailable("could not reach the email provider") from error

        status = getattr(response, "status_code", None)
        if status != 200:
            raise MailerUnavailable(f"email provider rejected the message (status {status})")


@dataclass
class RecordingMailer:
    """Test double that keeps what it was asked to send."""

    sent: list[EmailMessage] = field(default_factory=list)

    async def send(self, message: EmailMessage) -> None:
        self.sent.append(message)
