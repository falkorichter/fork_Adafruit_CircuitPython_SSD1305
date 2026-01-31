# SPDX-FileCopyrightText: 2026 Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
VEML7700 light sensor plugin
"""

from typing import Any, Dict

from sensor_plugins.base import SensorPlugin


class VEML7700Plugin(SensorPlugin):
    """Plugin for VEML7700 light sensor"""

    def __init__(self, check_interval: float = 5.0):
        super().__init__("VEML7700", check_interval)

    def _initialize_hardware(self) -> Any:
        """Initialize VEML7700 sensor"""
        import adafruit_veml7700  # noqa: PLC0415 - Import inside method for optional dependency
        import board  # noqa: PLC0415 - Import inside method for optional dependency

        i2c = board.I2C()
        return adafruit_veml7700.VEML7700(i2c)

    def _read_sensor_data(self) -> Dict[str, Any]:
        """Read light level from VEML7700"""
        light = self.sensor_instance.light
        return {"light": light}

    def _get_unavailable_data(self) -> Dict[str, Any]:
        """Return n/a for light level"""
        return {"light": "n/a"}

    def format_display(self, data: Dict[str, Any]) -> str:
        """Format light data for display"""
        light = data.get("light", "n/a")
        if light == "n/a":
            return "light:n/a"
        return f"light:{light:.0f}"
