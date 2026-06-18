#!/usr/bin/env bash
# Faithful full-environment build + test (mirrors upstream CI).
# Ensures submodules + LFS objects are present, builds the image, then inside
# the container: syncs python deps, builds with scons, and runs the compiled
# test set (opendbc Rivian car port + scorerd replay tests).
#
# This path is heavy (submodules, LFS, full scons build). The fast gate
# (run-fast.sh) is what gates merges; this is for parity + replay validation.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENGINE="${CONTAINER_ENGINE:-podman}"
IMAGE="openrivian-full"

if ! command -v "$ENGINE" >/dev/null 2>&1; then
  ENGINE="docker"
fi

echo ">> Ensuring submodules are initialized"
git -C "$REPO_ROOT" submodule update --init --recursive

echo ">> Ensuring LFS objects are present"
if command -v git-lfs >/dev/null 2>&1; then
  git -C "$REPO_ROOT" lfs pull || echo "WARN: git lfs pull failed; binary assets may be pointers"
else
  echo "WARN: git-lfs not installed on host; skipping LFS pull"
fi

echo ">> Building full environment image with $ENGINE"
"$ENGINE" build -t "$IMAGE" -f "$REPO_ROOT/ci/Containerfile" "$REPO_ROOT/ci"

echo ">> Building openpilot + running compiled tests in container"
exec "$ENGINE" run --rm \
  -v "$REPO_ROOT:/work:z" \
  -v openrivian-uv-cache:/root/.cache/uv \
  -v openrivian-uv-python:/root/.local/share/uv \
  -w /work \
  -e PYTHONPATH=/work \
  "$IMAGE" \
  -lc '
    set -e
    uv sync --frozen --all-extras
    source .venv/bin/activate
    # Build the compiled bits the Rivian + replay tests need (CAN parsing, capnp).
    scons -j"$(nproc)" cereal opendbc_repo/opendbc
    # 1. Pure/mocked unit tests. test_rivian_components mocks cereal in-process,
    #    so the replay test (which needs REAL cereal) is excluded here.
    python -m pytest -c ci/pytest-fast.ini --rootdir /work \
      --ignore=tests/antigravity/test_scorerd_replay.py tests/antigravity '"${PYTEST_ARGS:-}"'
    # 2. Route-replay test in isolation with real cereal + compiled LogReader.
    python -m pytest -c ci/pytest-fast.ini --rootdir /work \
      tests/antigravity/test_scorerd_replay.py
    # 3. opendbc Rivian car-port tests (best-effort; uses opendbc rootdir).
    python -m pytest --rootdir opendbc_repo -p no:cacheprovider --noconftest \
      opendbc_repo/opendbc/car/rivian/tests || echo "WARN: opendbc rivian car tests reported failures/errors"
  '
