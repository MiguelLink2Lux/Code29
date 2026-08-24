"""`vercel.json` routes every request to the single Python function.

The backend is deployed as its own Vercel project with Root Directory
`backend/`. Without a catch-all rewrite, only `/api/index` would answer.

The rewrite alone is not enough, though: it is *not* transparent. The function
receives the literal path `/api/index`, so every real route — `/api/v1/health`,
`/docs` — answered 404 in production while working locally. The destination
therefore carries the original path in a query parameter, which the entrypoint
puts back into the ASGI scope. Both halves are asserted here: they are useless
apart, and nothing else would notice if one of them drifted.
"""

import json
from pathlib import Path

from api.index import PATH_PARAM

BACKEND_ROOT = Path(__file__).resolve().parent.parent
VERCEL_JSON = BACKEND_ROOT / "vercel.json"
ENTRYPOINT = BACKEND_ROOT / "api" / "index.py"


def _config() -> dict:
    return json.loads(VERCEL_JSON.read_text())


def test_vercel_json_is_valid_json() -> None:
    assert isinstance(_config(), dict)


def test_catch_all_rewrite_points_at_the_entrypoint() -> None:
    rewrites = _config()["rewrites"]
    assert {"source": "/(.*)", "destination": f"/api/index?{PATH_PARAM}=$1"} in rewrites


def test_the_rewrite_carries_the_original_path() -> None:
    # The capture group is what makes the path recoverable at all; a destination
    # without `$1` deploys happily and 404s every route.
    destination = _config()["rewrites"][0]["destination"]
    assert f"{PATH_PARAM}=$1" in destination


def test_rewrite_destination_exists_on_disk() -> None:
    # A rewrite to a missing file deploys fine and 404s at runtime.
    assert ENTRYPOINT.is_file()


def test_no_legacy_builds_key() -> None:
    # `builds` opts the project out of dashboard settings and of zero-config
    # detection of requirements.txt; the modern equivalent is plain rewrites.
    assert "builds" not in _config()
