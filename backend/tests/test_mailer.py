"""Outbound email: the Resend adapter and its contract.

The mailer is a port so the flow can be tested end to end without sending a
single real email, and so a Resend outage surfaces as a typed failure instead of
a silent loss.
"""

import pytest

from app.services.mailer import (
    EmailMessage,
    MailerUnavailable,
    RecordingMailer,
    ResendMailer,
)


class _FakeResponse:
    def __init__(self, status_code: int = 200, text: str = "{}") -> None:
        self.status_code = status_code
        self.text = text


class _FakeClient:
    def __init__(self, response: object = None, error: Exception | None = None) -> None:
        self._response = response
        self._error = error
        self.calls: list[dict] = []

    async def post(
        self, url: str, json: dict, headers: dict, timeout: float | None = None
    ) -> object:
        self.calls.append({"url": url, "json": json, "headers": headers})
        if self._error:
            raise self._error
        return self._response


MESSAGE = EmailMessage(
    to="ada@example.com",
    subject="Your report",
    text_body="Plain text body",
)


@pytest.mark.anyio
class TestResendMailer:
    async def test_sends_with_bearer_auth_and_the_configured_sender(self) -> None:
        client = _FakeClient(_FakeResponse())
        mailer = ResendMailer(api_key="re_key", sender="noreply@code29.dev", client=client)

        await mailer.send(MESSAGE)

        call = client.calls[0]
        assert call["headers"]["Authorization"] == "Bearer re_key"
        assert call["json"]["from"] == "noreply@code29.dev"
        assert call["json"]["to"] == ["ada@example.com"]
        assert call["json"]["subject"] == "Your report"

    async def test_raises_on_a_rejected_send(self) -> None:
        client = _FakeClient(_FakeResponse(status_code=422, text="invalid sender"))
        mailer = ResendMailer(api_key="re_key", sender="noreply@code29.dev", client=client)

        with pytest.raises(MailerUnavailable):
            await mailer.send(MESSAGE)

    async def test_raises_when_resend_is_unreachable(self) -> None:
        client = _FakeClient(error=RuntimeError("timeout"))
        mailer = ResendMailer(api_key="re_key", sender="noreply@code29.dev", client=client)

        with pytest.raises(MailerUnavailable):
            await mailer.send(MESSAGE)

    async def test_never_puts_the_api_key_in_the_exception(self) -> None:
        # Exceptions get logged; a leaked key in a log is a leaked key.
        client = _FakeClient(_FakeResponse(status_code=500, text="server error"))
        mailer = ResendMailer(api_key="re_supersecret", sender="noreply@code29.dev", client=client)

        with pytest.raises(MailerUnavailable) as error:
            await mailer.send(MESSAGE)

        assert "re_supersecret" not in str(error.value)


@pytest.mark.anyio
async def test_recording_mailer_captures_messages_for_assertions() -> None:
    mailer = RecordingMailer()

    await mailer.send(MESSAGE)

    assert mailer.sent == [MESSAGE]
