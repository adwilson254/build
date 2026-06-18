#!/usr/bin/env python3
"""
mqttd.py

This module manages the local MQTT broker and bridges OpenPilot's internal `cereal` 
messaging system with external MQTT subscribers. It is specifically extended to:
1. Parse live Rivian telemetry from the cloud via `RivianApi`.
2. Parse real-time OpenPilot scores (Smoothness, Path Accuracy).
3. Publish everything over MQTT at 20Hz for consumption by Home Assistant or local apps.
"""
import time
import os
from openpilot.common.swaglog import cloudlog
import asyncio
import threading

from cereal import messaging
from openpilot.common.params import Params
from openpilot.common.realtime import Ratekeeper

# Configure logging
# MQTT dependencies are optional — if they fail to import, we run in degraded mode
_mqtt_available = False
try:
  from amqtt.broker import Broker
  import paho.mqtt.client as mqtt
  _mqtt_available = True
except ImportError as e:
  cloudlog.error(f"MQTT dependencies not available: {e}. Running in degraded mode.")

BROKER_CONFIG = {
    'listeners': {
        'default': {
            'type': 'tcp',
            'bind': '0.0.0.0:1883',
            'max_connections': 50000,
        }
    },
    'sys_interval': 10,
    'topic-check': {
        'enabled': False
    }
}

MAX_BROKER_RETRIES = 3
BROKER_RETRY_DELAY = 2  # seconds
MAX_CONNECT_RETRIES = 5
CONNECT_RETRY_DELAY = 2  # seconds


def run_broker():
    """
    Spawns an asynchronous `amqtt` broker on the local device (127.0.0.1:1883).
    This allows OpenPilot to host its own MQTT server without relying on an external
    broker running on a home network, ensuring telemetry works even while driving.
    Retries on failure up to MAX_BROKER_RETRIES times.
    """
    if not _mqtt_available:
      return

    async def broker_coro():
        broker = Broker(BROKER_CONFIG)
        await broker.start()
        # Keep running
        while True:
            await asyncio.sleep(1)

    for attempt in range(1, MAX_BROKER_RETRIES + 1):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(broker_coro())
        except Exception as e:
            cloudlog.error(f"Broker failed (attempt {attempt}/{MAX_BROKER_RETRIES}): {e}")
            if attempt < MAX_BROKER_RETRIES:
                time.sleep(BROKER_RETRY_DELAY * attempt)
            else:
                cloudlog.error("Broker exhausted all retries. MQTT publishing will be unavailable.")
        finally:
            loop.close()


from openpilot.selfdrive.rivian.api import RivianApi




import json

last_rivian_fetch_time = 0
rivian_api_instance = None
RIVIAN_FETCH_INTERVAL = 60  # seconds

