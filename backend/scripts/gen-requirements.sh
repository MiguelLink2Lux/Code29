#!/usr/bin/env bash
# Regenerates backend/requirements.txt from pyproject.toml + uv.lock.
#
# Vercel's Python runtime does not read pyproject.toml/uv, so the deployment
# needs a plain requirements file. pyproject.toml stays canonical; run this
# after every dependency change. tests/test_requirements_manifest.py fails if
# the two manifests drift.
set -euo pipefail

cd "$(dirname "$0")/.."

{
  echo "# GENERATED FILE — do not edit by hand."
  echo "#"
  echo "# pyproject.toml is the canonical dependency manifest. This file exists only"
  echo "# because Vercel's Python runtime does not read pyproject.toml/uv."
  echo "#"
  echo "# Regenerate after every dependency change:"
  echo "#   ./scripts/gen-requirements.sh"
  echo "#"
  uv export --no-dev --no-hashes --no-emit-project
} > requirements.txt

echo "requirements.txt regenerated ($(grep -cvE '^\s*(#|$)' requirements.txt) pinned packages)"
