# SPDX-FileCopyrightText: 2026 Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
Tests for sensor plugin system
"""

import sys
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestSensorPlugin(unittest.TestCase):
    """Test the base SensorPlugin class"""

    def setUp(self):
        """Set up test fixtures"""
        from sensor_plugins import SensorPlugin

        class TestPlugin(SensorPlugin):
            """Concrete implementation for testing"""

            def _initialize_hardware(self):
                if not hasattr(self, "should_fail") or not self.should_fail:
                    return MagicMock()
                raise RuntimeError("Hardware not found")

            def _read_sensor_data(self):
                if hasattr(self, "read_should_fail") and self.read_should_fail:
                    raise RuntimeError("Read failed")
                return {"test_value": 42}

            def _get_unavailable_data(self):
                return {"test_value": "n/a"}

        self.TestPlugin = TestPlugin

    def test_sensor_available(self):
        """Test sensor when hardware is available"""
        plugin = self.TestPlugin("TestSensor")
        plugin.should_fail = False

        self.assertTrue(plugin.check_availability())
        self.assertTrue(plugin.available)

        data = plugin.read()
        self.assertEqual(data["test_value"], 42)

    def test_sensor_unavailable(self):
        """Test sensor when hardware is not available"""
        plugin = self.TestPlugin("TestSensor")
        plugin.should_fail = True

        self.assertFalse(plugin.check_availability())
        self.assertFalse(plugin.available)

        data = plugin.read()
        self.assertEqual(data["test_value"], "n/a")

    def test_check_interval(self):
        """Test that availability check respects interval"""
        plugin = self.TestPlugin("TestSensor", check_interval=10.0)
        plugin.should_fail = False

        # First check should initialize
        self.assertTrue(plugin.check_availability())
        
        # Immediate second check should use cached value
        self.assertTrue(plugin.check_availability())

        # Simulate hardware becoming unavailable
        # Force the sensor instance to None and set should_fail
        plugin.sensor_instance = None
        plugin.should_fail = True

        # After interval, should re-check and fail
        plugin.last_check_time = time.time() - 11.0
        self.assertFalse(plugin.check_availability())

    def test_read_failure_recovery(self):
        """Test that read failures mark sensor as unavailable"""
        plugin = self.TestPlugin("TestSensor")
        plugin.should_fail = False

        # Initial read should work
        data = plugin.read()
        self.assertEqual(data["test_value"], 42)

        # Make read fail
        plugin.read_should_fail = True
        data = plugin.read()
        self.assertEqual(data["test_value"], "n/a")
        self.assertFalse(plugin.available)

    def test_requires_background_updates_default(self):
        """Test that default sensor plugins do not require background updates"""
        plugin = self.TestPlugin("TestSensor")
        plugin.should_fail = False
        
        # Default should be False
        self.assertFalse(plugin.requires_background_updates)


class TestTMP117Plugin(unittest.TestCase):
    """Test TMP117 sensor plugin"""

    def setUp(self):
        """Set up mock sensor"""
        self.mock_sensor = MagicMock()
        self.mock_sensor.begin.return_value = True
        self.mock_sensor.read_temp_c.return_value = 23.5

        self.qwiic_module = MagicMock()
        self.qwiic_module.QwiicTMP117.return_value = self.mock_sensor

    def test_initialization(self):
        """Test TMP117 plugin initialization"""
        with patch.dict("sys.modules", {"qwiic_tmp117": self.qwiic_module}):
            from sensor_plugins import TMP117Plugin

            plugin = TMP117Plugin()
            self.assertEqual(plugin.name, "TMP117")

    def test_read_temperature(self):
        """Test reading temperature from TMP117"""
        with patch.dict("sys.modules", {"qwiic_tmp117": self.qwiic_module}):
            from sensor_plugins import TMP117Plugin

            plugin = TMP117Plugin()
            data = plugin.read()
            self.assertEqual(data["temp_c"], 23.5)

    def test_hardware_not_found(self):
        """Test TMP117 when hardware is not available"""
        self.mock_sensor.begin.return_value = False

        with patch.dict("sys.modules", {"qwiic_tmp117": self.qwiic_module}):
            from sensor_plugins import TMP117Plugin

            plugin = TMP117Plugin()
            data = plugin.read()
            self.assertEqual(data["temp_c"], "n/a")

    def test_unavailable_data(self):
        """Test TMP117 unavailable data format"""
        with patch.dict("sys.modules", {"qwiic_tmp117": self.qwiic_module}):
            from sensor_plugins import TMP117Plugin

            plugin = TMP117Plugin()
            data = plugin._get_unavailable_data()
            self.assertEqual(data["temp_c"], "n/a")


class TestVEML7700Plugin(unittest.TestCase):
    """Test VEML7700 sensor plugin"""

    def setUp(self):
        """Set up mock sensor"""
        self.mock_sensor = MagicMock()
        self.mock_sensor.light = 150.5

        self.veml_module = MagicMock()
        self.veml_module.VEML7700.return_value = self.mock_sensor

        self.board_module = MagicMock()

    def test_read_light(self):
        """Test reading light from VEML7700"""
        with patch.dict(
            "sys.modules",
            {"adafruit_veml7700": self.veml_module, "board": self.board_module},
        ):
            from sensor_plugins import VEML7700Plugin

            plugin = VEML7700Plugin()
            data = plugin.read()
            self.assertEqual(data["light"], 150.5)

    def test_unavailable_data(self):
        """Test VEML7700 unavailable data format"""
        with patch.dict(
            "sys.modules",
            {"adafruit_veml7700": self.veml_module, "board": self.board_module},
        ):
            from sensor_plugins import VEML7700Plugin

            plugin = VEML7700Plugin()
            data = plugin._get_unavailable_data()
            self.assertEqual(data["light"], "n/a")


class TestBME680Plugin(unittest.TestCase):
    """Test BME680 sensor plugin"""

    def setUp(self):
        """Set up mock sensor"""
        self.mock_data = MagicMock()
        self.mock_data.temperature = 22.5
        self.mock_data.humidity = 45.0
        self.mock_data.pressure = 1013.25
        self.mock_data.gas_resistance = 50000
        self.mock_data.heat_stable = True

        self.mock_sensor = MagicMock()
        self.mock_sensor.data = self.mock_data
        self.mock_sensor.get_sensor_data.return_value = True

        self.bme_module = MagicMock()
        self.bme_module.BME680.return_value = self.mock_sensor
        self.bme_module.I2C_ADDR_SECONDARY = 0x77
        self.bme_module.OS_2X = 2
        self.bme_module.OS_4X = 4
        self.bme_module.OS_8X = 8
        self.bme_module.FILTER_SIZE_3 = 3
        self.bme_module.ENABLE_GAS_MEAS = 1

    def test_initialization(self):
        """Test BME680 plugin initialization"""
        import tempfile
        
        with patch.dict("sys.modules", {"bme680": self.bme_module}):
            from sensor_plugins import BME680Plugin

            # Create a temporary non-existent cache file path
            with tempfile.NamedTemporaryFile(delete=True, suffix='.json') as f:
                cache_file = f.name
            # File is now deleted, so it won't load any cache
            
            plugin = BME680Plugin(burn_in_time=1.0, cache_file=cache_file)
            self.assertEqual(plugin.name, "BME680")
            self.assertFalse(plugin.burn_in_complete)

    def test_burn_in_period(self):
        """Test BME680 burn-in period"""
        import tempfile
        
        with patch.dict("sys.modules", {"bme680": self.bme_module}):
            from sensor_plugins import BME680Plugin

            # Create a temporary non-existent cache file path
            with tempfile.NamedTemporaryFile(delete=True, suffix='.json') as f:
                cache_file = f.name
            # File is now deleted, so it won't load any cache
            
            # Use a longer burn-in time to ensure we catch it in progress
            plugin = BME680Plugin(burn_in_time=10.0, cache_file=cache_file)
            data = plugin.read()

            # Should show burn-in remaining time
            self.assertIn("burn_in_remaining", data)

    def test_read_after_burn_in(self):
        """Test BME680 reading after burn-in"""
        with patch.dict("sys.modules", {"bme680": self.bme_module}):
            from sensor_plugins import BME680Plugin

            plugin = BME680Plugin(burn_in_time=0.0)
            # Force burn-in complete
            plugin.burn_in_complete = True
            plugin.gas_baseline = 50000

            data = plugin.read()

            self.assertNotEqual(data["temperature"], "n/a")
            self.assertNotEqual(data["humidity"], "n/a")
            self.assertNotEqual(data["air_quality"], "n/a")

    def test_unavailable_data(self):
        """Test BME680 unavailable data format"""
        with patch.dict("sys.modules", {"bme680": self.bme_module}):
            from sensor_plugins import BME680Plugin

            plugin = BME680Plugin()
            data = plugin._get_unavailable_data()
            self.assertEqual(data["temperature"], "n/a")
            self.assertEqual(data["humidity"], "n/a")
            self.assertEqual(data["air_quality"], "n/a")

    def test_cache_save_and_load(self):
        """Test BME680 burn-in cache save and load"""
        import tempfile
        
        with patch.dict("sys.modules", {"bme680": self.bme_module}):
            from sensor_plugins import BME680Plugin

            # Create a temporary cache file
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
                cache_file = f.name

            try:
                # Create plugin and set burn-in data
                plugin = BME680Plugin(burn_in_time=0.0, cache_file=cache_file)
                plugin.gas_baseline = 50000
                plugin.burn_in_complete = True
                
                # Save cache
                result = plugin._save_burn_in_cache()
                self.assertTrue(result)
                
                # Create new plugin and load cache
                plugin2 = BME680Plugin(burn_in_time=300, cache_file=cache_file)
                # Trigger initialization by calling read
                data = plugin2.read()
                # The cache should be loaded during initialization
                self.assertTrue(plugin2.burn_in_complete)
                self.assertEqual(plugin2.gas_baseline, 50000)
                # Should not show burn_in_remaining since cache was loaded
                self.assertNotIn("burn_in_remaining", data)
            finally:
                # Clean up
                import os
                if os.path.exists(cache_file):
                    os.remove(cache_file)

    def test_cache_expiry(self):
        """Test BME680 cache expiration after 1 hour"""
        import json
        import tempfile
        
        with patch.dict("sys.modules", {"bme680": self.bme_module}):
            from sensor_plugins import BME680Plugin

            # Create a temporary cache file with old timestamp
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
                cache_file = f.name
                # Write cache with timestamp from 2 hours ago
                old_cache = {
                    'gas_baseline': 50000,
                    'timestamp': time.time() - 7200  # 2 hours ago
                }
                json.dump(old_cache, f)

            try:
                # Create plugin - should not load expired cache
                plugin = BME680Plugin(burn_in_time=300, cache_file=cache_file)
                self.assertFalse(plugin.burn_in_complete)
                self.assertIsNone(plugin.gas_baseline)
            finally:
                # Clean up
                import os
                if os.path.exists(cache_file):
                    os.remove(cache_file)

    def test_cache_missing_file(self):
        """Test BME680 behavior when cache file doesn't exist"""
        import tempfile
        
        with patch.dict("sys.modules", {"bme680": self.bme_module}):
            from sensor_plugins import BME680Plugin

            # Create a temporary non-existent cache file path
            with tempfile.NamedTemporaryFile(delete=True, suffix='.json') as f:
                cache_file = f.name
            # File is now deleted, so it won't exist
            
            # Create plugin with non-existent cache file
            plugin = BME680Plugin(burn_in_time=300, cache_file=cache_file)
            self.assertFalse(plugin.burn_in_complete)
            self.assertIsNone(plugin.gas_baseline)

    def test_cache_invalid_json(self):
        """Test BME680 behavior with corrupted cache file"""
        import tempfile
        
        with patch.dict("sys.modules", {"bme680": self.bme_module}):
            from sensor_plugins import BME680Plugin

            # Create a temporary cache file with invalid JSON
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
                cache_file = f.name
                f.write("invalid json content {")

            try:
                # Create plugin - should handle invalid cache gracefully
                plugin = BME680Plugin(burn_in_time=300, cache_file=cache_file)
                self.assertFalse(plugin.burn_in_complete)
                self.assertIsNone(plugin.gas_baseline)
            finally:
                # Clean up
                import os
                if os.path.exists(cache_file):
                    os.remove(cache_file)

    def test_read_only_cache(self):
        """Test BME680 read-only cache mode doesn't write to cache"""
        import os
        import tempfile
        
        with patch.dict("sys.modules", {"bme680": self.bme_module}):
            from sensor_plugins import BME680Plugin

            # Create a temporary cache file path (file doesn't exist yet)
            with tempfile.NamedTemporaryFile(delete=True, suffix='.json') as f:
                cache_file = f.name
            # File is now deleted

            try:
                # Create plugin with read_only_cache=True and burn_in_time=0 to complete immediately
                plugin = BME680Plugin(burn_in_time=0.0, cache_file=cache_file, read_only_cache=True)
                
                # Trigger read which would normally save cache after burn-in completes
                plugin.read()
                
                # Cache file should not have been created since we're in read-only mode
                self.assertFalse(os.path.exists(cache_file),
                               "Read-only cache mode should not create cache file")
            finally:
                # Clean up
                if os.path.exists(cache_file):
                    os.remove(cache_file)

    def test_burn_in_data_size_limit(self):
        """Test that burn_in_data is limited to 50 samples"""
        with patch.dict("sys.modules", {"bme680": self.bme_module}):
            from sensor_plugins import BME680Plugin

            plugin = BME680Plugin(burn_in_time=1000)  # Long burn-in time
            plugin.start_time = time.time()
            
            # Simulate collecting 100 readings
            for _ in range(100):
                plugin.read()
            
            # burn_in_data should be limited to 50 samples
            self.assertLessEqual(len(plugin.burn_in_data), 50)

    def test_requires_background_updates(self):
        """Test that BME680 plugin requires background updates"""
        with patch.dict("sys.modules", {"bme680": self.bme_module}):
            from sensor_plugins import BME680Plugin

            plugin = BME680Plugin()
            # BME680 should always require background updates for burn-in and air quality
            self.assertTrue(plugin.requires_background_updates)


