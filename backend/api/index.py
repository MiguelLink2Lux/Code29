"""Vercel serverless entrypoint for the FastAPI backend.

Vercel's Python runtime imports this module and serves the application object it
finds here. The application itself is built by the factory in `app.main`, so
local uvicorn, the test suite and the deployed function all run the same object.

The one thing that happens here is undoing a rewrite. `vercel.json` sends every
request to this function, and that rewrite is not transparent: measured on a
live deployment, the function receives the literal path `/api/index` whatever
was asked, so FastAPI answered 404 to all of its routes — `/docs` included —
while serving them locally. The query string does survive, so the rewrite
carries the original path in `__vpath` and the middleware below puts it back
into the ASGI scope before the router sees the request.

It has to be a middleware, not a wrapping callable: the runtime serves the
application object it finds in this module and ignores a plain ASGI function,
which is how the first attempt failed silently. Adding it here rather than in
the factory keeps uvicorn and the tests on the untouched application.

Both halves must change together: `PATH_PARAM` here and the `destination` in
`vercel.json`. `tests/test_vercel_config.py` asserts they agree.
"""

from collections.abc import Awaitable, Callable, MutableMapping
from typing import Any
from urllib.parse import parse_qs, urlencode

from app.main import app

# Must match the `destination` in vercel.json. Double-underscored so it cannot
# be confused with a caller's own parameter.
PATH_PARAM = "__vpath"

Scope = MutableMapping[str, Any]
Receive = Callable[[], Awaitable[MutableMapping[str, Any]]]
Send = Callable[[MutableMapping[str, Any]], Awaitable[None]]


def restore_rewritten_path(scope: Scope) -> Scope:
    """Return a scope whose path is the one the caller asked for.

    Returned untouched when the parameter is absent, so running under uvicorn —
    where nothing rewrote anything — behaves exactly as before.
    """
    if scope.get("type") != "http":
        return scope

    query = parse_qs(scope.get("query_string", b"").decode(), keep_blank_values=True)
    original = query.pop(PATH_PARAM, None)

    if not original:
        return scope

    path = "/" + original[0].lstrip("/")
    restored = dict(scope)
    restored["path"] = path
    restored["raw_path"] = path.encode()
    # Whatever the caller sent survives; only our own parameter is consumed.
    restored["query_string"] = urlencode(query, doseq=True).encode()

    return restored


class RestoreRewrittenPathMiddleware:
    """Outermost middleware: the path is fixed before anything else reads it."""

    def __init__(self, app: Callable[[Scope, Receive, Send], Awaitable[None]]) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        await self.app(restore_rewritten_path(scope), receive, send)


app.add_middleware(RestoreRewrittenPathMiddleware)

__all__ = ["PATH_PARAM", "app", "restore_rewritten_path", "RestoreRewrittenPathMiddleware"]
