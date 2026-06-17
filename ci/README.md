# OpenRivian CI / local test harness

This directory contains the container definitions and scripts used both locally
(podman) and in GitHub Actions to validate the Rivian feature pipeline.

There are two tiers, matching the agreed strategy ("option B"):

## 1. Fast gate (`run-fast.sh`)

Pure-Python tests that need **no compiled openpilot artifacts**. This is the
merge gate that must be green before `main` is promoted to `ap`:

- injection-script correctness + idempotency (`test_injectors.py`)
- the non-Rivian cleaner (`test_cleaner.py`)
- `process_config.py` import-safety regression (`test_process_config_safe.py`)
- Rivian cloud API / MQTT / Web UI logic driven by **captured golden fixtures**
  (`test_rivian_components.py`)

Image: `Containerfile.fast` (python:3.12-slim + pytest). Runs in seconds.

```sh
./ci/run-fast.sh
```

## 2. Full environment (`run-full.sh`)

Faithful build environment that mirrors upstream CI (`ubuntu:24.04` +
`tools/setup_dependencies.sh`). Required for tests that need compiled
`cereal`/`opendbc` (CAN parsing) and for **route-replay tests**:

- opendbc Rivian car-port tests
- `scorerd` replay tests fed by a captured Rivian route segment

Image: `Containerfile`. This pulls submodules + LFS and builds, so it is slow.

```sh
./ci/run-full.sh
```

## Route data for replay tests

Replay tests look for a captured Rivian route under `tests/antigravity/routes/`.
See `tests/antigravity/routes/README.md` for how to capture one from the comma
device. Replay tests `skip` automatically when no route is present, so the fast
gate is never blocked by missing hardware data.