class TestSystemInfoPlugins(unittest.TestCase):
    """Test system information sensor plugins"""

    def test_ip_address_plugin(self):
        """Test IPAddressPlugin reads IP address"""
        from sensor_plugins import IPAddressPlugin

        plugin = IPAddressPlugin()
        data = plugin.read()
        self.assertIn("ip_address", data)
        self.assertIsNotNone(data["ip_address"])

    def test_cpu_load_plugin(self):
        """Test CPULoadPlugin reads CPU load"""
        from sensor_plugins import CPULoadPlugin

        plugin = CPULoadPlugin()
        data = plugin.read()
        self.assertIn("cpu_load", data)
        self.assertIsNotNone(data["cpu_load"])

    def test_memory_usage_plugin(self):
        """Test MemoryUsagePlugin reads memory usage"""
        from sensor_plugins import MemoryUsagePlugin

        plugin = MemoryUsagePlugin()
        data = plugin.read()
        self.assertIn("memory_usage", data)
        self.assertIsNotNone(data["memory_usage"])


class TestKeyboardPlugin(unittest.TestCase):
    """Test keyboard sensor plugin"""

    def setUp(self):
        """Set up mock evdev module"""
        # Create mock evdev module
        self.mock_evdev = MagicMock()
        self.mock_device = MagicMock()
        self.mock_evdev.InputDevice.return_value = self.mock_device
        self.mock_evdev.list_devices.return_value = ['/dev/input/event0']
        
        # Mock device capabilities
        self.mock_device.capabilities.return_value = {1: []}  # EV_KEY = 1
        
        # Mock key codes
        self.mock_evdev.ecodes = MagicMock()
        self.mock_evdev.ecodes.EV_KEY = 1
        self.mock_evdev.ecodes.KEY_A = 30
        self.mock_evdev.ecodes.KEY_B = 48
        self.mock_evdev.ecodes.KEY_C = 46
        self.mock_evdev.ecodes.KEY_D = 32
        self.mock_evdev.ecodes.KEY_E = 18
        self.mock_evdev.ecodes.KEY_SPACE = 57
        
        # Mock KeyEvent
        self.mock_evdev.KeyEvent = MagicMock()
        self.mock_evdev.KeyEvent.key_down = 1

    def test_initialization(self):
        """Test KeyboardPlugin initialization"""
        with patch.dict("sys.modules", {"evdev": self.mock_evdev}):
            from sensor_plugins import KeyboardPlugin

            plugin = KeyboardPlugin()
            self.assertEqual(plugin.name, "Keyboard")

    def test_unavailable_data(self):
        """Test KeyboardPlugin unavailable data format"""
        with patch.dict("sys.modules", {"evdev": self.mock_evdev}):
            from sensor_plugins import KeyboardPlugin

            plugin = KeyboardPlugin()
            data = plugin._get_unavailable_data()
            self.assertEqual(data["last_keys"], "n/a")

    def test_format_display_empty(self):
        """Test KeyboardPlugin format display with empty buffer"""
        with patch.dict("sys.modules", {"evdev": self.mock_evdev}):
            from sensor_plugins import KeyboardPlugin

            plugin = KeyboardPlugin()
            data = {"last_keys": ""}
            formatted = plugin.format_display(data)
            self.assertEqual(formatted, "Keys: _____")

    def test_format_display_with_keys(self):
        """Test KeyboardPlugin format display with keys"""
        with patch.dict("sys.modules", {"evdev": self.mock_evdev}):
            from sensor_plugins import KeyboardPlugin

            plugin = KeyboardPlugin()
            data = {"last_keys": "hello"}
            formatted = plugin.format_display(data)
            self.assertEqual(formatted, "Keys: hello")

    def test_format_display_right_aligned(self):
        """Test KeyboardPlugin format display is right-aligned"""
        with patch.dict("sys.modules", {"evdev": self.mock_evdev}):
            from sensor_plugins import KeyboardPlugin

            plugin = KeyboardPlugin()
            data = {"last_keys": "abc"}
            formatted = plugin.format_display(data)
            # Should be right-aligned with padding to 5 characters
            self.assertEqual(formatted, "Keys:   abc")

    def test_hardware_not_found(self):
        """Test KeyboardPlugin when hardware is not available"""
        # Mock no keyboard devices
        self.mock_evdev.list_devices.return_value = []
        
        with patch.dict("sys.modules", {"evdev": self.mock_evdev}):
            from sensor_plugins import KeyboardPlugin

            plugin = KeyboardPlugin()
            data = plugin.read()
            self.assertEqual(data["last_keys"], "n/a")


