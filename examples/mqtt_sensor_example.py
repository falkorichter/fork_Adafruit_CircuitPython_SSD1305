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
- System information (WiFi SSID, RSSI)

The sensor is hot-pluggable - it will automatically detect when the
MQTT broker becomes available or unavailable.
"""

import sys
import time
from pathlib import Path

# Add parent directory to path to import sensor_plugins
sys.path.insert(0, str(Path(__file__).parent.parent))

from sensor_plugins import MQTTPlugin


def main():
    """Main function to demonstrate MQTT plugin"""
    print("MQTT Virtual Sensor Plugin Example")
    print("=" * 50)
    
    # Create MQTT plugin instance
    # Adjust broker_host and topic as needed
    mqtt_sensor = MQTTPlugin(
        broker_host="localhost",  # Change to your MQTT broker
        broker_port=1883,
        topic="iot_logger",  # Change to your topic
        check_interval=5.0,
        burn_in_time=60,  # Reduced from 300s for example
    )
    
    print(f"Connecting to MQTT broker at {mqtt_sensor.broker_host}:{mqtt_sensor.broker_port}")
    print(f"Subscribing to topic: {mqtt_sensor.topic}")
    print("\nExample JSON payload format:")
    print("""{
    "System Info": {"SSID": "MyWiFi", "RSSI": 198},
    "VEML7700": {"Lux": 50.688},
    "MAX17048": {"Voltage (V)": 4.21, "State Of Charge (%)": 108.89},
    "TMP117": {"Temperature (C)": 22.375},
    "BME68x": {
        "Humidity": 36.19836,
        "TemperatureC": 22.40555,
        "Pressure": 99244.27,
        "Gas Resistance": 29463.11
    }
}""")
    print("\n" + "=" * 50)
    print("Reading sensor data (Ctrl+C to exit)...")
    print()
    
    try:
        while True:
            # Read sensor data
            data = mqtt_sensor.read()
            
            # Display the data
            print(f"\nTimestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
            print("-" * 50)
            
            # BME68x environmental data
            if data.get("burn_in_remaining") is not None:
                print(f"BME68x Burn-in: {data['burn_in_remaining']}s remaining")
            else:
                print(f"Temperature:    {data['temperature']} °C")
                print(f"Humidity:       {data['humidity']} %")
                print(f"Pressure:       {data['pressure']} Pa")
                print(f"Gas Resistance: {data['gas_resistance']} Ω")
                print(f"Air Quality:    {data['air_quality']}")
            
            # Other sensors
            print(f"\nLight Level:    {data['light']} lux (VEML7700)")
            print(f"Temperature:    {data['temp_c']} °C (TMP117)")
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
