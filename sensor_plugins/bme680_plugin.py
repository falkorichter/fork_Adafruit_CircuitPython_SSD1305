"""
BME680 environmental sensor plugin
"""

import json
import time
from pathlib import Path
from typing import Any, Dict, Optional

from sensor_plugins.base import SensorPlugin


class BME680Plugin(SensorPlugin):
    """Plugin for BME680 environmental sensor"""

    def __init__(
        self,
        check_interval: float = 5.0,
        burn_in_time: float = 300,
        cache_file: Optional[str] = None,
    ):
        super().__init__("BME680", check_interval)
        self.burn_in_time = burn_in_time
        self.start_time = None
        self.burn_in_data = []
        self.gas_baseline = None
        self.hum_baseline = 40.0  # Must be > 0 and < 100
        self.hum_weighting = 0.25
        self.burn_in_complete = False
        
        # Cache file path - default to examples/bme680_burn_in_cache.json
        if cache_file is None:
            # Get the examples directory relative to this file
            plugin_dir = Path(__file__).parent
            repo_root = plugin_dir.parent
            examples_dir = repo_root / "examples"
            self.cache_file = examples_dir / "bme680_burn_in_cache.json"
        else:
            self.cache_file = Path(cache_file)

    def _initialize_hardware(self) -> Any:
        """Initialize BME680 sensor"""
        import bme680  # noqa: PLC0415 - Import inside method for optional dependency

        sensor = bme680.BME680(bme680.I2C_ADDR_SECONDARY)
        sensor.set_humidity_oversample(bme680.OS_2X)
        sensor.set_pressure_oversample(bme680.OS_4X)
        sensor.set_temperature_oversample(bme680.OS_8X)
        sensor.set_filter(bme680.FILTER_SIZE_3)
        sensor.set_gas_status(bme680.ENABLE_GAS_MEAS)
        sensor.set_gas_heater_temperature(320)
        sensor.set_gas_heater_duration(150)
        sensor.select_gas_heater_profile(0)

        self.start_time = time.time()
        self.burn_in_complete = False
        self.burn_in_data = []
        
        # Try to load cached burn-in data
        self._load_burn_in_cache()
        
        return sensor

    def _read_sensor_data(self) -> Dict[str, Any]:
        """Read environmental data from BME680"""
        result = {
            "temperature": "n/a",
            "humidity": "n/a",
            "pressure": "n/a",
            "gas_resistance": "n/a",
            "air_quality": "n/a",
        }

        # Collect burn-in data if needed
        curr_time = time.time()
        if not self.burn_in_complete:
            if curr_time - self.start_time < self.burn_in_time:
                if (
                    self.sensor_instance.get_sensor_data()
                    and self.sensor_instance.data.heat_stable
                ):
                    gas = self.sensor_instance.data.gas_resistance
                    self.burn_in_data.append(gas)
                    result["burn_in_remaining"] = int(
                        self.burn_in_time - (curr_time - self.start_time)
                    )
                    return result
            elif len(self.burn_in_data) > 0:
                samples_to_average = self.burn_in_data[-50:]
                self.gas_baseline = sum(samples_to_average) / len(samples_to_average)
                self.burn_in_complete = True
                # Save burn-in cache when complete
                self._save_burn_in_cache()
            else:
                self.gas_baseline = 100000
                self.burn_in_complete = True
                # Save burn-in cache when complete
                self._save_burn_in_cache()

        # Read actual sensor data
        if (
            self.sensor_instance.get_sensor_data()
            and self.sensor_instance.data.heat_stable
        ):
            result["temperature"] = self.sensor_instance.data.temperature
            result["humidity"] = self.sensor_instance.data.humidity
            result["pressure"] = self.sensor_instance.data.pressure
            result["gas_resistance"] = self.sensor_instance.data.gas_resistance

            # Calculate air quality score
            if self.burn_in_complete and self.gas_baseline:
                gas = self.sensor_instance.data.gas_resistance
                gas_offset = self.gas_baseline - gas

                hum = self.sensor_instance.data.humidity
                hum_offset = hum - self.hum_baseline

                # Calculate hum_score as the distance from the hum_baseline
                # Protect against division by zero
                if hum_offset > 0:
                    denominator = 100 - self.hum_baseline
                    if denominator > 0:
                        hum_score = (100 - self.hum_baseline - hum_offset) / (
                            100 - self.hum_baseline
                        )
                        hum_score *= self.hum_weighting * 100
                    else:
                        hum_score = 0
                elif self.hum_baseline > 0:
                    hum_score = (self.hum_baseline + hum_offset) / self.hum_baseline
                    hum_score *= self.hum_weighting * 100
                else:
                    hum_score = 0

                # Calculate gas_score as the distance from the gas_baseline
                # Protect against division by zero
                if gas_offset > 0 and self.gas_baseline > 0:
                    gas_score = (gas / self.gas_baseline) * (
                        100 - (self.hum_weighting * 100)
                    )
                else:
                    gas_score = 100 - (self.hum_weighting * 100)

                result["air_quality"] = hum_score + gas_score

        return result

    def _get_unavailable_data(self) -> Dict[str, Any]:
        """Return n/a for all BME680 values"""
        return {
            "temperature": "n/a",
            "humidity": "n/a",
            "pressure": "n/a",
            "gas_resistance": "n/a",
            "air_quality": "n/a",
        }

    def format_display(self, data: Dict[str, Any]) -> str:
        """Format air quality or burn-in status for display"""
        burn_in_remaining = data.get("burn_in_remaining")
        air_quality = data.get("air_quality", "n/a")

        if burn_in_remaining is not None:
            return f"Burn-in: {burn_in_remaining}s"
        elif air_quality != "n/a":
            return f"AirQ: {air_quality:.1f}"
        else:
            return "AirQ: n/a"

    def _load_burn_in_cache(self) -> bool:
        """
        Load burn-in data from cache if it exists and is not older than 1 hour.
        
        Returns:
            True if cache was loaded successfully, False otherwise
        """
        try:
            if not self.cache_file.exists():
                return False
            
            # Load cache data
            with open(self.cache_file) as f:
                cache_data = json.load(f)
            
            # Validate cache data structure
            if 'gas_baseline' not in cache_data or 'timestamp' not in cache_data:
                return False
            
            # Check if cache is older than 1 hour using the stored timestamp
            cache_age = time.time() - cache_data['timestamp']
            if cache_age > 3600:  # 1 hour in seconds
                return False
            
            # Apply cached values
            self.gas_baseline = cache_data['gas_baseline']
            self.burn_in_complete = True
            
            return True
        except (json.JSONDecodeError, OSError, KeyError, TypeError):
            # If any error occurs, just return False and proceed with normal burn-in
            return False

    def _save_burn_in_cache(self) -> bool:
        """
        Save burn-in data to cache file.
        
        Returns:
            True if cache was saved successfully, False otherwise
        """
        try:
            # Ensure the directory exists
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Prepare cache data
            cache_data = {
                'gas_baseline': self.gas_baseline,
                'timestamp': time.time(),
            }
            
            # Write cache to file
            with open(self.cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
            
            return True
        except OSError:
            # If we can't write the cache, just continue without it
            return False
