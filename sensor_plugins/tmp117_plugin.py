# SPDX-FileCopyrightText: 2026 Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
TMP117 temperature sensor plugin
"""

from typing import Any, Dict

from sensor_plugins.base import SensorPlugin


class TMP117Plugin(SensorPlugin):
    """Plugin for TMP117 temperature sensor"""

    def __init__(self, check_interval: float = 5.0):
        super().__init__("TMP117", check_interval)

    def _initialize_hardware(self) -> Any:
        """Initialize TMP117 sensor"""
        import qwiic_tmp117  # noqa: PLC0415 - Import inside method for optional dependency

        sensor = qwiic_tmp117.QwiicTMP117()
        if not sensor.begin():
            raise RuntimeError("TMP117 not found")
        return sensor

    def _read_sensor_data(self) -> Dict[str, Any]:
        """Read temperature from TMP117"""
        temp_c = self.sensor_instance.read_temp_c()
        return {"temp_c": temp_c}

    def _get_unavailable_data(self) -> Dict[str, Any]:
        """Return n/a for temperature"""
        return {"temp_c": "n/a"}
