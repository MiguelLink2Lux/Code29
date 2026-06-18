"""FastAPI application factory and module-level app for uvicorn."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_v1
from app.core.config import get_settings


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
    return app


# Module-level instance for `uvicorn app.main:app`. Import is side-effect-free
# (only reads env via cached settings; no I/O or network).
app = create_app()