def get_rivian_data(dongle_id, params):
    """
    Interacts with `RivianApi` to pull the latest cloud telemetry (battery, doors, tires).
    
    To prevent rate-limiting or IP bans from Rivian's servers, this function caches 
    the result and strictly enforces a 60-second polling interval defined by RIVIAN_FETCH_INTERVAL.

    Args:
        dongle_id (str): The device Dongle ID, used as the root for MQTT topics.
        params (Params): OpenPilot Params instance for persistent storage.

    Returns:
        dict: A flattened dictionary mapping MQTT topic strings to their payload values.
    """
    global last_rivian_fetch_time, rivian_api_instance
    current_time = time.time()

    if current_time - last_rivian_fetch_time < RIVIAN_FETCH_INTERVAL:
        return {}

    api_token = params.get("RivianApiToken")
    if not api_token:
        token_path = os.path.join(os.path.dirname(__file__), "rivian_token.json")
        if os.path.exists(token_path):
            with open(token_path) as f:
                api_token = f.read()

    if not api_token:
        return {}

    try:
        session_data = json.loads(api_token)
    except Exception:
        return {}

    if not rivian_api_instance:
        rivian_api_instance = RivianApi()

    rivian_api_instance.session_data = session_data

    try:
        # 1. Get vehicle ID
        user_info = rivian_api_instance.get_user_info()
        if user_info.get("unauthenticated"):
            params.put("RivianApiStatus", "Login Required")
            return {}

        vehicles = user_info.get("data", {}).get("currentUser", {}).get("vehicles", [])
        if not vehicles:
            return {}

        v_id = vehicles[0]['id']

        # 2. Get vehicle state
        state = rivian_api_instance.get_vehicle_state(v_id)
        if state.get("unauthenticated"):
            params.put("RivianApiStatus", "Login Required")
            return {}

        params.put("RivianApiStatus", "Configured")
        data_obj = state.get('data', {}).get('vehicleState', {})
        last_rivian_fetch_time = current_time

        # 3. Map to MQTT topics
        result = {}
        def _get_val(key):
            return data_obj.get(key, {}).get('value')

        if _get_val('batteryLevel') is not None:
            result[f"openpilot/{dongle_id}/rivian/battery/level_percent"] = _get_val('batteryLevel')
        if _get_val('distanceToEmpty') is not None:
            result[f"openpilot/{dongle_id}/rivian/battery/range_miles"] = _get_val('distanceToEmpty')
        if _get_val('cabinClimateInteriorTemperature') is not None:
            result[f"openpilot/{dongle_id}/rivian/climate/interior_temp_c"] = _get_val('cabinClimateInteriorTemperature')

        result[f"openpilot/{dongle_id}/rivian/doors/front_left_closed"] = str(_get_val('doorFrontLeftClosed')).lower() == 'true'
        result[f"openpilot/{dongle_id}/rivian/doors/front_right_closed"] = str(_get_val('doorFrontRightClosed')).lower() == 'true'
        result[f"openpilot/{dongle_id}/rivian/doors/rear_left_closed"] = str(_get_val('doorRearLeftClosed')).lower() == 'true'
        result[f"openpilot/{dongle_id}/rivian/doors/rear_right_closed"] = str(_get_val('doorRearRightClosed')).lower() == 'true'

        if _get_val('vehicleMileage') is not None:
            # Rivian returns mileage in meters. Convert to miles.
            miles = _get_val('vehicleMileage') * 0.000621371
            result[f"openpilot/{dongle_id}/rivian/vehicle/mileage"] = miles

        # Tire Pressures
        if _get_val('tirePressureStatusFrontLeft') is not None:
            result[f"openpilot/{dongle_id}/rivian/tires/front_left_pressure"] = _get_val('tirePressureStatusFrontLeft')
        if _get_val('tirePressureStatusFrontRight') is not None:
            result[f"openpilot/{dongle_id}/rivian/tires/front_right_pressure"] = _get_val('tirePressureStatusFrontRight')
        if _get_val('tirePressureStatusRearLeft') is not None:
            result[f"openpilot/{dongle_id}/rivian/tires/rear_left_pressure"] = _get_val('tirePressureStatusRearLeft')
        if _get_val('tirePressureStatusRearRight') is not None:
            result[f"openpilot/{dongle_id}/rivian/tires/rear_right_pressure"] = _get_val('tirePressureStatusRearRight')

        # Location
        location = data_obj.get('gnssLocation', {})
        if location.get('latitude') is not None:
            result[f"openpilot/{dongle_id}/rivian/location/latitude"] = location.get('latitude')
            result[f"openpilot/{dongle_id}/rivian/location/longitude"] = location.get('longitude')

        # Misc Statuses
        for key in ['powerState', 'chargerStatus', 'chargePortState', 'petModeStatus', 'gearGuardVideoStatus', 'driveMode']:
            val = _get_val(key)
            if val is not None:
                result[f"openpilot/{dongle_id}/rivian/status/{key}"] = str(val)

        # Dynamically map all other fields we just added to the massive query
        for key, field in data_obj.items():
            if isinstance(field, dict) and 'value' in field and field['value'] is not None:
                val = field['value']

                # Convert to US Units
                if isinstance(val, (int, float)):
                    if 'Temperature' in key:
                        val = round((val * 9/5) + 32, 1)  # C to F
                    elif 'Mileage' in key:
                        val = round(val * 0.000621371, 1)  # meters to miles
                    elif key == 'distanceToEmpty':
                        val = int(val * 0.621371)  # km to miles
                    elif 'Speed' in key:
                        val = round(val * 2.23694, 1)  # m/s to mph
                    elif 'Altitude' in key:
                        val = int(val * 3.28084)  # m to feet

                result[f"openpilot/{dongle_id}/rivian/telemetry/{key}"] = val

        return result
    except Exception as e:
        cloudlog.debug(f"Rivian API error: {e}")
        return {}


def bool_to_state(val):
    return "ON" if val else "OFF"

