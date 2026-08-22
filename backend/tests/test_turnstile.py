"""Turnstile is the gate that stops the code endpoint being an email amplifier.

The endpoint can send mail to any address a caller names, and the stateless
design has no per-address counter, so a human-verification challenge is what
keeps automated abuse out. These tests assert the verifier's contract and, above
all, that it FAILS CLOSED.
"""

import pytest

from app.services.turnstile import (
    AlwaysPassVerifier,
    HttpTurnstileVerifier,
    TurnstileUnavailable,
)


class _FakeResponse:
    def __init__(self, payload: dict, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def json(self) -> dict:
        return self._payload


class _FakeClient:
    """Minimal stand-in for httpx.AsyncClient.post."""

    def __init__(self, response: object = None, error: Exception | None = None) -> None:
        self._response = response
        self._error = error
        self.calls: list[dict] = []

    async def post(self, url: str, data: dict, timeout: float | None = None) -> object:
        self.calls.append({"url": url, "data": data, "timeout": timeout})
        if self._error:
            raise self._error
        return self._response


@pytest.mark.anyio
class TestHttpTurnstileVerifier:
    async def test_accepts_a_successful_challenge(self) -> None:
        client = _FakeClient(_FakeResponse({"success": True}))
        verifier = HttpTurnstileVerifier(secret="secret", client=client)

        assert await verifier.verify("token", remote_ip="203.0.113.7") is True

    async def test_sends_the_secret_and_the_token(self) -> None:
        client = _FakeClient(_FakeResponse({"success": True}))
        verifier = HttpTurnstileVerifier(secret="s3cr3t", client=client)

        await verifier.verify("the-token", remote_ip=None)

        sent = client.calls[0]["data"]
        assert sent["secret"] == "s3cr3t"
        assert sent["response"] == "the-token"

    async def test_rejects_a_failed_challenge(self) -> None:
        client = _FakeClient(_FakeResponse({"success": False, "error-codes": ["invalid-input"]}))
        verifier = HttpTurnstileVerifier(secret="secret", client=client)

        assert await verifier.verify("token", remote_ip=None) is False

    async def test_rejects_an_empty_token_without_calling_cloudflare(self) -> None:
        client = _FakeClient(_FakeResponse({"success": True}))
        verifier = HttpTurnstileVerifier(secret="secret", client=client)

        assert await verifier.verify("   ", remote_ip=None) is False
        assert client.calls == []

    async def test_fails_closed_when_cloudflare_is_unreachable(self) -> None:
        # An outage must not silently open the gate.
        client = _FakeClient(error=RuntimeError("connection reset"))
        verifier = HttpTurnstileVerifier(secret="secret", client=client)

        with pytest.raises(TurnstileUnavailable):
            await verifier.verify("token", remote_ip=None)

    async def test_fails_closed_on_a_non_200_response(self) -> None:
        client = _FakeClient(_FakeResponse({}, status_code=500))
        verifier = HttpTurnstileVerifier(secret="secret", client=client)

        with pytest.raises(TurnstileUnavailable):
            await verifier.verify("token", remote_ip=None)

    async def test_fails_closed_on_an_unparseable_body(self) -> None:
        class _Broken(_FakeResponse):
            def json(self) -> dict:
                raise ValueError("not json")

        verifier = HttpTurnstileVerifier(secret="secret", client=_FakeClient(_Broken({})))

        with pytest.raises(TurnstileUnavailable):
            await verifier.verify("token", remote_ip=None)


@pytest.mark.anyio
async def test_always_pass_verifier_is_for_tests_and_local_only() -> None:
    # Explicit test double, so no production path can accidentally bypass the gate.
    assert await AlwaysPassVerifier().verify("anything", remote_ip=None) is True
