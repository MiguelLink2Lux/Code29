"""`requirements.txt` is a generated artifact kept in sync with pyproject.

Vercel's Python runtime does not read `pyproject.toml`/uv, so the deployment
needs a requirements file. That makes two manifests for one dependency set;
pyproject stays canonical and this test is what stops them from drifting.
"""

import re
import tomllib
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
REQUIREMENTS = BACKEND_ROOT / "requirements.txt"
PYPROJECT = BACKEND_ROOT / "pyproject.toml"

# Package name at the start of a requirement line, e.g. "fastapi==0.1.0".
_NAME = re.compile(r"^([A-Za-z0-9._-]+)")


def _requirement_names() -> set[str]:
    names = set()
    for line in REQUIREMENTS.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        match = _NAME.match(line)
        if match:
            names.add(match.group(1).lower().replace("_", "-"))
    return names


def _declared_runtime_names() -> set[str]:
    data = tomllib.loads(PYPROJECT.read_text())
    names = set()
    for spec in data["project"]["dependencies"]:
        # Strip extras and version markers: "uvicorn[standard]>=1" -> "uvicorn".
        names.add(re.split(r"[\[<>=!;\s]", spec, maxsplit=1)[0].lower())
    return names


def test_requirements_file_exists() -> None:
    assert REQUIREMENTS.is_file()


def test_marked_as_generated_with_regeneration_command() -> None:
    header = REQUIREMENTS.read_text()[:600]
    assert "generated" in header.lower()
    assert "uv export" in header


def test_every_runtime_dependency_is_present() -> None:
    missing = _declared_runtime_names() - _requirement_names()
    assert not missing, f"pyproject runtime deps missing from requirements.txt: {missing}"


def test_dev_dependencies_are_excluded() -> None:
    # Shipping pytest/ruff to a serverless function only inflates the bundle,
    # which matters against Vercel's size ceiling.
    assert {"pytest", "ruff"}.isdisjoint(_requirement_names())
