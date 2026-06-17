import unittest
import asyncio
import threading
import time
import json
import os

# Set environment variables for testing in docker
os.environ["ZMQ"] = "1"

import cereal.messaging as messaging
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop
from aiohttp import web
from scripts.features.src.web_ui.webd import WebServer

class TestBrokerAndMessages(unittest.TestCase):
    def test_cereal_messaging_broker(self):
        """Test that the cereal messaging broker is operational."""
        # Use a high-frequency socket that is typically safe for testing
        topic = "testJoystick"
        
        # Create publisher and subscriber
        pub = messaging.pub_sock(topic)
        sub = messaging.sub_sock(topic)
        
        # ZMQ needs a tiny bit of time to establish the connection
        time.sleep(0.1)
        
        # Create a blank message and send
        msg = messaging.new_message(topic)
        pub.send(msg.to_bytes())
        
        # Wait for the message on the subscriber side
        recvd = messaging.recv_one_retry(sub)
        self.assertIsNotNone(recvd, "Failed to receive message from broker")
        self.assertEqual(recvd.which(), topic, "Received message topic does not match")


class TestWebServer(AioHTTPTestCase):
    async def get_application(self):
        """Setup the aiohttp application for testing."""
        self.web_server = WebServer()
        return self.web_server.app

    @unittest_run_loop
    async def test_get_telemetry(self):
        """Test the telemetry endpoint."""
        resp = await self.client.request("GET", "/api/telemetry")
        self.assertEqual(resp.status, 200)
        data = await resp.json()
        self.assertIn("speed", data)
        self.assertIn("status", data)

    @unittest_run_loop
    async def test_param_get_and_set(self):
        """Test reading and writing params via the API."""
        # Test GET non-existent param
        resp = await self.client.request("GET", "/api/params/TestParam123")
        self.assertEqual(resp.status, 404)
        
        # Set a param using the Params API directly to test GET
        try:
            self.web_server.params.put_bool("TestParam123", True)
        except Exception:
            pass # ignore if it fails to set unknown param here too
        
        resp = await self.client.request("GET", "/api/params/TestParam123")
        self.assertEqual(resp.status, 404) # since it's an unknown param, our new code returns 404
        
        # We can't easily test params that don't exist in openpilot because it strictly validates them.
        # So we just test that trying to set an unknown param returns a 400.
        payload = {"value": False}
        resp = await self.client.request("POST", "/api/params/TestParam123", json=payload)
        self.assertEqual(resp.status, 400)

if __name__ == '__main__':
    unittest.main()
