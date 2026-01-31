
# SSD1305 Examples

## Examples Overview

### ssd1305_simpletest.py
Basic example demonstrating simple text and shapes on the SSD1305 display.

### ssd1305_pillow_demo.py
Demonstrates using the Python Imaging Library (PIL/Pillow) to draw on the display.

### ssd1305_stats.py
**Updated with hot-pluggable sensor support!**

Displays system statistics and sensor readings on the SSD1305 OLED. Features:
- **Hot-pluggable sensors**: Automatically detects sensors when connected
- **Graceful error handling**: Shows "n/a" when sensors are not available
- **Plugin-based architecture**: Each sensor is a modular plugin
- Displays:
  - IP address
  - Temperature (TMP117)
  - CPU load
  - Light level (VEML7700)
  - Memory usage
  - Air quality (BME680)

### ssd1305_web_simulator.py
**NEW**: Web-based simulator for testing without hardware!

A web server that simulates the SSD1305 display with mocked sensors. Perfect for:
- Testing the plugin system without physical hardware
- Demonstrating sensor integration
- Visualizing the display output in a web browser

Run with: `python examples/ssd1305_web_simulator.py` and open http://localhost:8000

## Plugin System

The new plugin system (in the `sensor_plugins` package) provides:
- **Base `SensorPlugin` class**: Abstract base for all sensor plugins
- **Automatic error handling**: Sensors gracefully fail when hardware is unavailable
- **Hot-plug support**: Periodic checking allows sensors to be connected/disconnected
- **Consistent interface**: All plugins provide data or "n/a" values

### Package Structure
The sensor plugins are organized in a modular package:
```
sensor_plugins/
├── __init__.py           # Package exports
├── base.py               # Base SensorPlugin class
├── tmp117_plugin.py      # TMP117 temperature sensor
├── veml7700_plugin.py    # VEML7700 light sensor
└── bme680_plugin.py      # BME680 environmental sensor
```

### Available Plugins
- `TMP117Plugin` - Temperature sensor
- `VEML7700Plugin` - Ambient light sensor
- `BME680Plugin` - Environmental sensor (temperature, humidity, pressure, gas, air quality)

### Usage
```python
from sensor_plugins import TMP117Plugin, VEML7700Plugin, BME680Plugin

# Initialize plugins
tmp117 = TMP117Plugin(check_interval=5.0)
veml7700 = VEML7700Plugin(check_interval=5.0)
bme680 = BME680Plugin(check_interval=5.0, burn_in_time=300)

# Read sensor data (returns "n/a" if unavailable)
temp_data = tmp117.read()
light_data = veml7700.read()
env_data = bme680.read()
```

**Note:** The old `sensor_plugin.py` module is maintained for backward compatibility but is deprecated. New code should use the `sensor_plugins` package.

## System Service Setup

`sudo nano /etc/logrotate.d/ssd1305_stats`

```
/var/log/ssd1305_stats.log {
    daily
    missingok
    rotate 7
    compress
    notifempty
    create 0640 root root
}
```


`sudo nano /etc/systemd/system/ssd1305_stats.service`

```
[Unit]
Description=SSD1305 OLED Status Display
After=multi-user.target

[Service]
Type=simple
User=root
ExecStart=/home/user/env/bin/python3 /home/user/Dokumente/git/Adafruit_CircuitPython_SSD1305/examples/ssd1305_stats.py
Restart=on-failure
StandardOutput=append:/var/log/ssd1305_stats.log
StandardError=append:/var/log/ssd1305_stats.log

[Install]
WantedBy=multi-user.target
```

Test
Reload the daemon:
`sudo systemctl daemon-reload`

Enable the service (this ensures it runs on boot):
`sudo systemctl enable ssd1305_stats.service`

Start the service now (to test it):
`sudo systemctl start ssd1305_stats.service`
