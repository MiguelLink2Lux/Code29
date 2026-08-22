"""Email verification endpoints for the guided contact flow.

Two doors, both narrow:

- `POST /contact/verification/request` — Turnstile first, then email a derived
  code. The code never appears in the response; that is the whole point.
- `POST /contact/verification/confirm` — exchange a valid code for a signed
  access token, which is what authorises the expensive downstream steps.

Refusals are deliberately uniform: the endpoint must not become an oracle for
which addresses exist. No address is ever written to a log.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field

from app.services.mailer import EmailMessage, Mailer, MailerUnavailable
from app.services.tokens import derive_code, issue_access_token, verify_code
from app.services.turnstile import TurnstileUnavailable, TurnstileVerifier

router = APIRouter(prefix="/contact", tags=["contact"])

# Same body for every rejected code, so timing aside the response reveals nothing.
INVALID_CODE_DETAIL = "That code is not valid. Request a new one."


class VerificationRequest(BaseModel):
    email: EmailStr
    turnstile_token: str = Field(alias="turnstileToken", min_length=1)


class VerificationConfirm(BaseModel):
    email: EmailStr
    code: str = Field(min_length=1, max_length=12)


class AccessTokenResponse(BaseModel):
    access_token: str = Field(serialization_alias="accessToken")


def _require_configured_flow(request: Request) -> None:
    if not request.app.state.settings.contact_flow_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The contact flow is not configured on this deployment.",
        )


def _signing_secret(request: Request) -> str:
    return request.app.state.settings.contact_token_secret.get_secret_value()


def _code_email(code: str) -> str:
    return (
        "Your Code29 verification code is:\n\n"
        f"    {code}\n\n"
        "It is valid for the next 10 minutes. If you did not request it, ignore "
        "this message — nothing happens until the code is used."
    )


@router.post(
    "/verification/request",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Send a verification code to an email address",
)
async def request_verification(payload: VerificationRequest, request: Request) -> dict[str, str]:
    _require_configured_flow(request)

    verifier: TurnstileVerifier = request.app.state.turnstile_verifier
    client_host = request.client.host if request.client else None

    try:
        human = await verifier.verify(payload.turnstile_token, remote_ip=client_host)
    except TurnstileUnavailable as error:
        # Fail closed: an outage must not open the email path.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Verification is temporarily unavailable. Try again shortly.",
        ) from error

    if not human:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Human verification failed.",
        )

    code = derive_code(payload.email, secret=_signing_secret(request))
    mailer: Mailer = request.app.state.mailer

    try:
        await mailer.send(
            EmailMessage(
                to=str(payload.email),
                subject="Your Code29 verification code",
                text_body=_code_email(code),
            )
        )
    except MailerUnavailable as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not send the verification email. Try again shortly.",
        ) from error

    return {"status": "sent"}


@router.post(
    "/verification/confirm",
    response_model=AccessTokenResponse,
    response_model_by_alias=True,
    summary="Exchange a verification code for an access token",
)
async def confirm_verification(
    payload: VerificationConfirm, request: Request
) -> AccessTokenResponse:
    _require_configured_flow(request)

    secret = _signing_secret(request)

    if not verify_code(str(payload.email), payload.code, secret=secret):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=INVALID_CODE_DETAIL)

    return AccessTokenResponse(access_token=issue_access_token(str(payload.email), secret=secret))
