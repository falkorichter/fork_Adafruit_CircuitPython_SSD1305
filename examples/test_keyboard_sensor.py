#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
Test script for keyboard sensor plugin

This script helps verify that the keyboard sensor is working correctly.
It will display the last 5 characters you type on the keyboard.

Requirements:
    - evdev library: pip install evdev
    - User must be in 'input' group OR run with sudo
    
To add user to input group (then logout/login):
    sudo usermod -a -G input $USER

Usage:
    python3 examples/test_keyboard_sensor.py
    
    or with sudo if not in input group:
    sudo python3 examples/test_keyboard_sensor.py
"""

import sys
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sensor_plugins import KeyboardPlugin

def main():
    print("=" * 60)
    print("Keyboard Sensor Test")
    print("=" * 60)
    
    # Create keyboard plugin
    print("\n1. Creating keyboard plugin...")
    keyboard = KeyboardPlugin(check_interval=0.1)
    
    # Check availability
    print("2. Checking if keyboard devices are available...")
    available = keyboard.check_availability()
    
    if not available:
        print("\n❌ ERROR: Keyboard sensor is not available!")
        print("\nPossible reasons:")
        print("  - evdev library not installed: pip install evdev")
        print("  - No keyboard devices found")
        print("  - Permission denied to access /dev/input")
        print("\nTo fix permission issues:")
        print("  1. Add user to input group: sudo usermod -a -G input $USER")
        print("  2. Logout and login again")
        print("  3. OR run this script with sudo (not recommended)")
        sys.exit(1)
    
    print("✓ Keyboard sensor is available!")
    print(f"  Monitoring {len(keyboard.keyboards)} keyboard device(s)")
    
    # Display keyboard info
    for i, kbd in enumerate(keyboard.keyboards):
        print(f"  - Device {i+1}: {kbd.name} ({kbd.path})")
    
    print("\n3. Starting keyboard monitoring...")
    print("   Type some keys and watch them appear below.")
    print("   Press Ctrl+C to exit.\n")
    
    try:
        while True:
            # Read sensor data
            data = keyboard.read()
            display_text = keyboard.format_display(data)
            
            # Clear line and print current state
            print(f"\r{display_text}", end="", flush=True)
            
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n\n✓ Test completed successfully!")
        print("  The keyboard sensor is working correctly.")
        return 0

if __name__ == "__main__":
    sys.exit(main())
