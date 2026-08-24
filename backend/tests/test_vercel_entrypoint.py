"""The Vercel entrypoint must hand the application the caller's real path.

`vercel.json` rewrites every request to this function and, in doing so, replaces
the path with `/api/index`. These tests exercise the shim as plain ASGI, without
Vercel in the loop — the deployed entrypoint is otherwise code that only ever
runs in production, which is exactly where a bug hides longest.
"""

from fastapi.testclient import TestClient

from api.index import PATH_PARAM, app, restore_rewritten_path


class TestRestoreRewrittenPath:
    def test_the_original_path_replaces_the_rewritten_one(self) -> None:
        scope = {
            "type": "http",
            "path": "/api/index",
            "query_string": f"{PATH_PARAM}=api/v1/health".encode(),
        }

        restored = restore_rewritten_path(scope)

        assert restored["path"] == "/api/v1/health"
        assert restored["raw_path"] == b"/api/v1/health"

    def test_the_parameter_is_consumed_and_the_rest_of_the_query_survives(self) -> None:
        scope = {
            "type": "http",
            "path": "/api/index",
            "query_string": f"{PATH_PARAM}=api/v1/health&probe=1".encode(),
        }

        restored = restore_rewritten_path(scope)

        assert PATH_PARAM not in restored["query_string"].decode()
        assert restored["query_string"] == b"probe=1"

    def test_a_scope_without_the_parameter_is_left_alone(self) -> None:
        # Running under uvicorn: nothing rewrote anything, so nothing is undone.
        scope = {"type": "http", "path": "/api/v1/health", "query_string": b""}

        assert restore_rewritten_path(scope) is scope

    def test_a_non_http_scope_is_left_alone(self) -> None:
        scope = {"type": "lifespan"}

        assert restore_rewritten_path(scope) is scope


class TestThroughTheEntrypoint:
    def test_the_rewritten_request_reaches_the_real_endpoint(self) -> None:
        client = TestClient(app)

        response = client.get(f"/api/index?{PATH_PARAM}=api/v1/health")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_an_unknown_path_still_answers_404(self) -> None:
        # The diagnostics catch-all is gone: unknown paths must 404 again.
        client = TestClient(app)

        response = client.get(f"/api/index?{PATH_PARAM}=nope")

        assert response.status_code == 404