class TestMQTTPlugin(unittest.TestCase):
    """Test MQTT sensor plugin"""

    def setUp(self):
        """Set up mock MQTT client"""
        self.mock_client = MagicMock()
        self.mqtt_module = MagicMock()
        self.mqtt_module.Client.return_value = self.mock_client
        
        # Patch the paho module hierarchy
        self.paho_mock = MagicMock()
        self.paho_mqtt_mock = MagicMock()
        self.paho_mqtt_mock.client = self.mqtt_module
        self.paho_mock.mqtt = self.paho_mqtt_mock
        
        # Create a reusable patch dict
        self.paho_patches = {
            "paho": self.paho_mock,
            "paho.mqtt": self.paho_mqtt_mock,
            "paho.mqtt.client": self.mqtt_module
        }

    def test_initialization(self):
        """Test MQTT plugin initialization"""
        with patch.dict("sys.modules", self.paho_patches):
            from sensor_plugins import MQTTPlugin

            plugin = MQTTPlugin(broker_host="test.mosquitto.org", topic="test/topic")
            self.assertEqual(plugin.name, "MQTT")
            self.assertEqual(plugin.broker_host, "test.mosquitto.org")
            self.assertEqual(plugin.topic, "test/topic")

    def test_connection_success(self):
        """Test successful MQTT connection"""
        # Set up a side effect to trigger on_connect callback immediately when loop_start is called
        def trigger_on_connect_callback():
            """Simulate immediate connection success"""
            if hasattr(self.mock_client, 'on_connect') and callable(self.mock_client.on_connect):
                self.mock_client.on_connect(self.mock_client, None, None, 0)
        
        self.mock_client.loop_start.side_effect = trigger_on_connect_callback
        
        with patch.dict("sys.modules", {
            "paho": self.paho_mock,
            "paho.mqtt": self.paho_mqtt_mock,
            "paho.mqtt.client": self.mqtt_module
        }):
            from sensor_plugins import MQTTPlugin

            plugin = MQTTPlugin()
            # Force initialization by resetting last check time
            plugin.last_check_time = 0
            result = plugin.check_availability()
            # Connection should have succeeded
            self.assertTrue(result)
            self.assertTrue(plugin.available)
            self.mock_client.connect.assert_called()
            self.mock_client.loop_start.assert_called()
            self.mock_client.subscribe.assert_called()

    def test_connection_failure(self):
        """Test MQTT connection failure"""
        self.mock_client.connect.side_effect = Exception("Connection refused")
        
        with patch.dict("sys.modules", {
            "paho": self.paho_mock,
            "paho.mqtt": self.paho_mqtt_mock,
            "paho.mqtt.client": self.mqtt_module
        }):
            from sensor_plugins import MQTTPlugin

            plugin = MQTTPlugin()
            data = plugin.read()
            # Should return n/a values when connection fails
            self.assertEqual(data["temperature"], "n/a")
            self.assertEqual(data["humidity"], "n/a")
            self.assertFalse(plugin.available)

    def test_connection_timeout(self):
        """Test MQTT connection timeout when broker doesn't respond"""
        # Simulate connection that never completes - don't trigger on_connect callback
        # We need to mock time to avoid actually waiting 5 seconds
        with patch.dict("sys.modules", {
            "paho": self.paho_mock,
            "paho.mqtt": self.paho_mqtt_mock,
            "paho.mqtt.client": self.mqtt_module
        }):
            with patch('sensor_plugins.mqtt_plugin.time') as mock_time_module:
                # Simulate time advancing to trigger timeout
                # Need enough iterations to exceed 5 second timeout with 0.1s sleep intervals
                # Two initial calls (start time, first check) + 55 iterations = ~5.5 seconds
                time_values = [0.0, 0.0] + [0.1 * i for i in range(55)]
                mock_time_module.time.side_effect = time_values
                mock_time_module.sleep = MagicMock()  # Don't actually sleep
                
                from sensor_plugins import MQTTPlugin

                plugin = MQTTPlugin()
                data = plugin.read()
                # Should return n/a values when connection times out
                self.assertEqual(data["temperature"], "n/a")
                self.assertEqual(data["humidity"], "n/a")
                self.assertFalse(plugin.available)
                # loop_stop should have been called on timeout
                self.mock_client.loop_stop.assert_called()

    def test_parse_bme68x_data(self):
        """Test parsing BME68x data from MQTT message"""
        with patch.dict("sys.modules", self.paho_patches):
            from sensor_plugins import MQTTPlugin

            plugin = MQTTPlugin(burn_in_time=0)  # Skip burn-in for test
            plugin.sensor_instance = self.mock_client
            plugin.available = True
            plugin.burn_in_complete = True
            plugin.gas_baseline = 100000
            
            # Simulate received message
            plugin.message_received = True
            plugin.latest_message = {
                "BME68x": {
                    "Humidity": 36.19836,
                    "TemperatureC": 22.40555,
                    "Pressure": 99244.27,
                    "Gas Resistance": 29463.11,
                }
            }
            
            data = plugin._read_sensor_data()
            self.assertEqual(data["temperature"], 22.40555)
            self.assertEqual(data["humidity"], 36.19836)
            self.assertEqual(data["pressure"], 99244.27)
            self.assertEqual(data["gas_resistance"], 29463.11)
            self.assertNotEqual(data["air_quality"], "n/a")

    def test_parse_multiple_sensors(self):
        """Test parsing data from multiple sensors"""
        with patch.dict("sys.modules", self.paho_patches):
            from sensor_plugins import MQTTPlugin

            plugin = MQTTPlugin()
            plugin.sensor_instance = self.mock_client
            plugin.available = True
            plugin.message_received = True
            # Note: Test data uses actual values from real sensor payload (issue example)
            # Values like SOC > 100% and RSSI = 198 are non-standard but match real data
            plugin.latest_message = {
                "VEML7700": {"Lux": 50.688},
                "TMP117": {"Temperature (C)": 22.375},
                "MAX17048": {"Voltage (V)": 4.21, "State Of Charge (%)": 108.8906},
                "System Info": {"SSID": "vfExpress", "RSSI": 198},
            }

            data = plugin._read_sensor_data()
            self.assertEqual(data["light"], 50.688)
            self.assertEqual(data["temp_c"], 22.375)
            self.assertEqual(data["voltage"], 4.21)
            self.assertEqual(data["soc"], 108.8906)
            self.assertEqual(data["ssid"], "vfExpress")
            self.assertEqual(data["rssi"], 198)

    def test_no_message_received(self):
        """Test behavior when no MQTT message has been received"""
        with patch.dict("sys.modules", self.paho_patches):
            from sensor_plugins import MQTTPlugin

            plugin = MQTTPlugin()
            plugin.sensor_instance = self.mock_client
            plugin.available = True
            plugin.message_received = False

            data = plugin._read_sensor_data()
            # All values should be n/a
            self.assertEqual(data["temperature"], "n/a")
            self.assertEqual(data["light"], "n/a")
            self.assertEqual(data["temp_c"], "n/a")

    def test_parse_sths34pf80_data(self):
        """Test parsing STHS34PF80 data from MQTT message"""
        with patch.dict("sys.modules", self.paho_patches):
            from sensor_plugins import MQTTPlugin

            plugin = MQTTPlugin()
            plugin.sensor_instance = self.mock_client
            plugin.available = True
            plugin.message_received = True
            # Test data matching the issue example
            plugin.latest_message = {
                "STHS34PF80": {
                    "Presence (cm^-1)": 1377,
                    "Motion (LSB)": 24,
                    "Temperature (C)": 0,
                }
            }

            data = plugin._read_sensor_data()
            self.assertEqual(data["presence_value"], 1377)
            self.assertEqual(data["motion_value"], 24)
            self.assertEqual(data["sths34_temperature"], 0)
            # Verify person_detected is calculated correctly
            # With presence=1377 (>=1000) and motion=24 (>0), person should be detected
            self.assertTrue(data["person_detected"])

    def test_sths34pf80_person_detection(self):
        """Test STHS34PF80 person detection logic in MQTT plugin"""
        with patch.dict("sys.modules", self.paho_patches):
            from sensor_plugins import MQTTPlugin

            plugin = MQTTPlugin()
            plugin.sensor_instance = self.mock_client
            plugin.available = True
            plugin.message_received = True
            
            # Test 1: Person detected via high presence value
            plugin.latest_message = {
                "STHS34PF80": {
                    "Presence (cm^-1)": 1500,
                    "Motion (LSB)": 0,
                    "Temperature (C)": 0,
                }
            }
            data = plugin._read_sensor_data()
            self.assertTrue(data["person_detected"])
            
            # Test 2: Person detected via motion
            plugin.latest_message = {
                "STHS34PF80": {
                    "Presence (cm^-1)": 500,
                    "Motion (LSB)": 10,
                    "Temperature (C)": 0,
                }
            }
            data = plugin._read_sensor_data()
            self.assertTrue(data["person_detected"])
            
            # Test 3: No person detected (low values)
            plugin.latest_message = {
                "STHS34PF80": {
                    "Presence (cm^-1)": 500,
                    "Motion (LSB)": 0,
                    "Temperature (C)": 0,
                }
            }
            data = plugin._read_sensor_data()
            self.assertFalse(data["person_detected"])
            
            # Test 4: Edge case - exactly at threshold
            plugin.latest_message = {
                "STHS34PF80": {
                    "Presence (cm^-1)": 1000,
                    "Motion (LSB)": 0,
                    "Temperature (C)": 0,
                }
            }
            data = plugin._read_sensor_data()
            self.assertTrue(data["person_detected"])

    def test_air_quality_calculation(self):
        """Test BME68x air quality calculation similar to BME680Plugin"""
        with patch.dict("sys.modules", self.paho_patches):
            from sensor_plugins import MQTTPlugin

            plugin = MQTTPlugin(burn_in_time=0)
            plugin.sensor_instance = self.mock_client
            plugin.available = True
            plugin.burn_in_complete = True
            plugin.gas_baseline = 50000
            plugin.message_received = True
            
            # Test with good air quality (gas resistance near baseline)
            plugin.latest_message = {
                "BME68x": {
                    "Humidity": 40.0,
                    "TemperatureC": 22.0,
                    "Pressure": 1013.25,
                    "Gas Resistance": 50000,
                }
            }
            
            data = plugin._read_sensor_data()
            air_quality = data["air_quality"]
            self.assertNotEqual(air_quality, "n/a")
            self.assertIsInstance(air_quality, (int, float))
            # Air quality should be a reasonable value (0-100 scale)
            self.assertGreaterEqual(air_quality, 0)

    def test_requires_background_updates(self):
        """Test that MQTT plugin requires background updates"""
        with patch.dict("sys.modules", self.paho_patches):
            from sensor_plugins import MQTTPlugin

            plugin = MQTTPlugin()
            self.assertTrue(plugin.requires_background_updates)

    def test_format_display(self):
        """Test display formatting"""
        with patch.dict("sys.modules", self.paho_patches):
            from sensor_plugins import MQTTPlugin

            plugin = MQTTPlugin()
            
            # Test burn-in display
            data = {"burn_in_remaining": 150}
            display = plugin.format_display(data)
            self.assertIn("150", display)
            self.assertIn("Burn-in", display)
            
            # Test air quality display
            data = {"air_quality": 75.5}
            display = plugin.format_display(data)
            self.assertIn("75.5", display)
            self.assertIn("AirQ", display)
            
            # Test n/a display
            data = {"air_quality": "n/a"}
            display = plugin.format_display(data)
            self.assertIn("n/a", display)

    def test_connection_timeout(self):
        """Test MQTT connection timeout when broker doesn't respond"""
        with patch.dict("sys.modules", {"paho.mqtt.client": self.mqtt_module}):
            from sensor_plugins import MQTTPlugin

            # Mock connect to succeed but loop_start doesn't trigger on_connect callback
            # This simulates a broker that accepts connections but doesn't complete handshake
            plugin = MQTTPlugin()
            
            # Force a timeout by preventing the callback from being called
            # The timeout is 5 seconds, but we don't want tests to wait that long
            with patch('time.time') as mock_time:
                # First call returns 0 (start time)
                # Second call returns 10 (past the timeout)
                mock_time.side_effect = [0, 10]
                
                data = plugin.read()
                # Should return n/a values when connection times out
                self.assertEqual(data["temperature"], "n/a")
                self.assertEqual(data["humidity"], "n/a")
                self.assertFalse(plugin.available)


