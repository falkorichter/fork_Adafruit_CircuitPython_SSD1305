"""
Base sensor plugin class
"""

import time
from abc import ABC, abstractmethod
from typing import Any, Dict


class SensorPlugin(ABC):
    """Base class for sensor plugins"""

    def __init__(self, name: str, check_interval: float = 5.0):
        """
        Initialize the sensor plugin
        
        :param name: Display name for the sensor
        :param check_interval: How often to check if hardware is available (seconds)
        """
        self.name = name
        self.check_interval = check_interval
        self.available = False
        self.last_check_time = 0
        self.sensor_instance = None

    @property
    def requires_background_updates(self) -> bool:
        """
        Whether this sensor requires continuous background updates even when display is off.
        
        Override this property to return True for sensors that need to maintain state
        (e.g., burn-in periods, calibration, running averages) even when display is blanked.
        
        :return: True if sensor needs background updates, False otherwise (default)
        """
        return False

    @abstractmethod
    def _initialize_hardware(self) -> Any:
        """
        Initialize and return the hardware sensor instance.
        This should raise an exception if hardware is not available.
        
        :return: The initialized sensor object
        """
        pass

    @abstractmethod
    def _read_sensor_data(self) -> Dict[str, Any]:
        """
        Read data from the sensor.
        
        :return: Dictionary with sensor readings
        """
        pass

    def check_availability(self) -> bool:
        """
        Check if the sensor hardware is available.
        Automatically called periodically based on check_interval.
        
        :return: True if sensor is available, False otherwise
        """
        current_time = time.time()
        if current_time - self.last_check_time < self.check_interval:
            return self.available

        self.last_check_time = current_time

        try:
            if self.sensor_instance is None:
                self.sensor_instance = self._initialize_hardware()
            self.available = True
        except Exception:
            self.available = False
            self.sensor_instance = None

        return self.available

    def read(self) -> Dict[str, Any]:
        """
        Read sensor data if available, otherwise return n/a values.
        
        :return: Dictionary with sensor readings or "n/a" for unavailable sensors
        """
        if not self.check_availability():
            return self._get_unavailable_data()

        try:
            return self._read_sensor_data()
        except Exception:
            self.available = False
            self.sensor_instance = None
            return self._get_unavailable_data()

    @abstractmethod
    def _get_unavailable_data(self) -> Dict[str, Any]:
        """
        Return a dictionary with "n/a" values for this sensor.
        
        :return: Dictionary with "n/a" values
        """
        pass
