"""Stateless email verification: derived codes and signed access tokens.

Nothing is stored. A verification code is *derived* from the address, a time
bucket and a purpose using HMAC-SHA256, so the server recomputes and compares it
instead of persisting it. Once an address is verified, the caller receives a
signed access token that authorises the expensive steps (site analysis, report
delivery) — the token, never the client's own claim, is what grants that right.

Trade-off accepted by decision: a code cannot be revoked before its window
expires, and single-use cannot be enforced without a store. See ADR 0006.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time

# A code stays valid for its own bucket and the previous one, so a visitor who
# receives it a second before the boundary is not rejected: 10-20 minutes.
CODE_BUCKET_SECONDS = 600
CODE_PURPOSE = "email-verification"
CODE_LENGTH = 6

ACCESS_TOKEN_TTL_SECONDS = 1800
ACCESS_TOKEN_PURPOSE = "contact-report"


class InvalidToken(Exception):
    """Raised when an access token is malformed, forged, or expired."""


def normalize_email(email: str) -> str:
    """Lowercased and stripped: what the visitor types must not change the code."""
    return email.strip().lower()


def _sign(message: bytes, secret: str) -> bytes:
    return hmac.new(secret.encode("utf-8"), message, hashlib.sha256).digest()


def _bucket(at: float | None, offset: int = 0) -> int:
    now = time.time() if at is None else at
    return int(now // CODE_BUCKET_SECONDS) - offset


def derive_code(email: str, *, secret: str, at: float | None = None) -> str:
    """Deterministic 6-digit code for an address within the current time bucket."""
    message = f"{normalize_email(email)}|{_bucket(at)}|{CODE_PURPOSE}".encode()
    digest = _sign(message, secret)

    # Fold the digest into a fixed-width decimal code.
    return str(int.from_bytes(digest[:8], "big") % 10**CODE_LENGTH).zfill(CODE_LENGTH)


def verify_code(email: str, candidate: str, *, secret: str, at: float | None = None) -> bool:
    """True when `candidate` matches the code for this address, current or previous bucket."""
    candidate = candidate.strip()

    if len(candidate) != CODE_LENGTH or not candidate.isdigit():
        return False

    now = time.time() if at is None else at

    for offset in (0, 1):
        expected_bucket = _bucket(now, offset)
        message = f"{normalize_email(email)}|{expected_bucket}|{CODE_PURPOSE}".encode()
        digest = _sign(message, secret)
        expected = str(int.from_bytes(digest[:8], "big") % 10**CODE_LENGTH).zfill(CODE_LENGTH)

        # compare_digest: constant time, so a wrong code leaks no positional hint.
        if hmac.compare_digest(expected, candidate):
            return True

    return False


def _b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def issue_access_token(email: str, *, secret: str, at: float | None = None) -> str:
    """Signed proof that `email` was verified. Format: base64(payload).base64(signature)."""
    issued_at = time.time() if at is None else at
    payload = {
        "email": normalize_email(email),
        "exp": int(issued_at + ACCESS_TOKEN_TTL_SECONDS),
        "purpose": ACCESS_TOKEN_PURPOSE,
    }
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")

    return f"{_b64encode(raw)}.{_b64encode(_sign(raw, secret))}"


def verify_access_token(token: str, *, secret: str, at: float | None = None) -> str:
    """Return the verified address, or raise InvalidToken. Never raises anything else."""
    try:
        encoded_payload, encoded_signature = token.split(".")
        raw = _b64decode(encoded_payload)
        signature = _b64decode(encoded_signature)
    except (ValueError, TypeError, base64.binascii.Error) as error:
        raise InvalidToken("malformed token") from error

    if not hmac.compare_digest(_sign(raw, secret), signature):
        raise InvalidToken("bad signature")

    try:
        payload = json.loads(raw)
        email = str(payload["email"])
        expires_at = int(payload["exp"])
        purpose = str(payload["purpose"])
    except (ValueError, KeyError, TypeError) as error:
        raise InvalidToken("malformed payload") from error

    if purpose != ACCESS_TOKEN_PURPOSE:
        raise InvalidToken("wrong purpose")

    now = time.time() if at is None else at
    if expires_at < now:
        raise InvalidToken("expired")

    return email
