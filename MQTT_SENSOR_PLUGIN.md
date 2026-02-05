# MQTT Virtual Sensor Plugin

The MQTT Virtual Sensor Plugin allows you to receive sensor data from IoT devices over MQTT and display it on your SSD1305 OLED display.

## Features

- **Hot-pluggable**: Automatically detects when MQTT broker becomes available or unavailable
- **Multi-sensor support**: Parses data from multiple sensors in a single JSON payload
- **Air quality calculation**: Implements BME68x burn-in period and air quality scoring (compatible with BME680 logic)
- **Background updates**: Continuously receives MQTT messages even when display is off

## Supported Sensors

The plugin can extract data from the following sensors in the MQTT payload:

- **BME68x**: Environmental sensor (temperature, humidity, pressure, gas resistance, air quality)
- **VEML7700**: Light sensor (lux)
- **TMP117**: Temperature sensor
- **MAX17048**: Battery monitor (voltage, state of charge)
- **System Info**: WiFi information (SSID, RSSI)

## Installation

1. Install the paho-mqtt library:
```bash
pip install paho-mqtt
```

Or install all optional dependencies:
```bash
pip install -r optional_requirements.txt
```

## Usage

### Basic Example

```python
from sensor_plugins import MQTTPlugin

# Create MQTT sensor plugin
mqtt_sensor = MQTTPlugin(
    broker_host="localhost",  # Your MQTT broker
    broker_port=1883,         # Default MQTT port
    topic="iot_logger",       # Topic to subscribe to
    check_interval=5.0,       # Check availability every 5 seconds
    burn_in_time=300,         # BME68x burn-in period (5 minutes)
)

# Read sensor data
data = mqtt_sensor.read()

print(f"Temperature: {data['temperature']} °C")
print(f"Humidity: {data['humidity']} %")
print(f"Air Quality: {data['air_quality']}")
print(f"Light: {data['light']} lux")
```

### Expected MQTT Payload Format

The plugin expects JSON payloads in this format:

```json
{
  "System Info": {
    "SSID": "MyWiFi",
    "RSSI": -45,
    "Uptime": 158665,
    "Heap": 34484,
    "SD Free": 3220832256
  },
  "VEML7700": {
    "Ambient Light Level": 880,
    "White Level": 1508,
    "Lux": 50.688
  },
  "MAX17048": {
    "Voltage (V)": 4.21,
    "State Of Charge (%)": 85.5,
    "Change Rate (%/hr)": -14.768
  },
  "TMP117": {
    "Temperature (C)": 22.375
  },
  "BME68x": {
    "Humidity": 36.19836,
    "TemperatureC": 22.40555,
    "Pressure": 99244.27,
    "Gas Resistance": 29463.11,
    "Sensor Status": 176
  }
}
```

### Using with SSD1305 Stats Display

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sensor_plugins import MQTTPlugin

# Initialize MQTT sensor
mqtt_sensor = MQTTPlugin(
    broker_host="192.168.1.100",
    topic="iot_logger"
)

# Use in your display loop
while True:
    data = mqtt_sensor.read()
    
    # Check if sensor is available
    if mqtt_sensor.available:
        # Display the data
        display_text = mqtt_sensor.format_display(data)
        print(display_text)
    else:
        print("MQTT: Waiting for broker...")
    
    time.sleep(2)
```

## Configuration

### Constructor Parameters

- `broker_host` (str): MQTT broker hostname or IP address (default: "localhost")
- `broker_port` (int): MQTT broker port (default: 1883)
- `topic` (str): MQTT topic to subscribe to (default: "iot_logger")
- `check_interval` (float): Seconds between availability checks (default: 5.0)
- `burn_in_time` (float): BME68x burn-in period in seconds (default: 300)

### Return Data

The `read()` method returns a dictionary with the following keys:

- `temperature`: BME68x temperature (°C) or "n/a"
- `humidity`: BME68x humidity (%) or "n/a"
- `pressure`: BME68x pressure (Pa) or "n/a"
- `gas_resistance`: BME68x gas resistance (Ω) or "n/a"
- `air_quality`: BME68x air quality score (0-100) or "n/a"
- `burn_in_remaining`: Seconds remaining in burn-in period (only during burn-in)
- `light`: VEML7700 light level (lux) or "n/a"
- `temp_c`: TMP117 temperature (°C) or "n/a"
- `voltage`: MAX17048 battery voltage (V) or "n/a"
- `soc`: MAX17048 state of charge (%) or "n/a"
- `ssid`: WiFi SSID or "n/a"
- `rssi`: WiFi RSSI (signal strength) or "n/a"

## BME68x Air Quality Calculation

The plugin implements the same air quality calculation as the BME680Plugin:

1. **Burn-in Period**: Collects gas resistance readings for `burn_in_time` seconds
2. **Baseline Calculation**: Averages the last 50 readings to establish a baseline
3. **Air Quality Score**: Combines gas resistance and humidity to calculate a score (0-100)
   - Higher scores indicate better air quality
   - Uses humidity baseline of 40% and weighting of 25%

## Testing

Run the MQTT plugin tests:

```bash
python -m unittest tests.test_sensor_plugin.TestMQTTPlugin -v
```

## Example

See `examples/mqtt_sensor_example.py` for a complete working example.

## Troubleshooting

### Plugin shows "n/a" for all values

- Check that MQTT broker is running and accessible
- Verify the broker_host and broker_port are correct
- Check that messages are being published to the topic
- Verify the JSON payload format matches expected structure

### Air quality always shows "n/a"

- Wait for the burn-in period to complete (default: 5 minutes)
- Check that BME68x data is present in the MQTT payload
- Verify gas resistance and humidity values are being received

### Connection fails immediately

- Check network connectivity to MQTT broker
- Verify firewall allows connection on MQTT port (default: 1883)
- Try using `mosquitto_sub` to test MQTT connectivity:
  ```bash
  mosquitto_sub -h localhost -t iot_logger -v
  ```