class TestSTHS34PF80Plugin(unittest.TestCase):
    """Test STHS34PF80 sensor plugin"""

    def setUp(self):
        """Set up mock sensor"""
        self.mock_sensor = MagicMock()
        self.mock_sensor.presence_value = 1500
        self.mock_sensor.motion_value = 50
        self.mock_sensor.ambient_temperature = 22.5

        self.sths_module = MagicMock()
        self.sths_module.STHS34PF80.return_value = self.mock_sensor

        self.board_module = MagicMock()

    def test_read_presence_motion(self):
        """Test reading presence and motion from STHS34PF80"""
        with patch.dict(
            "sys.modules",
            {"adafruit_sths34pf80": self.sths_module, "board": self.board_module},
        ):
            from sensor_plugins import STHS34PF80Plugin

            plugin = STHS34PF80Plugin()
            data = plugin.read()
            self.assertEqual(data["presence_value"], 1500)
            self.assertEqual(data["motion_value"], 50)
            self.assertEqual(data["temperature"], 22.5)
            self.assertTrue(data["person_present"])

    def test_person_not_present(self):
        """Test when presence value is below threshold"""
        self.mock_sensor.presence_value = 500  # Below default threshold of 1000

        with patch.dict(
            "sys.modules",
            {"adafruit_sths34pf80": self.sths_module, "board": self.board_module},
        ):
            from sensor_plugins import STHS34PF80Plugin

            plugin = STHS34PF80Plugin()
            data = plugin.read()
            self.assertEqual(data["presence_value"], 500)
            self.assertFalse(data["person_present"])

    def test_custom_threshold(self):
        """Test custom presence threshold"""
        self.mock_sensor.presence_value = 1200

        with patch.dict(
            "sys.modules",
            {"adafruit_sths34pf80": self.sths_module, "board": self.board_module},
        ):
            from sensor_plugins import STHS34PF80Plugin

            # With threshold 1500, should not detect presence
            plugin = STHS34PF80Plugin(presence_threshold=1500)
            data = plugin.read()
            self.assertFalse(data["person_present"])

            # With threshold 1000, should detect presence
            plugin2 = STHS34PF80Plugin(presence_threshold=1000)
            data2 = plugin2.read()
            self.assertTrue(data2["person_present"])

            # With threshold equal to value (1200), should detect presence (>=)
            plugin3 = STHS34PF80Plugin(presence_threshold=1200)
            data3 = plugin3.read()
            self.assertTrue(data3["person_present"])

    def test_unavailable_data(self):
        """Test STHS34PF80 unavailable data format"""
        with patch.dict(
            "sys.modules",
            {"adafruit_sths34pf80": self.sths_module, "board": self.board_module},
        ):
            from sensor_plugins import STHS34PF80Plugin

            plugin = STHS34PF80Plugin()
            data = plugin._get_unavailable_data()
            self.assertEqual(data["presence_value"], "n/a")
            self.assertEqual(data["motion_value"], "n/a")
            self.assertEqual(data["temperature"], "n/a")
            self.assertEqual(data["person_present"], "n/a")

    def test_format_display_present(self):
        """Test display formatting when person is present"""
        with patch.dict(
            "sys.modules",
            {"adafruit_sths34pf80": self.sths_module, "board": self.board_module},
        ):
            from sensor_plugins import STHS34PF80Plugin

            plugin = STHS34PF80Plugin()
            data = {"person_present": True, "presence_value": 1500}
            display = plugin.format_display(data)
            self.assertIn("PRESENT", display)
            self.assertIn("1500", display)

    def test_format_display_absent(self):
        """Test display formatting when person is absent"""
        with patch.dict(
            "sys.modules",
            {"adafruit_sths34pf80": self.sths_module, "board": self.board_module},
        ):
            from sensor_plugins import STHS34PF80Plugin

            plugin = STHS34PF80Plugin()
            data = {"person_present": False, "presence_value": 500}
            display = plugin.format_display(data)
            self.assertIn("ABSENT", display)
            self.assertIn("500", display)

    def test_format_display_unavailable(self):
        """Test display formatting when sensor is unavailable"""
        with patch.dict(
            "sys.modules",
            {"adafruit_sths34pf80": self.sths_module, "board": self.board_module},
        ):
            from sensor_plugins import STHS34PF80Plugin

            plugin = STHS34PF80Plugin()
            data = plugin._get_unavailable_data()
            display = plugin.format_display(data)
            self.assertIn("n/a", display)


