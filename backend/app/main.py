"""FastAPI application factory and module-level app for uvicorn."""

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_v1
from app.core.config import Settings, get_settings
from app.core.report_settings import ReportDeliveryUnavailable
from app.services.mailer import Mailer, ResendMailer
from app.services.turnstile import (
    VERIFY_TIMEOUT_SECONDS as TURNSTILE_TIMEOUT_SECONDS,
)
from app.services.turnstile import HttpTurnstileVerifier, TurnstileVerifier


def create_app(
    *,
    settings: Settings | None = None,
    turnstile_verifier: TurnstileVerifier | None = None,
    mailer: Mailer | None = None,
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

    app.include_router(api_v1)

    @app.exception_handler(ReportDeliveryUnavailable)
    async def _unconfigured_flow(
        _request: Request, error: ReportDeliveryUnavailable
    ) -> JSONResponse:
        # A feature switched off or half-configured on this deployment: the
        # caller did nothing wrong, so it is 503 and not 4xx. The message names
        # the missing variable so the operator can act on it.
        return JSONResponse(status_code=503, content={"detail": str(error)})

    return app


# Module-level instance for `uvicorn app.main:app`. Import is side-effect-free
# (only reads env via cached settings; no I/O or network).
app = create_app()
