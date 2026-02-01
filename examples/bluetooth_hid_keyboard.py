#!/usr/bin/env python3
"""
Example: Bluetooth HID Keyboard Bridge

This example demonstrates how to use the Raspberry Pi 500+ as a Bluetooth
keyboard for another computer. It bridges the Pi's built-in keyboard to
Bluetooth HID, allowing you to type on the Pi and have the input appear
on a connected Bluetooth host.

Prerequisites:
    1. Raspberry Pi 500+ with Bluetooth enabled
    2. Install dependencies:
       pip install dbus-python PyGObject evdev

    3. Run with root privileges (required for Bluetooth and evdev):
       sudo python3 examples/bluetooth_hid_keyboard.py

    4. On the target computer, scan for Bluetooth devices and pair with
       "Pi500 Keyboard"

Usage:
    sudo python3 examples/bluetooth_hid_keyboard.py [--name NAME]

Options:
    --name NAME    Custom Bluetooth device name (default: "Pi500 Keyboard")

To stop:
    Press Ctrl+C
"""

import argparse
import logging
import signal
import sys
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Turn Pi 500+ into a Bluetooth keyboard",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--name",
        default="Pi500 Keyboard",
        help="Bluetooth device name (default: Pi500 Keyboard)",
    )
    args = parser.parse_args()

    # Import after argument parsing to show help even without dependencies
    try:
        from sensor_plugins import KeyboardPlugin  # noqa: PLC0415
        from sensor_plugins.bluetooth_hid_service import (  # noqa: PLC0415
            BluetoothHIDService,
            BluetoothKeyboardBridge,
        )
    except ImportError as e:
        logger.error(
            "Missing dependencies. Install with:\n"
            "  pip install dbus-python PyGObject evdev"
        )
        logger.error("Import error: %s", e)
        sys.exit(1)

    # Create components
    logger.info("Initializing keyboard plugin...")
    try:
        keyboard = KeyboardPlugin()
        keyboard.check_availability()
        if not keyboard.available:
            logger.error(
                "No keyboard devices found. Make sure you have evdev access.\n"
                "Try running with: sudo python3 %s",
                sys.argv[0],
            )
            sys.exit(1)
    except Exception as e:
        logger.error("Failed to initialize keyboard: %s", e)
        sys.exit(1)

    logger.info("Creating Bluetooth HID service...")
    bt_service = BluetoothHIDService(device_name=args.name)

    # Set up connection callbacks
    def on_connect():
        logger.info("=" * 50)
        logger.info("Bluetooth host connected!")
        logger.info("Start typing on the Pi keyboard...")
        logger.info("=" * 50)

    def on_disconnect():
        logger.info("Bluetooth host disconnected")

    bt_service.on_connect(on_connect)
    bt_service.on_disconnect(on_disconnect)

    # Create and start the bridge
    logger.info("Starting Bluetooth keyboard bridge...")
    bridge = BluetoothKeyboardBridge(keyboard, bt_service)

    # Handle graceful shutdown
    running = True

    def signal_handler(signum, frame):
        nonlocal running
        logger.info("\nShutting down...")
        running = False

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        bridge.start()
        logger.info("=" * 50)
        logger.info("Bluetooth HID Keyboard Ready!")
        logger.info("Device name: %s", args.name)
        logger.info("")
        logger.info("On your target computer:")
        logger.info("  1. Open Bluetooth settings")
        logger.info("  2. Scan for devices")
        logger.info("  3. Pair with '%s'", args.name)
        logger.info("")
        logger.info("Press Ctrl+C to stop")
        logger.info("=" * 50)

        # Keep running until interrupted
        while running:
            # Periodically log status
            if bt_service.connected:
                data = keyboard.read()
                keys = data.get("last_keys", "")
                if keys:
                    logger.debug("Recent keys: %s", keys)
            time.sleep(1)

    except Exception as e:
        logger.error("Error: %s", e)
        raise
    finally:
        logger.info("Stopping bridge...")
        bridge.stop()
        logger.info("Goodbye!")


if __name__ == "__main__":
    main()
