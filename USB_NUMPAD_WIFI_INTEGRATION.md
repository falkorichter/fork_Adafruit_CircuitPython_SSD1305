# USB Numpad WiFi Integration Guide

This document provides architecture options for integrating a USB numpad over WiFi into your software stack, compatible with the SSD1305 display simulator and keyboard plugin.

## Table of Contents

1. [Overview](#overview)
2. [Architecture Options](#architecture-options)
3. [Hardware Options](#hardware-options)
4. [Architecture Diagrams](#architecture-diagrams)
5. [Implementation Examples](#implementation-examples)
6. [Comparison Matrix](#comparison-matrix)

---

## Overview

### Problem Statement

You have a permanently installed USB numpad that needs to be integrated over WiFi for a stable connection. The goal is to read numpad entries remotely and display them on an SSD1305 OLED display.

### Requirements

- USB numpad input capture
- WiFi connectivity for data transmission
- Stable, low-latency communication
- Integration with existing keyboard plugin infrastructure

---

## Architecture Options

### Option 1: Raspberry Pi Zero W as USB-to-WiFi Bridge

**Description**: Use a Raspberry Pi Zero W to read USB numpad input and transmit keystrokes over WiFi.

```
┌─────────────┐     USB      ┌─────────────────────┐     WiFi      ┌─────────────────────┐
│  USB Numpad │──-──────────▶│   Raspberry Pi      │◀───────-─────▶│   Main Server       │
│             │              │   Zero W            │   WebSocket   │   (SSD1305 Display) │
└─────────────┘              │   - evdev reader    │               │   - keyboard_plugin │
                             │   - WebSocket client│               │   - web_simulator   │
                             └─────────────────────┘               └─────────────────────┘
```

**Pros**:
- Full Linux environment for easy development
- Direct USB host support
- Python compatibility with existing keyboard plugin
- Built-in WiFi
- Community support and documentation

**Cons**:
- Higher power consumption (~120mA idle)
- Larger form factor
- Requires SD card and power supply
- Boot time ~30 seconds

### Option 2: ESP32-S2/S3 with Native USB Host

**Description**: Use an ESP32-S2 or ESP32-S3 with native USB host capability to read the numpad and transmit over WiFi.

```
┌─────────────┐     USB      ┌─────────────────────┐     WiFi      ┌─────────────────────┐
│  USB Numpad │────────-────▶│   ESP32-S2/S3       │◀────────-────▶│   Main Server       │
│             │              │   - USB Host stack  │   HTTP/WS     │   (SSD1305 Display) │
└─────────────┘              │   - WiFi client     │               │   - keyboard_plugin │
                             └─────────────────────┘               └─────────────────────┘
```

**Pros**:
- Low power consumption (~20-50mA active)
- Fast boot (~1 second)
- Native USB OTG support
- Small form factor
- CircuitPython compatible

**Cons**:
- Limited USB host library support
- May require custom USB HID parsing
- Less debugging tools available

### Option 3: USB-to-Serial Adapter + WiFi Module

**Description**: Use a dedicated USB host chip (CH559/MAX3421E) connected to an ESP8266/ESP32 for WiFi.

```
┌─────────────┐     USB      ┌─────────────────────┐    Serial    ┌─────────────────────┐
│  USB Numpad │─────-───────▶│   CH559/MAX3421E    │──────-──────▶│   ESP8266/ESP32     │
│             │              │   USB Host Chip     │              │   WiFi Module       │
└─────────────┘              └─────────────────────┘              └──────────┬──────────┘
                                                                             │ WiFi
                                                                             ▼
                                                                  ┌─────────────────────┐
                                                                  │   Main Server       │
                                                                  │   (SSD1305 Display) │
                                                                  └─────────────────────┘
```

**Pros**:
- Dedicated USB host with proven HID support
- Modular design
- Low cost components

**Cons**:
- More complex hardware setup
- Multiple components to manage
- Custom firmware development required

### Option 4: Commercial USB-to-WiFi Device Server

**Description**: Use an off-the-shelf USB device server for enterprise-grade reliability.

```
┌─────────────┐     USB      ┌─────────────────────┐     WiFi      ┌─────────────────────┐
│  USB Numpad │──────-──────▶│   USB Device Server │◀────────-────▶│   Main Server       │
│             │              │   (Silex/Digi/etc)  │   TCP/IP      │   (Virtual USB)     │
└─────────────┘              │                     │               │   - usbip client    │
                             └─────────────────────┘               └─────────────────────┘
```

**Pros**:
- Enterprise-grade reliability
- No firmware development
- Full USB device passthrough
- Professional support available

**Cons**:
- Higher cost ($50-200)
- May require proprietary software
- Less flexibility for customization

### Option 5: ESP32-S3 Wireless Dongle (USB-to-BLE/WiFi Bridge)

**Description**: Use an ESP32-S3 as a compact wireless dongle that reads USB keyboard input via native USB-OTG and transmits over Bluetooth Low Energy (BLE) or WiFi. This approach was featured in the [Hackaday article "A Keyboard For Anything Without A Keyboard"](https://hackaday.com/2026/02/04/a-keyboard-for-anything-without-a-keyboard/).

The ESP32-S3 acts as a USB host, receiving HID reports from the numpad, then forwards keypresses wirelessly. Open-source firmware like [ESP32S3-USB-Keyboard-To-BLE](https://github.com/KoStard/ESP32S3-USB-Keyboard-To-BLE) provides a ready-to-use solution.

```
┌─────────────┐     USB-C OTG    ┌─────────────────────┐   BLE/WiFi    ┌─────────────────────┐
│  USB Numpad │─────────────────▶│   ESP32-S3 Dongle   │◀─────────────▶│   Main Server       │
│             │                  │   - USB Host mode   │               │   (SSD1305 Display) │
└─────────────┘                  │   - BLE HID or WiFi │               │   - BLE/WiFi client │
                                 │   - Multi-device    │               │   - keyboard_plugin │
                                 └─────────────────────┘               └─────────────────────┘
```

**Pros**:
- Very compact form factor (dongle-sized)
- Native USB-OTG hardware (no software emulation)
- Low latency direct HID forwarding
- Multi-device switching (up to 3 paired devices with hotkeys)
- Open-source firmware available
- Low power consumption (~20-50mA)
- Fast boot (~1 second)
- Works with any BLE-compatible device (Windows, macOS, Linux, iOS, Android)

**Cons**:
- ESP32-S3 USB-C port typically doesn't output 5V (requires powered hub or external power)
- Limited USB host channels may not support complex multi-interface devices
- BLE range limited (~10m typical)
- For WiFi mode, additional firmware customization may be needed

**Key Resources**:
- [ESP32S3-USB-Keyboard-To-BLE (GitHub)](https://github.com/KoStard/ESP32S3-USB-Keyboard-To-BLE) - Ready-to-use firmware
- [Hackaday: Wired To Wireless: ESP32 Gives Your USB Keyboard Bluetooth](https://hackaday.com/2026/01/23/wired-to-wireless-esp32-gives-your-usb-keyboard-bluetooth/)
- [Adafruit USB Host to BLE Keyboard Adapter Guide](https://learn.adafruit.com/esp32-s3-usb-to-ble-keyboard-adapter/overview)

---

## Hardware Options

### Recommended Hardware for Option 1 (Raspberry Pi Zero W)

| Component | Product | Price | Link |
|-----------|---------|-------|------|
| SBC | Raspberry Pi Zero W | ~$15 | [raspberrypi.com](https://www.raspberrypi.com/products/raspberry-pi-zero-w/) |
| USB OTG Cable | Micro USB OTG | ~$5 | Standard micro USB OTG adapter |
| Power Supply | 5V 2.5A | ~$10 | Any quality 5V micro USB supply |
| SD Card | 8GB+ microSD | ~$8 | Class 10 recommended |

**Datasheets**:
- [Raspberry Pi Zero W Datasheet](https://datasheets.raspberrypi.com/rpizero/raspberry-pi-zero-w-mechanical-drawing.pdf)
- [BCM2835 ARM Peripherals](https://www.raspberrypi.org/app/uploads/2012/02/BCM2835-ARM-Peripherals.pdf)

### Recommended Hardware for Option 2 (ESP32-S3)

| Component | Product | Price | Link |
|-----------|---------|-------|------|
| MCU Board | ESP32-S3-DevKitC-1 | ~$10 | [Espressif](https://www.espressif.com/en/products/devkits/esp32-s3-devkitc-1) |
| USB-A Connector | USB-A Female Breakout | ~$3 | Standard breakout board |
| Power | USB-C cable | ~$5 | Included with devkit |

**Datasheets**:
- [ESP32-S3 Datasheet](https://www.espressif.com/sites/default/files/documentation/esp32-s3_datasheet_en.pdf)
- [ESP32-S3 Technical Reference](https://www.espressif.com/sites/default/files/documentation/esp32-s3_technical_reference_manual_en.pdf)

### Recommended Hardware for Option 3 (CH559 + ESP32)

| Component | Product | Price | Link |
|-----------|---------|-------|------|
| USB Host | CH559 Development Board | ~$8 | Various vendors on AliExpress |
| WiFi | ESP32-WROOM-32 | ~$5 | [Espressif](https://www.espressif.com/en/products/modules/esp32) |
| Level Shifter | 3.3V-5V Bi-directional | ~$2 | Standard logic level shifter |

**Datasheets**:
- [CH559 Datasheet (English)](http://www.wch-ic.com/downloads/CH559DS1_PDF.html)
- [ESP32-WROOM-32 Datasheet](https://www.espressif.com/sites/default/files/documentation/esp32-wroom-32_datasheet_en.pdf)

### Recommended Hardware for Option 4 (Commercial Device Server)

| Product | Description | Price | Link |
|---------|-------------|-------|------|
| Silex SX-DS-4000U2 | 2-port USB Device Server | ~$150 | [Silex](https://www.silextechnology.com/connectivity-solutions/device-connectivity/sx-ds-4000u2) |
| Digi AnywhereUSB | Industrial USB Hub | ~$200+ | [Digi](https://www.digi.com/products/networking/infrastructure-management/usb-connectivity/anywhereusb) |
| IOGear GUWIP204 | 4-port USB Server | ~$80 | Various retailers |

### Recommended Hardware for Option 5 (ESP32-S3 Wireless Dongle)

| Component | Product | Price | Link |
|-----------|---------|-------|------|
| MCU Board | ESP32-S3-DevKitC-1 | ~$10 | [Espressif](https://www.espressif.com/en/products/devkits/esp32-s3-devkitc-1) |
| MCU Board (Alt) | ESP32-S3-USB-OTG Board | ~$20 | [Espressif](https://www.espressif.com/en/products/devkits/esp32-s3-usb-otg) |
| USB Hub | Powered USB Hub | ~$10-20 | Required if using standard DevKit |
| Power | USB-C cable | ~$5 | Included with devkit |

**Notes on Power**:
- Most ESP32-S3 boards do NOT output 5V on the USB-C port
- Use the **ESP32-S3-USB-OTG** board which has a dedicated USB-A host port with proper 5V output
- Alternatively, use a **powered USB hub** between the ESP32-S3 and keyboard

**Datasheets**:
- [ESP32-S3 Datasheet](https://www.espressif.com/sites/default/files/documentation/esp32-s3_datasheet_en.pdf)
- [ESP32-S3-USB-OTG User Guide](https://docs.espressif.com/projects/esp-dev-kits/en/latest/esp32s3/esp32-s3-usb-otg/user_guide.html)

**Firmware**:
- [ESP32S3-USB-Keyboard-To-BLE](https://github.com/KoStard/ESP32S3-USB-Keyboard-To-BLE) - Open source, ready to use

---

## Architecture Diagrams

### Complete System Architecture (Option 1 - Recommended)

```
                                    ┌─────────────────────────────────────────────────────┐
                                    │                    WiFi Network                      │
                                    └───────────────────────────┬─────────────────────────┘
                                                                │
           ┌────────────────────────────────────────────────────┼────────────────────────────┐
           │                                                    │                            │
           ▼                                                    │                            ▼
┌─────────────────────┐                                         │                 ┌─────────────────────┐
│  USB Numpad Station │                                         │                 │   Display Station   │
├─────────────────────┤                                         │                 ├─────────────────────┤
│                     │                                         │                 │                     │
│  ┌───────────────┐  │                                         │                 │  ┌───────────────┐  │
│  │  USB Numpad   │  │                                         │                 │  │ SSD1305 OLED  │  │
│  │  (HID Device) │  │                                         │                 │  │   Display     │  │
│  └───────┬───────┘  │                                         │                 │  └───────┬───────┘  │
│          │ USB      │                                         │                 │          │ I2C/SPI  │
│          ▼          │                                         │                 │          ▼          │
│  ┌───────────────┐  │    WebSocket: ws://server:8001          │                 │  ┌───────────────┐  │
│  │ Raspberry Pi  │  │◀────────────────────────────────────────┼────────────────▶│  │ Raspberry Pi  │  │
│  │   Zero W      │  │    {"type":"keypress","key":"5"}        │                 │  │  (Main Server)│  │
│  │               │  │                                         │                 │  │               │  │
│  │ - evdev       │  │                                         │                 │  │ - web_sim.py  │  │
│  │ - ws_client   │  │                                         │                 │  │ - keyboard    │  │
│  └───────────────┘  │                                         │                 │  │   plugin      │  │
│                     │                                         │                 │  └───────────────┘  │
└─────────────────────┘                                         │                 └─────────────────────┘
                                                                │
                                                                │
                                                                │                 ┌─────────────────────┐
                                                                │                 │   Web Browser       │
                                                                └────────────────▶│   (Monitoring)      │
                                                                                  │   localhost:8000    │
                                                                                  └─────────────────────┘
```

### Data Flow Diagram

```
┌────────────────────────────────────────────────────────────────────────────────────────────┐
│                                      Data Flow                                              │
└────────────────────────────────────────────────────────────────────────────────────────────┘

  1. Key Press          2. USB HID Event       3. Character           4. WebSocket
     on Numpad            Generated               Extraction             Message
        │                     │                      │                      │
        ▼                     ▼                      ▼                      ▼
   ┌─────────┐          ┌──────────┐          ┌──────────┐          ┌──────────┐
   │  User   │─────────▶│  USB HID │─────────▶│  evdev   │─────────▶│ ws_client│
   │ presses │  keydown │ Scancode │  kernel  │ key code │  Python  │  sends   │
   │  key 5  │          │  0x5E    │  driver  │  KEY_KP5 │          │ {"key":5}│
   └─────────┘          └──────────┘          └──────────┘          └──────────┘
                                                                          │
                                                                          │ WiFi
                                                                          ▼
   ┌─────────┐          ┌──────────┐          ┌──────────┐          ┌──────────┐
   │ Display │◀─────────│ SSD1305  │◀─────────│ keyboard │◀─────────│ ws_server│
   │ shows   │  I2C/SPI │ driver   │  buffer  │ _plugin  │  parse   │ receives │
   │ "5"     │          │ update   │  update  │ processes│  JSON    │ message  │
   └─────────┘          └──────────┘          └──────────┘          └──────────┘

  8. OLED Update        7. Display Buffer      6. Plugin Update       5. Server
                           Changed                                      Processing
```

### Network Protocol Stack

```
┌────────────────────────────────────────────────────────────────┐
│                    Application Layer                            │
├─────────────────────────────┬──────────────────────────────────┤
│     Client (Pi Zero W)      │     Server (Main Pi)             │
│  ┌───────────────────────┐  │  ┌────────────────────────────┐  │
│  │  numpad_client.py     │  │  │  ssd1305_web_simulator.py  │  │
│  │  - Read evdev events  │  │  │  - WebSocket server        │  │
│  │  - Send JSON messages │  │  │  - Keyboard plugin         │  │
│  └───────────────────────┘  │  └────────────────────────────┘  │
├─────────────────────────────┴──────────────────────────────────┤
│                    WebSocket Protocol (RFC 6455)                │
│  Message Format: {"type": "keypress", "key": "<char>"}         │
├────────────────────────────────────────────────────────────────┤
│                    TCP/IP (Port 8001)                           │
├────────────────────────────────────────────────────────────────┤
│                    WiFi (802.11n)                               │
└────────────────────────────────────────────────────────────────┘
```

---

## Implementation Examples

### Option 1: Raspberry Pi Zero W Client

This implementation reads USB numpad input and sends keystrokes over WebSocket to the main server.

#### Client Script (numpad_wifi_client.py)

```python
#!/usr/bin/env python3
"""
USB Numpad to WiFi Bridge Client

This script runs on a Raspberry Pi Zero W connected to the USB numpad.
It reads keyboard events and sends them over WebSocket to the main server.

Requirements:
    pip install evdev websockets

Usage:
    python3 numpad_wifi_client.py --server ws://192.168.1.100:8001
"""

import argparse
import asyncio
import json
import logging
import select
import sys
from typing import Optional

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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Numpad key mapping (evdev key codes to characters)
NUMPAD_KEY_MAP = {
    evdev.ecodes.KEY_KP0: '0',
    evdev.ecodes.KEY_KP1: '1',
    evdev.ecodes.KEY_KP2: '2',
    evdev.ecodes.KEY_KP3: '3',
    evdev.ecodes.KEY_KP4: '4',
    evdev.ecodes.KEY_KP5: '5',
    evdev.ecodes.KEY_KP6: '6',
    evdev.ecodes.KEY_KP7: '7',
    evdev.ecodes.KEY_KP8: '8',
    evdev.ecodes.KEY_KP9: '9',
    evdev.ecodes.KEY_KPENTER: '\n',
    evdev.ecodes.KEY_KPPLUS: '+',
    evdev.ecodes.KEY_KPMINUS: '-',
    evdev.ecodes.KEY_KPASTERISK: '*',
    evdev.ecodes.KEY_KPSLASH: '/',
    evdev.ecodes.KEY_KPDOT: '.',
    evdev.ecodes.KEY_NUMLOCK: None,  # Ignore numlock
    # Also support regular number keys in case numlock is off
    evdev.ecodes.KEY_0: '0',
    evdev.ecodes.KEY_1: '1',
    evdev.ecodes.KEY_2: '2',
    evdev.ecodes.KEY_3: '3',
    evdev.ecodes.KEY_4: '4',
    evdev.ecodes.KEY_5: '5',
    evdev.ecodes.KEY_6: '6',
    evdev.ecodes.KEY_7: '7',
    evdev.ecodes.KEY_8: '8',
    evdev.ecodes.KEY_9: '9',
}


def find_numpad_device() -> Optional[evdev.InputDevice]:
    """Find USB numpad device"""
    devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
    
    for device in devices:
        caps = device.capabilities(verbose=False)
        if 1 not in caps:  # No EV_KEY capability
            continue
            
        keys = caps[1]
        # Check if device has numpad keys
        numpad_keys = [
            evdev.ecodes.KEY_KP0, evdev.ecodes.KEY_KP1, evdev.ecodes.KEY_KP2,
            evdev.ecodes.KEY_KP3, evdev.ecodes.KEY_KP4, evdev.ecodes.KEY_KP5,
            evdev.ecodes.KEY_KP6, evdev.ecodes.KEY_KP7, evdev.ecodes.KEY_KP8,
            evdev.ecodes.KEY_KP9, evdev.ecodes.KEY_KPENTER
        ]
        
        if any(k in keys for k in numpad_keys):
            logger.info(f"Found numpad: {device.name} at {device.path}")
            return device
    
    return None


async def send_keypress(ws, key: str):
    """Send keypress message over WebSocket"""
    message = json.dumps({"type": "keypress", "key": key})
    await ws.send(message)
    logger.debug(f"Sent: {key}")


async def websocket_client(server_url: str, device: evdev.InputDevice):
    """Main WebSocket client loop"""
    reconnect_delay = 1
    max_reconnect_delay = 30
    
    while True:
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
                        try:
                            for event in device.read():
                                if event.type != evdev.ecodes.EV_KEY:
                                    continue
                                if event.value != 1:  # Only key press, not release
                                    continue
                                    
                                char = NUMPAD_KEY_MAP.get(event.code)
                                if char:
                                    await send_keypress(ws, char)
                        except OSError as e:
                            logger.error(f"Device read error: {e}")
                            break
                    
                    # Small delay to prevent busy loop
                    await asyncio.sleep(0.01)
                    
        except websockets.exceptions.ConnectionClosed:
            logger.warning("Connection closed by server")
        except ConnectionRefusedError:
            logger.warning(f"Connection refused, retrying in {reconnect_delay}s...")
        except Exception as e:
            logger.error(f"Error: {e}")
        
        # Exponential backoff for reconnection
        await asyncio.sleep(reconnect_delay)
        reconnect_delay = min(reconnect_delay * 2, max_reconnect_delay)


def main():
    parser = argparse.ArgumentParser(description='USB Numpad to WiFi Bridge')
    parser.add_argument('--server', type=str, default='ws://localhost:8001',
                        help='WebSocket server URL (default: ws://localhost:8001)')
    parser.add_argument('--debug', action='store_true',
                        help='Enable debug logging')
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Find numpad device
    device = find_numpad_device()
    if not device:
        logger.error("No numpad device found!")
        logger.info("Available devices:")
        for path in evdev.list_devices():
            dev = evdev.InputDevice(path)
            logger.info(f"  {dev.path}: {dev.name}")
        sys.exit(1)
    
    logger.info(f"Using device: {device.name}")
    logger.info(f"Connecting to: {args.server}")
    
    # Run async event loop
    try:
        asyncio.run(websocket_client(args.server, device))
    except KeyboardInterrupt:
        logger.info("Shutting down...")


if __name__ == "__main__":
    main()
```

#### Server Integration

The existing `ssd1305_web_simulator.py` already supports receiving keyboard input via WebSocket. Simply run:

```bash
# On the main server (with SSD1305 display)
python3 examples/ssd1305_web_simulator.py --enable-websocket

# On the Pi Zero W (connected to numpad)
python3 numpad_wifi_client.py --server ws://192.168.1.100:8001
```

### Option 2: ESP32-S3 Implementation (Arduino/C++)

For embedded solution with ESP32-S3:

```cpp
/**
 * ESP32-S3 USB Numpad to WiFi Bridge
 * 
 * Requires:
 * - ESP32-S3 board with USB OTG
 * - Arduino ESP32 core v2.0.5+
 * - ESP32 USB Host library
 * - WebSocketsClient library
 */

#include <WiFi.h>
#include <WebSocketsClient.h>
#include <usb/usb_host.h>
#include <hid_host.h>

// WiFi credentials
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";

// WebSocket server
const char* ws_host = "192.168.1.100";
const int ws_port = 8001;

WebSocketsClient webSocket;

// HID Report parser for numpad
void process_hid_report(uint8_t* report, size_t len) {
    // Standard HID keyboard report format:
    // Byte 0: Modifier keys
    // Byte 1: Reserved
    // Byte 2-7: Key codes (up to 6 simultaneous keys)
    
    if (len < 3) return;
    
    for (int i = 2; i < len && i < 8; i++) {
        uint8_t keycode = report[i];
        if (keycode == 0) continue;
        
        char key = translate_keycode(keycode);
        if (key != 0) {
            send_keypress(key);
        }
    }
}

char translate_keycode(uint8_t keycode) {
    // USB HID keycode to character mapping for numpad
    // Reference: USB HID Usage Tables (Section 10: Keyboard/Keypad Page)
    switch (keycode) {
        case 0x59: return '1';  // Keypad 1
        case 0x5A: return '2';  // Keypad 2
        case 0x5B: return '3';  // Keypad 3
        case 0x5C: return '4';  // Keypad 4
        case 0x5D: return '5';  // Keypad 5
        case 0x5E: return '6';  // Keypad 6
        case 0x5F: return '7';  // Keypad 7
        case 0x60: return '8';  // Keypad 8
        case 0x61: return '9';  // Keypad 9
        case 0x62: return '0';  // Keypad 0
        case 0x58: return '\n'; // Keypad Enter
        case 0x57: return '+';  // Keypad +
        case 0x56: return '-';  // Keypad -
        case 0x55: return '*';  // Keypad *
        case 0x54: return '/';  // Keypad /
        case 0x63: return '.';  // Keypad .
        default: return 0;
    }
}

void send_keypress(char key) {
    if (webSocket.isConnected()) {
        String json = "{\"type\":\"keypress\",\"key\":\"";
        if (key == '\n') {
            json += "\\n";
        } else {
            json += key;
        }
        json += "\"}";
        webSocket.sendTXT(json);
        Serial.printf("Sent: %c\n", key);
    }
}

void webSocketEvent(WStype_t type, uint8_t* payload, size_t length) {
    switch (type) {
        case WStype_DISCONNECTED:
            Serial.println("WebSocket Disconnected");
            break;
        case WStype_CONNECTED:
            Serial.println("WebSocket Connected");
            break;
        case WStype_TEXT:
            // Handle incoming messages if needed
            break;
    }
}

void setup() {
    Serial.begin(115200);
    
    // Connect to WiFi
    WiFi.begin(ssid, password);
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.println("\nWiFi connected");
    Serial.println(WiFi.localIP());
    
    // Initialize WebSocket
    webSocket.begin(ws_host, ws_port, "/");
    webSocket.onEvent(webSocketEvent);
    webSocket.setReconnectInterval(5000);
    
    // Initialize USB Host
    // Note: USB Host initialization is board-specific
    // Refer to ESP32-S3 USB Host examples
}

void loop() {
    webSocket.loop();
    // USB Host polling handled by ESP-IDF
}
```

### Systemd Service for Auto-start (Option 1)

Create `/etc/systemd/system/numpad-wifi.service`:

```ini
[Unit]
Description=USB Numpad WiFi Bridge
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=pi
Group=input
ExecStart=/usr/bin/python3 /home/pi/numpad_wifi_client.py --server ws://192.168.1.100:8001
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

Enable with:
```bash
sudo systemctl enable numpad-wifi.service
sudo systemctl start numpad-wifi.service
```

---

## Comparison Matrix

| Feature | Option 1: Pi Zero W | Option 2: ESP32-S3 | Option 3: CH559+ESP | Option 4: Commercial | Option 5: ESP32-S3 Dongle |
|---------|--------------------|--------------------|---------------------|---------------------|---------------------------|
| **Cost** | ~$35-40 | ~$15-20 | ~$15-20 | ~$80-200 | ~$10-25 |
| **Setup Difficulty** | Easy | Medium | Hard | Easy | Easy (pre-built firmware) |
| **Power Consumption** | ~120mA idle | ~20-50mA | ~30-50mA | ~100-200mA | ~20-50mA |
| **Boot Time** | ~30s | ~1s | ~1s | ~10-30s | ~1s |
| **USB Compatibility** | Excellent | Good | Excellent | Excellent | Good (HID only) |
| **Wireless Type** | WiFi | WiFi | WiFi | WiFi | BLE or WiFi |
| **Development Time** | Low | Medium | High | Very Low | Very Low |
| **Customizability** | High | High | Medium | Low | Medium |
| **Form Factor** | Medium | Small | Medium | Large | Very Small (dongle) |
| **Maintenance** | Low | Low | Medium | Very Low | Low |
| **Multi-Device** | No | No | No | No | Yes (3 devices) |

### Recommendation

**For most users**: **Option 1 (Raspberry Pi Zero W)** is recommended because:
- Easy setup with existing Python infrastructure
- Compatible with the existing keyboard plugin
- Reliable WiFi connectivity
- Extensive documentation and community support
- Quick development time

**For embedded/low-power**: **Option 2 (ESP32-S3)** is ideal if:
- Power consumption is critical
- Small form factor required
- Fast boot time needed
- Comfortable with embedded development

**For plug-and-play BLE**: **Option 5 (ESP32-S3 Wireless Dongle)** is ideal if:
- You want the smallest form factor (dongle-sized)
- BLE connectivity is preferred over WiFi
- Multi-device switching is needed (pair with up to 3 devices)
- Ready-to-use firmware with minimal setup
- You need to connect to phones, tablets, or smart TVs

**For enterprise**: **Option 4 (Commercial Device Server)** if:
- Reliability is paramount
- Budget is not constrained
- Minimal development effort preferred
- Professional support required

---

## Additional Resources

### USB HID Specification
- [USB HID Usage Tables](https://usb.org/sites/default/files/hut1_22.pdf) - Official USB-IF document
- [USB HID Class Specification](https://www.usb.org/sites/default/files/hid1_11.pdf)

### Raspberry Pi Documentation
- [Raspberry Pi Zero W](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html)
- [USB OTG on Raspberry Pi](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#usb-mass-storage-boot)

### ESP32 Documentation
- [ESP32-S3 USB Host](https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/api-reference/peripherals/usb_host.html)
- [ESP32-S3 Datasheet](https://www.espressif.com/sites/default/files/documentation/esp32-s3_datasheet_en.pdf)

### ESP32-S3 Wireless Dongle Resources
- [Hackaday: A Keyboard For Anything Without A Keyboard](https://hackaday.com/2026/02/04/a-keyboard-for-anything-without-a-keyboard/) - Original article on ESP32 wireless dongle approach
- [Hackaday: Wired To Wireless: ESP32 Gives Your USB Keyboard Bluetooth](https://hackaday.com/2026/01/23/wired-to-wireless-esp32-gives-your-usb-keyboard-bluetooth/)
- [ESP32S3-USB-Keyboard-To-BLE (GitHub)](https://github.com/KoStard/ESP32S3-USB-Keyboard-To-BLE) - Open source firmware
- [Adafruit USB Host to BLE Keyboard Adapter Guide](https://learn.adafruit.com/esp32-s3-usb-to-ble-keyboard-adapter/overview)
- [ESP32-S3-USB-OTG Development Board](https://docs.espressif.com/projects/esp-dev-kits/en/latest/esp32s3/esp32-s3-usb-otg/user_guide.html)

### evdev Library
- [python-evdev Documentation](https://python-evdev.readthedocs.io/)
- [Linux Input Subsystem](https://www.kernel.org/doc/html/latest/input/input.html)

### WebSocket Protocol
- [RFC 6455 - The WebSocket Protocol](https://tools.ietf.org/html/rfc6455)
- [websockets Python Library](https://websockets.readthedocs.io/)

---

## Conclusion

This guide provides multiple architecture options for integrating a USB numpad over WiFi. The recommended approach using a Raspberry Pi Zero W offers the best balance of ease of implementation, reliability, and compatibility with the existing SSD1305 display simulator infrastructure.

For a compact dongle-style solution, Option 5 (ESP32-S3 Wireless Dongle) provides excellent plug-and-play BLE functionality with ready-to-use open-source firmware.

The provided implementation example can be directly used with the existing `ssd1305_web_simulator.py` WebSocket server, requiring minimal changes to the existing codebase.
