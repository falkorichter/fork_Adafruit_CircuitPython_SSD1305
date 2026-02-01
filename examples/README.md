
# SSD1305 Examples

## Installation

To run the examples, install the required dependencies:

```bash
pip install -r examples/requirements.txt
```

This will install all necessary packages including:
- Core library dependencies (Adafruit Blinka, etc.)
- PIL/Pillow for image operations
- Sensor libraries (TMP117, VEML7700, BME680)
- pynput for keyboard monitoring (burn-in prevention)

Alternatively, you can install dependencies individually as needed for specific examples.

## Examples Overview

### ssd1305_simpletest.py
Basic example demonstrating simple text and shapes on the SSD1305 display.

### ssd1305_pillow_demo.py
Demonstrates using the Python Imaging Library (PIL/Pillow) to draw on the display.

### ssd1305_stats.py
**Updated with hot-pluggable sensor support and OLED burn-in prevention!**

Displays system statistics and sensor readings on the SSD1305 OLED. Features:
- **Hot-pluggable sensors**: Automatically detects sensors when connected
- **Graceful error handling**: Shows "n/a" when sensors are not available
- **Plugin-based architecture**: Each sensor is a modular plugin
- **OLED burn-in prevention**: Automatically blanks display after keyboard inactivity
- Displays:
  - IP address
  - Temperature (TMP117)
  - CPU load
  - Light level (VEML7700)
  - Memory usage
  - Air quality (BME680)

#### OLED Burn-in Prevention

The stats display now supports automatic display blanking to prevent OLED burn-in.

**Usage:**

Default behavior (10-second timeout with auto-detect input method):
```bash
python examples/ssd1305_stats.py
```

Custom timeout (e.g., 30 seconds):
```bash
python examples/ssd1305_stats.py --blank-timeout 30
```

Disable blanking:
```bash
python examples/ssd1305_stats.py --no-blank
# OR
python examples/ssd1305_stats.py --blank-timeout 0
```

Select specific input detection method:
```bash
# Use evdev for Linux systems (recommended for headless systems)
python examples/ssd1305_stats.py --input-method evdev

# Use file timestamp monitoring (universal fallback)
python examples/ssd1305_stats.py --input-method file

# Use pynput (requires X11/display server)
python examples/ssd1305_stats.py --input-method pynput

# Use stdin (only works when running in terminal)
python examples/ssd1305_stats.py --input-method stdin
```

Enable debug logging to see keystroke detection:
```bash
python examples/ssd1305_stats.py --debug
```

**Input Detection Methods:**

The display supports four different keyboard input detection methods:

1. **pynput** (Option A): Cross-platform keyboard monitoring using the pynput library
   - Works on systems with X11/display server
   - Requires: `pip install pynput`
   - Best for desktop environments

2. **evdev** (Option B): Linux-specific, reads from `/dev/input/event*`
   - Works on Linux systems without X11
   - Requires: `pip install evdev`
   - May need permission to access `/dev/input` (add user to `input` group)
   - Best for headless Raspberry Pi setups

3. **file** (Option C): File timestamp monitoring of `/dev/input` devices
   - Universal fallback that works on most Linux systems
   - No additional dependencies required
   - Monitors file access times to detect input activity
   - Best for systems where evdev doesn't work

4. **stdin** (Option D): Terminal input monitoring
   - Only works when running interactively in a terminal
   - No additional dependencies required
   - Fallback for testing purposes

**Auto-detect mode** (default): Tries all methods in order until one works:
`pynput` → `evdev` → `file` → `stdin`

**How It Works:**

- The display monitors keyboard activity in the background using one of the detection methods above
- After the specified timeout period with no keyboard input, the display is blanked
- Any keyboard press immediately restores the display
- This helps prevent OLED burn-in from static content
- Works in SSH sessions, systemd services, and other headless environments
- Use `--debug` flag to see which keys are being detected for troubleshooting

**Reusable Module:**

The burn-in prevention functionality has been extracted into a reusable `display_timeout` module that can be used in other projects:

