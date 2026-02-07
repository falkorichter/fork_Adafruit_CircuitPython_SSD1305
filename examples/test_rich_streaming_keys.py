#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
Test script to verify mqtt_sensor_example_rich_streaming.py works with correct data keys.

This script tests that the rich streaming example can handle the data dictionary
returned by the MQTT plugin without KeyError exceptions.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# Import the functions we want to test
from examples.mqtt_sensor_example_rich_streaming import (
    create_sensor_table_left,
    create_sensor_table_right,
    create_layout,
)


class MockMQTTSensor:
    """Mock MQTT sensor for testing"""
    
    def __init__(self):
        self.broker_host = "localhost"
        self.broker_port = 1883
        self.topic = "iot_logger"
        self.available = True
    
    def format_display(self, data):
        """Mock format_display method"""
        return "MQTT: Test"


def get_sample_data():
    """Return sample data matching the MQTT plugin's data structure"""
    return {
        # BME680 environmental data
        "temperature": 22.5,
        "humidity": 45.3,
        "pressure": 101325,
        "gas_resistance": 50000,
        "air_quality": 75.5,
        
        # VEML7700 light sensor
        "light": 150.2,
        
        # TMP117 temperature sensor
        "temp_c": 22.8,  # Correct key name
        
        # STHS34PF80 presence sensor
        "presence_value": 1500,  # Correct key name
        "motion_value": 5,  # Correct key name
        "sths34_temperature": 23.1,  # Correct key name
        "person_detected": True,
        
        # MAX17048 battery monitor
        "voltage": 4.15,
        "soc": 85,
        
        # WiFi information
        "ssid": "TestNetwork",
        "rssi": "-55 dBm",
    }


def test_key_access():
    """Test that all data keys can be accessed without KeyError"""
    print("Testing mqtt_sensor_example_rich_streaming.py with correct data keys...\n")
    
    # Create mock sensor
    mqtt_sensor = MockMQTTSensor()
    
    # Get sample data
    data = get_sample_data()
    
    try:
        # Test creating left table (this is where the KeyError occurred)
        print("Testing create_sensor_table_left()...")
        left_table = create_sensor_table_left(data, mqtt_sensor)
        print("✓ Left table created successfully")
        
        # Test creating right table
        print("Testing create_sensor_table_right()...")
        right_table = create_sensor_table_right(data, mqtt_sensor)
        print("✓ Right table created successfully")
        
        # Test creating complete layout
        print("Testing create_layout()...")
        layout = create_layout(data, mqtt_sensor)
        print("✓ Layout created successfully")
        
        print("\n" + "=" * 60)
        print("SUCCESS: All tests passed!")
        print("=" * 60)
        print("\nThe rich_streaming example should now work correctly with")
        print("the MQTT plugin's data structure.")
        
        return True
        
    except KeyError as e:
        print(f"\n✗ FAILED: KeyError occurred - {e}")
        print("\nThe data key that caused the error was:", str(e))
        print("\nAvailable keys in data:", list(data.keys()))
        return False
    except Exception as e:
        print(f"\n✗ FAILED: Unexpected error - {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_key_access()
    sys.exit(0 if success else 1)
