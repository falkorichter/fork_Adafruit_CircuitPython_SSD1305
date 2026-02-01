"""
Bluetooth HID Keyboard Service for Raspberry Pi 500+

This module bridges the keyboard sensor plugin to Bluetooth HID,
allowing the Pi 500+ to act as a wireless keyboard for other devices.

Dependencies:
    pip install dbus-python PyGObject

Usage:
    from sensor_plugins.bluetooth_hid_service import (
        BluetoothHIDService,
        BluetoothKeyboardBridge
    )
    from sensor_plugins import KeyboardPlugin

    # Create components
    keyboard = KeyboardPlugin()
    bt_service = BluetoothHIDService()
    bridge = BluetoothKeyboardBridge(keyboard, bt_service)

    # Start the bridge (this also starts the BT service)
    bridge.start()

Resources:
    - BlueZ D-Bus API: https://git.kernel.org/pub/scm/bluetooth/bluez.git/tree/doc
    - HID Descriptor: USB HID Usage Tables 1.12
    - Bluetooth HID Profile: https://www.bluetooth.com/specifications/specs/human-interface-device-profile-1-1-1/
"""

import logging
import socket
import threading
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

# HID Report Descriptor for a standard keyboard
# Based on USB HID Usage Tables specification
KEYBOARD_HID_DESCRIPTOR = bytes(
    [
        0x05,
        0x01,  # Usage Page (Generic Desktop)
        0x09,
        0x06,  # Usage (Keyboard)
        0xA1,
        0x01,  # Collection (Application)
        0x85,
        0x01,  # Report ID (1)
        0x05,
        0x07,  # Usage Page (Key Codes)
        0x19,
        0xE0,  # Usage Minimum (224)
        0x29,
        0xE7,  # Usage Maximum (231)
        0x15,
        0x00,  # Logical Minimum (0)
        0x25,
        0x01,  # Logical Maximum (1)
        0x75,
        0x01,  # Report Size (1)
        0x95,
        0x08,  # Report Count (8)
        0x81,
        0x02,  # Input (Data, Variable, Absolute) - Modifier keys
        0x95,
        0x01,  # Report Count (1)
        0x75,
        0x08,  # Report Size (8)
        0x81,
        0x01,  # Input (Constant) - Reserved byte
        0x95,
        0x06,  # Report Count (6)
        0x75,
        0x08,  # Report Size (8)
        0x15,
        0x00,  # Logical Minimum (0)
        0x25,
        0x65,  # Logical Maximum (101)
        0x05,
        0x07,  # Usage Page (Key Codes)
        0x19,
        0x00,  # Usage Minimum (0)
        0x29,
        0x65,  # Usage Maximum (101)
        0x81,
        0x00,  # Input (Data, Array) - Key array
        0xC0,  # End Collection
    ]
)

# USB HID key codes for common characters
CHAR_TO_HID_KEYCODE = {
    "a": 0x04,
    "b": 0x05,
    "c": 0x06,
    "d": 0x07,
    "e": 0x08,
    "f": 0x09,
    "g": 0x0A,
    "h": 0x0B,
    "i": 0x0C,
    "j": 0x0D,
    "k": 0x0E,
    "l": 0x0F,
    "m": 0x10,
    "n": 0x11,
    "o": 0x12,
    "p": 0x13,
    "q": 0x14,
    "r": 0x15,
    "s": 0x16,
    "t": 0x17,
    "u": 0x18,
    "v": 0x19,
    "w": 0x1A,
    "x": 0x1B,
    "y": 0x1C,
    "z": 0x1D,
    "1": 0x1E,
    "2": 0x1F,
    "3": 0x20,
    "4": 0x21,
    "5": 0x22,
    "6": 0x23,
    "7": 0x24,
    "8": 0x25,
    "9": 0x26,
    "0": 0x27,
    " ": 0x2C,  # Space
    "\n": 0x28,  # Enter
    "\t": 0x2B,  # Tab
}

