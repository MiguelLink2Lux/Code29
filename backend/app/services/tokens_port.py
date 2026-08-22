"""Port for verifying an email-verification token.

The token *service* (HMAC signing, expiry, purpose) ships in the verification
phase. This module is only the seam the report endpoint depends on, so the two
can land in either order: the default adapter resolves the real implementation
lazily and reports a clear, mappable error when it is not there yet.
"""

from __future__ import annotations

from typing import Protocol


class InvalidVerificationToken(Exception):
    """The token is missing, malformed, forged, expired, or for another purpose."""


class VerificationUnavailable(Exception):
    """The token service is not wired up — a configuration fault, not a bad token."""


class TokenVerifier(Protocol):
    """Returns the verified address, or raises InvalidVerificationToken."""

    def __call__(self, token: str) -> str: ...


def build_token_verifier(secret: str) -> TokenVerifier:
    """Adapter over the HMAC token service.

    Imported inside the closure on purpose: this module must import cleanly
    before the token service exists, so the endpoint can be developed, tested
    and reviewed independently of it.
    """

    def verify(token: str) -> str:
        try:
            from app.services import tokens as token_service
        except ImportError as error:  # pragma: no cover - depends on merge order
            raise VerificationUnavailable("token service is not installed") from error

        verify_access_token = getattr(token_service, "verify_access_token", None)
        invalid_token = getattr(token_service, "InvalidToken", Exception)

        if verify_access_token is None:  # pragma: no cover - depends on merge order
            raise VerificationUnavailable("token service exposes no verify_access_token")

        try:
            return str(verify_access_token(token, secret=secret))
        except invalid_token as error:
            raise InvalidVerificationToken("token rejected") from error

    return verify
