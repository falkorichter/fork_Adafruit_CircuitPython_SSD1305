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
        import tempfile
        import os
        
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
                data = plugin.read()
                
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
                data = plugin.read()
            
            # burn_in_data should be limited to 50 samples
            self.assertLessEqual(len(plugin.burn_in_data), 50)


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


if __name__ == "__main__":
    unittest.main()
