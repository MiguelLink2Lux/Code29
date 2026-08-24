"""Vercel serverless entrypoint for the FastAPI backend.

Vercel's Python runtime imports this module and serves the module-level ASGI
callable named `app`. The application itself is built once by the factory in
`app.main`, so local uvicorn, the test suite and the deployed function all run
the exact same object.

The one thing that happens here is undoing a rewrite. `vercel.json` sends every
request to this function, and that rewrite is not transparent: the function
receives the literal path `/api/index`, never the path the caller asked for, so
FastAPI answered 404 to everything — `/docs` included — while serving the same
routes locally. The query string *is* preserved, so the rewrite carries the
original path in `__vpath` and `restore_rewritten_path` puts it back into the
ASGI scope before the application sees the request.

Both halves must change together: the parameter name here and in `vercel.json`.
"""

from collections.abc import Awaitable, Callable, MutableMapping
from typing import Any
from urllib.parse import parse_qs, urlencode

from app.main import app as _app

# Must match the `destination` in vercel.json. Double-underscored so it cannot
# be confused with a caller's own parameter.
PATH_PARAM = "__vpath"

Scope = MutableMapping[str, Any]
Receive = Callable[[], Awaitable[MutableMapping[str, Any]]]
Send = Callable[[MutableMapping[str, Any]], Awaitable[None]]


def restore_rewritten_path(scope: Scope) -> Scope:
    """Return a scope whose path is the one the caller asked for.

    Untouched when the parameter is absent, so running under uvicorn — where no
    rewrite happened — behaves exactly as before.
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


async def app(scope: Scope, receive: Receive, send: Send) -> None:
    await _app(restore_rewritten_path(scope), receive, send)


__all__ = ["app", "restore_rewritten_path"]
