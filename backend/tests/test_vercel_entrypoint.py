"""The Vercel entrypoint exposes the same app as `uvicorn app.main:app`.

Vercel's Python runtime imports `api/index.py` and looks for a module-level
ASGI callable named `app`. These tests are the only automated guard that the
deployed entrypoint boots at all: a broken import there builds fine and then
500s on every request.
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient


def test_entrypoint_exposes_asgi_app() -> None:
    from api.index import app

    assert isinstance(app, FastAPI)


def test_entrypoint_import_is_side_effect_free() -> None:
    # Importing twice must not rebuild or mutate the app: Vercel may import the
    # module more than once across warm invocations.
    from api.index import app as first
    from api.index import app as second

    assert first is second


def test_health_reachable_through_entrypoint() -> None:
    from api.index import app

    response = TestClient(app).get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
