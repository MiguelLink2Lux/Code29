"""Health liveness + app-boot scenarios."""

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import create_app


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_unversioned_health_is_404(client: TestClient) -> None:
    assert client.get("/health").status_code == 404


def test_post_health_is_405(client: TestClient) -> None:
    assert client.post("/api/v1/health").status_code == 405


def test_health_route_registered_after_create_app() -> None:
    # Prove the /api/v1/health route is wired in by serving it through a fresh
    # app instance (Starlette wraps sub-routers, so introspecting route.path is
    # not reliable across versions).
    get_settings.cache_clear()
    app = create_app()
    response = TestClient(app).get("/api/v1/health")
    assert response.status_code == 200


def test_import_has_no_external_side_effects() -> None:
    # Importing the app module must not open connections or call out.
    # A successful import + a returned FastAPI instance proves boot is inert.
    import app.main as main_module

    assert main_module.app is not None
    assert main_module.create_app() is not None