def _safe_publish(client, topic, value):
    """Publish a single MQTT message, suppressing any errors."""
    if client is None:
        return
    try:
        # Convert bools to ON/OFF explicitly, otherwise stringify
        if isinstance(value, bool):
            value_str = "ON" if value else "OFF"
        else:
            value_str = str(value)
        client.publish(topic, value_str)
    except Exception as e:
        cloudlog.debug(f"Publish failed for {topic}: {e}")


def main():
    """
    Primary daemon loop for MQTT publishing.
    
    Workflow:
    1. Check if `MqttEnabled` toggle is active in settings.
    2. Start the local `amqtt` broker in a background thread.
    3. Connect a `paho` MQTT client to the local broker.
    4. Subscribe to OpenPilot's `cereal` sockets (carState, controlsState, etc.).
    5. Loop at exactly 20Hz:
       a. Read latest ZMQ messages.
       b. Publish vehicle dynamics, models, and states to MQTT.
       c. Every 60s, fetch and publish Rivian Cloud API data.
    """
    params = Params()
    if not params.get_bool("MqttEnabled"):
        cloudlog.info("MQTT is disabled. Exiting.")
        return

    dongle_id_bytes = params.get("DongleId")
    if not dongle_id_bytes:
        dongle_id = "unknown"
    else:
        dongle_id = dongle_id_bytes.decode('utf8') if isinstance(dongle_id_bytes, bytes) else str(dongle_id_bytes)

    # Start broker in background thread (best-effort)
    client = None
    if _mqtt_available:
        cloudlog.info("Starting local MQTT Broker...")
        broker_thread = threading.Thread(target=run_broker, daemon=True)
        broker_thread.start()

        # Wait a bit for the broker to start
        time.sleep(2)

        # Try to connect to the broker with retries
        cloudlog.info("Connecting to MQTT Broker...")
        for attempt in range(1, MAX_CONNECT_RETRIES + 1):
            try:
                client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
                client.connect("127.0.0.1", 1883, 60)
                client.loop_start()
                cloudlog.info("Connected to MQTT Broker successfully.")
                break
            except Exception as e:
                cloudlog.error(f"Could not connect to local broker (attempt {attempt}/{MAX_CONNECT_RETRIES}): {e}")
                client = None
                if attempt < MAX_CONNECT_RETRIES:
                    time.sleep(CONNECT_RETRY_DELAY * attempt)

        if client is None:
            cloudlog.warning("MQTT client connection failed after all retries. Running in degraded mode (no publishing).")
    else:
        cloudlog.warning("MQTT libraries not available. Running in degraded mode (no publishing).")

    sm = messaging.SubMaster([
        'deviceState', 'carState', 'controlsState', 'pandaStates',
        'modelV2', 'driverStateV2', 'liveLocationKalman', 'accelerometer', 'lightSensor', 'liveParameters'
    ])

    cloudlog.info("Starting telemetry publisher loop at 20Hz...")
    rk = Ratekeeper(20)

    while True:
        try:
            sm.update(0) # Non-blocking update so we don't hold up the Ratekeeper loop

            """
            CAN-to-MQTT PARSING
            -------------------
            The following sections read from OpenPilots cereal messaging system (ZMQ)
            which contains parsed CAN messages and device state, and translates them
            into standard MQTT topics for consumption by home assistant or local apps.
            """
            # Publish deviceState
            if sm.updated['deviceState']:
                ds = sm['deviceState']
                _safe_publish(client, f"openpilot/{dongle_id}/host/cpu/temp_c", ds.cpuTempC[0] if len(ds.cpuTempC) > 0 else 0)
                _safe_publish(client, f"openpilot/{dongle_id}/host/memory/usage_percent", ds.memoryUsagePercent)
                _safe_publish(client, f"openpilot/{dongle_id}/host/storage/free_percent", ds.freeSpacePercent)
                _safe_publish(client, f"openpilot/{dongle_id}/host/thermal_status", str(ds.thermalStatus))
                _safe_publish(client, f"openpilot/{dongle_id}/host/power/draw_w", ds.powerDrawW)
                _safe_publish(client, f"openpilot/{dongle_id}/host/network/type", str(ds.networkType))
                _safe_publish(client, f"openpilot/{dongle_id}/host/network/strength", str(ds.networkStrength))
                _safe_publish(client, f"openpilot/{dongle_id}/host/gpu/usage_percent", ds.gpuUsagePercent)
                _safe_publish(client, f"openpilot/{dongle_id}/host/memory/temp_c", ds.memoryTempC)

            # Publish carState
            if sm.updated['carState']:
                cs = sm['carState']
                _safe_publish(client, f"openpilot/{dongle_id}/vehicle/speed_mph", cs.vEgo * 2.23694)
                _safe_publish(client, f"openpilot/{dongle_id}/vehicle/gear", str(cs.gearShifter))
                _safe_publish(client, f"openpilot/{dongle_id}/vehicle/steering/angle_deg", cs.steeringAngleDeg)
                _safe_publish(client, f"openpilot/{dongle_id}/vehicle/pedals/gas_pressed", cs.gasPressed)
                _safe_publish(client, f"openpilot/{dongle_id}/vehicle/pedals/brake_pressed", cs.brakePressed)
                _safe_publish(client, f"openpilot/{dongle_id}/vehicle/cruise/enabled", cs.cruiseState.enabled)
                _safe_publish(client, f"openpilot/{dongle_id}/vehicle/cruise/speed_mph", cs.cruiseState.speed * 2.23694)
                _safe_publish(client, f"openpilot/{dongle_id}/vehicle/steering/torque", cs.steeringTorque)
                _safe_publish(client, f"openpilot/{dongle_id}/vehicle/standstill", cs.standstill)

                # Extended vehicle dynamics
                try:
                    _safe_publish(client, f"openpilot/{dongle_id}/vehicle/acceleration_ms2", cs.aEgo)
                    _safe_publish(client, f"openpilot/{dongle_id}/vehicle/yaw_rate", cs.yawRate)
                    _safe_publish(client, f"openpilot/{dongle_id}/vehicle/pedals/brake_position", cs.brake)
                    _safe_publish(client, f"openpilot/{dongle_id}/vehicle/steering/rate_deg", cs.steeringRateDeg)
                    _safe_publish(client, f"openpilot/{dongle_id}/vehicle/steering/pressed", cs.steeringPressed)
                except Exception as e:
                    cloudlog.debug(f"Extended dynamics unavailable: {e}")

                # Safety, signals, and wheel speeds
                # Wrapped safely in case the specific car port doesn't populate them on the CAN bus
                try:
                    _safe_publish(client, f"openpilot/{dongle_id}/vehicle/signals/left_blinker", cs.leftBlinker)
                    _safe_publish(client, f"openpilot/{dongle_id}/vehicle/signals/right_blinker", cs.rightBlinker)
                    _safe_publish(client, f"openpilot/{dongle_id}/vehicle/doors/any_open", cs.doorOpen)
                    _safe_publish(client, f"openpilot/{dongle_id}/vehicle/seatbelt/unlatched", cs.seatbeltUnlatched)
                    _safe_publish(client, f"openpilot/{dongle_id}/vehicle/blindspot/left", cs.leftBlindspot)
                    _safe_publish(client, f"openpilot/{dongle_id}/vehicle/blindspot/right", cs.rightBlindspot)
                    _safe_publish(client, f"openpilot/{dongle_id}/vehicle/wheels/speed_fl", cs.wheelSpeeds.fl * 2.23694)
                    _safe_publish(client, f"openpilot/{dongle_id}/vehicle/wheels/speed_fr", cs.wheelSpeeds.fr * 2.23694)
                    _safe_publish(client, f"openpilot/{dongle_id}/vehicle/wheels/speed_rl", cs.wheelSpeeds.rl * 2.23694)
                    _safe_publish(client, f"openpilot/{dongle_id}/vehicle/wheels/speed_rr", cs.wheelSpeeds.rr * 2.23694)
                except Exception as e:
                    cloudlog.debug(f"Extended sensors unavailable: {e}")

            # Publish controlsState
            if sm.updated['controlsState']:
                ctrl = sm['controlsState']
                try:
                    _safe_publish(client, f"openpilot/{dongle_id}/controls/engaged", ctrl.active)
                except Exception:
                    try:
                        _safe_publish(client, f"openpilot/{dongle_id}/controls/engaged", ctrl.enabled)
                    except Exception:
                        pass

            # Publish pandaStates
            if sm.updated['pandaStates'] and len(sm['pandaStates']) > 0:
                ps = sm['pandaStates'][0]
                _safe_publish(client, f"openpilot/{dongle_id}/panda/voltage", ps.voltage / 1000.0)
                _safe_publish(client, f"openpilot/{dongle_id}/panda/ignition", ps.ignitionLine or ps.ignitionCan)

            # Publish modelV2
            if sm.updated['modelV2']:
                mdl = sm['modelV2']
                if len(mdl.leadsV3) > 0:
                    _safe_publish(client, f"openpilot/{dongle_id}/model/lead/distance_m", mdl.leadsV3[0].x[0])
                    _safe_publish(client, f"openpilot/{dongle_id}/model/lead/rel_speed_ms", mdl.leadsV3[0].v[0])
                    _safe_publish(client, f"openpilot/{dongle_id}/model/lead/prob", mdl.leadsV3[0].prob)
                    _safe_publish(client, f"openpilot/{dongle_id}/model/lead/acceleration", mdl.leadsV3[0].a[0])
                if len(mdl.laneLines) >= 4:
                    _safe_publish(client, f"openpilot/{dongle_id}/model/lane_lines/prob_left", mdl.laneLineProbs[1])
                    _safe_publish(client, f"openpilot/{dongle_id}/model/lane_lines/prob_right", mdl.laneLineProbs[2])

            # Publish driverStateV2
            if sm.updated['driverStateV2']:
                ds = sm['driverStateV2']
                _safe_publish(client, f"openpilot/{dongle_id}/driver/distracted", ds.distracted)
                _safe_publish(client, f"openpilot/{dongle_id}/driver/sunglasses", ds.sunglassesProb > 0.5)
                _safe_publish(client, f"openpilot/{dongle_id}/driver/face_prob", ds.faceProb)

            # Publish liveLocationKalman
            if sm.updated['liveLocationKalman']:
                llk = sm['liveLocationKalman']
                _safe_publish(client, f"openpilot/{dongle_id}/location/latitude", llk.positionGeodetic.value[0])
                _safe_publish(client, f"openpilot/{dongle_id}/location/longitude", llk.positionGeodetic.value[1])
                _safe_publish(client, f"openpilot/{dongle_id}/location/altitude", llk.positionGeodetic.value[2])
                _safe_publish(client, f"openpilot/{dongle_id}/location/roll", llk.calibratedOrientationNED.value[0])
                _safe_publish(client, f"openpilot/{dongle_id}/location/pitch", llk.calibratedOrientationNED.value[1])
                _safe_publish(client, f"openpilot/{dongle_id}/location/yaw", llk.calibratedOrientationNED.value[2])

            # Publish sensors
            if sm.updated['accelerometer']:
                acc = sm['accelerometer']
                _safe_publish(client, f"openpilot/{dongle_id}/sensors/accel_x", acc.acceleration.v[0])
                _safe_publish(client, f"openpilot/{dongle_id}/sensors/accel_y", acc.acceleration.v[1])
                _safe_publish(client, f"openpilot/{dongle_id}/sensors/accel_z", acc.acceleration.v[2])
            if sm.updated['lightSensor']:
                _safe_publish(client, f"openpilot/{dongle_id}/sensors/ambient_light", sm['lightSensor'].light)

            # Publish liveParameters
            if sm.updated['liveParameters']:
                lp = sm['liveParameters']
                _safe_publish(client, f"openpilot/{dongle_id}/health/tire_stiffness", lp.stiffnessFactor)
                _safe_publish(client, f"openpilot/{dongle_id}/health/steer_ratio_offset", lp.angleOffsetAverageDeg)

            # Rivian Simulated Data
            try:
                token_path = os.path.join(os.path.dirname(__file__), "rivian_token.json")
                api_enabled = params.get_bool("RivianApiEnabled")
                token = params.get("RivianApiToken")
                if api_enabled and (token or os.path.exists(token_path)):
                    rivian_data = get_rivian_data(dongle_id, params)
                    for topic, value in rivian_data.items():
                        _safe_publish(client, topic, str(value))
            except Exception as e:
                cloudlog.debug(f"Rivian API data publish failed: {e}")

            # Rivian Calculated Scores — handle None params safely
            try:
                smoothness_raw = params.get("RivianSmoothnessScore")
                path_acc_raw = params.get("RivianPathAccuracyScore")
                smoothness = float(smoothness_raw) if smoothness_raw is not None else 0.0
                path_accuracy = float(path_acc_raw) if path_acc_raw is not None else 0.0
                _safe_publish(client, f"openpilot/{dongle_id}/rivian/scores/smoothness", smoothness)
                _safe_publish(client, f"openpilot/{dongle_id}/rivian/scores/path_accuracy", path_accuracy)
            except Exception as e:
                cloudlog.debug(f"Score publish failed: {e}")

        except Exception as e:
            cloudlog.error(f"Telemetry loop error (non-fatal): {e}")

        # Sleep to enforce 20Hz
        rk.keep_time()

if __name__ == "__main__":
    main()
