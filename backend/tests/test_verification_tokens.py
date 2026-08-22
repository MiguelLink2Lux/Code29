"""Stateless email verification: derived codes and signed access tokens.

Nothing is persisted. A code is derived from (email, time bucket, purpose) with
HMAC, so the server can recompute and compare it without storing anything; an
access token is a signed payload proving an address was verified.

The security properties asserted here are the whole point of the design, so they
are tested directly rather than through the endpoints.
"""

import time

import pytest

from app.services.tokens import (
    InvalidToken,
    derive_code,
    issue_access_token,
    verify_access_token,
    verify_code,
)

SECRET = "test-secret-at-least-32-characters-long!!"
EMAIL = "ada@example.com"


class TestDeriveCode:
    def test_is_six_digits(self) -> None:
        code = derive_code(EMAIL, secret=SECRET)
        assert len(code) == 6
        assert code.isdigit()

    def test_is_stable_within_the_same_time_bucket(self) -> None:
        assert derive_code(EMAIL, secret=SECRET) == derive_code(EMAIL, secret=SECRET)

    def test_differs_per_email(self) -> None:
        assert derive_code(EMAIL, secret=SECRET) != derive_code("eve@example.com", secret=SECRET)

    def test_differs_per_secret(self) -> None:
        assert derive_code(EMAIL, secret=SECRET) != derive_code(EMAIL, secret=SECRET + "x")

    def test_is_case_and_space_insensitive_on_the_email(self) -> None:
        # The address the visitor types must not change the code.
        assert derive_code("  ADA@Example.com ", secret=SECRET) == derive_code(EMAIL, secret=SECRET)


class TestVerifyCode:
    def test_accepts_the_current_code(self) -> None:
        assert verify_code(EMAIL, derive_code(EMAIL, secret=SECRET), secret=SECRET) is True

    def test_accepts_the_previous_bucket_so_a_boundary_does_not_break_a_valid_code(self) -> None:
        now = time.time()
        previous = derive_code(EMAIL, secret=SECRET, at=now - 601)
        assert verify_code(EMAIL, previous, secret=SECRET, at=now) is True

    def test_rejects_a_code_two_buckets_old(self) -> None:
        now = time.time()
        stale = derive_code(EMAIL, secret=SECRET, at=now - 1300)
        assert verify_code(EMAIL, stale, secret=SECRET, at=now) is False

    def test_rejects_another_addresss_code(self) -> None:
        other = derive_code("eve@example.com", secret=SECRET)
        assert verify_code(EMAIL, other, secret=SECRET) is False

    def test_rejects_garbage(self) -> None:
        for candidate in ["", "abcdef", "12345", "1234567", "  ", "12 456", "-12345"]:
            assert verify_code(EMAIL, candidate, secret=SECRET) is False

    def test_rejects_a_wrong_code_of_the_right_shape(self) -> None:
        # Picked relative to the real code so this can never collide by chance.
        real = derive_code(EMAIL, secret=SECRET)
        wrong = str((int(real) + 1) % 10**6).zfill(6)
        assert verify_code(EMAIL, wrong, secret=SECRET) is False


class TestAccessToken:
    def test_round_trips_the_verified_address(self) -> None:
        token = issue_access_token(EMAIL, secret=SECRET)
        assert verify_access_token(token, secret=SECRET) == EMAIL

    def test_normalizes_the_address(self) -> None:
        token = issue_access_token(" ADA@Example.COM ", secret=SECRET)
        assert verify_access_token(token, secret=SECRET) == EMAIL

    def test_rejects_a_tampered_payload(self) -> None:
        token = issue_access_token(EMAIL, secret=SECRET)
        payload, signature = token.split(".", 1)
        forged = f"{payload}x.{signature}"
        with pytest.raises(InvalidToken):
            verify_access_token(forged, secret=SECRET)

    def test_rejects_a_token_signed_with_another_secret(self) -> None:
        token = issue_access_token(EMAIL, secret="another-secret-that-is-long-enough!!!")
        with pytest.raises(InvalidToken):
            verify_access_token(token, secret=SECRET)

    def test_rejects_an_expired_token(self) -> None:
        token = issue_access_token(EMAIL, secret=SECRET, at=time.time() - 3600)
        with pytest.raises(InvalidToken):
            verify_access_token(token, secret=SECRET)

    def test_rejects_a_malformed_token(self) -> None:
        for candidate in ["", "nodot", "a.b.c.d", "...", "!!!.???"]:
            with pytest.raises(InvalidToken):
                verify_access_token(candidate, secret=SECRET)
