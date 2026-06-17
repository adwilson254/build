#!/usr/bin/env bash
# Fast pure-Python test gate. Builds the minimal image and runs the Rivian
# feature tests that need no compiled openpilot artifacts.
#
# Works with podman (preferred) or docker. Source is bind-mounted so edits are
# picked up without rebuilding the image.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENGINE="${CONTAINER_ENGINE:-podman}"
IMAGE="openrivian-fast"

if ! command -v "$ENGINE" >/dev/null 2>&1; then
  ENGINE="docker"
fi

echo ">> Building fast test image with $ENGINE"
"$ENGINE" build -t "$IMAGE" -f "$REPO_ROOT/ci/Containerfile.fast" "$REPO_ROOT/ci"

echo ">> Running fast Rivian feature tests"
# :z relabels for SELinux hosts; harmless elsewhere. Read-only mount keeps the
# container from mutating the working tree (tests copy into tmp dirs).
exec "$ENGINE" run --rm \
  -v "$REPO_ROOT:/work:ro,z" \
  -w /work \
  -e PYTHONPATH=/work \
  "$IMAGE" \
  -lc "pytest -c ci/pytest-fast.ini --rootdir /work tests/antigravity ${PYTEST_ARGS:-}"
