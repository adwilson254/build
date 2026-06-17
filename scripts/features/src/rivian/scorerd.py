#!/usr/bin/env python3
"""
scorerd.py

Calculates two proprietary driving metrics for OpenRivian:
1. Smoothness Score (0-100%): Penalizes jerky longitudinal acceleration and lateral "ping-ponging" (steering oscillation).
2. Path Accuracy Score (0-100%): Tracks how closely the vehicle follows the center of the lane model.

These scores are written to standard OpenPilot parameters and pushed via MQTT.

The scoring math lives in `RivianScorer`, which is intentionally free of any
`cereal`/`Params` dependency so it can be unit-tested with synthetic inputs and
validated against real recorded route data (see tests/antigravity).
"""
import math

# Speed below which low-speed steering "ping-pong" is penalized (40 mph -> m/s).
PING_PONG_SPEED = 40 * 0.44704


class RivianScorer:
  """Accumulates smoothness and path-accuracy metrics frame by frame.

  Decoupled from messaging so the exact same logic runs in the daemon, in unit
  tests, and over replayed route logs.
  """
  ACCURACY_DEVIATION = 0.3   # max lateral deviation (m) from lane center before penalizing accuracy
  UNCOMFORTABLE_ACCEL = 2.0  # "uncomfortable" g-force threshold (m/s^2)
  JERKY_ACCEL = 4.0          # "jerky" (harsh) g-force threshold (m/s^2)
  PING_PONG_SPEED = PING_PONG_SPEED

  def __init__(self):
    self.total_path_frames = 0
    self.accurate_path_frames = 0
    self.total_smoothness_frames = 0
    self.accumulated_smoothness = 0.0
    self.latest_accel_mag = 0.0

  def update_accel(self, accel_x: float, accel_y: float) -> None:
    self.latest_accel_mag = math.hypot(accel_x, accel_y)

  def update_carstate(self, v_ego: float, steer_rate_deg: float, model_future_y: float | None = None) -> None:
    frame_smoothness = 1.0

    # Evaluate acceleration thresholds
    if self.latest_accel_mag > self.JERKY_ACCEL:
      frame_smoothness = 0.0
    elif self.latest_accel_mag > self.UNCOMFORTABLE_ACCEL:
      frame_smoothness = 0.5

    # Evaluate ping-ponging penalty (only when the path ahead is straight)
    if model_future_y is not None:
      if v_ego < self.PING_PONG_SPEED and abs(model_future_y) < 0.5 and abs(steer_rate_deg) > 15.0:
        frame_smoothness = min(frame_smoothness, 0.5)

    self.accumulated_smoothness += frame_smoothness
    self.total_smoothness_frames += 1

  def update_model(self, model_y0: float | None) -> None:
    if model_y0 is not None:
      if abs(model_y0) < self.ACCURACY_DEVIATION:
        self.accurate_path_frames += 1
      self.total_path_frames += 1

  @property
  def smoothness_score(self) -> float:
    return (self.accumulated_smoothness / max(1, self.total_smoothness_frames)) * 100.0

  @property
  def path_accuracy_score(self) -> float:
    return (self.accurate_path_frames / max(1, self.total_path_frames)) * 100.0


def main():
  # Imported lazily so RivianScorer stays importable without compiled openpilot.
  from cereal import messaging
  from openpilot.common.params import Params

  sm = messaging.SubMaster(['carState', 'accelerometer', 'modelV2', 'liveLocationKalman'])
  params = Params()

  scorer = RivianScorer()

  # Reset scores at start
  params.put_nonblocking("RivianSmoothnessScore", 100.0)
  params.put_nonblocking("RivianPathAccuracyScore", 100.0)

  while True:
    sm.update()

    if sm.updated['accelerometer']:
      accel = sm['accelerometer'].acceleration.v
      scorer.update_accel(accel[0], accel[1])

    if sm.updated['carState']:
      model_future_y = None
      if len(sm['modelV2'].position.y) > 16:
        model_future_y = sm['modelV2'].position.y[16]
      scorer.update_carstate(sm['carState'].vEgo, sm['carState'].steeringRateDeg, model_future_y)

    if sm.updated['modelV2']:
      model_y0 = sm['modelV2'].position.y[0] if len(sm['modelV2'].position.y) > 0 else None
      scorer.update_model(model_y0)

      # Calculate scores and write to params at 20Hz (modelV2 rate)
      params.put_nonblocking("RivianSmoothnessScore", float(scorer.smoothness_score))
      params.put_nonblocking("RivianPathAccuracyScore", float(scorer.path_accuracy_score))


if __name__ == "__main__":
  main()