class TestMagnetDetector(unittest.TestCase):
    """Test robust MAD-based magnet detector"""

    def test_calibration_phase(self):
        """No detection during calibration (< min_baseline_samples)"""
        from sensor_plugins.magnet_detector import MagnetDetector

        detector = MagnetDetector(min_baseline_samples=5)
        for _ in range(4):
            detected, _, z = detector.update(1.0)
            self.assertFalse(detected)
            self.assertEqual(z, 0.0)

    def test_detection_after_calibration(self):
        """Detect a large deviation after calibration completes"""
        from sensor_plugins.magnet_detector import MagnetDetector

        detector = MagnetDetector(min_baseline_samples=5, detection_sigma=5.0)
        for _ in range(5):
            detector.update(1.0)

        # Large outlier — should trigger detection
        detected, baseline, z = detector.update(10.0)
        self.assertTrue(detected)
        self.assertAlmostEqual(baseline, 1.0)
        self.assertGreater(z, 5.0)

    def test_no_false_positive_on_small_deviation(self):
        """Small deviation should NOT trigger detection"""
        from sensor_plugins.magnet_detector import MagnetDetector

        detector = MagnetDetector(min_baseline_samples=5, detection_sigma=5.0)
        for _ in range(10):
            detector.update(1.0)

        detected, _, _ = detector.update(1.02)
        self.assertFalse(detected)

    def test_hysteresis(self):
        """Verify Schmitt-trigger hysteresis between detect/release"""
        from sensor_plugins.magnet_detector import MagnetDetector

        detector = MagnetDetector(
            min_baseline_samples=5, detection_sigma=5.0, release_sigma=3.0
        )
        # Build baseline
        for _ in range(10):
            detector.update(1.0)

        # Trigger detection
        detected, _, _ = detector.update(10.0)
        self.assertTrue(detected)

        # Still above release threshold — stays detected
        detected, _, z = detector.update(5.0)
        # z should still be high because 5.0 is far from baseline of 1.0
        self.assertTrue(detected)

        # Return to baseline — release detection
        detected, _, _ = detector.update(1.0)
        self.assertFalse(detected)

    def test_baseline_not_polluted_during_detection(self):
        """Baseline must NOT update while magnet is detected"""
        from sensor_plugins.magnet_detector import MagnetDetector

        detector = MagnetDetector(min_baseline_samples=5, detection_sigma=5.0)
        for _ in range(10):
            detector.update(1.0)

        baseline_before = MagnetDetector._median(detector.clean_history)

        # Trigger detection, send many high readings
        for _ in range(20):
            detector.update(10.0)

        baseline_after = MagnetDetector._median(detector.clean_history)
        self.assertAlmostEqual(baseline_before, baseline_after)

    def test_bidirectional_detection(self):
        """Detect magnet removal (magnitude DROP from high baseline)"""
        from sensor_plugins.magnet_detector import MagnetDetector

        # Simulate sensor starting with a magnet nearby
        detector = MagnetDetector(min_baseline_samples=5, detection_sigma=5.0)
        for _ in range(10):
            detector.update(5.0)

        # Magnet removed → field drops to Earth's field
        detected, _, _ = detector.update(0.5)
        self.assertTrue(detected)

    def test_reset(self):
        """Reset clears all state"""
        from sensor_plugins.magnet_detector import MagnetDetector

        detector = MagnetDetector(min_baseline_samples=3)
        for _ in range(5):
            detector.update(1.0)
        detector.update(10.0)  # trigger

        detector.reset()
        self.assertEqual(len(detector.clean_history), 0)
        self.assertFalse(detector.magnet_detected)

    def test_median_calculation(self):
        """Verify static median helper"""
        from sensor_plugins.magnet_detector import MagnetDetector

        self.assertEqual(MagnetDetector._median([1, 2, 3]), 2.0)
        self.assertEqual(MagnetDetector._median([1, 2, 3, 4]), 2.5)
        self.assertEqual(MagnetDetector._median([5]), 5.0)


