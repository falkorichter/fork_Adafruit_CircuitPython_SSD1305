"""
MMC5983 magnetometer sensor plugin with robust magnet detection.

Uses Median Absolute Deviation (MAD) for outlier-resistant anomaly
detection with conditional baseline updates and hysteresis to prevent
baseline drift and oscillation.  See ``magnet_detector.MagnetDetector``
for full algorithm details.
"""

import math
from typing import Any, Dict

from sensor_plugins.base import SensorPlugin
from sensor_plugins.magnet_detector import MagnetDetector


class MMC5983Plugin(SensorPlugin):
    """Plugin for MMC5983 magnetometer with magnet proximity detection"""

    def __init__(
        self,
        check_interval: float = 5.0,
        baseline_samples: int = 50,
        detection_sigma: float = 5.0,
        release_sigma: float = 3.0,
        min_baseline_samples: int = 10,
    ):
        """
        Initialize MMC5983 sensor plugin

        :param check_interval: How often to check if hardware is available
        :param baseline_samples: Max clean samples kept for MAD baseline
        :param detection_sigma: MAD-sigma threshold for triggering detection
        :param release_sigma: MAD-sigma threshold for releasing detection
        :param min_baseline_samples: Minimum samples before detection starts
        """
        super().__init__("MMC5983", check_interval)
        self.detector = MagnetDetector(
            baseline_samples=baseline_samples,
            detection_sigma=detection_sigma,
            release_sigma=release_sigma,
            min_baseline_samples=min_baseline_samples,
        )

    @property
    def requires_background_updates(self) -> bool:
        """
        MMC5983 requires background updates to maintain the baseline
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

    @staticmethod
    def _calculate_magnitude(x: float, y: float, z: float) -> float:
        """
        Calculate the magnitude of the 3D magnetic field vector

        :param x: X-axis magnetic field (Gauss)
        :param y: Y-axis magnetic field (Gauss)
        :param z: Z-axis magnetic field (Gauss)
        :return: Magnitude of the magnetic field vector (Gauss)
        """
        return math.sqrt(x**2 + y**2 + z**2)

    def _read_sensor_data(self) -> Dict[str, Any]:
        """Read magnetic field data from MMC5983"""
        mag_x, mag_y, mag_z = self.sensor_instance.magnetic
        temperature = self.sensor_instance.temperature

        magnitude = self._calculate_magnitude(mag_x, mag_y, mag_z)
        magnet_detected, baseline, z_score = self.detector.update(magnitude)

        return {
            "mag_x": mag_x,
            "mag_y": mag_y,
            "mag_z": mag_z,
            "magnitude": magnitude,
            "temperature": temperature,
            "magnet_detected": magnet_detected,
            "baseline": baseline,
            "detection_z_score": z_score,
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
            "detection_z_score": "n/a",
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
