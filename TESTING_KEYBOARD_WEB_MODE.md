# Testing Keyboard Functionality in Web Mode

This document explains how to test the keyboard functionality in web mode with WebSocket support.

## Prerequisites

1. Install required dependencies:
```bash
pip install websockets pillow
```

## Running the Web Simulator with Keyboard Support

1. Start the web simulator with mocked sensors and WebSocket enabled:
```bash
python3 examples/ssd1305_web_simulator.py --use-mocks --enable-websocket
```

This will start:
- HTTP server on http://localhost:8000
- WebSocket server on ws://localhost:8001

2. Open your web browser and navigate to:
```
http://localhost:8000
```

## Testing Keyboard Input

### Via Web Browser

1. Once the page loads, verify that:
   - The connection mode shows "WebSocket Push" (instead of "Polling")
   - You see a message "Keyboard enabled: Type any key to see it on the display"

2. Click anywhere on the page to focus it, then type some keys (a-z, 0-9, space)

3. Observe the display:
   - The "Keys:" line at the bottom of the display should update to show the last 5 characters you typed
   - Updates should appear immediately after each keystroke
   - The browser console should show WebSocket messages being sent

### Via Python Script

You can also test keyboard input programmatically:

```python
import asyncio
import json
import websockets

async def test_keyboard():
    uri = "ws://localhost:8001"
    async with websockets.connect(uri) as ws:
        # Receive initial image
        msg = await ws.recv()
        data = json.loads(msg)
        print(f"Connected: {data['type']}")
        
        # Send keyboard inputs
        for key in ['h', 'e', 'l', 'l', 'o']:
            await ws.send(json.dumps({"type": "keypress", "key": key}))
            print(f"Sent: {key}")
            await asyncio.sleep(0.2)
        
        # Wait for updates
        for i in range(3):
            msg = await asyncio.wait_for(ws.recv(), timeout=2.0)
            print(f"Received update {i+1}")

asyncio.run(test_keyboard())
```

## Expected Behavior

1. **WebSocket Connection**: The page should connect to the WebSocket server and display "WebSocket Push" mode
2. **Keyboard Capture**: When you type keys, they should be sent to the server via WebSocket
3. **Immediate Updates**: The display should update immediately (within 500ms) to show the new key buffer
4. **Last 5 Keys**: The display shows the last 5 alphanumeric characters or spaces you typed

## Troubleshooting

### WebSocket connection fails
- Ensure the server was started with `--enable-websocket` flag
- Check that port 8001 is not blocked by a firewall
- Verify websockets module is installed: `pip install websockets`

### Keyboard input not working
- Verify you're using `--use-mocks` flag (keyboard input via browser only works with mocked sensors)
- Check the browser console for errors
- Ensure the page is focused (click on it) before typing

### Display not updating
- Check server console for any errors
- Verify the WebSocket connection is established (should show "WebSocket client connected" in server output)
- Try refreshing the browser page

## Implementation Details

The keyboard functionality works as follows:

1. **Client Side** (web_simulator_template.html):
   - Captures `keydown` events when WebSocket is connected and mocks are enabled
   - Filters to only alphanumeric and space characters
   - Sends keypress messages to server: `{"type": "keypress", "key": "<char>"}`

2. **Server Side** (ssd1305_web_simulator.py):
   - WebSocket handler receives keypress messages
   - Maps characters to evdev key codes using `CHAR_TO_KEYCODE` dictionary
   - Simulates key press events using `MockEvdevDevice.simulate_keypress()`
   - Invalidates sensor cache to force immediate display update
   - Sends updated display image to all connected WebSocket clients

3. **Keyboard Plugin** (sensor_plugins/keyboard_plugin.py):
   - Maintains a buffer of last 5 characters
   - In mock mode, reads from `MockEvdevDevice` event queue
   - Formats display as "Keys: xxxxx" with right-aligned padding
