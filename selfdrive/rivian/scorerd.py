#!/usr/bin/env python3
"""
scorerd.py

Calculates two proprietary driving metrics for OpenRivian:
1. Smoothness Score (0-100%): Penalizes jerky longitudinal acceleration and lateral "ping-ponging" (steering oscillation).
2. Path Accuracy Score (0-100%): Tracks how closely the vehicle follows the center of the lane model.

These scores are written to standard OpenPilot parameters and pushed via MQTT.
"""
import math
from cereal import messaging
from openpilot.common.params import Params

def main():
  sm = messaging.SubMaster(['carState', 'accelerometer', 'modelV2', 'liveLocationKalman'])
  params = Params()

  # Track variables for percentage-based scoring
  total_path_frames = 0
  accurate_path_frames = 0
  
  total_smoothness_frames = 0
  accumulated_smoothness = 0.0
  latest_accel_mag = 0.0

  # Constants
  ACCURACY_DEVIATION = 0.3 # Max allowed lateral deviation from lane center (in meters) before penalizing accuracy
  UNCOMFORTABLE_ACCEL = 2.0 # Threshold for "uncomfortable" longitudinal or lateral g-forces (m/s^2)
  JERKY_ACCEL = 4.0 # Threshold for "jerky" (harsh braking/acceleration) (m/s^2)
  PING_PONG_SPEED = 40 * 0.44704 # Max speed threshold (40 mph) to evaluate low-speed ping-pong penalties

  # Reset scores at start
  params.put_nonblocking("RivianSmoothnessScore", 100.0)
  params.put_nonblocking("RivianPathAccuracyScore", 100.0)

  while True:
    sm.update()

    if sm.updated['accelerometer']:
      accel_x = sm['accelerometer'].acceleration.v[0]
      accel_y = sm['accelerometer'].acceleration.v[1]
      latest_accel_mag = math.hypot(accel_x, accel_y)

    if sm.updated['carState']:
      frame_smoothness = 1.0
      
      # Evaluate acceleration thresholds
      if latest_accel_mag > JERKY_ACCEL:
        frame_smoothness = 0.0
      elif latest_accel_mag > UNCOMFORTABLE_ACCEL:
        frame_smoothness = 0.5
      
      # Evaluate ping-ponging penalty
      v_ego = sm['carState'].vEgo
      steer_rate = abs(sm['carState'].steeringRateDeg)
      
      # Check if model has enough points and path is straight
      if len(sm['modelV2'].position.y) > 16:
        future_y = abs(sm['modelV2'].position.y[16])
        if v_ego < PING_PONG_SPEED and future_y < 0.5 and steer_rate > 15.0:
          frame_smoothness = min(frame_smoothness, 0.5)

      accumulated_smoothness += frame_smoothness
      total_smoothness_frames += 1

    if sm.updated['modelV2']:
      if len(sm['modelV2'].position.y) > 0:
        dev = abs(sm['modelV2'].position.y[0]) 
        if dev < ACCURACY_DEVIATION:
          accurate_path_frames += 1
        total_path_frames += 1

      # Calculate scores and write to params at 20Hz (modelV2 rate)
      smoothness_score = (accumulated_smoothness / max(1, total_smoothness_frames)) * 100.0
      path_accuracy_score = (accurate_path_frames / max(1, total_path_frames)) * 100.0

      params.put_nonblocking("RivianSmoothnessScore", float(smoothness_score))
      params.put_nonblocking("RivianPathAccuracyScore", float(path_accuracy_score))

if __name__ == "__main__":
  main()
