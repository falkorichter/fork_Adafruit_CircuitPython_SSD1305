#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
Integration test for mqtt_sensor_example_rich_streaming.py with static MQTT data.

This test simulates the full script execution with mock MQTT messages to verify
that all the key access issues have been resolved.
"""

import sys
import time
from pathlib import Path
from unittest.mock import Mock, patch
import json

sys.path.insert(0, str(Path(__file__).parent.parent))


def create_mock_mqtt_client():
    """Create a mock MQTT client that provides test data"""
    
    # Sample MQTT message matching the expected format
    sample_message = {
        "BME68x": {
            "TemperatureC": 22.5,
            "Humidity": 45.3,
            "Pressure": 101325,
            "Gas Resistance": 50000
        },
        "VEML7700": {
            "Lux": 150.2
        },
        "TMP117": {
            "Temperature (C)": 22.8
        },
        "STHS34PF80": {
            "Presence (cm^-1)": 1500,
            "Motion (LSB)": 5,
            "Temperature (C)": 23.1
        },
        "MAX17048": {
            "Voltage (V)": 4.15,
            "State Of Charge (%)": 85
        },
        "System Info": {
            "SSID": "TestNetwork",
            "RSSI": "-55 dBm"
        }
    }
    
    mock_client = Mock()
    
    # Store the message callbacks so we can trigger them
    callbacks = {}
    
    def on_connect_setter(callback):
        callbacks['on_connect'] = callback
        
    def on_message_setter(callback):
        callbacks['on_message'] = callback
    
    # Set up callback setters
    mock_client.on_connect = None
    mock_client.on_message = None
    
    # Override __setattr__ to capture callback assignments
    original_setattr = mock_client.__setattr__
    
    def custom_setattr(name, value):
        if name == 'on_connect':
            callbacks['on_connect'] = value
        elif name == 'on_message':
            callbacks['on_message'] = value
        original_setattr(name, value)
    
    mock_client.__setattr__ = custom_setattr
    
    # Simulate successful connection
    def mock_connect(host, port, keepalive=60):
        # Trigger on_connect callback immediately
        if 'on_connect' in callbacks and callbacks['on_connect']:
            callbacks['on_connect'](mock_client, None, None, 0)
    
    def mock_loop_start():
        # Simulate receiving a message shortly after starting
        if 'on_message' in callbacks and callbacks['on_message']:
            msg = Mock()
            msg.payload = json.dumps(sample_message).encode()
            callbacks['on_message'](mock_client, None, msg)
    
    mock_client.connect = mock_connect
    mock_client.loop_start = mock_loop_start
    mock_client.loop_stop = Mock()
    mock_client.disconnect = Mock()
    mock_client.subscribe = Mock()
    
    return mock_client


def test_integration():
    """Test the full mqtt_sensor_example_rich_streaming with mock MQTT data"""
    print("Testing mqtt_sensor_example_rich_streaming.py integration...\n")
    
    # Mock the MQTT client
    with patch('paho.mqtt.client.Client', side_effect=create_mock_mqtt_client):
        try:
            # Import after patching
            from sensor_plugins import MQTTPlugin
            from examples.mqtt_sensor_example_rich_streaming import create_layout
            
            # Create MQTT sensor plugin
            print("Creating MQTT plugin...")
            mqtt_sensor = MQTTPlugin(
                broker_host="localhost",
                broker_port=1883,
                topic="iot_logger",
                check_interval=0.1,  # Short interval for testing
                burn_in_time=1,  # Short burn-in for testing
            )
            
            # Wait a bit for mock connection
            time.sleep(0.2)
            
            # Read data multiple times to test different states
            print("Reading sensor data...")
            for i in range(3):
                data = mqtt_sensor.read()
                print(f"  Read #{i+1}: {len(data)} keys")
                
                # Create layout to test all key accesses
                layout = create_layout(data, mqtt_sensor)
                print(f"  Layout created successfully")
                
                time.sleep(0.5)
            
            # Verify all expected keys are present
            final_data = mqtt_sensor.read()
            expected_keys = [
                'temperature', 'humidity', 'pressure', 'gas_resistance', 'air_quality',
                'light', 'temp_c', 'voltage', 'soc', 'ssid', 'rssi',
                'presence_value', 'motion_value', 'sths34_temperature', 'person_detected'
            ]
            
            print("\nVerifying data keys:")
            for key in expected_keys:
                if key in final_data:
                    print(f"  ✓ {key}: {final_data[key]}")
                else:
                    print(f"  ✗ {key}: MISSING")
                    raise KeyError(f"Expected key '{key}' not found in data")
            
            print("\n" + "=" * 60)
            print("SUCCESS: Integration test passed!")
            print("=" * 60)
            print("\nThe mqtt_sensor_example_rich_streaming.py script should now")
            print("work correctly with real MQTT data.")
            
            return True
            
        except Exception as e:
            print(f"\n✗ FAILED: {e}")
            import traceback
            traceback.print_exc()
            return False


if __name__ == "__main__":
    success = test_integration()
    sys.exit(0 if success else 1)
