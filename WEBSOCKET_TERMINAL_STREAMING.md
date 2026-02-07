# WebSocket Terminal Streaming

This feature allows you to stream terminal output from MQTT sensor examples to a web browser via WebSocket, maintaining the terminal charm with minimal effort.

## Architecture

The WebSocket terminal streaming system consists of three independent components:

1. **Terminal Streamer** (`terminal_streamer.py`) - A reusable module for capturing and broadcasting terminal output
2. **WebSocket Server** (`examples/websocket_terminal_server.py`) - Bridges the terminal streamer with WebSocket clients
3. **Web Viewer** (`examples/websocket_terminal_viewer.html`) - A simple HTML/JS client for displaying terminal output in a browser

These components are designed to be independent, so MQTT sensor scripts can work standalone or be integrated with the WebSocket streaming architecture.

## Installation

Install the required WebSocket dependency:

```bash
pip install websockets
```

Or install all optional dependencies:

```bash
pip install -r optional_requirements.txt
```

## Usage

### Basic Usage

1. **Start the WebSocket server** (this will also start the MQTT sensor script):

```bash
python examples/websocket_terminal_server.py
```

2. **Open the web viewer** in your browser:

```bash
# Open the HTML file directly in your browser
open examples/websocket_terminal_viewer.html  # macOS
xdg-open examples/websocket_terminal_viewer.html  # Linux
start examples/websocket_terminal_viewer.html  # Windows
```

Or simply drag and drop `websocket_terminal_viewer.html` into your browser.

### Advanced Usage

#### Custom WebSocket Server Configuration

You can customize the WebSocket server host and port:

```bash
python examples/websocket_terminal_server.py --host 0.0.0.0 --port 8765
```

#### Choose Different MQTT Script Variants

The server can run different MQTT example scripts:

```bash
# Basic ANSI terminal output (default)
python examples/websocket_terminal_server.py --script basic

# Rich library with enhanced formatting
python examples/websocket_terminal_server.py --script rich

# Textual TUI (may not display well in browser)
python examples/websocket_terminal_server.py --script textual
```

#### Custom MQTT Broker Configuration

Configure the MQTT broker connection:

```bash
python examples/websocket_terminal_server.py \
    --mqtt-host mqtt.example.com \
    --mqtt-port 1883 \
    --mqtt-topic sensor/data
```

#### Access from Different Host

If you're running the server on a different machine, you can specify the WebSocket URL in the browser:

```
file:///path/to/websocket_terminal_viewer.html?ws_host=192.168.1.100&ws_port=8765
```

## Architecture Details

### Terminal Streamer

The `TerminalStreamer` class provides a flexible way to capture terminal output:

- **Callback-based**: Register multiple callbacks to receive terminal output
- **Thread-safe**: Uses locks to ensure safe concurrent access
- **File-like interface**: Can replace `sys.stdout` for transparent capture
- **Non-invasive**: Original scripts continue to work normally

Example usage:

```python
from terminal_streamer import TerminalStreamer

streamer = TerminalStreamer()

# Register a callback
def my_callback(text):
    print(f"Captured: {text}")

streamer.register_callback(my_callback)

# Start capturing
streamer.start_capture()

# Now all print() calls will be captured and sent to callbacks
print("Hello, World!")

# Stop capturing
streamer.stop_capture()
```

### WebSocket Server

The `WebSocketTerminalServer` wraps the terminal streamer and broadcasts output to WebSocket clients:

- **Async I/O**: Uses `asyncio` and `websockets` for efficient handling
- **Multi-client**: Supports multiple simultaneous web viewers
- **JSON protocol**: Messages are JSON-formatted for easy parsing
- **Thread integration**: Runs sensor scripts in separate threads

### Web Viewer

The HTML viewer provides a terminal-like interface:

- **Terminal styling**: Dark theme with monospace font
- **Auto-scroll**: Automatically scrolls to show latest output
- **Connection management**: Connect/disconnect controls
- **Clear function**: Clear terminal output
- **Responsive**: Works on desktop and mobile browsers

## Testing with Static MQTT Messages

To test the WebSocket streaming without a real MQTT broker, you can use a mock MQTT broker or publish static messages. Here's an example using mosquitto:

1. **Install mosquitto** (if not already installed):

```bash
# Ubuntu/Debian
sudo apt-get install mosquitto mosquitto-clients

# macOS
brew install mosquitto
```

2. **Start mosquitto broker**:

```bash
mosquitto -v
```

3. **Publish test messages** (in another terminal):

```bash
mosquitto_pub -t iot_logger -m '{
  "BME68x": {
    "TemperatureC": 22.5,
    "Humidity": 45.0,
    "Pressure": 101325,
    "Gas Resistance": 50000
  },
  "VEML7700": {
    "Light": 500
  },
  "TMP117": {
    "TemperatureC": 22.3
  },
  "MAX17048": {
    "Voltage": 3.7,
    "StateOfCharge": 85
  },
  "WiFi": {
    "SSID": "TestNetwork",
    "RSSI": -45
  }
}'
```

4. **Start the WebSocket server**:

```bash
python examples/websocket_terminal_server.py
```

5. **View in browser**: Open `websocket_terminal_viewer.html`

## Troubleshooting

### WebSocket Connection Fails

- Check that the WebSocket server is running
- Verify the host and port match between server and viewer
- Check firewall settings if accessing from a different machine

### Terminal Output Not Appearing

- Verify the MQTT broker is running and accessible
- Check that MQTT messages are being published to the correct topic
- Ensure the sensor script is running (check server console output)

### Rich/Textual Output Not Displaying Correctly

The basic ANSI terminal output works best with WebSocket streaming. Rich and Textual libraries use advanced terminal features that may not translate well to HTML. Use `--script basic` for the best web viewing experience.

## Future Enhancements

Possible improvements to this architecture:

1. **ANSI escape code rendering**: Parse and render ANSI color codes in the web viewer
2. **Multiple script support**: Run multiple sensor scripts simultaneously
3. **Recording/playback**: Record terminal sessions and play them back
4. **Authentication**: Add authentication for WebSocket connections
5. **Better Rich/Textual support**: Enhanced rendering of Rich and Textual output in the browser

## License

SPDX-FileCopyrightText: 2026 Adafruit Industries

SPDX-License-Identifier: MIT
