"""
Sensor plugin system for hot-pluggable sensor support
"""

from sensor_plugins.base import SensorPlugin
from sensor_plugins.bme680_plugin import BME680Plugin
from sensor_plugins.keyboard_plugin import KeyboardPlugin
from sensor_plugins.system_info_plugin import CPULoadPlugin, IPAddressPlugin, MemoryUsagePlugin
from sensor_plugins.tmp117_plugin import TMP117Plugin
from sensor_plugins.veml7700_plugin import VEML7700Plugin

# Bluetooth HID is optional - only import if dependencies are available
try:
    from sensor_plugins.bluetooth_hid_service import (
        BluetoothHIDService,
        BluetoothKeyboardBridge,
    )

    _BLUETOOTH_HID_AVAILABLE = True
except ImportError:
    _BLUETOOTH_HID_AVAILABLE = False

__all__ = [
    "SensorPlugin",
    "TMP117Plugin",
    "BME680Plugin",
    "VEML7700Plugin",
    "IPAddressPlugin",
    "CPULoadPlugin",
    "MemoryUsagePlugin",
    "KeyboardPlugin",
]

# Add Bluetooth HID exports only if available
if _BLUETOOTH_HID_AVAILABLE:
    __all__.extend(["BluetoothHIDService", "BluetoothKeyboardBridge"])
