# MQTT Sensor Example Variants

This directory contains multiple implementations of the MQTT sensor monitor example, each using different terminal display methods.

## Quick Start

All examples support command-line arguments to configure the MQTT broker:

```bash
# Use default settings (localhost:1883, topic: iot_logger)
python examples/mqtt_sensor_example.py

# Specify custom broker, port, and topic
python examples/mqtt_sensor_example.py --host 192.168.1.100 --port 1883 --topic sensors/data

# See all available options
python examples/mqtt_sensor_example.py --help
```

### Option 1: Basic Version (No Dependencies)
```bash
python examples/mqtt_sensor_example.py
```

### Option 2: Rich UI Version (Recommended) ⭐
```bash
pip install rich
python examples/mqtt_sensor_example_rich.py --host your-broker-ip
```

### Option 3: Textual TUI Version
```bash
pip install textual
python examples/mqtt_sensor_example_textual.py --host your-broker-ip
```

### Install All Optional Dependencies
```bash
pip install -r optional_requirements.txt
```

### Command-Line Arguments

All MQTT examples accept the following command-line arguments:

- `--host HOST` - MQTT broker hostname or IP address (default: `localhost`)
- `--port PORT` - MQTT broker port (default: `1883`)
- `--topic TOPIC` - MQTT topic to subscribe to (default: `iot_logger`)

**Examples:**
```bash
# Connect to a specific broker
python examples/mqtt_sensor_example_rich.py --host 192.168.178.98

# Use a different port
python examples/mqtt_sensor_example.py --host broker.example.com --port 8883

# Subscribe to a different topic
python examples/mqtt_sensor_example_textual.py --topic home/sensors
```

---

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

All versions support command-line arguments for easy configuration (see Command-Line Arguments section above).

You can also configure additional parameters by modifying the script:

```python
mqtt_sensor = MQTTPlugin(
    broker_host=args.host,        # Set via --host argument
    broker_port=args.port,        # Set via --port argument
    topic=args.topic,             # Set via --topic argument
    check_interval=5.0,           # How often to check sensor availability
    burn_in_time=60,              # Air quality sensor burn-in period
)
```

**Recommended:** Use command-line arguments instead of editing the script:
```bash
python examples/mqtt_sensor_example.py --host your-broker --port 1883 --topic your-topic
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
