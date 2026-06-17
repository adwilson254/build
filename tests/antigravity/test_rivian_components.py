import unittest
from unittest.mock import MagicMock, patch
import os
import json
import asyncio

# OpenPilot mocking
os.environ["ZMQ"] = "1"
import sys

# Mock messaging to avoid ZMQ compilation issues if run on a basic env
sys.modules['cereal'] = MagicMock()
sys.modules['cereal.messaging'] = MagicMock()
sys.modules['serial'] = MagicMock()
sys.modules['aiohttp'] = MagicMock()
sys.modules['aiohttp.web'] = MagicMock()
sys.modules['serial'] = MagicMock()
sys.modules['setproctitle'] = MagicMock()
sys.modules['zstandard'] = MagicMock()
# realtime pulls in system.hardware (platform-specific); mock it for the fast gate
sys.modules['openpilot.common.realtime'] = MagicMock()

# Golden fixtures captured/shaped from the real Rivian GraphQL API.
FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def load_fixture(name):
    with open(os.path.join(FIXTURES, name)) as f:
        return json.load(f)

# Mock Params completely so we don't load the compiled params_pyx.so
mock_params = MagicMock()
class MockParams:
    def __init__(self): pass
    def get(self, key): return None
    def put(self, key, val): pass
    def put_bool(self, key, val): pass
    def get_bool(self, key): return False
    def put_nonblocking(self, key, val): pass

mock_params.Params = MockParams
sys.modules['openpilot.common.params'] = mock_params

# Mock swaglog completely so it doesn't load tici hardware paths
mock_swaglog = MagicMock()
sys.modules['openpilot.common.swaglog'] = mock_swaglog

# Manually mock web response classes
class MockResponse:
    def __init__(self, text="{}", status=200):
        self.text = text
        self.status = status

class MockWeb:
    json_response = lambda data, status=200: MockResponse(json.dumps(data), status)
    Response = lambda text, status=200: MockResponse(text, status)
    FileResponse = lambda path: MockResponse("file", 200)
    Application = MagicMock

sys.modules['aiohttp'].web = MockWeb
sys.modules['aiohttp.web'] = MockWeb

# Import the actual modules we want to test
from openpilot.selfdrive.rivian.api import RivianApi
from openpilot.selfdrive.rivian.mqttd import get_rivian_data
from openpilot.selfdrive.web_ui.webd import WebServer

class TestRivianComponents(unittest.TestCase):
    
    def test_rivian_api_headers(self):
        """Test that RivianApi correctly constructs headers for authentication."""
        api = RivianApi()
        
        # Test headers without auth
        headers = api.get_headers(require_auth=False)
        self.assertIn("User-Agent", headers)
        self.assertNotIn("U-Sess", headers)
        self.assertNotIn("Authorization", headers)

        # Inject mock session data
        api.session_data = {
            "csrf_token": "mock_csrf",
            "app_session_token": "mock_app",
            "user_session_token": "mock_user",
            "access_token": "mock_access"
        }
        
        # Test full auth headers
        full_headers = api.get_headers(require_auth=True)
        self.assertEqual(full_headers["Csrf-Token"], "mock_csrf")
        self.assertEqual(full_headers["A-Sess"], "mock_app")
        self.assertEqual(full_headers["U-Sess"], "mock_user")
        self.assertEqual(full_headers["Authorization"], "Bearer mock_access")

    @patch('openpilot.selfdrive.rivian.mqttd.RivianApi')
    def test_mqttd_parsing_logic(self, MockRivianApi):
        """Test that mqttd correctly parses Rivian API responses into flat MQTT topics."""
        # Setup mock params
        mock_params = MagicMock()
        mock_params.get.return_value = json.dumps({"access_token": "valid"}).encode('utf-8')
        
        # Setup mock API response from golden fixtures (real Rivian GraphQL shape)
        mock_api_instance = MockRivianApi.return_value
        mock_api_instance.get_user_info.return_value = load_fixture("rivian_user_info.json")
        mock_api_instance.get_vehicle_state.return_value = load_fixture("rivian_vehicle_state.json")
        
        # We must clear the fetch timer lock
        import openpilot.selfdrive.rivian.mqttd as mqttd
        mqttd.last_rivian_fetch_time = 0
        
        result = get_rivian_data("TEST_DONGLE", mock_params)
        
        # Verify the parsed topics
        self.assertIn("openpilot/TEST_DONGLE/rivian/battery/level_percent", result)
        self.assertEqual(result["openpilot/TEST_DONGLE/rivian/battery/level_percent"], 85.5)
        
        self.assertIn("openpilot/TEST_DONGLE/rivian/doors/front_left_closed", result)
        self.assertEqual(result["openpilot/TEST_DONGLE/rivian/doors/front_left_closed"], True)
        
        self.assertIn("openpilot/TEST_DONGLE/rivian/climate/interior_temp_c", result)
        self.assertEqual(result["openpilot/TEST_DONGLE/rivian/climate/interior_temp_c"], 22.0)
        
        # It also does a massive dynamic dump
        self.assertIn("openpilot/TEST_DONGLE/rivian/telemetry/batteryLevel", result)
        self.assertEqual(result["openpilot/TEST_DONGLE/rivian/telemetry/batteryLevel"], 85.5)
        # Temperature is converted from C to F in the massive dump!
        self.assertIn("openpilot/TEST_DONGLE/rivian/telemetry/cabinClimateInteriorTemperature", result)
        self.assertEqual(result["openpilot/TEST_DONGLE/rivian/telemetry/cabinClimateInteriorTemperature"], 71.6)

    def test_web_server_endpoints(self):
        """Test web server API param fetching/setting using mocked requests."""
        server = WebServer()
        
        # Mock request for get_param
        class MockRequest:
            def __init__(self, key, payload=None):
                self.match_info = {'key': key}
                self.payload = payload
                
            async def json(self):
                return self.payload
        
        # Mock params inside WebServer
        server.params = MagicMock()
        server.params.get.return_value = b'100.0'
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Test GET
        req = MockRequest('RivianSmoothnessScore')
        response = loop.run_until_complete(server.get_param(req))
        self.assertEqual(response.status, 200)
        resp_data = json.loads(response.text)
        self.assertEqual(resp_data['key'], 'RivianSmoothnessScore')
        self.assertEqual(resp_data['value'], '100.0')

        # Test POST
        server.params.put = MagicMock()
        req_post = MockRequest('MqttEnabled', {'value': True})
        response_post = loop.run_until_complete(server.set_param(req_post))
        self.assertEqual(response_post.status, 200)
        
        # It should use put_bool since we passed a bool
        server.params.put_bool.assert_called_with('MqttEnabled', True)
        
        loop.close()

if __name__ == '__main__':
    unittest.main()
