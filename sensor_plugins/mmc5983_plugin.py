"""
MMC5983 magnetometer sensor plugin with automatic magnet detection
"""

import math
from collections import deque
from typing import Any, Dict

from sensor_plugins.base import SensorPlugin


class MMC5983Plugin(SensorPlugin):
    """Plugin for MMC5983 magnetometer with magnet proximity detection"""

    def __init__(
        self,
        check_interval: float = 5.0,
        moving_average_samples: int = 20,
        detection_threshold: float = 2.0,
    ):
        """
        Initialize MMC5983 sensor plugin
        
        :param check_interval: How often to check if hardware is available
        :param moving_average_samples: Number of samples for moving average baseline
        :param detection_threshold: Multiplier for detection (2.0 = 2x baseline)
        """
        super().__init__("MMC5983", check_interval)
        self.moving_average_samples = moving_average_samples
        self.detection_threshold = detection_threshold
        self.magnitude_history = deque(maxlen=moving_average_samples)
        self.baseline_magnitude = None

    @property
    def requires_background_updates(self) -> bool:
        """
        MMC5983 requires background updates to maintain moving average baseline
        for magnet detection.
        
        :return: True - needs background updates for baseline tracking
        """
        return True

    def _initialize_hardware(self) -> Any:
        """Initialize MMC5983 sensor"""
        import adafruit_mmc56x3  # noqa: PLC0415 - Import inside method for optional dependency
        import board  # noqa: PLC0415 - Import inside method for optional dependency

        i2c = board.I2C()
        sensor = adafruit_mmc56x3.MMC5983(i2c)
        return sensor

    def _calculate_magnitude(self, x: float, y: float, z: float) -> float:
        """
        Calculate the magnitude of the 3D magnetic field vector
        
        :param x: X-axis magnetic field (Gauss)
        :param y: Y-axis magnetic field (Gauss)
        :param z: Z-axis magnetic field (Gauss)
        :return: Magnitude of the magnetic field vector (Gauss)
        """
        return math.sqrt(x**2 + y**2 + z**2)

    def _update_baseline(self, magnitude: float) -> None:
        """
        Update the moving average baseline
        
        :param magnitude: Current magnetic field magnitude
        """
        self.magnitude_history.append(magnitude)
        
        # Calculate baseline as average of history
        if len(self.magnitude_history) > 0:
            self.baseline_magnitude = sum(self.magnitude_history) / len(
                self.magnitude_history
            )

    def _detect_magnet(self, magnitude: float) -> bool:
        """
        Detect if a magnet is close based on deviation from baseline
        
        :param magnitude: Current magnetic field magnitude
        :return: True if magnet is detected, False otherwise
        """
        if self.baseline_magnitude is None:
            return False
        
        # Detect if current magnitude is significantly higher than baseline
        # Use threshold multiplier (e.g., 2.0 means 2x the baseline)
        return magnitude > (self.baseline_magnitude * self.detection_threshold)

    def _read_sensor_data(self) -> Dict[str, Any]:
        """Read magnetic field data from MMC5983"""
        # Read raw magnetic field values
        mag_x, mag_y, mag_z = self.sensor_instance.magnetic
        temperature = self.sensor_instance.temperature
        
        # Calculate magnitude of the 3D vector
        magnitude = self._calculate_magnitude(mag_x, mag_y, mag_z)
        
        # Update baseline with current reading
        self._update_baseline(magnitude)
        
        # Detect if magnet is close
        magnet_detected = self._detect_magnet(magnitude)
        
        return {
            "mag_x": mag_x,
            "mag_y": mag_y,
            "mag_z": mag_z,
            "magnitude": magnitude,
            "temperature": temperature,
            "magnet_detected": magnet_detected,
            "baseline": self.baseline_magnitude,
        }

    def _get_unavailable_data(self) -> Dict[str, Any]:
        """Return n/a for all magnetic sensor values"""
        return {
            "mag_x": "n/a",
            "mag_y": "n/a",
            "mag_z": "n/a",
            "magnitude": "n/a",
            "temperature": "n/a",
            "magnet_detected": "n/a",
            "baseline": "n/a",
        }

    def format_display(self, data: Dict[str, Any]) -> str:
        """Format magnetic sensor data for display"""
        magnitude = data.get("magnitude", "n/a")
        magnet_detected = data.get("magnet_detected", "n/a")
        
        if magnitude == "n/a":
            return "MAG:n/a"
        
        if magnet_detected:
            return f"MAG:{magnitude:.2f}G 🧲"
        else:
            return f"MAG:{magnitude:.2f}G"
