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


def test_pydantic_email_extra_is_declared() -> None:
    """`EmailStr` needs pydantic's email extra, and fails only at request time.

    A merge once dropped this line from pyproject while uv.lock and
    requirements.txt still carried the package, so the deployed API worked and a
    fresh `uv sync` produced a backend whose verification endpoints raised
    ImportError on every call. Nothing else noticed.
    """
    declared = PYPROJECT.read_text()

    assert "pydantic[email]" in declared, "pydantic[email] must stay declared: EmailStr needs it"


def test_every_third_party_module_the_app_imports_is_declared() -> None:
    """Top-level imports in app/ must trace back to a declared dependency."""
    import re

    app_dir = BACKEND_ROOT / "app"
    stdlib_or_local = {"app", "__future__"}
    imported: set[str] = set()

    for path in app_dir.rglob("*.py"):
        for line in path.read_text().splitlines():
            match = re.match(r"^\s*(?:from|import)\s+([a-zA-Z_][\w]*)", line)
            if match:
                imported.add(match.group(1))

    # Names that map to a declared distribution under a different spelling.
    aliases = {"pydantic_settings": "pydantic-settings"}
    declared = _declared_runtime_names()
    unresolved = {
        name
        for name in imported
        if name not in stdlib_or_local
        and aliases.get(name, name) not in declared
        and not _is_stdlib(name)
    }

    assert not unresolved, f"imported in app/ but not declared in pyproject: {unresolved}"


def _is_stdlib(name: str) -> bool:
    import sys

    return name in sys.stdlib_module_names
