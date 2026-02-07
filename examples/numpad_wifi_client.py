#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
USB Numpad to WiFi Bridge Client

This script runs on a Raspberry Pi Zero W (or similar) connected to a USB numpad.
It reads keyboard events using evdev and sends them over WebSocket to the main
server running ssd1305_web_simulator.py.

This enables remote numpad input to be displayed on an SSD1305 OLED display
connected to a different device on the same network.

Requirements:
    pip install evdev websockets

Hardware Setup:
    - Raspberry Pi Zero W with USB OTG adapter
    - USB numpad connected to the Pi Zero W
    - WiFi network connectivity

Usage:
    python3 numpad_wifi_client.py --server ws://192.168.1.100:8001

    Options:
        --server URL    WebSocket server URL (default: ws://localhost:8001)
        --debug         Enable debug logging
        --list-devices  List available input devices and exit

Server Setup:
    On the main server (with SSD1305 display), run:
    python3 examples/ssd1305_web_simulator.py --enable-websocket

Permissions:
    User must be in 'input' group to read evdev devices:
    sudo usermod -a -G input $USER
    (logout and login for changes to take effect)

See USB_NUMPAD_WIFI_INTEGRATION.md for full documentation.
"""

import argparse
import asyncio
import json
import logging
import select
import sys
from typing import Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Check for required dependencies
try:
    import evdev
except ImportError:
    print("Error: evdev not installed. Run: pip install evdev")
    sys.exit(1)

try:
    import websockets
except ImportError:
    print("Error: websockets not installed. Run: pip install websockets")
    sys.exit(1)


# Numpad key mapping (evdev key codes to characters)
# Supports both numpad-specific keys and regular number keys
NUMPAD_KEY_MAP = {
    # Numpad keys (when NumLock is on)
    evdev.ecodes.KEY_KP0: "0",
    evdev.ecodes.KEY_KP1: "1",
    evdev.ecodes.KEY_KP2: "2",
    evdev.ecodes.KEY_KP3: "3",
    evdev.ecodes.KEY_KP4: "4",
    evdev.ecodes.KEY_KP5: "5",
    evdev.ecodes.KEY_KP6: "6",
    evdev.ecodes.KEY_KP7: "7",
    evdev.ecodes.KEY_KP8: "8",
    evdev.ecodes.KEY_KP9: "9",
    evdev.ecodes.KEY_KPENTER: "\n",
    evdev.ecodes.KEY_KPPLUS: "+",
    evdev.ecodes.KEY_KPMINUS: "-",
    evdev.ecodes.KEY_KPASTERISK: "*",
    evdev.ecodes.KEY_KPSLASH: "/",
    evdev.ecodes.KEY_KPDOT: ".",
    # Regular number keys (fallback)
    evdev.ecodes.KEY_0: "0",
    evdev.ecodes.KEY_1: "1",
    evdev.ecodes.KEY_2: "2",
    evdev.ecodes.KEY_3: "3",
    evdev.ecodes.KEY_4: "4",
    evdev.ecodes.KEY_5: "5",
    evdev.ecodes.KEY_6: "6",
    evdev.ecodes.KEY_7: "7",
    evdev.ecodes.KEY_8: "8",
    evdev.ecodes.KEY_9: "9",
    evdev.ecodes.KEY_ENTER: "\n",
}


def list_input_devices():
    """List all available input devices"""
    print("\nAvailable input devices:")
    print("-" * 60)

    for path in evdev.list_devices():
        try:
            device = evdev.InputDevice(path)
            caps = device.capabilities(verbose=False)

            # Check for keyboard/numpad capability
            has_keys = 1 in caps
            if has_keys:
                keys = caps[1]
                numpad_check_keys = {
                    evdev.ecodes.KEY_KP0,
                    evdev.ecodes.KEY_KP1,
                    evdev.ecodes.KEY_KP5,
                    evdev.ecodes.KEY_KPENTER,
                }
                has_numpad = any(k in numpad_check_keys for k in keys)
                has_regular_keys = any(k in range(1, 128) for k in keys)

                device_type = []
                if has_numpad:
                    device_type.append("NUMPAD")
                if has_regular_keys:
                    device_type.append("KEYBOARD")

                type_str = "/".join(device_type) if device_type else "OTHER"
                print(f"  {path}: {device.name}")
                print(f"    Type: {type_str}")
            else:
                print(f"  {path}: {device.name}")
                print("    Type: NON-KEYBOARD")
        except (PermissionError, OSError) as e:
            print(f"  {path}: (access denied: {e})")

    print("-" * 60)


def find_numpad_device() -> Optional[evdev.InputDevice]:
    """Find USB numpad device among available input devices"""
    devices = [evdev.InputDevice(path) for path in evdev.list_devices()]

    for device in devices:
        caps = device.capabilities(verbose=False)
        if 1 not in caps:  # No EV_KEY capability
            continue

        keys = caps[1]
        # Check if device has numpad keys
        numpad_keys = [
            evdev.ecodes.KEY_KP0,
            evdev.ecodes.KEY_KP1,
            evdev.ecodes.KEY_KP2,
            evdev.ecodes.KEY_KP3,
            evdev.ecodes.KEY_KP4,
            evdev.ecodes.KEY_KP5,
            evdev.ecodes.KEY_KP6,
            evdev.ecodes.KEY_KP7,
            evdev.ecodes.KEY_KP8,
            evdev.ecodes.KEY_KP9,
            evdev.ecodes.KEY_KPENTER,
        ]

        if any(k in keys for k in numpad_keys):
            logger.info(f"Found numpad: {device.name} at {device.path}")
            return device

    return None


async def send_keypress(ws, key: str):
    """Send keypress message over WebSocket"""
    # Escape special characters for JSON
    if key == "\n":
        key_str = "\\n"
    else:
        key_str = key

    message = json.dumps({"type": "keypress", "key": key_str})
    await ws.send(message)
    logger.debug(f"Sent: {repr(key)}")


async def process_device_events(device, ws) -> bool:
    """Process events from the input device.
    
    Returns False if the device read failed, True otherwise.
    """
    try:
        for event in device.read():
            # Only process key press events (not release)
            if event.type != evdev.ecodes.EV_KEY or event.value != 1:
                continue

            char = NUMPAD_KEY_MAP.get(event.code)
            if char:
                await send_keypress(ws, char)
    except OSError as e:
        logger.error(f"Device read error: {e}")
        return False
    return True


async def websocket_client(server_url: str, device: evdev.InputDevice):
    """Main WebSocket client loop with automatic reconnection"""
    reconnect_delay = 1
    max_reconnect_delay = 30

    while True:  # noqa: PLR1702 - Reconnection loop requires nesting
        try:
            logger.info(f"Connecting to {server_url}...")
            async with websockets.connect(server_url) as ws:
                logger.info("Connected to server")
                reconnect_delay = 1  # Reset delay on successful connection

                # Main event loop
                while True:
                    # Use select for non-blocking read with timeout
                    r, w, x = select.select([device], [], [], 0.1)

                    if device in r:
                        if not await process_device_events(device, ws):
                            break

                    # Small delay to prevent busy loop
                    await asyncio.sleep(0.01)

        except websockets.exceptions.ConnectionClosed:
            logger.warning("Connection closed by server")
        except ConnectionRefusedError:
            logger.warning(f"Connection refused, retrying in {reconnect_delay}s...")
        except OSError as e:
            logger.error(f"Network error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")

        # Exponential backoff for reconnection
        logger.info(f"Reconnecting in {reconnect_delay} seconds...")
        await asyncio.sleep(reconnect_delay)
        reconnect_delay = min(reconnect_delay * 2, max_reconnect_delay)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="USB Numpad to WiFi Bridge Client",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Connect to local server
    python3 numpad_wifi_client.py

    # Connect to remote server
    python3 numpad_wifi_client.py --server ws://192.168.1.100:8001

    # List available input devices
    python3 numpad_wifi_client.py --list-devices

    # Enable debug output
    python3 numpad_wifi_client.py --debug
        """,
    )
    parser.add_argument(
        "--server",
        type=str,
        default="ws://localhost:8001",
        help="WebSocket server URL (default: ws://localhost:8001)",
    )
    parser.add_argument(
        "--debug", action="store_true", help="Enable debug logging"
    )
    parser.add_argument(
        "--list-devices",
        action="store_true",
        help="List available input devices and exit",
    )
    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    # List devices mode
    if args.list_devices:
        list_input_devices()
        return 0

    print("=" * 60)
    print("USB Numpad to WiFi Bridge")
    print("=" * 60)

    # Find numpad device
    device = find_numpad_device()
    if not device:
        logger.error("No numpad device found!")
        print("\nTroubleshooting:")
        print("  1. Ensure USB numpad is connected")
        print("  2. Check user is in 'input' group: groups $USER")
        print("  3. Add to input group: sudo usermod -a -G input $USER")
        print("  4. List devices: python3 numpad_wifi_client.py --list-devices")
        list_input_devices()
        return 1

    print(f"\nUsing device: {device.name}")
    print(f"Device path:  {device.path}")
    print(f"Server:       {args.server}")
    print("\nPress numpad keys to send to server.")
    print("Press Ctrl+C to exit.\n")

    # Run async event loop
    try:
        asyncio.run(websocket_client(args.server, device))
    except KeyboardInterrupt:
        logger.info("Shutting down...")

    return 0


if __name__ == "__main__":
    sys.exit(main())
