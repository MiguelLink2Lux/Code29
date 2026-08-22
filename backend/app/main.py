"""FastAPI application factory and module-level app for uvicorn."""

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_v1
from app.core.config import Settings, get_settings
from app.services.mailer import Mailer, ResendMailer
from app.services.turnstile import HttpTurnstileVerifier, TurnstileVerifier


def create_app(
    *,
    settings: Settings | None = None,
    turnstile_verifier: TurnstileVerifier | None = None,
    mailer: Mailer | None = None,
) -> FastAPI:
    """Build the FastAPI app: CORS from settings + the /api/v1 router.

    The three collaborators are injectable so tests exercise the real endpoints
    without reaching Cloudflare or Resend (DIP). In production they default to
    the HTTP adapters, built from settings.
    """
    settings = settings or get_settings()
    app = FastAPI(title="Code29 Backend", docs_url="/docs")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # One client per app: connection reuse matters on a serverless warm start.
    http_client = httpx.AsyncClient()

    app.state.settings = settings
    app.state.turnstile_verifier = turnstile_verifier or HttpTurnstileVerifier(
        secret=settings.turnstile_secret_key.get_secret_value(),
        client=http_client,
    )
    app.state.mailer = mailer or ResendMailer(
        api_key=settings.resend_api_key.get_secret_value(),
        sender=settings.contact_from_email,
        client=http_client,
    )

    app.include_router(api_v1)
    return app


# Module-level instance for `uvicorn app.main:app`. Import is side-effect-free
# (only reads env via cached settings; no I/O or network).
app = create_app()
