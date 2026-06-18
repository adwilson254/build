"""Fast unit tests for the Rivian scoring math (no cereal/Params needed)."""
from openpilot.selfdrive.rivian.scorerd import RivianScorer


def test_initial_scores_are_neutral():
    s = RivianScorer()
    # no frames yet -> denominators guarded, scores are 0/0-safe
    assert s.smoothness_score == 0.0
    assert s.path_accuracy_score == 0.0


def test_smooth_driving_scores_full_smoothness():
    s = RivianScorer()
    for _ in range(100):
        s.update_accel(0.1, 0.1)        # well under comfort threshold
        s.update_carstate(v_ego=30.0, steer_rate_deg=1.0, model_future_y=0.0)
    assert s.smoothness_score == 100.0


def test_jerky_acceleration_tanks_smoothness():
    s = RivianScorer()
    for _ in range(10):
        s.update_accel(5.0, 0.0)        # > JERKY_ACCEL (4.0)
        s.update_carstate(v_ego=30.0, steer_rate_deg=1.0, model_future_y=0.0)
    assert s.smoothness_score == 0.0


def test_uncomfortable_acceleration_is_half_credit():
    s = RivianScorer()
    for _ in range(10):
        s.update_accel(3.0, 0.0)        # between UNCOMFORTABLE (2) and JERKY (4)
        s.update_carstate(v_ego=30.0, steer_rate_deg=1.0, model_future_y=0.0)
    assert s.smoothness_score == 50.0


def test_low_speed_ping_pong_is_penalized():
    s = RivianScorer()
    # comfortable accel, but straight path + high steer rate at low speed
    for _ in range(10):
        s.update_accel(0.0, 0.0)
        s.update_carstate(v_ego=5.0, steer_rate_deg=30.0, model_future_y=0.0)
    assert s.smoothness_score == 50.0


def test_ping_pong_not_penalized_at_highway_speed():
    s = RivianScorer()
    for _ in range(10):
        s.update_accel(0.0, 0.0)
        s.update_carstate(v_ego=40.0, steer_rate_deg=30.0, model_future_y=0.0)  # >= PING_PONG_SPEED
    assert s.smoothness_score == 100.0


def test_path_accuracy_tracks_lane_center_deviation():
    s = RivianScorer()
    for _ in range(8):
        s.update_model(0.1)   # within ACCURACY_DEVIATION (0.3)
    for _ in range(2):
        s.update_model(1.0)   # outside
    assert s.path_accuracy_score == 80.0


def test_scores_always_bounded():
    s = RivianScorer()
    for i in range(50):
        s.update_accel(float(i % 6), 0.0)
        s.update_carstate(v_ego=float(i), steer_rate_deg=float(i), model_future_y=0.0)
        s.update_model(float(i) / 10.0)
    assert 0.0 <= s.smoothness_score <= 100.0
    assert 0.0 <= s.path_accuracy_score <= 100.0
