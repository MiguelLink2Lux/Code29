"""Vercel serverless entrypoint for the FastAPI backend.

Vercel's Python runtime imports this module and serves the module-level ASGI
callable named `app`. It deliberately contains no logic: the application is
built once by the factory in `app.main`, so local uvicorn, the test suite and
the deployed function all run the exact same object.
"""

from app.main import app

__all__ = ["app"]
