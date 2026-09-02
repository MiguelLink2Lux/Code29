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

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
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
)
from app.services.report import (
    ReportGenerator,
    SiteSignals,
    WorkflowAnswers,
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
    """The payload the chat posts. See tests/contracts/report-request.json.

    Free-text fields the chat does not collect are dropped rather than trusted:
    `ReportFacts` is serialised straight into the model prompt, so any field a
    caller controls is a channel into it. Output validation is the hard
    guarantee, but narrowing the input costs nothing.
    """

    #: The signed conversation envelope. When present it is the ONLY source of
    #: facts: a client that could post its own would put any company into a
    #: report we sign our name to. Absent for the legacy questionnaire payload,
    #: which the cutover retires — see ADR 0009.
    envelope: str | None = None
    contact_name: str = Field(default="", max_length=120)
    # The chat presents the company as optional, so an empty string must not
    # strand a visitor on a step they were told they could skip.
    company: str = Field(default="", max_length=160)
    locale: str = "es"
    #: Legacy questionnaire field. The canon report does not read it: practices
    #: now arrive as reported evidence from the conversation. Optional so the
    #: conversational payload validates.
    workflow: WorkflowAnswers = WorkflowAnswers()
    site_url: str | None = None
    transcript: list[TranscriptEntry] = Field(default_factory=list)
    consent: ConsentPayload

    @field_validator("workflow")
    @classmethod
    def _drop_client_free_text(cls, value: WorkflowAnswers) -> WorkflowAnswers:
        # The chat posts notes/team_size as null; anything arriving here came
        # from a direct API caller and has no business reaching the prompt.
        return value.model_copy(update={"notes": None, "team_size": None})

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
):
    """The canon generator: ten points, not the superseded five axes (ADR 0008).

    `stub` is the deterministic template — what runs with no key and what every
    test exercises. `gemini` verifies claims with Search when the account is
    entitled to grounding, and degrades to ungrounded (dropping every cited
    claim) when it is not: without grounding a "citation" is a claim nobody
    checked.
    """
    from app.services.canon_report import TemplateCanonGenerator
    from app.services.grounded_report import GroundedCanonGenerator

    selected = (settings.report_generator or "stub").strip().lower()

    if selected == "stub":
        return TemplateCanonGenerator()

    if selected == "gemini":
        key = settings.gemini_api_key.get_secret_value()
        if not key:
            # Misconfiguration, not a bad request: surface it as 503 rather than
            # silently emailing a template report as if a model wrote it.
            raise ReportDeliveryUnavailable(
                "REPORT_GENERATOR=gemini requires GEMINI_API_KEY to be set"
            )
        return GroundedCanonGenerator(api_key=key, grounding=settings.gemini_grounding)

    raise ReportDeliveryUnavailable(
        f"Unknown REPORT_GENERATOR value: {settings.report_generator!r}. "
        "Valid values: 'stub', 'gemini'"
    )


def get_mailer(
    request: Request,
    settings: Annotated[ReportDeliverySettings, Depends(get_settings)],
) -> Mailer:
    """The app's mailer if one was injected, otherwise a Resend adapter.

    Two ways to obtain a mailer is one too many: create_app already accepts one,
    and a route building its own quietly ignored it — which is how a test that
    asserts on delivery can pass while nothing is delivered.
    """
    injected = getattr(request.app.state, "mailer", None)

    if injected is not None:
        return injected

    api_key, sender, _owner = settings.require_mail_configuration()
    return ResendMailer(api_key=api_key, sender=sender)


async def _no_site_analysis(url: str | None) -> SiteSignals:
    """Kept as the explicit "nothing was measured" path, used when no URL is held.

    It is no longer the default: leaving it wired meant every lead's site was
    reported as unreadable even though the SSRF-guarded analyser existed.
    """
    return SiteSignals(available=False, url=url)


async def _analyse_through_the_guard(url: str | None) -> SiteSignals:
    """Analyse the lead's home page behind the SSRF guard.

    Degrades rather than fails: an unreachable or refused site yields
    `available=False`, which is a specified state the report knows how to read.
    """
    if not url or not url.strip():
        return await _no_site_analysis(url)

    from app.api.v1.site_analysis import _analyse_with_a_fresh_client
    from app.services.url_guard import UrlRejected

    try:
        return await _analyse_with_a_fresh_client(url.strip())
    except UrlRejected:
        # A blocked target is not our error and not the lead's fault either: the
        # report simply has no measured signal for that site.
        return await _no_site_analysis(url)


def get_site_analyzer() -> SiteAnalyzer:
    return _analyse_through_the_guard


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

    contact_name = payload.contact_name
    company = payload.company
    website = payload.site_url
    team: str | None = None
    # The four optional facts of the script. Without them the generator has a
    # company and no practice attached to it, and every point it could have
    # judged stays `no evaluado` — a report about nothing (COD-67).
    #
    # Imported here, like `open_envelope` below: the conversation service pulls in
    # the model client, and this module is imported at app build time.
    from app.services.conversation import OPTIONAL_FACTS

    ground: dict[str, str | None] = dict.fromkeys(OPTIONAL_FACTS)

    if payload.envelope:
        from app.services.conversation import open_envelope
        from app.services.tokens import InvalidToken

        try:
            state = open_envelope(
                payload.envelope, secret=settings.require_verification_secret()
            )
        except InvalidToken as error:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="That conversation is no longer valid. Start a new one.",
            ) from error

        # The envelope wins outright. Anything in the body is a claim by the
        # caller about themselves, and this report carries our name.
        contact_name = state.facts.contact_name or ""
        company = state.facts.company or ""
        website = state.facts.website
        team = state.facts.team
        ground = {field: getattr(state.facts, field) for field in OPTIONAL_FACTS}

    signals = await _analyse(analyzer, website)

    try:
        report = await generator.generate(
            contact_name=contact_name,
            company=company,
            locale=payload.locale,
            team=team,
            site=signals,
            ground=ground,
        )
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
        recommendation_count=len(report.sections),
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
    report: object,
    payload: ReportRequest,
    verified_email: str,
    mailer: Mailer,
    settings: ReportDeliverySettings,
) -> None:
    generated_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    consent_statement = CONSENT_STATEMENT[payload.locale]
    from app.services.mailer import render_canon_email

    body = render_canon_email(
        report=report,
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
