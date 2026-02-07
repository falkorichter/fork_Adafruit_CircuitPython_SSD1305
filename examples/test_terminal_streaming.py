#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
Simple test script to verify terminal streaming works with mock MQTT data.

This script simulates the MQTT sensor example without needing a real MQTT broker.
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from terminal_streamer import TerminalStreamer


def test_terminal_streaming():
    """Test the terminal streamer with simulated output"""
    print("=" * 60)
    print("Testing Terminal Streamer")
    print("=" * 60)
    
    # Create streamer
    streamer = TerminalStreamer()
    
    # Track captured output
    captured = []
    
    def capture_callback(text):
        captured.append(text)
        # Also log to file for verification
        with open("/tmp/terminal_capture.log", "a") as f:
            f.write(text)
    
    streamer.register_callback(capture_callback)
    
    print("\nStarting output capture...")
    streamer.start_capture()
    
    # Simulate some MQTT sensor output
    print("\nMQTT Virtual Sensor Plugin Example")
    print("=" * 50)
    print("Connecting to MQTT broker at localhost:1883")
    print("Subscribing to topic: iot_logger")
    print()
    print("=" * 50)
    print("Reading sensor data (Ctrl+C to exit)...")
    print()
    
    # Simulate some sensor readings
    for i in range(3):
        print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("-" * 50)
        print(f"Temperature:    22.{i} °C")
        print(f"Humidity:       {45 + i} %")
        print(f"Pressure:       101325 Pa")
        print(f"Light Level:    {500 + i*10} lux")
        print()
        time.sleep(1)
    
    # Stop capturing
    streamer.stop_capture()
    print("\nStopped output capture")
    
    # Verify we captured output
    full_output = "".join(captured)
    
    print(f"\nCaptured {len(captured)} output chunks")
    print(f"Total captured length: {len(full_output)} characters")
    
    # Write full output to file
    with open("/tmp/terminal_full_capture.txt", "w") as f:
        f.write(full_output)
    
    print("\nCapture log saved to: /tmp/terminal_capture.log")
    print("Full capture saved to: /tmp/terminal_full_capture.txt")
    
    # Verify key content
    assert "Temperature:" in full_output, "Temperature not found in output"
    assert "Humidity:" in full_output, "Humidity not found in output"
    assert "MQTT Virtual Sensor" in full_output, "Header not found in output"
    
    print("\n✓ All assertions passed!")
    print("=" * 60)
    
    return full_output


if __name__ == "__main__":
    test_terminal_streaming()
