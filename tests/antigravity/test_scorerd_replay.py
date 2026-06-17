"""Replay-based validation of the Rivian scorer against real route data.

Runs recorded `carState`/`accelerometer`/`modelV2` messages from an openpilot
route segment through `RivianScorer` and checks the metrics are well-formed.

This is part of the *full* suite: it needs compiled cereal + the openpilot
LogReader, and a route segment under `tests/antigravity/routes/`. It skips
cleanly (never errors) when either is missing, so the fast gate is unaffected.
"""
import glob
import os

import pytest

ROUTES_DIR = os.path.join(os.path.dirname(__file__), "routes")


def _find_rlogs():
    patterns = ["**/rlog.bz2", "**/rlog.zst", "**/rlog", "**/*.rlog"]
    found = []
    for p in patterns:
        found += glob.glob(os.path.join(ROUTES_DIR, p), recursive=True)
    return sorted(found)


def test_scorer_processes_real_route():
    # Skip rather than error when the heavy deps / data are unavailable.
    pytest.importorskip("cereal", reason="full environment required")
    try:
        from openpilot.tools.lib.logreader import LogReader
    except Exception as e:  # pragma: no cover - env dependent
        pytest.skip(f"LogReader unavailable: {e}")

    from openpilot.selfdrive.rivian.scorerd import RivianScorer

    rlogs = _find_rlogs()
    if not rlogs:
        pytest.skip(
            "no route segment in tests/antigravity/routes/ "
            "(see routes/README.md to capture one from the comma)"
        )

    scorer = RivianScorer()
    lr = LogReader(rlogs[0])

    latest_future_y = None
    counts = {"carState": 0, "accelerometer": 0, "modelV2": 0}
    for msg in lr:
        which = msg.which()
        if which == "accelerometer":
            v = msg.accelerometer.acceleration.v
            if len(v) >= 2:
                scorer.update_accel(v[0], v[1])
                counts[which] += 1
        elif which == "modelV2":
            ys = msg.modelV2.position.y
            latest_future_y = ys[16] if len(ys) > 16 else latest_future_y
            scorer.update_model(ys[0] if len(ys) > 0 else None)
            counts[which] += 1
        elif which == "carState":
            scorer.update_carstate(msg.carState.vEgo, msg.carState.steeringRateDeg, latest_future_y)
            counts[which] += 1

    # carState is the core driving signal; a usable (onroad) segment must have it.
    if counts["carState"] == 0:
        pytest.skip("segment has no carState (likely an offroad capture); drop a driving segment")

    # The scorer must have processed real driving frames and produced well-formed
    # percentage scores. modelV2 is optional: not every capture contains it, and
    # path-accuracy is only meaningful when it does.
    assert scorer.total_smoothness_frames > 0
    assert 0.0 <= scorer.smoothness_score <= 100.0
    assert 0.0 <= scorer.path_accuracy_score <= 100.0
    if counts["modelV2"] > 0:
        assert scorer.total_path_frames > 0