class TestMMC5983Plugin(unittest.TestCase):
    """Test MMC5983 magnetometer sensor plugin"""

    def setUp(self):
        """Set up mock sensor"""
        self.mock_sensor = MagicMock()
        self.mock_sensor.magnetic = (-0.38, -0.79, -0.64)
        self.mock_sensor.temperature = 16.0

        self.mmc_module = MagicMock()
        self.mmc_module.MMC5983.return_value = self.mock_sensor

        self.board_module = MagicMock()

    def test_read_magnetic_data(self):
        """Test reading magnetic field data from MMC5983"""
        with patch.dict(
            "sys.modules",
            {"adafruit_mmc56x3": self.mmc_module, "board": self.board_module},
        ):
            from sensor_plugins import MMC5983Plugin

            plugin = MMC5983Plugin()
            data = plugin.read()
            self.assertEqual(data["mag_x"], -0.38)
            self.assertEqual(data["mag_y"], -0.79)
            self.assertEqual(data["mag_z"], -0.64)
            self.assertEqual(data["temperature"], 16.0)
            # Check magnitude is calculated correctly
            self.assertIsInstance(data["magnitude"], float)
            self.assertGreater(data["magnitude"], 0)

    def test_magnitude_calculation(self):
        """Test 3D vector magnitude calculation"""
        with patch.dict(
            "sys.modules",
            {"adafruit_mmc56x3": self.mmc_module, "board": self.board_module},
        ):
            from sensor_plugins import MMC5983Plugin

            plugin = MMC5983Plugin()
            # Test with known values: sqrt(3^2 + 4^2 + 0^2) = 5
            magnitude = plugin._calculate_magnitude(3.0, 4.0, 0.0)
            self.assertAlmostEqual(magnitude, 5.0, places=5)

    def test_baseline_calculation(self):
        """Test MAD-based baseline calculation"""
        with patch.dict(
            "sys.modules",
            {"adafruit_mmc56x3": self.mmc_module, "board": self.board_module},
        ):
            from sensor_plugins import MMC5983Plugin

            plugin = MMC5983Plugin(baseline_samples=50, min_baseline_samples=3)
            
            # Detector starts with empty clean history
            self.assertEqual(len(plugin.detector.clean_history), 0)
            
            # Feed stable values through the detector
            plugin.detector.update(1.0)
            plugin.detector.update(1.0)
            plugin.detector.update(1.0)
            
            # Baseline (median) should be 1.0
            _, baseline, _ = plugin.detector.update(1.0)
            self.assertAlmostEqual(baseline, 1.0)

    def test_magnet_detection(self):
        """Test magnet proximity detection via MagnetDetector"""
        with patch.dict(
            "sys.modules",
            {"adafruit_mmc56x3": self.mmc_module, "board": self.board_module},
        ):
            from sensor_plugins import MMC5983Plugin

            plugin = MMC5983Plugin(
                min_baseline_samples=5,
                detection_sigma=5.0,
                release_sigma=3.0,
            )
            
            # No detection during calibration
            for _ in range(5):
                detected, _, _ = plugin.detector.update(1.0)
                self.assertFalse(detected)
            
            # Small deviation — no detection
            detected, _, _ = plugin.detector.update(1.02)
            self.assertFalse(detected)
            
            # Huge deviation — magnet detected
            detected, _, _ = plugin.detector.update(5.0)
            self.assertTrue(detected)

    def test_magnet_detection_with_reads(self):
        """Test magnet detection through actual sensor reads"""
        with patch.dict(
            "sys.modules",
            {"adafruit_mmc56x3": self.mmc_module, "board": self.board_module},
        ):
            from sensor_plugins import MMC5983Plugin

            plugin = MMC5983Plugin(
                baseline_samples=50, min_baseline_samples=3,
                detection_sigma=5.0, release_sigma=3.0,
            )
            
            # Calibration reads
            self.mock_sensor.magnetic = (0.1, 0.0, 0.0)
            data = plugin.read()
            self.assertFalse(data["magnet_detected"])
            
            self.mock_sensor.magnetic = (0.1, 0.0, 0.0)
            data = plugin.read()
            self.assertFalse(data["magnet_detected"])
            
            self.mock_sensor.magnetic = (0.1, 0.0, 0.0)
            data = plugin.read()
            self.assertFalse(data["magnet_detected"])
            
            # Strong field (magnet close) — should be detected
            self.mock_sensor.magnetic = (5.0, 0.0, 0.0)
            data = plugin.read()
            self.assertTrue(data["magnet_detected"])

    def test_unavailable_data(self):
        """Test MMC5983 unavailable data format"""
        with patch.dict(
            "sys.modules",
            {"adafruit_mmc56x3": self.mmc_module, "board": self.board_module},
        ):
            from sensor_plugins import MMC5983Plugin

            plugin = MMC5983Plugin()
            data = plugin._get_unavailable_data()
            self.assertEqual(data["mag_x"], "n/a")
            self.assertEqual(data["mag_y"], "n/a")
            self.assertEqual(data["mag_z"], "n/a")
            self.assertEqual(data["magnitude"], "n/a")
            self.assertEqual(data["temperature"], "n/a")
            self.assertEqual(data["magnet_detected"], "n/a")
            self.assertEqual(data["baseline"], "n/a")
            self.assertEqual(data["detection_z_score"], "n/a")

    def test_format_display_normal(self):
        """Test display formatting with normal field"""
        with patch.dict(
            "sys.modules",
            {"adafruit_mmc56x3": self.mmc_module, "board": self.board_module},
        ):
            from sensor_plugins import MMC5983Plugin

            plugin = MMC5983Plugin()
            data = {"magnitude": 1.5, "magnet_detected": False}
            display = plugin.format_display(data)
            self.assertIn("1.5", display)
            self.assertNotIn("🧲", display)

    def test_format_display_magnet_detected(self):
        """Test display formatting when magnet is detected"""
        with patch.dict(
            "sys.modules",
            {"adafruit_mmc56x3": self.mmc_module, "board": self.board_module},
        ):
            from sensor_plugins import MMC5983Plugin

            plugin = MMC5983Plugin()
            data = {"magnitude": 5.0, "magnet_detected": True}
            display = plugin.format_display(data)
            self.assertIn("5.0", display)
            self.assertIn("🧲", display)

    def test_format_display_unavailable(self):
        """Test display formatting when sensor is unavailable"""
        with patch.dict(
            "sys.modules",
            {"adafruit_mmc56x3": self.mmc_module, "board": self.board_module},
        ):
            from sensor_plugins import MMC5983Plugin

            plugin = MMC5983Plugin()
            data = plugin._get_unavailable_data()
            display = plugin.format_display(data)
            self.assertIn("n/a", display)

    def test_requires_background_updates(self):
        """Test that MMC5983 plugin requires background updates"""
        with patch.dict(
            "sys.modules",
            {"adafruit_mmc56x3": self.mmc_module, "board": self.board_module},
        ):
            from sensor_plugins import MMC5983Plugin

            plugin = MMC5983Plugin()
            self.assertTrue(plugin.requires_background_updates)


