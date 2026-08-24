"""`vercel.json` must not stand between a request and the application.

The backend is deployed as its own Vercel project with Root Directory
`backend/`. The runtime resolves the FastAPI application by itself and serves
it — no rewrite needed, and `api/index.py` is not even imported.

A catch-all rewrite to `/api/index` looks like the thing that makes routing
work and is in fact what breaks it: measured on a live deployment, the function
then receives that literal path for every request, so FastAPI answers 404 to
all of its routes — `/docs` included — while serving them under uvicorn. These
tests pin the absence of that rewrite, since nothing else would notice its
return until production 404s again.
"""

import json
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
VERCEL_JSON = BACKEND_ROOT / "vercel.json"
ENTRYPOINT = BACKEND_ROOT / "api" / "index.py"


def _config() -> dict:
    return json.loads(VERCEL_JSON.read_text())


def test_vercel_json_is_valid_json() -> None:
    assert isinstance(_config(), dict)


def test_there_is_no_catch_all_rewrite() -> None:
    # Measured on a live deployment: a rewrite to /api/index hands the function
    # that literal path for every request, so every route 404s. The runtime
    # resolves and serves the app without any rewrite at all.
    assert "rewrites" not in _config()


def test_the_entrypoint_exists_on_disk() -> None:
    assert ENTRYPOINT.is_file()


def test_no_legacy_builds_key() -> None:
    # `builds` opts the project out of dashboard settings and of zero-config
    # detection of requirements.txt; the modern equivalent is plain rewrites.
    assert "builds" not in _config()
