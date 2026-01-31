# SPDX-FileCopyrightText: 2026 Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
BME680 environmental sensor plugin
"""

import time
from typing import Any, Dict

from sensor_plugins.base import SensorPlugin


class BME680Plugin(SensorPlugin):
    """Plugin for BME680 environmental sensor"""

    def __init__(self, check_interval: float = 5.0, burn_in_time: float = 300):
        super().__init__("BME680", check_interval)
        self.burn_in_time = burn_in_time
        self.start_time = None
        self.burn_in_data = []
        self.gas_baseline = None
        self.hum_baseline = 40.0  # Must be > 0 and < 100
        self.hum_weighting = 0.25
        self.burn_in_complete = False

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
            else:
                self.gas_baseline = 100000
                self.burn_in_complete = True

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