class TestMQTTPluginMMC5983(unittest.TestCase):
    """Test MQTT plugin's MMC5983 data extraction"""

    def setUp(self):
        """Set up mock MQTT client"""
        self.mock_client = MagicMock()
        self.mqtt_module = MagicMock()
        self.mqtt_module.Client.return_value = self.mock_client

        self.paho_patches = {"paho.mqtt.client": self.mqtt_module}

    def test_mmc5983_data_extraction(self):
        """Test extracting MMC5983 data from MQTT message"""
        with patch.dict("sys.modules", self.paho_patches):
            from sensor_plugins import MQTTPlugin

            plugin = MQTTPlugin()
            plugin.sensor_instance = self.mock_client
            plugin.available = True
            plugin.message_received = True
            plugin.latest_message = {
                "MMC5983": {
                    "X Field (Gauss)": -0.382629,
                    "Y Field (Gauss)": -0.799194,
                    "Z Field (Gauss)": -0.648071,
                    "Temperature (C)": 16,
                }
            }

            data = plugin._read_sensor_data()
            self.assertAlmostEqual(data["mag_x"], -0.382629, places=5)
            self.assertAlmostEqual(data["mag_y"], -0.799194, places=5)
            self.assertAlmostEqual(data["mag_z"], -0.648071, places=5)
            self.assertEqual(data["mag_temperature"], 16)
            self.assertIsInstance(data["mag_magnitude"], float)
            self.assertGreater(data["mag_magnitude"], 0)

    def test_mmc5983_magnitude_calculation(self):
        """Test magnitude calculation in MQTT plugin"""
        with patch.dict("sys.modules", self.paho_patches):
            from sensor_plugins import MQTTPlugin

            plugin = MQTTPlugin()
            plugin.sensor_instance = self.mock_client
            plugin.available = True
            plugin.message_received = True
            plugin.latest_message = {
                "MMC5983": {
                    "X Field (Gauss)": 3.0,
                    "Y Field (Gauss)": 4.0,
                    "Z Field (Gauss)": 0.0,
                    "Temperature (C)": 20,
                }
            }

            data = plugin._read_sensor_data()
            # sqrt(3^2 + 4^2 + 0^2) = 5.0
            self.assertAlmostEqual(data["mag_magnitude"], 5.0, places=5)

    def test_mmc5983_magnet_detection(self):
        """Test magnet detection logic in MQTT plugin"""
        with patch.dict("sys.modules", self.paho_patches):
            from sensor_plugins import MQTTPlugin

            plugin = MQTTPlugin(mag_min_baseline_samples=3)
            plugin.sensor_instance = self.mock_client
            plugin.available = True
            plugin.message_received = True

            # Establish baseline with 3 clean reads (magnitude = 1.0)
            plugin.latest_message = {
                "MMC5983": {
                    "X Field (Gauss)": 1.0,
                    "Y Field (Gauss)": 0.0,
                    "Z Field (Gauss)": 0.0,
                    "Temperature (C)": 20,
                }
            }
            for _ in range(3):
                data = plugin._read_sensor_data()
                self.assertAlmostEqual(data["mag_baseline"], 1.0)
                self.assertFalse(data["magnet_detected"])

            # Strong field — magnet detected (magnitude 5.0 >> baseline 1.0)
            plugin.latest_message = {
                "MMC5983": {
                    "X Field (Gauss)": 5.0,
                    "Y Field (Gauss)": 0.0,
                    "Z Field (Gauss)": 0.0,
                    "Temperature (C)": 20,
                }
            }
            data = plugin._read_sensor_data()
            self.assertTrue(data["magnet_detected"])

    def test_mmc5983_partial_data(self):
        """Test handling partial MMC5983 data"""
        with patch.dict("sys.modules", self.paho_patches):
            from sensor_plugins import MQTTPlugin

            plugin = MQTTPlugin()
            plugin.sensor_instance = self.mock_client
            plugin.available = True
            plugin.message_received = True

            # Missing Z field - should not calculate magnitude
            plugin.latest_message = {
                "MMC5983": {
                    "X Field (Gauss)": 1.0,
                    "Y Field (Gauss)": 2.0,
                    "Temperature (C)": 20,
                }
            }

            data = plugin._read_sensor_data()
            self.assertEqual(data["mag_x"], 1.0)
            self.assertEqual(data["mag_y"], 2.0)
            self.assertEqual(data["mag_z"], "n/a")
            self.assertEqual(data["mag_magnitude"], "n/a")
            self.assertEqual(data["magnet_detected"], "n/a")


if __name__ == "__main__":
    unittest.main()
