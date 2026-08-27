"""Cloudflare Turnstile verification — the human gate before any email is sent.

The verification-code endpoint can send mail to any address a caller names, and
the stateless design (no store) has no per-address counter, so this challenge is
what stops the endpoint being an email amplifier.

Everything here **fails closed**: an outage, a non-200 response or an unparseable
body raises `TurnstileUnavailable` rather than returning a permissive default.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
VERIFY_TIMEOUT_SECONDS = 5.0

#: Cloudflare's always-passing secret. It approves every token by design, which
#: is what a preview deployment wants — those live on `*.vercel.app`, a hostname
#: no widget can claim — and what production must never run: here it would turn
#: the only limit on an endpoint that mails a code to any address into a no-op.
#: `Settings.contact_flow_enabled` reads this to refuse the pairing.
TEST_SECRET_KEY = "1x0000000000000000000000000000000AA"


class TurnstileUnavailable(Exception):
    """The challenge could not be evaluated. Callers must treat this as a refusal."""


@runtime_checkable
class TurnstileVerifier(Protocol):
    """Port: something that can decide whether a challenge token is valid."""

    async def verify(self, token: str, *, remote_ip: str | None) -> bool: ...


class _PostClient(Protocol):
    """The slice of an HTTP client this module needs (httpx.AsyncClient fits)."""

    async def post(self, url: str, data: dict, timeout: float | None = None) -> object: ...


class HttpTurnstileVerifier:
    """Verifies against Cloudflare's siteverify endpoint."""

    def __init__(self, *, secret: str, client: _PostClient) -> None:
        self._secret = secret
        self._client = client

    async def verify(self, token: str, *, remote_ip: str | None) -> bool:
        if not token or not token.strip():
            # No round trip for an obviously absent challenge.
            return False

        payload = {"secret": self._secret, "response": token.strip()}
        if remote_ip:
            payload["remoteip"] = remote_ip

        try:
            response = await self._client.post(
                VERIFY_URL, data=payload, timeout=VERIFY_TIMEOUT_SECONDS
            )
        except Exception as error:  # noqa: BLE001 — any transport failure is a refusal
            raise TurnstileUnavailable("could not reach Turnstile") from error

        if getattr(response, "status_code", None) != 200:
            raise TurnstileUnavailable("unexpected status from Turnstile")

        try:
            body = response.json()
        except Exception as error:  # noqa: BLE001 — an unreadable body is a refusal
            raise TurnstileUnavailable("unreadable Turnstile response") from error

        return bool(body.get("success", False))


class AlwaysPassVerifier:
    """Test double. Never wired into a production path: the factory requires a secret."""

    async def verify(self, token: str, *, remote_ip: str | None) -> bool:
        return True
