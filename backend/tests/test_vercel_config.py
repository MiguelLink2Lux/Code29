"""`vercel.json` routes every request to the single Python function.

The backend is deployed as its own Vercel project with Root Directory
`backend/`. Without a catch-all rewrite, only `/api/index` would answer and
every real route — `/api/v1/health`, `/docs` — would 404.
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


def test_catch_all_rewrite_points_at_the_entrypoint() -> None:
    rewrites = _config()["rewrites"]
    assert {"source": "/(.*)", "destination": "/api/index"} in rewrites


def test_rewrite_destination_exists_on_disk() -> None:
    # A rewrite to a missing file deploys fine and 404s at runtime.
    assert ENTRYPOINT.is_file()


def test_no_legacy_builds_key() -> None:
    # `builds` opts the project out of dashboard settings and of zero-config
    # detection of requirements.txt; the modern equivalent is plain rewrites.
    assert "builds" not in _config()