# L2CAP ports for HID
L2CAP_PSM_HID_CONTROL = 0x11  # HID Control channel
L2CAP_PSM_HID_INTERRUPT = 0x13  # HID Interrupt channel


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
        """
        Initialize the Bluetooth HID service.

        :param device_name: Name to advertise for the Bluetooth device
        """
        self.device_name = device_name
        self.bus = None
        self.mainloop = None
        self.connected = False
        self._on_connect_callback: Optional[Callable[[], None]] = None
        self._on_disconnect_callback: Optional[Callable[[], None]] = None
        self._control_socket: Optional[socket.socket] = None
        self._interrupt_socket: Optional[socket.socket] = None
        self._running = False
        self._accept_thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Initialize and start the Bluetooth HID service"""
        try:
            import dbus  # noqa: PLC0415
            import dbus.mainloop.glib  # noqa: PLC0415
            from gi.repository import GLib  # noqa: PLC0415
        except ImportError as e:
            raise ImportError(
                "Bluetooth HID requires dbus-python and PyGObject. "
                "Install with: pip install dbus-python PyGObject"
            ) from e

        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        self.bus = dbus.SystemBus()

        # Configure Bluetooth adapter
        self._configure_adapter(dbus)

        # Register HID profile
        self._register_hid_profile(dbus)

        # Start L2CAP sockets for HID
        self._start_hid_sockets()

        # Start main loop in background thread
        # The GLib main loop handles D-Bus events and must run continuously.
        # Since it blocks, we run it in a separate daemon thread.
        self.mainloop = GLib.MainLoop()
        self._mainloop_thread = threading.Thread(target=self.mainloop.run, daemon=True)
        self._mainloop_thread.start()

        # Wait briefly for the mainloop to start
        import time  # noqa: PLC0415

        time.sleep(0.1)

        logger.info("Bluetooth HID service started as '%s'", self.device_name)

    def stop(self) -> None:
        """Stop the Bluetooth HID service"""
        self._running = False

        if self._control_socket:
            try:
                self._control_socket.close()
            except OSError:
                pass
            self._control_socket = None

        if self._interrupt_socket:
            try:
                self._interrupt_socket.close()
            except OSError:
                pass
            self._interrupt_socket = None

        if self.mainloop:
            self.mainloop.quit()

        logger.info("Bluetooth HID service stopped")

    def _configure_adapter(self, dbus: Any) -> None:
        """Configure the Bluetooth adapter for HID mode"""
        try:
            adapter = dbus.Interface(
                self.bus.get_object("org.bluez", "/org/bluez/hci0"),
                "org.freedesktop.DBus.Properties",
            )

            # Make adapter discoverable and pairable
            adapter.Set("org.bluez.Adapter1", "Powered", dbus.Boolean(True))
            adapter.Set("org.bluez.Adapter1", "Discoverable", dbus.Boolean(True))
            adapter.Set("org.bluez.Adapter1", "Pairable", dbus.Boolean(True))
            adapter.Set("org.bluez.Adapter1", "Alias", dbus.String(self.device_name))

            logger.info("Bluetooth adapter configured: %s", self.device_name)
        except Exception as e:
            logger.error("Failed to configure Bluetooth adapter: %s", e)
            raise

    def _register_hid_profile(self, dbus: Any) -> None:
        """Register the HID keyboard profile with BlueZ"""
        try:
            manager = dbus.Interface(
                self.bus.get_object("org.bluez", "/org/bluez"),
                "org.bluez.ProfileManager1",
            )

            opts = {
                "Name": dbus.String("Pi500 HID Keyboard"),
                "Role": dbus.String("server"),
                # Enable authentication for security - requires pairing before use
                "RequireAuthentication": dbus.Boolean(True),
                "RequireAuthorization": dbus.Boolean(False),
                "ServiceRecord": self._get_sdp_record(),
            }

            manager.RegisterProfile(self.BT_PROFILE_PATH, self.HID_UUID, opts)
            logger.info("HID profile registered")
        except Exception as e:
            logger.error("Failed to register HID profile: %s", e)
            raise

    def _start_hid_sockets(self) -> None:
        """Start L2CAP sockets for HID communication"""
        self._running = True

        # Create control channel socket
        # Note: Binding to "" (all interfaces) is required for Bluetooth L2CAP sockets
        # to accept connections from any paired Bluetooth device. This is secured by
        # RequireAuthentication=True in the HID profile registration.
        self._control_socket = socket.socket(
            socket.AF_BLUETOOTH, socket.SOCK_SEQPACKET, socket.BTPROTO_L2CAP
        )
        self._control_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._control_socket.bind(("", L2CAP_PSM_HID_CONTROL))  # noqa: S104
        self._control_socket.listen(1)

        # Create interrupt channel socket
        self._interrupt_socket = socket.socket(
            socket.AF_BLUETOOTH, socket.SOCK_SEQPACKET, socket.BTPROTO_L2CAP
        )
        self._interrupt_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._interrupt_socket.bind(("", L2CAP_PSM_HID_INTERRUPT))  # noqa: S104
        self._interrupt_socket.listen(1)

        # Start accept thread
        self._accept_thread = threading.Thread(target=self._accept_connections, daemon=True)
        self._accept_thread.start()

        logger.info("HID L2CAP sockets started")

    def _accept_connections(self) -> None:
        """Accept incoming HID connections"""
        while self._running:
            try:
                self._control_socket.settimeout(1.0)
                self._interrupt_socket.settimeout(1.0)

                # Accept control channel
                try:
                    control_client, control_addr = self._control_socket.accept()
                    logger.info("Control channel connected from %s", control_addr)
                except socket.timeout:
                    continue

                # Accept interrupt channel
                try:
                    interrupt_client, interrupt_addr = self._interrupt_socket.accept()
                    logger.info("Interrupt channel connected from %s", interrupt_addr)
                except socket.timeout:
                    control_client.close()
                    continue

                # Store client sockets
                self._hid_control = control_client
                self._hid_interrupt = interrupt_client
                self.connected = True

                if self._on_connect_callback:
                    self._on_connect_callback()

                logger.info("HID client connected")

            except OSError:
                if self._running:
                    logger.error("Socket error in accept loop")
                break

    def _get_sdp_record(self) -> str:
        """Return SDP service record XML for HID keyboard"""
        hid_descriptor_hex = KEYBOARD_HID_DESCRIPTOR.hex()
        return f"""<?xml version="1.0" encoding="UTF-8" ?>
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
                <text value="{self.device_name}"/>
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
                        <text encoding="hex" value="{hid_descriptor_hex}"/>
                    </sequence>
                </sequence>
            </attribute>
        </record>
        """

    def send_key(self, char: str, pressed: bool = True) -> bool:
        """
        Send a key event via Bluetooth HID

        :param char: The character to send (a-z, 0-9, space, etc.)
        :param pressed: True for key press, False for key release
        :return: True if sent successfully, False otherwise
        """
        if not self.connected:
            return False

        keycode = CHAR_TO_HID_KEYCODE.get(char.lower())
        if keycode is None:
            logger.debug("Unknown character: %s", char)
            return False

        # Build HID report: [Report ID, Modifiers, Reserved, Key1-6]
        if pressed:
            report = bytes([0xA1, 0x01, 0x00, 0x00, keycode, 0x00, 0x00, 0x00, 0x00, 0x00])
        else:
            report = bytes([0xA1, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])

        return self._send_hid_report(report)

    def _send_hid_report(self, report: bytes) -> bool:
        """
        Send an HID report to connected host.

        :param report: The HID report bytes to send
        :return: True if sent successfully, False otherwise
        """
        if not hasattr(self, "_hid_interrupt") or self._hid_interrupt is None:
            return False

        try:
            self._hid_interrupt.send(report)
            return True
        except OSError as e:
            logger.error("Failed to send HID report: %s", e)
            self.connected = False
            if self._on_disconnect_callback:
                self._on_disconnect_callback()
            return False

    def on_connect(self, callback: Callable[[], None]) -> None:
        """Register callback for when a host connects"""
        self._on_connect_callback = callback

    def on_disconnect(self, callback: Callable[[], None]) -> None:
        """Register callback for when a host disconnects"""
        self._on_disconnect_callback = callback


class BluetoothKeyboardBridge:
    """
    Bridge between KeyboardPlugin and BluetoothHIDService

    This class connects the existing keyboard sensor plugin to the
    Bluetooth HID service, forwarding all key events wirelessly.

    Usage:
        from sensor_plugins import KeyboardPlugin
        from sensor_plugins.bluetooth_hid_service import (
            BluetoothHIDService,
            BluetoothKeyboardBridge
        )

        keyboard = KeyboardPlugin()
        bt_service = BluetoothHIDService()
        bridge = BluetoothKeyboardBridge(keyboard, bt_service)

        bridge.start()
    """

    def __init__(self, keyboard_plugin: Any, bt_service: BluetoothHIDService):
        """
        Initialize the bridge.

        :param keyboard_plugin: KeyboardPlugin instance to bridge
        :param bt_service: BluetoothHIDService instance to send keys to
        """
        self.keyboard = keyboard_plugin
        self.bt_service = bt_service
        self._original_append: Optional[Callable] = None

    def start(self) -> None:
        """
        Start the bridge - keyboard events will be forwarded via Bluetooth.

        This method patches the keyboard plugin to forward key events.
        For a cleaner approach, consider using register_key_listener() if
        the keyboard plugin supports it.
        """
        # Check if keyboard plugin supports observer pattern
        if hasattr(self.keyboard, "register_key_listener"):
            self.keyboard.register_key_listener(self._on_key_pressed)
            logger.info("Using observer pattern for key forwarding")
        else:
            # Fallback: intercept buffer append to forward keys
            self._original_append = self.keyboard.key_buffer.append

            def _append_and_forward(char: str) -> None:
                """Wrapper that appends to buffer and forwards to Bluetooth"""
                if self._original_append:
                    self._original_append(char)
                # Forward to Bluetooth
                self._on_key_pressed(char)

            self.keyboard.key_buffer.append = _append_and_forward
            logger.info("Using buffer interception for key forwarding")

        # Start Bluetooth service
        self.bt_service.start()

    def stop(self) -> None:
        """Stop the bridge and restore original behavior"""
        # Restore original append if we patched it
        if self._original_append is not None:
            self.keyboard.key_buffer.append = self._original_append
            self._original_append = None

        # Stop Bluetooth service
        self.bt_service.stop()

    def _on_key_pressed(self, char: str) -> None:
        """
        Callback for key press events.
        Forward key press and release to Bluetooth HID service.

        :param char: The character that was pressed
        """
        self.bt_service.send_key(char, pressed=True)
        self.bt_service.send_key(char, pressed=False)