```python
from display_timeout import DisplayTimeoutManager, keyboard_listener
import threading

# Create timeout manager
timeout_manager = DisplayTimeoutManager(timeout_seconds=10.0, enabled=True)

# Start keyboard monitoring in background thread
keyboard_thread = threading.Thread(
    target=keyboard_listener, 
    args=(timeout_manager, "auto"),  # method: auto, pynput, evdev, file, or stdin
    daemon=True
)
keyboard_thread.start()

# In your main loop
if timeout_manager.should_display_be_active():
    # Update display
    pass
else:
    # Blank display
    pass
```

See `display_timeout.py` in the repository root for full documentation.

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
  - **Burn-in Caching**: The BME680 sensor requires a burn-in period (default 300 seconds) to establish a baseline for air quality measurements. To avoid this delay on subsequent runs, burn-in data is automatically cached in `examples/bme680_burn_in_cache.json` and reused if less than 1 hour old.

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

**BME680 Burn-in Cache:**
- The BME680 plugin automatically saves burn-in calibration data after the initial burn-in period
- Cached data is stored in `examples/bme680_burn_in_cache.json`
- Cache is valid for 1 hour, after which a new burn-in is performed
- **Master/Read-only mode**: The OLED process (`ssd1305_stats.py`) is the master and writes to the cache. The web simulator (`ssd1305_web_simulator.py`) uses `read_only_cache=True` to only read from the cache, preventing file conflicts.
- Memory usage is limited by keeping only the last 50 burn-in samples in memory
- To disable caching or use a custom cache location, pass `cache_file` parameter to `BME680Plugin()`
- To use read-only mode (for secondary processes), pass `read_only_cache=True` to `BME680Plugin()`

**Note:** The old `sensor_plugin.py` module is maintained for backward compatibility but is deprecated. New code should use the `sensor_plugins` package.

## System Service Setup

When running as a systemd service, you can configure the burn-in prevention timeout and input method:

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
# Default (10-second timeout with auto-detect):
ExecStart=/home/user/env/bin/python3 /home/user/Dokumente/git/Adafruit_CircuitPython_SSD1305/examples/ssd1305_stats.py
# Custom timeout (30 seconds) with evdev method (recommended for headless):
# ExecStart=/home/user/env/bin/python3 /home/user/Dokumente/git/Adafruit_CircuitPython_SSD1305/examples/ssd1305_stats.py --blank-timeout 30 --input-method evdev
# With debug logging to troubleshoot input detection:
# ExecStart=/home/user/env/bin/python3 /home/user/Dokumente/git/Adafruit_CircuitPython_SSD1305/examples/ssd1305_stats.py --debug --input-method evdev
# Disable burn-in prevention:
# ExecStart=/home/user/env/bin/python3 /home/user/Dokumente/git/Adafruit_CircuitPython_SSD1305/examples/ssd1305_stats.py --no-blank
Restart=on-failure
StandardOutput=append:/var/log/ssd1305_stats.log
StandardError=append:/var/log/ssd1305_stats.log

[Install]
WantedBy=multi-user.target
```

**Input Method for Systemd Services:**

For headless systems running as systemd services, the recommended input method is `evdev`:
```bash
# Install evdev
/home/user/env/bin/pip install evdev

# Add user to input group (required for evdev to access /dev/input)
sudo usermod -a -G input root

# Or use file timestamp method (no dependencies, no special permissions needed)
# Just add --input-method file to the ExecStart line
```

**Note:** If using `pynput`, install it in the Python environment:
```bash
/home/user/env/bin/pip install pynput
```

However, `pynput` requires X11/display server and won't work in headless environments.

**Testing the Service:**

Reload the daemon:
`sudo systemctl daemon-reload`

Enable the service (this ensures it runs on boot):
`sudo systemctl enable ssd1305_stats.service`

Start the service now (to test it):
`sudo systemctl start ssd1305_stats.service`

Check logs to see which input method is being used:
`tail -f /var/log/ssd1305_stats.log`
