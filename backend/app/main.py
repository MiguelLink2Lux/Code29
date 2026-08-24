"""FastAPI application factory and module-level app for uvicorn."""

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_v1
from app.api.v1.site_analysis import (
    AccessTokenVerifier,
    FlowNotConfigured,
    InvalidAccessToken,
    get_access_token_verifier,
)
from app.core.config import Settings, get_settings
from app.core.report_settings import ReportDeliveryUnavailable
from app.services.extraction import FactExtractor, GeminiFactExtractor, StubFactExtractor
from app.services.mailer import Mailer, ResendMailer
from app.services.tokens import InvalidToken, verify_access_token
from app.services.turnstile import (
    VERIFY_TIMEOUT_SECONDS as TURNSTILE_TIMEOUT_SECONDS,
)
from app.services.turnstile import HttpTurnstileVerifier, TurnstileVerifier


class _SignedTokenVerifier:
    """Bridges the site-analysis port to the real token service.

    Each phase shipped against a Protocol with a refusing default so it could
    deploy alone. Wiring them is this factory's job — without it a caller with a
    valid token gets 503, which is precisely what a local run caught.
    """

    def __init__(self, secret: str) -> None:
        self._secret = secret

    def verified_email(self, token: str) -> str:
        if not self._secret:
            raise FlowNotConfigured("no signing secret is configured")

        try:
            return verify_access_token(token, secret=self._secret)
        except InvalidToken as error:
            # The route's own type: it turns this into 401, and it must never
            # surface as a 500 or be confused with a configuration failure.
            raise InvalidAccessToken("invalid access token") from error


def create_app(
    *,
    settings: Settings | None = None,
    turnstile_verifier: TurnstileVerifier | None = None,
    mailer: Mailer | None = None,
    fact_extractor: FactExtractor | None = None,
) -> FastAPI:
    """Build the FastAPI app: CORS from settings + the /api/v1 router.

    The collaborators are injectable so tests exercise the real endpoints without
    reaching Cloudflare or Resend (DIP). In production they default to the HTTP
    adapters, built from settings.
    """
    settings = settings or get_settings()
    app = FastAPI(title="Code29 Backend", docs_url="/docs")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.state.settings = settings
    # Turnstile keeps a shared client: connection reuse matters on a warm start.
    app.state.turnstile_verifier = turnstile_verifier or HttpTurnstileVerifier(
        secret=settings.turnstile_secret_key.get_secret_value(),
        client=httpx.AsyncClient(timeout=TURNSTILE_TIMEOUT_SECONDS),
    )
    # ResendMailer opens its own timed client per send and takes a transport for
    # tests, so it needs no client injected here.
    app.state.mailer = mailer or ResendMailer(
        api_key=settings.resend_api_key.get_secret_value(),
        sender=settings.contact_from_email,
    )

    # The deterministic stub is the default: with no model key the conversation
    # still works, it just extracts less. A 503 per turn would be worse.
    app.state.fact_extractor = fact_extractor or _build_extractor(settings)

    app.include_router(api_v1)

    def _token_verifier() -> AccessTokenVerifier:
        return _SignedTokenVerifier(settings.contact_token_secret.get_secret_value())

    app.dependency_overrides[get_access_token_verifier] = _token_verifier

    @app.exception_handler(ReportDeliveryUnavailable)
    async def _unconfigured_flow(
        _request: Request, error: ReportDeliveryUnavailable
    ) -> JSONResponse:
        # A feature switched off or half-configured on this deployment: the
        # caller did nothing wrong, so it is 503 and not 4xx. The message names
        # the missing variable so the operator can act on it.
        return JSONResponse(status_code=503, content={"detail": str(error)})

    return app


def _build_extractor(settings: Settings) -> FactExtractor:
    key = settings.gemini_api_key.get_secret_value() if hasattr(settings, "gemini_api_key") else ""

    return GeminiFactExtractor(api_key=key) if key else StubFactExtractor()


# Module-level instance for `uvicorn app.main:app`. Import is side-effect-free
# (only reads env via cached settings; no I/O or network).
app = create_app()


# TEMPORARY — diagnostics for the Vercel routing issue (all routes answer 404 in
# production while the same app serves them locally). Registered last, so it only
# catches what no real route matched: it reports the path the function actually
# received. Delete once the routing cause is known.
@app.api_route("/{full_path:path}", methods=["GET"])
def _echo_received_path(full_path: str) -> dict[str, str]:
    return {"seen_path": full_path}
