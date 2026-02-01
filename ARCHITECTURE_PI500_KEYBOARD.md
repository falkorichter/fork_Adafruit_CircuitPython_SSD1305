# Architecture: Raspberry Pi 500+ as External USB/Bluetooth Keyboard

## Overview

This document outlines hardware options for making the **Raspberry Pi 500+** act as an external keyboard to another computer. The Pi 500+ has a built-in keyboard that we want to expose to external devices via USB or Bluetooth.

## Hardware Options

### Option 1: USB HID Gadget Mode (Recommended for USB)

```
┌───────────────────────────────────────────────────────────────┐
│                     RASPBERRY PI 500+                          │
│  ┌─────────────────┐    ┌──────────────────────────────────┐  │
│  │  Built-in       │    │       Linux Kernel               │  │
│  │  Keyboard       ├───►│  evdev ─► USB Gadget Driver      │  │
│  │  (Input Device) │    │           (g_hid / configfs)     │  │
│  └─────────────────┘    └──────────────┬───────────────────┘  │
│                                        │                       │
│                                        ▼                       │
│                              ┌──────────────────┐              │
│                              │  USB-C Port      │              │
│                              │  (OTG Mode)      │              │
│                              └────────┬─────────┘              │
└───────────────────────────────────────┼───────────────────────┘
                                        │ USB Cable
                                        ▼
                              ┌──────────────────┐
                              │  TARGET COMPUTER │
                              │  (Windows/Mac/   │
                              │   Linux)         │
                              └──────────────────┘
```

**Hardware Required:**
- USB-C to USB-A/C cable
- Pi 500+ USB-C port in OTG mode

**Pros:**
- No additional hardware needed
- Low latency, reliable connection
- Native HID support on all operating systems

