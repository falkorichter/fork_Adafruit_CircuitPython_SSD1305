"""
STHS34PF80 IR presence/motion sensor plugin
"""

from typing import Any, Dict

from sensor_plugins.base import SensorPlugin


class STHS34PF80Plugin(SensorPlugin):
    """Plugin for STHS34PF80 IR presence/motion sensor"""

    def __init__(self, check_interval: float = 5.0, presence_threshold: int = 1000):
        """
        Initialize STHS34PF80 sensor plugin
        
        :param check_interval: How often to check if hardware is available
        :param presence_threshold: Threshold for determining if person is likely present
        """
        super().__init__("STHS34PF80", check_interval)
        self.presence_threshold = presence_threshold

    def _initialize_hardware(self) -> Any:
        """Initialize STHS34PF80 sensor"""
        import adafruit_sths34pf80  # noqa: PLC0415 - Import inside method for optional dependency
        import board  # noqa: PLC0415 - Import inside method for optional dependency

        i2c = board.I2C()
        return adafruit_sths34pf80.STHS34PF80(i2c)

    def _read_sensor_data(self) -> Dict[str, Any]:
        """Read presence, motion and temperature from STHS34PF80"""
        # Get raw sensor values
        presence_value = self.sensor_instance.presence_value
        motion_value = self.sensor_instance.motion_value
        temperature = self.sensor_instance.ambient_temperature
        
        # Determine if person is likely present based on threshold
        # Higher presence_value indicates stronger presence detection
        person_present = presence_value > self.presence_threshold
        
        return {
            "presence_value": presence_value,
            "motion_value": motion_value,
            "temperature": temperature,
            "person_present": person_present,
        }

    def _get_unavailable_data(self) -> Dict[str, Any]:
        """Return n/a for all sensor values"""
        return {
            "presence_value": "n/a",
            "motion_value": "n/a",
            "temperature": "n/a",
            "person_present": "n/a",
        }

    def format_display(self, data: Dict[str, Any]) -> str:
        """Format sensor data for display"""
        person_present = data.get("person_present", "n/a")
        presence_value = data.get("presence_value", "n/a")
        
        if person_present == "n/a":
            return "STHS34:n/a"
        elif person_present:
            return f"STHS34:PRESENT({presence_value})"
        else:
            return f"STHS34:ABSENT({presence_value})"
