"""FastAPI application factory and module-level app for uvicorn."""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_v1
from app.core.config import get_settings
from app.core.report_settings import ReportDeliveryUnavailable


def create_app() -> FastAPI:
    """Build the FastAPI app: CORS from settings + the /api/v1 router."""
    settings = get_settings()
    app = FastAPI(title="Code29 Backend", docs_url="/docs")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
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