**Cons:**
- Requires physical USB connection
- Pi 500+ must be in USB gadget mode (can't use USB-C for power while acting as device)

**Datasheets/Resources:**
- [Raspberry Pi USB Gadget Documentation](https://www.raspberrypi.com/documentation/computers/config_txt.html#usb-host-and-gadget-mode)
- [Linux USB Gadget API](https://www.kernel.org/doc/html/latest/driver-api/usb/gadget.html)
- [ConfigFS USB Gadget Documentation](https://www.kernel.org/doc/Documentation/usb/gadget_configfs.txt)

---

### Option 2: USB HID Bridge with Dedicated Controller

```
┌───────────────────────────────────────────────────────────────┐
│                     RASPBERRY PI 500+                          │
│  ┌─────────────────┐    ┌──────────────────────────────────┐  │
│  │  Built-in       │    │  Python Application               │  │
│  │  Keyboard       ├───►│  (keyboard_plugin.py)            │  │
│  │  (evdev)        │    │         │                        │  │
│  └─────────────────┘    └─────────┼────────────────────────┘  │
│                                   │ Serial/I2C/SPI             │
│                                   ▼                            │
│    ┌───────────────────────────────────────────────────────┐  │
│    │  USB HID CONTROLLER BOARD                             │  │
│    │  (Adafruit Trinket M0 / Arduino Pro Micro / Pico)     │  │
│    │  ┌─────────────┐    ┌─────────────┐                   │  │
│    │  │ UART/I2C    │───►│ USB HID     │                   │  │
│    │  │ Input       │    │ Output      │                   │  │
│    │  └─────────────┘    └──────┬──────┘                   │  │
│    └────────────────────────────┼──────────────────────────┘  │
└─────────────────────────────────┼─────────────────────────────┘
                                  │ USB Cable
                                  ▼
                        ┌──────────────────┐
                        │  TARGET COMPUTER │
                        └──────────────────┘
```

**Hardware Options:**

| Board | Interface | Link | Price |
|-------|-----------|------|-------|
| **Adafruit Trinket M0** | USB HID + Serial | [Adafruit](https://www.adafruit.com/product/3500) | ~$9 |
| **Arduino Pro Micro** | USB HID + Serial | [SparkFun](https://www.sparkfun.com/products/12640) | ~$18 |
| **Raspberry Pi Pico** | USB HID + UART | [Raspberry Pi](https://www.raspberrypi.com/products/raspberry-pi-pico/) | ~$4 |
| **Adafruit QT Py** | USB HID + I2C/STEMMA QT | [Adafruit](https://www.adafruit.com/product/4600) | ~$8 |

- Adafruit QT Py ESP32-S2 WiFi Dev Board mit STEMMA QT https://www.berrybase.de/adafruit-qt-py-esp32-s2-wifi-dev-board-mit-stemma-qt

**STEMMA QT/Qwiic Connection Option:**

Since you have a Qwiic/STEMMA QT connector, you can use the **Adafruit QT Py** which has native STEMMA QT support:

```
┌────────────────────┐    STEMMA QT    ┌────────────────────┐
│  Raspberry Pi 500+ │◄──────────────►│  Adafruit QT Py    │
│  (I2C Master)      │    I2C Cable    │  (I2C Slave +      │
│                    │                 │   USB HID Device)  │
└────────────────────┘                 └─────────┬──────────┘
                                                 │ USB
                                                 ▼
                                       ┌──────────────────┐
                                       │  TARGET COMPUTER │
                                       └──────────────────┘
```

**Datasheets:**
- [Adafruit QT Py SAMD21 Datasheet](https://cdn-learn.adafruit.com/downloads/pdf/adafruit-qt-py.pdf)
- [ATSAMD21 Datasheet](https://ww1.microchip.com/downloads/en/DeviceDoc/SAM_D21_DA1_Family_DataSheet_DS40001882F.pdf)
- [Raspberry Pi Pico Datasheet](https://datasheets.raspberrypi.com/pico/pico-datasheet.pdf)
- [STEMMA QT Connector Specs](https://learn.adafruit.com/introducing-adafruit-stemma-qt/what-is-stemma-qt)

---

### Option 3: Bluetooth HID (Wireless - Recommended for Prototype)

```
┌───────────────────────────────────────────────────────────────┐
│                     RASPBERRY PI 500+                          │
│  ┌─────────────────┐    ┌──────────────────────────────────┐  │
│  │  Built-in       │    │  Python Application               │  │
│  │  Keyboard       ├───►│  (bluetooth_keyboard_service.py) │  │
│  │  (evdev)        │    │         │                        │  │
│  └─────────────────┘    └─────────┼────────────────────────┘  │
│                                   │                            │
│                                   ▼                            │
│                    ┌──────────────────────────────┐            │
│                    │  Built-in Bluetooth          │            │
│                    │  (BCM43438 or similar)       │            │
│                    │  BlueZ + D-Bus + HID Profile │            │
│                    └──────────────┬───────────────┘            │
└───────────────────────────────────┼───────────────────────────┘
                                    │ Bluetooth LE/Classic
                                    │ (Wireless)
                                    ▼
                          ┌──────────────────┐
                          │  TARGET COMPUTER │
                          │  (Any Bluetooth  │
                          │   HID Host)      │
                          └──────────────────┘
```

**Hardware Required:**
- No additional hardware (Pi 500+ has built-in Bluetooth)

**Software Stack:**
- BlueZ (Linux Bluetooth stack)
- D-Bus for BlueZ communication
- Python `dbus-python` or `dasbus` library

**Pros:**
- Wireless, no cables needed
- No additional hardware costs
- Can connect to multiple devices
- Perfect for prototyping

**Cons:**
- Slightly higher latency than USB
- Requires pairing setup
- Battery/power still needed on Pi 500+

**Datasheets/Resources:**
- [BlueZ HID Profile](http://www.bluez.org/)
- [Bluetooth HID Specification](https://www.bluetooth.com/specifications/specs/human-interface-device-profile-1-1-1/)
- [BCM43438 Wireless Controller (typical Pi BT chip)](https://www.cypress.com/file/298076/download)

---

### Option 4: External Bluetooth HID Adapter

```
┌───────────────────────────────────────────────────────────────┐
│                     RASPBERRY PI 500+                          │
│  ┌─────────────────┐    ┌──────────────────────────────────┐  │
│  │  Built-in       │    │  Python Application               │  │
│  │  Keyboard       ├───►│  (Sends HID reports via UART)    │  │
│  │  (evdev)        │    │         │                        │  │
│  └─────────────────┘    └─────────┼────────────────────────┘  │
│                                   │ UART/Serial               │
│                                   ▼                            │
│    ┌───────────────────────────────────────────────────────┐  │
│    │  BLUETOOTH HID MODULE                                 │  │
│    │  (Adafruit Bluefruit LE UART Friend / HC-05 with HID) │  │
│    │  ┌─────────────┐    ┌─────────────┐                   │  │
│    │  │ UART Input  │───►│ BT HID      │)))))) Wireless    │  │
│    │  │             │    │ Transmitter │                   │  │
│    │  └─────────────┘    └─────────────┘                   │  │
│    └───────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────┘
                                    │
                                    │ Bluetooth
                                    ▼
                          ┌──────────────────┐
                          │  TARGET COMPUTER │
                          └──────────────────┘
```

**Hardware Options:**

| Module | Interface | Link | Price |
|--------|-----------|------|-------|
| **Adafruit Bluefruit LE UART Friend** | UART | [Adafruit](https://www.adafruit.com/product/2479) | ~$18 |
| **Adafruit Bluefruit LE SPI Friend** | SPI | [Adafruit](https://www.adafruit.com/product/2633) | ~$18 |
| **HM-10 BLE Module** | UART | [Various](https://www.seeedstudio.com/Bluetooth-4-0-Low-Energy-BLE-Pro-Module-HM-10-p-2623.html) | ~$8 |

**Datasheets:**
- [Bluefruit LE UART Friend](https://learn.adafruit.com/introducing-the-adafruit-bluefruit-le-uart-friend)
- [nRF51822 (Bluefruit LE chip) Datasheet](https://infocenter.nordicsemi.com/pdf/nRF51822_PS_v3.4.pdf)

---

## Comparison Matrix

| Aspect | USB Gadget | USB HID Bridge | Bluetooth (Built-in) | External BT |
|--------|------------|----------------|---------------------|-------------|
| **Additional Hardware** | None | $4-18 | None | $8-18 |
| **Wireless** | ❌ | ❌ | ✅ | ✅ |
| **Latency** | Very Low | Low | Medium | Medium |
| **Setup Complexity** | Medium | Medium | Low | Low |
| **Prototype Friendly** | ✅ | ✅ | ✅✅ | ✅ |
| **STEMMA QT Compatible** | N/A | ✅ (QT Py) | N/A | ❌ |

---

## Recommendation for Prototyping

**For a quick prototype, we recommend Option 3: Bluetooth HID with built-in Bluetooth.**

Reasons:
1. No additional hardware purchase required
2. Wireless operation is more practical for keyboard use
3. Easy to integrate with existing keyboard sensor code
4. Works with any Bluetooth-capable target computer

---

## Bluetooth Integration Sketch

Below is a sketch of how to integrate Bluetooth HID functionality into the existing keyboard sensor plugin:

### Architecture Diagram

```
┌────────────────────────────────────────────────────────────────────┐
│                     KEYBOARD BLUETOOTH BRIDGE                       │
│                                                                     │
│   ┌─────────────────────┐         ┌─────────────────────────────┐  │
│   │  keyboard_plugin.py │         │  bluetooth_hid_service.py   │  │
│   │  (Existing)         │         │  (New Component)            │  │
│   │                     │         │                             │  │
│   │  ┌───────────────┐  │         │  ┌───────────────────────┐  │  │
│   │  │ evdev         │  │  keys   │  │  BlueZ D-Bus Client   │  │  │
│   │  │ keyboard      ├──┼────────►│  │                       │  │  │
│   │  │ listener      │  │         │  │  ┌─────────────────┐  │  │  │
│   │  └───────────────┘  │         │  │  │ HID Profile     │  │  │  │
│   │         │           │         │  │  │ (Keyboard)      │  │  │  │
│   │         ▼           │         │  │  └────────┬────────┘  │  │  │
│   │  ┌───────────────┐  │         │  └───────────┼───────────┘  │  │
│   │  │ key_buffer    │  │         │              │              │  │
│   │  │ (display)     │  │         │              │ BT HID       │  │
│   │  └───────────────┘  │         │              ▼              │  │
│   └─────────────────────┘         │     ┌───────────────┐       │  │
│                                   │     │ Bluetooth     │       │  │
│                                   │     │ Radio         │)))))) │  │
│                                   │     └───────────────┘       │  │
│                                   └─────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────┘
```

### Code Integration Sketch

```python
# bluetooth_hid_service.py - New file to add Bluetooth HID support

"""
Bluetooth HID Keyboard Service for Raspberry Pi 500+

This module bridges the keyboard sensor plugin to Bluetooth HID,
allowing the Pi 500+ to act as a wireless keyboard for other devices.

Dependencies:
    pip install dbus-python pybluez

Resources:
    - BlueZ D-Bus API: https://git.kernel.org/pub/scm/bluetooth/bluez.git/tree/doc
    - HID Descriptor: USB HID Usage Tables 1.12
"""

import dbus
import dbus.service
import dbus.mainloop.glib
from gi.repository import GLib
from typing import Callable, Optional

# HID Report Descriptor for a standard keyboard
# Based on USB HID Usage Tables specification
KEYBOARD_HID_DESCRIPTOR = bytes([
    0x05, 0x01,  # Usage Page (Generic Desktop)
    0x09, 0x06,  # Usage (Keyboard)
    0xA1, 0x01,  # Collection (Application)
    0x85, 0x01,  # Report ID (1)
    0x05, 0x07,  # Usage Page (Key Codes)
    0x19, 0xE0,  # Usage Minimum (224)
    0x29, 0xE7,  # Usage Maximum (231)
    0x15, 0x00,  # Logical Minimum (0)
    0x25, 0x01,  # Logical Maximum (1)
    0x75, 0x01,  # Report Size (1)
    0x95, 0x08,  # Report Count (8)
    0x81, 0x02,  # Input (Data, Variable, Absolute) - Modifier keys
    0x95, 0x01,  # Report Count (1)
    0x75, 0x08,  # Report Size (8)
    0x81, 0x01,  # Input (Constant) - Reserved byte
    0x95, 0x06,  # Report Count (6)
    0x75, 0x08,  # Report Size (8)
    0x15, 0x00,  # Logical Minimum (0)
    0x25, 0x65,  # Logical Maximum (101)
    0x05, 0x07,  # Usage Page (Key Codes)
    0x19, 0x00,  # Usage Minimum (0)
    0x29, 0x65,  # Usage Maximum (101)
    0x81, 0x00,  # Input (Data, Array) - Key array
    0xC0,        # End Collection
])

# USB HID key codes for common characters
CHAR_TO_HID_KEYCODE = {
    'a': 0x04, 'b': 0x05, 'c': 0x06, 'd': 0x07, 'e': 0x08,
    'f': 0x09, 'g': 0x0A, 'h': 0x0B, 'i': 0x0C, 'j': 0x0D,
    'k': 0x0E, 'l': 0x0F, 'm': 0x10, 'n': 0x11, 'o': 0x12,
    'p': 0x13, 'q': 0x14, 'r': 0x15, 's': 0x16, 't': 0x17,
    'u': 0x18, 'v': 0x19, 'w': 0x1A, 'x': 0x1B, 'y': 0x1C,
    'z': 0x1D, '1': 0x1E, '2': 0x1F, '3': 0x20, '4': 0x21,
    '5': 0x22, '6': 0x23, '7': 0x24, '8': 0x25, '9': 0x26,
    '0': 0x27, ' ': 0x2C,  # Space
}


class BluetoothHIDService:
    """
    Bluetooth HID Keyboard Service
    
    This service registers the Pi 500+ as a Bluetooth HID keyboard device
    and forwards key events to connected hosts.
    
    Usage:
        service = BluetoothHIDService()
        service.start()
        
        # When a key is pressed (from keyboard_plugin)
        service.send_key('a')
        
        # When done
        service.stop()
    """
    
    BT_PROFILE_PATH = "/org/bluez/hid_keyboard"
    HID_UUID = "00001124-0000-1000-8000-00805f9b34fb"  # HID Service UUID
    
    def __init__(self, device_name: str = "Pi500 Keyboard"):
        self.device_name = device_name
        self.bus = None
        self.mainloop = None
        self.connected = False
        self._on_connect_callback: Optional[Callable] = None
        self._on_disconnect_callback: Optional[Callable] = None
        
    def start(self):
        """Initialize and start the Bluetooth HID service"""
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        self.bus = dbus.SystemBus()
        
        # Configure Bluetooth adapter
        self._configure_adapter()
        
        # Register HID profile
        self._register_hid_profile()
        
        # Start main loop in background thread
        # The GLib main loop handles D-Bus events and must run continuously.
        # Since it blocks, we run it in a separate daemon thread to avoid
        # blocking the caller. Use threading.Thread for simplicity.
        self.mainloop = GLib.MainLoop()
        import threading
        self._mainloop_thread = threading.Thread(target=self.mainloop.run, daemon=True)
        self._mainloop_thread.start()
        
    def stop(self):
        """Stop the Bluetooth HID service"""
        if self.mainloop:
            self.mainloop.quit()
            
    def _configure_adapter(self):
        """Configure the Bluetooth adapter for HID mode"""
        adapter = dbus.Interface(
            self.bus.get_object("org.bluez", "/org/bluez/hci0"),
            "org.freedesktop.DBus.Properties"
        )
        
        # Make adapter discoverable and pairable
        adapter.Set("org.bluez.Adapter1", "Powered", dbus.Boolean(True))
        adapter.Set("org.bluez.Adapter1", "Discoverable", dbus.Boolean(True))
        adapter.Set("org.bluez.Adapter1", "Pairable", dbus.Boolean(True))
        adapter.Set("org.bluez.Adapter1", "Alias", dbus.String(self.device_name))
        
    def _register_hid_profile(self):
        """Register the HID keyboard profile with BlueZ"""
        manager = dbus.Interface(
            self.bus.get_object("org.bluez", "/org/bluez"),
            "org.bluez.ProfileManager1"
        )
        
        opts = {
            "Name": dbus.String("Pi500 HID Keyboard"),
            "Role": dbus.String("server"),
            "RequireAuthentication": dbus.Boolean(False),
            "RequireAuthorization": dbus.Boolean(False),
            "ServiceRecord": self._get_sdp_record(),
        }
        
        manager.RegisterProfile(self.BT_PROFILE_PATH, self.HID_UUID, opts)
        
    def _get_sdp_record(self) -> str:
        """Return SDP service record XML for HID keyboard"""
        return '''<?xml version="1.0" encoding="UTF-8" ?>
        <record>
            <attribute id="0x0001">
                <sequence>
                    <uuid value="0x1124"/>
                </sequence>
            </attribute>
            <attribute id="0x0004">
                <sequence>
                    <sequence>
                        <uuid value="0x0100"/>
                        <uint16 value="0x0011"/>
                    </sequence>
                    <sequence>
                        <uuid value="0x0011"/>
                    </sequence>
                </sequence>
            </attribute>
            <attribute id="0x0005">
                <sequence>
                    <uuid value="0x1002"/>
                </sequence>
            </attribute>
            <attribute id="0x0006">
                <sequence>
                    <uint16 value="0x656e"/>
                    <uint16 value="0x006a"/>
                    <uint16 value="0x0100"/>
                </sequence>
            </attribute>
            <attribute id="0x0009">
                <sequence>
                    <sequence>
                        <uuid value="0x1124"/>
                        <uint16 value="0x0100"/>
                    </sequence>
                </sequence>
            </attribute>
            <attribute id="0x000d">
                <sequence>
                    <sequence>
                        <sequence>
                            <uuid value="0x0100"/>
                            <uint16 value="0x0013"/>
                        </sequence>
                        <sequence>
                            <uuid value="0x0011"/>
                        </sequence>
                    </sequence>
                </sequence>
            </attribute>
            <attribute id="0x0100">
                <text value="Pi500 Keyboard"/>
            </attribute>
            <attribute id="0x0101">
                <text value="Raspberry Pi 500+ Bluetooth Keyboard"/>
            </attribute>
            <attribute id="0x0102">
                <text value="Raspberry Pi"/>
            </attribute>
            <attribute id="0x0200">
                <uint16 value="0x0100"/>
            </attribute>
            <attribute id="0x0201">
                <uint16 value="0x0111"/>
            </attribute>
            <attribute id="0x0202">
                <uint8 value="0x40"/>
            </attribute>
            <attribute id="0x0203">
                <uint8 value="0x00"/>
            </attribute>
            <attribute id="0x0204">
                <boolean value="true"/>
            </attribute>
            <attribute id="0x0205">
                <boolean value="true"/>
            </attribute>
            <attribute id="0x0206">
                <sequence>
                    <sequence>
                        <uint8 value="0x22"/>
                        <text encoding="hex" value="''' + KEYBOARD_HID_DESCRIPTOR.hex() + '''"/>
                    </sequence>
                </sequence>
            </attribute>
        </record>
        '''
        
    def send_key(self, char: str, pressed: bool = True):
        """
        Send a key event via Bluetooth HID
        
        Args:
            char: The character to send (a-z, 0-9, space)
            pressed: True for key press, False for key release
        """
        keycode = CHAR_TO_HID_KEYCODE.get(char.lower())
        if keycode is None:
            return
            
        # Build HID report: [Report ID, Modifiers, Reserved, Key1-6]
        if pressed:
            report = bytes([0x01, 0x00, 0x00, keycode, 0x00, 0x00, 0x00, 0x00, 0x00])
        else:
            report = bytes([0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
            
        self._send_hid_report(report)
        
    def _send_hid_report(self, report: bytes):
        """
        Send an HID report to connected host.
        
        Implementation notes:
        - For BlueZ 5.x, use the org.bluez.Profile1 interface with NewConnection()
          to get a file descriptor, then write HID reports directly to the socket.
        - Alternatively, use the org.bluez.Input1 interface for established connections.
        - Reference: https://git.kernel.org/pub/scm/bluetooth/bluez.git/tree/doc/profile-api.txt
        - Reference: https://github.com/AnesBenmerzoug/Bluetooth-HID-Controller (Python example)
        
        Example socket write (once connected):
            self._hid_socket.send(report)
        """
        # Placeholder - actual implementation writes to the L2CAP socket
        # obtained from BlueZ ProfileManager1.NewConnection callback
        if hasattr(self, '_hid_socket') and self._hid_socket:
            try:
                self._hid_socket.send(report)
            except OSError:
                pass  # Connection lost
        
    def on_connect(self, callback: Callable):
        """Register callback for when a host connects"""
        self._on_connect_callback = callback
        
    def on_disconnect(self, callback: Callable):
        """Register callback for when a host disconnects"""
        self._on_disconnect_callback = callback


# Integration with existing KeyboardPlugin
class BluetoothKeyboardBridge:
    """
    Bridge between KeyboardPlugin and BluetoothHIDService
    
    This class connects the existing keyboard sensor plugin to the
    Bluetooth HID service, forwarding all key events wirelessly.
    
    Usage:
        from sensor_plugins import KeyboardPlugin
        
        keyboard = KeyboardPlugin()
        bt_service = BluetoothHIDService()
        bridge = BluetoothKeyboardBridge(keyboard, bt_service)
        
        bridge.start()
    """
    
    def __init__(self, keyboard_plugin, bt_service: BluetoothHIDService):
        self.keyboard = keyboard_plugin
        self.bt_service = bt_service
        
    def start(self):
        """
        Start the bridge - keyboard events will be forwarded via Bluetooth.
        
        NOTE: This example uses monkey-patching for simplicity, but a cleaner
        production approach would be to modify KeyboardPlugin to support
        an observer/callback pattern:
        
            # In keyboard_plugin.py, add:
            def register_key_listener(self, callback):
                self._listeners.append(callback)
            
            # Then in _process_keyboard_event, call:
            for listener in self._listeners:
                listener(char)
        
        This would allow:
            bridge.keyboard.register_key_listener(bridge._on_key_pressed)
        """
        # Simple approach: intercept buffer append to forward keys
        original_append = self.keyboard.key_buffer.append
        
        def forwarding_append(char):
            original_append(char)
            # Forward to Bluetooth
            self.bt_service.send_key(char, pressed=True)
            self.bt_service.send_key(char, pressed=False)  # Key release
            
        self.keyboard.key_buffer.append = forwarding_append
        
        # Start Bluetooth service
        self.bt_service.start()
    
    def _on_key_pressed(self, char: str):
        """
        Callback for observer pattern (recommended approach).
        Forward key press to Bluetooth HID service.
        """
        self.bt_service.send_key(char, pressed=True)
        self.bt_service.send_key(char, pressed=False)
```

---

## Hardware Links Summary

### USB HID Controllers
| Product | Link | Datasheet |
|---------|------|-----------|
| Adafruit Trinket M0 | [Buy](https://www.adafruit.com/product/3500) | [Learn](https://learn.adafruit.com/adafruit-trinket-m0-circuitpython-arduino) |
| Adafruit QT Py SAMD21 | [Buy](https://www.adafruit.com/product/4600) | [Learn](https://learn.adafruit.com/adafruit-qt-py) |
| Arduino Pro Micro | [Buy](https://www.sparkfun.com/products/12640) | [Hookup Guide](https://learn.sparkfun.com/tutorials/pro-micro--fio-v3-hookup-guide) |
| Raspberry Pi Pico | [Buy](https://www.raspberrypi.com/products/raspberry-pi-pico/) | [Datasheet](https://datasheets.raspberrypi.com/pico/pico-datasheet.pdf) |

### Bluetooth Modules
| Product | Link | Datasheet |
|---------|------|-----------|
| Adafruit Bluefruit LE UART Friend | [Buy](https://www.adafruit.com/product/2479) | [Learn](https://learn.adafruit.com/introducing-the-adafruit-bluefruit-le-uart-friend) |
| Adafruit Bluefruit LE SPI Friend | [Buy](https://www.adafruit.com/product/2633) | [Learn](https://learn.adafruit.com/introducing-the-adafruit-bluefruit-le-spi-friend) |

### STEMMA QT / Qwiic Accessories
| Product | Link | Notes |
|---------|------|-------|
| STEMMA QT / Qwiic JST SH 4-Pin Cable | [Buy](https://www.adafruit.com/product/4210) | For connecting to I2C devices |
| SparkFun Qwiic Cable Kit | [Buy](https://www.sparkfun.com/products/15081) | Various lengths |

### Specifications
| Document | Link |
|----------|------|
| USB HID Usage Tables 1.12 | [USB.org](https://www.usb.org/sites/default/files/documents/hut1_12v2.pdf) |
| Bluetooth HID Profile 1.1.1 | [Bluetooth.com](https://www.bluetooth.com/specifications/specs/human-interface-device-profile-1-1-1/) |
| BlueZ Documentation | [BlueZ.org](http://www.bluez.org/) |
| Linux USB Gadget API | [Kernel.org](https://www.kernel.org/doc/html/latest/driver-api/usb/gadget.html) |

---

## Next Steps

1. **For Bluetooth Prototype:**
   - Install dependencies: `pip install dbus-python`
   - Create `bluetooth_hid_service.py` based on the sketch above
   - Test pairing with target computer
   - Integrate with existing `keyboard_plugin.py`

2. **For USB Gadget Mode:**
   - Enable USB gadget mode in `/boot/config.txt`
   - Configure dwc2 overlay
   - Create HID gadget using ConfigFS

3. **For USB HID Bridge:**
   - Purchase Adafruit QT Py or similar
   - Flash with CircuitPython USB HID firmware
   - Connect via STEMMA QT to Pi 500+
   - Write serial/I2C bridge code
