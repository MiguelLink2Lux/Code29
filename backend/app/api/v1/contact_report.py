"""POST /api/v1/contact/report — generate the workflow report and deliver it.

The verification token, never the request body, decides who receives the report:
a body claiming a different address cannot redirect it. Without a valid token no
report is generated, no site is fetched and no email leaves.

Kept in its own module rather than in `contact.py` so this phase and the
verification phase could be written in parallel without fighting over one file.
**Merge task:** the two can be folded into a single `contact.py` router.

Failure contracts:
  401 — missing, malformed or rejected token
  400 — consent not granted (semantic); 422 — malformed body (schema)
  502 — the generator raised, or mail delivery failed (nothing partial is sent)
  503 — the flow is not configured on this deployment
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Annotated, Protocol

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field, field_validator

from app.core.report_settings import (
    ReportDeliverySettings,
    ReportDeliveryUnavailable,
    get_report_delivery_settings,
)
from app.services.mailer import (
    EmailMessage,
    MailDeliveryError,
    Mailer,
    ResendMailer,
    render_report_email,
)
from app.services.report import (
    ContactReport,
    ReportFacts,
    ReportGenerator,
    SiteSignals,
    UnusableReportGenerator,
    WorkflowAnswers,
    build_report_generator,
)
from app.services.tokens_port import (
    InvalidVerificationToken,
    TokenVerifier,
    VerificationUnavailable,
    build_token_verifier,
)

logger = logging.getLogger(__name__)

router = APIRouter()

CONSENT_STATEMENT = {
    "es": (
        "El visitante aceptó la política de privacidad y autorizó expresamente el uso de sus "
        "respuestas para generar este informe y recibirlo por email."
    ),
    "en": (
        "The visitor accepted the privacy policy and expressly authorised the use of their "
        "answers to generate this report and receive it by email."
    ),
}


class SiteAnalyzer(Protocol):
    """Port for the home-page analyser. Its own phase provides the real one."""

    async def __call__(self, url: str | None) -> SiteSignals: ...


class TranscriptEntry(BaseModel):
    step_id: str
    answer: str


class ConsentPayload(BaseModel):
    privacy_accepted: bool
    report_accepted: bool


class ReportRequest(BaseModel):
    contact_name: str = Field(min_length=1, max_length=120)
    # The chat presents the company as optional, so an empty string must not
    # strand a visitor on a step they were told they could skip.
    company: str = Field(default="", max_length=160)
    locale: str = "es"
    workflow: WorkflowAnswers
    site_url: str | None = None
    transcript: list[TranscriptEntry] = Field(default_factory=list)
    consent: ConsentPayload

    @field_validator("locale")
    @classmethod
    def _known_locale(cls, value: str) -> str:
        return value if value in CONSENT_STATEMENT else "es"

    @field_validator("site_url")
    @classmethod
    def _http_scheme_only(cls, value: str | None) -> str | None:
        # Syntax only. Rejecting private and loopback targets is the analyser's
        # job: it must resolve the host, which cannot be done here.
        if value is None or not value.strip():
            return None
        candidate = value.strip()
        if not candidate.lower().startswith(("http://", "https://")):
            raise ValueError("site_url must start with http:// or https://")
        return candidate


class ReportResponse(BaseModel):
    """Confirmation only: the document itself travels by email."""

    delivered: bool
    title: str
    summary: str
    recommendation_count: int


# --- Dependencies (each one overridable in tests) --------------------------


def get_settings() -> ReportDeliverySettings:
    return get_report_delivery_settings()


def get_token_verifier(
    settings: Annotated[ReportDeliverySettings, Depends(get_settings)],
) -> TokenVerifier:
    return build_token_verifier(settings.require_verification_secret())


def get_verified_email(
    verifier: Annotated[TokenVerifier, Depends(get_token_verifier)],
    authorization: Annotated[str | None, Header()] = None,
) -> str:
    """Extract and verify the bearer token. Never echoes it back."""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="A verification token is required.",
        )

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Expected an Authorization header of the form: Bearer <token>.",
        )

    try:
        return verifier(token.strip())
    except InvalidVerificationToken:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="The verification token is invalid or has expired.",
        ) from None
    except VerificationUnavailable as error:
        raise ReportDeliveryUnavailable(str(error)) from error


def get_report_generator(
    settings: Annotated[ReportDeliverySettings, Depends(get_settings)],
) -> ReportGenerator:
    try:
        return build_report_generator(
            settings.report_generator,
            model_api_key=settings.gemini_api_key.get_secret_value(),
        )
    except UnusableReportGenerator as error:
        # Misconfiguration, not a bad request: surface it as 503.
        raise ReportDeliveryUnavailable(str(error)) from error


def get_mailer(
    settings: Annotated[ReportDeliverySettings, Depends(get_settings)],
) -> Mailer:
    api_key, sender, _owner = settings.require_mail_configuration()
    return ResendMailer(api_key=api_key, sender=sender)


async def _no_site_analysis(url: str | None) -> SiteSignals:
    """Default analyser: reports the site as not analysed.

    The real one arrives with its own phase. Until then the report degrades
    exactly as it does for an unreachable site, which is a specified state.
    """
    return SiteSignals(available=False, url=url)


def get_site_analyzer() -> SiteAnalyzer:
    return _no_site_analysis


# --- Route -----------------------------------------------------------------


@router.post("/contact/report", response_model=ReportResponse)
async def create_contact_report(
    payload: ReportRequest,
    verified_email: Annotated[str, Depends(get_verified_email)],
    generator: Annotated[ReportGenerator, Depends(get_report_generator)],
    mailer: Annotated[Mailer, Depends(get_mailer)],
    analyzer: Annotated[SiteAnalyzer, Depends(get_site_analyzer)],
    settings: Annotated[ReportDeliverySettings, Depends(get_settings)],
) -> ReportResponse:
    if not (payload.consent.privacy_accepted and payload.consent.report_accepted):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Both the privacy policy and the report consent must be accepted.",
        )

    signals = await _analyse(analyzer, payload.site_url)

    facts = ReportFacts(
        contact_name=payload.contact_name,
        company=payload.company,
        locale=payload.locale,  # type: ignore[arg-type]
        workflow=payload.workflow,
        site=signals,
    )

    try:
        report = await generator.generate(facts)
    except Exception as error:
        # Contained on purpose: a half-written report must never be emailed.
        logger.warning("report generation failed: %s", type(error).__name__)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The report could not be generated. Please try again.",
        ) from error

    await _deliver(
        report=report,
        payload=payload,
        verified_email=verified_email,
        mailer=mailer,
        settings=settings,
    )

    return ReportResponse(
        delivered=True,
        title=report.title,
        summary=report.summary,
        recommendation_count=len(report.recommendations),
    )


async def _analyse(analyzer: SiteAnalyzer, url: str | None) -> SiteSignals:
    """Analysis is best-effort: the report is the product, not the site scan."""
    if not url:
        return SiteSignals(available=False, url=None)

    try:
        return await analyzer(url)
    except Exception as error:
        # Broad by intent — a timeout, a DNS failure or a malformed page must
        # degrade the report, never lose it. The host is safe to log; the
        # visitor's address is not, and is not in scope here.
        logger.info("site analysis unavailable: %s", type(error).__name__)
        return SiteSignals(available=False, url=url)


async def _deliver(
    *,
    report: ContactReport,
    payload: ReportRequest,
    verified_email: str,
    mailer: Mailer,
    settings: ReportDeliverySettings,
) -> None:
    generated_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    consent_statement = CONSENT_STATEMENT[payload.locale]
    body = render_report_email(
        report=report,
        transcript=[(entry.step_id, entry.answer) for entry in payload.transcript],
        consent_statement=consent_statement,
        generated_at=generated_at,
    )

    owner = settings.contact_to_email

    try:
        # The verified address, never a value from the body.
        await mailer.send(
            EmailMessage(to=[verified_email], subject=report.title, text=body)
        )
        if owner:
            await mailer.send(
                EmailMessage(
                    to=[owner],
                    subject=f"[lead] {report.title}",
                    text=body,
                    # So the owner can answer the lead straight from the copy.
                    reply_to=verified_email,
                )
            )
    except MailDeliveryError as error:
        logger.warning("report delivery failed: %s", error)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The report was generated but could not be emailed. Please retry.",
        ) from error
