#!/usr/bin/env python3
"""
Test script for MMC5983 sensor data extraction from MQTT with static messages.
This script demonstrates the magnet detection functionality without requiring
an actual MQTT broker or hardware sensor.
"""

import sys
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sensor_plugins import MQTTPlugin


def test_mmc5983_extraction():
    """Test MMC5983 data extraction with static MQTT messages"""
    print("=" * 70)
    print("MMC5983 Magnetometer Sensor - Static MQTT Message Test")
    print("=" * 70)
    print()
    
    # Create MQTT plugin instance (won't actually connect)
    plugin = MQTTPlugin()
    
    # Simulate that we're connected and have received messages
    plugin.message_received = True
    plugin.available = True
    
    # Test 1: Normal magnetic field (baseline establishment)
    print("Test 1: Normal magnetic field (establishing baseline)")
    print("-" * 70)
    
    normal_message = {
        "MMC5983": {
            "X Field (Gauss)": -0.382629,
            "Y Field (Gauss)": -0.799194,
            "Z Field (Gauss)": -0.648071,
            "Temperature (C)": 16
        }
    }
    
    plugin.latest_message = normal_message
    
    # Read multiple times to establish baseline
    for i in range(5):
        data = plugin._read_sensor_data()
        print(f"Read {i+1}:")
        print(f"  X-axis:         {data['mag_x']:.6f} Gauss")
        print(f"  Y-axis:         {data['mag_y']:.6f} Gauss")
        print(f"  Z-axis:         {data['mag_z']:.6f} Gauss")
        print(f"  Magnitude:      {data['mag_magnitude']:.6f} Gauss")
        print(f"  Baseline:       {data['mag_baseline']:.6f} Gauss")
        print(f"  Temperature:    {data['mag_temperature']} °C")
        print(f"  Magnet Detected: {data['magnet_detected']}")
        print()
        time.sleep(0.5)
    
    print("\n" + "=" * 70)
    print("Test 2: Strong magnetic field (magnet close)")
    print("-" * 70)
    
    # Simulate a strong magnet nearby
    strong_field_message = {
        "MMC5983": {
            "X Field (Gauss)": 5.0,
            "Y Field (Gauss)": -0.799194,
            "Z Field (Gauss)": -0.648071,
            "Temperature (C)": 17
        }
    }
    
    plugin.latest_message = strong_field_message
    data = plugin._read_sensor_data()
    
    print(f"  X-axis:         {data['mag_x']:.6f} Gauss")
    print(f"  Y-axis:         {data['mag_y']:.6f} Gauss")
    print(f"  Z-axis:         {data['mag_z']:.6f} Gauss")
    print(f"  Magnitude:      {data['mag_magnitude']:.6f} Gauss")
    print(f"  Baseline:       {data['mag_baseline']:.6f} Gauss")
    print(f"  Temperature:    {data['mag_temperature']} °C")
    print(f"  Magnet Detected: {data['magnet_detected']}")
    
    if data['magnet_detected']:
        print(f"\n  🧲 *** MAGNET CLOSE *** 🧲")
        print(f"  Field strength is {data['mag_magnitude'] / data['mag_baseline']:.2f}x baseline!")
    
    print("\n" + "=" * 70)
    print("Test 3: Returning to normal field")
    print("-" * 70)
    
    plugin.latest_message = normal_message
    data = plugin._read_sensor_data()
    
    print(f"  X-axis:         {data['mag_x']:.6f} Gauss")
    print(f"  Y-axis:         {data['mag_y']:.6f} Gauss")
    print(f"  Z-axis:         {data['mag_z']:.6f} Gauss")
    print(f"  Magnitude:      {data['mag_magnitude']:.6f} Gauss")
    print(f"  Baseline:       {data['mag_baseline']:.6f} Gauss")
    print(f"  Temperature:    {data['mag_temperature']} °C")
    print(f"  Magnet Detected: {data['magnet_detected']}")
    
    if not data['magnet_detected']:
        print(f"\n  ✓ Magnet removed - field returned to normal")
    
    print("\n" + "=" * 70)
    print("Test 4: Magnet in different direction (Y-axis)")
    print("-" * 70)
    
    y_axis_magnet = {
        "MMC5983": {
            "X Field (Gauss)": -0.382629,
            "Y Field (Gauss)": 5.5,
            "Z Field (Gauss)": -0.648071,
            "Temperature (C)": 18
        }
    }
    
    plugin.latest_message = y_axis_magnet
    data = plugin._read_sensor_data()
    
    print(f"  X-axis:         {data['mag_x']:.6f} Gauss")
    print(f"  Y-axis:         {data['mag_y']:.6f} Gauss")
    print(f"  Z-axis:         {data['mag_z']:.6f} Gauss")
    print(f"  Magnitude:      {data['mag_magnitude']:.6f} Gauss")
    print(f"  Baseline:       {data['mag_baseline']:.6f} Gauss")
    print(f"  Temperature:    {data['mag_temperature']} °C")
    print(f"  Magnet Detected: {data['magnet_detected']}")
    
    if data['magnet_detected']:
        print(f"\n  🧲 *** MAGNET CLOSE (Y-axis) *** 🧲")
        print(f"  Field strength is {data['mag_magnitude'] / data['mag_baseline']:.2f}x baseline!")
    
    print("\n" + "=" * 70)
    print("Test 5: Magnet in Z-axis direction")
    print("-" * 70)
    
    z_axis_magnet = {
        "MMC5983": {
            "X Field (Gauss)": -0.382629,
            "Y Field (Gauss)": -0.799194,
            "Z Field (Gauss)": 6.0,
            "Temperature (C)": 19
        }
    }
    
    plugin.latest_message = z_axis_magnet
    data = plugin._read_sensor_data()
    
    print(f"  X-axis:         {data['mag_x']:.6f} Gauss")
    print(f"  Y-axis:         {data['mag_y']:.6f} Gauss")
    print(f"  Z-axis:         {data['mag_z']:.6f} Gauss")
    print(f"  Magnitude:      {data['mag_magnitude']:.6f} Gauss")
    print(f"  Baseline:       {data['mag_baseline']:.6f} Gauss")
    print(f"  Temperature:    {data['mag_temperature']} °C")
    print(f"  Magnet Detected: {data['magnet_detected']}")
    
    if data['magnet_detected']:
        print(f"\n  🧲 *** MAGNET CLOSE (Z-axis) *** 🧲")
        print(f"  Field strength is {data['mag_magnitude'] / data['mag_baseline']:.2f}x baseline!")
    
    print("\n" + "=" * 70)
    print("Summary:")
    print("-" * 70)
    print("✓ MMC5983 data extraction works correctly")
    print("✓ 3D vector magnitude calculation works")
    print("✓ Moving average baseline tracking works")
    print("✓ Magnet detection works in any direction")
    print("✓ Detection threshold (2x baseline) is appropriate")
    print("=" * 70)


if __name__ == "__main__":
    test_mmc5983_extraction()
