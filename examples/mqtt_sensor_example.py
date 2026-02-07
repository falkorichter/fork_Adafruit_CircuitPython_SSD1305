#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
Example demonstrating the MQTT virtual sensor plugin.

This example shows how to use the MQTTPlugin to receive sensor data
over MQTT and display it on an SSD1305 OLED display.

The MQTT plugin subscribes to a topic (default: "iot_logger") and
parses JSON sensor data including:
- BME68x environmental sensor (temperature, humidity, pressure, gas, air quality)
- VEML7700 light sensor
- TMP117 temperature sensor
- MAX17048 battery monitor
- STHS34PF80 IR presence/motion sensor
- System information (WiFi SSID, RSSI)

The sensor is hot-pluggable - it will automatically detect when the
MQTT broker becomes available or unavailable.

The terminal display clears and redraws with each update using ANSI escape
codes, providing a clean interface similar to top/htop that doesn't scroll.
"""

import argparse
import sys
import time
from pathlib import Path

# Add parent directory to path to import sensor_plugins
sys.path.insert(0, str(Path(__file__).parent.parent))

from sensor_plugins import MQTTPlugin


def main():
    """Main function to demonstrate MQTT plugin"""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="MQTT Virtual Sensor Plugin Example with ANSI terminal display"
    )
    parser.add_argument(
        "--host",
        default="localhost",
        help="MQTT broker hostname or IP address (default: localhost)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=1883,
        help="MQTT broker port (default: 1883)"
    )
    parser.add_argument(
        "--topic",
        default="iot_logger",
        help="MQTT topic to subscribe to (default: iot_logger)"
    )
    args = parser.parse_args()
    
    # Create MQTT plugin instance
    mqtt_sensor = MQTTPlugin(
        broker_host=args.host,
        broker_port=args.port,
        topic=args.topic,
        check_interval=5.0,
        burn_in_time=60,  # Reduced from 300s for example
    )
    
    # ANSI escape codes for terminal control
    CLEAR_SCREEN = "\033[2J"  # Clear entire screen
    HOME_CURSOR = "\033[H"    # Move cursor to home (top-left)
    
    def print_header():
        """Print the static header information"""
        print("MQTT Virtual Sensor Plugin Example")
        print("=" * 50)
        print(f"Connecting to MQTT broker at {mqtt_sensor.broker_host}:{mqtt_sensor.broker_port}")
        print(f"Subscribing to topic: {mqtt_sensor.topic}")
        print("\n" + "=" * 50)
        print("Reading sensor data (Ctrl+C to exit)...")
        print()
    
    # Print initial header
    print_header()
    
    try:
        first_iteration = True
        while True:
            # Read sensor data
            data = mqtt_sensor.read()
            
            # Clear screen and redraw header (skip on first iteration to avoid double print)
            if not first_iteration:
                print(CLEAR_SCREEN + HOME_CURSOR, end="", flush=True)
                print_header()
            first_iteration = False
            
            # Display the data
            print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
            print("-" * 50)
            
            # BME68x environmental data - always show raw values
            print(f"Temperature:    {data['temperature']} °C")
            print(f"Humidity:       {data['humidity']} %")
            print(f"Pressure:       {data['pressure']} Pa")
            print(f"Gas Resistance: {data['gas_resistance']} Ω")
            
            # Show air quality or burn-in status
            if data.get("burn_in_remaining") is not None:
                print(f"Air Quality:    Burn-in ({data['burn_in_remaining']}s remaining)")
            else:
                print(f"Air Quality:    {data['air_quality']}")
            
            # Other sensors
            print(f"\nLight Level:    {data['light']} lux (VEML7700)")
            print(f"Temperature:    {data['temp_c']} °C (TMP117)")
            
            # STHS34PF80 presence/motion sensor
            print(f"\nPresence:       {data['presence_value']} cm^-1 (STHS34PF80)")
            print(f"Motion:         {data['motion_value']} LSB (STHS34PF80)")
            print(f"Obj Temp:       {data['sths34_temperature']} °C (STHS34PF80)")
            
            # Display person detection status (condensed value)
            person_status = data.get('person_detected', 'n/a')
            if person_status == "n/a":
                print(f"Person Status:  UNKNOWN - No STHS34PF80 data available")
            elif person_status:
                print(f"Person Status:  *** PERSON DETECTED *** (Presence >= 1000 OR Motion > 0)")
            else:
                print(f"Person Status:  No person detected (Presence < 1000 AND Motion = 0)")
            
            print(f"\nBattery Voltage: {data['voltage']} V")
            print(f"Battery SOC:     {data['soc']} %")
            print(f"\nWiFi SSID:      {data['ssid']}")
            print(f"WiFi RSSI:      {data['rssi']}")
            
            # Display formatted output
            display_text = mqtt_sensor.format_display(data)
            print(f"\nDisplay Text:   {display_text}")
            
            # Check availability status
            if mqtt_sensor.available:
                print("\nStatus: Connected ✓")
            else:
                print("\nStatus: Disconnected (waiting for MQTT broker...)")
            
            # Wait before next read
            time.sleep(2)
            
    except KeyboardInterrupt:
        print("\n\nStopping...")
        print("Goodbye!")


if __name__ == "__main__":
    main()
