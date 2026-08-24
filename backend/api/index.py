"""Vercel serverless entrypoint for the FastAPI backend.

Kept as the conventional entrypoint and as the target of `uvicorn api.index:app`,
but note what a live deployment showed: this module is not what the runtime
imports. It resolves the application on its own and serves it directly — a
middleware added here never ran, which is how a first attempt at fixing the
routing failed without any error.

There is deliberately no rewrite in `vercel.json` either. A catch-all rewrite to
`/api/index` is not transparent: the function then receives that literal path
for every request, and FastAPI answers 404 to all of its routes, `/docs`
included, while serving them perfectly under uvicorn. See
`docs/protocols/deployment.md`.
"""

from app.main import app

__all__ = ["app"]
