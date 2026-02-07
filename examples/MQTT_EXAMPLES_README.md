# MQTT Sensor Example Variants

This directory contains multiple implementations of the MQTT sensor monitor example, each using different terminal display methods.

## Available Versions

### 1. `mqtt_sensor_example.py` (Basic ANSI)
**Dependencies**: None (uses standard ANSI escape codes)

The original implementation using ANSI escape codes to clear the screen and redraw content.

**Pros**:
- No external dependencies
- Simple implementation
- Works on most terminals

**Cons**:
- Clears entire screen on each update
- Pollutes terminal history with cleared screens
- Not ideal for reviewing terminal output after execution

**Usage**:
```bash
python examples/mqtt_sensor_example.py
```

### 2. `mqtt_sensor_example_rich.py` (Rich Library) ⭐ **Recommended**
**Dependencies**: `pip install rich`

Uses the [Rich library](https://rich.readthedocs.io/) for beautiful, clean terminal updates.

**Pros**:
- ✨ Beautiful formatting with colors and styles
- Clean in-place updates (only redraws changed content)
- Doesn't pollute terminal history
- Tables, panels, and structured layout
- Lightweight and easy to use
- Excellent performance

**Cons**:
- Requires external dependency (~500KB installed)

**Usage**:
```bash
pip install rich
python examples/mqtt_sensor_example_rich.py
```

**Preview**: Displays sensor data in a structured table with color-coded air quality, status panels, and clean formatting.

### 3. `mqtt_sensor_example_textual.py` (Textual Framework)
**Dependencies**: `pip install textual`

Uses the [Textual framework](https://textual.textualize.io/) for a full TUI (Text User Interface) experience.

**Pros**:
- 🎨 Most sophisticated and polished UI
- Uses alternate screen buffer (doesn't affect terminal history at all)
- Reactive updates (only redraws changed widgets)
- CSS-like styling
- Keyboard shortcuts (press 'q' to quit)
- Best for long-running monitoring

**Cons**:
- Heavier dependency (~2MB installed)
- More complex implementation
- Slightly more resource intensive

**Usage**:
```bash
pip install textual
python examples/mqtt_sensor_example_textual.py
```

**Preview**: Full-screen app with header, footer, and organized sections. Press 'q' to quit.

## Which Should I Use?

| Use Case | Recommended Version |
|----------|---------------------|
| Quick demo, no dependencies | `mqtt_sensor_example.py` |
| Best overall experience | `mqtt_sensor_example_rich.py` ⭐ |
| Professional monitoring app | `mqtt_sensor_example_textual.py` |
| Embedded/resource-constrained | `mqtt_sensor_example.py` |
| Clean terminal history required | `mqtt_sensor_example_rich.py` or `mqtt_sensor_example_textual.py` |

## Testing Terminal Compatibility

Use `test_terminal_update.py` to test different ANSI escape code methods on your terminal:

```bash
python examples/test_terminal_update.py
```

This script tests three methods:
1. Save/Restore Cursor (not widely supported)
2. Cursor Positioning (moderate support)
3. Clear Screen (universal support but with history pollution)

## Configuration

All versions use the same MQTT configuration. Edit the following in the script:

```python
mqtt_sensor = MQTTPlugin(
    broker_host="localhost",  # Change to your MQTT broker IP/hostname
    broker_port=1883,         # MQTT broker port
    topic="iot_logger",       # Topic to subscribe to
    check_interval=5.0,       # How often to check sensor availability
    burn_in_time=60,          # Air quality sensor burn-in period
)
```

## Example MQTT Payload

All versions expect JSON payloads in this format:

```json
{
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
}
```

## Installation

To install all optional dependencies including Rich and Textual:

```bash
pip install -r optional_requirements.txt
```

Or install individually:

```bash
# For basic MQTT support
pip install paho-mqtt

# For Rich UI version (recommended)
pip install rich

# For Textual UI version
pip install textual
```
